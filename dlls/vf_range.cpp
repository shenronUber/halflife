#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "monsters.h"
#include "weapons.h"
#include "vf_range.h"
#include "vf_death.h"
#include "vf_equipment.h"
#include "vf_voice.h"
#include "vf_combat.h"
#include "../game_shared/vf_proc_policy.h"
#include "../game_shared/vf_combat_policy.h"
#include "../game_shared/vf_voice_catalog.h"
#include <cstdio>
#include <cstring>
#include <cmath>
#include <algorithm>
#include <cstdlib>
#undef min
#undef max
namespace { int targetMessage=0;const char* rig="models/vf_skins/persona_rig.mdl";int outfitClock=-1; }
class CVFRangeTarget:public CBaseMonster {
public:
 int slot,skin,actor,deathMask,deathMotion;float revive,nextSync,replyAt;EHANDLE source;unsigned int sourceLife;float replyUntil;
 vfs::State status;vfp::Accumulator hits;vfv::State voice;
 void Spawn();void Precache();void KeyValue(KeyValueData*);
 int Classify(){return CLASS_HUMAN_MILITARY;}
 int BloodColor(){return BLOOD_COLOR_RED;}
 void TraceAttack(entvars_t*,float,Vector,TraceResult*,int);
 int TakeDamage(entvars_t*,entvars_t*,float,int);void Killed(entvars_t*,int);
 void EXPORT TargetThink();void Send(CBasePlayer* to=0);void Reset();
 int Save(CSave&);int Restore(CRestore&);static TYPEDESCRIPTION m_SaveData[];
};
LINK_ENTITY_TO_CLASS(vf_range_target,CVFRangeTarget);
TYPEDESCRIPTION CVFRangeTarget::m_SaveData[]={DEFINE_FIELD(CVFRangeTarget,slot,FIELD_INTEGER),DEFINE_FIELD(CVFRangeTarget,skin,FIELD_INTEGER),DEFINE_FIELD(CVFRangeTarget,actor,FIELD_INTEGER)};
int CVFRangeTarget::Save(CSave& save){if(!CBaseMonster::Save(save))return 0;return save.WriteFields("VF_RANGE",this,m_SaveData,ARRAYSIZE(m_SaveData));}
int CVFRangeTarget::Restore(CRestore& restore){if(!CBaseMonster::Restore(restore))return 0;int ok=restore.ReadFields("VF_RANGE",this,m_SaveData,ARRAYSIZE(m_SaveData));Reset();revive=IsAlive()?0:gpGlobals->time+2;nextSync=0;SetThink(&CVFRangeTarget::TargetThink);pev->nextthink=gpGlobals->time+.1f;return ok;}
void CVFRangeTarget::KeyValue(KeyValueData* k){if(!strcmp(k->szKeyName,"vf_slot")){slot=atoi(k->szValue);k->fHandled=TRUE;}else CBaseMonster::KeyValue(k);}
void CVFRangeTarget::Precache(){PRECACHE_MODEL((char*)rig);PRECACHE_MODEL("models/vf_skins/persona_scout.mdl");}
void CVFRangeTarget::Reset(){vfs::Reset(status);vfp::Reset(hits);vfv::Reset(voice);replyAt=replyUntil=0;source=NULL;sourceLife=0;}
void CVFRangeTarget::Spawn(){
 deathMask=deathMotion=0;Precache();SET_MODEL(edict(),rig);
 pev->movetype=MOVETYPE_NONE;pev->solid=SOLID_SLIDEBOX;pev->flags|=FL_MONSTER;pev->effects&=~EF_NODRAW;
 pev->takedamage=DAMAGE_YES;pev->deadflag=DEAD_NO;pev->health=pev->max_health=300;
 // Link only after solidity is set, so engine traces can find the target.
 UTIL_SetSize(pev,Vector(-16,-16,-36),Vector(16,16,36));UTIL_SetOrigin(pev,pev->origin);
 if(outfitClock<0)outfitClock=RANDOM_LONG(0,13);skin=(outfitClock+++slot*3)%14;actor=RANDOM_LONG(0,vfv::ActorCount-1);
 pev->sequence=LookupSequence("look_idle");if(pev->sequence<0)pev->sequence=0;pev->frame=0;ResetSequenceInfo();
 pev->controller[0]=pev->controller[1]=pev->controller[2]=pev->controller[3]=127;pev->blending[0]=127;pev->blending[1]=0;
 Reset();revive=0;nextSync=gpGlobals->time+1;SetThink(&CVFRangeTarget::TargetThink);pev->nextthink=gpGlobals->time+.1f;
 Send();ALERT(at_console,"VFRange target=%d entity=%d skin=%d actor=%s model=%s health=300\n",slot,entindex(),skin,vfv::Actors[actor].id,rig);
}
void CVFRangeTarget::Send(CBasePlayer* to){
 if(!targetMessage)return;MESSAGE_BEGIN(to?MSG_ONE:MSG_ALL,targetMessage,NULL,to?to->edict():NULL);
 WRITE_BYTE(1);WRITE_SHORT(entindex());WRITE_BYTE(slot);WRITE_BYTE(skin);WRITE_BYTE(actor);WRITE_BYTE(IsAlive()?1:0);WRITE_SHORT((int)pev->health);WRITE_SHORT((int)pev->max_health);
 for(int e=0;e<vfp::Elements;++e){float left=status.until[e]-gpGlobals->time;WRITE_SHORT(left>0?(int)(left*100+.5f):0);}
 for(int e=0;e<vfp::Elements;++e)WRITE_BYTE(hits.count[e]);MESSAGE_END();
}
void CVFRangeTarget::TraceAttack(entvars_t* attacker,float damage,Vector dir,TraceResult* trace,int bits){
 if(!IsAlive()||!pev->takedamage)return;
 vfc::Multipliers m={gSkillData.plrHead,gSkillData.plrChest,gSkillData.plrStomach,gSkillData.plrArm,gSkillData.plrLeg};
 damage=vfc::LegacyTraceDamage(damage,vfc::HitRegion(trace->iHitgroup),m);
 int e=(bits&DMG_BULLET)&&damage>0?VF_CurrentShotElement():-1;
 if(vfp::Hit(hits,e,gpGlobals->time)){
  vfs::Result r=vfs::ApplyPrimary(status,e,gpGlobals->time,vfp::Duration);
  if(r.entered)vfv::QueueEffect(voice,vfv::E_hydro+e,gpGlobals->time);
  ALERT(at_console,"VFProc target=%d entity=%d effect=%s hits=6 window=3 duration=6\n",slot,entindex(),vfs::effects[e].id);
 }
 SpawnBlood(trace->vecEndPos,BloodColor(),damage);AddMultiDamage(attacker,this,damage,bits);Send();
}
int CVFRangeTarget::TakeDamage(entvars_t*,entvars_t* attacker,float damage,int){
 if(!IsAlive()||!pev->takedamage)return 0;pev->health-=damage;
 if(pev->health<=0){pev->health=0;Killed(attacker,GIB_NEVER);}else VF_VoiceEntity(this,actor,voice,vfv::E_pain);Send();return 1;
}
void CVFRangeTarget::Killed(entvars_t*,int){
 if(pev->deadflag!=DEAD_NO)return;VF_DeathTarget(this,skin,status,deathMask,deathMotion);deathMask=deathMotion=0;
 VF_VoiceEntityDeath(this,actor,voice,status);pev->deadflag=DEAD_DEAD;pev->takedamage=DAMAGE_NO;pev->solid=SOLID_NOT;pev->effects|=EF_NODRAW;
 UTIL_SetOrigin(pev,pev->origin);vfs::Reset(status);vfp::Reset(hits);replyAt=0;revive=gpGlobals->time+2;Send();
 ALERT(at_console,"VFRange death target=%d respawn=2\n",slot);
}
void CVFRangeTarget::TargetThink(){
 if(!IsAlive()){if(revive>0&&gpGlobals->time>=revive)Spawn();pev->nextthink=gpGlobals->time+.1f;return;}
 StudioFrameAdvance();bool changed=vfs::Expire(status,gpGlobals->time);int old[8];memcpy(old,hits.count,sizeof(old));vfp::Expire(hits,gpGlobals->time);
 if(memcmp(old,hits.count,sizeof(old)))changed=true;
 if(voice.pendingEvent>=0){int e=voice.pendingEvent-vfv::E_hydro;int event=vfv::PendingEffect(voice,vfs::Active(status,e,gpGlobals->time),true,gpGlobals->time);if(event>=0&&VF_VoiceEntity(this,actor,voice,event))voice.pendingEvent=-1;}
 if(replyAt>0&&gpGlobals->time>=replyAt){
  CBasePlayer* p=source&&source->IsPlayer()?(CBasePlayer*)(CBaseEntity*)source:NULL;
  if(p&&p->IsAlive()&&p->m_vfVoiceLife==sourceLife&&gpGlobals->time<replyUntil&&(p->pev->origin-pev->origin).Length()<=CVAR_GET_FLOAT("vf_taunt_radius")){
   if(VF_VoiceEntity(this,actor,voice,vfv::E_counter_taunt))replyAt=0;
  }else replyAt=0;
 }
 if(changed||gpGlobals->time>=nextSync){Send();nextSync=gpGlobals->time+1;}
 pev->nextthink=gpGlobals->time+.1f;
}
void VF_RangePrecache(){VF_DeathPrecache();if(!targetMessage)targetMessage=REG_USER_MSG("VFTarget",35);outfitClock=-1;}
void VF_RangeSync(CBasePlayer* p){VF_DeathSync(p);CBaseEntity* e=NULL;while((e=UTIL_FindEntityByClassname(e,"vf_range_target"))!=NULL)((CVFRangeTarget*)e)->Send(p);}
void VF_RangeHear(CBasePlayer* p,float duration,float radius,float window){
 CBaseEntity* e=NULL;CVFRangeTarget* nearest=NULL;float best=radius;
 unsigned char* pas=ENGINE_SET_PAS((float*)&p->pev->origin);
 while((e=UTIL_FindEntityByClassname(e,"vf_range_target"))!=NULL){CVFRangeTarget* t=(CVFRangeTarget*)e;float d=(t->pev->origin-p->pev->origin).Length();if(t->IsAlive()&&d<best&&(!pas||ENGINE_CHECK_VISIBILITY(t->edict(),pas))){best=d;nearest=t;}}
 if(nearest){nearest->source=p;nearest->sourceLife=p->m_vfVoiceLife;nearest->replyAt=gpGlobals->time+duration+.8f;nearest->replyUntil=gpGlobals->time+duration+window;ALERT(at_console,"VFRange heard target=%d source=%d\n",nearest->slot,p->entindex());}
}
bool VF_RangeCommand(CBasePlayer* p,const char* cmd){
 if(strncmp(cmd,"vf_range_",9))return false;
 if(!strcmp(cmd,"vf_range_info")){
  CBaseEntity* e=NULL;while((e=UTIL_FindEntityByClassname(e,"vf_range_target"))!=NULL){CVFRangeTarget* t=(CVFRangeTarget*)e;char line[300];snprintf(line,sizeof(line),"VFRange info target=%d entity=%d skin=%d actor=%s health=%.1f alive=%d\n",t->slot,t->entindex(),t->skin,vfv::Actors[t->actor].id,t->pev->health,t->IsAlive());CLIENT_PRINTF(p->edict(),print_console,line);
   for(int i=0;i<vfs::Count;++i){snprintf(line,sizeof(line),"VFRange effect target=%d id=%s hits=%d active=%d remaining=%.2f\n",t->slot,vfs::effects[i].id,i<8?t->hits.count[i]:0,vfs::Active(t->status,i,gpGlobals->time),std::max(0.f,t->status.until[i]-gpGlobals->time));CLIENT_PRINTF(p->edict(),print_console,line);}}
  return true;
 }
 if(!VF_DeveloperAllowed()||strcmp(STRING(gpGlobals->mapname),"vf_range")||CMD_ARGC()<2)return true;
 int slot=atoi(CMD_ARGV(1));CBaseEntity* e=NULL;CVFRangeTarget* t=NULL;while((e=UTIL_FindEntityByClassname(e,"vf_range_target"))!=NULL)if(((CVFRangeTarget*)e)->slot==slot)t=(CVFRangeTarget*)e;
 if(!t)return true;
 if(!strcmp(cmd,"vf_range_voice")&&CMD_ARGC()==3){
  for(int i=0;i<vfv::ActorCount;++i)if(!strcmp(CMD_ARGV(2),vfv::Actors[i].id)){t->actor=i;vfv::Reset(t->voice);t->Send();return true;}
  return true;
 }
 if(!strcmp(cmd,"vf_range_effect")&&t->IsAlive()&&(CMD_ARGC()==3||CMD_ARGC()==4)){
  float duration=6;char* end=0;if(CMD_ARGC()==4){duration=strtof(CMD_ARGV(3),&end);if(!end||*end||!std::isfinite(duration)||duration<.2f||duration>30)return true;}
  for(int i=0;i<vfs::Count;++i)if(!strcmp(CMD_ARGV(2),vfs::effects[i].id)){
   vfs::Result r=vfs::Apply(t->status,i,gpGlobals->time,duration);if(r.entered)vfv::QueueEffect(t->voice,vfv::E_hydro+r.id,gpGlobals->time);t->Send();return true;
  }return true;
 }
 if(!strcmp(cmd,"vf_range_death")&&t->IsAlive()&&(CMD_ARGC()>=3&&CMD_ARGC()<=5)){
  int mask=VF_DeathMask(CMD_ARGV(2));int motion=CMD_ARGC()==5?VF_DeathMotion(CMD_ARGV(4)):0;if(mask<0||motion<0)return true;
  if(CMD_ARGC()>=4){int effect=-1;if(strcmp(CMD_ARGV(3),"standard")){for(int i=0;i<vfs::Count;++i)if(!strcmp(CMD_ARGV(3),vfs::effects[i].id))effect=i;if(effect<0)return true;}vfs::Reset(t->status);if(effect>=0)vfs::Apply(t->status,effect,gpGlobals->time,6);}
  t->deathMask=mask;t->deathMotion=motion;t->TakeDamage(p->pev,p->pev,t->pev->health+1,DMG_BULLET);return true;
 }
 if(!strcmp(cmd,"vf_range_kill")&&t->IsAlive()){
  t->TakeDamage(p->pev,p->pev,t->pev->health+1,DMG_BULLET);return true;
 }
 if(!strcmp(cmd,"vf_range_reset")){if(!t->IsAlive()){t->Spawn();return true;}t->Reset();t->pev->health=t->pev->max_health;t->Send();return true;}
 if(!strcmp(cmd,"vf_range_aim")){Vector pos=t->pev->origin+Vector(0,-160,0);UTIL_SetOrigin(p->pev,pos);p->pev->velocity=p->pev->basevelocity=g_vecZero;p->pev->v_angle=p->pev->angles=Vector(3.6f,90,0);p->pev->fixangle=1;return true;}
 if(!strcmp(cmd,"vf_range_fire")&&t->IsAlive()){
  Vector dest=t->pev->origin+Vector(0,0,15),src=dest+Vector(0,-140,0);int count=CMD_ARGC()>2?atoi(CMD_ARGV(2)):1;count=count<1?1:count>6?6:count;
  p->FireBulletsPlayer(count,src,Vector(0,1,0),g_vecZero,8192,BULLET_PLAYER_MP5,0,0,p->pev,p->random_seed);return true;
 }
 return true;
}
