"""Small native preview of world-space first-person body and upright crouch."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from traversal_review_bundle import prepare_review,review_assets
from native_workspace import private_copy

def run():
 engine,mod=prepare_review('body-probe')
 private_copy(ROOT/'build/engine-candidate/ref_gl.dll',engine/'ref_gl.dll')
 out=ROOT/'docs/validation/traversal/body-probe';out.mkdir(parents=True,exist_ok=True)
 lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','host_framerate .03333333','fps_max 30','hud_draw 0','sv_cheats 1','god','cmd give weapon_9mmAR','weapon_9mmAR','wait 40','vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 12']
 if '--bundle-check' in sys.argv:
  lines+=['vf_operator','wait 25','vf_item helmet_riot','vf_commit','wait 25','vf_operator','wait 10','cmd vf_headgear_toggle','wait 85','vf_headgear_info','vf_headgear_audit','wait 5']
 initial_count=len(lines)
 def shot(name,*commands):
  lines.extend(commands);lines.extend(['wait 5','echo BODY_'+name,'cmd vf_traversal_info','snapshot scrshots/'+name+'.png','wait 2'])
 shot('standing','cmd vf_traversal_place 128 -750 36 0','wait 2','vf_traversal_look 0 80')
 shot('standing_body','vf_traversal_look 0 0','cam_snapto 1','cam_idealdist 80','cam_idealyaw 120','cam_idealpitch 8','cam_command 1')
 shot('standing_clear','cam_command 2','vf_traversal_look 0 80','r_drawviewmodel 0')
 lines.append('r_drawviewmodel 1')
 shot('crouched','vf_traversal_look 0 0','+duck','wait 20','cam_snapto 1','cam_idealdist 70','cam_idealyaw 120','cam_idealpitch 8','cam_command 1')
 shot('crouch_down','cam_command 2','vf_traversal_look 0 80')
 shot('sliding','-duck','wait 50','cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','vf_traversal_look 0 50','+duck','wait 9')
 shot('hanging','-duck','wait 70','cmd vf_traversal_place 238 0 54 0','vf_traversal_look 0 0','wait 1','+jump','wait 20','-jump','vf_traversal_look 0 80')
 vault_start=len(lines)
 shot('vault','-jump','-duck','wait 40','cmd vf_traversal_place -28 0 36 0','wait 2','vf_traversal_look 0 0','+forward','+jump','wait 1','-forward','-jump','wait 1')
 shot('stepup','wait 40','cmd vf_traversal_place 996 -450 36 0','wait 2','vf_traversal_look 0 0','+forward','+jump','wait 1','-forward','-jump','wait 1')
 if '--vault-only' in sys.argv:lines=lines[:initial_count]+lines[vault_start:]
 lines.append('quit');(mod/'body.cfg').write_text('\n'.join(lines)+'\n')
 process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','960','-height','540','-console','-nointro','-nowriteconfig','-log','body.log','+sv_cheats','1','+developer','2','+map','vf_traversal','+exec','body.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
 try:process.wait(timeout=70);assert process.returncode==0
 finally:
  if process.poll()is None:process.terminate();process.wait(timeout=8)
 for p in(mod/'scrshots').glob('*.png'):shutil.copy2(p,out/p.name)
 shutil.copy2(engine/'body.log',out/'native.log')
 text=(out/'native.log').read_text(errors='replace');assert 'VFFirstPersonBody' in text
 assert 'VFEngine: native extension v4 connected' in text or 'VFEngine: native extension v3 connected' in text,'Legacy avatar capture rejected'
 if '--bundle-check' in sys.argv:
  assert 'VF catalogue:'not in text
  assert re.search(r'VFHeadgear render: player=1 type=1 ',text),'Equipped helmet rig must be present'
  assert len(re.findall(r'VFHeadgear pose: view=1 ',text))>20,'Helmet action must render with the R1'
  for wide in ('0','1'):
   contacts=[float(e)for w,e in re.findall(r'VFVaultPalm view=1 wide='+wide+r' t=[\d.]+ weight=([\d.]+) error=([\d.]+)',text)if float(w)>.999]
   assert contacts and max(contacts)<.001,('Equipped helmet must preserve traversal contact',wide)
  sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
  report=dict(bundle_checked=True,client_sha256=sha(mod/'cl_dlls/client.dll'),server_sha256=sha(mod/'dlls/hl.dll'),renderer_sha256=sha(engine/'ref_gl.dll'),assets=review_assets(mod))
  (out/'bundle.json').write_text(json.dumps(report,indent=2))
 print('PASS body preview',out)
if __name__=='__main__':run()
