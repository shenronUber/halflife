"""Articulated mirrored right fingers on dedicated traversal carriers only."""
from types import SimpleNamespace
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from animation_assets import globals_of,sequence_frames
FIRST=43
LEFT=list(range(13,32))
MIRROR=np.diag([-1.,1.,1.,1.])

def extend(rig):
 names=rig.names.copy();parents=rig.parents.copy();bind=list(rig.bind)
 for bone in LEFT:
  names.append('VFRight_'+rig.names[bone]);parents.append(6 if rig.parents[bone]==12 else FIRST+rig.parents[bone]-13)
  bind.append(rig.bind[6]@MIRROR@np.linalg.inv(rig.bind[12])@rig.bind[bone]@MIRROR)
 model=SimpleNamespace(names=names,parents=parents,bind=np.array(bind),source=rig)
 model.extra=np.array([np.linalg.inv(model.bind[parents[i]])@model.bind[i]for i in range(FIRST,len(names))])
 return model

def idle(rig):return np.concatenate([sequence_frames(rig.source,'idle')[0],rig.extra])

def extend_smd(path,out,model,reference=False):
 text=Path(path).read_text();lines=text.splitlines();nodes=lines.index('nodes');end=lines.index('end',nodes);old={}
 import re
 for line in lines[nodes+1:end]:
  i,name,parent=re.fullmatch(r'\s*(\d+) "([^"]+)" (-?\d+)',line).groups();old[name]=int(i)
 offset=max(old.values())+1;added=[];keys=[]
 for i,bone in enumerate(LEFT):
  parent=old['Bone07'] if model.parents[FIRST+i]==6 else offset+model.parents[FIRST+i]-FIRST
  added.append(f'{offset+i} "{model.names[FIRST+i]}" {parent}')
  matrix=model.extra[i];v=[*matrix[:3,3],*Rotation.from_matrix(matrix[:3,:3]).as_euler('xyz')];keys.append(str(offset+i)+' '+' '.join(f'{x:.8f}'for x in v))
 lines[end:end]=added;start=lines.index('skeleton');end=lines.index('end',start);result=lines[:start+1]
 for line in lines[start+1:end]:
  if line.startswith('time ') and result[-1]!='skeleton':result.extend(keys)
  result.append(line)
 result.extend(keys);result.extend(lines[end:])
 if reference:
  start=result.index('triangles');end=result.index('end',start);material=result[start+1];triangles=[]
  # Invisible carrier bodygroup keeps all new bones in StudioMDL's skeleton.
  undo=np.eye(4);undo[:3,:3]=Rotation.from_euler('z',-90,degrees=True).as_matrix()
  for i in range(len(LEFT)):
   p=(undo@model.bind[FIRST+i])[:3,3];triangles.append(material)
   for delta in ([0,0,0],[.001,0,0],[0,.001,0]):triangles.append(str(offset+i)+' '+' '.join(f'{x:.8f}'for x in [*(p+delta),0,0,1,0,0]))
  result[end:end]=triangles
 Path(out).write_text('\n'.join(result)+'\n',encoding='ascii')
