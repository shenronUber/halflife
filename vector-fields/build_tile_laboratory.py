"""Playable 3x3 room kit: shared movement kit plus eight selectable interiors."""
import argparse,json,subprocess
from pathlib import Path
import build_cache
import build_modular_range as grid
import build_modular_ambience as ambience
import tile_blockout_textures as textures
from build_traversal_range import base

ROOT=Path(__file__).resolve().parent; OUT=ROOT/'generated/tile-laboratory'
FAMILIES=['Chambre froide / sas','Chantier ouvert','Galeries sur deux niveaux','Conduits de service']

def shared():
    b=[]
    def box(x,y,z,X,Y,Z,tex):b.append(((x,y,z),(X,Y,Z),tex))
    # Upper ring reached by normal 16-unit stair steps.
    box(120,104,176,1160,224,192,'VX_LEVEL')
    box(120,96,192,1160,104,224,'VX_VOID')
    for i in range(12):box(96,464-i*24,0,192,488-i*24,(i+1)*16,'VX_LEDGE')
    # An optional low shortcut; both sides can be bypassed while standing.
    box(280,240,48,448,400,68,'VX_SLIDE')
    box(280,228,0,448,240,68,'VX_WALL');box(280,400,0,448,412,68,'VX_WALL')
    # Pair of shelves reproducing the existing ledge/back-jump dimensions.
    box(356,960,0,540,1120,96,'VX_LEDGE');box(100,960,0,196,1120,160,'VX_LEDGE')
    # Smooth run surface, with low cover underneath the aerial shortcut.
    box(800,820,0,1180,844,256,'VX_RUN')
    box(944,852,0,1032,944,64,'VX_COVER')
    # Compact combat cover around a clear spawn and orthogonal port approaches.
    box(780,520,0,908,604,96,'VX_COVER');box(420,704,0,508,800,112,'VX_COVER')
    # Structural feet disappear into the existing cloud sea.
    box(608,608,-1000,672,672,-64,'VX_WALL')
    return b

