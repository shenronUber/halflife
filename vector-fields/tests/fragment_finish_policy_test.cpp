#include "../../game_shared/vf_death_visual.h"
#include <cassert>
#include <cstdio>
int main(){
 bool used[vfdeath::FragmentSkinCount]={};
 for(int a=0;a<14;++a)for(int b=0;b<14;++b){
  int skin=vfdeath::FragmentPairSkin(a,b),p,d;assert(skin>=0&&skin<196&&!used[skin]);used[skin]=true;
  assert(vfdeath::FragmentPairFinishes(skin,p,d)&&p==a&&d==b);if(a==b)assert(skin==a);
 }
 const int skins[]={5,2,0,1,13};
 const int primary[]={5,2,2,1,1},detail[]={5,0,0,13,13};
 for(int region=0;region<5;++region){int p,d;assert(vfdeath::FragmentPairFinishes(vfdeath::FragmentSkin(region,skins),p,d));assert(p==primary[region]&&d==detail[region]);}
 int p,d;assert(!vfdeath::FragmentPairFinishes(-1,p,d)&&!vfdeath::FragmentPairFinishes(196,p,d));
 puts("PASS fragment finishes: 196 reversible pairs, stable uniform indices, head/arms/legs use their own clothing zones");
}
