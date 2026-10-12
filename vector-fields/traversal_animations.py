"""Traversal poses fitted to existing skeletons with verified source body motion.
Four corner blends in each 45-degree aim sector support continuous 360 aiming.
The left wrist is fitted in wall coordinates, independently of the gun.
"""
import math
import numpy as np
from scipy.spatial.transform import Rotation
from animation_assets import globals_of,sequence_frames

NAMES=['vf_vault','vf_hang_catch','vf_hang_idle','vf_hang_arm']+[f'vf_hang_aim_{i}'for i in range(8)]+['vf_climb','vf_slide_start','vf_slide_loop','vf_slide_end','vf_drop','vf_stepup','vf_wall_jump','vf_wall_jump_turn']
TIMES={'vf_vault':.82,'vf_stepup':.92,'vf_hang_catch':.28,'vf_hang_idle':1.2,'vf_hang_arm':.28,'vf_climb':.85,'vf_slide_start':.25,'vf_slide_loop':1.2,'vf_slide_end':.3,'vf_drop':.30,'vf_wall_jump':.65,'vf_wall_jump_turn':.65}
LOOPS={'vf_hang_idle','vf_slide_loop'}|{f'vf_hang_aim_{i}'for i in range(8)}

def easing(t):return t*t*(3-2*t)
def rotate(local,parents,bone,angles):
 g=globals_of(local,parents);m=Rotation.from_euler('xyz',angles,degrees=True).as_matrix()
 local[bone][:3,:3]=g[parents[bone]][:3,:3].T@m@g[bone][:3,:3] if parents[bone]>=0 else m@local[bone][:3,:3]

def ik(local,parents,ids,goal,pole):
 from build_reference_platforms import rotation_between
 upper,fore,hand=ids;g=globals_of(local,parents)
 s=g[upper][:3,3];e=g[fore][:3,3];w=g[hand][:3,3]
 a=np.linalg.norm(e-s);b=np.linalg.norm(w-e);delta=goal[:3,3]-s;d=np.linalg.norm(delta)
 if not abs(a-b)+1e-5<d<a+b-1e-5:raise ValueError(f'Unreachable traversal joint {ids}: {d:.2f}, reach {a+b:.2f}, target {goal[:3,3]}')
 v=delta/d;p=np.array(pole)-s;p-=v*(p@v)
 if np.linalg.norm(p)<1e-6:p=np.cross(v,[0,1,0])
 p/=np.linalg.norm(p);along=(a*a-b*b+d*d)/(2*d)
 new_e=s+along*v+math.sqrt(max(0,a*a-along*along))*p
 target=rotation_between(e-s,new_e-s)@g[upper][:3,:3]
 local[upper][:3,:3]=g[parents[upper]][:3,:3].T@target
 g=globals_of(local,parents)
 target=rotation_between(g[hand][:3,3]-g[fore][:3,3],goal[:3,3]-g[fore][:3,3])@g[fore][:3,:3]
 local[fore][:3,:3]=g[upper][:3,:3].T@target
 g=globals_of(local,parents);local[hand][:3,:3]=g[fore][:3,:3].T@goal[:3,:3]
 return float(np.max(np.abs(globals_of(local,parents)[hand]-goal)))

# Palm frames follow the anatomy of the two rigs: view hands have fingers on
# +Y and an inward -Z normal; the fitted body has fingers on +X, dorsal -Y.
FP_PALM=np.array([.3,3.,-1.])
FP_WALL=Rotation.from_euler("z",90,degrees=True).as_matrix()
TP_PALM=np.array([1.8,-.2,-.4])
FP_GRASP=np.array([[0,0,1],[1,0,0],[0,1,0]],dtype=float)
TP_GRASP=np.array([[0,1,0],[0,0,1],[1,0,0]],dtype=float)

def ledge_hand(contact,view=False,rotation=None):
 m=np.eye(4);m[:3,:3]=FP_GRASP if view else TP_GRASP
 if rotation is not None:m[:3,:3]=rotation@m[:3,:3]
 point=np.array(contact)
 if view:m[:3,:3]=FP_WALL@m[:3,:3];point=FP_WALL@point
 m[:3,3]=point-m[:3,:3]@(FP_PALM if view else TP_PALM)
 return m

def align_child(local,parents,bone,child,direction):
 from build_reference_platforms import rotation_between
 g=globals_of(local,parents)
 desired=rotation_between(g[child][:3,3]-g[bone][:3,3],np.array(direction))@g[bone][:3,:3]
 local[bone][:3,:3]=g[parents[bone]][:3,:3].T@desired

