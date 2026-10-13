"""Two real loopback players; paired exact-state server pose benchmarks."""
import json,os,re,subprocess,sys,time,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from native_workspace import engine_path,stage_installed,port
OUT=ROOT/'build/maintenance-2026-10-13/pose-cache'
def run():
 OUT.mkdir(parents=True,exist_ok=True);pairs=[]
 for name in ('owner','peer'):
  engine=engine_path(OUT/name);mod=stage_installed(engine);pairs.append((engine,mod))
 owner,game=pairs[0];peer,peer_mod=pairs[1];server_port=port();processes=[]
 for mod in (game,peer_mod):(mod/'pose_ready.cfg').write_text('wait 30\nexec pose_ready.cfg\n',encoding='ascii')
 def launch(engine,mod,name,args):
  p=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','640','-height','480','-nointro','-nowriteconfig','-log',name+'.log','-clientport',str(port()),*args,'+exec','pose_ready.cfg'],cwd=engine,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));processes.append(p)
 def ready(path,player):
  deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   if path.exists()and f'VFState player={player}'in path.read_text(errors='replace'):return
   if any(p.poll()is not None for p in processes):raise RuntimeError('Benchmark client exited during sign-on')
   time.sleep(.2)
  raise TimeoutError('Benchmark sign-on failed')
 try:
  launch(owner,game,'owner',['-port',str(server_port),'+maxplayers','2','+sv_lan','1','+deathmatch','1','+sv_cheats','1','+developer','1','+map','vf_range'])
  ready(owner/'owner.log',1)
  launch(peer,peer_mod,'peer',['+name','pose-peer','+developer','1','+connect',f'127.0.0.1:{server_port}']);ready(peer/'peer.log',2)
  (peer_mod/'pose_ready.cfg').write_text('developer 0\ngl_vsync 0\nfps_max 60\nwait 5000\nquit\n',encoding='ascii')
  lines=['developer 0','gl_vsync 0','fps_max 120','host_framerate .016666667','wait 30']
  # Alternating order limits warm-up/order bias; discard the first pair.
  for repeat in range(8):
   for mode in ((0,1)if repeat%2==0 else(1,0)):
    lines += [f'vf_sv_pose_cache {mode}','wait 1','vf_sv_pose_bench 2048']
  lines+=['vf_sv_pose_cache 1','vf_sv_pose_info','quit'];(game/'pose_ready.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii')
  processes[0].wait(timeout=100);assert processes[0].returncode==0
 finally:
  for p in processes:
   if p.poll()is None:p.terminate();p.wait(timeout=10)
 log=(owner/'owner.log').read_text(errors='replace');(OUT/'native.log').write_text(log,encoding='utf-8')
 assert not any(error in log for error in ('Host_Error','SV_Error','Crash:'))
 rows=[dict(clients=int(c),queries=int(q),requests=int(n),enabled=int(mode),milliseconds=float(ms),hits=int(h),evaluations=int(e))for c,q,n,mode,ms,h,e in re.findall(r'VFPoseBench clients=(\d+) queries=(\d+) requests=(\d+) enabled=(\d+) milliseconds=([\d.]+) hits=(\d+) evaluations=(\d+)',log)]
 assert len(rows)==16 and all(r['clients']==2 and r['requests']==4096 for r in rows),rows
 for row in rows:
  assert row['hits']+row['evaluations']==row['requests'],row
  if row['enabled']:assert row['hits']>=4094 and row['evaluations']<=2,row
  else:assert row['hits']==0 and row['evaluations']==4096,row
 medians={str(mode):statistics.median(r['milliseconds']for r in rows[2:]if r['enabled']==mode)for mode in(0,1)}
 report=dict(passed=True,rows=rows,median_batch_ms=medians,speedup=medians['0']/medians['1'],scope='4096 identical-state server pose requests across two real loopback players; excludes network latency, collision planes and rendering. Cache-off already includes the removed redundant torso evaluation.')
 (OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PASS pose cache',json.dumps(report),flush=True)
 return report
if __name__=='__main__':run()
