/* Shared predicted traversal state. Ammo owns vuser3.z; never touch it. */
#ifndef VF_TRAVERSAL_H
#define VF_TRAVERSAL_H
#include <math.h>
#include "vf_wallrun.h"
enum { VF_TR_NORMAL, VF_TR_VAULT, VF_TR_HANG, VF_TR_ARMED, VF_TR_CLIMB, VF_TR_SLIDE, VF_TR_DROP, VF_TR_WALL_JUMP };
#define VF_TR_RETURNING 32768
/* Same bit, disjoint phases: keeps the existing 24-bit network contract. */
#define VF_TR_TURNED 32768
#define VF_TR_WALL_JUMP_TIME .65f
#define VF_TR_WALL_JUMP_RELEASE .16f
#define VF_TR_WALL_JUMP_SPEED 270.0f
#define VF_TR_WALL_JUMP_UP 330.0f
#define VF_TR_WALL_JUMP_ANGLE 100.0f
#define VF_TR_WIDE 65536
#define VF_TR_SPAN_MASK (127<<17)
#define VF_TR_VAULT_TIME 0.82f
#define VF_TR_STEP_TIME 0.92f
#define VF_TR_CLIMB_TIME 0.85f
#define VF_TR_DROP_TIME 0.30f
#define VF_TR_SLIDE_TIME 1.2f
#define VF_TR_SLIDE_SOUND "vf_traversal/slide.wav"
#define VF_TR_SLIDE_MIN_SPEED 280.0f
#define VF_TR_SLIDE_MAX_SPEED 400.0f
#define VF_TR_SLIDE_FRICTION 0.35f
#define VF_TR_SLIDE_COOLDOWN 0.85f
#define VF_TR_HANG_DEPTH 40.0f
#define VF_TR_ARMED_DEPTH 18.0f
#define VF_TR_FP_GRIP_BELOW_TOP 2.8f
#define VF_TR_ARM_TIME .28f
#define VF_TR_GUARD_ANGLE 45.0f
#define VF_TR_FIRE_ANGLE 75.0f
static int VF_TR_Phase(int state) { return VF_WR_Running(state)?VF_TR_WALL_RUN:state&7; }
static float VF_TR_TransferTime(int state) { return VF_TR_Phase(state)==VF_TR_CLIMB?VF_TR_CLIMB_TIME:(state&VF_TR_WIDE)?VF_TR_STEP_TIME:VF_TR_VAULT_TIME; }
static float VF_TR_VaultSpan(int state) { int width=(state>>17)&127;return width?width:42; }
static int VF_TR_Hanging(int state) { int p=VF_TR_Phase(state);return p==VF_TR_HANG||p==VF_TR_ARMED; }
static int VF_TR_BusyHands(int state) { int p=VF_TR_Phase(state);return p==VF_TR_HANG||p==VF_TR_VAULT||p==VF_TR_CLIMB||p==VF_TR_DROP||p==VF_TR_WALL_JUMP; }
static int VF_TR_HideWeapon(int state,float remaining) { return (VF_TR_BusyHands(state)&&VF_TR_Phase(state)!=VF_TR_VAULT)||(VF_TR_Phase(state)==VF_TR_ARMED&&remaining>VF_TR_ARM_TIME*.15f); }
static int VF_TR_NoReload(int state) { return VF_TR_Hanging(state)||VF_TR_BusyHands(state); }
static float VF_TR_Yaw(int state) { return ((state>>3)&4095)*0.1f; }
static int VF_TR_State(int phase,float yaw) {
 while(yaw<0)yaw+=360;while(yaw>=360)yaw-=360;
 return (phase==VF_TR_WALL_RUN?VF_WR_ACTIVE:phase)|(((int)(yaw*10+0.5f)%3600)<<3);
}
static float VF_TR_Angle(float angle) { while(angle>180)angle-=360;while(angle<-180)angle+=360;return angle; }
/* Body-only facing: release the palms, then follow the freely controlled
   look direction. Entity angles carry this same pose to Studio collision
   and remote renderers; first-person view and jump physics are unchanged. */
static float VF_TR_WallJumpBodyYaw(int state,float remaining,float viewYaw) {
 float wall=VF_TR_Yaw(state),t=(VF_TR_WALL_JUMP_TIME-remaining-.04f)/.20f;
 if(t<0)t=0;if(t>1)t=1;t=t*t*(3.f-2.f*t);
 return VF_TR_Angle(wall+VF_TR_Angle(viewYaw-wall)*t);
}
static float VF_TR_AimDeploy(float relative) {
 float t=(fabsf(VF_TR_Angle(relative))-VF_TR_GUARD_ANGLE)/(VF_TR_FIRE_ANGLE-VF_TR_GUARD_ANGLE);
 if(t<=0)return 0;if(t>=1)return 1;return t*t*(3-2*t);
}
static int VF_TR_CanFire(int state,float remaining,float yaw) {
 if(VF_TR_BusyHands(state))return 0;
 return VF_TR_Phase(state)!=VF_TR_ARMED||(remaining<=0&&fabsf(VF_TR_Angle(yaw-VF_TR_Yaw(state)))>=VF_TR_FIRE_ANGLE);
}
/* Validate serialized durations and packed yaw before putting them back in
   pmove. Zero also migrates saves made before traversal existed. */
static int VF_TR_SaveValid(int state,float remaining,const float *anchor) {
 int p=VF_TR_Phase(state),i;float limit;
 if(state<0||(state&~(65535|VF_TR_WIDE|VF_TR_SPAN_MASK))||((state>>3)&4095)>=3600)return 0;
 if(p!=VF_TR_VAULT&&(state&VF_TR_SPAN_MASK))return 0;
 if(p!=VF_TR_VAULT&&p!=VF_TR_WALL_RUN&&(state&VF_TR_WIDE))return 0;
 if((state&VF_TR_RETURNING)&&p!=VF_TR_HANG&&p!=VF_TR_WALL_JUMP&&p!=VF_TR_WALL_RUN)return 0;
 if(p==VF_TR_NORMAL)return state==0&&remaining>=-1&&remaining<=0;
 limit=p==VF_TR_VAULT?VF_TR_TransferTime(state):p==VF_TR_CLIMB?VF_TR_CLIMB_TIME:
  p==VF_TR_SLIDE?VF_TR_SLIDE_TIME:p==VF_TR_DROP?VF_TR_DROP_TIME:p==VF_TR_WALL_JUMP?VF_TR_WALL_JUMP_TIME:p==VF_TR_WALL_RUN?1:VF_TR_ARM_TIME;
 if(!(remaining>=0&&remaining<=limit+.001f))return 0;
 for(i=0;i<3;i++)if(!(anchor[i]-anchor[i]==0))return 0;
 return 1;
}
#endif
