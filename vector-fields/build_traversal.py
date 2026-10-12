"""Compile dedicated traversal view carriers without modifying historical rigs."""
import argparse,re,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of
from third_person import smd
from traversal_animations import NAMES,TIMES,LOOPS,easing,ledge_hand,fingers,FP_WALL
from build_reference_platforms import solve_arm,blend
from build_modular import compile_model
import build_cache
ROOT=Path(__file__).resolve().parent;SOURCE=ROOT/'generated/r01';OUT=ROOT/'generated/traversal'
FP_NAMES=NAMES[:16]+[f'vf_hang_both_{i}'for i in range(8)]+NAMES[16:]
VARIANTS=['r01_rig','r01_rig_side','r01_rig_top','r01_rig_fg','r01_rig_side_fg','r01_rig_top_fg']

def pose(rig,name,t,yaw=0,pitch=0):
 if name in ('vf_vault','vf_stepup'):
  from traversal_vault import first_person
  return first_person(rig,name,t)
 from traversal_hands import idle
 base=idle(rig).copy();g=globals_of(base,rig.parents)
 from external_traversal_animations import RECIPE
 contacts=json.loads(RECIPE.read_text())['contacts']['first_person']
 original_gun=g[40].copy();right_in_gun=np.linalg.inv(original_gun)@g[6]
 gun=original_gun.copy();hang=name.startswith('vf_hang');armed='aim_'in name or name=='vf_hang_arm'
 busy=hang and not armed or name in ('vf_climb','vf_vault','vf_drop')
 if busy:
  # Gun remains on its socket below view while both palms are on the obstacle.
  gun[:3,3]+=[0,0,-32]
 elif hang:
  gun[:3,3]+=[0,-1,-1];gun[:3,:3]=Rotation.from_euler('x',-4,degrees=True).as_matrix()@gun[:3,:3]
 elif 'slide'in name:
  weight=easing(t) if name=='vf_slide_start'else 1-easing(t)if name=='vf_slide_end'else 1
  gun[:3,3]+=[-2*weight,0,-2*weight]
 target_right=gun@right_in_gun
 if hang and armed:
  from traversal_aim import aim_deploy
  guard=(1-aim_deploy(yaw))*(easing(t) if name=='vf_hang_arm' else 1.)
  turn=Rotation.from_euler('y',-90*guard,degrees=True).as_matrix()
  pivot=target_right[:3,3].copy();gun[:3,3]=pivot+turn@(gun[:3,3]-pivot);gun[:3,:3]=turn@gun[:3,:3]
  target_right=gun@right_in_gun
 left=g[12].copy()
 if busy or hang:
  rotation=Rotation.from_euler('zy',[-yaw,-pitch],degrees=True).as_matrix()
  depth=8-18*t if name=='vf_hang_arm' else -10 if armed else 8
  contact=np.array(contacts['left']);contact[2]-=8-depth
  left=ledge_hand(rotation@contact,view=True,rotation=rotation)
  if busy:target_right=ledge_hand(rotation@np.array([18,-8,depth-1.8 if hang else -5.]),view=True,rotation=rotation)
  if name=='vf_hang_catch':
   left=blend(g[12],left,easing(t));target_right=blend(g[6],target_right,easing(t))
  if name=='vf_hang_arm':target_right=blend(ledge_hand([18,-8,depth-1.8],view=True),target_right,easing(t))
  if name in ('vf_vault','vf_climb','vf_drop'):
   for side,hand in [('left',12),('right',6)]:
    if name=='vf_climb':
     contact=np.array(contacts[side]);contact[2]-=22*min(1,t/.4)
     w=1-easing(np.clip((t-.48)/.35,0,1))
    elif name=='vf_drop':
     contact=np.array(contacts[side])+[-7*t,0,-12*t];w=1-easing(t)
    else:
     contact=np.array([18,8 if side=='left' else -8,-3-4*t])
     w=easing(min(1,t/.2)*min(1,(1-t)/.28))
    goal=blend(g[hand],ledge_hand(contact,view=True),w)
    if side=='left':left=goal
    else:target_right=goal
 # Compiler-space IK utilities accept dicts as well as arrays.
 local={i:matrix.copy()for i,matrix in enumerate(base)}
 solve_arm(local,rig.parents,left,neutral_wrist=True,elbow_pole=FP_WALL@np.array(contacts['elbow_left']) if hang or busy else None)
 solve_arm(local,rig.parents,target_right,neutral_wrist=True,right=True,elbow_pole=FP_WALL@np.array(contacts['elbow_right']) if busy else None)
 result=np.array([local[i]for i in range(len(base))])
 grip=easing(t) if name=='vf_hang_catch' else w if name in ('vf_vault','vf_climb','vf_drop') else 1
 if hang or busy:
  fingers(result,rig.parents,'left',view=True,rotation=rotation)
  if busy:fingers(result,rig.parents,'right',view=True,rotation=rotation)
  for b in list(range(13,32))+list(range(43,62)):
   result[b][:3,:3]=blend(base[b],result[b],grip)[:3,:3]
 result[40]=np.linalg.inv(globals_of(result,rig.parents)[rig.parents[40]])@gun
 # A ledge pole is appropriate only while reaching. At the equipped ends
 # use the original variant's whole arm pose, including its elbow roll.
 edge=easing(np.clip(t/.15,0,1)) if name in ('vf_hang_catch','vf_vault') else 1.
 if name in ('vf_climb','vf_drop','vf_vault','vf_slide_end'):
  edge*=1-easing(np.clip((t-.8)/.2,0,1))
 if edge<1:
  anatomical=[i for i,n in enumerate(rig.names) if n not in {'Bone75','Bone76','Bone71','R01_Bolt'}]
  for i in anatomical:
   result[i]=blend(base[i],result[i],edge)
   expected=np.linalg.norm(base[i,:3,3]);length=np.linalg.norm(result[i,:3,3])
   if length>1e-8:result[i,:3,3]*=expected/length
 return result

