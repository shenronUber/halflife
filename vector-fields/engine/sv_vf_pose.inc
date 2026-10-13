/* Collision adapter for the same canonical/procedural pose as ref/gl.
 * No bone matrices from a client are trusted by the server. */
#include "cl_entity.h"
#include "vf_engine_api.h"
#include "vf_player_pose.h"
#include "vf_headgear.h"
#include "vf_pose_cache.h"
static struct {
 qboolean valid;vf_pose_key_t key;
 matrix3x4 bones[MAXSTUDIOBONES],transform;
} vf_sv_pose_cache[33];
static unsigned int vf_sv_pose_hits,vf_sv_pose_evaluations;
static convar_t *vf_sv_pose_enabled;
static void VF_SVPoseBench(void);
static void VF_SVPoseInfo(void){Con_Printf("VFPoseCache hits=%u evaluations=%u bytes=%u enabled=%d\n",vf_sv_pose_hits,vf_sv_pose_evaluations,(unsigned)sizeof(vf_sv_pose_cache),vf_sv_pose_enabled&&vf_sv_pose_enabled->value!=0);}
static void Mod_VFClearPoseCache(void){memset(vf_sv_pose_cache,0,sizeof(vf_sv_pose_cache));vf_sv_pose_hits=vf_sv_pose_evaluations=0;}

static struct {
 matrix3x4 bonestransform[MAXSTUDIOBONES],lighttransform[MAXSTUDIOBONES],rotationmatrix;
 double time;int interpolate;
} vf_sv_studio;
static struct {cl_entity_t *viewent;} vf_sv_tr;
static struct {vec3_t vforward,vright,vup;struct {vec3_t vieworigin;} rvp;} vf_sv_ri;
static struct {int developer;} vf_sv_globals;
typedef struct {float gaityaw;} vf_sv_player_info_t;
static vf_sv_player_info_t vf_sv_player,*vf_sv_info;
static void *VF_SVExtra(int type,model_t *model){return Mod_StudioExtradata(model);}
static model_t *VF_SVLoadModel(const char *name){return Mod_ForName(name,false,false);}
static struct {void *(*R_StudioGetAnim)(studiohdr_t*,model_t*,mstudioseqdesc_t*);void (*Con_Printf)(const char*,...);void *(*Mod_Extradata)(int,model_t*);} vf_sv_functions={R_StudioGetAnim,Con_Printf,VF_SVExtra};
static vf_sv_player_info_t *VF_SVPlayerInfo(int index){return &vf_sv_player;}
static void VF_SVSaveBones(void){}
static void VF_SVAttachments(void){}
static void VF_SVFallback(cl_entity_t *ent){}
static float VF_SVFrame(cl_entity_t *ent,mstudioseqdesc_t *seq,double time){
 double f=seq->numframes>1?ent->curstate.frame*(seq->numframes-1)/256.0:0;
 if(time>ent->curstate.animtime)f+=(time-ent->curstate.animtime)*ent->curstate.framerate*seq->fps;
 if(seq->numframes>1&&(seq->flags&STUDIO_LOOPING)){f=fmod(f,seq->numframes-1);if(f<0)f+=seq->numframes-1;}
 return bound(0.f,(float)f,Q_max(0.f,seq->numframes-1.001f));
}
#define g_studio vf_sv_studio
#define tr vf_sv_tr
#define RI vf_sv_ri
#define gpGlobals (&vf_sv_globals)
#define gEngfuncs vf_sv_functions
#define m_pStudioHeader mod_studiohdr
#define m_pPlayerInfo vf_sv_info
#define player_info_t vf_sv_player_info_t
#define pfnPlayerInfo VF_SVPlayerInfo
#define R_StudioSaveBones VF_SVSaveBones
#define R_StudioCalcAttachments(...) VF_SVAttachments()
#define R_StudioSetupBones VF_SVFallback
#define R_StudioEstimateFrame VF_SVFrame
#define R_VFLoadModel VF_SVLoadModel
#include "vf_player_pose.inc"
#include "gl_vf_headgear.inc"
#undef R_VFLoadModel
#undef player_info_t
#undef R_StudioEstimateFrame
#undef R_StudioSetupBones
#undef R_StudioCalcAttachments
#undef R_StudioSaveBones
#undef pfnPlayerInfo
#undef m_pPlayerInfo
#undef m_pStudioHeader
#undef gEngfuncs
#undef gpGlobals
#undef RI
#undef tr
#undef g_studio

