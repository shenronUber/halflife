// Dedicated action state; included by client.cpp, without new project targets.
#include "vf_weapon_melee.h"
#include "../game_shared/vf_weapon_melee.h"
#include "../game_shared/vf_model_contract.h"
namespace {
struct MeleeServerState {bool active,impacted,crouch;unsigned int life;float start,cooldown;int mount,hits,lastEntity;float lastDamage;};
MeleeServerState meleeServer[33];int meleeMessage=0,meleeModels[3]={};
const char* meleeBody[3]={"models/vf_melee/r01_tp.mdl","models/vf_melee/r01_tp_side.mdl","models/vf_melee/r01_tp_top.mdl"};
void MeleeSend(CBasePlayer* p,CBasePlayer* to=0){
 MeleeServerState& s=meleeServer[p->entindex()];
 MESSAGE_BEGIN(to?MSG_ONE:MSG_ALL,meleeMessage,NULL,to?to->edict():NULL);
 WRITE_BYTE(p->entindex());WRITE_BYTE(s.active?1:0);WRITE_SHORT(s.active?1+(int)(max(0.f,gpGlobals->time-s.start)*1000):0);
 WRITE_BYTE(s.mount);WRITE_BYTE(s.crouch?1:0);MESSAGE_END();
}
void MeleeStop(CBasePlayer* p){
 MeleeServerState& s=meleeServer[p->entindex()];bool was=s.active;s.active=false;
 // A dead player already selected a death sequence from this preserved bank.
 // Leave it running; Spawn restores the ordinary carrier through skin sync.
 if(p->IsAlive()&&strstr(STRING(p->pev->model),"models/vf_melee/")){
  VF_ApplyPlayerModel(p);p->pev->sequence=0;p->pev->frame=0;p->pev->framerate=1;p->ResetSequenceInfo();
 }
 if(was)MeleeSend(p);
}
bool MeleeValid(CBasePlayer* p,MeleeServerState& s){
 return s.active&&p->IsAlive()&&s.life==p->m_vfVoiceLife&&p->m_pActiveItem&&p->m_pActiveItem->m_iId==WEAPON_MP5&&
  VF_ReferenceMount(p)==s.mount&&!VF_TR_Phase(p->pev->iuser4)&&!p->pev->iuser1&&!FBitSet(p->pev->flags,FL_FROZEN)&&vf::MeleeClockValid(gpGlobals->time-s.start);
}
void MeleeStrike(CBasePlayer* p,MeleeServerState& s){
 s.impacted=true;UTIL_MakeVectors(p->pev->v_angle);Vector start=p->GetGunPosition(),end=start+gpGlobals->v_forward*vf::MeleeRange;
 TraceResult tr;UTIL_TraceLine(start,end,dont_ignore_monsters,p->edict(),&tr);
 if(tr.flFraction>=1)UTIL_TraceHull(start,end,dont_ignore_monsters,head_hull,p->edict(),&tr);
 s.lastEntity=0;s.lastDamage=0;
 if(tr.flFraction<1){
  CBaseEntity* target=CBaseEntity::Instance(tr.pHit);s.lastEntity=target?target->entindex():0;
  bool flesh=target&&target->pev->takedamage!=DAMAGE_NO&&(target->IsPlayer()||FBitSet(target->pev->flags,FL_MONSTER))&&target->Classify()!=CLASS_MACHINE;
  EMIT_SOUND_DYN(p->edict(),CHAN_WEAPON,flesh?"weapons/cbar_hitbod1.wav":"weapons/cbar_hit1.wav",1,ATTN_NORM,0,100);
  if(target&&target->pev->takedamage!=DAMAGE_NO){
   float before=target->pev->health;ClearMultiDamage();target->TraceAttack(p->pev,vf::MeleeDamage,gpGlobals->v_forward,&tr,DMG_CLUB);
   ApplyMultiDamage(p->pev,p->pev);s.lastDamage=max(0.f,before-target->pev->health);++s.hits;
  }
  p->pev->punchangle.x-=.75f;
 }
 ALERT(at_console,"VFMelee impact: player=%d entity=%d damage=%.1f hits=%d age=%.3f fraction=%.3f\n",p->entindex(),s.lastEntity,s.lastDamage,s.hits,gpGlobals->time-s.start,tr.flFraction);
}
}
void VF_MeleeForget(int index){if(index>0&&index<33)meleeServer[index]=MeleeServerState();}
void VF_MeleePrecache(){
 memset(meleeServer,0,sizeof(meleeServer));if(!meleeMessage)meleeMessage=REG_USER_MSG("VFMelee",vf::MeleeMessageSize);
 for(int i=0;i<3;++i){int bytes=0;byte* data=LOAD_FILE_FOR_ME((char*)meleeBody[i],&bytes);meleeModels[i]=0;
  if(data){FREE_FILE(data);meleeModels[i]=PRECACHE_MODEL((char*)meleeBody[i]);}}
 PRECACHE_SOUND("weapons/cbar_miss1.wav");PRECACHE_SOUND("weapons/cbar_hit1.wav");PRECACHE_SOUND("weapons/cbar_hitbod1.wav");
}
void VF_MeleeSync(CBasePlayer* recipient){
 for(int i=1;i<=gpGlobals->maxClients&&i<=32;++i){CBasePlayer* p=(CBasePlayer*)UTIL_PlayerByIndex(i);
  if(p&&!FBitSet(p->pev->flags,FL_DORMANT))MeleeSend(p,recipient);}
}
bool VF_MeleeCommand(CBasePlayer* p,const char* command){
 if(strcmp(command,"vf_melee")&&strcmp(command,"vf_melee_cancel")&&strcmp(command,"vf_melee_info")&&strcmp(command,"vf_melee_place"))return false;
 if(!p||p->entindex()<1||p->entindex()>32)return true;MeleeServerState& s=meleeServer[p->entindex()];
 if(!strcmp(command,"vf_melee_place")){
  if(!VF_DeveloperAllowed()||CMD_ARGC()!=6)return true;float values[5];
  for(int i=0;i<5;++i){values[i]=(float)atof(CMD_ARGV(i+1));if(!std::isfinite(values[i])||fabs(values[i])>32768)return true;}
  Vector position(values[0],values[1],values[2]);TraceResult trace;UTIL_TraceHull(position,position,dont_ignore_monsters,human_hull,p->edict(),&trace);
  if(trace.fStartSolid||trace.fAllSolid)return true;
  UTIL_SetOrigin(p->pev,position);p->pev->velocity=p->pev->basevelocity=g_vecZero;p->pev->punchangle=g_vecZero;
  p->pev->v_angle=p->pev->angles=Vector(values[4],values[3],0);p->pev->fixangle=1;return true;
 }
 if(!strcmp(command,"vf_melee_info")){
  char text[240];CBasePlayerWeapon* w=p->m_pActiveItem?(CBasePlayerWeapon*)p->m_pActiveItem:NULL;
  snprintf(text,sizeof(text),"VFMelee server: active=%d age=%.3f impact=%d hits=%d entity=%d damage=%.1f clip=%d model=%s\n",s.active,s.active?gpGlobals->time-s.start:0,s.impacted,s.hits,s.lastEntity,s.lastDamage,w?w->m_iClip:-1,STRING(p->pev->model));
  CLIENT_PRINTF(p->edict(),print_console,text);return true;
 }
 if(!strcmp(command,"vf_melee_cancel")){MeleeStop(p);return true;}
 if(CMD_ARGC()!=1||!VF_EnsureEquipment(p))return true;
 CBasePlayerWeapon* w=p->m_pActiveItem?(CBasePlayerWeapon*)p->m_pActiveItem:NULL;int mount=VF_ReferenceMount(p);
 if(!vf::MeleeReady(p->IsAlive(),w?w->m_iId:0,w&&w->m_fInReload,p->m_flNextAttack>UTIL_WeaponTimeBase(),VF_TR_Phase(p->pev->iuser4))||
    p->pev->iuser1||FBitSet(p->pev->flags,FL_FROZEN)||mount<0||mount>2||!meleeModels[mount]||!VF_DeathCompatible(p)||s.active||gpGlobals->time<s.cooldown)return true;
 s.active=true;s.impacted=false;s.start=gpGlobals->time;s.cooldown=s.start+vf::MeleeDuration;s.life=p->m_vfVoiceLife;s.mount=mount;s.crouch=FBitSet(p->pev->flags,FL_DUCKING)!=0;
 p->m_flNextAttack=UTIL_WeaponTimeBase()+vf::MeleeDuration;w->m_flNextPrimaryAttack=w->m_flNextSecondaryAttack=w->m_flTimeWeaponIdle=UTIL_WeaponTimeBase()+vf::MeleeDuration;
 EMIT_SOUND_DYN(p->edict(),CHAN_WEAPON,"weapons/cbar_miss1.wav",.75f,ATTN_NORM,0,100);
 VF_MeleePose(p);MeleeSend(p);ALERT(at_console,"VFMelee start: player=%d mount=%d crouch=%d\n",p->entindex(),mount,s.crouch);return true;
}
bool VF_MeleePose(CBasePlayer* p){
 if(!p||p->entindex()<1||p->entindex()>32)return false;MeleeServerState& s=meleeServer[p->entindex()];
 if(!MeleeValid(p,s)){if(s.active||strstr(STRING(p->pev->model),"models/vf_melee/"))MeleeStop(p);return false;}
 if(strcmp(STRING(p->pev->model),meleeBody[s.mount])){Vector lo=p->pev->mins,hi=p->pev->maxs;SET_MODEL(p->edict(),meleeBody[s.mount]);UTIL_SetSize(p->pev,lo,hi);}
 int sequence=p->LookupSequence(FBitSet(p->pev->flags,FL_DUCKING)?"vf_melee_crouch":"vf_melee");if(sequence<0){MeleeStop(p);return false;}
 if(p->pev->sequence!=sequence){p->pev->sequence=sequence;p->ResetSequenceInfo();}
 p->pev->frame=min(255.99f,max(0.f,(gpGlobals->time-s.start)*256/vf::MeleeDuration));p->pev->framerate=0;p->pev->animtime=gpGlobals->time;
 float speed=p->pev->velocity.Length2D();const char* gait=FBitSet(p->pev->flags,FL_DUCKING)?(speed>5?"crawl":"crouch_idle"):(speed>220?"run2":speed>5?"walk2handed":"idle");
 p->pev->gaitsequence=max(0,p->LookupSequence(gait));return true;
}
void VF_MeleeThink(CBasePlayer* p){
 if(!VF_MeleePose(p))return;MeleeServerState& s=meleeServer[p->entindex()];
 bool crouch=FBitSet(p->pev->flags,FL_DUCKING)!=0;if(crouch!=s.crouch){s.crouch=crouch;MeleeSend(p);}
 if(vf::MeleeImpactDue(gpGlobals->time-s.start,s.impacted))MeleeStrike(p,s);
}
