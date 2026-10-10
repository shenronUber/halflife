"""Developer-only sealed arena: concrete, metal, wood, brush and studio targets."""
from pathlib import Path
import hashlib, importlib.util, json, subprocess
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"generated/weapon-fx/range"
def build():
    OUT.mkdir(parents=True,exist_ok=True)
    marker=OUT/"source.sha256"
    source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if marker.exists() and marker.read_text()==source and (OUT/"vf_fx_range.bsp").exists():return
    spec=importlib.util.spec_from_file_location("vf_fx_map_asset",ROOT.parent/"asset-probe/generate_assets.py")
    asset=importlib.util.module_from_spec(spec);spec.loader.exec_module(asset)
    def entity(p,brushes=()):
        return "{\n"+"".join(f'"{k}" "{v}"\n' for k,v in p.items())+"\n".join(brushes)+"\n}\n"
    walls=[((-528,-528,-16),(528,528,0),"FIFTIES_FLR01"),
           ((-528,-528,256),(528,528,272),"SKY"),
           ((-528,-528,0),(-512,528,256),"CRETE3_WALL01"),
           ((512,-528,0),(528,528,256),"CRETE3_WALL01"),
           ((-512,-528,0),(512,-512,256),"CRETE3_WALL01"),
           ((-512,512,0),(512,528,256),"CRETE3_WALL01")]
    for y,tex in [(-260,"CRETE3_WALL01"),(-80,"C1A1_FLR1"),(100,"CRATE01")]:
        walls.append(((256,y-75,0),(272,y+75,156),tex))
    text=entity(dict(classname="worldspawn",message="Vector Fields / Weapon FX test range",wad="F:/SteamLibrary/steamapps/common/Half-Life/valve/halflife.wad",skyname="desert"),[asset.map_box(*b) for b in walls])
    text+=entity(dict(classname="info_player_start",origin="0 -260 36",angle="0"))
    for y in (-260,-80,100,340):text+=entity(dict(classname="info_player_deathmatch",origin=f"0 {y} 36",angle="0"))
    text+=entity(dict(classname="game_player_equip",targetname="fx_equipment",spawnflags="1",item_suit="1",weapon_9mmAR="1",ammo_9mmbox="2"))
    text+=entity(dict(classname="trigger_once",target="fx_equipment"),[asset.map_box((-64,-324,0),(64,-196,100),"AAATRIGGER")])
    text+=entity(dict(classname="cycler",model="models/vf_skins/persona_rig.mdl",origin="240 340 36",angle="180"))
    # A brush entity exercises native entity-relative decal placement/clipping.
    text+=entity(dict(classname="func_door",targetname="fx_brush",angle="90",speed="30",wait="2",spawnflags="32"),[asset.map_box((256,200,0),(272,275,156),"C1A1_FLR1")])
    for x in (-380,0,380):
        for y in (-380,0,380):text+=entity(dict(classname="light",origin=f"{x} {y} 220",_light="230 235 255 500"))
    path=OUT/"vf_fx_range.map";path.write_text(text,encoding="ascii")
    tools=ROOT.parent/"asset-probe/sdhlt/sdhlt-v1.3.0/tools/Win64"
    for stage in ("CSG","BSP","VIS","RAD"):
        cmd=[str(tools/f"sdHL{stage}_x64.exe"),"-threads","2"]
        if stage=="CSG":cmd+=["-wadinclude","halflife.wad"]
        cmd.append(str(path.with_suffix("")))
        p=subprocess.run(cmd,capture_output=True)
        (OUT/(stage+".log")).write_bytes(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError("FX test map build failed: "+stage)
    assert "leaked" not in path.with_suffix(".log").read_text(errors="replace").lower()
    marker.write_text(source)
    print("Built developer FX range",path.with_suffix(".bsp").stat().st_size)
if __name__=="__main__":build()
