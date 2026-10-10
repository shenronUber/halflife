"""Real damage deaths, anatomical variants, persistent corpses and native captures."""
import json,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import third_person_native_test as harness
from studio_assets import Studio
from animation_assets import sequence_frames
import numpy as np
OUT=ROOT/'build/death-visual';OUT.mkdir(parents=True,exist_ok=True)
MASKS={'none':0,'head':1,'left_arm':2,'right_arm':4,'left_leg':8,'right_leg':16,'all':31}
def assets():
 m=Studio(ROOT/'generated/deaths/persona_death.mdl');base=Studio(ROOT/'generated/personas/persona_rig.mdl')
 assert m.names==base.names and m.sequences[:77]==base.sequences
 assert all(np.allclose(a,b,atol=1e-4) for a,b in zip(m.bind,base.bind))
 for name in ['die_simple','headshot','gutshot','die_forwards']:assert np.allclose(sequence_frames(m,name),sequence_frames(base,name),atol=1e-4)
 e=sequence_frames(m,'vf_electro');fall=sequence_frames(base,'die_simple');assert np.allclose(e[-len(fall):],fall,atol=.005) and not np.allclose(e[5],e[0])
 full=m.mesh({0:-1,**{i+1:1 if i<11 else 0 for i in range(16)}});original=base.mesh({0:-1,1:0});assert len(original)==740 and len(full)>=740
 # Planar cuts subdivide the corpse mesh. Original UV corners remain, with
 # <=.02 model-unit recompilation rounding when a collar vertex changes bone.
 vertices=np.array([np.r_[v['p'],v['uv']] for _,t in full for v in t])
 for _,tri in original:
  for v in tri:
   candidates=vertices[np.max(abs(vertices[:,3:]-v['uv']),axis=1)<1e-6]
   assert len(candidates) and np.linalg.norm(candidates[:,:3]-v['p'],axis=1).min()<.02,'Original surface corner or UV changed'
 def area(mesh):return sum(np.linalg.norm(np.cross(t[1]['p']-t[0]['p'],t[2]['p']-t[0]['p']))*.5 for _,t in mesh)
 assert abs(area(full)/area(original)-1)<1e-4,'Cut subdivision changed the intact exterior surface'
 for missing in range(32):
  choices={i:int(not(missing&r) if i<11 else bool(missing&r)) for i,r in enumerate([1,0,2,4,2,4,8,16,8,16,0,1,2,4,8,16])}
  tri=m.mesh({0:-1,**{i+1:v for i,v in choices.items()}});assert tri and all(np.isfinite(v['p']).all() for _,t in tri for v in t)
 g=Studio(ROOT/'generated/deaths/persona_death_gibs.mdl');assert g.parts[0][1]==20 and g.numskinfamilies==196
 for i in range(20):assert g.mesh({0:i})
 print('PASS death geometry: original silhouette/UVs, 77 sequences, 32 anatomical combinations, electrical contraction, 20 fragments, 14 corpse skins and 196 fragment pairs',flush=True)
def run():
 assets();engine=harness.stage('death-visual');mod=engine/'vf_animation';(mod/'maps').mkdir(exist_ok=True);shutil.copy2(ROOT/'generated/test-room/vf_range.bsp',mod/'maps/vf_range.bsp')
 cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nr_drawviewmodel 0\ncmd give item_suit\ncmd give weapon_9mmAR\nweapon_9mmAR\nwait 15\n'
 for effect in ['standard','electro']:
  for name in MASKS:
   key=effect+'_'+name
   cfg+=f'cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_aim 0\nwait 3\necho CLEARED_{key}\nvf_death_client\necho BEGIN_{key}\ncmd vf_range_death 0 {name} {effect}\ncmd vf_range_death 0 {name} {effect}\nwait 8\nvf_death_client\nscreenshot scrshots/{key}_start.png\nwait 35\nscreenshot scrshots/{key}_motion.png\nwait 88\nvf_death_client\ncmd vf_range_info\nwait 4\nscreenshot scrshots/{key}_corpse.png\necho END_{key}\n'
 cfg+='cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_aim 0\ncmd vf_range_effect 0 electro\ncmd vf_range_kill 0\nwait 15\necho ACTIVE_STATE_DEATH\nvf_death_client\nwait 920\necho EXPIRED_CORPSE\nvf_death_client\n'
 cfg+='vf_death_lab\nwait 10\nscreenshot scrshots/death_menu.png\nvf_effects\nwait 5\n'
 cfg+='echo PLAYER_DEATH\ncmd vf_death_test head electro\nwait 160\nvf_death_client\necho PLAYER_END\nquit\n'
 (mod/'death_visual.cfg').write_text(cfg,encoding='ascii');start=time.monotonic()
 child=subprocess.Popen([str(engine/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','death-visual.log','+exec','lab_controls.cfg','+sv_cheats','1','+map','vf_range','+exec','death_visual.cfg'],cwd=engine)
 try:child.wait(timeout=80);assert child.returncode==0
 finally:
  if child.poll() is None:child.terminate();child.wait(10)
 log=(engine/'death-visual.log').read_text(errors='replace');(OUT/'native.log').write_text(log)
 for effect in ['standard','electro']:
  for name,mask in MASKS.items():
   key=effect+'_'+name;assert 'VFCorpse client' not in log.split('CLEARED_'+key,1)[1].split('BEGIN_'+key,1)[0],(key,'old corpse not cleared');part=log.split('BEGIN_'+key,1)[1].split('END_'+key,1)[0]
   corpses=re.findall(r'VFDeathVisual corpse=(\d+) victim=(\d+) mask=(\d+) effect=(-?\d+) sequence=(\w+)',part)
   assert len(corpses)==1 and int(corpses[0][2])==mask and int(corpses[0][3])==(-1 if effect=='standard' else 1),(key,corpses,part[-3000:])
   assert f'mask={mask} effect={-1 if effect=="standard" else 1}' in part and part.count('VFCorpse client')>=2,(key,part)
   assert 'health=300.0 alive=1' in part,(key,'target failed to respawn')
   if effect=='electro':assert 'sequence=vf_electro' in part
   for suffix in ['start','motion','corpse']:assert (mod/'scrshots'/f'{key}_{suffix}.png').stat().st_size>1000
 assert 'VFCorpse client' not in log.split('EXPIRED_CORPSE',1)[1].split('PLAYER_DEATH',1)[0]
 part=log.split('PLAYER_DEATH',1)[1].split('PLAYER_END',1)[0];assert re.search(r'VFDeathVisual corpse=\d+ victim=1 mask=1 effect=1',part),part
 for error in ['Host_Error','SV_Error','not precached','S_LoadSound:','Could not load','VFState rejected']:assert error not in log,error
 report=dict(seconds=round(time.monotonic()-start,2),checks=['original silhouette, UVs and 77 sequences unchanged','all 32 anatomical combinations valid; 20 themed fragments','14 real target deaths, standard and electrical independently of anatomical loss','one corpse per death; corpse survives target respawn','active effect captured on normal fatal damage','cadaver expiry clears client state','actual player head explosion with electrical death','native screenshots of initial pose, motion, settled corpse and menu'],log=str(OUT/'native.log'),captures=str(mod/'scrshots'))
 (OUT/'verification.json').write_text(json.dumps(report,indent=2));print('PASS native deaths',json.dumps(report),flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',action='store_true');args=p.parse_args()
 assets() if args.assets else run()
