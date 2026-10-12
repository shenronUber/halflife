"""Record real thin-wall vault, platform step, crouch, slide and own-body views."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from traversal_review_bundle import prepare_review,review_assets
from native_workspace import private_copy,remove_tree,SESSIONS
OUT=ROOT/'docs/validation/traversal/posture-review'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run():
 engine,mod=prepare_review('posture-review')
 sources=[ROOT/'engine/gl_vf.inc',ROOT/'engine/gl_vf_headgear.inc',ROOT.parent/'game_shared/vf_engine_api.h',ROOT.parent/'game_shared/vf_headgear.h',ROOT.parent/'game_shared/vf_traversal.h']
 source_hashes={str(p.relative_to(ROOT.parent)):digest(p)for p in sources}
 OUT.mkdir(parents=True,exist_ok=True);frames=mod/'scrshots/review';frames.mkdir()
 lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','sys_timescale 1','host_framerate .03333333','fps_max 30','hud_draw 0','vf_voice_subtitles 0','sv_cheats 1','god','cmd give weapon_9mmAR','cmd give ammo_9mmbox','weapon_9mmAR','wait 40','vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 12']
 timeline=[];count=0
 def clip(gesture,view,commands,events=None,n=75,angle=110):
  nonlocal count
  lines.extend(['-duck','-jump','-forward','-attack','-reload','cam_command 2','wait 50'])
  lines.extend(commands)
  if view=='third-person':lines.extend(['cam_snapto 1','cam_idealdist 85',f'cam_idealyaw {angle}','cam_idealpitch 8','cam_command 1'])
  timeline.append(dict(frame=count,view=view,gesture=gesture,angle=angle))
  for i in range(n):
   lines.extend((events or {}).get(i,[]));lines.extend([f'echo POSTURE_FRAME_{count:04}','cmd vf_traversal_info',f'snapshot scrshots/review/frame_{count:04}.png','wait 1']);count+=1
 clip('body','first-person',['cmd vf_traversal_place 128 -750 36 0','wait 2','vf_traversal_look 0 60'],{24:['vf_traversal_look 0 80']})
 clip('crouch','third-person',['cmd vf_traversal_place 128 -750 36 0','wait 2','vf_traversal_look 0 0','+duck','wait 20'],{4:['+attack'],24:['-attack'],35:['+reload'],37:['-reload']})
 for angle in(110,230):
  clip('slide','third-person',['cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','vf_traversal_look 0 0'],{0:['+duck'],8:['+attack'],22:['-attack'],42:['-duck']},angle=angle)
 clip('slide','first-person',['cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','vf_traversal_look 0 35'],{0:['+duck'],15:['vf_traversal_look 0 65'],42:['-duck']})
 for view in('third-person','first-person'):
  for gesture,point in [('vault','-28 0 36'),('stepup','996 -450 36')]:
   clip(gesture,view,[f'cmd vf_traversal_place {point} 0','wait 2','vf_traversal_look 0 0'],{0:['+forward','+jump'],1:['-forward','-jump']},n=65,angle=110)
 clip('hang','first-person',['cmd vf_traversal_place 238 0 54 0','wait 1','vf_traversal_look 0 0','+jump','wait 20','-jump','wait 10'],{10:['vf_traversal_look 0 60'],35:['vf_traversal_look 0 80']})
 clip('climb','first-person',['cmd vf_traversal_place 238 0 54 0','wait 1','vf_traversal_look 0 0','+jump','wait 20','-jump','wait 10','vf_traversal_look 0 45'],{0:['+jump'],1:['-jump']})
 lines.append('quit')
 for part,start in enumerate(range(0,len(lines),140)):
  chunk=lines[start:start+140]
  if start+140<len(lines):chunk.append(f'exec posture_{part+1:03}.cfg')
  (mod/f'posture_{part:03}.cfg').write_text('\n'.join(chunk)+'\n')
 process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','960','-height','540','-console','-nointro','-nowriteconfig','-log','posture.log','+sv_cheats','1','+developer','2','+map','vf_traversal','+exec','posture_000.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
 try:process.wait(timeout=240);assert process.returncode==0
 finally:
  if process.poll()is None:process.terminate();process.wait(timeout=8)
 text=(engine/'posture.log').read_text(errors='replace');shutil.copy2(engine/'posture.log',OUT/'native.log')
 assert re.search(r'VFEngine: native extension v[34] connected',text),'R1 renderer disconnected; legacy avatar capture rejected'
 assert 'VF catalogue:'not in text,'Equipment catalog rejected; legacy capture rejected'
 assert source_hashes=={str(p.relative_to(ROOT.parent)):digest(p)for p in sources},'Renderer inputs changed during capture; review the new candidate'
 blocks={int(f):b for f,b in re.findall(r'POSTURE_FRAME_(\d+)(.*?)(?=POSTURE_FRAME_|\Z)',text,re.S)}
 assert len(blocks)==count
 for i,event in enumerate(timeline):
  end=timeline[i+1]['frame']if i+1<len(timeline)else count;rows=[blocks[f]for f in range(event['frame'],end)]
  phases=[int(re.search(r'VFTraversal phase=(\d+)',r)[1])for r in rows];event['phases']=sorted(set(phases))
  if event['gesture']in('vault','stepup'):
   assert phases.count(1)>15 and phases[-1]==0,(event,phases)
   states=[int(s)for r in rows for s in re.findall(r'VFTraversal phase=1 state=(\d+)',r)]
   assert all(bool(s&65536)==(event['gesture']=='stepup')for s in states),event
   palms=[float(e)for r in rows for v,w,weight,e in re.findall(r'VFVaultPalm view=(\d) wide=(\d) t=[\d.]+ weight=([\d.]+) error=([\d.]+)',r)if int(v)==(event['view']=='first-person')and float(weight)>.999]
   assert len(palms)>=2 and max(palms)<.001,(event,'plant',palms)
   event['planted_palm_error']=max(palms)
  if event['gesture']=='slide':assert phases.count(5)>25,event
  if event['gesture']=='crouch':
   clips=[int(re.search(r'clip=(\d+)',r)[1])for r in rows]
   assert clips[0]-min(clips)>=4 and any('reload=1' in r for r in rows),event
   directions=[tuple(map(float,b.split(',')))for r in rows for b in re.findall(r'VFCrouchCombat view=0 sequence=ref_(?:aim|shoot)_mp5 frame=[\d.]+ barrel=([\d.,-]+)',r)]
   assert len(directions)>12 and min(b[0] for b in directions)>.9999,event
   event['shots']=clips[0]-min(clips);event['reload_started']=True;event['minimum_aim_alignment']=min(b[0] for b in directions)
  if event['view']=='first-person':
   assert any('VFFirstPersonBody parts=3 mask=26' in r for r in rows),event
  for offset in(5,12,20,30,45):
   src=frames/f"frame_{event['frame']+offset:04}.png";shutil.copy2(src,OUT/f"{i:02}-{event['gesture']}-{event['view']}-{offset}.png")
 report=dict(fps=30,width=960,height=540,frames=count,frames_directory=str(frames),timeline=timeline,posture=True,
  renderer_sha256=digest(engine/'ref_gl.dll'),client_sha256=digest(mod/'cl_dlls/client.dll'),server_sha256=digest(mod/'dlls/hl.dll'),
  delta_sha256=digest(mod/'delta.lst'),renderer_source_sha256=digest(ROOT/'engine/gl_vf.inc'),body_patch_sha256=digest(ROOT/'engine/first-person-body.patch'),
  engine_core={name:digest(engine/name)for name in('xash3d.exe','xash.dll','xash.exe','SDL2.dll')},
  assets=review_assets(mod),source_hashes=source_hashes)
 manifest=OUT/'capture.json';manifest.write_text(json.dumps(report,indent=2));print('PASS posture native',count,'frames',flush=True)
 if '--encode' in sys.argv:
  blender=ROOT.parent/'devtools/blender/blender-4.5.14-windows-x64/blender.exe'
  subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1','--python',str(ROOT/'animation-workshop/encode-traversal-transitions.py'),'--','--manifest',str(manifest)],check=True,stdout=(OUT/'encoding.log').open('w'),stderr=subprocess.STDOUT)
  report=json.loads(manifest.read_text());report.pop('frames_directory');report['temporary_pngs_removed']=count;manifest.write_text(json.dumps(report,indent=2));remove_tree(frames,SESSIONS)
if __name__=='__main__':run()
