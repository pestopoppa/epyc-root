#!/usr/bin/env python3
"""Token guards G1-G5 (operator 2026-11-06, token-efficiency audit recs 1-5): each guard has a positive test and a
negative control (the guard must NOT fire when its condition is absent)."""
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
sys.path.insert(0, str(_COORD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import codex_budget_meter as meter  # noqa: E402
import handoff_sessions as hs  # noqa: E402
import token_guards as tg  # noqa: E402

CAT = {"gpt-6-luna": ["low", "medium", "high", "xhigh", "max"], "gpt-6.1-terra": ["low", "medium", "high", "xhigh", "max", "ultra"]}


class G1ModelEffort(unittest.TestCase):
    def test_default_is_cheap_not_terra_high(self):
        r = tg.resolve_spawn("codex", {}, "", (), tg.DEFAULTS, CAT)
        self.assertEqual((r["model"], r["effort"]), ("gpt-6-luna", "medium"))
        self.assertEqual(r["source"], {"model": "default", "effort": "default"})

    def test_precedence_row_over_handoff_over_registry(self):
        text = "# H\n**Model**: gpt-6.1-terra\n- effort: high\n"
        r = tg.resolve_spawn("codex", {"model": "gpt-6-luna", "effort": "low"}, text, [{"id": "r1", "effort": "xhigh"}], tg.DEFAULTS, CAT)
        self.assertEqual((r["model"], r["effort"]), ("gpt-6.1-terra", "xhigh"))
        self.assertEqual(r["source"], {"model": "handoff", "effort": "row:r1"})

    def test_refuses_unknown_model_bad_effort_or_no_catalog(self):
        with self.assertRaises(tg.SpawnRefused):
            tg.resolve_spawn("codex", {"model": "gpt-9-imaginary"}, "", (), tg.DEFAULTS, CAT)
        with self.assertRaises(tg.SpawnRefused):
            tg.resolve_spawn("codex", {"effort": "ultra"}, "", (), tg.DEFAULTS, CAT)  # luna has no ultra
        with self.assertRaises(tg.SpawnRefused):
            tg.resolve_spawn("codex", {}, "", (), tg.DEFAULTS, None)
        with self.assertRaises(tg.SpawnRefused):
            tg.resolve_spawn("opencode", {}, "", (), tg.DEFAULTS, None)  # no opencode default

    def test_engine_cmd_pins_model_effort_and_plan_mode(self):
        fresh = hs.engine_cmd("codex", None, True, "gpt-6-luna", "low")
        resume = hs.engine_cmd("codex", "T1", False, "gpt-6-luna", "low")
        for c in (fresh, resume):
            self.assertEqual(c[c.index("-m") + 1], "gpt-6-luna")
            self.assertIn('model_reasoning_effort="low"', c)
            self.assertIn('plan_mode_reasoning_effort="low"', c)
        self.assertEqual(resume[:3] + resume[-2:], ["codex", "exec", "resume", "T1", "-"])
        self.assertIn("--effort", hs.engine_cmd("claude", "S", False, "sonnet", "medium"))

    def test_negative_control_no_unpinned_command_exists(self):
        with self.assertRaises(tg.SpawnRefused):
            hs.engine_cmd("codex", None, True)


class G2LeaseResumeQuota(unittest.TestCase):
    def test_ceiling_and_lease_fire(self):
        now = 1_800_000_000.0
        self.assertIn("ceiling", tg.lease_verdict({}, {"total_tokens": 20_000_000}, now, now, tg.DEFAULTS))
        self.assertIn("lease", tg.lease_verdict({}, {"total_tokens": 1}, now, now - 6000, tg.DEFAULTS))

    def test_negative_control_lease_quiet_within_limits(self):
        now = 1_800_000_000.0
        self.assertIsNone(tg.lease_verdict({}, {"total_tokens": 1_000_000}, now, now - 600, tg.DEFAULTS))
        self.assertIsNone(tg.lease_verdict({}, None, now, 0, tg.DEFAULTS))

    def test_resume_needs_progress_and_caps_count(self):
        now = 1_800_000_000.0
        self.assertFalse(tg.resume_verdict({"noop_turns": 1}, now)[0])
        e = {"noop_turns": 0}
        for _ in range(tg.DEFAULTS["max_resumes"]):
            self.assertTrue(tg.resume_verdict(e, now)[0])
            tg.note_resume(e, now)
        ok, why = tg.resume_verdict(e, now)
        self.assertFalse(ok)
        self.assertIn("max_resumes", why)
        self.assertTrue(tg.resume_verdict(e, now + 86401)[0], "negative control: the 24 h window rolls")

    def test_park_is_hard_until_unpark(self):
        e = {}
        tg.park(e, "x", "t")
        self.assertFalse(tg.resume_verdict(e, 0)[0])
        tg.unpark(e)
        self.assertTrue(tg.resume_verdict(e, 0)[0])

    def test_quota_until_uses_resets_at_never_30_min(self):
        now = 1_800_000_000.0
        self.assertEqual(tg.quota_until(now, {"resets_at": now + 9999}), (now + 9999, "budget.json resets_at"))
        t, _ = tg.quota_until(now, None)
        self.assertGreaterEqual(t - now, 6 * 3600)

    def test_kill_pid_never_kills_self(self):
        self.assertFalse(tg.kill_pid(os.getpid()))
        self.assertFalse(tg.kill_pid(1))


class G3Meter(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.flags = os.path.join(self.td.name, "flags")
        self.root = os.path.join(self.td.name, "sessions")
        os.makedirs(self.flags)
        os.makedirs(os.path.join(self.root, "2026", "11", "06"))
        self.f = os.path.join(self.root, "2026", "11", "06", "rollout-x-T1.jsonl")
        self.now = time.time()

    def tearDown(self):
        self.td.cleanup()

    def event(self, ts, pct, inp=1000, out=10, reached=None):
        rec = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(ts)), "type": "event_msg",
               "payload": {"type": "token_count", "info": {"last_token_usage": {"input_tokens": inp, "output_tokens": out},
                                                           "total_token_usage": {"total_tokens": inp + out}},
                           "rate_limits": {"primary": {"used_percent": pct, "window_minutes": 10080, "resets_at": self.now + 2 * 86400},
                                           "rate_limit_reached_type": reached}}}
        with open(self.f, "a") as fh:
            fh.write(json.dumps(rec) + "\n")

    def test_sums_alarms_and_pauses_when_exhausted(self):
        sent = []
        emit = lambda *a, **k: sent.append(a[3])
        self.event(self.now - 60, 40.0)
        b = meter.compute(self.flags, now=self.now, codex_root=self.root, notify=emit)
        self.assertEqual(b["weekly_fraction"], 0.4)
        self.assertEqual(b["tokens_last_1h"], 1010)
        self.assertEqual(sent, [], "negative control: 40 % raises no alarm")
        self.assertIsNone(b["paused_until"])
        self.event(self.now - 30, 85.0)
        b = meter.compute(self.flags, now=self.now, codex_root=self.root, notify=emit)
        self.assertEqual(b["tokens_last_1h"], 2020, "incremental: the first line is not counted twice")
        self.assertEqual(b["alarms"], [0.5, 0.8])
        self.event(self.now - 10, 100.0, reached="primary")
        b = meter.compute(self.flags, now=self.now, codex_root=self.root, notify=emit)
        self.assertEqual(b["paused_until"], b["resets_at"])
        self.assertTrue(os.path.exists(os.path.join(self.flags, "budget.json")))

    def test_dry_run_writes_nothing(self):
        self.event(self.now - 60, 90.0)
        meter.compute(self.flags, now=self.now, codex_root=self.root, write=False, notify=lambda *a, **k: self.fail("alerted"))
        self.assertEqual(os.listdir(self.flags), [])

    def test_dispatcher_honours_paused_until(self):
        now = 1_800_000_000.0
        self.assertEqual(tg.budget_paused_until({"paused_until": now + 10}, now), now + 10)
        self.assertEqual(tg.budget_paused_until({"paused_until": now - 10}, now), 0.0, "negative control: past pause")


class G4Rotation(unittest.TestCase):
    def test_threshold_default_and_configurable(self):
        self.assertTrue(tg.rotate_verdict(60_001))
        self.assertFalse(tg.rotate_verdict(59_999), "negative control")
        self.assertFalse(tg.rotate_verdict(None), "negative control: unknown context")
        self.assertFalse(tg.rotate_verdict(90_000, tg.cfg({"token_guards": {"context_rotate_tokens": 100_000}})))

    def test_checkpoint_carries_next_step(self):
        cp = tg.checkpoint_from({"next": "inference", "next_step": "publish row r2", "box": "B3", "wrapped_sha": "abc1234"},
                                {"handoff": "h.md", "session_id": "T1"})
        blk = tg.checkpoint_block(cp)
        self.assertIn("publish row r2", blk)
        self.assertIn("T1", blk)
        self.assertEqual(tg.checkpoint_block(None), "")


class G5Width(unittest.TestCase):
    def test_default_cap_is_two_and_budget_derives_lower(self):
        now = 1_800_000_000.0
        self.assertEqual(tg.width_cap(tg.cfg({}), None, now)[0], 2)
        tight = {"weekly_fraction": 0.9, "resets_at": now + 10 * 3600, "burn_frac_per_h": 0.02}
        self.assertEqual(tg.width_cap(tg.cfg({}), tight, now, live=2)[0], 1)  # 0.01/h allowed / 0.01 per session
        self.assertEqual(tg.width_cap(tg.cfg({}), dict(tight, paused_until=now + 5), now)[0], 0)

    def test_negative_control_ample_budget_keeps_cap(self):
        now = 1_800_000_000.0
        ample = {"weekly_fraction": 0.1, "resets_at": now + 24 * 3600, "burn_frac_per_h": 0.01}
        self.assertEqual(tg.width_cap(tg.cfg({"max_live": 5}), ample, now, live=1)[0], 3)  # derived 3.75 -> 3
        self.assertEqual(tg.width_cap(tg.cfg({}), ample, now, live=1)[0], 2)

    def test_fanout_line_says_at_most_two(self):
        self.assertIn("at most 2 concurrent subagents", hs.FANOUT_LINE)
        self.assertNotIn("3-5", hs.FANOUT_LINE)


class DryRun(unittest.TestCase):
    def test_plan_reports_spawn_and_park_without_writing(self):
        with tempfile.TemporaryDirectory() as flags:
            reg = {"sessions": {"a": {"engine": "codex", "session_id": "no-such-thread-a", "noop_turns": 0},
                                "b": {"engine": "codex", "session_id": "no-such-thread-b", "noop_turns": 2},
                                "c": {"engine": "opencode"}}}
            with patch.object(hs, "alive", lambda pid: False):
                plan = hs.guard_plan(flags, reg, now=1_800_000_000.0, repo=flags, catalog=CAT, budget={})
            rows = {r.get("slug"): r for r in plan}
            self.assertEqual(rows[None]["guard"] if None in rows else "width", "width")
            self.assertEqual(rows["a"]["would"], "RESUME-ELIGIBLE")
            self.assertIn("gpt-6-luna", rows["a"]["cmd"])
            self.assertTrue(rows["b"]["would"].startswith("PARK"))
            self.assertTrue(rows["c"]["would"].startswith("REFUSE-SPAWN"))
            self.assertEqual(os.listdir(flags), [], "dry run writes nothing")
            self.assertNotIn("parked", reg["sessions"]["b"], "dry run mutates nothing")


if __name__ == "__main__":
    unittest.main()
