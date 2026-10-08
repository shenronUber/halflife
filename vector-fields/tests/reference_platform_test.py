"""Three R-01 feed layouts: geometry, grip continuity and actual 1080p renderer."""
import json,re,sys
from pathlib import Path
import numpy as np
from library_engine_test import run_cfg,click,ROOT,MOD
sys.path.insert(0,str(ROOT))
import build_reference_platforms as pf
import build_modular as base
from studio_assets import Studio

OUT=ROOT/'generated/r01'

def assets():
 manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
 assert len(manifest['pieces'])==26 and manifest['combinations']==8192
 motion=json.loads((OUT/'platform-motion.json').read_text())
 names,parents,_=base.skeleton(OUT/'mp40_hands.smd')
 _,original=pf.read_frames(OUT/'idle.smd');old=pf.globals_of(original[0],parents)
 expected_lengths=[np.linalg.norm(old[10][:3,3]-old[3][:3,3]),np.linalg.norm(old[12][:3,3]-old[10][:3,3])]
 frames_checked=0;max_error=0
 for key in ('side','top'):
  model=Studio(OUT/('r01_rig_'+key+'.mdl'))
  assert model.sequences==Studio(OUT/'r01_rig.mdl').sequences
  grip=np.array(motion[key]['grip'])
  for seq in ['idle','idle_1','shoot1','reload','draw','shoot1_1','shoot2','shoot2_1','empty_idle']:
   _,frames=pf.read_frames(OUT/(key+'_'+seq+'.smd'))
   for t,local in enumerate(frames):
    g=pf.globals_of(local,parents)
    lengths=[np.linalg.norm(g[10][:3,3]-g[3][:3,3]),np.linalg.norm(g[12][:3,3]-g[10][:3,3])]
    assert np.allclose(lengths,expected_lengths,atol=2e-5),(key,seq,t,lengths)
    assert all(np.isfinite(m).all()and abs(np.linalg.det(m[:3,:3])-1)<1e-5 for m in g.values())
    if seq=='reload'and t==18:
     hand=np.linalg.inv(g[40])@g[12]
     centre=(hand@np.array([.3,3.9,-2.1,1]))[:3]
     assert np.allclose(centre,[-9.25,15.25,.1]if key=='side'else[0,15.25,9.75],atol=2e-5)
     assert np.allclose(hand[:3,2],[0,-1,0]if key=='side'else[0,1,0],atol=2e-5) # visible fist / inward palm
    # From the serialized SMD, not the builder's internal error report.
    if key=='side' or seq=='reload'and 18<=t<=99:
     actual=np.linalg.inv(g[43])@g[12]
     error=np.max(abs(actual-grip));max_error=max(error,max_error)
     assert error<2e-5,(key,seq,t,error)
    frames_checked+=1
  _,reload=pf.read_frames(OUT/(key+'_reload.smd'))
  assert np.allclose(reload[0][43],reload[-1][43],atol=1e-6)
  outward=reload[34][43][:3,3]-reload[18][43][:3,3]
  assert outward[0]<-4 and abs(outward[2])<1e-5 if key=='side'else outward[2]>4 and abs(outward[0])<1e-5
  # Identical magazine connector ends exactly on this platform's entry plane.
  assert np.allclose((pf.mount_matrix(key)@np.r_[pf.SOURCE_ENTRY,1])[:3],pf.PLATFORMS[key]['entry'])
 rows=[x.split('|')for x in (ROOT/'data/equipment.txt').read_text(encoding='utf-8').splitlines()if x.startswith(('feed|','receiver|'))]
 mags=[x for x in rows if x[1].startswith('r01_feed_')]
 assert [x[1]for x in mags]==['r01_feed_a','r01_feed_b']
 chassis=[x for x in rows if x[1].startswith('r01_receiver_')]
 assert len(chassis)==4 and all(x[6:12]==chassis[0][6:12]for x in chassis)
 assert all(x[6:12]==mags[0][6:12]for x in mags)
 from r01_styles_engine_test import assets as styles
 _,style_checks=styles()
 return dict(serialized_frames=frames_checked,max_grip_error=max_error,styles=style_checks,checks=['left arm lengths unchanged','lateral hand holds magazine at idle and throughout all sequences','hand follows magazine during both reloads','centred lateral fist; top palm faces the player','directional extraction and identical seated endpoints','two shared magazine IDs and unchanged costs','26 meshes with seven finishes each'])

