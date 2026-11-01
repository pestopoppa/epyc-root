import datetime as dt
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_COORD = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_COORD, 'rowflow'))
import rowflow as rf
from test_rowflow import Fixture


class AdmissionClassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()

    def test_optional_validate_and_persist(self):
        fx = self.fx
        rid = 'class-diagnostic-r2'
        d = fx.job(rid)
        row = rf.publish(fx.spec(rid, d, admission_class='diagnostic'), fx.flags)
        self.assertEqual(row['admission_class'], 'diagnostic')

        no_class_id = 'class-optional-r2'
        no_class_dir = fx.job(no_class_id)
        no_class_spec = fx.spec(no_class_id, no_class_dir)
        self.assertNotIn('admission_class', no_class_spec)
        no_class_row = rf.publish(no_class_spec, fx.flags)
        self.assertNotIn('admission_class', no_class_row)

        for invalid in ('invented', {'name': 'diagnostic'}, 12):
            bad_id = 'class-invalid-' + str(abs(hash(repr(invalid))))
            bad_dir = fx.job(bad_id)
            with self.assertRaises(rf.Refused):
                rf.publish(fx.spec(bad_id, bad_dir, admission_class=invalid), fx.flags)

    def test_synthetic_grant_carries_id_class_and_regions(self):
        start = dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc)
        end = dt.datetime(2026, 11, 1, 0, 10, tzinfo=dt.timezone.utc)
        text = rf.dryrun_grant_text('class-diagnostic-r2', 'diagnostic', '0-23', {'q0'}, start, end)
        self.assertIn('schema=epyc.rowflow.dryrun-grant.v1', text)
        self.assertIn('id=class-diagnostic-r2', text)
        self.assertIn('kind=rowflow-dryrun', text)
        self.assertIn('admission_class=diagnostic', text)
        self.assertIn('regions=0-23', text)
        self.assertIn('holds=q0', text)
        no_class = rf.dryrun_grant_text('class-optional-r2', None, 'q1', {'q1'}, start, end)
        self.assertIn('id=class-optional-r2', no_class)
        self.assertNotIn('admission_class=', no_class)
        with self.assertRaises(rf.Refused):
            rf.dryrun_grant_text('class-invalid-r2', 'bogus', 'q0', {'q0'}, start, end)

    def test_legacy_class_survives_v3_migration(self):
        fx = self.fx
        rid = 'class-legacy-r2'
        d = fx.job(rid)
        legacy = {'id': rid, 'owner': 'codex-test', 'regions': 'any-cpu-quarter',
                  'window_s': 3600, 'min_window_s': 300, 'gib': 8,
                  'launcher': {'path': os.path.join(d, 'launch.sh')},
                  'scratch_root': d, 'result_path': os.path.join(d, 'out/results.jsonl'),
                  'decision_rule': 'descriptive only', 'class': 'diagnostic'}
        spec = rf.spec_from_legacy(legacy, fx.flags)
        self.assertEqual(spec['admission_class'], 'diagnostic')
        row = rf.publish(spec, fx.flags, source='migrate-test')
        self.assertEqual(row['admission_class'], 'diagnostic')


if __name__ == '__main__':
    unittest.main()
