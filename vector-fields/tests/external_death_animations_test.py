"""Pinned-bank retarget geometry and actual native death combinations."""
import argparse,json,re,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info,globals_of
import external_death_animations as bank
import third_person_native_test as harness
OUT=ROOT/'build/external-deaths';OUT.mkdir(parents=True,exist_ok=True)
NAMES=['quaternius','kaykit_a','kaykit_b'];MASKS={'none':0,'head':1,'left_arm':2,'right_arm':4,'left_leg':8,'right_leg':16}

def assets():
 m=Studio(ROOT/'generated/deaths/persona_death.mdl');base=Studio(ROOT/'generated/personas/persona_rig.mdl');assert m.sequences[:77]==base.sequences and m.sequences[77]=='vf_electro' and m.sequences[78:]==[s[0] for s in bank.CLIPS]
 assert m.names==base.names and m.parents==base.parents and len(m.names)==28
 mesh=m.mesh({0:-1,**{i:1 for i in range(1,12)},**{i:0 for i in range(12,17)}});bones=np.array([v['b'] for _,t in mesh for v in t]);vertices=np.array([np.linalg.inv(m.bind[v['b']])@np.r_[v['p'],1] for _,t in mesh for v in t]);records=[]
 for spec in bank.CLIPS:
  f=sequence_frames(m,spec[0]);source,record=bank.retarget(base,spec);assert f.shape==source.shape and np.allclose(f,source,atol=.005),'Compiled motion differs from the pinned source transfer'
  info=sequence_info(m,spec[0]);assert not info['flags']&1 and abs((len(f)-1)/info['fps']-record['seconds'])<1e-5
  lengths=np.linalg.norm(f[:,1:,:3,3],axis=2);assert np.max(np.ptp(lengths,axis=0))<.001,'Retarget stretched a GIGN limb'
  floors=[];torso=None
  for frame in f:
   g=globals_of(frame,m.parents);world=np.einsum('vij,vj->vi',g[bones],vertices);floors.append(float(world[:,2].min()));assert np.isfinite(world).all()
   torso=float(world[np.isin(bones,[1,8,9,10,11,12,13]),2].min())
  assert max(abs(np.array(floors)+35.9))<.02,'Body clips or floats above the flat floor';assert abs(torso+35.9)<.02,'Settled torso floats above the floor'
  assert np.max(abs(f[-1]-f[0]))>10,'No actual collapse movement';record.update(compiled_sequence=info['index'],floor_range=[min(floors),max(floors)],settled_torso_min=torso);records.append(record)
 (OUT/'assets-verification.json').write_text(json.dumps(dict(clips=records,checks=['pinned donor tracks compiled on the original 28 bones','77 historical sequences and electrical index preserved','constant GIGN limb lengths in every imported frame','ground contact and settled torso checked on the actual compiled mesh']),indent=2));print('PASS imported death assets:',len(records),'donor clips,',sum(r['frames'] for r in records),'poses, unchanged bone lengths, grounded final torso',flush=True)
 return records

