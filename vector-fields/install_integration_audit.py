"""Publish the verified integrated bundle without overwriting concurrent work."""
import datetime,hashlib,json,os,shutil
from pathlib import Path
from release import check_native_interface,verify_deployment
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
OUT=ROOT/'build/integration-audit';CANDIDATE=OUT/'candidate';PROOFS=OUT/'final-native';RUNTIME=PROJECT/'runtime/vector-engine'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def install():
    pose=read(PROOFS/'pose_extended/verification.json');assert pose['passed'] and len(pose['poses'])==43 and pose['boxes_compared']==860
    for field,path in [('engine_sha256','engine/xash.dll'),('renderer_sha256','engine/ref_gl.dll'),('server_sha256','server/hl.dll')]:assert pose[field]==sha(CANDIDATE/path)
    for path in ['melee/native.json','melee_network/network.json','gesture_status/verification.json','headgear.json','walk/native.json']:
        proof=read(PROOFS/path);assert proof['passed'],path
        for field,relative in [('client_sha256','client/client.dll'),('server_sha256','server/hl.dll'),('renderer_sha256','engine/ref_gl.dll')]:
            if field in proof:assert proof[field]==sha(CANDIDATE/relative),(path,field)
    for path in ['combat/verification.json','wallrun/native.json','walljump/native.json','melee_integration/verification.json']:assert read(PROOFS/path)['passed'],path
    assert (PROOFS/'wallrun_network/network.json').is_file()
    for name,expected in read(CANDIDATE/'source-hashes.json').items():
        path=PROJECT/name
        if path.is_file():assert sha(path).lower()==expected.lower(),('Compiler input changed',name)
    assert read(ROOT/'build/validation-unit-assets.json')['passed']
    policies=read(ROOT/'build/policy-tests/results.json');assert len(policies)==15 and all(p['passed']for p in policies)
    assert 'tests that fail 0/18' in (CANDIDATE/'engine-tests.log').read_text()
    metadata=read(CANDIDATE/'engine/vector-engine-build.json')
    metadata.update(player_pose_verified=True,melee_pose_verified=True,body_verified=True,headgear_verified=True,wallrun_version=1,
        player_pose_validation='vector-fields/docs/validation/integration-2026-10-12.json',integration_verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (CANDIDATE/'engine/vector-engine-build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    check_native_interface(CANDIDATE/'engine',CANDIDATE/'client/client.dll')
    before={name.replace('\\','/'):value for name,value in read(CANDIDATE/'runtime-before.json').items()};targets=[]
    for name,expected in metadata['binaries'].items():
        assert sha(CANDIDATE/'engine'/name).upper()==expected.upper()
        targets.append((CANDIDATE/'engine'/name,RUNTIME/name,before[name]))
    targets.append((CANDIDATE/'engine/vector-engine-build.json',RUNTIME/'vector-engine-build.json',before['vector-engine-build.json']))
    for part,name,relative in [('client','client.dll','cl_dlls/client.dll'),('server','hl.dll','dlls/hl.dll')]:
        for target in [RUNTIME/'vf_visual'/relative,ROOT/'build'/part/name]:targets.append((CANDIDATE/part/name,target,before[part+'/'+name]))
    for source,target,expected in targets:
        assert PROJECT in target.resolve().parents
        assert sha(target)==expected,('Concurrent delivery',target)
        with target.open('r+b'):pass
    staged=[]
    for source,target,expected in targets:
        old=OUT/'installation-backup'/target.relative_to(PROJECT);old.parent.mkdir(parents=True,exist_ok=True)
        if old.exists():assert sha(old)==expected
        else:shutil.copy2(target,old)
        pending=target.with_name(target.name+'.integration-next');shutil.copy2(source,pending);assert sha(pending)==sha(source)
        staged.append((target,pending,old,expected,sha(source)))
    replaced=[]
    try:
        for target,pending,old,expected,new in staged:
            assert sha(target)==expected,('Concurrent write during publication',target)
            os.replace(pending,target);replaced.append((target,old));assert sha(target)==new
    except Exception:
        for target,old in reversed(replaced):
            pending=target.with_name(target.name+'.integration-rollback');shutil.copy2(old,pending);os.replace(pending,target)
        raise
    check_native_interface(RUNTIME,ROOT/'build/client/client.dll')
    delivery=verify_deployment(RUNTIME/'vf_visual')
    report=dict(passed=True,installed=True,delivery=delivery,files={str(t.relative_to(PROJECT)):new for t,_,_,_,new in staged},backup=str(OUT/'installation-backup'))
    (OUT/'installed.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS verified integration installed:',len(staged),'files;',delivery,flush=True)
    return report
if __name__=='__main__':install()
