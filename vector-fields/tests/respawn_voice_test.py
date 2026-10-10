"""Actual deaths/respawns and owner-only audio on two native Xash clients."""
import json,re,shutil,socket,subprocess,time
from pathlib import Path
import voices_test as base
PROJECT=base.PROJECT;ROOT=base.ROOT
ENGINE=PROJECT/'runtime/vector-engine-respawn-validation'
PEER=PROJECT/'runtime/vector-engine-respawn-peer'
base.ENGINE=ENGINE;base.MOD=ENGINE/'vf_visual'
PASSWORD='vf_respawn_validation';PORT=27115

def rcon(command):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  s.settimeout(.2);s.sendto(b'\xff\xff\xff\xffrcon '+PASSWORD.encode()+b' '+command.encode()+b'\n\0',('127.0.0.1',PORT))
  try:
   while True:s.recv(65535)
  except (socket.timeout,ConnectionResetError):pass

def phase(folder,index,body):
 mod=folder/'vf_visual'
 (mod/f'respawn_phase_{index}.cfg').write_text(body+f'wait 5\nexec respawn_wait_{index}.cfg\n',encoding='ascii')
 (mod/f'respawn_wait_{index}.cfg').write_text(f'wait 30\nexec respawn_wait_{index}.cfg\n',encoding='ascii')

def advance(folder,index):
 p=folder/'vf_visual'/f'respawn_wait_{index}.cfg';tmp=p.with_suffix('.tmp')
 tmp.write_text(f'exec respawn_phase_{index+1}.cfg\n',encoding='ascii')
 # Xash briefly opens the barrier file without Windows delete-sharing.
 deadline=time.monotonic()+3
 while True:
  try:tmp.replace(p);return
  except PermissionError:
   if time.monotonic()>=deadline:raise
   time.sleep(.03)

def wait_for(folder,marker,filename='respawn-peer.log',timeout=45):
 deadline=time.time()+timeout
 while time.time()<deadline:
  p=folder/filename
  if p.exists() and marker in p.read_text(errors='replace'):return
  time.sleep(.2)
 raise AssertionError('timeout '+marker)

def read(folder,name='respawn-peer.log'):return (folder/name).read_text(errors='replace')
def events(log):return re.findall(r'VFVoice play: player=(\d+) actor=(\w+) event=(\w+) clip=(\d+)',log)

