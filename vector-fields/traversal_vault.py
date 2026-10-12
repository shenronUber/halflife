"""One-hand wall vault and distinct leading-foot step onto a broad platform.
The local Vault_Over_Box bank was inspected for reach/tuck/release timing;
its turning two-arm pose is deliberately refitted to the equipped R1 rig.
"""
import math
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from animation_assets import globals_of
from build_reference_platforms import blend,solve_arm,steady_forearm
from traversal_animations import easing,ik,rotate,ledge_hand,fingers,FP_WALL

def key(t,values):
 for (a,x),(b,y) in zip(values,values[1:]):
  if t<=b:return np.array(x)*(1-easing(np.clip((t-a)/(b-a),0,1)))+np.array(y)*easing(np.clip((t-a)/(b-a),0,1))
 return np.array(values[-1][1])

def support(t):return float(key(t,[(0,0),(.24,1),(.30,1),(.48,0),(1,0)]))

def mix(a,b,w):
 result=np.eye(4);result[:3,:3]=Slerp([0,1],Rotation.from_matrix([a[:3,:3],b[:3,:3]]))([w]).as_matrix()[0]
 result[:3,3]=a[:3,3]*(1-w)+b[:3,3]*w
 return result

def third_person(a,platform,name,t):
 wide=name=='vf_stepup';local=a.neutral.copy();normal=a.frame(a.neutral,platform)
 weight=float(key(t,[(0,0),(.4,1),(.68,1),(.96,0),(1,0)]))
 # During the plant the shoulder stays close to the top. The body rises as
 # the arm extends and releases, then the feet clear the obstacle separately.
 rootz=float(key(t,[(0,18),(.15,3),(.27,-10),(.42,0),(.72,0),(.96,18),(1,18)]))
 local[0][:3,3]+=[8*support(t),0,rootz]
 rotate(local,a.rig.parents,8,[0,24*support(t)+12*weight,0])
 g=globals_of(local,a.rig.parents)
 for ids,goalpoint,pole in [((2,3,4),[14,8,-10],[24,9,8]),((5,6,7),[-3,-8,-5],[20,-10,8])]:
  if wide and ids[0]==2:goalpoint=[20,7,-14]
  goal=g[ids[2]].copy();goal[:3,3]=(1-weight)*goal[:3,3]+weight*(np.array(goalpoint)+[0,0,rootz])
  ik(local,a.rig.parents,ids,goal,np.array(pole)+[0,0,rootz])
 # Right hand retains its weapon grip; only the left hand leaves the rifle.
 follow=globals_of(local,a.rig.parents)[11]@np.linalg.inv(a.chest);gun=follow@a.gun
 left=a.goal(gun,'left');right=a.goal(gun,'right')
 # Carry the muzzle above the wall while the support hand pushes. Pivot
 # around the firing grip so the rifle never pulls away from the right hand.
 turn=Rotation.from_euler('y',-55*support(t),degrees=True).as_matrix();pivot=right[:3,3].copy()
 gun[:3,3]=pivot+turn@(gun[:3,3]-pivot);gun[:3,:3]=turn@gun[:3,:3]
 right=a.goal(gun,'right')
 contact=key(t,[(0,[18,9,30]),(.15,[18,9,10]),(.27,[18,9,-5]),(.42,[8,9,-8]),(1,[8,9,-8])])
 plant=ledge_hand(contact);grip=a.goal(a.gun,'left')
 # Use one fixed quaternion arc: the moving chest could cross 180 degrees
 # and change Slerp's shortest path while the hand was still travelling.
 left=mix(left,plant,support(t))
 left[:3,:3]=mix(grip,plant,support(t))[:3,:3]
 from third_person import solve
 g=globals_of(local,a.rig.parents)
 solve(local,a.rig.parents,'left',left,g[15,:3,3]+[6,10,-10])
 solve(local,a.rig.parents,'right',right,g[22,:3,3]+[5,-10,-12])
 posed=local.copy();fingers(posed,a.rig.parents,'left')
 for i in(18,19,20):local[i]=blend(local[i],posed[i],support(t))
 g=globals_of(local,a.rig.parents)
 mag=a.mag.copy()
 if platform!='bottom':
  from build_reference_platforms import mount_matrix
  mount=mount_matrix(platform);mount[:3,3]*=a.scale;mag=mount@mag
 return np.concatenate([local,[np.linalg.inv(g[24])@gun,mag,np.eye(4)]])

def first_person(rig,name,t):
 from traversal_hands import idle
 base=idle(rig).copy();g=globals_of(base,rig.parents);gun=g[40].copy()
 w=support(t)
 # Readable left reach -> heel-of-palm push -> release. Keep the rifle in
 # the right hand beside the chest rather than floating between two palms.
 gun[:3,3]+=FP_WALL@np.array([-2*w,-2*w,-2*w])
 pivot=g[6,:3,3].copy()+FP_WALL@np.array([-2*w,-2*w,-2*w])
 turn=FP_WALL@Rotation.from_euler('y',-55*w,degrees=True).as_matrix()@FP_WALL.T
 gun[:3,3]=pivot+turn@(gun[:3,3]-pivot);gun[:3,:3]=turn@gun[:3,:3]
 right=gun@np.linalg.inv(g[40])@g[6]
 contact=key(t,[(0,[18,8,7]),(.12,[18,8,4]),(.27,[15,8,-12]),(.42,[7,8,-10]),(1,[7,8,-10])])
 left=mix(g[12],ledge_hand(contact,view=True),w)
 local={i:m.copy()for i,m in enumerate(base)}
 solve_arm(local,rig.parents,left,neutral_wrist=True,elbow_pole=FP_WALL@np.array([3,14,-12]))
 steady_forearm(local,rig.parents,base[10])
 solve_arm(local,rig.parents,right,neutral_wrist=True,right=True)
 result=np.array([local[i]for i in range(len(base))]);posed=result.copy();fingers(posed,rig.parents,'left',view=True)
 for i in range(13,32):result[i]=blend(result[i],posed[i],w)
 result[40]=np.linalg.inv(globals_of(result,rig.parents)[rig.parents[40]])@gun
 # The broad-platform step has a longer palm press and a separate leg pose;
 # the view reach remains fitted to the same anatomical wrist axes.
 return result
