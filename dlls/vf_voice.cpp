#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "gamerules.h"
#include "vf_equipment.h"
#include "vf_voice.h"
#include "vf_status.h"
#include "vf_range.h"
#include "../game_shared/vf_voice_catalog.h"
#include "../game_shared/vf_death_policy.h"
#include <cstring>
#include <cstdio>
#include <cmath>
namespace {
cvar_t enabled={"vf_voices","1",FCVAR_SERVER};
cvar_t taunts={"vf_taunts","1",FCVAR_SERVER};
cvar_t counters={"vf_counter_taunts","1",FCVAR_SERVER};
cvar_t radius={"vf_taunt_radius","768",FCVAR_SERVER};
cvar_t window={"vf_counter_window","5",FCVAR_SERVER};
cvar_t tauntCooldown={"vf_taunt_cooldown","6",FCVAR_SERVER};
cvar_t botTaunts={"vf_bot_taunts","1",FCVAR_SERVER};
cvar_t botChance={"vf_bot_taunt_chance","0.25",FCVAR_SERVER};
cvar_t botInterval={"vf_bot_taunt_interval","12",FCVAR_SERVER};
cvar_t botCounterChance={"vf_bot_counter_chance","0.7",FCVAR_SERVER};
cvar_t botCounterDelay={"vf_bot_counter_delay","0.8",FCVAR_SERVER};
int message=0,targetMessage=0,deathMessage=0;unsigned int lifeClock=0;
float Setting(const cvar_t& c,float low,float high,float fallback){return !std::isfinite(c.value)?fallback:c.value<low?low:c.value>high?high:c.value;}
bool Bot(CBasePlayer* p){return (p->pev->flags&FL_FAKECLIENT)!=0;}
void SocialReset(CBasePlayer* p){p->m_vfVoiceLife=++lifeClock;vft::Reset(p->m_vfHeardTaunt);p->m_vfBotCounterAt=0;p->m_vfBotTauntAt=gpGlobals->time+RANDOM_FLOAT(4,10);}
void Heard(CBasePlayer*,float);
bool Audible(CBasePlayer*,CBasePlayer*);
void BotThink(CBasePlayer*);

int Priority(int e){
    if(e==vfv::E_death)return 100;
    if(e==vfv::E_respawn)return 10; // personal complaint, below gameplay warnings
    if(e==vfv::E_low_health)return 80;
    if(e==vfv::E_armor_break)return 70;
    if(e>=vfv::E_arc_chain&&e<=vfv::E_steam_veil)return 65;
    if(e>=vfv::E_hydro)return 60;
    if(e==vfv::E_pain)return 50;
    if(e==vfv::E_reload||e==vfv::E_kill)return 20;
    return 10;
}
float Cooldown(int e){
    if(e==vfv::E_death)return 0;
    if(e==vfv::E_pain)return 2.0f;
    if(e==vfv::E_taunt||e==vfv::E_counter_taunt)return Setting(tauntCooldown,1,60,6);
    if(e==vfv::E_reload)return 8.0f;
    if(e==vfv::E_kill)return 5.0f;
    if(e==vfv::E_low_health||e==vfv::E_armor_break)return 15.0f;
    return 10.0f;
}
bool Ready(CBasePlayer* p,bool allowDead=false){
    return p&&enabled.value!=0&&!(p->pev->flags&FL_SPECTATOR)&&!p->IsObserver()
        &&!(p->pev->flags&FL_PROXY)&&(allowDead||p->IsAlive());
}
int Event(const char* text){
    for(int i=0;i<vfv::EventCount;++i)if(!strcmp(text,vfv::Events[i]))return i;
    return -1;
}
}
void VF_VoiceRegister(){
    CVAR_REGISTER(&enabled);CVAR_REGISTER(&taunts);CVAR_REGISTER(&counters);
    CVAR_REGISTER(&radius);CVAR_REGISTER(&window);CVAR_REGISTER(&tauntCooldown);
    CVAR_REGISTER(&botTaunts);CVAR_REGISTER(&botChance);CVAR_REGISTER(&botInterval);
    CVAR_REGISTER(&botCounterChance);CVAR_REGISTER(&botCounterDelay);
}
void VF_VoicePrecache(){
    if(!message)message=REG_USER_MSG("VFVoice",3);
    if(!targetMessage)targetMessage=REG_USER_MSG("VFRangeVoice",4);
    if(!deathMessage)deathMessage=REG_USER_MSG("VFDeath",4);
    for(int i=0;i<vfv::ClipCount;++i)if(vfv::Clips[i].event!=vfv::E_death)PRECACHE_SOUND(const_cast<char*>(vfv::Clips[i].path));
    for(int i=0;i<vfd::ClipCount;++i)PRECACHE_SOUND(const_cast<char*>(vfd::Clips[i].path));
    ALERT(at_console,"VFDeath precache: actors=%d causes=%d clips=%d\n",vfd::ActorCount,vfd::CauseCount,vfd::ClipCount);
    ALERT(at_console,"VFVoice precache: actors=%d clips=%d\n",vfv::ActorCount,vfv::ClipCount);
}
void VF_VoiceRestore(CBasePlayer* p){
    if(p->m_vfVoice<1||p->m_vfVoice>vfv::ActorCount)p->m_vfVoice=RANDOM_LONG(1,vfv::ActorCount);
    vfv::Reset(p->m_vfVoiceState);SocialReset(p);
    p->m_vfVoiceSpawnAt=0;p->m_vfVoiceSpawnEvent=vfv::E_spawn;p->m_vfVoiceDeathSpoken=false;VF_StatusReset(p);
}
void VF_VoiceSpawn(CBasePlayer* p){
    p->m_vfVoiceSpawnEvent=p->m_vfVoiceDied?vfv::E_respawn:vfv::E_spawn;
    p->m_vfVoiceDied=0;
    p->m_vfVoice=RANDOM_LONG(1,vfv::ActorCount); // server chooses once per life
    p->m_vfVoiceDeathSpoken=false;VF_StatusReset(p);SocialReset(p);
    vfv::Reset(p->m_vfVoiceState);
    // New clients cannot yet hear sounds at Spawn. Wait until their HUD is ready.
    p->m_vfVoiceSpawnAt=gpGlobals->time+1.5f;
    ALERT(at_console,"VFVoice assigned: player=%d actor=%s\n",ENTINDEX(p->edict()),vfv::Actors[p->m_vfVoice-1].id);
}
void VF_VoiceEffect(CBasePlayer* p,int effect){
    // Brief coalescing window avoids announcing A then B when they form A+B.
    vfv::QueueEffect(p->m_vfVoiceState,vfv::E_hydro+effect,gpGlobals->time);
}
bool VF_VoiceDeath(CBasePlayer* p){
    p->m_vfVoiceDied=1; // record real death even when voices are disabled
    p->m_vfVoiceState.pendingEvent=-1;p->m_vfVoiceSpawnAt=0;
    vft::Reset(p->m_vfHeardTaunt);p->m_vfBotCounterAt=0;
    if(p->m_vfVoiceDeathSpoken)return true;
    // Read effects before Killed clears them. DeathSound calls this again later.
    if(p->m_vfVoice<1||p->m_vfVoice>vfv::ActorCount)p->m_vfVoice=RANDOM_LONG(1,vfv::ActorCount);
    p->m_vfVoiceDeathSpoken=true; // handled once per life, including muted deaths
    if(Ready(p,true))VF_VoiceEntityDeath(p,p->m_vfVoice-1,p->m_vfVoiceState,p->m_vfStatus);
    return true;
}
void VF_VoiceThink(CBasePlayer* p){
    VF_StatusThink(p);
    if(Bot(p))BotThink(p);
    vfv::State& s=p->m_vfVoiceState;
    if(s.pendingEvent>=0){
        int effect=s.pendingEvent-vfv::E_hydro;
        int event=vfv::PendingEffect(s,vfs::Active(p->m_vfStatus,effect,gpGlobals->time),p->IsAlive()!=0,gpGlobals->time);
        if(event>=0&&VF_VoiceSpeak(p,event))s.pendingEvent=-1;
    }
    if(p->m_vfVoiceSpawnAt>0&&gpGlobals->time>=p->m_vfVoiceSpawnAt){
        p->m_vfVoiceSpawnAt=0;VF_VoiceSpeak(p,p->m_vfVoiceSpawnEvent);
    }
}
bool VF_VoiceSpeak(CBasePlayer* p,int event,bool audition){
    if(event<0||event>=vfv::EventCount||!Ready(p,event==vfv::E_death))return false;
    if(event==vfv::E_death){
        if(p->m_vfVoice<1||p->m_vfVoice>vfv::ActorCount)p->m_vfVoice=RANDOM_LONG(1,vfv::ActorCount);
        return audition?VF_VoiceEntityDeath(p,p->m_vfVoice-1,p->m_vfVoiceState,p->m_vfStatus,true):VF_VoiceDeath(p);
    }
    if(event==vfv::E_respawn&&Bot(p))return false; // no human owner for a private complaint
    if(p->m_vfVoice<1||p->m_vfVoice>vfv::ActorCount)VF_VoiceRestore(p);
    if((event==vfv::E_taunt||event==vfv::E_counter_taunt)&&!taunts.value)return false;
    if(event==vfv::E_counter_taunt&&!counters.value)return false;
    vfv::State& state=p->m_vfVoiceState;float now=gpGlobals->time;int priority=Priority(event);
    // Audition bypasses scheduling only; callers must check developer permission.
    if(!audition&&!vfv::CanSpeak(state,event,priority,now))return false;
    int choices[16],count=0;
    for(int i=0;i<vfv::ClipCount;++i)
        if(vfv::Clips[i].actor==p->m_vfVoice-1&&vfv::Clips[i].event==event&&count<16)choices[count++]=i;
    int previous=event==vfv::E_respawn?p->m_vfVoiceRespawnLast-1:state.last[event];
    int index=vfv::Select(choices,count,previous,static_cast<unsigned int>(RANDOM_LONG(0,0x7fff)));
    if(index<0)return false;
    const vfv::Clip& clip=vfv::Clips[index];
    vfv::Commit(state,event,index,priority,now,clip.duration,Cooldown(event));
    if(event==vfv::E_respawn)p->m_vfVoiceRespawnLast=index+1;
    if(event==vfv::E_taunt||event==vfv::E_counter_taunt){
        state.next[vfv::E_taunt]=state.next[vfv::E_counter_taunt]=now+Cooldown(event);
    }
    // Native positional sound replication includes the emitter. CHAN_VOICE
    // replaces lower-priority speech; it never interrupts weapons or footsteps.
    bool social=event==vfv::E_taunt||event==vfv::E_counter_taunt;
    // Xash/GoldSrc uses dist_mult=attenuation/1000. Keep the native cutoff
    // aligned with the reply radius; protocol attenuation is capped below 4.
    float attenuation=social?1000.0f/Setting(radius,256,1024,768):ATTN_NORM;
    // Personal respawn dialogue has no positional sound broadcast. Its owner
    // plays the precached clip locally after a reliable private user message.
    bool personal=event==vfv::E_respawn;
    if(!personal)EMIT_SOUND_DYN(p->edict(),CHAN_VOICE,clip.path,0.85f,attenuation,0,PITCH_NORM);
    if(message){
        if(personal){
            MESSAGE_BEGIN(MSG_ONE,message,NULL,p->edict());
            WRITE_BYTE(ENTINDEX(p->edict()));WRITE_BYTE(clip.actor);WRITE_BYTE(index);MESSAGE_END();
            ALERT(at_console,"VFVoice private: player=%d event=respawn recipients=1\n",ENTINDEX(p->edict()));
        }else if(social){
            for(int i=1;i<=gpGlobals->maxClients;++i){CBaseEntity* e=UTIL_PlayerByIndex(i);if(!e||!e->IsPlayer())continue;
                CBasePlayer* listener=static_cast<CBasePlayer*>(e);
                if(Bot(listener)||(listener!=p&&!Audible(p,listener)))continue;
                MESSAGE_BEGIN(MSG_ONE,message,NULL,listener->edict());
                WRITE_BYTE(ENTINDEX(p->edict()));WRITE_BYTE(clip.actor);WRITE_BYTE(index);MESSAGE_END();
            }
        }else{
            MESSAGE_BEGIN(MSG_PAS,message,p->pev->origin);
            WRITE_BYTE(ENTINDEX(p->edict()));WRITE_BYTE(clip.actor);WRITE_BYTE(index);MESSAGE_END();
        }
    }
    ALERT(at_console,"VFVoice play: player=%d actor=%s event=%s clip=%d sample=%s\n",
        ENTINDEX(p->edict()),vfv::Actors[clip.actor].id,vfv::Events[event],index,clip.path);
    if(event==vfv::E_taunt&&!audition)Heard(p,clip.duration);
    return true;
}
namespace {
bool Audible(CBasePlayer* source,CBasePlayer* listener){
    Vector delta=source->pev->origin-listener->pev->origin;
    if(!vft::Within(delta.x,delta.y,delta.z,Setting(radius,256,1024,768)))return false;
    unsigned char* pas=ENGINE_SET_PAS((float*)&source->pev->origin);
    return !pas||ENGINE_CHECK_VISIBILITY(listener->edict(),pas)!=0;
}
CBasePlayer* ReplyTarget(CBasePlayer* p){
    const vft::Memory& m=p->m_vfHeardTaunt;
    CBaseEntity* e=m.source>0&&m.source<=gpGlobals->maxClients?UTIL_PlayerByIndex(m.source):NULL;
    CBasePlayer* source=e&&e->IsPlayer()?static_cast<CBasePlayer*>(e):NULL;
    if(!counters.value||!source||source==p||!vft::Reply(m,gpGlobals->time,ENTINDEX(source->edict()),source->m_vfVoiceLife,Ready(source),Audible(source,p))){
        vft::Reset(p->m_vfHeardTaunt);p->m_vfBotCounterAt=0;return NULL;
    }
    return source;
}
void Heard(CBasePlayer* source,float duration){
    if(!counters.value)return;
    VF_RangeHear(source,duration,Setting(radius,256,1024,768),Setting(window,0,30,5));
    for(int i=1;i<=gpGlobals->maxClients;++i){CBaseEntity* e=UTIL_PlayerByIndex(i);if(!e||!e->IsPlayer()||e==source)continue;
        CBasePlayer* p=static_cast<CBasePlayer*>(e);if(!Ready(p)||!Audible(source,p))continue;
        vft::Hear(p->m_vfHeardTaunt,ENTINDEX(source->edict()),source->m_vfVoiceLife,gpGlobals->time,duration,Setting(window,0,30,5));
        p->m_vfBotCounterAt=0;
        if(Bot(p)&&botTaunts.value&&vft::Chance(Setting(botCounterChance,0,1,.7f),RANDOM_FLOAT(0,1)))
            p->m_vfBotCounterAt=gpGlobals->time+duration+Setting(botCounterDelay,.1f,5,.8f)*RANDOM_FLOAT(.7f,1.3f);
        ALERT(at_console,"VFVoice heard: listener=%d source=%d bot=%d expires=%.2f\n",i,ENTINDEX(source->edict()),Bot(p),p->m_vfHeardTaunt.until);
    }
}
void BotThink(CBasePlayer* p){
    if(!Ready(p)||!taunts.value||!botTaunts.value){p->m_vfBotCounterAt=0;return;}
    CBasePlayer* reply=ReplyTarget(p);
    if(reply){
        if(p->m_vfBotCounterAt>0&&gpGlobals->time>=p->m_vfBotCounterAt)VF_VoiceTaunt(p);
        return; // a declined answer is not retried via the initiative probability
    }
    if(gpGlobals->time<p->m_vfBotTauntAt)return;
    float interval=Setting(botInterval,2,120,12);p->m_vfBotTauntAt=gpGlobals->time+interval*RANDOM_FLOAT(1,1.5f);
    if(!vft::Chance(Setting(botChance,0,1,.25f),RANDOM_FLOAT(0,1)))return;
    for(int i=1;i<=gpGlobals->maxClients;++i){CBaseEntity* e=UTIL_PlayerByIndex(i);if(!e||!e->IsPlayer()||e==p)continue;
        CBasePlayer* other=static_cast<CBasePlayer*>(e);
        if(Ready(other)&&g_pGameRules->PlayerRelationship(p,other)!=GR_TEAMMATE&&Audible(p,other)&&p->FVisible(other)){
            VF_VoiceTaunt(p);return;
        }
    }
}
}
bool VF_VoiceTaunt(CBasePlayer* p){
    if(!Ready(p)||(Bot(p)&&!botTaunts.value))return false;
    CBasePlayer* target=ReplyTarget(p);int event=target?vfv::E_counter_taunt:vfv::E_taunt;
    if(!VF_VoiceSpeak(p,event))return false; // failed presses keep a valid reply opportunity
    ALERT(at_console,"VFVoice social: player=%d event=%s reply_to=%d bot=%d\n",ENTINDEX(p->edict()),vfv::Events[event],target?ENTINDEX(target->edict()):0,Bot(p));
    vft::Reset(p->m_vfHeardTaunt);p->m_vfBotCounterAt=0;
    float interval=Setting(botInterval,2,120,12);p->m_vfBotTauntAt=gpGlobals->time+interval*RANDOM_FLOAT(1,1.5f);
    return true;
}
void VF_VoiceDamage(CBasePlayer* p,int type,float healthBefore,float armorBefore){
    if(!p->IsAlive())return;
    int effect=-1;
    if(type&(DMG_BURN|DMG_SLOWBURN))effect=vfs::S_thermal;
    else if(type&(DMG_FREEZE|DMG_SLOWFREEZE))effect=vfs::S_cryo;
    else if(type&DMG_SHOCK)effect=vfs::S_electro;
    else if(type&DMG_ACID)effect=vfs::S_corrosion;
    else if(type&(DMG_POISON|DMG_NERVEGAS))effect=vfs::S_toxic;
    else if(type&DMG_SONIC)effect=vfs::S_sonic;
    else if(type&(DMG_CLUB|DMG_CRUSH|DMG_FALL|DMG_BLAST))effect=vfs::S_kinetic;
    int critical=healthBefore>25&&p->pev->health<=25?vfv::E_low_health:
        armorBefore>0&&p->pev->armorvalue<=0?vfv::E_armor_break:-1;
    if(effect>=0)VF_ApplyPlayerEffect(p,effect,4.0f,critical<0);
    if(critical>=0){p->m_vfVoiceState.pendingEvent=-1;VF_VoiceSpeak(p,critical);}
    else if(effect<0)VF_VoiceSpeak(p,vfv::E_pain);
}
void VF_VoiceKilled(CBasePlayer* victim,entvars_t* attacker){
    VF_VoiceDeath(victim);VF_StatusClear(victim);
    CBaseEntity* killer=CBaseEntity::Instance(attacker);
    if(!killer||!killer->IsPlayer()||killer==victim)return;
    if(g_pGameRules->PlayerRelationship(victim,killer)==GR_TEAMMATE)return;
    VF_VoiceSpeak(static_cast<CBasePlayer*>(killer),vfv::E_kill);
}
bool VF_VoiceCommand(CBasePlayer* p,const char* command){
    if(!strcmp(command,"vf_taunt")){
        if(!VF_VoiceTaunt(p))CLIENT_PRINTF(p->edict(),print_console,"VFVoice taunt unavailable (busy, cooldown, spectator, or disabled).\n");
        return true;
    }
    if(!strcmp(command,"vf_voice_info")){
        if(p->m_vfVoice<1||p->m_vfVoice>vfv::ActorCount)VF_VoiceRestore(p);
        char text[128];snprintf(text,sizeof(text),"VFVoice info: player=%d actor=%s\n",ENTINDEX(p->edict()),vfv::Actors[p->m_vfVoice-1].id);
        CLIENT_PRINTF(p->edict(),print_console,text);
        snprintf(text,sizeof(text),"VFVoice context: reply_to=%d remaining=%.2f bot=%d\n",p->m_vfHeardTaunt.source,p->m_vfHeardTaunt.until>gpGlobals->time?p->m_vfHeardTaunt.until-gpGlobals->time:0,Bot(p));
        CLIENT_PRINTF(p->edict(),print_console,text);return true;
    }
    if(!strcmp(command,"vf_voice_test")){
        if(!VF_DeveloperAllowed()||!p->IsAlive())return true;
        if(CMD_ARGC()!=2)return true;
        int damage=0,type=DMG_GENERIC;
        if(!strcmp(CMD_ARGV(1),"critical")){damage=80;type=DMG_BULLET;}
        else if(!strcmp(CMD_ARGV(1),"armor")){damage=40;type=DMG_BULLET;}
        else if(!strcmp(CMD_ARGV(1),"burn")){damage=10;type=DMG_BURN;}
        else if(!strcmp(CMD_ARGV(1),"shock")){damage=10;type=DMG_SHOCK;}
        else if(!strcmp(CMD_ARGV(1),"pain")){damage=10;type=DMG_BULLET;}
        else if(!strcmp(CMD_ARGV(1),"death")){damage=110;type=DMG_BULLET;}
        else if(!strcmp(CMD_ARGV(1),"gib")){damage=500;type=DMG_ALWAYSGIB;}
        else return true;
        vfv::Reset(p->m_vfVoiceState);p->m_vfVoiceSpawnAt=0;
        p->pev->health=100;p->pev->armorvalue=!strcmp(CMD_ARGV(1),"armor")?5:0;
        // Developer probe uses the actual damage pipeline, including armor,
        // fatal damage and voice hooks. It does not simulate a speech event.
        p->TakeDamage(VARS(INDEXENT(0)),VARS(INDEXENT(0)),damage,type);
        return true;
    }
    if(!strcmp(command,"vf_voice_set")||!strcmp(command,"vf_voice_preview")){
        if(!VF_DeveloperAllowed()){
            CLIENT_PRINTF(p->edict(),print_console,"VFVoice rejected: developer command requires local play or sv_cheats.\n");return true;
        }
        if(CMD_ARGC()!=2){
            CLIENT_PRINTF(p->edict(),print_console,"Usage: cmd vf_voice_set ACTOR / cmd vf_voice_preview EVENT\n");return true;
        }
        if(!strcmp(command,"vf_voice_set")){
            for(int i=0;i<vfv::ActorCount;++i)if(!strcmp(CMD_ARGV(1),vfv::Actors[i].id)){
                p->m_vfVoice=i+1;vfv::Reset(p->m_vfVoiceState);p->m_vfVoiceSpawnAt=0;
                CLIENT_PRINTF(p->edict(),print_console,"VFVoice audition actor selected.\n");return true;
            }
            CLIENT_PRINTF(p->edict(),print_console,"VFVoice rejected: unknown actor.\n");
        }else{
            int e=Event(CMD_ARGV(1));
            if(e<0)CLIENT_PRINTF(p->edict(),print_console,"VFVoice rejected: unknown event.\n");
            else VF_VoiceSpeak(p,e,true);
        }
        return true;
    }
    return false;
}


