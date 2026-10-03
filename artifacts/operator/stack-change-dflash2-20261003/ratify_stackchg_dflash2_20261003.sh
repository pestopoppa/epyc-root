#!/bin/bash
# Operator signature for STACKCHG-DFLASH2-20261003 (see PACKAGE.md in this directory):
#   * :8083 Qwen3.8-27B-Q8_0 -> DFlash2 drafter, selected by stack_topology drafter_selection
#     from the master's per-model `drafters` list (DRAFT-SEL-1), production shape unchanged;
#   * Qwen3-VL-30B :8086 -> cold CPU (WARM tier, NUMA_HALF_A) until the 2nd MI210;
#   * amendment of the canonical `speculative_decoding_policy` block (A-1) and reversal of the
#     2026-09-22 "BOTH GPU ROLES STAY ON THE CARD" ruling (A-2) — PACKAGE.md section 8.
#
# What it does: verifies PACKAGE.md, the intent, the three patches, the tools and the key
# evidence against the sha256 values pinned below; verifies every patch STILL applies
# (`git apply --check`, read-only) to the current working tree of its repo — if not, the
# package must be REFRESHED by its preparer, never reconciled at signing; asks the signer to
# retype the token on the controlling terminal; writes ONE receipt.
#
# What it does NOT do: apply a patch, commit, compile, start, stop or reload anything. The
# apply and bring-up (PACKAGE.md section 7) run afterwards and begin by checking this receipt.
#
# GOVERNANCE (OPERATING_CONSTRAINTS: "the operator signs from a terminal"): TTY-gated. An agent
# must not run --attest, with or without chat consent; hand the operator the command:
#   RATIFY_OPERATOR="<your name>" bash ratify_stackchg_dflash2_20261003.sh --attest RATIFY-STACKCHG-DFLASH2-20261003
# Run it in a separate terminal — never under a `!` command, never chained with `&&`.
set -euo pipefail
export PATH="/usr/bin:/bin"

TOKEN="RATIFY-STACKCHG-DFLASH2-20261003"
PKG="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOTREPO="/workspace"
RECEIPT="$ROOTREPO/artifacts/operator/receipts/$TOKEN.json"
RECEIPT_COPY="$PKG/receipts/$TOKEN.json"
ORCH="/mnt/raid0/llm/epyc-orchestrator"
RESEARCH="/mnt/raid0/llm/epyc-inference-research"
PYTHON="/usr/bin/python3"

# repo|patch — each must `git apply --check` cleanly on that repo's current working tree.
APPLIES=(
  "$ORCH|patches/orchestrator/stackchg-dflash2-20261003.orchestrator.patch"
  "$RESEARCH|patches/research/stackchg-dflash2-20261003.research.patch"
  "$ROOTREPO|patches/root/stackchg-dflash2-20261003.root.patch"
)