def run():
 records=assets();e=harness.stage('external-deaths');m=e/'vf_animation';(m/'maps').mkdir(exist_ok=True);shutil.copy2(ROOT/'generated/test-room/vf_range.bsp',m/'maps/vf_range.bsp')
 cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\nr_drawviewmodel 0\ncmd give item_suit\ncmd give weapon_crowbar\ncmd weapon_crowbar\nnoclip\ndefault_fov 50\nwait 10\n'
 # Detailed motion samples of every donor, then each limb independently and an
 # electrical combination. Real damage/respawn and networked assemblies run.
 for clip in NAMES:
  for region in MASKS:
   effect='electro' if region=='right_arm' else 'standard';key=clip+'_'+region
   cfg+=f'cmd vf_death_clear\ncmd vf_range_reset 0\necho BEGIN_{key}\ncmd vf_range_death 0 {region} {effect} {clip}\ncmd vf_death_view\nwait 4\n'
   if region=='none':
    for i in range(18):cfg+=f'screenshot scrshots/{clip}_{i:02d}.png\nwait 10\n'
   else:cfg+=f'wait 26\nscreenshot scrshots/{key}_motion.png\nwait 400\n'
   cfg+=f'vf_death_client\nvf_engine_stats\nscreenshot scrshots/{key}_settled.png\necho END_{key}\nwait 6\n'
 cfg+='cmd vf_death_clear\ncmd vf_range_reset 0\necho INVALID_MOTION\ncmd vf_range_death 0 head electro invalid\nwait 3\ncmd vf_range_info\nwait 5\necho INVALID_END\n'
 cfg+='default_fov 90\nvf_death_lab\nwait 10\nscreenshot scrshots/animations_menu.png\necho GUI_BEGIN\nvf_ui_pointer 300 462 1\nwait 3\nvf_ui_pointer 300 462 0\nwait 3\nvf_ui_pointer 1100 445 1\nwait 3\nvf_ui_pointer 1100 445 0\nwait 25\ncmd vf_death_view\ndefault_fov 50\nwait 4\nvf_death_client\nvf_engine_stats\nscreenshot scrshots/menu_kaykit_electro_head.png\necho GUI_END\n'
 cfg+='save vf_imported_death\nwait 8\nload vf_imported_death\nwait 170\necho RESTORED\nvf_death_client\necho RESTORED_END\n'
 cfg+='cmd vf_death_clear\necho PLAYER_BEGIN\ncmd vf_death_test left_leg electro quaternius\nwait 420\nvf_death_client\necho PLAYER_END\nwait 8\nquit\n'
 (m/'external.cfg').write_text(cfg);started=time.monotonic();p=subprocess.Popen([str(e/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','external.log','+sv_cheats','1','+map','vf_range','+exec','external.cfg'],cwd=e)
 try:p.wait(timeout=95);assert p.returncode==0
 finally:
  if p.poll() is None:p.terminate();p.wait(10)
 return verify(e,records,started)

def verify(e,records,started=None):
 import hashlib
 m=e/'vf_animation'
 for installed,current in [(m/'models/vf_deaths/persona_death.mdl',ROOT/'generated/deaths/persona_death.mdl'),(m/'dlls/hl.dll',ROOT/'build/server/hl.dll'),(m/'cl_dlls/client.dll',ROOT/'build/client/client.dll')]:assert hashlib.sha256(installed.read_bytes()).digest()==hashlib.sha256(current.read_bytes()).digest(),'Saved run uses stale artifacts'
 log=(e/'external.log').read_text(errors='replace');(OUT/'native.log').write_text(log)
 for clip,record in zip(NAMES,records):
  for region,mask in MASKS.items():
   key=clip+'_'+region;part=log.split('BEGIN_'+key)[1].split('END_'+key)[0];effect=1 if region=='right_arm' else -1
   assert re.search(fr'VFDeathVisual corpse=\d+ victim=\d+ mask={mask} effect={effect} sequence={record["id"]}',part),key
   assert f'sequence={record["compiled_sequence"]} frame=255.0' in part and 'rejected=0' in part,key
   source=m/'scrshots'/f'{key}_settled.png';assert source.stat().st_size>1000
 invalid=log.split('INVALID_MOTION')[1].split('GUI_BEGIN')[0];assert 'VFDeathVisual' not in invalid and 'health=300.0 alive=1' in invalid
 gui=log.split('GUI_BEGIN')[1].split('GUI_END')[0];assert 'VFUI click: KayKit : chute rapide' in gui and 'VFUI click: Tete explosee' in gui and 'mask=1 effect=1 sequence=vf_k_death_a' in gui and 'sequence=79' in gui
 restored=log.split('RESTORED',1)[1].split('RESTORED_END')[0];assert 'mask=1 effect=1' in restored and 'sequence=79 frame=255.0' in restored
 player=log.split('PLAYER_BEGIN')[1].split('PLAYER_END')[0];assert re.search(r'victim=1 mask=8 effect=1 sequence=vf_q_death',player) and 'sequence=78 frame=255.0' in player
 for error in ['Host_Error','SV_Error','not precached','Could not load','VFState rejected']:assert error not in log,error
 # Preview the genuine native motion, cropped only to exclude HUD/margins.
 frames=[]
 for i in range(18):
  sheet=Image.new('RGB',(960,365),(12,20,26));draw=ImageDraw.Draw(sheet)
  for column,clip in enumerate(NAMES):
   im=Image.open(m/'scrshots'/f'{clip}_{i:02d}.png').convert('RGB').crop((350,90,1090,650)).resize((320,242));sheet.paste(im,(320*column,50));draw.text((12+320*column,20),records[column]['label'],fill='white')
  draw.text((12,318),'Captures GoldSource / trois mouvements importes sur notre GIGN',fill='white');frames.append(sheet)
 frames[0].save(OUT/'morts-importees.gif',save_all=True,append_images=frames[1:],duration=167,loop=0);frames[7].save(OUT/'morts-importees.jpg')
 for name in ['animations_menu.png','menu_kaykit_electro_head.png']:shutil.copy2(m/'scrshots'/name,OUT/name)
 result=dict(seconds=round(time.monotonic()-started,2) if started else None,verification_mode="live run" if started else "saved native run",target_deaths=18,imported_clips=3,checks=['three native motion previews','each imported clip combined with head, both arms and both legs removed','electrical arcs combined with all three imported clips','actual F8 choice of KayKit A plus electrical head explosion','imported corpse retains animation, effect and wound through save/load','actual player death with imported Quaternius motion and missing leg','invalid clip rejected without causing damage'],captures=str(m/'scrshots'),log=str(OUT/'native.log'))
 (OUT/'native-verification.json').write_text(json.dumps(result,indent=2));print('PASS imported native deaths',json.dumps(result),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--assets',action='store_true');p.add_argument('--verify',action='store_true');args=p.parse_args();verify(ROOT/'build/animation-native/external-deaths',assets()) if args.verify else assets() if args.assets else run()
