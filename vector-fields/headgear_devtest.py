"""Diagnostic materials on the actual fitted meshes, in isolated reviews only.

Keep the compiled vertices, normals, bones and animation payload. Replace just
the draw-command UVs/materials, so shared outfit UVs cannot disguise a hand face.
Both hand rigs have dorsal +Z and palmar -Z in their reference hand frame:
the thumb roots and the relaxed finger tips bend toward -Z.
"""
import collections
import hashlib
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from native_workspace import private_copy
from studio_assets import Studio

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated/headgear-devtest'
SOURCES = {
    'persona_scout': ROOT / 'generated/visual_skins/persona_scout.mdl',
    'r01_fp_gloves': ROOT / 'generated/r01/r01_fp_gloves.mdl',
    'r01_fp_sleeves': ROOT / 'generated/r01/r01_fp_sleeves.mdl',
}
COLORS = {
    'palm': '#ff7d23', 'back': '#1599ef', 'edge': '#eeeeee',
    'thumb': '#ffe52a', 'forearm': '#56d5a5', 'upperarm': '#b696ee',
    'front': '#eb617f', 'rear': '#ae75cf', 'top': '#75e4c8',
    'legs': '#9ba8bd', 'feet': '#65758c',
}
WORDS = {
    'palm': 'PAUME / INT', 'back': 'DOS / EXT', 'edge': 'TRANCHE',
    'thumb': 'POUCE', 'forearm': 'AVANT-BRAS', 'upperarm': 'BRAS',
    'front': 'AVANT', 'rear': 'ARRIERE', 'top': 'HAUT',
    'legs': 'JAMBES', 'feet': 'PIEDS',
}


