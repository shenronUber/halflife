"""Actual replicated extended phase and run gait, including a late joiner."""
import json,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from slide_feet_bundle import prepare_slide_feet
from native_workspace import port
BUILD=ROOT/'build/wallrun';OUT=ROOT/'docs/validation/wallrun/network'
def run():
    OUT.mkdir(parents=True,exist_ok=True);pairs={}
    for name in ('server','actor','observer','late'):
        pairs[name]=prepare_slide_feet('wallrun-'+name,build=BUILD,server=BUILD/'server/hl.dll',engine_binaries=BUILD/'engine')
    server_port=port();server,server_mod=pairs['server'];processes=[]
    dedicated=subprocess.Popen([str(server/'xash.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game','vf_animation','-nointro','-nowriteconfig','-log','wallrun-server.log','-port',str(server_port),
        '+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+map','vf_traversal'],cwd=server,creationflags=subprocess.CREATE_NO_WINDOW)
    init=['wait 30','gl_vsync 0','fps_max 60','sys_timescale 1','developer 2','con_notifytime -1','vf_voice_subtitles 0',
        'vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character','wait 12']
    def start(name,lines,defer=False):
        engine,mod=pairs[name];cfg='wallrun_peer.cfg';gate=mod/'wallrun_ready.cfg'
        # Frame waits can expire while a large current model bank is signing
        # on. Keep the scenario gated until the real server state arrives.
        gate.write_text('wait 30\nexec wallrun_ready.cfg\n',encoding='ascii')
        (mod/cfg).write_text('wait 30\nexec wallrun_ready.cfg\n',encoding='ascii')
        processes.append(subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
            '-game','vf_animation','-windowed','-width','800','-height','600','-nointro','-nowriteconfig','-dev','2',
            '-log','wallrun-'+name+'.log','-clientport',str(port()),'+name',name,'+developer','2',
            '+connect','127.0.0.1:'+str(server_port),'+exec',cfg],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW))
        deadline=time.monotonic()+45;log=engine/('wallrun-'+name+'.log')
        while time.monotonic()<deadline:
            text=log.read_text(errors='replace') if log.exists() else ''
            if 'VFState player=' in text:break
            assert processes[-1].poll() is None,(name,'exited during sign-on')
            time.sleep(.25)
        else:raise AssertionError((name,'server equipment state never arrived'))
        scenario='\n'.join(init+lines)+'\n'
        if not defer:gate.write_text(scenario,encoding='ascii')
        return gate,scenario
    try:
        time.sleep(1)
        actor_gate,actor_script=start('actor',['cmd give weapon_9mmAR','weapon_9mmAR','cmd vf_traversal_place -900 -1006 128 300 320 0 0',
            'vf_traversal_look 300 0','+forward','+jump','wait 4','-jump','vf_traversal_look 0 0','wait 120',
            'vf_traversal_look 90 -85','wait 60','echo WRNET_FREE_POS','cmd vf_traversal_info',
            'vf_traversal_look 270 85','wait 60','echo WRNET_FREE_NEG','cmd vf_traversal_info',
            'vf_traversal_look 0 0','wait 960','cmd vf_traversal_info','wait 180','quit'],defer=True)
        time.sleep(.5)
        observer=['r_drawviewmodel 0','cmd vf_traversal_place 300 -800 36 230','vf_traversal_look 230 -8','wait 12']
        for i in range(12):observer+=['wait 20','vf_engine_stats',f'screenshot scrshots/wallrun_peer_{i:02}.png']
        observer_gate,observer_script=start('observer',observer+['wait 120','quit'],defer=True)
        actor_gate.write_text(actor_script,encoding='ascii');observer_gate.write_text(observer_script,encoding='ascii')
        deadline=time.monotonic()+20;observer_log=pairs['observer'][0]/'wallrun-observer.log'
        while time.monotonic()<deadline:
            if re.search(r'VFPeerTraversal player=1 phase=8',observer_log.read_text(errors='replace')):break
            time.sleep(.25)
        else:raise AssertionError('Observer never received active wall run before late join')
        late=['r_drawviewmodel 0','cmd vf_traversal_place 2000 -800 36 250','vf_traversal_look 250 -8','wait 12']
        for i in range(8):late+=['wait 15','vf_engine_stats']
        start('late',late+['wait 20','quit'])
        for p in processes:p.wait(timeout=55)
    finally:
        for p in [*processes,dedicated]:
            if p.poll()is None:p.terminate();p.wait(timeout=8)
    report={}
    for name in ('actor','observer','late'):
        engine,mod=pairs[name];log=engine/('wallrun-'+name+'.log');text=log.read_text(errors='replace');shutil.copy2(log,OUT/log.name)
        rows=[dict(player=int(p),phase=int(phase),sequence=int(s),gait=int(g),yaw=float(y))for p,phase,s,g,y in re.findall(r'VFPeerTraversal player=(\d+) phase=(\d+) sequence=(\d+) gait=(\d+) wall=([\d.-]+)',text)]
        report[name]=rows
        if name!='actor':assert any(r['phase']==8 and r['gait']>0 for r in rows),(name,rows)
        else:
            for label in ['WRNET_FREE_POS','WRNET_FREE_NEG']:
                block=text.split(label)[1].split('WRNET_')[0]
                assert re.search(r'VFBodyFeet phase=8 .*own=1',block),(label,'local player dropped a permitted look')
        assert 'VFState rejected' not in text,(name,'equipment rejected')
        for image in (mod/'scrshots').glob('wallrun_peer_*.png'):shutil.copy2(image,OUT/image.name)
    from build_weapon_melee import digest
    report.update(passed=True,server_sha256=digest(pairs['server'][1]/'dlls/hl.dll'),
                  client_sha256=digest(pairs['actor'][1]/'cl_dlls/client.dll'),
                  renderer_sha256=digest(pairs['actor'][0]/'ref_gl.dll'),engine_sha256=digest(pairs['actor'][0]/'xash.dll'))
    (OUT/'network.json').write_text(json.dumps(report,indent=2));print('PASS wall-run free look, phase and animated gait received by observer and late joiner',flush=True)
if __name__=='__main__':run()
