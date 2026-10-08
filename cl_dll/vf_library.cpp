#include "hud.h"
#include "cl_util.h"
#include "keydefs.h"
#include "vf_library.h"
#include "vf_engine.h"
#include "vf_preview.h"
#include "vf_ui.h"
#include "vf_skinmenu.h"
#include "../game_shared/vf_engine_api.h"
#include "../game_shared/vf_loadout.h"
#include <algorithm>
#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include <vector>
#undef min
#undef max
struct VF_LibraryEntry {const char *key,*name,*collection,*model;int kind,playable,slot;};
#include "vf_library_data.h"
namespace {
const int count=sizeof(vfLibrary)/sizeof(vfLibrary[0]);
int selected=0,page=0,collection=0,type=1;bool searching=false;char query[64]="",status[160]="Choisir un modele pour inspecter ses animations.";
cvar_t* equipped=NULL; cvar_t* attachments[5]={};
const char* collections[]={"Tous","CS 1.6","CS HD","GameBanana","WW2","TFC","Source converti","Pieces","Cartes CS"};
const char* slots[]={"Optique","Bouche","Crosse","Poignee","Chargeur"};
bool Has(const char* s,const char* term){char a[240],b[64];snprintf(a,sizeof(a),"%s",s);snprintf(b,sizeof(b),"%s",term);for(char* p=a;*p;++p)*p=(char)tolower((unsigned char)*p);for(char* p=b;*p;++p)*p=(char)tolower((unsigned char)*p);return strstr(a,b)!=NULL;}
int Lookup(const char* key){if(!key||!*key)return -1;for(int i=0;i<count;++i)if(!strcmp(vfLibrary[i].key,key))return i;return -1;}
std::vector<int> Matches(){std::vector<int> ids;for(int i=0;i<count;++i){const auto& r=vfLibrary[i];if(collection&&strcmp(r.collection,collections[collection]))continue;if(type==1&&!r.playable)continue;if(type==2&&r.kind!=3)continue;if(*query&&!Has(r.name,query)&&!Has(r.collection,query))continue;ids.push_back(i);}return ids;}
void Select(int id){if(id<0||id>=count)return;selected=id;gEngfuncs.Con_DPrintf("VFLibrary selected: %d %s %s\n",id,vfLibrary[id].key,vfLibrary[id].name);}
void Action(){const auto& r=vfLibrary[selected];
 if(r.kind==4){char cmd[128];snprintf(cmd,sizeof(cmd),"exec vf_visit_%s.cfg\n",r.name);gEngfuncs.pfnClientCmd(cmd);VF_SkinsClose();return;}
 if(r.kind==3){gEngfuncs.Cvar_Set(equipped->name,"");gEngfuncs.Cvar_Set(attachments[r.slot]->name,(char*)r.key);gEngfuncs.Cvar_SetValue("vf_visual_enabled",1);VF_EngineSetAppearanceMode(1);snprintf(status,sizeof(status),"%s monte sur le prototype. Fermer F2 pour jouer.",slots[r.slot]);VF_SkinsShow(2);gEngfuncs.Con_Printf("VFLibrary attached: slot=%d key=%s\n",r.slot,r.key);return;}
 if(!r.playable)return;
 gEngfuncs.Cvar_Set(equipped->name,(char*)r.key);VF_EngineSetAppearanceMode(1);gEngfuncs.pfnClientCmd("weapon_9mmAR\n");snprintf(status,sizeof(status),"Modele equipe en mode libre. Tir du MP5 conserve.");gEngfuncs.Con_Printf("VFLibrary equipped: %s model=%s\n",r.key,r.model);
}
void Command(){if(gEngfuncs.Cmd_Argc()!=2)return;const char* arg=gEngfuncs.Cmd_Argv(1);unsigned int n;if(vf::ParseUnsigned(arg,n)&&n<(unsigned int)count)Select((int)n);else {int id=Lookup(arg);if(id>=0)Select(id);}VF_SkinsShow(1);}
void EquipCommand(){Action();}
void FindCommand(){snprintf(query,sizeof(query),"%.63s",gEngfuncs.Cmd_Argc()>1?gEngfuncs.Cmd_Argv(1):"");page=0;}
void FilterCommand(){if(gEngfuncs.Cmd_Argc()!=3)return;unsigned int a,b;if(vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),a)&&a<9&&vf::ParseUnsigned(gEngfuncs.Cmd_Argv(2),b)&&b<3){collection=a;type=b;page=0;}}
void ClearCommand(){VF_LibraryClearWeapon();for(int i=0;i<5;++i)gEngfuncs.Cvar_Set(attachments[i]->name,"");strcpy(status,"Choix de la bibliotheque retires.");}
void AuditCommand(){int start=0,end=count;if(gEngfuncs.Cmd_Argc()==3){unsigned int a,b;if(!vf::ParseUnsigned(gEngfuncs.Cmd_Argv(1),a)||!vf::ParseUnsigned(gEngfuncs.Cmd_Argv(2),b)||a>=b||b>(unsigned int)count)return;start=a;end=b;}int pass=0,fail=0;for(int i=start;i<end;++i){if(vfLibrary[i].kind==4)continue;if(VF_EngineValidateModel(vfLibrary[i].model))++pass;else{++fail;gEngfuncs.Con_Printf("VFLibrary FAILED: %d %s\n",i,vfLibrary[i].model);}}gEngfuncs.Con_Printf("VFLibrary audit: start=%d end=%d passed=%d failed=%d\n",start,end,pass,fail);}
}
void VF_LibraryInit(){equipped=gEngfuncs.pfnRegisterVariable("vf_library_weapon","",FCVAR_ARCHIVE);const char* names[]={"vf_library_optic","vf_library_muzzle","vf_library_stock","vf_library_grip","vf_library_mag"};for(int i=0;i<5;++i)attachments[i]=gEngfuncs.pfnRegisterVariable((char*)names[i],"",FCVAR_ARCHIVE);gEngfuncs.pfnAddCommand("vf_library_select",Command);gEngfuncs.pfnAddCommand("vf_library_equip",EquipCommand);gEngfuncs.pfnAddCommand("vf_library_find",FindCommand);gEngfuncs.pfnAddCommand("vf_library_filter",FilterCommand);gEngfuncs.pfnAddCommand("vf_library_clear",ClearCommand);gEngfuncs.pfnAddCommand("vf_library_audit",AuditCommand);}
const char* VF_LibraryWeaponPath(){int i=equipped?Lookup(equipped->string):-1;return i>=0&&vfLibrary[i].playable?vfLibrary[i].model:NULL;}
void VF_LibraryClearWeapon(){if(equipped)gEngfuncs.Cvar_Set(equipped->name,"");}
void VF_LibraryAccessories(vf_assembly_s& a){for(int slot=0;slot<5;++slot){int id=attachments[slot]?Lookup(attachments[slot]->string):-1;if(id<0||vfLibrary[id].kind!=3||vfLibrary[id].slot!=slot)continue;
 if(slot==2&&a.count>=4){for(int i=2;i+1<a.count;++i)a.parts[i]=a.parts[i+1];--a.count;}if(slot==4)a.body&=~2;
 if(a.count>=VF_MAX_PARTS)break;vf_part_t& p=a.parts[a.count++];memset(&p,0,sizeof(p));snprintf(p.model,sizeof(p.model),"models/vf_attach/%s.mdl",vfLibrary[id].key);p.mode=VF_PART_SOCKET;strcpy(p.bone,slot==4?"Bone71":"Bone76");}}
