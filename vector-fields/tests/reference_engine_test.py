"""Native 1080p validation of the original Relais R-01 reference weapon."""
import json,re,sys,struct
from pathlib import Path
from PIL import Image,ImageChops
from library_engine_test import run_cfg,click,ROOT,MOD
sys.path.insert(0,str(ROOT))
from studio_assets import Studio
import build_modular as base
import numpy as np

def assets():
 manifest=json.loads((ROOT/'generated/r01/manifest.json').read_text(encoding='utf-8'))
 rig=Studio(ROOT/'generated/r01/r01_rig.mdl')
 assert len(manifest['pieces'])==60 and len(rig.sequences)==9
 for record in manifest['pieces']:
  s=Studio(ROOT/'generated/r01'/(record['id']+'.mdl'));mesh=s.mesh()
  assert len(mesh)==record['triangles'] and len(s.names)==1
  for _,tri in mesh:
   assert all(np.isfinite(v['p']).all() and np.isfinite(v['n']).all() for v in tri)
  assert all(0<w<=256 and 0<h<=256 for _,w,h,_,_ in s.textures) # StudioMDL may crop unused texels.
 # An animated bolt must actually translate, not merely have a different name.
 text=(ROOT/'generated/r01/shoot1_1.smd').read_text(encoding='ascii')
 bid=int(re.search(r'(\d+) "R01_Bolt"',text)[1]);values=[float(m[1])for m in re.finditer(r'^'+str(bid)+r' 0 ([\d.\-]+) 0 0 0 0$',text,re.M)]
 assert len(values)>2 and max(values)-min(values)>.5
 # The reload socket retains the original pose in the new rig.
 old=Studio(ROOT/'generated/weapon_visuals/mp40_rig.mdl')
 for name in ['Bone71','Bone76']:assert np.allclose(rig.bind[rig.names.index(name)],old.bind[old.names.index(name)],atol=1e-5)
 return manifest

def run():
 manifest=assets();captures=[]
 def snap(name):
  name='r01_'+name;captures.append(name);return 'wait 16\nscreenshot scrshots/'+name+'.png\nwait 4\n'
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\nvf_dev\nwait 20\nvf_reference 0\nwait 35\nvf_animation_time 0\n'
 # Both presets and every part are rendered through the actual client.
 for v,letter in enumerate('ab'):
  if v:s+=click(445,170)+'wait 20\n'
  s+=snap('assembly_'+letter)+'vf_visual_bench r01_'+letter+'\nwait 215\n'
  s+=click(1000,602)
  for slot in range(9,21):
   s+=f'vf_select_slot {slot}\n'+snap(f'part_{slot}_{letter}')
  s+=click(1000,602)+click(1110,690)+'wait 30\n'+click(1220,40)+'wait 30\n'
  # Move away from the range ammo prop to inspect the weapon silhouette.
  if v==0:s+='+forward\nwait 25\n-forward\nwait 20\n'
  s+=snap('hand_'+letter)+'+attack\nwait 20\n-attack\nwait 30\n+reload\nwait 23\n'+snap('reload_'+letter)+'-reload\nwait 100\nvf_reference\nwait 25\nvf_animation_time 0\n'
 # Change one module via the same mouse route used by the player.
 s+='vf_select_slot 19\n'+click(1000,258)+snap('mixed_power')+click(1110,690)+'wait 30\n'
 s+=click(1220,40)+'+attack\nwait 20\n-attack\nwait 30\n+reload\nwait 50\n'+snap('reload_late')+'wait 30\n'+snap('reload_return')+'-reload\nwait 100\nvf_reference\nwait 25\n'
 s+=click(1090,40)+click(648,173)+snap('guide')+click(1090,40)
 s+=click(1220,40)+'save vf_r01_test\nwait 50\nload vf_r01_test\nwait 170\ndeveloper 1\ncon_notifytime 0\nvf_reference\nwait 30\nvf_animation_time 0\n'+snap('after_load')
 s+='vf_reference_audit\nvf_equipment_audit\nvf_engine_stats\nquit\n'
 assert len(s.encode('ascii'))<24000
 log=run_cfg('vf_r01_validation',s,captures=captures,timeout=150)
 assert 'VFR01 audit: checked=1700 failed=0 parts=12 combinations=169869312'in log
 assert 'VFEquipment audit: objects=248 passed=248 failed=0 max_parts=16'in log
 assert 'VFState rejected'not in log and 'rejected=0'in log
 assert log.count('VF equipment: result=0')>=3
 assert 'VFUI click: Circuit'in log
 assert 'VFEquipment selection: slot=19 id=r01_power_a'in log
 assert 'VFUI click: Isoler cette piece en 3D'in log
 assert 'VFUI click: Relais R-01'in log
 after=log.split('Loading game from save/vf_r01_test.sav')[-1]
 assert 'VFAppearance state: player=1 mode=0'in after
 assert 'VFR01 applied: receiver=r01_receiver_b power=r01_power_a'in after
 benches=re.findall(r'VFBench (\w+): samples=180 mean_ms=([\d.]+) p95_ms=([\d.]+) frame_ms=([\d.]+) loads=(\d+) textures_bytes=(\d+)',log)
 assert len(benches)==2 and all(int(b[4])==0 for b in benches),benches
 changes={}
 for slot in range(9,21):
  a=Image.open(MOD/'scrshots'/f'r01_part_{slot}_a.png').convert('RGB').crop((490,305,1210,726))
  b=Image.open(MOD/'scrshots'/f'r01_part_{slot}_b.png').convert('RGB').crop((490,305,1210,726))
  count=sum(max(x)>20 for x in ImageChops.difference(a,b).getdata());assert count>150,(slot,count);changes[slot]=count
 report=dict(captures=captures,resolution=[1920,1080],combinations=169869312,checked_assemblies=1700,parts=60,changed_pixels=changes,benchmarks=[dict(zip(['name','cpu_mean_ms','cpu_p95_ms','frame_ms','model_loads','texture_bytes'],b))for b in benches],checks=['24 compiled textured meshes, finite geometry','12 visually distinct variant pairs','1700 individual/pair native assemblies','248-item regression audit','real mouse-route presets, isolation, equip, mixed battery and guide','first-person firing and reload of both sets','save/load and linked mode retained','new bolt translation track and original reload socket preserved'],limits=['CPU preview timings, not GPU timings','individual/pair validation is not exhaustive full-build or visual inspection','MP5 gameplay retained','third-person weapon unchanged'])
 (ROOT/'build/reference-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('PASS Relais R-01:',len(captures),'1080p captures; 1700 assemblies; 60 meshes')
 print(json.dumps(report['benchmarks'],indent=2))
if __name__=='__main__':run()
