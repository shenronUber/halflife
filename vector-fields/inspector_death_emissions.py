"""Native death additions for the offline workshop: wounds, fragments, blood and SFX."""
import ast
import base64
import hashlib
import io
import json
import re
import struct
import wave
from pathlib import Path

import numpy as np
from PIL import Image
from animation_assets import sequence_frames, globals_of
from studio_assets import Studio

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def legacy_resource(relative):
    # Use the same local Half-Life installation as the game's deployment tool.
    tree = ast.parse((PROJECT/'weapon-lab/play.py').read_text(encoding='utf-8'))
    assignment = next(n for n in tree.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'HALF_LIFE' for t in n.targets))
    installation = Path(ast.literal_eval(assignment.value.args[0]))
    candidates = [PROJECT/'runtime/vector-engine'/folder/relative for folder in ('vf_visual', 'cs_assets', 'valve')]
    candidates.append(installation/'valve'/relative)
    return next(p for p in candidates if p.exists())


def sources():
    return [Path(__file__), ROOT/'data/death_sounds.json', ROOT/'generated/death-sfx/manifest.json',
            *sorted((ROOT/'generated/death-sfx/sound').glob('*.wav')),
            PROJECT/'cl_dll/vf_death.cpp', PROJECT/'cl_dll/vf_effects.cpp',
            PROJECT/'cl_dll/vf_effect_math.h', PROJECT/'dlls/vf_death.cpp',
            PROJECT/'dlls/combat.cpp', PROJECT/'dlls/util.cpp', PROJECT/'dlls/vf_voice.cpp',
            PROJECT/'game_shared/vf_death_sfx_catalog.h', PROJECT/'game_shared/vf_fragment_geometry.h',
            PROJECT/'runtime/engine-source/engine/server/sv_phys.c', PROJECT/'weapon-lab/play.py',
            legacy_resource('sprites/blood.spr'), legacy_resource('sprites/lgtning.spr'),
            legacy_resource('decals.wad')]


def blood_decals(path):
    """WAD3 gradient palette = colour #255 and index as alpha, as img_wad.c."""
    data = path.read_bytes()
    magic, count, offset = struct.unpack_from('<4sii', data)
    assert magic == b'WAD3'
    result = {}
    for i in range(count):
        pos, size, _, kind, compression, _, raw_name = struct.unpack_from('<iiiBBH16s', data, offset+i*32)
        name = raw_name.split(b'\0')[0].decode('latin1').lower()
        if name not in ['{blood'+str(n) for n in range(1, 7)]:
            continue
        assert kind == 67 and compression == 0
        lump = data[pos:pos+size]
        _, width, height, first, _, _, _ = struct.unpack_from('<16s6i', lump)
        pal_offset = first+width*height*85//64
        assert struct.unpack_from('<H', lump, pal_offset)[0] == 256
        palette = np.frombuffer(lump, dtype=np.uint8, count=768, offset=pal_offset+2).reshape(256, 3)
        pixels = np.frombuffer(lump, dtype=np.uint8, count=width*height, offset=first).reshape(height, width)
        rgba = np.empty((height, width, 4), dtype=np.uint8)
        masked = list(palette[255]) == [0, 0, 255]
        rgba[:, :, :3] = palette[pixels] if masked else palette[255]
        rgba[:, :, 3] = np.where(pixels == 255, 0, 255) if masked else pixels
        out = io.BytesIO(); Image.fromarray(rgba).save(out, format='PNG')
        result[name] = dict(name=name, width=width, height=height,
                            src='data:image/png;base64,'+base64.b64encode(out.getvalue()).decode('ascii'))
    assert len(result) == 6
    return [result['{blood'+str(i)] for i in range(1, 7)]


