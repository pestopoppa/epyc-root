#!/usr/bin/env python3
"""Unit tests for index_state.derive_readiness — the derived ready/blocked/no_open channel.

Stdlib ``unittest`` only (no pytest dependency) so it runs anywhere with
``python3 tests/test_index_state_readiness.py``; pytest also discovers it. Sibling of
``test_index_state_dep_cycles.py`` and follows its conventions, including the pairing
discipline below.

WHY THIS FILE EXISTS. The graph carried `open` and `last_advanced` per node but never answered
the only question a dispatcher asks — *can this be picked up right now?* — so the readiness
computation had to be re-derived by hand each time, and the one time it was actually run (by
hand, 2026-09-07) it immediately surfaced the INF-06 ⇄ INF-64 dep cycle that had been rendering
as two ordinary dispatchable rows. `index_graph.v2` makes that computation a product of the
builder instead of an errand.

THE RULE, and nothing more: a node is **blocked** iff at least one of its `dep` edge targets
still has `open > 0`; otherwise **ready**; and a node with `open == 0` of its own is
**no_open**, because it is neither dispatchable nor gated. `no_open` is deliberately not
"closed" — `open` counts DISPATCHABLE boxes, so it is also 0 for a handoff whose remaining
boxes are all guarded, and this module's parent already rules that `open == 0` is not
completion.

Each positive case is paired with a MUTATION case proving the derivation is what produced the
verdict: flip exactly one thing (the target's open count, the edge kind, the id's existence)
and the same graph must land on a different value. Without that pairing a test can pass
because the fixture is inert rather than because the code under test fired.
"""

import importlib.util
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


index_state = _load("index_state", "scripts/handoffs/index_state.py")
compute_ready = _load("compute_ready", "scripts/coordination/compute_ready.py")


def nodes(**opens: int) -> list[dict]:
    """`A=3, B=0` -> the node list `derive_readiness` reads (id + open count)."""
    return [{"id": rid, "open": n} for rid, n in opens.items()]


def deps(*pairs: tuple[str, str]) -> list[dict]:
    return [{"from": src, "to": dst, "kind": "dep"} for src, dst in pairs]


def verdicts(node_list: list[dict], edge_list: list[dict]) -> dict[str, str]:
    index_state.derive_readiness(node_list, edge_list)
    return {n["id"]: n["readiness"] for n in node_list}


