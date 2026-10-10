"""Compiled foregrip contacts, preserved tracks and continuous reload handoff."""
import json,sys,struct,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info,globals_of
from build_foregrip import grip_pose
FP=ROOT/'generated/r01'

def events(m,name):
 _,off=struct.unpack_from('<ii',m.data,164);start=off+m.sequences.index(name)*176
 n,p=struct.unpack_from('<ii',m.data,start+48)
 return m.data[p:p+n*76]

def run():
 recipe=json.loads((ROOT/'assets/animations/r01-first-person-foregrip.json').read_text(encoding='utf-8'));target=grip_pose(recipe)
 results=[];poses=0
 glove=Studio(FP/'r01_fp_gloves.mdl')
 for platform,suffix in [('bottom',''),('side','_side'),('top','_top')]:
  base=Studio(FP/f'r01_rig{suffix}.mdl');fg=Studio(FP/f'r01_rig{suffix}_fg.mdl')
  assert base.names==fg.names and base.parents==fg.parents and base.sequences==fg.sequences
  assert len(fg.sequences)==9

  # Descendants define the left limb, avoiding dependence on compiler-culling ids.
  root=fg.names.index('Bone40');left=[]
  for i in range(len(fg.names)):
   p=i
   while p>=0 and p!=root:p=fg.parents[p]
   if p==root:left.append(i)
  keep=[i for i in range(len(fg.names))if i not in left]
  gun=fg.names.index('Bone76');hand=fg.names.index('Bone42');elbow=fg.names.index('Bone40');shoulder=fg.names.index('Bone04')
  error=0.;tracks=0.;length_error=0.;handoff=0.;max_step=0.;max_wrist_step=0.
  for name in fg.sequences:
   a=sequence_frames(base,name);b=sequence_frames(fg,name)
   assert a.shape==b.shape and events(base,name)==events(fg,name)
   tracks=max(tracks,float(np.max(np.abs(a[:,keep]-b[:,keep]))))
   for t,(old,pose) in enumerate(zip(a,b)):
    g=globals_of(pose,fg.parents);og=globals_of(old,base.parents)
    for u,v in [(shoulder,elbow),(elbow,hand)]:length_error=max(length_error,abs(np.linalg.norm(g[u,:3,3]-g[v,:3,3])-np.linalg.norm(og[u,:3,3]-og[v,:3,3])))
    if name!='reload' or t==0 or t>=129:error=max(error,float(np.max(np.abs(np.linalg.inv(g[gun])@g[hand]-target))))
    if name=='reload'and 18<=t<=99:handoff=max(handoff,float(np.max(np.abs(pose[left]-old[left]))))
    if name=='reload'and t:
     max_step=max(max_step,float(Rotation.from_matrix(b[t-1,elbow,:3,:3].T@pose[elbow,:3,:3]).magnitude()*180/np.pi))
     max_wrist_step=max(max_wrist_step,float(np.linalg.norm(g[hand,:3,3]-globals_of(b[t-1],fg.parents)[hand,:3,3])))
    poses+=1
  idle=sequence_frames(fg,'idle')[0];reload=sequence_frames(fg,'reload');assert np.max(np.abs(idle[left]-reload[0,left]))<.01 and np.max(np.abs(idle[left]-reload[-1,left]))<.01
  info=sequence_info(fg,'reload');seconds=(info['frames']-1)/info['fps'];assert abs(seconds-1.5)<1e-6
  assert error<.035,(platform,error)
  assert tracks<.01,(platform,tracks)
  assert length_error<.04,(platform,length_error)
  assert handoff<.01,(platform,handoff)
  assert max_step<20,(platform,max_step)
  assert max_wrist_step<6,(platform,max_wrist_step)
  g=globals_of(idle,fg.parents);convert=np.linalg.inv(g[gun]);points=[]
  for _,tri in glove.mesh():
   for v in tri:
    n=glove.names[v['b']]
    if n=='Bone42' or n in ['Bone43','Bone44','Bone45'] or n.startswith('Bone')and n[4:].isdigit()and 47<=int(n[4:])<=62:
     points.append((convert@g[fg.names.index(n)]@np.linalg.inv(glove.bind[v['b']])@np.r_[v['p'],1])[:3])
  q=np.array(points)-[0,23,-.5];axis=np.array([0,-2,-3.6]);t=q@axis/(axis@axis)
  distance=np.linalg.norm(q-t[:,None]*axis,axis=1)-(.68+.17*np.clip(t,0,1));valid=(t>.05)&(t<.95)
  penetration=max(0.,float(-distance[valid].min()));assert penetration<.1,(platform,'grip shaft penetration',penetration)
  collar=0.
  for centre,size in [([0,23,-.55],[1.55,4,.4]),([0,21,-4.2],[1.7,1.4,.5])]:
   q=np.abs(np.array(points)-centre)-np.array(size)/2
   sdf=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(q.max(1),0)
   collar=max(collar,float(-sdf.min()))
  assert collar<.1,(platform,'foregrip collar/base penetration',collar)
  results.append(dict(platform=platform,max_grip_collar_penetration=collar,max_grip_shaft_penetration=penetration,sha256=hashlib.sha256(fg.data).hexdigest(),max_grip_error=error,max_preserved_track_error=tracks,max_arm_length_error=length_error,max_magazine_handoff_error=handoff,max_forearm_step_degrees=max_step,max_wrist_step_units=max_wrist_step,reload_seconds=seconds))
 # Meshes and finishes stay byte-for-byte identical.
 manifest=json.loads((FP/'manifest.json').read_text(encoding='utf-8'))
 for piece in manifest['pieces']:assert hashlib.sha256((FP/(piece['id']+'.mdl')).read_bytes()).hexdigest()==piece['sha256']
 report=dict(compiled_poses=poses,platforms=results,unchanged_meshes=len(manifest['pieces']),checks=['all nine native MP5 sequence indices and sound events preserved','all weapon, right-hand, magazine and bolt local tracks preserved','palm reaches angled grip at hold/fire/draw and after reload','original magazine contacts retained for the held reload phase','arm lengths retained and no forearm flips','first-person gesture completes at the existing 1.5-second reload delay','skinned palm and fingers clear the foregrip shaft and collar'])
 out=ROOT/'build/foregrip';out.mkdir(exist_ok=True);(out/'assets-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PASS foregrip assets',json.dumps(report))
 return report
if __name__=='__main__':run()
