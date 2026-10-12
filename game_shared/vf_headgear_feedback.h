// Shared transition weights: presentation/audio follow the same moving equipment.
#ifndef VF_HEADGEAR_FEEDBACK_H
#define VF_HEADGEAR_FEEDBACK_H
#include "vf_headgear.h"
namespace vf {
inline float HeadgearCover(int type,int raised,float age,bool moving){
 if(type<1||type>HeadgearTypes)return 0;
 return moving?1-HeadgearPose(HeadgearClamp(age/HeadgearDuration),raised):raised?0.f:1.f;
}
inline bool HeadgearMuffled(int type,float cover){return (type==1||type==2||type==5)&&cover>.65f;}
inline int HeadgearFeedbackDue(float age,int steps){
 int due=0;
 if(!(steps&1)&&age>=HeadgearDuration*.30f)due|=1;
 if(!(steps&2)&&age>=0)due|=2;
 return due;
}
}
#endif
