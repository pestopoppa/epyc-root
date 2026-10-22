# HIL-6 pilot redesign: fitting the first-feature pilot to a compute budget

**Date**: 2026-10-22. **For**: coordinator session 3c4ca599, to present to the operator through the
decision tool. **Owner handoff**: [`harness-improvement-loop.md`](../../handoffs/active/harness-improvement-loop.md)
HIL-6j run row. **Redesigns**: [`hil6i-pilot-design-first-feature-20261022.md`](hil6i-pilot-design-first-feature-20261022.md)
(the "original design"), as wired in orchestrator `a8551a5b` (`src/harness_loop/pilot_run.py`) and
[`progress/2026-10/2026-10-22-hil6j-pilot-wiring.md`](../../progress/2026-10/2026-10-22-hil6j-pilot-wiring.md).

**Scope.** Design and estimation only. No inference ran, nothing was armed, and no pilot code was
changed. Implementation follows the operator's choice. Every latency below is either a cited measurement
or a labelled ESTIMATE; none is a claim.

## 0. The question and the short answer

**The operator asked** (verbatim): *"I'm leaning for redesign. Is there a reason why this pilot targets
flash-next and not a faster model like q38-35b-a3b running on the mI210?"*

**Short answer.**

1. **There is no "q38-35b-a3b".** No Qwen3.8-35B-A3B GGUF exists under `/mnt/raid0/llm/models`, and no
   role, champion id or registry row carries that name. The 35B-A3B on disk is **Qwen3.6-35B-A3B**
   (`Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, 37.8 GB; `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf`, 36.9 GB). In production
   it serves `frontdoor` and, by alias, `worker_general` **on the CPU** (:8070). It has been benchmarked
   on the MI210 but has never been served there. The only model served on the MI210 is
   **Qwen3.8-27B-Q8_0** with the DFlash2 drafter (:8083, 4 slots), which serves `architect_critic`,
   `coder_escalation` and `ingest_long_context`.
2. **The original pilot targets Flash-Next because its surface has exactly one consumer.**
   `architect_investigate.md` is resolved only for `architect_general`. In
   `src/api/routes/chat_pipeline/delegation_stage.py` (`_execute_delegated`), even a non-architect request
   in delegated mode passes `architect_role="architect_general"`. Harness value depends on the model
   (HIL-4 evidence note; HIL-2 item 19), so tuning that prompt on a faster model would tune a prompt that
   no production request sends to that model.
3. **There is a fast GPU surface inside the same §3.5 home.** It is the delegation **child** prompt
   `orchestration/prompts/roles/coder_escalation.md`. In production, the Qwen3.8-27B on the MI210 receives
   it on every delegated coding call, through `_build_compact_specialist_prompt`
   (`src/api/routes/chat_delegation_reports.py`; `compact_specialist_prompt` defaults to `"1"`). It is
   scored by deterministic code execution. That is option A1, and the recommendation (D1) is built on it.

## 1. Why the original design costs 232–300 h

These are the figures from `pilot_run.estimate_requests` at `a8551a5b`, reproduced exactly:

| Step | Requests |
|---|---|
| Cycle 1: traces 150, A/A 840, candidates 3,360, arrival 600, verification modes 1,200, all-off 840, reference-trajectory arm 840, matched rollout (runs 3..8) 2,520 | 10,350 |
| Cycle 2: traces 600, incumbents A/A 1,680, candidates 3,360, arrival 600, verification modes 1,200 | 7,440 |
| TEST: 3 arms × 240 × 2 runs | 1,440 |
| **Total (lower bound is upper minus the conditional steps)** | **14,850–19,230** |

- **Per-request time** is the mean of the five per-stratum ESTIMATES in `SECONDS_PER_REQUEST`:
  15 / 30 / 28 / 28 / 180 s, giving **56.2 s**. Flash-Next has no measured delegated `/chat` latency.
  - **`livecodebench` drives the cost.** At an estimated 180 s it is 64% of the per-request mean. Without
    it, the mean is 25.3 s.
  - The 180 s figure is derived from 2026-03/04 medians on an older architect model.
- **Concurrency is 1.** `architect_general` serves one slot (`model_registry.yaml` :2365, "-np 1"). Its
  `NUMA_FULL` instance holds all four CPU region locks (`stack_topology.yaml` :258-273), so the whole
  host is claimed.
- **The power structure is not the problem.** V = 420 with 8 attempts gives power 0.842 at the declared
  MDE 0.075 (§6 of the original design). The cost is the number of solver requests the full loop
  structure needs, multiplied by a slow, serial solver.

**The fit test** used throughout this package: 32 h is 115,200 s.

- At the original structure (19,230 requests), that budget needs ≤ 6.0 s effective per request.
- At the smallest structure that keeps every requirement (option C1, ~10,400 requests), it needs ≤ 11 s
  effective per request.
- Flash-Next at np 1 is estimated at 56 s.

## 2. Power at a smaller N (recomputed)

The method is the original design's own, as in `first_feature.sign_test_critical_wins` and
`sign_test_power` and `pilot_run.power_gate`:

- d = round(n·ψ), with ψ = 0.20 as declared;
- k is the exact one-sided sign-test critical count at α / attempts;
- the win share at a true gain δ is ½ + δ / (2ψ);
- power = P(Bin(d, w) ≥ k).

The calculator is reproducible from the formulas above; it is a scratch script and is not committed.

**Minimum V for power ≥ 0.8 at MDE 0.075.** These values carry a sawtooth caused by discreteness: some
neighbours of a passing n fall back below 0.8, so a design must pick an n that passes, not just a large
one.

| Attempts (α per attempt) | Smallest passing V | Chosen V | d | k | Power at 0.075 | MDE at power 0.8 |
|---|---|---|---|---|---|---|
| 8 (0.00625), the original | 385 | 420 | 84 | 54 | 0.842 | 0.072 |
| 4 (0.0125) | 325 | 350 / 351 | 70 | 45 | 0.826 | 0.073 |
| 2 (0.025) | 280 | 290 | 58 | 37 | 0.831 | 0.072 |
| 1 (0.05) | 220 | 220 | 44 | 28 | 0.816 | 0.074 |

**Shrinking V without cutting attempts loses power fast.** At 8 attempts, V = 300 gives 0.589 (MDE 0.089),
V = 250 gives 0.492 (MDE 0.097), and V = 210 gives 0.426 (MDE 0.103). **The validation split is the one
place C cannot cut.** The savings have to come from attempts, cycles, diagnostics and TEST.

**ψ sensitivity.** The power gate replaces ψ with the measured A/A discordance before any candidate.
For the chosen designs, power at MDE 0.075 is:

| Design | ψ 0.10 | ψ 0.15 | ψ 0.20 | ψ 0.25 | ψ 0.30 |
|---|---|---|---|---|---|
| V 420, 8 attempts | 1.00 | 0.95 | 0.84 | 0.72 | 0.59 |
| V 351, 4 attempts | 1.00 | 0.91 | 0.83 | 0.73 | 0.59 |
| V 290, 2 attempts | 0.99 | 0.94 | 0.83 | 0.72 | 0.58 |
| V 220, 1 attempt | 0.99 | 0.90 | 0.82 | 0.64 | 0.58 |

- Every design, the original included, becomes underpowered at ψ ≥ 0.25. The existing gate then stops
  the run before any candidate. That behaviour is unchanged.
- Each option keeps the near-ceiling rule, with the ceiling recomputed as 1 − k/V: 0.871 for the original,
  0.872 for A1/C1, 0.873 for C2.

## 3. Options

### Common to every option

**Settings.**

- Runs = 2, with the RunMeanSignTest decision rule and the α budget of 0.05 split over the planned
  attempts.
- One paired TEST touch, n ≥ 200 (the P-QUAL-PROMO floor), with the egress clearance, the AutoPilot
  exclusion (repointed to the new target where it changes), the fence, the tripwire and the canary.
- `protocol_id` stays `None`, so every number remains an observation.
- Window length is assumed to be 8 h, with 15 min of stack bring-up per window (`STACK_BRINGUP_S`).

**Rate inputs.**

- **Flash-Next (np 1)**: 56.2 s per request. ESTIMATE, as in §1.
- **Flash-Next at np 4 on the CPU**: aggregate ×1.32 with MTP and ×1.76 without, against np 1 on the same
  setting (`handoffs/active/cpu-decode-roofline-program.md` :4832-4838, 2026-09-03, older binary).
  - Against production's np 1 with MTP (14.8 t/s), np 4 gives 17.4 (×1.18) without MTP and 19.6 (×1.32)
    with it.
  - Effective rate: 56.2 / 1.18–1.32, or **43–48 s**.
- **Qwen3.8-27B DFlash2 on the MI210 at 4 slots**: aggregate **167.76 tok/s**, 41.94 per slot, from the
  bench (`handoffs/active/autokernel-champion-aggregate.md` :578). Live :8083 measured **94 tok/s** at
  concurrency 4 in the 2026-09-24 configuration, before DFlash2.
  - A delegated coder call is at most 4 REPL turns × 768 tokens: `specialist_max_turns_repl` 4 and
    `specialist_turn_n_tokens_code` 768 (`src/api/routes/chat_delegation_config.py` :89-110).
  - ESTIMATE: about 900 decode tokens per call, plus per-turn prefill and REPL execution, gives
    **6–15 s effective** at 4 slots (central 10 s).
  - Worst case: 3,072 tokens / 94 tok/s, about 33 s.
- **Qwen3.6-35B-A3B on the MI210** (bench only, never served there): np 1 = 112.68 tok/s, np 4 = 189.57
  aggregate (37.5 GiB VRAM), np 16 = 310.96 (`docs/design/champion-max-performance-20260908.md` §6, :198).
  On the CPU, as production `frontdoor`, it runs at 40.22 tok/s.
- **Not found**: end-to-end `/chat` latency for any of these roles, and any serving-gate record of one.
  Every per-request figure is therefore derived from decode/prefill rates and caps.

### (A) Retarget the first feature to a surface served by a fast model

| | A1. `roles/coder_escalation.md` (delegation child) | A2. `roles/worker_general.md` on a 35B-A3B moved to the MI210 | A3. `task_decomposition.md` / `plan_review.md` |
|---|---|---|---|
| HIL-1 home | §3.5, the delegation child prompt | §3.5, the delegation search child | §3.5, `src/proactive_delegation/` |
| Consumer in production | `coder_escalation`, **Qwen3.8-27B-Q8_0 + DFlash2, MI210 :8083**; registry :1832-1880, alias of `architect_critic`, `enable_thinking: true` | `worker_general`, Qwen3.6-35B-A3B, **CPU** :8070 | `architect_critic` (planner and reviewer default), 27B, MI210 |
| Used in production? | Yes. Every delegated coding call (`architect_delegation` and `compact_specialist_prompt` are both default on) | Yes, on the CPU | Only for prompts classed COMPLEX (`classify_task_complexity`: architect triggers, multi-file or architecture work) |
| Same model and placement as production | **Yes** | Model yes, **placement no** (CPU → GPU) | Yes |
| Suite | The code-execution suites in the pool: `livecodebench` 704, `bigcodebench` 1,140, `usaco` 520 (before caps and exclusions) | `simpleqa` F1. The child's preamble requires `web_search()`, which conflicts with item 7 (egress to answer-key hosts) | **None.** The five strata are not COMPLEX, so `treatment_fired` ≈ 0. Forcing it with `/plan` changes the input distribution |
| Effective per request | 6–15 s (4 slots) | ~4–10 s at np 4 (189.6 tok/s aggregate) plus web latency | Not costable |
| Verdict | **Viable, with one fidelity cost (below)** | Excluded by item 7 and the placement transfer | Not runnable until a COMPLEX suite exists (P0.4 OpenCode shell suite) |

**A1 in detail.** A1 is the basis of the recommendation.

- **Unit.** The child sees `(question, Flash-Next's phase-A brief)`. Each arm's role instructions are
  inserted into the compact specialist prompt. The child runs its own REPL loop of at most 4 turns,
  which needs no architect between turns. Its `FINAL()` code is scored by `code_execution`.
- **The fidelity cost: frozen parent briefs.**
  - Flash-Next's phase-A decision and brief are produced once per item, in a **freeze pass on the
    unmodified `architect_investigate.md`**. Items it answers directly (`D|`) are not production
    delegations, so they are excluded before the draw. That exclusion is declared under item 15.
  - The claim is therefore **child-artifact correctness given the production parent's first brief**.
    That is a named §3.5 primary axis (HIL-2 table: "Delegation task success and child-artifact
    correctness").
  - It is **not** end-to-end delegated task success. The architect's re-decision loops (`max_loops` 3)
    after a child report are not replayed.
- **Freeze-pass cost** (whole host, Flash-Next, phase A only).
  - Items needed: 855 delegated code items (V 351 + T1 99 + T2 99 + T3 99 + TEST 207).
  - Items scanned: 855 / (the measured delegation rate).
  - Time per item: about 10–27 s. Prefill runs at about 92 tok/s on the live :8074 basis
    (`handoffs/completed/deepseek-v41-flash-evaluation-completed-through-2026-09-24.md` :143), with the
    static template prefix cached.
  - At a 50–80% delegation rate that is **~3–13 h**.
  - Below a rate of about 0.36, the eligible pool cannot fill the strata. The draw then **refuses rather
    than shrinking**, and the fallback is D2.
- **What the freeze pass also yields.**
  - The first measured Flash-Next phase-A latency.
  - The production `coder_escalation` delegation rate per suite, which is the item-12 "mechanical
    invocation rate per consuming model".
- **Smaller fidelity notes, declared as relaxations.**
  - The coder role's registry slot cap is 1 on a 4-slot shared server. The pilot runs 4 concurrent child
    calls, and every arm uses the same server shape.
  - The arm prompt root has to reach `resolve_prompt(delegate_role, "", subdir="roles")` inside the child
    call. This is to be verified in implementation, as `treatment_fired` proof.

### (B) Keep the architect target and raise throughput

| | B1. Flash-Next np 4 on the CPU | B2. Flash-Next partially offloaded to the MI210 |
|---|---|---|
| Data | The 2026-09-03 concurrency table: C4 MTP on 19.6 vs C1 MTP on 14.8 (×1.32). Old binary. **Gate G2-CONC is open** (roofline :4867): concurrency has to be re-run on the promotion-candidate binary. Three of four concurrent streams differ from solo without row-exact mode, at a 5–8% per-slot cost (:4816-4820) | **Not measured** (PF1 is open; `handoffs/active/mi210-big-model-and-acceleration-roadmap.md` :221-227) |
| Fit | No NUMA-quarter Flash-Next shape exists. It stays whole host | 87.25 GiB (`file_bytes` 93,682,584,224) against 64 GiB. The routed-expert pool alone is "~66 GB … ≈ the whole card" (roadmap :75), so it would need `-ngl 99 --n-cpu-moe N` with most experts on the CPU |
| Speed-up, ESTIMATE | ×1.18–1.32 (child calls overlap across slots; prefill-bound phases barely batch on CPU) | ×1.5–3. Prior from the 122B UD-Q4_K_M `-ncmoe` 8/16/24: tg ×2.9/×2.1/×1.6 (`handoffs/active/fable5-window2-findings-02-heterogeneous-gpu.md` :63) |
| Blocking facts | Production serves np 1. An np-4 verdict is a different served shape (item 14) | It **evicts the 27B** that serves the `coder_escalation` delegatee the `livecodebench` stratum needs. The operator's 2026-09-02 direction for this model was "No GPU offload". The placement differs from production |
| Original design (14,850–19,230) | 177–256 h | ~80–200 h, unmeasured |

**Neither B option fits.** Even with B2's optimistic ×3, the original design would need ~80–100 h, and
B2 breaks the delegatee.

### (C) Shrink, keeping Flash-Next

| | C1. Compliance-minimum | C2. Powered core | C3. Two editors, one cycle |
|---|---|---|---|
| Structure | 2 lineages × 2 cycles × **1** candidate (4 attempts); V 350 (70/stratum); T1/T2/T3 100; TEST 200; matched rollout k = 4; all-off kept; M9 reference-trajectory arm dropped | **1 lineage (local editor) × 1 cycle × 1 candidate** (1 attempt); V 220 (44/stratum); T1 100 traces; T2 100 arrival; TEST 200 (2 arms); all-off dropped | 2 lineages × 1 cycle × 1 candidate (2 attempts); V 290 (58/stratum); T1, T2 100; TEST 200 |
| Requests | 7,200–10,400 | 1,980–2,380 | 4,020–4,820 |
| Power at 0.075 / MDE at power 0.8 | 0.826 / 0.073 | 0.816 / 0.074 | 0.831 / 0.072 |
| Wall time at 56.2 s, plus bring-up | 116–167 h (15–21 windows) | 32–38 h (4–5 windows) | 65–78 h (8–10 windows) |
| Fits 32 h? | No | Only if the true rate is ≤ ~46 s | No |

### (D) Combinations

- **D1 = A1 at the compliance-minimum structure, plus the Flash-Next brief-freeze pass.**
  - 2 lineages × 2 cycles × 1 candidate (4 attempts).
  - Three code strata: `livecodebench`, `bigcodebench`, `usaco`.
  - V 351 (117 per stratum), T1/T2/T3 99, TEST 207, matched rollout k = 4.
  - All-off is kept: the role file is absent, so `role_instructions` is empty.
  - Self-judged mode: the local editor chooses between {incumbent, its candidate} with no labels.
- **D2 = C2 with B1.** Flash-Next at np 4, with the powered core: 1 lineage, 1 cycle, 1 candidate.

## 4. Costed comparison

| | Original | A1 / D1 (recommended) | B1 alone | B2 alone | C1 | C2 | C3 | D2 |
|---|---|---|---|---|---|---|---|---|
| Solver model, role | Flash-Next, architect_general | **27B DFlash2, coder_escalation** | Flash-Next np 4 | Flash-Next, partly on GPU | Flash-Next | Flash-Next | Flash-Next | Flash-Next np 4 |
| Requests (solver) | 14,850–19,230 | 7,245–10,431 child calls + 855/rate Flash-Next phase-A calls | 14,850–19,230 | 14,850–19,230 | 7,200–10,400 | 1,980–2,380 | 4,020–4,820 | 1,980–2,380 |
| Per request | 56.2 s (est.) | 6–15 s (central 10) | 43–48 s | ~19–37 s, unmeasured | 56.2 s | 56.2 s | 56.2 s | 43–48 s |
| Wall hours (bring-up included) | 240–310 | **GPU 13–45 (central 21–30); whole host 3–13** | 183–264 | ~85–210 | 116–167 | 32–38 | 65–78 | 25–33 |
| Windows (8 h, bring-up included) | 30–39 whole host | **1–2 whole host (freeze), then 2–6 GPU + q3 (central 3–4)** | 23–33 whole host | 13–26 whole host + GPU | 15–21 whole host | 4–5 whole host | 8–10 whole host | 3–4 whole host |
| Claim | Whole host + MI210 | Freeze: whole host. Pilot: **MI210 + CPU quarter q3 only** | Whole host + MI210 | Whole host + MI210 | Whole host + MI210 | Whole host + MI210 | Whole host + MI210 | Whole host + MI210 |
| MI210 use | `coder_escalation` delegatee (27B) | **Solver: the 27B at 4 slots** | Delegatee | Flash-Next attention and part of the experts; **the delegatee is evicted** | Delegatee | Delegatee | Delegatee | Delegatee |
| Attempts / α per attempt | 8 / 0.00625 | 4 / 0.0125 | 8 / 0.00625 | 8 / 0.00625 | 4 / 0.0125 | 1 / 0.05 | 2 / 0.025 | 1 / 0.05 |
| Power at 0.075 / MDE at 0.8 (ψ 0.20) | 0.842 / 0.072 | 0.826 / 0.073 | 0.842 / 0.072 | 0.842 / 0.072 | 0.826 / 0.073 | 0.816 / 0.074 | 0.831 / 0.072 | 0.816 / 0.074 |
| Cloud calls (upper bound) | 84 | 72 (2 preflight + 2 codex + 68 judge chunks) | 84 | 84 | 72 | 12 (1 preflight + 11 judge chunks) | 31 | 12 |
| Fits ≤ 32 whole-host h | No | **Yes** (whole host 3–13 h) | No | No | No | Borderline | No | Borderline, at the upper edge |

**Wall-hour formula.** Requests × rate, plus 0.25 h per window.

- The D1 GPU range spans the 6–15 s rate band.
- The D1 freeze range assumes a 50–80% delegation rate and 10–27 s per phase-A call.

**Cloud calls.**

- Judge chunks are ceil(V / 21) per lineage-cycle with survivors.
- C2 and D2 use no codex editor.
- The egress clearance has to name the suites that will actually leave the host: D1 sends
  `livecodebench`/`bigcodebench`/`usaco` items, not the five strata. The ratify script's suite id has to
  change accordingly.

## 5. Requirements held and relaxed

Key: **K** = kept as in the original design; **R** = relaxed (the reason follows the table); **n/a** = not
applicable, as before.

| Requirement | Original | A1 / D1 | B1 | B2 | C1 | C2 | C3 | D2 |
|---|---|---|---|---|---|---|---|---|
| P1: ≥ 2 cycles with an arriving split | K | K | K | K | K | **R1** | **R1** | **R1** |
| P2: local vs reference editor | K | K | K | K | K | **R2** | K | **R2** |
| P3: cross-model judge | K | K | K | K | K | K | K | K |
| P4 / item 20: memory-accumulating | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 1: matched-rollout baseline | K (k 8) | K (k 4) | K | K | K (k 4) | **R3** (k 2 = the A/A runs) | **R3** | **R3** |
| 2: all seats' tokens | K | K; the parent seat is counted once, at freeze | K | K | K | K | K | K |
| 3: disjoint splits, single TEST touch | K | K | K | K | K | K | K | K |
| 4 / 17d: with, none, self-judged | K | K (self-judged over {incumbent, candidate}) | K | K | K, same | K, same | K, same | K, same |
| 5: ≥ 2 runs, CI, MDE | K | K | K | K | K | K | K | K |
| 6: unmodified control | K | K | K | K | K | K | K | K |
| 7: isolation | K | K | K | K | K | K | K | K |
| 8: context-policy contract | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| 9: arrival and commitment | K | K | K | K | K | K (T2 only) | K (T2 only) | K (T2 only) |
| 10: harness growth | K | K | K | K | K | K (one point) | K (one point) | K (one point) |
| 11: validation power | K | K | K | K | K | K | K | K |
| 12: treatment fired | K | K, plus the delegation rate measured at freeze | K | K | K | K | K | K |
| 13: headroom | K | K (scan of child failures) | K | K | K | K | K | K |
| 14: pinned arm identity | K | K, plus the frozen-brief manifest sha | **R4** | **R5** | K | K | K | **R4** |
| 15: exclusions | K | K, plus the declared "parent did not delegate" exclusion | K | K | K | K | K | K |
| 16, 17a–c, 18, 21, 22 | K | K | K | K | K | K | K | K |
| 19: per-role arm set | K | K (all-off = role file absent) | K | K | K | **R6** | K | **R6** |
| M9 reference-trajectory arm (M9 extra, not HIL-2) | K | **dropped** | K | K | dropped | dropped | dropped | dropped |
| Feature under test | `architect_investigate.md` | **R7** | K | K | K | K | K | K |
| Production placement and shape | K | **R8** | **R4** | **R5** | K | K | K | **R4** |

**Relaxations.**

- **R1.** One cycle only. There is no second cycle, so there is no evidence about compounding
  (`intake-2143#00`). The HIL-6 pilot requirement of at least two cycles is **not met**.
- **R2.** The local editor only. The editor-capability comparison of the HIL-6 pilot requirement is **not
  met**.
- **R3.** k = 2 equals the A/A runs, so the label-free majority of two is degenerate. Item 1 is nominal
  only.
- **R4.** np 4 is not the production np 1. Batch numerics differ (row-exact is off), and the G2-CONC gate
  is open.
- **R5.** A GPU placement that production does not run, and the delegatee is displaced.
- **R6.** The all-off arm is dropped to fit the budget.
- **R7.** The feature changes from the architect's decision prompt to the coder child's role
  instructions. The architect-prompt question stays unanswered, and Flash-Next is not tuned.
- **R8.** Frozen parent briefs (the first brief only; no architect re-loop), and 4 concurrent child calls
  against the role's 1-slot cap on the same 4-slot server.

## 6. What each option can and cannot claim

These are observations only (`protocol_id` None) under every option.

| Option | Can support | Cannot support |
|---|---|---|
| Original | Paired, powered keep or revert of `architect_investigate.md` on Flash-Next, over 2 cycles, both editors, with TEST | Nothing extra; its problem is cost (30–39 windows) |
| **A1 / D1** | Paired, powered (0.83 at 0.075) keep or revert of `coder_escalation` role instructions **on the production 27B at its production placement**: child-artifact correctness given the production parent's brief, over 2 cycles, both editors, judge, matched rollout, all-off, and TEST | End-to-end delegated task success; anything about `architect_investigate.md` or about Flash-Next; transfer to the 35B or to any other role (HIL-4) |
| B1 | The original claim, at np 4 | A production-shape claim before G2-CONC passes on the current binary |
| B2 | The original claim, at a non-production placement | Anything about the delegatee while it is evicted; it is also against the operator's 2026-09-02 direction |
| C1 | The original claim, with 1 candidate per cycle | Fitting the budget |
| C2 | One powered paired comparison of one local-editor candidate against the incumbent on Flash-Next, with TEST: in effect a P-AB-1-shaped A/B | Loop compounding (P1), editor capability (P2), the all-off contrast |
| C3 | Editor capability in a single cycle | Compounding; fitting the budget |
| D2 | The C2 claim at np 4 | The C2 limits, plus the np-4 shape caveat |

## 7. Recommendation: D1

**D1** is A1 at the compliance-minimum structure, after a one-off Flash-Next brief-freeze night.

**Why D1.**

- It is the only option that keeps **every** HIL-2 item 1–22 and **all three** HIL-6 pilot
  requirements (two cycles, two editors, a cross-model judge) **and** keeps power at the declared MDE
  (0.826 at 0.075, ψ 0.20) inside the budget.
- Its whole-host need is the freeze pass alone, **~3–13 h (1–2 nights)**.
- The loop itself runs on **the MI210 plus CPU quarter q3**:
  - the 27B's host threads 184–191 sit in q3;
  - the local editor (the 35B-A3B) runs on a q3 instance, which serves only about 3 proposals per cycle;
  - so do the REPL sandbox and the scorer.
  
  Its central estimate is **21–30 h**, or 3–4 GPU windows. This is the shape the coordinator asked to
  prefer, and the other three quarters stay free for other work.
- It answers the operator's question directly: it **is** the fast-model-on-MI210 pilot. The model is the
  production 27B rather than the 35B-A3B, because the 27B is the model that consumes a §3.5 surface on
  the MI210 in production. That keeps main's model-conditional rule intact.

**What D1 gives up (R7, R8).**

- The pilot no longer tests the architect's decision prompt.
- Its claim is child-artifact correctness on frozen first briefs, not end-to-end delegated success.

The architect-prompt pilot stays designed and wired (`a8551a5b`). It can run later at its true cost, or
as C2 once real Flash-Next latencies exist.

**Gates declared in advance**, so that no gate needs the operator in the middle of the run.

1. **Freeze-pass gate.**
   - Each code stratum must fill V/T1/T2/T3/TEST from items Flash-Next delegates to `coder_escalation`.
   - If any stratum is short, the draw refuses. **Fallback: D2.** D2's sizes are frozen beside D1's now,
     and the freeze night's measured phase-A latency re-estimates it.
2. **Budget gate**, after the first GPU window.
   - The traces and A/A runs give the measured seconds per child call.
   - If the projected total exceeds 40 h of GPU windows, the run stops before the first attempt opens.
     No α is spent, and the result is reported as ENDED_OVER_BUDGET.
   - The existing power gate (ψ, ceiling) runs at the same point.
3. **Treatment-fired proof.** The first child call under a candidate arm has to show that the arm's
   role-file bytes were resolved. Otherwise the run is BLOCKED.

**Implementation estimate** (after the operator's choice; nothing here is built):

- a new feature id and protected layer: the preamble is code, so only the role file is mutable, and
  `FINAL()`/`CALL()` grammar lines are protected;
- the code-strata split builder and the brief-freeze phase;
- a harness-side child evaluator that reuses the delegation specialist loop with no production-path
  change. If the loop cannot be called without the architect, that is a new seam and needs a parity check;
- the AutoPilot exclusion repointed to `orchestration/prompts/roles/coder_escalation.md`;
- a new egress suite id.

Roughly 1.5–2.5 engineering days. The filler row becomes two rows: a whole-host freeze row, and a
GPU + q3 pilot row.

## 8. Decision for the operator

- **The decision**: choose D1 (recommended), C2/D2 (keep Flash-Next as a one-cycle powered A/B; P1 and P2
  relaxed), or C1/original at its true cost (15–39 windows).
- **What depends on it**: the pilot code changes, the egress clearance's suite list, and the filler rows.
- **Default if no answer**: nothing runs. The existing job refuses without the egress clearance anyway.
