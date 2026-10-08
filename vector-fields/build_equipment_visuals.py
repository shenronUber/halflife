"""Build low-poly equipment accessories from primitives, with six family silhouettes.
Existing Half-Life models remain local; this generator creates new accessory meshes.
"""
import json,sys,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
import build_modular as base
import build_skins as geometry
from build_weapon_visuals import box,HEADER
from studio_assets import Studio
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'generated/equipment_visuals'
FAMILIES=['Baseline','Predator','Fortress','Rogue','Engine','Anomalous']
COLORS=[(128,151,165),(208,153,63),(62,111,179),(45,155,131),(139,80,185),(200,65,107)]
SLOTS=['shoulders','belt','shield','special','muzzle','feed','chamber','ammo','projectile','optic','power','cooling']
BONES={'shoulders':'Bip01 Spine3','belt':'Bip01 Pelvis','shield':'Bip01 L Arm2','special':'Bip01 Spine3'}


def housing(lo,hi):
 lo=np.array(lo,float);hi=np.array(hi,float);center=(lo+hi)/2;half=(hi-lo)/2
 ring=[(-.65,-1),(.65,-1),(1,-.65),(1,.65),(.65,1),(-.65,1),(-1,.65),(-1,-.65)]
 verts=[np.array([center[0]+a*half[0],y,center[2]+b*half[2]]) for y in (lo[1],hi[1]) for a,b in ring]
 faces=[list(range(7,-1,-1)),list(range(8,16))]+[[i,(i+1)%8,(i+1)%8+8,i+8] for i in range(8)];result=[]
 for face in faces:
  n=np.cross(verts[face[1]]-verts[face[0]],verts[face[2]]-verts[face[0]]);n/=np.linalg.norm(n)
  result+=geometry.fan('connector.bmp',[geometry.vertex(verts[i],n,[(j%2),(j//2)%2],0) for j,i in enumerate(face)])
 return result

def tube(lo,hi):
 lo=np.array(lo,float);hi=np.array(hi,float);c=(lo+hi)/2;h=(hi-lo)/2;result=[]
 for i in range(10):
  angle=np.array([i,i+1])*2*np.pi/10
  points=[]
  for y,r in [(lo[1],1),(hi[1],1),(hi[1],.64),(lo[1],.64)]:
   points.extend([np.array([c[0]+np.cos(a)*h[0]*r,y,c[2]+np.sin(a)*h[2]*r]) for a in angle])
  for ids in [(0,1,3,2),(2,3,5,4),(4,5,7,6),(6,7,1,0)]:
   n=np.cross(points[ids[1]]-points[ids[0]],points[ids[2]]-points[ids[0]]);n/=np.linalg.norm(n)
   result+=geometry.fan('connector.bmp',[geometry.vertex(points[k],n,uv,0) for k,uv in zip(ids,[(0,0),(1,0),(1,1),(0,1)])])
 return result

def shapes(slot,f):
 scale=[1.,.85,1.3,.65,1.1,.95][f]
 if slot=='shoulders': parts=[([-13,-3,55],[-8,4,60]),([8,-3,55],[13,4,60])]
 elif slot=='belt':parts=[([-8,-6,39],[-3,-3,43]),([3,-6,39],[8,-3,43])]
 elif slot=='shield':parts=[([10,-7,37],[14,-3,50])]
 elif slot=='special':parts=[([-5,4,45],[5,9,57])]
 elif slot=='muzzle':parts=[([-1,31,1],[1,35,3])]
 elif slot=='feed':parts=[([-1.6,3,-5],[1.6,6,-2])]
 elif slot=='chamber':parts=[([1.8,5,.5],[3.3,12,2])]
 elif slot=='ammo':parts=[([-3,4,1.8],[-1.8,7,3.3])]
 elif slot=='projectile':parts=[([-1,16,3],[1,19,4.1])]
 elif slot=='optic':parts=[([-.8,6,3],[.8,13,5.2])]
 elif slot=='power':parts=[([-3.4,-3,-1],[-1.8,2,1])]
 else:parts=[([1.5,18,-.1],[3.2,24,2])]
 result=[]
 for lo,hi in parts:
  lo=np.array(lo,float);hi=np.array(hi,float);center=(lo+hi)/2;half=(hi-lo)/2*scale
  result+=(tube if slot in ("optic","muzzle","ammo","power") else housing)(center-half,center+half)
  # Faceplate and ribs make the family readable beyond its color.
  if f in (2,4,5):
   for j in range(2 if f==2 else 3):
    a=center-half*.85;b=center+half*.85
    a[2]=center[2]+half[2]+.1+j*.38;b[2]=a[2]+.24
    result+=housing(a,b)
 return result

def main():
 OUT.mkdir(exist_ok=True)
 (OUT/'idle.smd').write_text('\n'.join(HEADER)+'\n',encoding='ascii')
 rig=Studio(ROOT/'generated/modular/vf_operator.mdl');gun=Studio(ROOT/'generated/weapon_visuals/mp40_rig.mdl');records=[]
 for f,c in enumerate(COLORS):
  im=Image.new('P',(16,16));im.putpalette([*c,*[max(0,x//3) for x in c],210,219,222]+[0]*759)
  im.putdata([1 if x in (0,15) or y in (0,15) else 2 if y==3 and 3<x<12 else 0 for y in range(16) for x in range(16)])
  im.save(OUT/f'family_{f}.bmp')
 for slot in SLOTS:
  qc=f'$modelname "eq_{slot}.mdl"\n$cd "."\n$cdtexture "."\n$origin 0 0 0 -90\n$bodygroup family\n{{\n'
  count=0
  for f in range(6):
   mesh=shapes(slot,f)
   if slot in BONES:
    inv=np.linalg.inv(rig.bind[rig.names.index(BONES[slot])])
    for _,tri in mesh:
     for v in tri:v['p']=(inv@np.r_[v['p'],1])[:3];v['n']=inv[:3,:3]@v['n']
   if slot=='feed':
    transform=np.linalg.inv(gun.bind[gun.names.index('Bone71')])@gun.bind[gun.names.index('Bone76')]
    for _,tri in mesh:
     for v in tri:v['p']=(transform@np.r_[v['p'],1])[:3];v['n']=transform[:3,:3]@v['n']
   mesh=[(f'family_{f}.bmp',t) for _,t in mesh];count+=len(mesh)
   base.write_smd(OUT/f'{slot}_{f}.smd',HEADER,geometry.smd_tri(mesh));qc+=f' studio "{slot}_{f}"\n'
  qc+='}\n$sequence idle "idle" fps 1\n';path=OUT/f'eq_{slot}.qc';path.write_text(qc,encoding='ascii')
  model=base.compile_model(path);s=Studio(model)
  assert s.parts[0][1]==6 and np.allclose(s.bind[0],np.eye(4),atol=1e-5)
  records.append(dict(slot=slot,variants=6,triangles_total=count,bytes=model.stat().st_size,sha256=hashlib.sha256(model.read_bytes()).hexdigest()))
 (ROOT/'build/equipment-assets-verification.json').write_text(json.dumps(dict(models=records,provenance='Procedural boxes and faceplates authored in this repository; no external download.'),indent=2),encoding='utf-8')
 print('PASS equipment assets:',len(records),'models,',len(records)*6,'variants')
if __name__=='__main__':main()
