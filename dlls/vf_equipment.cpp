#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "vf_equipment.h"
#include "vf_skins.h"
#include "../game_shared/vf_loadout.h"
#include "../game_shared/vf_appearance.h"
#include "../game_shared/vf_legacy_save.h"
#include <string.h>
#include "../game_shared/vf_weapon_fx_catalog.h"
static vf::Catalog catalog;
static vf::AppearanceCatalog weaponStyles;
static int equipmentMessage,shotMessage;
bool VF_DeveloperAllowed() { return gpGlobals->maxClients==1||CVAR_GET_FLOAT("sv_cheats")!=0; }
void VF_RegisterMessages() {
    if(!equipmentMessage) equipmentMessage=REG_USER_MSG("VFBuild",vf::BuildMessageSize);
    if(!shotMessage)shotMessage=REG_USER_MSG("VFShot",2);
}
static void LoadCatalog() {
    int size=0;
    byte* bytes=LOAD_FILE_FOR_ME("vf/equipment.txt",&size);
    vf::ParseCatalog((const char*)bytes,size>0?size:0,catalog);
    if(bytes) FREE_FILE(bytes);
    size=0;bytes=LOAD_FILE_FOR_ME("vf/r01_styles.txt",&size);
    vf::ParseAppearances((const char*)bytes,size>0?size:0,weaponStyles);
    if(bytes) FREE_FILE(bytes);
    if(catalog.valid&&weaponStyles.valid)for(int i=1;i<catalog.count;++i)if(catalog.items[i].weaponStyle[0]&&vf::FindAppearance(weaponStyles,catalog.items[i].weaponStyle)<0){
        catalog.valid=false;strcpy(catalog.error,"Finition d objet absente du catalogue");break;
    }
    if(!catalog.valid) ALERT(at_console,"VF catalogue: %s\n",catalog.error);
}
static void StoreKey(string_t& target,const char* key) {
    if(strcmp(STRING(target),key))target=ALLOC_STRING(key);
}
static void StoreKeys(CBasePlayer* p) {
    for(int s=0;s<vf::SlotCount;++s)StoreKey(p->m_vfItemKeys[s],catalog.items[p->m_vfItems[s]].id);
    for(int s=0;s<vf::WeaponStyleSlots;++s)StoreKey(p->m_vfStyleKeys[s],weaponStyles.entries[p->m_vfWeaponStyles[s]].key);
    p->m_vfKeyFlags|=3;
}
static void Send(CBasePlayer* p,vf::Result result) {
    CBaseEntity* mannequin=NULL;
    while((mannequin=UTIL_FindEntityByTargetname(mannequin,"vf_operator_preview"))!=NULL)
        mannequin->pev->body=vf::OperatorBody(catalog,p->m_vfItems);
    VF_RegisterMessages();
    MESSAGE_BEGIN(MSG_ONE,equipmentMessage,NULL,p->edict());
    WRITE_BYTE(vf::Protocol); WRITE_BYTE(result); WRITE_LONG(catalog.fingerprint); WRITE_LONG(weaponStyles.hash);
    for(int s=0;s<vf::SlotCount;++s) WRITE_SHORT(p->m_vfItems[s]);
    for(int s=0;s<vf::WeaponStyleSlots;++s) WRITE_BYTE(p->m_vfWeaponStyles[s]);
    MESSAGE_END();
    if(result==vf::Accepted)VF_BroadcastPlayer(p);
}
unsigned int VF_EnsureEquipment(CBasePlayer* p) {
    LoadCatalog();if(!catalog.valid||!weaponStyles.valid)return 0;
    int totals[vf::BudgetCount];
    const unsigned int oldHash=(unsigned int)p->m_vfCatalogHash;
    if(oldHash!=catalog.fingerprint||vf::Evaluate(catalog,p->m_vfItems,totals)!=vf::Accepted){
        const char* keys[vf::SlotCount];
        for(int s=0;s<vf::SlotCount;++s)keys[s]=(p->m_vfKeyFlags&1)?STRING(p->m_vfItemKeys[s]):vf::LegacyItemKey(oldHash,p->m_vfItems[s]);
        vf::RestoreEquipment(catalog,keys,p->m_vfItems);
    }
    // Old experimental saves have no explicit mode flag. Preserve their valid
    // historical objects when importing the known 0.14.0 index dictionary.
    if(!(p->m_vfKeyFlags&1)&&oldHash==vf::LegacyItemHash&&VF_DeveloperAllowed())
        for(int s=0;s<vf::SlotCount;++s)if(p->m_vfItems[s]&&!vf::GameplayItem(catalog.items[p->m_vfItems[s]])&&strncmp(catalog.items[p->m_vfItems[s]].id,"r01_",4))p->m_vfDeveloper=1;
    if(p->m_vfDeveloper&&!VF_DeveloperAllowed())p->m_vfDeveloper=0;
    if((unsigned int)p->m_vfWeaponStyleHash!=weaponStyles.hash||!vf::ValidWeaponStyles(weaponStyles,p->m_vfWeaponStyles)){
        const char* keys[vf::WeaponStyleSlots];
        for(int s=0;s<vf::WeaponStyleSlots;++s)keys[s]=(p->m_vfKeyFlags&2)?STRING(p->m_vfStyleKeys[s]):vf::LegacyStyleKey((unsigned int)p->m_vfWeaponStyleHash,p->m_vfWeaponStyles[s]);
        vf::RestoreAppearances(weaponStyles,keys,p->m_vfWeaponStyles,vf::WeaponStyleSlots);
        p->m_vfWeaponStyleHash=(int)weaponStyles.hash;
    }
    if(!p->m_vfDeveloper)vf::PromoteGameplayEquipment(catalog,weaponStyles,p->m_vfItems,p->m_vfWeaponStyles);
    vf::BindWeaponStyles(catalog,weaponStyles,p->m_vfItems,p->m_vfWeaponStyles);
    vf::Result valid=p->m_vfDeveloper?vf::EvaluateExperiment(catalog,p->m_vfItems,totals):vf::EvaluateGameplay(catalog,p->m_vfItems,totals);
    if(valid!=vf::Accepted){
        if(p->m_vfDeveloper){vf::GameplayDefaults(catalog,p->m_vfItems);p->m_vfDeveloper=0;}
        else vf::NormalizeGameplay(catalog,p->m_vfItems);
    }
    p->m_vfCatalogHash=(int)catalog.fingerprint;
    StoreKeys(p);
    return catalog.fingerprint;
}
const vf::Item* VF_EquippedItem(CBasePlayer* p,int slot) {
    if(!p||slot<0||slot>=vf::SlotCount)return NULL;
    if((!catalog.valid||(unsigned int)p->m_vfCatalogHash!=catalog.fingerprint)&&!VF_EnsureEquipment(p))return NULL;
    int index=p->m_vfItems[slot];
    return index>0&&index<catalog.count&&catalog.items[index].slot==slot?&catalog.items[index]:NULL;
}
bool VF_EquipmentCommand(CBasePlayer* p,const char* command) {
    if(!strcmp(command,"vf_fx_camera")){
        if(!VF_DeveloperAllowed()||strcmp(STRING(gpGlobals->mapname),"vf_fx_range")||CMD_ARGC()!=2)return true;
        const char* names[]={"concrete","metal","wood","flesh","sky","brush","side"};
        const int ys[]={-260,-80,100,340,-260,237,-130};
        for(int i=0;i<7;++i)if(!strcmp(CMD_ARGV(1),names[i])){
            UTIL_SetOrigin(p->pev,Vector(i==6?32:0,ys[i],36));p->pev->velocity=p->pev->basevelocity=g_vecZero;
            p->pev->angles=p->pev->v_angle=Vector(i==4?-85:i==6?3:0,i==6?270:0,0);p->pev->fixangle=1;
            ALERT(at_console,"VFShot camera: %s\n",names[i]);break;
        }
        return true;
    }
    if(!strcmp(command,"vf_fx_profile")){
        int code=-1;
        if(CMD_ARGC()==2&&!strcmp(CMD_ARGV(1),"auto"))code=0;
        for(int i=0;CMD_ARGC()==2&&i<vfshot::Count;++i)if(!strcmp(CMD_ARGV(1),vfshot::profiles[i].id))code=i+1;
        if(code<0||!VF_DeveloperAllowed()){
            VF_SendWeaponFX(p);
            CLIENT_PRINTF(p->edict(),print_console,"Weapon FX profile rejected: developer access or profile invalid.\n");
            ALERT(at_console,"VFShot rejected: player=%d\n",p->entindex());return true;
        }
        p->m_vfShotFX=code;VF_SendWeaponFX(p);
        ALERT(at_console,"VFShot accepted: player=%d code=%d\n",p->entindex(),code);return true;
    }
    if(!strcmp(command,"vf_gameplay")){
        p->m_vfShotFX=0;VF_SendWeaponFX(p);
        if(!VF_EnsureEquipment(p)){Send(p,vf::BadCatalog);return true;}
        vf::PromoteGameplayEquipment(catalog,weaponStyles,p->m_vfItems,p->m_vfWeaponStyles);p->m_vfAppearanceMode=0;p->m_vfDeveloper=0;StoreKeys(p);
        Send(p,vf::Accepted);VF_SyncPlayer(p);
        ALERT(at_console,"VFGameplay: active player=%d head=%s receiver=%s\n",p->entindex(),catalog.items[p->m_vfItems[0]].id,catalog.items[p->m_vfItems[9]].id);return true;
    }
    const bool request=!strcmp(command,"vf_request"),experimental=!strcmp(command,"vf_apply_dev");
    if(!request&&!experimental&&strcmp(command,"vf_apply"))return false;
    if(!VF_EnsureEquipment(p)){Send(p,vf::BadCatalog);return true;}
    if(request){Send(p,vf::Accepted);return true;}
    if(experimental&&!VF_DeveloperAllowed()){Send(p,vf::BadRequest);return true;}
    unsigned int hash;
    if((CMD_ARGC()!=vf::SlotCount+2&&CMD_ARGC()!=vf::SlotCount+3+vf::WeaponStyleSlots)||!vf::ParseUnsigned(CMD_ARGV(1),hash)){Send(p,vf::BadRequest);return true;}
    if(hash!=catalog.fingerprint){Send(p,vf::BadCatalog);return true;}
    int candidate[vf::SlotCount];
    for(int s=0;s<vf::SlotCount;++s){
        unsigned int value;
        if(!vf::ParseUnsigned(CMD_ARGV(s+2),value)||value>=(unsigned int)catalog.count){Send(p,vf::BadItem);return true;}
        candidate[s]=value;
    }
    int styles[vf::WeaponStyleSlots];memcpy(styles,p->m_vfWeaponStyles,sizeof(styles));
    if(CMD_ARGC()==vf::SlotCount+3+vf::WeaponStyleSlots){
        unsigned int styleHash;
        if(!vf::ParseUnsigned(CMD_ARGV(vf::SlotCount+2),styleHash)||styleHash!=weaponStyles.hash){Send(p,vf::BadCatalog);return true;}
        for(int s=0;s<vf::WeaponStyleSlots;++s){
            unsigned int value;if(!vf::ParseUnsigned(CMD_ARGV(vf::SlotCount+3+s),value)||value>=(unsigned int)weaponStyles.count){Send(p,vf::BadItem);return true;}
            styles[s]=(int)value;
        }
        if(!vf::ValidWeaponStyles(weaponStyles,styles)){Send(p,vf::BadItem);return true;}
    }
    int totals[vf::BudgetCount];
    vf::Result result=experimental?vf::EvaluateExperiment(catalog,candidate,totals):vf::EvaluateGameplay(catalog,candidate,totals);
    if(result==vf::Accepted&&!vf::BoundWeaponStyles(catalog,weaponStyles,candidate,styles))result=vf::BadItem;
    if(result==vf::Accepted){
        memcpy(p->m_vfItems,candidate,sizeof(candidate));memcpy(p->m_vfWeaponStyles,styles,sizeof(styles));
        p->m_vfDeveloper=experimental?1:0;StoreKeys(p);
    }
    ALERT(at_console,"VF equipment: result=%d TED=%d IP=%d HS=%d OI=%d SIG=%d BIO=%d\n",result,totals[0],totals[1],totals[2],totals[3],totals[4],totals[5]);
    if(result==vf::Accepted)ALERT(at_console,"VFR01 styles accepted: player=%d first=%d optic=%d feed=%d\n",p->entindex(),styles[0],styles[7],styles[3]);
    Send(p,result);return true;
}
bool VF_ResolveEquipmentSkins(CBasePlayer* p,const vf::AppearanceCatalog& skins,int* out){return vf::EquipmentSkins(catalog,p->m_vfItems,skins,out);}

