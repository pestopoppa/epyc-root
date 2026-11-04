import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from loss_coverage_verifier import verify
from replay_receipt import adapt
from replay_receipt import main
from test_loss_coverage_verifier import sample


class ReceiptAdapterTests(unittest.TestCase):
    def test_structural_replay_and_tamper_refusal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw, head = sample(100, 0, 1100)
            ring = root / "cpu-0.ring"
            ring.write_bytes(raw)
            capture = {"cpu": 0, "event_id": 100, "tracepoint_id": 1100,
                       "raw_file": ring.name, "raw_size": len(raw),
                       "raw_sha256": hashlib.sha256(raw).hexdigest(),
                       "data_size": len(raw), "head": head, "tail": 0,
                       "target": {"pid": 1, "start_ticks": 1},
                       "counter": {"count": 1, "enabled_ns": 300,
                                   "running_ns": 300, "lost_samples": 0},
                       "enable_after_ns": 100, "disable_before_ns": 400}
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"schema": "epyc.ch26.hostscope-perf-evidence.v1",
                                            "measurement_claim": "none", "captures": [capture]}))
            result = verify(adapt(manifest, {0}), expected_cpus={0},
                            expected_events=frozenset({"sched_switch"}))
            self.assertEqual(result["measurement_admission"], "none")
            output = root / "result.json"
            with patch("sys.argv", ["replay_receipt.py", "--manifest", str(manifest),
                                    "--manifest-sha256", hashlib.sha256(manifest.read_bytes()).hexdigest(),
                                    "--cpus", "0", "--output", str(output)]), \
                 patch("builtins.print"):
                self.assertEqual(main(), 0)
            saved = json.loads(output.read_text())
            self.assertEqual(saved["capture_overlap_ns"], [100, 400])
            self.assertNotIn("request_window_ns", saved)
            self.assertIn("empty error arrays are adapter scaffolding, not producer error receipts",
                          saved["limitations"])
            with self.assertRaisesRegex(ValueError, "inventory size"):
                adapt(manifest, {0, 1})
            with self.assertRaisesRegex(ValueError, "manifest digest"):
                adapt(manifest, {0}, expected_sha256="0" * 64)
            bad_identity = dict(capture, target={"pid": 0, "start_ticks": 1})
            manifest.write_text(json.dumps({"schema": "epyc.ch26.hostscope-perf-evidence.v1",
                                            "measurement_claim": "none", "captures": [bad_identity]}))
            with self.assertRaisesRegex(ValueError, "owned-child identity"):
                adapt(manifest, {0})
            ring.write_bytes(raw + b"x")
            manifest.write_text(json.dumps({"schema": "epyc.ch26.hostscope-perf-evidence.v1",
                                            "measurement_claim": "none", "captures": [capture]}))
            with self.assertRaisesRegex(ValueError, "size or digest"):
                adapt(manifest, {0})
            manifest.write_text(json.dumps({"schema": "epyc.ch26.hostscope-perf-evidence.v1",
                                            "measurement_claim": "floor", "captures": [capture]}))
            with self.assertRaisesRegex(ValueError, "measurement claim"):
                adapt(manifest, {0})
            manifest.write_text("[]")
            with self.assertRaisesRegex(ValueError, "must be an object"):
                adapt(manifest, {0})


if __name__ == "__main__":
    unittest.main()
