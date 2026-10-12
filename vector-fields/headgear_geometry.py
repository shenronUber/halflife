"""Editable rigid helmet geometry and GoldSrc diffuse-material conversion."""
import hashlib
import math
from pathlib import Path

import numpy as np
from PIL import Image

import build_cache
import build_modular as base
import build_skins as geo
from studio_assets import Studio

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated/headgear'
ART = ROOT / 'assets/headgear'
REFERENCE = ROOT / 'generated/personas/persona_anchors.smd'
HEAD = geo.TARGET['head']
MOVING = 28
FLEX = 29
CENTER = np.array([.23387, -.6, 64.8])
TEX_SIZE = 256
RADIUS = np.array([3.95, 5.45, 6.05])
MATERIALS = {
    'riot_shell': ('riot-materials.png', 0), 'hardware': ('riot-materials.png', 1),
    'rim': ('riot-materials.png', 2), 'vents': ('riot-materials.png', 3),
    'lining': ('riot-materials.png', 2), 'bronze': ('spartan-materials.png', 0),
    'engraving': ('spartan-materials.png', 1), 'bronze_edge': ('spartan-materials.png', 2),
    'ornament': ('spartan-materials.png', 1),
    'crest': ('spartan-materials.png', 3), 'crest_dark': ('spartan-materials.png', 3),
    'lens_red': ('optics-materials.png', 0), 'lens_green': ('optics-materials.png', 1),
    'optics_metal': ('optics-materials.png', 2), 'red_housing': ('optics-materials.png', 3),
    'ballistic_paint': ('ballistic-gas-materials.png', 0),
    'gas_rubber': ('ballistic-gas-materials.png', 1),
    'filter_front': ('ballistic-gas-materials.png', 2),
    'filter_side': ('ballistic-gas-materials.png', 3),
}


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


class Mesh:
    def __init__(self):
        self.triangles = []

    def face(self, points, material, outward=None, normals=None, uv=None, bones=None):
        points = [np.asarray(p, dtype=float) for p in points]
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        if np.linalg.norm(normal) < 1e-7 and len(points) == 4:
            normal = np.cross(points[2] - points[0], points[3] - points[0])
        if np.linalg.norm(normal) < 1e-7:
            return
        normal = unit(normal)
        if uv is None:
            uv = [(0, 0), (1, 0), (1, 1), (0, 1)] if len(points) == 4 else [
                (.5 + .48 * math.cos(i * 2 * math.pi / len(points)),
                 .5 + .48 * math.sin(i * 2 * math.pi / len(points))) for i in range(len(points))]
        uv = list(uv)
        if outward is not None and normal @ outward < 0:
            points.reverse(); uv.reverse()
            if bones is not None:
                bones = list(reversed(bones))
            if normals is not None:
                normals = list(reversed(normals))
            normal = -normal
        normals = normals if normals is not None else [normal] * len(points)
        for i in range(1, len(points) - 1):
            if np.linalg.norm(np.cross(points[i] - points[0], points[i + 1] - points[0])) < 1e-7:
                continue
            # These are newly authored normalized SMD UVs, not imported MDL
            # texel coordinates; retain the compiler's native 0..1 convention.
            rows = [geo.vertex(points[k], normals[k], np.clip(uv[k], 0, 1), bones[k] if bones else HEAD)
                    for k in (0, i, i + 1)]
            self.triangles.append((material + '.bmp', rows))

    def articulate(self):
        for _, rows in self.triangles:
            for row in rows:
                row['b'] = MOVING
        return self

    def panel(self, points, normal, material, edge='hardware', bevel=.12, depth=.16):
        """Closed plate with a raised face and actual chamfer, arbitrary outline."""
        points = np.array(points, dtype=float); normal = unit(normal)
        center = points.mean(axis=0)
        inner = [p + unit(center - p) * bevel + normal * depth for p in points]
        axis = unit(points[1] - points[0]); other = unit(np.cross(normal, axis))
        projected = np.array([[p @ axis, p @ other] for p in points])
        uv = (projected - projected.min(axis=0)) / np.maximum(np.ptp(projected, axis=0), .001)
        self.face(inner, material, normal, uv=uv.tolist())
        self.face(points, 'lining', -normal, uv=uv.tolist())
        for i in range(len(points)):
            j = (i + 1) % len(points)
            self.face([points[i], points[j], inner[j], inner[i]], edge)

    def pin(self, center, axis, radius, depth, material='hardware', segments=10):
        """Machined circular hinge/rivet, with chamfered face."""
        center = np.asarray(center, dtype=float); axis = unit(axis)
        u = unit(np.cross(axis, [0, 0, 1] if abs(axis[2]) < .9 else [0, 1, 0])); v = np.cross(axis, u)
        for i in range(segments):
            a, b = i * 2 * math.pi / segments, (i + 1) * 2 * math.pi / segments
            radial = lambda t: u * math.cos(t) + v * math.sin(t)
            p0, p1 = center + radius * radial(a), center + radius * radial(b)
            q0, q1 = center + axis * depth + radius * .78 * radial(a), center + axis * depth + radius * .78 * radial(b)
            self.face([p0, p1, q1, q0], material, radial((a + b) / 2))
            self.face([center + axis * depth, q0, q1], material, axis,
                      uv=[(.5, .5), (.5 + .38 * math.cos(a), .5 + .38 * math.sin(a)),
                          (.5 + .38 * math.cos(b), .5 + .38 * math.sin(b))])

    def tube(self, points, radius, material, segments=6, bones=None):
        """Rolled edges and brackets following the designed contour."""
        points = np.array(points, dtype=float); rings = []; directions = []
        for i, p in enumerate(points):
            tangent = unit(points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)])
            u = unit(np.cross(tangent, [1, 0, 0] if abs(tangent[0]) < .9 else [0, 0, 1])); v = np.cross(tangent, u)
            directions.append([u * math.cos(j * 2 * math.pi / segments) + v * math.sin(j * 2 * math.pi / segments) for j in range(segments)])
            rings.append([p + radius * n for n in directions[-1]])
        for i in range(len(points) - 1):
            for j in range(segments):
                k = (j + 1) % segments
                ns = [directions[i][j], directions[i + 1][j], directions[i + 1][k], directions[i][k]]
                self.face([rings[i][j], rings[i + 1][j], rings[i + 1][k], rings[i][k]], material,
                          sum(ns), ns, [(i/(len(points)-1), j/segments), ((i+1)/(len(points)-1), j/segments),
                                        ((i+1)/(len(points)-1), (j+1)/segments), (i/(len(points)-1), (j+1)/segments)],
                          bones=[bones[i], bones[i+1], bones[i+1], bones[i]] if bones else None)


