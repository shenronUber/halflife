"""Export the game's compiled deaths, effect sprites and compressed cries offline."""
import base64
import hashlib
import io
import json
import struct
import wave
from pathlib import Path

import numpy as np
from PIL import Image
from animation_assets import sequence_frames, globals_of
from studio_assets import Studio

ROOT = Path(__file__).resolve().parent


def sprite_frames(path):
    data = path.read_bytes()
    magic, version, _, fmt, _, _, _, count, _, _ = struct.unpack_from('<4siiifiiifi', data)
    assert magic == b'IDSP' and version == 2, path
    colors = struct.unpack_from('<H', data, 40)[0]
    palette = np.frombuffer(data, dtype=np.uint8, count=colors * 3, offset=42).reshape(-1, 3)
    offset = 42 + colors * 3
    frames = []
    for _ in range(count):
        frame_type, _, _, width, height = struct.unpack_from('<5i', data, offset)
        assert frame_type == 0, 'Grouped sprites are not supported'
        offset += 20
        pixels = np.frombuffer(data, dtype=np.uint8, count=width * height, offset=offset).reshape(height, width)
        offset += width * height
        rgba = np.empty((height, width, 4), dtype=np.uint8)
        rgba[:, :, :3] = palette[255] if fmt == 2 else palette[pixels]
        rgba[:, :, 3] = pixels if fmt == 2 else (np.where(pixels == 255, 0, 255) if fmt == 3 else 255)
        stream = io.BytesIO()
        Image.fromarray(rgba).save(stream, format='PNG')
        frames.append('data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode('ascii'))
    assert offset == len(data), path
    return frames


def export_deaths(exporter, scenes, make_clip):
    atlas = json.loads((ROOT / 'assets/animations/death-atlas.json').read_text(encoding='utf-8'))
    visual = json.loads((ROOT / 'generated/deaths/manifest.json').read_text(encoding='utf-8'))
    model = Studio(ROOT / 'generated/deaths/persona_death.mdl')
    from inspector_death_emissions import export_emissions
    models, emissions = export_emissions(exporter, model, visual, sprite_frames)
    clips = {}
    for motion in atlas['motions']:
        if motion['sequence']:
            clips[motion['id']] = make_clip(model, motion['sequence'], motion['label'])
    historical = {
        'die_simple': 'Historique · chute simple',
        'die_backwards1': 'Historique · recul court',
        'die_backwards': 'Historique · chute en arrière',
        'die_forwards': 'Historique · chute en avant',
        'die_headshot': 'Historique · impact à la tête',
        'gutshot': 'Historique · impact au ventre',
    }
    used = {c['source'] for c in clips.values()}
    for name in model.sequences[18:25]:
        if name not in used:
            clips[name] = make_clip(model, name, historical.get(name, 'Historique · ' + name))
    # Match the native corpse emitter's 33-point chest/head centre tracks.
    for value in clips.values():
        poses = sequence_frames(model, value['source'])
        centers = np.array([(g[11, :3, 3] + g[13, :3, 3]) * .5
                            for g in (globals_of(p, model.parents) for p in poses)])
        sampled = []
        for t in np.linspace(0, len(poses) - 1, 33):
            i = min(int(t), len(poses) - 2)
            sampled.append(centers[i] * (1 - (t - i)) + centers[i + 1] * (t - i))
        value['effect_centers'] = np.round(sampled, 6).tolist()
    scenes['deaths'] = dict(label='Morts et effets', death=True, bones=model.names, parents=model.parents,
                            models=models, magazines=[], hand=17, index=[], clips=clips,
                            note='Animations compilées du jeu, effets du même catalogue et cris compressés. '
                                 'La lecture joue une seule mort et conserve la pose finale. '
                                 'La voix et la tenue se choisissent indépendamment.')
    audio_root = ROOT / 'assets/audio/operator-deaths'
    bank = json.loads((audio_root / 'manifest.json').read_text(encoding='utf-8'))
    script = json.loads((ROOT / 'data/death_voices.json').read_text(encoding='utf-8'))
    accents = dict(rocco='Italien', lucien='Français', diego='Espagnol', viktor='Russe', otto='Allemand', nikos='Grec')
    actors = [dict(id=a['id'], name=a['name'], accent=accents[a['id']]) for a in bank['actors']]
    cries = {}
    for value in bank['clips']:
        path = audio_root / value['path'].removeprefix('vf_deaths/')
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == value['sha256'], path
        with wave.open(io.BytesIO(data)) as wav:
            assert (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) == (1, 11025, 1), path
            duration = wav.getnframes() / wav.getframerate()
            assert 0 < duration <= 3, path
        cries.setdefault(value['actor'], {})[value['cause']] = dict(
            src='data:audio/wav;base64,' + base64.b64encode(data).decode('ascii'),
            duration=round(duration, 6), path=value['path'], sha256=value['sha256'])
    assert len(cries) == 6 and all(len(c) == 17 for c in cries.values())
    effects = json.loads((ROOT / 'data/effects.json').read_text(encoding='utf-8'))['effects']
    causes = [dict(id=c['id'], name=c['name'], kind=c['kind']) for c in script['causes']]
    causes += [dict(id=e['id'], name=e['name'] + ' · cri standard', kind=2) for e in effects if e['kind'] == 2]
    sprites = ['bubble', 'hotglow', 'steam1', 'fire', 'white']
    result = dict(emissions=emissions, actors=actors, causes=causes, cries=cries, profiles=atlas['profiles'],
                  effects={e['id']: dict(id=e['id'], layers=e['layers'], visual=e['visual']) for e in effects},
                  sprites=[sprite_frames(ROOT / 'generated/effects' / (s + '.spr')) for s in sprites])
    record = dict(model=str(model.path), model_sha256=hashlib.sha256(model.data).hexdigest(),
                  voices=6, cries=102, causes=22, profiles=16, sprite_frames=[len(f) for f in result['sprites']],
                  compressed_audio=dict(channels=1, hz=11025, bits=8, max_seconds=3),
                  motions={k: dict(sequence=c['source'], frames=len(c['frames']), fps=c['fps']) for k, c in clips.items()},
                  death_sounds=16, detachment_sounds=17, fragment_meshes=20, blood_decals=6,
                  emission_sources=emissions['sources'],
                  limitations=['Offline physics against a flat floor; level collisions require the game.'])
    return result, record
