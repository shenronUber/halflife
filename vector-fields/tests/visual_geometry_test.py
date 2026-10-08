"""Regression for inward faces, shared texture-family geometry and modular bounds."""
import json,sys,struct,itertools,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from studio_assets import Studio
import build_skins as g
from build_modular import read_smd
ROOT=Path(__file__).resolve().parents[1];SKINS=ROOT/'generated/visual_skins';WEAPONS=ROOT/'generated/weapon_visuals'

def main():
 donor=Studio(g.STEAM/'tfc/models/player/soldier/soldier2.mdl')
 mesh=donor.mesh();orientation=[np.dot(np.cross(t[1]['p']-t[0]['p'],t[2]['p']-t[0]['p']),t[0]['n']) for _,t in mesh]
 # Two tiny authored faces have inconsistent source normals; the former
 # import bug reversed virtually every face, not just those exceptions.
 assert np.mean(np.array(orientation)>0)>.99,'MDL strip/fan faces must be exported outward, matching the original SMD'
 manifest=json.loads((SKINS/'skins.json').read_text());records=manifest['characters'];assert len(records)==145
 assert len({r['display_name'] for r in records})==145
 for r in records:
  mdl=Studio(SKINS/(r['key']+'.mdl'));assert [p[1] for p in mdl.parts]==[2]*5
  assert mdl.sequences==['idle','walk'];assert np.isfinite(np.array(mdl.bind)).all()
 for base,model in [(0,'family_bastion'),(2,'family_eclaireur'),(32,'family_hev')]:
  a=Studio(SKINS/(model.replace('family_','base_')+'.mdl'));b=Studio(SKINS/(model+'.mdl'))
  for zone in range(5):
   choice={z:int(zone==z) for z in range(5)}
   def points(s):return sorted(tuple(np.round(v['p'],4)) for _,t in s.mesh(choice) for v in t)
   assert points(a)==points(b),(model,zone,'texture families must keep geometry exactly identical')
  assert struct.unpack_from('<i',b.data,196)[0]==4,'original plus three dye families'
 report=json.loads((WEAPONS/'manifest.json').read_text());assert len(report['pieces'])==12
 for r in report['pieces']+[report['adapters']]:
  s=Studio(WEAPONS/(r['key']+'.mdl'));assert s.names==['module_root'] and np.allclose(s.bind[0],np.eye(4),atol=1e-5)
  mesh=s.mesh();points=np.array([v['p'] for _,t in mesh for v in t]);assert np.isfinite(points).all() and abs(points).max()<64
  assert len(mesh)==r['triangles'];assert hashlib.sha256(s.data).hexdigest()==r['sha256']
 weights=[]
 for variants in itertools.product(range(3),repeat=4):
  weights.append(sum(next(p['triangles'] for p in report['pieces'] if p['zone']==z and p['variant']==v) for z,v in enumerate(variants))+report['adapters']['triangles'])
 result={'characters':145,'shared_meshes':3,'texture_variants':9,'modules':12,'combinations':81,'module_triangles_min':min(weights),'module_triangles_max':max(weights),'checks':['MDL winding matches outward SMD convention','all five-zone rigs compile with shared animation contract','texture-family geometry is identical','all socket modules have identity roots and finite bounds']}
 (ROOT/'build/visual-geometry-verification.json').write_text(json.dumps(result,indent=2));print('PASS:',result)

if __name__=='__main__':main()