static qboolean Mod_VFPlayerModel(model_t *model,const edict_t *edict){
 return edict&&FBitSet(edict->v.flags,FL_CLIENT|FL_FAKECLIENT)&&
  VF_PosePlayerModel(model->name);
}
static qboolean Mod_VFPlayerPose(model_t *model,float frame,int sequence,const edict_t *edict){
 if(!Mod_VFPlayerModel(model,edict)||edict->v.deadflag!=DEAD_NO)return false;
 vf_get_player_pose_fn get=(vf_get_player_pose_fn)COM_GetProcAddress(svgame.hInstance,"VF_GetPlayerPoseState");
 vf_player_pose_t state={0};if(!get||!get(VF_PLAYER_POSE_VERSION,edict,&state))return false;
 cl_entity_t ent={0};ent.player=true;ent.index=NUM_FOR_EDICT(edict);ent.model=model;
 VectorCopy(edict->v.origin,ent.origin);VectorCopy(edict->v.angles,ent.angles);
 ent.curstate.sequence=sequence;ent.curstate.frame=frame;ent.curstate.animtime=edict->v.animtime;ent.curstate.framerate=edict->v.framerate;
 ent.curstate.gaitsequence=edict->v.gaitsequence;ent.curstate.iuser4=edict->v.iuser4;ent.curstate.fuser1=edict->v.fuser1;ent.curstate.fuser4=edict->v.fuser4;
 ent.curstate.usehull=FBitSet(edict->v.flags,FL_DUCKING)?1:0;
 VectorCopy(edict->v.vuser3,ent.curstate.vuser3);memcpy(ent.curstate.blending,edict->v.blending,2);memset(ent.curstate.controller,127,4);memset(ent.latched.prevcontroller,127,4);
 ent.curstate.vuser4[0]=state.gait_yaw;ent.curstate.vuser4[1]=state.gait_frame;ent.curstate.vuser4[2]=VF_PLAYER_POSE_MARKER;
 ent.curstate.vuser1[0]=state.previous_sequence;ent.curstate.vuser1[1]=state.previous_frame;ent.curstate.vuser1[2]=state.transition_time;
 ent.curstate.vuser2[0]=VF_PosePackBlend(state.previous_blend[0],state.previous_blend[1]);
 ent.curstate.vuser2[1]=VF_PosePackGear(state.headgear_phase,state.headgear_type,state.headgear_raised);ent.curstate.vuser2[2]=state.sample_time;
 vf_sv_studio.time=svgame.globals->time;vf_sv_studio.interpolate=1;vf_sv_globals.developer=0;vf_sv_player.gaityaw=state.gait_yaw;
 if(!vf_sv_pose_enabled){vf_sv_pose_enabled=Cvar_Get("vf_sv_pose_cache","1",0,"Reuse identical authoritative Studio poses");Cmd_AddCommand("vf_sv_pose_info",VF_SVPoseInfo,"Server pose cache counters");Cmd_AddCommand("vf_sv_pose_bench",VF_SVPoseBench,"Measure repeated server pose queries (cheats only)");}
 vf_pose_key_t key={0};key.model=model;key.header=mod_studiohdr;key.entity=edict;key.game=svgame.hInstance;key.time=vf_sv_studio.time;
 key.sequence=sequence;key.gait=ent.curstate.gaitsequence;key.hull=ent.curstate.usehull;key.traversal=ent.curstate.iuser4;memcpy(key.blend,ent.curstate.blending,2);
 memcpy(key.values,ent.origin,3*sizeof(float));memcpy(key.values+3,ent.angles,3*sizeof(float));
 key.values[6]=frame;key.values[7]=ent.curstate.animtime;key.values[8]=ent.curstate.framerate;key.values[9]=ent.curstate.fuser1;key.values[10]=ent.curstate.fuser4;
 memcpy(key.values+11,ent.curstate.vuser1,3*sizeof(float));memcpy(key.values+14,ent.curstate.vuser2,3*sizeof(float));
 memcpy(key.values+17,ent.curstate.vuser3,3*sizeof(float));memcpy(key.values+20,ent.curstate.vuser4,3*sizeof(float));key.values[23]=state.headgear_phase;
 int slot=ent.index; qboolean cacheable=slot>0&&slot<=32&&vf_sv_pose_enabled->value!=0;
 if(cacheable&&vf_sv_pose_cache[slot].valid&&VF_PoseKeyEqual(&key,&vf_sv_pose_cache[slot].key)){
  ++vf_sv_pose_hits;
  for(int i=0;i<mod_studiohdr->numbones;++i){Matrix3x4_Copy(studio_bones[i],vf_sv_pose_cache[slot].bones[i]);Matrix3x4_Copy(vf_sv_studio.bonestransform[i],studio_bones[i]);}
  Matrix3x4_Copy(studio_transform,vf_sv_pose_cache[slot].transform);
  if(Cvar_VariableInteger("developer")>=3)R_VFAuditPlayerPose("server",&ent);
  return true;
 }
 ++vf_sv_pose_evaluations;
 R_VFCanonicalBones(&ent,true);
 if(VF_PoseReferenceModel(model->name))R_VFPlayerTorsoYaw(&ent,true);
 R_VFSlideCombat(&ent);R_VFLedgePalms(&ent);R_VFVaultPalm(&ent);
 vf_assembly_t gear={0};gear.headgear_type=state.headgear_type;gear.headgear_phase=state.headgear_phase;
 if(state.headgear_type>0){
  gear.count=1;Q_strncpy(gear.parts[0].model,"models/vf_headgear/headgear.mdl",sizeof(gear.parts[0].model));
  float pivot[3],angle,shift[3];HeadgearTransform(state.headgear_type,HeadgearPose(state.headgear_phase,state.headgear_raised),pivot,&angle,shift);gear.parts[0].angles[1]=angle;
  R_VFHeadgearGesture(&ent,&gear);
 }
 for(int i=0;i<mod_studiohdr->numbones;++i)Matrix3x4_Copy(studio_bones[i],vf_sv_studio.bonestransform[i]);
 if(Cvar_VariableInteger("developer")>=3)R_VFAuditPlayerPose("server",&ent);
 Matrix3x4_Copy(studio_transform,vf_sv_studio.rotationmatrix);
 if(cacheable){vf_sv_pose_cache[slot].valid=true;vf_sv_pose_cache[slot].key=key;
  for(int i=0;i<mod_studiohdr->numbones;++i)Matrix3x4_Copy(vf_sv_pose_cache[slot].bones[i],studio_bones[i]);
  Matrix3x4_Copy(vf_sv_pose_cache[slot].transform,studio_transform);
 }
 return true;
}

