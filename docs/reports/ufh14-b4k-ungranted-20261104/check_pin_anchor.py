import hashlib
import json
import shlex
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).parent
ORIGINAL = BASE.parent / 'b4k-guard-v2-20261104'


def check_only(launcher, root):
    line = next(line for line in launcher.read_text().splitlines() if line.startswith('"$PY" -c '))
    code = shlex.split(line)[2]
    with patch.object(sys, 'argv', ['offline-check', str(root)]):
        exec(compile(code, '<isolated-pin-check>', 'exec'), {})


class PinAnchorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        pins = json.loads((BASE / 'packet-pins.json').read_text())
        for name in pins:
            source = BASE / name if (BASE / name).exists() else ORIGINAL / name
            shutil.copyfile(source, self.root / name)
        shutil.copyfile(BASE / 'packet-pins.json', self.root / 'packet-pins.json')

    def test_literal_manifest_passes(self):
        check_only(BASE / 'launch.sh', self.root)

    def test_input_and_pin_co_mutation_rejected(self):
        (self.root / 'job.py').write_text('modified input')
        pins = json.loads((self.root / 'packet-pins.json').read_text())
        pins['job.py'] = hashlib.sha256((self.root / 'job.py').read_bytes()).hexdigest()
        (self.root / 'packet-pins.json').write_text(json.dumps(pins))
        # Original's runtime self-consistency is satisfied by jointly replaced pins.
        check_only(ORIGINAL / 'launch.sh', self.root)
        with self.assertRaisesRegex(AssertionError, 'pin manifest mismatch'):
            check_only(BASE / 'launch.sh', self.root)

    def test_manifest_omission_rejected(self):
        (self.root / 'packet-pins.json').write_text('{}')
        check_only(ORIGINAL / 'launch.sh', self.root)
        with self.assertRaisesRegex(AssertionError, 'pin manifest mismatch'):
            check_only(BASE / 'launch.sh', self.root)

    def test_input_only_mutation_rejected(self):
        (self.root / 'job.py').write_text('modified input')
        with self.assertRaisesRegex(AssertionError, 'content mismatch'):
            check_only(BASE / 'launch.sh', self.root)

if __name__ == '__main__':
    unittest.main()
