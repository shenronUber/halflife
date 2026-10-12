"""Compile a private source snapshot; concurrent caches and assets stay untouched."""
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
OUT=ROOT/'build/wallrun'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def copy_changed(source,target):
    source=Path(source);target=Path(target)
    if not target.exists() or source.read_bytes()!=target.read_bytes():shutil.copy2(source,target)
def command(args,cwd,log):
    environment=dict(os.environ,PYTHONUTF8='1')
    with Path(log).open('w',encoding='utf-8') as stream:
        result=subprocess.run(args,cwd=cwd,env=environment,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f'Build failed: {log}')
def build(engine_only=False,movement_only=False):
    OUT.mkdir(parents=True,exist_ok=True)
    snapshot=OUT/'source';snapshot.mkdir(exist_ok=True)
    ignored=shutil.ignore_patterns('.git','__pycache__','*.obj','*.pdb','*.log','*.ilk','*.exp')
    if movement_only:
        for name in ('pm_shared/pm_wallrun.inc','game_shared/vf_wallrun.h','game_shared/vf_traversal.h','dlls/player.cpp'):
            copy_changed(PROJECT/name,snapshot/name)
    elif not engine_only:
        for folder in ('dlls','cl_dll','common','engine','pm_shared','game_shared','public','external','lib','utils/vgui','utils/common','projects/vs2019'):
            shutil.copytree(PROJECT/folder,snapshot/folder,dirs_exist_ok=True,ignore=ignored)
    source_hashes={str(p.relative_to(snapshot)):digest(p)for p in snapshot.rglob('*')if p.is_file()}
    vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    vs=Path(subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip())
    msbuild=vs/'MSBuild/Current/Bin/MSBuild.exe'
    for name,project in ([] if engine_only else [('server','hldll'),('client','hl_cdll')]):
        (OUT/name).mkdir(exist_ok=True)
        command([str(msbuild),str(snapshot/f'projects/vs2019/{project}.vcxproj'),'/t:Build','/m','/nologo','/v:quiet','/clp:ErrorsOnly',
            '/p:Configuration=Release','/p:Platform=Win32','/p:PlatformToolset=v143','/p:WindowsTargetPlatformVersion=10.0.22000.0',
            '/p:PostBuildEventUseInBuild=false',f'/p:OutDir={OUT/name}/',f'/p:IntDir={OUT/("obj-"+name)}/'],snapshot,OUT/f'{name}.log')
        print('PASS private wall-run '+name,flush=True)
    engine_source=OUT/'engine-source'
    if not engine_only and not movement_only:
        shutil.copytree(PROJECT/'runtime/engine-source',engine_source,dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('.git','build','.builds','.lock-*','__pycache__','*.log'))
    # This checkout names the DLL and dedicated PDBs explicitly. Waf's MSVC
    # tool otherwise invents xash.pdb for both. Repair only our private tool.
    for msvc in engine_source.glob('waf3-*/waflib/Tools/msvc.py'):
        code=msvc.read_text(encoding='utf-8')
        old="pdbnode = self.link_task.outputs[0].change_ext('.pdb')"
        new="pdbpath = next((flag[5:] for flag in list(getattr(self, 'linkflags', [])) + list(self.env.LINKFLAGS) if flag.lower().startswith('/pdb:')), None)\n\t\t\t\tpdbnode = self.bld.root.make_node(pdbpath) if pdbpath else self.link_task.outputs[0].change_ext('.pdb')"
        if 'pdbpath = next(' not in code:
            if old not in code:raise RuntimeError('Private Waf PDB adapter changed; inspect before building.')
            msvc.write_text(code.replace(old,new),encoding='utf-8')
        elif 'for flag in self.env.LINKFLAGS if' in code:
            msvc.write_text(code.replace('for flag in self.env.LINKFLAGS if',"for flag in list(getattr(self, 'linkflags', [])) + list(self.env.LINKFLAGS) if"),encoding='utf-8')
    for name in ('vf_engine_api.h','vf_assembly_policy.h','vf_traversal.h','vf_wallrun.h','vf_headgear.h','vf_player_pose.h'):
        shutil.copy2(snapshot/'game_shared'/name,engine_source/'common'/name)
    for name in ('vf_player_pose.inc','vf_wallrun_pose.inc','gl_vf_headgear.inc','sv_vf_pose.inc'):
        shutil.copy2(ROOT/'engine'/name,engine_source/'common'/name)
    for name in ('gl_vf.inc','gl_vf_perf.inc','gl_vf_headgear.inc','vf_player_pose.inc','vf_wallrun_pose.inc'):
        shutil.copy2(ROOT/'engine'/name,engine_source/'ref/gl'/name)
    sdl=PROJECT/'devtools/SDL2-sdk/SDL2-2.32.10'
    if not engine_only:
        command([sys.executable,'waf','configure',f'--sdl2={sdl}','-T','release','--enable-tests','--enable-dedicated','--enable-bundled-deps',
            '--msvc_version=msvc 17.4','--msvc_targets=x86','--disable-werror'],engine_source,OUT/'engine-configure.log')
    command([sys.executable,'waf','build','-j','8','--notests'],engine_source,OUT/'engine-build.log')
    command([sys.executable,'waf','build','-j','1','--alltests'],engine_source,OUT/'engine-tests.log')
    engine=OUT/'engine'
    command([sys.executable,'waf','install',f'--destdir={engine}'],engine_source,OUT/'engine-install.log')
    shutil.copy2(sdl/'lib/x86/SDL2.dll',engine/'SDL2.dll')
    metadata=json.loads((PROJECT/'runtime/vector-engine/vector-engine-build.json').read_text(encoding='utf-8-sig'))
    metadata['wallrun_version']=1
    metadata['player_pose_version']=1
    metadata['built_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    for field in ('body_verified','headgear_verified','motion_validation','motion_published_utc'):
        metadata.pop(field,None)
    for key,name in (('player_pose_sha256','vf_player_pose.inc'),('player_collision_sha256','sv_vf_pose.inc'),('renderer_sha256','gl_vf.inc')):
        metadata[key]=digest(engine_source/('ref/gl' if name=='gl_vf.inc' else 'common')/name).upper()
    metadata['wallrun_pose_sha256']=digest(engine_source/'common/vf_wallrun_pose.inc').upper()
    metadata['binaries']={name:digest(engine/name).upper()for name in ('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')}
    (engine/'vector-engine-build.json').write_text(json.dumps(metadata,indent=2))
    (OUT/'source-hashes.json').write_text(json.dumps(source_hashes,indent=2))
    print('PASS isolated wall-run engine and engine tests',flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--engine-only',action='store_true');parser.add_argument('--movement-only',action='store_true');args=parser.parse_args();build(args.engine_only,args.movement_only)
