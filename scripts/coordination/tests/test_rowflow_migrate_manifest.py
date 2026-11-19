"""Regression: `publish --migrate` of a real ready/<id>.json keeps its handoff_task and spec fields (2026-11-05)."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), 'rowflow'))
import rowflow as rf
from test_rowflow import Fixture


def ready_manifest(fx, rid, **over):
    d = fx.job(rid)
    lp = os.path.join(d, 'launch.sh')
    m = {
        'schema': 'epyc.row.v3', 'id': rid, 'owner': 'handoff-akagg', 'lane': 'cpu', 'regions': 'any-cpu-quarter',
        'launcher': {'path': lp, 'sha256': 'deadbeef'}, 'engine': {'path': fx.engine, 'sha256': 'cafe'},
        'result_path': os.path.join(d, 'out', 'results.jsonl'), 'result_format': 'jsonl',
        'decision_rule': 'pass when tests pass', 'handoff_task': 'handoffs/active/kernel-champion-and-promotion.md:CH-LB1.1',
        'estimate_s': 3000, 'min_window_s': 300, 'window_s': 3900, 'gib': 12, 'ports': [], 'priority_rank': 65.0,
        'scratch_root': d, 'keep': ['out/full', 'job.sh'], 'stop_file': os.path.join(d, 'STOP'), 'workdir': d,
        'first_progress_s': 3600, 'budget_gib': 5.0, 'shape': 'quarter', 'smoke_predicate': '/usr/bin/python3 -B ' + d + '/smoke.py',
        'unit_key': 'id', 'dryrun_native_result': True, 'busy_fraction': 0.5,
        'published_at': '2026-11-04T18:46:44Z', 'published_from': d + '/spec.json', 'publisher': {'pid': 1},
        'publish_warnings': ['x'], 'supersedes': 'older-row',
    }
    m.update(over)
    return m


class MigrateManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = Fixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()

    def test_handoff_task_kept_and_launcher_path_dict(self):
        spec = rf.spec_from_legacy(ready_manifest(self.fx, 'mig-keep-1'), self.fx.flags)
        self.assertEqual(spec['handoff_task'], 'handoffs/active/kernel-champion-and-promotion.md:CH-LB1.1')
        self.assertTrue(spec['launcher'].endswith('launch.sh'))

    def test_bare_file_normalised(self):
        for bare, want in (('kv-cache-program.md:KPF-61', 'handoffs/active/kv-cache-program.md:KPF-61'),
                           ('kv-cache-program.md', 'handoffs/active/kv-cache-program.md'),
                           ('kernel-champion-and-promotion.md: C3 r4 free text',
                            'handoffs/active/kernel-champion-and-promotion.md: C3 r4 free text')):
            spec = rf.spec_from_legacy(ready_manifest(self.fx, 'mig-bare-1', handoff_task=bare), self.fx.flags)
            self.assertEqual(spec['handoff_task'], want)

    def test_fillers_fallback_only_without_task(self):
        m = ready_manifest(self.fx, 'mig-fill-1')
        del m['handoff_task']
        self.assertEqual(rf.spec_from_legacy(m, self.fx.flags)['handoff_task'], 'FILLERS:mig-fill-1')
        m['row'] = 'alpha.md:X-1'
        self.assertEqual(rf.spec_from_legacy(m, self.fx.flags)['handoff_task'], 'handoffs/active/alpha.md:X-1')

    def test_spec_fields_carried_and_bookkeeping_dropped(self):
        spec = rf.spec_from_legacy(ready_manifest(self.fx, 'mig-fields-1'), self.fx.flags)
        for k, v in (('priority_rank', 65.0), ('shape', 'quarter'), ('regions', 'any-cpu-quarter'), ('ram_gib', 12),
                     ('estimate_s', 3000), ('first_progress_s', 3600), ('unit_key', 'id'), ('dryrun_native_result', True),
                     ('keep', ['out/full', 'job.sh']), ('result_format', 'jsonl'), ('busy_fraction', 0.5),
                     ('decision_rule', 'pass when tests pass'), ('supersedes', 'older-row'), ('ports', [])):
            self.assertEqual(spec[k], v, k)
        self.assertIn('smoke.py', spec['smoke_predicate'])
        for k in ('window_s', 'published_at', 'published_from', 'publisher', 'publish_warnings', 'engine', 'stop_file',
                  'workdir', 'schema', 'gib', 'sha256'):
            self.assertNotIn(k, spec, k)

    def test_republish_roundtrip(self):
        fx = self.fx
        m = ready_manifest(fx, 'mig-round-1')
        row = rf.publish(rf.spec_from_legacy(m, fx.flags), fx.flags, source='migrate-test')
        self.assertEqual(row['handoff_task'], m['handoff_task'])
        self.assertEqual(row['first_progress_s'], 3600)
        self.assertEqual(row['gib'], 12)
        self.assertEqual(row['priority_rank'], 65.0)


if __name__ == '__main__':
    unittest.main()
