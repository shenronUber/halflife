"""Intentional contact and both inclusive look limits on the tested release."""
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
 lines+=['quit'];log=run_cfg('release_wallrun_intent','\n'.join(lines)+'\n',mapname='vf_traversal',timeout=90)
 states={}
 for n,b in re.findall(r'RELEASE_WR_(\w+)\s+(.*?)(?=RELEASE_WR_|$)',log,re.S):
  m=re.search(r'VFTraversal phase=(\d+).*?velocity=([-\d.,]+)',b);assert m,n
  states[n]=dict(phase=int(m[1]),velocity=list(map(float,m[2].split(','))))
 assert {n:s['phase']for n,s in states.items()}==dict(ENTRY=8,POS_90=8,NEG_90=8,OVER_90=0,NO_JUMP=0,PARALLEL_JUMP=0),states
 for n in('POS_90','NEG_90'):assert states[n]['velocity'][0]>300 and abs(states[n]['velocity'][1])<25
 assert states['OVER_90']['velocity'][2]<0
 target=Path(os.environ.get('VF_RELEASE_CANDIDATE',ROOT/'build/release-integration'))/'integration/intent';target.mkdir(parents=True,exist_ok=True)
 (target/'native.json').write_text(json.dumps(dict(passed=True,states=states),indent=2));print('PASS intentional contact and free look limits')
if __name__=='__main__':run()
