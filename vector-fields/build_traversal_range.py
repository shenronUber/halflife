"""Authored vault/ledge/slide course, separate from the existing death range."""
import argparse,importlib.util,subprocess
from pathlib import Path
import build_cache
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'generated/traversal-range'
spec=importlib.util.spec_from_file_location('range_base',ROOT.parent/'weapon-lab/build_range.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def course_boxes():
 # Geometry shared by the standalone course and the combined shooting room.
 boxes=[
 ((0,-128,0),(24,128,48),'CRATE01'),((256,-128,0),(512,128,96),'CRATE01'),
 ((256,256,0),(512,384,96),'CRATE01'),((232,256,112),(520,384,144),'CRETE3_WALL01'),
 ((-640,400,0),(-384,656,512),'CRETE3_WALL01'),((1024,-600,0),(1100,-300,32),'CRATE01'),
 ((256,-600,0),(512,-400,96),'CRATE01'),((0,-600,0),(96,-400,160),'CRATE01'),
 ((1560,734,48),(1660,900,68),'CRETE3_WALL01'),
 ((1560,710,0),(1580,734,68),'CRETE3_WALL01'),((1640,710,0),(1660,734,68),'CRETE3_WALL01'),
 ((1710,900,0),(2696,924,192),'CRETE3_WALL01'),
 ((2600,690,0),(2696,900,128),'CRETE3_WALL01'),((2300,690,0),(2440,850,192),'CRETE3_WALL01'),
 ((2600,690,120),(2696,900,128),'CRATE01'),((2300,690,184),(2440,850,192),'CRATE01')]
 for step in range(12):boxes.append(((2300-step*24,586,0),(2324-step*24,686,(12-step)*16),'CRETE3_FLR04'))
 return boxes

def build(ensure=False):
 tools=ROOT.parent/'asset-probe/sdhlt/sdhlt-v1.3.0/tools/Win64'
 inputs=[Path(__file__),ROOT.parent/'asset-probe/generate_assets.py',*[tools/f'sdHL{x}_x64.exe'for x in('CSG','BSP','VIS','RAD')]]
 digest=build_cache.fingerprint(inputs);manifest=OUT/'manifest.json';target=OUT/'vf_traversal.bsp'
 if ensure and build_cache.current(build_cache.read(manifest).get('build_cache'),digest):return target
 OUT.mkdir(parents=True,exist_ok=True)
 boxes=[((-1024,-1024,-32),(4096,1024,0),'CRETE3_FLR04'),((-1040,-1040,768),(4112,1040,800),'CRETE3_WALL01'),
 ((-1040,-1040,-32),(-1024,1040,800),'CRETE3_WALL01'),((4096,-1040,-32),(4112,1040,800),'CRETE3_WALL01'),
 ((-1024,-1040,-32),(4096,-1024,800),'CRETE3_WALL01'),((-1024,1024,-32),(4096,1040,800),'CRETE3_WALL01')]+course_boxes()
 text=base.entity({'classname':'worldspawn','message':'Vector Fields - Deplacements','wad':'F:/SteamLibrary/steamapps/common/Half-Life/valve/halflife.wad'},[base.asset.map_box(*b)for b in boxes])
 for c,p,yaw in [('info_player_start',(-160,0,40),0),('info_player_deathmatch',(-160,0,40),0),('info_player_deathmatch',(128,-480,40),90),('info_player_deathmatch',(192,480,40),270)]:text+=base.entity(dict(classname=c,origin=' '.join(map(str,p)),angle=str(yaw)))
 text+=base.entity(dict(classname='game_player_equip',weapon_9mmAR='1',ammo_9mmbox='5',item_suit='1'))
 # Physical pickups also equip a single-player arrival through the F9 map bind.
 for classname,point in [('weapon_9mmAR',(-160,0,24)),('item_suit',(-160,16,24)),('ammo_9mmbox',(-160,-16,24))]:text+=base.entity(dict(classname=classname,origin=' '.join(map(str,point))))
 for x in (-700,0,700,1400,2100,2800,3500):
  for y in(-700,0,700):text+=base.entity(dict(classname='light',origin=f'{x} {y} 650',_light='225 240 255 1100'))
 path=OUT/'vf_traversal.map';path.write_text(text,encoding='ascii')
 for stage in('CSG','BSP','VIS','RAD'):
  args=[str(tools/f'sdHL{stage}_x64.exe'),'-threads','4']
  if stage=='CSG':args+=['-wadinclude','halflife.wad']
  if stage=='RAD':args+=['-bounce','1','-fast']
  result=subprocess.run(args+[str(path.with_suffix(''))],capture_output=True,text=True)
  (OUT/(stage+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 build_cache.write(manifest,dict(build_cache=build_cache.record(digest,[target,path]),course=dict(vault_top=48,ledge_top=96,blocked_ledge=(256,256,96),fall_tower=512,slide_runway_length=3800,wall_jump=dict(first_top=96,second_top=160,gap=160,y=-500),library=dict(start=[1440,882,36],slide_clearance=48,wall_y=900,launch_top=128,receiving_top=144,gap=160,lip_y=770,return_stair_rise=16,concept='concept-art/2026-10-12-parcours/06-librairie-etude-de-volumes.png'))))
 print('PASS traversal course',target);return target
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ensure',action='store_true');build(p.parse_args().ensure)
