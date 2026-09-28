#!/bin/bash
# Operator signature for the ARCHSWAP-20260927 stack-change package: swap the architect
# role labels (Qwen3.8-Flash-Next :8074 -> architect_general, Qwen3.8-27B :8083 ->
# architect_critic). See PACKAGE.md in this directory.
#
# What it does: verifies PACKAGE.md, the patches, the tools and the evidence against the
# sha256 values pinned below; verifies every lane commit is on its origin lane; verifies
# that NOTHING this package touches has moved on origin/main since the lanes were cut
# (otherwise the package must be REFRESHED by its preparer, never reconciled at signing);
# records the operator's choice for the two open decisions; writes ONE receipt.
#
# What it does NOT do: apply a patch, merge a branch, compile, start, stop or reload
# anything. Phases 7-8 (PACKAGE.md section 7) are run afterwards, and begin by checking
# this receipt.
#
# GOVERNANCE: the signer must be named. RATIFY_OPERATOR must be set to a real name and
# must not be a default/placeholder value; this script refuses otherwise. Signing from a
# terminal:   RATIFY_OPERATOR="<your name>" ./ratify_archswap_20260927.sh --attest <TOKEN>
# Recording chat consent (a session acting on the operator's explicit chat approval):
#   RATIFY_OPERATOR="<name>" RATIFY_CONSENT_REF="<chat/session reference>" ... --attest <TOKEN>
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-ARCHSWAP-20260927"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
ROOTREPO="/workspace"
PYTHON="/usr/bin/python3"

# repo|lane|base|commits  (base = origin/main the lane was cut from; every commit must be
# an ancestor of origin/<lane>)
LANES=(
  "$RESEARCH|lane/archswap-20260927|86a33a54c150ca5f417376ff70be8b790068d06a|61af24fa"
  "$ORCH|lane/archswap-20260927|280059ccc2fc733ac6e9f286a46f0aae098f17f8|48a012c3 b0d3317e 28cbe113 667c78d4 c81f6b60 9d3eae6c e08ec06d"
  "$ROOTREPO|lane/archswap-20260927|e8abf01d0631c7e8408b14410d4dd0a98be2ecc2|3acce399"
)

