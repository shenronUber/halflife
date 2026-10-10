"""Bounded native verification of physical impact metadata and legacy damage."""
import hashlib,json,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import third_person_native_test as harness
OUT=ROOT/'build/combat'

def run(server=None,client=None):
 engine=harness.stage('combat',server=server or ROOT/'build/server/hl.dll',client=client or harness.BASE/'vf_visual/cl_dlls/client.dll');mod=engine/'vf_animation'
 for name in ('xash.dll','ref_gl.dll'):shutil.copy2(harness.BASE/name,engine/name)
 shutil.copy2(client or harness.BASE/'vf_visual/cl_dlls/client.dll',mod/'cl_dlls/client.dll')
 # Keep the established first-person carriers, including their optional foregrip.
 for path in (ROOT/'generated/r01').glob('r01_rig*.mdl'):shutil.copy2(path,mod/'models/vf_r01'/path.name)
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\nvf_reference\nwait 25\nvf_item gign_torso_gign\nvf_item gign_legs_gign\nvf_item r01_ammo_a__medieval-forge\nvf_item r01_projectile_a__medieval-forge\nvf_commit\nwait 25\nvf_ui_pointer 1220 40 1\nwait 3\nvf_ui_pointer 1220 40 0\nwait 15\ncmd vf_peer_pose\nwait 15\n'
 s+='cmd vf_materials_info\ncmd vf_body_info\necho COMBAT_IDLE\ncmd vf_hitbox_info\nvf_impact_debug 1\ncmd vf_combat_selftest\nwait 10\nvf_impact_debug 1\n+attack\nwait 12\n-attack\nwait 10\necho COMBAT_SHOT\ncmd vf_impact_info\n'
 s+='+reload\nwait 2\n-reload\nwait 20\necho COMBAT_RELOAD_A\ncmd vf_reload_info\ncmd vf_hitbox_info\ncmd vf_hitbox_probe\nwait 45\necho COMBAT_RELOAD_B\ncmd vf_reload_info\ncmd vf_hitbox_info\ncmd vf_hitbox_probe\nwait 55\necho COMBAT_FINISHED\ncmd vf_reload_info\ncmd vf_hitbox_info\nvf_engine_stats\nwait 15\nquit\n'
 (mod/'combat_test.cfg').write_text(s,encoding='ascii')
 command=[str(engine/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','combat-test.log','+exec','lab_controls.cfg','+developer','1','+sv_cheats','1','+map','vf_range','+exec','combat_test.cfg']
 start=time.time();child=subprocess.Popen(command,cwd=engine)
 try:
  child.wait(timeout=35);assert child.returncode==0,child.returncode
 finally:
  if child.poll() is None:child.terminate();child.wait(10)
 return verify(engine,start)

def verify(engine,start=None):
 log=(engine/'combat-test.log').read_text(encoding='utf-8',errors='replace')
 assert 'VFCombatTest summary groups=7/7 armor_unchanged=1 no_projectile_leak=1' in log,log[-6000:]
 materials=re.search(r'VFMaterials count=(\d+) profiles=(\d+).*head=([\d.]+) chest=([\d.]+) abdomen=([\d.]+) arm=([\d.]+) leg=([\d.]+)',log);assert materials
 assert 'VFState rejected' not in log and 'rejected=0' in log
 assert 'VFBody player=1 mins=-16,-16,-36 maxs=16,16,36' in log
 assert 'ammo=r01_ammo_a__medieval-forge projectile=r01_projectile_a__medieval-forge' in log
 assert 'id=textile' in log and 'id=flesh' in log and 'profile=concrete' in log
 assert 'VFMaterialItem slot=torso item=gign_torso_gign profile=uniform' in log and 'VFMaterialItem slot=gloves item=gign_gloves_gign profile=glove' in log
 samples={}
 for label in ['COMBAT_IDLE','COMBAT_RELOAD_A','COMBAT_RELOAD_B','COMBAT_FINISHED']:
  part=re.split(label+r'\s*\n',log)[-1]
  header=re.search(r'VFHitboxes player=1 model=(\S+) boxes=(\d+) sequence=(\d+) frame=([\d.]+) clienttrace=([\d.]+)',part);assert header,(label,part[:300])
  rows=re.findall(r'VFHitbox index=(\d+) group=(\d+) bone=(.*?) center=([-\d.,]+)',part[:part.index('VFHitbox index=19')+200]);assert len(rows)==20,(label,rows)
  assert set(int(r[1])for r in rows)==set(range(1,8)),rows
  probe=re.search(r'VFHitboxProbe index=15 group=4 found=(\d) point=([-\d.,]+)',part)
  if label in ['COMBAT_RELOAD_A','COMBAT_RELOAD_B']:assert probe and probe[1]=='1',(label,probe)
  samples[label]=dict(probe=list(map(float,probe[2].split(',')))if probe else None,model=header[1],boxes=int(header[2]),sequence=int(header[3]),frame=float(header[4]),clienttrace=float(header[5]),centers={r[2]:list(map(float,r[3].split(',')))for r in rows})
 assert samples['COMBAT_RELOAD_A']['sequence']==77 and samples['COMBAT_RELOAD_B']['sequence']==77,samples
 assert samples['COMBAT_RELOAD_B']['frame']>samples['COMBAT_RELOAD_A']['frame'],samples
 hand='Bip01 L Hand'
 a=samples['COMBAT_RELOAD_A']['centers'][hand];b=samples['COMBAT_RELOAD_B']['centers'][hand]
 motion=sum((x-y)**2 for x,y in zip(a,b))**.5;assert motion>1,(a,b)
 probe_motion=sum((x-y)**2 for x,y in zip(samples['COMBAT_RELOAD_A']['probe'],samples['COMBAT_RELOAD_B']['probe']))**.5;assert probe_motion>1
 assert all(abs(x-y)<.05 for x,y in zip(samples['COMBAT_RELOAD_A']['centers']['Bip01 Pelvis'],samples['COMBAT_RELOAD_B']['centers']['Bip01 Pelvis'])), 'trace displacement must not be caused by player movement'
 assert 'active=0 clip=50 model=models/vf_r01/r01_tp.mdl' in log
 report=dict(elapsed_seconds=round(time.time()-start,2)if start else None,material_count=int(materials[1]),profile_count=int(materials[2]),multipliers=dict(zip(['head','chest','abdomen','arm','leg'],map(float,materials.groups()[2:]))),reload_samples=samples,left_hand_motion_units=motion,actual_trace_motion_units=probe_motion,server_sha256=hashlib.sha256((engine/'vf_animation/dlls/hl.dll').read_bytes()).hexdigest(),catalog_sha256=hashlib.sha256((ROOT/'data/combat-materials.json').read_bytes()).hexdigest(),checks=['actual engine traces find all seven anatomical regions','legacy health damage verified for seven regions','legacy armor ratio and armor consumption preserved','projectile context does not leak into unscoped melee','equipped projectile and ammo identity captured independently of finish/VFX','textile and flesh layers identified','20 anatomical hitboxes, no invisible shield','actual engine trace intersections and server bone centers advance with reload; pelvis stays fixed','movement hull unchanged','reload completes and no renderer rejection'],limits=['GET_BONE_POSITION diagnostics reflect the server pose; precise hull blending may differ','client gait and torso corrections are not fully reproduced in server collision','clothing coverage is a coarse hitgroup proxy; no triangle-level layering or penetration','density is provisional; resistance, thickness, mass and speed are uncalibrated'],mode='identify_only')
 (OUT/'native-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PASS native combat:',json.dumps({k:v for k,v in report.items()if k!='reload_samples'}));return report
if __name__=='__main__':
 if '--verify' in sys.argv:verify(harness.OUT/'combat')
 else:run()
