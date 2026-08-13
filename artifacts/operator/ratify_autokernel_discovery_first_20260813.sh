#!/bin/bash
# RATIFICATION — AutoKernel discovery-first search policy (P-AK-SEARCH-1-A2)
#
# RUN BY THE OPERATOR ONLY.  The default is a read-only dry run:
#
#   bash artifacts/operator/ratify_autokernel_discovery_first_20260813.sh
#   bash artifacts/operator/ratify_autokernel_discovery_first_20260813.sh --apply
#
# The apply is deliberately narrow: it appends P-AK-SEARCH-1-A2 to Annex K and
# the narrowing cross-reference required by Annex K's admission test to Annex B.
# It does not execute AutoKernel, signal a process, modify a kernel tree, or
# authorize promotion.  Running with --apply is the operator's ratification.
set -euo pipefail

usage() {
    cat <<'EOF'
usage: ratify_autokernel_discovery_first_20260813.sh [--apply]

With no argument, print the exact proposed Annex K and Annex B diffs and write
nothing.  --apply performs the human-owned amendment and emits its consolidated
ratification receipt.
EOF
}

APPLY=0
case "${1:-}" in
    "") ;;
    --apply) APPLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { usage >&2; exit 2; }

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
ANNEX_K_REL="measurement/protocols/kernel-research.md"
ANNEX_B_REL="measurement/protocols/bench-cpu.md"
SCRIPT_REL="artifacts/operator/ratify_autokernel_discovery_first_20260813.sh"
RECEIPT_REL="artifacts/operator/receipts/autokernel-discovery-first-20260813.receipt.json"
ANNEX_K="$ROOT/$ANNEX_K_REL"
ANNEX_B="$ROOT/$ANNEX_B_REL"
RECEIPT="$ROOT/$RECEIPT_REL"
K_MARKER='## P-AK-SEARCH-1-A2 — discovery-first screening and confirmation separation (RATIFIED 2026-08-13)'
# Literal Markdown code span; the backticks are data, not shell expansion.
# shellcheck disable=SC2016
B_MARKER='**AutoKernel narrowing cross-reference (2026-08-13, `P-AK-SEARCH-1-A2`).**'
PREIMAGE_COMMIT="26b69cbcdbd0ce80823ad5b8fe701cae1d294955"
K_BEFORE_SHA256="2305e17f598f024b26a34b86373c5b3f81b52d39172baedc528a25b79716c6bd"
B_BEFORE_SHA256="090be6ea5cce268dfa9b7691dc116111e153d78de1cea7903bf3928f9dc8cc93"
K_REFUSED_SHA256="0d49f66dabe696f04075b6bb1673b03427a8733c222db8e9661c1e86175e7e61"
B_REFUSED_SHA256="2cc09d782ace0f246cf3c23c6c534006cda78001c071d1e70d2ff55d2442b1c7"
K_AFTER_SHA256="16bf2d373cfa6a85bcdf21ffdbaf9fd6090fe5a3030f31ed622cbe605b116e43"
B_AFTER_SHA256="a7e27f50c6690d588a6c66d575e1d5b7453f3e78835d47a4ddda35ba15f8e4e2"

fail() {
    printf 'REFUSING: %s\n' "$1" >&2
    exit 1
}

for path in "$ANNEX_K" "$ANNEX_B" "$ROOT/scripts/operator/lib/ratify_receipt.sh"; do
    [[ -f "$path" ]] || fail "required file is missing: $path"
done

has_k=0
has_b=0
RECOVERY=0
grep -qF "$K_MARKER" "$ANNEX_K" && has_k=1
grep -qF "$B_MARKER" "$ANNEX_B" && has_b=1
if (( has_k != has_b )); then
    fail "partial prior apply: Annex K marker=$has_k, Annex B marker=$has_b"
fi
if (( has_k == 1 )); then
    [[ -f "$RECEIPT" ]] || fail \
        "amendment markers exist without a consolidated receipt; do not treat this state as ratified"
    receipt_verdict="$(python3 - "$RECEIPT" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    receipt = json.load(handle)
