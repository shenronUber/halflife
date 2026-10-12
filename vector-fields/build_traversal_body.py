"""Derived first-person sliding legs and open right-hand ledge glove.
Actual fitted character geometry, palette and authored skin families.
"""
import json,re
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of
from third_person import smd,transform
from traversal_animations import ik,fingers,FP_GRASP
from build_modular import compile_model
import build_cache
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'generated/traversal'

def triangle_lines(mesh,materials,undo=True):
 lines=[];rotation=transform(angles=(0,0,-90))[:3,:3]
 for material,vertices in mesh:
  lines.append(materials[material] if isinstance(material,int) else material)
  for vertex in vertices:
   p=rotation@vertex['p'] if undo else vertex['p'];n=rotation@vertex['n'] if undo else vertex['n']
   lines.append(str(vertex['b'])+' '+' '.join(f'{v:.8f}'for v in [*p,*n,*vertex['uv']]))
 return lines

def legs():
 source=Studio(ROOT/'generated/personas/persona_scout.mdl');rig=Studio(ROOT/'generated/personas/persona_rig.mdl')
 local=sequence_frames(rig,'ref_aim_mp5')[0].copy()
 # The left heel leads. The right knee faces forwards and its boot folds
 # under the seat, matching the third-person silhouette.
 g=globals_of(local,rig.parents);local[0][:3,3]+=np.array([-3.,0.,-18.])-g[1][:3,3]
 for ids,position,pole in [((2,3,4),[28,8,-14],[12,8,-3]),((5,6,7),[-3,-3,-22],[15,-4,-18])]:
  goal=np.eye(4);goal[:3,3]=position
  from traversal_aim import slide_foot_rotation,slide_tucked_foot_rotation
  goal[:3,:3]=slide_foot_rotation() if ids[0]==2 else slide_tucked_foot_rotation()
  ik(local,rig.parents,ids,goal,pole)
 g=globals_of(local,rig.parents);mapping={i:(i,rig.names.index(name))for i,name in enumerate(source.names)}
 materials=source.write_textures(OUT,'slide_skin');model=SimpleNamespace(names=['VF_SlideLegs'],parents=[-1]);frame=np.array([[np.eye(4)]])
 qc='$modelname "slide_legs.mdl"\n$cd "."\n$cdtexture "."\n';counts=[];bounds=[]
 for part,label in [(3,'legs'),(4,'feet')]:
  mesh=source.mesh(choices={i:1 if i==part else 0 for i in range(5)},target=g,mapping=mapping)
  for _,vertices in mesh:
   for v in vertices:v['b']=0;bounds.append(v['p'])
  counts.append(len(mesh));smd(model,frame,OUT/('slide_'+label+'.smd'),triangle_lines(mesh,materials))
  qc+='$bodygroup '+label+'\n{\n blank\n studio "slide_'+label+'"\n}\n'
 smd(model,frame,OUT/'slide_idle.smd');qc+='$sequence idle "slide_idle" fps 1\n$texturegroup personas\n{\n'
 qc+=''.join('{ "'+materials[source.skin[skin*source.numskinref]]+'" }\n'for skin in range(source.numskinfamilies))+'}\n'
 path=OUT/'slide_legs.qc';path.write_text(qc,encoding='ascii');compiled=Studio(compile_model(path));assert compiled.numskinfamilies==source.numskinfamilies
 # Existing view carriers keep their complete historical skeleton. A static
 # seated mesh attaches to Bone01 with its bind transform cancelled exactly.
 view=Studio(ROOT/'generated/r01/r01_rig.mdl');root=globals_of(sequence_frames(view,'idle')[0],view.parents)[0];socket=np.linalg.inv(root)
 record=dict(model='slide_legs.mdl',triangles=counts,skin_families=compiled.numskinfamilies,bounds=[np.min(bounds,axis=0).tolist(),np.max(bounds,axis=0).tolist()],socket=dict(bone='Bone01',offset=socket[:3,3].tolist(),angles=Rotation.from_matrix(socket[:3,:3]).as_euler('xyz',degrees=True).tolist()))
 return record

