#!/usr/bin/env python3
"""Tests for alarm_channel — dedupe state machine, delivery, loud failures.

Stdlib unittest only (no pytest dependency); pytest also discovers it.
Every test runs against a temp state file + temp record file via the module's
env overrides, so nothing under coordination/session-bus/ is ever written.

CONTAINS A MUTATION CHECK (``TestDedupeMutation``). The dedupe assertion is the
load-bearing one — "exactly ONE alarm" is the Phase 0 gate — and an assertion
that has never failed has not been shown to test anything. That test class
imports a MUTATED copy of the module with the suppression branch disabled and
requires the dedupe assertion to FAIL against it. A mutation the suite survives
is reported as a defect of this suite, not as a pass.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_COORD = Path(__file__).resolve().parents[1]
if str(_COORD) not in sys.path:
    sys.path.insert(0, str(_COORD))

import alarm_channel as ac  # noqa: E402

MODULE_PATH = _COORD / "alarm_channel.py"
REPO_CONFIG = _COORD.parents[1] / "coordination" / "session-bus" / "alarm_config.yaml"


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def events(path: Path, event: str, key: str | None = None) -> list[dict]:
    return [r for r in read_records(path)
            if r.get("event") == event and (key is None or r.get("key") == key)]


class ChannelTestCase(unittest.TestCase):
    """Base: a sandboxed channel on the `file` backend."""

    module = ac

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.state = self.tmp / "state.json"
        self.record = self.tmp / "alarms.jsonl"
        self.cfg = {
            "schema_version": ac.SCHEMA_CONFIG,
            "enabled": True,
            "backend": "file",
            "advisory_mirror": False,
            "file": {"path": str(self.record)},
            "_config_path": "<test>",
        }
        self._old_env = os.environ.get("ALARM_STATE_PATH")
        os.environ["ALARM_STATE_PATH"] = str(self.state)

    def tearDown(self):
        if self._old_env is None:
            os.environ.pop("ALARM_STATE_PATH", None)
        else:
            os.environ["ALARM_STATE_PATH"] = self._old_env
        self._tmp.cleanup()

    def raise_(self, key="fleet-absent", severity="critical", message="msg", evidence=None, **kw):
        return self.module.raise_alarm(key, severity, message, evidence, cfg=self.cfg,
                                       state_file=self.state, **kw)

    def clear_(self, key="fleet-absent", message=None, **kw):
        return self.module.clear_alarm(key, message, cfg=self.cfg, state_file=self.state, **kw)


# ── the gate property: emit once on state change ───────────────────────────
class TestDedupe(ChannelTestCase):

    def test_five_raises_deliver_once(self):
        """THE Phase 0 gate: 5 raises of one key == exactly ONE delivery."""
        for i in range(5):
            self.raise_(evidence={"tick": i})
        self.assertEqual(len(events(self.record, "raised", "fleet-absent")), 1,
                         "a repeated alarm must notify exactly once")

    def test_first_raise_reports_notified_rest_suppressed(self):
        self.assertEqual(self.raise_()["action"], "notified")
        for _ in range(4):
            self.assertEqual(self.raise_()["action"], "suppressed")

    def test_suppressed_raises_are_counted_not_discarded(self):
        for i in range(5):
            self.raise_(evidence={"tick": i})
        entry = json.loads(self.state.read_text())["active"]["fleet-absent"]
        self.assertEqual(entry["count"], 5)
        self.assertEqual(entry["evidence"]["tick"], 4, "latest evidence must win")
        self.assertEqual(entry["notified_at"], entry["raised_at"],
                         "notified_at must not advance on a suppressed raise")

    def test_distinct_keys_each_deliver(self):
        self.raise_(key="fleet-absent")
        self.raise_(key="runner-dead")
        self.assertEqual(len(events(self.record, "raised")), 2)

    def test_reraise_after_clear_delivers_again(self):
        self.raise_()
        self.clear_()
        self.raise_()
        self.assertEqual(len(events(self.record, "raised", "fleet-absent")), 2,
                         "dedupe is a state machine, not a permanent mute")


class TestClear(ChannelTestCase):

    def test_clear_notifies_once(self):
        self.raise_()
        res = self.clear_()
        self.assertEqual(res["action"], "notified")
        self.assertEqual(len(events(self.record, "cleared", "fleet-absent")), 1)

    def test_clear_of_inactive_key_is_silent(self):
        res = self.clear_(key="never-raised")
        self.assertEqual(res["action"], "not-active")
        self.assertEqual(events(self.record, "cleared"), [])

    def test_double_clear_delivers_once(self):
        self.raise_()
        self.clear_()
        self.clear_()
        self.assertEqual(len(events(self.record, "cleared", "fleet-absent")), 1)

    def test_clear_removes_from_active_and_records_history(self):
        self.raise_()
        self.raise_()
        self.clear_()
        state = json.loads(self.state.read_text())
        self.assertNotIn("fleet-absent", state["active"])
        self.assertEqual(state["recent_resolved"][-1]["count"], 2)

    def test_status_reports_active(self):
        self.raise_(key="a")
        self.raise_(key="b", severity="warning")
        st = self.module.status(self.state)
        self.assertEqual(sorted(st["active"]), ["a", "b"])
        self.clear_(key="a")
        self.assertEqual(sorted(self.module.status(self.state)["active"]), ["b"])


# ── delivery: always recorded, failures loud ───────────────────────────────
class TestDelivery(ChannelTestCase):

    def test_record_is_written_before_outcome_is_known(self):
        self.raise_()
        raised = events(self.record, "raised")[0]
        self.assertEqual(raised["delivery"], "pending",
                         "the first record may only claim what has happened so far")
        result = events(self.record, "delivery-result")[0]
        self.assertEqual(result["delivery"], "ok")

    def test_unreachable_backend_still_records_and_shouts(self):
        cfg = dict(self.cfg, backend="ntfy",
                   ntfy={"url": "http://127.0.0.1:1/unreachable", "timeout_s": 2})
        res = self.module.raise_alarm("backend-down", "critical", "boom",
                                      cfg=cfg, state_file=self.state)
        self.assertEqual(res["event"]["delivery"], "failed")
        self.assertEqual(len(events(self.record, "raised", "backend-down")), 1,
                         "a failed push must never cost the local record")
        fails = events(self.record, "delivery-failed", "backend-down")
        self.assertEqual(len(fails), 1, "the failure must itself be an event")
        self.assertIn("NO HUMAN WAS PAGED", fails[0]["message"])
        self.assertEqual(fails[0]["severity"], "critical")

    def test_unknown_backend_is_a_failure_not_a_silent_skip(self):
        cfg = dict(self.cfg, backend="carrier-pigeon")
        res = self.module.raise_alarm("k", "warning", "m", cfg=cfg, state_file=self.state)
        self.assertEqual(res["event"]["delivery"], "failed")
        self.assertEqual(len(events(self.record, "delivery-failed", "k")), 1)

    def test_placeholder_endpoint_never_touches_the_network(self):
        cfg = dict(self.cfg, backend="ntfy",
                   ntfy={"url": f"https://ntfy.sh/{ac.PLACEHOLDER_SENTINEL}-topic"})

        def explode(*a, **kw):  # any network attempt is a test failure
            raise AssertionError("the placeholder endpoint must not be contacted")

        orig = ac.PUSH_BACKENDS["ntfy"]
        ac.PUSH_BACKENDS["ntfy"] = explode
        try:
            res = self.module.raise_alarm("ph", "warning", "m", cfg=cfg, state_file=self.state)
        finally:
            ac.PUSH_BACKENDS["ntfy"] = orig
        self.assertEqual(res["event"]["delivery"], "skipped_not_live")
        self.assertEqual(len(events(self.record, "raised", "ph")), 1)

    def test_disabled_channel_still_records_locally(self):
        cfg = dict(self.cfg, enabled=False, backend="ntfy",
                   ntfy={"url": "https://ntfy.sh/real-topic"})

        def explode(*a, **kw):
            raise AssertionError("a disabled channel must not be contacted")

        orig = ac.PUSH_BACKENDS["ntfy"]
        ac.PUSH_BACKENDS["ntfy"] = explode
        try:
            res = self.module.raise_alarm("dis", "critical", "m", cfg=cfg, state_file=self.state)
        finally:
            ac.PUSH_BACKENDS["ntfy"] = orig
        self.assertEqual(res["event"]["delivery"], "skipped_disabled")
        self.assertEqual(len(events(self.record, "raised", "dis")), 1)

    def test_dry_run_writes_nothing(self):
        self.raise_(dry_run=True)
        self.assertFalse(self.record.exists())
        self.assertFalse(self.state.exists())

    def test_ntfy_request_shape(self):
        """The ntfy backend must set Title/Priority and POST the body."""
        captured = {}

        class FakeResp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["headers"] = {k.lower(): v for k, v in req.header_items()}
            captured["body"] = req.data.decode("utf-8")
            return FakeResp()

        orig = ac.urllib.request.urlopen
        ac.urllib.request.urlopen = fake_urlopen
        try:
            cfg = dict(self.cfg, backend="ntfy",
                       ntfy={"url": "https://ntfy.example/topic", "priority_critical": "urgent"})
            res = self.module.raise_alarm("fleet-absent", "critical", "0 live mains",
                                          {"live_mains": 0}, cfg=cfg, state_file=self.state)
        finally:
            ac.urllib.request.urlopen = orig
        # Guard against passing for the wrong reason: the captured values are set
        # before the request is issued, so this must ALSO have delivered cleanly.
        self.assertEqual(res["event"]["delivery"], "ok", res["event"].get("delivery_error"))
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://ntfy.example/topic")
        self.assertEqual(captured["headers"]["priority"], "urgent")
        self.assertIn("fleet-absent", captured["headers"]["title"])
        self.assertIn("0 live mains", captured["body"])
        self.assertIn("live_mains: 0", captured["body"])

    def test_http_error_code_is_a_failure(self):
        class FakeResp:
            status = 503

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        orig = ac.urllib.request.urlopen
        ac.urllib.request.urlopen = lambda req, timeout=None: FakeResp()
        try:
            cfg = dict(self.cfg, backend="ntfy", ntfy={"url": "https://ntfy.example/topic"})
            res = self.module.raise_alarm("http-err", "critical", "m",
                                          cfg=cfg, state_file=self.state)
        finally:
            ac.urllib.request.urlopen = orig
        self.assertEqual(res["event"]["delivery"], "failed")
        self.assertIn("503", res["event"]["delivery_error"])


# ── validation + state robustness ──────────────────────────────────────────
class TestValidation(ChannelTestCase):

    def test_bad_severity_rejected(self):
        with self.assertRaises(ValueError):
            self.raise_(severity="apocalyptic")

    def test_key_with_whitespace_rejected(self):
        with self.assertRaises(ValueError):
            self.raise_(key="fleet absent")

    def test_corrupt_state_is_quarantined_not_ignored(self):
        self.state.write_text("{not json", encoding="utf-8")
        self.raise_()
        quarantined = list(self.tmp.glob("state.json.corrupt-*"))
        self.assertEqual(len(quarantined), 1,
                         "a corrupt state file must be preserved, not overwritten")

    def test_state_survives_a_round_trip(self):
        self.raise_(evidence={"a": 1})
        reloaded = json.loads(self.state.read_text())
        self.assertEqual(reloaded["schema_version"], ac.SCHEMA_STATE)
        self.assertIn("fleet-absent", reloaded["active"])


class TestConfigParser(unittest.TestCase):

    def test_nested_scalars_comments_and_types(self):
        cfg = ac.parse_simple_yaml(
            "# leading comment\n"
            "schema_version: alarm_channel.config.v1\n"
            "enabled: true\n"
            "advisory_mirror: false\n"
            "\n"
            "ntfy:\n"
            "  url: https://ntfy.sh/topic-a7f3   # trailing comment\n"
            "  timeout_s: 10\n"
            "  priority_critical: 'urgent'\n"
            "file:\n"
            "  path: /tmp/alarms.jsonl\n"
        )
        self.assertIs(cfg["enabled"], True)
        self.assertIs(cfg["advisory_mirror"], False)
        self.assertEqual(cfg["ntfy"]["url"], "https://ntfy.sh/topic-a7f3")
        self.assertEqual(cfg["ntfy"]["timeout_s"], 10)
        self.assertEqual(cfg["ntfy"]["priority_critical"], "urgent")
        self.assertEqual(cfg["file"]["path"], "/tmp/alarms.jsonl")

    def test_sequences_raise_rather_than_vanish(self):
        with self.assertRaises(ValueError):
            ac.parse_simple_yaml("keys:\n  - a\n  - b\n")

    def test_json_body_is_accepted(self):
        cfg = ac.parse_simple_yaml('{"backend": "file", "enabled": true}')
        self.assertEqual(cfg["backend"], "file")

    def test_shipped_repo_config_parses_and_is_not_live(self):
        self.assertTrue(REPO_CONFIG.exists(), f"missing shipped config {REPO_CONFIG}")
        cfg = ac.parse_simple_yaml(REPO_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(cfg["schema_version"], ac.SCHEMA_CONFIG)
        self.assertIs(cfg["enabled"], True)
        self.assertEqual(cfg["backend"], "ntfy")
        self.assertIn(ac.PLACEHOLDER_SENTINEL, cfg["ntfy"]["url"],
                      "the shipped config must ship with a placeholder endpoint")

    def test_missing_config_falls_back_to_builtin_defaults(self):
        cfg = ac.load_config(Path("/nonexistent/alarm_config.yaml"))
        self.assertEqual(cfg["backend"], "ntfy")
        self.assertIn(ac.PLACEHOLDER_SENTINEL, cfg["ntfy"]["url"])

    def test_pyyaml_agrees_with_the_hand_rolled_parser(self):
        """If pyyaml is installed, the two parsers must agree on the shipped config.

        The hand-rolled parser exists so the alarm path has zero non-stdlib
        import surface, not because the config is a private dialect.
        """
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("pyyaml not importable")
        text = REPO_CONFIG.read_text(encoding="utf-8")
        self.assertEqual(ac.parse_simple_yaml(text), yaml.safe_load(text))


class TestCLI(ChannelTestCase):
    """The CLI is what the daemon and the drill actually call."""

    def _run(self, *args, config=None):
        env = dict(os.environ)
        env["ALARM_STATE_PATH"] = str(self.state)
        env["ALARM_FILE_PATH"] = str(self.record)
        env["ALARM_BACKEND"] = "file"
        if config:
            env["ALARM_CONFIG_PATH"] = str(config)
        return subprocess.run([sys.executable, str(MODULE_PATH), *args],
                              capture_output=True, text=True, env=env, timeout=60)

    def test_raise_status_clear_round_trip(self):
        r = self._run("raise", "--severity", "critical", "--key", "fleet-absent",
                      "--message", "0 live mains")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("notified", r.stdout)

        r = self._run("raise", "--severity", "critical", "--key", "fleet-absent",
                      "--message", "0 live mains")
        self.assertEqual(r.returncode, 0)
        self.assertIn("suppressed", r.stdout)

        r = self._run("status")
        self.assertIn("fleet-absent", r.stdout)

        r = self._run("clear", "--key", "fleet-absent")
        self.assertIn("RESOLVED", r.stdout)

        r = self._run("status")
        self.assertIn("active alarms: none", r.stdout)
        self.assertEqual(len(events(self.record, "raised", "fleet-absent")), 1)

    def test_bad_evidence_json_is_a_usage_error(self):
        r = self._run("raise", "--severity", "warning", "--key", "k",
                      "--message", "m", "--evidence", "not-json")
        self.assertEqual(r.returncode, ac.EXIT_USAGE)

    def test_evidence_must_be_an_object(self):
        r = self._run("raise", "--severity", "warning", "--key", "k",
                      "--message", "m", "--evidence", "[1,2]")
        self.assertEqual(r.returncode, ac.EXIT_USAGE)

    def test_unreachable_backend_exits_3(self):
        cfg = self.tmp / "fail.yaml"
        cfg.write_text(
            "schema_version: alarm_channel.config.v1\n"
            "enabled: true\n"
            "backend: ntfy\n"
            "ntfy:\n"
            "  url: http://127.0.0.1:1/unreachable\n"
            "  timeout_s: 3\n"
            f"file:\n  path: {self.record}\n", encoding="utf-8")
        env = dict(os.environ)
        env["ALARM_STATE_PATH"] = str(self.state)
        env["ALARM_CONFIG_PATH"] = str(cfg)
        env.pop("ALARM_BACKEND", None)
        env.pop("ALARM_FILE_PATH", None)
        r = subprocess.run([sys.executable, str(MODULE_PATH), "raise", "--severity", "critical",
                            "--key", "down", "--message", "m"],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, ac.EXIT_DELIVERY_FAILED)
        self.assertIn("DELIVERY FAILED", r.stderr)

    def test_test_subcommand_is_repeatable(self):
        """`test` must deliver every time — it self-clears, so dedupe cannot mute it."""
        for _ in range(3):
            r = self._run("test")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("DELIVERED", r.stdout)
        self.assertEqual(len(events(self.record, "raised", "alarm-channel-selftest")), 3)
        r = self._run("status")
        self.assertIn("active alarms: none", r.stdout,
                      "`test` must not leave a self-test alarm active")

    def test_dry_run_cli_writes_nothing(self):
        r = self._run("--dry-run", "raise", "--severity", "critical", "--key", "k",
                      "--message", "m")
        self.assertEqual(r.returncode, 0)
        self.assertIn("DRY RUN", r.stdout)
        self.assertFalse(self.record.exists())
        self.assertFalse(self.state.exists())


class TestDrillScript(unittest.TestCase):
    """The Phase 0 gate script must itself pass, and be safe to run."""

    def test_drill_passes(self):
        drill = Path(__file__).resolve().parent / "alarm_drill.sh"
        self.assertTrue(drill.exists())
        r = subprocess.run(["bash", str(drill)], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("RESULT: PASS", r.stdout)

    def test_drill_does_no_process_management(self):
        """A shared host: the drill must contain no kill/pkill/systemctl."""
        text = (Path(__file__).resolve().parent / "alarm_drill.sh").read_text(encoding="utf-8")
        body = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
        for forbidden in ("pkill", "pgrep", "systemctl", "kill "):
            self.assertNotIn(forbidden, body,
                             f"the drill must never do process management ({forbidden!r})")


# ── MUTATION CHECK ─────────────────────────────────────────────────────────
def _load_mutant(name: str, source: str, tmpdir: Path):
    path = tmpdir / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class TestDedupeMutation(ChannelTestCase):
    """Proves the dedupe assertions above are not vacuous.

    Method: take alarm_channel.py, disable the suppression branch by an EXACT
    literal replacement that must match exactly once (a rotted pattern is a
    defect, not a silent skip), import the mutant, and require the dedupe
    assertions to FAIL against it. A mutation the suite survives means the
    dedupe test is checking nothing.
    """

    MUTATIONS = {
        # 1. the suppression branch never fires -> every raise notifies
        "no_suppression": ("        if existing:\n", "        if False:  # MUTANT\n"),
        # 2. state is never persisted -> every process/call starts blank
        "no_state_write": ("            _write_state(sp, state)\n            return {\"action\": \"suppressed\"",
                           "            pass  # MUTANT\n            return {\"action\": \"suppressed\""),
    }

    @staticmethod
    def _silent_run(suite):
        """Run a suite with its output discarded (and the sink actually closed)."""
        with open(os.devnull, "w", encoding="utf-8") as sink:
            return unittest.TextTestRunner(stream=sink, verbosity=0).run(suite)

    def _mutate(self, name):
        src = MODULE_PATH.read_text(encoding="utf-8")
        frm, to = self.MUTATIONS[name]
        self.assertEqual(src.count(frm), 1,
                         f"mutation {name!r} must match EXACTLY once (matched {src.count(frm)}) — "
                         "the pattern has rotted; fix the mutation, do not skip it")
        return _load_mutant(f"alarm_channel_mutant_{name}", src.replace(frm, to), self.tmp)

    def test_dedupe_assertion_fails_without_the_suppression_branch(self):
        self.module = self._mutate("no_suppression")
        for i in range(5):
            self.raise_(evidence={"tick": i})
        n = len(events(self.record, "raised", "fleet-absent"))
        self.assertEqual(n, 5, "sanity: the mutant should notify on every raise")
        with self.assertRaises(AssertionError, msg=(
                "MUTATION SURVIVED: the dedupe test passes with dedupe removed, "
                "so it asserts nothing. This suite is defective.")):
            self.assertEqual(n, 1)

    def test_run_real_dedupe_test_against_the_mutant(self):
        """Run the ACTUAL test method (not a paraphrase) against the mutant.

        A hand-written restatement of the assertion could drift from the real
        one; this re-binds TestDedupe.test_five_raises_deliver_once to the
        mutated module and requires that exact test to fail.
        """
        mutant = self._mutate("no_suppression")

        class MutatedDedupe(TestDedupe):
            module = mutant

        result = self._silent_run(
            unittest.TestLoader().loadTestsFromName(
                "test_five_raises_deliver_once", MutatedDedupe))
        self.assertEqual(len(result.failures) + len(result.errors), 1,
                         "MUTATION SURVIVED: test_five_raises_deliver_once passed against a "
                         "module with dedupe removed — the Phase 0 gate test is vacuous.")

    def test_pristine_module_passes_the_same_test(self):
        """Control: without the control case, a suite broken for an unrelated
        reason would 'catch' every mutation and score perfectly while testing
        nothing."""
        result = self._silent_run(
            unittest.TestLoader().loadTestsFromName(
                "test_five_raises_deliver_once", TestDedupe))
        self.assertEqual(len(result.failures) + len(result.errors), 0,
                         "the pristine module must PASS the dedupe test")

    def test_state_persistence_mutation_is_caught(self):
        mutant = self._mutate("no_state_write")

        class MutatedCount(TestDedupe):
            module = mutant

        result = self._silent_run(
            unittest.TestLoader().loadTestsFromName(
                "test_suppressed_raises_are_counted_not_discarded", MutatedCount))
        self.assertEqual(len(result.failures) + len(result.errors), 1,
                         "MUTATION SURVIVED: dropping the suppressed-raise state write did not "
                         "fail the occurrence-count test.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
