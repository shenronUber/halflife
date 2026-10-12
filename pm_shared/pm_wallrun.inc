/* Uses traversal traces and Valve's hull solver. All state is predicted. */
static void VF_WR_Basis(int state,vec3_t tangent,vec3_t normal) {
 float side=(state&VF_WR_RIGHT)?1.0f:-1.0f;
 VF_TR_Direction(VF_TR_Yaw(state),tangent);
 normal[0]=-tangent[1]*side;normal[1]=tangent[0]*side;normal[2]=0;
}
static int VF_WR_Forward(void) {
 return (pmove->cmd.buttons&IN_FORWARD)&&pmove->cmd.forwardmove>10&&
  !(pmove->cmd.buttons&IN_DUCK)&&!(pmove->flags&FL_DUCKING)&&pmove->usehull==0;
}
static int VF_WR_Wall(vec3_t normal,pmtrace_t *wall) {
 vec3_t end;pmtrace_t hull;
 VectorMA(pmove->origin,-VF_WR_REACH,normal,end);hull=VF_TR_Trace(pmove->origin,end,0);
 if(!VF_TR_Static(&hull)||fabs(hull.plane.normal[2])>.2f||DotProduct(normal,hull.plane.normal)<.98f)return 0;
 /* Store the world surface, not the expanded collision-hull face. */
 VectorMA(pmove->origin,-48,normal,end);*wall=VF_TR_Trace(pmove->origin,end,2);
 return VF_TR_Static(wall)&&fabs(wall->plane.normal[2])<=.2f&&DotProduct(normal,wall->plane.normal)>.98f;
}
static void VF_WR_Anchor(pmtrace_t *wall) {
 pmove->vuser3[0]=wall->endpos[0];pmove->vuser3[1]=wall->endpos[1];pmove->fuser4=wall->endpos[2];
}
static void VF_WR_Drop(void) {
 VF_TR_End(VF_WR_COOLDOWN);pmove->velocity[2]=min(pmove->velocity[2],-60.0f);
}
static void VF_WR_Jump(vec3_t tangent,vec3_t normal) {
 vec3_t look;float pitch=pmove->angles[0]*(float)(3.141592653589793/180),out,speed;
 VF_TR_Direction(pmove->angles[1],look);
 pmove->velocity[0]=look[0]*(float)cos(pitch)*VF_WR_JUMP_SPEED+tangent[0]*60;
 pmove->velocity[1]=look[1]*(float)cos(pitch)*VF_WR_JUMP_SPEED+tangent[1]*60;
 out=DotProduct(pmove->velocity,normal);
 if(out<VF_WR_JUMP_OUT){pmove->velocity[0]+=normal[0]*(VF_WR_JUMP_OUT-out);pmove->velocity[1]+=normal[1]*(VF_WR_JUMP_OUT-out);}
 speed=(float)sqrt(pmove->velocity[0]*pmove->velocity[0]+pmove->velocity[1]*pmove->velocity[1]);
 if(speed>560){pmove->velocity[0]*=560/speed;pmove->velocity[1]*=560/speed;}
 pmove->velocity[2]=max(140.0f,min(480.0f,220-(float)sin(pitch)*VF_WR_JUMP_SPEED));
 VF_TR_End(VF_WR_COOLDOWN);pmove->oldbuttons|=IN_JUMP;pmove->flFallVelocity=0;
 // Air steering starts on the next command; this launch cannot be cancelled
 // by the same forward input that was needed to stay attached.
 pmove->cmd.forwardmove=pmove->cmd.sidemove=pmove->cmd.upmove=0;
}
static int VF_WR_Move(void) {
 vec3_t tangent,normal;pmtrace_t wall;float speed;
 VF_WR_Basis(pmove->iuser4,tangent,normal);
 if(!VF_WR_Forward()||!VF_WR_LookAllowed(pmove->angles[1],VF_TR_Yaw(pmove->iuser4))||
    pmove->onground!=-1||!VF_WR_Wall(normal,&wall)){VF_WR_Drop();return 0;}
 if((pmove->cmd.buttons&~pmove->oldbuttons)&IN_JUMP){VF_WR_Jump(tangent,normal);return 0;}
 speed=DotProduct(pmove->velocity,tangent);
 if(speed<VF_WR_MIN_TANGENT){VF_WR_Drop();return 0;}
 speed=min(speed,VF_WR_MAX_SPEED);
 /* Only supported forward movement suspends gravity. Inward adhesion uses
    the ordinary swept hull; obstacles, ceilings and endpoints still collide. */
 pmove->velocity[0]=tangent[0]*speed-normal[0]*24;
 pmove->velocity[1]=tangent[1]*speed-normal[1]*24;pmove->velocity[2]=0;
 PM_FlyMove();PM_CatagorizePosition();
 if(pmove->onground!=-1||DotProduct(pmove->velocity,tangent)<VF_WR_MIN_TANGENT||!VF_WR_Wall(normal,&wall)){
  VF_WR_Drop();
 }else{
  VF_WR_Anchor(&wall);
  // A normalized distance clock is predicted, replicated and saved even for
  // the local player, whose authoritative gait frame may be unavailable.
  pmove->fuser1=(float)fmod(pmove->fuser1+pmove->frametime*speed/VF_WR_CYCLE_DISTANCE,1.0f);
  pmove->flFallVelocity=0;
 }
 pmove->oldbuttons=pmove->cmd.buttons;return 1;
}
static int VF_WR_Start(void) {
 vec3_t travel,probe,end,tangent,look,normal;pmtrace_t wall;float speed,along,yaw;int side,state;
 /* A nearby wall alone is not an input. Space plus a look toward it is
    required at contact, including the held Space from a running takeoff. */
 if(pmove->onground!=-1||!(pmove->cmd.buttons&IN_JUMP)||!VF_WR_Forward()||pmove->velocity[2]<-450)return 0;
 speed=(float)sqrt(pmove->velocity[0]*pmove->velocity[0]+pmove->velocity[1]*pmove->velocity[1]);
 if(speed<VF_WR_MIN_SPEED)return 0;
 travel[0]=pmove->velocity[0]/speed;travel[1]=pmove->velocity[1]/speed;travel[2]=0;
 VF_TR_Direction(pmove->angles[1],look);
 for(side=-1;side<=1;side+=2){
  probe[0]=-travel[1]*side;probe[1]=travel[0]*side;probe[2]=0;
  VectorMA(pmove->origin,24,probe,end);wall=VF_TR_Trace(pmove->origin,end,0);
  if(!VF_TR_Static(&wall)||fabs(wall.plane.normal[2])>.2f)continue;
  VectorCopy(wall.plane.normal,normal);normal[2]=0;VectorNormalize(normal);
  along=DotProduct(travel,normal);
  tangent[0]=travel[0]-normal[0]*along;tangent[1]=travel[1]-normal[1]*along;tangent[2]=0;VectorNormalize(tangent);
  along=DotProduct(pmove->velocity,tangent);
  if(along<VF_WR_MIN_TANGENT||
     -DotProduct(look,normal)*(float)cos(pmove->angles[0]*3.141592653589793/180)<VF_WR_ENTRY_LOOK_DOT||
     !VF_WR_Wall(normal,&wall))continue;
  yaw=(float)(atan2(tangent[1],tangent[0])*180/3.141592653589793);
  /* Entry and continuation must use the same packed heading. Otherwise
     its 0.1-degree rounding can accept an entry and immediately drop it,
     consuming the normal jump after its vertical velocity was cleared. */
  state=VF_TR_State(VF_TR_WALL_RUN,yaw);
  if(!VF_WR_LookAllowed(pmove->angles[1],VF_TR_Yaw(state)))continue;
  pmove->iuser4=state;
  if(normal[0]*(-tangent[1])+normal[1]*tangent[0]>0)pmove->iuser4|=VF_WR_RIGHT;
  pmove->velocity[0]=tangent[0]*min(along,VF_WR_MAX_SPEED);pmove->velocity[1]=tangent[1]*min(along,VF_WR_MAX_SPEED);pmove->velocity[2]=0;
  pmove->fuser1=0;VF_WR_Anchor(&wall);
  /* Held takeoff jump cannot automatically become a wall bounce. */
  pmove->oldbuttons|=pmove->cmd.buttons&IN_JUMP;
  return 1;
 }
 return 0;
}
