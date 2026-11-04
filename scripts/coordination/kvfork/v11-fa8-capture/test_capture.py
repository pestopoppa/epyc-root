import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('capture', Path(__file__).with_name('capture.py'))
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.ids = [dict(arm=a, context=c, layer=0, kind=k, index=0)
                    for a in ('A', 'C') for c in (8192, 57000)
                    for k in ('v_abs_max', 'row_sum')]
        self.manifest = {'schema': 'v11-fa8-identities-v1', 'expected': self.ids}
        self.records = [{**row, 'value': (3.0 if row['kind'] == 'v_abs_max' else -65505)} for row in self.ids]

    def test_complete_raw_summary_not_verdict(self):
        rows = capture.validate_capture(self.manifest, self.records)
        self.assertEqual(sum(r['above_fp16_range'] for r in rows), 4)
        self.assertEqual(sum(r['count'] for r in rows), 8)

    def test_nonfinite_explicit_and_unsafe_float_rejected(self):
        self.records[1]['value'] = 'nan'
        rows = capture.validate_capture(self.manifest, self.records)
        self.assertEqual(sum(r['nonfinite'] for r in rows), 1)
        self.records[1]['value'] = float('nan')
        with self.assertRaises(ValueError): capture.validate_capture(self.manifest, self.records)

    def test_missing_duplicate_and_unknown_refused(self):
        for rows in (self.records[:1], self.records + [self.records[0]],
                     self.records + [{**self.records[0], 'index': 9}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                capture.validate_capture(self.manifest, rows)

    def test_manifest_requires_both_metrics_and_unique_ids(self):
        for ids in ([], self.ids[:1], self.ids + [self.ids[0]]):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                capture.validate_capture({'schema': 'v11-fa8-identities-v1', 'expected': ids}, self.records)

    def test_missing_arm_or_context_refused_even_when_records_match(self):
        for subset in ([r for r in self.records if r['arm'] == 'A'],
                       [r for r in self.records if r['context'] == 8192]):
            ids = [{k: row[k] for k in capture.KEYS} for row in subset]
            with self.assertRaises(ValueError):
                capture.validate_capture({'schema': 'v11-fa8-identities-v1', 'expected': ids}, subset)

    def test_negative_vmax_and_invalid_identity_rejected(self):
        self.records[0]['value'] = -1
        with self.assertRaises(ValueError): capture.validate_capture(self.manifest, self.records)
        self.records[0] = {**self.ids[0], 'context': True, 'value': 1}
        with self.assertRaises(ValueError): capture.validate_capture(self.manifest, self.records)

if __name__ == '__main__': unittest.main()
