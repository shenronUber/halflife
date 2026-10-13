"""Disposable native test engines; immutable resources shared by content hash.

Only test workspaces are removed. Canonical runtime and authoring workshops are
never linked for writes or cleaned. Logs/captures survive in native-evidence.
"""
import atexit,hashlib,json,os,shutil,uuid,time,socket
from contextlib import contextmanager
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SESSIONS=ROOT/'build/native-sessions'
CACHE=ROOT/'build/native-resources'
EVIDENCE=ROOT/'build/native-evidence'
SESSION=SESSIONS/(str(os.getpid())+'-'+uuid.uuid4().hex[:12])
IMMUTABLE={'.mdl','.spr','.bsp','.wad','.pk3','.pak','.png','.jpg','.jpeg','.tga','.bmp'}
_engines={}
_index={}
_blob_ids={}
_loaded=False

def checked_child(path,parent):
 path=Path(path).absolute();parent=Path(parent).resolve()
 resolved=path.resolve()
 if resolved==parent or parent not in resolved.parents:raise ValueError('Workspace cleanup target escaped its root: '+str(path))
 # A junction inside a test tree must never redirect deletion into a library.
 for item in (path,*path.parents):
  if item==parent:break
  if item.exists() and getattr(item.lstat(),'st_file_attributes',0)&0x400:
   raise ValueError('Reparse point in test workspace: '+str(item))
 return resolved

def remove_tree(path,parent):
 path=checked_child(path,parent)
 if not path.exists():return
 for folder,dirs,files in os.walk(path,followlinks=False):
  for name in dirs+files:
   entry=Path(folder)/name
   if entry.is_symlink() or getattr(entry.lstat(),'st_file_attributes',0)&0x400:
    raise ValueError('Refusing to clean a tree containing links: '+str(entry))
 shutil.rmtree(path)

def engine_path(legacy_path):
 """Keep a stable path within this process, isolate concurrent test processes."""
 legacy=Path(legacy_path).absolute()
 if ROOT.parent not in legacy.parents:raise ValueError('Test engine must be inside the project')
 name='--'.join(legacy.relative_to(ROOT.parent).parts)
 engine=SESSION/name
 _engines[engine]=name
 return engine

@contextmanager
def file_lock(path,timeout=60):
 """OS-owned advisory lock: released even when a test process crashes."""
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a+b') as handle:
  if path.stat().st_size==0:handle.write(b'0');handle.flush()
  started=time.monotonic()
  while True:
   try:
    handle.seek(0)
    if os.name=='nt':
     import msvcrt
     msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
    else:
     import fcntl
     fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    break
   except OSError:
    if time.monotonic()-started>=timeout:raise TimeoutError('Test workspace lock timed out: '+str(path))
    time.sleep(.025)
  try:yield
  finally:
   handle.seek(0)
   if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
   else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


def wait_for_log(path,markers,processes=(),timeout=60):
 """Wait for observed engine state, fail on process exit or a bounded timeout."""
 path=Path(path);markers=(markers,)if isinstance(markers,str)else tuple(markers)
 if not markers or any(not marker for marker in markers):raise ValueError('Readiness needs nonempty log markers')
 deadline=time.monotonic()+timeout;text=''
 while time.monotonic()<deadline:
  for process in processes:
   code=process.poll()
   if code is not None:raise RuntimeError(f'Engine exited with code {code} before readiness: {path}')
  if path.is_file():text=path.read_text(encoding='utf-8',errors='replace')
  if all(marker in text for marker in markers):return text
  time.sleep(.05)
 missing=[marker for marker in markers if marker not in text]
 raise TimeoutError(f'Engine readiness timed out: {path}; missing {missing}\n'+text[-1500:])

def port():
 """Let the OS choose a free local UDP port for an isolated native launch."""
 with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as bound:
  bound.bind(('127.0.0.1',0));return bound.getsockname()[1]


