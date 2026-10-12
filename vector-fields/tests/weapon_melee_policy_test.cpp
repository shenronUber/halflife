#include "../../game_shared/vf_weapon_melee.h"
#include <assert.h>
#include <stdio.h>
int main(){
 assert(vf::MeleeReady(true,4,false,false,0));
 assert(!vf::MeleeReady(false,4,false,false,0));
 for(int w=0;w<=15;++w)if(w!=4)assert(!vf::MeleeReady(true,w,false,false,0));
 assert(!vf::MeleeReady(true,4,true,false,0));
 assert(!vf::MeleeReady(true,4,false,true,0));
 for(int phase=1;phase<16;++phase)assert(!vf::MeleeReady(true,4,false,false,phase));
 for(int fps=20;fps<=240;fps+=10){
  bool impacted=false;int hits=0;
  for(int frame=0;frame<fps*2;++frame){float age=(float)frame/fps;
   if(vf::MeleeImpactDue(age,impacted)){assert(age>=vf::MeleeImpact&&age<vf::MeleeImpact+1.f/fps+.0001f);impacted=true;++hits;}}
  assert(hits==1);
 }
 assert(!vf::MeleeImpactDue(-1,false));assert(!vf::MeleeImpactDue(vf::MeleeImpact-.001f,false));
 assert(vf::MeleeImpactDue(vf::MeleeImpact,false));assert(!vf::MeleeImpactDue(vf::MeleeImpact,true));
 assert(!vf::MeleeImpactDue(vf::MeleeDuration,false));
 assert(vf::MeleeClockValid(-.04f)&&vf::MeleeClockValid(0));
 assert(!vf::MeleeClockValid(-.06f)&&!vf::MeleeClockValid(vf::MeleeDuration));
 puts("PASS melee policy: R1/alive/busy/reload/traversal gates, one impact at 20-240 fps and no late impact");
}
