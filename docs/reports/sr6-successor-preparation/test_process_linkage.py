import os
import tempfile
import unittest
from pathlib import Path

from process_linkage import _LIBS, inspect_maps


class ProcessLinkageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'bin').mkdir()
        self.lines = []
        for name in sorted(_LIBS):
            p = self.root / name
            p.write_bytes(b'x')
            st = p.stat()
            self.lines.append(f'1000-2000 r-xp 00000000 {os.major(st.st_dev):02x}:{os.minor(st.st_dev):02x} {st.st_ino} {p}')

    def test_exact_mappings_and_multiple_segments(self):
        self.assertEqual(inspect_maps('\n'.join(self.lines + self.lines[:1]), self.root), sorted(_LIBS))

    def test_server_mtmd_mapping_must_be_pinned_and_local(self):
        name = 'bin/libmtmd.so.0.0.10303'
        self.assertIn(name, _LIBS)
        mtmd = next(line for line in self.lines if line.endswith(name))
        with self.assertRaises(ValueError):
            inspect_maps('\n'.join(line for line in self.lines if line != mtmd), self.root)
        with self.assertRaisesRegex(ValueError, '/foreign/bin/libmtmd'):
            inspect_maps('\n'.join(self.lines + [mtmd.replace(str(self.root), '/foreign')]), self.root)

    def test_missing_replaced_deleted_or_foreign_refused(self):
        with self.assertRaises(ValueError): inspect_maps('\n'.join(self.lines[1:]), self.root)
        with self.assertRaises(ValueError): inspect_maps('\n'.join(self.lines + [self.lines[0] + ' (deleted)']), self.root)
        with self.assertRaises(ValueError): inspect_maps('\n'.join(self.lines + [self.lines[0].replace(str(self.root), '/foreign')]), self.root)
        p = self.root / sorted(_LIBS)[0]
        replacement = self.root / 'replacement'
        replacement.write_bytes(b'replacement')
        os.replace(replacement, p)
        with self.assertRaises(ValueError): inspect_maps('\n'.join(self.lines), self.root)


if __name__ == '__main__':
    unittest.main()
