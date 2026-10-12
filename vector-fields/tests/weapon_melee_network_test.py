"""Two real loopback clients observe the manually authored standing/crouched action."""
import json,re,subprocess,sys,time,shutil
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from play_weapon_melee import stage,OUT
from native_workspace import engine_path,copy_resources,port
from build_weapon_melee import sources,digest
def run():
    build=json.loads((OUT/'build.json').read_text());assert sources()==build['sources']
    from studio_assets import Studio
    rig=Studio(ROOT/'generated/weapon-melee/r01_tp.mdl')
    expected={rig.sequences.index('vf_melee'),rig.sequences.index('vf_melee_crouch')}
    engine,mod=stage();peer=engine_path(OUT/'network-peer');copy_resources(engine,peer,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
    (peer/mod.name/'scrshots').mkdir(exist_ok=True);serverport=port();clients=[port(),port()]
    initial='wait 220\ndeveloper 1\ncon_notifytime -1\ngl_vsync 0\nfps_max 60\ncl_cmdrate 100\ncl_updaterate 60\nrate 100000\nweapon_9mmAR\nwait 45\ngod\n'
    observer=initial+'cmd vf_peer_pose\ndefault_fov 60\nr_drawviewmodel 0\nwait 20\n'
    for frame in range(180):observer+=f'wait 6\necho REMOTE_{frame}\nvf_engine_stats\nscreenshot scrshots/remote_{frame:03}.png\nwait 1\n'
    observer+='quit\n'
    actor=initial+'cmd vf_peer_pose\nwait 20\n'
    for crouch in (False,True,False):
        actor+=('+duck\n' if crouch else '-duck\n')+'wait 100\ncmd vf_traversal_info\ncmd vf_body_info\nvf_melee\nwait 28\ncmd vf_melee_info\nvf_engine_stats\nwait 90\n'
    actor+='wait 45\nvf_engine_stats\nquit\n'
    (mod/'observer.cfg').write_text(observer);(peer/mod.name/'actor.cfg').write_text(actor)
    common=['-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game',mod.name,'-console','-nointro','-nowriteconfig']
    server=subprocess.Popen([str(engine/'xash.exe'),'-ip','127.0.0.1','-noip6',*common,'-port',str(serverport),'-log','melee-network-server.log','+sv_lan','1','+sv_cheats','1','+maxplayers','4','+deathmatch','1','+developer','1','+map','vf_range'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    children=[];started=time.time()
    try:
        time.sleep(3);assert server.poll() is None
        for i,(folder,cfg) in enumerate(((engine,'observer.cfg'),(peer,'actor.cfg'))):
            children.append(subprocess.Popen([str(folder/'xash3d.exe'),'-ip','127.0.0.1','-noip6',*common,'-windowed','-width','1280','-height','720','-clientport',str(clients[i]),'-log','melee-network-client.log','+exec','lab_controls.cfg','+name','Melee_'+str(i),'+connect','127.0.0.1:'+str(serverport),'+exec',cfg],cwd=folder))
            if i==0:time.sleep(3)
        for process in children:process.wait(100);assert process.returncode==0
    finally:
        for process in children+[server]:
            if process.poll() is None:process.terminate();process.wait(10)
    logs=[(folder/'melee-network-client.log').read_text(errors='replace') for folder in (engine,peer)]
    for i,log in enumerate(logs):(OUT/('network-'+str(i)+'.log')).write_text(log)
    for i,log in enumerate(logs):
        assert not any(e in log for e in ('Host_Error','SV_Error','VFState rejected'))
        assert 'VFMelee received: player=2 active=1' in log and 'VFMelee received: player=2 active=0' in log
        assert re.search(r'VFMelee received: player=2 active=1.*crouch=1',log)
    blocks=dict(re.findall(r'REMOTE_(\d+)\s+(.*?)(?=REMOTE_|$)',logs[0],re.S));frames=[];sequences=set()
    target=OUT/'network-captures';target.mkdir(exist_ok=True)
    for label,block in blocks.items():
        m=re.search(r'VFPeerPose player=2 sequence=(\d+) frame=([\d.]+).*model=models/vf_melee/',block)
        if m:
            sequence=int(m[1]);sequences.add(sequence);name='remote_'+label.zfill(3)+'.png'
            image=mod/'scrshots'/name;assert image.stat().st_mtime>=started;shutil.copy2(image,target/name);frames.append((label,sequence,float(m[2]),name))
    assert sequences==expected,frames
    for sequence in sorted(expected):
        samples=[row[2] for row in frames if row[1]==sequence]
        contact_frame=(13/30)/1.1*256
        assert len(samples)>=2 and min(samples)<contact_frame and max(samples)>contact_frame and max(samples)-min(samples)>40,(sequence,samples)
    # Preserve a chronological actual remote-view film around the gesture.
    first=int(frames[0][0]);last=int(frames[-1][0]);images=[Image.open(mod/'scrshots'/f'remote_{i:03}.png').convert('RGB').resize((960,540)) for i in range(first,last+1)]
    palette=images[0].quantize(colors=256);images=[i.quantize(palette=palette,dither=Image.Dither.NONE) for i in images]
    images[0].save(OUT/'remote-player.gif',save_all=True,append_images=images[1:],duration=117,loop=0,optimize=False)
    assert sources()==build['sources'],'Concurrent source edits require a current network test'
    report=dict(passed=True,client_sha256=digest(mod/'cl_dlls/client.dll'),server_sha256=digest(mod/'dlls/hl.dll'),renderer_sha256=digest(engine/'ref_gl.dll'),
        engine_binaries={n:digest(engine/n) for n in ('ref_gl.dll','xash.dll','xash3d.exe','xash.exe','SDL2.dll')},
        sequences=sorted(sequences),remote_frames=frames,checks=['two real native clients and dedicated loopback server','start/stop messages received by both clients','standing/crouched appended sequences rendered on remote player','remote modular rifle remains attached'])
    (OUT/'network.json').write_text(json.dumps(report,indent=2));print('PASS network melee:',len(frames),'remote standing/crouched poses; both clients synchronized',flush=True)
if __name__=='__main__':run()
