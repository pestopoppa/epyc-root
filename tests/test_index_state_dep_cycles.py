#!/usr/bin/env python3
"""Unit tests for index_state.dep_cycles — cycles in the hand-authored `Deps` graph.

Stdlib ``unittest`` only (no pytest dependency) so it runs anywhere with
``python3 tests/test_index_state_dep_cycles.py``; pytest also discovers it.

WHY THIS FILE EXISTS. `--check` validated that a dep points at a KNOWN row (`BAD DEP`) and
nothing else. It could not see a dep pointing at something that points back, and a cycle is
strictly worse than a dangling id: every row on it is permanently unreachable under any
readiness rule, while still rendering as an ordinary dispatchable row in its domain index, in
the master rollup and on the hub graph. It is invisible precisely because each individual edge
is well-formed.

Found live on 2026-09-07 by running the readiness computation for the first time:
`inference-research-index.md` listed INF-64 among INF-06's deps and INF-06 as INF-64's only
dep. The back-edge was expressing RIDER-OF — `autokernel-restart-and-strip.md` says in its own
header "This is a rider on autokernel-research-loop.md ... Owning index row: INF-06" — in a
column whose only semantic is BLOCKED-ON. That relationship was already carried as a derived
`ref` edge, so deleting the `dep` back-edge lost nothing.

Each positive case is paired with a MUTATION case proving the detector is what rejects it:
break the cycle and the same graph becomes clean. Without that pairing a test can pass because
the fixture is inert rather than because the guard fires.
"""

import importlib.util
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "index_state", _REPO / "scripts" / "handoffs" / "index_state.py")
index_state = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(index_state)


def state(graph: dict[str, list[str]]) -> dict:
    """`{row_id: [dep_ids]}` -> the shape `dep_cycles` reads."""
    return {"rows": {k: {"deps": v} for k, v in graph.items()}}


class DepCycles(unittest.TestCase):

    def test_acyclic_graph_is_clean(self):
        self.assertEqual(dep_errs({"A": ["B"], "B": ["C"], "C": []}), 0)

    def test_diamond_is_not_a_cycle(self):
        # Two paths to one node is a normal shape and must not be reported.
        self.assertEqual(dep_errs({"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}), 0)

    def test_two_cycle_detected(self):
        errs = index_state.dep_cycles(state({"A": ["B"], "B": ["A"]}))
        self.assertEqual(len(errs), 1)
        self.assertIn("DEP CYCLE", errs[0])
        self.assertIn("A -> B -> A", errs[0])

    def test_two_cycle_mutation_breaking_the_back_edge_clears_it(self):
        # Same graph, back-edge removed: the detector must go quiet. This is what proves the
        # test above fails for the right reason.
        self.assertEqual(dep_errs({"A": ["B"], "B": []}), 0)

    def test_three_cycle_detected(self):
        errs = index_state.dep_cycles(state({"A": ["B"], "B": ["C"], "C": ["A"]}))
        self.assertEqual(len(errs), 1)
        self.assertIn("A -> B -> C -> A", errs[0])

    def test_self_loop_detected(self):
        errs = index_state.dep_cycles(state({"A": ["A"]}))
        self.assertEqual(len(errs), 1)
        self.assertIn("A -> A", errs[0])

    def test_each_cycle_reported_once_not_once_per_entry_point(self):
        # D reaches the A->B->C->A cycle without being on it. Reporting the same cycle twice
        # would make one defect look like two and train readers to skim the errors.
        errs = index_state.dep_cycles(
            state({"A": ["B"], "B": ["C"], "C": ["A"], "D": ["A"]}))
        self.assertEqual(len(errs), 1)

    def test_two_disjoint_cycles_reported_separately(self):
        errs = index_state.dep_cycles(
            state({"A": ["B"], "B": ["A"], "C": ["D"], "D": ["C"]}))
        self.assertEqual(len(errs), 2)

    def test_unknown_dep_is_left_to_BAD_DEP(self):
        # A dep pointing at a row that does not exist is already an error with its own message.
        # Emitting a second one here would double-count one bad cell.
        self.assertEqual(dep_errs({"A": ["NOPE"]}), 0)

    def test_regression_the_real_INF_06_INF_64_shape(self):
        # The live defect, reduced. Pinned so a future edit that re-adds the back-edge fails
        # here rather than being found again by hand a year later.
        errs = index_state.dep_cycles(state({
            "INF-06": ["INF-48", "EVL-47", "INF-64"],
            "INF-64": ["INF-06"],
            "INF-48": [], "EVL-47": [],
        }))
        self.assertEqual(len(errs), 1)
        self.assertIn("INF-06 -> INF-64 -> INF-06", errs[0])

    def test_regression_the_shipped_fix_is_clean(self):
        # Same rows with the rider back-edge deleted — the state actually committed.
        self.assertEqual(dep_errs({
            "INF-06": ["INF-48", "EVL-47", "INF-64"],
            "INF-64": [],
            "INF-48": [], "EVL-47": [],
        }), 0)

    def test_check_surfaces_cycles_through_the_public_entry_point(self):
        # dep_cycles is correct in isolation; this pins that `check()` actually calls it, which
        # is the property that makes `--check` a gate rather than a decoration.
        self.assertIn("errs.extend(dep_cycles(state))",
                      (_REPO / "scripts" / "handoffs" / "index_state.py").read_text())


def dep_errs(graph: dict[str, list[str]]) -> int:
    return len(index_state.dep_cycles(state(graph)))


if __name__ == "__main__":
    unittest.main()
