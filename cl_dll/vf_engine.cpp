#include "hud.h"
#include "cl_util.h"
#include "cl_entity.h"
#include "com_model.h"
#include "r_studioint.h"
extern engine_studio_api_t IEngineStudio;
#include "parsemsg.h"
#include "Exports.h"
#include "vf_engine.h"
#include "vf_death.h"
#include "../game_shared/vf_death_visual.h"
#include "vf_range.h"
#include "vf_third_person_scale.h"
#include "vf_library.h"
#include "vf_preview.h"
#include "../game_shared/vf_engine_api.h"
#include "../game_shared/vf_appearance.h"
#include "../game_shared/vf_loadout.h"
#include "../game_shared/vf_model_contract.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <algorithm>
#include <chrono>

namespace {
const vf_engine_api_t* engine=NULL;
vf::AppearanceCatalog skins,arsenal;
vf::AppearanceCatalog modules,weaponStyles;
cvar_t *thirdPersonEnabled=NULL;
cvar_t *visualEnabled=NULL,*visualParts[4]={};
int draftParts[4]={};
int benchWarmup=0,benchCount=-1;double benchTimes[180],benchFrames[180];
std::chrono::steady_clock::time_point benchLast;
char benchLabel[32]="";unsigned int benchLoads=0;
vf::Catalog equipment;
struct Player {bool active;int skins[5],items[vf::SlotCount],styles[vf::WeaponStyleSlots],body,mode;bool thirdPerson;int reloadStage;};
Player players[33];
bool requested=false,paused=false;
int sequence=0,sequences=0;
bool referenceHands=false;
void ReferenceHands(){referenceHands=gEngfuncs.Cmd_Argc()>1?atoi(gEngfuncs.Cmd_Argv(1))!=0:!referenceHands;}
float animationStart=0,pauseTime=0;
char lastRig[64]="",animationLabel[112]="";
const char* rig="models/vf_operator.mdl";
void LoadCatalogs() {
 int n=0;byte* bytes=gEngfuncs.COM_LoadFile((char*)"vf/skins.txt",5,&n);
 vf::ParseAppearances((char*)bytes,n>0?n:0,skins);if(bytes)gEngfuncs.COM_FreeFile(bytes);
 bytes=gEngfuncs.COM_LoadFile((char*)"vf/arsenal.txt",5,&n);
 vf::ParseAppearances((char*)bytes,n>0?n:0,arsenal);if(bytes)gEngfuncs.COM_FreeFile(bytes);
 bytes=gEngfuncs.COM_LoadFile((char*)"vf/equipment.txt",5,&n);
 vf::ParseCatalog((char*)bytes,n>0?n:0,equipment);if(bytes)gEngfuncs.COM_FreeFile(bytes);
 bytes=gEngfuncs.COM_LoadFile((char*)"vf/weapon_modules.txt",5,&n);
 vf::ParseAppearances((char*)bytes,n>0?n:0,modules);if(bytes)gEngfuncs.COM_FreeFile(bytes);
 bytes=gEngfuncs.COM_LoadFile((char*)"vf/r01_styles.txt",5,&n);
 vf::ParseAppearances((char*)bytes,n>0?n:0,weaponStyles);if(bytes)gEngfuncs.COM_FreeFile(bytes);
}
int PartCount(int zone){int n=0;for(int i=0;i<modules.count;++i)if(modules.entries[i].animations==zone)++n;return n;}
const vf::Appearance* Part(int zone,int variant){for(int i=0;i<modules.count;++i)if(modules.entries[i].animations==zone&&variant--==0)return &modules.entries[i];return NULL;}
bool VisualAssembly(vf_assembly_t& a,bool hands,bool draft,const int* choices=NULL){
 if(!modules.valid)return false;
 memset(&a,0,sizeof(a));strcpy(a.rig,"models/vf_modules/mp40_rig.mdl");a.draw_rig=1;a.body=hands?3:2;
 for(int z=0;z<4;++z){
  float value=choices?(float)choices[z]:(draft?(float)draftParts[z]:visualParts[z]->value);
  if(!_finite(value)||value<0||value>=PartCount(z)||value!=(int)value)return false;
  const vf::Appearance* item=Part(z,(int)value);if(!item)return false;
  vf_part_t& p=a.parts[a.count++];snprintf(p.model,sizeof(p.model),"models/vf_modules/%s.mdl",item->key);p.mode=VF_PART_SOCKET;strcpy(p.bone,"Bone76");
 }
 vf_part_t& p=a.parts[a.count++];strcpy(p.model,"models/vf_modules/adapters.mdl");p.mode=VF_PART_SOCKET;strcpy(p.bone,"Bone76");if(!choices)VF_LibraryAccessories(a);return true;
}
void ModuleCommand(){unsigned int z,id;if(gEngfuncs.Cmd_Argc()==3&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),z)&&z<4&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(2),id)&&id<(unsigned int)PartCount(z))draftParts[z]=id;}
void ModuleAudit(){
 if(!engine||!modules.valid)return;int saved[4];memcpy(saved,draftParts,sizeof(saved));int passed=0,failed=0;
 for(int a=0;a<PartCount(0);++a)for(int b=0;b<PartCount(1);++b)for(int c=0;c<PartCount(2);++c)for(int d=0;d<PartCount(3);++d){draftParts[0]=a;draftParts[1]=b;draftParts[2]=c;draftParts[3]=d;vf_assembly_t def;if(VisualAssembly(def,false,true)&&engine->SetAssembly(2046,&def))++passed;else ++failed;}
 engine->ClearAssembly(2046);memcpy(draftParts,saved,sizeof(saved));gEngfuncs.Con_Printf("VFVisual audit: combinations=%d failed=%d\n",passed,failed);
}
void BenchCommand(){
 if(!engine)return;snprintf(benchLabel,sizeof(benchLabel),"%.30s",gEngfuncs.Cmd_Argc()>1?gEngfuncs.Cmd_Argv(1):"preview");
 benchWarmup=30;benchCount=0;vf_render_stats_t s={};s.size=sizeof(s);engine->GetStats(&s);benchLoads=s.model_loads;
 gEngfuncs.Con_DPrintf("VFBench start: %s\n",benchLabel);
}
// Legacy family_* variants dye clothing only. Authored skin families also style the head.
void SkinAssembly(vf_assembly_t& a,const char* keys[5],int isolate) {
 if(!skins.valid)LoadCatalogs();
 int ids[5];for(int z=0;z<5;++z)ids[z]=vf::FindAppearance(skins,keys[z]);
 memset(&a,0,sizeof(a));strcpy(a.rig,vf::OperatorRig(skins,ids));
 for(int z=0;z<5;++z)if(isolate<0||z==isolate){vf_part_t& p=a.parts[a.count++];const char* model=keys[z];for(int i=0;i<skins.count;++i)if(!strcmp(keys[z],skins.entries[i].key)){model=skins.entries[i].model;p.skin=(z==0&&!strncmp(model,"family_",7))?0:skins.entries[i].skin;break;}snprintf(p.model,sizeof(p.model),"models/vf_skins/%s.mdl",model);p.body=1<<z;}
}

