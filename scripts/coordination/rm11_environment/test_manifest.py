import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import warnings

from manifest import generate_manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ids = self.root / 'ids.txt'
        self.rows = self.root / 'rows.jsonl'
        self.archive = self.root / 'tests.zip'
        self.ids.write_text('row-1\n')
        self.row = {'row_id': 'row-1', 'decontamination': {'instance_id': 'repo-1', 'repo': 'org/repo', 'base_commit': 'abc'},
                    'provenance': {'instance_id': 'repo-1', 'comment_index': 0}}
        self.rows.write_text(json.dumps(self.row) + '\n')
        self.write_archive()

    def write_archive(self, test_file='repo-1/test_review_comment_0.py', include_test=True):
        result = {'instance_id': 'repo-1', 'results': [{'comment_index': 0, 'success': True, 'test_file': test_file}]}
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('testgen_combined/repo-1/result.json', json.dumps(result))
            if include_test:
                z.writestr('testgen_combined/repo-1/test_review_comment_0.py', '# test')

    def inventory(self):
        return generate_manifest(self.ids, self.rows, self.archive, expected_count=1)

    def test_selected_test_is_located_but_readiness_stays_false(self):
        result = self.inventory()
        row = result['instances'][0]
        self.assertEqual(row['archive']['selected_test_path'], 'testgen_combined/repo-1/test_review_comment_0.py')
        self.assertTrue(row['archive']['selected_historical_success'])
        self.assertFalse(result['ready_for_solve_scoring'])
        self.assertFalse(row['ready_for_solve_scoring'])
        self.assertEqual(row['tests_independent_for_issue_solve'], 'unknown')
        self.assertEqual(row['image_available'], 'unknown')
        self.assertEqual(len(result['inputs']['testgen_archive']['sha256']), 64)

    def test_missing_selected_test_does_not_imply_availability(self):
        self.write_archive(include_test=False)
        row = self.inventory()['instances'][0]
        self.assertTrue(row['archive']['selected_comment_present'])
        self.assertIsNone(row['archive']['selected_test_path'])
        self.assertFalse(row['ready_for_solve_scoring'])

    def test_rejects_cross_instance_and_traversal_selected_paths(self):
        for name in ('other/test.py', 'repo-1/../other/test.py'):
            with self.subTest(name=name):
                self.write_archive(name)
                with self.assertRaisesRegex(ValueError, 'escapes instance'):
                    self.inventory()

    def test_rejects_duplicate_ids_and_mismatched_instance(self):
        self.ids.write_text('row-1\nrow-1\n')
        with self.assertRaises(ValueError):
            self.inventory()
        self.ids.write_text('row-1\n')
        self.row['decontamination']['instance_id'] = 'other'
        self.rows.write_text(json.dumps(self.row) + '\n')
        with self.assertRaisesRegex(ValueError, 'inconsistent instance identity'):
            self.inventory()

    def test_rejects_ambiguous_duplicate_archive_member(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.archive, 'a') as z:
                z.writestr('testgen_combined/repo-1/result.json', '{}')
        with self.assertRaisesRegex(ValueError, 'duplicate member names'):
            self.inventory()


if __name__ == '__main__':
    unittest.main()
