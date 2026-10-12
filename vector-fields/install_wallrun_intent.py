"""Guarded SDK-only delivery; preserve the current renderer and every asset."""
import datetime,json,os,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest,sources
from release import check_native_interface,verify_deployment
OUT=ROOT/'build/wallrun-intent';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def install():
    wall=read(OUT/'native/wallrun/native.json');network=read(OUT/'native/wallrun_network/network.json')
    pose=read(OUT/'native/pose_strike/verification.json');walk=read(OUT/'native/walk/native.json')
    assert all(p['passed']for p in [wall,network,pose,walk])
    assert len(pose['poses'])==70 and pose['boxes_compared']==1400
    assert all(p['passed']for p in read(ROOT/'build/policy-tests/results.json'))
    assert '0 wall-run failures'in(ROOT/'build/policy-tests/wallrun/result.log').read_text()
    assert all(p['passed']for p in read(OUT/'policy/results.json'))
    assert sources()==read(CANDIDATE/'source-hashes.json')
    for proof in [wall,network,pose]:
        for field,path in [('server_sha256','server/hl.dll'),('client_sha256','client/client.dll'),('engine_sha256','engine/xash.dll'),('renderer_sha256','engine/ref_gl.dll')]:
            if field in proof:assert proof[field]==digest(CANDIDATE/path),(field,'binary changed after native verification')
    assert walk['binaries']=={n:digest(CANDIDATE/p)for n,p in [('server','server/hl.dll'),('client','client/client.dll')]}
    assert walk['renderer_sha256']==digest(CANDIDATE/'engine/ref_gl.dll')
    assert walk['delta_sha256']==digest(CANDIDATE/'delta.lst')
    assert pose['melee_assets']=={p.name:digest(p)for p in(CANDIDATE/'models/vf_melee').glob('*.mdl')}
    before=read(OUT/'runtime-before.json');assert all(digest(PROJECT/p)==sha for p,sha in before.items())
    staged=[]
    for part,name,folder in [('client','client.dll','cl_dlls'),('server','hl.dll','dlls')]:
        source=CANDIDATE/part/name
        for target in [LIVE/'vf_visual'/folder/name,ROOT/'build'/part/name]:
            assert PROJECT.resolve()in target.resolve().parents
            old=digest(target);new=digest(source)
            if old==new:continue
            saved=OUT/'installation-backup'/new[:12]/target.relative_to(PROJECT);saved.parent.mkdir(parents=True,exist_ok=True)
            if saved.exists():assert digest(saved)==old
            else:shutil.copy2(target,saved)
            pending=target.with_name(target.name+'.wallrun-intent-next');shutil.copy2(source,pending);assert digest(pending)==new
            staged.append((target,pending,saved,old,new))
    replaced=[]
    try:
        assert all(digest(PROJECT/p)==sha for p,sha in before.items())
        for target,pending,saved,old,new in staged:
            assert digest(target)==old;os.replace(pending,target);replaced.append((target,saved));assert digest(target)==new
        delivery=verify_deployment(LIVE/'vf_visual')
        updated={str(target.relative_to(PROJECT))for target,_,_,_,_ in staged}
        assert all(digest(PROJECT/p)==sha for p,sha in before.items()if p not in updated)
        check_native_interface(LIVE,LIVE/'vf_visual/cl_dlls/client.dll')
    except Exception:
        for target,saved in reversed(replaced):
            pending=target.with_name(target.name+'.wallrun-intent-rollback');shutil.copy2(saved,pending);os.replace(pending,target)
        raise
    report=dict(passed=True,installed=True,date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        files={str(t.relative_to(PROJECT)):new for t,_,_,_,new in staged},delivery=delivery,
        backup=str(OUT/'installation-backup'),source_snapshot=str(CANDIDATE/'source'),
        changes=['running momentum + held jump + look toward the wall required for entry',
                 'entry look within 60 degrees of inward wall normal, and within forward 90 degrees',
                 'forward input preserves the stored direction irrespective of look or pitch',
                 'yaw through both inclusive 90 degree limits; exceeding either drops on the same command',
                 'wall-run play shortcut uses current installed build'],
        checks=wall['checks'],network_observer_and_late_joiner=True,
        poses=len(pose['poses']),hitboxes=pose['boxes_compared'],maximum_hitbox_corner_error_units=pose['maximum_corner_error_units'],
        ordinary_walking_views=walk['views'],ordinary_walking_directions=walk['walking_directions'],
        renderer_models_maps_unchanged=True)
    for target in [OUT/'installed.json',ROOT/'docs/validation/wallrun-intent-2026-10-12.json']:
        target.write_text(json.dumps(report,indent=2))
    print('PASS voluntary wall run installed:',len(staged),'SDK files;',delivery,flush=True)
    return report
if __name__=='__main__':install()