print(receipt.get("verdict", ""))
PY
    )"
    if [[ "$receipt_verdict" == "RATIFIED" ]]; then
        python3 - "$ROOT" "$RECEIPT" \
            "$K_BEFORE_SHA256" "$B_BEFORE_SHA256" \
            "$K_AFTER_SHA256" "$B_AFTER_SHA256" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import sys

root, receipt_path = Path(sys.argv[1]), Path(sys.argv[2])
k_before, b_before, k_after, b_after = sys.argv[3:]
expected = {
    "measurement/protocols/kernel-research.md": (k_before, k_after),
    "measurement/protocols/bench-cpu.md": (b_before, b_after),
}
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
if (receipt.get("verdict") != "RATIFIED"
        or receipt.get("ratification_id") != "autokernel-discovery-first-20260813"
        or receipt.get("protocol_id") != "P-AK-SEARCH-1"):
    raise SystemExit("REFUSING: existing RATIFIED receipt identity does not match this amendment")
diffs = receipt.get("state_diff")
if not isinstance(diffs, list) or len(diffs) != 2:
    raise SystemExit("REFUSING: existing RATIFIED receipt lacks the exact protected state diffs")
seen = {}
for item in diffs:
    if not isinstance(item, dict) or item.get("path") not in expected:
        raise SystemExit("REFUSING: existing RATIFIED receipt carries an unexpected state diff")
    rel = item["path"]
    pair = (item.get("sha256_before"), item.get("sha256_after"))
    if pair != expected[rel]:
        raise SystemExit(f"REFUSING: existing RATIFIED receipt hashes for {rel} do not match")
    seen[rel] = pair
if set(seen) != set(expected):
    raise SystemExit("REFUSING: existing RATIFIED receipt is missing a protected state diff")
for rel, (_, after) in expected.items():
    actual = sha256((root / rel).read_bytes()).hexdigest()
    if actual != after:
        raise SystemExit(
            f"REFUSING: ratified protected path {rel} drifted: expected {after}, got {actual}")
PY
        printf 'Already ratified: both amendments and a RATIFIED receipt are present.\n'
        exit 0
    fi
    [[ "$receipt_verdict" == "REFUSED" ]] || fail \
        "amendment markers carry receipt verdict '$receipt_verdict', not RATIFIED or recoverable REFUSED"
    RECOVERY=1
fi

if (( APPLY && ! RECOVERY )); then
    dirty="$(git -C "$ROOT" status --porcelain -- "$ANNEX_K_REL" "$ANNEX_B_REL")"
    [[ -z "$dirty" ]] || fail "protected target already has local changes: $dirty"
fi

tmp_dir="$(mktemp -d -t ratify-autokernel-discovery-first-XXXXXX)"
cleanup() {
    [[ -z "${RECEIPT_PRE_STATE:-}" ]] || rm -f -- "$RECEIPT_PRE_STATE"
    rm -rf -- "$tmp_dir"
}
trap cleanup EXIT

RECOVERY_STAGE=""
if (( RECOVERY )); then
    RECOVERY_STAGE="$(python3 - "$ROOT" "$RECEIPT" \
        "$K_BEFORE_SHA256" "$B_BEFORE_SHA256" \
        "$K_REFUSED_SHA256" "$B_REFUSED_SHA256" \
        "$K_AFTER_SHA256" "$B_AFTER_SHA256" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
receipt_path = Path(sys.argv[2])
k_before, b_before, k_refused, b_refused, k_corrected, b_corrected = sys.argv[3:]
before = {
    "measurement/protocols/kernel-research.md": k_before,
    "measurement/protocols/bench-cpu.md": b_before,
}
states = {
    "refused_draft": {
        "measurement/protocols/kernel-research.md": k_refused,
        "measurement/protocols/bench-cpu.md": b_refused,
    },
    "corrected_retry": {
        "measurement/protocols/kernel-research.md": k_corrected,
        "measurement/protocols/bench-cpu.md": b_corrected,
    },
}

def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()

