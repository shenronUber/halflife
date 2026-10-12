"""Single release identity and inventory startup used by the normal launcher."""
import json, hashlib, shutil, os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
VERSION=json.loads((ROOT/'version.json').read_text(encoding='utf-8-sig'))

def startup():
 # A launch opens the player's inventory without overwriting saved equipment.
 return ('exec vf_voice_behavior.cfg\nwait 180\ncon_notifytime 0\nweapon_9mmAR\nvf_operator\n'
         'wait 30\nvf_animation_time 0\n')


def check_native_interface(engine,client):
    # Both interfaces are versioned. Refuse a mixed installation before copying
    # files: a disconnected renderer can otherwise expose the stock HEV player.
    if not client.exists():return
    required=4 if b'v4 connected' in client.read_bytes() else 3 if b'v3 connected' in client.read_bytes() else 2
    manifest=engine/'vector-engine-build.json'
    actual=json.loads(manifest.read_text(encoding='utf-8-sig')).get('extension_version') if manifest.exists() else None
    if b'VFPlayerPose collision: shared=1' in client.read_bytes() and json.loads(manifest.read_text(encoding='utf-8-sig')).get('player_pose_version',0)<1:
        raise RuntimeError('This client requires the matching shared player-pose engine and renderer for anatomical collision.')
    if b'VFMelee pose: shared=1' in client.read_bytes() and json.loads(manifest.read_text(encoding='utf-8-sig')).get('melee_pose_version',0)<1:
        raise RuntimeError('This client requires the matching shared melee-pose engine and renderer.')
    if actual==required==4 and json.loads(manifest.read_text(encoding='utf-8-sig')).get('headgear_renderer_version',0)<1:
        raise RuntimeError('This client requires the articulated headgear renderer. Rebuild the matching native bundle before deploying.')
    if actual==required and b'VFStatus arms: renderer=1' in client.read_bytes() and json.loads(manifest.read_text(encoding='utf-8-sig')).get('status_viewmodel_version',0)<1:
        raise RuntimeError('The client requires the tested arm-only status renderer. Relaunch with Jouer - Vector Fields.cmd to install its pending update.')
    traversal=2 if b'VFTraversal render: world palms=2' in client.read_bytes() else 1 if b'VFTraversal render: world palms=1' in client.read_bytes() else 0
    if actual==required and json.loads(manifest.read_text(encoding='utf-8-sig')).get('traversal_renderer_version',0)<traversal:
        raise RuntimeError('Rebuild the native engine with vector-fields/build-engine.ps1: this client requires world-anchored ledge palms.')
    body=2 if b'VFBody motion: world slide=1' in client.read_bytes() else 1 if b'VFBody render: world body=1' in client.read_bytes() else 0
    if actual==required and json.loads(manifest.read_text(encoding='utf-8-sig')).get('body_renderer_version',0)<body:
        raise RuntimeError('This client requires the world-space first-person body renderer. Install the reviewed native bundle before deploying.')
    if actual!=required:
        raise RuntimeError(f'Native renderer/client versions differ ({actual}/{required}). Rebuild both with vector-fields/build-engine.ps1 and vector-fields/build.ps1 before deploying. Existing installed files were not changed.')


