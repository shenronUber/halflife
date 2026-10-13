import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import build_weapon_melee as sdk
import build_release as release
import build_wall_jump_native as cache

class BuildInputsTests(unittest.TestCase):
 def test_removed_header_does_not_survive_in_compilation_cache(self):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp);project=root/'project';out=root/'build';source=out/'source'
   for p,data in [(project/'dlls/current.h',b'new'),(source/'dlls/current.h',b'old'),(source/'dlls/deleted.h',b'obsolete')]:
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   with patch.object(cache,'PROJECT',project),patch.object(cache,'OUT',out):cache.sync_game_sources(source)
   self.assertEqual(b'new',(source/'dlls/current.h').read_bytes())
   self.assertFalse((source/'dlls/deleted.h').exists())
 def test_network_resources_libraries_and_deleted_headers_change_identity(self):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp)
   files=['network/delta.lst','dlls/live.h','utils/vgui/panel.cpp','lib/vgui.lib','projects/vs2019/flags.props','cl_dll/client.rc']
   for name in files:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'original')
   before=sdk.sources(root);self.assertEqual(len(before),len(files))
   for name in files:
    p=root/name;p.write_bytes(b'changed');self.assertNotEqual(before,sdk.sources(root));p.write_bytes(b'original')
   (root/'dlls/live.h').unlink();self.assertNotEqual(before,sdk.sources(root))
 def test_engine_patches_belong_to_release_inputs(self):
  with tempfile.TemporaryDirectory()as tmp:
   project=Path(tmp);root=project/'vector-fields'
   for name in ['version.json','engine/test.patch','melee-workshop/Frappe-au-canon-R1-poing.blend','animation-workshop/traversal/blender/Corps-R1-revue-complete.blend','animation-workshop/traversal/blender/Mains-R1-revue-complete.blend']:
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'original')
   for name in ['asset-probe/generate_assets.py','devtools/bootstrap-worktree.py']:
    p=project/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'original')
   with patch.object(release,'ROOT',root),patch.object(release,'PROJECT',project),patch.object(release,'sources',side_effect=lambda:{}):
    before=release.inputs();(root/'engine/test.patch').write_bytes(b'changed')
    self.assertNotEqual(before,release.inputs())

if __name__=='__main__':unittest.main()
