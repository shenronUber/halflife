"""Exercise server effect transitions and contextual speech in actual Xash DLLs."""
import argparse,json,re,subprocess,time,shutil
from pathlib import Path
import voices_test as base
ROOT=base.ROOT;ENGINE=base.ENGINE;MOD=base.MOD
ACTORS=base.ACTORS
EFFECTS=base.read(ROOT/'data/effects.json')['effects']
def click(x,y):return f'vf_ui_pointer {x} {y} 1\nwait 3\nvf_ui_pointer {x} {y} 0\nwait 10\n'
def block(name,body):return f'echo STATUS_BEGIN_{name}\n'+body+'wait 8\n'+f'echo STATUS_END_{name}\n'
def segment(log,name):return log.split(f'STATUS_BEGIN_{name}',1)[1].split(f'STATUS_END_{name}',1)[0]
def events(log):return re.findall(r'VFVoice play: player=1 actor=(\w+) event=(\w+)',log)
def native():
 base.prepare();cfg='wait 240\ndeveloper 1\ncon_notifytime 0\nfps_max 100\nwait 200\n'
 cfg+=block('disabled','cmd vf_status_apply hydro\nwait 30\n')
 cfg+='vf_effect_player_test\nwait 20\nscreenshot scrshots/status_panel_off.png\n'+click(960,292)
 cfg+=click(800,490)+'wait 20\nscreenshot scrshots/status_panel_on.png\n'
 cfg+=block('ui_apply',click(966,377)+'wait 40\ncmd vf_status_info\nvf_status_client\nscreenshot scrshots/status_hydro.png\n')
 cfg+='cmd vf_status_reset\nwait 15\n'
 for actor in ACTORS:
  cfg+=f'cmd vf_voice_set {actor}\nwait 10\n'
  for e in EFFECTS:
   cfg+=block(actor+'_'+e['id'],f'cmd vf_status_reset\nwait 3\ncmd vf_status_apply {e["id"]} 6\nwait 35\n')
 cfg+='cmd vf_voice_set viktor\nwait 10\n'
 cfg+=block('refresh','cmd vf_status_reset\nwait 4\ncmd vf_status_apply hydro 1\nwait 25\ncmd vf_status_apply hydro 6\nwait 35\ncmd vf_status_info\n')
 cfg+=block('rapid_pair','cmd vf_status_reset\nwait 4\ncmd vf_status_apply hydro\ncmd vf_status_apply electro\nwait 35\ncmd vf_status_info\nvf_status_client\n')
 cfg+=block('atomic_pair','cmd vf_status_reset\nwait 4\ncmd vf_status_pair toxic thermal\nwait 35\ncmd vf_status_info\n')
 cfg+='vf_effect_select toxic_ignition\nvf_effect_player_test\nwait 20\nscreenshot scrshots/status_reaction_panel.png\nvf_effects\nwait 5\n'
 cfg+=block('cancel','cmd vf_status_reset\nwait 4\ncmd vf_status_apply hydro\ncmd vf_status_clear\nwait 50\n')
 cfg+=block('expire','cmd vf_status_reset\nwait 4\ncmd vf_status_apply ward .3\nwait 60\ncmd vf_status_info\nvf_status_client\n')
 cfg+=block('invalid','cmd vf_status_reset\nwait 4\ncmd vf_status_apply unknown\ncmd vf_status_pair hydro cryo\ncmd vf_status_apply toxic nan\ncmd vf_status_apply toxic 31\nwait 30\ncmd vf_status_info\n')
 for probe in ['pain','armor','critical','burn','shock']:
  cfg+=block('action_'+probe,f'cmd vf_status_reset\nwait 4\ncmd vf_voice_test {probe}\nwait 60\n')
 cfg+=block('death','cmd vf_status_reset\nwait 4\ncmd vf_status_apply toxic\ncmd vf_voice_test death\nwait 60\ncmd vf_status_info\n')
 cfg+='map vf_range\nwait 240\ndeveloper 1\ncon_notifytime 0\n'
 cfg+=block('gib','cmd vf_voice_set lucien\nwait 5\ncmd vf_voice_test gib\nwait 80\n')
 cfg+='map vf_range\nwait 240\ndeveloper 1\ncon_notifytime 0\ncmd vf_status_dev 1\nwait 5\ncmd vf_voice_set diego\nwait 5\ncmd vf_status_apply ward 30\nwait 25\nsave vf_status_transient\nwait 60\nload vf_status_transient\nwait 180\ncmd vf_status_info\nvf_status_client\nscreenshot scrshots/status_after_load.png\nwait 5\nquit\n'
 assert len(cfg.encode())<24000,len(cfg)
 (MOD/'vf_status_native.cfg').write_text(cfg,encoding='ascii');started=time.time()
 p=subprocess.Popen([str(ENGINE/'xash3d.exe'),'-rodir',base.STEAM,'-game','vf_visual','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','status-native.log','+exec','lab_controls.cfg','+sv_cheats','1','+developer','1','+map','vf_range','+exec','vf_status_native.cfg'],cwd=ENGINE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:p.wait(timeout=230)
 except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
 assert p.returncode==0,p.returncode
 log=(ENGINE/'status-native.log').read_text(errors='replace')
 assert 'VFStatus rejected: enable developer effect testing' in segment(log,'disabled')
 assert events(segment(log,'ui_apply'))==[('rocco','hydro')],segment(log,'ui_apply')
 assert 'VFStatus client active: player=1 effect=hydro' in segment(log,'ui_apply')
 for actor in ACTORS:
  for e in EFFECTS:assert events(segment(log,actor+'_'+e['id']))==[(actor,e['id'])],(actor,e['id'],segment(log,actor+'_'+e['id']))
 assert events(segment(log,'refresh'))==[('viktor','hydro')]
 for name,event in [('rapid_pair','arc_chain'),('atomic_pair','toxic_ignition')]:
  section=segment(log,name);assert events(section)==[('viktor',event)],section
  assert f'VFStatus active: effect={event}' in section
  assert not re.search(r'VFStatus active: effect=(hydro|electro|toxic|thermal) ',section)
 for name in ['cancel','invalid']:assert not events(segment(log,name)),segment(log,name)
 expired=segment(log,'expire');assert 'VFStatus expired: player=1' in expired and 'VFStatus active:' not in expired and 'VFStatus client active:' not in expired
 for probe,event in [('pain','pain'),('armor','armor_break'),('critical','low_health'),('burn','thermal'),('shock','electro')]:assert events(segment(log,'action_'+probe))==[('viktor',event)],segment(log,'action_'+probe)
 assert not events(segment(log,'death')) and len(re.findall(r'VFDeath play: entity=1 actor=viktor cause=toxic ',segment(log,'death')))==1,segment(log,'death')
 assert 'VFStatus active:' not in segment(log,'death')
 assert not events(segment(log,'gib')) and len(re.findall(r'VFDeath play: entity=1 actor=lucien cause=standard ',segment(log,'gib')))==1,segment(log,'gib')
 tail=log.rsplit('VFStatus info:',1)[1];assert 'VFStatus active:' not in tail and 'VFStatus client active:' not in tail and 'developer=0' in tail
 for name in ['panel_off','panel_on','hydro','reaction_panel','after_load']:
  shot=MOD/'scrshots'/f'status_{name}.png';assert shot.stat().st_mtime>=started
 for error in ['Host_Error','SV_Error','S_LoadSound:']:assert error not in log,error
 report=dict(actors=len(ACTORS),effects=len(EFFECTS),actual_onsets=len(ACTORS)*len(EFFECTS),checks=['F3 pointer controls enable server testing, choose actor and apply a real state','every actor speaks once for every actual effect onset','refresh extends duration without repeated dialogue','rapid component application coalesces to one reaction line','atomic pair consumes its parents and speaks only the result','clear cancels pending dialogue','expiry removes server and client states','invalid IDs, incompatible pairs and invalid durations rejected','actual pain, armor break, critical health and elemental damage select contextual lines','normal and gib deaths each speak once and cancel pending effects','save/load clears temporary states and developer mode'],limits=['Effect states currently provide visuals and voice; combat balance and abilities remain undefined.','Audio intelligibility still benefits from human listening.'])
 base.write_report('status-native-verification.json',report);print('PASS status native',report,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['native'],default='native');p.parse_args();native()
