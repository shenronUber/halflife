#ifndef VF_STATUS_SERVER_H
#define VF_STATUS_SERVER_H
class CBasePlayer;
void VF_StatusPrecache();
void VF_StatusReset(CBasePlayer*);
void VF_StatusClear(CBasePlayer*);
void VF_StatusThink(CBasePlayer*);
void VF_StatusSync(CBasePlayer*);
bool VF_StatusCommand(CBasePlayer*,const char*);
// Normal gameplay and developer scenarios share this server-authoritative path.
int VF_ApplyPlayerEffect(CBasePlayer*,int effect,float seconds=6.0f,bool cue=true);
void VF_ElementalPlayerHit(CBasePlayer*,int effect);
#endif
