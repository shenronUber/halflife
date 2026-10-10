// Screen-edge geometry shared by native feedback and visibility checks.
#ifndef VF_STATUS_FEEDBACK_H
#define VF_STATUS_FEEDBACK_H
#include <cmath>
#include <algorithm>
#include "vf_effect_catalog.h"
#include "vf_status_decal_catalog.h"
namespace vffeedback {
struct Point {float x,y;};
struct Rect {float left,top,right,bottom;};
struct FrameBlend {int current,next;float mix;};
// Disjoint strips own the corners once; screen coordinates and UVs agree.
inline Rect DecalEdge(int edge){const float b=vfdecal::Border;
 if(edge==0)return {0,0,b,1};if(edge==1)return {1-b,0,1,1};
 if(edge==2)return {b,0,1-b,b};return {b,1-b,1-b,1};
}
inline FrameBlend DecalFrame(int id,float elapsed){
 if(id<0||id>=vfdecal::Count||!std::isfinite(elapsed))return {0,1,0};
 float cycle=fmodf(std::max(0.f,elapsed),4096.f)*vfdecal::assets[id].fps;
 int whole=int(floorf(cycle));float mix=cycle-whole;
 return {whole%vfdecal::Frames,(whole+1)%vfdecal::Frames,mix*mix*(3-2*mix)};
}

struct Quad {Point p[4];int texture;float r,g,b,a;};
inline float Clamp(float x,float a,float b){return x<a?a:x>b?b:x;}
inline float Fade(float now,float start,float until){return Clamp((now-start)/.16f,0,1)*Clamp((until-now)/.35f,0,1);}
inline bool Protected(Point p,float w,float h){return p.x>w*.16f&&p.x<w*.84f&&p.y>h*.16f&&p.y<h*.80f;}
struct Builder {
 Quad* out;int count,capacity;float w,h,scale;int edge;float r,g,b,alpha;
 Builder(Quad* q,int cap,float W,float H):out(q),count(0),capacity(cap),w(W),h(H),scale(H/720.f),edge(0),r(1),g(1),b(1),alpha(1){}
 Point Clip(Point p){p.x=Clamp(p.x,0,w);p.y=Clamp(p.y,0,h);
  if(edge==0)p.x=Clamp(p.x,0,w*.12f);if(edge==1)p.x=Clamp(p.x,w*.88f,w);
  if(edge==2)p.y=Clamp(p.y,0,h*.12f);if(edge==3)p.y=Clamp(p.y,h*.88f,h);return p;}
 void Emit(Point a,Point b,Point c,Point d,int tex,float opacity){if(count>=capacity)return;
  Quad q; q.p[0]=Clip(a);q.p[1]=Clip(b);q.p[2]=Clip(c);q.p[3]=Clip(d);q.texture=tex;q.r=r;q.g=g;q.b=this->b;q.a=Clamp(alpha*opacity,0,1);out[count++]=q;}
 void Sprite(float x,float y,float rx,float ry,int tex,float opacity){Emit({x-rx,y-ry},{x+rx,y-ry},{x+rx,y+ry},{x-rx,y+ry},tex,opacity);}
 void Line(Point a,Point b,float width,float opacity){float dx=b.x-a.x,dy=b.y-a.y,len=sqrtf(dx*dx+dy*dy);if(len<.1f)return;
  float x=-dy/len*width,y=dx/len*width;Emit({a.x-x,a.y-y},{a.x+x,a.y+y},{b.x+x,b.y+y},{b.x-x,b.y-y},4,opacity);}
 void Diamond(float x,float y,float rx,float ry,float opacity){Emit({x,y-ry},{x+rx,y},{x,y+ry},{x-rx,y},4,opacity);}
};
inline int Generate(int id,int edge,float now,float w,float h,float alpha,Quad* out,int capacity){
 if(id<0||id>=vfx::Count||edge<0||edge>3||!out||capacity<=0||w<1||h<1||!std::isfinite(now))return 0;
 Builder b(out,capacity,w,h);b.edge=edge;b.alpha=alpha;now=fmodf(now,4096.f);
 const vfx::Effect& e=vfx::effects[id];int components[2]={id,-1};int passes=1;
 if(e.kind==1){components[0]=e.parentA;components[1]=e.parentB;passes=2;}
 // Steam is recognisable as pale vapor rather than continuing to show flames.
 if(id==15){components[0]=15;components[1]=0;}
 for(int pass=0;pass<passes;++pass){int type=components[pass];const vfx::Effect& c=vfx::effects[type];
  b.r=c.color[0]/255.f;b.g=c.color[1]/255.f;b.b=c.color[2]/255.f;
  for(int i=0;i<6;++i){float seed=(i+.37f+pass*.31f)/6.f;
   float cycle=(now*(type==0||type==5?.30f:.18f)+seed);cycle-=floorf(cycle);
   float phase=seed*6.2831853f;float s=b.scale;
   float along=.14f+.72f*seed,depth=(16+9*sinf(now*1.4f+phase)+pass*13)*s;
   float x=edge==0?depth:edge==1?w-depth:w*along;
   float y=edge==2?depth:edge==3?h-depth:h*along;
   float fade=.55f+.25f*sinf(cycle*3.14159265f);
   switch(type){
    case 0:case 5: // Falling water / thicker corrosive drops.
     if(edge<2)y=h*(.12f+.76f*cycle);
     b.Sprite(x,y,(type==0?5:8)*s,(type==0?18:24)*s,0,fade);
     if(type==5)b.Sprite(x+12*s,y-8*s,9*s,9*s,0,.48f);break;
    case 1: // Six-segment branching electrical edge arcs; continuous, no strobe.
     for(int j=0;j<5;++j){Point a={x+s*(j*9-20),y+s*(sinf(now*3+j*2+phase)*13)},z={x+s*((j+1)*9-20),y+s*(sinf(now*3+(j+1)*2+phase)*13)};
      if(edge<2){a={x+s*sinf(now*3+j*2+phase)*13,y+s*(j*9-20)};z={x+s*sinf(now*3+(j+1)*2+phase)*13,y+s*((j+1)*9-20)};}b.Line(a,z,1.8f*s,.84f);}
     break;
    case 2: // Frost crystals with distinct branch silhouette.
     b.Diamond(x,y,9*s,22*s,.67f);b.Line({x-14*s,y-9*s},{x+14*s,y+9*s},1.5f*s,.75f);
     b.Line({x-14*s,y+9*s},{x+14*s,y-9*s},1.5f*s,.75f);break;
    case 3: // Flame licks stay on the frame, rising and fading at the edge.
     y-=cycle*24*s;b.Sprite(x,y,20*s,(34+12*cycle)*s,3,fade);b.Sprite(x,y+20*s,18*s,18*s,1,.32f);break;
    case 4: // Purple spores drift up; clearly distinct from green acid.
     y-=cycle*32*s;b.Sprite(x+sin(now+phase)*9*s,y,9*s,9*s,0,fade);
     b.Sprite(x-12*s,y+18*s,3*s,3*s,1,.7f);break;
    case 6:case 16:case 17: // Expanding sound waves, phase orbit, collapsing null.
     {float radius=(type==17?28-18*cycle:10+20*cycle)*s;
      for(int j=0;j<14;++j){float a=j*6.2831853f/14,aa=(j+1)*6.2831853f/14;
       b.Line({x+cosf(a)*radius,y+sinf(a)*radius},{x+cosf(aa)*radius,y+sinf(aa)*radius},1.2f*s,type==17?.7f:.48f);}}break;
    case 7: // Impact splinters, no camera shake or full-screen flash.
     b.Line({x-12*s,y-18*s},{x+7*s,y},2*s,.8f);b.Line({x+7*s,y},{x-2*s,y+16*s},2*s,.8f);
     b.Diamond(x+15*s,y+13*s,3*s,7*s,.8f);break;
    case 15: // Steam at the perimeter leaves the center clear.
     b.Sprite(x,y,32*s,39*s,2,.38f);break;
    case 18: // Protective hexagons.
     for(int j=0;j<6;++j){float a=j*6.2831853f/6,aa=(j+1)*6.2831853f/6;
      b.Line({x+cosf(a)*19*s,y+sinf(a)*19*s},{x+cosf(aa)*19*s,y+sinf(aa)*19*s},1.7f*s,.72f);}break;
    case 19: // Scanner brackets.
     b.Line({x-13*s,y-18*s},{x-13*s,y+18*s},1.6f*s,.8f);b.Line({x-13*s,y-18*s},{x+13*s,y-18*s},1.6f*s,.8f);
     b.Line({x-13*s,y+18*s},{x+13*s,y+18*s},1.6f*s,.8f);break;
    case 20: // Paired chevrons and moving orange energy sparks.
     for(int j=0;j<2;++j){float xx=x+j*10*s;b.Line({xx-8*s,y-13*s},{xx+4*s,y},2*s,.75f);b.Line({xx+4*s,y},{xx-8*s,y+13*s},2*s,.75f);}
     b.Sprite(x,y+24*s*sinf(now*2+phase),5*s,5*s,1,.75f);break;
   }
  }
 }
 return b.count;
}
}
#endif
