"""Generate a GoldSrc modular-model and sealed-room map compatibility probe.

Uses only Python's standard library. Reads textures from the user's installed
Half-Life; those textures and compiled outputs are intentionally gitignored.
This is a geometry/format test, not a playable weapon or finished art asset.
"""
import argparse
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated'


def extract_bmp(model, name, target):
    data = model.read_bytes()
    assert data[:4] == b'IDST' and struct.unpack_from('<i', data, 4)[0] == 10
    count, offset = struct.unpack_from('<2i', data, 180)
    for i in range(count):
        raw, flags, width, height, start = struct.unpack_from('<64s4i', data, offset + 80*i)
        if raw.split(b'\0')[0].decode().lower() != name.lower():
            continue
        pixels = data[start:start + width*height]
        palette = data[start + width*height:start + width*height + 768]
        assert len(palette) == 768
        stride = (width + 3) & ~3
        rows = b''.join(pixels[y*width:(y+1)*width] + b'\0'*(stride-width)
                        for y in reversed(range(height)))
        palette_bgra = b''.join(bytes((palette[j+2], palette[j+1], palette[j], 0))
                                for j in range(0, 768, 3))
        header = struct.pack('<2sIHHI', b'BM', 1078+len(rows), 0, 0, 1078)
        info = struct.pack('<IiiHHIIiiII', 40, width, height, 1, 8, 0, len(rows), 0, 0, 256, 256)
        target.write_bytes(header + info + palette_bgra + rows)
        return {'source_model': str(model), 'source_texture': name,
                'width': width, 'height': height}
    raise ValueError(f'Texture {name} missing from {model}')


def face(mesh, points):
    a,b,c = points[:3]
    u = [b[i]-a[i] for i in range(3)]
    v = [c[i]-a[i] for i in range(3)]
    n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
    length = math.sqrt(sum(x*x for x in n))
    normal = tuple(x/length for x in n)
    for i in range(1,len(points)-1):
        mesh.append([(points[k], normal, ((0,0),(1,0),(1,1),(0,1))[j])
                     for j,k in enumerate((0,i,i+1))])


def box(mesh, low, high):
    x,y,z=low; X,Y,Z=high
    for q in [((x,y,z),(x,y,Z),(x,Y,Z),(x,Y,z)),
              ((X,y,z),(X,Y,z),(X,Y,Z),(X,y,Z)),
              ((x,y,z),(X,y,z),(X,y,Z),(x,y,Z)),
              ((x,Y,z),(x,Y,Z),(X,Y,Z),(X,Y,z)),
              ((x,y,z),(x,Y,z),(X,Y,z),(X,y,z)),
              ((x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z))]:
        face(mesh,q)


def cylinder(mesh, x0, x1, radius, cy=0, cz=0, sides=8):
    rings = [[(x,cy+radius*math.cos(i*math.tau/sides),cz+radius*math.sin(i*math.tau/sides))
              for i in range(sides)] for x in (x0,x1)]
    face(mesh, list(reversed(rings[0])))
    face(mesh, rings[1])
    for i in range(sides):
        j=(i+1)%sides
        face(mesh, [rings[0][i],rings[0][j],rings[1][j],rings[1][i]])


def write_smd(name, mesh):
    lines=['version 1','nodes','0 "root" -1','end','skeleton','time 0','0 0 0 0 0 0 0','end']
    if mesh:
        lines.append('triangles')
        for triangle in mesh:
            lines.append('metal.bmp')
            for pos,normal,uv in triangle:
                lines.append('0 '+' '.join(f'{v:.6f}' for v in (*pos,*normal,*uv)))
        lines.append('end')
    (OUT/(name+'.smd')).write_text('\n'.join(lines)+'\n',encoding='ascii')


def map_box(lo,hi,texture):
    x,y,z=lo; X,Y,Z=hi
    # Outward normals for GoldSrc MAP planes (clockwise when seen from outside).
    planes=[((x,y,z),(x,Y,z),(x,Y,Z)),((X,y,z),(X,y,Z),(X,Y,Z)),
            ((x,y,z),(x,y,Z),(X,y,Z)),((x,Y,z),(X,Y,z),(X,Y,Z)),
            ((x,y,z),(X,y,z),(X,Y,z)),((x,y,Z),(x,Y,Z),(X,Y,Z))]
    return '{\n'+'\n'.join(' '.join('( %d %d %d )'%p for p in plane)+
                           ' '+texture+' 0 0 0 1 1' for plane in planes)+'\n}'


