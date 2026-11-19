#!/usr/bin/env python3
"""Pipeline audit 2026-11-10, workstream B (operator 2026-11-10 scope "Publish-time checks").

#2 ONE RUNNABLE PREDICATE: rowflow.runnable(status) is the only candidate test; a parked/failed/stopped row is never
   re-planned and never "fits but was not placed". Replayed from the akx-lb3-2-cv6-pair-20261107-r2 keeper log
   (fixtures/cv6-r2-keeper-20261108.log): refused rc=13 56 times, PARKed, then RE-PLAN 37 / IDLE-VIOLATION 36 more.
   Its cause, a launcher --claim-cpus wider than the contract's grant, is refused at publish (CLAIM-WIDER-THAN-CONTRACT).
#4 PUBLISH PREFLIGHT (publish_row.preflight): smoke_predicate already true, --complete-cmd already true, --precond-cmd
   false, prose decision_rule without verdict_by agent are refused; env cleaning without FILLER_ID / start_new_session
   in the scanned job files is warned. Every command runs bounded, in --workdir, with the smoke env minus FILLER_SMOKE*.
"""
import contextlib
import io
import json
import os
import re
import sys
import textwrap
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _TESTS)
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
from test_rowflow import Fixture as JobFixture, write  # noqa: E402
from test_rowflow_arming_park import Fixture as TickFixture  # noqa: E402

CV6 = "akx-lb3-2-cv6-pair-20261107-r2"
CV6_LOG = os.path.join(_TESTS, "fixtures", "cv6-r2-keeper-20261108.log")


def cv6_log():
    return open(CV6_LOG).read().splitlines()


def cv6_refusal():
    """The admission gate's rc=13 line, verbatim from the keeper log."""
    ln = next(x for x in cv6_log() if f" SKIP {CV6}: " in x)
    return re.search(r"(refuse rc=13: .*?) \(\d+ consecutive", ln).group(1)


# ---------------------------------------------------------------- #2 runnable()
class RunnablePredicate(unittest.TestCase):
    def test_states(self):
        self.assertTrue(rf.runnable({"state": "grantable"}))
        self.assertTrue(rf.runnable({"state": "armed", "arm_fails": rf.MAX_FAILS - 1}))
        for st in ("parked", "failed", "stopped", "done", "running", "dryrun-running", "stale", "needs-dryrun", "unknown"):
            self.assertFalse(rf.runnable({"state": st}), st)
        self.assertFalse(rf.runnable({"state": "armed", "arm_fails": rf.MAX_FAILS}))
        self.assertFalse(rf.runnable({"state": "grantable", "precond_parked": True}))
        self.assertFalse(rf.runnable(None))


