"""Two real clients exercise automatic counter selection and auditory gating."""
import json,re,shutil,socket,subprocess,time
from pathlib import Path
import voices_test as base
ROOT=base.ROOT;ENGINE=base.ENGINE;MOD=base.MOD;PASSWORD='vf_taunt_validation';PORT=27095

def rcon(command):
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
  s.settimeout(.2);s.sendto(b'\xff\xff\xff\xffrcon '+PASSWORD.encode()+b' '+command.encode()+b'\n\0',('127.0.0.1',PORT))
  try:
   while True:s.recv(65535)
  except (socket.timeout,ConnectionResetError):pass

def phase(folder,index,body):
 mod=folder/'vf_visual';(mod/f'taunt_phase_{index}.cfg').write_text(body+f'wait 5\nexec taunt_wait_{index}.cfg\n',encoding='ascii')
 (mod/f'taunt_wait_{index}.cfg').write_text(f'wait 30\nexec taunt_wait_{index}.cfg\n',encoding='ascii')
def advance(folder,index):
 p=folder/'vf_visual'/f'taunt_wait_{index}.cfg';tmp=p.with_suffix('.tmp');tmp.write_text(f'exec taunt_phase_{index+1}.cfg\n',encoding='ascii');tmp.replace(p)
def wait_for(folder,marker,filename='taunt-peer.log',timeout=45):
 deadline=time.time()+timeout
 while time.time()<deadline:
  p=folder/filename
  if p.exists() and marker in p.read_text(errors='replace'):return
  time.sleep(.2)
 raise AssertionError('timeout '+marker)
