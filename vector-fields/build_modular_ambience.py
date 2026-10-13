"""Quiet, long native WAV loops for the open modular arena."""
import argparse, hashlib, json, math, shutil, struct, wave
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt, resample_poly
import build_cache

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets/audio/modular-ambience'
OUT = ROOT / 'generated/modular-ambience'
RATE = 22050
CLIPS = [('wind', 34, .38), ('vortex', 47, .29), ('strain_a', 43, .48),
         ('strain_b', 59, .48), ('strain_c', 71, .48)]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def source(name):
    with wave.open(str(ASSETS / name), 'rb') as w:
        raw = w.readframes(w.getnframes())
        x = ((np.frombuffer(raw, np.uint8).astype(float)-128)/128 if w.getsampwidth()==1
             else np.frombuffer(raw, '<i2').astype(float)/32768)
        x = x.reshape(-1, w.getnchannels()).mean(axis=1)
        divisor = math.gcd(RATE, w.getframerate())
        x = resample_poly(x, RATE//divisor, w.getframerate()//divisor)
    return x

def periodic_noise(rng, n, lo, hi):
    f = np.fft.rfftfreq(n, 1/RATE)
    spectrum = np.fft.rfft(rng.normal(size=n))
    weights = (1-np.exp(-(f/max(lo, 1))**4))*np.exp(-(f/hi)**4)/np.sqrt(np.maximum(f, 1))
    x = np.fft.irfft(spectrum*weights, n)
    return x / max(np.std(x), 1e-9)

def synthesize(name, duration, peak):
    rng = np.random.default_rng(131026 + [c[0] for c in CLIPS].index(name))
    count = int(.45*RATE)
    n = duration*RATE+count; t = np.arange(n)/RATE
    if name in ('wind', 'vortex'):
        if name == 'wind':
            airy = periodic_noise(rng, n, 130, 2000)
            deep = periodic_noise(rng, n, 45, 230)
            detail = source('wind2.wav')
            detail = sosfilt(butter(2, [500, 2400], 'bandpass', fs=RATE, output='sos'), detail)
            detail /= max(np.std(detail), 1e-9)
            sampled = np.interp(np.mod(t*RATE*.91, len(detail)-1), np.arange(len(detail)), detail)
            gust = .68 + .18*np.sin(2*np.pi*t/duration) + .09*np.sin(6*np.pi*t/duration+.8)
            x = (.72*airy+.20*deep+.08*sampled)*gust
        else:
            gust = .70+.18*np.sin(4*np.pi*t/duration+.7)
            x = (.75*periodic_noise(rng,n,32,180)+.25*periodic_noise(rng,n,140,700))*gust
            x *= 1+.045*np.sin(2*np.pi*2.7*t)  # distant rotating air, no siren or scream
    else:
        x = np.zeros(n)
        index = ord(name[-1])-ord('a')
        events = [(7+index*3,.58,.8), (duration*.67,.66,.65)]
        for k,(start,speed,gain) in enumerate(events):
            donor = source('squeeks1.wav' if (k+index)%2==0 else 'doormove1.wav')
            event = np.interp(np.arange(0,len(donor)-1,speed),np.arange(len(donor)),donor)
            event = event[:int(4.6*RATE)]
            event = sosfilt(butter(3,[70,1800],'bandpass',fs=RATE,output='sos'),event)
            et = np.arange(len(event))/RATE
            # A low, decaying plate resonance gives the stock metal a larger body.
            envelope = np.minimum(et/.08,1)*np.minimum((et[-1]-et)/.35,1)
            resonance = sum(np.sin(2*np.pi*(f*et+2*np.sin(et*.7)))/(i+1)
                            for i,f in enumerate((53,91,137,211)))
            envelope = np.maximum(envelope,0)
            event = event + .018*resonance*np.exp(-et/2.1)
            event = (event-(event*envelope).sum()/max(envelope.sum(),1e-9))*envelope*gain
            begin = round(start*RATE); length = min(len(event),n-begin)
            x[begin:begin+length] += event[:length]
    # Crossfade the tail into the beginning, then start after that overlap.
    blend = np.linspace(0,1,count)
    x[-count:] = x[-count:]*(1-blend)+x[:count]*blend
    x = x[count:]
    if name in ('wind','vortex'):x -= x.mean()
    x *= peak/max(np.max(np.abs(x)),1e-9)
    x[-1] = x[0]
    return np.rint(x*32767).astype('<i2')

def wav_loop(path, pcm):
    def chunk(tag, data):
        return tag+struct.pack('<I',len(data))+data+(b'\0' if len(data)%2 else b'')
    fmt = struct.pack('<HHIIHH',1,1,RATE,RATE*2,2,16)
    cue = struct.pack('<III4sIII',1,1,0,b'data',0,0,0)
    body = b'WAVE'+chunk(b'fmt ',fmt)+chunk(b'cue ',cue)+chunk(b'data',pcm.tobytes())
    path.write_bytes(b'RIFF'+struct.pack('<I',len(body))+body)

def build(ensure=False):
    inputs = [Path(__file__),ROOT/'build_cache.py',*sorted(ASSETS.glob('*'))]
    fingerprint = build_cache.fingerprint(inputs)
    manifest = OUT/'manifest.json'
    if ensure and build_cache.current(build_cache.read(manifest).get('cache'),fingerprint):
        return build_cache.read(manifest)
    OUT.mkdir(parents=True,exist_ok=True); clips=[]; outputs=[]
    for name,duration,peak in CLIPS:
        pcm = synthesize(name,duration,peak); path = OUT/(name+'.wav'); wav_loop(path,pcm)
        x = pcm.astype(float)/32768
        clips.append(dict(id=name,path='vf_ambience/'+path.name,seconds=duration,frames=len(pcm),
                          loop_start=0,peak=float(abs(x).max()),rms=float(np.sqrt(np.mean(x*x))),sha256=sha(path)))
        outputs.append(path)
    state = dict(format='PCM mono 16-bit 22050 Hz; native cue loop at sample zero',clips=clips,
                 provenance=json.loads((ASSETS/'sources.json').read_text()),
                 intent='Low continuous air; filtered distant vortex; three sparse local structure strain cycles.',
                 cache=build_cache.record(fingerprint,outputs))
    manifest.write_text(json.dumps(state,indent=2)+'\n')
    return state

def runtime_files(folder=OUT):
    folder=Path(folder); state=json.loads((folder/'manifest.json').read_text())
    files=[(folder/'manifest.json',Path('vf/modular-ambience.json'))]
    for clip in state['clips']:
        path=folder/Path(clip['path']).name
        if sha(path)!=clip['sha256']:raise RuntimeError('Stale ambience export: '+str(path))
        files.append((path,Path('sound')/clip['path']))
    return files

def deploy(mod):
    build(ensure=True)
    for source,target in runtime_files():
        target=Path(mod)/target; target.parent.mkdir(parents=True,exist_ok=True)
        if target.is_file() and sha(target)==sha(source):continue
        if target.is_file() and target.stat().st_nlink>1:target.unlink()
        shutil.copy2(source,target)

def entities(geometry):
    rows=[dict(classname='ambient_generic',targetname='vf_air_wind',origin='0 0 256',
               message='vf_ambience/wind.wav',health='2',spawnflags='1',pitch='100'),
          dict(classname='ambient_generic',targetname='vf_air_vortex',origin='-2000 2000 600',
               message='vf_ambience/vortex.wav',health='.6',spawnflags='1',pitch='100')]
    half=geometry['extent']//2; pitch=geometry['cell']+geometry['gap']
    for c,name in zip((0,4,8),('strain_a','strain_b','strain_c')):
        x=-half+c%3*pitch+geometry['cell']//2
        y=-half+c//3*pitch+geometry['cell']//2-350
        rows.append(dict(classname='ambient_generic',targetname='vf_structure_'+name,
                         origin=f'{x} {y} 56',message='vf_ambience/'+name+'.wav',health='2.2',spawnflags='8',pitch='100'))
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--ensure',action='store_true'); build(p.parse_args().ensure)
