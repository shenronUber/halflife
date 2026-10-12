"""Disposable native R1 melee session; installed binaries/resources are read-only."""
import shutil,subprocess
from pathlib import Path
from native_workspace import engine_path,copy_resources,private_copy
from release import check_native_interface
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'runtime/vector-engine';OUT=ROOT/'build/weapon-melee'
def stage(candidate=True):
    engine=engine_path(OUT/'native-engine');mod=engine/'vf_melee';engine.mkdir(parents=True,exist_ok=True)
    client=OUT/'client/client.dll' if candidate else BASE/'vf_visual/cl_dlls/client.dll'
    binaries=BASE
    try:check_native_interface(binaries,client)
    except RuntimeError:
        if not candidate:raise
        binaries=ROOT/'build/combat-fixes/engine';check_native_interface(binaries,client)
        import json,hashlib
        metadata=json.loads((binaries/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
        assert all(hashlib.sha256((binaries/n).read_bytes()).hexdigest().lower()==sha.lower() for n,sha in metadata['binaries'].items())
    for path in binaries.iterdir():
        if path.is_file() and (path.suffix.lower() in ('.exe','.dll') or path.name=='vector-engine-build.json'):private_copy(path,engine/path.name)
    import json,hashlib
    metadata=json.loads((engine/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
    assert all(hashlib.sha256((engine/n).read_bytes()).hexdigest().lower()==sha.lower() for n,sha in metadata['binaries'].items()),'Engine bundle changed while staging'
    for name in ('valve','vf_visual'):copy_resources(BASE/name,engine/name,ignore=shutil.ignore_patterns('scrshots','save','*.log','*.tmp','*.pdb','.fontcache'))
    for name in ('cl_dlls','dlls','scrshots','vf','models/vf_melee'):(mod/name).mkdir(parents=True,exist_ok=True)
    for part,filename,destination in (('client','client.dll','cl_dlls'),('server','hl.dll','dlls')):
        source=OUT/part/filename if candidate else BASE/'vf_visual'/destination/filename
        private_copy(source,mod/destination/filename)
    if candidate:
        for path in (ROOT/'generated/weapon-melee').glob('*.mdl'):private_copy(path,mod/'models/vf_melee'/path.name)
    private_copy(BASE/'vf_visual/delta.lst',mod/'delta.lst')
    (mod/'gameinfo.txt').write_text('title "Vector Fields - frappe au canon"\nbasedir "valve"\nfallback_dir "vf_visual"\ngamedll "dlls/hl.dll"\ndllpath "cl_dlls"\ngamemode "normal"\nmax_edicts "2048"\n')
    check_native_interface(engine,mod/'cl_dlls/client.dll');return engine,mod
def command(engine,mod,cfg):
    return [str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game',mod.name,'-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log','weapon-melee.log',
        '-port','27183','-clientport','27184','+exec','lab_controls.cfg','+sv_lan','1','+sv_cheats','1','+map','vf_range','+exec',cfg.name]
def run():
    engine,mod=stage(False);cfg=mod/'melee_play.cfg';cfg.write_text('wait 180\nbind v "vf_melee"\nweapon_9mmAR\nwait 30\n')
    process=subprocess.Popen(command(engine,mod,cfg),cwd=engine)
    try:process.wait()
    except KeyboardInterrupt:process.terminate();process.wait(10)
if __name__=='__main__':run()
