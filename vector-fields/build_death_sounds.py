"""Generate and package separate positional death / detachment sound layers.

Default build and --ensure are offline. Only --generate contacts ElevenLabs;
its existing DPAPI workshop retains request provenance and uncertain markers.
"""
from __future__ import annotations
import argparse,array,hashlib,html,json,math,shutil,sys,wave
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import audio_workshop as audio
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/death_sounds.json'
MASTERS=ROOT/'assets/audio/death-sfx'
OUT=ROOT/'generated/death-sfx'
HEADER=ROOT.parent/'game_shared/vf_death_sfx_catalog.h'
ENDPOINT='/v1/sound-generation?output_format=mp3_44100_128'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def recipe():
    data=json.loads(DATA.read_text(encoding='utf-8-sig'))
    atlas=json.loads((ROOT/'assets/animations/death-atlas.json').read_text(encoding='utf-8'))
    assert [p['id'] for p in data['profiles']]==['standard']+[p['effect'] for p in atlas['profiles']]
    assert len(data['profiles'])==17
    return data

def items(data):
    for p in data['profiles']:
        for layer in ('death','dismemberment'):
            if layer not in p:continue
            r=p[layer]
            yield dict(id=layer+'_'+p['id'],name=p['name']+' / '+layer,profile=p,layer=layer,recipe=r),dict(text=r['prompt'],duration_seconds=r['seconds'],prompt_influence=.65,loop=False,model_id='eleven_text_to_sound_v2')

def generate(data):
    audio.ASSETS=MASTERS
    # One listening page is written by build after the two workers have joined.
    audio.preview=lambda:None
    key=audio.load_key();quota=audio.status(key)
    if quota.get('character_limit') and quota.get('character_count',0)>=quota['character_limit']:
        raise RuntimeError('Included quota exhausted; no generation requested.')
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(audio.generate_one,key,'sfx',item,request,ENDPOINT) for item,request in items(data)]
        for job in as_completed(jobs):job.result()
    audio.status(key)

def export(source,target,layer):
    # Masters were trimmed by the workshop. Reserve mix headroom for the cry,
    # death cause and a detachment playing simultaneously on native channels.
    with wave.open(str(source),'rb') as w:
        assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,22050,2)
        samples=array.array('h',w.readframes(w.getnframes()))
    if sys.byteorder!='little':samples.byteswap()
    peak=max(abs(s) for s in samples)/32768
    rms=math.sqrt(sum((s/32768)**2 for s in samples)/len(samples))
    if peak<.01 or rms<.002:raise ValueError('Silent generated candidate: '+str(source))
    gain=min((.18 if layer=='death' else .20)/peak,(.060 if layer=='death' else .070)/rms)
    fade_in,fade_out=110,551
    values=array.array('h',(round(s*gain*min(1,i/fade_in,(len(samples)-1-i)/fade_out)) for i,s in enumerate(samples)))
    if sys.byteorder!='little':values.byteswap()
    target.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(target),'wb') as w:
        w.setparams((1,2,22050,0,'NONE','not compressed'));w.writeframes(values.tobytes())
    with wave.open(str(target),'rb') as w:count=w.getnframes()
    return dict(duration=round(count/22050,6),peak=round(max(abs(s) for s in values)/32768,6),rms=round(math.sqrt(sum((s/32768)**2 for s in values)/len(values)),6))

def catalog(clips):
    lookup={c['id']:c for c in clips}
    rows=['// Generated offline by vector-fields/build_death_sounds.py.','#ifndef VF_DEATH_SFX_CATALOG_H','#define VF_DEATH_SFX_CATALOG_H','namespace vfds {','struct Profile {const char* id;const char* death;const char* dismemberment;};','static const Profile Profiles[]={']
    for p in recipe()['profiles']:
        d=lookup.get('death_'+p['id']);m=lookup['dismemberment_'+p['id']]
        rows.append('{'+json.dumps(p['id'])+','+(json.dumps(d['path']) if d else '0')+','+json.dumps(m['path'])+'},')
    rows+=['};','enum {ProfileCount=sizeof(Profiles)/sizeof(Profiles[0])};','inline const Profile& For(int effect){return Profiles[effect>=0&&effect<ProfileCount-1?effect+1:0];}','}','#endif']
    return '\n'.join(rows)+'\n'

def listening_mix(profile,clips):
    """A mono listening example only; gameplay uses three native sound events."""
    voice=ROOT/'assets/audio/operator-deaths/rocco'/(profile['id']+'_v2.wav')
    if not voice.exists():return None
    paths=[(voice,.85,.015)]
    for layer in ('death','dismemberment'):
        c=clips.get(layer+'_'+profile['id'])
        if c:paths.append((OUT/'sound'/(c['id']+'.wav'),.8,0))
    result=[]
    for path,gain,delay in paths:
        with wave.open(str(path),'rb') as w:
            channels,width,rate,count=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes();raw=w.readframes(count)
        assert channels==1
        if width==1:values=[(v-128)/128 for v in raw]
        else:
            a=array.array('h',raw)
            if sys.byteorder!='little':a.byteswap()
            values=[v/32768 for v in a]
        n=round(len(values)*22050/rate);offset=round(delay*22050)
        if len(result)<offset+n:result.extend([0.]*(offset+n-len(result)))
        for i in range(n):
            pos=i*rate/22050;j=min(len(values)-1,int(pos));k=min(len(values)-1,j+1)
            result[offset+i]+=gain*(values[j]+(values[k]-values[j])*(pos-j))
    assert max(abs(v) for v in result)<1,'Listening mix clips'
    path=OUT/'mixes'/(profile['id']+'.wav');path.parent.mkdir(parents=True,exist_ok=True)
    pcm=array.array('h',(round(v*32767) for v in result))
    if sys.byteorder!='little':pcm.byteswap()
    with wave.open(str(path),'wb') as w:w.setparams((1,2,22050,0,'NONE','not compressed'));w.writeframes(pcm.tobytes())
    return path

