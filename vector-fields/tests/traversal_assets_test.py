"""Traversal asset, original animation and packed networking contracts."""
import json,re,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of
from build_traversal import VARIANTS,FP_NAMES
from traversal_animations import NAMES,TP_PALM

def run():
 checked=0
 for name in VARIANTS:
  old=Studio(ROOT/'generated/r01'/(name+'.mdl'));new=Studio(ROOT/'generated/traversal'/(name+'_tr.mdl'))
  assert set(old.names)<=set(new.names) and len(new.names)==62 and new.sequences[:9]==old.sequences and new.sequences[9:]==FP_NAMES
  for sequence in old.sequences:
   assert np.max(np.abs(sequence_frames(old,sequence)-sequence_frames(new,sequence)[:,[new.names.index(n)for n in old.names]]))<.01,(name,sequence)
  checked+=1
 for name in ['r01_tp','r01_tp_side','r01_tp_top']:
  model=Studio(ROOT/'generated/third-person'/(name+'.mdl'));assert model.sequences[81:]==NAMES
  # Player origin rises 22 units when peeking: the same world ledge is 18
  # units above the armed origin and 40 above the two-hand hanging origin.
  for seq,depth in [('vf_hang_idle',40)]+[(f'vf_hang_aim_{i}',18)for i in range(8)]:
   for corner in range(4 if 'aim'in seq else 1):
    pose=sequence_frames(model,seq,blend=corner)[0];g=globals_of(pose,model.parents)
    palm=(g[17]@np.r_[TP_PALM,1])[:3]
    assert np.linalg.norm(palm-[18,8,depth-1.4])<.015,(name,seq,corner,palm)
  checked+=1
 legs=Studio(ROOT/'generated/traversal/slide_legs.mdl');glove=Studio(ROOT/'generated/traversal/ledge_gloves.mdl')
 families=Studio(ROOT/'generated/personas/persona_scout.mdl').numskinfamilies
 assert legs.numskinfamilies==glove.numskinfamilies==families and len(legs.names)==1
 original_glove=Studio(ROOT/'generated/r01/r01_fp_gloves.mdl')
 palm_bounds=[]
 for model in [original_glove,glove]:
  b=model.names.index('Bone42');points=np.array([(np.linalg.inv(model.bind[b])@np.r_[v['p'],1])[:3]for _,tri in model.mesh()for v in tri if v['b']==b])
  palm_bounds.append([points.min(0),points.max(0)])
 assert np.max(np.abs(np.array(palm_bounds[0])-palm_bounds[1]))<.02,palm_bounds
 assert len(legs.mesh({0:1,1:1}))>200
 sleeve=Studio(ROOT/'generated/traversal/ledge_sleeves.mdl');assert sleeve.numskinfamilies==families
 counts={name:sum(v['b']==sleeve.names.index(name)for _,tri in sleeve.mesh()for v in tri)for name in ['Bone40','Bone05']}
 assert counts['Bone40']==counts['Bone05'] and counts['Bone05']>200,counts
 body=json.loads((ROOT/'generated/traversal/body_manifest.json').read_text());assert body['legs']['socket']['bone']=='Bone01'
 # The engine crashes on duplicate delta declarations; field counts are
 # bounded by its 64-entry bitmask. Verify actual lists, including ammo fields.
 text=(ROOT.parent/'network/delta.lst').read_text();blocks=re.findall(r'(\w+)\s+\w+\s+\w*\s*\{([^}]+)\}',text,re.S)
 assert blocks,'No network delta blocks found'
 for name,block in blocks:
  fields=re.findall(r'DEFINE_DELTA(?:_POST)?\s*\(\s*([\w.\[\]]+)',block)
  assert len(fields)==len(set(fields)) and len(fields)<=64,(name,len(fields))
 assert text.count('DEFINE_DELTA( iuser4, DT_INTEGER, 24, 1.0 )')>=2
 report=dict(carriers=checked,view_sequences=len(FP_NAMES),body_sequences=len(NAMES),original_first_person_sequences=9,skin_families=families,checks=['historical view animation tracks retained','world palm contacts in all third-person aim sectors','real sliding legs and boots','unique bounded network delta fields'])
 (ROOT/'generated/traversal/verification.json').write_text(json.dumps(report,indent=2));print('PASS traversal assets',json.dumps(report))
if __name__=='__main__':run()
