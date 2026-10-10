#include <cmath>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <chrono>
#include <algorithm>
#include "vf_effect_math.h"
#include "vf_status_feedback.h"
#include "vf_engine.h"
#include "hud.h"
#include "cl_util.h"
#include "cl_entity.h"
#include "entity_types.h"
#include "com_model.h"
#include "triangleapi.h"
#include "pmtrace.h"
#include "pm_defs.h"
#include "event_api.h"
#include "vf_effects.h"
#include "vf_death.h"
#include "vf_range.h"
#include "vf_weapon_fx.h"
#include "vf_character.h"
#include "vf_skinmenu.h"
#include "vf_preview.h"
#include "vf_ui.h"
#include "parsemsg.h"
#include "../game_shared/vf_status_catalog.h"
#include "../game_shared/vf_voice_catalog.h"
extern "C" { int CL_IsThirdPerson(void); }
#undef min
#undef max
namespace {
bool deathLab=false;
using vfx::V;namespace u=vfui;
const char* textures[]={"bubble.spr","hotglow.spr","steam1.spr","fire.spr","white.spr"};
HSPRITE sprites[5]={};
HSPRITE statusDecals[vfdecal::Count]={};
int selected=0,filter=0;bool matrix=false,halo=true,particles=true,paused=false;float pauseAt=0,epoch=0;
struct Emitter {int effect,entity;V center;float yaw;cl_entity_t model;};
Emitter emitters[3]={};int emitterCount=0;model_s* mannequin=NULL;int mannequinIndex=0;
int generated=0,visibleModels=0;unsigned int frames=0;double totalMs=0;
int bench=-1;double benchTimes[180],benchFrames[180];std::chrono::steady_clock::time_point previous;
struct PlayerStatus {float until[vfs::Count],started[vfs::Count],duration[vfs::Count];unsigned int order[vfs::Count];bool developer;cl_entity_t model;};
PlayerStatus playerStatus[33]={};unsigned int statusOrder=0;bool testPlayer=false;float testSeconds=6;
static_assert(vfs::Count==vfx::Count,"Client/server effect catalogs must match");
int LocalIndex(){cl_entity_t* p=gEngfuncs.GetLocalPlayer();return p&&p->index>=1&&p->index<=32?p->index:0;}
bool StatusActive(int player,int id){return playerStatus[player].until[id]>gEngfuncs.GetClientTime();}
int ReceiveStatus(const char*,int size,void* data){
 if(size!=2+vfs::Count*2)return 1;BEGIN_READ(data,size);int player=READ_BYTE(),dev=READ_BYTE();
 if(player<1||player>32||player>gEngfuncs.GetMaxClients()||dev>1)return 1;
 int remaining[vfs::Count];for(int i=0;i<vfs::Count;++i){remaining[i]=READ_SHORT();if(remaining[i]<0||remaining[i]>3000)return 1;}
 float now=gEngfuncs.GetClientTime();int active=0;
 for(int i=0;i<vfs::Count;++i){
  if(remaining[i]>0){if(!StatusActive(player,i)){playerStatus[player].started[i]=now;playerStatus[player].duration[i]=remaining[i]*.01f;playerStatus[player].order[i]=++statusOrder;}
   else playerStatus[player].duration[i]=std::max(playerStatus[player].duration[i],remaining[i]*.01f);++active;}
  else playerStatus[player].started[i]=playerStatus[player].duration[i]=0;
  playerStatus[player].until[i]=remaining[i]>0?now+remaining[i]*.01f:0;
 }
 playerStatus[player].developer=dev!=0;gEngfuncs.Con_DPrintf("VFStatus received: player=%d developer=%d active=%d\n",player,dev,active);return 1;
}
void PlayerStats(){for(int p=1;p<=gEngfuncs.GetMaxClients()&&p<=32;++p){
 gEngfuncs.Con_DPrintf("VFStatus client: player=%d developer=%d\n",p,playerStatus[p].developer);
 for(int i=0;i<vfs::Count;++i)if(StatusActive(p,i))gEngfuncs.Con_DPrintf("VFStatus client active: player=%d effect=%s remaining=%.2f\n",p,vfs::effects[i].id,playerStatus[p].until[i]-gEngfuncs.GetClientTime());
}}
char status[160]="Choisir un effet, puis le faire apparaitre dans la salle.";
float Time(){return paused?pauseAt:gEngfuncs.GetClientTime()-epoch;}
u::Color Color(int id){return u::Color{vfx::effects[id].color[0],vfx::effects[id].color[1],vfx::effects[id].color[2]};}
bool Bind(int tex,float t){
 if(tex<0||tex>=5)return false;
 if(!sprites[tex]){char path[96];snprintf(path,sizeof(path),"sprites/vf_effects/%s",textures[tex]);sprites[tex]=gEngfuncs.pfnSPR_Load(path);}
 if(!sprites[tex])return false;int count=gEngfuncs.pfnSPR_Frames(sprites[tex]);
 return count>0&&gEngfuncs.pTriAPI->SpriteTexture(const_cast<model_s*>(gEngfuncs.GetSpritePointer(sprites[tex])),int(fabsf(t)*10)%count)!=0;
}
V Cross(V a,V b){return V(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);}
V Normal(V a){float d=sqrtf(a.x*a.x+a.y*a.y+a.z*a.z);return d>.001f?a*(1/d):V(1,0,0);}
V Rotate(V a,float yaw){float c=cosf(yaw),s=sinf(yaw);return V(a.x*c-a.y*s,a.x*s+a.y*c,a.z);}
void Quad(V a,V b,V c,V d){triangleapi_t* p=gEngfuncs.pTriAPI;p->TexCoord2f(0,0);p->Vertex3f(a.x,a.y,a.z);p->TexCoord2f(1,0);p->Vertex3f(b.x,b.y,b.z);p->TexCoord2f(1,1);p->Vertex3f(c.x,c.y,c.z);p->TexCoord2f(0,1);p->Vertex3f(d.x,d.y,d.z);}
int Draw(int id,V center,V right,V up,float scale,bool screen){
 if(!particles||id<0||id>=vfx::Count)return 0;
 triangleapi_t* api=gEngfuncs.pTriAPI;int total=0;const vfx::Effect& e=vfx::effects[id];
 api->CullFace(TRI_NONE);api->RenderMode(kRenderTransAdd);
 for(int k=0;k<e.layerCount;++k){const vfx::Layer& layer=e.layers[k];vfx::Primitive p[512];int n=vfx::Generate(layer,Time(),p,512);
  if(!Bind(layer.texture,Time()))continue;api->Begin(TRI_QUADS);
  for(int i=0;i<n;++i){V a=p[i].a,b=p[i].b;
   if(screen){a=Rotate(a,VF_PreviewYaw()*.01745329252f);b=Rotate(b,VF_PreviewYaw()*.01745329252f);a=V(a.x,-a.z+a.y*.17f,0);b=V(b.x,-b.z+b.y*.17f,0);}
   a=center+a*scale;b=center+b*scale;float size=p[i].size*scale;
   api->Color4f(layer.r,layer.g,layer.b,p[i].alpha);
   if(p[i].line){V normal=Normal(Cross(b-a,Cross(right,up)))*size;Quad(a-normal,a+normal,b+normal,b-normal);}
   else if(layer.pattern==vfx::Shards){V x=right*size,z=up*size*2;Quad(a-z,a+x,a+z,a-x);}
   else{V x=right*size,y=up*size;Quad(a-x-y,a+x-y,a+x+y,a-x+y);}
  }api->End();total+=n;
 }
 api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);return total;
}
void Select(int id){if(id<0||id>=vfx::Count)return;selected=id;filter=vfx::effects[id].kind;epoch=gEngfuncs.GetClientTime();pauseAt=0;snprintf(status,sizeof(status),"%s / demonstration visuelle",vfx::effects[id].name);gEngfuncs.Con_DPrintf("VFX select: %s\n",vfx::effects[id].id);}
void Clear(){emitterCount=0;visibleModels=generated=0;snprintf(status,sizeof(status),"Effets retires de la salle.");gEngfuncs.Con_DPrintf("VFX clear: active=0\n");}
void Close(){VF_CharacterClose();VF_SkinsClose();}
void Spawn(bool compare){
 cl_entity_t* player=gEngfuncs.GetLocalPlayer();if(!player)return;
 float angles[3];gEngfuncs.GetViewAngles(angles);float yaw=angles[1]*.01745329252f;V forward(cosf(yaw),sinf(yaw),0),right(-sinf(yaw),cosf(yaw),0);
 const vfx::Effect& e=vfx::effects[selected];bool triple=compare&&e.kind==1;int ids[3]={selected,selected,selected};if(triple){ids[0]=e.parentA;ids[1]=selected;ids[2]=e.parentB;}
 Emitter proposed[3]={};int count=triple?3:1;
 for(int i=0;i<count;++i){V start(player->origin[0],player->origin[1],player->origin[2]+16);V end=start+forward*(triple?205.f:145.f)+right*(triple?(1-i)*85.f:0);
  float from[3]={start.x,start.y,start.z},to[3]={end.x,end.y,end.z};pmtrace_t* tr=gEngfuncs.PM_TraceLine(from,to,PM_TRACELINE_PHYSENTSONLY,2,-1);
  if(!tr||tr->startsolid||tr->fraction<.92f){strcpy(status,"Place insuffisante : viser une zone libre dans la salle.");gEngfuncs.Con_DPrintf("VFX spawn rejected: obstructed\n");return;}
  float down[3]={end.x,end.y,end.z-200};tr=gEngfuncs.PM_TraceLine(to,down,PM_TRACELINE_PHYSENTSONLY,2,-1);
  if(!tr||tr->startsolid||tr->fraction>=1||tr->plane.normal[2]<.65f){strcpy(status,"Aucun sol stable : choisir un autre emplacement.");return;}
  proposed[i].center=V(tr->endpos[0],tr->endpos[1],tr->endpos[2]+36);proposed[i].effect=ids[i];proposed[i].yaw=angles[1]+180;
 }
 memcpy(emitters,proposed,sizeof(emitters));emitterCount=count;Close();
 gEngfuncs.Con_DPrintf("VFX spawn: %s active=%d visual_only=1\n",e.id,emitterCount);
}
void Attach(){
 cl_entity_t* player=gEngfuncs.GetLocalPlayer();if(!player)return;
 float angles[3],forward[3],right[3],up[3];gEngfuncs.GetViewAngles(angles);gEngfuncs.pfnAngleVectors(angles,forward,right,up);
 float start[3]={player->origin[0],player->origin[1],player->origin[2]+28},end[3];for(int i=0;i<3;++i)end[i]=start[i]+forward[i]*512;
 pmtrace_t* tr=gEngfuncs.PM_TraceLine(start,end,PM_TRACELINE_PHYSENTSONLY,2,-1);int id=tr?gEngfuncs.pEventAPI->EV_IndexFromTrace(tr):0;
 cl_entity_t* target=id>0?gEngfuncs.GetEntityByIndex(id):NULL;
 if(!target||!target->model||target->model->type!=mod_studio){strcpy(status,"Viser un personnage ou un mannequin de la salle.");gEngfuncs.Con_DPrintf("VFX attach rejected: no studio target\n");return;}
 memset(emitters,0,sizeof(emitters));emitters[0].entity=id;emitters[0].effect=selected;emitterCount=1;Close();gEngfuncs.Con_DPrintf("VFX attach: entity=%d effect=%s\n",id,vfx::effects[selected].id);
}
void Next(){Select((selected+1)%vfx::Count);for(int i=0;i<emitterCount;++i)emitters[i].effect=selected;}
void Prev(){Select((selected+vfx::Count-1)%vfx::Count);for(int i=0;i<emitterCount;++i)emitters[i].effect=selected;}
void OpenTest();
void Open(){u::SetDeveloper(true);VF_CharacterShow(0);u::OpenEffects();gEngfuncs.pfnClientCmd("-attack\n-attack2\n");}
void OpenTest(){testPlayer=true;matrix=false;Open();}
void ChooseCommand(){if(gEngfuncs.Cmd_Argc()!=2)return;for(int i=0;i<vfx::Count;++i)if(!strcmp(gEngfuncs.Cmd_Argv(1),vfx::effects[i].id)){Select(i);return;}gEngfuncs.Con_DPrintf("VFX rejected: unknown effect\n");}
void SpawnCommand(){Spawn(gEngfuncs.Cmd_Argc()>1&&!strcmp(gEngfuncs.Cmd_Argv(1),"compare"));}
void Audit(){int loaded=0;for(int i=0;i<5;++i)if(Bind(i,0))++loaded;gEngfuncs.Con_DPrintf("VFX audit: effects=%d sprites=%d/5 active=%d\n",vfx::Count,loaded,emitterCount);}
void Stats(){gEngfuncs.Con_DPrintf("VFX stats: active=%d visible=%d primitives=%d frames=%u mean_ms=%.4f halo=%d particles=%d\n",emitterCount,visibleModels,generated,frames,frames?totalMs/frames:0,halo,particles);}
void Bench(){bench=0;previous=std::chrono::steady_clock::now();}
void LayersCommand(){if(gEngfuncs.Cmd_Argc()!=3)return;halo=atoi(gEngfuncs.Cmd_Argv(1))!=0;particles=atoi(gEngfuncs.Cmd_Argv(2))!=0;}
void Icon(int id,float x,float y,float size){
 u::Color c=Color(id);int icons[]={26,3,36,34,39,26,36,35};const vfx::Effect& e=vfx::effects[id];
 if(e.kind==0)u::Icon(icons[id],x,y,size,c);
 else if(e.kind==1){u::Icon(icons[e.parentA],x,y,size*.64f,Color(e.parentA));u::Icon(icons[e.parentB],x+size*.42f,y+size*.38f,size*.6f,Color(e.parentB));}
 else u::Icon(id==16?5:id==17?37:id==18?2:id==19?38:31,x,y,size,c);
}
void TestPanel(){
 const vfx::Effect& e=vfx::effects[selected];int local=LocalIndex();bool enabled=local&&playerStatus[local].developer;
 u::Box(728,231,528,417,u::panel);u::Text(747,246,"TEST JOUEUR / EFFETS ET VOIX",u::white,490);
 if(u::Button(747,277,489,34,enabled?"Mode developpeur : ACTIF":"Activer le test developpeur",enabled))gEngfuncs.pfnServerCmd(enabled?"vf_status_dev 0\n":"vf_status_dev 1\n");
 u::Text(747,323,"Duree",u::muted);const float durations[]={6,12,30};for(int i=0;i<3;++i){char label[24];snprintf(label,sizeof(label),"%g sec",durations[i]);if(u::Button(835+i*134.f,317,126,30,label,testSeconds==durations[i]))testSeconds=durations[i];}
 char label[128];snprintf(label,sizeof(label),"Sur moi : %s",e.name);
 if(u::Button(747,358,489,37,label,true,enabled)){char command[128];snprintf(command,sizeof(command),"vf_status_apply %s %g\n",e.id,testSeconds);gEngfuncs.pfnServerCmd(command);Close();}
 if(e.kind==1){snprintf(label,sizeof(label),"Combiner %s + %s",vfx::effects[e.parentA].id,vfx::effects[e.parentB].id);
  if(u::Button(747,402,489,32,label,false,enabled)){char command[128];snprintf(command,sizeof(command),"vf_status_pair %s %s %g\n",vfx::effects[e.parentA].id,vfx::effects[e.parentB].id,testSeconds);gEngfuncs.pfnServerCmd(command);Close();}}
 else u::Text(747,411,"Deux vecteurs compatibles forment leur reaction.",u::muted,489);
 u::Text(747,450,"PERSONNAGE / VOIX",u::teal);float actorWidth=489.f/vfv::ActorCount;
 for(int i=0;i<vfv::ActorCount;++i)if(u::Button(747+i*actorWidth,474,actorWidth-5,30,vfv::Actors[i].id,false,enabled)){char command[80];snprintf(command,sizeof(command),"vf_voice_set %s\n",vfv::Actors[i].id);gEngfuncs.pfnServerCmd(command);}
 u::Text(747,519,"ACTIONS / DEGATS REELS",u::teal);
 const char* actions[]={"pain","armor","critical","burn","death","gib"};const char* names[]={"Blessure","Armure brisee","Sante critique","Brulure","Mort","Mort explosive"};
 for(int i=0;i<6;++i)if(u::Button(747+(i%3)*166.f,545+(i/3)*43.f,157,34,names[i],false,enabled)){char command[80];snprintf(command,sizeof(command),"vf_voice_test %s\n",actions[i]);gEngfuncs.pfnServerCmd(command);Close();}
 u::Text(25,653,enabled?"Etat serveur + visuel partage + replique contextuelle. Rafraichir un etat actif ne rejoue pas la voix.":"Activation reservee au solo ou aux serveurs sv_cheats 1. Choisir un effet a gauche.",u::muted,1210);
 if(u::Button(24,682,266,30,"Retirer mes effets",false,enabled))gEngfuncs.pfnServerCmd("vf_status_clear\n");
 if(u::Button(309,682,400,30,"Reinitialiser le scenario / voix",false,enabled))gEngfuncs.pfnServerCmd("vf_status_reset\n");
 u::Text(747,689,"F3 pour revenir. J : provoquer. R : recharger.",u::muted,489);
}
void StatusEntities(){
 int local=LocalIndex();cl_entity_t* viewer=gEngfuncs.GetLocalPlayer();if(!viewer)return;
 for(int p=1;p<=gEngfuncs.GetMaxClients()&&p<=32;++p){if(p==local&&!CL_IsThirdPerson())continue;
  int id=-1;for(int i=0;i<vfs::Count;++i)if(StatusActive(p,i)){id=i;break;}if(id<0)continue;
  cl_entity_t* target=gEngfuncs.GetEntityByIndex(p);if(!target||!target->model||target->curstate.messagenum!=viewer->curstate.messagenum)continue;
  // Keep player identity so the halo reuses the equipped GIGN/R1 assembly.
  cl_entity_t& m=playerStatus[p].model;m=*target;m.curstate.rendermode=kRenderTransAdd;m.curstate.renderfx=kRenderFxGlowShell;m.curstate.renderamt=5;
  m.curstate.rendercolor.r=vfx::effects[id].color[0];m.curstate.rendercolor.g=vfx::effects[id].color[1];m.curstate.rendercolor.b=vfx::effects[id].color[2];
  if(halo)gEngfuncs.CL_CreateVisibleEntity(ET_NORMAL,&m);
 }
}
void StatusWorld(){
 int local=LocalIndex();cl_entity_t* viewer=gEngfuncs.GetLocalPlayer();if(!viewer)return;
 float angles[3],forward[3],right[3],up[3];gEngfuncs.GetViewAngles(angles);gEngfuncs.pfnAngleVectors(angles,forward,right,up);
 for(int p=1;p<=gEngfuncs.GetMaxClients()&&p<=32;++p){if(p==local&&!CL_IsThirdPerson())continue;
  cl_entity_t* target=gEngfuncs.GetEntityByIndex(p);if(!target||!target->model||target->curstate.messagenum!=viewer->curstate.messagenum)continue;
  int drawn=0;for(int i=0;i<vfs::Count&&drawn<4;++i)if(StatusActive(p,i)){Draw(i,V(target->origin[0],target->origin[1],target->origin[2]),V(right[0],right[1],right[2]),V(up[0],up[1],up[2]),1,false);++drawn;}
 }
}
bool screenFeedback=true,armFeedback=true,armOwned=false;
int previousArmFx=0,previousArmAmt=0,previousArmColor[3]={};
int feedbackEdges=0,feedbackPrimitives=0,feedbackDominant=-1;
int LocalFeedbackPlayer(){int p=LocalIndex();return p&&!g_iUser1&&!gHUD.m_iIntermission&&gHUD.m_Health.m_iHealth>0?p:0;}
int FeedbackSelection(int local,int ids[4]){
 if(!local)return 0;int all[vfs::Count],n=0;
 for(int i=0;i<vfs::Count;++i)if(StatusActive(local,i))all[n++]=i;
 std::stable_sort(all,all+n,[local](int a,int b){
  // Coupled reactions are the result the player must recognize first.
  bool ar=vfs::effects[a].kind==1,br=vfs::effects[b].kind==1;
  if(ar!=br)return ar;return playerStatus[local].order[a]>playerStatus[local].order[b];
 });for(int i=0;i<n&&i<4;++i)ids[i]=all[i];return n;
}
float FeedbackFade(int p,int id){return vffeedback::Fade(gEngfuncs.GetClientTime(),playerStatus[p].started[id],playerStatus[p].until[id]);}
void RestoreArms(){
 cl_entity_t* vm=gEngfuncs.GetViewModel();
 if(vm&&armOwned){vm->curstate.renderfx=previousArmFx;vm->curstate.renderamt=previousArmAmt;
  vm->curstate.rendercolor.r=previousArmColor[0];vm->curstate.rendercolor.g=previousArmColor[1];vm->curstate.rendercolor.b=previousArmColor[2];}
 armOwned=false;feedbackDominant=-1;
}
void StatusArms(){
 int p=LocalFeedbackPlayer(),ids[4];int count=FeedbackSelection(p,ids);cl_entity_t* vm=gEngfuncs.GetViewModel();
 bool fitted=p&&VF_EngineIsReferenceWeapon(p)&&vm&&vm->model&&!stricmp(vm->model->name,"models/v_9mmar.mdl");
 if(!armFeedback||!count||!fitted||CL_IsThirdPerson()){RestoreArms();return;}
 if(!armOwned){previousArmFx=vm->curstate.renderfx;previousArmAmt=vm->curstate.renderamt;
  previousArmColor[0]=vm->curstate.rendercolor.r;previousArmColor[1]=vm->curstate.rendercolor.g;previousArmColor[2]=vm->curstate.rendercolor.b;armOwned=true;}
 int id=ids[0];feedbackDominant=id;const vfx::Effect& e=vfx::effects[id];float fade=FeedbackFade(p,id);
 float rgb[3];for(int k=0;k<3;++k)rgb[k]=(float)e.color[k];
 if(e.kind==1){float mix=.5f+.40f*sinf(gEngfuncs.GetClientTime()*1.8f);
  for(int k=0;k<3;++k)rgb[k]=vfx::effects[e.parentA].color[k]*(1-mix)+vfx::effects[e.parentB].color[k]*mix;
  if(id==15)for(int k=0;k<3;++k)rgb[k]=rgb[k]*.35f+e.color[k]*.65f;
 }
 float strength=fade*(.82f+.06f*sinf(gEngfuncs.GetClientTime()*2.f));
 vm->curstate.renderfx=kRenderFxGlowShell;vm->curstate.renderamt=6;
 vm->curstate.rendercolor.r=int(rgb[0]*strength);vm->curstate.rendercolor.g=int(rgb[1]*strength);vm->curstate.rendercolor.b=int(rgb[2]*strength);
}
void VisualLayers(){if(gEngfuncs.Cmd_Argc()==3){screenFeedback=atoi(gEngfuncs.Cmd_Argv(1))!=0;armFeedback=atoi(gEngfuncs.Cmd_Argv(2))!=0;}}
bool BindDecal(int id,int frame){
 if(id<0||id>=vfdecal::Count)return false;HSPRITE& sprite=statusDecals[id];
 if(!sprite){char path[128];snprintf(path,sizeof(path),"sprites/vf_status/%s.spr",vfdecal::assets[id].id);sprite=gEngfuncs.pfnSPR_Load(path);}
 model_s* model=sprite?const_cast<model_s*>(gEngfuncs.GetSpritePointer(sprite)):NULL;
 return model&&gEngfuncs.pfnSPR_Frames(sprite)==vfdecal::Frames&&gEngfuncs.pTriAPI->SpriteTexture(model,frame)!=0;
}
void DecalAudit(){int loaded=0,frames=0;
 for(int id=0;id<vfdecal::Count;++id)if(BindDecal(id,0)){++loaded;frames+=gEngfuncs.pfnSPR_Frames(statusDecals[id]);}
 gEngfuncs.Con_DPrintf("VFStatus decals: loaded=%d/%d frames=%d/%d\n",loaded,vfdecal::Count,frames,vfdecal::Count*vfdecal::Frames);
}
void DecalQuad(const vffeedback::Rect& rect){triangleapi_t* api=gEngfuncs.pTriAPI;
 const float xs[]={rect.left,rect.right,rect.right,rect.left},ys[]={rect.top,rect.top,rect.bottom,rect.bottom};
 api->Begin(TRI_QUADS);for(int v=0;v<4;++v){api->TexCoord2f(xs[v],ys[v]);api->Vertex3f(xs[v]*ScreenWidth,ys[v]*ScreenHeight,0);}api->End();
}
bool StatusDecal(int p,int id,int edge,float fade){
 if(id<0||id>=vfdecal::Count)return false;
 if(!BindDecal(id,0))return false;
 triangleapi_t* api=gEngfuncs.pTriAPI;vffeedback::Rect rect=vffeedback::DecalEdge(edge);
 float elapsed=gEngfuncs.GetClientTime()-playerStatus[p].started[id];vffeedback::FrameBlend frame=vffeedback::DecalFrame(id,elapsed);
 api->CullFace(TRI_NONE);api->RenderMode(kRenderTransTexture);
 // Each source has genuine alpha; the shared strength applies equally to all
 // materials. Smooth source-over weights sum to the desired total opacity.
 float opacity=fade*vfdecal::Opacity;
 float next=opacity*frame.mix;
 float current=opacity*(1-frame.mix)/(1-next);
 for(int layer=0;layer<2;++layer){float weight=layer?next:current;if(weight<.001f)continue;
  if(!BindDecal(id,layer?frame.next:frame.current))continue;
  api->Color4fRendermode(1,1,1,weight,kRenderTransAlpha);
  DecalQuad(rect);++feedbackPrimitives;
 }api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);return true;
}
void VisualStats(){int p=LocalFeedbackPlayer(),ids[4];int n=FeedbackSelection(p,ids);
 gEngfuncs.Con_DPrintf("VFStatus visual: local=%d active=%d edges=%d primitives=%d arms=%d dominant=%s\n",p,n,feedbackEdges,feedbackPrimitives,armOwned?1:0,feedbackDominant>=0?vfs::effects[feedbackDominant].id:"none");
 if(n&&ids[0]<vfdecal::Count){vffeedback::FrameBlend f=vffeedback::DecalFrame(ids[0],gEngfuncs.GetClientTime()-playerStatus[p].started[ids[0]]);
 gEngfuncs.Con_DPrintf("VFStatus decal: effect=%s frame=%d next=%d blend=%.3f\n",vfdecal::assets[ids[0]].id,f.current,f.next,f.mix);}

}
void EdgeBand(int id,int edge,float fade){
 u::Color c=Color(id);int depth=int(ScreenHeight*.065f);if(depth<1)return;
 for(int i=0;i<16;++i){int a=i*depth/16,b=(i+1)*depth/16;float t=1.f-i/16.f;int alpha=int(64*fade*t*t);
  if(edge==0)gEngfuncs.pfnFillRGBABlend(a,0,b-a,ScreenHeight,c.r,c.g,c.b,alpha);
  if(edge==1)gEngfuncs.pfnFillRGBABlend(ScreenWidth-b,0,b-a,ScreenHeight,c.r,c.g,c.b,alpha);
  if(edge==2)gEngfuncs.pfnFillRGBABlend(0,a,ScreenWidth,b-a,c.r,c.g,c.b,alpha);
  if(edge==3)gEngfuncs.pfnFillRGBABlend(0,ScreenHeight-b,ScreenWidth,b-a,c.r,c.g,c.b,alpha);
 }
}
void StatusEdges(int p,const int ids[4],int total){
 feedbackEdges=feedbackPrimitives=0;if(!screenFeedback||!total)return;
 int count=std::min(total,4);triangleapi_t* api=gEngfuncs.pTriAPI;
 for(int edge=0;edge<4;++edge){int id=ids[edge%count];float fade=FeedbackFade(p,id);if(fade<=0)continue;
  if(StatusDecal(p,id,edge,fade)){++feedbackEdges;continue;}
  EdgeBand(id,edge,fade);vffeedback::Quad q[512];int n=vffeedback::Generate(id,edge,gEngfuncs.GetClientTime(),(float)ScreenWidth,(float)ScreenHeight,fade,q,512);
  ++feedbackEdges;api->CullFace(TRI_NONE);api->RenderMode(kRenderTransAdd);
  for(int i=0;i<n;++i){if(!Bind(q[i].texture,gEngfuncs.GetClientTime()))continue;api->Color4f(q[i].r,q[i].g,q[i].b,q[i].a);api->Begin(TRI_QUADS);
   for(int v=0;v<4;++v){api->TexCoord2f(v==1||v==2?1.f:0.f,v>=2?1.f:0.f);api->Vertex3f(q[i].p[v].x,q[i].p[v].y,0);}api->End();++feedbackPrimitives;
  }api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);
 }
}
void StatusHud(){
 if(VF_CharacterOpen())return;int local=LocalFeedbackPlayer(),ids[4];int count=FeedbackSelection(local,ids);if(!count)return;
 int rows=std::min(count,4);float y=570-rows*58.f;
 for(int row=0;row<rows;++row){int id=ids[row];const vfx::Effect& e=vfx::effects[id];float yy=y+row*58;
  float left=std::max(0.f,playerStatus[local].until[id]-gEngfuncs.GetClientTime());
  float ratio=left/std::max(.01f,playerStatus[local].duration[id]);u::Box(24,yy,264,51,u::bg,218);u::Box(24,yy,3,51,Color(id),230);
  Icon(id,35,yy+10,25);u::Text(69,yy+8,e.hudName,u::white,167);char timer[24];snprintf(timer,sizeof(timer),"%.1fs",left);u::Text(239,yy+8,timer,Color(id),46);
  char recipe[112];if(e.kind==1)snprintf(recipe,sizeof(recipe),"%s + %s",vfx::effects[e.parentA].id,vfx::effects[e.parentB].id);else snprintf(recipe,sizeof(recipe),"%s",e.kind==2?"TACTICAL STATUS":"ELEMENTAL STATUS");
  u::Text(69,yy+28,recipe,Color(id),209);u::Box(69,yy+46,204,2,u::muted,80);u::Box(69,yy+46,204*vffeedback::Clamp(ratio,0,1),2,Color(id),230);
 }
 if(count>4){char more[80];snprintf(more,sizeof(more),"+%d additional active statuses",count-4);u::Text(35,574,more,u::white,300);}
}
void Matrix(){
 u::Text(24,226,"8 VECTEURS PRIMAIRES / 2 PARTENAIRES CHACUN / 8 REACTIONS COUPLEES",u::teal);
 const char* labels[]={"Hydro","Electro","Cryo","Thermal","Toxic","Corrosion","Sonic","Kinetic"};
 for(int i=0;i<8;++i){float y=290+i*42.f;Icon(i,25,y+6,25);u::Text(65,y+12,labels[i],Color(i));u::Text(180+i*82.f,255,labels[i],Color(i),79);
  for(int j=0;j<8;++j){float x=180+j*82.f;int result=vfx::Reaction(i,j);if(u::Button(x,y,73,35,result>=0?"+":"-",result>=0,result>=0)){Select(result);matrix=false;}
   if(result>=0&&u::Hover(x,y,73,35))u::Tip(vfx::effects[result].name);
  }
 }
 u::Box(870,255,386,365,u::panel);u::Text(890,280,"LE LANGAGE DES EFFETS",u::white);u::Wrap(890,319,"Vecteur primaire (VP) : composante. Etat : empreinte sur la cible, comme Soaked. Reaction couplee (RC) : resultat de deux VP compatibles.",343,u::muted,4);
 u::Wrap(890,430,"Chaque VP a deux partenaires au choix : l'un OU l'autre. Cliquer sur + pour voir la RC. A+B = B+A ; pas de combinaison triple.",343,u::white,4);
 u::Wrap(890,538,"ArcChain et SteamVeil sont retrouves. Les six autres croisements sont des propositions.",343,u::amber,3);
}
}
void VF_EffectsDeathLab(){deathLab=true;testPlayer=false;Open();}
void VF_EffectsInit(){
 gEngfuncs.pfnAddCommand("vf_death_lab",VF_EffectsDeathLab);
 VF_WeaponFXInit();
 gEngfuncs.pfnHookUserMsg("VFStatus",ReceiveStatus);gEngfuncs.pfnAddCommand("vf_status_visual_layers",VisualLayers);gEngfuncs.pfnAddCommand("vf_status_visual_stats",VisualStats);gEngfuncs.pfnAddCommand("vf_status_decal_audit",DecalAudit);gEngfuncs.Con_DPrintf("VFStatus arms: renderer=1\n");gEngfuncs.pfnAddCommand("vf_effect_player_test",OpenTest);gEngfuncs.pfnAddCommand("vf_status_client",PlayerStats);
 gEngfuncs.pfnAddCommand("vf_effects",Open);gEngfuncs.pfnAddCommand("vf_effect_select",ChooseCommand);gEngfuncs.pfnAddCommand("vf_effect_spawn",SpawnCommand);gEngfuncs.pfnAddCommand("vf_effect_attach",Attach);gEngfuncs.pfnAddCommand("vf_effect_clear",Clear);gEngfuncs.pfnAddCommand("vf_effect_next",Next);gEngfuncs.pfnAddCommand("vf_effect_prev",Prev);gEngfuncs.pfnAddCommand("vf_effect_audit",Audit);gEngfuncs.pfnAddCommand("vf_effect_stats",Stats);gEngfuncs.pfnAddCommand("vf_effect_bench",Bench);gEngfuncs.pfnAddCommand("vf_effect_layers",LayersCommand);VF_EffectsReset();
}
void VF_EffectsReset(){VF_RangeReset();RestoreArms();feedbackEdges=feedbackPrimitives=0;screenFeedback=armFeedback=true;VF_WeaponFXReset();memset(playerStatus,0,sizeof(playerStatus));statusOrder=0;testPlayer=false;emitterCount=0;memset(sprites,0,sizeof(sprites));memset(statusDecals,0,sizeof(statusDecals));mannequin=NULL;mannequinIndex=0;generated=visibleModels=0;frames=0;totalMs=0;bench=-1;paused=false;epoch=0;pauseAt=0;}
void VF_EffectsEntities(){
 VF_RangeEntities();StatusArms();StatusEntities();visibleModels=0;if(!emitterCount)return;
 if(!mannequin)mannequin=gEngfuncs.CL_LoadModel("models/vf_skins/persona_scout.mdl",&mannequinIndex);
 for(int i=0;i<emitterCount;++i){Emitter& e=emitters[i];cl_entity_t& m=e.model;
  if(e.entity){cl_entity_t* target=gEngfuncs.GetEntityByIndex(e.entity);if(!target||!target->model||target->model->type!=mod_studio)continue;
   // Keep the render identity so a modular target reuses its registered skin assembly.
   // Only this local copy receives the halo; the network entity is untouched.
   m=*target;m.player=0;m.curstate.rendermode=kRenderTransAdd;e.center=V(m.origin[0],m.origin[1],m.origin[2]);
  }else{if(!mannequin)continue;memset(&m,0,sizeof(m));m.model=mannequin;m.curstate.modelindex=mannequinIndex;m.curstate.rendermode=kRenderNormal;m.curstate.body=31;m.curstate.skin=e.effect%14;m.curstate.sequence=0;m.curstate.framerate=1;m.curstate.animtime=gEngfuncs.GetClientTime();m.curstate.frame=0;memset(m.curstate.controller,128,sizeof(m.curstate.controller));memset(m.latched.prevcontroller,128,sizeof(m.latched.prevcontroller));
   m.origin[0]=e.center.x;m.origin[1]=e.center.y;m.origin[2]=e.center.z;m.angles[1]=e.yaw;VectorCopy(m.origin,m.curstate.origin);VectorCopy(m.angles,m.curstate.angles);
  }
  const vfx::Effect& def=vfx::effects[e.effect];m.curstate.renderfx=halo?kRenderFxGlowShell:kRenderFxNone;m.curstate.renderamt=halo?5:255;
  m.curstate.rendercolor.r=def.color[0];m.curstate.rendercolor.g=def.color[1];m.curstate.rendercolor.b=def.color[2];
  if(!e.entity||halo){if(gEngfuncs.CL_CreateVisibleEntity(ET_NORMAL,&m))++visibleModels;}
 }
}
void VF_EffectsWorld(){
 VF_DeathWorld();VF_RangeWorld();VF_WeaponFXWorld();StatusWorld();
 if(!emitterCount)return;auto start=std::chrono::steady_clock::now();float angles[3],forward[3],right[3],up[3];gEngfuncs.GetViewAngles(angles);gEngfuncs.pfnAngleVectors(angles,forward,right,up);generated=0;
 for(int i=0;i<emitterCount;++i){Emitter& e=emitters[i];if(e.entity){cl_entity_t* t=gEngfuncs.GetEntityByIndex(e.entity);if(!t||!t->model)continue;e.center=V(t->origin[0],t->origin[1],t->origin[2]);}
  generated+=Draw(e.effect,e.center,V(right[0],right[1],right[2]),V(up[0],up[1],up[2]),1,false);
 }
 auto now=std::chrono::steady_clock::now();double ms=std::chrono::duration<double,std::milli>(now-start).count();totalMs+=ms;++frames;
 if(bench>=0){benchTimes[bench]=ms;benchFrames[bench]=std::chrono::duration<double,std::milli>(now-previous).count();previous=now;
  if(++bench==180){double sum=0,frame=0;for(int i=0;i<180;++i){sum+=benchTimes[i];frame+=benchFrames[i];}std::sort(benchTimes,benchTimes+180);gEngfuncs.Con_DPrintf("VFX bench: active=%d primitives=%d samples=180 mean_ms=%.4f p95_ms=%.4f frame_ms=%.4f\n",emitterCount,generated,sum/180,benchTimes[170],frame/180);bench=-1;}
 }
}
void VF_EffectsGuide(){
 if(VF_WeaponFXGuide())return;
 if(u::Button(350,192,140,30,"Morts",deathLab)){deathLab=!deathLab;testPlayer=false;matrix=false;}
 if(u::Button(500,192,280,30,testPlayer?"Retour au laboratoire visuel":"Test joueur / voix",testPlayer)){testPlayer=!testPlayer;deathLab=false;matrix=false;}
 if(u::Button(800,192,222,30,"Weapon FX / R1"))gEngfuncs.pfnClientCmd("vf_shotfx_lab\n");
 u::Text(24,195,"EFFETS / LABORATOIRE VISUEL",u::white);if(u::Button(1040,192,216,30,matrix?"Retour au catalogue":"Matrice 8 x 8"))matrix=!matrix;
 if(matrix){Matrix();return;}
 if(deathLab){VF_DeathGuide(selected);return;}
 const char* groups[]={"Vecteurs","Reactions","Etats"};const float groupX[]={24,114,216},groupW[]={88,96,74};for(int i=0;i<3;++i)if(u::Button(groupX[i],231,groupW[i],34,groups[i],filter==i)){filter=i;for(int j=0;j<vfx::Count;++j)if(vfx::effects[j].kind==i){Select(j);break;}}
 int row=0;for(int i=0;i<vfx::Count;++i)if(vfx::effects[i].kind==filter){float y=277+row++*43.f;if(u::Button(24,y,266,38,"",selected==i))Select(i);Icon(i,33,y+6,24);char label[96];snprintf(label,sizeof(label),"%s",vfx::effects[i].name);if(filter==1){char* separator=strchr(label,'/');if(separator){if(separator>label)--separator;*separator=0;}}u::Text(67,y+11,label,selected==i?u::white:u::muted,212);}
 const vfx::Effect& e=vfx::effects[selected];u::Color c=Color(selected);
 u::Box(309,231,400,417,u::panel);u::Text(325,246,"APERCU 3D / PARTICULES",u::muted,365);
 int variants[3]={0,0,0};bool ready=VF_PreviewDraw(false,variants,u::X(355),u::Y(282),305*u::SX(),310*u::SY());
 if(!ready)u::Wrap(329,370,"Modele indisponible. Les particules restent visibles.",350,u::amber,2);
 Draw(selected,V(u::X(509),u::Y(440),0),V(1,0,0),V(0,1,0),3.45f*VF_PreviewZoomValue()*u::SX(),true);
 u::Viewport(313,270,392,337);
 if(u::Button(324,611,105,28,paused?"Reprendre":"Pause")){if(paused){epoch=gEngfuncs.GetClientTime()-pauseAt;paused=false;}else{pauseAt=Time();paused=true;}}
 if(u::Button(438,611,120,28,particles?"VFX ON":"VFX OFF",particles))particles=!particles;
 if(u::Button(567,611,125,28,halo?"Halo salle":"Sans halo",halo))halo=!halo;
 if(testPlayer){TestPanel();return;}
 u::Box(728,231,528,417,u::panel);Icon(selected,745,247,37);u::Text(796,246,e.kind==0?"VECTEUR PRIMAIRE / VP":e.kind==1?"REACTION COUPLEE / RC":"ETAT TACTIQUE / ET",u::muted,441);u::Text(796,270,e.name,c,441);u::Text(747,303,e.recipe,u::white,489);
 u::Text(747,333,"INTENTION / NON ACTIVE",u::teal);u::Wrap(747,357,e.meaning,485,u::white,4);
 u::Text(747,447,"SIGNATURE VISUELLE",c);u::Wrap(747,473,e.visual,485,u::muted,2);
 if(e.kind==0){int n=0;for(int i=0;i<vfx::Count;++i){const vfx::Effect& r=vfx::effects[i];if(r.kind!=1||(r.parentA!=selected&&r.parentB!=selected))continue;int other=r.parentA==selected?r.parentB:r.parentA;
   char label[120];snprintf(label,sizeof(label),"+ %s  >  %s",vfx::effects[other].id,r.name);if(u::Button(745,533+n*43.f,491,37,label))Select(i);++n;
  }}else if(e.kind==1){if(u::Button(745,541,241,39,vfx::effects[e.parentA].name))Select(e.parentA);if(u::Button(995,541,241,39,vfx::effects[e.parentB].name))Select(e.parentB);}
 else u::Wrap(747,540,"Etat tactique distinct des 8 elements. Il ne compte pas dans la matrice des croisements.",478,u::muted,3);
 u::Text(746,616,e.origin,strstr(e.origin,"PROPOSITION")?u::amber:u::muted,488);
 u::Text(25,653,status,u::muted,1190);
 if(u::Button(24,682,178,30,"Retirer les effets",false,emitterCount>0))Clear();
 if(u::Button(217,682,220,30,"Appliquer a la cible"))Attach();
 if(u::Hover(217,682,220,30))u::Tip("Viser d'abord un personnage dans la salle, puis ouvrir F3 et appliquer. Visuel local seulement.");
 if(u::Button(450,682,355,30,"Comparer A / B / resultat",false,e.kind==1))Spawn(true);
 if(u::Button(820,682,436,30,"Voir cet effet dans la salle",true))Spawn(false);
}
void VF_EffectsScreen(){
 feedbackEdges=feedbackPrimitives=0;if(VF_CharacterOpen())return;
 int local=LocalFeedbackPlayer(),ids[4];int count=FeedbackSelection(local,ids);StatusEdges(local,ids,count);
}
void VF_EffectsHud(){
 VF_RangeHud();VF_WeaponFXHud();StatusHud();
 if(VF_CharacterOpen()||!emitterCount)return;
 u::Box(24,570,575,72,u::bg,215);char label[160];snprintf(label,sizeof(label),"%s / VISUEL UNIQUEMENT",vfx::effects[selected].name);u::Text(36,582,label,Color(selected),550);u::Text(36,608,"F3 : guide   PgPrec / PgSuiv : effet   F9 : retirer",u::white,550);
 for(int i=0;i<emitterCount;++i){float point[3]={emitters[i].center.x,emitters[i].center.y,emitters[i].center.z+49},screen[3];if(!gEngfuncs.pTriAPI->WorldToScreen(point,screen)&&fabsf(screen[0])<.85f&&fabsf(screen[1])<.9f){float x=(screen[0]+1)*ScreenWidth*.5f,y=(1-screen[1])*ScreenHeight*.5f;x=(x-u::X(0))/u::SX();y=(y-u::Y(0))/u::SY();u::Text(x-94,y,vfx::effects[emitters[i].effect].name,Color(emitters[i].effect),210);}}
}

