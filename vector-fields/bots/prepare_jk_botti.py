"""Prepare the isolated Windows jk_botti experiment from pinned downloads."""
import argparse,hashlib,json,shutil,subprocess,tarfile,urllib.request,zipfile,sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]
ROOT=PROJECT/'runtime/jk-botti-research'
SOURCE_COMMIT='b7e94c9c2f578672ebad9237b67fd849761f3702'
DOWNLOADS=[
('jk_botti-v1.62-win32.tar.xz','https://github.com/Bots-United/jk_botti/releases/download/v1.62/jk_botti-v1.62-win32.tar.xz','8fbbd14119e26c76354c220b2be01bf335c8111c50e56dee8062ce0017f7ca68'),
('jk_botti-v1.62-source.zip','https://api.github.com/repos/Bots-United/jk_botti/zipball/v1.62','5bd8c218c83b995d0252847b534c79bf4cf294ce60d3c7e958c2d16ce6081f88'),
('metamod-fwgs_windows_x86.zip','https://github.com/FWGS/metamod-fwgs/releases/download/continuous/metamod-fwgs_windows_x86.zip','1be2a6727c703dcc3a4b06ceaa6ffa6fb88b0481b6978b24e89759884f310120')]

def download():
    folder=ROOT/'downloads';folder.mkdir(parents=True,exist_ok=True)
    for name,url,digest in DOWNLOADS:
        target=folder/name
        if not target.exists():
            print('Downloading',name,flush=True)
            with urllib.request.urlopen(url,timeout=45) as r:target.write_bytes(r.read())
        if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise RuntimeError('Download differs from tested artifact: '+name)
    with tarfile.open(folder/DOWNLOADS[0][0]) as archive:
        destination=ROOT/'package';destination.mkdir(exist_ok=True)
        for entry in archive.getmembers():
            if not (destination/entry.name).resolve().is_relative_to(destination.resolve()) or entry.issym() or entry.islnk():raise ValueError('Unsafe archive entry')
        archive.extractall(destination)
    for name,destination in [(DOWNLOADS[1][0],ROOT/'source'),(DOWNLOADS[2][0],ROOT/'metamod')]:
        destination.mkdir(exist_ok=True)
        with zipfile.ZipFile(folder/name) as archive:
            for entry in archive.namelist():
                if not (destination/entry).resolve().is_relative_to(destination.resolve()):raise ValueError('Unsafe archive entry')
            archive.extractall(destination)

def build_probe(engine):
    vswhere=Path('C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe')
    installation=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
    if not installation:raise RuntimeError('Visual Studio C++ build tools missing')
    vcvars=Path(installation)/'VC/Auxiliary/Build/vcvarsall.bat'
    source=next((ROOT/'source').glob('Bots-United-jk_botti-*'))
    # Literal batch content; only known workspace and tool paths are interpolated.
    command='@call "'+str(vcvars)+'" x86 >nul\n@cl /nologo /LD /MT /EHsc /W3 /D_CRT_SECURE_NO_WARNINGS /I dlls /I engine /I common /I pm_shared /I public /I "'+str(source/'metamod')+'" vector-fields\\bots\\jk_botti_probe.cpp /Fo:runtime\\jk-botti-research\\probe.obj /Fe:runtime\\jk-botti-research\\engine\\valve\\addons\\metamod\\vf_bot_probe.dll /link /DEF:vector-fields\\bots\\jk_botti_probe.def\n'
    script=ROOT/'build-probe.cmd';script.write_text(command,encoding='ascii')
    subprocess.run(['cmd.exe','/d','/c',str(script)],cwd=PROJECT,check=True)

def adapt_maps(mod):
    sys.path.insert(0,str(PROJECT/'vector-fields'))
    from import_tfc import entities,write_entities
    records={}
    for source,name in [('vf_cs_de_dust2','vf_bot_dust2'),('vf_tfc_2fort','vf_bot_2fort')]:
        data=(mod/'maps'/(source+'.bsp')).read_bytes();items=entities(data);count=0
        for item in items:
            if item.get('classname') in ('info_player_teamspawn','i_p_t'):item['classname']='info_player_deathmatch';count+=1
        items.append({'classname':'game_player_equip','item_suit':'1','weapon_9mmAR':'1','ammo_9mmbox':'3'})
        (mod/'maps'/(name+'.bsp')).write_bytes(write_entities(data,items))
        records[name]={'source':source,'converted_spawns':count,'equipment':['weapon_9mmAR','ammo_9mmbox'],'waypoints':'no complete navigation supplied'}
    (ROOT/'map-adaptations.json').write_text(json.dumps(records,indent=2))

