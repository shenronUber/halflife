#include "hud.h"
#include "cl_util.h"
#include "parsemsg.h"
#include "cl_entity.h"
#include "event_api.h"
#include "vf_voice.h"
#include "../game_shared/vf_voice_catalog.h"
#include "../game_shared/vf_death_catalog.h"
#include <cstdio>
#include <cstring>
namespace {
cvar_t* subtitles=0;
int ReceiveDeath(const char*,int size,void* data){
    if(size!=4)return 1;
    BEGIN_READ(data,size);int entity=READ_SHORT(),actor=READ_BYTE(),cause=READ_BYTE();
    int index=vfd::Index(actor,cause);if(entity<1||entity>=2048||index<0)return 1;
    gEngfuncs.Con_DPrintf("VFDeath received: entity=%d actor=%s cause=%s sample=%s\n",entity,vfv::Actors[actor].id,vfd::Causes[cause].id,vfd::Clips[index].path);
    return 1; // audio is already replicated by the native sound channel
}
int Receive(const char*,int size,void* data){
    if(size!=3)return 1;
    BEGIN_READ(data,size);
    int player=READ_BYTE(),actor=READ_BYTE(),line=READ_BYTE();
    if(player<1||player>gEngfuncs.GetMaxClients()||actor>=vfv::ActorCount||line>=vfv::ClipCount)return 1;
    const vfv::Clip& clip=vfv::Clips[line];
    if(clip.actor!=actor||clip.event==vfv::E_death)return 1; // obsolete spoken death packets
    gEngfuncs.Con_DPrintf("VFVoice received: player=%d actor=%s event=%s clip=%d sample=%s\n",
        player,vfv::Actors[actor].id,vfv::Events[clip.event],line,clip.path);
    cl_entity_t* local=gEngfuncs.GetLocalPlayer();
    if(clip.event==vfv::E_respawn){
        if(!local||local->index!=player)return 1;
        // This engine call only plays on this client. Keep gameplay speech on
        // the same local voice channel so injuries/death can interrupt it.
        gEngfuncs.pEventAPI->EV_PlaySound(player,local->origin,CHAN_VOICE,clip.path,.85f,ATTN_NONE,0,PITCH_NORM);
        gEngfuncs.Con_DPrintf("VFVoice private played: player=%d clip=%d\n",player,line);
    }
    if(!subtitles||subtitles->value<=0||!local)return 1;
    if(subtitles->value<2&&local->index!=player)return 1;
    char text[256];snprintf(text,sizeof(text),"%s: %s\n",vfv::Actors[actor].name,clip.text);
    gHUD.m_SayText.SayTextPrint(text,static_cast<int>(strlen(text)),player);
    return 1;
}
}
void VF_VoiceInit(){
    subtitles=gEngfuncs.pfnRegisterVariable("vf_voice_subtitles","1",FCVAR_ARCHIVE);
    gEngfuncs.pfnHookUserMsg("VFVoice",Receive);
    gEngfuncs.pfnHookUserMsg("VFDeath",ReceiveDeath);
}

