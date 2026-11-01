"""Static identity and row/manifest scheduling consistency checks."""
import os
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/coordination'))
import qualify_launcher as q


class ManifestBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.m = {'id': 'bind-1', 'launcher': str(self.root/'launch.sh'), 'row': str(self.root/'row.md'),
                  'regions': 'any-cpu-quarter', 'claimed_cpus': 'any-cpu-quarter',
                  'window_s': 600, 'min_window_s': 60, 'gib': 8, 'process_limit_GiB': 6,
                  'est_output_GiB': 2, 'scratch_root': str(self.root), 'requires_tools':['bash'],
                  'ports':[], 'shared_state':[], 'exclusive_class':None,
                  'items':1, 'tokens_per_item':1, 'n_ctx_required':32}
        self.cells = ['bind-1', 'refactor', str(self.root/'launch.sh'), 'any-cpu-quarter', '60 s', '8 GiB',
                      str(self.root/'STOP'), 'READY', 'cpu', '600 s', '60 s', 'n', 'n', 'manifest', 'purpose',
                      'n/a (fixture)', 'cpu',
                      'requested_window_s=600; est_output_GiB=2; scratch_root=%s; claimed_cpus=any-cpu-quarter; process_limit_GiB=6' % self.root]
        self.write_row()

    def write_row(self):
        Path(self.m['row']).write_text('| ' + ' | '.join(self.cells) + ' |\n')

    def test_matching_row_binds_all_scheduling_fields(self):
        record = q.check_row_binding(self.m)
        self.assertEqual(record['reserved_ram_gib'], 8)
        self.assertEqual(record['process_limit_GiB'], 6)
        self.assertEqual(record['est_output_GiB'], 2)
        self.assertEqual(record['scratch_root'], str(self.root.resolve()))

    def test_row_ram_mismatch_refused(self):
        self.cells[5] = '32 GiB'; self.write_row()
        with self.assertRaisesRegex(q.Refused, 'row-ram-manifest-mismatch'):
            q.check_row_binding(self.m)

    def test_row_output_scratch_and_region_mismatch_refused(self):
        mutations = [
            (17, 'requested_window_s=600; est_output_GiB=3; scratch_root=%s; claimed_cpus=any-cpu-quarter; process_limit_GiB=6' % self.root, 'row-output-estimate'),
            (17, 'requested_window_s=600; est_output_GiB=2; scratch_root=/tmp; claimed_cpus=any-cpu-quarter; process_limit_GiB=6', 'row-scratch-root'),
            (3, 'q0', 'row-regions-manifest'),
            (17, 'requested_window_s=600; est_output_GiB=2; scratch_root=%s; claimed_cpus=0-95; process_limit_GiB=6' % self.root, 'row-relocatable-cpus'),
        ]
        for index, value, reason in mutations:
            with self.subTest(reason=reason):
                original = self.cells[index]; self.cells[index] = value; self.write_row()
                with self.assertRaisesRegex(q.Refused, reason): q.check_row_binding(self.m)
                self.cells[index] = original; self.write_row()

    def test_engine_copy_cannot_define_itself_as_canonical(self):
        fake_root = self.root/'copied-package'; (fake_root/'scripts/coordination').mkdir(parents=True)
        engine = fake_root/'scripts/coordination/filler_run14.sh'; engine.write_text('# copied\n')
        for field in ('launcher', 'job', 'qual_fixture', 'source_manifest'):
            path = self.root/field; path.write_text('# fixture\n'); self.m[field] = str(path)
        model = self.root / 'model'
        model.write_text('model identity fixture\n')
        self.m['qualification_model'] = {
            'id': 'fixture-model', 'path': str(model), 'sha256': q.sha(model)}
        self.m['engine'] = str(engine)
        allow = self.root/'allow.json'
        allow.write_text(json.dumps({'kind':'epyc.engine-allowlist.v1',
            'engines':[hashlib.sha256(engine.read_bytes()).hexdigest()]}))
        with patch.dict(os.environ, {'WS58_ROOT': str(ROOT)}):
            with patch.object(q, 'checked_manifest', return_value='fixture'):
                with self.assertRaisesRegex(q.Refused, 'noncanonical-engine'):
                    q.static_check(self.m, allow)


if __name__ == '__main__':
    unittest.main()
