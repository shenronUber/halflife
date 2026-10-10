#ifndef VF_WEAPON_FX_H
#define VF_WEAPON_FX_H
struct pmtrace_s;
struct cl_entity_s;
bool VF_WeaponFXSuppressStudioFlash(const cl_entity_s* entity,int eventCode);
void VF_WeaponFXInit();
void VF_WeaponFXReset();
void VF_WeaponFXWorld();
bool VF_WeaponFXGuide();
void VF_WeaponFXHud();
int VF_WeaponFXProfile(int player,int eventCode);
void VF_WeaponFXFire(int player,int profile,const float* source,const float* forward,const float* right,const float* up);
void VF_WeaponFXTrace(int player,int profile,const float* source,const float* end,pmtrace_s* trace);
#endif
