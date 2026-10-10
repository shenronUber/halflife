"""Real jk_botti clients make voice decisions; a real human client hears and answers."""
import json,re,shutil,subprocess,sys,time
from pathlib import Path
import voices_test as base
sys.path.insert(0,str(base.ROOT/'bots'))
import jk_botti_lab as jk
ROOT=base.ROOT;ENGINE=base.PROJECT/'runtime/vector-engine-bot-voice-validation';MOD=ENGINE/'valve'
SOURCE=base.PROJECT/'runtime/jk-botti-research/engine'
def stage():
 ENGINE.mkdir(parents=True,exist_ok=True)
 for p in SOURCE.iterdir():
  if p.is_file() and p.suffix.lower() in ('.exe','.dll'):shutil.copy2(p,ENGINE/p.name)
 for folder in ['valve','cs_assets']:
  shutil.copytree(SOURCE/folder,ENGINE/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('scrshots','save','*.log','*.matrix'))
 for part,path in [('server','dlls/hl.dll'),('client','cl_dlls/client.dll')]:shutil.copy2(ROOT/f'build/{part}'/Path(path).name,MOD/path)
 manifest=base.read(base.ASSETS/'manifest.json')
 for clip in manifest['clips']:
  out=MOD/'sound'/clip['path'];out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base.ASSETS/clip['path'].removeprefix('vf_voices/'),out)
 from death_voice_workshop import deploy as deploy_death_voices
 deploy_death_voices(MOD)
 shutil.copy2(ROOT/'data/voice_behavior.cfg',MOD/'vf_voice_behavior.cfg')
 # Autonomous bot movement is retained; only shooting is disabled for stable dialogue tests.
 config=MOD/'addons/jk_botti/jk_botti.cfg';s=config.read_text();s=s.replace('pause 2','pause 2\nbotdontshoot 1');config.write_text(s)
def phase(index,body):
 (MOD/f'bot_voice_phase_{index}.cfg').write_text(body+f'wait 5\nexec bot_voice_wait_{index}.cfg\n')
 (MOD/f'bot_voice_wait_{index}.cfg').write_text(f'wait 30\nexec bot_voice_wait_{index}.cfg\n')
def advance(index):
 p=MOD/f'bot_voice_wait_{index}.cfg';tmp=p.with_suffix('.tmp');tmp.write_text(f'exec bot_voice_phase_{index+1}.cfg\n');tmp.replace(p)
