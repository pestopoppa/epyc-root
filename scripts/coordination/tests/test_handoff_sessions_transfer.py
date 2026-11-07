#!/usr/bin/env python3
"""Tests for handoff_sessions.py — the 2026-11-01 portability rulings.

Pinned here, each with a temp dir, a stubbed runner and a monkeypatched `landed`
(no network, no real engine, no git):

  1. TRANSFER FROM FILES ONLY. `transfer(slug, "claude")` hands the new engine a
     prompt that contains the brief, the handoff file, the newest progress file
     and the BACKLOG, says the old transcript is unavailable, and records
     engine=claude, a new session_id and `transferred_from` in the registry.
     A live previous session is refused unless force.
  2. UNWRAPPED GATE. A session whose `last_wrapup` is not landed is NOT resumed
     on an end event; the event stays queued and the log says UNWRAPPED.
  3. `WRAPPED <sha>` parsing: the LAST such line of the turn output becomes
     `last_wrapup`.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_COORD = Path(__file__).resolve().parents[1]
if str(_COORD) not in sys.path:
    sys.path.insert(0, str(_COORD))

import handoff_sessions as hs  # noqa: E402


def _w(p, txt):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(txt)


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.flags = os.path.join(self.td.name, "flags")
        self.repo = os.path.join(self.td.name, "repo")
        os.makedirs(self.flags)
        _w(os.path.join(self.flags, "budget.json"), '{"weekly_fraction": 0.1}')  # reserve admission fails closed without a meter
        self.slug = "yarn"
        self.handoff = "handoffs/active/yarn-context-extension-research.md"
        _w(os.path.join(self.repo, self.handoff), "# YaRN handoff\n- [ ] HANDOFF-TASK-MARKER do the sweep\n")
        _w(os.path.join(self.repo, "progress/2026-10/2026-10-30-handoff-yarn.md"), "OLD-PROGRESS-MARKER\n")
        time.sleep(0.01)
        _w(os.path.join(self.repo, "progress/2026-11/2026-11-01-handoff-yarn.md"), "NEW-PROGRESS-MARKER\n")
        _w(os.path.join(self.flags, "BACKLOG-handoff-yarn.md"), "## Inference\n- [blocked] BACKLOG-MARKER yarn-1 rank=1 **x**\n")
        self.reg = {"schema": "epyc.handoff-sessions.v1", "max_live": 5, "paused_until": None, "sessions": {
            self.slug: {"handoff": self.handoff, "engine": "codex", "session_id": "codex-thread-1",
                        "status": "suspended", "row_patterns": ["yarn"], "row_ids": ["yarn-1"],
                        "last_wrapup": "deadbeef1", "last_end": "2026-11-01T10:00:00Z", "pid": None}}}
        hs.save(hs.reg_path(self.flags), self.reg)
        # auto-start ranking inputs live beside the handoffs: empty here so nothing but the fixture session exists
        _w(os.path.join(self.repo, "handoffs/active/backlog-priority.json"), json.dumps({"rows": {}, "inference_prep": []}))
        _w(os.path.join(self.repo, "handoffs/active/.index-state.json"), json.dumps({"handoffs": {}, "rows": {}}))
        self.calls = []
        self._lane = patch.object(hs, "ensure_lane", lambda slug, repo=None: (self.repo, "fast-forwarded"))
        self._lane.start()
        self._disk = patch.object(hs, "free_gib", lambda path="/": 999.0)  # the real disk may be below the floor
        self._disk.start()
        self._cwd = patch.object(hs, "project_cwd", lambda e, repo=None: self.repo)  # the fixture repo is not a git clone
        self._cwd.start()

    def dispatch(self, **kw):
        return hs.dispatch_once(self.flags, runner=self.runner, repo=self.repo, **kw)


    def tearDown(self):
        self._lane.stop()
        self._disk.stop()
        self._cwd.stop()
        self.td.cleanup()

    def runner(self, cmd, prompt_file, out):
        """Stub engine: record the command and prompt, emit a claude-style session line, 'exit' at once."""
        self.calls.append({"cmd": cmd, "prompt": open(prompt_file).read(), "out": out})
        _w(out, '{"type":"system","session_id":"claude-sess-NEW"}\n')
        return 99999999, out  # pid that cannot be alive

    def log_text(self):
        try:
            return open(os.path.join(self.flags, "handoff-sessions.log")).read()
        except OSError:
            return ""


class TransferTests(_Fixture):
    def test_transfer_from_files_only(self):
        e = hs.transfer(self.flags, self.slug, "claude", runner=self.runner, repo=self.repo)
        self.assertEqual(len(self.calls), 1)
        c = self.calls[0]
        self.assertEqual(c["cmd"][:2], ["claude", "-p"])
        self.assertNotIn("--resume", c["cmd"], "transfer must start a FRESH session")
        p = c["prompt"]
        for marker in ("session-per-handoff brief", "HANDOFF-TASK-MARKER", "NEW-PROGRESS-MARKER", "BACKLOG-MARKER",
                       "transcript is UNAVAILABLE", "WRAPPED <sha>", "publish_row.py"):
            self.assertIn(marker, p)
        self.assertNotIn("OLD-PROGRESS-MARKER", p, "only the NEWEST progress file is handed over")
        reg = hs.load(hs.reg_path(self.flags), {})
        r = reg["sessions"][self.slug]
        self.assertEqual(r["engine"], "claude")
        self.assertEqual(r["session_id"], "claude-sess-NEW")
        self.assertEqual(e["session_id"], "claude-sess-NEW")
        self.assertEqual(r["transferred_from"][-1]["engine"], "codex")
        self.assertEqual(r["transferred_from"][-1]["session_id"], "codex-thread-1")
        self.assertIn("at", r["transferred_from"][-1])
        self.assertEqual(r["status"], "live")
        self.assertFalse(r.get("fresh_next"))
        self.assertTrue(os.path.exists(os.path.join(self.flags, "briefs", "HANDOFF-yarn.md")))
        self.assertIn("TRANSFER yarn -> claude", self.log_text())

    def test_transfer_refuses_live_session_unless_forced(self):
        self.reg["sessions"][self.slug]["pid"] = os.getpid()
        # G1 (2026-11-06): opencode has no built-in default model; the registry declares one or the spawn is refused
        self.reg["token_guards"] = {"default_model": {"opencode": "openai/gpt-6-luna"}, "default_effort": {"opencode": "medium"}}
        hs.save(hs.reg_path(self.flags), self.reg)
        with self.assertRaises(RuntimeError):
            hs.transfer(self.flags, self.slug, "opencode", runner=self.runner, repo=self.repo)
        self.assertEqual(self.calls, [])
        hs.transfer(self.flags, self.slug, "opencode", force=True, runner=self.runner, repo=self.repo)
        self.assertEqual(self.calls[0]["cmd"][:2], ["opencode", "run"])
        self.assertNotIn("-s", self.calls[0]["cmd"])

    def test_transfer_rejects_unknown_engine(self):
        with self.assertRaises(ValueError):
            hs.transfer(self.flags, self.slug, "gemini", runner=self.runner, repo=self.repo)


class UnwrappedGateTests(_Fixture):
    def test_end_event_waits_while_unwrapped_and_push_prompt_is_sent(self):
        _w(os.path.join(self.flags, "grants", "yarn-1.ended"), "rc=0\n")
        with patch.object(hs, "landed", return_value=False):
            reg, st = self.dispatch()
        self.assertEqual(len(self.calls), 1, "unwrapped: the PUSH prompt, never a park")
        self.assertIn("NOT on origin/main", self.calls[0]["prompt"])
        self.assertEqual([ev["rid"] for ev in st["queue"]], ["yarn-1"], "the run-end waits for the landed wrap-up")
        self.assertIn("UNWRAPPED yarn: PUSH prompt instead of new work; last_wrapup=deadbeef1", self.log_text())
        # once the wrap-up lands, the queued event is served
        with patch.object(hs, "landed", return_value=True):
            reg, st = self.dispatch()
        self.assertEqual(len(self.calls), 2)
        self.assertIn("row `yarn-1`", self.calls[1]["prompt"])
        self.assertIn("File the verdict yourself", self.calls[1]["prompt"])
        self.assertIn("filing-done/yarn-1.FILED", self.calls[1]["prompt"])
        self.assertEqual(st["queue"], [])

    def test_missing_wrapup_gets_push_prompt(self):
        self.reg["sessions"][self.slug]["last_wrapup"] = None
        hs.save(hs.reg_path(self.flags), self.reg)
        _w(os.path.join(self.flags, "grants", "yarn-1.ended"), "rc=0\n")
        with patch.object(hs, "landed", return_value=True):
            reg, st = self.dispatch()
        self.assertEqual(len(self.calls), 1)
        self.assertIn("NOT on origin/main", self.calls[0]["prompt"])
        self.assertEqual(len(st["queue"]), 1)
        self.assertIn("last_wrapup=None", self.log_text())


class WrappedParsingTests(_Fixture):
    def test_last_wrapped_line_sets_last_wrapup(self):
        out = os.path.join(self.flags, "handoff-sessions", "yarn", "turn.jsonl")
        _w(out, '{"text":"progress... WRAPPED 1111111aaaa"}\n{"text":"final: WRAPPED 83c110265331"}\n')
        self.reg["sessions"][self.slug].update({"pid": 99999999, "last_output": out, "status": "live"})
        hs.save(hs.reg_path(self.flags), self.reg)
        with patch.object(hs, "landed", return_value=True) as ld:
            reg, _ = self.dispatch()
        e = reg["sessions"][self.slug]
        self.assertEqual(e["last_wrapup"], "83c110265331")
        ld.assert_any_call("83c110265331")
        # token audit rec 2 (2026-11-06) supersedes "never parked": a no-op turn is no progress evidence -> hard park
        self.assertIn("NOOP yarn: turn completed nothing", self.log_text())
        self.assertIn("PARK yarn: no progress evidence", self.log_text())
        self.assertEqual(self.calls, [])
        hs.tg.unpark(reg["sessions"][self.slug])
        hs.save(hs.reg_path(self.flags), reg)
        with patch.object(hs, "landed", return_value=True):
            reg, _ = self.dispatch()
        e = reg["sessions"][self.slug]
        self.assertIn("OPEN yarn: next=unreported", self.log_text())
        self.assertEqual(e["status"], "live")
        self.assertEqual(len(self.calls), 1)
        p = self.calls[0]["prompt"]
        for marker in ("go on: next=unreported", "NEVER wait in this turn", hs.REPORT_LINE, "`blocked_by`", "priority order",
                       "A turn ends ONLY at one of", "Spend this turn on the task itself", "Progress = a box in YOUR handoff"):
            self.assertIn(marker, p)

    def test_legacy_wrapup_form_still_parsed(self):
        self.assertEqual(hs.WRAPPED_RX.findall("WRAPUP: abcdef0 then WRAPPED 1234567"), ["abcdef0", "1234567"])



class FanoutPolicyTests(unittest.TestCase):
    """Operator rule 2026-11-01: every launched session carries the subagent fan-out policy explicitly."""

    def test_brief_and_prompts_carry_fanout(self):
        import tempfile
        e = {"handoff": "handoffs/active/x.md", "engine": "codex", "row_ids": ["r1"], "row_patterns": [], "handoff_rows": ["INF-1"]}
        flags = tempfile.mkdtemp()
        for name, text in (("brief", hs.brief_text("x", e, flags)), ("end", hs.end_prompt("x", e, flags, "r1", flags + "/r1.ended")),
                           ("idle", hs.idle_prompt("x", e, flags)), ("continue", hs.continue_prompt("x", e, flags, "why"))):
            self.assertIn("FAN OUT", text, name)
            self.assertIn("at most 2 concurrent subagents", text, name)
            self.assertIn("OPERATING_CONSTRAINTS.md", text, name)
            self.assertIn(hs.REPORT_LINE, text, name)
        self.assertIn("## Working mode: fan out", hs.brief_text("x", e, flags))



class ProjectCwdTests(unittest.TestCase):
    """Operator rule 2026-11-01: a session is spawned only with cwd inside the project repo or one of its worktrees."""

    def test_repo_and_worktree_accepted_other_dirs_refused(self):
        import subprocess, tempfile
        repo = tempfile.mkdtemp()
        subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
        subprocess.run(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "x"], check=True)
        wt = tempfile.mkdtemp() + "/wt"
        subprocess.run(["git", "-C", repo, "worktree", "add", "-q", wt, "-b", "wt-lane"], check=True)
        self.assertEqual(hs.project_cwd({}, repo=repo), os.path.realpath(repo))
        self.assertEqual(hs.project_cwd({"cwd": wt}, repo=repo), os.path.realpath(wt))
        other = tempfile.mkdtemp()
        with self.assertRaises(ValueError):
            hs.project_cwd({"cwd": other}, repo=repo)
        other_repo = tempfile.mkdtemp()
        subprocess.run(["git", "-C", other_repo, "init", "-q"], check=True)
        with self.assertRaises(ValueError):
            hs.project_cwd({"cwd": other_repo}, repo=repo)
        # the dispatcher refuses to spawn and logs REFUSED-CWD instead of launching
        flags = tempfile.mkdtemp()
        calls = []
        def runner(cmd, pf, out, cwd=None):
            calls.append(cwd); return 1, out
        e = {"handoff": "handoffs/active/x.md", "engine": "codex", "cwd": other}
        hs.ROOT, old = repo, hs.ROOT
        try:
            with patch.object(hs, "ensure_lane", lambda slug, repo=None: (other, "created")):  # a lane outside the project
                hs._go(flags, "x", e, "p", runner, None, fresh=True)
            self.assertEqual(calls, [])
            self.assertIn("REFUSED-CWD", open(os.path.join(flags, "handoff-sessions.log")).read())
            e2 = {"handoff": "handoffs/active/x.md", "engine": "codex", "cwd": wt}
            with patch.object(hs, "ensure_lane", lambda slug, repo=None: (wt, "fast-forwarded")):
                hs._go(flags, "x", e2, "p", runner, None, fresh=True)
            self.assertEqual(calls, [os.path.realpath(wt)])
            self.assertEqual(e2["cwd"], wt)
            # a real lane on this fixture repo: created from origin/main, then fast-forwarded
            subprocess.run(["git", "-C", repo, "branch", "-M", "main"], check=True)
            subprocess.run(["git", "-C", repo, "remote", "add", "origin", repo], check=True)
            subprocess.run(["git", "-C", repo, "fetch", "-q", "origin"], check=True)
            with patch.object(hs, "LANES_DIR", tempfile.mkdtemp()):
                d, st = hs.ensure_lane("x", repo=repo)
                self.assertEqual((os.path.basename(d), st), ("h-x", "created"))
                self.assertEqual(subprocess.run(["git", "-C", d, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip(), "lane/h-x")
                self.assertEqual(hs.ensure_lane("x", repo=repo)[1], "fast-forwarded")
                self.assertEqual(hs.project_cwd({"cwd": d}, repo=repo), os.path.realpath(d))
        finally:
            hs.ROOT = old

if __name__ == "__main__":
    unittest.main()