void EquipmentAccessories(vf_assembly_t& a,const int* items,bool weapon){
 const int opSlots[]={1,4,7,8};const char* bones[]={"Bip01 Spine3","Bip01 Pelvis","Bip01 L Arm2","Bip01 Spine3"};
 const int gunSlots[]={11,12,13,14,15,16,19,20};
 for(int n=0;n<(weapon?8:4);++n){int slot=weapon?gunSlots[n]:opSlots[n];int f=vf::EquipmentFamily(equipment,items,slot);if(f<0)continue;
  vf_part_t& p=a.parts[a.count++];snprintf(p.model,sizeof(p.model),"models/vf_equipment/eq_%s.mdl",vf::SlotKeys[slot]);p.body=f;p.mode=VF_PART_SOCKET;strcpy(p.bone,weapon?(slot==12?"Bone71":"Bone76"):bones[n]);
 }
}

bool ReferenceWeapon(vf_assembly_t& a,const int* items,bool hands,int isolate=-1,const int* styles=NULL){
 if(!items||items[9]<=0||items[9]>=equipment.count||strncmp(equipment.items[items[9]].id,"r01_receiver_",13))return false;
 int platform=vf::ReceiverMount(equipment.items[items[9]]);
 // Styled finishes share geometry; only the angled foregrip needs this pose.
 int underbarrel=items[17];bool foregrip=hands&&underbarrel>0&&underbarrel<equipment.count&&
  vf::FindModelTraits(vf::ItemModel(equipment.items[underbarrel]))&&
  vf::FindModelTraits(vf::ItemModel(equipment.items[underbarrel]))->supportGrip;
 memset(&a,0,sizeof(a));strcpy(a.rig,vf::Carrier(platform).firstPerson);a.draw_rig=0;a.body=1;
 if(foregrip)strcpy(a.rig,vf::Carrier(platform).foregrip);
 for(int slot=9;slot<vf::SlotCount;++slot){
  if(isolate>=0&&slot!=isolate)continue;
  int id=items[slot];if(id<=0||id>=equipment.count||equipment.items[id].slot!=slot)return false;
  const char* key=vf::ItemModel(equipment.items[id]);if(strncmp(key,"r01_",4))return false;
  vf_part_t& p=a.parts[a.count++];
  snprintf(p.model,sizeof(p.model),"models/vf_r01/%s.mdl",key);
  int style=equipment.items[id].weaponStyle[0]?vf::FindAppearance(weaponStyles,equipment.items[id].weaponStyle):styles?styles[slot-9]:0;
  if(style<0||style>=weaponStyles.count)return false;
  p.skin=weaponStyles.entries[style].skin;
  p.mode=VF_PART_SOCKET;strcpy(p.bone,slot==12?vf::FirstPersonFeedSocket:slot==13?vf::FirstPersonChamberSocket:vf::FirstPersonWeaponSocket);
  if(platform==2&&slot==16)p.offset[0]=3.4f;
 }
 if(hands){
  const int zones[]={2,3};const char* models[]={"gloves","sleeves"};
  for(int z=0;z<2;++z){
   vf_part_t& p=a.parts[a.count++];snprintf(p.model,sizeof(p.model),"models/vf_r01/r01_fp_%s.mdl",models[z]);
   p.mode=VF_PART_MERGE;p.skin=vf::FirstPersonSkin(equipment,items,skins,zones[z]);
  }
 }
 return a.count>0;
}
void ReferenceAudit(){
 if(!engine)return;LoadCatalogs();int ids[12][vf::MaxItems]={},counts[12]={},items[vf::SlotCount];vf::GameplayDefaults(equipment,items);
 for(int i=1;i<equipment.count;++i){const vf::Item& p=equipment.items[i];if(p.slot>=9&&!strcmp(p.weaponStyle,"original"))ids[p.slot-9][counts[p.slot-9]++]=i;}
 unsigned long long combinations=1;for(int s=0;s<12;++s){if(!counts[s]){gEngfuncs.Con_Printf("VFR01 audit: missing slot=%d\n",s+9);return;}combinations*=counts[s];}
 // Every shape and pair of sockets is exercised. Enumerating millions of
 // complete builds would block the game without adding new socket contracts.
 int checked=0,failed=0;
 for(int left=0;left<12;++left)for(int right=left;right<12;++right)
  for(int a=0;a<counts[left];++a)for(int b=0;b<(left==right?1:counts[right]);++b){
   for(int s=0;s<12;++s)items[s+9]=ids[s][0];items[left+9]=ids[left][a];if(left!=right)items[right+9]=ids[right][b];
   vf_assembly_t assembly;int costs[vf::BudgetCount];++checked;
   if(vf::EvaluateGameplay(equipment,items,costs)!=vf::Accepted||!ReferenceWeapon(assembly,items,true)||assembly.count!=14||!engine->SetAssembly(2044,&assembly))++failed;
  }
 engine->ClearAssembly(2044);gEngfuncs.Con_Printf("VFR01 audit: checked=%d failed=%d parts=12 combinations=%llu coverage=single-and-pairs\n",checked,failed,combinations);
}

