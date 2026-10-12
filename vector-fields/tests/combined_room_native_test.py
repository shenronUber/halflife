"""Actual combat and traversal in the same installed main map and session."""
import os,re,json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from library_engine_test import run_cfg,MOD
def run():
 s=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','fps_max 60','host_framerate .016666667','sv_cheats 1','god',
    'weapon_9mmAR','vf_reference 0','wait 25','vf_commit','wait 25','vf_character','vf_character','wait 10',
    'cmd vf_range_reset 0','cmd vf_fx_profile thermal','cmd vf_range_fire 0 6','wait 10','cmd vf_range_info',
    'cam_command 2','cmd vf_traversal_place 1252 0 36 0','vf_traversal_look 0 0','wait 4','+forward','+jump','wait 8','-jump',
    'echo COMBINED_VAULT','cmd vf_traversal_info','-forward','wait 70',
    'cmd vf_traversal_place 1518 -500 54 0','vf_traversal_look 0 0','wait 2','+jump','wait 22','-jump','wait 20',
    'echo COMBINED_HANG','cmd vf_traversal_info','+back','+jump','wait 3',
    'echo COMBINED_PUSH','cmd vf_traversal_info','-back','vf_traversal_look 180 0','wait 40',
    'echo COMBINED_CAUGHT','cmd vf_traversal_info','-jump',
    'cmd vf_traversal_place 1400 -1006 128 300 320 0 0','vf_traversal_look 300 0','+forward','+jump','wait 4','-jump','vf_traversal_look 0 0','wait 4',
    'echo COMBINED_RUN','cmd vf_traversal_info','screenshot scrshots/combined_wallrun_first.png',
    'cam_snapto 1','cam_idealdist 130','cam_idealyaw -90','cam_command 1','wait 8','screenshot scrshots/combined_wallrun_third.png',
    '-forward','wait 20','cam_command 2','cmd vf_traversal_place 1960 -750 36 0','wait 5','+forward','wait 15','+duck','wait 5',
    'echo COMBINED_SLIDE','cmd vf_traversal_info','-forward','-duck','wait 80',
    'cmd vf_melee_place -300 -240 36 0 0','wait 5','cmd vf_range_info','screenshot scrshots/combined_combat.png','wait 3','quit']
 log=run_cfg('combined_room','\n'.join(s)+'\n',timeout=100)
 states={n:int(p)for n,p in re.findall(r'COMBINED_(\w+)\s+VFTraversal phase=(\d+)',log)}
 assert states==dict(VAULT=1,HANG=2,PUSH=7,CAUGHT=2,RUN=8,SLIDE=5),states
 assert 'VFProc target=0' in log and 'effect=thermal hits=6' in log
 assert 'Host_Error'not in log and 'VFState rejected'not in log
 out=Path(os.environ.get('VF_RELEASE_CANDIDATE',ROOT/'build/release-integration'))/'integration/combined-room';out.mkdir(parents=True,exist_ok=True)
 for name in ['combined_wallrun_first','combined_wallrun_third','combined_combat']:shutil.copy2(MOD/'scrshots'/(name+'.png'),out/(name+'.png'))
 (out/'native.json').write_text(json.dumps(dict(passed=True,map='vf_range',states=states,shooting_proc=True),indent=2));print('PASS combined combat and traversal room',states)
if __name__=='__main__':run()
