import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from child_evidence import EvidenceError, validate

RUN = "kpf18-20261104T120000Z-7"
def row(suffix, *, run_id=RUN, http=200, error=None, count=60000):
    return {"run_id": run_id, "role": "child", "suffix": suffix, "http": http,
            "error": error, "timings": {"n_fork_tokens": count}}

class ChildEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "rows.jsonl"
    def tearDown(self):
        self.tmp.cleanup()
    def write(self, rows):
        self.path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    def test_validates_exact_children_identity_and_digest_as_partial(self):
        rows = [{"run_id": RUN, "role": "trunk_first", "http": 200}] + [row(i, count=60000+i) for i in range(4)]
        self.write(rows)
        out = validate(self.path, RUN)
        self.assertEqual(out["fork_tokens"], [60000, 60001, 60002, 60003])
        self.assertEqual(out["source_sha256"], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(out["run_id"], RUN)
        self.assertFalse(out["complete_outcome"])
    def test_rejects_missing_duplicate_and_unexpected_suffix(self):
        for rows in ([row(i) for i in range(3)], [row(i) for i in range(3)] + [row(2)],
                     [row(i) for i in range(3)] + [row(4)]):
            with self.subTest(rows=rows):
                self.write(rows)
                with self.assertRaises(EvidenceError): validate(self.path, RUN)
    def test_rejects_non_integer_or_below_threshold_counts(self):
        for value in (True, "60000", 59999):
            self.write([row(i, count=value if i == 1 else 60000) for i in range(4)])
            with self.subTest(value=value), self.assertRaises(EvidenceError): validate(self.path, RUN)
    def test_rejects_failed_http_or_error(self):
        for kw in ({"http": 500}, {"error": "failed"}):
            self.write([row(i, **kw) if i == 2 else row(i) for i in range(4)])
            with self.subTest(kw=kw), self.assertRaises(EvidenceError): validate(self.path, RUN)
    def test_rejects_foreign_run_malformed_json_and_non_object(self):
        self.write([row(i, run_id="other" if i == 1 else RUN) for i in range(4)])
        with self.assertRaises(EvidenceError): validate(self.path, RUN)
        for raw in ('{bad json}\n', '[]\n'):
            self.path.write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(EvidenceError): validate(self.path, RUN)
    def test_rejects_foreign_non_child_row(self):
        self.write([{"run_id": "other", "role": "trunk_first"}] + [row(i) for i in range(4)])
        with self.assertRaises(EvidenceError): validate(self.path, RUN)

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("child_evidence.py")),
             str(self.path), "--run-id", RUN, *map(str, args)],
            capture_output=True, text=True, check=False)

    def test_cli_refuses_input_aliases_without_changing_raw_bytes(self):
        self.write([row(i) for i in range(4)])
        raw = self.path.read_bytes()
        symlink = self.path.with_name("symlink.jsonl")
        symlink.symlink_to(self.path)
        hardlink = self.path.with_name("hardlink.jsonl")
        hardlink.hardlink_to(self.path)
        for output in (self.path, symlink, hardlink):
            with self.subTest(output=output):
                result = self.cli("--out", output)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("File exists", result.stderr)
                self.assertEqual(self.path.read_bytes(), raw)
                self.assertEqual(output.read_bytes(), raw)

    def test_cli_creates_separate_nested_output_and_preserves_input(self):
        self.write([row(i) for i in range(4)])
        raw = self.path.read_bytes()
        output = self.path.parent / "nested" / "partial.json"
        result = self.cli("--out", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.read_bytes(), raw)
        evidence = json.loads(output.read_text())
        self.assertEqual(evidence["source_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(evidence["complete_outcome"])

    def test_cli_refuses_existing_separate_output_and_dangling_symlink(self):
        self.write([row(i) for i in range(4)])
        raw = self.path.read_bytes()
        output = self.path.with_name("existing.json")
        output.write_bytes(b"keep existing evidence")
        dangling = self.path.with_name("dangling.json")
        missing = self.path.with_name("missing.json")
        dangling.symlink_to(missing)
        for destination in (output, dangling):
            with self.subTest(destination=destination):
                result = self.cli("--out", destination)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(self.path.read_bytes(), raw)
                self.assertEqual(output.read_bytes(), b"keep existing evidence")
                self.assertFalse(missing.exists())

    def test_cli_stdout_still_emits_partial_evidence(self):
        self.write([row(i) for i in range(4)])
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "partial_structural_evidence")

if __name__ == "__main__": unittest.main()
