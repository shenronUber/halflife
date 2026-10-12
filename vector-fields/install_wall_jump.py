"""Deliver only the tested wall-jump bundle with concurrent-write guards."""
import hashlib,json,os,shutil,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;CANDIDATE=ROOT/'build/wall-jump'
OUT=ROOT/'docs/validation/traversal/wall-jump';RUNTIME=PROJECT/'runtime/vector-engine'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def install():
    proof=json.loads((OUT/'native.json').read_text());assert proof.get('passed'),'Native verification must pass'
    walking=json.loads((OUT/'walking/native.json').read_text());assert walking.get('passed'),'Ordinary walking must pass before delivery'
    assert walking['binaries']==proof['binaries'], 'Walking and jumping must use the same game build'
    assert walking['renderer_sha256']==proof['engine']['ref_gl.dll'], 'Walking and jumping must use the same renderer'
    assert walking['delta_sha256']==proof['delta_sha256']==sha(PROJECT/'network/delta.lst'), 'Verified player-pose network fields changed'
    inputs=json.loads((CANDIDATE/'source-hashes.json').read_text())
    from build_wall_jump_native import without_audit_input
    diagnostic_path=CANDIDATE/'diagnostic-inputs.json'
    diagnostics=json.loads(diagnostic_path.read_text())if diagnostic_path.exists()else{}
    drift=[n for n,h in inputs.items()if(PROJECT/n).exists()and sha(PROJECT/n)!=h and
           not(n in diagnostics and without_audit_input((PROJECT/n).read_text())==without_audit_input(Path(diagnostics[n]).read_text()))]
    if drift:raise RuntimeError('Sources changed since compilation; rebuild before installing: '+str(drift))
    for path,expected in json.loads((CANDIDATE/'artifact-inputs.json').read_text()).items():
        assert sha(path)==expected,('Animation or course changed since verification',path)
    runtime_before=json.loads((CANDIDATE/'runtime-before.json').read_text())
    engine_before=json.loads((CANDIDATE/'engine-before.json').read_text())
    generated_before=json.loads((CANDIDATE/'generated-before.json').read_text())
    candidates=[]
    for name,part,relative in [('server','hl.dll','dlls/hl.dll'),('client','client.dll','cl_dlls/client.dll')]:
        source=CANDIDATE/name/part;assert sha(source)==proof['binaries'][name]
        candidates.extend([(source,RUNTIME/'vf_visual'/relative,runtime_before[relative]),
                           (source,ROOT/'build'/name/part,generated_before['build/'+name+'/'+part])])
    for record in proof['assets']:
        source=Path(record['candidate']);assert sha(source)==record['sha256']
        assert walking['assets'][record['relative']]==record['sha256'], 'Walking carrier changed after verification'
        folder='traversal'if record['view']=='first-person'else'third-person'
        candidates.extend([(source,RUNTIME/'vf_visual'/record['relative'],record['runtime_sha256']),
                           (source,ROOT/'generated'/folder/source.name,record['source_sha256'])])
    metadata=json.loads((CANDIDATE/'engine/vector-engine-build.json').read_text())
    for name,expected in metadata['binaries'].items():
        source=CANDIDATE/'engine'/name;assert sha(source).upper()==expected.upper()
        assert sha(source)==proof['engine'][name],('Engine changed after native test',name)
        candidates.append((source,RUNTIME/name,engine_before[name]))
    candidates.append((CANDIDATE/'engine/vector-engine-build.json',RUNTIME/'vector-engine-build.json',engine_before['vector-engine-build.json']))
    source=CANDIDATE/'generated/traversal-range/vf_traversal.bsp'
    candidates.append((source,RUNTIME/'vf_visual/maps/vf_traversal.bsp',runtime_before['maps/vf_traversal.bsp']))
    target=ROOT/'generated/traversal-range/vf_traversal.bsp'
    candidates.append((source,target,sha(target)))
    candidates.append((PROJECT/'network/delta.lst',RUNTIME/'vf_visual/delta.lst',runtime_before['delta.lst']))
    # Check every target before replacing anything. A newer installed bundle
    # belongs to the other agent; an old candidate must never overwrite it.
    for source,target,baseline in candidates:
        assert PROJECT in target.resolve().parents,('Destination escaped project',target)
        if sha(target)!=baseline:raise RuntimeError('Concurrent delivery detected: '+str(target))
        with target.open('r+b'):pass
    candidates=[(s,t,b)for s,t,b in candidates if sha(s)!=sha(t)]
    backup=OUT/'installed-backup';pending=[];tag=uuid.uuid4().hex[:8]
    for source,target,baseline in candidates:
        old=backup/target.relative_to(PROJECT);old.parent.mkdir(parents=True,exist_ok=True)
        if old.exists():assert sha(old)==baseline,('Backup already belongs to a different revision',old)
        else:shutil.copy2(target,old)
        temporary=target.with_name(target.name+'.wall-jump-'+tag)
        shutil.copy2(source,temporary);assert sha(temporary)==sha(source)
        pending.append((target,temporary,old,baseline,sha(source)))
    replaced=[]
    try:
        for target,temporary,old,baseline,expected in pending:
            if sha(target)!=baseline:raise RuntimeError('Concurrent write before replacement: '+str(target))
            os.replace(temporary,target);replaced.append((target,old));assert sha(target)==expected
    except Exception:
        for target,old in reversed(replaced):
            temporary=target.with_name(target.name+'.rollback-'+tag);shutil.copy2(old,temporary);os.replace(temporary,target)
        raise
    report=dict(installed={str(t.relative_to(PROJECT)):h for t,_,_,_,h in pending},
                backup=str(backup),native=proof,walking=walking,movement='16899 checks; server/client parity at 8, 16 and 33 ms')
    (OUT/'installed.json').write_text(json.dumps(report,indent=2))
    print('PASS installed tested wall jump:',len(pending),'files; prior files backed up',flush=True)

if __name__=='__main__':install()
