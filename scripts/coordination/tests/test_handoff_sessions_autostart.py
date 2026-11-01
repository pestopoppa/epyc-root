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

    def tearDown(self):
        self._lane.stop()
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
        # max_live=2: the gpu-unblocking handoff first (score 1.0), then the best backlog-priority rank (zed, rank 1);
        # alpha (rank 9) is NOT started although it sorts first alphabetically
        self.assertEqual(sorted(k for k in S if k != "codex-gen"), ["mid", "zed"], S.keys())
        self.assertTrue(S["codex-gen"]["generalist"], "codex-gen is an ordinary managed session, always registered")
        self.assertEqual(len(self.calls), 2)
        self.assertIn("handoffs/active/mid.md", self.calls[0]["prompt"])
        self.assertIn("handoffs/active/zed.md", self.calls[1]["prompt"])
        for slug in ("mid", "zed"):
            e = S[slug]
            self.assertEqual(e["engine"], "claude", "registry default_engine knob")
            self.assertEqual(e["status"], "live")
            self.assertTrue(os.path.exists(e["brief"]))
            self.assertTrue(os.path.exists(os.path.join(self.flags, f"BACKLOG-handoff-{slug}.md")), "backlog written at start")
        self.assertEqual(self.calls[0]["cmd"][:2], ["claude", "-p"])
        self.assertIn(hs.FANOUT_LINE, self.calls[0]["prompt"])
        self.assertIn("WRAPPED <sha>", self.calls[0]["prompt"])
        self.assertEqual(S["mid"]["auto_start"]["rows"], ["row-gpu-1"])
        self.assertEqual(S["mid"]["handoff_rows"], ["INF-5"])
        log = self.log_text()
        self.assertIn("AUTO-START mid handoff=handoffs/active/mid.md engine=claude", log)
        self.assertIn("rows=row-gpu-1", log)
        self.assertIn("AUTO-START zed handoff=handoffs/active/zed.md engine=claude", log)
        self.assertNotIn("AUTO-START alpha", log)
        # the stub pids are dead: the next pass reaps the turns, parses session ids, and fills the freed slots with alpha
        reg, _ = self.dispatch()
        S = reg["sessions"]
        self.assertEqual(S["mid"]["session_id"], "claude-sess-1")
        self.assertIn("alpha", S)
        self.assertNotIn("closed", S, "a handoff with no open task never gets a session")

    def test_suspended_session_does_not_count_as_live_and_done_frees_slot(self):
        self.reg["max_live"] = 1
        self.reg["sessions"] = {
            "waiting": {"handoff": "handoffs/active/alpha.md", "engine": "codex", "session_id": "t1", "status": "suspended",
                        "pid": None, "last_wrapup": "abc1234", "last_end": "2026-11-01T10:00:00Z", "waits_on": ["row-x"]},
            "finished": {"handoff": "handoffs/active/closed.md", "engine": "codex", "session_id": "t2", "status": "suspended",
                         "pid": None, "last_wrapup": "abc1234", "last_end": "2026-11-01T10:00:00Z"}}
        hs.save(hs.reg_path(self.flags), self.reg)
        # `waiting` has nothing open but a running row: the ONLY state in which a session may be paused
        _w(os.path.join(self.flags, "BACKLOG-handoff-waiting.md"), "## Inference rows\n- [running] cpu rank=1 **row-x**\n\n## Non-inference tasks\n\n- none\n")
        reg, _ = self.dispatch()
        S = reg["sessions"]
        self.assertEqual(S["finished"]["status"], "done")
        self.assertIn("DONE finished: nothing open and no rows waiting", self.log_text())
        self.assertEqual(S["waiting"]["status"], "suspended", "paused: everything left waits on a queued/running row")
        self.assertIn("PAUSE waiting: waiting on row(s) row-x (queued/running)", self.log_text())
        self.assertEqual(S["waiting"]["work_state"], "pause")
        # the suspended session holds no slot: with max_live=1 exactly one auto-start happened, for the best candidate
        self.assertEqual(len(self.calls), 1)
        self.assertIn("mid", S)
        self.assertEqual(S["mid"]["status"], "live")
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
        self.assertEqual(n, 2)
        # make the started pids "alive": a second pass must not start the same handoffs again
        with patch.object(hs, "alive", return_value=True):
            reg, _ = self.dispatch()
        self.assertEqual(len(self.calls), n, "no second start while the sessions are live")

    def test_slug_for(self):
        self.assertEqual(hs.slug_for("handoffs/active/autokernel-research-loop.md", {}), "autokernel-research-loop")
        self.assertEqual(hs.slug_for("handoffs/active/kv-unified-stack-rollout.md", {}), "kv-unified-stack")
        taken = {"yarn-context-extension": {"handoff": "handoffs/active/other.md"}}
        self.assertEqual(hs.slug_for("handoffs/active/yarn-context-extension-research.md", taken), "yarn-context-extension-2")


