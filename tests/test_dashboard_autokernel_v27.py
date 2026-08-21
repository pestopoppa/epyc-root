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
    value = {key: "1" * 64 for key in server._DISCOVERY_V27_ERRATUM_KEYS}
    value.update({
        "schema": "epyc.autokernel.attribution_expectation_erratum.v1",
        "predecessor_campaign_id": "ak-discovery-03fc1b1230487a35",
        "operation_key":
            "fdfbf8434c361a32cd07d86ac247f61c62f9f840bc3ed8b437053f089e33f837",
        "hypothesis_id": "akh-v2-q5-onewave-preauthored",
        "candidate_semantic_sha256":
            "06973eb2e4f643b76de198d6cae5e2e9f1b915773dafdf5efd08682bf0df2b63",
        "candidate_patch_sha256":
            "f4cc49cd11cdfd93a2d5d2e00e653f503b6a16ce675bfb12c034fbbfae3e7a77",
        "cross_campaign_candidate_sha256":
            "d5671a1dc197e5d0d53f34f9c4d25f640e0e410d6917b3099459bc40064581b2",
        "attribution_refusal_file_sha256":
            "40707008b6fceae9749dfca56253836e07ce51b19eb7fb003377c3340503eb86",
        "classification": "attribution_route_falsified",
        "candidate_source_commit": "9" * 40,
        "reason": "candidate LDS expectation was invalid",
        "invalidated_predecessor_projection": {
            "turn": 1,
            "result_file_sha256":
                "40707008b6fceae9749dfca56253836e07ce51b19eb7fb003377c3340503eb86",
            "removed_effects": [
                "scientific_attempt", "attempted_candidate_identity",
                "portfolio_skip", "cross_campaign_do_not_repeat"],
            "history_retained": True,
        },
        "stale_candidate_lds_bytes": {
            "route.0": 512, "route.1": 512, "route.2": 512,
            "route.3": 256,
        },
        "corrected_candidate_lds_bytes": {
            "route.0": 0, "route.1": 0, "route.2": 0, "route.3": 0,
        },
        "compiler_metadata_proof": {
            "schema": "epyc.autokernel.amdgpu_group_segment_proof.v2",
            "llvm_objcopy_sha256": "a" * 64,
            "llvm_objcopy_version": "AMD LLVM 18",
            "section_extraction_command": [
                "/opt/rocm/llvm/bin/llvm-objcopy",
                "--dump-section=.hip_fatbin=<section-output>",
                "<hip-library>",
            ],
            "clang_offload_bundler_sha256": "b" * 64,
            "clang_offload_bundler_version": "AMD clang bundler 18",
            "llvm_readobj_sha256": "c" * 64,
            "llvm_readobj_version": "AMD LLVM 18",
            "metadata_command": [
                "/opt/rocm/llvm/bin/llvm-readobj", "--notes",
                "<gfx90a-code-object>",
            ],
            "symbol_command": [
                "/opt/rocm/llvm/bin/llvm-readelf", "-sW",
                "<gfx90a-code-object>",
            ],
            "bundle_parser": {
                "format": "clang_offload_bundle_header_little_endian_v1",
                "container_count": 135,
                "selected_bundle_index": 35,
                "bundle_index_base": 0,
                "selected_target_index": 1,
                "target_index_base": 0,
                "selected_target": "hipv4-amdgcn-amd-amdhsa--gfx90a",
                "payload_offset_within_container": 4096,
                "candidate": {
                    "section_sha256": "d" * 64,
                    "section_size": 100,
                    "container_offset": 10,
                    "code_object_size": 50,
                },
                "anchor": {
                    "section_sha256": "e" * 64,
                    "section_size": 101,
                    "container_offset": 10,
                    "code_object_size": 51,
                },
            },
            "candidate_code_object_sha256":
                "53c63348f3e1797c6c27a82e887bb0b20649636c725fb04d85af3e2038838bd6",
            "anchor_code_object_sha256":
                "ba878a186026165135705597b1c4966c06c7af6a46a5dd99c3194dc76e7d8ab0",
            "selected_mangled_name_set": ["sym_a", "sym_b"],
            "rows": [
                {"mangled_name": "sym_a",
                 "candidate_group_segment_fixed_size": 0,
                 "anchor_group_segment_fixed_size": 1024},
                {"mangled_name": "sym_b",
                 "candidate_group_segment_fixed_size": 0,
                 "anchor_group_segment_fixed_size": 512},
            ],
        },
        "preserved_evidence": ["source_manifest", "governed_correctness"],
        "scientific_budget_spent": False,
        "do_not_repeat": False,
        "replay_authorized": True,
        "replacement_disposition": "attribution_expectation_invalid",
        "resolution": "unresolved_retry_eligible",
    })
    value["erratum_sha256"] = server._discovery_controller_state_hash({
        key: item for key, item in value.items() if key != "erratum_sha256"})
    return value


class V27Fixture(V26Fixture):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.erratum = _q5_erratum()
        erratum_path = self.inputs / "q5-lds0-attribution-erratum-v1.json"
        raw = server._canonical_json_bytes(self.erratum) + b"\n"
        erratum_path.write_bytes(raw)
        erratum_input = {
            "path": str(erratum_path),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        self.input_rows["q5_lds0_attribution_erratum"] = erratum_input
        self.config["schema"] = "epyc.autokernel.discovery_deployment.v6"
        self.config["immutable_inputs"][
            "q5_lds0_attribution_erratum"] = erratum_input
        self.graph["schema"] = "epyc.autokernel.static_discovery_graph.v9"
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
        self.write()

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
        identity = {
            "source_commit": "9" * 40,
            "source_sha256": "1" * 64,
            "binary_sha256": "2" * 64,
            "hip_library_sha256": "3" * 64,
            "config_sha256": "4" * 64,
            "linkage_sha256": "5" * 64,
        }
        anchor_identity = {**identity, "binary_sha256": "6" * 64}
        path_fields = {
            key: None for key in server._DISCOVERY_POSTBUILD_PATH_FIELDS}
        path_fields.update(anchor_build=str(anchor_build),
                           candidate_build=str(candidate_build))
        scalar_fields = {
            key: None for key in server._DISCOVERY_POSTBUILD_SCALAR_FIELDS}
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
        policy = {
            "schema": "epyc.autokernel.gpu_source_execution_policy.v2",
            "manifest_sha256": "6" * 64,
            "candidate_build_identity": identity,
            "anchor_build_identity": anchor_identity,
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
                lease={"admitted": False, "reason": "device_busy",
                       "operation_key": "a" * 64})
            state = _seal(state, "state_sha256")
            projected = server._discovery_v27_state_contract(state, contract)
            self.assertEqual(projected["resource_wait"], {
                "kind": "prebuild_resource_wait",
                "operation_key": "a" * 64,
                "reason": "device_busy",
                "completed_builds_preserved": False,
                "evidence_policy_bound": False,
            })

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