def prepare_native_renderer_update(engine,client,update=None,force=False):
    """Apply the verified renderer update before the classic launcher stages a mod."""
    if not client.exists():return False
    capabilities=client.read_bytes()
    manifest=engine/'vector-engine-build.json'
    installed=json.loads(manifest.read_text(encoding='utf-8-sig')) if manifest.exists() else {}
    status=b'VFStatus arms: renderer=1' in capabilities and installed.get('status_viewmodel_version',0)<1
    traversal=b'VFTraversal render: world palms=2' in capabilities and installed.get('traversal_renderer_version',0)<2
    body_required=2 if b'VFBody motion: world slide=1' in capabilities else 1 if b'VFBody render: world body=1' in capabilities else 0
    body=installed.get('body_renderer_version',0)<body_required
    headgear=b'v4 connected' in capabilities and (force or installed.get('extension_version')!=4 or installed.get('headgear_renderer_version',0)<1)
    pose=b'VFPlayerPose collision: shared=1' in capabilities and installed.get('player_pose_version',0)<1
    melee=b'VFMelee pose: shared=1' in capabilities and installed.get('melee_pose_version',0)<1
    if not status and not traversal and not body and not headgear and not pose and not melee:return False
    update=update or ROOT/('build/integration-audit/candidate/engine' if melee else 'build/combat-fixes/engine' if pose else 'build/first-person-motion/engine' if body_required==2 else 'build/headgear-action/engine' if headgear else 'build/engine-candidate' if body else 'build/traversal-reference-engine' if traversal else 'build/status-renderer-update')
    metadata=update/'vector-engine-build.json'
    if not metadata.exists():raise RuntimeError('Build the status renderer with vector-fields/build-engine.ps1 before launching this client.')
    tested=json.loads(metadata.read_text(encoding='utf-8-sig'))
    names=('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')
    if tested.get('extension_version')!=(4 if b'v4 connected' in capabilities else 3) or tested.get('status_viewmodel_version',0)<1:
        raise RuntimeError('The pending renderer has incompatible native capabilities.')
    if headgear and not tested.get('headgear_verified'):raise RuntimeError('The pending renderer has not passed headgear animation validation.')
    if pose and (tested.get('player_pose_version',0)<1 or not tested.get('player_pose_verified')):
        raise RuntimeError('The pending shared player-pose engine has not passed native collision/render validation.')
    if melee and (tested.get('melee_pose_version',0)<1 or not tested.get('melee_pose_verified')):
        raise RuntimeError('The pending melee-pose engine has not passed native collision/render validation.')
    if status and not tested.get('status_feedback_verified'):
        raise RuntimeError('The pending renderer has not passed status feedback validation.')
    if traversal and (tested.get('traversal_renderer_version',0)<2 or not tested.get('traversal_grip_verified')):
        raise RuntimeError('The pending renderer has not passed traversal grip validation.')
    if body and (tested.get('body_renderer_version',0)<body_required or not tested.get('body_verified')):
        raise RuntimeError('The pending renderer has not passed own-body validation.')
    check_native_interface(update,client)
    for name in names:
        if hashlib.sha256((update/name).read_bytes()).hexdigest().lower()!=tested['binaries'][name].lower():
            raise RuntimeError('Pending native renderer hash differs: '+name)
    # Probe every destination before replacing anything; loaded Windows DLLs are locked.
    try:
        for name in names:
            path=engine/name
            if path.exists():
                with path.open('r+b'):pass
        for name in (*names,'vector-engine-build.json'):
            path=engine/name;pending=engine/(name+'.vf-next')
            shutil.copy2(update/name,pending);os.replace(pending,path)
    except PermissionError as error:
        raise RuntimeError('Close the running Vector Fields game, then use Jouer - Vector Fields.cmd again to load the reviewed visuals.') from error
    return True


MODEL_GROUPS = (
    ('weapon-melee', 'vf_melee', ('r01_rig', 'r01_rig_side', 'r01_rig_top', 'r01_rig_fg', 'r01_rig_side_fg', 'r01_rig_top_fg', 'r01_tp', 'r01_tp_side', 'r01_tp_top', 'melee_gloves', 'melee_sleeves')),
    ('weapon-inspect', 'vf_inspect', ('r01_rig', 'r01_rig_side', 'r01_rig_top', 'r01_rig_fg', 'r01_rig_side_fg', 'r01_rig_top_fg', 'inspect_gloves', 'inspect_sleeves')),
    ('headgear', 'vf_headgear', ('headgear',)),
    ('personas', 'vf_skins', ('persona_scout', 'persona_rig')),
    ('deaths', 'vf_deaths', ('persona_death', 'persona_death_gibs')),
    ('r01', 'vf_r01', ('r01_rig', 'r01_rig_side', 'r01_rig_top', 'r01_rig_fg', 'r01_rig_side_fg', 'r01_rig_top_fg', 'r01_fp_gloves', 'r01_fp_sleeves')),
    ('third-person', 'vf_r01', ('r01_tp', 'r01_tp_side', 'r01_tp_top')),
    ('traversal', 'vf_traversal', ('r01_rig_tr', 'r01_rig_side_tr', 'r01_rig_top_tr', 'r01_rig_fg_tr', 'r01_rig_side_fg_tr', 'r01_rig_top_fg_tr', 'slide_legs', 'ledge_gloves', 'ledge_sleeves')),
)


