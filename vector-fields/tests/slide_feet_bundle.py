"""Isolated slide review using installed assets and an incremental visual build."""
import atexit,hashlib,json,os,shutil,sys,_winapi
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from build_traversal_range import build as build_range
from native_workspace import engine_path,private_copy,shared_copy
from release import check_native_interface

BUILD=ROOT/'build/slide-feet'
INSTALLED=Path(os.environ.get('VF_TEST_ENGINE',ROOT.parent/'runtime/vector-engine'))
_fallbacks=[]

def unlink_fallbacks():
    # Remove only the directory junction, never recurse into its target.
    for link in _fallbacks:
        if link.exists():os.rmdir(link)

# Registered after native_workspace.finish, so links disappear before its
# guarded archive/cleanup walks the private session.
atexit.register(unlink_fallbacks)

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def prepare_slide_feet(name,build=BUILD,server=None,engine_binaries=None,client=None):
    engine=engine_path(ROOT/'build/animation-native'/('slide-feet-'+name));engine.mkdir(parents=True)
    for path in (engine_binaries or build/'engine').iterdir():
        if path.is_file() and path.suffix.lower() in ('.dll','.exe','.json'):private_copy(path,engine/path.name)
    # Stock resources and sounds remain read-only fallback inputs; the game
    # writes exclusively into vf_animation with -nowriteconfig. This avoids
    # cloning unrelated maps, audio and workshop launch configurations.
    for folder in ('valve','tfc_assets','vf_visual'):
        link=engine/folder;_winapi.CreateJunction(str(INSTALLED/folder),str(link));_fallbacks.append(link)
    mod=engine/'vf_animation';baseline=INSTALLED/'vf_visual'
    for folder in ('vf','cl_dlls','dlls','maps','scrshots'):(mod/folder).mkdir(parents=True,exist_ok=True)
    private_copy(client or build/'client/client.dll',mod/'cl_dlls/client.dll')
    private_copy(server or INSTALLED/'vf_visual/dlls/hl.dll',mod/'dlls/hl.dll')
    # The other animation chat owns the generated banks. Review our visual
    # switch with the installed R1 assets, never its unpublished experiments.
    for folder in ('vf','models/vf_r01','models/vf_skins','models/vf_deaths','models/vf_traversal','models/vf_headgear'):
        if(baseline/folder).is_dir():
            shutil.copytree(baseline/folder,mod/folder,dirs_exist_ok=True,copy_function=shared_copy)
    private_copy(ROOT.parent/'network/delta.lst',mod/'delta.lst')
    private_copy(build_range(ensure=True),mod/'maps/vf_traversal.bsp')
    (mod/'gameinfo.txt').write_text('title "Vector Fields - Slide review"\nbasedir "valve"\nfallback_dir "vf_visual"\ngamedll "dlls/hl.dll"\ndllpath "cl_dlls"\ngamemode "normal"\nmax_edicts "2048"\n')
    check_native_interface(engine,mod/'cl_dlls/client.dll')
    return engine,mod
