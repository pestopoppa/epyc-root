#!/usr/bin/env python3
"""Tests for scripts/handoffs/backlog_priority.py (v2: dispatch order + compute-lane order + graph priority).

Most tests build from SYNTHETIC boxes / queue (fast, deterministic, no dependence on live handoff text); one class runs the real
tree once and asserts structural invariants only.
"""

import copy
import datetime
import importlib.util
import json
import re
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

NOW = datetime.datetime(2026, 10, 24, 12, 0, tzinfo=datetime.timezone.utc)
GIT_OK = dict(head="a" * 40, origin_main="a" * 40, behind=0, newest_handoffs_commit=int(NOW.timestamp()))


class FakeIndexState:
    """Just enough of index_state for build(): rows -> nodes, no dep edges unless asked."""

    def __init__(self, rows, edges=()):
        self.rows, self.edges = rows, list(edges)

    def build_graph(self, state):
        return {"nodes": [dict(id=r, domain="t", handoff=h, open=n, readiness="ready", next_action="") for r, (h, n) in self.rows.items()],
                "edges": self.edges}


def mkboxes(spec, rows=None):
    """spec: list of (file, text, kwargs). kwargs: open, indent, parent (index), touched, code, reasons, head."""
    boxes = []
    for k, (f, text, kw) in enumerate(spec):
        row = (rows or {}).get(f, "T-01")
        b = dict(handoff=f, file=f"handoffs/active/{f}", line=10 + k, text=text, head=kw.get("head", "Tasks"), rows=[row], open=kw.get("open", True),
                 indent=kw.get("indent", 0), parent=kw.get("parent"), children=[], token=bp.box_token(text), idx=k,
                 code=kw.get("code", 0), reasons=kw.get("reasons", []), touched=kw.get("touched", "2026-10-23"), full=text, sub="")
        if b["parent"] is not None:
            boxes[b["parent"]]["children"].append(k)
        boxes.append(b)
    return boxes


def curated(**kw):
    c = dict(row_weights={}, park_rows={}, holds=[], briefs={}, entries=[], done_pending_tick=[])
    c.update(kw)
    return c


def run(spec, queue=None, cur=None, rows=None, edges=(), cache=None):
    boxes = mkboxes(spec, rows)
    files = {b["handoff"]: b["rows"][0] for b in boxes}
    fis = FakeIndexState({r: (h, sum(1 for b in boxes if b["handoff"] == h and b["open"])) for h, r in files.items()}, edges)
    state = {"rows": {r: {"handoff": h} for h, r in files.items()}}
    return bp.build(cur or curated(), fis, state, boxes, queue=queue, cache=cache or {}, git=GIT_OK, now=NOW)


def item(res, token):
    return next(a for a in res["items"].values() if a["b"]["token"] == token)


def rec(fid, status="ARMED-UNBOOKED", **kw):
    r = dict(id=fid, owner="o", status=status, resources="CPU: one quarter", min_window="30 m", ram_gib="20", **{"class": "block-correctness"},
             shape="CPU: one quarter", duration="~1 h", substrate="cpu", ready="y", ds41="n", decision="", notes="")
    r.update(kw)
    return r


def queue(**buckets):
    b = {k: [] for k in ("COMPLETE", "RUNNING", "BOOKED", "ARMED-UNBOOKED", "STALE-ARMED", "BACKLOG")}
    b.update(buckets)
    return {"schema": "queue_status.v2", "as_of": "2026-10-24T12:00Z", "writers": {}, "buckets": b}


