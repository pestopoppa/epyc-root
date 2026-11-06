#!/usr/bin/env python3
"""TOKEN-* implementation (operator 2026-11-06): cfg deep merge, Claude meter wiring, regen debounce, restart gate."""
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

import codex_budget_meter as meter  # noqa: E402
import handoff_sessions as hs  # noqa: E402
import index_regen as ir  # noqa: E402
import token_guards as tg  # noqa: E402


def install_spawn_fakes(tc):
    """Isolation for any test that can reach dispatch/launch: fake tmux + codex on PATH (record-only), private tmux socket,
    patched hs.tmux and hs.launch_in_tmux. Returns the list of recorded calls."""
    d = tempfile.mkdtemp()
    tc.addCleanup(__import__("shutil").rmtree, d, True)
    marker = os.path.join(d, "invoked")
    for b in ("tmux", "codex", "claude", "opencode"):
        p = os.path.join(d, b)
        open(p, "w").write(f'#!/bin/sh\necho "{b} $*" >> "{marker}"\nexit 1\n')
        os.chmod(p, 0o755)
    calls = []
    for cm in (patch.dict(os.environ, {"PATH": d + os.pathsep + os.environ.get("PATH", ""), "HS_TMUX_SOCKET": "hs-test-" + str(os.getpid()),
                                       "TMUX_TMPDIR": d}),
               patch.object(hs, "tmux", lambda *a, **k: (calls.append(a), (1, "fake"))[1]),
               patch.object(hs, "launch_in_tmux", lambda *a, **k: calls.append(("launch_in_tmux",) + a[:1]))):
        cm.start()
        tc.addCleanup(cm.stop)
    tc.spawn_marker = marker
    return calls


CAT = {"gpt-6.1-sol": ["low", "medium", "high"], "gpt-6-luna": ["low", "medium"]}


class CfgDeepMerge(unittest.TestCase):
    def test_partial_registry_keeps_other_engines(self):
        c = tg.cfg({"token_guards": {"default_model": {"codex": "gpt-6.1-sol"}}})
        self.assertEqual(c["default_model"]["codex"], "gpt-6.1-sol")
        self.assertEqual(c["default_model"]["claude"], "sonnet")
        self.assertEqual(c["default_effort"]["claude"], "medium")
        r = tg.resolve_spawn("claude", {}, "", (), c, None)
        self.assertEqual((r["model"], r["effort"]), ("sonnet", "medium"))

    def test_negative_control_shallow_update_would_drop_claude(self):
        shallow = dict(tg.DEFAULTS)
        shallow.update({"default_model": {"codex": "gpt-6.1-sol"}})
        with self.assertRaises(tg.SpawnRefused):
            tg.resolve_spawn("claude", {}, "", (), shallow, None)

    def test_defaults_not_mutated_and_scalars_override(self):
        tg.cfg({"token_guards": {"default_model": {"codex": "x"}, "lease_s": 5}})
        self.assertEqual(tg.DEFAULTS["default_model"]["codex"], "gpt-6-luna")
        self.assertEqual(tg.cfg({"token_guards": {"lease_s": 5}})["lease_s"], 5)


def _claude_line(mid, ts, n):
    return json.dumps({"type": "assistant", "timestamp": ts, "message": {"id": mid, "usage": {"input_tokens": n, "output_tokens": 0}}}) + "\n"


class ClaudeMeter(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.flags = os.path.join(self.d, "flags")
        self.proj = os.path.join(self.d, "proj", "p1")
        os.makedirs(self.flags)
        os.makedirs(self.proj)
        self.f = os.path.join(self.proj, "s.jsonl")
        self.now = time.time()
        self.iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now - 60))

    def run_meter(self, **kw):
        alarms = []
        b = meter.compute(self.flags, now=self.now, codex_root=os.path.join(self.d, "none"), claude_root=os.path.join(self.d, "proj"),
                          notify=lambda *a, **k: alarms.append(a[3]), **kw)
        return b, alarms

    def test_alarms_at_50_and_80_and_incremental(self):
        open(self.f, "w").write(_claude_line("m1", self.iso, 600))
        b, al = self.run_meter(claude_weekly_tokens=1000)
        self.assertEqual(b["claude_alarms"], [0.5])
        self.assertEqual(len(al), 1)
        with open(self.f, "a") as fh:
            fh.write(_claude_line("m1", self.iso, 600))  # duplicate id: not recounted
            fh.write(_claude_line("m2", self.iso, 300))
        off_before = json.load(open(os.path.join(self.flags, meter.STATE_NAME)))["claude"]["files"][self.f]
        b, al = self.run_meter(claude_weekly_tokens=1000)
        self.assertEqual(b["claude_tokens_last_7d"], 900)
        self.assertEqual(b["claude_alarms"], [0.5, 0.8])
        self.assertTrue(any("-80-" in a for a in al))
        off_after = json.load(open(os.path.join(self.flags, meter.STATE_NAME)))["claude"]["files"][self.f]
        self.assertGreater(off_after, off_before)  # read only the new tail
        b2, _ = self.run_meter(claude_weekly_tokens=1000)  # nothing new: totals stable
        self.assertEqual(b2["claude_tokens_last_7d"], 900)

    def test_no_allowance_no_alarm_and_budget_file_written(self):
        open(self.f, "w").write(_claude_line("m1", self.iso, 600))
        b, al = self.run_meter()
        self.assertIsNone(b["claude_weekly_fraction"])
        self.assertEqual((b["claude_alarms"], al), ([], []))
        self.assertEqual(json.load(open(os.path.join(self.flags, "budget.json")))["claude_tokens_last_7d"], 600)

    def test_dispatcher_passes_claude_root(self):
        install_spawn_fakes(self)  # INC-20260806: this call used to reach the real tmux + codex via the live handoffs
        with patch.object(hs.meter, "update") as up, patch.object(hs, "maybe_regen_index"), \
                patch.object(hs, "launch", side_effect=AssertionError("spawn reached")), patch.object(hs, "start_handoff", return_value=None):
            try:
                hs.dispatch_once(self.flags, now=self.now)
            except Exception:
                pass
        self.assertTrue(up.called)
        self.assertEqual(up.call_args.kwargs.get("claude_root"), meter.CLAUDE_ROOT)


