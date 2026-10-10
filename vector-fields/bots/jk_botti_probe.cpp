// Local integration-test observer. Does not alter bot decision-making.
#include <extdll.h>
#ifdef _WIN32
static int strcasecmp(const char *a,const char *b) { return _stricmp(a,b); }
static int strncasecmp(const char *a,const char *b,size_t n) { return _strnicmp(a,b,n); }
#endif
#include <meta_api.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
enginefuncs_t g_engfuncs;
globalvars_t *gpGlobals;
meta_globals_t *gpMetaGlobals;
gamedll_funcs_t *gpGamedllFuncs;
mutil_funcs_t *gpMetaUtilFuncs;
plugin_info_t Plugin_info = { META_INTERFACE_VERSION, "VF bot probe", "1.0", __DATE__, "Vector Fields", "", "VF_BOT_PROBE", PT_STARTUP, PT_ANYTIME };
struct Sample { float x,y,z,health,distance,damage; int valid,dead,deaths,shots,mp5shots,clip,minclip,maxclip,reloads,weapon; } samples[33];
static int msgtype=0,msgclient=0,msgbytes[8],msgcount=0;
static void print(const char *s) { g_engfuncs.pfnServerPrint(s); }
static edict_t *client(int n) {
    if(n<1||n>gpGlobals->maxClients)return NULL;
    edict_t *e=g_engfuncs.pfnPEntityOfEntIndex(n);
    if(!e||e->free||!e->v.netname||!STRING(e->v.netname)[0])return NULL;
    return e;
}
static void probe() {
    char b[1200];
    for(int i=1;i<=gpGlobals->maxClients;i++) {
        edict_t *e=client(i); if(!e)continue; Sample &s=samples[i];
        snprintf(b,sizeof(b),"VFBOT {\"index\":%d,\"name\":\"%s\",\"fake\":%d,\"health\":%.1f,\"dead\":%d,\"frags\":%.0f,\"x\":%.1f,\"y\":%.1f,\"z\":%.1f,\"distance\":%.1f,\"damage\":%.1f,\"deaths\":%d,\"shots\":%d,\"mp5_shots\":%d,\"weapon_id\":%d,\"clip\":%d,\"clip_min\":%d,\"clip_max\":%d,\"reloads\":%d,\"weapon_model\":\"%s\",\"player_model\":\"%s\"}\n",i,STRING(e->v.netname),!!(e->v.flags&FL_FAKECLIENT),e->v.health,e->v.deadflag,e->v.frags,e->v.origin.x,e->v.origin.y,e->v.origin.z,s.distance,s.damage,s.deaths,s.shots,s.mp5shots,s.weapon,s.clip,s.minclip,s.maxclip,s.reloads,STRING(e->v.weaponmodel),STRING(e->v.model));
        print(b);
    }
}
static void place() {
    if(g_engfuncs.pfnCVarGetFloat("sv_cheats")==0 || g_engfuncs.pfnCmd_Argc()!=6)return;
    int n=atoi(g_engfuncs.pfnCmd_Argv(1));edict_t *e=client(n);if(!e)return;
    float v[3]={(float)atof(g_engfuncs.pfnCmd_Argv(2)),(float)atof(g_engfuncs.pfnCmd_Argv(3)),(float)atof(g_engfuncs.pfnCmd_Argv(4))};
    g_engfuncs.pfnSetOrigin(e,v);e->v.velocity=Vector(0,0,0);e->v.v_angle=Vector(0,(float)atof(g_engfuncs.pfnCmd_Argv(5)),0);e->v.angles=e->v.v_angle;e->v.fixangle=1;
    samples[n].valid=0;
}
static void give() {
    if(g_engfuncs.pfnCVarGetFloat("sv_cheats")==0 || g_engfuncs.pfnCmd_Argc()!=3)return;
    edict_t *e=client(atoi(g_engfuncs.pfnCmd_Argv(1)));if(!e)return;
    edict_t *item=g_engfuncs.pfnCreateNamedEntity(g_engfuncs.pfnAllocString(g_engfuncs.pfnCmd_Argv(2)));if(!item)return;
    item->v.origin=e->v.origin;gpGamedllFuncs->dllapi_table->pfnSpawn(item);gpGamedllFuncs->dllapi_table->pfnTouch(item,e);
}
static void frame() {
    for(int i=1;i<=gpGlobals->maxClients;i++) {
        edict_t *e=client(i);if(!e)continue;Sample &s=samples[i];
        if(s.valid) {
            float dx=e->v.origin.x-s.x,dy=e->v.origin.y-s.y,dz=e->v.origin.z-s.z;float d=sqrtf(dx*dx+dy*dy+dz*dz);
            if(!s.dead&&!e->v.deadflag&&d<100)s.distance+=d;
            if(!s.dead&&e->v.health<s.health)s.damage+=s.health-e->v.health;
            if(!s.dead&&e->v.deadflag)s.deaths++;
        }
        s.x=e->v.origin.x;s.y=e->v.origin.y;s.z=e->v.origin.z;s.health=e->v.health;s.dead=e->v.deadflag;s.valid=1;
    }
    RETURN_META(MRES_IGNORED);
}
static void activate(edict_t *,int,int) { memset(samples,0,sizeof(samples)); RETURN_META(MRES_IGNORED); }
static void init() { g_engfuncs.pfnAddServerCommand("vf_bot_probe",probe);g_engfuncs.pfnAddServerCommand("vf_bot_place",place);g_engfuncs.pfnAddServerCommand("vf_bot_give",give);RETURN_META(MRES_IGNORED); }
static void playback(int,const edict_t *e,unsigned short,float,float *,float *,float,float,int,int,int,int) {
    if(e) { int n=g_engfuncs.pfnIndexOfEdict(e);if(n>0&&n<=gpGlobals->maxClients) { samples[n].shots++;const char *m=STRING(e->v.weaponmodel);if(m&&(strstr(m,"9mmAR")||strstr(m,"9mmar")))samples[n].mp5shots++; } }
    RETURN_META(MRES_IGNORED);
}
static void begin(int,int type,const float *,edict_t *e) { msgtype=type;msgclient=e?g_engfuncs.pfnIndexOfEdict(e):0;msgcount=0;RETURN_META(MRES_IGNORED); }
static void writebyte(int v) { if(msgcount<8)msgbytes[msgcount++]=v;RETURN_META(MRES_IGNORED); }
static void end() {
    if(msgclient>0&&msgclient<=gpGlobals->maxClients&&msgcount==3&&msgbytes[0]==1) {
        int size=0;int id=gpMetaUtilFuncs->pfnGetUserMsgID(&Plugin_info,"CurWeapon",&size);
        if(msgtype==id) { Sample &s=samples[msgclient];int c=msgbytes[2],w=msgbytes[1];if(w==4) { if(s.weapon==4&&c>s.clip)s.reloads++;if(!s.maxclip||c<s.minclip)s.minclip=c;if(c>s.maxclip)s.maxclip=c; }s.clip=c;s.weapon=w; }
    }
    RETURN_META(MRES_IGNORED);
}
C_DLLEXPORT int GetEntityAPI2(DLL_FUNCTIONS *t,int *) { memset(t,0,sizeof(*t));t->pfnGameInit=init;t->pfnStartFrame=frame;t->pfnServerActivate=activate;return 1; }
C_DLLEXPORT int GetEngineFunctions(enginefuncs_t *t,int *) { memset(t,0,sizeof(*t));t->pfnPlaybackEvent=playback;t->pfnMessageBegin=begin;t->pfnWriteByte=writebyte;t->pfnMessageEnd=end;return 1; }
extern "C" __declspec(dllexport) void WINAPI GiveFnptrsToDll(enginefuncs_t *e,globalvars_t *g) { g_engfuncs=*e;gpGlobals=g; }
C_DLLEXPORT int Meta_Query(char *,plugin_info_t **p,mutil_funcs_t *u) { *p=&Plugin_info;gpMetaUtilFuncs=u;return 1; }
C_DLLEXPORT int Meta_Attach(PLUG_LOADTIME,META_FUNCTIONS *t,meta_globals_t *g,gamedll_funcs_t *d) { gpMetaGlobals=g;gpGamedllFuncs=d;memset(t,0,sizeof(*t));t->pfnGetEntityAPI2=GetEntityAPI2;t->pfnGetEngineFunctions=GetEngineFunctions;return 1; }
C_DLLEXPORT int Meta_Detach(PLUG_LOADTIME,PL_UNLOAD_REASON) { return 1; }
