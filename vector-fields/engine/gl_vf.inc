/* Vector Fields optional renderer extension. Included here to share the Studio pose cache. */
#include "vf_engine_api.h"
#include "vf_traversal.h"
#include "vf_player_pose.h"
#include "vf_assembly_policy.h"

typedef struct
{
	int entity;
	vf_assembly_t definition;
	model_t *rig, *parts[VF_MAX_PARTS];
	short bone_map[VF_MAX_PARTS][MAXSTUDIOBONES];
} vf_resolved_t;

typedef struct
{
	char path[64];
	model_t *model;
} vf_cached_model_t;

unsigned int vf_topology_resolves,vf_pose_updates;
static vf_resolved_t vf_assemblies[VF_MAX_ASSEMBLIES];
static vf_cached_model_t vf_models[2048];
static vf_render_stats_t vf_stats;
static qboolean vf_drawing;
static qboolean vf_first_person_body;
static vf_resolved_t vf_preview_cache;

static model_t *R_VFLoadModel( const char *path )
{
	if( !path || !memchr( path, 0, 64 ) || Q_strncmp( path, "models/", 7 ) || Q_strstr( path, ".." ) || Q_strchr( path, ':' ))
		return NULL;
	for( int i = 0; i < vf_stats.cached_models; i++ )
	{
		if( !Q_strcmp( vf_models[i].path, path ))
		{
			vf_stats.cache_hits++;
			return vf_models[i].model;
		}
	}
	if( vf_stats.cached_models >= ARRAYSIZE( vf_models ))
		return NULL;
	model_t *model = gEngfuncs.Mod_ForName( path, false, false );
	if( !model || model->type != mod_studio )
		return NULL;
	vf_cached_model_t *entry = &vf_models[vf_stats.cached_models++];
	Q_strncpy( entry->path, path, sizeof( entry->path ));
	entry->model = model;
	vf_stats.model_loads++;
	return model;
}

static qboolean R_VFResolve( const vf_assembly_t *in, vf_resolved_t *out )
{
	memset( out, 0, sizeof( *out ));
	if( !VF_AssemblyValid(in) )
		return false;
	if(in->headgear_type<0||in->headgear_type>5||IS_NAN(in->headgear_phase)||in->headgear_phase<0||in->headgear_phase>1)return false;
	out->rig = R_VFLoadModel( in->rig );
	if( !out->rig )
		return false;
	for( int i = 0; i < in->count; i++ )
	{
		const vf_part_t *part = &in->parts[i];
		if( IS_NAN( part->scale ) || part->scale < 0 || part->scale > 4 ) return false;
		if( part->body < 0 || part->skin < 0 || part->mode < VF_PART_MERGE || part->mode > VF_PART_SOCKET || !memchr( part->bone, 0, sizeof( part->bone )))
			return false;
		for( int j = 0; j < 3; j++ )
			if( IS_NAN( part->offset[j] ) || IS_NAN( part->angles[j] ) || fabs( part->offset[j] ) > 4096 || fabs( part->angles[j] ) > 3600 )
				return false;
		out->parts[i] = R_VFLoadModel( part->model );
		if( !out->parts[i] )
			return false;
		if( part->mode == VF_PART_SOCKET )
		{
			studiohdr_t *hdr = gEngfuncs.Mod_Extradata( mod_studio, out->rig );
			mstudiobone_t *bones = (void *)((byte *)hdr + hdr->boneindex );
			int bone;
			for( bone = 0; bone < hdr->numbones; bone++ )
				if( !Q_stricmp( bones[bone].name, part->bone )) break;
			if( bone == hdr->numbones ) return false;
		}
		else
		{
			studiohdr_t *rig = gEngfuncs.Mod_Extradata( mod_studio, out->rig );
			studiohdr_t *child = gEngfuncs.Mod_Extradata( mod_studio, out->parts[i] );
			mstudiobone_t *rb = (void *)((byte *)rig + rig->boneindex );
			mstudiobone_t *cb = (void *)((byte *)child + child->boneindex );
			for( int b = 0; b < child->numbones; b++ )
			{
				int parent;
				for( parent = 0; parent < rig->numbones; parent++ )
					if( !Q_stricmp( cb[b].name, rb[parent].name )) break;
				if( parent == rig->numbones && !Q_strcmp(part->model,"models/vf_headgear/headgear.mdl") &&
                    (!Q_strcmp(cb[b].name,"VF_Headgear")||!Q_strcmp(cb[b].name,"VF_HeadgearFlex")) &&
                    cb[b].parent>=0 && !Q_strcmp(cb[cb[b].parent].name,"Bip01 Head"))
                    for(parent=0;parent<rig->numbones;++parent)if(!Q_strcmp(rb[parent].name,"Bip01 Head"))break;
				if( parent == rig->numbones ) return false;
				out->bone_map[i][b] = parent;
			}
		}
	}
	++vf_topology_resolves;
	out->definition = *in;
	return true;
}