def native_rules():
    client = (PROJECT/'cl_dll/vf_death.cpp').read_text()
    server = (PROJECT/'dlls/vf_death.cpp').read_text()
    def number(text, pattern):
        match = re.search(pattern, text)
        assert match, 'Death emission rule changed: '+pattern
        return float(match.group(1))
    # Constants come from the running game's sources; changed rules invalidate
    # the export cache instead of leaving an old preview silently in place.
    return dict(capacity=int(number(client, r'TrailCapacity=(\d+)')),
                burst_count=int(number(client, r'n<(\d+);\+\+n\)EmitBlood')),
                trail_seconds=number(client, r'age>([\d.]+)f\)continue'),
                trail_interval=number(client, r'f.next=now\+([\d.]+)f'),
                emission_limit=int(number(client, r'emits<(\d+)')),
                particle_min_seconds=number(client, r't.until=now\+Random\(([\d.]+)f,'),
                particle_max_seconds=number(client, r't.until=now\+Random\([\d.]+f,([\d.]+)f\)'),
                blood_gravity=number(client, r't.gravity=(-[\d.]+)f;t.draw.blood'),
                burst_spread=number(client, r'float spread=burst\?([\d.]+)f'),
                trail_spread=number(client, r'float spread=burst\?[\d.]+f:([\d.]+)f'),
                corpse_seconds=number(server, r'const float lifetime=([\d.]+)'),
                fragment_seconds=number(server, r'until=started\+([\d.]+)'),
                death_volume=number(server, r'vf_death_sfx_volume","([\d.]+)"'),
                dismember_volume=number(server, r'vf_dismember_sfx_volume","([\d.]+)"'),
                gravity=800, friction=.55, floor_radius=2, impact_decal_budget=5,
                voice_volume=.85, dt=1/60)


def export_emissions(exporter, corpse, visual, sprite_frames):
    models = []
    for i, name in enumerate(visual['bodygroups']):
        choices = {j: -1 for j in range(len(corpse.parts))}; choices[i+1] = 1
        key = exporter.model('death_'+name, corpse, corpse.names, 'body', choices=choices)
        exporter.models[key].update(region=visual['regions'][i], wound=i>=visual['clothing_groups'])
        models.append(key)
    gibs = Studio(ROOT/'generated/deaths/persona_death_gibs.mdl')
    fragments = []
    for i, meta in enumerate(visual['fragments']):
        key = exporter.model('death_fragment_'+str(i), gibs, corpse.names, 'body', choices={0:i}, socket=corpse.names[0])
        exporter.models[key].update(fragment=i, region=meta['region'])
        models.append(key)
        points = np.array([row[:3] for group in exporter.models[key]['groups'] for row in group['vertices']])
        fragments.append(dict(body=i, region=meta['region'], whole=i>=15,
                              rest_pitch=meta.get('rest_pitch', 0),
                              floor_offset=meta.get('floor_offset', float(-points[:, 2].min()+.1))))
    victim = Studio(ROOT/'generated/personas/persona_rig.mdl')
    pose = globals_of(sequence_frames(victim, 'ref_aim_mp5')[0], victim.parents)
    spawn_points = {str(bit): np.round(pose[bone, :3, 3]+[0, 0, 36], 6).tolist()
                    for bit, bone in zip([1, 2, 4, 8, 16], [13, 16, 23, 3, 6])}
    sfx = {}
    bank = json.loads((ROOT/'generated/death-sfx/manifest.json').read_text(encoding='utf-8'))
    for c in bank['clips']:
        path = ROOT/'generated/death-sfx/sound'/(c['id']+'.wav')
        data = path.read_bytes(); assert hashlib.sha256(data).hexdigest() == c['sha256']
        with wave.open(io.BytesIO(data)) as wav:
            assert (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) == (1, 22050, 2)
            duration = wav.getnframes()/wav.getframerate()
        sfx.setdefault(c['effect'], {})[c['layer']] = dict(
            src='data:audio/wav;base64,'+base64.b64encode(data).decode('ascii'),
            duration=duration, path=c['path'], sha256=c['sha256'])
    assert len(sfx) == 17 and sum(map(len, sfx.values())) == 33
    assert 'death' not in sfx['standard']
    sprite_path = legacy_resource('sprites/blood.spr'); lightning_path = legacy_resource('sprites/lgtning.spr')
    decal_path = legacy_resource('decals.wad')
    result = dict(rules=native_rules(), fragments=fragments, spawn_points=spawn_points,
                  blood_sprite=sprite_frames(sprite_path), lightning_sprite=sprite_frames(lightning_path),
                  decals=blood_decals(decal_path), sounds=sfx,
                  masks=[dict(id=id, name=name, mask=mask) for id, name, mask in [
                      ('none','Corps entier',0),('head','Tête',1),('left_arm','Bras gauche',2),
                      ('right_arm','Bras droit',4),('left_leg','Jambe gauche',8),
                      ('right_leg','Jambe droite',16),('all','Tous les membres',31)]],
                  sources=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sources()])
    return models, result
