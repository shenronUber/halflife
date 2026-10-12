"""Build current client/server privately; reject source changes during compilation."""
import hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;OUT=ROOT/'build/weapon-melee'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def sources():
    paths=[p for folder in ('cl_dll','dlls','game_shared','common','engine','public','pm_shared') for p in (PROJECT/folder).rglob('*')
           if p.is_file() and p.suffix.lower() in ('.c','.cpp','.h','.inc')]
    paths += [PROJECT/'projects/vs2019'/name for name in ('hl_cdll.vcxproj','hldll.vcxproj')]
    return {str(p.relative_to(PROJECT)):digest(p) for p in sorted(paths)}
def build():
    assets=json.loads((ROOT/'generated/weapon-melee/manifest.json').read_text())
    assert all(digest(path)==sha for path,sha in assets['inputs'].items()),'Refresh melee assets against installed models'
    OUT.mkdir(parents=True,exist_ok=True)
    vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    install=Path(subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip())
    msbuild=install/'MSBuild/Current/Bin/MSBuild.exe';before=sources();started=time.time()
    for part,project in (('client','hl_cdll'),('server','hldll')):
        args=[str(msbuild),str(PROJECT/'projects/vs2019'/(project+'.vcxproj')),'/t:Build','/m','/nologo','/v:quiet','/clp:ErrorsOnly',
            '/p:Configuration=Release','/p:Platform=Win32','/p:PlatformToolset=v143','/p:WindowsTargetPlatformVersion=10.0.22000.0',
            '/p:PostBuildEventUseInBuild=false','/p:OutDir='+str(OUT/part)+'/', '/p:IntDir='+str(OUT/('obj-'+part))+'/']
        with (OUT/(part+'-build.log')).open('w') as log:result=subprocess.run(args,cwd=PROJECT,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError((OUT/(part+'-build.log')).read_text(errors='replace')[-12000:])
        print('PASS private melee '+part,flush=True)
    after=sources()
    if before!=after:
        changed=[k for k in before.keys()|after.keys() if before.get(k)!=after.get(k)]
        raise RuntimeError('Sources changed during build; recompile current changes: '+', '.join(changed))
    report=dict(sources=after,started=started,client_sha256=digest(OUT/'client/client.dll'),server_sha256=digest(OUT/'server/hl.dll'),
        assets={p.name:digest(p) for p in (ROOT/'generated/weapon-melee').glob('*.mdl')},elapsed=time.time()-started)
    (OUT/'build.json').write_text(json.dumps(report,indent=2));print('PASS guarded client/server build',flush=True)
    test=OUT/'policy';test.mkdir(exist_ok=True);exe=test/'melee.exe';script=test/'compile.cmd'
    script.write_text('@echo off\ncall "'+str(install/'VC/Auxiliary/Build/vcvarsall.bat')+'" x86 >nul\n'
        'if errorlevel 1 exit /b 1\ncl.exe /nologo /EHsc /MT /O2 /W3 "'+str(ROOT/'tests/weapon_melee_policy_test.cpp')+
        '" /Fo"'+str(test/'melee.obj')+'" /Fe"'+str(exe)+'"\nexit /b %errorlevel%\n')
    with (test/'compile.log').open('w') as log:result=subprocess.run([os.environ['ComSpec'],'/d','/c',str(script)],cwd=PROJECT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,(test/'compile.log').read_text(errors='replace')
    result=subprocess.run([str(exe)],capture_output=True,text=True);(test/'result.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
    print(result.stdout.strip(),flush=True)
if __name__=='__main__':build()
