#!/usr/bin/env python3
"""Operator 2026-11-03 (session review §3.1): a smoke PASSes only on the job's FIRST REAL PROGRESS within first_progress_s.
"A JSON appeared" is not progress: the records that passed on 2026-11-03 (qualification_only / measurement:false) and
whose real runs died in seconds must FAIL here, with cause + fix in one line."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
from test_rowflow import Fixture  # noqa: E402

# the 2026-11-03 smoke records whose rows PASSed and then died in 3-12 s (copied from compute-flags/dryrun/*/native-attempts)
YARN = {"qualification_only": True, "first_request_ok": True, "result_writer_ok": True, "pid": 1865475, "image": "E1",
        "arm": "A0", "level": "low", "at": 1793723360.332529}
INF22 = {"schema": "epyc.m4.cpu.recipe.qualification.v1", "qualification_only": True, "measurement": False, "spawn_path_exercised": True}


class RecordVerdictTests(unittest.TestCase):
    def test_real_2026_11_03_placeholders_are_not_progress(self):
        self.assertEqual(rf.record_verdict(YARN), (False, "placeholder (qualification_only: true)"))
        self.assertFalse(rf.record_verdict(INF22)[0])
        self.assertFalse(rf.record_verdict({"measurement": False, "tps": 3.0})[0], "an explicit marker always wins")
        self.assertFalse(rf.record_verdict({"tps": 3.0, "qualification_only": True}, unit_key="tps")[0])

    def test_bookkeeping_only_and_empty_records_are_not_progress(self):
        for rec in ({}, {"status": "started"}, {"id": "x", "ts": 1793723360, "pid": 5, "rc": 0, "started_at": 1.0},
                    {"ok": True, "why": []}, {"tps": None}, {"value": float("nan")}, {"flag": True}, "started", None):
            self.assertFalse(rf.record_verdict(rec)[0], rec)

    def test_measured_records_are_progress(self):
        for rec in ({"item": 1, "score": 1}, {"tps": 12.3}, {"metrics": {"ppl": 6.1}}, {"lat_ms": [1, 2]}, 7):
            self.assertTrue(rf.record_verdict(rec)[0], rec)
        self.assertFalse(rf.record_verdict({"a": {"b": {"c": 1}}})[0], "depth > 2 is not a measurement field")

    def test_unit_key(self):
        self.assertTrue(rf.record_verdict({"answer": "B"}, unit_key="answer")[0])
        self.assertTrue(rf.record_verdict({"r": {"answer": "B"}}, unit_key="r.answer")[0])
        self.assertFalse(rf.record_verdict({"answer": ""}, unit_key="answer")[0])
        self.assertFalse(rf.record_verdict({"tps": 1.0}, unit_key="answer")[0])

    def test_table_and_text_formats(self, tmp=None):
        fx = Fixture()
        try:
            p = os.path.join(fx.root, "r.csv")
            Path(p).write_text("id,ts,status\n")
            self.assertEqual(rf.result_records(p, "csv"), [])
            Path(p).write_text("id,ts,status\nx,17937,ok\n")
            self.assertFalse(rf.result_records(p, "csv")[0][1], "bookkeeping columns only")
            Path(p).write_text("id,tps\nx,12.5\n")
            self.assertTrue(rf.result_records(p, "csv")[0][1])
            t = os.path.join(fx.root, "r.txt")
            Path(t).write_text("starting\nRESULT tps=3\n")
            self.assertEqual([r[1] for r in rf.result_records(t, "text-lines", unit_key=r"^RESULT ")], [False, True])
            m = os.path.join(fx.root, "r.md")
            Path(m).write_text("| id | tps |\n|---|---|\n| a | 3.5 |\n")
            self.assertEqual([r[1] for r in rf.result_records(m, "markdown-table")], [True])
            dd = os.path.join(fx.root, "outdir")
            os.makedirs(dd)
            Path(dd, "a.json").write_text(json.dumps(YARN))
            Path(dd, "b.log").write_text("")
            self.assertEqual([r[1] for r in rf.result_records(dd, "json")], [False, False])
            Path(dd, "c.json").write_text('{"tps": 4}')
            self.assertIn(True, [r[1] for r in rf.result_records(dd, "json")])
        finally:
            fx.cleanup()


class Done:
    pid = 424242
    def poll(self): return 0
    def wait(self, timeout=None): return 0


class DryrunProgressTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.cleanup()

    def _run(self, rid, write, **spec_kw):
        """Publish rid, then a dry run whose 'job' (mocked Popen) runs write(env, result_path) and ends with `rc` in ended."""
        fx = self.fx
        d = fx.job(rid)
        spec = fx.spec(rid, d, **spec_kw)
        if "dryrun_timeout_s" not in spec_kw:
            spec.pop("dryrun_timeout_s")  # the fixture's legacy alias; these tests exercise the 300 s default
        row = rf.publish(spec, fx.flags)

        real_popen = rf.subprocess.Popen

        def launch(argv, **kw):
            if argv[:2] == ["bash", "-c"]:  # the smoke_predicate probe runs for real; only the launcher is mocked
                return real_popen(argv, **kw)
            env = kw["env"]
            rc = write(env, row["result_path"])
            Path(env["FILLER_DRYRUN_DIR"], "ended").write_text(f"rc={rc} time=x reason=exited\n")
            return Done()
        with mock.patch.object(rf, "status", return_value={"state": "needs-dryrun"}), \
                mock.patch.object(rf, "row_orphans", return_value=[]), \
                mock.patch.object(rf.subprocess, "Popen", side_effect=launch) as P, \
                mock.patch.object(rf.time, "sleep", return_value=None):
            v, msg = rf.dryrun_run(fx.flags, rid, "0-3", True, smoke_s=row["first_progress_s"])
        return v, msg, P, row

    def test_placeholder_then_clean_exit_fails_in_one_line(self):
        def w(env, rp):
            Path(rp).write_text(json.dumps(INF22) + "\n")
            return 75
        v, msg, _, row = self._run("t-fp-placeholder", w)
        self.assertEqual(v, "FAIL")
        self.assertNotIn("\n", msg)
        self.assertIn("no first progress within 300 s", msg)
        self.assertIn("placeholder (qualification_only: true)", msg)
        self.assertIn("fix: ", msg)
        self.assertNotIn("WS58_REGIONS", msg, "the one-quarter claim hint is not this failure's cause")
        self.assertIn("no unit in " + row["result_path"] + " (", msg, "repair/typed_classify parse this phrase")
        self.assertEqual(rf.load_json(rf.fail_paths(self.fx.flags, "t-fp-placeholder")[-1])["progress_rule"], "record")

    def test_rc0_with_no_record_fails(self):
        v, msg, _, _ = self._run("t-fp-nothing", lambda env, rp: 0, first_progress_s=120)
        self.assertEqual(v, "FAIL")
        self.assertIn("no first progress within 120 s: job ended rc=0", msg)

    def test_preexisting_records_are_not_this_runs_progress(self):
        fx = self.fx
        d = fx.job("t-fp-old")
        Path(d, "out", "results.jsonl").write_text('{"tps": 9}\n')
        v, msg, _, _ = self._run("t-fp-old", lambda env, rp: 0)
        self.assertEqual(v, "FAIL", msg)

    def test_real_record_passes(self):
        def w(env, rp):
            with open(rp, "a") as f:
                f.write('{"status": "started"}\n{"item": 1, "tps": 11.5}\n')
            return 75
        v, msg, _, row = self._run("t-fp-real", w)
        self.assertEqual(v, "PASS", msg)
        self.assertTrue(msg.startswith("first progress: new record in " + row["result_path"]), msg)
        p = rf.load_json(rf.pass_path(self.fx.flags, "t-fp-real"))
        self.assertEqual((p["progress_rule"], p["first_progress_s"]), ("record", 300))
        self.assertTrue(p["first_unit_at"])

    def test_unit_key_record(self):
        def w(env, rp):
            Path(rp).write_text('{"answer": "B", "case": "c1"}\n')
            return 0
        self.assertEqual(self._run("t-fp-key", w, unit_key="answer")[0], "PASS")
        self.assertEqual(self._run("t-fp-key2", w)[0], "FAIL", "no numeric field and no unit_key")

    def test_smoke_predicate_must_flip_during_the_run(self):
        def w(env, rp):
            Path(env["FILLER_DRYRUN_DIR"], "step1.done").write_text(env["FILLER_SMOKE_T0"])
            return 75
        pred = 'test -s "$FILLER_DRYRUN_DIR/step1.done"'
        v, msg, _, _ = self._run("t-fp-pred", w, smoke_predicate=pred)
        self.assertEqual(v, "PASS", msg)
        self.assertIn("smoke_predicate exited 0", msg)
        # a predicate that is ALREADY true cannot see the run: FAIL before anything is launched
        v, msg, P, _ = self._run("t-fp-pred-stale", w, smoke_predicate="true")
        self.assertEqual(v, "FAIL")
        self.assertIn("already exits 0 BEFORE the launch", msg)
        self.assertNotIn("\n", msg)
        self.assertEqual([c for c in P.call_args_list if c.args[0][:2] != ["bash", "-c"]], [], "the launcher never started")

    def test_predicate_never_true_fails(self):
        v, msg, _, _ = self._run("t-fp-pred-no", lambda env, rp: 0, smoke_predicate="false")
        self.assertEqual(v, "FAIL")
        self.assertIn("smoke_predicate `false` never exited 0", msg)


class PublishFieldTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.cleanup()

    def test_first_progress_s_default_alias_and_spec(self):
        fx = self.fx
        d = fx.job("t-fps")
        spec = fx.spec("t-fps", d)
        spec.pop("dryrun_timeout_s")
        self.assertEqual(rf.publish(spec, fx.flags)["first_progress_s"], 300)
        self.assertEqual(rf.publish(fx.spec("t-fps", d), fx.flags)["first_progress_s"], 60, "dryrun_timeout_s is an alias")
        row = rf.publish(fx.spec("t-fps", d, first_progress_s=900, smoke_predicate="test -s x", unit_key="tps"), fx.flags)
        self.assertEqual((row["first_progress_s"], row["smoke_predicate"], row["unit_key"]), (900, "test -s x", "tps"))
        for bad in ({"first_progress_s": "soon"}, {"smoke_predicate": ""}, {"unit_key": 3},
                    {"unit_key": "(", "result_format": "text-lines"}):
            with self.assertRaises(rf.Refused):
                rf.publish(fx.spec("t-fps", d, **bad), fx.flags)

    def test_publish_smoked_uses_the_rows_first_progress_s(self):
        seen = {}
        flags = self.fx.flags

        def pub(spec, flags, source=None):
            rf.atomic_json(rf.ready_path(flags, "r1"), {"id": "r1"})
            return {"id": "r1", "first_progress_s": 900}

        def dry(flags, rid, regions, one_quarter=False, smoke_s=None):
            seen["smoke_s"] = smoke_s
            return "PASS", "ok"
        with mock.patch.object(pr, "smoke_regions", return_value="0-3"), mock.patch.object(rf, "publish", pub), \
                mock.patch.object(rf, "dryrun_run", dry):
            pr.publish_smoked({"lane": "cpu"}, flags, "t")
        self.assertEqual(seen["smoke_s"], 900)


if __name__ == "__main__":
    unittest.main()
