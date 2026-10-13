/* One deterministic Studio player pose for server collision and visible bodies.
 * Rendering-only viewmodel corrections remain outside this shared evaluator. */
#include "vf_player_pose.h"
#include "vf_traversal.h"

static qboolean R_VFCanonicalPlayer( const cl_entity_t *ent )
{
 return ent->player && ent->curstate.vuser4[2]==VF_PLAYER_POSE_MARKER &&
  VF_PosePlayerModel(ent->model->name);
}
static void R_VFAuditPlayerPose(const char *source,const cl_entity_t *ent){
 gEngfuncs.Con_Printf("VFPlayerPoseInput source=%s model=%s angles=%.6f,%.6f,%.6f blend=%d,%d previous=%.4f,%.4f,%.6f oldblend=%.1f,%.1f gaitframe=%.6f rate=%.6f interpolate=%d\n",source,ent->model->name,ent->angles[0],ent->angles[1],ent->angles[2],ent->curstate.blending[0],ent->curstate.blending[1],ent->curstate.vuser1[0],ent->curstate.vuser1[1],ent->curstate.vuser1[2],ent->curstate.vuser2[0],ent->curstate.vuser2[1],ent->curstate.vuser4[1],ent->curstate.framerate,g_studio.interpolate);
 mstudiobbox_t *boxes=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->hitboxindex);
 for(int b=0;b<m_pStudioHeader->numhitboxes;++b){
  const float (*matrix)[4]=g_studio.bonestransform[boxes[b].bone];
  gEngfuncs.Con_Printf("VFPlayerPose source=%s entity=%d sequence=%d frame=%.4f time=%.6f sample=%.6f gait=%d yaw=%.4f phase=%d box=%d matrix=%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",source,ent->index,ent->curstate.sequence,ent->curstate.frame,g_studio.time,ent->curstate.vuser2[2],ent->curstate.gaitsequence,ent->curstate.vuser4[0],VF_TR_Phase(ent->curstate.iuser4),b,matrix[0][0],matrix[0][1],matrix[0][2],matrix[0][3],matrix[1][0],matrix[1][1],matrix[1][2],matrix[1][3],matrix[2][0],matrix[2][1],matrix[2][2],matrix[2][3]);
 }
}
static void R_VFSampleTrack( cl_entity_t *ent,int sequence,float frame,byte blend0,byte blend1,vec3_t *pos,vec4_t *q )
{
 mstudioseqdesc_t *seq=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->seqindex);
 mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
 mstudiobonecontroller_t *controllers=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->bonecontrollerindex);
 if(sequence<0||sequence>=m_pStudioHeader->numseq)sequence=0;
 mstudioseqdesc_t *clip=&seq[sequence];mstudioanim_t *anim=gEngfuncs.R_StudioGetAnim(m_pStudioHeader,ent->model,clip);
 float adj[MAXSTUDIOCONTROLLERS]={0};
 for(int j=0;j<m_pStudioHeader->numbonecontrollers&&j<MAXSTUDIOCONTROLLERS;++j){
  int i=controllers[j].index;if(i<0||i>=4)continue;
  float value=(controllers[j].type&STUDIO_RLOOP)?ent->curstate.controller[i]*(360.f/256)+controllers[j].start:
   controllers[j].start+(controllers[j].end-controllers[j].start)*ent->curstate.controller[i]/255.f;
  adj[j]=value;if(controllers[j].type&(STUDIO_XR|STUDIO_YR|STUDIO_ZR))adj[j]*=(float)(M_PI/180);
 }
 frame=bound(0.f,frame,Q_max(0.f,clip->numframes-1.001f));
 for(int i=0;i<m_pStudioHeader->numbones;++i)R_StudioCalcBones((int)frame,frame-(int)frame,&bones[i],&anim[i],adj,pos[i],q[i]);
 if(clip->motiontype&STUDIO_X)pos[clip->motionbone][0]=0;
 if(clip->motiontype&STUDIO_Y)pos[clip->motionbone][1]=0;
 if(clip->motiontype&STUDIO_Z)pos[clip->motionbone][2]=0;
 if(clip->numblends>1){
  vec3_t pos2[MAXSTUDIOBONES],pos3[MAXSTUDIOBONES],pos4[MAXSTUDIOBONES];vec4_t q2[MAXSTUDIOBONES],q3[MAXSTUDIOBONES],q4[MAXSTUDIOBONES];
  anim+=m_pStudioHeader->numbones;
  for(int i=0;i<m_pStudioHeader->numbones;++i)R_StudioCalcBones((int)frame,frame-(int)frame,&bones[i],&anim[i],adj,pos2[i],q2[i]);
  if(clip->numblends==4){
   anim+=m_pStudioHeader->numbones;for(int i=0;i<m_pStudioHeader->numbones;++i)R_StudioCalcBones((int)frame,frame-(int)frame,&bones[i],&anim[i],adj,pos3[i],q3[i]);
   anim+=m_pStudioHeader->numbones;for(int i=0;i<m_pStudioHeader->numbones;++i)R_StudioCalcBones((int)frame,frame-(int)frame,&bones[i],&anim[i],adj,pos4[i],q4[i]);
   R_StudioSlerpBones(m_pStudioHeader->numbones,q3,pos3,q4,pos4,blend0/255.f);
  }
  R_StudioSlerpBones(m_pStudioHeader->numbones,q,pos,q2,pos2,blend0/255.f);
  if(clip->numblends==4)R_StudioSlerpBones(m_pStudioHeader->numbones,q,pos,q3,pos3,blend1/255.f);
 }
}
static void R_VFCanonicalBones( cl_entity_t *ent,qboolean gait )
{
 cl_entity_t sample=*ent;vec3_t pos[MAXSTUDIOBONES],otherPos[MAXSTUDIOBONES];vec4_t q[MAXSTUDIOBONES],otherQ[MAXSTUDIOBONES];
 mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
 mstudioseqdesc_t *seq=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->seqindex);
 int sequence=ent->curstate.sequence;if(sequence<0||sequence>=m_pStudioHeader->numseq)sequence=0;
 int gaitseq=gait?ent->curstate.gaitsequence:0;if(gaitseq<0||gaitseq>=m_pStudioHeader->numseq)gaitseq=0;
 memset(sample.curstate.controller,127,4);
 byte blend=ent->curstate.blending[0];
 // Removing the gait layer for seated combat must not remove pitch blending.
 // The legacy renderer already rewrote blending[0]; server entvars do not.
 if(ent->curstate.gaitsequence){
  float pitch=ent->angles[PITCH]*3;int value;
  if(pitch<seq[sequence].blendstart[0])value=0;
  else if(pitch>seq[sequence].blendend[0])value=255;
  else value=seq[sequence].blendend[0]-seq[sequence].blendstart[0]<.1f?127:(int)(255*(pitch-seq[sequence].blendstart[0])/(seq[sequence].blendend[0]-seq[sequence].blendstart[0]));
  blend=(byte)value;
  if(gaitseq&&!VF_PoseReferenceModel(ent->model->name)){
   float yaw=VF_TR_Angle(ent->angles[YAW]-ent->curstate.vuser4[0]);
   memset(sample.curstate.controller,(byte)bound(0,(int)((yaw*.25f+30)/(60.f/255)),255),4);
  }
 }
 // The transmitted frame belongs to the authoritative sample timestamp.
 // Legacy animtime packets have coarser precision and would shift fast limbs.
 sample.curstate.animtime=ent->curstate.vuser2[2];
 // Scripted melee publishes a normalized frame each server tick. Advance
 // that frame using its own authored FPS between packets, on both evaluators.
 if(Q_strstr(ent->model->name,"models/vf_melee/r01_tp")&&
    (!Q_strcmp(seq[sequence].label,"vf_melee")||!Q_strcmp(seq[sequence].label,"vf_melee_crouch")))sample.curstate.framerate=1;
 float frame=R_StudioEstimateFrame(&sample,&seq[sequence],g_studio.time);
 R_VFSampleTrack(&sample,sequence,frame,blend,ent->curstate.blending[1],pos,q);
 int previous=(int)ent->curstate.vuser1[0];float elapsed=g_studio.time-ent->curstate.vuser1[2];
 if(ent->curstate.vuser1[2]>0&&elapsed>=0&&elapsed<.2f&&previous>=0&&previous<m_pStudioHeader->numseq){
  float oldframe=ent->curstate.vuser1[1]*(seq[previous].numframes-1)/256.f;
  R_VFSampleTrack(&sample,previous,oldframe,VF_PoseBlend(ent->curstate.vuser2[0],0),VF_PoseBlend(ent->curstate.vuser2[0],1),otherPos,otherQ);
  R_StudioSlerpBones(m_pStudioHeader->numbones,q,pos,otherQ,otherPos,1-elapsed/.2f);
 }
 if(gaitseq){
  R_VFSampleTrack(&sample,gaitseq,ent->curstate.vuser4[1],blend,0,otherPos,otherQ);
  qboolean copy=true;
  for(int i=0;i<m_pStudioHeader->numbones;++i){
   if(!Q_strcmp(bones[i].name,"Bip01 Spine"))copy=false;
   else if(bones[i].parent>=0&&!Q_strcmp(bones[bones[i].parent].name,"Bip01 Pelvis"))copy=true;
   if(copy){VectorCopy(otherPos[i],pos[i]);Vector4Copy(otherQ[i],q[i]);}
  }
 }
 // The engine may temporarily restore view yaw while running a command,
 // and the local rendered entity may carry predicted camera angles. Use
 // the SDK's replicated body yaw in both cases, including gaitless jumps.
 vec3_t angles={0,ent->curstate.vuser4[0],0};
 Matrix3x4_CreateFromEntity(g_studio.rotationmatrix,angles,ent->origin,1);
 for(int i=0;i<m_pStudioHeader->numbones;++i){matrix3x4 local;Matrix3x4_FromOriginQuat(local,q[i],pos[i]);
  Matrix3x4_ConcatTransforms(g_studio.bonestransform[i],bones[i].parent<0?g_studio.rotationmatrix:g_studio.bonestransform[bones[i].parent],local);
  Matrix3x4_Copy(g_studio.lighttransform[i],g_studio.bonestransform[i]);
 }
}

