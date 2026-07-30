#!/bin/bash
# Operator ratification — MEASUREMENT.md trust boundary (human-amendment-only).
#
# Written by mainA 2026-07-30 but NOT executed: MEASUREMENT.md and
# measurement/protocols/ are the measurement trust boundary and are
# human-amendment-only, so an agent must not apply these itself.
#
# THREE amendments, all justified by measurements taken 2026-07-30:
#   A. register P-BENCH-PLACEMENT-1 (new protocol; placement is an axis none of
#      P-BENCH-1/2/3 constrain, which is why the 2026-07-30 defect was reachable)
#   B. correct P-BENCH-3's metric from "tasks/h" to decode tok/s, per the
#      operator ruling that tasks/hour is an AutoPilot-only metric
#   C. replace the claim-grammar exemplar that cites retracted evidence
#
# CAUTION — the trust boundary is mid-restructure by another session:
#   * MEASUREMENT.md has uncommitted modifications
#   * measurement/protocols/ is entirely UNTRACKED (created 2026-07-30 10:32)
# This script therefore VERIFIES its expected context before touching anything
# and aborts if that session has moved things. It is idempotent: re-running
# after a successful pass is a no-op.
set -euo pipefail
cd /workspace

M=MEASUREMENT.md
ANNEX=measurement/protocols/bench-cpu.md
fail() { echo "ABORT: $*" >&2; exit 1; }

# ---- context checks -------------------------------------------------------
[ -f "$M" ]     || fail "$M not found"
[ -f "$ANNEX" ] || fail "$ANNEX not found — the annex layout changed; re-derive this patch"

grep -q '^| P-BENCH-4 | Single-instance server-native spec-dec' "$M" \
  || fail "registry index row for P-BENCH-4 not found in the expected form — table was restructured"
grep -q '^| P-BENCH-3 | Batched/slot decode' "$M" \
  || fail "P-BENCH-3 row not found in the expected form"
grep -q '^- ✅ `frontdoor decode 27.06 t/s' "$M" \
  || fail "the 27.06 exemplar is not where expected — already amended, or section moved"

echo "context OK — applying three amendments to the measurement trust boundary"

python3 - <<'PY'
import pathlib, sys

m = pathlib.Path("MEASUREMENT.md"); t = m.read_text()

# --- A. register P-BENCH-PLACEMENT-1, immediately after P-BENCH-4 ----------
row = ("| P-BENCH-PLACEMENT-1 | CPU affinity / NUMA memory policy / mmap mode / "
       "instance count / slot concurrency | aggregate + per-stream decode tok/s (↑) "
       "| ✅ 2026-07-30 | B |\n")
if "P-BENCH-PLACEMENT-1" not in t:
    anchor = next(l for l in t.splitlines(keepends=True)
                  if l.startswith("| P-BENCH-4 | Single-instance server-native spec-dec"))
    t = t.replace(anchor, anchor + row, 1)

# --- B. P-BENCH-3 metric: tasks/h is an AutoPilot-only metric --------------
old3 = "| P-BENCH-3 | Batched/slot decode (`-np N` sweep) | tasks/h + p50/p95 latency |"
new3 = ("| P-BENCH-3 | Batched/slot decode (`-np N` sweep) | aggregate + per-stream "
        "decode tok/s (↑); p50/p95 latency (↓) |")
if old3 in t:
    t = t.replace(old3, new3, 1)

