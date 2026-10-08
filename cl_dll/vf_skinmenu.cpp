#include "hud.h"
#include "cl_util.h"
#include "parsemsg.h"
#include "keydefs.h"
#include "vf_character.h"
#include "vf_preview.h"
#include "vf_engine.h"
#include "vf_skinmenu.h"
#include "vf_library.h"
#include "vf_ui.h"
#include "../game_shared/vf_appearance.h"
#include "../game_shared/vf_loadout.h"
#include <stdio.h>
#include <string.h>
namespace {
vf::AppearanceCatalog skins,arsenal;
int draft[5],applied[5],zone=0,tab=0,weapon=0,filter=0,moduleZone=0,libraryPage=0;
bool opened=false,synced=false,pending=false,isolate=false;
float angles[3],requested=0;
char status[160]="";
const char* prefixes[]={"","TFC / ","HL / ","OF / ","BS / ","VF / ","CS / ","GIGN / "};
void Load(const char* file,vf::AppearanceCatalog& c) {int n=0;byte* p=gEngfuncs.COM_LoadFile((char*)file,5,&n);vf::ParseAppearances((const char*)p,n>0?n:0,c);if(p)gEngfuncs.COM_FreeFile(p);}
bool Dirty(){return memcmp(draft,applied,sizeof(draft))!=0;}
void Toggle() {
 vfui::Focus();gEngfuncs.pfnClientCmd("-attack\n-attack2\n");
 if(opened){opened=false;return;}VF_CharacterClose();opened=true;gEngfuncs.GetViewAngles(angles);VF_SkinsRefresh();
}
bool Matches(int id){return !filter||!strncmp(skins.entries[id].name,prefixes[filter],strlen(prefixes[filter]));}
void Cycle(int step) {
 if(tab==2){if(VF_EngineLinked())return;VF_EngineModuleCycle(moduleZone,step);return;}
 if(tab){if(arsenal.valid){weapon=(weapon+step+arsenal.count*10)%arsenal.count;libraryPage=weapon/8;}return;}
 if(VF_EngineLinked()||!synced||pending)return;
 int id=draft[zone],direction=step>0?1:-1;
 for(int j=0;j<(step>0?step:-step);++j)for(int n=0;n<skins.count;++n){id=(id+direction+skins.count)%skins.count;if(Matches(id))break;}
 draft[zone]=id;strcpy(status,Dirty()?"Selection en attente - ENTREE pour l'appliquer au mannequin.":"Apparence actuelle.");
}
void Commit() {
 if(VF_EngineLinked()||!opened||tab||!synced||pending||!vf::ValidSkins(skins,draft))return;
 char cmd[160];snprintf(cmd,sizeof(cmd),"vf_skin_apply %u %d %d %d %d %d\n",skins.hash,draft[0],draft[1],draft[2],draft[3],draft[4]);
 pending=true;requested=gEngfuncs.GetClientTime();strcpy(status,"Validation de l'apparence...");gEngfuncs.pfnServerCmd(cmd);
}
void Restore(){if(!pending){memcpy(draft,applied,sizeof(draft));strcpy(status,"Apparence precedente restauree.");}}
void Tab(){if(opened){int count=VF_EngineModulesAvailable()?3:2;unsigned int id;if(gEngfuncs.Cmd_Argc()==2&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),id)&&id<(unsigned int)count)tab=id;else tab=(tab+1)%count;}}
void Filter(){unsigned int id;if(gEngfuncs.Cmd_Argc()==2&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),id)&&id<8){filter=id;libraryPage=0;}}
void Isolate(){if(opened&&!tab)isolate=!isolate;}
void Set(){
 if(VF_EngineLinked()||!opened||!synced||pending||gEngfuncs.Cmd_Argc()!=3)return;unsigned int z,id;
 if(vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),z)&&z<5&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(2),id)&&id<(unsigned int)skins.count){zone=z;draft[z]=id;}
}
void All(){
 if(VF_EngineLinked()||!opened||!synced||pending)return;unsigned int id=draft[zone];
 if(gEngfuncs.Cmd_Argc()==2&&!vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),id))return;
 if(id<(unsigned int)skins.count)for(int z=0;z<5;++z)draft[z]=id;
}
void Arsenal(){unsigned int id;if(gEngfuncs.Cmd_Argc()==2&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),id)&&id<(unsigned int)arsenal.count){tab=1;weapon=id;VF_LibraryLegacy(arsenal.entries[id].name);}}
void Audit(){
 int passed=0,failed=0;for(int c=0;c<2;++c){const vf::AppearanceCatalog& cat=c?arsenal:skins;for(int i=0;i<cat.count;++i){if(VF_PreviewValidateAsset(cat.entries[i].key))++passed;else{++failed;gEngfuncs.Con_Printf("VFSkin preview FAILED: %s\n",cat.entries[i].key);}}}
 gEngfuncs.Con_Printf("VFSkin preview audit: loaded=%d failed=%d\n",passed,failed);
}
int Message(const char*,int size,void* data) {
 if(size!=11)return 1;BEGIN_READ(data,size);int version=READ_BYTE(),result=READ_BYTE();unsigned int hash=(unsigned int)READ_LONG();int ids[5];for(int z=0;z<5;++z)ids[z]=READ_BYTE();
 pending=false;
 if(version!=1||!skins.valid||hash!=skins.hash||!vf::ValidSkins(skins,ids)){synced=false;strcpy(status,"Catalogue different : fermer puis rouvrir F2.");return 1;}
 memcpy(applied,ids,sizeof(ids));if(!synced||!result)memcpy(draft,ids,sizeof(ids));synced=true;
 strcpy(status,result?"Selection refusee. Le mannequin conserve son apparence.":"Apparence appliquee au mannequin. SIG/BIO et statistiques d'arme inchanges.");
 gEngfuncs.Con_DPrintf("VFSkin client: result=%d ids=%d,%d,%d,%d,%d\n",result,ids[0],ids[1],ids[2],ids[3],ids[4]);return 1;
}
}
void VF_SkinsInit(){
 VF_LibraryInit();
 gEngfuncs.pfnAddCommand("vf_skins",Toggle);gEngfuncs.pfnAddCommand("vf_skin_set",Set);gEngfuncs.pfnAddCommand("vf_skin_all",All);
 gEngfuncs.pfnAddCommand("vf_skin_commit",Commit);gEngfuncs.pfnAddCommand("vf_skin_tab",Tab);gEngfuncs.pfnAddCommand("vf_skin_isolate",Isolate);gEngfuncs.pfnAddCommand("vf_skin_filter",Filter);
 gEngfuncs.pfnAddCommand("vf_arsenal_select",Arsenal);gEngfuncs.pfnHookUserMsg("VFSkin",Message);VF_SkinsReset();
 gEngfuncs.pfnAddCommand("vf_skin_audit",Audit);
}
void VF_SkinsReset(){opened=synced=pending=false;skins.valid=arsenal.valid=false;memset(draft,0,sizeof(draft));memset(applied,0,sizeof(applied));}
void VF_SkinsRefresh(){Load("vf/skins.txt",skins);Load("vf/arsenal.txt",arsenal);synced=false;pending=false;requested=gEngfuncs.GetClientTime();strcpy(status,skins.valid?"Lecture de l'apparence...":"Catalogue de skins indisponible.");if(skins.valid)gEngfuncs.pfnServerCmd("vf_skin_request\n");}
void VF_SkinsClose(){opened=false;vfui::Focus();}
void VF_SkinsShow(int page){
 if(!opened){if(skins.valid&&synced&&!pending){VF_CharacterClose();vfui::Focus();opened=true;gEngfuncs.GetViewAngles(angles);}else Toggle();}
 tab=page>=0&&page<3?page:0;libraryPage=0;
}
bool VF_SkinsOpen(){return opened;}
void VF_SkinsView(float* out){memcpy(out,angles,sizeof(angles));}
bool VF_SkinsPreview(float x,float y,float w,float h){
 if(VF_EngineLinked())return VF_EnginePreviewCurrent(false,x,y,w,h);
 if(!skins.valid)return false;const char* keys[5];for(int z=0;z<5;++z){int id=opened?draft[z]:applied[z];if(id<0||id>=skins.count)return false;keys[z]=skins.entries[id].key;}
 return VF_PreviewSkins(keys,opened&&isolate?zone:-1,x,y,w,h);
}
int VF_SkinsKey(int down,int key){
 if(!opened||!down)return 1;
 if(tab==1&&VF_LibraryKey(key))return 0;
 if(key==K_ESCAPE||key==K_F2){opened=false;return 0;}
 if(key==K_F1){opened=false;return 1;}
 if(key==K_F3||key==K_F9||key==K_F8||key==K_F10||key==K_F11)return 1;
 if(key==K_TAB)Tab();else if(key=='q')VF_PreviewRotate(-10);else if(key=='e')VF_PreviewRotate(10);
 else if(key=='z')VF_PreviewZoom(.05f);else if(key=='x')VF_PreviewZoom(-.05f);else if(key=='i')Isolate();
 else if(key=='t')VF_EngineAnimation(1);else if(key=='p')VF_EnginePause();
 else if(key==K_UPARROW){if(tab==2)moduleZone=(moduleZone+3)%4;else if(tab)Cycle(-1);else zone=(zone+4)%5;}
 else if(key==K_DOWNARROW){if(tab==2)moduleZone=(moduleZone+1)%4;else if(tab)Cycle(1);else zone=(zone+1)%5;}
 else if(key==K_RIGHTARROW||key==K_SPACE)Cycle(1);else if(key==K_LEFTARROW)Cycle(-1);
 else if(key==K_PGUP)Cycle(-10);else if(key==K_PGDN)Cycle(10);
 else if(key=='g'&&!tab){filter=(filter+1)%8;if(synced&&!Matches(draft[zone]))Cycle(1);}
 else if(key=='a'&&!tab){if(!VF_EngineLinked()&&synced&&!pending&&!VF_EngineLinked())for(int z=0;z<5;++z)draft[z]=draft[zone];}
 else if(key==K_ENTER){if(tab==2)VF_EngineModuleEquip();else Commit();}else if(key==K_BACKSPACE){if(tab==2)VF_EngineModuleReset();else Restore();}return 0;
}

