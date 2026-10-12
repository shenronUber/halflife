"""Deliver only the Blender-reviewed fist assets after frozen native checks."""
import datetime,json,os,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,digest,sources
from release import check_native_interface,verify_deployment
OUT=ROOT/'build/fist-refinement';CANDIDATE=OUT/'candidate';LIVE=PROJECT/'runtime/vector-engine'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def install():
    geometry=read(OUT/'geometry.json');thumb=read(OUT/'thumb-preservation.json')
    melee=read(OUT/'native/melee/native.json');pose=read(OUT/'native/pose_strike/verification.json')
    network=read(OUT/'native/melee_network/network.json');network_build=read(OUT/'native/melee_network/build.json')
    headgear=read(OUT/'native/headgear.json')
    assert all(p['passed']for p in [geometry,thumb,melee,pose,network,headgear])
    assert len(pose['poses'])==64 and pose['boxes_compared']==1280
    assert geometry['assets']==melee['assets']==pose['melee_assets']==network_build['assets']
    assert geometry['assets']=={p.name:digest(p)for p in(CANDIDATE/'models/vf_melee').glob('*.mdl')}
    assert sources()==read(CANDIDATE/'source-hashes.json')
    manifest=read(OUT/'assets/manifest.json');assert all(digest(p)==sha for p,sha in manifest['inputs'].items())
    for proof in [melee,pose,network,headgear]:
        for field,path in [('server_sha256','server/hl.dll'),('client_sha256','client/client.dll'),('engine_sha256','engine/xash.dll'),('renderer_sha256','engine/ref_gl.dll')]:
            if field in proof:assert proof[field]==digest(CANDIDATE/path),(field,'unreviewed binary')
    before=read(OUT/'runtime-before.json');assert all(digest(PROJECT/p)==sha for p,sha in before.items())
    articulated=read(OUT/'articulated-models.json')
    assert {r['file']:r['sha256']for r in thumb['models']}=={r['relative']:r['sha256']for r in articulated}
    pairs=[]
    for p in(CANDIDATE/'models/vf_melee').glob('*.mdl'):
        pairs.extend([(p,LIVE/'vf_visual/models/vf_melee'/p.name),(p,ROOT/'generated/weapon-melee'/p.name)])
    for r in articulated:
        source=CANDIDATE/r['relative'];assert digest(source)==r['sha256']
        pairs.append((source,LIVE/'vf_visual'/r['relative']))
    pairs.append((OUT/'assets/manifest.json',ROOT/'generated/weapon-melee/manifest.json'))
    staged=[]
    for source,target in pairs:
        assert PROJECT.resolve()in target.resolve().parents
        old=digest(target);new=digest(source)
        if old==new:continue
        saved=OUT/'installation-backup'/target.relative_to(PROJECT);saved.parent.mkdir(parents=True,exist_ok=True)
        if saved.exists():assert digest(saved)==old
        else:shutil.copy2(target,saved)
        pending=target.with_name(target.name+'.fist-next');shutil.copy2(source,pending);assert digest(pending)==new
        staged.append((target,pending,saved,old,new))
    replaced=[]
    try:
        assert all(digest(PROJECT/p)==sha for p,sha in before.items())
        for target,pending,saved,old,new in staged:
            assert digest(target)==old;os.replace(pending,target);replaced.append((target,saved));assert digest(target)==new
        delivery=verify_deployment(LIVE/'vf_visual')
        # This delivery changes no native binaries and retains the previous
        # shared pose/collision, traversal, reload and combat implementations.
        unchanged={p:sha for p,sha in before.items()if not p.lower().endswith('.mdl')}
        assert all(digest(PROJECT/p)==sha for p,sha in unchanged.items())
        check_native_interface(LIVE,LIVE/'vf_visual/cl_dlls/client.dll')
    except Exception:
        for target,saved in reversed(replaced):
            pending=target.with_name(target.name+'.fist-rollback');shutil.copy2(saved,pending);os.replace(pending,target)
        raise
    report=dict(passed=True,installed=True,date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        files={str(target.relative_to(PROJECT)):new for target,_,_,_,new in staged},delivery=delivery,
        blend_file=manifest['blend_file'],backup=str(OUT/'installation-backup'),native_binaries_unchanged=unchanged,
        poses=len(pose['poses']),hitboxes=pose['boxes_compared'],maximum_hitbox_corner_error_units=pose['maximum_corner_error_units'],
        checks=['Blender close-ups of fingers, thumb, wrist and release/regrip in both views',
        'six FP mounts and standing/crouched TP actions','all four magazines clear of the guard',
        f"{len(thumb['models'])} delivered rigs/clothing preserve every legacy animation channel and rest geometry",
        'actual remote player standing/crouched melee on two native clients','headgear reach/grip, save/restore and FP/TP pose checks'],
        changes=['Explicit curled finger poses with staggered closure','Neutral wrist throughout the free-hand guard',
                 'TP distal thumb articulation preserves palm webbing','Smooth release and return to the original weapon grip'])
    (OUT/'installed.json').write_text(json.dumps(report,indent=2))
    (ROOT/'docs/validation/fist-refinement-2026-10-12.json').write_text(json.dumps(report,indent=2))
    print('PASS reviewed fist installed:',len(staged),'files;',delivery,flush=True)
    return report
if __name__=='__main__':install()
