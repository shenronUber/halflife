#ifndef VF_VOICE_SERVER_H
#define VF_VOICE_SERVER_H
class CBasePlayer;
struct entvars_s;
void VF_VoiceRegister();
void VF_VoicePrecache();
void VF_VoiceSpawn(CBasePlayer*);
void VF_VoiceRestore(CBasePlayer*);
void VF_VoiceThink(CBasePlayer*);
bool VF_VoiceSpeak(CBasePlayer*,int event,bool audition=false);
bool VF_VoiceTaunt(CBasePlayer*);
bool VF_VoiceCommand(CBasePlayer*,const char*);
void VF_VoiceDamage(CBasePlayer*,int damageType,float healthBefore,float armorBefore);
void VF_VoiceEffect(CBasePlayer*,int effect);
bool VF_VoiceDeath(CBasePlayer*);
void VF_VoiceKilled(CBasePlayer*,entvars_s* attacker);
class CBaseEntity;
namespace vfv {struct State;}
namespace vfs {struct State;}
bool VF_VoiceEntityDeath(CBaseEntity*,int actor,vfv::State&,const vfs::State&,bool audition=false);
bool VF_VoiceEntity(CBaseEntity*,int actor,vfv::State&,int event);
#endif

