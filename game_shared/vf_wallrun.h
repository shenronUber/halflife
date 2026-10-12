/* Low phase zero + bit 16 is a disjoint tag in the existing 24-bit word.
   Vault owns bit 16 only with low phase one. No network lanes are added. */
#ifndef VF_WALLRUN_H
#define VF_WALLRUN_H
#define VF_TR_WALL_RUN 8
#define VF_WR_ACTIVE 65536
#define VF_WR_RIGHT 32768
#define VF_WR_MIN_SPEED 280.0f
#define VF_WR_MIN_TANGENT 200.0f
#define VF_WR_MAX_SPEED 400.0f
#define VF_WR_REACH 12.0f
#define VF_WR_COOLDOWN .18f
#define VF_WR_JUMP_SPEED 420.0f
#define VF_WR_JUMP_OUT 180.0f
#define VF_WR_CYCLE_DISTANCE 160.0f
/* Intentional entry: look within 60 degrees of the supporting wall's
   inward normal. Once attached, yaw is free through either side's 90
   degrees from the stored run direction; pitch never breaks attachment. */
#define VF_WR_ENTRY_LOOK_DOT .5f
#define VF_WR_LOOK_LIMIT 90.0f
static int VF_WR_LookAllowed(float viewYaw,float runYaw) {
 float delta=viewYaw-runYaw;
 while(delta>180)delta-=360;while(delta<-180)delta+=360;
 return delta<=VF_WR_LOOK_LIMIT+.0001f&&delta>=-VF_WR_LOOK_LIMIT-.0001f;
}
static int VF_WR_Running(int state) { return (state&7)==0&&(state&VF_WR_ACTIVE)!=0; }
#endif
