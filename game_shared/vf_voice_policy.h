// Scheduling policy shared by the game and deterministic tests.
#ifndef VF_VOICE_POLICY_H
#define VF_VOICE_POLICY_H
namespace vfv {
enum { MaxEvents=32 };
struct State {
    float next[MaxEvents], busyUntil, nextGlobal;
    int last[MaxEvents], priority, pendingEvent;
    float pendingAt, pendingUntil;
};
inline void Reset(State& s) {
    s.busyUntil=s.nextGlobal=0;s.priority=0;s.pendingEvent=-1;s.pendingAt=s.pendingUntil=0;
    for(int i=0;i<MaxEvents;++i){s.next[i]=0;s.last[i]=-1;}
}
inline void QueueEffect(State& s,int event,float now){s.pendingEvent=event;s.pendingAt=now+.12f;s.pendingUntil=now+2.0f;}
inline int PendingEffect(State& s,bool active,bool alive,float now){
    if(!active||!alive||now>s.pendingUntil){s.pendingEvent=-1;return -1;}
    return now>=s.pendingAt?s.pendingEvent:-1;
}
inline bool CanSpeak(const State& s,int event,int priority,float now) {
    if(event<0||event>=MaxEvents)return false;
    if(priority>=100)return true; // death must always replace the current utterance
    if(now<s.next[event])return false;
    if((now<s.busyUntil||now<s.nextGlobal)&&priority<=s.priority)return false;
    return true;
}
inline void Commit(State& s,int event,int clip,int priority,float now,float duration,float cooldown) {
    s.next[event]=now+cooldown;s.last[event]=clip;s.priority=priority;
    s.busyUntil=now+duration;s.nextGlobal=s.busyUntil+0.35f;
}
inline int Select(const int* choices,int count,int previous,unsigned int roll) {
    if(count<=0)return -1;
    int available=count;
    for(int i=0;i<count;++i)if(choices[i]==previous&&count>1){--available;break;}
    int pick=roll%available;
    for(int i=0;i<count;++i){
        if(count>1&&choices[i]==previous)continue;
        if(pick--==0)return choices[i];
    }
    return -1;
}
}
#endif

