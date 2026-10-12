// Included only by vf_equipment.cpp. No authored player/viewmodel sequences.
#include "../game_shared/vf_headgear.h"
#include "../game_shared/vf_traversal.h"
static int headgearMessage;
void VF_SendHeadgear(CBasePlayer* p,CBasePlayer* recipient) {
 if(!headgearMessage)headgearMessage=REG_USER_MSG("VFHeadgear",vf::HeadgearMessageSize);
 const float age=gpGlobals->time-p->m_vfHeadgearStart;
 const bool moving=p->IsAlive()&&p->m_vfHeadgearStart>0&&age>=0&&age<vf::HeadgearDuration&&VF_EquippedItem(p,vf::HelmetSlot);
 MESSAGE_BEGIN(recipient?MSG_ONE:MSG_ALL,headgearMessage,NULL,recipient?recipient->edict():NULL);
 WRITE_BYTE(p->entindex());WRITE_BYTE(p->m_vfHeadgearRaised?1:0);
 WRITE_SHORT(moving?1+(int)(age*1000):0);MESSAGE_END();
}
static bool VF_HeadgearCommand(CBasePlayer* p,const char* command) {
 if(strcmp(command,"vf_headgear_toggle"))return false;
 if(CMD_ARGC()!=1||!VF_EnsureEquipment(p))return true;
 const vf::Item* item=VF_EquippedItem(p,vf::HelmetSlot);
 if(!p->IsAlive()||!item){ClientPrint(p->pev,HUD_PRINTCENTER,"Equipez un casque dans l'atelier operateur.\n");return true;}
 const float age=gpGlobals->time-p->m_vfHeadgearStart;
 if((p->m_vfHeadgearStart>0&&age>=0&&age<vf::HeadgearDuration)||
    VF_TR_Phase(p->pev->iuser4)||p->m_flNextAttack>UTIL_WeaponTimeBase())return true;
 CBasePlayerWeapon* weapon=p->m_pActiveItem?(CBasePlayerWeapon*)p->m_pActiveItem:NULL;
 if(weapon&&weapon->m_fInReload)return true;
 // A background client may send no movement tick during the old gesture.
 // Deliver its pending feedback before replacing the completed action clock.
 VF_HeadgearFeedbackFlush(p);
 p->m_vfHeadgearRaised=!p->m_vfHeadgearRaised;p->m_vfHeadgearStart=gpGlobals->time;
 // Keep the weapon in the right hand while the support hand operates equipment.
 p->m_flNextAttack=UTIL_WeaponTimeBase()+vf::HeadgearDuration;
 if(weapon)weapon->m_flTimeWeaponIdle=UTIL_WeaponTimeBase()+vf::HeadgearDuration;
 VF_SendHeadgear(p,NULL);
 VF_HeadgearFeedbackStart(p,item->visual,p->m_vfHeadgearRaised!=0);
 ALERT(at_console,"VFHeadgear action: player=%d item=%s raised=%d duration=%.2f\n",p->entindex(),item->id,p->m_vfHeadgearRaised,vf::HeadgearDuration);
 return true;
}