def open_glove():
 from traversal_hands import extend,MIRROR
 source=Studio(ROOT/'generated/r01/r01_fp_gloves.mdl');rig=extend(Studio(ROOT/'generated/r01/r01_rig.mdl'))
 local=np.array([np.linalg.inv(rig.bind[p])@rig.bind[i]if p>=0 else rig.bind[i]for i,p in enumerate(rig.parents)])
 kept=[];new=[]
 # Rebuild the entire right glove from the articulated left glove, including
 # wrist/forearm seam triangles. Keeping mixed old right-hand triangles left
 # a few vertices bound to the original weapon-grip thumb.
 right_bones={10:4,11:5,12:6}|{i:i+30 for i in range(13,32)}
 for material,vertices in source.mesh():
  bones=[v['b']for v in vertices]
  if not all(10<=b<=31 for b in bones):continue
  left=[];right=[]
  for v in vertices:
   b=rig.names.index(source.names[v['b']]);matrix=rig.bind[b]@np.linalg.inv(source.bind[v['b']])
   left.append(dict(p=(matrix@np.r_[v['p'],1])[:3],n=matrix[:3,:3]@v['n'],b=b,uv=v['uv']))
  for v in reversed(vertices):
   left_bone=rig.names.index(source.names[v['b']])
   matrix=rig.bind[6]@MIRROR@np.linalg.inv(rig.bind[12])@rig.bind[left_bone]@np.linalg.inv(source.bind[v['b']])
   right.append(dict(p=(matrix@np.r_[v['p'],1])[:3],n=matrix[:3,:3]@v['n'],b=right_bones[left_bone],uv=v['uv']))
  kept.append((material,left));new.append((material,right))
 qc=(ROOT/'generated/r01/r01_fp_gloves.qc').read_text().replace('r01_fp_gloves','ledge_gloves').replace('$cdtexture "."','$cdtexture "../r01"').replace('"mp40_hands"','"ledge_gloves"')
 smd(rig,np.array([local]),OUT/'ledge_gloves.smd',triangle_lines(kept+new,[t[0]for t in source.textures]))
 path=OUT/'ledge_gloves.qc';path.write_text(qc,encoding='ascii');compiled=Studio(compile_model(path));assert compiled.numskinfamilies==source.numskinfamilies
 return dict(model='ledge_gloves.mdl',triangles=len(kept+new),skin_families=compiled.numskinfamilies,articulated_right_fingers=19)


def both_sleeves():
 source=Studio(ROOT/'generated/r01/r01_fp_sleeves.mdl');rig=Studio(ROOT/'generated/r01/r01_rig.mdl')
 local=np.array([np.linalg.inv(rig.bind[p])@rig.bind[i] if p>=0 else rig.bind[i] for i,p in enumerate(rig.parents)])
 mirror=np.diag([-1.,1.,1.]);mesh=[]
 for material,vertices in source.mesh():
  left=[];right=[]
  for v in vertices:
   relative=np.linalg.inv(source.bind[v['b']])@np.r_[v['p'],1]
   normal=source.bind[v['b']][:3,:3].T@v['n']
   left.append(dict(p=(rig.bind[10]@relative)[:3],n=rig.bind[10][:3,:3]@normal,b=10,uv=v['uv']))
   right.append(dict(p=(rig.bind[4]@np.r_[mirror@relative[:3],1])[:3],n=rig.bind[4][:3,:3]@mirror@normal,b=4,uv=v['uv']))
  mesh.extend([(material,left),(material,list(reversed(right)))])
 qc=(ROOT/'generated/r01/r01_fp_sleeves.qc').read_text().replace('r01_fp_sleeves','ledge_sleeves').replace('$cdtexture "."','$cdtexture "../r01"').replace('"mp40_hands"','"ledge_sleeves"')
 smd(rig,np.array([local]),OUT/'ledge_sleeves.smd',triangle_lines(mesh,[t[0]for t in source.textures]))
 path=OUT/'ledge_sleeves.qc';path.write_text(qc,encoding='ascii');compiled=Studio(compile_model(path))
 assert compiled.numskinfamilies==source.numskinfamilies
 return dict(model='ledge_sleeves.mdl',triangles=len(mesh),skin_families=compiled.numskinfamilies)

def build(ensure=False):
 OUT.mkdir(parents=True,exist_ok=True);manifest=OUT/'body_manifest.json'
 inputs=[ROOT/'traversal_hands.py',Path(__file__),ROOT/'traversal_animations.py',ROOT/'traversal_aim.py',ROOT/'third_person.py',ROOT/'animation_assets.py',ROOT/'generated/personas/persona_scout.mdl',ROOT/'generated/personas/persona_rig.mdl',ROOT/'generated/r01/r01_rig.mdl',ROOT/'generated/r01/r01_fp_gloves.mdl',ROOT/'generated/r01/r01_fp_gloves.qc',ROOT/'generated/r01/r01_fp_sleeves.mdl',ROOT/'generated/r01/r01_fp_sleeves.qc']+list((ROOT/'generated/r01').glob('fp_gloves_*.bmp'))+list((ROOT/'generated/r01').glob('fp_sleeves_*.bmp'))+build_cache.compiler_inputs()
 digest=build_cache.fingerprint(inputs)
 if ensure and build_cache.current(build_cache.read(manifest).get('build_cache'),digest):print('Traversal body meshes are current.');return
 record=dict(legs=legs(),gloves=open_glove(),sleeves=both_sleeves());build_cache.write(manifest,dict(**record,build_cache=build_cache.record(digest,[OUT/'slide_legs.mdl',OUT/'ledge_gloves.mdl',OUT/'ledge_sleeves.mdl',OUT/'ledge_sleeves.qc',OUT/'slide_legs.qc',OUT/'ledge_gloves.qc'])))
 print('PASS traversal body meshes',json.dumps(record))
if __name__=='__main__':build()
