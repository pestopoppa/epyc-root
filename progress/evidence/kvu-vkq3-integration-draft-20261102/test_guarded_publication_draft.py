import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from guarded_publication_draft import publish_unit, run_and_publish
from receipts import write_attempt


class IntegratedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.grants = self.root / 'grants'; self.grants.mkdir()
        self.now = 1793613600; end = self.now + 3600
        stamp = lambda n: dt.datetime.fromtimestamp(n, dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ')
        self.grant = self.grants / 'sample.grant'
        self.grant.write_text(f'regions=0-95 start={stamp(self.now-60)} end={stamp(end)} holds=\n')
        self.env = {'FILLER_ID':'sample', 'FILLER_NEEDGPU':'0', 'FILLER_CPUS':'0-95',
                    'FILLER_END':str(end), 'FILLER_DEADLINE':str(end-90),
                    'FILLER_STOPFILE':str(self.root/'stop')}
        self.args = dict(grant_dir=self.grants, local_stop=self.root/'local-stop', expected_id='sample',
                         attempt_id='x', root=self.root, argv=[sys.executable, '-c',
                         "import sys; sys.stdin.buffer.read(); print('[7, 8]')"],
                         input_bytes=b'abc', child_env=dict(os.environ), wall=lambda:self.now)
        self.full = self.root/'full.jsonl'

    def test_real_guard_child_receipt_and_atomic_publication(self):
        path = run_and_publish(env=self.env, full_result_path=self.full, **self.args)
        self.assertEqual(path, self.full)
        data = json.loads(path.read_text())
        self.assertEqual((data['mode'], data['validated_token_count']), ('full', 2))
        self.assertTrue((self.root/'full-x'/'complete.json').exists())
        with self.assertRaises(FileExistsError):
            run_and_publish(env=self.env, full_result_path=self.full, **self.args)

    def test_qualification_uses_engine_output_and_never_full_path(self):
        self.env.update(FILLER_DRYRUN='1', FILLER_DRYRUN_RESULT_PATH=str(self.root/'qual.jsonl'))
        self.grant.write_text(self.grant.read_text().rstrip() + ' schema=epyc.rowflow.dryrun-grant.v1 id=sample kind=rowflow-dryrun\n')
        output = run_and_publish(env=self.env, full_result_path=self.full, **self.args)
        self.assertEqual(output, self.root/'qual.jsonl')
        self.assertEqual(json.loads(output.read_text())['verdict'], 'excluded_qualification')
        self.assertFalse(self.full.exists())

    def test_incomplete_receipt_never_visible(self):
        result = dict(status='completed', cleanup=True, returncode=0, input_bytes_written=3,
                      elapsed_s=.1, stdout=b'[7]\n', stderr=b'')
        attempt = write_attempt(self.root, 'x', 'full', result, expected_input_bytes=3, ceiling_s=10)
        (attempt/'complete.json').unlink()
        with self.assertRaises(ValueError): publish_unit('full', 'x', attempt, self.full)
        self.assertFalse(self.full.exists())

    def test_link_failure_keeps_partial_invisible(self):
        result = dict(status='completed', cleanup=True, returncode=0, input_bytes_written=3,
                      elapsed_s=.1, stdout=b'[7]\n', stderr=b'')
        attempt = write_attempt(self.root, 'x', 'full', result, expected_input_bytes=3, ceiling_s=10)
        with mock.patch('guarded_publication_draft.os.link', side_effect=OSError('injected')):
            with self.assertRaises(OSError): publish_unit('full', 'x', attempt, self.full)
        self.assertFalse(self.full.exists())
        self.assertTrue((self.root/'.full.jsonl.tmp').exists())

if __name__ == '__main__': unittest.main()
