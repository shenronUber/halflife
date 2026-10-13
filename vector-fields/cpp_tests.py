"""Compile and run policy tests from current sources, never cached executables."""
import json,os,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
OUT=ROOT/'build/policy-tests'
TESTS={
 'modular':(['tests/modular_layout_test.cpp'],[]),
 'tile_rooms':(['tests/tile_rooms_policy_test.cpp'],[]),
 'backend':(['tests/backend_policy_test.cpp'],[]),
 'voice_filter':(['tests/voice_filter_policy_test.cpp'],[]),
 'headgear':(['tests/headgear_policy_test.cpp','../game_shared/vf_loadout.cpp','../game_shared/vf_appearance.cpp'],['data/equipment.txt','data/r01_styles.txt']),
 'loadout':(['tests/loadout_test.cpp','../game_shared/vf_loadout.cpp','../game_shared/vf_appearance.cpp'],['data/equipment.txt','generated/visual_skins/skins.txt','generated/skins/arsenal.txt']),
 'architecture':(['tests/architecture_test.cpp','../game_shared/vf_loadout.cpp','../game_shared/vf_appearance.cpp'],['data/equipment.txt','data/r01_styles.txt','generated/visual_skins/skins.txt']),
 **{name:([f'tests/{source}_test.cpp'],[]) for name,source in (
  ('effects','effects'),('voice','voice_policy'),('combat','combat_policy'),
  ('proc','proc_policy'),('fragments','fragment_finish_policy'),('inspect','weapon_inspect_policy'),('melee','weapon_melee_policy'),('player_pose','player_pose_policy'))},
 'traversal':(['tests/traversal_movement_test.c','../pm_shared/pm_shared.c','../pm_shared/pm_math.c','../pm_shared/pm_debug.c'],[]),
 'wallrun':(['tests/wallrun_movement_test.c','../pm_shared/pm_shared.c','../pm_shared/pm_math.c','../pm_shared/pm_debug.c'],[]),
}

def run():
 vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
 install=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
 if not install:raise RuntimeError('Visual Studio C++ build tools are required for policy tests.')
 vcvars=Path(install)/'VC/Auxiliary/Build/vcvarsall.bat'
 results=[]
 for name,(sources,args) in TESTS.items():
  folder=OUT/name;folder.mkdir(parents=True,exist_ok=True);exe=folder/(name+'.exe')
  flags='/MT /O2 /W3 /D_CRT_SECURE_NO_WARNINGS'
  if name in ('traversal','wallrun'):flags+=' /Icommon /Iengine /Ipm_shared /Idlls /Ipublic'
  else:flags+=' /EHsc'
  # Paths are repository/toolchain paths, not shell fragments from user input.
  command='cl.exe /nologo '+flags+' '+ ' '.join('"'+str(ROOT/s)+'"' for s in sources)+f' /Fo"{folder.as_posix()}/" /Fe"{exe}"'
  script=folder/'compile.cmd'
  script.write_text(f'@echo off\ncall "{vcvars}" x86 >nul\nif errorlevel 1 exit /b 1\n{command}\nexit /b %errorlevel%\n',encoding='utf-8')
  with (folder/'compile.log').open('w') as log:
   built=subprocess.run([os.environ['ComSpec'],'/d','/c',str(script)],cwd=PROJECT,stdout=log,stderr=subprocess.STDOUT)
  if built.returncode:raise RuntimeError(f'{name} compilation failed: {folder / "compile.log"}')
  result=subprocess.run([str(exe)]+[str(ROOT/a) for a in args],cwd=PROJECT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (folder/'result.log').write_text(result.stdout,encoding='utf-8')
  print(f'[{name}] {result.stdout.strip()}',flush=True)
  results.append(dict(test=name,passed=result.returncode==0))
  if result.returncode:break
 (OUT/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 return 0 if len(results)==len(TESTS) and all(r['passed']for r in results) else 1

if __name__=='__main__':raise SystemExit(run())
