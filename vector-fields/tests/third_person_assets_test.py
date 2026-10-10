"""Check arm constraints, preserved gait and actual compiled module contacts."""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from third_person import Author,OUT,KEEP
from studio_assets import Studio
from animation_assets import sequence_frames,sequence_info,globals_of

def run():
    from release import check_native_interface
    engine=Path(__file__).resolve().parents[2]/'runtime/vector-engine'
    check_native_interface(engine,OUT.parents[1]/'build/client/client.dll')
    # The normal engine is now v3. Exercise mismatch rejection with isolated metadata.
    import tempfile
    with tempfile.TemporaryDirectory(dir=OUT.parents[1]/'build') as directory:
        old=Path(directory);(old/'vector-engine-build.json').write_text(json.dumps(dict(extension_version=2)),encoding='utf-8')
        try:check_native_interface(old,OUT.parents[1]/'build/client/client.dll')
        except RuntimeError:pass
        else:raise AssertionError('v3 client must reject v2 renderer metadata')
    a=Author();samples=0;contact=0.;length=0.;lower=0.;reload_contact=0.
    for platform,suffix in [('bottom',''),('side','_side'),('top','_top')]:
        rig=Studio(OUT/f'r01_tp{suffix}.mdl');assert rig.names[:28]==a.rig.names
        for name in ['ref_aim_mp5','ref_shoot_mp5','crouch_aim_mp5','crouch_shoot_mp5']:
            for bi in [0,1,None]:
                old=sequence_frames(a.rig,name,blend=bi);frames=sequence_frames(rig,name,blend=bi)
                lower=max(lower,float(np.max(np.abs(old[:,KEEP]-frames[:,KEEP]))))
                for frame,base in zip(frames,old):
                    g=globals_of(frame,rig.parents)
                    for side,ids in [('left',(15,16,17)),('right',(22,23,24))]:
                        cfg=a.recipe[side];palm=(g[ids[2]]@np.r_[cfg['palm'],1])[:3];socket=(g[28]@np.r_[np.array(cfg['contact'])*a.scale,1])[:3]
                        contact=max(contact,float(np.linalg.norm(palm-socket)))
                        for i,j in zip(ids,ids[1:]):
                            length=max(length,float(abs(np.linalg.norm(frame[j][:3,3])-np.linalg.norm(base[j][:3,3]))))
                    samples+=1
        # Engine gait replaces only the root/pelvis/leg chain before Spine.
        for stance,gait in [('ref_aim_mp5','walk'),('ref_aim_mp5','run'),('crouch_aim_mp5','crawl')]:
            upper=sequence_frames(rig,stance)[0]
            for gaitpose in sequence_frames(rig,gait):
                local=upper.copy();local[:8]=gaitpose[:8];g=globals_of(local,rig.parents)
                for side,i in [('left',17),('right',24)]:
                    cfg=a.recipe[side];palm=(g[i]@np.r_[cfg['palm'],1])[:3];target=(g[28]@np.r_[np.array(cfg['contact'])*a.scale,1])[:3]
                    contact=max(contact,float(np.linalg.norm(palm-target)))
                samples+=1
        # Magazine moves relative to the chassis, then returns to its seat.
        for name in ['ref_reload_mp5','crouch_reload_mp5','ref_reload_rifle','crouch_reload_rifle']:
            f=sequence_frames(rig,name);assert np.ptp(f[:,29,:3,3],axis=0).max()>3
            assert np.max(np.abs(f[0,29]-f[-1,29]))<.001
            info=sequence_info(rig,name)
            assert abs((info['frames']-1)/info['fps']-(3 if 'rifle' in name else 1.5))<.001
            magpoint=np.linalg.inv(a.mag)@np.r_[np.array([2.25,13.6,-6.0])*a.scale,1]
            for i,local in enumerate(f):
                g=globals_of(local,rig.parents);t=i/(len(f)-1)
                palm=(g[24]@np.r_[a.recipe['right']['palm'],1])[:3]
                target=(g[28]@np.r_[np.array(a.recipe['right']['contact'])*a.scale,1])[:3]
                reload_contact=max(reload_contact,float(np.linalg.norm(palm-target)))
                if .18<=t<=.9:
                    palm=(g[17]@np.r_[a.recipe['left']['palm'],1])[:3]
                    target=(g[29]@magpoint)[:3]
                    reload_contact=max(reload_contact,float(np.linalg.norm(palm-target)))
                samples+=1
    # GoldSrc interpolates two authored aim channels in joint space.
    # This is nonlinear at the support hand; allow half a unit (~1 cm),
    # while endpoint constraints themselves are below .01 units.
    assert contact<.5,contact
    assert length<1e-6,length
    assert lower<.01,lower
    assert reload_contact<.03,reload_contact
    report=dict(samples=samples,max_reload_contact_error=reload_contact,max_palm_contact_error=contact,max_arm_length_change=length,max_preserved_local_error=lower,checks=['three feed platforms, standing/crouched hold and fire','both authored aim blend endpoints and neutral interpolation','walk/run/crouch lower-body layering preserves hand contacts','twelve magazine tracks move and return to their exact seats','reload palms remain attached to the firing grip and moving magazine','MP5 reload duration matches the authoritative 1.5-second delay','no bone stretching or edited lower-body tracks','mixed renderer/client rejected before deployment (prevents stock player fallback)'])
    (OUT/'verification.json').write_text(json.dumps(report,indent=2));print('PASS R01 arm constraints',json.dumps(report))

if __name__=='__main__':run()
