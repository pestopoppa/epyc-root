from __future__ import annotations

import copy
import base64
import hashlib
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from dashboard import server
from tests.test_dashboard_autokernel_v26 import V26Fixture, _seal


def _q5_erratum() -> dict:
    return json.loads((
        Path(__file__).parent / "fixtures" / "dashboard_autokernel_v27" /
        "q5_lds0_attribution_erratum_v1.json").read_text(encoding="utf-8"))


def _carry_forward(erratum: dict) -> dict:
    digest = lambda label: hashlib.sha256(label.encode()).hexdigest()
    value = {
        "schema": "epyc.autokernel.discovery_carry_forward.v2",
        **server._DISCOVERY_V27_PREDECESSOR,
        "portfolio_outcomes": copy.deepcopy(
            server._DISCOVERY_V27_CARRY_OUTCOMES),
        "candidate_semantic_sha256": sorted({
            *(digest(f"semantic-{index}") for index in range(12)),
            erratum["candidate_semantic_sha256"]}),
        "candidate_patch_sha256": sorted({
            *(digest(f"patch-{index}") for index in range(7)),
            erratum["candidate_patch_sha256"]}),
        "cross_campaign_candidate_sha256": sorted({
            *(digest(f"cross-{index}") for index in range(7)),
            erratum["cross_campaign_candidate_sha256"]}),
        "attribution_expectation_erratum": copy.deepcopy(erratum),
    }
    return _seal(value, "carry_forward_sha256")


def _build_identity(commit: str, prefix: str) -> dict:
    return {
        "source_commit": commit,
        "source_sha256": prefix * 64,
        "binary_sha256": chr(ord(prefix) + 1) * 64,
        "hip_library_sha256": chr(ord(prefix) + 2) * 64,
        "config_sha256": chr(ord(prefix) + 3) * 64,
        "linkage_sha256": chr(ord(prefix) + 4) * 64,
    }


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _composition_authority(
        *, accepted: list[dict], campaign_id: str,
        production_base_commit: str, instrument_commit: str) -> dict:
    patch_set = server._discovery_content_hash({
        "schema": "epyc.autokernel.ordered_patch_set.v1",
        "campaign_id": campaign_id,
        "production_base_commit": production_base_commit,
        "instrument_commit": instrument_commit,
        "lever_sha256s": [row["lever_sha256"] for row in accepted],
        "source_manifest_sha256s": [
            row["manifest_sha256"] for row in accepted],
    })
    return _seal({
        "schema": "epyc.autokernel.cumulative_composition_authority.v1",
        "campaign_id": campaign_id,
        "production_base_commit": production_base_commit,
        "instrument_commit": instrument_commit,
        "ordered_patch_set_sha256": patch_set,
        "accepted": copy.deepcopy(accepted),
    }, "authority_sha256")


def _composition_plan() -> dict:
    campaign_id = "ak-dashboard-v27-test"
    production_base_commit = server._DISCOVERY_V27_PRODUCTION_COMMIT
    instrument_commit = "e" * 40
    patch = (
        b"diff --git a/src/test.cpp b/src/test.cpp\n"
        b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
        b"@@ -1 +1 @@\n-int test() { return 0; }\n"
        b"+int test() { return 1; }\n")
    manifest = {
        "schema": "epyc.autokernel.source-patch.v1",
        "campaign_id": campaign_id,
        "proposal_id": "akp-dashboard-v27-test",
        "candidate_id": "akc-dashboard-v27-test",
        "source_tree": "llama.cpp",
        "production_base_commit": production_base_commit,
        "instrument_commit": instrument_commit,
        "change_class": "arithmetic",
        "declared_files": ["src/test.cpp"],
        "declared_symbols": {"src/test.cpp": ["<file-scope>"]},
        "mechanism_id": "dashboard-v27-test",
        "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "patch_encoding": "base64",
        "patch_base64": base64.b64encode(patch).decode("ascii"),
    }
    manifest_sha256 = server._discovery_content_hash(manifest)
    replications = [{
        "result_sha256": _digest(f"isolated-result-{index}"),
        "series_key": _digest("isolated-series"),
        "build_identity_sha256": _digest("isolated-build"),
        "correctness_receipt_sha256": _digest(
            f"isolated-correctness-{index}"),
        "attribution_receipt_sha256": _digest(
            f"isolated-attribution-{index}"),
        "graphs_off_receipt_sha256": _digest(
            f"isolated-graphs-off-{index}"),
        "graphs_on_receipt_sha256": _digest(
            f"isolated-graphs-on-{index}"),
        "effect_fraction": .01 + index / 100,
    } for index in range(2)]
    lever = _seal({
        "schema": "epyc.autokernel.replicated_positive_lever.v2",
        "hypothesis_id": "akh-dashboard-v27-test",
        "cross_campaign_candidate_sha256": _digest("cross-campaign"),
        "manifest": manifest,
        "manifest_sha256": manifest_sha256,
        "isolated_disposition": "top_k_replicated_candidate",
        "replications": replications,
    }, "lever_sha256")
    anchor = _composition_authority(
        accepted=[], campaign_id=campaign_id,
        production_base_commit=production_base_commit,
        instrument_commit=instrument_commit)
    candidate = _composition_authority(
        accepted=[lever], campaign_id=campaign_id,
        production_base_commit=production_base_commit,
        instrument_commit=instrument_commit)
    dnr = _seal({
        "schema": "epyc.autokernel.composition_dnr.v1",
        "campaign_id": campaign_id,
        "anchor_patch_set_sha256": anchor["ordered_patch_set_sha256"],
        "candidate_patch_set_sha256": candidate[
            "ordered_patch_set_sha256"],
        "proposed_cross_campaign_candidate_sha256": lever[
            "cross_campaign_candidate_sha256"],
        "registry_sha256": _digest("registry"),
        "checked_cross_campaign_candidate_sha256s": [],
        "outcome": "PASS",
    }, "receipt_sha256")
    body = {
        "schema": "epyc.autokernel.cumulative_composition_plan.v1",
        "attempt_id": _digest("attempt"),
        "anchor_authority": anchor,
        "candidate_authority": candidate,
        "anchor_patch_set_sha256": anchor["ordered_patch_set_sha256"],
        "candidate_patch_set_sha256": candidate[
            "ordered_patch_set_sha256"],
        "ordered_component_lever_sha256s": [lever["lever_sha256"]],
        "ordered_source_manifest_sha256s": [manifest_sha256],
        "new_lever_sha256": lever["lever_sha256"],
        "isolated_result_sha256s": [
            row["result_sha256"] for row in replications],
        "dnr": dnr,
    }
    operation_key = server._discovery_content_hash({
        "schema": "epyc.autokernel.composition_operation.v1",
        "attempt_id": body["attempt_id"],
        "plan_body_sha256": server._discovery_content_hash(body),
    })
    return {
        **body, "operation_key": operation_key,
        "plan_sha256": server._discovery_content_hash({
            **body, "operation_key": operation_key}),
    }


def _full_correctness(pair: dict) -> dict:
    return _seal({
        "schema": "epyc.autokernel.composition_full_correctness.v1",
        "operation_key": pair["operation_key"],
        "build_pair_sha256": pair["pair_sha256"],
        "candidate_build_identity_sha256": pair["candidate"][
            "build_identity_sha256"],
        "suite_id": "dashboard-v27-current-full-suite",
        "cases_sha256": _digest("full-suite-cases"),
        "receipt_sha256": _digest("full-suite-receipt"),
        "passed": True,
        "current_full_suite": True,
    }, "result_sha256")


def _incremental_comparison(
        pair: dict, correctness: dict, effect: float) -> dict:
    effects = (effect, effect, effect)
    classification = (
        "candidate" if all(value > 0 for value in effects)
        else "screened_out" if all(value <= 0 for value in effects)
        else "inconclusive")
    return _seal({
        "schema": "epyc.autokernel.incremental_composition_comparison.v2",
        "operation_key": pair["operation_key"],
        "build_pair_sha256": pair["pair_sha256"],
        "correctness_result_sha256": correctness["result_sha256"],
        "exact_route_receipt_sha256": _digest("incremental-exact-route"),
        "expected_route_set_sha256": _digest("expected-route-set"),
        "graphs_off_receipt_sha256": "d" * 64,
        "graphs_on_receipt_sha256": "e" * 64,
        "target_runtime_frame_sha256": _digest("target-runtime-frame"),
        "exact_route_effect_fraction": effect,
        "graphs_off_effect_fraction": effect,
        "graphs_on_effect_fraction": effect,
        "classification": classification,
        "exact_route_executed": True,
        "graphs_off_executed": True,
        "graphs_on_executed": True,
    }, "result_sha256")


def _reseal_plan(plan: dict) -> None:
    body = {
        key: value for key, value in plan.items()
        if key not in {"operation_key", "plan_sha256"}}
    plan["operation_key"] = server._discovery_content_hash({
        "schema": "epyc.autokernel.composition_operation.v1",
        "attempt_id": plan["attempt_id"],
        "plan_body_sha256": server._discovery_content_hash(body),
    })
    plan["plan_sha256"] = server._discovery_content_hash({
        **body, "operation_key": plan["operation_key"]})


def _reseal_plan_authorities(
        plan: dict, *, anchor_levers: list[dict],
        candidate_levers: list[dict]) -> None:
    anchor_template = plan["anchor_authority"]
    candidate_template = plan["candidate_authority"]
    anchor = _composition_authority(
        accepted=anchor_levers,
        campaign_id=anchor_template["campaign_id"],
        production_base_commit=anchor_template["production_base_commit"],
        instrument_commit=anchor_template["instrument_commit"])
    candidate = _composition_authority(
        accepted=candidate_levers,
        campaign_id=candidate_template["campaign_id"],
        production_base_commit=candidate_template["production_base_commit"],
        instrument_commit=candidate_template["instrument_commit"])
    newest = candidate_levers[-1]
    plan.update({
        "anchor_authority": anchor,
        "candidate_authority": candidate,
        "anchor_patch_set_sha256": anchor["ordered_patch_set_sha256"],
        "candidate_patch_set_sha256": candidate[
            "ordered_patch_set_sha256"],
        "ordered_component_lever_sha256s": [
            row["lever_sha256"] for row in candidate_levers],
        "ordered_source_manifest_sha256s": [
            row["manifest_sha256"] for row in candidate_levers],
        "new_lever_sha256": newest["lever_sha256"],
        "isolated_result_sha256s": [
            row["result_sha256"] for row in newest["replications"]],
    })
    plan["dnr"].update({
        "campaign_id": anchor["campaign_id"],
        "anchor_patch_set_sha256": anchor["ordered_patch_set_sha256"],
        "candidate_patch_set_sha256": candidate[
            "ordered_patch_set_sha256"],
        "proposed_cross_campaign_candidate_sha256": newest[
            "cross_campaign_candidate_sha256"],
        "checked_cross_campaign_candidate_sha256s": sorted({
            row["cross_campaign_candidate_sha256"]
            for row in anchor_levers}),
    })
    plan["dnr"] = _seal(plan["dnr"], "receipt_sha256")
    _reseal_plan(plan)