// Fitted crouch poses bend the spine forward. Rotating each local spine X
// axis then rolls the torso while strafing. Distribute the same yaw around
// world-up instead, preserving the native feet/gait and every hand socket.
static void R_VFPlayerTorsoYaw( cl_entity_t *ent,qboolean prepared )
{
 if( VF_TR_Phase(ent->curstate.iuser4)==VF_TR_SLIDE ) return;
 if( !ent->player || !ent->curstate.gaitsequence ) return;
 player_info_t *info = pfnPlayerInfo( ent->index - 1 );
 if( !info ) return;
 float yaw = ent->angles[YAW] - (R_VFCanonicalPlayer(ent)?ent->curstate.vuser4[0]:info->gaityaw);
 while( yaw > 180.0f ) yaw -= 360.0f;
 while( yaw < -180.0f ) yaw += 360.0f;
 // StudioProcessGait already chose forward/backward gait at +/-120 degrees.
 for( int i = 0; i < 4; ++i )
  ent->curstate.controller[i] = ent->latched.prevcontroller[i] = 127;
 m_pPlayerInfo = info;
 if(!prepared){if(R_VFCanonicalPlayer(ent))R_VFCanonicalBones(ent,true);else R_StudioSetupBones( ent );}
 m_pPlayerInfo = NULL;
 mstudiobone_t *bones = (void *)((byte *)m_pStudioHeader + m_pStudioHeader->boneindex);
 const char *spines[] = {"Bip01 Spine", "Bip01 Spine1", "Bip01 Spine2", "Bip01 Spine3"};
 for( int joint = 0; joint < 4; ++joint )
 {
  int root = -1;
  for( int b = 0; b < m_pStudioHeader->numbones; ++b )
   if( !Q_strcmp( bones[b].name, spines[joint] )) { root = b; break; }
  if( root < 0 ) continue;
  matrix3x4 turn;
  vec3_t angles = {0, yaw * .25f, 0}, pivot, rotated, origin;
  for( int i = 0; i < 3; ++i ) pivot[i] = g_studio.bonestransform[root][i][3];
  VectorClear( origin );
  Matrix3x4_CreateFromEntity( turn, angles, origin, 1 );
  Matrix3x4_VectorRotate( turn, pivot, rotated );
  for( int i = 0; i < 3; ++i ) turn[i][3] = pivot[i] - rotated[i];
  for( int b = 0; b < m_pStudioHeader->numbones; ++b )
  {
   int ancestor = b;
   while( ancestor >= 0 && ancestor != root ) ancestor = bones[ancestor].parent;
   if( ancestor != root ) continue;
   matrix3x4 posed;
   Matrix3x4_ConcatTransforms( posed, turn, g_studio.bonestransform[b] );
   Matrix3x4_Copy( g_studio.bonestransform[b], posed );
   Matrix3x4_ConcatTransforms( posed, turn, g_studio.lighttransform[b] );
   Matrix3x4_Copy( g_studio.lighttransform[b], posed );
  }
 }
 R_StudioSaveBones();
 R_StudioCalcAttachments();
}

// Ledge IK runs AFTER Studio interpolation, before merge/socket parts copy
// the carrier pose. This keeps the actual palm on world geometry at all look
// angles; it also removes viewmodel bob/recoil from the support hand.
static void R_VFInverseRigid( const matrix3x4 in, matrix3x4 out )
{
 for( int i=0;i<3;++i ) { for( int j=0;j<3;++j ) out[i][j]=in[j][i]; out[i][3]=0; }
 for( int i=0;i<3;++i ) for( int j=0;j<3;++j ) out[i][3]-=out[i][j]*in[j][3];
}

