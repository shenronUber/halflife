#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "vf_modular.h"
#include "../game_shared/vf_modular_layout.h"
#include "../game_shared/vf_tile_rooms.h"
#include "../game_shared/vf_static_brush.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cerrno>
#include <climits>

namespace {
cvar_t seedCvar={"vf_modular_seed","0",FCVAR_SERVER};
cvar_t roomCvar={"vf_tiles_variant","-1",FCVAR_SERVER};
bool RoomMap(){return !strcmp(STRING(gpGlobals->mapname),"vf_tiles");}
bool MapAllowed(){return RoomMap()||!strcmp(STRING(gpGlobals->mapname),"vf_modular");}
}

class CVFModularPiece:public CBaseEntity {
public:
 int role,index,variant;
 void Spawn();void KeyValue(KeyValueData*);void Select(const vfm::Layout&,int seed,int forced);
 int ObjectCaps(){return CBaseEntity::ObjectCaps()&~FCAP_ACROSS_TRANSITION;}
 int Save(CSave&);int Restore(CRestore&);static TYPEDESCRIPTION m_SaveData[];
};
LINK_ENTITY_TO_CLASS(vf_modular_piece,CVFModularPiece);
TYPEDESCRIPTION CVFModularPiece::m_SaveData[]={DEFINE_FIELD(CVFModularPiece,role,FIELD_INTEGER),DEFINE_FIELD(CVFModularPiece,index,FIELD_INTEGER),DEFINE_FIELD(CVFModularPiece,variant,FIELD_INTEGER)};
int CVFModularPiece::Save(CSave& s){return CBaseEntity::Save(s)&&s.WriteFields("VF_MODULAR_PIECE",this,m_SaveData,ARRAYSIZE(m_SaveData));}
int CVFModularPiece::Restore(CRestore& s){return CBaseEntity::Restore(s)&&s.ReadFields("VF_MODULAR_PIECE",this,m_SaveData,ARRAYSIZE(m_SaveData));}
void CVFModularPiece::KeyValue(KeyValueData* k){
 if(!strcmp(k->szKeyName,"vf_role")){role=atoi(k->szValue);k->fHandled=TRUE;}
 else if(!strcmp(k->szKeyName,"vf_index")){index=atoi(k->szValue);k->fHandled=TRUE;}
 else if(!strcmp(k->szKeyName,"vf_variant")){variant=atoi(k->szValue);k->fHandled=TRUE;}
 else CBaseEntity::KeyValue(k);
}
void CVFModularPiece::Spawn(){
 // Static BSP submodels share engine traces and normal entity networking.
 // The engine requires PUSH for BSP solids; the shared immobile tag allows
 // traversal without accepting ordinary moving doors/platforms.
 pev->angles=g_vecZero;pev->movetype=MOVETYPE_PUSH;pev->solid=SOLID_NOT;
 pev->controller[0]=VF_STATIC_BRUSH_TAG_0;pev->controller[1]=VF_STATIC_BRUSH_TAG_1;
 pev->controller[2]=VF_STATIC_BRUSH_TAG_2;pev->controller[3]=VF_STATIC_BRUSH_TAG_3;
 pev->effects|=EF_NODRAW;pev->flags|=FL_WORLDBRUSH;
 SET_MODEL(edict(),STRING(pev->model));UTIL_SetOrigin(pev,pev->origin);
}
void CVFModularPiece::Select(const vfm::Layout& layout,int seed,int forced){
 bool active=RoomMap()?vft::Active(layout,seed,forced,role,index,variant):vfm::Active(layout,role,index,variant);
 pev->solid=active?SOLID_BSP:SOLID_NOT;
 if(active)pev->effects&=~EF_NODRAW;else pev->effects|=EF_NODRAW;
 UTIL_SetOrigin(pev,pev->origin);
}

