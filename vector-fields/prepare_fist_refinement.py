"""Pin current main without recompiling or reverting SDK/engine/traversal fixes."""
import json,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest,sources
from release import check_native_interface
from native_workspace import shared_copy
OUT=ROOT/'build/fist-refinement';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'

def prepare():
    CANDIDATE.mkdir(parents=True,exist_ok=True);inputs=sources()
    for p in LIVE.iterdir():
        if p.is_file()and(p.suffix.lower()in('.exe','.dll')or p.name=='vector-engine-build.json'):
            target=CANDIDATE/'engine'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
    for relative,target in [('cl_dlls/client.dll','client/client.dll'),('dlls/hl.dll','server/hl.dll'),('delta.lst','delta.lst')]:
        source=LIVE/'vf_visual'/relative;dest=CANDIDATE/target;dest.parent.mkdir(exist_ok=True);shutil.copy2(source,dest)
    for folder in ['models','maps','vf']:shutil.copytree(LIVE/'vf_visual'/folder,CANDIDATE/folder,dirs_exist_ok=True,copy_function=shared_copy)
    compiled=ROOT/'build/animation-feedback/candidate/source'
    for relative,expected in inputs.items():
        assert digest(compiled/relative)==expected,('Installed SDK snapshot no longer matches source',relative)
        target=CANDIDATE/'source'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(compiled/relative,target)
    (CANDIDATE/'source-hashes.json').write_text(json.dumps(inputs,indent=2))
    files=[p for p in LIVE.iterdir()if p.is_file()and(p.suffix.lower()in('.exe','.dll')or p.name=='vector-engine-build.json')]
    files +=[LIVE/'vf_visual'/p for p in ['cl_dlls/client.dll','dlls/hl.dll','delta.lst']]
    files +=list((LIVE/'vf_visual/models').rglob('*.mdl'))
    guard={str(p.relative_to(PROJECT)):digest(p)for p in files};(OUT/'runtime-before.json').write_text(json.dumps(guard,indent=2))
    manifest=json.loads((OUT/'assets/manifest.json').read_text())
    assert all(digest(p)==sha for p,sha in manifest['inputs'].items())
    for path in (OUT/'assets').glob('*.mdl'):shutil.copy2(path,CANDIDATE/'models/vf_melee'/path.name)
    from thumb_articulation import upgrade
    articulated=[]
    for folder,pattern in [('vf_r01','r01_tp*.mdl'),('vf_skins','*.mdl')]:
        for path in (CANDIDATE/'models'/folder).glob(pattern):
            if upgrade(path):articulated.append(dict(relative=str(path.relative_to(CANDIDATE)),sha256=digest(path)))
    (OUT/'articulated-models.json').write_text(json.dumps(articulated,indent=2))
    check_native_interface(CANDIDATE/'engine',CANDIDATE/'client/client.dll')
    assert sources()==inputs
    print('PASS isolated fist candidate: current main engine/SDK, new models only',flush=True)

if __name__=='__main__':prepare()
