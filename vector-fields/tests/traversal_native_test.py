"""Exercise actual server/client movement, gun policy and screenshot poses."""
import json,shutil,subprocess,time,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from third_person_native_test import stage
from build_traversal_range import build
OUT=ROOT/'docs/validation/traversal'
def run(renderer=None):
 engine=stage('traversal',renderer=renderer);mod=engine/'vf_animation'
 shutil.copy2(ROOT.parent/'network/delta.lst',mod/'delta.lst')
 shutil.copy2(build(ensure=True),mod/'maps/vf_traversal.bsp')
 shutil.copytree(ROOT/'generated/traversal',mod/'models/vf_traversal',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.smd','*.qc','*.log','manifest.json'))
 # Script waits count rendered frames. Pin simulation time so a fast/offscreen
 # renderer cannot consume 70 waits before a .62-second vault has completed.
 lines=['wait 180','developer 2','con_notifytime 0','gl_vsync 0','sys_timescale 1','host_framerate 0.0166667','fps_max 60','sv_cheats 1','cmd give weapon_9mmAR','cmd give ammo_9mmbox','weapon_9mmAR','wait 40','vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 10']
 def cmd(*items):lines.extend(items)
 def info(name):cmd('echo TR_'+name,'cmd vf_traversal_info','vf_traversal_render_info','wait 2')
 def image(name):cmd('screenshot scrshots/'+name+'.png','wait 4')
 cmd('cmd vf_traversal_place -28 0 36 0','wait 4','+forward','+jump','wait 8');info('VAULT');image('vault')
 cmd('-jump','-forward','wait 70');info('VAULT_FINISHED')
 cmd('cmd vf_traversal_place 238 0 54 0','wait 1','+jump','wait 12');info('CATCH');image('hang_catch')
 cmd('-jump','wait 95');info('HOLD');image('hang_both')
 cmd('vf_traversal_look 180','vf_shotfx_clear','+attack2','wait 2','-attack2','+attack','wait 4','-attack');info('EARLY_SHOT')
 cmd('echo TR_PREDICTED_DRAW','vf_shotfx_stats');image('arm_begin');cmd('wait 3');image('arm_middle');cmd('wait 30','vf_traversal_look 0');info('ARMED');image('hang_armed')
 cmd('r_drawviewmodel 0','wait 2');image('hang_armed_clear');cmd('r_drawviewmodel 1','wait 2')
 for yaw in (0,45,90,135,180,225,270,315):
  cmd(f'vf_traversal_look {yaw}','wait 8','+attack','wait 5','-attack','wait 8');info('AIM_'+str(yaw));image('aim_'+str(yaw))
 for yaw in (74.9,75.1,285.1,284.9):
  cmd(f'vf_traversal_look {yaw} 0','wait 18','+attack','wait 5','-attack','wait 12');info('FIRE_EDGE_'+str(int(yaw*10)))
 info('BEFORE_RELOAD');cmd('+reload','wait 100','-reload');info('NO_RELOAD')
 for pitch in (-60,60):
  cmd(f'vf_traversal_look 0 {pitch}','wait 10');info('PITCH_'+str(pitch).replace('-','M'));image('pitch_'+str(pitch).replace('-','M'))
 cmd('vf_traversal_look 0 0')
 cmd('vf_traversal_look 0','+jump','wait 16');info('CLIMB');image('climb')
 cmd('-jump','wait 80');info('CLIMB_FINISHED')
 cmd('cmd vf_traversal_place 238 0 54 0','wait 1','+jump','wait 20','-jump','wait 10','+duck','wait 5');info('RELEASE');image('drop');cmd('-duck','wait 15');info('DROP')
 cmd('cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','+duck','wait 10');info('SLIDE_START');image('slide_start')
 cmd('wait 25');info('SLIDE_LOOP');image('slide_long')
 cmd('wait 60');info('SLIDE_FINISHED')
 cmd('-duck','wait 60');info('SLIDE_STOP')
 cmd('cmd vf_traversal_place 238 320 54 0','wait 1','+jump','wait 20','-jump','wait 20','+jump','wait 25','-jump');info('BLOCKED_LEDGE')
 cmd('cmd vf_traversal_place -700 0 512 0','wait 100');info('FALL');cmd('wait 180')
 cmd('cmd vf_traversal_place 238 0 54 0','wait 1','+jump','wait 20','-jump','wait 15','cam_snapto 1','cam_idealdist 120','cam_idealyaw 50','cam_idealpitch 8','cam_command 1','wait 20');info('THIRD_HOLD');image('third_hang_both')
 cmd('+attack2','wait 2','-attack2','wait 30','vf_traversal_look 180','wait 20');image('third_over_shoulder')
 for yaw in (0,45,90,135,180,225,270,315):
  cmd(f'vf_traversal_look {yaw} 0','wait 12');info('THIRD_AIM_'+str(yaw));image('third_aim_'+str(yaw))
 for yaw in (22.4,22.6,157.4,157.6,337.4,337.6):
  cmd(f'vf_traversal_look {yaw} 0','wait 8');info('THIRD_BOUNDARY_'+str(int(yaw*10)))
 for yaw in (0,90,180,270):
  for pitch in (-60,60):
   cmd(f'vf_traversal_look {yaw} {pitch}','wait 12');image(f'third_pitch_{yaw}_{pitch}')
 cmd('cam_command 2','wait 10')
 cmd('cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','+duck','wait 20','cam_snapto 1','cam_idealdist 100','cam_idealyaw 110','cam_idealpitch 4','cam_command 1','wait 10');image('third_slide');cmd('cam_command 2','-duck','wait 40')
 # Check the six real R1 feed/foregrip assemblies, including the angle
 # boundaries that the eight four-corner Studio blends interpolate across.
 for variant in range(6):
  cmd('vf_reference '+str(variant),'wait 25','vf_commit','wait 35','vf_character','vf_character','wait 5','cmd vf_traversal_place 238 0 54 0','+jump','wait 22','-jump','wait 20')
  info('PROFILE_'+str(variant));image('profile_'+str(variant)+'_both')
  cmd('+attack2','wait 2','-attack2','wait 30')
  for yaw in (22.4,22.6,157.4,157.6,337.4,337.6):
   cmd(f'vf_traversal_look {yaw} 0','wait 6');info('BOUNDARY_'+str(variant)+'_'+str(int(yaw*10)))
  image('profile_'+str(variant)+'_armed');cmd('+duck','wait 4','-duck','wait 20')
 cmd('+duck','wait 4','-duck','cmd vf_traversal_place -160 0 36 0','+reload','wait 10','-reload');info('PENDING_RELOAD')
 cmd('cmd vf_traversal_place 238 0 54 0','+jump','wait 22','-jump','wait 10');info('CANCEL_PENDING')
 cmd('+attack2','wait 2','-attack2','wait 30','vf_traversal_look 180 0','wait 18','+attack','wait 220','-attack','wait 160');info('EMPTY_HANG');image('empty_hang')
 cmd('quit')
 (mod/'traversal_test.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii')
 log=engine/'traversal.log'
 if log.exists():log.unlink()
 process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','traversal.log','+sv_cheats','1','+developer','2','+maxplayers','1','+map','vf_traversal','+exec','traversal_test.cfg'],cwd=engine)
 try:process.wait(timeout=180)
 finally:
  if process.poll()is None:process.terminate();process.wait(timeout=8)
 return validate(engine)


def validate(engine):
 """Recheck an unchanged native capture after editing validation criteria."""
 engine=Path(engine);mod=engine/'vf_animation';log=engine/'traversal.log'
 text=log.read_text(errors='replace');pattern=r'TR_([A-Z_0-9]+)\s+VFTraversal phase=(\d+) state=(\d+) origin=([\d.,-]+) velocity=([\d.,-]+) time=([\d.-]+) health=([\d.-]+) clip=(-?\d+) reload=(\d+) sequence=(\d+) yaw=([\d.-]+) anchor=([\d.-]+)'
 cases={}
 for row in re.findall(pattern,text):
  name,phase,state,origin,velocity,remaining,health,clip,reload,sequence,yaw,anchor=row
  cases[name]=dict(phase=int(phase),state=int(state),origin=list(map(float,origin.split(','))),velocity=list(map(float,velocity.split(','))),remaining=float(remaining),health=float(health),clip=int(clip),reload=int(reload),sequence=int(sequence),yaw=float(yaw),anchor=float(anchor))
 OUT.mkdir(parents=True,exist_ok=True);shutil.copy2(log,OUT/'native.log');(OUT/'native.json').write_text(json.dumps(cases,indent=2))
 print(json.dumps({k:dict(phase=v['phase'],origin=v['origin'],clip=v['clip'],sequence=v['sequence'])for k,v in cases.items()}),flush=True)
 assert cases['VAULT']['phase']==1,cases
 assert cases['VAULT_FINISHED']['phase']==0 and cases['VAULT_FINISHED']['origin'][0]>48,cases
 assert cases['CATCH']['phase']==2 and cases['HOLD']['phase']==2,cases
 assert cases['ARMED']['phase']==3,cases
 assert cases['EARLY_SHOT']['phase']==3 and cases['EARLY_SHOT']['remaining']>0,cases['EARLY_SHOT']
 assert cases['EARLY_SHOT']['clip']==cases['HOLD']['clip'],'server must reject fire during draw'
 predicted=re.search(r'TR_PREDICTED_DRAW\s+VFShot stats: shots=(\d+)',text)
 assert predicted and int(predicted[1])==0,'client must emit no predicted firing event during draw'
 for yaw in (0,45,90,135,180,225,270,315):
  c=cases['AIM_'+str(yaw)];assert c['phase']==3 and c['sequence']==85+yaw//45,c
 assert cases['AIM_0']['clip']==cases['ARMED']['clip'] and cases['AIM_45']['clip']==cases['ARMED']['clip'],('front guard must not fire',cases)
 assert cases['AIM_315']['clip']==cases['AIM_270']['clip'] and cases['AIM_270']['clip']<=cases['ARMED']['clip']-5,('side and rear firing',cases)
 assert cases['FIRE_EDGE_749']['clip']==cases['AIM_315']['clip'] and cases['FIRE_EDGE_751']['clip']<cases['FIRE_EDGE_749']['clip'],('right cone boundary',cases)
 assert cases['FIRE_EDGE_2851']['clip']==cases['FIRE_EDGE_751']['clip'] and cases['FIRE_EDGE_2849']['clip']<cases['FIRE_EDGE_2851']['clip'],('left cone boundary',cases)
 assert cases['NO_RELOAD']['clip']==cases['BEFORE_RELOAD']['clip'] and not cases['NO_RELOAD']['reload'],cases
 assert cases['CLIMB']['phase']==4 and cases['CLIMB_FINISHED']['phase']==0 and cases['CLIMB_FINISHED']['origin'][2]>=130,cases
 assert cases['RELEASE']['phase']==6 and cases['RELEASE']['velocity'][2]<-80,cases
 assert cases['DROP']['phase']==0 and cases['DROP']['origin'][2]<50,cases
 assert cases['SLIDE_START']['phase']==5 and cases['SLIDE_LOOP']['phase']==5,cases
 assert cases['SLIDE_FINISHED']['phase']==0 and 200<cases['SLIDE_FINISHED']['origin'][0]-128<500,cases
 assert cases['SLIDE_STOP']['phase']==0,cases
 assert cases['BLOCKED_LEDGE']['phase']==2,cases
 assert cases['FALL']['health']<cases['BLOCKED_LEDGE']['health'],cases
 assert cases['PENDING_RELOAD']['reload']==1,cases
 assert cases['CANCEL_PENDING']['phase']==2 and not cases['CANCEL_PENDING']['reload'],cases
 assert cases['CANCEL_PENDING']['clip']==cases['PENDING_RELOAD']['clip'],cases
 assert cases['EMPTY_HANG']['phase']==3 and cases['EMPTY_HANG']['clip']==0 and not cases['EMPTY_HANG']['reload'],cases
 render=[tuple(map(float,row))for row in re.findall(r'VFTraversalRender phase=(\d+) left_error=([\d.-]+) right_error=([\d.-]+) yaw=([\d.-]+)',text)]
 assert len(render)>=10,render
 assert all(left>=0 and left<.01 for phase,left,right,yaw in render if phase in (2,3)),render
 assert any(phase==2 and right>=0 and right<.01 for phase,left,right,yaw in render if phase in (2,3)),render
 (OUT/'render.json').write_text(json.dumps(render,indent=2))
 view_guns=[tuple(map(float,row))for row in re.findall(r'VFTraversalViewGun yaw=([\d.-]+) deploy=([\d.-]+) barrel_up=([\d.-]+) gun_error=([\d.-]+)',text)]
 assert len(view_guns)>100,('missing first-person gun constraints',len(view_guns))
 view_guards=[r for r in view_guns if r[1]<.0001]
 assert view_guards and min(r[2]for r in view_guards)>.999,('first-person guard barrel not upright',view_guards[:3])
 assert all(0<=r[3]<.01 for r in view_guns),('first-person gun grip',view_guns[:3])
 (OUT/'view-gun.json').write_text(json.dumps(dict(samples=len(view_guns),guard_samples=len(view_guards),minimum_guard_barrel_up=min(r[2]for r in view_guards),maximum_grip_error=max(r[3]for r in view_guns)),indent=2))
 # Correct world axes are insufficient if the upright rifle passes behind
 # the FPS near plane. Compare the same camera with/without the viewmodel.
 from PIL import Image
 import numpy as np
 visible=np.asarray(Image.open(mod/'scrshots/hang_armed.png').convert('RGB'),dtype=np.int16)
 clear=np.asarray(Image.open(mod/'scrshots/hang_armed_clear.png').convert('RGB'),dtype=np.int16)
 gun_pixels=int((np.max(np.abs(visible-clear),axis=2)[120:620,640:1260]>20).sum())
 assert gun_pixels>2500,('upright guard must be visible below the top of the FPS frame',gun_pixels)
 (OUT/'guard-visibility.json').write_text(json.dumps(dict(first_person_visible_gun_pixels=gun_pixels),indent=2))
 body=[tuple(map(float,row))for row in re.findall(r'VFTraversalBody phase=(\d+) sequence=(\d+) left_error=([\d.-]+) right_error=([\d.-]+) gun_error=([\d.-]+) body_shift=([\d.-]+) face_error=([\d.-]+)',text)]
 (OUT/'body-render.json').write_text(json.dumps(body,indent=2))
 assert len(body)>100,body
 assert all(0<=left<.01 for phase,seq,left,right,gun,shift,face in body),body
 # Phase 3 includes draw sequence 84 before the eight stable aim sectors.
 armed=[row for row in body if row[0]==3 and 85<=row[1]<=92]
 assert {row[1]for row in armed}==set(range(85,93)),armed
 # The FPS draw hides the body; the server checkpoint still proves sequence 84.
 assert cases['EARLY_SHOT']['sequence']==84,'missing arm transition'
 assert all(0<=r[4]<.01 for r in armed),('firing wrist reach',sum(r[4]<0 for r in armed))
 # Turning the camera instantaneously through 180 degrees still blends
 # the BODY over .2 seconds. Check the settled pose at each screenshot.
 settled={}
 for yaw,block in re.findall(r'TR_THIRD_AIM_(\d+)\s+(.*?)Write scrshots/third_aim_\1.png',text,re.S):
  rows=[tuple(map(float,row))for row in re.findall(r'VFTraversalBody phase=(\d+) sequence=(\d+) left_error=([\d.-]+) right_error=([\d.-]+) gun_error=([\d.-]+) body_shift=([\d.-]+) face_error=([\d.-]+)',block)]
  assert rows and rows[-1][1]==85+int(yaw)//45,(yaw,'missing pose at capture')
  if int(yaw) in (90,270):assert 0<=rows[-1][6]<6,(yaw,'face/barrel within neck reach',rows[-1])
  assert rows[-1][5]<1.,(yaw,'upper body reach compensation',rows[-1])
  settled[yaw]=rows[-1]
 assert len(settled)==8,settled
 (OUT/'body-settled.json').write_text(json.dumps(settled,indent=2))
 arm=[tuple(map(float,row))for row in re.findall(r'VFTraversalArm yaw=([\d.-]+) extension=([\d.-]+) right_elbow_z=([\d.-]+) left_elbow_z=([\d.-]+) crossing=([\d.-]+) deploy=([\d.-]+) wrist_height=([\d.-]+) barrel_up=([\d.-]+) expected_rise=([\d.-]+) expected_extension=([\d.-]+) route=([\d.-]+)',text)]
 assert len(arm)>100,('missing extended firing arm telemetry',len(arm))
 firing=[r for r in arm if r[5]>.9999];guard=[r for r in arm if r[5]<.0001]
 assert firing and guard and all((.62 if r[10]>.999 else .25)<r[1]<.95 and abs(r[1]-r[9])<.001 for r in firing),('firing wrist reach',firing[:3])
 assert all(.935<r[1]<.945 for r in firing if r[10]<.0001),('right firing pose changed',firing[:3])
 assert max(abs(r[6]-r[8])for r in arm)<.01,('firing wrist must match left shoulder clearance',arm[:3])
 assert min(r[7]for r in guard)>.999,('guard barrel not upright',guard[:3])
 (OUT/'extended-arm.json').write_text(json.dumps(dict(samples=len(arm),minimum_firing_extension=min(r[1]for r in firing),maximum_wrist_height_error=max(abs(r[6]-r[8])for r in arm),maximum_left_shoulder_clearance=max(r[8]for r in arm),minimum_guard_barrel_up=min(r[7]for r in guard),guard_samples=len(guard)),indent=2))
 from traversal_torso_clearance import native_clearance
 clearance=native_clearance(text,mod/'models/vf_skins/persona_scout.mdl',mod/'models/vf_r01/r01_tp.mdl')
 (OUT/'torso-clearance.json').write_text(json.dumps(clearance,indent=2))
 # The waist and bent knee must retain their WORLD positions while drawing,
 # aiming through every sector, and pitching the gun up/down.
 block=re.search(r'TR_THIRD_HOLD\s+(.*?)Write scrshots/third_hang_both.png',text,re.S).group(1)
 pattern=r'VFTraversalAnchor phase=(\d+) hip=([\d.,-]+) knee=([\d.,-]+)'
 def anchors(block):return [(int(p),[float(v)for v in (hip+','+knee).split(',')])for p,hip,knee in re.findall(pattern,block)]
 reference=anchors(block)[-1][1]
 block=text.split('Write scrshots/third_hang_both.png',1)[1].split('Write scrshots/third_slide.png',1)[0]
 from traversal_pose_telemetry import anchored_lean
 proof=anchored_lean(block,reference)
 assert proof['samples']>100 and proof['left_lean_samples']>20 and proof['maximum_lift']>2.9,proof
 (OUT/'body-anchor.json').write_text(json.dumps(proof,indent=2))
 for p in(mod/'scrshots').glob('*.png'):shutil.copy2(p,OUT/p.name)
 print('PASS native traversal: visible upright guard, side/rear fire cone, vault, indefinite hang, reload lock, climb, drop, short slide, ceiling and original fall damage.')
 return cases
if __name__=='__main__':run()