current = {rel: digest(root / rel) for rel in before}
matching = [name for name, values in states.items() if current == values]
if len(matching) != 1:
    detail = ", ".join(f"{rel}={value}" for rel, value in current.items())
    raise SystemExit(f"REFUSING: protected paths are not an exact recoverable state: {detail}")
stage = matching[0]
expected = {rel: (before[rel], states[stage][rel]) for rel in before}

try:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
except (OSError, ValueError) as exc:
    raise SystemExit(f"REFUSING: prior REFUSED receipt is unreadable: {exc}")
if (receipt.get("verdict") != "REFUSED"
        or receipt.get("ratification_id") != "autokernel-discovery-first-20260813"
        or receipt.get("protocol_id") != "P-AK-SEARCH-1"):
    raise SystemExit("REFUSING: prior receipt identity is not the expected REFUSED ratification")
diffs = receipt.get("state_diff")
if not isinstance(diffs, list) or len(diffs) != 2:
    raise SystemExit("REFUSING: prior receipt does not carry exactly the two protected state diffs")
seen = {}
for item in diffs:
    if not isinstance(item, dict) or item.get("path") not in expected:
        raise SystemExit("REFUSING: prior receipt carries an unexpected protected state diff")
    rel = item["path"]
    pair = (item.get("sha256_before"), item.get("sha256_after"))
    if pair != expected[rel]:
        raise SystemExit(f"REFUSING: prior receipt hashes for {rel} do not match this amendment")
    seen[rel] = pair
if set(seen) != set(expected):
    raise SystemExit("REFUSING: prior receipt is missing a protected state diff")
validation = receipt.get("sections", {}).get("validation", {})
if validation.get("verdict") != "FAIL":
    raise SystemExit("REFUSING: recovery is only valid for the exact failed-validation state")
print(stage)
PY
    )"
    printf 'Verified exact REFUSED amendment state (%s) and protected before/after hashes.\n' \
        "$RECOVERY_STAGE"
    python3 - "$ROOT" "$PREIMAGE_COMMIT" "$tmp_dir" \
        "$ANNEX_K_REL" "$ANNEX_B_REL" "$K_BEFORE_SHA256" "$B_BEFORE_SHA256" <<'PY'
from hashlib import sha256
from pathlib import Path
import subprocess
import sys

root, commit, output = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
items = ((sys.argv[4], sys.argv[6], "kernel-research.preimage.md"),
         (sys.argv[5], sys.argv[7], "bench-cpu.preimage.md"))
for rel, expected, name in items:
    data = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{rel}"],
        check=True, capture_output=True).stdout
    actual = sha256(data).hexdigest()
    if actual != expected:
        raise SystemExit(
            f"REFUSING: reconstructed preimage {rel} expected {expected}, got {actual}")
    (output / name).write_bytes(data)
PY
    K_SOURCE="$tmp_dir/kernel-research.preimage.md"
    B_SOURCE="$tmp_dir/bench-cpu.preimage.md"
else
    K_SOURCE="$ANNEX_K"
    B_SOURCE="$ANNEX_B"
fi

python3 - "$K_SOURCE" "$B_SOURCE" "$tmp_dir/kernel-research.md" "$tmp_dir/bench-cpu.md" <<'PY'
from pathlib import Path
import sys

k_path, b_path, k_out, b_out = map(Path, sys.argv[1:])
k_text = k_path.read_text(encoding="utf-8")
b_text = b_path.read_text(encoding="utf-8")

k_heading = "## P-AK-SEARCH-1 — Kernel-candidate search authority (RATIFIED 2026-08-03)\n"
a1_xref = """**NARROWED 2026-08-03 by `P-AK-SEARCH-1-A1`** (this annex, below): a banked candidate additionally requires a mechanism explanation backed by bytes, FLOPs, counters or a clean A/B; and a backend-capability claim additionally requires both correctness and performance evidence. This protocol as stated below is purely statistical and does not carry either requirement on its own.\n"""
a2_xref = """
**NARROWED 2026-08-13 by `P-AK-SEARCH-1-A2`** (this annex, below): AutoKernel search is discovery-first. A sealed exact-frame O(1) baseline bank plus three candidate-only samples may nominate a non-promotable top-K before strict paired confirmation; the bank binds the complete anchor runtime parameter/environment surface and every screen proves that its declared factor is the sole intended difference. Ordinary service, agent, build, filesystem and host-load activity is recorded noise and never an AutoKernel search blocker. Only competing model inference overlapping the held compute claim is an environmental blocker. Correctness and identity gates remain, and promotion remains solely under the owning Annex B, Q, G or S release protocol.\n"""

