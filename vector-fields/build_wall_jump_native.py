"""Build private game/engine snapshots while other agents use shared caches."""
import hashlib,json,os,shutil,subprocess,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;OUT=ROOT/'build/wall-jump'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def without_audit_input(text):
    return '\n'.join(line for line in text.splitlines()if 'gEngfuncs.Con_Printf("VFPlayerPoseInput 'not in line)

def command(args,cwd,log):
    with Path(log).open('w')as stream:
        r=subprocess.run(args,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT)
    if r.returncode:raise RuntimeError('Compilation failed: '+str(log))

def adopt_engine(source,candidate):
    """Reuse an independently tested engine only with identical input files."""
    candidate=Path(candidate);compiled=candidate/'engine-source';engine=OUT/'engine';engine.mkdir(exist_ok=True)
    pairs={}
    for n in ('vf_engine_api.h','vf_assembly_policy.h','vf_traversal.h','vf_wallrun.h','vf_headgear.h','vf_player_pose.h'):
        pairs['game_shared/'+n]=compiled/'common'/n
    for n in ('vf_player_pose.inc','vf_wallrun_pose.inc','gl_vf_headgear.inc','sv_vf_pose.inc','gl_vf.inc','gl_vf_perf.inc'):
        pairs['vector-fields/engine/'+n]=compiled/('ref/gl'if n in ('gl_vf.inc','gl_vf_perf.inc')else'common')/n
    diagnostics={}
    for relative,p in pairs.items():
        if digest(PROJECT/relative)==digest(p):continue
        if relative=='vector-fields/engine/vf_player_pose.inc'and without_audit_input((PROJECT/relative).read_text())==without_audit_input(p.read_text()):
            reference=OUT/'input-references/vf_player_pose.inc';reference.parent.mkdir(exist_ok=True);shutil.copy2(p,reference)
            diagnostics[relative]=str(reference)
        else:raise AssertionError(('Engine source drift',relative))
    for relative,p in pairs.items():
        if relative.startswith('game_shared/'):assert digest(source/relative)==digest(p),('Game/engine header mismatch',relative)
    assert 'tests that fail 0/18'in(candidate/'engine-tests.log').read_text()
    hashes={str(p.relative_to(source)):digest(p)for p in source.rglob('*')if p.is_file()}
    hashes.update({n:digest(p)for n,p in pairs.items()})
    metadata=json.loads((candidate/'engine/vector-engine-build.json').read_text())
    for n,expected in metadata['binaries'].items():assert digest(candidate/'engine'/n).upper()==expected.upper()
    for n,expected in metadata['binaries'].items():
        shutil.copy2(candidate/'engine'/n,engine/n)
        assert digest(engine/n).upper()==expected.upper()
    # Candidate-only fixtures also need the unchanged filesystem/menu DLLs.
    # Native installed-game fixtures already inherit them from the runtime.
    for p in(PROJECT/'runtime/vector-engine').iterdir():
        if p.is_file()and p.suffix.lower()in('.dll','.exe')and not(engine/p.name).exists():shutil.copy2(p,engine/p.name)
    metadata['wall_jump_version']=1
    metadata['renderer_sha256']=digest(pairs['vector-fields/engine/gl_vf.inc']).upper()
    metadata['wall_jump_engine_tests']=18
    (engine/'vector-engine-build.json').write_text(json.dumps(metadata,indent=2))
    (OUT/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
    (OUT/'diagnostic-inputs.json').write_text(json.dumps(diagnostics,indent=2))
    print('PASS reused identical engine snapshot: 18 engine tests passed',flush=True)

def refresh_game(source):
    """Incrementally rebuild our existing private game snapshot after drift."""
    source=Path(source);assert OUT.resolve()in source.resolve().parents
    ignored={'.obj','.pdb','.log','.ilk','.exp'}
    for folder in ('dlls','cl_dll','common','engine','pm_shared','game_shared','public','external','lib','utils/vgui','utils/common','projects/vs2019'):
        for p in(PROJECT/folder).rglob('*'):
            if not p.is_file()or p.suffix in ignored or '.git'in p.parts:continue
            target=source/p.relative_to(PROJECT)
            if target.exists()and digest(p)==digest(target):continue
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():os.chmod(target,0o666)
            shutil.copy2(p,target)
    vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    vs=Path(subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip())
    for name,project in [('server','hldll'),('client','hl_cdll')]:
        command([str(vs/'MSBuild/Current/Bin/MSBuild.exe'),str(source/f'projects/vs2019/{project}.vcxproj'),'/t:Build','/m','/nologo','/v:quiet','/clp:ErrorsOnly',
            '/p:Configuration=Release','/p:Platform=Win32','/p:PlatformToolset=v143','/p:WindowsTargetPlatformVersion=10.0.22000.0',
            '/p:PostBuildEventUseInBuild=false',f'/p:OutDir={OUT/name}/',f'/p:IntDir={OUT/("snapshot-obj-"+name)}/'],source,OUT/(name+'.log'))
        print('PASS refreshed snapshot',name,flush=True)

def rebuild_engine(source):
    """Private incremental engine tree, independent of the other agent's Waf."""
    import sys
    engine_source=OUT/'engine-walking'
    def copy_changed(src,dst):
        src=Path(src);dst=Path(dst)
        if dst.exists()and src.stat().st_size==dst.stat().st_size and src.stat().st_mtime_ns==dst.stat().st_mtime_ns:return str(dst)
        # Waf writes outputs into build/, never into these pinned dependency
        # inputs. Sharing them avoids duplicating thousands of SDK files.
        if not dst.exists()and '3rdparty'in src.parts:
            try:os.link(src,dst);return str(dst)
            except OSError:pass
        if dst.exists():
            if dst.stat().st_nlink>1:dst.unlink()
            else:os.chmod(dst,0o666)
        return shutil.copy2(src,dst)
    shutil.copytree(ROOT/'build/wallrun/engine-source',engine_source,dirs_exist_ok=True,copy_function=copy_changed,
        ignore=shutil.ignore_patterns('.git','build','.builds','.lock-*','__pycache__','*.log'))
    for n in ('vf_engine_api.h','vf_assembly_policy.h','vf_traversal.h','vf_wallrun.h','vf_headgear.h','vf_player_pose.h'):
        copy_changed(source/'game_shared'/n,engine_source/'common'/n)
    snapshots={}
    for n in ('vf_player_pose.inc','vf_wallrun_pose.inc','gl_vf_headgear.inc','sv_vf_pose.inc'):
        copy_changed(ROOT/'engine'/n,engine_source/'common'/n);snapshots['vector-fields/engine/'+n]=engine_source/'common'/n
    for n in ('gl_vf.inc','gl_vf_perf.inc','gl_vf_headgear.inc','vf_player_pose.inc','vf_wallrun_pose.inc'):
        copy_changed(ROOT/'engine'/n,engine_source/'ref/gl'/n);snapshots['vector-fields/engine/'+n]=engine_source/'ref/gl'/n
    sdl=PROJECT/'devtools/SDL2-sdk/SDL2-2.32.10'
    command([sys.executable,'waf','configure',f'--sdl2={sdl}','-T','release','--enable-tests','--enable-dedicated','--enable-bundled-deps',
        '--msvc_version=msvc 17.4','--msvc_targets=x86','--disable-werror'],engine_source,OUT/'engine-configure.log')
    command([sys.executable,'waf','build','-j','8','--notests'],engine_source,OUT/'engine-build.log')
    command([sys.executable,'waf','build','-j','1','--alltests'],engine_source,OUT/'engine-tests.log')
    engine=OUT/'engine';command([sys.executable,'waf','install',f'--destdir={engine}'],engine_source,OUT/'engine-install.log')
    copy_changed(sdl/'lib/x86/SDL2.dll',engine/'SDL2.dll')
    hashes={str(p.relative_to(source)):digest(p)for p in source.rglob('*')if p.is_file()}
    hashes.update({n:digest(p)for n,p in snapshots.items()})
    (OUT/'source-hashes.json').write_text(json.dumps(hashes,indent=2));(OUT/'diagnostic-inputs.json').write_text('{}')
    metadata=json.loads((PROJECT/'runtime/vector-engine/vector-engine-build.json').read_text(encoding='utf-8-sig'))
    metadata.update(wall_jump_version=1,walking_gait_version=1)
    for key,n in [('player_pose_sha256','vf_player_pose.inc'),('player_collision_sha256','sv_vf_pose.inc'),('renderer_sha256','gl_vf.inc')]:metadata[key]=digest(snapshots['vector-fields/engine/'+n]).upper()
    metadata['binaries']={n:digest(engine/n).upper()for n in ('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')}
    (engine/'vector-engine-build.json').write_text(json.dumps(metadata,indent=2))
    print('PASS private engine: current player-state gait and engine tests',flush=True)

def build():
    import sys
    generation=uuid.uuid4().hex[:10]
    source=OUT/('source-'+generation);source.mkdir(parents=True,exist_ok=True)
    for folder in ('dlls','cl_dll','common','engine','pm_shared','game_shared','public','external','lib','utils/vgui','utils/common','projects/vs2019'):
        shutil.copytree(PROJECT/folder,source/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__','*.obj','*.pdb','*.log','*.ilk','*.exp'))
    hashes={str(p.relative_to(source)):digest(p)for p in source.rglob('*')if p.is_file()}
    vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    vs=Path(subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip())
    for name,project in [('server','hldll'),('client','hl_cdll')]:
        command([str(vs/'MSBuild/Current/Bin/MSBuild.exe'),str(source/f'projects/vs2019/{project}.vcxproj'),'/t:Build','/m','/nologo','/v:quiet','/clp:ErrorsOnly',
            '/p:Configuration=Release','/p:Platform=Win32','/p:PlatformToolset=v143','/p:WindowsTargetPlatformVersion=10.0.22000.0',
            '/p:PostBuildEventUseInBuild=false',f'/p:OutDir={OUT/name}/',f'/p:IntDir={OUT/("snapshot-obj-"+name)}/'],source,OUT/(name+'.log'))
        print('PASS snapshot',name,flush=True)
    engine_source=OUT/('engine-source-'+generation)
    shutil.copytree(PROJECT/'runtime/engine-source',engine_source,dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('.git','build','.builds','.lock-*','__pycache__','*.log'))
    for name in ('vf_engine_api.h','vf_assembly_policy.h','vf_traversal.h','vf_wallrun.h','vf_headgear.h','vf_player_pose.h'):
        shutil.copy2(source/'game_shared'/name,engine_source/'common'/name)
    for name in ('vf_player_pose.inc','vf_wallrun_pose.inc','gl_vf_headgear.inc','sv_vf_pose.inc'):
        shutil.copy2(ROOT/'engine'/name,engine_source/'common'/name)
    for name in ('gl_vf.inc','gl_vf_perf.inc','gl_vf_headgear.inc','vf_player_pose.inc','vf_wallrun_pose.inc'):
        shutil.copy2(ROOT/'engine'/name,engine_source/'ref/gl'/name)
    snapshots={n:engine_source/('ref/gl'if n in ('gl_vf.inc','gl_vf_perf.inc')else'common')/n
               for n in ('vf_player_pose.inc','vf_wallrun_pose.inc','gl_vf_headgear.inc','sv_vf_pose.inc','gl_vf.inc','gl_vf_perf.inc')}
    hashes.update({'vector-fields/engine/'+n:digest(p)for n,p in snapshots.items()})
    sdl=PROJECT/'devtools/SDL2-sdk/SDL2-2.32.10'
    command([sys.executable,'waf','configure',f'--sdl2={sdl}','-T','release','--enable-tests','--enable-dedicated','--enable-bundled-deps',
        '--msvc_version=msvc 17.4','--msvc_targets=x86','--disable-werror'],engine_source,OUT/'engine-configure.log')
    command([sys.executable,'waf','build','-j','8','--notests'],engine_source,OUT/'engine-build.log')
    command([sys.executable,'waf','build','-j','1','--alltests'],engine_source,OUT/'engine-tests.log')
    engine=OUT/'engine';command([sys.executable,'waf','install',f'--destdir={engine}'],engine_source,OUT/'engine-install.log')
    shutil.copy2(sdl/'lib/x86/SDL2.dll',engine/'SDL2.dll')
    metadata=json.loads((PROJECT/'runtime/vector-engine/vector-engine-build.json').read_text(encoding='utf-8-sig'))
    metadata['wall_jump_version']=1
    for key,name in [('player_pose_sha256','vf_player_pose.inc'),('player_collision_sha256','sv_vf_pose.inc'),('renderer_sha256','gl_vf.inc')]:metadata[key]=digest(snapshots[name]).upper()
    metadata['binaries']={n:digest(engine/n).upper()for n in ('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')}
    (engine/'vector-engine-build.json').write_text(json.dumps(metadata,indent=2))
    (OUT/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
    print('PASS isolated wall-jump engine and engine tests',flush=True)

if __name__=='__main__':build()
