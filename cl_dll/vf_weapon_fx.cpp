// R1 presentation follows the existing predicted MP5 event and hitbox trace.
// Pools are bounded; this module never deals damage or changes bullet spread.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <chrono>
#include "hud.h"
#include "cl_util.h"
#include "cl_entity.h"
#include "com_model.h"
#include "triangleapi.h"
#include "pmtrace.h"
#include "pm_defs.h"
#include "pm_materials.h"
#include "event_api.h"
#include "r_efx.h"
#include "vf_weapon_fx.h"
#include "exports.h"
#include "vf_engine.h"
#include "vf_effect_math.h"
#include "vf_character.h"
#include "vf_skinmenu.h"
#include "vf_ui.h"
#include "../game_shared/vf_weapon_fx_catalog.h"
extern "C" {
#include "pm_shared.h"
}
#undef min
#undef max
namespace {
using vfx::V; namespace u=vfui;
const int MaxParticles=512,MaxFlashes=64,MaxTrails=64;
const char* kinds[]={"muzzle","impact","particle","smoke","core"};
const char* surfaces[]={"hard","metal","wood","flesh"};
cvar_t* debug=0;
HSPRITE sprites[8][5]={};bool warmed=false;
int codes[33]={};bool lab=false;int chosen=7;
bool layers[5]={true,true,true,true,true}; // muzzle, trails, particles, decals, sound
struct Particle { V p,v,n; float born,life,size,gravity; int profile,kind; bool surface,active; };
struct Flash { V fallback,axis,up; int player,profile; float born; bool active; };
struct Trail { V from,to; int player,profile; float born; bool active; };
Particle particles[MaxParticles]={};Flash flashes[MaxFlashes]={};Trail trails[MaxTrails]={};
unsigned int shots=0,hits=0,misses=0,marks=0,audios=0,sky=0,frames=0,drawn=0,overwrites=0,frontDraws=0,sideDraws=0,stockSuppressed=0,materialHits[4]={};
int particleCursor=0,flashCursor=0,trailCursor=0,peak=0;
double renderMs=0;float lastTime=0;
float Now(){return gEngfuncs.GetClientTime();}
V Read(const float* f){return V(f[0],f[1],f[2]);}
float Length(V a){return sqrtf(a.x*a.x+a.y*a.y+a.z*a.z);}
V Normal(V a){float n=Length(a);return n>.001f?a*(1/n):V(0,0,1);}
V Cross(V a,V b){return V(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);}
float Rand(float a,float b){return gEngfuncs.pfnRandomFloat(a,b);}
u::Color Color(int p){return u::Color{vfshot::profiles[p].color[0],vfshot::profiles[p].color[1],vfshot::profiles[p].color[2]};}
bool Bind(int p,int k,float phase){
 if(!sprites[p][k]){char path[96];snprintf(path,sizeof(path),"sprites/vf_weaponfx/%s_%s.spr",vfshot::profiles[p].id,kinds[k]);sprites[p][k]=gEngfuncs.pfnSPR_Load(path);}
 if(!sprites[p][k])return false;
 int n=gEngfuncs.pfnSPR_Frames(sprites[p][k]);if(n<1)return false;
 int frame=int(phase*n);if(frame<0)frame=0;if(frame>=n)frame=n-1;
 return gEngfuncs.pTriAPI->SpriteTexture(const_cast<model_s*>(gEngfuncs.GetSpritePointer(sprites[p][k])),frame)!=0;
}
void Quad(V a,V b,V c,V d){
 triangleapi_t* t=gEngfuncs.pTriAPI;t->Begin(TRI_QUADS);
 t->TexCoord2f(0,0);t->Vertex3f(a.x,a.y,a.z);t->TexCoord2f(1,0);t->Vertex3f(b.x,b.y,b.z);
 t->TexCoord2f(1,1);t->Vertex3f(c.x,c.y,c.z);t->TexCoord2f(0,1);t->Vertex3f(d.x,d.y,d.z);t->End();++drawn;
}
void Tint(int p,float alpha){const vfshot::Profile& d=vfshot::profiles[p];gEngfuncs.pTriAPI->Color4f(d.color[0]/255.f,d.color[1]/255.f,d.color[2]/255.f,alpha);}
void Sprite(int p,int kind,V center,V right,V up,float size,float phase,float alpha){
 if(!Bind(p,kind,phase))return;Tint(p,alpha);V r=right*size,z=up*size;Quad(center-r-z,center+r-z,center+r+z,center-r+z);
}
void Beam(int p,V a,V b,V view,float size,float phase,float alpha){
 if(!Bind(p,2,phase))return;Tint(p,alpha);V side=Normal(Cross(b-a,view))*size;Quad(a-side,a+side,b+side,b-side);
}
bool FirstPerson(int player){
 cl_entity_t* local=gEngfuncs.GetLocalPlayer();return local&&player==local->index&&!CL_IsThirdPerson();
}
V Muzzle(int player,V fallback){
 cl_entity_t* e=FirstPerson(player)?gEngfuncs.GetViewModel():gEngfuncs.GetEntityByIndex(player);
 if(!e||!e->model)return fallback;
 V point=Read(e->attachment[0]);
 // Attachments are initially zero before the first rendered frame.
 if(Length(point-fallback)>100||Length(point)<.01f)return fallback;
 return point;
}
void MuzzleCone(const Flash& x,float phase){
 V base=Muzzle(x.player,x.fallback),axis=x.axis,up=x.up;
 cl_entity_t* e=FirstPerson(x.player)?gEngfuncs.GetViewModel():gEngfuncs.GetEntityByIndex(x.player);
 if(e&&Length(Read(e->attachment[0])-base)<1){
  V delta=Read(e->attachment[1])-base,vertical=Read(e->attachment[3])-base;
  if(Length(delta)>4&&Length(delta)<14&&Length(vertical)>4&&Length(vertical)<14){axis=Normal(delta);up=Normal(vertical);}
 }
 V side=Normal(Cross(axis,up));up=Normal(Cross(side,axis));
 const vfshot::Profile& d=vfshot::profiles[x.profile];
 // The shooter sees a dedicated radial flash, never the side-view plume.
 // External cameras crossfade between head-on and axial art as the angle changes.
 float angles[3],forward[3],right[3],vertical[3];gEngfuncs.GetViewAngles(angles);
 gEngfuncs.pfnAngleVectors(angles,forward,right,vertical);
 V view=Read(forward);float alignment=fabsf(axis.x*view.x+axis.y*view.y+axis.z*view.z);
 float front=FirstPerson(x.player)?1.f:fminf(1.f,fmaxf(0.f,(alignment-.55f)/.35f));
 float lateral=1.f-front;
 float length=d.muzzleSize*1.65f*(.85f+.15f*sinf(phase*3.14159f));
 float radius=d.muzzleSize*.32f*(.8f+.2f*phase);
 if(lateral>.01f&&Bind(x.profile,0,phase)){
  // Axial planes are only visible in an external oblique/side view.
  for(int plane=0;plane<3;++plane){
   float angle=plane*1.04719755f;V radial=side*cosf(angle)+up*sinf(angle);
   V rimNear=radial*.26f,rimFar=radial*radius,end=base+axis*length;
   Tint(x.profile,.86f*lateral);
   triangleapi_t* api=gEngfuncs.pTriAPI;api->Begin(TRI_QUADS);
   V verts[4]={base-rimNear,base+rimNear,end+rimFar,end-rimFar};
   const float uv[4][2]={{.0625f,.875f},{.0625f,.125f},{.9375f,.125f},{.9375f,.875f}};
   for(int v=0;v<4;++v){api->TexCoord2f(uv[v][0],uv[v][1]);api->Vertex3f(verts[v].x,verts[v].y,verts[v].z);}
   api->End();++drawn;
  }
  ++sideDraws;
 }
 // The frontal star is perpendicular to the actual barrel and centered at its tip.
 // It naturally becomes edge-on from the side; no camera-facing lateral sprite.
 Sprite(x.profile,4,base+axis*1.5f,side,up,d.muzzleSize*(.10f+.30f*front),phase,.20f+.68f*front);
 ++frontDraws;
}
void AddParticle(int profile,int kind,V p,V v,V n,float size,float life,float gravity=0,bool surface=false){
 Particle& x=particles[particleCursor++%MaxParticles];if(x.active&&Now()-x.born<x.life)++overwrites;
 x.p=p;x.v=v;x.n=n;x.born=Now();x.life=life;x.size=size;x.gravity=gravity;x.profile=profile;x.kind=kind;x.surface=surface;x.active=true;
}
int Message(const char*,int size,void* data){
 if(size!=2)return 0;unsigned char* b=(unsigned char*)data;
 if(b[0]<1||b[0]>32||b[1]>vfshot::Count)return 0;
 codes[b[0]]=b[1];cl_entity_t* local=gEngfuncs.GetLocalPlayer();
 if(local&&local->index==b[0])chosen=b[1]?b[1]-1:vfshot::Default;
 gEngfuncs.Con_DPrintf("VFShot sync: player=%d code=%d\n",b[0],b[1]);return 1;
}
void Choose(const char* id){
 int code=-1;if(!strcmp(id,"auto"))code=0;
 for(int i=0;i<vfshot::Count;++i)if(!strcmp(id,vfshot::profiles[i].id))code=i+1;
 if(code<0){gEngfuncs.Con_Printf("Weapon FX: unknown profile.\n");return;}
 char cmd[80];snprintf(cmd,sizeof(cmd),"vf_fx_profile %s\n",id);gEngfuncs.pfnServerCmd(cmd);
}
void SelectCommand(){if(gEngfuncs.Cmd_Argc()==2)Choose(gEngfuncs.Cmd_Argv(1));else gEngfuncs.Con_Printf("vf_shotfx <hydro|electro|cryo|thermal|toxic|corrosion|sonic|kinetic|auto>\n");}
void Open(){lab=true;u::SetDeveloper(true);VF_CharacterShow(0);u::OpenEffects();gEngfuncs.pfnClientCmd("-attack\n-attack2\n");}
void Clear(){
 memset(particles,0,sizeof(particles));memset(flashes,0,sizeof(flashes));memset(trails,0,sizeof(trails));
 shots=hits=misses=marks=audios=sky=frames=drawn=overwrites=frontDraws=sideDraws=stockSuppressed=0;memset(materialHits,0,sizeof(materialHits));peak=0;renderMs=0;particleCursor=flashCursor=trailCursor=0;
}
void ClearCommand(){
 Clear();
 for(int p=0;p<8;++p){char name[32];snprintf(name,sizeof(name),"{vf_%s",vfshot::profiles[p].id);
  int index=gEngfuncs.pEfxAPI->Draw_DecalIndexFromName(name);if(index>0)gEngfuncs.pEfxAPI->R_DecalRemoveAll(index);
 }
}
void Audit(){
 int count=0;for(int p=0;p<8;++p)for(int k=0;k<5;++k)if(Bind(p,k,0))++count;
 int decals=0;for(int p=0;p<8;++p){char name[32];snprintf(name,sizeof(name),"{vf_%s",vfshot::profiles[p].id);if(gEngfuncs.pEfxAPI->Draw_DecalIndexFromName(name)>0)++decals;}
 gEngfuncs.Con_Printf("VFShot audit: profiles=8 sprites=%d/40 decals=%d/8\n",count,decals);
}
void Stats(){
 int alive=0;for(int i=0;i<MaxParticles;++i)if(particles[i].active&&Now()-particles[i].born<particles[i].life)++alive;
 gEngfuncs.Con_Printf("VFShot stats: shots=%u hits=%u misses=%u decals=%u audio=%u sky=%u hard=%u metal=%u wood=%u flesh=%u alive=%d peak=%d capacity=512 overwrites=%u drawn=%u frames=%u muzzle_front=%u muzzle_side=%u stock_suppressed=%u mean_ms=%.4f\n",
 shots,hits,misses,marks,audios,sky,materialHits[0],materialHits[1],materialHits[2],materialHits[3],alive,peak,overwrites,drawn,frames,frontDraws,sideDraws,stockSuppressed,frames?renderMs/frames:0);
}
void Layers(){
 if(gEngfuncs.Cmd_Argc()!=6)return;for(int i=0;i<5;++i)layers[i]=atoi(gEngfuncs.Cmd_Argv(i+1))!=0;
}
}
bool VF_WeaponFXSuppressStudioFlash(const cl_entity_s* entity,int eventCode){
 if(eventCode!=5001&&eventCode!=5011&&eventCode!=5021&&eventCode!=5031)return false;
 if(!entity||!entity->model||strncmp(entity->model->name,"models/vf_r01/r01_",17))return false;
 ++stockSuppressed;return true;
}
int VF_WeaponFXProfile(int player,int eventCode){
 if(player<1||player>32)return -1;
 if(eventCode>0&&eventCode<=vfshot::Count)return eventCode-1;
 if(!VF_EngineIsReferenceWeapon(player))return -1;
 return codes[player]>0&&codes[player]<=vfshot::Count?codes[player]-1:vfshot::Default;
}
void VF_WeaponFXFire(int player,int p,const float* source,const float* forward,const float* right,const float* up){
 if(p<0||p>=8)return;++shots;
 if(debug&&debug->value>0)gEngfuncs.Con_Printf("VFShot fire: player=%d profile=%s local=%d\n",player,vfshot::profiles[p].id,gEngfuncs.GetLocalPlayer()&&player==gEngfuncs.GetLocalPlayer()->index?1:0);
 const vfshot::Profile& d=vfshot::profiles[p];V fallback=Read(source)+Read(forward)*30+Read(right)*3+Read(up)*-4;
 Flash& f=flashes[flashCursor++%MaxFlashes];f.fallback=fallback;f.axis=Read(forward);f.up=Read(up);f.player=player;f.profile=p;f.born=Now();f.active=layers[0];
 V muzzle=Muzzle(player,fallback);
 if(layers[0]&&d.lightRadius>0){dlight_t* light=gEngfuncs.pEfxAPI->CL_AllocDlight(7000+player);if(light){
  light->origin[0]=muzzle.x;light->origin[1]=muzzle.y;light->origin[2]=muzzle.z;light->radius=d.lightRadius;
  light->color.r=d.color[0];light->color.g=d.color[1];light->color.b=d.color[2];light->die=Now()+d.muzzleLife;light->decay=d.lightRadius/d.muzzleLife;
 }}
 if(layers[4]){char path[96];snprintf(path,sizeof(path),"vf_weaponfx/%s_fire.wav",d.id);
  gEngfuncs.pEventAPI->EV_PlaySound(player,const_cast<float*>(source),CHAN_WEAPON,path,.85f,ATTN_NORM,0,98+gEngfuncs.pfnRandomLong(0,4));++audios;
 }
}
void VF_WeaponFXTrace(int player,int p,const float* source,const float* end,pmtrace_s* tr){
 if(p<0||p>=8||!tr)return;
 const vfshot::Profile& d=vfshot::profiles[p];V from=Read(source),to=Read(tr->endpos),n=Normal(Read(tr->plane.normal));
 V fallback=from+Normal(to-from)*30+V(0,0,-4);
 if(layers[1]){Trail& t=trails[trailCursor++%MaxTrails];t.from=Muzzle(player,fallback);t.to=to;t.player=player;t.profile=p;t.born=Now();t.active=true;
  if(tr->fraction>=1&&Length(t.to-t.from)>2048)t.to=t.from+Normal(t.to-t.from)*2048;
 }
 if(tr->fraction>=1||tr->allsolid||tr->startsolid){++misses;return;}
 int entity=gEngfuncs.pEventAPI->EV_IndexFromTrace(tr);
 physent_t* pe=gEngfuncs.pEventAPI->EV_GetPhysent(tr->ent);
 bool flesh=(entity>0&&entity<=gEngfuncs.GetMaxClients())||(pe&&pe->studiomodel&&pe->solid!=SOLID_BSP);
 const char* texture=flesh?NULL:gEngfuncs.pEventAPI->EV_TraceTexture(tr->ent,const_cast<float*>(source),const_cast<float*>(end));
 char tex[64]={};if(texture){strncpy(tex,texture,sizeof(tex)-1);char* t=tex;
  if(*t=='+'||*t=='-')t+=2;if(*t=='{'||*t=='!'||*t=='~'||*t==' ')++t;
  if(t!=tex)memmove(tex,t,strlen(t)+1);
 }
 if(!strncmp(tex,"sky",3)){++sky;return;}
 char material=flesh?CHAR_TEX_FLESH:PM_FindTextureType(tex);
 int surface=material==CHAR_TEX_METAL||material==CHAR_TEX_GRATE||material==CHAR_TEX_VENT?1:material==CHAR_TEX_WOOD?2:material==CHAR_TEX_FLESH?3:0;
 ++hits;++materialHits[surface];
 V center=to+n*1.1f;
 if(layers[2]){
  AddParticle(p,1,center,V(),n,p==6?3.5f:2.5f,.15f,0,true);
  AddParticle(p,3,center+n*2,V(0,0,p==3?16.f:8.f),n,2.4f,d.particleLife*.65f);
  int count=d.particles+(surface==1?3:0);
  for(int i=0;i<count;++i){V v=Normal(V(Rand(-1,1),Rand(-1,1),Rand(-1,1))+n*.9f)*Rand(12,surface==1?40.f:30.f);
   float gravity=(p==0||p==2||p==5||p==7)?100.f:p==3?-15.f:0;
   float size=p==4?.65f:surface==3?.65f:Rand(.35f,.85f);
   AddParticle(p,2,center,v,n,size,d.particleLife*Rand(.6f,1),gravity);
  }
 }
 if(layers[3]&&!flesh&&pe&&pe->solid==SOLID_BSP){
  char name[32];snprintf(name,sizeof(name),"{vf_%s",d.id);
  int index=gEngfuncs.pEfxAPI->Draw_DecalIndexFromName(name);
  if(index>0){gEngfuncs.pEfxAPI->R_FireCustomDecal(gEngfuncs.pEfxAPI->Draw_DecalIndex(index),entity,0,tr->endpos,0,64.f/d.decalSize);++marks;}
 }
 if(layers[4]){char path[96];snprintf(path,sizeof(path),"vf_weaponfx/%s_hit_%s.wav",d.id,surfaces[surface]);
  gEngfuncs.pEventAPI->EV_PlaySound(0,tr->endpos,CHAN_STATIC,path,.65f,ATTN_NORM,0,98+gEngfuncs.pfnRandomLong(0,4));++audios;
 }
}
void VF_WeaponFXWorld(){
 float now=Now();if(now<lastTime){Clear();}lastTime=now;
 if(!warmed){for(int p=0;p<8;++p)for(int k=0;k<5;++k){char path[96];snprintf(path,sizeof(path),"sprites/vf_weaponfx/%s_%s.spr",vfshot::profiles[p].id,kinds[k]);sprites[p][k]=gEngfuncs.pfnSPR_Load(path);Bind(p,k,0);}warmed=true;}
 auto started=std::chrono::steady_clock::now();
 float angles[3],f[3],r[3],z[3];gEngfuncs.GetViewAngles(angles);gEngfuncs.pfnAngleVectors(angles,f,r,z);
 V right=Read(r),up=Read(z),forward=Read(f);
 triangleapi_t* api=gEngfuncs.pTriAPI;api->CullFace(TRI_NONE);api->RenderMode(kRenderTransAdd);drawn=0;int alive=0;
 for(int i=0;i<MaxFlashes;++i){Flash& x=flashes[i];if(!x.active)continue;float age=now-x.born,life=vfshot::profiles[x.profile].muzzleLife;
  if(age<0||age>=life){x.active=false;continue;}
  MuzzleCone(x,age/life);
 }
 for(int i=0;i<MaxTrails;++i){Trail& t=trails[i];if(!t.active)continue;const vfshot::Profile& d=vfshot::profiles[t.profile];float age=now-t.born;
  if(age<0||age>=d.trailLife){t.active=false;continue;}float phase=age/d.trailLife,alpha=(1-phase)*.75f;V from=Muzzle(t.player,t.from),delta=t.to-from,prev=from;
  int segments=t.profile==1?24:t.profile==6?12:1;
  for(int j=1;j<=segments;++j){V point=from+delta*(float(j)/segments);
   if(t.profile==1&&j<segments)point=point+right*(sinf(j*17.f+floorf(age*50)*3)*2)+up*(cosf(j*9.f)*2);
   Beam(t.profile,prev,point,forward,d.trailWidth*.17f,phase,alpha);prev=point;
  }
 }
 for(int i=0;i<MaxParticles;++i){Particle& x=particles[i];if(!x.active)continue;float age=now-x.born;
  if(age<0||age>=x.life){x.active=false;continue;}++alive;float phase=age/x.life;
  V point=x.p+x.v*age+V(0,0,-.5f*x.gravity*age*age),rx=right,uz=up;
  if(x.surface){rx=Normal(Cross(x.n,fabsf(x.n.z)>.9f?V(0,1,0):V(0,0,1)));uz=Normal(Cross(rx,x.n));}
  float size=x.size*(x.kind==3?1+phase*2:x.profile==6&&x.kind==1?1+phase*3:1);
  float alpha=(1-phase)*(x.kind==3?.30f:1.f);
  Sprite(x.profile,x.kind,point,rx,uz,size,phase,alpha);
 }
 if(alive>peak)peak=alive;
 api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);
 renderMs+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-started).count();++frames;
}
void VF_WeaponFXInit(){
 debug=gEngfuncs.pfnRegisterVariable("vf_shotfx_debug","0",0);
 gEngfuncs.pfnAddCommand("vf_shotfx",SelectCommand);gEngfuncs.pfnAddCommand("vf_shotfx_lab",Open);
 gEngfuncs.pfnAddCommand("vf_shotfx_clear",ClearCommand);gEngfuncs.pfnAddCommand("vf_shotfx_audit",Audit);
 gEngfuncs.pfnAddCommand("vf_shotfx_stats",Stats);gEngfuncs.pfnAddCommand("vf_shotfx_layers",Layers);
 gEngfuncs.pfnHookUserMsg("VFShot",Message);VF_WeaponFXReset();
}
void VF_WeaponFXReset(){Clear();memset(codes,0,sizeof(codes));memset(sprites,0,sizeof(sprites));lastTime=0;warmed=false;chosen=vfshot::Default;lab=false;}
bool VF_WeaponFXGuide(){
 if(!lab)return false;
 u::Text(24,195,"WEAPON FX / LIVE R1 TEST",u::white);
 if(u::Button(1040,192,216,30,"Effect catalogue"))lab=false;
 u::Wrap(24,237,"Select a vector, close this panel and fire the R1. The server confirms the test profile.",650,u::muted,2);
 for(int i=0;i<8;++i){float x=24+(i%4)*310.f,y=300+(i/4)*86.f;
  if(u::Button(x,y,294,66,vfshot::profiles[i].name,chosen==i))Choose(vfshot::profiles[i].id);
  u::Box(x,y+60,294,4,Color(i));
 }
 const char* materials[]={"concrete","metal","wood","flesh","sky","brush"};
 const char* aims[]={"Concrete","Metal","Wood","Studio target","Sky","Brush entity"};
 for(int i=0;i<6;++i)if(u::Button(24+i*157.f,469,148,30,aims[i])){
  char cmd[80];snprintf(cmd,sizeof(cmd),"vf_fx_camera %s\n",materials[i]);gEngfuncs.pfnServerCmd(cmd);
 }
 if(u::Button(980,469,276,30,"Open FX test range"))gEngfuncs.pfnClientCmd("map vf_fx_range\nwait 180\nweapon_9mmAR\nvf_shotfx_lab\n");

 const char* labels[]={"Muzzle / light","Shot trails","Impact / particles","Surface decals","Sound"};
 for(int i=0;i<5;++i)if(u::Button(24+i*249.f,513,237,38,labels[i],layers[i]))layers[i]=!layers[i];
 u::Wrap(24,578,"6 hits of the selected vector within 3 seconds trigger a 6-second status. Default: Kinetic. Cosmetics do not select elements. Surface audio: hard / metal / wood / flesh.",1180,u::muted,3);
 if(u::Button(24,660,290,40,"Return to gameplay / Kinetic")){Choose("auto");lab=false;VF_CharacterGameplay(0);}
 if(u::Button(329,660,290,40,"Clear FX / marks / counters"))ClearCommand();
 if(u::Button(634,660,622,40,"Close and test the equipped R1",true)){VF_CharacterClose();VF_SkinsClose();}
 return true;
}
void VF_WeaponFXHud(){
 if(!u::Developer()||VF_CharacterOpen())return;
 cl_entity_t* local=gEngfuncs.GetLocalPlayer();int code=local&&local->index>0&&local->index<=32?codes[local->index]:0;
 if(!code)return;
 u::Box(24,540,585,65,u::bg,205);char text[120];snprintf(text,sizeof(text),"R1 SHOT FX / %s / DEVELOPER TEST",vfshot::profiles[code-1].name);
 u::Text(36,552,text,Color(code-1),560);u::Text(36,578,"F3 > Weapon FX : profile / presentation layers",u::white,560);
}