def _rebind_plan_evidence(terminal: dict, receipt: dict) -> None:
    plan = terminal["plan"]
    newest = plan["candidate_authority"]["accepted"][-1]
    terminal.update({
        "lever_sha256": newest["lever_sha256"],
        "cross_campaign_candidate_sha256": newest[
            "cross_campaign_candidate_sha256"],
        "isolated_result_sha256s": [
            row["result_sha256"] for row in newest["replications"]],
        "admitted_authority_sha256": plan["candidate_authority"][
            "authority_sha256"],
    })
    terminal["build_pair"]["anchor"]["patch_set_sha256"] = plan[
        "anchor_patch_set_sha256"]
    terminal["build_pair"]["candidate"]["patch_set_sha256"] = plan[
        "candidate_patch_set_sha256"]
    receipt.update({
        "accepted_authority_sha256": plan["candidate_authority"][
            "authority_sha256"],
        "accepted_patch_set_sha256": plan["candidate_patch_set_sha256"],
    })
    _rebind_terminal_nested(terminal, receipt)


def _rebind_terminal_nested(terminal: dict, receipt: dict) -> None:
    plan = terminal["plan"]
    pair = terminal["build_pair"]
    correctness = terminal["correctness"]
    comparison = terminal["comparison"]
    terminal["operation_key"] = plan["operation_key"]
    terminal["plan_sha256"] = plan["plan_sha256"]
    pair["operation_key"] = plan["operation_key"]
    pair["plan_sha256"] = plan["plan_sha256"]
    pair.update(_seal(pair, "pair_sha256"))
    correctness["operation_key"] = pair["operation_key"]
    correctness["build_pair_sha256"] = pair["pair_sha256"]
    correctness.update(_seal(correctness, "result_sha256"))
    comparison["operation_key"] = pair["operation_key"]
    comparison["build_pair_sha256"] = pair["pair_sha256"]
    comparison["correctness_result_sha256"] = correctness["result_sha256"]
    comparison.update(_seal(comparison, "result_sha256"))
    terminal["correctness_result_sha256"] = correctness["result_sha256"]
    terminal["comparison_result_sha256"] = comparison["result_sha256"]
    receipt.update({
        "operation_key": plan["operation_key"],
        "plan_sha256": plan["plan_sha256"],
        "build_pair_sha256": pair["pair_sha256"],
        "correctness_result_sha256": correctness["result_sha256"],
        "incremental_comparison_result_sha256": comparison["result_sha256"],
    })


