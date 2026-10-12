"""Paired native measurements: identical profiler, map, assets and fixed simulation.

Frame wall time includes presentation/backend work; CPU render/HUD time is
submission time; GPU elapsed queries are asynchronous and exclude swap/present.
The 1000 FPS cap is recorded, not interpreted as an uncapped throughput result.
"""
import argparse,hashlib,json,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import third_person_native_test as harness
from native_workspace import port,private_copy
OUT=ROOT/'build/maintenance-perf'
SCENES={1:'body_off',2:'body_on',3:'headgear_gesture',4:'corpses_plain',5:'corpses_elemental',6:'night_vision',7:'airstrip_realtime'}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def script():
    cfg=['wait 180','developer 1','con_notifytime -1','gl_vsync 0','gl_finish 0','fps_max 1000',
         'host_framerate .016666667','sys_timescale 1','sv_cheats 1','vf_voices 0','vf_voice_subtitles 0',
         'god','weapon_9mmAR','wait 30','firstperson','cmd vf_range_aim 0','wait 30']
    def gear(key):
        cfg.extend(['vf_operator','wait 8',f'vf_item {key}','vf_commit','wait 20','vf_operator','wait 20'])
    gear('helmet_riot')
    for label in SCENES:
        cfg+=['vf_perf 0','cmd vf_death_clear','wait 30',f'echo PERF_SCENE_{label}']
        if label in (1,2):
            cfg+=[f'vf_first_person_body {int(label==2)}',f'vf_perf {label}','wait 1050']
        elif label==3:
            cfg+=['vf_first_person_body 1',f'vf_perf {label}']
            for _ in range(8):cfg+=['vf_headgear_toggle','wait 150']
        elif label in (4,5):
            cfg+=[f'vf_perf {label}']
            for _ in range(24):
                for target in range(4):
                    cfg+=[f'cmd vf_range_reset {target}',f'cmd vf_range_death {target} all '+('electro'if label==5 else 'standard')]
                cfg+=['wait 36']
            cfg+=['vf_death_client']
        elif label==6:
            gear('helmet_nvg_green');cfg+=[f'vf_perf {label}','wait 1050']
        if label==7:
            cfg+=['map vf_cs_de_airstrip','wait 300','developer 1','host_framerate 0','gl_vsync 0','fps_max 1000',
                  'vf_first_person_body 1','cmd give weapon_9mmAR','weapon_9mmAR','wait 60',f'vf_perf {label}','+forward','wait 1050','-forward']
        cfg+=['vf_perf 0','vf_engine_stats',f'screenshot scrshots/perf_{label}.png','wait 4']
    return '\n'.join(cfg+['quit',''])

def run(kind,repeat,engine=None):
    candidate=OUT/'candidate';baseline=OUT/'baseline'
    client=(candidate if kind=='optimized'else baseline)/'client/client.dll'
    renderer=candidate/'engine' if kind=='optimized'else OUT/'reference-engine'
    if engine is None:engine=harness.stage('performance-paired',client=client,server=ROOT/'build/server/hl.dll',renderer=renderer)
    else:
        for source in renderer.iterdir():
            if source.is_file() and source.suffix.lower() in {'.dll','.exe'}:private_copy(source,engine/source.name)
        private_copy(client,engine/'vf_animation/cl_dlls/client.dll')
    mod=engine/'vf_animation';(mod/'performance.cfg').write_text(script(),encoding='ascii')
    command=[str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-port',str(port()),'-clientport',str(port()),
             '-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720',
             '-console','-nointro','-nowriteconfig','-log','performance.log','+exec','lab_controls.cfg',
             '+map','vf_range','+exec','performance.cfg']
    started=time.monotonic();process=subprocess.Popen(command,cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        process.wait(timeout=180);assert process.returncode==0
    finally:
        if process.poll()is None:process.terminate();process.wait(timeout=10)
    log=(engine/'performance.log').read_text(errors='replace')
    assert not any(x in log for x in ('Host_Error','SV_Error','VFState rejected','Crash:'))
    pattern=r'VFPerf label=(\d+) metric=(\w+) samples=(\d+) mean_ms=([\d.]+) p50_ms=([\d.]+) p95_ms=([\d.]+) max_ms=([\d.]+)'
    scenes={}
    for label,metric,count,mean,p50,p95,maximum in re.findall(pattern,log):
        scenes.setdefault(SCENES[int(label)],{})[metric]=dict(samples=int(count),mean_ms=float(mean),p50_ms=float(p50),p95_ms=float(p95),max_ms=float(maximum))
    for label,resolves,updates,gpu in re.findall(r'VFPerf work label=(\d+) resolves=(\d+) pose_updates=(\d+) gpu_samples=(\d+)',log):
        scenes[SCENES[int(label)]]['work']=dict(resolves=int(resolves),pose_updates=int(updates),gpu_samples=int(gpu))
    assert len(scenes)==len(SCENES),scenes
    for scene in scenes.values():assert scene['frame']['samples']==240 and scene['cpu_render_hud']['samples']==240
    if kind=='optimized':
        assert scenes['headgear_gesture']['work']['pose_updates']>100
        assert scenes['headgear_gesture']['work']['resolves']<20
    graphics={key:value.strip()for key,value in re.findall(r'(GL_VENDOR|GL_RENDERER|GL_VERSION): ([^\n]+)',log)}
    result=dict(kind=kind,repeat=repeat,scenes=scenes,graphics=graphics,elapsed=time.monotonic()-started,
                client_sha256=digest(client),renderer_sha256=digest(renderer/'ref_gl.dll'),server_sha256=digest(ROOT/'build/server/hl.dll'),
                resolution=[1280,720],vsync=False,fps_cap=1000,host_frame_override_seconds=1/60,realtime_scene='airstrip_realtime',
                scope='CPU render+HUD submission, GPU render+HUD excluding present, whole-frame wall interval')
    (OUT/f'performance-{kind}-{repeat}.json').write_text(json.dumps(result,indent=2))
    (OUT/f'performance-{kind}-{repeat}.log').write_text(log)
    for label in SCENES:
        import shutil
        shutil.copy2(mod/'scrshots'/f'perf_{label}.png',OUT/f'performance-{kind}-{repeat}-scene-{label}.png')
    print('PASS native performance',kind,repeat,json.dumps(scenes),flush=True)
    return result,engine

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['baseline','optimized']);p.add_argument('--repeat',type=int,default=1);p.add_argument('--pairs',type=int)
    a=p.parse_args()
    if a.pairs:
        engine=None
        for repeat in range(1,a.pairs+1):
            for kind in (['baseline','optimized']if repeat%2 else ['optimized','baseline']):
                _,engine=run(kind,repeat,engine)
    elif a.kind:run(a.kind,a.repeat)
    else:p.error('Choose --kind or --pairs')
