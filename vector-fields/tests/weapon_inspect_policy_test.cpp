#include "../../game_shared/vf_weapon_inspect.h"
#include <assert.h>
#include <stdio.h>
#include <math.h>
int main(){
 vf::InspectState s;
 assert(!s.Begin(10,4,true)&&!s.Begin(10,2,false));
 assert(s.Begin(10,4,false)&&!s.Begin(11,4,false)&&s.start==10);
 assert(s.Update(11,4,false));assert(!s.Update(11,4,true));
 assert(s.Begin(12,4,false));assert(!s.Update(13,2,false));
 assert(s.Begin(14,4,false));assert(!s.Update(13,4,false));
 assert(s.Begin(20,4,false)&&s.Update(24.49f,4,false)&&!s.Update(24.5f,4,false));
 assert(s.Begin(30,4,false));s.Reset();assert(!s.active&&s.weapon==0);
 assert(vf::InspectSample(0).yaw==0&&vf::InspectSample(4.5f).yaw==0);
 assert(vf::InspectSample(.8f).yaw==-48&&vf::InspectSample(.8f).pitch==42);
 for(int i=1;i<=14;++i){
  const float t=i*.05f;
  assert(vf::InspectSample(t+.05f).pitch>vf::InspectSample(t).pitch);
  assert(vf::InspectSample(t+.05f).yaw<vf::InspectSample(t).yaw);
 }
 assert(vf::InspectSample(1.5f).yaw==-48&&vf::InspectSample(3.1f).yaw==48);
 assert(vf::InspectSample(1.5f).pitch>40&&vf::InspectSample(3.1f).pitch>40);
 assert(vf::InspectSample(1.5f).roll<0&&vf::InspectSample(3.1f).roll>0);
 float last=0;
 for(int i=0;i<=4500;++i){
  const vf::InspectPose p=vf::InspectSample(i*.001f);
  assert(fabsf(p.yaw)<=48&&fabsf(p.roll)<=12&&fabsf(p.yaw-last)<.24f);
  last=p.yaw;
 }
 for(int i=0;i<2;++i){
  const float t=i?3.1f:1.5f;
  assert(vf::InspectSample(t-.1f).yaw==vf::InspectSample(t+.1f).yaw);
 }
 assert(fabsf(vf::InspectSample(.001f).yaw)<.0001f);
 assert(fabsf(vf::InspectSample(4.499f).yaw)<.0001f);
 puts("PASS inspection: continuous faster opening, opposite sides, readable holds, smooth return, combat/weapon/clock cancellation, no retrigger");
}
