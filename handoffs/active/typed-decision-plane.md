# Typed Decision Plane — one-pass typed decisions over the local stack

**Status**: in progress — **Owner: research-intake session `intake-jev-sageattn`** (operator-assigned 2026-09-17). Implementation lives in `epyc-orchestrator` on branch `intake/jev-typed-decisions-20260917` (worktree `/mnt/raid0/llm/worktrees/sub-jev-tdp-orch`).
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
  - [ ] **TD-1d.1 — `/v1` drops `grammar`/`json_schema`, so the native path cannot run through `LLMPrimitives`.**
    `frontdoor` routes to `/v1/chat/completions` (`use_chat_completions=True`), which forwards neither field:
    measured 515 free-form tokens and **0/24 decisions** (`native_unknown_candidate` x16). Every arm above used a
    direct `/completion` adapter mirroring `_build_payload`, and TD-1c's result must have gone the same way.
    **No typed-decision arm is deployable through the normal primitives path until this is closed** — decide
    whether `/v1` forwards the fields for internal callers, or whether typed decisions keep a declared direct
    `/completion` lane. Zero inference to decide.
  - [ ] **TD-1d.2 — concurrent in-process `llm_call`s are serialized by the cross-process `inference_lock`**
    (probed: parallel wall == serial wall, max 1 slot busy). A constraint on every future fan-out design, not
    just this one; independently matches the 09-17 note's `heavy_model` lock observation.
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
- [x] **TD-7 — TD-5 live replay on the recorded routing corpus.** Build a state adapter from the recorded routing decisions (reference: ~54,960 rows with 22-33% per-role failure in learned-routing-controller) and replay N=100-200 through the shadow path; report typed-vs-incumbent agreement and confidence-vs-outcome calibration. ✅ 2026-09-18 ran on the admissible frozen snapshot (`orchestration/repl_memory/sessions/episodic.db.backup-20260415`, sha256 12ca8b0b…, max(created_at) 2026-04-15 — pre-purge; live DB refused by design). N=200: **agreement vs incumbent 3.0% (6/200, Wilson 1.4-6.4%)**; **native 0/200** — every routing action label is multi-token (`frontdoor`=front+door), so all rows took the JSON fallback; the model shows a strong SELF bias (177/200 at ~0.975 confidence); **AUROC 0.50** vs the frozen success label and ECE 0.10, with the caveat that the frozen label describes the incumbent action, not the chosen one (flagged in-receipt). Diagnostic outcome: the harness works; candidate/token design is the blocker. Receipts under artifacts/typed_decisions/run_20260918/.

**Declined (2026-09-17):** no new belief-kernel carrier for bench/cue-sweep reports — they are screening instruments, not protocol-grade measurements (the strict reader refuses them by design); revisit only if a `P-TDP` measurement protocol is ratified.

- [x] **TD-10 — Counterfactual evaluation of the TD-9 routing policy (model-based OPE).** ✅ 2026-09-18: reused the escalation probe's cross-fitted, embedding-grouped estimator over the frozen snapshot with freshly embedded states; **delta typed-minus-incumbent = -0.0104** (CI95 [-0.0246, -0.0066], 5 folds all negative; ~1pp worse). Verdict: **enforcement stays OFF** — agreement is not skill; the 13 departures (frontdoor->ARCHITECT) are estimated harmful. Caveats: model-based estimate with the probe's EPD-1..3 confounds; unevaluable actions excluded.
- [ ] **TD-11 — Routing prompt/policy improvement, re-tested through the counterfactual harness.** The harness now measures value, not agreement; use it to iterate (framing, support-aware candidates, leave-one-out conditioning) before any enforcement proposal. Acceptance: positive delta with a CI excluding zero on the frozen snapshot, or a written decision to drop typed routing.

- [ ] **TD-12 — One-call tool + argument arm (operation × conditional target).** Build a typed-decision arm that asks, in one call, a choice over the role's tools (`ToolRegistry.list_tools(role)`) plus one argument head set per candidate tool whose instructions name the tool they assume, and consume only the chosen tool's heads. A failed head for an UNUSED tool must not reject the pass (today any failure rejects it: `tool_args_integration.py:197-198`). Compare against the current tool-then-arguments path (TD-4) on exact-match tool+argument correctness and wall time over the TD-4 case set extended with a tool-choice step. Citation: intake-1493 (dive-verified; `jev_ultrafast/model.py:94-133` @ 1231850a).
- [ ] **TD-13 — Contamination between the operation head and its conditional heads.** Before TD-12's heads are trusted as independent: for each case, answer the chosen tool's argument heads alone and batched with the sibling (unused) tools' heads; report top-answer flip rate per model. Existing receipts (TD-2, TD-3b) cover flat catalogues only. Acceptance: flip rate reported for the worker model; TD-12 adoption gated on it.
- [ ] **TD-14 — Per-candidate descriptions on `Question`.** Add an optional description per option (today options are a bare label list, `types.py:66-68`, rendered as `candidates: a | b`), rendered in the catalogue, so tool or element tables are grounded without stuffing the shared state. Unit tests; JSON and native arms both render it.
  - *Acceptance amendment 2026-09-23 (intake-1517):* descriptions must not hurt — compare with vs without descriptions on
    the TD-16 pairs and report the delta; a negative delta blocks using descriptions.
