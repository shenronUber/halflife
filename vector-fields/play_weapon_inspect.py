"""An isolated inspection session over the currently installed game and assets."""
import argparse,shutil,subprocess
from pathlib import Path
from native_workspace import engine_path,copy_resources,private_copy
from release import check_native_interface
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'runtime/vector-engine'
OUT=ROOT/'build/weapon-inspect'

def stage(candidate=True):
    engine=engine_path(OUT/'native-engine');mod=engine/'vf_inspect'
    engine.mkdir(parents=True,exist_ok=True)
    for p in BASE.iterdir():
        if p.is_file() and p.suffix.lower() in ('.exe','.dll'):private_copy(p,engine/p.name)
    for name in ('valve','vf_visual'):
        if (BASE/name).is_dir():copy_resources(BASE/name,engine/name,
            ignore=shutil.ignore_patterns('scrshots','save','*.log','*.tmp','*.pdb','.fontcache'))
    for name in ('cl_dlls','dlls','vf','scrshots'):(mod/name).mkdir(parents=True,exist_ok=True)
    client=OUT/'client/client.dll' if candidate else BASE/'vf_visual/cl_dlls/client.dll'
    private_copy(client,mod/'cl_dlls/client.dll')
    private_copy(BASE/'vf_visual/dlls/hl.dll',mod/'dlls/hl.dll')
    private_copy(BASE/'vf_visual/delta.lst',mod/'delta.lst')
    if candidate:
        for path in (ROOT/'generated/weapon-inspect').glob('*.mdl'):
            target=mod/'models/vf_inspect'/path.name;target.parent.mkdir(parents=True,exist_ok=True)
            private_copy(path,target)
    (mod/'gameinfo.txt').write_text('title "Vector Fields - inspection"\nbasedir "valve"\nfallback_dir "vf_visual"\ngamedll "dlls/hl.dll"\ndllpath "cl_dlls"\ngamemode "normal"\nmax_edicts "2048"\n')
    check_native_interface(BASE,client)
    return engine,mod

def command(engine,mod,cfg):
    return [str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,
        '-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig',
        '-log','weapon-inspect.log','-port','27173','-clientport','27174','+exec','lab_controls.cfg',
        '+sv_lan','1','+sv_cheats','1','+map','vf_range','+exec',cfg.name]

def run():
    engine,mod=stage(candidate=False)
    cfg=mod/'inspect_play.cfg'
    cfg.write_text('wait 180\nbind i "vf_inspect"\nweapon_9mmAR\nwait 30\n',encoding='ascii')
    process=subprocess.Popen(command(engine,mod,cfg),cwd=engine)
    try:process.wait()
    except KeyboardInterrupt:
        process.terminate();process.wait(timeout=10)

if __name__=='__main__':run()
