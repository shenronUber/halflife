"""Measure installed BSP v30 maps without counting imported runtime copies.

Bounds are geometric envelopes, not reachable navigation area. In particular,
excluding sky faces does not remove distant scenery or sealed rooms.
"""
import argparse
import csv
import hashlib
import json
import re
import statistics
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEAM = Path('F:/SteamLibrary/steamapps/common/Half-Life')


def measure(data):
    if len(data) < 124 or struct.unpack_from('<i', data)[0] != 30:
        raise ValueError('Expected GoldSrc BSP v30')
    lumps = [struct.unpack_from('<ii', data, 4 + i * 8) for i in range(15)]
    if any(o < 0 or n < 0 or o + n > len(data) for o, n in lumps):
        raise ValueError('Invalid BSP lump bounds')

    def records(index, fmt):
        offset, length = lumps[index]
        size = struct.calcsize(fmt)
        if length % size:
            raise ValueError('Invalid BSP record size')
        return list(struct.iter_unpack(fmt, data[offset:offset + length]))

    models = records(14, '<9f7i')
    vertices = records(3, '<3f')
    faces = records(7, '<Hhihh4Bi')
    edges = records(12, '<2H')
    surfedges = records(13, '<i')
    texinfo = records(6, '<8f2i')
    offset, length = lumps[2]
    count = struct.unpack_from('<i', data, offset)[0]
    names = []
    for i in range(count):
        position = struct.unpack_from('<i', data, offset + 4 + i * 4)[0]
        names.append(data[offset + position:offset + position + 16].split(b'\0')[0].decode('latin1').lower() if position >= 0 else '')
    chosen = set()
    sky_faces = 0
    # World model only: brush submodels can be local-space geometry.
    for face in faces[models[0][-2]:models[0][-2] + models[0][-1]]:
        first, number, texture = face[2:5]
        name = names[texinfo[texture][8]]
        if name.startswith('sky') or name in {'clip', 'origin', 'null', 'hint', 'skip'}:
            sky_faces += 1
            continue
        for (signed,) in surfedges[first:first + number]:
            chosen.add(edges[abs(signed)][0 if signed >= 0 else 1])
    if not chosen:
        raise ValueError('World has no non-sky faces')
    lo = [min(vertices[i][axis] for i in chosen) for axis in range(3)]
    hi = [max(vertices[i][axis] for i in chosen) for axis in range(3)]
    dimensions = [round(hi[i] - lo[i], 2) for i in range(3)]
    envelope = [round(models[0][i + 3] - models[0][i], 2) for i in range(3)]
    return dict(non_sky_min=lo, non_sky_max=hi, dimensions=dimensions,
                long_side=max(dimensions[:2]), short_side=min(dimensions[:2]),
                footprint=dimensions[0] * dimensions[1], world_envelope=envelope,
                world_faces=models[0][-1], all_faces=len(faces), brush_models=len(models) - 1,
                excluded_faces=sky_faces, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def survey(source=STEAM, output=ROOT / 'docs/validation/modular/maps'):
    rows = []
    seen = set()
    for game in ('valve', 'cstrike', 'tfc', 'bshift', 'gearbox'):
        for path in sorted((Path(source) / game / 'maps').glob('*.bsp')):
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            cohort = game
            if game == 'valve':
                cohort = 'hl_campaign_training' if re.match(r'^(c\d|t\d|hldemo)', path.stem) else 'hl_multiplayer'
            rows.append(dict(game=game, cohort=cohort, map=path.stem, source=str(path), **measure(data)))
    groups = {}
    for cohort in ('hl_campaign_training', 'hl_multiplayer', 'cstrike', 'tfc', 'bshift', 'gearbox'):
        group = [row for row in rows if row['cohort'] == cohort]
        if not group:
            continue
        groups[cohort] = dict(count=len(group))
        for metric in ('long_side', 'short_side', 'footprint', 'all_faces', 'brush_models'):
            values = [row[metric] for row in group]
            groups[cohort][metric] = dict(mean=round(statistics.mean(values), 2), median=round(statistics.median(values), 2), min=min(values), max=max(values))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = dict(source=str(source), count=len(rows), units='native engine units',
                  method='World-model face vertices excluding sky/clip/origin/null/hint/skip. Envelopes include scenery; not navigable area. One original BSP per SHA256; runtime imports excluded.',
                  cohorts=groups, maps=rows)
    (output / 'dimensions.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    with (output / 'dimensions.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        writer.writerow(('game', 'cohort', 'map', 'x', 'y', 'z', 'long_side', 'short_side', 'faces', 'brush_models', 'source'))
        for row in rows:
            writer.writerow((row['game'], row['cohort'], row['map'], *row['dimensions'], row['long_side'], row['short_side'], row['all_faces'], row['brush_models'], row['source']))
    print(json.dumps(dict(count=len(rows), cohorts=groups), indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=STEAM)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/validation/modular/maps')
    args = parser.parse_args()
    survey(args.source, args.output)
