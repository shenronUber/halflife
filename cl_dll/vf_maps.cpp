#include "hud.h"
#include "cl_util.h"
#include "keydefs.h"
#include "vf_maps.h"
#include "vf_character.h"
#include "vf_skinmenu.h"
#include "vf_ui.h"
#include <cstdio>
#include <cstring>
#include <cstdlib>
namespace {
struct Entry {char map[64],title[96],description[192],config[64];int variant;};
Entry entries[512];int count=0,selected=0,first=0;bool opened=false;float angles[3];
const int visible=8;
bool Identifier(const char* s){
 if(!*s||strlen(s)>60)return false;
 for(;*s;++s)if(!(*s>='a'&&*s<='z')&&!(*s>='0'&&*s<='9')&&*s!='_')return false;
 return true;
}
void Read(const char* path){
 int size=0;byte* data=gEngfuncs.COM_LoadFile((char*)path,5,&size);
 if(!data)return;
 // Catalog prose never becomes console text. Validate each bounded row.
 char line[512];int pos=0;
 while(pos<size&&count<512){int n=0;bool longRow=false;
  while(pos<size&&data[pos]!='\n'){if(n<511)line[n++]=data[pos];else longRow=true;++pos;}
  ++pos;line[n]=0;if(n&&line[n-1]=='\r')line[--n]=0;if(longRow||!n||line[0]=='#')continue;
  char* fields[5]={line};int parts=1;
  for(char* p=line;*p;++p)if(*p=='|'){if(parts==5){parts=6;break;}*p=0;fields[parts++]=p+1;}
  if(parts!=5||!Identifier(fields[0])||!Identifier(fields[4]))continue;
  char* end=NULL;long variant=strtol(fields[1],&end,10);
  if(!*fields[1]||*end||variant< -1||variant>7)continue;
  if(variant>=0&&strcmp(fields[0],"vf_tiles"))continue;
  Entry& e=entries[count++];snprintf(e.map,sizeof(e.map),"%s",fields[0]);e.variant=(int)variant;
  snprintf(e.title,sizeof(e.title),"%s",fields[2]);snprintf(e.description,sizeof(e.description),"%s",fields[3]);
  snprintf(e.config,sizeof(e.config),"%s",fields[4]);
 }
 gEngfuncs.COM_FreeFile(data);
}
void Load(){
 count=0;Read("vf/maps.txt");Read("vf/maps-extra.txt");
 if(selected>=count)selected=0;first=0;
 gEngfuncs.Con_DPrintf("VFMaps catalog: %d entries\n",count);
}
void Reveal(){if(selected<first)first=selected;if(selected>=first+visible)first=selected-visible+1;}
void Launch(){
 if(!count)return;const Entry& e=entries[selected];char command[256];
 snprintf(command,sizeof(command),"vf_tiles_variant %d\nvf_modular_seed %d\nmap %s\nexec %s.cfg\n",e.variant,e.variant<0?0:6,e.map,e.config);
 gEngfuncs.Con_DPrintf("VFMaps launch: map=%s variant=%d\n",e.map,e.variant);
 VF_MapsClose();gEngfuncs.pfnClientCmd(command);
}
void Toggle(){
 if(opened){VF_MapsClose();return;}
 VF_CharacterClose();VF_SkinsClose();vfui::Focus();Load();opened=true;Reveal();gEngfuncs.GetViewAngles(angles);
 gEngfuncs.pfnClientCmd("-attack\n-attack2\n-forward\n-back\n-moveleft\n-moveright\n-jump\n-duck\n");
}
}
void VF_MapsInit(){gEngfuncs.pfnAddCommand("vf_maps",Toggle);VF_MapsClose();}
void VF_MapsClose(){opened=false;vfui::Focus();}
bool VF_MapsOpen(){return opened;}
void VF_MapsView(float* out){memcpy(out,angles,sizeof(angles));}
int VF_MapsKey(int down,int key){
 if(!opened)return 1;
 if(key==K_MOUSE1||key==K_MOUSE2||key==K_MWHEELUP||key==K_MWHEELDOWN)return 1;
 if(!down)return 1;
 if(key==K_ESCAPE||key==K_F4){VF_MapsClose();return 0;}
 if(key==K_ENTER){Launch();return 0;}
 if(count){if(key==K_UPARROW)selected=(selected+count-1)%count;
  if(key==K_DOWNARROW)selected=(selected+1)%count;
  if(key==K_PGUP)selected=selected>visible?selected-visible:0;
  if(key==K_PGDN)selected=selected+visible<count?selected+visible:count-1;
  Reveal();}
 return 0;
}
void VF_MapsDraw(){
 if(!opened)return;namespace u=vfui;
 u::Box(0,0,1280,720,u::bg,250);u::Box(24,24,1232,4,u::teal);
 u::Text(48,52,"CARTES / VECTOR FIELDS",u::white);
 u::Text(48,86,"Choisir une carte ou une variante, puis lancer.",u::muted);
 if(u::Button(1160,47,72,38,"",false,true,10)){VF_MapsClose();return;}
 int wheel=u::Scroll(40,136,728,480);
 if(count&&wheel){selected=selected-wheel;if(selected<0)selected=0;if(selected>=count)selected=count-1;Reveal();}
 for(int i=0;i<visible&&first+i<count;++i){int at=first+i;
  if(u::Button(48,142+i*57.f,696,49,entries[at].title,at==selected))selected=at;
 }
 u::Box(776,142,456,454,u::panel);
 if(count){const Entry& e=entries[selected];u::Text(800,167,e.title,u::teal,402);
  u::Wrap(800,215,e.description,400,u::white,7);
  u::Text(800,412,"La carte sera rechargee.",u::amber,400);
  u::Text(800,446,"Choix de l'equipement conserve.",u::muted,400);
  if(u::Button(800,522,408,48,"Lancer la carte",true)){Launch();return;}
 }else u::Wrap(800,180,"Aucune carte disponible. Reparer le build pour restaurer le catalogue.",400,u::amber,4);
 char status[64];snprintf(status,sizeof(status),"%d / %d",count?selected+1:0,count);
 u::Text(48,620,status,u::teal);u::Text(200,620,"Molette / fleches : selection    Entree : lancer",u::muted,970);
 u::Text(48,671,"F4 : cartes    Echap : retour au jeu",u::white,1180);u::End();
}
