"""Real engine: slide bob, live sound mixer, jump/release/timeout and combat."""
import argparse,json,re,shutil,struct,subprocess,sys,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from slide_feet_bundle import INSTALLED,prepare_slide_feet,digest
import build_traversal_sounds as bank
BUILD=ROOT/'build/slide-feedback'
OUT=ROOT/'docs/validation/traversal/slide-feedback'

def channels(save):
    # Xash serializes the actual client mixer, not just server sound intents.
    data=save.read_bytes();base=data.find(b'JSAV'+struct.pack('<i',103));assert base>=0,save
    _,version,size,count,token_bytes=struct.unpack_from('<4s4i',data,base)
    assert version==103 and 0<count<10000 and 0<size<100000
    tokens=data[base+20:base+20+token_bytes].split(b'\0')
    payload=data[base+20+token_bytes:base+20+token_bytes+size];result=[];current=None;o=0
    formats={'entnum':'<H','channel':'<B','pitch':'<B','samplePos':'<d'}
    while o<len(payload):
        n,token=struct.unpack_from('<HH',payload,o);value=payload[o+4:o+4+n];name=tokens[token].decode('ascii');o+=n+4
        if name=='SOUNDLIST':
            if current:result.append(current)
            current={}
        elif current is not None:
            if name=='name':current[name]=value.split(b'\0')[0].decode('ascii')
            elif name in formats:current[name]=struct.unpack(formats[name],value)[0]
    if current:result.append(current)
    return result

