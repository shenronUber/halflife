"""Read installed GoldSrc MDL v10 geometry without changing source assets."""
import math,re,struct
from pathlib import Path
import numpy as np

def transform(values):
 x,y,z,rx,ry,rz=values;cx,sx=math.cos(rx),math.sin(rx);cy,sy=math.cos(ry),math.sin(ry);cz,sz=math.cos(rz),math.sin(rz)
 m=np.eye(4);m[:3,:3]=[[cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx],[sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx],[-sy,cy*sx,cy*cx]];m[:3,3]=[x,y,z];return m

def canonical(name):
 s=re.sub(r'^bip\d*\s*','',name.lower()).strip()
 for a,b in [('clavicle','arm'),('upperarm','arm1'),('forearm','arm2'),('thigh','leg'),('calf','leg1')]:s=s.replace(a,b)
 return s or 'root'

class Studio:
 def __init__(self,path):
  self.path=Path(path);self.data=d=self.path.read_bytes();assert d[:4]==b'IDST' and struct.unpack_from('<i',d,4)[0]==10
  self.names=[];self.parents=[];self.bind=[]
  count,off=struct.unpack_from('<ii',d,140)
  for i in range(count):
   name,parent,flags,*v=struct.unpack_from('<32sii6i12f',d,off+112*i);self.names.append(name.split(b'\0')[0].decode('latin1'));self.parents.append(parent)
   m=transform(v[6:12]);self.bind.append(self.bind[parent]@m if parent>=0 else m)
  self.parts=[];count,off=struct.unpack_from('<ii',d,204)
  for i in range(count):
   name,n,base,index=struct.unpack_from('<64siii',d,off+76*i)
   self.parts.append((name.split(b'\0')[0].decode('latin1'),n,index))
  self.textures=[];nt,ti=struct.unpack_from('<ii',d,180);td=d
  if not nt:
   tp=self.path.with_name(self.path.stem+'t.mdl')
   if not tp.exists():tp=self.path.with_name(self.path.stem+'T.mdl')
   if tp.exists():td=tp.read_bytes();nt,ti=struct.unpack_from('<ii',td,180)
  for i in range(nt):
   name,flags,w,h,p=struct.unpack_from('<64s4i',td,ti+i*80)
   self.textures.append((name.split(b'\0')[0].decode('latin1'),w,h,td[p:p+w*h],td[p+w*h:p+w*h+768]))
  ns,nf,si=struct.unpack_from('<iii',td,192);self.numskinref=ns;self.numskinfamilies=nf;self.skin=list(struct.unpack_from('<'+'h'*(ns*nf),td,si)) if ns else []
  count,off=struct.unpack_from('<ii',d,164)
  self.sequences=[d[off+i*176:off+i*176+32].split(b'\0')[0].decode('latin1') for i in range(count)]
 def mesh(self,choices=None,target=None,mapping=None,skin=0):
  d=self.data;result=[];selected=skin
  assert 0<=selected<max(1,self.numskinfamilies)
  for k,(label,n,off) in enumerate(self.parts):
   index=(choices or {}).get(k,0)
   if index<0:continue
   if target is not None and any(t in label.lower() for t in ['gun','weapon']):
    blanks=[j for j in range(n) if struct.unpack_from('<i',d,off+112*j+80)[0]==0]
    if blanks:index=blanks[0]
   q=off+112*index
   _,_,_,nm,mi,nv,vi,v,nn,ni,no=struct.unpack_from('<64sif8i',d,q)
   for j in range(nm):
    _,idx,skin,_,_=struct.unpack_from('<5i',d,mi+20*j);tex=self.skin[skin + selected*self.numskinref] if self.skin else skin
    if tex>=len(self.textures):continue
    _,w,h,_,_=self.textures[tex]
    while True:
     num=struct.unpack_from('<h',d,idx)[0];idx+=2
     if not num:break
     rows=[]
     for a in range(abs(num)):
      vertex,normal,u,uv=struct.unpack_from('<4h',d,idx);idx+=8
      assert 0<=vertex<nv and 0<=normal<nn
      bone=d[vi+vertex];nb=d[ni+normal]
      p=np.array(struct.unpack_from('<3f',d,v+12*vertex)+ (1.,));norm=np.array(struct.unpack_from('<3f',d,no+12*normal))
      source=self.bind[bone]@p
      if target is None:pos=source[:3];norm=self.bind[nb][:3,:3]@norm;outbone=bone
      else:
       ancestor,outbone=mapping[bone];na,nt=mapping[nb]
       mat=target[outbone]@np.linalg.inv(self.bind[ancestor]);pos=(mat@source)[:3]
       norm=(target[nt]@np.linalg.inv(self.bind[na]))[:3,:3]@self.bind[nb][:3,:3]@norm
      rows.append({'p':pos,'n':norm,'uv':np.array([u/w,1-uv/h]),'b':outbone,'source':source[:3]})
     for a in range(2,len(rows)):
      ids=[0,a-1,a] if num<0 else ([a-2,a-1,a] if a%2==0 else [a-1,a-2,a])
      # MDL strip/fan winding is opposite to the SMD triangle convention.
      # Preserve outward faces when recompiling, including at UV seams.
      result.append((tex,[dict(rows[t]) for t in reversed(ids)]))
  return result
 def write_textures(self,folder,prefix):
  folder.mkdir(parents=True,exist_ok=True);names=[]
  for i,(_,w,h,pixels,palette) in enumerate(self.textures):
   name=f'{prefix}_{i}.bmp';stride=(w+3)&~3;offset=1078
   pal=b''.join(bytes([palette[j*3+2],palette[j*3+1],palette[j*3],0]) for j in range(256))
   raw=b''.join(pixels[j*w:(j+1)*w]+bytes(stride-w) for j in range(h-1,-1,-1))
   bmp=struct.pack('<2sIHHI',b'BM',offset+len(raw),0,0,offset)+struct.pack('<IiiHHIIiiII',40,w,h,1,8,0,len(raw),0,0,256,256)+pal+raw
   (folder/name).write_bytes(bmp);names.append(name)
  return names