void VF_EffectsTargetDraw(int effect,const float* origin){
 if(effect<0||effect>=vfx::Count)return;float angles[3],forward[3],right[3],up[3];gEngfuncs.GetViewAngles(angles);gEngfuncs.pfnAngleVectors(angles,forward,right,up);
 Draw(effect,V(origin[0],origin[1],origin[2]),V(right[0],right[1],right[2]),V(up[0],up[1],up[2]),1,false);
}

// Small independent particles for severed pieces, batched by the five existing
// sprites. World positions are retained by the death emitter to form trails.
void VF_EffectsParticleDraw(const vf_fx_particle_t* points,int count){
 if(!particles||!count)return;float angles[3],forward[3],right_[3],up_[3];gEngfuncs.GetViewAngles(angles);gEngfuncs.pfnAngleVectors(angles,forward,right_,up_);
 V right(right_[0],right_[1],right_[2]),up(up_[0],up_[1],up_[2]);triangleapi_t* api=gEngfuncs.pTriAPI;
 api->CullFace(TRI_NONE);api->RenderMode(kRenderTransAdd);
 for(int texture=0;texture<5;++texture){if(!Bind(texture,gEngfuncs.GetClientTime()))continue;api->Begin(TRI_QUADS);
  for(int i=0;i<count;++i){const vf_fx_particle_t& p=points[i];if(p.blood||p.texture!=texture)continue;V a(p.origin[0],p.origin[1],p.origin[2]),b(p.end[0],p.end[1],p.end[2]);api->Color4f(p.color[0],p.color[1],p.color[2],p.alpha);
   if(p.pattern==vfx::Rings){for(int k=0;k<12;++k){float t=k*6.2831853f/12,t2=(k+1)*6.2831853f/12;V c=a+right*(cosf(t)*p.size)+up*(sinf(t)*p.size),d=a+right*(cosf(t2)*p.size)+up*(sinf(t2)*p.size);V n=Normal(Cross(d-c,Cross(right,up)))*.22f;Quad(c-n,c+n,d+n,d-n);}}
   else if(p.line){V n=Normal(Cross(b-a,Cross(right,up)))*.3f;Quad(a-n,a+n,b+n,b-n);}
   else if(p.pattern==vfx::Shards){V x=right*p.size,z=up*p.size*1.7f;Quad(a-z,a+x,a+z,a-x);}
   else{V x=right*p.size,y=up*p.size;Quad(a-x-y,a+x-y,a+x+y,a-x+y);}
  }api->End();
 }
 // Blood uses alpha blending and an explicitly dark-red tint. Bright elemental
 // layers retain additive blending; they cannot bleach a blood droplet white.
 int bloodIndex=0;model_t* bloodSprite=gEngfuncs.CL_LoadModel("sprites/blood.spr",&bloodIndex);
 if(bloodSprite&&api->SpriteTexture(bloodSprite,0)){
  api->RenderMode(kRenderTransTexture);api->Begin(TRI_QUADS);
  for(int i=0;i<count;++i){const vf_fx_particle_t& p=points[i];if(!p.blood)continue;
   V a(p.origin[0],p.origin[1],p.origin[2]);api->Color4f(p.color[0],p.color[1],p.color[2],p.alpha);
   V x=right*p.size,y=up*p.size*1.4f;Quad(a-x-y,a+x-y,a+x+y,a-x+y);
  }api->End();
 }api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);
}
