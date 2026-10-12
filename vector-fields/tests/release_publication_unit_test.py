"""Reject untested/stale/tampered bundles and recover a failed mod swap."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import build_release as release
class PublicationTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);base=Path(self.temp.name)
  self.candidate=base/'candidate';self.live=base/'live';self.sdk=base/'canonical';self.state={'source':'hash'}
  for path,data in [('engine/vf_visual/cl_dlls/client.dll',b'new-client'),('engine/vf_visual/dlls/hl.dll',b'new-server'),('engine/vf_visual/vf/version.json',b'{}'),('sdk/client/client.dll',b'new-client'),('sdk/server/hl.dll',b'new-server')]:
   p=self.candidate/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  files={str(p.relative_to(self.candidate/'engine')):release.sha(p)for p in(self.candidate/'engine').rglob('*')if p.is_file()}
  self.manifest=dict(id='test',passed=True,source_identity=release.identity(self.state),files=files)
  self.write()
  for p in [self.live/'vf_visual/cl_dlls/client.dll',self.live/'vf_visual/dlls/hl.dll',self.sdk/'client/client.dll',self.sdk/'server/hl.dll']:
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'old')
  p=self.live/'vf_visual/save/player.sav';p.parent.mkdir();p.write_bytes(b'player-save')
  self.patcher=patch.object(release,'inputs',return_value=self.state);self.patcher.start();self.addCleanup(self.patcher.stop)
 def write(self):(self.candidate/'bundle.json').write_text(json.dumps(self.manifest))
 def test_unvalidated_rejected_before_live_write(self):
  self.manifest['passed']=False;self.write()
  with self.assertRaisesRegex(RuntimeError,'validated'):release.publish(self.candidate,self.live,self.sdk)
  self.assertEqual(b'old',(self.sdk/'client/client.dll').read_bytes())
 def test_stale_sources_rejected(self):
  self.manifest['source_identity']='stale';self.write()
  with self.assertRaisesRegex(RuntimeError,'stale'):release.publish(self.candidate,self.live,self.sdk)
 def test_changed_tested_binary_rejected(self):
  (self.candidate/'engine/vf_visual/dlls/hl.dll').write_bytes(b'tampered')
  with self.assertRaisesRegex(RuntimeError,'changed after'):release.publish(self.candidate,self.live,self.sdk)
 def test_success_keeps_player_save(self):
  with patch.object(release,'verify_deployment'):release.publish(self.candidate,self.live,self.sdk)
  self.assertEqual(b'player-save',(self.live/'vf_visual/save/player.sav').read_bytes())
  self.assertEqual(b'new-client',(self.sdk/'client/client.dll').read_bytes())
 def test_failed_swap_restores_entire_old_mod_and_binaries(self):
  real=release.os.replace
  def replace(a,b):
   if Path(a).name.startswith('.vf_visual-next-'):raise OSError('simulated locked mod')
   return real(a,b)
  with patch.object(release.os,'replace',side_effect=replace):
   with self.assertRaisesRegex(OSError,'locked'):release.publish(self.candidate,self.live,self.sdk)
  for p in [self.sdk/'client/client.dll',self.sdk/'server/hl.dll',self.live/'vf_visual/dlls/hl.dll']:self.assertEqual(b'old',p.read_bytes())
  self.assertEqual(b'player-save',(self.live/'vf_visual/save/player.sav').read_bytes())
if __name__=='__main__':unittest.main()
