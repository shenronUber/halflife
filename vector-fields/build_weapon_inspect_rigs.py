"""Independent one-handed inspection: free left hand, raised gun, rooted arms."""
import argparse,hashlib,json,math,struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation,Slerp
from studio_assets import Studio
from animation_assets import sequence_frames,globals_of
from build_reference_platforms import solve_arm
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'runtime/vector-engine/vf_visual/models/vf_r01'
OUT=ROOT/'generated/weapon-inspect'
RAISE_SECONDS=.8

def smooth(t):t=np.clip(t,0,1);return np.clip(t**3*(t*(t*6-15)+10),0,1)
def sample(t):
    times=[0,RAISE_SECONDS,1.95,2.75,3.60,4.5]
    poses=np.array([[0,0,0,0,0,0],[42,-48,-12,4,2.5,2.5],
        [42,-48,-12,4,2.5,2.5],[42,48,12,4,-2.5,2.5],[42,48,12,4,-2.5,2.5],[0,0,0,0,0,0]])
    if t>=4.5:return poses[0]
    i=min(4,max(0,np.searchsorted(times,t,side='right')-1));u=smooth((t-times[i])/(times[i+1]-times[i]))
    return poses[i]*(1-u)+poses[i+1]*u

def left_release(t):
    return smooth((t-.20)/.50)*(1-smooth((t-3.60)/.65))

def fingers_open(t):
    return smooth((t-.10)/.30)*(1-smooth((t-4.12)/.30))

def mix_rotation(a,b,u):
    return Slerp([0,1],Rotation.from_matrix([a,b]))([np.clip(u,0,1)]).as_matrix()[0]

def encode(model,frames):
    data=bytearray(model.data);bones,off=struct.unpack_from('<ii',data,140)
    channels=[]
    for bone in range(bones):
        defaults=np.array(struct.unpack_from('<6f',data,off+112*bone+64))
        xyz=frames[:,bone,:3,3]
        angles=np.unwrap(Rotation.from_matrix(frames[:,bone,:3,:3]).as_euler('xyz'),axis=0)
        angles+=np.round((defaults[3:]-angles[0])/(2*math.pi))*2*math.pi
        delta=np.concatenate([xyz,angles],axis=1)-defaults
        scales=np.maximum(np.max(np.abs(delta),axis=0)/30000,1e-8)
        struct.pack_into('<6f',data,off+112*bone+88,*scales)
        channels.append(np.round(delta/scales).astype('<i2'))
    while len(data)%4:data.append(0)
    seqoff=len(data);oldseq=struct.unpack_from('<i',data,168)[0];descriptor=bytearray(data[oldseq:oldseq+176])
    descriptor[:32]=b'inspect_both_sides'.ljust(32,b'\0')
    struct.pack_into('<f',descriptor,32,30);struct.pack_into('<i',descriptor,56,len(frames))
    struct.pack_into('<5i',descriptor,36,0,0,0,0,0)
    struct.pack_into('<i',descriptor,120,1)
    animoff=seqoff+176;struct.pack_into('<i',descriptor,124,animoff)
    data.extend(descriptor);data.extend(bytes(bones*12))
    for bone,values in enumerate(channels):
        entry=animoff+bone*12
        for axis in range(6):
            if not np.any(values[:,axis]):continue
            struct.pack_into('<H',data,entry+2*axis,len(data)-entry)
            data.extend(bytes([len(frames),len(frames)]));data.extend(values[:,axis].tobytes())
    struct.pack_into('<ii',data,164,1,seqoff);struct.pack_into('<i',data,72,len(data))
    return bytes(data)

