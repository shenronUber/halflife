"""Install only the reviewed strike carriers, with a rollback and main-build guards."""
import datetime,json,os,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest,sources
from release import check_native_interface,verify_deployment

OUT=ROOT/'build/barrel-strike';CANDIDATE=OUT/'candidate';PROOFS=OUT/'native'
LIVE=PROJECT/'runtime/vector-engine'
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def install():
    geometry=read(OUT/'geometry.json');native=read(PROOFS/'melee/native.json')
    network=read(PROOFS/'melee_network/network.json');pose=read(PROOFS/'pose_strike/verification.json')
    transitions=read(PROOFS/'melee_integration/verification.json');status=read(PROOFS/'gesture_status/verification.json')
    assert all(p['passed'] for p in [geometry,native,network,pose,transitions,status])
    assert len(geometry['rigs'])==12 and len(native['configurations'])==6
    assert len(pose['poses'])==61 and pose['boxes_compared']==1220
    required={f'melee_{mount}_{stance}_{phase}' for mount in ['bottom','side','top'] for stance in ['stand','crouch'] for phase in ['raise','contact','follow']}
    assert required<={p['name']for p in pose['poses']}
    assets={p.name:digest(p)for p in(CANDIDATE/'models/vf_melee').glob('*.mdl')}
    assert len(assets)==11 and assets==geometry['assets']==native['assets']==pose['melee_assets']
    assert assets=={p.name:digest(p)for p in(ROOT/'generated/weapon-melee').glob('*.mdl')}
    for proof in [native,network,pose,transitions,status]:
        for field,relative in [('client_sha256','client/client.dll'),('server_sha256','server/hl.dll'),('renderer_sha256','engine/ref_gl.dll'),('engine_sha256','engine/xash.dll')]:
            if field in proof:assert proof[field]==digest(CANDIDATE/relative),(field,'untested binary')
    manifest=read(ROOT/'generated/weapon-melee/manifest.json')
    assert all(digest(path)==sha for path,sha in manifest['inputs'].items()),'Authoring inputs changed'
    assert all(digest(path)==sha for path,sha in geometry['magazine_inputs'].items()),'Magazine shape changed'
    assert len(manifest['models'])==9 and all(m['old_animation_error']<.001 and m['compiled_error']<.02 for m in manifest['models'])
    assert sources()==read(CANDIDATE/'source-hashes.json'),'SDK changed during animation review'
    baseline=read(OUT/'binary-baseline.json')
    assert all(digest(PROJECT/path)==sha for path,sha in baseline.items()),'Main engine or DLLs changed during review'
    check_native_interface(LIVE,LIVE/'vf_visual/cl_dlls/client.dll')
    before=read(OUT/'runtime-before.json');staged=[]
    for name,sha in assets.items():
        target=LIVE/'vf_visual/models/vf_melee'/name;source=CANDIDATE/'models/vf_melee'/name
        assert digest(target)==before[str(target.relative_to(PROJECT))],('Concurrent model delivery',name)
        if digest(target)==sha:continue
        saved=OUT/'installation-backup'/name;saved.parent.mkdir(parents=True,exist_ok=True)
        if saved.exists():assert digest(saved)==digest(target)
        else:shutil.copy2(target,saved)
        pending=target.with_name(target.name+'.barrel-next');shutil.copy2(source,pending);assert digest(pending)==sha
        staged.append((target,pending,saved,digest(target),sha))
    replaced=[]
    try:
        assert all(digest(PROJECT/path)==sha for path,sha in baseline.items())
        for target,pending,saved,old,new in staged:
            assert digest(target)==old,('Concurrent write during installation',target)
            os.replace(pending,target);replaced.append((target,saved));assert digest(target)==new
        assert all(digest(LIVE/'vf_visual/models/vf_melee'/name)==sha for name,sha in assets.items())
        delivery=verify_deployment(LIVE/'vf_visual')
    except Exception:
        for target,saved in reversed(replaced):
            pending=target.with_name(target.name+'.barrel-rollback');shutil.copy2(saved,pending);os.replace(pending,target)
        raise
    report=dict(passed=True,installed=True,date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        gesture=manifest['gesture'],binding='V',duration=manifest['duration'],impact=manifest['impact'],
        damage=35,range=40,models_changed=len(staged),assets=assets,delivery=delivery,
        main_binaries=baseline,backup=str(OUT/'installation-backup'),
        blender_file=manifest['blend_file'],source_reference='Photo 1.jpg supplied by user, six-stage overhead strike',
        validation=dict(geometry_tracks=12,first_person_configurations=6,native_captures=len(native['captures']),
            third_person=['standing','crouching'],remote_frames=network['remote_frames'],poses=61,boxes=1220,
            maximum_hitbox_corner_error_units=pose['maximum_corner_error_units'],
            body_and_cancellations=transitions,status_shells=status),
        preserved_sequences={m['file']:m['old_sequences_preserved']for m in manifest['models']},
        evidence=[str(p.relative_to(ROOT))for p in [OUT/'geometry.json',PROOFS/'melee/native.json',PROOFS/'melee_network/network.json',
            PROOFS/'pose_strike/verification.json',PROOFS/'melee_integration/verification.json',PROOFS/'gesture_status/verification.json']])
    (OUT/'installed.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'docs/validation/barrel-strike-2026-10-12.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS barrel strike installed in main:',len(staged),'carriers;',delivery,flush=True)
    return report

if __name__=='__main__':install()
