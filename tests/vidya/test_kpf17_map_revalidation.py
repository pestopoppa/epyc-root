"""Focused software controls for the prospective KPF-17 fixture and strict KPF projection."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import kv_prefix_fork
from claim_tuple import ProjectionError, grade
from producers import kpf17_map_revalidation as run


class Kpf17MapRevalidation(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.source = self.root / "source"
        self.source.mkdir()
        (self.root / "out").mkdir()
        for name in run.SOURCE_PINS:
            shutil.copyfile(ROOT / "docs/reports/kv-cache/kpf17-map-safe-row-20261104" / name, self.source / name)

    def setup_attempt(self, *, smoke=False, stop=False):
        def simulated_grant(context, threads):
            self.assertEqual(threads, 4)
            now = time.time()
            stamp = lambda epoch: datetime.fromtimestamp(epoch, timezone.utc).isoformat()
            raw = f"regions=72-75,168-171 start={stamp(now-30)} end={stamp(now+120)}"
            if smoke:
                raw += f" kind=rowflow-dryrun id={run.ROW}"
            flags = self.root if smoke else run.FLAGS
            context.update(grant_path=str(flags / "grants" / (run.ROW + ".grant")),
                           grant_text=raw, grant_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                           granted_cpus=[72, 73, 74, 75, 168, 169, 170, 171],
                           fixture_cpus=[72, 73, 74, 75], deadline_epoch=now+30)

        stop_path = self.root / "STOP"
        if stop:
            stop_path.touch()
        smoke_result = self.root / "smoke-result.json"
        variables = {"FILLER_DRYRUN": str(int(smoke)), "FILLER_DRYRUN_RESULT_PATH": str(smoke_result),
                     "FILLER_DRYRUN_DIR": str(self.root), "FILLER_STOPFILE": str(stop_path)}
        with patch.object(run, "acquire", side_effect=simulated_grant), patch.dict(os.environ, variables):
            rc = run.run(self.root, 4)
            if smoke and rc == 0:
                self.assertEqual(run.complete(self.root), 0)
            return rc

    def official_sidecar(self):
        self.assertEqual(self.setup_attempt(), 0)
        result = json.loads((self.root / "out/RESULT.json").read_text())
        self.assertEqual(run.complete(self.root), 0)
        return Path(result["sidecar"])

    def test_original_validator_and_existing_carrier(self):
        sidecar = self.official_sidecar()
        native, = kv_prefix_fork.native_rows(sidecar)
        claim = kv_prefix_fork.project(native)
        self.assertEqual(grade(claim)[:2], ("Judged", "Located"))
        self.assertEqual(claim.source_kind, kv_prefix_fork.SOURCE_KIND)
        self.assertFalse(claim.applicability)
        self.assertIn("second call", claim.claim)
        self.assertEqual(len(kv_prefix_fork.frames_for_sidecar(sidecar, as_of=claim.date)), 3)
        evidence = json.loads(sidecar.with_name("native.json").read_text())
        observed = evidence["observation"]
        self.assertTrue(observed["cleanup"])
        self.assertFalse(Path(observed["fixture"]).exists())
        self.assertEqual(len(observed["baseline"]), 5)

    def test_rehashed_wrong_observations_refuse(self):
        sidecar = self.official_sidecar()
        native_path = sidecar.with_name("native.json")
        baseline = native_path.read_bytes()
        context_sha = hashlib.sha256(sidecar.with_name("attempt.json").read_bytes()).hexdigest()
        for key, mutation in (
            ("cleanup", False),
            ("revalidation", {"outcome": "ACCEPTED"}),
            ("barrier", {}),
        ):
            with self.subTest(key=key):
                native = json.loads(baseline)
                native["observation"][key] = mutation
                raw = json.dumps(native).encode()
                native_path.write_bytes(raw)
                sidecar.write_text(json.dumps(run.sidecar_record(native, hashlib.sha256(raw).hexdigest(), context_sha)))
                with self.assertRaisesRegex(ProjectionError, "map-revalidation refused"):
                    kv_prefix_fork.frames_for_sidecar(sidecar, as_of=run.ended_utc(time.time()))

    def test_coherently_resealed_unreviewed_writer_refuses(self):
        sidecar = self.official_sidecar()
        producer_path = sidecar.parent / "source/producer.py"
        swapped = b"# Unreviewed writer\n" + producer_path.read_bytes()
        producer_path.write_bytes(swapped)
        context_path = sidecar.with_name("attempt.json")
        context = json.loads(context_path.read_bytes())
        context["producer_sha256"] = run.sha(swapped)
        context_bytes = json.dumps(context).encode()
        context_path.write_bytes(context_bytes)
        native_path = sidecar.with_name("native.json")
        native = json.loads(native_path.read_bytes())
        native["attempt_context_sha256"] = run.sha(context_bytes)
        native_bytes = json.dumps(native).encode()
        native_path.write_bytes(native_bytes)
        row = run.sidecar_record(native, run.sha(native_bytes), run.sha(context_bytes))
        sidecar.write_text(json.dumps(row))
        self.assertEqual(run.check_sidecar(row, sidecar), native)
        with self.assertRaisesRegex(ProjectionError, "does not bind the reviewed writer"):
            kv_prefix_fork.frames_for_sidecar(sidecar, as_of=run.ended_utc(time.time()))

    def test_smoke_stays_disjoint_and_historical_attempts_do_not_project(self):
        self.assertEqual(self.setup_attempt(smoke=True), 0)
        smoke = json.loads((self.root / "smoke-result.json").read_text())
        self.assertEqual(smoke["result_kind"], "smoke")
        self.assertFalse((self.root / "out/RESULT.json").exists())
        smoke_attempt, = (self.root / "out/smoke").iterdir()
        self.assertFalse((smoke_attempt / "belief_measurements.jsonl").exists())
        historic = ROOT / "docs/reports/kv-cache/kpf17-map-r3-20261104/RESULT.json"
        self.assertEqual(kv_prefix_fork.native_rows(historic), ())

    def test_stop_preserves_invalid_attempt_without_claim(self):
        self.assertEqual(self.setup_attempt(stop=True), 2)
        attempt, = (self.root / "out/attempts").iterdir()
        native = json.loads((attempt / "native.json").read_text())
        self.assertEqual(native["status"], "INVALID")
        self.assertEqual(native["observation"], {})
        self.assertFalse((attempt / "belief_measurements.jsonl").exists())
        self.assertFalse((self.root / "out/RESULT.json").exists())

    def test_external_exec_tripwire(self):
        with self.assertRaisesRegex(RuntimeError, "cannot execute"):
            run.no_external_exec("subprocess.Popen", ("/path/to/llama-server",))
