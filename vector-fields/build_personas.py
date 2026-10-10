"""Compile authored character textures on one five-zone Counter-Strike-derived mesh."""
import argparse,hashlib,json,shutil,collections,re,struct,itertools
from scipy.spatial.transform import Rotation
import numpy as np
import build_skins as geometry
from pathlib import Path
from PIL import Image
from build_modular import compile_model
from studio_assets import Studio,canonical
import build_cache
ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets/personas';OUT=ROOT/'generated/personas';CATALOG=ROOT/'generated/visual_skins'

def donor(config):
 return next(r for r in json.loads((CATALOG/'cs-skins.json').read_bytes())['records']if r['id']==config['base_skin'])

def input_hash(config):
 paths=[Path(__file__),ASSETS/'personas.json',ASSETS/config['reference'],Path(donor(config)['path'])]
 paths += [ASSETS/t['id']/'texture-atlas.png'for t in config['themes']]
 paths += [ROOT/'generated/modular/vf_operator.qc',ROOT/'build_skins.py']+sorted((ROOT/'generated/tfc-soldier').glob('*.smd'))
 return build_cache.fingerprint(paths+[CATALOG/'cs-skins.json']+build_cache.compiler_inputs())

def fitted_skeleton(source):
 import build_modular as base
 _,parents,old=base.skeleton(ROOT/'generated/tfc-soldier/soldier_reference_2.smd')
 byname={canonical(name):i for i,name in enumerate(source.names)}
 fitted={b:matrix.copy()for b,matrix in old.items()}
 for b,name in geometry.NODES.items():
  fitted[b]=source.bind[byname[canonical(name)]].copy()
 local={b:np.linalg.inv(fitted[parents[b]])@matrix if parents[b]>=0 else matrix for b,matrix in fitted.items()}
 oldlocal={b:np.linalg.inv(old[parents[b]])@matrix if parents[b]>=0 else matrix for b,matrix in old.items()}
 header=geometry.HEADER[:geometry.HEADER.index('skeleton')]+['skeleton','time 0']
 for b,matrix in local.items():
  values=[*matrix[:3,3],*Rotation.from_matrix(matrix[:3,:3]).as_euler('xyz')]
  header.append(str(b)+' '+' '.join(f'{v:.8f}'for v in values))
 header.append('end')
 return header,fitted,local,oldlocal

def fitted_hitboxes(source,bind):
 # Preserve the donor's anatomical hit groups in the fitted bone coordinates.
 count,offset=struct.unpack_from('<ii',source.data,156);rows=[]
 for i in range(count):
  bone,group,*bounds=struct.unpack_from('<ii6f',source.data,offset+32*i)
  # The CS donor contains a left-hand shield volume, without a shield mesh.
  # Keep only anatomical groups; an actual future shield needs its own geometry.
  if group==8:continue
  ancestor=bone
  while canonical(source.names[ancestor])not in geometry.TARGET and source.parents[ancestor]>=0:ancestor=source.parents[ancestor]
  target=geometry.TARGET[canonical(source.names[ancestor])]
  matrix=np.linalg.inv(bind[target])@source.bind[bone]
  corners=np.array([(matrix@np.r_[p,1])[:3] for p in itertools.product(*zip(bounds[:3],bounds[3:]))])
  rows.append(f'$hbox {group} "{geometry.NODES[target]}" '+' '.join(f'{v:.8f}'for v in [*corners.min(0),*corners.max(0)]))
 return rows

