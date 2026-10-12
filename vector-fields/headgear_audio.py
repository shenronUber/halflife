"""Generate reusable gear foley and six established actors; filter existing WAVs offline."""
import argparse
import hashlib
import html
import json
import shutil
import subprocess
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import audio_workshop as audio
from voice_workshop import caption, HL_FILTER

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data/headgear_audio.json'
ASSETS = ROOT / 'assets/audio/headgear'
OUT = ROOT / 'generated/headgear-audio'
HEADER = ROOT.parent / 'game_shared/vf_headgear_audio_catalog.h'
FILTER = 'highpass=f=130,lowpass=f=2200:poles=2,equalizer=f=650:t=q:w=1:g=3,acompressor=threshold=0.12:ratio=2:attack=5:release=80:makeup=1.25,alimiter=limit=0.85:level=false,aresample=11025:osf=u8:dither_method=triangular'

def dialogue_entries():
    """Derive all worn-gear speech from the existing voice contract, excluding death."""
    events=read(ROOT/'data/voices.json')['events']
    clips=read(ROOT/'assets/audio/operators/manifest.json')['clips']
    return [(clip,events[clip['event']]) for clip in clips if events[clip['event']]!='death']

def remove_filtered(path, expected, parent):
    """Remove only a known generated derivative, never an original voice asset."""
    path=Path(path);parent=Path(parent).resolve()
    if parent not in path.resolve().parents or path.suffix!='.wav':raise ValueError(path)
    if path.is_file() and digest(path)==expected:path.unlink()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def generate():
    recipe = read(DATA)
    actors = read(ROOT / 'data/voices.json')['actors']
    assert list(recipe['actors']) == [a['id'] for a in actors]
    audio.ASSETS = ASSETS
    audio.preview = lambda: None
    key = audio.load_key()
    quota = audio.status(key)
    if quota.get('remaining_credits_reported', 1) <= 0:
        raise RuntimeError('Included generation quota exhausted')
    jobs = []
    for actor in actors:
        voice_id = read(ROOT / 'assets/audio/operators' / actor['id'] / 'voice.json')['response']['voice_id']
        for category, text in zip(recipe['categories'], recipe['actors'][actor['id']]):
            name = actor['id']+'_'+category
            body = dict(text=text, model_id='eleven_v4', voice_settings=dict(stability=.5, similarity_boost=.8))
            jobs.append(('voice', dict(id=name, name=actor['name']+' / '+category), body,
                         '/v1/text-to-speech/'+voice_id+'?output_format=mp3_44100_128', dict(voice_id=voice_id, name=actor['name'])))
    for sound in recipe['sounds']:
        body = dict(text=sound['prompt'], duration_seconds=sound['seconds'], prompt_influence=.65, loop=False, model_id='eleven_text_to_sound_v2')
        jobs.append(('sfx', dict(id=sound['id'], name=sound['id']), body, '/v1/sound-generation?output_format=mp3_44100_128', None))
    def one(job):
        kind, item, body, endpoint, voice = job
        audio.generate_one(key, kind, item, body, endpoint, voice)
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(one, jobs))
    audio.status(key)

def export(source, destination, filters, width=1, rate=11025):
    destination.parent.mkdir(parents=True, exist_ok=True)
    executable = audio.ffmpeg()
    if not executable:
        raise RuntimeError('A local FFmpeg encoder is required')
    subprocess.run([executable, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
                    '-vn', '-ac', '1', '-af', filters, '-ar', str(rate), '-c:a', 'pcm_u8' if width == 1 else 'pcm_s16le', str(destination)], check=True)
    with wave.open(str(destination)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, width, rate)
        duration = wav.getnframes()/rate
        samples = wav.readframes(wav.getnframes())
        assert duration > .15
        if width == 1:
            assert max(abs(v-128) for v in samples) > 8
    return round(duration, 4)

