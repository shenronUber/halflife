/* Compiled in both movement DLLs. All persistent state travels in pmove. */
#include "../game_shared/vf_static_brush.h"
static pmtrace_t VF_TR_Trace(const float *a,const float *b,int hull) {
 int previous=pmove->usehull;pmtrace_t tr;
 pmove->usehull=hull;tr=pmove->PM_PlayerTrace((float*)a,(float*)b,PM_NORMAL,-1);pmove->usehull=previous;return tr;
}
static int VF_TR_Clear(const float *p,int hull) { pmtrace_t tr=VF_TR_Trace(p,p,hull);return !tr.startsolid&&!tr.allsolid; }
static int VF_TR_Static(pmtrace_t *tr) {
 return tr->fraction<1&&!tr->startsolid&&!tr->allsolid&&tr->ent>=0&&tr->ent<pmove->numphysent&&
  !pmove->physents[tr->ent].player&&(tr->ent==0||pmove->physents[tr->ent].movetype==MOVETYPE_NONE||
   VF_StaticBrush(pmove->physents[tr->ent].movetype,pmove->physents[tr->ent].solid,pmove->physents[tr->ent].controller));
}
static void VF_TR_Direction(float yaw,vec3_t dir) {
 dir[0]=(float)cos(yaw*3.141592653589793/180);dir[1]=(float)sin(yaw*3.141592653589793/180);dir[2]=0;
}
static void VF_TR_End(float cooldown) { pmove->iuser4=0;pmove->fuser1=-cooldown; }
static void VF_TR_Crouch(void) {
 if(!(pmove->flags&FL_DUCKING)&&pmove->onground!=-1)pmove->origin[2]-=18;
 pmove->flags|=FL_DUCKING;pmove->usehull=1;pmove->bInDuck=false;pmove->flDuckTime=0;pmove->view_ofs[2]=VEC_DUCK_VIEW;
}
static int VF_TR_Sweep(vec3_t target) {
 pmtrace_t tr=VF_TR_Trace(pmove->origin,target,pmove->usehull);
 if(tr.startsolid||tr.allsolid)return 0;
 VectorCopy(tr.endpos,pmove->origin);
 if(tr.fraction<1){PM_AddToTouched(tr,pmove->velocity);return 0;}return 1;
}
static int VF_TR_Ledge(vec3_t dir,pmtrace_t *wall,pmtrace_t *top,float low,float high) {
 vec3_t a,b;
 VectorCopy(pmove->origin,a);a[2]=low;
 VectorMA(a,40,dir,b);*wall=VF_TR_Trace(a,b,2);
 if(!VF_TR_Static(wall)||fabs(wall->plane.normal[2])>.2f)return 0;
 /* Approach squarely enough that the capsule and both palms can fit. */
 if(DotProduct(dir,wall->plane.normal)>-.7f)return 0;
 VectorMA(wall->endpos,-8,wall->plane.normal,a);a[2]=high;
 VectorCopy(a,b);b[2]=low;*top=VF_TR_Trace(a,b,2);
 return VF_TR_Static(top)&&top->plane.normal[2]>.7f;
}
static int VF_TR_StartVault(void) {
 vec3_t dir,a,b,target,above;pmtrace_t wall,top,floor,back;float foot,delta,width,eye;int wide;
 if(pmove->onground==-1||(pmove->flags&FL_DUCKING)||pmove->cmd.forwardmove<10)return 0;
 VF_TR_Direction(pmove->angles[1],dir);foot=pmove->origin[2]-36;
 if(!VF_TR_Ledge(dir,&wall,&top,foot+8,foot+62))return 0;
 delta=top.endpos[2]-foot;if(delta<20||delta>60)return 0;
 /* A reverse trace finds the rear face of a thin wall. A broad platform
    gets a distinct step-up onto its top instead of a blind far-side vault. */
 VectorMA(wall.endpos,80,dir,a);a[2]=top.endpos[2]-2;
 VectorMA(wall.endpos,-4,dir,b);b[2]=a[2];back=VF_TR_Trace(a,b,2);
 width=(back.endpos[0]-wall.endpos[0])*dir[0]+(back.endpos[1]-wall.endpos[1])*dir[1];
 wide=back.startsolid||back.allsolid||!VF_TR_Static(&back)||width>64;
 if(!wide&&(width<2||DotProduct(dir,back.plane.normal)<.7f))return 0;
 width=wide?0:(float)((int)(width+.5f));
 /* Check the whole crouched route before committing, including landing. */
 VectorCopy(pmove->origin,a);a[2]=top.endpos[2]+20;
 VectorMA(wall.endpos,wide?32:width+26,dir,target);target[2]=a[2];
 if(!VF_TR_Clear(a,1)||!VF_TR_Clear(target,1))return 0;
 above[0]=pmove->origin[0];above[1]=pmove->origin[1];above[2]=a[2];
 VectorCopy(pmove->origin,b);b[2]-=18;
 if(VF_TR_Trace(b,above,1).fraction<1||VF_TR_Trace(above,target,1).fraction<1)return 0;
 VectorCopy(target,b);b[2]=foot-24;floor=VF_TR_Trace(target,b,1);
 if(floor.startsolid||floor.allsolid||floor.fraction==1||floor.plane.normal[2]<.7f)return 0;
 pmove->iuser4=VF_TR_State(VF_TR_VAULT,pmove->angles[1])|(wide?VF_TR_WIDE:((int)width<<17));pmove->fuser1=VF_TR_TransferTime(pmove->iuser4);
 pmove->vuser3[0]=target[0];pmove->vuser3[1]=target[1];pmove->fuser4=top.endpos[2];
 eye=pmove->origin[2]+pmove->view_ofs[2];VF_TR_Crouch();pmove->view_ofs[2]=eye-pmove->origin[2];
 pmove->onground=-1;VectorClear(pmove->velocity);pmove->oldbuttons|=IN_JUMP;return 1;
}
static int VF_TR_StartHang(void) {
 vec3_t dir,target;pmtrace_t wall,top;float depth;
 if(pmove->onground!=-1||!(pmove->cmd.buttons&IN_JUMP)||pmove->velocity[2]<-450||pmove->usehull!=0)return 0;
 VF_TR_Direction(pmove->angles[1],dir);
 if(!VF_TR_Ledge(dir,&wall,&top,pmove->origin[2]+8,pmove->origin[2]+54))return 0;
 depth=top.endpos[2]-pmove->origin[2];if(depth<26||depth>52)return 0;
 VectorMA(wall.endpos,18,wall.plane.normal,target);target[2]=top.endpos[2]-VF_TR_HANG_DEPTH;
 if(!VF_TR_Clear(target,0)||VF_TR_Trace(pmove->origin,target,0).fraction<1)return 0;
 /* No overhang where the palms grip. */
 {vec3_t a,b;VectorCopy(top.endpos,a);a[2]+=3;VectorMA(a,-6,wall.plane.normal,b);if(VF_TR_Trace(a,b,2).fraction<1)return 0;}
 pmove->iuser4=VF_TR_State(VF_TR_HANG,(float)(atan2(-wall.plane.normal[1],-wall.plane.normal[0])*180/3.141592653589793));
 pmove->vuser3[0]=target[0];pmove->vuser3[1]=target[1];pmove->fuser4=top.endpos[2];pmove->fuser1=.28f;
 VectorCopy(target,pmove->origin);VectorClear(pmove->velocity);pmove->flFallVelocity=0;pmove->oldbuttons|=IN_JUMP;return 1;
}
static int VF_TR_StartClimb(void) {
 vec3_t dir,target,above;float eye=pmove->view_ofs[2];VF_TR_Direction(VF_TR_Yaw(pmove->iuser4),dir);
 target[0]=pmove->vuser3[0]+dir[0]*42;target[1]=pmove->vuser3[1]+dir[1]*42;target[2]=pmove->fuser4+36;
 VectorCopy(pmove->origin,above);above[2]=pmove->fuser4+20;
 if(!VF_TR_Clear(target,0)||VF_TR_Trace(pmove->origin,above,1).fraction<1)return 0;
 target[2]=above[2];if(VF_TR_Trace(above,target,1).fraction<1)return 0;
 pmove->iuser4=VF_TR_State(VF_TR_CLIMB,VF_TR_Yaw(pmove->iuser4));pmove->fuser1=VF_TR_CLIMB_TIME;
 VF_TR_Crouch();pmove->view_ofs[2]=eye;pmove->onground=-1;return 1;
}
static void VF_TR_StartWallJump(void) {
 vec3_t dir;float yaw=VF_TR_Yaw(pmove->iuser4);
 int turned=fabs(VF_TR_Angle(pmove->angles[1]-yaw))>=VF_TR_WALL_JUMP_ANGLE;
 VF_TR_Direction(yaw,dir);
 pmove->iuser4=VF_TR_State(VF_TR_WALL_JUMP,yaw)|(turned?VF_TR_TURNED:0);
 pmove->fuser1=VF_TR_WALL_JUMP_TIME;
 /* Push away from the support, independently of the camera or S direction.
    The ordinary air solver owns gravity, collision and steering. */
 pmove->velocity[0]=-dir[0]*VF_TR_WALL_JUMP_SPEED;
 pmove->velocity[1]=-dir[1]*VF_TR_WALL_JUMP_SPEED;
 pmove->velocity[2]=VF_TR_WALL_JUMP_UP;
 pmove->onground=-1;pmove->flags&=~FL_ONGROUND;pmove->flFallVelocity=0;
 pmove->oldbuttons=pmove->cmd.buttons;
}
static int VF_TR_Hold(void) {
 int phase=VF_TR_Phase(pmove->iuser4),changed=pmove->cmd.buttons^pmove->oldbuttons;
 vec3_t dir,target,a,b;pmtrace_t support;
 pmove->fuser1=max(0,pmove->fuser1-pmove->frametime);
 if(pmove->fuser1<=0)pmove->iuser4&=~VF_TR_RETURNING;
 VF_TR_Direction(VF_TR_Yaw(pmove->iuser4),dir);
 /* Check support every frame: breakable geometry can disappear. */
 a[0]=pmove->vuser3[0]+dir[0]*26;a[1]=pmove->vuser3[1]+dir[1]*26;a[2]=pmove->fuser4+4;
 VectorCopy(a,b);b[2]-=10;support=VF_TR_Trace(a,b,2);
 if(!VF_TR_Static(&support)||support.plane.normal[2]<.7f||fabs(support.endpos[2]-pmove->fuser4)>2){VF_TR_End(.4f);return 0;}
 if(pmove->cmd.buttons&IN_DUCK){pmove->iuser4=VF_TR_State(VF_TR_DROP,VF_TR_Yaw(pmove->iuser4));pmove->fuser1=VF_TR_DROP_TIME;pmove->velocity[2]=-80;return 0;}
 if(changed&pmove->cmd.buttons&IN_JUMP){
  if(pmove->cmd.forwardmove<-10||(pmove->cmd.buttons&IN_BACK)||
     fabs(VF_TR_Angle(pmove->angles[1]-VF_TR_Yaw(pmove->iuser4)))>=VF_TR_WALL_JUMP_ANGLE){
   VF_TR_StartWallJump();return 0;
  }
  if(VF_TR_StartClimb()){pmove->oldbuttons=pmove->cmd.buttons;return 1;}
 }
 if((changed&pmove->cmd.buttons&IN_ATTACK2)||(phase==VF_TR_HANG&&(pmove->cmd.buttons&IN_ATTACK))) {
  phase=phase==VF_TR_HANG?VF_TR_ARMED:VF_TR_HANG;pmove->fuser1=.28f;pmove->iuser4=VF_TR_State(phase,VF_TR_Yaw(pmove->iuser4))|(phase==VF_TR_HANG?VF_TR_RETURNING:0);
 }
 target[0]=pmove->vuser3[0];target[1]=pmove->vuser3[1];
 target[2]=pmove->fuser4-(phase==VF_TR_ARMED?VF_TR_ARMED_DEPTH:VF_TR_HANG_DEPTH);
 /* Smooth the pull-up needed to expose the shooting eye above the ledge. */
 {float dz=target[2]-pmove->origin[2],step=90*pmove->frametime;if(dz>step)dz=step;if(dz<-step)dz=-step;target[2]=pmove->origin[2]+dz;}
 if(!VF_TR_Sweep(target)){VF_TR_End(.4f);return 0;}
 VectorClear(pmove->velocity);pmove->onground=-1;pmove->flFallVelocity=0;pmove->view_ofs[2]=VEC_VIEW+4*max(0,min(1,(pmove->fuser4-pmove->origin[2]-VF_TR_ARMED_DEPTH)/(VF_TR_HANG_DEPTH-VF_TR_ARMED_DEPTH)));
 pmove->oldbuttons=pmove->cmd.buttons;return 1;
}
static int VF_TR_Transfer(void) {
 int phase=VF_TR_Phase(pmove->iuser4);vec3_t dir,target;float remaining=pmove->fuser1;
 float total=VF_TR_TransferTime(pmove->iuser4);
 float elapsed=total-remaining,dt=pmove->frametime;
 VF_TR_Direction(VF_TR_Yaw(pmove->iuser4),dir);
 pmove->flags|=FL_DUCKING;pmove->usehull=1;pmove->view_ofs[2]=VEC_DUCK_VIEW;
 if(phase==VF_TR_VAULT){
  /* Duck toward the planted hand, then recover the standing eye before
     landing. Start/end keep the eye continuous across the hull switch. */
  float t=min(1,max(0,(elapsed+dt)/total));
  float w=t<.25f?t/.25f:t<.42f?1:(.85f-t)/.43f;
  w=max(0,min(1,w));w=w*w*(3-2*w);
  pmove->view_ofs[2]=VEC_VIEW+18-28*w;
 }
 if(phase==VF_TR_CLIMB){
  /* Crouch the collision hull without dropping the eye to a crouched pose.
     Finish at the standing eye relative to the still-crouched origin, so
     vanilla unduck does not add a second camera jump at the end. */
  float t=min(1,max(0,(elapsed+dt)/total));t=t*t*(3-2*t);
  pmove->view_ofs[2]=VEC_VIEW+4+(18-4)*t;
 }
 VectorCopy(pmove->origin,target);
 if(elapsed<total*.4f){
  float t=max(dt,total*.4f-elapsed);target[2]+=(pmove->fuser4+20-target[2])*min(1,dt/t);
 }else{
  float t=max(dt,phase==VF_TR_VAULT?total*.8f-elapsed:remaining);
  float x=pmove->vuser3[0]+(phase==VF_TR_CLIMB?dir[0]*42:0);
  float y=pmove->vuser3[1]+(phase==VF_TR_CLIMB?dir[1]*42:0);
  target[0]+=(x-target[0])*min(1,dt/t);target[1]+=(y-target[1])*min(1,dt/t);
  if(phase==VF_TR_VAULT&&elapsed>=total*.8f){
   vec3_t a,b;pmtrace_t floor;VectorCopy(target,a);a[2]=pmove->fuser4+20;VectorCopy(a,b);b[2]-=120;
   floor=VF_TR_Trace(a,b,1);
   if(!VF_TR_Static(&floor)||floor.plane.normal[2]<.7f){VF_TR_End(.45f);return 0;}
   target[2]+=(floor.endpos[2]-target[2])*min(1,dt/max(dt,remaining));
  }
 }
 if(!VF_TR_Sweep(target)){VF_TR_End(.45f);return 0;}
 VectorClear(pmove->velocity);pmove->flFallVelocity=0;pmove->onground=-1;
 pmove->fuser1=max(0,remaining-dt);pmove->oldbuttons=pmove->cmd.buttons;
 if(pmove->fuser1<=0){
  VF_TR_End(.25f);PM_CatagorizePosition();
  /* Standing clearance is rechecked by vanilla unduck, never forced. */
  if(!(pmove->cmd.buttons&IN_DUCK))PM_UnDuck();
  pmove->velocity[0]=dir[0]*100;pmove->velocity[1]=dir[1]*100;
 }
 return 1;
}
/* Return true only when traversal has consumed movement. Slide uses vanilla
   hull collision, steps, gravity and landing, with reduced ground friction. */
