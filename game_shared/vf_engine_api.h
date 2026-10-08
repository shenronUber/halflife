/* Optional, versioned Vector Fields renderer extension. No GoldSrc ABI changes. */
#ifndef VF_ENGINE_API_H
#define VF_ENGINE_API_H
#define VF_ENGINE_API_VERSION 2
#define VF_MAX_PARTS 16
#define VF_MAX_ASSEMBLIES 96
#define VF_PART_MERGE 0
#define VF_PART_SOCKET 1
typedef struct vf_part_s {
 char model[64];
 int body,skin,mode;
 char bone[32];
 float offset[3],angles[3];
} vf_part_t;
typedef struct vf_assembly_s {
 char rig[64];
 int draw_rig,body,skin,count;
 vf_part_t parts[VF_MAX_PARTS];
} vf_assembly_t;
typedef struct vf_preview_s {
 int size,x,y,width,height,sequence;
 float seconds,yaw,zoom;
 float center[3],radius;
} vf_preview_t;
typedef struct vf_render_stats_s {
 int size,assemblies,parts,cached_models,model_loads,cache_hits;
 unsigned int pose_evaluations,merged_parts,socket_parts,preview_draws,rejected;
 unsigned int textures,texture_bytes;
 unsigned int weapon_draws;
 float last_preview_ms;
} vf_render_stats_t;
typedef struct vf_engine_api_s {
 int version,size;
 int (*SetAssembly)(int entity,const vf_assembly_t* assembly);
 void (*ClearAssembly)(int entity); /* 0 clears all, -1 identifies viewmodel */
 int (*DrawPreview)(const vf_preview_t* view,const vf_assembly_t* assembly);
 void (*GetStats)(vf_render_stats_t* stats);
 int (*SequenceInfo)(const char* model,int sequence,char* name,int capacity,float* duration);
} vf_engine_api_t;
typedef const vf_engine_api_t* (*vf_get_engine_api_fn)(int version);
typedef int (*vf_client_engine_init_fn)(int version,const vf_engine_api_t* api);
#endif
