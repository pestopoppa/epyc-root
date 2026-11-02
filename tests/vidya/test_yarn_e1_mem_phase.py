"""Prospective synthetic controls, never a historical measurement."""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
from adapters import yarn_e1_mem_phase as adapter
from claim_tuple import ProjectionError, grade

PACKET = ROOT / 'scripts/coordination/gpu-serving-tie-in/yarn-e1-memory'


class YarnPhaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.d = self.root / 'out/E1-A0-low'; self.d.mkdir(parents=True)
        (self.root / 'inputs').mkdir(); (self.root / 'inputs/manifest.json').write_text('{}')
        (self.root / 'source.py').write_text('source')
        srcsha = hashlib.sha256((self.root / 'source.py').read_bytes()).hexdigest()
        (self.root / 'SOURCE.sha256').write_text(f'{srcsha}  source.py\n')
        self.source = hashlib.sha256((self.root / 'SOURCE.sha256').read_bytes()).hexdigest()
        (self.root / 'model-pin.json').write_text(json.dumps({'sha256': adapter.MODEL_SHA256}))
        (self.root / 'image-binding.json').write_text(json.dumps({'source_commit': adapter.IMAGE_COMMIT}))
        (self.d / 'launch.json').write_text(json.dumps({'pid': 123, 'at': 1}))
        (self.d / 'runtime-proof.json').write_text(json.dumps({'pid': 123}))
        (self.d / 'kfd.jsonl').write_text(json.dumps({'t': 2.5, 'pid_vram_gib': 2.0, 'kfd_pids': [123]}) + '\n')
        (self.d / 'hip.jsonl').write_text('trace')
        at = datetime.fromtimestamp(3, timezone.utc).isoformat()
        calls = [{'stage': s, 'at': at, 'timings': {'wall_s': 1}} for s in ('128k', '240k') for _ in range(6)]
        (self.d / 'calls.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in calls))
        self.a = {'kfd': str(self.d / 'kfd.jsonl'), 'shim': str(self.d / 'hip.jsonl'),
                  'native_calls': str(self.d / 'calls.jsonl'), 'stages': {
                      s: {'start': 2, 'end': 3, 'requests': 6, 'own_kfd_peak_gib': 2.0} for s in ('128k', '240k')}}
        (self.d / 'phase-attribution.json').write_text(json.dumps(self.a))
        spec = importlib.util.spec_from_file_location('yarn_fixture_writer', PACKET / 'belief_capture.py')
        capture = importlib.util.module_from_spec(spec); spec.loader.exec_module(capture)
        with patch.dict(os.environ, {'FILLER_ID': adapter.RUN_ID}):
            self.path = capture.emit(self.d, self.a)
        self.trust = patch.object(adapter, 'TRUSTED_SOURCE_SHA256', self.source); self.trust.start()

    def tearDown(self):
        self.trust.stop(); self.tmp.cleanup()

    def test_observations_project_with_shared_grader(self):
        rows = adapter.native_rows(self.path)
        self.assertEqual([x['phase'] for x in rows], ['128k', '240k'])
        self.assertEqual(grade(adapter.project(rows[0]))[:2], ('Judged', 'Located'))

    def test_relocated_retained_run_projects_and_escape_refuses(self):
        moved = self.root.parent / (self.root.name + '-retained')
        self.addCleanup(shutil.rmtree, moved, ignore_errors=True)
        shutil.copytree(self.root, moved)
        moved_path = moved / self.path.relative_to(self.root)
        self.assertEqual(len(adapter.native_rows(moved_path)), 2)
        rows = [json.loads(x) for x in moved_path.read_text().splitlines()]
        rows[0]['kfd_path'] = '../outside'
        body = dict(rows[0]); body.pop('row_sha256')
        rows[0]['row_sha256'] = hashlib.sha256(adapter._canonical(body)).hexdigest()
        moved_path.write_text(''.join(json.dumps(x) + '\n' for x in rows))
        with self.assertRaises(ProjectionError): adapter.native_rows(moved_path)

    def test_changed_source_or_trace_refuses(self):
        (self.root / 'source.py').write_text('changed')
        with self.assertRaises(ProjectionError): adapter.native_rows(self.path)
        (self.root / 'source.py').write_text('source')
        (self.d / 'kfd.jsonl').write_text('{}\n')
        with self.assertRaises(ProjectionError): adapter.native_rows(self.path)

    def test_tampered_row_and_missing_phase_refuse(self):
        original = self.path.read_text().splitlines(); row = json.loads(original[0]); row['value'] = 99
        self.path.write_text(json.dumps(row) + '\n' + original[1] + '\n')
        with self.assertRaises(ProjectionError): adapter.native_rows(self.path)
        self.path.write_text(original[0] + '\n')
        with self.assertRaises(ProjectionError): adapter.native_rows(self.path)

if __name__ == '__main__': unittest.main()