def build(source=BASE,ensure=False):
    grip_sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.glob('r01_grip_*.mdl'))}
    if ensure and (OUT/'manifest.json').exists():
        records=json.loads((OUT/'manifest.json').read_text())
        if all((source/r['file']).exists() and hashlib.sha256((source/r['file']).read_bytes()).hexdigest()==r['source_sha256']
            and (OUT/r['file']).exists() and hashlib.sha256((OUT/r['file']).read_bytes()).hexdigest()==r['sha256']
            and r.get('builder_sha256')==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            and r.get('grip_sources_sha256')==grip_sources for r in records):return
    OUT.mkdir(parents=True,exist_ok=True);records=[]
    grip_points=np.array([np.r_[v['p'],1] for name in grip_sources for _,tri in Studio(source/name).mesh() for v in tri])
    assert len(grip_points)>0,'Rear grip/stock geometry is required for camera clearance validation'
    for path in sorted(source.glob('r01_rig*.mdl')):
        model=Studio(path);idle=sequence_frames(model,model.sequences[0])[0]
        g=globals_of(idle,model.parents);gun=g[40];frames=[];error=0;length_error=0
        stock_clearance=float('inf');left_separation=float('inf')
        relaxed=g[12].copy();relaxed[:3,3]=[12,10,-25]
        relaxed[:3,:3]=g[12,:3,:3]@Rotation.from_euler('z',30,degrees=True).as_matrix()
        # Relax the articulated left fingers before withdrawing the wrist.
        open_fingers={13:(-10,0,0),14:(-5,0,0),15:(-5,0,0)}
        for root,spread in ((16,-5),(20,-2),(24,2),(28,6)):
            for joint,angle in enumerate((12,12,18,14)):
                open_fingers[root+joint]=(-angle,0,spread if joint==0 else 0)
        lengths={right:np.array([np.linalg.norm(g[4 if right else 10,:3,3]-g[3,:3,3]),
            np.linalg.norm(g[6 if right else 12,:3,3]-g[4 if right else 10,:3,3])]) for right in (False,True)}
        for t in np.arange(136)/30:
            pitch,yaw,roll,forward,right,up=sample(t);lift=smooth(t/RAISE_SECONDS)*(1-smooth((t-3.6)/.9))
            d=np.eye(4);d[:3,:3]=Rotation.from_euler('xyz',[roll,-pitch,yaw],degrees=True).as_matrix()
            centre=gun[:3,3]+lift*np.array([9,7,2])+[forward,-right,up]
            d[:3,3]=centre-d[:3,:3]@gun[:3,3]
            local={i:m.copy() for i,m in enumerate(idle)}
            released=left_release(t);opened=fingers_open(t)
            for bone,angles in open_fingers.items():
                local[bone][:3,:3]=mix_rotation(idle[bone,:3,:3],Rotation.from_euler('xyz',angles,degrees=True).as_matrix(),opened)
            for side,wrist in ((True,6),(False,12)):
                goal=d@g[wrist]
                if not side:
                    goal[:3,3]=goal[:3,3]*(1-released)+relaxed[:3,3]*released
                    # Clear the contact along this grip's outward palm normal.
                    # Side-feed palms face upwards; a shared downward arc
                    # pulled their fingers back through the magazine shell.
                    detour=(d[:3,:3]@g[12,:3,2])*5
                    if path.stem.endswith('_fg'):
                        # Foregrip wrists start ahead of the feed collar. Clear
                        # it forward before lowering the hand beside the gun.
                        detour+=(d[:3,:3]@gun[:3,1])*8
                    goal[:3,3]+=math.sin(math.pi*released)*detour
                    goal[:3,:3]=mix_rotation(goal[:3,:3],relaxed[:3,:3],released)
                e,a,b=solve_arm(local,model.parents,goal,right=side,
                    elbow_pole=g[4 if side else 10,:3,3]+lift*np.array([8,-6,-6] if side else [0,0,-6]))
                error=max(error,e);length_error=max(length_error,float(np.max(np.abs(np.array([a,b])-lengths[side]))))
            now=globals_of(np.array(list(local.values())),model.parents)
            for side,elbow,wrist in ((True,4,6),(False,10,12)):
                actual=[np.linalg.norm(now[elbow,:3,3]-now[3,:3,3]),np.linalg.norm(now[wrist,:3,3]-now[elbow,:3,3])]
                length_error=max(length_error,float(np.max(np.abs(np.array(actual)-lengths[side]))))
            local[40]=np.linalg.inv(now[model.parents[40]])@d@gun
            if RAISE_SECONDS<=t<=3.60:
                stock_clearance=min(stock_clearance,float((d@gun@grip_points.T)[0].min()))
                left_separation=min(left_separation,float(np.linalg.norm(now[12,:3,3]-(d@g[12])[:3,3])))
            frames.append(np.array(list(local.values())))
        frames=np.array(frames);assert error<1e-5 and length_error<1e-6
        assert np.max(np.abs(frames[[0,-1]]-idle))<1e-5
        assert stock_clearance>5,stock_clearance
        assert left_separation>15,left_separation
        target=OUT/path.name;target.write_bytes(encode(model,frames))
        decoded=sequence_frames(Studio(target),'inspect_both_sides')
        wrist_error=0
        for n,(raw,quantized) in enumerate(zip(frames,decoded)):
            a=globals_of(raw,model.parents);b=globals_of(quantized,model.parents)
            wrist_error=max(wrist_error,float(np.max(np.abs(a[[6,12,40]]-b[[6,12,40]]))))
        assert wrist_error<.015,wrist_error
        records.append(dict(file=path.name,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            sha256=hashlib.sha256(target.read_bytes()).hexdigest(),frames=len(frames),hand_error=error,
            length_error=length_error,compiled_error=wrist_error,left_release_distance=left_separation,
            min_stock_camera_clearance=stock_clearance,grip_sources_sha256=grip_sources,
            builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
    assert len(records)==6
    (OUT/'manifest.json').write_text(json.dumps(records,indent=2))
    print('PASS six one-handed inspection carriers; left hand released, raised stock clears camera, right grip attached, rooted arms')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ensure',action='store_true');parser.add_argument('--source-generated',action='store_true')
    args=parser.parse_args();build(ROOT/'generated/r01' if args.source_generated else BASE,args.ensure)
