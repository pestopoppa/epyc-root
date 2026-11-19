"""Controls against retained sealed inputs with synthetic ColGREP assets and output."""
import json
import os
import subprocess
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import colgrep_compare as comparator

PILOT = Path(os.environ.get(
    "DCP10_TEST_PILOT", "/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp10",
)).absolute()


def write_json(path, data):
    path.write_text(comparator.pilot.encode(data), encoding="utf-8")
    return comparator.hash_file(path)


def hit(file, score=1, start=1, end=1):
    return {"score": score, "unit": {"file": file, "line": start, "end_line": end}}


class ResultControls(unittest.TestCase):
    def test_result_path_requires_tracked_regular_source(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "base"
            root.mkdir()
            tracked = root / "src.py"
            tracked.touch()
            untracked = root / "scratch.py"
            untracked.touch()
            external = parent / "outside.py"
            external.touch()
            alias = root / "alias.py"
            alias.symlink_to(external)
            scope = {"src.py", "alias.py"}
            self.assertEqual(comparator.read_path(root, str(tracked), scope), "src.py")
            for path in (str(untracked), "../outside.py", str(external), str(alias), ".git"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    comparator.read_path(root, path, scope)

    def test_result_shape_scores_and_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.py").touch()
            scope = {"source.py"}
            self.assertEqual(comparator.normalize_hits([hit("source.py", 0.75)], root, 1, scope), [
                {"file": "source.py", "score": 0.75, "start_line": 1, "end_line": 1},
            ])
            invalid = [
                {"results": []}, [{}], [hit("source.py", float("nan"))],
                [hit("source.py", score=True)], [hit("source.py", start=0)],
                [hit("source.py", start=2, end=1)], [hit("source.py")] * 2,
            ]
            for raw in invalid:
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    comparator.normalize_hits(raw, root, 1, scope)


@unittest.skipUnless((PILOT / "packet/request.json").is_file(), "retained DCP-10 pilot unavailable")
class SealedComparatorControls(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.assets = Path(directory.name)
        binary = self.assets / "bin/colgrep"
        binary.parent.mkdir()
        binary.write_bytes(b"fixture data, never an executable program")
        binary.chmod(0o700)
        binary_sha = comparator.hash_file(binary)
        binary_patch = patch.object(comparator, "BINARY_SHA", binary_sha)
        binary_patch.start()
        self.addCleanup(binary_patch.stop)
        model = self.assets / "model"
        model.mkdir()
        (model / "dummy-model").write_bytes(b"synthetic fixture")
        model_sha = comparator.directory_digest(model)
        self.selected = comparator.pilot.read(PILOT / "packet/request.json")["selected"]
        self.projects = {}
        bindings = {}
        for task in self.selected:
            language = task["language"]
            root = PILOT / "bases" / language
            data_home = self.assets / "bases" / language
            project = data_home / "colgrep/indices/mock"
            (project / "index").mkdir(parents=True)
            write_json(project / "project.json", {"project_path": str(root)})
            write_json(project / "state.json", {"fixture": True})
            write_json(project / "index/metadata.json", {"fixture": True})
            (project / "index/dummy-index").write_bytes(b"synthetic fixture")
            self.projects[language] = project
            bindings[task["task_id"]] = {
                "base_commit": task["base_commit"],
                "base_tree": comparator.pilot.git(root, "rev-parse", "HEAD^{tree}"),
                "root": str(root),
                "app_revision": comparator.pilot.APP_REV,
                "query_sha256": sha256(task["query"].encode()).hexdigest(),
                "binary_sha256": binary_sha,
                "model_revision": comparator.MODEL_REVISION,
                "model_directory_sha256": model_sha,
                "index_data_sha256": comparator.directory_digest(data_home),
            }
        self.config_path = self.assets / "config.json"
        self.config = {
            "schema": comparator.SCHEMA,
            "arm": comparator.ARM,
            "pilot_request_sha256": comparator.ORIGINAL_REQUEST_SHA,
            "lexical_predictions_sha256": comparator.LEXICAL_PREDICTIONS_SHA,
            "app_revision": comparator.pilot.APP_REV,
            "runner_sha256": comparator.hash_file(Path(comparator.__file__)),
            "pilot_helpers_sha256": comparator.hash_file(Path(comparator.pilot.__file__)),
            "binary_sha256": binary_sha,
            "model": {"id": comparator.MODEL_ID, "revision": comparator.MODEL_REVISION,
                      "directory_sha256": model_sha},
            "limit": comparator.LIMIT,
            "max_files": comparator.MAX_FILES,
            "budgets": list(comparator.BUDGETS),
            "alpha": comparator.ALPHA,
            "timeout_s": comparator.TIMEOUT_S,
            "tasks": bindings,
        }

    def admission(self):
        config_sha = write_json(self.config_path, self.config)
        return comparator.admit(PILOT, self.assets, self.config_path, config_sha)

    def test_common_seals_are_required(self):
        write_json(self.config_path, self.config)
        with self.assertRaisesRegex(ValueError, "sealed input drift"):
            comparator.admit(PILOT, self.assets, self.config_path, "0" * 64)
        for field, changed in (("limit", 21), ("app_revision", "wrong"),
                               ("pilot_helpers_sha256", "0" * 64)):
            old = self.config[field]
            self.config[field] = changed
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.admission()
            self.config[field] = old
        self.config["tasks"].pop(self.selected[0]["task_id"])
        with self.assertRaisesRegex(ValueError, "fixed cohort bindings"):
            self.admission()
        self.assets.joinpath("model/dummy-model").write_bytes(b"stale")
        with self.assertRaisesRegex(ValueError, "model directory drift"):
            self.admission()

    def test_per_task_binding_rejects_changed_base_app_binary_model_and_query(self):
        task = self.selected[0]
        binding = self.config["tasks"][task["task_id"]]
        for field in ("base_commit", "base_tree", "root", "query_sha256", "app_revision",
                      "binary_sha256", "model_revision", "model_directory_sha256"):
            old = binding[field]
            binding[field] = "wrong"
            with self.subTest(field=field), self.assertRaises(ValueError):
                comparator.admit_task(PILOT, self.assets, self.config, task)
            binding[field] = old

    def test_index_drift_and_wrong_resealed_root(self):
        task = self.selected[0]
        language = task["language"]
        project = self.projects[language]
        write_json(project / "project.json", {"project_path": "/different/root"})
        with self.assertRaisesRegex(ValueError, "stale index bytes"):
            comparator.admit_task(PILOT, self.assets, self.config, task)
        self.config["tasks"][task["task_id"]]["index_data_sha256"] = comparator.directory_digest(
            self.assets / "bases" / language)
        with self.assertRaisesRegex(ValueError, "different root"):
            comparator.admit_task(PILOT, self.assets, self.config, task)
        (project / "alias").symlink_to(project / "state.json")
        with self.assertRaisesRegex(ValueError, "regular file"):
            comparator.admit_task(PILOT, self.assets, self.config, task)

    def test_compare_uses_sealed_query_and_retains_empty_and_failed_denominator(self):
        config_sha = write_json(self.config_path, self.config)
        seen = []
        wanted_file = "xarray/__init__.py"
        full_file = "README.md"
        wanted_excluded = "xarray/backends/__init__.py"

        def mock_search(argv, root, data_home, timeout):
            task = next(task for task in self.selected if task["language"] == root.name)
            self.assertEqual(argv[-3:], ["--", task["query"], str(root)])
            self.assertEqual(argv[3], str(comparator.LIMIT))
            self.assertEqual(data_home, self.assets / "bases" / root.name)
            self.assertEqual(timeout, comparator.TIMEOUT_S)
            seen.append(task["task_id"])
            if root.name == "c":
                return "[]"
            if root.name == "cpp":
                raise subprocess.TimeoutExpired(argv, timeout)
            source = "xarray"
            candidates = [wanted_file, full_file] + [
                f"{source}/backends/{name}.py" for name in
                ("api", "cfgrib_", "common", "file_manager", "h5netcdf_", "locks")
            ] + [wanted_excluded]
            return json.dumps([hit(path, score=20 - rank) for rank, path in enumerate(candidates)])

        predictions, evidence, scored = comparator.compare(PILOT, self.assets, config_sha, search=mock_search)
        self.assertEqual(seen, [task["task_id"] for task in self.selected])
        self.assertEqual([row["status"] for row in predictions], ["ok", "no_context_extracted", "error"])
        self.assertEqual(len(predictions[0]["pred_files"]), comparator.MAX_FILES)
        self.assertNotIn(wanted_excluded, predictions[0]["pred_files"])
        self.assertEqual(len(evidence[0]["raw_search"]), comparator.MAX_FILES + 1)
        self.assertEqual([plan["budget_tokens"] for plan in evidence[0]["pack_plans"]], list(comparator.BUDGETS))
        for plan in evidence[0]["pack_plans"]:
            self.assertLessEqual(plan["estimated_packed_tokens"], plan["budget_tokens"])
            self.assertEqual(len(plan["rendered_sha256"]), 64)
            for row in plan["entries"]:
                if row["rendered_mode"] == "full":
                    lines = (PILOT / "bases/python" / row["path"]).read_text().splitlines()
                    self.assertEqual(row["pred_spans"], [[1, len(lines)]])
                elif row["rendered_mode"] == "excluded":
                    self.assertEqual(row["pred_spans"], [])
        self.assertTrue(any(
            row["rendered_mode"] == "slices" and row["pred_spans"]
            for plan in evidence[0]["pack_plans"] for row in plan["entries"]
        ))
        self.assertTrue(any(
            row["rendered_mode"] == "full" and row["pred_spans"]
            for plan in evidence[0]["pack_plans"] for row in plan["entries"]
        ))
        self.assertEqual(evidence[0]["config_sha256"], config_sha)
        self.assertEqual(scored["eligible_task_count"], 3)
        for scope in scored["arms"][1]["scopes"]:
            self.assertCountEqual([row["status"] for row in scope["per_task"]],
                                  ["ok", "no_context_extracted", "error"])
            for row in scope["per_task"]:
                if row["status"] != "ok":
                    self.assertEqual(set(row["metrics"].values()), {0.0})

    def test_malformed_and_escaping_searches_fail_as_attempts(self):
        config_sha = write_json(self.config_path, self.config)
        payloads = iter([
            json.dumps([hit("../outside.py")]),
            json.dumps([hit("README.md", end=200_000)]),
            b"not JSON",
        ])
        predictions, evidence, scored = comparator.compare(
            PILOT, self.assets, config_sha, search=lambda *_: next(payloads))
        self.assertTrue(all(row["status"] == "error" for row in predictions))
        self.assertIn("escapes checkout", evidence[0]["error"])
        self.assertIn("past the end", evidence[1]["error"])
        self.assertIn("JSONDecodeError", evidence[2]["error"])
        self.assertEqual(scored["eligible_task_count"], 3)

    def test_stale_task_index_does_not_call_search_or_replace_task(self):
        config_sha = write_json(self.config_path, self.config)
        (self.projects["python"] / "index/dummy-index").write_bytes(b"stale")
        seen = []

        def search(_argv, root, _data_home, _timeout):
            seen.append(root.name)
            return "[]"

        predictions, _, scored = comparator.compare(PILOT, self.assets, config_sha, search=search)
        self.assertEqual(seen, ["c", "cpp"])
        self.assertEqual([row["status"] for row in predictions], ["error", "no_context_extracted",
                                                                "no_context_extracted"])
        self.assertEqual(scored["eligible_task_count"], 3)


if __name__ == "__main__":
    unittest.main()
