#!/bin/bash
# Operator signature for STACKCHG-KVPOOL-20261003 (see PACKAGE.md in this directory):
#   * :8083 Qwen3.8-27B-Q8_0 unified KV pool -c 196608 -> 393216 (np 4, kv-unified, q8_0 K/V kept);
#   * per-request context = 262144 (n_ctx_train) — clamped by the v10 server itself, mirrored by
#     the orchestrator's context limits (fix to the step-1 cap so pool admission stays armed);
#   * DFlash2 drafter --spec-draft-n-max 8 -> 7 (roles.qwen38_27b_q8_local.drafters.dflash2);
#   * serving_shape.vram_non_kv_gib 37.92 -> 39.15 (DERIVED, UNVALIDATED until bring-up);
#   * stack_change_pipeline `update` stale-priors fix; stale template spec_overrides deleted.
#
# What it does: verifies PACKAGE.md, the intent, both patches, the tools and the key evidence
# against the sha256 values pinned below; verifies every patch STILL applies (`git apply
# --check`, read-only) to the current working tree of its repo — if not, the package must be
# REFRESHED by its preparer, never reconciled at signing; asks the signer to retype the token
# on the controlling terminal; writes ONE receipt.
#
# What it does NOT do: apply a patch, commit, compile, start, stop or reload anything. The
# apply and bring-up (PACKAGE.md section 7) run afterwards and begin by checking this receipt.
#
# GOVERNANCE (OPERATING_CONSTRAINTS: "the operator signs from a terminal"): TTY-gated. An agent
# must not run --attest, with or without chat consent; hand the operator the command:
#   RATIFY_OPERATOR="<your name>" bash ratify_stackchg_kvpool_20261003.sh --attest RATIFY-STACKCHG-KVPOOL-20261003
# Run it in a separate terminal — never under a `!` command, never chained with `&&`.
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-STACKCHG-KVPOOL-20261003"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOTREPO="/workspace"
RECEIPT="$ROOTREPO/artifacts/operator/receipts/$TOKEN.json"
RECEIPT_COPY="$PKG/receipts/$TOKEN.json"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
PYTHON="/usr/bin/python3"

# repo|patch — each must `git apply --check` cleanly on that repo's current working tree.
APPLIES=(
  "$ORCH|patches/orchestrator/stackchg-kvpool-20261003.orchestrator.patch"
  "$RESEARCH|patches/research/stackchg-kvpool-20261003.research.patch"
)

PINS=(
@@PINS@@
)

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  printf 'usage: %s --validate-only\n' "$0" >&2
  printf '       RATIFY_OPERATOR=<name> %s --attest %s   (from a terminal)\n' "$0" "$TOKEN" >&2
}

