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


if __name__ == "__main__":
    unittest.main()
