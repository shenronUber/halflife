"""Build native weapon sprites, clipped decals, sound variants and shared catalog.
Normal builds are offline. --generate-audio explicitly spends ElevenLabs credits.
"""
from pathlib import Path
import argparse, array, hashlib, json, math, shutil, struct, subprocess, wave
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT=Path(__file__).resolve().parent
ASSETS=ROOT/"assets/weapon-fx"
OUT=ROOT/"generated/weapon-fx"
DATA=ROOT/"data/weapon_fx.json"
KINDS=("muzzle","impact","particle","smoke")
SURFACES=("hard","metal","wood","flesh")

def profiles():
    d=json.loads(DATA.read_text())
    assert [p["id"] for p in d["profiles"]]==["hydro","electro","cryo","thermal","toxic","corrosion","sonic","kinetic"]
    return d["profiles"]

def generate_audio():
    import audio_workshop as a
    a.ASSETS=ASSETS/"audio"
    key=a.load_key()
    a.status(key)
    for p in profiles():
        for kind in ("fire","impact"):
            req=dict(text=p[kind+"_prompt"],duration_seconds=1.2,prompt_influence=.55,loop=False,model_id="eleven_text_to_sound_v2")
            a.generate_one(key,"sfx",dict(id=p["id"]+"_"+kind,name=p["name"]+" / "+kind),req,"/v1/sound-generation?output_format=mp3_44100_128")

