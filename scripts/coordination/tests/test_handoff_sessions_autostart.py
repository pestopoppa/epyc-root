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

    def tearDown(self):
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
        self.assertEqual(sorted(S), ["mid", "zed"], S.keys())
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
        reg, _ = self.dispatch()
        S = reg["sessions"]
        self.assertEqual(S["finished"]["status"], "done")
        self.assertIn("DONE finished: no open tasks left in handoffs/active/closed.md", self.log_text())
        self.assertEqual(S["waiting"]["status"], "suspended", "a suspended session is left alone")
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
        self.assertEqual(reg["sessions"], {})
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
