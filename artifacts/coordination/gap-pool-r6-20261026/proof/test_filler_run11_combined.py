"""Private native-producer integration fixtures; no model, server or canonical writes."""
from __future__ import annotations
import atexit
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
from unittest import mock
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "scripts/coordination/filler_run11.sh"
# Explicit artifact roots retain receipts; unconfigured collection owns and cleans
# a portable temporary root. Each fixture separately cleans its own child dir.
_ART_ROOT = os.environ.get("EVL47_TEST_ARTIFACTS")
_ART_TEMP = tempfile.TemporaryDirectory(prefix="epyc-filler-run10-") if not _ART_ROOT else None
if _ART_TEMP is not None:
    atexit.register(_ART_TEMP.cleanup)
ART = Path(_ART_ROOT or _ART_TEMP.name).resolve()
_RECEIPT_ROOT = ART.parent if _ART_ROOT else ART
sys.path.insert(0, str(ROOT / "scripts/vidya"))
from adapters import calendar_overrun as adapter
import claim_tuple

ACTIVE_LAUNCHERS = []

def shutdown_captured_launchers(signum, frame):
    # The outer grant may end during a fixture. Each nested native launcher
    # owns its captured setsid stub group; give its existing TERM trap cleanup.
    for process in ACTIVE_LAUNCHERS:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    raise SystemExit(128 + signum)

signal.signal(signal.SIGTERM, shutdown_captured_launchers)
signal.signal(signal.SIGINT, shutdown_captured_launchers)

def utc(epoch):
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