a2_heading = "## P-AK-SEARCH-1-A2 — discovery-first screening and confirmation separation (RATIFIED 2026-08-13)"
a2 = r"""
## P-AK-SEARCH-1-A2 — discovery-first screening and confirmation separation (RATIFIED 2026-08-13)

Appended to Annex K as a narrowing of `P-AK-SEARCH-1`, which it does not restate or replace. It
narrows the calibration, paired-block, anchor-motion and generic host-health requirements only as
specified below, and leaves the owning release protocols untouched.

**Discovery dominates.** AutoKernel T0-T2 search begins with the cheapest honest falsification
capable of finding a useful direction. It does not spend fully paired confirmation cost on every
candidate merely to decide which candidates deserve confirmation.

### Two modes, two authorities

1. **Discovery screen.** The controller MAY create one immutable, content-addressed baseline bank
   from exactly three anchor invocations and reuse it across any number of candidates while its
   common frame remains byte-identical. Baseline work is therefore O(1) in the number of candidates.
   Each candidate screen executes exactly three candidate-only samples and zero new anchor samples.
   Creating the bank requires the held compute claim, an inference-exclusion witness, and exact
   recipe, model, evaluator/runtime-source, source-commit, binary, linkage, backend, phase, shape,
   frequency and power-envelope identity **plus the complete anchor command's runtime parameter and
   environment surface** (including every `GGML_*` value such as `GGML_IQK`). It does **not** require
   completed strict T1 calibration, its paired-block count, or its anchor-motion settling rule. Any
   identity drift closes the bank; it is never relabelled or recalibrated in place.
2. **Sole-factor attestation.** Before spending a candidate sample, the screen binds the complete
   candidate command runtime parameter/environment surface and the declared experimental factor,
   then proves that every anchor/candidate semantic identity difference is an intended manifestation
   of that one factor. For a runtime-parameter experiment, exactly the declared runtime field differs
   and its two values MUST be unequal; `anchor GGML_IQK=1` versus `candidate GGML_IQK=1` is an invalid
   no-op, not a screen. A registered runtime-parameter screen MUST execute both arms with the exact
   same sealed instrument executable and DSO set and performs no candidate worktree or build; after
   normalizing arm-local path spelling and non-experimental seed bookkeeping, normalized argv,
   environment, recipe, model, phase, shape and repetition semantics MUST match except for the one
   declared unequal runtime field. A source-changing screen is a separate mode: runtime semantics
   MUST be identical and only its declared content-addressed source commit, executable, DSO and
   linkage identity may differ. A zero-factor or multi-factor comparison is `INVALID` and consumes
   no nomination authority.
3. **Nomination and confirmation.** A discovery screen MAY form an advisory top-K nomination set.
   Every screen and every ordering derived from it is non-promotable and is not a claim: it cannot
   bank a candidate, enter a champion lineage, contribute to readiness, or appear as a registry or
   headline result. Only nominees consume the original protocol's fully paired, randomized,
   calibrated selection/confirmation path. Banking, composition, readiness and any durable
   performance statement require that strict paired evidence; discovery evidence is never upgraded
   or pooled into it.

### Interference and coexistence

Ordinary services, other agents, their builds, filesystem activity, scheduler traffic and ordinary
host load are **recorded measurement noise**. They MUST NOT cause AutoKernel search to wait, refuse,
abort, stop, pause a foreign worker, or request a quiet host. The controller works with that noise;
it may use it to widen uncertainty or decline to nominate a candidate, but never to manufacture an
environmental blocker.

The sole environmental-interference blocker is **witnessed competing model inference whose compute
footprint overlaps the compute claim held by the AutoKernel measurement**. Model inference on
unclaimed compute is outside that blocker. Correctness, oracle integrity, exact source/binary/linkage
identity, recipe/evaluator identity, frequency and power envelopes, and resource-claim open/close
witnesses remain mandatory gates; their failure is a correctness or instrument-invalidity result,
not ordinary-machine interference.

**No process-signalling authority.** Nothing in this amendment authorizes AutoKernel or an agent to
send `SIGTSTP`, `SIGSTOP`, `SIGCONT`, `SIGTERM`, `SIGKILL`, a terminal Ctrl-Z, or any other control
signal to a process or tmux pane it did not launch and record as its own. Discovery coexists with
foreign work. A competing-inference witness causes the affected phase to checkpoint and release or
wait on its own claimed resource; it never authorizes suppressing the competing process.

### Durable phase resume

Every discovery, build, correctness, nomination and confirmation phase persists a self-identifying
completion record at its boundary before the next phase begins. After interruption, the controller
reuses only sealed completed phases whose full identity still matches and resumes at the earliest
incomplete phase. It MUST NOT restart a campaign or discard completed work solely because ordinary
machine noise changed. A competing-inference pause is likewise resumable after a fresh overlap
witness passes.

### Record class and release boundary

This amendment emits a **screening verdict that is not a claim**. Its grammar is:

`<metric> <three candidate samples>, vs sealed baseline <baseline_sha256[:12]> — DISCOVERY SCREEN,
NOT A CLAIM [P-AK-SEARCH-1-A2, category=CANDIDATE, candidate_invocations=3,
anchor_invocations=0, nomination=top_k, promotable=false, res=<claim_receipt>,
inference=<witness_ref>, frame=<frame_sha256[:12]>, factor=<declared_factor>,
anchor_runtime=<anchor_runtime_sha256[:12]>, candidate_runtime=<candidate_runtime_sha256[:12]>,
delta_attest=<sole_factor_attestation_ref>, raw=<raw_samples_ref>, YYYY-MM-DD]`.

Promotion is unchanged. A nominee must be re-measured through fully paired confirmation and then
satisfy its owning Annex B, Q, G or S release protocol. This amendment grants no T3, production,
freeze, cutover, registry, waiver or deployment authority and creates no retro-certification route.

**Prospective.** This amendment applies only to phases started after its ratification timestamp.
Earlier screening artifacts remain observations under the authority they had when produced.
"""

