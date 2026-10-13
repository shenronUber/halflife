"""Build, test and atomically publish a source-pinned complete game bundle."""
import argparse,hashlib,json,os,shutil,subprocess,sys,uuid
from pathlib import Path
from datetime import datetime,timezone
from native_workspace import file_lock,copy_resources,private_copy
from release import verify_deployment,check_native_interface
from build_weapon_melee import sources
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
LIVE=PROJECT/'runtime/vector-engine';OUT=ROOT/'build/releases'
RECEIPT=LIVE/'vf_visual/vf/release-bundle.json'
LOCK=ROOT/'build/release.lock'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def inputs():
 result=sources()
 paths=list(ROOT.glob('*.py'))+list(ROOT.glob('*.ps1'))+list((PROJECT/'weapon-lab').glob('*.py'))+[ROOT/'version.json',PROJECT/'asset-probe/generate_assets.py']
 paths += [p for p in(ROOT/'tests').rglob('*')if p.is_file()and p.suffix in('.py','.c','.cpp','.h')]
 paths += list(PROJECT.glob('*.cmd'))+[PROJECT/'devtools/bootstrap-worktree.py']
 for folder in ('data','assets','engine','animation-workshop/traversal','melee-workshop'):
  extensions={'.json','.txt','.py','.js','.smd','.qc','.inc','.h','.c','.cpp','.patch'}
  if folder=='assets':extensions|={'.bmp','.png','.wav'}
  paths += [p for p in(ROOT/folder).rglob('*')if p.is_file()and p.suffix.lower()in extensions and 'review-backups'not in p.parts and '__pycache__'not in p.parts]
 paths += [ROOT/p for p in ['melee-workshop/Frappe-au-canon-R1-poing.blend','animation-workshop/traversal/blender/Corps-R1-revue-complete.blend','animation-workshop/traversal/blender/Mains-R1-revue-complete.blend']]
 for p in paths:result[str(p.relative_to(PROJECT))]=sha(p)
 return result
def identity(state):return hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest()
def engine_identity():
 paths=[p for p in(ROOT/'engine').rglob('*')if p.is_file()and p.suffix in('.patch','.h','.inc','.c','.cpp')]
 paths += [PROJECT/'game_shared'/name for name in('vf_engine_api.h','vf_assembly_policy.h','vf_player_pose.h','vf_pose_cache.h','vf_headgear.h','vf_traversal.h','vf_wallrun.h')]
 return identity({str(p.relative_to(PROJECT)):sha(p)for p in paths})
def run(arguments,folder,env=None):
 folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True)
 with folder.open('w',encoding='utf-8')as log:
  child=subprocess.Popen(arguments,cwd=PROJECT,env=env,stdout=log,stderr=subprocess.STDOUT)
  try:code=child.wait()
  except BaseException:
   child.terminate();child.wait(timeout=15);raise
 if code:raise RuntimeError(f'Command failed ({code}): {folder}\n'+folder.read_text(errors='replace')[-3500:])
 print('PASS',folder.name,flush=True)
def verify_bundle(candidate):
 candidate=Path(candidate);manifest=read(candidate/'bundle.json')
 for name,value in manifest['files'].items():
  if sha(candidate/'engine'/name)!=value:raise RuntimeError('Bundle changed after validation: '+name)
 return manifest
