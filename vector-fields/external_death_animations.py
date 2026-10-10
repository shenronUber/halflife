"""Retarget pinned glTF death tracks onto the existing GIGN Studio skeleton.
Only animation channels are imported: no donor meshes, joints or textures.
"""
import base64,hashlib,json,math,struct,warnings
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from animation_assets import globals_of
ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets/animations/death-banks'
CLIPS=[('vf_q_death','Quaternius - chute','quaternius-standard.gltf','Death01','A_TPose'),
       ('vf_k_death_a','KayKit - mort A','kaykit-general.glb','Death_A','T-Pose'),
       ('vf_k_death_b','KayKit - mort B','kaykit-general.glb','Death_B','T-Pose')]
ATLAS=json.loads((ASSETS.parent/'death-atlas.json').read_text())
CLIPS += [(m['sequence'],m['label'],m['source_file'],m['source_clip'],m['reference']) for m in ATLAS['motions'] if 'source_file' in m]

class Gltf:
 def __init__(self,path):
  self.path=Path(path);raw=self.path.read_bytes();self.buffers=[]
  if raw[:4]==b'glTF':
   assert struct.unpack_from('<II',raw,4)==(2,len(raw));p=12;binary=None
   while p<len(raw):
    size,kind=struct.unpack_from('<II',raw,p);p+=8;chunk=raw[p:p+size];p+=size
    if kind==0x4e4f534a:self.doc=json.loads(chunk)
    elif kind==0x004e4942:binary=chunk
  else:self.doc=json.loads(raw);binary=None
  for b in self.doc['buffers']:
   uri=b.get('uri');self.buffers.append(base64.b64decode(uri.split(',',1)[1]) if uri and uri.startswith('data:') else (self.path.parent/uri).read_bytes() if uri else binary)
  self.nodes=self.doc['nodes'];self.names={n.get('name',''):i for i,n in enumerate(self.nodes)};self.parents=[-1]*len(self.nodes)
  for i,n in enumerate(self.nodes):
   for j in n.get('children',[]):self.parents[j]=i
  self.rest=self.local();self.bind=self.globals(self.rest)
 def accessor(self,i):
  a=self.doc['accessors'][i];v=self.doc['bufferViews'][a['bufferView']];dtype={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];size=np.dtype(dtype).itemsize;start=v.get('byteOffset',0)+a.get('byteOffset',0)
  return np.ndarray((a['count'],n),dtype=dtype,buffer=self.buffers[v['buffer']],offset=start,strides=(v.get('byteStride',size*n),size)).copy()
 def local(self):
  out=[]
  for n in self.nodes:
   if 'matrix' in n:m=np.array(n['matrix']).reshape(4,4).T
   else:
    m=np.eye(4);m[:3,:3]=Rotation.from_quat(n.get('rotation',[0,0,0,1])).as_matrix()@np.diag(n.get('scale',[1,1,1]));m[:3,3]=n.get('translation',[0,0,0])
   out.append(m)
  return np.array(out)
 def globals(self,local):
  result={}
  def visit(i):
   if i not in result:result[i]=visit(self.parents[i])@local[i] if self.parents[i]>=0 else local[i]
   return result[i]
  return np.array([visit(i) for i in range(len(local))])
 def sample(self,name,fps=30):
  a=next(a for a in self.doc['animations'] if a['name']==name);duration=max(self.accessor(s['input'])[-1,0] for s in a['samplers']);times=np.linspace(0,duration,max(2,math.ceil(duration*fps)+1));frames=np.tile(self.rest,(len(times),1,1,1))
  for c in a['channels']:
   target=c['target'];s=a['samplers'][c['sampler']];t=self.accessor(s['input'])[:,0];v=self.accessor(s['output']);p=target['path'];node=target['node'];interpolation=s.get('interpolation','LINEAR');assert interpolation in ('LINEAR','STEP'),interpolation
   if interpolation=='STEP':values=v[np.maximum(0,np.searchsorted(t,times,side='right')-1)]
   elif p=='rotation':values=Slerp(t,Rotation.from_quat(v))(np.clip(times,t[0],t[-1])).as_quat() if len(t)>1 else np.tile(v,(len(times),1))
   else:values=np.array([np.interp(times,t,v[:,k]) for k in range(v.shape[1])]).T
   if p=='rotation':frames[:,node,:3,:3]=Rotation.from_quat(values).as_matrix()
   elif p=='translation':frames[:,node,:3,3]=values
   elif p=='scale':assert np.allclose(values,1,atol=1e-4),'Animated scale unsupported'
  return np.array([self.globals(f) for f in frames]),float(duration)

