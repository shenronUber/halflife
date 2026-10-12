#include "../../game_shared/vf_assembly_policy.h"
#include "../../game_shared/vf_active_entities.h"
#include "../../game_shared/vf_headgear_feedback.h"
#include <stdio.h>
#include <limits>
static int checks,failures;
static void Check(bool value,const char* label){++checks;if(!value){++failures;printf("FAIL %s\n",label);}}
int main(){
 vf_assembly_t a={};strcpy(a.rig,"models/rig.mdl");a.count=1;
 strcpy(a.parts[0].model,"models/glove.mdl");strcpy(a.parts[0].bone,"hand");a.parts[0].mode=VF_PART_MERGE;
 Check(VF_AssemblyValid(&a),"valid assembly");vf_assembly_t b=a;
 b.headgear_type=3;b.headgear_phase=.65f;b.parts[0].angles[1]=42;b.parts[0].skin=7;b.parts[0].body=3;
 Check(VF_AssemblyValid(&b)&&VF_AssemblySameTopology(&a,&b),"moving pose and finish reuse bone maps");
 b.parts[0].scale=2;Check(VF_AssemblySameTopology(&a,&b),"scale is pose data");
 b.parts[0].offset[0]=std::numeric_limits<float>::quiet_NaN();Check(!VF_AssemblyValid(&b),"NaN pose rejected on cache hit");
 b=a;b.headgear_phase=std::numeric_limits<float>::infinity();Check(!VF_AssemblyValid(&b),"infinite clock rejected");
 b=a;strcpy(b.rig,"models/other.mdl");Check(!VF_AssemblySameTopology(&a,&b),"carrier change resolves maps");
 b=a;strcpy(b.parts[0].bone,"missing");Check(!VF_AssemblySameTopology(&a,&b),"socket change resolves maps");
 b=a;b.parts[0].mode=VF_PART_SOCKET;Check(!VF_AssemblySameTopology(&a,&b),"merge/socket change resolves maps");
 b=a;strcpy(b.parts[0].model,"models/new.mdl");Check(!VF_AssemblySameTopology(&a,&b),"mesh change resolves maps");
 b=a;b.count=0;Check(!VF_AssemblySameTopology(&a,&b),"removing part resolves maps");
 b=a;memset(b.parts[0].model,'x',64);Check(!VF_AssemblyValid(&b),"unterminated path rejected");
 b=a;strcpy(b.parts[0].model,"models/../private");Check(!VF_AssemblyValid(&b),"escaped path rejected");
 b=a;b.count=VF_MAX_PARTS+1;Check(!VF_AssemblyValid(&b),"capacity rejected before array access");
 vf::ActiveEntities<2048> live;
 Check(!live.Add(0)&&!live.Add(-1)&&!live.Add(2048),"invalid entity IDs rejected");
 for(int id=1;id<2048;++id)Check(live.Add(id),"all legal IDs fit without allocation");
 Check(live.count==2047,"full capacity");live.Add(15);Check(live.count==2047,"repeated network refresh is idempotent");
 for(int id=1;id<2048;id+=2){live.Remove(id);live.Remove(id);}
 Check(live.count==1023,"repeated removal is idempotent");
 for(int i=0;i<live.count;++i)Check(live.ids[i]%2==0&&live.positions[live.ids[i]]==i,"swap removal preserves dense membership");
 for(int id=1;id<2048;id+=2)Check(live.Add(id),"expired/reused entity can be added again");
 live.Reset();Check(live.count==0&&live.positions[15]==-1,"map reset clears membership");
 Check(vf::HeadgearFeedbackDue(-1,0)==0,"clock rewind dispatches nothing");
 Check(vf::HeadgearFeedbackDue(0,0)==2,"intent announcement before the face is covered");
 Check(vf::HeadgearFeedbackDue(.1f,2)==0,"latch waits; announcement cannot replay");
 Check(vf::HeadgearFeedbackDue(.4f,2)==1,"latch follows the intent announcement");
 Check(vf::HeadgearFeedbackDue(2.f,0)==3,"late tick catches both cues");
 Check(vf::HeadgearFeedbackDue(2.f,1)==2,"previous latch cannot replay");
 Check(vf::HeadgearFeedbackDue(2.f,3)==0,"completed feedback is idempotent");
 printf("backend policy: %d checks, %d failures\n",checks,failures);return failures?1:0;
}
