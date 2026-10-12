"""Record the real multiplayer renderer from a stationary external camera.

Only isolated local game instances and their configuration files are used.
The camera's PNG frames govern the actor's commands, keeping the demonstration
aligned even when rendering and screenshot compression take longer.
"""
import argparse,hashlib,json,math,os,re,shutil,subprocess,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from traversal_multiplayer_test import prepare

OUT=ROOT/'docs/validation/traversal/video'
PORT='27785'
FPS=12


def atomic(path,text):
    temporary=path.with_suffix('.next')
    temporary.write_text(text,encoding='ascii')
    # The game briefly opens this file on every polling tick on Windows.
    deadline=time.monotonic()+2
    while True:
        try:os.replace(temporary,path);return
        except PermissionError:
            if time.monotonic()>deadline:raise
            time.sleep(.005)


def run(preview=False,renderer=None):
    OUT.mkdir(parents=True,exist_ok=True)
    renderer=Path(renderer) if renderer else ROOT.parent/'runtime/vector-engine'
    def prepared(name):
        engine=ROOT/'build/animation-native'/('traversal-video-'+name);mod=engine/'vf_animation'
        required=[(renderer/n,engine/n)for n in('xash3d.exe','xash.exe','xash.dll','ref_gl.dll','SDL2.dll')]
        required.extend((ROOT/'build'/kind/file,mod/dest/file)for kind,dest,file in
            [('client','cl_dlls','client.dll'),('server','dlls','hl.dll')])
        for source,dest in [('traversal','vf_traversal'),('third-person','vf_r01'),('r01','vf_r01'),('personas','vf_skins')]:
            required.extend((p,mod/'models'/dest/p.name)for p in(ROOT/'generated'/source).glob('*.mdl'))
        if (mod/'gameinfo.txt').exists() and all(b.exists() and hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest()for a,b in required):
            return engine,mod
        return prepare('video-'+name,renderer)
    pairs=[prepared(n)for n in ('server','actor','camera')]
    (server,server_mod),(actor,actor_mod),(camera,camera_mod)=pairs
    frames=camera_mod/'scrshots'/('ledge-preview'if preview else 'ledge-video')
    frames.mkdir(parents=True,exist_ok=True)
    # Reruns use another directory instead of replacing review evidence.
    if any(frames.glob('frame_*.png')):
        frames=frames.with_name(frames.name+'-'+str(time.time_ns()))
        frames.mkdir()
    timeline=[dict(frame=0,yaw=0.,shoot=False,label='Suspension a deux mains')]
    events=[(0,0.,False,False)]
    if preview:
        count=8
    else:
        events.extend([(12,0.,False,True),(15,0.,False,False)])
        timeline.append(dict(frame=12,yaw=0.,shoot=False,label='Sortie de l arme'))
        cursor=24;previous=0.
        for target in (0.,45.,90.,135.,180.,225.,270.,315.,360.):
            if target!=previous:
                for step in range(1,7):
                    events.append((cursor+step-1,previous+(target-previous)*step/6,False,False))
                cursor+=6
            allowed=abs((target+180)%360-180)>=75
            timeline.append(dict(frame=cursor,yaw=target%360,shoot=True,fire_allowed=allowed,label='Tir' if allowed else 'Garde'))
            events.extend([(cursor,target,True,False),(cursor+4,target,False,False)])
            cursor+=15;previous=target
        events.append((cursor,0.,False,True));events.append((cursor+3,0.,False,False))
        timeline.append(dict(frame=cursor,yaw=0.,shoot=False,label='Retour a deux mains'))
        count=cursor+12
    events.sort(key=lambda e:e[0])
    control=actor_mod/'video_control.cfg';atomic(control,'vf_traversal_look 0 0\n-attack\n-attack2\n')
    (actor_mod/'video_loop.cfg').write_text('exec video_control.cfg\nwait 1\nexec video_loop.cfg\n',encoding='ascii')
    init=('wait 180\nfps_max 30\ndeveloper 1\ncon_notifytime -1\nvf_voice_subtitles 0\n'
          'vf_reference 0\nwait 30\nvf_commit\nwait 35\nvf_character\nvf_character\nwait 12\n')
    actor_script=(init+'cmd give weapon_9mmAR\nweapon_9mmAR\nwait 20\n'
        'cmd vf_traversal_place 238 0 54 0\nwait 1\n+jump\nwait 22\n-jump\nwait 40\n'
        'echo VIDEO_ACTOR_READY\ncmd vf_traversal_info\nexec video_loop.cfg\n')
    (actor_mod/'video_actor.cfg').write_text(actor_script,encoding='ascii')
    camera_lines=[init,'r_drawviewmodel 0','hud_draw 0','crosshair 0','default_fov 52',
        'cmd vf_traversal_place 132 -132 36 49.4','vf_traversal_look 49.4 -0.7','wait 35','con_notifytime -1']
    # GoldSrc's command buffer is 32 KiB; chain small capture scripts.
    camera_lines.append('exec video_frames_000.cfg')
    for start in range(0,count,100):
        chunk=[]
        for i in range(start,min(count,start+100)):
            chunk.extend([f'echo VIDEO_FRAME_{i:05}', 'vf_engine_stats',
                f'snapshot scrshots/{frames.name}/frame_{i:05}.png','wait 1'])
        chunk.extend(['exec video_frames_'+f'{start+100:03}'+'.cfg']if start+100<count else ['wait 2','quit'])
        (camera_mod/f'video_frames_{start:03}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
    (camera_mod/'video_camera.cfg').write_text('\n'.join(camera_lines)+'\n',encoding='ascii')
    common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-nointro','-nowriteconfig']
    processes=[]
    def launch(engine,name,extra):
        log=engine/(name+'.log')
        if log.exists():log.unlink()
        p=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2',*common,'-windowed','-width','1280','-height','720',
            '-log',log.name,'-clientport',str(27786+len(processes)),'+name',name,
            '+connect','127.0.0.1:'+PORT,'+exec',extra],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
        processes.append(p);return p,log
    server_log=server/'video-server.log'
    if server_log.exists():server_log.unlink()
    dedicated=subprocess.Popen([str(server/'xash.exe'),'-ip','127.0.0.1','-noip6',*common,'-log',server_log.name,'+ip','127.0.0.1',
        '-port',PORT,'+maxplayers','3','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+map','vf_traversal'],
        cwd=server,creationflags=subprocess.CREATE_NO_WINDOW)
    started=time.monotonic()
    try:
        time.sleep(1.5)
        actor_process,actor_log=launch(actor,'VideoActor','video_actor.cfg')
        deadline=time.monotonic()+35
        while not actor_log.exists() or 'VIDEO_ACTOR_READY'not in actor_log.read_text(errors='replace'):
            assert actor_process.poll() is None,'actor exited before hanging'
            if time.monotonic()>deadline:raise TimeoutError('actor setup')
            time.sleep(.15)
        camera_process,camera_log=launch(camera,'VideoCamera','video_camera.cfg')
        current=0;last_frame=-1;deadline=time.monotonic()+240;release_attack=None;current_yaw=0.
        while camera_process.poll() is None:
            paths=list(frames.glob('frame_*.png'))
            last_frame=max((int(p.stem[-5:])for p in paths),default=-1)
            while current<len(events) and events[current][0]<=last_frame:
                frame,yaw,shoot,arm=events[current]
                atomic(control,f'vf_traversal_look {yaw:.3f} 0\n'+('+attack\n'if shoot else '-attack\n')+('+attack2\n'if arm else '-attack2\n'))
                current_yaw=yaw
                if shoot:release_attack=time.monotonic()+.18
                print('VIDEO EVENT',frame,round(yaw,1),'shoot'if shoot else 'hold','arm'if arm else '',flush=True)
                current+=1
            if release_attack is not None and time.monotonic()>=release_attack:
                atomic(control,f'vf_traversal_look {current_yaw:.3f} 0\n-attack\n-attack2\n');release_attack=None
            if time.monotonic()>deadline:raise TimeoutError(f'camera recording at frame {last_frame}')
            time.sleep(.015)
        assert camera_process.returncode==0,camera_process.returncode
        paths=sorted(frames.glob('frame_*.png'));assert len(paths)==count,(len(paths),count)
        from PIL import Image
        assert all(Image.open(p).size==(1280,720)for p in(paths[0],paths[len(paths)//2],paths[-1]))
        text=camera_log.read_text(errors='replace')
        assert 'VFState rejected'not in text and 'rejected=0'in text
        anchors=[(int(p),[float(v)for v in(hip+','+knee).split(',')])for p,hip,knee in re.findall(
            r'VFTraversalAnchor phase=(\d+) hip=([\d.,-]+) knee=([\d.,-]+)',text)]
        assert len(anchors)>count*.7,('missing rendered body',len(anchors),count)
        from traversal_pose_telemetry import anchored_lean
        lean=anchored_lean(text)
        error=lean['max_world_error']
        if not preview:assert lean['left_lean_samples']>20 and lean['maximum_lift']>2.9,lean
        if not preview:
            from traversal_torso_clearance import native_clearance
            clearance=native_clearance(text,camera_mod/'models/vf_skins/persona_scout.mdl',camera_mod/'models/vf_r01/r01_tp.mdl')
            assert {85+i for i in range(8)}<=set(map(int,re.findall(r'VFPeerTraversal player=1 phase=3 sequence=(\d+)',text)))
            rows=[tuple(map(float,row))for row in re.findall(r'VFTraversalBody phase=(\d+) sequence=(\d+) left_error=([\d.-]+) right_error=([\d.-]+) gun_error=([\d.-]+) body_shift=([\d.-]+) face_error=([\d.-]+)',text)]
            assert all(0<=r[2]<.01 and(r[0]!=3 or 0<=r[4]<.01)for r in rows)
            atomic(control,'-attack\n-attack2\ncmd vf_traversal_info\nwait 1\necho VIDEO_FINAL\n')
            time.sleep(.2)
        report=dict(source='Live GoldSrc multiplayer renderer, stationary remote client',fps=FPS,width=1280,height=720,camera_fov=52,
            frames=len(paths),frames_directory=str(frames),timeline=timeline,wall_clock_seconds=round(time.monotonic()-started,2),
            planted_lower_body_samples=len(anchors),max_waist_knee_world_error=error,
            left_lean=lean,
            client_sha256=hashlib.sha256((camera_mod/'cl_dlls/client.dll').read_bytes()).hexdigest(),
            server_sha256=hashlib.sha256((server_mod/'dlls/hl.dll').read_bytes()).hexdigest(),
            renderer_sha256=hashlib.sha256((camera/'ref_gl.dll').read_bytes()).hexdigest())
        report['playback']='Accelerated PNG-frame recording; all poses are live game frames'
        if not preview:report['torso_clearance']=clearance
        clip=re.findall(r'VFTraversal phase=\d+ .*?clip=(-?\d+)',actor_log.read_text(errors='replace'))
        if not preview and len(clip)>=2:
            assert 0<int(clip[-1])<int(clip[0]),('live firing clip',clip)
            report['clip_before_after']=[int(clip[0]),int(clip[-1])]
        name='preview'if preview else 'capture'
        (OUT/(name+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        shutil.copy2(paths[0],OUT/(name+'-first.png'));shutil.copy2(paths[len(paths)//2],OUT/(name+'-middle.png'))
        for log in(actor_log,camera_log,server_log):shutil.copy2(log,OUT/log.name)
        print('PASS LIVE VIDEO CAPTURE',json.dumps(report),flush=True)
        return report
    finally:
        # Stop only the processes owned by this recording.
        for process in[*processes,dedicated]:
            if process.poll() is None:process.terminate();process.wait(timeout=8)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true')
    parser.add_argument('--revision',default='')
    parser.add_argument('--renderer',type=Path)
    args=parser.parse_args()
    assert all(c.isalnum() or c=='-' for c in args.revision),'invalid video revision'
    if args.revision:OUT=OUT.with_name('video-'+args.revision)
    run(args.preview,args.renderer)