class DeriveReadiness(unittest.TestCase):

    def test_no_deps_and_open_work_is_ready(self):
        self.assertEqual(verdicts(nodes(A=3), []), {"A": "ready"})

    def test_dep_on_an_open_row_blocks(self):
        self.assertEqual(verdicts(nodes(A=3, B=2), deps(("A", "B"))),
                         {"A": "blocked", "B": "ready"})

    def test_mutation_closing_the_dep_target_makes_it_ready(self):
        # Same graph, B's open count zeroed: A must flip to ready. This is what proves the
        # test above fails for the right reason — the dep edge alone does not block.
        self.assertEqual(verdicts(nodes(A=3, B=0), deps(("A", "B"))),
                         {"A": "ready", "B": "no_open"})

    def test_one_open_dep_among_several_closed_ones_still_blocks(self):
        self.assertEqual(
            verdicts(nodes(A=3, B=0, C=0, D=1), deps(("A", "B"), ("A", "C"), ("A", "D")))["A"],
            "blocked")

    def test_mutation_closing_the_last_open_dep_clears_the_block(self):
        self.assertEqual(
            verdicts(nodes(A=3, B=0, C=0, D=0), deps(("A", "B"), ("A", "C"), ("A", "D")))["A"],
            "ready")

    def test_blocked_by_names_only_the_deps_that_actually_gate(self):
        # A tooltip that listed every dep would say "blocked by C" about a finished row.
        ns = nodes(A=3, B=2, C=0, D=1)
        index_state.derive_readiness(ns, deps(("A", "B"), ("A", "C"), ("A", "D")))
        self.assertEqual({n["id"]: n["blocked_by"] for n in ns},
                         {"A": ["B", "D"], "B": [], "C": [], "D": []})

    def test_no_open_wins_over_a_blocking_dep(self):
        # A has nothing to dispatch, so "blocked" would be a lie about work that does not
        # exist: there is no unit of work here for B to be holding up.
        self.assertEqual(verdicts(nodes(A=0, B=2), deps(("A", "B")))["A"], "no_open")

    def test_mutation_giving_the_same_node_open_work_makes_it_blocked(self):
        self.assertEqual(verdicts(nodes(A=1, B=2), deps(("A", "B")))["A"], "blocked")

    def test_unknown_dep_id_does_not_block(self):
        # `--check`'s BAD DEP already owns the dangling-id error. Gating on it here would
        # report one bad cell twice AND park a dispatchable row behind a typo.
        self.assertEqual(verdicts(nodes(A=3), deps(("A", "NOPE"))), {"A": "ready"})

    def test_mutation_the_same_id_when_it_exists_and_is_open_does_block(self):
        # Identical edge; only the target's existence changed. Proves the skip above is the
        # unknown-id rule and not a dead code path that never blocks on anything.
        self.assertEqual(verdicts(nodes(A=3, NOPE=1), deps(("A", "NOPE")))["A"], "blocked")

    def test_ref_edges_never_gate(self):
        # A `ref` edge is "this handoff's markdown links to that one" and claims nothing about
        # ordering. 530+ of them exist; treating one as a dep would block most of the board.
        edges = [{"from": "A", "to": "B", "kind": "ref", "weight": 4}]
        self.assertEqual(verdicts(nodes(A=3, B=2), edges)["A"], "ready")

    def test_mutation_the_same_edge_as_a_dep_does_gate(self):
        edges = [{"from": "A", "to": "B", "kind": "dep"}]
        self.assertEqual(verdicts(nodes(A=3, B=2), edges)["A"], "blocked")

    def test_direction_is_not_symmetric(self):
        # A depends on B, so A waits for B and never the reverse. An inverted arrow would
        # produce the mirror image of this and be equally self-consistent, which is exactly
        # why the heuristic dep import was rejected.
        self.assertEqual(verdicts(nodes(A=1, B=1), deps(("A", "B"))),
                         {"A": "blocked", "B": "ready"})

    def test_transitive_dep_does_not_reach_through_a_closed_middle(self):
        # A -> B -> C with B finished. A is ready: the rule is one hop by construction, and
        # a finished B means nothing is left for C to hold up on A's behalf.
        self.assertEqual(verdicts(nodes(A=1, B=0, C=5), deps(("A", "B"), ("B", "C")))["A"],
                         "ready")

    def test_cycle_members_are_all_blocked(self):
        # The honest consequence of a cycle: neither row can ever become ready. `dep_cycles`
        # in `--check` is what calls it a DEFECT; this function only reports the effect.
        self.assertEqual(verdicts(nodes(A=1, B=1), deps(("A", "B"), ("B", "A"))),
                         {"A": "blocked", "B": "blocked"})

    def test_mutation_breaking_the_back_edge_frees_one_end(self):
        # The real INF-06/INF-64 fix, reduced: delete the rider-of back-edge and B becomes
        # dispatchable, which is the state that was destroyed by writing it into a
        # blocked-on column.
        self.assertEqual(verdicts(nodes(A=1, B=1), deps(("A", "B"))),
                         {"A": "blocked", "B": "ready"})

    def test_every_node_is_stamped_and_the_tally_matches(self):
        # A node missing `readiness` renders as an unclassified dot rather than an error, so
        # the count identity is the guard that nothing was skipped.
        ns = nodes(A=1, B=1, C=0, D=2)
        counts = index_state.derive_readiness(ns, deps(("A", "B")))
        self.assertEqual(counts, {"ready": 2, "blocked": 1, "no_open": 1})
        self.assertEqual(sum(counts.values()), len(ns))
        self.assertTrue(all("readiness" in n and "blocked_by" in n for n in ns))

    def test_empty_graph_tallies_zero_rather_than_raising(self):
        self.assertEqual(index_state.derive_readiness([], []),
                         {"ready": 0, "blocked": 0, "no_open": 0})


