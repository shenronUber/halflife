#include <cassert>
#include <cstdio>
#include <initializer_list>
#include <limits>
#include "../../cl_dll/vf_effect_math.h"
int main(){
 int checks=0;for(int a=0;a<8;++a){int count=0;for(int b=0;b<8;++b){assert(vfx::Reaction(a,b)==vfx::Reaction(b,a));++checks;if(vfx::Reaction(a,b)>=0)++count;}assert(count==2);++checks;assert(vfx::Reaction(a,a)==-1);++checks;}
 for(int e=0;e<vfx::Count;++e)for(int l=0;l<vfx::effects[e].layerCount;++l)for(float time: {0.f,.37f,4.7f,4095.9f,86400.f}){
  vfx::Primitive p[513]={};p[512].alpha=1234;int n=vfx::Generate(vfx::effects[e].layers[l],time,p,512);assert(n>0&&n<=512&&p[512].alpha==1234);++checks;
  for(int i=0;i<n;++i){const auto& q=p[i];assert(std::isfinite(q.a.x)&&std::isfinite(q.a.y)&&std::isfinite(q.a.z)&&std::isfinite(q.b.x)&&std::isfinite(q.b.y)&&std::isfinite(q.b.z));assert(fabs(q.a.x)<100&&fabs(q.a.y)<100&&fabs(q.a.z)<100&&fabs(q.b.x)<100&&fabs(q.b.y)<100&&fabs(q.b.z)<100);assert(q.alpha>=0&&q.alpha<=1&&q.size>0);++checks;}
  vfx::Primitive tiny[2]={};tiny[1].alpha=1234;assert(vfx::Generate(vfx::effects[e].layers[l],time,tiny,1)==1&&tiny[1].alpha==1234);++checks;
 }
 vfx::Primitive p[2];assert(vfx::Generate(vfx::effects[0].layers[0],std::numeric_limits<float>::quiet_NaN(),p,2)==0);++checks;
 printf("PASS effects: %d graph, trajectory, finite-value and capacity checks\n",checks);return 0;
}
