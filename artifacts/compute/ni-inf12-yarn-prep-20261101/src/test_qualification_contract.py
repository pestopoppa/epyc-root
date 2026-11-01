#!/usr/bin/env python3
"""Model-free behavioral checks for the private YARN r2 packet."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class QualificationContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_text = (HERE / "run.py").read_text()
        cls.needle_text = (HERE / "yarn_needle.py").read_text()
        cls.launch_text = (HERE / "launch.sh").read_text()
        cls.metadata = json.loads((HERE / "qualification/REQUEST-METADATA.json").read_text())
        cls.request = json.loads((HERE / "qualification/request_manifest.json").read_text())
        cls.recipe = json.loads((HERE / "qualification/production_recipe.json").read_text())
        cls.request_sha = digest(HERE / "qualification/request_manifest.json")
        cls.recipe_sha = digest(HERE / "qualification/production_recipe.json")

    def test_exact_500k_request_metadata(self):
        p = self.metadata["prompt"]
        self.assertEqual((p["arm"], p["stage"], p["needle"]), ("A1", "500k", "N19"))
        self.assertEqual(p["token_count"], 498965)
        self.assertEqual(p["token_count"], max(x["token_count"] for x in self.metadata["planned_500k_prompts"]))
        self.assertTrue(self.metadata["identity_audit"]["request_bytes_match_historical"])
        self.assertFalse(self.metadata["qualification_claim"])

    def test_science_cells_preserved(self):
        expected = "[('E1', 'A0', 'low'), ('W', 'A0', 'low'), ('E1', 'A1', 'low'),"
        self.assertIn(expected, self.run_text)
        self.assertIn("('W', 'A1', 'low'), ('E1', 'A1', 'high'), ('W', 'A1', 'high')]", self.run_text)
        self.assertEqual(self.run_text.count("('E1', 'A0', 'low')"), 1)

    def test_completion_rejects_empty_and_cross_recipe_native_events(self):
        checker = HERE / "helper/check_complete.py"
        request_max = self.request["request_max"]
        nonce = "c" * 64
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            identities = []
            for index, image in enumerate(("E1", "W")):
                cell = root / f"{image}-A1-high"
                cell.mkdir()
                for name in ("kfd.jsonl", "hipmalloc.jsonl", "phase-attribution.json"):
                    (cell / name).write_text("{}\n")
                report_dir = root / f"native-{image}"
                report_dir.mkdir()
                report_path = report_dir / "report.json"
                report_path.write_text(json.dumps({
                    "arm": "A1", "inputs_manifest_sha256": self.request["input_manifest"]["sha256"],
                    "needle": {"500k": {"n": 5}}, "out": str(report_dir)}))
                rows = [{"id": f"N{n:02d}", "stage": "500k", "arm": "A1",
                         "prompt_sha256": request_max["messages_sha256"], "http_ok": True}
                        for n in range(15, 20)]
                (report_dir / "needle_500k.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
                pid, birth = 32100 + index, 700000 + index
                event = {
                    "id": self.request["id"], "nonce": nonce, "image": image, "phase": "normal",
                    "native_first_event": True, "native_pid": pid, "native_birth_ticks": birth,
                    "first_request": {
                        "ok": True, "scope": "TARGET_SCRATCH_SERVER",
                        "manifest_sha256": self.request_sha,
                        "production_recipe_sha256": self.recipe_sha,
                        "n_ctx_total": 524288, "n_ctx_per_slot": 524288, "total_slots": 1,
                        "prompt_tokens": request_max["prompt_tokens_required"], "kv_cache_mode": "split",
                        "native_pid": pid, "native_birth_ticks": birth,
                        "request": {"arm": "A1", "cache_seed_stage": "400k", "stage": "500k",
                                    "needle": request_max["needle"],
                                    "messages_sha256": request_max["messages_sha256"],
                                    "rendered_sha256": request_max["rendered_sha256"]}}}
                event_path = cell / "native-first-event.json"
                event_path.write_text(json.dumps(event) + "\n")
                runtime_path = cell / "runtime-proof.json"
                binary_path = Path(self.recipe["images"][image]["binary"]["path"])
                runtime_path.write_text(json.dumps({"pid": pid, "birth_ticks": birth,
                    "image": image, "arm": "A1", "level": "high",
                    "ggml_paths": [str(binary_path)]}))
                complete = {"status": "COMPLETE", "row_id": self.request["id"],
                    "image": image, "arm": "A1", "level": "high",
                    "request_manifest_sha256": self.request_sha,
                    "production_recipe_sha256": self.recipe_sha,
                    "kfd_samples": str(cell / "kfd.jsonl"), "shim_log": str(cell / "hipmalloc.jsonl"),
                    "phase_attribution": str(cell / "phase-attribution.json"),
                    "report": str(report_path), "native_event_path": str(event_path),
                    "native_event_sha256": digest(event_path),
                    "runtime_proof_path": str(runtime_path),
                    "native_pid": pid, "native_birth_ticks": birth}
                (cell / "complete.json").write_text(json.dumps(complete))
                identities.append((pid, birth))
            e1_event = root / "E1-A1-high/native-first-event.json"
            result = {"status": "COMPLETE", "qualification_only": True,
                "row_id": self.request["id"], "nonce": nonce,
                "request_manifest_sha256": self.request_sha,
                "production_recipe_sha256": self.recipe_sha,
                "steps": [["E1", "A1", "high"], ["W", "A1", "high"]],
                "work_unit": self.recipe["qualification_work_unit"],
                "work_unit_wall_s": 100.0,
                "native_first_event_sha256": digest(e1_event)}
            result_path = root / "RESULT.json"
            result_path.write_text(json.dumps(result))
            env = dict(os.environ, FILLER_RESULTS_DIR=str(root))
            def check():
                return subprocess.run([sys.executable, str(checker)], env=env,
                                      capture_output=True, text=True).returncode
            self.assertEqual(check(), 0)
            self.assertNotEqual(identities[0], identities[1])

            e1_event.write_text("{}\n")
            result["native_first_event_sha256"] = digest(e1_event)
            result_path.write_text(json.dumps(result))
            e1_complete_path = root / "E1-A1-high/complete.json"
            e1_complete = json.loads(e1_complete_path.read_text())
            e1_complete["native_event_sha256"] = digest(e1_event)
            e1_complete_path.write_text(json.dumps(e1_complete))
            self.assertNotEqual(check(), 0, "empty event with matching file hashes must be rejected")

            good_event = {
                "id": self.request["id"], "nonce": nonce, "image": "E1", "phase": "normal",
                "native_first_event": True, "native_pid": 32100, "native_birth_ticks": 700000,
                "first_request": {"ok": True, "scope": "TARGET_SCRATCH_SERVER",
                    "manifest_sha256": self.request_sha, "production_recipe_sha256": "f" * 64,
                    "n_ctx_total": 524288, "n_ctx_per_slot": 524288, "total_slots": 1,
                    "prompt_tokens": request_max["prompt_tokens_required"], "kv_cache_mode": "split",
                    "native_pid": 32100, "native_birth_ticks": 700000,
                    "request": {"arm": "A1", "cache_seed_stage": "400k", "stage": "500k",
                                "needle": request_max["needle"],
                                "messages_sha256": request_max["messages_sha256"],
                                "rendered_sha256": request_max["rendered_sha256"]}}}
            e1_event.write_text(json.dumps(good_event) + "\n")
            result["native_first_event_sha256"] = digest(e1_event)
            result_path.write_text(json.dumps(result))
            e1_complete["native_event_sha256"] = digest(e1_event)
            e1_complete_path.write_text(json.dumps(e1_complete))
            self.assertNotEqual(check(), 0, "cross-recipe event with matching file hashes must be rejected")

    def test_native_event_writer_refuses_prompt_hash_kv_and_context_mismatches(self):
        spec = importlib.util.spec_from_file_location("yarn_needle_qual_test", HERE / "yarn_needle.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        messages = [{"role": "user", "content": "fixture exact request"}]
        messages_sha = hashlib.sha256(json.dumps(messages).encode()).hexdigest()
        recipe_sha, request_sha, nonce = "a" * 64, "b" * 64, "c" * 64

        def invoke(case):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                manifest = {"id": self.request["id"], "request_manifest_sha256": request_sha,
                    "prompt_tokens_required": 498965, "kv_cache_mode": "split",
                    "n_ctx_required": 524288, "per_slot_n_ctx_required": 524288,
                    "n_parallel_required": 1, "production_recipe": {"sha256": recipe_sha}}
                fixture = {"request_manifest_sha256": request_sha,
                    "production_recipe_sha256": recipe_sha,
                    "request": {"messages_sha256": messages_sha, "needle": "N19",
                        "prompt_tokens_required": 498965, "request_manifest_sha256": request_sha,
                        "production_recipe_sha256": recipe_sha, "rendered_sha256": "3" * 64}}
                manifest_path, fixture_path = root / "manifest.json", root / "fixture.json"
                log_path, event_path, stop_path = root / "server.log", root / "event.json", root / "stop"
                if case == "cross-recipe":
                    fixture["request"]["production_recipe_sha256"] = "d" * 64
                manifest_path.write_text(json.dumps(manifest))
                fixture_path.write_text(json.dumps(fixture))
                log_path.write_text("llama_context: kv_unified = true\n" if case == "wrong-kv"
                                    else "llama_context: kv_unified = false\n")
                stop_path.touch()
                env = {"YARN_QUAL_PHASE": "cutoff", "YARN_QUAL_IMAGE": "E1",
                    "YARN_QUAL_FIXTURE": str(fixture_path),
                    "WS58_MANIFEST_PATH": str(manifest_path), "WS58_PRODUCTION_RECIPE_SHA256": recipe_sha,
                    "YARN_QUAL_NATIVE_PID": str(os.getpid()), "YARN_QUAL_SERVER_LOG": str(log_path),
                    "YARN_QUAL_EVENT_FILE": str(event_path), "WS58_QUAL_NONCE": nonce,
                    "FILLER_STOPFILE": str(stop_path)}
                old = {key: os.environ.get(key) for key in env}
                os.environ.update(env)
                original_http_json = module.http_json
                def fake_http(url, body=None, timeout=30.0):
                    if url.endswith("/props"):
                        n_ctx = 262144 if case == "low-total-context" else 524288
                        return 200, {"default_generation_settings": {"n_ctx": n_ctx}}
                    n_ctx = 262144 if case == "low-slot-context" else 524288
                    return 200, [{"n_ctx": n_ctx}]
                module.http_json = fake_http
                prompt_count = 498964 if case == "wrong-prompt-count" else 498965
                actual_messages = messages + ([{"role": "user", "content": "tampered"}]
                                              if case == "wrong-message-hash" else [])
                try:
                    if case in ("wrong-prompt-count", "wrong-message-hash", "wrong-kv",
                                "low-total-context", "low-slot-context", "cross-recipe"):
                        with self.assertRaises(RuntimeError):
                            module.qualification_first_event("http://127.0.0.1:18437", "A1", "500k",
                                {"needle": "N19"}, actual_messages,
                                {"prompt_n": prompt_count, "cache_n": 0, "wall_s": 12.0})
                        self.assertFalse(event_path.exists())
                    else:
                        module.qualification_first_event("http://127.0.0.1:18437", "A1", "500k",
                            {"needle": "N19"}, actual_messages,
                            {"prompt_n": prompt_count, "cache_n": 0, "wall_s": 12.0})
                        event = json.loads(event_path.read_text())
                        self.assertEqual(event["first_request"]["prompt_tokens"], 498965)
                        self.assertEqual(event["first_request"]["n_ctx_total"], 524288)
                        self.assertEqual(event["first_request"]["n_ctx_per_slot"], 524288)
                        self.assertEqual(event["first_request"]["kv_cache_mode"], "split")
                        self.assertEqual(event["native_pid"], os.getpid())
                finally:
                    module.http_json = original_http_json
                    for key, value in old.items():
                        if value is None:
                            os.environ.pop(key, None)
                        else:
                            os.environ[key] = value
        for case in ("good", "wrong-prompt-count", "wrong-message-hash", "wrong-kv",
                     "low-total-context", "low-slot-context", "cross-recipe"):
            with self.subTest(case=case):
                invoke(case)

    def test_launcher_refuses_without_manifest_bound_owner_booking(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("WS58_")}
        result = subprocess.run(["/bin/bash", str(HERE / "launch.sh")], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 70)
        self.assertIn("REFUSED_UNREADY", result.stderr)
        self.assertNotIn("--min-window 5700", self.launch_text)
        self.assertIn('"$MIN_WINDOW_S"', self.launch_text)

    def test_window_validator_requires_and_accepts_exact_owner_booking(self):
        validator = HERE / "helper/validate_launch_window.py"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            record_path = root / "qual-bookings" / f"{self.request['id']}.json"
            record_path.parent.mkdir()
            window_s, min_window_s, max_wall_s, cleanup_s = 22500, 21600, 19000, 900
            manifest = {
                "id": self.request["id"], "request_manifest_sha256": self.request_sha,
                "production_recipe": {"path": str(HERE / "qualification/production_recipe.json"),
                                      "sha256": self.recipe_sha},
                "qual_fixture": {"sha256": digest(HERE / "qualification/qual_fixture.json")},
                "source_manifest": {"sha256": digest(HERE / "SOURCE.sha256")},
                "engine": {"path": "/mnt/raid0/llm/bin/filler_run14.sh", "sha256": "e" * 64},
                "claimed_cpus": [36, 37],
                "window_s": window_s, "min_window_s": min_window_s,
                "qualification": {}}
            target = {key: self.recipe[key] for key in ("images", "model", "request", "qualification_work_unit")}
            canonical = lambda value: hashlib.sha256(json.dumps(
                value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            unbooked = dict(manifest)
            unbooked["qualification"] = {}
            record = {
                "kind": "epyc.qual.booking.v1", "state": "BOOKED", "id": self.request["id"],
                "owner": "owner", "calendar_ref": "booking-ref",
                "issuer": {"pid": 123, "birth_ticks": 456},
                "start_utc": "2099-01-01T00:00:00Z", "end_utc": "2099-01-01T06:15:00Z",
                "resource": {"class": "gpu-quiet", "gpu": "mi210_0",
                    "gpu_quiet_exclusive": True, "cpus": "36-37", "physical_family": "36-37"},
                "limits": {"max_wall_s": max_wall_s, "cleanup_reserve_s": cleanup_s,
                    "max_rss_gib": 100, "max_output_gib": 20, "disk_floor_gib": 150},
                "pins": {"manifest_binding_sha256": canonical(unbooked),
                    "source_manifest_sha256": manifest["source_manifest"]["sha256"],
                    "production_recipe_sha256": self.recipe_sha, "engine_sha256": "e" * 64,
                    "qual_fixture_sha256": manifest["qual_fixture"]["sha256"],
                    "request_manifest_sha256": self.request_sha,
                    "prompt_tokens_required": self.request["request_max"]["prompt_tokens_required"],
                    "window_s": window_s, "min_window_s": min_window_s,
                    "recipe_target_sha256": canonical(target)}}
            record_path.write_text(json.dumps(record))
            manifest["qualification"] = {"booking": {
                "mode": "owner-booked-long-native", "record": {"path": str(record_path),
                    "sha256": digest(record_path)}, "requested_max_wall_s": max_wall_s,
                "cleanup_reserve_s": cleanup_s}}
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            env = dict(os.environ, WS58_MANIFEST_PATH=str(manifest_path))
            accepted = subprocess.run([sys.executable, str(validator)], env=env,
                                      capture_output=True, text=True)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(accepted.stdout.strip(), str(min_window_s))
            record["pins"]["production_recipe_sha256"] = "f" * 64
            record_path.write_text(json.dumps(record))
            manifest["qualification"]["booking"]["record"]["sha256"] = digest(record_path)
            manifest_path.write_text(json.dumps(manifest))
            rejected = subprocess.run([sys.executable, str(validator)], env=env,
                                      capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 70)
            self.assertIn("REFUSED_UNREADY", rejected.stderr)

    def test_qualification_work_unit_is_not_calibration(self):
        record = json.loads((HERE / "qualification/WORK-UNIT-CALIBRATION-REQUIRED.json").read_text())
        self.assertEqual(record["status"], "MISSING")
        self.assertIsNone(record["observed_wall_s_per_unit"])
        self.assertTrue(record["ready_manifest_must_remain_unpublished"])

    def test_candidate_contract_names_keeper_and_both_real_high_cells(self):
        self.assertIn("phase not in ('normal', 'cutoff')", self.run_text)
        self.assertIn("run_step('E1', 'A1', 'high', 'full', deadline)", self.run_text)
        self.assertIn("run_step('W', 'A1', 'high', 'full', deadline)", self.run_text)
        self.assertIn("'work_unit': recipe['qualification_work_unit']", self.run_text)
        self.assertIn("filler_run14.sh", self.launch_text)
        self.assertNotIn("filler_run13.sh", self.launch_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
