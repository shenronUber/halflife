#include "../../game_shared/vf_player_pose.h"
#include "../../game_shared/vf_pose_cache.h"
#include <limits>
#include <cassert>
#include <cstdio>
int main(){
 vf_pose_key_t key={};key.model=&key;key.header=&key;key.entity=&key;key.game=&key;
 vf_pose_key_t other=key;assert(VF_PoseKeyEqual(&key,&other));
 for(int i=0;i<24;++i){other=key;other.values[i]=1;assert(!VF_PoseKeyEqual(&key,&other));}
 other=key;other.time=.01;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.sequence=1;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.gait=1;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.hull=1;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.traversal=65536;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.model=&other;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.header=&other;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.entity=&other;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.game=&other;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;other.blend[1]=255;assert(!VF_PoseKeyEqual(&key,&other));
 other=key;key.values[0]=other.values[0]=std::numeric_limits<float>::quiet_NaN();assert(!VF_PoseKeyEqual(&key,&other));
 key.values[0]=other.values[0]=std::numeric_limits<float>::infinity();assert(!VF_PoseKeyEqual(&key,&other));
 assert(VF_PosePitchBlend(0,-35,35)==127);
 assert(VF_PosePitchBlend(-35.f/3,-35,35)==0);
 assert(VF_PosePitchBlend(35.f/3,-35,35)==255);
 assert(VF_PosePitchBlend(-80,-35,35)==0&&VF_PosePitchBlend(80,-35,35)==255);
 assert(VF_PosePitchBlend(0,0,0)==127);
 const char* reference[]={"models/vf_r01/r01_tp.mdl","models/vf_r01/r01_tp_side.mdl","models/vf_r01/r01_tp_top.mdl","models/vf_melee/r01_tp.mdl","models/vf_melee/r01_tp_side.mdl","models/vf_melee/r01_tp_top.mdl"};
 for(int i=0;i<6;++i){assert(VF_PoseReferenceModel(reference[i]));assert(VF_PosePlayerModel(reference[i]));}
 assert(!VF_PoseReferenceModel("models/vf_skins/persona_rig.mdl")&&VF_PosePlayerModel("models/vf_skins/persona_rig.mdl"));
 const char* otherModels[]={0,"models/vf_r01/r01_rig.mdl","models/vf_melee/r01_rig.mdl","models/vf_deaths/persona_death.mdl","models/vf_skins/persona_scout.mdl","models/player.mdl"};
 for(int i=0;i<6;++i)assert(!VF_PosePlayerModel(otherModels[i]));
 puts("PASS shared player-pose families: all six reference/strike bodies and fitted GIGN; viewmodels and corpses excluded");
}
