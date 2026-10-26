"""Real CLI tests: native-shaped fake records, no models/network/live state."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/coordination/registration_sweep.py"
sys.path.insert(0, str(SCRIPT.parent))
import registration_sweep as sweep
import validate_fillers as vf


class RegistrationSweepTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.queue, self.candidate, self.catalog = [self.base / x for x in ("queue.md", "candidate.md", "catalog.json")]
        self.col = {x: i for i, x in enumerate(vf.COLUMNS)}
        self.a, self.b = self.row("old"), self.row("new")
        self.recipe = {"schema": sweep.RECIPE, "launch_contract": "orchestrator-production/v1",
                       "model": self.artifact("model", "a"), "drafter": None,
                       "executable": self.artifact("executable", "b"),
                       "dsos": [self.artifact("dso", "c")],
                       "argv": ["/fake/llama-server", "-m", "/fake/model", "--port", "9999"],
                       "launch_env": {"LD_LIBRARY_PATH": "/fake"}, "relevant_environment": {},
                       "absent_environment": [], "execution_digest": "e" * 64}
        self.plan = {"schema": "epyc.autokernel.experiment_plan.v1", "anchor_identity": {"commit": "anchor-1", "recipe": "f" * 64}}
        self.cat = {"schema": sweep.SCHEMA, "rows": {}}
        self.regenerate()

    def artifact(self, role, char):
        return {"schema": "epyc.autokernel.launch_artifact.v1", "role": role,
                "path": "/fake/" + role, "sha256": char * 64}

    def row(self, rid):
        return [rid, "fixture-owner", "/fake/launcher.sh pid=123", "q0", "600", "4", "/fake/STOP",
                "ARMED", "block-correctness", "900", "600", "n", "y", "none found (fixture, 2026-10-26)",
                "check exact identity", "n/a (fixture correctness)", "cpu", "fixture only"]

    def ref(self, name, value):
        path = self.base / name
        raw = (json.dumps(value, sort_keys=True) + "\n").encode()
        path.write_bytes(raw)
        return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}

    def regenerate(self):
        body = {k: v for k, v in self.recipe.items() if k not in {"schema", "snapshot_digest", "execution_digest"}}
        self.recipe["snapshot_digest"] = sweep.digest(body)
        recipe_ref = self.ref("recipe.json", self.recipe)
        plan_ref = self.ref("plan.json", self.plan)
        # Independently construct the documented load binding, then actual CLI verifies it.
        argv_sha = hashlib.sha256("\0".join(self.recipe["argv"]).encode()).hexdigest()
        shape = (self.recipe["model"]["sha256"], None, self.recipe["executable"]["sha256"],
                 (("dso", self.recipe["dsos"][0]["sha256"]),),
                 "sha256:nul-joined-utf8-argv/v1", argv_sha)
        load = sweep.digest([shape, self.recipe["launch_env"], self.recipe["relevant_environment"], self.recipe["absent_environment"]])
        for cells in (self.a, self.b):
            self.cat["rows"][cells[0]] = {"row_sha256": sweep.digest(cells), "recipe": recipe_ref,
                                          "session": {"id": "owner/session-1", "load_sha256": load, "anchors": [plan_ref]}}

    def table(self, rows):
        return "| " + " | ".join(vf.COLUMNS) + " |\n|" + "---|" * 18 + "\n" + "".join("| " + " | ".join(row) + " |\n" for row in rows)

    def invoke(self, strict=True, expected=0):
        self.queue.write_text(self.table([self.a]))
        self.candidate.write_text(self.table([self.b]))
        self.catalog.write_text(json.dumps(self.cat))
        before = {p: p.read_bytes() for p in (self.queue, self.candidate, self.catalog)}
        args = [sys.executable, str(SCRIPT), "--file", str(self.queue), "--candidate-row", str(self.candidate),
                "--candidate-id", "new", "--catalog", str(self.catalog)]
        if strict:
            args.append("--for-registration")
        proc = subprocess.run(args, capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
        for path, raw in before.items():
            self.assertEqual(path.read_bytes(), raw)
        return json.loads(proc.stdout if proc.stdout else proc.stderr)

    def separate(self):
        self.cat["rows"]["new"]["resolutions"] = {"old": {"action": "separate", "reason": "Fresh-process protocol requires independent load"}}

    def join(self):
        meta = self.cat["rows"]["new"]
        anchors = [[meta["session"]["anchors"][0]["path"], meta["session"]["anchors"][0]["sha256"], sweep.digest(self.plan["anchor_identity"])]]
        meta["resolutions"] = {"old": {"action": "join", "session": "owner/session-1", "shared_load_sha256": meta["session"]["load_sha256"], "anchor_refs": anchors}}

    def ds41(self):
        self.a[11] = self.b[11] = "y"
        self.regenerate()
        launch = {"schema": sweep.LAUNCH, "launch_id": "unique-native-launch", "launched_at": "2026-10-26T01:00:00Z",
                  "binary_realpath": "/fake/llama-server", "model_path": "/fake/model", "argv": self.recipe["argv"],
                  "argv_sha256": hashlib.sha256("\0".join(self.recipe["argv"]).encode()).hexdigest()}
        ref = self.ref("server.json", launch)
        for meta in self.cat["rows"].values():
            meta["server"] = ref
        return launch

    def test_exact_duplicate_requires_resolution(self):
        result = self.invoke(expected=2)
        self.assertEqual(result["matches"][0]["row"], "old")
        self.assertEqual(result["matches"][0]["kinds"], ["same-model-build-argv"])
        self.assertFalse(result["owner_adopted"])

    def test_review_warns_without_refusal(self):
        self.assertFalse(self.invoke(strict=False)["allowed"])

    def test_join_real_anchor_refs(self):
        self.join()
        self.assertEqual(self.invoke()["matches"][0]["resolution"]["action"], "join")

    def test_per_peer_reason(self):
        self.separate()
        self.assertTrue(self.invoke()["allowed"])

    def test_fabricated_anchor_join_refused(self):
        self.join()
        self.cat["rows"]["new"]["resolutions"]["old"]["anchor_refs"][0][2] = "0" * 64
        self.invoke(expected=2)

    def test_unrelated_model_or_build_or_argv_no_false_match(self):
        original = copy.deepcopy(self.cat)
        original_recipe = copy.deepcopy(self.recipe)
        for field in ("model", "executable", "argv"):
            with self.subTest(field=field):
                self.recipe = copy.deepcopy(original_recipe)
                if field == "argv":
                    self.recipe[field] = self.recipe[field] + ["--different"]
                else:
                    self.recipe[field]["sha256"] = "d" * 64
                self.regenerate()
                old = original["rows"]["old"]
                # Keep old provenance immutable; changed artifact gets a distinct file.
                old["recipe"] = self.ref("old-recipe.json", original_recipe)
                self.cat["rows"]["old"] = old
                self.assertEqual(self.invoke()["matches"], [])

    def test_environment_drift_groups_but_forbids_join(self):
        old = copy.deepcopy(self.cat["rows"]["old"])
        old["recipe"] = self.ref("old-recipe.json", self.recipe)
        self.recipe["launch_env"]["KNOB"] = "changed"
        self.regenerate()
        self.cat["rows"]["old"] = old
        self.join()
        self.assertEqual(self.invoke(expected=2)["matches"][0]["kinds"], ["same-model-build-argv"])

    def test_native_ds41_server_matches(self):
        self.ds41()
        self.separate()
        self.assertIn("same-DS41-server", self.invoke()["matches"][0]["kinds"])

    def test_ds41_boolean_alone_never_key(self):
        self.a[11] = self.b[11] = "y"
        self.regenerate()
        self.invoke(expected=3)

    def test_reused_port_different_launch_not_same_server(self):
        launch = self.ds41()
        launch["launch_id"] = "different-native-launch"
        self.cat["rows"]["new"]["server"] = self.ref("server-new.json", launch)
        self.separate()
        self.assertNotIn("same-DS41-server", self.invoke()["matches"][0]["kinds"])

    def test_changed_source_digest_or_row_binding_fails(self):
        for field in ("recipe", "row_sha256"):
            with self.subTest(field=field):
                self.regenerate()
                if field == "recipe":
                    self.cat["rows"]["new"][field]["sha256"] = "0" * 64
                else:
                    self.cat["rows"]["new"][field] = "0" * 64
                self.invoke(expected=3)

    def test_wrong_domain_or_mutated_argv_fails(self):
        for mutate in (lambda r: r.update(schema="other-domain"), lambda r: r["argv"].append("drift")):
            with self.subTest(mutate=mutate):
                source = copy.deepcopy(self.recipe)
                mutate(source)
                self.cat["rows"]["new"]["recipe"] = self.ref("bad.json", source)
                self.invoke(expected=3)

    def test_legacy_unknown_preserved_without_null_match(self):
        del self.cat["rows"]["old"]
        result = self.invoke()
        self.assertEqual(result["matches"], [])
        self.assertEqual([x["row"] for x in result["unknown_legacy"]], ["old"])
        self.assertFalse(result["exhaustive"])

    def test_terminal_peer_excluded(self):
        self.a[7] = "COMPLETE"
        self.assertEqual(self.invoke()["matches"], [])

    def test_self_replacement_is_not_duplicate(self):
        self.a = self.b[:]
        self.assertEqual(self.invoke()["matches"], [])

    def test_non_model_rows_no_null_group(self):
        for cells in (self.a, self.b):
            self.cat["rows"][cells[0]] = {"row_sha256": sweep.digest(cells), "non_model": "pure source fixture test"}
        self.assertEqual(self.invoke()["matches"], [])

    def test_multiple_peers_not_silently_covered(self):
        self.separate()
        extra = self.row("third")
        meta = copy.deepcopy(self.cat["rows"]["old"])
        meta["row_sha256"] = sweep.digest(extra)
        self.cat["rows"]["third"] = meta
        result = sweep.sweep({"old": self.a, "third": extra}, self.b, self.col, self.cat)
        self.assertFalse(result["allowed"])
        self.assertEqual(len(result["matches"]), 2)

    def test_duplicate_json_keys_refused(self):
        self.assertRaises(sweep.Invalid, json.loads, '{"rows":{},"rows":{}}', object_pairs_hook=sweep.unique_object)

    def test_fake_writer_generation_race_no_publication(self):
        self.join()
        result = self.invoke()
        # Fake owner's existing lease checks the actual CLI receipt before mutation.
        writes = []
        def publish(expected):
            current = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                       for name, path in (("queue", self.queue), ("candidate", self.candidate), ("catalog", self.catalog))}
            if expected != current:
                return False
            writes.append("row+catalog+receipt")
            return True
        for path in (self.queue, self.candidate, self.catalog):
            original = path.read_bytes()
            path.write_bytes(original + b"\n")
            self.assertFalse(publish(result["input_sha256"]))
            self.assertEqual(writes, [])
            path.write_bytes(original)
        self.assertTrue(publish(result["input_sha256"]))
        self.assertEqual(writes, ["row+catalog+receipt"])
        self.cat["rows"]["new"].pop("resolutions")
        refused = self.invoke(expected=2)
        self.assertFalse(refused["allowed"])

    def test_stale_server_cannot_join(self):
        launch = self.ds41()
        launch["launched_at"] = "2026-10-26T02:00:00Z"
        self.cat["rows"]["new"]["server"] = self.ref("server-restarted.json", launch)
        self.join()
        self.invoke(expected=2)

    def test_invalid_resolution_type_fails_closed(self):
        self.cat["rows"]["new"]["resolutions"] = {"old": "join"}
        self.invoke(expected=3)

    def test_legacy_validator_cli_and_print_class(self):
        self.queue.write_text(self.table([self.a]))
        p = subprocess.run([sys.executable, str(SCRIPT.with_name("validate_fillers.py")), "--file", str(self.queue),
                            "--print-class", "old"], capture_output=True, text=True, timeout=15)
        self.assertEqual((p.returncode, p.stdout.strip()), (0, "block-correctness"))
        self.assertEqual(len(vf.COLUMNS), 18)

    def test_actual_import_paths_and_bytes(self):
        self.assertEqual(Path(sweep.__file__).resolve(), SCRIPT.resolve())
        self.assertEqual(Path(vf.__file__).resolve(), SCRIPT.with_name("validate_fillers.py").resolve())
        self.assertEqual(hashlib.sha256(Path(sweep.__file__).read_bytes()).hexdigest(),
                         hashlib.sha256(SCRIPT.read_bytes()).hexdigest())

    def test_bounded_regular_reader_and_parent_alias(self):
        native = self.base / "regular.json"
        native.write_bytes(b'{"value":1}\n')
        alias = self.base / "parent-alias"
        alias.symlink_to(self.base, target_is_directory=True)
        loaded, actual = sweep.load_json(alias / native.name)
        self.assertEqual(loaded, {"value": 1})
        self.assertEqual(actual, hashlib.sha256(native.read_bytes()).hexdigest())

    def test_native_source_final_symlink_fifo_directory_oversize_refused_cli(self):
        regular = self.base / "native.json"
        regular.write_text(json.dumps(self.recipe))
        symlink = self.base / "final-symlink.json"
        symlink.symlink_to(regular)
        fifo = self.base / "fifo.json"
        os.mkfifo(fifo)
        oversized = self.base / "oversized.json"
        with oversized.open("wb") as stream:
            stream.truncate(sweep.MAX_BYTES + 1)
        for path in (symlink, fifo, self.base, oversized):
            with self.subTest(path=path):
                self.cat["rows"]["new"]["recipe"] = {"path": str(path), "sha256": "0" * 64}
                self.invoke(expected=3)

    def test_table_reader_uses_same_bounded_regular_contract(self):
        self.queue.write_text(self.table([self.a]))
        symlink = self.base / "table-symlink.md"
        symlink.symlink_to(self.queue)
        with self.assertRaises(OSError):
            sweep.rows(symlink)
        fifo = self.base / "table-fifo.md"
        os.mkfifo(fifo)
        with self.assertRaises(sweep.Invalid):
            sweep.rows(fifo)
        with self.queue.open("wb") as stream:
            stream.truncate(sweep.MAX_BYTES + 1)
        with self.assertRaises(sweep.Invalid):
            sweep.rows(self.queue)

    def test_nonfinite_json_constants_refused_cli(self):
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                raw = ('{"value":' + constant + '}').encode()
                path = self.base / "nonfinite.json"
                path.write_bytes(raw)
                self.cat["rows"]["new"]["recipe"] = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
                result = self.invoke(expected=3)
                self.assertIn("nonfinite JSON constant", result["error"])

    def test_regular_reader_closes_descriptor_after_refusal(self):
        from unittest.mock import patch
        fifo = self.base / "close-check.json"
        os.mkfifo(fifo)
        real_open, real_close = os.open, os.close
        captured = []
        def opened(*args):
            fd = real_open(*args)
            captured.append(fd)
            return fd
        with patch.object(sweep.os, "open", side_effect=opened), patch.object(sweep.os, "close", wraps=real_close) as close:
            with self.assertRaises(sweep.Invalid):
                sweep.read_regular(fifo)
            close.assert_called_once_with(captured[0])
        with self.assertRaises(OSError):
            os.fstat(captured[0])


if __name__ == "__main__":
    unittest.main()
