#include <cmath>
#include "hud.h"
#include "cl_util.h"
#include "cl_entity.h"
#include "com_model.h"
#include "parsemsg.h"
#include "r_efx.h"
#include "vf_death.h"
#include "vf_effects.h"
#include "../game_shared/vf_death_visual.h"
#include "../game_shared/vf_status_catalog.h"
#include "../game_shared/vf_death_tracks.h"
#include "../game_shared/vf_death_atlas.h"
#include "../game_shared/vf_death_sfx_catalog.h"
#include "vf_effect_catalog.h"
#include <cstring>
namespace {
struct Corpse{int missing,effect,skins[5];float until,started;};Corpse corpses[2048];int lightning=0;
struct Fragment{int body,effect,serial,blood,elemental;float started,until,next,lastAt,travel;Vector last;bool seen,burst;};Fragment fragments[2048];
enum {TrailCapacity=384};
struct Trail{bool active;float born,until,gravity;Vector origin,velocity,span;vf_fx_particle_t draw;};Trail trail[TrailCapacity];
int trailCursor=0,scanCursor=1,trailPeak=0;float lastTrailTime=0;
int ReceiveSound(const char*,int size,void* data){
 if(size!=5)return 1;BEGIN_READ(data,size);int id=READ_SHORT(),layer=READ_BYTE(),effect=READ_BYTE()-1,pitch=READ_BYTE();
 if(id<1||id>=2048||layer>1||effect<-1||effect>=16)return 1;
 const vfds::Profile& p=vfds::For(effect);const char* sample=layer?p.dismemberment:p.death;if(!sample)return 1;
 // Diagnostic only. The engine already receives the positional native sound.
 gEngfuncs.Con_DPrintf("VFDeathSfx received: entity=%d layer=%s effect=%s channel=%d pitch=%d sample=%s\n",id,layer?"dismemberment":"death",p.id,layer?CHAN_ITEM:CHAN_BODY,pitch,sample);return 1;
}
int ReceiveFragment(const char*,int size,void* data){
 if(size!=10)return 1;BEGIN_READ(data,size);int id=READ_SHORT(),body=READ_BYTE(),effect=READ_BYTE()-1,age=READ_SHORT(),left=READ_SHORT(),serial=(unsigned short)READ_SHORT();
 if(id<1||id>=2048||body>=20||effect>=16||age<0||age>1200||left<0||left>1200||!serial)return 1;
 Fragment& f=fragments[id];if(f.serial!=serial){f=Fragment();f.serial=serial;}f.body=body;f.effect=effect;f.started=gEngfuncs.GetClientTime()-age*.01f;f.until=left?gEngfuncs.GetClientTime()+left*.01f:0;
 gEngfuncs.Con_DPrintf("VFFragment received entity=%d body=%d effect=%d age=%.2f remaining=%.2f serial=%d\n",id,body,effect,age*.01f,left*.01f,serial);return 1;
}
float Random(float a,float b){return gEngfuncs.pfnRandomFloat(a,b);}
void EmitElement(Fragment& f,const Vector& origin,const Vector& velocity,const vfx::Layer& layer,float now){
 Trail& t=trail[trailCursor++%TrailCapacity];t=Trail();t.active=true;t.born=now;t.until=now+Random(.35f,.65f);
 t.origin=origin+Vector(Random(-2,2),Random(-2,2),Random(-2,2));t.velocity=velocity*.12f+Vector(Random(-16,16),Random(-16,16),Random(0,18));
 t.draw.texture=layer.texture;t.draw.pattern=layer.pattern;t.draw.color[0]=layer.r;t.draw.color[1]=layer.g;t.draw.color[2]=layer.b;t.draw.size=layer.pattern==vfx::Cloud?3.2f:layer.pattern==vfx::Rings?2.f:1.6f;
 t.gravity=(layer.pattern==vfx::Drops)?-125.f:layer.pattern==vfx::Rise||layer.pattern==vfx::Cloud?22.f:-60.f;
 t.draw.line=layer.pattern==vfx::Arcs||layer.pattern==vfx::Sparks||layer.pattern==vfx::Chain||layer.pattern==vfx::Burst;t.span=Vector(Random(-4,4),Random(-4,4),Random(-4,4));++f.elemental;
}
void EmitBlood(Fragment& f,const Vector& origin,const Vector& velocity,float now,bool burst){
 Trail& t=trail[trailCursor++%TrailCapacity];t=Trail();t.active=true;t.born=now;t.until=now+Random(.35f,.65f);
 t.origin=origin+Vector(Random(-3,3),Random(-3,3),Random(-2,2));
 float spread=burst?65.f:25.f;
 t.velocity=velocity*(burst?.22f:.10f)+Vector(Random(-spread,spread),Random(-spread,spread),Random(burst?20.f:2.f,burst?100.f:28.f));
 t.gravity=-300.f;t.draw.blood=true;t.draw.size=Random(burst?.65f:.35f,burst?1.3f:.75f);
 t.draw.color[0]=Random(.55f,.8f);t.draw.color[1]=Random(.015f,.035f);t.draw.color[2]=Random(.02f,.04f);++f.blood;
}
void EmitTrail(Fragment& f,const Vector& origin,const Vector& velocity,float now){
 for(int i=0;i<(f.body>=15?2:1);++i)EmitBlood(f,origin,velocity,now,false);
 if(f.effect<0)return;const vfx::Effect& e=vfx::effects[f.effect];for(int k=0;k<e.layerCount;++k)EmitElement(f,origin,velocity,e.layers[k],now);
}
void FragmentWorld(float now,const cl_entity_t* viewer){
 float dt=lastTrailTime?fminf(.05f,fmaxf(0.f,now-lastTrailTime)):0;lastTrailTime=now;int emits=0;
 for(int i=0;i<2047;++i){int id=1+(scanCursor-1+i)%2047;Fragment& f=fragments[id];float age=now-f.started;if(f.until<=now||age<0||age>2.2f)continue;
  cl_entity_t* e=gEngfuncs.GetEntityByIndex(id);if(!e||!e->model||strcmp(e->model->name,vfdeath::GibModel)||e->curstate.body!=f.body||e->curstate.messagenum!=viewer->curstate.messagenum)continue;
  Vector position=e->origin,velocity(0,0,0);if(f.seen&&now>f.lastAt){velocity=(position-f.last)*(1.f/(now-f.lastAt));f.travel+=(position-f.last).Length();}f.last=position;f.lastAt=now;f.seen=true;
  if(!f.burst){f.burst=true;if(f.body>=15&&age<.3f)for(int n=0;n<10;++n)EmitBlood(f,position,e->curstate.velocity,now,true);}
  if(emits<12&&now>=f.next&&(velocity.Length()>12||age<.15f)){EmitTrail(f,position,velocity,now);f.next=now+.06f;++emits;}
 }scanCursor=1+(scanCursor+126)%2047;
 vf_fx_particle_t draws[TrailCapacity];int count=0;
 for(int i=0;i<TrailCapacity;++i){Trail& t=trail[i];if(!t.active)continue;if(now>=t.until){t.active=false;continue;}t.origin=t.origin+t.velocity*dt;t.origin.z+=.5f*t.gravity*dt*dt;t.velocity.z+=t.gravity*dt;float life=(now-t.born)/(t.until-t.born);t.draw.alpha=(1-life)*(t.draw.blood?.92f:.8f);
  float size=t.draw.size;t.draw.size=t.draw.pattern==vfx::Rings?2+life*7:size;for(int k=0;k<3;++k){t.draw.origin[k]=t.origin[k];t.draw.end[k]=t.origin[k]+t.span[k]*(1-life);}draws[count++]=t.draw;if(t.draw.pattern==vfx::Rings)t.draw.size=size;
 }if(count>trailPeak)trailPeak=count;VF_EffectsParticleDraw(draws,count);
}
int Receive(const char*,int size,void* data){
 if(size!=13)return 1;BEGIN_READ(data,size);int id=READ_SHORT(),missing=READ_BYTE(),effect=READ_BYTE()-1,skins[5];for(int z=0;z<5;++z)skins[z]=READ_BYTE();int age=READ_SHORT(),left=READ_SHORT();
 if(id<1||id>=2048||missing>31||effect>=vfs::Count||age<0||left<0||left>1500)return 1;for(int z=0;z<5;++z)if(skins[z]>=14)return 1;
 Corpse& c=corpses[id];c.missing=missing;c.effect=effect;memcpy(c.skins,skins,sizeof(skins));c.until=left?gEngfuncs.GetClientTime()+left*.01f:0;c.started=gEngfuncs.GetClientTime()-age*.01f;
 gEngfuncs.Con_DPrintf("VFCorpse received entity=%d mask=%d effect=%d age=%.2f remaining=%.2f\n",id,missing,effect,age*.01f,left*.01f);return 1;
}
void Stats(){int bloodActive=0,invalidBlood=0;for(int n=0;n<TrailCapacity;++n)if(trail[n].active&&trail[n].draw.blood&&trail[n].until>gEngfuncs.GetClientTime()){++bloodActive;const vf_fx_particle_t& p=trail[n].draw;if(p.color[0]<.5f||p.color[1]>.05f||p.color[2]>.05f)++invalidBlood;}
 gEngfuncs.Con_Printf("VFBlood alpha_rgb=1 radial_burst=10 gravity=300 active=%d invalid_color=%d\n",bloodActive,invalidBlood);
 int active=0;for(int i=0;i<TrailCapacity;++i)if(trail[i].active&&trail[i].until>gEngfuncs.GetClientTime())++active;gEngfuncs.Con_Printf("VFFragment pool active=%d peak=%d capacity=%d\n",active,trailPeak,TrailCapacity);for(int i=1;i<2048;++i)if(fragments[i].until>gEngfuncs.GetClientTime()){const Fragment& f=fragments[i];cl_entity_t* e=gEngfuncs.GetEntityByIndex(i);int skin=e&&e->model&&!strcmp(e->model->name,vfdeath::GibModel)?e->curstate.skin:-1;int primary,detail;vfdeath::FragmentPairFinishes(skin,primary,detail);gEngfuncs.Con_Printf("VFFragment client entity=%d body=%d effect=%d whole=%d age=%.2f blood=%d elemental=%d travel=%.1f position=%.1f,%.1f,%.1f skin=%d primary=%d detail=%d\n",i,f.body,f.effect,f.body>=15,gEngfuncs.GetClientTime()-f.started,f.blood,f.elemental,f.travel,f.last.x,f.last.y,f.last.z,skin,primary,detail);}for(int i=1;i<2048;++i)if(corpses[i].until>gEngfuncs.GetClientTime()){
 const Corpse& c=corpses[i];cl_entity_t* e=gEngfuncs.GetEntityByIndex(i);
 gEngfuncs.Con_Printf("VFCorpse client entity=%d mask=%d effect=%d body=%d skins=%d,%d,%d,%d,%d age=%.2f sequence=%d frame=%.1f model=%s\n",i,c.missing,c.effect,vfdeath::Body(c.missing),c.skins[0],c.skins[1],c.skins[2],c.skins[3],c.skins[4],gEngfuncs.GetClientTime()-c.started,e?e->curstate.sequence:-1,e?e->curstate.frame:0,e&&e->model?e->model->name:"none");
}}
}
void VF_DeathInit(){gEngfuncs.pfnHookUserMsg("VFDeathSfx",ReceiveSound);gEngfuncs.pfnHookUserMsg("VFCorpse",Receive);gEngfuncs.pfnHookUserMsg("VFFragment",ReceiveFragment);gEngfuncs.pfnAddCommand("vf_death_client",Stats);VF_DeathReset();}
void VF_DeathReset(){memset(corpses,0,sizeof(corpses));memset(fragments,0,sizeof(fragments));memset(trail,0,sizeof(trail));trailCursor=0;scanCursor=1;trailPeak=0;lastTrailTime=0;lightning=0;}
bool VF_DeathAssembly(int id,vf_assembly_t& a){
 if(id<1||id>=2048||corpses[id].until<=gEngfuncs.GetClientTime())return false;const Corpse& c=corpses[id];memset(&a,0,sizeof(a));strcpy(a.rig,vfdeath::Model);a.body=vfdeath::Body(c.missing);
 for(int z=0;z<5;++z){int body=vfdeath::Body(c.missing,z);if(!body)continue;vf_part_t& p=a.parts[a.count++];strcpy(p.model,vfdeath::Model);p.body=body;p.skin=c.skins[z];p.mode=VF_PART_MERGE;}return true;
}
void VF_DeathWorld(){
 float now=gEngfuncs.GetClientTime();cl_entity_t* viewer=gEngfuncs.GetLocalPlayer();if(!viewer)return;FragmentWorld(now,viewer);
 for(int id=1;id<2048;++id){Corpse& c=corpses[id];float age=now-c.started;const vfdeath::Profile* profile=vfdeath::ProfileFor(c.effect);if(c.until<=now||!profile||age>profile->fxSeconds)continue;cl_entity_t* e=gEngfuncs.GetEntityByIndex(id);if(!e||!e->model||strcmp(e->model->name,vfdeath::Model)||e->curstate.messagenum!=viewer->curstate.messagenum)continue;
  // Effect survives status clearing/respawn because it belongs to this corpse.
  float fall=vfdeath::Electric(c.effect)?fminf(1.f,fmaxf(0.f,(age-.85f)/.83f)):0;Vector center=e->origin-Vector(0.f,0.f,fall*26);float offset[3];
  if(vfmotion::Centre(e->curstate.sequence,e->curstate.frame,offset)){float a=e->angles[1]*.01745329252f;center=e->origin+Vector(cosf(a)*offset[0]-sinf(a)*offset[1],sinf(a)*offset[0]+cosf(a)*offset[1],offset[2]);}
  if(!vfdeath::Electric(c.effect)||age<1.4f||c.effect!=1)VF_EffectsTargetDraw(c.effect,center);
  if(!vfdeath::Electric(c.effect))continue;
  if(!lightning)gEngfuncs.CL_LoadModel("sprites/lgtning.spr",&lightning);
  if(lightning&&age<2.1f)for(int arc=0;arc<5;++arc){float t=now*13+arc*1.7f;Vector a=center+Vector(cosf(t)*15,sinf(t)*15,8+sinf(t*1.3f)*14*(1-fall*.6f)),b=center+Vector(cosf(t+2)*21,sinf(t+2)*21,-18*(1-fall)+cosf(t)*13*(1-fall*.6f));gEngfuncs.pEfxAPI->R_BeamPoints(a,b,lightning,.045f,1.3f,.45f,.85f,2,0,20,.25f,.65f,1);}
 }
}
#include "vf_ui.h"
#include "vf_character.h"
#include "vf_effect_catalog.h"
#include "../game_shared/vf_death_motion.h"
#include <cstdio>
void VF_DeathGuide(int selectedEffect){
 namespace u=vfui;static int target=0,mode=1,motion=0,page=0,atlasPage=0,atlasEffect=-1;static bool atlas=false;
 u::Box(24,231,684,417,u::panel);u::Text(44,251,"ANIMATION DE MORT",u::white);
 if(u::Button(443,244,112,29,"Catalogue",!atlas))atlas=false;if(u::Button(567,244,121,29,"Atlas",atlas))atlas=true;
 if(!atlas){
  for(int row=0;row<5;++row){int i=page*5+row;if(i<vfmotion::Count&&u::Button(44,290+row*51.f,644,39,vfmotion::Motions[i].label,motion==i))motion=i;}
  if(u::Button(44,555,150,29,"Precedent",false,page>0))--page;char label[48];snprintf(label,sizeof(label),"Page %d / %d",page+1,(vfmotion::Count+4)/5);u::Text(265,560,label,u::muted);
  if(u::Button(538,555,150,29,"Suivant",false,(page+1)*5<vfmotion::Count))++page;
  u::Wrap(44,597,"Automatique suit l atlas de l effet. Chaque mouvement reste combinable avec les cinq zones de demembrement.",622,u::muted,2);
 }else{
  for(int row=0;row<8;++row){int id=atlasPage*8+row;const vfdeath::Profile& p=vfdeath::Profiles[id];char label[96];snprintf(label,sizeof(label),"%s / %s",vfx::effects[id].hudName,p.label);
   if(u::Button(44+(row%2)*327.f,290+(row/2)*51.f,317,39,label,atlasEffect==id&&mode==2)){atlasEffect=id;mode=2;motion=0;}
  }
  if(u::Button(44,512,317,29,"Elements",atlasPage==0))atlasPage=0;if(u::Button(371,512,317,29,"Reactions",atlasPage==1))atlasPage=1;
  int id=mode==1?1:mode==0?-1:atlasEffect>=0?atlasEffect:selectedEffect;const vfdeath::Profile* p=vfdeath::ProfileFor(id);
  u::Text(44,558,p?p->label:"Chute classique",u::teal,622);
  u::Wrap(44,592,"Choisir un effet ici puis une zone a droite. Les fragments projetes laissent du sang et des particules de cet effet.",622,u::muted,2);
 }
 u::Box(728,231,528,417,u::panel);u::Text(747,247,"MORTS / DEMEMBREMENT",u::white,489);
 u::Text(747,280,"Effet de la mort",u::muted);
 const char* modes[]={"Classique","Electrique","Effet choisi"};
 for(int i=0;i<3;++i)if(u::Button(747+i*166.f,305,157,31,modes[i],mode==i))mode=i;
 u::Text(747,353,"Cible GIGN",u::teal);
 for(int i=0;i<4;++i){char label[24];snprintf(label,sizeof(label),"GIGN %d",i+1);if(u::Button(747+i*125.f,376,116,31,label,target==i))target=i;}
 const char* names[]={"Corps entier","Tete explosee","Bras gauche","Bras droit","Jambe gauche","Jambe droite","Tous les membres"};
 const char* masks[]={"none","head","left_arm","right_arm","left_leg","right_leg","all"};
 for(int i=0;i<7;++i)if(u::Button(747+(i%2)*250.f,429+(i/2)*43.f,239,34,names[i])){
  const char* effect=mode==0?"standard":mode==1?"electro":vfx::effects[atlasEffect>=0?atlasEffect:selectedEffect].id;char command[256];
  snprintf(command,sizeof(command),"vf_range_reset %d\n",target);gEngfuncs.pfnServerCmd(command);
  snprintf(command,sizeof(command),"vf_range_aim %d\n",target);gEngfuncs.pfnServerCmd(command);
  snprintf(command,sizeof(command),"vf_range_death %d %s %s %s\n",target,masks[i],effect,vfmotion::Motions[motion].id);gEngfuncs.pfnServerCmd(command);VF_CharacterClose();
 }
 if(u::Button(747,611,489,28,"Retirer les cadavres"))gEngfuncs.pfnServerCmd("vf_death_clear\n");
 u::Text(25,653,"F4 : salle de test. Choisir un membre et un effet independamment. Le cadavre reste 15 secondes.",u::muted,1210);
 u::Text(25,688,"Essais autorises en solo ou avec sv_cheats 1. Les seuils de demembrement seront regles plus tard.",u::muted,1210);
}
