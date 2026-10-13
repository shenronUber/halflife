#ifndef VF_TILE_ROOMS_H
#define VF_TILE_ROOMS_H
#include "vf_modular_layout.h"
namespace vft {
enum { Variants=8, Room=5, Shell=6, Joint=7 };
inline int Choice(const vfm::Layout& layout,int seed,int cell,int forced=-1){
 if(cell<0||cell>=9)return -1;
 if(forced>=0&&forced<Variants)return forced;
 int module=layout.cell[cell];
 vfm::Random random((uint32_t)seed^0xa17e531bu);int offset=random.Pick(4);
 vfm::Random detail((uint32_t)seed^((uint32_t)(module+1)*0x9e3779b9u));
 return ((module+offset)%4)*2+detail.Pick(2);
}
inline bool Enclosed(int choice){return choice/2==0||choice/2==3;}
inline bool Active(const vfm::Layout& layout,int seed,int forced,int role,int index,int variant){
 if(role==Room)return index>=0&&index<9&&variant==Choice(layout,seed,index,forced);
 if(role==Shell)return index>=0&&index<9&&Enclosed(Choice(layout,seed,index,forced));
 if(role==Joint){
  if(index<0||index>=12||layout.link[index]!=vfm::Internal)return false;
  int a,b;vfm::EdgeCells(index,a,b);return Enclosed(Choice(layout,seed,a,forced));
 }
 return vfm::Active(layout,role,index,variant);
}
inline const char* Form(const vfm::Layout& layout,int module){
 int count=0,minx=3,maxx=0,miny=3,maxy=0;
 for(int c=0;c<9;++c)if(layout.cell[c]==module){++count;
  if(c%3<minx)minx=c%3;if(c%3>maxx)maxx=c%3;if(c/3<miny)miny=c/3;if(c/3>maxy)maxy=c/3;}
 return count==1?"mono":count==2?"domino":maxx-minx==2||maxy-miny==2?"I":"L";
}
}
#endif
