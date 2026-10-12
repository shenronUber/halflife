/* Opt-in diagnostics. CPU submission and asynchronous GPU elapsed queries;
 * no glFinish, no per-frame logging and no public renderer ABI changes. */
extern unsigned int vf_topology_resolves,vf_pose_updates;
static cvar_t *vf_perf;
static int vf_perf_label,vf_perf_count,vf_perf_gpu_count,vf_perf_warmup;
static unsigned int vf_perf_resolves,vf_perf_updates;
static double vf_perf_cpu[240],vf_perf_frame[240],vf_perf_gpu[240],vf_perf_start,vf_perf_previous;
static qboolean vf_perf_active,vf_perf_done;
typedef void (APIENTRY *vf_gen_query_fn)(GLsizei,GLuint*);
typedef void (APIENTRY *vf_begin_query_fn)(GLenum,GLuint);
typedef void (APIENTRY *vf_end_query_fn)(GLenum);
typedef void (APIENTRY *vf_get_query_fn)(GLuint,GLenum,GLuint*);
static vf_gen_query_fn vf_gen_queries;
static vf_begin_query_fn vf_begin_query;
static vf_end_query_fn vf_end_query;
static vf_get_query_fn vf_get_query;
static GLuint vf_perf_queries[16];
static int vf_perf_pending[16],vf_perf_slot=-1,vf_perf_cursor;
static qboolean vf_perf_initialized;
static void R_VFPerfInit(void){
 if(vf_perf_initialized)return;vf_perf_initialized=true;
 if(!glConfig.extensions_string || (!Q_strstr(glConfig.extensions_string,"GL_EXT_timer_query") &&
    !Q_strstr(glConfig.extensions_string,"GL_ARB_timer_query")))return;
 vf_gen_queries=(vf_gen_query_fn)gEngfuncs.GL_GetProcAddress("glGenQueries");
 vf_begin_query=(vf_begin_query_fn)gEngfuncs.GL_GetProcAddress("glBeginQuery");
 vf_end_query=(vf_end_query_fn)gEngfuncs.GL_GetProcAddress("glEndQuery");
 vf_get_query=(vf_get_query_fn)gEngfuncs.GL_GetProcAddress("glGetQueryObjectuiv");
 if(vf_gen_queries&&vf_begin_query&&vf_end_query&&vf_get_query)vf_gen_queries(16,vf_perf_queries);
 else vf_gen_queries=NULL;
}
static int R_VFPerfCompare(const void *a,const void *b){double x=*(const double*)a,y=*(const double*)b;return (x>y)-(x<y);}
static void R_VFPerfPrint(const char *kind,double *samples,int count){
 if(!count)return;double total=0;for(int i=0;i<count;++i)total+=samples[i];
 qsort(samples,count,sizeof(double),R_VFPerfCompare);
 gEngfuncs.Con_Printf("VFPerf label=%d metric=%s samples=%d mean_ms=%.6f p50_ms=%.6f p95_ms=%.6f max_ms=%.6f\n",
  vf_perf_label,kind,count,total/count,samples[count/2],samples[(count-1)*95/100],samples[count-1]);
}
static void R_VFPerfBegin(void){
 if(!vf_perf)vf_perf=gEngfuncs.Cvar_Get("vf_perf","0",0,"Opt-in native frame/GPU diagnostic scene ID");
 int label=(int)vf_perf->value;if(label<=0||vf_perf_active)return;
 R_VFPerfInit();
 if(label!=vf_perf_label){
  gEngfuncs.Con_Printf("VFPerf begin label=%d previous=%d previous_samples=%d warmup=%d gpu=%d\n",label,vf_perf_label,vf_perf_count,vf_perf_warmup,vf_perf_gpu_count);
  vf_perf_label=label;vf_perf_count=vf_perf_gpu_count=0;vf_perf_warmup=60;vf_perf_done=false;vf_perf_previous=0;
  vf_perf_resolves=vf_topology_resolves;vf_perf_updates=vf_pose_updates;
  for(int i=0;i<16;++i)if(vf_perf_pending[i])vf_perf_pending[i]=-1;
 }
 if(vf_perf_done)return;
 if(vf_gen_queries)for(int i=0;i<16;++i)if(vf_perf_pending[i]){
  GLuint ready=0;vf_get_query(vf_perf_queries[i],0x8867,&ready); // QUERY_RESULT_AVAILABLE
  if(ready){GLuint ns=0;vf_get_query(vf_perf_queries[i],0x8866,&ns);
   if(vf_perf_pending[i]>0&&vf_perf_gpu_count<240&&ns!=0xffffffffU)vf_perf_gpu[vf_perf_gpu_count++]=ns*.000001;
   vf_perf_pending[i]=0;
  }
 }
 if(vf_perf_count==240){
  qboolean pending=false;for(int i=0;i<16;++i)if(vf_perf_pending[i]>0)pending=true;
  if(pending)return;
  R_VFPerfPrint("cpu_render_hud",vf_perf_cpu,240);R_VFPerfPrint("frame",vf_perf_frame,240);
  R_VFPerfPrint("gpu_render_hud",vf_perf_gpu,vf_perf_gpu_count);
  gEngfuncs.Con_Printf("VFPerf work label=%d resolves=%u pose_updates=%u gpu_samples=%d\n",vf_perf_label,
   vf_topology_resolves-vf_perf_resolves,vf_pose_updates-vf_perf_updates,vf_perf_gpu_count);vf_perf_done=true;return;
 }
 vf_perf_slot=-1;
 if(vf_gen_queries)for(int n=0;n<16;++n){int i=(vf_perf_cursor+n)%16;if(!vf_perf_pending[i]){
  vf_perf_slot=i;vf_perf_cursor=(i+1)%16;vf_begin_query(0x88BF,vf_perf_queries[i]);break;
 }}
 vf_perf_start=gEngfuncs.pfnTime();vf_perf_active=true;
}
static void R_VFPerfEnd(void){
 if(!vf_perf_active)return;double now=gEngfuncs.pfnTime();
 if(vf_perf_slot>=0){vf_end_query(0x88BF);vf_perf_pending[vf_perf_slot]=vf_perf_warmup?-1:1;}
 if(vf_perf_warmup)--vf_perf_warmup;
 else if(vf_perf_count<240){vf_perf_cpu[vf_perf_count]=(now-vf_perf_start)*1000;
  vf_perf_frame[vf_perf_count]=(vf_perf_start-vf_perf_previous)*1000;++vf_perf_count;}
 vf_perf_previous=vf_perf_start;vf_perf_active=false;
}