def stage_installed(engine,mod_name='vf_visual'):
 """Snapshot the installed release without placing test files in its runtime."""
 SESSIONS.mkdir(parents=True,exist_ok=True)
 engine=checked_child(engine,SESSIONS);base=Path(os.environ.get('VF_TEST_ENGINE',ROOT.parent/'runtime/vector-engine'))
 engine.mkdir(parents=True,exist_ok=True)
 for source in base.iterdir():
  if source.is_file() and (source.suffix.lower() in {'.dll','.exe'} or source.name=='vector-engine-build.json'):
   private_copy(source,engine/source.name)
 (engine/'valve').mkdir(exist_ok=True)
 for name in ('tfc_assets','cs_assets'):
  if (base/name).exists():copy_resources(base/name,engine/name,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
 mod=engine/mod_name
 copy_resources(base/'vf_visual',mod,ignore=shutil.ignore_patterns('scrshots','save','*.log'))
 for name in ('save','scrshots'):(mod/name).mkdir(exist_ok=True)
 return mod


def shared_copy(source,target):
 """Copy mutable files; hardlink media to an independent immutable snapshot.

 Rebuilding a canonical model later cannot silently modify an earlier test.
 """
 global _loaded
 source=Path(source);target=Path(target)
 target.parent.mkdir(parents=True,exist_ok=True)
 # Audio deployment helpers and the font renderer may rewrite files directly.
 # Keep those private even when they live in a copied game directory.
 if source.suffix.lower() not in IMMUTABLE or '.fontcache' in source.parts:
  return shutil.copy2(source,target)
 CACHE.mkdir(parents=True,exist_ok=True)
 if not _loaded:
  index=CACHE/'index.json'
  _index.update(json.loads(index.read_text()) if index.exists() else {})
  _loaded=True
  for digest in {r['sha256']for r in _index.values()}:
   blob=CACHE/digest
   if blob.is_file():
    stat=blob.stat();_blob_ids[(stat.st_dev,stat.st_ino)]=digest
 stat=source.stat();key=str(source.resolve())
 stamp=[stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns]
 record=_index.get(key,{})
 if record.get('stamp')!=stamp:
  # A multiplayer peer can clone files already linked to this immutable cache.
  digest=_blob_ids.get((stat.st_dev,stat.st_ino)) or hashlib.sha256(source.read_bytes()).hexdigest()
  record=dict(stamp=stamp,sha256=digest);_index[key]=record
 blob=CACHE/record['sha256']
 with file_lock(CACHE/'.lock'):
  if not blob.exists():
   pending=CACHE/(record['sha256']+'.'+uuid.uuid4().hex+'.tmp')
   shutil.copy2(source,pending)
   # Atomic publication. Parallel writers of this hash have identical content.
   if blob.exists():pending.unlink()
   else:pending.replace(blob)
  blob_stat=blob.stat();_blob_ids[(blob_stat.st_dev,blob_stat.st_ino)]=record['sha256']
  if target.exists():target.unlink()
  try:os.link(blob,target)
  except OSError:shutil.copy2(blob,target) # a different volume still works
 return str(target)

def copy_resources(source,target,**kwargs):
 kwargs.setdefault('dirs_exist_ok',True)
 kwargs.setdefault('copy_function',shared_copy)
 return shutil.copytree(source,target,**kwargs)

def private_copy(source,target):
 """Detach a staged hardlink before a test overrides one of its media files."""
 target=Path(target)
 if target.is_file() and target.stat().st_nlink>1:
  checked_child(target,SESSIONS)
  target.unlink()
 return shutil.copy2(source,target)

def selected_captures(paths,limit=32):
 paths=sorted(paths)
 if len(paths)<=limit:return paths
 return [paths[round(i*(len(paths)-1)/(limit-1))]for i in range(limit)]

def copy_retired_captures(source,target):
 source=Path(source);target=Path(target)
 for p in selected_captures([p for p in source.rglob('*')if p.is_file()]):
  dest=target/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)

def compact_captures(root,limit=32):
 """Bound retired screenshots per case; logs and saves remain complete."""
 root=Path(root);removed=0
 for case in root.iterdir():
  if not case.is_dir()or case.name.startswith('.'):continue
  checked_child(case,root)
  paths=[p for p in case.rglob('*')if p.is_file()and 'scrshots'in p.parts and p.suffix.lower()in('.png','.jpg','.bmp','.tga')]
  kept=set(selected_captures(paths,limit))
  for p in paths:
   if p not in kept:checked_child(p,root).unlink();removed+=1
 return removed