b_anchor = """- **Preconditions (all enforced or attested)**: no concurrent inference (`pgrep llama` zombie
  check; benches require a region claim per `feedback_no_concurrent_inference` as amended
  07-27); host-health tier — uptime ≤1wk → `drop_caches` + **NUMA-interleave re-warm** (never a
  bare re-read; `feedback_drop_caches_numa_eviction`), ≥1wk → reboot required
  (`feedback_host_throttle_check`); governor + `kernel.numa_balancing` checked per session (it
  self-resets); THP pool noted (production `--no-mmap --mlock` depletes it).\n"""
b_xref = """
**AutoKernel narrowing cross-reference (2026-08-13, `P-AK-SEARCH-1-A2`).** For AutoKernel T0-T2
search only, Annex K now owns a discovery-screen mode: a sealed exact-frame three-anchor baseline
bank is reused with exactly three candidate-only samples; ordinary service, agent, build,
filesystem and host-load activity is recorded noise and never blocks search; only competing model
inference overlapping the held compute claim is an environmental blocker. The bank binds the full
anchor runtime parameter/environment surface and each screen proves its declared factor is the sole
intended semantic anchor/candidate difference. A runtime-parameter screen uses one sealed instrument
binary/DSO set for both arms and performs no candidate build; a source-changing screen is a separate
mode whose content-addressed source/build identity may differ while normalized runtime semantics
remain fixed. Same-valued or multi-factor screens are invalid. Strict paired confirmation and every
Annex B release or promotion requirement remain unchanged.

"""

