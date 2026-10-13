#include "../../game_shared/vf_tile_rooms.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <set>
int main(int argc,char** argv){
 if(argc==3&&!strcmp(argv[1],"--dump")){
  int seed=atoi(argv[2]);vfm::Layout l=vfm::Generate(seed,4);
  printf("{\"seed\":%d,\"cells\":[",seed);for(int c=0;c<9;++c)printf("%s%d",c?",":"",l.cell[c]);
  printf("],\"rooms\":[");for(int c=0;c<9;++c)printf("%s%d",c?",":"",vft::Choice(l,seed,c));
  printf("],\"links\":[");for(int e=0;e<12;++e)printf("%s%d",e?",":"",l.link[e]);
  printf("],\"forms\":[");for(int m=0;m<l.modules;++m)printf("%s\"%s\"",m?",":"",vft::Form(l,m));puts("]}");return 0;
 }
 std::set<int> variants;std::set<const char*> forms;
 for(int seed=1;seed<=10000;++seed){
  vfm::Layout l=vfm::Generate(seed,4);assert(l.modules>=4&&l.modules<=6);std::set<int> families;
  for(int c=0;c<9;++c){int choice=vft::Choice(l,seed,c);variants.insert(choice);families.insert(choice/2);
   int selected=0;for(int v=0;v<8;++v)selected+=vft::Active(l,seed,-1,vft::Room,c,v);assert(selected==1);
   for(int other=0;other<9;++other)if(l.cell[c]==l.cell[other])assert(choice==vft::Choice(l,seed,other));
   for(int forced=0;forced<8;++forced)assert(vft::Choice(l,seed,c,forced)==forced);
  }
  assert(families.size()==4);
  for(int m=0;m<l.modules;++m)forms.insert(vft::Form(l,m));
  for(int e=0;e<12;++e){int a,b;vfm::EdgeCells(e,a,b);
   assert(vft::Active(l,seed,-1,vft::Joint,e,0)==(l.link[e]==vfm::Internal&&vft::Enclosed(vft::Choice(l,seed,a))));
  }
 }
 assert(variants.size()==8&&forms.size()==4);
 puts("PASS tile rooms: 10000 seeded layouts, eight variants, all four forms, coherent module interiors, forced comparisons and sealed internal joints");
}