def retire_engine(engine,destination):
 """Preserve diagnostics before removing the disposable tree."""
 engine=checked_child(engine,SESSIONS)
 destination=checked_child(destination,EVIDENCE)
 destination.mkdir(parents=True,exist_ok=True)
 for path in engine.iterdir():
  if path.is_file() and path.suffix.lower() in {'.log','.json'}:shutil.copy2(path,destination/path.name)
  elif path.is_dir() and path.name not in {'valve','tfc_assets','cs_assets','vf_visual'}:
   # Active isolated mods, not fallback media libraries.
   for folder in ('scrshots','save'):
    if (path/folder).exists():
     if folder=='scrshots':copy_retired_captures(path/folder,destination/path.name/folder)
     else:shutil.copytree(path/folder,destination/path.name/folder,dirs_exist_ok=True)
   for cfg in path.glob('*.cfg'):
    target=destination/path.name/cfg.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(cfg,target)
 # Some older harnesses use vf_visual or valve as their writable game mod.
 for folder in ('vf_visual','valve'):
  for child in ('scrshots','save'):
   if (engine/folder/child).exists():
    if child=='scrshots':copy_retired_captures(engine/folder/child,destination/folder/child)
    else:shutil.copytree(engine/folder/child,destination/folder/child,dirs_exist_ok=True)
 # Full capture sequences used by harnesses remain in their published OUT.
 # The disposable engine keeps only a representative retired sample.
 screenshots=[p for p in destination.rglob('*')if p.is_file()and 'scrshots'in p.parts and p.suffix.lower()in('.png','.jpg','.bmp','.tga')]
 kept=set(selected_captures(screenshots))
 for p in screenshots:
  if p not in kept:checked_child(p,EVIDENCE).unlink()
 remove_tree(engine,SESSIONS)

def publish_evidence(engine,name):
 """Archive privately, then replace the latest proof under a case-specific lock."""
 EVIDENCE.mkdir(parents=True,exist_ok=True)
 target=checked_child(EVIDENCE/name,EVIDENCE)
 pending=EVIDENCE/(name+'.pending-'+uuid.uuid4().hex)
 retire_engine(engine,pending)
 with file_lock(EVIDENCE/'.locks'/(name+'.lock')):
  backup=EVIDENCE/(name+'.previous-'+uuid.uuid4().hex)
  if target.exists():target.replace(backup)
  try:pending.replace(target)
  except Exception:
   if backup.exists():backup.replace(target)
   raise
  if backup.exists():remove_tree(backup,EVIDENCE)


def finish():
 if not SESSION.exists():return
 try:
  for engine,name in _engines.items():
   if engine.exists():
    publish_evidence(engine,name)
  if SESSION.exists():remove_tree(SESSION,SESSIONS)
  if _loaded:
   with file_lock(CACHE/'.lock'):
    # Merge metadata from other processes; races only trigger an extra rehash.
    index=CACHE/'index.json'
    current=json.loads(index.read_text()) if index.exists() else {}
    current.update(_index)
    fresh={}
    for key,record in current.items():
     source=Path(key)
     if source.suffix.lower() not in IMMUTABLE or '.fontcache' in source.parts:continue
     if source.is_file():
      stat=source.stat()
      if record['stamp']==[stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns]:fresh[key]=record
    current=fresh
    pending=CACHE/('index-'+uuid.uuid4().hex+'.tmp')
    pending.write_text(json.dumps(current),encoding='utf-8');pending.replace(index)
    retained={v['sha256']for v in current.values()}
    for blob in CACHE.iterdir():
     if len(blob.name)==64 and blob.name not in retained and blob.stat().st_nlink==1:blob.unlink()
 except Exception as error:
  # No deletion after a failed diagnostic archive or locked live DLL.
  print('Native workspace retained for inspection:',SESSION,error,flush=True)

atexit.register(finish)