def build(ensure=False):
    import build_cache
    inputs=[Path(__file__),DATA,ROOT/'data/voices.json',ROOT/'audio_workshop.py',ROOT/'voice_workshop.py',Path(audio.ffmpeg())]
    for folder in (ASSETS,ROOT/'assets/audio/operators'):
        inputs.extend(p for p in folder.rglob('*') if p.suffix in ('.wav','.mp3','.json'))
    fingerprint=build_cache.fingerprint(inputs);cache=OUT/'build-cache.json'
    if ensure and build_cache.current(build_cache.read(cache),fingerprint):
        print('Headgear audio is current.',flush=True);return read(OUT/'manifest.json')
    recipe = read(DATA)
    actors = read(ROOT / 'data/voices.json')['actors']
    previous=read(OUT/'manifest.json') if (OUT/'manifest.json').exists() else {}
    old_masked={c['original']:c for c in previous.get('muffled',[])}
    clips, sounds, muffled = [], [], []
    for ai, actor in enumerate(actors):
        for ci, category in enumerate(recipe['categories']):
            stem = actor['id']+'_'+category
            source = ASSETS / 'voices' / (stem+'.wav')
            meta = read(source.with_suffix('.json'))
            expected = recipe['actors'][actor['id']][ci]
            assert meta['text'] == expected
            assert meta['voice_id'] == read(ROOT / 'assets/audio/operators' / actor['id'] / 'voice.json')['response']['voice_id']
            assert digest(source.with_suffix('.mp3')) == meta['sha256']
            path = 'vf_headgear/voices/'+stem+'.wav'
            duration = export(source, OUT / 'sound' / path, HL_FILTER)
            clips.append(dict(actor=ai, category=ci, path=path, text=caption(expected), duration=duration,
                              voice_id=meta['voice_id'], source_sha256=meta['sha256'], sha256=digest(OUT / 'sound' / path)))
    for sound in recipe['sounds']:
        source = ASSETS / 'shots' / (sound['id']+'.wav')
        meta = read(source.with_suffix('.json'))
        assert meta['request']['text'] == sound['prompt'] and digest(source.with_suffix('.mp3')) == meta['sha256']
        path = 'vf_headgear/sfx/'+sound['id']+'.wav'
        duration = export(source, OUT / 'sound' / path, 'highpass=f=60,lowpass=f=9000,alimiter=limit=0.60:level=false', 2, 22050)
        sounds.append(dict(id=sound['id'], path=path, duration=duration, sha256=digest(OUT / 'sound' / path)))
    banks = [(ROOT / 'assets/audio/operators', dialogue_entries())]
    for bank, entries in banks:
        for clip,event in entries:
            original = clip['path']
            rel = original.split('/', 1)[1]
            source = bank / rel
            # Use clean existing masters when available; no new voice performance.
            master = source.with_name(source.stem+'_master.wav')
            if master.exists():
                source = master
            actor = clip['actor'] if isinstance(clip['actor'], str) else actors[clip['actor']]['id']
            name = Path(original).stem
            path = 'vf_muffle/'+actor+'/v_'+name+'.wav'
            assert len(path) < 64
            old=old_masked.get(original);source_hash=digest(source);target=OUT/'sound'/path
            if old and previous.get('muffle_filter')==FILTER and old['source_sha256']==source_hash and target.is_file() and digest(target)==old['sha256']:
                duration=old['duration']
            else:duration = export(source, target, FILTER)
            muffled.append(dict(original=original, path=path, duration=duration, source_sha256=digest(source),
                                sha256=digest(target),event=event,actor=actor))
    lines = ['// Generated by vector-fields/headgear_audio.py build.', '#ifndef VF_HEADGEAR_AUDIO_CATALOG_H', '#define VF_HEADGEAR_AUDIO_CATALOG_H',
             '#include <string.h>', 'namespace vfha {', 'enum {ScheduleEvent=31};',
             'struct Clip {int actor,category;const char* path;const char* text;float duration;};', 'static const Clip Clips[]={']
    for c in clips:
        lines.append('{%d,%d,%s,%s,%.4ff},' % (c['actor'], c['category'], json.dumps(c['path']), json.dumps(c['text']), c['duration']))
    lines += ['};', 'enum {ClipCount=sizeof(Clips)/sizeof(Clips[0])};', 'static const char* Sounds[3][2]={']
    lookup = {s['id']:s['path'] for s in sounds}
    for category in ('visor', 'mask', 'goggles'):
        lines.append('{'+json.dumps(lookup[category+'_down'])+','+json.dumps(lookup[category+'_up'])+'},')
    lines += ['};', 'struct Masked {const char* original;const char* path;};', 'static const Masked Muffled[]={']
    lines.extend('{'+json.dumps(c['original'])+','+json.dumps(c['path'])+'},' for c in muffled)
    lines += ['};', 'enum {MuffledCount=sizeof(Muffled)/sizeof(Muffled[0])};',
              'inline const char* Mask(const char* path){for(int i=0;i<MuffledCount;++i)if(!strcmp(path,Muffled[i].original))return Muffled[i].path;return path;}',
              'inline int Category(int type){return type==5?2:type==3||type==4?3:1;}', '}', '#endif']
    HEADER.write_text('\n'.join(lines)+'\n', encoding='ascii')
    manifest = dict(schema=1, provider='ElevenLabs', recipe_sha256=digest(DATA), clips=clips, sounds=sounds,
                    muffled=muffled, muffle_filter=FILTER, existing_voice_identities_only=True,
                    muffle_policy=dict(dialogue_events=sorted({c['event'] for c in muffled}),activation='normal before lowering',death_sounds='original only'))
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    preview(manifest)
    kept={c['path'] for c in muffled}
    for old in previous.get('muffled',[]):
        if old['path'] not in kept:remove_filtered(OUT/'sound'/old['path'],old['sha256'],OUT/'sound/vf_muffle')
    outputs=[HEADER,OUT/'manifest.json',OUT/'listen.html']+[OUT/'sound'/c['path']for c in clips+sounds+muffled]
    build_cache.write(cache,build_cache.record(fingerprint,outputs))
    print('PASS headgear audio:', len(clips), 'new lines;', len(sounds), 'gear sounds;', len(muffled), 'filtered existing recordings', flush=True)
    return manifest

