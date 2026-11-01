"""Native CS22 receipt replay and corruption controls; no model execution."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
from adapters.cs22v0_parity import native_rows, project
from claim_tuple import ProjectionError, grade

class CS22V0Tests(unittest.TestCase):
    def native(self):
        path = os.environ.get("CS22V0_TEST_RECEIPT")
        if not path or not os.environ.get("CS22V0_RELOCATIONS"):
            self.skipTest("native receipt and explicit custody map unavailable")
        return Path(path)

    def test_actual_negative(self):
        rows = native_rows(self.native())
        self.assertEqual([r["arm"] for r in rows], ["whisper", "gguf", "jit"])
        self.assertEqual([r["value"] for r in rows], [False, False, False])
        for row in rows:
            tup = project(row)
            self.assertEqual((tup.protocol_id, tup.source_class), ("", "verifier"))
            self.assertEqual(grade(tup)[:2], ("Judged", "Located"))
            self.assertGreater(tup.extra["posterior_max_abs_diff_descriptive"], 0)

    def test_changed_or_incomplete_receipt_refuses(self):
        native = self.native()
        for corruption in ("raw_missing", "raw_tamper", "predeclaration", "proposition", "null_result"):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as td:
                doc = json.loads(native.read_text())
                path = Path(td) / "VERIFIER-RECEIPT.json"
                (Path(td) / "precheck").symlink_to(native.parent / "precheck", target_is_directory=True)
                if corruption == "raw_missing":
                    doc["raw_sha256"].pop(next(iter(doc["raw_sha256"])))
                elif corruption == "raw_tamper":
                    doc["raw_sha256"][next(iter(doc["raw_sha256"]))] = "0" * 64
                elif corruption == "predeclaration":
                    doc["predeclaration_sha256"] = "0" * 64
                elif corruption == "proposition":
                    doc["propositions"][0]["result"] = True
                else:
                    doc["propositions"][0]["result"] = None
                path.write_text(json.dumps(doc))
                with self.assertRaises(ProjectionError):
                    native_rows(path)

    def test_synthetic_positive(self):
        # In-memory-derived fake evidence for the reader only: never a native run or ledger input.
        native = self.native()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            doc = json.loads(native.read_text())
            srcresult = Path(doc["native_result_path"])
            result = json.loads(srcresult.read_text())
            raw = root / "run" / "raw"
            raw.mkdir(parents=True)
            for source in (srcresult.parent / "raw").iterdir():
                name = source.name
                if any(name.endswith("." + a + ".stdout") for a in ("whisper", "gguf", "jit")):
                    clip = name.rsplit(".", 2)[0]
                    source = srcresult.parent / "raw" / (clip + ".reference.stdout")
                (raw / name).symlink_to(source)
                import hashlib
                doc["raw_sha256"][name] = hashlib.sha256(source.read_bytes()).hexdigest()
            for row in result["comparisons"]:
                row["max_abs_diff"] = 0.0
                for point in row["operating_points"].values():
                    point.update(cs47_stop_equal=True, serving_segments_equal=True)
            for arm in ("whisper", "gguf", "jit"):
                result["exclusions"][arm] = dict(eligible=True, status="complete", stop_mismatches=0, segment_mismatches=0)
            for proposition in doc["propositions"]:
                proposition["result"] = True
            resultpath = root / "run" / "result.json"
            resultpath.write_text(json.dumps(result))
            doc["native_result_path"] = str(resultpath)
            doc["native_result_sha256"] = hashlib.sha256(resultpath.read_bytes()).hexdigest()
            path = root / "VERIFIER-RECEIPT.json"
            path.write_text(json.dumps(doc))
            (root / "precheck").symlink_to(native.parent / "precheck", target_is_directory=True)
            rows = native_rows(path)
            self.assertEqual([r["value"] for r in rows], [True, True, True])

    def test_oversized_integer_posterior_refuses(self):
        import hashlib
        native = self.native()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            doc = json.loads(native.read_text())
            original_result = Path(doc["native_result_path"])
            result = json.loads(original_result.read_text())
            clip = result["comparisons"][0]["clip"]
            changed = clip + ".reference.stdout"
            raw = root / "run" / "raw"
            raw.mkdir(parents=True)
            for source in (original_result.parent / "raw").iterdir():
                if source.name == changed:
                    obj = json.loads(source.read_text())
                    obj["probs"][0] = 10 ** 400
                    (raw / changed).write_text(json.dumps(obj))
                    doc["raw_sha256"][changed] = hashlib.sha256((raw / changed).read_bytes()).hexdigest()
                else:
                    (raw / source.name).symlink_to(source)
            resultpath = root / "run" / "result.json"
            resultpath.write_bytes(original_result.read_bytes())
            doc["native_result_path"] = str(resultpath)
            path = root / "VERIFIER-RECEIPT.json"
            path.write_text(json.dumps(doc))
            (root / "precheck").symlink_to(native.parent / "precheck", target_is_directory=True)
            with self.assertRaises(ProjectionError):
                native_rows(path)

    def test_bad_relocation_refuses(self):
        native = self.native()
        reloc = json.loads(Path(os.environ["CS22V0_RELOCATIONS"]).read_text())
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bad = root / "changed"
            bad.write_bytes(b"not the pinned source")
            reloc[next(iter(reloc))] = str(bad)
            path = root / "relocations.json"
            path.write_text(json.dumps(reloc))
            with patch.dict(os.environ, {"CS22V0_RELOCATIONS": str(path)}):
                with self.assertRaises(ProjectionError):
                    native_rows(native)

    def test_cli_and_dispatcher_choices_match(self):
        import cli
        import ingest_sources
        self.assertEqual(set(cli._FILE_SOURCES), set(ingest_sources.SOURCES))
        self.assertIn("cs22v0-parity", ingest_sources.SOURCES)

    def test_unrelated_record_declines(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "foreign.json"
            path.write_text("{}")
            self.assertEqual(native_rows(path), ())

if __name__ == "__main__":
    unittest.main()