bool EquipmentWeapon(vf_assembly_t& a,const int* items,bool hands,const int* styles=NULL){
 int totals[vf::BudgetCount];vf::Result valid=vf::EvaluateExperiment(equipment,items,totals);
 if(valid!=vf::Accepted&&valid!=vf::OverBudget)return false;
 if(ReferenceWeapon(a,items,hands,-1,styles))return true;
 int choices[4];for(int z=0;z<4;++z)choices[z]=vf::EquipmentModule(equipment,items,z);
 if(!VisualAssembly(a,hands,false,choices))return false;EquipmentAccessories(a,items,true);if(vf::EquipmentFamily(equipment,items,12)>=0)a.body&=~2;return true;
}
bool ThirdPersonWeapon(vf_assembly_t& body,const Player& player,const cl_entity_t* entity){
 // MP5 sequence indices 0..76 are preserved in all three authored carriers.
 // Only fitted GIGN bodies use this bind skeleton. Other donor bodies retain
 // their existing carried model and animation contract.
 if(!thirdPersonEnabled||thirdPersonEnabled->value<.5f||strcmp(body.rig,"models/vf_skins/persona_rig.mdl"))return false;
 if(entity->player){
  model_t* carried=IEngineStudio.GetModelByIndex(entity->curstate.weaponmodel);
  if(!carried||stricmp(carried->name,"models/p_9mmAR.mdl"))return false;
 }
 vf_assembly_t weapon;if(!ReferenceWeapon(weapon,player.items,false,-1,player.styles)||body.count+weapon.count>VF_MAX_PARTS)return false;
 int mount=vf::ReceiverMount(equipment.items[player.items[9]]);
 const char* path=vf::Carrier(mount).thirdPerson;
 // Missing optional assets leave the previous working body/weapon intact.
 if(engine->SequenceInfo(path,0,NULL,0,NULL)<=0)return false;
 strcpy(body.rig,path);body.replace_carried=1;
 for(int i=0;i<weapon.count;++i){
  vf_part_t& part=body.parts[body.count++];part=weapon.parts[i];
  strcpy(part.bone,!strcmp(part.bone,vf::FirstPersonFeedSocket)?vf::ThirdPersonFeedSocket:!strcmp(part.bone,vf::FirstPersonChamberSocket)?vf::ThirdPersonChamberSocket:vf::ThirdPersonWeaponSocket);
  part.scale=VF_THIRD_PERSON_SCALE;for(int axis=0;axis<3;++axis)part.offset[axis]*=part.scale;
 }
 return true;
}
void WeaponAssembly(vf_assembly_t& a,int body) {
 memset(&a,0,sizeof(a));strcpy(a.rig,"models/v_9mmar.mdl");a.draw_rig=1;a.body=body&1;
 if(body&2){vf_part_t& p=a.parts[a.count++];strcpy(p.model,"models/vf_modules/suppressor.mdl");p.mode=VF_PART_SOCKET;strcpy(p.bone,"M16A2");}
}