def build_fitted_rig(config):
 from build_modular import write_smd
 source=Studio(donor(config)['path']);header,bind,local,oldlocal=fitted_skeleton(source)
 animation_root=ROOT/'generated/tfc-soldier'
 # Both donors use compatible biped local rotation channels. Preserve their
 # animation values/order, with reference axes and lengths from the GIGN.
 for path in animation_root.glob('*.smd'):
  if 'reference'in path.name:continue
  text=path.read_text();rows=text.splitlines();inside=False;changed=[]
  for row in rows:
   if row=='skeleton':inside=True;changed.append(row);continue
   if row=='end':inside=False
   if inside and not row.startswith('time '):
    values=row.split()
    if len(values)==7:
     b=int(values[0]);position=np.array(list(map(float,values[1:4])))+local[b][:3,3]-oldlocal[b][:3,3]
     row=str(b)+' '+' '.join(f'{v:.8f}'for v in position)+' '+' '.join(values[4:])
   changed.append(row)
  (OUT/path.name).write_text('\n'.join(changed)+'\n')
 anchors=[]
 for b,matrix in bind.items():
  center=matrix[:3,3];tri=[geometry.vertex(center+offset,[0,0,1],[.5,.5],b)for offset in (np.array([0.,0,0]),np.array([.02,0,0]),np.array([0,.02,0]))]
  anchors.append(('persona_original.bmp',tri))
 write_smd(OUT/'persona_anchors.smd',header,geometry.smd_tri(anchors))
 qc=(ROOT/'generated/modular/vf_operator.qc').read_text()
 qc=qc.replace('vf_operator.mdl','persona_rig.mdl')
 qc=re.sub(r'\$bodygroup\s+\w+\s*\{.*?\}', '',qc,flags=re.S)
 qc=re.sub(r'^\$hbox .*$', '',qc,flags=re.M)
 qc+='\n'+'\n'.join(fitted_hitboxes(source,bind))+'\n'
 # The renderer hides the carrier. Keep a complete fallback for corpses.
 zones,_=tailored_mesh(config)
 write_smd(OUT/'persona_body.smd',header,geometry.smd_tri([t for zone in zones for t in zone]))
 qc+='\n$body rig "persona_anchors"\n$body body "persona_body"\n'
 path=OUT/'persona_rig.qc';path.write_text(qc);compile_model(path)
 rig=Studio(path.with_suffix('.mdl'));oldrig=Studio(ROOT/'generated/modular/vf_operator.mdl')
 assert rig.sequences==oldrig.sequences
 return header,dict(model='persona_rig',sequences=len(rig.sequences),source='TFC animation rotations, GIGN anatomical bone origins',bone_names=rig.names)

def tailored_mesh(config):
 source=Studio(donor(config)['path']);mapping={}
 for b,name in enumerate(source.names):
  a=b
  while canonical(source.names[a])not in geometry.TARGET and source.parents[a]>=0:a=source.parents[a]
  mapping[b]=(a,geometry.TARGET.get(canonical(source.names[a]),0))
 triangles=source.mesh();buckets=collections.defaultdict(list)
 for _,tri in triangles:
  for v in tri:v['b']=mapping[v['b']][1]
 for _,tri in triangles:
  for v in tri:buckets[tuple(np.round(v['source'],4))].append(v)
 for vertices in buckets.values():
  assert len({v['b']for v in vertices})==1,'Donor seam has incompatible bone weights'
  position=np.mean([v['p']for v in vertices],axis=0)
  for v in vertices:v['p']=position.copy()
 zones=[[]for _ in range(5)];labels=[]
 for material,tri in triangles:
  assert material==0,'This GIGN base must use its single body atlas'
  center=np.mean([v['source']for v in tri],axis=0)
  # Select whole existing GIGN faces at its own neck, glove cuffs, belt and
  # boot rims. No projected socket profiles, cuts, caps or added collars.
  zone=0 if center[2]>59.15 and abs(center[0])<5 else 2 if abs(center[0])>28 else 4 if center[2]<9.5 else 3 if center[2]<40 else 1
  zones[zone].append(('persona_original.bmp',tri));labels.append(zone)
 return zones,dict(source=donor(config)['path'],source_triangles=len(triangles),zone_triangles=list(map(len,zones)),face_zones=labels,added_triangles=0,collars=0)

