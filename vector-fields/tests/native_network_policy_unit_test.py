"""Local native tests must not listen on the machine's LAN interfaces."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def native_commands():
    paths = set((ROOT / 'tests').glob('*.py'))
    paths.update(ROOT / name for name in ('play_headgear.py', 'play_weapon_inspect.py'))
    paths.update((ROOT / 'animation-workshop').glob('record-*.py'))
    paths.update((ROOT / 'bots').glob('*.py'))
    for folder in ('weapon-workshop', 'chassis-workshop'):
        paths.update((ROOT / folder).glob('*/test_native*.py'))
    for path in sorted(paths):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.List) or not node.elts:
                continue
            executables = [part.value for part in ast.walk(node.elts[0])
                           if isinstance(part, ast.Constant) and isinstance(part.value, str)]
            if not {'xash.exe', 'xash3d.exe'}.intersection(executables):
                continue
            yield path, node.lineno, node


class NativeNetworkPolicyUnitTest(unittest.TestCase):
    def test_native_launches_bind_ipv4_loopback_and_disable_ipv6(self):
        commands = list(native_commands())
        self.assertTrue(commands, 'No native launch commands checked')
        for path, line, node in commands:
            with self.subTest(path=str(path.relative_to(ROOT)), line=line):
                # These options must be in the literal prefix, before *common
                # or other expanded arguments. Xash parses -ip during NET_Init;
                # the later +ip console command alone does not cover startup.
                prefix = []
                for element in node.elts[1:]:
                    if not isinstance(element, ast.Constant):
                        break
                    prefix.append(element.value)
                self.assertIn('-ip', prefix)
                self.assertEqual(prefix[prefix.index('-ip') + 1], '127.0.0.1')
                self.assertIn('-noip6', prefix)
                literals = [part.value for part in node.elts
                            if isinstance(part, ast.Constant)]
                # Dedicated servers and their clients still need IPv4 UDP.
                self.assertNotIn('-noip', literals)
                for index, value in enumerate(literals):
                    if value in ('-ip', '+ip'):
                        self.assertEqual(literals[index + 1], '127.0.0.1')


if __name__ == '__main__':
    unittest.main()
