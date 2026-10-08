#ifndef VF_ENGINE_CLIENT_H
#define VF_ENGINE_CLIENT_H
struct cl_entity_s;
void VF_EngineInit();
void VF_EngineReset();
bool VF_EngineAvailable();
void VF_EngineEntity(cl_entity_s* entity,const char* model);
void VF_EngineWeapon(cl_entity_s* entity,int fallbackBody);
bool VF_EnginePreviewSkins(const char* keys[5],int isolate,float yaw,float zoom,float x,float y,float w,float h);
bool VF_EnginePreviewModel(const char* path,int body,bool modular,float yaw,float zoom,float x,float y,float w,float h);
bool VF_EnginePreviewAsset(const char* key,float yaw,float zoom,float x,float y,float w,float h);
void VF_EngineAnimation(int step);
void VF_EnginePause();
const char* VF_EngineAnimationLabel();
bool VF_EngineModulesAvailable();
void VF_EngineModuleCycle(int zone,int step);
int VF_EngineModuleChoice(int zone);
int VF_EngineModuleCount(int zone);
void VF_EngineModuleSelect(int zone,int choice);
const char* VF_EngineModuleOption(int zone,int choice);
const char* VF_EngineModuleName(int zone);
void VF_EngineModuleEquip();
void VF_EngineModuleReset();
bool VF_EngineModulesEquipped();
bool VF_EnginePreviewModules(float yaw,float zoom,float x,float y,float w,float h);
bool VF_EngineLinked();
void VF_EngineSetAppearanceMode(int mode);
bool VF_EnginePreviewEquipment(const int* items,bool weapon,float x,float y,float w,float h,const int* styles=0);
bool VF_EnginePreviewCurrent(bool weapon,float x,float y,float w,float h);
bool VF_EngineValidateModel(const char* path);
bool VF_EnginePreviewReferencePart(const int* items,int slot,float x,float y,float w,float h,const int* styles=0);
#endif
