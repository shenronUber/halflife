"""Play the tested wall-run build with isolated binaries and installed equipment."""
import shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from build_wallrun_range import build
from native_workspace import engine_path,stage_installed,private_copy,port
def main():
    engine=engine_path(ROOT/'build/wallrun-intent/play')
    mod=stage_installed(engine,'vf_animation')
    private_copy(build(ensure=True),mod/'maps/vf_wallrun.bsp')
    lines=['wait 180','sv_cheats 1','cmd give weapon_9mmAR','cmd give ammo_9mmbox','weapon_9mmAR',
        'wait 20','vf_reference 0','wait 30','vf_commit','wait 35','vf_character','vf_character',
        'bind F9 "map vf_wallrun"','bind F10 "cam_command 1"','bind F12 "cam_command 2"',
        'cam_snapto 1','cam_idealdist 120','cam_idealyaw 0','cam_idealpitch 8','con_notifytime 0',
        'echo Wall run: courir le long du mur, le regarder et maintenir ESPACE pour accrocher.',
        'echo Garder avancer: la course garde son cap. Regard libre jusqu a 90 degres; au-dela, on lache.',
        'echo Relacher puis appuyer sur ESPACE: rebond vers le regard. F10: vue 3D. F12: vue subjective.']
    (mod/'wallrun_play.cfg').write_text('\n'.join(lines)+'\n',encoding='ascii')
    process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game','vf_animation','-windowed','-width','1280','-height','720','-nointro','-nowriteconfig',
        '-log','wallrun-play.log','-port',str(port()),'-clientport',str(port()),'+sv_cheats','1','+maxplayers','1',
        '+map','vf_wallrun','+exec','wallrun_play.cfg'],cwd=engine,creationflags=subprocess.CREATE_NO_WINDOW)
    return process.wait()
if __name__=='__main__':sys.exit(main())
