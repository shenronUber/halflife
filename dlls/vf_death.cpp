#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "monsters.h"
#include "weapons.h"
#include "vf_death.h"
#include "vf_equipment.h"
#include "vf_skins.h"
#include "../game_shared/vf_death_policy.h"
#include "../game_shared/vf_death_visual.h"
#include "../game_shared/vf_wound_catalog.h"
#include "../game_shared/vf_death_motion.h"
#include "../game_shared/vf_death_atlas.h"
#include "../game_shared/vf_death_tracks.h"
#include "../game_shared/vf_death_sfx_catalog.h"
#include <cmath>
#include "../game_shared/vf_fragment_geometry.h"
#include <cstring>
#include <cstdio>
#include <algorithm>
#undef max
#undef min
namespace {
int message=0,fragmentMessage=0,soundMessage=0;
cvar_t deathVolume={"vf_death_sfx_volume","1",FCVAR_SERVER};
cvar_t dismemberVolume={"vf_dismember_sfx_volume","1",FCVAR_SERVER};unsigned int fragmentSerial=0;const float lifetime=15;
struct Snapshot{bool valid,grounded;int mask,effect,motion,skins[5];Vector impact;};Snapshot snapshots[33];int pending[33],pendingMotion[33],lastMotion[17];
struct FatalTrace{int hitgroup,bits;float time,total,weights[5];Vector direction;entvars_t* attacker;bool applied;};FatalTrace fatalTraces[33];
}
class CVFDeathCorpse:public CBaseAnimating {
public:
 int missing,effect,skins[5];float until,started,nextSync;
 void Spawn(){pev->classname=MAKE_STRING("vf_death_corpse");pev->solid=SOLID_NOT;pev->movetype=MOVETYPE_TOSS;pev->takedamage=DAMAGE_NO;pev->deadflag=DEAD_DEAD;pev->gravity=1;SetThink(&CVFDeathCorpse::Animate);pev->nextthink=gpGlobals->time+.04f;}
 void Send(CBasePlayer* to=0){
  if(!message)return;MESSAGE_BEGIN(to?MSG_ONE:MSG_ALL,message,NULL,to?to->edict():NULL);
  WRITE_SHORT(entindex());WRITE_BYTE(missing);WRITE_BYTE(effect+1);for(int z=0;z<5;++z)WRITE_BYTE(skins[z]);
  WRITE_SHORT((int)((gpGlobals->time-started)*100));WRITE_SHORT((int)(std::max(0.f,until-gpGlobals->time)*100));MESSAGE_END();
 }
 void EXPORT Animate(){
  if(gpGlobals->time>=until){Send();UTIL_Remove(this);return;}
  if(!m_fSequenceFinished)StudioFrameAdvance();else {pev->frame=255;pev->framerate=0;if(FBitSet(pev->flags,FL_ONGROUND)){pev->movetype=MOVETYPE_NONE;pev->velocity=g_vecZero;}}
  if(gpGlobals->time>=nextSync){Send();nextSync=gpGlobals->time+1;}
  pev->nextthink=gpGlobals->time+.04f;
 }
 int Save(CSave& save){if(!CBaseAnimating::Save(save))return 0;return save.WriteFields("VF_CORPSE",this,m_SaveData,ARRAYSIZE(m_SaveData));}
 int Restore(CRestore& restore){if(!CBaseAnimating::Restore(restore))return 0;int ok=restore.ReadFields("VF_CORPSE",this,m_SaveData,ARRAYSIZE(m_SaveData));nextSync=0;SetThink(&CVFDeathCorpse::Animate);pev->nextthink=gpGlobals->time+.04f;return ok;}
 static TYPEDESCRIPTION m_SaveData[6];
};
LINK_ENTITY_TO_CLASS(vf_death_corpse,CVFDeathCorpse);
TYPEDESCRIPTION CVFDeathCorpse::m_SaveData[]={DEFINE_FIELD(CVFDeathCorpse,missing,FIELD_INTEGER),DEFINE_FIELD(CVFDeathCorpse,effect,FIELD_INTEGER),DEFINE_ARRAY(CVFDeathCorpse,skins,FIELD_INTEGER,5),DEFINE_FIELD(CVFDeathCorpse,until,FIELD_TIME),DEFINE_FIELD(CVFDeathCorpse,started,FIELD_TIME),DEFINE_FIELD(CVFDeathCorpse,nextSync,FIELD_TIME)};
// Genuine bouncing Studio entities. The effect metadata follows their lifetime,
// independently of the victim's status, corpse animation or subsequent respawn.
class CVFDeathFragment:public CGib {
public:
 int effect,serial;float started,until,nextSync;
 void Configure(int id){pev->solid=SOLID_NOT;pev->flags&=~FL_ONGROUND;pev->groundentity=NULL;UTIL_SetSize(pev,Vector(-2,-2,-2),Vector(2,2,2));effect=id;serial=(++fragmentSerial)%65535+1;started=gpGlobals->time;until=started+12;nextSync=started+.4f;SetThink(&CVFDeathFragment::Animate);pev->nextthink=started+.1f;Send();
  ALERT(at_console,"VFFragment spawn entity=%d body=%d effect=%d whole=%d velocity=%.1f,%.1f,%.1f skin=%d\n",entindex(),pev->body,effect,pev->body>=15,pev->velocity.x,pev->velocity.y,pev->velocity.z,pev->skin);
 }
 void Send(CBasePlayer* to=0){if(!fragmentMessage)return;MESSAGE_BEGIN(to?MSG_ONE:MSG_ALL,fragmentMessage,NULL,to?to->edict():NULL);WRITE_SHORT(entindex());WRITE_BYTE(pev->body);WRITE_BYTE(effect+1);WRITE_SHORT((int)((gpGlobals->time-started)*100));WRITE_SHORT((int)(std::max(0.f,until-gpGlobals->time)*100));WRITE_SHORT(serial);MESSAGE_END();}
 void End(){until=gpGlobals->time;Send();UTIL_Remove(this);}
 void EXPORT Animate(){if(gpGlobals->time>=until||!IsInWorld()){End();return;}if(FBitSet(pev->flags,FL_ONGROUND)&&pev->movetype==MOVETYPE_BOUNCE){
  if(pev->body>=15){const vfdeath::FragmentRest& pose=vfdeath::FragmentPoses[pev->body-15];pev->angles.x=pose.pitch;pev->angles.z=0;UTIL_SetOrigin(pev,pev->origin+Vector(0,0,pose.floorOffset-2));}
  pev->movetype=MOVETYPE_NONE;pev->velocity=pev->avelocity=g_vecZero;TraceResult trace;UTIL_TraceLine(pev->origin+Vector(0,0,8),pev->origin-Vector(0,0,24),ignore_monsters,edict(),&trace);if(trace.flFraction<1)UTIL_BloodDecalTrace(&trace,BLOOD_COLOR_RED);
 }if(gpGlobals->time>=nextSync&&gpGlobals->time-started<2.2f){Send();nextSync=gpGlobals->time+.4f;}pev->nextthink=gpGlobals->time+.1f;}
};
LINK_ENTITY_TO_CLASS(vf_death_fragment,CVFDeathFragment);
namespace {
// Native sound events, never played by corpse sync or fragment metadata.
// A voice (victim/CHAN_VOICE), cause (victim/CHAN_BODY), and detachment
// (corpse/CHAN_ITEM) coexist without replacing each other.
void DeathAudio(CBaseEntity* emitter,int layer,int effect,int mask=0){
 const vfds::Profile& profile=vfds::For(effect);
 const char* sample=layer?((mask&vfdeath::Head)?profile.head:profile.dismemberment):profile.death;if(!sample)return;
 float volume=layer?dismemberVolume.value:deathVolume.value;
 if(!std::isfinite(volume)||volume<=0)return;volume=std::min(1.f,volume);
 int channel=layer?CHAN_ITEM:CHAN_BODY;
 // One detachment salvo per event rather than one sound for every small gib.
 int pitch=!layer?PITCH_NORM:mask==vfdeath::Head?104:(mask==vfdeath::LeftLeg||mask==vfdeath::RightLeg)?96:PITCH_NORM;
 EMIT_SOUND_DYN(emitter->edict(),channel,sample,volume,ATTN_NORM,0,pitch);
 if(soundMessage){MESSAGE_BEGIN(MSG_PAS_R,soundMessage,(float*)&emitter->pev->origin);WRITE_SHORT(emitter->entindex());WRITE_BYTE(layer);WRITE_BYTE(effect+1);WRITE_BYTE(pitch);MESSAGE_END();}
 ALERT(at_console,"VFDeathSfx play entity=%d layer=%s effect=%s channel=%d pitch=%d volume=%.2f sample=%s\n",emitter->entindex(),layer?"dismemberment":"death",profile.id,channel,pitch,volume,sample);
}
void TrimFragments(){
 CBaseEntity* e=NULL;CBaseEntity* oldest=NULL;int count=0;
 while((e=UTIL_FindEntityByClassname(e,"gib"))!=NULL){
  if(FBitSet(e->pev->flags,FL_KILLME)||strcmp(STRING(e->pev->model),vfdeath::GibModel))continue;
  ++count;if(!oldest||e->pev->fuser4<oldest->pev->fuser4)oldest=e;
 }
 if(count>=72&&oldest)((CVFDeathFragment*)oldest)->End();
}
int SelectMotion(CBaseAnimating* corpse,const Snapshot& s){
 const vfdeath::Profile* profile=vfdeath::ProfileFor(s.effect);
 const int* pool=profile?profile->motions:(s.mask&vfdeath::Head?vfdeath::HeadMotions:vfdeath::StandardMotions);
 int count=profile?profile->count:3,candidates[3],size=0,key=s.effect+1;
 float yaw=corpse->pev->angles.y*.01745329252f;
 float x=cosf(yaw)*s.impact.x+sinf(yaw)*s.impact.y,y=-sinf(yaw)*s.impact.x+cosf(yaw)*s.impact.y;
 for(int i=0;i<count;++i){
  int motion=pool[i];bool compatible=true;
  if(vfmotion::Motions[motion].directional&&x*x+y*y>.01f){
   int sequence=corpse->LookupSequence(vfmotion::Motions[motion].sequence);float start[3],end[3];
   if(vfmotion::Centre(sequence,0,start)&&vfmotion::Centre(sequence,255,end)){
    float dx=end[0]-start[0],dy=end[1]-start[1];
    compatible=dx*x+dy*y>=-.25f*sqrtf((dx*dx+dy*dy)*(x*x+y*y));
   }
  }
  if(compatible)candidates[size++]=motion;
 }
 // Each profile has two grounded collapses as well as its signature gesture.
 // Those remain available for every impact direction and anatomical loss.
 if(!size){for(int i=0;i<count;++i)candidates[size++]=pool[i];}
 if(size>1&&key>=0&&key<17)for(int i=0;i<size;++i)if(candidates[i]==lastMotion[key]){candidates[i]=candidates[--size];break;}
 int selected=candidates[RANDOM_LONG(0,size-1)];if(key>=0&&key<17)lastMotion[key]=selected;return selected;
}
void Corpse(CBaseMonster* victim,const Snapshot& s){
 CBaseEntity* e=NULL;CVFDeathCorpse* oldest=NULL;int count=0;
 while((e=UTIL_FindEntityByClassname(e,"vf_death_corpse"))!=NULL){if(FBitSet(e->pev->flags,FL_KILLME))continue;CVFDeathCorpse* c=(CVFDeathCorpse*)e;++count;if(!oldest||c->started<oldest->started)oldest=c;}
 if(count>=12&&oldest){oldest->until=gpGlobals->time;oldest->Send();UTIL_Remove(oldest);}
 CVFDeathCorpse* c=GetClassPtr((CVFDeathCorpse*)NULL);SET_MODEL(c->edict(),vfdeath::Model);
 c->missing=s.mask;c->effect=s.effect;memcpy(c->skins,s.skins,sizeof(c->skins));c->started=gpGlobals->time;c->until=gpGlobals->time+lifetime;c->nextSync=gpGlobals->time+1;
 c->pev->controller[0]=c->pev->controller[1]=c->pev->controller[2]=c->pev->controller[3]=127;c->pev->blending[0]=127;
 c->pev->angles=Vector(0,victim->pev->angles.y,0);c->pev->skin=s.skins[1];c->pev->body=vfdeath::Body(s.mask);c->pev->velocity=s.grounded?g_vecZero:victim->pev->velocity;
 UTIL_SetSize(c->pev,Vector(-16,-16,-36),Vector(16,16,36));// Preserve foot height when the victim used the crouching hull.
 Vector origin=victim->pev->origin;origin.z+=36+victim->pev->mins.z;UTIL_SetOrigin(c->pev,origin);
 int motion=s.motion;if(!motion)motion=SelectMotion(c,s);
 const char* sequence=(s.mask&vfdeath::Head)?"headshot":(s.mask&(vfdeath::LeftLeg|vfdeath::RightLeg))?"die_forwards":"die_simple";
 if(motion>=2&&motion<vfmotion::Count){sequence=vfmotion::Motions[motion].sequence;c->pev->sequence=c->LookupSequence(sequence);}
 else if(!s.mask){int desired=c->LookupActivity(victim->GetDeathActivity());if(desired>=0){c->pev->sequence=desired;sequence="historical_activity";}else c->pev->sequence=c->LookupSequence(sequence);}else c->pev->sequence=c->LookupSequence(sequence);
 if(c->pev->sequence<0)c->pev->sequence=c->LookupSequence("die_simple");c->pev->frame=0;c->ResetSequenceInfo();c->Spawn();c->Send();
 const int bits[]={1,2,4,8,16},bones[]={13,16,23,3,6};
 for(int i=0;i<5;++i)if(s.mask&bits[i]){
  Vector point,angles;victim->GetBonePosition(bones[i],point,angles);
  // The client emits a bounded ballistic burst at the fresh whole fragment.
  // Legacy BloodStream used a fixed vertical ray and a broad palette ramp.
  // Keep the recognizable member and three physical debris pieces, each
  // with an independent trajectory, clothing finish and elemental trail.
  for(int piece=0;piece<vfdeath::FragmentsPerRegion;++piece){
   TrimFragments();CVFDeathFragment* g=GetClassPtr((CVFDeathFragment*)NULL);g->Spawn(vfdeath::GibModel);g->pev->fuser4=gpGlobals->time;
   g->pev->body=piece?i*3+piece-1:15+i;g->pev->skin=vfdeath::FragmentSkin(i,s.skins);g->m_bloodColor=BLOOD_COLOR_RED;g->m_lifeTime=10;
   g->pev->angles=Vector(RANDOM_FLOAT(-90,90),RANDOM_FLOAT(0,360),RANDOM_FLOAT(-90,90));
   float force=(s.effect==7||s.effect==11)?1.3f:1.f;
   g->pev->velocity=Vector(RANDOM_FLOAT(-130,130),RANDOM_FLOAT(-130,130),RANDOM_FLOAT(100,230))*force;
   g->pev->avelocity=Vector(RANDOM_FLOAT(-350,350),RANDOM_FLOAT(-350,350),RANDOM_FLOAT(-350,350));
   UTIL_SetOrigin(g->pev,point+Vector(RANDOM_FLOAT(-3,3),RANDOM_FLOAT(-3,3),0));g->Configure(s.effect);
  }
 }
 if(s.mask)DeathAudio(c,1,s.effect,s.mask);
 ALERT(at_console,"VFDeathVisual corpse=%d victim=%d mask=%d effect=%d sequence=%s lifetime=15 origin_z=%.1f victim_mins_z=%.1f motion=%d impact=%.3f,%.3f grounded=%d origin_xy=%.2f,%.2f yaw=%.2f velocity_xy=%.2f,%.2f\n",c->entindex(),victim->entindex(),s.mask,s.effect,sequence,c->pev->origin.z,victim->pev->mins.z,motion,s.impact.x,s.impact.y,s.grounded,c->pev->origin.x,c->pev->origin.y,c->pev->angles.y,c->pev->velocity.x,c->pev->velocity.y);
}
}
void VF_DeathRegister(){CVAR_REGISTER(&deathVolume);CVAR_REGISTER(&dismemberVolume);}
void VF_DeathPrecache(){if(!soundMessage)soundMessage=REG_USER_MSG("VFDeathSfx",5);for(int i=0;i<vfds::ProfileCount;++i){const vfds::Profile& p=vfds::Profiles[i];if(p.death)PRECACHE_SOUND((char*)p.death);PRECACHE_SOUND((char*)p.dismemberment);PRECACHE_SOUND((char*)p.head);}if(!message)message=REG_USER_MSG("VFCorpse",13);if(!fragmentMessage)fragmentMessage=REG_USER_MSG("VFFragment",10);PRECACHE_MODEL((char*)vfdeath::Model);PRECACHE_MODEL((char*)vfdeath::GibModel);PRECACHE_MODEL("sprites/lgtning.spr");PRECACHE_SOUND("common/null.wav");memset(snapshots,0,sizeof(snapshots));for(int i=0;i<17;++i)lastMotion[i]=-1;memset(pendingMotion,0,sizeof(pendingMotion));for(int i=0;i<33;++i){pending[i]=-1;fatalTraces[i].time=-1;}}
void VF_DeathSync(CBasePlayer* p){CBaseEntity* e=NULL;while((e=UTIL_FindEntityByClassname(e,"vf_death_corpse"))!=NULL)((CVFDeathCorpse*)e)->Send(p);e=NULL;while((e=UTIL_FindEntityByClassname(e,"gib"))!=NULL)if(!FBitSet(e->pev->flags,FL_KILLME)&&!strcmp(STRING(e->pev->model),vfdeath::GibModel))((CVFDeathFragment*)e)->Send(p);}
void VF_DeathDiscardTrace(CBasePlayer* p){int i=p->entindex();if(i>0&&i<=32){fatalTraces[i]=FatalTrace();fatalTraces[i].time=-1;}}
void VF_DeathSpawn(CBasePlayer* p){int i=p->entindex();if(i>0&&i<=32){snapshots[i].valid=false;snapshots[i].mask=0;pending[i]=-1;pendingMotion[i]=0;VF_DeathDiscardTrace(p);memset(p->m_vfRegionDamage,0,sizeof(p->m_vfRegionDamage));}}
void VF_DeathTrace(CBasePlayer* p,int hitgroup,const Vector& direction,float damage,entvars_t* attacker,int bits){
 int i=p->entindex();if(i<1||i>32||!std::isfinite(damage)||damage<=0)return;FatalTrace& t=fatalTraces[i];
 if(t.time!=gpGlobals->time||t.attacker!=attacker||t.applied){t=FatalTrace();t.time=gpGlobals->time;t.attacker=attacker;}
 t.hitgroup=hitgroup;t.direction=direction;t.bits|=bits;t.total+=damage;
 int region=vfdeath::DamageRegion(hitgroup);if(region>=0)t.weights[region]+=damage;
}
void VF_DeathDamage(CBasePlayer* p,entvars_t* attacker,float healthDamage,int bits){
 static_assert(vfdeath::GibPolicyMask==(DMG_NEVERGIB|DMG_ALWAYSGIB),"SDK gib flags changed");
 int i=p->entindex();if(i<1||i>32)return;FatalTrace& t=fatalTraces[i];
 if(t.time!=gpGlobals->time||t.attacker!=attacker||t.applied||!vfdeath::SameDamageType(t.bits,bits)||
    !p->pev->takedamage||(p->pev->flags&FL_GODMODE)||!std::isfinite(healthDamage)||healthDamage<=0){VF_DeathDiscardTrace(p);return;}
 vfdeath::AccumulateDamage(p->m_vfRegionDamage,t.weights,t.total,healthDamage);t.applied=true;
}
bool VF_DeathCompatible(CBasePlayer* p){return strstr(STRING(p->pev->model),"persona_rig")||strstr(STRING(p->pev->model),"r01_tp");}
bool VF_DeathHeadMissing(CBasePlayer* p){int i=p->entindex();return i>0&&i<=32&&(snapshots[i].mask&vfdeath::Head)!=0;}
void VF_DeathCapture(CBasePlayer* p,bool fullGib,const Vector& impact){if(p->m_vfVoiceDeathSpoken)return;int i=p->entindex();if(i<1||i>32)return;Snapshot& s=snapshots[i];s.valid=VF_DeathCompatible(p);
const bool localized=fatalTraces[i].time==gpGlobals->time&&fatalTraces[i].applied;
int group=localized?fatalTraces[i].hitgroup:HITGROUP_GENERIC;
s.impact=localized?fatalTraces[i].direction:impact;s.grounded=FBitSet(p->pev->flags,FL_ONGROUND)!=0;
s.mask=pending[i]>=0?pending[i]:vfdeath::AutomaticMask(group,p->m_vfRegionDamage,p->pev->max_health);s.motion=pendingMotion[i];
int region=vfdeath::DamageRegion(group);
ALERT(at_console,"VFDeath anatomy victim=%d hitgroup=%d mask=%d override=%d regional_damage=%.3f maximum_health=%.3f\n",i,group,s.mask,pending[i]>=0,region>=0?p->m_vfRegionDamage[region]:0,p->pev->max_health);
pending[i]=-1;pendingMotion[i]=0;fatalTraces[i].time=-1;s.effect=vfd::Causes[vfd::CauseFor(p->m_vfStatus,gpGlobals->time)].effect;VF_DeathPlayerSkins(p,s.skins);if(!(s.mask&vfdeath::Head))DeathAudio(p,0,s.effect);}
void VF_DeathPlayer(CBasePlayer* p){int i=p->entindex();if(i<1||i>32||!snapshots[i].valid)return;Corpse(p,snapshots[i]);snapshots[i].valid=false;p->pev->effects|=EF_NODRAW;}
void VF_DeathTarget(CBaseMonster* p,int skin,const vfs::State& state,int mask,int motion,const Vector& impact){Snapshot s={};s.grounded=FBitSet(p->pev->flags,FL_ONGROUND)||p->pev->movetype==MOVETYPE_NONE;s.impact=impact;s.motion=motion;s.mask=mask<0?0:mask&31;s.effect=vfd::Causes[vfd::CauseFor(state,gpGlobals->time)].effect;for(int z=0;z<5;++z)s.skins[z]=skin;if(!(s.mask&vfdeath::Head))DeathAudio(p,0,s.effect);Corpse(p,s);}
bool VF_DeathGibSound(CBaseMonster* p){if(!p->IsPlayer())return false;int i=p->entindex();if(i<1||i>32)return false;DeathAudio(p,1,snapshots[i].effect,31);return true;}
int VF_DeathMask(const char* name){const char* names[]={"none","head","left_arm","right_arm","left_leg","right_leg","all"};const int masks[]={0,1,2,4,8,16,31};for(int i=0;i<7;++i)if(!strcmp(name,names[i]))return masks[i];return -1;}
int VF_DeathMotion(const char* id){for(int i=0;i<vfmotion::Count;++i)if(!strcmp(id,vfmotion::Motions[i].id))return i;return -1;}
bool VF_DeathCommand(CBasePlayer* p,const char* cmd){
 if(strcmp(cmd,"vf_death_test")&&strcmp(cmd,"vf_death_clear")&&strcmp(cmd,"vf_death_inspect")&&strcmp(cmd,"vf_death_view"))return false;if(!VF_DeveloperAllowed())return true;
 if(!strcmp(cmd,"vf_death_clear")){CBaseEntity* e=NULL;while((e=UTIL_FindEntityByClassname(e,"vf_death_corpse"))!=NULL){((CVFDeathCorpse*)e)->until=gpGlobals->time;((CVFDeathCorpse*)e)->Send();UTIL_Remove(e);}e=NULL;while((e=UTIL_FindEntityByClassname(e,"gib"))!=NULL)if(!strcmp(STRING(e->pev->model),vfdeath::GibModel))((CVFDeathFragment*)e)->End();return true;}
 if(!strcmp(cmd,"vf_death_view")){
  if(strcmp(STRING(gpGlobals->mapname),"vf_range")||!p->IsAlive())return true;
  CBaseEntity* e=NULL;CVFDeathCorpse* c=NULL;while((e=UTIL_FindEntityByClassname(e,"vf_death_corpse"))!=NULL){CVFDeathCorpse* next=(CVFDeathCorpse*)e;if(!FBitSet(next->pev->flags,FL_KILLME)&&(!c||next->started>c->started))c=next;}
  if(!c)return true;if(CMD_ARGC()==2&&!strcmp(CMD_ARGV(1),"scene")){CBaseEntity* g=NULL;while((g=UTIL_FindEntityByClassname(g,"gib"))!=NULL)if(!FBitSet(g->pev->flags,FL_KILLME)&&!strcmp(STRING(g->pev->model),vfdeath::GibModel)&&fabs(g->pev->fuser4-c->started)<.02f)UTIL_SetOrigin(g->pev,g->pev->origin+Vector(96,-96,0));}UTIL_SetOrigin(c->pev,c->pev->origin+Vector(96,-96,0));Vector center=c->pev->origin+Vector(0,0,-16),eye=c->pev->origin+Vector(100,-155,53);UTIL_SetOrigin(p->pev,eye-p->pev->view_ofs);p->pev->velocity=g_vecZero;Vector angle=UTIL_VecToAngles(center-eye);angle.x=-angle.x;p->pev->angles=p->pev->v_angle=angle;p->pev->fixangle=1;ALERT(at_console,"VFDeath view corpse=%d\n",c->entindex());return true;
 }
 if(!strcmp(cmd,"vf_death_inspect")){
  if(strcmp(STRING(gpGlobals->mapname),"vf_range")||CMD_ARGC()!=2||!p->IsAlive())return true;
  int mask=VF_DeathMask(CMD_ARGV(1)),index=-1;const int regions[]={1,2,4,8,16};for(int i=0;i<5;++i)if(mask==regions[i])index=i;if(index<0)return true;
  CBaseEntity* e=NULL;CVFDeathCorpse* c=NULL;while((e=UTIL_FindEntityByClassname(e,"vf_death_corpse"))!=NULL){CVFDeathCorpse* next=(CVFDeathCorpse*)e;if(!FBitSet(next->pev->flags,FL_KILLME)&&(next->missing&mask)&&(!c||next->started>c->started))c=next;}
  if(!c)return true;UTIL_SetOrigin(c->pev,c->pev->origin+Vector(96,-96,0));c->pev->sequence=c->LookupSequence("look_idle");c->pev->frame=0;c->ResetSequenceInfo();c->pev->framerate=0;c->pev->movetype=MOVETYPE_NONE;c->pev->velocity=g_vecZero;
  Vector center,angle;const vfwound::Cut& cut=vfwound::Cuts[index];c->GetBonePosition(cut.bone,center,angle);UTIL_MakeVectors(angle);center=center+gpGlobals->v_forward*cut.offset[0]-gpGlobals->v_right*cut.offset[1]+gpGlobals->v_up*cut.offset[2];
  Vector normal=gpGlobals->v_forward*cut.normal[0]-gpGlobals->v_right*cut.normal[1]+gpGlobals->v_up*cut.normal[2];
  float distance=index>=3?22.f:42.f;Vector eye=center+normal*distance+Vector(0,-15,0);
  UTIL_SetOrigin(p->pev,eye-p->pev->view_ofs);p->pev->velocity=g_vecZero;angle=UTIL_VecToAngles(center-eye);angle.x=-angle.x;p->pev->angles=p->pev->v_angle=angle;p->pev->fixangle=1;
  c->Send();ALERT(at_console,"VFWound inspect region=%s bone=%d center=%.2f,%.2f,%.2f\n",CMD_ARGV(1),cut.bone,center.x,center.y,center.z);return true;
 }
 if(!p->IsAlive()||CMD_ARGC()<2||CMD_ARGC()>4)return true;int mask=VF_DeathMask(CMD_ARGV(1));if(mask<0)return true;
 int motion=CMD_ARGC()==4?VF_DeathMotion(CMD_ARGV(3)):0;if(motion<0)return true;
 if(CMD_ARGC()>=3){int id=-1;if(strcmp(CMD_ARGV(2),"standard")){for(int e=0;e<vfs::Count;++e)if(!strcmp(CMD_ARGV(2),vfs::effects[e].id))id=e;if(id<0)return true;}vfs::Reset(p->m_vfStatus);if(id>=0)vfs::Apply(p->m_vfStatus,id,gpGlobals->time,6);}
 pending[p->entindex()]=mask;pendingMotion[p->entindex()]=motion;p->pev->flags&=~FL_GODMODE;p->pev->armorvalue=0;p->TakeDamage(p->pev,p->pev,p->pev->health+1,DMG_GENERIC|DMG_NEVERGIB);return true;
}

