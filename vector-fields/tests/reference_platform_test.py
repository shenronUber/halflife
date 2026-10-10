"""Three R-01 feed layouts: geometry, grip continuity and actual 1080p renderer."""
import argparse,json,re,sys,math
from pathlib import Path
import numpy as np
from library_engine_test import run_cfg,click,ROOT,MOD
sys.path.insert(0,str(ROOT))
import build_reference_platforms as pf
import build_modular as base
from animation_assets import sequence_info
from studio_assets import Studio

OUT=ROOT/'generated/r01'

def assets():
 manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
 assert len(manifest['pieces'])==61 and manifest['combinations']==191102976
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
     assert np.allclose(centre,[-9.25,15.25,.1]if key=='side'else[0,15.25,8.45],atol=2e-5)
     if key=='side':assert hand[2,2]>.7 and .5<hand[1,2]*-1<.7,'lateral palm must face down/forward with a relaxed wrist'
     else:assert np.allclose(hand[:3,2],[0,1,0],atol=2e-5)
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
 rows=[x.split('|')for x in (ROOT/'data/equipment.txt').read_text(encoding='utf-8').splitlines()if x.startswith(('feed|','receiver|')) and len(x.split('|'))==14]
 mags=[x for x in rows if x[1].startswith('r01_feed_')]
 assert [x[1]for x in mags]==['r01_feed_a','r01_feed_b','r01_feed_c','r01_feed_d']
 chassis=[x for x in rows if x[1].startswith('r01_receiver_')]
 assert len(chassis)==9 and all(x[6:12]==chassis[0][6:12]for x in chassis)
 assert all(x[6:12]==mags[0][6:12]for x in mags)
 from r01_styles_engine_test import assets as styles
 _,style_checks=styles()
 return dict(serialized_frames=frames_checked,max_grip_error=max_error,styles=style_checks,checks=['left arm lengths unchanged','lateral hand holds magazine at idle and throughout all sequences','hand follows magazine during both reloads','centred overhand lateral grasp; top palm faces the player','directional extraction and identical seated endpoints','four shared magazine IDs and unchanged costs','61 meshes with all installed finishes'])

def audit_counts():
 manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
 counts=[sum(p['slot_index']==slot for p in manifest['pieces']) for slot in range(9,21)]
 checked=sum(counts)+sum(a*b for i,a in enumerate(counts) for b in counts[i+1:])
 rows=[x for x in (ROOT/'data/equipment.txt').read_text(encoding='utf-8').splitlines() if x and not x.startswith(('#','limits|'))]
 return checked,len(rows),math.prod(counts)


def native():
 captures=[]
 def snap(name):
  name='r01_platform_'+name;captures.append(name)
  return f'wait 5\nscreenshot scrshots/{name}.png\nwait 3\n'
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\ngod\nvf_reference\nwait 30\nvf_item r01_underbarrel_b__original\n'
 for platform,receiver in [('bottom','a'),('side','side'),('top','arch_top')]:
  s+=f'vf_item r01_receiver_{receiver}__original\n'
  for mag in 'abcd':
   s+=f'vf_item r01_feed_{mag}__original\nvf_commit\nwait 25\n'
   if mag=='a':s+=f'vf_visual_bench platform_{platform}\nwait 220\n'+snap(platform+'_assembly')
   s+=click(1220,40)+f'echo PLATFORM_{platform}_{mag}\nvf_engine_stats\n'
   s+='+attack\nwait 12\n-attack\nwait 15\n+reload\nwait 30\n'+snap(f'{platform}_{mag}_out')+'wait 70\n'+snap(f'{platform}_{mag}_in')+'wait 80\n-reload\nvf_reference\nwait 25\n'
 s+='vf_item r01_receiver_arch_top__dieselpunk\nvf_commit\nwait 25\n'+click(1220,40)+'save vf_platform_test\nwait 40\nload vf_platform_test\nwait 180\ndeveloper 1\ncon_notifytime 0\necho PLATFORM_RESTORED\nvf_engine_stats\n'+snap('restored')
 s+='vf_reference_audit\nvf_equipment_audit\nvf_engine_stats\nquit\n'
 log=run_cfg('vf_platform_validation',s,captures=captures,timeout=180)
 checked,objects,combinations=audit_counts()
 assert f'VFR01 audit: checked={checked} failed=0 parts=12 combinations={combinations}' in log
 assert f'VFEquipment audit: objects={objects} passed={objects} failed=0' in log
 assert 'rejected=0' in log and 'VFState rejected' not in log
 for platform,suffix in [('bottom',''),('side','_side'),('top','_top')]:
  for mag in 'abcd':
   marker=re.search(f'PLATFORM_{platform}_{mag}'+r'\s*\n',log);assert marker
   section=log[marker.end():].split('PLATFORM_',1)[0]
   assert f'rig=models/vf_r01/r01_rig{suffix}.mdl' in section,(platform,mag)
 restored=log.split('Loading game from save/vf_platform_test.sav')[-1]
 assert 'VFR01 state: player=1 first=13' in restored
 assert 'rig=models/vf_r01/r01_rig_top.mdl' in restored
 bench=re.findall(r'VFBench (\w+): samples=180 mean_ms=([\d.]+) p95_ms=([\d.]+) frame_ms=([\d.]+) loads=(\d+) textures_bytes=(\d+)',log)
 assert len(bench)==3 and all(int(row[4])==0 for row in bench),bench
 return dict(captures=captures,benchmarks=[dict(zip(['name','mean_cpu_ms','p95_cpu_ms','frame_ms','model_loads','texture_bytes'],row))for row in bench],checked_assemblies=checked,equipment_objects=objects,checks=['current named inventory items selected individually','four magazines fire and reload on all three platforms','top chassis and immutable finish restored after save/load','all individual and pair assemblies accepted'],resolution=[1920,1080])


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['assets','native','all'],default='all');args=p.parse_args();report={}
 if args.mode in ('assets','all'):report['assets']=assets()
 if args.mode in ('native','all'):report['native']=native()
 report['limits']=['native captures need artistic review; pair coverage is not exhaustive full-build inspection','CPU preview timing is not GPU timing']
 (ROOT/'build/reference-platform-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('PASS R-01 platforms',args.mode,json.dumps(report))
