/* Vector Fields optional renderer extension. Included here to share the Studio pose cache. */
#include "vf_engine_api.h"

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

static vf_resolved_t vf_assemblies[VF_MAX_ASSEMBLIES];
static vf_cached_model_t vf_models[2048];
static vf_render_stats_t vf_stats;
static qboolean vf_drawing;
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
	if( !in || in->count < 0 || in->count > VF_MAX_PARTS || in->body < 0 || in->skin < 0 || in->replace_carried < 0 || in->replace_carried > 1 )
		return false;
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
				if( parent == rig->numbones ) return false;
				out->bone_map[i][b] = parent;
			}
		}
	}
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
 if( player && player->model && (!Q_stricmp( player->model->name, "models/vf_skins/persona_rig.mdl" ) ||
  !Q_stricmp( player->model->name, "models/vf_r01/r01_tp.mdl" ) ||
  !Q_stricmp( player->model->name, "models/vf_r01/r01_tp_side.mdl" ) ||
  !Q_stricmp( player->model->name, "models/vf_r01/r01_tp_top.mdl" ))) return player->model;
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
static void R_VFDrawParts( cl_entity_t *parent, const vf_resolved_t *assembly, qboolean bounds, vec3_t mins, vec3_t maxs )
{
	alight_t light;
	vec3_t dir;
	matrix3x4 root;
	Matrix3x4_Copy( root, g_studio.rotationmatrix );
	for( int i = 0; i < assembly->definition.count; i++ )
	{
		cl_entity_t piece = *parent;
		Matrix3x4_Copy( g_studio.rotationmatrix, root );
		R_VFPreparePart( &piece, &assembly->definition.parts[i], assembly->parts[i], assembly->bone_map[i] );
		if( bounds ) { R_VFBounds( mins, maxs ); continue; }
		cl_entity_t *viewent = tr.viewent;
        // Status shells belong to the fitted hands/sleeves, never the R1 sockets.
        // Preserve the original mesh and pose; Studio adds its shell pass.
        if( parent == viewent && piece.curstate.renderfx == kRenderFxGlowShell &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_r01/r01_fp_gloves.mdl" ) &&
            Q_strcmp( assembly->definition.parts[i].model, "models/vf_r01/r01_fp_sleeves.mdl" ))
            piece.curstate.renderfx = kRenderFxNone;
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

// Fitted crouch poses bend the spine forward. Rotating each local spine X
// axis then rolls the torso while strafing. Distribute the same yaw around
// world-up instead, preserving the native feet/gait and every hand socket.
static void R_VFPlayerTorsoYaw( cl_entity_t *ent )
{
 if( !ent->player || !ent->curstate.gaitsequence ) return;
 player_info_t *info = pfnPlayerInfo( ent->index - 1 );
 if( !info ) return;
 float yaw = ent->angles[YAW] - info->gaityaw;
 while( yaw > 180.0f ) yaw -= 360.0f;
 while( yaw < -180.0f ) yaw += 360.0f;
 // StudioProcessGait already chose forward/backward gait at +/-120 degrees.
 for( int i = 0; i < 4; ++i )
  ent->curstate.controller[i] = ent->latched.prevcontroller[i] = 127;
 m_pPlayerInfo = info;
 R_StudioSetupBones( ent );
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

static qboolean R_VFDrawRegistered( cl_entity_t *ent, int flags )
{
	if( vf_drawing ) return false;
	vf_resolved_t *assembly = R_VFFind( ent == tr.viewent ? -1 : ent->index );
	if( !assembly ) return false;
	cl_entity_t saved = *ent;
	model_t *oldmodel = RI.currentmodel;
	vf_drawing = true;
	ent->model = assembly->rig;
	ent->curstate.body = assembly->definition.body;
	ent->curstate.skin = assembly->definition.skin;
	if( assembly->definition.replace_carried ) ent->curstate.weaponmodel = 0;
	RI.currentmodel = ent->model;
	int base_flags = assembly->definition.draw_rig ? flags : flags & ~STUDIO_RENDER;
	int drawn = ent->player ? R_StudioDrawPlayer( base_flags, &ent->curstate ) : R_StudioDrawModel( base_flags );
	vf_stats.pose_evaluations++;
 if( drawn && assembly->definition.replace_carried ) R_VFPlayerTorsoYaw( ent );
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
