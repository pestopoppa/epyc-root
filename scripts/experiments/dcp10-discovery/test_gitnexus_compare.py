"""Synthetic controls for the DCP-10 direct-edge fixture comparator."""
import copy
import os
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

import gitnexus_compare as control

PILOT = Path(os.environ.get(
    "DCP10_TEST_PILOT", "/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10",
)).absolute()
SOURCE = Path(os.environ.get("DCP10_TEST_GITNEXUS_SOURCE", control.SOURCE_ROOT)).absolute()
PYTHON_SEEDS = ["xarray/core/dataset.py", "xarray/core/dataarray.py", "xarray/core/variable.py"]


def edge(source, target, confidence=0.95, depth=1):
    return {
        "source_id": f"node:{source}", "source_path": source, "target_id": f"node:{target}",
        "target_path": target, "confidence": confidence, "relation": "CALLS", "depth": depth,
    }


def search_hit(path, score):
    return {"score": score, "unit": {"file": path, "line": 1, "end_line": 1}}


def make_fixture(pilot_root, parent, source_root):
    tasks = control.pilot.read(pilot_root / "packet/request.json")["selected"]
    records = {}
    seeds_by_language = {"python": PYTHON_SEEDS, "c": [], "cpp": ["include/fmt/format.h"]}
    for task in tasks:
        language = task["language"]
        root = pilot_root / "bases" / language
        binding = {
            "root": str(root), "base_commit": task["base_commit"],
            "query_sha256": sha256(task["query"].encode()).hexdigest(),
            "base_tree": control.pilot.git(root, "rev-parse", "HEAD^{tree}"),
        }
        index = parent / "indexes" / language
        index.mkdir(parents=True)
        (index / "meta.json").write_text(control.pilot.encode({
            "repoPath": str(root), "lastCommit": task["base_commit"], "fixture": True,
        }), encoding="utf-8")
        (index / "lbug").write_bytes(b"synthetic fixture bytes, no database")
        seeds = seeds_by_language[language]
        records[task["task_id"]] = {
            "base": binding,
            "mock_search": [search_hit(path, 20 - rank) for rank, path in enumerate(seeds)],
            "graph": {"index_sha256": control.common.directory_digest(index), "seed_paths": seeds,
                      "edges": [], "error": None},
        }
    records[tasks[0]["task_id"]]["graph"]["edges"] = [
        edge(PYTHON_SEEDS[1], PYTHON_SEEDS[2], 0.99), edge("xarray/__init__.py", PYTHON_SEEDS[0], 0.9),
    ]
    records[tasks[2]["task_id"]]["graph"]["error"] = "synthetic query timeout"
    return {
        "schema": control.SCHEMA, "kind": "synthetic", "gitnexus_source": control.source_identity(source_root),
        "pilot_request_sha256": control.common.ORIGINAL_REQUEST_SHA,
        "lexical_predictions_sha256": control.common.LEXICAL_PREDICTIONS_SHA,
        "graph_query_sha256": control.GRAPH_QUERY_SHA, "producer_sha256": control.producer_identity(),
        "tasks": records,
    }


