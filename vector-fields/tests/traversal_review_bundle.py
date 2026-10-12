"""Review a new renderer with the installed, immutable engine core."""
import hashlib,json
from pathlib import Path
from traversal_multiplayer_test import prepare
from native_workspace import private_copy
from release import check_native_interface
ROOT=Path(__file__).resolve().parents[1]

def review_assets(mod):
    paths=[p for folder in ('vf_traversal','vf_r01')for p in (mod/'models'/folder).glob('*.mdl')]
    # The concurrent helmet slot upgrade changes the catalog/protocol and
    # optional attachment rig. Keep them tied to the filmed DLL pair too.
    paths += [p for p in (mod/'vf/equipment.txt',mod/'models/vf_headgear/headgear.mdl')if p.is_file()]
    return {str(p.relative_to(mod)):hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}

def prepare_review(name):
    installed=ROOT.parent/'runtime/vector-engine';candidate=installed
    engine,mod=prepare(name,renderer=candidate)
    helmet=ROOT/'generated/headgear/headgear.mdl'
    if helmet.is_file():
        (mod/'models/vf_headgear').mkdir(parents=True,exist_ok=True)
        private_copy(helmet,mod/'models/vf_headgear/headgear.mdl')
    metadata=json.loads((candidate/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
    old=json.loads((installed/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
    # The engine bridges the versioned renderer API to the client. An ABI
    # upgrade also needs that bridge rebuilt; retaining an older xash.dll
    # would silently disconnect the modular avatar despite valid metadata.
    for name in ('xash3d.exe','xash.dll','xash.exe','SDL2.dll'):
        if name!='xash.dll' or old.get('extension_version')==metadata['extension_version']:
            private_copy(installed/name,engine/name)
            metadata['binaries'][name]=hashlib.sha256((engine/name).read_bytes()).hexdigest().upper()
    (engine/'vector-engine-build.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    check_native_interface(engine,mod/'cl_dlls/client.dll')
    return engine,mod
