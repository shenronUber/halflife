"""Freeze the installed integrated binaries and new authored strike models for QA."""
import json,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest,sources
from release import check_native_interface

OUT=ROOT/'build/barrel-strike';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'

def prepare():
    inputs=sources();compiled=ROOT/'build/integration-audit/candidate'
    # These are the installed, previously audited binaries. Animation-only
    # authoring must not accidentally restore the older standalone melee DLLs.
    for relative,expected in inputs.items():
        assert digest(compiled/'source'/relative)==expected,('SDK changed since integrated build',relative)
    for relative,source in [('client/client.dll',LIVE/'vf_visual/cl_dlls/client.dll'),('server/hl.dll',LIVE/'vf_visual/dlls/hl.dll')]:
        assert digest(source)==digest(compiled/relative),('Installed binary changed',relative)
        target=CANDIDATE/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    manifest=json.loads((ROOT/'generated/weapon-melee/manifest.json').read_text())
    assert all(digest(path)==sha for path,sha in manifest['inputs'].items()),'Authoring inputs changed'
    for folder in ['models','maps','vf']:
        shutil.copytree(LIVE/'vf_visual'/folder,CANDIDATE/folder,dirs_exist_ok=True)
    shutil.copytree(compiled/'generated',CANDIDATE/'generated',dirs_exist_ok=True)
    shutil.copy2(compiled/'assets.json',CANDIDATE/'assets.json')
    shutil.copy2(LIVE/'vf_visual/delta.lst',CANDIDATE/'delta.lst')
    engine=json.loads((LIVE/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
    for name,sha in engine['binaries'].items():
        assert digest(LIVE/name).upper()==sha.upper(),('Installed engine changed',name)
    binary_files=sorted(p for p in LIVE.iterdir() if p.is_file() and p.suffix.lower() in ['.dll','.exe'])
    for source in binary_files:
        target=CANDIDATE/'engine'/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    shutil.copy2(LIVE/'vector-engine-build.json',CANDIDATE/'engine/vector-engine-build.json')
    for relative,expected in inputs.items():
        target=CANDIDATE/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(PROJECT/relative,target);assert digest(target)==expected
    for path in (ROOT/'generated/weapon-melee').glob('*.mdl'):
        shutil.copy2(path,CANDIDATE/'models/vf_melee'/path.name)
    (CANDIDATE/'source-hashes.json').write_text(json.dumps(inputs,indent=2)+'\n')
    check_native_interface(CANDIDATE/'engine',CANDIDATE/'client/client.dll')
    assert sources()==inputs,'Concurrent SDK change during snapshot'
    guard={str(p.relative_to(PROJECT)):digest(p) for p in binary_files+[
        LIVE/'vector-engine-build.json',LIVE/'vf_visual/cl_dlls/client.dll',LIVE/'vf_visual/dlls/hl.dll',LIVE/'vf_visual/delta.lst']}
    target=OUT/'binary-baseline.json'
    if target.exists():assert all(guard.get(n)==sha for n,sha in json.loads(target.read_text()).items()),'Installed bundle changed during animation review'
    target.write_text(json.dumps(guard,indent=2)+'\n')
    print('PASS frozen current main binaries and eleven revised strike assets',flush=True)

if __name__=='__main__':prepare()
