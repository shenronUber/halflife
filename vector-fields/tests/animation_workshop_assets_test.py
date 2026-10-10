"""Geometry-based grip checks and compiled animation/retarget validation, offline."""
import hashlib,json,struct,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from studio_assets import Studio
from animation_assets import channel,sequence_frames,sequence_info,globals_of
from build_reference_platforms import read_frames,globals_of as smd_globals
from build_modular import skeleton
FP=ROOT/'generated/r01'
INDEX=('Bone47','Bone48','Bone49','Bone50')


def grip_checks():
    model=Studio(FP/'r01_fp_gloves.mdl');points={}
    for _,tri in model.mesh():
        for v in tri:
            name=model.names[v['b']]
            if name in INDEX:
                points.setdefault(name,[]).append(np.linalg.inv(model.bind[v['b']])@np.r_[v['p'],1])
    report={}
    for key,suffix in [('bottom',''),('side','_side'),('top','_top')]:
        rig=Studio(FP/f'r01_rig{suffix}.mdl');frames=sequence_frames(rig,'reload')
        mag=rig.names.index('Bone71');gun=rig.names.index('Bone76')
        design=np.linalg.inv(np.linalg.inv(rig.bind[mag])@rig.bind[gun])
        worst=0.
        for t in range(18,94):
            g=globals_of(frames[t],rig.parents);convert=design@np.linalg.inv(g[mag])
            posed=np.vstack([(convert@g[rig.names.index(n)]@np.array(ps).T).T[:,:3]for n,ps in points.items()])
            # Conservative un-bevelled envelope of the widest shared hand-contact
            # shell. It excludes the collar and low drum: visual checks still matter.
            q=np.abs(posed-[-.15,15.25,-8.3])-np.array([2.35,2.05,10.8])/2
            signed=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(q.max(1),0)
            worst=max(worst,float(-signed.min()))
        assert worst<.1,(key,'index penetrates shared cassette shell',worst)
        report[key]=dict(held_frames=76,max_conservative_shell_penetration=worst)
    return report


def assets():
    # A literal compressed run validates held samples and the next RLE block.
    data=bytes([2,4])+struct.pack('<hh',10,20)+bytes([1,2])+struct.pack('<h',30)
    assert [channel(data,0,i)for i in range(6)]==[10,20,20,20,30,30]
    grip=grip_checks()
    names,parents,_=skeleton(FP/'mp40_hands.smd')
    root=np.eye(4);root[:3,:3]=Rotation.from_euler('z',90,degrees=True).as_matrix()
    max_decoder_error=0.;poses=0
    for key,suffix,prefix in [('bottom','',''),('side','_side','side_'),('top','_top','top_')]:
        model=Studio(FP/f'r01_rig{suffix}.mdl')
        for name in ['idle','shoot1_1','reload']:
            compiled=sequence_frames(model,name)
            _,smd=read_frames(FP/(prefix+name+'.smd'))
            for t in range(len(smd)):
                actual=globals_of(compiled[t],model.parents);expected=smd_globals(smd[t],parents)
                for bone,label in enumerate(model.names):
                    source=next(b for b,n in names.items()if n==label)
                    error=np.max(np.abs(actual[bone]-root@expected[source]))
                    max_decoder_error=max(max_decoder_error,float(error))
                poses+=1
    assert max_decoder_error<.025,max_decoder_error
    # The grip edit preserves every weapon mesh/texture file from its manifest.
    manifest=json.loads((FP/'manifest.json').read_text());unchanged=0
    for piece in manifest['pieces']:
        assert hashlib.sha256((FP/(piece['id']+'.mdl')).read_bytes()).hexdigest()==piece['sha256'],piece['id']
        unchanged+=1
    # Verify the compiled donor preview rather than just the authoring report.
    current=Studio(ROOT/'generated/personas/persona_rig.mdl')
    preview=Studio(ROOT/'generated/animation-workshop/persona_rig_cs_preview.mdl')
    assert preview.names==current.names and preview.sequences[:77]==current.sequences
    assert len(preview.sequences)==81
    record=json.loads((ROOT/'generated/animation-workshop/third-person-preview.json').read_text())
    assert hashlib.sha256(preview.data).hexdigest()==record['sha256']
    return dict(grips=grip,compiled_poses=poses,max_decoder_global_error=max_decoder_error,
                weapon_models_unchanged=unchanged,third_person_old_sequences=77,third_person_added_reloads=4,
                limits=['cassette shell envelope is not a full mesh collision solver','borrowed third-person reloads still need a moving magazine and game trigger'])


if __name__=='__main__':
    result=assets();path=ROOT/'build/animation-workshop/assets-verification.json';path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result,indent=2));print('PASS offline animations',json.dumps(result))
