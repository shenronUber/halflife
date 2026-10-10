#ifndef VF_EQUIPMENT_H
#define VF_EQUIPMENT_H
class CBasePlayer;
bool VF_DeveloperAllowed();
int VF_ReferenceMount(CBasePlayer* player);
void VF_RegisterMessages();
void VF_PrecacheWeaponFX();
void VF_SendWeaponFX(CBasePlayer* player,CBasePlayer* recipient=0);
int VF_WeaponFXCode(CBasePlayer* player);
unsigned int VF_EnsureEquipment(CBasePlayer* player);
bool VF_EquipmentCommand(CBasePlayer* player,const char* command);
namespace vf { struct Catalog; struct AppearanceCatalog; struct Item; }
const vf::Item* VF_EquippedItem(CBasePlayer* player,int slot);
bool VF_ResolveEquipmentSkins(CBasePlayer* player,const vf::AppearanceCatalog& skins,int* output);
#endif
