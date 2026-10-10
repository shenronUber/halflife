#ifndef VF_STATUS_POLICY_H
#define VF_STATUS_POLICY_H
#include "vf_status_catalog.h"
namespace vfs {
struct State { float until[Count], applied[Count]; };
inline void Reset(State& s){for(int i=0;i<Count;++i)s.until[i]=s.applied[i]=0;}
inline bool Active(const State& s,int id,float now){return id>=0&&id<Count&&s.until[id]>now;}
inline bool Expire(State& s,float now){bool changed=false;for(int i=0;i<Count;++i)if(s.until[i]>0&&s.until[i]<=now){s.until[i]=s.applied[i]=0;changed=true;}return changed;}
struct Result {int id;bool entered;};
inline Result Apply(State& s,int id,float now,float duration){
 if(id<0||id>=Count||duration<=0)return Result{-1,false};
 Expire(s,now);int partner=-1,result=-1;
 if(effects[id].kind==0){
  for(int i=0;i<Count;++i)if(Active(s,i,now)&&effects[i].kind==0&&Reaction(id,i)>=0)
   if(partner<0||s.applied[i]>s.applied[partner]){partner=i;result=Reaction(id,i);}
 }
 if(result>=0){s.until[id]=s.applied[id]=0;s.until[partner]=s.applied[partner]=0;id=result;}
 if(effects[id].kind==1){s.until[effects[id].a]=s.applied[effects[id].a]=0;s.until[effects[id].b]=s.applied[effects[id].b]=0;}
 bool entered=!Active(s,id,now);s.until[id]=now+duration;s.applied[id]=now;
 return Result{id,entered};
}
inline Result ApplyPrimary(State& s,int id,float now,float duration){
 if(id<0||id>=8||effects[id].kind!=0||duration<=0)return Result{-1,false};
 Expire(s,now);bool entered=!Active(s,id,now);s.until[id]=now+duration;s.applied[id]=now;return Result{id,entered};
}
// Two components enter atomically: only their resulting state gets an onset cue.
inline Result ApplyPair(State& s,int a,int b,float now,float duration){int id=Reaction(a,b);return id<0?Result{-1,false}:Apply(s,id,now,duration);}
}
#endif
