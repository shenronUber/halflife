"""Stage a disposable native headgear review without changing installed assets."""
import os
import shutil
from pathlib import Path
from native_workspace import engine_path, shared_copy, private_copy

ROOT=Path(__file__).resolve().parent


def asset_library():
    """Read stock resources from the original Half-Life library, including gfx.wad."""
    return Path('F:/SteamLibrary/steamapps/common/Half-Life')


def stage(name='headgear-native',candidate=None):
    base=ROOT.parent/'runtime/vector-engine'
    engine=engine_path(ROOT/'build'/name)
    mod=engine/'vf_headgear_test'
    engine.mkdir(parents=True,exist_ok=True)
    (engine/'valve').mkdir(exist_ok=True)
    binary_base=Path(candidate)/'engine' if candidate else base
    for p in binary_base.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.exe'):
            private_copy(p,engine/p.name)
    folders=('tfc_assets','vf_visual') if os.environ.get('VF_HEADGEAR_READONLY_ASSETS','1')=='1' else ('valve','tfc_assets','vf_visual')
    for folder in folders:
        # Candidate reviews install the complete current model groups below.
        # Avoid copying years of unused workshop models into that fixture.
        ignored=('scrshots','save','*.log','.fontcache')
        if candidate and folder=='vf_visual' and os.environ.get('VF_HEADGEAR_READONLY_ASSETS','1')=='1':
            ignored+=('models',)
        shutil.copytree(base/folder,engine/folder,dirs_exist_ok=True,copy_function=shared_copy,
                        ignore=shutil.ignore_patterns(*ignored))
        if 'models' in ignored:
            # The legacy root vf_operator.mdl is still precached before the
            # current assembled player takes over; keep those root carriers.
            for model in (base/folder/'models').glob('*.mdl'):
                shared_copy(model,engine/folder/'models'/model.name)
    for folder in ('cl_dlls','dlls','vf','models/vf_headgear','scrshots'):
        (mod/folder).mkdir(parents=True,exist_ok=True)
    binaries=Path(candidate) if candidate else ROOT/'build'
    private_copy(binaries/'client/client.dll',mod/'cl_dlls/client.dll')
    private_copy(binaries/'server/hl.dll',mod/'dlls/hl.dll')
    private_copy(ROOT/'data/equipment.txt',mod/'vf/equipment.txt')
    private_copy(ROOT/'data/r01_styles.txt',mod/'vf/r01_styles.txt')
    private_copy(ROOT/'generated/visual_skins/skins.txt',mod/'vf/skins.txt')
    private_copy(ROOT/'generated/headgear/headgear.mdl',mod/'models/vf_headgear/headgear.mdl')
    if candidate:
        from release import MODEL_GROUPS
        for source,target,_ in MODEL_GROUPS:
            for asset in (ROOT/'generated'/source).glob('*.mdl'):
                shared_copy(asset,mod/'models'/target/asset.name)
        private_copy(ROOT.parent/'network/delta.lst',mod/'delta.lst')
    (mod/'vf/native_engine.txt').write_text('isolated headgear review\n')
    from headgear_audio import deploy as deploy_headgear_audio
    deploy_headgear_audio(mod)
    from build_headgear_hud import deploy as deploy_headgear_hud
    deploy_headgear_hud(mod)
    (mod/'gameinfo.txt').write_text('title "Vector Fields - Headgear review"\nbasedir "valve"\nfallback_dir "vf_visual"\ngamedll "dlls/hl.dll"\ndllpath "cl_dlls"\ngamemode "normal"\nmax_edicts "2048"\n')
    from release import check_native_interface
    check_native_interface(binary_base,binaries/'client/client.dll')
    return engine,mod
