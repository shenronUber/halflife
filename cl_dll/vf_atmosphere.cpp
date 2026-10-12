// Cosmetic scenery outside vf_modular. No entities, traces, damage or movement state.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <algorithm>
#include <chrono>
#include "hud.h"
#include "cl_util.h"
#include "cl_entity.h"
#include "triangleapi.h"
#include "vf_atmosphere.h"
#undef min
#undef max
extern vec3_t v_origin;
namespace {
constexpr float Pi=3.14159265359f;
struct V {float x,y,z; V(float X=0,float Y=0,float Z=0):x(X),y(Y),z(Z){} V operator+(V b)const{return V(x+b.x,y+b.y,z+b.z);} V operator-(V b)const{return V(x-b.x,y-b.y,z-b.z);} V operator*(float s)const{return V(x*s,y*s,z*s);} };
struct Bank {V center;float width,height,shade,alpha,depth;bool horizontal,flip;};
cvar_t *enabled=nullptr,*quality=nullptr,*clockOverride=nullptr,*layers=nullptr;
HSPRITE sprites[3]={};bool attempted[3]={};
const char* paths[]={"sprites/vf_atmosphere/cloud.spr","sprites/vf_atmosphere/deck.spr","sprites/vf_atmosphere/white.spr"};
bool active=false;int drawn=0,loaded=0;float animation=0,flash=0;
unsigned frames=0;double cpuTotal=0;int bench=0;double benchCPU[180],benchFrame[180];
std::chrono::steady_clock::time_point previous;
float Fraction(float v){return v-floorf(v);}
float Hash(int n){return Fraction(sinf(float(n)*127.13f+17.71f)*43758.5453f);}
float Dot(V a,V b){return a.x*b.x+a.y*b.y+a.z*b.z;}
V Cross(V a,V b){return V(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);}
V Normalize(V a){float length=sqrtf(Dot(a,a));return length>.001f?a*(1/length):V(1,0,0);}
bool Modular(){
 const char* level=gEngfuncs.pfnGetLevelName();if(!level)return false;
 const char* name=level;for(const char* p=level;*p;++p)if(*p=='/'||*p=='\\')name=p+1;
 return !strcmp(name,"vf_modular.bsp")||!strcmp(name,"vf_modular");
}
bool Bind(int id,int frame=0){
 if(!attempted[id]){attempted[id]=true;sprites[id]=gEngfuncs.pfnSPR_Load(paths[id]);
  gEngfuncs.Con_DPrintf("VFAtmosphere texture: id=%d loaded=%d\n",id,sprites[id]!=0);}
 model_s* model=sprites[id]?const_cast<model_s*>(gEngfuncs.GetSpritePointer(sprites[id])):nullptr;
 return model&&gEngfuncs.pTriAPI->SpriteTexture(model,frame)!=0;
}
void Color(float r,float g,float b,float a){gEngfuncs.pTriAPI->Color4fRendermode(r,g,b,a,kRenderTransAlpha);}
void Vertex(V p,float u,float v){auto* api=gEngfuncs.pTriAPI;api->TexCoord2f(u,v);api->Vertex3f(p.x,p.y,p.z);}
void Quad(V c,V right,V up,bool flip=false){
 Vertex(c-right-up,flip?1.f:0.f,1);Vertex(c+right-up,flip?0.f:1.f,1);
 Vertex(c+right+up,flip?0.f:1.f,0);Vertex(c-right+up,flip?1.f:0.f,0);
}
void Info(){gEngfuncs.Con_Printf("VFAtmosphere active=%d enabled=%d quality=%d loaded=%d banks=%d time=%.3f wind=%.3f,%.3f flash=%.3f cpu_mean_ms=%.4f frames=%u collision=0\n",
 active,enabled&&enabled->value>0,quality?int(quality->value):0,loaded,drawn,animation,animation*38,animation*11,flash,frames?cpuTotal/frames:0,frames);}
void Bench(){bench=1;previous=std::chrono::steady_clock::now();}
void BaseDeck(){
 if(!Bind(1))return;auto* api=gEngfuncs.pTriAPI;
 // Native TriAPI does not preserve vertex opacity. The texture carries the radial feather.
 Color(1,1,1,1);api->Begin(TRI_QUADS);Quad(V(0,0,-940),V(11500,0,0),V(0,11500,0));api->End();
}
int Gather(Bank* banks,int capacity,V eye,V forward,V right,V up,int detail,float time){
 int count=0;
 auto add=[&](V center,float width,float height,float shade,float alpha,bool horizontal,bool flip){
  if(count>=capacity||alpha<.005f)return;
  V delta=center-eye;float depth=Dot(delta,forward),r=width+height;
  if(depth< -r||fabsf(Dot(delta,right))>depth*1.7f+r||fabsf(Dot(delta,up))>depth*1.1f+r)return;
  banks[count++]={center,width,height,shade,alpha,Dot(delta,delta),horizontal,flip};
 };
 // World-anchored coordinates: only the wind moves the clouds.
 int rings=detail>=2?5:4;
 for(int y=-rings;y<=rings;++y)for(int x=-rings;x<=rings;++x){
  int id=(y+5)*11+x+5;float h=Hash(id+1),j=Hash(id+197);
  float px=x*1450.f+260*(h-.5f)+time*38,py=y*1450.f+260*(j-.5f)+time*11;
  const float span=(2*rings+1)*1450.f;
  px=Fraction((px+span*.5f)/span)*span-span*.5f;py=Fraction((py+span*.5f)/span)*span-span*.5f;
  float radius=sqrtf(px*px+py*py),fade=std::max(0.f,std::min(1.f,(8300-radius)/2600));
  add(V(px,py,-825+45*h),1000+350*j,1000+350*j,.95f,fade*.92f,true,id%2!=0);
  float mx=Fraction((x*1450.f+260*(h-.5f)+time*17+span*.5f)/span)*span-span*.5f;
  float my=Fraction((y*1450.f+260*(j-.5f)-time*23+span*.5f)/span)*span-span*.5f;
  float mr=sqrtf(mx*mx+my*my);
  if(detail>=2&&mr<6000)add(V(mx+300,my-170,-680+75*j+22*sinf(time*.07f+id)),800+210*h,800+210*h,1.f,fade*.65f,true,id%3!=0);
 }
 // Upper banks remain beyond all playable platforms.
 for(int i=0;i<10;++i){float a=i*2*Pi/10+time*.0012f;
  add(V(cosf(a)*8600,sinf(a)*8600,2100+260*Hash(i+550)),1900,640,.61f,.24f,false,i%2!=0);
 }
 // Distant funnel joining the upper storm to the cloud ocean.
 if(detail>=2)for(int ring=0;ring<10;++ring)for(int i=0;i<4;++i){
  float t=ring/9.f,a=i*Pi*.5f+time*.16f+ring*.47f,r=70+620*t*t;
  V c(-7200+160*sinf(t*3+time*.03f)+cosf(a)*r,4700+cosf(t*4)*120+sinf(a)*r,-1040+2900*t);
  add(c,160+540*t*t,210+140*t,.32f+.1f*t,.52f,false,(i+ring)%2!=0);
 }
 std::sort(banks,banks+count,[](const Bank& a,const Bank& b){return a.depth>b.depth;});return count;
}
void Lightning(V eye,float time){
 // Two pulse bursts followed by a long calm; no lights on actors or geometry.
 float phase=fmodf(time,23.f);flash=0;
 if(phase>6.8f&&phase<7.03f)flash=.85f*sinf((phase-6.8f)/.23f*Pi);
 if(phase>7.19f&&phase<7.31f)flash=.58f*sinf((phase-7.19f)/.12f*Pi);
 if(flash<.015f||!Bind(2))return;
 auto* api=gEngfuncs.pTriAPI;api->RenderMode(kRenderTransAdd);api->Begin(TRI_QUADS);
 V prev(6600,6500,2600);int tick=int(time*22);
 for(int i=1;i<=11;++i){V next(6600+105*sinf(float(i*17+tick)),6500+65*cosf(float(i*9+tick)),2600-i*245.f);
  V width=Normalize(Cross(next-prev,eye-prev));
  api->Color4f(.38f,.61f,1,flash*.24f);Quad((prev+next)*.5f,width*24,(next-prev)*.5f);
  api->Color4f(.88f,.95f,1,flash);Quad((prev+next)*.5f,width*4,(next-prev)*.5f);
  if(i==4||i==7){V branch=next+V(-220,70,-190);api->Color4f(.7f,.85f,1,flash*.55f);Quad((next+branch)*.5f,width*2,(branch-next)*.5f);}
  prev=next;
 }api->End();api->RenderMode(kRenderTransAlpha);
}
}
void VF_AtmosphereInit(){
 enabled=gEngfuncs.pfnRegisterVariable("vf_atmosphere","1",FCVAR_ARCHIVE);
 quality=gEngfuncs.pfnRegisterVariable("vf_atmosphere_quality","2",FCVAR_ARCHIVE);
 clockOverride=gEngfuncs.pfnRegisterVariable("vf_atmosphere_time","-1",0);
 layers=gEngfuncs.pfnRegisterVariable("vf_atmosphere_layers","7",0);
 gEngfuncs.pfnAddCommand("vf_atmosphere_info",Info);gEngfuncs.pfnAddCommand("vf_atmosphere_bench",Bench);
 VF_AtmosphereReset();
}
void VF_AtmosphereReset(){memset(sprites,0,sizeof(sprites));memset(attempted,0,sizeof(attempted));active=false;drawn=loaded=0;animation=flash=0;frames=0;cpuTotal=0;bench=0;}
void VF_AtmosphereWorld(){
 auto start=std::chrono::steady_clock::now();active=Modular();drawn=loaded=0;flash=0;
 if(!active||!enabled||enabled->value<=0||!gEngfuncs.pTriAPI||!gEngfuncs.pTriAPI->Color4fRendermode)return;
 float time=clockOverride&&clockOverride->value>=0?clockOverride->value:gEngfuncs.GetClientTime();
 if(!std::isfinite(time))return;time=std::max(0.f,time);animation=time;
 float angles[3],f[3],r[3],u[3];gEngfuncs.GetViewAngles(angles);gEngfuncs.pfnAngleVectors(angles,f,r,u);
 V eye(v_origin[0],v_origin[1],v_origin[2]),forward(f[0],f[1],f[2]),right(r[0],r[1],r[2]),up(u[0],u[1],u[2]);
 auto* api=gEngfuncs.pTriAPI;api->CullFace(TRI_NONE);api->RenderMode(kRenderTransAlpha);
 int mask=layers?int(layers->value):7;
 if(mask&1)BaseDeck();
 Bank banks[320];int detail=quality&&quality->value>=2?2:1;
 int count=Gather(banks,320,eye,forward,right,up,detail,time);
 const float coverage[]={.03f,.08f,.16f,.25f,.4f,.55f,.75f,1.f};int bound=-1;
 for(int i=0;i<count;++i){const Bank& b=banks[i];if(!(mask&(b.horizontal?2:4)))continue;
   int frame=0;for(int j=1;j<8;++j)if(fabsf(coverage[j]-b.alpha)<fabsf(coverage[frame]-b.alpha))frame=j;
   // Bake uniform coverage in RGBA frames; never depend on the legacy TriAPI vertex-alpha bug.
   if(frame!=bound){if(bound>=0)api->End();if(!Bind(0,frame)){bound=-1;continue;}api->Begin(TRI_QUADS);bound=frame;}
   Color(b.shade,b.shade,b.shade,1);
   V x,y;if(b.horizontal){x=V(b.width,0,0);y=V(0,b.height,0);}else{
    V tangent=Normalize(V(eye.y-b.center.y,b.center.x-eye.x,0));
    x=tangent*b.width;y=Normalize(Cross(tangent,Normalize(eye-b.center)))*b.height;
   }Quad(b.center,x,y,b.flip);++drawn;
 }if(bound>=0)api->End();
 Lightning(eye,time);
 for(int i=0;i<3;++i)loaded+=sprites[i]!=0;
 api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);
 auto now=std::chrono::steady_clock::now();double ms=std::chrono::duration<double,std::milli>(now-start).count();cpuTotal+=ms;++frames;
 if(bench){int n=bench-1;benchCPU[n]=ms;benchFrame[n]=std::chrono::duration<double,std::milli>(now-previous).count();previous=now;
  if(++bench>180){double cpu=0,frame=0;for(int i=0;i<180;++i){cpu+=benchCPU[i];frame+=benchFrame[i];}
   std::sort(benchCPU,benchCPU+180);std::sort(benchFrame,benchFrame+180);
   gEngfuncs.Con_Printf("VFAtmosphere bench: samples=180 banks=%d cpu_mean_ms=%.4f cpu_p95_ms=%.4f frame_mean_ms=%.4f frame_p95_ms=%.4f\n",drawn,cpu/180,benchCPU[170],frame/180,benchFrame[170]);bench=0;
  }
 }
}

