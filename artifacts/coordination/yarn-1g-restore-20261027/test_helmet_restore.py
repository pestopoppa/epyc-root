import io
import hashlib
import json
import os
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch
import helmet_restore as h

class RestoreTests(unittest.TestCase):
    def archive(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as tar:
            for name in sorted(h.FILES):
                raw = ('fixture ' + name).encode()
                info = tarfile.TarInfo('data/kilt/' + name); info.size = len(raw)
                tar.addfile(info, io.BytesIO(raw))
        return data.getvalue()

    def test_small_archive_extracts_selected_and_verifies_digest(self):
        base = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch') / f'helmet-fixture-{os.getpid()}'
        if base.exists():
            self.fail('fixture directory already exists')
        blob = self.archive()
        class Response(io.BytesIO):
            status = 200
        with patch.object(h, 'ROOT', base), patch.object(h, 'SIZE', len(blob)), patch.object(h, 'SHA', hashlib.sha256(blob).hexdigest()), patch.object(h.urllib.request, 'urlopen', return_value=Response(blob)), patch.object(h, 'free', return_value=300*h.GIB), patch.object(sys, 'argv', ['restore', '--budget-gib', '1', '--deadline-epoch', '4000000000']):
            h.main()
        receipt = json.loads((base/'RESTORE_RECEIPT.json').read_text())
        self.assertEqual(set(receipt['files']), h.FILES)
        self.assertEqual((base/'data.tar.gz.part').read_bytes(), blob)

    def test_budget_refusal_precedes_network(self):
        with patch.object(h, 'free', return_value=150*h.GIB), patch.object(h.urllib.request, 'urlopen') as urlopen, patch.object(sys, 'argv', ['restore', '--budget-gib', '20', '--deadline-epoch', '4000000000']):
            with self.assertRaises(SystemExit): h.main()
            urlopen.assert_not_called()

    def test_nan_budget_is_refused(self):
        with patch.object(h, 'free', return_value=300*h.GIB), patch.object(h.urllib.request, 'urlopen') as urlopen, patch.object(sys, 'argv', ['restore', '--budget-gib', 'nan', '--deadline-epoch', '4000000000']):
            with self.assertRaises(SystemExit): h.main()
            urlopen.assert_not_called()

    def test_bad_digest_refuses_before_extract(self):
        base = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch') / f'helmet-bad-{os.getpid()}'
        data = b'not-the-archive'
        class Response(io.BytesIO):
            status = 200
        with patch.object(h, 'ROOT', base), patch.object(h, 'SIZE', len(data)), patch.object(h, 'SHA', '0'*64), patch.object(h.urllib.request, 'urlopen', return_value=Response(data)), patch.object(h, 'free', return_value=300*h.GIB), patch.object(sys, 'argv', ['restore', '--budget-gib', '1', '--deadline-epoch', '4000000000']):
            with self.assertRaises(SystemExit): h.main()
        self.assertFalse((base/'data').exists())

    def test_resume_partial_and_refuse_wrong_existing_final(self):
        base = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch') / f'helmet-resume-{os.getpid()}'
        target = base/'data/kilt'; target.mkdir(parents=True)
        blob = self.archive(); (base/'data.tar.gz.part').write_bytes(blob)
        first, second = sorted(h.FILES)[:2]
        (target/(first+'.part')).write_bytes(b'interrupted')
        (target/second).write_bytes(b'wrong')
        with patch.object(h, 'ROOT', base), patch.object(h, 'SIZE', len(blob)), patch.object(h, 'SHA', hashlib.sha256(blob).hexdigest()), patch.object(h.urllib.request, 'urlopen') as urlopen, patch.object(h, 'free', return_value=300*h.GIB), patch.object(sys, 'argv', ['restore', '--budget-gib', '1', '--deadline-epoch', '4000000000']):
            with self.assertRaises(SystemExit): h.main()
            self.assertEqual((target/(first+'.part')).read_bytes(), b'interrupted')
            (target/second).unlink()
            h.main()
            urlopen.assert_not_called()
        self.assertEqual((target/first).read_bytes(), ('fixture '+first).encode())
        self.assertFalse((target/(first+'.part')).exists())
        receipt = json.loads((base/'RESTORE_RECEIPT.json').read_text())
        self.assertEqual(receipt['files'][first]['sha256'], hashlib.sha256(('fixture '+first).encode()).hexdigest())

if __name__ == '__main__': unittest.main()
