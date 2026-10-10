#ifndef VF_DEATH_CLIENT_H
#define VF_DEATH_CLIENT_H
#include "../game_shared/vf_engine_api.h"
void VF_DeathInit();void VF_DeathReset();void VF_DeathWorld();
void VF_DeathGuide(int selectedEffect);
bool VF_DeathAssembly(int entity,vf_assembly_t& assembly);
#endif
