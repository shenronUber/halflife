/* Fixed model/bone topology is independent of the per-frame pose. */
#ifndef VF_ASSEMBLY_POLICY_H
#define VF_ASSEMBLY_POLICY_H
#include "vf_engine_api.h"
#include <string.h>
#include <math.h>
static inline int VF_AssemblyPath(const char *path) {
 return memchr(path,0,64) && !strncmp(path,"models/",7) && !strstr(path,"..") && !strchr(path,':');
}
static inline int VF_AssemblyValid(const vf_assembly_t *a) {
 if(!a || a->count<0 || a->count>VF_MAX_PARTS || a->body<0 || a->skin<0 ||
    a->replace_carried<0 || a->replace_carried>1 || !VF_AssemblyPath(a->rig))return 0;
 if(a->headgear_type<0 || a->headgear_type>5 || !(a->headgear_phase>=0 && a->headgear_phase<=1))return 0;
 for(int i=0;i<a->count;++i){const vf_part_t *p=&a->parts[i];
  if(!VF_AssemblyPath(p->model) || p->body<0 || p->skin<0 || p->mode<VF_PART_MERGE ||
     p->mode>VF_PART_SOCKET || !memchr(p->bone,0,sizeof(p->bone)) || !(p->scale>=0 && p->scale<=4))return 0;
  for(int j=0;j<3;++j)if(!(fabs(p->offset[j])<=4096) || !(fabs(p->angles[j])<=3600))return 0;
 }
 return 1;
}
/* Called only after validation. Body groups, textures and transforms reuse maps. */
static inline int VF_AssemblySameTopology(const vf_assembly_t *a,const vf_assembly_t *b) {
 if(a->count!=b->count || strcmp(a->rig,b->rig))return 0;
 for(int i=0;i<a->count;++i)if(a->parts[i].mode!=b->parts[i].mode ||
  strcmp(a->parts[i].model,b->parts[i].model) || strcmp(a->parts[i].bone,b->parts[i].bone))return 0;
 return 1;
}
#endif
