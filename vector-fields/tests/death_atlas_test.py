"""Effect-atlas assignments, projected anatomical entities and moving trails."""
import argparse,json,re,shutil,subprocess,sys,time
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from studio_assets import Studio
import death_atlas
import third_person_native_test as harness
OUT=ROOT/'build/death-atlas';OUT.mkdir(parents=True,exist_ok=True)
REGIONS=['head','left_arm','right_arm','left_leg','right_leg']
def assets():
 d=json.loads(death_atlas.DATA.read_text());m=Studio(ROOT/'generated/deaths/persona_death.mdl');g=Studio(ROOT/'generated/deaths/persona_death_gibs.mdl');manifest=json.loads((ROOT/'generated/deaths/manifest.json').read_text())
 assert len(d['profiles'])==16 and len(manifest['imported_animations'])==10
 ids={o['id']:o for o in d['motions']}
 status=(ROOT.parent/'game_shared/vf_status_catalog.h').read_text();positions=[]
 for p in d['profiles']:
  positions.append(status.index('"'+p['effect']+'"'));assert 0<p['fx_seconds']<12
  for id in p['motions']:assert ids[id]['sequence'] in m.sequences
 assert positions==sorted(positions) and all(len(p['motions']) in [1,2] for p in d['profiles'])
 assert g.parts[0][1]==20
 for i,name in enumerate(REGIONS):
  tri=g.mesh({0:15+i});small=[g.mesh({0:i*3+k}) for k in range(3)];points=np.array([v['p'] for _,t in tri for v in t]);bounds=np.ptp(points,axis=0)
  assert len(tri)>max(len(t) for t in small),name
  assert bounds.max()>(8 if i==0 else 22),name
  assert any(g.textures[t][0]==manifest['wound_textures'][i]['material'] for t,_ in tri),name
  assert all(v['b']==0 for _,t in tri for v in t),name
  info=manifest['fragments'][15+i];assert info['kind']=='whole' and info['region']==1<<i
 result=dict(profiles=len(d['profiles']),imported_clips=10,new_mixamo_clips=7,whole_limbs=5,small_fragments=15,checks=['all elemental profile pools resolve to compiled sequences','profile order matches server catalog','recognizable rigid head/arms/legs with wound materials','existing fragment indices 0..14 retained'])
 (OUT/'assets-verification.json').write_text(json.dumps(result,indent=2));print('PASS atlas assets',json.dumps(result),flush=True);return d

