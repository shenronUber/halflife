"""Anatomical UV charts for the full-volume R-01 first-person hands.

Only pixels from the existing character atlases are used. Rectifying their UV
islands before packing preserves their native detail and avoids grey background.
Gloves and sleeves remain independently skinned, on the existing animated bones.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image
import build_modular as base
from studio_assets import Studio
import build_cache

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated/r01'
ASSETS = ROOT / 'assets/personas'
# Packed rectangles, in pixels. Finger/cuff charts contain 1.5 turns so triangles
# crossing the underside seam can unwrap continuously instead of being clamped.
CHARTS = {
    'hand': (8, 8, 504, 376),
    'cap': (8, 392, 248, 504), 'cuff': (264, 392, 504, 504),
}



def themes():
    cfg = json.loads((ASSETS / 'personas.json').read_text(encoding='utf-8'))
    return [dict(key='gign', skin=0, path=ASSETS/cfg['reference'])] + [
        dict(key=t['key'], skin=t['skin'], path=ASSETS/t['id']/'texture-atlas.png') for t in cfg['themes']]


def digest():
    paths = [Path(__file__), OUT/'mp40_hands.smd', ASSETS/'personas.json'] + [t['path'] for t in themes()]
    return build_cache.fingerprint(paths + build_cache.compiler_inputs())


def sample(image, x, y):
    """Bilinear sampling in the 512-pixel reference layout, at native resolution."""
    h, w = image.shape[:2]
    x = np.clip(x*w/512, 0, w-1)
    y = np.clip(y*h/512, 0, h-1)
    ix, iy = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x-ix)[..., None], (y-iy)[..., None]
    jx, jy = np.minimum(ix+1, w-1), np.minimum(iy+1, h-1)
    return ((1-fx)*(1-fy)*image[iy, ix] + fx*(1-fy)*image[iy, jx]
            + (1-fx)*fy*image[jy, ix] + fx*fy*image[jy, jx]).astype('uint8')


def texture_atlases(path):
    src = np.array(Image.open(path).convert('RGB'))
    glove = Image.new('RGB', (512, 512))
    for name, (x0, y0, x1, y1) in CHARTS.items():
        u, v = np.meshgrid(np.linspace(0, 1, x1-x0), np.linspace(0, 1, y1-y0))
        if name == 'hand':
            # Continuous wrap: the existing back and palm islands meet at the
            # sides. A single chart prevents triangular seams on the palm.
            theta = (np.mod(v*1.5, 1)-.25)*2*math.pi
            across = .5+.5*np.sin(theta)
            yhand = .3+9.4*u
            body_along = np.clip((yhand-.3)/5.5, 0, 1)
            back = sample(src, 148-23*body_along, 471+32*across).astype(float)
            palm = sample(src, 7+24*body_along, 470+22*across).astype(float)
            weight = np.clip((np.cos(theta)+.2)/.6, 0, 1)
            weight = (weight*weight*(3-2*weight))[..., None]
            body = back*weight+palm*(1-weight)
            # A shared transition across the bases of all fingers avoids moving
            # whole web triangles to a different material at a bone boundary.
            finger_along = np.clip((yhand-4.8)/4.9, 0, 1)
            leather = sum(sample(src, 101-13*finger_along, 478+7*i+4*np.mod(v*1.5, 1)).astype(float) for i in range(4))/4
            transition = np.clip((yhand-4.6)/1.7, 0, 1)
            transition = (transition*transition*(3-2*transition))[..., None]
            pixels = (body*(1-transition)+leather*transition).astype('uint8')
        else:
            x, y = 8+21*u, 474+13*v
            if name == 'cuff':
                y = 474+13*np.mod(v*1.5, 1)
            pixels = sample(src, x, y)
        patch = Image.fromarray(pixels)
        glove.paste(patch, (x0, y0))
        # Extrude border texels into the gutters for filtered rendering.
        glove.paste(patch.resize((x1-x0+4, y1-y0+4)), (x0-2, y0-2))
        glove.paste(patch, (x0, y0))
    u, v = np.meshgrid(np.linspace(0, 1, 496), np.linspace(0, 1.5, 240))
    x = 138+148*u
    top, bottom = 232-.035*(x-138), 266-.108*(x-138)
    sleeve_patch = Image.fromarray(sample(src, x, top+(bottom-top)*np.mod(v, 1)))
    sleeve = Image.new('RGB', (512, 256))
    sleeve.paste(sleeve_patch.resize((500, 244)), (6, 6))
    sleeve.paste(sleeve_patch, (8, 8))
    return {'gloves': glove, 'sleeves': sleeve}


def continuous_angles(angles):
    if max(angles)-min(angles) > .5:
        return [a+1 if a < .5 else a for a in angles]
    return angles


def packed(name, u, v):
    x0, y0, x1, y1 = CHARTS[name]
    return (x0+(x1-x0)*u)/512, 1-(y0+(y1-y0)*v)/512


def tube_uv(points, start, end, depth, name, normal):
    axis = end-start
    length = np.linalg.norm(axis)
    axis /= length
    depth = depth-axis*(depth@axis)
    depth /= np.linalg.norm(depth)
    across = np.cross(axis, depth)
    delta = points-start
    along = delta@axis/length
    angles = continuous_angles([(math.atan2(p@across, p@depth)/(2*math.pi)+.25)%1 for p in delta])
    uv = [packed(name, np.clip(t, .01, .99), a/1.5) for t, a in zip(along, angles)]
    # Only a truly collapsed end face needs the planar cap chart. Selecting it
    # by normal direction also moved oblique palm faces, producing visible seams.
    a = np.array(uv)
    if abs(np.cross(a[1]-a[0], a[2]-a[0])) < 1e-8:
        r = max(.6, np.max(np.linalg.norm(delta-np.outer(delta@axis, axis), axis=1)))
        return [packed('cap', np.clip(.5+p@across/(2*r), .02, .98),
                       np.clip(.5+p@depth/(2*r), .02, .98)) for p in delta]
    return uv



def hand_uv(points, side):
    along = np.clip((points[:, 1]-.3)/9.4, .001, .999)
    angles = []
    for x, y, z in points:
        center_x, center_z = 0., -.1
        if side == 12 and y > 4.8 and abs(x) < 2.45:
            centers = np.array([1.78, .72, -.32, -1.39])
            finger_x = centers[np.argmin(abs(centers-x))]
            blend = np.clip((y-4.8)/1.4, 0, 1)
            blend = blend*blend*(3-2*blend)
            center_x = finger_x*blend
            center_z = -.1-.15*blend
        angles.append((math.atan2(x-center_x, z-center_z)/(2*math.pi)+.25)%1)
    angles = continuous_angles(angles)
    uv = [packed('hand', t, a/1.5) for t, a in zip(along, angles)]
    a = np.array(uv)
    if abs(np.cross(a[1]-a[0], a[2]-a[0])) < 1e-9:
        lo, hi = points[:, [0, 2]].min(0), points[:, [0, 2]].max(0)
        size = np.maximum(hi-lo, .1)
        uv = [packed('cap', .05+.9*(p[0]-lo[0])/size[0],
                     .05+.9*(p[2]-lo[1])/size[1]) for p in points]
    return uv


def refine_knuckles(mesh):
    """One conforming subdivision around fingers, with the existing rigid weights.

    Split an edge only when both ends belong to the same finger bone. The shared
    midpoint is propagated to both faces, including at UV seams; joint boundaries
    keep their original weights and there can be no animated cracks.
    """
    fingers = set(range(7, 10)) | set(range(13, 32))
    parsed = [(material, np.array([list(map(float, r.split())) for r in rows])) for material, rows in mesh]
    def key(v):
        return tuple(np.round(v[:4], 4))
    def edge(a, b):
        return tuple(sorted((key(a), key(b))))
    mids = {}
    max_shift = 0.
    for _, rows in parsed:
        for i in range(3):
            a, b = rows[i], rows[(i+1)%3]
            if a[0] != b[0] or int(a[0]) not in fingers:
                continue
            if np.linalg.norm(a[1:4]-b[1:4]) < .45 or a[4:7]@b[4:7] > .94:
                continue
            m = (a[1:4]+b[1:4])/2
            # Hermite-style rounding from the endpoint tangent planes.
            smooth = m-.5*((m-a[1:4])@a[4:7]*a[4:7]+(m-b[1:4])@b[4:7]*b[4:7])
            shift = smooth-m
            length = np.linalg.norm(shift)
            if length > .10:
                shift *= .10/length
            mids[edge(a, b)] = m+shift
            max_shift = max(max_shift, np.linalg.norm(shift))
    result = []
    for material, rows in parsed:
        cut = {}
        for i in range(3):
            a, b = rows[i], rows[(i+1)%3]
            if edge(a, b) in mids:
                m = (a+b)/2;m[1:4] = mids[edge(a, b)]
                m[4:7] /= max(np.linalg.norm(m[4:7]), 1e-9)
                cut[i] = m
        if len(cut) == 0:
            children = [rows]
        elif len(cut) == 1:
            i = next(iter(cut));j, k = (i+1)%3, (i+2)%3
            children = [[rows[i], cut[i], rows[k]], [cut[i], rows[j], rows[k]]]
        elif len(cut) == 2:
            i = next(i for i in range(3) if i in cut and (i+2)%3 in cut)
            j, k = (i+1)%3, (i+2)%3
            children = [[rows[i], cut[i], cut[k]], [cut[i], rows[j], rows[k]], [cut[i], rows[k], cut[k]]]
        else:
            children = [[rows[0], cut[0], cut[2]], [cut[0], rows[1], cut[1]],
                        [cut[2], cut[1], rows[2]], [cut[0], cut[1], cut[2]]]
        for child in children:
            result.append((material, [str(int(v[0]))+' '+' '.join(f'{x:.8f}' for x in v[1:]) for v in child]))
    return result, dict(edges=len(mids), added_triangles=len(result)-len(mesh),
                        max_rounding_units=max_shift, new_bones=0)


def clean_source(triangles, bind):
    """Remove complete imported accessories, including their glove-material sides.

    The wrist display and its frame use different materials. The cuff has its
    own elbow-driven bones, so it cannot follow the wrist during our reloads.
    Group by shared positions to remove accessories without cutting the hand.
    """
    owners = {}
    groups = [{i} for i in range(len(triangles))]
    for i, (_, rows) in enumerate(triangles):
        for row in rows:
            key = tuple(round(float(x), 4) for x in row.split()[1:4])
            if key in owners:
                other = groups[owners[key]]
                if groups[i] is not other:
                    merged = groups[i] | other
                    for j in merged:
                        groups[j] = merged
            owners[key] = i
    removed = {}; counts = dict(display=0, wrist_frame=0, detached_cuff=0)
    inv = np.linalg.inv(bind[12])
    for group in {id(g): g for g in groups}.values():
        rows = [r for i in group for r in triangles[i][1]]
        bones = {int(r.split()[0]) for r in rows}
        reason = None
        if any(triangles[i][0] == 'GLOVE_handpak.bmp.bmp' for i in group):
            reason = 'display'
        elif bones & set(range(33, 39)):
            reason = 'detached_cuff'
        elif len(group) <= 2 and bones == {12}:
            points = np.array([(inv@np.r_[list(map(float, r.split()[1:4])), 1])[:3] for r in rows])
            if np.all(points >= [-1.4, 1., -.5]) and np.all(points <= [1.6, 4.2, 1.2]):
                reason = 'wrist_frame'
        if reason:
            counts[reason] += len(group)
            removed.update({i: reason for i in group})
    assert counts == dict(display=12, wrist_frame=7, detached_cuff=36), counts
    return [tri for i, tri in enumerate(triangles) if i not in removed], counts


def meshes():
    header, _, tris = base.read_smd(OUT/'mp40_hands.smd')
    _, _, bind = base.skeleton(OUT/'mp40_hands.smd')
    tris, removed = clean_source(tris, bind)
    inv = {b: np.linalg.inv(bind[b]) for b in (6, 12)}
    result = {'gloves': [], 'sleeves': []}
    charts = {}
    for mat, rows in tris:
        values = np.array([list(map(float, r.split())) for r in rows])
        bones = values[:, 0].astype(int)
        sleeve = mat == 'GLOVED_sleeve.bmp' or all(b in (4, 10) for b in bones)
        kind = 'sleeves' if sleeve else 'gloves'
        side = 12 if np.mean(values[:, 1]) > 0 else 6
        local = np.array([(inv[side]@np.r_[v[1:4], 1])[:3] for v in values])
        normal = inv[side][:3, :3]@np.mean(values[:, 4:7], axis=0)
        normal /= max(np.linalg.norm(normal), 1e-8)
        if not sleeve and local[:, 1].min() < -3:
            # The imported glove material also covered long under-sleeve panels.
            # They must follow the torso, including at their mixed-bone boundary.
            sleeve, kind = True, 'sleeves'
        if sleeve:
            elbow = 10 if side == 12 else 4
            start, end = bind[elbow][:3, 3], bind[side][:3, 3]
            axis = end-start
            length = np.linalg.norm(axis)
            axis /= length
            across = np.array([1., 0, 0])
            across -= axis*(across@axis)
            across /= np.linalg.norm(across)
            depth = np.cross(axis, across)
            delta = values[:, 1:4]-start
            angles = continuous_angles([math.atan2(p@depth, p@across)/(2*math.pi)+.5 for p in delta])
            uv = [((8+496*np.clip(p@axis/length, .01, .99))/512,
                   1-(8+240*a/1.5)/256) for p, a in zip(delta, angles)]
            a = np.array(uv)
            if abs(np.cross(a[1]-a[0], a[2]-a[0])) < 1e-8:
                uv = [(.5+.12*(p@across)/4, .65+.12*(p@depth)/4) for p in delta]
            chart = 'sleeve'
        else:
            mid = local.mean(0)
            if mid[1] < .65 or any(33 <= b <= 38 for b in bones):
                uv = tube_uv(local, np.array([0., -2, 0]), np.array([0., 1.5, 0]),
                             np.array([0., 0, 1]), 'cuff', normal)
                chart = 'cuff'
            else:
                chart = 'hand'
                uv = hand_uv(local, side)
        charts[chart] = charts.get(chart, 0)+1
        converted = [str(int(v[0]))+' '+' '.join(f'{x:.8f}' for x in [*v[1:7], *tex]) for v, tex in zip(values, uv)]
        result[kind].append((f'fp_{kind}_00.bmp', converted))
    # Smooth the glove surface across UV seams. The old CHROME mesh had hard
    # normal splits which made the newly textured palm look like separate shards.
    normals = {}
    parsed = []
    for material, rows in result['gloves']:
        a = np.array([list(map(float, r.split())) for r in rows])
        face = np.cross(a[1, 1:4]-a[0, 1:4], a[2, 1:4]-a[0, 1:4])
        face /= max(np.linalg.norm(face), 1e-9)
        keys = []
        for i in range(3):
            key = tuple(np.round(a[i, :4], 4));keys.append(key)
            e1, e2 = a[(i+1)%3, 1:4]-a[i, 1:4], a[(i+2)%3, 1:4]-a[i, 1:4]
            angle = math.acos(np.clip(e1@e2/max(np.linalg.norm(e1)*np.linalg.norm(e2), 1e-9), -1, 1))
            normals[key] = normals.get(key, np.zeros(3))+face*angle
        parsed.append((material, a, keys))
    result['gloves'] = []
    for material, a, keys in parsed:
        for row, key in zip(a, keys):
            n = normals[key];row[4:7] = n/max(np.linalg.norm(n), 1e-9)
        result['gloves'].append((material, [str(int(v[0]))+' '+' '.join(f'{x:.8f}' for x in v[1:]) for v in a]))
    result['gloves'], refinement = refine_knuckles(result['gloves'])
    return header, result, charts, refinement, removed


def build(ensure=False):
    manifest = OUT/'first-person.json'
    identity, bank = digest(), themes()
    if ensure and manifest.exists():
        old = json.loads(manifest.read_text())
        if build_cache.current(old.get('build_cache'), identity):
            print('First-person gloves and sleeves are current.')
            return old
    assert [t['skin'] for t in bank] == list(range(len(bank)))
    for t in bank:
        for kind, atlas in texture_atlases(t['path']).items():
            atlas.quantize(256).save(OUT/f'fp_{kind}_{t["skin"]:02}.bmp')
    header, pieces, charts, refinement, removed = meshes()
    records = {}
    for kind, mesh in pieces.items():
        name = 'r01_fp_'+kind
        base.write_smd(OUT/(name+'.smd'), header, mesh)
        qc = f'$modelname "{name}.mdl"\n$cd "."\n$cdtexture "."\n$body part "{name}"\n$sequence idle "mp40_hands" fps 1\n'
        qc += '$texturegroup personas\n{\n'+''.join('{ "fp_'+kind+f'_{t["skin"]:02}'+'.bmp" }\n' for t in bank)+'}\n'
        path = OUT/(name+'.qc')
        path.write_text(qc, encoding='ascii')
        model = base.compile_model(path)
        s = Studio(model)
        assert s.numskinfamilies == len(bank) and len(s.mesh()) == len(mesh)
        records[kind] = dict(model=name, triangles=len(mesh), sha256=hashlib.sha256(model.read_bytes()).hexdigest())
    record = dict(inputs_sha256=identity, texture_quality='classic', uv_layout='anatomical charts',
                  source_triangles=546, removed_display_triangles=removed['display'],
                  removed_source_triangles=removed, replacement_back_triangles=0,
                  refinement=refinement, skin_families=len(bank), charts=charts,
                  themes=[dict(key=t['key'], skin=t['skin'], source=str(t['path'].relative_to(ROOT))) for t in bank],
                  parts=records, triangles=sum(map(len, pieces.values())),
                  limits=['existing first-person silhouette and finger animation',
                          'existing character pixels only; no generated HD textures',
                          'legacy imported weapons retain their own hands'])
    outputs=[OUT/(p['model']+ext) for p in records.values() for ext in ('.mdl','.qc','.smd')]+list(OUT.glob('fp_*.bmp'))
    record['build_cache']=build_cache.record(identity,outputs)
    build_cache.write(manifest,record)
    print('Built first-person parts:', records, 'with', len(bank), 'independent appearances')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ensure', action='store_true')
    build(parser.parse_args().ensure)
