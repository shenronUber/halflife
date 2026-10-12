// Included by client.cpp so the export is built by all existing server targets.
#include "../game_shared/vf_player_pose.h"
#include "../game_shared/vf_headgear.h"
#include "../game_shared/vf_traversal.h"
namespace {
struct VFPoseHistory {
 unsigned int life;float time,yaw,gaitFrame,frame,transition;int sequence,gait;
 unsigned char blend[2];int previous;float previousFrame;unsigned char previousBlend[2];
 Vector origin;
};
VFPoseHistory vfPoseHistory[33];
bool VF_PlayerPose(CBasePlayer* p,vf_player_pose_t& result){
 if(!p||!p->IsAlive()||!VF_DeathCompatible(p)||p->entindex()<1||p->entindex()>32)return false;
 VFPoseHistory& h=vfPoseHistory[p->entindex()];float now=gpGlobals->time;
 // Player commands use the client's timebase; packing and collision also
 // query this pose at the server clock. That clock can be a few milliseconds
 // earlier in the same frame. Keep the gait history across those reads.
 if(h.life!=p->m_vfVoiceLife||now<h.time-1.f){h=VFPoseHistory();h.life=p->m_vfVoiceLife;h.time=now;h.yaw=p->pev->angles.y;h.sequence=h.previous=p->pev->sequence;h.origin=p->pev->origin;}
 if(h.sequence!=p->pev->sequence){h.previous=h.sequence;h.previousFrame=h.frame;memcpy(h.previousBlend,h.blend,2);h.transition=now;h.sequence=p->pev->sequence;
  // The push-off already starts at the exact hanging pose. A second .2s
  // crossfade would keep the old hands planted after the body turns away.
  if(VF_TR_Phase(p->pev->iuser4)==VF_TR_WALL_JUMP)h.transition=now-.2f;
 }
 float dt=now-h.time;
 if(dt>0){
  Vector movement=p->pev->origin-h.origin;float distance=movement.Length();
  if(!p->pev->gaitsequence)h.yaw=p->pev->angles.y;
  else if(distance/dt<5||(!movement.x&&!movement.y)){
   float delta=VF_TR_Angle(p->pev->angles.y-h.yaw);h.yaw=VF_TR_Angle(h.yaw+delta*(dt<.25f?dt*4:dt));distance=0;
  }else h.yaw=atan2f(movement.y,movement.x)*57.295779513f;
  float yaw=VF_TR_Angle(p->pev->angles.y-h.yaw);
  if(yaw>120||yaw<-120){h.yaw=VF_TR_Angle(h.yaw+180);distance=-distance;}
  studiohdr_t* header=(studiohdr_t*)GET_MODEL_PTR(p->edict());
  if(header&&p->pev->gaitsequence>0&&p->pev->gaitsequence<header->numseq){
   mstudioseqdesc_t* seq=(mstudioseqdesc_t*)((byte*)header+header->seqindex)+p->pev->gaitsequence;
   h.gaitFrame+=seq->linearmovement[0]>0?distance/seq->linearmovement[0]*seq->numframes:seq->fps*dt;
   if(seq->numframes>0){h.gaitFrame=fmodf(h.gaitFrame,(float)seq->numframes);if(h.gaitFrame<0)h.gaitFrame+=seq->numframes;}
  }
  h.origin=p->pev->origin;h.time=now;
 }
 // Several collision/packing queries can happen at the same timestamp,
 // before or after the engine temporarily assigns the camera's yaw. The
 // traversal body facing is a function of authoritative state, not that
 // transient entvars value, and must be refreshed even when dt is zero.
 if(!p->pev->gaitsequence){
  int phase=VF_TR_Phase(p->pev->iuser4);
  h.yaw=phase==VF_TR_WALL_JUMP?VF_TR_WallJumpBodyYaw(p->pev->iuser4,p->pev->fuser1,p->pev->v_angle.y):
   phase&&phase!=VF_TR_SLIDE&&phase!=VF_TR_WALL_RUN?VF_TR_Yaw(p->pev->iuser4):p->pev->angles.y;
 }
 h.frame=p->pev->frame;h.gait=p->pev->gaitsequence;memcpy(h.blend,p->pev->blending,2);
 // Transition from the pose actually evaluated above the gait, rather than
 // the raw entvars blend (often zero at neutral aim). Reusing that raw byte
 // briefly sampled the downward aim channel when entering a reload.
 if(h.gait){
  studiohdr_t* header=(studiohdr_t*)GET_MODEL_PTR(p->edict());
  if(header&&h.sequence>=0&&h.sequence<header->numseq){
   mstudioseqdesc_t* seq=(mstudioseqdesc_t*)((byte*)header+header->seqindex)+h.sequence;
   h.blend[0]=VF_PosePitchBlend(p->pev->angles.x,seq->blendstart[0],seq->blendend[0]);
  }
 }
 result.gait_yaw=h.yaw;result.gait_frame=h.gaitFrame;result.sample_time=now;
 result.previous_sequence=h.previous;result.previous_frame=h.previousFrame;result.transition_time=h.transition;memcpy(result.previous_blend,h.previousBlend,2);
 const vf::Item* item=VF_EquippedItem(p,vf::HelmetSlot);result.headgear_type=item?item->visual:0;result.headgear_raised=p->m_vfHeadgearRaised;
 float age=now-p->m_vfHeadgearStart;result.headgear_phase=p->m_vfHeadgearStart>0&&age>=0&&age<vf::HeadgearDuration?age/vf::HeadgearDuration:1;
 return true;
}
}
extern "C" __declspec(dllexport) int VF_GetPlayerPoseState(int version,const edict_t* edict,vf_player_pose_t* pose){
 if(version!=VF_PLAYER_POSE_VERSION||!edict||!pose)return 0;
 CBaseEntity* entity=CBaseEntity::Instance((edict_t*)edict);return entity&&entity->IsPlayer()&&VF_PlayerPose((CBasePlayer*)entity,*pose);
}
void VF_PlayerPoseUpdate(CBasePlayer* player){vf_player_pose_t pose={};VF_PlayerPose(player,pose);}
