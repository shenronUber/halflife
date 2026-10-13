#ifndef VF_MAPS_H
#define VF_MAPS_H
void VF_MapsInit();
void VF_MapsClose();
bool VF_MapsOpen();
void VF_MapsDraw();
int VF_MapsKey(int down,int key);
void VF_MapsView(float* angles);
#endif
