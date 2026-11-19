from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts/speech'
sys.path.insert(0, str(SCRIPTS))
import stt5_voxtral_restore as m


class RestoreTests(unittest.TestCase):
    def test_replace_exact_only(self):
        self.assertEqual(m.replace_one(['cc', 'lib.a'], 'lib.a', '/new'), ['cc', '/new'])
        for cmd in (['cc'], ['lib.a', 'lib.a']):
            with self.assertRaises(ValueError):
                m.replace_one(cmd, 'lib.a', '/new')

    def test_compile_preserves_flags_and_cwd(self):
        recipe = dict(file='/src/x.cpp', directory='/build', command='cc -O3 -o old.o -c /src/x.cpp')
        cmd, cwd = m.compile_overlay([recipe], 'x.cpp', '/overlay.cpp', '/out.o', '/src')
        self.assertEqual(cwd, '/build')
        self.assertEqual(cmd, ['cc', '-I/src/examples/cli', '-O3', '-o', '/out.o', '-c', '/overlay.cpp'])
        self.assertIn('old.o', recipe['command'])

    def test_ambiguous_or_missing_recipe_refused(self):
        recipe = dict(file='/src/x.cpp', directory='/b', command='cc -o x.o -c /src/x.cpp')
        for entries in ([], [recipe, recipe]):
            with self.assertRaises(ValueError):
                m.compile_overlay(entries, 'x.cpp', '/new', '/out', '/s')

    def test_invalid_compile_refused(self):
        with self.assertRaises(ValueError):
            m.compile_overlay([dict(file='/x.cpp', directory='/', command='cc /x.cpp')],
                              'x.cpp', '/new', '/out', '/s')

    def test_submodule_commit_drift_refused(self):
        cfg = {'submodules': {'/source/ggml': 'expected'}}
        with mock.patch.object(m, 'verify'), mock.patch.object(m.subprocess, 'check_output', side_effect=['other\n', b'']):
            with self.assertRaisesRegex(ValueError, 'submodule source drift'):
                m.verify_all(cfg)

    def test_dirty_submodule_refused(self):
        cfg = {'submodules': {'/source/ggml': 'expected'}}
        with mock.patch.object(m, 'verify'), mock.patch.object(m.subprocess, 'check_output', side_effect=['expected\n', b' M source.cpp']):
            with self.assertRaisesRegex(ValueError, 'submodule source drift'):
                m.verify_all(cfg)

    def test_parent_pin_failure_propagates(self):
        with mock.patch.object(m, 'verify', side_effect=ValueError('prepared input drift')):
            with self.assertRaisesRegex(ValueError, 'prepared input drift'):
                m.verify_all({'submodules': {}})

    def test_all_native_witnesses_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'object'
            for data in (b'', b'\x7fELF', b'\x7fELF' + b' '.join(m.WITNESSES[:-1]),
                         b'notELF' + b' '.join(m.WITNESSES)):
                p.write_bytes(data)
                with self.assertRaises(ValueError):
                    m.witness(p)
            p.write_bytes(b'\x7fELF' + b' '.join(m.WITNESSES))
            self.assertEqual(m.witness(p), m.sha(p))


if __name__ == '__main__':
    unittest.main()