bool VF_VoiceEntity(CBaseEntity* entity,int actor,vfv::State& state,int event){
 if(!entity||actor<0||actor>=vfv::ActorCount||event<0||event>=vfv::EventCount||!enabled.value)return false;
 if(event==vfv::E_death){vfs::State status;vfs::Reset(status);return VF_VoiceEntityDeath(entity,actor,state,status);}
 if(!entity->IsAlive())return false;
 bool social=event==vfv::E_taunt||event==vfv::E_counter_taunt;
 if(social&&(!taunts.value||(event==vfv::E_counter_taunt&&!counters.value)))return false;
 int priority=Priority(event);float now=gpGlobals->time;if(!vfv::CanSpeak(state,event,priority,now))return false;
 int choices[16],count=0;for(int i=0;i<vfv::ClipCount&&count<16;++i)if(vfv::Clips[i].actor==actor&&vfv::Clips[i].event==event)choices[count++]=i;
 int index=vfv::Select(choices,count,state.last[event],RANDOM_LONG(0,0x7fff));if(index<0)return false;
 const vfv::Clip& clip=vfv::Clips[index];vfv::Commit(state,event,index,priority,now,clip.duration,Cooldown(event));
 EMIT_SOUND_DYN(entity->edict(),CHAN_VOICE,clip.path,.85f,social?1000.f/Setting(radius,256,1024,768):ATTN_NORM,0,PITCH_NORM);
 if(!targetMessage)targetMessage=REG_USER_MSG("VFRangeVoice",4);
 MESSAGE_BEGIN(MSG_PAS,targetMessage,entity->pev->origin);WRITE_SHORT(entity->entindex());WRITE_BYTE(actor);WRITE_BYTE(index);MESSAGE_END();
 ALERT(at_console,"VFRange voice entity=%d actor=%s event=%s clip=%d\n",entity->entindex(),vfv::Actors[actor].id,vfv::Events[event],index);return true;
}

