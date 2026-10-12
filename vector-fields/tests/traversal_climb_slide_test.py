"""Check the compiled retouch against pre-edit clips and anatomical limits."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info,globals_of

def main():
    before=ROOT/'docs/validation/traversal/climb-slide-before'
    report=dict(preserved_tracks=0,climb_samples=0,slide_samples=0,
                maximum_slide_gaze_degrees=0.,minimum_early_hand_separation=999.)
    for folder,changed in [('traversal',{'vf_climb'}),
                           ('third-person',{'vf_slide_start','vf_slide_loop','vf_slide_end'})]:
        for path in (ROOT/'generated'/folder).glob('*.mdl'):
            old=Studio(before/(folder+'-'+path.name));new=Studio(path)
            assert old.names==new.names and old.sequences==new.sequences,path.name
            assert old.numskinfamilies==new.numskinfamilies,(path.name,'skin count')
            for seq in old.sequences:
                for corner in range(sequence_info(old,seq)['blends']):
                    a=sequence_frames(old,seq,blend=corner);b=sequence_frames(new,seq,blend=corner)
                    if seq not in changed:
                        assert np.max(np.abs(a-b))<.012,(path.name,seq,corner,'unrelated track changed')
                        report['preserved_tracks']+=1
                    elif folder=='third-person':
                        neck,head=(new.names.index(n)for n in('Bip01 Neck','Bip01 Head'))
                        right_leg=[new.names.index(n)for n in('Bip01 R Leg','Bip01 R Leg1','Bip01 R Foot')]
                        untouched=[i for i in range(len(new.names))if i not in (neck,head,*right_leg)]
                        assert np.max(np.abs(a[:,untouched]-b[:,untouched]))<.012,(path.name,seq,'slide body changed')
                        normal=globals_of(sequence_frames(new,'vf_climb')[-1],new.parents)
                        face_axis=normal[head][:3,:3].T@np.array([1.,0,0])
                        for index,pose in enumerate(b):
                            g=globals_of(pose,new.parents);look=g[head][:3,:3]@face_axis
                            if seq=='vf_slide_loop':
                                pitch=float(np.degrees(np.arcsin(np.clip(look[2],-1,1))))
                                assert -8<pitch<0,(path.name,'head must look ahead and slightly down',pitch)
                                report['maximum_slide_gaze_degrees']=max(report['maximum_slide_gaze_degrees'],abs(pitch))
                            report['slide_samples']+=1
                    else:
                        if seq!='vf_climb':continue
                        left=new.names.index('Bone42');right=new.names.index('Bone07')
                        # The held hand is camera constrained in game. The new
                        # climb must start with the same forward-facing contact
                        # and withdraw under the eye, retaining every bone length.
                        initial=globals_of(b[0],new.parents)
                        assert initial[left][0,3]>14 and initial[right][0,3]>14,(path.name,'climb grip must be forward')
                        assert initial[left][1,3]>7 and initial[right][1,3]<-7,(path.name,'palms must straddle the ledge')
                        for index,pose in enumerate(b):
                            g=globals_of(pose,new.parents)
                            assert np.max(np.abs(np.linalg.norm(pose[1:,:3,3],axis=1)-np.linalg.norm(a[index,1:,:3,3],axis=1)))<.012,(path.name,index,'bone stretch')
                            t=index/(len(b)-1)
                            if t<.65:
                                separation=np.linalg.norm(g[left][:3,3]-g[right][:3,3])
                                assert separation>15,(path.name,index,'hands crossed during press')
                                report['minimum_early_hand_separation']=min(report['minimum_early_hand_separation'],float(separation))
                            report['climb_samples']+=1
    (ROOT/'docs/validation/traversal/transitions/compiled-retouch.json').write_text(json.dumps(report,indent=2))
    print('PASS compiled climb/slide retouch',json.dumps(report))

if __name__=='__main__':main()