def entries(text):return re.findall(r'VFVoice social: player=(\d+) event=(\w+) reply_to=(\d+) bot=(\d+)',text)
def run():
 stage();jk.ENGINE=ENGINE;jk.MOD=MOD;jk.PORT=27105
 phase(0,'wait 180\ndeveloper 1\ngl_vsync 0\nfps_max 100\ncon_notifytime 0\nvf_voice_subtitles 2\ncmd vf_peer_pose\ncmd vf_voice_set nikos\nwait 20\necho BOT_HUMAN_READY\n')
 phase(1,'cmd vf_taunt\nwait 20\necho BOT_HUMAN_ZERO\n')
 phase(2,'cmd vf_voice_set nikos\ncmd vf_taunt\nwait 20\necho BOT_HUMAN_ONE\n')
 phase(3,'cmd vf_voice_set nikos\ncmd vf_taunt\nwait 20\nscreenshot scrshots/bot_counter_exchange.png\necho BOT_HUMAN_COUNTER\n')
 phase(4,'cmd vf_peer_pose\nweapon_9mmAR\nvf_reference\nwait 15\nvf_commit\nwait 10\nvf_ui_pointer 1220 40 1\nwait 2\nvf_ui_pointer 1220 40 0\nwait 5\n+lookdown\nwait 3\n-lookdown\ncmd vf_fx_profile electro\nwait 5\n+attack\nwait 240\n-attack\nwait 15\necho BOT_DEATH_DONE\n')
 phase(5,'quit\n')
 for name in ['bot-voice-server.log','bot-voice-client.log']:(ENGINE/name).unlink(missing_ok=True)
 server=jk.Server('vf_range','bot-voice-server.log');client=None
 def log():return server.log.read_text(errors='replace')
 def place():
  server.command('vf_bot_place 1 -355 -65 36 270');server.command('vf_bot_place 2 -155 -65 36 270')
 def wait(predicate,timeout=25):
  deadline=time.time()+timeout
  while time.time()<deadline:
   if predicate():return
   place();time.sleep(.3)
  raise AssertionError('bot voice condition timed out; tail='+log()[-1200:])
 def human_ready(marker):
  path=ENGINE/'bot-voice-client.log';wait(lambda:path.exists() and marker in path.read_text(errors='replace'),45)
 try:
  server.ready();server.command('vf_bot_taunts 0');server.command('jk_botti botdontshoot 1')
  wait(lambda:len([s for s in server.probe() if s['fake']])==2,25)
  server.command('vf_bot_taunt_chance 1');server.command('vf_bot_taunt_interval 2');server.command('vf_bot_counter_chance 1');server.command('vf_bot_counter_delay 0.1');server.command('vf_taunt_cooldown 1');server.command('vf_taunt_radius 1024');server.command('vf_bot_taunts 1')
  start=len(log());wait(lambda:any(x[1]=='taunt' and x[3]=='1' for x in entries(log()[start:])) and any(x[1]=='counter_taunt' and x[2] in ['1','2'] and x[3]=='1' for x in entries(log()[start:])),25)
  bot_exchange=entries(log()[start:]);server.command('vf_bot_taunts 0');time.sleep(1);mute_start=len(log());time.sleep(3);assert not entries(log()[mute_start:]),'bot mute failed'
  server.command('vf_bot_taunt_chance 0');server.command('vf_bot_counter_chance 0')
  client=subprocess.Popen([str(ENGINE/'xash3d.exe'),'-rodir',str(jk.STEAM),'-game','valve','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','bot-voice-client.log','-clientport','27106','+exec','lab_controls.cfg','+developer','1','+gl_vsync','0','+fps_max','100','+name','VOICE_HUMAN','+connect','127.0.0.1:27105','+exec','bot_voice_phase_0.cfg'],cwd=ENGINE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  human_ready('BOT_HUMAN_READY');place();server.command('vf_bot_taunts 1')
  start=len(log());advance(0);human_ready('BOT_HUMAN_ZERO');time.sleep(5)
  zero=log()[start:];assert ('3','taunt','0','0') in entries(zero),entries(zero);assert not any(x[3]=='1' for x in entries(zero)),entries(zero)
  assert re.search(r'VFVoice heard: listener=[12] source=3',zero),'bots did not hear human'
  server.command('vf_bot_counter_chance 1');start=len(log());advance(1);human_ready('BOT_HUMAN_ONE')
  wait(lambda:len({x[0] for x in entries(log()[start:]) if x[1]=='counter_taunt' and x[2]=='3' and x[3]=='1'})==2,20)
  human_to_bots=entries(log()[start:]);server.command('vf_bot_counter_chance 0');server.command('vf_bot_taunt_chance 1');start=len(log())
  wait(lambda:any(x[1]=='taunt' and x[3]=='1' for x in entries(log()[start:])) and re.search(r'VFVoice heard: listener=3 source=[12]',log()[start:]),20)
  advance(2);human_ready('BOT_HUMAN_COUNTER');assert any(x[0]=='3' and x[1]=='counter_taunt' and x[2] in ['1','2'] and x[3]=='0' for x in entries(log()[start:])),entries(log()[start:])
  server.command('vf_bot_taunts 0');server.command('sv_maxspeed 1');place();start=len(log());advance(3)
  wait(lambda:re.search(r'VFDeath play: entity=1 actor=\w+ cause=electro ',log()[start:]),25)
  human_ready('BOT_DEATH_DONE')
  assert 'VFProc player=1 effect=electro' in log()[start:]
  advance(4);client.wait(20);assert client.returncode==0
  received=(ENGINE/'bot-voice-client.log').read_text(errors='replace');assert re.search(r'VFVoice received: player=[12] actor=\w+ event=counter_taunt',received)
  assert 'VFVoice received: player=3 actor=nikos event=counter_taunt' in received
  assert re.search(r'VFDeath received: entity=1 actor=\w+ cause=electro ',received)
  assert not re.search(r'VFVoice play:.*?event=death ',log())
  assert 'Host_Error' not in log() and 'S_LoadSound:' not in log()
  report=dict(real_bots=2,human_clients=1,bot_exchange=bot_exchange,human_to_bots=human_to_bots,checks=['real jk_botti clients initiate taunts without injected speech commands','bots counter each other through ordinary auditory memory','bot master switch stops all new social speech','zero initiative and counter chances suppress bot speech','both bots hear and automatically answer the human when probability is one','a human answers an audible bot through the same key','native client receives bot and human counter clips','actual bullets proc Electro on a real bot and its fatal hit emits one contextual nonverbal cry'],scope='local dedicated server; voice behavior uses the mod player think hook alongside jk_botti navigation and combat')
  base.write_report('bot-voice-verification.json',report);print('PASS real bot voices',report,flush=True)
 finally:
  if client and client.poll()is None:client.terminate();client.wait(10)
  server.close()
if __name__=='__main__':run()
