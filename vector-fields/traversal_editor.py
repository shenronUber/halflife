"""Editable SMD overrides and a fragMOTION workshop for the game rigs.
Generated workshop files are disposable; edits live outside generated/.
"""
import argparse,hashlib,json,re,shutil,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.spatial.transform import Rotation
from animation_assets import globals_of,sequence_frames,sequence_info
from build_reference_platforms import blend
from studio_assets import Studio
ROOT=Path(__file__).resolve().parent
EDITS=ROOT/'assets/animations/traversal-edits'
WORKSHOP=ROOT/'animation-workshop/traversal'

def inputs(view):return [Path(__file__)]+list((EDITS/view).glob('*.smd'))+list((EDITS/view).glob('*.accepted.json'))

def read(path,model):
 text=Path(path).read_text(encoding='utf-8-sig');lines=[l.split('//',1)[0].strip() for l in text.splitlines()];mode=None;nodes={};frames={};time=None
 for line in lines:
  if not line or line.startswith('version'):continue
  if line in ('nodes','skeleton','triangles'):mode=line;continue
  if line=='end':mode=None;continue
  if mode=='nodes':
   m=re.fullmatch(r'(\d+)\s+"([^"\n]+)"\s+(-?\d+)',line)
   if not m:raise ValueError('Invalid SMD node: '+line)
   i,name,parent=m.groups();nodes[int(i)]=(name,int(parent))
  elif mode=='skeleton':
   if line.startswith('time '):
    time=int(line[5:])
    if time in frames or time<0:raise ValueError('Duplicate or negative SMD frame')
    frames[time]={}
   else:
    row=line.split()
    if time is None or len(row)!=7:raise ValueError('Invalid SMD transform')
    i=int(row[0]);v=np.array(row[1:],float)
    if not np.isfinite(v).all() or np.max(np.abs(v[:3]))>512:raise ValueError('Invalid or excessive bone translation')
    matrix=np.eye(4);matrix[:3,3]=v[:3];matrix[:3,:3]=Rotation.from_euler('xyz',v[3:]).as_matrix();frames[time][i]=matrix
 expected=set(model.names)
 if len(nodes)!=len(expected) or {v[0]for v in nodes.values()}!=expected:raise ValueError('SMD skeleton must keep every original bone name, with no extra bones')
 ids={name:i for i,(name,_)in nodes.items()}
 for i,name in enumerate(model.names):
  parent=nodes[ids[name]][1];actual=nodes[parent][0] if parent>=0 else None;wanted=model.names[model.parents[i]] if model.parents[i]>=0 else None
  if actual!=wanted:raise ValueError('Changed parent for '+name)
 if len(frames)<2 or len(frames)>1001 or sorted(frames)!=list(range(max(frames)+1)):raise ValueError('SMD needs 2..1001 contiguous frames starting at zero')
 out=[];undo=np.eye(4);undo[:3,:3]=Rotation.from_euler('z',90,degrees=True).as_matrix()
 for t in sorted(frames):
  if set(frames[t])!=set(nodes):raise ValueError('Every frame must contain all bones')
  frame=np.array([frames[t][ids[n]]for n in model.names]);frame[0]=undo@frame[0];out.append(frame)
 return np.array(out)

def resample(frames,count):
 out=[]
 for t in np.linspace(0,len(frames)-1,count):
  i=min(int(t),len(frames)-2);out.append([blend(a,b,t-i)for a,b in zip(frames[i],frames[i+1])])
 return np.array(out)