void EquipmentAudit(){
 if(!engine)return;LoadCatalogs();int items[vf::SlotCount],passed=0,failed=0;
 for(int i=1;i<equipment.count;++i){if(!strncmp(equipment.items[i].id,"r01_",4))vf::GameplayDefaults(equipment,items);else vf::Defaults(equipment,items);items[equipment.items[i].slot]=i;vf_assembly_t a;bool ok;
  if(equipment.items[i].slot>=vf::GearSlots)ok=EquipmentWeapon(a,items,false);
  else{int ids[5];ok=vf::EquipmentSkins(equipment,items,skins,ids);if(ok){const char* keys[5];for(int z=0;z<5;++z)keys[z]=skins.entries[ids[z]].key;SkinAssembly(a,keys,-1);EquipmentAccessories(a,items,false);}}
  if(ok&&engine->SetAssembly(2045,&a))++passed;else ++failed;
 }engine->ClearAssembly(2045);gEngfuncs.Con_DPrintf("VFEquipment audit: objects=%d passed=%d failed=%d max_parts=%d\n",equipment.count-1,passed,failed,VF_MAX_PARTS);
}
int State(const char*,int size,void* data) {
 if(size!=vf::StateMessageSize)return 1;BEGIN_READ(data,size);
 int version=READ_BYTE(),index=READ_BYTE(),active=READ_BYTE(),mode=READ_BYTE();
 unsigned int skinHash=(unsigned int)READ_LONG(),equipHash=(unsigned int)READ_LONG(),styleHash=(unsigned int)READ_LONG();
 Player p={};p.mode=mode;for(int z=0;z<5;++z)p.skins[z]=READ_BYTE();for(int s=0;s<vf::SlotCount;++s)p.items[s]=READ_SHORT();for(int s=0;s<vf::WeaponStyleSlots;++s)p.styles[s]=READ_BYTE();
 if(version!=vf::Protocol||index<1||index>32||active>1||mode>1)return 1;
 if(!active){players[index]=Player();if(engine)engine->ClearAssembly(index);return 1;}
 if(!skins.valid||!equipment.valid||!weaponStyles.valid)LoadCatalogs();
 int totals[vf::BudgetCount];
 if(styleHash!=weaponStyles.hash||!vf::BoundWeaponStyles(equipment,weaponStyles,p.items,p.styles)||skinHash!=skins.hash||equipHash!=equipment.fingerprint||!vf::ValidSkins(skins,p.skins)||vf::Evaluate(equipment,p.items,totals)!=vf::Accepted){
  players[index]=Player();if(engine)engine->ClearAssembly(index);gEngfuncs.Con_DPrintf("VFState rejected catalog/loadout for player=%d\n",index);return 1;
 }
 gEngfuncs.Con_DPrintf("VFAppearance state: player=%d mode=%d\n",index,mode);
 gEngfuncs.Con_DPrintf("VFR01 state: player=%d first=%d optic=%d feed=%d\n",index,p.styles[0],p.styles[7],p.styles[3]);
 p.active=true;p.body=vf::WeaponBody(equipment,p.items);players[index]=p;
 gEngfuncs.Con_DPrintf("VFState player=%d skins=%d,%d,%d,%d,%d weapon=%d\n",index,p.skins[0],p.skins[1],p.skins[2],p.skins[3],p.skins[4],p.body);
 return 1;
}
void Stats() {
 if(!engine){gEngfuncs.Con_DPrintf("VFEngine: extension unavailable\n");return;}
 vf_render_stats_t s={};s.size=sizeof(s);engine->GetStats(&s);
 gEngfuncs.Con_DPrintf("VFEngine: assemblies=%d parts=%d models=%d loads=%d cache_hits=%d poses=%u merged=%u sockets=%u previews=%u rejected=%u textures=%u texture_bytes=%u preview_ms=%.3f\n",s.assemblies,s.parts,s.cached_models,s.model_loads,s.cache_hits,s.pose_evaluations,s.merged_parts,s.socket_parts,s.preview_draws,s.rejected,s.textures,s.texture_bytes,s.last_preview_ms);
 for(int i=1;i<=32;++i)if(players[i].active)gEngfuncs.Con_DPrintf("VFPeer %d: %d,%d,%d,%d,%d weapon=%d\n",i,players[i].skins[0],players[i].skins[1],players[i].skins[2],players[i].skins[3],players[i].skins[4],players[i].body);
 for(int i=1;i<=32;++i)if(players[i].active){
  cl_entity_t* peer=gEngfuncs.GetEntityByIndex(i);
  if(peer)gEngfuncs.Con_DPrintf("VFPeerPose player=%d sequence=%d frame=%.1f gait=%d model=%s\n",i,peer->curstate.sequence,peer->curstate.frame,peer->curstate.gaitsequence,peer->model?peer->model->name:"none");
 }
 cl_entity_t* local=gEngfuncs.GetLocalPlayer();int id=local?local->index:0;
 vf_assembly_t a;
 if(id>0&&id<=32&&players[id].active&&ReferenceWeapon(a,players[id].items,true,-1,players[id].styles))
  gEngfuncs.Con_DPrintf("VFFirstPerson: player=%d gloves=%d sleeves=%d parts=%d rig=%s\n",id,a.parts[a.count-2].skin,a.parts[a.count-1].skin,a.count,a.rig);
 gEngfuncs.Con_DPrintf("VFEngine remote weapons drawn=%u\n",s.weapon_draws);
}
void AnimationCommand(){
 unsigned int id;
 if(gEngfuncs.Cmd_Argc()==2&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),id)&&id<(unsigned int)sequences){sequence=id;animationStart=gEngfuncs.GetClientTime();pauseTime=0;}
 else VF_EngineAnimation(1);
}
void PauseCommand(){VF_EnginePause();}
void FrameCommand(){
 if(gEngfuncs.Cmd_Argc()!=2)return;float seconds=(float)atof(gEngfuncs.Cmd_Argv(1));
 if(_finite(seconds)&&seconds>=0&&seconds<3600){paused=true;pauseTime=seconds;}
}
void Audit(){
 if(!engine)return;LoadCatalogs();int passed=0,failed=0;
 for(int i=0;i<skins.count;++i){vf_assembly_t a;const char* keys[5];for(int z=0;z<5;++z)keys[z]=skins.entries[i].key;SkinAssembly(a,keys,-1);if(engine->SetAssembly(2047,&a))passed++;else failed++;}
 engine->ClearAssembly(2047);
 for(int i=0;i<arsenal.count;++i){char path[64];snprintf(path,sizeof(path),"models/vf_tfc_arsenal/%s.mdl",arsenal.entries[i].name);if(engine->SequenceInfo(path,0,NULL,0,NULL)>0)passed++;else failed++;}
 // Rejection must be atomic: an invalid replacement preserves the prior assembly.
 vf_assembly_t a;WeaponAssembly(a,3);int valid=engine->SetAssembly(2047,&a);
 a.count=VF_MAX_PARTS+1;int invalid=engine->SetAssembly(2047,&a);
 WeaponAssembly(a,3);strcpy(a.parts[0].bone,"missing_socket");int socket=engine->SetAssembly(2047,&a);
 vf_render_stats_t s={};s.size=sizeof(s);engine->GetStats(&s);
 engine->ClearAssembly(2047);
 gEngfuncs.Con_DPrintf("VFEngine audit: loaded=%d failed=%d valid=%d rejected_count=%d rejected_socket=%d\n",passed,failed,valid,!invalid,!socket);
}
bool Preview(vf_assembly_t& a,float yaw,float zoom,float x,float y,float w,float h){
 if(!engine)return false;
 if(strcmp(lastRig,a.rig)){strcpy(lastRig,a.rig);sequence=0;animationStart=gEngfuncs.GetClientTime();pauseTime=0;}
 char name[40];float duration=0;sequences=engine->SequenceInfo(a.rig,0,NULL,0,NULL);
 if(sequence>=sequences)sequence=0;
 engine->SequenceInfo(a.rig,sequence,name,sizeof(name),&duration);
 snprintf(animationLabel,sizeof(animationLabel),"T : animation %d/%d %s   P : %s",sequence+1,sequences,name,paused?"reprendre":"pause");
 vf_preview_t v={};v.size=sizeof(v);v.x=(int)x;v.y=(int)y;v.width=(int)w;v.height=(int)h;v.sequence=sequence;
 v.seconds=paused?pauseTime:gEngfuncs.GetClientTime()-animationStart;v.yaw=yaw;v.zoom=zoom;
 v.yaw+=(!strcmp(a.rig,rig)||!strcmp(a.rig,"models/vf_skins/persona_rig.mdl"))?0.f:55.f;
 int drawn=engine->DrawPreview(&v,&a);
 if(drawn&&benchCount>=0){
  auto now=std::chrono::steady_clock::now();
  if(benchWarmup>0){--benchWarmup;benchLast=now;}
  else{
   vf_render_stats_t s={};s.size=sizeof(s);engine->GetStats(&s);
   benchTimes[benchCount]=s.last_preview_ms;benchFrames[benchCount]=std::chrono::duration<double,std::milli>(now-benchLast).count();benchLast=now;
   if(++benchCount==180){double sum=0,frames=0;for(int i=0;i<180;++i){sum+=benchTimes[i];frames+=benchFrames[i];}std::sort(benchTimes,benchTimes+180);
    gEngfuncs.Con_DPrintf("VFBench %s: samples=180 mean_ms=%.4f p95_ms=%.4f frame_ms=%.4f loads=%u textures_bytes=%u\n",benchLabel,sum/180,benchTimes[170],frames/180,s.model_loads-benchLoads,s.texture_bytes);benchCount=-1;
   }
  }
 }
 return drawn!=0;
}
}
extern "C" int CL_DLLEXPORT HUD_VFEngineInterface(int version,const vf_engine_api_t* api){
 engine=NULL;if(version!=VF_ENGINE_API_VERSION||!api||api->version!=version||api->size!=sizeof(*api))return 0;
 engine=api;return 1;
}
bool VF_EngineAvailable(){return engine!=NULL;}
void VF_EngineInit(){
 gEngfuncs.pfnAddCommand("vf_reference_audit",ReferenceAudit);
 gEngfuncs.pfnAddCommand("vf_reference_hands",ReferenceHands);
 gEngfuncs.pfnHookUserMsg("VFState",State);gEngfuncs.pfnAddCommand("vf_engine_stats",Stats);gEngfuncs.pfnAddCommand("vf_equipment_audit",EquipmentAudit);gEngfuncs.pfnAddCommand("vf_engine_audit",Audit);
 gEngfuncs.pfnAddCommand("vf_animation",AnimationCommand);gEngfuncs.pfnAddCommand("vf_animation_pause",PauseCommand);gEngfuncs.pfnAddCommand("vf_animation_time",FrameCommand);
 const char* names[]={"vf_visual_body","vf_visual_barrel","vf_visual_stock","vf_visual_front"};
 for(int z=0;z<4;++z)visualParts[z]=gEngfuncs.pfnRegisterVariable((char*)names[z],"0",FCVAR_ARCHIVE);
 thirdPersonEnabled=gEngfuncs.pfnRegisterVariable("vf_third_person","1",0);
 visualEnabled=gEngfuncs.pfnRegisterVariable("vf_visual_enabled","0",FCVAR_ARCHIVE);
 gEngfuncs.pfnAddCommand("vf_weapon_part",ModuleCommand);gEngfuncs.pfnAddCommand("vf_weapon_equip",VF_EngineModuleEquip);gEngfuncs.pfnAddCommand("vf_weapon_reset",VF_EngineModuleReset);gEngfuncs.pfnAddCommand("vf_weapon_audit",ModuleAudit);gEngfuncs.pfnAddCommand("vf_visual_bench",BenchCommand);
 gEngfuncs.Con_DPrintf("VFEngine: native extension %s\n",engine?"v3 connected":"unavailable (legacy previews)");VF_EngineReset();
}
bool VF_EngineIsReferenceWeapon(int id){return id>0&&id<=32&&players[id].active&&equipment.valid&&players[id].items[9]>0&&players[id].items[9]<equipment.count&&!strncmp(equipment.items[players[id].items[9]].id,"r01_receiver_",13);}
void VF_EngineReset(){memset(players,0,sizeof(players));weaponStyles.valid=false;requested=false;paused=false;sequence=0;lastRig[0]=0;skins.valid=arsenal.valid=equipment.valid=modules.valid=false;benchCount=-1;for(int z=0;z<4;++z)draftParts[z]=visualParts[z]&&_finite(visualParts[z]->value)&&visualParts[z]->value>=0&&visualParts[z]->value<3?(int)visualParts[z]->value:0;if(engine)engine->ClearAssembly(0);}
void VF_EngineEntity(cl_entity_s* e,const char* model){
 if(!engine||!e||!model||e->index<=0)return;
 int id=e->index;
 if(!stricmp(model,vfdeath::Model)){vf_assembly_t a;if(VF_DeathAssembly(id,a))engine->SetAssembly(id,&a);else engine->ClearAssembly(id);return;}
 int targetSkin=!e->player?VF_RangeSkin(id):-1;
 if(targetSkin>=0&&!stricmp(model,"models/vf_skins/persona_rig.mdl")){
  vf_assembly_t a={};strcpy(a.rig,"models/vf_skins/persona_rig.mdl");a.count=1;
  strcpy(a.parts[0].model,"models/vf_skins/persona_scout.mdl");a.parts[0].body=31;a.parts[0].skin=targetSkin;a.parts[0].mode=VF_PART_MERGE;
  engine->SetAssembly(id,&a);return;
 }
 if(!e->player){if(stricmp(model,rig)){engine->ClearAssembly(e->index);return;}cl_entity_t* local=gEngfuncs.GetLocalPlayer();id=local?local->index:0;}
 if(!e->player){memset(e->curstate.controller,128,sizeof(e->curstate.controller));memset(e->latched.prevcontroller,128,sizeof(e->latched.prevcontroller));}
 if(id<1||id>32||!players[id].active){engine->ClearAssembly(e->index);return;}
 const char* keys[5];for(int z=0;z<5;++z)keys[z]=skins.entries[players[id].skins[z]].key;
 vf_assembly_t a;SkinAssembly(a,keys,-1);if(!players[id].mode)EquipmentAccessories(a,players[id].items,false);bool third=ThirdPersonWeapon(a,players[id],e);if(third&&!e->player){e->curstate.sequence=41;e->curstate.frame=0;e->curstate.framerate=0;e->latched.prevsequence=41;}if(e->player){if(third&&!players[id].thirdPerson)gEngfuncs.Con_DPrintf("VFThirdPerson player=%d rig=%s parts=%d scale=%.2f replace_carried=%d\n",id,a.rig,a.count,VF_THIRD_PERSON_SCALE,a.replace_carried);players[id].thirdPerson=third;
 int stage=third&&(e->curstate.sequence==vf::PersonaSequenceCount||e->curstate.sequence==vf::PersonaSequenceCount+1)?1+(int)e->curstate.frame/64:0;
 if(stage!=players[id].reloadStage){
  gEngfuncs.Con_DPrintf("VFThirdPersonReload player=%d stage=%d sequence=%d frame=%.1f gait=%d\n",id,stage,e->curstate.sequence,e->curstate.frame,e->curstate.gaitsequence);
  players[id].reloadStage=stage;
 }
 }engine->SetAssembly(e->index,&a);
}
void VF_EngineWeapon(cl_entity_s* e,int fallbackBody){
 if(!engine)return;
 if(!requested&&gEngfuncs.GetClientTime()>1){requested=true;gEngfuncs.pfnServerCmd("vf_skin_request\nvf_request\n");}
 if(!e||!e->model||stricmp(e->model->name,"models/v_9mmar.mdl")){engine->ClearAssembly(-1);return;}
 cl_entity_t* local=gEngfuncs.GetLocalPlayer();int id=local?local->index:0;
 int body=id>0&&id<=32&&players[id].active?players[id].body:fallbackBody;
 vf_assembly_t a;if(id>0&&id<=32&&players[id].active&&!players[id].mode&&EquipmentWeapon(a,players[id].items,true,players[id].styles)){engine->SetAssembly(-1,&a);return;}
 const char* imported=VF_LibraryWeaponPath();if(imported&&!VF_EngineLinked()){memset(&a,0,sizeof(a));snprintf(a.rig,sizeof(a.rig),"%s",imported);a.draw_rig=1;if(engine->SetAssembly(-1,&a))return;}
 if(visualEnabled&&visualEnabled->value>=.5f&&VisualAssembly(a,true,false)){engine->SetAssembly(-1,&a);return;}
 // Free character skins can keep the equipped R-01. Explicit local weapon trials above still win.
 if(id>0&&id<=32&&players[id].active&&ReferenceWeapon(a,players[id].items,true,-1,players[id].styles)){engine->SetAssembly(-1,&a);return;}
 WeaponAssembly(a,body);if(engine->SetAssembly(-1,&a))e->curstate.body=body&1;
}
bool VF_EnginePreviewSkins(const char* keys[5],int isolate,float yaw,float zoom,float x,float y,float w,float h){vf_assembly_t a;SkinAssembly(a,keys,isolate);return Preview(a,yaw,zoom,x,y,w,h);}
bool VF_EnginePreviewModel(const char* path,int body,bool modular,float yaw,float zoom,float x,float y,float w,float h){
 vf_assembly_t a={};if(modular)WeaponAssembly(a,body);else{snprintf(a.rig,sizeof(a.rig),"%s",path);a.draw_rig=1;a.body=body;}
 return Preview(a,yaw,zoom,x,y,w,h);
}
bool VF_EnginePreviewAsset(const char* key,float yaw,float zoom,float x,float y,float w,float h){
 if(!arsenal.valid)LoadCatalogs();for(int i=0;i<arsenal.count;++i)if(!strcmp(key,arsenal.entries[i].key)){char path[64];snprintf(path,sizeof(path),"models/vf_tfc_arsenal/%s.mdl",arsenal.entries[i].name);return VF_EnginePreviewModel(path,0,false,yaw,zoom,x,y,w,h);}return false;
}
void VF_EngineAnimation(int step){if(sequences>0)sequence=(sequence+step+sequences)%sequences;animationStart=gEngfuncs.GetClientTime();pauseTime=0;}
void VF_EnginePause(){if(paused)animationStart=gEngfuncs.GetClientTime()-pauseTime;else pauseTime=gEngfuncs.GetClientTime()-animationStart;paused=!paused;}
const char* VF_EngineAnimationLabel(){return animationLabel;}
bool VF_EngineModulesAvailable(){if(!skins.valid)LoadCatalogs();return engine&&modules.valid;}
void VF_EngineModuleCycle(int z,int step){if(z<0||z>3)return;int n=PartCount(z);if(n)draftParts[z]=(draftParts[z]+step%n+n)%n;}
const char* VF_EngineModuleName(int z){const vf::Appearance* p=z>=0&&z<4?Part(z,draftParts[z]):NULL;return p?p->name:"Indisponible";}
void VF_EngineModuleEquip(){
 VF_LibraryClearWeapon();
 vf_assembly_t a;if(VF_EngineLinked()||!engine||!VisualAssembly(a,true,true)||!engine->SetAssembly(-1,&a))return;
 for(int z=0;z<4;++z)gEngfuncs.Cvar_SetValue(visualParts[z]->name,(float)draftParts[z]);gEngfuncs.Cvar_SetValue("vf_visual_enabled",1);
 gEngfuncs.Con_Printf("VFVisual equipped: %d,%d,%d,%d (local appearance)\n",draftParts[0],draftParts[1],draftParts[2],draftParts[3]);
}
void VF_EngineModuleReset(){VF_LibraryClearWeapon();if(visualEnabled)gEngfuncs.Cvar_SetValue("vf_visual_enabled",0);}
bool VF_EngineModulesEquipped(){if(!visualEnabled||visualEnabled->value<.5f)return false;for(int z=0;z<4;++z)if(!visualParts[z]||visualParts[z]->value!=draftParts[z])return false;return true;}
bool VF_EnginePreviewModules(float yaw,float zoom,float x,float y,float w,float h){vf_assembly_t a;return VisualAssembly(a,false,true)&&Preview(a,yaw,zoom,x,y,w,h);}

