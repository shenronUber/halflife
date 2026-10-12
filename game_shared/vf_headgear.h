// Shared, deterministic headgear timing. Independent of authored animation banks.
#ifndef VF_HEADGEAR_H
#define VF_HEADGEAR_H
#include <math.h>
#ifdef __cplusplus
namespace vf {
#endif
enum { HeadgearTypes=5, HeadgearMessageSize=4 };
static const float HeadgearDuration=1.15f;
static inline float HeadgearClamp(float v) { return v<0?0:v>1?1:v; }
static inline float HeadgearSmooth(float v) { v=HeadgearClamp(v);return v*v*(3-2*v); }
static inline float HeadgearPose(float phase,int raised) {
 float move=HeadgearSmooth((phase-.30f)/.42f);return raised?move:1-move;
}
static inline float HeadgearReach(float phase) {
 return phase<.30f?HeadgearSmooth(phase/.30f):1-HeadgearSmooth((phase-.72f)/.28f);
}
static inline int HeadgearBody(int type) { const int bodies[]={0,1,8,4,5,10};return type>0&&type<=HeadgearTypes?bodies[type]:0; }
// Pivot/translation in the fitted persona source coordinates; X is transverse.
static inline void HeadgearTransform(int type,float pose,float pivot[3],float* angle,float shift[3]) {
 pivot[0]=.23387f;pivot[1]=-1.9f;pivot[2]=66.8f;*angle=-112;
 shift[0]=shift[1]=shift[2]=0;
 if(type==2){pivot[1]=-1.8f;pivot[2]=66.85f;*angle=-110;}
 if(type==3||type==4){pivot[1]=-3.8f;pivot[2]=67.85f;*angle=-80;}
 if(type==5){pivot[1]=-6.7f;pivot[2]=64;*angle=-45;shift[1]=6.4f*pose;shift[2]=7.6f*pose;}
 *angle*=pose;
}
#ifdef __cplusplus
}
#endif
#endif
