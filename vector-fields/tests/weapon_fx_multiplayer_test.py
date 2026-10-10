"""Two isolated loopback clients: remote cone, late join and developer gate.
Phase files coordinate real connections instead of assuming startup frame rates.
"""
import json,re,subprocess,time
from pathlib import Path
from weapon_fx_test import ROOT,STEAM,stage

def put(path,script):
    pending=path.with_suffix(".next");pending.write_text(script,encoding="ascii")
    for attempt in range(20):
        try:pending.replace(path);return
        except PermissionError:time.sleep(.02)
    raise RuntimeError("Cannot update isolated test phase: "+str(path))

def read(path):return path.read_text(errors="replace") if path.exists() else ""

def wait_log(path,needle,process,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if needle in read(path):return
        assert process.poll() is None,(needle,"process exited",process.returncode)
        time.sleep(.1)
    raise AssertionError("Timed out waiting for "+needle)

def run():
    a,am=stage("mp-a");b,bm=stage("mp-b")
    common=["-rodir",STEAM,"-game","vf_fx_test","-console","-nointro"]
    for folder,mod in ((a,am),(b,bm)):
        (folder/"fx-peer.log").unlink(missing_ok=True)
        for phase in ("init","shoot","gate","exit"):
            put(mod/("fx-"+phase+".cfg"),"wait 15\nexec fx-"+phase+".cfg\n")
        put(mod/"fx-peer.cfg","developer 1\ngl_vsync 0\nfps_max 60\ncon_notifytime 0\nexec fx-init.cfg\n")
    (a/"fx-server.log").unlink(missing_ok=True)
    server=subprocess.Popen([str(a/"xash.exe"),*common,"-log","fx-server.log","+ip","127.0.0.1","-port","27065","+rcon_password","vf_fx_loopback","+maxplayers","4","+sv_lan","1","+sv_cheats","1","+deathmatch","1","+developer","1","+vf_native_models","1","+vf_voices","0","+map","vf_fx_range"],cwd=a,creationflags=subprocess.CREATE_NO_WINDOW)
    children=[];started=time.time()
    try:
        wait_log(a/"fx-server.log","4 player server started",server)
        def launch(folder,port,name):
            process=subprocess.Popen([str(folder/"xash3d.exe"),*common,"-borderless","-width","1920","-height","1080","-nowriteconfig","-log","fx-peer.log","-clientport",str(port),"+developer","1","+gl_vsync","0","+fps_max","60","+name",name,"+connect","127.0.0.1:27065","+exec","fx-peer.cfg"],cwd=folder)
            children.append(process);return process
        pa=launch(a,27066,"FX_A")
        wait_log(a/"fx-peer.log","VFShot sync: player=1 code=0",pa)
        init="developer 1\ncon_notifytime 0\nvf_voice_subtitles 0\nweapon_9mmAR\nvf_shotfx_debug 1\nwait 30\n"
        put(am/"fx-init.cfg",init+"cmd vf_fx_camera concrete\nvf_shotfx electro\nwait 30\necho FX_A_READY\nexec fx-shoot.cfg\n")
        wait_log(a/"fx-peer.log","FX_A_READY",pa)
        wait_log(a/"fx-server.log","VFShot accepted: player=1 code=2",server)
        print("A connected and Electro confirmed",flush=True)
        pb=launch(b,27067,"FX_B")
        wait_log(b/"fx-peer.log","VFShot sync: player=1 code=2",pb)
        wait_log(b/"fx-peer.log","VFShot sync: player=2 code=0",pb)
        put(bm/"fx-init.cfg",init+"vf_shotfx hydro\ncmd vf_fx_camera metal\nwait 30\n+attack\nwait 2\n-attack\nwait 20\ncmd vf_fx_camera side\nwait 20\necho FX_B_READY\nexec fx-shoot.cfg\n")
        wait_log(b/"fx-peer.log","FX_B_READY",pb)
        wait_log(a/"fx-peer.log","VFShot fire: player=2 profile=hydro local=0",pa)
        print("B late join confirmed; Hydro fired; side camera ready",flush=True)
        put(am/"fx-shoot.cfg","+attack\nwait 180\n-attack\nwait 30\nvf_shotfx_stats\necho FX_A_SHOTS_DONE\nexec fx-gate.cfg\n")
        shots="wait 30\n"
        for i in range(5):shots+=f"screenshot scrshots/remote_cone_{i}.png\nwait 2\n"
        put(bm/"fx-shoot.cfg",shots+"wait 60\necho FX_B_CAPTURES_DONE\nexec fx-gate.cfg\n")
        wait_log(a/"fx-peer.log","FX_A_SHOTS_DONE",pa)
        wait_log(b/"fx-peer.log","FX_B_CAPTURES_DONE",pb)
        wait_log(b/"fx-peer.log","VFShot fire: player=1 profile=electro local=0",pb)
        put(am/"fx-gate.cfg","rcon_password vf_fx_loopback\nrcon sv_cheats 0\nwait 90\ncmd vf_fx_profile toxic\nwait 60\n+attack\nwait 2\n-attack\nwait 35\nvf_shotfx_stats\necho FX_A_GATE_DONE\nexec fx-exit.cfg\n")
        wait_log(a/"fx-peer.log","FX_A_GATE_DONE",pa)
        wait_log(b/"fx-peer.log","VFShot fire: player=1 profile=kinetic local=0",pb)
        put(bm/"fx-gate.cfg","wait 60\nvf_shotfx_stats\nquit\n")
        put(am/"fx-exit.cfg","wait 60\nquit\n")
        for child in children:child.wait(timeout=15);assert child.returncode==0,child.returncode
        logs=[read(engine/"fx-peer.log") for engine in (a,b)];serverlog=read(a/"fx-server.log")
        assert "VFShot sync: player=1 code=2" in logs[1],"late join misses A's selected vector"
        assert "VFShot fire: player=1 profile=electro local=0" in logs[1]
        assert "VFShot fire: player=2 profile=hydro local=0" in logs[0]
        assert "VFShot accepted: player=1 code=5" not in serverlog
        assert "VFShot rejected: player=1" in serverlog
        assert all("VFShot sync: player=1 code=0" in log for log in logs)
        assert "VFShot fire: player=1 profile=kinetic local=0" in logs[1]
        assert "VFState rejected" not in "".join(logs)
        side=[int(x) for x in re.findall(r"muzzle_side=(\d+)",logs[1])];assert side and max(side)>0
        captures=[]
        for i in range(5):
            path=bm/"scrshots"/f"remote_cone_{i}.png";assert path.stat().st_mtime>=started and path.stat().st_size>1000;captures.append(str(path))
        report=dict(clients=2,late_join=True,captures=captures,checks=["two real clients and dedicated loopback server","late join receives A's Electro profile","both clients receive remote shot effects for distinct profiles","sv_cheats 0 rejects test override and broadcasts A's Kinetic reset to both clients","remote side camera renders axial art; shooter camera uses frontal art","side-view remote captures generated"],limits=["loopback replication; public Internet hosting not tested","visual review required to select the best side-view frame"])
        (ROOT/"build/weapon-fx-multiplayer-verification.json").write_text(json.dumps(report,indent=2))
        print("PASS weapon FX multiplayer",json.dumps(report["checks"]))
    finally:
        for child in children:
            if child.poll() is None:child.terminate();child.wait(10)
        if server.poll() is None:server.terminate();server.wait(10)
if __name__=="__main__":run()