def override(model,default,view,name,corner,yaw=0,pitch=0):
 path=EDITS/view/(name+'_'+str(corner)+'.smd')
 # Old vault exports describe the superseded two-hand gesture. Accept a new
 # manual vault/step only after the ordinary validated import has marked it.
 if name in ('vf_vault','vf_stepup') and not path.with_suffix('.accepted.json').exists():return default
 # The settled FP view uses the camera sectors. Transfer idle finger keys
 # and edited elbow directions to those sectors, so the primary workshop
 # gesture also changes the actual in-game suspension.
 idle_path=EDITS/view/'vf_hang_idle_0.smd'
 if not path.exists() and idle_path.exists() and (name.startswith('vf_hang_both_') or name.startswith('vf_hang_aim_')):
  idle=read(idle_path,model);edited=resample(idle,len(default));out=default.copy()
  if view=='first-person':
   from build_traversal import pose
   from build_reference_platforms import solve_arm
   neutral=pose(model,'vf_hang_idle',0);ng=globals_of(neutral,model.parents)
   from traversal_animations import FP_WALL
   rotation=FP_WALL@Rotation.from_euler('zy',[-yaw,-pitch],degrees=True).as_matrix()@FP_WALL.T
   for t,frame in enumerate(out):
    eg=globals_of(edited[t],model.parents);g=globals_of(frame,model.parents);local={i:m.copy()for i,m in enumerate(frame)}
    for fore,hand,right in [(10,12,False),(4,6,True)]:
     if right and 'aim_' in name:continue
     pole=g[fore,:3,3]+rotation@(eg[fore,:3,3]-ng[fore,:3,3])
     solve_arm(local,model.parents,g[hand],neutral_wrist=True,right=right,elbow_pole=pole)
    frame[:]=[local[i]for i in range(len(frame))]
   fingers=[i for i,n in enumerate(model.names)if n in ['Bone43','Bone44','Bone45','Bone47','Bone48','Bone49','Bone50','Bone51','Bone52','Bone53','Bone54','Bone55','Bone56','Bone57','Bone58','Bone59','Bone60','Bone61','Bone62'] or (n.startswith('VFRight_') and 'both_'in name)]
  else:fingers=[18,19,20]
  out[:,fingers,:3,:3]=edited[:,fingers,:3,:3];return out
 if not path.exists():return default
 edited=resample(read(path,model),len(default))
 # Keep each carrier's own equipped stance at the edges of traversal. The
 # same reviewed ledge pose is shared by bottom/side/top R1 carriers, but
 # their ordinary support-hand placements differ.
 if name in ('vf_hang_catch','vf_climb','vf_drop','vf_vault','vf_slide_end'):
  for t,frame in enumerate(edited):
   progress=t/(len(edited)-1)
   smooth=lambda x:(lambda u:u*u*(3-2*u))(np.clip(x,0,1))
   weight=smooth(progress/.15) if name=='vf_hang_catch' else 1-smooth((progress-.8)/.2)
   if name=='vf_vault':weight*=smooth(progress/.15)
   frame[:]=[blend(a,b,weight)for a,b in zip(default[t],frame)]
   for i in range(1,len(frame)):
    length=np.linalg.norm(frame[i,:3,3]);expected=np.linalg.norm(default[t,i,:3,3])
    if length>1e-8:frame[i,:3,3]*=expected/length
 # Attachment layouts remain specific to each weapon variant.
 sockets={'Bone76','Bone71','R01_Bolt'}if view=='first-person'else{'VF_Magazine','VF_Bolt'}
 for i,n in enumerate(model.names):
  if n in sockets:edited[:,i]=default[:,i]
 if view=='first-person' and (name=='vf_hang_arm' or name.startswith('vf_hang_aim_')):
  # A socket's LOCAL transform cannot be copied from a different arm pose:
  # the parent shoulder's roll changes when the wrist turns into the guard.
  # Preserve the variant's equipped grip relative to the reviewed hand.
  from traversal_hands import idle
  equipped=globals_of(idle(model),model.parents)
  hand=model.names.index('Bone07');gun=model.names.index('Bone76')
  hand_to_gun=np.linalg.inv(equipped[hand])@equipped[gun]
  for frame in edited:
   g=globals_of(frame,model.parents)
   frame[gun]=np.linalg.inv(g[model.parents[gun]])@g[hand]@hand_to_gun
 anatomical=[i for i,n in enumerate(model.names)if i and n not in {'VF_Weapon','VF_Magazine','VF_Bolt'}|sockets]
 length=np.linalg.norm(edited[:,anatomical,:3,3],axis=-1);expected=np.linalg.norm(default[:,anatomical,:3,3],axis=-1)
 if np.max(np.abs(length-expected))>.15:raise ValueError('Bone lengths changed in '+str(path)+'; animate rotations instead of stretching the rig')
 return edited

def posed_triangles(model,frames,triangles):
 # A combined SMD defines its bind pose with skeleton time 0. Its mesh must
 # therefore be posed to that same frame, rather than the MDL header bind.
 # Standalone reference and animation SMDs retain the original rig bind.
 first=globals_of(frames[0],model.parents)
 undo=np.eye(4);undo[:3,:3]=Rotation.from_euler('z',-90,degrees=True).as_matrix()
 matrices=[undo@first[i]@np.linalg.inv(model.bind[i])@np.linalg.inv(undo)for i in range(len(model.names))]
 result=[]
 for i,line in enumerate(triangles):
  if i%4==0:result.append(line);continue
  row=line.split();bone=int(row[0]);matrix=matrices[bone]
  position=(matrix@np.r_[np.array(row[1:4],float),1])[:3]
  normal=matrix[:3,:3]@np.array(row[4:7],float)
  result.append(str(bone)+' '+' '.join(f'{v:.8f}'for v in [*position,*normal,*map(float,row[7:9])]))
 return result

