// Physical lookup, unknown handling and preservation of the legacy damage policy.
#include "../../game_shared/vf_combat_policy.h"
#include <cassert>
#include <cstdio>
#include <cstring>
int main(){
 using namespace vfc;
 Multipliers m={2,1,1,1,1};
 const float expected[]={10,20,10,10,10,10,10,10,10};
 for(int i=0;i<=8;++i)assert(LegacyTraceDamage(10,HitRegion(i),m)==expected[i]);
 assert(HitRegion(-1)==Unknown&&HitRegion(9)==Unknown&&HitRegion(200)==Unknown);
 assert(SurfaceSlot(Chest)==Slot_torso&&Slot_torso==3&&Slot_gloves==2);
 assert(SurfaceSlot(Unknown)==-1&&SurfaceSlot(Generic)==-1);
 // Distinct live skill settings must also preserve each historical branch.
 Multipliers custom={3.5f,.8f,1.2f,.7f,.5f};
 assert(LegacyTraceDamage(20,Head,custom)==70);
 assert(LegacyTraceDamage(20,Chest,custom)==16);
 assert(LegacyTraceDamage(20,Abdomen,custom)==24);
 assert(LegacyTraceDamage(20,LeftArm,custom)==14&&LegacyTraceDamage(20,RightArm,custom)==14);
 assert(LegacyTraceDamage(20,LeftLeg,custom)==10&&LegacyTraceDamage(20,RightLeg,custom)==10);
 assert(LegacyTraceDamage(0,Head,custom)==0&&LegacyTraceDamage(10,Unknown,custom)==10);
 assert(ItemProfile(-1,0,0)==Profile_unknown&&ItemProfile(21,0,0)==Profile_unknown);
 assert(ItemProfile(Slot_torso,"gign_torso_gign","gign_torso")==Profile_uniform);
 assert(ItemProfile(Slot_torso,"gign_torso_medieval-forge","gign_torso")==Profile_uniform);
 // Exact object wins even when a generic geometry mapping occurs earlier.
 const ItemOverride test[]={ {"test_geometry",Profile_metal}, {"test_geometry__paint",Profile_uniform}, {"",Profile_unknown} };
 assert(ItemProfile(Slot_torso,"test_geometry__paint","test_geometry",test)==Profile_uniform);
 assert(ItemProfile(Slot_torso,"test_geometry__other","test_geometry",test)==Profile_metal);
 assert(ItemProfile(Slot_torso,"unmapped","unmapped",test)==Profile_uniform);
 for(int p=0;p<ProfileCount;++p)for(int i=0;i<profiles[p].count;++i){
  const LayerDefinition& l=profiles[p].layers[i];assert(l.material>=0&&l.material<MaterialCount);
  assert(l.thicknessMm==-1&&!LayerCalibrated(l));
 }
 assert(materials[Mat_unknown].densityKgM3==-1&&materials[Mat_composite].densityKgM3==-1);
 assert(TextureMaterial('M')==Mat_steel&&TextureMaterial('W')==Mat_wood&&TextureMaterial('Y')==Mat_glass&&TextureMaterial('F')==Mat_flesh&&TextureMaterial('?')==Mat_unknown);
 assert(ProjectileCount==9&&projectiles[5].nature==Blunt);
 for(int i=1;i<ProjectileCount;++i){assert(projectiles[i].nativeType==i);if(i!=5)assert(projectiles[i].nature==Kinetic);assert(projectiles[i].massKg==-1&&projectiles[i].speedMS==-1&&!projectiles[i].calibrated);}
 puts("PASS combat policy: seven regions, unchanged skill damage, physical override precedence, unknown calibration and projectile types");
}
