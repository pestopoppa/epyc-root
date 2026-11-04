#!/usr/bin/env python3
"""Tests for scripts/handoffs/backlog_priority.py (generator of handoffs/active/backlog-priority.json)."""

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, _REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bp = _load("backlog_priority", "scripts/handoffs/backlog_priority.py")
index_state = _load("index_state_bp", "scripts/handoffs/index_state.py")


class CuratedTable(unittest.TestCase):
    def setUp(self):
        self.cur = json.loads(bp.CURATED_PATH.read_text(encoding="utf-8"))

    def test_schema(self):
        keys = set()
        for e in self.cur["entries"]:
            self.assertIn(e["kind"], ("I", "N", "O"), e["tok"])
            self.assertIn(e["cls"], ("live", "ready", "routine", "hold", "N", "NB"), e["tok"])
            self.assertTrue(0.0 <= e["s"] <= 1.0, e["tok"])
            if e.get("new"):
                self.assertTrue(e.get("title") and e.get("file"), e["tok"])
            keys.add(f"{e['row']}:{e['tok']}")
        for e in self.cur["entries"]:
            if e.get("before"):
                self.assertIn(e["before"], keys, f"before of {e['tok']} names no curated entry")

    def test_completions_recorded_as_done(self):
        done = {(e["row"], e["tok"]) for e in self.cur["entries"] if e.get("done")}
        for want in (("INF-65", "CH-24"), ("INF-65", "CH-20.2"), ("INF-60", "Q38-T10.1a"), ("RTG-58", "KPF-62.1"),
                     ("INF-70", "XFER-3"), ("INF-67", "FD-DIV-1b"), ("EVL-47", "VB-CAL-OVERRUN-WIRE")):
            self.assertIn(want, done)


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state, cls.boxes = bp.collect_boxes(index_state)
        cls.cur = json.loads(bp.CURATED_PATH.read_text(encoding="utf-8"))
        cls.res = bp.build(copy.deepcopy(cls.cur), index_state, cls.state, cls.boxes)

    def test_rows_cover_open_work_and_scores_are_valid(self):
        doc = self.res["doc"]
        opened = {rid for rid, r in self.state["rows"].items()
                  if self.state["handoffs"].get(r["handoff"], {}).get("open", 0) > 0}
        self.assertLessEqual(len(opened - set(doc["rows"])), 3)       # allow boxes the row resolver cannot place
        scores = [r["score"] for r in doc["rows"].values()]
        self.assertTrue(all(0.0 <= s <= 1.0 for s in scores))
        self.assertEqual(max(scores), 1.0)
        ranks = sorted(r["rank"] for r in doc["rows"].values())
        self.assertEqual(ranks, list(range(1, len(ranks) + 1)))
        self.assertTrue(doc["generated_by"] and doc["generated_at"] and doc["method"])

    def test_done_items_are_excluded_and_listed(self):
        texts = [i["text"] for i in self.res["items"].values()]
        self.assertFalse(any(t.startswith("CH-24 ") for t in texts))
        self.assertFalse(any(t.startswith("Q38-T10.1a") for t in texts))
        self.assertTrue(any("CH-24" in d["task"] for d in self.res["doc"]["done_pending_tick"]))

    def test_new_and_in_progress_entries(self):
        new = [i for i in self.res["items"].values() if i["line"] == 0]
        self.assertTrue(any("VB-CAL-OVERRUN-WRITE" in i["text"] for i in new))
        self.assertTrue(any(i["in_progress"] for i in new))

    def test_blocker_ranks_above_the_inference_it_gates(self):
        n = 0
        for i in self.res["items"].values():
            if i["source"] == "curated" and i["before"] and i["kind"] in ("N", "O"):
                tgt = self.res["items"].get(self._key(i["before"]))
                if tgt is not None and tgt["kind"] == "I":
                    n += 1
                    self.assertLess(i["rank"], tgt["rank"], i["text"][:40])
        self.assertGreater(n, 5)

    def _key(self, ref):
        row, tok = ref.split(":", 1)
        for i in self.res["items"].values():
            if i["row"] == row and i["source"] == "curated" and (tok in i["text"][:110].replace("**", "")):
                return i["key"]
        return None

    def test_track_scoped_hold_and_weight(self):
        # BRF-T1-1: a folded track keeps its retired row's hold/weight via a `<ROW>#<track>` key
        self.assertEqual(bp.scoped({"R": "row", "R#t": ""}, "R", "t"), "")          # explicit no-hold wins
        self.assertEqual(bp.scoped({"R": "row"}, "R", "t"), "row")                  # unscoped falls back to the row
        self.assertEqual(bp.scoped({"R#t": 0.9}, "R", None, 0.2), 0.2)              # untracked boxes never read a track key
        hold = dict(self.cur.get("holds", {}))
        b = next(b for b in self.boxes if b["code"] == 0 and b["rows"] and b["rows"][0] not in hold
                 and not bp.HOLD_RX.search(b["text"][:300]) and not b.get("track"))
        boxes = [dict(x, track="T") if x is b else x for x in self.boxes]
        row = b["rows"][0]
        cur = copy.deepcopy(self.cur)
        cur["holds"][f"{row}#T"] = "track hold under test"
        res = bp.build(cur, index_state, self.state, boxes)
        it = next(i for i in res["items"].values() if i["file"] == b["file"] and i["line"] == b["line"])
        self.assertEqual((it["cls"], it["blocker"]), ("H", "track hold under test"))
        # mutation: the same box without the track key is not held
        res0 = bp.build(copy.deepcopy(self.cur), index_state, self.state, boxes)
        it0 = next(i for i in res0["items"].values() if i["file"] == b["file"] and i["line"] == b["line"])
        self.assertNotEqual(it0["cls"], "H")

    def test_dep_tracks_scope_the_row_dep_inheritance(self):
        # BRF-T1-1: a Deps edge repointed by a fold keeps landing on the retired row's track
        inh = [i for i in self.res["items"].values() if i["unblocks"].startswith("row-dep (coarse Deps edge ")]
        self.assertTrue(inh, "fixture: some row-dep inheritance must fire on the live tree")
        it = inh[0]
        frm = it["unblocks"].split("edge ", 1)[1].split(")", 1)[0].split(", ")[0]
        cur = copy.deepcopy(self.cur)
        cur["dep_tracks"] = {f"{frm}>{it['row']}": [{"track": "no-such-track", "next_action": it["text"]}]}
        res = bp.build(cur, index_state, self.state, self.boxes)
        moved = res["items"][it["key"]]
        self.assertFalse(moved["unblocks"].startswith(f"row-dep (coarse Deps edge {frm}"), moved["unblocks"])
        # mutation: the entry naming the box's own track (None = untracked) keeps the inheritance
        cur["dep_tracks"] = {f"{frm}>{it['row']}": [{"track": it.get("track"), "next_action": it["text"]}]}
        res = bp.build(cur, index_state, self.state, self.boxes)
        self.assertTrue(res["items"][it["key"]]["unblocks"].startswith("row-dep (coarse Deps edge "))

    def test_mutation_curated_score_changes_the_order(self):
        cur = copy.deepcopy(self.cur)
        for e in cur["entries"]:
            if e["row"] == "INF-22" and e["tok"] == "PB-QCOST-1 confirm-R":
                e["s"] = 0.01
        res2 = bp.build(cur, index_state, self.state, self.boxes)
        pick = lambda r: next(i for i in r["items"].values() if i["text"].startswith("PB-QCOST-1 confirm-R"))
        self.assertGreater(pick(res2)["rank"], pick(self.res)["rank"])

    def test_check_fresh_file_passes_then_mutations_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bp.json"
            p.write_text(json.dumps(self.res["doc"]))
            problems, _ = bp.check(self.res, p)
            self.assertEqual(problems, [])
            old = json.loads(p.read_text()); old["generated_at"] = "2026-01-01T00:00Z"
            p.write_text(json.dumps(old))
            self.assertTrue(any("days old" in x for x in bp.check(self.res, p)[0]))
            old = copy.deepcopy(self.res["doc"]); old["rows"].pop(next(iter(old["rows"])))
            p.write_text(json.dumps(old))
            self.assertTrue(any("missing" in x for x in bp.check(self.res, p)[0]))
            old = copy.deepcopy(self.res["doc"])
            for r in old["rows"].values(): r["tier"] = 9
            p.write_text(json.dumps(old))
            self.assertTrue(any("drift" in x for x in bp.check(self.res, p)[0]))
            self.assertTrue(bp.check(self.res, Path(d) / "absent.json")[0])

    def test_committed_file_is_consumable_by_index_state(self):
        doc, probs = index_state.load_priority_file(index_state.PRIORITY_FILE)
        self.assertEqual(probs, [])
        self.assertGreater(len(doc["rows"]), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