class GraphSchemaV2(unittest.TestCase):
    """The bump itself, and the one consumer that pins the schema string."""

    def _graph(self) -> dict:
        rows = {
            "A": {"id": "A", "index": "x-index.md", "line": 1, "track": "t",
                  "handoff": "a.md", "next_action": "go", "deps": ["B"]},
            "B": {"id": "B", "index": "x-index.md", "line": 2, "track": "t",
                  "handoff": "b.md", "next_action": "go", "deps": []},
            "C": {"id": "C", "index": "x-index.md", "line": 3, "track": "t",
                  "handoff": "c.md", "next_action": "go", "deps": []},
        }
        handoffs = {
            "a.md": {"open": 2, "closed": 0, "blocked": 0, "state": "active",
                     "last_advanced": None},
            "b.md": {"open": 1, "closed": 0, "blocked": 0, "state": "active",
                     "last_advanced": None},
            "c.md": {"open": 0, "closed": 4, "blocked": 0, "state": "active",
                     "last_advanced": None},
        }
        return index_state.build_graph({"rows": rows, "handoffs": handoffs})

    def test_build_graph_emits_v2_with_readiness_on_every_node(self):
        graph = self._graph()
        self.assertEqual(graph["schema"], "index_graph.v2")
        self.assertEqual({n["id"]: n["readiness"] for n in graph["nodes"]},
                         {"A": "blocked", "B": "ready", "C": "no_open"})
        self.assertEqual(graph["readiness_counts"],
                         {"ready": 1, "blocked": 1, "no_open": 1})

    def test_v2_is_additive_so_every_v1_node_field_survives(self):
        # The bump must not be an excuse to rename anything: a v1 reader stays correct only
        # if the fields it already reads are all still there under the same names.
        node = self._graph()["nodes"][0]
        for field in ("id", "domain", "track", "handoff", "next_action", "state", "open",
                      "closed", "blocked", "last_advanced", "age_days"):
            self.assertIn(field, node)

    def test_compute_ready_accepts_v2(self):
        # The one module that pins the schema string (`validate_graph`). If this fails, the
        # bump silently breaks the ready-window projection rather than the graph.
        graph = {"schema": "index_graph.v2",
                 "nodes": [{"id": "A", "state": "active", "open": 1}], "edges": []}
        h = "a" * 64
        self.assertEqual(compute_ready.validate_graph(graph, h, h), {"A": graph["nodes"][0]})

    def test_compute_ready_still_accepts_v1(self):
        # Widened, not moved: a hash-pinned older artifact must stay readable.
        graph = {"schema": "index_graph.v1",
                 "nodes": [{"id": "A", "state": "active", "open": 1}], "edges": []}
        h = "a" * 64
        self.assertEqual(compute_ready.validate_graph(graph, h, h), {"A": graph["nodes"][0]})

    def test_mutation_compute_ready_still_refuses_an_unknown_schema(self):
        # Proves the two tests above pass because the schema is on the accept list, not
        # because the check was deleted.
        graph = {"schema": "index_graph.v3",
                 "nodes": [{"id": "A", "state": "active", "open": 1}], "edges": []}
        h = "a" * 64
        with self.assertRaises(compute_ready.ContractError) as caught:
            compute_ready.validate_graph(graph, h, h)
        self.assertEqual(caught.exception.code, "wrong_graph_schema")


class LiveArtifact(unittest.TestCase):
    """Against the artifact actually on disk, when there is one.

    Absolute counts are NOT pinned — they move with every checkbox — but the derivation must
    agree with itself: recomputing readiness from the artifact's own nodes and edges has to
    reproduce what the artifact carries. A stale or hand-edited value fails here.
    """

    def setUp(self):
        path = _REPO / "handoffs" / "active" / ".index-graph.json"
        if not path.exists():
            self.skipTest("no .index-graph.json in this checkout (generated, git-ignored)")
        import json
        self.graph = json.loads(path.read_text(encoding="utf-8"))

    def test_live_graph_is_v2_and_self_consistent(self):
        self.assertEqual(self.graph["schema"], "index_graph.v2")
        stamped = {n["id"]: n["readiness"] for n in self.graph["nodes"]}
        recomputed = [{"id": n["id"], "open": n["open"]} for n in self.graph["nodes"]]
        counts = index_state.derive_readiness(recomputed, self.graph["edges"])
        self.assertEqual({n["id"]: n["readiness"] for n in recomputed}, stamped)
        self.assertEqual(counts, self.graph["readiness_counts"])

    def test_live_graph_has_no_row_blocked_by_an_unknown_id(self):
        # The skip rule, on real data: every id in a `blocked_by` must be a real node, or the
        # graph is gating rows on typos that BAD DEP is separately reporting.
        ids = {n["id"] for n in self.graph["nodes"]}
        dangling = {n["id"]: [b for b in n["blocked_by"] if b not in ids]
                    for n in self.graph["nodes"]}
        self.assertEqual({k: v for k, v in dangling.items() if v}, {})


if __name__ == "__main__":
    unittest.main()