def fixture(candidate):
 candidate=Path(candidate);target=candidate/'fixture';game=candidate/'engine/vf_visual'
 target.mkdir(exist_ok=True)
 for a,b in [('cl_dlls','client'),('dlls','server'),('models','models'),('maps','maps'),('vf','vf')]:
  shutil.copytree(game/a,target/b,dirs_exist_ok=True,copy_function=private_copy if a in('cl_dlls','dlls')else shutil.copy2)
 shutil.copy2(game/'delta.lst',target/'delta.lst')
 shutil.copytree(candidate/'sdk/source',target/'source',dirs_exist_ok=True)
 shutil.copytree(candidate/'engine',target/'engine',dirs_exist_ok=True,ignore=shutil.ignore_patterns('vf_visual','valve','tfc_assets','cs_assets'))
 (target/'generated/third-person').mkdir(parents=True,exist_ok=True)
 from game_profiles import MAPS
 for name,row in MAPS.items():
  dest=target/'generated'/row['source']/(name+'.bsp');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(game/'maps'/(name+'.bsp'),dest)
 for p in(game/'models/vf_r01').glob('r01_tp*.mdl'):shutil.copy2(p,target/'generated/third-person'/p.name)
 assets=[]
 for folder,view in [('vf_traversal','first-person'),('vf_r01','third-person')]:
  for p in(game/'models'/folder).glob('*.mdl'):
   if folder=='vf_r01'and not p.name.startswith('r01_tp'):continue
   assets.append(dict(candidate=str(target/'models'/folder/p.name),relative=f'models/{folder}/{p.name}',model=p.stem,view=view,sha256=sha(p)))
 (target/'assets.json').write_text(json.dumps(assets,indent=2))
 return target
def create():
 OUT.mkdir(parents=True,exist_ok=True)
 candidate=OUT/(datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);candidate.mkdir()
 before=inputs();(candidate/'source-inputs.json').write_text(json.dumps(before,indent=2))
 import build_wall_jump_native as sdk
 # Incremental objects are private, locked and never deployed. Every candidate
 # receives its own frozen source/binary copy after both compilers succeed.
 sdk.OUT=OUT/'sdk-cache';sdk.OUT.mkdir(exist_ok=True);sdk.refresh_game(sdk.OUT/'source')
 for folder in('client','server','source'):
  shutil.copytree(sdk.OUT/folder,candidate/'sdk'/folder,dirs_exist_ok=True)
 if inputs()!=before:raise RuntimeError('Sources changed during build; retry against a stable worktree.')
 engine=candidate/'engine';engine.mkdir()
 for p in LIVE.iterdir():
  if p.is_file()and(p.suffix in('.exe','.dll')or p.name=='vector-engine-build.json'):shutil.copy2(p,engine/p.name)
 pending_engine=ROOT/'build/engine-candidate'
 engine_updated=False
 if(pending_engine/'vector-engine-build.json').exists():
  metadata=read(pending_engine/'vector-engine-build.json')
  try:check_native_interface(pending_engine,candidate/'sdk/client/client.dll')
  except RuntimeError:print('Older incompatible engine candidate ignored; keeping the matching installed engine.',flush=True)
  else:
   if metadata.get('engine_source_identity')!=engine_identity():raise RuntimeError('Engine candidate sources are stale; run build-engine.ps1 before publishing.')
   for name,value in metadata['binaries'].items():
    if sha(pending_engine/name).lower()!=value.lower():raise RuntimeError('Engine candidate hash differs: '+name)
   for p in pending_engine.iterdir():
    if p.is_file()and(p.suffix in('.exe','.dll')or p.name=='vector-engine-build.json'):shutil.copy2(p,engine/p.name)
   engine_updated=True
 if RECEIPT.exists()and read(RECEIPT).get('engine_source_identity')!=engine_identity()and not engine_updated:
  raise RuntimeError('Engine sources changed. Build the private engine candidate with build-engine.ps1 before publishing.')
 for folder in ('valve','tfc_assets','cs_assets'):
  if(LIVE/folder).exists():copy_resources(LIVE/folder,engine/folder,ignore=shutil.ignore_patterns('save','scrshots','*.log'))
 env=dict(os.environ,VF_RELEASE_SDK=str(candidate/'sdk'),VF_TEST_ENGINE=str(engine))
 run([sys.executable,str(ROOT/'play.py'),'--visual-lab','--deploy-only','--stage-engine',str(engine),'--sdk-build',str(candidate/'sdk')],candidate/'prepare.log',env)
 if inputs()!=before:raise RuntimeError('Authoring sources changed during preparation; candidate was not published.')
 files={str(p.relative_to(engine)):sha(p)for p in engine.rglob('*')if p.is_file()and not any(x in p.parts for x in('save','scrshots'))and p.suffix!='.log'and p.name not in('config.cfg','vf_voice_behavior.cfg','release-bundle.json')}
 manifest=dict(id=candidate.name,source_identity=identity(before),engine_source_identity=engine_identity(),files=files,passed=False,created_utc=datetime.now(timezone.utc).isoformat())
 (candidate/'bundle.json').write_text(json.dumps(manifest,indent=2))
 env['VF_RELEASE_BUNDLE']=str(fixture(candidate));env['VF_RELEASE_CANDIDATE']=str(candidate)
 run([sys.executable,str(ROOT/'validate.py'),'--suite','unit','--suite','policy','--suite','assets','--suite','integration'],candidate/'validation.log',env)
 if inputs()!=before:raise RuntimeError('Sources changed during validation; candidate was not published.')
 verify_bundle(candidate);verify_deployment(engine/'vf_visual',sdk=candidate/'sdk');check_native_interface(engine,engine/'vf_visual/cl_dlls/client.dll')
 manifest['passed']=True;manifest['validation']=read(ROOT/'build/validation-unit-policy-assets-integration.json')
 (candidate/'bundle.json').write_text(json.dumps(manifest,indent=2));return candidate
