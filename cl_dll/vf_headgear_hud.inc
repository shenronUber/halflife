// Pre-authored first-person lens textures; included in vf_engine.cpp's private scope.
cvar_t* headgearHud=NULL;
int headgearHudType=0;float headgearHudCover=0;
HSPRITE headgearHudSprites[vfhud::Count]={};
bool headgearHudAttempted[vfhud::Count]={};
struct GearVisionBackup {cl_entity_t* entity;int message,model,fx,amount,effects; color24 color;bool active;};
GearVisionBackup gearVisionBackup[2048];
float HeadgearPlayerCover(int index,int* type=NULL){
 if(index<1||index>32||!players[index].active||players[index].mode){if(type)*type=0;return 0;}
 int kind=EquippedHeadgear(players[index].items);if(type)*type=kind;
 HeadgearState& h=headgearStates[index];float age=gEngfuncs.GetClientTime()-h.start;
 return vf::HeadgearCover(kind,h.raised,age,h.moving&&age<vf::HeadgearDuration);
}
float HeadgearLocalCover(int* type){
 cl_entity_t* local=gEngfuncs.GetLocalPlayer();
 if(!local||cam_thirdperson||gHUD.m_iIntermission||gHUD.m_Health.m_iHealth<=0||g_iUser1||
    !headgearHud||headgearHud->value<=0||VF_CharacterOpen()){*type=0;return 0;}
 return HeadgearPlayerCover(local->index,type);
}
bool HeadgearHudBind(int type){
 if(type<1||type>vfhud::Count||!gEngfuncs.pTriAPI)return false;
 int id=type-1;HSPRITE& sprite=headgearHudSprites[id];bool first=!headgearHudAttempted[id];
 if(first){
  headgearHudAttempted[id]=true;char path[128];
  snprintf(path,sizeof(path),"sprites/vf_headgear_hud/%s.spr",vfhud::assets[id].id);
  sprite=gEngfuncs.pfnSPR_Load(path);
 }
 model_s* model=sprite?const_cast<model_s*>(gEngfuncs.GetSpritePointer(sprite)):NULL;
 bool bound=model&&gEngfuncs.pfnSPR_Frames(sprite)==1&&gEngfuncs.pTriAPI->SpriteTexture(model,0)!=0;
 if(first)gEngfuncs.Con_DPrintf("VFHeadgear texture: type=%d asset=%s loaded=%d\n",type,vfhud::assets[id].id,bound);
 return bound;
}
void HeadgearHudInfo(){
 int type=0;float cover=HeadgearLocalCover(&type);
 gEngfuncs.Con_Printf("VFHeadgear HUD: type=%d cover=%.4f active=%d thirdperson=%d texture=%s loaded=%d\n",
  type,cover,cover>.01f,cam_thirdperson,type>=1&&type<=vfhud::Count?vfhud::assets[type-1].id:"none",
  type>=1&&type<=vfhud::Count&&headgearHudSprites[type-1]!=0);
}
void HeadgearVisionRestore(cl_entity_t* e){
 if(!e||e->index<1||e->index>=2048)return;GearVisionBackup& b=gearVisionBackup[e->index];
 if(b.active&&b.entity==e&&b.model==e->curstate.modelindex&&b.message==e->curstate.messagenum&&
    e->curstate.renderfx==kRenderFxGlowShell&&e->curstate.rendercolor.r==255&&e->curstate.rendercolor.g==118){
  e->curstate.renderfx=b.fx;e->curstate.renderamt=b.amount;e->curstate.effects=b.effects;e->curstate.rendercolor=b.color;
 }
 b.active=false;
}
void HeadgearVisionReset(){
 for(int i=1;i<2048;++i)if(gearVisionBackup[i].active&&gEngfuncs.GetEntityByIndex(i)==gearVisionBackup[i].entity)HeadgearVisionRestore(gearVisionBackup[i].entity);
 memset(gearVisionBackup,0,sizeof(gearVisionBackup));headgearHudType=0;headgearHudCover=0;
 memset(headgearHudSprites,0,sizeof(headgearHudSprites));memset(headgearHudAttempted,0,sizeof(headgearHudAttempted));
}
void HeadgearVisionEntity(cl_entity_t* e){
 if(!e||e->index<1||e->index>=2048)return;HeadgearVisionRestore(e);
 int type=0;float cover=HeadgearLocalCover(&type);cl_entity_t* local=gEngfuncs.GetLocalPlayer();
 if(type!=3||cover<.75f||e==local||(!e->player&&VF_RangeSkin(e->index)<0))return;
 // A client-only warm outline on actually visible actors; no wall penetration.
 GearVisionBackup& b=gearVisionBackup[e->index];b.entity=e;b.message=e->curstate.messagenum;b.model=e->curstate.modelindex;
 b.fx=e->curstate.renderfx;b.amount=e->curstate.renderamt;b.effects=e->curstate.effects;b.color=e->curstate.rendercolor;b.active=true;
 e->curstate.renderfx=kRenderFxGlowShell;e->curstate.renderamt=5;e->curstate.rendercolor.r=255;e->curstate.rendercolor.g=118;e->curstate.rendercolor.b=48;
 // Xash common/const.h: optional client-only fullbright bit (outside stock SDK).
 if(engine)e->curstate.effects|=(1U<<27);
}
void HeadgearScreenDraw(){
 int type=0;float cover=HeadgearLocalCover(&type);headgearHudType=type;headgearHudCover=cover;
 if(cover<.005f||!HeadgearHudBind(type))return;
 // The painting supplies every edge, lens reflection, fastener and obstruction.
 // Only gesture opacity changes at runtime, exactly like the RGBA status decals.
 triangleapi_t* api=gEngfuncs.pTriAPI;
 api->CullFace(TRI_NONE);api->RenderMode(kRenderTransTexture);
 api->Color4fRendermode(1,1,1,cover,kRenderTransAlpha);api->Begin(TRI_QUADS);
 api->TexCoord2f(0,0);api->Vertex3f(0,0,0);
 api->TexCoord2f(1,0);api->Vertex3f((float)ScreenWidth,0,0);
 api->TexCoord2f(1,1);api->Vertex3f((float)ScreenWidth,(float)ScreenHeight,0);
 api->TexCoord2f(0,1);api->Vertex3f(0,(float)ScreenHeight,0);api->End();
 api->Color4f(1,1,1,1);api->CullFace(TRI_FRONT);api->RenderMode(kRenderNormal);
 if(type==4&&gEngfuncs.pEfxAPI){
  dlight_t* light=gEngfuncs.pEfxAPI->CL_AllocDlight(18973);
  if(light){cl_entity_t* local=gEngfuncs.GetLocalPlayer();float height[3]={0,0,28};
   if(gEngfuncs.pEventAPI)gEngfuncs.pEventAPI->EV_LocalPlayerViewheight(height);
   for(int i=0;i<3;++i)light->origin[i]=local->origin[i]+height[i];light->radius=520*cover;light->die=gEngfuncs.GetClientTime()+.08f;
   light->color.r=76;light->color.g=170;light->color.b=101;light->decay=0;light->minlight=0;}
 }
 if(cover>.8f){const char* names[]={"","VISOR / CLOSED","ARMOR / LOCKED","IR / ONLINE","LOW LIGHT / ONLINE","SEAL / CLOSED"};
  vfui::Text(920,618,names[type],type==3?vfui::amber:type==4?vfui::teal:vfui::muted,250);
  vfui::Text(920,642,"H : relever",vfui::muted,250);}
}