static vf_resolved_t *R_VFFind( int entity )
{
	for( int i = 0; i < VF_MAX_ASSEMBLIES; i++ )
		if( vf_assemblies[i].entity == entity && entity != 0 ) return &vf_assemblies[i];
	return NULL;
}

static int R_VFSetAssembly( int entity, const vf_assembly_t *definition )
{
	if( entity == 0 || entity < -1 || entity >= MAX_EDICTS || !definition ) return 0;
	vf_resolved_t *entry = R_VFFind( entity );
	if( entry && !memcmp( &entry->definition, definition, sizeof( *definition ))) return 1;
	if( !VF_AssemblyValid(definition) ) { vf_stats.rejected++; return 0; }
	if( entry && VF_AssemblySameTopology(&entry->definition,definition) ) { entry->definition=*definition; ++vf_pose_updates; return 1; }
	if( !entry )
		for( int i = 0; i < VF_MAX_ASSEMBLIES; i++ )
			if( !vf_assemblies[i].entity ) { entry = &vf_assemblies[i]; break; }
	vf_resolved_t candidate;
	if( !entry || !R_VFResolve( definition, &candidate )) { vf_stats.rejected++; return 0; }
	candidate.entity = entity;
	*entry = candidate;
	return 1;
}

static void R_VFClearAssembly( int entity )
{
	if( !entity ) memset( vf_assemblies, 0, sizeof( vf_assemblies ));
	else { vf_resolved_t *entry = R_VFFind( entity ); if( entry ) memset( entry, 0, sizeof( *entry )); }
}

void R_VFReset( void )
{
	R_VFClearAssembly( 0 );
	memset( vf_models, 0, sizeof( vf_models ));
	memset( &vf_stats, 0, sizeof( vf_stats ));
	vf_topology_resolves=vf_pose_updates=0;
	memset( &vf_preview_cache, 0, sizeof( vf_preview_cache ));
	vf_drawing = false;
}

static model_t *R_VFPlayerModel( int entity )
{
	vf_resolved_t *entry = R_VFFind( entity );
	if( entry ) return entry->rig;
 // Before VFState arrives (or if an optional assembly is unavailable), use
 // the server's complete fitted body rather than Half-Life's gordon/HEV default.
 cl_entity_t *player = CL_GetEntityByIndex( entity );
 if( player && player->model && VF_PosePlayerModel(player->model->name)) return player->model;
 return NULL;
}

static void R_VFPreparePart( cl_entity_t *piece, const vf_part_t *part, model_t *model, const short *mapping )
{
	piece->model = model;
	piece->curstate.body = part->body;
	piece->curstate.skin = part->skin;
	RI.currententity = piece;
	RI.currentmodel = model;
	R_StudioSetHeader( gEngfuncs.Mod_Extradata( mod_studio, model ));
	if( part->mode == VF_PART_MERGE )
	{
		for( int b = 0; b < m_pStudioHeader->numbones; b++ )
		{
			Matrix3x4_Copy( g_studio.bonestransform[b], g_studio.cached_bonestransform[mapping[b]] );
			Matrix3x4_Copy( g_studio.lighttransform[b], g_studio.cached_lighttransform[mapping[b]] );
            mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
            if(!Q_strcmp(part->model,"models/vf_headgear/headgear.mdl") &&
                (!Q_strcmp(bones[b].name,"VF_Headgear")||!Q_strcmp(bones[b].name,"VF_HeadgearFlex"))){
                matrix3x4 local,posed,light;Matrix3x4_CreateFromEntity(local,part->angles,part->offset,1);
                Matrix3x4_ConcatTransforms(posed,g_studio.cached_bonestransform[mapping[b]],local);
                Matrix3x4_ConcatTransforms(light,g_studio.cached_lighttransform[mapping[b]],local);
                float weight=!Q_strcmp(bones[b].name,"VF_HeadgearFlex")?.5f:1.f;
                for(int r=0;r<3;++r)for(int c=0;c<4;++c){
                    g_studio.bonestransform[b][r][c]=g_studio.cached_bonestransform[mapping[b]][r][c]*(1-weight)+posed[r][c]*weight;
                    g_studio.lighttransform[b][r][c]=g_studio.cached_lighttransform[mapping[b]][r][c]*(1-weight)+light[r][c]*weight;
                }
            }
		}
	}
	else
	{
		for( int i = 0; i < g_studio.cached_numbones; i++ )
		{
			if( Q_stricmp( part->bone, g_studio.cached_bonenames[i] )) continue;
			matrix3x4 local;
			Matrix3x4_CreateFromEntity( local, part->angles, part->offset, part->scale > 0 ? part->scale : 1.0f );
			Matrix3x4_ConcatTransforms( g_studio.rotationmatrix, g_studio.cached_bonestransform[i], local );
			piece->curstate.sequence = 0;
			piece->curstate.frame = 0;
			piece->curstate.framerate = 0;
			memset( &piece->latched, 0, sizeof( piece->latched ));
			R_StudioSetupBones( piece );
			break;
		}
	}
}

