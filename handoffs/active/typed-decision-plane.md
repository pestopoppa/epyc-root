# Typed Decision Plane — one-pass typed decisions over the local stack

**Status**: in progress — **Owner: the research-intake lane** (operator-assigned 2026-09-17 to `intake-jev-sageattn`; that session is closed, and the lane owns this handoff from 2026-09-23). *Ownership note (operator-directed tidy 2026-09-26):* ownership is unchanged, but TD-21 and every TD-21.N row, plus the TD-1d.1/TD-1d.2/TD-1d.5 closures, were executed 2026-09-24 by a separate operator-dispatched main session with no roster lane (`workspace-8d`; `progress/2026-09/2026-09-24-td21.md`, `progress/2026-09/2026-09-24-main-ak-seat.md:123`), not by the research-intake lane. Implementation landed in `epyc-orchestrator` main from branch `intake/jev-typed-decisions-20260917` (merged; its worktree was retired 2026-09-23 — cut a fresh lane worktree from origin/main for new TD work).
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Categories**: routing_intelligence, cost_aware_routing, inference_serving, tool_implementation, agent_architecture
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Evidence**: intake-1472, intake-1473, intake-1474, intake-1485, intake-1486, intake-1487, intake-1490 (all dive-verified); intake-1476#record (application survey, anecdote-grade)

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

## Tasks

- [x] **TD-1 — Implement the local typed-decision call path over the frozen v9 server.** ✅ 2026-09-17 (epyc-orchestrator branch `intake/jev-typed-decisions-20260917`: `src/typed_decisions/` types/schema/runner/confidence, flag `typed_decisions` default off, not wired to any route; 31 unit tests green; native mode deliberately deferred to TD-1a). Per-request JSON-Schema
  generation from declared questions (choice/score/noul), one chat completion with `response_format
  json_schema`, client-side decode + validation with corrective retry, expected-value scoring, local confidence
  statistics (fixed formulas + one documented alternative), and a per-call diagnostics record. Cite intake-1472
  (contract) and intake-1473 (pattern set). Acceptance: a fixture of ≥20 questions returns schema-valid typed
  answers with per-question probabilities; malformed-output retry path exercised.
- [x] **TD-1a — Native candidate-scoring fast path (the actual speed lever).** Implement the local one-pass mechanism:
  enum-constrained single-token readout with per-question probabilities (`response_format json_schema` enum +
  `n_probs`/`completion_probabilities`) over a shared prompt prefix with prompt-cache reuse, batching multiple
  questions into as few requests as the server allows. Benchmark it against TD-1's JSON-schema generation path —
  wall time, output tokens, argmax agreement, and cache-reuse drift (intake-1487 measures 5-6/777 argmax flips
  under BF16 reuse; intake-1474 measures 3.4-7.9x for the pattern vs same-model naive JSON). Acceptance: our own
  **2026-09-17 live validation found the mechanism broken (23/24 `native_unknown_candidate`); superseded by TD-1b (tokenization) and TD-1c (parity), both landed the same day.**
- [x] **TD-2 — Measure cross-question contamination and confidence calibration before any gate.** On a frozen
  EPYC decision set: (a) question-order permutation on one batched call vs single-question calls, report
  top-answer flips; (b) ECE / reliability of the local confidence statistic per model and schema. Acceptance:
  ✅ 2026-09-17 measured on MI210 (GPU, frozen-v9 HIP server; receipts + vidya frames ingested; metric_direction recorded): contamination flip rate 6.25% (27B, 3/48 pairs) vs 37.5% (LFM2.5-2.6B, 18/48) on the 24-question decision set; calibration accuracy 91.7% / mean confidence 0.8875 / ECE 0.0625 / Brier 0.078 (27B) vs 50.0% / 0.567 / 0.267 / 0.313 (LFM) — one 27B miss at ~0.90 confidence, so the tail is not empty. TD-5 gate: SATISFIED for a first shadow.
- [x] **TD-3 — Measure speculative fan-out locally.** Fixed state, N batched questions in one call vs N
  singleton calls, cache-warm; report serial-sum and concurrent wall-clock plus token cost. ✅ 2026-09-17 measured on the GPU (LFM2.5-2.6B): 3 batched calls vs 12 singleton calls over 3 states x 4 questions = 1.54x serial/wall speedup at 100% agreement; the saving is per-call overhead at this small state size. **Long-context replication (2026-09-17, Qwen3.6-35B-A3B, three 40k-char states): 3.22x (33.9 s batched vs 109.2 s singleton).** The agreement metric in that run is NOT interpretable — the fan-out probe catalogue is deliberately content-neutral, so its answers are unanchored. Vendor multipliers stay banned.
- [x] **TD-1b — Tokenizer-aware native candidates.** Obtain each candidate's token id(s) from the server (`/tokenize`) or a tokenizer before building the native grammar and matching probabilities; native mode must not presume single tokens, and multi-token candidates must fall back to JSON mode explicitly. ✅ 2026-09-17 mechanically fixed and live-validated on Qwen3.6-35B-A3B (MI210): candidate tokenization via the server /tokenize seam, grammar positions as exact-token terminals `<[id]>` (quoted literals expand per-character — that was the `fal` failure), probability rows matched by token id. Result: **0 `native_unknown_candidate` failures, 8/24 `native_unsupported_candidates` by design** (mammal/reptile/oregon/vermont/arizona/alaska tokenize multi-token), 16/24 natively resolved, **1.03 s vs 19.4 s = 18.9x faster** than the JSON arm. NOT yet semantically equivalent: agreement 11/16, native accuracy 68.8% vs JSON 91.7% on the overlap (a false-bias on noul) -> TD-1c.
- [x] **TD-1c — Native semantic parity.** Close the 5/16 disagreement between native and JSON arms before the speed is trusted: check the native prompt's answer cueing vs the JSON prompt, whether the candidate slice is over pre- or post-grammar probabilities, and per-position conditioning (later answers are generated after earlier ones). ✅ 2026-09-17 accepted: root cause was prompt cueing — only the first answer was grounded on the prompt; later positions were conditioned on prior answer tokens, collapsing noul answers to false. Fix replays each question's cue as tokenized grammar terminals so every answer follows its own question. Live on the worker: **agreement 15/16 = 93.75%**, native 15/16 correct on the overlap (JSON 22/24 overall), 8.1 s vs 16.9 s = **2.08x** — parity at a speed cost; recovering the 18.9x is TD-1d.
- [x] **TD-3b — Meaningful fan-out agreement.** ✅ 2026-09-17 measured on the worker with the real 24-question catalogue: **agreement 87.5% (21/24) at 2.2x** (17.2 s batched vs 37.9 s singleton) — a quantified speed/stability trade-off for the fan-out lever; consistent with the 6.25% order-flip rate (27B) and far from the LFM's 37.5%.
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
      alone. Inference-gated (one short window; the whole sweep above took ~20 min including model load).
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
  intake-1473 adapter. ✅ 2026-09-17 live pilot on the worker (18 deterministic cases, 3 tool schemas): **closed-set 18/18 exact-match (0 failures) vs free-form 6/18 (12 failures)**, per-arg exact 66 vs 24, at 116.6 s vs 11.4 s (10.2x wall). Exact tool use is the closed-set arm's to win; the free-form arm's failures are parse/schema failures, not merely wrong values. Coordinate with `tool-use-eval-contract.md` (TU-TD-1 there).
- [x] **TD-5 — One shadow integration after TD-2 passes.** Wire the typed-decision call into exactly one live
  surface as a shadow arm (routing classifier or judge, chosen by the owning handoff), gated on TD-2's
  calibration result. **2026-09-17: IMPLEMENTED + SMOKE-VALIDATED.** `src/typed_decisions/shadow.py` wired at `routing.py` (`_plan_review_gate`), flag `typed_decisions_shadow` default off, fixed canonical order, non-blocking bounded daemon (MAX_PENDING=4, drops counted), fail-open, JSONL log via `ORCHESTRATOR_TYPED_DECISIONS_SHADOW_LOG`. Live smoke against the 35B produced one well-formed record (incumbent + decisions + confidences + prompt/state hashes). Next: enable it for a real window and accumulate labeled outcomes (the calibration set), then report agreement + calibration. No enforcement without operator approval.

- [x] **TD-9 — Routing candidate redesign + belief-kernel wiring.** Map role candidates to single-token codes (A-E) with a code→role map so the native id_only arm can engage, fix the question framing (incumbent-aware; the SELF bias dominates today), and extend the vidya adapter `STUDIES` with `routing_replay` before the next run. ✅ 2026-09-18: deterministic code map (A..Z,0..9) with per-row incumbent-aware framing and a /tokenize preflight; live N=200 on the frozen snapshot: **native resolution 200/200**, **agreement 93.5% (187/200, Wilson 89.2-96.2%)**, AUROC **0.758** vs the frozen label (incumbent-label caveat in-receipt), 590 ms/row, 0 failures. All 13 disagreements pick ARCHITECT with lower confidence (0.448 vs 0.662) — incumbent anchoring, not demonstrated routing skill. Belief-kernel `routing_replay` study wired and the receipts ingested.
  - *Receipt note 2026-09-23 (intake-1521 write-side check):* the same receipt also carries ECE 0.2416, Brier 0.1514 and a
    label base rate of 0.89 against the incumbent label — the AUROC 0.758 is not calibration evidence.
