"""Build a playable movement and firing range using stock Half-Life entities."""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('asset_generator',ROOT.parent/'asset-probe'/'generate_assets.py')
asset=importlib.util.module_from_spec(spec)
spec.loader.exec_module(asset)
OUT=ROOT/'generated'/'range'

def entity(properties,brushes=()):
    return '{\n'+''.join(f'"{key}" "{value}"\n' for key,value in properties.items())+'\n'.join(brushes)+'\n}\n'

def build(ensure=False):
    # Authoring source, owned WAD and compilers define this map; no runtime BSP is read.
    sys.path.insert(0,str(ROOT.parent/'vector-fields'))
    import build_cache
    tools=ROOT.parent/'asset-probe'/'sdhlt'/'sdhlt-v1.3.0'/'tools'/'Win64'
    inputs=[Path(__file__),ROOT.parent/'asset-probe/generate_assets.py',ROOT.parent/'vector-fields/build_traversal_range.py',
            Path('F:/SteamLibrary/steamapps/common/Half-Life/valve/halflife.wad'),
            *[tools/f'sdHL{stage}_x64.exe' for stage in ('CSG','BSP','VIS','RAD')]]
    digest=build_cache.fingerprint(inputs)
    manifest=OUT/'build-cache.json';target=OUT/'vf_range.bsp'
    if ensure and build_cache.current(build_cache.read(manifest),digest):return target
    OUT.mkdir(parents=True,exist_ok=True)
    brushes=[((-528,-1040,-32),(5392,1040,0),'FIFTIES_FLR01'),
             ((-528,-1040,768),(5392,1040,800),'CRETE3_WALL01'),
             ((-528,-1040,0),(-512,1040,800),'CRETE3_WALL01'),
             ((5376,-1040,0),(5392,1040,800),'CRETE3_WALL01'),
             ((-512,-1040,0),(5376,-1024,800),'CRETE3_WALL01'),
             ((-512,1024,0),(5376,1040,800),'CRETE3_WALL01'),
             # Shooting and movement bays share a wide, walkable doorway.
             ((512,-1024,0),(528,128,256),'CRETE3_WALL01'),
             ((512,384,0),(528,1024,256),'CRETE3_WALL01')]
    from build_traversal_range import course_boxes
    for lo,hi,texture in course_boxes():
        brushes.append(((lo[0]+1280,lo[1],lo[2]),(hi[0]+1280,hi[1],hi[2]),texture))
    for i in range(6): brushes.append(((-450+40*i,100,0),(-410+40*i,220,16*(i+1)),'CRETE3_WALL01'))
    brushes += [((-120,100,0),(-40,220,96),'CRATE01'),
                ((60,100,0),(140,220,96),'CRATE01'),
                ((240,100,0),(320,220,128),'CRATE01'),
                ((-40,-160,0),(40,-80,48),'CRATE01')]
    text=entity({'classname':'worldspawn','message':'Vector Fields - Combat et parcours',
                 'wad':'F:/SteamLibrary/steamapps/common/Half-Life/valve/halflife.wad'},
                [asset.map_box(*b) for b in brushes])
    text+=entity({'classname':'info_player_start','origin':'-400 -400 40','angle':'45'})
    for x,y in [(-400,-400),(400,-400),(-400,400),(400,400)]:
        text+=entity({'classname':'info_player_deathmatch','origin':f'{x} {y} 40'})
    text+=entity({'classname':'game_player_equip','targetname':'lab_equipment','spawnflags':'1',
                  'item_suit':'1','weapon_crowbar':'1','weapon_9mmAR':'1','ammo_9mmbox':'2','ammo_ARgrenades':'1'})
    text+=entity({'classname':'trigger_once','target':'lab_equipment'},
                 [asset.map_box((-455,-455,0),(-340,-340,96),'AAATRIGGER')])
    for x in [-350,0,350]:
        for y in [-350,0,350]:
            text+=entity({'classname':'light','origin':f'{x} {y} 220','_light':'255 230 200 500'})
    for x in (900,1600,2300,3000,3700,4400,5100):
        for y in (-700,0,700):text+=entity({'classname':'light','origin':f'{x} {y} 650','_light':'225 240 255 1100'})
    for x in [-300,-100,100,300]:
        text+=entity({'classname':'func_breakable','health':'150','material':'1'},
                    [asset.map_box((x-28,400,0),(x+28,440,80),'CRATE01')])
    text+=entity({'classname':'ammo_9mmbox','origin':'-280 -400 16'})
    text+=entity({'classname':'ammo_ARgrenades','origin':'-230 -400 16'})
    path=OUT/'vf_range.map'
    path.write_text(text,encoding='ascii')
    tools=ROOT.parent/'asset-probe'/'sdhlt'/'sdhlt-v1.3.0'/'tools'/'Win64'
    for stage in ['CSG','BSP','VIS','RAD']:
        args=[str(tools/f'sdHL{stage}_x64.exe'),'-threads','2']
        if stage=='CSG': args+=['-wadinclude','halflife.wad']
        args.append(str(path.with_suffix('')))
        r=subprocess.run(args,capture_output=True,text=True)
        (OUT/(stage+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
        if r.returncode: raise RuntimeError(r.stdout+r.stderr)
    log=path.with_suffix('.log').read_text(encoding='utf-8',errors='replace')
    assert 'leaked' not in log.lower() and 'Error:' not in log
    print('Built',path.with_suffix('.bsp'),'bytes',path.with_suffix('.bsp').stat().st_size)
    build_cache.write(manifest,build_cache.record(digest,[target,OUT/'vf_range.map']))
    return target

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ensure',action='store_true')
    build(parser.parse_args().ensure)
