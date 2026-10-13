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
from build_release import launch_command

def run():
    mod=prepare()
    out=ROOT/'docs/validation/modular';out.mkdir(parents=True,exist_ok=True)
    cases=[]
    for mapname,candidates in [('vf_modular',102),('vf_tiles',141)]:
        screenshot=mapname+'_launch.png';logname=mapname+'-launch-smoke.log'
        (mod/'modular_launch_smoke.cfg').write_text('gl_vsync 0\nhost_framerate .016666667\nfps_max 60\nwait 120\ndeveloper 1\necho MODULAR_LAUNCH_READY\ncmd vf_modular_info\ncmd vf_modular_check\ncmd vf_traversal_info\n+attack\nwait 12\n-attack\ncmd vf_traversal_info\nwait 12\nscreenshot scrshots/'+screenshot+'\nwait 4\nquit\n',encoding='ascii')
        command=launch_command(mapname,seed=42,engine=LIVE)
        command[1:1]=['-nowriteconfig','-dev','1','-port',str(port()),'-clientport',str(port()),
                      '-log',logname,'+sv_cheats','1','+maxplayers','1']
        command+=['+exec','modular_launch_smoke.cfg']
        process=subprocess.Popen(command,cwd=LIVE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:process.wait(timeout=60)
        finally:
            if process.poll() is None:process.terminate();process.wait(timeout=8)
        text=(LIVE/logname).read_text(errors='replace')
        shutil.copy2(LIVE/logname,out/logname)
        shutil.copy2(mod/'scrshots'/screenshot,out/screenshot)
        assert process.returncode==0 and f'VFModular check seed=42 candidates={candidates} mismatches=0' in text
        assert 'Host_Error' not in text and 'Unknown command: vf_modular' not in text
        seeds=[int(v)for v in re.findall(r'VFModular seed=(\d+)',text)]
        assert seeds and all(seed==42 for seed in seeds),('Seed must apply to the first generated layout',seeds)
        if mapname=='vf_tiles':
            forced=re.findall(r'VFTiles .*?forced=(-?\d+)',text)
            assert forced and all(value=='-1'for value in forced),forced
        clips=[int(v)for v in re.findall(r'VFTraversal .*?clip=(-?\d+)',text)]
        assert len(clips)>=2 and clips[0]>0 and 0<=clips[1]<clips[0],('Modular arrival must have a usable rifle',clips)
        cases.append(dict(map=mapname,passed=True,exit_code=process.returncode,seed=42,command=command,
                          clips=clips,observed_seeds=seeds,map_requests=command.count('+map'),
                          files={str(path.relative_to(ROOT.parent)):hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in (mod/'dlls/hl.dll',mod/'cl_dlls/client.dll',mod/'maps'/(mapname+'.bsp'))}))
    report=dict(passed=True,mod=MOD_NAME,cases=cases)
    (out/'launch.json').write_text(json.dumps(report,indent=2))
    print('PASS public launcher: both modular maps, seed before first layout and usable rifle',flush=True)

if __name__=='__main__':run()
