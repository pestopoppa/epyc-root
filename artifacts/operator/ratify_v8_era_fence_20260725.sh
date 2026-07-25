#!/bin/bash
# Human-only ratification of the v8 measurement-era eligibility fence.
# This does not freeze production. A separate reviewed freeze transaction follows.
set -euo pipefail

ROOT=/mnt/raid0/llm/epyc-root
ORCH=/mnt/raid0/llm/epyc-orchestrator
PROD=/mnt/raid0/llm/llama.cpp
RESEARCH=/mnt/raid0/llm/epyc-inference-research

ERAS_REL=orchestration/instrument_eras.yaml
STATE_REL=orchestration/autopilot_state.json
CARD_REL=scripts/autopilot/system_card.md
ERAS="$ORCH/$ERAS_REL"
STATE="$ORCH/$STATE_REL"
CARD="$ORCH/$CARD_REL"

PROMOTION_AT="2026-07-25T18:38:43Z"
PROMOTION_EPOCH="1785004723.0"
EXPECTED_HEAD="67a433bf45a8a091d83b4ea0b32ff0735fd51800"
EXPECTED_CPU_SHA="a4b667163022aa166ade7c0e00fa4e775b37662e02c10da7642c8c23a4d6b414"
EXPECTED_HIP_SHA="112c560f1c978c584a9899539851348a0ce1e05cde458061c281758aff066882"
ROOT_EVIDENCE_COMMIT="97e6dd8687204cdce7af95351f77e1477bcd486e"
ORCH_FIXTURE_COMMIT="bf300a2688d924e23bd946e0ece1978f3c87f586"
CPU_EVIDENCE_COMMIT="367ed4ca05c52c83f735414ff389cc7d4994873d"
PGPU_EVIDENCE_COMMIT="991942334f4e1dca8c905e7ce4ca5a642d8d470d"

CUTOVER_REL=artifacts/operator/v8-cutover-20260725T183843Z-67a433bf4/journal.json
QUARTER_REL=artifacts/operator/v8-quarter-smoke-20260725T190117Z/summary.json
QUARTER_ROWS_REL=artifacts/operator/v8-quarter-smoke-20260725T190117Z/quarter_smoke_rerun2.jsonl
QUARTER_GATE_REL=artifacts/operator/v8-quarter-smoke-20260725T190117Z/quarter_promotion_gate.log
WAIVE_REL=artifacts/operator/waive_q8_cpu_prefill_v8_20260725.json
PROMOTION_ATTESTATION_REL=handoffs/active/laguna-pgpu1-v8-promotion-attestation.json
CPU_REL=data/kernel-v8-candidate/cpu-prefill-regression/run-20260725T155655Z-v4-waive-q8-kfd-procrace-swapoff/summary.json
PGPU_REL=data/gpu-mi210/laguna-iq2-dflash-pgpu1-v8-rerun1/run-20260725T184624Z/summary.json
PGPU_AUDIT_REL=data/gpu-mi210/laguna-iq2-dflash-pgpu1-v8-rerun1/run-20260725T184624Z/retrocert_completeness_audit.json
PGPU_PROVENANCE_REL=data/gpu-mi210/laguna-iq2-dflash-pgpu1-v8-rerun1/run-20260725T184624Z/retrocert_audit_provenance.json

CUTOVER="$ROOT/$CUTOVER_REL"
QUARTER="$ROOT/$QUARTER_REL"
QUARTER_ROWS="$ROOT/$QUARTER_ROWS_REL"
QUARTER_GATE="$ROOT/$QUARTER_GATE_REL"
WAIVE="$ROOT/$WAIVE_REL"
PROMOTION_ATTESTATION="$ROOT/$PROMOTION_ATTESTATION_REL"
CPU_SUMMARY="$RESEARCH/$CPU_REL"
PGPU_SUMMARY="$RESEARCH/$PGPU_REL"
PGPU_AUDIT="$RESEARCH/$PGPU_AUDIT_REL"
PGPU_PROVENANCE="$RESEARCH/$PGPU_PROVENANCE_REL"

CUTOVER_SHA="e2c3b9f67072798eafcb945004c2faed59a04e048ce7e1510a98611d82330991"
QUARTER_SHA="e25feaadba51d8d75736b31932ea088f8f2a0a7fafbd29d63f80c66a799c54f4"
QUARTER_ROWS_SHA="808207961490e5d2df9a24e79e3d53ee617ccfec3e69a2229e2656f2b54fa639"
QUARTER_GATE_SHA="9d37c9fc6b90889a2b68cbf99bd7d6417508eb9c0ed93b25147f8c36f526de4b"
WAIVE_SHA="fcd52b61610fcc2782e11f41ffac359343233924805f83d872eeceffbb7522d7"
PROMOTION_ATTESTATION_SHA="54daa05c3c0540a65fda3cb008fd1ec6e89a9c2a169ced0b2af81bf12783bc5d"
CPU_SUMMARY_SHA="fb0b8db8bcf1f8aea34cbf1ca7231df36b223ebd7556df61f98d8a471176943a"
PGPU_SUMMARY_SHA="73c28e4b86a38732c7fa99f3210e31f53efcced6420b8e81607007690621059e"
PGPU_AUDIT_SHA="c9410dc7124232c8652f5ccec17e3bea3e9d5c6a0a77d537a0b70ea8689c74e9"
PGPU_PROVENANCE_SHA="c8d06d81f9dddb5df130f48bff1d0a3918576ba0f8ec9a0137041322598555ca"

OUTPUT="$ROOT/artifacts/operator/ratify_v8_era_fence_20260725.json"
TXN_DIR="$ROOT/artifacts/operator/v8-era-fence-transaction-20260725T183843Z"
PREP_DIR="$TXN_DIR.preparing"
JOURNAL="$TXN_DIR/journal.json"
PRE_ERAS="$TXN_DIR/instrument_eras.yaml.before"
PRE_STATE="$TXN_DIR/autopilot_state.json.before"
PRE_CARD="$TXN_DIR/system_card.md.before"
INTERRUPTED_OUTPUT="$TXN_DIR/attestation.interrupted.json"
OPERATOR_LOCK="$ROOT/artifacts/operator/.v8-era-fence.lock"
AUTOPILOT_LOCK="$ORCH/orchestration/.autopilot.lock"
STATE_LOCK="$STATE.lock"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

