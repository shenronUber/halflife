// A presentation gesture over the existing weapon rig; no sequence indices change.
#ifndef VF_WEAPON_INSPECT_H
#define VF_WEAPON_INSPECT_H
#include <math.h>
namespace vf {
static const float InspectDuration=4.5f;
static const float InspectRaiseDuration=.8f;
struct InspectPose { float pitch,yaw,roll,forward,right,up; };
static inline float InspectSmooth(float t) {t=t<0?0:t>1?1:t;const float s=t*t*t*(t*(t*6-15)+10);return s<0?0:s>1?1:s;}
static inline InspectPose InspectSample(float seconds) {
 const float times[]={0,InspectRaiseDuration,1.95f,2.75f,3.60f,InspectDuration};
 const InspectPose poses[]={
  {0,0,0,0,0,0},
  {42,-48,-12,4,2.5f,2.5f}, {42,-48,-12,4,2.5f,2.5f},
  {42,48,12,4,-2.5f,2.5f}, {42,48,12,4,-2.5f,2.5f}, {0,0,0,0,0,0}};
 if(seconds<=0||seconds>=InspectDuration)return poses[0];
 int i=0;while(i<4&&seconds>times[i+1])++i;
 const float t=InspectSmooth((seconds-times[i])/(times[i+1]-times[i]));
 InspectPose p;
 p.pitch=poses[i].pitch+(poses[i+1].pitch-poses[i].pitch)*t;
 p.yaw=poses[i].yaw+(poses[i+1].yaw-poses[i].yaw)*t;
 p.roll=poses[i].roll+(poses[i+1].roll-poses[i].roll)*t;
 p.forward=poses[i].forward+(poses[i+1].forward-poses[i].forward)*t;
 p.right=poses[i].right+(poses[i+1].right-poses[i].right)*t;
 p.up=poses[i].up+(poses[i+1].up-poses[i].up)*t;
 return p;
}
struct InspectState {
 bool active;float start;int weapon;
 InspectState():active(false),start(0),weapon(0){}
 void Reset(){active=false;start=0;weapon=0;}
 bool Begin(float now,int id,bool busy){if(active||busy||id!=4)return false;active=true;start=now;weapon=id;return true;}
 bool Update(float now,int id,bool busy){
  if(active&&(busy||id!=weapon||now<start-.05f||now-start>=InspectDuration))active=false;
  return active;
 }
};
}
#endif
