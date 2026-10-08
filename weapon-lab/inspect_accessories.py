"""Inventory downloaded MDLs and extract accessories without destructive plane cuts."""
import base64,collections,hashlib,io,json,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'vector-fields'))
from studio_assets import Studio
import build_modular as build
OUT=ROOT/'generated'/'accessories';OUT.mkdir(parents=True,exist_ok=True)
HEADER=['version 1','nodes','0 "accessory_root" -1','end','skeleton','time 0','0 0 0 0 0 0 0','end']
# Each extraction explicitly selects original materials or a complete original bodypart.
SPECS=[
 ('acog_mp5','ACOG · MP5','Optique',355401,'models/HEV/v_9mmAR_acog.mdl',['acog.bmp','lense.bmp','knob.bmp'],1,'acog'),
 ('aimpoint_m4','Aimpoint · M4','Optique',179775,'default/HL/v_9mmar.mdl',['aim1.bmp','aim2.bmp'],None,None),
 ('eotech_aug','Holographique · AUG F10','Optique',231336,'Aug F10/v_aug.mdl',['eotech.bmp','glass.bmp'],None,None),
 ('eotech_hk','Holographique · HK416','Optique',236019,'HK 416 Animation/v_m4a1.mdl',['eotech.bmp','glass.bmp'],None,None),
 ('eotech_cso','Holographique compact · UTS15','Optique',236099,'models/v_uts15eo.mdl',['pv_itech552.bmp'],None,None),
 ('holosight_scar','Holosight · SCAR-L','Optique',224405,'Scar-L with Eotech/Behemoth Origins/v_m4a1.mdl',['holosight.bmp','glass.bmp'],None,None),
 ('suppressor_hk','Silencieux · HK416','Bouche',236019,'HK 416 Animation/v_m4a1.mdl',['silencer.bmp'],None,None),
 ('stock_hk','Crosse · HK416','Crosse',236019,'HK 416 Animation/v_m4a1.mdl',['craner.bmp'],None,None),
 ('grip_hk','Poignée verticale · HK416','Poignée',236019,'M4A1 Gold Animation/v_m4a1gold.mdl',['vert.bmp'],None,None),
 ('mag_m4','Chargeur · Twinke M4','Chargeur',618463,'1.6 hands/cstrike - czero/models/v_m4a1.mdl',['mag.bmp'],None,None),
 ('stock_m4','Crosse + tube · Twinke M4','Crosse',618463,'1.6 hands/cstrike - czero/models/v_m4a1.mdl',['stock.bmp','stocktube.bmp'],None,None),
 ('gemtech_m4','Silencieux Gemtech · M4','Bouche',618463,'1.6 hands/cstrike - czero/models/v_m4a1.mdl',['gemtech.bmp'],None,None),
]
def find_source(i,rel):
 folder=ROOT/'extracted'/str(i)
 p=folder/rel
 if p.exists():return p
 matches=[p for p in folder.rglob('*.mdl') if p.as_posix().lower().endswith(rel.lower())]
 assert len(matches)==1,(i,rel,matches)
 return matches[0]
