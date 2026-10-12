"""Publish reviewed inspection models/client with guards for concurrent edits."""
import argparse,json,os,shutil
from pathlib import Path
from build_weapon_inspect import ROOT,OUT,PROJECT,sources,digest
from release import check_native_interface

def optional_digest(path):return digest(path) if path.exists() else None

def reviewed_sources(build,models_only):
    current=sources();reviewed=build['sources']
    if models_only:
        names=('build_weapon_inspect_rigs.py','build_weapon_inspect_hands.py','build_reference_platforms.py','animation_assets.py','studio_assets.py')
        reviewed={key:sha for key,sha in reviewed.items() if '/models/vf_r01/' in key.replace('\\','/') or
                  key.replace('\\','/') in {'vector-fields/'+name for name in names}}
    assert reviewed and all(current.get(key)==sha for key,sha in reviewed.items()),'Concurrent source edits require a new client build/test'

def run(models_only=False):
    build=json.loads((OUT/'build.json').read_text())
    proof=json.loads((OUT/'native.json').read_text())
    assert proof['passed'];reviewed_sources(build,models_only)
    expected={platform+'_'+grip for platform in ('bottom','side','top') for grip in ('standard','foregrip')}
    assert set(proof.get('configurations',{}))==expected,'Review all six configurations before publication'
    clearance=json.loads((OUT/'clearance.json').read_text())
    assert clearance['passed'] and clearance['model_sha256']==proof['inspection_assets'],'Clearance review must match the tested models'
    candidate=OUT/'client/client.dll'
    assert digest(candidate)==build['client_sha256']==proof['client_sha256']
    assert b'VFInspect pose:' in candidate.read_bytes()
    engine=PROJECT/'runtime/vector-engine';mod=engine/'vf_visual'
    assert all(digest(mod/'models/vf_r01'/name)==sha for name,sha in clearance['geometry_sources'].items()),'Magazine geometry changed since clearance review'
    assert digest(engine/'ref_gl.dll')==proof['renderer_sha256'],'Renderer changed since native review'
    assert digest(mod/'dlls/hl.dll')==proof['server_sha256'],'Server changed since native review'
    check_native_interface(engine,candidate)
    clients=(ROOT/'build/client/client.dll',mod/'cl_dlls/client.dll')
    before={str(t):digest(t) for t in clients}
    assert before[str(clients[1])]==proof['installed_client_sha256'],'Installed client changed since review'
    if models_only:
        assert before[str(clients[1])]==proof['client_sha256'],'Model-only publication requires the exact tested installed client'
    elif clients[0].stat().st_mtime>build['started'] and before[str(clients[0])]!=proof['shared_client_sha256']:
        raise RuntimeError('A newer shared client needs to be included before publication')
    assets=proof['inspection_assets'];assert len(assets)==8
    publications=[]
    for name,sha in assets.items():
        source=ROOT/'generated/weapon-inspect'/name;target=mod/'models/vf_inspect'/name
        assert name==Path(name).name and digest(source)==sha
        prior=proof['installed_inspection_assets'][name]
        actual=optional_digest(target)
        assert actual in (prior,sha),'Concurrent inspection asset deployment detected: '+name
        before[str(target)]=actual;publications.append((source,target,sha))
    if not models_only:publications.extend((candidate,t,proof['client_sha256']) for t in clients)
    controls=mod/'lab_controls.cfg';data=controls.read_bytes();binding=b'bind i "vf_inspect"'
    if models_only:assert binding in data,'Model-only publication requires the existing I binding'
    backup=OUT/'before-publication';backup.mkdir(exist_ok=True)
    for source,target,sha in publications:
        target.parent.mkdir(parents=True,exist_ok=True)
        saved=backup/(target.name if target not in clients else 'client-'+str(clients.index(target))+'.dll')
        if target.exists() and not saved.exists():shutil.copy2(target,saved)
        pending=target.with_name(target.name+'.weapon-inspect');shutil.copy2(source,pending)
        assert digest(pending)==sha
    pending_controls=controls.with_name(controls.name+'.weapon-inspect')
    if binding not in data:pending_controls.write_bytes(data+b'\r\n'+binding+b'\r\n')
    reviewed_sources(build,models_only)
    if models_only:assert digest(clients[1])==proof['client_sha256'],'Installed client changed during model staging'
    assert all(digest(mod/'models/vf_r01'/name)==sha for name,sha in clearance['geometry_sources'].items())
    assert digest(engine/'ref_gl.dll')==proof['renderer_sha256']
    assert digest(mod/'dlls/hl.dll')==proof['server_sha256']
    assert controls.read_bytes()==data,'Concurrent control change detected'
    for _,target,_ in publications:
        assert optional_digest(target)==before[str(target)],'Concurrent deployment detected: '+str(target)
    # Assets first; original R1/player/traversal banks are never destinations.
    for _,target,_ in publications:os.replace(target.with_name(target.name+'.weapon-inspect'),target)
    if binding not in data:os.replace(pending_controls,controls)
    assert all(digest(target)==sha for _,target,sha in publications)
    report=dict(passed=True,client_sha256=proof['client_sha256'],client_files=0 if models_only else 2,binding='I',
        inspection_assets=assets,inspection_carriers=6,inspection_hand_models=2,
        original_animation_banks_written=0,player_models_written=0,server_written=False,renderer_written=False,
        publication='inspection_models_only' if models_only else 'client_and_models',
        model_sources_current=True,sources_current=sources()==build['sources'],validation='vector-fields/build/weapon-inspect/native.json')
    (OUT/'installed.json').write_text(json.dumps(report,indent=2))
    print('PASS installed inspection: eight dedicated models; tested installed client and I binding preserved; no DLLs or shared animation/player banks written' if models_only else
          'PASS installed inspection: eight dedicated models, client and I binding; original animation/player banks untouched')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--models-only',action='store_true')
    args=parser.parse_args();run(args.models_only)
