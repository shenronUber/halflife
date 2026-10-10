#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "vf_status.h"
#include "vf_voice.h"
#include "vf_equipment.h"
#include "vf_range.h"
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cmath>
namespace {
int message=0;
void Send(CBasePlayer* p,CBasePlayer* to=0){
 if(!message)return;
 MESSAGE_BEGIN(to?MSG_ONE:MSG_ALL,message,NULL,to?to->edict():NULL);
 WRITE_BYTE(ENTINDEX(p->edict()));WRITE_BYTE(p->m_vfStatusDeveloper?1:0);
 for(int i=0;i<vfs::Count;++i){float left=p->m_vfStatus.until[i]-gpGlobals->time;WRITE_SHORT(left>0?int(left*100+.5f):0);}
 MESSAGE_END();
}
int Find(const char* id){for(int i=0;i<vfs::Count;++i)if(!strcmp(id,vfs::effects[i].id))return i;return -1;}
int Finish(CBasePlayer* p,vfs::Result r,float seconds,bool cue){
 if(r.id<0)return -1;Send(p);
 ALERT(at_console,"VFStatus apply: player=%d effect=%s entered=%d duration=%.2f\n",ENTINDEX(p->edict()),vfs::effects[r.id].id,r.entered,seconds);
 if(r.entered&&cue)VF_VoiceEffect(p,r.id);
 return r.id;
}
bool Allowed(CBasePlayer* p){return VF_DeveloperAllowed()&&p->m_vfStatusDeveloper&&p->IsAlive()&&!p->IsObserver();}
}
void VF_StatusPrecache(){if(!message)message=REG_USER_MSG("VFStatus",2+vfs::Count*2);}
void VF_StatusReset(CBasePlayer* p){vfs::Reset(p->m_vfStatus);vfp::Reset(p->m_vfProc);p->m_vfStatusDeveloper=false;Send(p);}
void VF_StatusClear(CBasePlayer* p){vfs::Reset(p->m_vfStatus);vfp::Reset(p->m_vfProc);p->m_vfVoiceState.pendingEvent=-1;Send(p);ALERT(at_console,"VFStatus clear: player=%d\n",ENTINDEX(p->edict()));}
void VF_StatusThink(CBasePlayer* p){
 vfp::Expire(p->m_vfProc,gpGlobals->time);
 if(p->m_vfStatusDeveloper&&!VF_DeveloperAllowed()){p->m_vfStatusDeveloper=false;VF_StatusClear(p);}
 if(vfs::Expire(p->m_vfStatus,gpGlobals->time)){Send(p);ALERT(at_console,"VFStatus expired: player=%d\n",ENTINDEX(p->edict()));}
}
void VF_StatusSync(CBasePlayer* to){
 VF_RangeSync(to);
 for(int i=1;i<=gpGlobals->maxClients;++i){CBaseEntity* e=UTIL_PlayerByIndex(i);if(e&&e->IsPlayer())Send(static_cast<CBasePlayer*>(e),to);}
}
int VF_ApplyPlayerEffect(CBasePlayer* p,int effect,float seconds,bool cue){
 if(!p||!p->IsAlive()||p->IsObserver()||effect<0||effect>=vfs::Count||!std::isfinite(seconds)||seconds<=0||seconds>30)return -1;
 return Finish(p,vfs::Apply(p->m_vfStatus,effect,gpGlobals->time,seconds),seconds,cue);
}
bool VF_StatusCommand(CBasePlayer* p,const char* command){
 if(strncmp(command,"vf_status_",10))return false;
 if(!strcmp(command,"vf_status_info")){
  char text[160];snprintf(text,sizeof(text),"VFStatus info: player=%d developer=%d\n",ENTINDEX(p->edict()),p->m_vfStatusDeveloper);CLIENT_PRINTF(p->edict(),print_console,text);
  for(int i=0;i<vfs::Count;++i)if(vfs::Active(p->m_vfStatus,i,gpGlobals->time)){snprintf(text,sizeof(text),"VFStatus active: effect=%s remaining=%.2f\n",vfs::effects[i].id,p->m_vfStatus.until[i]-gpGlobals->time);CLIENT_PRINTF(p->edict(),print_console,text);}
  return true;
 }
 if(!VF_DeveloperAllowed()){CLIENT_PRINTF(p->edict(),print_console,"VFStatus rejected: developer command requires local play or sv_cheats.\n");return true;}
 if(!strcmp(command,"vf_status_dev")&&CMD_ARGC()==2){
  if(strcmp(CMD_ARGV(1),"0")&&strcmp(CMD_ARGV(1),"1"))return true;
  p->m_vfStatusDeveloper=!strcmp(CMD_ARGV(1),"1");VF_StatusClear(p);return true;
 }
 if(!Allowed(p)){CLIENT_PRINTF(p->edict(),print_console,"VFStatus rejected: enable developer effect testing on a living player.\n");return true;}
 if(!strcmp(command,"vf_status_clear")){VF_StatusClear(p);return true;}
 if(!strcmp(command,"vf_status_reset")){
  VF_StatusClear(p);vfv::Reset(p->m_vfVoiceState);p->m_vfVoiceSpawnAt=0;return true;
 }
 bool pair=!strcmp(command,"vf_status_pair");
 if(pair||!strcmp(command,"vf_status_apply")){
  int minimum=pair?3:2;
  if(CMD_ARGC()!=minimum&&CMD_ARGC()!=minimum+1)return true;
  int a=Find(CMD_ARGV(1)),b=pair?Find(CMD_ARGV(2)):-1;float seconds=6;
  if(CMD_ARGC()==minimum+1){char* end=0;seconds=strtof(CMD_ARGV(minimum),&end);if(!end||*end||!std::isfinite(seconds)||seconds<.2f||seconds>30)return true;}
  if(a<0||(pair&&(b<0||vfs::Reaction(a,b)<0))){CLIENT_PRINTF(p->edict(),print_console,"VFStatus rejected: unknown effect or incompatible pair.\n");return true;}
  if(pair)Finish(p,vfs::ApplyPair(p->m_vfStatus,a,b,gpGlobals->time,seconds),seconds,true);
  else VF_ApplyPlayerEffect(p,a,seconds);
  return true;
 }
 return true;
}

void VF_ElementalPlayerHit(CBasePlayer* p,int effect){
 if(!p||!p->IsAlive()||p->IsObserver()||(p->pev->flags&FL_GODMODE))return;
 if(vfp::Hit(p->m_vfProc,effect,gpGlobals->time)){vfs::Result r=vfs::ApplyPrimary(p->m_vfStatus,effect,gpGlobals->time,vfp::Duration);Finish(p,r,vfp::Duration,true);ALERT(at_console,"VFProc player=%d effect=%s hits=6 window=3 duration=6\n",p->entindex(),vfs::effects[effect].id);}
}