def publish(candidate,live=LIVE,canonical=ROOT/'build'):
 candidate=Path(candidate);live=Path(live);canonical=Path(canonical)
 manifest=verify_bundle(candidate)
 if not manifest['passed']:raise RuntimeError('Publication requires a successfully validated bundle.')
 if manifest['source_identity']!=identity(inputs()):raise RuntimeError('Validated bundle is stale; rebuild before publishing.')
 if manifest.get('engine_source_identity')!=engine_identity():raise RuntimeError('Validated engine sources are stale; rebuild before publishing.')
 token=uuid.uuid4().hex[:10];current=live/'vf_visual';pending=live/('.vf_visual-next-'+token);backup=live/('.vf_visual-before-'+token)
 pending.mkdir(parents=True);replaced=[];swapped=False
 try:
  for name in manifest['files']:
   path=Path(name)
   if path.parts[0]=='vf_visual':
    dest=pending/Path(*path.parts[1:]);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(candidate/'engine'/path,dest)
  # Retain player saves and personal controls when replacing the release.
  if(current/'save').exists():shutil.copytree(current/'save',pending/'save',dirs_exist_ok=True)
  for name in ('config.cfg','vf_voice_behavior.cfg'):
   if(current/name).exists():shutil.copy2(current/name,pending/name)
  receipt=dict(manifest,candidate=str(candidate));(pending/'vf/release-bundle.json').write_text(json.dumps(receipt,indent=2))
  for name in ('cl_dlls/client.dll','dlls/hl.dll'):
   if(current/name).exists():
    with(current/name).open('r+b'):pass
  for name,value in manifest['files'].items():
   path=Path(name)
   if path.parts[0]=='vf_visual':continue
   dest=live/path
   if dest.is_file()and sha(dest)==value:continue
   dest.parent.mkdir(parents=True,exist_ok=True)
   saved=candidate/'publication-backup/engine'/path;saved.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists():
    with dest.open('r+b'):pass
    shutil.copy2(dest,saved)
   temp=dest.with_name(dest.name+'.next');shutil.copy2(candidate/'engine'/path,temp);os.replace(temp,dest);replaced.append((dest,saved))
  for name in ('client/client.dll','server/hl.dll'):
   dest=canonical/name;dest.parent.mkdir(parents=True,exist_ok=True)
   saved=candidate/'publication-backup'/name;saved.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists():shutil.copy2(dest,saved)
   temp=dest.with_suffix('.next');shutil.copy2(candidate/'sdk'/name,temp);os.replace(temp,dest);replaced.append((dest,saved))
  if current.exists():os.replace(current,backup)
  try:os.replace(pending,current);swapped=True
  except BaseException:
   if backup.exists():os.replace(backup,current)
   raise
  old=os.environ.pop('VF_RELEASE_SDK',None)
  try:verify_deployment(current)
  finally:
   if old is not None:os.environ['VF_RELEASE_SDK']=old
  print('PASS published complete release',manifest['id'],flush=True)
 except BaseException:
  if swapped:
   os.replace(current,pending)
   if backup.exists():os.replace(backup,current)
  for dest,saved in reversed(replaced):
   if saved.exists():shutil.copy2(saved,dest)
   elif dest.exists():dest.unlink()
  raise
 # The previous complete mod stays available for recovery. No authoring files
 # or player save directories are deleted by publication.
 return manifest