static void R_VFBounds( vec3_t mins, vec3_t maxs )
{
	for( int part = 0; part < m_pStudioHeader->numbodyparts; part++ )
	{
		R_StudioSetupModel( part, (void **)&m_pBodyPart, (void **)&m_pSubModel );
		const vec3_t *vertices = (void *)((byte *)m_pStudioHeader + m_pSubModel->vertindex );
		const byte *bones = (byte *)m_pStudioHeader + m_pSubModel->vertinfoindex;
		for( int v = 0; v < m_pSubModel->numverts; v++ )
		{
			vec3_t point;
			if( FBitSet( m_pStudioHeader->flags, STUDIO_HAS_BONEWEIGHTS ) && m_pSubModel->blendvertinfoindex )
			{
				mstudioboneweight_t *weights = (void *)((byte *)m_pStudioHeader + m_pSubModel->blendvertinfoindex );
				matrix3x4 skin;
				R_StudioComputeSkinMatrix( &weights[v], skin );
				Matrix3x4_VectorTransform( skin, vertices[v], point );
			}
			else Matrix3x4_VectorTransform( g_studio.bonestransform[bones[v]], vertices[v], point );
			AddPointToBounds( point, mins, maxs );
		}
	}
}

static void R_VFLighting( cl_entity_t *parent, alight_t *light, vec3_t dir )
{
	light->plightvec = dir;
	if( !FBitSet( RI.rvp.flags, RF_DRAW_WORLD ))
	{
		// A menu model lives at the origin, often below the map floor. Use a
		// neutral studio light instead of sampling that unrelated world point.
		light->ambientlight = 100; light->shadelight = 90;
		VectorSet( light->color, 1, 1, 1 );
		VectorSet( dir, -.8f, -.3f, -1 ); VectorNormalize( dir );
		g_studio.numlocallights = 0;
		R_StudioSetupLighting( light );
		return;
	}
	R_EntityDynamicLight( parent, light, FBitSet( RI.rvp.flags, RF_DRAW_WORLD ), g_studio.time, g_studio.lightspot, g_studio.lightvec );
	R_StudioEntityLight( light );
	R_StudioSetupLighting( light );
}

static void R_VFMuzzleAttachment( cl_entity_t *parent )
{
 float front = -999999.0f; vec3_t center; int count = 0, bone = 0;
 VectorClear( center );
 for( int pass = 0; pass < 2; ++pass )
 for( int part = 0; part < m_pStudioHeader->numbodyparts; ++part )
 {
  R_StudioSetupModel( part, (void **)&m_pBodyPart, (void **)&m_pSubModel );
  const vec3_t *vertices = (void *)((byte *)m_pStudioHeader + m_pSubModel->vertindex);
  const byte *bones = (byte *)m_pStudioHeader + m_pSubModel->vertinfoindex;
  for( int v = 0; v < m_pSubModel->numverts; ++v )
  {
   if( pass == 0 ) { if( vertices[v][1] > front ) front = vertices[v][1]; }
   else if( fabsf( vertices[v][1] - front ) < 0.1f ) { VectorAdd( center, vertices[v], center ); bone = bones[v]; count++; }
  }
 }
 if( count ) {
  vec3_t along,up;
  VectorScale( center, 1.0f / count, center );
  Matrix3x4_VectorTransform( g_studio.bonestransform[bone], center, parent->attachment[0] );
  VectorCopy(center,along);along[1]+=8.0f;
  VectorCopy(center,up);up[2]+=8.0f;
  Matrix3x4_VectorTransform( g_studio.bonestransform[bone], along, parent->attachment[1] );
  Matrix3x4_VectorTransform( g_studio.bonestransform[bone], up, parent->attachment[3] );
 }
}
// The legacy torso zone includes its sleeves. Keep those third-person arms
// out of the own-body pass; the viewmodel already supplies both sleeves.
static qboolean R_VFDrawBodyMesh( short *commands, vec3_t *normals, float s, float t )
{
 if(!vf_first_person_body)return false;
 const byte *assigned=(byte *)m_pStudioHeader+m_pSubModel->vertinfoindex;
 const mstudiobone_t *bones=(void *)((byte *)m_pStudioHeader+m_pStudioHeader->boneindex);
 qboolean hide[MAXSTUDIOBONES];
 for(int b=0;b<m_pStudioHeader->numbones;++b){
  int parent=b;hide[b]=false;
  while(parent>=0){if(Q_strstr(bones[parent].name," Arm")){hide[b]=true;break;}parent=bones[parent].parent;}
 }
 pglBegin(GL_TRIANGLES);
 for(int count;(count=*commands++);){
  qboolean fan=count<0;count=abs(count);
  for(int i=2;i<count;++i){
   short *tri[3]={commands+(fan?0:(i&1)?i-1:i-2)*4,commands+(fan?i-1:(i&1)?i-2:i-1)*4,commands+i*4};
   if(hide[assigned[tri[0][0]]]||hide[assigned[tri[1][0]]]||hide[assigned[tri[2][0]]])continue;
   for(int j=0;j<3;++j){short *v=tri[j];R_StudioSetColorBegin(v,normals);pglTexCoord2f(v[2]*s,v[3]*t);pglVertex3fv(g_studio.verts[v[0]]);}
  }
  commands+=count*4;
 }
 pglEnd();return true;
}

