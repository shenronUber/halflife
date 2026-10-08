"""Losslessly pack preview textures into Xash SPR32 frame banks (HUD has 256 sprite slots)."""
import hashlib,json,math,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent/'generated/skins'

def read_frame(path,frame=0):
 d=path.read_bytes();assert d[:4]==b'IDSP';version=struct.unpack_from('<i',d,4)[0]
 if version==2:
  assert frame==0;palette=np.frombuffer(d[42:810],dtype=np.uint8).reshape(256,3);_,_,_,w,h=struct.unpack_from('<5i',d,810)
  rgb=palette[np.frombuffer(d[830:830+w*h],dtype=np.uint8)];rgba=np.concatenate([rgb,np.full((w*h,1),255,np.uint8)],axis=1).tobytes()
 elif version==32:
  pos=36
  for i in range(frame+1):
   _,_,_,w,h=struct.unpack_from('<5i',d,pos);pos+=20
   rgba=d[pos:pos+w*h*4];pos+=w*h*4
 else:raise ValueError(version)
 assert len(rgba)==w*h*4
 return w,h,rgba

def pack():
 records=json.loads((ROOT/'skins.json').read_text())['characters']+json.loads((ROOT/'arsenal.json').read_text())
 unique={};frames=[];files=[]
 for record in records:
  path=ROOT/(record['key']+'.vfm');data=bytearray(path.read_bytes());count=struct.unpack_from('<I',data,8)[0];refs=[]
  for i in range(count):
   name=data[16+i*96:16+(i+1)*96].split(b'\0')[0].decode();parts=name.split('#');frame=int(parts[1]) if len(parts)>1 else 0
   w,h,rgba=read_frame(ROOT/'sprites'/Path(parts[0]).name,frame);digest=hashlib.sha256(struct.pack('<ii',w,h)+rgba).digest()
   if digest not in unique:unique[digest]=len(frames);frames.append((w,h,rgba))
   refs.append(unique[digest])
  files.append((path,data,refs))
 # Read all inputs before replacing banks: repeated runs are safe and deterministic.
 for bank,start in enumerate(range(0,len(frames),64)):
  group=frames[start:start+64];mw=max(t[0] for t in group);mh=max(t[1] for t in group)
  data=struct.pack('<4siifiiifi',b'IDSP',32,2,math.hypot(mw,mh)/2,mw,mh,len(group),0.,0)
  for w,h,rgba in group:data+=struct.pack('<5i',0,-w//2,h//2,w,h)+rgba
  (ROOT/'sprites'/f'bank_{bank:02}.spr').write_bytes(data)
 for path,data,refs in files:
  for i,id in enumerate(refs):
   name=f'sprites/vf_preview/bank_{id//64:02}.spr#{id%64}'.encode();data[16+i*96:16+(i+1)*96]=name+bytes(96-len(name))
  path.write_bytes(data)
 result={'models':len(files),'unique_textures':len(frames),'sprite_slots':(len(frames)+63)//64,'format':'Xash SPR32, original palette colors expanded losslessly to RGBA'}
 (ROOT/'texture-banks.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':pack()