def fingers(local,parents,side='left',view=False,rotation=None):
 # Knuckles rise along the front face. The last two phalanges extend onto
 # the top, rather than retaining the closed cylindrical weapon grasp.
 r=np.eye(3) if rotation is None else rotation
 if view:r=FP_WALL@r
 if view:
  if side=='left' or len(parents)>=62:
   offset=0 if side=='left' else 30
   for a,b,c,d in [tuple(i+offset for i in ids)for ids in [(16,17,18,19),(20,21,22,23),(24,25,26,27),(28,29,30,31)]]:
    align_child(local,parents,a,b,r@np.array([0,0,1]))
    align_child(local,parents,b,c,r@np.array([1,0,.12]))
    align_child(local,parents,c,d,r@np.array([1,0,-.08]))
  a,b,c=(13,14,15) if side=='left' else (43,44,45) if len(parents)>=62 else (7,8,9)
  # The thumb must spread toward the outside of each palm. A straight-up
  # thumb sits on the middle finger's axis and folds into the fingertip mesh.
  lateral=1 if side=='left' else -1
  align_child(local,parents,a,b,r@np.array([.2,.65*lateral,.7]))
  align_child(local,parents,b,c,r@np.array([.3,.7*lateral,.6]))
 else:
  a,b,c=(18,19,20) if side=='left' else (25,26,27)
  align_child(local,parents,b,c,[1,0,.12])
  g=globals_of(local,parents)
  # Thumb leaf uses the same anatomical axes as the extended finger.
  desired=g[b][:3,:3].copy()
  local[a][:3,:3]=g[parents[a]][:3,:3].T@desired