def installed_current():
 if not RECEIPT.exists():return False
 receipt=read(RECEIPT)
 if not receipt.get('passed')or receipt['source_identity']!=identity(inputs()):return False
 if receipt.get('engine_source_identity')!=engine_identity():return False
 for name,value in receipt['files'].items():
  p=LIVE/name
  if not p.is_file()or sha(p)!=value:return False
 return True
def retain_releases():
 from release_retention import cleanup
 if not RECEIPT.exists():return
 try:
  report=cleanup(OUT,LIVE,ROOT/'build/retention')
  print('Release retention:',len(report['removed']),'obsolete generated trees removed.',flush=True)
 except (OSError,ValueError,RuntimeError)as error:print('Retention deferred; validated release retained:',error,flush=True)
def ensure_published(force=False):
 with file_lock(LOCK,timeout=60):
  # Prune previous failed candidates before allocating another complete game.
  retain_releases()
  if not force and installed_current():print('Verified installed release is current.',flush=True)
  else:publish(create())
  retain_releases()
def launch_command(mapname='vf_range',reference=False,seed=0,engine=None):
 from game_profiles import MAPS,arrival_config
 engine=LIVE if engine is None else Path(engine)
 if mapname not in MAPS and not(engine/'vf_visual/maps'/(mapname+'.bsp')).is_file():raise ValueError('Unknown map: '+mapname)
 if mapname in('vf_modular','vf_tiles')and(type(seed)is not int or not 0<=seed<=2147483647):raise ValueError('seed must be 0..2147483647')
 command=[str(engine/'xash3d.exe'),'-ip','127.0.0.1','-noip6','-rodir','F:/SteamLibrary/steamapps/common/Half-Life','-game','vf_visual','-windowed','-width','1280','-height','720','-nointro','+exec','lab_controls.cfg']
 # Xash initializes the game DLL before processing startup commands. Apply the
 # server's choices before its sole map request instead of scheduling it twice.
 if mapname=='vf_tiles':command+=['+vf_tiles_variant','-1']
 if mapname in('vf_modular','vf_tiles'):command+=['+vf_modular_seed',str(seed)]
 return command+['+map',mapname,'+exec',arrival_config(mapname,reference)+'.cfg']

def launch(mapname='vf_range',reference=False,seed=0):
 command=launch_command(mapname,reference,seed)
 with file_lock(LOCK):
  if not RECEIPT.exists()or not read(RECEIPT).get('passed'):raise RuntimeError('Prepare the validated release first.')
  for name,value in read(RECEIPT)['files'].items():
   path=LIVE/name
   if not path.is_file()or sha(path)!=value:raise RuntimeError('Installed release differs; use the normal launcher to rebuild: '+name)
  child=subprocess.Popen(command,cwd=LIVE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
 return child.wait()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--force',action='store_true');p.add_argument('--publish',type=Path);p.add_argument('--launch-only',action='store_true');p.add_argument('--map',default='vf_range');p.add_argument('--engine-identity',action='store_true');a=p.parse_args()
 if a.engine_identity:print(engine_identity());raise SystemExit(0)
 if a.launch_only:raise SystemExit(launch(a.map))
 if a.publish:
   with file_lock(LOCK):publish(a.publish);retain_releases()
 else:ensure_published(a.force)
