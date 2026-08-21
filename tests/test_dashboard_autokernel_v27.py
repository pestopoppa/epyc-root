from __future__ import annotations

import copy
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


def _frozen_comparator(
        model_sha256: str, workload_sha256: str,
        runtime_config_sha256: str) -> dict:
    value = {
        "schema": "epyc.autokernel.frozen_production_comparator.v1",
        "branch": "production-consolidated-v9",
        "commit": server._DISCOVERY_V27_PRODUCTION_COMMIT,
        "build_identity": _build_identity(
            server._DISCOVERY_V27_PRODUCTION_COMMIT, "1"),
        "build_receipt_sha256": "6" * 64,
        "linkage_receipt_sha256": "7" * 64,
        "runtime_receipt_sha256": "8" * 64,
        "runtime_snapshot_sha256": "c" * 64,
        "measurement_receipt_sha256": "9" * 64,
        "model_sha256": model_sha256,
        "workload_sha256": workload_sha256,
        "runtime_config_sha256": runtime_config_sha256,
        "frame_sha256": "a" * 64,
        "graphs_mode": "graphs_on",
        "metric": "tokens_per_second",
        "direction": "higher_is_better",
        "measurement_protocol_sha256": "b" * 64,
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
    ) -> tuple[dict, dict, Path]:
        state, _ = self.checkpoint()
        operation_key = "d" * 64
        plan_sha256 = "e" * 64
        anchor_identity = _build_identity("e" * 40, "1")
        candidate_identity = _build_identity("f" * 40, "a")
        def build_binding(identity: dict, patch: str) -> dict:
            return {
                "patch_set_sha256": patch * 64,
                "source_materialization_receipt_sha256": "4" * 64,
                "build_identity": identity,
                "build_identity_sha256":
                    server._discovery_content_hash(identity),
            }
        anchor = build_binding(anchor_identity, "7")
        candidate = build_binding(candidate_identity, "8")
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
        correctness = {"result_sha256": "1" * 64}
        comparison = {"result_sha256": "2" * 64}
        terminal = {
            "schema": "epyc.autokernel.cumulative_composition_terminal.v3",
            "operation_key": operation_key, "plan_sha256": plan_sha256,
            "plan": {"operation_key": operation_key,
                     "plan_sha256": plan_sha256},
            "lever_sha256": "3" * 64,
            "cross_campaign_candidate_sha256": "4" * 64,
            "isolated_result_sha256s": ["5" * 64, "6" * 64],
            "disposition": disposition, "scientific_budget_spent": True,
            "build_pair": build_pair, "correctness": correctness,
            "comparison": comparison, "cumulative_performance": None,
            "cumulative_performance_ref": None,
            "correctness_result_sha256": correctness["result_sha256"],
            "comparison_result_sha256": comparison["result_sha256"],
            "cumulative_performance_result_sha256": None,
            "promotion_eligible": eligible, "promotion_reason": reason,
            "admitted_authority_sha256": (
                "9" * 64 if disposition == "admitted" else None),
            "reason_code": (
                "incremental_admitted_promotion_eligible"
                if disposition == "admitted" and eligible else
                "incremental_admitted_" + reason
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
            "schema": "epyc.autokernel.frozen_production_authority.v1",
            "production_commit": server._DISCOVERY_V27_PRODUCTION_COMMIT,
            "build_identity": copy.deepcopy(
                self.comparator["build_identity"]),
            "build_identity_sha256": server._discovery_content_hash(
                self.comparator["build_identity"]),
            "runtime_snapshot_sha256":
                self.comparator["runtime_snapshot_sha256"],
        }
        frozen = {
            **frozen_body,
            "authority_sha256": server._discovery_content_hash(frozen_body)}
        off_frame = (
            self.comparator["frame_sha256"]
            if candidate_off_frame_substitution else "c" * 64)
        on_frame = "e" * 64
        production_frame = (
            on_frame if candidate_frame_substitution else "0" * 64
            if frame_mismatch else self.comparator["frame_sha256"])
        performance = _seal({
            "schema": server._DISCOVERY_V27_CUMULATIVE_SCHEMA,
            "authority": "frozen_production_promotion_gate",
            "promotion_authority": True,
            "operation_key": operation_key, "plan_sha256": plan_sha256,
            "accepted_authority_sha256": "9" * 64,
            "accepted_patch_set_sha256": candidate["patch_set_sha256"],
            "build_pair_sha256": build_pair["pair_sha256"],
            "correctness_result_sha256": correctness["result_sha256"],
            "incremental_comparison_result_sha256":
                comparison["result_sha256"],
            "frozen_production": frozen,
            "model_sha256": self.comparator["model_sha256"],
            "workload_sha256": self.comparator["workload_sha256"],
            "runtime_config_sha256":
                self.comparator["runtime_config_sha256"],
            "protocol_frame_sha256": (
                "0" * 64 if protocol_mismatch else
                self.comparator["measurement_protocol_sha256"]),
            "metric": "tokens_per_second", "metric_direction": "higher_better",
            "incremental_exact_route_effect_fraction": incremental,
            "incremental_graphs_off_effect_fraction": incremental,
            "incremental_graphs_on_effect_fraction": incremental,
            "cumulative_graphs_on_effect_fraction": cumulative,
            "incremental_graphs_off_receipt_sha256": "d" * 64,
            "incremental_graphs_on_receipt_sha256": "e" * 64,
            "production_graphs_on_receipt_sha256": "0" * 64,
            "incremental_graphs_off_frame_sha256": off_frame,
            "incremental_graphs_on_frame_sha256": on_frame,
            "production_graphs_on_frame_sha256": production_frame,
            "production_graphs_mode": production_graphs_mode,
            "cumulative_classification": cumulative_class,
            "promotion_eligible": eligible, "promotion_reason": reason,
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
        terminal["terminal_sha256"] = server._discovery_content_hash({
            key: value for key, value in terminal.items()
            if key != "terminal_sha256"})
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

    def test_cumulative_authority_fails_closed_for_bad_or_nonpromotable_states(
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
            ("nonpositive", dict(cumulative=-.02, incremental=.03,
                                 disposition="admitted"),
             "cumulative_screened_out"),
            ("incremental", dict(cumulative=.03, incremental=-.01,
                                 disposition="incremental_rollback"),
             "incremental_screened_out"),
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

    def test_terminal_core_rejects_wrong_and_full_envelope_hashes(self) -> None:
        for name in ("wrong-core", "full-envelope"):
            with self.subTest(name=name), \
                    tempfile.TemporaryDirectory() as directory:
                fixture = V27Fixture(Path(directory))
                with _frozen(fixture):
                    contract = server._discovery_v27_contract(
                        fixture.config_path, fixture.config, fixture.bundle)
                state, receipt, path = fixture.cumulative_state()
                terminal = state["cumulative_composition_terminal"]
                receipt["composition_terminal_sha256"] = (
                    "0" * 64 if name == "wrong-core"
                    else terminal["terminal_sha256"])
                receipt = _seal(receipt, "result_sha256")
                raw = (json.dumps(
                    receipt, sort_keys=True, indent=2) + "\n").encode()
                path.write_bytes(raw)
                binding = {
                    "path": str(path),
                    "sha256": hashlib.sha256(raw).hexdigest()}
                terminal["cumulative_performance"] = receipt
                terminal["cumulative_performance_ref"] = {
                    "schema":
                        "epyc.autokernel.cumulative_performance_ref.v1",
                    **binding}
                terminal["cumulative_performance_result_sha256"] = receipt[
                    "result_sha256"]
                terminal["terminal_sha256"] = server._discovery_content_hash({
                    key: value for key, value in terminal.items()
                    if key != "terminal_sha256"})
                state["cumulative_performance"] = binding
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
