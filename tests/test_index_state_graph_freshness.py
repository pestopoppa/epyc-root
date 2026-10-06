#!/usr/bin/env python3
"""Focused tests for the non-fatal generated handoff-graph freshness warning."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


_REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "index_state_graph_freshness", _REPO / "scripts" / "handoffs" / "index_state.py")
index_state = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(index_state)


def _state(track="track-a", deps=None):
    return {
        "rows": {
            "AAA-1": {
                "index": "sample-index.md", "track": track, "handoff": None,
                "next_action": "continue", "deps": list(deps or ()),
            },
        },
        "handoffs": {},
    }


class GraphFreshnessWarnings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.graph = Path(self.tmp.name) / ".index-graph.json"
        self.graph_patch = patch.object(index_state, "GRAPH", self.graph)
        self.graph_patch.start()
        self.addCleanup(self.graph_patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def _write_graph(self, state):
        self.graph.write_text(json.dumps(index_state.build_graph(state)), encoding="utf-8")

    def test_missing_graph_is_advisory(self):
        self.assertIn("missing", index_state.graph_freshness_warnings(_state())[0])

    def test_invalid_json_and_non_object_are_reported(self):
        self.graph.write_text("{broken", encoding="utf-8")
        self.assertIn("invalid JSON", index_state.graph_freshness_warnings(_state())[0])
        self.graph.write_text("[]", encoding="utf-8")
        self.assertIn("malformed", index_state.graph_freshness_warnings(_state())[0])

    def test_fresh_graph_ignores_only_generated_at(self):
        state = _state()
        self._write_graph(state)
        graph = json.loads(self.graph.read_text(encoding="utf-8"))
        graph["generated_at"] = "2000-01-01T00:00:00Z"
        self.graph.write_text(json.dumps(graph), encoding="utf-8")
        self.assertEqual(index_state.graph_freshness_warnings(state), [])

    def test_real_node_edge_and_schema_changes_are_stale(self):
        state = _state()
        for mutate in (
            lambda graph: graph["nodes"][0].update(track="changed"),
            lambda graph: graph["edges"].append(
                {"from": "AAA-1", "to": "BBB-2", "kind": "dep"}),
            lambda graph: graph.update(schema="index_graph.v1"),
        ):
            with self.subTest(mutate=mutate):
                graph = index_state.build_graph(state)
                mutate(graph)
                self.graph.write_text(json.dumps(graph), encoding="utf-8")
                self.assertIn("stale", index_state.graph_freshness_warnings(state)[0])

    def test_existing_hard_check_failure_is_unchanged(self):
        state = {"rows": {}, "handoffs": {}}
        self.graph.write_text("not json", encoding="utf-8")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(index_state, "collect", return_value=state), \
             patch.object(index_state, "check", return_value=["HARD CHECK"]), \
             patch.object(index_state, "citation_check", return_value=[]), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            rc = index_state.main(["--check"])
        self.assertEqual(rc, 1)
        self.assertIn("1 problem(s)", stdout.getvalue())
        self.assertIn("ADVISORY WARNING:", stderr.getvalue())

    def test_advisory_warning_does_not_fail_or_rewrite_graph(self):
        state = {"rows": {}, "handoffs": {}}
        self.graph.write_text("invalid graph receipt", encoding="utf-8")
        original = self.graph.read_bytes()
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(index_state, "collect", return_value=state), \
             patch.object(index_state, "check", return_value=[]), \
             patch.object(index_state, "citation_check", return_value=[]), \
             redirect_stdout(stdout), redirect_stderr(stderr):
            rc = index_state.main(["--check"])
        self.assertEqual(rc, 0)
        self.assertIn("0 problem(s)", stdout.getvalue())
        self.assertIn("ADVISORY WARNING:", stderr.getvalue())
        self.assertEqual(self.graph.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
