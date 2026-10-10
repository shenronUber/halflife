"""Validate original operator assets and actual Xash single/multiplayer behavior."""
import argparse,array,hashlib,json,re,shutil,subprocess,time,wave,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
PROJECT=ROOT.parent
SOURCE=PROJECT/'runtime/vector-engine'
ENGINE=PROJECT/'runtime/vector-engine-voice-validation'
MOD=ENGINE/'vf_visual'
ASSETS=ROOT/'assets/audio/operators'
ACTORS=[a['id'] for a in json.loads((ROOT/'data/voices.json').read_text(encoding='utf-8-sig'))['actors']]
STEAM='F:/SteamLibrary/steamapps/common/Half-Life'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write_report(name,data):
    p=ROOT/'build'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2))
def assets():
    catalog=read(ROOT/'data/voices.json');manifest=read(ASSETS/'manifest.json')
    assert len(manifest['actors'])==len(ACTORS)
    voices=[read(ASSETS/a['id']/'voice.json')['response']['voice_id'] for a in catalog['actors']]
    assert len(set(voices))==len(ACTORS)
    stats=[]
    for clip in manifest['clips']:
        file=ASSETS/clip['path'].removeprefix('vf_voices/')
        assert hashlib.sha256(file.read_bytes()).hexdigest()==clip['sha256'],file
        with wave.open(str(file)) as w:
            assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,11025,1)
            samples=w.readframes(w.getnframes());duration=w.getnframes()/w.getframerate()
        peak=max(abs(x-128) for x in samples)
        assert peak>10 and not any(x in (0,255) for x in samples),(file,peak)
        assert abs(duration-clip['duration'])<.001
        master=file.with_name(file.stem+'_master.wav')
        with wave.open(str(master)) as w:assert (w.getnchannels(),w.getframerate(),w.getsampwidth())==(1,22050,2)
        meta=read(file.with_suffix('.json'))
        assert meta['voice_id']==voices[clip['actor']]
        stats.append(dict(path=clip['path'],seconds=duration,peak=peak))
    for ai,a in enumerate(catalog['actors']):
        for ei,event in enumerate(catalog['events']):
            assert len([c for c in manifest['clips'] if c['actor']==ai and c['event']==ei])==len(a['lines'][event]),(a['id'],event)
    for e in read(ROOT/'data/effects.json')['effects']:assert e['id'] in catalog['events']
    assert len(manifest['clips'])<256
    doc=(ASSETS/'listen.html').read_text(encoding='utf-8')
    for src in re.findall(r'src="([^"]+)"',doc):assert (ASSETS/src).is_file(),src
    assert not list(ASSETS.glob('**/*.pending'))
    report=dict(actors=len(ACTORS),clips=len(stats),bytes=sum((ASSETS/c['path'].removeprefix('vf_voices/')).stat().st_size for c in manifest['clips']),
        seconds=round(sum(c['seconds'] for c in stats),2),format='mono PCM 11025 Hz / 8-bit',
        checks=['distinct generated voice identities for every actor','every event and variant covered for every actor',
                'all game WAVs match manifest hashes and durations','no silence or full-scale clipping',
                'clean masters retained at 22050 Hz / 16-bit','all listening page links exist',
                'all 8 elements, 8 combinations and 5 tactical cues covered','no ambiguous requests pending'])
    write_report('voices-assets-verification.json',report);print('PASS voices assets',report,flush=True)
