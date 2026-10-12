// Independent inspection carriers; no shared animation bank or camera changes.
static vf::InspectState inspectState;
static int inspectWeapon=0,inspectButtons=0;
static bool inspectReload=false,inspectReport=false;
static float inspectNextAttack=0;
static bool inspectPosed=false;
static bool InspectBusy(){
 cl_entity_t* local=gEngfuncs.GetLocalPlayer();int id=local?local->index:0;
 return inspectWeapon!=4||inspectReload||inspectNextAttack>0||
  (inspectButtons&(IN_ATTACK|IN_ATTACK2|IN_RELOAD))||VF_TR_Phase(traversalState)!=VF_TR_NORMAL||
  VF_CharacterOpen()||gHUD.m_Health.m_iHealth<=0||gEngfuncs.IsSpectateOnly()||CL_IsThirdPerson()||
  (id>0&&id<=32&&headgearStates[id].moving);
}
static void InspectCancel(const char* reason){
 if(inspectState.active)gEngfuncs.Con_DPrintf("VFInspect cancel: %s\n",reason);
 inspectState.Reset();
}
static void InspectCommand(){
 cl_entity_t* e=gEngfuncs.GetViewModel();
 if(!e||!e->model||stricmp(e->model->name,"models/v_9mmar.mdl"))return;
 if(inspectState.Begin(gEngfuncs.GetClientTime(),inspectWeapon,InspectBusy()))
  gEngfuncs.Con_DPrintf("VFInspect start: weapon=%d duration=%.2f\n",inspectWeapon,vf::InspectDuration);
}
static void InspectInfo(){inspectReport=true;}
static void InspectView(cl_entity_t* e){
 const float now=gEngfuncs.GetClientTime();const bool wasActive=inspectState.active;
 if(!inspectState.Update(now,inspectWeapon,InspectBusy())&&wasActive)
  gEngfuncs.Con_DPrintf("VFInspect end: elapsed=%.3f busy=%d\n",now-inspectState.start,InspectBusy());
 // A new shoot/reload animation already has framerate=1. Restore only our
 // frozen inspection frame; never reset an animation started by prediction.
 if(!inspectState.active&&inspectPosed&&e->curstate.framerate==0){
  e->curstate.frame=0;e->curstate.framerate=1;e->curstate.animtime=now;
  e->latched.prevsequence=e->curstate.sequence;e->latched.prevframe=0;e->latched.prevanimtime=now;
 }
 inspectPosed=false;
 if(inspectReport){
  const float elapsed=inspectState.active?now-inspectState.start:0;
  const vf::InspectPose pose=vf::InspectSample(elapsed);
  gEngfuncs.Con_Printf("VFInspect pose: active=%d elapsed=%.3f pitch=%.3f yaw=%.3f roll=%.3f weapon=%d reload=%d frame_rate=%.3f\n",
   inspectState.active,elapsed,pose.pitch,pose.yaw,pose.roll,inspectWeapon,inspectReload,e->curstate.framerate);
  inspectReport=false;
 }
}
static void InspectAssembly(cl_entity_t* e,vf_assembly_t& a){
 if(!inspectState.active)return;
 if(strncmp(a.rig,"models/vf_r01/r01_rig",strlen("models/vf_r01/r01_rig"))){InspectCancel("unsupported rig");return;}
 char path[64];snprintf(path,sizeof(path),"models/vf_inspect/%s",strrchr(a.rig,'/')+1);
 if(engine->SequenceInfo(path,0,NULL,0,NULL)!=1){InspectCancel("inspection carrier unavailable");return;}
 strcpy(a.rig,path);e->curstate.sequence=0;
 for(int i=0;i<a.count;++i){
  if(!strcmp(a.parts[i].model,"models/vf_r01/r01_fp_gloves.mdl"))strcpy(a.parts[i].model,"models/vf_inspect/inspect_gloves.mdl");
  if(!strcmp(a.parts[i].model,"models/vf_r01/r01_fp_sleeves.mdl"))strcpy(a.parts[i].model,"models/vf_inspect/inspect_sleeves.mdl");
 }
 inspectPosed=true;
 e->curstate.frame=(std::max)(0.f,(std::min)(255.99f,(gEngfuncs.GetClientTime()-inspectState.start)/vf::InspectDuration*256));
 e->curstate.framerate=0;e->curstate.animtime=gEngfuncs.GetClientTime();
 e->latched.prevsequence=0;e->latched.prevframe=e->curstate.frame;e->latched.prevanimtime=e->curstate.animtime;
}