phase="preflight"
transaction_active=0
output_sha=""
pre_eras_sha=""
pre_state_sha=""
pre_card_sha=""
preprompt_state_sha=""

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

sha256() {
    sha256sum -- "$1" | awk '{print $1}'
}

require_sha() {
    local path=$1 expected=$2 label=$3
    [[ -f "$path" ]] || fail "$label is missing: $path"
    [[ "$(sha256 "$path")" == "$expected" ]] ||
        fail "$label SHA256 does not match the reviewed evidence"
}

require_tracked_clean() {
    local repo=$1 rel=$2 expected_sha=${3:-}
    git -C "$repo" ls-files --error-unmatch -- "$rel" >/dev/null ||
        fail "$repo/$rel is not tracked"
    git -C "$repo" diff --quiet -- "$rel" ||
        fail "$repo/$rel has unstaged changes"
    git -C "$repo" diff --cached --quiet -- "$rel" ||
        fail "$repo/$rel has staged changes"
    if [[ -n "$expected_sha" ]]; then
        require_sha "$repo/$rel" "$expected_sha" "$repo/$rel"
    fi
}

require_commit_ancestor() {
    local repo=$1 commit=$2 label=$3
    git -C "$repo" cat-file -e "$commit^{commit}" ||
        fail "$label commit is unavailable: $commit"
    git -C "$repo" merge-base --is-ancestor "$commit" HEAD ||
        fail "$label commit is not an ancestor of $repo HEAD"
}

require_blob_at_commit() {
    local repo=$1 commit=$2 rel=$3 expected_sha=$4 label=$5 actual_sha
    actual_sha="$(
        git -C "$repo" show "$commit:$rel" |
            sha256sum |
            awk '{print $1}'
    )" || fail "$label is absent from its immutable evidence commit"
    [[ "$actual_sha" == "$expected_sha" ]] ||
        fail "$label hash does not match its immutable evidence commit"
}

require_orchestrator_clean() {
    require_commit_ancestor "$ORCH" "$ORCH_FIXTURE_COMMIT" "E8 validation fixture"
    git -C "$ORCH" diff --quiet ||
        fail "epyc-orchestrator has tracked unstaged changes"
    git -C "$ORCH" diff --cached --quiet ||
        fail "epyc-orchestrator has tracked staged changes"
    require_tracked_clean "$ORCH" "$ERAS_REL"
    require_tracked_clean "$ORCH" "$CARD_REL"
    [[ -f "$STATE" && ! -L "$STATE" ]] ||
        fail "live AutoPilot state is missing, not regular, or a symlink"
    if git -C "$ORCH" ls-files --error-unmatch -- "$STATE_REL" >/dev/null 2>&1; then
        require_tracked_clean "$ORCH" "$STATE_REL"
    else
        git -C "$ORCH" check-ignore -q -- "$STATE_REL" ||
            fail "untracked AutoPilot state is not intentionally ignored"
    fi
}

require_only_expected_orchestrator_changes() {
    local changed expected
    git -C "$ORCH" diff --cached --quiet ||
        fail "epyc-orchestrator index changed during the ratification"
    changed="$(git -C "$ORCH" diff --name-only | LC_ALL=C sort)"
    if git -C "$ORCH" ls-files --error-unmatch -- "$STATE_REL" >/dev/null 2>&1; then
        expected="$(printf '%s\n%s\n%s\n' "$ERAS_REL" "$STATE_REL" "$CARD_REL" | LC_ALL=C sort)"
    else
        expected="$(printf '%s\n%s\n' "$ERAS_REL" "$CARD_REL" | LC_ALL=C sort)"
    fi
    [[ "$changed" == "$expected" ]] ||
        fail "unexpected tracked files changed during the ratification"
}

require_same_preprompt_state() {
    [[ "$preprompt_state_sha" =~ ^[0-9a-f]{64}$ ]] ||
        fail "pre-prompt AutoPilot state digest was not captured"
    [[ "$(sha256 "$STATE")" == "$preprompt_state_sha" ]] ||
        fail "live AutoPilot state changed while awaiting operator confirmation"
}

autopilot_is_running() {
    pgrep -f '[s]cripts/autopilot/autopilot.py' >/dev/null
}

acquire_locks() {
    exec 7>>"$OPERATOR_LOCK"
    flock -n 7 || fail "another v8 era-fence transaction holds $OPERATOR_LOCK"

    # This is the singleton lock acquired for the full AutoPilot process lifetime.
    exec 8>>"$AUTOPILOT_LOCK"
    flock -n 8 || fail "AutoPilot lifetime lock is held"

    # This is the shared lock used by every cooperating autopilot_state.json writer.
    exec 9>>"$STATE_LOCK"
    flock -w 10 9 || fail "could not acquire the live AutoPilot state lock"

    autopilot_is_running &&
        fail "AutoPilot process exists despite the singleton lock; inspect before proceeding"
}

