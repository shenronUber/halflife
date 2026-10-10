"""Replace legacy range mannequins with four server-driven GIGN targets."""
import argparse,importlib.util,json,hashlib,struct
import build_cache
from pathlib import Path
from import_tfc import entities,write_entities
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'generated/test-room'
POSITIONS=[(-300,-160,36),(-100,-160,36),(100,-160,36),(300,-160,36)]
def patch(data,native=True):
 rows=entities(data);kept=[]
 for e in rows:
  if e.get('classname')=='vf_range_target':continue
  if e.get('classname')=='cycler'and(e.get('model','').startswith('models/vf_tfc/')or e.get('targetname','').startswith('vf_skin_')):continue
  if e.get('classname')=='game_player_equip':e['ammo_9mmbox']='1'
  kept.append(e)
 if native:
  for x,y in [(-355,-265),(-355,-65),(300,200),(300,-200)]:
   row=dict(classname='info_player_deathmatch',origin=f'{x} {y} 36',angle='90')
   if not any(e.get('classname')==row['classname']and e.get('origin')==row['origin']for e in kept):kept.append(row)
 for i,p in enumerate(POSITIONS):kept.append(dict(classname='vf_range_target',targetname=f'vf_target_{i+1}',vf_slot=str(i),origin=' '.join(map(str,p)),angle='270'))
 return data if rows==kept else write_entities(data,kept)
def base_room(ensure=True):
 source=ROOT.parent/'weapon-lab/build_range.py'
 spec=importlib.util.spec_from_file_location('vf_base_range',source)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module.build(ensure=ensure)

def build(source=None,ensure=False):
 source=Path(source) if source is not None else base_room()
 digest=build_cache.fingerprint([Path(__file__),ROOT/'import_tfc.py',source])
 manifest=OUT/'manifest.json';target=OUT/'vf_range.bsp'
 if ensure and build_cache.current(build_cache.read(manifest).get('build_cache'),digest):return target
 OUT.mkdir(parents=True,exist_ok=True)
 before=source.read_bytes();after=patch(before);target.write_bytes(after)
 for i in range(1,15):assert struct.unpack_from('<ii',before,4+i*8)==struct.unpack_from('<ii',after,4+i*8)
 record=dict(source=str(source),source_sha256=hashlib.sha256(before).hexdigest(),sha256=hashlib.sha256(after).hexdigest(),targets=4,positions=POSITIONS,geometry_and_lighting_preserved=True,entities=entities(after),build_cache=build_cache.record(digest,[target]))
 build_cache.write(manifest,record);print('Prepared GIGN test room from authored base: four reactive targets, geometry and lighting retained');return target

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ensure',action='store_true')
 build(ensure=parser.parse_args().ensure)
