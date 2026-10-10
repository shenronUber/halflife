#include "hud.h"
#include "cl_util.h"
#include "parsemsg.h"
#include "keydefs.h"
#include "vf_character.h"
#include "vf_preview.h"
#include "vf_engine.h"
#include "vf_range.h"
#include "vf_skinmenu.h"
#include "vf_ui.h"
#include "vf_effects.h"
#include "cl_entity.h"
#include "com_model.h"
#include "../game_shared/vf_loadout.h"
#include "../game_shared/vf_appearance.h"
#include <stdio.h>
#include <string.h>

namespace {
vf::Catalog catalog;
vf::AppearanceCatalog weaponStyles;
int draftStyles[vf::WeaponStyleSlots]={},appliedStyles[vf::WeaponStyleSlots]={};
bool styleWhole=true;
bool Eligible(const vf::Item& item){return vfui::Developer()?!item.model[0]:vf::GameplayItem(item);}
int draft[vf::SlotCount],applied[vf::SlotCount];
int gameplayItems[vf::SlotCount]={},gameplayStyles[vf::WeaponStyleSlots]={};bool gameplaySaved=false;
bool opened=false,synchronized=false,pending=false;
int tab=0,row=0,familyFilter=-1,itemPage=0,collectionFilter=-1;
bool CollectionMatch(const vf::Item& item){return collectionFilter<0||!strcmp(item.flavor,weaponStyles.entries[collectionFilter].name);}
float fixedAngles[3],requestTime=0;
char status[128]="F1 : ouvrir le personnage";

int referencePending=-1,platformPending=-1;bool referenceIsolate=false;
bool IsReference(){return draft[9]>0&&draft[9]<catalog.count&&!strncmp(catalog.items[draft[9]].id,"r01_receiver_",13);}
void FocusSelection();
void ApplyReference(int v){
 if(!vfui::Developer()||v<0||v>5)return;
 int selected[vf::SlotCount];memcpy(selected,draft,sizeof(selected));
 const char* theme=v==4?"inventor":v==5?"diesel":NULL;
 int base=v<4?v:v-2,finish=theme?vf::FindAppearance(weaponStyles,v==4?"roman_inventor":"dieselpunk"):-1;
 if(theme&&finish<0){strcpy(status,"Finition du theme absente du catalogue.");return;}
 for(int s=9;s<vf::SlotCount;++s){
  char key[40];
  if(theme&&s==9)snprintf(key,sizeof(key),"r01_receiver_%s",v==4?"arch":"gyre");
  else if(theme&&(s==13||s==16||s==19||s==20))snprintf(key,sizeof(key),"r01_%s_%s",vf::SlotKeys[s],theme);
  else snprintf(key,sizeof(key),"r01_%s_%c",vf::SlotKeys[s],"abcd"[base]);
  int id=vf::FindItem(catalog,key);if(id<=0){strcpy(status,"Ensemble incomplet dans le catalogue.");return;}selected[s]=id;
 }
 memcpy(draft,selected,sizeof(draft));
 if(theme)for(int s=0;s<vf::WeaponStyleSlots;++s)draftStyles[s]=finish;
 familyFilter=-1;FocusSelection();referenceIsolate=false;VF_PreviewRotate(185.f-VF_PreviewYaw());
 strcpy(status,theme?"Ensemble et finition du theme charges. Inspecter puis appliquer.":"Relais R-01 : 12 interfaces / 3 alimentations. Inspecter puis appliquer.");
 if(theme)gEngfuncs.Con_DPrintf("VFR01 themed set: %s chamber=%s optic=%s power=%s cooling=%s\n",theme,catalog.items[draft[13]].id,catalog.items[draft[16]].id,catalog.items[draft[19]].id,catalog.items[draft[20]].id);
}
void ReferenceCommand(){
 if(gEngfuncs.Cmd_Argc()==1){VF_CharacterReference(-1);return;}
 unsigned int variant;if(gEngfuncs.Cmd_Argc()==2&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),variant)&&variant<6)VF_CharacterReference((int)variant);
}
void ReferenceIsolate(){referenceIsolate=!referenceIsolate;}

void ApplyPlatform(int platform){
 if(!vfui::Developer())return;
 if(!IsReference())ApplyReference(0);
 const char* key=platform==1?"r01_receiver_side":platform==2?"r01_receiver_top":"r01_receiver_a";
 // Retain a chassis already using this feed position, and all other pieces.
 const char* current=catalog.items[draft[9]].id;
 if(platform==vf::ReceiverMount(catalog.items[draft[9]]))key=current;
 for(int i=1;i<catalog.count;++i)if(!strcmp(key,catalog.items[i].id)){draft[9]=i;break;}
 FocusSelection();referenceIsolate=false;strcpy(status,"Alimentation modifiee. Chargeur et autres pieces conserves.");
 gEngfuncs.Con_DPrintf("VFR01 platform: %d feed=%s\n",platform,catalog.items[draft[12]].id);
}
void PlatformCommand(){
 if(!vfui::Developer())return;
 unsigned int p;if(gEngfuncs.Cmd_Argc()!=2||!vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),p)||p>2)return;
 VF_CharacterReference(-1);if(pending)return;
 if(synchronized)ApplyPlatform((int)p);else platformPending=(int)p;
}

