"""Acceptance contract for an operator-legible AutoKernel live dashboard.

The live logs are evidence, not a status display.  A controller can hold its lock
for minutes without writing another event, and a controller that dies after critic
acceptance can leave a durable inflight build record with no completed iteration.
Neither case is allowed to render as an inert wall of timestamps or generic idle.

These tests intentionally specify the operator questions the surface must answer:

* what phase is active, for how long, and is it plausibly stalled;
* what the loop is waiting on;
* whether the GPU is expected now and whether its claim is actually held;
* which transitions led here;
* whether any durable checkpoint exists and whether it authorizes resume; and
* whether a stopped controller actually failed during source materialization,
  including a concrete recovery action.

Abandoned/retest detail remains available but collapsed by default.  The live
summary and transition timeline stay above that diagnostic history.

This file used to answer those questions twice: once against ``server.py``'s
projection, and once by executing the renderers of ``dashboard/static/kernel.html``
under node.  The rendering half was retired on 2026-08-30 together with that page.
The markup it asserted against no longer exists, and a test that renders a deleted
file can only pass vacuously.  What survives below is the contract half: the
operator questions above are pinned on the shape of the discovery payload
``server.py`` projects, which the page's retirement does not touch and which any
surface rendering the loop still has to consume.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from dashboard import server


def _iso(seconds_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat(
    ).replace("+00:00", "Z")


def _event(event: str, *, seconds_ago: int, channel: str = "planner",
           model: str = "gpt-5.6-sol", provider: str = "codex",
           result: dict | None = None,
           campaign_id: str = "ak-discovery-visibility") -> dict:
    row = {
        "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
        "ts": _iso(seconds_ago),
        "channel": channel,
        "event": event,
        "campaign_id": campaign_id,
        "hypothesis_id": "akh-v2-q5-type-specific-dequant",
        "provider": provider,
        "model": model,
        "effort": "high",
    }
    if event in {"planner_completed", "planner_failed"}:
        row["result"] = {
            "returncode": 0 if event == "planner_completed" else 1,
            "stdout_sha256": "a" * 64,
            "stderr_sha256": "b" * 64,
            **(result or {}),
        }
    elif event == "critic_completed":
        row["result"] = {
            "stdout_sha256": "a" * 64,
            "stderr_sha256": "b" * 64,
            "decision": "accept",
            **(result or {}),
        }
    elif result is not None:
        row["result"] = result
    return row


def _seal(body: dict) -> dict:
    sealed = dict(body)
    sealed["receipt_sha256"] = hashlib.sha256(json.dumps(
        sealed, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return sealed


class AutoKernelVisibilityContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_root = server.AUTOKERNEL_DEPLOYMENTS_ROOT
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "deployments"
        self.bundle = root / "campaign-a"
        self.state = self.bundle / "state"
        self.operations = self.bundle / "operations"
        (self.bundle / "config").mkdir(parents=True)
        self.state.mkdir()
        (self.operations / "live").mkdir(parents=True)
        config = {
            "config_sha256": "a" * 64,
            "controller": {
                "state_root": str(self.state),
                "operations_root": str(self.operations),
            },
            "gpu": {"device_id": "mi210_0"},
        }
        (self.bundle / "config/deployment.json").write_text(json.dumps(config))
        (self.state / "controller.run.lock").touch()
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = root

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self._old_root
        self.temp.cleanup()

    def _write_events(self, rows: list[dict]) -> None:
        encoded = "".join(json.dumps(row) + "\n" for row in rows)
        (self.operations / "live/autokernel.jsonl").write_text(encoded)
        planner = [row for row in rows if row.get("channel") == "planner"]
        (self.operations / "live/planner.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in planner))

    def _private_json(self, path: Path, body: dict, *, sealed: bool = True) -> dict:
        path.parent.mkdir(parents=True, exist_ok=True)
        value = _seal(body) if sealed else dict(body)
        path.write_bytes(server._canonical_json_bytes(value) + b"\n")
        path.chmod(0o600)
        return value

    def _v24_live_process_fixture(self, *, seconds_ago: int = 30) -> dict:
        """Exact v24 owned-process/sandbox receipt prefix for a HIP build."""
        attempt = (self.operations / "build-cache/entries" / ("7" * 64) /
                   "attempts/attempt-000001")
        logs = attempt / "logs"
        writable = (self.bundle / "builds" / ("7" * 64) /
                    "attempt-000001" / "ak-discovery-aaaaaaaaaaaaaaaa" /
                    "akc-anchor")
        writable.mkdir(parents=True, exist_ok=True)
        prefix = logs / "akc-anchor.log.build"
        stream = logs / "akc-anchor.log.build.stream"
        sandbox_path = logs / "akc-anchor.log.build-sandbox.json"
        started_at = _iso(seconds_ago)
        started_epoch = server._parse_semantic_timestamp(started_at)
        cgroup_root = "/sys/fs/cgroup/epyc-autokernel-fixture-1000-0"
        argv = ["/usr/bin/cmake", "--build", str(writable), "-j", "1",
                "--target", "llama-bench", "--target", "test-backend-ops"]
        policy_document = {
            "sandbox_id": "autokernel.execution.sandbox/landlock-seccomp-cgroup-v2",
            "profile": "candidate_default_v1", "writable_root": str(writable),
            "cgroup_root": cgroup_root, "writable_device_paths": [],
            "readable_roots": [], "readable_files": [], "executable_files": [],
            "broker_socket_path": None, "broker_peer_pid": None,
            "broker_peer_start_ticks": None, "read_allowlist_enforced": False,
            "network_profile": "deny_all",
            "blocked_syscalls": sorted(server._DISCOVERY_SANDBOX_BLOCKED),
            "deny_unix_socket_creation": False,
            "resource_limits": server._DISCOVERY_SANDBOX_LIMITS,
        }
        policy_sha = hashlib.sha256(
            server._canonical_json_bytes(policy_document)).hexdigest()
        intent = self._private_json(prefix.with_name(
            prefix.name + "-process-intent.json"), {
                "schema": "epyc.autokernel.owned_process_intent.v1",
                "argv": argv, "epoch_token": "e" * 64,
                "stdout_path": str(stream),
                "sandbox_receipt_path": str(sandbox_path),
                "sandbox_policy_sha256": policy_sha,
                "sandbox_token": "1" * 16, "cgroup_root": cgroup_root,
            })
        intent_raw = server._canonical_json_bytes(intent) + b"\n"
        start = self._private_json(prefix.with_name(
            prefix.name + "-process-start.json"), {
                "schema": "epyc.autokernel.owned_process_start.v1",
                "intent_receipt_sha256": hashlib.sha256(intent_raw).hexdigest(),
                "epoch_token": "e" * 64, "argv": argv, "pid": 424242,
                "pgid": 424242, "process_start_ticks": 987654,
                "started_at": started_at, "stdout_path": str(stream),
                "sandbox_receipt_path": str(sandbox_path),
            })
        argv_sha = hashlib.sha256(json.dumps(
            argv, separators=(",", ":")).encode()).hexdigest()
        self._private_json(sandbox_path, {
            "schema": "epyc.autokernel.sandbox_receipt.v2",
            "sandbox_id": "autokernel.execution.sandbox/landlock-seccomp-cgroup-v2",
            "pid": 424242, "process_start_ticks": 987654,
            "euid": os.geteuid(), "landlock_abi": 6,
            "landlock_write_rights": 32754, "landlock_handled_rights": 32754,
            "read_allowlist_enforced": False, "readable_roots": [],
            "readable_files": [], "executable_files": [],
            "seccomp_sha256":
                "80658aa1b897a70b445c4449ba3e5fa21db7b31388833cabbf9fb14a5e782fb7",
            "blocked_syscalls": sorted(server._DISCOVERY_SANDBOX_BLOCKED),
            "profile": "candidate_default_v1", "network_profile": "deny_all",
            "outbound_socket_families": [],
            "server_socket_operations_denied": ["bind", "listen", "accept", "accept4"],
            "unix_socket_creation_denied": False, "broker_socket_path": None,
            "broker_fd_inherited": False, "broker_peer": None,
            "writable_root": str(writable), "writable_device_paths": [],
            "cgroup_path": f"{cgroup_root}/autokernel-424242-{'1' * 16}",
            "resource_limits": server._DISCOVERY_SANDBOX_LIMITS,
            "policy_sha256": policy_sha,
            "activated_at_unix_ns": int(started_epoch * 1_000_000_000),
            "argv_sha256": argv_sha,
        }, sealed=False)
        stream.parent.mkdir(parents=True, exist_ok=True)
        stream.write_bytes(b"[  5%] Building HIP object ggml-hip.dir/quant.cu.o\n")
        stream.chmod(0o600)
        return {"attempt": attempt, "prefix": prefix, "writable": writable,
                "argv": argv, "cgroup_root": cgroup_root, "stream": stream,
                "start": start, "sandbox": sandbox_path}

    def _v24_build_observation_fixture(self) -> dict:
        """Build the exact v2 contract/owner/attempt prefix around one live arm."""
        def tool(requested: str) -> dict:
            resolved = Path(requested).resolve(strict=True)
            return {"requested": requested, "resolved": str(resolved),
                    "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest()}
        programs = {
            "cmake": tool("/usr/bin/cmake"), "cc": tool("/usr/bin/cc"),
            "c++": tool("/usr/bin/c++"), "make": tool("/usr/bin/make"),
            "ninja": None, "hipcc": tool("/opt/rocm/bin/hipcc"),
        }
        rocm_programs = {
            "bin/hipcc": tool("/opt/rocm/bin/hipcc"),
            "llvm/bin/clang": tool("/opt/rocm/llvm/bin/clang"),
            "llvm/bin/clang++": tool("/opt/rocm/llvm/bin/clang++"),
            "llvm/bin/ld.lld": tool("/opt/rocm/llvm/bin/ld.lld"),
        }
        toolchain = {
            "schema": "epyc.autokernel.build_toolchain.v1",
            "programs": programs, "rocm_root": "/opt/rocm",
            "rocm_programs": rocm_programs,
            "dynamic_environment": {"PYTHONDONTWRITEBYTECODE": "1",
                                    "TMPDIR": "<arm-build-dir>/.autokernel-tmp"},
        }
        toolchain["toolchain_sha256"] = hashlib.sha256(
            server._canonical_json_bytes(toolchain)).hexdigest()
        proposal = {"change": {"estimated_diff_size": 1,
                                "files_and_symbols": ["ggml/src/ggml-cuda/x.cu:x"]},
                    "change_class": "arithmetic", "proposal_id": "akp-fixture"}
        proposal_sha = hashlib.sha256(
            server._canonical_json_bytes(proposal)).hexdigest()
        patch = b"diff --git a/x b/x\n"
        native_manifest = {
            "schema": "epyc.autokernel.source-patch.v1",
            "campaign_id": "ak-discovery-aaaaaaaaaaaaaaaa",
            "candidate_id": "akc-fixture", "change_class": "arithmetic",
            "declared_files": ["ggml/src/ggml-cuda/x.cu"],
            "declared_symbols": {"ggml/src/ggml-cuda/x.cu": ["x"]},
            "instrument_commit": "1" * 40, "mechanism_id": "2" * 64,
            "patch_base64": base64.b64encode(patch).decode(),
            "patch_encoding": "base64",
            "patch_sha256": hashlib.sha256(patch).hexdigest(),
            "production_base_commit": "0" * 40,
            "proposal_id": "akp-fixture", "source_tree": "llama.cpp",
        }
        manifest_raw = server._canonical_json_bytes(native_manifest)
        manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
        projected_manifest = {key: value for key, value in native_manifest.items()
                              if key not in {"schema", "patch_encoding"}}
        instrument = {
            "schema": "epyc.autokernel.measurement_instrument_authority.v1",
            "production_base_commit": "0" * 40,
            "instrument_branch": "codex/fixture", "instrument_commit": "1" * 40,
            "instrument_tree": "3" * 40, "tree_listing_sha256": "4" * 64,
        }
        instrument["authority_sha256"] = hashlib.sha256(
            server._canonical_json_bytes(instrument)).hexdigest()
        process = {
            "pid": 31337, "start_ticks": 123456,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "host": os.uname().nodename, "host_id_source": "kernel-hostname",
            "host_id_sha256": hashlib.sha256(
                os.uname().nodename.encode()).hexdigest()}
        controller = {**process, "pgid": 31300, "argv_sha256": "5" * 64}
        stable = {
            "schema": "epyc.autokernel.supervised_launch_authority.v2",
            "launch_spec": {"device": 1, "inode": 2, "mode": 0o600,
                            "nlink": 1, "path": "/fixture/launch-spec.json",
                            "sha256": "6" * 64, "uid": os.geteuid()},
            "death_ledger": {"device": 1, "inode": 3, "mode": 0o600,
                             "nlink": 1, "path": "/fixture/death-ledger.jsonl",
                             "uid": os.geteuid()},
            "spec_sha256": "7" * 64,
            "deployment_config_canonical_sha256": "8" * 64,
            "deployment_config_semantic_sha256": "a" * 64,
        }
        stable_sha = hashlib.sha256(
            server._canonical_json_bytes(stable)).hexdigest()
        contract = {
            "schema": "epyc.autokernel.gpu_source_build_key.v2",
            "builder_schema": "epyc.autokernel.static_gpu_source_builder.v6",
            "deployment_config_canonical_sha256": "8" * 64,
            "deployment_config_semantic_sha256": "a" * 64,
            "supervised_build_authority": stable,
            "supervised_build_authority_sha256": stable_sha,
            "production_base_authority": {
                "path": "/mnt/raid0/llm/llama.cpp",
                "branch": "production-consolidated-v9", "commit": "0" * 40},
            "instrument_authority": instrument,
            "patch_bundle_sha256": manifest_sha,
            "patch_sha256": native_manifest["patch_sha256"],
            "proposal_sha256": proposal_sha,
            "selected_gpu_base_blobs": {"ggml/src/ggml-cuda/x.cu": "9" * 64},
            "cmake_defines": server._DISCOVERY_BUILD_CMAKE_DEFINES_V2,
            "build_type": "Release",
            "parallelism": server._DISCOVERY_BUILD_PARALLELISM_V2,
            "required_targets": server._DISCOVERY_BUILD_TARGETS_V2,
            "build_environment": {
                "CC": programs["cc"]["resolved"],
                "CXX": programs["c++"]["resolved"], "HIP_PATH": "/opt/rocm",
                "HOME": "/home/node", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
                "LD_LIBRARY_PATH": "/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib",
                "PATH": "/opt/rocm/bin:/usr/local/bin:/usr/bin:/bin",
                "ROCM_PATH": "/opt/rocm"},
            "toolchain": toolchain, "operations_root": str(self.operations),
            "build_root": str(self.bundle / "builds"),
        }
        contract["build_key"] = hashlib.sha256(
            server._canonical_json_bytes(contract)).hexdigest()
        build_key = contract["build_key"]
        entry = self.operations / "build-cache/entries" / build_key
        attempt = entry / "attempts/attempt-000001"
        logs = attempt / "logs"
        logs.mkdir(parents=True)
        entry.chmod(0o700); attempt.chmod(0o700)
        locks_root = self.operations / "build-cache/locks"
        locks_root.mkdir(parents=True)
        request_preimage = {
            "schema": "epyc.autokernel.gpu_source_build_request.v2",
            **{key: contract[key] for key in (
                "deployment_config_canonical_sha256",
                "deployment_config_semantic_sha256",
                "supervised_build_authority_sha256", "production_base_authority",
                "instrument_authority", "patch_bundle_sha256", "proposal_sha256",
                "builder_schema")}}
        request_key = hashlib.sha256(
            server._canonical_json_bytes(request_preimage)).hexdigest()
        request_lock = locks_root / f"request-{request_key}.lock"
        build_lock = locks_root / f"build-{build_key}.lock"
        for path in (request_lock, build_lock):
            path.touch(); path.chmod(0o600)
        identities = [{"device": path.stat().st_dev, "inode": path.stat().st_ino,
                       "path": str(path), "uid": os.geteuid()}
                      for path in (request_lock, build_lock)]
        intent_body = {
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "authority": "nonpromotable_candidate_only_discovery",
            "build_key": build_key, "build_contract": contract,
            "promotion_claim": False, "request_key": request_key}
        intent = self._private_json(entry / "intent.json", intent_body)
        intent_raw = server._canonical_json_bytes(intent) + b"\n"
        full_authority = {
            **stable, "schema": "epyc.autokernel.supervised_build_authority.v2",
            "controller": controller, "supervisor": process,
            "ledger_child_started_record_sha256": "b" * 64}
        full_sha = hashlib.sha256(
            server._canonical_json_bytes(full_authority)).hexdigest()
        holder = {key: controller[key] for key in ("pid", "start_ticks", "boot_id", "host")}
        holder["label"] = f"autokernel-build:{build_key}:attempt-000001"
        transaction_holder = dict(holder)
        transaction_holder["label"] = f"autokernel-build-transaction:{build_key}"
        self._private_json(entry / "transaction-owner.json", {
            "schema": "epyc.autokernel.gpu_source_build_transaction_owner.v2",
            "build_key": build_key, "holder": transaction_holder,
            "intent": intent_body, "intent_file_sha256": hashlib.sha256(intent_raw).hexdigest(),
            "locks": identities, "promotion_claim": False,
            "supervised_build_authority": full_authority,
            "supervised_build_authority_sha256": full_sha})
        self._private_json(attempt / "owner.json", {
            "schema": "epyc.autokernel.gpu_source_build_attempt.v2",
            "attempt": 1, "attempt_name": "attempt-000001", "build_key": build_key,
            "cache_root": str(entry),
            "build_root": str(self.bundle / "builds" / build_key / "attempt-000001"),
            "holder": holder, "locks": identities,
            "supervised_build_authority": full_authority,
            "supervised_build_authority_sha256": full_sha,
            "promotion_claim": False})
        campaign = native_manifest["campaign_id"]
        source = attempt / "worktrees" / f"llama.cpp-{campaign}-akc-anchor-snapshot"
        writable = self.bundle / "builds" / build_key / "attempt-000001" / campaign / "akc-anchor"
        source.mkdir(parents=True, exist_ok=True)
        writable.mkdir(parents=True, exist_ok=True)
        configure_argv = [programs["cmake"]["resolved"], "-S", str(source),
                          "-B", str(writable), "-DCMAKE_BUILD_TYPE=Release"] + [
                              f"-D{key}={value}" for key, value in
                              server._DISCOVERY_BUILD_CMAKE_DEFINES_V2]
        self._private_json(logs / "akc-anchor.log.configure-process-intent.json", {
            "schema": "epyc.autokernel.owned_process_intent.v1",
            "argv": configure_argv, "epoch_token": "c" * 64,
            "stdout_path": str(logs / "akc-anchor.log.configure.stream"),
            "sandbox_receipt_path": str(logs / "akc-anchor.log.configure-sandbox.json"),
            "sandbox_policy_sha256": "d" * 64, "sandbox_token": "e" * 16,
            "cgroup_root": "/sys/fs/cgroup/controller-fixture"})
        state = {"inflight": {
            "candidate": {"manifest": projected_manifest,
                          "manifest_raw_base64": base64.b64encode(manifest_raw).decode(),
                          "source_manifest_sha256": manifest_sha,
                          "manifest_file_sha256": manifest_sha,
                          "patch_bundle_sha256": manifest_sha, "proposal": proposal},
            "row": {"proposal_sha256": proposal_sha,
                    "source_manifest_sha256": manifest_sha}}}
        return {"state": state, "entry": entry, "attempt": attempt,
                "request_lock": request_lock, "build_lock": build_lock,
                "contract": contract, "configure_argv": configure_argv}

    def _v24_terminal_fixture(self) -> dict:
        """Seal a real-schema v24 terminal/closure/materialization epoch."""
        fixture = self._v24_build_observation_fixture()
        entry, attempt = fixture["entry"], fixture["attempt"]
        contract = fixture["contract"]
        build_key = entry.name
        logs = attempt / "logs"
        campaign = fixture["state"]["inflight"]["candidate"]["manifest"][
            "campaign_id"]
        candidate_id = fixture["state"]["inflight"]["candidate"]["manifest"][
            "candidate_id"]
        cmake = contract["toolchain"]["programs"]["cmake"]["resolved"]
        # A terminal transaction contains both configure/build subprocess
        # terminals while its owning discovery controller may remain live for
        # correctness and screening.  The full-adapter regression below mocks
        # only the already-unit-tested subprocess receipt parser; these exact
        # names/argv still exercise the two-arm build state machine and closure.
        for name in ("akc-anchor", candidate_id):
            source = (attempt / "worktrees" /
                      f"llama.cpp-{campaign}-{name}-snapshot")
            writable = (self.bundle / "builds" / build_key /
                        "attempt-000001" / campaign / name)
            configure_argv = [
                cmake, "-S", str(source), "-B", str(writable),
                "-DCMAKE_BUILD_TYPE=Release",
                *[f"-D{key}={value}" for key, value in
                  server._DISCOVERY_BUILD_CMAKE_DEFINES_V2],
            ]
            self._private_json(
                logs / f"{name}.log.configure-process-intent.json", {
                    "schema": "epyc.autokernel.owned_process_intent.v1",
                    "argv": configure_argv, "epoch_token": "c" * 64,
                    "stdout_path": str(logs / f"{name}.log.configure.stream"),
                    "sandbox_receipt_path": str(
                        logs / f"{name}.log.configure-sandbox.json"),
                    "sandbox_policy_sha256": "d" * 64,
                    "sandbox_token": "e" * 16,
                    "cgroup_root": "/sys/fs/cgroup/controller-fixture",
                })
            self._private_json(
                logs / f"{name}.log.build-process-terminal.json", {
                    "schema": "epyc.autokernel.owned_process_terminal.v2",
                    "start_receipt_sha256": "a" * 64,
                    "disposition": {},
                    "stdout_path": str(logs / f"{name}.log.build.stream"),
                    "stdout_sha256": "b" * 64, "stdout_identity": {},
                })
        receipts = attempt / "receipts"
        receipts.mkdir()
        owner_raw = (attempt / "owner.json").read_bytes()
        manifest_sha = contract["patch_bundle_sha256"]
        anchor_identity = {"id": "anchor"}
        candidate_identity = {"id": "candidate"}
        reward_sha = "e" * 64
        materialization_body = {
            "schema": "epyc.autokernel.gpu_source_materialization.v1",
            "authority": "nonpromotable_candidate_only_discovery",
            "operation_key": build_key, "build_key": build_key,
            "build_contract": contract,
            "actor_worktree": None, "actor_proof": None,
            "manifest_sha256": manifest_sha,
            "production_base_authority": contract["production_base_authority"],
            "instrument_authority": contract["instrument_authority"],
            "selected_gpu_base_blobs": contract["selected_gpu_base_blobs"],
            "applied": True, "anchor_commit": "0" * 40,
            "candidate_source_commit": "1" * 40,
            "candidate_source_sha256": "2" * 64,
            "patch_applied": True, "production_tree": False,
            "builds": {}, "anchor_identity": anchor_identity,
            "candidate_identity": candidate_identity,
            "anchor_source_tree_receipt": "anchor-tree.json",
            "anchor_source_tree_receipt_sha256": "3" * 64,
            "candidate_source_tree_receipt": "candidate-tree.json",
            "candidate_source_tree_receipt_sha256": "4" * 64,
            "source_identity_receipts": [], "correctness_capabilities": {},
            "build_identity_files": [], "shared_runtime": {},
            "reward_runtime_receipt": "reward.json",
            "reward_runtime_sha256": reward_sha,
            "promotion_claim": False,
        }
        materialization = self._private_json(
            entry / "materialization.json", materialization_body)
        materialization_path = entry / "materialization.json"
        materialization_sha = hashlib.sha256(
            materialization_path.read_bytes()).hexdigest()
        build = {key: None for key in server._DISCOVERY_V2_TERMINAL_BUILD_KEYS}
        build.update({
            "build_key": build_key,
            "anchor_identity": anchor_identity,
            "candidate_identity": candidate_identity,
            "materialization_receipt": str(materialization_path),
            "materialization_sha256": materialization_sha,
            "reward_runtime_sha256": reward_sha,
        })

        def closure_rows(root: Path) -> list[dict]:
            rows = []
            for path in sorted(root.iterdir(), key=lambda item: item.name):
                info = path.stat()
                rows.append({
                    "name": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "identity": {
                        "device": info.st_dev, "inode": info.st_ino,
                        "mode": info.st_mode & 0o7777, "nlink": info.st_nlink,
                        "uid": info.st_uid, "size": info.st_size,
                        "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns,
                    },
                })
            return rows

        proofs = []
        for name in ("akc-anchor", candidate_id):
            for phase in ("build", "configure"):
                prefix = attempt / "logs" / f"{name}.log.{phase}"
                proofs.append({
                    "intent": str(prefix.with_name(
                        prefix.name + "-process-intent.json")),
                    "start": str(prefix.with_name(
                        prefix.name + "-process-start.json")),
                    "terminal": str(prefix.with_name(
                        prefix.name + "-process-terminal.json")),
                    "state": "terminal_verified_dead",
                    "sandbox": {
                        "receipt": str(prefix.with_name(
                            prefix.name + "-sandbox.json")),
                        "receipt_present": True, "pid": 100,
                        "process_start_ticks": 200,
                        "cgroup_path": str(Path(self.temp.name) /
                                           f"absent-{name}-{phase}"),
                        "cgroup_state": "absent",
                        "state": "activation_dead_cgroup_drained",
                        "reason": None,
                    },
                })
        closure = {
            "schema": "epyc.autokernel.build_process_closure.v1",
            "entries": closure_rows(attempt / "logs"), "proofs": proofs,
            "require_terminals": True,
        }
        closure["closure_sha256"] = hashlib.sha256(
            server._canonical_json_bytes(closure)).hexdigest()
        epoch = {
            "schema": "epyc.autokernel.build_artifact_epoch.v1",
            "attempt": "attempt-000001",
            "attempt_owner_sha256": hashlib.sha256(owner_raw).hexdigest(),
            "attempt_recovery": None, "prior_recoveries": [],
            "process_closure": closure,
            "materialization_sha256": materialization_sha,
            "artifact_receipts": closure_rows(receipts),
        }
        epoch["artifact_epoch_sha256"] = hashlib.sha256(
            server._canonical_json_bytes(epoch)).hexdigest()
        terminal = self._private_json(entry / "terminal.json", {
            "schema": "epyc.autokernel.gpu_source_build_terminal.v2",
            "build_key": build_key,
            "intent_file_sha256": hashlib.sha256(
                (entry / "intent.json").read_bytes()).hexdigest(),
            "state": "complete", "build": build,
            "attempt_name": "attempt-000001",
            "attempt_owner_sha256": hashlib.sha256(owner_raw).hexdigest(),
            "process_closure_sha256": closure["closure_sha256"],
            "artifact_epoch": epoch, "promotion_claim": False,
        })
        return {**fixture, "terminal": terminal,
                "materialization": materialization}

    def _active_payload(self) -> dict:
        with (self.state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return server.discovery_live_payload()

    def _complete_build(self, entry: Path, *, build_key: str,
                        manifest_sha: str, contract: dict) -> None:
        materialization = _seal({
            "schema": "epyc.autokernel.gpu_source_materialization.v1",
            "authority": "nonpromotable_candidate_only_discovery",
            "operation_key": build_key,
            "build_key": build_key,
            "build_contract": contract,
            "manifest_sha256": manifest_sha,
            "promotion_claim": False,
        })
        materialization_path = entry / "materialization.json"
        materialization_path.write_text(json.dumps(materialization) + "\n")
        intent_path = entry / "intent.json"
        terminal = _seal({
            "schema": "epyc.autokernel.gpu_source_build_terminal.v1",
            "build_key": build_key,
            "intent_file_sha256": hashlib.sha256(
                intent_path.read_bytes()).hexdigest(),
            "state": "complete",
            "build": {
                "build_key": build_key,
                "materialization_receipt": str(materialization_path),
                "materialization_sha256": hashlib.sha256(
                    materialization_path.read_bytes()).hexdigest(),
            },
            "promotion_claim": False,
        })
        (entry / "terminal.json").write_text(json.dumps(terminal) + "\n")

    def _write_v10_correctness_parser_terminal(self) -> None:
        """Reproduce the durable v10 boundary, without inventing telemetry."""
        manifest_sha = "b" * 64
        proposal_sha = "c" * 64
        operation_key = "8" * 64
        build_key = "d" * 64
        acquired_at = _iso(60)
        released_at = _iso(5)
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(2), "next": 1, "complete": False,
            "iterations": [],
            "inflight": {
                "operation_key": operation_key,
                "candidate": {
                    "source_manifest_sha256": manifest_sha,
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                },
                "row": {
                    "proposal_sha256": proposal_sha,
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                },
                "lease": {"admitted": True, "device_id": "mi210_0"},
                "exception": {
                    "type": "EvidenceProducerError",
                    "message": "correctness stdout must contain exactly one summary",
                },
            },
        }))
        entry = self.operations / "build-cache/entries" / build_key
        entry.mkdir(parents=True)
        contract = {
            "build_key": build_key,
            "patch_bundle_sha256": manifest_sha,
            "proposal_sha256": proposal_sha,
            "deployment_config_sha256": "a" * 64,
        }
        (entry / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key,
            "build_contract": contract,
        }))
        self._complete_build(entry, build_key=build_key,
                             manifest_sha=manifest_sha, contract=contract)
        build_completed = datetime.fromisoformat(
            acquired_at.replace("Z", "+00:00")).timestamp() - 1
        os.utime(entry / "terminal.json", (build_completed, build_completed))
        operation = self.operations / operation_key
        (operation / "proof/correctness").mkdir(parents=True)
        (operation / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_operation.v1",
            "operation_key": operation_key,
            "manifest_sha256": manifest_sha,
        }))
        (operation / "evidence-policy.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_execution_policy.v1",
            "manifest_sha256": manifest_sha,
        }))
        (operation / "proof/correctness/stdout.txt").write_text(
            "Testing 2 devices\n  1139/1139 tests passed\n"
            "  Backend ROCm0: OK\nBackend 2/2: CPU\n  Skipping\n"
            "2/2 backends passed\nOK\n")
        (operation / "proof/correctness/stderr.txt").write_text(
            "ggml_cuda_init: found 1 ROCm devices\n")
        (operation / "reservation-release.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_reservation_release.v1",
            "operation_key": operation_key,
            "device_claim_released": {
                "schema": "epyc.autokernel.device_claim_receipt.v1",
                "claim_id": "akd-v10-correctness",
                "device_id": "mi210_0",
                "purpose": "AutoKernel GPU source proof and throughput",
                "acquired_at": acquired_at,
                "released_at": released_at,
            },
        }))

    def test_active_precheckpoint_planner_answers_the_operator_questions(self) -> None:
        self._write_events([_event("planner_started", seconds_ago=95)])

        payload = self._active_payload()
        activity = payload["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertTrue(activity["phase"]["label"])
        self.assertGreaterEqual(activity["phase"]["elapsed_s"], 90)
        self.assertIn(activity["stall"]["state"],
                      {"healthy", "slow", "stalled"})
        self.assertGreater(activity["stall"]["threshold_s"], 0)
        self.assertTrue(activity["stall"]["detail"])
        self.assertIn("planner", activity["waiting_on"].lower())
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertTrue(activity["gpu"]["detail"])
        self.assertFalse(activity["checkpoint"]["available"])
        self.assertIn("no", activity["checkpoint"]["detail"].lower())
        self.assertIn("checkpoint", activity["checkpoint"]["detail"].lower())

        transitions = activity["transitions"]
        self.assertGreaterEqual(len(transitions), 1)
        self.assertEqual(transitions[-1]["event"], "planner_started")
        self.assertEqual(transitions[-1]["phase"], "planner")
        self.assertTrue(transitions[-1]["label"])
        self.assertEqual(
            [row["ts"] for row in transitions],
            sorted(row["ts"] for row in transitions),
            "the transition timeline must be chronological")

    def test_v11_planner_event_supplies_hypothesis_before_pending_checkpoint(self) -> None:
        expected_campaign = "ak-discovery-" + "a" * 16
        self._write_events([_event(
            "planner_started", seconds_ago=4,
            campaign_id=expected_campaign)])

        activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertEqual(activity["hypothesis_id"],
                         "akh-v2-q5-type-specific-dequant")

        self._write_events([
            _event("planner_started", seconds_ago=4,
                   campaign_id=expected_campaign),
            _event("planner_started", seconds_ago=3,
                   campaign_id="ak-discovery-wrong"),
        ])
        self.assertEqual(self._active_payload()["activity"]["hypothesis_id"],
                         "akh-v2-q5-type-specific-dequant")

        self._write_events([
            _event("planner_started", seconds_ago=4,
                   campaign_id=expected_campaign),
            _event("planner_completed", seconds_ago=3,
                   campaign_id=expected_campaign),
        ])
        self.assertIsNone(self._active_payload()["activity"]["hypothesis_id"])

    def test_planner_uses_its_sealed_actor_budget_before_stall_warning(self) -> None:
        self._write_events([_event("planner_started", seconds_ago=600)])

        activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertEqual(activity["stall"]["state"], "healthy")
        self.assertEqual(activity["stall"]["threshold_s"], 900.0)

    def test_v7_exit_after_planner_completion_is_validation_failure(self) -> None:
        """Two actor events are not a launch-idle state after the lock exits."""
        self._write_events([
            _event("planner_started", seconds_ago=90),
            _event("planner_completed", seconds_ago=30,
                   result={"returncode": 0}),
        ])

        payload = server.discovery_live_payload()
        activity = payload["activity"]

        self.assertFalse(payload["active"])
        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "planner_validation")
        self.assertIsNone(activity["hypothesis_id"])
        self.assertFalse(activity["checkpoint"]["available"])
        self.assertTrue(activity["failure"]["detected"])
        self.assertEqual(activity["failure"]["stage"], "planner_validation")
        self.assertIn("did not persist", activity["failure"]["detail"])
        self.assertIn("exact planner-validation exception",
                      activity["failure"]["detail"])
        self.assertFalse(activity["resume"]["possible"])
        self.assertIn("fresh sealed deployment", activity["resume"]["detail"])
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertIn("not reached", activity["gpu"]["detail"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"]["state"], "complete")
        self.assertEqual(pipeline["planner_validation"]["state"], "failed")
        self.assertEqual(pipeline["critic"]["state"], "not_reached")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "planner_validation_interrupted")

    def test_noncontract_planner_validation_events_are_rejected(self) -> None:
        for event in ("planner_validation_failed", "planner_validation_refused"):
            with self.subTest(event=event):
                self._write_events([
                    _event("planner_started", seconds_ago=90),
                    _event("planner_completed", seconds_ago=30,
                           result={"returncode": 0}),
                    _event(event, seconds_ago=29, channel="autokernel",
                           model="local-validator", provider="controller"),
                ])

                payload = server.discovery_live_payload()
                activity = payload["activity"]

                self.assertEqual(activity["status"], "failed")
                self.assertEqual(activity["phase"]["id"], "planner_validation")
                self.assertTrue(activity["failure"]["detected"])
                self.assertIn("did not persist",
                              activity["failure"]["detail"])
                self.assertEqual(payload["telemetry_integrity"]["state"],
                                 "degraded")
                self.assertIn("rejected by telemetry contract",
                              payload["telemetry_integrity"]["detail"])
                pipeline = {row["id"]: row for row in activity["pipeline"]}
                self.assertEqual(pipeline["planner"]["state"], "complete")
                self.assertEqual(pipeline["planner_validation"]["state"], "failed")

    def test_gpu_expected_and_claimed_are_two_independent_facts(self) -> None:
        self._write_events([
            _event("planner_started", seconds_ago=180),
            _event("planner_completed", seconds_ago=150, result={"returncode": 0}),
            _event("critic_started", seconds_ago=145, channel="autokernel",
                   model="claude-fable-5", provider="claude"),
            _event("critic_completed", seconds_ago=120, channel="autokernel",
                   model="claude-fable-5", provider="claude",
                   result={"decision": "accept", "returncode": 0}),
        ])
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(5),
            "next": 1,
            "complete": False,
            "terminal_reason": None,
            "pending": None,
            "iterations": [],
            "inflight": {
                "phase": "measurement",
                "lease": {
                    "phase": "measurement",
                    "device_id": "mi210_0",
                    # This is the controller's native durable field, not a
                    # dashboard-only fixture shape.
                    "device_claim_probe_open": {
                        "state": "held",
                        "released_at": None,
                        "device_id": "mi210_0",
                    },
                },
            },
        }))

        activity = self._active_payload()["activity"]
        self.assertTrue(activity["gpu"]["expected_now"])
        self.assertTrue(activity["gpu"]["claim_held"])
        self.assertIn("mi210", activity["gpu"]["detail"].lower())

    def test_v8_critic_pending_actor_outranks_resource_admission(self) -> None:
        self._write_events([
            _event("planner_started", seconds_ago=180),
            _event("planner_completed", seconds_ago=60,
                   result={"returncode": 0}),
            _event("critic_started", seconds_ago=30, channel="autokernel",
                   model="claude-fable-5", provider="claude"),
        ])
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(31),
            "next": 1,
            "complete": False,
            "terminal_reason": None,
            "inflight": None,
            "iterations": [],
            "pending": {
                "phase": "critic_pending",
                "candidate": {
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                },
                "row": {
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                },
            },
        }))
        journal = self.state / "journal"
        journal.mkdir()
        (journal / "events.jsonl").write_text(json.dumps({
            "campaign_id": "ak-discovery-v8",
            "event_id": "akj-000000000003-planner-checkpointed",
            "journal_schema": "epyc.autokernel.journal_entry.v1",
            "kind": "STOP_STATE",
            "payload": {
                "controller_state_sha256": "c" * 64,
                "state": "discovery_planner_checkpointed",
            },
            "record_id": None,
            "seq": 3,
            "written_at": _iso(31),
        }) + "\n")

        payload = self._active_payload()
        activity = payload["activity"]

        self.assertTrue(payload["active"])
        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "critic")
        self.assertEqual(activity["phase"]["label"], "Critic review")
        self.assertEqual(activity["waiting_on"], "critic review completion")
        self.assertEqual(activity["hypothesis_id"],
                         "akh-v2-q5-type-specific-dequant")
        self.assertFalse(activity["gpu"]["expected_now"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"]["state"], "complete")
        self.assertEqual(pipeline["planner_validation"]["state"], "complete")
        self.assertEqual(pipeline["critic"]["state"], "running")
        self.assertEqual(pipeline["authorization"]["state"], "not_reached")
        self.assertEqual(pipeline["resource_admission"]["state"], "not_reached")
        self.assertTrue(activity["checkpoint"]["available"])
        self.assertEqual(activity["checkpoint"]["seq"], 3)

    def test_held_identity_bound_build_transaction_is_the_active_stage(self) -> None:
        manifest_sha = "b" * 64
        proposal_sha = "c" * 64
        build_key = "d" * 64
        state = {
            "updated_at": _iso(5), "next": 1, "complete": False,
            "iterations": [],
            "inflight": {
                "candidate": {"source_manifest_sha256": manifest_sha,
                              "manifest": {"candidate_id": "akc-candidate-1"},
                              "hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "row": {"proposal_sha256": proposal_sha,
                        "hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "lease": {"admitted": True,
                          "device_claim_probe_released": {"released_at": _iso(6)}},
            },
        }
        (self.state / "state.json").write_text(json.dumps(state))
        entry = self.operations / "build-cache/entries" / build_key
        locks = self.operations / "build-cache/locks"
        entry.mkdir(parents=True)
        locks.mkdir(parents=True)
        (entry / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key,
            "build_contract": {
                "build_key": build_key,
                "patch_bundle_sha256": manifest_sha,
                "proposal_sha256": proposal_sha,
                "deployment_config_sha256": "a" * 64,
            },
        }))
        build_lock = locks / f"build-{build_key}.lock"
        build_lock.touch()
        logs = entry / "logs"
        logs.mkdir()
        (logs / "akc-candidate-1.log.build-sandbox.json").write_text("{}")
        with build_lock.open("r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "build")
        self.assertEqual(activity["phase"]["label"], "Compiling candidate arm 2 of 2")
        self.assertEqual(activity["waiting_on"], "candidate build completion")
        self.assertFalse(activity["gpu"]["expected_now"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["source_materialization"]["state"], "running")
        self.assertEqual(pipeline["build"]["state"], "running")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "build_transaction_observed")
        self.assertEqual(activity["transitions"][-1]["label"],
                         "candidate arm active")

    def test_v24_live_build_receipts_project_verified_hip_progress(self) -> None:
        fixture = self._v24_live_process_fixture()
        with mock.patch.object(server, "_discovery_process_identity_live",
                               return_value=True):
            result = server._discovery_v2_process_receipts(
                prefix=fixture["prefix"], attempt_root=fixture["attempt"],
                writable_root=fixture["writable"], expected_argv=fixture["argv"],
                expected_cgroup_root=fixture["cgroup_root"],
                require_live=True, now=datetime.now(timezone.utc).timestamp())
        self.assertIsNotNone(result)
        self.assertEqual(result["progress_percent"], 5)
        self.assertTrue(result["hip_compile"])
        self.assertFalse(result["stream_stale"])

    def test_v24_full_v2_attempt_projects_only_with_held_bound_authority(self) -> None:
        fixture = self._v24_build_observation_fixture()
        def process(**kwargs):
            if kwargs["require_live"]:
                return {"started_at": _iso(20), "progress_percent": 5,
                        "hip_compile": True, "progress_at": _iso(1),
                        "stream_stale": False}
            return {"started_at": _iso(30), "completed": True,
                    "completed_at": _iso(21)}
        with (fixture["request_lock"].open("r+") as request_handle,
              fixture["build_lock"].open("r+") as build_handle):
            fcntl.flock(request_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(build_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with (mock.patch.object(server, "_discovery_v2_git_authority",
                                    return_value=True),
                  mock.patch.object(server, "_discovery_authority_cgroup",
                                    return_value={"path":
                                                  "/sys/fs/cgroup/controller-fixture"}),
                  mock.patch.object(server, "_discovery_proc_stat",
                                    return_value=("S", 31300, 123456)),
                  mock.patch.object(server, "_discovery_v2_process_receipts",
                                    side_effect=process)):
                observation, claimed = server._discovery_v2_build_observation(
                    self.operations, fixture["state"], "a" * 64)
        self.assertTrue(claimed)
        self.assertEqual(observation["stage"], "build")
        self.assertEqual(observation["arm"], "anchor")
        self.assertEqual(observation["attempt"], "attempt-000001")
        self.assertTrue(observation["source_materialized"])
        self.assertTrue(observation["process_verified"])

    def test_v24_full_attempt_tamper_release_and_extra_log_fail_closed(self) -> None:
        fixture = self._v24_build_observation_fixture()
        intent_path = fixture["entry"] / "intent.json"
        intent = json.loads(intent_path.read_text())
        intent["receipt_sha256"] = "0" * 64
        intent_path.write_bytes(server._canonical_json_bytes(intent) + b"\n")
        intent_path.chmod(0o600)
        # A legacy marker cannot rescue a claimed but malformed v2 transaction.
        legacy = fixture["entry"] / "logs"
        legacy.mkdir(exist_ok=True)
        (legacy / "akc-anchor.log.build-sandbox.json").write_text("{}")
        with mock.patch.object(server, "_discovery_legacy_build_observation") as legacy_read:
            self.assertIsNone(server._discovery_build_observation(
                self.operations, fixture["state"], "a" * 64))
            legacy_read.assert_not_called()

        shutil.rmtree(self.operations / "build-cache")
        fixture = self._v24_build_observation_fixture()
        with fixture["request_lock"].open("r+") as request_handle:
            fcntl.flock(request_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Build lock deliberately released: names/receipts alone are not liveness.
            with (mock.patch.object(server, "_discovery_v2_git_authority",
                                    return_value=True),
                  mock.patch.object(server, "_discovery_authority_cgroup",
                                    return_value={"path":
                                                  "/sys/fs/cgroup/controller-fixture"})):
                observation, claimed = server._discovery_v2_build_observation(
                    self.operations, fixture["state"], "a" * 64)
        self.assertTrue(claimed)
        self.assertIsNone(observation)

    def test_v24_recovered_attempt_is_claimed_but_fails_closed(self) -> None:
        fixture = self._v24_build_observation_fixture()
        second = fixture["entry"] / "attempts/attempt-000002"
        second.mkdir()
        (fixture["attempt"] / "recovery.json").write_text("{}")
        with mock.patch.object(server, "_discovery_v2_git_authority",
                               return_value=True):
            observation, claimed = server._discovery_v2_build_observation(
                self.operations, fixture["state"], "a" * 64)
        self.assertTrue(claimed)
        self.assertIsNone(observation)

    def test_v24_owner_labels_are_exact_authority_bindings(self) -> None:
        fixture = self._v24_build_observation_fixture()
        owner_path = fixture["attempt"] / "owner.json"
        owner = json.loads(owner_path.read_text())
        owner["holder"]["label"] = "coherently-rehashed-but-not-the-owner"
        owner.pop("receipt_sha256")
        self._private_json(owner_path, owner)
        with (fixture["request_lock"].open("r+") as request_handle,
              fixture["build_lock"].open("r+") as build_handle):
            fcntl.flock(request_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(build_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with mock.patch.object(server, "_discovery_v2_git_authority",
                                   return_value=True):
                observation, claimed = server._discovery_v2_build_observation(
                    self.operations, fixture["state"], "a" * 64)
        self.assertTrue(claimed)
        self.assertIsNone(observation)

    def test_v24_process_receipt_identity_requires_positive_integers(self) -> None:
        valid = {"pid": 1, "pgid": 1, "process_start_ticks": 2}
        self.assertTrue(server._discovery_process_receipt_identity(valid))
        for key in valid:
            for invalid in (True, 0, -1, "1", 1.5):
                mutated = dict(valid)
                mutated[key] = invalid
                with self.subTest(key=key, invalid=invalid):
                    self.assertFalse(
                        server._discovery_process_receipt_identity(mutated))

    def test_v24_terminal_closure_is_exact_and_tamper_fails_closed(self) -> None:
        fixture = self._v24_terminal_fixture()
        arguments = {
            "entry": fixture["entry"], "attempt": fixture["attempt"],
            "intent_raw": (fixture["entry"] / "intent.json").read_bytes(),
            "owner_raw": (fixture["attempt"] / "owner.json").read_bytes(),
            "contract": fixture["contract"], "candidate_id": "akc-fixture",
        }
        self.assertTrue(server._discovery_v2_terminal_complete(**arguments))

        terminal_path = fixture["entry"] / "terminal.json"
        terminal = json.loads(terminal_path.read_text())
        terminal["build"]["invented"] = "self-hashed"
        terminal.pop("receipt_sha256")
        self._private_json(terminal_path, terminal)
        self.assertFalse(server._discovery_v2_terminal_complete(**arguments))

        shutil.rmtree(self.operations / "build-cache")
        fixture = self._v24_terminal_fixture()
        arguments.update({
            "entry": fixture["entry"], "attempt": fixture["attempt"],
            "intent_raw": (fixture["entry"] / "intent.json").read_bytes(),
            "owner_raw": (fixture["attempt"] / "owner.json").read_bytes(),
            "contract": fixture["contract"],
        })
        terminal_path = fixture["entry"] / "terminal.json"
        terminal = json.loads(terminal_path.read_text())
        epoch = terminal["artifact_epoch"]
        epoch["prior_recoveries"] = [{"attempt": "attempt-000000",
                                       "recovery_sha256": "f" * 64}]
        epoch.pop("artifact_epoch_sha256")
        epoch["artifact_epoch_sha256"] = hashlib.sha256(
            server._canonical_json_bytes(epoch)).hexdigest()
        terminal["artifact_epoch"] = epoch
        terminal.pop("receipt_sha256")
        self._private_json(terminal_path, terminal)
        self.assertFalse(server._discovery_v2_terminal_complete(**arguments))

    def test_v25_supervisor_ledger_shape_selects_live_or_historical_authority(
            self) -> None:
        self.assertIs(server._discovery_authority_ledger_live(
            require_live=True, row_count=2), True)
        self.assertIs(server._discovery_authority_ledger_live(
            require_live=False, row_count=2), True)
        self.assertIs(server._discovery_authority_ledger_live(
            require_live=False, row_count=5), False)
        for require_live, row_count in (
                (True, 5), (True, 0), (False, 0), (False, 1), (False, 3),
                (False, 4), (False, 6)):
            with self.subTest(require_live=require_live, row_count=row_count):
                self.assertIsNone(server._discovery_authority_ledger_live(
                    require_live=require_live, row_count=row_count))

    def test_v25_terminal_build_accepts_live_two_row_owner_and_seals_postbuild(
            self) -> None:
        fixture = self._v24_terminal_fixture()
        expected_authority = json.loads(
            (fixture["attempt"] / "owner.json").read_text())[
                "supervised_build_authority"]
        completed = {
            "started_at": _iso(120), "completed": True,
            "completed_at": _iso(60),
        }
        with (mock.patch.object(server, "_discovery_v2_git_authority",
                                return_value=True),
              mock.patch.object(server, "_discovery_authority_cgroup",
                                return_value={"path":
                                              "/sys/fs/cgroup/controller-fixture"})
              as authority,
              mock.patch.object(server, "_discovery_v2_process_receipts",
                                return_value=completed)):
            observation, claimed = server._discovery_v2_build_observation(
                self.operations, fixture["state"], "a" * 64)
        self.assertTrue(claimed)
        self.assertEqual(observation["stage"], "evidence_binding")
        self.assertEqual(observation["state"], "running")
        self.assertTrue(observation["source_materialized"])
        authority.assert_called_once_with(
            expected_authority, require_live=False)

        (fixture["entry"] / "terminal.json").unlink()
        observation, claimed = server._discovery_v2_build_observation(
            self.operations, fixture["state"], "a" * 64)
        self.assertTrue(claimed)
        self.assertIsNone(observation)

    def test_v24_terminal_materialization_identity_tamper_fails_closed(self) -> None:
        fixture = self._v24_terminal_fixture()
        materialization_path = fixture["entry"] / "materialization.json"
        materialization = json.loads(materialization_path.read_text())
        materialization["anchor_identity"] = {"id": "invented"}
        materialization.pop("receipt_sha256")
        self._private_json(materialization_path, materialization)
        # Re-sealing the terminal's materialization and epoch hashes must not
        # authorize an identity that disagrees with the exact build mapping.
        terminal_path = fixture["entry"] / "terminal.json"
        terminal = json.loads(terminal_path.read_text())
        materialization_sha = hashlib.sha256(
            materialization_path.read_bytes()).hexdigest()
        terminal["build"]["materialization_sha256"] = materialization_sha
        terminal["artifact_epoch"]["materialization_sha256"] = materialization_sha
        epoch = terminal["artifact_epoch"]
        epoch.pop("artifact_epoch_sha256")
        epoch["artifact_epoch_sha256"] = hashlib.sha256(
            server._canonical_json_bytes(epoch)).hexdigest()
        terminal.pop("receipt_sha256")
        self._private_json(terminal_path, terminal)
        self.assertFalse(server._discovery_v2_terminal_complete(
            fixture["entry"], fixture["attempt"],
            intent_raw=(fixture["entry"] / "intent.json").read_bytes(),
            owner_raw=(fixture["attempt"] / "owner.json").read_bytes(),
            contract=fixture["contract"], candidate_id="akc-fixture"))

    def test_v24_terminal_requires_both_owner_locks_released(self) -> None:
        fixture = self._v24_terminal_fixture()
        transaction = json.loads(
            (fixture["entry"] / "transaction-owner.json").read_text())
        identities = transaction["locks"]
        self.assertTrue(server._discovery_v2_lock_identity(
            fixture["request_lock"], identities[0], require_held=False))
        self.assertTrue(server._discovery_v2_lock_identity(
            fixture["build_lock"], identities[1], require_held=False))
        with fixture["build_lock"].open("r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertFalse(server._discovery_v2_lock_identity(
                fixture["build_lock"], identities[1], require_held=False))

    def test_v24_stale_stream_remains_live_when_pid_cgroup_is_verified(self) -> None:
        fixture = self._v24_live_process_fixture(seconds_ago=1800)
        old = datetime.now(timezone.utc).timestamp() - 1200
        os.utime(fixture["stream"], (old, old))
        with mock.patch.object(server, "_discovery_process_identity_live",
                               return_value=True):
            result = server._discovery_v2_process_receipts(
                prefix=fixture["prefix"], attempt_root=fixture["attempt"],
                writable_root=fixture["writable"], expected_argv=fixture["argv"],
                expected_cgroup_root=fixture["cgroup_root"],
                require_live=True, now=datetime.now(timezone.utc).timestamp())
        self.assertIsNotNone(result)
        self.assertTrue(result["stream_stale"])

    def test_v24_dead_tampered_or_unverified_build_never_projects_running(self) -> None:
        fixture = self._v24_live_process_fixture()
        arguments = dict(
            prefix=fixture["prefix"], attempt_root=fixture["attempt"],
            writable_root=fixture["writable"], expected_argv=fixture["argv"],
            expected_cgroup_root=fixture["cgroup_root"], require_live=True,
            now=datetime.now(timezone.utc).timestamp())
        with mock.patch.object(server, "_discovery_process_identity_live",
                               return_value=False):
            self.assertIsNone(server._discovery_v2_process_receipts(**arguments))
        fixture["sandbox"].unlink()
        with mock.patch.object(server, "_discovery_process_identity_live",
                               return_value=True):
            self.assertIsNone(server._discovery_v2_process_receipts(**arguments))

        fixture = self._v24_live_process_fixture()
        start_path = fixture["prefix"].with_name(
            fixture["prefix"].name + "-process-start.json")
        start = json.loads(start_path.read_text())
        start["argv"][-1] = "tampered-target"
        self._private_json(start_path, {
            key: value for key, value in start.items() if key != "receipt_sha256"})
        with mock.patch.object(server, "_discovery_process_identity_live",
                               return_value=True):
            self.assertIsNone(server._discovery_v2_process_receipts(
                prefix=fixture["prefix"], attempt_root=fixture["attempt"],
                writable_root=fixture["writable"], expected_argv=fixture["argv"],
                expected_cgroup_root=fixture["cgroup_root"], require_live=True,
                now=datetime.now(timezone.utc).timestamp()))

    def test_v24_terminal_presence_suppresses_live_projection(self) -> None:
        fixture = self._v24_live_process_fixture()
        terminal = fixture["prefix"].with_name(
            fixture["prefix"].name + "-process-terminal.json")
        self._private_json(terminal, {
            "schema": "epyc.autokernel.owned_process_terminal.v2",
            "start_receipt_sha256": "a" * 64, "disposition": {},
            "stdout_path": str(fixture["stream"]), "stdout_sha256": "b" * 64,
            "stdout_identity": {},
        })
        with mock.patch.object(server, "_discovery_process_identity_live",
                               return_value=True):
            self.assertIsNone(server._discovery_v2_process_receipts(
                prefix=fixture["prefix"], attempt_root=fixture["attempt"],
                writable_root=fixture["writable"], expected_argv=fixture["argv"],
                expected_cgroup_root=fixture["cgroup_root"], require_live=True,
                now=datetime.now(timezone.utc).timestamp()))

    def test_v24_completed_process_receipts_do_not_expire_after_24h(self) -> None:
        fixture = self._v24_live_process_fixture(seconds_ago=25 * 3600)
        sandbox = json.loads(fixture["sandbox"].read_text())
        stream = fixture["stream"]
        info = stream.stat()
        terminal = fixture["prefix"].with_name(
            fixture["prefix"].name + "-process-terminal.json")
        self._private_json(terminal, {
            "schema": "epyc.autokernel.owned_process_terminal.v2",
            "start_receipt_sha256": hashlib.sha256(
                fixture["prefix"].with_name(
                    fixture["prefix"].name + "-process-start.json").read_bytes()
            ).hexdigest(),
            "disposition": {
                "argv": fixture["argv"], "pid": 424242, "pgid": 424242,
                "exit_code": 0, "timed_out": False, "signals_sent": [],
                "verified_dead": True, "duration_s": 10.0,
                "started_at": fixture["start"]["started_at"],
                "sandbox_receipt": sandbox,
                "sandbox_teardown": {
                    "cgroup_path": sandbox["cgroup_path"],
                    "verified_empty": True, "removed": True,
                    "descendants_killed": [],
                },
            },
            "stdout_path": str(stream),
            "stdout_sha256": hashlib.sha256(stream.read_bytes()).hexdigest(),
            "stdout_identity": {
                "device": info.st_dev, "inode": info.st_ino,
                "mode": info.st_mode & 0o7777, "nlink": info.st_nlink,
                "uid": info.st_uid, "size": info.st_size,
                "mtime_ns": info.st_mtime_ns, "ctime_ns": info.st_ctime_ns,
            },
        })
        result = server._discovery_v2_process_receipts(
            prefix=fixture["prefix"], attempt_root=fixture["attempt"],
            writable_root=fixture["writable"], expected_argv=fixture["argv"],
            expected_cgroup_root=fixture["cgroup_root"], require_live=False,
            now=datetime.now(timezone.utc).timestamp())
        self.assertIsNotNone(result)
        self.assertTrue(result["completed"])

    def test_v24_tool_digest_cache_binds_ctime_and_rehashes(self) -> None:
        resolved = Path("/usr/bin/true")
        first = SimpleNamespace(st_dev=1, st_ino=2, st_size=3,
                                st_mtime_ns=4, st_ctime_ns=5,
                                st_mode=0o100755, st_uid=0, st_nlink=1)
        changed = SimpleNamespace(st_dev=1, st_ino=2, st_size=3,
                                  st_mtime_ns=4, st_ctime_ns=6,
                                  st_mode=0o100755, st_uid=0, st_nlink=1)
        server._DISCOVERY_TOOL_DIGEST_CACHE.clear()
        value = {"requested": str(resolved), "resolved": str(resolved),
                 "sha256": "a" * 64}
        with (mock.patch.object(Path, "resolve", return_value=resolved),
              mock.patch.object(Path, "lstat",
                                side_effect=[first, first, changed, changed]),
              mock.patch.object(server, "_sha256_file",
                                side_effect=[("a" * 64, None),
                                             ("b" * 64, None)])):
            self.assertTrue(server._discovery_tool_identity(value))
            self.assertFalse(server._discovery_tool_identity(value))

    def test_v24_verified_build_pipeline_completes_materialization_without_gpu(self) -> None:
        observation = {
            "stage": "build", "state": "running", "arm": "anchor",
            "started_at": _iso(30), "progress_at": _iso(2),
            "build_key": "7" * 64, "attempt": "attempt-000001",
            "source_materialized": True, "process_verified": True,
            "progress_percent": 5, "hip_compile": True, "stream_stale": False,
        }
        activity = server._discovery_activity(
            lock_held=True, campaign_id="ak-discovery-aaaaaaaaaaaaaaaa",
            state={"updated_at": _iso(3), "iterations": [], "inflight": {
                "candidate": {"hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "row": {"hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "lease": {"admitted": True}}}, events=[], checkpoint=None,
            operation_observation=observation, correctness_observation=None,
            postbuild_observation=None, claim_observation=None,
            refusal_observation=None, refusal_history_observations=[],
            now=datetime.now(timezone.utc).timestamp())
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(activity["phase"]["id"], "build")
        self.assertIn("5%", activity["phase"]["label"])
        self.assertEqual(pipeline["source_materialization"]["state"], "complete")
        self.assertEqual(pipeline["build"]["state"], "running")
        self.assertEqual(activity["stage_contract"]["first_incomplete_stage"], "build")
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertFalse(activity["gpu"]["screen_started"])
        self.assertNotIn("424242", json.dumps(activity))

    def test_v24_terminal_then_held_claim_advances_to_gpu_correctness(self) -> None:
        terminal = {
            "stage": "evidence_binding", "state": "running", "arm": "complete",
            "started_at": _iso(20), "build_key": "7" * 64,
            "attempt": "attempt-000001", "source_materialized": True,
        }
        activity = server._discovery_activity(
            lock_held=True, campaign_id="ak-discovery-aaaaaaaaaaaaaaaa",
            state={"updated_at": _iso(1), "iterations": [], "inflight": {
                "candidate": {"hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "row": {"hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "lease": {"admitted": True}}}, events=[], checkpoint=None,
            operation_observation=terminal, correctness_observation=None,
            postbuild_observation={
                "first_incomplete_stage": "correctness", "receipts": {},
                "process_progress": None},
            claim_observation={
                "claim_held": True, "claim_released": False,
                "identity_live": True, "claim_id": "akd-fixture",
                "device_id": "mi210_0", "acquired_at": _iso(3),
                "released_at": None},
            refusal_observation=None, refusal_history_observations=[],
            now=datetime.now(timezone.utc).timestamp())
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(activity["phase"]["id"], "correctness")
        self.assertEqual(pipeline["source_materialization"]["state"], "complete")
        self.assertEqual(pipeline["build"]["state"], "complete")
        self.assertEqual(pipeline["evidence_binding"]["state"], "complete")
        self.assertEqual(pipeline["correctness"]["state"], "running")
        self.assertTrue(activity["gpu"]["expected_now"])
        self.assertTrue(activity["gpu"]["claim_held"])
        self.assertTrue(activity["gpu"]["screen_started"])

    def test_v25_terminal_correctness_and_claim_bind_active_graphs_off_screen(
            self) -> None:
        campaign = "ak-discovery-" + "a" * 16
        acquired_at = _iso(90)
        completed_at = _iso(30)
        terminal = {
            "stage": "evidence_binding", "state": "running",
            "arm": "complete", "started_at": _iso(120),
            "build_key": "7" * 64, "attempt": "attempt-000001",
            "source_materialized": True,
        }
        correctness = {
            "started_at": acquired_at, "acquired_at": acquired_at,
            "completed_at": completed_at, "elapsed_s": 60.0,
            "passed": 1139, "total": 1139,
            "summary": "1139/1139 tests passed", "campaign_id": campaign,
            "claim_id": "akd-975298e22b074ccb", "device_id": "mi210_0",
            "claim_released": False,
        }
        postbuild = {
            "completed": [
                "correctness", "correctness_validation",
                "candidate_attribution", "anchor_attribution",
                "dispatch_proof", "profile",
            ],
            "first_incomplete_stage": "measurement_graphs_off_screen",
            "correctness_execution": correctness,
            "receipts": {}, "process_progress": None, "transitions": [],
            "repetition": 1, "arm_order": ["anchor", "candidate"],
        }
        claim = {
            "claim_held": True, "claim_released": False,
            "identity_live": True, "campaign_id": campaign,
            "claim_id": correctness["claim_id"],
            "device_id": correctness["device_id"],
            "acquired_at": acquired_at, "released_at": None,
        }
        state = {"updated_at": _iso(1), "iterations": [], "inflight": {
            "candidate": {
                "hypothesis_id": "akh-v2-q5-type-specific-dequant"},
            "row": {"hypothesis_id":
                    "akh-v2-q5-type-specific-dequant"},
            "lease": {"admitted": True, "repetition": 1},
        }}
        arguments = dict(
            lock_held=True, campaign_id=campaign, state=state, events=[],
            checkpoint=None, operation_observation=terminal,
            correctness_observation=None, postbuild_observation=postbuild,
            claim_observation=claim, refusal_observation=None,
            refusal_history_observations=[],
            now=datetime.now(timezone.utc).timestamp())
        activity = server._discovery_activity(**arguments)
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(activity["phase"]["id"],
                         "measurement_graphs_off_screen")
        self.assertEqual(activity["stage_contract"]["first_incomplete_stage"],
                         "measurement_graphs_off_screen")
        self.assertTrue(activity["correctness"]["execution_completed"])
        self.assertEqual(activity["correctness"]["summary"],
                         "1139/1139 tests passed")
        self.assertTrue(activity["gpu"]["expected_now"])
        self.assertTrue(activity["gpu"]["claim_held"])
        self.assertTrue(activity["gpu"]["screen_started"])
        for stage in ("source_materialization", "build", "evidence_binding",
                      "correctness", "correctness_validation",
                      "candidate_attribution", "anchor_attribution",
                      "dispatch_proof", "profile"):
            self.assertEqual(pipeline[stage]["state"], "complete", stage)

        for key, value in (
                ("claim_id", "akd-0000000000000000"),
                ("device_id", "mi210_1"),
                ("campaign_id", "ak-discovery-" + "b" * 16),
                ("acquired_at", _iso(89))):
            foreign = dict(claim)
            foreign[key] = value
            with self.subTest(foreign_identity=key):
                refused = server._discovery_activity(
                    **{**arguments, "claim_observation": foreign})
                self.assertFalse(refused["gpu"]["claim_held"])
                self.assertFalse(refused["gpu"]["expected_now"])
                self.assertEqual(refused["phase"]["id"],
                                 "resource_admission")

        suppressed = server._discovery_activity(
            **{**arguments, "operation_observation": None})
        self.assertEqual(suppressed["phase"]["id"],
                         "source_materialization")
        self.assertFalse(suppressed["correctness"]["execution_completed"])
        self.assertFalse(suppressed["gpu"]["expected_now"])

    def test_v25_correctness_projection_requires_exact_outer_claim_identity(
            self) -> None:
        operation_key = "6" * 64
        manifest_sha = "5" * 64
        campaign = "ak-discovery-" + "a" * 16
        operation = self.operations / operation_key
        operation.mkdir()
        (operation / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_operation.v1",
            "operation_key": operation_key,
            "manifest_sha256": manifest_sha,
        }))
        (operation / "evidence-policy.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_execution_policy.v2",
            "manifest_sha256": manifest_sha,
            "attribution_arm_order": ["anchor", "candidate"],
        }))
        acquired_at = _iso(90)
        ended_at = _iso(30)
        expires_at = _iso(-3500)
        claim_id = "akd-975298e22b074ccb"
        claim = {
            "schema": "epyc.autokernel.device_claim_receipt.v1",
            "claim_id": claim_id, "campaign_id": campaign,
            "device_id": "mi210_0",
            "purpose": "AutoKernel GPU source proof and throughput",
            "holder_pid": os.getpid(), "holder_start_ticks": 123456,
            "holder_boot_id": Path(
                "/proc/sys/kernel/random/boot_id").read_text().strip(),
            "holder_label": "autokernel-discovery-controller",
            "host": os.uname().nodename,
            "lock_path": "/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock",
            "acquired_at": acquired_at, "expires_at": expires_at,
            "released_at": None, "reclaimed_from": None, "state": "held",
        }
        base = {
            "schema": "epyc.autokernel.targeted_correctness_receipt.v3",
            "authority": "nonpromotable_candidate_only_discovery",
            "promotion_claim": False, "manifest_sha256": manifest_sha,
            "campaign_id": campaign, "status": "complete", "result": "PASS",
            "overall": "OK", "passed_cases": 1139, "expected_cases": 1139,
            "summary": "1139/1139 tests passed", "exit_code": 0,
            "exact_case_ok": True, "device_id": "mi210_0",
            "device_claim_open": claim,
            "device_claim_borrowed_phase_end": {
                "schema": "epyc.autokernel.borrowed_device_claim_phase.v1",
                "campaign_id": campaign, "device_id": "mi210_0",
                "mode": "borrowed_outer_reservation",
                "outer_claim_id": claim_id, "phase_ended_at": ended_at,
                "physical_release": False,
            },
            "residency_witness": {
                "device_claim_mode": "borrowed_outer_reservation",
                "outer_claim_id": claim_id, "overlapped": True,
                "claim_verified_before": True, "claim_verified_after": True,
                "overlap_sample_count": 2, "max_vram_bytes": 1024,
            },
            "ended_at": ended_at,
        }
        receipt_path = operation / "proof/correctness/receipt.json"
        self._private_json(receipt_path, base)
        state = {"inflight": {
            "operation_key": operation_key,
            "candidate": {
                "source_manifest_sha256": manifest_sha,
                "manifest": {"campaign_id": campaign}},
            "lease": {"repetition": 1},
        }}
        observed = server._discovery_postbuild_observation(
            self.operations, state)
        self.assertEqual(observed["correctness_execution"]["summary"],
                         "1139/1139 tests passed")
        self.assertEqual(observed["correctness_execution"]["claim_id"],
                         claim_id)

        for mutation in ("missing_holder_boot_id", "foreign_campaign",
                         "foreign_borrowed_claim", "no_residency_overlap"):
            body = json.loads(receipt_path.read_text())
            body.pop("receipt_sha256")
            if mutation == "missing_holder_boot_id":
                body["device_claim_open"].pop("holder_boot_id")
            elif mutation == "foreign_campaign":
                body["campaign_id"] = "ak-discovery-" + "b" * 16
            elif mutation == "foreign_borrowed_claim":
                body["device_claim_borrowed_phase_end"]["outer_claim_id"] = (
                    "akd-0000000000000000")
            else:
                body["residency_witness"]["overlapped"] = False
            self._private_json(receipt_path, body)
            with self.subTest(mutation=mutation):
                refused = server._discovery_postbuild_observation(
                    self.operations, state)
                self.assertIsNone(refused["correctness_execution"])
            self._private_json(receipt_path, base)

    def test_v25_source_claim_journal_is_exact_fresh_and_process_bound(
            self) -> None:
        claims = self.operations / "claims"
        claims.mkdir()
        path = claims / "device.jsonl"
        campaign = "ak-discovery-" + "a" * 16
        now = datetime.now(timezone.utc)
        acquired = (now - timedelta(seconds=2)).isoformat()
        expires = (now + timedelta(seconds=300)).isoformat()
        pid = os.getpid()
        ticks = 424242
        receipt = {
            "schema": "epyc.autokernel.device_claim_receipt.v1",
            "claim_id": "akd-975298e22b074ccb", "campaign_id": campaign,
            "device_id": "mi210_0",
            "purpose": "AutoKernel GPU source proof and throughput",
            "holder_pid": pid, "holder_start_ticks": ticks,
            "holder_boot_id": Path(
                "/proc/sys/kernel/random/boot_id").read_text().strip(),
            "holder_label": "autokernel-discovery-controller",
            "host": os.uname().nodename,
            "lock_path": "/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock",
            "acquired_at": acquired, "expires_at": expires,
            "released_at": None, "reclaimed_from": None, "state": "held",
        }
        row = {
            "schema": "epyc.autokernel.device_claim_journal.v1",
            "kind": "claim_acquired", "created_at": now.isoformat(),
            "device_id": "mi210_0", "host": os.uname().nodename,
            "record_id": "akj-0123456789abcdef", "writer_pid": pid,
            "detail": {"attempts": 1, "claim_id": receipt["claim_id"],
                       "receipt": receipt, "reclaimed": False},
        }

        def write(value: dict, *, canonical: bool = True) -> None:
            raw = (server._canonical_json_bytes(value) if canonical else
                   json.dumps(value, indent=2).encode())
            path.write_bytes(raw + b"\n")

        def observe(*, proc_ticks: int = ticks) -> dict | None:
            with (mock.patch.object(server, "_discovery_lock_held",
                                    return_value=True),
                  mock.patch.object(server, "_discovery_proc_stat",
                                    return_value=("S", pid, proc_ticks))):
                return server._discovery_claim_observation(
                    self.operations, campaign)

        write(row)
        valid = observe()
        self.assertTrue(valid["claim_held"])
        self.assertFalse(valid["claim_released"])

        self.assertFalse(observe(proc_ticks=ticks + 1)["claim_held"])

        expired = json.loads(json.dumps(row))
        expired["detail"]["receipt"]["expires_at"] = (
            now - timedelta(seconds=1)).isoformat()
        write(expired)
        self.assertFalse(observe()["claim_held"])

        mutations = {}
        future = json.loads(json.dumps(row))
        future["created_at"] = (now + timedelta(seconds=60)).isoformat()
        mutations["future_created"] = future
        malformed = json.loads(json.dumps(row))
        malformed["created_at"] = "not-a-time"
        mutations["malformed_created"] = malformed
        stale_acquired = json.loads(json.dumps(row))
        stale_acquired["detail"]["receipt"]["acquired_at"] = (
            now - timedelta(days=7)).isoformat()
        mutations["stale_acquired"] = stale_acquired
        extra = json.loads(json.dumps(row)); extra["invented"] = True
        mutations["extra_row_key"] = extra
        missing = json.loads(json.dumps(row)); missing.pop("record_id")
        mutations["missing_row_key"] = missing
        state_mismatch = json.loads(json.dumps(row))
        state_mismatch["detail"]["receipt"]["state"] = "released"
        mutations["state_mismatch"] = state_mismatch
        released_mismatch = json.loads(json.dumps(row))
        released_mismatch["detail"]["receipt"]["released_at"] = now.isoformat()
        mutations["kind_release_mismatch"] = released_mismatch
        wrong_boot = json.loads(json.dumps(row))
        wrong_boot["detail"]["receipt"]["holder_boot_id"] = (
            "00000000-0000-0000-0000-000000000000")
        mutations["wrong_boot"] = wrong_boot
        wrong_lock = json.loads(json.dumps(row))
        wrong_lock["detail"]["receipt"]["lock_path"] = "/tmp/foreign.lock"
        mutations["wrong_lock"] = wrong_lock
        for name, mutated in mutations.items():
            write(mutated)
            with self.subTest(mutation=name):
                self.assertIsNone(observe())

        historical_acquired = json.loads(json.dumps(row))
        historical_at = now - timedelta(days=8)
        historical_acquired["created_at"] = historical_at.isoformat()
        historical_acquired["detail"]["receipt"]["acquired_at"] = (
            historical_at.isoformat())
        historical_acquired["detail"]["receipt"]["expires_at"] = (
            historical_at + timedelta(hours=1)).isoformat()
        stale_release = json.loads(json.dumps(historical_acquired))
        stale_release["kind"] = "claim_released"
        stale_release["created_at"] = now.isoformat()
        stale_release_at = (now - timedelta(days=7)).isoformat()
        stale_release["detail"]["receipt"]["released_at"] = stale_release_at
        stale_release["detail"] = {
            "claim_id": receipt["claim_id"],
            "payload_clear_error": None,
            "receipt": stale_release["detail"]["receipt"],
            "released_at": stale_release_at,
            "revocation_read_error": None,
        }
        path.write_bytes(server._canonical_json_bytes(historical_acquired) +
                         b"\n" + server._canonical_json_bytes(stale_release) +
                         b"\n")
        self.assertIsNone(observe())

        write(row, canonical=False)
        self.assertIsNone(observe())

    def test_v11_pre_screen_intent_keeps_active_anchor_build_fail_closed(self) -> None:
        """Exact v11 boundary: declared proof plan cannot invent correctness."""
        manifest_sha = "6bb3454fac66b311f126311837b85cad11af609d62c349a5eafb1b5674525569"
        proposal_sha = "c02c48262a7634cf023ec454547517925f8d1df6c5158ee90a28eb85414e869a"
        operation_key = "3818df9f05218f6b2583c7d8d4f1436d849e874e19ea47841b9d7055ce2df307"
        build_key = "d21841b48fca9adbd410d8f4cadcf91f41087567088197bc85bf88ce633d70f5"
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(3), "next": 1, "complete": False,
            "pending": None, "planning": None, "iterations": [],
            "inflight": {
                "phase": "prebuild_probe", "operation_key": operation_key,
                "candidate": {
                    "source_manifest_sha256": manifest_sha,
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                    "manifest": {"candidate_id": "akc-discovery-1",
                                 "campaign_id": "ak-discovery-8e4eee8d36dc7e9e"},
                },
                "row": {"proposal_sha256": proposal_sha,
                        "hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "lease": {"admitted": True, "phase": "prebuild_probe",
                          "repetition": 1,
                          "device_claim_probe_released": {"released_at": _iso(4)}},
                "confirmation": False,
            },
        }))
        operation = self.operations / operation_key
        operation.mkdir()
        (operation / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_operation.v1",
            "operation_key": operation_key,
            "manifest_sha256": manifest_sha,
        }))
        # The v11 incident had no evidence-policy or any correctness receipt.
        entry = self.operations / "build-cache/entries" / build_key
        locks = self.operations / "build-cache/locks"
        entry.mkdir(parents=True)
        locks.mkdir(parents=True)
        (entry / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key,
            "build_contract": {
                "build_key": build_key,
                "patch_bundle_sha256": manifest_sha,
                "proposal_sha256": proposal_sha,
                "deployment_config_sha256": "a" * 64,
            },
        }))
        logs = entry / "logs"
        logs.mkdir()
        (logs / "akc-anchor.log.build-sandbox.json").write_text("{}")
        build_lock = locks / f"build-{build_key}.lock"
        build_lock.touch()
        with build_lock.open("r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "build")
        self.assertEqual(activity["phase"]["label"],
                         "Compiling anchor arm 1 of 2")
        self.assertFalse(activity["correctness"]["execution_started"])
        self.assertFalse(activity["gpu"]["expected_now"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["resource_admission"]["state"], "complete")
        self.assertEqual(pipeline["source_materialization"]["state"], "running")
        self.assertEqual(pipeline["build"]["state"], "running")
        for stage in ("evidence_binding", "correctness",
                      "correctness_validation", "candidate_attribution"):
            self.assertEqual(pipeline[stage]["state"], "not_reached", stage)
        self.assertEqual(activity["stage_contract"]["first_incomplete_stage"],
                         "build")

    def test_completed_build_then_factory_error_is_evidence_binding_failure(self) -> None:
        manifest_sha = "b" * 64
        proposal_sha = "c" * 64
        build_key = "d" * 64
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(2), "next": 1, "complete": False,
            "iterations": [],
            "inflight": {
                "candidate": {"source_manifest_sha256": manifest_sha},
                "row": {"proposal_sha256": proposal_sha},
                "lease": {"admitted": True},
                "exception": {
                    "type": "DeploymentFactoryError",
                    "message": "candidate manifest canonical carrier hash mismatch",
                },
            },
        }))
        entry = self.operations / "build-cache/entries" / build_key
        entry.mkdir(parents=True)
        contract = {
            "build_key": build_key,
            "patch_bundle_sha256": manifest_sha,
            "proposal_sha256": proposal_sha,
            "deployment_config_sha256": "a" * 64,
        }
        (entry / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key,
            "build_contract": contract,
        }))
        self._complete_build(entry, build_key=build_key,
                             manifest_sha=manifest_sha, contract=contract)

        activity = server.discovery_live_payload()["activity"]

        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "evidence_binding")
        self.assertIn("after completed build", activity["phase"]["label"])
        self.assertEqual(activity["failure"]["stage"], "evidence_binding")
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["source_materialization"]["state"], "complete")
        self.assertEqual(pipeline["build"]["state"], "complete")
        self.assertEqual(pipeline["evidence_binding"]["state"], "failed")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "build_transaction_complete")

    def test_v10_correctness_parser_failure_preserves_completed_gpu_execution(self) -> None:
        self._write_v10_correctness_parser_terminal()

        activity = server.discovery_live_payload()["activity"]

        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "correctness_validation")
        self.assertEqual(activity["phase"]["label"],
                         "Correctness result parsing failed after GPU proof")
        self.assertEqual(activity["failure"]["stage"], "correctness_validation")
        self.assertTrue(activity["failure"]["gpu_screen_started"])
        self.assertTrue(activity["failure"]["correctness_execution_completed"])
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertTrue(activity["gpu"]["screen_started"])
        self.assertTrue(activity["gpu"]["claim_released"])
        self.assertIn("1139/1139 tests passed", activity["gpu"]["detail"])
        self.assertEqual(activity["correctness"]["summary"],
                         "1139/1139 tests passed")
        self.assertTrue(activity["correctness"]["execution_completed"])
        self.assertFalse(activity["correctness"]["validation_passed"])
        self.assertGreaterEqual(activity["correctness"]["elapsed_s"], 54)
        self.assertLessEqual(activity["correctness"]["elapsed_s"], 56)
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        for stage in ("source_materialization", "build", "evidence_binding",
                      "correctness"):
            self.assertEqual(pipeline[stage]["state"], "complete", stage)
        self.assertEqual(pipeline["correctness_validation"]["state"], "failed")
        for stage in ("dispatch_proof", "profile", "benchmark", "decision"):
            self.assertEqual(pipeline[stage]["state"], "not_reached", stage)
        for stage in ("replication_s1", "replication_s2"):
            self.assertEqual(pipeline[stage]["state"], "not_reached", stage)
        self.assertIsNone(activity["stage_contract"]["replication"])
        self.assertEqual(activity["transitions"][-2]["event"],
                         "correctness_execution_complete")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "correctness_validation_failed")

    def test_correctness_observation_rejects_a_symlinked_release_receipt(self) -> None:
        self._write_v10_correctness_parser_terminal()
        operation = self.operations / ("8" * 64)
        release = operation / "reservation-release.json"
        outside = Path(self.temp.name) / "outside-release.json"
        outside.write_bytes(release.read_bytes())
        release.unlink()
        release.symlink_to(outside)

        activity = server.discovery_live_payload()["activity"]

        self.assertFalse(activity["gpu"]["screen_started"])
        self.assertFalse(activity["correctness"]["execution_started"])
        self.assertNotEqual(activity["phase"]["id"], "correctness_validation")

    def test_terminal_source_materialization_failure_is_not_idle_or_resumable(self) -> None:
        self._write_events([
            _event("planner_started", seconds_ago=240),
            _event("planner_completed", seconds_ago=180, result={"returncode": 0}),
            _event("critic_started", seconds_ago=175, channel="autokernel",
                   model="claude-fable-5", provider="claude"),
            _event("critic_completed", seconds_ago=120, channel="autokernel",
                   model="claude-fable-5", provider="claude",
                   result={"decision": "accept", "returncode": 0}),
        ])
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(90),
            "next": 1,
            "complete": False,
            "terminal_reason": None,
            "pending": None,
            "iterations": [],
            "inflight": {
                "lease": {"phase": "prebuild_probe", "device_id": "mi210_0"},
                "operation_key": "operation-source-materialization",
                "exception": {
                    "type": "SourceCandidateError",
                    "message": "candidate diff derives an undeclared file-scope symbol",
                },
            },
        }))
        journal = self.state / "journal"
        journal.mkdir()
        (journal / "events.jsonl").write_text("".join([
            json.dumps({
                "campaign_id": None,
                "event_id": "akj-000000000001-pre-screen",
                "journal_schema": "epyc.autokernel.journal_entry.v1",
                "kind": "STOP_STATE",
                "payload": {"controller_state_sha256": "b" * 64,
                            "state": "discovery_pre_screen_intent"},
                "record_id": None,
                "seq": 1,
                "written_at": _iso(91),
            }) + "\n",
            json.dumps({
                "campaign_id": None,
                "event_id": "akj-000000000002-ambiguous",
                "journal_schema": "epyc.autokernel.journal_entry.v1",
                "kind": "STOP_STATE",
                "payload": {"controller_state_sha256": "c" * 64,
                            "state": "discovery_screen_ambiguous"},
                "record_id": None,
                "seq": 2,
                "written_at": _iso(90),
            }) + "\n",
        ]))

        payload = server.discovery_live_payload()  # lock is not held
        activity = payload["activity"]

        self.assertFalse(payload["active"])
        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "source_materialization")
        self.assertTrue(activity["failure"]["detected"])
        self.assertEqual(activity["failure"]["stage"], "source_materialization")
        self.assertIn("SourceCandidateError", activity["failure"]["detail"])
        self.assertTrue(activity["failure"]["recovery"])
        self.assertFalse(activity["failure"]["source_proof_created"])
        self.assertFalse(activity["failure"]["runner_started"])
        self.assertFalse(activity["failure"]["gpu_screen_started"])
        self.assertNotEqual(activity["waiting_on"].lower(), "nothing")
        self.assertTrue(activity["checkpoint"]["available"])
        self.assertEqual(activity["checkpoint"]["kind"], "STOP_STATE")
        self.assertEqual(activity["checkpoint"]["state"],
                         "discovery_screen_ambiguous")
        self.assertFalse(activity["resume"]["possible"])
        self.assertEqual(activity["resume"]["recoverability"], "ambiguous")
        self.assertTrue(activity["resume"]["detail"])
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])

    def test_abandoned_and_retest_history_is_summarized_separately(self) -> None:
        self._write_events([_event("planner_started", seconds_ago=20)])
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(5),
            "next": 4,
            "complete": False,
            "terminal_reason": None,
            "pending": None,
            "inflight": None,
            "iterations": [
                {"turn": 1, "hypothesis_id": "akh-old-a", "status": "abandoned"},
                {"turn": 2, "hypothesis_id": "akh-old-b", "status": "abandoned"},
                {"turn": 3, "hypothesis_id": "akh-retest", "status": "retest"},
            ],
        }))

        history = self._active_payload()["activity"]["history"]
        self.assertEqual(history["abandoned_count"], 2)
        self.assertEqual(history["retest_count"], 1)
        self.assertIn("2", history["summary"])
        self.assertIn("abandoned", history["summary"].lower())
        self.assertIn("retest", history["summary"].lower())
        self.assertEqual(len(history["rows"]), 3)

    def test_newer_sealed_bundle_does_not_mask_failed_launched_campaign(self) -> None:
        """A config mtime is availability, never a replacement for run truth."""
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(5),
            "next": 1,
            "complete": False,
            "terminal_reason": None,
            "pending": None,
            "iterations": [],
            "inflight": {
                "phase": "screen",
                "exception": {
                    "type": "DeploymentFactoryError",
                    "message": "candidate manifest canonical carrier hash mismatch",
                },
            },
        }))
        next_bundle = self.bundle.parent / "campaign-v6"
        next_state = next_bundle / "state"
        next_operations = next_bundle / "operations"
        (next_bundle / "config").mkdir(parents=True)
        next_state.mkdir()
        (next_operations / "live").mkdir(parents=True)
        (next_state / "controller.run.lock").touch()
        next_config = next_bundle / "config/deployment.json"
        next_config.write_text(json.dumps({
            "config_sha256": "b" * 64,
            "controller": {
                "state_root": str(next_state),
                "operations_root": str(next_operations),
            },
        }))
        newer = datetime.now(timezone.utc).timestamp() + 60
        os.utime(next_config, (newer, newer))

        payload = server.discovery_live_payload()

        self.assertEqual(payload["deployment"], "campaign-a")
        self.assertEqual(payload["activity"]["status"], "failed")
        self.assertIn("canonical carrier hash mismatch",
                      payload["activity"]["failure"]["detail"])
        sealed = payload["newest_unlaunched_deployment"]
        self.assertTrue(sealed["available"])
        self.assertEqual(sealed["deployment"], "campaign-v6")
        self.assertEqual(sealed["launch_state"], "not_launched")

    def test_active_v7_supersedes_older_unlaunched_v6(self) -> None:
        base_stamp = (self.bundle / "config/deployment.json").stat().st_mtime

        def add_bundle(name: str, stamp: float) -> tuple[Path, Path]:
            bundle = self.bundle.parent / name
            state = bundle / "state"
            operations = bundle / "operations"
            (bundle / "config").mkdir(parents=True)
            state.mkdir()
            (operations / "live").mkdir(parents=True)
            (state / "controller.run.lock").touch()
            config_path = bundle / "config/deployment.json"
            config_path.write_text(json.dumps({
                "config_sha256": ("6" if name.endswith("v6") else "7") * 64,
                "controller": {
                    "state_root": str(state),
                    "operations_root": str(operations),
                },
            }))
            os.utime(config_path, (stamp, stamp))
            return state, operations

        add_bundle("campaign-v6", base_stamp + 10)
        v7_state, _ = add_bundle("campaign-v7", base_stamp + 20)

        with (v7_state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()

        self.assertTrue(payload["active"])
        self.assertEqual(payload["deployment"], "campaign-v7")
        self.assertEqual(payload["activity"]["status"], "running")
        self.assertFalse(payload["newest_unlaunched_deployment"]["available"])


if __name__ == "__main__":
    unittest.main()