void VF_SkinsDraw(){
 namespace u=vfui;
 if(!opened)return;
 if((pending||!synced)&&skins.valid&&gEngfuncs.GetClientTime()-requested>5){pending=false;synced=false;strcpy(status,"Connexion absente. Fermer et rouvrir l'atelier.");}
 u::Begin(tab==0?2:tab==1?4:3);if(!opened)return;if(u::Guide()){u::End();return;}
 if(tab==1){VF_LibraryDraw();u::End();return;}
 const char* shortZones[]={"Tete / visage","Torse / bras","Mains / gants","Jambes","Chaussures"};
 const int zoneIcons[]={14,17,16,19,20}; const int moduleIcons[]={21,22,30,29};
 const char* moduleZones[]={"Corps","Canon","Crosse","Avant"};
 char text[192];
 u::Text(24,160,tab==0?"ZONES / PERSONNAGE":tab==2?"MODULES / ARME":"COLLECTION / TFC",u::white,275);
 if(tab!=1){int count=tab==0?5:4;
  for(int i=0;i<count;++i){float y=199+i*59.f;if(u::Button(24,y,272,50,tab==0?shortZones[i]:moduleZones[i],tab==0?zone==i:moduleZone==i,true,tab==0?zoneIcons[i]:moduleIcons[i])){if(tab==0)zone=i;else moduleZone=i;libraryPage=0;}}
  if(tab==0){
   if(u::Button(24,521,272,37,"Appliquer aux 5 zones",false,synced&&!pending&&!VF_EngineLinked()))for(int z=0;z<5;++z)draft[z]=draft[zone];
   if(u::Button(24,568,272,37,isolate?"Afficher le personnage":"Isoler cette zone",isolate))isolate=!isolate;
  }else{
   if(u::Button(24,432,272,28,"RELAIS R-01 / 24 PIECES")){VF_CharacterReference(0);u::End();return;}
   u::Text(24,467,"PROTOTYPES VISUELS",u::muted);
   const char* names[]={"MP40","Thompson","Hybride"};int parts[3][4]={{0,0,0,0},{2,2,2,2},{0,1,2,1}};
   for(int i=0;i<3;++i)if(u::Button(24+i*94.f,502,86,39,names[i],false,VF_EngineModulesAvailable()&&!VF_EngineLinked()))for(int z=0;z<4;++z)VF_EngineModuleSelect(z,parts[i][z]);
   u::Wrap(24,564,"4 modules / 81 assemblages. Apparence locale en premiere personne.",268,u::muted,3);
  }
 }else{
  u::Icon(7,44,218,100,u::amber);u::Text(24,356,"TEAM FORTRESS CLASSIC",u::white,272);
  snprintf(text,sizeof(text),"%d modeles disponibles",arsenal.count);u::Text(24,389,text,u::teal);
  u::Wrap(24,440,"Armes, projectiles et accessoires. Choisir un modele pour inspecter ses animations.",268,u::muted,4);
  u::Wrap(24,557,"Collection de reference. Les classes et regles TFC ne sont pas activees.",268,u::muted,3);
 }
 u::Text(318,160,tab==0?"APERCU / APPARENCE":tab==2?"ASSEMBLAGE / APERCU 3D":"MODELE / APERCU 3D",u::muted);
 u::Box(314,194,512,377,u::panel);for(int x=330;x<812;x+=32)u::Box((float)x,208,1,325,u::edge,30);
 bool ok=false;
 if(tab==0)ok=VF_SkinsPreview(u::X(326),u::Y(203),488*u::SX(),332*u::SY());
 else if(tab==2&&VF_EngineLinked())ok=VF_EnginePreviewCurrent(true,u::X(326),u::Y(203),488*u::SX(),332*u::SY());
 else if(tab==2)ok=VF_PreviewModules(u::X(326),u::Y(203),488*u::SX(),332*u::SY());
 else if(arsenal.valid)ok=VF_PreviewAsset(arsenal.entries[weapon].key,u::X(326),u::Y(203),488*u::SX(),332*u::SY());
 if(!ok)u::Text(401,356,"Apercu indisponible",u::amber);
 u::Viewport(314,194,512,377);
 if(u::Button(314,580,50,31,"<"))VF_PreviewRotate(-30);
 if(u::Button(371,580,50,31,">"))VF_PreviewRotate(30);
 if(u::Button(429,580,104,31,"Animation"))VF_EngineAnimation(1);
 if(u::Button(541,580,87,31,"Pause"))VF_EnginePause();
 u::Text(640,589,VF_EngineAnimationLabel(),u::muted,186);
 u::Text(850,160,tab==0?"APPARENCES COMPATIBLES":tab==2?moduleZones[moduleZone]:"BIBLIOTHEQUE",u::white,406);
 if(tab==0){
  const char* names[]={"Tous","TFC","HL","OF","BS","VF","CS","GIGN"};
  for(int f=0;f<8;++f)if(u::Button(850+(f%4)*103.f,185+(f/4)*28.f,97,25,names[f],filter==f)){filter=f;libraryPage=0;}
  int matches[256],count=0;for(int i=0;i<skins.count&&count<256;++i)if(Matches(i))matches[count++]=i;
  int pages=(count+5)/6;if(pages<1)pages=1;
  libraryPage-=u::Scroll(842,230,414,380);if(libraryPage<0)libraryPage=0;if(libraryPage>=pages)libraryPage=pages-1;
  for(int n=0;n<6&&libraryPage*6+n<count;++n){int id=matches[libraryPage*6+n];float y=250+n*53.f;
   if(u::Button(850,y,406,46,"",draft[zone]==id,synced&&!pending&&!VF_EngineLinked())){draft[zone]=id;strcpy(status,"Apparence modifiee : appliquer pour valider.");}
   u::Icon(6,863,y+10,25,id>=145?u::teal:u::muted);u::Text(904,y+15,skins.entries[id].name,u::white,333);
  }
  if(!count)u::Text(868,259,"Aucune apparence disponible",u::muted);
  if(u::Button(850,573,66,36,"<",false,libraryPage>0))--libraryPage;
  snprintf(text,sizeof(text),"%d / %d  -  %d skins",libraryPage+1,pages,count);u::Text(932,584,text,u::muted,225);
  if(u::Button(1190,573,66,36,">",false,libraryPage+1<pages))++libraryPage;
  if(skins.valid)u::Text(318,630,skins.entries[draft[zone]].name,u::white,500);
  u::Text(24,630,VF_EngineLinked()?"LIEE AUX OBJETS / lecture seule":"LIBRE / SIG et BIO inchanges",u::teal,280);
 }else if(tab==2){
  int count=VF_EngineModuleCount(moduleZone);
  for(int i=0;i<count;++i){float y=214+i*82.f;if(u::Button(850,y,406,70,"",VF_EngineModuleChoice(moduleZone)==i,!VF_EngineLinked()))VF_EngineModuleSelect(moduleZone,i);
   u::Icon(7,867,y+20,30,u::amber);u::Text(915,y+14,VF_EngineModuleOption(moduleZone,i),u::white,326);u::Text(915,y+42,i==0?"MP40 / Arsenal 1944":i==1?(moduleZone==2?"Atelier / Piece procedurale":"Nailgun / TFC"):"Thompson / Arsenal 1944",u::muted,326);
  }
  u::Text(850,491,"STYLE / SANS EFFET TECHNIQUE",u::teal);u::Wrap(850,525,"Les modules changent la silhouette. Le tir conserve le comportement du MP5.",406,u::white,3);
  u::Text(24,630,"Assembler > inspecter > equiper",u::amber);u::Text(850,610,"Prises en main a ajuster selon l'assemblage.",u::muted,406);
 }else{
  int pages=(arsenal.count+7)/8;if(pages<1)pages=1;libraryPage-=u::Scroll(842,195,414,414);if(libraryPage<0)libraryPage=0;if(libraryPage>=pages)libraryPage=pages-1;
  for(int n=0;n<8&&libraryPage*8+n<arsenal.count;++n){int id=libraryPage*8+n;float y=194+n*46.f;if(u::Button(850,y,406,39,arsenal.entries[id].name,weapon==id,true,7))weapon=id;}
  if(u::Button(850,573,66,36,"<",false,libraryPage>0))--libraryPage;
  snprintf(text,sizeof(text),"%d / %d",libraryPage+1,pages);u::Text(1003,584,text,u::muted);
  if(u::Button(1190,573,66,36,">",false,libraryPage+1<pages))++libraryPage;
  if(arsenal.valid)u::Text(318,630,arsenal.entries[weapon].name,u::white,500);
 }
 u::Box(24,660,1232,1,u::edge);
 const char* note=(tab!=1&&VF_EngineLinked())?"Visuel lie aux objets. Choisir Apparence libre en haut pour activer cet atelier.":tab==0?status:tab==2?(VF_EngineModulesEquipped()?"Assemblage equipe. Fermer l'atelier pour jouer.":"Selection en attente. Equiper pour voir l'arme en main."):"Bibliotheque d'inspection / aucun changement de l'equipement.";
 u::Text(24,685,note,tab==0&&Dirty()?u::amber:u::muted,853);
 if(tab==0){if(u::Button(898,677,154,32,"Annuler",false,Dirty()&&!pending))Restore();if(u::Button(1064,677,192,32,pending?"Validation...":"Appliquer",true,synced&&!pending&&!VF_EngineLinked()&&Dirty()))Commit();}
 else if(tab==2){if(u::Button(898,677,154,32,"Revenir au HK416",false,!VF_EngineLinked()))VF_EngineModuleReset();if(u::Button(1064,677,192,32,"Equiper",true,!VF_EngineLinked()&&VF_EngineModulesAvailable()&&!VF_EngineModulesEquipped()))VF_EngineModuleEquip();}
 u::End();
}
