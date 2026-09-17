"""Hermetic checks for native, epoch-local serving momentum projection."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit/autokernel_observed_momentum.py"
SPEC = importlib.util.spec_from_file_location("autokernel_observed_momentum", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _row(*, rate: float, metric: str = "aggregate_tok_s", matched: bool = False) -> str:
    comparison = {
        "schema": "epyc.autokernel.serving_ab.v2" if matched else "epyc.autokernel.serving_ab.v1",
        "metric": metric,
        "surface": "serving:glm", "recipe_hash": "r" * 64,
        "request_digest": "q" * 64, "anchor_tok_s": 10.0,
        "candidate_tok_s": rate, "pairs": 5,
    }
    if matched:
        comparison["measurement_plan"] = {
            "instrument": "matched_process_v2", "unit": "process", "pairs": 5,
            "stopping": "fixed_pairs", "seed": "a" * 32,
            "order_algorithm": "autokernel.evaluator.statistics.OrderSchedule.v1",
            "orders": [["anchor", "candidate"]] * 5,
        }
        comparison["launch_membership"] = [{} for _ in range(10)]
    return json.dumps({"comparison": comparison})


class ObservedMomentumTest(unittest.TestCase):
    def test_epoch_boundary_resets_and_preserves_native_times(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "experiments.db"
            connection = sqlite3.connect(db)
            connection.execute("CREATE TABLE experiments (attempt_id TEXT, recorded_at TEXT, "
                               "epoch_sha256 TEXT, status TEXT, payload TEXT)")
            rows = [("a", "2026-09-17T10:00:00Z", "epoch-a", "measured_null", _row(rate=10.0)),
                    ("b", "2026-09-17T10:01:00Z", "epoch-a", "kept", _row(rate=11.0)),
                    ("c", "2026-09-17T11:00:00Z", "epoch-b", "measured_null",
                     _row(rate=20.0, matched=True)),
                    ("d", "2026-09-17T11:01:00Z", "epoch-b", "measured_null",
                     _row(rate=21.0, metric="unknown_metric"))]
            connection.executemany("INSERT INTO experiments VALUES (?,?,?,?,?)", rows)
            connection.commit()
            connection.close()
            report = MODULE.project(db)
        self.assertEqual(report["excluded"], {"unsupported_metric_direction": 1})
        self.assertEqual(len(report["epochs"]), 2)
        first = next(epoch for epoch in report["epochs"] if epoch["epoch_sha256"] == "epoch-a")
        second = next(epoch for epoch in report["epochs"] if epoch["epoch_sha256"] == "epoch-b")
        self.assertEqual(first["points"][0]["recorded_at"], "2026-09-17T10:00:00Z")
        self.assertIsNone(first["points"][0]["relative_progress_ewma"])
        self.assertAlmostEqual(first["points"][1]["relative_progress_ewma"], 0.015)
        self.assertIsNone(second["points"][0]["relative_progress_ewma"])
        self.assertEqual(second["instrument"], "matched_process_v2")
        self.assertIsNone(report["cross_epoch_absolute_gain"])
        self.assertIsNone(report["cost_credit_vs_ak_d32"])
        receipt = MODULE.provenance_receipt(report)
        self.assertEqual(receipt["report_sha256"], MODULE._digest(report))
        self.assertEqual(receipt["source_rows_sha256"], MODULE._digest(report["input_rows"]))
        self.assertEqual(receipt["content_sha256"],
                         MODULE._digest({key: value for key, value in receipt.items()
                                         if key != "content_sha256"}))

    def test_bound_refuses_partial_timeline(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "experiments.db"
            connection = sqlite3.connect(db)
            connection.execute("CREATE TABLE experiments (attempt_id TEXT, recorded_at TEXT, "
                               "epoch_sha256 TEXT, status TEXT, payload TEXT)")
            connection.executemany("INSERT INTO experiments VALUES (?,?,?,?,?)",
                                   [(str(i), str(i), "epoch", "measured_null", _row(rate=10.0))
                                    for i in range(3)])
            connection.commit()
            connection.close()
            with self.assertRaisesRegex(ValueError, "bound reached"):
                MODULE.project(db, max_attempts=2)


if __name__ == "__main__":
    unittest.main()
