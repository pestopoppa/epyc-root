"""The single backlog-flow counter: build_daily_flow classification on a real git fixture,
the hub's roll-up and its unavailable state, and the hub view's refresh report.

Run: ``python3 -m pytest -q tests/test_dashboard_flow_counter.py``
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import dashboard.server as server
from scripts.handoffs import build_handoff_timeline as bt


class _Repo:
    def __init__(self, root: Path):
        self.root = root
        self.git("init", "-q", "-b", "main")

    def git(self, *args, date=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e.x",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e.x")
        if date:
            env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        subprocess.run(["git", "-C", str(self.root), *args], check=True, env=env,
                       capture_output=True, text=True)

    def write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def commit(self, msg, date):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", msg, date=date)


def _t(day):
    return f"{day}T12:00:00+00:00"


class FlowClassification(unittest.TestCase):
    """Each day holds one scenario, so each expected count is checked on its own row."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        r = cls.repo = _Repo(Path(cls.tmp.name))
        r.write("handoffs/active/a.md",
                "- [ ] alpha task long enough\n- [ ] bravo task long enough\n"
                "- [ ] charlie task long enough\n- [ ] delta task long enough\n"
                "- [ ] echo task long enough\n")
        r.commit("seed", _t("2026-03-01"))                       # 5 filed
        r.write("handoffs/active/a.md",
                "- [ ] alpha task long enough, reworded\n- [ ] bravo task long enough\n"
                "- [ ] charlie task long enough\n- [ ] delta task long enough\n"
                "- [ ] echo task long enough\n")
        r.commit("rewrite an open box", _t("2026-03-02"))        # neither
        r.write("handoffs/active/a.md",
                "- [ ] alpha task long enough, reworded\n- [x] bravo task long enough\n"
                "- [ ] charlie task long enough\n- [ ] delta task long enough\n"
                "- [ ] echo task long enough\n")
        r.commit("tick", _t("2026-03-03"))                       # 1 closed
        r.write("handoffs/active/a.md",
                "- [ ] alpha task long enough, reworded\n- [x] bravo task long enough\n"
                "- [x] charlie task long enough — declined, not worth it\n"
                "- [ ] echo task long enough\n")
        r.commit("decline one, delete one", _t("2026-03-04"))    # 2 removed
        r.write("handoffs/active/a.md",
                "- [ ] alpha task long enough, reworded\n- [x] bravo task long enough\n"
                "- [x] charlie task long enough — declined, not worth it\n")
        r.write("handoffs/active/b.md", "- [ ] echo task long enough\n")
        r.commit("cross-file move, no trailer", _t("2026-03-05"))  # 1 moved
        r.write("handoffs/active/b.md", "- [ ] foxtrot brand new box here\n")
        r.write("handoffs/active/c.md", "- [ ] echo task long enough\n")
        r.commit("fold\n\nRepoint-Reason: ABC-1: folded\n", _t("2026-03-06"))  # 1 moved, 1 fold_added
        # A lane worked on 03-07, merged on 03-08: flow on 03-07, stock change on 03-08.
        r.git("checkout", "-q", "-b", "lane")
        r.write("handoffs/active/a.md",
                "- [x] alpha task long enough, reworded\n- [x] bravo task long enough\n"
                "- [x] charlie task long enough — declined, not worth it\n")
        r.commit("lane tick", _t("2026-03-07"))
        r.git("checkout", "-q", "main")
        r.git("merge", "-q", "--no-ff", "-m", "merge lane", "lane", date=_t("2026-03-08"))
        log = bt._run_git_log(r.root, first_parent=True)
        flow = bt._run_git_log(r.root, no_merges=True)
        cls.rows = {x["date"]: x for x in bt.build_daily_flow(log, today="2026-03-09", flow_log=flow)}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def counts(self, day):
        r = self.rows[day]
        return (r["closed"], r["filed"], r["removed"], r["moved"], r["net"])

    def test_filing(self):
        self.assertEqual(self.counts("2026-03-01"), (0, 5, 0, 0, 5))

    def test_rewrite_of_open_box_is_neither(self):
        self.assertEqual(self.counts("2026-03-02"), (0, 0, 0, 0, 0))
        self.assertEqual(self.rows["2026-03-02"]["reworded"], 1)

    def test_tick_is_a_closure(self):
        self.assertEqual(self.counts("2026-03-03"), (1, 0, 0, 0, -1))

    def test_decline_and_delete_are_removals_not_closures(self):
        self.assertEqual(self.counts("2026-03-04"), (0, 0, 2, 0, -2))
        row = self.rows["2026-03-04"]
        self.assertEqual((row["declined"], row["removed_open"]), (1, 1))

    def test_cross_file_move_without_trailer(self):
        self.assertEqual(self.counts("2026-03-05"), (0, 0, 0, 1, 0))

    def test_fold_trailer(self):
        self.assertEqual(self.counts("2026-03-06"), (0, 0, 0, 1, 0))
        row = self.rows["2026-03-06"]
        # foxtrot was added and echo left b.md only as the move; the replaced text is a fold-added box.
        self.assertEqual(row["fold_added"], 1)
        self.assertEqual(row["open_stock"], self.rows["2026-03-05"]["open_stock"] + 1)

    def test_merged_lane_lands_on_its_own_date(self):
        self.assertEqual(self.counts("2026-03-07"), (1, 0, 0, 0, -1))
        self.assertEqual(self.counts("2026-03-08"), (0, 0, 0, 0, 0))
        self.assertEqual(self.rows["2026-03-07"]["open_stock"], self.rows["2026-03-06"]["open_stock"])
        self.assertEqual(self.rows["2026-03-08"]["open_stock"], self.rows["2026-03-07"]["open_stock"] - 1)