def texture(kind, side):
    image = Image.new('RGB', (256, 256), COLORS[kind])
    draw = ImageDraw.Draw(image)
    small = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 14)
    large = ImageFont.truetype('C:/Windows/Fonts/consolab.ttf', 22)
    for i in range(16, 256, 32):
        draw.line((i, 0, i, 255), fill='#324458', width=1)
        draw.line((0, i, 255, i), fill='#324458', width=1)
        draw.text((4, i + 2), str(i // 32), font=small, fill='#132134')
    for y in (55, 155):
        text = WORDS[kind]
        if side:
            text += ' ' + side
        # Use a crisp white patch, independent of diffuse glove shading.
        draw.text((128, y), text, font=large if len(text)<12 else small,
                  fill='white',stroke_width=1,stroke_fill='#172232',anchor='mt')
        draw.line((128, y+28, 128, y+43), fill='#172232', width=3)
        draw.polygon([(128, y+48), (121, y+39), (135, y+39)], fill='#172232')
    return image


def ancestor(studio, bone, names):
    while bone >= 0:
        if studio.names[bone] in names:
            return bone
        bone = studio.parents[bone]
    return None


def classifier(studio, rows, points, normals, zone, fp):
    hand_names = {'Bone07', 'Bone42'} if fp else {'Bip01 L Hand', 'Bip01 R Hand'}
    hands = [ancestor(studio, b, hand_names) for b in rows]
    hand = next((h for h in hands if h is not None), None)
    side = ''
    if hand is not None:
        side = 'G' if studio.names[hand] in ('Bone42', 'Bip01 L Hand') else 'D'
        inverse = np.linalg.inv(studio.bind[hand])
        p = np.array([(inverse @ np.r_[v, 1])[:3] for v in points])
        normal = inverse[:3, :3] @ np.mean(normals, axis=0)
        thumb_names = {'Bone08', 'Bone43'} if fp else {'Bip01 L Finger0', 'Bip01 R Finger0'}
        # Shared wrist/palm triangles can have one thumb-weighted vertex.
        # Mark only faces entirely belonging to the thumb, not the whole web.
        thumb = all(ancestor(studio, b, thumb_names) is not None for b in rows)
        kind = 'thumb' if thumb else ('back' if normal[2]>.35 else 'palm' if normal[2]<-.35 else 'edge')
        if fp:
            uv = [(np.clip((v[0]+3)/6, .02, .98), np.clip((v[1]+.5)/10.5, .02, .98)) for v in p]
        else:
            uv = [(np.clip((v[1]+2.5)/4, .02, .98), np.clip(v[0]/6.5, .02, .98)) for v in p]
        return (kind, side), uv
    arms = {'Bone05', 'Bone40'} if fp else {'Bip01 L Arm1', 'Bip01 R Arm1', 'Bip01 L Arm2', 'Bip01 R Arm2'}
    arm = next((ancestor(studio, b, arms) for b in rows if ancestor(studio, b, arms) is not None), None)
    if arm is not None:
        name = studio.names[arm]
        side = 'G' if name == 'Bone40' or ' L ' in name else 'D'
        kind = 'forearm' if fp or 'Arm2' in name else 'upperarm'
        inv = np.linalg.inv(studio.bind[arm])
        p = np.array([(inv @ np.r_[v, 1])[:3] for v in points])
        # Numbered circumferential chart; wrap keeps the longitudinal marks.
        uv = [((math.atan2(v[2],v[0])/(2*math.pi)+.5), np.clip((v[1] if fp else v[0])/20, .02, .98)) for v in p]
        return (kind, side), uv
    n = np.mean(normals, axis=0)
    kind = 'top' if zone == 'head' and n[2]>.55 else 'front' if n[1]<0 else 'rear'
    if zone in ('legs', 'feet'):
        kind = zone
    bounds = {'head':(-6,6,59,72), 'torso':(-25,25,38,60), 'legs':(-12,12,8,40), 'feet':(-12,12,0,10)}
    lo,hi,bottom,top = bounds.get(zone,(-30,30,0,72))
    uv = [(np.clip((v[0]-lo)/(hi-lo),.02,.98),np.clip((v[2]-bottom)/(top-bottom),.02,.98)) for v in points]
    return (kind, side), uv


def build_model(source, target):
    studio = Studio(source)
    data = bytearray(studio.data)
    materials = {}
    counts = collections.Counter()
    def material(key):
        if key not in materials:
            materials[key] = len(materials)
        return materials[key]
    fp = source.stem.startswith('r01_fp')
    for zone, choices, model_offset in studio.parts:
        for choice in range(choices):
            model = model_offset + choice * 112
            nm, mi, nv, vi, vp, nn, ni, nptr = struct.unpack_from('<8i', data, model+72)
            groups = collections.defaultdict(list)
            for mesh in range(nm):
                _, commands, _, _, _ = struct.unpack_from('<5i', data, mi+20*mesh)
                while True:
                    count = struct.unpack_from('<h', data, commands)[0]; commands += 2
                    if not count:
                        break
                    rows = [struct.unpack_from('<4h', data, commands+8*i) for i in range(abs(count))]
                    commands += abs(count)*8
                    for i in range(2, len(rows)):
                        ids = [0,i-1,i] if count<0 else ([i-2,i-1,i] if i%2==0 else [i-1,i-2,i])
                        tri = [rows[j] for j in ids]
                        bones = [data[vi+r[0]] for r in tri]
                        points = [(studio.bind[b] @ np.r_[struct.unpack_from('<3f', data, vp+12*r[0]),1])[:3] for b,r in zip(bones,tri)]
                        normals = [studio.bind[data[ni+r[1]]][:3,:3] @ np.array(struct.unpack_from('<3f', data, nptr+12*r[1])) for r in tri]
                        key, uv = classifier(studio,bones,points,normals,zone,fp)
                        index = material(key); counts[key[0]] += 1
                        groups[index].append([(r[0],r[1],round(u*255),round((1-v)*255)) for r,(u,v) in zip(tri,uv)])
            meshes = []
            for index, tris in groups.items():
                offset = len(data)
                for tri in tris:
                    data += struct.pack('<h',3) + b''.join(struct.pack('<4h',*v) for v in tri)
                data += struct.pack('<h',0)
                meshes.append((len(tris),offset,index,nn,0))
            table = len(data)
            for mesh in meshes:
                data += struct.pack('<5i',*mesh)
            struct.pack_into('<ii', data, model+72, len(meshes), table)
    texture_headers = []
    for (kind,side),index in materials.items():
        image = texture(kind,side)
        image.save(target.parent/f'{target.stem}_{kind}_{side or "body"}.png')
        indexed = image.quantize(128)
        offset = len(data)
        # GoldSrc always consumes 256 RGB entries, including unused colors.
        palette=bytes(indexed.getpalette()[:768]).ljust(768,b'\0')
        data += indexed.tobytes() + palette
        texture_headers.append(struct.pack('<64s4i',f'dev_{kind}_{side}.bmp'.encode(),4,256,256,offset))
    table = len(data)
    data += b''.join(texture_headers)
    struct.pack_into('<iii',data,180,len(materials),table,0)
    skins = len(data)
    for _ in range(max(1,studio.numskinfamilies)):
        data += struct.pack('<'+'h'*len(materials),*range(len(materials)))
    struct.pack_into('<iii',data,192,len(materials),max(1,studio.numskinfamilies),skins)
    struct.pack_into('<i',data,72,len(data))
    target.write_bytes(data)
    untouched=np.ones(len(studio.data),dtype=bool)
    untouched[72:76]=False;untouched[180:204]=False
    for _,choices,model_offset in studio.parts:
        for choice in range(choices):
            start=model_offset+112*choice+72;untouched[start:start+8]=False
    assert np.array_equal(np.frombuffer(studio.data,dtype='uint8')[untouched],
                          np.frombuffer(data,dtype='uint8')[:len(studio.data)][untouched]),'Diagnostic skin changed skeleton or animation bytes'
    # Validate the rendered faces against the donor, independently of new UVs.
    result = Studio(target)
    for zone,choices,_ in studio.parts:
        z = [p[0] for p in studio.parts].index(zone)
        for choice in range(choices):
            selection = {i:-1 for i in range(len(studio.parts))}; selection[z]=choice
            def vertices(s):
                return sorted(tuple(np.round([v['b'],*v['p'],*v['n']],5)) for _,t in s.mesh(selection) for v in t)
            assert vertices(studio)==vertices(result),'Diagnostic skin changed geometry or bone weights'
    assert studio.names==result.names and studio.sequences==result.sequences
    return dict(source=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(studio.data).hexdigest(),
                target=target.name,sha256=hashlib.sha256(data).hexdigest(),triangles=dict(counts),
                geometry_and_bones_unchanged=True,animation_payload_unchanged=True)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    models = {name:build_model(source,OUT/(name+'.mdl')) for name,source in SOURCES.items()}
    record = dict(models=models,palm_local_axis='-Z',back_local_axis='+Z',
                  colors=COLORS,words=WORDS,production_assets_modified=False)
    (OUT/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('Built diagnostic skin: palm orange, back blue, thumb yellow; unchanged geometry',flush=True)
    return record


def install(mod):
    build()
    for name in SOURCES:
        folder = 'vf_skins' if name=='persona_scout' else 'vf_r01'
        private_copy(OUT/(name+'.mdl'),Path(mod)/'models'/folder/(name+'.mdl'))


if __name__=='__main__':
    build()
