// Bounded, deterministic visual trajectories. No game state or damage dependency.
#ifndef VF_EFFECT_MATH_H
#define VF_EFFECT_MATH_H
#include <cmath>
#include "vf_effect_catalog.h"
namespace vfx {
struct V { float x,y,z; V(float X=0,float Y=0,float Z=0):x(X),y(Y),z(Z){} V operator+(V b)const{return V(x+b.x,y+b.y,z+b.z);} V operator-(V b)const{return V(x-b.x,y-b.y,z-b.z);} V operator*(float s)const{return V(x*s,y*s,z*s);} };
struct Primitive { V a,b; float size,alpha; bool line; };
inline float Fraction(float v){return v-floorf(v);}
inline V Radial(float a,float r,float z){return V(cosf(a)*r,sinf(a)*r,z);}
inline int Generate(const Layer& l,float time,Primitive* out,int capacity){
 if(!std::isfinite(time)||!out||capacity<=0)return 0;time=fmodf(time,4096.f);int n=0;
 auto emit=[&](V a,V b,float size,float alpha,bool line){if(n<capacity){Primitive p={a,b,size,alpha,line};out[n++]=p;}};
 for(int i=0;i<l.count;++i){
  float seed=Fraction((i+1)*.618033989f),seed2=Fraction((i+1)*.41421356f);
  float t=Fraction(time*l.speed*.35f+seed),a=seed*6.2831853f,r=13+seed2*12,z=-30+60*seed;
  float fade=sinf(t*3.14159265f); V p;
  switch(l.pattern){
  case Drops:p=Radial(a,r,32-65*t);emit(p,p+V(0,0,3),l.size,.7f*fade,false);break;
  case Rise:p=Radial(a+time*.15f,r*(1-.4f*t),-31+73*t);emit(p,p,l.size*(.5f+t),.8f*fade,false);break;
  case Sparks:p=Radial(a+time*.1f,r+12*t,-26+66*t-10*t*t);emit(p,p,l.size*(1-.5f*t),fade,false);break;
  case Cloud:p=Radial(a+time*.18f,10+20*t,-20+65*t);emit(p,p,l.size*(.7f+t),.26f*fade,false);break;
  case Orbit:p=Radial(a+time*l.speed,r+4*sinf(time+seed),z+4*sinf(time*2+seed));emit(p,p,l.size,.65f,false);break;
  case Shards:p=Radial(a+time*l.speed*.3f,r+5*sinf(time+seed),z);emit(p,p+V(2,1,6),l.size,.7f,false);break;
  case Burst:p=Radial(a,10+30*t,z*(.3f+t));emit(p,p+Radial(a,4+5*t,z*.12f),l.size*.6f,fade,true);break;
  case Rings:case Collapse:case Scan:{
   float rr=l.pattern==Collapse?38*(1-t)+8:14+27*t;
   float zz=l.pattern==Scan?-34+70*t:l.pattern==Rings?(l.count<=3?-34:z):z;
   for(int s=0;s<28;++s){float q=s*6.2831853f/28;emit(Radial(q,rr,zz),Radial(q+6.2831853f/28,rr,zz),.4f,fade*.7f,true);}break;}
  case Arcs:{
   V begin=Radial(a,r,z),end=Radial(a+1.7f,r,z+12*sinf(time+seed));V prev=begin;
   float tick=floorf(time*l.speed*10);
   for(int s=1;s<=6;++s){V next=begin+(end-begin)*(s/6.f);if(s<6)next=next+V(sinf(tick+i*7+s*11)*4,cosf(tick+s*3)*4,sinf(tick*.9f+s*5)*5);emit(prev,next,.55f,.8f,true);prev=next;}break;}
  case Chain:{
   V begin(i%2?-42:42,0,12),end(0,0,-12+i*12);V prev=begin;
   emit(begin-V(0,0,3),begin+V(0,0,3),.7f,.8f,true);
   emit(begin-V(3,0,0),begin+V(3,0,0),.7f,.8f,true);
   for(int s=1;s<=12;++s){V next=begin+(end-begin)*(s/12.f);if(s<12)next.z+=sinf(floorf(time*12)+s*13+i*3)*5;emit(prev,next,.6f,.9f,true);prev=next;}break;}
  }
 }
 return n;
}
}
#endif
