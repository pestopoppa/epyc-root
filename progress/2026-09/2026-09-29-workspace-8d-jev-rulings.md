# 2026-09-29 — workspace-8d (Jev-techniques operator rulings Q1-Q5 recorded + duplicate owners folded)

Per-task wrap-up. Bookkeeping only: handoff text, no code, no inference, no process management, no index row edited.
Source: the operator's chat answer (2026-09-29) to Q1-Q5 of `/mnt/raid0/llm/tmp/jev-techniques-map-20260928.md` §6.

## What was recorded

- **Canonical record**: `handoffs/active/typed-decision-plane.md` → *Operator rulings — 2026-09-29* (new section above
  *Objective*). `agents/shared/OPERATING_CONSTRAINTS.md` was NOT edited: its *Doctrine rulings* section holds
  governance/workflow rulings, not project-technical ones.
- **Q1 local models only**: TD-23 hosted arm removed; CJ-16 retargeted to a LOCAL judge-cascade shadow (kept, not folded
  into CJ-13: CJ-13 has no threshold-accept first stage, fallback attribution or sequential latency, which URE-2a
  needs); URE-2a now runs on the local cascade.
- **Q2 unfreeze trigger** "autopilot has trained on the swapped stack AND UFH-13 re-opened" written into TD-28 (+ v11
  promotion), VB-TD-ADVICE, LRC-1, LRC-2, all eight DAR-LAT boxes (incl. DAR-LAT-3i) and VB-SEL-LOADAB.
- **Q3 `GATE: mi210-window`** (current MI210, scheduled with workspace-76 under a bus grant or coordinated window) on
  TD-1d.0, TD-12, TD-13, TD-16, TD-17, TD-19, TD-23, CJ-13, CJ-16 and the TD-29 probes.
- **Q4 shadow-only tool arguments**: new TD-29 (shadow mode; the orchestrator today has REPLACE semantics only,
  `context.py:630-631`) with TD-29.M0-M4 (cost split, per-request spec-off native probe on v10, validate-first fallback,
  JSON-output trim, prefix-cache reuse). TD-4 now carries the receipt-based cost decomposition: closed-set generated
  5,112 tokens vs 270 free-form, and the free-form arm failed fast (~1 token) on 12/18 cases; an exact decode-vs-calls
  split is not recoverable from the receipt.
- **Q5 + duplicate clusters**: RI-14 and LRC-TD-1 folded into TD-11 (with the revisit note); TU-TD-1 folded into
  TD-4/TD-12; ECR-TD-1 folded into CJ-13; JSON repair struck from PAW-5 (TD-21 owns it); RI-15 cross-linked to EV-CONF-2.

`scripts/handoffs/index_state.py --check`: 0 problems.
