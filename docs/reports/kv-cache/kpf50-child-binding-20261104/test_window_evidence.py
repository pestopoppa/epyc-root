import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from window_evidence import EvidenceError
from window_evidence import validate

RUN = "kpf18-20261104T120000Z-7"


def child(i):
    return {"run_id": RUN, "role": "child", "suffix": i, "http": 200,
            "error": None, "timings": {"n_fork_tokens": 60000 + i}}


class WindowEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.rows = self.root / "rows.jsonl"
        self.record = self.root / "record.json"
        self.rows.write_text("".join(json.dumps(child(i)) + "\n" for i in range(4)))
        self.write_record()

    def tearDown(self):
        self.tmp.cleanup()

    def write_record(self, **updates):
        record = {"schema": "epyc.kpf.run.v1", "kpf18_item": 7,
                  "run_id": RUN, "rows": str(self.rows.resolve()),
                  "rows_sha256": hashlib.sha256(self.rows.read_bytes()).hexdigest(),
                  "checks": {"fork_expected": {"ok": 4, "n": 4, "failed": []}}}
        record.update(updates)
        self.record.write_text(json.dumps(record))

    def test_binds_finish_digest_and_native_run_id_but_stays_partial(self):
        out = validate(self.rows, self.record)
        self.assertEqual(out["source_sha256"], hashlib.sha256(self.rows.read_bytes()).hexdigest())
        self.assertEqual(out["run_id"], RUN)
        self.assertEqual(out["fork_tokens"], [60000, 60001, 60002, 60003])
        self.assertEqual(out["status"], "partial_structural_evidence")
        self.assertFalse(out["complete_outcome"])

    def test_refuses_missing_record_bad_digest_wrong_rows_or_wrong_run(self):
        self.record.unlink()
        with self.assertRaises((OSError, EvidenceError)):
            validate(self.rows, self.record)
        self.write_record(rows_sha256="0" * 64)
        with self.assertRaises(EvidenceError):
            validate(self.rows, self.record)
        self.write_record(rows=str(self.root / "other.jsonl"))
        with self.assertRaises(EvidenceError):
            validate(self.rows, self.record)
        self.write_record(run_id="foreign")
        with self.assertRaises(EvidenceError):
            validate(self.rows, self.record)

    def test_refuses_partial_and_failed_finish_records(self):
        self.write_record(partial=True)
        with self.assertRaises(EvidenceError):
            validate(self.rows, self.record)
        self.write_record(checks={"requests": {"ok": 3, "n": 4, "failed": ["timeout"]}})
        with self.assertRaises(EvidenceError):
            validate(self.rows, self.record)

    def test_digest_changes_are_rejected_even_if_rows_remain_parseable(self):
        self.rows.write_text(self.rows.read_text() + "\n")
        with self.assertRaises(EvidenceError):
            validate(self.rows, self.record)

    def test_rejects_wrong_record_kind_item_and_malformed_fork_count(self):
        for update in ({"schema": "wrong"}, {"kpf18_item": 8},
                       {"checks": {}},
                       {"checks": {"fork_expected": {"ok": True, "n": 4, "failed": []}}}):
            with self.subTest(update=update):
                self.write_record(**update)
                with self.assertRaises(EvidenceError):
                    validate(self.rows, self.record)

    def test_documented_cli_works_without_pythonpath(self):
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        result = subprocess.run(
            [sys.executable, str(HERE / "window_evidence.py"), str(self.rows), str(self.record)],
            cwd=self.root, env=env, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["run_id"], RUN)
        self.assertFalse(output["complete_outcome"])


if __name__ == "__main__":
    unittest.main()
