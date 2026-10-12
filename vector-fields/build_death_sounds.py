"""Generate and package separate positional death / detachment sound layers.

Default build and --ensure are offline. Only --generate contacts ElevenLabs;
its existing DPAPI workshop retains request provenance and uncertain markers.
"""
from __future__ import annotations
import argparse,array,hashlib,html,json,math,shutil,subprocess,sys,wave
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
        for layer in ('death','dismemberment','head'):
            if layer not in p:continue
            r=p[layer]
            yield dict(id=layer+'_'+p['id'],name=p['name']+' / '+layer,master_id=r.get('master_id',layer+'_'+p['id']),master_bank=r['master_bank'],profile=p,layer=layer,recipe=r),dict(text=r['prompt'],duration_seconds=r['seconds'],prompt_influence=.65,loop=False,model_id='eleven_text_to_sound_v2')

def master_folder(item):
    bank=item['master_bank']
    assert bank in ('original','natural-heads')
    return MASTERS if bank=='original' else MASTERS/bank

def generate(data):
    assert all(1<=len(request["text"])<=450 for _,request in items(data)), "SFX prompt must fit 450 characters."
    # One listening page is written by build after the two workers have joined.
    audio.preview=lambda:None
    key=audio.load_key();quota=audio.status(key)
    if quota.get('character_limit') and quota.get('character_count',0)>=quota['character_limit']:
        raise RuntimeError('Included quota exhausted; no generation requested.')
    # The workshop asset directory is global: finish each bank before switching.
    for bank in ('original','natural-heads'):
        entries=[(item,request) for item,request in items(data) if item['master_bank']==bank]
        audio.ASSETS=master_folder(entries[0][0])
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(audio.generate_one,key,'sfx',dict(item,id=item['master_id']),request,ENDPOINT) for item,request in entries]
            for job in as_completed(jobs):job.result()
    audio.status(key)

def export(source,target,layer):
    # Master loudness only. Keep every source frame at its original tempo:
    # no duration padding, tail retiming, looping or pitch-changing resampling.
    executable=audio.ffmpeg()
    if not executable:raise RuntimeError("FFmpeg is required for audio mastering.")
    with wave.open(str(source),"rb") as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,22050)
        source_frames=w.getnframes()
    raw=subprocess.run([executable,"-hide_banner","-loglevel","error","-i",str(source),
        "-vn","-ac","1","-ar","22050","-af",
        "highpass=f=45,acompressor=threshold=0.08:ratio=3:attack=3:release=90:makeup=2",
        "-f","f32le","-"],check=True,stdout=subprocess.PIPE).stdout
    samples=array.array("f");samples.frombytes(raw)
    if sys.byteorder!="little":samples.byteswap()
    assert len(samples)==source_frames and all(math.isfinite(v) for v in samples)
    peak=max(abs(v) for v in samples);rms=math.sqrt(sum(v*v for v in samples)/len(samples))
    if peak<.01 or rms<.002:raise ValueError("Silent generated candidate: "+str(source))
    peak_limit={"death":.22,"dismemberment":.20,"head":.70}[layer]
    rms_target={"death":.17,"dismemberment":.18,"head":.24}[layer]
    gain=rms_target/rms
    fade_in,fade_out=44,1103
    values=array.array("h",(round(peak_limit*math.tanh(v*gain/peak_limit)*32767*min(1,i/fade_in,(len(samples)-1-i)/fade_out)) for i,v in enumerate(samples)))
    peak_out=max(abs(v) for v in values)/32768
    rms_out=math.sqrt(sum((v/32768)**2 for v in values)/len(values))
    if sys.byteorder!="little":values.byteswap()
    target.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(target),"wb") as w:
        w.setparams((1,2,22050,0,"NONE","not compressed"));w.writeframes(values.tobytes())
    return dict(duration=len(samples)/22050,source_frames=source_frames,tempo_scale=1.0,peak=round(peak_out,6),rms=round(rms_out,6))

def catalog(clips):
    lookup={c['id']:c for c in clips}
    rows=['// Generated offline by vector-fields/build_death_sounds.py.','#ifndef VF_DEATH_SFX_CATALOG_H','#define VF_DEATH_SFX_CATALOG_H','namespace vfds {','struct Profile {const char* id;const char* death;const char* dismemberment;const char* head;};','static const Profile Profiles[]={']
    for p in recipe()['profiles']:
        d=lookup.get('death_'+p['id']);m=lookup['dismemberment_'+p['id']];h=lookup['head_'+p['id']]
        rows.append('{'+json.dumps(p['id'])+','+(json.dumps(d['path']) if d else '0')+','+json.dumps(m['path'])+','+json.dumps(h['path'])+'},')
    rows+=['};','enum {ProfileCount=sizeof(Profiles)/sizeof(Profiles[0])};','inline const Profile& For(int effect){return Profiles[effect>=0&&effect<ProfileCount-1?effect+1:0];}','}','#endif']
    return '\n'.join(rows)+'\n'

