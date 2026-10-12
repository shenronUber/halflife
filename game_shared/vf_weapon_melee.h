#ifndef VF_WEAPON_MELEE_H
#define VF_WEAPON_MELEE_H
namespace vf {
static const float MeleeDuration=1.1f;
static const float MeleeImpact=13.f/30.f;
static const float MeleeRange=40.f;
static const float MeleeDamage=35.f;
static const int MeleeMessageSize=6;
inline bool MeleeReady(bool alive,int weapon,bool reload,bool busy,int traversal){return alive&&weapon==4&&!reload&&!busy&&!traversal;}
inline bool MeleeClockValid(float age){return age>=-.05f&&age<MeleeDuration;}
inline bool MeleeImpactDue(float age,bool impacted){return !impacted&&age>=MeleeImpact&&age<MeleeDuration;}
}
#endif
