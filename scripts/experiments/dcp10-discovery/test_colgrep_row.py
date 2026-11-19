"""Test the native allocator row with the exact sealed cohort and synthetic backend."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import colgrep_row as row
import prepare_colgrep_native as stage
from test_colgrep_compare import PILOT, hit, write_json


@unittest.skipUnless((PILOT / "packet/request.json").is_file(), "retained DCP-10 pilot unavailable")
class ColgrepRowControls(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        parent = Path(directory.name)
        self.root = parent / "row"
        binary = parent / "colgrep"
        binary.write_bytes(b"fixture binary")
        runtime = parent / row.native.RUNTIME_NAME
        runtime.write_bytes(b"fixture runtime")
        model = parent / "snapshot"
        model.mkdir()
        (model / "fixture.onnx").symlink_to(binary)
        patches = (
            patch.object(stage, "ORIGINAL_BINARY", binary),
            patch.object(stage, "MODEL_SNAPSHOT", model),
            patch.object(stage, "RUNTIME_SHA", row.comparator.hash_file(runtime)),
            patch.object(row.comparator, "BINARY_SHA", row.comparator.hash_file(binary)),
        )
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        self.digest_dir = row.comparator.directory_digest
        observed_hashes = []

        def prep_digest(path):
            observed_hashes.append(path)
            return self.digest_dir(path)

        with patch.object(row.comparator, "directory_digest", side_effect=prep_digest):
            self.seal = stage.prepare(self.root, PILOT, runtime)
        self.assertEqual(observed_hashes, [self.root / "assets/model"])

    def index_only_digest(self, path):
        if path == self.root / "assets/model":
            raise AssertionError("native execution attempted to rehash model weights")
        return self.digest_dir(path)

    @staticmethod
    def build(_assets, base, data_home, _timeout):
        project = data_home / "colgrep/indices/mock"
        (project / "index").mkdir(parents=True)
        write_json(project / "project.json", {"project_path": str(base)})
        write_json(project / "state.json", {"fixture": True})
        write_json(project / "index/metadata.json", {"fixture": True})
        (project / "index/fixture-index").write_bytes(b"fixture index")

    def run_official(self, search, **kwargs):
        with patch.object(row.comparator, "directory_digest", side_effect=self.index_only_digest):
            receipt, admitted = row.load_preparation(self.root, self.seal)
            return row.run_official(self.root, receipt, admitted, lambda cap=1800: cap, search=search,
                                    build=kwargs.get("build", self.build))

    def result(self):
        return json.loads((self.root / "native/RESULT.json").read_bytes())

    def test_success_empty_failure_kept_and_actual_plans_reconciled(self):
        def search(argv, root, _data_home, _timeout):
            self.assertEqual(argv[3], str(row.comparator.LIMIT))
            if root.name == "python":
                return json.dumps([hit("xarray/__init__.py"), hit("README.md")])
            if root.name == "c":
                return "[]"
            raise row.native.NativeError("synthetic retrieval failure")

        self.assertEqual(self.run_official(search), 0)
        result = self.result()
        self.assertTrue(row.completed(self.root))
        self.assertEqual(result["completed"], 3)
        self.assertTrue(result["reconciled"])
        self.assertFalse(result["comparison_valid"])
        self.assertEqual(result["unknown"], [])
        self.assertEqual([item["status"] for item in result["observed"]],
                         ["ok", "no_context_extracted", "error"])
        self.assertIsNotNone(result["outputs_sha256"].get("actual-colgrep-scopes.json"))

    def test_post_search_index_drift_stops_without_substitution(self):
        seen = []

        def search(_argv, root, data_home, _timeout):
            seen.append(root.name)
            (data_home / "colgrep/indices/mock/index/fixture-index").write_bytes(b"changed")
            return "[]"

        self.assertEqual(self.run_official(search), 1)
        self.assertFalse(row.completed(self.root))
        self.assertEqual(seen, ["python"])
        result = self.result()
        self.assertEqual(result["completed"], 0)
        self.assertEqual(len(result["unknown"]), 3)
        self.assertIn("sealed index changed", result["stop_reason"])

    def test_drift_in_prepared_model_fails_before_any_native_build(self):
        path = self.root / "assets/model/fixture.onnx"
        path.chmod(0o600)
        path.write_bytes(b"modified")
        path.chmod(0o400)
        with (
            patch.object(row.comparator, "directory_digest", side_effect=self.index_only_digest),
            self.assertRaisesRegex(ValueError, "staged model identity"),
        ):
            row.load_preparation(self.root, self.seal)

    def test_source_refresh_reseals_runner_and_preserves_asset_proofs(self):
        packet = self.root / "packet"
        receipt_path = packet / "preparation.json"
        prior_receipt = receipt_path.read_bytes()
        prior_launcher = (packet / "launcher.sh").read_bytes()
        prior_sources = {name: (packet / name).read_bytes() for name in row.PACKET_SOURCES}
        source = self.root.parent / "updated-source"
        source.mkdir()
        tree = Path(stage.__file__).parent
        for name in (*row.PACKET_SOURCES, "colgrep_row_launcher.sh"):
            (source / name).write_bytes((tree / name).read_bytes())
        adapter = source / "colgrep_native.py"
        adapter.write_bytes(adapter.read_bytes() + b"\n# Updated coordination lock.\n")
        native = self.root / "native"
        native.mkdir()
        marker = native / "checkpoint.json"
        marker.write_bytes(b"prior official output")
        assets = self.root / "assets"
        asset_paths = [p for p in assets.rglob("*") if p.is_file()]
        previous_asset_stats = {p: p.stat() for p in asset_paths}
        with (
            patch.object(stage, "__file__", str(source / "prepare_colgrep_native.py")),
            patch.object(stage, "copy_asset", side_effect=AssertionError("source refresh copied an asset")),
            patch.object(stage, "model_stat", side_effect=AssertionError("source refresh inspected the model")),
            patch.object(row.comparator, "directory_digest",
                         side_effect=AssertionError("source refresh hashed a payload directory")),
        ):
            new_seal = stage.refresh_sources(self.root)
            self.assertEqual(stage.refresh_sources(self.root), new_seal)
        self.assertNotEqual(new_seal, self.seal)
        old = json.loads(prior_receipt)
        new = json.loads(receipt_path.read_bytes())
        self.assertNotEqual(old.pop("source_hashes"), new.pop("source_hashes"))
        self.assertEqual(old, new)
        self.assertEqual({p: p.stat() for p in asset_paths}, previous_asset_stats)
        self.assertEqual(marker.read_bytes(), b"prior official output")
        recorded = packet / "source-history" / stage.digest(prior_launcher)
        self.assertEqual((recorded / "preparation.json").read_bytes(), prior_receipt)
        self.assertEqual({name: (recorded / name).read_bytes() for name in row.PACKET_SOURCES}, prior_sources)
        self.assertIn(new_seal.encode(), (packet / "launcher.sh").read_bytes())
        self.assertIn(stage.digest((packet / "SOURCE.sha256").read_bytes()).encode(),
                      (packet / "launcher.sh").read_bytes())
        self.assertIn(new_seal, json.loads((self.root / "spec.json").read_bytes())["smoke_predicate"])
        row.load_preparation(self.root, new_seal)

    def test_smoke_fresh_marker_has_nonce_and_no_official_output(self):
        dryrun = self.root / "dryrun"

        def search(argv, _root, _data_home, _timeout):
            self.assertEqual(argv[-2], row.FIXTURE_QUERY)
            return json.dumps([hit(row.FIXTURE_FILE)])

        environ = {"FILLER_SMOKE": "1", "FILLER_DRYRUN": "1", "FILLER_DRYRUN_DIR": str(dryrun),
                   "FILLER_SMOKE_T0": "1795000000"}
        with patch.dict(os.environ, environ):
            self.assertFalse(row.smoke_completed())
            row.run_smoke(self.root, lambda cap=1800: cap, build=self.build, search=search)
            self.assertTrue(row.smoke_completed())
        self.assertFalse((self.root / "native").exists())
        with patch.dict(os.environ, {**environ, "FILLER_SMOKE_T0": "1795000001"}):
            self.assertFalse(row.smoke_completed())


if __name__ == "__main__":
    unittest.main()
