#!/usr/bin/env python3
"""Self-test for validate_serving_config.py (no GPU, no grant): python3 -I test_validate_serving_config.py"""
import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate_serving_config as v  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SEED = os.path.join(ROOT, "docs", "reference", "kernel-manifests", "serving-configs", "C22.serving-config.json")
SHAPE = {"n_ctx": 1000, "batch": 512, "ubatch": 512, "kv_unified": True, "kv_quant": {"k": "q8_0", "v": "q8_0"}}
RUNTIME = {"slots": 4, "ctx_checkpoints": 32, "cache_ram": 65536}


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.res = os.path.join(self.d.name, "RESULT.json")
        open(self.res, "w").write('{"verdict": "PASS"}')
        self.sha = hashlib.sha256(open(self.res, "rb").read()).hexdigest()
        prov = {"row_id": "r1", "result_json": self.res, "result_sha256": self.sha, "store": "/s"}
        cfg = {"n_ctx": 1000, "np": 4, "batch": 512, "ubatch": 512, "kv_k": "q8_0", "kv_v": "q8_0", "kv_unified": True,
               "ctx_checkpoints": 32, "cache_ram_mib": 65536,
               "drafter": {"spec_type": "draft-dflash", "model": "m", "n_max": 7},
               "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 20}}
        pend = lambda n: {"name": n, "status": "pending", "row_id": "r2", "pending_reason": "no RESULT.json"}  # noqa: E731
        self.doc = {"schema": v.SCHEMA, "champion": "CX", "generated_utc": "2026-11-24T00:00:00Z", "servers": [{
            "server_mode": "m", "port": 1, "model": "M", "device": "d", "registry_serving_shape": SHAPE,
            "registry_runtime": dict(RUNTIME),
            "optimal": {"status": "measured", "config": cfg, "argv_delta": [], "provenance": prov},
            "alternates": [pend("latency"), pend("throughput")],
            "tradeoffs": [{"id": "t1", "config": "optimal", "throughput_tok_s": 30.0, "itl_p50_ms": None, "itl_p95_ms": None,
                           "temperature": 1.0, "acceptance": 0.4, "memory_gib": 49.0,
                           "unmeasured": {"itl_p50_ms": "not measured", "itl_p95_ms": "not measured"}, "provenance": prov}]}]}

    def tearDown(self):
        self.d.cleanup()

    def errs(self, doc=None, **kw):
        return v.validate(doc or self.doc, **kw).errors

    def has(self, text, **kw):
        return any(text in e for e in self.errs(**kw))

    def test_valid(self):
        self.assertEqual(self.errs(strict_files=True), [])

    def test_wrong_schema(self):
        self.doc["schema"] = "x"
        self.assertTrue(self.has("schema must be"))

    def test_sha_mismatch(self):
        self.doc["servers"][0]["optimal"]["provenance"]["result_sha256"] = "0" * 64
        self.assertTrue(self.has("does not match the file on disk"))

    def test_bad_sha_format(self):
        self.doc["servers"][0]["optimal"]["provenance"]["result_sha256"] = "abc"
        self.assertTrue(self.has("64 lowercase hex"))

    def test_missing_provenance_field(self):
        del self.doc["servers"][0]["optimal"]["provenance"]["row_id"]
        self.assertTrue(self.has("provenance.row_id required"))

    def test_missing_result_file_warns_or_errors(self):
        os.remove(self.res)
        self.assertEqual(self.errs(), [])
        self.assertEqual(len(v.validate(self.doc).warnings), 2)
        self.assertTrue(self.has("not present on this host", strict_files=True))

    def test_pending_cannot_carry_sha_or_numbers(self):
        a = self.doc["servers"][0]["alternates"][0]
        a["result_sha256"] = self.sha
        a["throughput_tok_s"] = 31.0
        e = self.errs()
        self.assertTrue(any("result_sha256" in x for x in e) and any("throughput_tok_s" in x for x in e))

    def test_pending_needs_row_id_or_needs_row(self):
        a = self.doc["servers"][0]["alternates"][0]
        a["row_id"] = None
        self.assertTrue(self.has("needs row_id"))
        a["needs_row"] = "no row exists"
        self.assertEqual(self.errs(), [])

    def test_pending_needs_reason(self):
        del self.doc["servers"][0]["alternates"][0]["pending_reason"]
        self.assertTrue(self.has("pending_reason"))

    def test_measured_optimal_needs_two_alternates(self):
        self.doc["servers"][0]["alternates"].pop()
        self.assertTrue(self.has("needs 2-3 named alternates"))

    def test_too_many_alternates(self):
        self.doc["servers"][0]["alternates"] += [
            {"name": "a", "status": "pending", "row_id": "r", "pending_reason": "x"},
            {"name": "b", "status": "pending", "row_id": "r", "pending_reason": "x"}]
        self.assertTrue(self.has("at most 3 alternates"))

    def test_pending_optimal_allows_no_alternates(self):
        s = self.doc["servers"][0]
        s["optimal"] = {"status": "pending", "row_id": "r9", "pending_reason": "not filed"}
        s["alternates"], s["tradeoffs"] = [], []
        self.assertEqual(self.errs(), [])

    def test_duplicate_alternate_name(self):
        self.doc["servers"][0]["alternates"][1]["name"] = "latency"
        self.assertTrue(self.has("duplicate alternate name"))

    def test_null_metric_needs_reason(self):
        del self.doc["servers"][0]["tradeoffs"][0]["unmeasured"]["itl_p95_ms"]
        self.assertTrue(self.has("itl_p95_ms is null without"))

    def test_tradeoff_missing_metric(self):
        del self.doc["servers"][0]["tradeoffs"][0]["memory_gib"]
        self.assertTrue(self.has("tradeoff.memory_gib required"))

    def test_acceptance_range(self):
        self.doc["servers"][0]["tradeoffs"][0]["acceptance"] = 1.4
        self.assertTrue(self.has("acceptance must be in [0, 1]"))

    def test_tradeoff_on_pending_config(self):
        self.doc["servers"][0]["tradeoffs"][0]["config"] = "latency"
        self.assertTrue(self.has("references pending config"))

    def test_tradeoff_unknown_config(self):
        self.doc["servers"][0]["tradeoffs"][0]["config"] = "nope"
        self.assertTrue(self.has("must be 'optimal'"))

    def test_config_differs_from_registry_needs_delta(self):
        self.doc["servers"][0]["optimal"]["config"]["ubatch"] = 1024
        self.assertTrue(self.has("differs from registry serving_shape.ubatch"))
        self.doc["servers"][0]["optimal"]["argv_delta"] = [{"flag": "-ub", "value": "1024", "reason": "arm"}]
        self.assertEqual(self.errs(), [])

    def test_kv_differs_needs_delta(self):
        self.doc["servers"][0]["optimal"]["config"]["kv_k"] = "f16"
        self.assertTrue(self.has("kv_k"))

    def test_argv_delta_needs_reason(self):
        self.doc["servers"][0]["optimal"]["argv_delta"] = [{"flag": "-ub", "value": "512"}]
        self.assertTrue(self.has("needs a reason"))

    def test_config_missing_key(self):
        del self.doc["servers"][0]["optimal"]["config"]["cache_ram_mib"]
        self.assertTrue(self.has("config.cache_ram_mib required"))

    def test_registry_drift(self):
        reg = {"server_mode": {"m": {"serving_shape": dict(SHAPE, batch=2048), "slots": 4,
                                     "ctx_checkpoints": 32, "cache_ram": 65536}}}
        self.assertTrue(self.has("drifted from the live registry", registry=reg))
        reg["server_mode"]["m"]["serving_shape"] = SHAPE
        self.assertEqual(self.errs(registry=reg), [])

    def test_duplicate_server(self):
        self.doc["servers"].append(copy.deepcopy(self.doc["servers"][0]))
        self.assertTrue(self.has("duplicate (server_mode, port)"))

    def test_evidence_provenance_checked(self):
        self.doc["servers"][0]["evidence"] = [{"row_id": "r3", "result_json": self.res, "result_sha256": "1" * 64}]
        self.assertTrue(self.has("does not match the file on disk"))

    # ---- defect 5: a fabricated provenance must fail strict validation (the fabricated-sha probe)
    def test_fabricated_sha_on_nonexistent_path_fails_strict_and_only_warns_lax(self):
        p = self.doc["servers"][0]["optimal"]["provenance"]
        p["result_json"], p["result_sha256"] = "/nonexistent/fabricated/RESULT.json", "f" * 64
        self.assertEqual(self.errs(), [])  # the lax CLI default cannot see it ...
        self.assertTrue(self.has("not present on this host", strict_files=True))  # ... strict callers must

    # ---- defect 12: value-taking flags need a value; `|` and whitespace are rejected
    def delta(self, *rows):
        self.doc["servers"][0]["optimal"]["argv_delta"] = [dict(r, reason="r") for r in rows]

    def test_value_flag_without_value_is_rejected(self):
        for flag in ("-b", "-ub", "-c", "-ctk", "--some-new-flag"):
            self.delta({"flag": flag})
            self.assertTrue(self.has("takes a value"), flag)

    def test_value_flag_with_boolean_value_is_rejected(self):
        self.delta({"flag": "-b", "value": True})
        self.assertTrue(self.has("takes a value"))

    def test_bare_switch_takes_no_value(self):
        self.delta({"flag": "--no-warmup"})
        self.assertEqual(self.errs(), [])
        self.delta({"flag": "--no-warmup", "value": 1})
        self.assertTrue(self.has("bare switch"))

    def test_pipe_and_whitespace_values_are_rejected(self):
        self.delta({"flag": "-ub", "value": "1024|2048"})
        self.assertTrue(self.has("contains '|'"))
        self.delta({"flag": "-ctk", "value": "q8_0 q4_0"})
        self.assertTrue(self.has("contains whitespace"))

    def test_int_flag_value_must_be_integer(self):
        self.delta({"flag": "-b", "value": "big"})
        self.assertTrue(self.has("must be an integer"))
        self.delta({"flag": "-b", "value": 1024.5})
        self.assertTrue(self.has("must be an integer"))

    def test_list_value_only_in_intended_delta(self):
        self.delta({"flag": "-b", "value": [1024, 2048]})
        self.assertTrue(self.has("must be a scalar"))
        a = self.doc["servers"][0]["alternates"][0]
        a["intended_delta"] = [{"flag": "-b", "value": [1024, 2048], "reason": "arms"}]
        self.doc["servers"][0]["optimal"]["argv_delta"] = []
        self.assertEqual(self.errs(), [])
        a["intended_delta"] = [{"flag": "-b", "value": "1024|2048", "reason": "arms"}]
        self.assertTrue(self.has("contains '|'"))

    def test_temperature_flag_is_low_temperature_only(self):
        self.delta({"flag": "--temp", "value": 0.6})
        self.assertEqual(self.errs(), [])
        self.delta({"flag": "--temp", "value": 1.5})
        self.assertTrue(self.has("no high-temperature testing"))

    def test_np_ctxcp_cache_ram_are_compared_not_just_written(self):
        cfg = self.doc["servers"][0]["optimal"]["config"]
        for ckey, val, flag in (("np", 6, "-np"), ("ctx_checkpoints", 16, "--ctx-checkpoints"),
                                ("cache_ram_mib", 32768, "--cache-ram")):
            old = cfg[ckey]
            cfg[ckey] = val
            self.assertTrue(self.has("differs from registry runtime"), ckey)
            self.delta({"flag": flag, "value": val})
            self.assertEqual(self.errs(), [], ckey)
            self.delta()
            cfg[ckey] = old

    def test_registry_runtime_required_for_measured_optimal_and_drift_checked(self):
        del self.doc["servers"][0]["registry_runtime"]
        self.assertTrue(self.has("registry_runtime"))
        self.doc["servers"][0]["registry_runtime"] = dict(RUNTIME)
        reg = {"server_mode": {"m": {"serving_shape": SHAPE, "slots": 4, "ctx_checkpoints": 32, "cache_ram": 65536}}}
        self.assertEqual(self.errs(registry=reg), [])
        reg["server_mode"]["m"]["slots"] = 2
        self.assertTrue(self.has("registry_runtime.slots=4 drifted", registry=reg))

    def test_cli_exit_codes(self):
        good, bad = os.path.join(self.d.name, "g.json"), os.path.join(self.d.name, "b.json")
        json.dump(self.doc, open(good, "w"))
        self.doc["schema"] = "x"
        json.dump(self.doc, open(bad, "w"))
        run = lambda p: subprocess.run([sys.executable, "-I", os.path.join(HERE, "validate_serving_config.py"), p],  # noqa: E731
                                       capture_output=True, text=True).returncode
        self.assertEqual((run(good), run(bad), run(os.path.join(self.d.name, "none.json"))), (0, 1, 2))

    def test_committed_seed_is_valid(self):
        if not os.path.isfile(SEED):
            self.skipTest("seed artifact absent")
        self.assertEqual(v.validate(json.load(open(SEED))).errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
