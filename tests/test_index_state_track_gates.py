#!/usr/bin/env python3
"""Per-track gates in index_state (BRF-T2-1) and the warn-only task_lint column (BRF-T6-2).

Stdlib ``unittest`` only; runs as ``python3 tests/test_index_state_track_gates.py`` or under pytest.

Route 1b of the 2026-11 backlog refactor folds several handoffs into one file with one
``## Track: <name>`` section per source. Whole-handoff readiness would then let one gated track
block every other track in the file. A track declares its own gates with ONE marker:

    ## Track: <name>
    <!-- gate: INF-65, BRF-T2-1 -->     (row ids and/or task ids)   |   <!-- gate: none -->

Each positive case is paired with a mutation that flips exactly one input and must flip the
verdict, so a test cannot pass on an inert fixture.
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


index_state = _load("index_state_tg", "scripts/handoffs/index_state.py")

FOLDED = """# Folded program

Status: active

## Track: alpha
<!-- gate: GATE-ROW -->

- [ ] **ALPHA-1** [non-inference] Implement the alpha parser. Done when: tests pass.
- [x] **ALPHA-0** [non-inference] Write the alpha schema. Done when: committed.

## Track: beta
<!-- gate: none -->

- [ ] **BETA-1** [non-inference] Implement the beta writer. Done when: tests pass.
- [ ] **BETA-2** [non-inference] Implement the beta reader. Done when: tests pass.

## Notes