def _reseal_cumulative_state(
        state: dict, receipt: dict, path: Path) -> dict:
    terminal = state["cumulative_composition_terminal"]
    core_sha256 = server._discovery_content_hash({
        key: value for key, value in terminal.items()
        if key not in server._DISCOVERY_V27_TERMINAL_CORE_EXCLUDED})
    receipt["composition_terminal_sha256"] = core_sha256
    receipt = _seal(receipt, "result_sha256")
    raw = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
    path.write_bytes(raw)
    binding = {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
    terminal["cumulative_performance"] = copy.deepcopy(receipt)
    terminal["cumulative_performance_ref"] = {
        "schema": "epyc.autokernel.cumulative_performance_ref.v1",
        **binding,
    }
    terminal["cumulative_performance_result_sha256"] = receipt[
        "result_sha256"]
    terminal["terminal_sha256"] = core_sha256
    state["cumulative_performance"] = binding
    state["cumulative_composition_terminal"] = terminal
    return _seal(state, "state_sha256")


def _frozen_comparator(
        model_sha256: str, workload_sha256: str,
        runtime_config_sha256: str) -> dict:
    build_identity = _build_identity(
        server._DISCOVERY_V27_PRODUCTION_COMMIT, "1")
    measured = server._discovery_v27_measurement_binding(
        model_sha256=model_sha256,
        build_identity=build_identity, graphs_mode="on", arm="anchor",
        factor_name="cumulative_production")
    assert measured is not None
    value = {
        "schema": "epyc.autokernel.frozen_production_comparator.v2",
        "branch": "production-consolidated-v9",
        "commit": server._DISCOVERY_V27_PRODUCTION_COMMIT,
        "build_identity": build_identity,
        "build_receipt_sha256": "6" * 64,
        "linkage_receipt_sha256": "7" * 64,
        "runtime_receipt_sha256": "8" * 64,
        "runtime_snapshot_sha256": "c" * 64,
        "measurement_receipt_sha256": "9" * 64,
        "model_sha256": model_sha256,
        "workload_sha256": workload_sha256,
        "runtime_config_sha256": runtime_config_sha256,
        "observed_workload_sha256": server._discovery_content_hash(
            server._DISCOVERY_V27_MEASURED_WORKLOAD),
        "observed_runtime_config_sha256": server._discovery_content_hash(
            server._DISCOVERY_V27_MEASURED_RUNTIME),
        "frame_sha256": measured[1],
        "graphs_mode": "graphs_on",
        "metric": "tokens_per_second",
        "direction": "higher_is_better",
        "measurement_protocol_sha256": measured[0],
    }
    return _seal(value, "receipt_sha256")


class V27Fixture(V26Fixture):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.erratum = _q5_erratum()
        erratum_path = self.inputs / "q5-lds0-attribution-erratum-v1.json"
        raw = ((Path(__file__).parent / "fixtures" /
                "dashboard_autokernel_v27" /
                "q5_lds0_attribution_erratum_v1.json").read_bytes())
        erratum_path.write_bytes(raw)
        erratum_input = {
            "path": str(erratum_path),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        self.input_rows["q5_lds0_attribution_erratum"] = erratum_input
        self.carry = _carry_forward(self.erratum)
        carry_path = self.inputs / "carry-forward-v2.json"
        carry_raw = (json.dumps(self.carry, sort_keys=True, indent=2) +
                     "\n").encode()
        carry_path.write_bytes(carry_raw)
        self.input_rows["carry_forward"] = {
            "path": str(carry_path),
            "sha256": hashlib.sha256(carry_raw).hexdigest(),
        }
        self.comparator = _frozen_comparator(
            self.input_rows["model"]["sha256"],
            self.input_rows["workload"]["sha256"],
            self.input_rows["runtime_config"]["sha256"])
        comparator_path = self.inputs / "frozen-production-comparator.json"
        comparator_raw = (json.dumps(
            self.comparator, sort_keys=True, indent=2) + "\n").encode()
        comparator_path.write_bytes(comparator_raw)
        self.input_rows["frozen_production_comparator"] = {
            "path": str(comparator_path),
            "sha256": hashlib.sha256(comparator_raw).hexdigest(),
        }
        self.config["schema"] = "epyc.autokernel.discovery_deployment.v6"
        self.config["production"] = {
            "path": "/mnt/raid0/llm/llama.cpp",
            "branch": "production-consolidated-v9",
            "head": server._DISCOVERY_V27_PRODUCTION_COMMIT,
        }
        self.config["instrument"]["production_ancestor"] = (
            server._DISCOVERY_V27_PRODUCTION_COMMIT)
        self.config["immutable_inputs"] = self.input_rows
        self.graph["schema"] = "epyc.autokernel.static_discovery_graph.v9"
        self.graph["carry_forward_sha256"] = self.carry[
            "carry_forward_sha256"]
        self.graph["attribution_expectation_erratum"] = {
            "schema":
                "epyc.autokernel.attribution_expectation_erratum_source.v1",
            "erratum_schema": self.erratum["schema"],
            "erratum_sha256": self.erratum["erratum_sha256"],
            "file_sha256": erratum_input["sha256"],
            "operation_key": self.erratum["operation_key"],
            "attribution_refusal_file_sha256":
                self.erratum["attribution_refusal_file_sha256"],
            "candidate_semantic_sha256":
                self.erratum["candidate_semantic_sha256"],
        }
        self.graph["frozen_production_comparator"] = {
            "schema":
                "epyc.autokernel.frozen_production_comparator_source.v1",
            "file_sha256": self.input_rows[
                "frozen_production_comparator"]["sha256"],
            "receipt_sha256": self.comparator["receipt_sha256"],
        }
        self.write()

    def checkpoint(self) -> tuple[dict, dict]:
        state, authority = super().checkpoint()
        state["carry_forward_sha256"] = self.carry["carry_forward_sha256"]
        return _seal(state, "state_sha256"), authority

    def cumulative_state(
            self, *, cumulative: float = .05, incremental: float = .01,
            disposition: str = "admitted",
            frame_mismatch: bool = False,
            protocol_mismatch: bool = False,
            candidate_frame_substitution: bool = False,
            candidate_off_frame_substitution: bool = False,
            production_graphs_mode: str = "on",
            runtime_config_mismatch: bool = False,
            measurement_receipt_alias: bool = False,
        promotion_eligible_override: bool | None = None,
    ) -> tuple[dict, dict, Path]:
        state, _ = self.checkpoint()
        plan = _composition_plan()
        operation_key = plan["operation_key"]
        plan_sha256 = plan["plan_sha256"]
        anchor_identity = _build_identity("e" * 40, "1")
        candidate_identity = _build_identity("f" * 40, "a")
        def build_binding(identity: dict, patch_sha256: str) -> dict:
            return {
                "patch_set_sha256": patch_sha256,
                "source_materialization_receipt_sha256": "4" * 64,
                "build_identity": identity,
                "build_identity_sha256":
                    server._discovery_content_hash(identity),
            }
        anchor = build_binding(
            anchor_identity, plan["anchor_patch_set_sha256"])
        candidate = build_binding(
            candidate_identity, plan["candidate_patch_set_sha256"])
        build_pair = _seal({
            "schema": "epyc.autokernel.cumulative_build_pair.v1",
            "operation_key": operation_key, "plan_sha256": plan_sha256,
            "anchor": anchor, "candidate": candidate,
        }, "pair_sha256")
        incremental_values = (incremental, incremental, incremental)
        incremental_class = (
            "candidate" if all(value > 0 for value in incremental_values)
            else "screened_out"
            if all(value <= 0 for value in incremental_values)
            else "inconclusive")
        cumulative_class = "candidate" if cumulative > 0 else "screened_out"
        eligible = (
            incremental_class == "candidate"
            and cumulative_class == "candidate")
        reason = (
            "incremental_and_cumulative_positive" if eligible
            else f"incremental_{incremental_class}"
            if incremental_class != "candidate"
            else f"cumulative_{cumulative_class}")
        claimed_eligible = (
            eligible if promotion_eligible_override is None
            else promotion_eligible_override)
        claimed_reason = (
            reason if promotion_eligible_override is None
            else "cumulative_screened_out")
        correctness = _full_correctness(build_pair)
        comparison = _incremental_comparison(
            build_pair, correctness, incremental)
        lever = plan["candidate_authority"]["accepted"][-1]
        terminal = {
            "schema": "epyc.autokernel.cumulative_composition_terminal.v3",
            "operation_key": operation_key, "plan_sha256": plan_sha256,
            "plan": plan,
            "lever_sha256": lever["lever_sha256"],
            "cross_campaign_candidate_sha256": lever[
                "cross_campaign_candidate_sha256"],
            "isolated_result_sha256s": [
                row["result_sha256"] for row in lever["replications"]],
            "disposition": disposition, "scientific_budget_spent": True,
            "build_pair": build_pair, "correctness": correctness,
            "comparison": comparison, "cumulative_performance": None,
            "cumulative_performance_ref": None,
            "correctness_result_sha256": correctness["result_sha256"],
            "comparison_result_sha256": comparison["result_sha256"],
            "cumulative_performance_result_sha256": None,
            "promotion_eligible": claimed_eligible,
            "promotion_reason": claimed_reason,
            "admitted_authority_sha256": (
                plan["candidate_authority"]["authority_sha256"]
                if disposition == "admitted" else None),
            "reason_code": (
                "incremental_admitted_promotion_eligible"
                if disposition == "admitted" and claimed_eligible else
                "incremental_admitted_" + claimed_reason
                if disposition == "admitted" else
                "incremental_" + incremental_class),
            "infrastructure_receipt_sha256": None,
            "attribution_receipt_sha256": None,
            "terminal_sha256": None,
        }
        core_sha256 = server._discovery_content_hash({
            key: value for key, value in terminal.items()
            if key not in server._DISCOVERY_V27_TERMINAL_CORE_EXCLUDED})
        frozen_body = {
            "schema": "epyc.autokernel.frozen_production_authority.v2",
            "production_commit": server._DISCOVERY_V27_PRODUCTION_COMMIT,
            "build_identity": copy.deepcopy(
                self.comparator["build_identity"]),
            "build_identity_sha256": server._discovery_content_hash(
                self.comparator["build_identity"]),
            "runtime_snapshot_sha256":
                self.comparator["runtime_snapshot_sha256"],
            "comparator_receipt_sha256":
                self.comparator["receipt_sha256"],
            "graphs_mode": self.comparator["graphs_mode"],
            "frame_sha256": self.comparator["frame_sha256"],
            "measurement_protocol_sha256":
                self.comparator["measurement_protocol_sha256"],
            "measurement_receipt_sha256":
                self.comparator["measurement_receipt_sha256"],
            "model_sha256": self.comparator["model_sha256"],
            "workload_sha256": self.comparator["workload_sha256"],
            "runtime_config_sha256":
                self.comparator["runtime_config_sha256"],
            "observed_workload_sha256":
                self.comparator["observed_workload_sha256"],
            "observed_runtime_config_sha256":
                self.comparator["observed_runtime_config_sha256"],
            "metric": self.comparator["metric"],
            "direction": self.comparator["direction"],
        }
        frozen = {
            **frozen_body,
            "authority_sha256": server._discovery_content_hash(frozen_body)}
        off_binding = server._discovery_v27_measurement_binding(
            model_sha256=self.comparator["model_sha256"],
            build_identity=candidate_identity, graphs_mode="off",
            arm="candidate", factor_name="source_patch")
        on_binding = server._discovery_v27_measurement_binding(
            model_sha256=self.comparator["model_sha256"],
            build_identity=candidate_identity, graphs_mode="on",
            arm="candidate", factor_name="source_patch")
        assert off_binding is not None and on_binding is not None
        off_frame = (
            self.comparator["frame_sha256"]
            if candidate_off_frame_substitution else off_binding[1])
        on_frame = on_binding[1]
        production_frame = (
            on_frame if candidate_frame_substitution else "0" * 64
            if frame_mismatch else self.comparator["frame_sha256"])
        performance = _seal({
            "schema": server._DISCOVERY_V27_CUMULATIVE_SCHEMA,
            "authority": "frozen_production_promotion_gate",
            "promotion_authority": True,
            "operation_key": operation_key, "plan_sha256": plan_sha256,
            "accepted_authority_sha256": plan["candidate_authority"][
                "authority_sha256"],
            "accepted_patch_set_sha256": candidate["patch_set_sha256"],
            "build_pair_sha256": build_pair["pair_sha256"],
            "correctness_result_sha256": correctness["result_sha256"],
            "incremental_comparison_result_sha256":
                comparison["result_sha256"],
            "frozen_production": frozen,
            "model_sha256": self.comparator["model_sha256"],
            "workload_sha256": self.comparator["workload_sha256"],
            "runtime_config_sha256":
                ("f" * 64 if runtime_config_mismatch else
                 self.comparator["runtime_config_sha256"]),
            "protocol_frame_sha256": (
                "0" * 64 if protocol_mismatch else
                self.comparator["measurement_protocol_sha256"]),
            "metric": "decode_tokens_per_s",
            "metric_direction": "higher_better",
            "incremental_exact_route_effect_fraction": incremental,
            "incremental_graphs_off_effect_fraction": incremental,
            "incremental_graphs_on_effect_fraction": incremental,
            "cumulative_graphs_on_effect_fraction": cumulative,
            "incremental_graphs_off_receipt_sha256": comparison[
                "graphs_off_receipt_sha256"],
            "incremental_graphs_on_receipt_sha256": comparison[
                "graphs_on_receipt_sha256"],
            "production_graphs_on_receipt_sha256": (
                "d" * 64 if measurement_receipt_alias else "0" * 64),
            "incremental_graphs_off_frame_sha256": off_frame,
            "incremental_graphs_on_frame_sha256": on_frame,
            "production_graphs_on_frame_sha256": production_frame,
            "production_graphs_mode": production_graphs_mode,
            "cumulative_classification": cumulative_class,
            "promotion_eligible": claimed_eligible,
            "promotion_reason": claimed_reason,
            "composition_terminal_sha256": core_sha256,
        }, "result_sha256")
        path = self.bundle / "evidence" / "cumulative-performance.json"
        raw = (json.dumps(performance, sort_keys=True, indent=2) + "\n").encode()
        path.write_bytes(raw)
        binding = {"path": str(path),
                   "sha256": hashlib.sha256(raw).hexdigest()}
        terminal["cumulative_performance"] = copy.deepcopy(performance)
        terminal["cumulative_performance_ref"] = {
            "schema": "epyc.autokernel.cumulative_performance_ref.v1",
            **binding}
        terminal["cumulative_performance_result_sha256"] = performance[
            "result_sha256"]
        terminal["terminal_sha256"] = core_sha256
        state["cumulative_performance"] = binding
        state["cumulative_composition_terminal"] = terminal
        return _seal(state, "state_sha256"), performance, path


    def postbuild_wait_state(self) -> dict:
        state, authority = self.checkpoint()
        operation_key = "a" * 64
        original_row = copy.deepcopy(state["pending"]["row"])
        original_row["operation_key"] = operation_key
        admitted = {
            "admitted": True, "operation_key": operation_key,
            "device_id": "mi210_0", "repetition": 1,
        }
        inflight = {
            "operation_key": operation_key,
            "row": original_row,
            "candidate": copy.deepcopy(state["pending"]["candidate"]),
            "authorization": {"claim": "candidate_only_discovery"},
            "lease": admitted,
            "confirmation": False,
            "parent_authorization": None,
            "infrastructure_retry_epoch": 0,
            "preauthored_continuation": authority,
        }
        operation_root = self.bundle / "operations" / operation_key
        waits = operation_root / "resource-waits"
        waits.mkdir(parents=True, mode=0o700)
        anchor_build = self.bundle / "build" / "anchor"
        candidate_build = self.bundle / "build" / "candidate"
        anchor_build.mkdir(mode=0o700)
        candidate_build.mkdir(mode=0o700)
        common_loader = self.bundle / "build" / "common-loader"
        anchor_loader = self.bundle / "build" / "anchor-loader"
        candidate_loader = self.bundle / "build" / "candidate-loader"
        for path in (common_loader, anchor_loader, candidate_loader):
            path.mkdir(mode=0o700)
        file_paths = {
            key: self.bundle / "build" / f"{key}.bin"
            for key in server._DISCOVERY_POSTBUILD_PATH_FIELDS - {
                "anchor_build", "candidate_build", "common_loader_dir",
                "anchor_loader_dir", "candidate_loader_dir"}}
        for key, path in file_paths.items():
            path.write_bytes(f"sealed-{key}\n".encode())
        identity = {
            "source_commit": "9" * 40,
            "source_sha256": "1" * 64,
            "binary_sha256": "2" * 64,
            "hip_library_sha256": "3" * 64,
            "config_sha256": "4" * 64,
            "linkage_sha256": "5" * 64,
        }
        anchor_identity = {**identity, "binary_sha256": "6" * 64}
        path_fields = {key: str(path) for key, path in file_paths.items()}
        path_fields.update(
            anchor_build=str(anchor_build), candidate_build=str(candidate_build),
            common_loader_dir=str(common_loader),
            anchor_loader_dir=str(anchor_loader),
            candidate_loader_dir=str(candidate_loader))
        scalar_fields = {
            key: hashlib.sha256(key.encode()).hexdigest()
            for key in server._DISCOVERY_POSTBUILD_SCALAR_FIELDS}
        scalar_fields.update(
            operation_key=operation_key, build_key="7" * 64,
            materialization_sha256="8" * 64)
        build = {
            "candidate_identity": identity,
            "anchor_identity": anchor_identity,
            **path_fields, **scalar_fields,
        }
        postbuild = _seal({
            "schema": "epyc.autokernel.gpu_source_postbuild_checkpoint.v1",
            "authority": "nonpromotable_candidate_only_discovery",
            "promotion_claim": False,
            "operation_key": operation_key,
            "manifest_sha256": "6" * 64,
            "build": build,
        }, "receipt_sha256")
        (operation_root / "postbuild-checkpoint.json").write_text(
            json.dumps(postbuild, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        def bound(role: str, path: Path) -> dict:
            return {"role": role, "path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

        correctness_binary = file_paths["candidate_correctness_binary"]
        measurement_binary = file_paths["measurement_binary"]
        exact = lambda signature: {
            "signature": signature, "kernel_pattern": "kernel_.*",
            "calls": 1, "grid": 64, "workgroup": 64,
            "lds_bytes": 0, "blocks_per_call": 1}
        policy = {
            "schema": "epyc.autokernel.gpu_source_execution_policy.v2",
            "manifest_sha256": "6" * 64,
            "model_sha256": self.input_rows["model"]["sha256"],
            "workload_sha256": self.input_rows["workload"]["sha256"],
            "runtime_config_sha256":
                self.input_rows["runtime_config"]["sha256"],
            "candidate_build_identity": identity,
            "anchor_build_identity": anchor_identity,
            "correctness_argv": [str(correctness_binary), "test"],
            "correctness_parser_id": "ak.t0.backend_ops_console/v1",
            "correctness_backend": "ROCm0", "correctness_op": "MUL_MAT",
            "expected_correctness_cases": 1,
            "correctness_invocations": [],
            "candidate_rocprof_argv": [str(measurement_binary), "-ngl", "99"],
            "anchor_rocprof_argv": [str(measurement_binary), "-ngl", "99"],
            "profiler_trace_schema_id": "rocprof-v3-kernel-trace-csv-v1",
            "expected_candidate_profiler_dispatch_rows": 1,
            "expected_anchor_profiler_dispatch_rows": 1,
            "profiler_transport_policy": "require-zero-exit-v1",
            "attribution_arm_order_seed_sha256": "c" * 64,
            "attribution_arm_order": ["candidate", "anchor"],
            "correctness_inputs": [bound("executable", correctness_binary)],
            "candidate_rocprof_inputs": [
                bound("executable", measurement_binary)],
            "anchor_rocprof_inputs": [bound("executable", measurement_binary)],
            "required_correctness_argv_paths": [str(correctness_binary)],
            "required_candidate_rocprof_argv_paths": [str(measurement_binary)],
            "required_anchor_rocprof_argv_paths": [str(measurement_binary)],
            "execution_cwd": str(self.bundle),
            "correctness_environment": [["LD_LIBRARY_PATH", str(common_loader)]],
            "candidate_rocprof_environment": [
                ["LD_LIBRARY_PATH", str(candidate_loader)]],
            "anchor_rocprof_environment": [
                ["LD_LIBRARY_PATH", str(anchor_loader)]],
            "shared_runtime": None,
            "dispatch": {
                "candidate_exact": [exact("candidate.reward")],
                "anchor_exact": [exact("anchor.reward")],
                "candidate_structural_exact": [],
                "anchor_structural_exact": [],
                "candidate_forbidden": [], "anchor_forbidden": [],
                "invariants": [],
            },
        }
        (operation_root / "evidence-policy.json").write_text(
            json.dumps(policy, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        contention = {
            "admitted": False,
            "phase": "pre_executor_reservation",
            "reason": "foreign_kfd_busy",
            "device_id": "mi210_0",
            "operation_key": operation_key,
            "promotion_claim": False,
            "foreign_kfd_pids": [4242],
        }
        wait_body = _seal({
            "schema": "epyc.autokernel.gpu_source_resource_wait.v1",
            "authority": "nonpromotable_candidate_only_discovery",
            "promotion_claim": False,
            "operation_key": operation_key,
            "manifest_sha256": "6" * 64,
            "gpu_executor_started": False,
            "proof_root_created": False,
            "runner_plan_created": False,
            "runner_output_created": False,
            "build_key": "7" * 64,
            "materialization_sha256": "8" * 64,
            "contention": contention,
        }, "receipt_sha256")
        wait_path = waits / "wait-0001.json"
        wait_path.write_text(
            json.dumps(wait_body, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")
        wait = {
            **contention,
            "stage_receipt_path": str(wait_path),
            "stage_receipt_sha256":
                hashlib.sha256(wait_path.read_bytes()).hexdigest(),
        }
        checkpoint = _seal({
            "schema":
                "epyc.autokernel.controller_resource_wait_checkpoint.v1",
            "authority": "nonpromotable_candidate_only_discovery",
            "promotion_claim": False,
            "operation_key": operation_key,
            "inflight": inflight,
            "inflight_sha256":
                server._discovery_controller_state_hash(inflight),
            "wait_receipt": wait,
            "wait_receipt_sha256":
                server._discovery_controller_state_hash(wait),
            "resume_permit": {**admitted, **wait},
        }, "checkpoint_sha256")
        waiting_row = {**original_row, "status": "waiting_resource",
                       "lease": wait}
        state["pending"] = {
            "row": waiting_row,
            "candidate": inflight["candidate"],
            "authorization": inflight["authorization"],
            "confirmation": False,
            "parent_authorization": None,
            "infrastructure_retry_epoch": 0,
            "preauthored_continuation": authority,
            "resource_wait": checkpoint,
        }
        return _seal(state, "state_sha256")


def _frozen(fixture: V27Fixture) -> ExitStack:
    stack = ExitStack()
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V27_EXECUTION_MODULE_SHA256",
        {role: row["sha256"] for role, row in fixture.modules.items()}))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V27_PRODUCER_COMMIT", "a" * 40))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V27_DEPLOYMENT_SEMANTIC_SHA256",
        fixture.config["config_sha256"]))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V27_DEPLOYMENT_FILE_SHA256",
        hashlib.sha256(fixture.config_path.read_bytes()).hexdigest()))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V27_GRAPH_SHA256",
        fixture.graph["graph_sha256"]))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V27_GRAPH_FILE_SHA256",
        hashlib.sha256(
            (fixture.state / "deployment-graph.json").read_bytes()).hexdigest()))
    return stack


