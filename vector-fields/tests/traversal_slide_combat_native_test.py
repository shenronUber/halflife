"""Show actual sliding weapon actions and validate ammo, aim and seated legs."""
import hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from traversal_review_bundle import prepare_review,review_assets
from native_workspace import private_copy,remove_tree,SESSIONS,port
from release import check_native_interface
OUT=ROOT/'docs/validation/traversal/slide-combat';FPS=30

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(slide_feet=False,candidate=None,timeout=120):
    if slide_feet:
        from slide_feet_bundle import prepare_slide_feet
        engine,mod=prepare_slide_feet('slide-combat',build=candidate or ROOT/'build',engine_binaries=candidate/'engine' if candidate else ROOT.parent/'runtime/vector-engine')
    else:engine,mod=prepare_review('slide-combat')
    # Keep the installed core; exercise only the candidate renderer with the
    # new client/server. This is exactly the bundle subsequently delivered.
    candidate_path=candidate/'engine' if candidate else ROOT.parent/'runtime/vector-engine'
    private_copy(candidate_path/'ref_gl.dll',engine/'ref_gl.dll')
    metadata=json.loads((ROOT.parent/'runtime/vector-engine/vector-engine-build.json').read_text(encoding='utf-8-sig'))
    candidate=json.loads((candidate_path/'vector-engine-build.json').read_text(encoding='utf-8-sig'))
    for field in ('extension_version','traversal_renderer_version','status_viewmodel_version','body_renderer_version','renderer_sha256'):
        metadata[field]=candidate[field]
    metadata['binaries']['ref_gl.dll']=digest(engine/'ref_gl.dll').upper()
    (engine/'vector-engine-build.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    check_native_interface(engine,mod/'cl_dlls/client.dll')
    OUT.mkdir(parents=True,exist_ok=True);frames=mod/'scrshots/combat';frames.mkdir()
    lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','sys_timescale 1',
           f'host_framerate {1/FPS:.8f}',f'fps_max {FPS}','hud_draw 0','crosshair 1',
           'vf_voice_subtitles 0','sv_cheats 1','god','cmd give weapon_9mmAR',
           'cmd give ammo_9mmbox','weapon_9mmAR','wait 40','vf_reference 0','wait 30',
           'vf_commit','wait 35','vf_character','vf_character','wait 12']
    timeline=[];count=0
    for view in('first-person','third-person'):
        for action in('shoot','reload'):
            lines.extend(['-duck','-attack','-reload','-attack2','cam_command 2','+reload','wait 2','-reload','wait 65'])
            if action=='reload':lines.extend(['+attack','wait 5','-attack','wait 14'])
            lines.extend(['cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1'])
            if view=='third-person':lines.extend(['cam_snapto 1','cam_idealdist 75','cam_idealyaw 110','cam_idealpitch 8','cam_command 1'])
            timeline.append(dict(frame=count,view=view,gesture='slide',action=action))
            events={0:['+duck'],6:['+attack'],24:['-attack'],42:['-duck']}if action=='shoot'else{0:['+duck'],10:['+reload'],12:['-reload'],42:['-duck']}
            for i in range(110):
                lines.extend(events.get(i,[]))
                lines.extend([f'echo COMBAT_FRAME_{count:04}','cmd vf_traversal_info',
                              f'snapshot scrshots/combat/frame_{count:04}.png','wait 1'])
                count+=1
    # Exercise camera aim independently from momentum, including vertical aim.
    aim_cases=[(0,-30),(0,30),(90,0)]
    for index,(yaw,pitch)in enumerate(aim_cases):
        lines.extend(['-duck','-attack','-reload','wait 40','cmd vf_traversal_place 128 -750 36 0 400 0 0','wait 1',
                      '+duck','wait 9',f'vf_traversal_look {yaw} {pitch}','wait 7',f'echo COMBAT_AIM_{index}',
                      'cmd vf_traversal_info','wait 3','-duck','wait 40'])
    lines.append('quit')
    for part,start in enumerate(range(0,len(lines),140)):
        chunk=lines[start:start+140]
        if start+140<len(lines):chunk.append(f'exec combat_{part+1:03}.cfg')
        (mod/f'combat_{part:03}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game','vf_animation','-windowed','-width','960','-height','540','-console','-nointro','-nowriteconfig',
        '-log','combat.log','-port',str(port()),'-clientport',str(port()),'+sv_cheats','1','+developer','2','+maxplayers','1','+map','vf_traversal',
        '+exec','combat_000.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        process.wait(timeout=timeout);assert process.returncode==0
    finally:
        if process.poll()is None:process.terminate();process.wait(timeout=8)
    text=(engine/'combat.log').read_text(errors='replace');observations={}
    assert re.search(r'VFEngine: native extension v[34] connected',text),'Legacy avatar capture rejected'
    assert 'VF catalogue:'not in text,'Invalid equipment catalog; capture rejected'
    if slide_feet:
        body_phases=list(map(int,re.findall(r'VFFirstPersonBody parts=\d+ mask=\d+ phase=(\d+)',text)))
        assert 0 in body_phases and 5 in body_phases,'Equipped world body must also supply slide legs'
    for frame,block in re.findall(r'COMBAT_FRAME_(\d+)(.*?)(?=COMBAT_FRAME_|\Z)',text,re.S):
        row=re.search(r'VFTraversal phase=(\d+) state=\d+ origin=([\d.,-]+) velocity=[\d.,-]+ time=([\d.-]+) health=[\d.-]+ clip=(-?\d+) reload=(\d+) sequence=(\d+)',block)
        if row:
            p,origin,remaining,clip,reload,sequence=row.groups()
            poses=[dict(view=int(v),sequence=s,frame=float(f),barrel=list(map(float,b.split(','))),forward=float(dot),hip=list(map(float,h.split(','))),knee=list(map(float,k.split(','))))for v,s,f,b,dot,h,k in re.findall(r'VFSlideCombat view=(\d+) sequence=(\w+) frame=([\d.-]+) barrel=([\d.,-]+) forward=([\d.-]+) hip=([\d.,-]+) knee=([\d.,-]+)',block)]
            observations[int(frame)]=dict(phase=int(p),origin=list(map(float,origin.split(','))),remaining=float(remaining),clip=int(clip),reload=int(reload),sequence=int(sequence),poses=poses)
    paths=sorted(frames.glob('frame_*.png'));assert len(paths)==count==len(observations)
    for index,event in enumerate(timeline):
        rows=[observations[i]for i in range(event['frame'],event['frame']+110)]
        sliding=[r for r in rows if r['phase']==5];assert len(sliding)>25,event
        assert rows[-1]['phase']==0 and 200<rows[-1]['origin'][0]-128<500,event
        poses=[p for r in sliding[3:-3]for p in r['poses']if bool(p['view'])==(event['view']=='first-person')]
        assert len(poses)>15,('Missing actual rendered weapon poses',event)
        event['sliding_frames']=len(sliding);event['rendered_sequences']=sorted({p['sequence']for p in poses})
        if event['action']=='shoot':
            assert sliding[-1]['clip']<=sliding[0]['clip']-4,('No shots during slide',event,sliding)
            aim=[p['forward']for p in poses if 'aim' in p['sequence']or p['sequence']=='idle'or(event['view']=='first-person'and'shoot' in p['sequence'])]
            assert len(aim)>2 and min(aim)>(.995 if event['view']=='first-person'else .9999),('Rifle must point forwards while ready',event,aim)
            assert any('shoot' in p['sequence']or 'fire' in p['sequence']for p in poses),event
            event['shots_in_slide']=sliding[0]['clip']-sliding[-1]['clip'];event['minimum_ready_forward']=min(aim)
        else:
            assert any(r['reload']for r in sliding),('Reload did not start while sliding',event)
            assert not rows[-1]['reload'] and rows[-1]['clip']>sliding[0]['clip'],('Reload did not finish after slide',event)
            assert any('reload' in p['sequence']for p in poses),('Reload gesture missing',event)
            reload_frames=[p['frame']for p in poses if 'reload' in p['sequence']]
            assert max(reload_frames)-min(reload_frames)>5,('Reload animation clock stopped',event,reload_frames)
            event['reload_started_while_sliding']=True;event['completed_clip']=rows[-1]['clip']
        if event['view']=='third-person':
            planted=[(r,p)for r in sliding if .32<r['remaining']<.85 for p in r['poses']if not p['view']]
            assert len(planted)>5,event
            relative=[]
            for r,p in planted:
                assert 5<p['hip'][2]<12 and 0<p['knee'][2]<6,('Seated lower body lost',p)
                relative.append([p['hip'][i]-r['origin'][i]for i in range(3)]+[p['knee'][i]-p['hip'][i]for i in range(3)])
            # Frame/server interpolation may shift along travel, never rotate
            # the folded knee or move its height when shooting/reloading.
            import numpy as np
            a=np.array(relative);assert np.ptp(a[:,2])<.02 and np.max(np.ptp(a[:,3:],axis=0))<.02,(event,a)
    import math
    aimed=[]
    for index,block in re.findall(r'COMBAT_AIM_(\d+)(.*?)(?=COMBAT_AIM_|\Z)',text,re.S):
        yaw,pitch=aim_cases[int(index)];yaw,pitch=math.radians(yaw),math.radians(pitch)
        direction=[math.cos(pitch)*math.cos(yaw),math.cos(pitch)*math.sin(yaw),-math.sin(pitch)]
        assert re.search(r'VFTraversal phase=5 ',block),('Aim must be checked during slide',index)
        barrels=[list(map(float,row.split(',')))for row in re.findall(r'VFSlideCombat view=0 sequence=ref_aim_mp5 frame=[\d.-]+ barrel=([\d.,-]+)',block)]
        dots=[sum(a*b for a,b in zip(barrel,direction))for barrel in barrels[:3]]
        assert len(dots)>=2 and min(dots)>.9999,('Rendered gun must follow yaw and pitch',index,dots)
        aimed.append(dict(yaw=aim_cases[int(index)][0],pitch=aim_cases[int(index)][1],minimum_alignment=min(dots)))
    assert len(aimed)==len(aim_cases)
    report=dict(source='Live GoldSrc renderer',fps=FPS,width=960,height=540,frames=count,
        frames_directory=str(frames),timeline=timeline,combat=True,
        aim_tests=aimed,
        renderer_sha256=digest(engine/'ref_gl.dll'),client_sha256=digest(mod/'cl_dlls/client.dll'),
        server_sha256=digest(mod/'dlls/hl.dll'),engine_core={name:digest(engine/name)for name in('xash3d.exe','xash.dll','xash.exe','SDL2.dll')},
        assets=review_assets(mod),world_slide_body=slide_feet)
    manifest=OUT/'capture.json';manifest.write_text(json.dumps(report,indent=2))
    blender=ROOT.parent/'devtools/blender/blender-4.5.14-windows-x64/blender.exe'
    subprocess.run([str(blender),'--background','--factory-startup','--python-exit-code','1','--python',
        str(ROOT/'animation-workshop/encode-traversal-transitions.py'),'--','--manifest',str(manifest)],
        check=True,stdout=(OUT/'encoding.log').open('w'),stderr=subprocess.STDOUT)
    for event in timeline:
        for offset in(5,18,28):shutil.copy2(paths[event['frame']+offset],frames.parent/(event['view']+'-'+event['action']+'-'+str(offset)+'.png'))
    report=json.loads(manifest.read_text());report.pop('frames_directory');report['temporary_pngs_removed']=count
    manifest.write_text(json.dumps(report,indent=2));shutil.copy2(engine/'combat.log',OUT/'native.log')
    remove_tree(frames,SESSIONS)
    print('PASS sliding combat',json.dumps(timeline),flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--slide-feet',action='store_true');parser.add_argument('--candidate-dir',type=Path);parser.add_argument('--timeout',type=float,default=120);args=parser.parse_args();run(args.slide_feet,args.candidate_dir,args.timeout)
