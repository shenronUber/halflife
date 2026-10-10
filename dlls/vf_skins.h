#ifndef VF_SKINS_H
#define VF_SKINS_H
class CBasePlayer;
void VF_InitSkins();
void VF_DeathPlayerSkins(CBasePlayer*,int*);
void VF_PreparePlayerSave(CBasePlayer* player);
bool VF_ApplyPlayerModel(CBasePlayer* player);
void VF_SyncPlayer(CBasePlayer* player,bool spawn=false);
void VF_BroadcastPlayer(CBasePlayer* player,bool active=true);
void VF_PrecacheSkins();
bool VF_SkinCommand(CBasePlayer* player,const char* command);
#endif