class CVFModularController:public CBaseEntity {
public:
 int seed,generated,roomVariant;vfm::Layout layout;
 void Spawn(){pev->movetype=MOVETYPE_NONE;pev->solid=SOLID_NOT;roomVariant=-1;}
 void Activate();void Print(CBasePlayer* player=0);
 int ObjectCaps(){return CBaseEntity::ObjectCaps()&~FCAP_ACROSS_TRANSITION;}
 int Save(CSave&);int Restore(CRestore&);static TYPEDESCRIPTION m_SaveData[];
};
LINK_ENTITY_TO_CLASS(vf_modular_controller,CVFModularController);
TYPEDESCRIPTION CVFModularController::m_SaveData[]={DEFINE_FIELD(CVFModularController,seed,FIELD_INTEGER),DEFINE_FIELD(CVFModularController,generated,FIELD_INTEGER),DEFINE_ARRAY(CVFModularController,layout.cell,FIELD_INTEGER,9),DEFINE_FIELD(CVFModularController,layout.modules,FIELD_INTEGER),DEFINE_ARRAY(CVFModularController,layout.link,FIELD_INTEGER,12),DEFINE_ARRAY(CVFModularController,layout.pillar,FIELD_INTEGER,12),DEFINE_ARRAY(CVFModularController,layout.cover,FIELD_INTEGER,9),DEFINE_FIELD(CVFModularController,roomVariant,FIELD_INTEGER)};
int CVFModularController::Save(CSave& s){return CBaseEntity::Save(s)&&s.WriteFields("VF_MODULAR",this,m_SaveData,ARRAYSIZE(m_SaveData));}
int CVFModularController::Restore(CRestore& s){return CBaseEntity::Restore(s)&&s.ReadFields("VF_MODULAR",this,m_SaveData,ARRAYSIZE(m_SaveData));}
void CVFModularController::Activate(){
 if(!MapAllowed())return;
 if(!generated){
  const char* input=CVAR_GET_STRING("vf_modular_seed");char* end=0;errno=0;
  unsigned long requested=strtoul(input,&end,10);
  if(errno||!end||*end||input[0]=='-'||requested>INT_MAX){ALERT(at_console,"VFModular invalid seed; using random seed\n");requested=0;}
  seed=requested?(int)requested:RANDOM_LONG(1,INT_MAX);layout=vfm::Generate((uint32_t)seed,RoomMap()?4:3);
  roomVariant=(int)CVAR_GET_FLOAT("vf_tiles_variant");if(roomVariant<0||roomVariant>=vft::Variants)roomVariant=-1;
  generated=1;
 }
 CBaseEntity* entity=0;
 while((entity=UTIL_FindEntityByClassname(entity,"vf_modular_piece"))!=0)((CVFModularPiece*)entity)->Select(layout,seed,roomVariant);
 Print();
}
void CVFModularController::Print(CBasePlayer* player){
 char line[512];int bridges=0,runs=0,pillars=0,cover=0,joins=0,active=0;
 for(int e=0;e<vfm::Edges;++e){bridges+=layout.link[e]==vfm::Bridge;runs+=layout.link[e]==vfm::WallRun;pillars+=layout.pillar[e];joins+=layout.link[e]==vfm::Internal;}
 if(!RoomMap())for(int c=0;c<vfm::Cells;++c)for(int p=0;p<vfm::Props;++p)cover+=(layout.cover[c]>>p)&1;
 CBaseEntity* entity=0;while((entity=UTIL_FindEntityByClassname(entity,"vf_modular_piece"))!=0)active+=entity->pev->solid==SOLID_BSP;
 snprintf(line,sizeof(line),"VFModular seed=%d cells=%d,%d,%d,%d,%d,%d,%d,%d,%d modules=%d cell_size=%d gap=%d extent=%d bridges=%d wallruns=%d pillars=%d joins=%d covers=%d active=%d\n",seed,layout.cell[0],layout.cell[1],layout.cell[2],layout.cell[3],layout.cell[4],layout.cell[5],layout.cell[6],layout.cell[7],layout.cell[8],layout.modules,vfm::CellSize,vfm::Gap,vfm::Extent,bridges,runs,pillars,joins,cover,active);
 if(player)CLIENT_PRINTF(player->edict(),print_console,line);else ALERT(at_console,"%s",line);
 for(int e=0;e<vfm::Edges;++e){int a,b;vfm::EdgeCells(e,a,b);snprintf(line,sizeof(line),"VFModular edge=%d cells=%d,%d type=%d pillar=%d\n",e,a,b,layout.link[e],layout.pillar[e]);if(player)CLIENT_PRINTF(player->edict(),print_console,line);else ALERT(at_console,"%s",line);}
 if(RoomMap())for(int m=0;m<layout.modules;++m){int mask=0,first=-1;for(int c=0;c<9;++c)if(layout.cell[c]==m){mask|=1<<c;if(first<0)first=c;}
  snprintf(line,sizeof(line),"VFTiles module=%d mask=%d form=%s room=%d forced=%d\n",m,mask,vft::Form(layout,m),vft::Choice(layout,seed,first,roomVariant),roomVariant);
  if(player)CLIENT_PRINTF(player->edict(),print_console,line);else ALERT(at_console,"%s",line);}
}
void VF_ModularInit(){CVAR_REGISTER(&seedCvar);CVAR_REGISTER(&roomCvar);}
bool VF_ModularCommand(CBasePlayer* player,const char* command){
 if(strcmp(command,"vf_modular_info")&&strcmp(command,"vf_modular_check")&&strcmp(command,"vf_tiles_info")&&strcmp(command,"vf_tiles_check"))return false;
 CBaseEntity* entity=MapAllowed()?UTIL_FindEntityByClassname(0,"vf_modular_controller"):0;
 if(!entity)return true;
 CVFModularController* controller=(CVFModularController*)entity;
 if(!strcmp(command,"vf_modular_info")||!strcmp(command,"vf_tiles_info")){controller->Print(player);return true;}
 int mismatches=0,pieces=0;CBaseEntity* piece=0;
 while((piece=UTIL_FindEntityByClassname(piece,"vf_modular_piece"))!=0){
  CVFModularPiece* candidate=(CVFModularPiece*)piece;
  bool expected=RoomMap()?vft::Active(controller->layout,controller->seed,controller->roomVariant,candidate->role,candidate->index,candidate->variant):vfm::Active(controller->layout,candidate->role,candidate->index,candidate->variant);
  if((piece->pev->solid==SOLID_BSP)!=expected||((piece->pev->effects&EF_NODRAW)==0)!=expected||piece->pev->movetype!=MOVETYPE_PUSH)++mismatches;
  ++pieces;
 }
 for(int e=0;e<vfm::Edges;++e){int a,b;vfm::EdgeCells(e,a,b);
  float x=-vfm::Extent/2+(a%3)*vfm::Pitch,y=-vfm::Extent/2+(a/3)*vfm::Pitch;
  Vector center=e<6?Vector(x+vfm::CellSize+vfm::Gap/2,y+vfm::CellSize/2,32):Vector(x+vfm::CellSize/2,y+vfm::CellSize+vfm::Gap/2,32);
  TraceResult floor,wall;UTIL_TraceLine(center,center-Vector(0,0,132),ignore_monsters,player->edict(),&floor);
  center.z=128;Vector end=center+(e<6?Vector(0,-144,0):Vector(-144,0,0));
  UTIL_TraceLine(center,end,ignore_monsters,player->edict(),&wall);
  bool floorHit=floor.flFraction<1,wallHit=wall.flFraction<1;
  if(floorHit!=(controller->layout.link[e]!=vfm::WallRun)||wallHit!=(controller->layout.link[e]==vfm::WallRun))++mismatches;
  char line[160];snprintf(line,sizeof(line),"VFModular trace edge=%d floor=%d wall=%d type=%d\n",e,floorHit,wallHit,controller->layout.link[e]);CLIENT_PRINTF(player->edict(),print_console,line);
 }
 char line[160];snprintf(line,sizeof(line),"VFModular check seed=%d candidates=%d mismatches=%d\n",controller->seed,pieces,mismatches);CLIENT_PRINTF(player->edict(),print_console,line);
 return true;
}
