#!/bin/bash
# Human-only, post-E8 mechanical freeze attestation for production-consolidated-v8.
# It never changes the production tree or the E8 trust-boundary files.
set -euo pipefail

ROOT=/mnt/raid0/llm/epyc-root
ORCH=/mnt/raid0/llm/epyc-orchestrator
PROD=/mnt/raid0/llm/llama.cpp
RESEARCH=/mnt/raid0/llm/epyc-inference-research

EXPECTED_HEAD=67a433bf45a8a091d83b4ea0b32ff0735fd51800
EXPECTED_VERSION='10107 (67a433bf4)'
EXPECTED_CPU_SHA=a4b667163022aa166ade7c0e00fa4e775b37662e02c10da7642c8c23a4d6b414
EXPECTED_HIP_SHA=112c560f1c978c584a9899539851348a0ce1e05cde458061c281758aff066882
PROMOTION_AT=2026-07-25T18:38:43Z
PROMOTION_EPOCH=1785004723.0

ERAS_REL=orchestration/instrument_eras.yaml
STATE_REL=orchestration/autopilot_state.json
CARD_REL=scripts/autopilot/system_card.md
ERAS="$ORCH/$ERAS_REL"
STATE="$ORCH/$STATE_REL"
CARD="$ORCH/$CARD_REL"

E8_REL=artifacts/operator/ratify_v8_era_fence_20260725.json
E8_TXN_REL=artifacts/operator/v8-era-fence-transaction-20260725T183843Z
E8="$ROOT/$E8_REL"
E8_TXN="$ROOT/$E8_TXN_REL"
E8_JOURNAL="$E8_TXN/journal.json"
E8_PRE_ERAS="$E8_TXN/instrument_eras.yaml.before"
E8_PRE_STATE="$E8_TXN/autopilot_state.json.before"
E8_PRE_CARD="$E8_TXN/system_card.md.before"

CUTOVER_REL=artifacts/operator/v8-cutover-20260725T183843Z-67a433bf4/journal.json
QUARTER_REL=artifacts/operator/v8-quarter-smoke-20260725T190117Z/summary.json
QUARTER_ROWS_REL=artifacts/operator/v8-quarter-smoke-20260725T190117Z/quarter_smoke_rerun2.jsonl
QUARTER_GATE_REL=artifacts/operator/v8-quarter-smoke-20260725T190117Z/quarter_promotion_gate.log
WAIVE_REL=artifacts/operator/waive_q8_cpu_prefill_v8_20260725.json
PROVISIONAL_REL=handoffs/active/laguna-pgpu1-v8-promotion-attestation.json
CPU_REL=data/kernel-v8-candidate/cpu-prefill-regression/run-20260725T155655Z-v4-waive-q8-kfd-procrace-swapoff/summary.json
PGPU_REL=data/gpu-mi210/laguna-iq2-dflash-pgpu1-v8-rerun1/run-20260725T184624Z/summary.json
PGPU_AUDIT_REL=data/gpu-mi210/laguna-iq2-dflash-pgpu1-v8-rerun1/run-20260725T184624Z/retrocert_completeness_audit.json
PGPU_PROV_REL=data/gpu-mi210/laguna-iq2-dflash-pgpu1-v8-rerun1/run-20260725T184624Z/retrocert_audit_provenance.json
BOTH_SMOKE_REL=artifacts/operator/v8-both-smoke-20260725T202558Z/both_stack_smoke.jsonl
LIVE_API_REL=artifacts/operator/v8-both-smoke-20260725T202558Z/api_health_6of6.json
QUALITY_POINTER=/tmp/v8-latest-quality-gate-dir.txt

CUTOVER="$ROOT/$CUTOVER_REL"
QUARTER="$ROOT/$QUARTER_REL"
QUARTER_ROWS="$ROOT/$QUARTER_ROWS_REL"
QUARTER_GATE="$ROOT/$QUARTER_GATE_REL"
WAIVE="$ROOT/$WAIVE_REL"
PROVISIONAL="$ROOT/$PROVISIONAL_REL"
CPU_SUMMARY="$RESEARCH/$CPU_REL"
PGPU_SUMMARY="$RESEARCH/$PGPU_REL"
PGPU_AUDIT="$RESEARCH/$PGPU_AUDIT_REL"
PGPU_PROV="$RESEARCH/$PGPU_PROV_REL"
BOTH_SMOKE="$ROOT/$BOTH_SMOKE_REL"
LIVE_API="$ROOT/$LIVE_API_REL"

QUALITY_DIR=''
QUALITY_DIR_REL=''
WORKER_BASELINE=''
WORKER_BASELINE_ROWS=''
WORKER_RESULT=''
WORKER_ROWS=''
WORKER_REPORT=''
ARCH_BASELINE=''
ARCH_BASELINE_ROWS=''
ARCH_RESULT=''
ARCH_ROWS=''
ARCH_REPORT=''
QUESTIONS=''

CUTOVER_SHA=e2c3b9f67072798eafcb945004c2faed59a04e048ce7e1510a98611d82330991
QUARTER_SHA=e25feaadba51d8d75736b31932ea088f8f2a0a7fafbd29d63f80c66a799c54f4
QUARTER_ROWS_SHA=808207961490e5d2df9a24e79e3d53ee617ccfec3e69a2229e2656f2b54fa639
QUARTER_GATE_SHA=9d37c9fc6b90889a2b68cbf99bd7d6417508eb9c0ed93b25147f8c36f526de4b
WAIVE_SHA=fcd52b61610fcc2782e11f41ffac359343233924805f83d872eeceffbb7522d7
PROVISIONAL_SHA=54daa05c3c0540a65fda3cb008fd1ec6e89a9c2a169ced0b2af81bf12783bc5d
CPU_SHA=fb0b8db8bcf1f8aea34cbf1ca7231df36b223ebd7556df61f98d8a471176943a
PGPU_SHA=73c28e4b86a38732c7fa99f3210e31f53efcced6420b8e81607007690621059e
PGPU_AUDIT_SHA=c9410dc7124232c8652f5ccec17e3bea3e9d5c6a0a77d537a0b70ea8689c74e9
PGPU_PROV_SHA=c8d06d81f9dddb5df130f48bff1d0a3918576ba0f8ec9a0137041322598555ca
BOTH_SMOKE_SHA=6742e1990581ed00ca6556ae167220a14d1b1275a94bb9f93d1c1083fb7bece2
LIVE_API_SHA=3632dd3323e1684bcee6d2be4cb93756dd7d758b44e5b88dae84659799281e92

OUTPUT="$ROOT/artifacts/operator/ratify_v8_final_freeze_20260725.json"
TXN_DIR="$ROOT/artifacts/operator/v8-final-freeze-transaction-20260725T183843Z"
PREP_DIR="$TXN_DIR.preparing"
JOURNAL="$TXN_DIR/journal.json"
SNAPSHOT_DIR="$TXN_DIR/preimages"
INTERRUPTED_OUTPUT="$TXN_DIR/attestation.interrupted.json"
LOCK="$ROOT/artifacts/operator/.v8-final-freeze.lock"
SCRIPT_REL=artifacts/operator/freeze_v8_production_20260725.sh
SCRIPT_PATH="$ROOT/$SCRIPT_REL"

phase=preflight
transaction_active=0
output_sha=''
preprompt_script_sha=''
preprompt_e8_sha=''
preprompt_journal_sha=''
preprompt_eras_sha=''
preprompt_state_sha=''
preprompt_card_sha=''
preprompt_both_smoke_sha=''
preprompt_live_api_sha=''
preprompt_quality_manifest=''

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sha256() { sha256sum -- "$1" | awk '{print $1}'; }

require_regular() {
    [[ -f "$1" && ! -L "$1" ]] || fail "$2 is missing, not regular, or is a symlink: $1"
}

require_sha() {
    require_regular "$1" "$3"
    [[ "$(sha256 "$1")" == "$2" ]] || fail "$3 SHA256 does not match reviewed evidence"
}

require_tracked_clean() {
    local repo=$1 rel=$2 expected_sha=$3
    git -C "$repo" ls-files --error-unmatch -- "$rel" >/dev/null ||
        fail "$repo/$rel is not tracked"
    git -C "$repo" diff --quiet -- "$rel" || fail "$repo/$rel has unstaged changes"
    git -C "$repo" diff --cached --quiet -- "$rel" || fail "$repo/$rel has staged changes"
    require_sha "$repo/$rel" "$expected_sha" "$repo/$rel"
}

require_tracked_at_head() {
    local repo=$1 rel=$2 label=$3 actual head_blob
    git -C "$repo" ls-files --error-unmatch -- "$rel" >/dev/null ||
        fail "$label is not tracked: $repo/$rel"
    git -C "$repo" diff --quiet -- "$rel" || fail "$label has unstaged changes"
    git -C "$repo" diff --cached --quiet -- "$rel" || fail "$label has staged changes"
    actual="$(sha256 "$repo/$rel")"
    head_blob="$(git -C "$repo" show "HEAD:$rel" | sha256sum | awk '{print $1}')" ||
        fail "$label is absent from the immutable HEAD commit"
    [[ "$actual" == "$head_blob" ]] || fail "$label does not match the immutable HEAD blob"
}

