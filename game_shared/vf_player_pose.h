// Authoritative gait and transition state used by both Studio collision and rendering.
#ifndef VF_PLAYER_POSE_H
#define VF_PLAYER_POSE_H
#include <string.h>
#define VF_PLAYER_POSE_VERSION 1
#define VF_PLAYER_POSE_MARKER 12026.0f
static inline int VF_PoseReferenceModel(const char* name){return name&&(strstr(name,"models/vf_r01/r01_tp")||strstr(name,"models/vf_melee/r01_tp"));}
static inline int VF_PosePlayerModel(const char* name){return VF_PoseReferenceModel(name)||(name&&strstr(name,"models/vf_skins/persona_rig"));}
// Same pitch blend as the canonical Studio evaluator, in entity-angle space.
static inline unsigned char VF_PosePitchBlend(float entity_pitch,float start,float end){
 float pitch=entity_pitch*3.f;
 if(pitch<start)return 0;
 if(pitch>end)return 255;
 return (unsigned char)(end-start<.1f?127:(int)(255.f*(pitch-start)/(end-start)));
}
// Player entity vuser2: packed previous blend bytes, packed gear, sample time.
// These are independent of the ammo-bearing clientdata vectors.
static inline float VF_PosePackBlend(unsigned char a,unsigned char b){return (float)((unsigned int)a|((unsigned int)b<<8));}
static inline unsigned char VF_PoseBlend(float value,int component){return (unsigned char)(((unsigned int)value>>(component*8))&255);}
static inline float VF_PosePackGear(float phase,int type,int raised){
 if(!(phase>=0&&phase<=1))phase=1;
 if(type<0||type>5)type=0;
 return (float)((unsigned int)(phase*65535.f+.5f)|((unsigned int)(raised!=0)<<16)|((unsigned int)type<<17));
}
static inline float VF_PoseGearPhase(float value){return ((unsigned int)value&65535)/65535.f;}
static inline int VF_PoseGearType(float value){return ((unsigned int)value>>17)&7;}
static inline int VF_PoseGearRaised(float value){return ((unsigned int)value>>16)&1;}
typedef struct vf_player_pose_s {
 float gait_yaw,gait_frame,sample_time;
 int previous_sequence;
 float previous_frame,transition_time;
 unsigned char previous_blend[2];
 int headgear_type,headgear_raised;
 float headgear_phase;
} vf_player_pose_t;
struct edict_s;
typedef int (*vf_get_player_pose_fn)(int,const struct edict_s*,vf_player_pose_t*);
#endif
