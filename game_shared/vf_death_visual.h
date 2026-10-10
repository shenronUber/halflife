// Independent anatomical loss and elemental presentation; no damage thresholds.
#ifndef VF_DEATH_VISUAL_H
#define VF_DEATH_VISUAL_H
namespace vfdeath {
enum {Head=1,LeftArm=2,RightArm=4,LeftLeg=8,RightLeg=16,All=31};
static const char* Model="models/vf_deaths/persona_death.mdl";
static const char* GibModel="models/vf_deaths/persona_death_gibs.mdl";
static const int Region[]={Head,0,LeftArm,RightArm,LeftArm,RightArm,LeftLeg,RightLeg,LeftLeg,RightLeg,0,Head,LeftArm,RightArm,LeftLeg,RightLeg};
static const int Zone[]={0,1,1,1,2,2,3,3,4,4,3,1,1,1,3,3};
enum { ClothingGroups=11, BodyGroups=16 };
inline int Body(int missing,int zone=-1){int result=0;for(int i=0;i<BodyGroups;++i)if((zone<0||Zone[i]==zone)&&(i<ClothingGroups?!(missing&Region[i]):(missing&Region[i])!=0))result|=1<<i;return result;}
// One physical fragment, two texture references; uniform legacy indices stay stable.
enum { FinishCount=14, FragmentSkinCount=FinishCount*FinishCount };
inline int FragmentPairSkin(int primary,int detail){
 if(primary<0||primary>=FinishCount||detail<0||detail>=FinishCount)return 0;
 return primary==detail?primary:FinishCount+primary*(FinishCount-1)+detail-(detail>primary?1:0);
}
inline bool FragmentPairFinishes(int skin,int& primary,int& detail){
 if(skin<0||skin>=FragmentSkinCount){primary=detail=0;return false;}
 if(skin<FinishCount){primary=detail=skin;return true;}
 int mixed=skin-FinishCount;primary=mixed/(FinishCount-1);detail=mixed%(FinishCount-1);if(detail>=primary)++detail;return true;
}
inline int FragmentSkin(int region,const int* skins){
 const int clothing[]={0,1,1,3,3},detail[]={0,2,2,4,4};
 return region>=0&&region<5?FragmentPairSkin(skins[clothing[region]],skins[detail[region]]):0;
}
inline bool Electric(int effect){return effect==1||effect==8||effect==9;}
}
#endif
