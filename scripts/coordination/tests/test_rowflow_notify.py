#!/usr/bin/env python3
"""Push notification for rowflow terminal events (incident 2026-11-04: a disk-floor kill went unseen for 3 h).
Covers notify.py (row-ended, smoke-fail, disk-floor hysteresis, idempotency, bus routing against a temp bus),
rowflow.record_fail's hook and filler_run15.sh's write_ended hook. Temp dirs only; the live bus is never written."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RF = os.path.join(_COORD, "rowflow")
_ROOT = os.path.dirname(os.path.dirname(_COORD))
sys.path.insert(0, _RF)
import notify  # noqa: E402
import rowflow as rf  # noqa: E402


def alerts(flags):
    p = os.path.join(flags, "rowflow-alerts.jsonl")
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="rowflow-notify-")
        self.flags = os.path.join(self.root, "flags")
        os.makedirs(os.path.join(self.flags, "ready"))
        os.makedirs(os.path.join(self.flags, "grants"))
        with open(os.path.join(self.flags, "ready", "r1.json"), "w") as f:
            json.dump({"id": "r1", "owner": "ws58"}, f)
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("ROWFLOW_BUS_ROOT", None)

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.root, ignore_errors=True)


class RowEnded(Base):
    ENDED = "rc=75 time=2026-11-04T20:04:09Z reason=disk-floor\njob_id=r1\nowner=ws58\nstarted=2026-11-04T19:54:13Z\n"

    def test_disk_floor_end_is_critical_and_idempotent(self):
        notify.row_ended(self.flags, "r1", self.ENDED)
        notify.row_ended(self.flags, "r1", self.ENDED)
        a = alerts(self.flags)
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["severity"], "critical")
        self.assertEqual(a[0]["row_owner"], "ws58")
        self.assertIn("NOT COMPLETE", a[0]["summary"])
        self.assertEqual(a[0]["detail"]["reason"], "disk-floor")

    def test_complete_is_info(self):
        notify.row_ended(self.flags, "r1", "rc=0 time=2026-11-04T01:00:00Z reason=complete\n")
        self.assertEqual(alerts(self.flags)[0]["severity"], "info")

    def test_highlighted_reasons(self):
        for r in ("hard-end", "job-rc-3:exited", "cleanup-failed", "disk-floor"):
            self.assertEqual(notify.severity_of(r), "critical", r)
        self.assertEqual(notify.severity_of("complete"), "info")

    def test_non_live_flags_never_touch_the_bus(self):
        with mock.patch.object(notify.subprocess, "run") as run:
            m = notify.row_ended(self.flags, "r1", self.ENDED)
        run.assert_not_called()
        self.assertTrue(m["bus"].startswith("skipped:"))

    def test_bus_message_against_temp_bus(self):
        bus = os.path.join(self.root, "bus")
        shutil.copytree(os.path.join(_ROOT, "coordination", "session-bus"), bus,
                        ignore=shutil.ignore_patterns("outbox", "inbox", "archive", "*.jsonl", "claims", "tasks", "tokens"))
        os.environ["ROWFLOW_BUS_ROOT"] = bus
        os.environ["ROWFLOW_SESSION_BUS"] = os.path.join(_COORD, "session_bus.py")
        m = notify.row_ended(self.flags, "r1", self.ENDED)
        self.assertTrue(m["bus"].startswith("sent:inference:"), m["bus"])  # ws58 is not a roster id -> resource owner
        rows = [json.loads(x) for x in open(os.path.join(bus, "outbox", "rowflow-keeper.jsonl"))]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["assignee"], "inference")
        self.assertEqual(rows[0]["kind"], "defect")
        self.assertEqual(rows[0]["payload"]["row_owner"], "ws58")
        notify.row_ended(self.flags, "r1", self.ENDED)   # repeat: no second message
        self.assertEqual(len(open(os.path.join(bus, "outbox", "rowflow-keeper.jsonl")).readlines()), 1)

    def test_autokernel_owner_routes_to_its_roster_identity(self):
        bus = os.path.join(self.root, "bus")
        shutil.copytree(os.path.join(_ROOT, "coordination", "session-bus"), bus,
                        ignore=shutil.ignore_patterns("outbox", "inbox", "archive", "*.jsonl", "claims", "tasks", "tokens"))
        os.environ["ROWFLOW_BUS_ROOT"] = bus
        os.environ["ROWFLOW_SESSION_BUS"] = os.path.join(_COORD, "session_bus.py")
        m = notify.row_ended(self.flags, "r1", self.ENDED.replace("owner=ws58", "owner=autokernel"))
        self.assertTrue(m["bus"].startswith("sent:autokernel:"), m["bus"])   # 2026-11-19: the owner roster id, no stale alias

    def test_failed_bus_send_is_retried_once_it_works(self):
        os.environ["ROWFLOW_BUS_ROOT"] = os.path.join(self.root, "nobus")
        os.environ["ROWFLOW_SESSION_BUS"] = os.path.join(self.root, "missing.py")
        m = notify.row_ended(self.flags, "r1", self.ENDED)
        self.assertTrue(m["bus"].startswith("failed"))
        with mock.patch.object(notify, "_bus_send", return_value="sent:x:y") as s:
            m = notify.row_ended(self.flags, "r1", self.ENDED)
            notify.row_ended(self.flags, "r1", self.ENDED)
        self.assertEqual(s.call_count, 1)
        self.assertEqual(m["bus"], "sent:x:y")
        self.assertEqual(len(alerts(self.flags)), 1)


class SmokeFail(Base):
    def test_record_fail_pushes(self):
        rf.TMP = self.root + "/"
        d = {"owner": "ws58", "launcher": {"path": os.path.join(self.root, "none.sh")}}
        rf.record_fail(self.flags, "r1", d, "first progress never came", {})
        rf.record_fail(self.flags, "r1", d, "again", {})
        a = alerts(self.flags)
        self.assertEqual([x["kind"] for x in a], ["smoke-fail", "smoke-fail"])
        self.assertIn("FAIL-1.json", a[0]["summary"])
        self.assertIn("FAIL-2.json", a[1]["summary"])


class DiskFloor(Base):
    def check(self, free):
        return notify.disk_floor_check(self.flags, os.path.join(self.flags, "st.json"), ["r1", "r2"], free=free,
                                       floor=150, hyst=25, log=lambda *_: None)

    def test_one_alert_per_crossing_with_hysteresis(self):
        seq = [200, 140, 120, 160, 149, 174, 176, 140]
        got = [self.check(f) for f in seq]
        self.assertEqual(got, [None, "raised", None, None, None, None, "cleared", "raised"])
        a = alerts(self.flags)
        self.assertEqual([x["kind"] for x in a], ["disk-floor", "disk-floor-cleared", "disk-floor"])
        self.assertEqual(a[0]["detail"]["rows_blocked"], ["r1", "r2"])
        self.assertEqual(a[0]["detail"]["floor_gib"], 150)
        self.assertEqual(a[0]["detail"]["free_gib"], 140)

    def test_reclaimable_is_information_only(self):
        big = os.path.join(self.root, "junk", "big")
        os.makedirs(big)
        with open(os.path.join(big, "f"), "wb") as f:
            f.write(b"x" * 1024)
        from unittest import mock   # hermetic: a LIVE quiet-host grant on the host must not defer the scan here
        with mock.patch.object(notify._quiet_host(), "defer", return_value=False):
            notify.disk_floor_check(self.flags, os.path.join(self.flags, "st.json"), [], free=1, floor=150, hyst=25,
                                    reclaim_root=os.path.join(self.root, "junk"), log=lambda *_: None)
        self.assertTrue(os.path.exists(os.path.join(big, "f")))
        self.assertEqual(alerts(self.flags)[0]["detail"]["reclaimable_candidates_info_only"][0]["path"], big)


class FillerHook(Base):
    def test_write_ended_calls_notify(self):
        """Run filler_run15.sh's write_ended + notify_end functions in isolation against a temp flags tree."""
        bin_ = os.path.join(self.flags, "bin")
        os.makedirs(bin_)
        shutil.copy(os.path.join(_RF, "notify.py"), bin_)
        src = open(os.path.join(_RF, "filler_run15.sh")).read()
        start = src.index("write_ended() {")
        end = src.index("\n}\n", src.index("notify_end() {")) + 3
        script = (f'set -u\nHERE={bin_}\nFLAGS={self.flags}\nGRANTS={self.flags}/grants\nID=r1\nDRYRUN=0\n'
                  f'ENDED=$GRANTS/r1.ended\nGRANT=$GRANTS/r1.grant\nts() {{ date -u +%FT%TZ; }}\nlog() {{ echo "$*"; }}\n'
                  + src[start:end] + '\nwrite_ended 75 disk-floor\n')
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        a = alerts(self.flags)
        self.assertEqual(len(a), 1, r.stdout + r.stderr)
        self.assertEqual(a[0]["detail"]["reason"], "disk-floor")
        self.assertEqual(a[0]["row_owner"], "ws58")


