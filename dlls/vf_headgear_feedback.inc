// Included by vf_voice.cpp; never changes authored animation or saved player layout.
#include "../game_shared/vf_headgear_feedback.h"
#include "../game_shared/vf_headgear_audio_catalog.h"
namespace {
struct HeadgearFeedback {int serial,type,raised,steps;float start;};
HeadgearFeedback gearFeedback[33];
int gearVoiceMessage;
cvar_t gearSfxVolume={"vf_headgear_sfx_volume","0.8",FCVAR_SERVER};
int GearType(CBasePlayer* p){const vf::Item* item=p?VF_EquippedItem(p,vf::HelmetSlot):NULL;return item?item->visual:0;}
float GearCover(CBasePlayer* p){
 float age=gpGlobals->time-p->m_vfHeadgearStart;
 return vf::HeadgearCover(GearType(p),p->m_vfHeadgearRaised,age,p->m_vfHeadgearStart>0&&age>=0&&age<vf::HeadgearDuration);
}
bool GearSpeak(CBasePlayer* p,int type,int category=-1,bool audition=false){
 if(!Ready(p)||p->m_vfVoice<1||p->m_vfVoice>vfv::ActorCount)return false;
 vfv::State& state=p->m_vfVoiceState;float now=gpGlobals->time;const int event=vfha::ScheduleEvent;
 if(!audition&&!vfv::CanSpeak(state,event,20,now))return false;
 int choices[4],count=0,specific=vfha::Category(type);
 for(int i=0;i<vfha::ClipCount;++i){const vfha::Clip& c=vfha::Clips[i];
  if(c.actor==p->m_vfVoice-1&&(category>=0?c.category==category:c.category==0||c.category==specific))choices[count++]=i;
 }
 int index=vfv::Select(choices,count,state.last[event],RANDOM_LONG(0,0x7fff));if(index<0)return false;
 const vfha::Clip& clip=vfha::Clips[index];vfv::Commit(state,event,index,20,now,clip.duration,6);
 // An intent announcement starts before the object covers the face.
 const char* sample=clip.path;
 EMIT_SOUND_DYN(p->edict(),CHAN_VOICE,sample,.85f,ATTN_NORM,0,PITCH_NORM);
 if(gearVoiceMessage){MESSAGE_BEGIN(MSG_PAS_R,gearVoiceMessage,p->pev->origin);
  WRITE_BYTE(p->entindex());WRITE_BYTE(clip.actor);WRITE_BYTE(index);MESSAGE_END();}
 ALERT(at_console,"VFHeadgear voice: player=%d actor=%s category=%d sample=%s audition=%d cover=%.4f\n",p->entindex(),vfv::Actors[clip.actor].id,clip.category,sample,audition,GearCover(p));
 return true;
}
}
const char* VF_HeadgearVoiceSample(CBasePlayer* p,const char* path){return p&&vf::HeadgearMuffled(GearType(p),GearCover(p))?vfha::Mask(path):path;}
static void GearThink(CBasePlayer* p);
void VF_HeadgearFeedbackStart(CBasePlayer* p,int type,bool raised){
 if(!p||p->entindex()<1||p->entindex()>32)return;
 HeadgearFeedback& f=gearFeedback[p->entindex()];
 f.serial=p->edict()->serialnumber;f.type=type;f.raised=raised?1:0;f.start=p->m_vfHeadgearStart;f.steps=0;
 GearThink(p);
}
static void GearRegister(){CVAR_REGISTER(&gearSfxVolume);}
static void GearPrecache(){
 if(!gearVoiceMessage)gearVoiceMessage=REG_USER_MSG("VFHeadVoice",3);
 for(int i=0;i<3;++i)for(int j=0;j<2;++j)PRECACHE_SOUND(const_cast<char*>(vfha::Sounds[i][j]));
 for(int i=0;i<vfha::ClipCount;++i)PRECACHE_SOUND(const_cast<char*>(vfha::Clips[i].path));
 for(int i=0;i<vfha::MuffledCount;++i)PRECACHE_SOUND(const_cast<char*>(vfha::Muffled[i].path));
 ALERT(at_console,"VFHeadgear audio precache: lines=%d sounds=6 muffled=%d\n",vfha::ClipCount,vfha::MuffledCount);
}
static void GearThink(CBasePlayer* p){
 if(!p||p->entindex()<1||p->entindex()>32)return;HeadgearFeedback& f=gearFeedback[p->entindex()];
 if(!f.start)return;float age=gpGlobals->time-f.start;
 if(!p->IsAlive()||p->edict()->serialnumber!=f.serial||p->m_vfHeadgearStart!=f.start||GearType(p)!=f.type||age<0){f.start=0;return;}
 int due=vf::HeadgearFeedbackDue(age,f.steps);
 if(due&1){
  f.steps|=1;const char* sample=vfha::Sounds[vfha::Category(f.type)-1][f.raised];
  float volume=Setting(gearSfxVolume,0,1,.8f);
  if(volume>0)EMIT_SOUND_DYN(p->edict(),CHAN_ITEM,sample,volume,ATTN_NORM,0,PITCH_NORM);
  ALERT(at_console,"VFHeadgear sfx: player=%d type=%d raised=%d sample=%s\n",p->entindex(),f.type,f.raised,sample);
 }
 if(due&2){f.steps|=2;if(!f.raised)GearSpeak(p,f.type);}
 if(age>=vf::HeadgearDuration&&f.steps==3)f.start=0;
}
void VF_HeadgearFeedbackFlush(CBasePlayer* p){GearThink(p);}
static bool GearVoiceCommand(CBasePlayer* p,const char* command){
 if(strcmp(command,"vf_headgear_voice_preview"))return false;
 if(!VF_DeveloperAllowed()||!p->IsAlive()||CMD_ARGC()!=2)return true;
 const char* categories[]={"generic","visor","mask","goggles"};
 for(int i=0;i<4;++i)if(!strcmp(CMD_ARGV(1),categories[i])){GearSpeak(p,GearType(p),i,true);return true;}
 return true;
}
