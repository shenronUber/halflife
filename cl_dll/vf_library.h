#ifndef VF_LIBRARY_H
#define VF_LIBRARY_H
struct vf_assembly_s;
void VF_LibraryInit();
void VF_LibraryDraw();
bool VF_LibraryKey(int key);
const char* VF_LibraryWeaponPath();
void VF_LibraryClearWeapon();
void VF_LibraryAccessories(vf_assembly_s& assembly);
void VF_LibraryLegacy(const char* name);
#endif