void Mod_VFPlayerBounds(edict_t *edict){
 model_t *model=SV_ModelHandle(edict->v.modelindex);if(!model||!Mod_VFPlayerModel(model,edict))return;
 studiohdr_t *saved=mod_studiohdr;mod_studiohdr=Mod_StudioExtradata(model);
 if(mod_studiohdr&&Mod_VFPlayerPose(model,edict->v.frame,edict->v.sequence,edict)){
  mstudiobbox_t *boxes=(void *)((byte *)mod_studiohdr+mod_studiohdr->hitboxindex);
  for(int b=0;b<mod_studiohdr->numhitboxes;++b)for(int corner=0;corner<8;++corner){
   vec3_t local,world;for(int axis=0;axis<3;++axis)local[axis]=(corner&(1<<axis))?boxes[b].bbmax[axis]:boxes[b].bbmin[axis];
   Matrix3x4_VectorTransform(studio_bones[boxes[b].bone],local,world);
   for(int axis=0;axis<3;++axis){edict->v.absmin[axis]=Q_min(edict->v.absmin[axis],world[axis]-1);edict->v.absmax[axis]=Q_max(edict->v.absmax[axis],world[axis]+1);}
  }
 }
 mod_studiohdr=saved;
}

static void VF_SVPoseBench(void){
 if(sv.state!=ss_active||!Cvar_VariableInteger("sv_cheats")||Cmd_Argc()!=2)return;
 int queries=Q_atoi(Cmd_Argv(1));if(queries<1||queries>4096)return;
 unsigned hits=vf_sv_pose_hits,evals=vf_sv_pose_evaluations;int clients=0,requests=0;
 studiohdr_t *saved=mod_studiohdr;double start=Platform_DoubleTime();
 for(int i=1;i<=svs.maxclients&&i<=32;++i){
  edict_t *edict=SV_EdictNum(i);model_t *model=SV_ModelHandle(edict->v.modelindex);
  if(!model||!Mod_VFPlayerModel(model,edict)||edict->v.deadflag!=DEAD_NO)continue;
  mod_studiohdr=Mod_StudioExtradata(model);if(!mod_studiohdr)continue;
  ++clients;for(int q=0;q<queries;++q)requests+=Mod_VFPlayerPose(model,edict->v.frame,edict->v.sequence,edict);
 }
 mod_studiohdr=saved;
 Con_Printf("VFPoseBench clients=%d queries=%d requests=%d enabled=%d milliseconds=%.4f hits=%u evaluations=%u\n",clients,queries,requests,vf_sv_pose_enabled->value!=0,(Platform_DoubleTime()-start)*1000,vf_sv_pose_hits-hits,vf_sv_pose_evaluations-evals);
}