static void R_VFTurnBetween( const vec3_t from, const vec3_t to, matrix3x4 out )
{
 vec3_t a,b,v;VectorCopy(from,a);VectorCopy(to,b);VectorNormalize(a);VectorNormalize(b);CrossProduct(a,b,v);
 float c=bound(-1.0f,DotProduct(a,b),1.0f),d=1+c;
 Matrix3x4_LoadIdentity(out);
 if( d<.00001f )
 {
  vec3_t axis={0,0,1}; if( fabsf(a[2])>.8f )VectorSet(axis,0,1,0);
  CrossProduct(a,axis,v);VectorNormalize(v);
  for(int i=0;i<3;++i)for(int j=0;j<3;++j)out[i][j]=2*v[i]*v[j]-(i==j?1:0);
  return;
 }
 float skew[3][3]={{0,-v[2],v[1]},{v[2],0,-v[0]},{-v[1],v[0],0}};
 for(int i=0;i<3;++i)for(int j=0;j<3;++j){out[i][j]+=skew[i][j];for(int k=0;k<3;++k)out[i][j]+=skew[i][k]*skew[k][j]/d;}
}

static void R_VFMoveJoint( int root, const matrix3x4 goal )
{
 mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
 matrix3x4 inverse,change,posed;R_VFInverseRigid(g_studio.bonestransform[root],inverse);
 float orthogonalError=0;
 for(int i=0;i<3;++i)for(int j=0;j<3;++j){float dot=0;for(int k=0;k<3;++k)dot+=g_studio.bonestransform[root][k][i]*g_studio.bonestransform[root][k][j];orthogonalError=Q_max(orthogonalError,fabsf(dot-(i==j?1:0)));}
 if(orthogonalError>.00001f){
  // Studio transitions/effects can briefly provide an affine basis. A
  // transpose is then NOT its inverse, and repeated support corrections
  // amplify the error. Keep descendants in their actual local frame.
  matrix4x4 full,inv;Matrix4x4_LoadIdentity(full);
  for(int i=0;i<3;++i)for(int j=0;j<4;++j)full[i][j]=g_studio.bonestransform[root][i][j];
  if(Matrix4x4_Invert_Full(inv,full))for(int i=0;i<3;++i)for(int j=0;j<4;++j)inverse[i][j]=inv[i][j];
 }
 Matrix3x4_ConcatTransforms(change,goal,inverse);
 for(int b=0;b<m_pStudioHeader->numbones;++b){
  int ancestor=b;while(ancestor>=0&&ancestor!=root)ancestor=bones[ancestor].parent;if(ancestor!=root)continue;
  Matrix3x4_ConcatTransforms(posed,change,g_studio.bonestransform[b]);Matrix3x4_Copy(g_studio.bonestransform[b],posed);
  Matrix3x4_ConcatTransforms(posed,change,g_studio.lighttransform[b]);Matrix3x4_Copy(g_studio.lighttransform[b],posed);
 }
 Matrix3x4_Copy(g_studio.bonestransform[root],goal);
}

static qboolean R_VFReach( int upper,int fore,int hand,const matrix3x4 goal,const vec3_t pole,qboolean sharedShoulder )
{
 vec3_t s,e,w,delta,direction,p,newElbow,from,to;matrix3x4 turn,posed;
 Matrix3x4_OriginFromMatrix(g_studio.bonestransform[upper],s);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],e);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[hand],w);
 VectorSubtract(e,s,from);float a=VectorLength(from);
 if(sharedShoulder){mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);a=VectorLength(bones[fore].value);}VectorSubtract(w,e,from);float b=VectorLength(from);
 Matrix3x4_OriginFromMatrix(goal,delta);VectorSubtract(delta,s,delta);float distance=VectorLength(delta);
 if(distance<=fabsf(a-b)+.0001f||distance>=a+b-.0001f)return false;
 VectorScale(delta,1/distance,direction);VectorSubtract(pole,s,p);VectorMA(p,-DotProduct(p,direction),direction,p);
 if(VectorLength(p)<.0001f){vec3_t up={0,0,1};CrossProduct(direction,up,p);}VectorNormalize(p);
 float along=(a*a-b*b+distance*distance)/(2*distance),height=sqrtf(Q_max(0,a*a-along*along));
 VectorMA(s,along,direction,newElbow);VectorMA(newElbow,height,p,newElbow);
 if(!sharedShoulder){
  VectorSubtract(e,s,from);VectorSubtract(newElbow,s,to);R_VFTurnBetween(from,to,turn);
  Matrix3x4_ConcatTransforms(posed,turn,g_studio.bonestransform[upper]);for(int i=0;i<3;++i)posed[i][3]=s[i];R_VFMoveJoint(upper,posed);
 }
 Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],e);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[hand],w);
 Matrix3x4_OriginFromMatrix(goal,to);VectorSubtract(to,newElbow,to);
 if(sharedShoulder||hand==17||hand==24){
  // Use the same wrist-driven forearm roll as the Blender workshop. Merely
  // turning the blended elbow axis leaves the sleeve twisted at its cuff.
  matrix3x4 inverse,relative,desired;R_VFInverseRigid(g_studio.bonestransform[fore],inverse);
  Matrix3x4_ConcatTransforms(relative,inverse,g_studio.bonestransform[hand]);Matrix3x4_LoadIdentity(desired);
  mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
  if(sharedShoulder){
   matrix3x4 bind,local,combined;Matrix3x4_LoadIdentity(bind);int chain[MAXSTUDIOBONES],count=0;
   for(int bone=hand;bone>=0&&bone!=fore&&count<MAXSTUDIOBONES;bone=bones[bone].parent)chain[count++]=bone;
   for(int n=count-1;n>=0;--n){vec4_t q;int bone=chain[n];AngleQuaternion(bones[bone].value+3,q,true);Matrix3x4_FromOriginQuat(local,q,bones[bone].value);Matrix3x4_ConcatTransforms(combined,bind,local);Matrix3x4_Copy(bind,combined);}
   for(int i=0;i<3;++i)for(int j=0;j<3;++j)relative[i][j]=bind[i][j];
  }else{
   // Anatomical wrist basis comes from the actual fitted body mesh. The R1
   // carrier header is already posed to an equipped stance.
   model_t *body=R_VFLoadModel("models/vf_skins/persona_scout.mdl");
   studiohdr_t *header=body?(studiohdr_t *)gEngfuncs.Mod_Extradata(mod_studio,body):NULL;
   if(header){mstudiobone_t *bodyBones=(void *)((byte *)header+header->boneindex);
    // The textured persona and its animation carrier have different orders.
    // Resolve by anatomical NAME, never by the carrier's numeric hand index.
    for(int bone=0;bone<header->numbones;++bone)if(!Q_strcmp(bodyBones[bone].name,bones[hand].name)){
     matrix3x4 bind;vec4_t q;AngleQuaternion(bodyBones[bone].value+3,q,true);Matrix3x4_FromOriginQuat(bind,q,bodyBones[bone].value);for(int i=0;i<3;++i)for(int j=0;j<3;++j)relative[i][j]=bind[i][j];break;
    }
   }
  }
  for(int i=0;i<3;++i)for(int j=0;j<3;++j){desired[i][j]=0;for(int k=0;k<3;++k)desired[i][j]+=goal[i][k]*relative[j][k];}
  vec3_t offset;Matrix3x4_OriginFromMatrix(relative,offset);Matrix3x4_VectorRotate(desired,offset,from);
  R_VFTurnBetween(from,to,turn);Matrix3x4_ConcatTransforms(posed,turn,desired);
 }else{
  VectorSubtract(w,e,from);R_VFTurnBetween(from,to,turn);Matrix3x4_ConcatTransforms(posed,turn,g_studio.bonestransform[fore]);
 }
 for(int i=0;i<3;++i)posed[i][3]=newElbow[i];R_VFMoveJoint(fore,posed);R_VFMoveJoint(hand,goal);
 return true;
}

