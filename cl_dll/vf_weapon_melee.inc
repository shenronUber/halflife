#include "../game_shared/vf_weapon_melee.h"
struct MeleeClientState {bool active,crouch;float start;int mount;};
static MeleeClientState meleeClients[33];static bool meleePosed=false,meleeReport=false;
static char meleeRenderedRig[64]={};static int meleeRenderedSequence=-1;
static bool MeleeLocalActive(){cl_entity_t* p=gEngfuncs.GetLocalPlayer();return p&&p->index>0&&p->index<33&&meleeClients[p->index].active&&gEngfuncs.GetClientTime()-meleeClients[p->index].start<vf::MeleeDuration;}
static int MeleeMessage(const char*,int size,void* data){
 if(size!=vf::MeleeMessageSize)return 1;BEGIN_READ(data,size);int id=READ_BYTE(),active=READ_BYTE(),age=READ_SHORT(),mount=READ_BYTE(),crouch=READ_BYTE();
 if(id<1||id>32||active>1||mount>2||crouch>1||age<0||age>1102)return 1;
 MeleeClientState& s=meleeClients[id];s.active=active!=0;s.start=gEngfuncs.GetClientTime()-max(0,age-1)*.001f;s.mount=mount;s.crouch=crouch!=0;
 cl_entity_t* p=gEngfuncs.GetLocalPlayer();if(active&&p&&p->index==id)InspectCancel("melee");
 gEngfuncs.Con_DPrintf("VFMelee received: player=%d active=%d age=%d mount=%d crouch=%d\n",id,active,age,mount,crouch);return 1;
}
static void MeleeCommand(){
 cl_entity_t* p=gEngfuncs.GetLocalPlayer();int id=p?p->index:0;
 if(inspectWeapon!=4||inspectReload||inspectNextAttack>0||VF_CharacterOpen()||gHUD.m_Health.m_iHealth<=0||gEngfuncs.IsSpectateOnly()||
    VF_TR_Phase(traversalState)||(id>0&&id<33&&headgearStates[id].moving)||MeleeLocalActive())return;
 gEngfuncs.pfnServerCmd("vf_melee\n");
}
static void MeleeInfo(){meleeReport=true;}
static bool MeleeAge(int id,float& age){
 if(id<1||id>32)return false;MeleeClientState& s=meleeClients[id];age=gEngfuncs.GetClientTime()-s.start;
 // Reliable messages can arrive ahead of the interpolated entity clock.
 // Hold the first pose during that rewind, like the headgear gesture.
 if(age>=vf::MeleeDuration)s.active=false;age=max(0.f,age);return s.active;
}
static void MeleeView(cl_entity_t* e){
 cl_entity_t* p=gEngfuncs.GetLocalPlayer();int id=p?p->index:0;float age=0;bool active=MeleeAge(id,age);
 bool changed=!e->model||stricmp(e->model->name,"models/v_9mmar.mdl");
 if(active&&(changed||VF_CharacterOpen()||gHUD.m_Health.m_iHealth<=0||VF_TR_Phase(traversalState))){meleeClients[id].active=false;gEngfuncs.pfnServerCmd("vf_melee_cancel\n");active=false;}
 if(active)InspectCancel("melee");
 if(!active&&meleePosed&&e->curstate.framerate==0){e->curstate.sequence=0;e->curstate.frame=0;e->curstate.framerate=1;e->curstate.animtime=gEngfuncs.GetClientTime();e->latched.prevsequence=0;e->latched.prevframe=0;e->latched.prevanimtime=e->curstate.animtime;}
 if(!active){meleeRenderedRig[0]=0;meleeRenderedSequence=-1;}
 meleePosed=false;
 if(meleeReport){gEngfuncs.Con_Printf("VFMelee view: active=%d age=%.3f sequence=%d frame_rate=%.2f rendered_sequence=%d rig=%s\n",active,active?age:0,e->curstate.sequence,e->curstate.framerate,meleeRenderedSequence,meleeRenderedRig[0]?meleeRenderedRig:"none");meleeReport=false;}
}
static void MeleeAssembly(cl_entity_t* e,vf_assembly_t& a,int id,bool view){
 float age=0;if(!MeleeAge(id,age))return;
 // Third-person collision follows entity snapshots, independently of the
 // reliable gesture cue's arrival time. Keep its sequence/frame/clock intact.
 if(!view&&e->player&&e->curstate.vuser4[2]==VF_PLAYER_POSE_MARKER){
  if(!e->model||!strstr(e->model->name,"models/vf_melee/r01_tp"))return;
  strcpy(a.rig,e->model->name);return;
 }
 const char* base=strrchr(a.rig,'/');if(!base||strncmp(base+1,view?"r01_rig":"r01_tp",view?7:6))return;
 char path[64];snprintf(path,sizeof(path),"models/vf_melee/%s",base+1);const char* wanted=view?"vf_melee":meleeClients[id].crouch?"vf_melee_crouch":"vf_melee";
 int count=engine->SequenceInfo(path,0,NULL,0,NULL),sequence=-1;
 for(int i=0;i<count;++i){char name[32];engine->SequenceInfo(path,i,name,sizeof(name),NULL);if(!strcmp(name,wanted)){sequence=i;break;}}
 if(sequence<0)return;strcpy(a.rig,path);
 for(int i=0;view&&i<a.count;++i){
  if(!strcmp(a.parts[i].model,"models/vf_r01/r01_fp_gloves.mdl"))strcpy(a.parts[i].model,"models/vf_melee/melee_gloves.mdl");
  if(!strcmp(a.parts[i].model,"models/vf_r01/r01_fp_sleeves.mdl"))strcpy(a.parts[i].model,"models/vf_melee/melee_sleeves.mdl");
 }
 e->curstate.sequence=sequence;e->curstate.frame=min(255.99f,age*256/vf::MeleeDuration);e->curstate.framerate=0;e->curstate.animtime=gEngfuncs.GetClientTime();
 e->latched.prevsequence=sequence;e->latched.prevframe=e->curstate.frame;e->latched.prevanimtime=e->curstate.animtime;
 if(view){meleePosed=true;strcpy(meleeRenderedRig,path);meleeRenderedSequence=sequence;}
}