class LivePush(Base):
    """notify.push (2026-11-24): dedupe per key, <=1 push/owner/60 s with batching, 15 min escalation, best-effort."""
    LAUNCHER = ("==== dry run 2026-11-24T20:09:59Z regions=mi210_0\n==== engine START at +5s\n"
                "SMOKE FAIL rc=3: knob witness missing for ['GGML_HIP_I8PC'] (/x/out/TERMINAL-smoke.json)\n"
                "SMOKE FAIL rc=3: second line\n==== dry run FAIL: job ended rc=3\n")

    def setUp(self):
        super().setUp()
        self.sent = []
        self.deliver = lambda flags, owner, text: self.sent.append((owner, text)) or {"channel": "fake"}

    def rec(self, key, kind="smoke-fail", cause="c"):
        return {"key": key, "kind": kind, "row_id": "r1", "detail": {"cause": cause, "fix_task": "FIX-1"}}

    def tick(self, now):
        return notify.push_tick(self.flags, now=now, deliver=self.deliver, log=lambda m: None)

    def test_cause_first_smoke_fail_line_from_launcher_out(self):
        d = os.path.join(self.flags, "dryrun", "r1")
        os.makedirs(d)
        with open(os.path.join(d, "launcher.out"), "w") as f:
            f.write(self.LAUNCHER)
        cause = notify.smoke_fail_cause(os.path.join(d, "FAIL-1.json"), {"reason": "fallback"})
        self.assertEqual(cause, "SMOKE FAIL rc=3: knob witness missing for ['GGML_HIP_I8PC'] (/x/out/TERMINAL-smoke.json)")

    def test_cause_falls_back_to_terminal_smoke_json(self):
        d = os.path.join(self.flags, "dryrun", "r1")
        os.makedirs(d)
        t = os.path.join(self.root, "TERMINAL-smoke.json")
        with open(t, "w") as f:
            json.dump({"ok": False, "reason": "build missing"}, f)
        with open(os.path.join(d, "launcher.out"), "w") as f:
            f.write(f"==== engine START\nwrote {t}\n")
        self.assertEqual(notify.smoke_fail_cause(os.path.join(d, "FAIL-1.json"), {}), "TERMINAL-smoke: build missing")

    def test_line_has_kind_row_cause_fix(self):
        self.assertEqual(notify.push_line(self.rec("k1", cause="SMOKE FAIL rc=3: x")),
                         "smoke-fail row=r1 cause=SMOKE FAIL rc=3: x fix_task=FIX-1 key=k1")

    def test_dedupe_one_push_per_key(self):
        notify.push(self.flags, self.rec("k1"), "ak", now=1000, deliver=self.deliver)
        self.assertEqual(notify.push(self.flags, self.rec("k1"), "ak", now=2000, deliver=self.deliver), "dup")
        self.assertEqual(len(self.sent), 1)

    def test_rate_limit_batches_into_one_message(self):
        notify.push(self.flags, self.rec("k1"), "ak", now=1000, deliver=self.deliver)
        self.assertEqual(notify.push(self.flags, self.rec("k2"), "ak", now=1010, deliver=self.deliver), "deferred")
        notify.push(self.flags, self.rec("k3"), "ak", now=1020, deliver=self.deliver)
        notify.push(self.flags, self.rec("k4"), "other", now=1020, deliver=self.deliver)   # other owner: own limit
        self.tick(1030)
        self.assertEqual([o for o, _ in self.sent], ["ak", "other"])
        self.tick(1061)
        self.assertEqual(len(self.sent), 3)
        self.assertTrue(self.sent[2][1].startswith("2 alerts: "))
        self.assertIn("key=k2", self.sent[2][1])
        self.assertIn("key=k3", self.sent[2][1])

    def test_escalates_once_after_15_min_unless_acked(self):
        notify.push(self.flags, self.rec("k1"), "ak", now=1000, deliver=self.deliver)
        notify.push(self.flags, self.rec("k2"), "ak2", now=1000, deliver=self.deliver)
        notify._append_line(notify.acks_path(self.flags), {"key": "k2"})
        self.tick(1000 + 899)
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(self.tick(1000 + 901)["escalated"], ["k1"])
        self.assertEqual(self.sent[-1][0], "pipeline-mgmt")
        self.assertIn("push-unacked", self.sent[-1][1])
        self.tick(5000)
        self.assertEqual(len(self.sent), 3)

    def test_failed_push_never_breaks_emit(self):
        with mock.patch.object(notify, "push", side_effect=RuntimeError("boom")):
            m = notify.emit(self.flags, "smoke-fail", "r1", "FAIL-1.json", "s", "warning", "ws58")
        self.assertEqual(m["record"]["kind"], "smoke-fail")
        self.assertEqual(len(alerts(self.flags)), 1)

    def test_emit_pushes_actionable_kinds_only_once(self):
        notify.emit(self.flags, "smoke-fail", "r1", "FAIL-1.json", "s", "warning", "ws58")
        notify.emit(self.flags, "smoke-fail", "r1", "FAIL-1.json", "s", "warning", "ws58")
        notify.emit(self.flags, "underused", "r1", "x", "s", "warning", "ws58")
        ch = os.path.join(self.flags, "notify", "push", "channel")
        lines = [ln for n in os.listdir(ch) for ln in open(os.path.join(ch, n))]
        self.assertEqual(len(lines), 1)
        self.assertIn("smoke-fail row=r1", lines[0])


if __name__ == "__main__":
    unittest.main()
