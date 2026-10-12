"""Independent wall-run corridor; leaves the existing F9 course unchanged."""
import argparse,json,subprocess
from pathlib import Path
from build_traversal_range import base
import build_cache
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'build/wallrun/range'
def build(ensure=False):
    tools=ROOT.parent/'asset-probe/sdhlt/sdhlt-v1.3.0/tools/Win64'
    inputs=[Path(__file__),ROOT/'build_traversal_range.py',ROOT.parent/'weapon-lab/build_range.py',ROOT.parent/'asset-probe/generate_assets.py',
        *[tools/f'sdHL{x}_x64.exe'for x in('CSG','BSP','VIS','RAD')]]
    stamp=build_cache.fingerprint(inputs);manifest=OUT/'manifest.json';target=OUT/'vf_wallrun.bsp'
    if ensure and build_cache.current(build_cache.read(manifest).get('build_cache'),stamp):return target
    OUT.mkdir(parents=True,exist_ok=True)
    boxes=[((-512,-512,-32),(3584,512,0),'CRETE3_FLR04'),((-528,-528,768),(3600,528,800),'CRETE3_WALL01'),
        ((-528,-528,-32),(-512,528,800),'CRETE3_WALL01'),((3584,-528,-32),(3600,528,800),'CRETE3_WALL01'),
        ((-512,-528,-32),(3584,-512,800),'CRETE3_WALL01'),((-512,512,-32),(3584,528,800),'CRETE3_WALL01'),
        ((0,-128,0),(2304,-96,512),'CRETE3_WALL01'),((0,96,0),(3072,128,512),'CRETE3_WALL01'),
        ((768,320,0),(1024,448,96),'CRATE01'),((768,-448,0),(800,-320,48),'CRATE01')]
    text=base.entity(dict(classname='worldspawn',message='Vector Fields - Wall run',wad='F:/SteamLibrary/steamapps/common/Half-Life/valve/halflife.wad'),[base.asset.map_box(*b)for b in boxes])
    for classname,point,yaw in [('info_player_start',(-160,-78,40),0),('info_player_deathmatch',(-160,-78,40),0),('info_player_deathmatch',(1800,78,40),180)]:
        text+=base.entity(dict(classname=classname,origin=' '.join(map(str,point)),angle=str(yaw)))
    text+=base.entity(dict(classname='game_player_equip',weapon_9mmAR='1',ammo_9mmbox='5',item_suit='1'))
    for classname,point in [('weapon_9mmAR',(-160,-78,24)),('item_suit',(-160,-60,24)),('ammo_9mmbox',(-160,-42,24))]:
        text+=base.entity(dict(classname=classname,origin=' '.join(map(str,point))))
    for x in (-256,512,1280,2048,2816,3456):
        for y in (-320,0,320):text+=base.entity(dict(classname='light',origin=f'{x} {y} 650',_light='225 240 255 1100'))
    path=OUT/'vf_wallrun.map';path.write_text(text,encoding='ascii')
    for stage in ('CSG','BSP','VIS','RAD'):
        args=[str(tools/f'sdHL{stage}_x64.exe'),'-threads','4']
        if stage=='CSG':args+=['-wadinclude','halflife.wad']
        if stage=='RAD':args+=['-bounce','1','-fast']
        result=subprocess.run(args+[str(path.with_suffix(''))],capture_output=True,text=True)
        (OUT/f'{stage}.log').write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(f'{stage} failed: {OUT/stage}')
    build_cache.write(manifest,dict(build_cache=build_cache.record(stamp,[target,path]),corridor_width=192,right_wall_length=2304,left_wall_length=3072))
    print('PASS private wall-run corridor',flush=True);return target
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ensure',action='store_true');build(parser.parse_args().ensure)
