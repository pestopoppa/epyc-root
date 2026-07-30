#!/bin/bash
# Operator ratification — MEASUREMENT.md trust boundary (human-amendment-only).
#
# v2 of mainA's ratify_p_bench_placement_1.sh (2026-07-30) — SUPERSEDES it; do
# not run the original. Same three amendments, three fixes:
#   - attest citation fully qualified (epyc-inference-research/...) and pointed
#     at the exact evidence file (prodopt_results.txt);
#   - rep-adequacy clause added to the exemplar's retraction comment (the
#     artifact is n=3 — honest cite; the reps rule governs decision use);
#   - stale closing NOTE dropped (MEASUREMENT.md + measurement/protocols/ were
#     committed & pushed at a9647a7a ~11:30Z; baseline is clean), post-apply
#     validation added instead.
#
# THREE amendments:
#   A. Register P-BENCH-PLACEMENT-1 (placement/concurrency axis none of
#      P-BENCH-1/2/3 constrain — the gap behind the 2026-07-30 N24 defect).
#   B. Conform P-BENCH-3 to the already-ratified §1: tok/s primary (a -np sweep
#      measures a MODEL INSTANCE); tasks/h retained as secondary readout.
#   C. Replace the claim-grammar exemplar citing retracted April evidence.
set -euo pipefail
cd /workspace

M=MEASUREMENT.md
ANNEX=measurement/protocols/bench-cpu.md
fail() { echo "ABORT: $*" >&2; exit 1; }

# ---- context checks -------------------------------------------------------
[ -f "$M" ]     || fail "$M not found"
[ -f "$ANNEX" ] || fail "$ANNEX not found — annex layout changed; re-derive this patch"
grep -q '^## 1. Metric scoping' "$M" \
  || fail "§1 Metric scoping not found — this patch assumes MEASUREMENT.md v2; re-derive"
grep -q '^| P-BENCH-4 | Single-instance server-native spec-dec' "$M" \
  || fail "P-BENCH-4 registry row not in the expected form — table restructured"
grep -q '^| P-BENCH-3 | Batched/slot decode' "$M" \
  || fail "P-BENCH-3 registry row not in the expected form"
grep -q '27.06 t/s' "$M" \
  || { grep -q 'P-BENCH-PLACEMENT-1' "$M" && echo "already applied — nothing to do" && exit 0 \
       || fail "27.06 exemplar absent but P-BENCH-PLACEMENT-1 not registered — re-derive"; }
[ -f repos/epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/prodopt_results.txt ] \
  || fail "attestation evidence file missing"
[ -f repos/epyc-inference-research/docs/protocols/numa-placement-measurement-protocol.md ] \
  || fail "full-contract doc missing"

echo "context OK — applying three amendments"

python3 - <<'PY'
import pathlib
m = pathlib.Path("MEASUREMENT.md"); t = m.read_text()

# --- A. register P-BENCH-PLACEMENT-1, immediately after P-BENCH-4 ----------
row = ("| P-BENCH-PLACEMENT-1 | CPU affinity / NUMA memory policy / mmap mode / "
       "instance count / slot concurrency | aggregate + per-stream decode tok/s (↑) "
       "| ✅ 2026-07-30 | B |\n")
if "P-BENCH-PLACEMENT-1" not in t:
    anchor = next(l for l in t.splitlines(keepends=True)
                  if l.startswith("| P-BENCH-4 | Single-instance server-native spec-dec"))
    t = t.replace(anchor, anchor + row, 1)

# --- B. P-BENCH-3 conforms to §1: tok/s primary, tasks/h retained ----------
old3 = "| P-BENCH-3 | Batched/slot decode (`-np N` sweep) | tasks/h + p50/p95 latency |"
new3 = ("| P-BENCH-3 | Batched/slot decode (`-np N` sweep) | aggregate + per-stream "
        "decode tok/s (↑) primary, per §1; p50/p95 latency (↓); tasks/h retained secondary |")
if old3 in t:
    t = t.replace(old3, new3, 1)