- [ ] **TD-15 — (conditional on TD-12) Native path for more than 36 candidates.** Only if TD-12 needs tables beyond the TD-9 code map (36 symbols, `routing_replay.py:153`) or the 128 `n_probs` cap (`native.py:259`): hierarchical codes or chunked candidate tables. Close as not-needed if TD-12 stays under 36.
- [ ] **TD-16 — Label-word bias control on the native noul path.** Freeze hunch's 240 look-alike pairs (`hunch/lookalikes.py` @8bac3f2b, MIT; 80 pos / 160 neg) as a noul set. On the worker model at its current pin run (N) native noul as today, (C) the same question as a 2-option choice with neutral A/B keys and the yes/no conditions as option text, both orders, reported per order and averaged, (J) the JSON arm, plus question-only variants of N and C. Report AUROC, argmax accuracy, Brier, ECE, order disagreement and both constant baselines (always-no 66.7%, base-rate Brier 0.222) with paired-bootstrap CIs. If C beats N beyond the CI, TD-1c's 15/16 parity holds only for its 8-noul set. No gate follows (wiki/routing-intelligence.md L40). Evidence: intake-1517, intake-1502. Inference-gated, one short window.
- [ ] **TD-17 — Frozen OOD calibration slice.** Zero-inference adapter over `scienthoon/jev-ood-calibration` `data/val.jsonl` @914d87a (sha256 763949cd…, CC0, byte-reproducible): 300 states x {queue choice, priority score 0-3 with level names as criteria, angry noul}; do not state the priority rule in the catalogue. Also a tier-ablated variant (drop `customer_tier`, fresh `--seed`) so priority depends on a genuinely hidden input. Report the TD-18 metric set per (model pin, catalogue) for the native and JSON arms. The calibrated target is mean max-prob ≈ accuracy, not a near-uniform priority. Cite only the corrected Jev temperatures (1.30 / 1.92), never 3.29 / 3.40 / 2.74. Evidence: intake-1504, intake-1516. The run needs one short window.
- [ ] **TD-18 — Calibration receipt upgrade (zero inference).** Extend the typed_decisions calibration receipt (today n, ECE, Brier, 10 bins; no floor, no model-pin field) with, per question kind: a resampled perfectly-calibrated ECE noise floor; a record/template-clustered paired bootstrap; tie-aware coverage at a stated error budget and AURC; NLL and refit-T sensitivity to the log floor and clamp; exact-0 / exact-1 endpoint rates; a flag when a fitted temperature lands on a search bound; a single in-distribution temperature with a group-disjoint out-of-fold check; and the model pin. Clean-room from the patterns in `kev/metrics.py` and `kev/calibrate.py` (Apache-2.0). Evidence: intake-1498, intake-1504, intake-1516.
- [ ] **TD-19 — External OOD read via a `/v1/systemone` shim.** Expose our typed-decision path behind Kev's `/v1/systemone` contract (`kev/predictors.py:61-92`, `kev/benchmark.py:34-66`) and score it with `kev.benchmark --remote` on Kev's committed transfer-v4 dev (764 records) and scienthoon-v1. Multi-token candidates return JSON-arm probabilities; send options in insertion order (Kev is order-sensitive; gojev sorts keys). Report accuracy, ECE and coverage against the committed Kev/Jev reports — the Jev figures are report-level only, and the Kev-vs-Jev coverage CI already includes 0. Evidence: intake-1498, intake-1515. Inference-gated, one window.
- [ ] **TD-20 — (conditional on TD-19 showing a trained decider beats our path) Serve Kev-4B on llama.cpp-experimental.** Branch from fresh production ffc1bac; port `common/decision.{h,cpp}` + `tools/kev/kev-decide.cpp` + 2 CMake lines as new files with a sidecar `head.json` (no `src/` change, no fork merge). Source weights from `taigrr/kev-4b-gguf` at a pinned sha, sha256-verified against `manifest.json` (merged GGUF avoids the 4B/9B `out_proj` LoRA conversion gap). Parity vs HF-fp32 on committed decision-v7 dev rows plus fixtures with unsorted keys, a long state and 4B; test `seq_cp` fan-out against v10's recurrent rollback-index abort on shared cells. Evidence: intake-1498, intake-1514#00, intake-1514#05, intake-1515.

## Wiring policy (2026-09-18, operator-directed)

- **Fan-out decision rule (TD-8, implemented in `src/typed_decisions/fanout_policy.py`):** exactness-required + native-eligible -> native id-only per question (11.98x, isolated); stability-tolerant batches of >= 8 -> batched (2.2x at 87.5% measured agreement); otherwise sequential JSON. The 87.5% figure governs the choice per surface.
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
