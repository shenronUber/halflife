/* Left-arm overlay only. The right arm, weapon, head and locomotion pose retain
 * the authored transforms. This file is independent of traversal/weapon data. */
#include "vf_headgear.h"
static int R_VFHeadgearBone( const char *name )
{
 mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
 for(int i=0;i<m_pStudioHeader->numbones;++i)if(!Q_strcmp(bones[i].name,name))return i;
 return -1;
}
static void R_VFHeadgearBlend( const matrix3x4 from,const matrix3x4 target,float weight,matrix3x4 out )
{
 vec3_t firstAngles,lastAngles,position;vec4_t first,last,q;
 Matrix3x4_AnglesFromMatrix(from,firstAngles);Matrix3x4_AnglesFromMatrix(target,lastAngles);
 AngleQuaternion(firstAngles,first,false);AngleQuaternion(lastAngles,last,false);QuaternionSlerp(first,last,weight,q);
 for(int i=0;i<3;++i)position[i]=from[i][3]*(1-weight)+target[i][3]*weight;
 Matrix3x4_FromOriginQuat(out,q,position);
}
static void R_VFHeadgearOpenHand( qboolean view,float weight )
{
 mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
 for(int b=0;b<m_pStudioHeader->numbones;++b){
  const char *name=bones[b].name;
  qboolean finger=view?(!Q_strncmp(name,"Bone",4)&&Q_atoi(name+4)>=43&&Q_atoi(name+4)<=62):!Q_strncmp(name,"Bip01 L Finger",14);
  if(!finger||bones[b].parent<0)continue;
  // Use this rig's open reference fingers without touching its authored keys.
  matrix3x4 inverse,local,bind,blend,posed;vec4_t q;
  R_VFInverseRigid(g_studio.bonestransform[bones[b].parent],inverse);
  Matrix3x4_ConcatTransforms(local,inverse,g_studio.bonestransform[b]);
  AngleQuaternion(bones[b].value+3,q,true);Matrix3x4_FromOriginQuat(bind,q,bones[b].value);
  if(view){
   int number=Q_atoi(name+4);
   if(number>=47){
    // A relaxed, cupped hand rather than a flat fan or a closed rifle grip.
    // This rig's fingers extend along local +Y; curl toward the palm (-Z).
    const float curls[4]={8,18,12,4};float angle=curls[(number-47)%4];
    if(number>=59)angle*=1.15f;
    float c=cosf(angle*(float)(M_PI/180)),s=sinf(angle*(float)(M_PI/180));
    matrix3x4 curl,curved;Matrix3x4_LoadIdentity(curl);
    curl[1][1]=c;curl[1][2]=s;curl[2][1]=-s;curl[2][2]=c;
    Matrix3x4_ConcatTransforms(curved,bind,curl);Matrix3x4_Copy(bind,curved);
   }
  }else if(Q_strstr(name,"Finger1")){
   // This body rig points the fingers along +X. Cup them gently toward
   // palmar -Z, instead of presenting a rigid flat plate at the forehead.
   qboolean tip=Q_strstr(name,"Finger11")!=NULL;
   if(tip){
    // The donor's reference has a 38-degree sideways grip in the distal
    // joint. Open it before curling toward the palm, so the tips point up.
    Matrix3x4_LoadIdentity(bind);
    for(int i=0;i<3;++i)bind[i][3]=bones[b].value[i];
   }
   float angle=tip?12:8;
   float c=cosf(angle*(float)(M_PI/180)),s=sinf(angle*(float)(M_PI/180));
   matrix3x4 curl,curved;Matrix3x4_LoadIdentity(curl);
   curl[0][0]=c;curl[0][2]=s;curl[2][0]=-s;curl[2][2]=c;
   Matrix3x4_ConcatTransforms(curved,bind,curl);Matrix3x4_Copy(bind,curved);
  }
  R_VFHeadgearBlend(local,bind,weight,blend);
  Matrix3x4_ConcatTransforms(posed,g_studio.bonestransform[bones[b].parent],blend);R_VFMoveJoint(b,posed);
 }
}
static void R_VFHeadgearGesture( cl_entity_t *ent,const vf_assembly_t *a )
{
 if(a->headgear_type<=0||a->headgear_type>HeadgearTypes)return;
 float phase=a->headgear_phase,w=HeadgearReach(phase);if(w<.00001f)return;
 qboolean view=ent==tr.viewent;
 if(VF_TR_Phase(ent->curstate.iuser4))return;
 int upper=R_VFHeadgearBone(view?"Bone04":"Bip01 L Arm1");
 int fore=R_VFHeadgearBone(view?"Bone40":"Bip01 L Arm2");
 int hand=R_VFHeadgearBone(view?"Bone42":"Bip01 L Hand");
 int head=view?-1:R_VFHeadgearBone("Bip01 Head");
 if(upper<0||fore<0||hand<0||(!view&&head<0))return;
 matrix3x4 goal;Matrix3x4_Copy(goal,g_studio.bonestransform[hand]);
 vec3_t contact,pole;float positionWeight=w,handWeight=w;
 if(view){
  // Lift the hand from its weapon grip, presenting the thumb edge, then
  // come back along the same path. Equipment moves while the hand is above us.
  float lift=phase<.32f?HeadgearSmooth((phase-.14f)/.18f):
             phase<.72f?1:1-HeadgearSmooth((phase-.72f)/.14f);
  if(phase<.14f)positionWeight=HeadgearSmooth(phase/.14f);
  else if(phase>.86f)positionWeight=HeadgearSmooth((1-phase)/.14f);
  else positionWeight=1;
  handWeight=phase<.14f?HeadgearSmooth(phase/.14f):phase>.86f?HeadgearSmooth((1-phase)/.14f):1;
  float lean=(18-10*lift)*(float)(M_PI/180),c=cosf(lean),s=sinf(lean);
  const float edgeCos=-.2588190451f,edgeSin=.9659258263f;
  for(int i=0;i<3;++i){
   float across=-RI.vright[i]*c+RI.vup[i]*s;
   goal[i][0]=across*edgeCos-RI.vforward[i]*edgeSin;
   goal[i][1]=RI.vright[i]*s+RI.vup[i]*c;
   goal[i][2]=across*edgeSin+RI.vforward[i]*edgeCos;
   contact[i]=RI.rvp.vieworigin[i]+RI.vforward[i]*(17-5*lift)-RI.vright[i]*(4.5f-2*lift)+RI.vup[i]*(-5+21*lift);
   pole[i]=RI.rvp.vieworigin[i]+RI.vforward[i]*3-RI.vright[i]*12-RI.vup[i]*15;
  }
 }else{
  // The hand meets the left upper rim rather than intersecting the face.
  float pose=0;const vf_part_t *moving=NULL;
  for(int n=0;n<a->count;++n)if(!Q_strcmp(a->parts[n].model,"models/vf_headgear/headgear.mdl")){moving=&a->parts[n];break;}
  float pivot[3],shift[3],angle;HeadgearTransform(a->headgear_type,1,pivot,&angle,shift);
  if(moving)pose=angle?moving->angles[1]/angle:0;
  HeadgearTransform(a->headgear_type,pose,pivot,&angle,shift);
  vec3_t point={1.8f,-5.8f,67.2f};
  if(a->headgear_type==5){point[1]=-6.9f;point[2]=66.6f;}
  float c=cosf(angle*(float)(M_PI/180)),s=sinf(angle*(float)(M_PI/180));
  float y=point[1]-pivot[1],z=point[2]-pivot[2];
  point[1]=pivot[1]+c*y-s*z+shift[1];point[2]=pivot[2]+s*y+c*z+shift[2];
  vec3_t local={-.182435f*(point[1]+.611241f)+.983218f*(point[2]-59.668064f),
               -.983218f*(point[1]+.611241f)-.182435f*(point[2]-59.668064f),point[0]-.23387f};
  Matrix3x4_VectorTransform(g_studio.bonestransform[head],local,contact);
  vec3_t elbow={-9,4,12};Matrix3x4_VectorTransform(g_studio.bonestransform[head],elbow,pole);
  float roll=110*(float)(M_PI/180),cr=cosf(roll),sr=sinf(roll);
  float tilt=12*(float)(M_PI/180),ct=cosf(tilt),st=sinf(tilt);
  for(int i=0;i<3;++i){
   // Rotate the whole hand toward the forehead. Palmar -Z faces back
   // toward the equipment; the open thumb passes behind the hand in front view.
   float up=g_studio.bonestransform[head][i][0];
   float front=g_studio.bonestransform[head][i][1];
   float side=g_studio.bonestransform[head][i][2];
   float along=up*ct-side*st,outward=up*st+side*ct;
   goal[i][0]=along;
   goal[i][1]=front*cr-outward*sr;
   goal[i][2]=front*sr+outward*cr;
  }
 }
 const vec3_t fpPalm={.3f,3,-1.45f},tpPalm={1.8f,-.2f,-1.55f};const float *palm=view?fpPalm:tpPalm;
 for(int i=0;i<3;++i)for(int j=0;j<3;++j)contact[i]-=goal[i][j]*palm[j];
 // Respect anatomical reach; never move the shoulder/torso to force contact.
 vec3_t shoulder,e,h,d;Matrix3x4_OriginFromMatrix(g_studio.bonestransform[upper],shoulder);
 Matrix3x4_OriginFromMatrix(g_studio.bonestransform[fore],e);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[hand],h);
 VectorSubtract(e,shoulder,d);float arm=VectorLength(d);
 if(view){mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);arm=VectorLength(bones[fore].value);}
 VectorSubtract(h,e,d);float lower=VectorLength(d),distance;
 VectorSubtract(contact,shoulder,d);distance=VectorLength(d);float reach=Q_max(.1f,arm+lower-.05f);
 if(view)reach*=.82f;
 if(distance>reach){VectorScale(d,reach/distance,d);VectorAdd(shoulder,d,contact);}
 for(int i=0;i<3;++i)goal[i][3]=contact[i];
 matrix3x4 blended;R_VFHeadgearBlend(g_studio.bonestransform[hand],goal,handWeight,blended);
 for(int i=0;i<3;++i)blended[i][3]=h[i]*(1-positionWeight)+contact[i]*positionWeight;
 Matrix3x4_Copy(goal,blended);
 int right=R_VFHeadgearBone(view?"Bone07":"Bip01 R Hand"),weapon=R_VFHeadgearBone(view?"Bone76":"VF_Weapon");
 matrix3x4 rightBefore,weaponBefore;
 if(right>=0)Matrix3x4_Copy(rightBefore,g_studio.bonestransform[right]);
 if(weapon>=0)Matrix3x4_Copy(weaponBefore,g_studio.bonestransform[weapon]);
 if(R_VFReach(upper,fore,hand,goal,pole,view)){
  R_VFHeadgearOpenHand(view,handWeight);
  R_StudioSaveBones();R_StudioCalcAttachments();
  if(gpGlobals->developer>=2){
   float rightError=0,weaponError=0;
   for(int i=0;i<3;++i)for(int j=0;j<4;++j){if(right>=0)rightError=Q_max(rightError,fabsf(rightBefore[i][j]-g_studio.bonestransform[right][i][j]));if(weapon>=0)weaponError=Q_max(weaponError,fabsf(weaponBefore[i][j]-g_studio.bonestransform[weapon][i][j]));}
   VectorSubtract(contact,shoulder,d);
   float wristNormal=0;for(int i=0;i<3;++i)wristNormal+=goal[i][2]*(view?RI.vforward[i]:g_studio.bonestransform[head][i][1]);
   float palmY=0;if(view){vec3_t actual;Matrix3x4_VectorTransform(g_studio.bonestransform[hand],palm,actual);VectorSubtract(actual,RI.rvp.vieworigin,actual);float depth=DotProduct(actual,RI.vforward);if(depth>.01f)palmY=DotProduct(actual,RI.vup)/depth;}
   gEngfuncs.Con_Printf("VFHeadgear pose: view=%d type=%d phase=%.4f reach=%.4f right_error=%.6f weapon_error=%.6f wrist=%.3f,%.3f,%.3f wrist_normal=%.4f extension=%.4f palm_y=%.4f\n",view,a->headgear_type,phase,w,rightError,weaponError,goal[0][3],goal[1][3],goal[2][3],wristNormal,VectorLength(d)/(arm+lower),palmY);
  }
 }
}
