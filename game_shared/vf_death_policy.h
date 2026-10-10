// Select a nonverbal cause from the server state at the instant of death.
#ifndef VF_DEATH_POLICY_H
#define VF_DEATH_POLICY_H
#include "vf_status_policy.h"
#include "vf_death_catalog.h"
namespace vfd {
inline int CauseFor(const vfs::State& state,float now){
 int selected=-1;
 for(int i=0;i<vfs::Count;++i){
  if(vfs::effects[i].kind>=2||!vfs::Active(state,i,now))continue;
  if(selected<0||vfs::effects[i].kind>vfs::effects[selected].kind||
   (vfs::effects[i].kind==vfs::effects[selected].kind&&state.applied[i]>state.applied[selected]))selected=i;
 }
 if(selected>=0)for(int i=0;i<CauseCount;++i)if(Causes[i].effect==selected)return i;
 return D_standard;
}
}
#endif