# repo|path ...  — every path this package's patches touch. If ANY of them differs
# between the lane base and current origin/main, the package is stale.
TOUCHED=(
  "$RESEARCH|orchestration/model_registry.yaml"
  "$RESEARCH|scripts/benchmark/prb_t4_tale_gpu.py"
  "$RESEARCH|scripts/benchmark/review_f1/ev13b_run.py"
  "$RESEARCH|scripts/kernel_rnd/autokernel/loop/run.py"
  "$ORCH|.env.example"
  "$ORCH|README.md"
  "$ORCH|docs/chapters/02-orchestration-architecture.md"
  "$ORCH|docs/generated/current_stack_summary.md"
  "$ORCH|docs/gpu-shadow-lane.md"
  "$ORCH|orchestration/contention_matrix.yaml"
  "$ORCH|orchestration/derived/stack_priors.yaml"
  "$ORCH|orchestration/interaction_skills.yaml"
  "$ORCH|orchestration/launch_manifest.yaml"
  "$ORCH|orchestration/model_descriptors.yaml"
  "$ORCH|orchestration/model_registry.yaml"
  "$ORCH|orchestration/repl_memory/q_scorer.py"
  "$ORCH|orchestration/review_plane_knobs.yaml"
  "$ORCH|orchestration/stack_topology.yaml"
  "$ORCH|scripts/autokernel_actor_cli.py"
  "$ORCH|scripts/autopilot/autopilot.py"
  "$ORCH|scripts/autopilot/config_applicator.py"
  "$ORCH|scripts/autopilot/eval_tower.py"
  "$ORCH|scripts/autopilot/kv_compress.py"
  "$ORCH|scripts/autopilot/operator_seed_strategies.yaml"
  "$ORCH|scripts/benchmark/debug_scorer.py"
  "$ORCH|scripts/benchmark/seeding_orchestrator.py"
  "$ORCH|scripts/server/contention_matrix.py"
  "$ORCH|scripts/server/gpu_shadow_lane_preflight.py"
  "$ORCH|scripts/server/gpu_shadow_lane_stage0.py"
  "$ORCH|scripts/server/gpu_shadow_lane_tenancy.py"
  "$ORCH|scripts/server/orchestrator_stack.py"
  "$ORCH|scripts/server/realized_fleet.py"
  "$ORCH|scripts/server/stack_env.py"
  "$ORCH|scripts/server/stack_manifest.py"
  "$ORCH|scripts/server/stack_numa.py"
  "$ORCH|scripts/server/stack_numa_evict.py"
  "$ORCH|scripts/toon/ab_test_harness.py"
  "$ORCH|scripts/voice/speech_layouts.yaml"
  "$ORCH|src/api/routes/chat.py"
  "$ORCH|src/api/routes/chat_pipeline/proactive_stage.py"
  "$ORCH|src/api/routes/chat_pipeline/scout_stage.py"
  "$ORCH|src/api/routes/chat_review.py"
  "$ORCH|src/api/routes/dashboard.html"
  "$ORCH|src/api/routes/dashboard.py"
  "$ORCH|src/api/routes/dashboard_snapshot.py"
  "$ORCH|src/api/routes/dashboard_topology.py"
  "$ORCH|src/api/routes/health.py"
  "$ORCH|src/api/routes/v1_escalation.py"
  "$ORCH|src/backends/context_limits.py"
  "$ORCH|src/classifiers/factual_risk.py"
  "$ORCH|src/config/models.py"
  "$ORCH|src/fleet.py"
  "$ORCH|src/graph/approval_gate.py"
  "$ORCH|src/graph/langgraph/nodes.py"
  "$ORCH|src/llm_primitives/inference.py"
  "$ORCH|src/proactive_delegation/delegator.py"
  "$ORCH|src/registry/stack_priors.py"
  "$ORCH|src/roles.py"
  "$ORCH|src/scheduling/contention.py"
  "$ORCH|src/scheduling/device_model.py"
  "$ORCH|src/services/escalation_prewarmer.py"
  "$ORCH|stack_templates/default.yaml"
  "$ORCH|tests/test_autopilot_review_integration.py"
  "$ORCH|tests/test_review_decision_plane.py"
  "$ORCH|tests/unit/test_approval_gate.py"
  "$ORCH|tests/unit/test_autokernel_enrollment_cross_repo.py"
  "$ORCH|tests/unit/test_build_server_command_helpers.py"
  "$ORCH|tests/unit/test_chat_routes.py"
  "$ORCH|tests/unit/test_config.py"
  "$ORCH|tests/unit/test_config_consolidation.py"
  "$ORCH|tests/unit/test_config_lineup_liveness.py"
  "$ORCH|tests/unit/test_consultation.py"
  "$ORCH|tests/unit/test_contention_device_model.py"
  "$ORCH|tests/unit/test_debug_scorer_hard_fail.py"
  "$ORCH|tests/unit/test_default_template_topology_parity.py"
  "$ORCH|tests/unit/test_escalation_prewarmer.py"
  "$ORCH|tests/unit/test_ev6b_cross_family_fail_closed.py"
  "$ORCH|tests/unit/test_eval_tower_concurrency_metrics.py"
  "$ORCH|tests/unit/test_fleet_layer_build.py"
  "$ORCH|tests/unit/test_full_slot_demotion.py"
  "$ORCH|tests/unit/test_graph_router_integration.py"
  "$ORCH|tests/unit/test_inference_mixin.py"
  "$ORCH|tests/unit/test_kv_compress_adaptive.py"
  "$ORCH|tests/unit/test_proactive_delegator.py"
  "$ORCH|tests/unit/test_quarter_stack_smoke.py"
  "$ORCH|tests/unit/test_registry_chat_template_kwargs.py"
  "$ORCH|tests/unit/test_registry_validator.py"
  "$ORCH|tests/unit/test_repl_routing.py"
  "$ORCH|tests/unit/test_roles.py"
  "$ORCH|tests/unit/test_seeding_orchestrator.py"
  "$ORCH|tests/unit/test_stack_change_pipeline_simulated_fixtures.py"
  "$ORCH|tests/unit/test_stack_env.py"
  "$ORCH|tests/unit/test_stack_manifest_imports.py"
  "$ORCH|tests/unit/test_stack_numa.py"
  "$ORCH|tests/unit/test_stack_numa_evict.py"
  "$ORCH|tests/unit/test_v1_escalation.py"
  "$ROOTREPO|.claude/skills/kernel-promotion/promotion_gates.yaml"
  "$ROOTREPO|docs/reference/speech/cpu-speech-contention-20260924.md"
  "$ROOTREPO|scripts/harness/task_delegation_probe.py"
  "$ROOTREPO|tests/harness/test_task_delegation_probe.py"
)

