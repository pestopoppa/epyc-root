"""Offline controls for DCP-10 native GitNexus capture preparation."""
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

import gitnexus_native as native


def seal(path, value):
    payload = native.pilot.encode(value).encode()
    path.write_bytes(payload)
    return sha256(payload).hexdigest()


def direct_edge():
    return {"source_id": "node:a", "source_path": "a.py", "target_id": "node:b", "target_path": "b.py",
            "relation": "CALLS", "confidence": 0.9, "depth": 1}


class OfflineCapture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="gitnexus-native-offline-", dir=native.WORK.parent)
        self.addCleanup(temp.cleanup)
        self.assets = Path(temp.name)
        self.root = self.assets / "base"
        self.root.mkdir()
        for filename in ("a.py", "b.py", "untracked.py"):
            (self.root / filename).touch()
        self.task_id = "synthetic-python"
        self.tasks = {self.task_id: {"task_id": self.task_id, "language": "python"}}
        self.base = {"root": str(self.root), "base_commit": "test", "base_tree": "tree", "query_sha256": "issue"}
        self.index = self.assets / "indexes/python"
        self.index.mkdir(parents=True)
        upstream = self.assets / "colgrep"
        upstream.mkdir()
        self.result = upstream / "RESULT.json"
        self.attempt = upstream / "python-attempt.json"
        self.write_upstream()
        self.writer = {"fixture": True}
        self.index_digest = self.write_index()
        (self.assets / native.WORKER.name).write_bytes(native.WORKER.read_bytes())
        self.producer = native.producer_identity()
        self.node, self.ladybug = self.assets / "fake-node", self.assets / "ladybug"
        self.node.write_bytes(b"fake node")
        self.ladybug.mkdir()
        (self.ladybug / "index.js").write_bytes(b"fake ladybug")

    def write_upstream(self, *, status="ok", lineage=None):
        seeds = ["a.py"] if status == "ok" else []
        attempt = {"task_id": self.task_id, "unit": self.task_id,
                   "evidence": {"task_id": self.task_id, "binding": self.base},
                   "prediction": {"task_id": self.task_id, "arm": native.common.ARM, "status": status,
                                  "pred_files": seeds, "pred_spans": [], "pack_candidates": []}}
        result = {"row": native.COLGREP_R2, "completed": 1, "reconciled": True, "comparison_valid": status != "error",
                  "observed": [{"task_id": self.task_id, "status": status}], "unknown": [], "stop_reason": None,
                  "outputs_sha256": {self.attempt.name: seal(self.attempt, attempt)},
                  "lineage": native.COLGREP_LINEAGE if lineage is None else lineage}
        self.result_sha = seal(self.result, result)

    def write_index(self, **metadata_changes):
        meta = {"repoPath": str(self.root), "lastCommit": self.base["base_commit"],
                "stats": {"files": 2, "nodes": 2, "edges": 1, "embeddings": 0}, **metadata_changes}
        (self.index / "lbug").write_bytes(b"synthetic database marker")
        self.receipt = self.assets / "index-builds/python.json"
        self.receipt.parent.mkdir(exist_ok=True)
        build_manifest = seal(self.receipt.with_suffix(".manifest.json"), {"fixture": True})
        return seal(self.receipt, {"schema": native.INDEX_BUILD_SCHEMA, "task_id": self.task_id, "base": self.base,
                                   "gitnexus_source": self.writer, "build_manifest_sha256": build_manifest,
                                   "files": {"meta.json": seal(self.index / "meta.json", meta),
                                             "lbug": native.common.hash_file(self.index / "lbug")}})

    def capture(self, search, *, seeds=None, request_changes=None):
        seeds = ["a.py"] if seeds is None else seeds
        with ExitStack() as stack:
            self.base_check = stack.enter_context(patch.object(native.graph, "bind_task", return_value=self.root))
            self.launch = stack.enter_context(patch.object(native, "launch", side_effect=search))
            for key, value in {"original_tasks": lambda: self.tasks, "check_custody": lambda _: None,
                               "writer_identity": lambda: self.writer, "tracked_files": lambda _: {"a.py", "b.py"},
                               "NODE": self.node, "NODE_SHA": native.common.hash_file(self.node), "LADYBUG": self.ladybug,
                               "LADYBUG_FILES": {"index.js": native.common.hash_file(self.ladybug / "index.js")}}.items():
                stack.enter_context(patch.object(native, key, value))
            request = {"schema": native.SCHEMA, "pilot_request_sha256": native.common.ORIGINAL_REQUEST_SHA,
                       "lexical_predictions_sha256": native.common.LEXICAL_PREDICTIONS_SHA,
                       "producer_sha256": self.producer, "gitnexus_source": self.writer, "runtime": native.runtime_identity(),
                       "query_sha256": native.QUERY_SHA, "output_schema": native.OUTPUT_SCHEMA,
                       "colgrep_row": native.COLGREP_R2, "colgrep_result_sha256": self.result_sha,
                       "tasks": {self.task_id: {"base": self.base, "seed_paths": seeds,
                                               "index_receipt_sha256": self.index_digest}}, **(request_changes or {})}
            digest = seal(self.assets / "request.json", request)
            return native.capture(self.assets, digest, self.task_id, lambda cap: cap)

    def test_sealed_capture_preserves_raw_rows_and_rechecks_snapshot(self):
        raw = native.pilot.encode([direct_edge()]).encode()
        result, archived = self.capture(lambda *_: raw)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["edges"], [direct_edge()])
        self.assertEqual(result["raw_stdout_sha256"], sha256(raw).hexdigest())
        self.assertEqual(archived, raw)
        self.assertEqual(self.base_check.call_count, 2)
        self.launch.assert_called_once()
        self.assertEqual(self.launch.call_args.args[1:], (["a.py"], native.TIMEOUT))

    def test_no_seed_empty_timeout_and_malformed_are_distinct(self):
        for raw, status in [(b"[]\n", "empty"), (b"| markdown |", "error"), (b" " * (native.MAX_OUTPUT + 1), "error")]:
            with self.subTest(status=status):
                self.assertEqual(self.capture(lambda *_, raw=raw: raw)[0]["status"], status)
        failed, archived = self.capture(native.QueryError("synthetic timeout"))
        self.assertEqual((failed["status"], failed["error"], archived), ("error", "synthetic timeout", None))
        self.write_upstream(status="no_context_extracted")
        self.assertEqual(self.capture(None, seeds=[])[0]["status"], "no_seeds")
        self.launch.assert_not_called()

    def test_index_drift_is_refused_even_when_query_failed(self):
        def drift(*_):
            (self.index / "lbug").write_bytes(b"changed")
            raise native.QueryError("raw query error")

        with self.assertRaisesRegex(ValueError, "sealed input drift"):
            self.capture(drift)
        self.assertEqual(self.base_check.call_count, 2)

    def test_index_metadata_sidecars_and_producer_drift_are_refused(self):
        (self.index / "lbug.wal").touch()
        with self.assertRaisesRegex(ValueError, "no sidecars"):
            self.capture(None)
        self.launch.assert_not_called()
        (self.index / "lbug.wal").unlink()
        self.index_digest = self.write_index(lastCommit="different")
        with self.assertRaisesRegex(ValueError, "metadata does not describe"):
            self.capture(None)
        with self.assertRaisesRegex(ValueError, "request drifted"):
            self.capture(None, request_changes={"producer_sha256": {}})

    def test_upstream_lineage_failed_run_and_seed_substitution_refused(self):
        with self.assertRaisesRegex(ValueError, "seed order differs"):
            self.capture(None, seeds=["b.py"])
        self.write_upstream(lineage={**native.COLGREP_LINEAGE, "prior_result_sha256": "bad"})
        with self.assertRaisesRegex(ValueError, "lineage differs"):
            self.capture(None)
        self.write_upstream(status="error")
        with self.assertRaisesRegex(ValueError, "complete official ColGREP"):
            self.capture(None)
        self.launch.assert_not_called()

    def test_direct_edge_path_depth_and_numeric_confidence_are_strict(self):
        for fields in ({"target_path": "untracked.py"}, {"target_path": "../b.py"}, {"depth": 2},
                       {"confidence": 0.8}, {"confidence": True}, {"confidence": "0.99"}, {"source_path": "b.py"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.capture(lambda *_, fields=fields: json.dumps([{**direct_edge(), **fields}]).encode())
        with patch.object(native, "MAX_EDGES", 1):
            raw = native.pilot.encode([direct_edge(), direct_edge()]).encode()
            self.assertEqual(self.capture(lambda *_: raw)[0]["status"], "error")

    def test_launch_is_immutable_bounded_and_does_not_mount_pilot(self):
        command = native.launch_config("/usr/bin/docker", "offline", [(self.index, "/dcp10/index")], 0.5)
        for option in ("--pull=never", "--network=none", "--read-only", "--cap-drop=ALL", "--cpus=1", "--memory=2g",
                       "HOME=/dcp10/empty-home", "NODE_PATH=", native.IMAGE, "/dcp10/worker.mjs", "0.500s"):
            self.assertIn(option, command)
        mounted, = [command[index + 1] for index, item in enumerate(command) if item == "--mount"]
        self.assertTrue(mounted.endswith(",readonly,bind-recursive=readonly"))
        self.assertNotIn(str(native.WORK), " ".join(command))
        with self.assertRaisesRegex(native.IsolationError, "untrusted isolated capture path"):
            native.check_custody(self.result)

    def test_stream_io_failure_removes_only_its_named_container(self):
        with (patch.object(native.shutil, "which", return_value="/usr/bin/docker"),
              patch.object(native.os, "geteuid", return_value=1000),
              patch.object(native, "read_bounded", side_effect=OSError("synthetic pipe failure")) as read,
              patch.object(native, "remove_container") as remove,
              self.assertRaisesRegex(native.IsolationError, "start or read")):
            native.launch([], ["a.py"], 1)
        command, env = read.call_args.args[:2]
        remove.assert_called_once_with("/usr/bin/docker", command[command.index("--name") + 1], env)

    def test_subprocess_streams_are_bounded_before_accumulation(self):
        echo = [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"]
        self.assertEqual(native.read_bounded(echo, {}, b"input", 5).stdout, b"input")
        with patch.object(native, "MAX_OUTPUT", 4), self.assertRaisesRegex(native.QueryError, "stream byte bound"):
            native.read_bounded(echo, {}, b"oversized", 5)


class OriginalPins(unittest.TestCase):
    def test_installed_runtime_and_failed_original_outcome(self):
        self.assertEqual(native.writer_identity()["version"], "1.6.1")
        native.seal_file(native.NODE, native.NODE_SHA)
        for name, digest in native.LADYBUG_FILES.items():
            native.seal_file(native.LADYBUG / name, digest)
        tasks = native.original_tasks()
        self.assertEqual([task["language"] for task in tasks.values()], ["python", "c", "cpp"])
        prior = Path(native.COLGREP_LINEAGE["prior_result_path"])
        with self.assertRaisesRegex(ValueError, "complete official ColGREP"):
            native.admit_upstream(prior.parent, native.COLGREP_ROW, native.COLGREP_LINEAGE["prior_result_sha256"], tasks)

    def test_worker_has_valid_node_syntax_without_loading_the_addon(self):
        subprocess.run([native.NODE, "--check", native.WORKER], check=True, timeout=10)


if __name__ == "__main__":
    unittest.main()
