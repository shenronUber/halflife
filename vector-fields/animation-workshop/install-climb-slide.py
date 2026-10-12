"""Deliver only the tested files and refresh editable masters, by SHA256."""
import hashlib,json,os,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release import deployment_files,verify_deployment,check_native_interface
from studio_assets import Studio

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    out=ROOT/'docs/validation/traversal/transitions'
    report=json.loads((out/'capture.json').read_text())
    proof=json.loads((out/'compiled-retouch.json').read_text())
    assert proof['preserved_tracks']==1002 and report['focused']
    assert len(report['timeline'])==2 and report['temporary_pngs_removed']==155
    destination=ROOT.parent/'runtime/vector-engine/vf_visual'
    engine=destination.parent
    assert digest(engine/'ref_gl.dll')==report['renderer_sha256']
    candidates=[(ROOT/'build/client/client.dll',Path('cl_dlls/client.dll'),report['client_sha256']),
                (ROOT/'build/server/hl.dll',Path('dlls/hl.dll'),report['server_sha256'])]
    for folder,target in [('traversal','vf_traversal'),('third-person','vf_r01')]:
        for p in(ROOT/'generated'/folder).glob('*.mdl'):
            relative=Path('models')/target/p.name
            candidates.append((p,relative,report['assets'][str(relative)]))
    allowed={t for _,t,_ in candidates}
    # Do not accidentally publish another chat's untested generated resources.
    other=[str(t)for s,t in deployment_files()if t not in allowed and
           (not(destination/t).exists()or digest(s)!=digest(destination/t))]
    assert not other,('Unrelated deployment drift',other)
    backup=ROOT/'docs/validation/traversal/climb-slide-before/runtime'
    changes=[]
    for source,relative,expected in candidates:
        assert digest(source)==expected,('File changed after native review',source)
        target=destination/relative
        if digest(target)==expected:continue
        with target.open('r+b'):pass
        old=backup/relative;old.parent.mkdir(parents=True,exist_ok=True)
        if old.exists():assert digest(old)==digest(target),('Backup conflict',target)
        else:shutil.copy2(target,old)
        pending=target.with_name(target.name+'.climb-slide')
        shutil.copy2(source,pending);assert digest(pending)==expected
        changes.append((target,pending,old,expected))
    replaced=[]
    try:
        for target,pending,old,expected in changes:
            os.replace(pending,target);replaced.append((target,old))
            assert digest(target)==expected
        check_native_interface(engine,destination/'cl_dlls/client.dll')
        deployed=verify_deployment(destination)
    except Exception:
        for target,old in reversed(replaced):shutil.copy2(old,target)
        raise
    blender=ROOT/'animation-workshop/traversal/blender'
    projects={}
    for view,master in [('first-person','Mains-R1-revue-complete.blend'),
                        ('third-person','Corps-R1-revue-complete.blend')]:
        audit=json.loads((blender/'verification/climb-slide'/(view+'.json')).read_text())
        target=blender/master;revision=Path(audit['revision'])
        assert digest(target)==audit['baseline_sha256'],('Blender master changed while authoring',target)
        old=target.with_name(target.stem+'-avant-climb-slide.blend')
        if old.exists():assert digest(old)==digest(target)
        else:shutil.copy2(target,old)
        pending=target.with_name(target.name+'.climb-slide');shutil.copy2(revision,pending)
        os.replace(pending,target);projects[str(target)]=digest(target)
    report['installed_files']={str(t.relative_to(destination)):expected for t,_,_,expected in changes}
    report['editable_projects']=projects;report['deployment']=deployed
    report['skin_families']=Studio(destination/'models/vf_skins/persona_scout.mdl').numskinfamilies
    report['compiled_validation']=proof
    movement=(ROOT/'build/policy-tests/traversal/result.log').read_text()
    result=re.search(r'Traversal movement: (\d+) checks, 0 failures',movement)
    assert result,'Movement regression failed'
    report['movement_checks']=int(result[1])
    (out/'installed-retouch.json').write_text(json.dumps(report,indent=2))
    print('PASS installed climb/slide:',len(changes),'changed files;',report['skin_families'],'skins;',deployed)

if __name__=='__main__':main()