- [x] **TD-6 — Adopt `id_only` as the native default after review.** The cue sweep measured 11.98x at 15/16 agreement for `id_only` (vs 2.66x `full`); ✅ 2026-09-18 adopted: native default is now `id_only` (11.98x at 15/16 measured); `full`/`short` remain selectable, JSON arm unchanged.
  - ⚠️ *Sequencing note (operator-directed tidy 2026-09-26):* this adoption (orch `0fd94a89`, 2026-09-18 12:39Z)
    landed ~12 h after the TD-1d re-measurement (root `742b5753`, 00:28Z) filed **TD-1d.0**, which says "do not
    adopt id_only as the native default on the n=1 number alone" — and it still cites that n=1 11.98x. The n=4
    re-measure gives **9.60x** (1.46 s vs 14.02 s mean) and **6.40x per decision** (native decides 16/24), both
    below the 10x bar (receipt `artifacts/typed_decisions/run_20260918/summary-td1d.json`). id_only is still the
    fastest native arm under both measurements, so **the default stands pending TD-1d.0**; no code default was
    changed by this note, and the orchestrator docstrings/`MEASURED_CONSTANTS` provenance now carry the same caveat.
- [x] **TD-7 — TD-5 live replay on the recorded routing corpus.** Build a state adapter from the recorded routing decisions (reference: ~54,960 rows with 22-33% per-role failure in learned-routing-controller) and replay N=100-200 through the shadow path; report typed-vs-incumbent agreement and confidence-vs-outcome calibration. ✅ 2026-09-18 ran on the admissible frozen snapshot (`orchestration/repl_memory/sessions/episodic.db.backup-20260415`, sha256 12ca8b0b…, max(created_at) 2026-04-15 — pre-purge; live DB refused by design). N=200: **agreement vs incumbent 3.0% (6/200, Wilson 1.4-6.4%)**; **native 0/200** — every routing action label is multi-token (`frontdoor`=front+door), so all rows took the JSON fallback; the model shows a strong SELF bias (177/200 at ~0.975 confidence); **AUROC 0.50** vs the frozen success label and ECE 0.10, with the caveat that the frozen label describes the incumbent action, not the chosen one (flagged in-receipt). Diagnostic outcome: the harness works; candidate/token design is the blocker. Receipts under artifacts/typed_decisions/run_20260918/.

**Declined (2026-09-17):** no new belief-kernel carrier for bench/cue-sweep reports — they are screening instruments, not protocol-grade measurements (the strict reader refuses them by design); revisit only if a `P-TDP` measurement protocol is ratified.

- [x] **TD-10 — Counterfactual evaluation of the TD-9 routing policy (model-based OPE).** ✅ 2026-09-18: reused the escalation probe's cross-fitted, embedding-grouped estimator over the frozen snapshot with freshly embedded states; **delta typed-minus-incumbent = -0.0104** (CI95 [-0.0246, -0.0066], 5 folds all negative; ~1pp worse). Verdict: **enforcement stays OFF** — agreement is not skill; the 13 departures (frontdoor->ARCHITECT) are estimated harmful. Caveats: model-based estimate with the probe's EPD-1..3 confounds; unevaluable actions excluded.
- [ ] **TD-11 — Routing prompt/policy improvement, re-tested through the counterfactual harness.** The harness now measures value, not agreement; use it to iterate (framing, support-aware candidates, leave-one-out conditioning) before any enforcement proposal. Acceptance: positive delta with a CI excluding zero on the frozen snapshot, or a written decision to drop typed routing.