static void R_VFDrawParts( cl_entity_t *parent, const vf_resolved_t *assembly, qboolean bounds, vec3_t mins, vec3_t maxs )
{
	alight_t light;
	vec3_t dir;
	matrix3x4 root;
	Matrix3x4_Copy( root, g_studio.rotationmatrix );
	for( int i = 0; i < assembly->definition.count; i++ )
	{
		vf_part_t part=assembly->definition.parts[i];
		if(vf_first_person_body){
		 if(part.mode!=VF_PART_MERGE||Q_strncmp(part.model,"models/vf_skins/",16))continue;
		 // The forward seated presentation shows legs; an advanced torso would
		 // put the cut-open vest directly in front of the eye.
		 part.body&=VF_TR_Phase(parent->curstate.iuser4)==VF_TR_SLIDE?(8|16):(2|8|16);if(!part.body)continue;
		}
		cl_entity_t piece = *parent;
		Matrix3x4_Copy( g_studio.rotationmatrix, root );
		R_VFPreparePart( &piece, &part, assembly->parts[i], assembly->bone_map[i] );
		if(vf_first_person_body&&gpGlobals->developer>=2){vec3_t lo,hi;ClearBounds(lo,hi);R_VFBounds(lo,hi);gEngfuncs.Con_Printf("VFBodyPart body=%d bounds=%.3f,%.3f,%.3f:%.3f,%.3f,%.3f\n",part.body,lo[0],lo[1],lo[2],hi[0],hi[1],hi[2]);}
		if( bounds ) { R_VFBounds( mins, maxs ); continue; }
		cl_entity_t *viewent = tr.viewent;
        // Status shells belong to the fitted hands/sleeves, never the R1 sockets.
        // Preserve the original mesh and pose; Studio adds its shell pass.
        if( parent == viewent && piece.curstate.renderfx == kRenderFxGlowShell &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_r01/r01_fp_gloves.mdl" ) &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_traversal/ledge_gloves.mdl" ) &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_traversal/ledge_sleeves.mdl" ) &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_inspect/inspect_gloves.mdl" ) &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_inspect/inspect_sleeves.mdl" ) &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_melee/melee_gloves.mdl" ) &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_melee/melee_sleeves.mdl" ) &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_r01/r01_fp_sleeves.mdl" ))
            piece.curstate.renderfx = kRenderFxNone;
        if(parent==viewent&&parent->curstate.renderfx==kRenderFxGlowShell&&gpGlobals->developer>=2)
            gEngfuncs.Con_Printf("VFStatusShell part=%s arms=%d\n",part.model,piece.curstate.renderfx==kRenderFxGlowShell);
		// Socket matrices already contain the parent's handedness. Keep the
		// renderer's viewmodel culling/lighting convention for each child.
		if( parent == viewent ) tr.viewent = &piece;
		g_studio.framecount++;
		R_VFLighting( &piece, &light, dir );
		R_StudioRenderModel();
        if( !strncmp(assembly->definition.parts[i].model,"models/vf_r01/r01_muzzle_",24) ) R_VFMuzzleAttachment(parent);
		tr.viewent = viewent;
		if( assembly->definition.parts[i].mode == VF_PART_MERGE ) vf_stats.merged_parts++;
		else vf_stats.socket_parts++;
	}
	Matrix3x4_Copy( g_studio.rotationmatrix, root );
}

#include "vf_player_pose.inc"

