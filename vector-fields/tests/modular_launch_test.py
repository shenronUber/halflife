"""Bounded smoke of the public mod and the exact interactive startup config."""
import hashlib
import json
import shutil
import subprocess
import sys
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from play_modular import prepare,LIVE,MOD_NAME
from native_workspace import port

def run():
    mod=prepare()
    (mod/'modular_launch_smoke.cfg').write_text('gl_vsync 0\nhost_framerate .016666667\nfps_max 60\nwait 120\ndeveloper 1\necho MODULAR_LAUNCH_READY\ncmd vf_modular_info\ncmd vf_modular_check\ncmd vf_traversal_info\n+attack\nwait 12\n-attack\ncmd vf_traversal_info\nwait 12\nscreenshot scrshots/modular_launch.png\nwait 4\nquit\n',encoding='ascii')
    process=subprocess.Popen([str(LIVE/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game',MOD_NAME,'-windowed','-width','1280','-height','720','-nointro','-nowriteconfig','-dev','1',
        '-port',str(port()),'-clientport',str(port()),'-log','modular-launch-smoke.log','+sv_cheats','1','+maxplayers','1',
        '+map','vf_modular','+vf_modular_seed','42','+map','vf_modular','+exec','modular_play.cfg','+exec','modular_launch_smoke.cfg'],
        cwd=LIVE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:process.wait(timeout=60)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=8)
    text=(LIVE/'modular-launch-smoke.log').read_text(errors='replace')
    out=ROOT/'docs/validation/modular';shutil.copy2(LIVE/'modular-launch-smoke.log',out/'launch.log')
    shutil.copy2(mod/'scrshots/modular_launch.png',out/'modular_launch.png')
    assert process.returncode==0 and 'VFModular check seed=42 candidates=102 mismatches=0' in text
    assert 'Host_Error' not in text and 'Unknown command: vf_modular' not in text
    clips=[int(v)for v in re.findall(r'VFTraversal .*?clip=(-?\d+)',text)]
    assert len(clips)>=2 and clips[0]>0 and 0<=clips[1]<clips[0],('Modular arrival must have a usable rifle',clips)
    report=dict(passed=True,exit_code=process.returncode,seed=42,mod=MOD_NAME,configuration='modular_play.cfg',
                files={str(path.relative_to(ROOT.parent)):hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in (mod/'dlls/hl.dll',mod/'cl_dlls/client.dll',mod/'maps/vf_modular.bsp')})
    (out/'launch.json').write_text(json.dumps(report,indent=2))
    print('PASS installed modular launcher configuration',flush=True)

if __name__=='__main__':run()
