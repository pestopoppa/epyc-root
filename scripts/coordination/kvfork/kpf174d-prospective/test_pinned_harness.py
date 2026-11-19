import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pinned_harness as harness


class Tests(unittest.TestCase):
    def test_restored_chain_matches_recorded_source(self):
        self.assertEqual(harness.verify_sources()['source_commit'], harness.SOURCE_COMMIT)
        b, k = harness.load_harness()
        self.assertIs(b.k13, k)
        self.assertTrue(callable(b.Runner.start))

    def test_each_dependency_refused_before_import(self):
        for name in harness.PINS:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                # Synthetic bytes only; never duplicate a source checkout.
                for relative in harness.PINS:
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'fixture')
                pins = dict.fromkeys(harness.PINS, hashlib.sha256(b'fixture').hexdigest())
                (root / name).write_bytes(b'changed')
                with patch.object(harness, 'PINS', pins), patch.object(harness.importlib.util, 'spec_from_file_location') as load:
                    with self.assertRaisesRegex(ValueError, 'pin mismatch'):
                        harness.load_harness(root)
                    load.assert_not_called()

    def test_missing_source_refused_before_import(self):
        with tempfile.TemporaryDirectory() as root, patch.object(harness.importlib.util, 'spec_from_file_location') as load:
            with self.assertRaises(FileNotFoundError):
                harness.load_harness(root)
            load.assert_not_called()

    def test_external_symlink_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scripts').symlink_to('/tmp', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'escapes root'):
                harness.verify_sources(root)