# --- C. claim-grammar exemplar citing retracted evidence -------------------
old_ex = "- ✅ `frontdoor decode 27.06 t/s [P-BENCH-2, n=5, 2026-04-26, attest a3f2]`"
new_ex = ("- ✅ `frontdoor decode 23.36 ± 0.11 tok/s per-stream, spec-dec off "
          "[P-BENCH-PLACEMENT-1 arm A2, n=10, 2026-07-30, attest "
          "data/numa_placement/20260730-P-BENCH-PLACEMENT-1/]`\n"
          "  <!-- Replaced 2026-07-30. The prior exemplar, `frontdoor decode 27.06 t/s\n"
          "  [P-BENCH-2, n=5, 2026-04-26, attest a3f2]`, was the NUMA_NODE0-arm figure from\n"
          "  the 2026-04-17 head-to-head. That head-to-head is invalid twice over: it\n"
          "  predates the 2026-04-24 NPS4 reboot (when `0-47,96-143` genuinely was one NUMA\n"
          "  node) and its source CSV records `spec == \"baseline\"`. Grammar unchanged; only\n"
          "  the illustration was retracted evidence. -->")
if old_ex in t:
    t = t.replace(old_ex, new_ex, 1)

m.write_text(t)
print("MEASUREMENT.md: amendments A, B, C applied")
PY

# ---- D. normative text into annex B --------------------------------------
if ! grep -q "P-BENCH-PLACEMENT-1" "$ANNEX"; then
  cat >> "$ANNEX" <<'ANNEXEOF'

## P-BENCH-PLACEMENT-1 — NUMA placement and concurrency

Ratified 2026-07-30. Direction: higher-better, **tok/s**.

**Scope.** Any decision-gating throughput number that varies with, or depends on, CPU
affinity, NUMA memory policy, mmap mode, instance count, or slot concurrency.
Composite: `P-BENCH-1` governs the single-instance decode arm, `P-BENCH-2` the
multi-instance aggregate, `P-BENCH-3` any batched-slot rung. This protocol governs
**placement** and its interaction with concurrency — which none of them constrain, and
that gap is why the 2026-07-30 defect was reachable.

**Full contract.** `epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md`

**Mandatory gates.**
1. Cpuset expanded against the live NPS4 node map. A multi-node cpuset with no `numactl`
   policy is a REJECT, not a warning.
2. `drop_caches` before every placement arm, `cache_state` recorded, warm arms paired with
   cold. `numactl --interleave` binds at FIRST TOUCH only, so a warm arm silently
   re-measures the previous arm's placement.
3. Measured per-instance `pages_by_node` and `local_fraction` from `/proc/<pid>/numa_maps`,
   ARMED regardless of mmap mode. `--membind` under shared mmap is rejected as a placement
   arm — pages are placed once by the first faulter and later instances inherit that
   placement regardless of their own binding. Shared-mmap fleet arms record instance start
   order, because throughput depends on it.
4. Decode rate from `predicted_n` / `predicted_ms` only. A wall-clock rate is never a
   decode rate. Report per-stream and system-wide separately, with a skip audit.
5. Achieved concurrency measured per rung against nominal, and floored.

**Arms.** A0 production as-wired · A1 same cpuset + correct interleave · A2 full machine +
`interleave=all` · A3 N-instance fleet, shared mmap · A4 N-instance fleet, `--no-mmap`.
Interleaved; all five required. A1 is the bridge cell — drop it and policy is confounded
with cpuset.

**Anchor gate.** `np=1` is measured FIRST and compared against a recorded production anchor
for that model. Outside band ⇒ the run is VOID and may not be reported.

**Reps.** Per `P-BENCH-1`; report median + MAD.

A run missing measured locality is observation-grade at best and can never gate a decision.
No pre-ratification placement artifact may be retro-certified under this protocol.

**Claim grammar.**
`<value> tok/s <per-stream|aggregate(T=n)>, spec-dec <on|off>, arm <A0..A4> [P-BENCH-PLACEMENT-1, n=<reps>, <date>, attest <ref>]`
ANNEXEOF
  echo "$ANNEX: normative text appended"
fi

echo
echo "=== review before committing ==="
git --no-pager diff -- "$M" | head -60
echo
echo "measurement/protocols/ is UNTRACKED — 'git status' it before staging so you do not"
echo "sweep in the parallel session's in-flight restructure."
