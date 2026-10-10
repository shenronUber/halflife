"""Measured wound UVs, animated edge continuity, and close native screenshots."""
import argparse,json,re,struct,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of
from death_wounds import REGIONS,DENSITY,PIXELS
import third_person_native_test as harness
OUT=ROOT/'build/wound-textures';OUT.mkdir(parents=True,exist_ok=True)
NAMES=['head','left_arm','right_arm','left_leg','right_leg']

def assets():
 report=json.loads((ROOT/'generated/deaths/manifest.json').read_text());m=Studio(ROOT/'generated/deaths/persona_death.mdl');g=Studio(ROOT/'generated/deaths/persona_death_gibs.mdl')
 assert struct.unpack_from('<i',m.data,212)[0]==4,'GoldSrc client stores only four attachments'
 assert len(m.parts)==17 and report['clothing_groups']==11
 intact=m.mesh({0:-1,**{i:1 for i in range(1,12)},**{i:0 for i in range(12,17)}})
 pelvis=m.mesh({i:1 if i==11 else -1 for i in range(17)});assert len(pelvis)>0
 poses=[globals_of(p,m.parents) for name in ['look_idle','headshot','die_simple','gutshot','die_forwards','vf_electro']+[c['id'] for c in report.get('imported_animations',[])] for p in sequence_frames(m,name)]
 checks=[]
 for index,(region,label,family,bone) in enumerate(REGIONS):
  wound=report['wounds'][index];chart=wound['charts'][0];record=report['wound_textures'][index];material=record['material']
  assert record['size']==[PIXELS,PIXELS] and record['texels_per_unit']==DENSITY
  with Image.open(ROOT/'generated/deaths'/material) as im:assert im.mode=='P' and im.size==(PIXELS,PIXELS)
  cap=m.mesh({i:1 if i==index+12 else -1 for i in range(17)})
  assert chart['depth_n']<(1.6 if region==1 else 1e-3),'Unexpected cut depth'
  assert len(cap)==chart['edge_count'] and {m.textures[t][0] for t,_ in cap}=={material}
  points=[];offsets=[];texture=next(t for t in m.textures if t[0]==material)
  for _,tri in cap:
   normal=np.cross(tri[1]['p']-tri[0]['p'],tri[2]['p']-tri[0]['p']);assert np.dot(normal,report['cut_planes'][str(region)]['n'])>0,'Wound faces into the body'
   q=np.array([v['uv'] for v in tri]);assert abs(np.linalg.det(np.column_stack((q[1]-q[0],q[2]-q[0]))))>1e-7,'UV triangle collapsed'
   for v in tri:
    expected=(.5+(v['p']-chart['uv_origin'])@np.array(chart['uv_axes']).T/16)*256;actual=v['uv']*np.array(texture[1:3]);offsets.append(actual-expected)
    if np.linalg.norm(v['p']-chart['center'])>.02 and not any(np.linalg.norm(v['p']-p['p'])<.001 for p in points):points.append(v)
  rounding_range=np.ptp(np.array(offsets),axis=0);assert max(rounding_range)<1.2,'Compiler changed physical UV scale beyond pixel rounding'
  max_gap=0
  for v in points:
   candidates=[p for _,tri in intact for p in tri if p['b']==v['b'] and np.linalg.norm(p['p']-v['p'])<.001]
   assert candidates,(label,'cap border changed bone or position',v)
   neighbor=min(candidates,key=lambda p:np.linalg.norm(p['p']-v['p']))
   for pose in poses:
    mat=pose[v['b']]@np.linalg.inv(m.bind[v['b']]);gap=np.linalg.norm((mat@np.r_[v['p'],1])-(mat@np.r_[neighbor['p'],1]));max_gap=max(max_gap,float(gap))
  assert max_gap<.001
  for skin in range(14):assert {m.textures[t][0] for t,_ in m.mesh({i:1 if i==index+12 else -1 for i in range(17)},skin=skin)}=={material}
  for model,key in [(m,'corpse'),(g,'fragments')]:
   tex=next(t for t in model.textures if t[0]==material);assert list(tex[1:3])==record['compiled_pixels'][key]
   count,offset=struct.unpack_from('<ii',model.data,180);ti=next(i for i,t in enumerate(model.textures) if t[0]==material);flags=struct.unpack_from('<i',model.data,offset+ti*80+64)[0];assert flags==1,'Wound must use opaque flat light, without emissive or additive flags'
  checks.append(dict(label=label,animated_border_vertices=len(points),maximum_gap=max_gap,compiled_uv_rounding_range_pixels=rounding_range.tolist(),poses=len(poses)))
 for mask in range(32):
  choices={0:-1,**{i+1:int(not(mask&r) if i<11 else bool(mask&r)) for i,r in enumerate(report['regions'])}}
  visible=m.mesh(choices);assert all(any(p['b']==v['b'] and np.linalg.norm(p['p']-v['p'])<.001 for _,t in visible for p in t) for _,tri in pelvis for v in tri),'Pelvis removed'
 for part in range(20):
  tri=g.mesh({0:part});assert any(g.textures[t][0].startswith('death_') for t,_ in tri)
  for skin in range(14):assert {g.textures[t][0] for t,_ in g.mesh({0:part},skin=skin) if g.textures[t][0].startswith('death_')}=={g.textures[t][0] for t,_ in tri if g.textures[t][0].startswith('death_')}
 report['continuity_checks']=checks
 (OUT/'measurements.json').write_text(json.dumps({k:v for k,v in report.items() if k!='build_cache'},indent=2))
 print('PASS wound assets: five 2D UV charts, constant 16 px/unit, 14 skins, animated borders, pelvis intact in 32 combinations, 20 closed fragments',flush=True)
 return report

