"""Compile authored atmospheric paintings into one seamless six-face sky and RGBA sprites."""
import argparse,hashlib,json,math,shutil,struct
from pathlib import Path
import numpy as np
from PIL import Image
import build_cache
ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/'assets/atmosphere'
OUT=ROOT/'generated/atmosphere'
SIZE=2048
# Matches Xash ref/gl/gl_warp.c st_to_vec and native sky texture order.
AXES={'rt':(3,-1,2),'lf':(-3,1,2),'bk':(1,3,2),'ft':(-1,-3,2),'up':(-2,-1,3),'dn':(2,-1,-3)}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def sample(panorama,x,y,z):
    length=np.sqrt(x*x+y*y+z*z)
    px=(np.arctan2(y,x)/(2*np.pi)+.5)*panorama.shape[1]
    py=(.5-np.arcsin(z/length)/np.pi)*(panorama.shape[0]-1)
    ix=np.floor(px).astype(np.int32);iy=np.floor(py).astype(np.int32)
    fx=(px-ix)[...,None];fy=(py-iy)[...,None]
    a=panorama[iy,ix%panorama.shape[1]]
    b=panorama[iy,(ix+1)%panorama.shape[1]]
    c=panorama[np.minimum(iy+1,panorama.shape[0]-1),ix%panorama.shape[1]]
    d=panorama[np.minimum(iy+1,panorama.shape[0]-1),(ix+1)%panorama.shape[1]]
    return (a*(1-fx)*(1-fy)+b*fx*(1-fy)+c*(1-fx)*fy+d*fx*fy)
def polar_sample(image,u,v):
    px=np.clip(u,0,1)*(image.shape[1]-1);py=np.clip(v,0,1)*(image.shape[0]-1)
    ix=np.floor(px).astype(np.int32);iy=np.floor(py).astype(np.int32)
    fx=(px-ix)[...,None];fy=(py-iy)[...,None]
    jx=np.minimum(ix+1,image.shape[1]-1);jy=np.minimum(iy+1,image.shape[0]-1)
    return image[iy,ix]*(1-fx)*(1-fy)+image[iy,jx]*fx*(1-fy)+image[jy,ix]*(1-fx)*fy+image[jy,jx]*fx*fy
def projection(panorama,axes,size=SIZE,caps=None):
    image=np.empty((size,size,3),np.uint8)
    s=np.linspace(-1,1,size,dtype=np.float32)[None,:]
    for first in range(0,size,128):
        t=np.linspace(1,-1,size,dtype=np.float32)[first:first+128,None]
        b=[np.broadcast_to(s,(len(t),size)),np.broadcast_to(t,(len(t),size)),np.ones((len(t),size),np.float32)]
        v=[b[abs(k)-1]*(1 if k>0 else -1)for k in axes]
        pixels=sample(panorama,*v)
        if caps:
            x,y,z=v;absolute=np.maximum(np.abs(z),.0001)
            ratio=np.maximum(np.abs(x),np.abs(y))/absolute
            weight=(.5+.5*np.cos(np.clip((ratio-.65)/.55,0,1)*np.pi))[...,None]
            # One directional field is sampled for ALL faces, preserving every cube seam.
            for sign,painting in caps.items():
                mask=weight*(z*sign>0)[...,None]
                polar=polar_sample(painting,.5-y/(absolute*2),.5+sign*x/(absolute*2))
                pixels=pixels*(1-mask)+polar*mask
        image[first:first+len(t)]=np.clip(np.rint(pixels),0,255).astype(np.uint8)
    return Image.fromarray(image)
