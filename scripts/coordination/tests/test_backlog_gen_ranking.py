#!/usr/bin/env python3
"""backlog_gen ranking (operator objective 2026-11-01): non-inference tasks are ordered by inference rows unblocked,
lane-weighted toward the emptiest lane, transitively through unblocks links; then effort; zero-unblock tasks last.
Also: closed workers' queues are re-routed (small -> codex-gen, large -> handoff session or 'needs a session')."""
import json
import os
import shutil
import sys
import tempfile
import unittest

_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _COORD)
import backlog_gen as bg  # noqa: E402


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="bg-test-")
        self.flags = os.path.join(self.d, "flags")
        os.makedirs(os.path.join(self.flags, "ready"))
        os.makedirs(os.path.join(self.flags, "grants"))
        bg._rf = None  # rows are plain v3 dicts here; state = needs-qualification unless blocked_by says otherwise
        for rid, lane, rank, extra in (("row-gpu-1", "gpu", 1, {}), ("row-cpu-1", "cpu", 2, {}), ("row-cpu-2", "cpu", 3, {}),
                                       ("row-cpu-ready", "cpu", 4, {})):
            json.dump({"schema": "epyc.row.v3", "id": rid, "owner": "o", "lane": lane, "regions": "mi210_0,184-191" if lane == "gpu" else "any-cpu-quarter",
                       "priority_rank": rank, "handoff_task": "handoffs/active/h.md:INF-1", **extra},
                      open(os.path.join(self.flags, "ready", rid + ".json"), "w"))
        # one cpu row running -> cpu lane has 1 ready row, gpu 0
        open(os.path.join(self.flags, "grants", "row-cpu-ready.grant"), "w").write("regions=0-23 start=2026-11-01T00:00Z end=2026-11-01T01:00Z\n")
        with open(os.path.join(self.flags, "WORK-codex-gen-code.md"), "w") as f:
            f.write("- [S] handoffs/active/h.md:10 — task A unblocks nothing\n"
                    "- [M] handoffs/active/h.md:20 — task B unblocks a gpu row [unblocks: row-gpu-1]\n"
                    "- [S] handoffs/active/h.md:30 — task C unblocks two cpu rows [unblocks: row-cpu-1,row-cpu-2]\n"
                    "- [S] handoffs/active/h.md:40 — task D unblocks B transitively [unblocks: handoffs/active/h.md:20]\n"
                    "- [L] handoffs/active/other.md:5 — task E big, no session\n"
                    "- [source-published; owner deployment pending] handoffs/active/h.md:50 — task F odd bracket [unblocks: row-gpu-1]\n")
        with open(os.path.join(self.flags, "WORK-ni-code.md"), "w") as f:
            f.write("- [S] handoffs/active/h.md:60 — legacy ni task small\n- [M] handoffs/active/h.md:70 — legacy ni task medium\n")
        self.pri = os.path.join(self.d, "pri.json")
        json.dump({"rows": {}, "inference_prep": []}, open(self.pri, "w"))
        self.sessions = os.path.join(self.d, "hs.json")
        json.dump({"sessions": {"h": {"handoff": "handoffs/active/h.md", "status": "suspended", "row_ids": [], "row_patterns": [], "handoff_rows": ["INF-1"]}}},
                  open(self.sessions, "w"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_ranking_and_routing(self):
        data = bg.build(self.flags, self.pri, os.path.join(self.flags, "nolog"), sessions_path=self.sessions)
        self.assertEqual(data["ready_by_lane"], {"cpu": 1, "gpu": 0, "host": 0})
        gen = data["workers"]["codex-gen"]
        texts = [wl["text"][:6] for wl in gen["code"]]
        # scores: B = 1.0 (gpu weight 1/(1+0)); D = 1.0 (transitive via B); C = 2 * 1/(1+1) = 1.0; F = 1.0
        # tie-break by effort: S before M; A (score 0) last. B is [M] so it is not codex-gen's but the handoff's.
        self.assertTrue(texts.index("task A") > texts.index("task C"), texts)  # zero-score after positive-score
        self.assertNotIn("task B", texts)  # M-sized -> handoff session
        scores = {wl["text"][:6]: wl["score"] for w in data["workers"].values() for wl in w["code"]}
        self.assertEqual(scores["task B"], 1.0)
        self.assertEqual(scores["task D"], 1.0, "transitive link through another task's file:line")
        self.assertEqual(scores["task C"], 1.0)
        self.assertEqual(scores["task F"], 1.0, "non-size status bracket must not drop the unblocks link")
        self.assertEqual(scores["task A"], 0.0)
        h = data["workers"]["handoff-h"]
        self.assertIn("task B", [wl["text"][:6] for wl in h["code"]])
        self.assertIn("task E", [wl["text"][:6] for wl in gen["routed"]], "L task with no session is routed, not hidden")
        self.assertIn("legacy", " ".join(wl["text"] for wl in gen["code"]), "closed ni queue small tasks reach codex-gen")
        self.assertIn("legacy ni task medium", " ".join(wl["text"] for wl in h["code"]))
        # rows: gpu (0 ready) sorts before cpu (1 ready)
        lanes = [r["lane"] for r in h["rows"] if r["state"] in bg.ADVANCEABLE]
        self.assertEqual(lanes[0], "gpu")
        out = bg.render("codex-gen", data)
        self.assertIn("score=", out)
        self.assertIn("Routed elsewhere", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
