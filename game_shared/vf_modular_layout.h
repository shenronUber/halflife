/* Server-owned, seed-reproducible 3x3 exact cover. No engine dependencies. */
#ifndef VF_MODULAR_LAYOUT_H
#define VF_MODULAR_LAYOUT_H
#include <vector>
#include <cstring>
#include <cstdint>
namespace vfm {
enum { Cells=9, Edges=12, CellSize=1280, Gap=256, Pitch=CellSize+Gap,
       Extent=3*CellSize+2*Gap, Props=6 };
enum Link { Internal, Bridge, WallRun };
enum Role { JoinFloor, BridgeFloor, BridgePillar, RunWall, Cover };
struct Layout { int cell[Cells], modules, link[Edges], pillar[Edges], cover[Cells]; };
struct Random {
 uint32_t value;
 explicit Random(uint32_t seed):value(seed?seed:0x6d2b79f5u){}
 uint32_t Next(){value^=value<<13;value^=value>>17;value^=value<<5;return value;}
 int Pick(int count){return (int)(Next()%(uint32_t)count);}
};
inline void EdgeCells(int edge,int& a,int& b){
 if(edge<6){a=(edge/2)*3+edge%2;b=a+1;}
 else {a=edge-6;b=a+3;}
}
inline void Placements(std::vector<int>& masks){
 // All rotations of monomino, domino, straight triomino and L triomino.
 static const int shapes[9][7]={{1,0,0,0,0,0,0},{2,0,0,1,0,0,0},
 {2,0,0,0,1,0,0},{3,0,0,1,0,2,0},{3,0,0,0,1,0,2},
 {3,0,0,1,0,0,1},{3,0,0,1,0,1,1},{3,0,0,0,1,1,1},{3,1,0,0,1,1,1}};
 for(int s=0;s<9;++s)for(int y=0;y<3;++y)for(int x=0;x<3;++x){
  int mask=0;bool valid=true;
  for(int k=0;k<shapes[s][0];++k){int xx=x+shapes[s][1+2*k],yy=y+shapes[s][2+2*k];
   if(xx>=3||yy>=3){valid=false;break;}mask|=1<<(yy*3+xx);}
  if(valid)masks.push_back(mask);
 }
}
inline void Enumerate(int occupied,int count,Layout& current,const std::vector<int>& masks,std::vector<Layout>& results){
 if(occupied==511){current.modules=count;results.push_back(current);return;}
 int first=0;while(occupied&(1<<first))++first;
 for(size_t i=0;i<masks.size();++i){int mask=masks[i];
  if(!(mask&(1<<first))||(mask&occupied))continue;
  for(int c=0;c<Cells;++c)if(mask&(1<<c))current.cell[c]=count;
  Enumerate(occupied|mask,count+1,current,masks,results);
 }
}
inline std::vector<Layout> Tilings(){
 std::vector<int> masks;Placements(masks);std::vector<Layout> result;Layout current={};
 Enumerate(0,0,current,masks,result);return result;
}
inline Layout Generate(uint32_t seed,int minimumModules=3){
 static const std::vector<Layout> all=Tilings();std::vector<int> eligible;
 if(minimumModules<3||minimumModules>6)minimumModules=3;
 for(size_t i=0;i<all.size();++i)if(all[i].modules>=minimumModules&&all[i].modules<=6)eligible.push_back((int)i);
 Random random(seed);Layout result=all[eligible[random.Pick((int)eligible.size())]];
 std::vector<int> external;
 for(int e=0;e<Edges;++e){int a,b;EdgeCells(e,a,b);
  result.link[e]=result.cell[a]==result.cell[b]?Internal:(random.Pick(2)?Bridge:WallRun);
  result.pillar[e]=0;if(result.link[e]!=Internal)external.push_back(e);
 }
 // Each first prototype demonstrates both transitions and both bridge supports.
 // Three or more modules guarantee at least two external grid boundaries.
 int first=random.Pick((int)external.size());result.link[external[first]]=WallRun;
 int second=(first+1+random.Pick((int)external.size()-1))%(int)external.size();
 result.link[external[second]]=Bridge;
 std::vector<int> bridges;
 for(int e=0;e<Edges;++e)if(result.link[e]==Bridge){result.pillar[e]=random.Pick(2);bridges.push_back(e);}
 if(bridges.size()>1){result.pillar[bridges[0]]=0;result.pillar[bridges[1]]=1;}
 for(int c=0;c<Cells;++c){result.cover[c]=0;
  // Exactly two to four of six reserved cover locations; approach lanes stay clear.
  int desired=2+random.Pick(3);
  while(desired){int bit=1<<random.Pick(Props);if(!(result.cover[c]&bit)){result.cover[c]|=bit;--desired;}}
 }
 return result;
}
inline bool Active(const Layout& layout,int role,int index,int variant){
 if(role==Cover)return index>=0&&index<Cells&&variant>=0&&variant<Props&&(layout.cover[index]&(1<<variant));
 if(index<0||index>=Edges)return false;
 if(role==JoinFloor)return layout.link[index]==Internal;
 if(role==BridgeFloor)return layout.link[index]==Bridge;
 if(role==BridgePillar)return layout.link[index]==Bridge&&layout.pillar[index];
 if(role==RunWall)return layout.link[index]==WallRun;
 return false;
}
}
#endif