def build(ensure=False):
 config=json.loads((ASSETS/'personas.json').read_text(encoding='utf-8'));digest=input_hash(config)
 manifest=OUT/'manifest.json';model=config['model'];catalog=CATALOG/'skins.txt'
 if ensure and manifest.exists():
  old=json.loads(manifest.read_text())
  if build_cache.current(old.get('build_cache'),digest):
   keys={x.split('|')[1]for x in catalog.read_text().splitlines()if x}
   if 'persona_gign'in keys and all(t['key']in keys for t in old['themes']):print('Character texture families are current.');return old
 OUT.mkdir(parents=True,exist_ok=True)
 materials=['persona_original.bmp']
 Image.open(ASSETS/config['reference']).convert('RGB').quantize(256).save(OUT/materials[0])
 for theme in config['themes']:
  source=ASSETS/theme['id']/'texture-atlas.png';im=Image.open(source).convert('RGB')
  assert abs(im.width/im.height-1)<.01,source
  name='persona_'+theme['key']+'.bmp'
  im.resize((512,512),Image.Resampling.LANCZOS).quantize(256).save(OUT/name)
  materials.append(name)
 header,rig=build_fitted_rig(config)
 zones,tailoring=tailored_mesh(config)
 for z,triangles in enumerate(zones):
  from build_modular import write_smd
  write_smd(OUT/f'{model}_{z}.smd',header,geometry.smd_tri(triangles))

 qc=f'$modelname "{model}.mdl"\n$cd "."\n$cdtexture "."\n'
 for z,zone in enumerate(('head','torso','hands','legs','feet')):
  qc+=f'$bodygroup {zone}\n{{\n blank\n studio "{model}_{z}"\n}}\n'
 qc+='$sequence idle "look_idle" fps 10 loop\n$sequence walk "walk" fps 20 loop\n'
 qc+='\n$texturegroup personas\n{\n'+''.join('{ "'+m+'" }\n'for m in materials)+'}\n'
 path=OUT/(model+'.qc');path.write_text(qc,encoding='ascii');compiled=compile_model(path)
 studio=Studio(compiled);assert studio.numskinfamilies==len(materials)and len(studio.parts)==5
 lines=catalog.read_text(encoding='ascii').splitlines();entries={x.split('|')[1]:i for i,x in enumerate(lines)if x};themes=[]
 for t in config['themes']:
  key='persona_'+t['key'];index=entries.get(key,len(lines));assert index<240
  line=f'{index}|{key}|GIGN / {t["title"]}|2|{model}|{t["skin"]}'
  if index==len(lines):lines.append(line)
  else:lines[index]=line
  themes.append(dict(t,key=key,id=index,model=model,atlas=str((ASSETS/t['id']/'texture-atlas.png').relative_to(ROOT))))
 basekey='persona_gign';baseid=entries.get(basekey,len(lines));line=f'{baseid}|{basekey}|GIGN / Base ajustee|2|{model}|0'
 if baseid==len(lines):lines.append(line)
 else:lines[baseid]=line
 catalog.write_text('\n'.join(lines)+'\n',encoding='ascii')
 shutil.copy2(compiled,CATALOG/compiled.name)
 shutil.copy2(OUT/'persona_rig.mdl',CATALOG/'persona_rig.mdl')
 record=dict(inputs_sha256=digest,base_skin=config['base_skin'],base_model=f'cs_skin_{config["base_skin"]}',base_entry=baseid,model=model,skin_families=len(materials),zones=5,themes=themes,triangles=sum(len(studio.mesh({i:1 if i==z else 0 for i in range(5)}))for z in range(5)),bytes=compiled.stat().st_size,sha256=hashlib.sha256(compiled.read_bytes()).hexdigest(),tailoring=tailoring,rig=rig,limits=['Original GIGN shape; compatible animation rotations on fitted bone origins; newly authored textures','same silhouette for all themes','five zones fitted to the GIGN topology; other donor bodies can have mismatched boundaries','indexed diffuse textures, no PBR or geometry relief'])
 outputs=[p for p in OUT.iterdir() if p.suffix in ('.mdl','.qc','.smd','.bmp')]+[CATALOG/(model+'.mdl'),CATALOG/'persona_rig.mdl']
 record['build_cache']=build_cache.record(digest,outputs)
 build_cache.write(manifest,record)
 print('Built',model,len(themes),'new appearances on one model;',len(lines),'catalog entries.')
 return record
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ensure',action='store_true');build(p.parse_args().ensure)
