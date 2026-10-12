"""Refresh deployment baseline after another agent publishes, without repeating the film."""
import json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from play_weapon_melee import stage,command,OUT
from build_weapon_melee import sources,digest
from weapon_melee_native_test import deployed
def run():
    build=json.loads((OUT/'build.json').read_text());full=json.loads((OUT/'native.json').read_text())
    assert full['passed'] and sources()==build['sources']
    before=deployed();engine,mod=stage();binaries={n:digest(engine/n) for n in full['engine_binaries']}
    assert binaries==full['engine_binaries'],'Repeat the full native test if the engine changed'
    assert digest(mod/'cl_dlls/client.dll')==full['client_sha256'] and digest(mod/'dlls/hl.dll')==full['server_sha256']
    lines=['wait 180','developer 1','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667','god','weapon_9mmAR','wait 60']
    names=[]
    for receiver in ('a47','side','top'):
        for grip in ('a','b'):
            name=receiver+'_'+grip;names.append(name)
            lines+=['vf_reference','wait 20','vf_item r01_receiver_'+receiver+'__original','vf_item r01_underbarrel_'+grip+'__original','vf_commit','wait 25',
                'vf_ui_pointer 1220 40 1','wait 3','vf_ui_pointer 1220 40 0','wait 15','vf_melee','wait 28','echo BASELINE_'+name,
                'vf_melee_info','cmd vf_melee_info','wait 2','wait 50']
    lines+=['vf_engine_stats','quit'];cfg=mod/'melee_publication.cfg';cfg.write_text('\n'.join(lines)+'\n')
    process=subprocess.Popen(command(engine,mod,cfg),cwd=engine)
    try:process.wait(120)
    finally:
        if process.poll() is None:process.terminate();process.wait(10)
    log=(engine/'weapon-melee.log').read_text(errors='replace');(OUT/'publication-baseline.log').write_text(log)
    assert process.returncode==0 and not any(t in log for t in ('Host_Error','SV_Error','VFState rejected'))
    blocks=dict(re.findall(r'BASELINE_(\w+)\s+(.*?)(?=BASELINE_|$)',log,re.S))
    for name in names:
        assert 'VFMelee server: active=1' in blocks[name] and 'rendered_sequence=9 rig=models/vf_melee/' in blocks[name],(name,blocks[name])
    assert 'rejected=0' in log and sources()==build['sources'] and deployed()==before
    report=dict(passed=True,sources=build['sources'],installed_before=before,engine_binaries=binaries,
        client_sha256=full['client_sha256'],server_sha256=full['server_sha256'],six_configurations=names)
    (OUT/'publication-baseline.json').write_text(json.dumps(report,indent=2));print('PASS current publication baseline: six mounts, exact previously reviewed candidate and current installed engine')
if __name__=='__main__':run()
