"""Status shells stay on fitted arm pieces during inspection and melee."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import integration_native_test as audit
from native_workspace import port

def run():
    engine,mod=audit.fixture('gesture-status');out=audit.OUT/'gesture_status';out.mkdir(parents=True,exist_ok=True)
    lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667','sv_cheats 1','god','weapon_9mmAR','wait 35',
        'vf_reference','wait 20','vf_commit','wait 25','vf_character','wait 5','vf_character','wait 15','firstperson',
        'cmd vf_status_dev 1','wait 12','cmd vf_status_apply cryo 6','wait 20',
        'echo STATUS_INSPECT_BEGIN','vf_inspect','wait 12','vf_status_visual_stats','screenshot scrshots/status_inspect.png','wait 3','echo STATUS_INSPECT_END',
        'echo STATUS_MELEE_BEGIN','vf_melee','wait 20','vf_status_visual_stats','screenshot scrshots/status_melee.png','wait 3','echo STATUS_MELEE_END',
        'cmd vf_status_clear','wait 20','vf_status_visual_stats','quit']
    (mod/'gesture_status.cfg').write_text('\n'.join(lines)+'\n')
    p=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-clientport',str(port()),'-dev','2',
        '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','gesture-status.log',
        '+sv_cheats','1','+developer','2','+map','vf_range','+exec','gesture_status.cfg'],cwd=engine)
    try:p.wait(120);assert p.returncode==0
    finally:
        if p.poll() is None:p.terminate();p.wait(10)
    log=(engine/'gesture-status.log').read_text(errors='replace');(out/'native.log').write_text(log)
    for name,folder,prefix in [('INSPECT','vf_inspect','inspect'),('MELEE','vf_melee','melee')]:
        part=log.split('STATUS_'+name+'_BEGIN ')[1].split('STATUS_'+name+'_END ')[0]
        for suffix in ['gloves','sleeves']:
            assert f'VFStatusShell part=models/{folder}/{prefix}_{suffix}.mdl arms=1' in part,(name,suffix)
        draws=re.findall(r'VFStatusShell part=(\S+) arms=(\d)',part);assert draws
        assert all(not active or any(key in model for key in ['gloves','sleeves']) for model,flag in draws for active in [int(flag)]),'Weapon part received an arm shell'
        assert re.search(r'VFStatus visual: .*arms=1 dominant=cryo',part),(name,'status stopped during gesture')
        shutil.copy2(mod/'scrshots'/('status_'+name.lower()+'.png'),out/('status_'+name.lower()+'.png'))
    assert not any(e in log for e in ['Host_Error','SV_Error','VFState rejected'])
    report=dict(passed=True,inspection_arm_shell=True,melee_arm_shell=True,weapon_shell_excluded=True,
        client_sha256=hashlib.sha256((mod/'cl_dlls/client.dll').read_bytes()).hexdigest(),server_sha256=hashlib.sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest(),renderer_sha256=hashlib.sha256((engine/'ref_gl.dll').read_bytes()).hexdigest())
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS status arm shells through inspection and melee; weapon parts excluded',flush=True)

if __name__=='__main__':
    audit.SNAP=ROOT/'build/integration-audit/candidate';audit.OUT=ROOT/'build/integration-audit/final-native';run()
