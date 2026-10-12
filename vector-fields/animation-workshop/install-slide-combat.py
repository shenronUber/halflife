"""Deliver exactly the live-reviewed combat DLLs; preserve authored assets."""
import hashlib,json,os,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release import deployment_files,verify_deployment,check_native_interface
from studio_assets import Studio

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    out=ROOT/'docs/validation/traversal/slide-combat'
    proof=json.loads((out/'capture.json').read_text())
    assert proof['combat'] and len(proof['timeline'])==4
    for event in proof['timeline']:
        assert event['sliding_frames']>25
        if event['action']=='shoot':assert event['shots_in_slide']>=4 and event['minimum_ready_forward']>(.995 if event['view']=='first-person'else .9999)
        else:assert event['reload_started_while_sliding'] and event['completed_clip']==50
    assert len(proof['aim_tests'])==3 and all(case['minimum_alignment']>.9999 for case in proof['aim_tests'])
    checks=re.search(r'Traversal movement: (\d+) checks, 0 failures',(ROOT/'build/policy-tests/traversal/result.log').read_text())
    assert checks
    engine=ROOT.parent/'runtime/vector-engine';destination=engine/'vf_visual'
    for name,expected in proof['engine_core'].items():assert digest(engine/name)==expected,('Core changed after review',name)
    for relative,expected in proof['assets'].items():assert digest(destination/relative)==expected,('Model changed after review',relative)
    allowed={Path('cl_dlls/client.dll'),Path('dlls/hl.dll')}
    drift=[str(t)for s,t in deployment_files()if t not in allowed and(not(destination/t).exists()or digest(s)!=digest(destination/t))]
    assert not drift,('Unrelated release drift',drift)
    candidate=json.loads((ROOT/'build/engine-candidate/vector-engine-build.json').read_text(encoding='utf-8-sig'))
    assert digest(ROOT/'engine/gl_vf.inc')==candidate['renderer_sha256'].lower()
    metadata=json.loads((engine/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
    for field in('extension_version','traversal_renderer_version','status_viewmodel_version','built_utc','renderer_sha256'):
        metadata[field]=candidate[field]
    metadata['binaries']['ref_gl.dll']=proof['renderer_sha256'].upper()
    metadata['slide_combat_verified']=True
    metadata['slide_combat_validation']='vector-fields/docs/validation/traversal/slide-combat/capture.json'
    staged_metadata=out/'engine-build.json';staged_metadata.write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    candidates=[(ROOT/'build/engine-candidate/ref_gl.dll',engine/'ref_gl.dll',proof['renderer_sha256']),
                (ROOT/'build/client/client.dll',destination/'cl_dlls/client.dll',proof['client_sha256']),
                (ROOT/'build/server/hl.dll',destination/'dlls/hl.dll',proof['server_sha256']),
                (staged_metadata,engine/'vector-engine-build.json',digest(staged_metadata))]
    before=ROOT/'docs/validation/traversal/slide-combat-before';changes=[]
    for source,target,expected in candidates:
        assert digest(source)==expected,('Candidate changed after review',source)
        if digest(target)==expected:continue
        with target.open('r+b'):pass
        old=before/target.relative_to(engine);old.parent.mkdir(parents=True,exist_ok=True)
        if old.exists():assert digest(old)==digest(target),('Backup conflict',target)
        else:shutil.copy2(target,old)
        pending=target.with_name(target.name+'.slide-combat');shutil.copy2(source,pending)
        assert digest(pending)==expected;changes.append((target,pending,old,expected))
    replaced=[]
    try:
        for target,pending,old,expected in changes:
            os.replace(pending,target);replaced.append((target,old));assert digest(target)==expected
        check_native_interface(engine,destination/'cl_dlls/client.dll');deployment=verify_deployment(destination)
    except Exception:
        for target,old in reversed(replaced):shutil.copy2(old,target)
        raise
    installed=dict(files={str(t.relative_to(engine)):sha for t,_,_,sha in changes},deployment=deployment,
                   movement_checks=int(checks[1]),skin_families=Studio(destination/'models/vf_skins/persona_scout.mdl').numskinfamilies,
                   native_validation=str(out/'capture.json'),video=proof['video'])
    assert installed['skin_families']==23
    (out/'installed.json').write_text(json.dumps(installed,indent=2),encoding='utf-8')
    print('PASS installed slide combat',len(changes),'files including metadata;',deployment)

if __name__=='__main__':main()