def mapping(source,model):
 if 'mixamorig:Hips' in source.names:
  names=['Hips','Hips','LeftUpLeg','LeftLeg','LeftFoot','RightUpLeg','RightLeg','RightFoot','Spine','Spine','Spine1','Spine2','Neck','Head','LeftShoulder','LeftArm','LeftForeArm','LeftHand',None,None,None,'RightShoulder','RightArm','RightForeArm','RightHand',None,None,None]
  return [source.names['mixamorig:'+n] if n else None for n in names]
 q='DEF-hips' in source.names
 names=['DEF-hips','DEF-hips','DEF-thigh.L','DEF-shin.L','DEF-foot.L','DEF-thigh.R','DEF-shin.R','DEF-foot.R','DEF-spine.001','DEF-spine.001','DEF-spine.002','DEF-spine.003','DEF-neck','DEF-head','DEF-shoulder.L','DEF-upper_arm.L','DEF-forearm.L','DEF-hand.L',None,None,None,'DEF-shoulder.R','DEF-upper_arm.R','DEF-forearm.R','DEF-hand.R',None,None,None] if q else ['hips','hips','upperleg.l','lowerleg.l','foot.l','upperleg.r','lowerleg.r','foot.r','spine','spine','chest','chest','chest','head',None,'upperarm.l','lowerarm.l','hand.l',None,None,None,None,'upperarm.r','lowerarm.r','hand.r',None,None,None]
 assert len(names)==len(model.names)==28
 return [source.names[n] if n else None for n in names]

def retarget(model,spec):
 sequence,label,file,clip,reference=spec;s=Gltf(ASSETS/file);animated,duration=s.sample(clip);ref=s.bind if reference=='bind' else s.sample(reference)[0][0];indices=mapping(s,model);hip=indices[0];C=Rotation.from_euler('x',90,degrees=True).as_matrix()
 bind=np.array(model.bind);local=np.array([np.linalg.inv(bind[p])@bind[i] if p>=0 else bind[i] for i,p in enumerate(model.parents)])
 # The compiled mesh uses standing feet at z=0; corpse origin is hull centre z=36.
 local[0,:3,3]-=np.array([0,0,36]);leg=indices[2];foot=indices[4];scale=np.linalg.norm(bind[2,:3,3]-bind[4,:3,3])/np.linalg.norm(ref[leg,:3,3]-ref[foot,:3,3]);out=[]
 if not hasattr(model,'death_mesh'):
  import build_personas as personas
  import death_wounds as wounds
  zones,_=personas.tailored_mesh(json.loads((personas.ASSETS/'personas.json').read_text()));groups,_,_=wounds.segment(zones,model);wounds.align_collar(groups);model.death_mesh=[t for g in groups for t in g]
 mesh=model.death_mesh;vertices=np.array([np.linalg.inv(bind[v['b']])@np.r_[v['p'],1] for _,tri in mesh for v in tri]);bones=np.array([v['b'] for _,tri in mesh for v in tri]);reference_hip=animated[0,hip,:3,3]
 for sample,pose in enumerate(animated):
  frame=local.copy();global_rot=[]
  for i,node in enumerate(indices):
   parent=model.parents[i]
   if node is None:r=global_rot[parent]@local[i,:3,:3] if parent>=0 else local[i,:3,:3]
   else:r=C@pose[node,:3,:3]@ref[node,:3,:3].T@C.T@bind[i,:3,:3]
   frame[i,:3,:3]=global_rot[parent].T@r if parent>=0 else r;global_rot.append(r)
  frame[0,:3,3]+=C@(pose[hip,:3,3]-reference_hip)*scale
  g=globals_of(frame,model.parents);world=np.einsum('vij,vj->vi',g[bones],vertices)
  # These are grounded collapses. Fit the actual retained GIGN body to the floor,
  # rather than transferring the short KayKit legs' vertical root trajectory.
  minimum=world[:,2].min();core=world[np.isin(bones,[1,8,9,10,11,12,13]),2].min()
  t=np.clip((sample/(len(animated)-1)-.65)/.35,0,1);settle=t*t*(3-2*t)
  frame[0,2,3]+=-35.9-(minimum*(1-settle)+core*settle)
  # Different leg/torso proportions must not suspend a settled back above the
  # floor. Keep each limb rigid, rotating at its hip/shoulder only as needed to
  # clear the ground after the late torso settling (no stretching or new bones).
  if settle>0:
   for upper in (2,5,14,21):
    g=globals_of(frame,model.parents);ids=np.isin(bones,list(range(upper,upper+7)) if upper>=14 else [upper,upper+1,upper+2]);limb=np.einsum('vij,vj->vi',g[bones[ids]],vertices[ids])[:,:3];pivot=g[upper,:3,3]
    if limb[:,2].min()<-35.9:
     candidates=[(axis,angle) for angle in range(0,121) for axis in ('x','y') for angle in ([angle,-angle] if angle else [0])]
     for axis,angle in candidates:
      rotation=Rotation.from_euler(axis,angle,degrees=True).as_matrix()
      if ((limb-pivot)@rotation.T+pivot)[:,2].min()>=-35.9:
       lo,hi=0.,float(angle)
       for _ in range(14):
        mid=(lo+hi)*.5;r=Rotation.from_euler(axis,mid,degrees=True).as_matrix()
        if ((limb-pivot)@r.T+pivot)[:,2].min()>=-35.9:hi=mid
        else:lo=mid
       rotation=Rotation.from_euler(axis,hi,degrees=True).as_matrix();frame[upper,:3,:3]=g[model.parents[upper],:3,:3].T@rotation@g[upper,:3,:3];break
     else:raise ValueError('Cannot fit settled limb to the ground: '+sequence+' frame '+str(sample)+' bone '+str(upper))
  out.append(frame)
 return np.array(out),dict(id=sequence,label=label,source_file=file,source_clip=clip,reference=reference,frames=len(out),fps=(len(out)-1)/duration,seconds=duration,leg_scale=float(scale),sha256=hashlib.sha256((ASSETS/file).read_bytes()).hexdigest())

