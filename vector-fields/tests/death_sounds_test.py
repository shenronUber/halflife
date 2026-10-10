"""Generated death sound bank and native concurrent mixer/network regressions."""
from __future__ import annotations
import argparse,array,hashlib,json,re,shutil,struct,subprocess,sys,time,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import build_death_sounds as bank
import third_person_native_test as harness
OUT=ROOT/'build/death-audio';OUT.mkdir(parents=True,exist_ok=True)
REGIONS=['head','left_arm','right_arm','left_leg','right_leg']
STEAM='F:/SteamLibrary/steamapps/common/Half-Life'

def report(name,data):
    (OUT/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print('PASS death audio '+name,json.dumps(data),flush=True)

def samples(path):
    with wave.open(str(path)) as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,22050)
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768

def assets():
    manifest=bank.build(ensure=True);assert len(manifest['clips'])==33
    keys={(c['layer'],c['effect']) for c in manifest['clips']};ids=[p['id'] for p in bank.recipe()['profiles']]
    assert keys=={('death',id) for id in ids[1:]}|{('dismemberment',id) for id in ids}
    assert len({c['sha256'] for c in manifest['clips']})==33
    assert len({c['source_sha256'] for c in manifest['clips']})==33
    durations={};features=[]
    for c in manifest['clips']:
        path=bank.OUT/'sound'/(c['id']+'.wav');x=samples(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==c['sha256']
        assert .3<len(x)/22050<2.6 and np.max(np.abs(x))<(.181 if c['layer']=='death' else .201)
        assert np.sqrt(np.mean(x*x))>.003,c['id']
        assert np.max(np.abs(x[:1544]))>.002,c['id'] # audible onset within 70 ms
        assert np.max(np.abs(x[-22:]))<.012,c['id'] # short fade prevents click
        assert abs(len(x)/22050-c['duration'])<.000001
        durations[c['id']]=c['duration']
        # Signal comparison complements the independent material/rhythm recipes;
        # it is not a claim that spectral measurements prove perceptual identity.
        frames=[x[i:i+2048]*np.hanning(2048) for i in range(0,len(x)-2048,512)]
        energy=np.abs(np.fft.rfft(frames))**2;freq=np.fft.rfftfreq(2048,1/22050)
        bands=np.geomspace(60,10000,17);spectral=np.array([np.mean(energy[:,(freq>=a)&(freq<b)]) for a,b in zip(bands,bands[1:])]);spectral/=spectral.sum()
        env=np.array([np.sqrt(np.mean(part**2)) for part in np.array_split(x,16)]);env/=np.linalg.norm(env)
        f=np.r_[spectral/np.linalg.norm(spectral),env];features.append((c['id'],f/np.linalg.norm(f)))
    pairs=sorted([(float(np.dot(a,b)),ia,ib) for i,(ia,a) in enumerate(features) for ib,b in features[:i]],reverse=True)
    assert not list(bank.MASTERS.glob('**/*.pending'))
    listen=(bank.OUT/'listen.html').read_text(encoding='utf-8')
    for src in re.findall(r'src="([^"]+)"',listen):assert (bank.OUT/src).is_file()
    report('assets',dict(clips=33,death=16,dismemberment=17,format=manifest['format'],bytes=sum((bank.OUT/'sound'/(c['id']+'.wav')).stat().st_size for c in manifest['clips']),duration_range=[min(durations.values()),max(durations.values())],closest_signal_pairs=pairs[:5],checks=['each element and cross-element reaction has independent death and detachment assets','neutral detachment exists without an elemental death cue','33 unique generated masters and exported WAV hashes','audible quick attacks, no digital clipping, fade-outs and mix headroom','complete offline bank; preview links and provenance valid']))
    return manifest

def mixer_channels(save):
    # Xash saves S_GetCurrentDynamicSounds from the actual client mixer, not
    # server intents. HL2 uses engine v103 with a tokenized SOUNDLIST stream.
    data=save.read_bytes();base=data.find(b'JSAV'+struct.pack('<i',103));assert base>=0,save
    _,version,size,count,token_bytes=struct.unpack_from('<4s4i',data,base)
    assert version==103 and 0<count<10000 and 0<size<100000
    tokens=data[base+20:base+20+token_bytes].split(b'\0')
    payload=data[base+20+token_bytes:base+20+token_bytes+size]
    channels=[];current=None;o=0
    formats={'entnum':'<H','volume':'<f','attenuation':'<f','channel':'<B','pitch':'<B','samplePos':'<d'}
    while o<len(payload):
        n,token=struct.unpack_from('<HH',payload,o);value=payload[o+4:o+4+n];name=tokens[token].decode('ascii');o+=n+4
        if name=='SOUNDLIST':
            if current:channels.append(current)
            current={}
        elif current is not None:
            if name=='name':current[name]=value.split(b'\0')[0].decode('ascii')
            elif name in formats:current[name]=struct.unpack(formats[name],value)[0]
    if current:channels.append(current)
    return channels

def setup(name):
    e=harness.stage(name);m=e/'vf_animation';(m/'maps').mkdir(exist_ok=True);shutil.copy2(ROOT/'generated/test-room/vf_range.bsp',m/'maps/vf_range.bsp');return e,m

def launch(e,cfg,log):
    p=subprocess.Popen([str(e/'xash3d.exe'),'-rodir',STEAM,'-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log',log,'+sv_cheats','1','+map','vf_range','+exec',cfg],cwd=e)
    try:p.wait(timeout=135);assert p.returncode==0
    finally:
        if p.poll() is None:p.terminate();p.wait(10)
    return (e/log).read_text(errors='replace')

def native():
    e,m=setup('death-audio');cfg='wait 180\ndeveloper 1\ncon_notifytime 0\ngl_vsync 0\nfps_max 60\ncmd vf_range_aim 0\nwait 260\ns_show 1\n'
    cases=[]
    for i,p in enumerate(bank.recipe()['profiles'][1:]):
        id=p['id'];region=REGIONS[i%5]
        cases.append(dict(id=id,cause=id,region=region,voices=True,death=True,tear=True,setup='cmd vf_range_effect 0 '+id+'\n'))
    cases += [
        dict(id='neutral',cause='standard',region='head',voices=True,death=False,tear=True,setup=''),
        dict(id='plain',cause='standard',region='none',voices=True,death=False,tear=False,setup=''),
        dict(id='effect_only',cause='electro',region='none',voices=True,death=True,tear=False,setup='cmd vf_range_effect 0 electro\n'),
        dict(id='voices_muted',cause='electro',region='left_arm',voices=False,death=True,tear=True,setup='vf_voices 0\ncmd vf_range_effect 0 electro\n'),
        dict(id='death_muted',cause='electro',region='right_arm',voices=True,death=False,tear=True,setup='vf_death_sfx_volume 0\ncmd vf_range_effect 0 electro\n'),
        dict(id='tear_muted',cause='electro',region='right_leg',voices=True,death=True,tear=False,setup='vf_dismember_sfx_volume 0\ncmd vf_range_effect 0 electro\n'),
        dict(id='both_muted',cause='electro',region='head',voices=True,death=False,tear=False,setup='vf_death_sfx_volume 0\nvf_dismember_sfx_volume 0\ncmd vf_range_effect 0 electro\n'),
        dict(id='reaction_priority',cause='arc_chain',region='left_arm',voices=True,death=True,tear=True,setup='cmd vf_range_effect 0 arc_chain\nwait 1\ncmd vf_range_effect 0 thermal\n'),
        dict(id='expired',cause='standard',region='none',voices=True,death=False,tear=False,setup='cmd vf_range_effect 0 electro .2\nwait 70\n'),
        dict(id='tactical',cause='standard',region='none',voices=True,death=False,tear=False,setup='cmd vf_range_effect 0 phase\n'),
        dict(id='all_limbs',cause='shatter',region='all',voices=True,death=True,tear=True,setup='cmd vf_range_effect 0 shatter\n'),
    ]
    for case in cases:
        id=case['id'];cfg+='cmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_voice 0 rocco\nvf_voices 1\nvf_death_sfx_volume .8\nvf_dismember_sfx_volume .8\nstopsound\necho BEGIN_'+id+'\n'+case['setup']+f'cmd vf_range_death 0 {case["region"]}\nwait 12\nsave vf_audio_{id}\n'
        if id in ('electro','cryo','corrosion','all_limbs'):cfg+=f'screenshot scrshots/{id}_mix.png\n'
        # A second fatal probe on the already dead target must be ignored.
        cfg+=f'cmd vf_range_kill 0\nwait 220\necho END_{id}\n'
    # Existing corpse state is restored after the one-shot sounds have ended.
    cfg+='vf_voices 1\nvf_death_sfx_volume .8\nvf_dismember_sfx_volume .8\ncmd vf_death_clear\ncmd vf_range_reset 0\ncmd vf_range_death 0 left_arm corrosion\nwait 340\nsave vf_audio_settled\nwait 12\necho RESTORE_BEGIN\nload vf_audio_settled\nwait 100\necho RESTORE_END\n'
    # Real player deaths and full gibbing use the same pre-clear cause snapshot.
    cfg+='stopsound\ncmd vf_voice_set rocco\necho PLAYER_BEGIN\ncmd vf_death_test right_leg cryo\nwait 12\nscreenshot scrshots/player_mix.png\nwait 280\necho PLAYER_END\n'
    cfg+='load vf_audio_settled\nwait 120\nstopsound\ncmd vf_voice_set rocco\ncmd vf_status_dev 1\ncmd vf_status_apply electro\necho GIB_BEGIN\ncmd vf_voice_test gib\nwait 12\nscreenshot scrshots/gib_mix.png\nwait 240\necho GIB_END\nquit\n'
    (m/'death_audio.cfg').write_text(cfg,encoding='ascii');started=time.monotonic();log=launch(e,'death_audio.cfg','death-audio.log');(OUT/'native.log').write_text(log)
    for error in ['Host_Error','SV_Error','not precached','Could not load','VFState rejected']:assert error not in log,error
    verified=[]
    for case in cases:
        id=case['id'];part=log.split('BEGIN_'+id+' ')[1].split('END_'+id+' ')[0]
        expected=[]
        if case['voices']:expected.append(('vf_deaths/rocco/'+case['cause']+'_v2.wav',2))
        if case['death']:expected.append(('vf_death_sfx/death_'+case['cause']+'.wav',4))
        if case['tear']:expected.append(('vf_death_sfx/dismemberment_'+case['cause']+'.wav',3))
        channels=mixer_channels(m/'save'/('vf_audio_'+id+'.sav'))
        actual=[c for c in channels if c.get('name','').startswith(('vf_deaths/','vf_death_sfx/'))]
        assert {(c['name'],c['channel']) for c in actual}==set(expected),(id,actual,expected)
        assert all(c.get('samplePos',0)>0 and c.get('volume',0)>0 and c['attenuation']>0 for c in actual),(id,actual)
        assert len(re.findall(r'VFDeathSfx play .*layer=death',part))==int(case['death']),(id,part[-1600:])
        assert len(re.findall(r'VFDeathSfx play .*layer=dismemberment',part))==int(case['tear']),(id,part[-1600:])
        verified.append(dict(case=id,region=case['region'],active_native_channels=actual))
    restored=log.split('RESTORE_BEGIN ')[1].split('RESTORE_END ')[0]
    assert 'VFDeathSfx play' not in restored and 'VFDeath play:' not in restored
    player_part=log.split('PLAYER_BEGIN ')[1].split('PLAYER_END ')[0]
    gib_part=log.split('GIB_BEGIN ')[1].split('GIB_END ')[0]
    for name,part,effect in [('player',player_part,'cryo'),('gib',gib_part,'electro')]:
        assert len(re.findall(r'VFDeath play: entity=1 actor=rocco cause='+effect,part))==1,(name,part[-2000:])
        assert len(re.findall(r'VFDeathSfx play .*layer=death effect='+effect,part))==1,(name,part[-2000:])
        assert len(re.findall(r'VFDeathSfx play .*layer=dismemberment effect='+effect,part))==1,(name,part[-2000:])
        assert len(re.findall(r'VFDeathSfx received:',part))==2,(name,part[-2000:])
        shutil.copy2(m/'scrshots'/(name+'_mix.png'),OUT/(name+'_mix.png'))
    player=dict(cause='cryo',native_s_show_capture=str(OUT/'player_mix.png'));gib=dict(cause='electro',native_s_show_capture=str(OUT/'gib_mix.png'))
    for id in ('electro','cryo','corrosion','all_limbs'):shutil.copy2(m/'scrshots'/(id+'_mix.png'),OUT/(id+'_mix.png'))
    report('native',dict(seconds=round(time.monotonic()-started,2),cases=verified,player=player,full_gib=gib,checks=['all 16 genuine status deaths play three simultaneous native mixer channels','five body regions plus all-limb event; one detachment cue per event','ordinary non-elemental deaths retain only the cry','elemental death without dismemberment has two channels','voice and each SFX volume mute independently','active reaction outranks a more recently applied base element','expired effects and tactical conditions do not select elemental sounds','already dead targets cannot trigger a second death','restoring a settled corpse does not trigger old death sounds','real player death and full-body gib preserve the pre-clear effect']))
    return verified

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['assets','native'],default='assets');a=p.parse_args();assets() if a.mode=='assets' else native()
