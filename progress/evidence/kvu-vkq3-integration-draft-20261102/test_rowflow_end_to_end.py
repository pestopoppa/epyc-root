"""Model-free grant-to-native-result integration; no real keeper or model."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
import time
import unittest

import rowflow_worker as rw


class EndToEndTests(unittest.TestCase):
    def test_qualification_publishes_only_isolated_native_unit(self):
        with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as td:
            root = Path(td)
            dry = root / 'dry'; dry.mkdir()
            grants = dry / 'grants'; grants.mkdir()
            receipt = root / 'receipts'; receipt.mkdir(mode=0o700)
            now = time.time(); end = int(now // 60) * 60 + 600
            stamp = lambda n: dt.datetime.fromtimestamp(n, dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
            (grants / 'sample.grant').write_text(
                f'regions=0-3 start={stamp(now-60)} end={stamp(end)} holds= '
                'schema=epyc.rowflow.dryrun-grant.v1 id=sample kind=rowflow-dryrun\n')
            full = root / 'full'; full.write_bytes(b'full synthetic')
            short = root / 'short'; short.write_bytes(b'short synthetic')
            model = root / 'fake-model'; model.write_bytes(b'fake model')
            library = root / 'fake-library'; library.write_bytes(b'fake library')
            tokenizer = root / 'fake-tokenizer'
            received = root / 'tokenizer-stdin'
            tokenizer.write_text('#!/bin/sh\ncat > ' + shlex.quote(str(received)) +
                                 '\nprintf "[1, 2, 3]\\n"\n')
            tokenizer.chmod(0o700)
            paths = [str(p) for p in (full, short, model, library, tokenizer)] + [sys.executable, str(rw._WRAPPER)]
            identities = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}
            result = dry / 'native-result.json'
            plan = dict(id='sample', local_stop=str(root/'local-stop'), result_path=str(root/'full-result.jsonl'),
                        qualification_input=str(short), full_input=str(full), tokenizer=str(tokenizer), model=str(model),
                        model_files=[str(model)], runtime_files=[str(library)], library_path=str(root),
                        input_sha256={'full': identities[str(full)], 'qualification': identities[str(short)]},
                        inputs={p: rw._stat(p) for p in paths}, identity_sha256=identities,
                        input_limit=100, cleanup_margin_s=2, attempt_id='synthetic', receipt_root=str(receipt))
            env = {'FILLER_ID':'sample', 'FILLER_NEEDGPU':'0', 'FILLER_CPUS':'0-3',
                   'FILLER_END':str(end), 'FILLER_DEADLINE':str(end-90),
                   'FILLER_STOPFILE':str(root/'stop'), 'FILLER_GRANTS_DIR':str(grants),
                   'FILLER_DRYRUN':'1', 'FILLER_DRYRUN_DIR':str(dry), 'FILLER_DRYRUN_RESULT_PATH':str(result)}
            self.assertEqual(rw.run(plan, env), str(result))
            self.assertEqual(received.read_bytes(), short.read_bytes())
            self.assertNotEqual(received.read_bytes(), full.read_bytes())
            data = json.loads(result.read_text())
            self.assertEqual((data['mode'], data['status'], data['verdict'], data['validated_token_count']),
                             ('qualification', 'completed', 'excluded_qualification', 3))
            self.assertTrue(data['cleanup'])
            self.assertFalse(Path(plan['result_path']).exists())
            self.assertTrue((receipt/'qualification-synthetic'/'complete.json').is_file())
            self.assertEqual(os.stat(result).st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
