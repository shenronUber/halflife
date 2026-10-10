"""One bounded loopback check of the authored remote R-01 on two real clients.
Uses isolated engine/mod directories; the installed release binaries stay intact.
"""
import os,json,shutil,subprocess,time,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
PROJECT=ROOT.parent
BASE=PROJECT/'runtime/vector-engine'
OUT=ROOT/'build/animation-native'


def shared_copy(source,target):
    if not Path(target).exists():os.link(source,target)
    return target


def stage(name,server=None,client=None):
    engine=OUT/name;mod=engine/'vf_animation';engine.mkdir(parents=True,exist_ok=True)
    for path in BASE.iterdir():
        if path.is_file() and path.suffix.lower() in ('.dll','.exe'):shutil.copy2(path,engine/path.name)
    # Shared immutable fallback resources; all writes go into vf_animation.
    for folder in ('valve','tfc_assets','vf_visual'):
        shutil.copytree(BASE/folder,engine/folder,dirs_exist_ok=True,copy_function=shared_copy,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
    for folder in ('cl_dlls','dlls','vf','models/vf_r01','models/vf_skins','scrshots'):(mod/folder).mkdir(parents=True,exist_ok=True)
    shutil.copy2(client or ROOT/'build/client/client.dll',mod/'cl_dlls/client.dll')
    shutil.copy2(server or ROOT/'build/server/hl.dll',mod/'dlls/hl.dll')
    from release import check_native_interface
    check_native_interface(BASE,Path(client or ROOT/'build/client/client.dll'))
    for path in (ROOT/'generated/r01').glob('*.mdl'):shutil.copy2(path,mod/'models/vf_r01'/path.name)
    for path in (ROOT/'generated/third-person').glob('*.mdl'):shutil.copy2(path,mod/'models/vf_r01'/path.name)
    for path in (ROOT/'generated/personas').glob('*.mdl'):shutil.copy2(path,mod/'models/vf_skins'/path.name)
    shutil.copytree(ROOT/'generated/deaths',mod/'models/vf_deaths',dirs_exist_ok=True,ignore=shutil.ignore_patterns('*.smd','*.qc','*.bmp','*.log','manifest.json'))
    for name in ('equipment.txt','r01_styles.txt'):shutil.copy2(ROOT/'data'/name,mod/'vf'/name)
    shutil.copy2(ROOT/'generated/visual_skins/skins.txt',mod/'vf/skins.txt')
    from build_test_room import build as build_test_room
    (mod/'maps').mkdir(exist_ok=True)
    shutil.copy2(build_test_room(ensure=True),mod/'maps/vf_range.bsp')
    from death_voice_workshop import deploy as deploy_death_voices
    deploy_death_voices(mod)
    from build_death_sounds import deploy as deploy_death_sounds
    deploy_death_sounds(mod)
    (mod/'vf/native_engine.txt').write_text('isolated animation test\n')
    (mod/'gameinfo.txt').write_text('title "Vector Fields - Animation test"\nbasedir "valve"\nfallback_dir "vf_visual"\ngamedll "dlls/hl.dll"\ndllpath "cl_dlls"\ngamemode "normal"\nmax_edicts "2048"\n')
    return engine


def run():
    engines=[stage('a'),stage('b')]
    slots='receiver barrel muzzle feed chamber ammo projectile optic underbarrel grip power cooling'.split()
    initial='wait 220\ndeveloper 1\ncon_notifytime 0\nfps_max 60\ndefault_fov 45\nr_drawviewmodel 0\ncmd give weapon_crowbar\nweapon_9mmAR\nwait 20\nvf_reference\nwait 35\n'
    cfg=[]
    for index in range(2):
        finish='living-jungle' if index else 'medieval-forge'
        commands=initial+''.join(f'vf_item r01_{s}_{"arch_top" if index and s=="receiver" else "a"}__{finish}\nwait 1\n' for s in slots)
        commands+='vf_commit\nwait 35\nvf_character\nvf_character\nwait 20\ncmd vf_peer_pose\ngod\ncmd vf_body_info\ncmd vf_model_info\n'
        if index==0:
            # One observer; sampling around the actual received sequence avoids
            # depending on window focus or matching the clients' frame clocks.
            commands+='wait 120\n'
            for sample in range(60):commands+=f'wait 20\necho CAPTURE_{sample:02}\nvf_engine_stats\nscreenshot scrshots/reload_{sample:02}.png\n'
            commands+='quit\n'
        else:
            commands+='wait 140\n+attack\nwait 8\n-attack\nwait 12\n+reload\nwait 2\n-reload\nwait 25\necho RELOAD_STANDING\ncmd vf_reload_info\nwait 100\necho RELOAD_FINISHED\ncmd vf_reload_info\n'
            commands+='+reload\nwait 4\n-reload\nwait 20\necho FULL_CLIP_IGNORED\ncmd vf_reload_info\n'
            commands+='+attack\nwait 8\n-attack\nwait 12\n+duck\nwait 12\n+reload\nwait 2\n-reload\n+moveleft\nwait 20\n-moveleft\necho RELOAD_CROUCHED\ncmd vf_reload_info\nwait 10\n-duck\nwait 12\necho RELOAD_STOOD_UP\ncmd vf_reload_info\nwait 100\n'
            commands+='cmd vf_peer_pose\n+attack\nwait 8\n-attack\nwait 12\n+reload\nwait 2\n-reload\nwait 20\ncmd weapon_crowbar\nwait 20\necho RELOAD_HOLSTERED\ncmd vf_reload_info\nweapon_9mmAR\nwait 100\ncmd vf_body_info\ncmd vf_model_info\nvf_engine_stats\nwait 160\nquit\n'
        (engines[index]/'vf_animation/animation_test.cfg').write_text(commands,encoding='ascii')
    common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-console','-nointro']
    server=subprocess.Popen([str(engines[0]/'xash.exe'),*common,'-log','animation-server.log','+ip','127.0.0.1','-port','27065','+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','1','+map','vf_range'],cwd=engines[0],creationflags=subprocess.CREATE_NO_WINDOW)
    children=[];started=time.time()
    try:
        time.sleep(3);assert server.poll() is None
        for i,engine in enumerate(engines):
            if i:time.sleep(4)
            children.append(subprocess.Popen([str(engine/'xash3d.exe'),*common,'-windowed','-width','1200','-height','800','-nowriteconfig','-log','animation-peer.log','-clientport',str(27066+i),'+name','Animator_'+str(i),'+connect','127.0.0.1:27065','+exec','animation_test.cfg'],cwd=engine))
        for child in children:child.wait(timeout=80);assert child.returncode==0
        verify(engines,started)
    finally:
        for p in children+[server]:
            if p.poll() is None:p.terminate();p.wait(10)

def verify(engines,started=None):
    logs=[(e/'animation-peer.log').read_text(errors='replace') for e in engines]
    for log in logs:
        assert 'VFState rejected' not in log
        assert 'VFThirdPerson player=' in log
        assert 'replace_carried=1' in log
        assert 'rejected=0' in log
    for log in logs:
        assert 'VFR01 state: player=1 first=2 optic=2 feed=2' in log
        assert 'VFR01 state: player=2 first=4 optic=4 feed=4' in log
        assert 'VFState player=1 skins=182,182,182,182,182' in log
        assert 'VFState player=2 skins=182,182,182,182,182' in log
    combined='\n'.join(logs)
    assert 'rig=models/vf_r01/r01_tp.mdl' in combined
    assert 'rig=models/vf_r01/r01_tp_top.mdl' in combined
    actor=logs[1]
    cases={}
    for marker in ['RELOAD_STANDING','RELOAD_FINISHED','FULL_CLIP_IGNORED','RELOAD_CROUCHED','RELOAD_STOOD_UP','RELOAD_HOLSTERED']:
        part=re.split(marker+r'\s*\n',actor)[-1]
        match=re.search(r'VFReload player=2 sequence=(\d+) frame=([\d.]+) gait=(\d+) active=(\d+) clip=(-?\d+) model=(\S+)',part)
        assert match,(marker,part[-1000:]);cases[marker]=match.groups()
    assert cases['RELOAD_STANDING'][0]=='77' and cases['RELOAD_STANDING'][3]=='1',cases
    assert cases['RELOAD_CROUCHED'][0]=='78' and cases['RELOAD_CROUCHED'][3]=='1',cases
    assert cases['RELOAD_STOOD_UP'][0]=='77' and cases['RELOAD_STOOD_UP'][3]=='1',cases
    assert float(cases['RELOAD_STOOD_UP'][1])>float(cases['RELOAD_CROUCHED'][1]),cases
    for marker in ['RELOAD_FINISHED','FULL_CLIP_IGNORED','RELOAD_HOLSTERED']:
        assert cases[marker][3]=='0' and int(cases[marker][0])<77,cases
    assert cases['RELOAD_FINISHED'][4]=='50' and cases['FULL_CLIP_IGNORED'][4]=='50',cases
    assert cases['RELOAD_HOLSTERED'][5]=='models/vf_skins/persona_rig.mdl',cases
    remote=re.findall(r'VFThirdPersonReload player=2 stage=(\d+) sequence=(\d+) frame=([\d.]+) gait=(\d+)',logs[0])
    assert {'1','2','3','4'}<=set(r[0] for r in remote),remote
    assert {'77','78'}<=set(r[1] for r in remote),remote
    assert any(r[3]=='6' for r in remote),remote
    assert 'model=models/vf_r01/r01_tp_top.mdl' in logs[0]
    assert 'model=models/player.mdl' not in logs[0], 'old per-frame Gordon override returned'
    captures=[]
    for sample,part in re.findall(r'CAPTURE_(\d+)\s*\n(.*?)(?=CAPTURE_|Log stopped|$)',logs[0],re.S):
        pose=re.search(r'VFPeerPose player=2 sequence=(77|78) frame=([\d.]+)',part)
        if pose and 50<float(pose[2])<210:
            path=engines[0]/'vf_animation/scrshots'/f'reload_{sample}.png'
            assert path.exists() and (started is None or path.stat().st_mtime>=started) and path.stat().st_size>1000;captures.append(str(path))
    assert captures,'observer must capture an actual received reload'
    assert 'VFBody player=2 mins=-16,-16,-36 maxs=16,16,36 rifle=1' in actor
    report=dict(clients=2,late_join=True,captures=captures,cases=cases,remote_reload_samples=remote,elapsed_seconds=round(time.time()-started,2) if started else None,verification_mode="live run" if started else "saved native run",checks=['remote modular R-01 rendered with independent finishes','server transmits standing and crouching reload sequences','reload frame advances across all four quarters on the observer','walking gait continues underneath reload','standing up preserves reload progress','full clip does not trigger reload; completion restores 50 rounds','holster cancels reload and restores compatible original body rig','collision hull remains unchanged','no rejected assemblies; GIGN fallback preserved','installed release binaries unchanged'],limits=['engaged posture remains an offline experiment','native captures do not replace artistic review of every equipment combination'])
    (OUT/'verification.json').write_text(json.dumps(report,indent=2));print('PASS remote R-01',json.dumps(report))

if __name__=='__main__':
    if '--verify' in sys.argv:verify([OUT/'a',OUT/'b'])
    else:run()