for label, text, anchor in (
    ("Annex K heading", k_text, k_heading),
    ("Annex K A1 cross-reference", k_text, a1_xref),
    ("Annex K A2 insertion point", k_text, "\n\n\n## P-AK-SEARCH-1 — owning-annex set extended 2026-08-03 (Annex S)"),
    ("Annex B precondition", b_text, b_anchor),
):
    if text.count(anchor) != 1:
        raise SystemExit(f"REFUSING: {label} must occur exactly once; found {text.count(anchor)}")

if a2_heading in k_text or "**AutoKernel narrowing cross-reference (2026-08-13" in b_text:
    raise SystemExit("REFUSING: amendment marker appeared during fresh transformation")

k_text = k_text.replace(a1_xref, a1_xref + a2_xref, 1)
k_text = k_text.replace(
    "\n\n\n## P-AK-SEARCH-1 — owning-annex set extended 2026-08-03 (Annex S)",
    "\n\n" + a2 + "\n\n## P-AK-SEARCH-1 — owning-annex set extended 2026-08-03 (Annex S)",
    1,
)
b_text = b_text.replace(b_anchor, b_anchor + b_xref, 1)

if k_text.count(a2_heading) != 1 or b_text.count(
        "**AutoKernel narrowing cross-reference (2026-08-13, `P-AK-SEARCH-1-A2`).**") != 1:
    raise SystemExit("REFUSING: transformed documents do not contain exactly one marker each")

k_out.write_text(k_text, encoding="utf-8")
b_out.write_text(b_text, encoding="utf-8")
PY

if (( ! APPLY )); then
    if (( RECOVERY )); then
        printf '%s\n' 'DRY RUN — no files written.'
        printf '%s\n' 'Exact prior amendment hashes and REFUSED receipt verified.'
        printf '%s\n' 'The apply will preserve the refused attempt, establish the exact corrected'
        printf '%s\n' 'sole-factor/runtime-bound amendment, rerun current focused validation, and'
        printf '%s\n' 'emit a new consolidated receipt.'
        if [[ "$RECOVERY_STAGE" == "refused_draft" ]]; then
            diff -u --label "a/$ANNEX_K_REL (REFUSED draft)" --label "b/$ANNEX_K_REL (corrected)" \
                "$ANNEX_K" "$tmp_dir/kernel-research.md" || [[ $? -eq 1 ]]
            diff -u --label "a/$ANNEX_B_REL (REFUSED draft)" --label "b/$ANNEX_B_REL (corrected)" \
                "$ANNEX_B" "$tmp_dir/bench-cpu.md" || [[ $? -eq 1 ]]
        else
            printf '%s\n' 'Protected paths already match the corrected post-state; validation will retry.'
        fi
        printf '\nCorrected post-state SHA-256:\n  %s  %s\n  %s  %s\n' \
            "$(sha256sum "$tmp_dir/kernel-research.md" | awk '{print $1}')" "$ANNEX_K_REL" \
            "$(sha256sum "$tmp_dir/bench-cpu.md" | awk '{print $1}')" "$ANNEX_B_REL"
        printf '\nRecover with:\n  bash %q --apply\n' "$ROOT/$SCRIPT_REL"
        exit 0
    fi
    printf '%s\n' 'DRY RUN — no files written. Proposed protected-path diff follows:'
    diff -u --label "a/$ANNEX_K_REL" --label "b/$ANNEX_K_REL" \
        "$ANNEX_K" "$tmp_dir/kernel-research.md" || [[ $? -eq 1 ]]
    diff -u --label "a/$ANNEX_B_REL" --label "b/$ANNEX_B_REL" \
        "$ANNEX_B" "$tmp_dir/bench-cpu.md" || [[ $? -eq 1 ]]
    printf '\nApply exactly this bundle with:\n  bash %q --apply\n' "$ROOT/$SCRIPT_REL"
    exit 0
fi

# Capture the exact two protected preimages before either amendment is written.
source "$ROOT/scripts/operator/lib/ratify_receipt.sh"
if (( RECOVERY )); then
    preimage_root="$tmp_dir/preimage"
    mkdir -p -- "$preimage_root/measurement/protocols"
    python3 - "$ROOT" "$PREIMAGE_COMMIT" "$preimage_root" \
        "$ANNEX_K_REL" "$ANNEX_B_REL" "$K_BEFORE_SHA256" "$B_BEFORE_SHA256" <<'PY'
