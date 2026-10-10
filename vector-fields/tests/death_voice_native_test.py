"""Real damage deaths across all six actors and elemental states in native Xash."""
import json,re,shutil,subprocess,time
from pathlib import Path
import voices_test as base
ROOT=base.ROOT;ENGINE=base.PROJECT/'runtime/vector-engine-death-validation';MOD=ENGINE/'vf_visual'
base.ENGINE=ENGINE;base.MOD=MOD

def block(name,body):return 'echo DEATH_BEGIN_'+name+'\n'+body+'wait 12\necho DEATH_END_'+name+'\n'
def section(log,name):return log.split('DEATH_BEGIN_'+name,1)[1].split('DEATH_END_'+name,1)[0]
def deaths(log):return re.findall(r'VFDeath play: entity=(\d+) actor=(\w+) cause=(\w+) sample=(\S+)',log)
def run():
 base.prepare();shutil.copy2(ROOT/'generated/test-room/vf_range.bsp',MOD/'maps/vf_range.bsp')
 manifest=base.read(ROOT/'assets/audio/operator-deaths/manifest.json');effects=base.read(ROOT/'data/effects.json')['effects']
 causes=[c['id'] for c in manifest['causes']];expected={}
 init='wait 180\ndeveloper 1\ngl_vsync 0\nfps_max 100\ncon_notifytime 0\nvf_voice_subtitles 2\ncmd vf_range_aim 0\nwait 20\n'
 files=[]
 for actor in base.ACTORS:
  cfg=''
  for effect in ['standard']+[e['id'] for e in effects]:
   name=actor+'_'+effect;cause=effect if effect in causes else 'standard'
   body=f'cmd vf_range_reset 0\ncmd vf_range_voice 0 {actor}\n'
   if effect!='standard':body+=f'cmd vf_range_effect 0 {effect}\n'
   body+='cmd vf_range_kill 0\ncmd vf_range_kill 0\n'
   cfg+=block(name,body);expected[name]=(actor,cause)
  name='death_'+actor+'.cfg';(MOD/name).write_text(cfg,encoding='ascii');files.append(name)
 extra=''
 cases={
  'pair':('cmd vf_range_effect 0 hydro\ncmd vf_range_effect 0 electro\n','arc_chain'),
  'reaction_priority':('cmd vf_range_effect 0 arc_chain\nwait 2\ncmd vf_range_effect 0 thermal\n','arc_chain'),
  'latest_primary':('cmd vf_range_effect 0 hydro\nwait 2\ncmd vf_range_effect 0 cryo\n','cryo'),
  'latest_reaction':('cmd vf_range_effect 0 arc_chain\nwait 2\ncmd vf_range_effect 0 toxic_ignition\n','toxic_ignition'),
  'expired':('cmd vf_range_effect 0 hydro .2\nwait 50\n','standard'),
  'cleared':('cmd vf_range_effect 0 hydro\ncmd vf_range_reset 0\n','standard'),
 }
 for name,(body,cause) in cases.items():
  extra+=block(name,'cmd vf_range_reset 0\ncmd vf_range_voice 0 rocco\n'+body+'cmd vf_range_kill 0\n');expected[name]=('rocco',cause)
 # This state enters through six genuine bullet traces, then genuine fatal damage.
 extra+=block('six_hits','cmd vf_range_reset 0\ncmd vf_range_voice 0 rocco\ncmd vf_fx_profile electro\ncmd vf_range_fire 0 6\ncmd vf_range_kill 0\n');expected['six_hits']=('rocco','electro')
 extra+=block('muted','cmd vf_range_reset 0\nvf_voices 0\nwait 10\ncmd vf_range_kill 0\nwait 10\nvf_voices 1\n')
 extra+='wait 240\ncmd vf_range_info\n'
 # Every actual player death selects from the state snapshot before it is cleared.
 for i,effect in enumerate(['standard']+[e['id'] for e in effects]):
  actor=base.ACTORS[i%len(base.ACTORS)];name='player_'+effect;cause=effect if effect in causes else 'standard'
  extra+='map vf_range\nwait 90\ndeveloper 1\n'
  body=f'cmd vf_voice_set {actor}\ncmd vf_status_dev 1\n'
  if effect!='standard':body+=f'cmd vf_status_apply {effect}\n'
  body+='cmd vf_voice_test '+('gib' if effect=='electro' else 'death')+'\ncmd vf_status_info\nwait 20\n'
  extra+=block(name,body);expected[name]=(actor,cause)
 extra+='map vf_range\nwait 100\ncmd vf_voice_set rocco\ncmd vf_status_dev 1\n'
 # Audition must not consume the real once-per-life death guard.
 extra+=block('audition','cmd vf_voice_preview death\ncmd vf_status_apply hydro\ncmd vf_voice_test death\nwait 20\n')
 extra+='quit\n';(MOD/'death_extra.cfg').write_text(extra,encoding='ascii');files.append('death_extra.cfg')
 (MOD/'death_run.cfg').write_text(init+''.join('exec '+f+'\n' for f in files),encoding='ascii')
 logpath=ENGINE/'death-native.log';logpath.unlink(missing_ok=True);start=time.monotonic()
 child=subprocess.Popen([str(ENGINE/'xash3d.exe'),'-rodir',base.STEAM,'-game','vf_visual','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log',logpath.name,'+exec','lab_controls.cfg','+sv_cheats','1','+developer','1','+map','vf_range','+exec','death_run.cfg'],cwd=ENGINE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:child.wait(timeout=150);assert child.returncode==0,child.returncode
 finally:
  if child.poll() is None:child.terminate();child.wait(10)
 log=logpath.read_text(errors='replace');assert 'VFDeath precache: actors=6 causes=17 clips=102' in log
 for name,(actor,cause) in expected.items():
  part=section(log,name);played=deaths(part)
  assert len(played)==1 and played[0][1:3]==(actor,cause),(name,played,part)
  assert played[0][3]==next(c['path'] for c in manifest['clips'] if c['actor']==actor and c['cause']==cause)
  assert len(re.findall(r'VFDeath received:',part))==1,(name,part)
  assert not re.search(r'(VFVoice play:.*?event=death |VFRange voice .*?event=death)',part),name
  if name.startswith('player_'):assert 'VFStatus active:' not in part and 'VFStatus clear: player=1' in part,name
  if name in [a+'_'+e for a in base.ACTORS for e in ['standard']+[x['id'] for x in effects]]:
   assert not re.search(r'VFRange voice .*?event=(hydro|electro|cryo|thermal|toxic|corrosion|sonic|kinetic|arc_chain|superconduction|shatter|resonant_impact|cavitation|caustic_contagion|toxic_ignition|steam_veil)',part),'pending cue escaped death '+name
 assert not deaths(section(log,'muted'))
 assert [(a,c) for _,a,c,_ in deaths(section(log,'audition'))]==[('rocco','standard'),('rocco','hydro')]
 assert not re.search(r'VFVoice play:.*?event=death |VFRange voice .*?event=death',log)
 for error in ['Host_Error','SV_Error','S_LoadSound:','missing sound']:assert error not in log,error
 report=dict(seconds=round(time.monotonic()-start,2),actors=6,bank_clips=102,target_deaths=6*22+7,player_deaths=23,checks=['all 102 short cries emitted through actual target damage deaths','all five tactical states fall back to standard for every actor','same selection on real player deaths across all 21 states, including a gib death','one cry per life; no old spoken deaths','instant death cancels queued effect dialogue','paired states before primaries, most recent within each category','expired and cleared states select standard','six real bullet traces proc the element before death','native positional sounds and caption-free VFDeath metadata reach the client','voice mute suppresses death audio; auditions do not swallow the next real death','player effects clear only after death selection'],server_sha256=base.hashlib.sha256((MOD/'dlls/hl.dll').read_bytes()).hexdigest(),client_sha256=base.hashlib.sha256((MOD/'cl_dlls/client.dll').read_bytes()).hexdigest(),log=str(logpath))
 assert report['server_sha256']==base.hashlib.sha256((ROOT/'build/server/hl.dll').read_bytes()).hexdigest()
 assert report['client_sha256']==base.hashlib.sha256((ROOT/'build/client/client.dll').read_bytes()).hexdigest()
 base.write_report('death-native-verification.json',report);print('PASS contextual deaths',json.dumps(report),flush=True)
if __name__=='__main__':run()
