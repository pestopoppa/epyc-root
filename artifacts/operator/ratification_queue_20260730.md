# Ratification queue — 2026-07-30

Every item below is a value that `P-BENCH-PLACEMENT-1` §7 or `MRG-1` §5 currently
carries as **TBD**. That matters more than it looks: a gate whose threshold is
unset cannot fail. Both documents are ratified, both describe checks, and none of
those checks can currently reject anything.

Each proposal states the measurement it is derived from, what it would have
caught today, and what it would cost if set wrong. Nothing here is applied —
`MEASUREMENT.md` and `measurement/protocols/` are human-amendment-only.

---

## A. Claim grammar — add a context-depth field

**Status: gap, not a threshold. Recommend ratifying first — it invalidates
nothing and prevents the largest class of error we hit today.**

The grammar is `(metric, protocol-id, n/reps, date, attestation ref)`, plus
`spec-dec` and `arm` for `P-BENCH-PLACEMENT-1`. There is **no context-depth
term**, so a decode rate is under-specified. Same model, same recipe, same
placement:

| frontdoor Qwen3.6-35B-A3B Q8_0 | decode | draft acceptance |
|---|---|---|
| 28-tok prompt | **40.22** | 0.746 |
| 570 tok | 28.96 | 0.500 |
| 8 754 tok | 25.18 | 0.478 |
| 34 938 tok | 17.23 | 0.429 |

A 2.3× spread driven purely by depth, compounded because acceptance decays with
it. **The currently-ratified exemplar carries the 28-token figure** and no depth
field — so it repeats the retracted `27.06` exemplar's failure mode by a
different mechanism.

**Proposed**: mandatory `@<measured prompt tokens>` on every decode-rate claim,
and re-base the exemplar on a representative depth so it models the right habit.

> `frontdoor decode 24.92 tok/s per-stream @14059-tok prompt, spec-dec on
> (draft-mtp n_max 4), arm A2 [P-BENCH-PLACEMENT-1, n=2, 2026-07-30, attest …]`

---

## B. Thresholds — proposed values with derivation

| # | Value | Proposed | Derivation | What it catches |
|---|---|---|---|---|
| 1 | `LOCALITY_THRESHOLD` (single-node `--membind`) | **0.95** | Measured 1.00 under `--no-mmap`+`--membind`; 0.256/0.256/0.242/0.269 under shared mmap. The two populations are separated by 0.7. | The shared-mmap defect (0.25) without tripping on allocator noise. Tool default 0.85 is loose; the salvage audit's 0.99 leaves no margin. |
| 2 | `INTERLEAVE_TOLERANCE` (multi-node) | **±25% relative** — each node within `[0.75/n, 1.25/n]` | Measured interleave gave 0.256/0.256/0.242/0.269 against an ideal 0.25, i.e. ≤7.6% relative deviation. | A 100%-on-one-node first-touch failure reads 400% of expected — rejected by a wide margin. Needed to arm the preflight hard-fail. |
| 3 | `ACHIEVED_CONCURRENCY_FLOOR` | **0.75** | Measured achieved/nominal: 1.00 at T=1, 0.86 at T=4, 0.80 at T=8, 0.77 at T=16, **0.47 at T=32**. | Admits T≤16, rejects T=32 — exactly where the E5 rungs stopped measuring what they claimed. |
| 4 | `STARVATION_THRESHOLD` | **0.25 × cell median** | Used descriptively in the slot-width study; separated cleanly (0% starved at short prompts, 25–29% at 8k). | Defines the label. Not a PASS condition on its own. |
| 5 | `MAX_STARVED_FRACTION` | **≤ 0.05** | 0% at short prompts across np=1/4/8; 25% at 8k np=4, 29% at 8k np=8. | Passes short-prompt batching, fails long-prompt batching — which is the real behaviour, not a conservative guess. |
| 6 | `MIN_P10_OVER_P50` | **≥ 0.50** | Measured 0.99 (short, np=8) vs **0.065** (8k, np=4) and 0.035 (8k, np=8). | The tail that the median hides. Two populations separated by an order of magnitude. |
| 7 | Anchor band-width policy | **median ± 10%, n ≥ 50** | The only existing anchor is frontdoor: median 35.7, band 35–40, n=154 — i.e. ≈ ±7% around the median. | Lets a new model establish an anchor at all. Currently impossible: there is a band for one role and no rule for deriving one. |

---

## C. Anchors that do not exist

`P-BENCH-PLACEMENT-1`'s anchor gate is mandatory and **three of four roles have
no anchor to gate against**. Only `frontdoor` has one (median 35.7 tok/s, n=154,
band 35–40), and it came from AutoPilot production traffic — a path independent
of the thing under test, which is what makes it valid.

Today's `prodopt` medians are **candidates at n=3, observation-grade, and
short-prompt** — they are not anchors and must not be adopted as such:

| role | candidate | why it is not yet an anchor |
|---|---|---|
| `worker_general` | 56.86 | n=3, 28-tok prompt, single invocation, no independent reproduction |
| `architect_general` | 24.00 | as above |
| `ingest_long_context` | 22.92 | as above |

**Proposed**: derive each from AutoPilot production traffic as frontdoor's was,
not from a bench invocation. Until then those three roles cannot pass Step 3 of
`MRG-1`, which is a true statement about our evidence, not a blocker to route
around.

---

## D. Not for ratification — engineering fixes that need a decision

1. **`placement_policy` vocabulary is quarter-shaped.** `SOLO_PREFER_FULL`
   ("concurrent requests spill to NUMA-disjoint quarters") and
   `BURST_PREFER_QUARTERS` both name a shape the new topology retires. The
   AXA3 autopilot knob surface exists (`config_applicator.py`
   `placement_policy_knobs`), so the lever is exposable — but its options would
   both mean "spill to quarters" on a machine with none. Generalise to
   shape-agnostic semantics before exposing `ingest_long_context` to autopilot.
2. **`affinity_preflight` self-disarms** — operator has chosen hard-fail; blocked
   on item B.2 above.
3. **A commit touching any `REQUIRED_SOURCE_ARTIFACTS` file silently blocks stack
   start** until the priors are recompiled, with no warning at commit time. Two
   occurrences today from two different sessions. Worth a pre-commit check.
