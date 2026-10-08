#ifndef VF_EQUIPMENT_H
#define VF_EQUIPMENT_H
class CBasePlayer;
void VF_RegisterMessages();
unsigned int VF_EnsureEquipment(CBasePlayer* player);
bool VF_EquipmentCommand(CBasePlayer* player,const char* command);
namespace vf { struct Catalog; struct AppearanceCatalog; }
bool VF_ResolveEquipmentSkins(CBasePlayer* player,const vf::AppearanceCatalog& skins,int* output);
#endif
