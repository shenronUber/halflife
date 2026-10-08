"""Cut three donor weapons into closed components in the MP40 socket space.

Geometry only. The nine original MP40 sequences still drive the hands and
magazine. Source archives, author credits and checksums remain local.
"""
import json,shutil,re,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
import build_modular as base
import build_skins as geometry
from studio_assets import Studio
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
OUT=ROOT/'generated/weapon_visuals'
HEADER=['version 1','nodes','0 "module_root" -1','end','skeleton','time 0','0 0 0 0 0 0 0','end']
ZONE_NAMES=['Corps','Canon','Crosse','Avant']
PLANES=[geometry.plane('rear',[0,-6,1],[0,1,0],[1.8,1.35],0,0),
        geometry.plane('front',[0,16,1],[0,1,0],[1.8,1.5],0,0),
        geometry.plane('barrel',[0,22,2],[0,1,0],[.85,.85],0,0)]
for p in PLANES:p['width']=2.

def compile_piece(key,triangles):
 assert triangles,key
 base.write_smd(OUT/(key+'.smd'),HEADER,geometry.smd_tri(triangles))
 qc=OUT/(key+'.qc');qc.write_text(f'$modelname "{key}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$body module "{key}"\n$sequence idle "module_idle" fps 1\n')
 model=base.compile_model(qc);s=Studio(model)
 assert len(s.names)==1 and np.allclose(s.bind[0],np.eye(4),atol=1e-5)
 return {'key':key,'triangles':len(triangles),'bytes':model.stat().st_size,'sha256':hashlib.sha256(model.read_bytes()).hexdigest()}

def cut_piece(triangles,zone):
 tests={0:[(PLANES[0],True),(PLANES[1],False)],1:[(PLANES[2],True)],2:[(PLANES[0],False)],3:[(PLANES[1],True),(PLANES[2],False)]}[zone]
 out=[];boundaries={}
 for mat,triangle in triangles:
  poly=[geometry.clone(v) for v in triangle]
  for p,pos in tests:poly=geometry.clip(poly,p,pos)
  if len(poly)<3:continue
  for p,pos in tests:
   geometry.socket(poly,p)
   boundaries.setdefault((p['name'],pos),[]).extend(geometry.segments(poly,p))
  out+=geometry.fan(mat,poly)
 for p,pos in tests:out+=geometry.close_cap(boundaries.get((p['name'],pos),[]),p,pos,'connector.bmp',np.array([.5,.5]))
 return out

def box(lo,hi):
 p=[np.array([hi[0] if i&1 else lo[0],hi[1] if i&2 else lo[1],hi[2] if i&4 else lo[2]],float) for i in range(8)]
 result=[]
 for ids in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]:
  n=np.cross(p[ids[1]]-p[ids[0]],p[ids[2]]-p[ids[0]]);n/=np.linalg.norm(n)
  result+=geometry.fan('connector.bmp',[geometry.vertex(p[i],n,uv,0) for i,uv in zip(ids,[(0,0),(1,0),(1,1),(0,1)])])
 return result

