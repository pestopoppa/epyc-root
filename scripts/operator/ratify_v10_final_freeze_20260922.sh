#!/bin/bash
# ratify_v10_final_freeze_20260922.sh — sign the v9 -> v10 production kernel freeze.
#
#   Review:  bash scripts/operator/ratify_v10_final_freeze_20260922.sh --show
#   Apply:   bash scripts/operator/ratify_v10_final_freeze_20260922.sh --apply
#
# WHAT --apply DOES, in order. It refuses at the first failure and changes nothing:
#   1. VERIFIES the live freeze rather than trusting it — runs
#      scripts/session/verify_llama_cpp.sh, which now pins branch + commit + clean
#      tracked state on the frozen tree AND version + sha256 + ggml linkage on the
#      kernel store that actually serves.
#   2. STAMPS ratified_at into artifacts/operator/ratify_v10_final_freeze_20260922.json.
#   3. HASHES the stamped artifact and rewrites the freeze paragraph in CLAUDE.md
#      with that digest, so the governance text and the artifact can never drift.
#   4. PRINTS the commit command. It does not commit and it does not push.
#
# WHY A SCRIPT. The ratification artifact's own SHA-256 goes into CLAUDE.md, so the
# hash cannot be written by hand before the file it describes is final. Doing it in
# one transaction is the only way the two agree. CLAUDE.md's freeze paragraph and
# the attestation are human-only paths (MEASUREMENT.md trust boundary); this script
# is the operator's hands, not an agent's.
#
# ROLLBACK, if v10 ever has to be abandoned:
#   ln -sfn /mnt/raid0/llm/kernels/archive/cpu-20260810-0db32c06e/bin /mnt/raid0/llm/kernels/production/cpu
#   ln -sfn /mnt/raid0/llm/kernels/archive/gpu-20260810-0db32c06e/bin /mnt/raid0/llm/kernels/production/gpu
#   cd /mnt/raid0/llm/llama.cpp && git checkout production-consolidated-v9
# That path is not theoretical: it was executed for real on 2026-09-22 to revert a
# first promotion that had shipped a partial build.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ART="${REPO_ROOT}/artifacts/operator/ratify_v10_final_freeze_20260922.json"
CLAUDE_MD="${REPO_ROOT}/CLAUDE.md"

usage() { echo "usage: $0 [--show|--apply]" >&2; exit 2; }
[[ $# -eq 1 ]] || usage

case "$1" in
  --show)
    echo "Attestation: ${ART}"
    echo "Governance:  ${CLAUDE_MD}  (the '* v9 final freeze' paragraph is rewritten for v10)"
    echo
    cat "${ART}"
    echo
    echo "--- live state this would attest ---"
    bash "${REPO_ROOT}/scripts/session/verify_llama_cpp.sh" || true
    ;;

  --apply)
    [[ -f "${ART}" ]] || { echo "REFUSED: no attestation at ${ART}" >&2; exit 1; }

    echo "=== 1/4 verifying the live freeze ==="
    if ! bash "${REPO_ROOT}/scripts/session/verify_llama_cpp.sh"; then
      echo "REFUSED: the live kernel does not match the attestation. Nothing changed." >&2
      exit 1
    fi

    echo
    echo "=== 2/4 stamping ratified_at ==="
    python3 - "${ART}" <<'PY'
import json, sys, datetime
p = sys.argv[1]
d = json.load(open(p))
if not str(d.get("ratified_at", "")).startswith("PENDING"):
    print(f"REFUSED: already ratified at {d['ratified_at']}", file=sys.stderr)
    raise SystemExit(1)
d["ratified_at"] = datetime.datetime.now(datetime.timezone.utc).replace(
    microsecond=0).isoformat().replace("+00:00", "Z")
json.dump(d, open(p, "w"), indent=2)
open(p, "a").write("\n")
print(f"ratified_at = {d['ratified_at']}")
PY

    echo
    echo "=== 3/4 rewriting the CLAUDE.md freeze paragraph ==="
    python3 - "${ART}" "${CLAUDE_MD}" <<'PY'
import hashlib, re, sys
art, md = sys.argv[1], sys.argv[2]
digest = hashlib.sha256(open(art, "rb").read()).hexdigest()
s = open(md).read()

new = (
    "**2026-09-22 v10 final freeze**: production runs ONE kernel, "
    "**production-consolidated-v10** (canonical tree `/mnt/raid0/llm/llama.cpp`, frozen at "
    "`ffc1bac82eeca6f9099e1ccd9ba49703c460a115`, `llama-server --version` reports `10303`). "
    "Ratification: [`artifacts/operator/ratify_v10_final_freeze_20260922.json`]"
    "(artifacts/operator/ratify_v10_final_freeze_20260922.json), SHA-256 `" + digest + "`. "
    "v9 (`0db32c06e3e550065b78311a6031ef3dd2c4f27c`, binary `10125`) is the rollback anchor, "
    "archived under `kernels/archive/{cpu,gpu}-20260810-0db32c06e`. "
    "**v10 is the first production kernel served from the KERNEL STORE, not from the source "
    "tree's own `build/` and `build-hip/`** — `kernels/production/{cpu,gpu}` are the serving "
    "path, the frozen tree's in-tree build dirs still hold the v9 binaries, and anything that "
    "hardcodes `llama.cpp/build/bin` is reading a kernel that serves nothing. "
    "`scripts/session/verify_llama_cpp.sh` enforces branch, commit and clean tracked state on "
    "the tree plus version, digest and ggml linkage on the store; "
    "`scripts/session/verify_kernel_store.sh` walks the store's own integrity. "
    "**ik_llama.cpp is fully deprecated as a serving path** (tree on disk = reference/"
    "measurement instrument only)."
)

pat = re.compile(r"^\*\*2026-08-11 v9 final freeze\*\*: .*$", re.M)
if not pat.search(s):
    print("REFUSED: could not find the v9 freeze paragraph in CLAUDE.md", file=sys.stderr)
    raise SystemExit(1)
s = pat.sub(lambda _: new, s, count=1)

# The iqk line names its inheritance chain; extend it rather than restate it.
s = s.replace(
    "**iqk coverage (v9, inherited from v8)**:",
    "**iqk coverage (v10, inherited unchanged from v9/v8)**:", 1)

# The kernel-set paragraph names the llama.cpp branch; the speech branches are untouched.
s = s.replace(
    "**2026-08-11 production kernel set**: the freeze covers a production **KERNEL SET**, "
    "not one kernel — `llama.cpp` @ `production-consolidated-v9`,",
    "**2026-09-22 production kernel set**: the freeze covers a production **KERNEL SET**, "
    "not one kernel — `llama.cpp` @ `production-consolidated-v10`,", 1)

s = s.replace(
    "**Production kernels are FROZEN.** `production-consolidated-v9` (and future `-v10`, …)",
    "**Production kernels are FROZEN.** `production-consolidated-v10` (and future `-v11`, …)", 1)

open(md, "w").write(s)
print(f"CLAUDE.md freeze block -> v10, attestation SHA-256 {digest}")
PY

    echo
    echo "=== 4/4 done — review, then commit ==="
    echo
    git -C "${REPO_ROOT}" --no-pager diff --stat -- CLAUDE.md artifacts/operator/ratify_v10_final_freeze_20260922.json
    cat <<'MSG'

Commit with (pathspec-limited, shared tree):

  git add -- CLAUDE.md \
             artifacts/operator/ratify_v10_final_freeze_20260922.json
  git commit -m "FREEZE-V10: ratify the v9->v10 production kernel promotion"

MSG
    ;;

  *) usage ;;
esac
