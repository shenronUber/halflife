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
 print('PASS renderer update: hash validation, arm capability gate, no replacement with locked DLL, verified classic install, repeat no-op')
if __name__=='__main__':run()
