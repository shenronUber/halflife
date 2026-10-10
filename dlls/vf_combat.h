#ifndef VF_COMBAT_SERVER_H
#define VF_COMBAT_SERVER_H
#include "../game_shared/vf_combat_policy.h"
class CBasePlayer;
// A shot's context is scoped to one actual trace. It cannot leak into later
// melee, hazards or a projectile that arrived after the shooter changed weapons.
class VF_ProjectileTraceScope {
 const VF_ProjectileTraceScope* previous;
public:
 int bulletType,element;entvars_t* attacker;Vector source,end;
 VF_ProjectileTraceScope(int bullet,entvars_t* from,const Vector& src,const Vector& destination,const TraceResult& trace,float baseDamage=0,bool allowProc=true);
 ~VF_ProjectileTraceScope();
private:
 VF_ProjectileTraceScope(const VF_ProjectileTraceScope&);
 VF_ProjectileTraceScope& operator=(const VF_ProjectileTraceScope&);
};
int VF_CurrentShotElement();
void VF_CombatInit();
void VF_CombatReset();
void VF_CombatClear(CBasePlayer* player);
float VF_PlayerTraceDamage(CBasePlayer* victim,entvars_t* attacker,float raw,const Vector& direction,const TraceResult& trace,int damageBits);
bool VF_CombatCommand(CBasePlayer*,const char*);
#endif
