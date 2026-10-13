"""Real traced fatal hits, saved regional totals, debris, and actual falling damage."""
import argparse,hashlib,json,re,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
import third_person_native_test as harness
import death_sounds_test as audio
OUT=ROOT/'build/combat-regression'

def run(candidate=None):
 candidate=Path(candidate) if candidate else None
 engine=harness.stage('combat-regression',server=candidate/'server/hl.dll' if candidate else None,client=candidate/'client/client.dll' if candidate else None,renderer=candidate/'engine' if candidate else None)
 mod=engine/'vf_animation';OUT.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT.parent/'network/delta.lst',mod/'delta.lst')
 lines=['wait 180','developer 1','con_notifytime 0','gl_vsync 0','fps_max 1000','host_framerate .016666667','sv_cheats 1','cmd give weapon_9mmAR','weapon_9mmAR','wait 30','vf_reference 0','wait 25','vf_commit','wait 25','vf_character','vf_character','cmd vf_peer_pose','wait 15']
 cases=[]
 def case(name,health,hits,mask,armor=0,commands=None):
  lines.extend(['cmd vf_death_clear','wait 3',f'echo BEGIN_{name}',f'cmd vf_anatomy_probe setup 100 {health} {armor}','wait 6'])
  lines.extend(commands or [])
  for group,amount in hits:lines.extend([f'cmd vf_anatomy_probe hit {group} {amount:.9f}','wait 2'])
  lines.extend(['cmd vf_anatomy_info','wait 5','vf_death_client',f'screenshot scrshots/{name}.png','wait 3',f'echo END_{name}'])
  cases.append((name,mask))
 groups=[1,4,5,6,7]
 for index,group in enumerate(groups):
  scale=3 if group==1 else 1
  case(f'exact_{group}',50,[(group,50/scale)],0)
  case(f'above_{group}',51,[(group,51/scale)],1<<index)
  other=groups[(index+1)%5];other_scale=3 if other==1 else 1
  case(f'wrong_final_{group}',80,[(group,60/scale),(other,20/other_scale)],0)
 case('cumulative',51,[(4,20),(4,20),(4,11)],2)
 case('central',100,[(2,100)],0)
 case('unlocalized',100,[(4,60)],0,commands=[])
 # The final hit is direct fall damage, after the localized trace was consumed.
 index=lines.index('echo END_unlocalized');lines[index:index]=['cmd vf_anatomy_probe fall 40','wait 5']
 case('armor',10,[(4,50)],0,armor=100)
 # Exercise FireBullets/FireBulletsPlayer rather than only TraceAttack.
 for weapon in ('mp5','9mm','buckshot'):
  case('real_'+weapon,51,[],2,commands=[f'cmd vf_anatomy_probe shoot 4 {8.5 if weapon=="buckshot" else 51} {weapon} {6 if weapon=="buckshot" else 1}','wait 3'])
 case('real_buckshot_armor',10,[],0,armor=100,commands=['cmd vf_anatomy_probe shoot 4 8.5 buckshot 6','wait 3'])
 lines.extend(['cmd vf_death_clear','wait 3','echo BEGIN_save','cmd vf_anatomy_probe setup 100 51 0','wait 6','cmd vf_anatomy_probe hit 4 20','wait 3','save vf_region_totals','wait 10','load vf_region_totals','wait 90','cmd vf_anatomy_info','wait 3','cmd vf_anatomy_probe hit 4 31','wait 5','echo END_save'])
 cases.append(('save',2))
 lines.extend(['cmd vf_death_clear','wait 3','echo BEGIN_god','cmd vf_anatomy_probe setup 100 100 0','wait 6','god','wait 3','cmd vf_anatomy_probe hit 4 100','wait 3','cmd vf_anatomy_info','wait 3','god','wait 3','cmd vf_anatomy_probe fall 100','wait 5','echo END_god'])
 cases.append(('god',0))
 lines.extend(['map vf_traversal','wait 120','host_framerate .016666667','fps_max 1000','vf_character','vf_character','wait 15'])
 for effect in ['hydro','electro','cryo','thermal','toxic','corrosion','sonic','kinetic']:
  lines.extend([f'echo BEGIN_fall_{effect}','cmd vf_anatomy_probe setup 100 100 0',f'vf_shotfx {effect}','wait 5','cmd vf_traversal_place 128 -750 500 0','wait 100','cmd vf_anatomy_info','cmd vf_status_info','wait 5',f'echo END_fall_{effect}'])
 lines.append('quit')
 # Avoid the engine's bounded command buffer by chaining small script chunks.
 for part,start in enumerate(range(0,len(lines),80)):
  chunk=lines[start:start+80]
  if start+80<len(lines):chunk.append(f'exec combat_regression_{part+1}.cfg')
  (mod/f'combat_regression_{part}.cfg').write_text('\n'.join(chunk)+'\n',encoding='ascii')
 started=time.monotonic();log=audio.launch(engine,'combat_regression_0.cfg','combat-regression.log')
 (OUT/'native.log').write_text(log,encoding='utf-8')
 for error in ['Host_Error','SV_Error','not precached','Could not load','VFState rejected','VFAnatomy probe missing']:assert error not in log,error
 verified=[]
 for name,mask in cases:
  part=log.split('BEGIN_'+name+' ')[1].split('END_'+name+' ')[0]
  deaths=re.findall(r'VFDeath anatomy victim=1 hitgroup=(\d+) mask=(\d+) override=(\d+)',part)
  assert len(deaths)==1 and int(deaths[0][1])==mask,(name,deaths,part[-3000:])
  fragments=re.findall(r'VFFragment spawn .*?body=(\d+).*?whole=(\d+).*?velocity=([-\d.,]+)',part)
  assert len(fragments)==(4 if mask else 0),(name,fragments)
  if mask:
   assert sum(int(f[1]) for f in fragments)==1 and len({f[2] for f in fragments})==4,(name,fragments)
   assert len(re.findall(r'VFDeathSfx play .*layer=dismemberment',part))==1,(name,part)
  if name in ('armor','real_buckshot_armor'):assert 'damage=0.000,10.000,0.000,0.000,0.000' in part,part
  if name=='god':assert 'health=100.000' in part and 'damage=0.000,0.000,0.000,0.000,0.000' in part,part
  if name=='save':assert 'damage=0.000,20.000,0.000,0.000,0.000' in part,part
  verified.append(dict(case=name,mask=mask,fragments=len(fragments)))
 falling=[]
 for effect in ['hydro','electro','cryo','thermal','toxic','corrosion','sonic','kinetic']:
  part=log.split('BEGIN_fall_'+effect+' ')[1].split('END_fall_'+effect+' ')[0]
  health=re.search(r'VFAnatomy player=1 health=([-\d.]+)',part);assert health and 0<float(health[1])<100,(effect,part)
  assert 'VFStatus apply:' not in part and 'VFStatus active:' not in part,(effect,part)
  assert 'damage=0.000,0.000,0.000,0.000,0.000' in part,(effect,part)
  falling.append(dict(profile=effect,health_after=float(health[1])))
 report=dict(passed=True,seconds=round(time.monotonic()-started,2),cases=verified,falling=falling,server_sha256=hashlib.sha256((mod/'dlls/hl.dll').read_bytes()).hexdigest(),renderer_sha256=hashlib.sha256((engine/'ref_gl.dll').read_bytes()).hexdigest())
 (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print('PASS combat regressions',json.dumps(report),flush=True)
 for name in ['above_1','above_4','above_6','exact_1']:
  shutil.copy2(mod/'scrshots'/f'{name}.png',OUT/f'{name}.png')
 return report

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--candidate-dir',type=Path);args=parser.parse_args();run(args.candidate_dir)
