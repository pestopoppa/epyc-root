import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import runner_receipts
import window_custody

HERE = Path(__file__).resolve().parent

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.window = 'full-a'
        self.run = 'lineage1'
        window_custody.begin(self.root, self.window, self.run)
        common = {'window': self.window, 'run_id': self.run}
        self.put('outcome', {**common, 'schema': 'kpf50.window-outcome.v1', 'complete': True})
        self.put('cleanup', {**common, 'schema': 'kpf50.cleanup.v1', 'verified_dead': True, 'remaining_children': 0})
        for phase, tick, ts in [('clock_before', 1, 100), ('clock_after', 2, 200)]:
            self.put(phase, {**common, 'schema': 'kpf50.clock-sample.v1', 'phase': phase,
                             'hsa_tick': tick, 'hsa_hz': 1000, 'mono_before_ns': ts, 'mono_after_ns': ts+1})
        trace = b'profile rows\n'
        (self.root / 'trace.csv').write_bytes(trace)
        self.put('trace_manifest', {**common, 'schema': 'kpf50.trace-manifest.v1', 'complete': True,
            'files': [{'file': 'trace.csv', 'sha256': hashlib.sha256(trace).hexdigest()}]})

    def put(self, key, data):
        (self.root / f'{self.window}.{key}.json').write_text(json.dumps(data))

    def publish(self, fan=True, stop=None):
        return runner_receipts.publish_window(self.root, 0, self.run, fan,
              {'verified_dead': True} if stop is None else stop)

    def test_complete_produces_receipt_and_unlocks_next(self):
        self.publish()
        window_custody.begin(self.root, 'mask-a', self.run, window_custody.validate_prior)

    def test_incomplete_fan_and_missing_server_proof_refused(self):
        for fan, stop in [(False, {'verified_dead': True}), (True, {}), (True, {'verified_dead': 1})]:
            with self.assertRaises(ValueError): self.publish(fan, stop)
        self.assertFalse((self.root / 'full-a.complete.json').exists())

    def test_no_fabricated_proofs_and_trace_tampering_rejected(self):
        (self.root / 'full-a.cleanup.json').unlink()
        with self.assertRaises(OSError): self.publish()
        self.put('cleanup', {'schema': 'kpf50.cleanup.v1', 'window': self.window, 'run_id': self.run,
                             'verified_dead': True, 'remaining_children': 0})
        self.publish()
        (self.root / 'trace.csv').write_bytes(b'tampered')
        with self.assertRaises(ValueError): window_custody.begin(self.root, 'mask-a', self.run, window_custody.validate_prior)

    def test_runner_places_receipt_after_stop_and_after_clock(self):
        tree = ast.parse((HERE / 'kpf18_gate.py').read_text())
        item = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'item7')
        loop = next(n for n in item.body if isinstance(n, ast.For))
        segment = ast.get_source_segment((HERE / 'kpf18_gate.py').read_text(), loop)
        self.assertLess(segment.index('steps.append(stop_step(srv))'), segment.index('stage="after"'))
        self.assertLess(segment.index('stage="after"'), segment.index('def publish_window_receipt'))
        self.assertIn('state["fan_finished"] = True', segment)
        self.assertIn('state.get("fan_finished"), srv.stop_rec', segment)

if __name__ == '__main__':
    unittest.main()
