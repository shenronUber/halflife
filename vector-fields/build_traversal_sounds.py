"""Original deterministic slide friction, timed from the movement contract.

No downloads or paid generation. No loop marker; PM_Move stops early exits.
--ensure preserves verified exports instead of building another audio bank.
"""
from __future__ import annotations
import argparse,hashlib,json,re,shutil,wave
from pathlib import Path
import numpy as np
from scipy.signal import butter,sosfilt

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'generated/traversal-sfx'
RATE=22050
SEED=291017
RECIPE=1

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def contract():
    header=(ROOT.parent/'game_shared/vf_traversal.h').read_text()
    duration=float(re.search(r'#define VF_TR_SLIDE_TIME\s+([\d.]+)f',header)[1])
    path=re.search(r'#define VF_TR_SLIDE_SOUND\s+"([^"]+)"',header)[1]
    return dict(recipe=RECIPE,seed=SEED,sample_rate=RATE,channels=1,sample_width=2,
                frames=round(duration*RATE),duration=duration,path=path)

def synthesize(spec):
    rng=np.random.default_rng(SEED);n=spec['frames'];t=np.arange(n)/RATE
    def noise(lo,hi):
        x=sosfilt(butter(3,[lo,hi],btype='bandpass',fs=RATE,output='sos'),rng.standard_normal(n))
        return x/max(1e-9,np.sqrt(np.mean(x*x)))
    # Cloth rubbing, floor grain and a soft low rush. Irregular swells avoid
    # the rhythm of footsteps and keep the cue distinct beneath gunfire.
    cloth=noise(220,1300);grain=noise(1700,6200);rush=noise(60,200)
    motion=sosfilt(butter(2,18,fs=RATE,output='sos'),rng.standard_normal(n))
    motion/=max(1e-9,np.std(motion));texture=np.clip(1+.14*motion,.5,1.5)
    x=(.65*cloth+.24*grain+.11*rush)*texture
    envelope=(1-.28*t/spec['duration'])*np.minimum(1,t/.022)*np.minimum(1,(spec['duration']-t)/.045)
    x*=envelope;x*=.38/max(1e-9,np.max(np.abs(x)));x[0]=x[-1]=0
    return np.rint(x*32767).astype('<i2')

def build(ensure=False):
    spec=contract();manifest_path=OUT/'manifest.json';path=OUT/Path(spec['path']).name
    if ensure and manifest_path.is_file() and path.is_file():
        old=json.loads(manifest_path.read_text())
        if old.get('contract')==spec and old['clips'][0]['sha256']==digest(path):return old
    OUT.mkdir(parents=True,exist_ok=True);pcm=synthesize(spec)
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(pcm.tobytes())
    x=pcm.astype(float)/32768
    clip=dict(path=spec['path'],duration=spec['frames']/RATE,frames=len(pcm),sha256=digest(path),
              peak=float(np.max(np.abs(x))),rms=float(np.sqrt(np.mean(x*x))))
    manifest=dict(contract=spec,format='PCM mono 16-bit 22050 Hz',
                  provenance='Original procedural cloth and floor friction; deterministic noise; no external samples.',
                  loop=False,clips=[clip])
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest

def deploy(destination):
    manifest=build(ensure=True);destination=Path(destination)
    for clip in manifest['clips']:
        target=destination/'sound'/clip['path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(OUT/Path(clip['path']).name,target)
    target=destination/'vf/traversal-sfx-manifest.json';target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(OUT/'manifest.json',target)
    return manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ensure',action='store_true')
    args=parser.parse_args();manifest=build(ensure=args.ensure)
    print('Slide friction:',manifest['clips'][0]['duration'],'seconds;',manifest['format'])
