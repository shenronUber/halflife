"""Headgear renderer retains own-body, crouch, slide and ledge rendering."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from headgear_preview import stage,asset_library
from native_workspace import shared_copy,port
def run(candidate=None):
    engine,mod=stage('headgear-body-regression',candidate)
    shared_copy(ROOT/'generated/traversal-range/vf_traversal.bsp',mod/'maps/vf_traversal.bsp')
    script='wait 180\ndeveloper 2\ncon_notifytime -1\ngl_vsync 0\nfps_max 30\nhost_framerate .03333333\nhud_draw 0\nsv_cheats 1\ngod\ncmd give weapon_9mmAR\nweapon_9mmAR\nwait 40\n'
    cases=[('standing',['cmd vf_traversal_place 128 -750 36 0','vf_traversal_look 0 80']),
           ('crouched',['vf_traversal_look 0 60','+duck','wait 20']),
           ('sliding',['-duck','wait 50','cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1','vf_traversal_look 0 50','+duck','wait 8']),
           ('hanging',['-duck','wait 70','cmd vf_traversal_place 238 0 54 0','vf_traversal_look 0 0','wait 1','+jump','wait 20','-jump','vf_traversal_look 0 80'])]
    for name,commands in cases:script+='\n'.join(commands)+f'\nwait 3\necho HEADGEAR_BODY_{name}\ncmd vf_traversal_info\nscreenshot scrshots/{name}.png\nwait 2\n'
    script+='quit\n';(mod/'body.cfg').write_text(script,encoding='ascii')
    p=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2','-rodir',str(asset_library()),'-game',mod.name,
        '-windowed','-width','960','-height','540','-console','-nointro','-nowriteconfig','-log','body.log','-port',str(port()),'-clientport',str(port()),
        '+exec','lab_controls.cfg','+sv_cheats','1','+developer','2','+map','vf_traversal','+exec','body.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:p.wait(timeout=100);assert p.returncode==0
    finally:
        if p.poll()is None:p.terminate();p.wait(timeout=10)
    log=(engine/'body.log').read_text(errors='replace')
    assert 'VFFirstPersonBody' in log and 'native extension v4 connected' in log
    assert all('HEADGEAR_BODY_'+name in log and (mod/'scrshots'/f'{name}.png').stat().st_size>1000 for name,_ in cases)
    assert not any(x in log for x in ('Host_Error','SV_Error','VFState rejected'))
    target=ROOT/'docs/validation/headgear/body';target.mkdir(parents=True,exist_ok=True)
    for name,_ in cases:shutil.copy2(mod/'scrshots'/f'{name}.png',target/f'{name}.png')
    report=dict(passed=True,renderer_api=4,own_body_rendered=True,cases=[x[0]for x in cases],
                renderer_sha256=__import__('hashlib').sha256((engine/'ref_gl.dll').read_bytes()).hexdigest())
    (ROOT/'build/headgear-action/body-regression.json').write_text(json.dumps(report,indent=2));print('PASS headgear renderer regression: own body, crouch, slide and ledge captures',flush=True)
    return report
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-dir',type=Path);run(parser.parse_args().candidate_dir)
