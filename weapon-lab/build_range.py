"""Build a playable movement and firing range using stock Half-Life entities."""
import importlib.util
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('asset_generator',ROOT.parent/'asset-probe'/'generate_assets.py')
asset=importlib.util.module_from_spec(spec)
spec.loader.exec_module(asset)
OUT=ROOT/'generated'/'range'
OUT.mkdir(parents=True,exist_ok=True)

def entity(properties,brushes=()):
    return '{\n'+''.join(f'"{key}" "{value}"\n' for key,value in properties.items())+'\n'.join(brushes)+'\n}\n'

brushes=[((-528,-528,-16),(528,528,0),'FIFTIES_FLR01'),
         ((-528,-528,256),(528,528,272),'CRETE3_WALL01'),
         ((-528,-528,0),(-512,528,256),'CRETE3_WALL01'),
         ((512,-528,0),(528,528,256),'CRETE3_WALL01'),
         ((-512,-528,0),(512,-512,256),'CRETE3_WALL01'),
         ((-512,512,0),(512,528,256),'CRETE3_WALL01')]
for i in range(6): brushes.append(((-450+40*i,100,0),(-410+40*i,220,16*(i+1)),'CRETE3_WALL01'))
brushes += [((-120,100,0),(-40,220,96),'CRATE01'),
            ((60,100,0),(140,220,96),'CRATE01'),
            ((240,100,0),(320,220,128),'CRATE01'),
            ((-40,-160,0),(40,-80,48),'CRATE01')]
text=entity({'classname':'worldspawn','message':'Vector Fields - Weapon Lab',
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
log=path.with_suffix('.log').read_text()
assert 'leaked' not in log.lower() and 'Error:' not in log
print('Built',path.with_suffix('.bsp'),'bytes',path.with_suffix('.bsp').stat().st_size)
