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


class NeedsSessionAndRunningStateTests(unittest.TestCase):
    """2026-11-01 ws58: (a) handoffs needing a session are ranked by lane-weighted rows unblocked, ties by
    backlog-priority rank (never alphabetically), and a stuck row's handoff counts; (b) `running` needs an open grant,
    no .ended and a live recorded pid (the HSF row bug: running shown while grants/<id>.ended said rc=1)."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="bg-ns-")
        self.flags = os.path.join(self.d, "flags")
        for sub in ("ready/armed", "grants"):
            os.makedirs(os.path.join(self.flags, sub))
        bg._rf = None
        self.ha = os.path.join(self.d, "handoffs", "active")
        os.makedirs(self.ha)
        self.pri = os.path.join(self.ha, "backlog-priority.json")
        json.dump({"rows": {"INF-1": {"kind": "inference-ready", "rank": 1}, "INF-9": {"kind": "inference-ready", "rank": 9},
                            "INF-5": {"kind": "inference-ready", "rank": 5}},
                   "inference_prep": []}, open(self.pri, "w"))
        json.dump({"handoffs": {"alpha.md": {"row_id": "INF-9"}, "mid.md": {"row_id": "INF-5"}, "zed.md": {"row_id": "INF-1"}},
                   "rows": {"INF-9": {"handoff": "alpha.md"}, "INF-5": {"handoff": "mid.md"}, "INF-1": {"handoff": "zed.md"}}},
                  open(os.path.join(self.ha, ".index-state.json"), "w"))
        self.sessions = os.path.join(self.d, "hs.json")
        json.dump({"sessions": {}}, open(self.sessions, "w"))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def row(self, rid, lane="cpu", **extra):
        json.dump({"schema": "epyc.row.v3", "id": rid, "owner": "o", "lane": lane, "priority_rank": 3,
                   "regions": "mi210_0,184-191" if lane == "gpu" else "any-cpu-quarter", **extra},
                  open(os.path.join(self.flags, "ready", rid + ".json"), "w"))

    def build(self):
        return bg.build(self.flags, self.pri, os.path.join(self.flags, "nolog"), sessions_path=self.sessions)

    def test_needs_session_ranking_not_alphabetical(self):
        self.row("row-gpu-1", "gpu", handoff_task="handoffs/active/mid.md:INF-5")
        with open(os.path.join(self.flags, "WORK-codex-gen-code.md"), "w") as f:
            f.write("- [M] handoffs/active/alpha.md:10 — alpha task\n"
                    "- [M] handoffs/active/zed.md:10 — zed task\n"
                    "- [M] handoffs/active/mid.md:10 — mid task [unblocks: row-gpu-1]\n")
        data = self.build()
        ns = data["needs_session"]
        self.assertEqual([h["handoff"].split("/")[-1] for h in ns], ["mid.md", "zed.md", "alpha.md"])
        self.assertEqual(ns[0]["score"], 1.0)  # gpu lane weight 1/(1+0); the row counted ONCE though both the task
        self.assertEqual(ns[0]["rows"], ["row-gpu-1"])  # and the row's own handoff_task point at mid.md
        self.assertEqual((ns[1]["row_id"], ns[1]["priority_rank"]), ("INF-1", 1.0))
        self.assertEqual((ns[2]["row_id"], ns[2]["priority_rank"]), ("INF-9", 9.0))
        routed = data["workers"]["codex-gen"]["routed"]
        self.assertEqual([wl["file"].split("/")[-1] for wl in routed], ["mid.md", "zed.md", "alpha.md"])
        text = bg.render("codex-gen", data)
        self.assertLess(text.index("**handoffs/active/mid.md**"), text.index("**handoffs/active/zed.md**"))
        self.assertLess(text.index("**handoffs/active/zed.md**"), text.index("**handoffs/active/alpha.md**"))
        self.assertIn("handoff score=1.0 rows=row-gpu-1 own-inference-tasks=0 priority=INF-5 rank=5.0", text)

    def test_stuck_row_without_tasks_still_counts_for_its_handoff(self):
        # a FILLERS-migrated row has no handoff_task path; the inference_prep `row` -> index-state maps it to alpha.md
        self.row("HSF-ROW-2", handoff_task="FILLERS:HSF-ROW-2", blocked_by=["dry run failed"])
        pri = json.load(open(self.pri))
        pri["inference_prep"] = [{"rank": 4, "filler": "HSF-ROW-2", "row": "INF-9", "lane": "cpu", "blocker": "harness fix"}]
        json.dump(pri, open(self.pri, "w"))
        open(os.path.join(self.flags, "WORK-codex-gen-code.md"), "w").write("- [M] handoffs/active/zed.md:10 — zed task\n")
        data = self.build()
        ns = {h["handoff"].split("/")[-1]: h for h in data["needs_session"]}
        self.assertEqual(ns["alpha.md"]["rows"], ["HSF-ROW-2"])
        self.assertEqual(ns["alpha.md"]["score"], 1.0)
        self.assertEqual([h["handoff"].split("/")[-1] for h in data["needs_session"]], ["alpha.md", "zed.md"])

    def test_running_requires_live_grant_without_ended(self):
        G = os.path.join(self.flags, "grants")
        for rid in ("HSF-ENDED", "HSF-DEADPID", "HSF-LIVE", "HSF-NOPID"):
            self.row(rid, handoff_task="handoffs/active/zed.md:INF-1")
            open(os.path.join(G, rid + ".grant"), "w").write("regions=0-23 start=x end=y\n")
        open(os.path.join(G, "HSF-ENDED.ended"), "w").write("rc=1 time=2026-10-26T21:47:27Z reason=exited\n")
        json.dump({"id": "HSF-DEADPID", "pid": 99999997}, open(os.path.join(self.flags, "ready/armed/HSF-DEADPID.json"), "w"))
        json.dump({"id": "HSF-LIVE", "pid": os.getpid()}, open(os.path.join(self.flags, "ready/armed/HSF-LIVE.json"), "w"))
        states = {r["id"]: r for r in self.build()["workers"]["codex-gen"]["rows"]}
        self.assertEqual(states["HSF-ENDED"]["state"], "done", "an .ended record (rc=1) is never running")
        self.assertEqual(states["HSF-DEADPID"]["state"], "blocked")
        self.assertIn("pid 99999997 is dead", states["HSF-DEADPID"]["reasons"][0])
        self.assertEqual(states["HSF-LIVE"]["state"], "running")
        self.assertEqual(states["HSF-NOPID"]["state"], "running")
        self.assertEqual(bg.grant_run_state(self.flags + "/", "HSF-ENDED")[0], "done")
        self.assertEqual(bg.grant_run_state(self.flags + "/", "HSF-DEADPID")[0], "stale-grant")
        self.assertIsNone(bg.grant_run_state(self.flags + "/", "no-such-row")[0])
        # legacy (non-v3) manifests follow the same rule
        json.dump({"schema": "epyc.ready.v2", "id": "LEG-DEAD", "regions": "0-23"}, open(os.path.join(self.flags, "ready", "LEG-DEAD.json"), "w"))
        open(os.path.join(G, "LEG-DEAD.grant"), "w").write("regions=0-23\n")
        json.dump({"id": "LEG-DEAD", "pid": 99999997}, open(os.path.join(self.flags, "ready/armed/LEG-DEAD.json"), "w"))
        states = {r["id"]: r for r in self.build()["workers"]["codex-gen"]["rows"]}
        self.assertEqual(states["LEG-DEAD"]["state"], "blocked")

    def test_own_inference_tasks_count_as_candidate_rows(self):
        # alpha has two open boxes that read like runs (one GPU) and one prose box; zed has only a prose box
        open(os.path.join(self.ha, "alpha.md"), "w").write("# a\n- [ ] run llama-bench at depth 32k on the MI210\n- [ ] measure t/s for Q4_K_M on one CPU quarter\n- [ ] rewrite the README\n- [x] done sweep\n")
        open(os.path.join(self.ha, "zed.md"), "w").write("# z\n- [ ] rewrite the README\n")
        open(os.path.join(self.flags, "WORK-codex-gen-code.md"), "w").write("- [M] handoffs/active/zed.md:10 — zed task\n")
        data = self.build()
        hr = {h["handoff"].split("/")[-1]: h for h in data["handoff_rank"]}
        self.assertEqual(hr["alpha.md"]["candidate_rows"], 2)
        self.assertEqual(hr["alpha.md"]["score"], 1.0)  # 0.5 * (gpu 1/(1+0) + cpu 1/(1+0))
        self.assertEqual(hr["alpha.md"]["candidates"][0]["lane"], "gpu")
        self.assertEqual(hr["zed.md"]["candidate_rows"], 0)
        self.assertEqual([h["handoff"].split("/")[-1] for h in data["needs_session"]][:2], ["alpha.md", "zed.md"])
        self.assertEqual(hr["alpha.md"]["position"], 1)
        # a piloted handoff is ranked too (dispatcher yields slots by it) and its backlog carries the inference-first line
        json.dump({"sessions": {"a": {"handoff": "handoffs/active/alpha.md", "status": "live"}}}, open(self.sessions, "w"))
        data = self.build()
        hr = {h["handoff"].split("/")[-1]: h for h in data["handoff_rank"]}
        self.assertEqual(hr["alpha.md"]["session"], "a")
        self.assertNotIn("alpha.md", [h["handoff"].split("/")[-1] for h in data["needs_session"]])
        text = bg.render("handoff-a", data)
        self.assertIn("**Inference first.**", text)
        self.assertIn("Handoff rank: #1 of", text)
        self.assertIn("L2 [gpu] run llama-bench", text)
