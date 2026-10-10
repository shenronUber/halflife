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
int FirstPersonSkin(const Catalog& catalog,const int* items,const AppearanceCatalog& skins,int slot);
int EquipmentModule(const Catalog& catalog,const int* items,int zone);
int FindAppearance(const AppearanceCatalog& catalog,const char* key);
void RestoreAppearances(const AppearanceCatalog& catalog,const char* const* keys,int* selection,int count);
const char* OperatorRig(const AppearanceCatalog& catalog,const int skins[SkinZones]);
bool ValidSkins(const AppearanceCatalog& catalog,const int skins[SkinZones]);
bool BoundWeaponStyles(const Catalog& equipment,const AppearanceCatalog& styles,const int* items,const int* chosen);
void BindWeaponStyles(const Catalog& equipment,const AppearanceCatalog& styles,const int* items,int* chosen);
void PromoteGameplayEquipment(const Catalog& equipment,const AppearanceCatalog& styles,int* items,int* chosen);
bool ValidWeaponStyles(const AppearanceCatalog& catalog,const int* styles);
}
#endif