class Producer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="fixture-", dir=ART)
        self.d = Path(self.tmp.name).resolve()
        self.addCleanup(self.tmp.cleanup)
        self.flags = self.d / "flags"
        self.grants = self.flags / "grants"
        self.state = self.d / "state"
        self.grants.mkdir(parents=True)
        self.state.mkdir()
        self.fillers = self.flags / "FILLERS.md"
        self.id = "synthetic-evl47"
        self.ended = self.grants / (self.id + ".ended")
        self.grant = self.grants / (self.id + ".grant")
        self.started = self.d / "payload-started"
        self.done = self.d / "payload-done"
        self.stop = self.d / "STOP"
        self.cpu = min(os.sched_getaffinity(0))
        self.env = os.environ.copy()
        self.env.update(FILLER_FLAGS_DIR=str(self.flags), FILLER_GRANTS_DIR=str(self.grants),
                        FILLER_STATE_DIR=str(self.state), FILLERS_MD=str(self.fillers),
                        FILLER_RL=str(self.d / "never-run-region-lock"), FILLER_POLL="0.1",
                        FILLER_GPU_LOCK=str(self.d / "gpu.lock"), TMPDIR=str(self.d))
        # No inherited path may escape into canonical mutable runtime state.
        for name in ("FILLER_FLAGS_DIR", "FILLER_GRANTS_DIR", "FILLER_STATE_DIR",
                     "FILLERS_MD", "FILLER_RL", "FILLER_GPU_LOCK"):
            self.assertTrue(Path(self.env[name]).resolve().is_relative_to(self.d), name)
        self.row("~2 min (fixture)")
        self.processes = []
        self.addCleanup(self.clean_processes)

    def clean_processes(self):
        for p, log in self.processes:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
                try:
                    p.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=5)
            self.assertIsNotNone(p.poll(), "captured launcher survived cleanup")
            log.close()

    def row(self, duration, owner="fixture-owner", duplicate=False):
        quarter="q"+str((self.cpu%96)//24)
        fields = [self.id, owner, "fixture pid=1", quarter, "0", "0", str(self.stop),
                  "ARMED", "block-correctness", duration, "0", "n", "y",
                  "none found (fixture, 2026-10-26)", "synthetic exact correctness",
                  "n/a (correctness fixture)", "cpu", "synthetic"]
        header="| filler-id | owner | launcher + pid | resources | min useful window | max private ram | stop file | status | class | duration | min window | ds41-class y/n | ready y/n | prior | decision | min_effect | substrate | notes |\n"
        row = "| " + " | ".join(fields) + " |\n"
        self.assertEqual(row.count(chr(10)), 1)
        self.fillers.write_text(header + row * (2 if duplicate else 1))

    def base_args(self):
        return ["--id", self.id, "--class", "cpu", "--cmd", "true", "--stop", str(self.stop),
                "--workdir", str(self.d), "--min-window", "0"]

    def window(self, seconds=600, expired=False):
        now = int(time.time())
        end = now - 1 if expired else now + seconds
        self.grant.write_text(f"regions={self.cpu} start={utc(now-2)} end={utc(end)}\n")
        self.assertTrue(self.grant.read_bytes().endswith(bytes([10])))
        self.assertEqual(len(self.grant.read_text().splitlines()), 1)

    def wait_for(self, predicate, timeout=30):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            if predicate():
                return
            time.sleep(.02)
        self.fail("fixture condition timed out")

    def launch(self, payload=None, repeat=False, complete=False):
        if payload is None:
            payload = f"touch {shlex.quote(str(self.started))}; touch {shlex.quote(str(self.done))}"
        env = dict(self.env, FILLER_STUB_CMD=payload)
        args = ["bash", str(CANDIDATE), *self.base_args()]
        if repeat:
            args.append("--repeat")
        if complete:
            args += ["--complete-cmd", f"test -e {shlex.quote(str(self.done))}"]
        log = open(self.d / f"launcher-{len(self.processes)}.log", "w")
        p = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT)
        ACTIVE_LAUNCHERS.append(p)
        self.processes.append((p, log))
        return p

    def tuple(self):
        (native,) = adapter.native_rows(self.ended)
        t = adapter.project(native)
        self.assertEqual(t.attestation_sha256, hashlib.sha256(self.ended.read_bytes()).hexdigest())
        self.assertEqual(t.metric_direction, "lower_better")
        self.assertEqual(claim_tuple.grade(t)[:2], ("Judged", "Located"))
        # Same parser as current calendar writer, preserving line-one compatibility.
        out = subprocess.check_output(["bash", "-c", 'head -1 "$1" | sed -n "s/^rc=\\([0-9]*\\).*/\\1/p"', "fixture", str(self.ended)], text=True)
        self.assertEqual(int(out.strip()), native["rc"])
        lines = self.ended.read_text().splitlines()
        keys = [line.split("=", 1)[0] for line in lines[1:]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertRegex(lines[0], r"^rc=\d+ time=\S+ reason=.*$")
        return native, t

    def function_harness(self, body):
        # Exercise actual candidate function definitions with native CLI parsing,
        # but stop before the inner/poller entrypoint: no scheduled runtime access.
        for helper in ("gap_runtime_v1.py","gap_policy.py","gap_serialization_v1.py","engine_state_v2_consolidation_PROPOSED.py","validate_fillers.py"):
            (self.d/helper).write_bytes((CANDIDATE.parent/helper).read_bytes())
        prefix = CANDIDATE.read_text().split("# ------------------------------------------------------------------ inner", 1)[0]
        harness = self.d / "function-harness.sh"
        harness.write_text(prefix + "\n" + body + "\n")
        self.assertTrue(harness.read_bytes().startswith(b"#!/bin/bash" + bytes([10])))
        subprocess.run(["bash", str(harness), *self.base_args()], env=self.env, cwd=self.d, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=20)

    def test_duration_conversion_and_finite_overflow_refusal(self):
        for duration, expected in [("1 s", 1), ("~1.5 min (explanation)", 90), ("2 h", 7200),
                                   ("9" * 400 + " h", None), ("0 min", None), ("2-3 h", None),
                                   ("2 h remaining", None), ("1 h + 2 min", None), ("-", None)]:
            with self.subTest(duration=duration[:60]):
                self.row(duration)
                self.function_harness('snapshot_overrun fixture; OV_STARTED=$(ts); write_ended 0 fixture')
                if expected is None:
                    self.assertNotIn("estimated_wall_s=", self.ended.read_text())
                    self.assertEqual(adapter.native_rows(self.ended), ())
                else:
                    n, _ = self.tuple()
                    self.assertEqual(n["estimated_s"], expected)
        self.row("1 min", duplicate=True)
        self.function_harness('snapshot_overrun fixture; OV_STARTED=$(ts); write_ended 0 fixture')
        self.assertEqual(adapter.native_rows(self.ended), ())

    def test_write_consumes_metadata_before_later_trap_unstarted_grant(self):
        self.function_harness('''snapshot_overrun fixture
OV_STARTED=$(ts)
write_ended 0 first
cp "$ENDED" "$ENDED.first.ended"
# A subsequent grant exists but has not entered run_one; TERM invokes write_ended.
printf 'regions=fixture start=never end=never\\n' > "$GRANT"
trap 'write_ended 143 launcher-signalled; exit 0' TERM
kill -TERM $$
''')
        self.assertEqual(len(adapter.native_rows(Path(str(self.ended) + ".first.ended"))), 1)
        self.assertEqual(adapter.native_rows(self.ended), ())
        self.assertNotIn("estimated_wall_s=", self.ended.read_text())

    def test_complete_end_to_end_and_start_snapshot_survives_row_change(self):
        self.window()
        payload = f"touch {shlex.quote(str(self.started))}; sleep 1; touch {shlex.quote(str(self.done))}"
        p = self.launch(payload, complete=True)
        self.wait_for(self.started.exists)
        self.row("20 h", owner="changed-owner")
        self.assertEqual(p.wait(timeout=20), 0)
        n, _ = self.tuple()
        self.assertEqual((n["estimated_s"], n["owner"], n["step"]), (120, "fixture-owner", "job-run"))
        self.assertEqual(n["reason"], "complete")
        ledger = self.d / "private-ledger.jsonl"
        report = json.loads(subprocess.check_output(
            [sys.executable, str(ROOT / "scripts/vidya/cli.py"), "--json", "--ledger", str(ledger),
             "ingest", "calendar-overrun", "--path", str(self.ended), "--as-of", utc(int(time.time()))],
            cwd=self.d, text=True, timeout=30))
        self.assertEqual(report["rows_projected"], 1)
        self.assertEqual(report["units_projected"], 1)
        self.assertEqual(report["refused"], [])
        self.assertTrue(ledger.is_file())

    def test_repeat_then_unstarted_expired_attempt_does_not_reuse_snapshot(self):
        self.window()
        p = self.launch(repeat=True)
        self.wait_for(self.ended.exists)
        self.tuple()
        self.row("-")
        self.window(expired=True)
        self.wait_for(lambda: "grant-expired-unrun" in self.ended.read_text())
        self.assertEqual(adapter.native_rows(self.ended), ())
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=25)

    def test_prestart_complete_and_expired_are_legacy(self):
        self.done.touch()
        p = self.launch(complete=True)
        self.assertEqual(p.wait(timeout=10), 0)
        self.assertEqual(adapter.native_rows(self.ended), ())
        self.done.unlink()
        # Fresh launcher can test expiry despite prior complete marker.
        (self.grants / (self.id + ".complete")).unlink()
        self.window(expired=True)
        p = self.launch()
        self.wait_for(self.ended.exists)
        self.wait_for(lambda: "grant-expired-unrun" in self.ended.read_text())
        self.assertEqual(adapter.native_rows(self.ended), ())
        p.send_signal(signal.SIGTERM)
        p.wait(timeout=25)

    def test_hard_end_and_launcher_term_are_censored(self):
        for kind in ("hard-end", "term"):
            with self.subTest(kind=kind):
                self.started.unlink(missing_ok=True)
                self.ended.unlink(missing_ok=True)
                self.window(seconds=2 if kind == "hard-end" else 600)
                payload = f"touch {shlex.quote(str(self.started))}; sleep 60"
                p = self.launch(payload)
                self.wait_for(self.started.exists)
                if kind == "term":
                    p.send_signal(signal.SIGTERM)
                p.wait(timeout=30)
                n, t = self.tuple()
                self.assertEqual(n["rc"], 124 if kind == "hard-end" else 143)
                self.assertTrue(t.extra["censored"])

    def test_atomic_rename_never_exposes_partial_appended_record(self):
        # Same native seven-field semantics; new common-lease API uses os.replace.
        sys.path.insert(0,str(CANDIDATE.parent))
        import engine_state_v2_consolidation_PROPOSED as state_api
        self.ended.write_text("previous-final\n")
        real_replace=os.replace
        calls=[]
        def witness(source,target):
            self.assertEqual(self.ended.read_text(),"previous-final\n")
            pending=Path(source).read_text()
            self.assertEqual(len(pending.splitlines()),7)
            self.assertIn("estimated_wall_s=120\n",pending)
            self.assertIn("step=job-run\n",pending)
            self.assertEqual(Path(target),self.ended)
            calls.append((str(source),str(target)))
            return real_replace(source,target)
        with mock.patch.object(state_api.serial.os,"replace",side_effect=witness):
            state_api.mutate(self.flags,self.id,0,"fixture",overrun=(utc(int(time.time())),"fixture-owner","120","fixture"))
        self.assertEqual(len(calls),1)
        self.tuple()
        self.assertFalse(Path(calls[0][0]).exists())