class DashboardAutokernelV27Tests(unittest.TestCase):
    def test_deployment_and_measured_hash_namespaces_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            self.assertEqual(
                contract["deployment_workload_file_sha256"],
                fixture.input_rows["workload"]["sha256"])
            self.assertEqual(
                contract["deployment_runtime_file_sha256"],
                fixture.input_rows["runtime_config"]["sha256"])
            self.assertNotEqual(
                contract["deployment_workload_file_sha256"],
                server._discovery_content_hash(
                    server._DISCOVERY_V27_MEASURED_WORKLOAD))
            self.assertNotEqual(
                contract["deployment_runtime_file_sha256"],
                server._discovery_content_hash(
                    server._DISCOVERY_V27_MEASURED_RUNTIME))

    def test_coherently_resealed_static_observed_runtime_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            comparator = copy.deepcopy(fixture.comparator)
            runtime = copy.deepcopy(server._DISCOVERY_V27_MEASURED_RUNTIME)
            runtime["n_threads"] = 9
            protocol = {
                **server._DISCOVERY_V27_MEASURED_WORKLOAD,
                "model_sha256": fixture.input_rows["model"]["sha256"],
                "metric": "decode_tokens_per_s",
                "metric_direction": "higher_better",
                "cpu_list": "184-191", "device": "AMD Instinct MI210",
                "architecture": "gfx90a",
                "runtime_config_sha256":
                    server._discovery_content_hash(runtime),
                "graphs_mode": "on", "candidate_invocations": 9,
                "candidate_processes": 1,
            }
            comparator["measurement_protocol_sha256"] = (
                server._discovery_content_hash(protocol))
            comparator["observed_runtime_config_sha256"] = (
                server._discovery_content_hash(runtime))
            comparator["frame_sha256"] = server._discovery_content_hash({
                "schema": "epyc.autokernel.measurement_arm_frame.v1",
                "arm": "anchor", "protocol": protocol,
                "source_commit": comparator["build_identity"][
                    "source_commit"],
                "build_identity": comparator["build_identity"],
                "factor_name": "cumulative_production",
            })
            comparator = _seal(comparator, "receipt_sha256")
            self.assertFalse(server._discovery_v27_frozen_comparator(
                comparator,
                model_sha256=fixture.input_rows["model"]["sha256"],
                workload_sha256=fixture.input_rows["workload"]["sha256"],
                runtime_config_sha256=
                    fixture.input_rows["runtime_config"]["sha256"]))

    def test_coherently_resealed_dynamic_observed_runtime_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, receipt, path = fixture.cumulative_state()
            terminal = state["cumulative_composition_terminal"]
            candidate_identity = terminal["build_pair"]["candidate"][
                "build_identity"]
            runtime = copy.deepcopy(server._DISCOVERY_V27_MEASURED_RUNTIME)
            runtime["n_threads"] = 9

            def protocol(graphs_mode: str) -> dict:
                return {
                    **server._DISCOVERY_V27_MEASURED_WORKLOAD,
                    "model_sha256": fixture.input_rows["model"]["sha256"],
                    "metric": "decode_tokens_per_s",
                    "metric_direction": "higher_better",
                    "cpu_list": "184-191",
                    "device": "AMD Instinct MI210",
                    "architecture": "gfx90a",
                    "runtime_config_sha256":
                        server._discovery_content_hash(runtime),
                    "graphs_mode": graphs_mode,
                    "candidate_invocations": 9,
                    "candidate_processes": 1,
                }

            def frame(graphs_mode: str, *, arm: str, identity: dict,
                      factor: str) -> str:
                measured = protocol(graphs_mode)
                return server._discovery_content_hash({
                    "schema": "epyc.autokernel.measurement_arm_frame.v1",
                    "arm": arm, "protocol": measured,
                    "source_commit": identity["source_commit"],
                    "build_identity": identity, "factor_name": factor,
                })

            receipt["protocol_frame_sha256"] = (
                server._discovery_content_hash(protocol("on")))
            receipt["incremental_graphs_off_frame_sha256"] = frame(
                "off", arm="candidate", identity=candidate_identity,
                factor="source_patch")
            receipt["incremental_graphs_on_frame_sha256"] = frame(
                "on", arm="candidate", identity=candidate_identity,
                factor="source_patch")
            receipt["production_graphs_on_frame_sha256"] = frame(
                "on", arm="anchor", identity=fixture.comparator[
                    "build_identity"], factor="cumulative_production")
            receipt["frozen_production"][
                "observed_runtime_config_sha256"] = (
                    server._discovery_content_hash(runtime))
            receipt["frozen_production"]["authority_sha256"] = (
                server._discovery_content_hash({
                    key: value
                    for key, value in receipt["frozen_production"].items()
                    if key != "authority_sha256"}))
            receipt = _seal(receipt, "result_sha256")
            raw = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
            path.write_bytes(raw)
            binding = {
                "path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
            terminal["cumulative_performance"] = receipt
            terminal["cumulative_performance_ref"] = {
                "schema": "epyc.autokernel.cumulative_performance_ref.v1",
                **binding}
            terminal["cumulative_performance_result_sha256"] = receipt[
                "result_sha256"]
            terminal["terminal_sha256"] = server._discovery_content_hash({
                key: value for key, value in terminal.items()
                if key not in server._DISCOVERY_V27_TERMINAL_CORE_EXCLUDED})
            state["cumulative_performance"] = binding
            state["cumulative_composition_terminal"] = terminal
            state = _seal(state, "state_sha256")
            performance = server._discovery_v27_state_contract(
                state, contract)["performance"]
            self.assertIs(performance["available"], False)
            self.assertEqual(
                performance["promotion_reason"],
                "producer_authority_unavailable")

    def test_coherently_resealed_correctness_authority_refuses(self) -> None:
        for name, field in (
                ("failed", "passed"),
                ("not-current", "current_full_suite")):
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, receipt, path = fixture.cumulative_state()
                terminal = state["cumulative_composition_terminal"]
                terminal["correctness"][field] = False
                _rebind_terminal_nested(terminal, receipt)
                state = _reseal_cumulative_state(state, receipt, path)
                performance = server._discovery_v27_state_contract(
                    state, contract)["performance"]
                self.assertIs(performance["available"], False)
                self.assertEqual(
                    performance["promotion_reason"],
                    "producer_authority_unavailable")

    def test_nested_producer_carriers_require_exact_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            state, _, _ = fixture.cumulative_state()
            terminal = state["cumulative_composition_terminal"]
            plan = terminal["plan"]
            pair = terminal["build_pair"]
            correctness = terminal["correctness"]
            comparison = terminal["comparison"]
            self.assertTrue(server._discovery_v27_composition_plan(plan))
            self.assertTrue(server._discovery_v27_full_correctness(
                correctness, pair))
            self.assertTrue(server._discovery_v27_incremental_comparison(
                comparison, pair, correctness))
            mutations = (
                (server._discovery_v27_composition_plan, plan, "extra"),
                (lambda value: server._discovery_v27_full_correctness(
                    value, pair), correctness, "extra"),
                (lambda value: server._discovery_v27_incremental_comparison(
                    value, pair, correctness), comparison, "extra"),
            )
            for validate, value, key in mutations:
                with self.subTest(schema=value["schema"]):
                    malformed = copy.deepcopy(value)
                    malformed[key] = True
                    self.assertFalse(validate(malformed))

    def test_source_manifest_matches_producer_semantic_corpus(self) -> None:
        plan = _composition_plan()
        original = plan["candidate_authority"]["accepted"][-1]["manifest"]

        def manifest_for(
                patch: bytes, *, files: list[str] | None = None,
                symbols: dict[str, list[str]] | None = None) -> dict:
            value = copy.deepcopy(original)
            value["patch_sha256"] = hashlib.sha256(patch).hexdigest()
            value["patch_base64"] = base64.b64encode(patch).decode("ascii")
            if files is not None:
                value["declared_files"] = files
            if symbols is not None:
                value["declared_symbols"] = symbols
            return value

        valid = base64.b64decode(original["patch_base64"], validate=True)
        cases = (
            ("valid", manifest_for(valid), True),
            ("not-diff", manifest_for(b"not a unified diff\n"), False),
            ("missing-newline", manifest_for(valid.rstrip(b"\n")), False),
            ("bad-count", manifest_for(
                valid.replace(b"@@ -1 +1 @@", b"@@ -1,2 +1,2 @@")), False),
            ("wrong-path", manifest_for(
                valid, files=["src/other.cpp"],
                symbols={"src/other.cpp": ["<file-scope>"]}), False),
            ("wrong-scope", manifest_for(
                valid, symbols={"src/test.cpp": ["other"]}), False),
            ("named-scope", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
                b"@@ -1 +1 @@ int test()\n-int x;\n+int y;\n",
                symbols={"src/test.cpp": ["test"]}), True),
            ("named-scope-mismatch", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
                b"@@ -1 +1 @@ int test()\n-int x;\n+int y;\n",
                symbols={"src/test.cpp": ["other"]}), False),
            ("phase-probe", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
                b"@@ -1 +1 @@\n-int x;\n"
                b"+int benchmark_phase;\n"), False),
            ("capture-replay", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
                b"@@ -1 +1 @@\n-int x;\n+hipGraphLaunch(x);\n"), False),
            ("content-specialization", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
                b"@@ -1 +1 @@\n-int x;\n+int input_hash;\n"), False),
            ("surplus-capture", manifest_for(
                valid + b"+hipGraphLaunch(x);\n"), False),
            ("surplus-phase", manifest_for(
                valid + b"+int benchmark_phase;\n"), False),
            ("surplus-content", manifest_for(
                valid + b"+int input_hash;\n"), False),
            ("symlink-mode", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"new file mode 120000\n--- /dev/null\n"
                b"+++ b/src/test.cpp\n@@ -0,0 +1 @@\n+target\n"), False),
            ("valid-new-file", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"new file mode 100644\n--- /dev/null\n"
                b"+++ b/src/test.cpp\n@@ -0,0 +1 @@\n+int y;\n"), True),
            ("valid-deletion", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"deleted file mode 100644\n--- a/src/test.cpp\n"
                b"+++ /dev/null\n@@ -1 +0,0 @@\n-int x;\n"), True),
            ("rename", manifest_for(
                b"diff --git a/src/test.cpp b/src/other.cpp\n"
                b"--- a/src/test.cpp\n+++ b/src/other.cpp\n"
                b"@@ -1 +1 @@\n-int x;\n+int y;\n"), False),
            ("both-devnull", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- /dev/null\n+++ /dev/null\n"
                b"@@ -0,0 +1 @@\n+int y;\n"), False),
            ("unexpected-leading", manifest_for(
                b"commentary\n" + valid), False),
            ("unexpected-trailing", manifest_for(
                valid + b"commentary\n"), False),
            ("header-only", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"), False),
            ("missing-new-marker", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- a/src/test.cpp\n"
                b"@@ -1 +1 @@\n-int x;\n+int y;\n"), False),
            ("missing-old-marker", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"+++ b/src/test.cpp\n"
                b"@@ -1 +1 @@\n-int x;\n+int y;\n"), False),
            ("marker-reorder", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"+++ b/src/test.cpp\n--- a/src/test.cpp\n"
                b"@@ -1 +1 @@\n-int x;\n+int y;\n"), False),
            ("addition-outside-hunk", manifest_for(
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"+int benchmark_phase;\n"), False),
            ("duplicate-incomplete-section", manifest_for(
                valid
                + b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"+int benchmark_phase;\n"), False),
            ("duplicate-complete-section", manifest_for(
                valid + valid), False),
            ("two-valid-sections", manifest_for(
                valid
                + b"diff --git a/src/other.cpp b/src/other.cpp\n"
                b"--- a/src/other.cpp\n+++ b/src/other.cpp\n"
                b"@@ -1 +1 @@\n-int a;\n+int b;\n",
                files=["src/other.cpp", "src/test.cpp"],
                symbols={
                    "src/other.cpp": ["<file-scope>"],
                    "src/test.cpp": ["<file-scope>"]}), True),
            ("two-valid-hunks", manifest_for(
                valid
                + b"@@ -3 +3 @@\n-int a;\n+int b;\n"), True),
            ("newline-marker", manifest_for(
                valid[:-1] + b"\n\\ No newline at end of file\n"), True),
            ("arbitrary-backslash", manifest_for(
                valid[:-1] + b"\n\\ ignored material\n"), False),
        )
        for name, manifest, expected in cases:
            with self.subTest(name=name):
                self.assertIs(
                    server._discovery_v27_source_manifest(manifest)
                    is not None, expected)

        # Bounded transition mutations over every canonical row/boundary.  The
        # expected accept set was established against producer
        # SourcePatchManifest validation at 22e17405e: moving the two changed
        # rows is still an accounted hunk; every other deletion, duplication,
        # header reorder, truncation, or reward-token insertion is not.
        rows = valid.splitlines(keepends=True)
        mutation_cases: list[tuple[str, bytes, bool]] = []
        for index in range(len(rows)):
            mutation_cases.append((
                f"delete-row-{index}", b"".join(rows[:index] + rows[index + 1:]),
                False))
            mutation_cases.append((
                f"duplicate-row-{index}",
                b"".join(rows[:index] + [rows[index]] + rows[index:]), False))
        for index in range(len(rows) - 1):
            swapped = rows[:]
            swapped[index], swapped[index + 1] = (
                swapped[index + 1], swapped[index])
            mutation_cases.append((
                f"swap-rows-{index}-{index + 1}", b"".join(swapped),
                index == 4))
        for index in range(len(rows) + 1):
            mutation_cases.append((
                f"insert-reward-row-{index}",
                b"".join(rows[:index]) + b"+int benchmark_phase;\n"
                + b"".join(rows[index:]), False))
        for index in range(len(rows)):
            mutation_cases.append((
                f"truncate-at-row-{index}", b"".join(rows[:index]), False))
        mutation_cases.extend((
            ("old-count-two", valid.replace(
                b"@@ -1 +1 @@", b"@@ -1,2 +1 @@"), False),
            ("new-count-two", valid.replace(
                b"@@ -1 +1 @@", b"@@ -1 +1,2 @@"), False),
            ("old-start-two", valid.replace(
                b"@@ -1 +1 @@", b"@@ -2 +1 @@"), True),
            ("new-start-two", valid.replace(
                b"@@ -1 +1 @@", b"@@ -1 +2 @@"), True),
        ))
        for name, patch, expected in mutation_cases:
            with self.subTest(mutation=name):
                self.assertIs(
                    server._discovery_v27_source_manifest(
                        manifest_for(patch)) is not None,
                    expected)

    def test_composition_authority_matches_producer_compatibility_corpus(
            self) -> None:
        plan = _composition_plan()
        template = plan["candidate_authority"]["accepted"][0]

        def lever_for(
                label: str, patch: bytes, *, path: str = "src/test.cpp",
                symbol: str) -> dict:
            lever = copy.deepcopy(template)
            lever["hypothesis_id"] = f"akh-{label}"
            lever["cross_campaign_candidate_sha256"] = _digest(
                f"cross-{label}")
            manifest = lever["manifest"]
            manifest["proposal_id"] = f"akp-{label}"
            manifest["candidate_id"] = f"akc-{label}"
            manifest["mechanism_id"] = label
            manifest["declared_files"] = [path]
            manifest["declared_symbols"] = {path: [symbol]}
            manifest["patch_sha256"] = hashlib.sha256(patch).hexdigest()
            manifest["patch_base64"] = base64.b64encode(patch).decode("ascii")
            lever["manifest_sha256"] = server._discovery_content_hash(manifest)
            return _seal(lever, "lever_sha256")

        def patch_for(
                path: str, symbol: str, old_start: int,
                *, insertion: bool = False) -> bytes:
            if insertion:
                hunk = (
                    f"@@ -{old_start},0 +{old_start} @@ int {symbol}()\n"
                    f"+int {symbol}_value = 1;\n")
            else:
                hunk = (
                    f"@@ -{old_start} +{old_start} @@ int {symbol}()\n"
                    f"-int {symbol}_value = 0;\n"
                    f"+int {symbol}_value = 1;\n")
            return (
                f"diff --git a/{path} b/{path}\n"
                f"--- a/{path}\n+++ b/{path}\n{hunk}").encode()

        first = lever_for(
            "first", patch_for("src/test.cpp", "first", 1),
            symbol="first")
        nonoverlap = lever_for(
            "nonoverlap", patch_for("src/test.cpp", "second", 3),
            symbol="second")
        same_symbol = lever_for(
            "same-symbol", patch_for("src/test.cpp", "first", 3),
            symbol="first")
        overlap = lever_for(
            "overlap", patch_for("src/test.cpp", "second", 1),
            symbol="second")
        insertion_overlap = lever_for(
            "insertion-overlap",
            patch_for("src/test.cpp", "second", 1, insertion=True),
            symbol="second")
        insertion_nonoverlap = lever_for(
            "insertion-nonoverlap",
            patch_for("src/test.cpp", "second", 3, insertion=True),
            symbol="second")
        deletion_overlap = lever_for(
            "deletion-overlap",
            b"diff --git a/src/test.cpp b/src/test.cpp\n"
            b"--- a/src/test.cpp\n+++ /dev/null\n"
            b"@@ -1 +0,0 @@ int second()\n-int second_value = 0;\n",
            symbol="second")
        other_file = lever_for(
            "other-file", patch_for("src/other.cpp", "first", 1),
            path="src/other.cpp", symbol="first")
        file_scope = lever_for(
            "file-scope",
            b"diff --git a/src/test.cpp b/src/test.cpp\n"
            b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
            b"@@ -3 +3 @@\n-int x;\n+int y;\n",
            symbol="<file-scope>")
        duplicate_candidate = copy.deepcopy(nonoverlap)
        duplicate_candidate["cross_campaign_candidate_sha256"] = first[
            "cross_campaign_candidate_sha256"]
        duplicate_candidate = _seal(duplicate_candidate, "lever_sha256")
        duplicate_manifest = copy.deepcopy(first)

        authority = plan["candidate_authority"]
        cases = (
            ("single", [first], True),
            ("nonoverlap", [first, nonoverlap], True),
            ("reverse-nonoverlap", [nonoverlap, first], True),
            ("other-file", [first, other_file], True),
            ("same-symbol", [first, same_symbol], False),
            ("overlap", [first, overlap], False),
            ("insertion-overlap", [first, insertion_overlap], False),
            ("insertion-nonoverlap", [first, insertion_nonoverlap], True),
            ("deletion-overlap", [first, deletion_overlap], False),
            ("file-scope", [first, file_scope], False),
            ("duplicate-candidate", [first, duplicate_candidate], False),
            ("duplicate-manifest", [first, duplicate_manifest], False),
        )
        for name, accepted, expected in cases:
            with self.subTest(name=name):
                value = _composition_authority(
                    accepted=accepted,
                    campaign_id=authority["campaign_id"],
                    production_base_commit=authority[
                        "production_base_commit"],
                    instrument_commit=authority["instrument_commit"])
                self.assertIs(
                    server._discovery_v27_composition_authority(value),
                    expected)

    def test_coherently_resealed_non_diff_manifest_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, receipt, path = fixture.cumulative_state()
            terminal = state["cumulative_composition_terminal"]
            plan = terminal["plan"]
            lever = copy.deepcopy(
                plan["candidate_authority"]["accepted"][-1])
            patch = b"not a unified diff\n"
            lever["manifest"]["patch_sha256"] = hashlib.sha256(
                patch).hexdigest()
            lever["manifest"]["patch_base64"] = base64.b64encode(
                patch).decode("ascii")
            lever["manifest_sha256"] = server._discovery_content_hash(
                lever["manifest"])
            lever = _seal(lever, "lever_sha256")
            _reseal_plan_authorities(
                plan, anchor_levers=[], candidate_levers=[lever])
            _rebind_plan_evidence(terminal, receipt)
            state = _reseal_cumulative_state(state, receipt, path)
            performance = server._discovery_v27_state_contract(
                state, contract)["performance"]
            self.assertIs(performance["available"], False)
            self.assertEqual(
                performance["promotion_reason"],
                "producer_authority_unavailable")

    def test_coherently_resealed_surplus_and_devnull_patches_refuse(
            self) -> None:
        cases = (
            ("surplus-capture", b"+hipGraphLaunch(x);\n"),
            ("surplus-phase", b"+int benchmark_phase;\n"),
            ("surplus-content", b"+int input_hash;\n"),
            ("duplicate-incomplete",
             b"diff --git a/src/test.cpp b/src/test.cpp\n"
             b"+int benchmark_phase;\n"),
            ("both-devnull",
             b"diff --git a/src/test.cpp b/src/test.cpp\n"
             b"--- /dev/null\n+++ /dev/null\n"
             b"@@ -0,0 +1 @@\n+int y;\n"),
        )
        for name, material in cases:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, receipt, path = fixture.cumulative_state()
                terminal = state["cumulative_composition_terminal"]
                plan = terminal["plan"]
                lever = copy.deepcopy(
                    plan["candidate_authority"]["accepted"][-1])
                patch = (
                    material if name == "both-devnull" else
                    base64.b64decode(
                        lever["manifest"]["patch_base64"], validate=True)
                    + material)
                lever["manifest"]["patch_sha256"] = hashlib.sha256(
                    patch).hexdigest()
                lever["manifest"]["patch_base64"] = base64.b64encode(
                    patch).decode("ascii")
                lever["manifest_sha256"] = server._discovery_content_hash(
                    lever["manifest"])
                lever = _seal(lever, "lever_sha256")
                _reseal_plan_authorities(
                    plan, anchor_levers=[], candidate_levers=[lever])
                _rebind_plan_evidence(terminal, receipt)
                state = _reseal_cumulative_state(state, receipt, path)
                performance = server._discovery_v27_state_contract(
                    state, contract)["performance"]
                self.assertIs(performance["available"], False)
                self.assertEqual(
                    performance["promotion_reason"],
                    "producer_authority_unavailable")

    def test_coherently_resealed_conflicting_composition_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, receipt, path = fixture.cumulative_state()
            terminal = state["cumulative_composition_terminal"]
            plan = terminal["plan"]
            existing = copy.deepcopy(
                plan["candidate_authority"]["accepted"][-1])
            proposed = copy.deepcopy(existing)
            proposed["hypothesis_id"] = "akh-dashboard-v27-conflict"
            proposed["cross_campaign_candidate_sha256"] = _digest(
                "cross-campaign-conflict")
            proposed["manifest"].update({
                "proposal_id": "akp-dashboard-v27-conflict",
                "candidate_id": "akc-dashboard-v27-conflict",
                "mechanism_id": "dashboard-v27-conflict",
            })
            proposed["manifest_sha256"] = server._discovery_content_hash(
                proposed["manifest"])
            for index, row in enumerate(proposed["replications"]):
                row["result_sha256"] = _digest(
                    f"conflict-isolated-result-{index}")
            proposed = _seal(proposed, "lever_sha256")
            _reseal_plan_authorities(
                plan, anchor_levers=[existing],
                candidate_levers=[existing, proposed])
            _rebind_plan_evidence(terminal, receipt)
            state = _reseal_cumulative_state(state, receipt, path)
            performance = server._discovery_v27_state_contract(
                state, contract)["performance"]
            self.assertIs(performance["available"], False)
            self.assertEqual(
                performance["promotion_reason"],
                "producer_authority_unavailable")

    def test_coherently_resealed_old_coordinate_overlap_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, receipt, path = fixture.cumulative_state()
            terminal = state["cumulative_composition_terminal"]
            plan = terminal["plan"]
            template = plan["candidate_authority"]["accepted"][-1]

            def lever_for(label: str, symbol: str) -> dict:
                lever = copy.deepcopy(template)
                patch = (
                    "diff --git a/src/test.cpp b/src/test.cpp\n"
                    "--- a/src/test.cpp\n+++ b/src/test.cpp\n"
                    f"@@ -1 +1 @@ int {symbol}()\n"
                    "-int x;\n+int y;\n").encode()
                lever["hypothesis_id"] = f"akh-dashboard-v27-{label}"
                lever["cross_campaign_candidate_sha256"] = _digest(
                    f"cross-{label}")
                lever["manifest"].update({
                    "proposal_id": f"akp-dashboard-v27-{label}",
                    "candidate_id": f"akc-dashboard-v27-{label}",
                    "mechanism_id": f"dashboard-v27-{label}",
                    "declared_symbols": {"src/test.cpp": [symbol]},
                    "patch_sha256": hashlib.sha256(patch).hexdigest(),
                    "patch_base64": base64.b64encode(patch).decode("ascii"),
                })
                lever["manifest_sha256"] = server._discovery_content_hash(
                    lever["manifest"])
                for index, row in enumerate(lever["replications"]):
                    row["result_sha256"] = _digest(
                        f"{label}-isolated-result-{index}")
                return _seal(lever, "lever_sha256")

            existing = lever_for("existing", "first")
            proposed = lever_for("proposed", "second")
            self.assertTrue(server._discovery_v27_replicated_lever(existing))
            self.assertTrue(server._discovery_v27_replicated_lever(proposed))
            _reseal_plan_authorities(
                plan, anchor_levers=[existing],
                candidate_levers=[existing, proposed])
            _rebind_plan_evidence(terminal, receipt)
            state = _reseal_cumulative_state(state, receipt, path)
            performance = server._discovery_v27_state_contract(
                state, contract)["performance"]
            self.assertIs(performance["available"], False)
            self.assertEqual(
                performance["promotion_reason"],
                "producer_authority_unavailable")

    def test_empty_raw_context_preserves_old_coordinate_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, receipt, path = fixture.cumulative_state()
            terminal = state["cumulative_composition_terminal"]
            plan = terminal["plan"]
            template = plan["candidate_authority"]["accepted"][-1]

            def lever_for(
                    label: str, symbol: str, patch: bytes) -> dict:
                lever = copy.deepcopy(template)
                lever["hypothesis_id"] = f"akh-dashboard-v27-{label}"
                lever["cross_campaign_candidate_sha256"] = _digest(
                    f"cross-{label}")
                lever["manifest"].update({
                    "proposal_id": f"akp-dashboard-v27-{label}",
                    "candidate_id": f"akc-dashboard-v27-{label}",
                    "mechanism_id": f"dashboard-v27-{label}",
                    "declared_symbols": {"src/test.cpp": [symbol]},
                    "patch_sha256": hashlib.sha256(patch).hexdigest(),
                    "patch_base64": base64.b64encode(patch).decode("ascii"),
                })
                lever["manifest_sha256"] = server._discovery_content_hash(
                    lever["manifest"])
                for index, row in enumerate(lever["replications"]):
                    row["result_sha256"] = _digest(
                        f"{label}-isolated-result-{index}")
                return _seal(lever, "lever_sha256")

            existing = lever_for(
                "empty-context", "first",
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
                b"@@ -1 +1,2 @@ int first()\n\n+int y;\n")
            proposed = lever_for(
                "delete-anchor", "second",
                b"diff --git a/src/test.cpp b/src/test.cpp\n"
                b"--- a/src/test.cpp\n+++ b/src/test.cpp\n"
                b"@@ -1 +0,0 @@ int second()\n-int x;\n")
            self.assertTrue(server._discovery_v27_replicated_lever(existing))
            self.assertTrue(server._discovery_v27_replicated_lever(proposed))
            _reseal_plan_authorities(
                plan, anchor_levers=[existing],
                candidate_levers=[existing, proposed])
            _rebind_plan_evidence(terminal, receipt)
            state = _reseal_cumulative_state(state, receipt, path)
            performance = server._discovery_v27_state_contract(
                state, contract)["performance"]
            self.assertIs(performance["available"], False)
            self.assertEqual(
                performance["promotion_reason"],
                "producer_authority_unavailable")

    def test_coherently_resealed_incremental_authority_refuses(self) -> None:
        def wrong_classification(comparison: dict) -> None:
            comparison["classification"] = "screened_out"

        def changed_effect(comparison: dict) -> None:
            comparison["exact_route_effect_fraction"] = .02

        def changed_admissibility(comparison: dict) -> None:
            comparison.update({
                "exact_route_effect_fraction": -.01,
                "graphs_off_effect_fraction": -.01,
                "graphs_on_effect_fraction": -.01,
                "classification": "screened_out",
            })

        def skipped_arm(comparison: dict) -> None:
            comparison["graphs_off_executed"] = False

        mutations = (
            ("classification", wrong_classification),
            ("effect", changed_effect),
            ("admissibility", changed_admissibility),
            ("executed", skipped_arm),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, receipt, path = fixture.cumulative_state()
                terminal = state["cumulative_composition_terminal"]
                mutate(terminal["comparison"])
                _rebind_terminal_nested(terminal, receipt)
                state = _reseal_cumulative_state(state, receipt, path)
                performance = server._discovery_v27_state_contract(
                    state, contract)["performance"]
                self.assertIs(performance["available"], False)
                self.assertEqual(
                    performance["promotion_reason"],
                    "producer_authority_unavailable")

    def test_coherently_resealed_plan_and_evidence_join_swaps_refuse(
            self) -> None:
        def plan_lever(terminal: dict, receipt: dict) -> None:
            terminal["plan"]["new_lever_sha256"] = "0" * 64
            _reseal_plan(terminal["plan"])
            _rebind_terminal_nested(terminal, receipt)

        def terminal_lever(terminal: dict, receipt: dict) -> None:
            terminal["lever_sha256"] = "0" * 64

        def terminal_isolated(terminal: dict, receipt: dict) -> None:
            terminal["isolated_result_sha256s"][0] = "0" * 64

        def pair_candidate(terminal: dict, receipt: dict) -> None:
            terminal["build_pair"]["candidate"][
                "patch_set_sha256"] = "0" * 64
            receipt["accepted_patch_set_sha256"] = "0" * 64
            _rebind_terminal_nested(terminal, receipt)

        def correctness_candidate(terminal: dict, receipt: dict) -> None:
            terminal["correctness"][
                "candidate_build_identity_sha256"] = "0" * 64
            _rebind_terminal_nested(terminal, receipt)

        def accepted_authority(terminal: dict, receipt: dict) -> None:
            receipt["accepted_authority_sha256"] = "0" * 64

        mutations = (
            ("plan-lever", plan_lever),
            ("terminal-lever", terminal_lever),
            ("terminal-isolated", terminal_isolated),
            ("pair-candidate", pair_candidate),
            ("correctness-candidate", correctness_candidate),
            ("accepted-authority", accepted_authority),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, receipt, path = fixture.cumulative_state()
                terminal = state["cumulative_composition_terminal"]
                mutate(terminal, receipt)
                state = _reseal_cumulative_state(state, receipt, path)
                performance = server._discovery_v27_state_contract(
                    state, contract)["performance"]
                self.assertIs(performance["available"], False)
                self.assertEqual(
                    performance["promotion_reason"],
                    "producer_authority_unavailable")

    def test_final_v27_product_pins_are_deliberately_fail_closed(self) -> None:
        self.assertIsNone(server._DISCOVERY_V27_PRODUCER_COMMIT)
        self.assertIsNone(server._DISCOVERY_V27_EXECUTION_MODULE_SHA256)
        self.assertIsNone(server._DISCOVERY_V27_DEPLOYMENT_SEMANTIC_SHA256)
        self.assertIsNone(server._DISCOVERY_V27_DEPLOYMENT_FILE_SHA256)
        self.assertIsNone(server._DISCOVERY_V27_GRAPH_SHA256)
        self.assertIsNone(server._DISCOVERY_V27_GRAPH_FILE_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            contract = server._discovery_v27_contract(
                fixture.config_path, fixture.config, fixture.bundle)
            self.assertIsNotNone(contract)
            self.assertIs(contract["ready"], False)

    def test_q5_erratum_annuls_science_but_preserves_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, _ = fixture.checkpoint()
            projected = server._discovery_v27_state_contract(state, contract)
            self.assertEqual(projected["scientific_attempts"], 0)
            self.assertEqual(projected["scientific_budget"], {
                "spent": 0, "maximum": 10})
            self.assertEqual(projected["annulled_scientific_attempts"], 1)
            self.assertEqual(projected["annulled_history"][0]["status"],
                             "attribution_expectation_invalid")
            self.assertEqual(projected["annulled_history"][0]["raw_status"],
                             "attribution_route_falsified")
            self.assertIs(
                projected["annulled_history"][0]["history_retained"], True)

    def test_postbuild_wait_is_stopped_on_foreign_gpu_and_resumable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = V27Fixture(root)
            state = fixture.postbuild_wait_state()
            (fixture.state / "state.json").write_bytes(
                server._canonical_json_bytes(state) + b"\n")
            fixture.write_journal([(
                "discovery_waiting_resource", state["state_sha256"])])
            with mock.patch.object(
                    server, "AUTOKERNEL_DEPLOYMENTS_ROOT", root), \
                    _frozen(fixture), \
                    mock.patch.object(
                        server, "_discovery_lock_held", return_value=False):
                payload, _ = server._discovery_live_read()
            activity = payload["activity"]
            self.assertEqual(activity["status"], "stopped")
            self.assertEqual(activity["phase"]["id"], "resource_admission")
            self.assertIn("foreign GPU", activity["waiting_on"])
            self.assertIs(activity["failure"]["detected"], False)
            self.assertIs(activity["resume"]["required"], True)
            self.assertIs(activity["resume"]["possible"], True)
            self.assertEqual(activity["resume"]["disposition"],
                             "resume_postbuild_resource_wait")
            self.assertEqual(activity["scientific_attempts"], 0)
            self.assertEqual(activity["scientific_budget"], {
                "spent": 0, "maximum": 10})
            self.assertEqual(activity["history"]["annulled_count"], 1)
            stages = {row["id"]: row for row in activity["pipeline"]}
            self.assertEqual(stages["build"]["state"], "complete")
            self.assertEqual(stages["evidence_binding"]["state"], "complete")
            self.assertEqual(stages["resource_admission"]["state"], "waiting")

    def test_missing_or_tampered_typed_wait_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            valid = fixture.postbuild_wait_state()
            self.assertIsNotNone(server._discovery_v27_state_contract(
                valid, contract))
            missing = copy.deepcopy(valid)
            missing["pending"].pop("resource_wait")
            missing = _seal(missing, "state_sha256")
            self.assertIsNone(server._discovery_v27_state_contract(
                missing, contract))
            tampered = copy.deepcopy(valid)
            tampered["pending"]["resource_wait"][
                "wait_receipt_sha256"] = "0" * 64
            tampered = _seal(tampered, "state_sha256")
            self.assertIsNone(server._discovery_v27_state_contract(
                tampered, contract))
            wait_path = Path(valid["pending"]["row"]["lease"][
                "stage_receipt_path"])
            wait_path.write_text("{}\n", encoding="utf-8")
            self.assertIsNone(server._discovery_v27_state_contract(
                valid, contract))

    def test_prebuild_legacy_wait_remains_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, _ = fixture.checkpoint()
            pending = state["pending"]
            pending.pop("phase")
            pending.pop("context")
            pending.pop("context_sha256")
            pending.update(authorization={}, infrastructure_retry_epoch=0)
            pending["row"].update(
                status="waiting_resource", operation_key="a" * 64,
                lease={"admitted": False, "phase": "prebuild_probe",
                       "reason": "device_busy", "operation_key": "a" * 64,
                       "promotion_claim": False, "mode": "cold_serialized",
                       "device_id": "mi210_0",
                       "inference_window_lock": "/lock",
                       "model_sha256": fixture.input_rows["model"]["sha256"],
                       "load_admission": {"decision": "busy"},
                       "detail": "device claim unavailable"})
            state = _seal(state, "state_sha256")
            projected = server._discovery_v27_state_contract(state, contract)
            self.assertEqual(projected["resource_wait"], {
                "kind": "prebuild_resource_wait",
                "operation_key": "a" * 64,
                "reason": "device_busy",
                "completed_builds_preserved": False,
                "evidence_policy_bound": False,
            })

    def test_torn_legacy_wait_cannot_hide_postbuild_artifacts(self) -> None:
        artifacts = ("postbuild-checkpoint.json", "evidence-policy.json",
                     "resource-waits")
        for artifact in artifacts:
            with self.subTest(artifact=artifact), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, _ = fixture.checkpoint()
                pending = state["pending"]
                pending.pop("phase")
                pending.pop("context")
                pending.pop("context_sha256")
                pending.update(authorization={}, infrastructure_retry_epoch=0)
                operation_key = "a" * 64
                pending["row"].update(
                    status="waiting_resource", operation_key=operation_key,
                    lease={
                        "admitted": False, "phase": "prebuild_probe",
                        "reason": "device_busy", "operation_key": operation_key,
                        "promotion_claim": False, "mode": "cold_serialized",
                        "device_id": "mi210_0", "inference_window_lock": "/lock",
                        "model_sha256": fixture.input_rows["model"]["sha256"],
                        "load_admission": {"decision": "busy"}, "detail": "busy"})
                target = fixture.bundle / "operations" / operation_key / artifact
                if artifact == "resource-waits":
                    target.mkdir(parents=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text("{}\n", encoding="utf-8")
                self.assertIsNone(server._discovery_v27_state_contract(
                    _seal(state, "state_sha256"), contract))

    def test_full_build_and_policy_grammar_refuses_mutations(self) -> None:
        mutations = (
            ("missing-build", lambda build, policy: build.pop("anchor_build")),
            ("typed-build", lambda build, policy: build.update(build_key=None)),
            ("weak-build-commit", lambda build, policy:
                build["candidate_identity"].update(source_commit="main")),
            ("extra-policy", lambda build, policy: policy.update(extra=True)),
            ("missing-policy", lambda build, policy: policy.pop("dispatch")),
            ("typed-policy", lambda build, policy:
                policy.update(expected_correctness_cases=True)),
            ("relative-policy-argv", lambda build, policy:
                policy.update(correctness_argv=["test-backend-ops"])),
            ("foreign-policy-model", lambda build, policy:
                policy.update(model_sha256="0" * 64)),
            ("boolean-policy-dispatch", lambda build, policy:
                policy["dispatch"]["candidate_exact"][0].update(calls=True)),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state = fixture.postbuild_wait_state()
                operation_key = state["pending"]["row"]["operation_key"]
                root = fixture.bundle / "operations" / operation_key
                postbuild_path = root / "postbuild-checkpoint.json"
                postbuild = json.loads(postbuild_path.read_text())
                policy_path = root / "evidence-policy.json"
                policy = json.loads(policy_path.read_text())
                mutate(postbuild["build"], policy)
                postbuild = _seal(postbuild, "receipt_sha256")
                postbuild_path.write_text(
                    json.dumps(postbuild, sort_keys=True, indent=2) + "\n")
                policy_path.write_text(
                    json.dumps(policy, sort_keys=True, indent=2) + "\n")
                self.assertIsNone(server._discovery_v27_state_contract(
                    state, contract))

    def test_carry_forward_missing_extra_type_and_coherent_mutation_refuse(self) -> None:
        mutations = (
            ("missing", lambda value: value.pop("portfolio_outcomes")),
            ("extra", lambda value: value.update(extra=True)),
            ("type", lambda value: value.update(candidate_patch_sha256={})),
            ("predecessor", lambda value: value.update(
                predecessor_state_file_sha256="0" * 64)),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                carry = copy.deepcopy(fixture.carry)
                mutate(carry)
                carry = _seal(carry, "carry_forward_sha256")
                path = Path(fixture.input_rows["carry_forward"]["path"])
                raw = (json.dumps(carry, sort_keys=True, indent=2) + "\n").encode()
                path.write_bytes(raw)
                fixture.input_rows["carry_forward"]["sha256"] = (
                    hashlib.sha256(raw).hexdigest())
                fixture.config["immutable_inputs"]["carry_forward"][
                    "sha256"] = hashlib.sha256(raw).hexdigest()
                fixture.graph["carry_forward_sha256"] = carry[
                    "carry_forward_sha256"]
                fixture.write()
                self.assertIsNone(server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle))

    def test_arbitrary_graph_carry_digest_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            fixture.graph["carry_forward_sha256"] = "0" * 64
            fixture.write()
            with _frozen(fixture):
                self.assertIsNone(server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle))

    def test_cumulative_headline_is_producer_authority_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, receipt, path = fixture.cumulative_state()
            projected = server._discovery_v27_state_contract(state, contract)
            performance = projected["performance"]
            self.assertIs(performance["available"], True)
            self.assertEqual(
                performance["cumulative_vs_frozen_production"][
                    "production_commit"],
                server._DISCOVERY_V27_PRODUCTION_COMMIT)
            self.assertAlmostEqual(
                performance["cumulative_vs_frozen_production"][
                    "effect_fraction"], .05)
            self.assertAlmostEqual(
                performance["incremental_vs_prior_stack"]["effect_fraction"],
                .01)
            self.assertEqual(
                performance["headline"],
                "+5.00% cumulative vs frozen production (1.0500x)")
            self.assertIs(performance["promotion_eligible"], True)
            rendered = json.dumps(performance)
            self.assertNotIn(str(path), rendered)
            self.assertNotIn(str(fixture.bundle), rendered)
            self.assertEqual(performance["receipt_sha256"],
                             receipt["result_sha256"])
            (fixture.state / "state.json").write_bytes(
                server._canonical_json_bytes(state) + b"\n")
            fixture.write_journal([(
                "discovery_preauthored_checkpointed", state["state_sha256"])])
            with mock.patch.object(
                    server, "AUTOKERNEL_DEPLOYMENTS_ROOT", Path(directory)), \
                    _frozen(fixture), \
                    mock.patch.object(
                        server, "_discovery_lock_held", return_value=False):
                payload, _ = server._discovery_live_read()
            self.assertEqual(payload["activity"]["performance"], performance)

    def test_cumulative_authority_fails_closed_for_bad_states(
            self) -> None:
        cases = (
            ("mixed", dict(frame_mismatch=True),
             "producer_authority_unavailable"),
            ("shared-protocol", dict(protocol_mismatch=True),
             "producer_authority_unavailable"),
            ("candidate-frame", dict(candidate_frame_substitution=True),
             "producer_authority_unavailable"),
            ("candidate-off-frame",
             dict(candidate_off_frame_substitution=True),
             "producer_authority_unavailable"),
            ("graphs-mode", dict(production_graphs_mode="off"),
             "producer_authority_unavailable"),
            ("runtime-config", dict(runtime_config_mismatch=True),
             "producer_authority_unavailable"),
            ("receipt-alias", dict(measurement_receipt_alias=True),
             "producer_authority_unavailable"),
            ("producer-verdict", dict(promotion_eligible_override=False),
             "producer_authority_unavailable"),
            ("impossible-cumulative", dict(
                cumulative=-1.0, incremental=.03, disposition="admitted"),
             "producer_authority_unavailable"),
        )
        for name, kwargs, reason in cases:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, _, _ = fixture.cumulative_state(**kwargs)
                performance = server._discovery_v27_state_contract(
                    state, contract)["performance"]
                self.assertIs(performance["promotion_eligible"], False)
                self.assertEqual(performance["promotion_reason"], reason)
                self.assertIs(performance["available"], False)

    def test_terminal_decision_core_excludes_exactly_four_fields(self) -> None:
        self.assertEqual(server._DISCOVERY_V27_TERMINAL_CORE_EXCLUDED, {
            "cumulative_performance", "cumulative_performance_ref",
            "cumulative_performance_result_sha256", "terminal_sha256"})

    def test_valid_nonpromotable_measurements_remain_headline_visible(
            self) -> None:
        cases = (
            ("cumulative-screened-out",
             dict(cumulative=-.02, incremental=.03, disposition="admitted"),
             "-2.00% cumulative vs frozen production (0.9800x)",
             "cumulative_screened_out"),
            ("incremental-rollback",
             dict(cumulative=.03, incremental=-.01,
                  disposition="incremental_rollback"),
             "+3.00% cumulative vs frozen production (1.0300x)",
             "incremental_screened_out"),
        )
        for name, kwargs, headline, reason in cases:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, _, _ = fixture.cumulative_state(**kwargs)
                performance = server._discovery_v27_state_contract(
                    state, contract)["performance"]
                self.assertIs(performance["available"], True)
                self.assertIs(performance["promotion_eligible"], False)
                self.assertEqual(performance["promotion_reason"], reason)
                self.assertEqual(performance["headline"], headline)
                self.assertIsNotNone(
                    performance["cumulative_vs_frozen_production"])
                self.assertIsNotNone(performance["incremental_vs_prior_stack"])

    def test_cumulative_comparator_tamper_and_missing_authority_are_unavailable(
            self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            missing, _ = fixture.checkpoint()
            self.assertEqual(server._discovery_v27_state_contract(
                missing, contract)["performance"]["promotion_reason"],
                "cumulative_authority_missing")
            state, receipt, path = fixture.cumulative_state()
            receipt["frozen_production"]["build_identity"][
                "binary_sha256"] = "0" * 64
            receipt = _seal(receipt, "receipt_sha256")
            raw = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
            path.write_bytes(raw)
            state["cumulative_performance"]["sha256"] = hashlib.sha256(
                raw).hexdigest()
            state = _seal(state, "state_sha256")
            performance = server._discovery_v27_state_contract(
                state, contract)["performance"]
            self.assertIs(performance["available"], False)
            self.assertIs(performance["promotion_eligible"], False)
            self.assertEqual(performance["promotion_reason"],
                             "producer_authority_unavailable")

    def test_producer_shaped_terminal_core_hash_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, receipt, _ = fixture.cumulative_state()
            terminal = state["cumulative_composition_terminal"]
            producer_core = server._discovery_content_hash({
                key: value for key, value in terminal.items()
                if key not in server._DISCOVERY_V27_TERMINAL_CORE_EXCLUDED})
            consumer_only_envelope = server._discovery_content_hash({
                key: value for key, value in terminal.items()
                if key != "terminal_sha256"})
            self.assertEqual(terminal["terminal_sha256"], producer_core)
            self.assertEqual(
                receipt["composition_terminal_sha256"], producer_core)
            self.assertNotEqual(producer_core, consumer_only_envelope)
            performance = server._discovery_v27_state_contract(
                state, contract)["performance"]
            self.assertIs(performance["available"], True)

    def test_consumer_only_full_envelope_terminal_hash_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, _, _ = fixture.cumulative_state()
            terminal = state["cumulative_composition_terminal"]
            terminal["terminal_sha256"] = server._discovery_content_hash({
                key: value for key, value in terminal.items()
                if key != "terminal_sha256"})
            state["cumulative_composition_terminal"] = terminal
            state = _seal(state, "state_sha256")
            performance = server._discovery_v27_state_contract(
                state, contract)["performance"]
            self.assertIs(performance["available"], False)
            self.assertIs(performance["promotion_eligible"], False)

    def test_terminal_core_ref_and_full_envelope_tampers_refuse(self) -> None:
        mutations = (
            ("core", lambda terminal:
             terminal.update(promotion_reason="tampered")),
            ("ref", lambda terminal:
             terminal["cumulative_performance_ref"].update(sha256="0" * 64)),
            ("full-envelope", lambda terminal:
             terminal["cumulative_performance"].update(
                 promotion_reason="tampered")),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, _, _ = fixture.cumulative_state()
                terminal = state["cumulative_composition_terminal"]
                mutate(terminal)
                state["cumulative_composition_terminal"] = terminal
                state = _seal(state, "state_sha256")
                performance = server._discovery_v27_state_contract(
                    state, contract)["performance"]
                self.assertIs(performance["available"], False)
                self.assertIs(performance["promotion_eligible"], False)

    def test_frozen_comparator_missing_extra_and_type_mutations_refuse(self) -> None:
        mutations = (
            ("missing", lambda value: value.pop("runtime_receipt_sha256")),
            ("extra", lambda value: value.update(extra=True)),
            ("type", lambda value: value.update(graphs_mode=1)),
            ("graphs-off", lambda value: value.update(
                graphs_mode="graphs_off")),
            ("runtime-missing", lambda value: value.pop(
                "runtime_config_sha256")),
        )
        for name, mutate in mutations:
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                comparator = copy.deepcopy(fixture.comparator)
                mutate(comparator)
                comparator = _seal(comparator, "receipt_sha256")
                path = Path(fixture.input_rows[
                    "frozen_production_comparator"]["path"])
                raw = (json.dumps(
                    comparator, sort_keys=True, indent=2) + "\n").encode()
                path.write_bytes(raw)
                fixture.input_rows[
                    "frozen_production_comparator"]["sha256"] = (
                        hashlib.sha256(raw).hexdigest())
                fixture.config["immutable_inputs"][
                    "frozen_production_comparator"]["sha256"] = (
                        hashlib.sha256(raw).hexdigest())
                fixture.graph["frozen_production_comparator"].update(
                    file_sha256=hashlib.sha256(raw).hexdigest(),
                    receipt_sha256=comparator["receipt_sha256"])
                fixture.write()
                self.assertIsNone(server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle))

    def test_frozen_comparator_runtime_must_match_deployment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V27Fixture(Path(directory))
            comparator = copy.deepcopy(fixture.comparator)
            comparator["runtime_config_sha256"] = "0" * 64
            comparator = _seal(comparator, "receipt_sha256")
            path = Path(fixture.input_rows[
                "frozen_production_comparator"]["path"])
            raw = (json.dumps(
                comparator, sort_keys=True, indent=2) + "\n").encode()
            path.write_bytes(raw)
            file_sha256 = hashlib.sha256(raw).hexdigest()
            fixture.input_rows[
                "frozen_production_comparator"]["sha256"] = file_sha256
            fixture.config["immutable_inputs"][
                "frozen_production_comparator"]["sha256"] = file_sha256
            fixture.graph["frozen_production_comparator"].update(
                file_sha256=file_sha256,
                receipt_sha256=comparator["receipt_sha256"])
            fixture.write()
            with _frozen(fixture):
                self.assertIsNone(server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle))

    def test_erratum_rejects_boolean_lds_under_coherent_reseal(self) -> None:
        value = _q5_erratum()
        key = next(iter(value["corrected_candidate_lds_bytes"]))
        value["corrected_candidate_lds_bytes"][key] = False
        value = _seal(value, "erratum_sha256")
        with mock.patch.object(
                server, "_DISCOVERY_V27_ERRATUM_SHA256",
                value["erratum_sha256"]):
            self.assertIs(server._discovery_v27_erratum(value), False)

    def test_coherent_erratum_and_graph_mutations_refuse(self) -> None:
        mutations = (
            lambda fixture: fixture.erratum.update(
                scientific_budget_spent=True),
            lambda fixture: fixture.graph[
                "attribution_expectation_erratum"].update(
                    candidate_semantic_sha256="0" * 64),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                mutate(fixture)
                if fixture.erratum["scientific_budget_spent"] is True:
                    fixture.erratum["erratum_sha256"] = (
                        server._discovery_controller_state_hash({
                            key: item for key, item in fixture.erratum.items()
                            if key != "erratum_sha256"}))
                    path = fixture.inputs / "q5-lds0-attribution-erratum-v1.json"
                    raw = server._canonical_json_bytes(fixture.erratum) + b"\n"
                    path.write_bytes(raw)
                    fixture.config["immutable_inputs"][
                        "q5_lds0_attribution_erratum"]["sha256"] = (
                            hashlib.sha256(raw).hexdigest())
                fixture.write()
                self.assertIsNone(server._discovery_v27_contract(
                    fixture.config_path, fixture.config, fixture.bundle))


if __name__ == "__main__":
    unittest.main()
