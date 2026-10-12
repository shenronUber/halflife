"""Install only the locally verified traversal files, preserving current skins."""
import argparse,hashlib,json,os,shutil,sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
OUT=ROOT/'docs/validation/traversal'
STAGED=ROOT/'build/traversal-reference-engine'
NATIVE=ROOT/'build/animation-native/traversal'
ENGINE=PROJECT/'runtime/vector-engine'
sys.path.insert(0,str(ROOT))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',default='reviewed-traversal')
    args=parser.parse_args()
    assert args.revision and all(c.isalnum() or c=='-' for c in args.revision),'invalid snapshot name'
    # Tests run with isolated DLLs. Do not deliver a newer file that another
    # chat rebuilt after those tests, or an older model from a prior attempt.
    for label in ('native','multiplayer','slide'):
        log=ROOT/'build'/('traversal-review-'+label+'.log')
        assert 'PASS' in log.read_text(errors='replace'),('validation incomplete',label)
    metadata=read(STAGED/'vector-engine-build.json')
    assert metadata['traversal_renderer_version']==2
    binaries=('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')
    for name in binaries:
        assert digest(STAGED/name)==metadata['binaries'][name].lower(),name
        assert digest(NATIVE/name)==digest(STAGED/name),('tested renderer changed',name)
    client=ROOT/'build/client/client.dll'
    assert digest(client)==digest(NATIVE/'vf_animation/cl_dlls/client.dll'),'client changed after native test'
    assert digest(client)==read(OUT/'slide-review/visibility.json')['client_sha256'],'slide client differs'
    server=ROOT/'build/server/hl.dll'
    assert digest(server)==digest(NATIVE/'vf_animation/dlls/hl.dll'),'server changed after native test'
    files=[(STAGED/name,Path(name))for name in binaries]
    files.append((client,Path('vf_visual/cl_dlls/client.dll')))
    files.append((server,Path('vf_visual/dlls/hl.dll')))
    for folder,target in [('traversal','vf_traversal'),('third-person','vf_r01')]:
        models=sorted((ROOT/'generated'/folder).glob('*.mdl'))
        assert len(models)==(9 if folder=='traversal' else 3),(folder,len(models))
        for path in models:
            relative=Path('models')/target/path.name
            assert digest(path)==digest(NATIVE/'vf_animation'/relative),('model changed after native test',path.name)
            files.append((path,Path('vf_visual')/relative))
    assets=read(OUT/'review-assets.json')
    assert assets['preserved_sequences']==297 and assets['aim_samples']==96,assets
    from studio_assets import Studio
    source_skins=Studio(ROOT/'generated/personas/persona_scout.mdl').numskinfamilies
    assert Studio(ENGINE/'vf_visual/models/vf_skins/persona_scout.mdl').numskinfamilies==source_skins,'skin catalogue changed'
    blender=ROOT/'animation-workshop/traversal/blender'
    assert digest(blender/'Mains-R1.blend')=='655f2ed5d9dd7501cd3f0821c964c738fee05bff1fa07585870eeede462645c0'
    audits={view:read(blender/'verification/audit-traversal/after'/view/'rig-audit.json')for view in ('first-person','third-person')}
    assert sum(len(a['tracks'])for a in audits.values())==114
    proof=dict(verified_utc=datetime.now(timezone.utc).isoformat(),client_sha256=digest(client),server_sha256=digest(server),
        engine=metadata['binaries'],models={str(target):digest(source)for source,target in files if source.suffix=='.mdl'},
        skin_families=source_skins,blender_tracks=114,blender_samples=sum(a['sampled_frames']for a in audits.values()),
        blender_renders=sum(len(a['renders'])for a in audits.values()),compiled_assets=assets,
        native_world_contacts=read(OUT/'body-settled.json'),planted_lower_body=read(OUT/'body-anchor.json'),
        extended_firing_arm=read(OUT/'extended-arm.json'),first_person_gun=read(OUT/'view-gun.json'),guard_visibility=read(OUT/'guard-visibility.json'),
        torso_clearance=read(OUT/'torso-clearance.json'),
        multiplayer=read(OUT/'multiplayer/network.json'))
    (OUT/'review-validation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    metadata['traversal_grip_verified']=True
    metadata['traversal_validation']='vector-fields/docs/validation/traversal/review-validation.json'
    (STAGED/'vector-engine-build.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    files.append((STAGED/'vector-engine-build.json',Path('vector-engine-build.json')))
    backup=OUT/'review-backups'/('runtime-before-'+args.revision)
    backup.mkdir(parents=True,exist_ok=True)
    before={}
    # Probe ALL destinations before replacing anything, including Windows DLLs.
    for source,relative in files:
        destination=ENGINE/relative
        assert destination.resolve().is_relative_to(ENGINE.resolve()),relative
        if destination.exists():
            with destination.open('r+b'):pass
            old=backup/relative;old.parent.mkdir(parents=True,exist_ok=True)
            if old.exists():assert digest(old)==digest(destination),('snapshot differs from installed file',old)
            else:shutil.copy2(destination,old)
            before[str(relative)]=digest(destination)
    (backup/'hashes.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
    replacements=[]
    try:
        for source,relative in files:
            destination=ENGINE/relative;destination.parent.mkdir(parents=True,exist_ok=True)
            pending=destination.with_name(destination.name+'.vf-reviewed')
            shutil.copy2(source,pending)
            assert digest(pending)==digest(source),relative
        for source,relative in files:
            destination=ENGINE/relative
            os.replace(destination.with_name(destination.name+'.vf-reviewed'),destination)
            replacements.append(relative)
            assert digest(destination)==digest(source),relative
    except Exception:
        for relative in reversed(replacements):
            old=backup/relative
            if old.exists():shutil.copy2(old,ENGINE/relative)
        raise
    from release import check_native_interface
    check_native_interface(ENGINE,ENGINE/'vf_visual/cl_dlls/client.dll')
    proof['installed_files']={str(relative):digest(ENGINE/relative)for _,relative in files}
    proof['runtime_backup']=str(backup)
    (OUT/'review-validation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('PASS installed reviewed traversal:',len(files),'files;',source_skins,'existing skin families preserved')


if __name__=='__main__':main()
