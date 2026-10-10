#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "weapons.h"
#include "vf_skins.h"
#include "vf_equipment.h"
#include "../game_shared/vf_appearance.h"
#include "../game_shared/vf_loadout.h"
#include "../game_shared/vf_legacy_save.h"
#include "../game_shared/vf_model_contract.h"
static vf::AppearanceCatalog skins;
static int skinMessage;
static int stateMessage;
static int legacyRigIndex,fittedRigIndex,referenceRigIndex[3];
static cvar_t nativeModels={"vf_native_models","0",FCVAR_SERVER};
void VF_InitSkins(){
 CVAR_REGISTER(&nativeModels);int size=0;byte* marker=LOAD_FILE_FOR_ME("vf/native_engine.txt",&size);
 if(marker){FREE_FILE(marker);CVAR_SET_FLOAT("vf_native_models",1);}
}
static void Ensure(CBasePlayer* p){
 if(!VF_DeveloperAllowed())p->m_vfAppearanceMode=0;
 if(skins.valid){
  if((unsigned int)p->m_vfSkinHash!=skins.hash||!vf::ValidSkins(skins,p->m_vfSkins)){
   const char* keys[vf::SkinZones];
   for(int z=0;z<vf::SkinZones;++z)keys[z]=(p->m_vfKeyFlags&4)?STRING(p->m_vfSkinKeys[z]):vf::LegacySkinKey((unsigned int)p->m_vfSkinHash,p->m_vfSkins[z]);
   vf::RestoreAppearances(skins,keys,p->m_vfSkins,vf::SkinZones);p->m_vfSkinHash=(int)skins.hash;
  }
  for(int z=0;z<vf::SkinZones;++z){const char* key=skins.entries[p->m_vfSkins[z]].key;if(strcmp(STRING(p->m_vfSkinKeys[z]),key))p->m_vfSkinKeys[z]=ALLOC_STRING(key);}
  p->m_vfKeyFlags|=4;
 }
 VF_EnsureEquipment(p);
}
static void State(CBasePlayer* p,CBasePlayer* recipient,bool active){
 if(!stateMessage)stateMessage=REG_USER_MSG("VFState",vf::StateMessageSize);
 MESSAGE_BEGIN(recipient?MSG_ONE:MSG_ALL,stateMessage,NULL,recipient?recipient->edict():NULL);
 int resolved[5];memcpy(resolved,p->m_vfSkins,sizeof(resolved));
 if(p->m_vfAppearanceMode!=1)VF_ResolveEquipmentSkins(p,skins,resolved);
 WRITE_BYTE(vf::Protocol);WRITE_BYTE(p->entindex());WRITE_BYTE(active?1:0);WRITE_BYTE(p->m_vfAppearanceMode==1?1:0);WRITE_LONG(skins.hash);WRITE_LONG(p->m_vfCatalogHash);WRITE_LONG(p->m_vfWeaponStyleHash);
 for(int z=0;z<5;++z)WRITE_BYTE(resolved[z]);for(int s=0;s<vf::SlotCount;++s)WRITE_SHORT(p->m_vfItems[s]);for(int s=0;s<vf::WeaponStyleSlots;++s)WRITE_BYTE(p->m_vfWeaponStyles[s]);MESSAGE_END();
}
void VF_PreparePlayerSave(CBasePlayer* p){Ensure(p);}
void VF_DeathPlayerSkins(CBasePlayer* p,int* out){
 Ensure(p);int resolved[5];memcpy(resolved,p->m_vfSkins,sizeof(resolved));
 if(p->m_vfAppearanceMode!=1)VF_ResolveEquipmentSkins(p,skins,resolved);
 for(int z=0;z<5;++z){int i=resolved[z];out[z]=skins.valid&&i>=0&&i<skins.count&&!strcmp(skins.entries[i].model,"persona_scout")?skins.entries[i].skin:0;}
}
bool VF_ApplyPlayerModel(CBasePlayer* p){
 if(!nativeModels.value||!skins.valid)return false;
 int resolved[5];memcpy(resolved,p->m_vfSkins,sizeof(resolved));
 if(p->m_vfAppearanceMode!=1&&!VF_ResolveEquipmentSkins(p,skins,resolved))return false;
 const char* model=vf::OperatorRig(skins,resolved);
 int index=!strcmp(model,"models/vf_operator.mdl")?legacyRigIndex:fittedRigIndex;
 int mount=VF_ReferenceMount(p);
 if(index==fittedRigIndex && mount>=0 && mount<3 && referenceRigIndex[mount] &&
    p->m_pActiveItem && p->m_pActiveItem->m_iId==WEAPON_MP5){model=vf::Carrier(mount).thirdPerson;index=referenceRigIndex[mount];}
 if(!index)return false;
 if(strcmp(STRING(p->pev->model),model)||p->pev->modelindex!=index){
  SET_MODEL(p->edict(),model);
  // Original sequences 0..76 are compatible across the carriers. A holster
  // during a new reload must not leave an out-of-range sequence on the old rig.
  if(index==fittedRigIndex && p->pev->sequence>=vf::PersonaSequenceCount){p->pev->sequence=0;p->pev->frame=0;p->ResetSequenceInfo();}
  if(FBitSet(p->pev->flags,FL_DUCKING))UTIL_SetSize(p->pev,VEC_DUCK_HULL_MIN,VEC_DUCK_HULL_MAX);
  else UTIL_SetSize(p->pev,VEC_HULL_MIN,VEC_HULL_MAX);
 }
 return true;
}
void VF_BroadcastPlayer(CBasePlayer* p,bool active){if(!nativeModels.value||!skins.valid)return;Ensure(p);if(active)VF_ApplyPlayerModel(p);State(p,NULL,active);}
void VF_SyncPlayer(CBasePlayer* p,bool spawn){
 if(!nativeModels.value||!skins.valid)return;Ensure(p);
 VF_ApplyPlayerModel(p);
 if(spawn&&gpGlobals->maxClients>1&&(!strcmp(STRING(gpGlobals->mapname),"vf_range")||!strcmp(STRING(gpGlobals->mapname),"vf_fx_range"))&&!p->HasNamedPlayerItem("weapon_9mmAR")){
  p->GiveNamedItem("weapon_9mmAR");p->GiveNamedItem("ammo_9mmbox");p->SelectItem("weapon_9mmAR");
 }
 for(int i=1;i<=gpGlobals->maxClients;++i){CBasePlayer* other=(CBasePlayer*)UTIL_PlayerByIndex(i);if(other&&!FBitSet(other->pev->flags,FL_DORMANT)&&other->IsPlayer()){Ensure(other);State(other,p,true);VF_SendWeaponFX(other,p);}}
 State(p,NULL,true);VF_SendWeaponFX(p);
}
void VF_PrecacheSkins() {
 VF_PrecacheWeaponFX();
 int size=0;byte* text=LOAD_FILE_FOR_ME("vf/skins.txt",&size);
 vf::ParseAppearances((const char*)text,size>0?size:0,skins);if(text)FREE_FILE(text);
 if(!skins.valid){ALERT(at_console,"VF skin catalog unavailable\n");return;}
 legacyRigIndex=PRECACHE_MODEL("models/vf_operator.mdl");fittedRigIndex=0;
 if(nativeModels.value)for(int i=0;i<skins.count;++i)if(!strcmp(skins.entries[i].model,"persona_scout")){fittedRigIndex=PRECACHE_MODEL("models/vf_skins/persona_rig.mdl");break;}
 for(int mount=0;mount<3;++mount){
  referenceRigIndex[mount]=0;
  if(fittedRigIndex){int bytes=0;byte* data=LOAD_FILE_FOR_ME((char*)vf::Carrier(mount).thirdPerson,&bytes);
   if(data){FREE_FILE(data);referenceRigIndex[mount]=PRECACHE_MODEL((char*)vf::Carrier(mount).thirdPerson);}}
 }
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
  if(CMD_ARGC()==2&&vf::ParseUnsigned(CMD_ARGV(1),mode)&&mode<=1){
   if(mode==1&&!VF_DeveloperAllowed()){Send(p,4);return true;}
   p->m_vfAppearanceMode=(int)mode;
  }
  VF_SyncPlayer(p);Send(p,0);ALERT(at_console,"VFAppearance mode=%d player=%d\n",p->m_vfAppearanceMode,p->entindex());return true;
 }
 if(!strcmp(cmd,"vf_model_info")){
  char line[160];snprintf(line,sizeof(line),"VFModel player=%d model=%s developer=%d keys=%d\n",p->entindex(),STRING(p->pev->model),p->m_vfDeveloper,p->m_vfKeyFlags);
  CLIENT_PRINTF(p->edict(),print_console,line);return true;
 }
 if(!strcmp(cmd,"vf_reload_info")){
  CBasePlayerWeapon* weapon=p->m_pActiveItem?(CBasePlayerWeapon*)p->m_pActiveItem->GetWeaponPtr():NULL;
  char line[240];snprintf(line,sizeof(line),"VFReload player=%d sequence=%d frame=%.1f gait=%d active=%d clip=%d model=%s\n",p->entindex(),p->pev->sequence,p->pev->frame,p->pev->gaitsequence,weapon?weapon->m_fInReload:0,weapon?weapon->m_iClip:-1,STRING(p->pev->model));
  CLIENT_PRINTF(p->edict(),print_console,line);return true;
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
 Ensure(p);
 if(request){VF_SyncPlayer(p);Send(p,0);return true;}
 if(p->m_vfAppearanceMode!=1||!VF_DeveloperAllowed()){Send(p,4);return true;}
 unsigned int hash;int next[5];
 if(CMD_ARGC()!=7||!vf::ParseUnsigned(CMD_ARGV(1),hash)||hash!=skins.hash){Send(p,2);return true;}
 for(int i=0;i<5;++i){unsigned int value;if(!vf::ParseUnsigned(CMD_ARGV(i+2),value)||value>=(unsigned int)skins.count){Send(p,3);return true;}next[i]=value;}
 memcpy(p->m_vfSkins,next,sizeof(next));Ensure(p);Send(p,0);return true;
}