class KindAndTokens(unittest.TestCase):
    def test_operator_label_is_not_the_operator_acting(self):                  # audit #9
        self.assertEqual(bp.auto_kind("GPS-PIN-3 - AutoKernel GPU A/A re-check (operator D2, 2026-10-22). At the next GPU AK window, run one GPU serving A/A"), "I")
        self.assertEqual(bp.auto_kind("CS-2 - prepare the Annex S amendment package for operator ratification"), "N")
        self.assertEqual(bp.auto_kind("OPS-1 - operator decision: pick the reference build"), "O")

    def test_piggyback_check_is_compute(self):                                 # audit #8
        self.assertEqual(bp.auto_kind("GPS-PIN-2a - first-GPU-run check of the drivers. At each driver's next GPU run (no dedicated window): affinity ok"), "I")

    def test_authoring_verb_beats_window_keywords(self):
        self.assertEqual(bp.auto_kind("CS-6 — write the second-GPU bench-window run plan: an ordered run list, so the window is used fully"), "N")
        self.assertEqual(bp.auto_kind("CS-7 — run the second-GPU bench window"), "I")

    def test_box_token(self):
        for t, want in (("**RI-11 — Enforce expand**: x", "RI-11"), ("VB-FOLDGATE-WRITE — write side", "VB-FOLDGATE-WRITE"),
                        ("KPF-17.4c — localize", "KPF-17.4c"), ("Re-screen the 19 modules", ""), ("The probe over-match above", ""), ("AP-63(b) — x", "AP-63(b)")):
            self.assertEqual(bp.box_token(t), want, t)


class Blockers(unittest.TestCase):
    SPEC = [("a.md", "A-1 — land the adapter", {}), ("a.md", "B-2 — wire the report. Depends on A-1 landing first.", {}),
            ("a.md", "C-3 — final step, only after A-1 and Z-9", {})]

    def test_in_box_anchor_blocks_and_gates(self):
        r = run(self.SPEC)
        b, a = item(r, "B-2"), item(r, "A-1")
        self.assertEqual((b["lane"], b["tier"]), ("held", 3))
        self.assertEqual(a["tier"], 2)
        self.assertTrue(any("B-2" in g for g in a["gates"]))
        self.assertGreater(a["dispatch_score"], b["dispatch_score"])            # the blocked box follows its blocker

    def test_unresolvable_id_is_not_an_anchor(self):
        self.assertEqual(item(run(self.SPEC), "C-3")["blocked_by"], [item(run(self.SPEC), "A-1")["b"]["idx"]])   # A-1 yes, Z-9 (no such box) no

    def test_closed_target_is_satisfied(self):
        spec = [("a.md", "A-1 — land the adapter", {"open": False}), ("a.md", "B-2 — wire the report. Depends on A-1.", {})]
        self.assertEqual(item(run(spec), "B-2")["tier"], 2)

    def test_row_deps_are_not_inherited_into_boxes(self):                      # audit 3.2: the 11 false T1s
        spec = [("a.md", "A-1 — fix the token cap contract", {}), ("b.md", "B-2 — run the long A/B on a quiet window", {})]
        rows = {"a.md": "ROW-A", "b.md": "ROW-B"}
        plain = run(spec, rows=rows)
        dep = run(spec, rows=rows, edges=[dict(kind="dep", **{"from": "ROW-B", "to": "ROW-A"})])
        for r in (plain, dep):
            self.assertEqual(item(r, "A-1")["tier"], 2)
            self.assertEqual(item(r, "A-1")["gates"], [])

    def test_prose_in_unblocks_does_not_create_t1(self):                       # audit 3.2: the 21 N1_RX promotions
        c = curated(entries=[dict(row="T-01", tok="A-1", kind="N", s=0.9, size="S", why="record the run decision", unblocks="gate the run window fold record")])
        self.assertEqual(item(run([("a.md", "A-1 — land the adapter", {})], cur=c), "A-1")["tier"], 2)

    def test_curated_before_gate_reaches_compute(self):
        spec = [("a.md", "A-1 — write side", {}), ("a.md", "CH-30 — the champion gates", {})]
        c = curated(entries=[dict(row="T-01", tok="A-1", kind="N", s=0.8, size="S", why="", unblocks="", before="T-01:CH-30"),
                             dict(row="T-01", tok="CH-30", kind="I", s=0.9, size="M", why="", unblocks="", fillers=["gate-x"])])
        r = run(spec, queue=queue(**{"ARMED-UNBOOKED": [rec("gate-x")]}), cur=c)
        a = item(r, "A-1")
        self.assertEqual((a["tier"], a["lane"]), (1, "dispatch"))
        self.assertGreater(a["dispatch_score"], 0.7)
        self.assertEqual(item(r, "CH-30")["tier"], 4)                             # live because FILLERS says so, not because curated says so

    def test_filler_precondition_clause_makes_t1(self):
        spec = [("a.md", "BUILD-7 — land the harness fix", {}), ("a.md", "OTHER-1 — unrelated cleanup", {})]
        q = queue(**{"ARMED-UNBOOKED": [rec("job-1", notes="Precondition (refuses, never warns): BUILD-7 must be ticked")]})
        r = run(spec, queue=q)
        self.assertEqual(item(r, "BUILD-7")["tier"], 1)
        self.assertEqual(item(r, "OTHER-1")["tier"], 2)
        self.assertTrue(any("job-1" in g for g in item(r, "BUILD-7")["gates"]))


