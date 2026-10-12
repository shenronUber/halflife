#include "../../game_shared/vf_headgear.h"
#include "../../game_shared/vf_loadout.h"
#include "../../game_shared/vf_appearance.h"
#include <stdio.h>
#include <string.h>
#include <string>
#include <fstream>
#include <iterator>
static int failures;
static void Check(bool ok,const char* text){if(!ok){printf("FAIL %s\n",text);++failures;}}
int main(int argc,char** argv){
 Check(vf::HelmetSlot==21&&vf::GearSlots==9&&vf::WeaponEnd==21,"append slot without shifting historical weapon/style identities");
 Check(vf::OperatorSlot(9)==vf::HelmetSlot&&!vf::WeaponSlot(vf::HelmetSlot)&&vf::OptionalSlot(vf::HelmetSlot),"operator UI and validator agree on optional helmet");
 Check(vf::BuildMessageSize==2+8+2*vf::SlotCount+vf::WeaponStyleSlots&&vf::StateMessageSize==4+12+5+2*vf::SlotCount+vf::WeaponStyleSlots,"network message lengths include appended slot");
 if(argc<3)return 1;
 std::ifstream file(argv[1],std::ios::binary),styleFile(argv[2],std::ios::binary);
 std::string text((std::istreambuf_iterator<char>(file)),{}),styles((std::istreambuf_iterator<char>(styleFile)),{});
 static vf::Catalog c;static vf::AppearanceCatalog finishes;
 Check(vf::ParseCatalog(text.data(),text.size(),c)&&vf::ParseAppearances(styles.data(),styles.size(),finishes),"current runtime catalogs parse");
 int base[vf::SlotCount],chosen[vf::SlotCount],style[vf::WeaponStyleSlots]={},totals[6];vf::GameplayDefaults(c,base);
 Check(base[vf::HelmetSlot]==0,"existing outfits do not acquire unsolicited headgear");
 const char* ids[]={"helmet_riot","helmet_ballistic","helmet_nvg_red","helmet_nvg_green","helmet_gas_mask"};
 for(int t=0;t<5;++t){
  memcpy(chosen,base,sizeof(base));int id=vf::FindItem(c,ids[t]);Check(id>0,"all five actual authored items exist");if(id<=0)continue;
  chosen[vf::HelmetSlot]=id;vf::BindWeaponStyles(c,finishes,chosen,style);
  Check(vf::EvaluateGameplay(c,chosen,totals)==vf::Accepted&&vf::BoundWeaponStyles(c,finishes,chosen,style),"each helmet equips with complete R01 gameplay loadout");
  vf::PromoteGameplayEquipment(c,finishes,chosen,style);Check(chosen[vf::HelmetSlot]==id,"weapon migration cannot overwrite helmet or access a thirteenth finish");
  const char* keys[vf::SlotCount];for(int s=0;s<vf::SlotCount;++s)keys[s]=c.items[chosen[s]].id;
  int restored[vf::SlotCount];vf::RestoreEquipment(c,keys,restored);Check(!memcmp(chosen,restored,sizeof(chosen)),"stable item keys preserve equipment across saves/catalog handshakes");
  chosen[0]=id;Check(vf::Evaluate(c,chosen,totals)==vf::WrongSlot,"helmet cannot overwrite the skin mask");
  float previous=0;
  for(int frame=0;frame<=100;++frame){float p=frame*.01f,a=vf::HeadgearPose(p,1),b=vf::HeadgearPose(p,0);
   Check(a>=previous&&fabsf(a+b-1)<1e-5f,"raise/lower continuous inverse motion");previous=a;
   Check(vf::HeadgearReach(p)>=0&&vf::HeadgearReach(p)<=1,"gesture weight bounded");
  }
 }
 Check(vf::HeadgearReach(0)==0&&vf::HeadgearReach(1)==0&&vf::HeadgearReach(.5f)==1,"hand returns to its existing weapon pose without endpoint jumps");
 Check(vf::HeadgearPose(.29f,1)==0&&vf::HeadgearPose(.73f,1)==1,"hand reaches before equipment moves and returns afterwards");
 printf("%s headgear policy: five optional items, stable slots/saves, complete R01 builds and reversible gesture\n",failures?"FAIL":"PASS");return failures?1:0;
}
