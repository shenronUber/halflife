#include <cassert>
#include <cstdio>
#include <limits>
#include "../../cl_dll/vf_status_feedback.h"
int main(){
 unsigned long long quads=0;const float sizes[][2]={{640,480},{1280,720},{1920,1080},{3440,1440},{720,1280}};
 for(auto& size:sizes)for(int id=0;id<vfx::Count;++id)for(int edge=0;edge<4;++edge)for(int frame=0;frame<180;++frame){
  vffeedback::Quad q[513];q[512].texture=997;
  int n=vffeedback::Generate(id,edge,frame/30.f,size[0],size[1],.8f,q,512);assert(n>0&&n<=512);assert(q[512].texture==997);quads+=n;
  for(int i=0;i<n;++i){assert(q[i].texture>=0&&q[i].texture<5);assert(q[i].a>0&&q[i].a<=.8f);
   for(auto& p:q[i].p){assert(std::isfinite(p.x)&&std::isfinite(p.y));assert(p.x>=0&&p.x<=size[0]&&p.y>=0&&p.y<=size[1]);assert(!vffeedback::Protected(p,size[0],size[1]));}
  }
 }
 for(int edge=0;edge<4;++edge){auto r=vffeedback::DecalEdge(edge);
  assert(r.left>=0&&r.top>=0&&r.right<=1&&r.bottom<=1&&r.left<r.right&&r.top<r.bottom);
  for(float x=r.left;x<=r.right;x+=.001f)for(float y=r.top;y<=r.bottom;y+=.001f)
   assert(!vffeedback::Protected({x*1920,y*1080},1920,1080));
 }
 for(int id=0;id<vfdecal::Count;++id){auto a=vffeedback::DecalFrame(id,0);assert(a.current==0&&a.next==1&&a.mix==0);
  float step=1.f/vfdecal::assets[id].fps;
  auto near=vffeedback::DecalFrame(id,step-.00001f),after=vffeedback::DecalFrame(id,step+.00001f);
  assert(near.current==0&&near.next==1&&near.mix>.999f);assert(after.current==1&&after.next==2&&after.mix<.001f);
  auto loop=vffeedback::DecalFrame(id,step*4+.00001f);assert(loop.current==0&&loop.next==1&&loop.mix<.001f);
  for(int frame=0;frame<1000;++frame){auto f=vffeedback::DecalFrame(id,frame*.113f);
   assert(f.current>=0&&f.current<4&&f.next==(f.current+1)%4&&f.mix>=0&&f.mix<=1);}
 }
 vffeedback::Quad q[3];assert(vffeedback::Generate(1,0,1,1280,720,1,q,3)==3);
 assert(!vffeedback::Generate(-1,0,1,1280,720,1,q,3));assert(!vffeedback::Generate(0,0,std::numeric_limits<float>::quiet_NaN(),1280,720,1,q,3));
 assert(vffeedback::Fade(0,0,6)==0&&vffeedback::Fade(1,0,6)==1&&vffeedback::Fade(6,0,6)==0);
 assert(vffeedback::Fade(5.9f,0,6)>0&&vffeedback::Fade(5.9f,0,6)<1);
 printf("PASS status edge geometry: 21 effects, 5 aspect ratios, 180 frames, %llu quads; protected center and bounded capacity\n",quads);
}
