"""Death anchoring, directional impact selection and non-repeating variant pools."""
import argparse,json,re,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of,sequence_info
import death_sounds_test as native
OUT=ROOT/'build/death-motion';OUT.mkdir(parents=True,exist_ok=True)

def assets():
 d=json.loads((ROOT/'assets/animations/death-atlas.json').read_text());m=Studio(ROOT/'generated/deaths/persona_death.mdl')
 living=globals_of(sequence_frames(m,'look_idle')[0],m.parents);motions={p['id']:p for p in d['motions']};records=[]
 for profile in d['profiles']:
  assert len(set(profile['motions']))==3
  assert sum(not motions[id]['directional'] for id in profile['motions'])>=2
 for pool in [d['standard_motions'],d['head_motions']]:assert len(set(pool))==3
 for motion in d['motions'][2:]:
  f=sequence_frames(m,motion['sequence']);g=np.array([globals_of(p,m.parents) for p in f]);drift=float(np.max(np.ptp(g[:,1,:2,3],axis=0)))
  assert drift<.015,(motion['id'],drift)
  assert np.max(abs(g[0,:,:3,:3]-living[:,:3,:3]))<.001,motion['id']
  assert np.max(abs(g[0,:,:2,3]-living[:,:2,3]))<.015,motion['id']
  assert not sequence_info(m,motion['sequence'])['flags']&1
  records.append(dict(motion=motion['id'],pelvis_drift=drift,sequence=m.sequences.index(motion['sequence'])))
 electric=[sequence_frames(m,motions[id]['sequence']) for id in ['electric','electric_back','electric_forward']]
 ends=[globals_of(f[-1],m.parents)[[11,13,17,24],:3,3] for f in electric]
 assert min(np.linalg.norm(a-b) for i,a in enumerate(ends) for b in ends[i+1:])>20
 result=dict(profiles=16,variants_per_profile=3,standard_variants=3,head_variants=3,motions=records,checks=['every automatic motion begins at the living pose and XY position','all automatic pelvis trajectories stay within .015 model units','two collapses per effect remain available from every shot direction','three electrical deaths end in different poses'])
 (OUT/'assets.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS death motion assets:',len(records),'anchored motions, 18 pools of 3 variants',flush=True);return d,m