def export():
 from third_person import smd
 from build_traversal_body import triangle_lines
 from build_modular import compile_model
 from traversal_animations import NAMES,TIMES,LOOPS
 from build_traversal import FP_NAMES
 records=[]
 for view,file,names,parts in [('first-person',ROOT/'generated/traversal/r01_rig_tr.mdl',FP_NAMES,[ROOT/'generated/traversal/ledge_gloves.mdl',ROOT/'generated/traversal/ledge_sleeves.mdl']),('third-person',ROOT/'generated/third-person/r01_tp.mdl',NAMES,[ROOT/'generated/personas/persona_scout.mdl'])]:
  folder=WORKSHOP/view;folder.mkdir(parents=True,exist_ok=True);(EDITS/view).mkdir(parents=True,exist_ok=True);skin_columns=[];skin_counts=[]
  model=Studio(file);bind=np.array([np.linalg.inv(model.bind[p])@model.bind[i]if p>=0 else model.bind[i]for i,p in enumerate(model.parents)]);triangles=[]
  for k,path in enumerate(parts):
   part=Studio(path);materials=part.write_textures(folder,'part'+str(k));mapping={i:(i,model.names.index(n))for i,n in enumerate(part.names)}
   mesh=part.mesh(choices={i:min(1,n-1)for i,(_,n,_)in enumerate(part.parts)},target=model.bind,mapping=mapping);triangles+=triangle_lines(mesh,materials)
   # Preserve the same skin choice across gloves, sleeves and the body.
   skin_counts.append(part.numskinfamilies)
   used={material for material,_ in mesh}
   for ref in range(part.numskinref):
    if part.skin[ref] in used:
     skin_columns.append([materials[part.skin[skin*part.numskinref+ref]]for skin in range(part.numskinfamilies)])
  smd(model,np.array([bind]),folder/'reference.smd',triangles)
  # SMD is the editor entry point; GoldSrc MDL needs decompilation in fragMOTION.
  for skin in range(skin_counts[0]):
   replacements={column[0]:column[skin]for column in skin_columns}
   smd(model,np.array([bind]),folder/f'reference_skin_{skin:02d}.smd',[replacements.get(line,line)for line in triangles])
  idle_frames=sequence_frames(model,'vf_hang_idle')
  idle_mesh=posed_triangles(model,idle_frames,triangles)
  smd(model,idle_frames,folder/'atelier.smd',idle_mesh)
  for skin in range(skin_counts[0]):
   replacements={column[0]:column[skin]for column in skin_columns}
   smd(model,idle_frames,folder/f'atelier_skin_{skin:02d}.smd',[replacements.get(line,line)for line in idle_mesh])
  for gesture in ('vf_vault','vf_hang_catch','vf_hang_arm','vf_climb','vf_drop','vf_slide_start','vf_slide_loop','vf_slide_end'):
   frames=sequence_frames(model,gesture)
   smd(model,frames,folder/(gesture+'_scene.smd'),posed_triangles(model,frames,triangles))
  # GoldSrc prunes bones with no mesh: keep weapon sockets and the full rig
  # available even though the workshop displays only hands or the character.
  keep=[];undo=Rotation.from_euler('z',-90,degrees=True).as_matrix()
  for b in range(len(model.names)):
   keep.append(triangles[0]);p=undo@model.bind[b][:3,3]
   for d in ([0,0,0],[.001,0,0],[0,.001,0]):keep.append(str(b)+' '+' '.join(f'{v:.8f}'for v in [*(p+d),0,0,1,0,0]))
  smd(model,np.array([bind]),folder/'skeleton_keep.smd',keep)
  qc='$modelname "atelier.mdl"\n$cd "."\n$cdtexture "."\n$body workshop "reference"\n$bodygroup keep_bones {\n blank\n studio "skeleton_keep"\n}\n'
  if len(set(skin_counts))!=1:raise ValueError('Workshop parts have incompatible skin families')
  skins=skin_counts[0]
  qc+='$texturegroup personas\n{\n'+''.join('{ '+' '.join('"'+column[skin]+'"'for column in skin_columns)+' }\n'for skin in range(skins))+'}\n'
  for name in names:
   info=sequence_info(model,name);refs=[]
   for b in range(info['blends']):
    frames=sequence_frames(model,name,blend=b);key=name+'_'+str(b);smd(model,frames,folder/(key+'.smd'));refs.append(' "'+key+'"')
    records.append(dict(view=view,gesture=name,corner=b,frames=len(frames),seconds=TIMES.get(name,1.2),fps=info['fps'],editable=str(folder/(key+'.smd')),override=str(EDITS/view/(key+'.smd'))))
   options='\n blend YR -22.5 22.5\n blend XR -70 70' if len(refs)==4 else ''
   qc+='$sequence "'+name+'" {\n'+'\n'.join(refs)+f"\n fps {info['fps']:.6f}"+(' loop'if name in LOOPS or 'both_'in name else '')+options+'\n}\n'
  path=folder/'atelier.qc';path.write_text(qc,encoding='ascii');compiled=Studio(compile_model(path))
  assert set(compiled.names)==set(model.names),'Workshop must preserve every bone'
  assert compiled.numskinfamilies==skins,'Workshop must preserve every skin family'
  config=json.loads((ROOT/'assets/personas/personas.json').read_text(encoding='utf-8'))
  titles={0:'Skin de base'}|{t['skin']:t['title']for t in config['themes']}
  (folder/'skins.json').write_text(json.dumps([dict(skin=i,title=titles.get(i,'Skin '+str(i)),textures=[column[i]for column in skin_columns])for i in range(skins)],ensure_ascii=False,indent=2),encoding='utf-8')
  table='# Skins de l’atelier\n\nOuvrir atelier_skin_XX.smd charge le modèle texturé dans la pose suspendue. Si seule Default Pose apparaît, utiliser File / Merge avec vf_hang_idle_0.smd pour charger l’animation. Pour un autre geste, fusionner sa piste SMD. Les BMP restent dans ce même dossier.\n\n| Skin | Nom | Modèle texturé |\n| --- | --- | --- |\n'
  table+=''.join(f'| {i} | {titles.get(i,"Skin "+str(i))} | [atelier_skin_{i:02d}.smd](atelier_skin_{i:02d}.smd) |\n'for i in range(skins))
  (folder/'SKINS.md').write_text(table,encoding='utf-8')
  from traversal_bone_guide import catalog
  catalog(model,view,folder)
 (WORKSHOP/'gestures.json').write_text(json.dumps(records,indent=2))
 from traversal_bone_guide import render
 render(WORKSHOP/'reperes-mains.png')
 print('Workshop prepared:',WORKSHOP)