def native():
 captures=[]
 def snap(name):
  name='r01_platform_'+name;captures.append(name)
  return f'wait 5\nscreenshot scrshots/{name}.png\nwait 3\n'
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\n+forward\nwait 30\n-forward\nvf_reference 0\nwait 35\n'
 for variant in range(2):
  s+='vf_select_slot 12\n'+click(1000,258+variant*54)
  if variant:s+='vf_reference_style 3 12\n'
  for platform,label in enumerate(['bottom','side','top']):
   s+=click(910+platform*137,210)+'wait 25\nvf_reference_hands 0\nvf_animation 0\nvf_animation_time 0\n'+snap(f'{label}_{variant}_assembly')
   if variant==0:
    s+=f'vf_visual_bench platform_{label}\nwait 220\n'
    if platform:
     s+='vf_reference_hands 1\nvf_animation 3\n'
     for frame in [0,18,34,54,82,93,129]:
      s+=f'vf_animation_time {frame/50}\n'+snap(f'{label}_pose_{frame}')
     s+='vf_reference_hands 0\n'
   s+=click(1110,690)+'wait 25\n'+click(1220,40)+'wait 40\n'+snap(f'{label}_{variant}_hand')
   s+='+attack\nwait 20\n-attack\nwait 30\n+reload\nwait 35\n'+snap(f'{label}_{variant}_reload_out')+'wait 51\n'+snap(f'{label}_{variant}_reload_in')+'-reload\nwait 115\nvf_reference\nwait 30\n'
 s+='vf_reference_platform 3\nvf_reference_platform -1\nvf_reference_platform invalid\n'
 s+=click(1220,40)+'save vf_platform_test\nwait 45\nload vf_platform_test\nwait 190\ndeveloper 1\ncon_notifytime 0\nvf_reference\nwait 35\nvf_animation 0\nvf_animation_time 0\n'+snap('restored')
 s+='vf_select_slot 9\n'+click(1230,471)+snap('chassis_catalogue')
 s+=click(1090,40)+click(648,173)+snap('guide')+click(1090,40)
 s+='vf_reference_audit\nvf_equipment_audit\nvf_engine_stats\nquit\n'
 assert len(s)<24000
 log=run_cfg('vf_platform_validation',s,captures=captures,timeout=180)
 assert 'VFR01 audit: combinations=8192 failed=0 parts=12'in log
 assert 'VFEquipment audit: objects=154 passed=154 failed=0'in log
 assert 'rejected=0'in log and 'VFState rejected'not in log
 for p in range(3):
  for mag in ['a','b']:assert f'VFR01 platform: {p} feed=r01_feed_{mag}'in log,(p,mag)
 for label in ['Dessous','Lateral','Dessus']:assert 'VFUI click: '+label in log
 after=log.split('Loading game from save/vf_platform_test.sav')[-1]
 assert 'VFR01 applied: receiver=r01_receiver_top power=r01_power_a'in after
 assert 'VFR01 state: player=1 first=0 optic=0 feed=3'in after
 bench=re.findall(r'VFBench (\w+): samples=180 mean_ms=([\d.]+) p95_ms=([\d.]+) frame_ms=([\d.]+) loads=(\d+) textures_bytes=(\d+)',log)
 assert len(bench)==3 and all(int(row[4])==0 for row in bench),bench
 return dict(captures=captures,benchmarks=[dict(zip(['name','mean_cpu_ms','p95_cpu_ms','frame_ms','model_loads','texture_bytes'],row))for row in bench],checks=['all three selectors clicked through native pointer routing','both unchanged magazines on all three platforms','first-person shooting and reload for all six combinations','top chassis and feed finish restored after save/load','8192 assemblies accepted, 154-equipment regression audit'],resolution=[1920,1080])

if __name__=='__main__':
 report=dict(assets=assets(),native=native(),limits=['existing MP5 firing, ammo and gameplay reload time','shared glove/finger grip; no dedicated latch finger animation','third-person weapon still stock','CPU preview timing is not GPU timing; combinations audit is not exhaustive visual inspection'])
 (ROOT/'build/reference-platform-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('PASS R-01 platforms',report['assets'])
 print(json.dumps(report['native']['benchmarks'],indent=2))