#include "gl_vf_headgear.inc"
static void R_VFOwnBodyYaw( cl_entity_t *ent )
{
 if(!vf_first_person_body||VF_TR_Phase(ent->curstate.iuser4))return;
 // Studio gait faces velocity while the subjective body faces our look yaw.
 // Rotate only this private render copy; preserve gait animation and physics.
 float current=atan2f(g_studio.rotationmatrix[1][0],g_studio.rotationmatrix[0][0])*(float)(180/M_PI);
 float target=RI.rvp.viewangles[YAW],delta=VF_TR_Angle(target-current);
 matrix3x4 turn,posed;vec3_t angles={0,delta,0},rotated;
 Matrix3x4_CreateFromEntity(turn,angles,vec3_origin,1);
 Matrix3x4_VectorRotate(turn,ent->origin,rotated);
 for(int i=0;i<3;++i)turn[i][3]=ent->origin[i]-rotated[i];
 for(int bone=0;bone<m_pStudioHeader->numbones;++bone){
  Matrix3x4_ConcatTransforms(posed,turn,g_studio.bonestransform[bone]);Matrix3x4_Copy(g_studio.bonestransform[bone],posed);
  Matrix3x4_ConcatTransforms(posed,turn,g_studio.lighttransform[bone]);Matrix3x4_Copy(g_studio.lighttransform[bone],posed);
 }
 Matrix3x4_ConcatTransforms(posed,turn,g_studio.rotationmatrix);Matrix3x4_Copy(g_studio.rotationmatrix,posed);
 R_StudioSaveBones();
 if(gpGlobals->developer>=2){float actual=atan2f(g_studio.rotationmatrix[1][0],g_studio.rotationmatrix[0][0])*(float)(180/M_PI);
  gEngfuncs.Con_Printf("VFBodyOrientation look=%.4f gait=%.4f rendered=%.4f error=%.6f\n",target,current,actual,fabsf(VF_TR_Angle(actual-target)));}
}
static qboolean R_VFDrawAssembly( cl_entity_t *ent, const vf_resolved_t *assembly, int flags )
{
	if( vf_drawing ) return false;
	if( !assembly ) return false;
	cl_entity_t saved = *ent;
	model_t *oldmodel = RI.currentmodel;
	vf_drawing = true;
	ent->model = assembly->rig;
	ent->curstate.body = assembly->definition.body;
	ent->curstate.skin = assembly->definition.skin;
	if( assembly->definition.replace_carried ) ent->curstate.weaponmodel = 0;
	RI.currentmodel = ent->model;
 // The local predicted entity keeps an older player pose. The ordinary
 // Studio renderer reads the current player-state packet instead. Keep that
 // same gait/transition source for our temporary assembled body as well.
 if(ent->player&&ent->index==gp_cl->playernum+1&&!VF_TR_Phase(ent->curstate.iuser4)){
  entity_state_t *current=gEngfuncs.pfnGetPlayerState(ent->index-1);
  if(current&&!VF_TR_Phase(current->iuser4)){
   ent->curstate.gaitsequence=current->gaitsequence;
   VectorCopy(current->vuser1,ent->curstate.vuser1);
   VectorCopy(current->vuser2,ent->curstate.vuser2);
   VectorCopy(current->vuser4,ent->curstate.vuser4);
  }
 }
	// The vault reaches a world-space support. Its carrier contains the right
	// sleeve, so draw it after IK alongside its weapon sockets, not beforehand.
	qboolean deferred = assembly->definition.draw_rig && ent==tr.viewent && VF_TR_Phase(ent->curstate.iuser4)==VF_TR_VAULT;
	int base_flags = assembly->definition.draw_rig && !deferred ? flags : flags & ~STUDIO_RENDER;
	int drawn = ent->player ? R_StudioDrawPlayer( base_flags, &ent->curstate ) : R_StudioDrawModel( base_flags );
	vf_stats.pose_evaluations++;
 if( drawn && R_VFCanonicalPlayer(ent) ) R_VFCanonicalBones(ent,true);
 if( drawn && !vf_first_person_body && assembly->definition.replace_carried ) R_VFPlayerTorsoYaw( ent,R_VFCanonicalPlayer(ent) );
 if( drawn ) R_VFSlideCombat( ent );
 if( drawn ) R_VFLedgePalms( ent );
 if( drawn ) R_VFVaultPalm( ent );
 if( drawn ) R_VFHeadgearGesture( ent, &assembly->definition );
 if( drawn ) R_VFOwnBodyYaw( ent );
 if(drawn&&R_VFCanonicalPlayer(ent)&&!vf_first_person_body&&gEngfuncs.pfnGetCvarFloat("developer")>=3)R_VFAuditPlayerPose("render",ent);
 if(drawn&&deferred&&(flags&STUDIO_RENDER)){
  alight_t light;vec3_t dir;R_VFLighting(ent,&light,dir);g_studio.framecount++;R_StudioRenderModel();
 }
 if(drawn&&ent->player&&gpGlobals->developer>=2){vec3_t hip,left,right;
  Matrix3x4_OriginFromMatrix(g_studio.bonestransform[1],hip);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[4],left);Matrix3x4_OriginFromMatrix(g_studio.bonestransform[7],right);
  gEngfuncs.Con_Printf("VFBodyFeet phase=%d hip=%.3f,%.3f,%.3f left=%.3f,%.3f,%.3f right=%.3f,%.3f,%.3f own=%d origin=%.3f,%.3f,%.3f look=%.3f,%.3f\n",VF_TR_Phase(ent->curstate.iuser4),hip[0],hip[1],hip[2],left[0],left[1],left[2],right[0],right[1],right[2],vf_first_person_body,ent->origin[0],ent->origin[1],ent->origin[2],RI.rvp.viewangles[YAW],RI.rvp.viewangles[PITCH]);}
	if( drawn && (flags & STUDIO_RENDER) ) R_VFDrawParts( ent, assembly, false, NULL, NULL );
	if( drawn && (flags & STUDIO_RENDER) && ent->player && assembly->definition.replace_carried ) vf_stats.weapon_draws++;
	// A separate carried model is drawn only when the assembly does not replace it.
	if( drawn && (flags & STUDIO_RENDER) && ent->player && !assembly->definition.draw_rig && ent->curstate.weaponmodel )
	{
		model_t *weapon = CL_ModelHandle( ent->curstate.weaponmodel );
		if( weapon && weapon->type == mod_studio )
		{
			cl_entity_t piece = *ent;
			piece.model = weapon; piece.curstate.body = 0;
			RI.currententity = &piece; RI.currentmodel = weapon;
			R_StudioSetHeader( gEngfuncs.Mod_Extradata( mod_studio, weapon ));
			R_StudioMergeBones( &piece, weapon );
			alight_t light; vec3_t dir;
			R_VFLighting( &piece, &light, dir );
			g_studio.framecount++;
			R_StudioRenderModel();
			vf_stats.weapon_draws++;
		}
	}
	vec3_t attachments[4];
	memcpy( attachments, ent->attachment, sizeof( attachments ));
	*ent = saved;
	memcpy( ent->attachment, attachments, sizeof( attachments ));
	RI.currententity = ent;
	RI.currentmodel = oldmodel;
	vf_drawing = false;
	return true;
}

