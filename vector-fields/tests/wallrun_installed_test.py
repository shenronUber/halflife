"""Six focused commands using a fresh copy of the actual installed release."""
import json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from native_workspace import engine_path,stage_installed,port
from build_weapon_melee import PROJECT,digest
from release import verify_deployment
OUT=ROOT/'build/wallrun-intent'

def run():
    report=json.loads((OUT/'installed.json').read_text())
    expected=json.loads((OUT/'runtime-before.json').read_text());expected.update(report['files'])
    assert all(digest(PROJECT/p)==sha for p,sha in expected.items())
    engine=engine_path(OUT/'post-main');mod=stage_installed(engine,'vf_animation')
    binaries={name:digest(mod/folder/name)for folder,name in [('cl_dlls','client.dll'),('dlls','hl.dll')]}
    assert all(h==digest(PROJECT/'runtime/vector-engine/vf_visual'/folder/name)for folder,name in [('cl_dlls','client.dll'),('dlls','hl.dll')]for h in [binaries[name]])
    lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667',
           'sv_cheats 1','god','weapon_9mmAR','wait 30','vf_reference 0','wait 20','vf_commit','wait 20','vf_character','vf_character','wait 10']
    def check(name):lines.extend(['echo MAIN_WR_'+name,'cmd vf_traversal_info','wait 2'])
    lines+=['cmd vf_traversal_place -800 -1006 128 300 320 0 0','vf_traversal_look 300 0','+forward','+jump','wait 4','-jump'];check('ENTRY')
    lines+=['vf_traversal_look 90 -85','wait 5'];check('POS_90')
    lines+=['vf_traversal_look 270 85','wait 5'];check('NEG_90')
    lines+=['vf_traversal_look 90.1 0','wait 1'];check('OVER_90')
    lines+=['-forward','-jump','wait 15','cmd vf_traversal_place -800 -1006 128 300 320 0 0','vf_traversal_look 300 0','+forward','wait 5'];check('NO_JUMP')
    lines+=['-forward','wait 15','cmd vf_traversal_place -800 -1006 128 0 320 0 0','vf_traversal_look 0 0','+forward','+jump','wait 5'];check('PARALLEL_JUMP')
    lines+=['quit'];(mod/'post_wallrun.cfg').write_text('\n'.join(lines)+'\n')
    p=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-clientport',str(port()),
        '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720',
        '-console','-dev','2','-nointro','-nowriteconfig','-log','post-wallrun.log','+developer','2','+sv_cheats','1',
        '+maxplayers','1','+map','vf_traversal','+exec','post_wallrun.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:p.wait(90);assert p.returncode==0
    finally:
        if p.poll()is None:p.terminate();p.wait(10)
    log=(engine/'post-wallrun.log').read_text(errors='replace');(OUT/'post-main.log').write_text(log)
    assert not any(e in log for e in ['Host_Error','SV_Error','VFState rejected'])
    states={}
    for name,block in re.findall(r'MAIN_WR_(\w+)\s+(.*?)(?=MAIN_WR_|$)',log,re.S):
        m=re.search(r'VFTraversal phase=(\d+) state=(\d+) origin=([-\d.,]+) velocity=([-\d.,]+)',block);assert m,name
        states[name]=dict(phase=int(m[1]),origin=list(map(float,m[3].split(','))),velocity=list(map(float,m[4].split(','))))
    assert {n:s['phase']for n,s in states.items()}==dict(ENTRY=8,POS_90=8,NEG_90=8,OVER_90=0,NO_JUMP=0,PARALLEL_JUMP=0),states
    for name in ['POS_90','NEG_90']:assert states[name]['velocity'][0]>300 and abs(states[name]['velocity'][1])<25
    assert states['OVER_90']['velocity'][2]<0
    assert all(digest(PROJECT/p)==sha for p,sha in expected.items())
    report['post_install_native']=dict(passed=True,states=states,client_sha256=binaries['client.dll'],server_sha256=binaries['hl.dll'])
    report['post_install_delivery']=verify_deployment(PROJECT/'runtime/vector-engine/vf_visual')
    for target in [OUT/'installed.json',ROOT/'docs/validation/wallrun-intent-2026-10-12.json']:target.write_text(json.dumps(report,indent=2))
    print('PASS installed main wall run:',{n:s['phase']for n,s in states.items()},flush=True)
if __name__=='__main__':run()