def run():
 manifest=base.prepare();PEER.mkdir(parents=True,exist_ok=True)
 for p in ENGINE.iterdir():
  if p.is_file() and p.suffix.lower() in ('.dll','.exe'):shutil.copy2(p,PEER/p.name)
 for folder in ['valve','vf_visual','cs_assets','tfc_assets']:
  if (ENGINE/folder).exists():shutil.copytree(ENGINE/folder,PEER/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
 init='wait 180\ndeveloper 1\ngl_vsync 0\nfps_max 100\ncon_notifytime 0\nvf_voice_subtitles 2\ncmd vf_peer_pose\nwait 200\n'
 phase(ENGINE,0,init+'echo RESPAWN_OWNER_READY\n')
 phase(PEER,0,init+'echo RESPAWN_PEER_READY\n')
 phase(ENGINE,1,'cmd vf_voice_test death\nwait 400\necho RESPAWN_OWNER_DEAD\n')
 phase(ENGINE,2,'+jump\nwait 8\n-jump\nwait 220\nscreenshot scrshots/private_respawn.png\necho RESPAWN_OWNER_RETURNED\n')
 phase(ENGINE,3,'cmd vf_voice_test gib\nwait 100\necho RESPAWN_OWNER_GIBBED\n')
 phase(ENGINE,4,'+jump\nwait 8\n-jump\nwait 220\necho RESPAWN_OWNER_GIB_RETURNED\n')
 audition='vf_voice_subtitles 0\n'
 for actor in base.ACTORS:
  audition+=f'cmd vf_voice_set {actor}\n'
  for n in range(3):audition+='cmd vf_voice_preview respawn\nwait 15\n'
 phase(ENGINE,5,audition+'echo RESPAWN_ALL_ACTORS_PRIVATE\n')
 phase(ENGINE,6,'cmd vf_voice_test death\nwait 400\necho RESPAWN_MUTED_DEATH\n')
 phase(ENGINE,7,'+jump\nwait 8\n-jump\nwait 220\necho RESPAWN_MUTED_RETURNED\n')
 phase(ENGINE,8,'quit\n');phase(PEER,1,'quit\n')
 common=['-rodir',base.STEAM,'-game','vf_visual','-console','-nointro']
 for folder in [ENGINE,PEER]:
  for name in ['respawn-server.log','respawn-peer.log']:(folder/name).unlink(missing_ok=True)
 server=subprocess.Popen([str(ENGINE/'xash.exe'),*common,'-log','respawn-server.log','+ip','127.0.0.1','-port',str(PORT),'+rcon_password',PASSWORD,'+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+mp_forcerespawn','0','+developer','1','+map','vf_range'],cwd=ENGINE,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 children=[]
 try:
  time.sleep(3)
  for folder,port,name in [(ENGINE,27116,'RESPAWN_OWNER'),(PEER,27117,'RESPAWN_PEER')]:
   children.append(subprocess.Popen([str(folder/'xash3d.exe'),*common,'-width','1280','-height','720','-nowriteconfig','-log','respawn-peer.log','-clientport',str(port),'+exec','lab_controls.cfg','+developer','1','+gl_vsync','0','+fps_max','100','+name',name,'+connect',f'127.0.0.1:{PORT}','+exec','respawn_phase_0.cfg'],cwd=folder,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
   wait_for(folder,name+'_READY')
  initial=events(read(ENGINE,'respawn-server.log'))
  assert len([e for e in initial if e[2]=='spawn'])==2,initial
  assert not [e for e in initial if e[2]=='respawn'],initial
  advance(ENGINE,0);wait_for(ENGINE,'RESPAWN_OWNER_DEAD')
  assert not [e for e in events(read(ENGINE,'respawn-server.log')) if e[2]=='respawn']
  advance(ENGINE,1);wait_for(ENGINE,'RESPAWN_OWNER_RETURNED')
  assert len([e for e in events(read(ENGINE,'respawn-server.log')) if e[2]=='respawn'])==1
  advance(ENGINE,2);wait_for(ENGINE,'RESPAWN_OWNER_GIBBED')
  advance(ENGINE,3);wait_for(ENGINE,'RESPAWN_OWNER_GIB_RETURNED')
  assert len([e for e in events(read(ENGINE,'respawn-server.log')) if e[2]=='respawn'])==2
  advance(ENGINE,4);wait_for(ENGINE,'RESPAWN_ALL_ACTORS_PRIVATE')
  rcon('vf_voices 0');advance(ENGINE,5);wait_for(ENGINE,'RESPAWN_MUTED_DEATH')
  rcon('vf_voices 1');advance(ENGINE,6);wait_for(ENGINE,'RESPAWN_MUTED_RETURNED')
  serverlog=read(ENGINE,'respawn-server.log');ownerlog=read(ENGINE);peerlog=read(PEER)
  assert len(re.findall(r'VFDeath play: entity=1 ',serverlog))==2
  for log in [ownerlog,peerlog]:assert len(re.findall(r'VFDeath received: entity=1 ',log))==2
  private=[e for e in events(serverlog) if e[2]=='respawn']
  assert len(private)==3+3*len(base.ACTORS),private
  assert len(re.findall(r'VFVoice private played: player=1 ',ownerlog))==len(private),'owner plays every private message, even with subtitles disabled'
  assert len(re.findall(r'VFVoice private: player=1 event=respawn recipients=1',serverlog))==len(private)
  assert not re.search(r'event=respawn |VFVoice private played:',peerlog),'nearby peer must not receive private dialogue'
  for actor in base.ACTORS:
   preview=[int(e[3]) for e in private if e[1]==actor]
   assert len(preview)>=3,(actor,preview)
  auditions=ownerlog.split('RESPAWN_OWNER_GIB_RETURNED',1)[1].split('RESPAWN_ALL_ACTORS_PRIVATE',1)[0]
  for actor in base.ACTORS:
   variants=[int(n) for n in re.findall(r'actor='+actor+r' event=respawn clip=(\d+)',auditions)]
   assert len(variants)==3 and variants[0]!=variants[1] and variants[1]!=variants[2],(actor,variants)
  assert len([e for e in events(serverlog) if e[2]=='spawn'])==2,'post-death spawns must not replay the initial introduction'
  for log in [serverlog,ownerlog,peerlog]:assert 'Host_Error' not in log and 'S_LoadSound:' not in log and 'missing sound' not in log
  assert len([c for c in manifest['clips'] if c['event']==base.read(ROOT/'data/voices.json')['events'].index('respawn')])==18
  advance(ENGINE,7);advance(PEER,0)
  for child in children:child.wait(20);assert child.returncode==0
  report=dict(clients=2,actors=len(base.ACTORS),private_variants=18,actual_respawns=3,checks=['owner and nearby peer each receive both reliable nonverbal normal/gib deaths','muted death emits no cry','first appearances retain the original introduction','actual normal and gib deaths trigger one post-death complaint each','death while voices are muted still selects respawn after re-enabling','all six actors play private variants without consecutive repeats','owner-only local audio plays independently of subtitle settings','a nearby native peer receives neither private metadata nor audio playback','post-death spawns do not replay initial introductions'],scope='two native loopback clients; audio acting quality requires listening')
  base.write_report('respawn-native-verification.json',report);print('PASS private respawn',report,flush=True)
 finally:
  for child in children:
   if child.poll()is None:child.terminate();child.wait(10)
  if server.poll()is None:server.terminate();server.wait(10)
if __name__=='__main__':run()