// No VFVoice clip index or caption: the death bank has its own actor/cause ID.
bool VF_VoiceEntityDeath(CBaseEntity* entity,int actor,vfv::State& state,const vfs::State& status,bool audition){
 if(!entity||actor<0||actor>=vfd::ActorCount)return false;
 state.pendingEvent=-1;
 if(!audition&&state.last[vfv::E_death]>=0)return true;
 int cause=vfd::CauseFor(status,gpGlobals->time),index=vfd::Index(actor,cause);
 const vfd::Clip& clip=vfd::Clips[index];
 if(!audition)state.last[vfv::E_death]=index; // reset by spawn, not by effect clearing
 if(!enabled.value)return true;
 int previous=state.last[vfv::E_death];
 vfv::Commit(state,vfv::E_death,index,100,gpGlobals->time,clip.duration,0);
 if(audition)state.last[vfv::E_death]=previous;
 EMIT_SOUND_DYN(entity->edict(),CHAN_VOICE,clip.path,.85f,ATTN_NORM,0,PITCH_NORM);
 if(deathMessage){
  // Diagnostic metadata follows the same audible set as native sound. The
  // client neither plays a second sound nor prints any subtitle for a cry.
  MESSAGE_BEGIN(MSG_PAS_R,deathMessage,entity->pev->origin);
  WRITE_SHORT(entity->entindex());WRITE_BYTE(actor);WRITE_BYTE(cause);MESSAGE_END();
 }
 ALERT(at_console,"VFDeath play: entity=%d actor=%s cause=%s sample=%s\n",entity->entindex(),vfv::Actors[actor].id,vfd::Causes[cause].id,clip.path);
 return true;
}
