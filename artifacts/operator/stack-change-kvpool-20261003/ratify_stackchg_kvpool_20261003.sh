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
  "e37fa00dcdb24e42ca31a912e1cd6b722ce940a652ee83daa4d8e3f2e21b07a6 PACKAGE.md"
  "5cc37561ef093f33c8e4783898a38d666892bcf37e5c2c6092b4f87f5d8bdc47 intent.yaml"
  "7d63614a4858f989aeab99d5bf67f4b686f9efbfb0e77e11c6e24a44ca1dcf18 patches/orchestrator/stackchg-kvpool-20261003.orchestrator.patch"
  "1cb040b018126da01857a665359625581f4ef4caf6794979f46ea5fd24150a29 patches/research/stackchg-kvpool-20261003.research.patch"
  "f8812a4f20f94d1ca7cfed2ca9ea74cd25f325232356a792dba6316abfbd5028 evidence/apply-proof.txt"
  "e8e72db5746cbafbe9b054f32def96382170130cdc41ccfb7c7b52cdc2d3a3af evidence/argv_8083-base.txt"
  "1356042d8031e4e8d8383a1b9d2fdff7452838cf6df68559ae04a6e234eb39cd evidence/argv_8083-pristine.txt"
  "4b4f185eb50097c032355d458f8e4a5ac426e8f0c70c54f44644b68aa12f9a4d evidence/capacity-base.txt"
  "665839439870102765fd6a93c8f0c9f8d04642ceeda21a1a8dfb7ce465a4914b evidence/capacity-pristine.txt"
  "8c948bcabddf1846dfdd089fe7974ea977becd3975aa575b512a3b4ce0dc45fe evidence/capacity_sh.txt"
  "d22c5a5464f06fa89585d50d2ca5a468ac6eeeedf433e890c3d71b2b43dc0c1f evidence/derived-delta.GENERATED.diff"
  "3f32ec8dffc837369d140b60f683dc42d1069e7fb25c6a91f74572d71ab2ffc9 evidence/gitnexus_impact.txt"
  "6745cfa66a212255e8b9ee23e94a07cff7e302817ebe810fe56e32e56d30d61b evidence/live-state.txt"
  "2281650e62f15e99e29c581271dba39cb00582b8138077382c34fda8b692c779 evidence/pipeline-check-base.txt"
  "02da774d6ddb745552d660bdb3785d315ee0f7426270b5a76a7c3bb4111f9bd3 evidence/pipeline-check-pristine.txt"
  "93a335efb030992482cd5a0c07b6460fb5cb9850291347dfdef32fd8b568642c evidence/pipeline-stale-priors-repro.txt"
  "bc5f7435a0803453b5660c001144bcf1762227f9daa35399b506896d2e17a6fd evidence/pipeline-update-base.txt"
  "55edfd31cce525f4c0857bad7157ca3864f309f33d9072cd99cc46a4fa225aa3 evidence/pipeline-update-pristine.txt"
  "13b069cd60acfc0f8a116a20ec898ded7262f4bc2c7db85117c9cb2bcab673d8 evidence/preflight-classified.txt"
  "dd3aa5ba2df6443e6a54622531a37519cd8525a143e7d039b133134ef0b373bf evidence/tests-baseline.txt"
  "df5bb9c1dbf1a21285ebcf77f512dc8b9c152b2433478903cbfdb9cdadb1daab evidence/tests.txt"
  "7e77e3d4b282b33b0119b0a7325939de778fdf9ba18c2738239d8606341f428f evidence/topology_check.txt"
  "3077cb14f9d813c604b6b680f1b78710c6855c2854cf64072295e116380c1938 evidence/topology_check_rootpatched.txt"
  "b5e20ccf3efcdedd675db902591488f3e4055e7350cfe9790740866c6d8b83ef tools/build_sandbox.sh"
  "d14dd732f4b57c7b72f244abcdd5119749dcc655a4dcc70d94c7ff9381d767f6 tools/capacity_report.py"
  "be5e221f45990f07a9e7cd4e6f7fabc742e9752fe30d8dc9a48d75a4ba43c6b3 tools/capacity_sh_local.sh"
  "0c28ac8934f65d30bc08f225336b5e3fb3cd699e961daa79b5b82cdd3d7371a4 tools/compile.sh"
  "13197a3a6d50839295683107516fdc1abb1e275f483ab102db6591bf992b85bc tools/concurrency_probe.py"
  "50be46bb30d791de879dd0cdb9e291201938a4eb139d0f3e4d696c6b1fe70b9b tools/gen_ratify.py"
  "5f8c84f66af62005bf0c36401e6c569b7bf1f8aa32da0c3d6e44dcbac46d55ba tools/impact.sh"
  "d0c7b2479f4084956132b9c9fbb1d9b0c3c91a8476c7ad7197381c164b0a1176 tools/live_state.sh"
  "bb3ca7e34288cc5d0378c0aafd05d95cacbffd78113404d98c9a1db16ba72e82 tools/make_patches.sh"
  "6befd62b769eb32d410c17fe1974d4a46f6470f78a4d3496d4996610b1b4c0e8 tools/preflight_scratch.sh"
  "25f5a796c5b892a659c9414093a1c1f2df7c9c51e5e2da341402e1ca26dc3927 tools/ratify_template.sh"
  "3b21393290ba65ae7ae0c58fbc8143f1a1a24e4470c103c5b29b36dfab4d4b11 tools/rebase_sandboxes.sh"
  "204310c1192a7b4b2fc7eabb60dae43cd0f079917e829da5545f34caf876322b tools/render_argv.py"
  "09d5e54a4ac1a0029907b25c83137e80a30a5fe8d2f676c46491f79f757c9470 tools/repro_stale_priors.sh"
  "03cac431bd5d854642bb4208b735e56474fc3dbd9e098399a6c70b55d71100e4 tools/reset_derived.sh"
  "fa50df3f5579920fc34e71560fe91ca2541314a00ea68fbaff40652144557e87 tools/run_tests.sh"
  "9280f3378c9385cdde3f32acfe761c2128e891fd001c1f1725c0a01a8431c0d4 tools/setup.sh"
  "ff30853c0b7f25b1df45e326983c8d633f331329e6cd8e95f7d2f35cbcb2a1d9 tools/topology_check_patched.sh"
  "49527d7bb2fc51a35b8ea19d5437573990c05da8a9b5e69b255dd4255ba29cc5 tools/verify.sh"
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
