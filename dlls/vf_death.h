#ifndef VF_DEATH_SERVER_H
#define VF_DEATH_SERVER_H
#include "../game_shared/vf_status_policy.h"
class CBasePlayer;class CBaseMonster;
void VF_DeathRegister();
void VF_DeathPrecache();
bool VF_DeathGibSound(CBaseMonster*);
void VF_DeathSync(CBasePlayer*);
void VF_DeathCapture(CBasePlayer*);
void VF_DeathPlayer(CBasePlayer*);
void VF_DeathSpawn(CBasePlayer*);
void VF_DeathTarget(CBaseMonster*,int,const vfs::State&,int mask=0,int motion=0);
bool VF_DeathCommand(CBasePlayer*,const char*);
int VF_DeathMotion(const char*);
int VF_DeathMask(const char*);
#endif