validate_production() {
    [[ "$(git -C "$PROD" branch --show-current)" == "production-consolidated-v8" ]] ||
        fail "production branch is not production-consolidated-v8"
    [[ "$(git -C "$PROD" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] ||
        fail "production HEAD does not match the validated v8 tip"
    git -C "$PROD" diff --quiet ||
        fail "production source has tracked unstaged changes"
    git -C "$PROD" diff --cached --quiet ||
        fail "production source has tracked staged changes"
    require_sha "$PROD/build/bin/llama-server" "$EXPECTED_CPU_SHA" "production CPU llama-server"
    require_sha "$PROD/build-hip/bin/llama-server" "$EXPECTED_HIP_SHA" "production HIP llama-server"
    bash "$ROOT/scripts/session/verify_llama_cpp.sh" >/dev/null
}

validate_evidence() {
    require_commit_ancestor "$ROOT" "$ROOT_EVIDENCE_COMMIT" "root v8 evidence"
    require_commit_ancestor "$RESEARCH" "$CPU_EVIDENCE_COMMIT" "CPU evidence"
    require_commit_ancestor "$RESEARCH" "$PGPU_EVIDENCE_COMMIT" "P-GPU evidence"

    require_blob_at_commit "$ROOT" "$ROOT_EVIDENCE_COMMIT" "$CUTOVER_REL" "$CUTOVER_SHA" "cutover journal"
    require_blob_at_commit "$ROOT" "$ROOT_EVIDENCE_COMMIT" "$QUARTER_REL" "$QUARTER_SHA" "quarter summary"
    require_blob_at_commit "$ROOT" "$ROOT_EVIDENCE_COMMIT" "$QUARTER_ROWS_REL" "$QUARTER_ROWS_SHA" "quarter rows"
    require_blob_at_commit "$ROOT" "$ROOT_EVIDENCE_COMMIT" "$QUARTER_GATE_REL" "$QUARTER_GATE_SHA" "quarter gate"
    require_blob_at_commit "$ROOT" "$ROOT_EVIDENCE_COMMIT" "$WAIVE_REL" "$WAIVE_SHA" "WAIVE-Q8"
    require_blob_at_commit "$ROOT" "$ROOT_EVIDENCE_COMMIT" "$PROMOTION_ATTESTATION_REL" "$PROMOTION_ATTESTATION_SHA" "promotion attestation"
    require_blob_at_commit "$RESEARCH" "$CPU_EVIDENCE_COMMIT" "$CPU_REL" "$CPU_SUMMARY_SHA" "CPU matrix"
    require_blob_at_commit "$RESEARCH" "$PGPU_EVIDENCE_COMMIT" "$PGPU_REL" "$PGPU_SUMMARY_SHA" "P-GPU summary"
    require_blob_at_commit "$RESEARCH" "$PGPU_EVIDENCE_COMMIT" "$PGPU_AUDIT_REL" "$PGPU_AUDIT_SHA" "P-GPU audit"
    require_blob_at_commit "$RESEARCH" "$PGPU_EVIDENCE_COMMIT" "$PGPU_PROVENANCE_REL" "$PGPU_PROVENANCE_SHA" "P-GPU audit provenance"

    require_tracked_clean "$ROOT" "$CUTOVER_REL" "$CUTOVER_SHA"
    require_tracked_clean "$ROOT" "$QUARTER_REL" "$QUARTER_SHA"
    require_tracked_clean "$ROOT" "$QUARTER_ROWS_REL" "$QUARTER_ROWS_SHA"
    require_tracked_clean "$ROOT" "$QUARTER_GATE_REL" "$QUARTER_GATE_SHA"
    require_tracked_clean "$ROOT" "$WAIVE_REL" "$WAIVE_SHA"
    require_tracked_clean "$ROOT" "$PROMOTION_ATTESTATION_REL" "$PROMOTION_ATTESTATION_SHA"
    require_tracked_clean "$RESEARCH" "$CPU_REL" "$CPU_SUMMARY_SHA"
    require_tracked_clean "$RESEARCH" "$PGPU_REL" "$PGPU_SUMMARY_SHA"
    require_tracked_clean "$RESEARCH" "$PGPU_AUDIT_REL" "$PGPU_AUDIT_SHA"
    require_tracked_clean "$RESEARCH" "$PGPU_PROVENANCE_REL" "$PGPU_PROVENANCE_SHA"

    jq -e --arg head "$EXPECTED_HEAD" --arg at "$PROMOTION_AT" '
        .schema == "epyc.kernel_cutover_journal.v1" and
        .cutover_id == "20260725T183843Z-67a433bf4" and
        .promoted_at == $at and .phase == "complete" and
        .production_branch == "production-consolidated-v8" and
        .production_head == $head and
        .rollback_branch == "production-consolidated-v7" and
        .rollback_head == "6ad45fa3ff6718c07c000061dbc6e29c1771f6e3" and
        .cpu_backed_up == 1 and .hip_backed_up == 1 and
        .cpu_installed == 1 and .hip_installed == 1 and
        .root_governance_committed == 1 and .completed == 1
    ' "$CUTOVER" >/dev/null || fail "cutover journal predicate failed"

    jq -e --arg head "$EXPECTED_HEAD" '
        .schema == "epyc.v8_quarter_stack_smoke.v1" and .status == "pass" and
        .production_kernel.branch == "production-consolidated-v8" and
        .production_kernel.head == $head and
        .production_kernel.version == "10107 (67a433bf4)" and
        .orchestrator.commit == "698c366fa2a9b93af2eebe4ed98c4522f841b795" and
        .scope.numa_mode == "quarter" and
        .scope.qwen3_5_122b_loaded == false and
        .scope.qwen3_5_122b_tested == false and
        .scope.chat_endpoints == 14 and .scope.embedding_endpoints == 6 and
        .scope.total_endpoints == 20 and
        .final_attempt.artifact == "quarter_smoke_rerun2.jsonl" and
        .final_attempt.sha256 == "808207961490e5d2df9a24e79e3d53ee617ccfec3e69a2229e2656f2b54fa639" and
        .final_attempt.rows == 20 and .final_attempt.passed == 20 and
        .final_attempt.failed == 0 and .final_attempt.chat_passed == 14 and
        .final_attempt.embedding_passed == 6 and
        .promotion_guard.sha256 == "9d37c9fc6b90889a2b68cbf99bd7d6417508eb9c0ed93b25147f8c36f526de4b" and
        .promotion_guard.kernel_regression == false and
        .gpu_posture.post_smoke_kfd_processes == 0 and
        .gpu_posture.post_smoke_vram_percent == 0
    ' "$QUARTER" >/dev/null || fail "quarter-stack smoke predicate failed"

    jq -e --arg head "$EXPECTED_HEAD" '
        .schema == "epyc.cpu_prefill_v8.operator_waiver.v1" and
        .decision == "WAIVE-Q8" and .protocol == "P-BENCH-PREFILL-1" and
        .protocol_changed == false and .candidate_head == $head and
        .production_head == "6ad45fa3ff6718c07c000061dbc6e29c1771f6e3" and
        .scope.excluded_model == "qwen36_q8" and
        .scope.excluded_arm_runs == 4 and
        .scope.remaining_matched_pairs == 14 and
        .scope.remaining_arm_runs == 28 and
        any(.consequences[]; . == "No v8 Q8 non-regression claim may be made from this campaign.")
    ' "$WAIVE" >/dev/null || fail "WAIVE-Q8 predicate failed"

    jq -e --arg head "$EXPECTED_HEAD" --arg hip "$EXPECTED_HIP_SHA" --arg at "$PROMOTION_AT" '
        .schema == "epyc.kernel_promotion_attestation.v1" and
        .status == "production_promoted_pending_gpu_certification" and
        .production_branch == "production-consolidated-v8" and
        .production_head == $head and .frozen == false and .promoted_at == $at and
        .server_binary.path == "/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server" and
        .server_binary.sha256 == $hip and
        .rollback.branch == "production-consolidated-v7" and
        .rollback.head == "6ad45fa3ff6718c07c000061dbc6e29c1771f6e3" and
        .rollback.backup_ref == "refs/heads/production-consolidated-v7" and
        .rollback.source_ref == "refs/heads/production-consolidated-v8"
    ' "$PROMOTION_ATTESTATION" >/dev/null ||
        fail "provisional promotion attestation predicate failed"

    jq -e --arg waive "$WAIVE_SHA" '
        .schema == "cpu-prefill-v8-regression.v3" and
        .protocol == "P-BENCH-PREFILL-1" and
        .throughput_status == "pass" and .throughput_failures == [] and
        .input_binding_status == "identical" and
        (.pair_results | length) == 14 and
        (.plan.arm_runs | length) == 28 and
        ([.plan.arm_runs[].model] | index("qwen36_q8")) == null and
        .plan.q8_waiver.source.sha256 == $waive and
        .plan.q8_waiver.semantic_binding.decision == "WAIVE-Q8" and
        (.plan.explicit_exclusion | index("qwen3.5-122b")) != null and
        any(.plan.explicit_exclusion[]; startswith("qwen36_q8")) and
        (.iq_utility | length) == 3 and
        all(.iq_utility[]; .iqk == 1 and .state == "pass") and
        ([.iq_utility[].model] | sort) == ["glm_iq2", "hy3_iq1", "qwen_next_iq2"]
    ' "$CPU_SUMMARY" >/dev/null || fail "final WAIVE-Q8 CPU matrix predicate failed"

    jq -e '
        .schema == "epyc.pgpu1_artifact_completeness_audit.v1" and
        .status == "complete" and
        .recommendation == "retro_cert_candidates_present" and
        (.artifacts | length) == 1 and
        .artifacts[0].status == "complete" and
        .artifacts[0].recommendation == "retro_cert_candidate" and
        .artifacts[0].summary_status == "ok" and
        .artifacts[0].missing_required_fields == [] and
        .artifacts[0].near_miss_fields == []
    ' "$PGPU_AUDIT" >/dev/null || fail "P-GPU completeness audit predicate failed"

    jq -e '
        .schema == "epyc.pgpu1_retrocert_audit_provenance.v1" and
        .protocol == "P-GPU-1" and
        .source_summary.path == "summary.json" and
        .source_summary.sha256 == "73c28e4b86a38732c7fa99f3210e31f53efcced6420b8e81607007690621059e" and
        .source_summary.status == "ok" and
        .corrected_audit.path == "retrocert_completeness_audit.json" and
        .corrected_audit.sha256 == "c9410dc7124232c8652f5ccec17e3bea3e9d5c6a0a77d537a0b70ea8689c74e9" and
        .corrected_audit.status == "complete" and
        .corrected_audit.missing_required_fields == [] and
        .decision.retro_certification_eligible == true
    ' "$PGPU_PROVENANCE" >/dev/null || fail "P-GPU audit provenance predicate failed"

    jq -e --arg hip "$EXPECTED_HIP_SHA" '
        .schema == "epyc.laguna_iq2_dflash_pgpu1.summary.v2" and
        .status == "ok" and .production_named_kernel == true and
        .final_guard_valid == true and .final_clean == true and
        .execution_binding_valid == true and
        .per_replicate_bindings_valid == true and
        .matrix_cardinality_valid == true and
        .attestation_ref == "/mnt/raid0/llm/epyc-root/handoffs/active/laguna-pgpu1-v8-promotion-attestation.json" and
        .post_execution_identity.binding.server.sha256 == $hip and
        (.results | length) == 10 and
        all(.results[]; .status == "ok") and
        ([.results[] | select(.arm == "base")] | length) == 5 and
        ([.results[] | select(.arm == "dflash")] | length) == 5 and
        ([.results[] | select(.arm == "base") | .rep] | sort) == [1,2,3,4,5] and
        ([.results[] | select(.arm == "dflash") | .rep] | sort) == [1,2,3,4,5]
    ' "$PGPU_SUMMARY" >/dev/null || fail "P-GPU production matrix predicate failed"
}

validate_pre_fence_state() {
    "$ORCH/.venv/bin/python" - "$ERAS" "$STATE" "$PROMOTION_AT" "$PROMOTION_EPOCH" <<'PY'
from datetime import datetime
import json
from pathlib import Path
import sys
import yaml

eras_path = Path(sys.argv[1])
state_path = Path(sys.argv[2])
boundary = sys.argv[3]
epoch = float(sys.argv[4])
parsed_epoch = datetime.fromisoformat(boundary.replace("Z", "+00:00")).timestamp()
if parsed_epoch != epoch:
    raise SystemExit("promotion timestamp and epoch are not identical")

registry = yaml.safe_load(eras_path.read_text(encoding="utf-8"))
rows = registry.get("eras")
if not isinstance(rows, list):
    raise SystemExit("instrument registry eras is not a list")
ids = [row.get("id") for row in rows if isinstance(row, dict)]
if "E8-cpu-kernel" in ids or "E8-autopilot-speed" in ids:
    raise SystemExit("E8 era already exists")
if ids.count("E6-cpu-kernel") != 1 or ids.count("E6-autopilot-speed") != 1:
    raise SystemExit("expected E6 predecessor rows are not unique")

state = json.loads(state_path.read_text(encoding="utf-8"))
expected_eras = {
    "autopilot_speed": "E6-autopilot-speed",
    "cpu_bench": "E6-cpu-kernel",
}
if state.get("active_instrument_eras") != expected_eras:
    raise SystemExit("live active instrument eras are not the exact E6 predecessor")
if state.get("pareto_epoch_ts") != 1784554213.0:
    raise SystemExit("unexpected pre-E8 pareto_epoch_ts")
if state.get("pareto_exclude_before_ts") != 1784554213.0:
    raise SystemExit("unexpected pre-E8 pareto_exclude_before_ts")
marker = state.get("frontier_rerun_required")
if not isinstance(marker, dict) or marker.get("required") is not True:
    raise SystemExit("pre-E8 frontier marker is missing or not fail-closed")
PY
}

atomic_restore() {
    local source=$1 target=$2 tmp
    tmp="$(mktemp "$(dirname "$target")/.$(basename "$target").restore.XXXXXX")"
    install -m 0644 "$source" "$tmp"
    sync -f "$tmp"
    mv -f "$tmp" "$target"
    sync -f "$target"
    sync -f "$(dirname "$target")"
}

write_journal_to() {
    local target_dir=$1
    local journal_tmp="$target_dir/.journal.json.tmp"
    python3 - \
        "$journal_tmp" "$phase" "$PROMOTION_AT" \
        "$pre_eras_sha" "$pre_state_sha" "$pre_card_sha" "$output_sha" <<'PY'
import json
import os
from pathlib import Path
import sys

path = Path(sys.argv[1])
payload = {
    "schema": "epyc.v8_era_fence_transaction.v1",
    "scope": "eligibility_fence_only",
    "production_frozen": False,
    "phase": sys.argv[2],
    "cutover_boundary": sys.argv[3],
    "preimages": {
        "instrument_eras_sha256": sys.argv[4],
        "autopilot_state_sha256": sys.argv[5],
        "system_card_sha256": sys.argv[6],
    },
    "output_sha256": sys.argv[7] or None,
}
with path.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())
os.replace(path, path.parent / "journal.json")
dir_fd = os.open(path.parent, os.O_RDONLY)
try:
    os.fsync(dir_fd)
finally:
    os.close(dir_fd)
PY
}

write_journal() {
    write_journal_to "$TXN_DIR"
}

restore_preimages() {
    local restore_ok=1
    set +e
    atomic_restore "$PRE_ERAS" "$ERAS" || restore_ok=0
    atomic_restore "$PRE_STATE" "$STATE" || restore_ok=0
    atomic_restore "$PRE_CARD" "$CARD" || restore_ok=0
    [[ "$(sha256 "$ERAS")" == "$pre_eras_sha" ]] || restore_ok=0
    [[ "$(sha256 "$STATE")" == "$pre_state_sha" ]] || restore_ok=0
    [[ "$(sha256 "$CARD")" == "$pre_card_sha" ]] || restore_ok=0
    git -C "$ORCH" diff --quiet -- "$ERAS_REL" "$STATE_REL" "$CARD_REL" || restore_ok=0
    git -C "$ORCH" diff --cached --quiet -- "$ERAS_REL" "$STATE_REL" "$CARD_REL" || restore_ok=0
    if [[ -e "$OUTPUT" ]]; then
        if [[ -e "$INTERRUPTED_OUTPUT" ]]; then
            restore_ok=0
        else
            mv -- "$OUTPUT" "$INTERRUPTED_OUTPUT" || restore_ok=0
            sync -f "$INTERRUPTED_OUTPUT" || restore_ok=0
        fi
    fi
    if (( restore_ok )); then
        phase="rolled_back"
        output_sha=""
        write_journal || restore_ok=0
    else
        phase="rollback_incomplete"
        write_journal || true
    fi
    set -e
    return "$((1 - restore_ok))"
}

archive_transaction() {
    local label=$1 stamp destination
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    destination="$TXN_DIR.$label-$stamp"
    [[ -d "$TXN_DIR" && ! -e "$destination" ]] || return 1
    mv -- "$TXN_DIR" "$destination" || return 1
    sync -f "$(dirname "$TXN_DIR")" || return 1
    printf 'Retained transaction and preimages at: %s\n' "$destination"
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM HUP
    if (( transaction_active )); then
        if ! restore_preimages; then
            printf 'ROLLBACK INCOMPLETE: inspect %s and its durable preimages.\n' "$JOURNAL" >&2
            exit 2
        fi
        if ! archive_transaction "rolled-back"; then
            printf 'ROLLBACK COMPLETE but transaction archival failed; inspect %s.\n' "$TXN_DIR" >&2
            exit 2
        fi
    fi
    exit "$rc"
}

recover_transaction() {
    if [[ -e "$PREP_DIR" && ! -e "$TXN_DIR" ]]; then
        local abandoned_at abandoned
        printf '%s\n' \
            "Interrupted preimage preparation found at $PREP_DIR." \
            "No live target mutation starts before preparation is promoted to $TXN_DIR." \
            "Type RECOVER-V8-ERA-FENCE to retain it under a timestamped forensic path."
        read -r -p '> ' recovery_decision
        [[ "$recovery_decision" == "RECOVER-V8-ERA-FENCE" ]] || fail "recovery aborted"
        acquire_locks
        autopilot_is_running && fail "AutoPilot started before preparation recovery"
        validate_pre_fence_state
        abandoned_at="$(date -u +%Y%m%dT%H%M%SZ)"
        abandoned="$PREP_DIR.abandoned-$abandoned_at"
        [[ ! -e "$abandoned" ]] || fail "preparation recovery destination already exists"
        mv -- "$PREP_DIR" "$abandoned"
        sync -f "$(dirname "$PREP_DIR")"
        printf 'Retained interrupted preparation at: %s\n' "$abandoned"
        return
    fi
    [[ -f "$JOURNAL" && -f "$PRE_ERAS" && -f "$PRE_STATE" && -f "$PRE_CARD" ]] ||
        fail "durable transaction preimages are incomplete"
    phase="$(jq -r '.phase' "$JOURNAL")"
    [[ "$phase" != "complete" ]] || {
        printf 'Transaction is already complete; recovery is neither needed nor allowed.\n'
        exit 0
    }
    pre_eras_sha="$(jq -r '.preimages.instrument_eras_sha256' "$JOURNAL")"
    pre_state_sha="$(jq -r '.preimages.autopilot_state_sha256' "$JOURNAL")"
    pre_card_sha="$(jq -r '.preimages.system_card_sha256' "$JOURNAL")"
    require_sha "$PRE_ERAS" "$pre_eras_sha" "era-registry preimage"
    require_sha "$PRE_STATE" "$pre_state_sha" "AutoPilot-state preimage"
    require_sha "$PRE_CARD" "$pre_card_sha" "system-card preimage"

    printf '%s\n' \
        "Recovery will restore exactly the three durable preimages in $TXN_DIR." \
        "Type RECOVER-V8-ERA-FENCE to continue."
    read -r -p '> ' recovery_decision
    [[ "$recovery_decision" == "RECOVER-V8-ERA-FENCE" ]] || fail "recovery aborted"

    acquire_locks
    autopilot_is_running && fail "AutoPilot started before recovery"
    restore_preimages || fail "recovery did not restore and verify every preimage"
    archive_transaction "recovered" ||
        fail "recovery restored live files but could not archive the transaction"
    printf 'Recovered the interrupted eligibility-fence transaction.\n'
}

idempotent_complete() {
    [[ -f "$JOURNAL" && -f "$OUTPUT" ]] || return 1
    [[ "$(jq -r '.phase' "$JOURNAL" 2>/dev/null)" == "complete" ]] || return 1
    local recorded
    recorded="$(jq -r '.output_sha256' "$JOURNAL")"
    [[ "$recorded" =~ ^[0-9a-f]{64}$ ]] || fail "completed journal has no output digest"
    require_sha "$OUTPUT" "$recorded" "completed eligibility-fence attestation"
    jq -e '
        .decision == "RATIFY-V8-ERA-FENCE" and
        .scope == "eligibility_fence_only" and
        .production_frozen == false and .separate_freeze_required == true
    ' "$OUTPUT" >/dev/null || fail "completed output has the wrong scope"
    printf 'Eligibility fence is already ratified and digest-valid: %s\n' "$OUTPUT"
}

mutate_eras() {
    python3 - "$ERAS" <<'PY'
from pathlib import Path
import os
import tempfile
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
marker = "\nknown_dead_instrument_items:\n"
if text.count(marker) != 1:
    raise SystemExit("instrument-era insertion marker is missing or ambiguous")
if "id: E8-cpu-kernel" in text or "id: E8-autopilot-speed" in text:
    raise SystemExit("E8 era already exists")
rows = """
  - id: E8-cpu-kernel
    from: "2026-07-25T18:38:43Z"
    scope: cpu_bench
    note: >
      v8 production cutover. Single kernel: production-consolidated-v8 at
      llama.cpp commit 67a433bf45a8a091d83b4ea0b32ff0735fd51800
      (binary version 10107 / 67a433bf4), promoted from the fully validated
      experimental-v8-refresh-20260724 lineage. RECONCILIATION: pre-boundary
      CPU throughput and quality/eval rows measured on v7 or experimental-v8
      are historical priors for decisions about the production-consolidated-v8
      stack. Do not rescale across this boundary; re-measure within era under
      P-BENCH/P-QUAL/P-GPU protocols with host attestation. The campaign-scoped
      WAIVE-Q8 decision means this eligibility fence makes no Q8 performance or
      non-regression claim.

  - id: E8-autopilot-speed
    from: "2026-07-25T18:38:43Z"
    scope: autopilot_speed
    note: >
      AutoPilot Pareto/frontier speed boundary for the v8 production kernel
      cutover. orchestration/autopilot_state.json:pareto_epoch_ts is advanced
      to this timestamp so pre-v8 speed rows cannot silently define the current
      production-consolidated-v8 frontier. Treat pre-boundary AutoPilot
      speed/frontier rows as historical priors until a controlled v8-only
      frontier rerun/rebuild clears the frontier_rerun_required state marker.
"""
new_text = text.replace(marker, rows + marker, 1)
fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(new_text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
except BaseException:
    Path(temporary).unlink(missing_ok=True)
    raise
PY
}

mutate_state() {
    python3 - "$STATE" "$PROMOTION_AT" "$PROMOTION_EPOCH" <<'PY'
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile

path = Path(sys.argv[1])
boundary = sys.argv[2]
epoch = float(sys.argv[3])
state = json.loads(path.read_text(encoding="utf-8"))
previous = deepcopy(state["frontier_rerun_required"])
state["active_instrument_eras"] = {
    "autopilot_speed": "E8-autopilot-speed",
    "cpu_bench": "E8-cpu-kernel",
}
state["pareto_epoch_ts"] = epoch
state["pareto_exclude_before_ts"] = epoch
state["frontier_rerun_required"] = {
    "completed_numeric_trials": 0,
    "min_numeric_trials": 16,
    "minimum_action": (
        "Run at least 16 completed current-marker numeric_trial rows under "
        "active_instrument_eras.autopilot_speed=E8-autopilot-speed, then "
        "rebuild/inspect the v8-only frontier before clearing this marker."
    ),
    "opened_at": boundary,
    "previous_marker": previous,
    "reason": (
        "E8-autopilot-speed production-consolidated-v8 era opened; rerun/rebuild "
        "a v8-only AutoPilot Pareto frontier before using speed maxima or "
        "consolidated max-performance guidance."
    ),
    "required": True,
    "rerun_started_at": boundary,
}
fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
except BaseException:
    Path(temporary).unlink(missing_ok=True)
    raise
PY
}

validate_post_fence() {
    "$ORCH/.venv/bin/python" - \
        "$PRE_ERAS" "$PRE_STATE" "$ERAS" "$STATE" "$CARD" \
        "$PROMOTION_AT" "$PROMOTION_EPOCH" <<'PY'
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sys
import yaml

pre_eras_path, pre_state_path, eras_path, state_path, card_path = map(Path, sys.argv[1:6])
boundary = sys.argv[6]
epoch = float(sys.argv[7])
if datetime.fromisoformat(boundary.replace("Z", "+00:00")).timestamp() != epoch:
    raise SystemExit("promotion timestamp and epoch diverged")

before_registry = yaml.safe_load(pre_eras_path.read_text(encoding="utf-8"))
after_registry = yaml.safe_load(eras_path.read_text(encoding="utf-8"))
before_rows = before_registry["eras"]
after_rows = after_registry["eras"]
if len(after_rows) != len(before_rows) + 2:
    raise SystemExit("era registry changed by something other than two appended rows")
if after_rows[:-2] != before_rows:
    raise SystemExit("historical era rows were modified or reordered")
cpu, speed = after_rows[-2:]
if cpu.get("id") != "E8-cpu-kernel" or cpu.get("from") != boundary or cpu.get("scope") != "cpu_bench":
    raise SystemExit("E8 CPU row identity is not exact")
if speed.get("id") != "E8-autopilot-speed" or speed.get("from") != boundary or speed.get("scope") != "autopilot_speed":
    raise SystemExit("E8 AutoPilot row identity is not exact")
cpu_note = str(cpu.get("note", ""))
speed_note = str(speed.get("note", ""))
for required in (
    "production-consolidated-v8",
    "67a433bf45a8a091d83b4ea0b32ff0735fd51800",
    "WAIVE-Q8",
    "no Q8 performance or non-regression claim",
):
    if required not in cpu_note:
        raise SystemExit(f"E8 CPU note is missing: {required}")
for required in ("production-consolidated-v8", "historical priors", "frontier_rerun_required"):
    if required not in speed_note:
        raise SystemExit(f"E8 AutoPilot note is missing: {required}")
if after_registry.get("known_dead_instrument_items") != before_registry.get("known_dead_instrument_items"):
    raise SystemExit("known-dead instrument rows changed")

before_state = json.loads(pre_state_path.read_text(encoding="utf-8"))
after_state = json.loads(state_path.read_text(encoding="utf-8"))
expected = deepcopy(before_state)
previous = deepcopy(before_state["frontier_rerun_required"])
expected["active_instrument_eras"] = {
    "autopilot_speed": "E8-autopilot-speed",
    "cpu_bench": "E8-cpu-kernel",
}
expected["pareto_epoch_ts"] = epoch
expected["pareto_exclude_before_ts"] = epoch
expected["frontier_rerun_required"] = {
    "completed_numeric_trials": 0,
    "min_numeric_trials": 16,
    "minimum_action": (
        "Run at least 16 completed current-marker numeric_trial rows under "
        "active_instrument_eras.autopilot_speed=E8-autopilot-speed, then "
        "rebuild/inspect the v8-only frontier before clearing this marker."
    ),
    "opened_at": boundary,
    "previous_marker": previous,
    "reason": (
        "E8-autopilot-speed production-consolidated-v8 era opened; rerun/rebuild "
        "a v8-only AutoPilot Pareto frontier before using speed maxima or "
        "consolidated max-performance guidance."
    ),
    "required": True,
    "rerun_started_at": boundary,
}
if after_state != expected:
    raise SystemExit("AutoPilot state differs from the exact allowed E8 transformation")

card = card_path.read_text(encoding="utf-8")
if "active_instrument_eras: autopilot_speed=E8-autopilot-speed, cpu_bench=E8-cpu-kernel" not in card:
    raise SystemExit("system card does not expose the exact E8 eras")
if "frontier_rerun_required: true" not in card or "production-consolidated-v8" not in card:
    raise SystemExit("system card does not expose the fail-closed v8 frontier marker")
PY
}

write_output() {
    local ratified_at script_sha eras_sha state_sha card_sha
    local root_head orch_head research_head output_tmp
    ratified_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    script_sha="$(sha256 "$SCRIPT_PATH")"
    eras_sha="$(sha256 "$ERAS")"
    state_sha="$(sha256 "$STATE")"
    card_sha="$(sha256 "$CARD")"
    root_head="$(git -C "$ROOT" rev-parse HEAD)"
    orch_head="$(git -C "$ORCH" rev-parse HEAD)"
    research_head="$(git -C "$RESEARCH" rev-parse HEAD)"
    output_tmp="$ROOT/artifacts/operator/.ratify_v8_era_fence_20260725.json.tmp"

    python3 - \
        "$output_tmp" "$ratified_at" "$script_sha" "$eras_sha" "$state_sha" "$card_sha" \
        "$root_head" "$orch_head" "$research_head" <<'PY'
import json
import os
from pathlib import Path
import sys

output = Path(sys.argv[1])
payload = {
    "schema": "epyc.operator_v8_era_fence_attestation.v2",
    "decision": "RATIFY-V8-ERA-FENCE",
    "scope": "eligibility_fence_only",
    "production_frozen": False,
    "separate_freeze_required": True,
    "ratified_at": sys.argv[2],
    "production_branch": "production-consolidated-v8",
    "production_head": "67a433bf45a8a091d83b4ea0b32ff0735fd51800",
    "production_binary_sha256": {
        "cpu": "a4b667163022aa166ade7c0e00fa4e775b37662e02c10da7642c8c23a4d6b414",
        "hip": "112c560f1c978c584a9899539851348a0ce1e05cde458061c281758aff066882",
    },
    "repository_heads": {
        "epyc_root": sys.argv[7],
        "epyc_orchestrator": sys.argv[8],
        "epyc_inference_research": sys.argv[9],
    },
    "evidence_commits": {
        "root": "97e6dd8687204cdce7af95351f77e1477bcd486e",
        "orchestrator_fixture": "bf300a2688d924e23bd946e0ece1978f3c87f586",
        "research_cpu": "367ed4ca05c52c83f735414ff389cc7d4994873d",
        "research_pgpu": "991942334f4e1dca8c905e7ce4ca5a642d8d470d",
    },
    "cutover_boundary": "2026-07-25T18:38:43Z",
    "active_instrument_eras": {
        "cpu_bench": "E8-cpu-kernel",
        "autopilot_speed": "E8-autopilot-speed",
    },
    "frontier_rerun_required": {"required": True, "min_numeric_trials": 16},
    "q8_claim": "none; campaign-scoped WAIVE-Q8 remains binding",
    "required_next_action": (
        "Run and validate the separate production freeze transaction; this "
        "attestation establishes only the E8 eligibility fence."
    ),
    "evidence_sha256": {
        "cutover_journal": "e2c3b9f67072798eafcb945004c2faed59a04e048ce7e1510a98611d82330991",
        "quarter_stack_summary": "e25feaadba51d8d75736b31932ea088f8f2a0a7fafbd29d63f80c66a799c54f4",
        "quarter_stack_rows": "808207961490e5d2df9a24e79e3d53ee617ccfec3e69a2229e2656f2b54fa639",
        "quarter_promotion_gate": "9d37c9fc6b90889a2b68cbf99bd7d6417508eb9c0ed93b25147f8c36f526de4b",
        "waive_q8": "fcd52b61610fcc2782e11f41ffac359343233924805f83d872eeceffbb7522d7",
        "promotion_attestation": "54daa05c3c0540a65fda3cb008fd1ec6e89a9c2a169ced0b2af81bf12783bc5d",
        "cpu_matrix": "fb0b8db8bcf1f8aea34cbf1ca7231df36b223ebd7556df61f98d8a471176943a",
        "pgpu_summary": "73c28e4b86a38732c7fa99f3210e31f53efcced6420b8e81607007690621059e",
        "pgpu_completeness_audit": "c9410dc7124232c8652f5ccec17e3bea3e9d5c6a0a77d537a0b70ea8689c74e9",
        "pgpu_audit_provenance": "c8d06d81f9dddb5df130f48bff1d0a3918576ba0f8ec9a0137041322598555ca",
    },
    "artifacts": {
        "operator_script_sha256": sys.argv[3],
        "instrument_eras_sha256": sys.argv[4],
        "autopilot_state_sha256": sys.argv[5],
        "system_card_sha256": sys.argv[6],
        "transaction_journal": (
            "artifacts/operator/v8-era-fence-transaction-20260725T183843Z/journal.json"
        ),
    },
}
with output.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())
PY
    mv "$output_tmp" "$OUTPUT"
    sync -f "$OUTPUT"
    sync -f "$(dirname "$OUTPUT")"
}

main() {
    for command in git jq sha256sum uv python3 flock rg install mktemp sync; do
        command -v "$command" >/dev/null || fail "missing required command: $command"
    done
    [[ -x "$ORCH/.venv/bin/python" ]] || fail "orchestrator venv Python is missing"

    case ${1:-} in
        --recover)
            recover_transaction
            return
            ;;
        --status)
            if [[ -f "$JOURNAL" ]]; then
                jq . "$JOURNAL"
            elif [[ -e "$PREP_DIR" ]]; then
                printf '%s\n' \
                    "Interrupted preparation exists at $PREP_DIR." \
                    "No live target mutation starts until preparation is atomically promoted to $TXN_DIR."
            else
                printf 'No v8 era-fence transaction exists.\n'
            fi
            return
            ;;
        "")
            ;;
        *)
            fail "usage: $0 [--status|--recover]"
            ;;
    esac

    if [[ -e "$PREP_DIR" ]]; then
        fail "interrupted preparation exists; no live target mutation started; inspect and quarantine $PREP_DIR"
    fi
    if [[ -e "$TXN_DIR" || -e "$OUTPUT" ]]; then
        idempotent_complete && return
        fail "partial or conflicting transaction exists; inspect --status and use --recover"
    fi

    require_tracked_clean "$ROOT" "${SCRIPT_PATH#"$ROOT/"}"
    validate_production
    validate_evidence
    require_orchestrator_clean
    validate_pre_fence_state
    preprompt_state_sha="$(sha256 "$STATE")"
    autopilot_is_running && fail "AutoPilot is running; stop it before ratification"

    [[ -t 0 ]] || fail "operator ratification requires an interactive terminal"
    printf '%s\n' \
        'This ratifies only the v8 E8 measurement-era eligibility fence.' \
        'It does not freeze production; a separate reviewed freeze transaction must follow.' \
        'It appends E8-cpu-kernel and E8-autopilot-speed at 2026-07-25T18:38:43Z.' \
        'It demotes pre-boundary speed/frontier evidence to historical prior for v8 decisions.' \
        'It requires 16 fresh v8-era numeric trials before AutoPilot speed maxima are trusted.' \
        'The campaign-scoped WAIVE-Q8 remains binding; no Q8 performance or non-regression claim is made.' \
        'Type RATIFY-V8-ERA-FENCE to attest this decision; anything else aborts.'
    read -r -p '> ' decision
    [[ "$decision" == "RATIFY-V8-ERA-FENCE" ]] || {
        printf 'Aborted; no files changed.\n'
        return 1
    }

    acquire_locks
    validate_production
    validate_evidence
    require_orchestrator_clean
    require_same_preprompt_state
    validate_pre_fence_state
    autopilot_is_running && fail "AutoPilot started after confirmation"

    mkdir "$PREP_DIR"
    install -m 0644 "$ERAS" "$PREP_DIR/$(basename "$PRE_ERAS")"
    install -m 0644 "$STATE" "$PREP_DIR/$(basename "$PRE_STATE")"
    install -m 0644 "$CARD" "$PREP_DIR/$(basename "$PRE_CARD")"
    sync -f "$PREP_DIR/$(basename "$PRE_ERAS")"
    sync -f "$PREP_DIR/$(basename "$PRE_STATE")"
    sync -f "$PREP_DIR/$(basename "$PRE_CARD")"
    pre_eras_sha="$(sha256 "$PREP_DIR/$(basename "$PRE_ERAS")")"
    pre_state_sha="$(sha256 "$PREP_DIR/$(basename "$PRE_STATE")")"
    pre_card_sha="$(sha256 "$PREP_DIR/$(basename "$PRE_CARD")")"
    phase="prepared"
    write_journal_to "$PREP_DIR"
    mv -- "$PREP_DIR" "$TXN_DIR"
    sync -f "$(dirname "$TXN_DIR")"

    transaction_active=1
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM HUP

    mutate_eras
    phase="eras_written"
    write_journal

    mutate_state
    phase="state_written"
    write_journal

    (
        cd "$ORCH"
        uv run python scripts/autopilot/gen_system_card.py
        uv run python scripts/autopilot/gen_system_card.py --check
        .venv/bin/pytest -q \
            tests/unit/test_dashboard_pareto_eras.py \
            tests/unit/test_autopilot_system_card.py \
            tests/unit/test_generate_attestation.py
    )
    phase="card_generated_and_tests_passed"
    write_journal

    validate_post_fence
    require_only_expected_orchestrator_changes
    autopilot_is_running && fail "AutoPilot appeared during the locked transaction"
    phase="deep_validation_passed"
    write_journal

    write_output
    output_sha="$(sha256 "$OUTPUT")"
    phase="output_written"
    write_journal

    # Recheck exact live content after publication and before declaring completion.
    validate_post_fence
    [[ "$(sha256 "$OUTPUT")" == "$output_sha" ]] ||
        fail "operator attestation changed before completion"
    phase="complete"
    write_journal
    transaction_active=0
    trap - EXIT INT TERM HUP

    printf '\nEligibility-fence attestation created:\n%s\n' "$OUTPUT"
    sha256sum "$OUTPUT"
    printf 'Production remains unfrozen; execute the separate reviewed freeze transaction next.\n'
}

main "$@"