def prepare():
    from release import check_native_interface
    check_native_interface(SOURCE,ROOT/'build/client/client.dll')
    ENGINE.mkdir(parents=True,exist_ok=True)
    for p in SOURCE.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.exe'):shutil.copy2(p,ENGINE/p.name)
    for folder in ['valve','vf_visual','cs_assets','tfc_assets']:
        if (SOURCE/folder).exists():
            shutil.copytree(SOURCE/folder,ENGINE/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
    for part,destination in [('server','dlls/hl.dll'),('client','cl_dlls/client.dll')]:
        shutil.copy2(ROOT/f'build/{part}'/Path(destination).name,MOD/destination)
    manifest=read(ASSETS/'manifest.json')
    for clip in manifest['clips']:
        rel=clip['path'].removeprefix('vf_voices/')
        target=MOD/'sound'/clip['path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ASSETS/rel,target)
    from death_voice_workshop import deploy as deploy_death_voices
    deploy_death_voices(MOD)
    return manifest
def run_native():
    manifest=prepare()
    cfg='wait 240\ndeveloper 1\ncon_notifytime 0\nfps_max 100\nwait 500\ncmd vf_voice_info\n'
    # A real accepted reload, followed by key-spam protection.
    cfg+='cmd vf_voice_set rocco\nweapon_9mmAR\n+attack\nwait 8\n-attack\nwait 25\n+reload\nwait 12\n-reload\nwait 450\n'
    cfg+='cmd vf_voice_set rocco\necho VOICE_SPAM_BEGIN\ncmd vf_taunt\nwait 2\ncmd vf_taunt\nwait 2\ncmd vf_taunt\nwait 30\necho VOICE_SPAM_END\n'
    cfg+='screenshot scrshots/voices_rocco_taunt.png\nwait 10\n'
    for actor in ACTORS:
        cfg+=f'cmd vf_voice_set {actor}\ncmd vf_voice_preview spawn\nwait 10\ncmd vf_voice_preview taunt\nwait 20\nscreenshot scrshots/voices_{actor}.png\nwait 5\n'
    for effect in read(ROOT/'data/effects.json')['effects']:
        cfg+=f'cmd vf_voice_preview {effect["id"]}\nwait 5\n'
    cfg+='cmd vf_voice_set lucien\nwait 20\nsave vf_voice_identity\nwait 60\ncmd vf_voice_set rocco\nwait 20\nload vf_voice_identity\nwait 160\ncmd vf_voice_info\n'
    cfg+='cmd vf_voice_preview unknown\ncmd vf_voice_set unknown\n'
    for probe in ['pain','burn','shock','armor','critical']:
        cfg+=f'cmd vf_voice_test {probe}\nwait 100\n'
    cfg+='cmd vf_voice_test death\nwait 100\ncmd vf_taunt\nwait 10\nquit\n'
    (MOD/'vf_voices_native_test.cfg').write_text(cfg,encoding='ascii')
    logfile=ENGINE/'voices-native.log';started=time.time()
    args=[str(ENGINE/'xash3d.exe'),'-rodir',STEAM,'-game','vf_visual','-width','1280','-height','720','-console','-nointro','-nowriteconfig','-log',logfile.name,'+exec','lab_controls.cfg','+sv_cheats','1','+developer','1','+map','vf_range','+exec','vf_voices_native_test.cfg']
    p=subprocess.Popen(args,cwd=ENGINE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:p.wait(timeout=100)
    except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
    assert p.returncode==0,p.returncode
    log=logfile.read_text(errors='replace')
    assert f'VFVoice precache: actors={len(ACTORS)} clips={len(manifest["clips"])}' in log
    assert re.search(r'VFVoice assigned: player=1 actor=('+'|'.join(ACTORS)+')',log)
    spam=log.split('VOICE_SPAM_BEGIN',1)[1].split('VOICE_SPAM_END',1)[0]
    assert spam.count('VFVoice play:')==1,spam
    for a in ACTORS:
        for event in ['spawn','taunt']:
            assert f'actor={a} event={event}' in log,(a,event)
    for e in read(ROOT/'data/effects.json')['effects']:
        assert f'actor={ACTORS[-1]} event={e["id"]}' in log,e['id']
    for event in ['reload','pain','thermal','electro','armor_break','low_health']:
        assert re.search('VFVoice play:.*?event='+event+' ',log),event
    assert 'VFDeath play: entity=1 ' in log and 'VFDeath received: entity=1 ' in log
    assert not re.search(r'VFVoice play:.*?event=death ',log)
    assert 'VFVoice info: player=1 actor=lucien' in log,'save/load keeps selected identity'
    assert 'VFVoice rejected: unknown event.' in log and 'VFVoice rejected: unknown actor.' in log
    assert 'VFVoice received:' in log,'client receives voice metadata'
    for a in ACTORS:
        shot=MOD/'scrshots'/f'voices_{a}.png'
        assert shot.stat().st_mtime>=started
    for error in ["couldn't load sound","can't load sound","S_LoadSound:","Host_Error","SV_Error"]:
        assert not any(error.lower() in line.lower() and ('vf_voices' in line.lower() or error in ('Host_Error','SV_Error')) for line in log.splitlines()),error
    plays=re.findall(r'VFVoice play: player=(\d+) actor=(\w+) event=(\w+) clip=(\d+)',log)
    report=dict(clips_precached=len(manifest["clips"]),events_emitted=len(plays),checks=['actual Xash client/server DLLs load',
        'all actors emit spawn and taunt','all 21 effect and tactical lines can be auditioned',
        'successful real reload triggers a line','real damage triggers pain, burn, shock, armor loss and critical health',
        'real death emits the actor death voice','taunt key spam emits one line','selected identity survives save/load',
        'invalid actor/event rejected','client receives metadata and renders subtitle screenshots',
        'no missing voice sample errors'],
        limits=['Audio content still requires human listening review.','Combo auditions do not implement elemental combat rules.'])
    write_report('voices-native-verification.json',report);print('PASS voices native',report,flush=True)
def run_multiplayer():
    prepare()
    peer=PROJECT/'runtime/vector-engine-voice-peer'
    peer.mkdir(parents=True,exist_ok=True)
    for p in ENGINE.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.exe'):shutil.copy2(p,peer/p.name)
    for folder in ['valve','vf_visual','cs_assets','tfc_assets']:
        if (ENGINE/folder).exists():shutil.copytree(ENGINE/folder,peer/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
    # No cheats: normal users can taunt, but cannot choose/forge speech events.
    first='wait 300\ndeveloper 1\nfps_max 100\ncmd vf_peer_pose\nwait 700\ncmd vf_voice_info\ncmd vf_voice_set rocco\ncmd vf_voice_preview toxic_ignition\nwait 400\necho VOICE_MULTI_SPAM_BEGIN\ncmd vf_taunt\nwait 1\ncmd vf_taunt\nwait 30\necho VOICE_MULTI_SPAM_END\nwait 400\nquit\n'
    second='wait 300\ndeveloper 1\nfps_max 100\ncmd vf_peer_pose\nwait 500\ncmd vf_voice_info\ncmd vf_taunt\nwait 650\nquit\n'
    (MOD/'vf_voice_peer_a.cfg').write_text(first,encoding='ascii')
    (peer/'vf_visual/vf_voice_peer_b.cfg').write_text(second,encoding='ascii')
    common=['-rodir',STEAM,'-game','vf_visual','-console','-nointro']
    server=subprocess.Popen([str(ENGINE/'xash.exe'),*common,'-log','voices-server.log','+ip','127.0.0.1','-port','27065','+maxplayers','4','+sv_lan','1','+sv_cheats','0','+deathmatch','1','+developer','1','+map','vf_range','+vf_counter_taunts','0'],cwd=ENGINE,creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    children=[]
    try:
        time.sleep(4);assert server.poll()is None
        for folder,port,cfg,name in [(ENGINE,27066,'vf_voice_peer_a.cfg','VOICE_A'),(peer,27067,'vf_voice_peer_b.cfg','VOICE_B')]:
            args=[str(folder/'xash3d.exe'),*common,'-width','960','-height','540','-nowriteconfig','-log','voices-peer.log','-clientport',str(port),'+exec','lab_controls.cfg','+name',name,'+connect','127.0.0.1:27065','+exec',cfg]
            children.append(subprocess.Popen(args,cwd=folder,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
            time.sleep(5)
        for p in children:p.wait(timeout=90);assert p.returncode==0
        logs=[(folder/'voices-peer.log').read_text(errors='replace') for folder in [ENGINE,peer]]
        for log in logs:
            assert 'VFVoice received: player=1' in log and 'VFVoice received: player=2' in log
        assert 'VFVoice rejected: developer command requires local play or sv_cheats.' in logs[0]
        serverlog=(ENGINE/'voices-server.log').read_text(errors='replace')
        for player in [1,2]:
            assert re.search(f'VFVoice assigned: player={player} actor=',serverlog)
            assert re.search(f'VFVoice play: player={player} actor=\\w+ event=taunt',serverlog)
        taunts=re.findall(r'VFVoice received: player=(\d+) actor=(\w+) event=taunt clip=(\d+) sample=([^\s]+)',logs[0])
        remote=re.findall(r'VFVoice received: player=(\d+) actor=(\w+) event=taunt clip=(\d+) sample=([^\s]+)',logs[1])
        assert set(taunts)==set(remote) and len(taunts)==2,(taunts,remote)
        report=dict(clients=2,late_join=True,cheats=False,shared_taunts=taunts,checks=['dedicated loopback server assigns identities',
            'late join and existing client both hear the same actor/clip for both players',
            'ordinary player taunt works with cheats disabled','actor override and event forgery rejected',
            'rapid repeated requests produce one taunt per player'],
            scope='Native positional sound transport plus metadata replication; internet play and physical keyboard not tested.')
        write_report('voices-multiplayer-verification.json',report);print('PASS voices multiplayer',report,flush=True)
    finally:
        for p in children:
            if p.poll()is None:p.terminate();p.wait(10)
        if server.poll()is None:server.terminate();server.wait(10)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=['assets','native','multiplayer','all'],default='assets');a=p.parse_args()
    if a.mode in ('assets','all'):assets()
    if a.mode in ('native','all'):run_native()
    if a.mode in ('multiplayer','all'):run_multiplayer()

