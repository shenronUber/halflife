"""Angular/strafe contact intent and both look limits on the tested release."""
import re,json,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from library_engine_test import run_cfg
def run():
 lines=['wait 180','developer 2','con_notifytime -1','gl_vsync 0','fps_max 1000','host_framerate .016666667',
        'sv_cheats 1','god','weapon_9mmAR','wait 30','vf_reference 0','wait 20','vf_commit','wait 20','vf_character','vf_character','wait 10']
 def probe(n):lines.extend(['echo RELEASE_WR_'+n,'cmd vf_traversal_info','wait 2'])
 lines+=['cmd vf_traversal_place -800 -1006 128 300 320 0 0','vf_traversal_look 300 0','+forward','+jump','wait 4','-jump'];probe('ENTRY')
 lines+=['vf_traversal_look 90 -85','wait 5'];probe('POS_90')
 lines+=['vf_traversal_look 270 85','wait 5'];probe('NEG_90')
 lines+=['vf_traversal_look 90.1 0','wait 1'];probe('OVER_90')
 lines+=['-forward','-jump','wait 15','cmd vf_traversal_place -800 -1006 128 300 320 0 0','vf_traversal_look 300 0','+forward','wait 5'];probe('NO_JUMP')
 lines+=['-forward','wait 15','cmd vf_traversal_place -800 -1006 128 0 320 0 0','vf_traversal_look 0 0','+forward','+jump','wait 5'];probe('PARALLEL_JUMP')
 expected=dict(ENTRY=8,POS_90=8,NEG_90=8,OVER_90=0,NO_JUMP=0,PARALLEL_JUMP=0)
 # Use real bound movement commands in the native engine, on both supports.
 # Pitch deliberately misses the visible wall: entry now expresses horizontal
 # angular intent rather than an eye-ray intersection with that finite face.
 for name,y,yaw,pitch,strafe,forward,jump,z,phase in [
  ('SHALLOW_RIGHT',-1006,359,0,None,True,True,128,8),
  ('SHALLOW_LEFT',1006,1,0,None,True,True,128,8),
  ('AWAY_RIGHT',-1006,1,0,None,True,True,128,0),
  ('AWAY_LEFT',1006,359,0,None,True,True,128,0),
  ('UP_RIGHT',-1006,359,-89,None,True,True,128,8),
  ('DOWN_LEFT',1006,1,89,None,True,True,128,8),
  ('STRAFE_RIGHT',-1006,0,0,'moveright',True,True,128,8),
  ('STRAFE_LEFT',1006,0,0,'moveleft',True,True,128,8),
  ('AWAY_VIEW_STRAFE_RIGHT',-1006,60,85,'moveright',True,True,128,8),
  ('AWAY_VIEW_STRAFE_LEFT',1006,300,-85,'moveleft',True,True,128,8),
  ('WRONG_STRAFE_RIGHT',-1006,0,0,'moveleft',True,True,128,0),
  ('WRONG_STRAFE_LEFT',1006,0,0,'moveright',True,True,128,0),
  ('STRAFE_NO_JUMP',-1006,0,0,'moveright',True,False,128,0),
  ('STRAFE_NO_FORWARD',-1006,0,0,'moveright',False,True,128,0),
  ('STRAFE_TAKEOFF_RIGHT',-1006,0,0,'moveright',True,True,36.1,8),
  ('STRAFE_TAKEOFF_LEFT',1006,0,0,'moveleft',True,True,36.1,8),
 ]:
  lines+=['-forward','-jump','-moveleft','-moveright','wait 15',
          f'cmd vf_traversal_place -800 {y} {z} 0 320 0 0',f'vf_traversal_look {yaw} {pitch}']
  if forward:lines+=['+forward']
  if strafe:lines+=['+'+strafe]
  if jump:lines+=['+jump']
  lines+=['wait 12'if z<100 else'wait 5'];probe(name);expected[name]=phase
 lines+=['-forward','-jump','-moveleft','-moveright']
 lines+=['quit'];log=run_cfg('release_wallrun_intent','\n'.join(lines)+'\n',mapname='vf_traversal',timeout=90)
 states={}
 for n,b in re.findall(r'RELEASE_WR_(\w+)\s+(.*?)(?=RELEASE_WR_|$)',log,re.S):
  m=re.search(r'VFTraversal phase=(\d+).*?velocity=([-\d.,]+)',b);assert m,n
  states[n]=dict(phase=int(m[1]),velocity=list(map(float,m[2].split(','))))
 assert {n:s['phase']for n,s in states.items()}==expected,states
 for n in expected:
  if expected[n]==8:assert states[n]['velocity'][0]>280 and abs(states[n]['velocity'][1])<25,(n,states[n])
 for n in('POS_90','NEG_90'):assert states[n]['velocity'][0]>300 and abs(states[n]['velocity'][1])<25
 assert states['OVER_90']['velocity'][2]<0
 target=Path(os.environ.get('VF_RELEASE_CANDIDATE',ROOT/'build/release-integration'))/'integration/intent';target.mkdir(parents=True,exist_ok=True)
 (target/'native.json').write_text(json.dumps(dict(passed=True,states=states),indent=2));print('PASS angular and strafe contact intent, both walls, ground takeoff and free look limits')
if __name__=='__main__':run()