def run():
 assets();engine=harness.stage('wound-textures');mod=engine/'vf_animation';(mod/'maps').mkdir(exist_ok=True);shutil.copy2(ROOT/'generated/test-room/vf_range.bsp',mod/'maps/vf_range.bsp')
 cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nr_drawviewmodel 0\ndefault_fov 35\ncmd give item_suit\nnoclip\nwait 3\n'
 for name in NAMES:
  cfg+=f'cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_aim 0\nwait 3\necho BEGIN_WOUND_{name}\ncmd vf_range_death 0 {name} standard\nwait 140\ncmd vf_death_inspect {name}\nwait 10\nvf_engine_stats\nvf_death_client\nscreenshot scrshots/wound_{name}.png\necho END_WOUND_{name}\nwait 6\n'
 cfg+='cmd vf_death_clear\ndefault_fov 90\nnoclip\nvf_death_lab\nwait 10\nvf_ui_pointer 1100 445 1\nwait 3\nvf_ui_pointer 1100 445 0\nwait 35\nvf_engine_stats\nscreenshot scrshots/wound_electro.png\nwait 130\nscreenshot scrshots/wound_electro_corpse.png\nwait 8\nquit\n'
 (mod/'wound_textures.cfg').write_text(cfg,encoding='ascii');started=time.monotonic()
 child=subprocess.Popen([str(engine/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','wound-textures.log','+sv_cheats','1','+map','vf_range','+exec','wound_textures.cfg'],cwd=engine)
 try:child.wait(timeout=40);assert child.returncode==0
 finally:
  if child.poll() is None:child.terminate();child.wait(10)
 log=(engine/'wound-textures.log').read_text(errors='replace');(OUT/'native.log').write_text(log)
 for name in NAMES:
  part=log.split('BEGIN_WOUND_'+name)[1].split('END_WOUND_'+name)[0];assert 'VFWound inspect region='+name in part and 'rejected=0' in part,part
  source=mod/'scrshots'/('wound_'+name+'.png');assert source.stat().st_size>1000;shutil.copy2(source,OUT/source.name)
 for name in ['wound_electro.png','wound_electro_corpse.png']:shutil.copy2(mod/'scrshots'/name,OUT/name)
 assert 'VFUI click: Tete explosee' in log and 'mask=1 effect=1 sequence=vf_electro' in log
 for error in ['Host_Error','SV_Error','not precached','Could not load','VFState rejected','bad attachment']:assert error not in log,error
 result=dict(seconds=round(time.monotonic()-started,2),checks=['five native close views of measured wounds','actual F8 head/electric death and settled corpse','native renderer accepts all new bodygroups'],captures=str(OUT),log=str(OUT/'native.log'))
 (OUT/'native-verification.json').write_text(json.dumps(result,indent=2));print('PASS native wound rendering',json.dumps(result),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',action='store_true');args=p.parse_args();assets() if args.assets else run()