// The ordinary equipped upper body remains authoritative for aim, recoil,
// magazine extraction and weapon switching. Only the seated lower body is
// sampled from the reviewed traversal clip, anchored to its momentum yaw.
#include "vf_wallrun_pose.inc"
static void R_VFSlideCombat( cl_entity_t *ent )
{
 if(VF_TR_Phase(ent->curstate.iuser4)==VF_TR_WALL_RUN){R_VFWallRunCombat(ent);return;}
 qboolean sliding=VF_TR_Phase(ent->curstate.iuser4)==VF_TR_SLIDE;
 if(!sliding&&(VF_TR_Phase(ent->curstate.iuser4)||ent->curstate.usehull!=1))return;
 qboolean view=ent==tr.viewent;
 if(view&&!Q_strstr(ent->model->name,"models/vf_traversal/r01_rig"))return;
 if(!view&&(!ent->player||!VF_PoseReferenceModel(ent->model->name)))return;
 mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
 mstudioseqdesc_t *sequences=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->seqindex);
 if(!view){
  // This verified carrier orders the pelvis and legs before the spine.
  if(m_pStudioHeader->numbones<29||Q_strcmp(bones[8].name,"Bip01 Spine"))return;
  matrix3x4 slide[9];
  for(int i=0;i<=8;++i)Matrix3x4_Copy(slide[i],g_studio.bonestransform[i]);
  // Evaluate the live combat track without the crouch gait's tilted pelvis.
  // Its inherited rotation would point the whole rifle toward the floor.
  // Aim yaw belongs to the upper body; travel yaw belongs to the seated legs.
  for(int i=0;i<4;++i)ent->curstate.controller[i]=ent->latched.prevcontroller[i]=127;
  vec3_t combatAngles={0,ent->angles[YAW],0};
  Matrix3x4_CreateFromEntity(g_studio.rotationmatrix,combatAngles,ent->origin,1);
  m_pPlayerInfo=NULL;if(R_VFCanonicalPlayer(ent))R_VFCanonicalBones(ent,false);else R_StudioSetupBones(ent);
  if(sliding){
  float elapsed=VF_TR_SLIDE_TIME-ent->curstate.fuser1,progress=0;
  const char *label=elapsed<.25f?"vf_slide_start":ent->curstate.fuser1<.3f?"vf_slide_end":"vf_slide_loop";
  int sequence=-1;
  for(int i=0;i<m_pStudioHeader->numseq;++i)if(!Q_strcmp(sequences[i].label,label)){sequence=i;break;}
  if(sequence<0)return;
  mstudioseqdesc_t *clip=&sequences[sequence];
  mstudioanim_t *anim=gEngfuncs.R_StudioGetAnim(m_pStudioHeader,ent->model,clip);if(!anim)return;
  if(elapsed<.25f)progress=elapsed/.25f*(clip->numframes-1);
  else if(ent->curstate.fuser1<.3f)progress=(.3f-ent->curstate.fuser1)/.3f*(clip->numframes-1);
  else if(clip->numframes>1)progress=fmodf((elapsed-.25f)*clip->fps,clip->numframes-1);
  progress=bound(0.0f,progress,Q_max(0,clip->numframes-1.001f));
  vec3_t angles={0,VF_TR_Yaw(ent->curstate.iuser4),0};matrix3x4 base;
  Matrix3x4_CreateFromEntity(base,angles,ent->origin,1);
  float adj[MAXSTUDIOCONTROLLERS]={0};
  for(int i=0;i<=8;++i){
   vec3_t pos;vec4_t q;matrix3x4 local;
   R_StudioCalcBones((int)progress,progress-(int)progress,&bones[i],&anim[i],adj,pos,q);
   Matrix3x4_FromOriginQuat(local,q,pos);
   Matrix3x4_ConcatTransforms(slide[i],bones[i].parent<0?base:slide[bones[i].parent],local);
  }
  }
  matrix3x4 upper;Matrix3x4_Copy(upper,g_studio.bonestransform[8]);
  for(int axis=0;axis<3;++axis)upper[axis][3]=slide[8][axis][3];
  R_VFMoveJoint(8,upper);
  for(int i=0;i<8;++i){
   Matrix3x4_Copy(g_studio.bonestransform[i],slide[i]);Matrix3x4_Copy(g_studio.lighttransform[i],slide[i]);
  }
  const char *action=sequences[ent->curstate.sequence].label;
  if(!Q_strncmp(action,"ref_aim_",8)||!Q_strncmp(action,"ref_shoot_",10)){
   int weapon=-1;
   for(int i=0;i<m_pStudioHeader->numbones;++i)if(!Q_strcmp(bones[i].name,"VF_Weapon")){weapon=i;break;}
   if(weapon>=0){
    // The source aim blends have a small downward bias. Fit both wrists
    // together around the firing-hand contact, so the rifle follows the
    // actual sight line without pitching the head or breaking either grip.
    float yaw=ent->angles[YAW]*(float)(M_PI/180),pitch=-ent->angles[PITCH]*3*(float)(M_PI/180);
    vec3_t aim={cosf(pitch)*cosf(yaw),cosf(pitch)*sinf(yaw),-sinf(pitch)};
    vec3_t barrel={g_studio.bonestransform[weapon][0][1],g_studio.bonestransform[weapon][1][1],g_studio.bonestransform[weapon][2][1]};
    vec3_t pivot,rotated,poles[2];matrix3x4 turn,goals[2];
    R_VFTurnBetween(barrel,aim,turn);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[24],pivot);
    Matrix3x4_VectorRotate(turn,pivot,rotated);for(int i=0;i<3;++i)turn[i][3]=pivot[i]-rotated[i];
    Matrix3x4_ConcatTransforms(goals[0],turn,g_studio.bonestransform[17]);
    Matrix3x4_ConcatTransforms(goals[1],turn,g_studio.bonestransform[24]);
    Matrix3x4_OriginFromMatrix(g_studio.bonestransform[16],poles[0]);
    Matrix3x4_OriginFromMatrix(g_studio.bonestransform[23],poles[1]);
    vec3_t shoulder,wrist,segment;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[15],shoulder);
    Matrix3x4_OriginFromMatrix(goals[0],wrist);VectorSubtract(wrist,shoulder,segment);float distance=VectorLength(segment);
    VectorSubtract(poles[0],shoulder,segment);float a=VectorLength(segment);
    Matrix3x4_OriginFromMatrix(g_studio.bonestransform[17],wrist);VectorSubtract(wrist,poles[0],segment);float b=VectorLength(segment);
    if(distance>fabsf(a-b)+.0001f&&distance<a+b-.0001f){
     R_VFReach(22,23,24,goals[1],poles[1],false);R_VFReach(15,16,17,goals[0],poles[0],false);
    }
   }
  }
  R_StudioSaveBones();R_StudioCalcAttachments();
 }
 if(gpGlobals->developer>=2){
  int weapon=-1;
  for(int i=0;i<m_pStudioHeader->numbones;++i)if(!Q_strcmp(bones[i].name,view?"Bone76":"VF_Weapon")){weapon=i;break;}
  if(weapon>=0){
   matrix3x4 *gun=&g_studio.bonestransform[weapon];vec3_t barrel={(*gun)[0][1],(*gun)[1][1],(*gun)[2][1]};VectorNormalize(barrel);
   float yaw=view?atan2f(RI.vforward[1],RI.vforward[0]):ent->angles[YAW]*(float)(M_PI/180);
   gEngfuncs.Con_Printf("%s view=%d sequence=%s frame=%.3f barrel=%.5f,%.5f,%.5f forward=%.5f hip=%.4f,%.4f,%.4f knee=%.4f,%.4f,%.4f\n",sliding?"VFSlideCombat":"VFCrouchCombat",view,sequences[ent->curstate.sequence].label,R_StudioEstimateFrame(ent,&sequences[ent->curstate.sequence],g_studio.time),barrel[0],barrel[1],barrel[2],barrel[0]*cosf(yaw)+barrel[1]*sinf(yaw),g_studio.bonestransform[view?0:1][0][3],g_studio.bonestransform[view?0:1][1][3],g_studio.bonestransform[view?0:1][2][3],g_studio.bonestransform[view?0:6][0][3],g_studio.bonestransform[view?0:6][1][3],g_studio.bonestransform[view?0:6][2][3]);
  }
 }
}