resolve_new_evidence() {
    require_regular "$QUALITY_POINTER" 'quality-gate pointer'
    [[ "$(wc -l < "$QUALITY_POINTER")" -eq 1 ]] || fail 'quality-gate pointer must contain exactly one line'
    QUALITY_DIR="$(realpath -e -- "$(sed -n '1p' "$QUALITY_POINTER")")" ||
        fail 'quality-gate pointer does not resolve'
    [[ -d "$QUALITY_DIR" && ! -L "$QUALITY_DIR" ]] || fail 'quality-gate directory is not a regular directory'
    case "$QUALITY_DIR/" in
        "$RESEARCH/data/kernel-v8-candidate/quality-gate/"run-*-both-mode/) ;;
        *) fail "quality-gate directory is outside the exact v8 both-mode namespace: $QUALITY_DIR" ;;
    esac
    QUALITY_DIR_REL="${QUALITY_DIR#"$RESEARCH/"}"
    WORKER_BASELINE="$QUALITY_DIR/v7-worker-general-baseline.json"
    WORKER_BASELINE_ROWS="$QUALITY_DIR/v7-worker-general-baseline.per-question.jsonl"
    WORKER_RESULT="$QUALITY_DIR/v8-production-worker-general.json"
    WORKER_ROWS="$QUALITY_DIR/v8-production-worker-general.per-question.jsonl"
    WORKER_REPORT="$QUALITY_DIR/v8-worker-quality-gate-report.md"
    ARCH_BASELINE="$QUALITY_DIR/v7-architect-general-baseline.json"
    ARCH_BASELINE_ROWS="$QUALITY_DIR/v7-architect-general-baseline.per-question.jsonl"
    ARCH_RESULT="$QUALITY_DIR/v8-production-architect-general.json"
    ARCH_ROWS="$QUALITY_DIR/v8-production-architect-general.per-question.jsonl"
    ARCH_REPORT="$QUALITY_DIR/v8-architect-quality-gate-report.md"
    QUESTIONS="$QUALITY_DIR/questions.json"
}

quality_manifest() {
    local path
    for path in "$WORKER_BASELINE" "$WORKER_BASELINE_ROWS" "$WORKER_RESULT" "$WORKER_ROWS" "$WORKER_REPORT" \
        "$ARCH_BASELINE" "$ARCH_BASELINE_ROWS" "$ARCH_RESULT" "$ARCH_ROWS" "$ARCH_REPORT" "$QUESTIONS"; do
        printf '%s  %s\n' "$(sha256 "$path")" "${path#"$RESEARCH/"}"
    done | LC_ALL=C sort
}

require_commit_ancestor() {
    local repo=$1 commit=$2 label=$3
    git -C "$repo" cat-file -e "$commit^{commit}" || fail "$label commit is unavailable"
    git -C "$repo" merge-base --is-ancestor "$commit" HEAD ||
        fail "$label commit is not an ancestor of $repo HEAD"
}

require_blob_at_commit() {
    local repo=$1 commit=$2 rel=$3 expected=$4 label=$5 actual
    actual="$(git -C "$repo" show "$commit:$rel" | sha256sum | awk '{print $1}')" ||
        fail "$label is absent from its immutable evidence commit"
    [[ "$actual" == "$expected" ]] || fail "$label differs in its immutable evidence commit"
}

validate_production() {
    [[ "$(git -C "$PROD" branch --show-current)" == production-consolidated-v8 ]] ||
        fail 'production branch is not production-consolidated-v8'
    [[ "$(git -C "$PROD" rev-parse HEAD)" == "$EXPECTED_HEAD" ]] ||
        fail 'production HEAD is not the validated v8 tip'
    git -C "$PROD" diff --quiet || fail 'production source has tracked unstaged changes'
    git -C "$PROD" diff --cached --quiet || fail 'production source has tracked staged changes'
    require_sha "$PROD/build/bin/llama-server" "$EXPECTED_CPU_SHA" 'production CPU llama-server'
    require_sha "$PROD/build-hip/bin/llama-server" "$EXPECTED_HIP_SHA" 'production HIP llama-server'
    local version
    version="$(timeout 15 "$PROD/build/bin/llama-server" --version 2>&1 | head -1)" ||
        fail 'production CPU llama-server --version failed'
    [[ "$version" == *"$EXPECTED_VERSION"* ]] || fail "production version is not $EXPECTED_VERSION: $version"
    bash "$ROOT/scripts/session/verify_llama_cpp.sh" >/dev/null
}

validate_evidence() {
    require_commit_ancestor "$ROOT" 97e6dd8687204cdce7af95351f77e1477bcd486e 'root v8 evidence'
    require_commit_ancestor "$RESEARCH" 367ed4ca05c52c83f735414ff389cc7d4994873d 'CPU evidence'
    require_commit_ancestor "$RESEARCH" 991942334f4e1dca8c905e7ce4ca5a642d8d470d 'P-GPU evidence'
    require_blob_at_commit "$ROOT" 97e6dd8687204cdce7af95351f77e1477bcd486e "$CUTOVER_REL" "$CUTOVER_SHA" 'cutover journal'
    require_blob_at_commit "$ROOT" 97e6dd8687204cdce7af95351f77e1477bcd486e "$QUARTER_REL" "$QUARTER_SHA" 'quarter summary'
    require_blob_at_commit "$ROOT" 97e6dd8687204cdce7af95351f77e1477bcd486e "$QUARTER_ROWS_REL" "$QUARTER_ROWS_SHA" 'quarter rows'
    require_blob_at_commit "$ROOT" 97e6dd8687204cdce7af95351f77e1477bcd486e "$QUARTER_GATE_REL" "$QUARTER_GATE_SHA" 'quarter gate'
    require_blob_at_commit "$ROOT" 97e6dd8687204cdce7af95351f77e1477bcd486e "$WAIVE_REL" "$WAIVE_SHA" 'WAIVE-Q8 attestation'
    require_blob_at_commit "$ROOT" 97e6dd8687204cdce7af95351f77e1477bcd486e "$PROVISIONAL_REL" "$PROVISIONAL_SHA" 'immutable provisional attestation'
    require_blob_at_commit "$RESEARCH" 367ed4ca05c52c83f735414ff389cc7d4994873d "$CPU_REL" "$CPU_SHA" 'CPU matrix'
    require_blob_at_commit "$RESEARCH" 991942334f4e1dca8c905e7ce4ca5a642d8d470d "$PGPU_REL" "$PGPU_SHA" 'P-GPU summary'
    require_blob_at_commit "$RESEARCH" 991942334f4e1dca8c905e7ce4ca5a642d8d470d "$PGPU_AUDIT_REL" "$PGPU_AUDIT_SHA" 'P-GPU audit'
    require_blob_at_commit "$RESEARCH" 991942334f4e1dca8c905e7ce4ca5a642d8d470d "$PGPU_PROV_REL" "$PGPU_PROV_SHA" 'P-GPU provenance'

    require_tracked_clean "$ROOT" "$CUTOVER_REL" "$CUTOVER_SHA"
    require_tracked_clean "$ROOT" "$QUARTER_REL" "$QUARTER_SHA"
    require_tracked_clean "$ROOT" "$QUARTER_ROWS_REL" "$QUARTER_ROWS_SHA"
    require_tracked_clean "$ROOT" "$QUARTER_GATE_REL" "$QUARTER_GATE_SHA"
    require_tracked_clean "$ROOT" "$WAIVE_REL" "$WAIVE_SHA"
    require_tracked_clean "$ROOT" "$PROVISIONAL_REL" "$PROVISIONAL_SHA"
    require_tracked_clean "$RESEARCH" "$CPU_REL" "$CPU_SHA"
    require_tracked_clean "$RESEARCH" "$PGPU_REL" "$PGPU_SHA"
    require_tracked_clean "$RESEARCH" "$PGPU_AUDIT_REL" "$PGPU_AUDIT_SHA"
    require_tracked_clean "$RESEARCH" "$PGPU_PROV_REL" "$PGPU_PROV_SHA"

    jq -e --arg head "$EXPECTED_HEAD" --arg at "$PROMOTION_AT" '
        .schema == "epyc.kernel_cutover_journal.v1" and .phase == "complete" and
        .production_branch == "production-consolidated-v8" and .production_head == $head and
        .promoted_at == $at and .rollback_branch == "production-consolidated-v7" and
        .rollback_head == "6ad45fa3ff6718c07c000061dbc6e29c1771f6e3" and
        .cpu_installed == 1 and .hip_installed == 1 and .completed == 1
    ' "$CUTOVER" >/dev/null || fail 'cutover journal predicate failed'
    jq -e --arg head "$EXPECTED_HEAD" '
        .schema == "epyc.v8_quarter_stack_smoke.v1" and .status == "pass" and
        .production_kernel.branch == "production-consolidated-v8" and
        .production_kernel.head == $head and .production_kernel.version == "10107 (67a433bf4)" and
        .final_attempt.rows == 20 and
        .final_attempt.passed == 20 and .final_attempt.failed == 0 and
        .promotion_guard.kernel_regression == false
    ' "$QUARTER" >/dev/null || fail 'superseded quarter-stack provenance predicate failed'
    jq -e --arg head "$EXPECTED_HEAD" '
        .schema == "epyc.cpu_prefill_v8.operator_waiver.v1" and .decision == "WAIVE-Q8" and
        .candidate_head == $head and .scope.excluded_arm_runs == 4 and
        .scope.remaining_matched_pairs == 14 and
        any(.consequences[]; . == "No v8 Q8 non-regression claim may be made from this campaign.")
    ' "$WAIVE" >/dev/null || fail 'WAIVE-Q8 predicate failed'
    jq -e --arg head "$EXPECTED_HEAD" --arg hip "$EXPECTED_HIP_SHA" '
        .schema == "epyc.kernel_promotion_attestation.v1" and
        .status == "production_promoted_pending_gpu_certification" and
        .production_branch == "production-consolidated-v8" and .production_head == $head and
        .frozen == false and .server_binary.sha256 == $hip and
        .rollback.branch == "production-consolidated-v7"
    ' "$PROVISIONAL" >/dev/null || fail 'provisional attestation predicate failed'
    jq -e --arg waive "$WAIVE_SHA" '
        .schema == "cpu-prefill-v8-regression.v3" and .throughput_status == "pass" and
        .throughput_failures == [] and .input_binding_status == "identical" and
        (.pair_results | length) == 14 and (.plan.arm_runs | length) == 28 and
        ([.plan.arm_runs[].model] | index("qwen36_q8")) == null and
        .plan.q8_waiver.source.sha256 == $waive and
        (.plan.explicit_exclusion | index("qwen3.5-122b")) != null and
        (.iq_utility | length) == 3 and all(.iq_utility[]; .iqk == 1 and .state == "pass")
    ' "$CPU_SUMMARY" >/dev/null || fail 'WAIVE-Q8 CPU matrix predicate failed'
    jq -e --arg hip "$EXPECTED_HIP_SHA" '
        .schema == "epyc.laguna_iq2_dflash_pgpu1.summary.v2" and .status == "ok" and
        .production_named_kernel == true and .final_guard_valid == true and .final_clean == true and
        .execution_binding_valid == true and .per_replicate_bindings_valid == true and
        .matrix_cardinality_valid == true and .post_execution_identity.binding.server.sha256 == $hip and
        (.results | length) == 10 and all(.results[]; .status == "ok")
    ' "$PGPU_SUMMARY" >/dev/null || fail 'P-GPU production matrix predicate failed'
    jq -e '
        .schema == "epyc.pgpu1_artifact_completeness_audit.v1" and .status == "complete" and
        .recommendation == "retro_cert_candidates_present" and
        .artifacts[0].missing_required_fields == [] and .artifacts[0].near_miss_fields == []
    ' "$PGPU_AUDIT" >/dev/null || fail 'P-GPU completeness predicate failed'
    jq -e '
        .schema == "epyc.pgpu1_retrocert_audit_provenance.v1" and .protocol == "P-GPU-1" and
        .source_summary.sha256 == "73c28e4b86a38732c7fa99f3210e31f53efcced6420b8e81607007690621059e" and
        .corrected_audit.status == "complete" and .decision.retro_certification_eligible == true
    ' "$PGPU_PROV" >/dev/null || fail 'P-GPU provenance predicate failed'
}

