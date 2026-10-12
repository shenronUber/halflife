"""Real movement, look-independent legs and H gestures after traversal."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from headgear_preview import stage,asset_library
from native_workspace import shared_copy,port

def run(candidate=None):
 engine,mod=stage('first-person-motion',candidate)
 shared_copy(ROOT/'generated/traversal-range/vf_traversal.bsp',mod/'maps/vf_traversal.bsp')
 lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','fps_max 60','host_framerate .016666667','sv_cheats 1','god','weapon_9mmAR','wait 30',
        'firstperson','vf_headgear_hud 0','hud_draw 0','vf_operator','wait 25','vf_item helmet_riot','vf_commit','wait 25','vf_operator','wait 10']
 shots=[]
 def shot(name):
  shots.append(name);lines.extend([f'screenshot scrshots/{name}.png','wait 1'])
 def begin(name):lines.append('echo MOTION_'+name+'_BEGIN')
 def end(name):lines.append('echo MOTION_'+name+'_END')
 # The actual slide must end before H. The previous viewmodel metadata was stale.
 lines.extend(['cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','+duck','wait 12','-duck','wait 140','vf_traversal_look 0 0'])
 begin('HAND_AFTER_SLIDE')
 for direction in ('up','down'):
  lines.extend(['vf_headgear_toggle','wait 7']);shot('hand_'+direction+'_present')
  lines.extend(['wait 6']);shot('hand_'+direction+'_rise')
  lines.extend(['wait 65'])
 end('HAND_AFTER_SLIDE')
 # Real directional input, with feet observed while gait faces diagonal motion.
 for name,yaw,commands in [('forward',0,['+forward']),('diagonal',0,['+forward','+moveright']),('sideways',0,['+moveleft']),('turned',90,['+forward','+moveright'])]:
  lines.extend(['-forward','-back','-moveleft','-moveright','-duck','wait 15',f'cmd vf_traversal_place 128 -750 36 {yaw}',f'vf_traversal_look {yaw} 75','wait 3'])
  begin('WALK_'+name);lines.extend(commands+['wait 18',f'vf_traversal_look {yaw} 75','wait 1']);shot('walk_'+name);end('WALK_'+name)
 # Match slide time/position across all look angles; compare the world pose.
 for name,yaw,pitch in [('flat',0,0),('down',0,55),('steep',0,80),('left',90,55),('back',180,55)]:
  lines.extend(['-forward','-back','-moveleft','-moveright','-duck','wait 90','cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','+duck','wait 12',f'vf_traversal_look {yaw} {pitch}','wait 1'])
  begin('SLIDE_'+name);lines.append('cmd vf_traversal_info');shot('slide_'+name);end('SLIDE_'+name)
 lines.extend(['-duck','wait 100','quit'])
 for part,start in enumerate(range(0,len(lines),100)):
  chunk=lines[start:start+100]
  if start+100<len(lines):chunk.append(f'exec motion_{part+1:03}.cfg')
  (mod/f'motion_{part:03}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
 child=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2','-rodir',str(asset_library()),'-game',mod.name,'-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','motion.log','-port',str(port()),'-clientport',str(port()),'+exec','lab_controls.cfg','+sv_cheats','1','+developer','2','+map','vf_traversal','+exec','motion_000.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
 try:child.wait(timeout=150);assert child.returncode==0
 finally:
  if child.poll() is None:child.terminate();child.wait(timeout=8)
 text=(engine/'motion.log').read_text(errors='replace')
 assert 'native extension v4 connected' in text
 assert not any(s in text for s in ('Host_Error','SV_Error','VFState rejected','Could not load'))
 def block(name):return text.split('MOTION_'+name+'_BEGIN')[1].split('MOTION_'+name+'_END')[0]
 hand=block('HAND_AFTER_SLIDE');assert len(re.findall(r'VFHeadgear action:',hand))==2
 assert len(re.findall(r'VFHeadgear pose: view=1 ',hand))>40,'H must render after a completed slide'
 errors=re.findall(r'right_error=([\d.]+) weapon_error=([\d.]+)',hand)
 assert errors and all(float(a)==float(b)==0 for a,b in errors)
 yaw_errors=[];gait_deltas=[]
 for name in ('forward','diagonal','sideways','turned'):
  records=re.findall(r'VFBodyOrientation look=([\d.-]+) gait=([\d.-]+) rendered=([\d.-]+) error=([\d.]+)',block('WALK_'+name))
  assert len(records)>8,name
  yaw_errors.extend(float(r[3]) for r in records)
  if name!='forward':gait_deltas.extend(abs((float(r[0])-float(r[1])+180)%360-180) for r in records)
 assert max(yaw_errors)<.001 and max(gait_deltas)>30,'Subjective legs must face look yaw during genuine sideways/diagonal motion'
 relative=[]
 pattern=r'VFBodyFeet phase=5 hip=([\d.,-]+) left=([\d.,-]+) right=([\d.,-]+) own=1 origin=([\d.,-]+) look=([\d.,-]+)'
 for name in ('flat','down','steep','left','back'):
  rows=re.findall(pattern,block('SLIDE_'+name));assert rows,('No world-space slide feet',name)
  hip,left,right,origin,look=rows[0];origin=np.array(list(map(float,origin.split(','))))
  relative.append(np.concatenate([np.array(list(map(float,p.split(','))))-origin for p in (hip,left,right)]))
 drift=float(np.max(np.ptp(np.array(relative),axis=0)))
 assert drift<.05,('Changing look must not change the seated world pose',drift,relative)
 out=ROOT/'docs/validation/first-person-motion';out.mkdir(parents=True,exist_ok=True)
 shutil.copy2(engine/'motion.log',out/'native.log')
 for name in shots:shutil.copy2(mod/'scrshots'/(name+'.png'),out/(name+'.png'))
 font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22);board=Image.new('RGB',(1920,1182),'#141e27');draw=ImageDraw.Draw(board)
 chosen=[('hand_up_present','H : main gauche'),('hand_up_rise','H : main sur la tranche'),('hand_down_rise','H : abaissement'),('walk_forward','Marche avant'),('walk_diagonal','Marche diagonale'),('walk_sideways','Pas latéral'),('slide_flat','Glissade : regard devant'),('slide_down','Glissade : regard baissé'),('slide_left','Glissade : regard à gauche')]
 for i,(name,label) in enumerate(chosen):
  x=(i%3)*640;y=(i//3)*394;draw.text((x+10,y+6),label,font=font,fill='#e3efed');board.paste(Image.open(out/(name+'.png')).resize((640,360)),(x,y+34))
 image=ROOT/'docs/images/first-person-motion-fixes.jpg';board.save(image,quality=94)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 report=dict(passed=True,headgear_after_slide=True,right_hand_and_weapon_preserved=True,maximum_leg_yaw_error=max(yaw_errors),maximum_slide_look_pose_drift=drift,slide_look_cases=5,walk_directions=4,world_slide_body=True,image=str(image),client_sha256=sha(mod/'cl_dlls/client.dll'),server_sha256=sha(mod/'dlls/hl.dll'),renderer_sha256=sha(engine/'ref_gl.dll'))
 (out/'native.json').write_text(json.dumps(report,indent=2));print('PASS first-person motion:',report,flush=True)
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--candidate-dir',type=Path);run(p.parse_args().candidate_dir)
