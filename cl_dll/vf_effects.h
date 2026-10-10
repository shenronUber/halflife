#ifndef VF_EFFECTS_H
#define VF_EFFECTS_H
void VF_EffectsInit();
void VF_EffectsReset();
void VF_EffectsEntities();
void VF_EffectsWorld();
void VF_EffectsGuide();
void VF_EffectsScreen();
void VF_EffectsHud();
void VF_EffectsTargetDraw(int effect,const float* origin);
struct vf_fx_particle_t {int texture,pattern;float origin[3],end[3],color[3],size,alpha;bool line,blood;};
void VF_EffectsParticleDraw(const vf_fx_particle_t* particles,int count);
#endif
