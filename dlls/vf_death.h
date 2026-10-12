#ifndef VF_DEATH_SERVER_H
#define VF_DEATH_SERVER_H
#include "../game_shared/vf_status_policy.h"
class CBasePlayer;class CBaseMonster;
void VF_DeathRegister();
void VF_DeathPrecache();
bool VF_DeathGibSound(CBaseMonster*);
void VF_DeathSync(CBasePlayer*);
void VF_DeathCapture(CBasePlayer*,bool fullGib=false,const Vector& impact=Vector(0,0,0));
void VF_DeathPlayer(CBasePlayer*);
void VF_DeathSpawn(CBasePlayer*);
bool VF_DeathCompatible(CBasePlayer*);
void VF_DeathTrace(CBasePlayer*,int hitgroup,const Vector& direction,float damage,entvars_t* attacker,int bits);
void VF_DeathDamage(CBasePlayer*,entvars_t* attacker,float healthDamage,int bits);
void VF_DeathDiscardTrace(CBasePlayer*);
bool VF_DeathHeadMissing(CBasePlayer*);
void VF_DeathTarget(CBaseMonster*,int,const vfs::State&,int mask=-1,int motion=0,const Vector& impact=Vector(0,0,0));
bool VF_DeathCommand(CBasePlayer*,const char*);
int VF_DeathMotion(const char*);
int VF_DeathMask(const char*);
#endif
