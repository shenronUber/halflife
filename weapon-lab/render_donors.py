"""Generate previews from the actual GoldSrc files, not remote marketing images."""
import sys,json,base64,io
from pathlib import Path
import numpy as np
from PIL import Image
from render_accessories import render
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT.parent/'vector-fields'))
from studio_assets import Studio
OUT=ROOT/'catalog/expansion/previews';OUT.mkdir(exist_ok=True)
rows=json.loads((ROOT/'catalog/expansion/inventory.json').read_bytes());reports=[]
for r in rows:
 candidates=[m for m in r['inventory'] if m['version']==10 and Path(m['file']).name.lower().startswith('v_')]
 if not candidates:continue
 def score(m):
  n=Path(m['file']).name.lower()
  return (0 if n in ['v_m4a1.mdl','v_9mmar.mdl','v_9mmar_hev.mdl'] else 1,len(m['file']))
 p=ROOT/min(candidates,key=score)['file'];s=Studio(p);tri=s.mesh();groups=[]
 for j,t in enumerate(s.textures):
  if any(x in t[0].lower() for x in ['hand','glove','finger','sleeve','gordon','soldier_arm','view_skin']):continue
  vs=np.array([[*v['p'],*v['n'],*v['uv']]for mat,vs in tri if mat==j for v in vs],dtype='<f4')
  if not len(vs):continue
  im=Image.frombytes('P',(t[1],t[2]),t[3]);im.putpalette(t[4]);b=io.BytesIO();im.convert('RGB').save(b,format='PNG')
  groups.append({'vertices':base64.b64encode(vs.tobytes()).decode(),'texture':'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()})
 if not groups:continue
 render({'groups':groups},480,270).save(OUT/f'{r["id"]}.png')
 reports.append({'id':r['id'],'source':str(p.relative_to(ROOT)).replace('\\','/'),'note':'Bind pose, default bodygroups; hands filtered by material name; not an in-game screenshot.'})
 print(r['id'],r['name'],flush=True)
(OUT/'provenance.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
