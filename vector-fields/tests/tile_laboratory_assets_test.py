"""The playable map has embedded blockout materials and remains in engine budgets."""
import hashlib,json,struct,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from build_tile_laboratory import OUT,build
from import_tfc import entities
from game_profiles import MAPS,menu_text
def run():
 p=build(ensure=True);data=p.read_bytes();assert struct.unpack_from('<i',data)[0]==30
 manifest=json.loads((OUT/'manifest.json').read_text());g=manifest['geometry']
 assert g['cell']==1280 and g['gap']==256 and len(g['candidates'])==141
 a,n=struct.unpack_from('<ii',data,4+14*8);assert n//64==143 and n//64<256
 a,n=struct.unpack_from('<ii',data,4+2*8);lump=data[a:a+n];textures=struct.unpack_from('<i',lump)[0]
 names=set()
 for i in range(textures):
  offset=struct.unpack_from('<i',lump,4+i*4)[0];assert offset>=0
  name,w,h,mip=struct.unpack_from('<16siii',lump,offset);name=name.rstrip(b'\0').decode();names.add(name)
  if name.startswith('VX_'):assert w==h==128 and mip==40
 assert {'VX_RUN','VX_SLIDE','VX_LEDGE','VX_PORT','VX_FLOOR'}<=names
 rows=entities(data);assert next(e for e in rows if e['classname']=='worldspawn')['skyname']=='vf_storm'
 assert sum(e['classname']=='ambient_generic'for e in rows)==5
 assert sum(e['classname']=='vf_modular_piece'for e in rows)==141
 lines=[r.split('|')for r in menu_text().splitlines()];assert {r[0]for r in lines}==set(MAPS)
 assert {int(r[1])for r in lines if r[0]=='vf_tiles'}==set(range(-1,8))
 if os.environ.get('VF_TEST_ENGINE'):
  mod=Path(os.environ['VF_TEST_ENGINE'])/'vf_visual'
  extra=[r.split('|')for r in(mod/'vf/maps-extra.txt').read_text().splitlines()]
  installed={p.stem for p in(mod/'maps').glob('*.bsp')}-set(MAPS)
  assert {r[0]for r in extra}==installed and all(r[4]=='vf_explore_start'for r in extra)
 print('PASS tile BSP: 143 brush models, embedded movement materials, sky/ambience and complete map/variant catalog')
if __name__=='__main__':run()