def social(log):return re.findall(r'VFVoice social: player=(\d+) event=(\w+) reply_to=(\d+) bot=(\d+)',log)
def run():
 base.prepare();peer=base.PROJECT/'runtime/vector-engine-taunt-peer';peer.mkdir(parents=True,exist_ok=True)
 for p in ENGINE.iterdir():
  if p.is_file() and p.suffix.lower() in ('.dll','.exe'):shutil.copy2(p,peer/p.name)
 for folder in ['valve','vf_visual','cs_assets','tfc_assets']:
  if (ENGINE/folder).exists():shutil.copytree(ENGINE/folder,peer/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
 init='wait 180\ndeveloper 1\ngl_vsync 0\nfps_max 100\ncon_notifytime 0\nvf_voice_subtitles 2\ncmd vf_peer_pose\n'
 phase(ENGINE,0,init+'cmd vf_voice_set otto\nwait 20\necho TAUNT_A_READY\n')
 phase(peer,0,init+'cmd vf_voice_set nikos\nwait 20\necho TAUNT_B_READY\n')
 phase(ENGINE,1,'cmd vf_taunt\nwait 20\necho TAUNT_A_NEAR\n')
 phase(peer,1,'cmd vf_taunt\nwait 2\ncmd vf_taunt\nwait 2\ncmd vf_taunt\nwait 20\nscreenshot scrshots/counter_nikos.png\necho TAUNT_B_COUNTER\n')
 phase(ENGINE,2,'cmd vf_voice_info\ncmd vf_voice_set otto\ncmd vf_taunt\nwait 20\necho TAUNT_A_EXPIRY\n')
 phase(peer,2,'cmd vf_voice_set nikos\ncmd vf_taunt\nwait 20\necho TAUNT_B_EXPIRED\n')
 phase(peer,3,'+back\nwait 90\n-back\nwait 10\necho TAUNT_B_FAR\n')
 phase(ENGINE,3,'cmd vf_voice_set otto\ncmd vf_taunt\nwait 20\necho TAUNT_A_FAR\n')
 phase(peer,4,'cmd vf_voice_set nikos\ncmd vf_taunt\nwait 20\necho TAUNT_B_NORMAL_FAR\n')
 phase(peer,5,'cmd vf_peer_pose\ncmd vf_voice_set nikos\nwait 20\necho TAUNT_B_RETURNED\n')
 phase(ENGINE,4,'cmd vf_voice_set otto\ncmd vf_taunt\nwait 20\necho TAUNT_A_SOURCE\n')
 phase(ENGINE,5,'cmd vf_voice_test death\nwait 20\necho TAUNT_A_DEAD\n')
 phase(peer,6,'cmd vf_voice_set nikos\ncmd vf_taunt\nwait 20\necho TAUNT_B_DEAD_SOURCE\n')
 phase(peer,7,'cmd vf_voice_set nikos\ncmd vf_taunt\nwait 20\necho TAUNT_B_MUTED\n')
 phase(ENGINE,6,'quit\n');phase(peer,8,'quit\n')
 common=['-rodir',base.STEAM,'-game','vf_visual','-console','-nointro']
 server=subprocess.Popen([str(ENGINE/'xash.exe'),*common,'-log','taunt-server.log','+ip','127.0.0.1','-port',str(PORT),'+rcon_password',PASSWORD,'+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','1','+map','vf_range'],cwd=ENGINE,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 children=[]
 try:
  time.sleep(3);rcon('vf_taunt_cooldown 1')
  for folder,port,name in [(ENGINE,27096,'TAUNT_A'),(peer,27097,'TAUNT_B')]:
   children.append(subprocess.Popen([str(folder/'xash3d.exe'),*common,'-width','1280','-height','720','-nowriteconfig','-log','taunt-peer.log','-clientport',str(port),'+exec','lab_controls.cfg','+developer','1','+gl_vsync','0','+fps_max','100','+name',name,'+connect',f'127.0.0.1:{PORT}','+exec','taunt_phase_0.cfg'],cwd=folder,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
   wait_for(folder,'TAUNT_'+('A' if folder==ENGINE else 'B')+'_READY')
  advance(ENGINE,0);wait_for(ENGINE,'TAUNT_A_NEAR');advance(peer,0);wait_for(peer,'TAUNT_B_COUNTER')
  near=(ENGINE/'taunt-server.log').read_text(errors='replace');assert social(near)==[('1','taunt','0','0'),('2','counter_taunt','1','0')],social(near)
  rcon('vf_counter_window 0.2');advance(ENGINE,1);wait_for(ENGINE,'TAUNT_A_EXPIRY');time.sleep(5);advance(peer,1);wait_for(peer,'TAUNT_B_EXPIRED')
  expiry=(ENGINE/'taunt-server.log').read_text(errors='replace');assert social(expiry)[-2:]==[('1','taunt','0','0'),('2','taunt','0','0')],social(expiry)
  rcon('vf_taunt_radius 256');rcon('vf_counter_window 5');advance(peer,2);wait_for(peer,'TAUNT_B_FAR');advance(ENGINE,2);wait_for(ENGINE,'TAUNT_A_FAR');advance(peer,3);wait_for(peer,'TAUNT_B_NORMAL_FAR')
  far=(ENGINE/'taunt-server.log').read_text(errors='replace');assert social(far)[-2:]==[('1','taunt','0','0'),('2','taunt','0','0')],social(far)
  rcon('vf_taunt_radius 768');advance(peer,4);wait_for(peer,'TAUNT_B_RETURNED');advance(ENGINE,3);wait_for(ENGINE,'TAUNT_A_SOURCE');advance(ENGINE,4);wait_for(ENGINE,'TAUNT_A_DEAD');advance(peer,5);wait_for(peer,'TAUNT_B_DEAD_SOURCE')
  dead=(ENGINE/'taunt-server.log').read_text(errors='replace');assert social(dead)[-1]==('2','taunt','0','0')
  before=len(social(dead));rcon('vf_taunts 0');advance(peer,6);wait_for(peer,'TAUNT_B_MUTED');assert len(social((ENGINE/'taunt-server.log').read_text(errors='replace')))==before
  advance(ENGINE,5);advance(peer,7)
  for p in children:p.wait(20);assert p.returncode==0
  logs=[(f/'taunt-peer.log').read_text(errors='replace') for f in [ENGINE,peer]]
  for log in logs:assert 'actor=nikos event=counter_taunt' in log,'native counter metadata replication'
  assert 'VFVoice context: reply_to=0' in logs[0],'counter responses must not start endless reply chains'
  assert 'Host_Error' not in near and 'S_LoadSound:' not in near
  report=dict(clients=2,checks=['real German and Greek speakers use the same taunt key','nearby taunt automatically selects counter dialogue','three rapid reply presses emit one counter','both native clients receive the selected counter clip','counter responses do not create an automatic chain','hearing window expiry restores normal taunts','moving outside the configured range prevents a reply','a dead source cannot receive a counter','server taunt mute blocks new speech'],scope='loopback native clients; audio acting quality requires listening')
  base.write_report('taunt-native-verification.json',report);print('PASS taunt native',report,flush=True)
 finally:
  for p in children:
   if p.poll()is None:p.terminate();p.wait(10)
  if server.poll()is None:server.terminate();server.wait(10)
if __name__=='__main__':run()
