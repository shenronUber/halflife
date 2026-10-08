#ifndef VF_SKINMENU_H
#define VF_SKINMENU_H
void VF_SkinsInit();
void VF_SkinsShow(int page);
void VF_SkinsReset();
void VF_SkinsRefresh();
void VF_SkinsClose();
bool VF_SkinsOpen();
int VF_SkinsKey(int down,int key);
void VF_SkinsView(float* angles);
void VF_SkinsDraw();
bool VF_SkinsPreview(float x,float y,float w,float h);
#endif
