"""Model-free whole-root arithmetic controls; fixtures are retained, not deleted."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[4] / 'docs/reports/kv-cache/kpf18-g3-output-reserve-20261104/output_reserve.py'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == 'a763c65fc953c1ec2957b0b0784e7ed94f52b63985a12a6c633422460dd5d4fe'
spec = importlib.util.spec_from_file_location('retained_output_reserve', SOURCE)
reserve = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reserve)
SCRATCH = Path('/mnt/raid0/llm/tmp/kvfork')
SCRATCH.mkdir(parents=True, exist_ok=True)


class AttemptOutputTests(unittest.TestCase):
    def test_entire_attempt_counts_logs_tmp_cache_raw_and_conformance(self):
        root = Path(tempfile.mkdtemp(prefix='kpf18-output-control-', dir=SCRATCH))
        files = []
        for name in ('driver.log', 'tmp/part', 'cache/entry', 'raw-gate/slot-save/slot', 'conformance/VERDICT.json'):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture')
            files.append(path)
        # Logical size must count even where the filesystem allocates no blocks.
        with files[-1].open('r+b') as stream:
            stream.truncate(1024 * 1024)
        expected = sum(max(p.stat().st_size, p.stat().st_blocks * 512) for p in files)
        self.assertEqual(reserve.owned_bytes(root), expected)
        self.assertTrue(reserve.check(reserve.FLOOR + reserve.CAP - expected, expected))
        with self.assertRaises(RuntimeError):
            reserve.check(reserve.FLOOR + reserve.CAP - expected - 1, expected)
        print('retained output fixture:', root)

    def test_nested_symlink_refused(self):
        root = Path(tempfile.mkdtemp(prefix='kpf18-output-symlink-control-', dir=SCRATCH))
        (root / 'cache').mkdir()
        (root / 'cache' / 'escape').symlink_to('/dev/null')
        with self.assertRaisesRegex(RuntimeError, 'output symlink'):
            reserve.owned_bytes(root)
        print('retained refusal fixture:', root)


if __name__ == '__main__':
    unittest.main()
