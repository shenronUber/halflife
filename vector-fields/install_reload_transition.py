"""Publish the reviewed SDK pose-history fix without changing engine or assets."""
import datetime,json,os,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest,sources
from release import check_native_interface,verify_deployment
OUT=ROOT/'build/crouch-reload';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def install():
    before=read(OUT/'before/verification.json');after=read(OUT/'after/verification.json')
    pose=read(OUT/'native/pose_strike/verification.json');policy=read(OUT/'policy/results.json')
    assert after['passed']and not after['baseline']and len(after['cases'])==6 and after['frames']==96
    assert before['maximum_step_degrees']>20 and after['maximum_step_degrees']<1.5
    assert digest(OUT/'after/native.log')==after['raw_log_sha256']
    assert pose['passed']and len(pose['poses'])==61 and pose['boxes_compared']==1220
    assert all(p['passed']for p in policy)
    for proof in [after,pose]:
        for field,relative in [('client_sha256','client/client.dll'),('server_sha256','server/hl.dll'),('renderer_sha256','engine/ref_gl.dll'),('engine_sha256','engine/xash.dll')]:
            if field in proof:assert proof[field]==digest(CANDIDATE/relative)
    assert sources()==read(CANDIDATE/'source-hashes.json'),'SDK source drift'
    resource_guard=read(OUT/'resource-baseline.json')
    assert all(digest(PROJECT/name)==sha for name,sha in resource_guard.items()),'Main resources changed during review'
    check_native_interface(LIVE,CANDIDATE/'client/client.dll')
    baseline=read(OUT/'runtime-before.json');staged=[]
    for part,name,folder in [('client','client.dll','cl_dlls'),('server','hl.dll','dlls')]:
        source=CANDIDATE/part/name
        for target in [ROOT/'build'/part/name,LIVE/'vf_visual'/folder/name]:
            relative=str(target.relative_to(PROJECT)).replace('\\','/')
            assert digest(target)==baseline[relative],('Concurrent SDK delivery',target)
            with target.open('r+b'):pass
            saved=OUT/'installation-backup'/target.relative_to(PROJECT);saved.parent.mkdir(parents=True,exist_ok=True)
            if saved.exists():assert digest(saved)==baseline[relative]
            else:shutil.copy2(target,saved)
            pending=target.with_name(target.name+'.reload-next');shutil.copy2(source,pending);assert digest(pending)==digest(source)
            staged.append((target,pending,saved,baseline[relative],digest(source)))
    replaced=[]
    try:
        assert all(digest(PROJECT/name)==sha for name,sha in resource_guard.items())
        for target,pending,saved,old,new in staged:
            assert digest(target)==old,('Concurrent write during publication',target)
            os.replace(pending,target);replaced.append((target,saved));assert digest(target)==new
        delivery=verify_deployment(LIVE/'vf_visual')
    except Exception:
        for target,saved in reversed(replaced):
            pending=target.with_name(target.name+'.reload-rollback');shutil.copy2(saved,pending);os.replace(pending,target)
        raise
    report=dict(passed=True,installed=True,date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        cause='The transition cached raw aim-blend zero instead of the pitch blend actually evaluated above the gait.',
        fix='Cache the canonical pitch blend for the previous animation, preserving the existing shared Studio evaluator.',
        maximum_adjacent_frame_torso_degrees_before=before['maximum_step_degrees'],maximum_adjacent_frame_torso_degrees_after=after['maximum_step_degrees'],
        six_configurations=[c['name']for c in after['cases']],native_frames_before=96,native_frames_after=96,
        poses=61,boxes=1220,maximum_hitbox_corner_error_units=pose['maximum_corner_error_units'],
        backup=str(OUT/'installation-backup'),files={str(t.relative_to(PROJECT)):new for t,_,_,_,new in staged},
        delivery=delivery,evidence=['build/crouch-reload/before/verification.json','build/crouch-reload/after/verification.json','build/crouch-reload/native/pose_strike/verification.json','build/crouch-reload/policy/results.json'])
    (OUT/'installed.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'docs/validation/reload-transition-2026-10-12.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS reviewed reload transition installed:',len(staged),'SDK files;',delivery,flush=True)
    return report
if __name__=='__main__':install()