def listening_mix(profile,clips):
    """A mono listening example only; gameplay uses three native sound events."""
    voice=ROOT/'assets/audio/operator-deaths/rocco'/(profile['id']+'_v2.wav')
    if not voice.exists():return None
    paths=[(voice,.85,.015)]
    for layer in ('death','dismemberment'):
        c=clips.get(layer+'_'+profile['id'])
        if c:paths.append((OUT/'sound'/(c['id']+'.wav'),1,0))
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
        for layer,label in [('death','Mort elementaire'),('dismemberment','Arrachement'),('head','Tete qui explose - sans cri')]:
            c=lookup.get(layer+'_'+p['id'])
            if c:
                cells.append('<div><b>'+label+'</b><p>'+html.escape(p[layer]['signature'])+'</p><audio controls preload="none" src="sound/'+c['id']+'.wav"></audio></div>')
            else:cells.append('<div><b>Mort sans effet</b><p>Cri habituel, sans signature elementaire.</p></div>')
        mix=listening_mix(p,lookup)
        extra=('<p>Mix d ecoute : cri de Rocco + cause + bras, sans spatialisation.</p><audio controls preload="none" src="mixes/'+p['id']+'.wav"></audio>') if mix else ''
        cards.append('<article><h2>'+html.escape(p['name'])+'</h2><section>'+''.join(cells)+'</section>'+extra+'</article>')
    document='<!doctype html><html lang="fr"><meta charset="utf-8"><title>Morts et demembrement - Vector Fields</title><style>body{background:#101c24;color:#eef7f9;font:16px system-ui;max-width:1000px;margin:36px auto;padding:16px}h1{color:#69d9c3}article{background:#1a2b35;padding:18px;margin:16px 0;border-radius:12px}section{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}audio{width:100%}p{color:#b6cbd1;line-height:1.5}</style><h1>Morts et demembrement</h1><p>16 causes elementaires, 17 arrachements, 17 explosions de tete. Prises courtes a leur duree naturelle : environ une a deux secondes, sans etirement. En jeu : cri + mort + arrachement sont trois sons natifs distincts. Une tete retiree joue sa seule explosion, sans cri. Les fichiers ci-dessous permettent d ecouter chaque signature seule. F4 puis F8 pour les essayer en situation. Une seule salve d arrachement par evenement, meme si plusieurs membres partent ensemble.</p>'+''.join(cards)+'<script>document.addEventListener("play",e=>document.querySelectorAll("audio").forEach(a=>{if(a!==e.target)a.pause()}),true)</script></html>'
    (OUT/'listen.html').write_text(document,encoding='utf-8')

def build(ensure=False):
    data=recipe();input_hash=digest(DATA);manifest_path=OUT/'manifest.json'
    if ensure and manifest_path.exists():
        old=json.loads(manifest_path.read_text(encoding='utf-8'))
        valid=old.get('recipe_sha256')==input_hash and len(old['clips'])==50 and old.get('build_sha256')==digest(Path(__file__))
        valid=valid and all((OUT/'sound'/(c['id']+'.wav')).is_file() and digest(OUT/'sound'/(c['id']+'.wav'))==c['sha256'] and (master_folder(c)/'shots'/(c.get('master_id',c['id'])+'.mp3')).is_file() and digest(master_folder(c)/'shots'/(c.get('master_id',c['id'])+'.mp3'))==c['source_sha256'] for c in old['clips'])
        if valid and HEADER.exists() and HEADER.read_text()==catalog(old['clips']):
            preview(data,old['clips']);return old
    clips=[]
    for item,request in items(data):
        id=item['id'];source=master_folder(item)/'shots'/(item['master_id']+'.mp3');meta=source.with_suffix('.json');wav=source.with_suffix('.wav')
        if not source.is_file() or not meta.is_file() or not wav.is_file():raise FileNotFoundError('Missing generated candidate '+id+'. Run --generate once; offline build never spends credits.')
        provenance=json.loads(meta.read_text(encoding='utf-8'))
        if provenance['request']!=request or provenance['sha256']!=digest(source):raise ValueError('Generated source does not match recipe: '+id)
        stats=export(wav,OUT/'sound'/(id+'.wav'),item['layer'])
        clips.append(dict(id=id,master_id=item['master_id'],master_bank=item['master_bank'],effect=item['profile']['id'],layer=item['layer'],path='vf_death_sfx/'+id+'.wav',sha256=digest(OUT/'sound'/(id+'.wav')),source_sha256=digest(source),request_id=provenance.get('request_id'),**stats))
    manifest=dict(schema=3,timing='natural source tempo; no time stretching or duration padding',build_sha256=digest(Path(__file__)),provider='ElevenLabs eleven_text_to_sound_v2',recipe_sha256=input_hash,format='mono PCM 22050 Hz / 16 bit',clips=clips)
    audio.json_write(manifest_path,manifest);HEADER.write_text(catalog(clips),encoding='utf-8');preview(data,clips)
    print('Built death audio: 16 deaths + 17 detachments + 17 head explosions, '+str(sum((OUT/'sound'/(c['id']+'.wav')).stat().st_size for c in clips))+' bytes.',flush=True)
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