def runtime_files():
    manifest = read(OUT / 'manifest.json')
    for row in manifest['clips'] + manifest['sounds'] + manifest['muffled']:
        source = OUT / 'sound' / row['path']
        assert digest(source) == row['sha256'], source
        yield source, Path('sound') / row['path']
    yield OUT / 'manifest.json', Path('vf/headgear-audio.json')

def deploy(mod):
    mod=Path(mod);previous=mod/'vf/headgear-audio.json'
    old=read(previous) if previous.exists() else {}
    for source, rel in runtime_files():
        target = Path(mod) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or digest(target) != digest(source):
            # Staged media can be immutable hardlinks; detach before replacing.
            if target.exists() and target.stat().st_nlink > 1:
                target.unlink()
            shutil.copy2(source, target)
    kept={c['path'] for c in read(OUT/'manifest.json')['muffled']}
    for entry in old.get('muffled',[]):
        if entry['path'] not in kept:remove_filtered(mod/'sound'/entry['path'],entry['sha256'],mod/'sound/vf_muffle')

def preview(manifest):
    sounds, voices, textures, worn = [], [], [], []
    labels = {'visor_down':'Visière : abaisser / verrouiller','visor_up':'Visière : déverrouiller / relever',
              'mask_down':'Masque : poser / fermer le joint','mask_up':'Masque : ouvrir / relever',
              'goggles_down':'Optiques : poser / allumer','goggles_up':'Optiques : relever / éteindre'}
    for c in manifest['sounds']:
        sounds.append('<article><h3>'+html.escape(labels[c['id']])+'</h3><audio controls preload="none" src="sound/'+c['path']+'"></audio></article>')
    masked = {c['original']:c['path'] for c in manifest['muffled']}
    actors = read(ROOT/'data/voices.json')['actors']
    categories = ['Équipement : générique','Visière','Masque','Lunettes']
    for c in manifest['clips']:
        label=actors[c['actor']]['name']+' / '+categories[c['category']]
        voices.append('<article><p class="label">'+html.escape(label)+'</p><h3>'+html.escape(c['text'])+'</h3><p>Annonce avant la pose : voix normale</p><audio controls preload="none" src="sound/'+c['path']+'"></audio></article>')
    for c,event in dialogue_entries():
        if c['variant']!=0 or event not in ('reload','taunt','counter_taunt','low_health','armor_break','pain','hydro','arc_chain'):continue
        label=actors[c['actor']]['name']+' / '+event
        source='../../assets/audio/operators/'+c['path'].split('/',1)[1]
        worn.append('<article><p class="label">'+html.escape(label)+'</p><h3>'+html.escape(c['text'])+'</h3><p>Protection relevée</p><audio controls preload="none" src="'+source+'"></audio><p>Protection portée</p><audio controls preload="none" src="sound/'+masked[c['path']]+'"></audio></article>')
    hud=ROOT/'data/headgear_hud.json'
    if hud.exists():
        for item in read(hud)['assets']:
            textures.append('<article><h3>'+html.escape(item['name'])+'</h3><img alt="Texture RGBA avec ouverture transparente" src="../../assets/headgear/hud/frames/'+item['id']+'.png"></article>')
    doc = '<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Équipements de tête — revue</title><style>body{background:#141e27;color:#eef5f8;font:16px system-ui;margin:30px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}article{background:#24313f;padding:18px;border-radius:12px}audio,img{width:100%}.label{color:#a8c5cb;font-size:14px}h2{margin-top:38px}img{background:#161f26}</style><h1>Équipements de tête</h1><p>H : relever / abaisser. Annonces de pose et cris de mort restent normaux. Les autres répliques sont étouffées lorsque la protection couvre le visage.</p><h2>Textures du HUD</h2><main>'+''.join(textures)+'</main><h2>Sons mécaniques</h2><main>'+''.join(sounds)+'</main><h2>Annonces d’activation : voix normale</h2><main>'+''.join(voices)+'</main><h2>Dialogue porté : normale / étouffée</h2><main>'+''.join(worn)+'</main><script>document.addEventListener("play",e=>document.querySelectorAll("audio").forEach(a=>{if(a!==e.target)a.pause()}),true)</script></html>'
    (OUT / 'listen.html').write_text(doc, encoding='utf-8')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('generate', 'build'))
    parser.add_argument('--ensure',action='store_true')
    args = parser.parse_args()
    generate() if args.command == 'generate' else build(ensure=args.ensure)