def deployment_files(root=ROOT,sdk=None):
    """Canonical generated assets and executable contracts that must be delivered."""
    root=Path(root)
    result=[(root/source,Path(target)) for source,target in (
        ('build/client/client.dll','cl_dlls/client.dll'),('build/server/hl.dll','dlls/hl.dll'),
        ('data/equipment.txt','vf/equipment.txt'),('data/r01_styles.txt','vf/r01_styles.txt'),
        ('generated/visual_skins/skins.txt','vf/skins.txt'),('data/effects.json','vf/effects.json'),
        ('data/status_decals.json','vf/status_decals.json'),('data/weapon_fx.json','vf/weapon_fx.json'),('generated/weapon-fx/decals.wad','decals.wad'),
        ('version.json','vf/version.json'))]
    from game_profiles import MAPS
    from build_atmosphere import runtime_files as atmosphere_files
    result += atmosphere_files(root/'generated/atmosphere')
    result += [(root/'generated'/row['source']/(name+'.bsp'),Path('maps')/(name+'.bsp'))
               for name,row in MAPS.items()]
    sdk=Path(sdk or (os.environ.get('VF_RELEASE_SDK',root/'build')if root.resolve()==ROOT.resolve()else root/'build'))
    result[0]=(sdk/'client/client.dll',result[0][1]);result[1]=(sdk/'server/hl.dll',result[1][1])
    result.append((root.parent/'network/delta.lst',Path('delta.lst')))
    for source,destination,required in MODEL_GROUPS:
        folder=root/'generated'/source
        paths=set(folder.glob('*.mdl')) | {folder/(name+'.mdl') for name in required}
        if source=='r01':
            manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
            paths |= {folder/(p['id']+'.mdl') for p in manifest['pieces']}
        result += [(p,Path('models')/destination/p.name) for p in sorted(paths)]
    for source,target in [('generated/effects','sprites/vf_effects'),('generated/weapon-fx/sprites','sprites/vf_weaponfx'),('generated/weapon-fx/sound','sound/vf_weaponfx')]:
        folder=root/source
        paths=[p for p in folder.rglob('*') if p.is_file()]
        if not paths:raise FileNotFoundError(f'Missing generated release assets: {folder}')
        result += [(p,Path(target)/p.relative_to(folder)) for p in paths]
    status=json.loads((root/'data/status_decals.json').read_text(encoding='utf-8-sig'))
    for effect in status['effects']:
        for suffix in ('',):
            name=effect['id']+suffix+'.spr'
            result.append((root/'generated/status-decals'/name,Path('sprites/vf_status')/name))
    bank=root/'assets/audio/operator-deaths';manifest_path=bank/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    result.append((manifest_path,Path('vf/death-voice-manifest.json')))
    for clip in manifest['clips']:
        result.append((bank/clip['path'].removeprefix('vf_deaths/'),Path('sound')/clip['path']))
    sfx=root/'generated/death-sfx';manifest_path=sfx/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    result.append((manifest_path,Path('vf/death-sfx-manifest.json')))
    for clip in manifest['clips']:
        result.append((sfx/'sound'/Path(clip['path']).name,Path('sound')/clip['path']))
    sfx=root/'generated/traversal-sfx';manifest_path=sfx/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    result.append((manifest_path,Path('vf/traversal-sfx-manifest.json')))
    for clip in manifest['clips']:
        result.append((sfx/Path(clip['path']).name,Path('sound')/clip['path']))
    # Headgear voice/foley and filtered derivatives are part of the normal release.
    bank=root/'generated/headgear-audio';manifest_path=bank/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    result.append((manifest_path,Path('vf/headgear-audio.json')))
    for clip in manifest['clips']+manifest['sounds']+manifest['muffled']:
        result.append((bank/'sound'/clip['path'],Path('sound')/clip['path']))
    bank=root/'generated/headgear-hud';manifest_path=bank/'manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    result.append((manifest_path,Path('vf/headgear-hud.json')))
    for asset in manifest['assets']:
        name=asset['id']+'.spr'
        result.append((bank/name,Path('sprites/vf_headgear_hud')/name))
    # Optional distal thumb joint keeps its rest transform on legacy clips.
    # Source authoring rigs retain their original skeleton contracts; the
    # delivered carriers and clothing share the appended articulation.
    from thumb_articulation import source_with_thumb
    return [(source_with_thumb(source)if source.suffix=='.mdl'and len(target.parts)>1 and target.parts[1]in('vf_r01','vf_skins')else source,target)for source,target in result]


def prepare_thumb_models(destination):
    """Normalize delivered models after the launcher copies authoring assets."""
    from thumb_articulation import upgrade
    for folder,pattern in [('vf_r01','r01_tp*.mdl'),('vf_skins','*.mdl')]:
        for path in (Path(destination)/'models'/folder).glob(pattern):upgrade(path)


def verify_deployment(destination,root=ROOT,sdk=None):
    files=deployment_files(root,sdk)
    for source,target in files:
        installed=Path(destination)/target
        if not source.is_file() or not installed.is_file():
            raise FileNotFoundError(f'Missing release artifact: {source} -> {installed}')
        if hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(installed.read_bytes()).digest():
            raise RuntimeError(f'Deployed artifact differs: {installed}')
    return dict(files=len(files),models=sum(source.suffix=='.mdl' for source,_ in files))
