#!/bin/bash
# Read-only validator for the human-only E8 quality-baseline apply transaction.
set -euo pipefail

ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
SOURCE_ROOT="${EPYC_SOURCE_ROOT:-/mnt/raid0/llm/epyc-root}"
ORCH="${EPYC_ORCH:-/mnt/raid0/llm/epyc-orchestrator}"
RESEARCH="${EPYC_RESEARCH:-/mnt/raid0/llm/epyc-inference-research}"
PYTHON="${EPYC_PYTHON:-$ORCH/.venv/bin/python}"
STATE="$ORCH/orchestration/autopilot_state.json"
JOURNAL="$ORCH/orchestration/autopilot_journal.jsonl"
RUNNER="$ORCH/scripts/benchmark/run_e8_quality_baseline_reseed.py"
RECEIPT="$ROOT/artifacts/operator/ratify_e8_quality_baseline_protocol_repair_20260727.json"
EVIDENCE="${E8_QUALITY_BASELINE_EVIDENCE:-$ROOT/artifacts/operator/e8_quality_baseline_evidence_20260726/e8_quality_baseline_evidence.json}"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

numeric_trial_count() {
    (cd "$ORCH"; "$PYTHON" - "$STATE" <<'PY'
import json
import sys
sys.path.insert(0, "scripts/autopilot")
from autopilot import _frontier_rerun_completed_numeric_trials
from experiment_journal import ExperimentJournal
state = json.load(open(sys.argv[1], encoding="utf-8"))
print(_frontier_rerun_completed_numeric_trials(state.get("frontier_rerun_required") or {}, ExperimentJournal()))
PY
    )
}