import math
def build(ensure=False):
 OUT.mkdir(parents=True,exist_ok=True)
 from build_traversal_body import build as build_body
 build_body(ensure)
 from external_traversal_animations import inputs as source_inputs
 from traversal_editor import inputs as edit_inputs
 inputs=source_inputs()+edit_inputs('first-person')+[Path(__file__),ROOT/'traversal_vault.py',ROOT/'traversal_animations.py',ROOT/'traversal_aim.py',ROOT/'third_person.py',ROOT/'animation_assets.py',ROOT/'build_reference_platforms.py',ROOT/'traversal_hands.py']+list(SOURCE.glob('*.mdl'))+list(SOURCE.glob('*.qc'))+build_cache.compiler_inputs()
 digest=build_cache.fingerprint(inputs);manifest=OUT/'manifest.json'
 if ensure and build_cache.current(build_cache.read(manifest).get('build_cache'),digest):print('Traversal view carriers are current.');return
 records=[]
 for variant in VARIANTS:
  original=Studio(SOURCE/(variant+'.mdl'))
  from traversal_hands import extend,extend_smd
  rig=extend(original);qc=(SOURCE/(variant+'.qc')).read_text()
  qc=qc.replace(f'"{variant}.mdl"',f'"{variant}_tr.mdl"').replace('$cdtexture "./"','$cdtexture "../r01"')
  for path in SOURCE.glob('*.smd'):qc=qc.replace('"'+path.stem+'"','"../r01/'+path.stem+'"')
  qc=re.sub(r'(\$sequence ")../r01/',r'\1',qc)
  for ref in set(re.findall(r'"../r01/([^"]+)"',qc)):
   key='extended_'+ref;extend_smd(SOURCE/(ref+'.smd'),OUT/(key+'.smd'),rig,reference=ref=='mp40_hands')
   qc=qc.replace('"../r01/'+ref+'"','"'+key+'"')
  for name in FP_NAMES:
   duration=TIMES.get(name,1.2);n=3 if 'aim_'in name or 'both_'in name else max(3,round(duration*30)+1);refs=[]
   corners=[(-22.5,-70),(22.5,-70),(-22.5,70),(22.5,70)]if'aim_'in name or 'both_'in name else [(0,0)]
   for bi,(offset,pitch)in enumerate(corners):
    yaw=(int(name[-1])*45+offset+180)%360-180 if'aim_'in name or 'both_'in name else 0
    frames=np.array([pose(rig,name,i/(n-1),yaw,pitch)for i in range(n)])
    from traversal_editor import override
    frames=override(rig,frames,'first-person',name,bi,yaw,pitch)
    key=f'{variant}_{name}_{bi}';smd(rig,frames,OUT/(key+'.smd'));refs.append(f' "{key}"')
   options='\n blend YR -22.5 22.5\n blend XR -70 70'if len(corners)>1 else ''
   qc+=f'\n$sequence "{name}" {{\n'+'\n'.join(refs)+f'\n fps {(n-1)/duration:.6f}'+(' loop'if name in LOOPS or 'both_'in name else '')+options+'\n}\n'
  path=OUT/(variant+'_tr.qc');path.write_text(qc,encoding='ascii');compiled=Studio(compile_model(path))
  assert set(compiled.names)==set(rig.names) and compiled.sequences[:9]==original.sequences
  assert all(compiled.names[compiled.parents[compiled.names.index(n)]]==rig.names[rig.parents[i]] for i,n in enumerate(rig.names) if rig.parents[i]>=0)
  assert compiled.sequences[9:]==FP_NAMES
  records.append(dict(model=compiled.path.name,sequences=len(compiled.sequences),bones=len(compiled.names)))
 outputs=[p for p in OUT.iterdir()if p.suffix in('.mdl','.qc','.smd')]
 build_cache.write(manifest,dict(models=records,gestures=FP_NAMES,build_cache=build_cache.record(digest,outputs)))
 print('PASS traversal view carriers',json.dumps(records))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ensure',action='store_true');build(p.parse_args().ensure)
