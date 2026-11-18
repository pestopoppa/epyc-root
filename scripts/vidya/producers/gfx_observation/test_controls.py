"""Synthetic structural controls. These paths carry no native measurement authority."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import native
import reader
from observation import *  # noqa: F403


def fixture(root, *, delta):
    root.mkdir()
    files = {
        "request.json": REQUEST, "response.json": {"stop": True, "content": "generated", "tokens_predicted": 32},
        "server.log": {"fixture": True}, "ggml-linkage.log": {"fixture": True},
    }
    trace = {
        "schema": gpu_counter.SCHEMA, "claim_device_id": "mi210_0", "closed": True,
        "full_claim_coverage": None, "claim_acquired_observed_ns": 1, "claim_release_observed_ns": 410,
        "errors": [],
        "identity": {"bdf": "0000:43:00.0", "library": str(LIBRARY_REAL), "library_sha256": LIBRARY_SHA,
                     "index": 0, "library_file_identity": [1, 2, 3, 4],
                     "version": {"major": 7, "minor": 3, "patch": 60200},
                     "counter_type": "RSMI_COARSE_GRAIN_GFX_ACTIVITY"},
    }
    # A large host/natural elapsed delta admits fixture counter deltas up to 1 per interval.
    at = (100, 20_000, 40_000, 60_000)
    trace["claim_release_observed_ns"] = at[-1] + 10
    trace["samples"] = [
        {"phase": PHASES[idx], "host_before_ns": sample, "host_after_ns": sample + 1,
         "counter_timestamp_ns": sample + 11, "counter": delta * idx}
        for idx, sample in enumerate(at)]
    trace.update(gpu_counter.reduce_trace(trace["samples"], []))
    files["gfx-counter.json"] = trace
    for name, content in files.items():
        (root / name).write_bytes(canonical(content))
    lock = {"pid": 12, "birth": 300, "device": 1, "inode": 2, "fd": "9", "path": str(GPU_LOCK),
            "raw": "lock:\t2: FLOCK  ADVISORY  WRITE 1 03:01:2 0 EOF"}
    witness = {"pid": 13, "birth": 305, "bound_loopback_inode": "7", "exe": str(SERVER),
               "argv": argv(), "kfd_vram_bytes": {"vram_fixture": 42}, "hip_mapping": {str(HIP): HIP_SHA}}
    report = {
        "schema": SCHEMA, "row_id": ROW, "run_id": root.name, "mode": "official", "status": "observed",
        "research_commit": RESEARCH, "build_commit": BUILD, "target": TARGET,
        "model_sha256": MODEL_SHA, "drafter_sha256": DRAFTER_SHA,
        "started_at": "2026-11-18T21:00:10+00:00", "ended_at": "2026-11-18T21:00:20+00:00",
        "grant": {"path": str(native.FLAGS / "grants" / (ROW + ".grant")),
                  "raw": "regions=mi210_0,184-187 start=2026-11-18T21:00Z end=2026-11-18T21:06Z holds=gpu-quiet",
                  "deadline_epoch": int(datetime.fromisoformat("2026-11-18T21:04:30+00:00").timestamp())},
        "cpus": list(range(184, 188)), "lock_begin": lock, "lock_end": lock.copy(),
        "server_before": {**witness, "at_ns": 150}, "server_after": {**witness, "at_ns": 55_000},
        "request_started_ns": 21_000, "request_ended_ns": 39_000,
        "server_cleanup": {"verified_gone": True, "verified_listener_released": True,
                           "verified_kfd_gone": True, "returncode": 0},
        "full_claim_coverage": None, "per_process_attribution": None, "binary_busy_time": None,
    }
    report["source_manifest"] = native.retain_sources(root)
    report["files"] = native.artifacts(root)
    reduction = counter_window(trace, report["request_started_ns"], report["request_ended_ns"])
    report["observed_window"] = reduction["observed_window"]
    report[METRIC] = reduction[METRIC]
    report["belief_measurements"] = [native_measurement(report, report["files"]["gfx-counter.json"], reduction)]
    return report


def project(path):
    return reader.project(reader.native_rows(path)[0])


def write(root, report):
    path = root / "observation.json"
    path.write_bytes(canonical({**report, "self_sha256": seal(report)}))
    return path


class Controls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / ("native-" + "f"*32)

    def test_grade_and_exact_context(self):
        path = write(self.root, fixture(self.root, delta=1))
        grade = reader.grade(project(path))
        self.assertEqual(grade[:2], ("Judged", "Located"))
        result = reader.canary(path, self.root.parent / "canary")
        self.assertEqual(result["visible"], {"exact_ak27b": True, "cpu": False, "other_weights": False, "same_name_other_digest": False})

    def test_installed_adapter(self):
        from adapters.autokernel_gfx_observation import native_rows, project as installed_project
        from ingest_sources import ingest
        from ledger import Ledger
        path = write(self.root, fixture(self.root, delta=1))
        result = installed_project(native_rows(path)[0])
        self.assertEqual(result.metric, COMPLETENESS)
        self.assertEqual(result.applicability["model_sha256"], MODEL_SHA)
        ledger = self.root.parent / "ingest.jsonl"
        ledger.touch()
        report = ingest(Ledger(ledger), "ak-gfx-observation", [path],
                        as_of="2026-11-18T23:00:00Z", dry_run=True)
        self.assertEqual((report["rows_projected"], report["frames_emitted"], report["refused"]),
                         (1, 3, []))

    def test_valid_zero(self):
        path = write(self.root, fixture(self.root, delta=0))
        self.assertEqual(project(path).extra[METRIC], 0)

    def test_refusals(self):
        report = fixture(self.root, delta=1)
        for field, value in (
                ("status", "UNKNOWN"), ("mode", "publisher-smoke"),
                ("belief_measurements", []), ("request_started_ns", 1),
                ("lock_end", {}), ("target", {"backend": "cpu"}),
                ("server_cleanup", {**report["server_cleanup"], "verified_kfd_gone": False}),
                ("source_manifest", {"locator": "../source-manifest.json", "sha256": "a"*64}),
                ("cpus", [188, 189, 190, 191])):
            with self.subTest(field=field), self.assertRaises(reader.ProjectionError):
                damaged = deepcopy(report)
                damaged[field] = value
                project(write(self.root, damaged))
        path = write(self.root, report)
        discovered = reader.native_rows(path)[0]
        discovered["sha256"] = "0" * 64
        with self.assertRaises(reader.ProjectionError):
            reader.project(discovered)
        (self.root / "gfx-counter.json").write_text("{}")
        with self.assertRaises(reader.ProjectionError):
            project(path)

    def test_resealed_unapproved_producer(self):
        report = fixture(self.root, delta=1)
        source = self.root / "source" / "native.py"
        source.write_bytes(source.read_bytes() + b"\n# unapproved producer change\n")
        manifest = self.root / "source-manifest.json"
        closure = json.loads(manifest.read_bytes())
        closure["files"]["native.py"] = digest(source)
        manifest.write_bytes(canonical(closure))
        report["source_manifest"]["sha256"] = digest(manifest)
        report["files"] = native.artifacts(self.root)
        reduction = counter_window(json.loads((self.root / "gfx-counter.json").read_bytes()),
                                   report["request_started_ns"], report["request_ended_ns"])
        report["belief_measurements"] = [native_measurement(
            report, report["files"]["gfx-counter.json"], reduction)]
        with self.assertRaises(reader.ProjectionError):
            project(write(self.root, report))

    def test_counter_native_refusals(self):
        record = fixture(self.root, delta=1)
        trace = json.loads((self.root / "gfx-counter.json").read_bytes())
        for label, change in (
                ("collector error", lambda t: t["errors"].append("recorded original failure")),
                ("counter reset", lambda t: t["samples"][2].update(counter=0)),
                ("clock mismatch", lambda t: t["samples"][2].update(counter_timestamp_ns=50_000)),
                ("missing phase", lambda t: t["samples"].pop(1))):
            with self.subTest(label=label), self.assertRaises(ValueError):
                modified = deepcopy(trace)
                change(modified)
                counter_window(modified, record["request_started_ns"], record["request_ended_ns"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
