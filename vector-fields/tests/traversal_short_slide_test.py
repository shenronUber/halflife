"""Compiled slide poses retain the reviewed upper body and fold a grounded leg."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info,globals_of

def main():
    before=ROOT/'docs/validation/traversal/short-slide-before'
    report=dict(preserved_tracks=0,slide_frames=0,max_untouched_error=0.,max_length_error=0.)
    for name in('r01_tp','r01_tp_side','r01_tp_top'):
        old=Studio(before/('third-person-'+name+'.mdl'));new=Studio(ROOT/'generated/third-person'/(name+'.mdl'))
        assert old.names==new.names and old.sequences==new.sequences
        assert old.numskinfamilies==new.numskinfamilies
        changed=[new.names.index(n)for n in('Bip01 R Leg','Bip01 R Leg1','Bip01 R Foot')]
        unchanged=[i for i in range(len(new.names))if i not in changed]
        for sequence in new.sequences:
            for corner in range(sequence_info(new,sequence)['blends']):
                a=sequence_frames(old,sequence,blend=corner);b=sequence_frames(new,sequence,blend=corner)
                if not sequence.startswith('vf_slide_'):
                    assert np.max(np.abs(a-b))<.012,(name,sequence,'unrelated animation changed')
                    report['preserved_tracks']+=1;continue
                error=float(np.max(np.abs(a[:,unchanged]-b[:,unchanged])))
                report['max_untouched_error']=max(report['max_untouched_error'],error)
                assert error<.012,(name,sequence,'head, gun, torso or left leg changed')
                length_error=float(np.max(np.abs(np.linalg.norm(a[:,:, :3,3],axis=2)-np.linalg.norm(b[:,:, :3,3],axis=2))))
                report['max_length_error']=max(report['max_length_error'],length_error)
                assert length_error<.012,(name,sequence,'stretched leg')
                if sequence=='vf_slide_loop':
                    assert np.max(np.abs(b[0]-b[-1]))<.012,(name,'open slide loop')
                    for pose in b:
                        g=globals_of(pose,new.parents);hip=g[1][:3,3];knee=g[6][:3,3];foot=g[7][:3,3]
                        assert knee[0]-hip[0]>12 and abs(foot[0]-hip[0])<1,(name,'heel must sit under buttock and knee lead')
                        assert min(knee[2],foot[2])>-16 and foot[2]<hip[2],(name,'right knee and boot must stay above floor')
                        assert abs(foot[1]-g[5][1,3])<1,(name,'right foot twisted sideways')
                        assert g[7][0,1]<-.99 and g[7][2,0]<-.99,(name,'tucked sole orientation')
                        assert g[4][0,3]-hip[0]>20 and g[4][2,1]>.97,(name,'leading left boot retained')
                report['slide_frames']+=len(b)
    old=Studio(before/'traversal-slide_legs.mdl');new=Studio(ROOT/'generated/traversal/slide_legs.mdl')
    assert old.numskinfamilies==new.numskinfamilies==23
    old_mesh=old.mesh({0:1,1:1});new_mesh=new.mesh({0:1,1:1});assert len(old_mesh)==len(new_mesh)
    a=np.array([v['p']for _,tri in old_mesh for v in tri]);b=np.array([v['p']for _,tri in new_mesh for v in tri])
    # Studio mesh vertices are in SMD coordinates: +X is the left side.
    left=a[:,0]>0
    assert np.max(np.abs(a[left]-b[left]))<.02,'first-person leading leg changed'
    assert np.isfinite(b).all() and np.max(np.abs(a-b))>15,'first-person right leg was not folded'
    report['first_person_legs_vertices']=len(b);report['skins']=23
    out=ROOT/'docs/validation/traversal/short-slide';out.mkdir(parents=True,exist_ok=True)
    (out/'compiled-pose.json').write_text(json.dumps(report,indent=2))
    print('PASS short slide poses',json.dumps(report))

if __name__=='__main__':main()
