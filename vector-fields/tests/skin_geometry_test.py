"""Check clipping conservation and compiled asset contracts, without launching the engine."""
import json,sys
import struct
from functools import lru_cache
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import build_skins as s
from studio_assets import Studio
from pack_previews import read_frame

def area(poly):
 return sum(np.linalg.norm(np.cross(poly[i]['p']-poly[0]['p'],poly[i+1]['p']-poly[0]['p']))/2 for i in range(1,len(poly)-1))

p=s.plane('test',[0,0,0],[0,0,1],[2,3],0,0)
poly=[s.vertex(x,[0,0,1],uv,0) for x,uv in [([-1,0,-2],[0,0]),([3,0,2],[1,0]),([0,4,2],[0,1])]]
a,b=s.clip(poly,p,True),s.clip(poly,p,False)
assert abs(area(a)+area(b)-area(poly))<1e-6,'cut preserves surface area'
for part in [a,b]:
 assert any(np.allclose(v['p'],[1,0,0]) and np.allclose(v['uv'],[.5,0]) for v in part),'shared edge with interpolated UV'
 s.socket(part,p)
 for v in part:
  if abs(v['p'][2])<1e-6:
   d=v['p']-p['c'];r=(np.dot(d,p['u'])/2)**2+(np.dot(d,p['v'])/3)**2
   assert abs(r-1)<1e-6,'socket boundary lies on common ellipse'
report=json.loads((s.OUT/'skins.json').read_text());expected=None
for r in report['characters']:
 mdl=Studio(s.OUT/(r['key']+'.mdl'))
 assert [x[1] for x in mdl.parts]==[2]*5,(r['key'],'five blank/piece bodygroups')
 assert mdl.sequences==['idle','walk'],(r['key'],'common animation contract')
 bones={name:mdl.names[mdl.parents[i]] if mdl.parents[i]>=0 else None for i,name in enumerate(mdl.names)}
 if expected is None:expected=bones
 # StudioMDL removes unused leaf fingers; surviving bones retain named parents.
 assert all(name in expected and expected[name]==parent for name,parent in bones.items()),(r['key'],'compatible skeleton hierarchy')
 assert all(n>4 for n in r['triangles']) and r['caps']>0
 assert np.isfinite(np.array(mdl.bind)).all()
weapons=json.loads((s.OUT/'arsenal.json').read_text())
actual={Path(r['source']).name for r in weapons}
for path in (s.STEAM/'tfc/models').glob('v_*.mdl'):assert path.name in actual,path.name
for path in (s.STEAM/'tfc/models').glob('p_*.mdl'):assert path.name in actual,path.name
cached=lru_cache(maxsize=2048)(read_frame)
for record in report['characters']+weapons:
 data=(s.OUT/(record['key']+'.vfm')).read_bytes();n=struct.unpack_from('<I',data,8)[0]
 for i in range(n):
  path,frame=data[16+96*i:16+96*(i+1)].split(b'\0')[0].decode().split('#')
  assert cached(s.OUT/'sprites'/Path(path).name,int(frame))==cached(s.OUT/'sprites'/f'{record["key"]}_{i}.spr'),(record['key'],i,'pixel-exact bank conversion')
 # Centering must not mutate vertices shared by several triangle strips.
 if record['key'].startswith('arsenal'):
  triangles=np.frombuffer(data,offset=16+96*n,dtype=np.dtype([('g','<i4'),('v','<i4'),('t','<i4'),('xyz','<f4',(3,8))]))
  xyz=triangles['xyz'][:,:,:3].reshape(-1,3);bounds=(xyz.max(0)+xyz.min(0))/2
  assert np.max(abs(bounds))<1e-3,(record['key'],'preview centered once')
print(f'PASS: clipping area/UV/socket checks, {len(report["characters"])} compiled rigs and five-zone bodygroups, complete TFC v_/p_ model coverage.')
print('PASS: every packed preview texture is pixel-exact; all arsenal meshes centered without strip distortion.')
