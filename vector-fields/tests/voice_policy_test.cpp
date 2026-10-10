#include <cassert>
#include <cstdio>
#include "../../game_shared/vf_voice_policy.h"
#include "../../game_shared/vf_status_policy.h"
#include "../../game_shared/vf_voice_catalog.h"
#include <cstring>
#include "../../game_shared/vf_taunt_policy.h"
#include "../../game_shared/vf_death_policy.h"
int main(){
    vfv::State s;vfv::Reset(s);
    assert(vfv::CanSpeak(s,7,10,0));
    vfv::Commit(s,7,42,10,0,3,6); // taunt
    assert(!vfv::CanSpeak(s,7,10,1)); // key spam
    assert(vfv::CanSpeak(s,1,20,0.1f)); // higher-priority reload may interrupt
    assert(vfv::CanSpeak(s,3,50,1)); // pain replaces a taunt
    vfv::Commit(s,3,11,50,1,1.1f,2);
    assert(!vfv::CanSpeak(s,7,10,2.5f)); // taunt's own cooldown persists
    assert(!vfv::CanSpeak(s,3,50,2.9f)); // damage ticks do not spam
    assert(vfv::CanSpeak(s,4,100,1.1f)); // death preempts everything
    vfv::Commit(s,4,20,100,1.1f,2,0);
    assert(!vfv::CanSpeak(s,1,20,2));
    assert(vfv::CanSpeak(s,1,20,3.5f));
    assert(vfv::CanSpeak(s,7,10,6.1f));
    assert(!vfv::CanSpeak(s,-1,100,10));
    assert(!vfv::CanSpeak(s,32,100,10));
    int options[]={8,12,17},single[]={19};
    for(unsigned int i=0;i<1000;++i){
        int id=vfv::Select(options,3,12,i);
        assert(id==8||id==17);
        assert(vfv::Select(single,1,19,i)==19);
    }
    assert(vfv::Select(options,0,-1,0)==-1);
    vfv::Reset(s);
    assert(s.last[7]==-1&&vfv::CanSpeak(s,7,10,0)); // restore clears transient sound state
    assert(s.pendingEvent==-1);
    vfv::QueueEffect(s,vfv::E_hydro,10);
    assert(vfv::PendingEffect(s,true,true,10.1f)==-1);
    vfv::QueueEffect(s,vfv::E_arc_chain,10.05f);
    assert(vfv::PendingEffect(s,true,true,10.18f)==vfv::E_arc_chain);
    assert(vfv::PendingEffect(s,false,true,10.2f)==-1&&s.pendingEvent==-1);
    vfv::QueueEffect(s,vfv::E_hydro,20);assert(vfv::PendingEffect(s,true,false,20.2f)==-1);
    vfv::QueueEffect(s,vfv::E_hydro,30);assert(vfv::PendingEffect(s,true,true,32.1f)==-1);
    vfs::State effects;vfs::Reset(effects);
    for(int i=0;i<vfs::Count;++i){assert(!strcmp(vfs::effects[i].id,vfv::Events[vfv::E_hydro+i]));}
    int pairs=0;
    for(int a=0;a<8;++a)for(int b=a+1;b<8;++b){int rc=vfs::Reaction(a,b);if(rc<0)continue;++pairs;
        for(int order=0;order<2;++order){vfs::Reset(effects);int x=order?b:a,y=order?a:b;
            assert(vfs::Apply(effects,x,1,6).entered);
            vfs::Result r=vfs::Apply(effects,y,1.05f,6);assert(r.id==rc&&r.entered);
            assert(!vfs::Active(effects,a,1.1f)&&!vfs::Active(effects,b,1.1f)&&vfs::Active(effects,rc,1.1f));
            assert(!vfs::Apply(effects,rc,2,6).entered);assert(vfs::Active(effects,rc,7));
            assert(vfs::Expire(effects,8)&&!vfs::Active(effects,rc,8));
        }
        vfs::Reset(effects);assert(vfs::ApplyPair(effects,a,b,1,6).id==rc);
    }
    assert(pairs==8);vfs::Reset(effects);
    assert(vfs::ApplyPair(effects,vfs::S_hydro,vfs::S_cryo,1,6).id==-1);
    vfs::Apply(effects,vfs::S_hydro,1,1);vfs::Result isolated=vfs::Apply(effects,vfs::S_electro,2.1f,6);
    assert(isolated.id==vfs::S_electro); // expired components cannot form reactions
    vfs::Reset(effects);vfs::Apply(effects,vfs::S_hydro,1,6);vfs::Apply(effects,vfs::S_thermal,1.1f,6);
    vfs::Apply(effects,vfs::S_electro,1.2f,6);assert(vfs::Active(effects,vfs::S_steam_veil,1.3f)&&vfs::Active(effects,vfs::S_electro,1.3f)); // no triple
    vfs::Reset(effects);vfs::Apply(effects,vfs::S_hydro,1,6);vfs::Apply(effects,vfs::S_cryo,2,6);
    assert(vfs::Apply(effects,vfs::S_electro,3,6).id==vfs::S_superconduction); // most recent compatible component
    assert(vfs::Active(effects,vfs::S_hydro,3.1f));
    assert(vfs::Apply(effects,-1,1,6).id==-1&&vfs::Apply(effects,vfs::Count,1,6).id==-1);
    assert(vfd::ActorCount==vfv::ActorCount&&vfd::ClipCount==102);
    for(int e=0;e<vfs::Count;++e){
        vfs::Reset(effects);vfs::Apply(effects,e,10,3);
        int cause=vfd::CauseFor(effects,11);
        assert(vfs::effects[e].kind<2?vfd::Causes[cause].effect==e:cause==vfd::D_standard);
        assert(vfd::CauseFor(effects,13)==vfd::D_standard);
        for(int a=0;a<vfv::ActorCount;++a){int index=vfd::Index(a,cause);
            assert(index>=0&&vfd::Clips[index].actor==a&&vfd::Clips[index].cause==cause&&vfd::Clips[index].duration<=3);
        }
    }
    assert(vfd::Index(-1,0)==-1&&vfd::Index(0,vfd::CauseCount)==-1);
    vfs::Reset(effects);assert(vfd::CauseFor(effects,0)==vfd::D_standard);
    vfs::ApplyPrimary(effects,vfs::S_hydro,1,6);vfs::ApplyPrimary(effects,vfs::S_cryo,2,6);
    assert(vfd::CauseFor(effects,3)==vfd::D_cryo);
    vfs::Apply(effects,vfs::S_arc_chain,3,6);vfs::Apply(effects,vfs::S_thermal,4,6);
    vfs::Apply(effects,vfs::S_ward,5,6);
    assert(vfd::CauseFor(effects,6)==vfd::D_arc_chain);
    vfs::Apply(effects,vfs::S_toxic_ignition,6,6);
    assert(vfd::CauseFor(effects,7)==vfd::D_toxic_ignition);
    vfs::Reset(effects);assert(vfd::CauseFor(effects,7)==vfd::D_standard);
    puts("PASS death selection: 102 clips, 16 elemental causes, tactical fallback, expiry, reaction priority and clearing.");
    vft::Memory heard;vft::Reset(heard);assert(!vft::Reply(heard,0,1,1,true,true));
    assert(vft::Within(3,4,0,5)&&!vft::Within(3,4,.1f,5));
    assert(!vft::Chance(0,0)&&vft::Chance(1,1)&&vft::Chance(.7f,.69f)&&!vft::Chance(.7f,.7f));
    vft::Hear(heard,2,7,10,2,5);
    assert(vft::Reply(heard,16.9f,2,7,true,true));
    assert(!vft::Reply(heard,17,2,7,true,true));
    assert(!vft::Reply(heard,11,2,8,true,true)); // new life or reused slot
    assert(!vft::Reply(heard,11,3,7,true,true));
    assert(!vft::Reply(heard,11,2,7,false,true)&&!vft::Reply(heard,11,2,7,true,false));
    vft::Hear(heard,3,9,11,1,5);assert(vft::Reply(heard,12,3,9,true,true)&&!vft::Reply(heard,12,2,7,true,true));
    puts("PASS taunt policy: radius boundary, chance limits, hearing window, life identity and source validity.");
    puts("PASS effect lifecycle: eight symmetric reactions, consumption, refresh, expiry, no triples, voice mapping and cancellable onsets.");
    puts("PASS voice scheduling: cooldowns, interruption priority, death, no immediate repeats, restore.");
}

