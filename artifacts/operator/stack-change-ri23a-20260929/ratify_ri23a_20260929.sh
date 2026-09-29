#!/bin/bash
# Operator signature for the RI-23a stack-change package: coder_escalation (an alias on the
# :8083 Qwen3.8-27B, host architect_critic) declares its host's thinking kwargs
# {enable_thinking: true, reasoning_effort: medium} instead of enable_thinking: false.
# See PACKAGE.md in this directory.
#
# What it does: verifies PACKAGE.md, the patches, the tool and the evidence against the
# sha256 values pinned below; verifies every lane commit is on its origin lane; verifies
# that NOTHING this package touches has moved on origin/main since the lanes were cut
# (otherwise the package must be REFRESHED by its preparer, never reconciled at signing);
# writes ONE receipt.
#
# What it does NOT do: apply a patch, merge a branch, compile, start, stop or reload
# anything. The bring-up (PACKAGE.md section 7) runs afterwards and begins by checking
# this receipt.
#
# GOVERNANCE: the signer must be named. RATIFY_OPERATOR must be set to a real name and
# must not be a default/placeholder value; this script refuses otherwise. Signing from a
# terminal:   RATIFY_OPERATOR="<your name>" ./ratify_ri23a_20260929.sh --attest <TOKEN>
# Recording chat consent (a session acting on the operator's explicit chat approval):
#   RATIFY_OPERATOR="<name>" RATIFY_CONSENT_REF="<chat/session reference>" ... --attest <TOKEN>
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-RI23A-20260929"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$PKG/../../.." && pwd)"
RECEIPT="$ROOT/artifacts/operator/receipts/$TOKEN.json"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
ROOTREPO="/workspace"
PYTHON="/usr/bin/python3"

# repo|lane|base|commits  (base = origin/main the lane was cut from, or last merged in;
# every commit must be an ancestor of origin/<lane>). The root lane carries only this
# package, whose files are pinned below, so it lists no commits.
LANES=(
  "$RESEARCH|lane/ri23a-20260929|48ed3f77ab69d5ef223f857334ce2ef32f2f98c9|4ba28678"
  "$ORCH|lane/ri23a-20260929|c62fcadd50fa7ea73c2c94add3ea4bce3230324c|1f437ac5 269e755a ac281703 8991000d"
  "$ROOTREPO|lane/ri23a-20260929|04a82bc87f55a6a71de6a954211800aa9590aa64|"
)

# repo|path ...  — every path this package's patches touch. If ANY of them differs
# between the lane base and current origin/main, the package is stale.
TOUCHED=(
  "$RESEARCH|orchestration/model_registry.yaml"
  "$ORCH|docs/generated/current_stack_summary.md"
  "$ORCH|orchestration/derived/stack_priors.yaml"
  "$ORCH|orchestration/model_descriptors.yaml"
  "$ORCH|orchestration/model_registry.yaml"
  "$ORCH|tests/unit/test_registry_chat_template_kwargs.py"
  "$ROOTREPO|artifacts/operator/receipts/RATIFY-RI23A-20260929.json"
)