def shell(cell):
    # Only edges facing another grid cell have doorways; exterior walls are sealed.
    b=[]
    for axis in (0,1):
        for high in (False,True):
            neighbour=(cell%3<2 if high else cell%3>0) if axis==0 else (cell//3<2 if high else cell//3>0)
            u0,u1=(1240,1264) if high else (16,40)
            spans=[(16,448,0,352),(832,1264,0,352),(448,832,288,352)] if neighbour else [(16,1264,0,352)]
            for v0,v1,z0,z1 in spans:
                lo,hi=((u0,v0,z0),(u1,v1,z1)) if axis==0 else ((v0,u0,z0),(v1,u1,z1))
                b.append((lo,hi,'VX_WALL'))
    b.append(((16,16,352),(1264,1264,384),'VX_WALL'))
    return b

def interior(variant):
    family,alt=divmod(variant,2); b=[]
    def box(x,y,z,X,Y,Z,tex):b.append(((x,y,z),(X,Y,Z),tex))
    if family==0:
        if not alt:
            for x in (840,1040):
                box(x,280,0,x+112,472,160,'VX_COLD');box(x-8,272,160,x+120,480,176,'VX_WHITE')
        else:
            box(824,80,0,848,392,256,'VX_COLD');box(896,432,0,1168,480,96,'VX_COLD')
            box(1016,128,0,1168,248,144,'VX_COVER')
        box(600,32,256,680,448,280,'VX_COLD')
    elif family==1:
        if not alt:
            box(864,256,0,1120,448,128,'VX_OPEN');box(904,296,128,1080,408,192,'VX_WHITE')
            box(888,1120,0,1192,1152,288,'VX_OPEN')
        else:
            box(824,256,0,944,440,160,'VX_OPEN');box(1024,440,0,1184,488,96,'VX_COVER')
            box(1128,1120,0,1160,1216,320,'VX_WALL');box(864,1120,0,960,1152,192,'VX_OPEN')
        box(64,704,0,320,752,64,'VX_COVER')
    elif family==2:
        end=496 if not alt else 448
        box(820,96,176,1216,end,192,'VX_LEVEL')
        box(820,end,192,1056,end+8,224,'VX_VOID');box(1168,end,192,1216,end+8,224,'VX_VOID')
        # Stair ends against the south edge of the deck without a ceiling over it.
        for i in range(12):
            y=end+264-i*24; box(1064,y,0,1160,y+24,(i+1)*16,'VX_LEDGE')
        box(872,256,192,1000,336,248,'VX_COVER')
        if alt:box(788,256,176,820,448,192,'VX_LEVEL')
        box(824,104,0,840,120,176,'VX_WALL');box(1192,104,0,1208,120,176,'VX_WALL')
    else:
        for x in (856,1152):
            box(x,96,0,x+24,240,256,'VX_DUCT');box(x,448,0,x+24,496,256,'VX_DUCT')
        box(880,256,48,1152,432,72,'VX_SLIDE')
        box(984,96,0,1008,240,192,'VX_DUCT')
        if alt:box(1008,464,0,1184,488,112,'VX_DUCT')
        else:box(1008,128,0,1168,160,80,'VX_COVER')
        box(520,80,240,744,112,272,'VX_DUCT')
    return b

def translate(boxes,x,y):
    return [((lo[0]+x,lo[1]+y,lo[2]),(hi[0]+x,hi[1]+y,hi[2]),tex)for lo,hi,tex in boxes]

def geometry():
    g=grid.geometry(); world=[]
    for lo,hi,tex in g['world']:world.append((lo,hi,tex if tex=='SKY' else 'VX_FLOOR'))
    candidates=[]
    for row in g['candidates']:
        if row['role']==4:continue
        tex={0:'VX_FLOOR',1:'VX_PORT',2:'VX_WALL',3:'VX_RUN'}[row['role']]
        candidates.append(dict(row,boxes=[(lo,hi,tex)for lo,hi,_ in row['boxes']]))
    for c in range(9):
        x=-g['extent']//2+c%3*(g['cell']+g['gap']);y=-g['extent']//2+c//3*(g['cell']+g['gap'])
        world+=translate(shared(),x,y)
        for variant in range(8):candidates.append(dict(role=5,index=c,variant=variant,boxes=translate(interior(variant),x,y)))
        candidates.append(dict(role=6,index=c,variant=0,boxes=translate(shell(c),x,y)))
        # Port paint is flush with the ground; it is a visual guide, not an obstacle.
        for axis in (0,1):
            for high in (False,True):
                neighbour=(c%3<2 if high else c%3>0)if axis==0 else(c//3<2 if high else c//3>0)
                if not neighbour:continue
                u=1200 if high else 48
                lo,hi=((u,512,0),(u+16,768,2))if axis==0 else((512,u,0),(768,u+16,2))
                world+=translate([(lo,hi,'VX_PORT')],x,y)
    for edge in g['edges']:
        start=edge['start'];center=edge['center'];end=start+g['gap']
        boxes=[((start-40,center-192,0),(end+40,center-176,288),'VX_WALL'),
               ((start-40,center+176,0),(end+40,center+192,288),'VX_WALL'),
               ((start-40,center-192,288),(end+40,center+192,312),'VX_WALL')]
        if edge['axis']=='y':boxes=[((a[1],a[0],a[2]),(b[1],b[0],b[2]),t)for a,b,t in boxes]
        candidates.append(dict(role=7,index=edge['edge'],variant=0,boxes=boxes))
    g.update(world=world,candidates=candidates,room_variants=8,shared_route_probes=dict(
        slide=dict(start=[224,320,36],end_x=480,yaw=0,velocity=[400,0,0]),
        hang=dict(start=[338,1040,54],yaw=0),back_jump=dict(target=[214,1040],yaw=180),
        wallrun=dict(start=[810,862,128],entry_yaw=300,yaw=0,velocity=[320,0,0]),
        stairs=dict(start=[144,512,36],yaw=270,top=192)))
    return g

def build(ensure=False):
    tools=ROOT.parent/'asset-probe/sdhlt/sdhlt-v1.3.0/tools/Win64'
    stock=Path('F:/SteamLibrary/steamapps/common/Half-Life/valve/halflife.wad')
    inputs=[Path(__file__),Path(grid.__file__),Path(ambience.__file__),Path(textures.__file__),
            ROOT/'build_traversal_range.py',ROOT.parent/'weapon-lab/build_range.py',ROOT.parent/'asset-probe/generate_assets.py',
            ROOT.parent/'game_shared/vf_modular_layout.h',ROOT.parent/'game_shared/vf_tile_rooms.h',stock,
            *[tools/f'sdHL{s}_x64.exe'for s in ('CSG','BSP','VIS','RAD')]]
    digest=build_cache.fingerprint(inputs); manifest=OUT/'manifest.json'; target=OUT/'vf_tiles.bsp'
    if ensure and build_cache.current(build_cache.read(manifest).get('cache'),digest):return target
    OUT.mkdir(parents=True,exist_ok=True); wad=OUT/'vf_tiles.wad'; textures.write(wad); g=geometry()
    text=base.entity(dict(classname='worldspawn',message='Vector Fields - Modules jouables',
        wad=stock.as_posix()+';'+wad.as_posix(),skyname='vf_storm',MaxRange='16384'),[base.asset.map_box(*b)for b in g['world']])
    text+=base.entity(dict(classname='vf_modular_controller',origin='0 0 128',targetname='vf_layout'))
    for row in g['candidates']:
        text+=base.entity(dict(classname='vf_modular_piece',vf_role=str(row['role']),vf_index=str(row['index']),
            vf_variant=str(row['variant']),targetname=f"vf_tile_{row['role']}_{row['index']}_{row['variant']}",_minlight='.15'),
            [base.asset.map_box(*b)for b in row['boxes']])
    for sound in ambience.entities(g):text+=base.entity(sound)
    for classname,c in [('info_player_start',0),*[('info_player_deathmatch',c)for c in (0,2,4,6,8)]]:
        x=-g['extent']//2+c%3*(g['cell']+g['gap'])+640; y=-g['extent']//2+c//3*(g['cell']+g['gap'])+640
        text+=base.entity(dict(classname=classname,origin=f'{x} {y} 40',angle='0'))
    text+=base.entity(dict(classname='game_player_equip',weapon_9mmAR='1',ammo_9mmbox='5',item_suit='1'))
    x,y,_=g['spawn']
    for name,dy in [('weapon_9mmAR',0),('ammo_9mmbox',-64),('item_suit',96)]:text+=base.entity(dict(classname=name,origin=f'{x-160} {y+dy} 24'))
    text+=base.entity(dict(classname='info_teleport_destination',targetname='vf_recovery',origin=' '.join(map(str,g['spawn'])),angle='0'))
    half=g['extent']//2
    text+=base.entity(dict(classname='trigger_teleport',target='vf_recovery',spawnflags='1'),
        [base.asset.map_box((-half-240,-half-240,-960),(half+240,half+240,-512),'AAATRIGGER')])
    text+=base.entity(dict(classname='light_environment',origin='0 0 900',angles='-80 35 0',_light='235 242 255 150'))
    for c in range(9):
        x=-half+c%3*(g['cell']+g['gap']);y=-half+c//3*(g['cell']+g['gap'])
        for dx,dy in ((640,640),(320,320),(1040,1040)):
            text+=base.entity(dict(classname='light',origin=f'{x+dx} {y+dy} 280',_light='235 235 225 450'))
    path=OUT/'vf_tiles.map';path.write_text(text,encoding='ascii')
    for stage in ('CSG','BSP','VIS','RAD'):
        args=[str(tools/f'sdHL{stage}_x64.exe'),'-threads','4']
        if stage=='CSG':args+=['-wadinclude','halflife.wad','-wadinclude','vf_tiles.wad']
        if stage in ('VIS','RAD'):args+=['-fast']
        if stage=='RAD':args+=['-bounce','1']
        result=subprocess.run(args+[str(path.with_suffix(''))],capture_output=True,text=True)
        (OUT/(stage+'.log')).write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(stage+' failed: '+result.stdout[-2000:]+result.stderr[-2000:])
    state=dict(cache=build_cache.record(digest,[target,path,wad]),geometry=g,families=FAMILIES,
        legend={'orange':'architecture','cyan':'wall run','violet':'glissade','yellow':'corniche et escalier','green':'raccord','red':'vide'},
        concepts=['2026-10-13-tiles-atmospheriques','2026-10-13-metiers-des-nuages'],
        scope='Eight playable blockout variants. Cinematic concept props and moving machines remain authoring references.')
    build_cache.write(manifest,state); print('PASS tile laboratory BSP:',target,flush=True); return target

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ensure',action='store_true');build(p.parse_args().ensure)
