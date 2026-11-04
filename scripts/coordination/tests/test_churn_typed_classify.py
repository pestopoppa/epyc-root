#!/usr/bin/env python3
"""JEV-3 replace: typed judgment decides; unavailable -> label None (never a guess) and only then the regex fallback;
replay over a temp dryrun tree prints answered/unavailable counts and writes nothing. Hermetic: typed_decisions is mocked."""
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "churn"))
import typed_classify as ts  # noqa: E402

FAIL_RC = {"at": "2026-11-01T22:43:16Z", "elapsed_s": 5, "id": "r1", "first_unit_at": None,
           "ended": "rc=3 time=2026-11-01T22:43:14Z reason=job-rc-3:exited",
           "reason": "job ended (rc=3 ...) before writing a unit to /nonexistent/x/measured.jsonl (jsonl)",
           "fix_task": "fix", "launcher_out_tail": ["REFUSED: regions q0-q3 are not all held"]}
FAIL_MARKER = dict(FAIL_RC, id="r2", reason="job ended (rc=? (no ended record)) before writing a unit to /nonexistent/y/COMPLETE.json (json)")
FAIL_DERIV = dict(FAIL_RC, id="r3", reason="spec.lane missing")
FAIL_STOP = dict(FAIL_RC, id="r4", reason="first unit written but the job did not stop within 180s of the stop file")


def mocked_answers(values):
    def _fake(catalogue, state):
        return {q["id"]: {"value": values[q["id"]], "probabilities": {values[q["id"]]: 0.9}, "confidence": 0.8, "mode": "native"}
                for q in catalogue}
    return _fake


class HeuristicTests(unittest.TestCase):
    def test_fail_classes_match_repair(self):
        self.assertEqual(ts.heuristic_fail(FAIL_RC)[0], ts.FailClass.unknown)
        self.assertEqual(ts.heuristic_fail(FAIL_MARKER)[0], ts.FailClass.marker_result_path)
        self.assertEqual(ts.heuristic_fail(FAIL_DERIV)[0], ts.FailClass.derivable_field_missing)
        self.assertEqual(ts.heuristic_fail(FAIL_STOP)[0], ts.FailClass.unknown)

    def test_fail_result_dir_path_when_results_written_during(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "results.jsonl")
            open(p, "w").write("{}\n")
            rec = dict(FAIL_RC, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), reason=f"job ended (rc=1) before writing a unit to {d}/other.jsonl (jsonl)")
            self.assertEqual(ts.heuristic_fail(rec)[0], ts.FailClass.result_dir_path)

    def test_work_state_branches(self):
        self.assertEqual(ts.heuristic_work_state("- [blocked] r rank=1 **t**\n", 0)[:2], (ts.WorkState.continue_, ts.StopReason.has_fix_tasks))
        self.assertEqual(ts.heuristic_work_state("- X L12 [cpu] run it\n", 0)[1], ts.StopReason.has_own_inference_tasks)
        self.assertEqual(ts.heuristic_work_state("## Non-inference\n- [ ] small\n", 0)[1], ts.StopReason.has_small_tasks)
        self.assertEqual(ts.heuristic_work_state("- [running] r rank=1 **task**\n", 3)[:2], (ts.WorkState.pause, ts.StopReason.waiting_on_own_rows))
        self.assertEqual(ts.heuristic_work_state("", 2)[:2], (ts.WorkState.continue_, ts.StopReason.backlog_empty))
        self.assertEqual(ts.heuristic_work_state("", 0)[:2], (ts.WorkState.done, ts.StopReason.no_open_boxes))


class TypedTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(ts, "_require_listening", return_value=None)
        p.start()
        self.addCleanup(p.stop)

    def test_port_closed_is_unavailable(self):
        mock.patch.stopall()
        with mock.patch.object(ts, "PORT", 1):
            r = ts.decide_fail(FAIL_MARKER)
        self.assertEqual((r["source"], r["label"]), ("regex-fallback", ts.FailClass.marker_result_path))
        self.assertIn("not listening", r["unavailable"])

    def test_decide_typed_wins_including_unknown(self):
        with mock.patch.object(ts, "_typed_answers", mocked_answers({"fail_class": "unknown"})):
            r = ts.decide_fail(FAIL_MARKER)
        self.assertEqual((r["source"], r["label"], r["unavailable"]), ("typed", ts.FailClass.unknown, None))
        with mock.patch.object(ts, "_typed_answers", mocked_answers({"work_state": "done", "stop_reason": "no_open_boxes"})):
            w = ts.decide_work_state("- [blocked] r rank=1 **t**\n", 1)
        self.assertEqual((w["source"], w["label"]), ("typed", ts.WorkState.done))

    def test_decide_falls_back_only_when_unavailable(self):
        with mock.patch.object(ts, "_typed_answers", side_effect=RuntimeError("down")):
            w = ts.decide_work_state("- [blocked] r rank=1 **t**\n", 1)
        self.assertEqual((w["source"], w["label"], w["stop_reason"]), ("regex-fallback", ts.WorkState.continue_, ts.StopReason.has_fix_tasks))
        self.assertIn("down", w["unavailable"])

    def test_unavailable_import_gives_none_label(self):
        with mock.patch.object(ts, "_typed_importable", return_value=True), \
                mock.patch.object(ts, "_load_typed", side_effect=ImportError("No module named 'src'")):
            r = ts.classify_fail(FAIL_RC)
        self.assertEqual(r["source"], "unavailable")
        self.assertIsNone(r["label"])
        self.assertIn("No module named 'src'", r["detail"])
        with mock.patch.object(ts, "_typed_importable", return_value=True), mock.patch.object(ts, "_load_typed", side_effect=ImportError("x")):
            w = ts.classify_work_state("- [blocked] r rank=1 **t**\n", 1)
        self.assertEqual((w["source"], w["label"], w["stop_reason"]), ("unavailable", None, None))

    def test_unavailable_with_bogus_orch_root(self):
        with mock.patch.object(ts, "ORCH_ROOT", "/nonexistent/orch"), mock.patch.object(ts, "_PRIMITIVES", None), \
                mock.patch.dict(os.environ, {"TYPED_CLASSIFY_PYTHON": "/nonexistent/py"}), \
                mock.patch.dict(sys.modules, {k: None for k in ("src", "src.typed_decisions")}):
            r = ts.classify_fail(FAIL_RC)
        self.assertEqual(r["source"], "unavailable")
        self.assertIsNone(r["label"])

    def test_no_worker_interpreter_is_unavailable(self):
        with mock.patch.object(ts, "_typed_importable", return_value=False), \
                mock.patch.dict(os.environ, {"TYPED_CLASSIFY_PYTHON": "/nonexistent/venv/python3"}):
            r = ts.classify_fail(FAIL_RC)
        self.assertEqual((r["source"], r["label"]), ("unavailable", None))
        self.assertIn("no separate interpreter", r["detail"])

    def test_worker_subprocess_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            shim = os.path.join(d, "py")
            with open(shim, "w") as f:  # fake venv interpreter: answers every question with its first option
                f.write("#!/bin/sh\nexec /usr/bin/python3 -c 'import json,sys; r=json.load(sys.stdin); "
                        "print(json.dumps({\"ok\": True, \"answers\": {q[\"id\"]: {\"value\": q[\"options\"][0], "
                        "\"probabilities\": {}, \"confidence\": None} for q in r[\"catalogue\"]}}))'\n")
            os.chmod(shim, 0o755)
            with mock.patch.object(ts, "_typed_importable", return_value=False), mock.patch.dict(os.environ, {"TYPED_CLASSIFY_PYTHON": shim}):
                r = ts.classify_fail(FAIL_RC)
        self.assertEqual((r["source"], r["label"]), ("typed", ts.FailClass.marker_result_path))

    def test_runtime_failure_is_unavailable(self):
        with mock.patch.object(ts, "_typed_answers", side_effect=RuntimeError("transport_error: connection refused")):
            r = ts.classify_fail(FAIL_RC)
        self.assertEqual((r["source"], r["label"]), ("unavailable", None))
        self.assertIn("connection refused", r["detail"])

    def test_mocked_typed_maps_to_enum(self):
        with mock.patch.object(ts, "_typed_answers", mocked_answers({"fail_class": "job_rc"})):
            r = ts.classify_fail(FAIL_RC)
        self.assertEqual((r["source"], r["label"]), ("typed", ts.FailClass.job_rc))
        self.assertIn("probabilities", r["detail"])
        with mock.patch.object(ts, "_typed_answers", mocked_answers({"work_state": "pause", "stop_reason": "waiting_on_own_rows"})):
            w = ts.classify_work_state("- [running] r rank=1 **t**\n", 2)
        self.assertEqual((w["label"], w["stop_reason"], w["source"]), (ts.WorkState.pause, ts.StopReason.waiting_on_own_rows, "typed"))

    def test_value_outside_enum_is_unavailable_not_guessed(self):
        with mock.patch.object(ts, "_typed_answers", mocked_answers({"fail_class": "something_else"})):
            r = ts.classify_fail(FAIL_RC)
        self.assertEqual((r["source"], r["label"]), ("unavailable", None))
        self.assertIn("not in FailClass", r["detail"])


