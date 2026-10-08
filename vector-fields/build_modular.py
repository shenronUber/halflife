"""Build real GoldSrc bodygroups and matching textured 3D menu meshes.

All source models are local assets. Derived files stay under generated/.
Character donor vertices are retargeted through bone bind transforms, never
just relabelled. Preview geometry uses the same SMD pieces as StudioMDL.
"""
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
GEN=ROOT/'generated'
OUT=GEN/'modular'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'weapon-lab'))
from mix_models import read_smd

def prepare_inputs():
    engine=PROJECT/'runtime/xash3d'
    steam=Path('F:/SteamLibrary/steamapps/common/Half-Life/tfc/models/player')
    inputs=[(steam/'soldier/soldier2.mdl',GEN/'tfc-soldier','soldier2.qc'),
            (steam/'hvyweapon/hvyweapon2.mdl',GEN/'tfc-heavy','hvyweapon2.qc'),
            (steam/'scout/scout2.mdl',GEN/'tfc-scout','scout2.qc')]
    hk=PROJECT/'weapon-lab/generated/hk416'
    if not (hk/'v_9mmar.qc').exists():
        sources=list((PROJECT/'weapon-lab/extracted/640445').glob('*/Hands Options/HEV Hands/v_9mmar.mdl'))
        if len(sources)!=1:raise RuntimeError('Install the HK416 pack from the weapon laboratory first')
        inputs.append((sources[0],hk,'v_9mmar.qc'))
    for source,target,qc in inputs:
        if (target/qc).exists():continue
        if not source.exists():raise RuntimeError('Installed source asset missing: '+str(source))
        target.mkdir(parents=True,exist_ok=True)
        result=subprocess.run([str(engine/'mdldec.exe'),'-m',str(source),str(target)],cwd=engine,capture_output=True,text=True)
        (target/'decompile.log').write_text(result.stdout+result.stderr)
        if result.returncode or not (target/qc).exists():raise RuntimeError('Decompilation failed: '+str(source))

def skeleton(path):
    lines=path.read_text().splitlines()
    names={};parents={};pose={}
    for line in lines[lines.index('nodes')+1:]:
        if line=='end':break
        m=re.fullmatch(r'\s*(\d+) "([^"]+)" (-?\d+)',line)
        names[int(m[1])]=m[2];parents[int(m[1])]=int(m[3])
    for line in lines[lines.index('time 0')+1:]:
        if line=='end' or line.startswith('time '):break
        v=line.split();pose[int(v[0])]=list(map(float,v[1:7]))
    glob={}
    for b,vals in pose.items():
        x,y,z,rx,ry,rz=vals
        cx,sx=math.cos(rx),math.sin(rx);cy,sy=math.cos(ry),math.sin(ry);cz,sz=math.cos(rz),math.sin(rz)
        m=np.eye(4);m[:3,:3]=[[cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx],[sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx],[-sy,cy*sx,cy*cx]]
        m[:3,3]=[x,y,z]
        glob[b]=glob[parents[b]]@m if parents[b]>=0 else m
    return names,parents,glob

def write_smd(path,header,triangles):
    path.write_text('\n'.join(header+['triangles']+[v for m,rows in triangles for v in [m,*rows]]+['end'])+'\n')

