#include "../../game_shared/vf_death_visual.h"
#include "../../game_shared/vf_player_pose.h"
#include <cassert>
#include <cmath>
#include <cstdio>
int main(){
 bool used[vfdeath::FragmentSkinCount]={};
 for(int a=0;a<vfdeath::FinishCount;++a)for(int b=0;b<vfdeath::FinishCount;++b){
  int skin=vfdeath::FragmentPairSkin(a,b),p,d;assert(skin>=0&&skin<vfdeath::FragmentSkinCount&&!used[skin]);used[skin]=true;
  assert(vfdeath::FragmentPairFinishes(skin,p,d)&&p==a&&d==b);if(a==b)assert(skin==a);
 }
 const int skins[]={5,2,0,1,13};
 const int primary[]={5,2,2,1,1},detail[]={5,0,0,13,13};
 for(int region=0;region<5;++region){int p,d;assert(vfdeath::FragmentPairFinishes(vfdeath::FragmentSkin(region,skins),p,d));assert(p==primary[region]&&d==detail[region]);}
 int p,d;assert(!vfdeath::FragmentPairFinishes(-1,p,d)&&!vfdeath::FragmentPairFinishes(vfdeath::FragmentSkinCount,p,d));
 float damage[5]={},weights[5]={};
 for(int region=0;region<5;++region){
  const int groups[]={1,4,5,6,7};for(int i=0;i<5;++i)damage[i]=0;
  damage[region]=50;assert(vfdeath::AutomaticMask(groups[region],damage,100)==0);
  damage[region]=50.001f;assert(vfdeath::AutomaticMask(groups[region],damage,100)==(1<<region));
  assert(vfdeath::AutomaticMask(2,damage,100)==0&&vfdeath::AutomaticMask(0,damage,100)==0);
  assert(vfdeath::AutomaticMask(groups[(region+1)%5],damage,100)==0);
  assert(vfdeath::AutomaticMask(groups[region],damage,0)==0);
 }
 for(int i=0;i<5;++i)damage[i]=weights[i]=0;
 weights[1]=20;weights[2]=30;vfdeath::AccumulateDamage(damage,weights,100,20);
 assert(damage[1]==4&&damage[2]==6); // central damage and armor cannot inflate limb totals
 vfdeath::AccumulateDamage(damage,weights,100,0);assert(damage[1]==4);
 for(int i=0;i<5;++i)damage[i]=0;weights[0]=1;
 for(int i=0;i<5;++i)vfdeath::AccumulateDamage(damage,weights,1,10);
 assert(vfdeath::AutomaticMask(1,damage,100)==0);
 vfdeath::AccumulateDamage(damage,weights,1,1);assert(vfdeath::AutomaticMask(1,damage,100)==vfdeath::Head);
 for(int a=0;a<256;++a)for(int b=0;b<256;++b){
  const float packed=VF_PosePackBlend((unsigned char)a,(unsigned char)b);
  assert(VF_PoseBlend(packed,0)==a&&VF_PoseBlend(packed,1)==b);
 }
 for(int type=0;type<=5;++type)for(int raised=0;raised<=1;++raised)for(int tick=0;tick<=65535;tick+=257){
  const float phase=tick/65535.f,packed=VF_PosePackGear(phase,type,raised);
  assert(VF_PoseGearType(packed)==type&&VF_PoseGearRaised(packed)==raised);
  assert(fabsf(VF_PoseGearPhase(packed)-phase)<=1.f/65535);
 }
 printf("PASS fragment finishes: %d reversible pairs, stable uniform indices, head/arms/legs use their own clothing zones\n",vfdeath::FragmentSkinCount);
}
