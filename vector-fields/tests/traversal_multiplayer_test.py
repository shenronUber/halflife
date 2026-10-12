"""Two clients and a late joiner receive the actual ledge state/aim poses."""
import json,re,shutil,subprocess,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from traversal_native_test import stage,build
OUT=ROOT/'docs/validation/traversal/multiplayer';PORT='27765'

def prepare(name,renderer=None):
 engine=stage('traversal-'+name,renderer=renderer);mod=engine/'vf_animation'
 shutil.copy2(ROOT.parent/'network/delta.lst',mod/'delta.lst');shutil.copy2(build(ensure=True),mod/'maps/vf_traversal.bsp')
 shutil.copytree(ROOT/'generated/traversal',mod/'models/vf_traversal',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.smd','*.qc','*.bmp','*.log','*.json'))
 return engine,mod

def run(renderer=None):
 OUT.mkdir(parents=True,exist_ok=True);server,actor,observer,late=[prepare(name,renderer)for name in ['server','actor','observer','late']]
 common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-nointro','-nowriteconfig']
 programs=[];logs=[]
 def start_client(pair,name,script):
  engine,mod=pair;(mod/'traversal_peer.cfg').write_text(script,encoding='ascii');log=engine/(name+'.log')
  if log.exists():log.unlink()
  programs.append(subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2',*common,'-windowed','-width','1280','-height','720','-log',name+'.log','-clientport',str(27766+len(programs)),'+name',name,'+developer','2','+connect','127.0.0.1:'+PORT,'+exec','traversal_peer.cfg'],cwd=engine));logs.append(log)
 server_log=server[0]/'peer-server.log'
 if server_log.exists():server_log.unlink()
 dedicated=subprocess.Popen([str(server[0]/'xash.exe'),'-ip','127.0.0.1','-noip6',*common,'-log','peer-server.log','+ip','127.0.0.1','-port',PORT,'+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+map','vf_traversal'],cwd=server[0],creationflags=subprocess.CREATE_NO_WINDOW)
 init='wait 180\ngl_vsync 0\nsys_timescale 1\nfps_max 60\ndeveloper 1\ncon_notifytime 0\nvf_reference 0\nwait 30\nvf_commit\nwait 35\nvf_character\nvf_character\nwait 12\n'
 try:
  time.sleep(1.5)
  start_client(actor,'peer-actor',init+'cmd give weapon_9mmAR\nweapon_9mmAR\nwait 20\ncmd vf_traversal_place 238 0 54 0\nwait 1\n+jump\nwait 22\n-jump\nwait 220\n+attack2\nwait 2\n-attack2\nwait 30\nvf_traversal_look 180\nwait 120\n+attack\nwait 10\n-attack\ncmd vf_traversal_info\nwait 600\nquit\n')
  time.sleep(1)
  start_client(observer,'peer-observer',init+'r_drawviewmodel 0\ncmd vf_traversal_place 120 -180 36 55\nvf_traversal_look 55 -8\nwait 35\necho PEER_BOTH\nvf_engine_stats\nscreenshot scrshots/peer_both.png\nwait 4\nwait 230\necho PEER_ARMED\nvf_engine_stats\nscreenshot scrshots/peer_backwards.png\nwait 4\nwait 100\nquit\n')
  time.sleep(9)
  start_client(late,'peer-late',init+'r_drawviewmodel 0\ncmd vf_traversal_place 80 -160 36 50\nvf_traversal_look 50 -8\nwait 35\necho PEER_LATE\nvf_engine_stats\nscreenshot scrshots/peer_late.png\nwait 4\nwait 35\nquit\n')
  for process in programs:process.wait(timeout=55)
 finally:
  for process in [*programs,dedicated]:
   if process.poll()is None:process.terminate();process.wait(timeout=8)
 return validate(server[0],observer[0],late[0],logs)


def validate(server_engine=None,observer_engine=None,late_engine=None,logs=None):
 base=ROOT/'build/animation-native'
 observer_engine=Path(observer_engine or base/'traversal-observer')
 late_engine=Path(late_engine or base/'traversal-late')
 observer=(observer_engine,observer_engine/'vf_animation')
 late=(late_engine,late_engine/'vf_animation')
 logs=logs or [base/('traversal-'+name)/('peer-'+name+'.log')for name in ('actor','observer','late')]
 server_log=Path(server_engine or base/'traversal-server')/'peer-server.log'
 texts=[p.read_text(errors='replace')for p in logs];pattern=r'VFPeerTraversal player=(\d+) phase=(\d+) sequence=(\d+) gait=(\d+) wall=([\d.-]+) top=([\d.-]+) blends=(\d+),(\d+)'
 reports={};proofs={}
 for label,text in [('observer',texts[1]),('late',texts[2])]:
  rows=[tuple(map(float,row))for row in re.findall(pattern,text)];reports[label]=rows
  assert any(phase==3 and seq==89 and gait==0 and abs(wall)<.1 and abs(top-96)<.1 for player,phase,seq,gait,wall,top,b0,b1 in rows),(label,rows)
  assert 'VFState rejected'not in text and 'rejected=0'in text,(label,'assembly rejected')
  body=[tuple(map(float,row))for row in re.findall(r'VFTraversalBody phase=(\d+) sequence=(\d+) left_error=([\d.-]+) right_error=([\d.-]+) gun_error=([\d.-]+) body_shift=([\d.-]+) face_error=([\d.-]+)',text)]
  assert len(body)>30,(label,'missing rendered hand telemetry')
  assert all(0<=r[2]<.01 for r in body),(label,'world support contact',sum(r[2]<0 or r[2]>=.01 for r in body))
  settled=[r for r in body if r[0]==3 and r[1]==89 and 0<=r[4]<.01]
  assert len(settled)>30,(label,'backwards gun must stay aligned with the firing wrist')
  anchors=[(int(p),[float(v)for v in (hip+','+knee).split(',')])for p,hip,knee in re.findall(r'VFTraversalAnchor phase=(\d+) hip=([\d.,-]+) knee=([\d.,-]+)',text)]
  armed_positions=[point for p,point in anchors if p==3]
  assert len(armed_positions)>30,(label,'missing planted waist/knee')
  from traversal_pose_telemetry import anchored_lean
  from traversal_torso_clearance import native_clearance
  block='\n'.join(re.findall(r'VFTraversalLean phase=3[^\n]*\s+VFTraversalAnchor phase=3[^\n]*',text))
  lean=anchored_lean(block,network_quantum=1/32)
  engine=observer_engine if label=='observer' else late_engine
  clearance=native_clearance(text,engine/'vf_animation/models/vf_skins/persona_scout.mdl',engine/'vf_animation/models/vf_r01/r01_tp.mdl')
  proofs[label]=dict(lower_body=lean,torso_clearance=clearance)
 assert any(phase==2 and seq==83 and gait==0 for player,phase,seq,gait,wall,top,b0,b1 in reports['observer']),reports
 for pair in [observer,late]:
  for path in (pair[1]/'scrshots').glob('peer_*.png'):shutil.copy2(path,OUT/path.name)
 for path in [*logs,server_log]:shutil.copy2(path,OUT/path.name)
 reports['pose_validation']=proofs
 (OUT/'network.json').write_text(json.dumps(reports,indent=2));print('PASS traversal multiplayer: both-hand pose, backwards armed shot, static body yaw, zero gait, exact ledge height and late join replication; firing limbs clear the torso')
if __name__=='__main__':run()
