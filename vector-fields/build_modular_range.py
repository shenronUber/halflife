"""Compile fixed collision candidates; the native server selects them at map load."""
import argparse
import json
import re
import subprocess
from pathlib import Path
import build_cache
from build_traversal_range import base

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated/modular-range'
HEADER = ROOT.parent / 'game_shared/vf_modular_layout.h'


def dimensions():
    text = HEADER.read_text()
    cell = int(re.search(r'CellSize=(\d+)', text)[1])
    gap = int(re.search(r'Gap=(\d+)', text)[1])
    return cell, gap


def edge_cells(edge):
    a = (edge // 2) * 3 + edge % 2 if edge < 6 else edge - 6
    return a, a + (1 if edge < 6 else 3)


def geometry():
    cell, gap = dimensions()
    extent = 3 * cell + 2 * gap
    half = extent // 2
    pitch = cell + gap
    world = []
    candidates = []
    shell = half + 256
    # A sealed sky shell keeps normal BSP compilation/PVS and collision hulls.
    for lo, hi in [((-shell-32,-shell-32,-1152),(-shell,shell+32,3104)),
                   ((shell,-shell-32,-1152),(shell+32,shell+32,3104)),
                   ((-shell,-shell-32,-1152),(shell,-shell,3104)),
                   ((-shell,shell,-1152),(shell,shell+32,3104)),
                   ((-shell,-shell,-1152),(shell,shell,-1120)),
                   ((-shell,-shell,3072),(shell,shell,3104))]:
        world.append((lo,hi,'SKY'))
    for c in range(9):
        x = -half + (c % 3) * pitch
        y = -half + (c // 3) * pitch
        world.append(((x,y,-64),(x+cell,y+cell,0),'CRETE3_FLR04'))
        # All blocks remain outside the central cross and the edge approaches.
        spots = [(256,256,96),(cell-256,256,144),(256,cell-256,192),
                 (cell-256,cell-256,96),(320,448,128),(cell-320,cell-448,48)]
        for variant,(dx,dy,height) in enumerate(spots):
            width = 96 if variant != 2 else 128
            candidates.append(dict(role=4,index=c,variant=variant,boxes=[((x+dx-width//2,y+dy-48,0),(x+dx+width//2,y+dy+48,height),'CRATE01')]))
    edges = []
    for e in range(12):
        a,b = edge_cells(e)
        x = -half + (a % 3) * pitch
        y = -half + (a // 3) * pitch
        # Author one local connector along X, then swap X/Y for north/south.
        horizontal = e < 6
        start = x + cell if horizontal else y + cell
        center = y + cell//2 if horizontal else x + cell//2

        def box(u0,v0,z0,u1,v1,z1,texture):
            if horizontal:
                return ((u0,v0,z0),(u1,v1,z1),texture)
            return ((v0,u0,z0),(v1,u1,z1),texture)

        join = [box(start,center-cell//2,-64,start+gap,center+cell//2,0,'CRETE3_FLR04')]
        bridge = [box(start,center-96,-24,start+gap,center+96,0,'FIFTIES_FLR01'),
                  box(start,center-104,0,start+gap,center-96,36,'CRETE3_WALL01'),
                  box(start,center+96,0,start+gap,center+104,36,'CRETE3_WALL01')]
        pillar = [box(start+gap//2-40,center-40,-1000,start+gap//2+40,center+40,-24,'CRETE3_WALL01')]
        # Bare wall across the gap. Its two 192-unit approach sections allow
        # ordinary running takeoff and safe landing on the next tile.
        wall = [box(start-192,center-104,-64,start+gap+192,center-80,256,'CRETE3_WALL01')]
        for role,boxes in enumerate((join,bridge,pillar,wall)):
            candidates.append(dict(role=role,index=e,variant=0,boxes=boxes))
        edges.append(dict(edge=e,cells=[a,b],axis='x' if horizontal else 'y',start=start,center=center,gap=gap,
                          bridge_width=192,wall_length=gap+384,wall_face=center-80,wall_approach=192))
    return dict(cell=cell,gap=gap,extent=extent,world=world,candidates=candidates,edges=edges,
                spawn=[-half+cell//2,-half+cell//2,40])


def build(ensure=False):
    tools=ROOT.parent/'asset-probe/sdhlt/sdhlt-v1.3.0/tools/Win64'
    wad=Path('F:/SteamLibrary/steamapps/common/Half-Life/valve/halflife.wad')
    inputs=[Path(__file__),HEADER,ROOT/'build_traversal_range.py',ROOT.parent/'weapon-lab/build_range.py',
            ROOT.parent/'asset-probe/generate_assets.py',wad,
            *[tools/f'sdHL{x}_x64.exe' for x in ('CSG','BSP','VIS','RAD')]]
    digest=build_cache.fingerprint(inputs)
    manifest=OUT/'manifest.json';target=OUT/'vf_modular.bsp'
    if ensure and build_cache.current(build_cache.read(manifest).get('build_cache'),digest):
        return target
    OUT.mkdir(parents=True,exist_ok=True)
    g=geometry()
    text=base.entity(dict(classname='worldspawn',message='Vector Fields - Grille modulaire',wad=wad.as_posix(),skyname='vf_storm',MaxRange='16384'),
                     [base.asset.map_box(*b) for b in g['world']])
    text+=base.entity(dict(classname='vf_modular_controller',origin='0 0 128',targetname='vf_layout'))
    for row in g['candidates']:
        text+=base.entity(dict(classname='vf_modular_piece',vf_role=str(row['role']),vf_index=str(row['index']),vf_variant=str(row['variant']),
                              targetname=f"vf_piece_{row['role']}_{row['index']}_{row['variant']}"),[base.asset.map_box(*b) for b in row['boxes']])
    text+=base.entity(dict(classname='info_player_start',origin=' '.join(map(str,g['spawn'])),angle='0'))
    half=g['extent']//2
    for c in (0,2,4,6,8):
        x=-half+(c%3)*(g['cell']+g['gap'])+g['cell']//2
        y=-half+(c//3)*(g['cell']+g['gap'])+g['cell']//2
        text+=base.entity(dict(classname='info_player_deathmatch',origin=f'{x} {y} 40',angle='0'))
    text+=base.entity(dict(classname='game_player_equip',weapon_9mmAR='1',ammo_9mmbox='5',item_suit='1'))
    # Keep already-owned pickup models behind the arrival camera; a suit placed
    # directly beside the spawn obscures the first-person view from inside it.
    for classname,dx,dy in [('weapon_9mmAR',-160,0),('ammo_9mmbox',-160,-64),('item_suit',-160,96)]:
        x,y,_=g['spawn'];text+=base.entity(dict(classname=classname,origin=f'{x+dx} {y+dy} 24'))
    # Prototype recovery instead of a long death/respawn cycle after a missed run.
    text+=base.entity(dict(classname='info_teleport_destination',targetname='vf_recovery',origin=' '.join(map(str,g['spawn'])),angle='0'))
    text+=base.entity(dict(classname='trigger_teleport',target='vf_recovery',spawnflags='1'),
                     [base.asset.map_box((-half-240,-half-240,-960),(half+240,half+240,-512),'AAATRIGGER')])
    text+=base.entity(dict(classname='light_environment',origin='0 0 900',angles='-80 35 0',_light='235 242 255 220'))
    for c in range(9):
        x=-half+(c%3)*(g['cell']+g['gap'])+g['cell']//2
        y=-half+(c//3)*(g['cell']+g['gap'])+g['cell']//2
        text+=base.entity(dict(classname='light',origin=f'{x} {y} 650',_light='225 240 255 650'))
    path=OUT/'vf_modular.map';path.write_text(text,encoding='ascii')
    for stage in ('CSG','BSP','VIS','RAD'):
        args=[str(tools/f'sdHL{stage}_x64.exe'),'-threads','4']
        if stage=='CSG':args+=['-wadinclude','halflife.wad']
        if stage=='VIS':args+=['-fast']
        if stage=='RAD':args+=['-bounce','1','-fast']
        result=subprocess.run(args+[str(path.with_suffix(''))],capture_output=True,text=True)
        (OUT/f'{stage}.log').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(f'{stage} failed: {OUT / (stage+".log")}')
    build_cache.write(manifest,dict(build_cache=build_cache.record(digest,[target,path]),geometry=g,
                                  runtime='server chooses an exact cover and toggles BSP candidates once in Activate; unchanged on saved-game restoration'))
    print('PASS modular BSP:',target,flush=True)
    return target


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ensure',action='store_true')
    build(parser.parse_args().ensure)