class Cv6ParkedNeverReplanned(TickFixture):
    """Replay of the cv6 incident: a live poller (armed, engine ok) whose admission is refused rc=13 every tick."""

    def setUp(self):
        super().setUp()
        self.saved.update({k: getattr(rf, k) for k in ("armed_engine_ok", "stop_row_poller")})
        rf.armed_engine_ok = lambda pid, rid, proc="/proc": True       # the incident's poller ran a real engine
        rf.stop_row_poller = lambda *a, **k: "survived"                 # ... and survived the park (never kill pytest)
        refusal = cv6_refusal()
        rf.admit = lambda flags, rid, d, pid, regions, window_s: (False, refusal) if rid == CV6 else (True, "ok")
        self.row(CV6, 5, [frozenset({"q3", rf.GPU})], "quarter", regions="72-95")

    def count(self, kind, since=0):
        return sum(1 for ln in self.lines[since:] if ln.startswith(kind) and CV6 in ln)

    def test_fixture_is_the_incident(self):
        log = cv6_log()
        self.assertTrue(any(f"PARK {CV6}" in x for x in log))
        after = [x for x in log if x[:20] > "2026-11-08T15:59:25Z"]
        self.assertTrue(any("RE-PLAN" in x for x in after) and any("IDLE-VIOLATION" in x for x in after),
                        "the log shows re-plans and idle violations after the PARK")
        self.assertIn("missing q1+q2+q3", "\n".join(log))

    def test_parks_at_max_fails_then_never_replanned_nor_idle_violation(self):
        for _ in range(rf.MAX_FAILS - 1):
            self.tick()
        park_tick = len(self.lines)
        self.tick()   # the MAX_FAILS-th refusal parks it (15:59:25Z in the fixture)
        st = rf.status(self.flags, CV6)
        self.assertEqual(st["state"], "parked", st)
        self.assertFalse(rf.runnable(st))
        self.assertEqual(self.count("SKIP"), rf.MAX_FAILS)
        # the park tick itself reports no "fits but was not placed" for the row that just parked
        self.assertEqual(self.count("IDLE-VIOLATION", park_tick), 0, self.lines[park_tick:])
        after = len(self.lines)
        for _ in range(4):   # the incident's next ticks: SKIP + RE-PLAN + IDLE-VIOLATION (ALERT) each
            self.tick()
        tail = self.lines[after:]
        self.assertEqual(self.count("SKIP", after), 0, "a parked row is never armed/admitted again")
        self.assertEqual(self.count("RE-PLAN", after), 0)
        self.assertFalse(any("IDLE-VIOLATION" in ln for ln in tail), tail)
        self.assertTrue(all("cands=0" in ln for ln in tail if ln.startswith("SNAPSHOT")), "never a planner candidate")
        self.assertEqual(len(rf.arm_fails_since_pass(self.flags, CV6)), rf.MAX_FAILS, "no FAIL record after the park")

    def test_unpark_makes_it_runnable_again(self):
        for _ in range(rf.MAX_FAILS):
            self.tick()
        rf.unpark(self.flags, CV6, by="test")
        self.assertTrue(rf.runnable(rf.status(self.flags, CV6)))


# ---------------------------------------------------------------- #2 publish refusal: claim wider than the contract
class ClaimWiderThanContract(unittest.TestCase):
    def setUp(self):
        self.fx = JobFixture()

    def tearDown(self):
        self.fx.cleanup()

    def launcher(self, rid, claim_flags):
        d = self.fx.job(rid)
        write(os.path.join(d, "launch.sh"), textwrap.dedent(f"""\
            #!/bin/bash
            set -euo pipefail
            D={d}
            ENGINE={self.fx.engine}
            exec bash "$ENGINE" --id {rid} --class cpu {claim_flags} --min-window 300 --stop "$D/STOP" \\
              --complete-cmd "test -e $D/out/COMPLETE" --workdir "$D" --cmd "bash '$D/job.sh' --threads 24"
            """), 0o755)
        return d

    def test_cv6_launcher_on_a_quarter_contract_is_refused_at_publish(self):
        rid = "cv6-like-r1"
        d = self.launcher(rid, "--claim-cpus 0-95 --gpu-quiet exclusive")
        with self.assertRaises(rf.Refused) as cm:
            rf.publish(self.fx.spec(rid, d, regions="0-23"), self.fx.flags)
        msg = str(cm.exception)
        self.assertIn("CLAIM-WIDER-THAN-CONTRACT", msg)
        # the same verdict the live admission gate printed 56 times (fixture), now before any smoke
        gate = cv6_refusal()
        self.assertIn("claims q0+q1+q2+q3+gpu-quiet", gate)
        self.assertIn("claims q0+q1+q2+q3+gpu-quiet", msg)
        self.assertIn("regions=0-23", msg)
        self.assertIn("miss q1+q2+q3", msg)
        self.assertIn("missing q1+q2+q3", gate)
        self.assertFalse(os.path.exists(rf.ready_path(self.fx.flags, rid)), "nothing published")

    def test_claim_matching_the_contract_publishes(self):
        rid = "claim-ok-r1"
        d = self.launcher(rid, "--claim-cpus 0-23")
        row = rf.publish(self.fx.spec(rid, d, regions="0-23"), self.fx.flags)
        self.assertEqual(row["id"], rid)

    def test_unresolved_claim_is_not_judged(self):
        rid = "claim-var-r1"
        d = self.launcher(rid, '--claim-cpus "$WS58_REGIONS"')
        self.assertIsNone(rf.claim_wider_refusal({"regions": "0-23"}, {"options": [frozenset({"q0"})]},
                                                 rf.parse_launcher(os.path.join(d, "launch.sh"))))