def sync_voice_runtime(engine):
    # DLLs, models and maps must travel together, including the fragment skin bank.
    vf=PROJECT/'vector-fields';mod=engine/'valve';voices=vf/'assets/audio/operators'
    sys.path.insert(0,str(vf))
    from release import deployment_files,verify_deployment,prepare_native_renderer_update,check_native_interface
    files=deployment_files(vf)
    for source,_ in files:
        if not source.is_file():raise RuntimeError('Build the current Vector Fields assets first: '+str(source))
    prepare_native_renderer_update(engine,vf/'build/client/client.dll')
    check_native_interface(engine,vf/'build/client/client.dll')
    for source,relative in files:
        target=mod/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    verify_deployment(mod,vf)
    manifest=json.loads((voices/'manifest.json').read_text(encoding='utf-8-sig'))
    for clip in manifest['clips']:
        if clip['event']==4:continue # obsolete spoken death; VFDeath uses its own bank
        target=mod/'sound'/clip['path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(voices/clip['path'].removeprefix('vf_voices/'),target)
    shutil.copy2(voices/'manifest.json',mod/'vf/voice-manifest.json')
    sys.path.insert(0,str(vf))
    from death_voice_workshop import deploy as deploy_death_voices
    deploy_death_voices(mod)
    if not (mod/'vf_voice_behavior.cfg').exists():shutil.copy2(vf/'data/voice_behavior.cfg',mod/'vf_voice_behavior.cfg')

def prepare(skip_download=False):
    if not skip_download:download()
    original=PROJECT/'runtime/vector-engine';engine=ROOT/'engine';mod=engine/'valve';base=original/'vf_visual'
    engine.mkdir(parents=True,exist_ok=True);mod.mkdir(exist_ok=True)
    for item in original.iterdir():
        if item.is_file() and item.suffix.lower() in ('.exe','.dll'):shutil.copy2(item,engine/item.name)
    for folder in ('models','sprites','sound','vf','maps','overviews','dlls','cl_dlls'):
        shutil.copytree(base/folder,mod/folder,dirs_exist_ok=True)
    shutil.copytree(original/'cs_assets',engine/'cs_assets',dirs_exist_ok=True)
    for source,target in [(base/'decals.wad',mod/'decals.wad'),(base/'lab_controls.cfg',mod/'lab_controls.cfg'),(original/'valve/extras.pk3',mod/'extras.pk3')]:shutil.copy2(source,target)
    for item in (ROOT/'package/addons').rglob('*'):
        if not item.is_file():continue
        target=mod/'addons'/item.relative_to(ROOT/'package/addons');target.parent.mkdir(parents=True,exist_ok=True)
        # Preserve learned navigation on subsequent preparations.
        if item.suffix=='.wpt' and target.exists():continue
        shutil.copy2(item,target)
    shutil.copytree(ROOT/'metamod/addons/metamod',mod/'addons/metamod',dirs_exist_ok=True)
    (mod/'gameinfo.txt').write_text('title "Vector Fields - laboratoire jk_botti"\nbasedir "valve"\nfallback_dir "cs_assets"\nstartmap "vf_range"\ngamedll "addons/metamod/metamod.dll"\ndllpath "cl_dlls"\ngamemode "normal"\nmax_edicts "2048"\n',encoding='ascii')
    (mod/'addons/metamod/config.ini').write_text('gamedll dlls/hl.dll\ndebuglevel 0\n',encoding='ascii')
    (mod/'addons/metamod/plugins.ini').write_text('win32 addons/jk_botti/dlls/jk_botti_mm.dll\nwin32 addons/metamod/vf_bot_probe.dll\n',encoding='ascii')
    (mod/'addons/jk_botti/jk_botti.cfg').write_text('pause 2\nautowaypoint 1\nbot_chat_percent 0\nbot_taunt_percent 0\nbot_whine_percent 0\nbot_endgame_percent 0\nbot_logo_percent 0\nbot_conntimes 0\nbotskill 3\naddbot gordon VF_BOT_A 3\naddbot barney VF_BOT_B 3\n',encoding='ascii')
    sync_voice_runtime(engine)
    build_probe(engine);adapt_maps(mod)
    (ROOT/'prepared.json').write_text(json.dumps({'jk_botti':'1.62','source_commit':SOURCE_COMMIT,'game_dll_sha256':hashlib.sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest(),'runtime':str(engine)},indent=2))
    print('Prepared:',engine,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--skip-download',action='store_true');args=p.parse_args();prepare(args.skip_download)