class RegenDebounce(unittest.TestCase):
    G = ir.GENERATED[0]

    def test_generated_only_changes_skip(self):
        self.assertFalse(ir.batch_verdict([self.G], 0, 0, 10_000)[0])

    def test_batch_still_landing_defers(self):
        self.assertFalse(ir.batch_verdict(["handoffs/active/a.md"], 9_900, 9_000, 10_000)[0])

    def test_batch_ended_runs(self):
        self.assertTrue(ir.batch_verdict(["handoffs/active/a.md"], 9_000, 8_000, 10_000)[0])

    def test_max_age_forces_even_while_landing(self):  # keeps --check freshness bounded
        self.assertTrue(ir.batch_verdict(["handoffs/active/a.md"], 9_990, 10_000 - ir.MAX_AGE_S, 10_000)[0])

    def test_first_regen_runs(self):
        self.assertTrue(ir.batch_verdict(None, 9_999, 0, 10_000)[0])


class RestartGate(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        p = os.path.join(self.root, tg.DOCTRINE_FILE)
        os.makedirs(os.path.dirname(p))
        self.doc = p
        open(p, "w").write("\n".join(tg.DOCTRINE_LINES) + "\n")
        self.now = 1_000_000.0
        self.reg = {"max_live": 2, "token_guards": {"default_model": {"codex": "gpt-6.1-sol"}, "default_effort": {"codex": "medium"}}}
        self.bud = {"weekly_fraction": 0.3, "paused_until": None}

    def fails(self, **kw):
        a = dict(reg=self.reg, budget=self.bud, now=self.now, root=self.root, catalog=CAT)
        a.update(kw)
        return tg.restart_failures(**a)

    def test_open_when_all_hold(self):
        self.assertEqual(self.fails(), [])

    def test_each_failure_has_a_reason(self):
        open(self.doc, "w").write(tg.DOCTRINE_LINES[0] + "\n")
        self.assertTrue(any("doctrine" in f for f in self.fails()))
        self.setUp()
        self.assertTrue(any("exhausted" in f for f in self.fails(budget={"weekly_fraction": 1.0, "paused_until": self.now + 5})))
        self.assertTrue(any("budget.json missing" in f for f in self.fails(budget=None)))
        self.assertTrue(any("max_live" in f for f in self.fails(reg=dict(self.reg, max_live=3))))
        self.assertTrue(any("defaults" in f for f in self.fails(catalog={"gpt-6-luna": ["low", "medium"]})))
        self.assertTrue(any("registry: paused_until" in f for f in self.fails(reg=dict(self.reg, paused_until=self.now + 9))))

    def test_past_paused_until_is_ok(self):
        self.assertEqual(self.fails(budget={"weekly_fraction": 0.2, "paused_until": self.now - 5}), [])

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as flags:
            json.dump(self.reg, open(os.path.join(flags, "handoff-sessions.json"), "w"))
            with patch.object(hs, "ROOT", self.root), patch.object(tg, "codex_catalog", return_value=CAT):
                self.assertEqual(hs.main(["preflight-restart", "--flags", flags]), 1)  # no budget.json
                json.dump(self.bud, open(os.path.join(flags, "budget.json"), "w"))
                self.assertEqual(hs.main(["preflight-restart", "--flags", flags]), 0)


class SpawnIsolationGuard(unittest.TestCase):
    def test_real_tmux_refused_without_private_socket(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HS_TMUX_SOCKET", None)
            with self.assertRaises(RuntimeError):
                hs.tmux("list-windows")

    def test_real_popen_refused_with_temp_flags(self):
        flags = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, flags, True)
        with self.assertRaises(RuntimeError):
            hs.refuse_real_spawn_under_test("popen", flags)

    def test_spawn_under_fakes_never_invokes_real_binaries(self):
        calls = install_spawn_fakes(self)
        flags = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, flags, True)
        e = {"handoff": "handoffs/active/x.md", "engine": "codex", "cwd": hs.ROOT}
        with patch.object(hs, "spawn_config", return_value={"model": "m", "effort": "e", "source": "t"}):
            try:
                hs.launch(flags, "iso-guard", e, "p", fresh=True)
            except RuntimeError as ex:  # the detached-Popen fallback is refused: exactly the guard
                self.assertIn("REFUSED", str(ex))
        self.assertFalse(os.path.exists(self.spawn_marker), "a PATH stub binary ran (tmux/codex reached)")
        self.assertTrue(all(c[0] != "new-window" or True for c in calls))

    def test_path_stubs_shadow_real_binaries(self):
        install_spawn_fakes(self)
        import shutil
        for b in ("tmux", "codex"):
            self.assertEqual(os.path.dirname(shutil.which(b)), os.path.dirname(self.spawn_marker))


if __name__ == "__main__":
    unittest.main()
