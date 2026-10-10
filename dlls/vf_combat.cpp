#include "extdll.h"
#include "util.h"
#include "cbase.h"
#include "player.h"
#include "weapons.h"
#include "monsters.h"
#include "gamerules.h"
#include "func_break.h"
#include "studio.h"
#include "vf_equipment.h"
#include "vf_combat.h"
#include "vf_status.h"
#include "../game_shared/vf_loadout.h"
#include "pm_materials.h"
#include <cstdio>
#include <cstring>
#include <cmath>
namespace {
static_assert(BULLET_NONE==0&&BULLET_PLAYER_MP5==2&&BULLET_PLAYER_BUCKSHOT==4&&BULLET_PLAYER_CROWBAR==5&&BULLET_MONSTER_12MM==8,"Native projectile catalog must match the SDK bullet enumeration");
const VF_ProjectileTraceScope* shot=NULL;
cvar_t impactDebug={"vf_impact_debug","0",FCVAR_SERVER};
struct Layer {int material,slot;float thickness;char item[80];};
struct Impact {
 bool valid,player,localized;int attacker,victim,hitgroup,bits,bullet,weapon,layerCount;
 vfc::Region region;vfc::ProjectileNature nature;float raw,multiplier,baseline,distance,mass,speed;
 Vector point,normal,direction;char ammo[80],projectile[80],texture[64],profile[40];Layer layers[5];
};
Impact incoming[33],outgoing[33];
int PlayerIndex(entvars_t* vars){CBaseEntity* e=vars?CBaseEntity::Instance(vars):NULL;return e&&e->IsPlayer()?e->entindex():0;}
vfc::Multipliers Multipliers(){vfc::Multipliers m={gSkillData.plrHead,gSkillData.plrChest,gSkillData.plrStomach,gSkillData.plrArm,gSkillData.plrLeg};return m;}
vfc::ProjectileNature Nature(int bits){
 if(bits&DMG_BLAST)return vfc::Explosive;if(bits&(DMG_BURN|DMG_SLOWBURN))return vfc::Thermal;
 if(bits&DMG_SHOCK)return vfc::Electrical;if(bits&(DMG_ACID|DMG_POISON|DMG_NERVEGAS))return vfc::Chemical;
 if(bits&DMG_BULLET)return vfc::Kinetic;if(bits&(DMG_CLUB|DMG_SLASH|DMG_CRUSH))return vfc::Blunt;return vfc::NatureUnknown;
}
void Projectile(Impact& r,entvars_t* attacker,int bits){
 r.attacker=PlayerIndex(attacker);r.bits=bits;r.bullet=-1;r.weapon=-1;r.mass=r.speed=-1;r.distance=-1;r.nature=Nature(bits);
 if(!shot)return;
 r.bullet=shot->bulletType;r.distance=(r.point-shot->source).Length();
 if(r.bullet>=0&&r.bullet<vfc::ProjectileCount){const vfc::ProjectileDefinition& p=vfc::projectiles[r.bullet];if(p.nature!=vfc::NatureUnknown)r.nature=p.nature;r.mass=p.massKg;r.speed=p.speedMS;}
 CBaseEntity* e=shot->attacker?CBaseEntity::Instance(shot->attacker):NULL;
 if(e&&e->IsPlayer()){
  CBasePlayer* p=(CBasePlayer*)e;CBasePlayerWeapon* w=p->m_pActiveItem?(CBasePlayerWeapon*)p->m_pActiveItem->GetWeaponPtr():NULL;r.weapon=w?w->m_iId:-1;
  // Inventory projectile objects apply only to the instant MP5 prototype.
  // Other guns and asynchronous arrivals must not inherit its equipped pieces.
  if(r.weapon==WEAPON_MP5&&(r.bullet==BULLET_PLAYER_MP5||r.bullet==BULLET_MONSTER_MP5)){
   const vf::Item* a=VF_EquippedItem(p,vfc::Slot_ammo);const vf::Item* q=VF_EquippedItem(p,vfc::Slot_projectile);
   if(a)snprintf(r.ammo,sizeof(r.ammo),"%s",a->id);if(q)snprintf(r.projectile,sizeof(r.projectile),"%s",q->id);
  }
 }
}
void AddLayer(Impact& r,int material,float thickness,int slot,const char* item){
 if(r.layerCount>=5)return;Layer& l=r.layers[r.layerCount++];l.material=material;l.thickness=thickness;l.slot=slot;snprintf(l.item,sizeof(l.item),"%s",item?item:"");
}
void Print(const Impact& r,edict_t* to){
 if(!r.valid){if(to)CLIENT_PRINTF(to,print_console,"VFImpact none\n");return;}
 char line[700];snprintf(line,sizeof(line),"VFImpact victim=%d attacker=%d region=%s group=%d nature=%s bullet=%d weapon=%d raw=%.3f multiplier=%.3f baseline=%.3f layers=%d localized=%d distance=%.3f profile=%s mode=identify_only\n",r.victim,r.attacker,vfc::RegionKey(r.region),r.hitgroup,vfc::NatureKey(r.nature),r.bullet,r.weapon,r.raw,r.multiplier,r.baseline,r.layerCount,r.localized,r.distance,r.profile);
 if(to)CLIENT_PRINTF(to,print_console,line);else ALERT(at_console,"%s",line);
 snprintf(line,sizeof(line),"VFImpactGeometry point=%.3f,%.3f,%.3f normal=%.3f,%.3f,%.3f direction=%.3f,%.3f,%.3f\n",r.point.x,r.point.y,r.point.z,r.normal.x,r.normal.y,r.normal.z,r.direction.x,r.direction.y,r.direction.z);
 if(to)CLIENT_PRINTF(to,print_console,line);else ALERT(at_console,"%s",line);
 snprintf(line,sizeof(line),"VFProjectile ammo=%s projectile=%s mass_kg=%.4f speed_m_s=%.3f texture=%s\n",r.ammo[0]?r.ammo:"unknown",r.projectile[0]?r.projectile:"unknown",r.mass,r.speed,r.texture[0]?r.texture:"none");
 if(to)CLIENT_PRINTF(to,print_console,line);else ALERT(at_console,"%s",line);
 for(int i=0;i<r.layerCount;++i){const Layer& l=r.layers[i];const vfc::Material& m=vfc::materials[l.material];
  snprintf(line,sizeof(line),"VFMaterial layer=%d id=%s family=%s density_kg_m3=%.1f thickness_mm=%.3f resistance_j_mm=%.3f calibrated=%d slot=%d item=%s coverage=%s\n",i,m.id,m.family,m.densityKgM3,l.thickness,m.resistanceJPerMm,m.calibrated,l.slot,l.item[0]?l.item:"none",r.player?"hitgroup_proxy":"surface_class");
  if(to)CLIENT_PRINTF(to,print_console,line);else ALERT(at_console,"%s",line);
 }
}
void Store(const Impact& r){if(r.victim>0&&r.victim<=32)incoming[r.victim]=r;if(r.attacker>0&&r.attacker<=32)outgoing[r.attacker]=r;if(impactDebug.value)Print(r,NULL);}
int BreakableMaterial(int m){switch(m){case matGlass:case matUnbreakableGlass:return vfc::Mat_glass;case matWood:return vfc::Mat_wood;case matMetal:return vfc::Mat_steel;case matFlesh:return vfc::Mat_flesh;case matCinderBlock:case matRocks:return vfc::Mat_concrete;case matCeilingTile:return vfc::Mat_ceramic;case matComputer:return vfc::Mat_composite;default:return vfc::Mat_unknown;}}
void SurfaceImpact(const TraceResult& trace,float damage){
 CBaseEntity* e=CBaseEntity::Instance(trace.pHit);if(e&&e->IsPlayer())return;
 Impact r={};r.valid=true;r.point=trace.vecEndPos;r.normal=trace.vecPlaneNormal;r.direction=(shot->end-shot->source).Normalize();r.hitgroup=trace.iHitgroup;r.region=vfc::HitRegion(trace.iHitgroup);r.raw=damage;r.multiplier=1;r.baseline=damage;
 Projectile(r,shot->attacker,shot->bulletType==BULLET_NONE?DMG_CLUB:DMG_BULLET);
 int material=vfc::Mat_unknown;
 if(e&&(FClassnameIs(e->pev,"func_breakable")||FClassnameIs(e->pev,"func_pushable")))material=BreakableMaterial(((CBreakable*)e)->m_Material);
 else if(e&&e->Classify()!=CLASS_NONE)material=e->Classify()==CLASS_MACHINE?vfc::Mat_steel:vfc::Mat_flesh;
 else {
  const char* texture=TRACE_TEXTURE(trace.pHit?trace.pHit:ENT(0),shot->source,shot->end);
  if(texture){snprintf(r.texture,sizeof(r.texture),"%.63s",texture);const char* t=texture;if((*t=='+'||*t=='-')&&strlen(t)>2)t+=2;if(*t=='{'||*t=='!'||*t=='~'||*t==' ')++t;
   char name[64];snprintf(name,sizeof(name),"%.63s",t);name[CBTEXTURENAMEMAX-1]=0;material=vfc::TextureMaterial(TEXTURETYPE_Find(name));}
 }
 snprintf(r.profile,sizeof(r.profile),"%s",vfc::materials[material].id);AddLayer(r,material,-1,-1,NULL);Store(r);
}
float BulletDamage(int type){switch(type){case BULLET_PLAYER_9MM:return gSkillData.plrDmg9MM;case BULLET_PLAYER_MP5:return gSkillData.plrDmgMP5;case BULLET_PLAYER_357:return gSkillData.plrDmg357;case BULLET_PLAYER_BUCKSHOT:return gSkillData.plrDmgBuckshot;case BULLET_MONSTER_9MM:return gSkillData.monDmg9MM;case BULLET_MONSTER_MP5:return gSkillData.monDmgMP5;case BULLET_MONSTER_12MM:return gSkillData.monDmg12MM;case BULLET_NONE:return 50;default:return 0;}}
Vector BonePoint(CBasePlayer* p,int bone,const Vector& local){Vector org,ang,f,r,u;GET_BONE_POSITION(p->edict(),bone,org,ang);UTIL_MakeVectorsPrivate(ang,f,r,u);return org+f*local.x-r*local.y+u*local.z;}
bool RegionTrace(CBasePlayer* p,int group,TraceResult& result,Vector& source,int preferred=-1){
 studiohdr_t* h=(studiohdr_t*)GET_MODEL_PTR(p->edict());if(!h||h->numhitboxes<0||h->numhitboxes>128)return false;
 mstudiobbox_t* boxes=(mstudiobbox_t*)((byte*)h+h->hitboxindex);
 for(int i=0;i<h->numhitboxes;++i)if(boxes[i].group==group&&(preferred<0||preferred==i)){const mstudiobbox_t& b=boxes[i];Vector center=(Vector(b.bbmin)+Vector(b.bbmax))*.5f;Vector end=BonePoint(p,b.bone,center);
  for(int axis=0;axis<3;++axis)for(int sign=-1;sign<=1;sign+=2){Vector start=center;start[axis]=(sign<0?b.bbmin[axis]:b.bbmax[axis])+sign*18.0f;source=BonePoint(p,b.bone,start);
   UTIL_TraceLine(source,end,dont_ignore_monsters,NULL,&result);if(result.pHit==p->edict()&&result.iHitgroup==group&&!result.fStartSolid)return true;
  }
 }
 return false;
}
void Hitboxes(CBasePlayer* p){
 studiohdr_t* h=(studiohdr_t*)GET_MODEL_PTR(p->edict());if(!h)return;char line[256];snprintf(line,sizeof(line),"VFHitboxes player=%d model=%s boxes=%d sequence=%d frame=%.2f clienttrace=%.3f\n",p->entindex(),STRING(p->pev->model),h->numhitboxes,p->pev->sequence,p->pev->frame,CVAR_GET_FLOAT("sv_clienttrace"));CLIENT_PRINTF(p->edict(),print_console,line);
 mstudiobbox_t* boxes=(mstudiobbox_t*)((byte*)h+h->hitboxindex);mstudiobone_t* bones=(mstudiobone_t*)((byte*)h+h->boneindex);
 for(int i=0;i<h->numhitboxes;++i){Vector center=BonePoint(p,boxes[i].bone,(Vector(boxes[i].bbmin)+Vector(boxes[i].bbmax))*.5f);snprintf(line,sizeof(line),"VFHitbox index=%d group=%d bone=%s center=%.3f,%.3f,%.3f\n",i,boxes[i].group,bones[boxes[i].bone].name,center.x,center.y,center.z);CLIENT_PRINTF(p->edict(),print_console,line);}
}
void HitboxProbe(CBasePlayer* p){
 if(!VF_DeveloperAllowed())return;
 studiohdr_t* h=(studiohdr_t*)GET_MODEL_PTR(p->edict());if(!h)return;
 mstudiobbox_t* boxes=(mstudiobbox_t*)((byte*)h+h->hitboxindex);
 mstudiobone_t* bones=(mstudiobone_t*)((byte*)h+h->boneindex);
 for(int i=0;i<h->numhitboxes;++i)if(strstr(bones[boxes[i].bone].name,"L Hand")){
  TraceResult trace={};Vector source;bool found=RegionTrace(p,boxes[i].group,trace,source,i);char line[240];
  snprintf(line,sizeof(line),"VFHitboxProbe index=%d group=%d found=%d point=%.3f,%.3f,%.3f sequence=%d frame=%.2f\n",i,boxes[i].group,found,trace.vecEndPos.x,trace.vecEndPos.y,trace.vecEndPos.z,p->pev->sequence,p->pev->frame);
  CLIENT_PRINTF(p->edict(),print_console,line);break;
 }
}
void Selftest(CBasePlayer* p){
 if(!VF_DeveloperAllowed()||!CVAR_GET_FLOAT("sv_cheats")||!p->IsAlive())return;
 float health=p->pev->health,armor=p->pev->armorvalue;int flags=p->pev->flags;float lastAmount=p->m_lastDamageAmount;int lastGroup=p->m_LastHitGroup;
 Vector velocity=p->pev->velocity,baseVelocity=p->pev->basevelocity,punch=p->pev->punchangle;
 float dmgTake=p->pev->dmg_take,dmgSave=p->pev->dmg_save;int damageBits=p->m_bitsDamageType,hudBits=p->m_bitsHUDDamage;
 vfs::State status=p->m_vfStatus;vfv::State voice=p->m_vfVoiceState;
 p->pev->flags&=~FL_GODMODE;int passed=0;char line[260];
 for(int group=1;group<=7;++group){TraceResult trace;Vector source;if(!RegionTrace(p,group,trace,source)){snprintf(line,sizeof(line),"VFCombatTest missing_group=%d\n",group);CLIENT_PRINTF(p->edict(),print_console,line);continue;}
  p->pev->health=1000;p->pev->armorvalue=0;float baseline=vfc::LegacyTraceDamage(10,vfc::HitRegion(group),Multipliers());
  ClearMultiDamage();{VF_ProjectileTraceScope scope(BULLET_PLAYER_MP5,p->pev,source,trace.vecEndPos,trace,10,false);p->TraceAttack(p->pev,10,(trace.vecEndPos-source).Normalize(),&trace,DMG_BULLET);}ApplyMultiDamage(p->pev,p->pev);
  float lost=1000-p->pev->health;bool ok=fabsf(lost-(int)baseline)<.001f;if(ok)passed++;
  snprintf(line,sizeof(line),"VFCombatTest group=%d raw=10 baseline=%.3f health_loss=%.3f passed=%d\n",group,baseline,lost,ok);CLIENT_PRINTF(p->edict(),print_console,line);
 }
 TraceResult trace;Vector source;bool armorOK=false,scopeOK=false;
 if(RegionTrace(p,HITGROUP_CHEST,trace,source)){
  p->pev->health=1000;p->pev->armorvalue=50;float raw=vfc::LegacyTraceDamage(10,vfc::Chest,Multipliers());ClearMultiDamage();
  {VF_ProjectileTraceScope scope(BULLET_PLAYER_MP5,p->pev,source,trace.vecEndPos,trace,10,false);p->TraceAttack(p->pev,10,(trace.vecEndPos-source).Normalize(),&trace,DMG_BULLET);}ApplyMultiDamage(p->pev,p->pev);
  armorOK=fabsf(1000-p->pev->health-(int)(raw*.2f))<.001f&&fabsf(p->pev->armorvalue-(50-raw*.8f*.5f))<.001f;
  p->pev->health=1000;p->pev->armorvalue=0;ClearMultiDamage();p->TraceAttack(p->pev,1,(trace.vecEndPos-source).Normalize(),&trace,DMG_CLUB);ApplyMultiDamage(p->pev,p->pev);
  const Impact& r=incoming[p->entindex()];scopeOK=r.bullet==-1&&r.weapon==-1&&!r.ammo[0]&&!r.projectile[0]&&r.nature==vfc::Blunt;
 }
 p->pev->health=health;p->pev->armorvalue=armor;p->pev->flags=flags;p->m_lastDamageAmount=lastAmount;p->m_LastHitGroup=lastGroup;
 p->pev->velocity=velocity;p->pev->basevelocity=baseVelocity;p->pev->punchangle=punch;p->pev->dmg_take=dmgTake;p->pev->dmg_save=dmgSave;
 p->m_bitsDamageType=damageBits;p->m_bitsHUDDamage=hudBits;p->m_vfStatus=status;p->m_vfVoiceState=voice;VF_StatusSync(p);
 snprintf(line,sizeof(line),"VFCombatTest summary groups=%d/7 armor_unchanged=%d no_projectile_leak=%d\n",passed,armorOK,scopeOK);CLIENT_PRINTF(p->edict(),print_console,line);
}
}
VF_ProjectileTraceScope::VF_ProjectileTraceScope(int bullet,entvars_t* from,const Vector& src,const Vector& destination,const TraceResult& trace,float baseDamage,bool allowProc):previous(shot),bulletType(bullet),attacker(from),source(src),end(destination){element=-1;CBaseEntity* e=from?CBaseEntity::Instance(from):NULL;
 if(allowProc&&bullet!=BULLET_NONE&&bullet!=BULLET_PLAYER_CROWBAR){element=vfs::S_kinetic;if(e&&e->IsPlayer()&&bullet==BULLET_PLAYER_MP5){int code=VF_WeaponFXCode((CBasePlayer*)e);if(code>0&&code<=8)element=code-1;}}
 shot=this;SurfaceImpact(trace,baseDamage?baseDamage:BulletDamage(bullet));}