PINS=(
  "68e8457c4d6ea7b6338695290fd45b5c766e70b24453ad9c060dc12c6e5b25d0 evidence/argv_8083-baseline.txt"
  "e8e72db5746cbafbe9b054f32def96382170130cdc41ccfb7c7b52cdc2d3a3af evidence/argv_8083.txt"
  "391d6ed8fe354a0d8918c13979811098969887b908ddb8fc8cb3613f71b4e200 evidence/argv_8086.txt"
  "203f315831267eae7eb259c06ad0f69417a542a4bf43ba797f8d1394e7c259fb evidence/assert_alias_clean.txt"
  "fe4eaa6012d0023533105774480daa39aae462047f5777947a397f0348b0216b evidence/capacity-baseline.txt"
  "438e7ab7009145004b7fe76d0c581dbd5d8357bd89d9b3eebab51b12b90f47a4 evidence/capacity.txt"
  "e85e0060c39e3f3bf1bb4f0a7342a18f5ec9e99646c2ad6de6175ff814da4a03 evidence/capacity_sh.txt"
  "505b5f88e632db1c5889d49656f9411c8f3981815bffffd63f212102b2ac3344 evidence/derived-delta.GENERATED.diff"
  "72517cb6b97dcbc2e924104d4d26c7fd00395a8f4c2b5b27ed5f6635a0dd23e7 evidence/gitnexus_impact.txt"
  "a5e315548af78e651ef5d391167bbe6fb078bc27b1e2ed6354c240c65937769c evidence/live-state.txt"
  "876bafa52be2009fdb552ba6935f01bc7a8130d32954ebc55f4ab6a424e9e080 evidence/pipeline-check-baseline.txt"
  "d7af1341e56cd30b48e5ebbf4447e593e423d254328b191bbdc5fa38705de396 evidence/pipeline-check.txt"
  "82d1c63c995e249c23245d11b1d0c4b7b19b1b83aa696db95447efd329f7fdb7 evidence/pipeline-update.txt"
  "84bd02fcc67e89aa1a72eed2124c1356dcb17c3b3f69430ad65ee4b809985bd6 evidence/preflight-classified.txt"
  "34dd3613fdcc90fcb05eeaa57869c219f57c5d778c7ad114f561879355929a32 evidence/tests-baseline.txt"
  "938e72a9fedf51819a311e5042f30fde5003fdfbf83c752460b6845c6f42b343 evidence/tests.txt"
  "47ebd927d92a9e45558efbc87fa27cf17d7494956bfed7008e8ec9cd4a04edab evidence/topology_check.txt"
  "296db6e0a84da946b1383159466d01f2c223d4179fb122120d6e47dd3d2901ff evidence/withdraw_contention.txt"
  "4235ffaf0b058518a38c75115fc96a03197a36e0c702b5297458b9bf35497966 intent.yaml"
  "040561a56ed1acf1402b03851c1caeb5d220efecc87ac92c7ccea8724fd891e9 patches/orchestrator/stackchg-dflash2-20261003.orchestrator.patch"
  "5996c660d92b502106b8f4e88fd2cce9f1883b932bf801029951484fd1e95168 patches/research/stackchg-dflash2-20261003.research.patch"
  "986dead1e43ee457f0a4d5ef9cf585efba68d0e75affa31a4344bdffbbb2b031 patches/root/stackchg-dflash2-20261003.root.patch"
  "7e1006490c2d2ec66c799c9530ad7b2465a685e528df54a5628eb918d7a5ecb7 tools/build_sandbox.sh"
  "d14dd732f4b57c7b72f244abcdd5119749dcc655a4dcc70d94c7ff9381d767f6 tools/capacity_report.py"
  "efcba64c06563f4c0a9296548af1b46805f9ca796aedd58b4f7f1845105b450e tools/edit.py"
  "f20039f1c330aac94e301dcd8fb46a5e2609d7c16769e9ed15ef8187affc6587 tools/make_patches.sh"
  "2ee1a20623b660fe7b18c7a747c9c44c7333a7eebf33451def6c8162ec4f98d7 tools/preflight_scratch.sh"
  "204310c1192a7b4b2fc7eabb60dae43cd0f079917e829da5545f34caf876322b tools/render_argv.py"
  "3725a10280e709a8e75f0ec62a189b5321e941945a3bdf00ef6f33e638fa8332 tools/run_tests.sh"
  "f9ca19114ddce6258873f933bc4c25c9436770668391865d1347dda8b49e4dcb tools/update_test_pins.py"
  "a2ffbfa491f85bc17d3ba6dd3e6d18b78c61d7f1bedb68d72c84f60e63534842 tools/verify.sh"
  "6b9a578d3ab7335d8253ed2e9d00327630f23d055d4e03aef934a6e5f2b79b47 tools/vision_transform.py"
  "a7038c5bd4c1e6b65dd6dfb9a5b00c42b28338542662cf4867cdeaa233ac03cc tools/withdraw_contention_role.py"
  "a32174f3c5a858040880832329878912273025b883ac4c29d1845d20acd9d43e PACKAGE.md"
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

printf '\nYou are signing %s.\nRead PACKAGE.md section 8 (A-1 .. A-8) first. Retype the token to sign: ' "$TOKEN" > /dev/tty
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
    "package": "/mnt/raid0/llm/tmp/stack-change-dflash2-20261003/PACKAGE.md "
               "(to be copied to artifacts/operator/stack-change-dflash2-20261003/)",
    "pinned_sha256": {p.split(" ", 1)[1]: p.split(" ", 1)[0] for p in pins},
    "decision": (
        "operator-decided 2026-10-01 'ALWAYS use dflash2' and 2026-10-03 'Vision down, canonical "
        "DFlash2' (refined: VL-30B to cold CPU, WARM tier). :8083 Qwen3.8-27B-Q8_0 runs DFlash2 "
        "(-md Qwen3.8-27B-DFlash2-Q8_0.gguf -ngld 99 --spec-type draft-dflash --spec-draft-n-max 8) "
        "at the unchanged production shape, selected by stack_topology drafter_selection from the "
        "master's roles.qwen38_27b_q8_local.drafters (DRAFT-SEL-1); Qwen3-VL-30B :8086 leaves the "
        "MI210 for a cold CPU placement until the 2nd MI210."
    ),
    "acknowledged": {
        "A-1": "Canonical speculative_decoding_policy (ratified_by operator 2026-07-31) AMENDED: "
               "production_recipe -> default_spec_type (n-gram composition scope), statement rewritten, "
               "exceptions.ingest_long_context closed, amended_on/amended_by_receipt added.",
        "A-2": "Reverses the 2026-09-22 ruling 'BOTH GPU ROLES STAY ON THE CARD' until MI210 #2.",
        "A-3": "Cold-CPU vision cpuset when started: cores 0-47 + SMT 96-143 (NPS4 nodes 0,1), -t 48, "
               "interleave=0,1, pre-evict 40 GiB/node; never started by default `start`; overlaps "
               "frontdoor :8070/:8080 when started; operator to confirm no DS41 A/B overlap.",
        "A-4": "While worker_vision is not HOT the API runs ORCHESTRATOR_VISION_VL_BACKEND=server: image "
               "requests fail fast instead of spawning an unpinned per-request llama-mtmd-cli 30B.",
        "A-5": "serving_shape.vram_non_kv_gib 36.34 is derived and UNVALIDATED; DFlash2 has never been "
               "served at the production shape; first window measures (PACKAGE.md 7.4).",
        "A-6": "Contention matrix DECLARED WITHDRAWAL: 3 worker_vision pairs -> unknown_pairs, "
               "topology_hash 5d772b2c4698b2ae -> 560d489bb6df16b9; NOT a re-measurement.",
        "A-7": "Orchestrator code: DRAFT-SEL-1 compiler/launcher, pipeline serving_shape_capacity step "
               "and lean bootstrap, VL-backend derivation, -ngld attestation (gitnexus HIGH on "
               "_launch_runtime_record; mitigation measured, PACKAGE.md section 5).",
        "A-8": "--spec-draft-n-max 8 kept (measured recipe); the kernel clamps it to 7 (block_size 8).",
    },
    "not_in_scope": [
        "retiring or deprecating Qwen3-VL-30B (weights stay; returns on MI210 #2)",
        "any production kernel change (v10 ffc1bac82 unchanged)",
        "re-benching the contention matrix",
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