class ReplayTests(unittest.TestCase):
    def _tree(self, d):
        for rec in (FAIL_RC, FAIL_MARKER, FAIL_DERIV):
            rd = os.path.join(d, "dryrun", rec["id"])
            os.makedirs(rd)
            json.dump(rec, open(os.path.join(rd, "FAIL-1.json"), "w"))
        os.makedirs(os.path.join(d, "dryrun", "nofail"))

    def _snapshot(self, d):
        return sorted((os.path.join(r, f), os.path.getmtime(os.path.join(r, f))) for r, _, fs in os.walk(d) for f in fs)

    def test_replay_counts_and_no_writes(self):
        with tempfile.TemporaryDirectory() as d:
            self._tree(d)
            before = self._snapshot(d)
            answers = mocked_answers({"fail_class": "marker_result_path"})
            with mock.patch.object(ts, "_typed_answers", answers):
                rows = ts.replay(d)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = ts.main(["replay", "--flags", d])
            self.assertEqual(rc, 0)
            self.assertEqual(len(rows), 3)
            self.assertEqual([r["source"] for r in rows], ["typed"] * 3)
            self.assertIn("records=3 typed_answered=3 typed_unavailable=0", out.getvalue())
            self.assertEqual(self._snapshot(d), before)
            self.assertEqual(sorted(os.listdir(d)), ["dryrun"])

    def test_replay_unavailable_counts(self):
        with tempfile.TemporaryDirectory() as d:
            self._tree(d)
            with mock.patch.object(ts, "_require_listening", return_value=None), \
                    mock.patch.object(ts, "_typed_importable", return_value=True), mock.patch.object(ts, "_load_typed", side_effect=ImportError("nope")):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    ts.main(["replay", "--flags", d])
            self.assertIn("records=3 typed_answered=0 typed_unavailable=3", out.getvalue())
            self.assertIn("ImportError: nope", out.getvalue())

    def test_fail_cli(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "FAIL-1.json")
            json.dump(FAIL_MARKER, open(p, "w"))
            with mock.patch.object(ts, "_typed_answers", mocked_answers({"fail_class": "job_rc"})):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    ts.main(["fail", p])
            j = json.loads(out.getvalue())
            self.assertEqual((j["source"], j["label"]), ("typed", "job_rc"))


if __name__ == "__main__":
    unittest.main()