PINS=(
  "63f88985a1a7add2b0580d2a6afb8e499bfe3c769a37fdc95752d2fc1c8863fc PACKAGE.md"
  "760fa555ef3530654df16c9885736d0a04c17177a365c8de3da155765fe076c7 evidence/assert_alias_clean.txt"
  "10a20ff4d3802aa21ba51bf38b3fdf545b36a01390b4a5ec997e5712a9bcbb81 evidence/classify.txt"
  "689a82db4c173bb54e784e47e283e6aa377ff6479ac2006d7c87d55780b283b7 evidence/pipeline-check-baseline.txt"
  "12b0b41bdfa59b5a70732297a2faa0fb1c5dbbc2dadf9299443c5f8b4799d872 evidence/pipeline-check-relabeled-state.txt"
  "e18e7f58c5e843d27888cc3111d64296bce1640e56be414e42ec65ea83031224 evidence/pipeline-update.txt"
  "2a8931c33338c23a371bff3f8b569b53c6b29a8ef6daf4df2f86c402fdb1704f evidence/tests.txt"
  "0973b8c1949fe932e06e6ef319394a5268ea75c5a92ef3f29b877058e0c4eaf3 evidence/url_diff.txt"
  "9214506d9a66d266ce12311acec5bc2dd353ea9dc879b1306004b4d9d1e46b2b evidence/urls-after-static.tsv"
  "62cd85e5880306106dbd055fd84cb3222dd3b52bb118c3a9bd7871c55b63a641 evidence/urls-before-static.tsv"
  "62cd85e5880306106dbd055fd84cb3222dd3b52bb118c3a9bd7871c55b63a641 evidence/urls-before.tsv"
  "89708ee091fb103bf57030b9cc766f901ab211cad557fd87ca746085aa11134c patches/orchestrator/0001-stack-ARCHSWAP-20260927-architect_general-Flash-Next.patch"
  "5a5e6d9f5a4ad67f5bcb3bc42eca42e3f283e2f1edcdfd344a0d7f4b56d2aa4a patches/orchestrator/0002-derived-regenerate-lean-registry-descriptors-stack-p.patch"
  "fe5483a4698901cb271cfee1e2028c6da9a0578dbd32fd2f2922653ec51f72be patches/orchestrator/0003-contention_matrix-DECLARED-RELABEL-for-ARCHSWAP-2026.patch"
  "1c687634465011c52631037c69e3ef76a5ecf7da91ef8c850d5cb4e084db87a9 patches/orchestrator/0004-roles-ARCHSWAP-20260927-review-and-plan-work-stay-on.patch"
  "7974b6021c6f21e1cbfe48245b3225a123bc3434eb2417ce5607656c8d28df7c patches/orchestrator/0005-derived-regenerate-for-the-reviewer-planner-bindings.patch"
  "a05e9cfb472d622a899a199f0ce9f4d47fca5f8352f2f8cebf47b1c5d95fdfbd patches/orchestrator/0006-v1_escalation-ARCHSWAP-20260927-auto-verdict-follows.patch"
  "2659b6994b55b79134a68aacccca3bd6157bcce24c4daaf3ef25da8134415905 patches/orchestrator/0007-derived-regenerate-after-merging-origin-main-into-th.patch"
  "138f6017a5cfa4c4d19814363f240349e40872be23ac772962d6d2d6a9f812b3 patches/orchestrator/NET.diff"
  "3453ea0da2759edf9dce02648e8489a9d14b246a685fc942ed1e462845345772 patches/research/0001-registry-ARCHSWAP-20260927-Flash-Next-becomes-archit.patch"
  "515116c237f42006939ebc62c3a3ea92ded83cc918c03e23fbec2648e3487b6c patches/research/NET.diff"
  "b6126e9321a26402f1530ace26df441e62688a5f82a66fa89b6debdd7eac2024 patches/root/0001-archswap-rebind-root-consumers-that-meant-the-27B-th.patch"
  "86a043877459292169c0d512896bbdfc24df431669b8b549882aee01365142ad patches/root/NET.diff"
  "d0865a51240fb69508e8cbdad569ba18df8dbfab526ff4c9a8856023c333d3a5 tools/relabel_contention_matrix.py"
  "b7f927b81e6aa11d1b25b8733558b608ecf59dca601856c96292a984f42de5ae tools/relabel_state.py"
  "59f46d65253559421d26673e4197587fb7c2b419f479f1a850757b271d16cff0 tools/transform_registry.py"
  "585cad92ea195fa576ac922611e590e870ab4fc43c25adb8591b66b8e747e138 tools/url_snapshot_static.py"
)

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  printf 'usage: %s --validate-only\n' "$0" >&2
  printf '       RATIFY_OPERATOR=<name> [THINKING_OPTION=follow-model|follow-role] [BRINGUP_OPTION=B1|B2] %s --attest %s\n' "$0" "$TOKEN" >&2
}

