"""Model-free check that the candidate's local source manifest is complete and intact."""
import hashlib
import re
import tempfile
from pathlib import Path
import unittest

BASE = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-qualification/candidate')
MANIFEST = BASE / 'SOURCES.sha256'


def check_manifest(manifest, base):
    entries = set()
    unchecked = []
    for line in Path(manifest).read_text(encoding='ascii').splitlines():
        if not line:
            continue
        digest, separator, name = line.partition('  ')
        if separator != '  ' or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError(f'malformed manifest line: {line!r}')
        path = Path(name)
        if path.is_absolute():
            unchecked.append(name)
            continue
        if '..' in path.parts:
            raise ValueError(f'manifest path escapes candidate: {name}')
        if name in entries:
            raise ValueError(f'duplicate manifest path: {name}')
        entries.add(name)
        target = Path(base)
        for component in path.parts:
            target = target / component
            if target.is_symlink():
                raise ValueError(f'manifest path contains symlink: {name}')
        if not target.is_file():
            raise ValueError(f'manifest source missing: {name}')
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError(f'manifest source changed: {name}')
    if not entries:
        raise ValueError('manifest contains no local custody entries')
    return {'checked': sorted(entries), 'unchecked_absolute': unchecked}


class SourceCustodyTests(unittest.TestCase):
    def test_local_manifest_entries_are_unique_present_and_hash_exact(self):
        self.assertEqual(hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                         '04c0d3922939496fb100b0a7b0a0efe228ee7f3611ad025cc6d47d3c8bb684f7')
        result = check_manifest(MANIFEST, BASE)
        self.assertTrue(result['checked'])
        self.assertEqual(result['unchecked_absolute'], [])

    def test_absolute_entries_are_explicitly_reported_unchecked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'local.txt').write_bytes(b'local')
            external = '/outside/source.txt'
            manifest = root / 'manifest.sha256'
            manifest.write_text(f'{hashlib.sha256(b"local").hexdigest()}  local.txt\n'
                                f'{"0" * 64}  {external}\n', encoding='ascii')
            result = check_manifest(manifest, root)
            self.assertEqual(result['unchecked_absolute'], [external])

    def test_traversal_and_symlink_paths_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root / 'outside.txt'
            outside.write_bytes(b'outside')
            manifest = root / 'manifest.sha256'
            digest = hashlib.sha256(b'outside').hexdigest()
            manifest.write_text(f'{digest}  ../outside.txt\n', encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'escapes candidate'):
                check_manifest(manifest, root)
            link = root / 'linked.txt'
            link.symlink_to(outside)
            manifest.write_text(f'{digest}  linked.txt\n', encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'contains symlink'):
                check_manifest(manifest, root)

    def test_duplicate_entries_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.txt'
            source.write_bytes(b'x')
            digest = hashlib.sha256(b'x').hexdigest()
            manifest = root / 'manifest.sha256'
            manifest.write_text(f'{digest}  source.txt\n{digest}  source.txt\n', encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                check_manifest(manifest, root)


if __name__ == '__main__':
    unittest.main()
