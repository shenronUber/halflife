"""Actual bullet deaths select anatomy; no vf_range_death mask override."""
import json,re,sys,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import death_sounds_test as audio
OUT=ROOT/'build/death-automatic';OUT.mkdir(parents=True,exist_ok=True)

def run():
 e,m=audio.setup('death-automatic')
 cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\ncmd give weapon_9mmAR\nweapon_9mmAR\nwait 20\n'
 cases=[('head',{1}),('left_arm',{2}),('right_arm',{4}),('left_leg',{8}),('right_leg',{16}),('chest',{0})]
 for region,_ in cases:
  cfg+='cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_voice 0 rocco\ncmd vf_range_aim 0\nstopsound\necho BEGIN_'+region+'\n'
  for i in range(10):cfg+='cmd vf_range_fire 0 6'+(' '+region if region!='chest' else '')+'\n'
  cfg+='wait 12\nsave vf_auto_'+region+'\nvf_death_client\nscreenshot scrshots/auto_'+region+'.png\nwait 240\necho END_'+region+'\n'
 cfg+='cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_voice 0 rocco\nstopsound\necho BEGIN_stale_head\ncmd vf_range_fire 0 1 head\nwait 3\ncmd vf_range_kill 0\nwait 12\nsave vf_auto_stale\nwait 240\necho END_stale_head\n'
 cfg+='cmd vf_death_clear\ncmd vf_voice_set rocco\nstopsound\necho BEGIN_player_head\ncmd vf_death_test head standard\nwait 12\nscreenshot scrshots/player_head.png\nwait 240\necho END_player_head\nquit\n'
 (m/'death_automatic.cfg').write_text(cfg,encoding='ascii')
 started=time.monotonic();log=audio.launch(e,'death_automatic.cfg','death-automatic.log')
 (OUT/'native.log').write_text(log)
 for error in ['Host_Error','SV_Error','not precached','Could not load','VFState rejected']:assert error not in log,error
 verified=[]
 for region,allowed in cases+[('stale_head',{0})]:
  part=log.split('BEGIN_'+region+' ')[1].split('END_'+region+' ')[0]
  deaths=re.findall(r'VFDeathVisual corpse=\d+ victim=\d+ mask=(\d+) effect=(-?\d+) sequence=(\w+)',part)
  assert len(deaths)==1 and int(deaths[0][0]) in allowed,(region,deaths,part[-4000:])
  fragments=re.findall(r'VFFragment spawn entity=\d+ body=(\d+) effect=(-?\d+) whole=(\d+)',part)
  expected=4 if int(deaths[0][0]) else 0
  assert len(fragments)==expected and sum(int(f[2]) for f in fragments)==(1 if expected else 0),(region,fragments)
  channels=audio.mixer_channels(m/'save'/('vf_auto_'+('stale' if region=='stale_head' else region)+'.sav'))
  layers=[c['name'] for c in channels if c.get('name','').startswith(('vf_deaths/','vf_death_sfx/'))]
  if region=='head':
   assert layers==['vf_death_sfx/head_kinetic.wav'],layers
   assert 'VFDeath voice suppressed:' in part and 'VFDeath play:' not in part
  elif region=='stale_head':
   assert layers==['vf_deaths/rocco/standard_v2.wav'],layers
  elif region=='chest':
   assert len(layers)==2 and 'vf_death_sfx/dismemberment_kinetic.wav' not in layers,layers
  else:
   assert len(layers)==3 and 'vf_death_sfx/dismemberment_kinetic.wav' in layers,layers
  if region!='stale_head':shutil.copy2(m/'scrshots'/('auto_'+region+'.png'),OUT/('auto_'+region+'.png'))
  verified.append(dict(region=region,mask=int(deaths[0][0]),sequence=deaths[0][2],fragments=fragments,mixer=layers))
 part=log.split('BEGIN_player_head ')[1].split('END_player_head ')[0]
 assert 'VFDeath voice suppressed: entity=1 reason=head_missing' in part and 'VFDeath play:' not in part,part
 assert 'sample=vf_death_sfx/head_standard.wav' in part and part.count('VFFragment spawn')==4,part
 shutil.copy2(m/'scrshots/player_head.png',OUT/'player_head.png')
 result=dict(seconds=round(time.monotonic()-started,2),cases=verified,checks=['real bullet head/arm/leg deaths detach only a region above half maximum health with a matching fatal hit','torso fatal impact removes no member','unlocalized later fatal damage does not reuse a stale headshot','one whole member and three physical debris pieces per loss','head loss plays its sole elemental pumpkin explosion with no cry'])
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS automatic death',json.dumps(result),flush=True)
if __name__=='__main__':run()