static qboolean R_VFDrawRegistered( cl_entity_t *ent, int flags )
{
 return R_VFDrawAssembly(ent,R_VFFind(ent==tr.viewent?-1:ent->index),flags);
}

// Render the same equipped lower body in world space, with ordinary world
// depth and occlusion. The viewmodel supplies the arms; exclude the head,
// third-person arms and carried weapon rather than drawing them twice.
static void R_VFDrawFirstPersonBody( void )
{
 static cvar_t *ownBody,*slideForward;
 if(!ownBody)ownBody=gEngfuncs.Cvar_Get("vf_first_person_body","1",0,"Show equipped first-person lower body");
 if(!slideForward)slideForward=gEngfuncs.Cvar_Get("vf_slide_body_forward","0",0,"First-person slide body presentation along travel yaw");
 if(!ownBody->value||!FBitSet(RI.rvp.flags,RF_DRAW_WORLD))return;
 cl_entity_t *local=CL_GetEntityByIndex(gp_cl->playernum+1);
 if(!local||!local->player||!local->model)return;
 vf_resolved_t *registered=R_VFFind(local->index);if(!registered)return;
 if(!VF_PosePlayerModel(registered->definition.rig))return;
 int count=0,mask=0;
 for(int i=0;i<registered->definition.count;++i){
  const vf_part_t *part=&registered->definition.parts[i];
  int visible=part->body&(VF_TR_Phase(local->curstate.iuser4)==VF_TR_SLIDE?(8|16):(2|8|16));
  if(part->mode!=VF_PART_MERGE||!visible||Q_strncmp(part->model,"models/vf_skins/",16))continue;
  ++count;mask|=visible;
 }
 if(!count)return;
 ref_instance_t saved=RI;float blend=tr.blend;qboolean flip=tr.fFlipViewModel;
 cl_entity_t entity=*local;tr.fFlipViewModel=false;tr.blend=1;
 // This legacy rig leans its chest ahead of the collision eye. Keep the
 // visual body behind that eye; this does not move player/camera physics.
 int phase=VF_TR_Phase(entity.curstate.iuser4);
 float visualYaw=phase?VF_TR_Yaw(entity.curstate.iuser4):RI.rvp.viewangles[YAW];
 if(!phase)entity.angles[YAW]=visualYaw;
 float bodyYaw=visualYaw*(float)(M_PI/180);
 // Put the seated legs inside the lower forward view. This offset belongs
 // only to our presentation copy and never follows camera pitch or yaw.
 float retreat=phase==VF_TR_SLIDE?-bound(-18.0f,slideForward->value,48.0f):18;
 entity.origin[0]-=retreat*cosf(bodyYaw);entity.origin[1]-=retreat*sinf(bodyYaw);
 RI.currententity=&entity;RI.currentmodel=entity.model;
 // Hide the collar/upper chest around the legacy eye. This plane clips
 // geometry cleanly, instead of exposing the inside of the open neck mesh.
 float eyeGap=phase==VF_TR_VAULT||phase==VF_TR_WALL_JUMP?30:2;
 GLdouble collar[4]={0,0,-1,RI.rvp.vieworigin[2]-eyeGap};
 GLenum bodyCull=glState.faceCull;GL_Cull(GL_NONE);
 pglClipPlane(GL_CLIP_PLANE5,collar);pglEnable(GL_CLIP_PLANE5);
 // A wider projection reveals the seated boots at a level look. The pose
 // remains in world space; restore the ordinary projection before other draws.
 if(phase==VF_TR_SLIDE){pglMatrixMode(GL_PROJECTION);pglPushMatrix();pglScalef(.5f,.5f,1);pglMatrixMode(GL_MODELVIEW);}
 vf_first_person_body=true;
 R_StudioSetupTimings();int drawn=R_VFDrawRegistered(&entity,STUDIO_RENDER);
 vf_first_person_body=false;
 if(phase==VF_TR_SLIDE){pglMatrixMode(GL_PROJECTION);pglPopMatrix();pglMatrixMode(GL_MODELVIEW);}
 pglDisable(GL_CLIP_PLANE5);
 GL_Cull(bodyCull);
 if(drawn&&gpGlobals->developer>=2)gEngfuncs.Con_Printf("VFFirstPersonBody parts=%d mask=%d phase=%d origin=%.3f,%.3f,%.3f\n",count,mask,VF_TR_Phase(entity.curstate.iuser4),entity.origin[0],entity.origin[1],entity.origin[2]);
 RI=saved;tr.blend=blend;tr.fFlipViewModel=flip;
}