#include "pm_wallrun.inc"
static int PM_VFTraversal(int ladder) {
 int phase=VF_TR_Phase(pmove->iuser4),pressed=pmove->cmd.buttons&~pmove->oldbuttons;float speed;
 if(pmove->dead||pmove->spectator||pmove->iuser1||pmove->movetype!=MOVETYPE_WALK||ladder||pmove->waterlevel>1||(pmove->flags&(FL_ONTRAIN|FL_FROZEN))) {
  if(phase)VF_TR_End(.2f);return 0;
 }
 if(phase==VF_TR_WALL_RUN)return VF_WR_Move();
 if(phase==VF_TR_DROP){pmove->fuser1-=pmove->frametime;if(pmove->fuser1<=0)VF_TR_End(.15f);return 0;}
 if(phase==VF_TR_WALL_JUMP){
  pmove->fuser1=max(0,pmove->fuser1-pmove->frametime);
  /* Holding Space can catch the next ledge; the departure ledge is ignored
     until the hands have released. No animation-length catch lockout. */
  if(pmove->fuser1<=VF_TR_WALL_JUMP_TIME-VF_TR_WALL_JUMP_RELEASE&&VF_TR_StartHang())return VF_TR_Hold();
  if(pmove->onground!=-1||pmove->fuser1<=0)VF_TR_End(0);
  return 0;
 }
 if(VF_TR_Hanging(pmove->iuser4))return VF_TR_Hold();
 if(phase==VF_TR_VAULT||phase==VF_TR_CLIMB)return VF_TR_Transfer();
 if(!phase&&pmove->fuser1<0){pmove->fuser1=min(0,pmove->fuser1+pmove->frametime);return 0;}
 if(!phase){
  if((pressed&IN_JUMP)&&VF_TR_StartVault())return VF_TR_Transfer();
  if(VF_TR_StartHang())return VF_TR_Hold();
  if(VF_WR_Start())return VF_WR_Move();
 }
 speed=(float)sqrt(pmove->velocity[0]*pmove->velocity[0]+pmove->velocity[1]*pmove->velocity[1]);
 if(phase==VF_TR_SLIDE){
  pmove->fuser1-=pmove->frametime;
  if(pmove->fuser1<=0||pmove->onground==-1||!(pmove->cmd.buttons&IN_DUCK)||(pressed&IN_JUMP)||speed<100){VF_TR_End(VF_TR_SLIDE_COOLDOWN);return 0;}
 }else if(!phase&&(pressed&IN_DUCK)&&pmove->onground!=-1&&speed>=VF_TR_SLIDE_MIN_SPEED&&!(pmove->flags&FL_DUCKING)) {
  pmove->iuser4=VF_TR_State(VF_TR_SLIDE,(float)(atan2(pmove->velocity[1],pmove->velocity[0])*180/3.141592653589793));pmove->fuser1=VF_TR_SLIDE_TIME;
  /* Use the earned running momentum; repeated crouches cannot manufacture
     speed. Cap unusually fast approaches before using the low-friction hull. */
  if(speed>VF_TR_SLIDE_MAX_SPEED){pmove->velocity[0]*=VF_TR_SLIDE_MAX_SPEED/speed;pmove->velocity[1]*=VF_TR_SLIDE_MAX_SPEED/speed;speed=VF_TR_SLIDE_MAX_SPEED;}
  VF_TR_Crouch();
 }else return 0;
 /* Limited steering rotates momentum; releasing Ctrl brakes normally. */
 if(fabs(pmove->cmd.forwardmove)+fabs(pmove->cmd.sidemove)>5) {
  float yaw=(float)(atan2(pmove->velocity[1],pmove->velocity[0])*180/3.141592653589793);
  float wish=pmove->angles[1]+(float)(atan2(-pmove->cmd.sidemove,pmove->cmd.forwardmove)*180/3.141592653589793);
  float change=VF_TR_Angle(wish-yaw),limit=18*pmove->frametime;vec3_t dir;
  change=max(-limit,min(limit,change));VF_TR_Direction(yaw+change,dir);
  pmove->velocity[0]=dir[0]*speed;pmove->velocity[1]=dir[1]*speed;
  pmove->iuser4=VF_TR_State(VF_TR_SLIDE,yaw+change);
 }
 pmove->cmd.forwardmove=pmove->cmd.sidemove=pmove->cmd.upmove=0;return 0;
}