- [ ] **LOOSE-1** [non-inference] Implement the loose adapter. Done when: tests pass.
"""


def track(name, gates, dispatchable):
    return {"name": name, "line": 1, "gates": gates, "open": dispatchable, "dispatchable": dispatchable}


def dep(src, dst):
    return {"from": src, "to": dst, "kind": "dep"}


class DeriveReadinessTracks(unittest.TestCase):
    def test_two_track_fold_one_blocked_one_ready(self):
        nodes = [{"id": "FOLD", "open": 3, "dispatchable": 3,
                  "tracks": [track("alpha", ["GATE"], 1), track("beta", [], 2)]},
                 {"id": "GATE", "open": 4, "dispatchable": 4}]
        index_state.derive_readiness(nodes, [])
        fold = nodes[0]
        self.assertEqual([t["readiness"] for t in fold["tracks"]], ["blocked", "ready"])
        self.assertEqual(fold["tracks"][0]["blocked_by"], ["GATE"])
        self.assertEqual(fold["readiness"], "ready")      # one ready track => dispatchable now
        self.assertEqual(fold["blocked_by"], [])

    def test_mutation_both_tracks_gated_blocks_node(self):
        nodes = [{"id": "FOLD", "open": 3, "dispatchable": 3,
                  "tracks": [track("alpha", ["GATE"], 1), track("beta", ["GATE2"], 2)]},
                 {"id": "GATE", "open": 4}, {"id": "GATE2", "open": 1}]
        counts = index_state.derive_readiness(nodes, [])
        self.assertEqual(nodes[0]["readiness"], "blocked")
        self.assertEqual(nodes[0]["blocked_by"], ["GATE", "GATE2"])
        self.assertEqual(counts, {"ready": 2, "blocked": 1, "no_open": 0})

    def test_mutation_gate_closed_unblocks_track(self):
        nodes = [{"id": "FOLD", "open": 1, "dispatchable": 1,
                  "tracks": [track("alpha", ["GATE"], 1), track("beta", [], 0)]},
                 {"id": "GATE", "open": 0}]
        index_state.derive_readiness(nodes, [])
        self.assertEqual(nodes[0]["tracks"][0]["readiness"], "ready")
        self.assertEqual(nodes[0]["tracks"][1]["readiness"], "no_open")
        self.assertEqual(nodes[0]["readiness"], "ready")

    def test_gate_on_task_id(self):
        def run(open_n):
            nodes = [{"id": "FOLD", "open": 1, "dispatchable": 1,
                      "tracks": [track("alpha", ["BRF-T2-1"], 1)]}]
            index_state.derive_readiness(nodes, [], {"BRF-T2-1": {"open": open_n, "closed": 1 - open_n}})
            return nodes[0]
        blocked = run(1)
        self.assertEqual((blocked["readiness"], blocked["blocked_by"]), ("blocked", ["BRF-T2-1"]))
        self.assertEqual(run(0)["readiness"], "ready")    # mutation: tick the task

    def test_unknown_gate_ref_is_skipped_not_blocking(self):
        nodes = [{"id": "FOLD", "open": 1, "tracks": [track("alpha", ["NOPE-9"], 1)]}]
        index_state.derive_readiness(nodes, [], {})
        self.assertEqual(nodes[0]["readiness"], "ready")

    def test_row_deps_gate_only_unmarked_tracks(self):
        def run(gates):
            nodes = [{"id": "FOLD", "open": 1, "tracks": [track("alpha", gates, 1)]},
                     {"id": "DEP", "open": 2}]
            index_state.derive_readiness(nodes, [dep("FOLD", "DEP")])
            return nodes[0]["readiness"]
        self.assertEqual(run([]), "ready")        # declared `gate: none` — row Deps do not apply
        self.assertEqual(run(None), "blocked")    # no marker — inherits the row's Deps

    def test_legacy_nodes_unchanged(self):
        def run(**kw):
            nodes = [{"id": "A", "open": 2}, {"id": "B", "open": 1}, {"id": "C", "open": 0},
                     {"id": "D", "open": 3}]
            edges = [dep("A", "B"), dep("D", "C"), dep("D", "MISSING")]
            counts = index_state.derive_readiness(nodes, edges, **kw)
            return counts, [(n["readiness"], n["blocked_by"]) for n in nodes]
        expect = ({"ready": 2, "blocked": 1, "no_open": 1},
                  [("blocked", ["B"]), ("ready", []), ("no_open", []), ("ready", [])])
        self.assertEqual(run(), expect)
        self.assertEqual(run(task_states={"B": {"open": 0}}), expect)   # task map never touches legacy


class ScanTracks(unittest.TestCase):
    def _write(self, text):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = Path(d.name) / "folded.md"
        p.write_text(text, encoding="utf-8")
        return p

    def test_folded_file_counts_per_track(self):
        st = index_state.scan_handoff(self._write(FOLDED))
        self.assertEqual((st["open"], st["closed"]), (4, 1))
        by = {t["name"]: t for t in st["tracks"]}
        self.assertEqual(by["alpha"]["gates"], ["GATE-ROW"])
        self.assertEqual((by["alpha"]["open"], by["alpha"]["closed"]), (1, 1))
        self.assertEqual((by["beta"]["gates"], by["beta"]["open"]), ([], 2))
        self.assertEqual((by[index_state.UNTRACKED]["gates"], by[index_state.UNTRACKED]["open"]), (None, 1))

    def test_folded_file_end_to_end_readiness(self):
        st = index_state.scan_handoff(self._write(FOLDED))
        node = {"id": "FOLD", "open": st["open"], "dispatchable": st["open"],
                "tracks": [{"name": t["name"], "line": t["line"], "gates": t["gates"],
                            "open": t["open"], "dispatchable": t["open"]} for t in st["tracks"]]}
        nodes = [node, {"id": "GATE-ROW", "open": 5}, {"id": "ROWDEP", "open": 1}]
        index_state.derive_readiness(nodes, [dep("FOLD", "ROWDEP")])
        got = {t["name"]: t["readiness"] for t in node["tracks"]}
        self.assertEqual(got, {"alpha": "blocked", "beta": "ready", index_state.UNTRACKED: "blocked"})
        self.assertEqual(node["readiness"], "ready")

    def test_track_headings_without_marker_are_legacy(self):
        legacy = FOLDED.replace("<!-- gate: GATE-ROW -->\n", "").replace("<!-- gate: none -->\n", "")
        p = self._write(legacy)
        self.assertEqual(index_state.scan_tracks(p), [])
        st = index_state.scan_handoff(p)
        self.assertNotIn("tracks", st)
        self.assertEqual(st, {"open": 4, "closed": 1, "guarded": 0, "blocked": 0, "total": 5})

    def test_gate_refs_parse(self):
        self.assertEqual(index_state.parse_gate_refs("INF-65, `BRF-T2-1`;X-1"), ["INF-65", "BRF-T2-1", "X-1"])
        self.assertEqual(index_state.parse_gate_refs("none"), [])


class CheckAndLint(unittest.TestCase):
    _live = None

    def _state(self, gates, markers=1):
        """The live tree's state with ONE track injected into its first handoff."""
        import copy
        if CheckAndLint._live is None:
            CheckAndLint._live = index_state.collect()
        st = copy.deepcopy(CheckAndLint._live)
        name = sorted(st["handoffs"])[0]
        st["handoffs"][name]["tracks"] = [{"name": "alpha", "line": 5, "gates": gates, "markers": markers}]
        row = next(iter(st["rows"]))
        st["gate_tasks"] = {"ZZ-TASK-1": {"open": 1, "closed": 0}}
        return st, row

    def _bad_gates(self, state):
        return [e for e in index_state.check(state) if e.startswith("BAD GATE")]

    def test_bad_gate_reported(self):
        st, row = self._state(None)
        for t in st["handoffs"][sorted(st["handoffs"])[0]]["tracks"]:
            t["gates"] = [row, "ZZ-TASK-1", "NOPE-9"]
        self.assertEqual(len(self._bad_gates(st)), 1)
        st, row = self._state(None)
        st["handoffs"][sorted(st["handoffs"])[0]]["tracks"][0]["gates"] = [row, "ZZ-TASK-1"]
        self.assertEqual(self._bad_gates(st), [])                     # mutation: drop the typo
        st, _ = self._state([], markers=2)
        self.assertEqual(len(self._bad_gates(st)), 1)

    def test_task_lint_column_is_advisory(self):
        lines = index_state.task_lint_column({})
        self.assertTrue(lines[0].startswith("TASK-LINT (warn-only"), lines[0])
        saved = index_state.REPO_ROOT
        index_state.REPO_ROOT = Path(tempfile.gettempdir()) / "ws58-no-such-root"
        try:
            broken = index_state.task_lint_column({})
        finally:
            index_state.REPO_ROOT = saved
        self.assertEqual(len(broken), 1)
        self.assertIn("lint unavailable", broken[0])


if __name__ == "__main__":
    unittest.main()
