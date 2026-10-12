"""Install the exact slide review, without publishing any animation assets."""
import hashlib,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from release import check_native_interface,verify_deployment
from slide_feet_bundle import digest

def main():
    engine=ROOT.parent/'runtime/vector-engine';mod=engine/'vf_visual';candidate=ROOT/'build/slide-feet'
    visual=json.loads((ROOT/'docs/validation/traversal/slide-review/visibility.json').read_text())
    combat=json.loads((ROOT/'docs/validation/traversal/slide-combat/capture.json').read_text())
    baseline=json.loads((candidate/'baseline.json').read_text())
    assert visual['permanent_body_hidden_during_slide'] and visual['permanent_body_restored_after_slide']
    assert visual['leg_pixels']>2000 and combat['dedicated_slide_legs'] and combat['frames']==440
    assert combat['client_sha256']==visual['client_sha256'] and combat['renderer_sha256']==visual['renderer_sha256']
    for event in combat['timeline']:
        if event['action']=='shoot':assert event['shots_in_slide']>=4
        else:assert event['reload_started_while_sliding'] and event['completed_clip']==50
    # Stop on a concurrent publication rather than rolling that chat back.
    assert digest(engine/'ref_gl.dll')==baseline['renderer_sha256'],'Renderer changed concurrently; rebase required'
    assert digest(mod/'cl_dlls/client.dll')==baseline['client_sha256'],'Installed client changed concurrently'
    assert digest(ROOT/'build/client/client.dll')==baseline['shared_client_sha256'],'Shared client changed concurrently'
    assert digest(engine/'vector-engine-build.json')==baseline['metadata_sha256'],'Engine metadata changed concurrently'
    assert digest(mod/'dlls/hl.dll')==combat['server_sha256']==baseline['server_sha256']
    for name,expected in combat['engine_core'].items():assert digest(engine/name)==expected,('Engine core changed',name)
    for name,expected in combat['assets'].items():assert digest(mod/name)==expected,('Installed asset changed',name)
    assert digest(mod/'models/vf_traversal/slide_legs.mdl')==visual['slide_model_sha256']
    metadata=json.loads((engine/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
    new=json.loads((candidate/'engine/vector-engine-build.json').read_text(encoding='utf-8-sig'))
    assert metadata['headgear_renderer_sha256']==new['headgear_renderer_sha256']
    assert digest(ROOT/'engine/gl_vf.inc')==new['renderer_sha256'].lower(),'Source changed after review'
    metadata.update(renderer_sha256=new['renderer_sha256'],built_utc=new['built_utc'],
                    slide_feet_verified=True,slide_feet_validation='vector-fields/docs/validation/traversal/slide-review/visibility.json',
                    slide_combat_verified=True,slide_combat_validation='vector-fields/docs/validation/traversal/slide-combat/capture.json')
    metadata['binaries']['ref_gl.dll']=combat['renderer_sha256'].upper()
    pending_meta=candidate/'installed-metadata.json';pending_meta.write_text(json.dumps(metadata,indent=2))
    updates=[(candidate/'engine/ref_gl.dll',engine/'ref_gl.dll',combat['renderer_sha256']),
             (candidate/'client/client.dll',mod/'cl_dlls/client.dll',combat['client_sha256']),
             (candidate/'client/client.dll',ROOT/'build/client/client.dll',combat['client_sha256']),
             (pending_meta,engine/'vector-engine-build.json',digest(pending_meta))]
    backup=candidate/'before';changes=[]
    for source,target,expected in updates:
        assert digest(source)==expected,('Reviewed binary changed',source)
        with target.open('r+b'):pass
        relative=target.relative_to(ROOT.parent);old=backup/relative;old.parent.mkdir(parents=True,exist_ok=True)
        assert not old.exists(),'This one-time deployment already has a rollback snapshot'
        shutil.copy2(target,old);pending=target.with_name(target.name+'.slide-feet');shutil.copy2(source,pending)
        changes.append((target,pending,old,expected,digest(target)))
    replaced=[]
    try:
        # Check each old file immediately before replacing it as well.
        for target,pending,old,expected,previous in changes:
            assert digest(target)==previous,('Concurrent publication',target)
            os.replace(pending,target);replaced.append((target,old));assert digest(target)==expected
        check_native_interface(engine,mod/'cl_dlls/client.dll')
        deployment=verify_deployment(mod)
        assert digest(mod/'dlls/hl.dll')==baseline['server_sha256']
        for name,expected in combat['assets'].items():assert digest(mod/name)==expected
    except Exception:
        for target,old in reversed(replaced):shutil.copy2(old,target)
        raise
    result=dict(passed=True,changed=[str(t.relative_to(ROOT.parent))for t,_,_,_,_ in changes],
                deployment=deployment,animation_assets_modified=0,server_modified=False,
                installed_headgear_preserved=True,visibility=visual,combat_frames=combat['frames'])
    (ROOT/'docs/validation/traversal/slide-review/installed.json').write_text(json.dumps(result,indent=2))
    print('PASS installed dedicated slide feet; permanent body restored afterwards; animation assets untouched')

if __name__=='__main__':main()