PINS=(
  "bbd12c2d037c3196b5b1bb85dfe03f53d21f89d5cfa84cc9986f73653c150ce0 PACKAGE.md"
  "5c87b28cc05ee4c225df4441e1841a9bf33892401f18033aaf5efeb297445ba3 evidence/assert_alias_clean.txt"
  "ba248f527844c6ad23337ad494310ca57b86b597903c1844cc88cb222097fe4b evidence/no_relaunch.txt"
  "6a35b4dae5c8a6934c1a810fad9773028fb6705a16e10d433e6a1fec699318d3 evidence/pipeline-check-after-livestate.txt"
  "da5fda7da63b48a82fe38da45aab800b3595e78595b173c700d6b19c3d334833 evidence/pipeline-check-after.txt"
  "da0c16d7b8695bf46803167afb8d3c0512fcbd322f433c0d5433db72e53991b3 evidence/pipeline-check-main-baseline.txt"
  "a59f3011fe9e82f9b6698f92a9c737bb7e317ef98fc37f93214b70e2a5dc0563 evidence/pipeline-update.txt"
  "fc74f8ec82efa089e058157fed6320c148044d04ffbb02762622253d3bf9e9d5 evidence/snapshot-after.tsv"
  "8340cd8516323472d0dc308222f01dee2723cd54ecc3b45779374a7d8a1f5b62 evidence/snapshot-before.tsv"
  "44c54b622df28e07aa0c25c9f66b287f529e1d700aa3cfa37bef7749213fb20b evidence/tests.txt"
  "abf05f59d5af05517dc93b29af707e311d0d11b37a2a242e40b518a0004c8a28 evidence/url_kwargs_diff.txt"
  "ba760d4dbb4c34ed2c0918ecc666982bdcd4deb75f901c2d127d879e2861380c patches/orchestrator/0001-tests-RI-23a-coder_escalation-declares-its-8083-host.patch"
  "87cc2849a6ff2a41bcb5e1fea006a04376bc9fd34f6c966bedb0220ae8254f4c patches/orchestrator/0002-derived-RI-23a-regenerate-lean-registry-descriptors-.patch"
  "1ce83722153855c308b4ee58abf9c76d88e19248a3d32f0cc9c4615269ec0a18 patches/orchestrator/0003-derived-RI-23a-regenerate-after-merging-origin-main-.patch"
  "fdd9fd1a157781948d5687a6c2f6678a7b8ae50cb51ac66570d0fe50b10e38f6 patches/orchestrator/NET.diff"
  "a23d213853a83beaedcf09508c11ec5709af1d1e96085ac9b93f1d4a2f6b709d patches/research/0001-registry-RI-23a-coder_escalation-thinks-at-medium-li.patch"
  "e8b97d1d2d27b29f75fe4d4beea3876df5e043437fe6d19f0e6d325a564bdfbc patches/research/NET.diff"
  "a608a8f3c4110d3401ca62073a553f5723a64297ba7bb59e29a6b8770eaa9dab tools/snapshot_static.py"
)

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  printf 'usage: %s --validate-only\n' "$0" >&2
  printf '       RATIFY_OPERATOR=<name> [RATIFY_CONSENT_REF=<ref>] %s --attest %s\n' "$0" "$TOKEN" >&2
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
  # The project's one shared guard (scripts/operator/lib/ratify_operator.sh): refuses an
  # unset name, a system account, the invoking login and any agent/session id. Exits 65.
  [[ -f "$ROOT/scripts/operator/lib/ratify_operator.sh" ]] || fail "shared operator guard missing: $ROOT/scripts/operator/lib/ratify_operator.sh"
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator
  [[ ! -e "$RECEIPT" ]] || fail "receipt already exists (token is SPENT): $RECEIPT"
  [[ ! -e "$ROOTREPO/artifacts/operator/receipts/$TOKEN.json" ]] \
    || fail "receipt already exists (token is SPENT): $ROOTREPO/artifacts/operator/receipts/$TOKEN.json"
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
  git -C "$repo" merge-base --is-ancestor "$base" "$lane_head" \
    || fail "lane base $base is not in origin/$lane in $repo"
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
      fail "STALE: $tpath moved on origin/main since $base ($(basename "$repo")). REFRESH the package (re-run the pipeline update on the new main and re-pin); do not sign a stale package."
    fi
  done
  printf 'ok  %s: no touched path moved on origin/main since %s\n' "$(basename "$repo")" "$base"
done

if [[ "$MODE" == "validate" ]]; then
  printf 'VALID: package, patches, tool, evidence and lane commits verified; origin/main has not moved under the package. Nothing written.\n'
  exit 0
fi

mkdir -p -- "$(dirname -- "$RECEIPT")"
"$PYTHON" - "$RECEIPT" "$TOKEN" "$RATIFY_OPERATOR" "${RATIFY_CONSENT_REF:-}" "${PINS[@]}" <<'PY'
import json, os, sys
from datetime import UTC, datetime
receipt, token, operator, consent_ref, *pins = sys.argv[1:]
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
    "package": "artifacts/operator/stack-change-ri23a-20260929/PACKAGE.md",
    "pinned_sha256": {p.split(" ", 1)[1]: p.split(" ", 1)[0] for p in pins},
    "decision": (
        "operator-decided 2026-09-29: OP-69 = (a) (thinking-on roles on the chat-completions lane) "
        "and 'proceed' on RI-23a in chat. coder_escalation (alias on the :8083 Qwen3.8-27B, host "
        "architect_critic) declares chat_template_kwargs {enable_thinking: true, reasoning_effort: "
        "medium}, mirroring its host; roles.coder_escalation.model.disable_thinking true -> false"
    ),
    "acknowledged": {
        "A-1": (
            "coder_escalation answers on the chat lane include thinking (reasoning_effort medium), "
            "split into reasoning_content. Latency goes up: RI-23b measured coder_escalation at "
            "1.44 s with thinking OFF on the chat lane and 5.65 s with inline thinking on /completion"
        ),
        "A-2": (
            "no port, process, model or launch argv changes; the kwargs are request-side, so the "
            "bring-up is an API reload only (no llama-server relaunch) - evidence/no_relaunch.txt"
        ),
    },
    "applies_nothing": True,
}
tmp = receipt + ".tmp"
with open(tmp, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2)
    fh.write("\n")
os.replace(tmp, receipt)
print(f"RATIFIED: {receipt}")
PY