class Holds(unittest.TestCase):
    HOLDS = [dict(name="ds41-1017", pattern=r"DS41", kinds=["I"], **{"except": r"autokernel|seed ledger"}, lift="AK kernel work lands"),
             dict(name="frozen", pattern=r"^\W*(FROZEN|PARKED)\b", inherit=True, case_sensitive=True, lift="unfrozen"),
             dict(name="stack-down", pattern=r"full-stack window", lift="stack up")]

    def test_hold_is_box_scoped_by_its_own_pattern(self):                      # audit #17
        spec = [("d.md", "DS41-1 — run the DS41 decode A/B on a quiet window (llama-bench)", {}),
                ("d.md", "DS41-2 — AutoKernel seed ledger: document the seeds", {}), ("d.md", "DS41-3 — write the repack gate doc", {})]
        r = run(spec, cur=curated(holds=self.HOLDS))
        self.assertEqual(item(r, "DS41-1")["lane"], "held")
        self.assertEqual(item(r, "DS41-1")["holds"][0]["name"], "ds41-1017")
        self.assertTrue(item(r, "DS41-1")["holds"][0]["lift"])
        self.assertEqual(item(r, "DS41-2")["tier"], 2)
        self.assertEqual(item(r, "DS41-3")["tier"], 2)

    def test_topic_word_parked_is_not_a_hold(self):                            # audit #19
        r = run([("u.md", "UFH14-B6d — route escalations around a parked target (filed 2026-10-03)", {})], cur=curated(holds=self.HOLDS))
        self.assertEqual(item(r, "UFH14-B6d")["tier"], 2)

    def test_frozen_marker_holds_and_passes_to_children(self):
        spec = [("u.md", "FROZEN 2026-09-27 — resume only once A2 pays", {}), ("u.md", "CH-1 — child task", {"indent": 2, "parent": 0})]
        r = run(spec, cur=curated(holds=self.HOLDS))
        self.assertEqual([a["lane"] for a in r["items"].values() if a["is_task"]], ["held"])      # the parent collapsed; its child is held by inheritance
        self.assertTrue(item(r, "CH-1")["holds"][0].get("inherited"))

    def test_only_parked_rows_hold_at_row_level(self):
        spec = [("p.md", "P-1 — do the thing", {}), ("q.md", "Q-1 — do the other thing", {})]
        rows = {"p.md": "ROW-P", "q.md": "ROW-Q"}
        r = run(spec, rows=rows, cur=curated(park_rows={"ROW-P": "2nd MI210 exists"}))
        self.assertEqual((item(r, "P-1")["lane"], item(r, "P-1")["holds"][0]["lift"]), ("held", "2nd MI210 exists"))
        self.assertEqual(item(r, "Q-1")["lane"], "dispatch")

    def test_event_hold_names_its_lifting_condition(self):                     # audit #11
        r = run([("r.md", "REPL-EMB-2.12 - EG2 throughput in the v11 full-stack window", {})], cur=curated(holds=self.HOLDS))
        self.assertEqual(item(r, "REPL-EMB-2.12")["holds"][0]["name"], "stack-down")


