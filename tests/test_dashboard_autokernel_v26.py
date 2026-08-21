from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from dashboard import server


def _seal(value: dict, key: str) -> dict:
    value = copy.deepcopy(value)
    value[key] = server._discovery_controller_state_hash({
        name: item for name, item in value.items() if name != key})
    return value


def _frozen(fixture: "V26Fixture") -> ExitStack:
    stack = ExitStack()
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V26_EXECUTION_MODULE_SHA256",
        {role: row["sha256"] for role, row in fixture.modules.items()}))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V26_PRODUCER_COMMIT", "a" * 40))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V26_DEPLOYMENT_SEMANTIC_SHA256",
        fixture.config["config_sha256"]))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V26_DEPLOYMENT_FILE_SHA256",
        hashlib.sha256(fixture.config_path.read_bytes()).hexdigest()))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V26_GRAPH_SHA256",
        fixture.graph["graph_sha256"]))
    stack.enter_context(mock.patch.object(
        server, "_DISCOVERY_V26_GRAPH_FILE_SHA256",
        hashlib.sha256(
            (fixture.state / "deployment-graph.json").read_bytes()).hexdigest()))
    return stack


class V26Fixture:
    def __init__(self, root: Path) -> None:
        self.bundle = root / "gpu-discovery-v26-fixture"
        self.config_dir = self.bundle / "config"
        self.inputs = self.bundle / "inputs"
        self.state = self.bundle / "state"
        for path in (self.config_dir, self.inputs, self.state,
                     self.bundle / "evidence", self.bundle / "operations",
                     self.bundle / "build"):
            path.mkdir(parents=True, mode=0o700)
        self.carrier = _seal({
            "schema": "epyc.autokernel.preauthored_source_continuation.v1",
            "hypothesis_id": "akh-v2-q5-onewave-preauthored",
            "source": {}, "historical_candidate": {"commit": "9" * 40},
            "patch": {"sha256": "5" * 64,
                      "source_backed_sha256": "b" * 64},
            "compatibility_bridge": {}, "experiment_intent": {},
            "historical_receipts": [], "correctness_policy": {},
        }, "carrier_sha256")
        self.input_rows = {}
        for name in (
                "model", "workload", "runtime_config",
                "hypothesis_portfolio", "hypothesis_evidence_manifest",
                "hypothesis_portfolio_contract"):
            raw = f"sealed-{name}\n".encode()
            path = self.inputs / f"{name}.bin"
            path.write_bytes(raw)
            self.input_rows[name] = {
                "path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
        self.admission = _seal({
            "schema": "epyc.autokernel.gpu_load_admission_policy.v2",
            "version": "fixture-admission-v1", "examples": [], "profiles": [],
        }, "policy_sha256")
        admission_path = self.inputs / "admission_policy.json"
        admission_raw = server._canonical_json_bytes(self.admission) + b"\n"
        admission_path.write_bytes(admission_raw)
        self.input_rows["admission_policy"] = {
            "path": str(admission_path),
            "sha256": hashlib.sha256(admission_raw).hexdigest(),
        }
        carrier_path = self.inputs / "preauthored.json"
        carrier_raw = server._canonical_json_bytes(self.carrier) + b"\n"
        carrier_path.write_bytes(carrier_raw)
        self.input_rows["preauthored_continuation"] = {
            "path": str(carrier_path),
            "sha256": hashlib.sha256(carrier_raw).hexdigest(),
        }
        self.planner = {
            key: [] for key in server._DISCOVERY_V26_PLANNER_KEYS}
        self.planner.update({
            "schema": "epyc.autokernel.discovery_planner_context.v4",
            "model_sha256": self.input_rows["model"]["sha256"],
            "workload_sha256": self.input_rows["workload"]["sha256"],
            "runtime_config_sha256": self.input_rows["runtime_config"]["sha256"],
            "source_constraints": {}, "template_symbol_authority": {},
            "template_surfaces": {}, "portfolio_dispatch_authority": {},
            "hypothesis_evidence": [],
            "hypothesis_portfolio_sha256": "c" * 64,
            "hypothesis_evidence_manifest_sha256": "d" * 64,
            "reviewed_source_package_sha256": "e" * 64,
            "template_registry_sha256": "f" * 64,
            "template_surfaces_sha256": server._discovery_controller_state_hash({}),
            "preauthored_continuation_sha256": self.carrier["carrier_sha256"],
            "preauthored_source_backed_diff_sha256": "b" * 64,
            "preauthored_historical_evidence_sha256": "a" * 64,
        })
        self.config = {
            "schema": "epyc.autokernel.discovery_deployment.v5",
            "production": {"path": "/production", "branch": "production-v9",
                           "head": "1" * 40},
            "instrument": {"repo_path": "/instrument", "branch": "instrument",
                           "commit": "2" * 40, "production_ancestor": "1" * 40},
            "controller": {
                "state_root": str(self.state),
                "evidence_root": str(self.bundle / "evidence"),
                "operations_root": str(self.bundle / "operations"),
                "build_root": str(self.bundle / "build"),
                "max_iterations": 10, "nomination_threshold": 0.01,
            },
            "actors": {"wrapper_path": "/actor", "wrapper_sha256": "3" * 64,
                       "critic_path": "/critic", "critic_sha256": "4" * 64,
                       "environment_profile_id": "safe"},
            "gpu": {"device_id": "mi210_0", "claim_timeout_s": 0,
                    "inference_window_lock": "/lock",
                    "inference_window_lease_id": "lease"},
            "immutable_inputs": self.input_rows,
            "source_plan": {
                "source_builder_id": "builder", "evidence_plan_id": "evidence",
                "runner_args_id": "runner",
                "experiment_template_registry_id": "templates",
                "experiment_template_registry_sha256": "f" * 64,
                "production_snapshot_id": "snapshot",
            },
        }
        self.modules = {
            role: {"logical_path": logical_path,
                   "sha256": hashlib.sha256(role.encode()).hexdigest()}
            for role, logical_path in
            server._SUPERVISOR_GRAPH_EXECUTION_MODULES_V4_V26.items()}
        reward = [{"route_id": f"q5.reward.{index}", "calls": count,
                   "grid": grid, "workgroup": 128, "lds_bytes": 1024,
                   "kernel_name": f"q5_kernel_{index}"}
                  for index, (count, grid) in enumerate(
                      ((6063, 57344), (4644, 8192), (3096, 311296)))]
        tail = {"route_id": "q5.structural.tail", "calls": 129,
                "grid": 57344, "workgroup": 128, "lds_bytes": 512}
        surfaces = {"cuda-mmvq-q5-onewave-continuation-v1": {
            "source_files": ["ggml/src/ggml-cuda/mmvq.cu"],
            "source_symbols": ["calc_nwarps"],
            "change_classes": ["dispatcher"],
            "dispatch_signatures": [{
                key: row[key] for key in (
                    "route_id", "calls", "grid", "workgroup", "lds_bytes")}
                for row in reward],
            "excluded_signatures": [tail],
        }}
        dispatch = {"akh-v2-q5-onewave-preauthored": reward}
        self.graph = {
            key: {} for key in server._DISCOVERY_V26_GRAPH_KEYS}
        self.graph.update({
            "schema": "epyc.autokernel.static_discovery_graph.v7",
            "authority": "nonpromotable_candidate_only_discovery",
            "promotion_claim": False, "inference_executed": False,
            "template_registry_sha256": "f" * 64,
            "template_surfaces": surfaces,
            "template_surfaces_sha256":
                server._discovery_controller_state_hash(surfaces),
            "portfolio_dispatch_authority": dispatch,
            "portfolio_dispatch_authority_sha256":
                server._discovery_controller_state_hash(dispatch),
            "execution_modules": self.modules,
            "hypothesis_portfolio": {
                "semantic_sha256": "c" * 64,
                "file_sha256": self.input_rows[
                    "hypothesis_portfolio"]["sha256"],
                "evidence_manifest_sha256": "d" * 64,
                "contract_sha256": self.input_rows[
                    "hypothesis_portfolio_contract"]["sha256"],
            },
            "carry_forward_sha256": "0" * 64,
            "preauthored_continuation": {
                "schema": self.carrier["schema"],
                "carrier_sha256": self.carrier["carrier_sha256"],
                "file_sha256": self.input_rows[
                    "preauthored_continuation"]["sha256"],
                "hypothesis_id": self.carrier["hypothesis_id"],
                "template_id": "cuda-mmvq-q5-onewave-continuation-v1",
                "patch_sha256": "5" * 64,
                "source_backed_diff_sha256": "b" * 64,
                "historical_evidence_sha256": "a" * 64,
                "historical_correctness_authority": "provenance_only",
                "modern_governed_correctness_required": True,
            },
        })
        self.carrier["experiment_intent"] = {
            "template_id": "cuda-mmvq-q5-onewave-continuation-v1"}
        self.carrier = _seal(self.carrier, "carrier_sha256")
        carrier_raw = server._canonical_json_bytes(self.carrier) + b"\n"
        carrier_path.write_bytes(carrier_raw)
        self.input_rows["preauthored_continuation"]["sha256"] = (
            hashlib.sha256(carrier_raw).hexdigest())
        self.planner["preauthored_continuation_sha256"] = (
            self.carrier["carrier_sha256"])
        self.graph["preauthored_continuation"]["carrier_sha256"] = (
            self.carrier["carrier_sha256"])
        self.graph["preauthored_continuation"]["file_sha256"] = (
            self.input_rows["preauthored_continuation"]["sha256"])
        self.write()

    def write(self) -> None:
        self.planner = _seal(self.planner, "context_sha256")
        planner_path = self.inputs / "planner.json"
        planner_raw = server._canonical_json_bytes(self.planner) + b"\n"
        planner_path.write_bytes(planner_raw)
        self.config["planner_context"] = {
            "path": str(planner_path),
            "sha256": hashlib.sha256(planner_raw).hexdigest(),
        }
        self.config = _seal(self.config, "config_sha256")
        config_path = self.config_dir / "deployment.json"
        config_path.write_bytes(server._canonical_json_bytes(self.config) + b"\n")
        self.graph["config_sha256"] = self.config["config_sha256"]
        self.graph = _seal(self.graph, "graph_sha256")
        (self.state / "deployment-graph.json").write_text(
            json.dumps(self.graph, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")

    @property
    def config_path(self) -> Path:
        return self.config_dir / "deployment.json"

    def checkpoint(self) -> tuple[dict, dict]:
        authority = _seal({
            "schema": "epyc.autokernel.preauthored_checkpoint.v1",
            "hypothesis_id": "akh-v2-q5-onewave-preauthored",
            "authoring_turn": 1,
            "carrier_sha256": self.carrier["carrier_sha256"],
            "source_backed_diff_sha256": "b" * 64,
            "source_manifest_sha256": "6" * 64,
            "candidate_semantic_sha256": "7" * 64,
            "cross_campaign_candidate_sha256": "8" * 64,
            "origin": "import", "author": "reviewed-eb26918-continuation",
            "historical_commit": "9" * 40,
            "modern_governed_correctness_required": True,
        }, "receipt_sha256")
        row = {
            "turn": 1, "authoring_turn": 1,
            "hypothesis_id": authority["hypothesis_id"],
            "preauthored_continuation": authority,
            "hypothesis_origin": "import",
            "hypothesis_author": "reviewed-eb26918-continuation",
            "historical_correctness_authority": "provenance_only",
            "modern_governed_correctness_required": True,
            "source_manifest_sha256": "6" * 64,
            "candidate_semantic_sha256": "7" * 64,
        }
        pending = {
            "phase": "preauthored_ready", "row": row,
            "candidate": {"hypothesis_id": authority["hypothesis_id"],
                          "source_manifest_sha256": "6" * 64},
            "preauthored_continuation": authority,
            "context": {},
            "context_sha256": server._discovery_controller_state_hash({}),
            "confirmation": False, "parent_authorization": None,
        }
        state = _seal({
            "schema": "epyc.autokernel.discovery_controller.v7",
            "authority": "nonpromotable_candidate_only_discovery",
            "roster": copy.deepcopy(server._DISCOVERY_V26_ROSTER),
            "iterations": [], "next": 1, "scientific_attempts": 0,
            "complete": False, "pending": pending,
            "deployment_identity_sha256": self.config["config_sha256"],
            "planner_context_sha256": server._discovery_content_hash({
                "planner_context_sha256": self.planner["context_sha256"],
                "admission_policy_sha256": self.admission["policy_sha256"],
                "admission_policy_version": self.admission["version"],
                "deployment_identity_sha256": self.config["config_sha256"],
            }),
            "experiment_template_registry_sha256": "f" * 64,
            "admission_corpus_sha256": self.admission["policy_sha256"],
            "admission_corpus_version": self.admission["version"],
            "hypothesis_portfolio_sha256": "c" * 64,
            "carry_forward_sha256": "0" * 64,
            "preauthored_continuation_sha256": self.carrier["carrier_sha256"],
            "preauthored_source_backed_diff_sha256": "b" * 64,
            "updated_at": "2026-08-21T12:00:00Z",
        }, "state_sha256")
        return state, authority

    def write_journal(self, states: list[tuple[str, str]],
                      *, start_at: str = "2026-08-21T12:00:00Z") -> Path:
        journal = self.state / "journal"
        journal.mkdir(mode=0o700, exist_ok=True)
        rows = []
        for seq, (name, digest) in enumerate(states, 1):
            payload = {"state": name, "controller_state_sha256": digest}
            rows.append({
                "journal_schema": "epyc.autokernel.journal_entry.v1",
                "event_id": (
                    f"akj-{seq:012d}-"
                    f"{server._discovery_content_hash(payload)[:12]}"),
                "seq": seq, "kind": "STOP_STATE", "campaign_id": None,
                "record_id": None, "written_at": start_at,
                "payload": payload,
            })
        path = journal / "events.jsonl"
        path.write_bytes(b"".join(
            server._canonical_json_bytes(row) + b"\n" for row in rows))
        return path


class DashboardAutokernelV26Tests(unittest.TestCase):
    def test_frozen_v26_product_authority_is_exact(self) -> None:
        self.assertEqual(
            server._DISCOVERY_V26_PRODUCER_COMMIT,
            "915f4ce5d38713b59545035d17e4a730214b5db1")
        self.assertEqual(
            server._DISCOVERY_V26_GRAPH_SHA256,
            "20dec69b26c84dbdf7f97b92e39349437df9c28a10300fed210752070e0a2e4c")
        self.assertEqual(
            server._DISCOVERY_V26_DEPLOYMENT_SEMANTIC_SHA256,
            "03fc1b1230487a35f8aefd843a546da9324361ee462d945bc076ef89263d2b89")
        self.assertEqual(
            server._DISCOVERY_V26_DEPLOYMENT_FILE_SHA256,
            "53a5f35f42baba05bc0a3c72741737f7d30583d8a3435078ee9edae59661bb5f")
        self.assertEqual(
            server._DISCOVERY_V26_GRAPH_FILE_SHA256,
            "ef35a550a96bdc8b9cd089097c216078a1b5b8fa842df746d975592fd6ad6075")
        self.assertEqual(
            set(server._DISCOVERY_V26_EXECUTION_MODULE_SHA256),
            set(server._SUPERVISOR_GRAPH_EXECUTION_MODULES_V4_V26))
        self.assertEqual(
            len(server._DISCOVERY_V26_EXECUTION_MODULE_SHA256), 30)
        self.assertTrue(all(server._discovery_sha256(value) for value in
                            server._DISCOVERY_V26_EXECUTION_MODULE_SHA256.values()))

    def test_exact_v26_graph_state_and_safe_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V26Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v26_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            self.assertIsNotNone(contract)
            self.assertIs(contract["ready"], True)
            self.assertEqual(contract["structural_tail"], {
                "exact_validation": True, "reward_excluded": True,
                "route_id": "q5.structural.tail", "calls": 129,
            })
            state, _authority = fixture.checkpoint()
            state_contract = server._discovery_v26_state_contract(
                state, contract)
            self.assertEqual(state_contract["scientific_attempts"], 0)
            self.assertIs(state_contract["provenance"]["actor_bypass"], True)

            activity = server._discovery_activity(
                lock_held=True, campaign_id="ak-discovery-" + "a" * 16,
                state=state, events=[], checkpoint={
                    "state": "discovery_preauthored_checkpointed", "seq": 1,
                    "written_at": "2026-08-21T12:00:00Z"},
                terminal_observation=None, operation_observation=None,
                correctness_observation=None, postbuild_observation=None,
                claim_observation=None, refusal_observation=None,
                refusal_history_observations=[], now=1_787_313_601.0,
                v26_contract=contract, v26_state=state_contract)
            self.assertEqual(activity["phase"]["id"], "authorization")
            self.assertIn("actors bypassed", activity["phase"]["label"])
            stages = {row["id"]: row for row in activity["pipeline"]}
            self.assertEqual(stages["planner"]["state"], "complete")
            self.assertEqual(stages["critic"]["state"], "complete")
            self.assertIs(activity["preauthored"]["imported"], True)
            self.assertEqual(activity["scientific_attempts"], 0)

    def test_v26_wrong_frozen_authority_does_not_become_live(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V26Fixture(Path(directory))
            contract = server._discovery_v26_contract(
                fixture.config_path, fixture.config, fixture.bundle)
            self.assertIsNotNone(contract)
            self.assertIs(contract["ready"], False)
            self.assertIsNone(contract["producer_commit"])

    def test_live_projection_selects_only_frozen_v26_and_exports_bounded_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = V26Fixture(root)
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
            self.assertEqual(payload["deployment"], fixture.bundle.name)
            self.assertEqual(payload["activity"]["phase"]["id"], "authorization")
            self.assertEqual(payload["state"]["scientific_attempts"], 0)
            self.assertIs(payload["activity"]["preauthored"]["actor_bypass"], True)
            self.assertEqual(payload["discovery_product_contract"], {
                "deployment_schema":
                    "epyc.autokernel.discovery_deployment.v5",
                "planner_schema":
                    "epyc.autokernel.discovery_planner_context.v4",
                "graph_schema": "epyc.autokernel.static_discovery_graph.v7",
                "graph_sha256": fixture.graph["graph_sha256"],
                "producer_commit": "a" * 40,
            })
            encoded = json.dumps(payload, sort_keys=True)
            for forbidden in (
                    "source_backed_base64", "historical_receipts", "patch_base64",
                    str(fixture.inputs), "process_start_ticks", "holder_pid"):
                self.assertNotIn(forbidden, encoded)

            journal_path = fixture.state / "journal" / "events.jsonl"
            journal_row = json.loads(journal_path.read_text(encoding="utf-8"))
            journal_row["payload"]["controller_state_sha256"] = "0" * 64
            journal_path.write_text(
                json.dumps(journal_row, sort_keys=True) + "\n",
                encoding="utf-8")
            with mock.patch.object(
                    server, "AUTOKERNEL_DEPLOYMENTS_ROOT", root), \
                    _frozen(fixture), \
                    mock.patch.object(
                        server, "_discovery_lock_held", return_value=True):
                refused, _ = server._discovery_live_read()
            self.assertIs(refused["available"], False)

    def test_v26_journal_requires_exact_canonical_contiguous_envelopes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V26Fixture(Path(directory))
            path = fixture.write_journal([
                ("discovery_planner_transient", "1" * 64),
                ("discovery_planner_intent", "2" * 64),
            ])
            checkpoint = server._discovery_v26_checkpoint(
                path, now=1_787_313_601.0)
            self.assertEqual(checkpoint["seq"], 2)
            self.assertEqual(checkpoint["controller_state_sha256"], "2" * 64)
            valid_rows = [json.loads(line) for line in path.read_text().splitlines()]

            def write_rows(rows: list[dict], *, canonical: bool = True,
                           newline: bool = True) -> None:
                encoded = b"\n".join(
                    server._canonical_json_bytes(row) if canonical else
                    json.dumps(row, indent=2).encode()
                    for row in rows)
                path.write_bytes(encoded + (b"\n" if newline else b""))

            mutations = {}
            missing = copy.deepcopy(valid_rows)
            missing[0].pop("record_id")
            mutations["missing envelope key"] = (missing, True, True)
            extra = copy.deepcopy(valid_rows)
            extra[0]["unexpected"] = True
            mutations["extra envelope key"] = (extra, True, True)
            gap = copy.deepcopy(valid_rows)
            gap[1]["seq"] = 3
            mutations["sequence gap"] = (gap, True, True)
            forged = copy.deepcopy(valid_rows)
            forged[1]["event_id"] = "akj-000000000002-deadbeefdead"
            mutations["event identity"] = (forged, True, True)
            payload_extra = copy.deepcopy(valid_rows)
            payload_extra[1]["payload"]["unexpected"] = True
            payload_extra[1]["event_id"] = (
                "akj-000000000002-" +
                server._discovery_controller_state_hash(
                    payload_extra[1]["payload"])[:12])
            mutations["payload grammar"] = (payload_extra, True, True)
            mutations["noncanonical bytes"] = (
                copy.deepcopy(valid_rows), False, True)
            mutations["torn tail"] = (copy.deepcopy(valid_rows), True, False)
            future = copy.deepcopy(valid_rows)
            future[1]["written_at"] = "2099-01-01T00:00:00Z"
            mutations["future timestamp"] = (future, True, True)
            unknown_phase = copy.deepcopy(valid_rows)
            unknown_phase[1]["payload"]["state"] = "discovery_forged"
            unknown_phase[1]["event_id"] = (
                "akj-000000000002-" + server._discovery_content_hash(
                    unknown_phase[1]["payload"])[:12])
            mutations["unknown producer phase"] = (
                unknown_phase, True, True)
            for label, (rows, canonical, newline) in mutations.items():
                with self.subTest(label=label):
                    write_rows(rows, canonical=canonical, newline=newline)
                    self.assertIsNone(server._discovery_v26_checkpoint(
                        path, now=1_787_313_601.0))

    def test_planner_transients_do_not_advance_scientific_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V26Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v26_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, _ = fixture.checkpoint()
            state.pop("pending")
            transient = {
                "turn": 1, "status": "planner_transient",
                "reason": "provider unavailable",
                "refusal_type": "planner_provider_transient",
                "scientific_budget_spent": False,
                "context_sha256": "1" * 64,
                "planner_operation_key": "2" * 64,
            }
            state.update(iterations=[transient], next=1,
                         planner_provider_attempt=1)
            state = _seal(state, "state_sha256")
            projected = server._discovery_v26_state_contract(state, contract)
            self.assertEqual(projected["scientific_attempts"], 0)

            second = copy.deepcopy(transient)
            second["planner_operation_key"] = "3" * 64
            repeated = copy.deepcopy(state)
            repeated["iterations"] = [transient, second, {
                "turn": 1, "status": "planner_refused",
                "reason": "malformed actor output",
                "refusal_type": "planner_output_refusal",
                "scientific_budget_spent": False,
                "telemetry_event": "planner_refused",
                "telemetry_status": "emitted",
                "planner_operation_key": "4" * 64}]
            repeated["next"] = 2
            repeated["planner_provider_attempt"] = 2
            repeated = _seal(repeated, "state_sha256")
            self.assertIsNotNone(server._discovery_v26_state_contract(
                repeated, contract))

            mutations = {
                "future turn": lambda value: value["iterations"][0].update(turn=2),
                "provider count": lambda value: value.update(
                    planner_provider_attempt=0),
                "cursor advanced": lambda value: value.update(next=2),
                "telemetry spoof": lambda value: value["iterations"][0].update(
                    telemetry_event="planner_refused"),
                "wrong refusal": lambda value: value["iterations"][0].update(
                    refusal_type="planner_output_refusal"),
            }
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    changed = copy.deepcopy(state)
                    mutate(changed)
                    changed = _seal(changed, "state_sha256")
                    self.assertIsNone(server._discovery_v26_state_contract(
                        changed, contract))
            duplicate = copy.deepcopy(state)
            duplicate["iterations"] = [transient, copy.deepcopy(transient)]
            duplicate["planner_provider_attempt"] = 2
            duplicate = _seal(duplicate, "state_sha256")
            self.assertIsNone(server._discovery_v26_state_contract(
                duplicate, contract))

    def test_preauthored_pending_lifecycle_variants_remain_visible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V26Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v26_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            initial, _ = fixture.checkpoint()
            variants = {"preauthored_ready": initial}

            waiting = copy.deepcopy(initial)
            pending = waiting["pending"]
            pending.pop("phase"); pending.pop("context"); pending.pop("context_sha256")
            pending.update(authorization={}, infrastructure_retry_epoch=0)
            pending["row"].update(
                status="waiting_resource", lease={}, operation_key="a" * 64)
            variants["waiting_resource"] = _seal(waiting, "state_sha256")

            ambiguity = copy.deepcopy(waiting)
            pending = ambiguity["pending"]
            pending["infrastructure_retry_epoch"] = 1
            pending["prior_operation_key"] = "b" * 64
            pending["row"].pop("status"); pending["row"].pop("lease")
            pending["row"].update(
                source_manifest_sha256="6" * 64,
                candidate_semantic_sha256="7" * 64)
            ambiguity["infrastructure_ambiguities"] = [{
                "schema": "epyc.autokernel.screen_infrastructure_ambiguity.v1",
                "operation_key": "b" * 64,
                "source_manifest_sha256": "6" * 64,
                "candidate_semantic_sha256": "7" * 64,
                "stage_receipt_path": "/private/receipt.json",
                "stage_receipt_sha256": "c" * 64,
                "reason_sha256": "d" * 64, "retry_epoch": 0,
            }]
            variants["ambiguity_retry"] = _seal(ambiguity, "state_sha256")

            s2 = copy.deepcopy(initial)
            pending = s2["pending"]
            pending.pop("phase"); pending.pop("context"); pending.pop("context_sha256")
            pending["confirmation"] = True
            pending["parent_authorization"] = {}
            pending["row"]["status"] = "replication_pending"
            variants["replication_s2"] = _seal(s2, "state_sha256")

            for label, state in variants.items():
                with self.subTest(label=label):
                    projected = server._discovery_v26_state_contract(
                        state, contract)
                    self.assertIs(projected["provenance"]["actor_bypass"], True)
                    activity = server._discovery_activity(
                        lock_held=True,
                        campaign_id="ak-discovery-" + "a" * 16,
                        state=state, events=[], checkpoint={
                            "state": "discovery_" + label, "seq": 1,
                            "written_at": "2026-08-21T12:00:00Z"},
                        terminal_observation=None, operation_observation=None,
                        correctness_observation=None,
                        postbuild_observation=None, claim_observation=None,
                        refusal_observation=None,
                        refusal_history_observations=[],
                        now=1_787_313_601.0,
                        v26_contract=contract, v26_state=projected)
                    stages = {row["id"]: row for row in activity["pipeline"]}
                    self.assertEqual(stages["planner"]["state"], "complete")
                    self.assertEqual(stages["critic"]["state"], "complete")
                    self.assertIs(activity["preauthored"]["actor_bypass"], True)
                    self.assertIn(
                        "actor bypassed", stages["planner"].get("detail", ""))

            malformed = copy.deepcopy(variants["ambiguity_retry"])
            malformed["pending"]["infrastructure_retry_epoch"] = 2
            malformed = _seal(malformed, "state_sha256")
            self.assertIsNone(server._discovery_v26_state_contract(
                malformed, contract))

            ambiguity_mutations = {
                "empty receipt path": lambda value: value[
                    "infrastructure_ambiguities"][0].update(
                        stage_receipt_path=""),
                "duplicate operation": lambda value: value[
                    "infrastructure_ambiguities"].append(copy.deepcopy(
                        value["infrastructure_ambiguities"][0])),
                "epoch gap": lambda value: value[
                    "infrastructure_ambiguities"][0].update(retry_epoch=1),
                "malformed earlier row": lambda value: value[
                    "infrastructure_ambiguities"].insert(0, {
                        **copy.deepcopy(value["infrastructure_ambiguities"][0]),
                        "operation_key": "e" * 64,
                        "stage_receipt_path": "",
                    }),
            }
            for label, mutate in ambiguity_mutations.items():
                with self.subTest(ambiguity=label):
                    changed = copy.deepcopy(variants["ambiguity_retry"])
                    mutate(changed)
                    changed = _seal(changed, "state_sha256")
                    self.assertIsNone(server._discovery_v26_state_contract(
                        changed, contract))

    def test_v26_state_exact_grammar_holders_terminal_and_budget(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V26Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v26_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, _ = fixture.checkpoint()

            terminal = copy.deepcopy(state)
            terminal.pop("pending")
            terminal.update(complete=True, terminal_reason="portfolio_exhausted")
            terminal = _seal(terminal, "state_sha256")
            self.assertIsNotNone(server._discovery_v26_state_contract(
                terminal, contract))

            mutations = {
                "missing complete": lambda value: value.pop("complete"),
                "missing roster": lambda value: value.pop("roster"),
                "changed roster": lambda value: value["roster"].update(
                    member_count=3),
                "unknown top key": lambda value: value.update(
                    raw_secret="must-not-project"),
                "pending plus inflight": lambda value: value.update(
                    inflight={"phase": "forged"}),
                "pending plus planning": lambda value: value.update(
                    planning={"phase": "forged"}),
                "explicit null inflight": lambda value: value.update(
                    inflight=None),
                "complete plus pending": lambda value: value.update(
                    complete=True, terminal_reason="portfolio_exhausted"),
                "terminal while incomplete": lambda value: value.update(
                    terminal_reason="portfolio_exhausted"),
                "budget above authority": lambda value: value.update(
                    scientific_attempts=contract["max_iterations"] + 1),
                "missing planner link": lambda value: value.pop(
                    "planner_context_sha256"),
                "changed admission link": lambda value: value.update(
                    admission_corpus_sha256="0" * 64),
                "future state timestamp": lambda value: value.update(
                    updated_at="2099-01-01T00:00:00Z"),
            }
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    changed = copy.deepcopy(state)
                    mutate(changed)
                    changed = _seal(changed, "state_sha256")
                    self.assertIsNone(server._discovery_v26_state_contract(
                        changed, contract))

    def test_coherently_rehashed_graph_mutations_fail_closed(self) -> None:
        def promote_structural_tail(fixture: V26Fixture) -> None:
            surface = fixture.graph["template_surfaces"][
                "cuda-mmvq-q5-onewave-continuation-v1"]
            structural = copy.deepcopy(surface["excluded_signatures"][0])
            reward = {**structural, "kernel_name": "structural_tail_promoted"}
            fixture.graph["portfolio_dispatch_authority"][
                "akh-v2-q5-onewave-preauthored"].append(reward)
            surface["dispatch_signatures"].append(structural)

        mutations = {
            "role path swap": lambda fixture: fixture.graph[
                "execution_modules"]["preauthored_continuation"].update(
                    logical_path=fixture.graph["execution_modules"][
                        "hypothesis_portfolio"]["logical_path"]),
            "structural tail missing": lambda fixture: fixture.graph[
                "template_surfaces"][
                    "cuda-mmvq-q5-onewave-continuation-v1"].update(
                        excluded_signatures=[]),
            "tail promoted into reward": promote_structural_tail,
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                fixture = V26Fixture(Path(directory))
                mutate(fixture)
                if label == "tail promoted into reward":
                    fixture.graph["portfolio_dispatch_authority_sha256"] = (
                        server._discovery_controller_state_hash(
                            fixture.graph["portfolio_dispatch_authority"]))
                    fixture.graph["template_surfaces_sha256"] = (
                        server._discovery_controller_state_hash(
                            fixture.graph["template_surfaces"]))
                if label == "structural tail missing":
                    fixture.graph["template_surfaces_sha256"] = (
                        server._discovery_controller_state_hash(
                            fixture.graph["template_surfaces"]))
                fixture.write()
                self.assertIsNone(server._discovery_v26_contract(
                    fixture.config_path, fixture.config, fixture.bundle))

    def test_state_counter_and_imported_join_mutations_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = V26Fixture(Path(directory))
            with _frozen(fixture):
                contract = server._discovery_v26_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, _ = fixture.checkpoint()
            wrong_count = copy.deepcopy(state)
            wrong_count.pop("pending")
            science_row = {
                "turn": 1, "status": "candidate",
                "hypothesis_id": "akh-v2-q5-onewave-preauthored",
                "portfolio_hypothesis_id":
                    "akh-v2-q5-onewave-preauthored",
                "proposal_sha256": "1" * 64,
                "source_manifest_sha256": "6" * 64,
                "candidate_semantic_sha256": "7" * 64,
                "portfolio_record_sha256": "2" * 64,
                "portfolio_binding": {}, "portfolio_decision_policy": {},
                "operation_key": "3" * 64,
                "result_sha256": "4" * 64,
                "evidence": {"baseline": "5" * 64, "source": "6" * 64,
                             "dispatch": "7" * 64},
                "effect_fraction": 0.1, "series_effect_fraction": 0.1,
                "series_key": "8" * 64,
                "component_series_keys": ["9" * 64],
                "exact_attribution_effect_fraction": 0.1,
                "target_runtime_effect_fraction": 0.1,
                "target_runtime_executed": True,
                "target_runtime_reason": None,
                "stages": [], "repetition": 1,
                "scientific_budget_spent": True,
            }
            wrong_count["iterations"] = [science_row]
            wrong_count["next"] = 2
            wrong_count["scientific_attempts"] = 2
            wrong_count["candidate_semantic_registry_schema"] = (
                "epyc.autokernel.candidate_semantic_registry.v1")
            wrong_count["attempted_candidate_identities"] = {
                "7" * 64: {
                    "hypothesis_id": "akh-v2-q5-onewave-preauthored",
                    "attempts": [{"operation_key": "3" * 64,
                                  "result_sha256": "4" * 64,
                                  "disposition": "candidate",
                                  "repetition": 1}],
                }}
            wrong_count = _seal(wrong_count, "state_sha256")
            self.assertIsNone(server._discovery_v26_state_contract(
                wrong_count, contract))

            exact_count = copy.deepcopy(wrong_count)
            exact_count["scientific_attempts"] = 1
            exact_count = _seal(exact_count, "state_sha256")
            projected = server._discovery_v26_state_contract(
                exact_count, contract)
            self.assertEqual(projected["scientific_attempts"], 1)

            bare_boolean = copy.deepcopy(exact_count)
            bare_boolean["iterations"] = [{
                "turn": 1, "status": "candidate",
                "scientific_budget_spent": True}]
            bare_boolean.pop("candidate_semantic_registry_schema")
            bare_boolean.pop("attempted_candidate_identities")
            bare_boolean = _seal(bare_boolean, "state_sha256")
            self.assertIsNone(server._discovery_v26_state_contract(
                bare_boolean, contract))

            nested_secret = copy.deepcopy(exact_count)
            nested_secret["iterations"][0]["raw_secret"] = "must-not-project"
            nested_secret = _seal(nested_secret, "state_sha256")
            self.assertIsNone(server._discovery_v26_state_contract(
                nested_secret, contract))

            wrong_origin = copy.deepcopy(state)
            authority = wrong_origin["pending"]["preauthored_continuation"]
            authority["origin"] = "actor"
            authority = _seal(authority, "receipt_sha256")
            wrong_origin["pending"]["preauthored_continuation"] = authority
            wrong_origin["pending"]["row"]["preauthored_continuation"] = authority
            wrong_origin["pending"]["row"]["hypothesis_origin"] = "actor"
            wrong_origin = _seal(wrong_origin, "state_sha256")
            self.assertIsNone(server._discovery_v26_state_contract(
                wrong_origin, contract))

            wrong_deployment = copy.deepcopy(state)
            wrong_deployment["deployment_identity_sha256"] = "f" * 64
            wrong_deployment = _seal(wrong_deployment, "state_sha256")
            self.assertIsNone(server._discovery_v26_state_contract(
                wrong_deployment, contract))


if __name__ == "__main__":
    unittest.main()
