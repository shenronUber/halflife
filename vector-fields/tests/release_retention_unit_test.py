import json,tempfile,unittest
from pathlib import Path
import release_retention as retention
from native_workspace import compact_captures
class RetentionTests(unittest.TestCase):
 def test_current_rollback_and_authored_assets_survive(self):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp);releases=root/'releases';live=root/'live';archive=root/'archives'
   ids=['20261012-100000-aaaaaaaa','20261012-110000-bbbbbbbb','20261012-120000-cccccccc']
   for name in ids:
    p=releases/name;p.mkdir(parents=True);(p/'source-inputs.json').write_text('{}');(p/'bundle.json').write_text(json.dumps({'passed':True}));(p/'runtime.dll').write_bytes(b'large')
   receipt=live/'vf_visual/vf/release-bundle.json';receipt.parent.mkdir(parents=True);receipt.write_text(json.dumps(dict(passed=True,candidate=str(releases/ids[-1]))))
   saved=releases/ids[0]/'engine/vf_visual/save/player.sav';saved.parent.mkdir(parents=True);saved.write_bytes(b'player save')
   authored=releases/'authoring';authored.mkdir();(authored/'keep.blend').write_bytes(b'authored')
   result=retention.cleanup(releases,live,archive)
   self.assertEqual(len(result['removed']),1);self.assertTrue((releases/ids[-1]).exists());self.assertTrue((releases/ids[-2]).exists());self.assertTrue((authored/'keep.blend').exists())
   self.assertEqual((archive/ids[0]/'engine/vf_visual/save/player.sav').read_bytes(),b'player save')
   self.assertFalse((archive/ids[0]/'runtime.dll').exists())
   self.assertEqual(retention.cleanup(releases,live,archive)['removed'],[])
 def test_receipt_outside_release_root_is_rejected(self):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp);receipt=root/'live/vf_visual/vf/release-bundle.json';receipt.parent.mkdir(parents=True);receipt.write_text(json.dumps(dict(passed=True,candidate=str(root/'authored'))));(root/'releases').mkdir()
   with self.assertRaises(ValueError):retention.plan(root/'releases',root/'live')
 def test_retired_captures_are_bounded_and_logs_saves_are_preserved(self):
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp);case=root/'case';screens=case/'vf_animation/scrshots';screens.mkdir(parents=True)
   for i in range(100):(screens/f'{i:03}.png').write_bytes(b'image')
   (case/'native.log').write_text('report');saved=case/'vf_animation/save/player.sav';saved.parent.mkdir();saved.write_bytes(b'save')
   self.assertEqual(compact_captures(root),68);self.assertEqual(len(list(screens.glob('*.png'))),32)
   self.assertTrue((screens/'000.png').exists()and(screens/'099.png').exists());self.assertTrue(saved.exists()and(case/'native.log').exists())
if __name__=='__main__':unittest.main()