class Structure(unittest.TestCase):
    def test_parent_collapses_into_children(self):                             # audit #7
        spec = [("g.md", "GPS-PIN-1 — pin every launch", {}), ("g.md", "GPS-PIN-1a — land it", {"indent": 2, "parent": 0, "open": False}),
                ("g.md", "GPS-PIN-1b — reload the roles", {"indent": 2, "parent": 0})]
        r = run(spec)
        self.assertFalse(item(r, "GPS-PIN-1")["is_task"])
        self.assertTrue(item(r, "GPS-PIN-1b")["is_task"])
        self.assertEqual(len(r["collapsed"]), 1)
        self.assertNotIn("GPS-PIN-1", [d["task"].split()[0] for d in r["doc"]["dispatch_now"]])

    def test_parent_with_all_children_closed_stays_a_task(self):
        spec = [("g.md", "GPS-PIN-9 — pin", {}), ("g.md", "GPS-PIN-9a — done", {"indent": 2, "parent": 0, "open": False})]
        self.assertTrue(item(run(spec), "GPS-PIN-9")["is_task"])

    def test_non_tasks_are_excluded_and_listed(self):                          # audit #22, #23
        spec = [("n.md", "NOT SHIPPED — ccache. The path is non-promotable by construction.", {}),
                ("n.md", "Open question — pause-loads-after-kill hook: worth doing?", {}), ("n.md", "REAL-1 — a real task", {})]
        r = run(spec)
        listed = " ".join(n["text"] for n in r["doc"]["non_tasks"])
        self.assertIn("NOT SHIPPED", listed)
        self.assertIn("Open question", listed)
        self.assertEqual([d["task"].split()[0] for d in r["doc"]["dispatch_now"]], ["REAL-1"])

    def test_struck_through_box_is_not_a_task(self):
        r = run([("n.md", "~~**Install the 5 missing deps**~~ — DOWNGRADED to optional", {}), ("n.md", "REAL-1 — a real task", {})])
        self.assertEqual([d["task"].split()[0] for d in r["doc"]["dispatch_now"]], ["REAL-1"])
        self.assertIn("struck", r["doc"]["non_tasks"][0]["why"])

    def test_done_pending_tick_is_excluded_and_reported(self):
        c = curated(done_pending_tick=[dict(row="T-01", tok="CH-24", done="patches handed over"), dict(row="T-01", tok="GONE-1", done="x")])
        r = run([("a.md", "CH-24 — gate the debug output", {})], cur=c)
        self.assertEqual(r["doc"]["dispatch_now"], [])
        self.assertEqual(r["doc"]["done_pending_tick"][0]["done"], "patches handed over")
        self.assertEqual(r["doc"]["done_stale"], ["T-01:GONE-1"])


