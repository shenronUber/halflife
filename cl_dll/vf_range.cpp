#include <cmath>
#include "hud.h"
#include "cl_util.h"
#include "cl_entity.h"
#include "parsemsg.h"
#include "triangleapi.h"
#include "vf_range.h"
#include "vf_death.h"
#include "vf_effects.h"
#include "vf_ui.h"
#include "entity_types.h"
#include "vf_character.h"
#include "../game_shared/vf_voice_catalog.h"
#include "../game_shared/vf_status_catalog.h"
#include "vf_effect_catalog.h"
#include <cstring>
#include <cstdio>
namespace {
namespace u=vfui;
struct Target {int entity,skin,actor,hp,maxhp;bool alive;float until[8];int hits[8];cl_entity_t halo;};
Target targets[4];
int Receive(const char*,int size,void* data){
 if(size!=35)return 1;BEGIN_READ(data,size);int protocol=READ_BYTE(),entity=READ_SHORT(),slot=READ_BYTE(),skin=READ_BYTE(),actor=READ_BYTE(),alive=READ_BYTE(),hp=READ_SHORT(),maxhp=READ_SHORT();
 if(protocol!=1||slot>=4||entity<1||entity>=2048||skin>=14||actor>=vfv::ActorCount||alive>1||hp<0||maxhp<1||hp>maxhp)return 1;
 int remaining[8],hits[8];for(int i=0;i<8;++i){remaining[i]=READ_SHORT();if(remaining[i]<0||remaining[i]>3000)return 1;}for(int i=0;i<8;++i){hits[i]=READ_BYTE();if(hits[i]>5)return 1;}
 Target& t=targets[slot];t.entity=entity;t.skin=skin;t.actor=actor;t.alive=alive!=0;t.hp=hp;t.maxhp=maxhp;
 for(int i=0;i<8;++i){t.until[i]=remaining[i]>0?gEngfuncs.GetClientTime()+remaining[i]*.01f:0;t.hits[i]=hits[i];}
 gEngfuncs.Con_DPrintf("VFRange received target=%d entity=%d skin=%d actor=%s alive=%d\n",slot,entity,skin,vfv::Actors[actor].id,alive);return 1;
}
int Voice(const char*,int size,void* data){
 if(size!=4)return 1;BEGIN_READ(data,size);int entity=READ_SHORT(),actor=READ_BYTE(),clip=READ_BYTE();if(entity<1||entity>=2048||actor>=vfv::ActorCount||clip>=vfv::ClipCount||vfv::Clips[clip].actor!=actor)return 1;
 gEngfuncs.Con_DPrintf("VFRange voice received entity=%d actor=%s event=%s\n",entity,vfv::Actors[actor].id,vfv::Events[vfv::Clips[clip].event]);
 if(vfv::Clips[clip].event==vfv::E_death)return 1;
 cvar_t* subtitles=gEngfuncs.pfnGetCvarPointer("vf_voice_subtitles");if(subtitles&&subtitles->value>=2){char text[256];snprintf(text,sizeof(text),"%s: %s\n",vfv::Actors[actor].name,vfv::Clips[clip].text);gHUD.m_SayText.SayTextPrint(text,strlen(text),0);}return 1;
}
bool Current(const Target& t,cl_entity_t*& e){e=gEngfuncs.GetEntityByIndex(t.entity);cl_entity_t* viewer=gEngfuncs.GetLocalPlayer();return t.entity>0&&t.alive&&e&&e->model&&viewer&&e->curstate.messagenum==viewer->curstate.messagenum;}
void Stats(){for(int t=0;t<4;++t)if(targets[t].entity){Target& a=targets[t];gEngfuncs.Con_Printf("VFRange client target=%d entity=%d skin=%d health=%d alive=%d\n",t,a.entity,a.skin,a.hp,a.alive);for(int i=0;i<8;++i)gEngfuncs.Con_Printf("VFRange client effect target=%d id=%s hits=%d active=%d\n",t,vfs::effects[i].id,a.hits[i],a.until[i]>gEngfuncs.GetClientTime());}}
}
void VF_RangeInit(){VF_DeathInit();gEngfuncs.pfnHookUserMsg("VFTarget",Receive);gEngfuncs.pfnHookUserMsg("VFRangeVoice",Voice);gEngfuncs.pfnAddCommand("vf_range_client",Stats);VF_RangeReset();}
void VF_RangeReset(){VF_DeathReset();memset(targets,0,sizeof(targets));}
int VF_RangeSkin(int entity){for(int t=0;t<4;++t)if(targets[t].entity==entity)return targets[t].skin;return -1;}
void VF_RangeEntities(){for(int t=0;t<4;++t){Target& a=targets[t];cl_entity_t* e; if(!Current(a,e))continue;for(int i=0;i<8;++i)if(a.until[i]>gEngfuncs.GetClientTime()){
 a.halo=*e;a.halo.curstate.rendermode=kRenderTransAdd;a.halo.curstate.renderfx=kRenderFxGlowShell;a.halo.curstate.renderamt=5;a.halo.curstate.rendercolor.r=vfx::effects[i].color[0];a.halo.curstate.rendercolor.g=vfx::effects[i].color[1];a.halo.curstate.rendercolor.b=vfx::effects[i].color[2];gEngfuncs.CL_CreateVisibleEntity(ET_NORMAL,&a.halo);break;
}}}
void VF_RangeWorld(){for(int t=0;t<4;++t){Target& a=targets[t];cl_entity_t* e;if(!Current(a,e))continue;for(int i=0;i<8;++i)if(a.until[i]>gEngfuncs.GetClientTime())VF_EffectsTargetDraw(i,e->origin);}}
void VF_RangeHud(){
 if(VF_CharacterOpen())return;
 for(int t=0;t<4;++t){Target& a=targets[t];cl_entity_t* e;if(!Current(a,e))continue;
  float point[3]={e->origin[0],e->origin[1],e->origin[2]+48},screen[3];if(gEngfuncs.pTriAPI->WorldToScreen(point,screen)||fabsf(screen[0])>.9f||fabsf(screen[1])>.9f)continue;
  float x=((screen[0]+1)*ScreenWidth*.5f-u::X(0))/u::SX()-92,y=((1-screen[1])*ScreenHeight*.5f-u::Y(0))/u::SY();
  u::Box(x,y,184,56,u::bg,190);char line[100];snprintf(line,sizeof(line),"GIGN %d / %s",t+1,vfv::Actors[a.actor].name);u::Text(x+7,y+6,line,u::white,175);
  int element=-1;for(int i=0;i<8;++i)if(a.until[i]>gEngfuncs.GetClientTime()){element=i;break;}if(element<0)for(int i=0;i<8;++i)if(a.hits[i]>0&&(element<0||a.hits[i]>a.hits[element]))element=i;
  if(element>=0){if(a.until[element]>gEngfuncs.GetClientTime())snprintf(line,sizeof(line),"%s / %.1fs",vfs::effects[element].id,a.until[element]-gEngfuncs.GetClientTime());
   if(a.until[element]<=gEngfuncs.GetClientTime())snprintf(line,sizeof(line),"%s / %d sur 6",vfs::effects[element].id,a.hits[element]);u::Text(x+7,y+25,line,u::teal,175);
  }else u::Text(x+7,y+25,"6 impacts / 3 secondes",u::muted,175);
  u::Box(x+7,y+46,170,3,u::muted,90);u::Box(x+7,y+46,170*a.hp/a.maxhp,3,u::teal,210);
 }
}
