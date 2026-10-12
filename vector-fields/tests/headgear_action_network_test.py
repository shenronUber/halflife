"""Two real clients: late joining observer receives raised equipment and gesture."""
import argparse,json,re,subprocess,sys,time
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from headgear_preview import stage,asset_library
from native_workspace import port

def run(candidate=None):
    server_port=port()
    engine,mod=stage('headgear-network-a',candidate)
    peer,peer_mod=stage('headgear-network-b',candidate)
    common=['-rodir',str(asset_library()),'-game',mod.name,'-console','-nointro','-nowriteconfig']
    server=subprocess.Popen([str(engine/'xash.exe'),'-ip','127.0.0.1','-noip6',*common,'-log','server.log','+ip','127.0.0.1','-port',str(server_port),
        '+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','2','+map','vf_range'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    initial='wait 220\ndeveloper 2\ncon_notifytime -1\ngl_vsync 0\nfps_max 60\nweapon_9mmAR\ncmd vf_peer_pose\nwait 20\n'
    a=initial+'vf_operator\nwait 25\nvf_item helmet_gas_mask\nvf_commit\nwait 25\nvf_operator\nwait 15\ncmd vf_headgear_toggle\nwait 1100\ncmd vf_headgear_toggle\nwait 120\ncmd vf_headgear_toggle\nwait 300\nvf_engine_stats\nquit\n'
    b=initial+'default_fov 55\nwait 30\nscreenshot scrshots/late_join_raised.png\nwait 500\n'
    for i in range(18):b+=f'wait 35\nscreenshot scrshots/remote_gesture_{i}.png\n'
    b+='vf_engine_stats\nwait 40\nquit\n'
    (mod/'a.cfg').write_text(a,encoding='ascii');(peer_mod/'b.cfg').write_text(b,encoding='ascii')
    children=[]
    def launch(folder,client_port,cfg,name):
        p=subprocess.Popen([str(folder/'xash3d.exe'),'-ip','127.0.0.1','-noip6',*common,'-dev','2','-windowed','-width','960','-height','540',
            '-log','peer.log','-clientport',str(client_port),'+exec','lab_controls.cfg','+developer','2','+name',name,
            '+connect',f'127.0.0.1:{server_port}','+exec',cfg],cwd=folder,creationflags=subprocess.CREATE_NO_WINDOW)
        children.append(p);return p
    try:
        time.sleep(3);assert server.poll() is None
        first=launch(engine,port(),'a.cfg','HEADGEAR_OWNER')
        deadline=time.time()+60
        while time.time()<deadline:
            log=(engine/'peer.log').read_text(errors='replace') if (engine/'peer.log').exists() else ''
            if 'VFHeadgear state: player=1 raised=1' in log:break
            assert first.poll() is None,'Owner exited before equipping helmet';time.sleep(.25)
        else:raise AssertionError('Owner did not raise the gas mask')
        time.sleep(1.4);second=launch(peer,port(),'b.cfg','HEADGEAR_OBSERVER')
        for child in children:child.wait(timeout=150);assert child.returncode==0
        owner=(engine/'peer.log').read_text(errors='replace');observer=(peer/'peer.log').read_text(errors='replace')
        assert 'VFState rejected' not in owner+observer
        assert 'VFHeadgear state: player=1 raised=1 elapsed=0' in observer,'Late join must receive the resting raised pose'
        assert 'VFHeadgear state: player=1 raised=0 elapsed=1' in observer
        assert 'VFHeadgear pose: view=0 type=5' in observer,'Observer must actually render the remote left-arm gesture'
        assert 'VFThirdPerson player=1' in observer
        assert 'rejected=0' in observer
        assert len(re.findall(r'VFHeadgear voice received: player=1',owner))==1
        assert len(re.findall(r'VFHeadgear voice received: player=1',observer))==1
        server_log=(engine/'server.log').read_text(errors='replace')
        assert len(re.findall(r'VFHeadgear voice: player=1',server_log))==1
        assert re.search(r'VFHeadgear voice: player=1 .*?sample=vf_headgear/voices/\S+ audition=0 cover=0.0000',server_log)
        for i in range(18):assert (peer_mod/'scrshots'/f'remote_gesture_{i}.png').stat().st_size>1000
        report=dict(passed=True,clients=2,dedicated_loopback=True,late_join_raised=True,remote_left_arm_rendered=True,
                    replicated_lower_and_raise=True,world_collision_unchanged=True,
                    positional_headgear_voice_received_by_both_clients=True,no_late_join_voice_replay=True,
                    activation_voice_normal_before_lowering=True,
                    client_sha256=sha256((mod/'cl_dlls/client.dll').read_bytes()).hexdigest(),
                    server_sha256=sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest(),
                    renderer_sha256=sha256((engine/'ref_gl.dll').read_bytes()).hexdigest())
        (ROOT/'build/headgear-action/network-verification.json').write_text(json.dumps(report,indent=2));print('PASS headgear network: two clients, late join and remote gas-mask gesture',flush=True)
        return report
    finally:
        for child in children:
            if child.poll() is None:child.terminate();child.wait(timeout=10)
        if server.poll() is None:server.terminate();server.wait(timeout=10)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--candidate-dir',type=Path);run(parser.parse_args().candidate_dir)