def generate(valve):
    OUT.mkdir(parents=True,exist_ok=True)
    model=valve/'models'/'v_9mmar.mdl'
    textures=[extract_bmp(model,'HK_chrome.bmp',OUT/'metal.bmp'),
              extract_bmp(model,'PLAYER_Chrome2.bmp',OUT/'alternate.bmp')]
    meshes={n:[] for n in ('receiver','barrel_short','barrel_long','mag_straight','mag_wide')}
    m=meshes['receiver']
    box(m,(-10,-2,0),(6,2,4))
    box(m,(-8,-1.3,-7),(-5,1.3,0))
    box(m,(-19,-1.7,0),(-10,1.7,3))
    box(m,(-20,-2,-1),(-18,2,5))
    box(m,(-6,-.8,4),(3,.8,4.8))
    box(m,(-5,-.5,-4),(0,.5,-3.5))
    box(m,(-.5,-.5,-4),(0,.5,0))
    for name,tip,radius in [('barrel_short',15,1.1),('barrel_long',23,.8)]:
        cylinder(meshes[name],6,tip,radius,cz=2)
        cylinder(meshes[name],6,9,1.7,cz=2)
        cylinder(meshes[name],tip-2,tip,1.4,cz=2)
    box(meshes['mag_straight'],(0,-1.25,-8),(3,1.25,0))
    box(meshes['mag_wide'],(-.5,-3,-6),(4,3,0))
    box(meshes['mag_wide'],(-1,-3.5,-6.5),(4.5,3.5,-5))
    for name,mesh in meshes.items():
        write_smd(name,mesh)
    write_smd('idle',[])
    (OUT/'vf_modular.qc').write_text('''$modelname "vf_modular.mdl"
$cd "."
$cdtexture "."
$scale 1
$origin 0 0 0 0
$body "receiver" "receiver"
$bodygroup "barrel"
{
 studio "barrel_short"
 studio "barrel_long"
}
$bodygroup "magazine"
{
 studio "mag_straight"
 studio "mag_wide"
}
$texturegroup "finish"
{
 { "metal.bmp" }
 { "alternate.bmp" }
}
$sequence "idle" "idle" fps 1 loop
''',encoding='ascii')
    # Local-only texture references, a sealed room, four MP starts and platforms.
    wad=(valve/'halflife.wad').as_posix()
    solids=[((-272,-272,-16),(272,272,0),'FIFTIES_FLR01'),
            ((-272,-272,192),(272,272,208),'CRETE3_WALL01'),
            ((-272,-272,0),(-256,272,192),'CRETE3_WALL01'),
            ((256,-272,0),(272,272,192),'CRETE3_WALL01'),
            ((-256,-272,0),(256,-256,192),'CRETE3_WALL01'),
            ((-256,256,0),(256,272,192),'CRETE3_WALL01'),
            ((-80,-48,0),(16,48,32),'CRATE01'),
            ((80,48,0),(144,112,64),'CRATE01')]
    text='{\n"classname" "worldspawn"\n"message" "Vector Fields - generated probe"\n'
    text+=f'"wad" "{wad}"\n'+ '\n'.join(map_box(*s) for s in solids)+'\n}\n'
    entities=[('info_player_start',(-180,-180,40)),
              *[('info_player_deathmatch',(x,y,40)) for x,y in [(-180,-180),(180,180),(-180,180),(180,-180)]],
              ('light',(0,0,150)),('light',(-150,150,140)),('light',(150,-150,140)),
              ('weapon_crowbar',(-140,0,16)),('weapon_9mmhandgun',(160,0,16)),
              ('item_battery',(0,-160,16))]
    for cls,pos in entities:
        text+=' {\n"classname" "'+cls+'"\n"origin" "'+' '.join(map(str,pos))+'"\n'
        if cls=='light': text+='"_light" "255 225 190 350"\n'
        text+='}\n'
    (OUT/'vf_asset_lab.map').write_text(text,encoding='ascii')
    manifest={'purpose':'Local format probe only. No shooting, hands or reload animation.',
              'textures_from_owned_installation':textures,'model_variants':4,'skins':2,
              'display_combinations':8,'triangles_per_component':{n:len(m) for n,m in meshes.items()},
              'body_encoding':'body = barrel_index + 2 * magazine_index; skin = finish_index',
              'map_brushes':len(solids),'multiplayer_starts':4,
              'map_compilers':'https://github.com/seedee/SDHLT/releases/tag/v1.3.0'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--valve',type=Path,default=Path('F:/SteamLibrary/steamapps/common/Half-Life/valve'))
    args=parser.parse_args()
    generate(args.valve)
