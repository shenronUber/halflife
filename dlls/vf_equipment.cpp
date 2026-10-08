#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "vf_equipment.h"
#include "vf_skins.h"
#include "../game_shared/vf_loadout.h"
#include "../game_shared/vf_appearance.h"
#include <string.h>
static vf::Catalog catalog;
static vf::AppearanceCatalog weaponStyles;
static int equipmentMessage;
void VF_RegisterMessages() {
    if(!equipmentMessage) equipmentMessage=REG_USER_MSG("VFBuild",43);
}
static void LoadCatalog() {
    int size=0;
    byte* bytes=LOAD_FILE_FOR_ME("vf/equipment.txt",&size);
    vf::ParseCatalog((const char*)bytes,size>0?size:0,catalog);
    if(bytes) FREE_FILE(bytes);
    size=0;bytes=LOAD_FILE_FOR_ME("vf/r01_styles.txt",&size);
    vf::ParseAppearances((const char*)bytes,size>0?size:0,weaponStyles);
    if(bytes) FREE_FILE(bytes);
    if(!catalog.valid) ALERT(at_console,"VF catalogue: %s\n",catalog.error);
}
static void Send(CBasePlayer* p,vf::Result result) {
    // The range mannequin shows the accepted assembly. This local laboratory
    // prop is shared, not a replacement for multiplayer player-model replication.
    CBaseEntity* mannequin=NULL;
    while((mannequin=UTIL_FindEntityByTargetname(mannequin,"vf_operator_preview"))!=NULL)
        mannequin->pev->body=vf::OperatorBody(catalog,p->m_vfItems);
    VF_RegisterMessages();
    MESSAGE_BEGIN(MSG_ONE,equipmentMessage,NULL,p->edict());
    WRITE_BYTE(vf::Protocol); WRITE_BYTE(result); WRITE_LONG(catalog.fingerprint); WRITE_LONG(weaponStyles.hash);
    for(int s=0;s<vf::SlotCount;++s) WRITE_BYTE(p->m_vfItems[s]);
    for(int s=0;s<vf::WeaponStyleSlots;++s) WRITE_BYTE(p->m_vfWeaponStyles[s]);
    MESSAGE_END();
    if(result==vf::Accepted)VF_BroadcastPlayer(p);
}
unsigned int VF_EnsureEquipment(CBasePlayer* p) {
    LoadCatalog();if(!catalog.valid)return 0;int totals[vf::BudgetCount];
    if((unsigned int)p->m_vfCatalogHash!=catalog.fingerprint||vf::Evaluate(catalog,p->m_vfItems,totals)!=vf::Accepted){vf::Defaults(catalog,p->m_vfItems);p->m_vfCatalogHash=(int)catalog.fingerprint;}
    if((unsigned int)p->m_vfWeaponStyleHash!=weaponStyles.hash||!vf::ValidWeaponStyles(weaponStyles,p->m_vfWeaponStyles)){
        memset(p->m_vfWeaponStyles,0,sizeof(p->m_vfWeaponStyles));p->m_vfWeaponStyleHash=(int)weaponStyles.hash;
    }
    return catalog.fingerprint;
}
bool VF_EquipmentCommand(CBasePlayer* p,const char* command) {
    const bool request=!strcmp(command,"vf_request");
    if(!request&&strcmp(command,"vf_apply")) return false;
    VF_EnsureEquipment(p); // loads equipment and the data-driven style catalog
    if(!catalog.valid) { Send(p,vf::BadCatalog); return true; }
    int totals[vf::BudgetCount];
    if((unsigned int)p->m_vfCatalogHash!=catalog.fingerprint||vf::Evaluate(catalog,p->m_vfItems,totals)!=vf::Accepted) {
        vf::Defaults(catalog,p->m_vfItems); p->m_vfCatalogHash=(int)catalog.fingerprint;
    }
    if(request) { Send(p,vf::Accepted); return true; }
    unsigned int hash;
    if((CMD_ARGC()!=vf::SlotCount+2&&CMD_ARGC()!=vf::SlotCount+3+vf::WeaponStyleSlots)||!vf::ParseUnsigned(CMD_ARGV(1),hash)) { Send(p,vf::BadRequest); return true; }
    if(hash!=catalog.fingerprint) { Send(p,vf::BadCatalog); return true; }
    int candidate[vf::SlotCount];
    for(int s=0;s<vf::SlotCount;++s) {
        unsigned int value;
        if(!vf::ParseUnsigned(CMD_ARGV(s+2),value)||value>=(unsigned int)catalog.count) { Send(p,vf::BadItem); return true; }
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
    vf::Result result=vf::Evaluate(catalog,candidate,totals);
    // Commit atomically. An invalid request cannot partially equip a build.
    if(result==vf::Accepted){
        memcpy(p->m_vfItems,candidate,sizeof(candidate));
        memcpy(p->m_vfWeaponStyles,styles,sizeof(styles));
    }
    ALERT(at_console,"VF equipment: result=%d TED=%d IP=%d HS=%d OI=%d SIG=%d BIO=%d\n",result,totals[0],totals[1],totals[2],totals[3],totals[4],totals[5]);
    if(result==vf::Accepted) ALERT(at_console,"VFR01 styles accepted: player=%d first=%d optic=%d feed=%d\n",p->entindex(),styles[0],styles[7],styles[3]);
    Send(p,result); return true;
}

bool VF_ResolveEquipmentSkins(CBasePlayer* p,const vf::AppearanceCatalog& skins,int* out){return vf::EquipmentSkins(catalog,p->m_vfItems,skins,out);}
