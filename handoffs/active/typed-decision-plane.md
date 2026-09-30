# Typed Decision Plane — one-pass typed decisions over the local stack

**Status**: in progress — **Owner: the research-intake lane** (operator-assigned 2026-09-17 to `intake-jev-sageattn`; that session is closed, and the lane owns this handoff from 2026-09-23). *Ownership note (operator-directed tidy 2026-09-26):* ownership is unchanged, but TD-21 and every TD-21.N row, plus the TD-1d.1/TD-1d.2/TD-1d.5 closures, were executed 2026-09-24 by a separate operator-dispatched main session with no roster lane (`workspace-8d`; `progress/2026-09/2026-09-24-td21.md`, `progress/2026-09/2026-09-24-main-ak-seat.md:123`), not by the research-intake lane. Implementation landed in `epyc-orchestrator` main from branch `intake/jev-typed-decisions-20260917` (merged; its worktree was retired 2026-09-23 — cut a fresh lane worktree from origin/main for new TD work).
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Categories**: routing_intelligence, cost_aware_routing, inference_serving, tool_implementation, agent_architecture
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Evidence**: intake-1472, intake-1473, intake-1474, intake-1485, intake-1486, intake-1487, intake-1490 (all dive-verified); intake-1476#record (application survey, anecdote-grade)

## Start here (2026-09-29)

- **Next, zero inference:** TD-29, the shadow mode (the typed pick is written beside the executed arguments in
  `decision_receipt.v1`; JSON mode in production until v11).
- **Next, GATE: champion-sidecar (CPU window):** TD-29.K2 runs the native arm (K1 keys landed, orch `c595e13d`) plus
  the same-machine JSON and free-form arms. Then TD-1d.0 (n≥4), TD-12, TD-16/17 (ruling 6 order).
- **GATE: mi210-window (JSON-mode only):** TD-29.M3, TD-13, TD-19, TD-23. CJ-13 and CJ-16 ride the same window.
- **Frozen:** TD-28, until v11 ships and autopilot has trained on the swapped stack and UFH-13 has re-opened. TD-11 is
  the single owner of typed routing.
- Closed work: § *Completed Scope*.

## Operator rulings — 2026-09-29

Canonical record of the operator's chat answer (2026-09-29) to Q1-Q5 of the 2026-09-28 Jev-techniques map
(`/mnt/raid0/llm/tmp/jev-techniques-map-20260928.md` §6). Each ruling is also written into the boxes it touches; a box
that contradicts this section is stale and must be corrected, not reconciled.

1. **Q1 — Local models only: no proprietary or hosted Jev.** We adopt Jev *techniques*, never the hosted product. This
   restates the operator's 2026-09-26 "no proprietary Jev" ruling, which no handoff recorded until now. TD-23 loses its
   hosted arm (one local compact decision backend vs the constrained incumbent readout); CJ-16
   (`canonical-judge-suite-revamp.md`) becomes a local judge-cascade shadow; URE-2a (`decision-aware-routing.md`) runs on
   that local cascade. No box may plan a call to the hosted service.
2. **Q2 — New unfreeze trigger: "autopilot has trained on the swapped stack AND UFH-13 re-opened".** UFH-13 is PARKED (2026-09-28), so the old "UFH-13 verdict" triggers could not
   fire. Applies to TD-28 (which ALSO needs the v11 promotion), VB-TD-ADVICE, LRC-1/LRC-2 and every DAR-LAT box
   (VB-SEL-LOADAB unfreezes with DAR-LAT-3).
3. **Q3 — Typed-decision measurement runs use the CURRENT MI210 as a fast test environment; do not hold them for the
   second MI210.** Gate token: **`GATE: mi210-window`** = a slot on the current MI210 scheduled with workspace-76 (DS41's
   planner and authors use `:8083`) under a session-bus grant or a coordinated window. It replaces the device-less "one
   short window" gates: TD-1d.0, TD-12 (live comparison), TD-13, TD-16, TD-17, TD-19, TD-23, TD-29.M0/M3, CJ-13, CJ-16
   (TD-29.M1 was on this list; DECLINED by ruling 6). **Amended by ruling 6:** the native-mode parts of TD-29/TD-29.M0,
   TD-1d.0, TD-12, TD-16 and TD-17 moved to `GATE: champion-sidecar (CPU window)`; their JSON-mode-only runs keep
   `mi210-window`.
4. **Q4 — Closed-set tool-argument selection (TD-4, flag `typed_decisions_tool_args`) runs SHADOW-ONLY until v11.** It
   records what it would pick, never replaces the model's arguments, and builds a labelled corpus in
   `decision_receipt.v1`. Enable task and latency mitigations: TD-29.
5. **Q5 — Typed routing has one owner: TD-11.** RI-14 (`routing-intelligence.md`) and LRC-TD-1
   (`learned-routing-controller.md`) are folded into it. Revisit TD-11's "written decision to drop typed routing" clause
   after the autopilot run on the swapped stack.
6. **Test bed — champion side instance (operator, 2026-09-29).** Features that need fixes only on the champion (v11) are tested on a CHAMPION SIDE INSTANCE (CPU build, spare port, in AutoKernel CPU windows agreed with workspace-76), not gated on production promotion. GPU champion side instances follow when a HIP champion build exists and the 2nd MI210 (or an approved displacement window) provides VRAM.
   Gate token: **`GATE: champion-sidecar (CPU window)`** = the champion CPU build `kernels/builds/cpu-20260925-90c12df42`
   (branch `ak/champion/llama-cpp-ffc1bac82eec`, contains the SW-9 fix `2b57340bf`, so native one-token scoring gets
   token probabilities on the MTP spec path) launched as a side instance with frontdoor's model and recipe args on spare
   port 8199 via `/mnt/raid0/llm/tmp/champion-sidecar/launch_champion_sidecar.sh`, inside an AutoKernel CPU window
   (`/mnt/raid0/llm/autokernel/cpu-window.json` open, `loop_holds_claim=false`, >=30 min left) or with workspace-76's
   agreement; bench driver `/mnt/raid0/llm/tmp/champion-sidecar/run_td_bench.sh`. It replaces `mi210-window` for NATIVE-mode
   tests; JSON-mode-only tests keep `GATE: mi210-window`. Precedent: 2026-09-24 champion CPU build on :8199 with frontdoor
   args through `LLMPrimitives` `/v1` (receipt `/workspace/tmp/td1d5-20260924/bench-candidate-8199.json`). Test order:
   TD-29 (native vs JSON vs free-form with TD-29.M0 instrumentation) → TD-1d.0 (n>=4 rounds) → TD-12 → TD-16/17.
   TD-29.M1 (per-request spec-off probe on v10) is DECLINED: native mode is measured on the champion directly.
   Window discipline (added 2026-09-29, INC-20260929-peer-window-closing-overrun): stop the bench and the sidecar at
   once on any window `state` other than `open`, or when `loop_holds_claim=true`; `closing` means stop. The sidecar
   lives exactly as long as its bench run. `window_loop.sh` and `run_td_bench.sh` enforce both.

