"""Body visibility and cancelling a strike when another activity takes over."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import integration_native_test as audit
from native_workspace import port

def run():
    engine,mod=audit.fixture('melee-body-transitions');out=audit.OUT/'melee_integration';out.mkdir(parents=True,exist_ok=True)
    lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667','sv_cheats 1','god','weapon_9mmAR','wait 35',
           'vf_reference 0','wait 25','vf_commit','wait 25','vf_ui_pointer 1220 40 1','wait 3','vf_ui_pointer 1220 40 0','wait 15',
           'cmd vf_melee_place -300 -240 36 0 85','vf_traversal_look 0 85','wait 15','vf_melee','wait 20','echo BODY_BEGIN','cmd vf_melee_info','wait 4','screenshot scrshots/melee_body.png','wait 4','echo BODY_END','wait 80',
           'cmd vf_range_reset 0','cmd vf_melee_place -300 -198 36 90 15','wait 15','echo MENU_BEGIN','vf_melee','wait 8','vf_reference','wait 20','cmd vf_melee_info','cmd vf_range_info','wait 3','echo MENU_END',
           'vf_ui_pointer 1220 40 1','wait 3','vf_ui_pointer 1220 40 0','wait 90',
           'map vf_traversal','wait 180','weapon_9mmAR','wait 60','cmd vf_traversal_place 128 -750 36 0','wait 15',
           'echo HANG_BEGIN','vf_melee','wait 8','cmd vf_traversal_place 238 0 54 0','wait 1','+jump','wait 22','-jump','cmd vf_traversal_info','cmd vf_melee_info','wait 3','echo HANG_END','quit']
    for part,start in enumerate(range(0,len(lines),70)):
        chunk=lines[start:start+70]
        if start+70<len(lines):chunk.append(f'exec melee_integration_{part+1}.cfg')
        (mod/f'melee_integration_{part}.cfg').write_text('\n'.join(chunk)+'\n')
    p=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-clientport',str(port()),'-dev','2',
        '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','melee-integration.log',
        '+sv_cheats','1','+developer','2','+map','vf_range','+exec','melee_integration_0.cfg'],cwd=engine)
    try:p.wait(120);assert p.returncode==0
    finally:
        if p.poll() is None:p.terminate();p.wait(10)
    log=(engine/'melee-integration.log').read_text(errors='replace');(out/'native.log').write_text(log)
    def block(name):return log.split(name+'_BEGIN ')[1].split(name+'_END ')[0]
    body=block('BODY');assert re.search(r'VFMelee server: active=1 .*model=models/vf_melee/',body)
    draws=re.findall(r'VFFirstPersonBody parts=(\d+) mask=(\d+) phase=0',body)
    assert draws and all(int(count)>0 and int(mask)&24==24 for count,mask in draws),'Legs/boots vanished during the strike'
    for name in ['MENU','HANG']:
        part=block(name);assert 'VFMelee start:' in part,(name,'action never started')
        assert 'VFMelee server: active=0' in part and 'VFMelee impact:' not in part,(name,'queued impact survived cancellation')
    assert 'VFTraversal phase=2' in block('HANG'),'Ledge catch did not take ownership'
    assert re.search(r'VFRange info target=0 .*health=300.0 alive=1',block('MENU')),block('MENU')
    assert not any(x in log for x in ['Host_Error','SV_Error','VFState rejected'])
    shutil.copy2(mod/'scrshots/melee_body.png',out/'melee_body.png')
    report=dict(passed=True,first_person_body_during_melee=True,body_samples=len(draws),menu_cancels_before_impact=True,ledge_catch_cancels_before_impact=True,
        client_sha256=hashlib.sha256((mod/'cl_dlls/client.dll').read_bytes()).hexdigest(),server_sha256=hashlib.sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest(),renderer_sha256=hashlib.sha256((engine/'ref_gl.dll').read_bytes()).hexdigest())
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS melee integration: visible body, inventory cancellation and ledge handoff',flush=True)

if __name__=='__main__':
    audit.SNAP=ROOT/'build/integration-audit/candidate';audit.OUT=ROOT/'build/integration-audit/final-native';run()
