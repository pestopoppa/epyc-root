#!/usr/bin/env python3
"""handoff_sessions.py AUTO-START (ws58, 2026-11-01): the dispatcher itself starts per-handoff sessions.

Pinned (temp dirs, stubbed runner, patched `landed`; no engine, no git, no network):
  1. With live < max_live the dispatcher STARTS sessions for the handoffs that need one, best first: the handoff whose
     tasks unblock an inference row before zero-score handoffs; zero-score ties by backlog-priority rank of the
     handoff's index row (NOT alphabetically). Engine = registry `default_engine`; brief written; cwd gate honoured;
     `AUTO-START` logged; BACKLOG-handoff-<slug>.md written at once; session_id parsed from the engine output.
  2. Slots: a suspended session (no live pid) does not count as live; a session whose handoff has no open task left
     becomes `done` and its slot is filled.
  3. `auto_start: false` disables it; a handoff that already has a non-done session is never started twice.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_COORD = Path(__file__).resolve().parents[1]
if str(_COORD) not in sys.path:
    sys.path.insert(0, str(_COORD))

import backlog_gen as bg  # noqa: E402
import handoff_sessions as hs  # noqa: E402

_REAL_ENSURE_LANE = hs.ensure_lane  # fixtures stub ensure_lane; the lane tests call the real one


def _w(p, txt):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(txt)


class AutoStartFixture(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.flags = os.path.join(self.td.name, "flags")
        self.repo = os.path.join(self.td.name, "repo")
        os.makedirs(os.path.join(self.flags, "ready"))
        os.makedirs(os.path.join(self.flags, "grants"))
        bg._rf = None
        # three handoffs needing a session: alpha (alphabetically first, lowest priority), mid (unblocks a gpu row),
        # zed (alphabetically last, best backlog-priority rank). One handoff with no open tasks: closed.
        for h in ("alpha", "mid", "zed"):
            _w(os.path.join(self.repo, f"handoffs/active/{h}.md"), f"# {h}\n- [ ] open task of {h}\n- [x] done task\n")
        _w(os.path.join(self.repo, "handoffs/active/closed.md"), "# closed\n- [x] everything ticked\n")
        _w(os.path.join(self.repo, "handoffs/active/backlog-priority.json"), json.dumps({
            "rows": {"INF-1": {"kind": "inference-ready", "rank": 1}, "INF-9": {"kind": "inference-ready", "rank": 9},
                     "INF-5": {"kind": "inference-ready", "rank": 5}}, "inference_prep": []}))
        _w(os.path.join(self.repo, "handoffs/active/.index-state.json"), json.dumps({
            "handoffs": {"alpha.md": {"row_id": "INF-9"}, "mid.md": {"row_id": "INF-5"}, "zed.md": {"row_id": "INF-1"},
                         "closed.md": {"row_id": "INF-7"}},
            "rows": {"INF-9": {"handoff": "alpha.md"}, "INF-5": {"handoff": "mid.md"}, "INF-1": {"handoff": "zed.md"}}}))
        json.dump({"schema": "epyc.row.v3", "id": "row-gpu-1", "owner": "o", "lane": "gpu", "regions": "mi210_0,184-191",
                   "priority_rank": 3, "handoff_task": "handoffs/active/mid.md:INF-5"},
                  open(os.path.join(self.flags, "ready", "row-gpu-1.json"), "w"))
        _w(os.path.join(self.flags, "WORK-codex-gen-code.md"),
           "- [M] handoffs/active/alpha.md:10 — alpha big task\n"
           "- [M] handoffs/active/zed.md:10 — zed big task\n"
           "- [M] handoffs/active/mid.md:10 — mid task unblocking a gpu row [unblocks: row-gpu-1]\n"
           "- [M] handoffs/active/closed.md:10 — stale task of a finished handoff\n")
        self.reg = {"schema": "epyc.handoff-sessions.v1", "max_live": 2, "paused_until": None, "default_engine": "claude",
                    "sessions": {}}
        hs.save(hs.reg_path(self.flags), self.reg)
        self.calls = []

        self._lane = patch.object(hs, "ensure_lane", lambda slug, repo=None: (self.repo, "fast-forwarded"))
        self._lane.start()
        self._disk = patch.object(hs, "free_gib", lambda path="/": 999.0)  # the real disk may be below the floor
        self._disk.start()

    def tearDown(self):
        self._lane.stop()
        self._disk.stop()
        self.td.cleanup()

    def runner(self, cmd, prompt_file, out, cwd=None):
        self.calls.append({"cmd": cmd, "prompt": open(prompt_file).read(), "out": out, "cwd": cwd})
        _w(out, '{"type":"system","session_id":"claude-sess-%d","thread_id":"codex-thr-%d"}\n' % (len(self.calls), len(self.calls)))
        return 99999990 + len(self.calls), out  # pids that cannot be alive

    def log_text(self):
        try:
            return open(os.path.join(self.flags, "handoff-sessions.log")).read()
        except OSError:
            return ""

    def dispatch(self):
        with patch.object(hs, "landed", return_value=True), patch.object(hs, "project_cwd", return_value=self.repo):
            return hs.dispatch_once(self.flags, runner=self.runner, repo=self.repo)


class AutoStartTests(AutoStartFixture):
    def test_ranking_engine_brief_backlog_and_log(self):
        reg, _ = self.dispatch()
        S = reg["sessions"]
        # operator loop 2026-11-02: every handoff with open boxes may get a session; free slots go by handoff priority
        self.assertEqual(sorted(k for k in S if k != "codex-gen"), ["mid", "zed"], S.keys())
        self.assertTrue(S["codex-gen"]["generalist"], "codex-gen is an ordinary managed session, always registered")
        self.assertEqual([c["prompt"].split("owns `")[1].split("`")[0] for c in self.calls],
                         ["handoffs/active/zed.md", "handoffs/active/mid.md"], "backlog-priority.json order: INF-1, INF-5")
        for slug in ("mid", "zed"):
            e = S[slug]
            self.assertEqual(e["engine"], "claude", "registry default_engine knob")
            self.assertEqual(e["status"], "live")
            self.assertTrue(os.path.exists(e["brief"]))
            self.assertTrue(os.path.exists(os.path.join(self.flags, f"BACKLOG-handoff-{slug}.md")), "backlog written at start")
        self.assertEqual(self.calls[0]["cmd"][:2], ["claude", "-p"])
        for marker in (hs.FANOUT_LINE, "WRAPPED <sha>", hs.REPORT_LINE):
            self.assertIn(marker, self.calls[0]["prompt"])
        self.assertEqual(S["mid"]["auto_start"]["rows"], ["row-gpu-1"])
        self.assertEqual(S["mid"]["handoff_rows"], ["INF-5"])
        log = self.log_text()
        self.assertIn("AUTO-START mid handoff=handoffs/active/mid.md engine=claude", log)
        self.assertIn("rows=row-gpu-1", log)
        self.assertIn("AUTO-START zed", log)
        self.assertNotIn("AUTO-START alpha", log, "max_live=2: the third handoff waits for a slot")
        self.assertNotIn("closed", S, "a handoff with no open task never gets a session")

    def test_suspended_session_does_not_count_as_live_and_done_frees_slot(self):
        self.reg["max_live"] = 1
        self.reg["sessions"] = {
            "waiting": {"handoff": "handoffs/active/alpha.md", "engine": "codex", "session_id": "t1", "status": "suspended",
                        "pid": None, "last_wrapup": "abc1234", "last_end": "2026-11-01T10:00:00Z", "waits_on": ["row-x"]},
            "finished": {"handoff": "handoffs/active/closed.md", "engine": "codex", "session_id": "t2", "status": "suspended",
                         "pid": None, "last_wrapup": "abc1234", "last_end": "2026-11-01T10:00:00Z"}}
        hs.save(hs.reg_path(self.flags), self.reg)
        # `waiting` reported blocked on a readied (granted) row: the ONLY state in which a session may be paused
        self.reg["sessions"]["waiting"]["last_report"] = {"next": "blocked", "blocked_by": ["row-x"]}
        self.reg["sessions"]["finished"]["last_report"] = {"next": "done"}
        hs.save(hs.reg_path(self.flags), self.reg)
        _w(os.path.join(self.flags, "grants", "row-x.grant"), "regions=0-23\n")
        reg, _ = self.dispatch()
        S = reg["sessions"]
        self.assertEqual(S["finished"]["status"], "retired", "closed: never resumed")
        self.assertIn("DONE finished: next=done; handoff archived on origin/main; session retired", self.log_text())
        self.assertEqual(S["waiting"]["status"], "suspended", "paused: every blocked_by row is readied")
        self.assertIn("PAUSE waiting: blocked on readied row(s) row-x [running]", self.log_text())
        self.assertEqual(S["waiting"]["work_state"], "pause")
        # the suspended session holds no slot: with max_live=1 exactly one auto-start happened, for the best candidate
        self.assertEqual(len(self.calls), 1)
        self.assertIn("zed", S)
        self.assertEqual(S["zed"]["status"], "live")
        self.assertNotIn("alpha", {k for k, e in S.items() if e.get("auto_started")}, "alpha already has a session (waiting)")

    def test_knob_off_and_no_double_start(self):
        self.reg["auto_start"] = False
        hs.save(hs.reg_path(self.flags), self.reg)
        reg, _ = self.dispatch()
        self.assertEqual(self.calls, [])
        self.assertEqual([k for k in reg["sessions"] if k != "codex-gen"], [])
        reg["auto_start"] = True
        hs.save(hs.reg_path(self.flags), reg)
        reg, _ = self.dispatch()
        n = len(self.calls)
        self.assertEqual(n, 2, "max_live=2 handoffs start on the first pass")
        # make the started pids "alive": a second pass must not start the same handoffs again
        with patch.object(hs, "alive", return_value=True):
            reg, _ = self.dispatch()
        self.assertEqual(len(self.calls), n, "no second start while the sessions are live")

    def test_slug_for(self):
        self.assertEqual(hs.slug_for("handoffs/active/autokernel-research-loop.md", {}), "autokernel-research-loop")
        self.assertEqual(hs.slug_for("handoffs/active/kv-unified-stack-rollout.md", {}), "kv-unified-stack")
        taken = {"yarn-context-extension": {"handoff": "handoffs/active/other.md"}}
        self.assertEqual(hs.slug_for("handoffs/active/yarn-context-extension-research.md", taken), "yarn-context-extension-2")


if __name__ == "__main__":
    unittest.main()


class TmuxWindowTests(AutoStartFixture):
    """Operator 2026-11-01: every session runs in tmux window agent:h-<slug> (by name), JSONL still captured via tee, pid/rc
    files for the dispatcher, pane reused on resume (respawn-pane), killed on done, protected windows untouched."""

    def fake_tmux_factory(self, windows):
        calls = []

        def fake(*args, timeout=20):
            calls.append(args)
            if args[0] == "list-windows":
                return 0, "\n".join(windows) + "\n"
            if args[0] in ("new-window", "respawn-pane"):
                line = args[-1]  # the bash -c script: emulate the pane writing the pid file
                pidf = line.split("echo $! > '")[1].split("'")[0]
                _w(pidf, "99999991\n")
                if args[0] == "new-window":
                    windows.append(args[args.index("-n") + 1])
                return 0, ""
            if args[0] == "kill-window":
                windows.remove(args[args.index("-t") + 1].split(":=")[1])
                return 0, ""
            return 0, ""
        return fake, calls

    def test_start_creates_named_window_resume_respawns_done_kills(self):
        windows = ["btop", "claude", "codex-gen"]
        fake, calls = self.fake_tmux_factory(windows)
        e = {"handoff": "handoffs/active/mid.md", "engine": "codex", "cwd": self.repo}
        with patch.object(hs, "tmux", fake), patch.object(hs, "project_cwd", return_value=self.repo):
            pid, out = hs.launch(self.flags, "mid", e, "PROMPT", fresh=True)
            self.assertEqual(pid, 99999991)
            self.assertIn("h-mid", windows)
            nw = [c for c in calls if c[0] == "new-window"][0]
            self.assertEqual(nw[:5], ("new-window", "-d", "-t", "agent:", "-n"))
            self.assertEqual(nw[5], "h-mid")
            script = nw[-1]
            self.assertIn(f"tee '{out}'", script, "JSONL capture kept")
            self.assertIn("pretty", script)
            self.assertIn(f"'{out}.rc'", script, "exit status file")
            self.assertIn("'codex' 'exec' '--json' '-m' 'gpt-6-luna' '-c' 'model_reasoning_effort=\"medium\"'", script)
            self.assertIn(("set-option", "-w", "-t", "agent:=h-mid", "remain-on-exit", "on"), calls)
            # resume: the window exists -> respawn-pane by NAME, no new window, never send-keys
            pid2, out2 = hs.launch(self.flags, "mid", dict(e, session_id="thr"), "PROMPT2", fresh=False)
            rs = [c for c in calls if c[0] == "respawn-pane"][0]
            self.assertEqual(rs[:4], ("respawn-pane", "-k", "-t", "agent:=h-mid"))
            self.assertEqual(sum(1 for c in calls if c[0] == "new-window"), 1)
            self.assertFalse(any(c[0] == "send-keys" for c in calls))
            self.assertFalse(any("codex-gen" in str(c) or "agent:=claude" in str(c) for c in calls if c[0] != "list-windows"))
            # done -> kill-window by name
            hs.kill_window("mid")
            self.assertNotIn("h-mid", windows)
            self.assertIn(("kill-window", "-t", "agent:=h-mid"), calls)
            hs.kill_window("claude")  # protected: never killed
            self.assertIn("claude", windows)

    def test_no_tmux_session_falls_back_to_detached(self):
        e = {"handoff": "handoffs/active/mid.md", "engine": "codex", "cwd": self.repo}
        with patch.object(hs, "tmux", lambda *a, **k: (1, "no server")), patch.object(hs, "project_cwd", return_value=self.repo), \
                patch.object(hs.subprocess, "Popen") as popen:
            popen.return_value.pid = 4242
            pid, out = hs.launch(self.flags, "mid", e, "PROMPT", fresh=True)
        self.assertEqual(pid, 4242)
        self.assertIn("TMUX-FALLBACK mid", self.log_text())

    def test_pretty_filter_and_rc(self):
        import io
        src = io.StringIO('{"type":"thread.started","thread_id":"thr-1"}\n{"type":"item.completed","item":{"type":"command_execution","command":"ls"}}\nplain\n')
        dst = io.StringIO()
        hs.pretty(src, dst)
        self.assertIn("[session thr-1]", dst.getvalue())
        self.assertIn("[item.completed] ls", dst.getvalue())
        self.assertIn("plain", dst.getvalue())
        out = os.path.join(self.flags, "x.jsonl")
        _w(out + ".rc", "3\n")
        self.assertEqual(hs.last_rc({"last_output": out}), 3)
        self.assertIsNone(hs.last_rc({"last_output": out + "nope"}))


class PauseRuleTests(AutoStartFixture):
    def test_decide_and_pane_status(self):
        e = {"handoff": "handoffs/active/alpha.md", "status": "suspended", "last_end": "2026-11-01T10:00:00Z"}
        d = lambda rep, **kw: hs.decide(self.flags, "a", dict(e, last_report=rep, **kw), self.repo)
        self.assertEqual(d(None), ("continue", "next=unreported"), "a missing report never stops a session")
        self.assertEqual(d("garbage"), ("continue", "next=unreported"))
        self.assertEqual(d({"next": "non-inference"})[0], "continue")
        self.assertEqual(d({"next": "inference"})[0], "continue")
        self.assertEqual(d({"next": "blocked"})[0], "continue", "blocked without ids never pauses")
        self.assertEqual(d({"next": "blocked", "blocked_by": ["r1"]}), ("continue", "making-ready: r1 is not ready (state: unknown) - make it ready"))
        _w(os.path.join(self.flags, "dryrun", "r1", "PASS.json"), "{}")
        _w(os.path.join(self.flags, "grants", "r2.grant"), "")
        self.assertEqual(d({"next": "blocked", "blocked_by": ["r1", "r2"]}), ("pause", "blocked on readied row(s) r1 [grantable], r2 [running]"))
        hs.time.sleep(0.02)
        _w(os.path.join(self.flags, "dryrun", "r1", "FAIL-1.json"), "{}")  # a later FAIL un-readies it: resumed
        self.assertTrue(d({"next": "blocked", "blocked_by": ["r1", "r2"]})[1].startswith("making-ready: r1 is not ready (state: failed) - make it ready"))
        _w(os.path.join(self.flags, "dryrun", "r3", "RUNNING.json"), '{"pid": 1}')  # pending dry run: NOT readied
        why = d({"next": "blocked", "blocked_by": ["r3"]})
        self.assertEqual(why[0], "continue")
        self.assertIn("making-ready", why[1])
        _w(os.path.join(self.flags, "dryrun", "r4", "FAIL-1.json"),
           json.dumps({"fix_task": "fix FIXME-X", "launcher_out_tail": ["line-a", "TAIL-MARK"]}))
        memo = d({"next": "blocked", "blocked_by": ["r4"]})[1]
        self.assertIn("FIX TASK (r4): fix FIXME-X", memo)
        self.assertIn("TAIL-MARK", memo)
        self.assertNotIn("dryrun-running", hs.READIED)
        _w(os.path.join(self.flags, "grants", "r2.ended"), "rc=0\n")  # the row ended: resumed
        self.assertEqual(d({"next": "blocked", "blocked_by": ["r2"]})[1], "making-ready: r2 is not ready (state: done) - make it ready")
        self.assertEqual(d({"next": "done"}), ("continue", "you reported next=done but the handoff has 1 open box(es) - finish or tick them"))
        e["handoff"] = "handoffs/active/closed.md"
        self.assertEqual(d({"next": "done"})[0], "done")
        with patch.object(hs, "active_on_main", lambda h, repo=None: True):  # still in active/ on origin/main: not closed
            self.assertEqual(d({"next": "done"})[0], "continue")
            self.assertIn("finish the completion wrap-up", d({"next": "done"})[1])
        self.assertEqual(d({"next": "non-inference"})[0], "continue", "only the session's own next=done closes a handoff")
        self.assertEqual(hs.decide(self.flags, "codex-gen", {"generalist": True, "last_report": {"next": "done"}})[0], "pause")
        # pane status lines: never "Pane is dead"
        self.assertTrue(hs.pane_status_line({"status": "live", "last_resume": "2026-11-01T10:00:00Z"}).startswith("RUNNING turn"))
        self.assertEqual(hs.pane_status_line({"status": "suspended", "work_state": "pause", "work_reason": "blocked on readied row(s) r2 [running]",
                                              "last_end": "2026-11-01T10:00:00Z"}),
                         "PAUSED — blocked on readied row(s) r2 [running] since 2026-11-01T10:00:00Z")
        self.assertTrue(hs.pane_status_line({"status": "suspended", "work_state": "continue", "work_reason": "x"}).startswith("RESUMING"))
        self.assertEqual(hs.pane_status_line({"status": "done"}), "DONE")
        self.assertIn("pane-status", hs.pane_command(["codex"], "p", "o", "/w"))


class WindowClutterTests(AutoStartFixture):
    def test_pause_kills_window_resume_recreates_it(self):
        windows = ["btop", "claude", "codex-gen", "h-alpha"]
        fake, calls = TmuxWindowTests.fake_tmux_factory(self, windows)
        self.reg["max_live"] = 3
        self.reg["auto_start"] = False
        self.reg["sessions"] = {"alpha": {"handoff": "handoffs/active/alpha.md", "engine": "codex", "session_id": "t1", "status": "suspended",
                                          "pid": None, "last_wrapup": "abc1234", "last_end": "2026-11-01T10:00:00Z",
                                          "last_output": os.path.join(self.flags, "handoff-sessions/alpha/old.jsonl"),
                                          "last_report": {"next": "blocked", "blocked_by": ["row-x"]}}}
        hs.save(hs.reg_path(self.flags), self.reg)
        # paused: blocked on a readied (granted) row -> window killed, state line logged with the pause reason
        _w(os.path.join(self.flags, "grants", "row-x.grant"), "regions=0-23\n")
        with patch.object(hs, "tmux", fake), patch.object(hs, "landed", return_value=True), patch.object(hs, "project_cwd", return_value=self.repo):
            reg, _ = hs.dispatch_once(self.flags, repo=self.repo)  # no stub runner: the tmux path is exercised
        self.assertNotIn("h-alpha", windows)
        self.assertIn(("kill-window", "-t", "agent:=h-alpha"), calls)
        self.assertIn("STATE alpha: paused - blocked on readied row(s) row-x [running]; tmux window h-alpha killed", self.log_text())
        self.assertEqual(reg["sessions"]["alpha"]["status"], "suspended")
        # the grant goes away (row no longer readied) -> resumed "row-x is not ready"; the window is created again BY NAME
        os.remove(os.path.join(self.flags, "grants", "row-x.grant"))
        with patch.object(hs, "tmux", fake), patch.object(hs, "landed", return_value=True), patch.object(hs, "project_cwd", return_value=self.repo):
            reg, _ = hs.dispatch_once(self.flags, repo=self.repo)
        self.assertIn("h-alpha", windows)
        nw = [c for c in calls if c[0] == "new-window"]
        self.assertEqual(len(nw), 1)
        self.assertEqual(nw[0][:6], ("new-window", "-d", "-t", "agent:", "-n", "h-alpha"))
        self.assertEqual(reg["sessions"]["alpha"]["status"], "live")
        self.assertIn("OPEN alpha: making-ready: row-x is not ready (state: unknown) - make it ready", self.log_text())
        self.assertFalse(any(c[0] == "send-keys" for c in calls))


class _DSHBase(AutoStartFixture):
    """shared helpers: a registered session and a finished turn."""

    def session(self, **kw):
        e = {"handoff": "handoffs/active/alpha.md", "engine": "codex", "session_id": "t1", "status": "suspended", "pid": None,
             "last_wrapup": "abc1234", "last_end": "2026-11-01T10:00:00Z", "last_resume": "2026-11-01T10:00:00Z",
             "row_ids": ["row-a", "row-b"]}
        e.update(kw)
        self.reg["auto_start"] = False
        self.reg["sessions"] = {"alpha": e}
        hs.save(hs.reg_path(self.flags), self.reg)
        return e

    def turn(self, text, rc=None):
        """Simulate a finished turn: dead pid, output file with `text`, optional rc file."""
        out = os.path.join(self.flags, "handoff-sessions", "alpha", "turn.jsonl")
        _w(out, text)
        if rc is not None:
            _w(out + ".rc", f"{rc}\n")
        return out

class DSHTests(_DSHBase):
    """intake-2603 DSH-1..4 (operator "All four", 2026-11-01)."""

    def test_dsh2_run_end_acked_by_receipt_requeued_then_escalated(self):
        self.session()
        _w(os.path.join(self.flags, "grants", "row-a.ended"), "rc=0\n")
        reg, st = self.dispatch()  # event queued and delivered (end_prompt)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("row `row-a`", self.calls[0]["prompt"])
        e = reg["sessions"]["alpha"]
        self.assertEqual(e["pending_event"]["rid"], "row-a")
        # the filing turn "crashes": ends with a WRAPPED line but no FILED receipt -> redelivered, not dropped
        for n in (1, 2, 3):
            e = reg["sessions"]["alpha"]
            e.update({"pid": 99999979, "last_output": self.turn('{"text":"WRAPPED abc1234"}\n')})
            hs.save(hs.reg_path(self.flags), reg)
            reg, st = self.dispatch()
            self.assertIn(f"REQUEUE row-a -> alpha: turn ended without filing-done/row-a.FILED (redelivery {n}/3)", self.log_text())
            self.assertEqual(len(self.calls), 1 + n, "the event is re-delivered once per crashed turn")
            self.assertIn("row `row-a`", self.calls[-1]["prompt"])
        # fourth crash -> escalation, no further delivery
        e = reg["sessions"]["alpha"]
        e.update({"pid": 99999979, "last_output": self.turn('{"text":"WRAPPED abc1234"}\n')})
        hs.save(hs.reg_path(self.flags), reg)
        reg, st = self.dispatch()
        self.assertIn("ESCALATE row-a -> alpha", self.log_text())
        self.assertTrue(os.path.exists(os.path.join(self.flags, "operator-escalations", "filing-row-a.md")))
        self.assertEqual(sum(1 for c in self.calls if "row `row-a`" in c["prompt"]), 4, "1 delivery + 3 redeliveries, never a 5th")
        # a turn that files (FILED receipt) consumes the event: nothing re-queued
        self.session()
        self.calls.clear()
        _w(os.path.join(self.flags, "grants", "row-b.ended"), "rc=0\n")
        reg, st = self.dispatch()
        _w(os.path.join(self.flags, "filing-done", "row-b.FILED"), "")
        reg["sessions"]["alpha"].update({"pid": 99999979, "last_output": self.turn('{"text":"WRAPPED abc1234"}\n')})
        hs.save(hs.reg_path(self.flags), reg)
        reg, st = self.dispatch()
        self.assertEqual([ev["rid"] for ev in st["queue"]], [])
        self.assertNotIn("REQUEUE row-b", self.log_text())

    def test_dsh4_filing_resume_gets_a_slot_above_max_live(self):
        self.reg["max_live"] = 1
        self.session()
        self.reg["sessions"]["busy"] = {"handoff": "handoffs/active/zed.md", "engine": "codex", "session_id": "t2", "status": "live",
                                        "pid": os.getpid(), "last_wrapup": "abc1234"}
        hs.save(hs.reg_path(self.flags), self.reg)
        _w(os.path.join(self.flags, "grants", "row-a.ended"), "rc=0\n")
        with patch.object(hs, "alive", lambda pid: pid == os.getpid()):
            reg, st = self.dispatch()
        self.assertEqual(len(self.calls), 1, "max_live is full, yet the run-end filing resume is dispatched")
        self.assertIn("row `row-a`", self.calls[0]["prompt"])

    def test_dsh3_error_resumes_with_go_on(self):
        e = self.session(pid=99999979)
        e["last_output"] = self.turn('{"type":"error","message":"stream disconnected before completion: 502 Bad Gateway"}\n', rc=1)
        hs.save(hs.reg_path(self.flags), self.reg)
        reg, _ = self.dispatch()
        self.assertEqual(reg["sessions"]["alpha"]["status"], "live", "an error is a go-on nudge: no backoff, no park")
        self.assertIn("go on:", self.calls[0]["prompt"])
        # PUSH_PROMPT only when a WRAPPED sha exists but has not landed
        e = self.session(pid=99999979, last_wrapup=None)
        e["last_output"] = self.turn('{"text":"no wrap-up line at all"}\n', rc=0)
        hs.save(hs.reg_path(self.flags), self.reg)
        self.calls.clear()
        with patch.object(hs, "landed", return_value=False):
            reg, _ = self.dispatch()
        self.assertNotEqual(reg["sessions"]["alpha"]["status"], "unpushed", "no sha -> not marked unpushed")
        self.assertTrue(any("NOT on origin/main" in c["prompt"] for c in self.calls), "unwrapped: PUSH prompt, never parked")
        e = self.session(pid=99999979, last_wrapup=None)
        e["last_output"] = self.turn('{"text":"WRAPPED feedfacecafe"}\n', rc=0)
        hs.save(hs.reg_path(self.flags), self.reg)
        self.calls.clear()
        with patch.object(hs, "landed", return_value=False), patch.object(hs, "project_cwd", return_value=self.repo):
            reg, _ = hs.dispatch_once(self.flags, runner=self.runner, repo=self.repo)
        self.assertIn("UNPUSHED alpha wrapup=feedfacecafe", self.log_text())
        self.assertTrue(any("NOT on origin/main" in c["prompt"] for c in self.calls))

    def test_dsh1_report_json_first_regex_fallback_and_transfer_includes_it(self):
        e = self.session(pid=99999979, last_wrapup=None, last_resume="2026-11-01T10:00:00Z")
        e["last_output"] = self.turn('{"text":"WRAPPED 0000000bad"}\n', rc=0)
        _w(hs.report_path(self.flags, "alpha"), json.dumps({"state": "progress", "wrapped_sha": "c0ffee123456", "question": None, "rows_published": ["r1"]}))
        hs.save(hs.reg_path(self.flags), self.reg)
        with patch.object(hs, "landed", return_value=True):
            reg, _ = self.dispatch()
        e = reg["sessions"]["alpha"]
        self.assertEqual(e["last_wrapup"], "c0ffee123456", "report.json wins over the transcript regex")
        self.assertEqual(e["last_report"]["rows_published"], ["r1"])
        # idle via report state -> idle_reported; a stale report (older than the resume) is ignored -> regex fallback
        e.update({"pid": 99999979, "last_resume": "2099-01-01T00:00:00Z", "last_output": self.turn('{"text":"WRAPPED 83c110265331"}\n', rc=0)})
        hs.save(hs.reg_path(self.flags), reg)
        with patch.object(hs, "landed", return_value=True):
            reg, _ = self.dispatch()
        self.assertEqual(reg["sessions"]["alpha"]["last_wrapup"], "83c110265331")
        self.assertIsNone(reg["sessions"]["alpha"]["last_report"])
        # transfer prompt carries the last report
        reg["sessions"]["alpha"]["last_report"] = {"state": "blocked", "wrapped_sha": "c0ffee123456", "question": "which lane?", "rows_published": []}
        hs.save(hs.reg_path(self.flags), reg)
        with patch.object(hs, "project_cwd", return_value=self.repo):
            hs.transfer(self.flags, "alpha", "claude", runner=self.runner, repo=self.repo)
        self.assertIn("LAST TURN REPORT (report.json, DSH-1)", self.calls[-1]["prompt"])
        self.assertIn("which lane?", self.calls[-1]["prompt"])
        self.assertIn("report.json", hs.brief_text("alpha", reg["sessions"]["alpha"], self.flags))


class CAF1Tests(_DSHBase):
    def test_brief_forbids_polling_and_dryrun_result_resumes(self):
        e = self.session()
        b = hs.brief_text("alpha", e, self.flags)
        self.assertIn("NEVER wait in a turn", b)
        self.assertNotIn("do not poll.", b)
        self.assertIn("awaiting/<name>.json", b)
        self.assertIn("NEVER wait in this turn", hs.idle_prompt("alpha", e, self.flags))
        # the dry run is publish_row's smoke in the owner's own turn: a FAIL file is no dispatcher event
        _w(os.path.join(self.flags, "dryrun", "row-a", "FAIL-1.json"), json.dumps({"reason": "no unit", "fix_task": "fix the result_path"}))
        self.dispatch()
        self.assertNotIn("DRYRUN-RESULT", self.log_text())
        # an awaited file: registered by the session, fires when it exists
        self.session(last_report={"next": "blocked", "blocked_by": ["row-a"]})  # paused on a readied row: only an event resumes it
        _w(os.path.join(self.flags, "grants", "row-a.grant"), "regions=0-23\n")
        self.calls.clear()
        target = os.path.join(self.flags, "subagent-out.json")
        _w(hs.report_path(self.flags, "alpha").replace("report.json", "awaiting/sub1.json"), json.dumps({"path": target, "note": "sub-agent output"}))
        reg, st = self.dispatch()
        self.assertEqual(self.calls, [], "not before the file exists")
        target2 = os.path.join(self.flags, "subagent-out2.json")
        _w(hs.report_path(self.flags, "alpha").replace("report.json", "awaiting/sub2.json"), json.dumps({"path": target2, "note": "second"}))
        # a registration for a file that ALREADY exists is a poll in disguise: ignored (renamed .preexisting), never an event
        pre = os.path.join(self.flags, "already-there.json"); _w(pre, "{}")
        hs.time.sleep(0.05)
        _w(hs.report_path(self.flags, "alpha").replace("report.json", "awaiting/pre.json"), json.dumps({"path": pre, "note": "poll"}))
        hs.time.sleep(0.05)
        _w(target, "{}"); _w(target2, "{}")
        reg, st = self.dispatch()
        self.assertIn("AWAITED 2 file(s) -> alpha", self.log_text())
        self.assertTrue(os.path.exists(hs.report_path(self.flags, "alpha").replace("report.json", "awaiting/pre.json.preexisting")))
        self.assertNotIn(pre, self.log_text())
        self.assertEqual(sum(1 for c in self.calls if "file(s) you were waiting for now exist" in c["prompt"]), 1, "coalesced into ONE turn")
        self.assertIn(target2, self.calls[-1]["prompt"])
        # CAF-6: duplicate run-end (.ended then .complete for the same row) is queued once
        e = self.session()
        self.calls.clear()
        _w(os.path.join(self.flags, "grants", "row-b.ended"), "rc=0\n")
        _w(os.path.join(self.flags, "grants", "row-b.complete"), "rc=0\n")
        reg, st = self.dispatch()
        self.assertIn("DEDUPE row-b -> alpha", self.log_text())
        self.assertEqual(sum(1 for c in self.calls if "row `row-b`" in c["prompt"]), 1)
        self.assertEqual([ev for ev in st["queue"] if ev["rid"] == "row-b"], [])


class CAF3Tests(_DSHBase):
    def test_resume_prompt_carries_state_delta_not_reread(self):
        self.session()
        _w(os.path.join(self.flags, "ready", "row-a.json"), json.dumps({"schema": "epyc.row.v3", "id": "row-a", "owner": "o", "lane": "gpu",
                                                                       "regions": "mi210_0", "priority_rank": 2, "handoff_task": "handoffs/active/alpha.md:INF-9",
                                                                       "blocked_by": ["dry run failed: no unit"]}))
        reg, _ = self.dispatch()
        self.assertEqual(len(self.calls), 1)
        p = self.calls[0]["prompt"]
        self.assertIn("STATE (CAF-3", p)
        self.assertIn("row row-a [blocked, gpu, rank 2]: dry run failed: no unit", p)
        self.assertIn("handoff rank #", p)
        self.assertNotIn("Re-read", p)
        self.assertNotIn("re-read the handoff", p)
        data = bg.build(self.flags, os.path.join(self.repo, "handoffs/active/backlog-priority.json"), "nolog", sessions_path=hs.reg_path(self.flags))
        self.assertIn("next task:", bg.resume_delta(data, "alpha")) if data["workers"]["handoff-alpha"]["code"] else None
        self.assertEqual(bg.resume_delta(data, "nope"), "(no backlog bucket for this session yet)")


class CAF5Tests(_DSHBase):
    def test_numeric_rule_filed_by_script_non_numeric_asks_agent_json(self):
        self.session()
        _w(os.path.join(self.flags, "grants", "row-a.ended"), "rc=0\n")
        with patch.object(hs, "file_result", lambda flags, rid, lane: (0, f"FILED {rid}: pass rc=0 rule=tps>=10 values=tps=12 by=file_result.py\nTICK INF-9 ✅ 2026-11-01 rc=0 pass tps=12 [no-belief: row verdict filed by file_result.py]\n")):
            reg, _ = self.dispatch()
        p = self.calls[0]["prompt"]
        self.assertIn("FILED BY SCRIPT", p)
        self.assertIn("do NOT re-file", p)
        self.assertIn("INF-9 ✅ 2026-11-01 rc=0 pass", p)
        self.assertNotIn("YOU file the verdict yourself", p)
        self.assertIn("FILED-BY-SCRIPT row-a -> alpha", self.log_text())
        self.session(); self.calls.clear()
        _w(os.path.join(self.flags, "grants", "row-b.ended"), "rc=0\n")
        with patch.object(hs, "file_result", lambda flags, rid, lane: (4, f"NEEDS-AGENT-VERDICT {rid}: judge coherence\n")):
            reg, _ = self.dispatch()
        p = self.calls[0]["prompt"]
        self.assertIn("not machine-checkable", p)
        self.assertIn("--verdict-json", p)
        self.assertIn("filing-done/row-b.FILED", p)
        self.assertTrue(os.path.exists(hs.FILE_RESULT))


class BudgetTests(_DSHBase):
    def test_generalist_orphans_and_rotation(self):
        # 2. codex-gen: registered automatically, resumed on its own report (bypasses the cap)
        self.reg["max_live"] = 1
        self.session(status="live", pid=os.getpid())
        hs.ensure_generalist(self.reg)["last_report"] = {"next": "non-inference"}
        hs.save(hs.reg_path(self.flags), self.reg)
        _w(os.path.join(self.flags, "BACKLOG-codex-gen.md"), "## Inference rows\n- [blocked] cpu rank=3 **r-orphan** (row r-orphan) — yours (no handoff session)\n\n## Non-inference tasks\n\n- [S] handoffs/active/zed.md:10 — small fix\n")
        _w(os.path.join(self.flags, "GOAL-codex-gen.md"), "# GOAL\nGOAL-MARKER\n")
        self.calls.clear()
        with patch.object(hs, "alive", lambda pid: pid == os.getpid()):
            reg, _ = self.dispatch()
        g = reg["sessions"]["codex-gen"]
        self.assertEqual(g["status"], "live")
        self.assertIn("GOAL-MARKER", self.calls[0]["prompt"])
        self.assertIn("OPEN codex-gen: next=non-inference", self.log_text())
        self.assertTrue(os.path.exists(os.path.join(self.flags, "briefs", "HANDOFF-codex-gen.md")))
        # 3. an ownerless run-end: file_result rc 4 -> routed to codex-gen; rc 0 -> filed, no turn
        _w(os.path.join(self.flags, "grants", "orphan-1.ended"), "rc=0\n")
        with patch.object(hs, "file_result", lambda f, rid, lane: (4, "NEEDS-AGENT-VERDICT")):
            reg, st = self.dispatch()
        self.assertIn("ORPHAN orphan-1 -> codex-gen: file_result rc=4", self.log_text())
        self.assertTrue(any(ev["slug"] == "codex-gen" and ev["rid"] == "orphan-1" for ev in st["queue"]) or
                        any("row `orphan-1`" in c["prompt"] for c in self.calls))
        _w(os.path.join(self.flags, "grants", "orphan-2.ended"), "rc=0\n")
        with patch.object(hs, "file_result", lambda f, rid, lane: (0, "FILED orphan-2: pass\nTICK x")):
            reg, st = self.dispatch()
        self.assertIn("FILED-BY-SCRIPT orphan-2 (no owner)", self.log_text())
        self.assertFalse(any(ev["rid"] == "orphan-2" for ev in st["queue"]))
        # 4. context rotation: a turn whose per-call context exceeds the threshold makes the next resume FRESH
        e = self.session(pid=99999979)
        e["last_output"] = self.turn('{"text":"WRAPPED abc1234"}\n', rc=0)
        hs.save(hs.reg_path(self.flags), self.reg)
        with patch.object(hs, "context_size", lambda sid, eng="codex": 180_000):
            reg, _ = self.dispatch()
        e = reg["sessions"]["alpha"]
        self.assertEqual(e["rotated_from"]["context_tokens"], 180_000)
        self.assertEqual(self.calls[-1]["cmd"][:3] + self.calls[-1]["cmd"][-1:], ["codex", "exec", "--json", "-"], "the next resume was a FRESH session (rotation)")
        self.assertIn("brief", self.calls[-1]["prompt"].lower())
        self.assertIn("ROTATE alpha: last-call input 180000 > 60000", self.log_text())


class InventoryTests(_DSHBase):
    """Operator 23:30Z: compute must be the ONLY bottleneck; the inventory target is a priority order, never a stop condition."""

    def test_running_rows_never_leave_slots_empty_and_deficit_ranks_first(self):
        # alpha owns 2 RUNNING rows (grant open, live pid), other handoffs have open blockers -> every slot busy
        self.reg["max_live"] = 3
        self.session(status="suspended", last_report={"next": "blocked", "blocked_by": ["run-1", "run-2"]})
        self.reg["auto_start"] = True
        hs.save(hs.reg_path(self.flags), self.reg)
        for rid in ("run-1", "run-2"):
            _w(os.path.join(self.flags, "ready", rid + ".json"), json.dumps({"schema": "epyc.row.v3", "id": rid, "owner": "o", "lane": "cpu", "regions": "any-cpu-quarter",
                                                                             "priority_rank": 1, "handoff_task": "handoffs/active/alpha.md:INF-9"}))
            _w(os.path.join(self.flags, "grants", rid + ".grant"), "regions=0-23\n")
            _w(os.path.join(self.flags, "ready", "armed", rid + ".json"), json.dumps({"id": rid, "pid": os.getpid()}))
        _w(os.path.join(self.flags, "BACKLOG-handoff-alpha.md"), "## Inference rows\n- [running] cpu rank=1 **run-1**\n- [running] cpu rank=1 **run-2**\n\n## Non-inference tasks\n\n- none\n")
        with patch.object(hs, "alive", lambda pid: pid == os.getpid()):
            reg, _ = self.dispatch()
        S = reg["sessions"]
        started = [k for k, e in S.items() if e.get("auto_started")]
        self.assertEqual(sorted(started), ["mid", "zed"], "alpha's slot goes to the next handoffs while its rows run")
        self.assertEqual(S["alpha"]["work_state"], "pause")  # blocked on its own running rows -> paused, slot given away
        self.assertIn("PAUSE alpha: blocked on readied row(s) run-1 [running], run-2 [running]", self.log_text())
        data = bg.build(self.flags, os.path.join(self.repo, "handoffs/active/backlog-priority.json"), "nolog", sessions_path=hs.reg_path(self.flags))
        inv = data["inventory"]
        self.assertEqual((inv["cpu"]["ready"], inv["cpu"]["target"], inv["gpu"]["deficit"]), (2, 8, 2))
        # the gpu lane is in deficit: mid (unblocks a gpu row) ranks first even if a cpu-heavy handoff has a higher plain score
        self.assertEqual(data["handoff_rank"][0]["handoff"], "handoffs/active/mid.md")
        self.assertGreater(data["handoff_rank"][0]["deficit_score"], 0)
        self.assertIn("inventory (ready rows vs target", bg.resume_delta(data, "mid"))

    def test_inventory_starved_alarm_and_dead_push_lock(self):
        now = 1_800_000_000.0
        st = {}
        data = {"inventory": {"gpu": {"ready": 0, "target": 2, "deficit": 2}, "cpu": {"ready": 3, "target": 8, "deficit": 5}},
                "klog_idle": [(hs._dt.datetime.fromtimestamp(now + 200, hs._dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "gpu-quiet")],
                "workers": {"codex-gen": {"rows": [{"id": "g1", "lane": "gpu", "state": "blocked", "rank": 3, "reasons": ["dry run failed: no unit"], "tasks": []},
                                                   {"id": "g2", "lane": "gpu", "state": "needs-launcher", "rank": 9, "reasons": ["missing launcher"], "tasks": []}]}}}
        hs.inventory_alarm(self.flags, st, data, now)
        self.assertNotIn("INVENTORY-STARVED", self.log_text(), "not before 2 keeper ticks")
        hs.inventory_alarm(self.flags, st, data, now + 250)
        log = self.log_text()
        self.assertIn("INVENTORY-STARVED gpu: free region, 0 ready rows, 0 publishable candidates for 4 min; nearest-to-ready: g1 [blocked] dry run failed: no unit; g2 [needs-launcher] missing launcher", log)
        self.assertNotIn("INVENTORY-STARVED cpu", log, "cpu has ready rows")
        hs.inventory_alarm(self.flags, st, data, now + 300)
        self.assertEqual(log.count("INVENTORY-STARVED"), self.log_text().count("INVENTORY-STARVED"), "at most once per 30 min")
        # dead push lock: reported, never released
        lockdir = os.path.join(self.td.name, "push-locks")
        _w(os.path.join(lockdir, "push-abc.json"), json.dumps({"agent": "codex-x", "pid": 99999977, "acquired": "2026-11-01T22:00:00Z"}))
        with patch.object(hs, "PUSH_LOCK_DIR", lockdir):
            hs.dead_push_lock(self.flags, st, now)
            hs.dead_push_lock(self.flags, st, now + 60)
        self.assertEqual(self.log_text().count("PUSH-LOCK-DEAD"), 1)
        self.assertIn("holder codex-x pid 99999977 is dead", self.log_text())
        self.assertIn("NOT released automatically", self.log_text())
        self.assertTrue(os.path.exists(os.path.join(lockdir, "push-abc.json")))


class StartGateTests(AutoStartFixture):
    def test_no_real_row_gate_no_cooldown_no_hourly_cap(self):
        # a just-done handoff that grew open boxes restarts on the next free slot: no per-handoff cooldown, no hourly cap
        self.reg["max_live"] = 1
        self.reg["sessions"]["zed"] = {"handoff": "handoffs/active/zed.md", "engine": "codex", "session_id": "old", "status": "done",
                                       "pid": None, "done_at": hs.now_iso()}
        hs.save(hs.reg_path(self.flags), self.reg)
        hs.save(hs.state_path(self.flags), {"starts": [hs.time.time()] * 50})
        reg, _ = self.dispatch()
        self.assertEqual(reg["sessions"]["zed"]["status"], "live")
        self.assertEqual(reg["sessions"]["zed"]["restarted_from_done"], "old")
        self.assertNotIn("THROTTLED", self.log_text())
        # no ready row anywhere: slots are still filled (no real-row gate)
        os.remove(os.path.join(self.flags, "ready", "row-gpu-1.json"))
        self.reg["sessions"], self.reg["max_live"] = {}, 2
        hs.save(hs.reg_path(self.flags), self.reg)
        reg, _ = self.dispatch()
        self.assertEqual(len([k for k in reg["sessions"] if k != "codex-gen"]), 2)


class SA23Tests(_DSHBase):
    def test_related_ids_in_run_end_and_no_effect_watchdog(self):
        self.session()
        _w(os.path.join(self.flags, "ready", "row-a.json"), json.dumps({"schema": "epyc.row.v3", "id": "row-a", "owner": "o", "lane": "cpu",
                                                                       "handoff_task": "handoffs/active/alpha.md:INF-9", "lineage": "row"}))
        _w(os.path.join(self.flags, "dryrun", "row-a", "FAIL-1.json"), json.dumps({"reason": "old fail"}))
        _w(os.path.join(self.flags, "grants", "row-a.ended"), "rc=0\n")
        reg, st = self.dispatch()
        p = self.calls[0]["prompt"]
        self.assertIn("Related: row=row-a", p)
        self.assertIn("handoff_task=handoffs/active/alpha.md:INF-9", p)
        self.assertIn("prior_fail=", p)
        self.assertNotIn("look in", p, "no cold re-read hint")
        ev = reg["sessions"]["alpha"]["pending_event"]
        self.assertEqual(ev["related"]["handoff_task"], "handoffs/active/alpha.md:INF-9")
        self.assertTrue(ev["related"]["prior_fail"].endswith("FAIL-1.json"))
        # SA-2: 3 starts in the hour, no PASS produced -> one alarm per hour
        st = {"starts": [hs.time.time() - 100] * 3}
        w = hs.start_watchdog(self.flags, st, hs.time.time())
        self.assertEqual((w["starts_h"], w["ready_rows_h"]), (3, 0))
        self.assertIn("AUTO-START-NO-EFFECT 3 auto-start(s)", self.log_text())
        hs.start_watchdog(self.flags, st, hs.time.time() + 60)
        self.assertEqual(self.log_text().count("AUTO-START-NO-EFFECT"), 1)
        _w(os.path.join(self.flags, "dryrun", "row-b", "PASS.json"), "{}")
        st2 = {"starts": [hs.time.time()] * 5}
        hs.start_watchdog(self.flags, st2, hs.time.time())
        self.assertNotIn("watchdog_alarm", st2, "a produced ready row is an effect: no alarm")

    def test_resume_stall_watchdog(self):
        now = hs.time.time()
        old = hs.dt_iso(now - 7200) if hasattr(hs, "dt_iso") else hs._dt.datetime.fromtimestamp(now - 7200, hs._dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        S = {"alpha": {"last_resume": old}}
        hs.start_watchdog(self.flags, {}, now, S)
        self.assertNotIn("RESUME-STALL", self.log_text(), "nothing queued: no alarm")
        st = {"queue": [{"slug": "alpha"}]}
        hs.start_watchdog(self.flags, st, now, S)
        hs.start_watchdog(self.flags, st, now + 60, S)
        self.assertEqual(self.log_text().count("RESUME-STALL"), 1, "rate-limited")
        st2 = {"queue": [{"slug": "alpha"}]}
        hs.start_watchdog(self.flags, st2, now, {"alpha": {"last_resume": hs.now_iso()}})
        self.assertNotIn("resume_stall_alarm", st2, "a recent RESUME: no alarm")


class LaneDiskTests(_DSHBase):
    def test_disk_gate_blocks_new_lanes(self):
        self.reg["auto_start"] = True
        hs.save(hs.reg_path(self.flags), self.reg)
        with patch.object(hs, "free_gib", lambda path="/": 150.0):
            reg, _ = self.dispatch()
        self.assertEqual([k for k in reg["sessions"] if k != "codex-gen"], [])
        self.assertIn("AUTO-START-THROTTLED disk: 150 GiB free < 160; no new lanes", self.log_text())

    def test_sparse_lane_excludes_artifacts_and_reap_removes_clean_landed_lane(self):
        import subprocess, tempfile
        repo = tempfile.mkdtemp()
        subprocess.run(["git", "-C", repo, "init", "-q", "-b", "main"], check=True)
        _w(os.path.join(repo, "artifacts", "big.bin"), "x" * 1000)
        _w(os.path.join(repo, "scripts", "a.py"), "print(1)\n")
        g = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True, capture_output=True)
        g("add", "."); g("commit", "-q", "-m", "base"); g("remote", "add", "origin", repo); g("fetch", "-q", "origin")
        lanes = tempfile.mkdtemp()
        with patch.object(hs, "LANES_DIR", lanes), patch.object(hs, "ROOT", repo):
            d, st = _REAL_ENSURE_LANE("x", repo=repo)
            self.assertEqual(st, "created")
            self.assertTrue(os.path.exists(os.path.join(d, "scripts", "a.py")))
            self.assertFalse(os.path.exists(os.path.join(d, "artifacts", "big.bin")), "artifacts/ excluded from the sparse lane")
            self.assertTrue(hs.lane_clean_and_landed(d))
            # reap: a suspended session's clean, landed lane is removed (no --force); recreated on the next ensure_lane
            reg = {"sessions": {"x": {"handoff": "handoffs/active/x.md", "status": "suspended", "pid": None}}}
            hs.reap_lanes(self.flags, reg, repo)
            self.assertFalse(os.path.exists(d))
            self.assertIn("LANE-REAPED x", self.log_text())
            d, st = _REAL_ENSURE_LANE("x", repo=repo)
            self.assertEqual(st, "created")
            # a dirty lane is kept and logged once
            _w(os.path.join(d, "scripts", "a.py"), "print(2)\n")
            hs.reap_lanes(self.flags, reg, repo); hs.reap_lanes(self.flags, reg, repo)
            self.assertTrue(os.path.exists(d))
            self.assertEqual(self.log_text().count("LANE-DIRTY x"), 1)
            # a live session's lane is never touched
            reg["sessions"]["x"]["pid"] = os.getpid()
            with patch.object(hs, "alive", lambda pid: pid == os.getpid()):
                hs.reap_lanes(self.flags, reg, repo)
            self.assertTrue(os.path.exists(d))


class WrappedGateTests(_DSHBase):
    def test_reaped_lane_passes_dirty_lane_gets_one_resume(self):
        import subprocess, tempfile
        lanes = tempfile.mkdtemp()
        with patch.object(hs, "LANES_DIR", lanes):
            e = {"session_id": "t", "last_end": "x", "cwd": os.path.join(lanes, "h-gone")}
            self.assertTrue(hs.wrapped(e), "a reaped lane (clean + landed by construction) has nothing unwrapped")
            d = os.path.join(lanes, "h-dirty"); os.makedirs(d)
            subprocess.run(["git", "-C", d, "init", "-q", "-b", "main"], check=True)
            _w(os.path.join(d, "f.txt"), "1")
            subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c", "user.name=t", "add", "."], check=True)
            subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "b"], check=True)
            subprocess.run(["git", "-C", d, "remote", "add", "origin", d], check=True); subprocess.run(["git", "-C", d, "fetch", "-q", "origin"], check=True)
            _w(os.path.join(d, "f.txt"), "2")  # dirty tracked edit
            e = {"session_id": "t", "last_end": "x", "cwd": d}
            self.assertTrue(hs.wrapped(e), "a dirty lane is resumed (its prompt ends with wrapup.py)")
            self.assertTrue(hs.wrapped(e), "and is not refused afterwards; the stuck rule caps churn")
        e = {"last_wrapup": None}
        hs.log_unwrapped(self.flags, "s", e); hs.log_unwrapped(self.flags, "s", e)
        self.assertEqual(self.log_text().count("UNWRAPPED s:"), 1)


class NoopLogTests(_DSHBase):
    def test_noop_turn_is_logged_and_hard_parked(self):
        # token audit rec 2 (operator 2026-11-06) supersedes the 11-02 "never parked": no progress evidence -> hard park
        self.session()
        self.reg["sessions"]["alpha"].update({"pid": 99999979, "last_output": self.turn('{"text":"nothing landed"}\n', rc=0), "status": "live"})
        hs.save(hs.reg_path(self.flags), self.reg)
        self.calls.clear()
        with patch.object(hs, "turn_effect", return_value=""):
            reg, _ = self.dispatch()
        self.assertIn("NOOP alpha: turn completed nothing (no landed tick, no row published, no filing) [1 consecutive]", self.log_text())
        self.assertEqual(self.calls, [], "a no-op turn is not progress evidence: parked, not resumed")
        self.assertIn("PARK alpha: no progress evidence", self.log_text())
        self.assertTrue(reg["sessions"]["alpha"]["parked"])
        with patch.object(hs, "turn_effect", return_value=""):
            reg, _ = self.dispatch()
        self.assertEqual(self.calls, [], "a hard park holds across passes until unpark")
        # a landed tick is an effect: turn_effect counts it
        with patch.object(hs, "landed_ticks", lambda sha, repo=None: 2), patch.object(hs, "landed", return_value=True):
            self.assertIn("2 landed tick(s)", hs.turn_effect(self.flags, "alpha", {"last_wrapup": "abc1234", "last_resume": hs.now_iso()}))
        self.assertEqual(hs.turn_effect(self.flags, "alpha", {"last_wrapup": None, "last_resume": "2099-01-01T00:00:00Z"}), "", "a commit alone is not an effect")


class LandLaneTests(_DSHBase):
    def test_dispatcher_lands_unlanded_ticks(self):
        import subprocess, tempfile
        # a clean lane with an unlanded commit that ticks a box: land_lane pushes it and the ticks count as the turn's effect
        origin = tempfile.mkdtemp(); subprocess.run(["git", "init", "-q", "--bare", "-b", "main", origin], check=True)
        lane = tempfile.mkdtemp()
        g = lambda *a: subprocess.run(["git", "-C", lane, "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True, capture_output=True)
        subprocess.run(["git", "-C", lane, "init", "-q", "-b", "main"], check=True)
        _w(os.path.join(lane, "handoffs/active/a.md"), "- [ ] A\n"); g("add", "."); g("commit", "-q", "-m", "base")
        g("remote", "add", "origin", origin); g("push", "-q", "origin", "main"); g("fetch", "-q", "origin")
        _w(os.path.join(lane, "handoffs/active/a.md"), "- [x] A ✅\n"); g("add", "."); g("commit", "-q", "-m", "tick A")
        real_run = subprocess.run
        def fake_push(cmd, **kw):
            if "serialized_push.py" in " ".join(map(str, cmd)):
                return real_run(["git", "-C", lane, "push", "-q", "origin", "HEAD:main"], capture_output=True)
            return real_run(cmd, **kw)
        with patch.object(hs.subprocess, "run", side_effect=fake_push), patch.object(hs, "ROOT", lane):
            landed = hs.land_lane(lane)
        self.assertEqual(len(landed), 1)
        self.assertEqual(hs.landed_ticks(landed[0], repo=lane), 1)
        self.assertEqual(hs.land_lane(lane), [], "nothing left to land")


class HandoffRoutingTests(unittest.TestCase):
    def test_row_routes_by_handoff_task_file_then_legacy_ids(self):
        pilots = {"a": {"handoff": "handoffs/active/alpha.md", "ids": set(), "rows": set()},
                  "b": {"handoff": "handoffs/active/contest.md", "ids": {"old-row"}, "rows": set()}}
        self.assertEqual(bg.handoff_file("handoffs/active/alpha.md:INF-3"), "alpha.md")
        self.assertEqual(bg.handoff_file("FILLERS"), "")
        self.assertEqual(bg.pilot_of(pilots, "new-row", None, "alpha.md:INF-3"), "a")
        self.assertEqual(bg.pilot_of(pilots, "new-row", None, "test.md"), None, "no suffix match (contest.md)")
        self.assertEqual(bg.pilot_of(pilots, "old-row", None, "FILLERS"), "b", "row_ids stay the fallback for old rows")



class InferenceFirstSlotTests(_DSHBase):
    """operator 2026-11-04: a session whose next task is inference gets the free slot ahead of priority order."""

    def test_inference_next_session_beats_higher_priority_non_inference(self):
        base = {"engine": "codex", "status": "suspended", "pid": None, "last_wrapup": "abc1234",
                "last_end": "2026-11-01T10:00:00Z", "last_resume": "2026-11-01T10:00:00Z", "row_ids": []}
        self.reg["max_live"] = 1
        self.reg["auto_start"] = False
        self.reg["sessions"] = {
            "zed": dict(base, handoff="handoffs/active/zed.md", session_id="tz", last_report={"next": "non-inference"}),
            "alpha": dict(base, handoff="handoffs/active/alpha.md", session_id="ta", last_report={"next": "inference"}),
        }
        hs.save(hs.reg_path(self.flags), self.reg)
        reg, _ = self.dispatch()
        S = reg["sessions"]
        self.assertEqual(S["alpha"]["work_reason"], "next=inference")
        self.assertEqual(len(self.calls), 1)
        self.assertIn("alpha", self.calls[0]["out"], "alpha (next=inference, rank 9) takes the slot ahead of zed (rank 1)")
        self.assertTrue(hs.inference_next({"_work": ("continue", "making-ready: r is not ready")}))
        self.assertFalse(hs.inference_next({"work_reason": "next=non-inference"}))
