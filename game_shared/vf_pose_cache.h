/* Exact-input server pose cache. No network ABI or animation quantization. */
#ifndef VF_POSE_CACHE_H
#define VF_POSE_CACHE_H
#include <float.h>
typedef struct vf_pose_key_s {
 const void *model,*header,*entity,*game;
 double time;
 int sequence,gait,hull,traversal;
 unsigned char blend[2];
 float values[24];
} vf_pose_key_t;
static inline int VF_PoseKeyEqual(const vf_pose_key_t *a,const vf_pose_key_t *b){
 if(a->model!=b->model||a->header!=b->header||a->entity!=b->entity||a->game!=b->game||
    a->time!=b->time||!(a->time>=-DBL_MAX&&a->time<=DBL_MAX)||
    a->sequence!=b->sequence||a->gait!=b->gait||a->hull!=b->hull||a->traversal!=b->traversal||
    a->blend[0]!=b->blend[0]||a->blend[1]!=b->blend[1])return 0;
 for(int i=0;i<24;++i)if(a->values[i]!=b->values[i]||!(a->values[i]>=-FLT_MAX&&a->values[i]<=FLT_MAX))return 0;
 return 1;
}
#endif
