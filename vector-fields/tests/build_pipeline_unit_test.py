"""Regression tests for generation invalidation and selective rebuild behavior."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import build_cache as cache
import build_reference_weapon as weapon
import third_person


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.output=self.root/'output'
        self.source.write_bytes(b'input');self.output.write_bytes(b'model')
        self.digest=cache.fingerprint([self.source]);self.state=cache.record(self.digest,[self.output])

    def test_unchanged_files_are_current(self):
        self.assertTrue(cache.current(self.state,self.digest))

    def test_same_size_same_timestamp_input_change_invalidates(self):
        import os
        timestamp=self.source.stat().st_mtime_ns
        self.source.write_bytes(b'other');os.utime(self.source,ns=(timestamp,timestamp))
        self.assertFalse(cache.current(self.state,cache.fingerprint([self.source])))

    def test_corrupted_output_invalidates(self):
        self.output.write_bytes(b'wrong')
        self.assertFalse(cache.current(self.state,self.digest))

    def test_missing_output_invalidates(self):
        self.output.unlink();self.assertFalse(cache.current(self.state,self.digest))

    def test_legacy_existence_only_cache_is_rebuilt(self):
        self.assertFalse(cache.current(dict(inputs_sha256=self.digest),self.digest))

    def test_empty_outputs_cannot_claim_success(self):
        with self.assertRaises(ValueError):cache.record(self.digest,[])
        self.assertFalse(cache.current(dict(inputs_sha256=self.digest,outputs={}),self.digest))

    def test_missing_input_reports_its_path(self):
        with self.assertRaisesRegex(FileNotFoundError,'missing-donor'):cache.fingerprint([self.root/'missing-donor'])

    def test_hash_is_order_independent_and_deduplicated(self):
        self.assertEqual(cache.fingerprint([self.output,self.source]),cache.fingerprint([self.source,self.output,self.source]))

    def test_file_boundaries_cannot_collide(self):
        a=self.root/'a';b=self.root/'b';a.write_bytes(b'a');b.write_bytes(b'bc');old=cache.fingerprint([a,b])
        a.write_bytes(b'ab');b.write_bytes(b'c');self.assertNotEqual(old,cache.fingerprint([a,b]))

    def test_renamed_input_invalidates(self):
        other=self.root/'new-source';self.source.rename(other)
        self.assertNotEqual(self.digest,cache.fingerprint([other]))

    def test_truncated_state_recovers(self):
        state=self.root/'state.json';state.write_text('{')
        self.assertEqual({},cache.read(state))
        cache.write(state,self.state);self.assertTrue(cache.current(cache.read(state),self.digest))


class RebuildTests(unittest.TestCase):
    """Exercise the production build orchestrator; replace only expensive compilers."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.inputs={key:[self.root/(key+'.source')] for key in ('modules','rigs')}
        self.outputs={key:[self.root/(key+'.mdl')] for key in self.inputs}
        state={}
        for key in self.inputs:
            self.inputs[key][0].write_bytes(b'original input');self.outputs[key][0].write_bytes(b'original model')
            state[key]=cache.record(cache.fingerprint(self.inputs[key]),self.outputs[key])
        cache.write(self.root/'build-state.json',state);cache.write(self.root/'manifest.json',dict(pieces=[dict(id='example')]))
        for name,value in [('OUT',self.root),('stage_inputs',lambda:self.inputs),('stage_outputs',lambda key,manifest:self.outputs[key]),('module_catalog_current',lambda manifest:True),('inputs_hash',lambda:cache.fingerprint(sum(self.inputs.values(),[])))]:
            p=patch.object(weapon,name,value);p.start();self.addCleanup(p.stop)
        for name in ('prepare_tiles','Studio'):
            p=patch.object(weapon,name);p.start();self.addCleanup(p.stop)
        p=patch('model_contract.generate');p.start();self.addCleanup(p.stop)
        self.rigs=patch.object(weapon,'build_rigs',side_effect=lambda:self.outputs['rigs'][0].write_bytes(b'rebuilt rig')).start()
        self.modules=patch.object(weapon,'build_modules',side_effect=lambda rig:self.outputs['modules'][0].write_bytes(b'rebuilt module')).start()
        self.addCleanup(patch.stopall)

    def test_unchanged_build_invokes_no_compiler(self):
        weapon.build(ensure=True);self.rigs.assert_not_called();self.modules.assert_not_called()

    def test_animation_edit_rebuilds_rigs_only(self):
        self.inputs['rigs'][0].write_bytes(b'new gesture');weapon.build(ensure=True)
        self.rigs.assert_called_once();self.modules.assert_not_called()
        self.assertEqual(b'original model',self.outputs['modules'][0].read_bytes())
        weapon.build(ensure=True);self.assertEqual(1,self.rigs.call_count)

    def test_texture_edit_rebuilds_modules_only(self):
        self.inputs['modules'][0].write_bytes(b'new finish');weapon.build(ensure=True)
        self.modules.assert_called_once();self.rigs.assert_not_called()
        self.assertEqual(b'original model',self.outputs['rigs'][0].read_bytes())

    def test_corrupted_rig_rebuilds_without_touching_modules(self):
        self.outputs['rigs'][0].write_bytes(b'corrupt');weapon.build(ensure=True)
        self.rigs.assert_called_once();self.modules.assert_not_called()

    def test_failed_compile_does_not_commit_cache(self):
        previous=(self.root/'build-state.json').read_bytes();self.inputs['rigs'][0].write_bytes(b'new gesture')
        self.rigs.side_effect=RuntimeError('compile failed')
        with self.assertRaisesRegex(RuntimeError,'compile failed'):weapon.build(ensure=True)
        self.assertEqual(previous,(self.root/'build-state.json').read_bytes())


class DependencyTests(unittest.TestCase):
    def test_gestures_and_foregrip_recipe_do_not_invalidate_weapon_meshes(self):
        paths=weapon.stage_inputs()
        for path in (ROOT/'first_person_grips.py',ROOT/'build_foregrip.py',ROOT/'assets/animations/r01-first-person-foregrip.json',weapon.SOURCE/'reload.smd'):
            self.assertIn(path,paths['rigs']);self.assertNotIn(path,paths['modules'])
        self.assertIn(weapon.SOURCE/'mp40_hands.smd',paths['modules'])
        self.assertIn(weapon.SOURCE/'mp40_rig.qc',paths['modules'])

    def test_finish_catalog_has_one_serialization_for_both_generators(self):
        from catalog_assets import weapon_style_catalog
        styles=json.loads((weapon.OUT/'manifest.json').read_text())['styles']
        content=json.loads((ROOT/'data/gameplay-content.json').read_text())
        self.assertEqual((ROOT/'data/r01_styles.txt').read_text(encoding='ascii'),weapon_style_catalog(styles,content))

    def test_third_person_includes_retarget_helpers_and_donor(self):
        paths=third_person.input_paths()
        for name in ('animation_assets.py','inspect_animations.py','studio_assets.py','model_contract.py'):
            self.assertIn(ROOT/name,paths)
        from build_personas import donor,ASSETS
        source=Path(donor(json.loads((ASSETS/'personas.json').read_text()))['path'])
        self.assertIn(source,paths)
        self.assertIn(third_person.TP/'persona_anchors.smd',paths)
        self.assertTrue(any(p.name=='studiomdl.exe' for p in paths))


if __name__=='__main__':unittest.main()