def run(installed=False):
    manifest=bank.build(ensure=True);clip=manifest['clips'][0];wav=bank.OUT/'slide.wav'
    stamps=[p.stat().st_mtime_ns for p in [wav,bank.OUT/'manifest.json']];bank.build(ensure=True)
    assert stamps==[p.stat().st_mtime_ns for p in [wav,bank.OUT/'manifest.json']],'ensure must reuse the asset'
    with wave.open(str(wav)) as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,22050)
        assert w.getnframes()==manifest['contract']['frames'] and w.getnframes()/w.getframerate()==manifest['contract']['duration']
        samples=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)/32768
    assert samples[0]==samples[-1]==0 and .03<np.sqrt(np.mean(samples*samples))<.12
    assert np.max(np.abs(samples))<.5 and not manifest['loop']
    bundle=ROOT/'build' if installed else BUILD
    engine,mod=prepare_slide_feet('feedback-installed' if installed else 'feedback',build=bundle,
        server=bundle/'server/hl.dll',engine_binaries=INSTALLED if installed else None);bank.deploy(mod)
    lines=['wait 180','gl_vsync 0','host_framerate 0.0166667','fps_max 60','developer 2',
           'con_notifytime -1','vf_voice_subtitles 0','god','cmd give weapon_9mmAR','weapon_9mmAR',
           'wait 20','vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 12']
    def add(*commands):lines.extend(commands)
    def probe(name):add('echo FEEDBACK_'+name,'cmd vf_traversal_info','save vf_feedback_'+name.lower(),'wait 2')
    def place(speed=400):add('-duck','-jump','-attack','-reload','cmd vf_traversal_place 128 -750 36 0 '+str(speed)+' 0 0','wait 1','vf_traversal_look 0 0')
    place(320);add('+forward','wait 20');probe('WALK');add('-forward','wait 35')
    place();add('+duck','wait 12');probe('JUMP_ACTIVE')
    add('+attack','wait 6');probe('SHOOT');add('-attack','wait 2','screenshot scrshots/slide_feedback.png','wait 3')
    add('+jump','wait 1','-jump','wait 2');probe('JUMP_EXIT');add('-duck','wait 110')
    place();add('+duck','wait 12');probe('RELEASE_ACTIVE');add('-duck','wait 2');probe('RELEASE_EXIT');add('wait 60')
    place();add('+duck','wait 15');probe('FULL_ACTIVE');add('wait 65');probe('FULL_EXIT');add('-duck','wait 55')
    place();add('+duck','wait 8','+reload','wait 2','-reload','wait 4');probe('RELOAD')
    add('-duck','wait 160');probe('RELOAD_EXIT');add('vf_engine_stats','quit')
    (mod/'slide_feedback.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii');log=engine/'slide-feedback.log'
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game','vf_animation','-windowed','-width','1280','-height','720','-console','-nointro','-nowriteconfig',
        '-dev','2','-log',log.name,'+sv_cheats','1','+developer','2','+maxplayers','1','+map','vf_traversal',
        '+exec','slide_feedback.cfg'],cwd=engine)
    try:process.wait(timeout=65)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=8)
    OUT.mkdir(parents=True,exist_ok=True);text=log.read_text(errors='replace');shutil.copy2(log,OUT/log.name)
    assert process.returncode==0,process.returncode
    assert 'VFEngine: native extension v4 connected' in text and 'rejected=0' in text
    assert not any(clip['path'] in line and any(error in line.lower() for error in ('not precached',"couldn't",'error'))
                   for line in text.splitlines()),'slide audio must load and be precached'
    observations={}
    for name,block in re.findall(r'FEEDBACK_(\w+)\s+(.*?)(?=FEEDBACK_|\Z)',text,re.S):
        row=re.search(r'VFTraversal phase=(\d+) state=\d+ origin=([\d.,-]+) velocity=([\d.,-]+) time=([\d.-]+) health=[\d.-]+ clip=(-?\d+) reload=(\d+)',block)
        assert row,name
        p,origin,velocity,remaining,ammo,reload=row.groups()
        sounds=channels(mod/'save'/('vf_feedback_'+name.lower()+'.sav'))
        observations[name]=dict(phase=int(p),remaining=float(remaining),clip=int(ammo),reload=int(reload),
                               velocity=list(map(float,velocity.split(','))),sounds=sounds)
        active=[s for s in sounds if s.get('name')==clip['path']]
        if int(p)==5:
            assert len(active)==1 and active[0]['channel']==4 and active[0]['entnum']==1,(name,sounds)
            assert 0<active[0]['samplePos']<clip['frames'],(name,active)
            assert not any(s.get('name','').startswith('player/pl_step') for s in sounds),(name,sounds)
        else:assert not active,(name,sounds)
    for name in ['JUMP_ACTIVE','SHOOT','RELEASE_ACTIVE','FULL_ACTIVE','RELOAD']:assert observations[name]['phase']==5,name
    for name in ['WALK','JUMP_EXIT','RELEASE_EXIT','FULL_EXIT','RELOAD_EXIT']:assert observations[name]['phase']==0,name
    assert observations['JUMP_EXIT']['velocity'][2]>200,'must retain the ordinary jump'
    assert observations['SHOOT']['clip']<observations['JUMP_ACTIVE']['clip'],'firing must work while the cue plays'
    assert observations['RELOAD']['reload']==1 and observations['RELOAD_EXIT']['reload']==0
    assert observations['RELOAD_EXIT']['clip']>observations['RELOAD']['clip'],'reload must complete normally'
    bob=[(float(s),float(raw),float(applied)) for s,raw,applied in re.findall(r'VFSlideView time=[\d.]+ scale=([\d.]+) raw=([\d.-]+) applied=([\d.-]+)',text)]
    sliding=[r for r in bob if r[0]<1];walking=[r for r in bob if r[0]==1 and abs(r[1])>.2]
    assert len(sliding)>60 and len(walking)>10,(len(sliding),len(walking))
    assert all(abs(s-.1)<.001 and abs(applied-raw*.1)<.00015 for s,raw,applied in sliding)
    assert all(abs(raw-applied)<.00015 for s,raw,applied in walking),'ordinary walking bob must remain unchanged'
    bodies=list(map(int,re.findall(r'VFFirstPersonBody parts=\d+ mask=\d+ phase=(\d+)',text)))
    assert 0 in bodies and 5 in bodies,'preserve the world-space first-person slide legs'
    shutil.copy2(mod/'scrshots/slide_feedback.png',OUT/'slide.png')
    report=dict(passed=True,source='Actual GoldSrc camera and live client audio mixer',bob_scale=.1,
                sliding_camera_samples=len(sliding),ordinary_camera_samples=len(walking),
                max_applied_slide_bob=max(abs(r[2]) for r in sliding),
                sound_duration=clip['duration'],sound_sha256=digest(wav),observations=observations,
                client_sha256=digest(mod/'cl_dlls/client.dll'),server_sha256=digest(mod/'dlls/hl.dll'),
                renderer_sha256=digest(engine/'ref_gl.dll'),world_slide_feet_preserved=True)
    (OUT/('native-installed.json' if installed else 'native.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('PASS native slide feedback: 90% less bob, one friction channel, jump/release/timeout silence, firing and reload.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--installed',action='store_true')
    run(installed=parser.parse_args().installed)
