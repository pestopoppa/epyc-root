#!/bin/bash
# ratify_inference_gate_amendment_20260727.sh
#
# Replaces the per-run operator-approval clause in
# agents/shared/OPERATING_CONSTRAINTS.md § Inference and Benchmarks with a
# held-region-claim requirement. Rationale, full before/after, and the enabling
# change (A0) are in:
#   artifacts/operator/proposed_inference_gate_amendment_20260727.md
#
# PRECONDITION (already satisfied 2026-07-27): the region-claim wrapper exists
# and bench_canonical.sh acquires it. Applying this WITHOUT that would delete
# the last serializer between benches and orchestrator placements.
#
# Properties: content-pinned (pre + post sha256), idempotent (exit 0 if already
# applied), refuses on any drift, touches exactly one file, changes nothing else.
#
# NOTE ON HEAD PINNING: unlike the era/measurement ratify scripts, this does NOT
# pin repo HEAD — parallel sessions commit to this tree continuously and a HEAD
# pin would spuriously refuse. The property that matters here is that the file
# content is byte-exactly what this amendment was authored against, which the
# sha256 pins guarantee.
set -euo pipefail

# RATIFY_ROOT exists only so this script can be exercised against a sandbox copy
# before being run for real; unset, it behaves exactly as a hardcoded path.
ROOT="${RATIFY_ROOT:-/workspace}"
TARGET="agents/shared/OPERATING_CONSTRAINTS.md"
EXPECTED_PRE_SHA256=68c4c7a9b9ef7b601a067ed3fb9eb9dbd3baa8962c0264964fe4191002a95151
EXPECTED_POST_SHA256=bc290da20f5693ff34d59ebb91d78c989e5fbf8db4231f0a2529affaf300ad2e

cd "$ROOT"

if [[ ! -f "$TARGET" ]]; then
    printf 'Refusing: %s not found under %s\n' "$TARGET" "$ROOT" >&2
    exit 1
fi

current="$(sha256sum "$TARGET" | awk '{print $1}')"

if [[ "$current" == "$EXPECTED_POST_SHA256" ]]; then
    printf 'Amendment already applied; no files changed.\n'
    exit 0
fi

if [[ "$current" != "$EXPECTED_PRE_SHA256" ]]; then
    printf 'Refusing: %s is neither the expected pre- nor post-amendment state.\n' "$TARGET" >&2
    printf '  found    %s\n' "$current" >&2
    printf '  expected %s (pre)\n' "$EXPECTED_PRE_SHA256" >&2
    printf '  or       %s (post)\n' "$EXPECTED_POST_SHA256" >&2
    printf 'The file drifted since this amendment was authored. Re-derive it from\n' >&2
    printf 'artifacts/operator/proposed_inference_gate_amendment_20260727.md rather than forcing.\n' >&2
    exit 1
fi

if ! git diff --quiet -- "$TARGET" || ! git diff --cached --quiet -- "$TARGET"; then
    printf 'Refusing: %s has staged or unstaged changes.\n' "$TARGET" >&2
    exit 1
fi

python3 - "$TARGET" <<'PY'
import pathlib, sys

path = pathlib.Path(sys.argv[1])
text = path.read_text()

OLD = "- Never launch inference/benchmark runs (llama-bench/cli/server, run_benchmark.py, eval suites) without explicit per-run operator approval — a parallel agent or the autopilot may be running; concurrent runs silently poison both sides.\n"
NEW = (
    "- Never launch inference/benchmark runs (llama-bench/cli/server, run_benchmark.py, eval suites) "
    "without a held CPU-region claim covering the cores the run pins — use "
    "`region-lock run --cpu-list <list> -- <command>` (epyc-orchestrator/scripts/region-lock); "
    "`bench_canonical.sh` acquires it automatically and refuses to run unlocked. Concurrent runs on "
    "overlapping regions silently poison both sides — the claim, not a human, is what prevents that.\n"
    "- Operator approval is required only where the run's `operator_gates[]` names an actual trust "
    "boundary (era registry rows, MEASUREMENT.md, AutoPilot baseline applies, production "
    "freezes/cutovers, host reboots). Concurrency alone is never grounds for a human gate.\n"
    "- Co-residency policy lives in versioned, staleness-guarded data "
    "(`orchestration/contention_matrix.yaml`, guarded by `topology_hash`), never in prose.\n"
)

count = text.count(OLD)
if count != 1:
    sys.exit(f"Refusing: expected exactly 1 occurrence of the target clause, found {count}")

path.write_text(text.replace(OLD, NEW))
PY

applied="$(sha256sum "$TARGET" | awk '{print $1}')"
if [[ "$applied" != "$EXPECTED_POST_SHA256" ]]; then
    printf 'FAILED: post-state sha256 mismatch — reverting.\n' >&2
    printf '  got      %s\n' "$applied" >&2
    printf '  expected %s\n' "$EXPECTED_POST_SHA256" >&2
    git checkout -- "$TARGET"
    exit 1
fi

printf 'Applied. %s -> %s\n' "$TARGET" "$applied"
printf '\nFollow-ups (not done by this script):\n'
printf '  - memory: feedback_no_concurrent_inference is now obsolete; superseded by\n'
printf '    feedback_contention_is_scheduling_not_trust.\n'
printf '  - flip R2 in handoffs/active/session-bus-thin-dispatcher.md §Rider.\n'
printf '  - M4 go/no-go is unblocked once this is in.\n'