def tp_pose(a,platform,name,t,yaw=0,pitch=0):
 from third_person import transform,solve
 from build_reference_platforms import blend,mount_matrix
 base=a.neutral.copy();hang=name.startswith('vf_hang');armed='aim' in name or name=='vf_hang_arm'
 if name in ('vf_vault','vf_stepup'):
  from traversal_vault import third_person
  return third_person(a,platform,name,t)
 from external_traversal_animations import body,RECIPE
 import json
 contacts=json.loads(RECIPE.read_text())['contacts']['third_person']
 if hang or name in ('vf_climb','vf_drop'):
  donor=body(name,t,a.neutral)
  weight=easing(t) if name=='vf_hang_catch' else 1
  base=np.array([blend(x,y,weight)for x,y in zip(base,donor)])
 if hang:
  weight=easing(t) if name=='vf_hang_catch' else 1
  alpha=easing(t) if name=='vf_hang_arm' else 1 if armed else 0
  if armed:
   planted=body('vf_hang_idle',0,a.neutral)
   base[:8]=planted[:8]
  shift=12-22*alpha
  base[0][2,3]+=shift*weight
  base[0][0,3]+=4*weight
  # Bent knees hang below the player rather than preserving the running gait.
  breath=math.sin(t*math.pi*2)*1.2 if name=='vf_hang_idle' else 0
  rotate(base,a.rig.parents,8,[0,breath,0])
  if armed:
   from traversal_aim import body_turn,head_turn
   hips,spine,lean=body_turn(yaw,pitch)
   turn=Rotation.from_euler('z',yaw,degrees=True).as_matrix()
   pitch_turn=turn@Rotation.from_euler('y',lean*alpha/4,degrees=True).as_matrix()@turn.T
   for bone in (8,9,10,11):
    rotate(base,a.rig.parents,bone,[0,0,spine*alpha/4])
    g=globals_of(base,a.rig.parents)
    base[bone][:3,:3]=g[a.rig.parents[bone]][:3,:3].T@pitch_turn@g[bone][:3,:3]
   g=globals_of(base,a.rig.parents)
   # Follow the gun within the neck's reach. A rear shot must not demand a
   # backwards head on a front-facing planted waist.
   head_yaw,head_pitch=head_turn(yaw,pitch)
   target=Rotation.from_euler('z',head_yaw*alpha,degrees=True).as_matrix()@Rotation.from_euler('y',head_pitch*alpha,degrees=True).as_matrix()@globals_of(a.neutral,a.rig.parents)[13][:3,:3]
   base[13][:3,:3]=g[a.rig.parents[13]][:3,:3].T@target
 elif 'slide' in name:
  crouch=sequence_frames(a.rig,'crouch_aim_mp5')[0]
  weight=easing(t) if name=='vf_slide_start' else 1-easing(t) if name=='vf_slide_end' else 1
  base=np.array([blend(x,y,weight)for x,y in zip(base,crouch)])
  # Seated skid: one heel leads, torso leans back. Fits the crouching hull.
  rotate(base,a.rig.parents,8,[0,-13*weight,0])
  if weight>0:
   g=globals_of(base,a.rig.parents)
   for ids,position,pole in [((2,3,4),[27,6,-14],[10,8,12]),((5,6,7),[3,6,-14],[18,-9,-11])]:
    goal=g[ids[2]].copy();goal[:3,3]=(1-weight)*goal[:3,3]+weight*np.array(position)
    from traversal_aim import slide_foot_rotation,slide_tucked_foot_rotation
    desired=goal.copy();desired[:3,:3]=slide_foot_rotation() if ids[0]==2 else slide_tucked_foot_rotation()
    goal[:3,:3]=blend(goal,desired,weight)[:3,:3]
    ik(base,a.rig.parents,ids,goal,pole)
 elif name=='vf_climb':
  base[0][2,3]+=12*(1-easing(t));base[0][0,3]+=4*(1-easing(t))
 elif name=='vf_drop':
  base[0][2,3]+=12*(1-easing(t));base[0][0,3]+=4*(1-easing(t))
 elif name=='vf_vault':
  weight=math.sin(math.pi*t)
  rotate(base,a.rig.parents,2,[0,-65*weight,0]);rotate(base,a.rig.parents,3,[0,95*weight,0])
  rotate(base,a.rig.parents,5,[0,-45*weight,0]);rotate(base,a.rig.parents,6,[0,72*weight,0])
  rotate(base,a.rig.parents,8,[0,16*weight,0])
 # Fit the gun and firing wrist to a direction independent of body yaw.
 follow=globals_of(base,a.rig.parents)[11]@np.linalg.inv(a.chest);gun=follow@a.gun
 if armed:
  alpha=easing(t) if name=='vf_hang_arm' else 1
  from traversal_aim import weapon_pitch
  gun[:3,:3]=Rotation.from_euler('z',yaw,degrees=True).as_matrix()@Rotation.from_euler('y',weapon_pitch(yaw,pitch),degrees=True).as_matrix()@a.gun[:3,:3]
  right=a.goal(gun,'right')
  # Behind the body, raise the grip and send the barrel over the right shoulder.
  behind=max(0,-math.cos(math.radians(yaw)))
  pos=np.array([7*math.cos(math.radians(yaw)),-9+4*math.sin(math.radians(yaw)),18+10*behind])
  gun[:3,3]+=pos-right[:3,3]
  if alpha<1:gun=blend(follow@a.gun,gun,alpha)
 left=a.goal(gun,'left');right=a.goal(gun,'right')
 if hang:
  g=globals_of(base,a.rig.parents)
  for side,goal,hand,y in [('left',left,17,8),('right',right,24,-8)]:
   if side=='right' and armed:continue
   depth=40-22*easing(t) if name=='vf_hang_arm' else 18 if armed else 40
   contact=np.array(contacts[side]);contact[2]-=40-depth
   goal[:]=ledge_hand(contact)
   if name=='vf_hang_catch':goal[:3,3]=g[hand][:3,3]*(1-easing(t))+goal[:3,3]*easing(t)
  if name=='vf_hang_arm':right[:]=blend(ledge_hand([18,-8,40-22*easing(t)-1.4]),right,easing(t))
 if name in ('vf_vault','vf_climb','vf_drop'):
  # Catch -> planted palms -> press -> release. Climb starts in the exact
  # two-hand suspension pose; release is distinct from the landing animation.
  for side,goal,hand,y in [('left',left,17,8),('right',right,24,-8)]:
   if name=='vf_climb':
    contact=ledge_hand([18,y,38.6-60*min(1,t/.4)])
    weight=1-easing(np.clip((t-.06)/.24,0,1))
   elif name=='vf_drop':
    contact=ledge_hand(contacts[side]);contact[:3,3]+=[-5*t,0,-15*t]
    weight=1-easing(t)
   else:
    contact=ledge_hand([16,y,22-12*t])
    weight=min(1,t/.20)*min(1,(1-t)/.30);weight=easing(weight)
   goal[:]=blend(goal,contact,weight)
 poles={'left':contacts['elbow_left'],'right':contacts['elbow_right']}
 if hang and armed:
  from traversal_aim import firing_arm
  g=globals_of(base,a.rig.parents)
  reach=np.linalg.norm(g[23][:3,3]-g[22][:3,3])+np.linalg.norm(g[24][:3,3]-g[23][:3,3])
  wrist,pole,crossing=firing_arm(yaw,pitch,reach)
  desired=right.copy();desired[:3,3]=g[22][:3,3]+wrist
  if name=='vf_hang_arm':desired=blend(right,desired,easing(t))
  gun[:3,3]+=desired[:3,3]-right[:3,3];right=desired
  alpha=easing(t) if name=='vf_hang_arm' else 1
  clearance=min(1.,2*crossing)*alpha
  poles['left']=(1-clearance)*g[16][:3,3]+clearance*(g[15][:3,3]+[-4,4,-16])
  poles['right']=g[22][:3,3]+pole
 for side,goal,pole in [('left',left,poles['left']),('right',right,poles['right'])]:
  a.max_error=max(a.max_error,solve(base,a.rig.parents,side,goal,pole))
 if hang or name in ('vf_vault','vf_climb','vf_drop'):
  fingers(base,a.rig.parents,'left')
  if not armed:fingers(base,a.rig.parents,'right')
 g=globals_of(base,a.rig.parents);mag=a.mag.copy()
 if platform!='bottom':
  mount=mount_matrix(platform);mount[:3,3]*=a.scale;mag=mount@mag
 result=np.concatenate([base,[np.linalg.inv(g[24])@gun,mag,np.eye(4)]])
 # Endpoints use the actual equipped R1 stance, including its elbow poles
 # and finger curl. Hanging fingers must not survive into normal aiming.
 normal=a.frame(a.neutral,platform)
 if name=='vf_hang_catch':
  weight=easing(min(1,t/.25));result=np.array([blend(x,y,weight)for x,y in zip(normal,result)])
 elif name in ('vf_climb','vf_drop','vf_slide_end','vf_vault'):
  weight=easing(np.clip((t-.65)/.35,0,1));result=np.array([blend(x,y,weight)for x,y in zip(result,normal)])
  if name=='vf_vault':
   weight=easing(min(1,t/.15));result=np.array([blend(x,y,weight)for x,y in zip(normal,result)])
 return result

