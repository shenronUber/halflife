"""Publish only reviewed movement DLLs and the original slide cue.

Concurrent renderer, skin and animation publications are preserved. All old
files are checked immediately before replacement and retained for rollback.
"""
import json,os,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from release import check_native_interface,verify_deployment
from build_traversal_sounds import digest

def main():
    project=ROOT.parent;candidate=ROOT/'build/slide-feedback'
    engine=project/'runtime/vector-engine';mod=engine/'vf_visual'
    out=ROOT/'docs/validation/traversal/slide-feedback'
    tested=json.loads((out/'native.json').read_text());baseline=json.loads((candidate/'baseline.json').read_text())
    sources=json.loads((candidate/'build-sources.json').read_text())
    assert tested['passed'] and tested['bob_scale']==.1 and tested['dedicated_slide_feet_preserved']
    assert tested['sound_duration']==1.2 and tested['sliding_camera_samples']>60
    assert tested['renderer_sha256']==digest(engine/'ref_gl.dll'),'Renderer changed after native review'
    assert re.search(r'Traversal movement: \d+ checks, 0 failures',(candidate/'movement.log').read_text())
    for name,expected in sources.items():assert digest(project/name)==expected,('Compile input changed after review',name)
    for name,expected in baseline.items():assert digest(project/name)==expected,('Concurrent publication',name)
    assert digest(candidate/'client/client.dll')==tested['client_sha256']
    assert digest(candidate/'server/hl.dll')==tested['server_sha256']
    assert digest(ROOT/'generated/traversal-sfx/slide.wav')==tested['sound_sha256']
    updates=[(candidate/'client/client.dll',mod/'cl_dlls/client.dll'),
             (candidate/'client/client.dll',ROOT/'build/client/client.dll'),
             (candidate/'server/hl.dll',mod/'dlls/hl.dll'),
             (candidate/'server/hl.dll',ROOT/'build/server/hl.dll'),
             (ROOT/'generated/traversal-sfx/slide.wav',mod/'sound/vf_traversal/slide.wav'),
             (ROOT/'generated/traversal-sfx/manifest.json',mod/'vf/traversal-sfx-manifest.json')]
    before=candidate/'before';assert not before.exists(),'This reviewed deployment already has a rollback snapshot'
    changes=[]
    # Probe all DLLs first. A running installed game must never be interrupted
    # merely to replace its loaded binaries.
    for source,target in updates:
        if target.exists():
            with target.open('r+b'):pass
    for source,target in updates:
        target.parent.mkdir(parents=True,exist_ok=True)
        previous=digest(target) if target.exists() else None
        old=before/target.relative_to(project)
        if previous:
            old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,old)
        pending=target.with_name(target.name+'.slide-feedback');shutil.copy2(source,pending)
        changes.append((target,pending,old,previous,digest(source)))
    replaced=[]
    try:
        for target,pending,old,previous,expected in changes:
            assert (digest(target) if target.exists() else None)==previous,('Concurrent publication',target)
            os.replace(pending,target);replaced.append((target,old,previous,expected));assert digest(target)==expected
        check_native_interface(engine,mod/'cl_dlls/client.dll');deployment=verify_deployment(mod)
        for name,expected in baseline.items():
            if not any(project/name==target for target,_,_,_,_ in changes):
                assert digest(project/name)==expected,('Unrelated asset changed',name)
    except Exception:
        for target,old,previous,expected in reversed(replaced):
            # Do not overwrite another publisher if it replaced our update.
            if digest(target)==expected:
                if previous:shutil.copy2(old,target)
                else:target.unlink()
        raise
    finally:
        for _,pending,_,_,_ in changes:
            if pending.exists():pending.unlink()
    result=dict(passed=True,changed=[str(target.relative_to(project)) for target,_,_,_,_ in changes],
                deployment=deployment,renderer_preserved=True,animation_assets_modified=0,
                client_sha256=tested['client_sha256'],server_sha256=tested['server_sha256'],
                sound_sha256=tested['sound_sha256'],sound_duration=tested['sound_duration'],bob_scale=.1)
    (out/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS installed slide feedback:',json.dumps(result))

if __name__=='__main__':main()
