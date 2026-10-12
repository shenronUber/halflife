"""Review installed climb, slide and release in both views, without rebuilding.

One disposable native_workspace session shares frozen resources. Encode before
retiring it; keep only representative PNGs, the log, manifest and final video.
"""
import argparse,hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from traversal_multiplayer_test import prepare
from native_workspace import remove_tree,SESSIONS,EVIDENCE

OUT=ROOT/'docs/validation/traversal/transitions'
FPS=30


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def run(existing=None,focused=False,slide_only=False):
    global OUT
    if slide_only:OUT=ROOT/'docs/validation/traversal/short-slide'
    if existing:
        engine=Path(existing).resolve();mod=engine/'vf_animation'
    else:engine,mod=prepare('transitions')
    OUT.mkdir(parents=True,exist_ok=True)
    frames=mod/'scrshots/transitions'
    if not existing:frames.mkdir()
    lines=['wait 180','developer 1','con_notifytime -1','gl_vsync 0',
           'sys_timescale 1',f'host_framerate {1/FPS:.8f}',f'fps_max {FPS}',
           'hud_draw 0','crosshair 0','vf_voice_subtitles 0','sv_cheats 1',
           'cmd give weapon_9mmAR','cmd give ammo_9mmbox','weapon_9mmAR',
           'wait 40','vf_reference 0','wait 30','vf_commit','wait 35',
           'vf_character','vf_character','wait 12']
    timeline=[];count=0

    def capture(n,events=None):
        nonlocal count
        for i in range(n):
            lines.extend((events or {}).get(i,[]))
            lines.extend([f'echo REVIEW_FRAME_{count:04}', 'cmd vf_traversal_info',
                          f'snapshot scrshots/transitions/frame_{count:04}.png','wait 1'])
            count+=1

    for view in ('first-person','third-person'):
        for gesture in ('climb','slide','drop'):
            if slide_only and gesture!='slide':continue
            if focused and (view,gesture)not in [('first-person','climb'),('third-person','slide')]:continue
            timeline.append(dict(frame=count,view=view,gesture=gesture))
            lines.extend(['-jump','-duck','-attack','-attack2','cam_command 2'])
            if gesture=='slide':
                lines.extend(['cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1'])
            else:
                lines.extend(['cmd vf_traversal_place 238 0 54 0','wait 1',
                              '+jump','wait 18','-jump','wait 12'])
            if view=='third-person':
                lines.extend(['cam_snapto 1','cam_idealdist '+('100'if gesture=='slide'else'120'),
                              'cam_idealyaw '+('110'if gesture=='slide'else'50'),
                              'cam_idealpitch 8','cam_command 1'])
            if gesture=='slide':
                capture(95,{0:['+duck'],72:['-duck']})
            else:
                capture(60 if gesture=='climb'else 40,
                        {10:['+jump'if gesture=='climb'else'+duck'],
                         12:['-jump'if gesture=='climb'else'-duck']})
    lines.append('quit')
    # Stay below the engine's 32 KiB command buffer, including snapshot paths.
    for part,start in enumerate(range(0,len(lines),140)):
        chunk=lines[start:start+140]
        if start+140<len(lines):chunk.append(f'exec review_{part+1:03}.cfg')
        (mod/f'review_{part:03}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
    if not existing:process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','1',
        '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation',
        '-windowed','-width','960','-height','540','-console','-nointro',
        '-nowriteconfig','-log','transitions.log','+sv_cheats','1','+developer','1',
        '+maxplayers','1','+map','vf_traversal','+exec','review_000.cfg'],
        cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        if existing:process=None
        else:
            process.wait(timeout=120)
            assert process.returncode==0,process.returncode
    finally:
        if process and process.poll()is None:process.terminate();process.wait(timeout=8)
    paths=sorted(frames.glob('frame_*.png'));assert len(paths)==count,(len(paths),count)
    text=(engine/'transitions.log').read_text(errors='replace')
    observations={}
    for frame,block in re.findall(r'REVIEW_FRAME_(\d+)(.*?)(?=REVIEW_FRAME_|\Z)',text,re.S):
        row=re.search(r'VFTraversal phase=(\d+) state=\d+ origin=([\d.,-]+) velocity=[\d.,-]+ time=([\d.-]+) health=[\d.-]+ clip=(-?\d+)',block)
        if row:
            phase,origin,remaining,clip=row.groups()
            observations[int(frame)]=dict(phase=int(phase),remaining=float(remaining),
                origin=list(map(float,origin.split(','))),clip=int(clip))
    assert len(observations)==count,(len(observations),count)
    for i,event in enumerate(timeline):
        end=timeline[i+1]['frame']if i+1<len(timeline)else count
        rows=[observations[f]for f in range(event['frame'],end)]
        expected={'climb':4,'slide':5,'drop':6}[event['gesture']]
        assert any(r['phase']==expected for r in rows),event
        assert rows[-1]['phase']==0,(event,rows[-1])
        event['phase_frames']={str(p):sum(r['phase']==p for r in rows)for p in sorted({r['phase']for r in rows})}
        event['final_origin']=rows[-1]['origin']
        if event['gesture']=='climb':assert rows[-1]['origin'][2]>130,event
        if event['gesture']=='slide':
            distance=rows[-1]['origin'][0]-128
            assert 200<distance<500,(event,distance)
            event['distance']=distance
    binary=ROOT.parent/'runtime/vector-engine'if existing else engine
    assets_mod=binary/'vf_visual'if existing else mod
    report=dict(source='Current compiled assets / live local GoldSrc renderer',
        fps=FPS,simulation_step=1/FPS,width=960,height=540,frames=count,
        frames_directory=str(frames),timeline=timeline,
        renderer_sha256=digest(binary/'ref_gl.dll'),
        client_sha256=digest(assets_mod/'cl_dlls/client.dll'),server_sha256=digest(assets_mod/'dlls/hl.dll'),
        assets={str(p.relative_to(assets_mod)):digest(p)for folder in('vf_traversal','vf_r01')
                for p in(assets_mod/'models'/folder).glob('*.mdl')},
        builds=0,focused=focused,slide_only=slide_only,workspace='One temporary engine; content-addressed immutable media')
    manifest=OUT/'capture.json';manifest.write_text(json.dumps(report,indent=2))
    blender=ROOT.parent/'devtools/blender/blender-4.5.14-windows-x64/blender.exe'
    subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1',
                    '--python',str(Path(__file__).with_name('encode-traversal-transitions.py')),
                    '--','--manifest',str(manifest)],
                   check=True,stdout=(OUT/'encoding.log').open('w'),stderr=subprocess.STDOUT)
    # Preserve a bounded set of pictures. The encoded video contains every frame.
    stills=[]
    for event in timeline:
        for offset in (10,18,28):
            source=paths[event['frame']+offset]
            target=frames.parent/f"{event['view']}-{event['gesture']}-{offset}.png"
            shutil.copy2(source,target);stills.append(target.name)
    report=json.loads(manifest.read_text());report.pop('frames_directory')
    report['retained_stills']=stills;report['temporary_pngs_removed']=count
    manifest.write_text(json.dumps(report,indent=2))
    # Checked removal applies only to this process's generated frame directory.
    remove_tree(frames,EVIDENCE if existing else SESSIONS)
    shutil.copy2(engine/'transitions.log',OUT/'native.log')
    print('PASS transitions review',json.dumps(dict(video=report['video'],frames=count,
          builds=0,temporary_pngs_removed=count,gestures=timeline)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--existing',type=Path)
    parser.add_argument('--focused',action='store_true')
    parser.add_argument('--slide-only',action='store_true');args=parser.parse_args()
    run(args.existing,args.focused,args.slide_only)