class ComputeLane(unittest.TestCase):
    def test_order_is_status_then_quiet_atomic_build_resumable(self):
        q = queue(**{"ARMED-UNBOOKED": [
            rec("res-1", duration="~30 min"), rec("big-atomic", duration="~6 h"), rec("tree-build", duration="~40 min"),
            rec("quiet-1", **{"class": "block-timing-quiet"}, duration="~1h45m")],
            "RUNNING": [rec("run-1", status="RUNNING", ends_in_min=30)], "BOOKED": [rec("booked-1")],
            "STALE-ARMED": [rec("stale-1")], "BACKLOG": [rec("back-1", blocker="harness fix")]})
        r = run([("a.md", "A-1 — x", {})], queue=q)
        ids = [f["id"] for f in r["doc"]["compute_lane"]["lanes"]["cpu"]["items"]]
        self.assertEqual(ids, ["run-1", "booked-1", "quiet-1", "big-atomic", "tree-build", "res-1", "stale-1", "back-1"])

    def test_eta_is_computed_from_running_end_and_declared_durations(self):
        q = queue(**{"RUNNING": [rec("run-1", status="RUNNING", ends_in_min=30, shape="mi210_0 whole card", resources="mi210_0")],
                     "ARMED-UNBOOKED": [rec("next-1", shape="mi210_0 exclusive", duration="~45 min")]})
        lane = run([("a.md", "A-1 — x", {})], queue=q)["doc"]["compute_lane"]["lanes"]["gpu"]
        self.assertEqual(lane["items"][0]["eta_end"], "2026-10-24T12:30Z")
        self.assertEqual(lane["items"][1]["eta_end"], "2026-10-24T13:15Z")
        self.assertEqual(lane["eta_end"], "2026-10-24T13:15Z")

    def test_cpu_lane_packs_four_quarters_in_parallel(self):
        q = queue(**{"ARMED-UNBOOKED": [rec(f"c{k}", duration="~1 h") for k in range(5)]})
        items = run([("a.md", "A-1 — x", {})], queue=q)["doc"]["compute_lane"]["lanes"]["cpu"]["items"]
        self.assertEqual([i["eta_end"] for i in items], ["2026-10-24T13:00Z"] * 4 + ["2026-10-24T14:00Z"])

    def test_lanes_are_split_by_shape(self):
        q = queue(**{"ARMED-UNBOOKED": [rec("w", shape="WHOLE HOST quiet: region-lock --cpu-list 0-95"), rec("g", shape="mi210_0 + 184-191"),
                                        rec("c", shape="CPU: one quarter"), rec("c2", shape="turn-1 confirmation A/B", substrate="gpu")]})
        lanes = run([("a.md", "A-1 — x", {})], queue=q)["doc"]["compute_lane"]["lanes"]
        self.assertEqual({k: [f["id"] for f in v["items"]] for k, v in lanes.items()}, {"whole-host": ["w"], "gpu": ["c2", "g"], "cpu": ["c"]})

    def test_inference_box_state_comes_from_the_queue_not_the_table(self):    # audit 3.3
        spec = [("a.md", "RUN-1 — run the replay A/B on a quarter", {}), ("a.md", "RUN-2 — run the other sweep on a quarter", {})]
        c = curated(entries=[dict(row="T-01", tok="RUN-1", kind="I", s=0.9, size="M", why="", unblocks="", fillers=["live-1"]),
                             dict(row="T-01", tok="RUN-2", kind="I", s=0.9, size="M", why="", unblocks="")])
        r = run(spec, queue=queue(**{"RUNNING": [rec("live-1", status="RUNNING", ends_in_min=10)]}), cur=c)
        self.assertEqual(item(r, "RUN-1")["tier"], 4)
        self.assertEqual(item(r, "RUN-2")["tier"], 5)                             # unqueued: no table entry can make it live
        self.assertGreater(item(r, "RUN-1")["compute_score"], item(r, "RUN-2")["compute_score"])
        r2 = run(spec, queue=queue(), cur=c)
        self.assertEqual(item(r2, "RUN-1")["tier"], 5)                            # the queue moved -> the tier moved, table untouched

    def test_code_blocked_backlog_row_is_a_dispatch_item(self):                # operator ruling 10-22
        q = queue(**{"BACKLOG": [rec("wait-1", blocker="harness fix (coherence)", decision="why")], "STALE-ARMED": [rec("dead-1")]})
        d = run([("a.md", "A-1 — x", {})], queue=q)["doc"]["dispatch_now"]
        self.assertEqual({x["id"] for x in d if x["source"] == "fillers"}, {"filler:wait-1", "filler:dead-1"})

    def test_no_queue_degrades_without_crashing(self):
        r = run([("a.md", "A-1 — x", {})], queue=None)
        self.assertIsNone(r["doc"]["queue_snapshot_at"])
        self.assertEqual(r["doc"]["compute_lane"]["lanes"], {})