Duplicate-owner consolidation the same day (the map's §3.2): closed-set tool arguments → TD-4/TD-12 (TU-TD-1 in
`tool-use-eval-contract.md` folded); cheap-judge redundancy → CJ-13 (ECR-TD-1 in `eval-benchmark-cost-reduction.md`
folded); JSON repair → TD-21 (struck from PAW-5's candidate list in `paw-compiled-specialists.md`).

## Objective

Give the orchestrator a first-class one-pass decision call: declared typed questions (choice / score / noul)
in, per-question values + probabilities + a caller-computed confidence statistic out, with no autoregressive
JSON generation, and with locally measured behaviour before any gate uses it. Operator steering 2026-09-17:
"extremely relevant for the orchestrator where json schemas are passed and tool use is important ... guarantees
exact tool use and also a pretty large overall speed boost ... may also be relevant for fast routing and
episodic memory writing."

## Research Context

| Intake ID | What it settles | Use |
|-----------|-----------------|-----|
| intake-1472 | Public typed-decision spec (primitives, one-call parallel questions, confidence is an undisclosed statistic) | Contract for the local implementation |
| intake-1473 | MIT reference implementation over generic LLM APIs (per-request schema, corrective retries, normalization, local confidence stats, injection guard) | Pattern set to transplant onto llama.cpp |
| intake-1474 | Independent evidence that candidate-softmax confidence is NOT calibrated (65% of wrong 7B fields >0.90) and the real local speedup is 3.4–7.9x, not 40–200x | Hard constraint: no gate before local calibration |
| intake-1485 | Paired Jev-vs-fast-LLM run: measured p50 176 ms vs 215 ms; fixture agreement scene-dependent | External datapoint; baseline is fast, so no multiplier transfer |
| intake-1486 | Independent rerank reproduction: Jev tied with Cohere Pro (nDCG 0.692 vs 0.691, CI crosses 0); Jev Choice order-sensitive 24.7% | Guarantees are not quality; order effects must be measured |
| intake-1487 | Fully local pinned one-pass implementation: 5.21x vs same-model JSON on a 3090; 20.03 decisions/s parallel reuse; reuse drifts 5–6/777 argmaxes | Local mechanism + acceptance envelope |
| intake-1490 | Independent audit of jevlike: shipped shuffled-context control was defective; informed-vs-blind lift ~25 pts after correcting | Verification discipline for our own measurements |
| intake-1493 | Open browser agent (MIT) that asks one typed call for an operation plus one speculative target head per operation, consuming only the matching head; its measured gain is ~half fewer model requests, ~half browser I/O | Pattern for TD-12..TD-15 (tool choice + arguments in one call) |
| intake-1498 | Kev: trained LoRA + pointer head over option hidden states; OOD numbers recount from committed rows; llama.cpp feasible with merge-first + `seq_cp` | TD-18, TD-19, TD-20 |
| intake-1504 | CC0 300-state x 3-question OOD set (tier visible; priority policy-unknown, not unknowable); corrected Jev T 1.30 / 1.92 | TD-17 |
| intake-1517 | Noul label-word bias (laya#156 reproduced); neutral-key choice changes three things at once | TD-16 |
| intake-1502 | Laya: fitted calibration holds in-task only (ECE 0.030 vs 0.204 held-out); shipped a sharpening T 0.1006 | Counterexample for TD-17, TD-18 |

## Completed Scope

| Scope | Where |
|---|---|
| TD-1 … TD-3b, TD-5/6/7/9/10 (2026-09-17/18) | [completed ledger](../completed/typed-decision-plane-completed-through-2026-09-29.md) |
| TD-21 and every TD-21.N except TD-21.1a (2026-09-24) | same file |

## Tasks

- TD-1, TD-1a, TD-2, TD-3, TD-1b, TD-1c and TD-3b are done (2026-09-17): the call path, native scoring,
  contamination/calibration, fan-out, tokenizer-aware candidates, parity and fan-out agreement. § *Completed Scope*.
- [x] **TD-1d — Recover native speed at parity.** The cue replay costs a forward pass per forced cue token (2.08x vs JSON; 18.9x pre-fix). Options to test: (a) minimal grounding cues (id + a few tokens) judged on the same 24-question set; (b) parallel per-question native reads against one cached prefix (use the server's multiple slots) — the faithful 'parallel sampler' shape; (c) routing cheap vs hard questions between native and JSON arms. ✅ 2026-09-17 ACCEPTED via the id-only cue. Cue sweep on the worker (same 35B, same 24-question set, one run each): JSON 19.3 s / 1,354 tok; native:full 7.3 s (2.66x) / 523 tok; native:short 3.2 s (6.0x) / 239 tok; **native:id_only 1.6 s (11.98x) / 112 tok** — all three native styles at 15/16 agreement and 15/16 accuracy on the overlap (JSON 14/16 on the same 16). The prompt catalogue carries the grounding; the id-only cue re-anchors position. Parallel per-question reads were tested and rejected on this stack (exclusive heavy_model lock serializes workers; client concurrency 0.65x vs batched; the true parallel-sampler needs a multi-slot readout readout the generation API lacks — record for any future runtime choice). Remaining: adopt id_only as the native default after review and decide whether a `native_cue_sweep` study gets a belief-kernel carrier.
  - ⚠️ **2026-09-18 RE-MEASUREMENT DISAGREES WITH THE ACCEPTANCE — the bar is not cleared at n>1.** The row above
    accepted TD-1d on **one run per arm**. A 4-round re-measurement on the same model and catalogue, with every
    arm run before the next round and arm order rotated, puts the best arm **below** the 10x bar. The tick is
    left standing because the box belongs to the accepting session; **this note is the evidence against it.**

    | arm | this run (n=4, mean ± sd) | speedup | 2026-09-17 (n=1) |
    |---|---|---|---|
    | json baseline | 14.02 ± 1.82 s (11.34–15.45) | 1.00x | 19.3 s |
    | native_full | 6.52 ± 0.05 s | 2.15x | 7.3 s (2.66x) |
    | native_short | 3.03 ± 0.12 s | 4.63x | 3.2 s (6.0x) |
    | **native_id_only** | **1.46 ± 0.03 s** | **9.60x** | 1.6 s (**11.98x**) |
    | native_pq1 (1 slot) | 2.09 ± 0.04 s | 6.69x | — |
    | native_pq3 (3 slots) | 5.24 ± 0.93 s | 2.67x | — |
    | native_pq3_id_only | 2.27 ± 0.45 s | 6.17x | — |

    **The disagreement is the JSON BASELINE, not the native arm** — the two id_only measurements agree (1.46 s
    vs 1.6 s). The 2026-09-17 JSON sample (19.3 s) is **above the maximum of four samples measured here**
    (15.45 s), and pairing each side's baseline with the other's native time spans **8.8x–13.2x**. A single
    baseline sample cannot see that spread, which is exactly why the bar needs a repeated baseline.
    Agreement is NOT in dispute: 60/64 pooled = 0.9375 = 15/16, every round, same `n01` disagreement as TD-1c.
    **Denominator caveat that applies to BOTH numbers:** native decides 16/24 (c01–c08 fail closed,
    `native_unsupported_candidates`), so the ratio compares a 16-decision run to a 24-decision one. Per decision
    it is 584 ms vs 91 ms = **6.40x**. The bar never stated its denominator; neither figure passes it.
    Independent corroboration of the 09-17 note: parallel reads ARE a loser here — measured 2.67x, slower than
    serial. Artifacts: `artifacts/typed_decisions/run_20260918/`; server launched and killed by the measuring
    session, VRAM 59% in all 24 in-run samples.
    - [ ] **TD-1d.0 — OWNER/OPERATOR: re-settle the acceptance.** Either re-run the 09-17 arms with a repeated
      baseline (n>=4, alternated) and keep the acceptance if it survives, or downgrade "ACCEPTED" to
      "best-effort 6.4–9.6x, bar not cleared". Do not adopt id_only as the native default on the n=1 number
      alone. Inference-gated — **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29); the whole sweep above took ~20 min including model load.
  - [x] **TD-1d.1 — `/v1` drops `grammar`/`json_schema`, so the native path cannot run through `LLMPrimitives`.**
    `frontdoor` routes to `/v1/chat/completions` (`use_chat_completions=True`), which forwards neither field:
    measured 515 free-form tokens and **0/24 decisions** (`native_unknown_candidate` x16). Every arm above used a
    direct `/completion` adapter mirroring `_build_payload`, and TD-1c's result must have gone the same way.
    **No typed-decision arm is deployable through the normal primitives path until this is closed** — decide
    whether `/v1` forwards the fields for internal callers, or whether typed decisions keep a declared direct
    `/completion` lane. Zero inference to decide.
    ✅ 2026-09-24 — closed by **TD-21.0** (folded here, per the TD-21 dispatch): `/v1` now forwards both
    (orch `b284ede3`), so no declared `/completion` lane is needed. Verified live on frontdoor :8070 through
    `LlamaServerBackend` (same prompt: prose without a schema, schema-valid JSON with one) and end to end through
    the reloaded API (`/chat` + `output_schema` + `force_role=frontdoor` → `{"answer": true, "city": "Paris"}`).
  - [x] **TD-1d.2 — re-run the TD-1d native arm through `LLMPrimitives` on frontdoor.** The 0/24 above was the
    dropped grammar; the schema path is now live, but the native candidate-probability readout over `/v1`
    (`logprobs`/`top_logprobs` instead of `/completion`'s `n_probs`) has not been re-measured. One short window
    with `src/typed_decisions/bench.py`; schedule it outside a CPU-decode campaign window.
    - *2026-09-24 live windows:* 12:07Z run through `LLMPrimitives` on frontdoor: JSON 0/24 (`no_json`), native
      full 1/16, `id_only` 0/16. Two fixes landed from the review: orch `4610be60` — the streaming
      repetition-loop guard ran unconditionally and aborted legitimately repetitive schema-constrained output,
      now exempt when `json_schema`/`grammar` is set; and orch `71be6ed3` — native `n_probs` was captured
      pre-grammar-mask by default, now the request sets `post_sampling_probs`. (The "noul" key one agent
      suspected as a bug turned out to be the schema's own key for yes/no questions — grammar converter
      verified faithful; that hypothesis was wrong.) Re-bench 13:38-13:41Z: JSON 0/24 now ends on `length`
      (1600-token budget too small for the schema+reasoning), native still unchanged (the flag appears not to
      reach the server). Diagnosis in flight.
    - [x] Raise the JSON arm's token budget above 1600 (measured ending on `length`, not a real parse failure)
      and re-bench. ✅ 2026-09-24 — schema-aware budget landed (`8977f540`); late-afternoon re-bench: **JSON arm
      24/24 decisions, 23/24 vs labels.**
    - [x] Trace why the native `post_sampling_probs` request flag (orch `71be6ed3`) is not reaching the
      server — native result unchanged across the fix. ✅ 2026-09-24 — root cause is not the flag: the frozen
      production kernel's MTP speculative-accept path never populates token probabilities at all (`// TODO: set
      result.probs` in `server-context.cpp`) — ~94% of frontdoor tokens come from accepted MTP drafts, so
      `post_sampling_probs` has nothing to read on those tokens regardless of the request flag. **Operator
      decision (2026-09-24 ~15:45Z): NATIVE mode is out of reach on the current production kernel; patch the
      spec-accept path in kernel research and advance the AutoKernel champion so future campaigns pick it up**,
      rather than disabling MTP for frontdoor or reworking the flag further. Filed as its own task: TD-1d.5.
    - ✅ 2026-09-24 **closed overall**: JSON arm cleared the bar (24/24, 23/24 vs labels, `8977f540`); the native
      arm's remaining gap is not a bench defect but a kernel limitation with an explicit operator disposition
      (patch-in-kernel-research, tracked as TD-1d.5). Nothing left dispatchable under TD-1d.2 itself.
  - [x] **TD-1d.5 — spec-accept path never fills token probabilities on the frozen production kernel (`llama.cpp`
    `server-context.cpp`, MTP speculative-accept path, `// TODO: set result.probs`).** Blocks the native
    typed-decision arm's candidate-probability readout (TD-1d.2) because ~94% of frontdoor tokens are accepted
    MTP drafts with no probs attached, regardless of the `post_sampling_probs` request flag (orch `71be6ed3`).
    Operator decision 2026-09-24 ~15:45Z: patch it via kernel research on an experimental branch (never patch
    the frozen `production-consolidated-v10` tree in place — full experimental → validate → new-production
    cycle per CLAUDE.md), then advance the AutoKernel champion so campaigns pick up the fix. A subagent is
    preparing the patch on an experimental branch as of this wrap-up; build/validation needs an operator-granted
    CPU window (**in flight**). Owner: `handoffs/active/speculative-decoding-mtp-refresh.md` **SW-9** (filed
    there as the kernel-side task; this row tracks the typed-decision consumer side and is closed by SW-9
    landing + a native re-bench).
    ✅ 2026-09-24 — fixed in the champion (`2b57340bf`, SW-9): native mode works on the champion build (16/16
    decisions, ~11× faster than JSON). Production (v10) still lacks it — native stays out of reach in production
    until a v11 promotion carries the champion.
    *Comparability caveat (operator-directed tidy 2026-09-26):* the ~11× (native `id_only` 7.1 s vs JSON 80.4 s
    = 11.4×) is ONE run per arm on the **CPU frontdoor** — the candidate champion CPU build (10306) on spare
    port 8199 with frontdoor args, through `LLMPrimitives` `/v1` (receipt
    `/workspace/tmp/td1d5-20260924/bench-candidate-8199.json`, role `frontdoor`, 2026-09-24T17:51Z). It is NOT
    comparable with the GPU figures above (11.98× n=1 and 9.60× n=4, MI210 worker, direct `/completion`): different
    device, server build (MTP draft-accept path), transport and JSON baseline (JSON 2,368 generated tokens here vs ~1,356 on the GPU).
    "16/16" = the 16 natively eligible of 24 questions (c01–c08 fail closed, the same 6.40×-style denominator
    confound). Agreement with JSON: `id_only` 15/16, `full` 14/16 (14/16 across all three arms). It shows the
    SW-9 fix unblocks the native readout; it is not evidence for the TD-1d 10× bar or for TD-1d.0.
  - [ ] **TD-1d.2b — concurrent in-process `llm_call`s are serialized by the cross-process `inference_lock`**
    (probed: parallel wall == serial wall, max 1 slot busy). A constraint on every future fan-out design, not
    just this one; independently matches the 09-17 note's `heavy_model` lock observation.
    *(Filed 2026-09-18 as "TD-1d.2"; renamed TD-1d.2b 2026-09-26 because the 2026-09-24 native re-bench row above
    reused that id. Code comments and the 2026-09-24 progress logs that say "TD-1d.2" mean the re-bench row.)*
  - [ ] **TD-1d.3 — `qwen35moe` is hybrid-recurrent (SSM layers), so prefix reuse is checkpoint-quantized.**
    Back-to-back per-question reads on one slot reuse **0** tokens (~450 ms each) unless a prefix-only request
    first leaves a checkpoint at the prefix end (then `cache_n` 1105, ~128 ms/read); under 3-way concurrency they
    stretch to 585–900 ms. This is the mechanism behind fan-out losing, and it belongs in any prefix-cache
    reasoning about this model class.
    - *Note 2026-09-23 (intake-1498, intake-1514#00):* an exact per-question prefix fork on hybrid qwen35/qwen35moe exists
      inside ONE request: decode the state once into seq 0, then `llama_memory_seq_cp` 0->i per question
      (`llama-memory-hybrid.cpp:152-155` copies KV + recurrent state), as espetro/llama.cpp@kev `common/decision.cpp:538`
      does. The 0-token reuse above comes from cross-request slot caching, not from the model class; the stock
      server's pooling-none embeddings path has no prefix reuse (`server-context.cpp:426-431`).
  - [ ] **TD-1d.4 — to clear the bar honestly, handle the 8 multi-token choice questions natively** (which also
    removes the denominator confound), or take option (c): per-question cost/confidence labels plus a JSON
    fallback for those 8. Not built; (c) is a routing policy, not a speed fix.
    Harness extension `run_typed_decisions_native_parallel` (`src/typed_decisions/native.py`, +251 lines, ruff
    clean, 209 native unit tests pass) is **uncommitted** pending TD-1d.0.
    - [x] ✅ 2026-09-24 — orch `11818eb5`: the parked 2026-09-22 harness landed **UNWIRED** (taken over from the
      other session at operator direction; the parked diff's silent `CueStyle` default reversion to `full` was
      deliberately NOT carried over). Still gated on TD-1d.0 — landing the code is not adopting it.
    - *Options added 2026-09-23 (intake-1498, intake-1514#00):* (d) a trained option-end pointer readout (Kev) — viable only
      as a separate small decision model, not a zero-shot fix; TD-9's single-token codes already removed the TD-7 blocker.
      (e) score multi-token candidates as `seq_cp` branches (summed teacher-forced log-prob), on llama.cpp-experimental.
- [x] **TD-4 — Closed-set tool-argument selection pilot.** Map tool arguments to closed sets (Literal → Choice,
  list[Literal] → multi-choice, bool → Noul) with per-argument confidence; compare against the current
  free-form tool-call path on exact-match argument correctness and wall time. Citation: intake-1472 pattern,
  intake-1473 adapter. ✅ 2026-09-17 live pilot on the worker (18 deterministic cases, 3 tool schemas): **closed-set 18/18 exact-match (0 failures) vs free-form 6/18 (12 failures)**, per-arg exact 66 vs 24, at 116.6 s vs 11.4 s (10.2x wall). Exact tool use is the closed-set arm's to win; the free-form arm's failures are parse/schema failures, not merely wrong values. `tool-use-eval-contract.md` TU-TD-1 was folded into TD-4/TD-12 on 2026-09-29: that contract reads this harness as its eval arm.
  - *Cost decomposition (receipt re-read 2026-09-29, `artifacts/typed_decisions/run_20260917/tool-args-pilot-worker.json`).*
    The 10.2x is not a like-for-like decode comparison. The closed-set arm (JSON mode) generated 5,112 tokens vs 270
    free-form (18.9x). The free-form arm stopped after ~1 token on its 12 parse failures (0.40-1.05 s per case), so its
    wall is flattered by failing fast; its 6 successes used 37-45 tokens. The closed-set arm made 1 call in 9 cases and
    2 (one corrective retry, `failure_count=1`) in the other 9: 27 calls vs 18, inferred, because the receipt has no call
    count. One-call closed-set cases still took 5.1-6.6 s for 136-447 tokens, which points at per-call fixed cost
    (prefill of the typed catalogue) more than decode. An exact split is not recoverable: per-case `tokens` is the LAST
    call's only (`tool_args_pilot.py:540-544`) and no prompt-token field survives (`_arm_case_view`, :643-656). TD-29.M0
    re-measures it. The receipt records `role: "frontdoor"` despite its `worker` filename.
- [ ] **TD-29 — Shadow-only closed-set tool arguments until v11 (operator ruling Q4, 2026-09-29).** Today
  `typed_decisions_tool_args` (`src/features.py:258`, default off) has REPLACE semantics only: `context.py:630-631` swaps
  the model's kwargs for the typed dict when validation is `accepted`, and neither `tool_args_integration.py` nor
  `prepared_action.py` has a shadow path (`shadow.py` covers routing only). Add a shadow mode (a separate flag or a mode
  value; decide in review) that runs the typed selection, executes the model's own arguments, and writes the typed pick
  beside the executed arguments and the tool outcome in `decision_receipt.v1` (`prepared_action.py:20`; sink
  `artifacts_dir/typed_decisions/decision_receipts.jsonl`, `context.py:684-688`), so the receipts form a labelled corpus.
  - Run the shadow off the tool call's critical path (non-blocking, bounded, fail-open, as `shadow.py` does), or its
    latency lands on the user.
  - Pin the shadow's decode mode explicitly. The integration defaults to native (`context.py:806-812` passes no mode),
    and native needs token probabilities that v10's MTP accept path does not return (SW-9, fixed only in v11). Use JSON
    mode in production until v11; native mode is measured on the champion sidecar (operator ruling 6, 2026-09-29).
  - The native vs JSON vs free-form comparison (with TD-29.M0 instrumentation) runs all arms on the same sidecar server —
    **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29).
  - [x] **Skip the typed-args call site when the flag is off** (the bullet below). ✅ 2026-09-28 — orchestrator
    `e60ee78a`: `_dispatch_tool` calls `_typed_tool_arguments` only when a prepared action exists; the flag-off test
    proves neither it nor `maybe_typed_arguments` runs and no receipt is written, and fails against the old code.
  - With the flag off, `context.py:593-597` still calls `_typed_tool_arguments` on every dispatch (it returns at
    `tool_args_integration.py:177`); skip it at the call site.
  - Acceptance: tests prove the shadow never alters executed arguments; the stack launcher enables it for one role; a
    live shadow window yields receipts with typed pick + executed arguments + outcome. No replacement mode before v11.
  - [ ] **TD-29.M0 — Split the TD-4 cost into decode, extra calls and prefill.** Make the pilot sum tokens across retries,
    keep `prompt_n`/`cache_n` and an explicit call count per case, then re-run the 18 cases. Code is zero-inference; the
    re-run is **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29), all arms on the sidecar as part of the TD-29 comparison (TD-29.M1 declined). Acceptance: per-arm decode tokens, prefill tokens, call count and
    wall, from the receipt.
    - Progress 2026-09-29: the code half landed as orchestrator `c4e99dbe` (`call_recorder.py` snapshots tokens,
      `prompt_tokens`, `cache_n`, `prompt_n`, `prompt_ms` and `gen_ms` after every call; the pilot sums per case and
      keeps `tokens_last_call`; new `--closed-mode`, `--cue-style`, `--arm`, `--case-log`, `--server-url`). The box
      ticks with the re-run, which rides TD-29.K2's sidecar window.
  - [x] ~~**TD-29.M1 — Native scoring probe on v10 with speculation disabled per request.**~~ **DECLINED (operator,
    2026-09-29):** the operator prefers testing native mode on the champion directly (ruling 6) over a per-request spec-off
    probe on v10. ✅ 2026-09-29 — resolved to a decline; the text below is kept for the record. Native one-token scoring needs
    token logprobs, which production v10's MTP/speculative accept path does not return; SW-9's fix is only in v11. Probe
    whether turning speculation off PER REQUEST returns logprobs on v10, so native mode works before v11. Source reading
    says llama-server parses a per-request `speculative.n_max`, where 0 disables speculation for that request
    (`tools/server/server-schema.cpp:205-207`, applied at `server-context.cpp:489`, tree `ffc1bac82`; `n_min`/`p_min`/
    `type` sit under `#if 0`, not wired per request); the orchestrator sends no speculative params today
    (`src/backends/llama_server.py`). That is not evidence the logprobs come back; the probe is. ~~GATE: mi210-window~~ (declined).
    Acceptance: logprobs present, the native path succeeds on the TD-4 case set, latency measured, with the decode cost
    of losing MTP on that request recorded.
  - [ ] **TD-29.M2 — Validate-first fallback.** Execute the free-form arguments and invoke the typed path only when schema
    validation fails, so correct calls pay nothing extra. First measure the real-traffic free-form failure rate from the
    TD-29 shadow receipts: the TD-4 cases were adversarial, so 12/18 is not a traffic rate. Acceptance: a failure rate
    with a CI from real receipts, and a design that charges the typed latency only to the failing share.
  - [ ] **TD-29.M3 — Trim the JSON-mode output.** In shadow mode emit no confidence fields, and put closed-set arguments
    only on exactness-critical tools (name them from `ToolRegistry`). Schema change and unit tests are zero-inference;
    the before/after tokens-per-pass count on the TD-4 case set is **GATE: mi210-window** (operator ruling Q3, 2026-09-29).
  - [ ] **TD-29.M4 — Confirm prompt-prefix cache reuse between the tool call and the typed call.** Check that the typed
    pass shares the tool call's prompt prefix, so llama-server reuses the cached prefix instead of re-prefilling it.
    Acceptance: `prompt_n`/`cache_n` recorded for paired calls (with TD-29.M0); if reuse is absent, name the prefix break.
  - **2026-09-29 champion-sidecar native result (n=1, CPU sidecar).** `--closed-mode native --cue-style id_only`, 18
    TD-4 cases, build `cpu-20260925-90c12df42` on :8199, 40 threads, cores 48-87. **12/18 exact; all 12 resolved cases
    correct.** The 6 failures are all `cannot assemble tool arguments: required argument 'severity' was not answered`:
    the `p1`..`p4` enum is multi-token, so native excluded the question (`native_unsupported_candidates`). 534 generated
    tokens in total (17-38 per case) vs 5,112 in the 2026-09-17 GPU JSON arm; 18 calls, one per case; wall 42.3 s
    (2.35 s per case); prompt 20.3 s vs gen 16.9 s, so prefill dominates and M4 prefix-cache reuse is the next lever.
    The same-machine JSON and free-form arms were NOT run (the window closed early), so no within-run native-vs-JSON
    ratio exists yet. Receipt: `/mnt/raid0/llm/tmp/champion-sidecar/runs/td-20260929/td29/closed_native_id_only.pre-K1.json`
    (cases in `closed_native_id_only.pre-K1.cases.jsonl` beside it; renamed with the `.pre-K1` suffix so the K2 re-run
    writes fresh receipts under the original names).
  - [x] **TD-29.K1 — Single-token keys for multi-token closed sets (native mode).** A closed set whose labels are not all
    single tokens is re-keyed with the TD-9 code alphabet (A-Z, 0-9), each key verified single-token and collision-free
    through `/tokenize`; the model picks a key and the layer maps it back to the original value (`Decision.native_key`
    plus value; the pilot receipt records both). Sets that already bind are untouched (byte-identical); more than 36
    labels falls back as before, with the reason recorded. JSON mode is unchanged. ✅ 2026-09-29 — orchestrator
    `c595e13d` (`src/typed_decisions/native.py` `_bind_single_token_keys`, serial and parallel native runners).
  - [ ] **TD-29.K2 — Re-run the native arm after K1.** Repeat `--closed-mode native --cue-style id_only` on the champion
    sidecar with the fixed harness (`orch-tdbench-8d`), together with the same-machine JSON and free-form arms that the
    2026-09-29 window missed. **GATE: champion-sidecar (CPU window).** Acceptance: 18/18 resolved or each failure named;
    `native_keys` present on the file_ticket cases; within-run native vs JSON token and wall ratios.
    - Progress 2026-09-29: a window-gated loop is running the remaining arms
      (`/mnt/raid0/llm/tmp/champion-sidecar/window_loop.sh td29 td-20260929`, started 23:48Z, log
      `window_loop-td29.log`). It waits for an open window, launches the sidecar, runs the bench, and confirms the
      sidecar is dead afterwards. It needs 10 min left in the window (`NEED_MIN=10`), not 30, because DS41's two-lane
      windows have all been shorter than 30 min. The bench still aborts on any state other than `open`. No arm had run
      by 23:50Z. The 03:3xZ JSON attempt was aborted at the window close; its partial cases are kept as
      `closed_json.aborted-0336Z.cases.jsonl` and are not a result.
    - Note 2026-09-30, one profile per run: workspace-76 will pause DS41 for 4-8 h (a 27B harness on :8083). They
      agreed the arms may run during that ANNOUNCED pause on an explicit override. The condition is that the
      sidecar stays off cores 72-79, where the 27B's host threads decode.
      - Pause profile: cpuset `48-71,80-87`, 32 threads, NUMA interleave 2,3. The standing profile is `48-87` with
        40 threads.
      - The arms must share one profile to be comparable, so under the pause profile all three run fresh in
        run `td-20260930-p32`.
      - The pre-K1 native receipt is superseded. The post-K1 native receipt in `td-20260929` (2026-09-30 01:48Z)
        is 48-87/40, so it is not mixed in. No JSON or free-form arm has completed in either run.
      - If the pause profile is not used, `td-20260929` continues at 48-87/40.
      - `run_td_bench.sh` now refuses a second profile in one run dir (`profile.json`).
      - Machinery: `champion-sidecar/window_gate.py --allow-announced-pause` (the pause file
        `sequencer-8d/DS41_PAUSE_ANNOUNCED.json`, plus an exited, claim-free, dead DS41 loop) and the lane
        `sequencer-8d/run_cpu_lane_pause.sh`.
    - [x] **TD-29.K2a — record workspace-76's agreement to the 10-minute threshold.** Ruling 6's gate names ≥30 min
      left, or workspace-76's agreement. The running loop uses 10 min, so record that agreement here (bus message
      id or chat date), or restart the loop at `NEED_MIN=30`.
      ✅ 2026-09-29 — workspace-76 agreed on the session bus: the loop may start in any cpu-window with ≥10 min
      left, each arm gated to fit the time remaining, and it stops on any window state other than `open`. Their
      words: "Keep going by cpu-window.json and its est_close_at; the flock is the truth." The loop stays at
      `NEED_MIN=10`.
- TD-5, TD-9, TD-6, TD-7 and TD-10 are done (2026-09-17/18): the shadow integration, the routing code map, the
  `id_only` native default (it stands pending TD-1d.0), the live replay, and the counterfactual OPE (typed routing is
  ~1pp worse, so enforcement is OFF; TD-11 owns the follow-up). § *Completed Scope*.
- [ ] **TD-11 — Routing prompt/policy improvement, re-tested through the counterfactual harness.** The harness now measures value, not agreement; use it to iterate (framing, support-aware candidates, leave-one-out conditioning) before any enforcement proposal. Acceptance: positive delta with a CI excluding zero on the frozen snapshot, or a written decision to drop typed routing.
  - *Single typed-routing owner (operator ruling Q5, 2026-09-29).* RI-14 (`routing-intelligence.md`) and LRC-TD-1
    (`learned-routing-controller.md`) are folded here; their "once TD-2 lands" gates were met 2026-09-17, and TD-10 then
    measured a loss. Scope carried over: (a) from RI-14, report agreement + calibration + wall time against the CURRENT
    routing classifier, never gate on uncalibrated confidence, and use the intake-1501 question shape (tier choice with
    criteria + an ordinal effort score) with a 20-card OOD probe whose labels come from a distribution the arm was not
    tuned on; (b) from LRC-TD-1, compare against the learned controller's BGE+MLP classifier on the recorded routing
    corpus, and treat the option-as-query head (intake-1462) as a second candidate-scoring arm beside native token
    logits (intake-1487).
  - *Revisit note (operator ruling Q5):* re-decide the "written decision to drop typed routing" clause after the autopilot
    has trained on the swapped stack. TD-7 showed multi-token role labels need v11-native scoring before a fair retest.
- [ ] ❄ FROZEN 2026-09-27 — resume only once v11 is promoted (native scoring) AND autopilot has trained on the swapped stack AND UFH-13 re-opened — **TD-28 — typed routing as ADVICE, not enforcement (operator direction 2026-09-26).** TD-10 showed typed routing ~1pp worse as an enforcer (delta -0.0104). A/B a typed routing hint in the frontdoor prompt vs no hint: measure how often frontdoor overrides the hint and whether overrides help (accuracy on overridden vs followed items). Wire the A/B's write side into the belief kernel (`vidya-belief-substrate-program.md` VB-TD-ADVICE).
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): typed advisors add a routing input before the base comparison exists, and 0/200 native scoring (TD-7) makes the advice JSON-fallback only; unfreeze trigger (operator ruling Q2, 2026-09-29; it replaces "the UFH-13 thesis experiment has a recorded verdict", which cannot fire while UFH-13 is PARKED): the v11 promotion ships native scoring (multi-token action labels scored natively) AND autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.

- [ ] **TD-12 — One-call tool + argument arm (operation × conditional target).** Build a typed-decision arm that asks, in one call, a choice over the role's tools (`ToolRegistry.list_tools(role)`) plus one argument head set per candidate tool whose instructions name the tool they assume, and consume only the chosen tool's heads. A failed head for an UNUSED tool must not reject the pass (today any failure rejects it: `tool_args_integration.py:197-198`). Compare against the current tool-then-arguments path (TD-4) on exact-match tool+argument correctness and wall time over the TD-4 case set extended with a tool-choice step. Citation: intake-1493 (dive-verified; `jev_ultrafast/model.py:94-133` @ 1231850a). Code and unit tests are zero-inference; the live comparison is **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29), both arms on the sidecar for a like-for-like comparison (a JSON-mode-only run keeps `mi210-window`). The tool-use eval contract reads this harness as its closed-set arm (TU-TD-1 folded here 2026-09-29).
- [ ] **TD-13 — Contamination between the operation head and its conditional heads.** Before TD-12's heads are trusted as independent: for each case, answer the chosen tool's argument heads alone and batched with the sibling (unused) tools' heads; report top-answer flip rate per model. Existing receipts (TD-2, TD-3b) cover flat catalogues only. Acceptance: flip rate reported for the worker model; TD-12 adoption gated on it. The run is **GATE: mi210-window** (operator ruling Q3, 2026-09-29).
  - *Acceptance amendment 2026-09-25 (intake-1577#record, intake-1583#record):* randomize and interleave two dependency controls: move one sentinel fact between shared state and an unused sibling head, and prepend/append one semantically irrelevant candidate inside the chosen head. Report chosen-answer flips and pairwise log-odds among unchanged candidates. Treat any effect as a behavioral dependency; do not infer an attention mask, prefix-cache layout, or readout architecture.
- [ ] **TD-14 — Per-candidate descriptions on `Question`.** Add an optional description per option (today options are a bare label list, `types.py:66-68`, rendered as `candidates: a | b`), rendered in the catalogue, so tool or element tables are grounded without stuffing the shared state. Unit tests; JSON and native arms both render it.
  - *Acceptance amendment 2026-09-23 (intake-1517):* descriptions must not hurt — compare with vs without descriptions on
    the TD-16 pairs and report the delta; a negative delta blocks using descriptions.
- [ ] **TD-15 — (conditional on TD-12) Native path for more than 36 candidates.** Only if TD-12 needs tables beyond the TD-9 code map (36 symbols, `routing_replay.py:153`) or the 128 `n_probs` cap (`native.py:259`): hierarchical codes or chunked candidate tables. Close as not-needed if TD-12 stays under 36.
  - [ ] **TD-15a — the chat-completions path caps `top_logprobs` at 20, not 128.** `src/backends/llama_server.py:709`
    (`payload["top_logprobs"] = max(1, min(int(_n_probs), 20))`) applies to every chat-completions role (frontdoor,
    gemma4 workers); only the native path allows 128 (`src/typed_decisions/native.py:300`, `_MAX_N_PROBS`). The 128
    ceiling above holds only for native-path roles. Before TD-12/TD-15 size a candidate table, state which path serves
    the target role, and either lift the chat-path cap (check the llama-server limit first) or budget for 20. Found by
    the 2026-09-28 Jev-techniques map (workspace-8d).
- [ ] **TD-16 — Label-word bias control on the native noul path.** Freeze hunch's 240 look-alike pairs (`hunch/lookalikes.py` @8bac3f2b, MIT; 80 pos / 160 neg) as a noul set. On the worker model at its current pin run (N) native noul as today, (C) the same question as a 2-option choice with neutral A/B keys and the yes/no conditions as option text, both orders, reported per order and averaged, (J) the JSON arm, plus question-only variants of N and C. Report AUROC, argmax accuracy, Brier, ECE, order disagreement and both constant baselines (always-no 66.7%, base-rate Brier 0.222) with paired-bootstrap CIs. If C beats N beyond the CI, TD-1c's 15/16 parity holds only for its 8-noul set. No gate follows (wiki/routing-intelligence.md L40). Evidence: intake-1517, intake-1502. Inference-gated — **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29); all arms, including (J), run on the sidecar so the comparison is like-for-like (a JSON-arm-only run keeps `mi210-window`).
  - *Acceptance amendment 2026-09-25 (intake-1618#record, intake-1634#record, intake-1635#record, intake-1636#record, intake-1637#record, intake-1654#record, intake-1655#record, intake-1656#record, intake-1657#record, intake-1677#record):* cross position, criteria/candidate order, opaque-key alphabet, key-to-description reassignment, semantic name/rubric rebinding, and answer-format conversion as distinct arms. Report mapped-back accuracy, probability divergence, flip rate, conjunction-based consistent accuracy, per-cardinality strata, and a repeat-only floor. A neutral key or one canonical sorted order is not evidence of invariance.
- [ ] **TD-17 — Frozen OOD calibration slice.** Zero-inference adapter over `scienthoon/jev-ood-calibration` `data/val.jsonl` @914d87a (sha256 763949cd…, CC0, byte-reproducible): 300 states x {queue choice, priority score 0-3 with level names as criteria, angry noul}; do not state the priority rule in the catalogue. Also a tier-ablated variant (drop `customer_tier`, fresh `--seed`) so priority depends on a genuinely hidden input. Report the TD-18 metric set per (model pin, catalogue) for the native and JSON arms. The calibrated target is mean max-prob ≈ accuracy, not a near-uniform priority. Cite only the corrected Jev temperatures (1.30 / 1.92), never 3.29 / 3.40 / 2.74. Evidence: intake-1504, intake-1516. The adapter is zero-inference; the run is **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29), native and JSON arms on the same sidecar (a JSON-arm-only run keeps `mi210-window`).
  - *Acceptance amendment 2026-09-25 (intake-1619#record, intake-1622#record):* add matched with-unknown and without-unknown fixtures. Report forced-choice error, abstain precision/recall, candidate eligibility, probability mass, and invalid responses; never infer abstention quality from confidence separation alone.
- [ ] **TD-18 — Calibration receipt upgrade (zero inference).** Extend the typed_decisions calibration receipt (today n, ECE, Brier, 10 bins; no floor, no model-pin field) with, per question kind: a resampled perfectly-calibrated ECE noise floor; a record/template-clustered paired bootstrap; tie-aware coverage at a stated error budget and AURC; NLL and refit-T sensitivity to the log floor and clamp; exact-0 / exact-1 endpoint rates; a flag when a fitted temperature lands on a search bound; a single in-distribution temperature with a group-disjoint out-of-fold check; and the model pin. Clean-room from the patterns in `kev/metrics.py` and `kev/calibrate.py` (Apache-2.0). Evidence: intake-1498, intake-1504, intake-1516.
  - *Receipt amendment 2026-09-25 (intake-1584#record, intake-1585#record, intake-1619#record, intake-1636#record, intake-1658#record, intake-1659#record, intake-1660#record, intake-1681#record):* record requested alias, resolved response model/build, model/head/base revisions, question and policy version, state and candidate fingerprints, adapter hash, effective config, region, concurrency, rate headers, price snapshot, typed failure cause, per-row prediction, fallback attribution, downstream outcome, raw timing samples, and deterministic report digest. The receipt must reconstruct one prior deterministic branch and detect deliberate drift mutations.
- [ ] **TD-19 — External OOD read via a `/v1/systemone` shim.** Expose our typed-decision path behind Kev's `/v1/systemone` contract (`kev/predictors.py:61-92`, `kev/benchmark.py:34-66`) and score it with `kev.benchmark --remote` on Kev's committed transfer-v4 dev (764 records) and scienthoon-v1. Multi-token candidates return JSON-arm probabilities; send options in insertion order (Kev is order-sensitive; gojev sorts keys). Report accuracy, ECE and coverage against the committed Kev/Jev reports — the Jev figures are report-level only, and the Kev-vs-Jev coverage CI already includes 0. Evidence: intake-1498, intake-1515. Inference-gated — **GATE: mi210-window** (operator ruling Q3, 2026-09-29).
- [ ] **TD-20 — (conditional on TD-19 showing a trained decider beats our path) Serve Kev-4B on llama.cpp-experimental.** Branch from fresh production ffc1bac; port `common/decision.{h,cpp}` + `tools/kev/kev-decide.cpp` + 2 CMake lines as new files with a sidecar `head.json` (no `src/` change, no fork merge). Source weights from `taigrr/kev-4b-gguf` at a pinned sha, sha256-verified against `manifest.json` (merged GGUF avoids the 4B/9B `out_proj` LoRA conversion gap). Parity vs HF-fp32 on committed decision-v7 dev rows plus fixtures with unsorted keys, a long state and 4B; test `seq_cp` fan-out against v10's recurrent rollback-index abort on shared cells. Evidence: intake-1498, intake-1514#00, intake-1514#05, intake-1515.
- [x] **TD-21 — Re-audit of every free-text JSON consumer (operator, 2026-09-24).** ✅ 2026-09-24 — every sub-row
  landed (the last, TD-21.33c, orch `c347600e`). Audit: `artifacts/audits/td-json-consumer-audit-20260924.md`.
  TD-21.0, TD-21.H, TD-21.1 and TD-21.2 … TD-21.35 (incl. TD-21.EQ1, TD-21.22a/b, TD-21.31 (a), TD-21.33a/b) are in
  the [completed ledger](../completed/typed-decision-plane-completed-through-2026-09-29.md). One residual stays here:
  - [x] **TD-21.1a — the FINAL() repair is INERT in production (OP-51).** All REPL schema validation — and so TD-21.1's
    repair and 422 — sits behind `final_schema_validation` (default OFF since `86957b6e`; production runs
    `baseline`). Live 11:53Z: `/chat` `force_mode=repl` with `output_schema {result: int}` returned the bare `51`, no
    error. Enabling is a production-posture pin in `orchestration/runtime_flags.spec.yaml` (reason + since) plus the
    live flag; it changes what `/chat` callers receive (a conforming object or a 422, instead of an unvalidated
    value). Recommendation: enable.
    - *2026-09-24:* OP-51 enabled (orch `98edfeb0`, `PRODUCTION_FEATURE_WAVE_OVERRIDES`), API reloaded. First
      live smoke (13:41Z) of REPL `/chat` (`{17*3, output_schema {result:int}}`) returned **HTTP 500**
      "repeated no-progress nudges at `coder_escalation`" (flag off it returned `51`), with `Model fallback:
      coder_escalation → frontdoor (connection_error)` in the logs although :8083 is healthy. Operator chose to
      **SUSPEND** → orch `6b26f3ae` (flag back OFF), API reloaded 13:48:02Z. Kept `[ ]` — regression diagnosis
      in flight (schema preamble ```` ```json ```` fence vs escalation routing).
    - [x] Root-cause the `coder_escalation → frontdoor (connection_error)` fallback logged during the OP-51
      smoke even though :8083 answers health checks — a live routing/connection defect independent of the
      schema-validation flag itself, surfaced only because OP-51 exercised the escalation path.
      ✅ 2026-09-30 — explained, not a routing defect. The ✅ note below attributes the 13:41Z failures to
      placement timeouts behind an AutoKernel CPU-floor calibration holding the whole CPU region, with a clean A/B
      at 15:35Z once the region was free. The `connection_error` label itself was a misclassification: the
      contention-gate denial of a healthy, busy backend fell through `health_tracker.classify_failure`'s string
      default to `connection_error`. Orch `8977f540` (2026-09-24, on main) classifies it structurally as
      `admission_denied` (`FailoverReason.ADMISSION_DENIED`, `src/roles.py`; `src/api/health_tracker.py`).
    ✅ 2026-09-24 — ON in production (orch `07fcf422`). History: enabled `98edfeb0`; the 13:41Z smoke's HTTP 500
    and the first A/B (all arms failing, flag on AND off, and the last-good d12202f2 too) were placement
    timeouts behind an AutoKernel CPU-floor calibration holding the whole CPU region — the REPL masked them as
    "all comments" no-progress failures (fixed: orch `32a52fba`, infra sentinels end the turn with the right
    status; live check → HTTP 504 in 1 turn). Suspended `6b26f3ae` meanwhile. Clean A/B 15:35Z with the region
    free: on 3/3 HTTP 200 `{"result": 51}`, off 3/3 HTTP 200 bare `51`, 1 turn each. (DS41 run 8 held the region
    ~13:43Z→15:32Z, stopped by the operator; the region-hog-vs-production-serving policy question is evidence
    under `autokernel-unified-surface-program.md` U4-SEQ, not a new decision — OP-41 already rules that space.)

## Immediate ROI path — 2026-09-25

- [x] **TD-22 — Refresh the public Jev contract and evidence boundary.** ✅ 2026-09-25 — Current official material was consolidated into intake-1470#record and intake-1472#record: moving aliases require resolved-model capture; current limits are dynamic; same-request questions inspect one shared state independently; dependent decisions require another call or host composition; host code owns permission, freshness, candidate existence, and outcome verification; current latency language is vendor guidance rather than an SLA; the hierarchy result is a four-case smoke; and the independent day-run cost report supplies no labels or public replay.
- [ ] **TD-23 — Shared typed-decision screen.** After the CJ-15 fixture and HS-TD-4 receipt exist, compare one available local compact decision backend against the constrained incumbent readout on one sealed, row-pinned workload (operator ruling Q1, 2026-09-29: local models only; the hosted-Jev arm is removed). Freeze the manifest, backend/model revisions, requested/resolved identities, candidate descriptions, prompts, threshold-selection split, and held-out source groups; retain per-row probabilities and raw outputs, invalids, failures, abstentions, timing, and cost in `decision_receipt.v1`. Cross position, order, opaque keys, semantic rebinding, response format, repeated calls, irrelevant siblings, explicit unknown, and long-context placement; report accuracy, consistent accuracy, ECE/Brier, flip rates, probability divergence, clustered intervals, and total decision cost. Predeclare quality, calibration, and operations stop/promotion thresholds; keep same-state independent questions, staged dependent decisions, and hierarchy search as separate protocol classes. This is the common cheap screen under the [minimum viable research execution contract](eval-tower-verification.md#minimum-viable-research-execution-contract), not a paper-wide reproduction. Sources: intake-1577#record, intake-1583#record, intake-1606#record, intake-1618#record, intake-1619#record, intake-1623#record, intake-1634#record, intake-1637#record, intake-1654#record, intake-1660#record, intake-1676#record, intake-1681#record. The run is **GATE: mi210-window** (operator ruling Q3, 2026-09-29).

### Trigger records — materialize only when the named condition fires

- **TD-24 — GLiNER2.5-Decide follow-on.** Activate only if the GLiNER backend in TD-23 clears the held-out quality, calibration, and operations gate or EPYC needs a claim-bearing public reproduction. Then pin model, library, and Fast Decisions revisions; pass `multi_label`; emit all 2,900 public rows and per-head outputs; report macro-domain and pooled-head exact match separately; and test constraint invariance, brute-force optimality on small schemas, candidate retention, infeasibility behavior, and `Classifier` versus `classify_text`. Do not claim the unavailable held-out result. Sources: intake-1586#record, intake-1587#record, intake-1588#record.
- **TD-25 — CLM specialized-head follow-on.** Activate only if the released default head in TD-23 clears the held-out quality, calibration, and operations gate. Pin exact base/head hashes and candidate-description policy; a task-specific projection head may enter shadow only after a group-disjoint comparison beats the incumbent on quality and calibration. Default-head JevBench results cannot substitute for that gate, and full three-stage training remains dormant until this candidate gate passes. Sources: intake-1581#record, intake-1589#record, intake-1590#record, intake-1591#record.
- **TD-26 — Phishing transfer.** Activate when phishing classification becomes an EPYC product or benchmark workload. Freeze the PhishNChips CSV, revision, licenses, prompts, and raw calls; report its synthetic arm separately from a pinned real-email split, with proper scores, order/key controls, model resolution, per-row outputs, and uncertainty. Sources: intake-1659#record, intake-1678#record.
- **TD-27 — BTZSC replay.** Activate when BTZSC-style classification becomes an active benchmark or claim surface. Replay historical commit `8a0d52cbe423` and current v0.1.2 separately, freezing rows, models, verbalizers, prompts, permutations, hardware, precision, failures, and raw timings. Alphabetical label sorting is one deterministic assignment, not robustness evidence. Sources: intake-1660#record, intake-1679#record, intake-1680#record, intake-1681#record.

## Wiring policy (2026-09-18, operator-directed)

- **Fan-out decision rule (TD-8, implemented in `src/typed_decisions/fanout_policy.py`):** exactness-required + native-eligible -> native id-only per question (11.98x n=1, contested: 9.60x at n=4 pending TD-1d.0; isolated); stability-tolerant batches of >= 8 -> batched (2.2x at 87.5% measured agreement); otherwise sequential JSON. The 87.5% figure governs the choice per surface.
- **Tool arguments (item 1):** closed-set wiring landed in the orchestrator tool path (`src/repl_environment/context.py` `_dispatch_tool`) behind `typed_decisions_tool_args` (default off), fail-open to model-provided args. Shadow-only until v11 (operator ruling Q4, 2026-09-29): TD-29.
- **Deferred but tracked:** routing replay -> TD-7; judge redundancy -> CJ-13/CJ-14 in `canonical-judge-suite-revamp.md`; episodic pre-write gate -> M-19 in `episodic-memory-integrity.md`; harness items -> HS-TD-1..3 in `harness-selection-and-integration.md`.
- [x] **TD-8 — Fan-out policy helper.** Implemented + 18 tests (`fanout_policy.py`, provenance-stamped constants). ✅ 2026-09-18

## Open Questions

- Which confidence statistic, if any, survives local calibration well enough to gate an action?
- Does the production server's (`production-consolidated-v10`, final freeze 2026-09-22; the question was first asked against frozen v9) json_schema→GBNF converter accept the nested probability-map schemas the adapter generates?
- Does question-order contamination on our stack reproduce the 24.7% seen in intake-1486, or is it smaller at our batch sizes?

## Notes

All numbers above are from dive-verified entries; none may be promoted to a deployment measurement until TD-2/TD-3
produce our own. This stub follows the 2026-09-17 operator steering; the vendor's own documentation states confidence
is an undisclosed statistic and calibration is group-level only.
