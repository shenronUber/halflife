#ifndef VF_CHARACTER_H
#define VF_CHARACTER_H
void VF_CharacterInit();
void VF_CharacterShow(int page);
void VF_CharacterGameplay(int page);
void VF_CharacterClose();
void VF_CharacterReset();
void VF_CharacterDraw();
bool VF_CharacterOpen();
int VF_CharacterKey(int down,int key);
void VF_CharacterView(float* angles);
void VF_CharacterUpdateModels();
void VF_CharacterReference(int variant);
#endif