def install(view,name,corner,path):
 from build_traversal import FP_NAMES
 from traversal_animations import NAMES
 names=FP_NAMES if view=='first-person' else NAMES
 if name not in names or not 0<=corner<=3:raise ValueError('Unknown traversal gesture or blend corner')
 if ('aim_' not in name and 'both_' not in name) and corner:raise ValueError('This gesture has one animation track')
 model=Studio(ROOT/('generated/traversal/r01_rig_tr.mdl'if view=='first-person'else'generated/third-person/r01_tp.mdl'))
 default=sequence_frames(model,name,blend=corner);edited=resample(read(path,model),len(default))
 anatomical=[i for i,n in enumerate(model.names)if i and n not in {'VF_Weapon','VF_Magazine','VF_Bolt','Bone76','Bone71','Bone75','R01_Bolt'}]
 if np.max(np.abs(np.linalg.norm(edited[:,anatomical,:3,3],axis=-1)-np.linalg.norm(default[:,anatomical,:3,3],axis=-1)))>.15:raise ValueError('Bone lengths changed; use rotations to pose the skeleton')
 destination=EDITS/view/(name+'_'+str(corner)+'.smd');destination.parent.mkdir(parents=True,exist_ok=True)
 if destination.exists():shutil.copy2(destination,destination.with_suffix('.smd.previous'))
 if not destination.exists() or destination.read_bytes()!=Path(path).read_bytes():shutil.copy2(path,destination)
 if name in ('vf_vault','vf_stepup'):destination.with_suffix('.accepted.json').write_text(json.dumps(dict(gesture=name,revision='one-hand',sha256=hashlib.sha256(destination.read_bytes()).hexdigest())))
 print('Accepted edit:',destination)

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True);sub.add_parser('export');i=sub.add_parser('import');i.add_argument('--view',choices=['first-person','third-person'],required=True);i.add_argument('--gesture',required=True);i.add_argument('--corner',type=int,default=0);i.add_argument('file');sub.add_parser('apply');a=p.parse_args()
 if a.command=='export':export()
 elif a.command=='import':install(a.view,a.gesture,a.corner,a.file)
 else:
  for view in ('first-person','third-person'):
   for path in sorted((WORKSHOP/'retouches'/view).glob('*.smd')):
    m=re.fullmatch(r'(vf_[a-z0-9_]+)_([0-3])',path.stem)
    if not m:raise ValueError('Export name must end in _0..3.smd: '+path.name)
    install(view,m[1],int(m[2]),path)
  from third_person import build as tp
  from build_traversal import build as fp
  tp(ensure=True);fp(ensure=True)
  subprocess=__import__('subprocess');subprocess.run([sys.executable,str(ROOT/'play.py'),'--visual-lab','--deploy-only'],check=True)
if __name__=='__main__':main()
