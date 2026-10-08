#ifndef VF_APPEARANCE_H
#define VF_APPEARANCE_H
#include <stddef.h>
namespace vf {
enum { SkinZones=5, MaxAppearances=240, WeaponStyleSlots=12, MaxWeaponStyles=32 };
struct Appearance { char key[32],name[72];int animations;char model[32];int skin; };
struct AppearanceCatalog { Appearance entries[MaxAppearances];int count;unsigned int hash;bool valid; };
bool ParseAppearances(const char* text,size_t size,AppearanceCatalog& out);
struct Catalog;
int EquipmentFamily(const Catalog& catalog,const int* items,int slot);
const char* EquipmentLookName(int family);
bool EquipmentSkins(const Catalog& catalog,const int* items,const AppearanceCatalog& skins,int* out);
int EquipmentModule(const Catalog& catalog,const int* items,int zone);
bool ValidSkins(const AppearanceCatalog& catalog,const int skins[SkinZones]);
bool ValidWeaponStyles(const AppearanceCatalog& catalog,const int* styles);
}
#endif
