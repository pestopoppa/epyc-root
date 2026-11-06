"""Dispatcher quota model (keeper-friction-review refinement 6, operator 2026-11-05): per-engine pause until the parsed
reset time, 30m/2h/6h backoff when unparseable, one alert per pause, filing never gated, uncompilable script refused."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

_COORD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_COORD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import handoff_sessions as hs  # noqa: E402
from test_handoff_sessions_transfer import _Fixture, _w  # noqa: E402

CODEX_MSG = "You've hit your usage limit. Upgrade to Pro or try again at Nov 11th, 2026 7:36 AM."


def local_epoch(y, mo, d, h, mi):
    return time.mktime((y, mo, d, h, mi, 0, 0, 0, -1))


class ParseTests(unittest.TestCase):
    def test_codex_absolute(self):
        now = local_epoch(2026, 11, 5, 12, 0)
        self.assertEqual(hs.parse_reset(CODEX_MSG, now), local_epoch(2026, 11, 11, 7, 36))

    def test_codex_relative_and_claude_shapes(self):
        now = 1_800_000_000.0
        self.assertEqual(hs.parse_reset("try again in 3 hours 20 minutes", now), now + 3 * 3600 + 20 * 60)
        self.assertEqual(hs.parse_reset("Claude AI usage limit reached|1800003600", now), 1_800_003_600)
        t = hs.parse_reset("5-hour limit reached ∙ resets 3pm (UTC)", now)
        self.assertTrue(now < t <= now + 86400 and time.gmtime(t).tm_hour == 15)

    def test_unparseable_or_implausible_is_none(self):
        self.assertIsNone(hs.parse_reset("rate limit exceeded", 1_800_000_000.0))
        self.assertIsNone(hs.parse_reset("try again at Jan 1st, 2020 1:00 AM", 1_800_000_000.0))


class PauseTests(_Fixture):
    def test_weekly_limit_sets_paused_until_reset_for_that_engine_only(self):
        now = local_epoch(2026, 11, 5, 12, 0)
        reg = {}
        until = hs.record_usage_limit(self.flags, reg, "codex", CODEX_MSG, now)
        self.assertEqual(hs._parse(until), local_epoch(2026, 11, 11, 7, 36) // 1)
        self.assertEqual(reg["engine_pause"]["codex"]["kind"], "weekly")
        self.assertTrue(hs.engine_paused(reg, "codex", now + 3600))
        self.assertFalse(hs.engine_paused(reg, "claude", now + 3600))
        self.assertFalse(hs.engine_paused(reg, "opencode", now + 3600))
        self.assertIsNone(reg.get("paused_until"))

    def test_unknown_reset_backs_off_6h_12h_24h_never_30m(self):
        # token audit rec 2 (2026-11-06): no 30-minute retry loop; a 24 h quiet gap resets the streak
        reg, t, got = {}, 1_800_000_000.0, []
        for i in range(4):
            d = hs._parse(hs.record_usage_limit(self.flags, reg, "codex", "rate limit", t)) - t
            got.append(d)
            t += d + 60  # each hit lands after the previous pause ended
        self.assertEqual(got, [21600, 43200, 86400, 21600])
        self.assertNotIn(1800, got)

    def test_unknown_reset_waits_for_budget_meter_resets_at(self):
        now = 1_800_000_000.0
        with open(os.path.join(self.flags, "budget.json"), "w") as f:
            json.dump({"resets_at": now + 3 * 86400}, f)
        reg = {}
        until = hs.record_usage_limit(self.flags, reg, "codex", "rate limit", now)
        self.assertEqual(hs._parse(until), int(now + 3 * 86400))
        self.assertEqual(reg["engine_pause"]["codex"]["kind"], "budget-meter")

    def test_alert_once_naming_reset(self):
        now = local_epoch(2026, 11, 5, 12, 0)
        reg = {}
        for k in range(3):  # three sessions die on the same quota
            hs.record_usage_limit(self.flags, reg, "codex", CODEX_MSG, now + k)
        alerts = [json.loads(l) for l in open(os.path.join(self.flags, "rowflow-alerts.jsonl"))]
        self.assertEqual(len(alerts), 1)
        self.assertIn(reg["engine_pause"]["codex"]["until"], alerts[0]["summary"])
        self.assertEqual(alerts[0]["severity"], "critical")

    def test_reap_pauses_codex_not_dispatcher(self):
        out = os.path.join(self.flags, "turn.out")
        _w(out, json.dumps({"type": "error", "message": CODEX_MSG}) + "\n")
        reg = hs.load(hs.reg_path(self.flags), {})
        reg["sessions"][self.slug].update(pid=99999999, last_output=out)
        hs.save(hs.reg_path(self.flags), reg)
        reg, _ = self.dispatch()
        self.assertIn("codex", reg["engine_pause"])
        self.assertIsNone(reg.get("paused_until"))
        self.assertIn("engine codex paused until 2026-11-11", self.log_text())


class FilingTests(_Fixture):
    def test_paused_dispatcher_still_files_and_does_not_resume(self):
        reg = hs.load(hs.reg_path(self.flags), {})
        reg["engine_pause"] = {"codex": {"until": "2099-01-01T00:00:00Z"}}
        hs.save(hs.reg_path(self.flags), reg)
        st = {"seen": [], "queue": [{"slug": self.slug, "rid": "yarn-1", "kind": "end", "end": "rc=0"}]}
        hs.save(hs.state_path(self.flags), st)
        filed_calls = []
        with patch.object(hs, "file_result", lambda f, rid, lane: filed_calls.append(rid) or (0, "TICK x")):
            _, st = self.dispatch()
        self.assertEqual(filed_calls, ["yarn-1"])
        self.assertEqual(self.calls, [], "no engine turn while its quota is paused")
        self.assertEqual(len(st["queue"]), 1, "the owner still gets the event after the reset")

    def test_quota_transfer_default_off(self):
        reg = {"engine_pause": {"codex": {"until": "2099-01-01T00:00:00Z"}}, "sessions": {}}
        e = {"engine": "codex", "handoff": "h.md", "pid": None, "_work": ("continue", "next=docs")}
        self.assertEqual(hs.quota_transfer_plan(reg, {"s": e}, time.time()), [])
        reg["quota_transfer"] = True
        self.assertEqual(hs.quota_transfer_plan(reg, {"s": e}, time.time()), [("s", "claude")])
        e["_work"] = ("continue", "next=inference")
        self.assertEqual(hs.quota_transfer_plan(reg, {"s": e}, time.time()), [])


class CompileGuardTests(unittest.TestCase):
    def test_uncompilable_script_is_refused(self):
        d = tempfile.mkdtemp()
        bad = os.path.join(d, "handoff_sessions.py")
        _w(bad, "import os\n!def awaiting_prompt():\n    pass\n")
        r = subprocess.run([sys.executable, str(_COORD / "handoff_sessions.py"), "compile-check", bad], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3)
        self.assertIn("SYNTAX-FAIL", r.stdout)
        ok, _ = hs.compile_ok(str(_COORD / "handoff_sessions.py"))
        self.assertTrue(ok)
        with self.assertRaises(SystemExit):
            hs.preflight(bad)


if __name__ == "__main__":
    unittest.main()
