#ifndef VF_SERVER_WEAPON_MELEE_H
#define VF_SERVER_WEAPON_MELEE_H
class CBasePlayer;
void VF_MeleePrecache();
void VF_MeleeForget(int index);
void VF_MeleeSync(CBasePlayer* player);
bool VF_MeleeCommand(CBasePlayer* player,const char* command);
bool VF_MeleePose(CBasePlayer* player);
void VF_MeleeThink(CBasePlayer* player);
#endif
