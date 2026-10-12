#include "../game_shared/vf_headgear.h"
struct HeadgearState {bool raised,moving;float start;int sequence;float frame;bool frozen;};
static HeadgearState headgearStates[33];
static bool headgearReport=false;
static int HeadgearMessage(const char*,int size,void* data) {
 if(size!=vf::HeadgearMessageSize)return 1;BEGIN_READ(data,size);
 int index=READ_BYTE(),raised=READ_BYTE(),elapsed=READ_SHORT();
 if(index<1||index>32||raised>1||elapsed<0||elapsed>(int)(vf::HeadgearDuration*1000)+1)return 1;
 HeadgearState& h=headgearStates[index];h.raised=raised!=0;h.moving=elapsed!=0;h.start=gEngfuncs.GetClientTime()-(elapsed?elapsed-1:0)*.001f;h.frozen=false;
 gEngfuncs.Con_DPrintf("VFHeadgear state: player=%d raised=%d elapsed=%d\n",index,raised,elapsed);return 1;
}
static void HeadgearToggle() {gEngfuncs.pfnServerCmd("vf_headgear_toggle\n");}
static void HeadgearInfo() {headgearReport=true;}
static float HeadgearPhase(int index) {
 HeadgearState& h=headgearStates[index];float phase=(gEngfuncs.GetClientTime()-h.start)/vf::HeadgearDuration;
 // Message parsing can precede the interpolated render clock by a frame.
 // Clamp that small rewind; cancelling it would skip the first raise gesture.
 if(phase>=1)h.moving=false;return vf::HeadgearClamp(phase);
}
static int EquippedHeadgear(const int* items) {
 if(!items||!equipment.valid)return 0;int id=items[vf::HelmetSlot];
 return id>0&&id<equipment.count&&equipment.items[id].slot==vf::HelmetSlot?equipment.items[id].visual:0;
}
static void AddEquippedHeadgear(vf_assembly_t& a,const int* items,int index=0,bool view=false,const cl_entity_t* body=NULL) {
 int type=EquippedHeadgear(items);
 float pose=0,phase=0;bool moving=false;
 if(index>0&&index<=32){phase=HeadgearPhase(index);HeadgearState& h=headgearStates[index];moving=h.moving;pose=moving?vf::HeadgearPose(phase,h.raised):h.raised?1.f:0.f;}
 if(body&&body->player&&body->curstate.vuser4[2]==VF_PLAYER_POSE_MARKER){
  type=VF_PoseGearType(body->curstate.vuser2[1]);
  phase=vf::HeadgearClamp(VF_PoseGearPhase(body->curstate.vuser2[1])+
   (std::max)(0.f,gEngfuncs.GetClientTime()-body->curstate.vuser2[2])/vf::HeadgearDuration);
  moving=phase<1;pose=vf::HeadgearPose(phase,VF_PoseGearRaised(body->curstate.vuser2[1]));
 }
 if(type<=0||type>vf::HeadgearTypes)return;
 if(moving){a.headgear_type=type;a.headgear_phase=phase;}
 if(view)return; // The first-person gesture uses its arm rig; face equipment stays on the world body.
 if(a.count>=VF_MAX_PARTS)return;
 // An equipped item wins over the historical local workshop trial.
 for(int n=0;n<a.count;++n)if(!strcmp(a.parts[n].model,headgearModel)){a.parts[n]=a.parts[--a.count];break;}
 vf_part_t& p=a.parts[a.count++];memset(&p,0,sizeof(p));strcpy(p.model,headgearModel);p.mode=VF_PART_MERGE;p.body=vf::HeadgearBody(type);
 float pivot[3],shift[3],angle;vf::HeadgearTransform(type,pose,pivot,&angle,shift);
 // Source X is head-local Z. Convert pivot and stow translation into the
 // immutable persona head bind basis, shared by all fitted skin families.
 float dy=pivot[1]+.611241f,dz=pivot[2]-59.668064f;
 float x=-.182435f*dy+.983218f*dz,y=-.983218f*dy-.182435f*dz;
 float c=cosf(angle*3.14159265f/180),s=sinf(angle*3.14159265f/180);
 p.angles[1]=angle;p.offset[0]=x-c*x+s*y-.182435f*shift[1]+.983218f*shift[2];
 p.offset[1]=y-s*x-c*y-.983218f*shift[1]-.182435f*shift[2];p.offset[2]=shift[0];
 if(headgearReport){gEngfuncs.Con_Printf("VFHeadgear render: player=%d type=%d moving=%d phase=%.4f pose=%.4f view=%d\n",index,type,moving,phase,pose,view);headgearReport=false;}
}
static void FreezeHeadgearWeapon(cl_entity_t* e,int index) {
 if(index<1||index>32||!EquippedHeadgear(players[index].items))return;
 HeadgearPhase(index);HeadgearState& h=headgearStates[index];if(!h.moving){if(h.frozen){e->curstate.framerate=1;h.frozen=false;}return;}
 if(!h.frozen){h.sequence=e->curstate.sequence;h.frame=e->curstate.frame;h.frozen=true;}
 e->curstate.sequence=h.sequence;e->curstate.frame=h.frame;e->curstate.framerate=0;e->curstate.animtime=gEngfuncs.GetClientTime();
 e->latched.prevsequence=h.sequence;e->latched.prevframe=h.frame;e->latched.prevanimtime=e->curstate.animtime;
}
