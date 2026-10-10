"""Validate native custom decal resources, authored animation and clear aim area."""
import hashlib, json, struct
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]

def run():
    config=json.loads((ROOT/'data/status_decals.json').read_text())
    entries=config['effects'];effects=json.loads((ROOT/'data/effects.json').read_text())['effects']
    assert [e['id'] for e in entries]==[e['id'] for e in effects if e['kind']<2]
    manifest=json.loads((ROOT/'generated/status-decals/manifest.json').read_text())
    assert (manifest['sprites'],manifest['frames'],manifest['size'])==(16,64,512)
    for file,digest in manifest['cache']['outputs'].items():assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==digest,file
    whole=[]
    for entry in entries:
        frames=[]
        name=entry['id']+'.spr'
        raw=(ROOT/'generated/status-decals'/name).read_bytes()
        magic,version,kind,radius,w,h,n,beam,sync=struct.unpack_from('<4siifiiifi',raw)
        assert (magic,version,kind,w,h,n)==(b'IDSP',32,2,512,512,4),name
        offset=36;digests=[]
        for f in range(n):
            frame_type,x,y,fw,fh=struct.unpack_from('<iiiii',raw,offset);offset+=20
            assert (frame_type,x,y,fw,fh)==(0,-256,256,512,512)
            pixels=raw[offset:offset+w*h*4];offset+=w*h*4
            assert len(pixels)==w*h*4,name
            rgba=Image.frombytes('RGBA',(w,h),pixels);image=rgba.getchannel('A')
            assert image.getextrema()[0]==0 and image.getextrema()[1]>100,name
            assert image.crop((72,72,440,440)).getextrema()==(0,0),(name,f,'aim region')
            strips=[(0,0,60,512),(452,0,512,512),(60,0,452,60),(60,452,452,512)]
            for rect in strips:assert image.crop(rect).getextrema()[1]>30,(name,f,rect)
            digests.append(hashlib.sha256(pixels).hexdigest())
            original=Image.open(ROOT/'assets/status-feedback/decals/frames'/(entry['id']+'-'+str(f)+'.png'))
            assert rgba.tobytes()==original.tobytes(),(name,'original RGB and opacity preserved')
        assert offset==len(raw) and len(set(digests))==4,(name,'distinct authored frames')
        whole.append(hashlib.sha256(raw).hexdigest())
        for f in range(4):
            rgba=Image.open(ROOT/'assets/status-feedback/decals/frames'/(entry['id']+'-'+str(f)+'.png'))
            assert rgba.mode=='RGBA' and rgba.size==(512,512)
            assert rgba.getchannel('A').crop((72,72,440,440)).getextrema()==(0,0)
    assert len(set(whole))==16,'All effects require their own art'
    report=dict(effects=16,authored_frames=64,native_sprites=16,checks=['all elemental and reaction IDs covered in catalog order','16 native RGBA sprite buffers and 64 distinct authored frames','all 4 peripheral sides populated; center exactly transparent','reaction colors and original alpha preserved exactly in native RGBA','source and generated output SHA256 contracts'])
    (ROOT/'build/status-decals-assets-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS custom HUD decals:',report)
    return report
if __name__=='__main__':run()