def sprite(path, tile, frames, axial=False):
    # Index-alpha sprites retain continuous opacity and can be tinted by TriangleAPI.
    size=128
    data=bytearray(struct.pack("<4siiifiiifi",b"IDSP",2,2,2,size*.707107,size,size,frames,0.,0))
    data+=struct.pack("<H",256)+bytes([255,255,255])*256
    for f in range(frames):
        factor=(.76,1.,1.12,1.20)[f] if frames>1 and not axial else 1.
        fade=(1.,.90,.52,.14)[f] if frames>1 else 1.
        t=tile.copy()
        gray=t.convert("L")
        alpha=Image.frombytes("L",t.size,bytes(round(a*g/255*fade) for a,g in zip(t.getchannel("A").tobytes(),gray.tobytes())))
        wh=max(1,round(size*factor))
        alpha=alpha.resize((wh,wh),Image.Resampling.LANCZOS)
        frame=Image.new("L",(size,size));frame.paste(alpha,((size-wh)//2,(size-wh)//2))
        data+=struct.pack("<iiiii",0,-size//2,size//2,size,size)+frame.tobytes()
    path.write_bytes(data)

def miptex(name,tile,color):
    size=64
    rgba=tile.resize((size,size),Image.Resampling.LANCZOS)
    # Native transparent decal palette uses index 255 for empty pixels.
    # 0..254 interpolate a dark stain toward the profile's physical deposit.
    color=tuple(max(22,round(v*.62)) for v in color)
    indices=Image.frombytes("L",rgba.size,bytes(min(254,round((.25+.75*g/255)*254)) if a>85 else 255 for a,g in zip(rgba.getchannel("A").tobytes(),rgba.convert("L").tobytes())))
    levels=[indices.resize((size>>i,size>>i),Image.Resampling.NEAREST).tobytes() for i in range(4)]
    offsets=[40]
    for level in levels[:-1]:offsets.append(offsets[-1]+len(level))
    pal=bytes(v for n in range(255) for v in tuple(round(c*(.22+.78*n/254)) for c in color))+bytes((0,0,255))
    return struct.pack("<16s6I",name.encode(),size,size,*offsets)+b"".join(levels)+struct.pack("<H",256)+pal+b"\0\0"

def merge_decals(entries):
    base=Path("F:/SteamLibrary/steamapps/common/Half-Life/valve/decals.wad")
    raw=base.read_bytes()
    magic,count,offset=struct.unpack_from("<4sii",raw)
    assert magic==b"WAD3"
    directory=raw[offset:offset+count*32]
    data=bytearray(raw[:offset])
    new=[]
    for name,lump in entries:
        pos=len(data);data+=lump
        new.append(struct.pack("<iiiBBH16s",pos,len(lump),len(lump),0x43,0,0,name.encode()))
    off=len(data);data+=directory+b"".join(new)
    struct.pack_into("<4sii",data,0,b"WAD3",count+len(new),off)
    (OUT/"decals.wad").write_bytes(data)
    return count

def audio_variant(source,path,surface):
    import audio_workshop as a
    # Offline derived variants: different transient bodies preserve elemental identity.
    with wave.open(str(source),"rb") as f:
        assert (f.getnchannels(),f.getsampwidth(),f.getframerate())==(1,2,22050)
        samples=array.array("h",f.readframes(f.getnframes()))
    material={"hard":(180,0.07,.16),"metal":(2300,.11,.12),"wood":(350,.08,.22),"flesh":(95,.065,.28)}[surface]
    hz,decay,gain=material
    for i in range(min(len(samples),int(.32*22050))):
        t=i/22050
        transient=math.sin(2*math.pi*hz*t)*math.exp(-t/decay)*gain
        if surface=="metal":transient+=math.sin(2*math.pi*hz*1.47*t)*math.exp(-t/(decay*.7))*gain*.35
        samples[i]=max(-32767,min(32767,round(samples[i]*.70+transient*25000)))
    with wave.open(str(path),"wb") as f:f.setparams((1,2,22050,0,"NONE","not compressed"));f.writeframes(samples.tobytes())

def build():
    ps=profiles()
    (OUT/"sprites").mkdir(parents=True,exist_ok=True)
    (OUT/"sound").mkdir(parents=True,exist_ok=True)
    tilesdir=ASSETS/"tiles";tilesdir.mkdir(exist_ok=True)
    atlas=Image.open(ASSETS/"source-atlas.png").convert("RGBA")
    assert atlas.getchannel("A").getextrema()[0]==0, "Atlas must have real transparency"
    w,h=atlas.size;frontal=Image.open(ASSETS/"source-muzzle-frontal.png").convert("RGBA");assert frontal.getchannel("A").getextrema()[0]==0;cones=Image.open(ASSETS/"source-muzzle-cones-mask.png").convert("L");entries=[];sprite_files=[];sound_files=[]
    preview=Image.new("RGB",(1200,8*174+60),(16,23,31));draw=ImageDraw.Draw(preview)
    try:font=ImageFont.truetype("C:/Windows/Fonts/consola.ttf",20)
    except OSError:font=ImageFont.load_default()
    for col,label in enumerate(("axial side","impact","particle","smoke","frontal")):draw.text((218+col*194,18),label.upper(),fill=(180,200,210),font=font)
    for row,p in enumerate(ps):
        draw.text((18,104+row*174),p["name"],fill=tuple(p["color"]),font=font)
        for col,kind in enumerate(KINDS):
            box=(round(col*w/4),round(row*h/8),round((col+1)*w/4),round((row+1)*h/8))
            cell=atlas.crop(box)
            gx,gy=round(cell.width*.06),round(cell.height*.06)
            cell=cell.crop((gx,gy,cell.width-gx,cell.height-gy))
            bbox=cell.getchannel("A").point(lambda a:255 if a>8 else 0).getbbox()
            assert bbox, (p["id"],kind,"empty sprite")
            crop=cell.crop(bbox);crop.thumbnail((96,96),Image.Resampling.LANCZOS)
            tile=Image.new("RGBA",(128,128));tile.alpha_composite(crop,((128-crop.width)//2,(128-crop.height)//2))
            if kind=="muzzle":
                # Dedicated head-on radial art; never reuse the directional plume.
                fw,fh=frontal.size;fc,fr=row%4,row//4
                core=frontal.crop((round(fc*fw/4),round(fr*fh/2),round((fc+1)*fw/4),round((fr+1)*fh/2)))
                assert core.getchannel("A").getbbox()
                core.thumbnail((112,112),Image.Resampling.LANCZOS)
                centered=Image.new("RGBA",(128,128));centered.alpha_composite(core,((128-core.width)//2,(128-core.height)//2));core=centered
                # Align the emission center with the socket; atlas gutters can be uneven.
                gray=core.convert("L");weights=[a*g for a,g in zip(core.getchannel("A").tobytes(),gray.tobytes())];total=sum(weights)
                cx=sum(v*(i%128) for i,v in enumerate(weights))/total;cy=sum(v*(i//128) for i,v in enumerate(weights))/total
                shifted=Image.new("RGBA",(128,128));shifted.alpha_composite(core,(round(63.5-cx),round(63.5-cy)));core=shifted
                core.save(tilesdir/(p["id"]+"_core.png"))
                core_name=p["id"]+"_core.spr";sprite(OUT/"sprites"/core_name,core,4);sprite_files.append(core_name)
                shown=ImageOps.colorize(core.convert("L"),(0,0,0),tuple(p["color"])).convert("RGBA");shown.putalpha(core.getchannel("A"));preview.paste(shown,(202+4*194,78+row*174),shown)
                # A black emission-mask atlas encodes opacity directly in luminance.
                mask=cones.crop((0,round(row*cones.height/8),cones.width,round((row+1)*cones.height/8)))
                bounds=mask.point(lambda x:255 if x>18 else 0).getbbox()
                assert bounds
                mask=mask.crop(bounds).resize((112,96),Image.Resampling.LANCZOS)
                tile=Image.new("RGBA",(128,128),(255,255,255,0))
                opacity=Image.new("L",(128,128));opacity.paste(mask,(8,16));tile.putalpha(opacity)
            tile.save(tilesdir/(p["id"]+"_"+kind+".png"))
            name=p["id"]+"_"+kind+".spr";sprite(OUT/"sprites"/name,tile,1 if kind=="particle" else 4,axial=kind=="muzzle");sprite_files.append(name)
            tinted=ImageOps.colorize(tile.convert("L"),(0,0,0),tuple(p["color"])).convert("RGBA");tinted.putalpha(tile.getchannel("A"))
            preview.paste(tinted,(202+col*194,78+row*174),tinted)
            if kind=="impact":
                decal="{vf_"+p["id"];entries.append((decal,miptex(decal,tile,p["color"])))
        src=ASSETS/"audio/shots"/(p["id"]+"_fire.wav")
        if not src.exists():raise RuntimeError("Missing source audio; run build_weapon_fx.py --generate-audio explicitly: "+str(src))
        dest=OUT/"sound"/(p["id"]+"_fire.wav");shutil.copy2(src,dest);sound_files.append(dest.name)
        for surface in SURFACES:
            dest=OUT/"sound"/(p["id"]+"_hit_"+surface+".wav")
            audio_variant(ASSETS/"audio/shots"/(p["id"]+"_impact.wav"),dest,surface);sound_files.append(dest.name)
    # Final game exports follow the same Half-Life quality target as voices.
    # Build variants in clean PCM first, then quantize once from preserved masters.
    import audio_workshop as audio_tools
    executable=audio_tools.ffmpeg()
    if not executable:raise RuntimeError("ffmpeg required for Half-Life sound exports")
    masters=OUT/"sound-masters";masters.mkdir(exist_ok=True)
    retro_filter="highpass=f=35,lowpass=f=4800,acompressor=threshold=0.12:ratio=2:attack=1:release=45:makeup=1.1,alimiter=limit=0.90:level=false,aresample=11025:osf=u8:dither_method=triangular"
    for name in sound_files:
        target=OUT/"sound"/name;master=masters/name
        shutil.copy2(target,master)
        subprocess.run([executable,"-hide_banner","-loglevel","error","-y","-i",str(master),"-vn","-ac","1","-af",retro_filter,"-ar","11025","-c:a","pcm_u8",str(target)],check=True)
    count=merge_decals(entries)
    preview.save(ASSETS/"sprite-contact-sheet.png")
    header=['// Generated by build_weapon_fx.py. Do not edit.','#ifndef VF_WEAPON_FX_CATALOG_H','#define VF_WEAPON_FX_CATALOG_H','namespace vfshot {',
            'struct Profile { const char* id; const char* name; int color[3]; float muzzleSize,muzzleLife,trailLife,trailWidth; int particles; float particleLife,lightRadius,decalSize; };',
            'static const int Count=8; static const int Default=7;','static const Profile profiles[Count]={']
    for p in ps:
        header.append('{"%s","%s",{%s},%sf,%sf,%sf,%sf,%d,%sf,%sf,%sf},'%(p["id"],p["name"],",".join(map(str,p["color"])),*(str(float(p[k])) for k in ("muzzle_size","muzzle_life","trail_life","trail_width")),p["particles"],str(float(p["particle_life"])),str(float(p["light_radius"])),str(float(p["decal_size"]))))
    header+=['};','}','#endif','']
    (ROOT.parent/"game_shared/vf_weapon_fx_catalog.h").write_text("\n".join(header))
    manifest=dict(version=1,audio_format=dict(channels=1,rate=11025,bits=8),profiles=8,sprites=len(sprite_files),sounds=len(sound_files),custom_decals=len(entries),preserved_stock_decals=count,atlas_size=atlas.size,frontal_atlas_size=frontal.size,
                  files={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob("*")) if p.is_file() and p.name!="manifest.json"})
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({k:v for k,v in manifest.items() if k!="files"}))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--generate-audio",action="store_true");args=parser.parse_args()
    if args.generate_audio:generate_audio()
    build()