def periodic_source(painting):
    # Projection conditioning only: narrow wrap/pole filter. Original artwork is preserved.
    a=np.asarray(painting.convert('RGB'),dtype=np.float32).copy()
    band=max(8,a.shape[1]//48)
    edge=(a[:,0]+a[:,-1])*.5
    for i in range(band):
        weight=.5+.5*math.cos(math.pi*i/band)
        a[:,i]=a[:,i]*(1-weight)+edge*weight
        a[:,-1-i]=a[:,-1-i]*(1-weight)+edge*weight
    cap=max(4,a.shape[0]//60)
    for pole in(0,-1):
        color=a[pole].mean(axis=0)
        for i in range(cap):
            row=i if pole==0 else -1-i
            weight=.5+.5*math.cos(math.pi*i/cap)
            a[row]=a[row]*(1-weight)+color*weight
    return a
def sprite(path,images):
    images=images if isinstance(images,list)else[images]
    w,h=images[0].size
    header=struct.pack('<4siifiiifi',b'IDSP',32,2,math.hypot(w,h)/2,w,h,len(images),0.,0)
    path.write_bytes(header+b''.join(struct.pack('<iiiii',0,-w//2,h//2,w,h)+image.convert('RGBA').tobytes()for image in images))
def build(ensure=False):
    fingerprint=build_cache.fingerprint([Path(__file__),Path(build_cache.__file__),*[ASSETS/p for p in('storm-panorama.png','cloud-bank.png','nadir.png','zenith.png')]])
    manifest=OUT/'manifest.json'
    if ensure and build_cache.current(build_cache.read(manifest).get('cache'),fingerprint):return OUT
    OUT.mkdir(parents=True,exist_ok=True);env=OUT/'gfx/env';env.mkdir(parents=True,exist_ok=True)
    sprites=OUT/'sprites';sprites.mkdir(exist_ok=True)
    source=Image.open(ASSETS/'storm-panorama.png');panorama=periodic_source(source)
    caps={sign:np.asarray(Image.open(ASSETS/name).convert('RGB'),dtype=np.float32)for sign,name in[(-1,'nadir.png'),(1,'zenith.png')]}
    outputs=[];faces=[]
    for suffix,axes in AXES.items():
        face=projection(panorama,axes,caps=caps);p=env/('vf_storm'+suffix+'.tga');face.save(p);outputs.append(p)
        faces.append(dict(suffix=suffix,axes=axes,size=face.size,sha256=sha(p)))
    deck=Image.open(ASSETS/'nadir.png').resize((1024,1024),Image.Resampling.LANCZOS).convert('RGBA')
    # Coverage is compiled instead of vertex alpha, which the installed TriAPI ignores.
    xy=np.linspace(-1,1,1024);x,y=np.meshgrid(xy,xy)
    fade=np.clip((1-np.sqrt(x*x+y*y))/.45,0,1);fade=fade*fade*(3-2*fade)
    deck.putalpha(Image.fromarray(np.rint(fade*255*.12).astype(np.uint8)))
    cloud=Image.open(ASSETS/'cloud-bank.png');assert cloud.mode=='RGBA','Authored cloud must have native alpha'
    # A transparent sampling gutter prevents clamp fringes. No repainting.
    frame=Image.new('RGBA',(1024,1024))
    fitted=cloud.resize((992,992),Image.Resampling.LANCZOS)
    frame.paste(fitted,(16,16))
    cloud_frames=[]
    for opacity in(.03,.08,.16,.25,.4,.55,.75,1.):
        variant=frame.copy();variant.putalpha(frame.getchannel('A').point(lambda a:round(a*opacity)));cloud_frames.append(variant)
    for name,image in [('cloud',cloud_frames),('deck',deck),('white',Image.new('RGBA',(8,8),(255,255,255,255)))]:
        p=sprites/(name+'.spr');sprite(p,image);outputs.append(p)
    state=dict(version=2,skyname='vf_storm',face_size=SIZE,faces=faces,
        source_size=source.size,cloud_source_size=cloud.size,originals={p.name:sha(p)for p in ASSETS.glob('*.png')},
        polar_source_sizes={name:Image.open(ASSETS/name).size for name in('nadir.png','zenith.png')},
        projection='Spherical panorama and two authored polar camera views, sampled as one continuous directional field; axes follow native renderer. 2048 faces resampled from authored source.',
        cloud_format='Xash native version-32 RGBA; eight precompiled opacity levels (RGB unchanged, authored soft alpha scaled); radial feather encoded in deck coverage; 1024 cloud/deck',
        cache=build_cache.record(fingerprint,outputs))
    manifest.write_text(json.dumps(state,indent=2)+'\n')
    print('PASS sky assets: six 2048 faces, three native RGBA textures',flush=True)
    return OUT
def runtime_files(folder=OUT):
    folder=Path(folder)
    state=json.loads((folder/'manifest.json').read_text())
    files=[(folder/'manifest.json',Path('vf/atmosphere.json'))]
    files +=[(folder/'gfx/env'/('vf_storm'+s+'.tga'),Path('gfx/env')/('vf_storm'+s+'.tga'))for s in AXES]
    files +=[(folder/'sprites'/(name+'.spr'),Path('sprites/vf_atmosphere')/(name+'.spr'))for name in('cloud','deck','white')]
    for source,target in files:
        if source.name!='manifest.json':assert sha(source)==state['cache']['outputs'][str(source.resolve())],source
    return files
def deploy(mod):
    build(ensure=True)
    for source,target in runtime_files():
        target=Path(mod)/target;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists()and sha(target)==sha(source):continue
        if target.is_file()and target.stat().st_nlink>1:target.unlink()
        shutil.copy2(source,target)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--ensure',action='store_true');build(p.parse_args().ensure)

