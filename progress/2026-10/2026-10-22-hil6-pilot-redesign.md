# 2026-10-22 HIL-6 pilot redesign package (coordinator 3c4ca599)

**Trigger.** The HIL-6j pilot as wired (orchestrator `a8551a5b`) needs about 232–300 h of whole-host
compute, because single-slot Flash-Next runs at an estimated 56 s per request over 14,850–19,230
requests. The operator answered: "I'm leaning for redesign. Is there a reason why this pilot targets
flash-next and not a faster model like q38-35b-a3b running on the mI210?"

**Deliverable:** [`docs/design/hil6i-pilot-redesign-20261022.md`](../../docs/design/hil6i-pilot-redesign-20261022.md).
It is a decision package with options A, B, C and D. Each option is costed, its requirements are marked
kept or relaxed, and the package recommends **D1**.

This was design and estimation only:
- no inference ran;
- nothing was armed, started or stopped;
- no pilot code was changed;
- the filler job and the HIL-6j worktree are untouched.

## Findings

- **No "q38-35b-a3b" exists**, on disk or in the registry.
  - The 35B-A3B is Qwen3.6-35B-A3B-MTP-Q8_0, which serves `frontdoor`/`worker_general` on the CPU.
    It has been benchmarked on the MI210 (np 4: 189.57 tok/s aggregate) but has never been served there.
  - The MI210 serves only Qwen3.8-27B-Q8_0 with DFlash2 (`architect_critic`, `coder_escalation`,
    `ingest_long_context`; 4 slots; np 4 bench 167.76 tok/s).
- **`architect_investigate.md` has exactly one consumer, `architect_general`.** Delegated mode always
  passes `architect_role="architect_general"`. So retargeting that surface to a faster model would tune
  a prompt no production request sends to that model.
- **A fast GPU §3.5 surface exists**: `orchestration/prompts/roles/coder_escalation.md`.
  - The 27B on the MI210 consumes it on every delegated coding call: the compact specialist prompt is
    on by default, at most 4 REPL turns × 768 tokens.
  - It is scored by the code-execution suites in the pool: `livecodebench` 704, `bigcodebench` 1,140
    and `usaco` 520.
- **The other GPU surfaces do not fit.**
  - `task_decomposition.md` and `plan_review.md` (both 27B) fire only on COMPLEX-classified prompts.
    The five strata never trigger that, and no COMPLEX suite exists yet.
- **Raising Flash-Next throughput does not fit.**
  - np 4 on the CPU gives ×1.18–1.32 against production's np 1 with MTP. The data is from 2026-09-03,
    and the G2-CONC gate is open.
  - Partial offload is unmeasured (PF1 is open), would evict the coder delegatee from the MI210, and
    goes against the operator's 2026-09-02 "No GPU offload" direction.
- **Power.** The minimum V for power ≥ 0.8 at MDE 0.075 (ψ 0.20) depends on the number of attempts.
  - It is 385 / 325 / 280 / 220 for 8 / 4 / 2 / 1 attempts. These carry a sawtooth.
  - V is the one thing a shrink cannot cut. At 8 attempts, V = 300 gives power 0.589 (MDE 0.089).
  - Every design becomes underpowered at ψ ≥ 0.25.

## Options at a glance (hours include bring-up)

| Option | Requests | Wall h | Claim | Power at 0.075 | Relaxed |
|---|---|---|---|---|---|
| Original | 14,850–19,230 | 240–310 | Whole host + MI210 | 0.842 | — |
| **D1 = A1 + freeze** | 7,245–10,431 child calls + 855/rate phase-A calls | GPU 13–45 (central 21–30); whole host 3–13 | **MI210 + q3**, plus 1–2 whole-host nights | 0.826 | R7 feature changes to the coder child prompt; R8 frozen first briefs and 4-slot concurrency; M9 reference-trajectory arm dropped |
| B1 np 4 | 14,850–19,230 | 183–264 | Whole host | 0.842 | np-4 shape |
| B2 offload | 14,850–19,230 | ~85–210 | Whole host + GPU | 0.842 | Placement; delegatee evicted |
| C1 compliance-min | 7,200–10,400 | 116–167 | Whole host | 0.826 | M9 arm |
| C2 core | 1,980–2,380 | 32–38 | Whole host | 0.816 | P1, P2, item 1 degenerate, item 19 |
| C3 two editors, one cycle | 4,020–4,820 | 65–78 | Whole host | 0.831 | P1, item 1 degenerate |
| D2 = C2 + np 4 | 1,980–2,380 | 25–33 | Whole host | 0.816 | As C2, plus the np-4 shape |

**Recommendation: D1.**

- It is the only option that keeps HIL-2 items 1–22, all three HIL-6 pilot requirements and power
  inside the budget.
- Its loop runs on the MI210 plus CPU quarter q3.
- It has gates declared in advance:
  - a freeze gate: if a stratum is short, the draw refuses and the fallback is D2;
  - a budget gate after the first GPU window: if the projection exceeds 40 h, the run stops before any α
    is spent;
  - a treatment-fired proof.
- Implementation is roughly 1.5–2.5 engineering days, after the operator's choice.

**Decision owner:** the operator, through the decision tool presented by main. Nothing runs until then.
The existing job refuses without the egress clearance, and the clearance's suite list changes under D1.

**Belief kernel:** no new measurement source. This package produced estimates only, and the eventual
pilot writes through the existing VB-HIL-WRITE `finalize_run`.