validate_evidence() {
    local evidence="$1"
    [[ -f "$evidence" ]] || fail "E8 full-pool evidence manifest is not staged: $evidence"
    [[ -f "$RUNNER" ]] || fail "canonical E8 evidence runner is missing: $RUNNER"
    "$PYTHON" - "$evidence" "$RECEIPT" "$RUNNER" "$SOURCE_ROOT" "$ORCH" "$RESEARCH" <<'PY'
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys


E8_BOUNDARY = 1785004723.0
EXPECTED_PROBES = [
    "architect_general",
    "coder_escalation/frontdoor/worker_summarize",
    "ingest_long_context",
    "toolrunner/worker_general/worker_math",
    "vision_escalation",
    "worker_vision",
]
RECEIPT_KEYS = {
    "schema",
    "decision",
    "era",
    "ratified_at",
    "operator_attestation",
    "t2_decision",
    "protocol",
    "t1_core_file_sha256",
    "expected_probe_groups",
    "acceptance",
    "sha256",
    "repository_heads",
    "supersedes",
}
PROTOCOL_KEYS = {
    "protocol_id",
    "seed",
    "repetitions",
    "generation_concurrency",
    "scoring_concurrency",
    "request_timeout_s",
    "frontdoor_request_contract",
    "watcher_contract",
    "baseline_mode",
    "route_policy",
    "selected_ports",
    "runtime_topology",
    "runtime_facts_sha256",
    "runtime_binding",
    "llama_source_provenance",
    "measurement_source_sha256",
    "judge_defaults",
    "expected_probe_groups",
    "tiers",
}
RUNTIME_BINDING_KEYS = {
    "runtime_facts_sha256",
    "stack_priors_sha256",
    "orchestrator_state_sha256",
    "model_registry_sha256",
    "lean_registry_sha256",
    "stack_numa_mode",
    "selected_ports",
    "server_pids",
    "server_binaries",
    "server_cmdlines",
    "server_cmdline_sha256",
    "server_model_flags",
    "server_state_model_paths",
    "runtime_artifacts",
    "llama_server",
    "llama_source_provenance",
    "runtime_topology",
    "llama_server_sha256",
    "llama_server_version",
}
RESPONSE_KEYS = {
    "qid",
    "suite",
    "scoring_method",
    "answer",
    "correct",
    "error",
    "partial",
    "degraded",
    "route_used",
    "scoring_config_sha256",
}


def fail(message):
    raise SystemExit(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def valid_sha256(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def finite(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        fail(f"{label} must be finite")


def same_float(left, right):
    return (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and math.isfinite(left)
        and math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-12)
    )


def iso_after(value, label):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        fail(f"{label} is not ISO-8601")
    if parsed.tzinfo is None or parsed.astimezone(timezone.utc).timestamp() < E8_BOUNDARY:
        fail(f"{label} predates E8")


def load(path, label):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {label}: {exc}")


def flag_values(cmdline, *flags):
    values = []
    for index, token in enumerate(cmdline):
        if token in flags and index + 1 < len(cmdline):
            values.append(cmdline[index + 1])
            continue
        for flag in flags:
            prefix = f"{flag}="
            if token.startswith(prefix):
                values.append(token[len(prefix):])
    return values


manifest_path = Path(sys.argv[1]).resolve()
expected_receipt_path = Path(sys.argv[2]).resolve()
expected_runner_path = Path(sys.argv[3]).resolve()
source_root = Path(sys.argv[4]).resolve()
orchestrator_root = Path(sys.argv[5]).resolve()
research_root = Path(sys.argv[6]).resolve()
bundle_root = manifest_path.parent
if bundle_root.name.startswith("."):
    fail("staging evidence is never validator-acceptable")


def contained_path(path_text, label):
    if not isinstance(path_text, str) or not path_text:
        fail(f"{label} path is malformed")
    path = Path(path_text)
    if not path.is_absolute():
        fail(f"{label} path is not absolute")
    resolved = path.resolve()
    if str(resolved) != path_text:
        fail(f"{label} path is not canonical")
    try:
        resolved.relative_to(bundle_root)
    except ValueError:
        fail(f"{label} resolves outside the evidence bundle")
    return resolved


def git_head(path):
    try:
        head = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        fail(f"cannot resolve repository head for {path}: {exc}")
    if re.fullmatch(r"[0-9a-f]{40,64}", head) is None:
        fail(f"repository head is malformed for {path}")
    return head


def current_artifact_identity(path):
    try:
        resolved = path.resolve(strict=True)
        info = resolved.stat()
    except OSError as exc:
        fail(f"cannot inspect runtime artifact {path}: {exc}")
    return {
        "path": str(resolved),
        "st_dev": info.st_dev,
        "st_ino": info.st_ino,
        "st_size": info.st_size,
        "st_mtime_ns": info.st_mtime_ns,
        "sha256": digest(resolved),
    }


manifest = load(manifest_path, "evidence manifest")
expected_top = {
    "schema",
    "eval_quality_era",
    "source_records",
    "replacement",
    "protocol_receipt",
    "runner",
    "run_seal_path",
}
if not isinstance(manifest, dict) or set(manifest) != expected_top:
    fail("evidence manifest has unexpected or missing top-level keys")
if (
    manifest["schema"] != "epyc.e8_quality_baseline_evidence.v2"
    or manifest["eval_quality_era"] != "E8"
):
    fail("evidence manifest is not an E8 quality-baseline proposal")

receipt_ref = manifest["protocol_receipt"]
if not isinstance(receipt_ref, dict) or set(receipt_ref) != {"path", "sha256"}:
    fail("protocol receipt reference is malformed")
receipt_path = Path(receipt_ref["path"]).resolve()
if receipt_path != expected_receipt_path:
    fail("protocol receipt is not at the canonical operator path")
if not receipt_path.is_file() or digest(receipt_path) != receipt_ref["sha256"]:
    fail("protocol receipt hash mismatch")

runner_ref = manifest["runner"]
if not isinstance(runner_ref, dict) or set(runner_ref) != {"path", "sha256"}:
    fail("runner reference is malformed")
runner_path = Path(runner_ref["path"]).resolve()
runner_hash = digest(expected_runner_path)
if (
    runner_path != expected_runner_path
    or runner_ref["sha256"] != runner_hash
    or digest(runner_path) != runner_hash
):
    fail("manifest runner identity does not match the canonical runner")

receipt = load(receipt_path, "protocol receipt")
if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
    fail("protocol receipt structure is invalid")
protocol = receipt["protocol"]
if (
    receipt["schema"] != "epyc.operator_e8_quality_baseline_protocol.v2"
    or receipt["decision"] != "RATIFY-E8-QUALITY-BASELINE-PROTOCOL-REPAIR-20260727"
    or receipt["era"] != "E8"
    or not isinstance(receipt["operator_attestation"], str)
    or not receipt["operator_attestation"].strip()
):
    fail("protocol receipt is not an operator-ratified E8 protocol")
iso_after(receipt["ratified_at"], "protocol ratification timestamp")
if receipt["sha256"] != {"runner": runner_hash}:
    fail("protocol receipt does not bind the canonical runner hash")
heads = receipt["repository_heads"]
if (
    not isinstance(heads, dict)
    or set(heads) != {"epyc_root", "epyc_orchestrator", "epyc_inference_research"}
    or not all(isinstance(head, str) and re.fullmatch(r"[0-9a-f]{40,64}", head) for head in heads.values())
):
    fail("protocol receipt repository heads are malformed")
current_heads = {
    "epyc_root": git_head(source_root),
    "epyc_orchestrator": git_head(orchestrator_root),
    "epyc_inference_research": git_head(research_root),
}
if heads != current_heads:
    fail("protocol receipt repository heads differ from current sources")
expected_supersedes = {
    "historical_receipt": {
        "path": str((source_root / "artifacts/operator/ratify_e8_quality_baseline_protocol_20260726.json").resolve()),
        "sha256": "f79ac3664ae2d8eabe181c095afc55a94ee61a49dc19d85a830ed10b4501aded",
    },
    "aborted_run_classification": {
        "path": str((source_root / "artifacts/operator/aborted-e8-quality-baseline-evidence-20260727T120846Z-monitor-and-request-timeouts/classification.json").resolve()),
        "sha256": "5660c3c38446498cdfd225a64d27da969fd62d262baf46bde2e11395212fdd44",
    },
}
if receipt["supersedes"] != expected_supersedes:
    fail("protocol receipt predecessor evidence differs")
for predecessor in receipt["supersedes"].values():
    predecessor_path = Path(predecessor["path"])
    if not predecessor_path.is_file() or digest(predecessor_path) != predecessor["sha256"]:
        fail("protocol receipt predecessor evidence hash mismatch")
if not valid_sha256(receipt["t1_core_file_sha256"]):
    fail("protocol receipt T1 core hash is malformed")
if receipt["expected_probe_groups"] != EXPECTED_PROBES:
    fail("protocol receipt probe groups differ")
acceptance = receipt["acceptance"]
if (
    not isinstance(acceptance, dict)
    or set(acceptance)
    != {
        "all_three_repetitions_clean",
        "no_monitor_gap_seconds",
        "api_groups_exact",
        "all_routes_frontdoor",
        "sealed_atomic_publish",
    }
    or acceptance["all_three_repetitions_clean"] is not True
    or acceptance["no_monitor_gap_seconds"] != 7
    or acceptance["api_groups_exact"] is not True
    or acceptance["all_routes_frontdoor"] is not True
    or acceptance["sealed_atomic_publish"] is not True
):
    fail("protocol receipt acceptance contract differs")
if not isinstance(protocol, dict) or set(protocol) != PROTOCOL_KEYS:
    fail("protocol receipt protocol structure differs")
if protocol["protocol_id"] != "e8_quality_full_pool_tier_baseline.v3":
    fail("protocol receipt does not pin the E8 runner protocol")
if (
    protocol["repetitions"] != 3
    or protocol["generation_concurrency"] != 3
    or protocol["scoring_concurrency"] != 3
    or protocol["request_timeout_s"] != 300
    or protocol["baseline_mode"] != "direct_core_only_v1"
    or protocol["route_policy"] != "frontdoor_only"
):
    fail("protocol receipt execution contract differs")
if protocol["frontdoor_request_contract"] != {
    "force_role": "frontdoor",
    "force_mode": "direct",
    "allow_delegation": False,
    "request_priority": "background",
    "workload_class": "eval_batch",
    "max_queue_wait_ms": 90000,
    "verification": "all_routes_frontdoor",
}:
    fail("protocol receipt frontdoor request contract differs")
if protocol["watcher_contract"] != {
    "active_load_scope": "per_tier_repetition",
    "allowed_probe_failure_reason": "read_timeout",
    "requires_http_200": True,
    "requires_models_loaded": 6,
    "requires_status": "degraded",
    "requires_exact_preflight_probe_urls": True,
    "preserves_binding_immutability_autopilot_checks": True,
}:
    fail("protocol receipt watcher contract differs")
if protocol["expected_probe_groups"] != EXPECTED_PROBES:
    fail("protocol receipt endpoint contract differs")
if protocol["judge_defaults"] != {
    "orchestrator_api_url": "http://127.0.0.1:8000",
    "role": "worker_general",
}:
    fail("protocol receipt judge defaults differ")

spec = importlib.util.spec_from_file_location("e8_quality_validator_runner", expected_runner_path)
if spec is None or spec.loader is None:
    fail("cannot import the canonical E8 runner")
runner_module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner_module
spec.loader.exec_module(runner_module)
if protocol["llama_source_provenance"] != runner_module.frozen_llama_source_provenance():
    fail("protocol frozen llama.cpp source provenance differs from the production v8 tree")
tier_contracts = protocol.get("tiers")
if not isinstance(tier_contracts, dict) or set(tier_contracts) != {"1", "2"}:
    fail("protocol receipt tier contracts differ")
t1_contract = tier_contracts["1"]
if not isinstance(t1_contract, dict) or not isinstance(t1_contract.get("core_id"), str):
    fail("protocol receipt T1 core identity is malformed")
tower = runner_module.EvalTower(
    url=protocol["judge_defaults"]["orchestrator_api_url"],
    timeout=1,
)
measurement_args = runner_module.parse_args(
    ["--protocol-proposal", "--t1-core-id", t1_contract["core_id"]]
)
measurement_paths = runner_module.measurement_source_paths(measurement_args)
if expected_runner_path not in measurement_paths:
    fail("canonical runner is absent from measurement source paths")
current_measurement_sources = {
    str(Path(path).resolve()): digest(Path(path).resolve()) for path in dict.fromkeys(measurement_paths)
}
if protocol["measurement_source_sha256"] != current_measurement_sources:
    fail("protocol measurement source hashes differ from current sources")

ports = protocol["selected_ports"]
if (
    not isinstance(ports, list)
    or len(ports) != 24
    or len(set(ports)) != 24
    or not all(isinstance(port, int) and not isinstance(port, bool) and 1 <= port <= 65535 for port in ports)
    or ports != sorted(ports)
):
    fail("protocol receipt selected-port contract differs")

binding = protocol["runtime_binding"]
if not isinstance(binding, dict) or set(binding) != RUNTIME_BINDING_KEYS:
    fail("protocol runtime binding structure differs")
if (
    binding["selected_ports"] != ports
    or binding["runtime_topology"] != protocol["runtime_topology"]
    or binding["runtime_facts_sha256"] != protocol["runtime_facts_sha256"]
    or binding["llama_source_provenance"] != protocol["llama_source_provenance"]
    or binding["stack_numa_mode"] != "both"
):
    fail("protocol runtime binding differs from the ratified topology")
if (
    not isinstance(binding["runtime_topology"], list)
    or [row.get("port") for row in binding["runtime_topology"] if isinstance(row, dict)] != ports
):
    fail("protocol runtime topology does not cover each selected port exactly once")
for name in (
    "runtime_facts_sha256",
    "stack_priors_sha256",
    "orchestrator_state_sha256",
    "model_registry_sha256",
    "lean_registry_sha256",
    "llama_server_sha256",
):
    if not valid_sha256(binding[name]):
        fail(f"protocol runtime binding {name} is malformed")
if "10107" not in str(binding["llama_server_version"]):
    fail("protocol runtime binding does not identify frozen llama-server 10107")
port_keys = {str(port) for port in ports}
for name in (
    "server_pids",
    "server_binaries",
    "server_cmdlines",
    "server_cmdline_sha256",
    "server_model_flags",
    "server_state_model_paths",
):
    value = binding[name]
    if not isinstance(value, dict) or set(value) != port_keys:
        fail(f"protocol runtime binding {name} does not cover every selected port")
for port in ports:
    key = str(port)
    cmdline = binding["server_cmdlines"][key]
    model_flags = binding["server_model_flags"][key]
    if (
        not isinstance(binding["server_pids"][key], int)
        or binding["server_pids"][key] <= 0
        or not isinstance(binding["server_binaries"][key], str)
        or not binding["server_binaries"][key]
        or not isinstance(binding["server_state_model_paths"][key], str)
        or not binding["server_state_model_paths"][key]
        or not isinstance(cmdline, list)
        or not cmdline
        or not all(isinstance(token, str) and token for token in cmdline)
    ):
        fail(f"protocol runtime process identity is malformed for port {port}")
    if binding["server_cmdline_sha256"][key] != canonical_hash(cmdline):
        fail(f"protocol runtime command hash differs for port {port}")
    expected_flags = {
        "model": flag_values(cmdline, "-m", "--model"),
        "mmproj": flag_values(cmdline, "--mmproj"),
        "draft_model": flag_values(cmdline, "-md", "--model-draft"),
    }
    if (
        model_flags != expected_flags
        or len(expected_flags["model"]) != 1
        or len(expected_flags["mmproj"]) > 1
        or len(expected_flags["draft_model"]) > 1
    ):
        fail(f"protocol runtime model flags differ for port {port}")
    if flag_values(cmdline, "--port") != [str(port)]:
        fail(f"protocol runtime command does not bind port {port}")
if len(set(binding["server_pids"].values())) != len(ports):
    fail("protocol runtime binding reuses a PID across selected ports")
runtime_artifacts = binding["runtime_artifacts"]
if not isinstance(runtime_artifacts, dict) or not runtime_artifacts:
    fail("protocol runtime artifact identities are missing")
seen_artifact_inodes = set()
for path_text, identity in runtime_artifacts.items():
    if (
        not isinstance(path_text, str)
        or not isinstance(identity, dict)
        or set(identity)
        != {"path", "st_dev", "st_ino", "st_size", "st_mtime_ns", "sha256"}
        or identity.get("path") != path_text
        or not valid_sha256(identity.get("sha256"))
    ):
        fail("protocol runtime artifact identity is malformed")
    current = current_artifact_identity(Path(path_text))
    if identity != current:
        fail(f"protocol runtime artifact changed: {path_text}")
    inode = (identity["st_dev"], identity["st_ino"])
    if inode in seen_artifact_inodes:
        fail("protocol runtime artifacts contain duplicate file identities")
    seen_artifact_inodes.add(inode)
canonical_binary = str(Path(binding["llama_server"]).resolve())
if (
    canonical_binary not in runtime_artifacts
    or runtime_artifacts[canonical_binary]["sha256"] != binding["llama_server_sha256"]
    or any(str(Path(path).resolve()) != canonical_binary for path in binding["server_binaries"].values())
):
    fail("protocol llama-server executable content identity differs")

t2_decision = receipt["t2_decision"]
if (
    not isinstance(t2_decision, dict)
    or set(t2_decision) != {"n", "recommended_default", "alternatives"}
    or t2_decision["n"] != 500
    or t2_decision["recommended_default"] != 500
    or t2_decision["alternatives"] != [500]
    or (protocol.get("tiers") or {}).get("2", {}).get("n") != t2_decision["n"]
):
    fail("protocol receipt T2 decision is malformed")

seal_path = contained_path(manifest["run_seal_path"], "completion seal")
if seal_path.name != "run_seal.json" or not seal_path.is_file():
    fail("completion seal is missing")
seal = load(seal_path, "completion seal")
if seal.get("schema") != "epyc.e8_quality_baseline_run_seal.v1" or seal.get("status") != "complete":
    fail("completion seal is not successful")
if (
    seal.get("manifest_sha256") != digest(manifest_path)
    or seal.get("protocol_receipt_sha256") != receipt_ref["sha256"]
    or seal.get("runner_sha256") != runner_hash
):
    fail("completion seal does not bind manifest, receipt, and runner")
bundle = seal.get("bundle_sha256")
if not isinstance(bundle, dict) or not bundle:
    fail("completion seal lacks bundle hashes")
for path_text, expected_hash in bundle.items():
    path = contained_path(path_text, "sealed artifact")
    if not path.is_file() or not valid_sha256(expected_hash) or digest(path) != expected_hash:
        fail(f"sealed bundle artifact hash mismatch: {path}")
if bundle.get(str(manifest_path)) != digest(manifest_path):
    fail("completion seal bundle does not include the manifest")


def sealed_artifact(path_text, expected_hash, label):
    path = contained_path(path_text, label)
    if (
        not path.is_file()
        or not valid_sha256(expected_hash)
        or digest(path) != expected_hash
        or bundle.get(str(path)) != expected_hash
    ):
        fail(f"{label} is missing, unsealed, or hash-mismatched")
    return path


report_path = bundle_root / "runner_report.json"
if (
    seal.get("runner_report_sha256") != digest(report_path)
    or bundle.get(str(report_path)) != digest(report_path)
):
    fail("completion seal does not bind runner report")
report = load(report_path, "runner report")
pre = report.get("preconditions") or {}
post = report.get("postconditions") or {}
checks = post.get("checks") or {}
if report.get("decision_grade") is not True or not checks or not all(value is True for value in checks.values()):
    fail("runner report contains a failed global check")
if (
    pre.get("runner_path") != str(expected_runner_path)
    or pre.get("runner_sha256") != runner_hash
    or (pre.get("file_sha256") or {}).get(str(expected_runner_path)) != runner_hash
):
    fail("runner report does not bind the canonical runner")
if (
    Path(str(pre.get("protocol_receipt"))).resolve() != expected_receipt_path
    or pre.get("protocol_receipt_sha256") != receipt_ref["sha256"]
    or (pre.get("file_sha256") or {}).get(str(expected_receipt_path)) != receipt_ref["sha256"]
):
    fail("runner report does not bind the canonical receipt")
if pre.get("runtime_binding") != binding or post.get("runtime_binding") != binding:
    fail("runner report runtime binding differs from the ratified binding")
if pre.get("file_sha256") != post.get("file_sha256"):
    fail("runner report immutable-file hashes changed")
if any(
    (pre.get("file_sha256") or {}).get(path) != source_hash
    for path, source_hash in current_measurement_sources.items()
):
    fail("runner report does not monitor every ratified measurement source")
immutable_hashes = set((pre.get("file_sha256") or {}).values())
if any(
    binding[name] not in immutable_hashes
    for name in (
        "runtime_facts_sha256",
        "stack_priors_sha256",
        "orchestrator_state_sha256",
        "model_registry_sha256",
        "lean_registry_sha256",
    )
):
    fail("runner report does not monitor every ratified runtime/config input")
if pre.get("numeric_rerun") != post.get("numeric_rerun"):
    fail("numeric rerun changed during evidence collection")
numeric = pre.get("numeric_rerun") or {}
if numeric.get("required", 0) < 16 or numeric.get("completed", 0) < numeric.get("required", 0):
    fail("numeric rerun was incomplete at evidence collection")

watch_path = sealed_artifact(post.get("watcher_path"), post.get("watcher_sha256"), "runtime watch")
try:
    watch_rows = [json.loads(line) for line in watch_path.read_text().splitlines() if line]
except json.JSONDecodeError as exc:
    fail(f"runtime watch is malformed: {exc}")
cheap_runtime_artifacts = {
    path: {key: value for key, value in identity.items() if key != "sha256"}
    for path, identity in runtime_artifacts.items()
}
if (
    not watch_rows
    or watch_rows != post.get("watcher_samples")
    or any(
        not isinstance(row, dict)
        or row.get("ok") is not True
        or row.get("runtime_artifacts") != cheap_runtime_artifacts
        for row in watch_rows
    )
):
    fail("runtime watch does not reproduce the clean monitor report")

records = manifest["source_records"]
if not isinstance(records, list) or len(records) != 2:
    fail("evidence manifest requires exactly two tier source records")
seen = set()
observed_by_tier = {}
summary_by_tier = {}
for record in records:
    keys = {
        "tier",
        "path",
        "sha256",
        "protocol_id",
        "core_id",
        "n",
        "timestamp",
        "era",
        "instrument",
        "quality",
        "question_vector_sha256",
        "scoring_vector_sha256",
    }
    if not isinstance(record, dict) or set(record) != keys:
        fail("source record contract is malformed")
    tier = record["tier"]
    if tier not in (1, 2) or tier in seen:
        fail("source records must cover tiers 1 and 2 exactly once")
    seen.add(tier)
    declared = (protocol.get("tiers") or {}).get(str(tier))
    if (
        not isinstance(declared, dict)
        or set(declared)
        != {
            "core_id",
            "n",
            "dataset_sha256",
            "scoring_vector_sha256",
            "vector_sha256",
        }
        or record["core_id"] != declared["core_id"]
        or record["n"] != declared["n"]
        or record["question_vector_sha256"] != declared["vector_sha256"]
        or record["scoring_vector_sha256"] != declared["scoring_vector_sha256"]
    ):
        fail("source record differs from ratified tier contract")
    if (
        record["protocol_id"] != protocol["protocol_id"]
        or record["era"] != "E8"
        or record["instrument"] != "dedicated_full_pool_tier_baseline"
    ):
        fail("source record protocol identity is invalid")
    iso_after(record["timestamp"], "source record timestamp")
    finite(record["quality"], "source quality")
    source_path = sealed_artifact(record["path"], record["sha256"], "source summary")
    summary = load(source_path, "source summary")
    summary_keys = {
        "tier",
        "core_id",
        "n",
        "quality",
        "per_suite_quality",
        "per_suite_counts",
        "era",
        "decision_grade",
        "observations",
        "question_vector_path",
        "question_vector_sha256",
        "scoring_vector_path",
        "scoring_vector_sha256",
        "response_artifacts",
    }
    if not isinstance(summary, dict) or set(summary) != summary_keys or summary["decision_grade"] is not True:
        fail("source summary is not decision-grade")
    if any(
        summary.get(key) != record.get(key)
        for key in ("tier", "core_id", "n", "quality", "era")
    ):
        fail("source summary differs from record")

    vector_path = sealed_artifact(
        summary["question_vector_path"],
        bundle.get(str(Path(summary["question_vector_path"]).resolve())),
        "question vector",
    )
    vector = load(vector_path, "question vector")
    vector_keys = {
        "schema",
        "era",
        "tier",
        "core_id",
        "seed",
        "n",
        "dataset_sha256",
        "per_suite_counts",
        "questions",
    }
    if not isinstance(vector, dict) or set(vector) != vector_keys:
        fail("question vector structure differs")
    if (
        vector["schema"] != "epyc.e8_quality_question_vector.v1"
        or vector["era"] != "E8"
        or vector["tier"] != tier
        or vector["n"] != record["n"]
        or vector["core_id"] != record["core_id"]
        or vector["dataset_sha256"] != declared["dataset_sha256"]
        or digest(vector_path) != summary["question_vector_sha256"]
        or canonical_hash(vector) != declared["vector_sha256"]
        or canonical_hash(vector) != record["question_vector_sha256"]
    ):
        fail("question vector does not match ratified identity")
    questions = vector["questions"]
    if not isinstance(questions, list) or len(questions) != record["n"]:
        fail("question vector count differs")
    qids = []
    for question in questions:
        if (
            not isinstance(question, dict)
            or set(question) != {"qid", "suite", "scoring_method", "scoring_config_sha256"}
            or not all(
                isinstance(question[name], str) and question[name]
                for name in ("qid", "suite", "scoring_method")
            )
            or not valid_sha256(question["scoring_config_sha256"])
        ):
            fail("question vector scoring identity is malformed")
        qids.append(question["qid"])
    if len(qids) != len(set(qids)):
        fail("question vector qids are not unique")
    vector_counts = dict(sorted(Counter(question["suite"] for question in questions).items()))
    if vector["per_suite_counts"] != vector_counts:
        fail("question vector per-suite counts are not reproducible")

    scoring_path = sealed_artifact(
        summary["scoring_vector_path"],
        bundle.get(str(Path(summary["scoring_vector_path"]).resolve())),
        "scoring vector",
    )
    scoring_vector = load(scoring_path, "scoring vector")
    scoring_keys = {
        "schema",
        "era",
        "tier",
        "core_id",
        "seed",
        "n",
        "dataset_sha256",
        "questions",
    }
    if (
        not isinstance(scoring_vector, dict)
        or set(scoring_vector) != scoring_keys
        or scoring_vector["schema"] != "epyc.e8_quality_scoring_vector.v1"
        or scoring_vector["era"] != "E8"
        or scoring_vector["tier"] != tier
        or scoring_vector["core_id"] != record["core_id"]
        or scoring_vector["seed"] != protocol["seed"]
        or scoring_vector["n"] != record["n"]
        or scoring_vector["dataset_sha256"] != declared["dataset_sha256"]
        or digest(scoring_path) != summary["scoring_vector_sha256"]
        or canonical_hash(scoring_vector) != declared["scoring_vector_sha256"]
        or canonical_hash(scoring_vector) != record["scoring_vector_sha256"]
    ):
        fail("scoring vector does not match ratified identity")
    scoring_questions = scoring_vector["questions"]
    if not isinstance(scoring_questions, list) or len(scoring_questions) != record["n"]:
        fail("scoring vector count differs")
    for public, private in zip(questions, scoring_questions):
        if (
            not isinstance(private, dict)
            or set(private)
            != {
                "qid",
                "suite",
                "scoring_method",
                "scoring_config",
                "expected",
                "prompt_sha256",
            }
            or any(
                private[name] != public[name]
                for name in ("qid", "suite", "scoring_method")
            )
            or not isinstance(private["expected"], str)
            or not isinstance(private["scoring_config"], dict)
            or public["scoring_config_sha256"]
            != canonical_hash(private["scoring_config"])
            or not valid_sha256(private["prompt_sha256"])
        ):
            fail("scoring vector row differs from public scoring identity")

    reconstructed_questions, reconstructed_core = runner_module.question_vector(
        tower,
        tier=tier,
        t1_core_id=tier_contracts["1"]["core_id"],
        n=record["n"],
        seed=protocol["seed"],
    )
    reconstructed_public = runner_module.public_vector(
        reconstructed_questions,
        tier=tier,
        core_id=reconstructed_core,
        seed=protocol["seed"],
    )
    reconstructed_scoring = runner_module.scoring_vector(
        reconstructed_questions,
        tier=tier,
        core_id=reconstructed_core,
        seed=protocol["seed"],
    )
    if vector != reconstructed_public or scoring_vector != reconstructed_scoring:
        fail("sealed question/scoring vectors cannot be reconstructed from ratified sources")
    try:
        runner_module.validate_source_vector_scorer_config(
            reconstructed_questions, tier=tier
        )
    except Exception as exc:
        fail(f"reconstructed source vector scorer config is invalid: {exc}")

    observations = summary["observations"]
    response_artifacts = summary["response_artifacts"]
    if not isinstance(observations, list) or len(observations) != 3:
        fail("source summary requires exactly three independent observations")
    if not isinstance(response_artifacts, list) or len(response_artifacts) != 3:
        fail("source summary requires three sealed response artifacts")
    raw_q = []
    raw_suite_quality = []
    artifact_paths = set()
    for repetition, (observation, response) in enumerate(
        zip(observations, response_artifacts), 1
    ):
        required_obs = {"path", "sha256", "q", "ts", "core_id", "protocol_id", "n", "era"}
        if not isinstance(observation, dict) or set(observation) != required_obs:
            fail("raw observation reference is malformed")
        raw_path = sealed_artifact(observation["path"], observation["sha256"], "raw observation")
        if raw_path in artifact_paths:
            fail("repetitions do not use independent artifact paths")
        artifact_paths.add(raw_path)
        raw = load(raw_path, "raw observation")
        if (
            not isinstance(raw, dict)
            or set(raw)
            != {
                "q",
                "ts",
                "core_id",
                "protocol_id",
                "n",
                "era",
                "per_suite_quality",
                "per_suite_counts",
            }
        ):
            fail("raw observation has unexpected fields")
        if any(
            raw[key] != observation[key]
            for key in ("q", "ts", "core_id", "protocol_id", "n", "era")
        ):
            fail("raw observation differs from source summary")
        iso_after(observation["ts"], "observation timestamp")
        finite(observation["q"], "observation quality")

        if not isinstance(response, dict) or set(response) != {
            "path",
            "sha256",
            "sidecar_path",
            "sidecar_sha256",
            "judge_trace_path",
            "judge_trace_sha256",
        }:
            fail("response artifact reference is malformed")
        response_path = sealed_artifact(response["path"], response["sha256"], "response ledger")
        sidecar_path = sealed_artifact(
            response["sidecar_path"], response["sidecar_sha256"], "EvalTower sidecar"
        )
        judge_trace_path = sealed_artifact(
            response["judge_trace_path"],
            response["judge_trace_sha256"],
            "LLM judge trace",
        )
        if (
            response_path in artifact_paths
            or sidecar_path in artifact_paths
            or judge_trace_path in artifact_paths
        ):
            fail("repetitions do not use independent artifact paths")
        artifact_paths.update((response_path, sidecar_path, judge_trace_path))
        try:
            rows = [json.loads(line) for line in response_path.read_text().splitlines() if line]
        except json.JSONDecodeError as exc:
            fail(f"response ledger is malformed: {exc}")
        if len(rows) != record["n"]:
            fail("response ledger count differs from the ratified vector")
        try:
            trace_rows = [
                json.loads(line)
                for line in judge_trace_path.read_text().splitlines()
                if line
            ]
        except json.JSONDecodeError as exc:
            fail(f"LLM judge trace is malformed: {exc}")
        judge_rows = [
            (ordinal, question)
            for ordinal, question in enumerate(questions)
            if question["scoring_method"] == "llm_judge"
        ]
        if len(trace_rows) != len(judge_rows):
            fail("LLM judge trace count does not match fixed-vector judge rows")
        traces_by_identity = {}
        for trace in trace_rows:
            fixed = trace.get("fixed_vector_row") if isinstance(trace, dict) else None
            if (
                not isinstance(trace, dict)
                or not isinstance(trace.get("correlation_sha256"), str)
                or not isinstance(fixed, dict)
                or set(fixed) != {"tier", "repetition", "ordinal", "qid"}
                or not isinstance(fixed["tier"], int)
                or not isinstance(fixed["repetition"], int)
                or not isinstance(fixed["ordinal"], int)
                or not isinstance(fixed["qid"], str)
            ):
                fail("LLM judge trace row has no fixed-vector identity")
            identity = (fixed["tier"], fixed["repetition"], fixed["ordinal"], fixed["qid"])
            if identity in traces_by_identity:
                fail("LLM judge trace fixed-vector identity is not unique")
            traces_by_identity[identity] = trace
        for ordinal, question in judge_rows:
            identity = (tier, repetition, ordinal, question["qid"])
            if identity not in traces_by_identity:
                fail("LLM judge trace does not cover every fixed-vector judge row")
        for ordinal, (row, question, scoring_question) in enumerate(zip(
            rows, questions, scoring_questions
        )):
            if not isinstance(row, dict) or set(row) != RESPONSE_KEYS:
                fail("response ledger row structure differs")
            if any(
                row[name] != question[name]
                for name in ("qid", "suite", "scoring_method", "scoring_config_sha256")
            ):
                fail("response ledger order or scoring identity differs from the ratified vector")
            if (
                not isinstance(row["answer"], str)
                or not isinstance(row["correct"], bool)
                or row["error"] is not None
                or row["partial"] is not False
                or row["degraded"] is not False
                or row["route_used"] != "frontdoor"
            ):
                fail("response ledger contains a non-clean result")
            trace = None
            if row["scoring_method"] == "llm_judge":
                trace = traces_by_identity.pop((tier, repetition, ordinal, question["qid"]))
            try:
                replayed = runner_module.independently_score_response(
                    row["answer"],
                    scoring_question["expected"],
                    row["scoring_method"],
                    scoring_question["scoring_config"],
                    judge_trace=trace,
                    default_api_url=protocol["judge_defaults"][
                        "orchestrator_api_url"
                    ],
                    default_role=protocol["judge_defaults"]["role"],
                )
            except Exception as exc:
                fail(f"independent scoring failed for {row['qid']}: {exc}")
            if replayed is not row["correct"]:
                fail("response correctness differs from independent scoring")
        if traces_by_identity:
            fail("LLM judge trace contains rows with no response")

        try:
            sidecar_rows = [
                json.loads(line) for line in sidecar_path.read_text().splitlines() if line
            ]
        except json.JSONDecodeError as exc:
            fail(f"EvalTower sidecar is malformed: {exc}")
        question_sidecars = [
            row for row in sidecar_rows if row.get("row_type") == "question_result"
        ]
        if (
            len(sidecar_rows) != record["n"] + 2
            or sidecar_rows[0].get("row_type") != "batch_start"
            or sidecar_rows[0].get("requested_n") != record["n"]
            or sidecar_rows[0].get("concurrency") != 3
            or sidecar_rows[0].get("complete") is not False
            or sidecar_rows[-1].get("row_type") != "batch_complete"
            or sidecar_rows[-1].get("completed_n") != record["n"]
            or sidecar_rows[-1].get("complete") is not True
            or len(question_sidecars) != record["n"]
        ):
            fail("EvalTower sidecar completion contract differs")
        try:
            question_sidecars.sort(key=lambda row: row["ordinal"])
        except (KeyError, TypeError):
            fail("EvalTower sidecar ordinals are malformed")
        if [row.get("ordinal") for row in question_sidecars] != list(range(record["n"])):
            fail("EvalTower sidecar ordinals do not cover the response vector")
        for ledger_row, sidecar_row in zip(rows, question_sidecars):
            result_row = sidecar_row.get("result")
            if (
                not isinstance(result_row, dict)
                or sidecar_row.get("answer") != ledger_row["answer"]
                or result_row.get("qid") != ledger_row["qid"]
                or result_row.get("suite") != ledger_row["suite"]
                or result_row.get("correct") is not ledger_row["correct"]
                or result_row.get("route") != ledger_row["route_used"]
                or result_row.get("scoring_method", "exact_match")
                != ledger_row["scoring_method"]
            ):
                fail("EvalTower sidecar differs from the response ledger")

        expected_q = 3.0 * sum(row["correct"] for row in rows) / len(rows)
        suite_rows = {
            suite: [row for row in rows if row["suite"] == suite] for suite in vector_counts
        }
        expected_suite_quality = {
            suite: 3.0 * sum(row["correct"] for row in values) / len(values)
            for suite, values in suite_rows.items()
        }
        if not same_float(raw["q"], expected_q):
            fail("raw observation quality is not reproducible from response correctness")
        if raw["per_suite_counts"] != vector_counts:
            fail("raw observation per-suite counts differ from the vector")
        if (
            not isinstance(raw["per_suite_quality"], dict)
            or set(raw["per_suite_quality"]) != set(expected_suite_quality)
            or any(
                not same_float(raw["per_suite_quality"][suite], value)
                for suite, value in expected_suite_quality.items()
            )
        ):
            fail("raw per-suite quality is not reproducible from response correctness")
        raw_q.append(float(raw["q"]))
        raw_suite_quality.append(raw["per_suite_quality"])

    expected_quality = statistics.median(raw_q)
    expected_summary_suite = {
        suite: statistics.median([row[suite] for row in raw_suite_quality])
        for suite in vector_counts
    }
    if not same_float(summary["quality"], expected_quality) or not same_float(record["quality"], expected_quality):
        fail("quality is not the recomputed raw-observation median")
    if record["timestamp"] != observations[-1]["ts"]:
        fail("source timestamp is not the final repetition timestamp")
    if summary["per_suite_counts"] != vector_counts:
        fail("summary per-suite counts differ from the ratified vector")
    if (
        not isinstance(summary["per_suite_quality"], dict)
        or set(summary["per_suite_quality"]) != set(expected_summary_suite)
        or any(
            not same_float(summary["per_suite_quality"][suite], value)
            for suite, value in expected_summary_suite.items()
        )
    ):
        fail("summary per-suite quality is not the recomputed median")
    observed_by_tier[str(tier)] = observations
    summary_by_tier[str(tier)] = summary

if seen != {1, 2}:
    fail("source records do not cover both tiers")
replacement = manifest["replacement"]
baseline = replacement.get("baseline_state") if isinstance(replacement, dict) else None
if not isinstance(baseline, dict) or baseline.get("eval_quality_era") != "E8":
    fail("replacement baseline is not E8-stamped")
if set(baseline.get("baselines_by_tier") or {}) != {"1", "2"}:
    fail("replacement baseline does not cover both tiers")
if set(replacement) != {
    "baseline_state",
    "quality_history_by_tier",
    "quality_history_provenance_by_tier",
}:
    fail("replacement contains unexpected fields")
for tier in ("1", "2"):
    summary = summary_by_tier[tier]
    observations = observed_by_tier[tier]
    history = replacement["quality_history_by_tier"].get(tier)
    provenance = replacement["quality_history_provenance_by_tier"].get(tier)
    if (
        not same_float(baseline["baselines_by_tier"].get(tier), summary["quality"])
        or history != [row["q"] for row in observations]
    ):
        fail("replacement baseline/history is not derived from raw observations")
    if (
        baseline.get("per_suite_quality_by_tier", {}).get(tier) != summary["per_suite_quality"]
        or baseline.get("per_suite_counts_by_tier", {}).get(tier) != summary["per_suite_counts"]
    ):
        fail("replacement per-suite baseline differs from source summary")
    expected_provenance = [
        {key: row[key] for key in ("q", "ts", "era", "core_id")} for row in observations
    ]
    if provenance != expected_provenance:
        fail("replacement provenance is not derived from raw observations")
PY
}

validate_preflight() {
    [[ -x "$PYTHON" && -f "$STATE" && -f "$JOURNAL" ]] || fail 'AutoPilot state or journal prerequisite is missing'
    jq -e '.active_instrument_eras.eval_quality == "E8" and .baseline_state.eval_quality_era != "E8" and .e8_quality_rebaseline.status == "hold_open"' "$STATE" >/dev/null || fail 'E8 quality hold is not open against a pre-E8 baseline'
    local completed required
    completed="$(numeric_trial_count)"; required="$(jq -er '.frontier_rerun_required.min_numeric_trials' "$STATE")"
    (( completed >= required && required >= 16 )) || fail "E8 numeric rerun is incomplete ($completed/$required); no quality baseline may be applied"
    validate_evidence "$EVIDENCE"
}

plan() {
    cat <<'EOF'
E8 quality-baseline reseed preparation
- require a canonical human-ratified protocol receipt bound to the exact runner
- require 16 or more E8 numeric trials before and after collection
- reject source vectors whose fixed scorer configurations cannot be replayed
- recompute all quality values from sealed response correctness and ratified vectors
- require one sealed, row-identified LLM judge outcome for every fixed judge row
- bind the frozen production llama.cpp branch and exact source head
- accept only an in-bundle, completion-sealed atomic publication
- use a separate human-reviewed atomic apply transaction after evidence review
EOF
}

case "${1:-}" in
    --plan) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--validate-evidence PATH'; plan ;;
    --validate-only) [[ $# -eq 1 ]] || fail 'usage: --plan|--validate-only|--validate-evidence PATH'; validate_preflight; printf 'E8 quality baseline reseed preflight passed; no files changed.\n' ;;
    --validate-evidence) [[ $# -eq 2 ]] || fail 'usage: --plan|--validate-only|--validate-evidence PATH'; validate_evidence "$2"; printf 'E8 quality evidence contract passed; no files changed.\n' ;;
    *) fail 'usage: --plan|--validate-only|--validate-evidence PATH' ;;
esac