def append_tp(a,platform,out):
 from third_person import smd
 authored={};qc=''
 for name in NAMES:
  duration=TIMES.get(name,1.2);frames=3 if 'aim_' in name else max(3,round(duration*30)+1);refs=[]
  corners=[(-22.5,-70),(22.5,-70),(-22.5,70),(22.5,70)] if 'aim_' in name else [(0,0)]
  for bi,(offset,pitch) in enumerate(corners):
   yaw=(int(name[-1])*45+offset+180)%360-180 if 'aim_' in name else 0
   motion=np.array([tp_pose(a,platform,name,i/(frames-1),yaw,pitch)for i in range(frames)])
   from traversal_editor import override
   motion=override(a.model,motion,'third-person',name,bi)
   if name in ('vf_wall_jump','vf_wall_jump_turn'):
    # Bake the reviewed release/regrip into ordinary generation as well as
    # the installed carrier. A cold launcher build must retain these poses.
    from build_reference_platforms import blend
    held=authored['vf_hang_idle',0][0]
    # Match Studio's equipped aim blend rather than solving IK from an
    # averaged donor pose; averaging and IK do not commute.
    from animation_assets import sequence_info
    count=sequence_info(a.rig,'ref_aim_mp5')['blends'];choices=[4]if count==9 else list(range(min(2,count)))
    aim=[a.motion('ref_aim_mp5',platform,b)[0]for b in choices]
    neutral=aim[0]if len(aim)==1 else np.array([blend(x,y,.5)for x,y in zip(*aim)])
    auxiliary=motion[:,29:].copy()
    for i in range(3):
     weight=easing(i/3);motion[i]=np.array([blend(x,y,weight)for x,y in zip(held,motion[i])])
    for i in range(16,21):
     weight=easing((i-16)/4);motion[i]=np.array([blend(x,y,weight)for x,y in zip(motion[i],neutral)])
    motion[:,29:]=auxiliary
   key=f'{platform}_{name}_{bi}';smd(a.model,motion,out/(key+'.smd'));refs.append(f' "{key}"');authored[name,bi]=motion
  options='\n blend YR -22.5 22.5\n blend XR -70 70' if len(corners)>1 else ''
  qc+=f'\n$sequence "{name}" {{\n'+ '\n'.join(refs)+f'\n fps {(frames-1)/duration:.6f}'+(' loop'if name in LOOPS else '')+options+'\n}\n'
 return qc,authored