void VF_LibraryLegacy(const char* name){for(int i=0;i<count;++i)if(!strcmp(vfLibrary[i].collection,"TFC")&&!strcmp(vfLibrary[i].name,name)){Select(i);collection=5;type=0;page=0;break;}}
bool VF_LibraryKey(int key){if(!searching)return false;if(key==K_ENTER||key==K_ESCAPE){searching=false;return true;}size_t n=strlen(query);if(key==K_BACKSPACE&&n)query[n-1]=0;else if(key>=32&&key<=126&&n<sizeof(query)-1){query[n]=(char)key;query[n+1]=0;}page=0;return true;}
void VF_LibraryDraw(){namespace u=vfui;char text[256];const auto& r=vfLibrary[selected];u::Text(24,160,"COLLECTIONS / CONTENU",u::white,272);
 for(int c=0;c<9;++c){if(u::Button(24,194+c*37.f,272,32,collections[c],collection==c)){collection=c;page=0;type=c==7?2:c==8?0:1;if(c==5)type=0;auto ids=Matches();if(!ids.empty())Select(ids[0]);}}
 u::Text(24,546,"AFFICHER",u::muted);const char* types[]={"Tout","En main","Pieces"};for(int i=0;i<3;++i)if(u::Button(24+i*94.f,573,86,32,types[i],type==i)){type=i;page=0;auto ids=Matches();if(!ids.empty())Select(ids[0]);}
 u::Text(318,160,r.collection,u::muted,500);u::Box(314,194,512,377,u::panel);
 if(r.kind==4){u::Icon(9,504,258,100,u::teal);u::Wrap(360,384,"Carte Counter-Strike visitable. Les objectifs de match ne sont pas actifs.",420,u::white,3);}
 else{bool ok=VF_EnginePreviewModel(r.model,0,false,VF_PreviewYaw(),VF_PreviewZoomValue(),u::X(326),u::Y(203),488*u::SX(),332*u::SY());if(!ok)u::Text(391,356,"Modele indisponible",u::amber);u::Viewport(314,194,512,377);}
 if(u::Button(314,580,50,31,"<"))VF_PreviewRotate(-30);if(u::Button(371,580,50,31,">"))VF_PreviewRotate(30);if(u::Button(429,580,104,31,"Animation",false,r.kind!=4))VF_EngineAnimation(1);if(u::Button(541,580,87,31,"Pause",false,r.kind!=4))VF_EnginePause();u::Text(640,589,VF_EngineAnimationLabel(),u::muted,186);
 snprintf(text,sizeof(text),"%s%s",searching?"> ":"Rechercher : ",*query?query:"nom, arme, collection");if(u::Button(850,153,406,33,text,searching)){searching=!searching;}if(searching)u::Tip("Saisir un nom. Entree termine la recherche, retour arriere efface.");
 auto ids=Matches();int pages=std::max(1,((int)ids.size()+7)/8);page-=u::Scroll(842,194,414,377);page=std::max(0,std::min(page,pages-1));
 for(int n=0;n<8&&page*8+n<(int)ids.size();++n){int id=ids[page*8+n];float y=194+n*46.f;const auto& row=vfLibrary[id];if(u::Button(850,y,406,39,"",selected==id)){Select(id);}u::Icon(row.kind==3?22:row.kind==2?6:row.kind==4?9:7,859,y+8,24,row.playable?u::teal:u::muted);u::Text(894,y+12,row.name,u::white,354);if(u::Hover(850,y,406,39))u::Tip(row.name);}
 if(ids.empty())u::Text(866,230,"Aucun modele pour ce filtre.",u::muted);if(u::Button(850,573,66,36,"<",false,page>0))--page;snprintf(text,sizeof(text),"%d / %d  -  %d entrees",page+1,pages,(int)ids.size());u::Text(930,584,text,u::muted,240);if(u::Button(1190,573,66,36,">",false,page+1<pages))++page;
 u::Text(24,630,"CONTENU LOCAL / AUCUN BONUS",u::teal,280);u::Text(318,630,r.name,u::white,910);u::Box(24,660,1232,1,u::edge);
 const char* note=r.kind==3?"Montage sur le prototype MP40. Piece attachee a son os anime.":r.kind==4?"Visite de carte. Retour au laboratoire avec F4.":r.playable?"Essai visuel en main : animations adaptees, regles et munitions du MP5.":"Modele de reference : personnages, objets, projectiles et vues externes.";
 u::Wrap(24,678,note,790,u::muted,2);
 if(u::Button(838,677,166,32,r.kind==3?"Retirer la piece":"Retirer l'essai",false,r.kind==3||VF_LibraryWeaponPath()!=NULL)){if(r.kind==3)gEngfuncs.Cvar_Set(attachments[r.slot]->name,"");else VF_LibraryClearWeapon();}
 if(u::Button(1016,677,240,32,r.kind==3?"Monter / mode libre":r.kind==4?"Visiter la carte":"Essayer / mode libre",true,r.playable||r.kind==3||r.kind==4))Action();
}
