"""Add a distal thumb joint while preserving every original animation and vertex."""
import hashlib,struct,os
from pathlib import Path
import numpy as np
from studio_assets import Studio
from animation_assets import sequence_info
NAME='VF_LThumbTip';PIVOT=np.array([2.1,0.,-.2]);CUT=3.45

def rle(data,start,frames):
    end=start;n=0
    while n<frames:
        valid,total=struct.unpack_from('<BB',data,end);assert 0<valid<=total
        n+=total;end+=2+valid*2
    return data[start:end]

def upgrade(path,target=None):
    path=Path(path);target=Path(target)if target else path;old=Studio(path)
    if NAME in old.names:
        if target!=path:target.write_bytes(old.data)
        return False
    if 'Bip01 L Finger0'not in old.names:return False
    parent=old.names.index('Bip01 L Finger0');n=len(old.names);assert n<128
    data=bytearray(old.data)
    def append(blob):
        while len(data)%4:data.append(0)
        off=len(data);data.extend(blob);return off
    boneoff=struct.unpack_from('<i',old.data,144)[0]
    bone=struct.pack('<32sii6i12f',NAME.encode().ljust(32,b'\0'),parent,0,*([-1]*6),*PIVOT,0,0,0,*([1/256]*3+[.0001]*3))
    newbones=append(old.data[boneoff:boneoff+112*n]+bone);struct.pack_into('<ii',data,140,n+1,newbones)
    count,seqoff=struct.unpack_from('<ii',old.data,164)
    descriptors=append(old.data[seqoff:seqoff+176*count]);struct.pack_into('<ii',data,164,count,descriptors)
    for index in range(count):
        info=sequence_info(old,index);assert info['group']==0
        headers=append(bytes(info['blends']*(n+1)*12));struct.pack_into('<i',data,descriptors+176*index+124,headers)
        chunks={}
        for blend in range(info['blends']):
            for b in range(n):
                source=info['animation']+(blend*n+b)*12;dest=headers+(blend*(n+1)+b)*12
                for axis,offset in enumerate(struct.unpack_from('<6H',old.data,source)):
                    if not offset:continue
                    start=source+offset
                    if start not in chunks:chunks[start]=append(rle(old.data,start,info['frames']))
                    offset=chunks[start]-dest;assert 0<offset<65536,(path,index,b,axis,offset)
                    struct.pack_into('<H',data,dest+axis*2,offset)
    # Assign distal vertices to the added bone. Rest local coordinates shift
    # by exactly the joint pivot, so all old poses keep identical geometry.
    seen=set()
    for _,models,off in old.parts:
        for model in range(models):
            q=off+112*model
            nm,mi,nv,vi,v,nn,ni,no=struct.unpack_from('<8i',old.data,q+72)
            if (vi,v)in seen:continue
            seen.add((vi,v));tip=set()
            for vertex in range(nv):
                if old.data[vi+vertex]!=parent:continue
                point=np.array(struct.unpack_from('<3f',old.data,v+12*vertex))
                if point[0]<CUT:continue
                tip.add(vertex);data[vi+vertex]=n;struct.pack_into('<3f',data,v+12*vertex,*(point-PIVOT))
            if not tip:continue
            duplicates={};normals=bytearray(old.data[no:no+12*nn]);normalbones=bytearray(old.data[ni:ni+nn])
            for mesh in range(nm):
                idx=struct.unpack_from('<i',old.data,mi+20*mesh+4)[0]
                while True:
                    num=struct.unpack_from('<h',old.data,idx)[0];idx+=2
                    if not num:break
                    for a in range(abs(num)):
                        entry=idx+8*a;vertex,normal=struct.unpack_from('<2h',old.data,entry)
                        if vertex not in tip or old.data[ni+normal]!=parent:continue
                        if normal not in duplicates:
                            duplicates[normal]=len(normalbones);normalbones.append(n);normals.extend(old.data[no+normal*12:no+normal*12+12])
                        struct.pack_into('<h',data,entry+2,duplicates[normal])
                    idx+=8*abs(num)
            newnormals=append(normals);newnormalbones=append(normalbones)
            struct.pack_into('<3i',data,q+92,len(normalbones),newnormalbones,newnormals)
    struct.pack_into('<i',data,72,len(data));target.parent.mkdir(parents=True,exist_ok=True)
    pending=target.with_name(target.name+'.thumb-next');pending.write_bytes(data);os.replace(pending,target)
    return True

def source_with_thumb(path):
    path=Path(path);model=Studio(path)
    if NAME in model.names or 'Bip01 L Finger0'not in model.names:return path
    key=hashlib.sha256(model.data+Path(__file__).read_bytes()).hexdigest()[:16]
    target=Path(__file__).resolve().parent/'build/fist-sources'/key/path.name
    if not target.exists():upgrade(path,target)
    return target
