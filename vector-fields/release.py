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
    required=3 if b'v3 connected' in client.read_bytes() else 2
    manifest=engine/'vector-engine-build.json'
    actual=json.loads(manifest.read_text(encoding='utf-8-sig')).get('extension_version') if manifest.exists() else None
    if actual==required and b'VFStatus arms: renderer=1' in client.read_bytes() and json.loads(manifest.read_text(encoding='utf-8-sig')).get('status_viewmodel_version',0)<1:
        raise RuntimeError('The client requires the tested arm-only status renderer. Relaunch with Jouer - Vector Fields.cmd to install its pending update.')
    if actual!=required:
        raise RuntimeError(f'Native renderer/client versions differ ({actual}/{required}). Rebuild both with vector-fields/build-engine.ps1 and vector-fields/build.ps1 before deploying. Existing installed files were not changed.')


def prepare_native_renderer_update(engine,client,update=None):
    """Apply the verified renderer update before the classic launcher stages a mod."""
    if not client.exists() or b'VFStatus arms: renderer=1' not in client.read_bytes():return False
    manifest=engine/'vector-engine-build.json'
    installed=json.loads(manifest.read_text(encoding='utf-8-sig')) if manifest.exists() else {}
    if installed.get('status_viewmodel_version',0)>=1:return False
    update=update or ROOT/'build/status-renderer-update'
    metadata=update/'vector-engine-build.json'
    if not metadata.exists():raise RuntimeError('Build the status renderer with vector-fields/build-engine.ps1 before launching this client.')
    tested=json.loads(metadata.read_text(encoding='utf-8-sig'))
    names=('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')
    if tested.get('extension_version')!=3 or tested.get('status_viewmodel_version')!=1 or not tested.get('status_feedback_verified'):
        raise RuntimeError('The pending renderer has not passed status feedback validation.')
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
        raise RuntimeError('Close the running Vector Fields game, then use Jouer - Vector Fields.cmd again to load the new status visuals.') from error
    return True


MODEL_GROUPS = (
    ('personas', 'vf_skins', ('persona_scout', 'persona_rig')),
    ('deaths', 'vf_deaths', ('persona_death', 'persona_death_gibs')),
    ('r01', 'vf_r01', ('r01_rig', 'r01_rig_side', 'r01_rig_top', 'r01_rig_fg', 'r01_rig_side_fg', 'r01_rig_top_fg', 'r01_fp_gloves', 'r01_fp_sleeves')),
    ('third-person', 'vf_r01', ('r01_tp', 'r01_tp_side', 'r01_tp_top')),
)


def deployment_files(root=ROOT):
    """Canonical generated assets and executable contracts that must be delivered."""
    root=Path(root)
    result=[(root/source,Path(target)) for source,target in (
        ('build/client/client.dll','cl_dlls/client.dll'),('build/server/hl.dll','dlls/hl.dll'),
        ('generated/test-room/vf_range.bsp','maps/vf_range.bsp'),
        ('generated/weapon-fx/range/vf_fx_range.bsp','maps/vf_fx_range.bsp'),
        ('data/equipment.txt','vf/equipment.txt'),('data/r01_styles.txt','vf/r01_styles.txt'),
        ('generated/visual_skins/skins.txt','vf/skins.txt'),('data/effects.json','vf/effects.json'),
        ('data/status_decals.json','vf/status_decals.json'),('data/weapon_fx.json','vf/weapon_fx.json'),('generated/weapon-fx/decals.wad','decals.wad'),
        ('version.json','vf/version.json'))]
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
    return result


def verify_deployment(destination,root=ROOT):
    files=deployment_files(root)
    for source,target in files:
        installed=Path(destination)/target
        if not source.is_file() or not installed.is_file():
            raise FileNotFoundError(f'Missing release artifact: {source} -> {installed}')
        if hashlib.sha256(source.read_bytes()).digest()!=hashlib.sha256(installed.read_bytes()).digest():
            raise RuntimeError(f'Deployed artifact differs: {installed}')
    return dict(files=len(files),models=sum(source.suffix=='.mdl' for source,_ in files))