# --- C. exemplar citing retracted evidence --------------------------------
old_ex = "- ✅ `frontdoor decode 27.06 t/s [P-BENCH-2, n=5, 2026-04-26, attest a3f2]`"
new_ex = ("- ✅ `frontdoor decode 40.22 tok/s per-stream, spec-dec on (draft-mtp n_max 4), "
          "arm A2 [P-BENCH-PLACEMENT-1, n=3, 2026-07-30, attest "
          "epyc-inference-research/data/numa_placement/20260730-P-BENCH-PLACEMENT-1/prodopt_results.txt]`\n"
          "  <!-- Replaced 2026-07-30. The prior exemplar, `frontdoor decode 27.06 t/s\n"
          "  [P-BENCH-2, n=5, 2026-04-26, attest a3f2]`, was the NUMA_NODE0-arm figure from the\n"
          "  2026-04-17 head-to-head, invalid twice over: it predates the 2026-04-24 NPS4 reboot\n"
          "  (when `0-47,96-143` genuinely was one NUMA node) and its source CSV records\n"
          "  `spec == \"baseline\"`. The replacement is deliberately a PRODUCTION-RECIPE figure\n"
          "  (spec-dec on), not a baseline. Grammar note: ✅ marks the FIELDS as complete; rep\n"
          "  adequacy for a decision is still judged by the owning protocol's reps rule — this\n"
          "  n=3 figure is an anchor; effect claims against it need reps per P-BENCH-1. -->")
if old_ex in t:
    t = t.replace(old_ex, new_ex, 1)

m.write_text(t)
print("MEASUREMENT.md: A, B, C applied")
PY

# ---- B (cont.) — same conformance fix in the annex ------------------------
python3 - <<'PY'
import pathlib
p = pathlib.Path("measurement/protocols/bench-cpu.md"); t = p.read_text()
old = "tasks/hour AND per-stream p50/p95 latency, reported per-N."
new = ("aggregate + per-stream decode tok/s (primary, per MEASUREMENT.md §1 — a `-np` sweep "
       "measures a MODEL INSTANCE) AND per-stream p50/p95 latency, reported per-N; tasks/hour "
       "retained as a secondary orchestration-facing readout, never as the ranking key.")
if old in t:
    t = t.replace(old, new, 1); p.write_text(t); print("bench-cpu.md: P-BENCH-3 metric conformed to §1")
elif "never as the ranking key" in t:
    print("bench-cpu.md: already conformed")
else:
    raise SystemExit("ABORT: P-BENCH-3 metric sentence not found in annex — re-derive")
PY

# ---- A (cont.) — normative text into annex B (mainA's text, verbatim) -----
if ! grep -q "P-BENCH-PLACEMENT-1" "$ANNEX"; then
  cat >> "$ANNEX" <<'ANNEXEOF'

## P-BENCH-PLACEMENT-1 — NUMA placement and concurrency

Ratified 2026-07-30. Direction: higher-better, **tok/s** (per §1: this measures a model
instance, not an orchestrator configuration).

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
6. **Every arm runs the role's PRODUCTION acceleration recipe** (speculative decoding,
   draft model, draft_max) as recorded in the registry. A spec-dec-off baseline is not a
   production-usable figure and may not be reported as a headline; if a baseline is needed
   to isolate an effect, it is labelled as such and quoted alongside, never instead.

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
  echo "$ANNEX: P-BENCH-PLACEMENT-1 normative text appended"
fi

# ---- post-apply validation -----------------------------------------------
grep -q 'P-BENCH-PLACEMENT-1' "$M" && grep -q 'P-BENCH-PLACEMENT-1' "$ANNEX" \
  || fail "post-check: registration incomplete"
grep -q 'never as the ranking key' "$ANNEX" || fail "post-check: annex conformance missing"
# The ✅ exemplar LINE must be gone; the figure legitimately survives inside the
# retraction comment (historical record), so match the line form, not the string.
! grep -q '^- ✅ `frontdoor decode 27.06' "$M" || fail "post-check: retracted exemplar still present"
scripts/validate/check_claims_grammar.sh >/dev/null && echo "claims-grammar validator: clean"
echo
echo "=== applied diff (review, then commit) ==="
git --no-pager diff --stat -- "$M" "$ANNEX"
echo "APPLY COMPLETE — MEASUREMENT.md + annex now carry uncommitted ratified changes."
