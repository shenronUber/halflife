"""Two independent clients on a loopback dedicated server; no public service."""
import json,os,re,shutil,subprocess,time
from pathlib import Path
from native_engine_test import ROOT,ENGINE,STEAM,fingerprint

def prepare_peer(mod):
    peer=ROOT.parent/'runtime/vector-engine-peer'
    peer.mkdir(parents=True,exist_ok=True)
    for f in ENGINE.iterdir():
        if f.is_file() and f.suffix.lower() in ('.dll','.exe'):shutil.copy2(f,peer/f.name)
    for folder in ['valve',mod,'tfc_assets']:
        shutil.copytree(ENGINE/folder,peer/folder,dirs_exist_ok=True,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
    return peer

def run(visual=False):
    mod='vf_visual' if visual else 'vf_engine'
    peer=prepare_peer(mod);skinHash=fingerprint(ROOT/'generated'/('visual_skins' if visual else 'skins')/'skins.txt')
    initial='wait 220\ndeveloper 1\ncon_notifytime 0\nfps_max 100\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 20\ncmd vf_peer_pose\nwait 90\ncmd vf_body_info\n'
    first=initial+f'cmd vf_skin_apply {skinHash} 44 0 69 138 9\nwait 50\nvf_character\nwait 90\nvf_select_slot 12\nvf_next_item\nvf_select_slot 11\nvf_next_item\nvf_commit\nwait 60\nvf_character\n'
    first+='wait 1200\nvf_engine_stats\nscreenshot scrshots/peer_a_sees_b.png\nwait 20\ncmd vf_appearance_mode 0\nwait 50\ncmd vf_appearance_mode 9\nwait 20\nvf_engine_stats\n+forward\nwait 15\n-forward\nwait 100\n+attack\nwait 25\n-attack\nwait 120\nvf_engine_stats\nwait 1000\nquit\n'
    second=initial+f'cmd vf_skin_apply {skinHash} 127 127 9 127 0\nwait 700\nvf_engine_stats\nscreenshot scrshots/peer_b_sees_a.png\nwait 20\n'
    second+='wait 2000\nvf_engine_stats\nscreenshot scrshots/peer_b_movement.png\nwait 20\nquit\n'
    if visual:first=first.replace('44 0 69 138 9','151 151 146 151 147')
    (ENGINE/mod/'vf_peer_a.cfg').write_text(first,encoding='ascii')
    (peer/mod/'vf_peer_b.cfg').write_text(second,encoding='ascii')
    common=['-rodir',STEAM,'-game',mod,'-console','-nointro']
    server_args=[str(ENGINE/'xash.exe'),*common,'-log','native-server.log','+ip','127.0.0.1','-port','27025','+maxplayers','4','+sv_lan','1','+sv_cheats','1','+deathmatch','1','+developer','1','+map','vf_range']
    server=subprocess.Popen(server_args,cwd=ENGINE,creationflags=subprocess.CREATE_NO_WINDOW)
    children=[];started=time.time()
    try:
        time.sleep(4)
        assert server.poll() is None,'Dedicated server exited'
        def launch(folder,port,cfg,name):
            args=[str(folder/'xash3d.exe'),*common,'-borderless','-width','1920','-height','1080','-log','native-peer.log','+exec','lab_controls.cfg','-clientport',str(port),'+name',name,'+connect','127.0.0.1:27025','+exec',cfg]
            child=subprocess.Popen(args,cwd=folder);children.append(child)
        launch(ENGINE,27026,'vf_peer_a.cfg','VF_A')
        # The second player joins after the first committed its appearance.
        time.sleep(8)
        launch(peer,27027,'vf_peer_b.cfg','VF_B')
        for child in children:child.wait(timeout=100);assert child.returncode==0,child.returncode
        logs=[(folder/'native-peer.log').read_text(errors='replace') for folder in [ENGINE,peer]]
        for player,log in enumerate(logs,1):
            for line in [('VFState player=1 skins=151,151,146,151,147 weapon=3' if visual else 'VFState player=1 skins=44,0,69,138,9 weapon=3'),'VFPeer 2: 127,127,9,127,0 weapon=0']:assert line in log,line
            assert 'VFState rejected' not in log
            if visual:assert 'VFState player=1 skins=150,145,147,147,148 weapon=3' in log,'linked appearance replicates to both clients'
            assert 'VFAppearance state: player=1 mode=9' not in log
            assert f'VFBody player={player} mins=-16,-16,-36 maxs=16,16,36 rifle=1' in log
            samples=re.findall(r'VFEngine: assemblies=(\d+).*?merged=(\d+)',log)
            assert any(int(a)>=3 and int(b)>0 for a,b in samples),samples
            assert any(int(n)>0 for n in re.findall(r'VFEngine remote weapons drawn=(\d+)',log)),'Carried weapons must remain visible with the hidden rig'
        captures=[(ENGINE,'peer_a_sees_b'),(peer,'peer_b_sees_a'),(peer,'peer_b_movement')]
        for folder,name in captures:
            file=folder/mod/'scrshots'/(name+'.png');assert file.stat().st_mtime>=started and file.stat().st_size>1000,name
        report={'checks':['dedicated server and two real client processes connected on loopback','late join receives existing appearance and all 21 equipment slots','both clients agree on both authoritative loadouts','remote modular player assemblies rendered','equipment-linked appearance switch replicated to both clients; invalid mode rejected','movement and firing exercised'],'captures':[str(f/mod/'scrshots'/(n+'.png')) for f,n in captures],'scope':'local network test; Internet hosting not tested'}
        report['checks']+=['both players receive a rifle automatically','SDK collision hulls preserved','carried third-person weapons rendered with the modular body']
        (ROOT/'build'/('visual-multiplayer-verification.json' if visual else 'native-multiplayer-verification.json')).write_text(json.dumps(report,indent=2))
        print('PASS: two clients, late join, synchronized skins and equipment',flush=True)
    finally:
        for child in children:
            if child.poll() is None:child.terminate();child.wait(10)
        if server.poll() is None:server.terminate();server.wait(10)

if __name__=='__main__':
    import sys
    run('--visual-lab' in sys.argv)