from hashlib import sha256
from pathlib import Path
import subprocess
import sys

root, commit, output = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
items = ((sys.argv[4], sys.argv[6]), (sys.argv[5], sys.argv[7]))
for rel, expected in items:
    data = subprocess.run(
        ["git", "-C", str(root), "show", f"{commit}:{rel}"],
        check=True, capture_output=True).stdout
    actual = sha256(data).hexdigest()
    if actual != expected:
        raise SystemExit(
            f"REFUSING: reconstructed preimage {rel} expected {expected}, got {actual}")
    target = output / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
PY
    RECEIPT_PRE_STATE="$(mktemp -t ratify-pre-XXXXXX.json)"
    python3 "$RECEIPT_TOOL" capture --repo-root "$preimage_root" \
        --state "$ANNEX_K_REL" --state "$ANNEX_B_REL" --out "$RECEIPT_PRE_STATE"
    refused_sha="$(sha256sum "$RECEIPT" | awk '{print $1}')"
    refused_archive="$ROOT/artifacts/operator/receipts/autokernel-discovery-first-20260813.refused-${refused_sha:0:12}.receipt.json"
    python3 - "$RECEIPT" "$refused_archive" <<'PY'
from pathlib import Path
import sys
source, target = map(Path, sys.argv[1:])
data = source.read_bytes()
if target.exists() and target.read_bytes() != data:
    raise SystemExit(f"REFUSING: prior-attempt archive already exists with different bytes: {target}")
target.write_bytes(data)
PY
else
    receipt_capture "$ANNEX_K_REL" "$ANNEX_B_REL"
fi

(
    cd "$ROOT"
    python3 - "$tmp_dir/kernel-research.md" "$tmp_dir/bench-cpu.md" <<'PY'
from pathlib import Path
import sys

k_stage, b_stage = map(Path, sys.argv[1:])
with open("measurement/protocols/kernel-research.md", "wb") as handle:
    handle.write(k_stage.read_bytes())
with open("measurement/protocols/bench-cpu.md", "wb") as handle:
    handle.write(b_stage.read_bytes())
PY
)

[[ "$(grep -cF "$K_MARKER" "$ANNEX_K")" == 1 ]] || fail "Annex K post-state marker count is not one"
[[ "$(grep -cF "$B_MARKER" "$ANNEX_B")" == 1 ]] || fail "Annex B post-state marker count is not one"
[[ "$(sha256sum "$ANNEX_K" | awk '{print $1}')" == "$K_AFTER_SHA256" ]] || \
    fail "Annex K post-state bytes differ from the reviewed amendment"
[[ "$(sha256sum "$ANNEX_B" | awk '{print $1}')" == "$B_AFTER_SHA256" ]] || \
    fail "Annex B post-state bytes differ from the reviewed amendment"

# The evidence is the already-landed prospective implementation and its focused
# current regression tests.  The receipt hashes and durability-checks each file.
RATIFY_EVIDENCE="scripts/kernel_rnd/autokernel/execution/screening_baseline.py scripts/kernel_rnd/autokernel/campaign.py scripts/kernel_rnd/autokernel/execution/test_screening_baseline.py scripts/kernel_rnd/autokernel/test_campaign.py"
RATIFY_VALIDATION="cd /mnt/raid0/llm/epyc-inference-research && python3 -m unittest scripts.kernel_rnd.autokernel.execution.test_screening_baseline scripts.kernel_rnd.autokernel.test_campaign"
export RATIFY_EVIDENCE RATIFY_VALIDATION

receipt_emit autokernel-discovery-first-20260813 P-AK-SEARCH-1 \
    --script "$SCRIPT_REL" \
    --out "$RECEIPT"

printf '\nRATIFIED by operator apply. Protected paths amended:\n  %s\n  %s\n' \
    "$ANNEX_K_REL" "$ANNEX_B_REL"
printf 'Consolidated receipt: %s\n' "$RECEIPT_REL"
printf 'No process was signalled and no AutoKernel or release action was executed.\n'