MODE=""
case "${1:-}" in
  --validate-only) [[ $# == 1 ]] || { usage; exit 2; }; MODE="validate" ;;
  --attest) [[ $# == 2 && "$2" == "$TOKEN" ]] || { usage; exit 2; }; MODE="attest" ;;
  *) usage; exit 2 ;;
esac

[[ -x "$PYTHON" ]] || fail "trusted interpreter unavailable"

if [[ "$MODE" == "attest" ]]; then
  op="${RATIFY_OPERATOR-}"
  op_trim="$(printf '%s' "$op" | tr -d '[:space:]')"
  [[ -n "$op_trim" ]] || fail "RATIFY_OPERATOR is unset or empty: the signer must be named"
  case "$(printf '%s' "$op_trim" | tr '[:upper:]' '[:lower:]')" in
    operator|default|unknown|unset|none|null|nobody|changeme|placeholder|test|tbd|todo|xxx|claude|agent|root|node|"<name>"|"<yourname>")
      fail "RATIFY_OPERATOR='$op' is a default/placeholder, not a signer" ;;
  esac
  THINKING_OPTION="${THINKING_OPTION:-follow-model}"
  BRINGUP_OPTION="${BRINGUP_OPTION:-B1}"
  # The project's one shared guard (scripts/operator/lib/ratify_operator.sh, 5ef39690): refuses an
  # unset name, a system account, the invoking login and any agent/session id. Exits 65.
  [[ -f "$ROOT/scripts/operator/lib/ratify_operator.sh" ]] || fail "shared operator guard missing: $ROOT/scripts/operator/lib/ratify_operator.sh"
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator
  [[ "$THINKING_OPTION" == "follow-model" ]] \
    || fail "THINKING_OPTION=$THINKING_OPTION: only follow-model is prepared; follow-role needs a REFRESHED package (PACKAGE.md O-2)"
  [[ "$BRINGUP_OPTION" == "B1" || "$BRINGUP_OPTION" == "B2" ]] || fail "BRINGUP_OPTION must be B1 or B2"
  [[ ! -e "$RECEIPT" ]] || fail "receipt already exists (token is SPENT): $RECEIPT"
fi

cd "$PKG"
for pin in "${PINS[@]}"; do
  want="${pin%% *}"; file="${pin#* }"
  [[ -f "$file" ]] || fail "missing package file: $file"
  got="$(sha256sum -- "$file" | cut -d' ' -f1)"
  [[ "$got" == "$want" ]] || fail "$file sha256 $got != pinned $want (package changed after preparation)"
  printf 'ok  %s\n' "$file"
done

for entry in "${LANES[@]}"; do
  IFS='|' read -r repo lane base commits <<<"$entry"
  git -C "$repo" fetch -q origin "$lane" || fail "cannot fetch origin/$lane in $repo"
  lane_head="$(git -C "$repo" rev-parse FETCH_HEAD)"
  for c in $commits; do
    git -C "$repo" merge-base --is-ancestor "$c" "$lane_head" \
      || fail "$c is not on origin/$lane in $repo"
    printf 'ok  %s %s on origin/%s\n' "$(basename "$repo")" "$c" "$lane"
  done
  git -C "$repo" fetch -q origin main || fail "cannot fetch origin/main in $repo"
  main_head="$(git -C "$repo" rev-parse FETCH_HEAD)"
  git -C "$repo" merge-base --is-ancestor "$base" "$main_head" \
    || fail "lane base $base is no longer an ancestor of origin/main in $repo"
  for t in "${TOUCHED[@]}"; do
    IFS='|' read -r trepo tpath <<<"$t"
    [[ "$trepo" == "$repo" ]] || continue
    if ! git -C "$repo" diff --quiet "$base" "$main_head" -- "$tpath"; then
      fail "STALE: $tpath moved on origin/main since $base ($(basename "$repo")). REFRESH the package (re-run its transform on the new main and re-pin); do not sign a stale package."
    fi
  done
  printf 'ok  %s: no touched path moved on origin/main since %s\n' "$(basename "$repo")" "$base"
done

if [[ "$MODE" == "validate" ]]; then
  printf 'VALID: package, patches, tools, evidence and lane commits verified; origin/main has not moved under the package. Nothing written.\n'
  exit 0
fi

mkdir -p -- "$(dirname -- "$RECEIPT")"
"$PYTHON" - "$RECEIPT" "$TOKEN" "$RATIFY_OPERATOR" "${RATIFY_CONSENT_REF:-}" \
  "$THINKING_OPTION" "$BRINGUP_OPTION" "${PINS[@]}" <<'PY'
import json, os, sys
from datetime import UTC, datetime
receipt, token, operator, consent_ref, think_opt, bringup_opt, *pins = sys.argv[1:]
doc = {
    "schema": "epyc.operator_receipt.v1",
    "token": token,
    "status": "ratified",
    "human_attestation": token,
    "signed_at": datetime.now(UTC).isoformat(),
    "signed_by": operator,
    "signed_by_uid": os.getuid(),
    "signature_channel": "chat-consent" if consent_ref else "terminal",
    "consent_ref": consent_ref or None,
    "package": "artifacts/operator/stack-change-archswap-20260927/PACKAGE.md",
    "pinned_sha256": {p.split(" ", 1)[1]: p.split(" ", 1)[0] for p in pins},
    "decision": "operator-decided 2026-09-27: swap architect roles — Qwen3.8-Flash-Next (:8074) -> architect_general, Qwen3.8-27B Q8 (:8083) -> architect_critic",
    "aliases": "operator ruling 2026-09-27: coder_escalation + ingest_long_context stay on the :8083 27B (host role architect_critic); not an option",
    "acknowledged": {
        "status": "approved in chat 2026-09-27 as amended; the approval, its wording and the session URL are recorded in PACKAGE.md section 4",
        "A-1": "routine graph escalation reaches the whole-machine-lock CPU role (supersedes the 2026-07-30 role definition and the D2 premise for architect_general)",
        "A-2": "AMENDED: review work (plan review, answer verdict, review_before_commit) AND plan decomposition (proactive_stage decomposition + repair) stay on the MI210 27B via DEFAULT_REVIEWER_ROLE / DEFAULT_PLANNER_ROLE = architect_critic; only escalation moves: routine escalation and risk_abstain_target_role go to architect_general (Flash-Next)",
        "A-3": "prewarm/scout cpu_region_lock bypass on :8074 — fixed by a separate orchestrator commit based on lane/archswap-20260927, merged before the bring-up API reload",
        "A-4": "by-name callers of architect_general now reach Flash-Next",
        "A-5": "pre-existing: ingest_long_context in serial_roles while its host is not",
    },
    "options_chosen": {
        "O-2_thinking": think_opt,
        "O-3_bringup": bringup_opt,
    },
    "not_in_scope": [
        "RI-21 (graph never reaches ARCHITECT_CRITIC) — deliberately left open",
        "DAR-LAT-3h/3i (G1 verdict T96: -t 96 kept; nothing folded) — their patches must be re-keyed to architect_general, the role serving Flash-Next after this swap",
        "registry schema refactor (servers keyed by model instance; roles bind to servers) — PACKAGE.md 4a",
    ],
    "applies_nothing": True,
}
tmp = receipt + ".tmp"
with open(tmp, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2)
    fh.write("\n")
os.replace(tmp, receipt)
print(f"RATIFIED: {receipt}")
PY
