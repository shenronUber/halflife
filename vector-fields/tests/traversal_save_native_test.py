"""Save in one process, restore in another with the actual engine serializer."""
import json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from traversal_multiplayer_test import prepare
OUT=ROOT/'docs/validation/traversal'

def run():
 engine,mod=prepare('save-regression');OUT.mkdir(parents=True,exist_ok=True)
 results={}
 def launch(label,commands):
  cfg=label+'.cfg';log=label+'.log';(mod/cfg).write_text('\n'.join(commands)+'\n',encoding='ascii')
  process=subprocess.Popen([str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-dev','2','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','800','-height','600','-nointro','-nowriteconfig','-log',log,'+sv_cheats','1','+developer','2','+map','vf_traversal','+exec',cfg],cwd=engine)
  try:process.wait(timeout=50)
  finally:
   if process.poll()is None:process.terminate();process.wait(timeout=8)
  assert process.returncode==0,(label,process.returncode)
  text=(engine/log).read_text(errors='replace');shutil.copy2(engine/log,OUT/log)
  row=re.search(r'SAVE_STATE\s+.*?VFTraversal phase=(\d+) state=(\d+) origin=([\d.,-]+).*?time=([\d.-]+).*?clip=(-?\d+)',text,re.S)
  assert row,(label,text[-3000:])
  return dict(phase=int(row[1]),state=int(row[2]),origin=list(map(float,row[3].split(','))),remaining=float(row[4]),clip=int(row[5]))
 init=['wait 180','developer 2','gl_vsync 0','fps_max 60','sv_cheats 1','cmd give weapon_9mmAR','weapon_9mmAR','wait 30',
       'cmd vf_traversal_place 238 0 54 0','wait 1','+jump','wait 22','-jump','wait 35']
 for name,phase,extra in [('hang',2,[]),('armed',3,['+attack2','wait 2','-attack2','wait 35','vf_traversal_look 180'])]:
  before=launch('save-'+name,init+extra+['echo SAVE_STATE','cmd vf_traversal_info','wait 2','save vf_regression_'+name,'wait 12','quit'])
  after=launch('restore-'+name,['wait 180','gl_vsync 0','fps_max 60','load vf_regression_'+name,'wait 35','developer 2','echo SAVE_STATE','cmd vf_traversal_info','wait 8','quit'])
  assert before['phase']==phase and after['phase']==phase,(name,before,after)
  assert before['state']==after['state'] and before['clip']==after['clip'],(name,before,after)
  assert max(abs(a-b)for a,b in zip(before['origin'],after['origin']))<.1,(name,before,after)
  results[name]=dict(before=before,after=after)
 # Versioned historical fixture contains no traversal save fields.
 legacy=ROOT/'tests/fixtures/traversal-pre-save-fields.sav'
 shutil.copy2(legacy,mod/'save/vf_legacy_traversal.sav')
 state=launch('restore-legacy',['wait 180','load vf_legacy_traversal','wait 35','developer 2','echo SAVE_STATE','cmd vf_traversal_info','wait 8','quit'])
 assert state['phase']==0 and state['state']==0,state
 results['legacy']=state
 (OUT/'save-restore.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 print('PASS native traversal save/restore:',json.dumps(results),flush=True)

if __name__=='__main__':run()