static int R_VFSequenceInfo( const char *path, int sequence, char *name, int capacity, float *duration )
{
	model_t *model = R_VFLoadModel( path );
	if( !model ) return 0;
	studiohdr_t *hdr = gEngfuncs.Mod_Extradata( mod_studio, model );
	if( sequence < 0 || sequence >= hdr->numseq ) return 0;
	mstudioseqdesc_t *seq = (void *)((byte *)hdr + hdr->seqindex );
	if( name && capacity > 0 ) Q_strncpy( name, seq[sequence].label, capacity );
	if( duration ) *duration = seq[sequence].fps > 0 ? seq[sequence].numframes / seq[sequence].fps : 0;
	return hdr->numseq;
}

static int R_VFDrawPreview( const vf_preview_t *view, const vf_assembly_t *definition )
{
	double start = gEngfuncs.pfnTime();
	if( !view || !definition || view->size != sizeof( *view ) || view->width <= 0 || view->height <= 0 || view->width > 16384 || view->height > 16384 || IS_NAN( view->seconds ) || IS_NAN( view->yaw ) || IS_NAN( view->zoom ) || view->zoom <= 0 )
		{ vf_stats.rejected++; return 0; }
	if( !vf_preview_cache.rig || memcmp( &vf_preview_cache.definition, definition, sizeof( *definition )))
	{
		vf_resolved_t candidate;
		if( !R_VFResolve( definition, &candidate )) { vf_stats.rejected++; return 0; }
		vf_preview_cache = candidate;
	}
	const vf_resolved_t assembly = vf_preview_cache;
	ref_instance_t saved = RI;
	qboolean saved_flip = tr.fFlipViewModel;
	GLenum saved_cull = glState.faceCull;
	tr.fFlipViewModel = false;
	cl_entity_t ent;
	memset( &ent, 0, sizeof( ent ));
	ent.model = assembly.rig;
	ent.curstate.body = definition->body;
	ent.curstate.skin = definition->skin;
	ent.curstate.renderamt = 255;
	ent.curstate.scale = 1;
	ent.curstate.effects = EF_NOSHADOW;
	ent.angles[1] = view->yaw;
	VectorCopy( ent.angles, ent.curstate.angles );
	studiohdr_t *hdr = gEngfuncs.Mod_Extradata( mod_studio, ent.model );
	// Preview entities have no game-side SetBoneController call. Zero bytes
	// would apply -30 degrees on each of the four torso controllers.
	mstudiobonecontroller_t *controls = (void *)((byte *)hdr + hdr->bonecontrollerindex);
	for( int i = 0; i < hdr->numbonecontrollers; i++ )
	{
		int index = controls[i].index;
		if( index < 0 || index > 3 || controls[i].end == controls[i].start ) continue;
		float neutral = -controls[i].start / ( controls[i].end - controls[i].start );
		ent.curstate.controller[index] = (byte)bound( 0, (int)( neutral * 255 + .5f ), 255 );
		ent.latched.prevcontroller[index] = ent.curstate.controller[index];
	}
	ent.curstate.sequence = bound( 0, view->sequence, hdr->numseq - 1 );
	mstudioseqdesc_t *seq = (void *)((byte *)hdr + hdr->seqindex );
	seq += ent.curstate.sequence;
	float frame = fmodf( Q_max( 0, view->seconds ) * seq->fps, Q_max( 1, seq->numframes - 1 ));
	ent.curstate.frame = seq->numframes > 1 ? frame * 256 / ( seq->numframes - 1 ) : 0;
	RI.rvp.flags = 0;
	RI.currententity = &ent;
	RI.currentmodel = ent.model;
	R_StudioSetupTimings();
	R_StudioDrawModel( 0 );
	vf_stats.pose_evaluations++;
	vec3_t mins, maxs, center;
	ClearBounds( mins, maxs );
	if( definition->draw_rig ) R_VFBounds( mins, maxs );
	R_VFDrawParts( &ent, &assembly, true, mins, maxs );
	if( mins[0] > maxs[0] ) { RI = saved; tr.fFlipViewModel = saved_flip; return 0; }
	VectorAverage( mins, maxs, center );
	float aspect = view->width / (float)view->height;
	float halfheight = Q_max(( maxs[2] - mins[2] ) * .5f, ( maxs[1] - mins[1] ) * .5f / aspect );
	float distance = halfheight * 1.15f / tanf( DEG2RAD( 17.5f )) / bound( .4f, view->zoom, 1.15f ) + ( maxs[0] - mins[0] ) * .5f;
	ref_viewpass_t pass;
	memset( &pass, 0, sizeof( pass ));
	pass.viewport[0] = view->x; pass.viewport[1] = view->y; pass.viewport[2] = view->width; pass.viewport[3] = view->height;
	pass.fov_y = 35;
	pass.fov_x = RAD2DEG( 2 * atanf( tanf( DEG2RAD( pass.fov_y * .5f )) * aspect ));
	VectorCopy( center, pass.vieworigin );
	pass.vieworigin[0] += Q_max( 8, distance );
	pass.viewangles[1] = 180;
	R_Set2DMode( false );
	R_SetupRefParams( &pass );
	R_SetupFrustum();
	R_SetupGL( true );
	// HUD is already composited: render to its screen target, at full resolution.
	GL_BindScreenTarget();
	pglViewport( view->x, gpGlobals->height - view->y - view->height, view->width, view->height );
	pglEnable( GL_SCISSOR_TEST );
	pglScissor( view->x, gpGlobals->height - view->y - view->height, view->width, view->height );
	pglEnable( GL_DEPTH_TEST );
	pglDepthMask( GL_TRUE );
	pglDepthFunc( GL_LEQUAL );
	pglDepthRange( 0, 1 );
	pglClear( GL_DEPTH_BUFFER_BIT );
	pglDisable( GL_FOG );
	// Legacy first-person assets often omit reverse faces. The workshop
	// inspects both sides, as the original viewmodel draw path does.
	GL_Cull( GL_NONE );
	RI.currententity = &ent; RI.currentmodel = ent.model;
	R_StudioSetHeader( hdr );
	R_StudioSetUpTransform( &ent );
	// Restore the parent's pose from the shared cache after the bounds pass.
	R_StudioMergeBones( &ent, ent.model );
	if( definition->draw_rig )
	{
		alight_t light; vec3_t dir;
		R_VFLighting( &ent, &light, dir );
		g_studio.framecount++;
		R_StudioRenderModel();
	}
	R_VFDrawParts( &ent, &assembly, false, NULL, NULL );
	RI = saved;
	tr.fFlipViewModel = saved_flip;
	GL_Cull( saved_cull );
	GL_CleanUpTextureUnits( 0 );
	pglDisable( GL_SCISSOR_TEST );
	R_Set2DMode( true );
	vf_stats.preview_draws++;
	vf_stats.last_preview_ms = (float)((gEngfuncs.pfnTime() - start) * 1000.0);
	return 1;
}

static void R_VFGetStats( vf_render_stats_t *out )
{
	if( !out || out->size != sizeof( *out )) return;
	vf_stats.assemblies = vf_stats.parts = 0;
	for( int i = 0; i < VF_MAX_ASSEMBLIES; i++ )
		if( vf_assemblies[i].entity ) { vf_stats.assemblies++; vf_stats.parts += vf_assemblies[i].definition.count; }
	R_VFTextureStats( &vf_stats.textures, &vf_stats.texture_bytes );
	*out = vf_stats; out->size = sizeof( *out );
}

static const vf_engine_api_t vf_api = { VF_ENGINE_API_VERSION, sizeof( vf_engine_api_t ), R_VFSetAssembly, R_VFClearAssembly, R_VFDrawPreview, R_VFGetStats, R_VFSequenceInfo };
EXPORT const vf_engine_api_t *VF_GetRenderAPI( int version )
{
	return version == VF_ENGINE_API_VERSION ? &vf_api : NULL;
}