# ---------------------------------------------------------------- #4 preflight
class Preflight(unittest.TestCase):
    def setUp(self):
        self.fx = JobFixture()
        self.rid = "pf-r1"
        self.d = self.fx.job(self.rid)

    def tearDown(self):
        self.fx.cleanup()

    def spec(self, **kw):
        kw.setdefault("decision_rule", "score >= 1")
        return self.fx.spec(self.rid, self.d, **kw)

    def run_pf(self, spec, **kw):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            pr.preflight(spec, self.fx.flags, **kw)
        return out.getvalue()

    def refused(self, spec, needle, **kw):
        with self.assertRaises(rf.Refused) as cm, contextlib.redirect_stdout(io.StringIO()):
            pr.preflight(spec, self.fx.flags, **kw)
        self.assertIn(needle, str(cm.exception))
        return str(cm.exception)

    def relaunch(self, extra, cmd="bash '$D/job.sh'"):
        write(os.path.join(self.d, "launch.sh"), textwrap.dedent(f"""\
            #!/bin/bash
            set -euo pipefail
            D={self.d}
            ENGINE={self.fx.engine}
            exec bash "$ENGINE" --id {self.rid} --class cpu --min-window 300 --stop "$D/STOP" {extra} \\
              --workdir "$D" --cmd "{cmd}"
            """), 0o755)

    def test_clean_row_passes_and_prints_the_checked_metrics(self):
        out = self.run_pf(self.spec(decision_rule="score >= 1 and tps > 2"))
        self.assertIn("DECISION-RULE machine-checkable", out)
        self.assertIn("score >= 1; tps > 2", out)
        self.assertNotIn("WARN", out)

    # decision rule
    def test_prose_rule_refused_without_verdict_by(self):
        msg = self.refused(self.spec(decision_rule="Accept LANE_LARGE only when both runs agree"), "decision_rule is prose")
        self.assertIn('"verdict_by": "agent"', msg)

    def test_prose_rule_with_verdict_by_agent_and_owner_passes(self):
        out = self.run_pf(self.spec(decision_rule="Accept LANE_LARGE only when both runs agree", verdict_by="agent"))
        self.assertIn("verdict_by agent", out)
        self.refused(self.spec(decision_rule="prose", verdict_by="agent", owner=""), "decision_rule is prose")
        self.refused(self.spec(decision_rule="prose", verdict_by="nobody"), "decision_rule is prose")

    def test_rule_check_matches_auto_file(self):
        af = pr._churn_mod("auto_file")
        for rule in ("score >= 1", "score>=1 on every item", "tps >= 10 and ppl_delta <= 0.01", "x"):
            ok = af.machine_checkable(rule)
            if ok:
                self.run_pf(self.spec(decision_rule=rule))
            else:
                self.refused(self.spec(decision_rule=rule), "decision_rule is prose")

    # smoke predicate
    def test_smoke_predicate_already_true_refused(self):
        write(os.path.join(self.d, "out", "results.jsonl"), '{"item": 1, "score": 1}\n')
        msg = self.refused(self.spec(smoke_predicate="test -s out/results.jsonl"), "already exits 0 BEFORE the launch")
        self.assertIn("FILLER_SMOKE_T0", msg)

    def test_smoke_predicate_false_passes(self):
        self.run_pf(self.spec(smoke_predicate="test -s out/results.jsonl"))

    def test_custom_format_predicate_is_checked_too(self):
        self.refused(self.spec(result_format="custom:true"), "result_format custom:")

    # complete_cmd
    def test_complete_cmd_already_true_refused_unless_rerun(self):
        open(os.path.join(self.d, "out", "COMPLETE"), "w").close()
        self.refused(self.spec(), "nothing to do; already complete")
        self.run_pf(self.spec(), rerun=True)

    def test_complete_cmd_runs_in_workdir_without_smoke_env(self):
        self.relaunch("--complete-cmd 'test \"$PWD\" = \"$FILLER_ID-x\" || test -n \"${FILLER_SMOKE:-}${FILLER_SMOKE_UNITS:-}\" "
                      "|| { test \"$FILLER_DRYRUN\" = 1 && test \"$(basename \"$PWD\")\" = pf-r1 && touch seen; exit 1; }'")
        os.environ["FILLER_SMOKE"] = "1"
        try:
            self.run_pf(self.spec())
        finally:
            os.environ.pop("FILLER_SMOKE", None)
        self.assertTrue(os.path.exists(os.path.join(self.d, "seen")), "ran in --workdir with the dry-run env, no FILLER_SMOKE*")

    # precond_cmd
    def test_precond_false_refused(self):
        self.relaunch("--complete-cmd 'test -e out/COMPLETE' --precond-cmd 'echo build missing; false'")
        self.assertEqual(rf.parse_launcher(os.path.join(self.d, "launch.sh"))["precond_cmd"], "echo build missing; false")
        msg = self.refused(self.spec(), "--precond-cmd")
        self.assertIn("build missing", msg)
        self.assertIn("PARKS the row", msg)

    def test_precond_true_passes(self):
        self.relaunch("--complete-cmd 'test -e out/COMPLETE' --precond-cmd 'true'")
        self.run_pf(self.spec())

    # bounded
    def test_timeout_warns_never_hangs(self):
        self.relaunch("--complete-cmd 'sleep 5' --precond-cmd 'sleep 5'")
        old = pr.PREFLIGHT_TIMEOUT_S
        pr.PREFLIGHT_TIMEOUT_S = 1
        try:
            spec = self.spec()
            out = self.run_pf(spec)
        finally:
            pr.PREFLIGHT_TIMEOUT_S = old
        self.assertIn("timed out after 1s", out)
        self.assertTrue(any("not judged" in w for w in spec["publish_warnings"]))

    # env cleaning
    def test_env_cleaning_without_filler_id_warns(self):
        write(os.path.join(self.d, "job.sh"), f"#!/bin/bash\nD={self.d}\nenv -i PATH=/usr/bin python3 run.py\n", 0o755)
        spec = self.spec()
        out = self.run_pf(spec)
        self.assertIn("WARN env-clean", out)
        self.assertIn("pass FILLER_ID through", out)
        self.assertTrue(any("env-clean" in w for w in spec["publish_warnings"]))

    def test_env_cleaning_with_filler_id_passthrough_and_comments_are_quiet(self):
        write(os.path.join(self.d, "job.sh"), f"#!/bin/bash\nD={self.d}\n# env -i is bad\n"
                                               "env -i PATH=/usr/bin FILLER_ID=\"$FILLER_ID\" python3 run.py\n", 0o755)
        self.assertNotIn("WARN", self.run_pf(self.spec()))

    def test_python_env_dict_and_new_session_warn(self):
        py = os.path.join(self.d, "run.py")
        write(py, "import subprocess\nsubprocess.run(['x'], env={'PATH': '/usr/bin'}, start_new_session=True)\n", 0o644)
        self.relaunch("--complete-cmd 'test -e out/COMPLETE'", cmd="python3 $D/run.py")
        out = self.run_pf(self.spec())
        self.assertIn("env={", out)
        self.assertIn("start_new_session=True", out)

    # end to end through the CLI
    def test_cli_refuses_before_publishing(self):
        open(os.path.join(self.d, "out", "COMPLETE"), "w").close()
        sp = os.path.join(self.d, "spec.json")
        with open(sp, "w") as f:
            json.dump(self.spec(), f)
        saved = (pr.check_handoff, pr.check_task_lint)
        pr.check_handoff = pr.check_task_lint = lambda spec, repo=None: []
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                rc = pr.main([sp, "--flags", self.fx.flags])
        finally:
            pr.check_handoff, pr.check_task_lint = saved
        self.assertEqual(rc, 2)
        self.assertIn("REFUSED: nothing to do; already complete", out.getvalue())
        self.assertFalse(os.path.exists(rf.ready_path(self.fx.flags, self.rid)))
        self.assertFalse(os.path.exists(os.path.join(rf.dry_dir(self.fx.flags, self.rid), "SMOKE-QUEUED.json")))


if __name__ == "__main__":
    unittest.main()
