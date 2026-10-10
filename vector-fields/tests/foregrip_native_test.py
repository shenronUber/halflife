"""One short isolated first-person run: three feeds, reloads, accessory switch."""
import json,re,shutil,subprocess,time,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import third_person_native_test as harness
BASE=harness.BASE;OUT=ROOT/'build/foregrip'

def run():
 OUT.mkdir(exist_ok=True);engine=harness.stage('foregrip');mod=engine/'vf_animation'
 # Use the current installed engine/server; only the new client and six carriers differ.
 for name in ('xash.dll','ref_gl.dll'):shutil.copy2(BASE/name,engine/name)
 shutil.copy2(ROOT/'build/server/hl.dll',mod/'dlls/hl.dll')
 for path in (ROOT/'generated/r01').glob('r01_rig*.mdl'):shutil.copy2(path,mod/'models/vf_r01'/path.name)
 captures=[]
 def snap(name):
  captures.append(name);return f'screenshot scrshots/{name}.png\nwait 2\n'
 def close():return 'vf_ui_pointer 1220 40 1\nwait 3\nvf_ui_pointer 1220 40 0\nwait 12\n'
 s='wait 180\ndeveloper 1\ncon_notifytime 0\nfps_max 60\nweapon_9mmAR\ngod\nvf_reference 0\nwait 35\nvf_item gign_gloves_gign\nvf_item gign_torso_gign\nvf_commit\nwait 25\n'+close()
 for platform,receiver in [('bottom','a'),('side','side'),('top','top')]:
  s+='vf_reference\nwait 25\n'+f'vf_item r01_receiver_{receiver}__original\n'
  s+='vf_item r01_underbarrel_a__medieval-forge\nvf_commit\nwait 25\n'+close()
  s+=f'echo FOREGRIP_{platform}\nvf_engine_stats\n'+snap(platform+'_hold')
  s+='+attack\nwait 12\n-attack\nwait 10\n+reload\nwait 2\n-reload\nwait 22\n'+snap(platform+'_out')
  s+='wait 50\n'+snap(platform+'_in')+'wait 40\n'+snap(platform+'_return')+'cmd vf_reload_info\n'
 s+='vf_reference\nwait 25\nvf_item r01_underbarrel_b__original\nvf_commit\nwait 25\n'+close()+'echo STANDARD_TOP\nvf_engine_stats\n'+snap('standard_top')
 s+='vf_reference\nwait 25\nvf_item r01_underbarrel_a__living-jungle\nvf_commit\nwait 25\n'+close()+'echo STYLED_FOREGRIP_TOP\nvf_engine_stats\n'+snap('styled_top')+'quit\n'
 (mod/'foregrip_test.cfg').write_text(s,encoding='ascii')
 started=time.time()
 command=[str(engine/'xash3d.exe'),'-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_animation','-windowed','-width','1920','-height','1080','-console','-nointro','-nowriteconfig','-log','foregrip-test.log','+exec','lab_controls.cfg','+developer','1','+sv_cheats','1','+map','vf_range','+exec','foregrip_test.cfg']
 child=subprocess.Popen(command,cwd=engine)
 try:child.wait(timeout=55);assert child.returncode==0
 finally:
  if child.poll() is None:child.terminate();child.wait(10)
 return verify(engine,started,captures)

def verify(engine,started=None,captures=None):
 mod=engine/'vf_animation'
 if captures is None:captures=[f'{p}_{q}'for p in ['bottom','side','top']for q in ['hold','out','in','return']]+['standard_top','styled_top']
 log=(engine/'foregrip-test.log').read_text(encoding='utf-8',errors='replace')
 assert 'VFState rejected'not in log and 'rejected=0'in log
 cases={}
 for label,rig in [('FOREGRIP_bottom','r01_rig_fg'),('FOREGRIP_side','r01_rig_side_fg'),('FOREGRIP_top','r01_rig_top_fg'),('STANDARD_TOP','r01_rig_top'),('STYLED_FOREGRIP_TOP','r01_rig_top_fg')]:
  part=re.split(re.escape(label)+r'\s*\n',log)[-1];match=re.search(r'VFFirstPerson: .*rig=models/vf_r01/(\S+)\.mdl',part);assert match and match[1]==rig,(label,match[1]if match else log[-2000:]);cases[label]=match[1]
 for label in ['STANDARD_TOP','STYLED_FOREGRIP_TOP']:
  part=re.split(re.escape(label)+r'\s*\n',log)[-1]
  assert re.search(r'VFPeerPose .*model=models/vf_r01/r01_tp_top\.mdl',part)
 assert log.count('active=0 clip=50 model=models/vf_r01/r01_tp')==3
 for name in captures:
  path=mod/'scrshots'/(name+'.png');assert path.exists() and (started is None or path.stat().st_mtime>=started) and path.stat().st_size>1000,name
  assert Image.open(path).size==(1920,1080)
 report=dict(elapsed_seconds=round(time.time()-started,2)if started else None,cases=cases,captures=[str(mod/'scrshots'/(n+'.png'))for n in captures],checks=['native first-person carrier switches on each of three feeds','fire/reload/return captured for every feed','replacing grip with auxiliary tube restores standard hand pose','styled foregrip uses the same authored grip','no rejected state or renderer assemblies','current installed engine and server used; installed files untouched during test'])
 report['loaded_client_sha256']=__import__('hashlib').sha256((mod/'cl_dlls/client.dll').read_bytes()).hexdigest()
 report['carriers']={p.name:__import__('hashlib').sha256(p.read_bytes()).hexdigest()for p in (mod/'models/vf_r01').glob('r01_rig*.mdl')}
 report['checks']+=['recharges finish with 50 rounds and no reload in progress','third-person top carrier stays identical when replacing or styling the foregrip']
 report['verification_mode']='live run'if started else'saved native run'
 (OUT/'native-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PASS native foregrip',json.dumps(report))
 return report
if __name__=='__main__':
 if '--verify'in sys.argv:verify(harness.OUT/'foregrip')
 else:run()