class OrdersAndRows(unittest.TestCase):
    def test_dispatch_now_is_capped_and_carries_the_contract_fields(self):
        spec = [("a.md", f"TASK-{k} — do small thing number {k}", {}) for k in range(70)]
        d = run(spec)["doc"]["dispatch_now"]
        self.assertEqual(len(d), bp.DISPATCH_CAP)
        for x in d:
            for k in ("rank", "id", "row", "task", "hint", "size", "gates", "owner", "brief", "dispatch_score", "tier"):
                self.assertIn(k, x)
            self.assertIn("never kill by name pattern", x["brief"])
        self.assertEqual([x["rank"] for x in d], list(range(1, 51)))

    def test_t2_has_secondary_keys(self):                                      # audit 3.1: no more 147-way ties
        spec = [("a.md", "OLD-1 — " + "x" * 900, {"touched": "2026-05-01"}), ("a.md", "NEW-1 — small fresh task", {"touched": "2026-10-24"}),
                ("a.md", "GATE-1 — small fresh gating task", {"touched": "2026-10-24"}), ("a.md", "AFTER-1 — later step, after GATE-1", {"touched": "2026-10-24"}),
                ("b.md", "INTAKE-1 — small fresh task", {"touched": "2026-10-24", "head": "Research intake"})]
        r = run(spec)
        s = lambda t: item(r, t)["dispatch_score"]
        self.assertGreater(s("NEW-1"), s("OLD-1"))                                 # size + age
        self.assertGreater(s("GATE-1"), s("NEW-1"))                                # gates something
        self.assertGreater(s("NEW-1"), s("INTAKE-1"))                              # non-intake
        self.assertEqual(len({s(t) for t in ("OLD-1", "NEW-1", "GATE-1", "INTAKE-1")}), 4)

    def test_row_priority_is_the_max_of_the_two_lanes_and_records_the_winner(self):
        spec = [("a.md", "SMALL-1 — fix a typo", {}), ("a.md", "RUN-1 — run the replay A/B on a quarter", {}), ("b.md", "ONLY-1 — fix something", {})]
        rows = {"a.md": "ROW-A", "b.md": "ROW-B"}
        c = curated(entries=[dict(row="ROW-A", tok="RUN-1", kind="I", s=0.9, size="M", why="", unblocks="", fillers=["live-1"])])
        r = run(spec, rows=rows, cur=c, queue=queue(**{"RUNNING": [rec("live-1", status="RUNNING", ends_in_min=10)]}))
        ra, rb = r["doc"]["rows"]["ROW-A"], r["doc"]["rows"]["ROW-B"]
        self.assertEqual(ra["priority"], max(ra["dispatch_score"], ra["compute_score"]))
        self.assertEqual(ra["score"], ra["priority"])
        self.assertEqual((ra["lane"], ra["tier"]), ("compute", 4))
        self.assertEqual((rb["lane"], rb["tier"]), ("dispatch", 2))
        self.assertGreater(ra["priority"], rb["priority"])

    def test_row_with_only_held_work_is_lane_held_with_a_lift(self):
        r = run([("p.md", "P-1 — do the thing", {})], rows={"p.md": "ROW-P"}, cur=curated(park_rows={"ROW-P": "2nd MI210 exists"}))
        row = r["doc"]["rows"]["ROW-P"]
        self.assertEqual((row["lane"], row["tier"]), ("held", 7))
        self.assertIn("2nd MI210", row["blocker"])
        self.assertTrue(0.0 <= row["score"] <= 1.0)

    def test_header_fields(self):
        d = run([("a.md", "A-1 — x", {})], queue=queue())["doc"]
        self.assertEqual(d["schema"], "backlog_priority.v2")
        self.assertEqual((d["queue_snapshot_at"], d["source_sha"], d["curated_unmatched"]), ("2026-10-24T12:00Z", "a" * 40, 0))
        self.assertIsNone(d["classifier_error_rate"])


