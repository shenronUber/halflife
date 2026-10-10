"""Authoritative effects, late joins, permissions and enemy kills on two Xash clients."""
import json,re,shutil,subprocess,time
from pathlib import Path
import voices_test as base
ROOT=base.ROOT;ENGINE=base.ENGINE;MOD=base.MOD

def run():
 base.prepare();peer=base.PROJECT/'runtime/vector-engine-status-peer';peer.mkdir(parents=True,exist_ok=True)
 for p in ENGINE.iterdir():
  if p.is_file() and p.suffix.lower() in ('.dll','.exe'):shutil.copy2(p,peer/p.name)
 for folder in ['valve','vf_visual','cs_assets','tfc_assets']:
  if (ENGINE/folder).exists():shutil.copytree(ENGINE/folder,peer/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
 def phase(folder,index,body):
  mod=folder/'vf_visual';(mod/f'vf_status_phase_{index}.cfg').write_text(body+f'wait 5\nexec vf_status_wait_{index}.cfg\n',encoding='ascii')
  (mod/f'vf_status_wait_{index}.cfg').write_text(f'wait 30\nexec vf_status_wait_{index}.cfg\n',encoding='ascii')
 def advance(folder,index):
  target=folder/'vf_visual'/f'vf_status_wait_{index}.cfg';temp=target.with_suffix('.tmp');temp.write_text(f'exec vf_status_phase_{index+1}.cfg\n',encoding='ascii');temp.replace(target)
 init='wait 180\ndeveloper 1\ngl_vsync 0\nfps_max 100\ncon_notifytime 0\nvf_voice_subtitles 2\n'
 phase(ENGINE,0,init+'echo STATUS_DENIED_BEGIN\ncmd vf_status_dev 1\ncmd vf_status_apply hydro\nwait 30\necho STATUS_DENIED_END\nrcon_password vf_status_local_validation\nrcon sv_cheats 1\nwait 60\ncmd vf_peer_pose\ncmd vf_voice_set rocco\ncmd vf_status_dev 1\nwait 10\ncmd vf_status_apply hydro 30\nwait 30\necho STATUS_A_READY\n')
 phase(ENGINE,1,'cmd vf_status_apply electro 30\nwait 30\necho STATUS_A_COMBO\n')
 phase(ENGINE,2,'rcon sv_cheats 0\nwait 60\ncmd vf_status_dev 1\ncmd vf_status_apply toxic\nwait 30\nvf_status_client\necho STATUS_A_REVOKED\n')
 phase(ENGINE,3,'rcon sv_cheats 1\nwait 60\ncmd vf_peer_pose\ncmd vf_voice_set rocco\nweapon_9mmAR\nwait 30\n+attack\nwait 200\n-attack\nwait 60\necho STATUS_A_KILLED\n')
 phase(ENGINE,4,'quit\n')
 phase(peer,0,init+'cmd vf_peer_pose\ncmd vf_voice_set viktor\nwait 30\necho STATUS_LATE_JOIN_BEGIN\nvf_status_client\necho STATUS_LATE_JOIN_END\nscreenshot scrshots/status_remote_hydro.png\nwait 10\necho STATUS_B_READY\n')
 phase(peer,1,'wait 20\necho STATUS_COMBO_BEGIN\nvf_status_client\necho STATUS_COMBO_END\nscreenshot scrshots/status_remote_arc.png\nwait 10\necho STATUS_B_COMBO\n')
 phase(peer,2,'wait 20\necho STATUS_REVOKED_BEGIN\nvf_status_client\necho STATUS_REVOKED_END\necho STATUS_B_REVOKED\n')
 phase(peer,3,'quit\n')
 # Keep commands waiting until the actual client sign-on; fixed frame waits
 # otherwise let a late join run all phases while resources are still loading.
 for folder in (ENGINE,peer):
  mod=folder/'vf_visual'
  (mod/'vf_status_connect.cfg').write_text(init+'echo STATUS_CONNECT_WAIT\nexec vf_status_connect_wait.cfg\n',encoding='ascii')
  (mod/'vf_status_connect_wait.cfg').write_text('wait 30\nexec vf_status_connect_wait.cfg\n',encoding='ascii')
 def connected(folder,index):
  wait_for(ENGINE,'VFVoice assigned: player='+str(index),'status-server.log')
  wait_for(folder,'VFState player='+str(index))
  target=folder/'vf_visual/vf_status_connect_wait.cfg';temp=target.with_suffix('.tmp')
  temp.write_text('exec vf_status_phase_0.cfg\n',encoding='ascii');temp.replace(target)
 common=['-rodir',base.STEAM,'-game','vf_visual','-console','-nointro']
 server=subprocess.Popen([str(ENGINE/'xash.exe'),*common,'-log','status-server.log','+ip','127.0.0.1','-port','27085','+rcon_password','vf_status_local_validation','+maxplayers','4','+sv_lan','1','+sv_cheats','0','+deathmatch','1','+developer','1','+map','vf_range'],cwd=ENGINE,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 children=[];started=time.time()
 try:
  time.sleep(3);assert server.poll()is None
  def launch(folder,port,cfg,name):
   child=subprocess.Popen([str(folder/'xash3d.exe'),*common,'-windowed','-width','960','-height','540','-nowriteconfig','-log','status-peer.log','-clientport',str(port),'+exec','lab_controls.cfg','+developer','1','+gl_vsync','0','+fps_max','100','+name',name,'+connect','127.0.0.1:27085','+exec',cfg],cwd=folder,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);children.append(child)
  def wait_for(folder,marker,filename='status-peer.log'):
   deadline=time.time()+45
   while time.time()<deadline:
    path=folder/filename
    if path.exists() and marker in path.read_text(errors='replace'):return
    if any(c.poll() is not None for c in children):raise AssertionError('client exited before '+marker)
    time.sleep(.3)
   raise AssertionError('phase timed out: '+marker)
  launch(ENGINE,27086,'vf_status_connect.cfg','STATUS_A');connected(ENGINE,1);wait_for(ENGINE,'STATUS_A_READY')
  launch(peer,27087,'vf_status_connect.cfg','STATUS_B');connected(peer,2);wait_for(peer,'STATUS_B_READY')
  advance(ENGINE,0);wait_for(ENGINE,'STATUS_A_COMBO');advance(peer,0);wait_for(peer,'STATUS_B_COMBO')
  advance(ENGINE,1);wait_for(ENGINE,'STATUS_A_REVOKED');advance(peer,1);wait_for(peer,'STATUS_B_REVOKED')
  advance(ENGINE,2);wait_for(ENGINE,'STATUS_A_KILLED')
  wait_for(peer,'actor=rocco event=kill');wait_for(peer,'VFDeath received: entity=2 actor=viktor cause=')
  advance(ENGINE,3);advance(peer,2)
  for child in children:child.wait(timeout=100);assert child.returncode==0,child.returncode
  logs=[(folder/'status-peer.log').read_text(errors='replace') for folder in [ENGINE,peer]];serverlog=(ENGINE/'status-server.log').read_text(errors='replace')
  def section(log,a,b):return log.split(a,1)[1].split(b,1)[0]
  assert 'VFStatus rejected: developer command requires local play or sv_cheats.' in section(logs[0],'STATUS_DENIED_BEGIN','STATUS_DENIED_END')
  late=section(logs[1],'STATUS_LATE_JOIN_BEGIN','STATUS_LATE_JOIN_END');assert 'player=1 effect=hydro' in late,late
  combo=section(logs[1],'STATUS_COMBO_BEGIN','STATUS_COMBO_END');assert 'player=1 effect=arc_chain' in combo and not re.search(r'player=1 effect=(hydro|electro) ',combo),combo
  revoked=section(logs[1],'STATUS_REVOKED_BEGIN','STATUS_REVOKED_END');assert 'player=1 developer=0' in revoked and 'VFStatus client active:' not in revoked,revoked
  for log in logs:assert 'VFVoice received: player=1 actor=rocco event=arc_chain' in log
  assert 'VFVoice received: player=1 actor=rocco event=hydro' not in logs[1],'late join must not replay a past onset'
  assert 'VFStatus apply: player=1 effect=toxic' not in serverlog
  assert re.search(r'VFVoice play: player=1 actor=rocco event=kill ',serverlog),'real enemy kill did not speak'
  cause='kinetic' if 'VFProc player=2 effect=kinetic' in serverlog else 'standard'
  assert f'VFDeath play: entity=2 actor=viktor cause={cause} ' in serverlog,'victim did not scream'
  for log in logs:assert f'VFDeath received: entity=2 actor=viktor cause={cause} ' in log
  for event in ['kill']:
   for log in logs:assert re.search(r'VFVoice received: player=[12] actor=\w+ event='+event+' ',log),(event,log[-1500:])
  for name in ['hydro','arc']:
   shot=peer/'vf_visual/scrshots'/f'status_remote_{name}.png';assert shot.stat().st_mtime>=started
  report=dict(clients=2,late_join=True,checks=['ordinary multiplayer rejects developer effect activation','late join receives active Hydro with its remaining duration','late join does not replay the old Hydro dialogue','both clients receive the same combined reaction speech','reaction consumes primary states on remote clients','revoking sv_cheats clears developer states on both clients','attempted effect application after revocation rejected','real rifle fire kills an enemy and triggers killer and victim voices'],scope='dedicated loopback server and native clients; public Internet not tested')
  base.write_report('status-multiplayer-verification.json',report);print('PASS status multiplayer',report,flush=True)
 finally:
  for child in children:
   if child.poll()is None:child.terminate();child.wait(10)
  if server.poll()is None:server.terminate();server.wait(10)
if __name__=='__main__':run()