def run():
 d,model=assets();e,m=native.setup('death-motion');motions={p['id']:p for p in d['motions']}
 cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nr_drawviewmodel 0\ncmd give weapon_9mmAR\nweapon_9mmAR\nwait 20\ncmd vf_range_aim 0\n'
 pools=[(p['effect'],'none',p['motions']) for p in d['profiles']]+[('standard','none',d['standard_motions']),('standard','head',d['head_motions'])]
 for i,(effect,region,pool) in enumerate(pools):
  cfg+=f'echo POOL_{i}\n'
  for j in range(5):cfg+=f'cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_death 0 {region} {effect} auto\nwait 6\n'
  cfg+=f'echo POOL_END_{i}\n'
 for side in ['front','back','left','right']:
  cfg+=f'echo SHOTS_{side}\n'
  for j in range(5):
   cfg+='cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_effect 0 kinetic\n'
   cfg+=''.join(f'cmd vf_range_fire 0 6 head {side}\n' for _ in range(10))
   cfg+='wait 6\n'
  cfg+=f'echo SHOTS_END_{side}\n'
 clips=['quaternius','impact_front','agony','electric','electric_back','electric_forward','spin','headshot']
 for clip in clips:
  cfg+=f'cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_aim 0\necho CLIP_{clip}\ncmd vf_range_death 0 none standard {clip}\nwait 6\nvf_death_client\nscreenshot scrshots/{clip}_start.png\nwait 415\nvf_death_client\nvf_engine_stats\nscreenshot scrshots/{clip}_end.png\necho CLIP_END_{clip}\n'
 cfg+='echo PLAYER_START\ncmd vf_death_clear\ncmd vf_death_test none standard quaternius\nwait 8\nvf_death_client\nwait 230\nvf_death_client\necho PLAYER_END\nquit\n'
 (m/'death_motion.cfg').write_text(cfg);start=time.monotonic();log=native.launch(e,'death_motion.cfg','death-motion.log');(OUT/'native.log').write_text(log)
 for error in ['Host_Error','SV_Error','not precached','Could not load','VFState rejected']:assert error not in log,error
 sequence=lambda part:re.findall(r'VFDeathVisual .*?sequence=(\w+)',part)
 pools_record=[]
 for i,(effect,region,pool) in enumerate(pools):
  part=log.split(f'POOL_{i} ')[1].split(f'POOL_END_{i} ')[0];chosen=sequence(part)
  assert len(chosen)==5 and all(s in [motions[id]['sequence'] for id in pool] for s in chosen),(i,chosen)
  assert all(a!=b for a,b in zip(chosen,chosen[1:])),(i,chosen)
  pools_record.append(dict(effect=effect,region=region,sequences=chosen))
 shot_records=[]
 for side in ['front','back','left','right']:
  part=log.split('SHOTS_'+side+' ')[1].split('SHOTS_END_'+side+' ')[0]
  lines=[s for s in part.splitlines() if 'VFDeathVisual corpse=' in s];assert len(lines)==5,(side,lines)
  for line in lines:
   name=re.search(r'sequence=(\w+)',line)[1];yaw=float(re.search(r'yaw=([\d.-]+)',line)[1])*np.pi/180
   impact=np.array([float(x) for x in re.search(r'impact=([\d.-]+),([\d.-]+)',line).groups()]);assert np.linalg.norm(impact)>.9,(side,line)
   local=np.array([np.cos(yaw)*impact[0]+np.sin(yaw)*impact[1],-np.sin(yaw)*impact[0]+np.cos(yaw)*impact[1]])
   expected={'front':[-1,0],'back':[1,0],'left':[0,-1],'right':[0,1]}[side];assert np.dot(local,expected)>.99,(side,local)
   motion=next(p for p in d['motions'] if p['sequence']==name)
   if motion['directional']:
    f=sequence_frames(model,name);a=globals_of(f[0],model.parents);b=globals_of(f[-1],model.parents);fall=((b[11,:2,3]+b[13,:2,3])-(a[11,:2,3]+a[13,:2,3]))*.5
    assert np.dot(fall,local)>=-.251*np.linalg.norm(fall),(side,name,fall)
  chosen=sequence(part);assert all(a!=b for a,b in zip(chosen,chosen[1:])),(side,chosen)
  shot_records.append(dict(side=side,sequences=chosen))
 for clip in clips:
  part=log.split('CLIP_'+clip+' ')[1].split('CLIP_END_'+clip+' ')[0];assert sequence(part)==[motions[clip]['sequence']]
  received=re.findall(r'VFCorpse client .*?frame=([\d.]+).*?origin_xy=([\d.-]+),([\d.-]+) yaw=([\d.-]+)',part)
  assert len(received)>=2 and float(received[-1][0])==255,(clip,received)
  positions=np.array([[float(x) for x in r[1:]] for r in received]);assert np.max(np.ptp(positions,axis=0))<.02,(clip,positions)
  assert 'grounded=1' in part and 'velocity_xy=0.00,0.00' in part and 'rejected=0' in part,(clip,part[-1000:])
 part=log.split('PLAYER_START ')[1].split('PLAYER_END ')[0];assert 'grounded=1' in part and 'velocity_xy=0.00,0.00' in part,part
 result=dict(seconds=round(time.monotonic()-start,2),pools=pools_record,shots=shot_records,completed_clips=clips,checks=['90 consecutive automatic deaths do not repeat their previous gesture','20 real bullet deaths retain the incoming front/back/left/right direction','opposing signature impacts excluded while two collapses remain available','eight representative deaths stay at their spawn XY and facing through frame 255','actual grounded player corpse does not inherit damage knockback'])
 (OUT/'native.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS native death motion',json.dumps(result),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--assets',action='store_true');run() if not p.parse_args().assets else assets()
