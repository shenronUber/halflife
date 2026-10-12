/* Real shared solver, controlled geometry, server/prediction parity.
   Reuse the existing collision fixture and run its regressions as well. */
#define main traversal_regressions
#include "traversal_movement_test.c"
#undef main
#include "../../game_shared/vf_static_brush.h"
static pmtrace_t modular_trace(float* start,float* end,int flags,int ignored){
 pmtrace_t result=trace(start,end,flags,ignored);
 if(result.fraction<1&&fabs(result.plane.normal[2])<.2f)result.ent=1;
 return result;
}
static void wallrun_setup(int right,float speed) {
 reset(0,0,128);player.velocity[0]=speed;player.vuser3[2]=73;
 if(right)block(-4096,-64,0,4096,-18,512);
 else block(-4096,18,0,4096,64,512);
}
/* Infinite vertical brush plane supplements the real floor fixture. The
   world hull remains axis-aligned, as in GoldSrc, even on oblique walls. */
static float obliqueYaw;
static pmtrace_t oblique_trace(float* start,float* end,int flags,int ignored) {
 pmtrace_t result=trace(start,end,flags,ignored);vec3_t normal;float extent,a,b,f;int axis;
 normal[0]=(float)sin(obliqueYaw*3.141592653589793/180);normal[1]=-(float)cos(obliqueYaw*3.141592653589793/180);normal[2]=0;
 extent=fabs(normal[0])*pmove->player_maxs[pmove->usehull][0]+fabs(normal[1])*pmove->player_maxs[pmove->usehull][1];
 a=start[0]*normal[0]+start[1]*normal[1]-extent;b=end[0]*normal[0]+end[1]*normal[1]-extent;
 if(a<-.001f){result.startsolid=result.allsolid=1;result.fraction=0;result.ent=0;memcpy(result.endpos,start,sizeof(vec3_t));return result;}
 if(b<0&&a>=0){
  f=fmaxf(0,(a-.03125f)/(a-b));
  if(f<result.fraction){result.fraction=f;result.ent=0;memcpy(result.plane.normal,normal,sizeof(vec3_t));
   for(axis=0;axis<3;++axis)result.endpos[axis]=start[axis]+f*(end[axis]-start[axis]);
  }
 }
 return result;
}
static void oblique_setup(float yaw) {
 float radians=yaw*(float)(3.141592653589793/180),nx=(float)sin(radians),ny=-(float)cos(radians);
 float distance=16*(fabs(nx)+fabs(ny))+2;
 reset(nx*distance,ny*distance,128);obliqueYaw=yaw;player.PM_PlayerTrace=oblique_trace;
 player.velocity[0]=(float)cos(radians)*320;player.velocity[1]=(float)sin(radians)*320;player.velocity[2]=80;
}
int main(void) {
 int ms,i,right,priorFailures;float x,z,entry;
 if(traversal_regressions())return 1;
 priorFailures=failures;
 for(ms=8;ms<=33;ms=ms==8?16:ms==16?33:34)for(right=0;right<2;++right){
  entry=right?300.f:60.f;
  wallrun_setup(right,320);tick(ms,IN_FORWARD,entry,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"brushing a wall while looking at it cannot attach without jump input");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"jumping parallel to a nearby wall is not intentional attachment");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,right?60:300,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"jumping while looking away from wall stays ordinary");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,right?331:29,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"a shallow wall-facing look no longer needs the old thirty degree entry cone");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,right?359:1,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"one degree into the wall side of its tangent is sufficient");
  wallrun_setup(right,320);count=1;
  if(right)block(-128,-64,0,128,-18,256);else block(-128,18,0,128,64,256);
  player.cmd.viewangles[0]=-89;tick(ms,IN_FORWARD|IN_JUMP,right?359:1,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"angular intent does not require an eye ray to hit the finite visible wall");
  for(i=0;i<2;++i){
   wallrun_setup(right,320);player.cmd.viewangles[0]=i?89:-89;tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);
   expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"entry uses horizontal intent independently of looking up or down");
  }
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,right?1:359,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"a shallow look on the away side of the tangent stays an ordinary jump");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP|(right?IN_MOVERIGHT:IN_MOVELEFT),0,320,right?320:-320);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"forward and strafe into either wall attaches while looking parallel");
  x=player.origin[0];tick(ms,IN_FORWARD,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN&&player.origin[0]>x,"strafe is only needed for entry and does not steer the stored run heading");
  wallrun_setup(right,320);player.velocity[0]=-320;
  tick(ms,IN_FORWARD|IN_JUMP|(right?IN_MOVELEFT:IN_MOVERIGHT),180,320,right?-320:320);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN&&player.velocity[0]<-300,"turning the run around reverses the required view-relative strafe key");
  wallrun_setup(right,320);player.cmd.viewangles[0]=-89;
  tick(ms,IN_FORWARD|IN_JUMP|(right?IN_MOVERIGHT:IN_MOVELEFT),right?60:300,320,right?320:-320);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"view-relative strafe into the wall supplies intent even while looking away and upward");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP|(right?IN_MOVELEFT:IN_MOVERIGHT),0,320,right?-320:320);
  expect(VF_TR_Phase(player.iuser4)==0,"strafe away from the wall cannot supply attachment intent");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,0,320,right?320:-320);
  expect(VF_TR_Phase(player.iuser4)==0,"lateral momentum without the directional input does not supply strafe intent");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP|(right?IN_MOVERIGHT:IN_MOVELEFT),0,320,right?-320:320);
  expect(VF_TR_Phase(player.iuser4)==0,"the strafe button must agree with its signed movement command");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|(right?IN_MOVERIGHT:IN_MOVELEFT),0,320,right?320:-320);
  expect(VF_TR_Phase(player.iuser4)==0,"pushing against a wall without jumping cannot attach");
  wallrun_setup(right,320);tick(ms,IN_JUMP|(right?IN_MOVERIGHT:IN_MOVELEFT),0,0,right?320:-320);
  expect(VF_TR_Phase(player.iuser4)==0,"jump and strafe without forward input cannot attach");
  wallrun_setup(right,320);count=1;tick(ms,IN_FORWARD|IN_JUMP|(right?IN_MOVERIGHT:IN_MOVELEFT),0,320,right?320:-320);
  expect(VF_TR_Phase(player.iuser4)==0,"jump and inward input still require a real supporting wall");
  reset(0,0,36.03125f);player.velocity[0]=320;
  if(right)block(-4096,-64,0,4096,-18,512);else block(-4096,18,0,4096,64,512);
  tick(ms,IN_FORWARD,0,320,0);
  tick(ms,IN_FORWARD|IN_JUMP|(right?IN_MOVERIGHT:IN_MOVELEFT),0,320,right?320:-320);
  tick(ms,IN_FORWARD|IN_JUMP|(right?IN_MOVERIGHT:IN_MOVELEFT),0,320,right?320:-320);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"a real grounded takeoff with inward strafe attaches on either wall");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"jump plus wall-facing look enters on either side");
  expect(!VF_TR_BusyHands(player.iuser4)&&!VF_TR_NoReload(player.iuser4)&&VF_TR_CanFire(player.iuser4,0,180),"wall running keeps weapon policy available");
  expect(player.vuser3[2]==73,"wall running never writes ammo lane");roundtrip();
  x=player.origin[0];z=player.origin[2];
  for(i=0;i<2000/ms;++i)tick(ms,IN_FORWARD|IN_JUMP,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN&&player.origin[0]-x>590,"continuous forward runs beyond ordinary traversal duration");
  expect(fabs(player.origin[2]-z)<.001f,"supported wall run holds height");
  expect(player.origin[1]>(right?-18.f:-.1f)&&player.origin[1]<(right?.1f:18.f),"hull never penetrates wall");
  for(i=0;i<5;++i){
   float view=i==0?89.f:i==1?90.f:i==2?270.f:i==3?359.f:0.f;
   player.cmd.viewangles[0]=i&1?89.f:-89.f;tick(ms,IN_FORWARD|IN_JUMP,view,320,0);
   expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN&&player.velocity[0]>300&&fabs(player.velocity[1])<25,
          "free yaw through both ninety-degree limits and full pitch keeps the original run direction");
  }
  player.cmd.viewangles[0]=0;
  tick(ms,0,0,0,0);expect(VF_TR_Phase(player.iuser4)==0&&player.velocity[2]<0&&player.origin[2]<z,"releasing forward falls on the same command");
  tick(ms,IN_FORWARD,0,320,0);expect(VF_TR_Phase(player.iuser4)==0,"release recovery prevents immediate reattachment");
  wallrun_setup(right,VF_WR_MIN_SPEED-1);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"walking below threshold cannot wall run");
  wallrun_setup(right,VF_WR_MIN_SPEED);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"minimum speed boundary enters wall run");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);count=1;tick(ms,IN_FORWARD,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==0&&player.velocity[2]<0,"removed support immediately releases wall run");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);tick(ms,IN_FORWARD|IN_DUCK,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"crouch cancels wall run");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);player.dead=1;tick(ms,IN_FORWARD,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"death clears wall run");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);player.movetype=MOVETYPE_NOCLIP;tick(ms,IN_FORWARD,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"noclip clears wall run");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);tick(ms,IN_FORWARD,0,320,0);
  player.cmd.viewangles[0]=-35;tick(ms,IN_FORWARD|IN_JUMP,right?90:270,320,0);
  expect(VF_TR_Phase(player.iuser4)==0&&player.velocity[2]>400,"fresh jump gets upward look-directed impulse");
  expect((right?player.velocity[1]:-player.velocity[1])>250,"bounce follows look away toward opposite wall");
  expect((right?player.velocity[1]:-player.velocity[1])>=VF_WR_JUMP_OUT-1,"bounce always clears its support");
  wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);tick(ms,IN_FORWARD,0,320,0);
  tick(ms,IN_FORWARD|IN_JUMP,right?270:90,320,0);
  expect((right?player.velocity[1]:-player.velocity[1])>=VF_WR_JUMP_OUT-1,"looking into wall still guarantees outward clearance");
  wallrun_setup(right,320);count=1;
  if(right)block(-4096,-64,0,64,-18,512);else block(-4096,18,0,64,64,512);
  tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);
  for(i=0;i<500/ms;++i)tick(ms,IN_FORWARD,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==0&&player.velocity[2]<0,"wall endpoint restores gravity");
  wallrun_setup(right,320);block(80,-128,0,112,128,512);
  tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);
  for(i=0;i<500/ms;++i)tick(ms,IN_FORWARD,0,320,0);
  expect(player.origin[0]<=64.1f&&VF_TR_Phase(player.iuser4)==0,"perpendicular obstacle cannot be run through");
  reset(0,0,36.03125f);player.velocity[0]=320;block(-4096,18,0,4096,64,512);tick(ms,IN_FORWARD,0,320,0);
  expect(VF_TR_Phase(player.iuser4)==0,"running on ground beside wall remains ordinary");
  // Actual takeoff, not just a pre-seeded airborne fixture.
  tick(ms,IN_FORWARD|IN_JUMP,60,320,0);tick(ms,IN_FORWARD|IN_JUMP,60,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"ordinary running jump can attach with held Space");
  // Two real wall contacts joined by flight, with no reseeding in between.
  reset(0,-82,128);player.velocity[0]=320;
  block(-4096,-128,0,4096,-100,512);block(-4096,100,0,4096,128,512);
  tick(ms,IN_FORWARD|IN_JUMP,315,320,0);tick(ms,IN_FORWARD,315,320,0);tick(ms,IN_FORWARD|IN_JUMP,45,320,0);
  for(i=0;i<1000/ms && VF_TR_Phase(player.iuser4)!=VF_TR_WALL_RUN;++i)tick(ms,IN_FORWARD|IN_JUMP,45,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN&&player.origin[1]>70,"look-directed bounce chains into opposite wall run");
  tick(ms,IN_FORWARD,45,320,0);tick(ms,IN_FORWARD|IN_JUMP,315,320,0);
  for(i=0;i<1000/ms && VF_TR_Phase(player.iuser4)!=VF_TR_WALL_RUN;++i)tick(ms,IN_FORWARD|IN_JUMP,315,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN&&player.origin[1]<-70,"second fresh bounce returns to first wall");
  for(i=0;i<2;++i){
   wallrun_setup(right,320);tick(ms,IN_FORWARD|IN_JUMP,entry,320,0);
   tick(ms,IN_FORWARD|IN_JUMP,i?269.9f:90.1f,320,0);
   expect(VF_TR_Phase(player.iuser4)==0&&player.velocity[2]<0,"crossing either ninety-degree boundary drops on the same command");
   for(int n=0;n<250/ms;++n)tick(ms,IN_FORWARD,entry,320,0);
   expect(VF_TR_Phase(player.iuser4)==0,"looking back toward wall cannot reattach without a new jump input");
  }
 }
 for(ms=8;ms<=33;ms=ms==8?16:ms==16?33:34){
  oblique_setup(17.04f);tick(ms,IN_FORWARD|IN_JUMP|IN_MOVELEFT,17.04f,320,-320);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"strafe intent follows view-relative movement on an oblique supporting wall");
  oblique_setup(17.04f);tick(ms,IN_FORWARD|IN_JUMP|IN_MOVERIGHT,17.04f,320,320);
  expect(VF_TR_Phase(player.iuser4)==0,"oblique-wall strafe away is rejected instead of relying on an axis-aligned wall label");
  oblique_setup(17.04f);tick(ms,IN_FORWARD|IN_JUMP,107.04f,320,0);
  expect(VF_TR_Phase(player.iuser4)==0&&player.velocity[2]>0&&player.fuser1>=0,
         "oblique entry outside packed heading limit preserves the ordinary airborne jump instead of forcing a drop");
  oblique_setup(17.04f);tick(ms,IN_FORWARD|IN_JUMP,106.84f,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"oblique entry inside packed view limit attaches normally");
  oblique_setup(17.06f);tick(ms,IN_FORWARD|IN_JUMP,107.06f,320,0);
  expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"upward heading rounding retains a valid perpendicular wall-facing entry");
 }
 {float anchor[3]={1,2,3};int state=VF_TR_State(VF_TR_WALL_RUN,359.9f)|VF_WR_RIGHT;
  expect(state<(1<<24)&&VF_TR_Yaw(state)>359.8f,"extended phase preserves packed yaw and 24-bit network word");
  expect(VF_TR_SaveValid(state,.5f,anchor)&&!VF_TR_SaveValid(state,1.5f,anchor),"wall run save validates normalized animation clock");
  expect(!VF_TR_SaveValid(state|(1<<17),0,anchor),"vault span cannot leak into wall run state");
  expect(VF_WR_LookAllowed(89.9f,359.9f)&&VF_WR_LookAllowed(269.9f,359.9f)&&!VF_WR_LookAllowed(90.1f,359.9f),
         "view limit wraps across the zero/360 seam and keeps exact ninety-degree boundaries");
 }
 for(ms=8;ms<=33;ms=ms==8?16:ms==16?33:34)for(int tagged=0;tagged<2;++tagged){
  wallrun_setup(1,320);player.numphysent=2;player.PM_PlayerTrace=modular_trace;
  player.physents[1].movetype=MOVETYPE_PUSH;player.physents[1].solid=SOLID_BSP;
  if(tagged){player.physents[1].controller[0]=VF_STATIC_BRUSH_TAG_0;player.physents[1].controller[1]=VF_STATIC_BRUSH_TAG_1;
   player.physents[1].controller[2]=VF_STATIC_BRUSH_TAG_2;player.physents[1].controller[3]=VF_STATIC_BRUSH_TAG_3;}
  tick(ms,IN_FORWARD|IN_JUMP,300,320,0);
  expect((VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN)==tagged,"only tagged immobile BSP submodels accept server and client wall run");
  if(tagged){for(i=0;i<600/ms;++i)tick(ms,IN_FORWARD,0,320,0);expect(VF_TR_Phase(player.iuser4)==VF_TR_WALL_RUN,"tagged BSP supports sustained wall run with prediction parity");}
 }
 printf("Wall run plus traversal: %d checks, %d wall-run failures\n",checks,failures-priorFailures);return failures?1:0;
}
