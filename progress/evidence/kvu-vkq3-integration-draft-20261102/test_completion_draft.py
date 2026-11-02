import json
from pathlib import Path
import tempfile
import unittest
from completion_draft import complete_diagnostic, publish_unit
from receipts import write_attempt


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make(self, mode='full', **kwargs):
        result = dict(status='completed', cleanup=True, returncode=0, input_bytes_written=3,
                      elapsed_s=0.1, stdout=b'[1, 2]\n', stderr=b'')
        result.update(kwargs)
        return write_attempt(self.root, 'test', mode, result, expected_input_bytes=3, ceiling_s=10)

    def test_full_and_qualification_are_separate(self):
        for mode in ('full', 'qualification'):
            path = self.make(mode)
            self.assertTrue(complete_diagnostic(mode, 'test', path))
            self.assertFalse(complete_diagnostic('full' if mode == 'qualification' else 'qualification', 'test', path))

    def test_qual_failure_cannot_qualify_but_full_failure_is_inconclusive(self):
        full = self.make('full', status='timeout')
        qual = self.make('qualification', status='timeout')
        self.assertTrue(complete_diagnostic('full', 'test', full))
        self.assertFalse(complete_diagnostic('qualification', 'test', qual))

    def test_cleanup_failure_and_empty_output_rejected(self):
        full = self.make('full', cleanup=False)
        qual = self.make('qualification', stdout=b'[]\n')
        self.assertFalse(complete_diagnostic('full', 'test', full))
        self.assertFalse(complete_diagnostic('qualification', 'test', qual))

    def test_full_zero_token_count_is_valid_native_result(self):
        full = self.make('full', stdout=b'[]\n')
        self.assertTrue(complete_diagnostic('full', 'test', full))

    def test_partial_mismatch_and_wrong_marker_rejected(self):
        path = self.make()
        (path / 'unit.jsonl').write_text('{}\n')
        self.assertFalse(complete_diagnostic('full', 'test', path))

    def test_rowflow_output_published_only_after_complete_receipt(self):
        path = self.make('full')
        marker = path / 'complete.json'
        marker_data = marker.read_bytes()
        marker.unlink()
        dest = self.root / 'rowflow-result.jsonl'
        with self.assertRaises(ValueError):
            publish_unit('full', 'test', path, dest)
        self.assertFalse(dest.exists())
        marker.write_bytes(marker_data)
        publish_unit('full', 'test', path, dest)
        self.assertEqual(json.loads(dest.read_text())['verdict'], 'synthetic_input_completed')
        with self.assertRaises(FileExistsError):
            publish_unit('full', 'test', path, dest)

    def test_revoked_grant_during_publication_stays_invisible(self):
        path = self.make()
        dest = self.root / 'rowflow-result.jsonl'
        def reject():
            raise RuntimeError('grant lost during result publication')
        with self.assertRaisesRegex(RuntimeError, 'grant lost'):
            publish_unit('full', 'test', path, dest, before_publish=reject)
        self.assertFalse(dest.exists())
        self.assertTrue((self.root / '.rowflow-result.jsonl.tmp').exists())

    def test_native_dryrun_json_contains_qualification_unit(self):
        path = self.make('qualification')
        dest = self.root / 'native-result.json'
        publish_unit('qualification', 'test', path, dest)
        self.assertEqual(json.loads(dest.read_text())['verdict'], 'excluded_qualification')
        (path / 'unit.jsonl').write_text((path / 'result.json').read_text())
        (path / 'complete.json').write_text(json.dumps({'mode': 'qualification', 'attempt_id': 'test'}))
        self.assertFalse(complete_diagnostic('full', 'test', path))
        (path / 'complete.json').unlink()
        self.assertFalse(complete_diagnostic('full', 'test', path))


if __name__ == '__main__':
    unittest.main()
