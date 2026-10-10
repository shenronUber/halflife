// Regression tests for stable persistence and authoritative assembly invariants.
#include "../../game_shared/vf_loadout.h"
#include "../../game_shared/vf_model_contract.h"
#include "../../game_shared/vf_appearance.h"
#include "../../game_shared/vf_legacy_save.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include <algorithm>
static int checks;
static void Check(bool ok,const char* why){++checks;if(!ok){fprintf(stderr,"FAIL: %s\n",why);exit(1);}}
static std::string Read(const char* file){std::ifstream f(file,std::ios::binary);Check(f.good(),"input file exists");return std::string((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());}
int main(int argc,char** argv){
 Check(argc==4,"equipment, finish and appearance paths supplied");
 std::string text=Read(argv[1]),styleText=Read(argv[2]),skinText=Read(argv[3]);
 static vf::Catalog catalog;vf::AppearanceCatalog styles,skins;
 Check(vf::ParseCatalog(text.data(),text.size(),catalog),"equipment parses");
 Check(vf::ParseAppearances(styleText.data(),styleText.size(),styles),"finishes parse");
 Check(vf::ParseAppearances(skinText.data(),skinText.size(),skins),"appearances parse");
 int selection[vf::SlotCount],totals[vf::BudgetCount];vf::GameplayDefaults(catalog,selection);
 Check(vf::EvaluateGameplay(catalog,selection,totals)==vf::Accepted,"complete gameplay defaults accepted");
 for(int s=0;s<vf::SlotCount;++s){
  int saved=selection[s];selection[s]=0;bool optional=s==1||s==4||s==7||s==8;
  Check(vf::EvaluateGameplay(catalog,selection,totals)==(optional?vf::Accepted:vf::Incompatible),"only the four optional gameplay slots may be empty");selection[s]=saved;
 }
 vf::Defaults(catalog,selection);
 Check(vf::EvaluateExperiment(catalog,selection,totals)==vf::Accepted,"complete historical builds retained in experimental mode");
 Check(vf::EvaluateGameplay(catalog,selection,totals)==vf::Incompatible,"historical objects rejected by gameplay validator");
 memset(selection,0,sizeof(selection));Check(vf::EvaluateExperiment(catalog,selection,totals)==vf::Accepted,"empty experimental builds allowed");
 vf::GameplayDefaults(catalog,selection);selection[12]=vf::FindItem(catalog,"feed_standard");
 Check(vf::EvaluateExperiment(catalog,selection,totals)==vf::Incompatible,"R01 and historical feed cannot mix even in the workshop");
 Check(vf::EvaluateGameplay(catalog,selection,totals)==vf::Incompatible,"mixed feed rejected by gameplay validator");
 vf::GameplayDefaults(catalog,selection);selection[10]=0;
 Check(vf::EvaluateExperiment(catalog,selection,totals)==vf::Incompatible,"R01 requires its barrel in experimental mode too");
 vf::GameplayDefaults(catalog,selection);selection[9]=vf::FindItem(catalog,"receiver_standard");
 Check(selection[9]>0,"historical receiver found");
 Check(vf::EvaluateExperiment(catalog,selection,totals)==vf::Incompatible,"R01 components cannot attach to a historical chassis");
 vf::GameplayDefaults(catalog,selection);selection[0]=vf::FindItem(catalog,"gign_head_trench");selection[2]=vf::FindItem(catalog,"gign_gloves_noir");selection[9]=vf::FindItem(catalog,"r01_receiver_top__original");selection[1]=0;
 Check(vf::EvaluateGameplay(catalog,selection,totals)==vf::Accepted,"non-default mixed outfit, top platform and empty shoulders accepted");
 const char* keys[vf::SlotCount];for(int s=0;s<vf::SlotCount;++s)keys[s]=catalog.items[selection[s]].id;
 static vf::Catalog commented;std::string changed=text+"\n# editorial change\n";
 Check(vf::ParseCatalog(changed.data(),changed.size(),commented)&&commented.fingerprint!=catalog.fingerprint,"comment changes handshake hash");
 int restored[vf::SlotCount];vf::RestoreEquipment(commented,keys,restored);
 Check(!memcmp(selection,restored,sizeof(selection)),"comment change preserves every equipped item");
 std::vector<std::string> rows;std::string limits;size_t start=0;
 while(start<text.size()){size_t end=text.find('\n',start);if(end==std::string::npos)end=text.size();std::string row=text.substr(start,end-start);if(!row.empty()&&row.back()=='\r')row.pop_back();if(row.find("limits|")==0)limits=row;else if(!row.empty()&&row[0]!='#')rows.push_back(row);start=end+1;}
 std::reverse(rows.begin(),rows.end());changed=limits+"\n";for(size_t i=0;i<rows.size();++i)changed+=rows[i]+"\n";
 static vf::Catalog reordered;Check(vf::ParseCatalog(changed.data(),changed.size(),reordered),"reordered catalog parses");
 vf::RestoreEquipment(reordered,keys,restored);
 for(int s=0;s<vf::SlotCount;++s)Check(!strcmp(reordered.items[restored[s]].id,keys[s]),"stable key survives reordered wire indices");
 Check(vf::EvaluateGameplay(reordered,restored,totals)==vf::Accepted,"migrated build remains valid");
 const char* legacy[vf::SlotCount];
 for(int s=0;s<vf::SlotCount;++s){
  int oldIndex=-1;for(size_t i=0;i<sizeof(vf::LegacyItemKeys)/sizeof(*vf::LegacyItemKeys);++i)if(!strcmp(vf::LegacyItemKeys[i],vf::ItemModel(catalog.items[selection[s]])))oldIndex=(int)i;
  Check(oldIndex>=0,"migration fixture exists in frozen 0.14.0 dictionary");legacy[s]=vf::LegacyItemKey(vf::LegacyItemHash,oldIndex);
 }
 vf::RestoreEquipment(reordered,legacy,restored);
 for(int s=0;s<vf::SlotCount;++s)Check(!strcmp(reordered.items[restored[s]].id,vf::ItemModel(catalog.items[selection[s]])),"legacy numeric save migrates to stable keys");
 Check(!vf::LegacyItemKey(0,1)&&!vf::LegacyItemKey(vf::LegacyItemHash,999),"unknown legacy dictionaries and invalid indices fail safely");
 changed=limits+"\n";for(size_t i=0;i<rows.size();++i)if(rows[i].find("|gign_gloves_noir|")==std::string::npos)changed+=rows[i]+"\n";
 static vf::Catalog removed;Check(vf::ParseCatalog(changed.data(),changed.size(),removed),"removed-item catalog parses");vf::RestoreEquipment(removed,keys,restored);
 for(int s=0;s<vf::SlotCount;++s)if(s!=2)Check(!strcmp(removed.items[restored[s]].id,keys[s]),"removing gloves preserves every other selection including optional empty slots");
 Check(restored[2]>0&&removed.items[restored[2]].slot==2,"removed item replaced only in its own slot");
 keys[2]=keys[0];vf::RestoreEquipment(catalog,keys,restored);Check(restored[2]>0&&catalog.items[restored[2]].slot==2,"a stale key cannot cross equip slots");
 const char* finishKeys[vf::WeaponStyleSlots];int finishes[vf::WeaponStyleSlots];
 for(int s=0;s<vf::WeaponStyleSlots;++s)finishKeys[s]=styles.entries[s%styles.count].key;
 vf::AppearanceCatalog remapped=styles;std::swap(remapped.entries[2],remapped.entries[7]);for(int i=0;i<remapped.count;++i)remapped.entries[i].skin=i;
 vf::RestoreAppearances(remapped,finishKeys,finishes,vf::WeaponStyleSlots);
 Check(vf::ValidWeaponStyles(remapped,finishes),"reordered finish selections remain valid");
 for(int s=0;s<vf::WeaponStyleSlots;++s)Check(!strcmp(remapped.entries[finishes[s]].key,finishKeys[s]),"each independent finish survives reordering");
 for(int s=0;s<vf::WeaponStyleSlots;++s)finishKeys[s]=vf::LegacyStyleKey(vf::LegacyStyleHash,s%styles.count);
 vf::RestoreAppearances(remapped,finishKeys,finishes,vf::WeaponStyleSlots);
 for(int s=0;s<vf::WeaponStyleSlots;++s)Check(!strcmp(remapped.entries[finishes[s]].key,finishKeys[s]),"legacy finish indices migrate");
 const char* appearanceKeys[5];int appearances[5];for(int z=0;z<5;++z)appearanceKeys[z]=skins.entries[skins.count-1-z].key;
 remapped=skins;std::swap(remapped.entries[skins.count-1],remapped.entries[0]);vf::RestoreAppearances(remapped,appearanceKeys,appearances,5);
 for(int z=0;z<5;++z)Check(!strcmp(remapped.entries[appearances[z]].key,appearanceKeys[z]),"independent free appearances survive reordering");
 appearanceKeys[2]="removed_appearance";vf::RestoreAppearances(skins,appearanceKeys,appearances,5);
 for(int z=0;z<5;++z)Check(z==2?appearances[z]==0:!strcmp(skins.entries[appearances[z]].key,appearanceKeys[z]),"only a deleted appearance falls back");
 vf::GameplayDefaults(catalog,selection);Check(vf::EquipmentSkins(catalog,selection,skins,appearances),"gameplay body resolves");
 Check(!strcmp(vf::OperatorRig(skins,appearances),"models/vf_skins/persona_rig.mdl"),"shared server/client rig selector uses fitted GIGN skeleton");
 appearances[0]=0;Check(!strcmp(vf::OperatorRig(skins,appearances),"models/vf_operator.mdl"),"mixed legacy bodies keep their original common skeleton");
 // Gameplay inventory binds geometry and finish atomically, including large wire IDs.
 vf::GameplayDefaults(catalog,selection);memset(finishes,0,sizeof(finishes));
 int variant=vf::FindItem(catalog,"r01_receiver_arch_top__dieselpunk");
 Check(variant>255,"real inventory IDs exceed byte range");selection[9]=variant;
 Check(vf::ReceiverMount(catalog.items[variant])==2&&vf::ReceiverMount(catalog.items[vf::FindItem(catalog,"r01_receiver_arch_top")])==2,"base and named chassis share the top feed mount");
 Check(vf::EvaluateGameplay(catalog,selection,totals)==vf::Accepted,"new top receiver is a gameplay item");
 Check(!vf::BoundWeaponStyles(catalog,styles,selection,finishes),"forged finish for a named item is rejected");
 vf::BindWeaponStyles(catalog,styles,selection,finishes);
 Check(vf::BoundWeaponStyles(catalog,styles,selection,finishes)&&finishes[0]==13,"fixed finish resolves correctly");
 Check(vf::BuildMessageSize==2+8+2*vf::SlotCount+vf::WeaponStyleSlots&&vf::StateMessageSize==4+12+5+2*vf::SlotCount+vf::WeaponStyleSlots,"shared protocol lengths include short inventory IDs");
 for(int i=1;i<catalog.count;++i)if(catalog.items[i].model[0]){
  int slot=catalog.items[i].slot,saved=selection[slot];selection[slot]=i;
  vf::BindWeaponStyles(catalog,styles,selection,finishes);
  Check(vf::BoundWeaponStyles(catalog,styles,selection,finishes),"every inventory finish exists and binds");
  Check(vf::EvaluateGameplay(catalog,selection,totals)==vf::Accepted,"every inventory object fits its intended slot");selection[slot]=saved;
 }
 vf::GameplayDefaults(catalog,selection);
 for(int s=9;s<vf::SlotCount;++s){selection[s]=vf::FindItem(catalog,vf::ItemModel(catalog.items[selection[s]]));finishes[s-9]=(s-9)%styles.count;}
 selection[9]=vf::FindItem(catalog,"r01_receiver_arch_top");finishes[0]=13;
 Check(vf::EvaluateGameplay(catalog,selection,totals)==vf::Incompatible,"base geometry is reserved for developer tools");
 vf::PromoteGameplayEquipment(catalog,styles,selection,finishes);
 Check(selection[9]==variant,"old chassis and separate finish migrate to the exact named item");
 for(int s=9;s<vf::SlotCount;++s)Check(catalog.items[selection[s]].model[0]&&!strcmp(catalog.items[selection[s]].weaponStyle,styles.entries[finishes[s-9]].key),"migration preserves each independent finish");
 int savedItems[vf::SlotCount];memcpy(savedItems,selection,sizeof(selection));
 vf::PromoteGameplayEquipment(catalog,styles,selection,finishes);Check(!memcmp(savedItems,selection,sizeof(selection)),"inventory migration is idempotent");
 static vf::Catalog invalid;std::string unsafe=text;size_t at=unsafe.find("||r01_receiver_a|original");
 Check(at!=std::string::npos,"variant fixture exists");unsafe.replace(at,strlen("||r01_receiver_a|original"),"||../receiver_a|original");
 Check(!vf::ParseCatalog(unsafe.data(),unsafe.size(),invalid),"unsafe model paths rejected");
 unsafe=text;at=unsafe.find("||r01_receiver_a|original");unsafe.replace(at,strlen("||r01_receiver_a|original"),"||r01_barrel_a|original");
 Check(!vf::ParseCatalog(unsafe.data(),unsafe.size(),invalid),"variant cannot bind to another socket");
 Check(!vf::FindModelTraits(NULL)&&!vf::FindModelTraits("unknown_model"),"unknown models do not acquire a grip pose");
 Check(!strcmp(vf::Carrier(-1).firstPerson,vf::Carrier(0).firstPerson)&&!strcmp(vf::Carrier(99).thirdPerson,vf::Carrier(0).thirdPerson),"invalid carrier mount falls back safely");
 for(int i=1;i<catalog.count;++i){
  const vf::Item& item=catalog.items[i];const char* model=vf::ItemModel(item);
  if(!strncmp(model,"r01_receiver_",13)||!strncmp(model,"r01_underbarrel_",15)){
   const vf::ModelTraits* traits=vf::FindModelTraits(model);Check(traits!=NULL,"every receiver and underbarrel has explicit model traits");
   if(traits){Check(vf::ReceiverMount(item)==traits->feedMount,"all finishes inherit their geometry feed mount");
    Check(traits->supportGrip==(!strcmp(model,"r01_underbarrel_a")),"only angled foregrip and its finishes use the support pose");}
  }
 }
 printf("PASS architecture: %d validation, stable-key migration and rig-selection checks\n",checks);
 return 0;
}
