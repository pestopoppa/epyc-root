import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import bundle_preflight as bp


def pins(src, guard):
    result = {str(Path('launcher') / name): bp.digest(src / name) for name in bp.MODULES}
    result['kvu-vkq3-guard-review-20261102/guard.py'] = bp.digest(guard)
    return result


class BundleTests(unittest.TestCase):
    def test_self_contained_guard_import_and_manifest(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            root = Path(tmp) / 'prepared'
            src = Path(bp.__file__).parent
            guard = src.parent / 'kvu-vkq3-guard-review-20261102' / 'guard.py'
            manifest = bp.prepare_bundle(src, guard, root, pins(src, guard))
            record = json.loads((root / 'bundle-manifest.json').read_text())
            self.assertEqual(record['files'], manifest)
            for rel, expected in manifest.items():
                self.assertEqual(bp.digest(root / rel), expected)
                self.assertEqual((root / rel).stat().st_mode & 0o777, 0o400)
            result = subprocess.run([sys.executable, '-B', '-c', 'import rowflow_worker'],
                                    cwd=root/'launcher', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with self.assertRaises(FileExistsError):
                bp.prepare_bundle(src, guard, root, pins(src, guard))

    def test_rejects_unpinned_or_changed_source_without_manifest(self):
        src = Path(bp.__file__).parent
        guard = src.parent / 'kvu-vkq3-guard-review-20261102' / 'guard.py'
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
            root = Path(tmp) / 'missing'
            with self.assertRaisesRegex(ValueError, 'exact bundle'):
                bp.prepare_bundle(src, guard, root, {})
            self.assertFalse(root.exists())
            bad = pins(src, guard)
            bad['launcher/rowflow_worker.py'] = '0' * 64
            root = Path(tmp) / 'changed'
            with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                bp.prepare_bundle(src, guard, root, bad)
            self.assertFalse((root / 'bundle-manifest.json').exists())

    def test_rejects_outside_scratch(self):
        with self.assertRaises(ValueError):
            bp.prepare_bundle(Path(bp.__file__).parent, Path('/missing'), '/tmp/not-kvu', {})


if __name__ == '__main__':
    unittest.main()