class HubRollup(unittest.TestCase):
    def _artifact(self, rows):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        p = Path(tmp.name) / "t.json"
        p.write_text(json.dumps({"generated_at": "2026-03-09T00:00:00Z", "last_sha": "abc",
                                 "daily_flow": rows}), encoding="utf-8")
        return p

    def _row(self, day, stock, **kw):
        base = dict(date=day, open_stock=stock, closed=0, filed=0, removed=0, net=0)
        return {**base, **kw}

    def test_stock_falls_while_net_is_reconciled(self):
        today = datetime.now().date()
        d = [(today - timedelta(days=i)).isoformat() for i in (8, 1, 0)]
        rows = [self._row(d[0], 100),
                self._row(d[1], 95, closed=3, removed=2, net=-5),
                self._row(d[2], 96, filed=1, net=1)]
        with mock.patch.object(server, "TIMELINE_PATH", self._artifact(rows)):
            w = server._activity_from_timeline()
        r = w["rollups"]["7d"]
        self.assertEqual((r["opening_stock"], r["closing_stock"], r["stock_delta"], r["net"]),
                         (100, 96, -4, -4))
        self.assertEqual(r["unexplained"], 0)
        self.assertEqual(w["commit"], "abc")

    def test_absent_artifact_is_unavailable_not_zero(self):
        with mock.patch.object(server, "TIMELINE_PATH", Path("/nonexistent/t.json")):
            w = server._activity_from_timeline()
        self.assertFalse(w["available"])
        self.assertEqual(w["rollups"], {})
        self.assertTrue(w["unavailable_reason"])
        self.assertFalse(server._activity_today_from(w)["available"])

    def test_old_format_artifact_is_unavailable(self):
        with mock.patch.object(server, "TIMELINE_PATH",
                               self._artifact([{"date": "2026-03-01", "open_stock": 1, "ticked": 2}])):
            self.assertFalse(server._activity_from_timeline()["available"])


class HubViewReport(unittest.TestCase):
    def _state(self, refresh):
        return {"head": "a" * 40, "origin_main": "a" * 40, "behind": 0,
                "head_committed_at": 1, "refresh": refresh, "refresh_present": refresh is not None,
                "refresh_error": None}

    def test_failed_fetch_degrades_health(self):
        state = self._state({"attempted_at": "2026-11-09T00:00:00Z", "ok": False, "stage": "fetch",
                             "detail": "git fetch origin failed"})
        with mock.patch.object(server, "_view_state", return_value=state):
            payload = server.hub_view_payload()
            health = server.health_payload()
        self.assertEqual(payload["_freshness"]["data_health"], "degraded")
        self.assertEqual(health["status"], "degraded")
        self.assertTrue(any(e["panel"] == "hub_view" and "fetch" in e["why"]
                            for e in health["attention"]))

    def test_no_report_is_absent_not_ok_claim(self):
        with mock.patch.object(server, "_view_state", return_value=self._state(None)):
            env = server.hub_view_payload()["_freshness"]
        self.assertEqual(env["reporting"], "absent")
        self.assertEqual(env["data_health"], "ok")


if __name__ == "__main__":
    unittest.main()