bool Dirty() { return memcmp(draft,applied,sizeof(draft))!=0||memcmp(draftStyles,appliedStyles,sizeof(draftStyles))!=0; }
int Slot() { return (tab?vf::GearSlots:0)+row; }
void FocusSelection(){
 int ordinal=0,slot=Slot();bool ref=tab&&IsReference();
 for(int i=1;i<catalog.count;++i){const vf::Item& item=catalog.items[i];
  if(item.slot!=slot||!Eligible(item)||(!vfui::Developer()&&!CollectionMatch(item))||(ref&&strncmp(item.id,"r01_",4)))continue;
  if(i==draft[slot]){itemPage=ordinal/(vfui::Developer()?(ref?2:4):6);return;}++ordinal;
 }itemPage=0;
}
void ChooseStyle(int id,int slot){
 if(!vfui::Developer()||!synchronized||pending||!IsReference()||!weaponStyles.valid||id<0||id>=weaponStyles.count)return;
 // Editing finishes belongs to the lab; detach any fixed inventory identity.
 for(int s=9;s<vf::SlotCount;++s)if(slot<0||s==slot){int at=draft[s];if(at>0&&catalog.items[at].model[0])draft[s]=vf::FindItem(catalog,catalog.items[at].model);}
 if(slot<0)for(int s=0;s<vf::WeaponStyleSlots;++s)draftStyles[s]=id;
 else if(slot>=9&&slot<vf::SlotCount)draftStyles[slot-9]=id;else return;
 gEngfuncs.Con_DPrintf("VFR01 draft style: id=%d slot=%d\n",id,slot);
 strcpy(status,"Finition modifiee : inspecter puis appliquer.");
}
void StyleCommand(){
 unsigned int id,slot;
 if((gEngfuncs.Cmd_Argc()!=2&&gEngfuncs.Cmd_Argc()!=3)||!vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),id))return;
 if(gEngfuncs.Cmd_Argc()==3){if(!vf::ParseUnsigned(gEngfuncs.Cmd_Argv(2),slot)||slot<9||slot>=vf::SlotCount)return;ChooseStyle((int)id,(int)slot);}
 else ChooseStyle((int)id,-1);
}
void Load() {
    int size=0; byte* bytes=gEngfuncs.COM_LoadFile((char*)"vf/equipment.txt",5,&size);
    vf::ParseCatalog((const char*)bytes,size>0?size:0,catalog);
    if(bytes) gEngfuncs.COM_FreeFile(bytes);
    size=0;bytes=gEngfuncs.COM_LoadFile((char*)"vf/r01_styles.txt",5,&size);
    vf::ParseAppearances((const char*)bytes,size>0?size:0,weaponStyles);
    if(bytes)gEngfuncs.COM_FreeFile(bytes);
}
void Toggle() {
    vfui::Focus();gEngfuncs.pfnClientCmd("-attack\n-attack2\n");
    if(opened) { opened=false; return; }
    VF_SkinsClose();VF_SkinsRefresh();Load(); opened=true; synchronized=false; pending=false;
    gEngfuncs.GetViewAngles(fixedAngles);
    if(vfui::Developer())vf::Defaults(catalog,draft);else vf::GameplayDefaults(catalog,draft); memcpy(applied,draft,sizeof(draft));
    memset(draftStyles,0,sizeof(draftStyles));vf::BindWeaponStyles(catalog,weaponStyles,draft,draftStyles);memcpy(appliedStyles,draftStyles,sizeof(appliedStyles));
    requestTime=gEngfuncs.GetClientTime();
    if(!catalog.valid) { snprintf(status,sizeof(status),"Catalogue indisponible : %s",catalog.error); return; }
    strcpy(status,"Lecture de l'equipement...");
    gEngfuncs.pfnServerCmd("vf_request\n");
}
void GameplayCommand(){
 if(opened&&!vfui::Developer()&&!tab){VF_CharacterClose();return;}
 VF_CharacterGameplay(0);
}
void ItemCommand(){
 if(!opened||!synchronized||pending||gEngfuncs.Cmd_Argc()!=2)return;
 for(int i=1;i<catalog.count;++i)if(!strcmp(catalog.items[i].id,gEngfuncs.Cmd_Argv(1))&&Eligible(catalog.items[i])){
  int at=catalog.items[i].slot;draft[at]=i;tab=at>=vf::GearSlots;row=at-(tab?vf::GearSlots:0);itemPage=0;
  vf::BindWeaponStyles(catalog,weaponStyles,draft,draftStyles);collectionFilter=-1;FocusSelection();gEngfuncs.Con_DPrintf("VFGameplay draft: %s\n",catalog.items[i].id);break;
 }
}
void Outfit(const char* appearance){
 if(!vfui::Developer()||!synchronized||pending||!appearance||!*appearance)return;
 for(int i=1;i<catalog.count;++i)if(!strcmp(catalog.items[i].appearance,appearance))draft[catalog.items[i].slot]=i;
 FocusSelection();strcpy(status,"Tenue chargee. Les autres equipements sont conserves. Appliquer pour valider.");
}
void OutfitCommand(){
 if(!opened||gEngfuncs.Cmd_Argc()!=2)return;
 char key[40];snprintf(key,sizeof(key),"persona_%s",gEngfuncs.Cmd_Argv(1));Outfit(key);
}
void CycleItem(int direction){
 if(!opened||!synchronized||pending)return;
 int at=Slot();bool optional=at==1||at==4||at==7||at==8;
 for(int step=1;step<=catalog.count;++step){int id=(draft[at]+(direction>0?step:catalog.count*2-step))%catalog.count;
  if(!id){if((vfui::Developer()&&!IsReference())||optional){draft[at]=0;break;}continue;}
  const vf::Item& item=catalog.items[id];
  if(item.slot!=at||!Eligible(item)||(tab&&IsReference()&&strncmp(item.id,"r01_",4)))continue;
  draft[at]=id;break;
 }
 vf::BindWeaponStyles(catalog,weaponStyles,draft,draftStyles);FocusSelection();
 strcpy(status,Dirty()?"Modifications en attente de validation.":"Equipement actuel.");
}
void Next(){CycleItem(1);}
void Commit() {
    if(!opened||!synchronized||pending) return;
    int totals[vf::BudgetCount];
    vf::Result result=vfui::Developer()?vf::EvaluateExperiment(catalog,draft,totals):vf::EvaluateGameplay(catalog,draft,totals);
    if(result!=vf::Accepted) { strcpy(status,result==vf::Incompatible?"Assemblage incomplet ou pieces incompatibles.":"Capacite depassee : alleger la configuration.");return; }
    char command[512]; int n=snprintf(command,sizeof(command),"%s %u",vfui::Developer()?"vf_apply_dev":"vf_apply",catalog.fingerprint);
    for(int s=0;s<vf::SlotCount;++s) n+=snprintf(command+n,sizeof(command)-n," %d",draft[s]);
    n+=snprintf(command+n,sizeof(command)-n," %u",weaponStyles.hash);
    for(int s=0;s<vf::WeaponStyleSlots;++s)n+=snprintf(command+n,sizeof(command)-n," %d",draftStyles[s]);
    snprintf(command+n,sizeof(command)-n,"\n");
    pending=true; requestTime=gEngfuncs.GetClientTime(); strcpy(status,"Validation de l'equipement...");
    gEngfuncs.pfnServerCmd(command);
}
void SwitchTab() { if(opened) { tab=1-tab;row=0;collectionFilter=-1;FocusSelection(); } }
void SelectSlot() {
    if(!opened||gEngfuncs.Cmd_Argc()!=2)return;
    unsigned int s;
    if(vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),s)&&s<vf::SlotCount) {tab=s>=vf::GearSlots;row=s-(tab?vf::GearSlots:0);collectionFilter=-1;FocusSelection();}
}
void Rotate() {VF_PreviewRotate(30);}
void InspectModel() {
    cl_entity_t* view=gEngfuncs.GetViewModel();
    if(view&&view->model)
        gEngfuncs.Con_Printf("VF viewmodel: body=%d model=%s\n",view->curstate.body,view->model->name);
}
void Restore() { if(opened&&!pending) { memcpy(draft,applied,sizeof(draft));memcpy(draftStyles,appliedStyles,sizeof(draftStyles));strcpy(status,"Modifications annulees."); } }
int Message(const char*,int size,void* buffer) {
    if(size!=vf::BuildMessageSize) return 1;
    BEGIN_READ(buffer,size);
    int protocol=READ_BYTE(),result=READ_BYTE(); unsigned int hash=(unsigned int)READ_LONG(),styleHash=(unsigned int)READ_LONG();
    int received[vf::SlotCount]; for(int s=0;s<vf::SlotCount;++s) received[s]=READ_SHORT();
    int receivedStyles[vf::WeaponStyleSlots];for(int s=0;s<vf::WeaponStyleSlots;++s)receivedStyles[s]=READ_BYTE();
    const bool firstSync=!synchronized;
    const bool referenceSubmission=pending&&tab&&IsReference();
    pending=false;
    if(protocol!=vf::Protocol||!catalog.valid||hash!=catalog.fingerprint||styleHash!=weaponStyles.hash||!vf::BoundWeaponStyles(catalog,weaponStyles,received,receivedStyles)) {
        synchronized=false;strcpy(status,"Catalogue different : fermer puis rouvrir le menu.");return 1;
    }
    int totals[vf::BudgetCount];
    if(vf::Evaluate(catalog,received,totals)!=vf::Accepted) {
        synchronized=false;strcpy(status,"Equipement recu invalide.");return 1;
    }
    memcpy(applied,received,sizeof(applied));memcpy(appliedStyles,receivedStyles,sizeof(appliedStyles));
    if(!synchronized||result==vf::Accepted){memcpy(draft,received,sizeof(draft));memcpy(draftStyles,receivedStyles,sizeof(draftStyles));}
    synchronized=true;if(firstSync)FocusSelection();
    if(!vfui::Developer()&&result==vf::Accepted){
        bool eligible=true;for(int s=0;s<vf::SlotCount;++s){int id=applied[s];if(id&&!vf::GameplayItem(catalog.items[id]))eligible=false;}
        if(eligible){memcpy(gameplayItems,applied,sizeof(applied));memcpy(gameplayStyles,appliedStyles,sizeof(appliedStyles));gameplaySaved=true;}
    }
    // A confirmed R-01 choice replaces local weapon previews, not the body skin.
    if(referenceSubmission&&result==vf::Accepted)VF_EngineModuleReset();
    strcpy(status,result==vf::Accepted?"Equipement enregistre.":"Configuration refusee. Equipement precedent conserve.");
    gEngfuncs.Con_DPrintf("VFBuild received: result=%d hash=%u head=%d slots=21\n",result,hash,received[0]);
    gEngfuncs.Con_DPrintf("VF visuals: operator=%d weapon=%d\n",vf::OperatorBody(catalog,applied),vf::WeaponBody(catalog,applied));
    if(applied[9]>0&&!strncmp(catalog.items[applied[9]].id,"r01_",4))gEngfuncs.Con_DPrintf("VFR01 applied: receiver=%s power=%s chamber=%s optic=%s cooling=%s\n",catalog.items[applied[9]].id,catalog.items[applied[19]].id,catalog.items[applied[13]].id,catalog.items[applied[16]].id,catalog.items[applied[20]].id);
    if(referencePending!=-1){int v=referencePending;referencePending=-1;if(v!=-2||!IsReference())ApplyReference(v>=0?v:0);}
    if(platformPending>=0){int p=platformPending;platformPending=-1;ApplyPlatform(p);}
    return 1;
}

}

