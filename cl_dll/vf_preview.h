#ifndef VF_PREVIEW_H
#define VF_PREVIEW_H
void VF_PreviewReset();
float VF_PreviewYaw();
float VF_PreviewZoomValue();
void VF_PreviewRotate(float degrees);
void VF_PreviewZoom(float amount);
bool VF_PreviewDraw(bool weapon,const int variants[3],float x,float y,float width,float height);
bool VF_PreviewSkins(const char* keys[5],int isolate,float x,float y,float width,float height);
bool VF_PreviewAsset(const char* key,float x,float y,float width,float height);
bool VF_PreviewValidateAsset(const char* key);
bool VF_PreviewModules(float x,float y,float w,float h);
#endif
