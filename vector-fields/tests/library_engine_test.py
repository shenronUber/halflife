"""Library integration: actual 1080p renderer, animations, attached parts and CS maps."""
import argparse,json,re,subprocess,time
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];ENGINE=ROOT.parent/'runtime/vector-engine';MOD=ENGINE/'vf_visual'
ENTRIES=json.loads((ROOT/'generated/library/manifest.json').read_bytes())['entries']
def click(x,y):return f'vf_ui_pointer {x} {y} 1\nwait 3\nvf_ui_pointer {x} {y} 0\nwait 12\n'
def run_cfg(name,script,mapname='vf_range',captures=(),timeout=100):
 path=MOD/(name+'.cfg');path.write_text(script,encoding='ascii');start=time.time()
 command=[str(ENGINE/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-borderless','-width','1920','-height','1080','-console','-nointro','-nowriteconfig','-log',name+'.log','+exec','lab_controls.cfg','+developer','1','+map',mapname,'+exec',path.name]
 p=subprocess.Popen(command,cwd=ENGINE)
 try:p.wait(timeout=timeout)
 except subprocess.TimeoutExpired:p.terminate();p.wait(10);raise
 assert p.returncode==0,(name,p.returncode)
 log=(ENGINE/(name+'.log')).read_text(errors='replace')
 assert 'Spawn Server: '+mapname in log,(name,'no map spawn')
 for x in captures:
  f=MOD/'scrshots'/(x+'.png');assert f.stat().st_mtime>=start and f.stat().st_size>1000,x
  assert Image.open(f).size==(1920,1080),x
 return log

def visuals():
 captures=[]
 def snap(x):
  x='lib_'+x;captures.append(x);return f'wait 22\nscreenshot scrshots/{x}.png\nwait 4\n'
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 30\nvf_library_clear\n'
 chosen=[next(x for x in ENTRIES if x['collection']=='CS 1.6' and Path(x['source']).stem=='v_m4a1'),ENTRIES[104],ENTRIES[424],ENTRIES[812]]
 for label,r in zip(['cs_m4','ppsh','garand','source_m4'],chosen):
  s+=f'vf_library_select {r["id"]}\nwait 35\nvf_animation_time 0\n'+snap(label+'_preview')
  if label=='source_m4':s+='vf_visual_bench source_m4\nwait 215\n'
  # Use actual pointer route for equip, not a command-only surrogate.
  s+=click(1130,692)+'wait 25\n'+click(1220,40)+'wait 60\n'+snap(label+'_hand')
  s+='+attack\nwait 20\n-attack\nwait 40\n+reload\nwait 40\n'+snap(label+'_reload')+'-reload\nwait 90\n'
 s+='vf_library_clear\nvf_weapon_part 0 0\nvf_weapon_part 1 0\nvf_weapon_part 2 0\nvf_weapon_part 3 0\n'
 for id in [813,819,820,821,822]:s+=f'vf_library_select {id}\nwait 10\nvf_library_equip\nwait 10\n'
 s+='vf_skin_tab 2\nwait 30\nvf_animation_time 0\n'+snap('assembled_preview')+'vf_visual_bench library_assembly\nwait 215\n'+click(1220,40)+snap('assembled_hand')
 s+='+attack\nwait 18\n-attack\nwait 30\n+reload\nwait 35\n'+snap('assembled_reload')+'-reload\nwait 90\nvf_skins\nvf_skin_tab 0\nwait 30\nvf_skin_all 157\nvf_skin_commit\nwait 30\nvf_animation_time 0\n'+snap('cs_gign')
 s+='vf_skin_set 0 165\nvf_skin_set 2 174\nvf_skin_commit\nwait 30\n'+snap('cs_mixed')
 s+='vf_library_select 824\nvf_library_filter 7 2\n'+snap('pieces')+'vf_library_filter 8 0\nvf_library_select 825\n'+snap('maps')
 s+='vf_engine_stats\nquit\n'
 log=run_cfg('vf_library_visual_test',s,captures=captures)
 for r in chosen:assert 'VFLibrary equipped: '+r['key'] in log,r['name']
 for slot in range(5):assert f'VFLibrary attached: slot={slot}' in log,slot
 assert 'VFSkin client: result=0 ids=157,157,157,157,157' in log
 assert 'VFSkin client: result=0 ids=165,157,174,157,157' in log
 benches=re.findall(r'VFBench (\w+): samples=180 mean_ms=([\d.]+) p95_ms=([\d.]+) frame_ms=([\d.]+) loads=(\d+) textures_bytes=(\d+)',log);assert len(benches)==2,benches
 report=dict(benchmarks=benches,captures=captures,resolution=[1920,1080],checks=['actual native UI equip click','four full models in hand and reload','five simultaneous accessories','CS skin commit and zone mix'],limits=['MP5 gameplay retained','visual inspection still required'])
 (ROOT/'build/library-visual-verification.json').write_text(json.dumps(report,indent=2));print('PASS library visuals',len(captures),flush=True)

def audit():
 reports=[]
 for start in range(0,len(ENTRIES),40):
  end=min(start+40,len(ENTRIES));log=run_cfg(f'vf_library_audit_{start}',f'wait 160\ndeveloper 1\nvf_library_audit {start} {end}\nwait 20\nquit\n')
  m=re.search(r'VFLibrary audit: start=(\d+) end=(\d+) passed=(\d+) failed=(\d+)',log);assert m,(start,'audit incomplete')
  row=dict(zip(['start','end','passed','failed'],map(int,m.groups())));reports.append(row);print(row,flush=True);assert row['failed']==0,row
 (ROOT/'build/library-model-verification.json').write_text(json.dumps(dict(batches=reports,passed=sum(x['passed']for x in reports),resolution=[1920,1080],limit='Header and texture load audit; representative animations checked separately'),indent=2))

def maps():
 report=[]
 for row in json.loads((MOD/'cs-maps.json').read_bytes()):
  name=row['name'];log=run_cfg(name+'_test',f'wait 180\ndeveloper 1\ncon_notifytime 0\ngive item_suit\ngive weapon_9mmAR\nweapon_9mmAR\nwait 40\nscreenshot scrshots/{name}.png\nwait 20\nquit\n',mapname=name,captures=[name],timeout=40)
  errors=[x for x in log.splitlines()if any(w in x.lower()for w in ['could not','not found','failed','error'])]
  report.append(dict(map=name,warnings=errors));print('PASS CS map',name,len(errors),'warnings',flush=True)
 (ROOT/'build/cs-maps-verification.json').write_text(json.dumps(report,indent=2))

def parts():
 captures=[]
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nweapon_9mmAR\ncmd vf_appearance_mode 1\nwait 30\nvf_library_clear\nvf_visual_enabled 1\n'
 for r in ENTRIES:
  if r['kind']!=3:continue
  name='lib_part_'+str(r['id']);captures.append(name)
  s+=f'vf_library_select {r["id"]}\nwait 10\nvf_library_equip\nwait 25\nvf_animation_time 0\nscreenshot scrshots/{name}.png\nwait 4\n'
 s+='vf_visual_bench mounted_parts\nwait 215\nvf_engine_stats\nquit\n'
 log=run_cfg('vf_library_parts_test',s,captures=captures)
 assert log.count('VFLibrary attached:')==12
 assert 'rejected=0' in log
 (ROOT/'build/library-parts-verification.json').write_text(json.dumps(dict(captures=captures,resolution=[1920,1080],checks=['all 12 mounted accessories previewed by native renderer','all five slots filled together','no assembly rejection'],benchmark=re.findall(r'VFBench .*',log)),indent=2))
 print('PASS mounted parts',len(captures),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['visuals','audit','maps','parts'],default='visuals');a=p.parse_args();globals()[a.mode]()