def bottom(theta):
    # Broad brow opening accommodates the forward-leaning GIGN skull and eyes.
    return 63.0 + 4.6 * max(0, math.cos(theta)) ** 1.5


def shell_point(theta, band, offset=0):
    phi = band * math.acos((bottom(theta) - CENTER[2]) / RADIUS[2])
    p = CENTER + RADIUS * np.array([math.sin(phi) * math.sin(theta),
                                   -math.sin(phi) * math.cos(theta), math.cos(phi)])
    normal = unit((p - CENTER) / (RADIUS * RADIUS))
    return p + normal * offset, normal


def dome(mesh, material, segments=48, bands=8, flat=False):
    for a in range(segments):
        t0, t1 = a * 2 * math.pi / segments, (a + 1) * 2 * math.pi / segments
        for j in range(bands):
            params = ((t0, j / bands), (t1, j / bands), (t1, (j + 1) / bands), (t0, (j + 1) / bands))
            samples = [shell_point(t, s) for t, s in params]
            mesh.face([p for p, n in samples], material, sum(n for p, n in samples),
                      None if flat else [n for p, n in samples], [(a % (segments//2) / (segments//2), j / bands), ((a % (segments//2) + 1) / (segments//2), j / bands),
                                               ((a % (segments//2) + 1) / (segments//2), (j+1) / bands), (a % (segments//2) / (segments//2), (j+1) / bands)])
        outer = [shell_point(t, 1)[0] for t in (t0, t1)]; inner = [shell_point(t, 1, -.22)[0] for t in (t0, t1)]
        mesh.face([outer[0], outer[1], inner[1], inner[0]], 'rim' if material == 'riot_shell' else 'bronze_edge', np.array([0, 0, -1]))
        mesh.face([inner[0], inner[1], inner[1] + [0, 0, .45], inner[0] + [0, 0, .45]],
                  'lining', -(sum(outer) / 2 - CENTER))


def shell_band(mesh, start, end, low, high, offset, material, segments=20, repeats=1):
    for i in range(segments):
        a, b = start+(end-start)*i/segments, start+(end-start)*(i+1)/segments
        samples = [shell_point(t,s,offset) for t,s in [(a,low),(b,low),(b,high),(a,high)]]
        per_repeat = segments // repeats
        u0, u1 = (i % per_repeat) / per_repeat, (i % per_repeat + 1) / per_repeat
        mesh.face([p for p,n in samples], material, sum(n for p,n in samples), [n for p,n in samples],
                  [(u0,1),(u1,1),(u1,0),(u0,0)])


def spartan():
    mesh=Mesh(); dome(mesh,'bronze',segments=20,bands=6,flat=True)
    shell_band(mesh,-math.pi,math.pi,.79,.90,.065,'engraving',32,repeats=2)
    mesh.tube([shell_point(t,1,.055)[0] for t in np.linspace(-math.pi,math.pi,33)],.085,'bronze_edge',6)
    for side in (-1,1):
        # Swept temple, concave eye edge, tapered jaw, rounded bevel.
        cheek=[np.array([CENTER[0]+side*x,y,z]) for x,y,z in
               [(3.67,-2.90,64.75),(3.22,-3.74,64.18),(1.64,-5.48,63.05),
                (1.34,-5.80,60.30),(1.68,-5.42,59.75),(3.05,-3.45,60.38),(3.67,-2.86,61.88)]]
        normal=unit([side*.78,-.62,0])
        mesh.panel(cheek,normal,'bronze','bronze_edge',.16,.13)
        mesh.tube([p+normal*.06 for p in cheek+[cheek[0]]],.055,'bronze_edge',4)
        ornament=[np.array([CENTER[0]+side*x,y,z])+normal*.19 for x,y,z in
                  [(3.32,-3.23,63.10),(2.20,-4.64,62.65),(1.96,-4.98,60.54),(3.10,-3.56,61.15)]]
        mesh.panel(ornament,normal,'ornament','bronze_edge',.05,.035)
        for x,y,z in ((3.62,-2.9,64.48),(3.42,-3.10,62.5)):
            mesh.pin(np.array([CENTER[0]+side*x,y,z])+normal*.19,normal,.115,.06,'bronze_edge',8)
        # Continuous raised eyebrow with thick tapered rim, deliberately open.
        for i in range(10):
            a,b=side*i*.08,side*(i+1)*.08
            p=lambda t,z: np.array([CENTER[0]+4.1*math.sin(t),-.75-5.8*math.cos(t),z])
            low=[p(t,66.00-.21*abs(math.sin(t))) for t in (a,b)]
            upper=[shell_point(t,.98,.075)[0] for t in (a,b)]
            mesh.face([low[0],low[1],upper[1],upper[0]],'engraving',np.array([0,-1,0]),
                      uv=[(abs(a)/.8,.1),(abs(b)/.8,.1),(abs(b)/.8,.8),(abs(a)/.8,.8)])
            mesh.face([low[0],low[1],low[1]+[0,-.10,.18],low[0]+[0,-.10,.18]],'bronze_edge',np.array([0,-1,-.25]))
        mesh.tube([np.array([CENTER[0]+4.1*math.sin(t),-.86-5.8*math.cos(t),66.18-.21*abs(math.sin(t))])
                   for t in np.linspace(0,side*.80,11)],.055,'bronze_edge',4)
    nasal=[(CENTER[0]-.23,-6.55,61.55),(CENTER[0]+.23,-6.55,61.55),
           (CENTER[0]+.34,-6.60,65.90),(CENTER[0]+.48,-5.37,67.50),
           (CENTER[0]-.48,-5.37,67.50),(CENTER[0]-.34,-6.60,65.90)]
    for points in ([nasal[0],nasal[1],nasal[2],nasal[5]],[nasal[5],nasal[2],nasal[3],nasal[4]]):
        mesh.panel(points,[0,-1,.05],'bronze','bronze_edge',.075,.10)
    mesh.tube([[CENTER[0],-6.74,61.75],[CENTER[0],-6.79,65.9],[CENTER[0],-5.56,67.35]],.045,'bronze_edge',4)
    # Narrow bronze crest carrier with fastening rivets.
    ts=np.linspace(-.91,1.40,25)
    def root(t,side=0):
        return np.array([CENTER[0]+side*.29,CENTER[1]+5.46*math.sin(t),CENTER[2]+6.19*math.cos(t)])
    for side in (-1,1):
        mesh.tube([root(t,side) for t in ts],.10,'bronze_edge',6)
        for t in ts[2::5]:
            mesh.pin(root(t,side)+[side*.08,0,.03],[side,0,0],.105,.04,'bronze_edge',8)
    # Separate tapered bundles create a combed, irregular horsehair silhouette.
    # Geometry handles silhouette; vertical painted fibers handle fine detail.
    for i in range(32):
        a=-.91+i*2.31/32; b=a+2.31/32*.98
        length=2.00+.36*math.cos((a+b)/2)+.12*math.sin(i*2.71)
        def tuft(t,side,raised):
            p=root(t,side)
            if raised:
                p += [side*(.13+.03*math.sin(i*1.71)),.38*math.sin(t),length]
            return p
        for side in (-1,1):
            mesh.face([tuft(a,side,0),tuft(b,side,0),tuft(b,side,1),tuft(a,side,1)],'crest',np.array([side,0,0]),
                      uv=[(i/32,0),((i+1)/32,0),((i+1)/32,1),(i/32,1)])
        mesh.face([tuft(a,-1,1),tuft(b,-1,1),tuft(b,1,1),tuft(a,1,1)],'crest',np.array([0,0,1]),
                  uv=[(i/32,.8),((i+1)/32,.8),((i+1)/32,1),(i/32,1)])
        for t,sign in ((a,-1),(b,1)):
            mesh.face([tuft(t,-1,0),tuft(t,1,0),tuft(t,1,1),tuft(t,-1,1)],'crest_dark',np.array([0,sign,0]))
    return mesh


def textures():
    for name,(filename,quadrant) in MATERIALS.items():
        image=Image.open(ART/filename).convert('RGB'); w,h=image.size
        x=(quadrant%2)*w//2; y=(quadrant//2)*h//2
        bounds=(x+12,y+12,x+w//2-12,y+h//2-12)
        if name=='engraving':
            # A single horizontal meander band, legible on the narrow frieze.
            bounds=(x+12,int(h*.048),x+w//2-12,int(h*.143))
        pixels=image.crop(bounds).resize((TEX_SIZE,TEX_SIZE),Image.Resampling.LANCZOS)
        if name=='crest_dark':
            pixels=Image.fromarray((np.asarray(pixels,dtype=float)*.65).astype('uint8'))
        pixels.quantize(colors=256).save(OUT/(name+'.bmp'))
    # Additive GoldSrc shield stays clear over the underlying eye masks.
    y,x=np.indices((TEX_SIZE,TEX_SIZE)); pixels=np.zeros((TEX_SIZE,TEX_SIZE,3),dtype='uint8'); pixels[:]=[2,5,7]
    for start,width in ((38,4),(192,5),(207,2)):
        pixels[(x>start)&(x<start+width)]=[14,21,25]
    pixels[y>250]=[8,12,16]
    Image.fromarray(pixels).quantize(colors=32).save(OUT/'visor.bmp')


def build(ensure=False):
    art_inputs=[ART/'riot-materials.png',ART/'spartan-materials.png',ART/'prompts.json',ART/'optics-materials.png',ART/'optics-prompt.txt',
                ART/'ballistic-gas-materials.png',ART/'ballistic-gas-prompt.txt']
    digest=build_cache.fingerprint([Path(__file__),ROOT/'headgear_designs.py',ROOT/'headgear_extra_designs.py',ROOT/'build_headgear.py',REFERENCE]+art_inputs+build_cache.compiler_inputs())
    manifest=OUT/'manifest.json'; old=build_cache.read(manifest)
    if ensure and build_cache.current(old.get('build_cache'),digest):
        return old
    OUT.mkdir(parents=True,exist_ok=True); textures()
    header,_,_=base.read_smd(REFERENCE); records=[]
    # Private joints inherit exactly the head bind matrix. Existing carriers and
    # authored animation banks remain byte-for-byte untouched.
    end=header.index('end')
    header[end:end]=['28 "VF_Headgear" 13','29 "VF_HeadgearFlex" 13']
    header[-1:-1]=['28 0 0 0 0 0 0','29 0 0 0 0 0 0']
    from headgear_designs import variants
    for variant,(key,mesh) in enumerate(variants(),1):
        base.write_smd(OUT/(key+'.smd'),header,geo.smd_tri(mesh.triangles))
        records.append(dict(key=key,body=variant,triangles=len(mesh.triangles),bone='Bip01 Head'))
    (OUT/'reference.smd').write_text('\n'.join(header)+'\n',encoding='ascii')
    qc=OUT/'headgear.qc'
    bodies=''.join(f' studio "{r["key"]}"\n' for r in records)
    qc.write_text('$modelname "headgear.mdl"\n$cd "."\n$cdtexture "."\n'
                  '$bodygroup headgear\n{\n blank\n'+bodies+'}\n'
                  '$sequence idle "reference" fps 1\n$texrendermode "visor.bmp" additive\n',encoding='ascii')
    model=base.compile_model(qc); studio=Studio(model)
    assert studio.parts[0][1]==12 and not studio.mesh({0:0})
    record=dict(model='models/vf_headgear/headgear.mdl',variants=records,mode='VF_PART_MERGE',
                reference=str(REFERENCE.relative_to(ROOT)),optional=False,gameplay_collision=False,
                material_sources=[str(p.relative_to(ROOT)) for p in art_inputs],texture_size=TEX_SIZE,
                sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
                articulation={'moving_bone':'VF_Headgear','flex_bone':'VF_HeadgearFlex','parent':'Bip01 Head'},
                limits=['clear windows use GoldSrc additive material, not physically based glass'],
                build_cache=build_cache.record(digest,[p for p in OUT.iterdir() if p.suffix in ('.smd','.qc','.mdl','.bmp')]))
    build_cache.write(manifest,record)
    print('Built head accessories:',', '.join(f"{r['key']} {r['triangles']} triangles" for r in records),flush=True)
    return record