def compile_model(qc):
    p=subprocess.run([str(PROJECT/'asset-probe/tools/studiomdl.exe'),qc.name],cwd=qc.parent,capture_output=True,text=True,input='',timeout=45)
    qc.with_suffix('.log').write_text(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    model=qc.with_suffix('.mdl')
    data=model.read_bytes();assert data[:4]==b'IDST' and struct.unpack_from('<i',data,4)[0]==10
    return model

def make_sprite(bmp,path):
    """Lossless BMP8 -> GoldSrc sprite conversion; keep original palette/pixels."""
    d=bmp.read_bytes();off=struct.unpack_from('<I',d,10)[0]
    w,h=struct.unpack_from('<ii',d,18);assert w>0 and h>0 and struct.unpack_from('<H',d,28)[0]==8
    stride=(w+3)&~3
    pixels=b''.join(d[off+y*stride:off+y*stride+w] for y in range(h-1,-1,-1))
    paloff=14+struct.unpack_from('<I',d,14)[0]
    palette=b''.join(bytes((d[paloff+i*4+2],d[paloff+i*4+1],d[paloff+i*4])) for i in range(256))
    spr=struct.pack('<4siiifiiifi',b'IDSP',2,2,0,math.hypot(w,h)/2,w,h,1,0.,0)
    spr+=struct.pack('<H',256)+palette+struct.pack('<iiiii',0,-w//2,h//2,w,h)+pixels
    path.write_bytes(spr)

def export_preview(name,pieces,pose_transforms=None):
    """VF3D v1: texture paths then triangles with group/variant/material and 3 x xyz/normal/uv."""
    textures=[];triangles=[]
    for group,variant,tri in pieces:
        for material,rows in tri:
            if material not in textures:textures.append(material)
            vertices=[]
            for row in rows:
                fields=row.split();bone=int(fields[0]);v=np.array(list(map(float,fields[1:4]))+[1.]);n=np.array(list(map(float,fields[4:7])))
                if pose_transforms is not None:
                    v=pose_transforms[bone]@v;n=pose_transforms[bone][:3,:3]@n
                vertices.extend([*v[:3],*n,float(fields[7]),1-float(fields[8])])
            triangles.append((group,variant,textures.index(material),vertices))
    (OUT/'sprites').mkdir(exist_ok=True)
    data=struct.pack('<4sIII',b'VF3D',1,len(textures),len(triangles))
    for i,material in enumerate(textures):
        sprite=f'{name}_{i}.spr';make_sprite(OUT/material,OUT/'sprites'/sprite)
        p=('sprites/vf_preview/'+sprite).encode();data+=p+b'\0'*(96-len(p))
    for g,v,t,verts in triangles:data+=struct.pack('<iii24f',g,v,t,*verts)
    (OUT/(name+'.vfm')).write_bytes(data)
    return {'triangles':len(triangles),'textures':len(textures),'bytes':len(data)}

def character():
    base=GEN/'tfc-soldier';ref=base/'soldier_reference_2.smd'
    header,nodes,_=read_smd(ref);_,_,target=skeleton(ref);byname={v:k for k,v in nodes.items()}
    parts=[];counts={}
    for variant,name in enumerate(['soldier','heavy','scout']):
        folder=GEN/('tfc-'+name);qc=next(folder.glob('*.qc')).read_text()
        refname=re.search(r'\$body "[^"]+" "([^"]+)"',qc)[1]
        smd=folder/(refname+'.smd');_,donor,tri=read_smd(smd);_,parents,bind=skeleton(smd)
        mapping={}
        for b,n in donor.items():
            p=b
            while donor[p] not in byname:p=parents[p]
            mapping[b]=byname[donor[p]]
        transforms={b:target[mapping[b]]@np.linalg.inv(bind[b]) for b in donor}
        groups=[[],[],[]]
        for mat,rows in tri:
            new=[];regions=[]
            for row in rows:
                f=row.split();b=int(f[0]);n=donor[b]
                regions.append(0 if ('Head' in n or 'Neck' in n) else 2 if ('Leg' in n or 'Foot' in n or 'Pelvis' in n) else 1)
                p=transforms[b]@np.array(list(map(float,f[1:4]))+[1.]);norm=transforms[b][:3,:3]@np.array(list(map(float,f[4:7])))
                new.append(f'{mapping[b]} '+' '.join(f'{v:.6f}' for v in [*p[:3],*norm,float(f[7]),float(f[8])]))
            group=max(set(regions),key=lambda r:(regions.count(r),r))
            material=f'{name}_{mat}';shutil.copy2(folder/mat,OUT/material)
            groups[group].append((material,new))
        counts[name]=[len(g) for g in groups]
        for group,tri in enumerate(groups):
            assert tri
            write_smd(OUT/f'operator_{group}_{variant}.smd',header,tri)
            parts.append((group,variant,tri))
    # Keep the original Soldier animation set and compatible bone controllers.
    for f in base.glob('*.smd'):
        if f.name!=ref.name:shutil.copy2(f,OUT/f.name)
    qc=(base/'soldier2.qc').read_text().replace('$modelname "soldier2.mdl"','$modelname "vf_operator.mdl"')
    groups='\n'.join('$bodygroup '+label+'\n{\n'+''.join(f' studio "operator_{g}_{v}"\n' for v in range(3))+'}' for g,label in enumerate(['head','torso','legs']))
    qc=re.sub(r'\$body "[^"]+" "[^"]+"',lambda m:groups,qc)
    qc='\n'.join(l for l in qc.splitlines() if not l.startswith(('$cliptotextures','$flags','$texrendermode')))+'\n'
    (OUT/'vf_operator.qc').write_text(qc);mdl=compile_model(OUT/'vf_operator.qc')
    _,_,idle=skeleton(base/'look_idle.smd')
    posed={b:idle[b]@np.linalg.inv(target[b]) for b in target}
    preview=export_preview('operator',parts,posed)
    return {'source_classes':['soldier2','hvyweapon2','scout2'],'parts_triangles':counts,'combinations':27,'model':str(mdl),'preview':preview,'limits':'Rough bone-based seams; fingers without exact matching bone are attached to nearest common ancestor.'}

def cylinder(center,radius,width,bone,material,axis=0,sides=20):
    """A capped low-poly attachment, with genuine editable geometry."""
    c=np.array(center);tri=[];other=[a for a in range(3) if a!=axis]
    rings=[]
    for end in [-1,1]:
        ring=[]
        for j in range(sides):
            ang=j*2*math.pi/sides;p=c.copy();p[axis]+=end*width/2;p[other[0]]+=radius*math.cos(ang);p[other[1]]+=radius*math.sin(ang)
            n=np.zeros(3);n[other[0]]=math.cos(ang);n[other[1]]=math.sin(ang)
            ring.append((p,n,j/sides,(end+1)/2))
        rings.append(ring)
    def row(v):
        p,n,u,w=v;return str(bone)+' '+' '.join(f'{x:.6f}' for x in [*p,*n,u,w])
    def emit(verts):
        normal=sum((v[1] for v in verts),np.zeros(3))
        if np.dot(np.cross(verts[1][0]-verts[0][0],verts[2][0]-verts[0][0]),normal)<0:
            verts=[verts[0],verts[2],verts[1]]
        tri.append((material,list(map(row,verts))))
    for i in range(sides):
        j=(i+1)%sides
        for verts in [[rings[0][i],rings[1][i],rings[1][j]],[rings[0][i],rings[1][j],rings[0][j]]]:emit(verts)
        for end in [0,1]:
            p=c.copy();p[axis]+=(end*2-1)*width/2;n=np.zeros(3);n[axis]=end*2-1
            verts=[(p,n,.5,.5)]
            for k in [i,j]:
                pos=rings[end][k][0]
                verts.append((pos,n,.5+(pos[other[0]]-c[other[0]])/(radius*2),.5+(pos[other[1]]-c[other[1]])/(radius*2)))
            emit(verts)
    return tri

def weapon():
    folder=PROJECT/'weapon-lab/generated/hk416'
    for f in folder.iterdir():
        if f.is_file():shutil.copy2(f,OUT/f.name)
    header,nodes,tri=read_smd(folder/'HK416_3.smd')
    original=[t for t in tri if t[0]=='mag.bmp'];remaining=[t for t in tri if t[0]!='mag.bmp']
    write_smd(OUT/'HK416_3.smd',header,remaining)
    write_smd(OUT/'mag_standard.smd',header,original)
    _,_,bind=skeleton(folder/'HK416_3.smd')
    mag=next(b for b,n in nodes.items() if n=='M16A2_MAG');spare=next(b for b,n in nodes.items() if n=='M16A2_MAG01')
    center=np.array([-3.63,-12.0,-11.0]);drum=cylinder(center,3.5,4.7,mag,'mag.bmp')
    delta=bind[spare][:3,3]-bind[mag][:3,3]
    drum+=cylinder(center+delta,3.5,4.7,spare,'mag.bmp')
    # Keep the upper insertion throat, so the drum joins the receiver cleanly.
    for material,rows in original:
        b=int(rows[0].split()[0]);local_z=[float(r.split()[3])-(delta[2] if b==spare else 0) for r in rows]
        if sum(local_z)/3>-8.8:drum.append((material,rows))
    write_smd(OUT/'mag_drum.smd',header,drum)
    root=next(b for b,n in nodes.items() if n=='M16A2')
    suppressor=cylinder([-3.63,-34.4,-3.55],1.0,7.5,root,'forerail.bmp',axis=1)
    write_smd(OUT/'muzzle_suppressor.smd',header,suppressor)
    qc=(folder/'v_9mmar.qc').read_text()
    qc=qc.replace('$body "studio" "HK416_3"','$body "studio" "HK416_3"\n$bodygroup magazine\n{\n studio "mag_standard"\n studio "mag_drum"\n}\n$bodygroup muzzle\n{\n blank\n studio "muzzle_suppressor"\n}')
    qc='\n'.join(l for l in qc.splitlines() if not l.startswith(('$cliptotextures','$flags','$texrendermode')))+'\n'
    (OUT/'v_9mmar.qc').write_text(qc);mdl=compile_model(OUT/'v_9mmar.qc')
    pieces=[]
    for name in ['HK416_1','HK416_2','HK416_3','HK416_4','M203']:
        _,_,ts=read_smd(OUT/(name+'.smd'));pieces.append((-1,0,ts))
    for variant,ts in enumerate([original,drum]):
        live=[(m,rows) for m,rows in ts if all(int(r.split()[0])!=spare for r in rows)]
        pieces.append((0,variant,live))
    pieces.append((1,1,suppressor))
    preview=export_preview('rifle',pieces)
    return {'model':str(mdl),'combinations':4,'magazines':['HK416 standard','procedural drum'],'muzzle':['stock','long attachment'],'preview':preview}

if __name__=='__main__':
    prepare_inputs()
    report={'operator':character(),'weapon':weapon()}
    (OUT/'build-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