int VF_CurrentShotElement(){return shot?shot->element:-1;}
VF_ProjectileTraceScope::~VF_ProjectileTraceScope(){shot=previous;}
void VF_CombatInit(){CVAR_REGISTER(&impactDebug);}
void VF_CombatReset(){shot=NULL;memset(incoming,0,sizeof(incoming));memset(outgoing,0,sizeof(outgoing));}
void VF_CombatClear(CBasePlayer* p){if(p&&p->entindex()>0&&p->entindex()<=32){incoming[p->entindex()]=Impact();outgoing[p->entindex()]=Impact();}}
float VF_PlayerTraceDamage(CBasePlayer* victim,entvars_t* attacker,float raw,const Vector& direction,const TraceResult& trace,int bits){
 Impact r={};r.valid=r.player=true;r.victim=victim->entindex();r.hitgroup=trace.iHitgroup;r.region=vfc::HitRegion(r.hitgroup);r.localized=r.region>=vfc::Head&&r.region<=vfc::RightLeg;r.point=trace.vecEndPos;r.normal=trace.vecPlaneNormal;r.direction=direction;r.raw=raw;r.multiplier=vfc::LocationMultiplier(r.region,Multipliers());r.baseline=vfc::LegacyTraceDamage(raw,r.region,Multipliers());Projectile(r,attacker,bits);
 int slot=vfc::SurfaceSlot(r.region);const vf::Item* item=slot>=0?VF_EquippedItem(victim,slot):NULL;int profile=item&&item->appearance[0]?vfc::ItemProfile(slot,item->id,vf::ItemModel(*item)):vfc::Profile_unknown;snprintf(r.profile,sizeof(r.profile),"%s",vfc::profiles[profile].id);
 const vfc::Profile& definition=vfc::profiles[profile];for(int i=0;i<definition.count;++i)AddLayer(r,definition.layers[i].material,definition.layers[i].thicknessMm,slot,item?item->id:NULL);
 if(r.region!=vfc::Unknown)AddLayer(r,vfc::Mat_flesh,-1,-1,NULL);Store(r);
 if(raw>0&&(bits&DMG_BULLET)&&g_pGameRules->FPlayerCanTakeDamage(victim,CBaseEntity::Instance(attacker)))VF_ElementalPlayerHit(victim,VF_CurrentShotElement());
 return r.baseline;
}
bool VF_CombatCommand(CBasePlayer* p,const char* cmd){
 if(!strcmp(cmd,"vf_impact_info")){Print(CMD_ARGC()>1&&!strcmp(CMD_ARGV(1),"incoming")?incoming[p->entindex()]:outgoing[p->entindex()],p->edict());return true;}
 if(!strcmp(cmd,"vf_hitbox_info")){Hitboxes(p);return true;}
 if(!strcmp(cmd,"vf_hitbox_probe")){HitboxProbe(p);return true;}
 if(!strcmp(cmd,"vf_combat_selftest")){Selftest(p);return true;}
 if(!strcmp(cmd,"vf_materials_info")){
  char line[240];snprintf(line,sizeof(line),"VFMaterials count=%d profiles=%d mode=identify_only hash=%s head=%.3f chest=%.3f abdomen=%.3f arm=%.3f leg=%.3f\n",vfc::MaterialCount,vfc::ProfileCount,vfc::catalogSha256,gSkillData.plrHead,gSkillData.plrChest,gSkillData.plrStomach,gSkillData.plrArm,gSkillData.plrLeg);CLIENT_PRINTF(p->edict(),print_console,line);
  for(int slot=0;slot<vf::SlotCount;++slot){const vf::Item* item=VF_EquippedItem(p,slot);if(!item)continue;int id=vfc::ItemProfile(slot,item->id,vf::ItemModel(*item));snprintf(line,sizeof(line),"VFMaterialItem slot=%s item=%s profile=%s\n",vf::SlotKeys[slot],item->id,vfc::profiles[id].id);CLIENT_PRINTF(p->edict(),print_console,line);}return true;
 }
 return false;
}
