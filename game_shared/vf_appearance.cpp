#include "vf_appearance.h"
#include "vf_loadout.h"
#include <string.h>
namespace vf {
bool ParseAppearances(const char* text,size_t size,AppearanceCatalog& c) {
 memset(&c,0,sizeof(c));if(!text||!size||size>65536)return false;c.hash=2166136261u;
 for(size_t i=0;i<size;++i)c.hash=(c.hash^(unsigned char)text[i])*16777619u;
 for(size_t p=0;p<size;) {
  char line[192];int n=0;
  while(p<size&&text[p]!='\n'){char ch=text[p++];if(ch=='\r')continue;if(ch<32||ch>126||n>=191)return false;line[n++]=ch;}
  if(p<size)++p;line[n]=0;if(!n)continue;
  char* f[6]={line,0,0,0,0,0};int nf=1;
  for(char* s=line;*s;++s)if(*s=='|'){if(nf==6)return false;*s=0;f[nf++]=s+1;}
  unsigned int id,anims=0,skin=0;
  if((nf!=3&&nf!=4&&nf!=6)||!ParseUnsigned(f[0],id)||id!=(unsigned int)c.count||id>=MaxAppearances)return false;
  if(nf>=4&&(!ParseUnsigned(f[3],anims)||anims>2048))return false;
  if(nf==6&&(!*f[4]||strlen(f[4])>=32||!ParseUnsigned(f[5],skin)||skin>31))return false;
  if(!*f[1]||strlen(f[1])>=32||!*f[2]||strlen(f[2])>=72)return false;
  for(char* s=f[1];*s;++s)if(!((*s>='a'&&*s<='z')||(*s>='0'&&*s<='9')||*s=='_'))return false;
  if(nf==6)for(char* s=f[4];*s;++s)if(!((*s>='a'&&*s<='z')||(*s>='0'&&*s<='9')||*s=='_'))return false;
  for(int i=0;i<c.count;++i)if(!strcmp(c.entries[i].key,f[1]))return false;
  Appearance& a=c.entries[c.count++];strcpy(a.key,f[1]);strcpy(a.name,f[2]);a.animations=anims;strcpy(a.model,nf==6?f[4]:f[1]);a.skin=skin;
 }
 c.valid=c.count>0;return c.valid;
}
bool ValidSkins(const AppearanceCatalog& c,const int skins[SkinZones]) {
 if(!c.valid)return false;for(int i=0;i<SkinZones;++i)if(skins[i]<0||skins[i]>=c.count)return false;return true;
}
bool ValidWeaponStyles(const AppearanceCatalog& c,const int* styles) {
 if(!c.valid||!styles||c.count>MaxWeaponStyles)return false;
 for(int i=0;i<c.count;++i)if(c.entries[i].skin!=i)return false;
 for(int i=0;i<WeaponStyleSlots;++i)if(styles[i]<0||styles[i]>=c.count)return false;
 return true;
}
int EquipmentFamily(const Catalog& c,const int* items,int slot) {
 if(!c.valid||!items||slot<0||slot>=SlotCount)return -1;
 int id=items[slot];if(id<=0||id>=c.count||c.items[id].slot!=slot)return -1;
 const char* families[]={"Baseline","Predator","Fortress","Rogue","Engine","Anomalous"};
 for(int f=0;f<6;++f)if(!strcmp(c.items[id].category,families[f]))return f;
 return -1;
}
const char* EquipmentLookName(int f){
 const char* names[]={"Bastion / Sable","Eclaireur / Sable","Bastion / Ardoise","Eclaireur / Ardoise","HEV / Cuivre","HEV / Ardoise"};
 return f>=0&&f<6?names[f]:"Sous-tenue / Eclaireur";
}
bool EquipmentSkins(const Catalog& c,const int* items,const AppearanceCatalog& skins,int* out){
 const char* keys[]={"style_bastion_3","style_eclaireur_3","style_bastion_1","style_eclaireur_1","style_hev_2","style_hev_1"};
 const int slots[]={0,3,2,5,6};
 if(!c.valid||!skins.valid||!items||!out)return false;int resolved[5];
 for(int z=0;z<5;++z){int f=EquipmentFamily(c,items,slots[z]);const char* key=f<0?"style_eclaireur_1":keys[f];int id=items[slots[z]];
  if(id>0&&id<c.count&&strstr(c.items[id].id,"_scout"))key="style_eclaireur_3";
  resolved[z]=-1;for(int i=0;i<skins.count;++i)if(!strcmp(skins.entries[i].key,key)){resolved[z]=i;break;}
  if(resolved[z]<0)return false;
 }memcpy(out,resolved,sizeof(resolved));return true;
}
int EquipmentModule(const Catalog& c,const int* items,int zone){
 const int slots[]={9,10,18,17};const int variants[6][4]={{0,0,0,0},{2,2,0,2},{1,1,2,1},{0,2,1,0},{1,0,1,1},{2,1,2,0}};
 if(zone<0||zone>3)return 0;int f=EquipmentFamily(c,items,slots[zone]);return f<0?0:variants[f][zone];
}

}
