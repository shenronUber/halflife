"""Validate actual sky edges/corners and native alpha, independent of the draw implementation."""
import json,struct,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from build_atmosphere import AXES,OUT,build
def run():
    build(ensure=True);state=json.loads((OUT/'manifest.json').read_text())
    edges={};corners={}
    for suffix,axes in AXES.items():
        image=np.asarray(Image.open(OUT/'gfx/env'/('vf_storm'+suffix+'.tga')).convert('RGB'))
        assert image.shape==(2048,2048,3)
        def direction(s,t):
            b=(s,t,1);return tuple(b[abs(k)-1]*(1 if k>0 else -1)for k in axes)
        for s,t,pixel in[(-1,1,image[0,0]),(1,1,image[0,-1]),(-1,-1,image[-1,0]),(1,-1,image[-1,-1])]:
            corners.setdefault(direction(s,t),[]).append(pixel)
        for start,end,pixels in[
            ((-1,1),(1,1),image[0]),((-1,-1),(1,-1),image[-1]),
            ((-1,1),(-1,-1),image[:,0]),((1,1),(1,-1),image[:,-1])]:
            a,b=direction(*start),direction(*end);key=tuple(sorted((a,b)))
            if key[0]!=a:pixels=pixels[::-1]
            edges.setdefault(key,[]).append(pixels)
    differences=[]
    for key,pair in edges.items():
        assert len(pair)==2,(key,len(pair))
        diff=np.abs(pair[0].astype(int)-pair[1].astype(int));differences.append(int(diff.max()))
        assert diff.max()<=2,('Visible cube seam',key,int(diff.max()))
    assert len(edges)==12 and len(corners)==8
    assert all(len(pixels)==3 and np.max(np.abs(np.asarray(pixels,dtype=int)-pixels[0]))<=2 for pixels in corners.values())
    for name,size in [('cloud',(1024,1024)),('deck',(1024,1024)),('white',(8,8))]:
        data=(OUT/'sprites'/(name+'.spr')).read_bytes()
        ident,version,kind,radius,w,h,count,beam,sync=struct.unpack_from('<4siifiiifi',data)
        assert (ident,version,count,w,h)==(b'IDSP',32,8 if name=='cloud'else 1,*size)
        offset=36+(count-1)*(20+w*h*4)+20
        pixels=np.frombuffer(data[offset:offset+w*h*4],dtype=np.uint8).reshape(h,w,4)
        if name=='cloud':
            alpha=pixels[:,:,3];assert alpha.min()==0 and alpha.max()==255
            assert not alpha[:16].any()and not alpha[-16:].any()and not alpha[:,:16].any()and not alpha[:,-16:].any()
            assert pixels[:,:,0].std()>20 and len(np.unique(alpha))>200
            previous=None
            for frame in range(count):
                start=36+frame*(20+w*h*4)+20
                current=np.frombuffer(data[start:start+w*h*4],dtype=np.uint8).reshape(h,w,4)
                assert np.array_equal(current[:,:,:3],pixels[:,:,:3]),'Opacity frames must preserve authored RGB'
                if previous is not None:assert np.all(current[:,:,3]>=previous)
                previous=current[:,:,3]
        if name=='deck':
            alpha=pixels[:,:,3]
            assert 20<=alpha.max()<=32 and not alpha[0].any()and not alpha[-1].any()and not alpha[:,0].any()and not alpha[:,-1].any()
    print('PASS sky: 12 seamless edges, 8 corners, six 2048 faces, soft native RGBA alpha',flush=True)
if __name__=='__main__':run()

