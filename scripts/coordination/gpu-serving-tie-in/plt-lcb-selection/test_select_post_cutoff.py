import datetime as dt
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from select_post_cutoff import _candidates_after_contest_date, make_manifest, main, REVISION, MODEL_REVISION


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'release.txt').write_text('original contest publication')
        digest = hashlib.sha256((self.root / 'release.txt').read_bytes()).hexdigest()
        self.audit = {'dataset_revision': REVISION, 'reviewed_by': 'fixture-reviewer', 'items': [
            {'question_id': 'x', 'finding': 'original_release_not_before_contest',
             'original_release_date': '2026-06-17', 'source_url': 'https://primary.example/event',
             'evidence_file': 'release.txt', 'evidence_sha256': digest}]}
        self.source = {'dataset': 'livecodebench/code_generation_lite', 'revision': REVISION, 'config': 'release_v6'}
        self.witness = {'model_revision': MODEL_REVISION, 'kind': 'author_cutoff', 'source_url': 'https://primary.example/model',
                        'source_sha256': 'f' * 64, 'cutoff_date': '2026-06-16'}
        self.rows = [{'question_id': 'x', 'contest_date': '2026-06-17T00:00:00'}]

    def tearDown(self): self.tmp.cleanup()

    def test_strict_after_and_stable_order(self):
        rows = [{'question_id': 'b', 'contest_date': '2026-06-17T12:00:00'},
                {'question_id': 'old', 'contest_date': '2026-06-16T23:59:59'},
                {'question_id': 'a', 'contest_date': '2026-06-17T00:00:00'}]
        got = _candidates_after_contest_date(rows, dt.date(2026, 6, 16), minimum=2)
        self.assertEqual([x['question_id'] for x in got], ['a', 'b'])

    def test_refuses_duplicate_unknown_date_and_insufficient(self):
        row = {'question_id': 'x', 'contest_date': '2026-06-18T00:00:00'}
        for rows in ([row, row], [{'question_id': 'x', 'contest_date': None}], [row]):
            with self.assertRaises(ValueError): _candidates_after_contest_date(rows, dt.date(2026, 6, 16), minimum=2)

    def test_refuses_to_hash_or_select_under_grant(self):
        argv = ['select', '--source-manifest', 'missing', '--witness', 'missing', '--witness-evidence', 'missing',
                '--release-audit', 'missing', '--release-evidence-root', 'missing', '--shard', 'missing', '--output', 'missing']
        with patch.dict(os.environ, {'FILLER_ID': 'test-row'}), patch.object(sys, 'argv', argv):
            with self.assertRaisesRegex(ValueError, 'before publishing'): main()

    def test_refuses_unpinned_model_or_evidence(self):
        self.assertEqual(len(make_manifest(self.source, self.witness, self.rows, 1, self.audit, self.root)['items']), 1)
        for key in ('model_revision', 'kind', 'source_url', 'source_sha256'):
            broken = dict(self.witness); broken[key] = ''
            with self.assertRaises(ValueError): make_manifest(self.source, broken, self.rows, 1, self.audit, self.root)

    def test_requires_item_specific_release_evidence_and_lower_bound(self):
        for bad in ({'dataset_revision': REVISION, 'reviewed_by': 'r', 'items': []},
                    {'dataset_revision': REVISION, 'reviewed_by': 'r', 'items': [dict(self.audit['items'][0], original_release_date='2026-06-15')]},
                    {'dataset_revision': REVISION, 'reviewed_by': 'r', 'items': [dict(self.audit['items'][0], evidence_file='../escape')]}):
            with self.assertRaises(ValueError): make_manifest(self.source, self.witness, self.rows, 1, bad, self.root)
        (self.root / 'release.txt').write_text('changed')
        with self.assertRaises(ValueError): make_manifest(self.source, self.witness, self.rows, 1, self.audit, self.root)


if __name__ == '__main__': unittest.main()
