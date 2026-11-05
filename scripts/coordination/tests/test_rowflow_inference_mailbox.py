#!/usr/bin/env python3
"""The inference mailbox (operator 2026-11-05; incident npd1-step3-20261105 unseen for 80 min).
Pinned: every alert lands once in <flags>/notify/inbox/inference.jsonl with owner/handoff_task/publisher; acks are
append-only and idempotent; `rowflow.py alerts` filters; the keeper escalates an unacked CRITICAL alert exactly once;
the dispatcher injects a session's unacked alerts into its prompt and wakes a non-running owner on a critical one.
Temp dirs and fakes only: no bus, no engine, no git."""
import contextlib
import datetime as dt
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_COORD, "rowflow"))
sys.path.insert(0, _COORD)
import notify  # noqa: E402
import rowflow as rf  # noqa: E402
import handoff_sessions as hs  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="rowflow-mailbox-")
        self.flags = os.path.join(self.root, "flags")
        os.makedirs(os.path.join(self.flags, "ready"))
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("ROWFLOW_BUS_ROOT", None)

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def ready(self, rid, owner="handoff-npd1", task="handoffs/active/npd1.md: step 3", pub=None):
        with open(os.path.join(self.flags, "ready", rid + ".json"), "w") as f:
            json.dump({"id": rid, "owner": owner, "handoff_task": task,
                       "publisher": pub or {"agent_id": None, "session": "sess-A", "user": "node"}}, f)

    def inbox(self):
        p = notify.inbox_path(self.flags)
        return [json.loads(x) for x in open(p)] if os.path.exists(p) else []

    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rf.main(["--flags", self.flags, "alerts", *args])
        return rc, out.getvalue()


class Mailbox(Base):
    def test_alert_lands_once_with_metadata(self):
        self.ready("npd1-step3")
        notify.row_ended(self.flags, "npd1-step3", "rc=1 time=2026-11-05T07:43:00Z reason=job-rc-1")
        notify.row_ended(self.flags, "npd1-step3", "rc=1 time=2026-11-05T07:43:00Z reason=job-rc-1")
        ib = self.inbox()
        self.assertEqual(len(ib), 1)
        r = ib[0]
        self.assertEqual((r["owner"], r["severity"], r["reason"], r["row_id"]), ("handoff-npd1", "critical", "job-rc-1", "npd1-step3"))
        self.assertEqual(r["publisher"]["session"], "sess-A")
        self.assertIn("npd1.md", r["handoff_task"])
        self.assertEqual(r["key"], json.loads(open(os.path.join(self.flags, "rowflow-alerts.jsonl")).readline())["key"])

    def test_premailbox_marker_not_backfilled(self):
        key = notify.event_key("row-ended", "old", "t")
        notify._write_json(notify._marker(self.flags, key), {"record": {"key": key, "kind": "row-ended", "row_owner": "x",
                           "severity": "info", "ts": "2026-11-04T00:00:00Z", "summary": "s"}, "bus": "skipped: x"})
        notify.emit(self.flags, "row-ended", "old", "t", "s", "info")
        self.assertEqual(self.inbox(), [])

    def test_ack_and_cli_filters(self):
        self.ready("a-1"); self.ready("b-1")
        notify.row_ended(self.flags, "a-1", "rc=1 time=T1 reason=job-rc-1")
        notify.smoke_fail(self.flags, "b-1", "/x/FAIL-1.json", {"reason": "boom"})
        keys = [r["key"] for r in self.inbox()]
        rc, out = self.cli("--unacked")
        self.assertEqual((rc, out.count("OPEN")), (0, 2))
        self.assertEqual(self.cli("--ack", keys[0])[0], 0)
        self.assertEqual(self.cli("--ack", keys[0])[0], 0)
        self.assertEqual(len(open(notify.acks_path(self.flags)).readlines()), 1)
        self.assertEqual(self.cli("--ack", "nope")[0], 2)
        rc, out = self.cli("--unacked", "--json")
        self.assertEqual([json.loads(x)["row_id"] for x in out.splitlines()], ["b-1"])
        rc, out = self.cli("--row", "a-*")
        self.assertIn("ACKED", out)
        self.assertEqual(self.cli("--since", "2999-01-01T00:00:00Z")[1], "")

    def test_publisher_info_env(self):
        p = notify.publisher_info({"WRAPUP_AGENT_ID": "mainB", "CODEX_THREAD_ID": "th-9", "USER": "u"})
        self.assertEqual((p["agent_id"], p["agent_id_env"], p["session"], p["session_env"]), ("mainB", "WRAPUP_AGENT_ID", "th-9", "CODEX_THREAD_ID"))
        p = notify.publisher_info({})
        self.assertIsNone(p["agent_id"]); self.assertIsNone(p["session"])


