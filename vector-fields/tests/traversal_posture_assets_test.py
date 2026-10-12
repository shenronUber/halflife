"""Intentional vault/slide changes preserve other fitted R1 animation tracks."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info,globals_of

def run():
 installed=ROOT.parent/'runtime/vector-engine/vf_visual/models';preserved=0;max_length=0.;max_wrist_step=0.
 for folder,files in [('vf_r01',['r01_tp','r01_tp_side','r01_tp_top']),('vf_traversal',['r01_rig_tr','r01_rig_side_tr','r01_rig_top_tr','r01_rig_fg_tr','r01_rig_side_fg_tr','r01_rig_top_fg_tr'])]:
  generated='third-person'if folder=='vf_r01'else'traversal'
  for name in files:
   previous=ROOT/'docs/validation/traversal/posture-review-before/vf_visual/models'/folder/(name+'.mdl')
   old=Studio(previous if previous.exists() else installed/folder/(name+'.mdl'));new=Studio(ROOT/'generated'/generated/(name+'.mdl'))
   assert new.names==old.names and new.sequences==old.sequences+['vf_stepup'],name
   for seq in old.sequences:
    if seq=='vf_vault':continue
    for corner in range(sequence_info(old,seq)['blends']):
     a=sequence_frames(old,seq,blend=corner);b=sequence_frames(new,seq,blend=corner)
     ids=[i for i in range(len(new.names))if not(seq.startswith('vf_slide_')and folder=='vf_r01'and i in(5,6,7))]
     assert np.max(np.abs(a[:,ids]-b[:,ids]))<.012,(name,seq,'unrelated joints changed');preserved+=1
   for seq in('vf_vault','vf_stepup','vf_slide_loop'):
    poses=sequence_frames(new,seq)
    # Reviewed slides already translate the torso; compare their limb lengths
    # against the original slide. Gun/magazine sockets are animated controls.
    normal=sequence_frames(old,seq)[0] if seq=='vf_slide_loop' else sequence_frames(new,'ref_aim_mp5'if folder=='vf_r01'else'idle')[0]
    ids=list(range(1,28)) if folder=='vf_r01' else [i for i,n in enumerate(new.names) if i and n not in ('Bone76','Bone71','Bone75','R01_Bolt')]
    lengths=np.linalg.norm(poses[:,ids][:,:,:3,3],axis=-1);base=np.linalg.norm(normal[ids][:,:3,3],axis=-1)
    error=float(np.max(np.abs(lengths-base)));max_length=max(max_length,error);assert error<.012,(name,seq,'stretched bone',error)
    if seq in ('vf_vault','vf_stepup'):
     hand=new.names.index('Bip01 L Hand'if folder=='vf_r01'else'Bone42')
     wrists=np.array([globals_of(p,new.parents)[hand,:3,:3]for p in poses])
     step=float(np.degrees(Rotation.from_matrix(wrists[:-1].transpose(0,2,1)@wrists[1:]).magnitude()).max())
     max_wrist_step=max(max_wrist_step,step);assert step<55,(name,seq,'wrist turn discontinuity',step)
   if folder=='vf_r01':
    for pose in sequence_frames(new,'vf_slide_loop'):
     g=globals_of(pose,new.parents);heel=g[7,:3,3];hip=g[1,:3,3]
     assert heel[1]-g[5,1,3]>8 and 2<heel[0]-hip[0]<4,(name,'right sole not under left buttock',heel,hip)
     assert g[6,0,3]-hip[0]>12 and g[6,1,3]<0,(name,'right knee must remain ahead/right')
     assert g[7,2,0]<-.99 and g[7,0,1]<-.85 and g[7,1,1]>.49,(name,'supporting sole/toe axes')
    for seq in('vf_vault','vf_stepup'):
     poses=sequence_frames(new,seq)
     for i in range(round(len(poses)*.42),round(len(poses)*.68)):
      g=globals_of(poses[i],new.parents)
      assert min(g[4,2,3],g[7,2,3])>-15.2,(name,seq,'ankles must clear the top',i)
 families=Studio(installed/'vf_skins/persona_scout.mdl').numskinfamilies;assert families==23
 report=dict(preserved_tracks=preserved,max_bone_length_error=max_length,maximum_wrist_step_degrees=max_wrist_step,skin_families=families)
 out=ROOT/'docs/validation/traversal/posture-review';out.mkdir(parents=True,exist_ok=True);(out/'compiled-assets.json').write_text(json.dumps(report,indent=2))
 print('PASS posture assets',json.dumps(report))
if __name__=='__main__':run()
