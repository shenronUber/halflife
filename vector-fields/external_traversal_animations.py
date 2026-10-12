"""Verified source body motion, fitted to the existing GoldSrc skeleton.
No source mesh, source skeleton or source root locomotion enters the game.
"""
import functools,hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from external_death_animations import Gltf,mapping
from animation_assets import globals_of,sequence_frames
from build_reference_platforms import blend
from studio_assets import Studio
ROOT=Path(__file__).resolve().parent
BANK=ROOT/'assets/animations/traversal-banks'
RECIPE=ROOT/'assets/animations/traversal.json'

def inputs():
 return [Path(__file__),RECIPE,BANK/'sources.json']+list(BANK.glob('*.glb'))

@functools.lru_cache(maxsize=8)
def track(file):
 source=Gltf(BANK/file)
 record=next(r for r in json.loads((BANK/'sources.json').read_text())['assets'] if r['file']==file)
 if hashlib.sha256((BANK/file).read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Traversal source hash mismatch: '+file)
 return source,*source.sample('mixamo.com')

@functools.lru_cache(maxsize=8)
def retarget(file):
 source,frames,duration=track(file);model=Studio(ROOT/'generated/personas/persona_rig.mdl')
 indices=mapping(source,model);reference=source.bind
 neutral=sequence_frames(model,'ref_aim_mp5')[0];target_bind=globals_of(neutral,model.parents)
 # Source +Z forward / +X left / +Y up -> compiled +X / +Y / +Z.
 convert=np.array([[0,0,1],[1,0,0],[0,1,0]],float);out=[]
 for pose in frames:
  local=neutral.copy();rotations=[]
  for i,node in enumerate(indices):
   parent=model.parents[i]
   rotation=neutral[0,:3,:3] if i==0 else convert@pose[node,:3,:3]@reference[node,:3,:3].T@convert.T@target_bind[i,:3,:3] if node is not None else rotations[parent]@neutral[i,:3,:3]
   local[i,:3,:3]=rotations[parent].T@rotation if parent>=0 else rotation
   rotations.append(rotation)
  # Root rotation/translation stays in the game's wall coordinate frame.
  local[0]=neutral[0]
  out.append(local)
 return np.array(out),duration

def body(name,t,neutral):
 recipe=json.loads(RECIPE.read_text());kind='climb' if name=='vf_climb' else 'drop' if name=='vf_drop' else 'hang'
 spec=recipe['clips'][kind];frames,duration=retarget(spec['file'])
 seconds=spec['range'][0]+(spec['range'][1]-spec['range'][0])*t
 index=np.clip(seconds/duration*(len(frames)-1),0,len(frames)-1);i=min(int(index),len(frames)-2)
 pose=np.array([blend(a,b,index-i) for a,b in zip(frames[i],frames[i+1])])
 if kind=='climb':
  start=body('vf_hang_idle',0,neutral)
  entry=min(1,t/.18);exit=min(1,(1-t)/.18)
  pose=np.array([blend(a,b,entry) for a,b in zip(start,pose)])
  pose=np.array([blend(a,b,exit) for a,b in zip(neutral,pose)])
 # Arm/wrist fitting is performed after the source torso and legs.
 for b in [0,14,15,16,17,18,19,20,21,22,23,24,25,26,27]:pose[b]=neutral[b]
 return pose