class ClassifierHook(unittest.TestCase):
    def test_cache_overrides_heuristics_and_reports_error_rate(self):
        text = "ZZZ-1 — tidy the report"
        h = bp.text_hash(text)
        cache = dict(model="m", validation=dict(error_rate=0.12), entries={h: dict(kind="I", is_task=True, blocked_by=None)})
        r = run([("a.md", text, {})], cache=cache)
        self.assertEqual(item(r, "ZZZ-1")["kind"], "I")
        self.assertEqual(r["doc"]["classifier_error_rate"], 0.12)
        self.assertEqual(r["doc"]["classifier"]["cached_boxes"], 1)
        cache["entries"][h]["is_task"] = False
        self.assertFalse(item(run([("a.md", text, {})], cache=cache), "ZZZ-1")["is_task"])

    def test_cached_blocked_by_is_an_anchor(self):
        spec = [("a.md", "A-1 — base", {}), ("a.md", "B-2 — follow-up with no phrase of its own", {})]
        cache = dict(entries={bp.text_hash(spec[1][1]): dict(kind="N", is_task=True, blocked_by=["A-1"])})
        self.assertEqual(item(run(spec, cache=cache), "B-2")["tier"], 3)

    def test_batch_lists_only_uncached_boxes(self):
        spec = [("a.md", "A-1 — base", {}), ("a.md", "B-2 — other", {})]
        r = run(spec, cache=dict(entries={bp.text_hash(spec[0][1]): dict(kind="N", is_task=True)}))
        self.assertEqual(len(bp.classifier_batch(r)), 1)
        self.assertIn("B-2", bp.classifier_batch(r)[0]["text"])


class Check(unittest.TestCase):
    def setUp(self):
        self.res = run([("a.md", "A-1 — x", {})], queue=queue())
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / "bp.json"
        self.p.write_text(json.dumps(self.res["doc"]))

    def tearDown(self):
        self.tmp.cleanup()

    def probs(self, git=GIT_OK, res=None):
        return bp.check(self.res if res is None else res, self.p, git)[0]

    def test_fresh_file_passes(self):
        self.assertEqual(self.probs(), [])

    def test_older_than_newest_handoffs_commit_by_a_day_fails(self):
        g = dict(GIT_OK, newest_handoffs_commit=int((NOW + datetime.timedelta(hours=25)).timestamp()))
        self.assertTrue(any("older than the newest handoffs/ commit" in x for x in self.probs(g)))
        g = dict(GIT_OK, newest_handoffs_commit=int((NOW + datetime.timedelta(hours=23)).timestamp()))
        self.assertEqual(self.probs(g), [])

    def test_unmatched_curated_over_five_percent_fails(self):
        res = copy.deepcopy(self.res)
        res["curated"] = dict(entries=[0] * 20)
        res["unmatched"] = ["R:a"]
        self.assertEqual(self.probs(res=res), [])                                  # 1/20 = 5 % is allowed
        res["unmatched"] = ["R:a", "R:b"]
        self.assertTrue(any("match no open box" in x for x in self.probs(res=res)))

    def test_tree_behind_origin_main_fails(self):
        self.assertTrue(any("behind origin/main" in x for x in self.probs(dict(GIT_OK, behind=3))))

    def test_invalid_json_missing_file_and_missing_header_fail(self):
        self.p.write_text("{nope")
        self.assertTrue(any("not valid JSON" in x for x in self.probs()))
        self.assertTrue(bp.check(self.res, Path(self.tmp.name) / "absent.json", GIT_OK)[0])
        d = copy.deepcopy(self.res["doc"]); d.pop("queue_snapshot_at")
        self.p.write_text(json.dumps(d))
        self.assertTrue(any("queue_snapshot_at" in x for x in self.probs()))


class Sample(unittest.TestCase):
    def test_stratified_sample_and_sheet(self):
        spec = [("a.md", f"GATE-{k} — gating task {k}", {}) for k in range(8)] + [("a.md", f"FREE-{k} — free task {k}", {}) for k in range(30)]
        c = curated(entries=[dict(row="T-01", tok=f"GATE-{k}", kind="N", s=0.5, size="S", why="", unblocks="", before="filler:f1") for k in range(8)])
        r = run(spec, cur=c, queue=queue(**{"ARMED-UNBOOKED": [rec("f1", decision="pick it")]}))
        s = bp.draw_sample(r, 20, seed=1)
        self.assertEqual(len(s), 20)
        self.assertEqual({x["stratum"] for x in s}, {"T1", "T2-top", "compute", "random"})
        self.assertEqual(bp.draw_sample(r, 20, seed=1), s)                         # reproducible
        sheet = bp.render_sheet(s, r)
        self.assertIn("| verdict |", sheet)
        rows = [l for l in sheet.splitlines() if l.startswith("| ") and "stratum" not in l and "|-|" not in l]
        self.assertEqual(len(rows), 20)
        self.assertTrue(all(l.rstrip().endswith("|  |") for l in rows))            # verdict column starts empty


