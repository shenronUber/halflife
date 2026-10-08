"""R-01 feed platforms: shared magazine meshes, authored tracks and arm IK.
All transforms are in the Bone76 chassis frame; units are GoldSrc units.
"""
import json,re,math
import numpy as np
from scipy.spatial.transform import Rotation, Slerp
from studio_assets import transform, Studio
import build_modular as base

PLATFORMS={
 'side':dict(name='R-01 / Traverse',label='Lateral',angle=90,entry=[-1.75,15.25,.1]),
 'top':dict(name='R-01 / Zenith',label='Superieur',angle=180,entry=[0,15.25,2.25]),
}
SOURCE_ENTRY=np.array([-.15,15.25,-.8])

def mount_matrix(key):
 spec=PLATFORMS[key];m=np.eye(4);m[:3,:3]=Rotation.from_euler('y',spec['angle'],degrees=True).as_matrix()
 m[:3,3]=np.array(spec['entry'])-m[:3,:3]@SOURCE_ENTRY
 return m

def read_frames(path):
 text=path.read_text(encoding='ascii');start=text.index('skeleton\n')+9;end=text.index('\nend',start)
 frames=[]
 for block in re.split(r'time \d+\n',text[start:end])[1:]:
  frame={}
  for line in block.strip().splitlines():
   row=line.split();frame[int(row[0])]=transform(list(map(float,row[1:7])))
  frames.append(frame)
 return text,frames

def globals_of(local,parents):
 result={}
 for b,m in local.items():result[b]=result[parents[b]]@m if parents[b]>=0 else m.copy()
 return result

def blend(a,b,t):
 t=np.clip(t,0,1);t=t*t*(3-2*t)
 m=np.eye(4);m[:3,:3]=Slerp([0,1],Rotation.from_matrix([a[:3,:3],b[:3,:3]]))([t]).as_matrix()[0]
 m[:3,3]=a[:3,3]*(1-t)+b[:3,3]*t
 return m

def rotation_between(a,b):
 a=a/np.linalg.norm(a);b=b/np.linalg.norm(b);cross=np.cross(a,b);dot=np.clip(a@b,-1,1)
 if np.linalg.norm(cross)<1e-8:
  if dot>0:return np.eye(3)
  axis=np.cross(a,[1,0,0]if abs(a[0])<.9 else[0,1,0]);axis/=np.linalg.norm(axis)
  return Rotation.from_rotvec(axis*np.pi).as_matrix()
 return Rotation.from_rotvec(cross/np.linalg.norm(cross)*math.acos(dot)).as_matrix()

def magazine_offset(key,frame):
 # Clip out at 18, clip in at 91; pocket exchange remains below/left of view.
 keys=([(0,[0,0,0]),(18,[0,0,0]),(35,[-5,0,0]),(54,[-15,-5,-22]),(64,[-15,-5,-22]),(81,[-5,0,0]),(91,[0,0,0]),(139,[0,0,0])]
       if key=='side' else
       [(0,[0,0,0]),(18,[0,0,0]),(34,[0,0,5]),(44,[-15,0,6]),(56,[-15,-5,-22]),(64,[-15,-5,-22]),(74,[-15,0,6]),(83,[0,0,5]),(93,[0,0,0]),(139,[0,0,0])])
 for (t0,a),(t1,b) in zip(keys,keys[1:]):
  if frame<=t1:
   f=np.clip((frame-t0)/(t1-t0),0,1);f=f*f*(3-2*f)
   return np.array(a)*(1-f)+np.array(b)*f
 return np.zeros(3)

def solve_arm(local,parents,goal):
 """Two-link arm with preserved lengths and a stable elbow pole.
 Bone04 anchors the arm, Bone40 is elbow, Bone42 wrist; Bone41 is a short
 intermediate joint. Only left-arm locals change. Finger pose is retained.
 """
 g=globals_of(local,parents);shoulder=g[3][:3,3];elbow=g[10][:3,3];wrist=g[12][:3,3]
 a=np.linalg.norm(elbow-shoulder);b=np.linalg.norm(wrist-elbow)
 delta=goal[:3,3]-shoulder;dist=np.linalg.norm(delta);direction=delta/dist
 if dist>a+b-1e-4 or dist<abs(a-b)+1e-4:raise ValueError(f'Unreachable R01 wrist: {dist:.3f} vs {a:.3f}+{b:.3f}')
 pole=elbow-shoulder;pole-=direction*np.dot(pole,direction)
 if np.linalg.norm(pole)<1e-6:pole=np.cross(direction,[0,0,1])
 pole/=np.linalg.norm(pole)
 along=(a*a-b*b+dist*dist)/(2*dist);height=math.sqrt(max(0,a*a-along*along))
 new_elbow=shoulder+along*direction+height*pole
 target=g[10].copy();target[:3,3]=new_elbow
 # Choose forearm roll from the desired palm, rather than retaining the old
 # MP40 roll. The remaining wrist bend is the smallest aiming adjustment.
 relative=np.linalg.inv(g[10])@g[12]
 desired=goal[:3,:3]@relative[:3,:3].T
 target[:3,:3]=rotation_between(desired@relative[:3,3],goal[:3,3]-new_elbow)@desired
 local[10]=np.linalg.inv(g[3])@target
 g=globals_of(local,parents)
 # Wrist rotation is independent of forearm direction; no bone stretching.
 local[12][:3,:3]=g[11][:3,:3].T@goal[:3,:3]
 g=globals_of(local,parents)
 return float(np.linalg.norm(g[12][:3,3]-goal[:3,3])),a,b

