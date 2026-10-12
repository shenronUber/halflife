"""Two real clients, including a late join, share the server's seeded BSP choices."""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from native_workspace import private_copy,port
from slide_feet_bundle import prepare_slide_feet
from build_modular_range import build,geometry
from play_modular import prepare,SERVER,CLIENT,LIVE
from modular_native_test import expected

OUT=ROOT/'docs/validation/modular/multiplayer'


def run():
    prepare();OUT.mkdir(parents=True,exist_ok=True)
    stages=[]
    for name in ('server','actor','late'):
        engine,mod=prepare_slide_feet('modular-'+name,build=ROOT/'build/modular',server=SERVER,engine_binaries=LIVE,client=CLIENT)
        private_copy(build(ensure=True),mod/'maps/vf_modular.bsp')
        stages.append((engine,mod))
    server,actor,late=stages;server_port=port();programs=[]
    common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-nointro','-nowriteconfig']
    dedicated=subprocess.Popen([str(server[0]/'xash.exe'),'-ip','127.0.0.1','-noip6',*common,'-port',str(server_port),'-log','modular-server.log',
               '+developer','1','+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+map','vf_modular',
               '+vf_modular_seed','42','+map','vf_modular'],cwd=server[0],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    initialization=['wait 180','gl_vsync 0','host_framerate 0.0166667','fps_max 60','developer 1','con_notifytime 0',
                    'cmd give weapon_9mmAR','weapon_9mmAR','wait 30','vf_reference 0','wait 25','vf_commit','wait 35',
                    'vf_character','vf_character','wait 10','echo PEER_LAYOUT','cmd vf_modular_info','cmd vf_modular_check','wait 12']
    actor_script=initialization+['cmd vf_traversal_place -992 -1598 128 300 320 0 0','vf_traversal_look 300 0',
                  '+forward','+jump','wait 3','-jump','vf_traversal_look 0 0','wait 30',
                  'echo PEER_RUN','cmd vf_traversal_info','wait 6','screenshot scrshots/modular_peer_run.png','wait 4',
                  'wait 60','-forward','wait 45','echo PEER_LAND','cmd vf_traversal_info','wait 10','quit']
    late_script=initialization+['cmd vf_traversal_place -896 -1536 96 0','wait 4','vf_traversal_look 0 10',
                 'wait 10','screenshot scrshots/modular_late_join.png','wait 4','wait 40','quit']
    def start(pair,name,commands):
        engine,mod=pair;(mod/'modular_peer.cfg').write_text('\n'.join(commands)+'\n',encoding='ascii')
        child=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6',*common,'-windowed','-width','1280','-height','720',
               '-clientport',str(port()),'-log',name+'.log','+name',name,'+connect',f'127.0.0.1:{server_port}',
               '+exec','modular_peer.cfg'],cwd=engine,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        programs.append(child)
    try:
        time.sleep(2);assert dedicated.poll() is None
        start(actor,'modular-actor',actor_script)
        time.sleep(3)
        start(late,'modular-late',late_script)
        for process in programs:process.wait(timeout=80)
    finally:
        for process in [*programs,dedicated]:
            if process.poll() is None:process.terminate();process.wait(timeout=8)
    texts=[]
    for pair,name in ((actor,'modular-actor'),(late,'modular-late')):
        file=pair[0]/(name+'.log');text=file.read_text(errors='replace');texts.append(text);shutil.copy2(file,OUT/file.name)
        for capture in (pair[1]/'scrshots').glob('modular_*.png'):shutil.copy2(capture,OUT/capture.name)
    shutil.copy2(server[0]/'modular-server.log',OUT/'server.log')
    grids=[re.findall(r'VFModular seed=(\d+) cells=([\d,]+)',text) for text in texts]
    checks=[re.findall(r'VFModular check seed=(\d+) candidates=(\d+) mismatches=(\d+)',text) for text in texts]
    server_text=(OUT/'server.log').read_text(errors='replace')
    rows=re.findall(r'VFTraversal phase=(\d+) state=\d+ origin=([\d.,-]+)',server_text)
    movements=[('RUN' if phase=='8' else 'LAND',phase,origin) for phase,origin in rows]
    report=dict(passed=False,grids=grids,collision_checks=checks,movements=movements,exit_codes=[p.returncode for p in programs])
    (OUT/'network.json').write_text(json.dumps(report,indent=2))
    assert all(p.returncode==0 for p in programs)
    expected_grid=','.join(map(str,expected(42)['cells']))
    assert all(('42',expected_grid) in grid for grid in grids),grids
    assert all(('42','102','0') in rows for rows in checks),checks
    assert any(name=='RUN' and phase=='8' and -896<float(origin.split(',')[0])<-640 for name,phase,origin in movements),movements
    assert any(name=='LAND' and phase=='0' and float(origin.split(',')[0])>-640 and 35<float(origin.split(',')[2])<38 for name,phase,origin in movements),movements
    report.update(passed=True,checks=['two connected clients share seed and partition','late join receives active candidates',
                  '102 candidate states and all junction collision traces agree','installed client traverses replicated wall-run BSP'])
    (OUT/'network.json').write_text(json.dumps(report,indent=2))
    print('PASS modular multiplayer and late join',flush=True)


if __name__=='__main__':run()