DECLARED_FIXTURES = (
    "test_atomic_rename_never_exposes_partial_appended_record",
    "test_complete_end_to_end_and_start_snapshot_survives_row_change",
    "test_duration_conversion_and_finite_overflow_refusal",
    "test_hard_end_and_launcher_term_are_censored",
    "test_prestart_complete_and_expired_are_legacy",
    "test_repeat_then_unstarted_expired_attempt_does_not_reuse_snapshot",
    "test_write_consumes_metadata_before_later_trap_unstarted_grant",
)

class ExactResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_ids = []

    def startTest(self, test):
        self.run_ids.append(test.id().rsplit(".", 1)[-1])
        super().startTest(test)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Producer)
    collected = [test.id().rsplit(".", 1)[-1] for test in suite]
    if collected != list(DECLARED_FIXTURES) or not collected or len(set(collected)) != len(collected):
        raise SystemExit("producer collection does not equal declared fixture IDs")
    result = unittest.TextTestRunner(verbosity=2, resultclass=ExactResult).run(suite)
    receipt = {"declared": list(DECLARED_FIXTURES), "collected": collected,
               "run": result.run_ids, "tests_run": result.testsRun,
               "skipped": len(result.skipped), "failures": len(result.failures), "errors": len(result.errors),
               "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses)}
    (_RECEIPT_ROOT / "producer-fixtures.json").write_text(json.dumps(receipt, indent=2) + chr(10))
    valid = (result.wasSuccessful() and result.run_ids == collected and result.testsRun == len(collected)
             and not result.skipped and not result.expectedFailures and not result.unexpectedSuccesses)
    raise SystemExit(0 if valid else 1)