validate_result_from_rows() {
    local result=$1 rows=$2 expected_arm=$3 expected_kernel=$4 expected_binary=$5
    python3 - "$QUESTIONS" "$result" "$rows" "$expected_arm" "$expected_kernel" "$expected_binary" <<'PY'
import json
import math
from pathlib import Path
import sys

questions_path = Path(sys.argv[1]).resolve(strict=True)
result_path = Path(sys.argv[2])
rows_path = Path(sys.argv[3])
expected_arm = sys.argv[4]
expected_kernel = sys.argv[5]
expected_binary = sys.argv[6]

questions = json.loads(questions_path.read_text(encoding="utf-8"))["suites"]
expected_counts = {"mmlu_pro": 200, "gpqa": 195}
if set(questions) != set(expected_counts):
    raise SystemExit("question suite set is not exact")
question_rows = {}
for suite, items in questions.items():
    if len(items) != expected_counts[suite]:
        raise SystemExit(f"question count mismatch for {suite}")
    for item in items:
        key = (suite, str(item["id"]))
        if key in question_rows:
            raise SystemExit(f"duplicate question key: {key}")
        if item.get("suite") != suite:
            raise SystemExit(f"question suite mismatch: {key}")
        question_rows[key] = item

observations = []
with rows_path.open(encoding="utf-8") as handle:
    for line_number, line in enumerate(handle, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSONL row {line_number}: {exc}") from exc
        observations.append(row)
if len(observations) != sum(expected_counts.values()):
    raise SystemExit("per-question total is not exactly 395")

seen = set()
derived = {suite: {"n": 0, "correct": 0, "errors": 0} for suite in expected_counts}
for row in observations:
    suite = row.get("suite")
    qid = str(row.get("id"))
    seed = row.get("seed")
    key = (suite, qid, seed)
    if key in seen:
        raise SystemExit(f"duplicate (suite,id,seed): {key}")
    seen.add(key)
    if seed != 42 or row.get("rep") != 0:
        raise SystemExit(f"unexpected seed/rep: {key}")
    if row.get("arm") != expected_arm:
        raise SystemExit(f"unexpected arm: {row.get('arm')}")
    question = question_rows.get((suite, qid))
    if question is None:
        raise SystemExit(f"row absent from questions.json: {(suite, qid)}")
    if row.get("expected") != question.get("expected"):
        raise SystemExit(f"expected-answer drift: {(suite, qid)}")
    if row.get("request_error") != "":
        raise SystemExit(f"nonempty request_error: {(suite, qid)}")
    derived[suite]["n"] += 1
    derived[suite]["correct"] += int(row.get("correct") is True)
    derived[suite]["errors"] += int(row.get("empty_response") is True)

if {(suite, qid) for suite, qid, _ in seen} != set(question_rows):
    raise SystemExit("result suite/id set differs from questions.json")
for suite, expected in expected_counts.items():
    if derived[suite]["n"] != expected:
        raise SystemExit(f"per-suite row cardinality mismatch: {suite}")

result = json.loads(result_path.read_text(encoding="utf-8"))
meta = result.get("meta", {})
if meta.get("arm") != expected_arm:
    raise SystemExit("result meta arm is not exact")
if meta.get("kernel") != expected_kernel:
    raise SystemExit("result meta kernel is not exact")
if meta.get("binary") != expected_binary:
    raise SystemExit("result meta binary is not exact")
if (
    meta.get("seed") != 42
    or meta.get("repeats") != 1
    or meta.get("n_per_suite") != 200
    or meta.get("stratify") is not True
):
    raise SystemExit("result meta seed/repeats/n_per_suite/stratify are not exact")
if Path(meta.get("questions_pinned", "")).resolve(strict=True) != questions_path:
    raise SystemExit("result questions_pinned does not resolve to bound questions.json")

summaries = result.get("suites", [])
if len(summaries) != 2 or {row.get("suite") for row in summaries} != set(expected_counts):
    raise SystemExit("result suite set is not exact")
for summary in summaries:
    suite = summary["suite"]
    recomputed = derived[suite]
    expected_accuracy = recomputed["correct"] / recomputed["n"]
    if summary.get("n") != recomputed["n"]:
        raise SystemExit(f"summary n mismatch: {suite}")
    if summary.get("n_questions") != recomputed["n"] or summary.get("repeats") != 1:
        raise SystemExit(f"summary n_questions/repeats mismatch: {suite}")
    if summary.get("correct") != recomputed["correct"]:
        raise SystemExit(f"summary correct mismatch: {suite}")
    if summary.get("errors") != recomputed["errors"] or recomputed["errors"] != 0:
        raise SystemExit(f"summary error mismatch/nonzero errors: {suite}")
    if not math.isclose(float(summary.get("accuracy", -1)), expected_accuracy, rel_tol=0, abs_tol=1e-15):
        raise SystemExit(f"summary accuracy mismatch: {suite}")
PY
}

validate_corrected_lineup_evidence() {
    resolve_new_evidence
    require_tracked_at_head "$ROOT" "$SCRIPT_REL" 'FREEZE-V8 terminal validator'
    require_tracked_at_head "$ROOT" "$BOTH_SMOKE_REL" 'final both-mode smoke artifact'
    require_tracked_at_head "$ROOT" "$LIVE_API_REL" 'live API 6/6 evidence'
    require_sha "$BOTH_SMOKE" "$BOTH_SMOKE_SHA" 'final both-mode smoke artifact'
    require_sha "$LIVE_API" "$LIVE_API_SHA" 'live API 6/6 evidence'

    local quality_path quality_rel
    for quality_path in "$WORKER_BASELINE" "$WORKER_BASELINE_ROWS" "$WORKER_RESULT" "$WORKER_ROWS" "$WORKER_REPORT" \
        "$ARCH_BASELINE" "$ARCH_BASELINE_ROWS" "$ARCH_RESULT" "$ARCH_ROWS" "$ARCH_REPORT" "$QUESTIONS"; do
        require_regular "$quality_path" 'quality-gate artifact'
        quality_rel="${quality_path#"$RESEARCH/"}"
        require_tracked_at_head "$RESEARCH" "$quality_rel" "quality-gate artifact $quality_rel"
    done

    jq -s -e '
        length == 24 and all(.[]; .ok == true and .status_code == 200) and
        ([.[] | select(.kind == "chat")] | length) == 18 and
        ([.[] | select(.kind == "embedding")] | length) == 6 and
        ([.[].port] | sort) == [8070,8072,8080,8082,8083,8085,8086,8087,8090,8091,8092,8093,8094,8095,8180,8182,8185,8280,8282,8285,8380,8382,8385,8485] and
        all(.[] | select(.kind == "chat"); (.content | type == "string") and (.content | length) > 0) and
        all(.[] | select(.kind == "embedding"); (.dimension | type == "number") and .dimension > 0)
    ' "$BOTH_SMOKE" >/dev/null || fail 'both-mode smoke is not the exact 24/24 contract (18 chat + 6 embedding)'

    jq -e '
        .status == "ok" and .models_loaded == 6 and
        (.backend_probes | type == "object") and (.backend_probes | length) == 6 and
        all(.backend_probes[]; .ok == true and .status_code == 200) and
        ([.backend_probes[].url] | sort) == [
            "http://localhost:8070", "http://localhost:8072", "http://localhost:8083",
            "http://localhost:8085", "http://localhost:8086", "http://localhost:8087"
        ]
    ' "$LIVE_API" >/dev/null || fail 'live API evidence is not the exact healthy 6/6 backend set'

    jq -e '
        .meta.kernel == "production-consolidated-v8" and
        .meta.binary == "/mnt/raid0/llm/llama.cpp/build/bin/llama-server" and
        .meta.n_per_suite == 200 and .meta.seed == 42 and .meta.stratify == true and
        ([.suites[].suite] | sort) == ["gpqa", "mmlu_pro"] and
        all(.suites[]; .n >= 195 and .errors == 0)
    ' "$WORKER_RESULT" >/dev/null || fail 'worker MMLU-Pro/GPQA result contract failed'
    jq -e '
        .meta.kernel == "production-consolidated-v8" and
        .meta.binary == "/mnt/raid0/llm/llama.cpp/build/bin/llama-server" and
        .meta.n_per_suite == 200 and .meta.seed == 42 and .meta.stratify == true and
        ([.suites[].suite] | sort) == ["gpqa", "mmlu_pro"] and
        all(.suites[]; .n >= 195 and .errors == 0)
    ' "$ARCH_RESULT" >/dev/null || fail 'architect MMLU-Pro/GPQA result contract failed'
    jq -e '
        .meta.kernel == "production-consolidated-v7" and
        .meta.binary == "/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff/cpu-bin/llama-server" and
        .meta.n_per_suite == 200 and .meta.seed == 42 and .meta.stratify == true and
        ([.suites[].suite] | sort) == ["gpqa", "mmlu_pro"] and
        all(.suites[]; .n >= 195 and .errors == 0)
    ' "$WORKER_BASELINE" >/dev/null || fail 'worker v7 baseline contract failed'
    jq -e '
        .meta.kernel == "production-consolidated-v7" and
        .meta.binary == "/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff/cpu-bin/llama-server" and
        .meta.n_per_suite == 200 and .meta.seed == 42 and .meta.stratify == true and
        ([.suites[].suite] | sort) == ["gpqa", "mmlu_pro"] and
        all(.suites[]; .n >= 195 and .errors == 0)
    ' "$ARCH_BASELINE" >/dev/null || fail 'architect v7 baseline contract failed'
    jq -n -e --slurpfile baseline "$WORKER_BASELINE" --slurpfile candidate "$WORKER_RESULT" '
        ($baseline[0].suites | map({key:.suite, value:.}) | from_entries) as $base |
        ($candidate[0].suites | map({key:.suite, value:.}) | from_entries) as $cand |
        all(["mmlu_pro", "gpqa"][];
            . as $suite |
            $cand[$suite].n >= 195 and
            $cand[$suite].accuracy >= ($base[$suite].accuracy - 0.05))
    ' >/dev/null || fail 'worker structured quality comparison failed the 5pp gate'
    jq -n -e --slurpfile baseline "$ARCH_BASELINE" --slurpfile candidate "$ARCH_RESULT" '
        ($baseline[0].suites | map({key:.suite, value:.}) | from_entries) as $base |
        ($candidate[0].suites | map({key:.suite, value:.}) | from_entries) as $cand |
        all(["mmlu_pro", "gpqa"][];
            . as $suite |
            $cand[$suite].n >= 195 and
            $cand[$suite].accuracy >= ($base[$suite].accuracy - 0.05))
    ' >/dev/null || fail 'architect structured quality comparison failed the 5pp gate'
    jq -e '
        ([.suites | keys[]] | sort) == ["gpqa", "mmlu_pro"] and
        (.suites.gpqa | length) == 195 and (.suites.mmlu_pro | length) == 200
    ' "$QUESTIONS" >/dev/null || fail 'quality gate did not bind the exact shared 195 GPQA + 200 MMLU-Pro question set'
    validate_result_from_rows \
        "$WORKER_BASELINE" "$WORKER_BASELINE_ROWS" "v7-worker-general-baseline-full-18072" \
        "production-consolidated-v7" "/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff/cpu-bin/llama-server"
    validate_result_from_rows \
        "$ARCH_BASELINE" "$ARCH_BASELINE_ROWS" "v7-architect-general-baseline-full-18083" \
        "production-consolidated-v7" "/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff/cpu-bin/llama-server"
    validate_result_from_rows \
        "$WORKER_RESULT" "$WORKER_ROWS" "v8-production-worker-general-full-8072" \
        "production-consolidated-v8" "/mnt/raid0/llm/llama.cpp/build/bin/llama-server"
    validate_result_from_rows \
        "$ARCH_RESULT" "$ARCH_ROWS" "v8-production-architect-general-full-8083" \
        "production-consolidated-v8" "/mnt/raid0/llm/llama.cpp/build/bin/llama-server"
    rg -F '**Verdict**: PASS: all 2/2 suites within regression threshold (-5.0%).' "$WORKER_REPORT" >/dev/null ||
        fail 'worker quality report is not a 2/2 PASS at the reviewed threshold'
    rg -F '**Verdict**: PASS: all 2/2 suites within regression threshold (-5.0%).' "$ARCH_REPORT" >/dev/null ||
        fail 'architect quality report is not a 2/2 PASS at the reviewed threshold'
}

validate_output_lineup_bindings() {
    local selector=$1 expected_repo=$2 expected_path=$3 source=$4
    [[ "$(jq -r "$selector.repository // empty" "$OUTPUT")" == "$expected_repo" ]] ||
        fail "final output repository binding failed for $selector"
    [[ "$(jq -r "$selector.path // empty" "$OUTPUT")" == "$expected_path" ]] ||
        fail "final output path binding failed for $selector"
    [[ "$(jq -r "$selector.sha256 // empty" "$OUTPUT")" == "$(sha256 "$source")" ]] ||
        fail "final output SHA256 binding failed for $selector"
}

validate_all_output_lineup_bindings() {
    jq -e '
        .production_lineup_gate.quality_contract == {
            roles:["worker_general", "architect_general"],
            suites:["mmlu_pro", "gpqa"],
            requested_questions_per_suite:200,
            effective_questions:{mmlu_pro:200, gpqa:195},
            regression_threshold:0.05,
            zero_errors_required:true,
            worker_baseline_arm:"v7-worker-general-baseline-full-18072",
            architect_baseline_arm:"v7-architect-general-baseline-full-18083",
            baseline_kernel:"production-consolidated-v7",
            baseline_binary:"/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff/cpu-bin/llama-server",
            worker_arm:"v8-production-worker-general-full-8072",
            architect_arm:"v8-production-architect-general-full-8083",
            candidate_kernel:"production-consolidated-v8",
            candidate_binary:"/mnt/raid0/llm/llama.cpp/build/bin/llama-server",
            shared_question_identity:{
                seed:42, repeats:1, questions_artifact:"questions.json",
                baseline_and_candidate_rows_exact:true
            },
            status:"pass"
        } and
        (.production_lineup_gate.quality_artifacts | keys | sort) == [
            "architect_baseline", "architect_baseline_per_question", "architect_per_question",
            "architect_report", "architect_result", "questions", "worker_baseline",
            "worker_baseline_per_question", "worker_per_question", "worker_report", "worker_result"
        ]
    ' "$OUTPUT" >/dev/null || fail 'final output quality contract is not exact'
    validate_output_lineup_bindings '.production_lineup_gate.both_mode_smoke' epyc-root "$BOTH_SMOKE_REL" "$BOTH_SMOKE"
    validate_output_lineup_bindings '.production_lineup_gate.live_api_evidence' epyc-root "$LIVE_API_REL" "$LIVE_API"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.worker_baseline' epyc-inference-research "${WORKER_BASELINE#"$RESEARCH/"}" "$WORKER_BASELINE"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.worker_baseline_per_question' epyc-inference-research "${WORKER_BASELINE_ROWS#"$RESEARCH/"}" "$WORKER_BASELINE_ROWS"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.worker_result' epyc-inference-research "${WORKER_RESULT#"$RESEARCH/"}" "$WORKER_RESULT"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.worker_per_question' epyc-inference-research "${WORKER_ROWS#"$RESEARCH/"}" "$WORKER_ROWS"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.worker_report' epyc-inference-research "${WORKER_REPORT#"$RESEARCH/"}" "$WORKER_REPORT"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.architect_baseline' epyc-inference-research "${ARCH_BASELINE#"$RESEARCH/"}" "$ARCH_BASELINE"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.architect_baseline_per_question' epyc-inference-research "${ARCH_BASELINE_ROWS#"$RESEARCH/"}" "$ARCH_BASELINE_ROWS"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.architect_result' epyc-inference-research "${ARCH_RESULT#"$RESEARCH/"}" "$ARCH_RESULT"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.architect_per_question' epyc-inference-research "${ARCH_ROWS#"$RESEARCH/"}" "$ARCH_ROWS"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.architect_report' epyc-inference-research "${ARCH_REPORT#"$RESEARCH/"}" "$ARCH_REPORT"
    validate_output_lineup_bindings '.production_lineup_gate.quality_artifacts.questions' epyc-inference-research "${QUESTIONS#"$RESEARCH/"}" "$QUESTIONS"
}

print_terminal_lineup_manifest() {
    python3 - "$BOTH_SMOKE" "$LIVE_API" "$WORKER_BASELINE" "$WORKER_BASELINE_ROWS" \
        "$WORKER_RESULT" "$WORKER_ROWS" "$WORKER_REPORT" "$ARCH_BASELINE" "$ARCH_BASELINE_ROWS" \
        "$ARCH_RESULT" "$ARCH_ROWS" "$ARCH_REPORT" "$QUESTIONS" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

def binding(argument, repository, root):
    path = Path(argument).resolve(strict=True)
    root = Path(root).resolve(strict=True)
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {
        "repository": repository,
        "path": str(path.relative_to(root)),
        "sha256": digest,
    }

payload = {
    "schema": "epyc.v8_terminal_lineup_evidence.v1",
    "status": "pass",
    "mode": "both",
    "validator": binding(
        "/mnt/raid0/llm/epyc-root/artifacts/operator/freeze_v8_production_20260725.sh",
        "epyc-root",
        "/mnt/raid0/llm/epyc-root",
    ),
    "production_head": "67a433bf45a8a091d83b4ea0b32ff0735fd51800",
    "smoke_contract": {
        "total": 24,
        "chat": 18,
        "embedding": 6,
        "ports": [8070,8072,8080,8082,8083,8085,8086,8087,8090,8091,8092,8093,8094,8095,8180,8182,8185,8280,8282,8285,8380,8382,8385,8485],
        "artifact": binding(sys.argv[1], "epyc-root", "/mnt/raid0/llm/epyc-root"),
    },
    "live_api_contract": {
        "models_loaded": 6,
        "backend_probes": 6,
        "ports": [8070,8072,8083,8085,8086,8087],
        "artifact": binding(sys.argv[2], "epyc-root", "/mnt/raid0/llm/epyc-root"),
    },
    "quality_contract": {
        "roles": ["worker_general", "architect_general"],
        "suites": ["mmlu_pro", "gpqa"],
        "requested_questions_per_suite": 200,
        "effective_questions": {"mmlu_pro": 200, "gpqa": 195},
        "regression_threshold": 0.05,
        "zero_errors_required": True,
        "worker_baseline_arm": "v7-worker-general-baseline-full-18072",
        "architect_baseline_arm": "v7-architect-general-baseline-full-18083",
        "baseline_kernel": "production-consolidated-v7",
        "baseline_binary": "/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff/cpu-bin/llama-server",
        "worker_arm": "v8-production-worker-general-full-8072",
        "architect_arm": "v8-production-architect-general-full-8083",
        "candidate_kernel": "production-consolidated-v8",
        "candidate_binary": "/mnt/raid0/llm/llama.cpp/build/bin/llama-server",
        "shared_question_identity": {
            "seed": 42,
            "repeats": 1,
            "questions_artifact": "questions.json",
            "baseline_and_candidate_rows_exact": True,
        },
        "architect_cpu_q4_live_and_quality_tested": True,
        "b2_regression_omission_scope": "separate operator-directed campaign scope; not a deprecation premise",
        "artifacts": {
            "worker_baseline": binding(sys.argv[3], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "worker_baseline_per_question": binding(sys.argv[4], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "worker_result": binding(sys.argv[5], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "worker_per_question": binding(sys.argv[6], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "worker_report": binding(sys.argv[7], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "architect_baseline": binding(sys.argv[8], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "architect_baseline_per_question": binding(sys.argv[9], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "architect_result": binding(sys.argv[10], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "architect_per_question": binding(sys.argv[11], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "architect_report": binding(sys.argv[12], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
            "questions": binding(sys.argv[13], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
        },
    },
    "historical_quarter_smoke": "superseded provenance; not the terminal production-lineup contract",
}
print(json.dumps(payload, indent=2, sort_keys=True))
PY
}

validate_e8_terminal_lineup_binding() {
    local current attested
    current="$(print_terminal_lineup_manifest)" || fail 'could not render the current terminal-lineup manifest'
    attested="$(jq -S -c '.terminal_production_lineup // empty' "$E8")"
    [[ "$(jq -S -c . <<<"$current")" == "$attested" ]] ||
        fail 'E8 attestation does not bind the current terminal-lineup evidence'
}

validate_e8() {
    require_regular "$E8" 'E8 eligibility-fence attestation'
    require_regular "$E8_JOURNAL" 'E8 transaction journal'
    require_regular "$E8_PRE_ERAS" 'E8 era preimage'
    require_regular "$E8_PRE_STATE" 'E8 state preimage'
    require_regular "$E8_PRE_CARD" 'E8 card preimage'
    require_tracked_clean "$ROOT" artifacts/operator/ratify_v8_era_fence_20260725.sh "$(jq -r '.artifacts.operator_script_sha256 // empty' "$E8")"
    jq -e --arg head "$EXPECTED_HEAD" --arg cpu "$EXPECTED_CPU_SHA" --arg hip "$EXPECTED_HIP_SHA" '
        .schema == "epyc.operator_v8_era_fence_attestation.v2" and
        .decision == "RATIFY-V8-ERA-FENCE" and .scope == "eligibility_fence_only" and
        .production_frozen == false and .separate_freeze_required == true and
        .production_branch == "production-consolidated-v8" and .production_head == $head and
        .production_binary_sha256.cpu == $cpu and .production_binary_sha256.hip == $hip and
        .cutover_boundary == "2026-07-25T18:38:43Z" and
        .active_instrument_eras == {cpu_bench:"E8-cpu-kernel", autopilot_speed:"E8-autopilot-speed"} and
        .frontier_rerun_required == {required:true, min_numeric_trials:16} and
        .q8_claim == "none; campaign-scoped WAIVE-Q8 remains binding" and
        (.required_next_action | contains("separate production freeze transaction"))
    ' "$E8" >/dev/null || fail 'E8 attestation does not state the exact eligibility-only posture'
    jq -e --arg e8_sha "$(sha256 "$E8")" '
        .schema == "epyc.v8_era_fence_transaction.v1" and .scope == "eligibility_fence_only" and
        .production_frozen == false and .phase == "complete" and .output_sha256 == $e8_sha
    ' "$E8_JOURNAL" >/dev/null || fail 'E8 transaction journal is not complete and bound to its output'
    require_sha "$E8_PRE_ERAS" "$(jq -r '.preimages.instrument_eras_sha256 // empty' "$E8_JOURNAL")" 'E8 era preimage'
    require_sha "$E8_PRE_STATE" "$(jq -r '.preimages.autopilot_state_sha256 // empty' "$E8_JOURNAL")" 'E8 state preimage'
    require_sha "$E8_PRE_CARD" "$(jq -r '.preimages.system_card_sha256 // empty' "$E8_JOURNAL")" 'E8 card preimage'
    require_sha "$ERAS" "$(jq -r '.artifacts.instrument_eras_sha256' "$E8")" 'E8-attested era registry'
    require_sha "$STATE" "$(jq -r '.artifacts.autopilot_state_sha256' "$E8")" 'E8-attested AutoPilot state'
    require_sha "$CARD" "$(jq -r '.artifacts.system_card_sha256' "$E8")" 'E8-attested system card'

    "$ORCH/.venv/bin/python" - "$E8_PRE_ERAS" "$E8_PRE_STATE" "$ERAS" "$STATE" "$CARD" "$PROMOTION_AT" "$PROMOTION_EPOCH" <<'PY'
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sys
import yaml

pre_eras, pre_state, eras, state, card = map(Path, sys.argv[1:6])
boundary, epoch = sys.argv[6], float(sys.argv[7])
if datetime.fromisoformat(boundary.replace("Z", "+00:00")).timestamp() != epoch:
    raise SystemExit("E8 boundary and epoch diverge")
before = yaml.safe_load(pre_eras.read_text(encoding="utf-8"))
after = yaml.safe_load(eras.read_text(encoding="utf-8"))
if after["eras"][:-2] != before["eras"] or len(after["eras"]) != len(before["eras"]) + 2:
    raise SystemExit("E8 altered historical era rows")
cpu, speed = after["eras"][-2:]
if (cpu.get("id"), cpu.get("from"), cpu.get("scope")) != ("E8-cpu-kernel", boundary, "cpu_bench"):
    raise SystemExit("E8 CPU era is not exact")
if (speed.get("id"), speed.get("from"), speed.get("scope")) != ("E8-autopilot-speed", boundary, "autopilot_speed"):
    raise SystemExit("E8 speed era is not exact")
for required in ("production-consolidated-v8", "67a433bf45a8a091d83b4ea0b32ff0735fd51800", "WAIVE-Q8", "no Q8 performance or non-regression claim"):
    if required not in str(cpu.get("note", "")):
        raise SystemExit(f"E8 CPU era note lacks {required}")
if after.get("known_dead_instrument_items") != before.get("known_dead_instrument_items"):
    raise SystemExit("E8 altered known-dead items")
before_state = json.loads(pre_state.read_text(encoding="utf-8"))
expected = deepcopy(before_state)
previous = deepcopy(before_state["frontier_rerun_required"])
expected["active_instrument_eras"] = {"autopilot_speed": "E8-autopilot-speed", "cpu_bench": "E8-cpu-kernel"}
expected["pareto_epoch_ts"] = epoch
expected["pareto_exclude_before_ts"] = epoch
expected["frontier_rerun_required"] = {
    "completed_numeric_trials": 0,
    "min_numeric_trials": 16,
    "minimum_action": "Run at least 16 completed current-marker numeric_trial rows under active_instrument_eras.autopilot_speed=E8-autopilot-speed, then rebuild/inspect the v8-only frontier before clearing this marker.",
    "opened_at": boundary,
    "previous_marker": previous,
    "reason": "E8-autopilot-speed production-consolidated-v8 era opened; rerun/rebuild a v8-only AutoPilot Pareto frontier before using speed maxima or consolidated max-performance guidance.",
    "required": True,
    "rerun_started_at": boundary,
}
if json.loads(state.read_text(encoding="utf-8")) != expected:
    raise SystemExit("AutoPilot state differs from the exact E8 transformation")
text = card.read_text(encoding="utf-8")
if "active_instrument_eras: autopilot_speed=E8-autopilot-speed, cpu_bench=E8-cpu-kernel" not in text:
    raise SystemExit("system card does not expose exact E8 eras")
if "frontier_rerun_required: true" not in text or "production-consolidated-v8" not in text:
    raise SystemExit("system card does not expose fail-closed v8 frontier marker")
PY
}

capture_preprompt_inputs() {
    preprompt_script_sha="$(sha256 "$SCRIPT_PATH")"
    preprompt_e8_sha="$(sha256 "$E8")"
    preprompt_journal_sha="$(sha256 "$E8_JOURNAL")"
    preprompt_eras_sha="$(sha256 "$ERAS")"
    preprompt_state_sha="$(sha256 "$STATE")"
    preprompt_card_sha="$(sha256 "$CARD")"
    preprompt_both_smoke_sha="$(sha256 "$BOTH_SMOKE")"
    preprompt_live_api_sha="$(sha256 "$LIVE_API")"
    preprompt_quality_manifest="$(quality_manifest)"
}

require_same_preprompt_inputs() {
    [[ "$(sha256 "$SCRIPT_PATH")" == "$preprompt_script_sha" ]] ||
        fail 'freeze script changed while awaiting operator confirmation'
    [[ "$(sha256 "$E8")" == "$preprompt_e8_sha" ]] ||
        fail 'E8 attestation changed while awaiting operator confirmation'
    [[ "$(sha256 "$E8_JOURNAL")" == "$preprompt_journal_sha" ]] ||
        fail 'E8 transaction journal changed while awaiting operator confirmation'
    [[ "$(sha256 "$ERAS")" == "$preprompt_eras_sha" ]] ||
        fail 'instrument era registry changed while awaiting operator confirmation'
    [[ "$(sha256 "$STATE")" == "$preprompt_state_sha" ]] ||
        fail 'AutoPilot state changed while awaiting operator confirmation'
    [[ "$(sha256 "$CARD")" == "$preprompt_card_sha" ]] ||
        fail 'system card changed while awaiting operator confirmation'
    [[ "$(sha256 "$BOTH_SMOKE")" == "$preprompt_both_smoke_sha" ]] ||
        fail 'both-mode smoke changed while awaiting operator confirmation'
    [[ "$(sha256 "$LIVE_API")" == "$preprompt_live_api_sha" ]] ||
        fail 'live API evidence changed while awaiting operator confirmation'
    [[ "$(quality_manifest)" == "$preprompt_quality_manifest" ]] ||
        fail 'quality-gate evidence changed while awaiting operator confirmation'
}

write_journal_to() {
    local target=$1
    local temp="$target/.journal.json.tmp"
    python3 - "$temp" "$phase" "$output_sha" <<'PY'
import json
import os
from pathlib import Path
import sys

path = Path(sys.argv[1])
payload = {
    "schema": "epyc.v8_final_freeze_transaction.v1",
    "scope": "mechanical_post_e8_freeze",
    "production_frozen": sys.argv[2] == "complete",
    "phase": sys.argv[2],
    "cutover_boundary": "2026-07-25T18:38:43Z",
    "output_sha256": sys.argv[3] or None,
    "preimages": "immutable attestation inputs copied beneath preimages/",
}
with path.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())
os.replace(path, path.parent / "journal.json")
fd = os.open(path.parent, os.O_RDONLY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
PY
}

write_journal() { write_journal_to "$TXN_DIR"; }

archive_transaction() {
    local label=$1 stamp dest
    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    dest="$TXN_DIR.$label-$stamp"
    [[ ! -e "$dest" ]] || return 1
    mv -- "$TXN_DIR" "$dest" || return 1
    sync -f "$(dirname "$TXN_DIR")" || return 1
    printf 'Retained transaction at: %s\n' "$dest"
}

rollback_output() {
    local ok=1
    set +e
    if [[ -e "$OUTPUT" ]]; then
        [[ ! -e "$INTERRUPTED_OUTPUT" ]] || ok=0
        mv -- "$OUTPUT" "$INTERRUPTED_OUTPUT" || ok=0
        sync -f "$INTERRUPTED_OUTPUT" || ok=0
        sync -f "$(dirname "$OUTPUT")" || ok=0
    fi
    if (( ok )); then
        phase=rolled_back
        output_sha=''
        write_journal || ok=0
    else
        phase=rollback_incomplete
        write_journal || true
    fi
    set -e
    return "$((1 - ok))"
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM HUP
    if (( transaction_active )); then
        if [[ "$phase" == complete && -f "$OUTPUT" && "$output_sha" =~ ^[0-9a-f]{64}$ &&
              "$(sha256 "$OUTPUT")" == "$output_sha" &&
              "$(jq -r '.phase' "$JOURNAL" 2>/dev/null)" == complete ]]; then
            exit "$rc"
        fi
        if ! rollback_output || ! archive_transaction rolled-back; then
            printf 'ROLLBACK INCOMPLETE: inspect %s and its durable snapshots.\n' "$JOURNAL" >&2
            exit 2
        fi
    fi
    exit "$rc"
}

snapshot_inputs() {
    mkdir -p "$SNAPSHOT_DIR"
    local path
    for path in "$E8" "$E8_JOURNAL" "$E8_PRE_ERAS" "$E8_PRE_STATE" "$E8_PRE_CARD" \
        "$CUTOVER" "$QUARTER" "$QUARTER_ROWS" "$QUARTER_GATE" "$WAIVE" "$PROVISIONAL" \
        "$CPU_SUMMARY" "$PGPU_SUMMARY" "$PGPU_AUDIT" "$PGPU_PROV" "$ERAS" "$STATE" "$CARD" \
        "$BOTH_SMOKE" "$LIVE_API" "$WORKER_BASELINE" "$WORKER_BASELINE_ROWS" "$WORKER_RESULT" \
        "$WORKER_ROWS" "$WORKER_REPORT" "$ARCH_BASELINE" "$ARCH_BASELINE_ROWS" "$ARCH_RESULT" \
        "$ARCH_ROWS" "$ARCH_REPORT" "$QUESTIONS"; do
        install -m 0644 "$path" "$SNAPSHOT_DIR/$(sha256 "$path").$(basename "$path")"
        sync -f "$SNAPSHOT_DIR/$(sha256 "$path").$(basename "$path")"
    done
    sync -f "$SNAPSHOT_DIR"
}

validate_snapshot() {
    local required=(
        "$CUTOVER_SHA" "$QUARTER_SHA" "$QUARTER_ROWS_SHA" "$QUARTER_GATE_SHA" "$WAIVE_SHA"
        "$PROVISIONAL_SHA" "$CPU_SHA" "$PGPU_SHA" "$PGPU_AUDIT_SHA" "$PGPU_PROV_SHA"
        "$(sha256 "$E8")" "$(sha256 "$E8_JOURNAL")" "$(sha256 "$E8_PRE_ERAS")"
        "$(sha256 "$E8_PRE_STATE")" "$(sha256 "$E8_PRE_CARD")" "$(sha256 "$ERAS")"
        "$(sha256 "$STATE")" "$(sha256 "$CARD")" "$BOTH_SMOKE_SHA" "$LIVE_API_SHA"
        "$(sha256 "$WORKER_BASELINE")" "$(sha256 "$WORKER_BASELINE_ROWS")" "$(sha256 "$WORKER_RESULT")"
        "$(sha256 "$WORKER_ROWS")" "$(sha256 "$WORKER_REPORT")" "$(sha256 "$ARCH_BASELINE")"
        "$(sha256 "$ARCH_BASELINE_ROWS")" "$(sha256 "$ARCH_RESULT")" "$(sha256 "$ARCH_ROWS")"
        "$(sha256 "$ARCH_REPORT")" "$(sha256 "$QUESTIONS")"
    )
    local digest
    for digest in "${required[@]}"; do
        compgen -G "$SNAPSHOT_DIR/$digest.*" >/dev/null || fail "snapshot missing digest $digest"
    done
}

write_output() {
    local now script_sha e8_sha eras_sha state_sha card_sha tmp
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    script_sha="$(sha256 "$SCRIPT_PATH")"
    e8_sha="$(sha256 "$E8")"
    eras_sha="$(sha256 "$ERAS")"
    state_sha="$(sha256 "$STATE")"
    card_sha="$(sha256 "$CARD")"
    tmp="$ROOT/artifacts/operator/.ratify_v8_final_freeze_20260725.json.tmp"
    python3 - "$tmp" "$now" "$script_sha" "$e8_sha" "$(sha256 "$E8_JOURNAL")" "$eras_sha" "$state_sha" "$card_sha" \
        "$(git -C "$ROOT" rev-parse HEAD)" "$(git -C "$ORCH" rev-parse HEAD)" "$(git -C "$RESEARCH" rev-parse HEAD)" \
        "$BOTH_SMOKE" "$LIVE_API" "$WORKER_BASELINE" "$WORKER_BASELINE_ROWS" "$WORKER_RESULT" \
        "$WORKER_ROWS" "$WORKER_REPORT" "$ARCH_BASELINE" "$ARCH_BASELINE_ROWS" "$ARCH_RESULT" \
        "$ARCH_ROWS" "$ARCH_REPORT" "$QUESTIONS" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import sys

out = Path(sys.argv[1])

def binding(argument, repository, root):
    path = Path(argument).resolve(strict=True)
    root = Path(root).resolve(strict=True)
    relative = path.relative_to(root)
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {
        "repository": repository,
        "path": str(relative),
        "absolute_path": str(path),
        "sha256": digest,
    }

both_smoke = binding(sys.argv[12], "epyc-root", "/mnt/raid0/llm/epyc-root")
live_api = binding(sys.argv[13], "epyc-root", "/mnt/raid0/llm/epyc-root")
quality_bindings = {
    "worker_baseline": binding(sys.argv[14], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "worker_baseline_per_question": binding(sys.argv[15], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "worker_result": binding(sys.argv[16], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "worker_per_question": binding(sys.argv[17], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "worker_report": binding(sys.argv[18], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "architect_baseline": binding(sys.argv[19], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "architect_baseline_per_question": binding(sys.argv[20], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "architect_result": binding(sys.argv[21], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "architect_per_question": binding(sys.argv[22], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "architect_report": binding(sys.argv[23], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
    "questions": binding(sys.argv[24], "epyc-inference-research", "/mnt/raid0/llm/epyc-inference-research"),
}
payload = {
    "schema": "epyc.operator_v8_final_freeze_attestation.v1",
    "decision": "FREEZE-V8",
    "status": "production_promoted_frozen",
    "scope": "mechanical_post_e8_freeze",
    "production_frozen": True,
    "ratified_at": sys.argv[2],
    "frozen_at": sys.argv[2],
    "production_branch": "production-consolidated-v8",
    "production_head": "67a433bf45a8a091d83b4ea0b32ff0735fd51800",
    "production_version": "10107 (67a433bf4)",
    "production_version_number": 10107,
    "production_binary_sha256": {
        "cpu": "a4b667163022aa166ade7c0e00fa4e775b37662e02c10da7642c8c23a4d6b414",
        "hip": "112c560f1c978c584a9899539851348a0ce1e05cde458061c281758aff066882",
    },
    "rollback": {
        "branch": "production-consolidated-v7",
        "head": "6ad45fa3ff6718c07c000061dbc6e29c1771f6e3",
    },
    "cutover_boundary": "2026-07-25T18:38:43Z",
    "e8_eligibility_fence": {
        "decision": "RATIFY-V8-ERA-FENCE",
        "scope": "eligibility_fence_only",
        "production_frozen_before_this_transaction": False,
        "separate_freeze_required": True,
        "attestation_path": "artifacts/operator/ratify_v8_era_fence_20260725.json",
        "attestation_sha256": sys.argv[4],
        "transaction_journal_path": "artifacts/operator/v8-era-fence-transaction-20260725T183843Z/journal.json",
        "transaction_journal_sha256": sys.argv[5],
        "active_instrument_eras": {"cpu_bench": "E8-cpu-kernel", "autopilot_speed": "E8-autopilot-speed"},
        "frontier_rerun_required": {"required": True, "min_numeric_trials": 16},
    },
    "promotion_decision": False,
    "promotion_decision_interpretation": (
        "The CPU campaign's promotion_decision=false is preserved as a non-automatic "
        "matrix verdict; this final freeze is an operator-attested release decision."
    ),
    "q8_claim": "none; campaign-scoped WAIVE-Q8 remains binding and v8 makes no Q8 non-regression claim",
    "production_lineup_gate": {
        "mode": "both",
        "status": "pass",
        "smoke_contract": {"total": 24, "chat": 18, "embedding": 6},
        "both_mode_smoke": both_smoke,
        "live_api_contract": {"models_loaded": 6, "backend_probes": 6, "all_ok": True},
        "live_api_evidence": live_api,
        "quality_contract": {
            "roles": ["worker_general", "architect_general"],
            "suites": ["mmlu_pro", "gpqa"],
            "requested_questions_per_suite": 200,
            "effective_questions": {"mmlu_pro": 200, "gpqa": 195},
            "regression_threshold": 0.05,
            "zero_errors_required": True,
            "worker_baseline_arm": "v7-worker-general-baseline-full-18072",
            "architect_baseline_arm": "v7-architect-general-baseline-full-18083",
            "baseline_kernel": "production-consolidated-v7",
            "baseline_binary": "/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff/cpu-bin/llama-server",
            "worker_arm": "v8-production-worker-general-full-8072",
            "architect_arm": "v8-production-architect-general-full-8083",
            "candidate_kernel": "production-consolidated-v8",
            "candidate_binary": "/mnt/raid0/llm/llama.cpp/build/bin/llama-server",
            "shared_question_identity": {
                "seed": 42,
                "repeats": 1,
                "questions_artifact": "questions.json",
                "baseline_and_candidate_rows_exact": True,
            },
            "status": "pass",
        },
        "quality_artifacts": quality_bindings,
    },
    "laguna_dflash": {
        "iq2_gpu_tested": True,
        "q4_cpu_tested": True,
        "lineup_disposition": "no-go; provisional fail-closed screen only",
    },
    "immutable_provisional_attestation": {
        "path": "handoffs/active/laguna-pgpu1-v8-promotion-attestation.json",
        "sha256": "54daa05c3c0540a65fda3cb008fd1ec6e89a9c2a169ced0b2af81bf12783bc5d",
    },
    "evidence_sha256": {
        "cutover_journal": "e2c3b9f67072798eafcb945004c2faed59a04e048ce7e1510a98611d82330991",
        "quarter_stack_summary": "e25feaadba51d8d75736b31932ea088f8f2a0a7fafbd29d63f80c66a799c54f4",
        "quarter_stack_rows": "808207961490e5d2df9a24e79e3d53ee617ccfec3e69a2229e2656f2b54fa639",
        "quarter_promotion_gate": "9d37c9fc6b90889a2b68cbf99bd7d6417508eb9c0ed93b25147f8c36f526de4b",
        "waive_q8": "fcd52b61610fcc2782e11f41ffac359343233924805f83d872eeceffbb7522d7",
        "provisional_laguna_attestation": "54daa05c3c0540a65fda3cb008fd1ec6e89a9c2a169ced0b2af81bf12783bc5d",
        "cpu_matrix": "fb0b8db8bcf1f8aea34cbf1ca7231df36b223ebd7556df61f98d8a471176943a",
        "pgpu_summary": "73c28e4b86a38732c7fa99f3210e31f53efcced6420b8e81607007690621059e",
        "pgpu_completeness_audit": "c9410dc7124232c8652f5ccec17e3bea3e9d5c6a0a77d537a0b70ea8689c74e9",
        "pgpu_audit_provenance": "c8d06d81f9dddb5df130f48bff1d0a3918576ba0f8ec9a0137041322598555ca",
    },
    "artifacts": {
        "operator_script_sha256": sys.argv[3],
        "e8_attestation_sha256": sys.argv[4],
        "e8_transaction_journal_sha256": sys.argv[5],
        "instrument_eras_sha256": sys.argv[6],
        "autopilot_state_sha256": sys.argv[7],
        "system_card_sha256": sys.argv[8],
        "transaction_journal": "artifacts/operator/v8-final-freeze-transaction-20260725T183843Z/journal.json",
    },
    "repository_heads": {"epyc_root": sys.argv[9], "epyc_orchestrator": sys.argv[10], "epyc_inference_research": sys.argv[11]},
}
with out.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())
PY
    mv -- "$tmp" "$OUTPUT"
    sync -f "$OUTPUT"
    sync -f "$(dirname "$OUTPUT")"
}

idempotent_complete() {
    [[ -f "$JOURNAL" && -f "$OUTPUT" ]] || return 1
    [[ "$(jq -r '.phase' "$JOURNAL" 2>/dev/null)" == complete ]] || return 1
    [[ "$(jq -r '.production_frozen' "$JOURNAL" 2>/dev/null)" == true ]] ||
        fail 'completed freeze journal does not declare production frozen'
    local recorded
    recorded="$(jq -r '.output_sha256 // empty' "$JOURNAL")"
    [[ "$recorded" =~ ^[0-9a-f]{64}$ ]] || fail 'completed freeze journal has no output digest'
    require_sha "$OUTPUT" "$recorded" 'completed final-freeze attestation'
    jq -e --arg head "$EXPECTED_HEAD" '
        .schema == "epyc.operator_v8_final_freeze_attestation.v1" and .decision == "FREEZE-V8" and
        .status == "production_promoted_frozen" and .production_frozen == true and
        .production_branch == "production-consolidated-v8" and .production_head == $head and
        .frozen_at == .ratified_at and .promotion_decision == false and (.q8_claim | startswith("none;")) and
        .immutable_provisional_attestation.path == "handoffs/active/laguna-pgpu1-v8-promotion-attestation.json" and
        .immutable_provisional_attestation.sha256 == "54daa05c3c0540a65fda3cb008fd1ec6e89a9c2a169ced0b2af81bf12783bc5d" and
        .e8_eligibility_fence.attestation_path == "artifacts/operator/ratify_v8_era_fence_20260725.json" and
        .e8_eligibility_fence.transaction_journal_path == "artifacts/operator/v8-era-fence-transaction-20260725T183843Z/journal.json" and
        .production_lineup_gate.mode == "both" and .production_lineup_gate.status == "pass" and
        .production_lineup_gate.smoke_contract == {total:24, chat:18, embedding:6} and
        .production_lineup_gate.both_mode_smoke.path == "artifacts/operator/v8-both-smoke-20260725T202558Z/both_stack_smoke.jsonl" and
        .production_lineup_gate.live_api_evidence.path == "artifacts/operator/v8-both-smoke-20260725T202558Z/api_health_6of6.json" and
        .production_lineup_gate.live_api_contract == {models_loaded:6, backend_probes:6, all_ok:true} and
        .production_lineup_gate.quality_contract.status == "pass"
    ' "$OUTPUT" >/dev/null || fail 'completed final-freeze output has an unsafe posture'
    validate_production
    validate_e8
    validate_evidence
    validate_corrected_lineup_evidence
    validate_e8_terminal_lineup_binding
    validate_all_output_lineup_bindings
    [[ "$(sha256 "$E8")" == "$(jq -r '.e8_eligibility_fence.attestation_sha256' "$OUTPUT")" ]] ||
        fail 'completed output no longer matches the E8 attestation'
    [[ "$(sha256 "$E8_JOURNAL")" == "$(jq -r '.e8_eligibility_fence.transaction_journal_sha256' "$OUTPUT")" ]] ||
        fail 'completed output no longer matches the E8 transaction journal'
    capture_preprompt_inputs
    printf 'v8 final freeze is already attested and digest-valid: %s\n' "$OUTPUT"
}

recover_transaction() {
    [[ -d "$TXN_DIR" ]] || fail 'no final-freeze transaction exists to recover'
    [[ -t 0 && -t 1 ]] || fail 'recovery requires an interactive terminal'
    [[ "$(jq -r '.phase // empty' "$JOURNAL" 2>/dev/null)" != complete ]] || {
        idempotent_complete
        return
    }
    printf '%s\n' \
        "Recovery will retain any partial final-freeze output under $TXN_DIR and archive the transaction." \
        'Type RECOVER-FREEZE-V8 to continue.'
    local token
    read -r -p '> ' token
    [[ "$token" == RECOVER-FREEZE-V8 ]] || fail 'recovery aborted'
    exec 7>>"$LOCK"
    flock -n 7 || fail 'another final-freeze transaction holds the operator lock'
    rollback_output || fail 'could not quarantine partial final-freeze output'
    archive_transaction recovered || fail 'could not archive recovered transaction'
}

main() {
    local command token attest_token=''
    for command in git jq sha256sum timeout python3 flock install sync mktemp rg realpath sed wc awk head; do
        command -v "$command" >/dev/null || fail "missing required command: $command"
    done
    [[ -x "$ORCH/.venv/bin/python" ]] || fail 'orchestrator venv Python is missing'
    case ${1:-} in
        --recover) recover_transaction; return ;;
        --status)
            if [[ -f "$JOURNAL" ]]; then jq . "$JOURNAL"; else printf 'No v8 final-freeze transaction exists.\n'; fi
            return ;;
        --validate-only)
            validate_production
            validate_e8
            validate_evidence
            validate_corrected_lineup_evidence
            validate_e8_terminal_lineup_binding
            printf 'Read-only FREEZE-V8 validation passed; no files changed.\n'
            return
            ;;
        --validate-terminal-lineup-only)
            validate_production
            validate_corrected_lineup_evidence
            printf 'Read-only terminal-lineup validation passed; no files changed.\n'
            return
            ;;
        --terminal-lineup-manifest)
            require_tracked_clean "$ROOT" "$SCRIPT_REL" "$(sha256 "$SCRIPT_PATH")"
            validate_production
            validate_corrected_lineup_evidence
            print_terminal_lineup_manifest
            return
            ;;
        --attest)
            [[ $# -eq 2 ]] || fail "usage: $0 --attest FREEZE-V8"
            [[ -n "$2" ]] || fail "operator attestation token must not be empty"
            attest_token=$2
            ;;
        '')
            [[ $# -eq 0 ]] ||
                fail "usage: $0 [--status|--recover|--validate-only|--validate-terminal-lineup-only|--terminal-lineup-manifest|--attest FREEZE-V8]"
            ;;
        *) fail "usage: $0 [--status|--recover|--validate-only|--validate-terminal-lineup-only|--terminal-lineup-manifest|--attest FREEZE-V8]" ;;
    esac
    [[ ! -e "$PREP_DIR" ]] || fail "interrupted preparation exists at $PREP_DIR; inspect before retrying"
    if [[ -e "$TXN_DIR" || -e "$OUTPUT" ]]; then
        idempotent_complete && return
        fail 'partial or conflicting final-freeze transaction exists; inspect --status or use --recover'
    fi
    require_tracked_clean "$ROOT" "$SCRIPT_REL" "$(sha256 "$SCRIPT_PATH")"
    validate_production
    validate_e8
    validate_evidence
    validate_corrected_lineup_evidence
    validate_e8_terminal_lineup_binding
    capture_preprompt_inputs
    [[ -t 0 && -t 1 ]] || fail 'operator final freeze requires an interactive terminal'
    printf '%s\n' \
        'This performs the separate, mechanical post-E8 FREEZE-V8 transaction.' \
        'It does not alter production binaries, the E8 era registry, AutoPilot state, or the system card.' \
        'It records production-consolidated-v8 at 67a433bf45a8a091d83b4ea0b32ff0735fd51800 as frozen.' \
        'It binds the corrected both-mode lineup: 24/24 endpoints, live API 6/6, and worker+architect MMLU-Pro/GPQA gates.' \
        'The CPU matrix promotion_decision=false is preserved; this is not an automatic matrix promotion.' \
        'WAIVE-Q8 remains binding; no Q8 non-regression claim is made.' \
        'Type FREEZE-V8 to attest this final release decision; anything else aborts.'
    if [[ -n "$attest_token" ]]; then
        token=$attest_token
        printf '> %s\n' "$token"
    else
        read -r -p '> ' token
    fi
    [[ "$token" == FREEZE-V8 ]] || { printf 'Aborted; no files changed.\n'; return 1; }

    exec 7>>"$LOCK"
    flock -n 7 || fail 'another final-freeze transaction holds the operator lock'
    validate_production
    validate_e8
    validate_evidence
    validate_corrected_lineup_evidence
    validate_e8_terminal_lineup_binding
    require_same_preprompt_inputs
    require_tracked_clean "$ROOT" "$SCRIPT_REL" "$preprompt_script_sha"
    mkdir "$PREP_DIR"
    phase=prepared
    snapshot_inputs
    write_journal_to "$PREP_DIR"
    mv -- "$PREP_DIR" "$TXN_DIR"
    sync -f "$(dirname "$TXN_DIR")"
    transaction_active=1
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM HUP
    validate_snapshot
    phase=snapshots_validated
    write_journal
    validate_production
    validate_e8
    validate_evidence
    validate_corrected_lineup_evidence
    validate_e8_terminal_lineup_binding
    write_output
    output_sha="$(sha256 "$OUTPUT")"
    phase=output_written
    write_journal
    jq -e --arg head "$EXPECTED_HEAD" '
        .schema == "epyc.operator_v8_final_freeze_attestation.v1" and .decision == "FREEZE-V8" and
        .status == "production_promoted_frozen" and .production_frozen == true and
        .production_head == $head and .promotion_decision == false and
        .q8_claim == "none; campaign-scoped WAIVE-Q8 remains binding and v8 makes no Q8 non-regression claim" and
        .production_lineup_gate.mode == "both" and .production_lineup_gate.status == "pass" and
        .production_lineup_gate.smoke_contract == {total:24, chat:18, embedding:6} and
        .production_lineup_gate.live_api_contract == {models_loaded:6, backend_probes:6, all_ok:true} and
        .production_lineup_gate.quality_contract.status == "pass"
    ' "$OUTPUT" >/dev/null || fail 'new final-freeze attestation did not preserve the required caveats'
    [[ "$(sha256 "$E8")" == "$(jq -r '.artifacts.e8_attestation_sha256' "$OUTPUT")" ]] ||
        fail 'new final-freeze output lost its E8 binding'
    [[ "$(sha256 "$E8_JOURNAL")" == "$(jq -r '.artifacts.e8_transaction_journal_sha256' "$OUTPUT")" ]] ||
        fail 'new final-freeze output lost its E8 transaction-journal binding'
    validate_all_output_lineup_bindings
    validate_production
    validate_e8
    validate_evidence
    validate_corrected_lineup_evidence
    validate_e8_terminal_lineup_binding
    [[ "$(sha256 "$OUTPUT")" == "$output_sha" ]] || fail 'final-freeze attestation changed before completion'
    phase=complete
    write_journal
    transaction_active=0
    trap - EXIT INT TERM HUP
    printf '\nFinal v8 freeze attestation created:\n%s\n' "$OUTPUT"
    sha256sum "$OUTPUT"
}

main "$@"