int VF_EngineModuleChoice(int z){return z>=0&&z<4?draftParts[z]:0;}
int VF_EngineModuleCount(int z){return z>=0&&z<4?PartCount(z):0;}
void VF_EngineModuleSelect(int z,int choice){if(z>=0&&z<4&&choice>=0&&choice<PartCount(z))draftParts[z]=choice;}
const char* VF_EngineModuleOption(int z,int choice){const vf::Appearance* p=z>=0&&z<4?Part(z,choice):NULL;return p?p->name:"Indisponible";}

bool VF_EngineLinked(){cl_entity_t* p=gEngfuncs.GetLocalPlayer();return !p||p->index<1||p->index>32||!players[p->index].active||!players[p->index].mode;}
void VF_EngineSetAppearanceMode(int mode){if(mode<0||mode>1)return;char cmd[48];snprintf(cmd,sizeof(cmd),"vf_appearance_mode %d\n",mode);gEngfuncs.pfnServerCmd(cmd);}
bool VF_EnginePreviewEquipment(const int* items,bool weapon,float x,float y,float w,float h,const int* styles){
 if(!skins.valid||!equipment.valid)LoadCatalogs();if(!engine||!items)return false;
 vf_assembly_t a;
 if(styles&&!vf::ValidWeaponStyles(weaponStyles,styles))return false;
 if(weapon){if(!EquipmentWeapon(a,items,referenceHands,styles))return false;}
 else{int ids[5];if(!vf::EquipmentSkins(equipment,items,skins,ids))return false;const char* keys[5];for(int z=0;z<5;++z)keys[z]=skins.entries[ids[z]].key;SkinAssembly(a,keys,-1);EquipmentAccessories(a,items,false);}
 return Preview(a,VF_PreviewYaw(),VF_PreviewZoomValue(),x,y,w,h);
}
bool VF_EnginePreviewCurrent(bool weapon,float x,float y,float w,float h){
 cl_entity_t* p=gEngfuncs.GetLocalPlayer();return p&&p->index>=1&&p->index<=32&&players[p->index].active&&VF_EnginePreviewEquipment(players[p->index].items,weapon,x,y,w,h,players[p->index].styles);
}

bool VF_EngineValidateModel(const char* path){return engine&&engine->SequenceInfo(path,0,NULL,0,NULL)>0;}

bool VF_EnginePreviewReferencePart(const int* items,int slot,float x,float y,float w,float h,const int* styles){
 if(!equipment.valid)LoadCatalogs();if(!engine||slot<9||slot>=vf::SlotCount)return false;
 if(styles&&!vf::ValidWeaponStyles(weaponStyles,styles))return false;
 vf_assembly_t a;if(!ReferenceWeapon(a,items,false,slot,styles))return false;
 // Side-mounted cassettes open towards +X; show their finished face first.
 return Preview(a,VF_PreviewYaw()+((slot==13||slot==14)?180.f:0.f),VF_PreviewZoomValue(),x,y,w,h);
}
