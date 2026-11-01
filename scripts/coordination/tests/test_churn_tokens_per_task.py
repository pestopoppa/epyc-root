#!/usr/bin/env python3
"""tokens_per_task: attribution (session id / lane cwd / unattributed), completed = ticks + rows + filings, top turns."""
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_COORD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_COORD / "churn"))
import tokens_per_task as tpt  # noqa: E402


def _w(p, txt):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(txt)


def ev(ts, typ, **kw):
    return json.dumps({"timestamp": ts, "type": "event_msg", "payload": dict({"type": typ}, **kw)})


class T(unittest.TestCase):
    def test_metric(self):
        td = tempfile.mkdtemp()
        flags, repo, lanes, sess = (os.path.join(td, x) for x in ("flags", "repo", "lanes", "sessions"))
        # repo with one wrap-up commit that ticks two boxes
        subprocess.run(["git", "-C", td, "init", "-q", repo], check=True)
        _w(os.path.join(repo, "handoffs/active/a.md"), "- [ ] A\n- [ ] B\n- [ ] C\n")
        g = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t", *a], check=True, capture_output=True, text=True)
        g("add", "."); g("commit", "-q", "-m", "base")
        _w(os.path.join(repo, "handoffs/active/a.md"), "- [x] A ✅\n- [x] B ✅\n- [ ] C\n")
        g("add", "."); g("commit", "-q", "-m", "Tick A and B")
        sha = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        # registry + log + rows + filing
        _w(os.path.join(flags, "handoff-sessions.json"), json.dumps({"sessions": {"s1": {"session_id": "thr-1"}, "s2": {"session_id": "thr-2"}}}))
        _w(os.path.join(flags, "handoff-sessions.log"), f"2026-11-01T10:30:00Z TURN-END s1 session=thr-1 rc=0 wrapup={sha}\n")
        _w(os.path.join(flags, "ready/r1.json"), json.dumps({"id": "r1", "owner": "handoff-s1"}))
        _w(os.path.join(flags, "filing-done/r1.FILED"), "")
        # rollouts: s1 own thread (2 turns), a sub-agent in s1's lane, s2 own thread, one unattributed (/workspace)
        day = "2026/11/01"
        def meta(tid, cwd): return json.dumps({"timestamp": "2026-11-01T10:00:00Z", "type": "session_meta", "payload": {"id": tid, "cwd": cwd}})
        tok = lambda ts, i, o: ev(ts, "token_count", info={"last_token_usage": {"input_tokens": i, "output_tokens": o}})
        _w(os.path.join(sess, day, "rollout-a-thr-1.jsonl"), "\n".join([meta("thr-1", "/x"), ev("2026-11-01T10:00:01Z", "task_started"), tok("2026-11-01T10:00:02Z", 1000, 10),
                                                                   ev("2026-11-01T10:05:00Z", "task_complete"), ev("2026-11-01T10:20:00Z", "task_started"), tok("2026-11-01T10:21:00Z", 5000, 50), ev("2026-11-01T10:25:00Z", "task_complete")]) + "\n")
        _w(os.path.join(sess, day, "rollout-b-sub.jsonl"), "\n".join([meta("sub-9", lanes + "/h-s1"), tok("2026-11-01T10:02:00Z", 2000, 20)]) + "\n")
        _w(os.path.join(sess, day, "rollout-c-thr-2.jsonl"), "\n".join([meta("thr-2", "/x"), ev("2026-11-01T11:00:00Z", "task_started"), tok("2026-11-01T11:00:01Z", 700, 7)]) + "\n")
        _w(os.path.join(sess, day, "rollout-d-old.jsonl"), "\n".join([meta("old", "/workspace"), tok("2026-11-01T09:00:00Z", 999, 1)]) + "\n")
        with patch.object(tpt, "SESSIONS", sess), patch.object(tpt, "LANES", lanes):
            res = tpt.compute(flags, repo, day=dt.date(2026, 11, 1))
        s1 = res["per"]["s1"]
        self.assertEqual((s1["input"], s1["output"], s1["subagent_input"], s1["subagent_rollouts"]), (8000, 80, 2000, 1))
        self.assertEqual((s1["ticks"], s1["rows"], s1["filings"], s1["completed"]), (2, 1, 1, 4))
        self.assertAlmostEqual(s1["tokens_per_task"], 8080 / 4)
        self.assertEqual(s1["ctx"], 5000)
        self.assertIsNone(res["per"]["s2"]["tokens_per_task"])  # spent, nothing completed -> inf
        self.assertEqual(res["per"]["unattributed"]["tokens"], 1000)
        top = res["top_turns"][0]
        self.assertEqual((top["slug"], top["tokens"]), ("s1", 5050))
        self.assertIn("Tick A and B", top["subject"])  # the TURN-END 5 min after the turn names the landed commit
        txt = tpt.render(res)
        self.assertIn("s2", txt)
        self.assertIn("inf", txt)


if __name__ == "__main__":
    unittest.main()