class CuratedTable(unittest.TestCase):
    def setUp(self):
        self.cur = json.loads(bp.CURATED_PATH.read_text(encoding="utf-8"))

    def test_schema_is_judgement_only(self):
        keys = set()
        for e in self.cur["entries"]:
            self.assertIn(e["kind"], ("I", "N", "O"), e["tok"])
            self.assertTrue(0.0 <= e["s"] <= 1.0, e["tok"])
            self.assertFalse({"cls", "blocker", "owner", "done", "new", "in_progress", "filler"} & set(e), f"live state in curated entry {e['tok']}")
            keys.add(f"{e['row']}:{e['tok']}")
        self.assertEqual(len(keys), len(self.cur["entries"]), "duplicate curated key")
        for e in self.cur["entries"]:
            b = e.get("before")
            if b and not b.startswith("filler:"):
                self.assertIn(b, keys, f"before of {e['tok']} names no curated entry")

    def test_holds_name_a_lifting_condition_and_compile(self):
        for h in self.cur["holds"]:
            self.assertTrue(h["lift"] and h["name"], h)
            re.compile(h["pattern"])
        for row, lift in self.cur["park_rows"].items():
            self.assertTrue(lift, row)
        self.assertTrue(set(self.cur["park_rows"]) <= {"UFH-13", "RTG-09", "RTG-40", "RTG-17", "INF-03"})   # row-level holds: PARKED/FROZEN files only


class RealTree(unittest.TestCase):
    """One real build; structural invariants only (live handoff text moves daily; --check owns the curated-unmatched limit)."""

    @classmethod
    def setUpClass(cls):
        cls.state, cls.boxes = bp.collect_boxes(index_state)
        cls.res = bp.build(None, index_state, cls.state, cls.boxes, queue=None, git=GIT_OK, now=NOW)
        cls.doc = cls.res["doc"]

    def test_rows_cover_open_work_and_scores_are_valid(self):
        opened = {rid for rid, r in self.state["rows"].items() if self.state["handoffs"].get(r["handoff"], {}).get("open", 0) > 0}
        self.assertLessEqual(len(opened - set(self.doc["rows"])), 3)
        for r in self.doc["rows"].values():
            self.assertTrue(0.0 <= r["score"] <= 1.0)
            self.assertIn(r["lane"], ("dispatch", "compute", "held"))
            if r["lane"] != "held":
                self.assertEqual(r["score"], max(r["dispatch_score"], r["compute_score"]))
        self.assertEqual(sorted(r["rank"] for r in self.doc["rows"].values()), list(range(1, len(self.doc["rows"]) + 1)))

    def test_t1_always_names_what_it_gates_and_dispatch_is_unblocked(self):
        for a in self.res["itemlist"]:
            if a["tier"] == 1:
                self.assertTrue(a["gates"], a["key"])
            if a["lane"] == "dispatch":
                self.assertFalse(a["holds"] or a["blocked_by"] or a["blocked_row"], a["key"])
                self.assertNotEqual(a["kind"], "I")
        self.assertLessEqual(len(self.doc["dispatch_now"]), bp.DISPATCH_CAP)
        ids = [d["id"] for d in self.doc["dispatch_now"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_no_collapsed_parent_or_non_task_is_ranked(self):
        ranked = {a["key"] for a in self.res["itemlist"]}
        for a in self.res["collapsed"]:
            self.assertNotIn(a["key"], ranked)
            self.assertTrue(any(self.boxes[c]["open"] for c in a["b"]["children"]))

    def test_committed_file_is_consumable_by_index_state(self):
        doc, probs = index_state.load_priority_file(index_state.PRIORITY_FILE)
        self.assertEqual(probs, [])
        self.assertGreater(len(doc["rows"]), 100)
        self.assertEqual(doc["schema"], "backlog_priority.v2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
