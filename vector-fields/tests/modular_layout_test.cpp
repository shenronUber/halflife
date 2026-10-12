#include "../../game_shared/vf_modular_layout.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <string>
#include <algorithm>

static void Valid(const vfm::Layout& layout){
 assert(layout.modules>=3&&layout.modules<=9);
 for(int m=0;m<layout.modules;++m){
  std::set<int> cells;for(int c=0;c<9;++c){assert(layout.cell[c]>=0&&layout.cell[c]<layout.modules);if(layout.cell[c]==m)cells.insert(c);}
  assert(!cells.empty()&&cells.size()<=3);
  std::set<int> reached;reached.insert(*cells.begin());
  for(int pass=0;pass<3;++pass)for(int e=0;e<12;++e){int a,b;vfm::EdgeCells(e,a,b);
   if(cells.count(a)&&cells.count(b)&&(reached.count(a)||reached.count(b))){reached.insert(a);reached.insert(b);}}
  assert(reached==cells); // Every 2/3-cell connected polyomino is domino, I or L.
 }
}
static std::string Signature(const vfm::Layout& l){
 std::string s;for(int c=0;c<9;++c)s+=(char)('A'+l.cell[c]);
 for(int e=0;e<12;++e){s+=(char)('0'+l.link[e]);s+=(char)('0'+l.pillar[e]);}
 for(int c=0;c<9;++c)s+=(char)l.cover[c];return s;
}
static void Dump(unsigned int seed){
 vfm::Layout l=vfm::Generate(seed);printf("{\"seed\":%u,\"modules\":%d,\"cells\":[",seed,l.modules);
 for(int c=0;c<9;++c)printf("%s%d",c?",":"",l.cell[c]);printf("],\"links\":[");
 for(int e=0;e<12;++e)printf("%s%d",e?",":"",l.link[e]);printf("],\"pillars\":[");
 for(int e=0;e<12;++e)printf("%s%d",e?",":"",l.pillar[e]);printf("],\"covers\":[");
 for(int c=0;c<9;++c)printf("%s%d",c?",":"",l.cover[c]);printf("]}\n");
}
int main(int argc,char** argv){
 if(argc==3&&std::string(argv[1])=="--dump"){Dump((unsigned int)strtoul(argv[2],0,10));return 0;}
 std::vector<vfm::Layout> all=vfm::Tilings();std::set<std::string> unique;bool shapes[4]={};
 for(size_t i=0;i<all.size();++i){Valid(all[i]);std::string grid;
  for(int c=0;c<9;++c)grid+=(char)('A'+all[i].cell[c]);assert(unique.insert(grid).second);
  for(int m=0;m<all[i].modules;++m){int n=0,minx=3,maxx=0,miny=3,maxy=0;
   for(int c=0;c<9;++c)if(all[i].cell[c]==m){++n;minx=std::min(minx,c%3);maxx=std::max(maxx,c%3);miny=std::min(miny,c/3);maxy=std::max(maxy,c/3);}
   shapes[n==1?0:n==2?1:(maxx-minx==2||maxy-miny==2)?2:3]=true;
  }
 }
 for(int s=0;s<4;++s)assert(shapes[s]);
 std::set<std::string> variants;
 for(unsigned int seed=1;seed<=10000;++seed){vfm::Layout l=vfm::Generate(seed);Valid(l);assert(l.modules<=6);
  assert(Signature(l)==Signature(vfm::Generate(seed)));variants.insert(Signature(l));
  int bridges=0,runs=0,supported=0,bare=0;
  for(int e=0;e<12;++e){int a,b;vfm::EdgeCells(e,a,b);
   assert((l.link[e]==vfm::Internal)==(l.cell[a]==l.cell[b]));
   if(l.link[e]==vfm::Bridge){++bridges;if(l.pillar[e])++supported;else ++bare;}
   else assert(l.pillar[e]==0);
   if(l.link[e]==vfm::WallRun)++runs;
   int count=0;for(int role=0;role<4;++role)count+=vfm::Active(l,role,e,0)?1:0;
   assert(count==(l.pillar[e]?2:1));
  }
  assert(bridges&&runs);if(bridges>1)assert(supported&&bare);
  for(int c=0;c<9;++c){int n=0;for(int p=0;p<6;++p)n+=(l.cover[c]>>p)&1;assert(n>=2&&n<=4);}
 }
 assert(variants.size()>9900);
 printf("PASS modular: %zu unique exact covers, 10000 seeds, connected I/L/domino/mono modules, joins/supports/approaches and deterministic layouts\n",all.size());
 return 0;
}
