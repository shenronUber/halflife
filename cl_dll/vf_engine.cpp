#include "hud.h"
#include "cl_util.h"
#include "cl_entity.h"
#include "com_model.h"
#include "r_studioint.h"
extern engine_studio_api_t IEngineStudio;
#include "parsemsg.h"
#include "Exports.h"
#include "vf_engine.h"
#include "vf_ui.h"
#include "vf_character.h"
#include "../game_shared/vf_traversal.h"
#include "../game_shared/vf_weapon_melee.h"
#include "vf_death.h"
#include "../game_shared/vf_death_visual.h"
#include "vf_range.h"
#include "vf_third_person_scale.h"
#include "vf_library.h"
#include "vf_preview.h"
#include "../game_shared/vf_engine_api.h"
#include "../game_shared/vf_appearance.h"
#include "../game_shared/vf_loadout.h"
#include "../game_shared/vf_headgear.h"
#include "../game_shared/vf_player_pose.h"
#include "../game_shared/vf_headgear_feedback.h"
#include "vf_headgear_hud_catalog.h"
#include "triangleapi.h"
#include "r_efx.h"
#include "dlight.h"
#include "event_api.h"
#include "../game_shared/vf_model_contract.h"
#include <stdio.h>
#include <string.h>
#include <math.h>
#include <algorithm>
#include <chrono>
#include "camera.h"
#include "in_defs.h"
#include "../game_shared/vf_weapon_inspect.h"

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
int traversalState=0;float traversalRemaining=0,traversalYaw=0,traversalPitch=0,traversalDepth=40;
float traversalAnchor[3]={};bool traversalReport=false;
int traversalSequence=-1;float traversalStart=0;
bool requested=false,paused=false;
int sequence=0,sequences=0;
bool referenceHands=false;
void TraversalRenderInfo(){traversalReport=true;}
void TraversalLook(){if(gEngfuncs.Cmd_Argc()<2||gEngfuncs.pfnGetCvarFloat("sv_cheats")==0)return;float angles[3]={gEngfuncs.Cmd_Argc()>2?(float)atof(gEngfuncs.Cmd_Argv(2)):0,(float)atof(gEngfuncs.Cmd_Argv(1)),0};if(_finite(angles[0])&&_finite(angles[1]))gEngfuncs.SetViewAngles(angles);}
void ReferenceHands(){referenceHands=gEngfuncs.Cmd_Argc()>1?atoi(gEngfuncs.Cmd_Argv(1))!=0:!referenceHands;}
float animationStart=0,pauseTime=0;
char lastRig[64]="",animationLabel[112]="";
const char* rig="models/vf_operator.mdl";
// Optional local workshop accessory. Equipment and network state stay authoritative.
int trialHeadgear=0;
const char* headgearModel="models/vf_headgear/headgear.mdl";
void AddTrialHeadgear(vf_assembly_t& a){
 if(trialHeadgear<=0||a.count>=VF_MAX_PARTS)return;
 vf_part_t& p=a.parts[a.count++];memset(&p,0,sizeof(p));
 strcpy(p.model,headgearModel);p.body=trialHeadgear;p.mode=VF_PART_MERGE;
}
#include "vf_headgear.inc"
#include "vf_headgear_hud.inc"
#include "vf_weapon_inspect.inc"
#include "vf_weapon_melee.inc"
void HeadgearCommand(){
 const char* option=gEngfuncs.Cmd_Argc()==2?gEngfuncs.Cmd_Argv(1):"";
 int selected=!strcmp(option,"none")?0:(!strcmp(option,"riot")||!strcmp(option,"riot-down"))?1:!strcmp(option,"spartan")?2:!strcmp(option,"riot-up")?3:
  (!strcmp(option,"nvg-red")||!strcmp(option,"nvg-red-down"))?4:(!strcmp(option,"nvg-green")||!strcmp(option,"nvg-green-down"))?5:
  !strcmp(option,"nvg-red-up")?6:!strcmp(option,"nvg-green-up")?7:(!strcmp(option,"ballistic")||!strcmp(option,"ballistic-down"))?8:
  !strcmp(option,"ballistic-up")?9:(!strcmp(option,"gas-mask")||!strcmp(option,"gas-mask-down"))?10:!strcmp(option,"gas-mask-up")?11:-1;
 if(selected<0){gEngfuncs.Con_Printf("Usage: vf_headgear none|riot|riot-down|riot-up|spartan|nvg-red|nvg-red-down|nvg-red-up|nvg-green|nvg-green-down|nvg-green-up|ballistic|ballistic-down|ballistic-up|gas-mask|gas-mask-down|gas-mask-up (local visual trial)\n");return;}
 if(selected&&(!engine||engine->SequenceInfo(headgearModel,0,NULL,0,NULL)<=0)){
  gEngfuncs.Con_Printf("VFHeadgear: optional model unavailable; build and deploy headgear first\n");return;
 }
 trialHeadgear=selected;gEngfuncs.Con_Printf("VFHeadgear trial: %s variant=%d bone=Bip01 Head local=1\n",option,selected);
}
void HeadgearAudit(){
 if(!engine)return;int passed=0,failed=0;
 for(int carrier=0;carrier<4;++carrier)for(int variant=0;variant<12;++variant){
  vf_assembly_t a={};strcpy(a.rig,carrier?vf::Carrier(carrier-1).thirdPerson:"models/vf_skins/persona_rig.mdl");
  if(variant){a.count=1;strcpy(a.parts[0].model,headgearModel);a.parts[0].body=variant;a.parts[0].mode=VF_PART_MERGE;}
  if(engine->SetAssembly(2043,&a))++passed;else ++failed;
 }
 engine->ClearAssembly(2043);gEngfuncs.Con_Printf("VFHeadgear audit: carriers=4 variants=12 passed=%d failed=%d\n",passed,failed);
}
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
void SkinAssembly(vf_assembly_t& a,const char* keys[5],int isolate,bool headgear=true) {
 if(!skins.valid)LoadCatalogs();
 int ids[5];for(int z=0;z<5;++z)ids[z]=vf::FindAppearance(skins,keys[z]);
 memset(&a,0,sizeof(a));strcpy(a.rig,vf::OperatorRig(skins,ids));
 for(int z=0;z<5;++z)if(isolate<0||z==isolate){vf_part_t& p=a.parts[a.count++];const char* model=keys[z];for(int i=0;i<skins.count;++i)if(!strcmp(keys[z],skins.entries[i].key)){model=skins.entries[i].model;p.skin=(z==0&&!strncmp(model,"family_",7))?0:skins.entries[i].skin;break;}snprintf(p.model,sizeof(p.model),"models/vf_skins/%s.mdl",model);p.body=1<<z;}
 if(headgear&&(isolate<0||isolate==0)&&!strcmp(a.rig,"models/vf_skins/persona_rig.mdl"))AddTrialHeadgear(a);
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
 for(int slot=9;slot<vf::WeaponEnd;++slot){
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

void TraversalView(cl_entity_t* e,vf_assembly_t& a,const int* items){
 // This viewmodel is reused after traversal. Clear renderer metadata as well
 // as the animation track, otherwise a stale phase suppresses the H gesture.
 e->curstate.iuser4=traversalState;e->curstate.fuser1=traversalRemaining;
 int phase=VF_TR_Phase(traversalState);if(!phase){if(traversalSequence>=0){e->curstate.sequence=0;e->curstate.frame=0;e->curstate.animtime=gEngfuncs.GetClientTime();e->latched.prevsequence=0;}traversalSequence=-1;return;}
 if(strncmp(a.rig,"models/vf_r01/r01_rig",strlen("models/vf_r01/r01_rig")))return;
 const char* base=strrchr(a.rig,'/');char path[64];snprintf(path,sizeof(path),"models/vf_traversal/%.40s",base+1);
 char* extension=strstr(path,".mdl");if(extension)strcpy(extension,"_tr.mdl");
 if(engine->SequenceInfo(path,0,NULL,0,NULL)<=0)return;
 strcpy(a.rig,path);
 // Renderer-only viewmodel metadata: world contacts do not inherit camera
 // interpolation, weapon bob or firing recoil. No network field is added.
 e->curstate.iuser4=traversalState;e->curstate.fuser1=traversalRemaining;
 e->curstate.fuser2=traversalReport?1:0;traversalReport=false;
 float radians=VF_TR_Yaw(traversalState)*3.141592653589793f/180;
 float forward[2]={(float)cos(radians),(float)sin(radians)};
 float supportOffset=phase==VF_TR_VAULT?((traversalState&VF_TR_WIDE)?-26.f:-VF_TR_VaultSpan(traversalState)-20.f):18.f;
 for(int axis=0;axis<2;++axis){
  float side=axis==0?-forward[1]:forward[0];
  e->curstate.vuser1[axis]=traversalAnchor[axis]+supportOffset*forward[axis]+8*side;
  e->curstate.vuser2[axis]=traversalAnchor[axis]+18*forward[axis]-8*side;
 }
 e->curstate.vuser1[2]=e->curstate.vuser2[2]=traversalAnchor[2]-VF_TR_FP_GRIP_BELOW_TOP;
 // Sliding occupies the lower body only. Keep the weapon's live sequence,
 // clock and interpolation so firing, reload, draw and idle remain visible.
 if(phase!=VF_TR_SLIDE&&phase!=VF_TR_WALL_RUN){
 int index=phase==VF_TR_VAULT?((traversalState&VF_TR_WIDE)?25:0):phase==VF_TR_HANG?(traversalRemaining>0?((traversalState&VF_TR_RETURNING)?3:1):2):
  phase==VF_TR_ARMED?(traversalRemaining>0?3:4):phase==VF_TR_CLIMB?12:phase==VF_TR_DROP?24:phase==VF_TR_WALL_JUMP?((traversalState&VF_TR_TURNED)?27:26):
  traversalRemaining>VF_TR_SLIDE_TIME-.25f?13:traversalRemaining<.3f?15:14;
 if(VF_TR_Hanging(traversalState)&&traversalRemaining<=0){
  float delta=VF_TR_Angle(traversalYaw-VF_TR_Yaw(traversalState));
  int sector=((int)floor((delta+22.5f)/45.f)+8)%8;index=(phase==VF_TR_ARMED?4:16)+sector;
  float offset=VF_TR_Angle(delta-sector*45.f);
  e->curstate.blending[0]=(byte)(std::max)(0.f,(std::min)(255.f,(offset+22.5f)*255/45));
  e->curstate.blending[1]=(byte)(((std::max)(-70.f,(std::min)(70.f,traversalPitch))+70)*255/140);
 }else e->curstate.blending[0]=e->curstate.blending[1]=127;
 if(index!=traversalSequence){traversalSequence=index;traversalStart=gEngfuncs.GetClientTime();e->latched.prevsequence=index+9;}
 e->curstate.sequence=index+9;e->curstate.animtime=traversalStart;e->curstate.framerate=1;
 if(phase==VF_TR_VAULT||phase==VF_TR_CLIMB||phase==VF_TR_DROP||phase==VF_TR_WALL_JUMP){
  float total=phase==VF_TR_WALL_JUMP?VF_TR_WALL_JUMP_TIME:phase==VF_TR_DROP?VF_TR_DROP_TIME:VF_TR_TransferTime(traversalState);
  e->curstate.frame=(std::max)(0.f,(std::min)(255.f,(1-traversalRemaining/total)*255));e->curstate.framerate=0;
 }else if(index==3){
  float progress=(VF_TR_HANG_DEPTH-traversalDepth)/(VF_TR_HANG_DEPTH-VF_TR_ARMED_DEPTH);
  e->curstate.frame=(std::max)(0.f,(std::min)(255.f,progress*255));e->curstate.framerate=0;
 }else e->curstate.frame=0;
 }else {
  traversalSequence=-1;
  if(e->curstate.sequence>=9)e->curstate.sequence=0;
  if(e->latched.prevsequence>=9)e->latched.prevsequence=e->curstate.sequence;
 }
 // Busy hands show the same equipped gloves and sleeves, with no gun floating
 // between them. Armed suspension retains the chassis and its muzzle socket.
 if(VF_TR_HideWeapon(traversalState,traversalRemaining)){
  int count=0;for(int i=0;i<a.count;++i)if(a.parts[i].mode==VF_PART_MERGE)a.parts[count++]=a.parts[i];a.count=count;
  for(int i=0;i<a.count;++i)if(strstr(a.parts[i].model,"_gloves.mdl"))strcpy(a.parts[i].model,"models/vf_traversal/ledge_gloves.mdl");
  for(int i=0;i<a.count;++i)if(strstr(a.parts[i].model,"_sleeves.mdl"))strcpy(a.parts[i].model,"models/vf_traversal/ledge_sleeves.mdl");
 }
 if(phase==VF_TR_VAULT)for(int i=0;i<a.count;++i)if(strstr(a.parts[i].model,"_gloves.mdl"))strcpy(a.parts[i].model,"models/vf_traversal/ledge_gloves.mdl");
 // Seated legs now use the equipped world body. A socket on the weapon root
 // would rotate both boots with camera pitch and yaw.
}
void ReferenceAudit(){
 if(!engine)return;LoadCatalogs();int ids[12][vf::MaxItems]={},counts[12]={},items[vf::SlotCount];vf::GameplayDefaults(equipment,items);
 for(int i=1;i<equipment.count;++i){const vf::Item& p=equipment.items[i];if(vf::WeaponSlot(p.slot)&&!strcmp(p.weaponStyle,"original"))ids[p.slot-9][counts[p.slot-9]++]=i;}
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
  if(vf::WeaponSlot(equipment.items[i].slot))ok=EquipmentWeapon(a,items,false);
  else{int ids[5];ok=vf::EquipmentSkins(equipment,items,skins,ids);if(ok){const char* keys[5];for(int z=0;z<5;++z)keys[z]=skins.entries[ids[z]].key;SkinAssembly(a,keys,-1);EquipmentAccessories(a,items,false);AddEquippedHeadgear(a,items);}}
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
  if(peer)gEngfuncs.Con_DPrintf("VFPeerTraversal player=%d phase=%d sequence=%d gait=%d wall=%.2f top=%.3f blends=%d,%d\n",i,VF_TR_Phase(peer->curstate.iuser4),peer->curstate.sequence,peer->curstate.gaitsequence,VF_TR_Yaw(peer->curstate.iuser4),peer->curstate.fuser4,peer->curstate.blending[0],peer->curstate.blending[1]);
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
void VF_TraversalPredict(int state,float remaining,float yaw,float pitch,float depth,const float* anchor,float top){traversalAnchor[0]=anchor[0];traversalAnchor[1]=anchor[1];traversalAnchor[2]=top;traversalDepth=depth;traversalState=state;traversalRemaining=remaining;traversalYaw=yaw;traversalPitch=pitch;}
float VF_TraversalViewBobScale(){return VF_TR_Phase(traversalState)==VF_TR_SLIDE?.1f:1.f;}
float VF_TraversalViewPitch(){
 if(VF_TR_Phase(traversalState)!=VF_TR_VAULT)return 0;
 float t=max(0.f,min(1.f,1-traversalRemaining/VF_TR_TransferTime(traversalState)));
 float w=t<.20f?t/.20f:t<.40f?1:(.62f-t)/.22f;w=max(0.f,min(1.f,w));
 return 35*w*w*(3-2*w);
}

void VF_TraversalHud(){
 if(VF_CharacterOpen())return;int phase=VF_TR_Phase(traversalState);const char* hint=NULL;
 if(phase==VF_TR_HANG)hint="Rebord : ESPACE monter / CTRL lacher / Clic droit armer";
 if(phase==VF_TR_ARMED)hint=VF_TR_CanFire(traversalState,traversalRemaining,traversalYaw)?"Tir / Recharge bloquee / Clic droit : deux mains":"Tournez-vous sur le cote pour tirer / Clic droit : deux mains";
 if(phase==VF_TR_SLIDE)hint="Glissade : CTRL maintenu / ESPACE sauter";
 if(phase==VF_TR_WALL_RUN)hint="Wall run : avancer maintenu / ESPACE rebond vers le regard";
 if(hint){vfui::Box(270,650,740,32,vfui::bg,185);vfui::Text(284,657,hint,vfui::white,710);}
}
bool VF_EngineAvailable(){return engine!=NULL;}
void VF_EngineInit(){
 headgearHud=gEngfuncs.pfnRegisterVariable("vf_headgear_hud","1",FCVAR_ARCHIVE);
 gEngfuncs.pfnAddCommand("vf_headgear_hud_info",HeadgearHudInfo);
 gEngfuncs.pfnAddCommand("vf_inspect",InspectCommand);gEngfuncs.pfnAddCommand("vf_inspect_info",InspectInfo);
 gEngfuncs.pfnAddCommand("vf_melee",MeleeCommand);gEngfuncs.pfnAddCommand("vf_melee_info",MeleeInfo);gEngfuncs.pfnHookUserMsg("VFMelee",MeleeMessage);
 gEngfuncs.pfnAddCommand("vf_headgear_toggle",HeadgearToggle);gEngfuncs.pfnAddCommand("vf_headgear_info",HeadgearInfo);gEngfuncs.pfnHookUserMsg("VFHeadgear",HeadgearMessage);
 gEngfuncs.pfnAddCommand("vf_headgear",HeadgearCommand);gEngfuncs.pfnAddCommand("vf_headgear_audit",HeadgearAudit);
 gEngfuncs.pfnAddCommand("vf_reference_audit",ReferenceAudit);
 gEngfuncs.pfnAddCommand("vf_traversal_look",TraversalLook);
 gEngfuncs.pfnAddCommand("vf_traversal_render_info",TraversalRenderInfo);
 gEngfuncs.pfnAddCommand("vf_reference_hands",ReferenceHands);
 gEngfuncs.pfnHookUserMsg("VFState",State);gEngfuncs.pfnAddCommand("vf_engine_stats",Stats);gEngfuncs.pfnAddCommand("vf_equipment_audit",EquipmentAudit);gEngfuncs.pfnAddCommand("vf_engine_audit",Audit);
 gEngfuncs.pfnAddCommand("vf_animation",AnimationCommand);gEngfuncs.pfnAddCommand("vf_animation_pause",PauseCommand);gEngfuncs.pfnAddCommand("vf_animation_time",FrameCommand);
 const char* names[]={"vf_visual_body","vf_visual_barrel","vf_visual_stock","vf_visual_front"};
 for(int z=0;z<4;++z)visualParts[z]=gEngfuncs.pfnRegisterVariable((char*)names[z],"0",FCVAR_ARCHIVE);
 thirdPersonEnabled=gEngfuncs.pfnRegisterVariable("vf_third_person","1",0);
 visualEnabled=gEngfuncs.pfnRegisterVariable("vf_visual_enabled","0",FCVAR_ARCHIVE);
 gEngfuncs.pfnAddCommand("vf_weapon_part",ModuleCommand);gEngfuncs.pfnAddCommand("vf_weapon_equip",VF_EngineModuleEquip);gEngfuncs.pfnAddCommand("vf_weapon_reset",VF_EngineModuleReset);gEngfuncs.pfnAddCommand("vf_weapon_audit",ModuleAudit);gEngfuncs.pfnAddCommand("vf_visual_bench",BenchCommand);
 gEngfuncs.Con_DPrintf("VFTraversal render: world palms=2\n");
 gEngfuncs.Con_DPrintf("VFBody render: world body=1\n");
 gEngfuncs.Con_DPrintf("VFBody motion: world slide=1\n");
 gEngfuncs.Con_DPrintf("VFEngine: native extension %s\n",engine?"v4 connected":"unavailable (legacy previews)");VF_EngineReset();
 gEngfuncs.Con_DPrintf("VFPlayerPose collision: shared=1\n");
 gEngfuncs.Con_DPrintf("VFMelee pose: shared=1\n");
}
bool VF_EngineIsReferenceWeapon(int id){return id>0&&id<=32&&players[id].active&&equipment.valid&&players[id].items[9]>0&&players[id].items[9]<equipment.count&&!strncmp(equipment.items[players[id].items[9]].id,"r01_receiver_",13);}
void VF_InspectPredict(int weapon,int buttons,bool reload,float nextAttack){inspectWeapon=weapon;inspectButtons=buttons;inspectReload=reload;inspectNextAttack=nextAttack;}
void VF_EngineReset(){memset(meleeClients,0,sizeof(meleeClients));meleePosed=meleeReport=false;HeadgearVisionReset();inspectState.Reset();inspectWeapon=inspectButtons=0;inspectReload=inspectReport=false;inspectNextAttack=0;trialHeadgear=0;traversalState=0;traversalSequence=-1;memset(players,0,sizeof(players));memset(headgearStates,0,sizeof(headgearStates));weaponStyles.valid=false;requested=false;paused=false;sequence=0;lastRig[0]=0;skins.valid=arsenal.valid=equipment.valid=modules.valid=false;benchCount=-1;for(int z=0;z<4;++z)draftParts[z]=visualParts[z]&&_finite(visualParts[z]->value)&&visualParts[z]->value>=0&&visualParts[z]->value<3?(int)visualParts[z]->value:0;if(engine)engine->ClearAssembly(0);}
void VF_EngineEntity(cl_entity_s* e,const char* model){
 HeadgearVisionEntity(e);
 if(!engine||!e||!model||e->index<=0)return;
 int id=e->index;
 if(!stricmp(model,vfdeath::Model)){vf_assembly_t a;if(VF_DeathAssembly(id,a))engine->SetAssembly(id,&a);else engine->ClearAssembly(id);return;}
 int targetSkin=!e->player?VF_RangeSkin(id):-1;
 if(targetSkin>=0&&!stricmp(model,"models/vf_skins/persona_rig.mdl")){
  vf_assembly_t a={};strcpy(a.rig,"models/vf_skins/persona_rig.mdl");a.count=1;
  strcpy(a.parts[0].model,"models/vf_skins/persona_scout.mdl");a.parts[0].body=31;a.parts[0].skin=targetSkin;a.parts[0].mode=VF_PART_MERGE;
  AddTrialHeadgear(a);
  engine->SetAssembly(id,&a);return;
 }
 if(!e->player){if(stricmp(model,rig)){engine->ClearAssembly(e->index);return;}cl_entity_t* local=gEngfuncs.GetLocalPlayer();id=local?local->index:0;}
 if(!e->player){memset(e->curstate.controller,128,sizeof(e->curstate.controller));memset(e->latched.prevcontroller,128,sizeof(e->latched.prevcontroller));}
 if(id<1||id>32||!players[id].active){engine->ClearAssembly(e->index);return;}
 const char* keys[5];for(int z=0;z<5;++z)keys[z]=skins.entries[players[id].skins[z]].key;
 cl_entity_t* local=gEngfuncs.GetLocalPlayer();
 vf_assembly_t a;SkinAssembly(a,keys,-1,local&&local->index==id);if(!players[id].mode)EquipmentAccessories(a,players[id].items,false);bool third=ThirdPersonWeapon(a,players[id],e);if(third&&!e->player){e->curstate.sequence=41;e->curstate.frame=0;e->curstate.framerate=0;e->latched.prevsequence=41;}if(e->player){if(third&&!players[id].thirdPerson)gEngfuncs.Con_DPrintf("VFThirdPerson player=%d rig=%s parts=%d scale=%.2f replace_carried=%d\n",id,a.rig,a.count,VF_THIRD_PERSON_SCALE,a.replace_carried);players[id].thirdPerson=third;
 int stage=third&&(e->curstate.sequence==vf::PersonaSequenceCount||e->curstate.sequence==vf::PersonaSequenceCount+1)?1+(int)e->curstate.frame/64:0;
 if(stage!=players[id].reloadStage){
  gEngfuncs.Con_DPrintf("VFThirdPersonReload player=%d stage=%d sequence=%d frame=%.1f gait=%d\n",id,stage,e->curstate.sequence,e->curstate.frame,e->curstate.gaitsequence);
  players[id].reloadStage=stage;
 }
 }
 if(e->player && VF_TR_Phase(e->curstate.iuser4) && !strcmp(a.rig,"models/vf_skins/persona_rig.mdl")){
  strcpy(a.rig,vf::Carrier(0).thirdPerson);
 }
 if(e->player && VF_TR_HideWeapon(e->curstate.iuser4,e->curstate.fuser1)){
  a.replace_carried=1;int count=0;for(int i=0;i<a.count;++i)if(a.parts[i].mode!=VF_PART_SOCKET || strncmp(a.parts[i].model,"models/vf_r01/",14))a.parts[count++]=a.parts[i];a.count=count;
 }
 MeleeAssembly(e,a,id,false);
 AddEquippedHeadgear(a,players[id].items,id,false,e);
 engine->SetAssembly(e->index,&a);
}
void VF_EngineWeapon(cl_entity_s* e,int fallbackBody){
 if(!engine)return;
 if(e)MeleeView(e);
 if(!requested&&gEngfuncs.GetClientTime()>1){requested=true;gEngfuncs.pfnServerCmd("vf_skin_request\nvf_request\n");}
 if(!e||!e->model||stricmp(e->model->name,"models/v_9mmar.mdl")){InspectCancel("weapon changed");engine->ClearAssembly(-1);return;}
 InspectView(e);
 cl_entity_t* local=gEngfuncs.GetLocalPlayer();int id=local?local->index:0;
 int body=id>0&&id<=32&&players[id].active?players[id].body:fallbackBody;
 vf_assembly_t a;if(id>0&&id<=32&&players[id].active&&!players[id].mode&&EquipmentWeapon(a,players[id].items,true,players[id].styles)){TraversalView(e,a,players[id].items);AddEquippedHeadgear(a,players[id].items,id,true);FreezeHeadgearWeapon(e,id);InspectAssembly(e,a);MeleeAssembly(e,a,id,true);engine->SetAssembly(-1,&a);return;}
 const char* imported=VF_LibraryWeaponPath();if(imported&&!VF_EngineLinked()){memset(&a,0,sizeof(a));snprintf(a.rig,sizeof(a.rig),"%s",imported);a.draw_rig=1;if(engine->SetAssembly(-1,&a))return;}
 if(visualEnabled&&visualEnabled->value>=.5f&&VisualAssembly(a,true,false)){TraversalView(e,a,players[id].items);AddEquippedHeadgear(a,players[id].items,id,true);FreezeHeadgearWeapon(e,id);InspectAssembly(e,a);MeleeAssembly(e,a,id,true);engine->SetAssembly(-1,&a);return;}
 // Free character skins can keep the equipped R-01. Explicit local weapon trials above still win.
 if(id>0&&id<=32&&players[id].active&&ReferenceWeapon(a,players[id].items,true,-1,players[id].styles)){TraversalView(e,a,players[id].items);AddEquippedHeadgear(a,players[id].items,id,true);FreezeHeadgearWeapon(e,id);InspectAssembly(e,a);MeleeAssembly(e,a,id,true);engine->SetAssembly(-1,&a);return;}
 WeaponAssembly(a,body);if(id>0&&id<=32){AddEquippedHeadgear(a,players[id].items,id,true);FreezeHeadgearWeapon(e,id);}if(engine->SetAssembly(-1,&a))e->curstate.body=body&1;
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
 else{int ids[5];if(!vf::EquipmentSkins(equipment,items,skins,ids))return false;const char* keys[5];for(int z=0;z<5;++z)keys[z]=skins.entries[ids[z]].key;SkinAssembly(a,keys,-1);EquipmentAccessories(a,items,false);AddEquippedHeadgear(a,items);}
 return Preview(a,VF_PreviewYaw(),VF_PreviewZoomValue(),x,y,w,h);
}
bool VF_EnginePreviewCurrent(bool weapon,float x,float y,float w,float h){
 cl_entity_t* p=gEngfuncs.GetLocalPlayer();return p&&p->index>=1&&p->index<=32&&players[p->index].active&&VF_EnginePreviewEquipment(players[p->index].items,weapon,x,y,w,h,players[p->index].styles);
}

bool VF_EngineValidateModel(const char* path){return engine&&engine->SequenceInfo(path,0,NULL,0,NULL)>0;}

void VF_HeadgearScreen(){HeadgearScreenDraw();}
bool VF_HeadgearVoiceMuffled(int player){int type=0;float cover=HeadgearPlayerCover(player,&type);return vf::HeadgearMuffled(type,cover);}

bool VF_EnginePreviewReferencePart(const int* items,int slot,float x,float y,float w,float h,const int* styles){
 if(!equipment.valid)LoadCatalogs();if(!engine||slot<9||slot>=vf::WeaponEnd)return false;
 if(styles&&!vf::ValidWeaponStyles(weaponStyles,styles))return false;
 vf_assembly_t a;if(!ReferenceWeapon(a,items,false,slot,styles))return false;
 // Side-mounted cassettes open towards +X; show their finished face first.
 return Preview(a,VF_PreviewYaw()+((slot==13||slot==14)?180.f:0.f),VF_PreviewZoomValue(),x,y,w,h);
}
