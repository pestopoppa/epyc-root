"""Synthetic controls for exact GPU-pool requests and ordinary planner exclusion."""
from dataclasses import replace
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
VIDYA = ROOT / "scripts/vidya"
sys.path[:0] = [str(VIDYA), str(VIDYA / "canary")]

import gpu_pool_context_exclusion as control
from adapters import gpu_pool_native as native_adapter
from claim_tuple import ClaimTuple, to_frames
from ledger import Ledger
from loop_beliefs import Target


class NativeResultBinding(unittest.TestCase):
    def test_repeated_seed_blocks_must_match_the_manifest_and_operator_order(self):
        out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        capture = out / "belief.json"
        result_path = out / "RESULT.json"
        capture_sha = "a" * 64
        row_id = "ni-gpu-pool-elementwise-20261118-v6"
        ops = ["NORM", "SUM", "SUM_ROWS"]
        seeds = list(range(2026102600, 2026102632))
        runs = [dict(seed=seed, op=op, rc=0, status="native_exit_recorded", generated_expected=2,
                     observed=2, passed=1, unsupported=1, failed=[])
                for seed in seeds for op in ops]
        request = dict(row_id=row_id, selected_ops=ops)
        native = dict(seeds=seeds, runs=runs, owned_pid_reaped=True,
                      grant=dict(smoke=False, record={},
                                 path=str(control.SCRATCH_ROOT / "compute-flags/grants" / f"{row_id}.grant")))

        # Keep the producer aggregates consistent with each control input so only block validation can reject it.
        def bind(request, native):
            count = len(native["runs"])
            result = dict(row_id=row_id, capture=str(capture), sha256=capture_sha, projected=count,
                          refused=0, failed=0, observed=2 * count, passed=count, unsupported=count,
                          resident_samples=2 * count)
            result_path.write_text(json.dumps(result))
            return control.validate_native_result(capture, capture_sha, dict(capture=request, native=native),
                                                  result_path)

        self.assertEqual(bind(request, native), {"path": str(result_path), "sha256": control.sha(result_path)})
        for name, malformed in (
            ("missing operator", runs[1:]),
            ("missing seed block", runs[:-3]),
            ("duplicate seed block", runs[:3] + runs[:3] + runs[6:]),
            ("out-of-order seed blocks", runs[3:6] + runs[:3] + runs[6:]),
            ("out-of-order operators", [runs[1], runs[0], *runs[2:]]),
            ("unlisted seed", [{**runs[0], "seed": seeds[-1] + 1}, *runs[1:]]),
        ):
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, "complete terminal invocations"):
                bind(request, {**native, "runs": malformed})
        for malformed in (None, [], [seeds[0], seeds[0]], [False, *seeds[1:]]):
            with self.subTest(seeds=malformed), self.assertRaisesRegex(RuntimeError, "unique seed manifest"):
                bind(request, {**native, "seeds": malformed})
        with self.assertRaisesRegex(RuntimeError, "complete terminal invocations"):
            bind(request, {k: v for k, v in native.items() if k != "seeds"})
        with self.assertRaisesRegex(RuntimeError, "unique selected operators"):
            bind({**request, "selected_ops": ops + [ops[0]]}, native)

        legacy = {k: v for k, v in native.items() if k != "seeds"}
        legacy.update(seed=seeds[0], runs=runs[:3])
        self.assertEqual(bind(request, legacy), {"path": str(result_path), "sha256": control.sha(result_path)})


