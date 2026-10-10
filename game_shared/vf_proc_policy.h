#ifndef VF_PROC_POLICY_H
#define VF_PROC_POLICY_H
#include <float.h>
namespace vfp {
enum { Elements=8, Required=6 };
static const float Window=3.0f,Duration=6.0f;
struct Accumulator {float hits[Elements][Required];int count[Elements];};
inline void Reset(Accumulator& a){for(int e=0;e<Elements;++e){a.count[e]=0;for(int i=0;i<Required;++i)a.hits[e][i]=0;}}
inline void Expire(Accumulator& a,float now){for(int e=0;e<Elements;++e){int n=0;for(int i=0;i<a.count[e];++i)if(now>=a.hits[e][i]&&now-a.hits[e][i]<=Window)a.hits[e][n++]=a.hits[e][i];a.count[e]=n;}}
inline bool Hit(Accumulator& a,int e,float now){
 if(e<0||e>=Elements||!(now>=-FLT_MAX&&now<=FLT_MAX))return false;Expire(a,now);
 a.hits[e][a.count[e]++]=now;if(a.count[e]<Required)return false;a.count[e]=0;return true;
}
}
#endif
