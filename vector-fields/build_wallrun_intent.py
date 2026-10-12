"""Compile current shared movement privately and pin the installed assets."""
import json,shutil
from build_weapon_melee import ROOT,PROJECT,digest,sources
import build_wall_jump_native as sdk
from native_workspace import shared_copy,private_copy
from release import check_native_interface
OUT=ROOT/'build/wallrun-intent';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'

def build():
    CANDIDATE.mkdir(parents=True,exist_ok=True);before=sources()
    files=[p for p in LIVE.iterdir()if p.is_file()and(p.suffix.lower()in('.dll','.exe')or p.name=='vector-engine-build.json')]
    files += [LIVE/'vf_visual'/p for p in ['dlls/hl.dll','cl_dlls/client.dll','delta.lst']]
    files += list((LIVE/'vf_visual/models').rglob('*.mdl'))+list((LIVE/'vf_visual/maps').glob('*.bsp'))
    files += [ROOT/'build/client/client.dll',ROOT/'build/server/hl.dll']
    guard={str(p.relative_to(PROJECT)):digest(p)for p in files}
    (OUT/'runtime-before.json').write_text(json.dumps(guard,indent=2))
    sdk.OUT=CANDIDATE;sdk.refresh_game(CANDIDATE/'source')
    assert sources()==before,'SDK sources changed during compilation'
    for folder in ['models','maps','vf']:shutil.copytree(LIVE/'vf_visual'/folder,CANDIDATE/folder,dirs_exist_ok=True,copy_function=shared_copy)
    for p in LIVE.iterdir():
        if p.is_file()and(p.suffix.lower()in('.dll','.exe')or p.name=='vector-engine-build.json'):
            target=CANDIDATE/'engine'/p.name;target.parent.mkdir(parents=True,exist_ok=True);private_copy(p,target)
    private_copy(LIVE/'vf_visual/delta.lst',CANDIDATE/'delta.lst')
    # Walking tests consume the same delivered FP/TP carriers, without using
    # an older asset build that would hide the latest fist articulation.
    assets=json.loads((ROOT/'build/animation-feedback/candidate/assets.json').read_text())
    for r in assets:
        r['candidate']=str(CANDIDATE/r['relative']);r['sha256']=digest(r['candidate'])
    (CANDIDATE/'assets.json').write_text(json.dumps(assets,indent=2))
    target=CANDIDATE/'generated/traversal-range/vf_traversal.bsp';target.parent.mkdir(parents=True,exist_ok=True)
    private_copy(CANDIDATE/'maps/vf_traversal.bsp',target)
    (CANDIDATE/'source-hashes.json').write_text(json.dumps(before,indent=2))
    check_native_interface(CANDIDATE/'engine',CANDIDATE/'client/client.dll')
    assert all(digest(PROJECT/p)==sha for p,sha in guard.items()),'Concurrent delivery to main detected'
    print('PASS current client/server with intentional wall-run entry; installed engine/models unchanged',flush=True)
if __name__=='__main__':build()
