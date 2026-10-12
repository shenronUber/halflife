/* Full shared Valve movement solver with controlled solid AABB geometry.
   Runs server and client frames against identical collision worlds. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "mathlib.h"
#include "const.h"
#include "usercmd.h"
#include "pm_defs.h"
#include "pm_movevars.h"
#define SND_STOP (1<<5) /* GoldSrc sound protocol flag, as in pm_shared.c. */
#include "../../game_shared/vf_traversal.h"
extern playermove_t* pmove;
void PM_Init(playermove_t*);void PM_Move(playermove_t*,int);
static playermove_t player,before,client;
static movevars_t variables;
static float boxes[8][6];static int count,checks,failures;
static void expect(int good,const char* name){checks++;if(!good){failures++;printf("FAIL %s phase=%d pos=%g,%g,%g vel=%g,%g,%g\n",name,VF_TR_Phase(player.iuser4),player.origin[0],player.origin[1],player.origin[2],player.velocity[0],player.velocity[1],player.velocity[2]);}}
static pmtrace_t trace(float* start,float* end,int flags,int ignored){
 pmtrace_t result;int box,axis;float extent[3];
 memset(&result,0,sizeof(result));result.fraction=1;result.ent=-1;
 for(axis=0;axis<3;axis++){result.endpos[axis]=end[axis];extent[axis]=pmove->player_maxs[pmove->usehull][axis];}
 for(box=0;box<count;box++){
  float enter=0,leave=1;int normal=-1,sign=0,inside=1,miss=0;
  for(axis=0;axis<3;axis++){
   float lo=boxes[box][axis]-extent[axis],hi=boxes[box][axis+3]+extent[axis],delta=end[axis]-start[axis],a,b;
   if(start[axis]<=lo+.001f||start[axis]>=hi-.001f)inside=0;
   if(fabs(delta)<.000001f){if(start[axis]<=lo||start[axis]>=hi)miss=1;continue;}
   a=(lo-start[axis])/delta;b=(hi-start[axis])/delta;
   if(a>b){float t=a;a=b;b=t;}
   if(a>enter){enter=a;normal=axis;sign=delta>0?-1:1;}
   if(b<leave)leave=b;
  }
  if(miss)continue;
  if(inside){result.startsolid=1;result.allsolid=1;result.fraction=0;result.ent=0;memcpy(result.endpos,start,sizeof(vec3_t));return result;}
  if(enter<=leave&&enter<result.fraction&&normal>=0&&leave>=0&&enter>=0){
   float delta=fabs(end[normal]-start[normal]);enter=fmaxf(0,enter-.03125f/delta);
   result.fraction=enter;result.ent=0;memset(result.plane.normal,0,sizeof(vec3_t));result.plane.normal[normal]=(float)sign;
   for(axis=0;axis<3;axis++)result.endpos[axis]=start[axis]+enter*(end[axis]-start[axis]);
  }
 }
 return result;
}
static int position(float* p,pmtrace_t* tr){pmtrace_t t=trace(p,p,0,-1);if(tr)*tr=t;return t.startsolid?0:-1;}
static int contents(float* p,int* c){if(c)*c=CONTENTS_EMPTY;return CONTENTS_EMPTY;}
static int file_size(char* s){return 0;}
static byte* load_file(char* s,int h,int* n){return NULL;}
static const char* info(const char* s,const char* k){return !strcmp(k,"hl")?"1":"0";}
static void print(char* fmt,...){ }
static void stuck(int e,pmtrace_t* t){ }
static double now(void){return 10;}
static int32 random_long(int32 a,int32 b){return a;}
static float random_float(float a,float b){return a;}
static const char* texture(int ground,float* a,float* b){return "CONCRETE";}
static int starts[2],stops[2],steps[2],badSound;
static void sound(int c,const char* s,float v,float a,int f,int p){
 int side=pmove->server?1:0;
 if(!strcmp(s,VF_TR_SLIDE_SOUND)){
  if(c!=CHAN_BODY||fabs(v-.65f)>.001f||a!=ATTN_NORM||p!=PITCH_NORM)badSound++;
  if(f&SND_STOP)stops[side]++;else starts[side]++;
 }else if(!strncmp(s,"player/pl_step",14))steps[side]++;
}
static int model_type(struct model_s* m){return 0;}
static void reset(float x,float y,float z){
 memset(starts,0,sizeof(starts));memset(stops,0,sizeof(stops));memset(steps,0,sizeof(steps));badSound=0;
 memset(&player,0,sizeof(player));memset(&variables,0,sizeof(variables));count=1;
 boxes[0][0]=boxes[0][1]=-20000;boxes[0][2]=-64;boxes[0][3]=boxes[0][4]=20000;boxes[0][5]=0;
 player.origin[0]=x;player.origin[1]=y;player.origin[2]=z;player.usehull=0;player.movetype=MOVETYPE_WALK;player.onground=-1;player.maxspeed=320;player.friction=1;player.view_ofs[2]=28;player.multiplayer=1;
 player.movevars=&variables;variables.gravity=800;variables.friction=4;variables.edgefriction=2;variables.accelerate=10;variables.airaccelerate=10;variables.stepsize=18;variables.stopspeed=100;variables.maxvelocity=2000;variables.rollspeed=200;
 player.numphysent=1;player.physents[0].movetype=MOVETYPE_PUSH;player.physents[0].solid=SOLID_BSP;
 player.player_mins[0][0]=player.player_mins[0][1]=-16;player.player_mins[0][2]=-36;player.player_maxs[0][0]=player.player_maxs[0][1]=16;player.player_maxs[0][2]=36;
 player.player_mins[1][0]=player.player_mins[1][1]=-16;player.player_mins[1][2]=-18;player.player_maxs[1][0]=player.player_maxs[1][1]=16;player.player_maxs[1][2]=18;
 player.PM_PlayerTrace=trace;player.PM_TestPlayerPosition=position;player.PM_PointContents=contents;player.PM_Info_ValueForKey=info;player.COM_FileSize=file_size;player.COM_LoadFile=load_file;
 player.Con_DPrintf=player.Con_Printf=print;player.Sys_FloatTime=now;player.PM_StuckTouch=stuck;player.RandomLong=random_long;player.RandomFloat=random_float;player.PM_TraceTexture=texture;player.PM_PlaySound=sound;player.PM_GetModelType=model_type;
}
static void block(float x0,float y0,float z0,float x1,float y1,float z1){float* b=boxes[count++];b[0]=x0;b[1]=y0;b[2]=z0;b[3]=x1;b[4]=y1;b[5]=z1;}
static void tick(int msec,int buttons,float yaw,float forward,float side){
 int i;player.cmd.msec=(byte)msec;player.cmd.buttons=(unsigned short)buttons;player.cmd.viewangles[1]=yaw;player.cmd.forwardmove=forward;player.cmd.sidemove=side;
 before=player;PM_Move(&player,1);client=before;PM_Move(&client,0);
 expect(client.iuser4==player.iuser4&&fabs(client.fuser1-player.fuser1)<.00001f,"server/client state parity");
 for(i=0;i<3;i++)expect(fabs(client.origin[i]-player.origin[i])<.00001f&&fabs(client.velocity[i]-player.velocity[i])<.00001f,"server/client movement parity");
 pmove=&player;
}
/* Simulate the fields carried by PLAYER save data, preserving the ammo lane.
   Continue both solvers after the round trip, including a vanished ledge. */
