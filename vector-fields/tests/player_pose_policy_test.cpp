#include "../../game_shared/vf_player_pose.h"
#include <cassert>
#include <cstdio>
int main(){
 assert(VF_PosePitchBlend(0,-35,35)==127);
 assert(VF_PosePitchBlend(-35.f/3,-35,35)==0);
 assert(VF_PosePitchBlend(35.f/3,-35,35)==255);
 assert(VF_PosePitchBlend(-80,-35,35)==0&&VF_PosePitchBlend(80,-35,35)==255);
 assert(VF_PosePitchBlend(0,0,0)==127);
 const char* reference[]={"models/vf_r01/r01_tp.mdl","models/vf_r01/r01_tp_side.mdl","models/vf_r01/r01_tp_top.mdl","models/vf_melee/r01_tp.mdl","models/vf_melee/r01_tp_side.mdl","models/vf_melee/r01_tp_top.mdl"};
 for(int i=0;i<6;++i){assert(VF_PoseReferenceModel(reference[i]));assert(VF_PosePlayerModel(reference[i]));}
 assert(!VF_PoseReferenceModel("models/vf_skins/persona_rig.mdl")&&VF_PosePlayerModel("models/vf_skins/persona_rig.mdl"));
 const char* other[]={0,"models/vf_r01/r01_rig.mdl","models/vf_melee/r01_rig.mdl","models/vf_deaths/persona_death.mdl","models/vf_skins/persona_scout.mdl","models/player.mdl"};
 for(int i=0;i<6;++i)assert(!VF_PosePlayerModel(other[i]));
 puts("PASS shared player-pose families: all six reference/strike bodies and fitted GIGN; viewmodels and corpses excluded");
}