def export(model,header,folder):
 records=[]
 for spec in CLIPS:
  frames,record=retarget(model,spec);rows=header[:header.index('skeleton')]+['skeleton'];undo=np.eye(4);undo[:3,:3]=Rotation.from_euler('z',-90,degrees=True).as_matrix()
  for t,pose in enumerate(frames):
   pose=pose.copy();pose[0]=undo@pose[0];rows.append('time '+str(t))
   with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for i,m in enumerate(pose):rows.append(str(i)+' '+' '.join(f'{v:.8f}' for v in [*m[:3,3],*Rotation.from_matrix(m[:3,:3]).as_euler('xyz')]))
  rows.append('end');(folder/(spec[0]+'.smd')).write_text('\n'.join(rows)+'\n');records.append(record)
 return records


def effect_tracks(model,path):
 """Bake effect centres from the compiled poses, including their root motion."""
 from animation_assets import sequence_frames
 rows=['// Generated from compiled corpse poses by build_deaths.py.', '#ifndef VF_DEATH_TRACKS_H', '#define VF_DEATH_TRACKS_H', 'namespace vfmotion {', 'static const int Sequences[]={18,19,20,21,22,23,24,'+','.join(str(model.sequences.index(n)) for n in ['vf_electro']+[s[0] for s in CLIPS])+'};', 'static const float Centres[][33][3]={']
 for name in model.sequences[18:25]+['vf_electro']+[s[0] for s in CLIPS]:
  poses=sequence_frames(model,name);centres=np.array([(g[11,:3,3]+g[13,:3,3])*.5 for g in (globals_of(p,model.parents) for p in poses)]);rows.append('{ // '+name)
  for t in np.linspace(0,len(poses)-1,33):
   i=min(int(t),len(poses)-2);v=centres[i]*(1-(t-i))+centres[i+1]*(t-i);rows.append('{'+','.join(f'{x:.6f}f' for x in v)+'},')
  rows.append('},')
 rows+=['};', 'inline bool Centre(int sequence,float frame,float* out){', 'int track=-1;for(int i=0;i<sizeof(Sequences)/sizeof(Sequences[0]);++i)if(Sequences[i]==sequence)track=i;if(track<0)return false;float t=frame*32.f/255.f;if(t<0)t=0;if(t>32)t=32;int i=(int)t;if(i>31)i=31;float mix=t-i;for(int k=0;k<3;++k)out[k]=Centres[track][i][k]*(1-mix)+Centres[track][i+1][k]*mix;return true;', '}', '}', '#endif'];path.write_text('\n'.join(rows)+'\n')
