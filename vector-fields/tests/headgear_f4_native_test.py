"""Fresh R1/F4 launch, normal clock and active headgear HUD, without traversal."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from headgear_preview import stage,asset_library
from native_workspace import port

def run(candidate=None):
    engine,mod=stage('headgear-f4-real-clock',candidate)
    out=ROOT/'docs/validation/first-person-motion'/('f4-candidate' if candidate else 'f4-installed')
    lines=['wait 260','developer 2','con_notifytime -1','gl_vsync 0','fps_max 100','host_framerate 0',
           'firstperson','vf_headgear_hud 1','vf_item helmet_nvg_red','vf_commit','wait 30','vf_operator',
           'wait 20','vf_engine_stats','echo F4_BEGIN','vf_headgear_toggle','wait 75',
           'screenshot scrshots/f4_raise.png','wait 425','vf_headgear_toggle','wait 75',
           'screenshot scrshots/f4_lower.png','wait 425','echo F4_END','quit']
    (mod/'after_f4.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii')
    # Same commands as the F4 binding; startup selects R1 and opens inventory.
    (mod/'launch.cfg').write_text('wait 120\nmap vf_range\nexec vf_start.cfg\nexec after_f4.cfg\n',encoding='ascii')
    child=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2',
        '-rodir',str(asset_library()),'-game',mod.name,'-windowed','-width','1920','-height','1080',
        '-console','-nointro','-nowriteconfig','-log','f4.log','-port',str(port()),'-clientport',str(port()),
        '+exec','lab_controls.cfg','+sv_cheats','1','+developer','2','+map','vf_range','+exec','launch.cfg'],
        cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:child.wait(timeout=140);assert child.returncode==0
    finally:
        if child.poll() is None:child.terminate();child.wait(timeout=8)
    text=(engine/'f4.log').read_text(errors='replace')
    assert 'native extension v4 connected' in text
    assert not any(s in text for s in ('Host_Error','SV_Error','VFState rejected'))
    block=text.split('F4_BEGIN')[1].split('F4_END')[0]
    actions=len(re.findall(r'VFHeadgear action:',block));poses=len(re.findall(r'VFHeadgear pose: view=1 ',block))
    assert actions==2 and poses>40,(actions,poses)
    right=re.findall(r'right_error=([\d.]+) weapon_error=([\d.]+)',block)
    assert right and all(float(a)==float(b)==0 for a,b in right)
    result=dict(passed=True,actions=actions,fp_poses=poses,normal_clock=True,F4_reload=True,active_overlay=True,
                width=1920,height=1080,right_hand_and_weapon_preserved=True,
                **{key:hashlib.sha256(path.read_bytes()).hexdigest() for key,path in
                   [('client_sha256',mod/'cl_dlls/client.dll'),('server_sha256',mod/'dlls/hl.dll'),('renderer_sha256',engine/'ref_gl.dll')]})
    out.mkdir(parents=True,exist_ok=True)
    for name in ('f4_raise','f4_lower'):shutil.copy2(mod/'scrshots'/(name+'.png'),out/(name+'.png'))
    shutil.copy2(engine/'f4.log',out/'native.log');(out/'result.json').write_text(json.dumps(result,indent=2))
    print('PASS fresh R1 after F4:',json.dumps(result),flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate-dir',type=Path);run(p.parse_args().candidate_dir)