def preview(data,clips):
    lookup={c['id']:c for c in clips}
    cards=[]
    for p in data['profiles']:
        cells=[]
        for layer,label in [('death','Mort elementaire'),('dismemberment','Arrachement')]:
            c=lookup.get(layer+'_'+p['id'])
            if c:
                cells.append('<div><b>'+label+'</b><p>'+html.escape(p[layer]['signature'])+'</p><audio controls preload="none" src="sound/'+c['id']+'.wav"></audio></div>')
            else:cells.append('<div><b>Mort sans effet</b><p>Cri habituel, sans signature elementaire.</p></div>')
        mix=listening_mix(p,lookup)
        extra=('<p>Mix d ecoute : cri de Rocco + cause + bras, sans spatialisation.</p><audio controls preload="none" src="mixes/'+p['id']+'.wav"></audio>') if mix else ''
        cards.append('<article><h2>'+html.escape(p['name'])+'</h2><section>'+''.join(cells)+'</section>'+extra+'</article>')
    document='<!doctype html><html lang="fr"><meta charset="utf-8"><title>Morts et demembrement - Vector Fields</title><style>body{background:#101c24;color:#eef7f9;font:16px system-ui;max-width:1000px;margin:36px auto;padding:16px}h1{color:#69d9c3}article{background:#1a2b35;padding:18px;margin:16px 0;border-radius:12px}section{display:grid;grid-template-columns:1fr 1fr;gap:20px}audio{width:100%}p{color:#b6cbd1;line-height:1.5}</style><h1>Morts et demembrement</h1><p>16 causes elementaires, 17 arrachements. En jeu : cri + mort + arrachement sont trois sons natifs distincts. Les fichiers ci-dessous permettent d ecouter chaque signature seule. F4 puis F8 pour les essayer en situation. Une seule salve d arrachement par evenement, meme si plusieurs membres partent ensemble.</p>'+''.join(cards)+'<script>document.addEventListener("play",e=>document.querySelectorAll("audio").forEach(a=>{if(a!==e.target)a.pause()}),true)</script></html>'
    (OUT/'listen.html').write_text(document,encoding='utf-8')

def build(ensure=False):
    data=recipe();input_hash=digest(DATA);manifest_path=OUT/'manifest.json'
    if ensure and manifest_path.exists():
        old=json.loads(manifest_path.read_text(encoding='utf-8'))
        valid=old.get('recipe_sha256')==input_hash and len(old['clips'])==33
        valid=valid and all((OUT/'sound'/(c['id']+'.wav')).is_file() and digest(OUT/'sound'/(c['id']+'.wav'))==c['sha256'] and (MASTERS/'shots'/(c['id']+'.mp3')).is_file() and digest(MASTERS/'shots'/(c['id']+'.mp3'))==c['source_sha256'] for c in old['clips'])
        if valid and HEADER.exists() and HEADER.read_text()==catalog(old['clips']):
            preview(data,old['clips']);return old
    clips=[]
    for item,request in items(data):
        id=item['id'];source=MASTERS/'shots'/(id+'.mp3');meta=source.with_suffix('.json');wav=source.with_suffix('.wav')
        if not source.is_file() or not meta.is_file() or not wav.is_file():raise FileNotFoundError('Missing generated candidate '+id+'. Run --generate once; offline build never spends credits.')
        provenance=json.loads(meta.read_text(encoding='utf-8'))
        if provenance['request']!=request or provenance['sha256']!=digest(source):raise ValueError('Generated source does not match recipe: '+id)
        stats=export(wav,OUT/'sound'/(id+'.wav'),item['layer'])
        clips.append(dict(id=id,effect=item['profile']['id'],layer=item['layer'],path='vf_death_sfx/'+id+'.wav',sha256=digest(OUT/'sound'/(id+'.wav')),source_sha256=digest(source),request_id=provenance.get('request_id'),**stats))
    manifest=dict(schema=1,provider='ElevenLabs eleven_text_to_sound_v2',recipe_sha256=input_hash,format='mono PCM 22050 Hz / 16 bit',clips=clips)
    audio.json_write(manifest_path,manifest);HEADER.write_text(catalog(clips),encoding='utf-8');preview(data,clips)
    print('Built death audio: 16 deaths + 17 detachments, '+str(sum((OUT/'sound'/(c['id']+'.wav')).stat().st_size for c in clips))+' bytes.',flush=True)
    return manifest

def deploy(destination):
    manifest=build(ensure=True);destination=Path(destination)
    for c in manifest['clips']:
        target=destination/'sound'/c['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OUT/'sound'/(c['id']+'.wav'),target)
    (destination/'vf').mkdir(parents=True,exist_ok=True);shutil.copy2(OUT/'manifest.json',destination/'vf/death-sfx-manifest.json')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--generate',action='store_true');p.add_argument('--ensure',action='store_true');a=p.parse_args()
    if a.generate:generate(recipe())
    build(ensure=a.ensure)