static float R_VFLeftLean( const char *label, int blend )
{
 if(Q_strncmp(label,"vf_hang_aim_",12))return 0;
 float relative=Q_atoi(label+12)*45.0f+blend*45.0f/255-22.5f;
 float side=Q_max(0,sinf(relative*(float)(M_PI/180)));
 return VF_TR_AimDeploy(relative)*side*side;
}

static void R_VFLedgePalms( cl_entity_t *ent )
{
 int phase=VF_TR_Phase(ent->curstate.iuser4);
 qboolean view=ent==tr.viewent;
 if(!VF_TR_Hanging(ent->curstate.iuser4)||(!view&&!ent->player))return;
 if(view&&!Q_strstr(ent->model->name,"models/vf_traversal/r01_rig"))return;
 if(!view&&!VF_PoseReferenceModel(ent->model->name))return;
 if(phase==VF_TR_HANG&&ent->curstate.fuser1>0&&!(ent->curstate.iuser4&VF_TR_RETURNING))return;
 float yaw=VF_TR_Yaw(ent->curstate.iuser4)*(float)(M_PI/180.0);vec3_t forward={cosf(yaw),sinf(yaw),0},side={-sinf(yaw),cosf(yaw),0},up={0,0,1};
 const vec3_t fpPalm[2]={{.3f,3,-1.45f},{-.3f,3,-1.45f}},tpPalm={1.8f,-.2f,-.4f};
 float errors[2]={-1,-1},bodyShift=0,gunError=-1,faceError=-1;
 float leftLean=0,retreat=0,lift=0,wristRise=0;
 if(!view){
  // The shooting eye rises independently of the planted legs. Sample the
  // authored hanging root, then cancel the live gameplay origin's rise.
  // This also keeps the waist still DURING drawing/returning, where the
  // collision origin and Studio animation advance at different rates.
  mstudioseqdesc_t *sequences=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->seqindex);
  mstudiobone_t *rootBone=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
  leftLean=R_VFLeftLean(sequences[ent->curstate.sequence].label,ent->curstate.blending[0]);
  if(R_VFCanonicalPlayer(ent)&&ent->curstate.vuser1[2]>0&&ent->curstate.vuser1[2]+.2f>g_studio.time&&(int)ent->curstate.vuser1[0]<m_pStudioHeader->numseq){
   float previous=R_VFLeftLean(sequences[(int)ent->curstate.vuser1[0]].label,VF_PoseBlend(ent->curstate.vuser2[0],0));
   float amount=bound(0.f,1-(g_studio.time-ent->curstate.vuser1[2])/.2f,1.f);leftLean+=amount*(previous-leftLean);
  }else if(g_studio.interpolate&&ent->latched.sequencetime&&ent->latched.sequencetime+.2f>g_studio.time&&ent->latched.prevsequence<m_pStudioHeader->numseq){
   float previous=R_VFLeftLean(sequences[ent->latched.prevsequence].label,ent->latched.prevseqblending[0]);
   float amount=bound(0.0f,1-(g_studio.time-ent->latched.sequencetime)/.2f,1.0f);
   leftLean+=amount*(previous-leftLean);
  }
  lift=3*leftLean;
  for(int i=0;i<m_pStudioHeader->numseq;++i)if(!Q_stricmp(sequences[i].label,"vf_hang_idle")){
   mstudioanim_t *anim=gEngfuncs.R_StudioGetAnim(m_pStudioHeader,ent->model,&sequences[i]);
   if(anim){float adj[MAXSTUDIOCONTROLLERS]={0};vec3_t pos;vec4_t q;matrix3x4 root;
    R_StudioCalcBones(0,0,rootBone,anim,adj,pos,q);Matrix3x4_Copy(root,g_studio.bonestransform[0]);
    vec3_t neutral;Matrix3x4_VectorTransform(g_studio.rotationmatrix,pos,neutral);
    root[0][3]=neutral[0];root[1][3]=neutral[1];
    root[2][3]=ent->curstate.fuser4-VF_TR_HANG_DEPTH+pos[2]+lift;R_VFMoveJoint(0,root);
   }
   break;
  }
  // The left-side pose deliberately rises a little and retreats while its
  // palm stays fixed. Lower-body joint angles remain the authored hang.
  if(leftLean>.000001f){
   vec3_t contact,goal,shoulder,elbow,wrist,delta,segment;
   VectorMA(ent->origin,18,forward,contact);VectorMA(contact,8,side,contact);contact[2]=ent->curstate.fuser4-1.4f;
   for(int i=0;i<3;++i)goal[i]=contact[i]-(.9396926208f*up[i]+.3420201433f*forward[i])*tpPalm[0]-(-.3420201433f*up[i]+.9396926208f*forward[i])*tpPalm[1]-side[i]*tpPalm[2];
   Matrix3x4_OriginFromMatrix(g_studio.bonestransform[15],shoulder);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[16],elbow);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[17],wrist);
   VectorSubtract(elbow,shoulder,segment);float reach=VectorLength(segment);VectorSubtract(wrist,elbow,segment);reach+=VectorLength(segment);
   VectorSubtract(goal,shoulder,delta);float distance=VectorLength(delta),along=DotProduct(delta,forward),across=DotProduct(delta,side);
   float target=distance*(1-leftLean)+.95f*reach*leftLean;
   retreat=bound(-6.0f,sqrtf(Q_max(0,target*target-across*across-delta[2]*delta[2]))-along,6.0f);
   matrix3x4 root;Matrix3x4_Copy(root,g_studio.bonestransform[0]);for(int i=0;i<3;++i)root[i][3]-=retreat*forward[i];R_VFMoveJoint(0,root);
  }
  // Fit only the upper body if a Studio transition briefly exceeds reach.
  int hands=phase==VF_TR_HANG?2:1;
  for(int iteration=0;iteration<24;++iteration){
   float largest=0;
   for(int h=0;h<hands;++h){
    vec3_t contact,goal,shoulder,elbow,wrist,delta,segment;
    VectorMA(ent->origin,18,forward,contact);VectorMA(contact,h?-8:8,side,contact);contact[2]=ent->curstate.fuser4-1.4f;
    for(int i=0;i<3;++i)goal[i]=contact[i]-(.9396926208f*up[i]+.3420201433f*forward[i])*tpPalm[0]-(-.3420201433f*up[i]+.9396926208f*forward[i])*tpPalm[1]-side[i]*tpPalm[2];
    int upper=h?22:15,fore=h?23:16,hand=h?24:17;
    Matrix3x4_OriginFromMatrix(g_studio.bonestransform[upper],shoulder);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],elbow);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[hand],wrist);
    VectorSubtract(elbow,shoulder,segment);float reach=VectorLength(segment);VectorSubtract(wrist,elbow,segment);reach+=VectorLength(segment)-.4f;
    VectorSubtract(goal,shoulder,delta);float distance=VectorLength(delta);
    if(distance>reach){matrix3x4 spine;Matrix3x4_Copy(spine,g_studio.bonestransform[8]);float scale=1-reach/distance;for(int i=0;i<3;++i)spine[i][3]+=delta[i]*scale;float shift=distance-reach;bodyShift+=shift;largest=Q_max(largest,shift);R_VFMoveJoint(8,spine);}
   }
   if(largest<.00001f)break;
  }
 }
 for(int h=0;h<(phase==VF_TR_HANG&&ent->curstate.fuser1<=0?2:1);++h){
  matrix3x4 goal;vec3_t contact,pole;
  const float *palm=view?fpPalm[h]:tpPalm;
  // The authored wide-ledge grip shows the backs of the hands: the local
  // dorsal +Z faces the eye, with a 20-degree lean over the top. Mirror the
  // contact offset, rather than rotating the right thumb out of the palm.
  const float leanSin=.3420201433f,leanCos=.9396926208f;
  for(int i=0;i<3;++i){
   goal[i][0]=view?-side[i]:leanCos*up[i]+leanSin*forward[i];
   goal[i][1]=view?leanCos*up[i]+leanSin*forward[i]:-leanSin*up[i]+leanCos*forward[i];
   goal[i][2]=view?leanSin*up[i]-leanCos*forward[i]:side[i];
  }
  if(view)VectorCopy(h?ent->curstate.vuser2:ent->curstate.vuser1,contact);
  else {VectorMA(ent->origin,18,forward,contact);VectorMA(contact,h?-8:8,side,contact);contact[2]=ent->curstate.fuser4-1.4f;}
  for(int i=0;i<3;++i){goal[i][3]=contact[i];for(int j=0;j<3;++j)goal[i][3]-=goal[i][j]*palm[j];}
  int upper=view?3:h?22:15,fore=view?(h?4:10):h?23:16,hand=view?(h?6:12):h?24:17;
  // Four view-angle corners do not preserve an elbow pole when blended:
  // averaging their positions can cross the sleeves in front of the eye.
  // Fit the approved wide-ledge pose in wall coordinates after the blend.
  if(view){
   VectorMA(contact,-10,forward,pole);VectorMA(pole,h?-4:4,side,pole);pole[2]-=18.2f;
  }else {
   Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],pole);
   if(phase==VF_TR_ARMED&&h==0&&ent->curstate.fuser1<=0){
    mstudioseqdesc_t *seq=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->seqindex);
    const char *label=seq[ent->curstate.sequence].label;
    if(!Q_strncmp(label,"vf_hang_aim_",12)){
     float relative=(Q_atoi(label+12)*45.0f+ent->curstate.blending[0]*45.0f/255-22.5f)*(float)(M_PI/180);
     float clearance=Q_min(1.0f,2*Q_max(0,Q_max(sinf(relative),-cosf(relative))));
     vec3_t low;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[upper],low);
     VectorMA(low,-4,forward,low);VectorMA(low,4,side,low);low[2]-=16;
     for(int i=0;i<3;++i)pole[i]+=clearance*(low[i]-pole[i]);
    }
   }
  }
  if(!R_VFReach(upper,fore,hand,goal,pole,view))continue;
  // The wrist constraint carries the authored finger subtree rigidly. Finger
  // keys remain editable in fragMOTION instead of being overwritten here.
  vec3_t actual,diff;Matrix3x4_VectorTransform(g_studio.bonestransform[hand],palm,actual);VectorSubtract(actual,contact,diff);errors[h]=VectorLength(diff);
 }
 // The gun and its right-hand grip also need a constraint after the four
 // Studio blends: interpolating parent joints otherwise points a backwards
 // shot upwards. The canonical R-01 barrel runs along its local +Y axis.
 if(phase==VF_TR_ARMED&&ent->curstate.fuser1<=0){
  mstudioseqdesc_t *sequence=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->seqindex);
  const char *label=sequence[ent->curstate.sequence].label;
  if(!Q_strncmp(label,"vf_hang_aim_",12)){
   float relative=Q_atoi(label+12)*45.0f+(ent->curstate.blending[0]*45.0f/255-22.5f);
   float aimYaw=yaw+relative*(float)(M_PI/180),pitch=(ent->curstate.blending[1]*140.0f/255-70)*(float)(M_PI/180);
   matrix3x4 gun,grip,inverse,goal;vec4_t q;
   mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
   int upper=view?3:22,fore=view?4:23,hand=view?6:24,weapon=28;
   // StudioMDL reorders the extended view rig when it inserts the mirrored
   // fingers. Bone76 is the R1 gun socket; source index 40 becomes a finger.
   if(view)for(int i=0;i<m_pStudioHeader->numbones;++i)if(!Q_strcmp(bones[i].name,"Bone76")){weapon=i;break;}
   if(view){matrix3x4 inverseHand;R_VFInverseRigid(g_studio.bonestransform[hand],inverseHand);Matrix3x4_ConcatTransforms(grip,inverseHand,g_studio.bonestransform[weapon]);}
   else {AngleQuaternion(bones[weapon].value+3,q,true);Matrix3x4_FromOriginQuat(grip,q,bones[weapon].value);}
   R_VFInverseRigid(grip,inverse);
   vec3_t wrist,pole,shoulder,elbow,segment;
   Matrix3x4_OriginFromMatrix(g_studio.bonestransform[upper],shoulder);
   Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],elbow);
   Matrix3x4_OriginFromMatrix(g_studio.bonestransform[hand],wrist);
   VectorSubtract(elbow,shoulder,segment);float upperLength=VectorLength(segment),reach=upperLength;
   VectorSubtract(wrist,elbow,segment);float foreLength=VectorLength(segment);reach+=foreLength;
   float angle=relative*(float)(M_PI/180),s=sinf(angle),c=cosf(angle),crossing=Q_max(0,Q_max(s,-c));
   float deploy=VF_TR_AimDeploy(relative),extend=deploy*deploy*deploy;
   float chest=bound(-45.0f,VF_TR_Angle(relative)-45*s,45.0f)*(float)(M_PI/180);
   float armAngle=angle+(20*Q_max(0,s)*Q_max(0,s))*(float)(M_PI/180);
   float poleFront=14*(1-2*Q_max(0,s));
   float route=0;vec3_t routeElbow={0,0,0};
   if(!view){
    vec3_t aimed={.94f*reach*cosf(armAngle),.94f*reach*sinf(armAngle),0},guard={6,-2,0};
    for(int i=0;i<3;++i){wrist[i]=shoulder[i]+forward[i]*(aimed[0]*extend+guard[0]*(1-extend))+side[i]*(aimed[1]*extend+guard[1]*(1-extend));}
    vec3_t supportShoulder;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[15],supportShoulder);
    float positive=relative;while(positive<0)positive+=360;while(positive>=360)positive-=360;
    if(positive<=180)route=deploy;
    else {float t=bound(0.0f,(225-positive)/45,1.0f);route=t*t*(3-2*t);}
    if(route>.000001f){
     vec3_t span;VectorSubtract(supportShoulder,shoulder,span);
     float torso=atan2f(-span[0],span[1]),upperAngle=torso-15*(float)(M_PI/180);
     VectorSet(routeElbow,upperLength*.9961946981f*cosf(upperAngle),upperLength*.9961946981f*sinf(upperAngle),upperLength*.0871557427f);
     vec3_t around;VectorSet(around,routeElbow[0]-foreLength*.7071067812f*sinf(torso),routeElbow[1]+foreLength*.7071067812f*cosf(torso),routeElbow[2]+foreLength*.7071067812f);
     for(int i=0;i<3;++i)wrist[i]+=(shoulder[i]+around[i]-wrist[i])*route;
    }
    wristRise=wrist[2]-shoulder[2];
   }else{
    // The equipped FPS wrist is very close to the eye. An upright rifle
    // pivoting there passes behind the near plane; bring the guard forward
    // while retaining the reviewed grip and keeping it below eye level.
    VectorMA(wrist,12*(1-deploy),RI.vforward,wrist);
    VectorMA(wrist,4*(1-deploy),RI.vup,wrist);
   }
   pitch=(-(float)M_PI/2)+(pitch+(float)M_PI/2)*deploy;
   for(int i=0;i<3;++i)gun[i][3]=0;
   gun[0][0]=sinf(aimYaw);gun[1][0]=-cosf(aimYaw);gun[2][0]=0;
   gun[0][1]=cosf(pitch)*cosf(aimYaw);gun[1][1]=cosf(pitch)*sinf(aimYaw);gun[2][1]=-sinf(pitch);
   gun[0][2]=sinf(pitch)*cosf(aimYaw);gun[1][2]=sinf(pitch)*sinf(aimYaw);gun[2][2]=cosf(pitch);
   vec3_t offset;Matrix3x4_OriginFromMatrix(inverse,offset);Matrix3x4_VectorRotate(gun,offset,pole);
   for(int i=0;i<3;++i)gun[i][3]=wrist[i]-pole[i];Matrix3x4_ConcatTransforms(goal,gun,inverse);
   if(view)Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],pole);
   else {
    VectorMA(shoulder,extend*poleFront*cosf(chest)+(1-extend)*4,forward,pole);
    VectorMA(pole,extend*poleFront*sinf(chest)-(1-extend)*10,side,pole);pole[2]+=extend*(-8+8*crossing)-(1-extend)*14;
    for(int i=0;i<3;++i)pole[i]+=(shoulder[i]+routeElbow[i]-pole[i])*route;
   }
   if(R_VFReach(upper,fore,hand,goal,pole,view)){
    R_VFMoveJoint(weapon,gun);
    vec3_t actual,diff;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[hand],actual);VectorSubtract(actual,wrist,diff);gunError=VectorLength(diff);
    if(view&&gpGlobals->developer>=2)gEngfuncs.Con_Printf("VFTraversalViewGun yaw=%.2f deploy=%.5f barrel_up=%.5f gun_error=%.5f\n",relative,deploy,gun[2][1],gunError);
    if(!view&&gpGlobals->developer>=2){
     vec3_t leftElbow;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[16],leftElbow);
     Matrix3x4_OriginFromMatrix(g_studio.bonestransform[23],elbow);
     VectorSubtract(actual,shoulder,diff);
     vec3_t planned;VectorSubtract(wrist,shoulder,planned);
     gEngfuncs.Con_Printf("VFTraversalArm yaw=%.2f extension=%.5f right_elbow_z=%.4f left_elbow_z=%.4f crossing=%.5f deploy=%.5f wrist_height=%.4f barrel_up=%.5f expected_rise=%.4f expected_extension=%.5f route=%.5f\n",relative,VectorLength(diff)/reach,elbow[2],leftElbow[2],crossing,deploy,wrist[2]-shoulder[2],gun[2][1],wristRise,VectorLength(planned)/reach,route);
     gEngfuncs.Con_Printf("VFTraversalEnvelope s=%.4f,%.4f,%.4f e=%.4f,%.4f,%.4f w=%.4f,%.4f,%.4f torso=",shoulder[0],shoulder[1],shoulder[2],elbow[0],elbow[1],elbow[2],actual[0],actual[1],actual[2]);
     int torsoBones[6]={8,9,10,11,14,21};
     for(int b=0;b<6;++b)for(int i=0;i<3;++i)for(int j=0;j<4;++j)gEngfuncs.Con_Printf("%.4f,",g_studio.bonestransform[torsoBones[b]][i][j]);
     gEngfuncs.Con_Printf("\n");
    }
   }
   const vec3_t faceAxis={.20738468f,.97767913f,.03369132f};vec3_t face,barrel={gun[0][1],gun[1][1],gun[2][1]};
   if(!view){Matrix3x4_VectorRotate(g_studio.bonestransform[13],faceAxis,face);VectorNormalize(face);faceError=acosf(bound(-1.0f,DotProduct(face,barrel),1.0f))*(float)(180/M_PI);}
  }
 }
 R_StudioSaveBones();R_StudioCalcAttachments();
 if(view&&ent->curstate.fuser2>0)gEngfuncs.Con_Printf("VFTraversalRender phase=%d left_error=%.5f right_error=%.5f yaw=%.1f\n",phase,errors[0],errors[1],ent->angles[YAW]);
 if(!view&&gpGlobals->developer>=2){
  vec3_t hip,knee;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[1],hip);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[3],knee);
  vec3_t shoulder,elbow,wrist,delta;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[15],shoulder);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[16],elbow);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[17],wrist);
  VectorSubtract(elbow,shoulder,delta);float reach=VectorLength(delta);VectorSubtract(wrist,elbow,delta);reach+=VectorLength(delta);VectorSubtract(wrist,shoulder,delta);
  gEngfuncs.Con_Printf("VFTraversalLean phase=%d weight=%.5f retreat=%.5f lift=%.5f support_extension=%.5f wall_yaw=%.2f\n",phase,leftLean,retreat,lift,VectorLength(delta)/reach,yaw*(float)(180/M_PI));
  gEngfuncs.Con_Printf("VFTraversalAnchor phase=%d hip=%.4f,%.4f,%.4f knee=%.4f,%.4f,%.4f\n",phase,hip[0],hip[1],hip[2],knee[0],knee[1],knee[2]);
  if(ent->curstate.fuser1<=0)gEngfuncs.Con_Printf("VFTraversalBody phase=%d sequence=%d left_error=%.5f right_error=%.5f gun_error=%.5f body_shift=%.5f face_error=%.3f\n",phase,ent->curstate.sequence,errors[0],errors[1],gunError,bodyShift,faceError);
 }
}

