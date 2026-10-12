"""Verify classic launch update validation and refusal to replace loaded native files."""
import ctypes,hashlib,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release import prepare_native_renderer_update,check_native_interface,ROOT
NAMES=('xash3d.exe','xash.dll','xash.exe','ref_gl.dll','SDL2.dll')
def run():
 with tempfile.TemporaryDirectory(dir=ROOT/'build') as directory:
  root=Path(directory);engine=root/'engine';update=root/'update';engine.mkdir();update.mkdir()
  client=root/'client.dll';client.write_bytes(b'v3 connected VFStatus arms: renderer=1')
  for n in NAMES:(engine/n).write_bytes(b'old-'+n.encode());(update/n).write_bytes(b'verified-'+n.encode())
  old={'extension_version':3};(engine/'vector-engine-build.json').write_text(json.dumps(old))
  meta={'extension_version':3,'status_viewmodel_version':1,'status_feedback_verified':True,'binaries':{n:hashlib.sha256((update/n).read_bytes()).hexdigest() for n in NAMES}}
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  try:check_native_interface(engine,client)
  except RuntimeError:pass
  else:raise AssertionError('arm-shell client must refuse old renderer')
  original=(update/'ref_gl.dll').read_bytes();(update/'ref_gl.dll').write_bytes(original+b'bad')
  try:prepare_native_renderer_update(engine,client,update)
  except RuntimeError as error:assert 'hash differs' in str(error)
  else:raise AssertionError('unverified bytes accepted')
  assert all((engine/n).read_bytes()==b'old-'+n.encode() for n in NAMES)
  (update/'ref_gl.dll').write_bytes(original)
  kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateFileW.restype=ctypes.c_void_p
  held=kernel.CreateFileW(str(engine/'ref_gl.dll'),0x80000000,0,None,3,0,None);assert held not in (None,ctypes.c_void_p(-1).value)
  try:
   try:prepare_native_renderer_update(engine,client,update)
   except RuntimeError as error:assert 'Close the running' in str(error)
   else:raise AssertionError('loaded/locked DLL accepted')
   assert all((engine/n).read_bytes()==b'old-'+n.encode() for n in NAMES if n!='ref_gl.dll')
  finally:kernel.CloseHandle(ctypes.c_void_p(held))
  assert prepare_native_renderer_update(engine,client,update)
  assert all((engine/n).read_bytes()==(update/n).read_bytes() for n in NAMES)
  check_native_interface(engine,client)
  assert not prepare_native_renderer_update(engine,client,update)
  client.write_bytes(b'v3 connected VFStatus arms: renderer=1 VFTraversal render: world palms=2')
  try:check_native_interface(engine,client)
  except RuntimeError:pass
  else:raise AssertionError('new grip client accepted the old traversal renderer')
  meta['traversal_renderer_version']=2
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  before=(engine/'vector-engine-build.json').read_bytes()
  try:prepare_native_renderer_update(engine,client,update)
  except RuntimeError as error:assert 'traversal grip validation' in str(error)
  else:raise AssertionError('untested traversal grip renderer accepted')
  assert (engine/'vector-engine-build.json').read_bytes()==before
  meta['traversal_grip_verified']=True
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  assert prepare_native_renderer_update(engine,client,update)
  check_native_interface(engine,client)
  assert not prepare_native_renderer_update(engine,client,update)
  client.write_bytes(b'v4 connected VFStatus arms: renderer=1 VFTraversal render: world palms=2')
  meta['extension_version']=4
  meta['headgear_verified']=True
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  before=(engine/'vector-engine-build.json').read_bytes()
  try:prepare_native_renderer_update(engine,client,update)
  except RuntimeError as error:assert 'articulated headgear' in str(error)
  else:raise AssertionError('renderer without headgear capability accepted')
  assert (engine/'vector-engine-build.json').read_bytes()==before
  meta['headgear_renderer_version']=1
  meta.pop('headgear_verified')
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  try:prepare_native_renderer_update(engine,client,update)
  except RuntimeError as error:assert 'headgear animation validation' in str(error)
  else:raise AssertionError('untested headgear renderer accepted')
  assert (engine/'vector-engine-build.json').read_bytes()==before
  meta['headgear_verified']=True
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  assert prepare_native_renderer_update(engine,client,update)
  check_native_interface(engine,client)
  assert not prepare_native_renderer_update(engine,client,update)
  assert prepare_native_renderer_update(engine,client,update,force=True)
  check_native_interface(engine,client)
  client.write_bytes(client.read_bytes()+b' VFBody render: world body=1 VFBody motion: world slide=1')
  meta['body_renderer_version']=1;meta['body_verified']=True
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  try:check_native_interface(update,client)
  except RuntimeError:pass
  else:raise AssertionError('world-slide client accepted old body renderer')
  try:prepare_native_renderer_update(engine,client,update)
  except RuntimeError as error:assert 'own-body validation' in str(error)
  else:raise AssertionError('old body renderer installed for world-slide client')
  meta['body_renderer_version']=2;meta['body_verified']=False
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  try:prepare_native_renderer_update(engine,client,update)
  except RuntimeError as error:assert 'own-body validation' in str(error)
  else:raise AssertionError('untested world-slide renderer installed')
  meta['body_verified']=True
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  assert prepare_native_renderer_update(engine,client,update)
  check_native_interface(engine,client)
  assert not prepare_native_renderer_update(engine,client,update)
  client.write_bytes(client.read_bytes()+b' VFPlayerPose collision: shared=1')
  before=(engine/'vector-engine-build.json').read_bytes()
  try:check_native_interface(engine,client)
  except RuntimeError as error:assert 'shared player-pose' in str(error)
  else:raise AssertionError('shared-pose client accepted legacy collision engine')
  meta['player_pose_version']=1
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  try:prepare_native_renderer_update(engine,client,update)
  except RuntimeError as error:assert 'collision/render validation' in str(error)
  else:raise AssertionError('untested shared collision engine installed')
  assert (engine/'vector-engine-build.json').read_bytes()==before
  meta['player_pose_verified']=True
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  assert prepare_native_renderer_update(engine,client,update)
  check_native_interface(engine,client)
  assert not prepare_native_renderer_update(engine,client,update)
  client.write_bytes(client.read_bytes()+b' VFMelee pose: shared=1')
  before=(engine/'vector-engine-build.json').read_bytes()
  try:check_native_interface(engine,client)
  except RuntimeError as error:assert 'shared melee-pose' in str(error)
  else:raise AssertionError('melee snapshot client accepted legacy body filters')
  meta['melee_pose_version']=1
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  try:prepare_native_renderer_update(engine,client,update)
  except RuntimeError as error:assert 'melee-pose engine' in str(error)
  else:raise AssertionError('untested melee-pose engine installed')
  assert (engine/'vector-engine-build.json').read_bytes()==before
  meta['melee_pose_verified']=True
  (update/'vector-engine-build.json').write_text(json.dumps(meta))
  assert prepare_native_renderer_update(engine,client,update)
  check_native_interface(engine,client)
  assert not prepare_native_renderer_update(engine,client,update)
 print('PASS renderer update: hash validation, shared collision/melee/body capability gates, locked DLL refusal, verified install, repeat no-op')
if __name__=='__main__':run()
