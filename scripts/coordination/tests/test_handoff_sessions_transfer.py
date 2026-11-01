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
        self.calls = []

    def tearDown(self):
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
    def test_end_event_not_resumed_while_unwrapped(self):
        _w(os.path.join(self.flags, "grants", "yarn-1.ended"), "rc=0\n")
        with patch.object(hs, "landed", return_value=False):
            reg, st = hs.dispatch_once(self.flags, runner=self.runner)
        self.assertEqual(self.calls, [], "no resume while last_wrapup is not landed")
        self.assertEqual([ev["rid"] for ev in st["queue"]], ["yarn-1"])
        e = reg["sessions"][self.slug]
        self.assertEqual(e["pending_event"]["rid"], "yarn-1")
        self.assertEqual(e["status"], "suspended")
        self.assertIn("UNWRAPPED yarn: refusing resume; last_wrapup=deadbeef1", self.log_text())
        # once the wrap-up lands, the queued event is served
        with patch.object(hs, "landed", return_value=True):
            reg, st = hs.dispatch_once(self.flags, runner=self.runner)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("row `yarn-1`", self.calls[0]["prompt"])
        self.assertIn("file the verdict yourself", self.calls[0]["prompt"])
        self.assertIn("filing-done/yarn-1.FILED", self.calls[0]["prompt"])
        self.assertEqual(st["queue"], [])

    def test_missing_wrapup_blocks_a_session_that_has_run(self):
        self.reg["sessions"][self.slug]["last_wrapup"] = None
        hs.save(hs.reg_path(self.flags), self.reg)
        _w(os.path.join(self.flags, "grants", "yarn-1.ended"), "rc=0\n")
        with patch.object(hs, "landed", return_value=True):
            reg, st = hs.dispatch_once(self.flags, runner=self.runner)
        self.assertEqual(self.calls, [])
        self.assertEqual(len(st["queue"]), 1)
        self.assertIn("last_wrapup=None", self.log_text())


class WrappedParsingTests(_Fixture):
    def test_last_wrapped_line_sets_last_wrapup(self):
        out = os.path.join(self.flags, "handoff-sessions", "yarn", "turn.jsonl")
        _w(out, '{"text":"progress... WRAPPED 1111111aaaa"}\n{"text":"final: WRAPPED 83c110265331"}\n')
        self.reg["sessions"][self.slug].update({"pid": 99999999, "last_output": out, "status": "live"})
        hs.save(hs.reg_path(self.flags), self.reg)
        with patch.object(hs, "landed", return_value=True) as ld:
            reg, _ = hs.dispatch_once(self.flags, runner=self.runner)
        e = reg["sessions"][self.slug]
        self.assertEqual(e["last_wrapup"], "83c110265331")
        self.assertEqual(e["status"], "suspended")
        self.assertIsNone(e["pid"])
        ld.assert_any_call("83c110265331")

    def test_legacy_wrapup_form_still_parsed(self):
        self.assertEqual(hs.WRAPPED_RX.findall("WRAPUP: abcdef0 then WRAPPED 1234567"), ["abcdef0", "1234567"])


if __name__ == "__main__":
    unittest.main()
