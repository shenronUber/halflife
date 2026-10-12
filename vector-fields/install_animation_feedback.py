"""Guarded delivery of fist poses, dynamic rebounds and the native test bay."""
import datetime,json,os,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest,sources
from release import check_native_interface,verify_deployment
OUT=ROOT/'build/animation-feedback';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def install():
    proofs=[read(OUT/'geometry.json'),read(OUT/'native/melee/native.json'),read(OUT/'native/pose_strike/verification.json'),read(OUT/'native/walljump/native.json')]
    course=read(ROOT/'docs/videos/parcours-2026-10-12/capture.json');proofs.append(course)
    assert all(p['passed']for p in proofs)
    pose=proofs[2];assert len(pose['poses'])==64 and pose['boxes_compared']==1280
    assert sources()==read(CANDIDATE/'source-hashes.json')
    before=read(OUT/'runtime-before.json');assert all(digest(PROJECT/p)==sha for p,sha in before.items())
    for proof in proofs[:4]:
        for field,path in [('server_sha256','server/hl.dll'),('client_sha256','client/client.dll'),('engine_sha256','engine/xash.dll'),('renderer_sha256','engine/ref_gl.dll')]:
            if field in proof:assert proof[field]==digest(CANDIDATE/path),(field,'unreviewed binary')
    assert proofs[0]['assets']==proofs[1]['assets']==pose['melee_assets']
    wall=proofs[3]
    assert wall['binaries']=={name:digest(CANDIDATE/path)for name,path in [('client','client/client.dll'),('server','server/hl.dll')]}
    for name in ['xash.dll','ref_gl.dll']:assert wall['engine'][name]==digest(CANDIDATE/'engine'/name)
    reload=read(OUT/'native/reload/verification.json')
    assert reload['passed']and reload['maximum_step_degrees']<1
    assert reload['server_sha256']==digest(CANDIDATE/'server/hl.dll')and reload['renderer_sha256']==digest(CANDIDATE/'engine/ref_gl.dll')
    assert all(digest(p)==sha for p,sha in course['sources'].items())
    check_native_interface(CANDIDATE/'engine',CANDIDATE/'client/client.dll')
    pairs=[]
    for part,name,folder in [('client','client.dll','cl_dlls'),('server','hl.dll','dlls')]:
        pairs +=[(CANDIDATE/part/name,LIVE/'vf_visual'/folder/name),(CANDIDATE/part/name,ROOT/'build'/part/name)]
    for p in (CANDIDATE/'engine').iterdir():
        if p.is_file()and(p.suffix.lower()in('.dll','.exe')or p.name=='vector-engine-build.json'):pairs.append((p,LIVE/p.name))
    for folder,pattern,generated in [('vf_melee','*.mdl','weapon-melee'),('vf_r01','r01_tp*.mdl','third-person')]:
        for p in (CANDIDATE/'models'/folder).glob(pattern):
            pairs +=[(p,LIVE/'vf_visual/models'/folder/p.name),(p,ROOT/'generated'/generated/p.name)]
    pairs.append((CANDIDATE/'maps/vf_traversal.bsp',LIVE/'vf_visual/maps/vf_traversal.bsp'))
    staged=[]
    for source,target in pairs:
        assert PROJECT.resolve()in target.resolve().parents
        old=digest(target);new=digest(source)
        if old==new:continue
        saved=OUT/'installation-backup'/target.relative_to(PROJECT);saved.parent.mkdir(parents=True,exist_ok=True)
        if saved.exists():assert digest(saved)==old
        else:shutil.copy2(target,saved)
        pending=target.with_name(target.name+'.feedback-next');shutil.copy2(source,pending);assert digest(pending)==new
        staged.append((target,pending,saved,old,new))
    replaced=[]
    try:
        assert all(digest(PROJECT/p)==sha for p,sha in before.items())
        for target,pending,saved,old,new in staged:
            assert digest(target)==old;os.replace(pending,target);replaced.append((target,saved));assert digest(target)==new
        delivery=verify_deployment(LIVE/'vf_visual')
    except Exception:
        for target,saved in reversed(replaced):
            pending=target.with_name(target.name+'.feedback-rollback');shutil.copy2(saved,pending);os.replace(pending,target)
        raise
    manifest_path=ROOT/'generated/weapon-melee/manifest.json';manifest=read(manifest_path)
    for record in manifest['models']:
        record['sha256']=digest(ROOT/'generated/weapon-melee'/record['file'])
        if record['file'].startswith('r01_tp'):record['revised_existing_sequences']=['vf_wall_jump','vf_wall_jump_turn']
    for p in manifest['inputs']:manifest['inputs'][p]=digest(p)
    manifest['gesture']='Right-handed barrel strike; closed left fist in forward fighting guard'
    manifest_path.write_text(json.dumps(manifest,indent=2))
    report=dict(passed=True,installed=True,date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        files={str(target.relative_to(PROJECT)):new for target,_,_,_,new in staged},delivery=delivery,
        poses=len(pose['poses']),hitboxes=pose['boxes_compared'],maximum_hitbox_corner_error_units=pose['maximum_corner_error_units'],
        changes=['Closed left fist with neutral wrist in FP and forward guard in TP','Early look-driven body rotation on both wall-jump commands','Leg push/tuck and early two-arm reach','One authoritative body yaw for rendering and collision','Library concept traversal bay and ordinary stairs'],
        reload_adjacent_frame_torso_degrees=reload['maximum_step_degrees'],
        video=str(ROOT/'docs/videos/parcours-2026-10-12'),backup=str(OUT/'installation-backup'))
    (OUT/'installed.json').write_text(json.dumps(report,indent=2));(ROOT/'docs/validation/animation-feedback-2026-10-12.json').write_text(json.dumps(report,indent=2))
    print('PASS installed reviewed fist/rebound/course:',len(staged),'files;',delivery,flush=True)
    return report

if __name__=='__main__':install()
