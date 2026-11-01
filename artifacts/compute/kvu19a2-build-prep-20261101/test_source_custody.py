#!/usr/bin/env python3
"""Offline custody checks; no source extraction, build, or inference."""
import errno
import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from prepare_sources import apply_validated_patch, open_private_parent, rename_noreplace, validated_patch


class CustodyTests(unittest.TestCase):
    def test_patch_input_is_the_validated_bytes_after_path_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'work'
            target.mkdir()
            (target / 'sample').write_text('old\n')
            patch = root / 'change.patch'
            good = b'--- a/sample\n+++ b/sample\n@@ -1 +1 @@\n-old\n+good\n'
            patch.write_bytes(good)
            captured = validated_patch(patch, hashlib.sha256(good).hexdigest())
            patch.write_bytes(good.replace(b'+good', b'+evil'))
            apply_validated_patch(target, captured)
            self.assertEqual((target / 'sample').read_text(), 'good\n')
            with self.assertRaises(ValueError):
                validated_patch(patch, hashlib.sha256(good).hexdigest())

    def test_collision_cannot_replace_empty_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'source').mkdir()
            (root / 'destination').mkdir()
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                with self.assertRaises(OSError) as exc:
                    rename_noreplace(fd, 'source', fd, 'destination')
                self.assertEqual(exc.exception.errno, errno.EEXIST)
                self.assertTrue((root / 'source').is_dir())
                self.assertTrue((root / 'destination').is_dir())
            finally:
                os.close(fd)

    def test_atomic_publish_to_new_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'source').mkdir()
            (root / 'source' / 'proof').write_text('original')
            fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                rename_noreplace(fd, 'source', fd, 'destination')
                self.assertEqual((root / 'destination' / 'proof').read_text(), 'original')
                self.assertFalse((root / 'source').exists())
            finally:
                os.close(fd)

    def test_symlink_parent_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'private').mkdir(mode=0o700)
            (root / 'link').symlink_to(root / 'private', target_is_directory=True)
            with self.assertRaises(OSError):
                open_private_parent(root, root / 'link' / 'out')

    def test_writable_shared_parent_and_dotdot_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'shared').mkdir()
            (root / 'shared').chmod(0o777)
            with self.assertRaises(PermissionError):
                open_private_parent(root, root / 'shared' / 'out')
            with self.assertRaises(ValueError):
                open_private_parent(root, root / 'shared' / '..' / 'out')


if __name__ == '__main__':
    unittest.main()
