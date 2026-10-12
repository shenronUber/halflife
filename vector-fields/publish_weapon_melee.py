"""Only publish the tested current DLLs and dedicated melee models; reject drift."""
import json,os,shutil
from pathlib import Path
from build_weapon_melee import ROOT,PROJECT,OUT,digest,sources
from release import check_native_interface
def optional(path):return digest(path) if path.exists() else None
def run():
    build=json.loads((OUT/'build.json').read_text());proof=json.loads((OUT/'native.json').read_text())
    network=json.loads((OUT/'network.json').read_text());geometry=json.loads((OUT/'geometry.json').read_text())
    manifest=json.loads((ROOT/'generated/weapon-melee/manifest.json').read_text());engine=PROJECT/'runtime/vector-engine';mod=engine/'vf_visual'
    assert proof['passed'] and network['passed'] and geometry['passed']
    assert sources()==build['sources'],'Include concurrent source changes in a new candidate before publishing'
    assert set(proof['configurations'])=={p+'_'+g for p in ('bottom','side','top') for g in ('standard','foregrip')}
    assert all(digest(path)==sha for path,sha in manifest['inputs'].items()),'Animation inputs changed'
    assert all(digest(path)==sha for path,sha in geometry['magazine_inputs'].items()),'Magazine geometry changed'
    assert proof['assets']==geometry['assets']==build['assets']
    assert len(proof['assets'])==11 and len(manifest['models'])==9
    assert all(m['old_animation_error']<.001 and m['compiled_error']<.02 for m in manifest['models'])
    assert {proof['renderer_sha256'],network['renderer_sha256']}=={digest(engine/'ref_gl.dll')},'Test the currently installed renderer before publication'
    assert proof['engine_binaries']==network['engine_binaries']=={n:digest(engine/n) for n in proof['engine_binaries']},'Test the current complete engine bundle before publication'
    candidate_client=OUT/'client/client.dll';candidate_server=OUT/'server/hl.dll'
    for field,path in (('client_sha256',candidate_client),('server_sha256',candidate_server)):
        assert digest(path)==build[field]==proof[field]==network[field],'Client/server candidate differs from reviewed version'
    check_native_interface(engine,candidate_client)
    publications=[];before={}
    installed_before=proof['installed_before']
    baseline=OUT/'publication-baseline.json'
    if baseline.exists():
        refreshed=json.loads(baseline.read_text())
        if refreshed['sources']==build['sources'] and refreshed['client_sha256']==proof['client_sha256'] and refreshed['server_sha256']==proof['server_sha256']:
            assert refreshed['passed'] and refreshed['engine_binaries']==proof['engine_binaries'] and len(refreshed['six_configurations'])==6
            installed_before=refreshed['installed_before']
    for name,sha in proof['assets'].items():
        assert name==Path(name).name
        source=ROOT/'generated/weapon-melee'/name;target=mod/'models/vf_melee'/name
        assert digest(source)==sha;before[str(target)]=optional(target);publications.append((source,target,sha))
    for part,candidate,dest,filename in (('client',candidate_client,'cl_dlls','client.dll'),('server',candidate_server,'dlls','hl.dll')):
        for target in (ROOT/'build'/part/filename,mod/dest/filename):
            before[str(target)]=optional(target)
            assert before[str(target)]==installed_before[str(target)],'Another agent published a newer binary; repeat native review against it: '+str(target)
            publications.append((candidate,target,digest(candidate)))
    controls=mod/'lab_controls.cfg';control_bytes=controls.read_bytes();binding=b'bind v "vf_melee"'
    backup=OUT/'before-publication';backup.mkdir(exist_ok=True)
    for i,(source,target,sha) in enumerate(publications):
        target.parent.mkdir(parents=True,exist_ok=True);saved=backup/(str(i)+'-'+target.name)
        if target.exists() and not saved.exists():shutil.copy2(target,saved)
        if target.exists():
            with target.open('r+b'):pass # Detect a loaded Windows DLL before replacing anything.
        pending=target.with_name(target.name+'.weapon-melee');shutil.copy2(source,pending);assert digest(pending)==sha
    pending_controls=controls.with_name(controls.name+'.weapon-melee')
    if binding not in control_bytes:pending_controls.write_bytes(control_bytes+b'\r\n'+binding+b'\r\n')
    assert sources()==build['sources'] and controls.read_bytes()==control_bytes
    assert digest(engine/'ref_gl.dll')==proof['renderer_sha256']
    assert all(digest(path)==sha for path,sha in manifest['inputs'].items())
    assert all(optional(target)==before[str(target)] for _,target,_ in publications),'Concurrent deployment during staging'
    for _,target,_ in publications:os.replace(target.with_name(target.name+'.weapon-melee'),target)
    if binding not in control_bytes:os.replace(pending_controls,controls)
    assert all(digest(target)==sha for _,target,sha in publications)
    report=dict(passed=True,binding='V',duration=1.1,impact=13/30,damage=35,range=40,
        client_sha256=digest(candidate_client),server_sha256=digest(candidate_server),assets=proof['assets'],
        original_animation_models_written=0,original_skin_models_written=0,renderer_written=False,
        source_guard=True,validation='vector-fields/build/weapon-melee/native.json',network='vector-fields/build/weapon-melee/network.json')
    (OUT/'installed.json').write_text(json.dumps(report,indent=2));print('PASS installed melee: V, current guarded client/server, eleven separate assets; original animation/skin banks preserved')
if __name__=='__main__':run()