class YieldTests(AutoStartFixture):
    def test_outranked_session_yields_after_its_turn_and_is_not_resumed_for_new_work(self):
        # cap 1; alpha (rank 9, score 0) has a live-looking session; mid (score 1.0) outranks it
        self.reg["max_live"] = 1
        self.reg["sessions"] = {"alpha": {"handoff": "handoffs/active/alpha.md", "engine": "codex", "session_id": "t1",
                                          "status": "live", "pid": 99999980, "last_wrapup": "abc1234", "last_end": "2026-11-01T10:00:00Z"}}
        hs.save(hs.reg_path(self.flags), self.reg)
        _w(os.path.join(self.flags, "BACKLOG-handoff-alpha.md"), "## Non-inference\n- [M] handoffs/active/alpha.md:10 — alpha big task\n")
        with patch.object(hs, "alive", return_value=True):
            reg, _ = self.dispatch()
        self.assertEqual(self.calls, [], "never killed or replaced mid-task; cap is full")
        self.assertTrue(reg["sessions"]["alpha"]["yield"])
        self.assertIn("YIELD alpha: handoff rank #", self.log_text())
        # its turn ends (pid gone, wrap-up landed): not resumed for new work although it has advanceable tasks; mid gets the slot
        reg, _ = self.dispatch()
        S = reg["sessions"]
        self.assertEqual(S["alpha"]["status"], "suspended")
        self.assertEqual([c["prompt"].split("owns `")[1].split("`")[0] for c in self.calls], ["handoffs/active/mid.md"])
        self.assertIn("mid", S)


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
            self.assertIn("'codex' 'exec' '--json' '-'", script)
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
    def test_work_state_and_pane_status(self):
        e = {"handoff": "handoffs/active/alpha.md", "status": "suspended", "last_end": "2026-11-01T10:00:00Z"}
        bp = os.path.join(self.flags, "BACKLOG-handoff-a.md")
        _w(bp, "## Inference rows\n- [blocked] cpu rank=1 **r1**\n- [running] cpu rank=2 **r2**\n\n## Non-inference tasks\n\n- none\n")
        self.assertEqual(hs.work_state(self.flags, "a", e, self.repo)[0], "continue")
        _w(bp, "## Inference rows\n- [running] cpu rank=2 **r2**\n\n## Non-inference tasks\n\n- none\n")
        self.assertEqual(hs.work_state(self.flags, "a", e, self.repo), ("pause", "waiting on row(s) r2 (queued/running)"))
        _w(bp, "Own inference tasks to publish as rows:\n- a L12 [gpu] run llama-bench\n## Inference rows\n- [running] cpu rank=2 **r2**\n")
        self.assertEqual(hs.work_state(self.flags, "a", e, self.repo)[0], "continue")
        _w(bp, "## Inference rows\n\n- none\n\n## Non-inference tasks\n\n- none\n")
        self.assertEqual(hs.work_state(self.flags, "a", e, self.repo), ("continue", "1 open box(es) in the handoff, none waiting on a row"))
        e["handoff"] = "handoffs/active/closed.md"
        self.assertEqual(hs.work_state(self.flags, "a", e, self.repo)[0], "done")
        # pane status lines: never "Pane is dead"
        self.assertTrue(hs.pane_status_line({"status": "live", "last_resume": "2026-11-01T10:00:00Z"}).startswith("RUNNING turn"))
        self.assertEqual(hs.pane_status_line({"status": "suspended", "work_state": "pause", "work_reason": "waiting on row(s) r2 (queued/running)",
                                              "last_end": "2026-11-01T10:00:00Z"}),
                         "PAUSED — waiting on row(s) r2 (queued/running) since 2026-11-01T10:00:00Z")
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
                                          "last_output": os.path.join(self.flags, "handoff-sessions/alpha/old.jsonl")}}
        hs.save(hs.reg_path(self.flags), self.reg)
        # paused: everything left waits on a running row -> window killed, state line logged with the pause reason
        _w(os.path.join(self.flags, "BACKLOG-handoff-alpha.md"), "## Inference rows\n- [running] cpu rank=1 **row-x**\n\n## Non-inference tasks\n\n- none\n")
        with patch.object(hs, "tmux", fake), patch.object(hs, "landed", return_value=True), patch.object(hs, "project_cwd", return_value=self.repo):
            reg, _ = hs.dispatch_once(self.flags, repo=self.repo)  # no stub runner: the tmux path is exercised
        self.assertNotIn("h-alpha", windows)
        self.assertIn(("kill-window", "-t", "agent:=h-alpha"), calls)
        self.assertIn("STATE alpha: paused - waiting on row(s) row-x (queued/running); tmux window h-alpha killed", self.log_text())
        self.assertEqual(reg["sessions"]["alpha"]["status"], "suspended")
        # the row ends -> open work again -> resumed; the window is created again BY NAME
        _w(os.path.join(self.flags, "BACKLOG-handoff-alpha.md"), "## Inference rows\n- [blocked] cpu rank=1 **row-x**\n")
        with patch.object(hs, "tmux", fake), patch.object(hs, "landed", return_value=True), patch.object(hs, "project_cwd", return_value=self.repo):
            reg, _ = hs.dispatch_once(self.flags, repo=self.repo)
        self.assertIn("h-alpha", windows)
        nw = [c for c in calls if c[0] == "new-window"]
        self.assertEqual(len(nw), 1)
        self.assertEqual(nw[0][:6], ("new-window", "-d", "-t", "agent:", "-n", "h-alpha"))
        self.assertEqual(reg["sessions"]["alpha"]["status"], "live")
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

    def test_dsh3_transient_error_retries_with_backoff_then_fails(self):
        e = self.session(pid=99999979)
        e["last_output"] = self.turn('{"type":"error","message":"stream disconnected before completion: 502 Bad Gateway"}\n', rc=1)
        hs.save(hs.reg_path(self.flags), self.reg)
        t0 = 1_800_000_000.0
        reg, _ = hs.dispatch_once(self.flags, runner=self.runner, repo=self.repo, now=t0)
        e = reg["sessions"]["alpha"]
        self.assertEqual((e["status"], e["transient_retries"]), ("retry", 1))
        self.assertIn("TRANSIENT alpha: rc=1 retry 1/3", self.log_text())
        self.assertEqual(self.calls, [], "not resumed before the backoff")
        with patch.object(hs, "landed", return_value=True), patch.object(hs, "project_cwd", return_value=self.repo):
            reg, _ = hs.dispatch_once(self.flags, runner=self.runner, repo=self.repo, now=t0 + 121)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("go on", self.calls[0]["prompt"])
        self.assertIn("retry 1/3", self.calls[0]["prompt"])
        for n in (2, 3):  # two more transient failures -> retries 2 and 3
            reg["sessions"]["alpha"].update({"pid": 99999979, "last_output": self.turn('{"type":"error","message":"connection reset"}\n', rc=1)})
            hs.save(hs.reg_path(self.flags), reg)
            reg, _ = hs.dispatch_once(self.flags, runner=self.runner, repo=self.repo, now=t0 + 1000 * n)
            self.assertEqual(reg["sessions"]["alpha"]["transient_retries"], n)
        reg["sessions"]["alpha"].update({"pid": 99999979, "last_output": self.turn('{"type":"error","message":"504 gateway timeout"}\n', rc=1)})
        hs.save(hs.reg_path(self.flags), reg)
        reg, _ = hs.dispatch_once(self.flags, runner=self.runner, repo=self.repo, now=t0 + 9000)
        self.assertEqual(reg["sessions"]["alpha"]["status"], "failed")
        self.assertIn("FAILED alpha: 3 transient retries exhausted", self.log_text())
        # the backlog shows the failed session
        data = bg.build(self.flags, os.path.join(self.repo, "handoffs/active/backlog-priority.json"), "nolog", sessions_path=hs.reg_path(self.flags))
        self.assertIn("[FAILED] session: 3 transient retries exhausted", bg.render("handoff-alpha", data))
        # PUSH_PROMPT only when a WRAPPED sha exists but has not landed
        e = self.session(pid=99999979, last_wrapup=None)
        e["last_output"] = self.turn('{"text":"no wrap-up line at all"}\n', rc=0)
        hs.save(hs.reg_path(self.flags), self.reg)
        self.calls.clear()
        with patch.object(hs, "landed", return_value=False):
            reg, _ = self.dispatch()
        self.assertNotEqual(reg["sessions"]["alpha"]["status"], "unpushed", "no sha -> nothing to push")
        self.assertFalse(any("NOT on origin/main" in c["prompt"] for c in self.calls))
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
        # a dry-run FAIL for an owned row resumes the session with the fix task (the session never polled for it)
        _w(os.path.join(self.flags, "dryrun", "row-a", "FAIL-1.json"), json.dumps({"reason": "no unit", "fix_task": "fix the result_path"}))
        reg, st = self.dispatch()
        self.assertIn("DRYRUN-RESULT row-a -> alpha", self.log_text())
        self.assertEqual(len(self.calls), 1)
        self.assertIn("Dry-run FAIL for your row `row-a`", self.calls[0]["prompt"])
        self.assertIn("fix the result_path", self.calls[0]["prompt"])
        # an awaited file: registered by the session, fires when it exists
        e = self.session(await_event=True)  # last turn was a no-op: only an event may resume it
        e["noop_reason"] = hs.work_state(self.flags, "alpha", e, self.repo)[1]
        hs.save(hs.reg_path(self.flags), self.reg)
        self.calls.clear()
        target = os.path.join(self.flags, "subagent-out.json")
        _w(hs.report_path(self.flags, "alpha").replace("report.json", "awaiting/sub1.json"), json.dumps({"path": target, "note": "sub-agent output"}))
        reg, st = self.dispatch()
        self.assertEqual(self.calls, [], "not before the file exists")
        target2 = os.path.join(self.flags, "subagent-out2.json")
        _w(hs.report_path(self.flags, "alpha").replace("report.json", "awaiting/sub2.json"), json.dumps({"path": target2, "note": "second"}))
        _w(target, "{}"); _w(target2, "{}")
        reg, st = self.dispatch()
        self.assertIn("AWAITED 2 file(s) -> alpha", self.log_text())
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
    def test_resume_gap_generalist_orphans_and_rotation(self):
        # 1. one non-filing resume per MIN_RESUME_GAP_S: a session resumed 1 min ago with open work is NOT resumed again
        e = self.session(last_resume=hs._dt.datetime.fromtimestamp(hs.time.time() - 60, hs._dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        reg, _ = self.dispatch()
        self.assertEqual([c for c in self.calls if "alpha" in c["prompt"] and "FINISH ALL READY ITEMS" in c["prompt"]], [])
        # ... but a run-end (filing) event still is
        _w(os.path.join(self.flags, "grants", "row-a.ended"), "rc=0\n")
        reg, _ = self.dispatch()
        self.assertTrue(any("row `row-a`" in c["prompt"] for c in self.calls))
        # 2. codex-gen: registered automatically, resumed on its own backlog (bypasses the cap), never yields
        self.reg["max_live"] = 1
        self.session(status="live", pid=os.getpid())
        _w(os.path.join(self.flags, "BACKLOG-codex-gen.md"), "## Inference rows\n- [blocked] cpu rank=3 **r-orphan** (row r-orphan) — yours (no handoff session)\n\n## Non-inference tasks\n\n- [S] handoffs/active/zed.md:10 — small fix\n")
        _w(os.path.join(self.flags, "GOAL-codex-gen.md"), "# GOAL\nGOAL-MARKER\n")
        self.calls.clear()
        with patch.object(hs, "alive", lambda pid: pid == os.getpid()):
            reg, _ = self.dispatch()
        g = reg["sessions"]["codex-gen"]
        self.assertEqual(g["status"], "live")
        self.assertIn("GOAL-MARKER", self.calls[0]["prompt"])
        self.assertIn("codex-gen backlog: 1 row fix(es), 0 filing(s), 1 small task(s)", self.log_text())
        self.assertFalse(g.get("yield"))
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
        self.assertEqual(self.calls[-1]["cmd"], ["codex", "exec", "--json", "-"], "the next resume was a FRESH session (rotation)")
        self.assertIn("brief", self.calls[-1]["prompt"].lower())
        self.assertIn("ROTATE alpha: per-call context 180000 > 150000", self.log_text())