def main():
 OUT.mkdir(exist_ok=True);(OUT/'module_idle.smd').write_text('\n'.join(HEADER)+'\n')
 im=Image.new('P',(8,8),0);im.putpalette([48,52,54,65,71,73]+[0]*762);im.putdata([(x+y)%2 for y in range(8) for x in range(8)]);im.save(OUT/'connector.bmp')
 source=ROOT/'generated/mp40';header,names,triangles=base.read_smd(source/'reference.smd');_,_,bind=base.skeleton(source/'reference.smd')
 bone=next(i for i,n in names.items() if n=='Bone76');mag=next(i for i,n in names.items() if n=='Bone71');inv=np.linalg.inv(bind[bone])
 hands=[];magazine=[];mp40=[]
 for material,rows in triangles:
  shutil.copy2(source/material,OUT/material)
  if not material.startswith('skin'):hands.append((material,rows));continue
  if all(int(row.split()[0]) in (mag,mag+1) for row in rows):magazine.append((material,rows));continue
  vertices=[]
  for row in rows:
   f=row.split();p=inv@np.array([*map(float,f[1:4]),1]);n=inv[:3,:3]@np.array(list(map(float,f[4:7])))
   vertices.append(geometry.vertex(p[:3],n,list(map(float,f[7:9])),0))
  mp40.append((material,vertices))
 base.write_smd(OUT/'mp40_hands.smd',header,hands);base.write_smd(OUT/'mp40_mag.smd',header,magazine)
 for path in source.glob('*.smd'):
  if path.name!='reference.smd':shutil.copy2(path,OUT/path.name)
 qc=(source/'v_9mmar.qc').read_text().replace('"v_9mmar.mdl"','"mp40_rig.mdl"').replace('$body "studio" "reference"','$bodygroup hands\n{\n blank\n studio "mp40_hands"\n}\n$bodygroup magazine\n{\n blank\n studio "mp40_mag"\n}')
 qc=re.sub(r'^\$(?:texrendermode|hbox).*\n','',qc,flags=re.M)
 (OUT/'mp40_rig.qc').write_text(qc);base.compile_model(OUT/'mp40_rig.qc')
 donors=[('mp40','MP40',mp40)]
 for key,label,path,bone,scale,offset in [
   ('nail','Nailgun TFC',Path('F:/SteamLibrary/steamapps/common/Half-Life/tfc/models/v_tfc_nailgun.mdl'),'Cylinder01',[.55,1.65,.7],[-2.05,12,-.3]),
   ('tommy','Thompson',PROJECT/'weapon-lab/extracted/351127/AI_HEV/v_9mmar.mdl','GUN',[-1,-1.4,.8],[-1,8.6,-.8])]:
  s=Studio(path);materials=s.write_textures(OUT,key);inv=np.linalg.inv(s.bind[s.names.index(bone)]);mesh=[];scale=np.array(scale);offset=np.array(offset)
  for mat,t in s.mesh():
   if mat>2:continue
   if key=='tommy' and any(s.names[v['b']] in ('MAG','BOOLIT') for v in t):continue
   vertices=[]
   for v in t:
    p=(inv@np.r_[v['p'],1])[:3]*scale+offset;n=(inv[:3,:3]@v['n'])/scale;n/=np.linalg.norm(n)
    vertices.append(geometry.vertex(p,n,v['uv'],0))
   mesh.append((materials[mat],vertices))
  donors.append((key,label,mesh))
 records=[];lines=[]
 # Twelve selectable pieces, three per slot. A small custom stock gives the
 # stock-less nailgun donor a useful interchangeable rear module.
 for zone in range(4):
  for variant,(key,label,mesh) in enumerate(donors):
   if zone==2 and key=='nail':
    part=box([-.65,-16,.3],[.65,-6,1.7])+box([-1,-17,-3],[1,-15.5,2.7]);label='Atelier tubulaire'
   else:part=cut_piece(mesh,zone)
   record=compile_piece(f'{key}_{zone}',part);record.update(zone=zone,variant=variant,name=f'{ZONE_NAMES[zone]} / {label}');records.append(record)
   lines.append(f'{len(lines)}|{record["key"]}|{record["name"]}|{zone}')
 adapters=[]
 for plane in PLANES:adapters+=geometry.band(plane,'connector.bmp',np.array([.5,.5]))
 adapters=compile_piece('adapters',adapters)
 report={'version':1,'rig':'mp40_rig','socket':'Bone76','pieces':records,'adapters':adapters,'combinations':3**4,
  'sources':[{'url':'https://gamebanana.com/mods/179714','authors':'Valve; GeneralRain01','use':'local visual study'},
             {'url':'https://gamebanana.com/mods/351127','credits_metadata':'weapon-lab/catalog/351127-raw.json','use':'local visual study'},
             {'source':'Installed Team Fortress Classic','authors':'Valve'}],
  'limitations':['Local first-person visual experiment; MP5 combat logic unchanged','MP40 hand/magazine animations reused; poses not refitted to every hybrid','Third-person weapon remains stock','No redistribution permission inferred from download availability']}
 (OUT/'weapon_modules.txt').write_text('\n'.join(lines)+'\n',encoding='ascii');(OUT/'manifest.json').write_text(json.dumps(report,indent=2))
 print('PASS: 12 modules, 3 socket adapters, 81 visual combinations; 9 original hand/magazine animations')

if __name__=='__main__':main()
