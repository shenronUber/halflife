"""Compile only the client into a private directory, preserving concurrent work."""
import hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
OUT=ROOT/'build/weapon-inspect'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def sources():
    folders=('cl_dll','game_shared','common','engine','public','pm_shared')
    files=[p for folder in folders for p in (PROJECT/folder).rglob('*')
           if p.is_file() and p.suffix.lower() in ('.cpp','.c','.h','.inc')]
    files.append(PROJECT/'projects/vs2019/hl_cdll.vcxproj')
    files.extend(ROOT/name for name in ('build_weapon_inspect_rigs.py','build_weapon_inspect_hands.py','build_reference_platforms.py','animation_assets.py','studio_assets.py'))
    files.extend((PROJECT/'runtime/vector-engine/vf_visual/models/vf_r01').glob('r01_rig*.mdl'))
    files.extend((PROJECT/'runtime/vector-engine/vf_visual/models/vf_r01')/('r01_fp_'+kind+'.mdl') for kind in ('gloves','sleeves'))
    return {str(p.relative_to(PROJECT)):digest(p) for p in sorted(files)}

def build():
    from build_weapon_inspect_rigs import build as build_rigs
    from build_weapon_inspect_hands import build as build_hands
    build_rigs()
    build_hands()
    OUT.mkdir(parents=True,exist_ok=True)
    vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    install=Path(subprocess.check_output([str(vswhere),'-latest','-products','*','-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip())
    msbuild=install/'MSBuild/Current/Bin/MSBuild.exe'
    before=sources();start=time.time()
    args=[str(msbuild),str(PROJECT/'projects/vs2019/hl_cdll.vcxproj'),'/t:Build','/m','/nologo','/v:quiet','/clp:ErrorsOnly',
          '/p:Configuration=Release','/p:Platform=Win32','/p:PlatformToolset=v143',
          '/p:WindowsTargetPlatformVersion=10.0.22000.0','/p:PostBuildEventUseInBuild=false',
          '/p:OutDir='+str(OUT/'client')+'/', '/p:IntDir='+str(OUT/'obj-client')+'/']
    with (OUT/'client-build.log').open('w') as log:
        p=subprocess.run(args,cwd=PROJECT,stdout=log,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError((OUT/'client-build.log').read_text(errors='replace'))
    after=sources()
    if before!=after:
        changed=[p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)]
        (OUT/'concurrent-changes.json').write_text(json.dumps(changed,indent=2))
        raise RuntimeError('Sources changed during compilation; rebuild the private candidate: '+', '.join(changed))
    report=dict(client_sha256=digest(OUT/'client/client.dll'),sources=after,started=start,elapsed=time.time()-start)
    (OUT/'build.json').write_text(json.dumps(report,indent=2))
    print('PASS private inspection client',round(report['elapsed'],1),'seconds',flush=True)
    test=OUT/'policy';test.mkdir(exist_ok=True)
    script=test/'compile.cmd';exe=test/'inspection.exe'
    script.write_text('@echo off\ncall "'+str(install/'VC/Auxiliary/Build/vcvarsall.bat')+'" x86 >nul\n'
        'if errorlevel 1 exit /b 1\ncl.exe /nologo /EHsc /MT /O2 /W3 "'+str(ROOT/'tests/weapon_inspect_policy_test.cpp')+
        '" /Fo"'+str(test/'inspection.obj')+'" /Fe"'+str(exe)+'"\nexit /b %errorlevel%\n')
    with (test/'compile.log').open('w') as log:
        result=subprocess.run([os.environ['ComSpec'],'/d','/c',str(script)],cwd=PROJECT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,(test/'compile.log').read_text(errors='replace')
    result=subprocess.run([str(exe)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (test/'result.log').write_text(result.stdout)
    assert result.returncode==0,result.stdout
    print(result.stdout.strip(),flush=True)
    return install

if __name__=='__main__':build()
