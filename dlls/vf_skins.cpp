#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "vf_skins.h"
#include "vf_equipment.h"
#include "../game_shared/vf_appearance.h"
#include "../game_shared/vf_loadout.h"
static vf::AppearanceCatalog skins;
static int skinMessage;
static int stateMessage;
static cvar_t nativeModels={"vf_native_models","0",FCVAR_SERVER};
void VF_InitSkins(){
 CVAR_REGISTER(&nativeModels);int size=0;byte* marker=LOAD_FILE_FOR_ME("vf/native_engine.txt",&size);
 if(marker){FREE_FILE(marker);CVAR_SET_FLOAT("vf_native_models",1);}
}
static void Ensure(CBasePlayer* p){
 if(skins.valid&&((unsigned int)p->m_vfSkinHash!=skins.hash||!vf::ValidSkins(skins,p->m_vfSkins))){memset(p->m_vfSkins,0,sizeof(p->m_vfSkins));p->m_vfSkinHash=(int)skins.hash;}
 VF_EnsureEquipment(p);
}
static void State(CBasePlayer* p,CBasePlayer* recipient,bool active){
 if(!stateMessage)stateMessage=REG_USER_MSG("VFState",54);
 MESSAGE_BEGIN(recipient?MSG_ONE:MSG_ALL,stateMessage,NULL,recipient?recipient->edict():NULL);
 int resolved[5];memcpy(resolved,p->m_vfSkins,sizeof(resolved));
 if(p->m_vfAppearanceMode!=1)VF_ResolveEquipmentSkins(p,skins,resolved);
 WRITE_BYTE(vf::Protocol);WRITE_BYTE(p->entindex());WRITE_BYTE(active?1:0);WRITE_BYTE(p->m_vfAppearanceMode==1?1:0);WRITE_LONG(skins.hash);WRITE_LONG(p->m_vfCatalogHash);WRITE_LONG(p->m_vfWeaponStyleHash);
 for(int z=0;z<5;++z)WRITE_BYTE(resolved[z]);for(int s=0;s<vf::SlotCount;++s)WRITE_BYTE(p->m_vfItems[s]);for(int s=0;s<vf::WeaponStyleSlots;++s)WRITE_BYTE(p->m_vfWeaponStyles[s]);MESSAGE_END();
}
void VF_BroadcastPlayer(CBasePlayer* p,bool active){if(!nativeModels.value||!skins.valid)return;Ensure(p);State(p,NULL,active);}
void VF_SyncPlayer(CBasePlayer* p,bool spawn){
 if(!nativeModels.value||!skins.valid)return;Ensure(p);
 if(strcmp(STRING(p->pev->model),"models/vf_operator.mdl")){
  // SET_MODEL clears a Studio entity's collision bounds. Keep the SDK hull.
  SET_MODEL(p->edict(),"models/vf_operator.mdl");
  if(FBitSet(p->pev->flags,FL_DUCKING))UTIL_SetSize(p->pev,VEC_DUCK_HULL_MIN,VEC_DUCK_HULL_MAX);
  else UTIL_SetSize(p->pev,VEC_HULL_MIN,VEC_HULL_MAX);
 }
 if(spawn&&gpGlobals->maxClients>1&&!strcmp(STRING(gpGlobals->mapname),"vf_range")&&!p->HasNamedPlayerItem("weapon_9mmAR")){
  p->GiveNamedItem("weapon_9mmAR");p->GiveNamedItem("ammo_9mmbox");p->SelectItem("weapon_9mmAR");
 }
 for(int i=1;i<=gpGlobals->maxClients;++i){CBasePlayer* other=(CBasePlayer*)UTIL_PlayerByIndex(i);if(other&&!FBitSet(other->pev->flags,FL_DORMANT)&&other->IsPlayer()){Ensure(other);State(other,p,true);}}
 State(p,NULL,true);
}
void VF_PrecacheSkins() {
 int size=0;byte* text=LOAD_FILE_FOR_ME("vf/skins.txt",&size);
 vf::ParseAppearances((const char*)text,size>0?size:0,skins);if(text)FREE_FILE(text);
 if(!skins.valid){ALERT(at_console,"VF skin catalog unavailable\n");return;}
 PRECACHE_MODEL("models/vf_operator.mdl");
 if(!nativeModels.value)for(int i=0;i<skins.count;++i){char path[80];snprintf(path,sizeof(path),"models/vf_skins/%s.mdl",skins.entries[i].model);PRECACHE_MODEL((char*)STRING(ALLOC_STRING(path)));}
 ALERT(at_console,"VF skin catalog: %d sources, five zones\n",skins.count);
}
static void Send(CBasePlayer* p,int result) {
 if(!skinMessage)skinMessage=REG_USER_MSG("VFSkin",11);
 if(skins.valid&&!nativeModels.value)for(int z=0;z<5;++z){
  char target[40],model[80];snprintf(target,sizeof(target),"vf_skin_zone_%d",z);
  const vf::Appearance& appearance=skins.entries[p->m_vfSkins[z]];
  snprintf(model,sizeof(model),"models/vf_skins/%s.mdl",appearance.model);
  CBaseEntity* e=NULL;
  while((e=UTIL_FindEntityByTargetname(e,target))!=NULL){SET_MODEL(e->edict(),model);e->pev->body=1<<z;e->pev->skin=z==0?0:appearance.skin;e->pev->solid=SOLID_NOT;}
 }
 MESSAGE_BEGIN(MSG_ONE,skinMessage,NULL,p->edict());WRITE_BYTE(1);WRITE_BYTE(result);WRITE_LONG(skins.hash);
 for(int i=0;i<5;++i)WRITE_BYTE(p->m_vfSkins[i]);MESSAGE_END();
 ALERT(at_console,"VFSkin: result=%d ids=%d,%d,%d,%d,%d\n",result,p->m_vfSkins[0],p->m_vfSkins[1],p->m_vfSkins[2],p->m_vfSkins[3],p->m_vfSkins[4]);
 if(!result)VF_BroadcastPlayer(p);
}
bool VF_SkinCommand(CBasePlayer* p,const char* cmd) {
 if(!strcmp(cmd,"vf_appearance_mode")){
  Ensure(p);unsigned int mode;
  if(CMD_ARGC()==2&&vf::ParseUnsigned(CMD_ARGV(1),mode)&&mode<=1)p->m_vfAppearanceMode=(int)mode;
  VF_SyncPlayer(p);Send(p,0);ALERT(at_console,"VFAppearance mode=%d player=%d\n",p->m_vfAppearanceMode,p->entindex());return true;
 }
 if(!strcmp(cmd,"vf_body_info")){
  char line[200];snprintf(line,sizeof(line),"VFBody player=%d mins=%.0f,%.0f,%.0f maxs=%.0f,%.0f,%.0f rifle=%d\n",p->entindex(),p->pev->mins.x,p->pev->mins.y,p->pev->mins.z,p->pev->maxs.x,p->pev->maxs.y,p->pev->maxs.z,p->HasNamedPlayerItem("weapon_9mmAR")?1:0);
  CLIENT_PRINTF(p->edict(),print_console,line);return true;
 }
 if(!strcmp(cmd,"vf_skin_inspect")){
  for(int z=0;z<5;++z){char target[40];snprintf(target,sizeof(target),"vf_skin_zone_%d",z);CBaseEntity* e=UTIL_FindEntityByTargetname(NULL,target);if(e)ALERT(at_console,"VFSkin entity: zone=%d body=%d model=%s\n",z,e->pev->body,STRING(e->pev->model));}
  return true;
 }
 if(!strcmp(cmd,"vf_peer_pose")&&!strcmp(STRING(gpGlobals->mapname),"vf_range")&&CVAR_GET_FLOAT("sv_cheats")){
  bool second=p->entindex()==2;UTIL_SetOrigin(p->pev,Vector(-355,second?-65:-265,36));p->pev->velocity=g_vecZero;
  p->pev->angles=p->pev->v_angle=Vector(0,second?270:90,0);p->pev->fixangle=1;return true;
 }
 if(!strcmp(cmd,"vf_skin_camera")&&!strcmp(STRING(gpGlobals->mapname),"vf_range")&&(gpGlobals->maxClients==1||CVAR_GET_FLOAT("sv_cheats"))){
  UTIL_SetOrigin(p->pev,Vector(-355,-265,36));p->pev->angles=p->pev->v_angle=Vector(4,55,0);p->pev->fixangle=1;return true;
 }
 bool request=!strcmp(cmd,"vf_skin_request");if(!request&&strcmp(cmd,"vf_skin_apply"))return false;
 if(!skins.valid){Send(p,1);return true;}
 if((unsigned int)p->m_vfSkinHash!=skins.hash||!vf::ValidSkins(skins,p->m_vfSkins)){memset(p->m_vfSkins,0,sizeof(p->m_vfSkins));p->m_vfSkinHash=(int)skins.hash;}
 if(request){VF_SyncPlayer(p);Send(p,0);return true;}
 if(p->m_vfAppearanceMode!=1){Send(p,4);return true;}
 unsigned int hash;int next[5];
 if(CMD_ARGC()!=7||!vf::ParseUnsigned(CMD_ARGV(1),hash)||hash!=skins.hash){Send(p,2);return true;}
 for(int i=0;i<5;++i){unsigned int value;if(!vf::ParseUnsigned(CMD_ARGV(i+2),value)||value>=(unsigned int)skins.count){Send(p,3);return true;}next[i]=value;}
 memcpy(p->m_vfSkins,next,sizeof(next));Send(p,0);return true;
}
