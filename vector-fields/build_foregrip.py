"""First-person R-01 foregrip poses; original weapon and magazine tracks retained."""
import hashlib,json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import build_modular as base
from build_reference_platforms import read_frames,write_frames,globals_of,solve_arm,blend,steady_forearm
from studio_assets import Studio

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'generated/r01'
RECIPE=ROOT/'assets/animations/r01-first-person-foregrip.json'
SEQUENCES=['idle','idle_1','shoot1','reload','draw','shoot1_1','shoot2','shoot2_1','empty_idle']
LEFT=set(range(10,32))


def grip_pose(recipe):
    # Index-to-pinky follows the grip's upward axis; the fingers wrap forward
    # around its small rubber cylinder, with the palm on the left outer side.
    x=np.array(recipe['axis_up'],dtype=float);x/=np.linalg.norm(x)
    y=np.array([0.,1.,0.]);y-=x*(x@y);y/=np.linalg.norm(y)
    m=np.eye(4);m[:3,:3]=np.column_stack([x,y,np.cross(x,y)])
    m[:3,3]=np.array(recipe['centre'])-m[:3,:3]@recipe['hand_centre']
    return m


def hold_weight(sequence,frame):
    if sequence!='reload':return 1.
    if frame<18:return 1-frame/18
    if frame>99:return min(1.,(frame-99)/30)
    return 0.


def build(out=OUT):
    recipe=json.loads(RECIPE.read_text(encoding='utf-8'))
    names,parents,_=base.skeleton(out/'mp40_hands.smd')
    from model_contract import check_skeleton
    check_skeleton(names,'first_person')
    _,idle=read_frames(out/'idle.smd')
    closed={b:idle[0][b].copy() for b in range(13,32)}
    # Match the index to the closed middle-finger chain on this smaller grip.
    for index,middle in zip(range(16,20),range(20,24)):
        closed[index][:3,:3]=closed[middle][:3,:3]
    for name,degrees in recipe.get('finger_curl_degrees',{}).items():
        b=next(i for i,n in names.items()if n==name)
        closed[b][:3,:3]=Rotation.from_euler('x',degrees,degrees=True).as_matrix()@closed[b][:3,:3]
    grip=grip_pose(recipe);records=[]
    for platform,suffix,prefix in [('bottom','',''),('side','_side','side_'),('top','_top','top_')]:
        qc=(out/f'r01_rig{suffix}.qc').read_text(encoding='ascii')
        qc=qc.replace(f'r01_rig{suffix}.mdl',f'r01_rig{suffix}_fg.mdl')
        max_error=0.;step=0.
        for sequence in SEQUENCES:
            source=prefix+sequence;text,original=read_frames(out/(source+'.smd'))
            authored=[];last=None
            for frame,pose in enumerate(original):
                local={b:m.copy() for b,m in pose.items()};weight=hold_weight(sequence,frame)
                if weight:
                    g=globals_of(local,parents);holding=g[40]@grip
                    target=blend(g[12],holding,weight)
                    if sequence=='reload' and weight<1:
                        # Move outside the receiver on approach/release, avoiding
                        # a straight line through the magazine collar.
                        u=frame/18 if frame<18 else min(1,(frame-99)/30)
                        target[:3,3]+=g[40][:3,:3]@np.array([-1.8*np.sin(np.pi*u),0,-.6*np.sin(np.pi*u)])
                    for b in range(13,32):local[b]=blend(local[b],closed[b],weight)
                    error,_,_=solve_arm(local,parents,target,neutral_wrist=platform=='side')
                    if platform=='top':steady_forearm(local,parents,idle[0][10])
                    max_error=max(max_error,error)
                assert all(np.array_equal(local[b],pose[b]) for b in names if b not in LEFT),'weapon/right hand track changed'
                if last is not None:
                    step=max(step,float(Rotation.from_matrix(last[10][:3,:3].T@local[10][:3,:3]).magnitude()*180/np.pi))
                last=local;authored.append(local)
            target_name=source+'_fg';write_frames(out/(target_name+'.smd'),text,authored)
            qc=qc.replace('"'+source+'"\n','"'+target_name+'"\n')
        path=out/f'r01_rig{suffix}_fg.qc';path.write_text(qc,encoding='ascii')
        model=Studio(base.compile_model(path))
        assert model.sequences==SEQUENCES and len(model.names)==43
        records.append(dict(platform=platform,path=str(model.path),sha256=hashlib.sha256(model.data).hexdigest(),max_ik_error=max_error,max_forearm_step_degrees=step))
    record=dict(recipe=recipe,models=records,edited_bones=[names[i]for i in sorted(LEFT)],preserved='all weapon, magazine, bolt and right-hand tracks; original sequence names/order/events',reload_seconds=1.5)
    (out/'foregrip-motion.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print('PASS foregrip authored',json.dumps(records));return record


if __name__=='__main__':build()
