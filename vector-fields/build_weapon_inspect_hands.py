"""Complete inspection hands without changing shared player/FPS meshes.

The MP40 donor only has a right palm/thumb and a left sleeve. Mirror its
complete left hand in a held pose to recover the right fingers and sleeve.
Keep all currently installed glove/sleeve skin families and articulated fingers.
Both wrist rims follow their wrists instead of stretching from an elbow bone.
"""
import hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from studio_assets import Studio,smd_uv
from animation_assets import sequence_frames,globals_of
from build_modular import write_smd,compile_model

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'runtime/vector-engine/vf_visual/models/vf_r01'
OUT=ROOT/'generated/weapon-inspect'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def build(source=BASE,ensure=False):
    inputs=[Path(__file__),source/'r01_rig.mdl',source/'r01_fp_gloves.mdl',source/'r01_fp_sleeves.mdl']
    fingerprint={p.name:digest(p) for p in inputs}
    manifest=OUT/'hands.json'
    if ensure and manifest.exists():
        old=json.loads(manifest.read_text())
        if old['inputs']==fingerprint and all((OUT/p['file']).exists() and digest(OUT/p['file'])==p['sha256'] for p in old['parts']):return
    OUT.mkdir(parents=True,exist_ok=True)
    rig=Studio(source/'r01_rig.mdl');byname={name:i for i,name in enumerate(rig.names)}
    idle=globals_of(sequence_frames(rig,0)[0],rig.parents)
    header=['version 1','nodes']+[f'{i} "{name}" {rig.parents[i]}' for i,name in enumerate(rig.names)]+['end','skeleton','time 0']
    for i,m in enumerate(rig.bind):
        local=np.linalg.inv(rig.bind[rig.parents[i]])@m if rig.parents[i]>=0 else m
        values=[*local[:3,3],*Rotation.from_matrix(local[:3,:3]).as_euler('xyz')]
        header.append(str(i)+' '+' '.join(f'{v:.9f}' for v in values))
    header.append('end');records=[]
    mirror=np.diag([-1.,1.,1.,1.])
    for kind in ('gloves','sleeves'):
        model=Studio(source/('r01_fp_'+kind+'.mdl'));name='inspect_'+kind
        textures=model.write_textures(OUT,name)
        mesh=[];right_added=0;left_wrist_corrected=0
        for tex,triangle in model.mesh():
            ids=[byname[model.names[v['b']]] for v in triangle]
            # The elbow-weighted glove rim stretched into a triangular flap
            # when either wrist rotated away from its original MP40 pose.
            if kind=='gloves' and any(i<=9 for i in ids):continue
            def row(v,b,p,n):
                uv=smd_uv(v['uv'],model.textures[tex][1],model.textures[tex][2])
                return str(b)+' '+' '.join(f'{x:.9f}' for x in [*p,*n,*uv])
            left=[]
            for v,b in zip(triangle,ids):
                p=v['p'].copy();n=v['n'].copy()
                if kind=='gloves' and b==10:
                    b=12;left_wrist_corrected+=1
                elif kind=='sleeves' and b==10:
                    local=(np.linalg.inv(rig.bind[12])@np.r_[p,1])[:3]
                    if local[1]>-4:
                        amount=np.clip((local[1]+4)/4,0,1)
                        if local[1]>-.35:amount=1
                        radius=math.sqrt((local[0]/1.8)**2+(local[2]/1.3)**2)
                        if radius>1:local[[0,2]]*=1-amount*(1-1/radius)
                        local[1]=min(local[1],-.35)
                        p=(rig.bind[12]@np.r_[local,1])[:3];b=12;left_wrist_corrected+=1
                left.append(row(v,b,p,n))
            mesh.append((textures[tex],left))
            right=[]
            for v,b in zip(triangle,ids):
                if kind=='gloves':
                    # Bake the donor's curved fingers into wrist coordinates.
                    # Inspection holds the grip throughout, so no new finger
                    # bones or shared finger animation tracks are needed.
                    donor=np.linalg.inv(idle[12])@idle[b]@np.linalg.inv(rig.bind[b])
                    mat=rig.bind[6]@mirror@donor;bone=6
                else:
                    mat=rig.bind[6]@mirror@np.linalg.inv(rig.bind[12]);bone=4
                p=(mat@np.r_[v['p'],1])[:3];n=mat[:3,:3]@v['n']
                if kind=='sleeves':
                    local=(np.linalg.inv(rig.bind[6])@np.r_[p,1])[:3]
                    if local[1]>-4:
                        # Let the sleeve opening follow the wrist. Its old
                        # rigid elbow weights exposed triangular cuff gaps.
                        amount=np.clip((local[1]+4)/4,0,1)
                        local[[0,2]]*=1-.22*amount
                        local[1]=min(local[1],.0)
                        p=(rig.bind[6]@np.r_[local,1])[:3];bone=6
                right.append(row(v,bone,p,n))
            mesh.append((textures[tex],list(reversed(right))));right_added+=1
        if kind=='gloves':
            # The rebuilt right hand needs a wrist band. The original left
            # glove already has a complete rim, now attached to its wrist.
            segments=16;rings=[]
            for y,rx,rz in ((-1.55,1.68,1.22),(-.35,1.60,1.14),(.82,1.53,1.08)):
                rings.append([np.array([rx*math.cos(i*2*math.pi/segments),y,rz*math.sin(i*2*math.pi/segments)]) for i in range(segments)])
            for j in range(2):
                for i in range(segments):
                    for corners in (((j,i),(j,(i+1)%segments),(j+1,i)),((j+1,i),(j,(i+1)%segments),(j+1,(i+1)%segments))):
                        rows=[]
                        for ring,k in corners:
                            local=rings[ring][k];normal=np.array([local[0]/1.6**2,0,local[2]/1.15**2]);normal/=np.linalg.norm(normal)
                            p=(rig.bind[6]@np.r_[local,1])[:3];normal=rig.bind[6][:3,:3]@normal
                            uv=[(264+240*(k/segments))/512,1-(392+112*ring/2)/512]
                            rows.append('6 '+' '.join(f'{x:.9f}' for x in [*p,*normal,*uv]))
                        mesh.append((textures[0],list(reversed(rows))));right_added+=1
        smd=OUT/(name+'.smd');write_smd(smd,header,mesh)
        qc=OUT/(name+'.qc')
        qc.write_text(f'$modelname "{name}.mdl"\n$cd "."\n$cdtexture "."\n$body part "{name}"\n$sequence idle "{name}" fps 1\n'
            +'$texturegroup personas\n{\n'+''.join('{ "'+textures[model.skin[i*model.numskinref]]+'" }\n' for i in range(model.numskinfamilies))+'}\n',encoding='ascii')
        target=compile_model(qc);compiled=Studio(target)
        assert compiled.numskinfamilies==model.numskinfamilies
        assert len(compiled.mesh())==len(mesh)
        assert ('Bone07' if kind=='gloves' else 'Bone05') in compiled.names
        assert left_wrist_corrected>0
        if kind=='gloves':assert not any(compiled.names[v['b']]=='Bone40' for _,tri in compiled.mesh() for v in tri)
        else:
            for _,tri in compiled.mesh():
                for v in tri:
                    if compiled.names[v['b']]=='Bone42':
                        p=(np.linalg.inv(rig.bind[12])@np.r_[v['p'],1])[:3]
                        if p[1]>=-.3501:assert (p[0]/1.8)**2+(p[2]/1.3)**2<1.001
        records.append(dict(file=target.name,sha256=digest(target),skin_families=compiled.numskinfamilies,
            source_sha256=digest(source/('r01_fp_'+kind+'.mdl')),right_triangles_added=right_added,
            left_wrist_vertices_corrected=left_wrist_corrected,triangles=len(mesh)))
    manifest.write_text(json.dumps(dict(inputs=fingerprint,parts=records),indent=2))
    print('PASS inspection right hand and sleeve: complete fingers, both sleeves, unchanged equipped skin indices')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--source-generated',action='store_true');parser.add_argument('--ensure',action='store_true')
    args=parser.parse_args();build(ROOT/'generated/r01' if args.source_generated else BASE,args.ensure)