static void R_VFVaultPalm( cl_entity_t *ent )
{
 if(VF_TR_Phase(ent->curstate.iuser4)!=VF_TR_VAULT)return;
 qboolean view=ent==tr.viewent;
 if(view&&!Q_strstr(ent->model->name,"models/vf_traversal/r01_rig"))return;
 if(!view&&(!ent->player||!VF_PoseReferenceModel(ent->model->name)))return;
 float t=bound(0.0f,1-ent->curstate.fuser1/VF_TR_TransferTime(ent->curstate.iuser4),1.0f);
 float w=t<.24f?t/.24f:t<=.30f?1:(.48f-t)/.18f;w=bound(0.0f,w,1.0f);w=w*w*(3-2*w);
 if(w<=.00001f)return;
 float yaw=VF_TR_Yaw(ent->curstate.iuser4)*(float)(M_PI/180);
 vec3_t forward={cosf(yaw),sinf(yaw),0},side={-sinf(yaw),cosf(yaw),0},contact,pole;
 matrix3x4 goal;int upper=view?3:15,fore=view?10:16,hand=view?12:17;
 if(view)VectorCopy(ent->curstate.vuser1,contact);
 else{
  float offset=(ent->curstate.iuser4&VF_TR_WIDE)?-26:-VF_TR_VaultSpan(ent->curstate.iuser4)-20;
  VectorSet(contact,ent->curstate.vuser3[0],ent->curstate.vuser3[1],ent->curstate.fuser4-1.4f);
  VectorMA(contact,offset,forward,contact);VectorMA(contact,8,side,contact);
 }
 const vec3_t fp={.3f,3,-1.45f},tp={1.8f,-.2f,-.4f};const float *palm=view?fp:tp;
 for(int i=0;i<3;++i){goal[i][0]=view?-side[i]:i==2?1:0;goal[i][1]=view?(i==2?1:0):forward[i];goal[i][2]=view?-forward[i]:side[i];
  goal[i][3]=contact[i];for(int j=0;j<3;++j)goal[i][3]-=goal[i][j]*palm[j];}
 if(w<.9999f){
  vec3_t firstAngles,lastAngles,position;vec4_t first,last,q;
  Matrix3x4_AnglesFromMatrix(g_studio.bonestransform[hand],firstAngles);Matrix3x4_AnglesFromMatrix(goal,lastAngles);
  AngleQuaternion(firstAngles,first,false);AngleQuaternion(lastAngles,last,false);QuaternionSlerp(first,last,w,q);
  for(int i=0;i<3;++i)position[i]=g_studio.bonestransform[hand][i][3]*(1-w)+goal[i][3]*w;
  Matrix3x4_FromOriginQuat(goal,q,position);
 }
 Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],pole);
 // A small torso reach correction covers low/high wall variations; the
 // leg bones retain their authored lengths and clearance.
 {
  vec3_t s,e,h,d;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[upper],s);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],e);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[hand],h);
  VectorSubtract(e,s,d);float reach=VectorLength(d);
  if(view){mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);reach=VectorLength(bones[fore].value);}
  VectorSubtract(h,e,d);reach+=VectorLength(d)-.2f;
  for(int i=0;i<3;++i)d[i]=goal[i][3]-s[i];float distance=VectorLength(d);
  if(distance>reach){int root=view?0:8;matrix3x4 spine;Matrix3x4_Copy(spine,g_studio.bonestransform[root]);float shift=distance-reach;for(int i=0;i<3;++i){spine[i][3]+=d[i]*shift/distance;pole[i]+=d[i]*shift/distance;}R_VFMoveJoint(root,spine);}
 }
 if(R_VFReach(upper,fore,hand,goal,pole,view)){
  R_StudioSaveBones();R_StudioCalcAttachments();
  if(gpGlobals->developer>=2){vec3_t actual;Matrix3x4_VectorTransform(g_studio.bonestransform[hand],palm,actual);VectorSubtract(actual,contact,actual);
   gEngfuncs.Con_Printf("VFVaultPalm view=%d wide=%d t=%.4f weight=%.4f error=%.5f\n",view,!!(ent->curstate.iuser4&VF_TR_WIDE),t,w,VectorLength(actual));}
 }
}