void VF_CharacterInit() {
    gEngfuncs.pfnAddCommand("vf_reference",ReferenceCommand);
    gEngfuncs.pfnAddCommand("vf_reference_platform",PlatformCommand);
    gEngfuncs.pfnAddCommand("vf_reference_style",StyleCommand);
    gEngfuncs.pfnAddCommand("vf_reference_isolate",ReferenceIsolate);
    vfui::Init();
    VF_EngineInit();
    VF_SkinsInit();
    VF_EffectsInit();
    VF_RangeInit();
    gEngfuncs.pfnAddCommand("vf_character",GameplayCommand);
    gEngfuncs.pfnAddCommand("vf_operator",GameplayCommand);
    gEngfuncs.pfnAddCommand("vf_item",ItemCommand);
    gEngfuncs.pfnAddCommand("vf_operator_set",OutfitCommand);
    gEngfuncs.pfnAddCommand("vf_next_item",Next);
    gEngfuncs.pfnAddCommand("vf_commit",Commit);
    gEngfuncs.pfnAddCommand("vf_tab",SwitchTab);
    gEngfuncs.pfnAddCommand("vf_revert",Restore);
    gEngfuncs.pfnAddCommand("vf_select_slot",SelectSlot);
    gEngfuncs.pfnAddCommand("vf_rotate",Rotate);
    gEngfuncs.pfnAddCommand("vf_model_info",InspectModel);
    gEngfuncs.pfnHookUserMsg("VFBuild",Message);
    VF_CharacterReset();
}
void VF_CharacterReset() { gameplaySaved=false;referencePending=-1;platformPending=-1;referenceIsolate=false; VF_EffectsReset(); vfui::Focus();opened=false;synchronized=false;pending=false;VF_PreviewReset();VF_SkinsReset();VF_EngineReset(); }
void VF_CharacterClose() {opened=false;vfui::Focus();}
void VF_CharacterShow(int page) {
    if(!opened) {
        if(catalog.valid&&synchronized&&!pending) {VF_SkinsClose();vfui::Focus();opened=true;gEngfuncs.GetViewAngles(fixedAngles);}
        else Toggle();
    }
    tab=page?1:0;row=0;familyFilter=-1;collectionFilter=-1;FocusSelection();
}
void VF_CharacterGameplay(int page){
 if(pending)return;
 bool fromDev=vfui::Developer(),restore=fromDev||!VF_EngineLinked();
 vfui::SetDeveloper(false);VF_CharacterShow(page);referenceIsolate=false;
 if(fromDev&&gameplaySaved&&synchronized){
  memcpy(draft,gameplayItems,sizeof(draft));memcpy(draftStyles,gameplayStyles,sizeof(draftStyles));Commit();
  gEngfuncs.Con_DPrintf("VFGameplay: restoring equipped loadout after developer trial\n");
 }
 if(restore||!synchronized){
  VF_EngineModuleReset();gEngfuncs.pfnClientCmd("vf_effect_clear\n");
  synchronized=false;requestTime=gEngfuncs.GetClientTime();gEngfuncs.pfnServerCmd("vf_gameplay\n");
 }
 VF_PreviewRotate((page?185.f:5.f)-VF_PreviewYaw());
}
void VF_CharacterReference(int variant){
 if(variant>5||(!vfui::Developer()&&variant>=0))return;
 if(vfui::Developer())VF_CharacterShow(1);else VF_CharacterGameplay(1);if(pending)return;
 if(synchronized){if(variant>=0||!IsReference())ApplyReference(variant>=0?variant:0);}
 else referencePending=variant<0?-2:variant;
}
void VF_CharacterUpdateModels() {
    cl_entity_t* view=gEngfuncs.GetViewModel();
    // The SDK precaches v_9mmAR.mdl; filesystem names are case-insensitive.
    if(view&&view->model&&!stricmp(view->model->name,"models/v_9mmar.mdl"))
        view->curstate.body=synchronized?vf::WeaponBody(catalog,applied):0;
    VF_EngineWeapon(view,synchronized?vf::WeaponBody(catalog,applied):0);
}
bool VF_CharacterOpen() { return opened||VF_SkinsOpen(); }
void VF_CharacterView(float* angles) { if(VF_SkinsOpen())VF_SkinsView(angles);else memcpy(angles,fixedAngles,sizeof(fixedAngles)); }
int VF_CharacterKey(int down,int key) {
    if(vfui::Key(down,key))return 0;
    if(VF_SkinsOpen())return VF_SkinsKey(down,key);
    if(!opened) return 1;
    // Let releases reach the engine, so opening while moving never leaves a held key.
    if(!down) return 1;
    if(key==K_F1&&vfui::Developer()){VF_CharacterGameplay(0);return 0;}
    if(key==K_ESCAPE||key==K_F1) { opened=false;return 0; }
    if(key==K_F2) {opened=false;return 1;}
    if(key==K_F11)return 1;
    if(key==K_F3||key==K_F6||key==K_F7||key==K_F9||key==K_F8||key==K_F10) return 1;
    if(key==K_TAB) { SwitchTab();return 0; }
    if(key=='q') VF_PreviewRotate(-10);
    else if(key=='e') VF_PreviewRotate(10);
    else if(key=='z') VF_PreviewZoom(.05f);
    else if(key=='x') VF_PreviewZoom(-.05f);
    else if(key=='t') VF_EngineAnimation(1);
    else if(key=='p') VF_EnginePause();
    else if(key==K_UPARROW) {row=(row+(tab?12:9)-1)%(tab?12:9);collectionFilter=-1;FocusSelection();}
    else if(key==K_DOWNARROW) {row=(row+1)%(tab?12:9);collectionFilter=-1;FocusSelection();}
    else if(key==K_RIGHTARROW||key==K_SPACE) Next();
    else if(key==K_LEFTARROW)CycleItem(-1);
    else if(key==K_ENTER) Commit();
    else if(key==K_BACKSPACE) Restore();
    return 0;
}