def write_frames(path,text,frames):
 start=text.index('skeleton\n')+9;end=text.index('\nend',start)
 out=[]
 for t,frame in enumerate(frames):
  out.append('time '+str(t))
  for i,m in frame.items():
   xyz=m[:3,3];ang=Rotation.from_matrix(m[:3,:3]).as_euler('xyz')
   out.append(str(i)+' '+' '.join(f'{v:.8f}'for v in [*xyz,*ang]))
 path.write_text(text[:start]+'\n'.join(out)+text[end:],encoding='ascii')

def build_rigs(out):
 names,parents,bind=base.skeleton(out/'mp40_hands.smd')
 _,idle=read_frames(out/'idle.smd');idle_g=globals_of(idle[0],parents)
 gun=40;mag=43;hand=12
 mag_in_gun=np.linalg.inv(idle_g[gun])@idle_g[mag]
 source_hand=np.linalg.inv(idle_g[gun])@idle_g[hand]
 # Close the index to the same grasp as the middle finger, retaining each
 # finger's own lengths and base positions. The legacy index is half-open.
 closed={i:m.copy()for i,m in idle[0].items()}
 for index,middle in [(17,21),(18,22),(19,23)]:closed[index][:3,:3]=closed[middle][:3,:3]
 curl=Rotation.from_euler('x',-20,degrees=True).as_matrix()
 for knuckle in [16,20,24,28]:closed[knuckle][:3,:3]=curl@closed[knuckle][:3,:3]
 support=source_hand.copy();support[:3,3]+=[0,8.2,1.5]
 left_desc=[]
 for i in names:
  p=parents[i]
  while p>=0 and p!=10:p=parents[p]
  if p==10 or i==10:left_desc.append(i)
 qc=(out/'r01_rig.qc').read_text(encoding='ascii');reports={}
 sequences=['idle','idle_1','shoot1','reload','draw','shoot1_1','shoot2','shoot2_1','empty_idle']
 for key,spec in PLATFORMS.items():
  errors=[];lengths=[];samples=[];mount=mount_matrix(key)
  # Palm coordinates: +Y wrist->knuckles, +X across fingers, -Z inward.
  # Traverse: dorsal face visible and fist centred on the horizontal body.
  # Zenith: inward palm faces the player (-weapon Y), thumb points upward.
  hand_pose=np.eye(4)
  hand_pose[:3,:3]=np.array([[1,0,0],[0,0,-1],[0,1,0]])if key=='side'else np.array([[0,1,0],[0,0,1],[1,0,0]])
  centre=(mount@np.array([-.15,15.25,-8.3,1]))[:3]
  hand_pose[:3,3]=centre-hand_pose[:3,:3]@np.array([.3,3.9,-2.1])
  grip=np.linalg.inv(mount@mag_in_gun)@hand_pose
  for seq in sequences:
   text,frames=read_frames(out/(seq+'.smd'))
   for t,local in enumerate(frames):
    g=globals_of(local,parents);relative=mount@mag_in_gun
    if seq=='reload':relative[:3,3]+=magazine_offset(key,t)
    local[mag]=relative # Bone71 is a direct child of Bone76.
    target=g[gun]@relative@grip
    resting=g[gun]@(mount@mag_in_gun@grip if key=='side'else support)
    if seq!='reload':target=resting
    elif t<18:
     target=blend(resting,target,t/18)
     if key=='top':target[:3,3]+=g[gun][:3,:3]@np.array([-2*math.sin(math.pi*t/18),0,0])
    elif t>99:
     u=min(1,(t-99)/30);target=blend(target,resting,u)
     if key=='top':target[:3,3]+=g[gun][:3,:3]@np.array([-2*math.sin(math.pi*u),0,0])
    # Retain a closed grip independently of the legacy MP40 finger motion.
    for i in left_desc:local[i]=closed[i].copy()
    error,a,b=solve_arm(local,parents,target)
    errors.append(error);lengths.append([a,b])
    if seq=='reload':
     final=globals_of(local,parents);inv=np.linalg.inv(final[gun])
     samples.append(dict(frame=t,magazine=(inv@final[mag]).tolist(),wrist=(inv@final[hand]).tolist(),grip_error=error))
   write_frames(out/(key+'_'+seq+'.smd'),text,frames)
  newqc=qc.replace('r01_rig.mdl','r01_rig_'+key+'.mdl')
  for seq in sequences:newqc=newqc.replace('"'+seq+'"\n','"'+key+'_'+seq+'"\n')
  newqc=newqc.replace('5004 17 ','5004 18 ').replace('5004 88 ',f'5004 {91 if key=="side" else 93} ')
  path=out/('r01_rig_'+key+'.qc');path.write_text(newqc,encoding='ascii');base.compile_model(path)
  rig=Studio(path.with_suffix('.mdl'));assert len(rig.sequences)==9 and 'Bone71'in rig.names
  reports[key]=dict(grip=grip.tolist(),support=('magazine'if key=='side'else'foregrip'),mount=mount.tolist(),entry=spec['entry'],max_wrist_error=max(errors),arm_lengths_range=np.ptp(lengths,axis=0).tolist(),reload=samples)
 (out/'platform-motion.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
 return reports
