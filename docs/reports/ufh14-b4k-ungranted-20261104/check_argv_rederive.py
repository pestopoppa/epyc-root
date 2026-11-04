import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).parent
ORIGINAL = BASE.parent / 'b4k-guard-v2-20261104'


def isolated(path, launch):
    tree = ast.parse(path.read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'launch_record')
    scope = {'json': json, 'hashlib': hashlib, 'LAUNCH': launch,
             'ARGV_SHA': 'f09f466f756884301f7286f75076582ea3d2ee1a846550d3c7f392a620e66e93'}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<isolated-launch-record>', 'exec'), scope)
    return scope['launch_record']


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.launch = Path(self.tmp.name) / 'launch.json'
        self.record = json.loads((ORIGINAL / 'prod-8083-launch.json').read_text())

    def save(self):
        self.launch.write_text(json.dumps(self.record))

    def test_original_reproduces_false_pin_acceptance(self):
        self.record['argv'][self.record['argv'].index('-m') + 1] = '/foreign.gguf'
        self.save()
        self.assertEqual(isolated(ORIGINAL / 'job.py', self.launch)()['argv'], self.record['argv'])

    def test_pinned_record_passes(self):
        self.save()
        self.assertEqual(isolated(BASE / 'job.py', self.launch)(), self.record)

    def test_changed_argv_with_original_claimed_pin_is_rejected(self):
        for original, replacement in [('-m', '/foreign.gguf'), ('--port', '1'), ('--device', 'CPU')]:
            with self.subTest(option=original):
                record = json.loads((ORIGINAL / 'prod-8083-launch.json').read_text())
                record['argv'][record['argv'].index(original) + 1] = replacement
                self.launch.write_text(json.dumps(record))
                with self.assertRaisesRegex(SystemExit, 'actual argv_sha256'):
                    isolated(BASE / 'job.py', self.launch)()

    def test_invalid_argv_types_and_nul(self):
        for argv in [None, [], 'argv', [1], ['a\0b']]:
            with self.subTest(argv=argv):
                self.record['argv'] = argv
                self.save()
                with self.assertRaisesRegex(SystemExit, 'nonempty strings'):
                    isolated(BASE / 'job.py', self.launch)()

    def test_wrong_claimed_pin_still_rejected(self):
        self.record['argv_sha256'] = '0' * 64
        self.save()
        with self.assertRaises(SystemExit):
            isolated(BASE / 'job.py', self.launch)()

if __name__ == '__main__':
    unittest.main()
