#ifndef VF_COMBAT_POLICY_H
#define VF_COMBAT_POLICY_H
#include "vf_material_catalog.h"
#include <cstring>
namespace vfc {
enum Region {Generic,Head,Chest,Abdomen,LeftArm,RightArm,LeftLeg,RightLeg,Unknown};
inline Region HitRegion(int group){return group>=0&&group<=7?(Region)group:Unknown;}
inline const char* RegionKey(Region r){static const char* ids[]={"generic","head","chest","abdomen","left_arm","right_arm","left_leg","right_leg","unknown"};return ids[r>=Generic&&r<=Unknown?r:Unknown];}
struct Multipliers {float head,chest,abdomen,arm,leg;};
inline float LocationMultiplier(Region r,const Multipliers& m){switch(r){case Head:return m.head;case Chest:return m.chest;case Abdomen:return m.abdomen;case LeftArm:case RightArm:return m.arm;case LeftLeg:case RightLeg:return m.leg;default:return 1;}}
// This stage deliberately has no material attenuation. Existing armor remains
// in CBasePlayer::TakeDamage, after the engine's legacy hit-region multiplier.
inline float LegacyTraceDamage(float raw,Region r,const Multipliers& m){return raw*LocationMultiplier(r,m);}
inline int SurfaceSlot(Region r){switch(r){case Head:return Slot_head;case Chest:case Abdomen:case LeftArm:case RightArm:return Slot_torso;case LeftLeg:case RightLeg:return Slot_legs;default:return -1;}}
inline int ItemProfile(int slot,const char* id,const char* model,const ItemOverride* overrides=itemOverrides){
 // A precise physical object overrides its generic geometry profile.
 for(int i=0;id&&overrides[i].key[0];++i)if(!strcmp(overrides[i].key,id))return overrides[i].profile;
 for(int i=0;model&&overrides[i].key[0];++i)if(!strcmp(overrides[i].key,model))return overrides[i].profile;
 return slot>=0&&slot<21?slotProfiles[slot]:Profile_unknown;
}
inline bool LayerCalibrated(const LayerDefinition& l){return l.material>=0&&l.material<MaterialCount&&materials[l.material].calibrated&&materials[l.material].resistanceJPerMm>=0&&l.thicknessMm>=0;}

}
#endif