def extract(spec):
 key,name,kind,i,rel,mats,part,rotation=spec
 path=find_source(i,rel);s=Studio(path)
 choices={k:(0 if k==part else -1) for k in range(len(s.parts))} if part is not None else None
 selected={j for j,t in enumerate(s.textures) if t[0].lower() in mats}
 assert len(selected)==len(mats),key
 triangles=[(t,vs) for t,vs in s.mesh(choices) if t in selected]
 assert triangles,key
 R=np.array([[1,0,0],[0,0,1],[0,-1,0]]) if rotation=='acog' else np.eye(3)
 points=np.array([R@v['p'] for _,tri in triangles for v in tri]);lo,hi=points.min(0),points.max(0)
 origin=(lo+hi)/2;origin[2]=lo[2]
 folder=OUT/key;folder.mkdir(exist_ok=True)
 tempnames=s.write_textures(folder,'tex')
 for j,n in enumerate(tempnames):
  if j not in selected:(folder/n).unlink()
 payload=[];smd=[];obj=['mtllib accessory.mtl'];mtl=[];counter=1
 for t in sorted(selected):
  bmp=folder/tempnames[t];im=Image.open(bmp).convert('RGB');png=io.BytesIO();im.save(png,format='PNG')
  im.save(folder/(bmp.stem+'.png'))
  flat=[]
  mtl.extend([f'newmtl mat{t}','Kd 1 1 1',f'map_Kd {bmp.stem}.png'])
  for mat,tri in triangles:
   if mat!=t:continue
   rows=[];obj.append(f'usemtl mat{t}')
   for v in tri:
    p=R@v['p']-origin;n=R@v['n'];uv=v['uv']
    flat.extend([*p,*n,*uv]);rows.append('0 '+' '.join(f'{x:.8f}' for x in [*p,*n,*uv]))
    obj.extend(['v '+' '.join(f'{x:.8f}' for x in p),'vt '+' '.join(f'{x:.8f}' for x in uv),'vn '+' '.join(f'{x:.8f}' for x in n)])
   obj.append('f '+' '.join(f'{v}/{v}/{v}' for v in range(counter,counter+3)));counter+=3
   smd.append((tempnames[t],rows))
  payload.append({'texture':'data:image/png;base64,'+base64.b64encode(png.getvalue()).decode(),'vertices':base64.b64encode(np.array(flat,dtype='<f4').tobytes()).decode(),'count':len(flat)//8})
 (folder/'accessory.obj').write_text('\n'.join(obj),encoding='utf-8');(folder/'accessory.mtl').write_text('\n'.join(mtl),encoding='utf-8')
 build.write_smd(folder/(key+'.smd'),HEADER,smd)
 (folder/'idle.smd').write_text('\n'.join(HEADER)+'\n',encoding='ascii')
 qc=folder/(key+'.qc');qc.write_text(f'$modelname "{key}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$body accessory "{key}"\n$sequence idle "idle" fps 1\n',encoding='ascii')
 model=build.compile_model(qc);compiled=Studio(model);outmesh=compiled.mesh()
 expected=np.array([[float(x) for x in row.split()[1:4]] for _,rows in smd for row in rows]);actual=np.array([v['p'] for _,tri in outmesh for v in tri])
 assert len(outmesh)==len(triangles),(key,len(outmesh),len(triangles))
 assert np.allclose(expected.min(0),actual.min(0),atol=0.011) and np.allclose(expected.max(0),actual.max(0),atol=0.011)
 assert len(compiled.names)==1 and np.allclose(compiled.bind[0],np.eye(4),atol=1e-5)
 raw=json.loads((ROOT/'catalog/expansion'/f'{i}-raw.json').read_bytes())
 report={'key':key,'name':name,'kind':kind,'source_id':i,'source':str(path.relative_to(ROOT)).replace('\\','/'),'url':raw['_sProfileUrl'],'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'materials':[s.textures[t][0]for t in sorted(selected)],'method':'complete bodypart' if part is not None else 'whole triangles by original material','triangles':len(triangles),'size':(hi-lo).tolist(),'recompiled':True,'mdl':str(model.relative_to(ROOT)).replace('\\','/'),'obj':str((folder/'accessory.obj').relative_to(ROOT)).replace('\\','/'),'license':raw.get('_sLicense'),'credits':raw.get('_aCredits'),'readback_check':'triangle count, bounds within 0.011 units (StudioMDL quantization), root identity','status':'extracted; attachment sockets and engine visual validation pending','glass':'original opaque texture preview; special transparency flags not recreated'}
 (folder/'provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(key,len(triangles),'triangles compiled',flush=True)
 return report,{'key':key,'name':name,'kind':kind,'triangles':len(triangles),'groups':payload,'size':(hi-lo).tolist()}
def inventory():
 records=json.loads((ROOT/'catalog/expansion/collection.json').read_bytes());allmodels=[]
 for r in records:
  files=[]
  for p in (ROOT/'extracted'/str(r['id'])).rglob('*'):
   if p.suffix.lower()!='.mdl':continue
   d=p.read_bytes();version=struct.unpack_from('<i',d,4)[0] if len(d)>=8 and d[:4]==b'IDST' else None
   m={'file':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':len(d),'version':version,'sha256':hashlib.sha256(d).hexdigest()}
   m['signature']=d[:4].decode('ascii',errors='replace')
   if d[:4]==b'IDSQ':m['kind']='external animation group';m['animation_version']=struct.unpack_from('<i',d,4)[0]
   if version==10:
    try:
     s=Studio(p);m['parts']=[{'name':n,'variants':c}for n,c,_ in s.parts];m['textures']=[t[0]for t in s.textures];m['sequences']=len(s.sequences)
    except Exception as e:m['inspection_error']=str(e)
   files.append(m)
  r['inventory']=files;r['formats']=dict(collections.Counter(str(x['version'])for x in files));allmodels+=files
 (ROOT/'catalog/expansion/inventory.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
 summary={'new_gamebanana_packs':len(records),'archives_bytes':sum(r['download']['bytes']for r in records),'mdl_files':len(allmodels),'unique_mdl_hashes':len({m['sha256']for m in allmodels}),'versions':dict(collections.Counter(str(m['version'])for m in allmodels)),'notes':['MDL file count includes hands, views, world models, animations and variants, not distinct weapons.','Likes and downloads are popularity signals, not visual or modularity certification.','Only the first current archive per entry was selected.']}
 (ROOT/'catalog/expansion/summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary))
if __name__=='__main__':
 inventory();reports=[];viewer=[]
 for spec in SPECS:
  r,v=extract(spec);reports.append(r);viewer.append(v)
 (OUT/'manifest.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
 (OUT/'viewer-data.json').write_text(json.dumps(viewer,separators=(',',':')),encoding='utf-8')