MODE=""
case "${1:-}" in
  --validate-only) [[ $# == 1 ]] || { usage; exit 2; }; MODE="validate" ;;
  --attest) [[ $# == 2 && "$2" == "$TOKEN" ]] || { usage; exit 2; }; MODE="attest" ;;
  *) usage; exit 2 ;;
esac
[[ -x "$PYTHON" ]] || fail "trusted interpreter unavailable"

if [[ "$MODE" == "attest" ]]; then
  # --- TTY gate: a human at a terminal, not a pipe, not a `!` command, not an agent tool ---
  [[ -t 0 && -t 1 ]] || fail "attest must run from an interactive terminal (stdin/stdout are not a TTY)"
  [[ -r /dev/tty && -w /dev/tty ]] || fail "no controlling terminal (/dev/tty)"
  # --- signer must be named, and not a placeholder, system account, the login, or an agent ---
  op="${RATIFY_OPERATOR-}"
  op_trim="$(printf '%s' "$op" | tr -d '[:space:]')"
  [[ -n "$op_trim" ]] || fail "RATIFY_OPERATOR is unset or empty: the signer must be named"
  op_lc="$(printf '%s' "$op_trim" | tr '[:upper:]' '[:lower:]')"
  case "$op_lc" in
    operator|default|unknown|unset|none|null|nobody|changeme|placeholder|test|tbd|todo|xxx|claude*|codex*|agent*|root|node|daemon|"<name>"|"<yourname>")
      fail "RATIFY_OPERATOR='$op' is a default/placeholder/system/agent name, not a signer" ;;
  esac
  [[ "$op_lc" =~ ^(main[a-d]|workspace-[0-9a-z]+|a[0-9a-f]{12,})$ ]] && fail "RATIFY_OPERATOR='$op' looks like an agent/session id"
  [[ "$op_lc" != "$(id -un | tr '[:upper:]' '[:lower:]')" ]] || fail "RATIFY_OPERATOR equals the invoking login ($(id -un)); type your own name"
  if [[ -f "$ROOTREPO/scripts/operator/lib/ratify_operator.sh" ]]; then
    # shellcheck source=/dev/null
    source "$ROOTREPO/scripts/operator/lib/ratify_operator.sh"   # the project's shared guard (exit 65)
    ratify_require_operator
  fi
  [[ ! -e "$RECEIPT" ]] || fail "receipt already exists (token is SPENT): $RECEIPT"
  [[ ! -e "$RECEIPT_COPY" ]] || fail "receipt already exists (token is SPENT): $RECEIPT_COPY"
fi

cd "$PKG"
for pin in "${PINS[@]}"; do
  want="${pin%% *}"; file="${pin#* }"
  [[ -f "$file" ]] || fail "missing package file: $file"
  got="$(sha256sum -- "$file" | cut -d' ' -f1)"
  [[ "$got" == "$want" ]] || fail "$file sha256 $got != pinned $want (package changed after preparation)"
  printf 'ok  %s\n' "$file"
done

for entry in "${APPLIES[@]}"; do
  IFS='|' read -r repo patch <<<"$entry"
  git -C "$repo" apply --check "$PKG/$patch" 2>/dev/null \
    || fail "STALE: $patch no longer applies to $repo @ $(git -C "$repo" rev-parse --short HEAD). REFRESH the package; do not sign a stale package."
  printf 'ok  %s applies to %s @ %s\n' "$patch" "$(basename "$repo")" "$(git -C "$repo" rev-parse --short HEAD)"
done

if [[ "$MODE" == "validate" ]]; then
  printf 'VALID: package, patches, tools and evidence verified; every patch applies to the current trees. Nothing written.\n'
  exit 0
fi

printf '\nYou are signing %s.\nRead PACKAGE.md section 8 (A-1 .. A-7) first. Retype the token to sign: ' "$TOKEN" > /dev/tty
IFS= read -r typed < /dev/tty
[[ "$typed" == "$TOKEN" ]] || fail "token not retyped exactly; nothing written"

mkdir -p -- "$(dirname -- "$RECEIPT")" "$(dirname -- "$RECEIPT_COPY")"
"$PYTHON" - "$RECEIPT" "$RECEIPT_COPY" "$TOKEN" "$RATIFY_OPERATOR" "${PINS[@]}" <<'PY'
import json, os, sys
from datetime import datetime, timezone
receipt, copy, token, operator, *pins = sys.argv[1:]
doc = {
    "schema": "epyc.operator_receipt.v1",
    "token": token,
    "status": "ratified",
    "human_attestation": token,
    "signed_at": datetime.now(timezone.utc).isoformat(),
    "signed_by": operator,
    "signed_by_uid": os.getuid(),
    "signature_channel": "terminal",
    "consent_ref": None,
    "package": "/mnt/raid0/llm/tmp/stack-change-kvpool-20261003/PACKAGE.md "
               "(to be copied to artifacts/operator/stack-change-kvpool-20261003/)",
    "pinned_sha256": {p.split(" ", 1)[1]: p.split(" ", 1)[0] for p in pins},
    "decision": (
        "operator-approved 2026-10-03 ('yes', kv-sizing-8083-20261003 DECISION.md option (a) "
        "at 393216): :8083 Qwen3.8-27B-Q8_0 runs a unified KV pool of -c 393216 at np 4, q8_0 K/V; "
        "each request capped at n_ctx_train 262144; DFlash2 --spec-draft-n-max 7; "
        "serving_shape.vram_non_kv_gib 39.15 (derived)."
    ),
    "acknowledged": {
        "A-1": "393216 holds ONE full 262144 request plus 131072 of others (or 4 x 98304). Two "
               "concurrent full-262144 requests do NOT fit (they would need -c 524288, ~57.2 GiB derived): "
               "orchestrated ones queue in SharedKVPoolAdmission; a direct client can still "
               "exhaust the pool. The approval rationale 'two such requests still fit' is "
               "arithmetically false at 393216 and is superseded by this line.",
        "A-2": "The per-request cap is enforced by the v10 server itself (n_ctx_slot = "
               "min(n_ctx_seq, n_ctx_train), WARN at load) for every client, and mirrored by the "
               "orchestrator from model.ctx_max (step 1, 2586a7bb). This package fixes step 1's "
               "unified/split inference and pool size for a server that clamps.",
        "A-3": "vram_non_kv_gib 39.15 is DERIVED from a runtime KFD reading plus measured slopes "
               "and is UNVALIDATED at -c 393216; the load-time peak and the 4 x ~90k concurrency "
               "probe are owed at bring-up (PACKAGE.md 7.3), in the owner's window.",
        "A-4": "Decode cost on a unified pool grows with pool FILL (DECISION.md section 2, [D]); a "
               "fuller 393216 pool can slow every slot's decode. Unmeasured; the zero-compute "
               "regression in DECISION.md section 4 decides unified vs split afterwards.",
        "A-5": "--spec-draft-n-max 7 is drafting-identical (block_size 8 clamps 8 to 7) and frees "
               "one GDN rollback snapshot per slot (0.58 GiB); the canonical AutoKernel recipe "
               "keeps 8 as its measurement identity.",
        "A-6": "Orchestrator code: context_limits unified inference + clamped pool; "
               "stack_change_pipeline `update` evicts stack_manifest after rewriting the lean "
               "(one `update` wrote stale priors and the next `check` failed, reproduced); the "
               "stale stack_templates/default.yaml architect_critic spec_overrides (draft_max 4) "
               "deleted.",
        "A-7": "Bring-up = `reload architect_critic` then `reload orchestrator` (the cap lives in "
               "the API), run by the owner of :8083 inference at its own boundary.",
    },
    "not_in_scope": [
        "np, kv_unified, KV quantisation, placement, kernel (v10 ffc1bac82 unchanged)",
        "the canonical recipe qwen3.8-27b-q8-gpu-dflash2-np4.json (stays draft_n_max 8)",
        "the DFLASH2 package's root topology_check.py patch (still unapplied; see PACKAGE.md 3)",
    ],
    "applies_nothing": True,
}
data = json.dumps(doc, indent=2) + "\n"
for path in (receipt, copy):
    tmp = path + ".tmp"
    with open(tmp, "x", encoding="utf-8") as fh:
        fh.write(data)
    os.replace(tmp, path)
print(f"RATIFIED: wrote {receipt}\n          and {copy}")
PY
