"""Check the compiled files, not just the generated source descriptions."""
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated'
model = (OUT / 'vf_modular.mdl').read_bytes()
assert model[:4] == b'IDST'
assert struct.unpack_from('<i', model, 4)[0] == 10
assert struct.unpack_from('<i', model, 72)[0] == len(model)
bones = struct.unpack_from('<i', model, 140)[0]
sequences = struct.unpack_from('<i', model, 164)[0]
textures = struct.unpack_from('<i', model, 180)[0]
skinrefs, skins, skin_offset = struct.unpack_from('<3i', model, 192)
body_count, body_offset = struct.unpack_from('<2i', model, 204)
parts = []
combinations = 1
for i in range(body_count):
    name, count, base, offset = struct.unpack_from('<64s3i', model, body_offset + i*76)
    assert base == combinations
    assert 0 <= offset < len(model)
    combinations *= count
    parts.append({'name': name.split(b'\0')[0].decode(), 'alternatives': count, 'base': base})
assert [p['alternatives'] for p in parts] == [1, 2, 2]
assert (bones, sequences, textures, skins) == (1, 1, 2, 2)
skin_table = struct.unpack_from('<' + 'h'*(skinrefs*skins), model, skin_offset)
assert all(0 <= value < textures for value in skin_table)

bsp = (OUT / 'vf_asset_lab.bsp').read_bytes()
assert struct.unpack_from('<i', bsp)[0] == 30
lumps = [struct.unpack_from('<2i', bsp, 4 + i*8) for i in range(15)]
for offset, length in lumps:
    assert 0 <= offset <= len(bsp) and offset+length <= len(bsp)
offset, length = lumps[0]
entities = bsp[offset:offset+length].decode('ascii').rstrip('\0')
assert entities.count('"info_player_deathmatch"') == 4
assert entities.count('"info_player_start"') == 1
assert lumps[7][1] > 0 and lumps[7][1] % 20 == 0  # faces
assert lumps[8][1] > 0  # lighting
assert lumps[4][1] > 0  # visibility
log = (OUT / 'vf_asset_lab.log').read_text(errors='replace')
assert 'leaked' not in log.lower()
assert 'Error:' not in log
result = {
    'model': {'file': 'generated/vf_modular.mdl', 'bytes': len(model), 'format': 'IDST v10',
              'bodygroups': parts, 'geometry_combinations': combinations,
              'skins': skins, 'display_combinations': combinations*skins,
              'animation': 'Single static idle frame; no hands, firing or reload'},
    'map': {'file': 'generated/vf_asset_lab.bsp', 'bytes': len(bsp), 'format': 'BSP v30',
            'multiplayer_spawns': 4, 'faces': lumps[7][1] // 20,
            'lightmap_bytes': lumps[8][1], 'visibility_bytes': lumps[4][1],
            'compiled_stages': ['CSG', 'BSP', 'VIS', 'RAD'], 'leak_reported': False},
    'validation': 'Compilation and binary structure verified; not loaded in game.',
    'textures': 'Read from the local Half-Life installation; generated assets are gitignored.'
}
(ROOT / 'results.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
print(json.dumps(result, indent=2))
