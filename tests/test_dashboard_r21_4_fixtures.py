"""Integrity controls for the producer-recorded R21-4 dashboard fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest



FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures/autokernel_producers"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ProducerFixtureIntegrityTests(unittest.TestCase):
    def test_every_fixture_matches_its_source_manifest_digest(self):
        manifest = json.loads((FIXTURE_DIR / "SOURCE-MANIFEST.json").read_text())
        self.assertTrue(manifest["root_source_commit"])
        self.assertTrue(manifest["root_source_files"])
        files = manifest["files"]
        required = {
            "operator_gate_bundle.json",
            "loop-status.json",
            "experiments-sample.db",
            "champion-vs-production.published.json",
        }
        self.assertTrue(required.issubset(files))
        for relative, record in files.items():
            with self.subTest(fixture=relative):
                path = FIXTURE_DIR / relative
                self.assertTrue(path.is_file(), f"missing recorded fixture {relative}")
                self.assertEqual(path.stat().st_size, record["bytes"])
                self.assertEqual(_sha256(path), record["fixture_sha256"])
                self.assertTrue(record.get("source_path"))
                self.assertTrue(record.get("source_sha256") or record.get("source_git_blob"))

    def test_controller_state_census_keeps_each_recorded_schema_and_keyset(self):
        manifest = json.loads((FIXTURE_DIR / "SOURCE-MANIFEST.json").read_text())
        census = manifest["controller_state_census"]
        selection = manifest["controller_state_selection"]
        self.assertEqual(len(census), selection["scanned_count"])
        self.assertEqual(selection["scanned_count"], 32)
        self.assertEqual(selection["selected_count"], len(manifest["controller_state_files"]))

        observed = {(record["schema"], tuple(record["top_level_keys"]))
                    for record in census}
        selected = {(record["schema"], tuple(record["top_level_keys"]))
                    for record in census if record["selected"]}
        self.assertEqual(selected, observed)
        self.assertEqual(len(selected), selection["distinct_schema_keyset_count"])
        for record in census:
            with self.subTest(source=record["source_path"]):
                self.assertEqual(len(record["source_sha256"]), 64)
                peers = [item for item in census
                         if (item["schema"], item["top_level_keys"])
                         == (record["schema"], record["top_level_keys"])]
                chosen = min(peers, key=lambda item: (item["bytes"], item["source_path"]))
                self.assertEqual(record["selected_fixture_path"], chosen["fixture_path"])
                self.assertEqual(record["selected"], record is chosen)
        for relative in manifest["controller_state_files"]:
            record = manifest["files"][relative]
            path = FIXTURE_DIR / relative
            raw = path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), record["source_sha256"])
            state = json.loads(raw)
            self.assertEqual(state["schema"], record["schema"])
            self.assertEqual(sorted(state), next(
                item["top_level_keys"] for item in census
                if item["selected_fixture_path"] == relative and item["selected"]))


if __name__ == "__main__":
    unittest.main()