static void roundtrip(void){
 int state=player.iuser4;float remaining=player.fuser1;
 float anchor[3]={player.vuser3[0],player.vuser3[1],player.fuser4};
 expect(VF_TR_SaveValid(state,remaining,anchor),"current state is serializable");
 player.vuser3[2]=73;player.iuser4=0;player.fuser1=0;player.fuser4=0;
 player.vuser3[0]=player.vuser3[1]=0;
 player.iuser4=state;player.fuser1=remaining;
 player.vuser3[0]=anchor[0];player.vuser3[1]=anchor[1];player.fuser4=anchor[2];
 expect(player.vuser3[2]==73,"traversal restore preserves ammo lane");
}
int main(void){
 int ms,i,frames;float start,eye,lastEye,distance;
 reset(0,0,36.03125f);PM_Init(&player);
 for(ms=8;ms<=33;ms=ms==8?16:ms==16?33:34){
  reset(-28,0,36.03125f);block(0,-128,0,24,128,48);tick(ms,IN_JUMP,0,320,0);expect(VF_TR_Phase(player.iuser4)==VF_TR_VAULT,"low obstacle vault");
  roundtrip();
  frames=1000/ms;for(i=0;i<frames;i++)tick(ms,0,0,0,0);expect(VF_TR_Phase(player.iuser4)==0&&player.origin[0]>48,"vault reaches far side");
  expect(player.origin[2]<37,"thin-wall vault lands automatically on far floor");
  reset(-28,0,36.03125f);block(0,-128,0,256,128,48);tick(ms,IN_JUMP,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_VAULT&&(player.iuser4&VF_TR_WIDE),"broad platform selects step-up");roundtrip();
  lastEye=player.origin[2]+player.view_ofs[2];
  for(i=0;i<1100/ms;i++){
   tick(ms,0,0,0,0);eye=player.origin[2]+player.view_ofs[2];
   if(VF_TR_Phase(player.iuser4)==VF_TR_VAULT){expect(player.view_ofs[2]>=17.99f&&player.view_ofs[2]<=46.01f,"vault eye follows crouch within bounded height");expect(fabs(eye-lastEye)<9.f,"vault eye has no hull-switch discontinuity");}
   lastEye=eye;
  }
  expect(player.origin[0]>16&&player.origin[0]<100&&player.origin[2]>83&&player.origin[2]<85,"step-up ends standing on platform, not beyond it");
  reset(-28,0,36.03125f);block(0,-128,0,40,128,48);tick(ms,IN_JUMP,0,320,0);
  expect(!(player.iuser4&VF_TR_WIDE)&&VF_TR_VaultSpan(player.iuser4)==40,"thin-wall rear face measures actual width");
  expect(fabs(player.origin[2]+player.view_ofs[2]-64.03125f)<8.f,"vault enters crouched hull without an eye-height jump");
  for(i=0;i<1100/ms;i++)tick(ms,0,0,0,0);
  expect(player.origin[0]>64&&player.origin[2]<37,"wider thin-wall vault reaches clear far floor");
  reset(238,0,54);block(256,-128,0,512,128,96);tick(ms,IN_JUMP,0,0,0);expect(VF_TR_Phase(player.iuser4)==VF_TR_HANG,"airborne ledge catch");
  roundtrip();
  for(i=0;i<1000/ms;i++)tick(ms,0,0,0,0);expect(VF_TR_Phase(player.iuser4)==VF_TR_HANG,"no automatic climb");
  tick(ms,IN_ATTACK2,180,0,0);roundtrip();
  while(player.fuser1>0){
   expect(!VF_TR_CanFire(player.iuser4,player.fuser1,180),"predicted drawing frame cannot fire");
   tick(ms,IN_ATTACK,180,0,0);
  }
  expect(VF_TR_CanFire(player.iuser4,player.fuser1,180),"predicted shot unlocks when draw completes");
  expect(VF_TR_Phase(player.iuser4)==VF_TR_ARMED,"armed hanging");
  expect(!VF_TR_CanFire(player.iuser4,0,0)&&!VF_TR_CanFire(player.iuser4,0,360),"wall-facing fire is blocked across wrap");
  expect(!VF_TR_CanFire(player.iuser4,0,74.9f)&&VF_TR_CanFire(player.iuser4,0,75.1f),"right guard cone boundary");
  expect(!VF_TR_CanFire(player.iuser4,0,-74.9f)&&VF_TR_CanFire(player.iuser4,0,-75.1f),"left guard cone boundary");
  expect(!VF_TR_CanFire(player.iuser4,.1f,180),"drawing cannot fire");
  expect(VF_TR_AimDeploy(0)==0&&VF_TR_AimDeploy(75)==1&&VF_TR_AimDeploy(60)>.49f&&VF_TR_AimDeploy(60)<.51f,"guard deploy transition");
  start=player.origin[0];for(i=0;i<8;i++){tick(ms,IN_ATTACK,(float)i*45,0,0);expect(fabs(player.origin[0]-start)<.001f&&VF_TR_Yaw(player.iuser4)==0,"360 aim preserves anchor");}
  tick(ms,0,0,0,0);eye=player.origin[2]+player.view_ofs[2];tick(ms,IN_JUMP,0,0,0);expect(VF_TR_Phase(player.iuser4)==VF_TR_CLIMB,"explicit climb");
  expect(fabs(player.origin[2]+player.view_ofs[2]-eye)<.01f,"climb preserves eye height on entry");
  roundtrip();
  lastEye=player.origin[2]+player.view_ofs[2];
  for(i=0;i<1200/ms;i++){
   tick(ms,0,0,0,0);eye=player.origin[2]+player.view_ofs[2];
   if(VF_TR_Phase(player.iuser4)==VF_TR_CLIMB){expect(eye>=lastEye-.01f,"climbing eye rises continuously");expect(eye-lastEye<8.f,"climbing eye has no crouch discontinuity");}
   lastEye=eye;
  }
  expect(VF_TR_Phase(player.iuser4)==0&&player.origin[0]>272&&player.origin[2]>131,"climb onto standing floor");
  /* Wall-to-wall transfer, with the second lip 64 units higher. Exercise
     both triggers through the real air solver and identical prediction. */
  for(frames=0;frames<2;frames++){
   reset(238,0,54);block(256,-128,0,512,128,96);block(-160,-128,0,96,128,160);
   tick(ms,IN_JUMP,0,0,0);tick(ms,0,0,0,0);
   eye=player.origin[2]+player.view_ofs[2];
   tick(ms,IN_JUMP|(frames?0:IN_BACK),frames?180:0,frames?0:-320,0);
   expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_JUMP,"fresh jump pushes off hanging wall");
   expect(!!(player.iuser4&VF_TR_TURNED)==frames,"look-back and straight departures choose different clips");
   expect(player.velocity[0]<-260&&player.velocity[2]>300,"wall jump launches outward and upward");
   expect(fabs(player.origin[2]+player.view_ofs[2]-eye)<12,"departure camera remains continuous");
   expect(VF_TR_BusyHands(player.iuser4)&&!VF_TR_CanFire(player.iuser4,player.fuser1,180)&&VF_TR_NoReload(player.iuser4),"push-off occupies both hands");
   roundtrip();
   for(i=0;i<750/ms&&VF_TR_Phase(player.iuser4)==VF_TR_WALL_JUMP;i++){
    tick(ms,IN_JUMP,180,0,0);
    if(player.fuser1>VF_TR_WALL_JUMP_TIME-VF_TR_WALL_JUMP_RELEASE)
     expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_JUMP,"release interval prevents immediate recatch");
   }
   expect(VF_TR_Phase(player.iuser4)==VF_TR_HANG&&fabs(player.fuser4-160)<.04f&&player.origin[0]>96&&player.origin[0]<116,"holding jump catches the higher opposite ledge before the clip ends");
   roundtrip();
   for(i=0;i<400/ms;i++)tick(ms,IN_JUMP,180,0,0);
   expect(VF_TR_Phase(player.iuser4)==VF_TR_HANG,"held jump does not climb or launch again after recatch");
  }
  reset(238,0,54);block(256,-128,0,512,128,96);
  tick(ms,IN_JUMP,0,0,0);
  for(i=0;i<400/ms;i++)tick(ms,IN_JUMP|IN_BACK,0,-320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_HANG,"held catch button cannot also trigger wall jump");
  tick(ms,0,0,0,0);tick(ms,IN_JUMP,100,0,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_JUMP,"look-back angle boundary triggers push-off");
  for(i=0;i<1800/ms;i++)tick(ms,IN_JUMP,180,0,0);
  expect(VF_TR_Phase(player.iuser4)==0&&player.origin[2]<37,"wall jump resumes ordinary flight and landing without a second impulse");
  reset(238,0,54);block(256,-128,0,512,128,96);
  tick(ms,IN_JUMP,0,0,0);tick(ms,IN_ATTACK2,180,0,0);tick(ms,IN_JUMP,180,0,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_JUMP,"armed hanging can push off during holstering");
  player.dead=1;tick(ms,0,180,0,0);expect(VF_TR_Phase(player.iuser4)==0,"death clears wall-jump state");
  reset(238,0,54);block(256,-128,0,512,128,96);block(100,-128,108,254,128,144);
  tick(ms,IN_JUMP,0,0,0);tick(ms,0,0,0,0);tick(ms,IN_JUMP|IN_BACK,0,-320,0);
  for(i=0;i<400/ms;i++)tick(ms,0,180,0,0);
  expect(player.origin[2]<=72.01f,"wall jump respects a low ceiling");
  reset(238,0,54);block(256,-128,0,512,128,96);tick(ms,IN_JUMP,0,0,0);tick(ms,0,0,0,0);tick(ms,IN_DUCK,0,0,0);expect(VF_TR_Phase(player.iuser4)==VF_TR_DROP&&player.velocity[2]<0,"release animation falls with vanilla gravity");
  for(i=0;i<400/ms;i++)tick(ms,0,0,0,0);expect(VF_TR_Phase(player.iuser4)==0,"release returns to original animation");
  reset(238,0,54);block(256,-128,0,512,128,96);block(232,-128,112,520,128,144);tick(ms,IN_JUMP,0,0,0);tick(ms,0,0,0,0);tick(ms,IN_JUMP,0,0,0);expect(VF_TR_Phase(player.iuser4)==VF_TR_HANG,"ceiling refuses climb");
  reset(0,0,36.03125f);player.velocity[0]=300;tick(ms,IN_DUCK,0,0,0);expect(VF_TR_Phase(player.iuser4)==VF_TR_SLIDE,"running slide");
  expect(player.velocity[0]<=300,"slide preserves earned speed instead of giving an impulse");
  expect(!VF_TR_BusyHands(player.iuser4)&&!VF_TR_HideWeapon(player.iuser4,player.fuser1)&&!VF_TR_NoReload(player.iuser4),"sliding keeps both hands available for combat and reload");
  for(i=0;i<8;i++)expect(VF_TR_CanFire(player.iuser4,player.fuser1,(float)i*45),"sliding can fire in every aim direction");
  roundtrip();
  start=player.origin[0];for(i=0;i<(int)(1400/ms);i++)tick(ms,IN_DUCK,0,0,0);
  distance=player.origin[0]-start;
  expect(VF_TR_Phase(player.iuser4)==0&&distance>250&&distance<380,"short slide travels about 320 units at running speed");
  for(i=0;i<1500/ms;i++)tick(ms,IN_DUCK,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"holding crouch never automatically starts another slide");
  reset(0,0,36.03125f);player.velocity[0]=VF_TR_SLIDE_MIN_SPEED-1;tick(ms,IN_DUCK,0,0,0);
  expect(VF_TR_Phase(player.iuser4)==0,"below minimum speed is ordinary crouch");
  reset(0,0,36.03125f);player.velocity[0]=VF_TR_SLIDE_MIN_SPEED;tick(ms,IN_DUCK,0,0,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_SLIDE,"minimum speed boundary can slide");
  tick(ms,0,0,0,0);expect(VF_TR_Phase(player.iuser4)==0&&player.fuser1<-.8f,"early release starts full recovery buffer");
  roundtrip();
  for(i=0;i<600/ms;i++){
   player.velocity[0]=320;tick(ms,i%2?0:IN_DUCK,0,320,0);
   expect(VF_TR_Phase(player.iuser4)==0,"crouch spam cannot bypass recovery even at running speed");
  }
  while(player.fuser1<0)tick(ms,0,0,320,0);
  tick(ms,0,0,320,0);player.velocity[0]=320;tick(ms,IN_DUCK,0,0,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_SLIDE,"fresh press after recovery may slide again");
  tick(ms,IN_JUMP,0,0,0);expect(VF_TR_Phase(player.iuser4)==0&&player.velocity[2]>240,"jump cancels slide with ordinary jump");
  reset(0,0,36.03125f);player.velocity[0]=800;tick(ms,IN_DUCK,0,0,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_SLIDE&&player.velocity[0]<=VF_TR_SLIDE_MAX_SPEED,"fast approaches are capped to bound slide distance");
  reset(0,0,36.03125f);tick(ms,IN_DUCK,0,0,0);expect(VF_TR_Phase(player.iuser4)==0,"stationary duck is ordinary crouch");
  reset(0,0,36.03125f);tick(ms,IN_JUMP,0,0,0);expect(player.velocity[2]>240&&VF_TR_Phase(player.iuser4)==0,"ordinary Half-Life jump");
  reset(0,0,512);for(i=0;i<1500/ms;i++)tick(ms,0,0,0,0);expect(VF_TR_Phase(player.iuser4)==0&&player.origin[2]<37,"ordinary high fall retains solver");
  reset(238,0,54);block(256,-128,0,512,128,96);tick(ms,IN_JUMP,0,0,0);roundtrip();
  count=1;tick(ms,0,0,0,0);expect(VF_TR_Phase(player.iuser4)==0,"missing restored support releases hang");
  /* Run both sound callbacks and silent prediction replays. The cue must
     start once and stop on the same frame as each traversal exit. */
  reset(0,0,36.03125f);player.runfuncs=1;player.velocity[0]=320;tick(ms,IN_DUCK,0,0,0);
  for(i=0;i<200/ms;i++)tick(ms,IN_DUCK,0,0,0);
  expect(starts[0]==1&&starts[1]==1&&stops[0]==0&&stops[1]==0&&!badSound,"slide cue starts once in server and prediction");
  expect(steps[0]==0&&steps[1]==0,"sliding replaces footsteps");
  tick(ms,IN_DUCK|IN_JUMP,0,0,0);
  expect(stops[0]==1&&stops[1]==1&&player.velocity[2]>240,"jump stops slide sound in same movement frame");
  reset(0,0,36.03125f);player.runfuncs=1;player.velocity[0]=320;tick(ms,IN_DUCK,0,0,0);tick(ms,0,0,0,0);
  expect(starts[0]==1&&starts[1]==1&&stops[0]==1&&stops[1]==1,"crouch release stops slide cue");
  reset(0,0,36.03125f);player.runfuncs=1;player.velocity[0]=320;tick(ms,IN_DUCK,0,0,0);
  for(i=0;i<1400/ms;i++)tick(ms,IN_DUCK,0,0,0);
  expect(starts[0]==1&&starts[1]==1&&stops[0]==1&&stops[1]==1,"full duration starts and stops only once");
  reset(0,0,36.03125f);player.runfuncs=1;player.velocity[0]=320;tick(ms,IN_DUCK,0,0,0);player.dead=1;tick(ms,IN_DUCK,0,0,0);
  expect(stops[0]==1&&stops[1]==1,"death interrupts slide cue");
  reset(0,0,36.03125f);player.velocity[0]=320;tick(ms,IN_DUCK,0,0,0);tick(ms,IN_JUMP,0,0,0);
  expect(starts[0]==0&&starts[1]==0&&stops[0]==0&&stops[1]==0,"replayed commands do not emit or stop audio");
  printf("PASS movement frame=%dms\n",ms);
 }
 {float anchor[3]={1,2,3};
  expect(VF_TR_SaveValid(0,0,anchor),"old save defaults to normal");
  expect(!VF_TR_SaveValid(7|VF_TR_WIDE,0,anchor)&&!VF_TR_SaveValid(1<<17,0,anchor),"invalid packed save flags rejected");
  expect(!VF_TR_SaveValid(VF_TR_State(VF_TR_ARMED,0),1,anchor),"excessive draw duration rejected");
  expect(VF_TR_SaveValid(VF_TR_State(VF_TR_WALL_JUMP,359.9f)|VF_TR_TURNED,VF_TR_WALL_JUMP_TIME,anchor),"turned wall jump fits saved and network state");
  expect(!VF_TR_SaveValid(VF_TR_State(VF_TR_WALL_JUMP,0),VF_TR_WALL_JUMP_TIME+.1f,anchor),"excessive wall-jump duration rejected");
  expect(!VF_TR_SaveValid(VF_TR_State(VF_TR_SLIDE,0),-1,anchor),"negative active duration rejected");
  anchor[1]=NAN;expect(!VF_TR_SaveValid(VF_TR_HANG,0,anchor),"invalid saved anchor rejected");
 }
 printf("Traversal movement: %d checks, %d failures\n",checks,failures);return failures?1:0;
}