namespace {
void SelectDraft(int id){if(!synchronized||pending)return;draft[Slot()]=id;vf::BindWeaponStyles(catalog,weaponStyles,draft,draftStyles);gEngfuncs.Con_DPrintf("VFEquipment selection: slot=%d id=%s\n",Slot(),catalog.items[id].id);strcpy(status,Dirty()?"Configuration modifiee : appliquer pour valider.":"Configuration actuelle.");}
void DrawGameplay(){
 namespace u=vfui;
 const char* labels[]={"Tete","Epaules","Gants","Torse","Ceinture","Jambes","Bottes","Bouclier","Special","Chassis","Canon","Bouche","Chargeur","Culasse","Charge","Projectile","Optique","Sous-canon","Poignee","Batterie","Refroidissement"};
 const int icons[]={14,15,16,17,18,19,20,2,5,21,22,23,24,4,26,27,28,29,30,31,32};
 int slot=Slot(),start=tab?9:0,count=tab?12:9;
 u::Text(24,158,"EMPLACEMENTS",u::muted);
 for(int n=0;n<count;++n){int at=start+n;float y=188+n*34.f;
  if(u::Button(24,y,204,29,labels[at],row==n,true,icons[at])){row=n;slot=at;collectionFilter=-1;FocusSelection();}
  if(draft[at]!=applied[at])u::Box(215,y+10,4,9,u::amber);
  if(u::Hover(24,y,204,29))u::Tip(catalog.items[draft[at]].name);
 }
 u::Box(246,158,570,386,u::panel);
 bool ok=VF_EnginePreviewEquipment(draft,tab!=0,u::X(258),u::Y(166),546*u::SX(),344*u::SY(),draftStyles);
 if(!ok)u::Text(399,345,"Apercu indisponible",u::amber);
 u::Viewport(246,158,570,386);
 const vf::Item& item=catalog.items[draft[slot]];
 u::Wrap(250,556,item.name,558,u::white,2);
 u::Wrap(250,596,item.description,558,u::muted,2);
 // Collection changes filter the owned objects only; equipping always selects one row.
 u::Text(838,158,labels[slot],u::white,418);
 u::Text(838,184,"FILTRER PAR COLLECTION",u::muted);
 bool filtering=slot>=9||slot==0||slot==2||slot==3||slot==5||slot==6;
 if(filtering){
  if(u::Button(838,209,42,29,"<")){collectionFilter=(collectionFilter+weaponStyles.count+1)%(weaponStyles.count+1)-1;itemPage=0;}
  if(u::Button(887,209,320,29,collectionFilter<0?"Toutes les collections":weaponStyles.entries[collectionFilter].name,false)) {collectionFilter=-1;itemPage=0;}
  if(u::Button(1214,209,42,29,">")){collectionFilter=(collectionFilter+2)%(weaponStyles.count+1)-1;itemPage=0;}
 }else u::Text(838,215,"Tous les objets",u::muted);
 int matches[vf::MaxItems],visible=0;
 for(int i=1;i<catalog.count;++i)if(catalog.items[i].slot==slot&&vf::GameplayItem(catalog.items[i])&&(!filtering||CollectionMatch(catalog.items[i])))matches[visible++]=i;
 const int pageSize=6;int pages=(visible+pageSize-1)/pageSize;if(pages<1)pages=1;
 itemPage-=u::Scroll(834,245,426,354);if(itemPage<0)itemPage=0;if(itemPage>=pages)itemPage=pages-1;
 for(int n=0;n<pageSize&&itemPage*pageSize+n<visible;++n){int id=matches[itemPage*pageSize+n];const vf::Item& candidate=catalog.items[id];float y=249+n*56.f;
  if(u::Button(838,y,418,51,"",draft[slot]==id,synchronized&&!pending))SelectDraft(id);
  u::Wrap(850,y+6,candidate.name,365,u::white,2);
  if(applied[slot]==id)u::Text(1223,y+17,"*",u::teal,22);
 }
 if(!visible)u::Text(850,268,"Aucun objet dans cette collection",u::muted,394);
 if(u::Button(838,590,42,27,"<",false,itemPage>0))--itemPage;
 char page[100];snprintf(page,sizeof(page),"%d objets  /  Page %d sur %d",visible,itemPage+1,pages);u::Text(894,596,page,u::muted,304);
 if(u::Button(1214,590,42,27,">",false,itemPage+1<pages))++itemPage;
 if(slot==1||slot==4||slot==7||slot==8)if(u::Button(838,622,418,27,"Retirer cet equipement",draft[slot]==0,synchronized&&!pending&&draft[slot]!=0))SelectDraft(0);
 int totals[vf::BudgetCount],old[vf::BudgetCount];vf::Result result=vf::EvaluateGameplay(catalog,draft,totals);vf::Evaluate(catalog,applied,old);
 const char* budgetLabels[]={"Chaleur","Inertie","Stabilite","Integrite","Signature","Effort"};int first=tab?0:4,last=tab?4:6;
 for(int b=first;b<last;++b){float step=786.f/(last-first),x=24+(b-first)*step;u::Meter(x,635,step-22,budgetLabels[b],totals[b],old[b],catalog.limits[b],u::BudgetColor(b),34+b);if(u::Hover(x,635,step-22,30))u::Tip(u::BudgetTip(b));}
 u::Box(24,674,1232,1,u::edge);
 const char* note=result==vf::OverBudget?"Capacite depassee : choisir des objets moins couteux.":pending?"Enregistrement...":Dirty()?"Modifications en attente.":"Tous les objets sont disponibles.";
 if(!synchronized)note=status;
 u::Text(24,691,note,result==vf::OverBudget?u::red:u::muted,800);
 if(u::Button(902,684,148,28,"Annuler",false,Dirty()&&!pending))Restore();
 if(u::Button(1064,684,192,28,"Equiper",true,synchronized&&!pending&&Dirty()&&result==vf::Accepted))Commit();
}
void Preset(int kind){
 if(!synchronized||pending)return;
 int start=tab?vf::GearSlots:0,end=tab?vf::SlotCount:vf::GearSlots;
 for(int slot=start;slot<end;++slot){
  int best=0,score=-100000;
  for(int i=1;i<catalog.count;++i)if(catalog.items[i].slot==slot&&Eligible(catalog.items[i])){
   const vf::Item& it=catalog.items[i];int f=vfui::FamilyId(it.category),cost=0;for(int b=0;b<vf::BudgetCount;++b)cost+=it.cost[b];
   int value=kind==0?-cost:kind==1?((f==3?1000:f==0?500:0)-cost):((f==4||f==5?1000:0)+it.tier*100);
   if(value>score){score=value;best=i;}
  }draft[slot]=best;
 }
 strcpy(status,kind==2?"Prototype experimental : verifier les capacites avant application.":"Prototype charge. Verifier puis appliquer.");
}
}
void VF_CharacterDraw() {
 namespace u=vfui;
 if(VF_SkinsOpen()){VF_SkinsDraw();return;}
 if(!opened){u::Text(22,30,"[F1 / F2] OPERATEUR    [F11] ARME    [F6] OPTIONS DEVELOPPEUR",u::amber);return;}
 if((pending||!synchronized)&&catalog.valid&&gEngfuncs.GetClientTime()-requestTime>5){pending=false;synchronized=false;strcpy(status,"Connexion absente. Fermer et rouvrir l'atelier.");}
 u::Begin(tab?1:0);if(!opened)return;if(u::Guide()){u::End();return;}
 if(!u::Developer()){DrawGameplay();u::End();return;}
 int slot=Slot(),count=tab?12:9,start=tab?9:0;
 u::Text(24,160,tab?"SOUS-TYPES / ARME":"SOUS-TYPES / EQUIPEMENT",u::white,272);
 const char* compact[]={"Tete","Epaules","Gants","Torse","Ceinture","Jambes","Bottes","Bouclier","Special","Chassis","Canon","Bouche","Chargeur","Culasse","Charge","Projectile","Optique","Sous-canon","Poignee","Batterie","Refroidir"};
 const int slotIcons[]={14,15,16,17,18,19,20,2,5,21,22,23,24,4,26,27,28,29,30,31,32};
 for(int n=0;n<count;++n){int at=start+n;float x=24+(n%2)*140.f,y=199+(n/2)*(tab?51.f:58.f);
  if(u::Button(x,y,131,tab?44.f:49.f,compact[at],row==n,true,slotIcons[at])){row=n;familyFilter=-1;itemPage=0;slot=Slot();}
  int id=draft[at];int f=id>0&&id<catalog.count?u::FamilyId(catalog.items[id].category):-1;
  if(f>=0)u::Box(x+113,y+6,9,3,u::families[f].color);
  if(u::Hover(x,y,131,tab?44.f:49.f))u::Tip(vf::SlotNames[at]);
 }
 u::Text(24,509,"FAMILLES DE GAMEPLAY",u::muted);
 const char* presets[]={"Baseline","Predator","Fortress","Rogue","Engine","Anom."};
 for(int f=0;f<6;++f)if(u::Button(24+(f%3)*94.f,536+(f/3)*38.f,87,31,presets[f],false,synchronized&&!pending)){
  for(int s=start;s<start+count;++s){int best=0,score=999999;for(int i=1;i<catalog.count;++i){const vf::Item& it=catalog.items[i];if(it.slot!=s||!Eligible(it)||u::FamilyId(it.category)!=f)continue;int cost=0;for(int b=0;b<vf::BudgetCount;++b)cost+=it.cost[b];if(cost<score){best=i;score=cost;}}if(best||u::Developer())draft[s]=best;}
  strcpy(status,"Famille selectionnee : inspecter puis appliquer.");familyFilter=f;itemPage=0;
 }
 if(tab){
  const char* sets[]={"Atelier","Circuit","Nomade","Bastion"};
  for(int v=0;v<4;++v)if(u::Button(318+v*90.f,157,88,28,sets[v],false,synchronized&&!pending))VF_CharacterReference(v);
 }
 else if(!u::Developer()){
  const vf::Item& selected=catalog.items[draft[slot]];
  if(selected.appearance[0]){if(u::Button(318,157,320,28,"Equiper la tenue complete",false,synchronized&&!pending))Outfit(selected.appearance);}
  else u::Text(318,160,"OPERATEUR / BASE GIGN",u::muted);
 }else u::Text(318,160,"OPERATEUR / APERCU 3D",u::muted);
 u::Box(314,194,512,326,u::panel);
 for(int x=330;x<812;x+=32)u::Box((float)x,208,1,270,u::edge,30);
 int variants[3]={vf::Visual(catalog,draft,tab?12:0),vf::Visual(catalog,draft,tab?11:3),tab?0:vf::Visual(catalog,draft,5)};
 bool ref=tab&&IsReference();
 bool ok=ref&&referenceIsolate&&u::Developer()?VF_EnginePreviewReferencePart(draft,slot,u::X(330),u::Y(202),480*u::SX(),283*u::SY(),draftStyles):(ref||VF_EngineLinked())?VF_EnginePreviewEquipment(draft,tab!=0,u::X(330),u::Y(202),480*u::SX(),283*u::SY(),draftStyles):(tab?(VF_EngineModulesEquipped()?VF_PreviewModules(u::X(330),u::Y(202),480*u::SX(),283*u::SY()):VF_PreviewDraw(true,variants,u::X(330),u::Y(202),480*u::SX(),283*u::SY())):VF_SkinsPreview(u::X(330),u::Y(202),480*u::SX(),283*u::SY()));
 if(!ok)u::Text(400,345,"Apercu indisponible",u::amber);
 u::Viewport(314,194,512,326);
 if(ref){
  const char* themes[]={"Inventeur","Dieselpunk"};
  for(int t=0;t<2;++t){float x=600+t*114.f;
   if(u::Button(x,490,108,25,themes[t],false,synchronized&&!pending))VF_CharacterReference(t+4);
   if(u::Hover(x,490,108,25))u::Tip("Charger l ensemble complet avec ses quatre nouvelles pieces et sa finition.");
  }
 }

 if(u::Button(680,157,42,28,"<"))VF_PreviewRotate(-30);
 if(u::Button(728,157,42,28,">"))VF_PreviewRotate(30);
 if(u::Developer()&&u::Button(776,157,50,28,"",false,true,8))VF_SkinsShow(tab?2:0);
 const vf::Item& item=catalog.items[draft[slot]>=0&&draft[slot]<catalog.count?draft[slot]:0];
 u::Text(318,529,item.name,u::white,500);int family=u::FamilyId(item.category);u::Badge(family,318,557,158);u::Text(490,565,item.flavor,u::muted,330);
 if(u::Developer())u::Text(318,596,VF_EngineLinked()?(tab?"Visuel de l'objet / modules et accessoires":vf::EquipmentLookName(family)):"Apparence libre / changer les objets ne change pas le skin",u::teal,507);
 else {
  char cosmetic[160];const char* collection=tab&&weaponStyles.valid?weaponStyles.entries[draftStyles[slot-9]].name:item.flavor;
  snprintf(cosmetic,sizeof(cosmetic),"Collection cosmetique : %s",collection);u::Text(318,596,cosmetic,u::teal,507);
 }
 u::Text(850,160,vf::SlotNames[slot],u::white,ref&&slot==9?220:396);
 if(ref&&slot==9){
  const char* keys[]={"r01_receiver_arch","r01_receiver_gyre"};const char* labels[]={"Arche","Gyre"};
  for(int c=0;c<2;++c){int id=vf::FindItem(catalog,keys[c]);
   if(id>0&&u::Button(1080+c*90.f,157,86,28,labels[c],draft[9]==id,synchronized&&!pending)){SelectDraft(id);FocusSelection();referenceIsolate=false;}
  }
 }
 if(ref){
  int platform=vf::ReceiverMount(catalog.items[draft[9]]);
  const char* labels[]={"Dessous","Lateral","Dessus"};
  for(int p=0;p<3;++p)if(u::Button(850+p*137.f,194,132,31,labels[p],platform==p,synchronized&&!pending))ApplyPlatform(p);
 }
 else {if(u::Button(850,194,60,31,"Tous",familyFilter==-1)){familyFilter=-1;itemPage=0;}
 for(int f=0;f<6;++f){float x=916+f*56.f;if(u::Button(x,194,50,31,"",familyFilter==f,true)){familyFilter=f;itemPage=0;}
  u::Icon(f,x+15,201,18,u::families[f].color);if(u::Hover(x,194,50,31)){char help[240];snprintf(help,sizeof(help),"%s / %s. %s",u::families[f].name,u::families[f].role,u::families[f].summary);u::Tip(help);}
 }

 }
 int matches[vf::MaxItems],visible=0;
 for(int i=1;i<catalog.count;++i)if(catalog.items[i].slot==slot&&Eligible(catalog.items[i])&&(ref?!strncmp(catalog.items[i].id,"r01_",4):(slot==9||strncmp(catalog.items[i].id,"r01_",4)))&&(ref||familyFilter<0||u::FamilyId(catalog.items[i].category)==familyFilter))matches[visible++]=i;
 int pageSize=ref?2:4;int pages=(visible+pageSize-1)/pageSize;if(pages<1)pages=1;itemPage-=u::Scroll(842,231,414,260);if(itemPage<0)itemPage=0;if(itemPage>=pages)itemPage=pages-1;
 for(int n=0;n<pageSize&&itemPage*pageSize+n<visible;++n){int i=matches[itemPage*pageSize+n];const vf::Item& candidate=catalog.items[i];float y=240+n*54.f;int f=u::FamilyId(candidate.category);
  if(u::Button(850,y,406,47,"",draft[slot]==i,synchronized&&!pending))SelectDraft(i);
  u::Icon(f,863,y+10,24,f>=0?u::families[f].color:u::muted);u::Text(901,y+5,candidate.name,u::white,339);
  char info[100];snprintf(info,sizeof(info),"%s / T%d%s",candidate.category,candidate.tier,applied[slot]==i?" / ACTUEL":"");u::Text(901,y+26,info,u::muted,339);
 }
 if(ref&&weaponStyles.valid){
  u::Text(850,347,"FINITION",u::amber);
  int selected=draftStyles[slot-9];bool mixed=false;for(int s=1;s<vf::WeaponStyleSlots;++s)if(draftStyles[s]!=draftStyles[0])mixed=true;
  const char* label=styleWhole&&mixed?"Melange de finitions":weaponStyles.entries[selected].name;
  bool enabled=synchronized&&!pending;
  if(u::Button(850,370,42,31,"<",false,enabled))ChooseStyle((selected+weaponStyles.count-1)%weaponStyles.count,styleWhole?-1:slot);
  u::Text(902,378,label,u::white,300);
  if(u::Button(1214,370,42,31,">",false,enabled))ChooseStyle((selected+1)%weaponStyles.count,styleWhole?-1:slot);
  if(u::Button(850,411,198,29,"Toute l arme",styleWhole,enabled))styleWhole=true;
  if(u::Button(1058,411,198,29,"Cette piece",!styleWhole,enabled))styleWhole=false;
 }
 if(!visible)u::Text(862,259,"Aucun objet de cette famille",u::muted,365);
 if(u::Button(850,460,50,27,"<",false,itemPage>0))--itemPage;
 char pageText[70];snprintf(pageText,sizeof(pageText),"%d objets / %d sur %d",visible,itemPage+1,pages);u::Text(918,465,pageText,u::muted,262);
 if(u::Button(1206,460,50,27,">",false,itemPage+1<pages))++itemPage;
 if(u::Developer()||slot==1||slot==4||slot==7||slot==8){if(u::Button(850,494,406,26,"Emplacement libre",draft[slot]==0,synchronized&&!pending))SelectDraft(0);}
 u::Text(850,526,ref?"PIECE / COLLECTION":item.appearance[0]?"EQUIPEMENT / GIGN":"EQUIPEMENT / MODELE PROVISOIRE",u::amber);u::Wrap(850,551,item.description,406,u::white,2);
 if(ref&&u::Developer()&&u::Button(850,591,406,25,referenceIsolate?"Revenir a l arme complete":"Isoler cette piece en 3D",referenceIsolate))referenceIsolate=!referenceIsolate;
 int totals[vf::BudgetCount],old[vf::BudgetCount];vf::Result result=u::Developer()?vf::EvaluateExperiment(catalog,draft,totals):vf::EvaluateGameplay(catalog,draft,totals);vf::Evaluate(catalog,applied,old);
 u::Box(24,622,1232,1,u::edge);int first=tab?0:4,last=tab?4:6;
 for(int b=first;b<last;++b){float step=1232.f/(last-first),x=24+(b-first)*step;u::Meter(x,632,step-28,vf::BudgetCodes[b],totals[b],old[b],catalog.limits[b],u::BudgetColor(b),34+b);if(u::Hover(x,632,step-28,30))u::Tip(u::BudgetTip(b));}
 const char* note=result==vf::Incompatible?"Assemblage incomplet ou pieces incompatibles.":result==vf::OverBudget?"Capacite depassee : alleger la configuration.":pending?"Validation en cours...":status;
 u::Text(24,685,note,result==vf::OverBudget?u::red:Dirty()?u::amber:u::muted,854);
 if(u::Button(898,677,154,32,"Annuler",false,Dirty()&&!pending))Restore();
 if(u::Button(1064,677,192,32,pending?"Validation...":"Appliquer",true,synchronized&&!pending&&Dirty()&&result==vf::Accepted))Commit();
 u::End();
}