int VF_ReferenceMount(CBasePlayer* p){
 int id=p->m_vfItems[9];
 if(!catalog.valid||id<=0||id>=catalog.count||strncmp(catalog.items[id].id,"r01_receiver_",13))return -1;
 return vf::ReceiverMount(catalog.items[id]);
}

void VF_PrecacheWeaponFX(){
 const char* kinds[]={"muzzle","impact","particle","smoke","core"};
 const char* surfaces[]={"hard","metal","wood","flesh"};
 for(int p=0;p<vfshot::Count;++p){
  char path[96];
  for(int k=0;k<5;++k){snprintf(path,sizeof(path),"sprites/vf_weaponfx/%s_%s.spr",vfshot::profiles[p].id,kinds[k]);PRECACHE_MODEL((char*)STRING(ALLOC_STRING(path)));}
  snprintf(path,sizeof(path),"vf_weaponfx/%s_fire.wav",vfshot::profiles[p].id);PRECACHE_SOUND((char*)STRING(ALLOC_STRING(path)));
  for(int s=0;s<4;++s){snprintf(path,sizeof(path),"vf_weaponfx/%s_hit_%s.wav",vfshot::profiles[p].id,surfaces[s]);PRECACHE_SOUND((char*)STRING(ALLOC_STRING(path)));}
 }
}
void VF_SendWeaponFX(CBasePlayer* p,CBasePlayer* recipient){
 if(!VF_DeveloperAllowed()||p->m_vfShotFX<0||p->m_vfShotFX>vfshot::Count)p->m_vfShotFX=0;
 VF_RegisterMessages();MESSAGE_BEGIN(recipient?MSG_ONE:MSG_ALL,shotMessage,NULL,recipient?recipient->edict():NULL);
 WRITE_BYTE(p->entindex());WRITE_BYTE(p->m_vfShotFX);MESSAGE_END();
}
int VF_WeaponFXCode(CBasePlayer* p){
 if(VF_ReferenceMount(p)<0)return 0;
 if(p->m_vfShotFX&&!VF_DeveloperAllowed()){p->m_vfShotFX=0;VF_SendWeaponFX(p);}
 return p->m_vfShotFX>0&&p->m_vfShotFX<=vfshot::Count?p->m_vfShotFX:vfshot::Default+1;
}