- [ ] **TD-12 — One-call tool + argument arm (operation × conditional target).** Build a typed-decision arm that asks, in one call, a choice over the role's tools (`ToolRegistry.list_tools(role)`) plus one argument head set per candidate tool whose instructions name the tool they assume, and consume only the chosen tool's heads. A failed head for an UNUSED tool must not reject the pass (today any failure rejects it: `tool_args_integration.py:197-198`). Compare against the current tool-then-arguments path (TD-4) on exact-match tool+argument correctness and wall time over the TD-4 case set extended with a tool-choice step. Citation: intake-1493 (dive-verified; `jev_ultrafast/model.py:94-133` @ 1231850a).
- [ ] **TD-13 — Contamination between the operation head and its conditional heads.** Before TD-12's heads are trusted as independent: for each case, answer the chosen tool's argument heads alone and batched with the sibling (unused) tools' heads; report top-answer flip rate per model. Existing receipts (TD-2, TD-3b) cover flat catalogues only. Acceptance: flip rate reported for the worker model; TD-12 adoption gated on it.
  - *Acceptance amendment 2026-09-25 (intake-1577#record, intake-1583#record):* randomize and interleave two dependency controls: move one sentinel fact between shared state and an unused sibling head, and prepend/append one semantically irrelevant candidate inside the chosen head. Report chosen-answer flips and pairwise log-odds among unchanged candidates. Treat any effect as a behavioral dependency; do not infer an attention mask, prefix-cache layout, or readout architecture.
- [ ] **TD-14 — Per-candidate descriptions on `Question`.** Add an optional description per option (today options are a bare label list, `types.py:66-68`, rendered as `candidates: a | b`), rendered in the catalogue, so tool or element tables are grounded without stuffing the shared state. Unit tests; JSON and native arms both render it.
  - *Acceptance amendment 2026-09-23 (intake-1517):* descriptions must not hurt — compare with vs without descriptions on
    the TD-16 pairs and report the delta; a negative delta blocks using descriptions.
- [ ] **TD-15 — (conditional on TD-12) Native path for more than 36 candidates.** Only if TD-12 needs tables beyond the TD-9 code map (36 symbols, `routing_replay.py:153`) or the 128 `n_probs` cap (`native.py:259`): hierarchical codes or chunked candidate tables. Close as not-needed if TD-12 stays under 36.
- [ ] **TD-16 — Label-word bias control on the native noul path.** Freeze hunch's 240 look-alike pairs (`hunch/lookalikes.py` @8bac3f2b, MIT; 80 pos / 160 neg) as a noul set. On the worker model at its current pin run (N) native noul as today, (C) the same question as a 2-option choice with neutral A/B keys and the yes/no conditions as option text, both orders, reported per order and averaged, (J) the JSON arm, plus question-only variants of N and C. Report AUROC, argmax accuracy, Brier, ECE, order disagreement and both constant baselines (always-no 66.7%, base-rate Brier 0.222) with paired-bootstrap CIs. If C beats N beyond the CI, TD-1c's 15/16 parity holds only for its 8-noul set. No gate follows (wiki/routing-intelligence.md L40). Evidence: intake-1517, intake-1502. Inference-gated, one short window.
  - *Acceptance amendment 2026-09-25 (intake-1618#record, intake-1634#record, intake-1635#record, intake-1636#record, intake-1637#record, intake-1654#record, intake-1655#record, intake-1656#record, intake-1657#record, intake-1677#record):* cross position, criteria/candidate order, opaque-key alphabet, key-to-description reassignment, semantic name/rubric rebinding, and answer-format conversion as distinct arms. Report mapped-back accuracy, probability divergence, flip rate, conjunction-based consistent accuracy, per-cardinality strata, and a repeat-only floor. A neutral key or one canonical sorted order is not evidence of invariance.
- [ ] **TD-17 — Frozen OOD calibration slice.** Zero-inference adapter over `scienthoon/jev-ood-calibration` `data/val.jsonl` @914d87a (sha256 763949cd…, CC0, byte-reproducible): 300 states x {queue choice, priority score 0-3 with level names as criteria, angry noul}; do not state the priority rule in the catalogue. Also a tier-ablated variant (drop `customer_tier`, fresh `--seed`) so priority depends on a genuinely hidden input. Report the TD-18 metric set per (model pin, catalogue) for the native and JSON arms. The calibrated target is mean max-prob ≈ accuracy, not a near-uniform priority. Cite only the corrected Jev temperatures (1.30 / 1.92), never 3.29 / 3.40 / 2.74. Evidence: intake-1504, intake-1516. The run needs one short window.
  - *Acceptance amendment 2026-09-25 (intake-1619#record, intake-1622#record):* add matched with-unknown and without-unknown fixtures. Report forced-choice error, abstain precision/recall, candidate eligibility, probability mass, and invalid responses; never infer abstention quality from confidence separation alone.
- [ ] **TD-18 — Calibration receipt upgrade (zero inference).** Extend the typed_decisions calibration receipt (today n, ECE, Brier, 10 bins; no floor, no model-pin field) with, per question kind: a resampled perfectly-calibrated ECE noise floor; a record/template-clustered paired bootstrap; tie-aware coverage at a stated error budget and AURC; NLL and refit-T sensitivity to the log floor and clamp; exact-0 / exact-1 endpoint rates; a flag when a fitted temperature lands on a search bound; a single in-distribution temperature with a group-disjoint out-of-fold check; and the model pin. Clean-room from the patterns in `kev/metrics.py` and `kev/calibrate.py` (Apache-2.0). Evidence: intake-1498, intake-1504, intake-1516.
  - *Receipt amendment 2026-09-25 (intake-1584#record, intake-1585#record, intake-1619#record, intake-1636#record, intake-1658#record, intake-1659#record, intake-1660#record, intake-1681#record):* record requested alias, resolved response model/build, model/head/base revisions, question and policy version, state and candidate fingerprints, adapter hash, effective config, region, concurrency, rate headers, price snapshot, typed failure cause, per-row prediction, fallback attribution, downstream outcome, raw timing samples, and deterministic report digest. The receipt must reconstruct one prior deterministic branch and detect deliberate drift mutations.
- [ ] **TD-19 — External OOD read via a `/v1/systemone` shim.** Expose our typed-decision path behind Kev's `/v1/systemone` contract (`kev/predictors.py:61-92`, `kev/benchmark.py:34-66`) and score it with `kev.benchmark --remote` on Kev's committed transfer-v4 dev (764 records) and scienthoon-v1. Multi-token candidates return JSON-arm probabilities; send options in insertion order (Kev is order-sensitive; gojev sorts keys). Report accuracy, ECE and coverage against the committed Kev/Jev reports — the Jev figures are report-level only, and the Kev-vs-Jev coverage CI already includes 0. Evidence: intake-1498, intake-1515. Inference-gated, one window.
- [ ] **TD-20 — (conditional on TD-19 showing a trained decider beats our path) Serve Kev-4B on llama.cpp-experimental.** Branch from fresh production ffc1bac; port `common/decision.{h,cpp}` + `tools/kev/kev-decide.cpp` + 2 CMake lines as new files with a sidecar `head.json` (no `src/` change, no fork merge). Source weights from `taigrr/kev-4b-gguf` at a pinned sha, sha256-verified against `manifest.json` (merged GGUF avoids the 4B/9B `out_proj` LoRA conversion gap). Parity vs HF-fp32 on committed decision-v7 dev rows plus fixtures with unsorted keys, a long state and 4B; test `seq_cp` fan-out against v10's recurrent rollback-index abort on shared cells. Evidence: intake-1498, intake-1514#00, intake-1514#05, intake-1515.
- [x] **TD-21 — Re-audit of every free-text JSON consumer (operator, 2026-09-24).** ✅ 2026-09-24 — every
  sub-row landed (the last, TD-21.33c, orch `c347600e`). The consumer list for
  TD-1 never named the AutoKernel loop actors, which fished JSON out of free text with `_extract_json` and
  retried 90-minute calls when it failed; that was closed 2026-09-24 in `epyc-inference-research`
  `ad2b89ff` (`scripts/kernel_rnd/autokernel/loop/actors.py` `_parse_reply` / `_schema_repair` — fish first,
  then ONE `response_format json_schema` turn at temperature 0 back to the SAME local server, plus a stage-1
  boolean decline probe so an abstention is never fabricated; measured on the 27B at :8083, five shapes
  correct in 2-12 s, three designs refuted on the way). A full re-audit of both stacks follows. **Audit file:
  `artifacts/audits/td-json-consumer-audit-20260924.md`** (62 consumers classified; 36 still fish structured
  output out of free text, 31 of those reachable by the same-server repair idiom; 13 write a silent default
  into persisted state or serve it to a user, 6 retry a full call from zero, 9 score a parse failure as a
  wrong answer). Cite intake-1472 (contract) and intake-1473 (pattern set); the measured warrant is TD-4
  (closed-set 18/18 vs free-form 6/18, the free-form failures being parse/schema failures) and the 2026-08-13
  review-plane rate of 4.1% parse failure over 1,366 `review_decision` events.
  - [x] **TD-21.0 — PREREQUISITE: forward `response_format`/`json_schema` on the `/v1` chat payload.**
    `src/backends/llama_server.py:607-616` (and the streaming variant at `:1397`) builds the chat payload with
    `messages`/`max_tokens`/`stream`/`tools`/`logprobs`/`stop`/`chat_template_kwargs` and **no schema field**,
    while the native `/completion` builder forwards both (`:1228-1231`). So every role on the `/v1` lane —
    `frontdoor`, `worker*`, `toolrunner` (:8070/:8080/:8180) and `architect_critic` (:8074) — is silently
    unconstrained even when the caller passed a schema, and `/chat`'s `output_schema` (`direct_stage.py:133`)
    is advisory for exactly those roles. **This is TD-1d.1, and the actors.py measurement shrinks it**:
    llama-server's own `/v1` DOES honour `response_format json_schema` (`actors.py:305-318`, live on :8083),
    so the fix is three lines in our payload builder, not a declared `/completion` lane. Every TD-21.x
    conversion on a `/v1`-lane role is a no-op until this lands. Zero inference to decide.
    ✅ 2026-09-24 — orch `b284ede3`: `_apply_schema_constraint` puts `response_format {type: json_schema}` and a
    raw `grammar` on both the non-streaming and streaming `/v1` builders (every `llm_call` reaches them through
    `_call_caching_backend` → `LlamaServerBackend.infer`); no-schema payloads are byte-identical; also fixed audit
    X5 (`direct_stage.py` retry now forwards `n_probs`). 121 tests. Gates: `stack_change_pipeline check` at its
    4-known-gap baseline, `validate_or_raise` OK, runtime attestation n/a (API-only change). API reloaded 09:57Z
    (no autopilot, 0 connections on :8000); verified live — see TD-1d.1. Server note (frozen tree): with
    `response_format` and `grammar` both set, precedence is chat-format-dependent, so callers pass one.
  - [x] **TD-21.H — shared repair helper** ✅ 2026-09-24 — orch `c4570158` + `577ccc5e`:
    `src/structured_output/repair.py` — `fish_json` (string-aware, fences first), `parse_with_repair` (fish →
    full-schema Draft 2020-12 validation → optional stage-1 boolean decline turn → one extraction turn →
    typed `failed`; never fabricates), `http_chat_completer` (temperature 0, thinking off, `model` on the wire)
    and `primitives_completer`; counters `STRUCTURED_OUTPUT_REPAIR_COUNTS`. Closes the reference's TD-21.30
    (b)(d)(e) weaknesses in the shared copy. 33 tests; live smoke on :8070: prose → `repaired` in one call,
    an explicit refusal → `declined`, never a fabricated object.
  - [x] **TD-21.1 — `repl_executor.py:671` REPL `FINAL()` schema validation** (validator `src/graph/helpers.py:1336`).
    Shape: the caller's `request.output_schema`. Today: strict `json.loads` + jsonschema with **retry from zero**
    — `turns=0`, role reset, the entire `run_task` graph re-run, up to 2 attempts, then the invalid answer is
    returned anyway. Action: adopt the TD-1 repair turn before the graph re-run. Highest failure cost in either repo.
    ✅ 2026-09-24 — orch `d7202dc9`: on FINAL() schema failure ONE `parse_with_repair` turn (`site="repl_final"`,
    producing role) runs before any graph re-run; fish-only recovery costs 0 calls, a hit costs 1 and no re-run; a
    miss falls back to the old retry-from-zero path. Terminal defect fixed: exhausted → `error_code=422` +
    `error_detail`, so `/chat` returns 422 with the full response body instead of a silent 200. No backfill.
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
    - [ ] Root-cause the `coder_escalation → frontdoor (connection_error)` fallback logged during the OP-51
      smoke even though :8083 answers health checks — a live routing/connection defect independent of the
      schema-validation flag itself, surfaced only because OP-51 exercised the escalation path.
    ✅ 2026-09-24 — ON in production (orch `07fcf422`). History: enabled `98edfeb0`; the 13:41Z smoke's HTTP 500
    and the first A/B (all arms failing, flag on AND off, and the last-good d12202f2 too) were placement
    timeouts behind an AutoKernel CPU-floor calibration holding the whole CPU region — the REPL masked them as
    "all comments" no-progress failures (fixed: orch `32a52fba`, infra sentinels end the turn with the right
    status; live check → HTTP 504 in 1 turn). Suspended `6b26f3ae` meanwhile. Clean A/B 15:35Z with the region
    free: on 3/3 HTTP 200 `{"result": 51}`, off 3/3 HTTP 200 bare `51`, 1 turn each. (DS41 run 8 held the region
    ~13:43Z→15:32Z, stopped by the operator; the region-hog-vs-production-serving policy question is evidence
    under `autokernel-unified-surface-program.md` U4-SEQ, not a new decision — OP-41 already rules that space.)
  - [x] **TD-21.2 — `scripts/autopilot/controller_io.py:739` autopilot ACTION block.** Shape: the fenced
    `json:autopilot_actions` object. Today: marker-index fish; on a miss the provider is failed, one fallback
    provider is re-prompted **from zero**, and a deterministic `seed_batch` default action is written into the
    journal. Action: adopt TD-1 against the local planner (`AUTOPILOT_LOCAL_PLANNER_URL`, :8000) at
    `_loads_json_payload` (`:687`), which is the natural hook. Highest call volume in the audit.
    ✅ 2026-09-24 — orch `4b4b30b8` + `dd07cedd` + `e3401b47`: `extract_action_with_repair` fishes first (0 calls on
    a clean draft), then one repair turn against a `oneOf` over all 15 `_ACTION_SCHEMAS`, sent to the role's
    llama-server (`get_config().server_urls`, default frontdoor — a first draft targeted :8000, which refuses
    `response_format`, caught in review). A live smoke then showed the repair INVENTING a required `tier`; the
    shared helper gained `require_evidence` (repaired numbers / short strings must appear in the reply), ON here.
    Live 11:25Z: no tier in the draft → `failed` (unevidenced `tier`); "tier 1" → `{"type":"deep_eval","tier":1}`.
    Journaled with `action_parse_status` / repair calls; no backfill. Also fixed an uncaught `ValueError` on an
    unterminated fence in `extract_action`.
  - [x] **TD-21.3 — `scripts/autopilot/controller_io.py:776` action RATIONALE block.** Shape:
    `json:autopilot_rationale`. Today: same fish; returns `{}` silently and an empty rationale is persisted.
    Action: adopt TD-1 (same repair call as TD-21.2).
    ✅ 2026-09-24 — same commits: `extract_rationale_with_repair`, evidence-guarded; an absent block stays the soft
    empty default, a malformed one is repaired or flagged `failed` instead of an indistinguishable empty default.
  - [x] **TD-21.4 — `src/api/routes/chat_delegation_decision.py:47,:107` TOON delegation decision.** Shape: a
    closed set — `D|<answer>` vs `I|brief:…|to:<role>|mode:<react|repl>`. Today: ~8 stacked regexes with **no
    failure mode** — unparsed architect prose is wrapped as `D|<prose>` and served as the user-visible answer,
    and `delegate_to`/`mode` are silently clamped. Action: adopt TD-1, or better a native enum (the decision
    is `{direct, investigate} x role x mode`). Server: `architect_general` :8083, already on the `/completion`
    lane, so no TD-21.0 dependency.
    ✅ 2026-09-24 — orch `dc36350f`: `resolve_architect_decision` — strict fish (0 extra calls, happy path
    byte-identical over 188 existing tests), then one repair turn on the same architect role against a schema
    whose `delegate_to`/`delegate_mode` enums come from the live allow-lists. Repair failure: a ≤50-char reply
    is kept as a short direct answer (the parser's own threshold); longer prose becomes the `[ERROR:` sentinel the
    loop already breaks on — no `D|<prose>` leak to the user, no silent role clamp.
  - [x] **TD-21.5 — `src/api/routes/chat_delegation_decision.py:423` MCQ letter re-prompt.** Shape: one of A-D.
    Today: `_extract_toon_decision` then `\b([A-D])\b`; on a miss it keeps the previous mis-routed decision.
    Action: native enum. Note this call ALREADY exists only to recover a parse failure from TD-21.4 — converting
    TD-21.4 may delete this site outright.
    ✅ 2026-09-24 — same commit. Not dead after TD-21.4: it is a business-rule re-prompt (MCQ misroute), not a
    parse recovery. Converted: cheap fish kept; on a miss one `{"letter": enum A-D}` repair turn; on a further
    miss the prior schema-valid decision is kept.
  - [x] **TD-21.6 — `src/proactive_delegation/review_service.py:916` `_parse_review_response`.** Shape:
    `{d,f,s,c}` / `{d,s,f,p}` / TaskIR steps. Today: fence slice then a raw `find("{")`/`rfind("}")` re-slice;
    `parse_failure_count` is incremented but a **default verdict still flows** (`request_changes` / `ok` /
    `approve`, rubric axes default `True`). Action: adopt TD-1. **The constraint already exists**:
    `review_grammar.py:59,:102` ship the json_schema payloads and `:185,:213` the GBNF, and `llm_call` is
    simply never passed either.
    ✅ 2026-09-24 — orch `2c72295d`: all four consumers send a closed schema on the first call and route a miss
    through `parse_with_repair`. Terminal failure is typed, never a default verdict: `review()` withholds
    `request_evidence` (was `request_changes`; the delegator's bounded iteration path is unchanged);
    `review_plan()`/`review_plan_rubric()` write `parse_failure` (the ledger's `PARSE_FAILURE_DECISIONS` now buckets
    it — was a fabricated `ok`/`approve`), rubric axes `None` not `True`; `generate_taskir()` returns an explicit
    `parse_failed=True` step instead of an empty plan. Every `review_decision` event gains `repaired`. No review
    era scope exists, so no era row; old rows not backfilled.
  - [x] **TD-21.7 — `src/proactive_delegation/review_service.py:1030` → `review_grammar.py:298` ReviewDecision.**
    Shape: the full `orchestration/review_decision.schema.json` object. Today: balanced-brace fish + Draft202012
    + typed `ParseFailure`, withholding as `REQUEST_EVIDENCE` (admissibility-safe). Action: pass the schema that
    `review_grammar` already generates, then keep the withhold path as the residual. Measured warrant: 4.1%
    parse failure over 1,366 events (2026-08-13).
    ✅ 2026-09-24 — same commit: `review_candidate()` sends `review_decision_response_schema()` (X4); the existing
    fish + Draft 2020-12 validation + typed `ParseFailure` stays first, one repair turn before the
    `REQUEST_EVIDENCE` withhold, which is now the residual.
    **Decision (operator ask: wire or archive):** `rubric_review.py` (RD-2 engine, no runtime caller since
    2026-07-17) and the rubric half of `review_grammar.py` were **archived by deletion** (repo precedent
    `87c5f970`; git history is the archive). `review_plan_rubric` is the production rubric path; the persisted
    `GradeResult` shape survives in `review_ledger.py`'s duck-typed adapter and `review_rubric.schema.json`.
  - [x] **TD-21.8 — `scripts/review/review_replay_50.py:110` seam swallows the constraint.**
    `LiveServerPrimitives.llm_call(..., **_: Any)` discards `json_schema`/`grammar`/`seed`, so TD-21.6/21.7 are
    unobservable through this harness. Action: forward the kwargs. Zero inference; blocks the reviewer replay
    evidence for the two rows above.
    ✅ 2026-09-24 — same commit: `LiveServerPrimitives.llm_call` forwards `json_schema` (as `response_format`),
    `grammar` and `seed`, so reviewer replay exercises the constraint.
  - [x] **TD-21.9 — `scripts/benchmark/debug_scorer.py:1111` LLM-judge boolean.** Shape: `true|false`.
    Today: `verdict.lower().startswith("true")`, and `output_schema` is forwarded only on the `/chat` branch
    (`:1169`). Action: enum-bound `true|false` — removes the prefix-match artifact at the source. Judge role is
    `LLM_JUDGE_ROLE` else `architect_general` :8083.
    ✅ 2026-09-24 — orch `62ab94ed`, behind `CONSTRAIN_JUDGE_OUTPUT` (default OFF, flip in OP-50): strict
    `true`/`false` replaces the prefix match; an unparseable judge reply raises `ScoringUnavailableError` (a
    SCORER-side failure → `scoring_failed`, excluded under E17 — distinct from the model-side `AnswerParseError`).
    Always-on `judge_parse_stats` report the strict outcome even while OFF, surfaced per arm in `_aggregate`.
  - [x] **TD-21.10 — `scripts/benchmark/debug_scorer.py:1211` raw llama-server judge branch.** Shape: the same
    verdict. Today: strict dict access with no schema sent on this branch. Action: send the schema here too.
    ✅ 2026-09-24 — same commit: flag ON sends the schema as `response_format` on the raw `/v1` branch (none
    before); OFF proven byte-identical on the wire.
  - [x] **TD-21.11 — `scripts/benchmark/debug_scorer.py:359` multiple-choice letter** (used `:234,:286,:294`).
    Shape: one option letter. Today: five regex strategies, the last returning the final standalone letter
    unconditionally; an unparseable model answer returns `False` = **scored wrong**, with no counter. Action:
    native enum, and record a `parse_fail` category instead of `False` — the exclusion path already exists
    (`seeding_scoring.py:83-113`) and is simply never reached for model-side failures.
    ✅ 2026-09-24 — orch `af8a4a1b`/`940e0553`/`ec412724`: a no-letter answer is a counted model-side parse failure; with
    `EXCLUDE_UNPARSEABLE_ANSWERS` (default OFF) it raises `AnswerParseError` (a `ScoringUnavailableError`) and
    leaves the denominator via `seeding_scoring.score_answer_or_error`. Default scores byte-identical.
  - [x] **TD-21.12 — `scripts/benchmark/debug_scorer.py:1400`/`:1649` list-answer F1.** Shape: a list of items.
    Today: bullets → numbered → **comma-split** → one-per-line; a mis-parse silently lowers F1. Action: ask for
    a JSON array under a schema. This is the `feedback_substring_scorer_comma_brittle` class.
    ✅ 2026-09-24 — same commits: only a sub-threshold F1 produced by the raw one-per-line fallback is a parse
    failure; a cleanly extracted but wrong list stays wrong.
  - [x] **TD-21.13 — `scripts/benchmark/debug_scorer.py:1433,:1743,:1758` structural exact-match.** Shape: a
    JSON/Python value after the last `solution =` marker. Today: marker fish + `json.loads`/`literal_eval` with a
    never-raising fallback; a missing marker returns `False` = scored wrong. Action: a schema makes the marker
    unnecessary.
    ✅ 2026-09-24 — same commits: a missing `solution =` marker is a flag-gated parse failure.
  - [x] **TD-21.14 — `scripts/benchmark/debug_scorer.py:1477,:1495,:1595` answer / `\boxed{}` / is-this-JSON.**
    Today: regex chain; `:1607-1611` is the classic `find("{")`/`rfind("}")` slice. Action: adopt TD-1 for the
    JSON and final-answer cases. Fence extraction (`:1550`) may stay wherever an execution oracle runs.
    **Acceptance for TD-21.9..21.14 jointly**: report the per-arm parse-failure rate beside every accuracy ✅ 2026-09-24 for 21.11–21.14 (orch `940e0553`): `EvalTower._aggregate` reports
    `parse_failure_count` / `parse_failure_by_method` / `parse_failure_rate` in `details` beside quality and accuracy
    on every trial, counted per `eval_batch_id` so concurrent arms never mix; always on, independent of the flag.
  - [x] **TD-21.EQ1 — operator: ratify the exclusion (OP-50).** `bash scripts/operator/ratify_eq1_answer_parse_exclusion_20260924.sh --show`
    then `--apply`: flips `EXCLUDE_UNPARSEABLE_ANSWERS`, appends era `E19-eval-answer-parse-failure-excluded-quality`
    (`eval_quality`), moves the one default-contract test with the flip, runs the scorer suite, prints the commit.
    Tension, stated in the era note: E17 pulled failures INTO the denominator; this pulls unparseable answers OUT —
    guarded by the always-on parse-failure rate beside every accuracy.
    before and after, per the 2026-07-20 standing rule; the warrant is the verbose arm's 15% false
    parse-failures vs 0% and the gpqa 43.4% -> 53.0% re-score.
    ✅ 2026-09-24 — same commits: only "fell back to the raw last line AND nothing matched" is a parse failure;
    IFEval `json_valid` stays byte-identical (a real oracle — a first draft's `fish_json` swap would have passed
    invalid JSON, reverted in review).
    ✅ 2026-09-24 — **applied by the operator** (`ratify_eq1_answer_parse_exclusion_20260924.sh --apply`,
    post-flip suite 271 passed): committed from a clean worktree as orch `eabc9b44`, era
    `E19-eval-answer-parse-failure-excluded-quality`, boundary `2026-09-24T11:59:11Z`.
    `EXCLUDE_UNPARSEABLE_ANSWERS` and `CONSTRAIN_JUDGE_OUTPUT` now both `True`.
    **Defect found and fixed 2026-09-24 (orch `15e1b35a`):** the live E19 exclusion scored WRONG answers without a
    structured marker ("Final answer: 999" vs 25) as unparseable and EXCLUDED them (TD-21.14; TD-21.12 mirror bug),
    inflating accuracy. The golden pin (`test_b7_golden_corpus_pin.py`) missed it at ratification because two
    fixtures leaked the flag value across test files. Suspended 15:2xZ (`fcbb705f`, operator), fixed (only empty
    extractions are parse failures; fixtures restore the prior value; a guard asserts the pin sees the real flag),
    re-enabled with the fix. Rows 11:59Z–~15:26Z with `answer_parse_failed[exact_match|f1_list]` may be excluded
    wrong answers; no backfill. **Investigated 2026-09-24: 0 affected rows, no correction needed.**
    - [x] **Investigate and resolve the E19-affected rows** (scored 11:59Z–~15:26Z with
      `answer_parse_failed[exact_match|f1_list]` under the defective exclusion). ✅ 2026-09-24 — resolved,
      **zero rows affected**: nothing that uses `debug_scorer`/seeding_scoring persisted a row in
      [11:59:11Z, 15:40Z]; AutoPilot was not running in that window (journals last written 2026-06-27 and
      2026-08-09); the ratify/unit-test runs in the window were ephemeral pytest; TD-1d.2's bench measures
      agreement and imports no scorer; the one gold-scored run in the window
      (research `np_context_kvu_study`, 15:44-15:46Z) uses the independent research `answer_scoring.py`, which
      carries no E19 flag; the AutoKernel loop is speed-only. `grep -rl answer_parse_failed` over
      orchestrator `data/`+`orchestration/`+`logs/`, research `data/benchmarks` and root `data/`+`tmp/` returns
      0 files. No backfill needed.
  - [x] **TD-21.15 — `scripts/autopilot/eval_tower.py:3887,:3911` rubric-judge scores** (call `:4464`). Shape:
    `{"scores":{dim: float in [0,1]}}`. Today: fence strip + brace slice with range validation; if EVERY judge
    is unparseable the question silently falls back to `deterministic_rubric_fallback` stamped
    `rubric_source="heuristic_fallback"` **and written into the eval results**. Action: adopt TD-1 — the judge
    role is pinned and on the same server, making this the cheapest high-value conversion in the autopilot.
    ✅ 2026-09-24 — same commit: flag ON sends `RUBRIC_JUDGE_SCHEMA` and spends one repair turn against the same
    judge role on a lenient-fish miss. The `heuristic_fallback` stays as is: already marked by `rubric_source` and
    counted per arm (SCORE-08 `rubric_source_counts`) — changing fallback policy is not a parse fix.
  - [x] **TD-21.16 — `scripts/autopilot/planner_coordinator.py:971` critic verdict** (`_extract_json_payload:1447`).
    Shape: `{decision, confidence, issues[], revised_action, revised_rationale}`. Today: marker fish; a
    `parse_error` routes to a **fallback critic provider**, i.e. one extra full critic call per iteration.
    Action: adopt TD-1 before the fallback provider.
    ✅ 2026-09-24 — orch `325cfb36`: `extract_critique_with_repair` — fish (unchanged `extract_critique`) → full
    `autopilot_critique_schema()` → one repair turn via `action_repair_completer()` with `require_evidence` (so a
    repair cannot invent an approve/revise/reject the critic never stated) → typed failure. A recovered verdict no
    longer trips `_mark_failure` or spends the fallback-critic call (the fallback critic got the same treatment);
    `critic_parse_status`/`critic_repair_calls` persisted; old rows read as `""`, not `parsed`.
  - [x] **TD-21.17 — `scripts/autopilot/planner_coordinator.py:342,:379` draft-action usability gate.** Today:
    delegates to the TD-21.2 fish; `_mark_failure` opens a per-provider circuit breaker and re-invokes a fallback
    from zero. Action: inherits TD-21.2's repair; verify the circuit breaker no longer trips on parse alone.
    ✅ 2026-09-24 — same commits: a recovered parse fills `action`, so `_draft_unusable_reason` is empty → no
    `_mark_failure`, no circuit-breaker trip, no fallback re-prompt (test pins it); unrepairable behaves as before.
  - [x] **TD-21.18 — `scripts/autopilot/review_policy_trials.py:251,:263` critique extraction.** Today: the
    `review_grammar` validator runs first (good), but extraction falls back to a local balanced-brace scanner.
    Action: adopt TD-1 on the extract side; `CritiqueEmissionStats.parse_failures` already gives the before/after
    metric.
    ✅ 2026-09-24 — orch `b7416130`: the only caller feeds `codex exec` text (external CLI), so no repair turn;
    the local first-brace scanner is replaced by the shared `fish_json`, which recovers a critique truncated
    inside its own fence; a genuine miss stays a typed `ParseFailure` counted in `CritiqueEmissionStats`.
  - [x] **TD-21.19 — `src/vision/analyzers/vl_describe.py:409` structured image extraction.** Shape: free-form
    JSON from an image. Today: fence split + `json.loads`; on failure `structured=None` with `parse_error` but
    `result.success` stays **True** — a fail-open silent default that downstream cannot distinguish from "nothing
    in the image". Action: adopt TD-1 against `worker_vision` :8086 (its payload at `:165-181` sets no schema, and
    that port is on the `/completion` lane, so no TD-21.0 dependency).
    ✅ 2026-09-24 — orch `d8a88f73`: `VLStructuredAnalyzer` sends an open object schema (fields are genuinely
    caller-open) and repairs on a fish miss against its own VL server; terminal failure now sets
    `success=False` + `error` (the signal `vision/pipeline.py` already routes on) instead of fail-open `True`.
    Describe/OCR payloads byte-identical.
  - [x] **TD-21.20 — `src/api/routes/chat_pipeline/proactive_stage.py:57` plan-step decomposition.** Shape:
    `[{id, action, actor, depends_on, outputs}]`. Today: fence strip + trailing-comma regex; on failure returns
    `[]` and falls through to the standard pipeline with no counter and no telemetry — the whole architect call
    is discarded invisibly. Action: adopt TD-1, and count the failure.
    ✅ 2026-09-24 — same commit: `_decompose_plan_steps` — fish unchanged (0 calls on the happy path), then one
    repair turn on the architect role with `actor` ∈ {worker, coder, architect} (from the architect's own prompt
    contract); a terminal failure is logged and counted, the `< 2 steps` fall-through rule is unchanged.
  - [x] **TD-21.21 — `src/edit_transaction.py:333,:401` whole-file rewrite protocol** (parser `:85`). Shape:
    `<<<FILE: path>>>…<<<END>>>` / `<<<DELETE: path>>>`. Today: two regex families, fail-closed (nothing written),
    but the prompt carries the full scoped file corpus, so a dropped `<<<END>>>` throws away a max-context
    generation. Action: a GBNF for the delimiter protocol, or a TD-1 repair turn that re-expresses the reply into
    the block form. Also fixes the J17/BEP arms (`internal_interaction_j17_live_ab.py:340`,
    `bep_edit_mode_wiring.py:118`) which share the parser — and whose in-code claim that "/chat does not expose
    constrained decoding" is only true for `/v1`-lane roles (TD-21.0).
    ✅ 2026-09-24 — orch `e784f281` + `8d1790ca`. GBNF rejected with evidence: llama.cpp grammars have no
    "any text until literal" primitive (token negation needs a one-token marker; `<<<END>>>` is not), and real
    files — this one included — contain `<<<END>>>`/`<<<`, so a grammar would mangle exactly the files that need the
    protocol. Instead the backend's own finish reason decides a trailing open FILE block: natural stop → closed and
    written (content never invented; `.py` still compile-checked); length cutoff → dropped as before, now counted;
    unknown → fail-closed as before. Finish reason read per call via a new `ContextVar`
    (`get_last_inference_meta()`) — the first draft read the shared instance attribute, which a concurrent request
    can overwrite (reproduced: a truncated `.txt` was written); caught in review. Outcomes counted.
  - [x] **TD-21.22 — `src/repl_environment/routing.py:605,:620` and `combined_ops.py:397,:412` schema delegation.**
    Shape: "return only a JSON value matching this JSON Schema" — the schema is already in hand. Today: strict
    parse + jsonschema + up to 2 **full re-calls** (multiplied across a batch in `combined_ops`). Action: pass it
    as `json_schema=` and adopt TD-1 for the residual; the retry loop should become dead code.
    ✅ 2026-09-24 (partial, orch `d7202dc9`) — `routing.py` `_delegate_single`: schema now on the wire +
    repair before the full re-call (re-call kept as the fallback). `combined_ops.py` `_batch_llm_query`: repair
    before re-call only — see TD-21.22a.
  - [x] **TD-21.22a — `llm_batch` has no `json_schema` parameter.** Wire-schema forwarding for the batch path needs
    the parameter threaded through `_real_batch`/`_mock_batch`/`_worker_pool_batch` and every `llm_batch` caller in
    `src/llm_primitives/`; until then the batch schema is prompt text plus the repair turn.
    ✅ 2026-09-24 — orch `b8778dad`: `llm_batch`/`llm_batch_async` take `json_schema`/`grammar` (per batch),
    threaded through `_real_batch`, `_worker_pool_batch` (→ worker-pool `/completion` payload),
    `_fallback_batch` and `_mock_batch` with conditional kwargs (omitted ⇒ byte-identical, proven against
    fixed-arity fakes); `combined_ops._batch_llm_query` now sends the schema on the wire. Side finding: two
    callers pass `n_tokens` to `llm_batch`, which never accepted it → real-mode TypeError silently degrading
    to sequential calls — see TD-21.22b.
  - [x] **TD-21.22b — `llm_batch(..., n_tokens=)` raises at `chat_summarization.py:233` and
    `repl_environment/context.py:141`**, caught and silently degraded to sequential calls. 
    ✅ 2026-09-24 — orch `318c4d27`: `llm_batch`/`llm_batch_async` take `n_tokens` through every batch path
    (worker pool as its own `max_tokens`); both call sites now run as real batches; the silent except in
    `repl_environment/context.py` now logs a warning.
  - [x] **TD-21.23 — `src/pipeline_monitor/model_grader.py:173` grader classification.** Shape: one letter from
    `spec.choice_strings`, expected on the last line. Today: a last-line word-boundary regex; a mis-formatted reply
    silently becomes an ungraded row. Action: native enum — the path already runs `/chat` `force_mode=direct`,
    which supports `output_schema`.
    ✅ 2026-09-24 — same commit: `grade_answer` sends `output_schema` = enum over `spec.choice_strings`; native
    parse first, the last-line regex as backstop; unparseable → `classification="parse_error"` (score `None`, as
    before) counted in `GRADER_CLASSIFICATION_OUTCOME_COUNTS` instead of a silent `None`.
  - [x] **TD-21.24 — `scripts/analysis/reviewer_policy_arm_ab.py:337` A/B reviewer verdict.** Today:
    `find("{")`/`rfind("}")` then a bare first token; unparseable falls to `DEFAULT_DECISION` **silently** and that
    default is written into the A/B result. Action: adopt TD-1 — a silent default biases the measurement the
    script exists to produce.
    ✅ 2026-09-24 — orch `b7416130`: `extract_decision` is fish-only and returns `None` on a miss (never the old
    `request_changes` default); `resolve_reviewer_decision` spends one repair turn against the reviewer role's
    own llama-server (via `get_config().server_urls`, never :8000) with a closed decision enum, then a typed
    `parse_failure`. `compute_policy_comparison` excludes parse failures from paired agreement/kappa and
    reports the per-arm parse-failure rate beside the verdict distributions.
  - [x] **TD-21.25 — `scripts/autopilot/species/evolution_manager.py:326,:343,:363` insight distillation.**
    Shape: a JSON list of insights, plus evidence trial ids. Today: marker fish returning `[]` on failure (a
    silent zero-insight round, indistinguishable from "nothing to learn"), and `_coerce_trial_ids` silently drops
    unparseable tokens so an insight is stored with weaker grounding. Action: adopt TD-1 against the local
    `explore` endpoint; count dropped ids.
    ✅ 2026-09-24 — orch `4f171de8`: fish → schema → one repair turn only when `use_local_model=True` (the
    Claude-CLI default is unreachable → typed failure); `distill()` reports `insight_parse_status`, repair calls
    and `evidence_ids_dropped` (was a silent `[]`); `TRIAL_ID_COERCION_COUNTS`.
  - [x] **TD-21.26 — `scripts/autopilot/species/env_synth/task_synthesizer.py:207` and `etd_agent.py:86`.**
    Shapes: a synthesized task object; a list of candidate environments. Today: strict `json.loads` with no fence
    tolerance — the synthesizer **retries the whole generation `max_retries+1` times from zero**, the ETD agent
    returns `[]` with no counter. Action: adopt TD-1; this is the exact retry-from-zero cost DS41 measured.
    ✅ 2026-09-24 — same commit: new `parse_with_repair_async` in the shared helper; both sites fish (fence
    tolerant) then one repair turn against the same injected `llm` before a from-zero regeneration / typed `[]`.
  - [x] **TD-21.27 — `scripts/autopilot/species/prompt_forge.py:2696,:3450` mutation extraction.** Shapes: a
    mutated prompt-file body; mutated Python source. Today: fence heuristics (">100 chars", "largest non-json
    block"); on failure it logs and **returns the original**, so the mutation is a silent no-op while a git commit
    may still be cut around it. Action: a delimiter contract plus a repair turn; the backend is the Claude CLI, so
    the repair must go to a local server or the contract must be made unambiguous.
    ✅ 2026-09-24 — same commit: Claude CLI → fish only; both extractors share one line-anchored fenced-block
    helper; an extraction miss now sets `safety_valid=False` (`mutation_extraction_failed`) instead of silently
    returning the original (an invisible no-op mutation that still burned an eval cycle); counted.
  - [x] **TD-21.28 — `scripts/benchmark/corpus_quality_gate.py:670` judged-pair fields.** Shape: 8 numeric A/B
    quality fields. Today: fence regex + `json.loads`; on failure the pair is **silently dropped** from the judged
    set with no counter, so the gate's denominator moves without anyone seeing it. Action: count the drops at
    minimum; adopt TD-1 if the judge moves onto a local server (it is `claude -p` today).
    ✅ 2026-09-24 — same commit: Claude CLI → fish only; `fish_json` + full validation of the 8 numeric fields;
    `_judge.json` now records `pairs_total`/`pairs_judged`/`judge_parse_failures` per model, and a model with
    zero judged pairs gets an explicit failing row instead of silent omission (the gate can no longer pass a
    model that was never judged).
  - [x] **TD-21.29 — `epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_preparation.py:333,:369`.**
    Shapes: source-actor advice `{mechanism, target_surface, target_symbol, implementation_plan}` (or a build
    recipe); critic verdict `{accepted, reason}`. Today: calls `actors._extract_json` **raw**, with no repair —
    the same path `ad2b89ff` just converted one file away. A `PreparationRefused` burns a **one-shot reservation**
    that cannot be re-invoked. Action: route both through `actors._parse_reply` with the matching schema
    (`:369` is literally `REVIEW_SCHEMA`); reachable whenever the `ActorProfile` names an opencode `provider/model`.
    ✅ 2026-09-24 — research `4915220f` (repair coverage for `actor_preparation.py` + `actors.py` residuals),
    coordinated directly with the DS41 session (workspace-76) on their seat branch `e9495971`, merged after
    their `21ca61b0`, landed on research main. `actor_preparation` through `_parse_reply` — no burned reservation
    on a malformed reply.
  - [x] **TD-21.30 — Close the `actors.py` residuals left by `ad2b89ff`.** (a) `:181` `_first_json_or_none` is
    still a raw probe and silently decides what `_parse_reply` later sees; (b) `:344` accepts any object where
    `"abstain" in body or _complete(body, schema)`, so a partial or hallucinated object carrying the required keys
    short-circuits repair entirely; (c) `_schema_repair` returns `None` for non-opencode backends, so the two
    DEFAULT roles (planner = codex `gpt-5.6-sol`, critic = Claude Fable 5.1) have **zero repair coverage today** —
    the idiom is live only on an explicit `provider/model` opt-in, and the DS41 retry-from-zero cost is unchanged
    for them; (d) `REVIEW_SCHEMA` leaves `additionalProperties` unset, so a repair turn may legally return extra
    keys; (e) the repair body carries no `model` field, so a multi-model local endpoint would 400 and degrade
    silently to `None`. — (c) is closed for free for the `orchestrator` Backend kind proposed in INF-78
    ([`autokernel-orchestrator-actor-backend.md`](autokernel-orchestrator-actor-backend.md)): its reply comes back
    through `/chat` with `output_schema` and TD-21.1's `repl_final` repair, so no loop-side repair is needed for
    that kind; codex/claude kinds remain uncovered.
    ✅ 2026-09-24 — research `4915220f` (same commit as TD-21.29): schema-aware stream choice; full type
    validation before skipping repair; `REVIEW_SCHEMA` closed (additionalProperties); `model` added on the
    repair wire. Same DS41-coordinated landing on research main; `loop/` suite 87 failures identical to clean
    `21ca61b0` (pre-existing, unrelated to this change). Shared research clone deliberately NOT fast-forwarded
    to this SHA (their run 8 in flight); the DS41 session holds the SHA.
  - [x] **TD-21.31 — Record the unreachable consumers rather than converting them.** `claude_codex_actor_critic.py:354,:373`
    and `claude_fable5_critic_actor.py:574` are already natively constrained (`--json-schema`, enum + `const`
    bindings) and need nothing. `discovery_controller.py:1416,:1434`, `loop_experiment_runner.py:517` (codex arm,
    which has **no schema enforcement at all**, only post-hoc validation), `evoengineer_arena.py:306` and the four
    vendored arena arms run behind external CLIs with no local server, so the repair idiom cannot reach them.
    Flag one defect anyway: `evoengineer_arena.py:306`'s last fallback **silently returns the whole raw reply as a
    candidate** (`{"name":"raw","thought":"Failed to parse"}`) which then goes on to compile and evaluate — make it
    a typed failure. And `k_search_arena.py:170`'s OpenAI shim **drops any `response_format` the vendor supplies**.
    `arena_upstream_common.py:357` is the single chokepoint if these ever move onto the local server.
    - [x] **TD-21.31 (a) — evoengineer typed failure + codex `response_format`** ✅ 2026-09-24 — research
      `9f55e94c` + `432e409e` (self-pinning re-pin of `arena_campaign_v1.json`): the raw-reply fallback now raises
      `EvoEngineerArenaError`; the vendored loop turns that into `Solution("")`, registered invalid and never
      compiled or evaluated. `arena_upstream_common.CodexTextModel` forwards a `json_schema` `response_format` as
      `codex --output-schema` (latent: the pinned k-search vendor never sends one today). Not on the live DS41
      import path (verified). Unreachable-consumer verdicts confirmed per site: claude_codex_actor_critic and
      claude_fable5_critic_actor natively constrained; discovery_controller, loop_experiment_runner (codex arm,
      post-hoc validation only), evoengineer and the four vendored arms are CLI-only — recorded, not converted.
  - [x] **TD-21.32 — Decide the judge binding before converting judge sites.** There is no declared `judge` role
    in the registry; the eval judge is still a prompt/model choice inside the harness, and CJ-11
    (`canonical-judge-suite-revamp.md`) calls for binding it at `src/llm.py:61-64`. TD-21.9/21.10/21.15 should land
    after or alongside that binding, or they convert against a moving target. Coordinate, do not duplicate.
  - [x] **TD-21.34 — evidence guard on the already-landed repair sites.** `require_evidence` arrived after
    TD-21.1/4/6/19/20/24/25/26 landed; review each site (ON where numbers/short strings must come from the reply,
    OFF where short strings are enum classifications of prose) and add `require_evidence` to
    `parse_with_repair_async`. In flight 2026-09-24.
    ✅ 2026-09-24 — orch `2ffc3f51`: helper gained `evidence_exempt` (keys/paths whose subtree is a classification)
    and `require_evidence` on `parse_with_repair_async`. Per site: ON for FINAL/delegate/batch answers, VL
    extraction, plan steps (`actor` exempt), review verdict content (`d`/`op`/`decision` exempt), rubric/candidate
    `confidence`, insight trial ids, env_synth (`verifier.type` exempt), architect decision (`mode`/`delegate_to`/
    `delegate_mode` exempt), MCQ letter; OFF only for the single-enum A/B verdict. Fixtures that "repaired" to values
    absent from their own raw text were the pattern the guard catches — they were made evidence-compliant.
  - [x] **TD-21.35 — the repair grammar no longer forces required fields.** Operator question (2026-09-24): can
    the harness limit which schema entries a repair turn is allowed to touch? Answer: the repair wire schema
    drops `required` except for const/single-enum discriminators, and the repaired object is still validated
    against the ORIGINAL schema (not the relaxed one).
    ✅ 2026-09-24 — orch `f09efc64`; the actors.py repair wire got the same treatment in research `34373dd8`
    (same DS41-coordinated landing as TD-21.29/21.30). **Live finding (smoke 13:43Z):** relaxing `required`
    alone did NOT stop invention — without `require_evidence` (TD-21.34) the model still filled an optional
    tier field (repaired `tier: 2` for a draft naming none). The relaxation removes the *forcing*; the evidence
    check is what actually prevents invention. Answers the operator's two questions this session: why the
    eval-quality changes were switched off earlier (era discipline — a scoring change is an era boundary,
    human-only registry) and whether the harness can constrain repair scope (yes, via `required`-dropping plus
    the pre-existing evidence guard, which is load-bearing here).
  - [x] **TD-21.33 — carry the actors.py grounding + min-report refusal into the shared helper.**
    `src/structured_output/repair.py` `parse_with_repair` (`:373`) fishes, validates, declines, extracts — but will
    happily "repair" an EMPTY or near-empty report into a schema-valid object, and never checks that a repaired
    file/symbol field names something the report itself names. DS41 run 7 (2026-09-24) hit exactly this: an empty
    retry reply was repaired into `replay-verification / src/verify/replay.ts` and a critic pass was spent rejecting
    it. The research reference now does both (research worktree `lane/ak-actor-seat-20260924`, DS41-C20):
    `actors.py` `REPAIR_MIN_REPORT_CHARS = 20` (no JSON and below it → no repair turn, typed transient) and
    `_grounded` / `_ungrounded_fields` (a required path/symbol field must appear in the report text — any path it
    carries or that path's basename, else its longest identifier — or the repair is refused; prose fields may
    paraphrase). Add to `parse_with_repair`: `min_report_chars` (default 20) and an optional
    `grounded_fields: Sequence[str]`; a failed grounding returns `RepairResult(status="failed",
    reason="ungrounded:<field>")` and bumps `STRUCTURED_OUTPUT_REPAIR_COUNTS`. Tests: empty report → `failed`, never
    an object; a repaired `target_symbol` absent from the report → `failed`. Consumers to opt in first: `repl_final`
    (TD-21.1) and the autokernel orchestrator backend (INF-78), which must get its repair coverage HERE rather than
    in `actors._schema_repair` (returns `None` for any non-opencode backend — TD-21.30 (c)). Zero inference.
    ✅ 2026-09-24 — **decided (main session):** judge BINDING (which model; CJ-11 is about the vendored BEAM
    harness's `src/llm.py`) and judge OUTPUT SHAPE (21.9/21.10/21.15) are orthogonal. The shape conversions go
    ahead now, resolving the judge only through its existing seam (`LLM_JUDGE_ROLE` / the pinned rubric-judge
    role) so a later rebinding changes nothing in them. Because constraining a judge changes eval scores, they
    ship behind a default-OFF `CONSTRAIN_JUDGE_OUTPUT`, and its flip is folded into the OP-50 ratification (one
    command, one era row) rather than a second boundary.
    ✅ 2026-09-24 — orch `d12202f2`: same-context readers migrated to `get_last_inference_meta()`
    (`chat_delegation.py`, `chat_completion_call`, `chat_pipeline/telemetry.py` — which runs under `to_thread`
    exactly like the TD-21.21 bug — `typed_decisions/measure.py` (+ judge_redundancy, tool_args_pilot) and
    `bench.py`), each with an `isinstance` guard for test doubles; 2 interleaving race tests.
  - [x] **TD-21.33a — `graph/helpers.py::_execute_turn` still reads meta across a thread hop.** The call runs in
    `asyncio.to_thread` and the read happens in the parent, where a ContextVar set in the child is invisible; it got
    a getter-first/attribute-fallback hybrid (never worse than before) but the real fix is to return the meta from
    the thread alongside `code`, as the edit-transaction path now does.
    ✅ 2026-09-24 — orch `f769f3e1`: closed for real — meta is now captured inside the thread via
    `_call_llm_capturing_meta` and returned alongside `code`, instead of read after the hop.
  - [x] **TD-21.33b — `typed_decisions/native.py:517,:1272` read the shared attribute right after their own call.**
    Same-context, migratable; not touched because another session holds uncommitted work in that file (in the
    shared orchestrator clone since 2026-09-22). For that session, or once the file is free.
    ✅ 2026-09-24 — orch `d63a11ed`: native.py's last two `_last_inference_meta` readers migrated. Taken over at
    operator direction alongside the parked 2026-09-22 `native.py` work (TD-1d.4); the parked copy was captured
    byte-identical under `/mnt/raid0/llm/worktrees/td21/native-capture/` before this landed, and the shared
    orchestrator clone is clean for the first time today.
  - [x] **TD-21.33 — `primitives._last_inference_meta` is read across a SHARED `LLMPrimitives`.** ✅ 2026-09-24 —
    per-call ContextVar channel + reader migration (orch `d12202f2`), residuals TD-21.33a (`f769f3e1`) and
    TD-21.33b (`d63a11ed`), and **TD-21.33c** (`c347600e`, found at the late re-check): `_real_call` itself
    re-read the shared attribute for three follow-up writes (`tool_calls`, `max_tokens_clamped`,
    `completion_reason=context_limit`), which a concurrent `to_thread` call could misdirect. They now use a local
    handle. The regression test fails on the old code; 253 related tests pass. Live after the next API reload.
    `_init_primitives` reuses one instance per worker across concurrent requests, so any code that reads the
    last call's meta after the fact can see another request's values: `graph/helpers.py:~941`,
    `chat_delegation.py:~470` today (and TD-21.21's first draft, caught in review). Give callers a per-call meta
    channel and migrate those reads. Found 2026-09-24.

## Immediate ROI path — 2026-09-25

- [x] **TD-22 — Refresh the public Jev contract and evidence boundary.** ✅ 2026-09-25 — Current official material was consolidated into intake-1470#record and intake-1472#record: moving aliases require resolved-model capture; current limits are dynamic; same-request questions inspect one shared state independently; dependent decisions require another call or host composition; host code owns permission, freshness, candidate existence, and outcome verification; current latency language is vendor guidance rather than an SLA; the hierarchy result is a four-case smoke; and the independent day-run cost report supplies no labels or public replay.
- [ ] **TD-23 — Shared typed-decision screen.** After the CJ-15 fixture and HS-TD-4 receipt exist, compare hosted Jev when its exact model identity is available, one available local compact decision backend, and the constrained incumbent readout on one sealed, row-pinned workload. Freeze the manifest, backend/model revisions, requested/resolved identities, candidate descriptions, prompts, threshold-selection split, and held-out source groups; retain per-row probabilities and raw outputs, invalids, failures, abstentions, timing, and cost in `decision_receipt.v1`. Cross position, order, opaque keys, semantic rebinding, response format, repeated calls, irrelevant siblings, explicit unknown, and long-context placement; report accuracy, consistent accuracy, ECE/Brier, flip rates, probability divergence, clustered intervals, and total decision cost. Predeclare quality, calibration, and operations stop/promotion thresholds; keep same-state independent questions, staged dependent decisions, and hierarchy search as separate protocol classes. This is the common cheap screen under the [minimum viable research execution contract](eval-tower-verification.md#minimum-viable-research-execution-contract), not a paper-wide reproduction. Sources: intake-1577#record, intake-1583#record, intake-1606#record, intake-1618#record, intake-1619#record, intake-1623#record, intake-1634#record, intake-1637#record, intake-1654#record, intake-1660#record, intake-1676#record, intake-1681#record.

### Trigger records — materialize only when the named condition fires

- **TD-24 — GLiNER2.5-Decide follow-on.** Activate only if the GLiNER backend in TD-23 clears the held-out quality, calibration, and operations gate or EPYC needs a claim-bearing public reproduction. Then pin model, library, and Fast Decisions revisions; pass `multi_label`; emit all 2,900 public rows and per-head outputs; report macro-domain and pooled-head exact match separately; and test constraint invariance, brute-force optimality on small schemas, candidate retention, infeasibility behavior, and `Classifier` versus `classify_text`. Do not claim the unavailable held-out result. Sources: intake-1586#record, intake-1587#record, intake-1588#record.
- **TD-25 — CLM specialized-head follow-on.** Activate only if the released default head in TD-23 clears the held-out quality, calibration, and operations gate. Pin exact base/head hashes and candidate-description policy; a task-specific projection head may enter shadow only after a group-disjoint comparison beats the incumbent on quality and calibration. Default-head JevBench results cannot substitute for that gate, and full three-stage training remains dormant until this candidate gate passes. Sources: intake-1581#record, intake-1589#record, intake-1590#record, intake-1591#record.
- **TD-26 — Phishing transfer.** Activate when phishing classification becomes an EPYC product or benchmark workload. Freeze the PhishNChips CSV, revision, licenses, prompts, and raw calls; report its synthetic arm separately from a pinned real-email split, with proper scores, order/key controls, model resolution, per-row outputs, and uncertainty. Sources: intake-1659#record, intake-1678#record.
- **TD-27 — BTZSC replay.** Activate when BTZSC-style classification becomes an active benchmark or claim surface. Replay historical commit `8a0d52cbe423` and current v0.1.2 separately, freezing rows, models, verbalizers, prompts, permutations, hardware, precision, failures, and raw timings. Alphabetical label sorting is one deterministic assignment, not robustness evidence. Sources: intake-1660#record, intake-1679#record, intake-1680#record, intake-1681#record.

## Wiring policy (2026-09-18, operator-directed)

- **Fan-out decision rule (TD-8, implemented in `src/typed_decisions/fanout_policy.py`):** exactness-required + native-eligible -> native id-only per question (11.98x n=1, contested: 9.60x at n=4 pending TD-1d.0; isolated); stability-tolerant batches of >= 8 -> batched (2.2x at 87.5% measured agreement); otherwise sequential JSON. The 87.5% figure governs the choice per surface.
- **Tool arguments (item 1):** closed-set wiring landed in the orchestrator tool path (`src/repl_environment/context.py` `_dispatch_tool`) behind `typed_decisions_tool_args` (default off), fail-open to model-provided args.
- **Deferred but tracked:** routing replay -> TD-7; judge redundancy -> CJ-13/CJ-14 in `canonical-judge-suite-revamp.md`; episodic pre-write gate -> M-19 in `episodic-memory-integrity.md`; harness items -> HS-TD-1..3 in `harness-selection-and-integration.md`.
- [x] **TD-8 — Fan-out policy helper.** Implemented + 18 tests (`fanout_policy.py`, provenance-stamped constants). ✅ 2026-09-18

## Open Questions

- Which confidence statistic, if any, survives local calibration well enough to gate an action?
- Does the frozen v9 server's json_schema→GBNF converter accept the nested probability-map schemas the adapter generates?
- Does question-order contamination on our stack reproduce the 24.7% seen in intake-1486, or is it smaller at our batch sizes?

## Notes

All numbers above are from dive-verified entries; none may be promoted to a deployment measurement until TD-2/TD-3
produce our own. This stub follows the 2026-09-17 operator steering; the vendor's own documentation states confidence
is an undisclosed statistic and calibration is group-level only.
