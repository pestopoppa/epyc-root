from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from dashboard import server
from tests.test_dashboard_autokernel_v26 import V26Fixture, _frozen, _seal

_STAGE_DIR_NAMES = {
    "measurement_graphs_off": "measurement-graphs-off",
    "target_runtime_graphs_on": "target-runtime-graphs-on",
    "production_graphs_on": "cumulative-vs-production-graphs-on",
}

RECEIPT_REF_KEYS = ("incremental_exact_route_receipt_sha256",
                    "incremental_graphs_off_receipt_sha256",
                    "incremental_graphs_on_receipt_sha256",
                    "production_graphs_on_receipt_sha256")


def _sha256(value: object) -> str:
    digest = server._discovery_controller_state_hash(value)
    assert digest is not None
    return digest


class FinalV27CumulativeFixture:
    """Seed one final-producer-schema cumulative operation into a V26Fixture.

    The operation mirrors the sealed carrier layout of the research repo
    (codex/autokernel-performance-carrier-closure-v3-20260822, PERF repair
    b12de815): runner-plan.json, proof/proof-bundle.json, three sealed runner
    results, cumulative-performance.json, composition-authority.jsonl (pre_run
    + result), screen-result.json, and the controller ledger next to state.
    Journal payloads are derived with the same pure re-derivation functions
    the dashboard uses to bind them.
    """

    def __init__(self, fixture: V26Fixture, *,
                 operation_key: str = "a" * 64,
                 cumulative_fraction: float = 0.04,
                 classification: str = "candidate",
                 promotion_eligible: bool = True,
                 promotion_reason: str = "incremental_and_cumulative_positive",
                 incremental_effects: tuple[float, float, float] = (0.02, 0.03, 0.04),
                 sealed: bool = True) -> None:
        self.fixture = fixture
        self.operation_key = operation_key
        self.operation = fixture.bundle / "operations" / self.operation_key
        self.operation.mkdir(mode=0o700)
        (self.operation / "proof").mkdir(mode=0o700)
        self.stages: dict[str, Path] = {}
        for label in server._V27_STAGE_LABELS:
            directory = (self.operation / "runner" / "s1" /
                         _STAGE_DIR_NAMES[label])
            directory.mkdir(parents=True, mode=0o700)
            self.stages[label] = directory
        self.performance_path = self.operation / "cumulative-performance.json"
        self.candidate_identity = self._identity("candidate")
        self.anchor_identity = self._identity("anchor")
        pair = _seal({
            "schema": "epyc.autokernel.cumulative_build_pair.v1",
            "operation_key": self.operation_key,
            "plan_sha256": "b" * 64,
            "anchor": self._binding("anchor"),
            "candidate": self._binding("candidate"),
        }, "pair_sha256")
        correctness = _seal({
            "schema": "epyc.autokernel.composition_full_correctness.v1",
            "operation_key": self.operation_key,
            "build_pair_sha256": pair["pair_sha256"],
            "candidate_build_identity_sha256": _sha256(self.candidate_identity),
            "suite_id": "fixture-suite",
            "cases_sha256": "c" * 64,
            "receipt_sha256": "d" * 64,
            "passed": True,
            "current_full_suite": True,
        }, "result_sha256")
        production = _seal({
            "schema": "epyc.autokernel.frozen_production_authority.v2",
            "production_commit": "1" * 40,
            "build_identity": self.anchor_identity,
            "build_identity_sha256": _sha256(self.anchor_identity),
            "runtime_snapshot_sha256": "e" * 64,
            "comparator_receipt_sha256": "f" * 64,
            "graphs_mode": "graphs_on",
            "frame_sha256": "10" * 32,
            "measurement_protocol_sha256": "11" * 32,
            "measurement_receipt_sha256": "12" * 32,
            "model_sha256": "13" * 32,
            "workload_sha256": "14" * 32,
            "runtime_config_sha256": "15" * 32,
            "observed_workload_sha256": "16" * 32,
            "observed_runtime_config_sha256": "17" * 32,
            "metric": "tokens_per_second",
            "direction": "higher_is_better",
        }, "authority_sha256")
        self.plan = _seal({
            "schema": server._V27_RUNNER_PLAN_SCHEMA,
            "authority": server._V27_AUTHORITY,
            "promotion_claim": False,
            "operation_key": self.operation_key,
            "composition_plan_sha256": "b" * 64,
            "composition_build_pair": pair,
            "composition_correctness": correctness,
            "composition_production_authority": production,
            "composition_exact_route_receipt_sha256": "18" * 32,
            "composition_expected_route_set_sha256": "19" * 32,
            "composition_target_runtime_frame_sha256": "1a" * 32,
            "measurement_graphs_off_output_dir": str(self.stages[
                "measurement_graphs_off"]),
            "target_runtime_graphs_on_output_dir": str(self.stages[
                "target_runtime_graphs_on"]),
            "production_graphs_on_output_dir": str(self.stages[
                "production_graphs_on"]),
            "cumulative_performance_path": str(self.performance_path),
        }, "receipt_sha256")
        self._write_sealed(self.operation / "runner-plan.json", self.plan,
                           "receipt_sha256")
        proof_bundle = _seal({
            "schema": server._V27_PROOF_BUNDLE_SCHEMA,
            "authority": server._V27_AUTHORITY,
            "promotion_claim": False,
            "bundle": {"manifest_sha256": "1b" * 32,
                       "candidate": self.candidate_identity,
                       "anchor": self.anchor_identity,
                       "workload_sha256": "14" * 32,
                       "correctness": {}, "attribution": {},
                       "bundle_sha256": "1c" * 32},
        }, "receipt_sha256")
        self._write_sealed(self.operation / "proof" / "proof-bundle.json",
                           proof_bundle, "receipt_sha256")
        for label in server._V27_STAGE_LABELS:
            graph_mode = ("on" if label in (
                "target_runtime_graphs_on", "production_graphs_on") else "off")
            factor = ("cumulative_production"
                      if label == "production_graphs_on" else "source_patch")
            effect = (incremental_effects[1] if label ==
                      "measurement_graphs_off" else
                      incremental_effects[2] if label ==
                      "target_runtime_graphs_on" else cumulative_fraction)
            body = _seal({
                "schema": server._V27_SCREEN_RESULT_SCHEMA,
                "authority": server._V27_AUTHORITY,
                "non_promotable": True,
                "promotion_claim": False,
                "hip_residency_proved": True,
                "runtime_graphs": graph_mode,
                "median_relative": effect,
                "baseline_sha256": "1d" * 32,
                "factor": factor,
                "candidate_identity": self.candidate_identity,
                "anchor_identity": self.anchor_identity,
            }, "result_sha256")
            self._write_sealed(self.stages[label] / "result.json", body,
                               "result_sha256")
        self.cumulative = self._cumulative_receipt(
            cumulative_fraction=cumulative_fraction,
            classification=classification,
            promotion_eligible=promotion_eligible,
            promotion_reason=promotion_reason,
            incremental_effects=incremental_effects,
            build_pair_sha256=pair["pair_sha256"],
            correctness_result_sha256=correctness["result_sha256"],
            production=production)
        self._append_journal_event(
            kind="pre_run",
            payload=server._v27_pre_run_commitment(
                (self.operation / "runner-plan.json").read_bytes(),
                self.plan, (self.operation / "proof" /
                            "proof-bundle.json").read_bytes()))
        if sealed:
            self.seal_result()

    def seal_result(self, *, cumulative: dict | None = None) -> None:
        self.cumulative = cumulative or self.cumulative
        self._write_sealed(self.performance_path, self.cumulative,
                           "result_sha256")
        screen = _seal({
            "schema": server._V27_OPERATION_RESULT_SCHEMA,
            "authority": server._V27_AUTHORITY,
            "promotion_claim": False,
            "operation_key": self.operation_key,
            "manifest_sha256": "1e" * 32,
            "composition_plan_sha256": "b" * 64,
            "screen": {}, "receipt_series": [], "effects": [],
        }, "receipt_sha256")
        self._write_sealed(self.operation / "screen-result.json", screen,
                           "receipt_sha256")
        self._append_journal_event(
            kind="result",
            payload=server._v27_result_commitment(
                self.operation,
                (self.operation / "runner-plan.json").read_bytes(),
                self._stage_results(),
                self.performance_path.read_bytes(),
                self.cumulative, True))

    def write_ledger(self, *, promotion_eligible: bool,
                     promotion_reason: str,
                     cumulative_performance_result_sha256: str | None = None,
                     terminal_sha256: str | None = None) -> None:
        ledger = {
            "schema": server._V27_COMPOSITION_LEDGER_SCHEMA,
            "campaign_id": "ak-cumulative-fixture",
            "max_scientific_attempts": 10,
            "initial_authority": {}, "authority": {}, "pending": None,
            "scientific_attempts": 1, "generation": 1,
            "terminals": [{
                "schema": "epyc.autokernel.cumulative_composition_terminal.v3",
                "operation_key": self.operation_key,
                "plan_sha256": "b" * 64,
                "plan": {}, "lever_sha256": "1f" * 32,
                "cross_campaign_candidate_sha256": "20" * 32,
                "isolated_result_sha256s": ["21" * 32, "22" * 32],
                "disposition": "admitted",
                "scientific_budget_spent": True,
                "build_pair": None, "correctness": None, "comparison": None,
                "cumulative_performance": None, "cumulative_performance_ref": None,
                "correctness_result_sha256": "d" * 64,
                "comparison_result_sha256": "23" * 32,
                "cumulative_performance_result_sha256": (
                    cumulative_performance_result_sha256
                    or self.cumulative["result_sha256"]),
                "promotion_eligible": promotion_eligible,
                "promotion_reason": promotion_reason,
                "admitted_authority_sha256": "24" * 32,
                "reason_code": "incremental_admitted_promotion_eligible",
                "infrastructure_receipt_sha256": None,
                "attribution_receipt_sha256": None,
                "terminal_sha256": terminal_sha256 or "25" * 32,
            }],
        }
        (self.fixture.state / "cumulative-composition.json").write_text(
            json.dumps(ledger, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")

    def _cumulative_receipt(self, *, cumulative_fraction: float,
                            classification: str, promotion_eligible: bool,
                            promotion_reason: str,
                            incremental_effects: tuple[float, float, float],
                            build_pair_sha256: str,
                            correctness_result_sha256: str,
                            production: dict) -> dict:
        refs = {
            "incremental_exact_route_receipt_ref": {
                "schema": "epyc.autokernel.cumulative_measurement_ref.v1",
                "role": "exact_route", "path": str(
                    self.operation / "proof" / "attribution-pair.json"),
                "sha256": "18" * 32},
            "incremental_graphs_off_receipt_ref": {
                "schema": "epyc.autokernel.cumulative_measurement_ref.v1",
                "role": "incremental_graphs_off", "path": str(
                    self.stages["measurement_graphs_off"] / "result.json"),
                "sha256": "26" * 32},
            "incremental_graphs_on_receipt_ref": {
                "schema": "epyc.autokernel.cumulative_measurement_ref.v1",
                "role": "incremental_graphs_on", "path": str(
                    self.stages["target_runtime_graphs_on"] / "result.json"),
                "sha256": "27" * 32},
            "production_graphs_on_receipt_ref": {
                "schema": "epyc.autokernel.cumulative_measurement_ref.v1",
                "role": "production_graphs_on", "path": str(
                    self.stages["production_graphs_on"] / "result.json"),
                "sha256": "28" * 32},
        }
        body = {
            "schema": server._V27_CUMULATIVE_PERFORMANCE_SCHEMA,
            "authority": server._V27_PROMOTION_GATE_AUTHORITY,
            "promotion_authority": True,
            "operation_key": self.operation_key,
            "plan_sha256": "b" * 64,
            "accepted_authority_sha256": "29" * 32,
            "accepted_patch_set_sha256": "2a" * 32,
            "build_pair_sha256": build_pair_sha256,
            "correctness_result_sha256": correctness_result_sha256,
            "incremental_comparison_result_sha256": "2b" * 32,
            "frozen_production": production,
            "model_sha256": "13" * 32,
            "workload_sha256": "14" * 32,
            "runtime_config_sha256": "15" * 32,
            "protocol_frame_sha256": "2c" * 32,
            "metric": "decode_tokens_per_s",
            "metric_direction": "higher_better",
            "incremental_exact_route_effect_fraction": incremental_effects[0],
            "incremental_graphs_off_effect_fraction": incremental_effects[1],
            "incremental_graphs_on_effect_fraction": incremental_effects[2],
            "cumulative_graphs_on_effect_fraction": cumulative_fraction,
            **refs,
            **{key: value for key, value in zip(
                RECEIPT_REF_KEYS, ("18" * 32, "26" * 32, "27" * 32, "28" * 32))},
            "incremental_graphs_off_frame_sha256": "2d" * 32,
            "incremental_graphs_on_frame_sha256": "2e" * 32,
            "production_graphs_on_frame_sha256": "2f" * 32,
            "production_graphs_mode": "on",
            "cumulative_classification": classification,
            "promotion_eligible": promotion_eligible,
            "promotion_reason": promotion_reason,
            "composition_terminal_sha256": "30" * 32,
        }
        return _seal(body, "result_sha256")

    def _identity(self, seed: str) -> dict:
        return {
            "source_commit": "1" * 40,
            "source_sha256": _sha256(seed + "-source"),
            "binary_sha256": _sha256(seed + "-binary"),
            "hip_library_sha256": _sha256(seed + "-hip"),
            "config_sha256": _sha256(seed + "-config"),
            "linkage_sha256": _sha256(seed + "-linkage"),
        }

    def _binding(self, seed: str) -> dict:
        return {
            "patch_set_sha256": "31" * 32,
            "source_materialization_receipt_sha256": "32" * 32,
            "build_identity": self._identity(seed),
            "build_identity_sha256": _sha256(self._identity(seed)),
        }

    def _stage_results(self) -> dict:
        results = {}
        for label in server._V27_STAGE_LABELS:
            path = self.stages[label] / "result.json"
            raw = path.read_bytes()
            results[label] = {
                "present": True, "valid": True,
                "path": str(path.resolve()),
                "file_sha256": hashlib.sha256(raw).hexdigest(),
                "result_sha256": json.loads(raw)["result_sha256"],
            }
        return results

    def _write_sealed(self, path: Path, body: dict, native_key: str) -> None:
        body = copy.deepcopy(body)
        body.pop(native_key, None)
        body[native_key] = server._discovery_controller_state_hash({
            key: item for key, item in body.items() if key != native_key})
        path.write_bytes(server._canonical_json_bytes(body) + b"\n")

    def _append_journal_event(self, *, kind: str, payload: dict) -> None:
        path = self.operation / "composition-authority.jsonl"
        rows = []
        if path.exists():
            rows = [json.loads(line) for line in
                    path.read_text(encoding="utf-8").splitlines()]
        event = {
            "schema": server._V27_AUTHORITY_JOURNAL_SCHEMA,
            "sequence": len(rows) + 1,
            "previous_event_sha256": (rows[-1]["event_sha256"]
                                      if rows else "0" * 64),
            "kind": kind,
            "operation_key": self.operation_key,
            "payload": payload,
        }
        event["event_sha256"] = server._discovery_controller_state_hash({
            key: item for key, item in event.items() if key != "event_sha256"})
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(
                event, sort_keys=True, separators=(",", ":")) + "\n")


class DashboardAutokernelV27FinalTests(unittest.TestCase):
    def _projected(self, fixture: FinalV27CumulativeFixture) -> dict:
        row = server._v27_cumulative_operation(
            fixture.operation, fixture.fixture.state,
            fixture.fixture.bundle.name)
        self.assertIsNotNone(row)
        return row

    def test_final_v27_product_pins_stay_unset_and_none_are_needed(self) -> None:
        for pin in (
                "_DISCOVERY_V27_PRODUCER_COMMIT",
                "_DISCOVERY_V27_EXECUTION_MODULE_SHA256",
                "_DISCOVERY_V27_DEPLOYMENT_SEMANTIC_SHA256",
                "_DISCOVERY_V27_DEPLOYMENT_FILE_SHA256",
                "_DISCOVERY_V27_GRAPH_SHA256",
                "_DISCOVERY_V27_GRAPH_FILE_SHA256"):
            self.assertIsNone(getattr(server, pin))
        with tempfile.TemporaryDirectory() as directory:
            fixture = FinalV27CumulativeFixture(V26Fixture(Path(directory)))
            row = self._projected(fixture)
            self.assertIs(row["available"], True)
            self.assertIs(row["trusted"], True)
            self.assertEqual(row["journal"]["integrity"], "matched")

    def test_positive_cumulative_headline_is_trusted_and_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = FinalV27CumulativeFixture(V26Fixture(Path(directory)))
            fixture.write_ledger(promotion_eligible=True,
                                 promotion_reason=
                                 "incremental_and_cumulative_positive")
            row = self._projected(fixture)
            self.assertIs(row["trusted"], True)
            self.assertIsNone(row["receipt_error"])
            self.assertEqual(row["headline"], {
                "classification": "candidate",
                "positive": True,
                "label": ("cumulative candidate is faster than frozen "
                          "production (validated)"),
            })
            receipt = row["receipt"]
            self.assertIs(receipt["valid"], True)
            self.assertEqual(receipt["cumulative_classification"], "candidate")
            self.assertEqual(receipt["cumulative_graphs_on_effect_fraction"],
                             0.04)
            self.assertEqual(receipt["incremental_exact_route_effect_fraction"],
                             0.02)
            self.assertEqual(receipt["incremental_graphs_off_effect_fraction"],
                             0.03)
            self.assertEqual(receipt["incremental_graphs_on_effect_fraction"],
                             0.04)
            self.assertIs(receipt["promotion_eligible"], True)
            self.assertEqual(receipt["promotion_reason"],
                             "incremental_and_cumulative_positive")
            self.assertEqual(receipt["metric"], "decode_tokens_per_s")
            self.assertEqual(receipt["metric_direction"], "higher_better")
            self.assertEqual(receipt["frozen_production"][
                "production_commit"], "1" * 40)
            self.assertEqual(receipt["frozen_production"]["graphs_mode"],
                             "graphs_on")
            self.assertEqual(row["journal"]["integrity"], "matched")
            self.assertIs(row["journal"]["pre_run"], True)
            self.assertIs(row["journal"]["result"], True)
            self.assertIs(row["ledger"]["agrees"], True)

    def test_valid_nonpositive_headline_renders_distinctly_not_blank(self) -> None:
        for fraction in (-0.03, 0.0):
            with self.subTest(fraction=fraction), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = FinalV27CumulativeFixture(
                    V26Fixture(Path(directory)),
                    cumulative_fraction=fraction,
                    classification="screened_out",
                    promotion_eligible=False,
                    promotion_reason="cumulative_screened_out")
                fixture.write_ledger(promotion_eligible=False,
                                     promotion_reason="cumulative_screened_out")
                row = self._projected(fixture)
                self.assertIs(row["available"], True)
                self.assertIs(row["trusted"], True)
                self.assertIsNone(row["receipt_error"])
                self.assertEqual(row["headline"], {
                    "classification": "screened_out",
                    "positive": False,
                    "label": ("cumulative candidate is not faster than frozen "
                              "production — promotion denied (valid "
                              "nonpositive result)"),
                })
                self.assertEqual(
                    row["receipt"]["cumulative_graphs_on_effect_fraction"],
                    fraction)
                self.assertIs(row["receipt"]["promotion_eligible"], False)
                self.assertEqual(row["receipt"]["promotion_reason"],
                                 "cumulative_screened_out")
                self.assertEqual(row["journal"]["integrity"], "matched")
                self.assertIs(row["ledger"]["agrees"], True)

    def test_producer_owned_promotion_fields_pass_through_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = FinalV27CumulativeFixture(
                V26Fixture(Path(directory)),
                promotion_eligible=False,
                promotion_reason="cumulative_screened_out")
            row = self._projected(fixture)
            self.assertIs(row["receipt"]["promotion_eligible"], False)
            self.assertEqual(row["receipt"]["promotion_reason"],
                             "cumulative_screened_out")
            self.assertNotIn("promotion_eligible", row)
            self.assertNotIn("eligible", row)
            self.assertNotIn("promotion_reason", row)
            encoded = json.dumps(row, sort_keys=True)
            self.assertNotIn('"eligible"', encoded)
            self.assertEqual(encoded.count('"promotion_eligible"'), 1)
            self.assertIs(row["ledger"]["agrees"], None)

    def test_journal_mismatch_marks_row_untrusted_but_never_hides_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = FinalV27CumulativeFixture(V26Fixture(Path(directory)))
            self.assertEqual(
                self._projected(fixture)["journal"]["integrity"], "matched")
            tampered = copy.deepcopy(fixture.cumulative)
            tampered["cumulative_graphs_on_effect_fraction"] = -0.05
            fixture._write_sealed(fixture.performance_path, tampered,
                                  "result_sha256")
            row = self._projected(fixture)
            self.assertIs(row["available"], True)
            self.assertIs(row["trusted"], False)
            self.assertEqual(row["journal"]["integrity"], "mismatched")
            self.assertIn("disagrees", row["journal"]["detail"])
            self.assertEqual(
                row["receipt"]["cumulative_graphs_on_effect_fraction"], -0.05)
            self.assertIs(row["receipt"]["valid"], True)

    def test_journal_absent_marks_row_untrusted_but_never_hides_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = FinalV27CumulativeFixture(V26Fixture(Path(directory)))
            (fixture.operation / "composition-authority.jsonl").unlink()
            row = self._projected(fixture)
            self.assertIs(row["available"], True)
            self.assertIs(row["trusted"], False)
            self.assertEqual(row["journal"]["integrity"], "absent")
            self.assertIs(row["journal"]["present"], False)
            self.assertEqual(row["receipt"]["cumulative_classification"],
                             "candidate")
            self.assertIs(row["receipt"]["valid"], True)

    def test_missing_data_behaviors_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            absent = server._v27_cumulative_projection(root)
            self.assertIs(absent["available"], False)
            self.assertIs(absent["trusted"], False)
            self.assertIn("no cumulative performance operation",
                          absent["error"])
            fixture = V26Fixture(root)
            row = server._v27_cumulative_projection(root)
            self.assertIs(row["available"], False)
            self.assertIn("no cumulative performance operation", row["error"])
            FinalV27CumulativeFixture(fixture, sealed=False)
            row = server._v27_cumulative_projection(root)
            self.assertIs(row["available"], True)
            self.assertIs(row["trusted"], False)
            self.assertIsNone(row["receipt"])
            self.assertIn("absent or unreadable", row["receipt_error"])
            self.assertIsNone(row["headline"])
            self.assertEqual(row["journal"]["integrity"], "incomplete")
            self.assertIs(row["journal"]["pre_run"], True)
            self.assertIs(row["journal"]["result"], False)

    def test_ledger_disagreement_marks_row_untrusted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = FinalV27CumulativeFixture(V26Fixture(Path(directory)))
            fixture.write_ledger(
                promotion_eligible=False,
                promotion_reason="cumulative_screened_out",
                cumulative_performance_result_sha256="0" * 64)
            row = self._projected(fixture)
            self.assertIs(row["trusted"], False)
            self.assertIs(row["ledger"]["agrees"], False)
            self.assertEqual(row["journal"]["integrity"], "matched")
            self.assertIs(row["receipt"]["promotion_eligible"], True)

    def test_selection_prefers_the_newest_sealed_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V26Fixture(Path(directory))
            older = FinalV27CumulativeFixture(fixture)
            newer = FinalV27CumulativeFixture(fixture, operation_key="b" * 64)
            older_stamp = older.performance_path.stat().st_mtime
            os.utime(newer.performance_path,
                     (older_stamp + 10.0, older_stamp + 10.0))
            row = server._v27_cumulative_projection(fixture.bundle.parent)
            self.assertIs(row["available"], True)
            self.assertEqual(row["operation_key"], "b" * 64)
            self.assertIs(row["trusted"], True)
            in_flight = FinalV27CumulativeFixture(
                fixture, operation_key="c" * 64, sealed=False)
            os.utime(in_flight.operation / "runner-plan.json",
                     (older_stamp + 20.0, older_stamp + 20.0))
            row = server._v27_cumulative_projection(fixture.bundle.parent)
            self.assertEqual(row["operation_key"], "b" * 64)
            self.assertIs(row["trusted"], True)

    def test_live_payload_carries_the_v27_cumulative_headline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = V26Fixture(root)
            cumulative = FinalV27CumulativeFixture(fixture)
            cumulative.write_ledger(
                promotion_eligible=True,
                promotion_reason="incremental_and_cumulative_positive")
            state, _ = fixture.checkpoint()
            (fixture.state / "state.json").write_bytes(
                server._canonical_json_bytes(state) + b"\n")
            fixture.write_journal([(
                "discovery_preauthored_checkpointed", state["state_sha256"])])
            with mock.patch.object(
                    server, "AUTOKERNEL_DEPLOYMENTS_ROOT", root), \
                    _frozen(fixture), \
                    mock.patch.object(
                        server, "_discovery_lock_held", return_value=True):
                payload, _ = server._discovery_live_read()
            self.assertIs(payload["available"], True)
            v27 = payload["v27_cumulative"]
            self.assertIs(v27["available"], True)
            self.assertIs(v27["trusted"], True)
            self.assertEqual(v27["deployment"], fixture.bundle.name)
            self.assertEqual(v27["operation_key"], "a" * 64)
            self.assertIs(v27["headline"]["positive"], True)
            self.assertEqual(v27["receipt"]["cumulative_classification"],
                             "candidate")
            self.assertEqual(v27["receipt"]["cumulative_graphs_on_effect_fraction"],
                             0.04)
            self.assertIs(v27["receipt"]["promotion_eligible"], True)
            self.assertIs(v27["ledger"]["agrees"], True)
            encoded = json.dumps(payload, sort_keys=True)
            self.assertIn("cumulative_graphs_on_effect_fraction", encoded)
            for forbidden in ("source_backed_base64", "patch_base64"):
                self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
