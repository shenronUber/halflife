/* Reuse ACT_RUN's leg cycle, rotate its lower body onto the supporting wall,
   and compose the existing weapon/upper-body track above it. No model or
   historical sequence is replaced. Shared by visible bones and hitboxes. */
static void R_VFWallRunCombat(cl_entity_t *ent)
{
 if(!ent->player||ent==tr.viewent||!VF_PosePlayerModel(ent->model->name))return;
 mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
 mstudioseqdesc_t *sequences=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->seqindex);
 if(m_pStudioHeader->numbones<28||Q_strcmp(bones[8].name,"Bip01 Spine"))return;
 int gait=ent->curstate.gaitsequence;
 if(gait<=0||gait>=m_pStudioHeader->numseq)return;
 float yaw=VF_TR_Yaw(ent->curstate.iuser4),side=(ent->curstate.iuser4&VF_WR_RIGHT)?1.f:-1.f;
 float radians=yaw*(float)(M_PI/180);vec3_t normal={-sinf(radians)*side,cosf(radians)*side,0};
 vec3_t pos[MAXSTUDIOBONES];vec4_t q[MAXSTUDIOBONES];matrix3x4 running[9],base;
 float frame=bound(0.f,ent->curstate.fuser1,1.f)*(sequences[gait].numframes-1);
 R_VFSampleTrack(ent,gait,frame,127,0,pos,q);
 vec3_t angles={0,yaw,-side*60.f};
 Matrix3x4_CreateFromEntity(base,angles,ent->origin,1);
 for(int i=0;i<=8;++i){matrix3x4 local;Matrix3x4_FromOriginQuat(local,q[i],pos[i]);
  Matrix3x4_ConcatTransforms(running[i],bones[i].parent<0?base:running[bones[i].parent],local);
 }
 // Place the nearest sole on the real surface without penetrating it.
 float nearest=10000;
 for(int foot=4;foot<=7;foot+=3){
  float distance=(running[foot][0][3]-ent->curstate.vuser3[0])*normal[0]+(running[foot][1][3]-ent->curstate.vuser3[1])*normal[1];
  nearest=Q_min(nearest,distance);
 }
 float shift=bound(-24.f,3.f-nearest,24.f);
 for(int i=0;i<=8;++i)for(int axis=0;axis<3;++axis)running[i][axis][3]+=normal[axis]*shift;
 // Evaluate combat with the same aim/reload clock as ordinary standing.
 // The upper body's orientation is preserved while its spine follows hips.
 for(int i=0;i<4;++i)ent->curstate.controller[i]=ent->latched.prevcontroller[i]=127;
 m_pPlayerInfo=NULL;R_VFCanonicalBones(ent,false);
 matrix3x4 upper;Matrix3x4_Copy(upper,g_studio.bonestransform[8]);
 for(int axis=0;axis<3;++axis)upper[axis][3]=running[8][axis][3];
 R_VFMoveJoint(8,upper);
 for(int i=0;i<8;++i){Matrix3x4_Copy(g_studio.bonestransform[i],running[i]);Matrix3x4_Copy(g_studio.lighttransform[i],running[i]);}
 R_StudioSaveBones();R_StudioCalcAttachments();
 if(gpGlobals->developer>=2)gEngfuncs.Con_Printf("VFWallRunPose entity=%d gait=%d frame=%.3f side=%.0f roll=%.1f sole=%.4f sequence=%s\n",ent->index,gait,frame,side,-side*60.f,nearest+shift,sequences[ent->curstate.sequence].label);
}