class Escalation(Base):
    def test_critical_unacked_escalates_exactly_once(self):
        self.ready("c-1")
        notify.row_ended(self.flags, "c-1", "rc=1 time=T reason=job-rc-1")
        notify.smoke_fail(self.flags, "c-1", "/x/FAIL-1.json", {"reason": "w"})  # warning: never escalated
        calls = []
        route = lambda k, m, ev: calls.append((k, ev["key"])) or True
        t0 = dt.datetime.now(dt.timezone.utc)
        self.assertEqual(notify.escalate_stale(self.flags, route, now=t0, after_s=1800, log=lambda *_: None), [])
        later = t0 + dt.timedelta(minutes=31)
        self.assertEqual(len(notify.escalate_stale(self.flags, route, now=later, after_s=1800, log=lambda *_: None)), 1)
        self.assertEqual(notify.escalate_stale(self.flags, route, now=later, after_s=1800, log=lambda *_: None), [])
        self.assertEqual(len(calls), 1)
        kinds = [json.loads(x)["kind"] for x in open(os.path.join(self.flags, "rowflow-alerts.jsonl"))]
        self.assertEqual(kinds.count("alert-unacked"), 1)

    def test_acked_never_escalates(self):
        self.ready("c-2")
        notify.row_ended(self.flags, "c-2", "rc=1 time=T reason=job-rc-1")
        notify.ack(self.flags, self.inbox()[0]["key"], by="t")
        later = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)
        self.assertEqual(notify.escalate_stale(self.flags, lambda *a: True, now=later, log=lambda *_: None), [])


class Dispatcher(Base):
    def setUp(self):
        super().setUp()
        self.ready("npd1-step3", owner="npd1", task="handoffs/active/npd1-program.md: step 3")
        notify.row_ended(self.flags, "npd1-step3", "rc=1 time=T reason=job-rc-1")
        self.ready("other-1", owner="someone-else", task="handoffs/active/other.md: x")
        notify.row_ended(self.flags, "other-1", "rc=1 time=T reason=job-rc-1")

    def test_matching(self):
        e = {"handoff": "handoffs/active/npd1-program.md"}
        self.assertEqual([a["row_id"] for a in hs.session_alerts(self.flags, "npd1-program", e)], ["npd1-step3"])
        self.assertEqual([a["row_id"] for a in hs.session_alerts(self.flags, "zzz", {"session_id": "sess-A"})],
                         ["npd1-step3", "other-1"])  # publisher session match
        self.assertEqual(hs.session_alerts(self.flags, "zzz", {"handoff": "handoffs/active/zzz.md"}), [])

    def test_go_injects_block_and_never_acks(self):
        seen = {}
        def fake_launch(flags, slug, e, prompt, fresh=False, runner=None):
            seen["prompt"] = prompt
            return 4242, "/dev/null"
        e = {"handoff": "handoffs/active/npd1-program.md"}
        with mock.patch.object(hs, "ensure_lane", return_value=(self.root, "ok")), \
             mock.patch.object(hs, "_git", return_value=mock.Mock(returncode=1, stdout="")), \
             mock.patch.object(hs, "scratch_lead", return_value=""), \
             mock.patch.object(hs, "launch", side_effect=fake_launch), mock.patch.object(hs, "log"):
            hs._go(self.flags, "npd1-program", e, "BODY", None, None)
        self.assertTrue(seen["prompt"].startswith("UNHANDLED ROW ALERTS"))
        self.assertIn("npd1-step3", seen["prompt"]); self.assertNotIn("other-1", seen["prompt"])
        self.assertEqual(len(e["alerts_injected"]), 1)
        self.assertFalse(os.path.exists(notify.acks_path(self.flags)))

    def test_alert_wake_rules(self):
        now = dt.datetime.now(dt.timezone.utc).timestamp()
        e = {"handoff": "handoffs/active/npd1-program.md", "status": "idle"}
        self.assertTrue(hs.alert_wake(self.flags, "npd1-program", e, now))
        self.assertFalse(hs.alert_wake(self.flags, "npd1-program", dict(e, status="done"), now))
        self.assertFalse(hs.alert_wake(self.flags, "npd1-program", dict(e, alert_wake_at=hs.now_iso()), now))
        with mock.patch.object(hs, "alive", return_value=True):
            self.assertFalse(hs.alert_wake(self.flags, "npd1-program", dict(e, pid=1), now))
        notify.ack(self.flags, hs.session_alerts(self.flags, "npd1-program", e)[0]["key"], by="t")
        self.assertFalse(hs.alert_wake(self.flags, "npd1-program", e, now))


if __name__ == "__main__":
    unittest.main()
