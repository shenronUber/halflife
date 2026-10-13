"""Native loop format, quiet mix budget and map-only ambient sound delivery."""
import argparse, json, os, re, shutil, struct, subprocess, sys, wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import build_modular_ambience as bank
from build_modular_range import build, geometry
from build_atmosphere import deploy as deploy_atmosphere
from native_workspace import private_copy, port
from slide_feet_bundle import prepare_slide_feet
OUT=ROOT/'docs/validation/modular-ambience'

def entities(path):
    data=Path(path).read_bytes(); offset,length=struct.unpack_from('<ii',data,4)
    return [dict(re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"',b))
            for b in re.findall(r'\{([^{}]*)\}',data[offset:offset+length].decode('latin1'))]

def assets():
    manifest=bank.build(ensure=True); assert len(manifest['clips'])==5
    for clip in manifest['clips']:
        path=bank.OUT/Path(clip['path']).name; data=path.read_bytes()
        with wave.open(str(path)) as w:
            assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,22050)
            x=np.frombuffer(w.readframes(w.getnframes()),'<i2').astype(float)/32768
        cue=data.index(b'cue '); assert struct.unpack_from('<I',data,cue+32)[0]==0
        assert len(x)==clip['frames'] and 30<len(x)/22050<75
        assert abs(x[0]-x[-1])<.0001 and abs(x[-2]-x[-1])<.03,('Loop click',clip['id'])
        assert abs(x).max()<.49 and .002<np.std(x)<.17,clip
        if clip['id'].startswith('strain'):assert np.mean(abs(x)<.0002)>.62,'Metal events must stay sparse'
    bsp=build(ensure=True); world=entities(bsp)
    assert world[0]['skyname']=='vf_storm'
    rows=[r for r in world if r.get('classname')=='ambient_generic']
    assert len(rows)==5 and {r['message'] for r in rows}=={c['path'] for c in manifest['clips']}
    assert all(int(r['spawnflags'])&32==0 and float(r['health'])<=2.2 for r in rows)
    assert [r['spawnflags'] for r in rows].count('1')==2
    # Absolute upper bound at one point, even if all events peak simultaneously.
    peaks={c['path']:c['peak'] for c in manifest['clips']}
    maximum=sum(float(r['health'])/10*peaks[r['message']] for r in rows)
    assert maximum<.42,maximum
    checks=dict(passed=True,clips=manifest['clips'],entities=rows,maximum_pre_master_mix_peak=maximum,
                checks=['native RIFF cue loop markers','quiet long loops without a hard seam','sparse metal events',
                        'two global air beds and three local structures','five actual BSP sound entities'])
    OUT.mkdir(parents=True,exist_ok=True); (OUT/'assets.json').write_text(json.dumps(checks,indent=2)+'\n')
    print('PASS modular ambience assets and BSP mix budget',flush=True)
    return manifest

def native():
    assets(); live=Path(os.environ.get('VF_TEST_ENGINE',ROOT.parent/'runtime/vector-engine'))
    sdk=Path(os.environ.get('VF_RELEASE_SDK',ROOT/'build'))
    engine,mod=prepare_slide_feet('modular-ambience',server=sdk/'server/hl.dll',client=sdk/'client/client.dll',engine_binaries=live)
    private_copy(build(ensure=True),mod/'maps/vf_modular.bsp'); bank.deploy(mod); deploy_atmosphere(mod)
    from build_atmosphere import runtime_files, sha
    sky_files=[(source,target) for source,target in runtime_files() if target.suffix=='.tga']
    assert len(sky_files)==6 and all(sha(source)==sha(mod/target) for source,target in sky_files)
    script=['gl_vsync 0','host_framerate .016666667','fps_max 60','developer 1','s_show 1','con_notifytime 0',
            'wait 240','echo AMBIENCE_STARTED','soundlist','cmd vf_modular_check',
            'screenshot scrshots/ambience_started.png','wait 12','save vf_ambience_check','wait 12',
            'load vf_ambience_check','wait 180','echo AMBIENCE_RESTORED','soundlist','cmd vf_modular_check',
            'screenshot scrshots/ambience_restored.png','wait 12',
            'map vf_range','wait 180','echo AMBIENCE_OTHER_MAP','screenshot scrshots/ambience_other.png','wait 12',
            'map vf_modular','wait 180','echo AMBIENCE_RETURNED','soundlist','cmd vf_modular_check',
            'screenshot scrshots/ambience_returned.png','wait 12','s_show 0','quit']
    (mod/'ambience_check.cfg').write_text('\n'.join(script)+'\n')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir',
        'F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-windowed','-width','1280','-height','720',
        '-nointro','-nowriteconfig','-dev','1','-log','ambience.log','-port',str(port()),'-clientport',str(port()),
        '+sv_cheats','1','+map','vf_modular','+exec','ambience_check.cfg'],cwd=engine,
        creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:process.wait(timeout=90)
    finally:
        if process.poll() is None:process.terminate();process.wait(timeout=8)
    log=(engine/'ambience.log').read_text(errors='replace'); shutil.copy2(engine/'ambience.log',OUT/'native.log')
    for p in (mod/'scrshots').glob('ambience_*.png'):shutil.copy2(p,OUT/p.name)
    assert process.returncode==0 and 'Host_Error' not in log
    names={c[0]+'.wav' for c in bank.CLIPS}
    for marker in ('STARTED','RESTORED','RETURNED'):
        part=log.split('AMBIENCE_'+marker,1)[1].split('AMBIENCE_',1)[0]
        loaded=set(re.findall(r'L\s+\(16b\).*?sound/vf_ambience/(\w+\.wav)',part))
        assert loaded==names,(marker,loaded)
    assert 'couldn\'t load' not in log.lower() and 'invalid wav' not in log.lower()
    report=dict(passed=True,checks=['native engine loads all five WAVs with loop flags',
                'save/load and map return reload the bank','map-only ambient entities','six storm sky faces deployed with the audio',
                'review s_show captures for real active mixer channels'],screenshots=[p.name for p in OUT.glob('ambience_*.png')])
    (OUT/'native.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS native modular ambience looping, saves and map return',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--native',action='store_true')
    native() if p.parse_args().native else assets()
