"""Capture every start-up frame and measure torso continuity in the real engine."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import integration_native_test as audit
from native_workspace import port

def frame_steps(log,cases):
    pattern=r'VFPlayerPose source=render entity=1 sequence=\d+ frame=[\d.]+.*? box=(\d+) matrix=([-\d.,]+)'
    def matrices(block):return {int(i):np.array(list(map(float,v.split(',')))).reshape(3,4)for i,v in re.findall(pattern,block)}
    results=[]
    for name in cases:
        before=matrices(log.split(f'RELOAD_{name}_BEFORE ')[1].split(f'RELOAD_{name}_START ')[0])
        last={i:before[0][:,:3].T@before[i][:,:3]for i in [7,8,9]};steps=[]
        for frame in range(16):
            block=log.split(f'RELOAD_{name}_FRAME_{frame} ')[1].split(f'RELOAD_{name}_'+(f'FRAME_{frame+1}'if frame<15 else 'END')+' ')[0]
            rows=matrices(block);now={i:rows[0][:,:3].T@rows[i][:,:3]for i in [7,8,9]}
            steps.append(float(max(np.degrees(Rotation.from_matrix(now[i]@last[i].T).magnitude())for i in [7,8,9])))
            last=now
        results.append(dict(name=name,maximum_step_degrees=max(steps),steps=steps))
    return results

def add_continuity(output):
    output=Path(output);report=json.loads((output/'verification.json').read_text())
    log=(output/'native.log').read_text();steps=frame_steps(log,[r['name']for r in report['cases']])
    report['frame_steps']=steps;report['maximum_step_degrees']=max(r['maximum_step_degrees']for r in steps)
    report['raw_log_sha256']=hashlib.sha256((output/'native.log').read_bytes()).hexdigest()
    if not report['baseline']:
        assert report['maximum_step_degrees']<1.5,('abrupt torso movement',report['maximum_step_degrees'])
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS measured adjacent-frame torso change:',report['maximum_step_degrees'],flush=True)
    return report

def run(candidate,output,baseline=False):
    audit.SNAP=Path(candidate).resolve();audit.OUT=Path(output).resolve();out=audit.OUT
    out.mkdir(parents=True,exist_ok=True);engine,mod=audit.fixture('reload-transition')
    lines=['wait 180','developer 0','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667',
        'sv_cheats 1','god','weapon_9mmAR','wait 45','thirdperson','cam_snapto 1','cam_idealyaw 120','cam_idealpitch 0','cam_idealdist 90']
    cases=[]
    for platform,receiver in [('bottom','a47'),('side','side'),('top','top')]:
        for crouch in [False,True]:
            name=platform+('_crouch'if crouch else '_stand');cases.append(name)
            lines+=['developer 0','-duck','wait 30','vf_reference','wait 20',f'vf_item r01_receiver_{receiver}__original',
                'vf_commit','wait 25','vf_character','wait 5','vf_character','wait 15',
                'cmd vf_melee_place -300 -240 36 0 0','vf_traversal_look 0 0','wait 20']
            if crouch:lines+=['+duck','wait 30']
            lines+=['+attack','wait 6','-attack','wait 35','developer 3',f'echo RELOAD_{name}_BEFORE',
                'cmd vf_hitbox_info',f'screenshot scrshots/{name}_before.png','wait 1',
                f'echo RELOAD_{name}_START','+reload','wait 1','-reload']
            for frame in range(16):
                lines += [f'echo RELOAD_{name}_FRAME_{frame}','cmd vf_hitbox_info',f'screenshot scrshots/{name}_{frame:02}.png','wait 1']
            lines += [f'echo RELOAD_{name}_END','developer 0','wait 100','cmd vf_reload_info']
    lines+=['quit']
    for part,start in enumerate(range(0,len(lines),60)):
        chunk=lines[start:start+60]
        if start+60<len(lines):chunk+=[f'exec reload_transition_{part+1}.cfg']
        (mod/f'reload_transition_{part}.cfg').write_text('\n'.join(chunk)+'\n')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-clientport',str(port()),
        '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720',
        '-console','-nointro','-nowriteconfig','-log','reload-transition.log','+sv_cheats','1','+map','vf_range','+exec','reload_transition_0.cfg'],cwd=engine)
    try:process.wait(150);assert process.returncode==0
    finally:
        if process.poll()is None:process.terminate();process.wait(10)
    log=(engine/'reload-transition.log').read_text(errors='replace');(out/'native.log').write_text(log)
    assert not any(e in log for e in ['Host_Error','SV_Error','VFState rejected'])
    pattern=r'VFPlayerPose source=(server|render) entity=1 sequence=(\d+) frame=([\d.]+).*? box=(\d+) matrix=([-\d.,]+)'
    def rows(block,source):
        data={}
        for src,sequence,frame,box,values in re.findall(pattern,block):
            if src==source:data[int(box)]=(int(sequence),float(frame),np.array(list(map(float,values.split(',')))).reshape(3,4))
        assert all(i in data for i in [0,7,8,9]),('missing actual torso matrices',source)
        return data
    results=[];captures=out/'captures';captures.mkdir(exist_ok=True)
    for name in cases:
        before=rows(log.split(f'RELOAD_{name}_BEFORE ')[1].split(f'RELOAD_{name}_START ')[0],'render')
        assert before[7][0]==41,(name,'wrong idle sequence',before[7][0])
        reference={i:before[0][2][:,:3].T@before[i][2][:,:3]for i in [7,8,9]}
        samples=[]
        for frame in range(16):
            block=log.split(f'RELOAD_{name}_FRAME_{frame} ')[1].split(f'RELOAD_{name}_'+(f'FRAME_{frame+1}'if frame<15 else 'END')+' ')[0]
            render=rows(block,'render');server=rows(block,'server')
            assert render[7][0]==server[7][0]==77,(name,frame,'reload not active')
            angles={i:float(np.degrees(Rotation.from_matrix((render[0][2][:,:3].T@render[i][2][:,:3])@reference[i].T).magnitude()))for i in [7,8,9]}
            matrix_error=max(float(np.max(np.abs(render[i][2]-server[i][2])))for i in [0,7,8,9])
            samples.append(dict(frame=frame,sequence=77,studio_frame=render[7][1],torso_degrees=angles,server_render_error=matrix_error))
        worst=max(max(s['torso_degrees'].values())for s in samples)
        if not baseline:assert worst<3,(name,'torso snaps during reload transition',worst)
        results.append(dict(name=name,maximum_torso_change_degrees=worst,samples=samples))
        for suffix in ['before']+[f'{i:02}'for i in range(16)]:shutil.copy2(mod/'scrshots'/f'{name}_{suffix}.png',captures/f'{name}_{suffix}.png')
    report=dict(passed=baseline or all(r['maximum_torso_change_degrees']<3 for r in results),baseline=baseline,
        cases=results,frames=96,maximum_torso_change_degrees=max(r['maximum_torso_change_degrees']for r in results),
        client_sha256=hashlib.sha256((mod/'cl_dlls/client.dll').read_bytes()).hexdigest(),server_sha256=hashlib.sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest(),
        renderer_sha256=hashlib.sha256((engine/'ref_gl.dll').read_bytes()).hexdigest())
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    report=add_continuity(out)
    print('PASS reload frame capture:',len(results),'cases, 96 frames; maximum torso change',report['maximum_torso_change_degrees'],flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--bundle',type=Path);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--baseline',action='store_true');parser.add_argument('--analyze-existing',action='store_true');a=parser.parse_args()
    if a.analyze_existing:add_continuity(a.output)
    else:
        if not a.bundle:parser.error('--bundle is required to capture new frames')
        run(a.bundle,a.output,a.baseline)
