"""Compile the pose-history fix privately against current main resources."""
import json,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest,sources
import build_wall_jump_native as builder
OUT=ROOT/'build/crouch-reload';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'

def build():
    CANDIDATE.mkdir(parents=True,exist_ok=True);before=sources();builder.OUT=CANDIDATE
    builder.refresh_game(CANDIDATE/'source')
    assert sources()==before,'SDK changed during compilation'
    for name in ['models','maps','vf']:
        shutil.copytree(LIVE/'vf_visual'/name,CANDIDATE/name,dirs_exist_ok=True)
    previous=ROOT/'build/barrel-strike/candidate'
    shutil.copytree(previous/'generated',CANDIDATE/'generated',dirs_exist_ok=True)
    shutil.copy2(previous/'assets.json',CANDIDATE/'assets.json')
    shutil.copy2(LIVE/'vf_visual/delta.lst',CANDIDATE/'delta.lst')
    binaries=[p for p in LIVE.iterdir()if p.is_file()and(p.suffix.lower()in ['.exe','.dll']or p.name=='vector-engine-build.json')]
    for path in binaries:
        target=CANDIDATE/'engine'/path.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    (CANDIDATE/'source-hashes.json').write_text(json.dumps(before,indent=2)+'\n')
    guard={str(p.relative_to(PROJECT)):digest(p)for p in binaries+[LIVE/'vf_visual/delta.lst']+list((LIVE/'vf_visual/models/vf_r01').glob('*.mdl'))+list((LIVE/'vf_visual/models/vf_melee').glob('*.mdl'))}
    (OUT/'resource-baseline.json').write_text(json.dumps(guard,indent=2)+'\n')
    print('PASS private reload-transition DLLs; exact installed engine and models',flush=True)

if __name__=='__main__':build()
