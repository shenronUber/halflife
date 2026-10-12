"""Enter the installed concept traversal bay, with the ordinary game controls."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;LIVE=ROOT.parent/'runtime/vector-engine'
def main():
    config=LIVE/'vf_visual/vf/parkour_play.cfg'
    lines=['wait 180','sv_cheats 1','god','weapon_9mmAR','wait 30','vf_reference','wait 20',
        'vf_item r01_receiver_a47__original','vf_commit','wait 25','vf_character','wait 5','vf_character','wait 15',
        'cmd vf_traversal_place 1440 882 36 0','vf_traversal_look 0 0','firstperson','r_drawviewmodel 1',
        'cam_snapto 1','cam_idealdist 130','cam_idealyaw 90','cam_idealpitch 8',
        'bind F9 "map vf_traversal; exec vf/parkour_play.cfg"',
        'bind F10 "thirdperson; r_drawviewmodel 0"','bind F12 "firstperson; r_drawviewmodel 1"',
        'bind v "vf_melee"','echo Parcours : glisser sous la traverse, courir le long du mur, le regarder et sauter pour accrocher.',
        'echo Wall run : garder avancer. Regard libre jusqu a 90 degres du cap de course; au-dela on lache.',
        'echo Rebond : S + ESPACE, tourner le regard vers la galerie, maintenir ESPACE pour reprendre la prise.',
        'echo F9 : depart / F10 : troisieme personne / F12 : premiere personne.']
    config.write_text('\n'.join(lines)+'\n',encoding='ascii')
    process=subprocess.Popen([str(LIVE/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life',
        '-game','vf_visual','-windowed','-width','1280','-height','720','-nointro','-nowriteconfig',
        '+sv_cheats','1','+maxplayers','1','+map','vf_traversal','+exec','vf/parkour_play.cfg'],cwd=LIVE,creationflags=subprocess.CREATE_NO_WINDOW)
    return process.wait()
if __name__=='__main__':sys.exit(main())
