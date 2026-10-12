"""Install the native-reviewed slide DLLs/poses without touching other assets."""
import hashlib,json,os,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release import deployment_files,verify_deployment,check_native_interface
from studio_assets import Studio

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    out=ROOT/'docs/validation/traversal/short-slide'
    report=json.loads((out/'capture.json').read_text());proof=json.loads((out/'compiled-pose.json').read_text())
    movement=(ROOT/'build/policy-tests/traversal/result.log').read_text()
    checks=re.search(r'Traversal movement: (\d+) checks, 0 failures',movement)
    assert checks and report['slide_only'] and len(report['timeline'])==2
    assert proof['skins']==23 and proof['slide_frames']>100
    destination=ROOT.parent/'runtime/vector-engine/vf_visual';engine=destination.parent
    assert digest(engine/'ref_gl.dll')==report['renderer_sha256']
    candidates=[(ROOT/'build/client/client.dll',Path('cl_dlls/client.dll'),report['client_sha256']),
                (ROOT/'build/server/hl.dll',Path('dlls/hl.dll'),report['server_sha256'])]
    for folder,target,names in [('third-person','vf_r01',['r01_tp','r01_tp_side','r01_tp_top']),
                               ('traversal','vf_traversal',['slide_legs'])]:
        for name in names:
            relative=Path('models')/target/(name+'.mdl')
            candidates.append((ROOT/'generated'/folder/(name+'.mdl'),relative,report['assets'][str(relative)]))
    allowed={t for _,t,_ in candidates}
    other=[str(t)for s,t in deployment_files()if t not in allowed and
           (not(destination/t).exists()or digest(s)!=digest(destination/t))]
    assert not other,('Unrelated deployment drift',other)
    blender=ROOT/'animation-workshop/traversal/blender'
    authored=json.loads((blender/'verification/short-slide/third-person.json').read_text())
    master=blender/'Corps-R1-revue-complete.blend'
    assert digest(master)==authored['baseline_sha256'],'Blender master edited during authoring'
    backup=ROOT/'docs/validation/traversal/short-slide-before/runtime';changes=[]
    for source,relative,expected in candidates:
        assert digest(source)==expected,('File changed since native review',source)
        target=destination/relative
        if digest(target)==expected:continue
        with target.open('r+b'):pass
        old=backup/relative;old.parent.mkdir(parents=True,exist_ok=True)
        if old.exists():assert digest(old)==digest(target),('Backup conflict',target)
        else:shutil.copy2(target,old)
        pending=target.with_name(target.name+'.short-slide');shutil.copy2(source,pending)
        assert digest(pending)==expected;changes.append((target,pending,old,expected))
    replaced=[]
    try:
        for target,pending,old,expected in changes:
            os.replace(pending,target);replaced.append((target,old));assert digest(target)==expected
        check_native_interface(engine,destination/'cl_dlls/client.dll');deployment=verify_deployment(destination)
    except Exception:
        for target,old in reversed(replaced):shutil.copy2(old,target)
        raise
    old_master=master.with_name(master.stem+'-avant-glissade-courte.blend')
    if old_master.exists():assert digest(old_master)==digest(master)
    else:shutil.copy2(master,old_master)
    pending=master.with_name(master.name+'.short-slide');shutil.copy2(authored['revision'],pending);os.replace(pending,master)
    report.update(installed_files={str(t.relative_to(destination)):sha for t,_,_,sha in changes},
                  editable_project=dict(path=str(master),sha256=digest(master)),deployment=deployment,
                  movement_checks=int(checks[1]),compiled_validation=proof,
                  skin_families=Studio(destination/'models/vf_skins/persona_scout.mdl').numskinfamilies,
                  tuning=dict(max_duration=1.2,minimum_speed=280,maximum_speed=400,friction=.35,recovery=.85))
    (out/'installed.json').write_text(json.dumps(report,indent=2))
    print('PASS installed short slide',len(changes),'changed files;',deployment)

if __name__=='__main__':main()