class RankingControls(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.tracked = {f"f{number}.py" for number in range(12)}
        self.tracked.add(".dot.py")
        for name in self.tracked:
            (self.root / name).touch()
        (self.root / "untracked.py").touch()
        (self.root / "alias.py").symlink_to(self.root / "f0.py")
        self.tracked.add("alias.py")

    def rank(self, seeds, edges):
        return control.ranked_paths(seeds, edges, root=self.root, tracked=self.tracked,
                                    excluded=lambda path: path == "f11.py")

    def test_append_cap_confidence_order_and_stable_rerank(self):
        seeds = ["f2.py", "f1.py", "f0.py"]
        edges = [
            edge("f0.py", "f1.py", 0.99), edge("f2.py", "f4.py", 0.9), edge("f3.py", "f2.py", 1),
            edge("f2.py", ".dot.py", 0.9), edge("f0.py", "f5.py", 0.89), edge("f1.py", "f11.py", 1),
        ]
        append, rerank, ranks = self.rank(seeds, edges)
        self.assertEqual(append, [*seeds, "f3.py", ".dot.py", "f4.py"])
        self.assertEqual(rerank, ["f1.py", "f0.py", "f2.py"])
        self.assertEqual(ranks["append_capacity"], 5)
        self.assertEqual(self.rank(seeds, list(reversed(edges))), (append, rerank, ranks))

    def test_full_original_rank_never_evicted(self):
        seeds = [f"f{number}.py" for number in range(control.pilot.MAX_FILES)]
        append, rerank, ranks = self.rank(seeds, [edge(seeds[0], "f10.py", 1)])
        self.assertEqual((append, rerank), (seeds, seeds))
        self.assertEqual(ranks["append_capacity"], 0)
        self.assertEqual(ranks["append_eligible"], ["f10.py"])

    def test_reject_transitive_bad_confidence_and_bad_paths(self):
        seed = ["f0.py"]
        malformed = [
            edge("f0.py", "f1.py", depth=2),
            edge("f0.py", "f1.py", depth=True),
            edge("f1.py", "f2.py"),
            edge("f0.py", "alias.py"),
            *(edge("f0.py", path) for path in ("../f1.py", "x/../f1.py", "./f1.py", "x//f1.py",
                                               str(self.root / "f1.py"), "missing.py", "untracked.py")),
            *(edge("f0.py", "f1.py", confidence) for confidence in
              (True, None, "0.95", -0.1, 1.1, float("nan"), float("inf"))),
        ]
        for bad in malformed:
            with self.subTest(edge=bad), self.assertRaises(ValueError):
                self.rank(seed, [edge("f0.py", "f1.py"), bad])

    def test_source_unavailable_blocks_replay(self):
        with self.assertRaisesRegex(ValueError, "source gate failed"):
            control.source_identity(self.root)

    def test_duplicate_capture_fields_are_invalid(self):
        with self.assertRaisesRegex(ValueError, "duplicate fixture field"):
            control.strict_json(b'{"tasks": {}, "tasks": {}}')


@unittest.skipUnless((PILOT / "packet/request.json").is_file() and (SOURCE / "package.json").is_file(),
                     "retained original pilot or installed GitNexus source unavailable")
class SealedFixtureControls(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.parent = Path(directory.name)
        self.capture = self.parent / "capture.json"
        self.fixture = make_fixture(PILOT, self.parent, SOURCE)

    def write_capture(self):
        self.capture.write_text(control.pilot.encode(self.fixture), encoding="utf-8")
        return control.common.hash_file(self.capture)

    def compare(self):
        return control.compare(PILOT, self.capture, self.write_capture(), SOURCE)

    def test_fixed_cohort_attempts_empty_failure_and_line_provenance(self):
        result = self.compare()
        self.assertEqual(result["native_execution"], "disabled")
        self.assertEqual(result["kind"], "synthetic")
        self.assertEqual(result["producer_sha256"], self.fixture["producer_sha256"])
        self.assertEqual([row["graph_status"] for row in result["outcomes"]], ["ok", "empty", "error"])
        rows = result["predictions"]
        self.assertEqual(len(rows), 9)
        self.assertEqual([row["status"] for row in rows], [
            "ok", "ok", "ok", "no_context_extracted", "no_context_extracted", "no_context_extracted",
            "ok", "error", "error",
        ])
        self.assertEqual(rows[0]["pred_files"], PYTHON_SEEDS)
        self.assertEqual(rows[1]["pred_files"], [*PYTHON_SEEDS, "xarray/__init__.py"])
        self.assertEqual(rows[2]["pred_files"], [PYTHON_SEEDS[1], PYTHON_SEEDS[2], PYTHON_SEEDS[0]])
        self.assertEqual(rows[1]["pred_spans"], rows[0]["pred_spans"])
        self.assertEqual(rows[2]["pred_spans"], rows[0]["pred_spans"])
        self.assertEqual([record["path"] for record in rows[2]["pack_candidates"]], rows[2]["pred_files"])
        scored = result["fixture_scores"]
        self.assertEqual(scored["eligible_task_count"], 3)
        for arm in scored["arms"]:
            self.assertEqual([scope["budget_tokens"] for scope in arm["scopes"]],
                             [None, *control.pilot.BUDGETS])
            for scope in arm["scopes"]:
                self.assertEqual(len(scope["per_task"]), 3)
                for row in scope["per_task"]:
                    if row["status"] != "ok":
                        self.assertEqual(set(row["metrics"].values()), {0.0})

    def test_resealed_cross_task_drift_is_retained_as_error(self):
        task_id = next(iter(self.fixture["tasks"]))
        original = copy.deepcopy(self.fixture["tasks"][task_id])
        for section, key, value, expected in (
            ("base", "base_commit", "wrong", "wrong task base"),
            ("base", "base_tree", "wrong", "wrong base tree"),
            ("base", "query_sha256", "wrong", "wrong task base"),
            ("graph", "seed_paths", [], "seed order"),
            ("graph", "index_sha256", "wrong", "index bytes"),
        ):
            self.fixture["tasks"][task_id] = copy.deepcopy(original)
            self.fixture["tasks"][task_id][section][key] = value
            with self.subTest(field=key):
                result = self.compare()
                self.assertIn(expected, result["outcomes"][0]["error"])
                self.assertEqual([row["status"] for row in result["predictions"][1:3]], ["error", "error"])
                self.assertEqual(len(result["predictions"]), 9)

    def test_index_metadata_binding_and_capture_seal(self):
        seal = self.write_capture()
        with self.assertRaisesRegex(ValueError, "sealed input drift"):
            control.compare(PILOT, self.capture, "0" * 64, SOURCE)
        self.fixture["kind"] = "native"
        with self.assertRaisesRegex(ValueError, "fixed source or protocol"):
            self.compare()
        self.fixture["kind"] = "synthetic"
        self.assertEqual(self.write_capture(), seal)
        index = self.parent / "indexes/python"
        meta = index / "meta.json"
        info = control.pilot.read(meta)
        info["lastCommit"] = "wrong"
        meta.write_text(control.pilot.encode(info), encoding="utf-8")
        task = next(iter(self.fixture["tasks"].values()))
        task["graph"]["index_sha256"] = control.common.directory_digest(index)
        self.assertIn("different root or commit", self.compare()["outcomes"][0]["error"])

    def test_source_and_original_task_coverage_cannot_be_resealed(self):
        self.fixture["gitnexus_source"]["version"] = "unknown"
        with self.assertRaisesRegex(ValueError, "fixed source or protocol"):
            self.compare()
        self.fixture["gitnexus_source"] = control.source_identity(SOURCE)
        self.fixture["tasks"].pop(next(iter(self.fixture["tasks"])))
        with self.assertRaisesRegex(ValueError, "original three-task fixture bindings"):
            self.compare()

    def test_producer_drift_is_rejected_with_a_resealed_capture(self):
        original = self.fixture["producer_sha256"].copy()
        self.assertEqual(set(original), {"gitnexus_compare.py", "colgrep_compare.py", "pilot.py"})
        for name in original:
            self.fixture["producer_sha256"] = {**original, name: "0" * 64}
            with self.subTest(producer=name), self.assertRaisesRegex(ValueError, "producer source bytes drifted"):
                self.compare()


if __name__ == "__main__":
    unittest.main()
