#ifndef VF_RANGE_SERVER_H
#define VF_RANGE_SERVER_H
class CBasePlayer;
void VF_RangePrecache();
void VF_RangeSync(CBasePlayer*);
void VF_RangeHear(CBasePlayer*,float duration,float radius,float window);
bool VF_RangeCommand(CBasePlayer*,const char*);
#endif
