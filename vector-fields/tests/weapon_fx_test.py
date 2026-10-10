"""Weapon FX regression: binary resources + actual predicted fires in native engine.
Runtime staging isolates tests from the normal build and from other workshops.
"""
import argparse,array,hashlib,json,math,os,re,shutil,struct,subprocess,time,wave
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
BASE=PROJECT/"runtime/vector-engine"
OUT=ROOT/"build/weapon-fx-native"
PROFILES=json.loads((ROOT/"data/weapon_fx.json").read_text())["profiles"]
STEAM="F:/SteamLibrary/steamapps/common/Half-Life"

def assets():
    gen=ROOT/"generated/weapon-fx";report=json.loads((gen/"manifest.json").read_text())
    assert report["profiles"]==8 and report["sprites"]==40 and report["sounds"]==40 and report["custom_decals"]==8
    for name,digest in report["files"].items():assert hashlib.sha256((gen/name).read_bytes()).hexdigest()==digest,name
    for path in (gen/"sprites").glob("*.spr"):
        raw=path.read_bytes()
        magic,version,kind,fmt,radius,w,h,n,beam,sync=struct.unpack_from("<4siiifiiifi",raw)
        assert (magic,version,kind,fmt,w,h)==(b"IDSP",2,2,2,128,128),path
        assert n==(1 if "_particle." in path.name else 4)
        assert math.isfinite(radius) and radius>0
        assert struct.unpack_from("<H",raw,40)[0]==256
        offset=810
        for f in range(n):
            typ,x,y,fw,fh=struct.unpack_from("<iiiii",raw,offset);offset+=20
            assert (typ,x,y,fw,fh)==(0,-64,64,128,128)
            pixels=raw[offset:offset+w*h];offset+=w*h
            assert len(pixels)==w*h and min(pixels)==0 and max(pixels)>5 and sum(pixels)>500
        assert offset==len(raw),path
        if "_core." in path.name:
            alpha=raw[830:830+w*h];total=sum(alpha)
            cx=sum(v*(i%w) for i,v in enumerate(alpha))/total;cy=sum(v*(i//w) for i,v in enumerate(alpha))/total
            assert abs(cx-63.5)<2 and abs(cy-63.5)<2,(path,cx,cy)
            quarters=[sum(alpha[y*w+x] for y in range(q//2*64,q//2*64+64) for x in range(q%2*64,q%2*64+64))/total for q in range(4)]
            assert min(quarters)>.10 and max(quarters)<.40,(path,quarters)

    wad=(gen/"decals.wad").read_bytes();magic,n,off=struct.unpack_from("<4sii",wad)
    assert magic==b"WAD3" and n==230 and off+n*32==len(wad)
    found=[]
    for i in range(n):
        pos,disk,size,typ,compression,_,rawname=struct.unpack_from("<iiiBBH16s",wad,off+i*32)
        assert pos+disk<=off and disk==size and compression==0
        name=rawname.split(b"\0")[0].decode()
        if name.startswith("{vf_"):
            found.append(name)
            lump=wad[pos:pos+disk];_,w,h,*mips=struct.unpack_from("<16s6I",lump)
            assert (w,h)==(64,64) and typ==0x43
            assert struct.unpack_from("<H",lump,mips[-1]+8*8)[0]==256
            assert lump[-5:-2]==bytes((0,0,255))
    assert set(found)=={"{vf_"+p["id"] for p in PROFILES}
    audio=[]
    for path in (gen/"sound").glob("*.wav"):
        with wave.open(str(path)) as f:
            assert (f.getnchannels(),f.getsampwidth(),f.getframerate())==(1,1,11025),path
            samples=[s-128 for s in f.readframes(f.getnframes())]
        peak=max(abs(s) for s in samples)/128;rms=math.sqrt(sum(s*s for s in samples)/len(samples))/128
        assert 0.1<peak<.98 and rms>.002
        assert .15<len(samples)/11025<1.5
        assert abs(sum(samples)/len(samples)/128)<.08
        audio.append(dict(file=path.name,duration=round(len(samples)/11025,4),peak=round(peak,4),rms=round(rms,4)))
    assert len(audio)==40
    for p in PROFILES:
        hashes={hashlib.sha256((gen/"sound"/(p["id"]+"_hit_"+s+".wav")).read_bytes()).hexdigest() for s in ("hard","metal","wood","flesh")}
        assert len(hashes)==4
    return dict(profiles=8,sprites=40,sounds=40,decals=8,stock_decals=222,audio=audio,
        checks=["native index-alpha sprite headers, frames, nonempty alpha and buffer lengths","WAD mip offsets, palette transparency, preserved stock entries","eight frontal flashes have centered emission and light in all four quadrants","40 mono 11025 Hz / 8-bit PCM WAVs: level, duration, RMS, DC and four distinct material variants"])

def shared_copy(source,target):
    if not Path(target).exists():os.link(source,target)
    return target

def stage(name):
    engine=OUT/name;engine.mkdir(parents=True,exist_ok=True)
    for f in BASE.iterdir():
        if f.is_file() and f.suffix.lower() in (".dll",".exe"):shutil.copy2(f,engine/f.name)
    for folder in ("valve","vf_visual","cs_assets"):
        shutil.copytree(BASE/folder,engine/folder,dirs_exist_ok=True,copy_function=shared_copy,ignore=shutil.ignore_patterns("scrshots","save","*.log","*.cfg"))
    mod=engine/"vf_fx_test"
    for folder in ("dlls","cl_dlls","vf","maps","sound","sprites","scrshots"):(mod/folder).mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/"build/weaponfx-server/hl.dll",mod/"dlls/hl.dll")
    shutil.copy2(ROOT/"build/weaponfx-client/client.dll",mod/"cl_dlls/client.dll")
    shutil.copy2(ROOT/"generated/weapon-fx/decals.wad",mod/"decals.wad")
    shutil.copy2(ROOT/"generated/weapon-fx/range/vf_fx_range.bsp",mod/"maps/vf_fx_range.bsp")
    shutil.copytree(ROOT/"generated/weapon-fx/sprites",mod/"sprites/vf_weaponfx",dirs_exist_ok=True)
    shutil.copytree(ROOT/"generated/weapon-fx/sound",mod/"sound/vf_weaponfx",dirs_exist_ok=True)
    for source,target in [("data/equipment.txt","equipment.txt"),("data/r01_styles.txt","r01_styles.txt"),("generated/visual_skins/skins.txt","skins.txt"),("generated/skins/arsenal.txt","arsenal.txt")]:
        shutil.copy2(ROOT/source,mod/"vf"/target)
    (mod/"vf/native_engine.txt").write_text("Isolated weapon FX test\n")
    (mod/"gameinfo.txt").write_text('title "Vector Fields / Weapon FX test"\nbasedir "valve"\nfallback_dir "vf_visual"\ngamedll "dlls/hl.dll"\ndllpath "cl_dlls"\ngamemode "normal"\nmax_edicts "2048"\n')
    # Explicit material table: fallback chains are one level on some engine builds.
    shutil.copy2(BASE/"cs_assets/sound/materials.txt",mod/"sound/materials.txt")
    return engine,mod

def click(x,y):return f"vf_ui_pointer {x} {y} 1\nwait 3\nvf_ui_pointer {x} {y} 0\nwait 12\n"
def run_cfg(engine,mod,name,script,timeout=70,mapname="vf_fx_range"):
    (mod/(name+".cfg")).write_text(script,encoding="ascii")
    command=[str(engine/"xash3d.exe"),"-rodir",STEAM,"-game","vf_fx_test","-borderless","-width","1920","-height","1080","-console","-nointro","-nowriteconfig","-log",name+".log","+sv_cheats","1","+map",mapname,"+exec",name+".cfg"]
    p=subprocess.Popen(command,cwd=engine)
    try:p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
    assert p.returncode==0,p.returncode
    return (engine/(name+".log")).read_text(errors="replace")

def native():
    engine,mod=stage("single");captures=[]
    s="gl_vsync 0\nfps_max 60\nwait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nvf_voices 0\nvf_voice_subtitles 0\nweapon_9mmAR\nvf_operator\nwait 30\n"+click(1220,40)+"wait 30\nvf_shotfx_debug 1\nvf_shotfx_audit\n"
    for p in PROFILES:
        name="shotfx_"+p["id"];captures+=[name]
        s+=f'echo FX_CASE_{p["id"]}\ncmd vf_fx_camera concrete\nvf_shotfx {p["id"]}\nwait 16\nvf_shotfx_clear\n+attack\nwait 2\nscreenshot scrshots/{name}.png\nwait 1\n-attack\nwait 24\nvf_shotfx_stats\n'
    for surface in ("metal","wood","flesh","sky","brush"):
        name="shotfx_surface_"+surface;captures+=[name]
        s+=f'echo FX_SURFACE_{surface}\ncmd vf_fx_camera {surface}\nwait 16\nvf_shotfx_clear\n+attack\nwait 2\nscreenshot scrshots/{name}.png\nwait 1\n-attack\nwait 24\nvf_shotfx_stats\n'
    s+='echo FX_BUDGET\ncmd vf_fx_camera concrete\nvf_shotfx toxic\nwait 16\nvf_shotfx_clear\n+attack\nwait 150\n-attack\nwait 3\nvf_shotfx_stats\nwait 100\nvf_shotfx_stats\n'
    s+='echo FX_SAVE\nvf_shotfx cryo\nwait 15\nsave vf_fx_state\nwait 30\nvf_shotfx thermal\nwait 15\nload vf_fx_state\nwait 180\ndeveloper 1\ncon_notifytime 0\nvf_shotfx_debug 1\n+attack\nwait 2\n-attack\nwait 24\nvf_shotfx_stats\n'
    s+='echo FX_INVALID\ncmd vf_fx_profile unknown\nwait 12\nvf_shotfx auto\nwait 12\nvf_shotfx_clear\n+attack\nwait 2\n-attack\nwait 20\nvf_shotfx_stats\nvf_shotfx_lab\nwait 20\nscreenshot scrshots/shotfx_ui.png\nwait 2\nquit\n'
    captures+=["shotfx_ui"]
    started=time.time();log=run_cfg(engine,mod,"weapon-fx-native",s,timeout=80)
    (ROOT/"build/weapon-fx-native.log").write_text(log)
    assert "VFShot audit: profiles=8 sprites=40/40 decals=8/8" in log
    sections={}
    for p in PROFILES:
        case=log.split("FX_CASE_"+p["id"],1)[1].split("FX_",1)[0]
        assert f'profile={p["id"]} local=1' in case,p["id"]
        assert "shots=1 hits=1 misses=0 decals=1 audio=2" in case,(p["id"],case[-1500:])
        front=re.findall(r"muzzle_front=(\d+) muzzle_side=(\d+)",case);assert front and int(front[-1][0])>0 and int(front[-1][1])==0,(p["id"],"shooter must render only frontal art")
        stock=[int(x) for x in re.findall(r"stock_suppressed=(\d+)",case)];assert stock and max(stock)>0,(p["id"],"legacy model flash was not suppressed")
        sections[p["id"]]=re.findall(r"VFShot stats: .*",case)[-1]
    for surface,key in [("metal","metal=1"),("wood","wood=1"),("flesh","flesh=1"),("sky","sky=1"),("brush","decals=1")]:
        case=log.split("FX_SURFACE_"+surface,1)[1].split("FX_",1)[0]
        assert key in case,(surface,case[-1800:])
        if surface in ("flesh","sky"):assert "decals=0" in case
    budget=log.split("FX_BUDGET",1)[1].split("FX_SAVE",1)[0]
    peaks=[int(x) for x in re.findall(r"peak=(\d+)",budget)];assert peaks and max(peaks)<=512
    assert "alive=0" in re.findall(r"VFShot stats: .*",budget)[-1]
    saved=log.split("Loading game from save/vf_fx_state.sav",1)[1].split("FX_INVALID",1)[0]
    assert "profile=cryo local=1" in saved
    assert "VFShot rejected" in log.split("FX_INVALID",1)[1]
    assert "profile=kinetic local=1" in log.split("FX_INVALID",1)[1]
    for name in captures:
        path=mod/"scrshots"/(name+".png")
        assert path.stat().st_mtime>=started and Image.open(path).size==(1920,1080),name
    assert "Decal has invalid texture" not in log and "VFState rejected" not in log
    sheet=Image.new("RGB",(1280,4*400),(16,23,31));draw=ImageDraw.Draw(sheet)
    try:font=ImageFont.truetype("C:/Windows/Fonts/consola.ttf",23)
    except OSError:font=ImageFont.load_default()
    for i,p in enumerate(PROFILES):
        frame=Image.open(mod/"scrshots"/("shotfx_"+p["id"]+".png")).convert("RGB");frame.thumbnail((640,360))
        x=(i%2)*640;y=(i//2)*400;sheet.paste(frame,(x,y+40));draw.text((x+15,y+9),p["name"],font=font,fill=tuple(p["color"]))
    preview=ROOT/"assets/weapon-fx/in-game-contact-sheet.jpg";sheet.save(preview,quality=92)
    return dict(profiles=sections,captures=[str(mod/"scrshots"/(x+".png")) for x in captures],peak_particles=max(peaks),preview=str(preview),
        checks=["8 actual predicted primary-fire events: one shot, one hit, one decal, two audio triggers each","concrete, metal, wood and studio contact; sky excluded; brush-local decal","bounded burst and pool returns to zero","developer profile survives save/load; invalid profile rejected; auto restores Kinetic","eight shooter views render frontal art and zero axial plume frames; legacy model flash suppressed","native 1080p screenshots produced"],
        limits=["audio quality and effect aesthetics need human listening/visual review","unchanged MP5 hitscan damage; elemental statuses and reactions are not activated"])

if __name__=="__main__":
    a=argparse.ArgumentParser();a.add_argument("--mode",choices=("assets","native","all"),default="assets");args=a.parse_args();report={}
    if args.mode in ("assets","all"):report["assets"]=assets()
    if args.mode in ("native","all"):report["native"]=native()
    (ROOT/"build"/("weapon-fx-"+args.mode+"-verification.json")).write_text(json.dumps(report,indent=2))
    print("PASS weapon FX",args.mode,json.dumps({k:{"checks":v["checks"]} for k,v in report.items()}))
