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


def _seal(value: dict, key: str) -> dict:
    value = copy.deepcopy(value)
    value[key] = server._discovery_controller_state_hash({
        name: item for name, item in value.items() if name != key})
    return value


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
                "model", "workload", "runtime_config", "admission_policy",
                "hypothesis_portfolio", "hypothesis_evidence_manifest",
                "hypothesis_portfolio_contract"):
            raw = f"sealed-{name}\n".encode()
            path = self.inputs / f"{name}.bin"
            path.write_bytes(raw)
            self.input_rows[name] = {
                "path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
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
                   "grid": grid, "workgroup": 128, "lds_bytes": 1024}
                  for index, (count, grid) in enumerate(
                      ((6063, 57344), (4644, 8192), (3096, 311296)))]
        tail = {"route_id": "q5.structural.tail", "calls": 129,
                "grid": 57344, "workgroup": 128, "lds_bytes": 512}
        surfaces = {"cuda-mmvq-q5-onewave-continuation-v1": {
            "source_files": ["ggml/src/ggml-cuda/mmvq.cu"],
            "source_symbols": ["calc_nwarps"],
            "change_classes": ["dispatcher"],
            "dispatch_signatures": reward, "excluded_signatures": [tail],
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
        }
        pending = {
            "phase": "preauthored_ready", "row": row,
            "candidate": {"hypothesis_id": authority["hypothesis_id"],
                          "source_manifest_sha256": "6" * 64},
            "preauthored_continuation": authority,
        }
        state = _seal({
            "schema": "epyc.autokernel.discovery_controller.v7",
            "authority": "nonpromotable_candidate_only_discovery",
            "iterations": [], "next": 1, "scientific_attempts": 0,
            "complete": False, "pending": pending,
            "deployment_identity_sha256": self.config["config_sha256"],
            "experiment_template_registry_sha256": "f" * 64,
            "hypothesis_portfolio_sha256": "c" * 64,
            "carry_forward_sha256": "0" * 64,
        }, "state_sha256")
        return state, authority


class DashboardAutokernelV26Tests(unittest.TestCase):
    def test_frozen_v26_product_authority_is_exact(self) -> None:
        self.assertEqual(
            server._DISCOVERY_V26_PRODUCER_COMMIT,
            "915f4ce5d38713b59545035d17e4a730214b5db1")
        self.assertEqual(
            server._DISCOVERY_V26_GRAPH_SHA256,
            "72985628302b06bb1dd4fe8c7afd23595a724cf549e63b8296e779763118545b")
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
            hashes = {role: row["sha256"]
                      for role, row in fixture.modules.items()}
            with mock.patch.object(
                    server, "_DISCOVERY_V26_EXECUTION_MODULE_SHA256", hashes), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_PRODUCER_COMMIT", "a" * 40), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_GRAPH_SHA256",
                        fixture.graph["graph_sha256"]):
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
            journal = fixture.state / "journal"
            journal.mkdir(mode=0o700)
            (journal / "events.jsonl").write_text(json.dumps({
                "journal_schema": "epyc.autokernel.journal_entry.v1",
                "seq": 1, "kind": "STOP_STATE",
                "written_at": "2026-08-21T12:00:00Z",
                "payload": {
                    "state": "discovery_preauthored_checkpointed",
                    "controller_state_sha256": state["state_sha256"],
                },
            }, sort_keys=True) + "\n", encoding="utf-8")
            hashes = {role: row["sha256"]
                      for role, row in fixture.modules.items()}
            with mock.patch.object(
                    server, "AUTOKERNEL_DEPLOYMENTS_ROOT", root), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_EXECUTION_MODULE_SHA256", hashes), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_PRODUCER_COMMIT", "a" * 40), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_GRAPH_SHA256",
                        fixture.graph["graph_sha256"]), \
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
                    mock.patch.object(
                        server, "_DISCOVERY_V26_EXECUTION_MODULE_SHA256", hashes), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_PRODUCER_COMMIT", "a" * 40), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_GRAPH_SHA256",
                        fixture.graph["graph_sha256"]), \
                    mock.patch.object(
                        server, "_discovery_lock_held", return_value=True):
                refused, _ = server._discovery_live_read()
            self.assertIs(refused["available"], False)

    def test_coherently_rehashed_graph_mutations_fail_closed(self) -> None:
        mutations = {
            "role path swap": lambda fixture: fixture.graph[
                "execution_modules"]["preauthored_continuation"].update(
                    logical_path=fixture.graph["execution_modules"][
                        "hypothesis_portfolio"]["logical_path"]),
            "structural tail missing": lambda fixture: fixture.graph[
                "template_surfaces"][
                    "cuda-mmvq-q5-onewave-continuation-v1"].update(
                        excluded_signatures=[]),
            "tail promoted into reward": lambda fixture: fixture.graph[
                "portfolio_dispatch_authority"][
                    "akh-v2-q5-onewave-preauthored"].append(
                        fixture.graph["template_surfaces"][
                            "cuda-mmvq-q5-onewave-continuation-v1"
                        ]["excluded_signatures"][0]),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                fixture = V26Fixture(Path(directory))
                mutate(fixture)
                if label == "tail promoted into reward":
                    fixture.graph["portfolio_dispatch_authority_sha256"] = (
                        server._discovery_controller_state_hash(
                            fixture.graph["portfolio_dispatch_authority"]))
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
            hashes = {role: row["sha256"]
                      for role, row in fixture.modules.items()}
            with mock.patch.object(
                    server, "_DISCOVERY_V26_EXECUTION_MODULE_SHA256", hashes), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_PRODUCER_COMMIT", "a" * 40), \
                    mock.patch.object(
                        server, "_DISCOVERY_V26_GRAPH_SHA256",
                        fixture.graph["graph_sha256"]):
                contract = server._discovery_v26_contract(
                    fixture.config_path, fixture.config, fixture.bundle)
            state, _ = fixture.checkpoint()
            wrong_count = copy.deepcopy(state)
            wrong_count.pop("pending")
            wrong_count["iterations"] = [
                {"turn": 1, "scientific_budget_spent": False},
                {"turn": 2, "scientific_budget_spent": True},
                {"turn": 3, "scientific_budget_spent": False},
            ]
            wrong_count["next"] = 4
            wrong_count["scientific_attempts"] = 2
            wrong_count = _seal(wrong_count, "state_sha256")
            self.assertIsNone(server._discovery_v26_state_contract(
                wrong_count, contract))

            exact_count = copy.deepcopy(wrong_count)
            exact_count["scientific_attempts"] = 1
            exact_count = _seal(exact_count, "state_sha256")
            projected = server._discovery_v26_state_contract(
                exact_count, contract)
            self.assertEqual(projected["scientific_attempts"], 1)

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