def run():
 d=assets();e=harness.stage('death-atlas');m=e/'vf_animation';(m/'maps').mkdir(exist_ok=True);shutil.copy2(ROOT/'generated/test-room/vf_range.bsp',m/'maps/vf_range.bsp')
 s='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nr_drawviewmodel 0\ncmd give item_suit\ncmd give weapon_crowbar\ncmd weapon_crowbar\nnoclip\ndefault_fov 50\nwait 10\n'
 previews={'electro','cryo','thermal','toxic','corrosion','sonic','kinetic','arc_chain'}
 for i,p in enumerate(d['profiles']):
  id=p['effect'];region=REGIONS[i%5];s+=f'cmd vf_death_clear\ncmd vf_range_reset 0\necho BEGIN_{id}\ncmd vf_range_death 0 {region} {id} auto\ncmd vf_death_view scene\nwait 6\nvf_death_client\nscreenshot scrshots/{id}_start.png\n'
  if id in previews:
   for f in range(12):s+=f'wait {54 if id=="toxic" else 24}\nscreenshot scrshots/{id}_{f:02}.png\n'+('vf_death_client\n' if f in (0,2,5) else '')
  else:s+='wait 42\nvf_death_client\n'
  s+=f'wait {780 if id not in previews else 250}\nvf_death_client\nvf_engine_stats\nscreenshot scrshots/{id}_end.png\necho END_{id}\nwait 6\n'
 # Menu effect selection and paginated catalogue remain independently usable.
 s+='cmd vf_death_clear\ncmd vf_range_reset 0\ndefault_fov 90\nvf_death_lab\nwait 10\necho ATLAS_GUI\nvf_ui_pointer 620 258 1\nwait 3\nvf_ui_pointer 620 258 0\nwait 3\nscreenshot scrshots/atlas_menu.png\nvf_ui_pointer 190 408 1\nwait 3\nvf_ui_pointer 190 408 0\nwait 3\nvf_ui_pointer 1100 445 1\nwait 3\nvf_ui_pointer 1100 445 0\nwait 40\nvf_death_client\necho ATLAS_GUI_END\n'
 s+='cmd vf_death_clear\nvf_death_lab\nwait 8\necho CATALOG_GUI\nvf_ui_pointer 490 258 1\nwait 3\nvf_ui_pointer 490 258 0\nwait 3\nvf_ui_pointer 610 568 1\nwait 3\nvf_ui_pointer 610 568 0\nwait 3\nscreenshot scrshots/catalog_page2.png\nvf_ui_pointer 290 459 1\nwait 3\nvf_ui_pointer 290 459 0\nwait 3\nvf_ui_pointer 1100 445 1\nwait 3\nvf_ui_pointer 1100 445 0\nwait 40\nvf_death_client\necho CATALOG_GUI_END\n'
 s+='cmd vf_death_clear\nwait 100\necho CLEARED_ATLAS\nvf_death_client\nwait 8\nquit\n'
 (m/'atlas.cfg').write_text(s);started=time.monotonic();p=subprocess.Popen([str(e/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','atlas.log','+sv_cheats','1','+map','vf_range','+exec','atlas.cfg'],cwd=e)
 try:p.wait(timeout=220);assert p.returncode==0
 finally:
  if p.poll() is None:p.terminate();p.wait(10)
 return verify(e,d,started)

def verify(e,d,started=None):
 import hashlib
 m=e/'vf_animation';log=(e/'atlas.log').read_text(errors='replace');(OUT/'native.log').write_text(log)
 for a,b in [(m/'cl_dlls/client.dll',ROOT/'build/client/client.dll'),(m/'dlls/hl.dll',ROOT/'build/server/hl.dll'),(m/'models/vf_deaths/persona_death.mdl',ROOT/'generated/deaths/persona_death.mdl'),(m/'models/vf_deaths/persona_death_gibs.mdl',ROOT/'generated/deaths/persona_death_gibs.mdl')]:assert hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest()
 motions={o['id']:o for o in d['motions']};records=[]
 for i,p in enumerate(d['profiles']):
  id=p['effect'];part=log.split('BEGIN_'+id)[1].split('END_'+id)[0];motion=re.search(r'VFDeathVisual .*sequence=(\w+)',part)[1];assert motion in [motions[o]['sequence'] for o in p['motions']],(id,motion)
  spawn=re.findall(r'VFFragment spawn entity=(\d+) body=(\d+) effect=(\d+) whole=(\d+)',part);assert len(spawn)==4 and all(int(x[2])==i for x in spawn) and sum(int(x[3]) for x in spawn)==1,id
  whole=int(next(x[0] for x in spawn if x[3]=='1'));trail=re.findall(fr'VFFragment client entity={whole} body=\d+ effect={i} whole=1 age=[\d.]+ blood=(\d+) elemental=(\d+) travel=([\d.]+)',part)
  assert trail and max(int(x[0]) for x in trail)>0 and max(int(x[1]) for x in trail)>0 and max(float(x[2]) for x in trail)>10,(id,trail)
  assert 'rejected=0' in part and 'frame=255.0' in part,(id,part[-2500:]);assert (m/'scrshots'/f'{id}_end.png').stat().st_size>1000
  records.append(dict(effect=id,animation=motion,region=REGIONS[i%5],blood=max(int(x[0]) for x in trail),elemental=max(int(x[1]) for x in trail),whole_limb_distance=max(float(x[2]) for x in trail)))
 gui=log.split('ATLAS_GUI ')[1].split('ATLAS_GUI_END ')[0];assert 'VFUI click: Atlas' in gui and 'VFUI click: TOXIC / Agonie lente' in gui and 'mask=1 effect=4 sequence=vf_m_agony' in gui,gui
 gui=log.split('CATALOG_GUI ')[1].split('CATALOG_GUI_END ')[0];assert 'VFUI click: Suivant' in gui and 'VFUI click: Mixamo : agonie lente' in gui and 'mask=1 effect=4 sequence=vf_m_agony' in gui,gui
 cleared=log.split('CLEARED_ATLAS ')[1];assert 'VFCorpse client' not in cleared and 'VFFragment client' not in cleared and 'pool active=0' in cleared
 assert all(int(n)<=384 for n in re.findall(r'pool active=(\d+)',log))
 for error in ['Host_Error','SV_Error','not precached','Could not load','VFState rejected']:assert error not in log,error
 labels=['electro','cryo','thermal','toxic','corrosion','sonic','kinetic','arc_chain'];frames=[]
 for f in range(12):
  sheet=Image.new('RGB',(1200,710),(12,20,26));draw=ImageDraw.Draw(sheet)
  for k,id in enumerate(labels):
   im=Image.open(m/'scrshots'/f'{id}_{f:02}.png').convert('RGB').crop((330,100,1110,650)).resize((300,212));x=(k%4)*300;y=(k//4)*345;sheet.paste(im,(x,y+42));draw.text((x+12,y+12),id.upper(),fill='white');draw.text((x+12,y+273),d['profiles'][next(i for i,p in enumerate(d['profiles']) if p['effect']==id)]['label'],fill='white')
  frames.append(sheet)
 frames[0].save(OUT/'atlas-morts.gif',save_all=True,append_images=frames[1:],duration=220,loop=0);frames[5].save(OUT/'atlas-morts.jpg')
 for f in ['atlas_menu.png','catalog_page2.png']:shutil.copy2(m/'scrshots'/f,OUT/f)
 result=dict(seconds=round(time.monotonic()-started,2) if started else None,profiles=records,checks=['sixteen automatic effect-to-animation selections','five anatomical regions exercised','real whole limb plus three small physics fragments per removal','blood and elemental particles emitted along each moving limb','sprite pool bounded at 384','native F8 atlas effect selection and second catalogue page','clearing deletes corpses, fragments and trails'],log=str(OUT/'native.log'))
 (OUT/'native-verification.json').write_text(json.dumps(result,indent=2));print('PASS native atlas',json.dumps(result),flush=True);return result
def manual():
 """Exercise the alternate atlas candidates that RNG need not choose in a run."""
 d=assets();e=harness.stage('death-atlas-manual');m=e/'vf_animation';(m/'maps').mkdir(exist_ok=True);shutil.copy2(ROOT/'generated/test-room/vf_range.bsp',m/'maps/vf_range.bsp')
 cases=[('collapse','left_arm','corrosion',81),('impact_right','right_leg','hydro',82),('spin','head','resonant_impact',23)]
 cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\ncmd give item_suit\ncmd give weapon_crowbar\ncmd weapon_crowbar\nnoclip\ndefault_fov 50\n'
 for motion,region,effect,index in cases:
  cfg+=f'cmd vf_death_clear\ncmd vf_range_reset 0\necho MANUAL_{motion}\ncmd vf_range_death 0 {region} {effect} {motion}\ncmd vf_death_view scene\nwait 48\nscreenshot scrshots/{motion}_motion.png\nwait 480\nvf_death_client\nvf_engine_stats\nscreenshot scrshots/{motion}_end.png\necho MANUAL_END_{motion}\nwait 6\n'
 cfg+='wait 8\nquit\n';(m/'atlas_manual.cfg').write_text(cfg);p=subprocess.Popen([str(e/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','atlas-manual.log','+sv_cheats','1','+map','vf_range','+exec','atlas_manual.cfg'],cwd=e)
 try:p.wait(timeout=45);assert p.returncode==0
 finally:
  if p.poll() is None:p.terminate();p.wait(10)
 log=(e/'atlas-manual.log').read_text(errors='replace');(OUT/'manual.log').write_text(log)
 for motion,region,effect,index in cases:
  part=log.split('MANUAL_'+motion+' ')[1].split('MANUAL_END_'+motion+' ')[0];sequence=next(m['sequence'] for m in d['motions'] if m['id']==motion)
  assert 'sequence='+sequence in part and f'sequence={index} frame=255.0' in part and 'rejected=0' in part,(motion,part[-2000:])
  assert (m/'scrshots'/f'{motion}_end.png').stat().st_size>1000
  for suffix in ['motion','end']:shutil.copy2(m/'scrshots'/f'{motion}_{suffix}.png',OUT/f'{motion}_{suffix}.png')
 result=dict(cases=[dict(motion=a,region=b,effect=c,sequence=d) for a,b,c,d in cases],checks=['alternate hydro and corrosion candidates render through completion','historical spinning death combines with resonant particles','all assemblies accepted']);(OUT/'manual-verification.json').write_text(json.dumps(result,indent=2));print('PASS manual atlas variants',json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--assets',action='store_true');p.add_argument('--verify',action='store_true');p.add_argument('--manual',action='store_true');a=p.parse_args();manual() if a.manual else verify(ROOT/'build/animation-native/death-atlas',assets()) if a.verify else assets() if a.assets else run()
