"""Exercise the public launcher's choices and installed-binary checks."""
import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_release as release
from game_profiles import MAPS, arrival_config


class LaunchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.engine = Path(temp.name)
        self.receipt = self.engine / 'vf_visual/vf/release-bundle.json'
        self.receipt.parent.mkdir(parents=True)
        self.binary = self.engine / 'xash3d.exe'
        self.binary.write_bytes(b'validated-engine')
        self.state = dict(passed=True, files={'xash3d.exe': release.sha(self.binary)})
        self.write_receipt()
        for name, value in [('LIVE', self.engine), ('RECEIPT', self.receipt), ('LOCK', self.engine / 'release.lock')]:
            guard = patch.object(release, name, value)
            guard.start()
            self.addCleanup(guard.stop)
        process = patch.object(release.subprocess, 'Popen')
        self.process = process.start()
        self.addCleanup(process.stop)
        self.process.return_value.wait.return_value = 23

    def write_receipt(self):
        self.receipt.write_text(json.dumps(self.state), encoding='utf-8')

    def test_registered_maps_have_one_map_request_and_their_arrival_config(self):
        for name in MAPS:
            with self.subTest(map=name):
                self.assertEqual(23, release.launch(name))
                command = self.process.call_args.args[0]
                self.assertEqual(1, command.count('+map'))
                self.assertEqual([name, '+exec', arrival_config(name) + '.cfg'], command[command.index('+map') + 1:])
                self.assertEqual(self.engine, self.process.call_args.kwargs['cwd'])

    def test_modular_seed_precedes_map_including_random_and_upper_boundary(self):
        for name in ('vf_modular', 'vf_tiles'):
            for seed in (0, 42, 2147483647):
                with self.subTest(map=name, seed=seed):
                    release.launch(name, seed=seed)
                    command = self.process.call_args.args[0]
                    index = command.index('+vf_modular_seed')
                    self.assertLess(index, command.index('+map'))
                    self.assertEqual(str(seed), command[index + 1])

    def test_tiles_resets_forced_variant_before_map(self):
        release.launch('vf_tiles')
        command = self.process.call_args.args[0]
        index = command.index('+vf_tiles_variant')
        self.assertEqual('-1', command[index + 1])
        self.assertLess(index, command.index('+map'))
        release.launch('vf_modular')
        self.assertNotIn('+vf_tiles_variant', self.process.call_args.args[0])

    def test_invalid_modular_seeds_cannot_start_process(self):
        for seed in (-1, 2147483648, 1.5, True, False, '42', '+quit'):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, 'seed'):
                release.launch('vf_modular', seed=seed)
        self.process.assert_not_called()

    def test_unknown_map_cannot_start_process(self):
        with self.assertRaisesRegex(ValueError, 'Unknown map'):
            release.launch('missing_map')
        self.process.assert_not_called()

    def test_installed_imported_map_and_reference_arrival_are_preserved(self):
        bsp = self.engine / 'vf_visual/maps/imported_map.bsp'
        bsp.parent.mkdir(parents=True)
        bsp.write_bytes(b'map')
        release.launch('imported_map', reference=True)
        self.assertEqual(['+map', 'imported_map', '+exec', 'vf_reference_start.cfg'], self.process.call_args.args[0][-4:])

    def test_unvalidated_installation_cannot_start_process(self):
        self.state['passed'] = False
        self.write_receipt()
        with self.assertRaisesRegex(RuntimeError, 'validated release'):
            release.launch()
        self.process.assert_not_called()

    def test_modified_engine_cannot_start_process(self):
        self.binary.write_bytes(b'changed-engine')
        with self.assertRaisesRegex(RuntimeError, 'Installed release differs'):
            release.launch()
        self.process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
