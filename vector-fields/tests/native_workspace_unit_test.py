import tempfile,unittest,subprocess,sys,textwrap
from pathlib import Path
from unittest.mock import patch
import native_workspace as workspace

class NativeWorkspaceTest(unittest.TestCase):
 def test_snapshots_survive_source_updates_and_config_is_private(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'source.mdl';source.write_bytes(b'old geometry')
   with patch.object(workspace,'CACHE',root/'cache'),patch.object(workspace,'_index',{}),patch.object(workspace,'_blob_ids',{}),patch.object(workspace,'_loaded',False):
    workspace.shared_copy(source,root/'one/model.mdl')
    source.write_bytes(b'new and different geometry')
    workspace.shared_copy(source,root/'two/model.mdl')
    self.assertEqual((root/'one/model.mdl').read_bytes(),b'old geometry')
    self.assertEqual((root/'two/model.mdl').read_bytes(),source.read_bytes())
    with patch.object(workspace,'SESSIONS',root):
     workspace.private_copy(source,root/'one/model.mdl')
     (root/'one/model.mdl').write_bytes(b'edited test mesh')
     self.assertEqual((root/'two/model.mdl').read_bytes(),source.read_bytes())
    cfg=root/'source.cfg';cfg.write_text('original')
    workspace.shared_copy(cfg,root/'one/private.cfg');(root/'one/private.cfg').write_text('changed')
    self.assertEqual(cfg.read_text(),'original')
    clip=root/'voice.wav';clip.write_bytes(b'original voice')
    workspace.shared_copy(clip,root/'one/voice.wav')
    workspace.shared_copy(clip,root/'two/voice.wav')
    (root/'one/voice.wav').write_bytes(b'deployed revised voice')
    self.assertEqual((root/'two/voice.wav').read_bytes(),b'original voice')
    self.assertEqual(clip.read_bytes(),b'original voice')
    font=root/'.fontcache/glyph.bmp';font.parent.mkdir();font.write_bytes(b'original glyphs')
    workspace.shared_copy(font,root/'one/glyph.bmp');(root/'one/glyph.bmp').write_bytes(b'new glyphs')
    self.assertEqual(font.read_bytes(),b'original glyphs')
 def test_cleanup_preserves_proof_and_rejects_escape(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);sessions=root/'sessions';evidence=root/'proof';engine=sessions/'case'
   capture=engine/'vf_animation/scrshots/capture.png';capture.parent.mkdir(parents=True);capture.write_bytes(b'image')
   (engine/'native.log').write_text('PASS');(engine/'xash.dll').write_bytes(b'binary')
   with patch.object(workspace,'SESSIONS',sessions),patch.object(workspace,'EVIDENCE',evidence):
    with self.assertRaises(ValueError):workspace.remove_tree(root,sessions)
    with self.assertRaises(ValueError):workspace.remove_tree(sessions,sessions)
    workspace.retire_engine(engine,evidence/'case')
    self.assertFalse(engine.exists());self.assertEqual((evidence/'case/native.log').read_text(),'PASS')
    self.assertTrue((evidence/'case/vf_animation/scrshots/capture.png').is_file())
    self.assertFalse((evidence/'case/xash.dll').exists())
 def test_failed_archive_preserves_previous_evidence_and_live_engine(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);sessions=root/'sessions';evidence=root/'proof';engine=sessions/'case'
   engine.mkdir(parents=True);(engine/'native.log').write_text('new')
   previous=evidence/'case';previous.mkdir(parents=True);(previous/'native.log').write_text('old')
   with patch.object(workspace,'SESSIONS',sessions),patch.object(workspace,'EVIDENCE',evidence),patch.object(workspace.shutil,'copy2',side_effect=OSError('archive failed')):
    with self.assertRaises(OSError):workspace.publish_evidence(engine,'case')
   self.assertEqual((previous/'native.log').read_text(),'old');self.assertTrue(engine.exists())
 def test_parallel_same_case_publishes_one_complete_snapshot(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   code=textwrap.dedent('''
    import sys
    from pathlib import Path
    import native_workspace as w
    root=Path(sys.argv[1]);marker=sys.argv[2]
    w.SESSIONS=root/'sessions';w.EVIDENCE=root/'proof'
    engine=w.SESSIONS/marker;capture=engine/'vf_animation/scrshots/capture.png'
    capture.parent.mkdir(parents=True);capture.write_text(marker)
    (engine/'native.log').write_text(marker)
    w.publish_evidence(engine,'same-case')
   ''')
   children=[subprocess.Popen([sys.executable,'-c',code,str(root),marker],cwd=workspace.ROOT)for marker in ('one','two')]
   for child in children:self.assertEqual(child.wait(timeout=30),0)
   proof=root/'proof/same-case';marker=(proof/'native.log').read_text()
   self.assertEqual((proof/'vf_animation/scrshots/capture.png').read_text(),marker)
   self.assertIn(marker,('one','two'))
   self.assertEqual([p.name for p in (root/'proof').iterdir()if p.is_dir() and p.name!='.locks'],['same-case'])

if __name__=='__main__':unittest.main()