class ScopeControls(unittest.TestCase):
    def setUp(self):
        self.out = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.research = Path(os.environ.get("GPU_POOL_CONTROL_RESEARCH", "/workspace/repos/epyc-inference-research")).resolve()
        if not (self.research / "scripts/kernel_rnd/autokernel/loop/belief_context.py").is_file():
            self.skipTest(f"research producer root missing belief_context.py: {self.research} "
                          "(set GPU_POOL_CONTROL_RESEARCH)")
        self.capture = self.out / "belief.json"

    def make_capture(self, *, smoke=False, spoof_scope=False, seeds=(7,)):
        identity = {"source": {"commit": "a" * 40, "removed_worktree_dirty_state": "UNKNOWN"},
                    "artifacts": [{"path": "/synthetic/backend-ops", "sha256": "b" * 64}],
                    "shim": {"path": "/synthetic/shim", "sha256": "c" * 64,
                             "original_source_digest_receipt": "d" * 64,
                             "later_recreated_source_matches_receipt": False}}
        ops = ["ROPE", "SOFT_MAX"]
        request = native_adapter.begin("attention", "ni-gpu-pool-attention-20990101-v1", identity,
                                       ops, producer=__file__)
        runs = []
        for seed in seeds:
            for op, passed in zip(ops, (1, 2)):
                log = self.out / f"{seed}-{op}.log"
                argv = ["synthetic", "-o", op, "--suite-seed", str(seed)]
                failed = f"  {op}(case=failed) FAIL"
                lines = [f"  {op}(case={i}) OK" for i in range(passed)]
                lines += [f"  {op}(case=unsupported) not supported", failed]
                log.write_text("\n".join(["ARGV " + json.dumps(argv), *lines]) + "\n")
                runs.append(dict(op=op, observed=passed + 2, passed=passed, unsupported=1,
                                 failed=[failed], argv=argv, log=str(log), log_sha256=control.sha(log), seed=seed, rc=1))
        scope = {"model_file": control.MODEL, "device": "gfx90a", "consumer": "autokernel.planner"}
        native = dict(schema=native_adapter.NATIVE, model_free=True, synthetic_control=True,
                      row_id=request["row_id"], invocation_token=request["invocation_token"],
                      **identity, scope=scope if spoof_scope else "candidate-local native CPU reference only",
                      runs=runs, grant={"smoke": smoke, "purpose": "synthetic control"})
        native_adapter.write_capture(self.capture, request, native)
        return runs

    def check_capture(self):
        return control.check_capture(self.capture, self.research, self.out, pinned_snapshot=True)

    def test_strict_ingest_preserves_candidate_counts_and_excludes_model_context(self):
        self.make_capture()
        report = self.check_capture()
        self.assertEqual([(c["op"], c["observed"], c["passed"], c["unsupported"], c["failed"])
                          for c in report["claims"]], [("ROPE", 3, 1, 1, 1), ("SOFT_MAX", 4, 2, 1, 1)])
        self.assertEqual(report["candidate_identity"]["source"]["removed_worktree_dirty_state"], "UNKNOWN")
        self.assertIs(report["candidate_identity"]["shim"]["later_recreated_source_matches_receipt"], False)
        self.assertEqual(set(report["readers"]), {"autokernel.planner", "autopilot.planner"})
        self.assertTrue(report["positive_planning_context"])
        self.assertFalse(report["official_native_acceptance"])
        self.assertFalse(report["production_consumer_adoption"])
        self.assertFalse(report["native_planning_context"])
        for claim in report["claims"]:
            read = report["candidate_reads"][claim["op"]]
            native_claim, = read["claims"]
            self.assertEqual(native_claim["op"], claim["op"])
            self.assertEqual(native_claim["candidate_sha256"], control.identity_digest(report["candidate_identity"]))
            self.assertEqual(read["reliance"]["accepted"], [claim["claim_id"]])
        for wrong in ("wrong_source", "wrong_artifact", "wrong_shim", "wrong_operator", "wrong_run", "missing_operator"):
            self.assertEqual(report["candidate_reads"][wrong]["claims"], [])
        records = [json.loads(line) for line in (self.out / "reads.jsonl").read_text().splitlines()]
        self.assertTrue(any(r["target_key"].startswith("candidate:") and r["nonempty_target"] for r in records))

    def test_partial_malformed_and_hybrid_candidate_requests_are_invalid(self):
        self.make_capture()
        request = json.loads(self.capture.read_text())["capture"]
        selector = {"scope": "candidate", "build_sha": request["identity"]["source"]["commit"],
                    "candidate_sha256": control.identity_digest(request["identity"]),
                    "op": "ROPE", "run_id": request["row_id"]}
        self.assertEqual(Target.from_mapping(selector).as_dict(), selector)
        for key in selector:
            with self.subTest(missing=key), self.assertRaises(ValueError):
                Target.from_mapping({k: v for k, v in selector.items() if k != key})
        for key, value in (("build_sha", "a" * 8), ("candidate_sha256", "b" * 63),
                           ("op", "rope"), ("run_id", "unsealed"), ("model_file", control.MODEL),
                           ("device", "gfx90a"), ("consumer", "autokernel.planner")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                Target.from_mapping({**selector, key: value})

    def test_repeated_candidate_claims_can_be_bounded_by_the_reader(self):
        self.make_capture(seeds=range(32))
        report = self.check_capture()
        self.assertEqual(report["ingest"]["rows_projected"], 64)
        for op in ("ROPE", "SOFT_MAX"):
            with self.subTest(op=op):
                read = report["candidate_reads"][op]
                expected = {c["claim_id"] for c in report["claims"] if c["op"] == op}
                presented = {c["claim_id"] for c in read["claims"]}
                self.assertEqual(len(expected), 32)
                self.assertEqual(read["reason"], "bounded")
                self.assertEqual(len(presented), control.CANDIDATE_TARGET_LIMIT)
                self.assertLess(presented, expected)
                self.assertEqual(set(read["reliance"]["accepted"]), presented)

    def test_native_scope_metadata_cannot_route_to_model_device_or_consumer(self):
        self.make_capture(spoof_scope=True)
        self.assertEqual(self.check_capture()["status"], "passed")

    def test_reader_can_present_a_real_scope_match_from_a_synthetic_triplet(self):
        self.make_capture()
        report = self.check_capture()
        claim = ClaimTuple(measurement_id="synthetic-gpu-pool-scope-positive-control",
                           metric="synthetic_control", value=1, date="2000-01-01T00:00:00Z",
                           category="CANDIDATE", claim="Independent model match control",
                           source_kind="synthetic-planner-scope-control", unit="cases",
                           attestation_locator="synthetic:planner-scope-positive-control",
                           applicability={"model_file": control.MODEL, "backend": "gpu"})
        path = self.out / "ledger.jsonl"
        ledger = Ledger(path)
        for frame in to_frames(claim, as_of="2000-01-01T00:00:00Z", adapter_id="synthetic-control/v1"):
            ledger.append(frame)
        consumer = control.consumer_for(self.research)
        reader = control.prepare(consumer, path, self.out, pinned_snapshot=True)[consumer.CONSUMER]
        self.assertEqual(consumer.reliable_claim_ids(reader.evidence), [f"clm_{claim.measurement_id}"])
        self.assertEqual(len(reader.evidence["claims"]), 1)
        self.assertIn("Independent model match control", reader.section)

        selector = report["candidate_reads"]["ROPE"]["selector"]
        harness = replace(claim, measurement_id="synthetic-harness",
                          applicability={"consumer": "gpu-pool.candidate"})
        foreign = replace(claim, measurement_id="synthetic-foreign-candidate",
                          applicability={**{k: v for k, v in selector.items() if k != "scope"},
                                         "scope_basis": "native"})
        for other in (harness, foreign):
            for frame in to_frames(other, as_of="2000-01-01T00:00:00Z", adapter_id="synthetic-control/v1"):
                ledger.append(frame)
        answer = control.prepare_candidate(consumer, path, self.out, selector, pinned_snapshot=True)
        visible = answer["evidence"]["claims"]
        self.assertEqual([c["claim_id"] for c in visible], report["candidate_reads"]["ROPE"]["reliance"]["accepted"])

    def test_same_source_candidate_hybrid_cannot_enter_ordinary_harness(self):
        consumer = control.consumer_for(self.research)
        hybrid = ClaimTuple(
            measurement_id="synthetic-gpu-pool-candidate-harness-hybrid",
            source_kind=native_adapter.SOURCE_KIND, metric="synthetic_control", value=1,
            date="2000-01-01T00:00:00Z", category="CANDIDATE",
            claim="Injected same-source candidate and harness scope", unit="cases",
            attestation_locator="synthetic:gpu-pool-candidate-harness-hybrid",
            applicability={"build_sha": "a" * 40, "candidate_sha256": "b" * 64,
                           "op": "ROPE", "run_id": "ni-gpu-pool-attention-20990101-v1",
                           "scope_basis": "native", "consumer": consumer.CONSUMER})
        ledger = Ledger(self.out / "ledger.jsonl")
        for frame in to_frames(hybrid, as_of="2000-01-01T00:00:00Z", adapter_id="synthetic-control/v1"):
            ledger.append(frame)
        answers = control.prepare(consumer, ledger.path, self.out, pinned_snapshot=True)
        for ready in answers.values():
            self.assertEqual(ready.ledger_state["frame_count"], 3)
            self.assertEqual(ready.evidence["reasons"], ["no_applicable_claims"])
            self.assertEqual(ready.evidence["claims"], [])
            self.assertEqual(ready.evidence["not_evidence_claim_ids"], [])
            self.assertEqual(ready.section, "")

    def test_smoke_capture_is_refused_before_planner_read(self):
        self.make_capture(smoke=True)
        with self.assertRaisesRegex(RuntimeError, "grant.smoke to be false"):
            self.check_capture()

    def test_native_result_must_bind_only_complete_official_terminal_capture(self):
        self.make_capture()
        record = json.loads(self.capture.read_text())
        native = record["native"]
        result_path = self.out / "RESULT.json"
        capture_sha = control.sha(self.capture)
        with self.assertRaisesRegex(RuntimeError, "official capture"):
            control.validate_native_result(self.capture, capture_sha, record, result_path)

        del native["synthetic_control"]
        native["grant"]["path"] = str(control.SCRATCH_ROOT / "compute-flags/grants" / (native["row_id"] + ".grant"))
        native["grant"]["record"] = {"regions": "mi210_0,184-191"}
        native["owned_pid_reaped"] = True
        with self.assertRaisesRegex(RuntimeError, "complete terminal invocations"):
            control.validate_native_result(self.capture, capture_sha, record, result_path)

        # Exercise the result-binding gate in isolation. The full replay separately verifies the seal and raw logs.
        for run in native["runs"]:
            run.update(rc=0, status="native_exit_recorded", observed=run["passed"] + 1, failed=[])
            run["generated_expected"] = run["observed"]
        result = dict(row_id=native["row_id"], capture=str(self.capture), sha256=capture_sha,
                      projected=2, refused=0, failed=0, observed=5, passed=3, unsupported=2, resident_samples=4)
        result_path.write_text(json.dumps(result))
        self.assertEqual(control.validate_native_result(self.capture, capture_sha, record, result_path),
                         {"path": str(result_path), "sha256": control.sha(result_path)})
        for key, value in (("row_id", "foreign"), ("sha256", "0" * 64), ("passed", 5), ("refused", False),
                           ("resident_samples", 3)):
            with self.subTest(key=key):
                result_path.write_text(json.dumps({**result, key: value}))
                with self.assertRaisesRegex(RuntimeError, "sealed capture|qualified residency"):
                    control.validate_native_result(self.capture, capture_sha, record, result_path)

    def test_pinned_snapshot_cannot_supply_native_planning_context(self):
        with self.assertRaisesRegex(RuntimeError, "requires checkout checks"):
            control.check_capture(self.capture, self.research, self.out, pinned_snapshot=True,
                                  native_result=self.out / "RESULT.json")

    def test_candidate_reader_refuses_stale_or_unchecked_context_even_with_matching_claim(self):
        self.make_capture()
        record = json.loads(self.capture.read_text())
        claims = [{"claim_id": f"clm_gpu-pool:{record['sha256']}:0", "op": "ROPE"}]
        ledger = self.out / "ledger.jsonl"
        head = "a" * 64
        matching = {"ledger_state": {"head_hash": head, "ledger_path": str(ledger), "fresh": True},
                    "evidence": {"claim_ids": [claims[0]["claim_id"]]},
                    "reader_checkout_check": True, "reader_checkout": {"current": True}}
        for changes, reason in (
            ({"ledger_state": {**matching["ledger_state"], "fresh": False}}, "current scratch ledger"),
            ({"reader_checkout_check": False}, "did not run"),
            ({"reader_checkout": None}, "current reader checkout"),
            ({"reader_checkout": {"current": False}}, "current reader checkout"),
        ):
            with self.subTest(changes=changes), patch.object(control, "prepare_candidate", return_value={**matching, **changes}):
                with self.assertRaisesRegex(RuntimeError, reason):
                    control.check_candidate_reads(None, ledger, self.out, record["capture"], claims, head,
                                                  pinned_snapshot=False)

    def test_historical_standalone_record_is_declined(self):
        self.capture.write_text(json.dumps({"schema": native_adapter.NATIVE, "model_free": True, "runs": []}))
        with self.assertRaisesRegex(RuntimeError, r"'declined': \['"):
            self.check_capture()

    def test_modified_log_is_refused_before_planner_read(self):
        runs = self.make_capture()
        Path(runs[0]["log"]).write_text("changed raw log\n")
        with self.assertRaisesRegex(RuntimeError, "raw log changed"):
            self.check_capture()
