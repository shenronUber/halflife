"""Verify the generated map against its authored BSP and all retained world lumps."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from build_test_room import OUT,POSITIONS,patch
from import_tfc import entities

def run():
 record=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
 source=ROOT.parent/'weapon-lab/generated/range/vf_range.bsp'
 assert Path(record['source']).resolve()==source.resolve(),'Room must use the authored map, never deployed runtime data'
 base=source.read_bytes();data=(OUT/'vf_range.bsp').read_bytes()
 assert hashlib.sha256(base).hexdigest()==record['source_sha256']
 assert hashlib.sha256(data).hexdigest()==record['sha256']
 assert data==patch(base)==patch(data)
 targets=[e for e in entities(data) if e.get('classname')=='vf_range_target']
 assert len(targets)==4 and [e['origin'] for e in targets]==[' '.join(map(str,p)) for p in POSITIONS]
 for i in range(1,15):
  a,n=struct.unpack_from('<ii',base,4+i*8);b,m=struct.unpack_from('<ii',data,4+i*8)
  assert (a,n)==(b,m) and base[a:a+n]==data[b:b+m]
 print('PASS authored room: four targets, geometry/light lumps preserved, exact generated SHA and idempotent transformation')

if __name__=='__main__':run()
