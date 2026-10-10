"""Content-based generation cache. Inputs and outputs are both verified."""
import hashlib
import json
import struct
from pathlib import Path
ROOT = Path(__file__).resolve().parent


def fingerprint(paths):
    digest = hashlib.sha256()
    for path in sorted(set(Path(p).resolve() for p in paths)):
        if not path.is_file():
            raise FileNotFoundError(f'Missing build input: {path}')
        name = path.as_posix().encode('utf-8')
        data = path.read_bytes()
        digest.update(struct.pack('<Q', len(name)) + name)
        digest.update(struct.pack('<Q', len(data)) + data)
    return digest.hexdigest()


def compiler_inputs():
    return [Path(__file__), ROOT/'build_modular.py', ROOT/'build_skins.py', ROOT/'studio_assets.py',
            ROOT.parent/'weapon-lab/mix_models.py', ROOT/'generated/tfc-soldier/soldier_reference_2.smd', ROOT/'generated/tfc-soldier/look_idle.smd', ROOT.parent/'asset-probe/tools/studiomdl.exe']


def record(inputs_sha256, outputs):
    paths = sorted(set(Path(p).resolve() for p in outputs))
    if not paths:
        raise ValueError('A build stage must declare its outputs')
    return dict(inputs_sha256=inputs_sha256, outputs={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})


def current(state, inputs_sha256):
    if not state or state.get('inputs_sha256') != inputs_sha256 or not state.get('outputs'):
        return False
    return all(Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest() == expected
               for p, expected in state['outputs'].items())


def read(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (FileNotFoundError, ValueError):
        return {}


def write(path, state):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(state, indent=2), encoding='utf-8')
    temporary.replace(path)
