# RE-4 / K-LCM-1 — LongCoT-Mini Protocol Redesign (design + harness SPEC)

**Status:** DESIGN (no inference, no execution). Deliverable of the RE-4 protocol-repair task.
**Owning entry:** `coordination/inference-batch/entries/20-eval-tower.yaml` → `RE-4-longcot-mini-calibration` (currently terminal `INFRA_BLOCKED` / quarantined `protocol_blocked/floor_saturated`).
**Owning handoff:** `handoffs/active/inference-batch-loop.md` (open task line: *"RE-4 protocol repair"*).
**Measurement grade:** OBSERVATION (non-saturated research benchmark; hypothesis-only, never a keep/revert/deploy/promote gate). Scoring stays deterministic — **NO LLM-judge** (MEASUREMENT.md).
**Runner code change required:** **YES** — the fix is *structural* (a second, forced-final-answer HTTP turn), so this doc SPECs it for a follow-on implementation pass rather than editing the runner in place.

---

## 1. Root cause — why the parked protocol floor-saturated

The benchmark requires **both** (a) genuine multi-step reasoning **and** (b) a terminal `solution = <value>` line the deterministic scorer can anchor on. The two generation modes shipped in `longcot_mini_stack_runner.py` each satisfy only *one* of those, so both score ~0%:

**Failure mode 1 — `concise_solution` + `--force-solution-grammar` (the aborted RE-4 run, `longcot_mini_re4_grammar_20260721T013833Z`).**
The grammar `root ::= "solution = " ([^\n])+ "\n"?` forces the output to be exactly one answer line, and the `concise_solution` system prompt tells the model *not* to show derivation. Result: **frontdoor 0/402, worker_general 0/307**, `canary_leak=0`, `missing_from_prompt_index=0`, all rows `reason=mismatch` (perfect marker compliance, every answer wrong). Completion lengths were **13–34 tokens** — the model emitted a blind guess with no reasoning. Concrete rows (frontdoor):

| qid | expected (gold) | forced response | ctoks |
|---|---|---|---:|
| longcot_mini_1 | `["2013^{4025}", 2692, 26]` | `solution = 1, 18, 27` | 13 |
| longcot_mini_100 | `["2^{2013}-6036", 144, 15, 36]` | `solution = [1024, 8, 2, 28]` | 19 |
| longcot_mini_101 | `"8/r7/kn3p2/1pr1pPpp/NP2PbPP/5K2/3B4/1bR1bB2 w - - 122 349"` | `solution = 8/2k5/1p6/1P6/8/8/8/4K3 b - - 0 1` | 34 |

Forcing `solution = X`-only output suppressed exactly the reasoning LongCoT-Mini exists to measure. This is the recorded terminal blocker.

**Failure mode 2 — `standard` prompt at `max_tokens=2048` (the two earlier partial runs, `…234821Z` / `…stack_…011903Z`).**
Free CoT, no grammar. The model reasons in full — but on these long-horizon items (chess games replayed move-by-move over 100s of plies; dependency-chain math; big-exponent algebra) it **never reaches a `solution =` line within 2048 tokens**. Every one of the 11 completed rows hit the 2048 cap mid-reasoning with **0 `solution =` markers present** → the deterministic scorer would return `no_solution_marker` for all of them → also ~0%. And at 2048 tok/item × 507 items × 2 roles the run is too slow for the window (those runs were aborted after 11/21 rows).

**Net:** grammar kills reasoning (mode 1); unbounded-at-2048 never terminates into the marker (mode 2). The scorer, the dataset, and the structural-match machinery are all **fine** — the *generation protocol* is the defect. The "easy" difficulty label is a dataset tag; these items are still genuinely long-horizon and need a large reasoning budget **plus** a guaranteed terminal answer.

Supporting memory: `feedback_accuracy_token_tradeoff_rescue_metric` explicitly flags **truncation caps** as a baseline confound that fakes a floor — precisely mode 2. `feedback_production_sampling_seed_not_temp0` — sampling-sensitive quality benches use production temp + seed 42; the current runner sends `temperature=0.6` **but no `seed`**, so even a good protocol is non-reproducible today (fixed in the runner SPEC below).

---

## 2. Design requirement (from the postmortem `next_action`)

> Allow **bounded reasoning** while preserving **deterministic final-answer extraction.**

Any redesign must (i) let the model do real CoT with a generous budget, (ii) guarantee a deterministic terminal `solution =` line even when the model is still mid-reasoning at the cap, **without** constraining the reasoning itself, and (iii) keep scoring judge-free.

---

## 3. Options evaluated

### (a) Two-phase prompt — free reasoning, then a grammar-forced final line after a reasoning budget  ← **CHOSEN (core mechanism)**
Phase 1 = free CoT, generous cap, no grammar. Phase 2 = only if Phase 1 did not already emit a `solution =` marker, a *second* turn that feeds the Phase-1 reasoning back and applies the `solution = ` grammar to **that turn only**, forcing exactly the final answer line.
- **Pros:** grammar constrains *only* the terminal answer, never the reasoning that produced it → directly satisfies the requirement. Deterministic marker guaranteed for the scorer. Reasoning-token count preserved for the reasoning-compression signal. Short-circuits (0 extra calls) whenever Phase 1 already ended with a marker.
- **Cons:** two HTTP calls on the truncating tail (~2× latency there); needs a structural runner change (new conditional second turn).

### (b) Unconstrained generation + robust extraction (B7 final-answer-region extractor + math_verify-style parsing; reuse E7-era scorer machinery)
Single call, no grammar, extract with the last-`solution =` anchor plus B7 SCORE-03 final-answer-region fallbacks (last line / `\boxed{}` / colon-anchored).
- **Pros:** parameter-only, no runner code; the adapter *already* does last-marker (final-region) anchoring.
- **Cons:** does **not** solve mode 2 — a mid-reasoning truncation has no marker and no boxed answer, so the region fallback scrapes garbage from the last line → wrong. It cannot *force termination*, so the budget must be pushed very high (slow) with still no guarantee. `math_verify` is math-only and orchestrator-copy-only; LongCoT-Mini answers are SMILES / FEN / JSON arrays/objects — the existing **structural** scorer is the correct one and already exists. **Verdict: insufficient alone.** Its robust-extraction fallback is worth *folding into (a)* as the Phase-1 short-circuit test, not used as the primary fix.

### (c) Reasoning-budget ladder (n_tokens caps at 512/1024/2048/4096) — measure the accuracy-vs-token curve
Run the same items at several reasoning caps to trace accuracy(R). This is *literally what LongCoT-Mini exists for* (the reasoning-compression premise) and directly serves the rescue-metric memory (which items get rescued by more tokens).
- **Pros:** produces the benchmark's headline signal; cheap to add once (a) exists (re-invoke per rung).
- **Cons:** a **bare** cap-ladder inherits mode 2 — at every rung an unfinished item has no marker → 0, conflating "ran out of budget" with "got it wrong". **Verdict: keep as the experimental structure, but build it ON TOP of (a)** so each rung = free-reasoning-capped-at-R + forced-answer terminal turn. That disentangles budget from marker-presence and yields a true accuracy(R) curve.

### Chosen design
**Two-phase forced-final-answer generation (a), with (b)'s robust extractor as the Phase-1 short-circuit, deployed over a reasoning-budget ladder (c).** Scoring is the existing deterministic `structural_exact_match` (`LongCoTMiniAdapter.compute_score_for_result` via `score_longcot_run.py`) — unchanged, no judge, canary reported separately.

---

## 4. Protocol specification (`bulk-inference.longcot-mini-calibration.v2`)

**Per item, per reasoning-budget rung `R`:**
1. **Phase 1 (free CoT):** `POST /v1/chat/completions`, `messages=[user(dataset_prompt)]` (the dataset prompt already ends with the `solution = <value>` format instruction via `SOLUTION_FORMAT_INSTRUCTION`; **no** `concise_solution` system prompt, **no** grammar), `max_tokens=R`, `temperature=0.6`, `seed=42`, `enable_thinking=false`. Record `text1`, `reasoning_tokens = usage.completion_tokens`.
2. **Short-circuit (B):** if `re.search(r"solution\s*=\s*", text1, re.I)` matches → `response=text1`, `phase2_used=false`. No second call.
3. **Phase 2 (forced final line):** only if no marker in `text1`. `messages=[user(dataset_prompt), assistant(text1), user("Output ONLY your final answer now, as a single line, exactly: solution = <value>")]`, `grammar = 'root ::= "solution = " ([^\n])+ "\n"?'`, `max_tokens=64`, `temperature=0.6`, `seed=42`. Record `text2`, `final_answer_tokens`. Set `response = text1.rstrip() + "\n" + text2.strip()` so the scorer's **last-marker** anchor lands on the forced line while the reasoning stays in the row.
4. **Score:** existing deterministic structural scorer over `response`. Canary-leak detection unchanged (reported separately; never folded into pass/fail).

**Reference budget** (non-saturation gate + full calibration run): `R = 4096` (2× the mode-2 truncation point). **Ladder rungs** (follow-on curve): `R ∈ {512, 1024, 2048, 4096}` — brackets the truncation regime; low rungs quantify how much the forced-answer path rescues vs. finished reasoning.

**Arms / roles / n / seed / scoring:**
- **Roles:** `frontdoor` and `worker_general` (v7 quarter stack; each role fans across its 4 CPU quarter ports, one role at a time — unchanged from the entry).
- **Arms:** the reasoning-budget rungs (each `R` is an arm). The probe and the reference full run use the single arm `R=4096`; the ladder run sweeps all four.
- **n:** full = **402 scorable rows** (chemistry 100 + chess 100 + cs 100 + math 102; the 105 null-gold `logic` rows stay excluded). Probe = **30** stratified rows (below).
- **seed:** 42 (production sampling; temp 0.6). *New* — must be added to the payload (runner SPEC §6).
- **scoring:** `structural_exact_match`, deterministic, no judge; `score_longcot_run.py` + `LongCoTMiniAdapter`. Report per-domain accuracy, canary-leak count (separately), and — new — mean `reasoning_tokens` and `phase2_used` rate per role/arm.

### Non-saturation acceptance test (30-question probe, gates the full run)
- **Probe set:** deterministic — first ~7–8 rows per domain by sorted `question_id` (chemistry/chess/cs/math ≈ 8/8/7/7 = 30), reproducible because the adapter sorts by `question_id`. Expose as a `--limit-per-domain`/explicit-id list in the runner SPEC, or a curated `--probe-ids` file; do **not** use a random slice.
- **Arm:** `frontdoor` only (fastest role), two-phase, `R=4096`.
- **Accept (proceed to full run) iff** overall probe accuracy is **strictly between ~10% and 90%** (i.e. `3 ≤ correct ≤ 27` of 30) — neither floor (~0%) nor ceiling (>90%). Marker presence must be ~100% (two-phase guarantees it); if any row still lacks a marker, that's a runner bug — fix before the full run.
- **Escalation:**
  - **Floor at R=4096** (< ~10%): re-probe at `R=8192`. If still floor, the conclusion is that the "easy" items exceed a practical reasoning budget on this stack — record as an OBSERVATION (`INFRA/marginal`: budget-bound floor, *not* a capability signal); do **not** flip K-LCM-1 as "discriminative".
  - **Ceiling (> 90%):** suite is saturated on this stack → entry fork `marginal` → `DONE_MARGINAL_OBS` (EV-9 saturation), record and stop.
  - **In-band:** proceed to the full 402-row reference run (both roles), then the ladder.

---

## 5. Entry YAML change — SPEC block (for `20-eval-tower.yaml` → `RE-4-longcot-mini-calibration`)

*Spec only — do not hand-edit the live entry here; the loop owner applies it. Changes vs. the parked entry:*

- `execution.protocol_id`: `bulk-inference.longcot-mini-calibration.v1` → **`…v2`**.
- `execution.command`: **remove** `--prompt-mode concise_solution` and `--force-solution-grammar`; **add** `--prompt-mode standard --two-phase --reasoning-budget "${LONGCOT_MINI_REASONING_BUDGET:-4096}" --final-answer-max-tokens 64 --seed 42`; keep `--endpoint chat`, the two `--role-ports` lines, `--timeout`, `--summary-out`, and the existing `score_longcot_run.py` scoring loop unchanged. Drop `--max-tokens` (superseded by `--reasoning-budget` in two-phase mode). Proposed command core:

  ```
  .venv/bin/python scripts/benchmark/longcot_mini_stack_runner.py
    --run-id "${RUN_ID}"
    --role-ports frontdoor=8080,8180,8280,8380
    --role-ports worker_general=8082,8182,8282,8382
    --endpoint chat --prompt-mode standard
    --two-phase --reasoning-budget "${LONGCOT_MINI_REASONING_BUDGET:-4096}"
    --final-answer-max-tokens 64 --seed 42
    --timeout "${LONGCOT_MINI_TIMEOUT_S:-900}"
    --summary-out "${OUT_DIR}/stack_runner_summary.json"
  # …then the unchanged score_longcot_run.py loop over frontdoor_*/worker_general_* result files
  ```
  Probe invocation: same command + `--probe-ids probe30.txt` (or `--limit-per-domain 8`) and only `--role-ports frontdoor=…`. Ladder: re-invoke once per `R∈{512,1024,2048,4096}` with `--run-id …_R${R}`.
- `execution.est_wall_clock_h`: raise the ceiling — reference run ≈ prior 4h scale; the 4-rung ladder ≈ up to ~4× on the truncating tail (short-circuit reduces it when Phase-1 markers appear early). Set `est_wall_clock_h: 12.0`, keep `timeout_s` generous.
- `outcomes.gate_table`: **prepend a non-saturation *probe* gate** — "30-q frontdoor probe at R=4096 yields overall accuracy in (10%,90%) with ~100% marker presence" as the precondition to the existing gate. Keep the existing `pass/marginal/fail/infra/ambiguous` fork; add to `pass.action`: "record the accuracy-vs-reasoning-budget curve (R∈{512,1024,2048,4096}) for the reasoning-compression premise." Keep `fail.rule` = "scoring is nondeterministic / requires a judge / harness error" (unchanged — scoring is still judge-free).
- `notes`: append one line — "v2 protocol: two-phase (free CoT → forced `solution=` terminal turn), deterministic structural scoring; supersedes the v1 answer-only-grammar protocol that floor-saturated (frontdoor 0/402, worker_general 0/307)."
- `ledger.journal_quarantine_rule`: already records `reasoning_token_count` — keep; add `phase2_used_rate` and `reasoning_budget_R` to the recorded fields.

---

## 6. Runner code-change SPEC (`scripts/benchmark/longcot_mini_stack_runner.py`)

Structural change → **implement in a follow-on pass** (not in this design task). Precise spec:

**New CLI args (in `main`):** `--two-phase` (store_true), `--reasoning-budget` (int; when set with `--two-phase`, this is the Phase-1 cap and overrides `--max-tokens`), `--final-answer-max-tokens` (int, default 64), `--seed` (int, default 42), and one of `--probe-ids <file>` (newline-delimited `question_id`s) or `--limit-per-domain <int>` for the stratified probe. Thread `seed`/`two_phase`/budgets/`final_answer_max_tokens` into `run_role` → `_run_question`.

**`_run_question` (or a new `_run_question_two_phase`):**
1. Add `"seed": seed` to **every** payload (also fixes the standard/single-phase path's reproducibility gap).
2. Phase 1: current chat call with `max_tokens = reasoning_budget`, **no** grammar, `prompt_mode=standard` (dataset prompt unchanged), `enable_thinking=false`. Capture `text1`, `usage1`.
3. Marker test: `bool(re.search(r"solution\s*=\s*", text1, re.I))`. If present → `response=text1`, `phase2_used=False`, `reasoning_tokens=usage1.completion_tokens`, `final_answer_tokens=0`.
4. Else Phase 2: second chat call, `messages=[user(prompt), assistant(text1), user(FINAL_ANSWER_INSTRUCTION)]`, `grammar=SOLUTION_MARKER_GRAMMAR`, `max_tokens=final_answer_max_tokens`, same `temperature`/`seed`. `response = text1.rstrip() + "\n" + text2.strip()`, `phase2_used=True`, `final_answer_tokens=usage2.completion_tokens`. Define `FINAL_ANSWER_INSTRUCTION = "Output ONLY your final answer now, as a single line, exactly: solution = <value>"`.
5. Row additions: `reasoning_tokens`, `final_answer_tokens`, `phase2_used`, `reasoning_budget`, `text1_len`; keep existing `completion_tokens`/`tokens_per_second` semantics (set `completion_tokens = reasoning_tokens + final_answer_tokens`).

**Probe selection (in `main`, after `load_suite`):** if `--probe-ids`, filter `questions` to that id set; elif `--limit-per-domain N`, group by `question.metadata` domain (available via the adapter's `scoring_config`/`metadata`) and take the first `N` per domain by sorted `question_id`. Deterministic, no sampling.

**Summary additions:** `two_phase`, `reasoning_budget`, `final_answer_max_tokens`, `seed`, and per-role `phase2_used_rate` + `mean_reasoning_tokens`.

**Scorer:** unchanged. `LongCoTMiniAdapter.compute_score_for_result` already anchors on the **last** `solution =` (the B7/SCORE-03 final-answer-region behavior) and canonicalizes JSON/SMILES/FEN — the forced Phase-2 line becomes that last marker. *(Optional belt-and-suspenders, not required since two-phase guarantees a marker: a `no_solution_marker` scorer fallback to `\boxed{}` / last-line, aligned to B7 SCORE-03. Leave off the primary path to keep the ratified pattern intact.)*

**Tests to add** (mirror existing `test_*` siblings; no live inference): monkeypatch the HTTP call to return (i) a Phase-1 text WITH a marker → asserts 1 call, `phase2_used=False`; (ii) Phase-1 WITHOUT a marker → asserts 2 calls, grammar present on the 2nd, `response` ends with the forced line, scorer extracts it; (iii) `seed` present in every payload; (iv) `--limit-per-domain`/`--probe-ids` yields the deterministic 30-row stratified set.

---

## 7. Probe → full-run sequence

- [x] **RE-4.0 — implement runner v2** ✅ 2026-07-21 (research `9323213d`: two-phase + seed + token accounting + probe selection; 7 tests; v1 byte-identical) (follow-on pass): apply §6 to `longcot_mini_stack_runner.py` + add the four tests; run the new unit tests (no inference). Land on the research repo.
- [x] **RE-4.1 — apply entry v2 spec** ✅ 2026-07-21 (protocol_id v2, two-phase command, probe gate prepended, est 12h; recompiled) (§5) to `20-eval-tower.yaml` (loop owner; recompile the batch entry). Protocol id → `…v2`.
- [ ] **RE-4.2 — non-saturation probe** (operator quiet-window, v7 quarter stack, autopilot stopped): frontdoor-only, two-phase, `R=4096`, 30 stratified rows. Score with `score_longcot_run.py`. **Gate:** overall accuracy ∈ (10%, 90%) AND marker presence ~100%. If floor → re-probe `R=8192` (§4 escalation); if ceiling → `DONE_MARGINAL_OBS`, stop.
- [ ] **RE-4.3 — full reference run** (only if RE-4.2 in-band): both roles, two-phase, `R=4096`, all 402 rows. Record per-model deterministic accuracy vs. the 90% saturation line, per-domain, canary-leak count (separately), mean reasoning tokens, `phase2_used` rate. Apply the existing entry gate fork.
- [ ] **RE-4.4 — reasoning-budget ladder** (follow-on curve; the reasoning-compression signal): re-run the 402 rows at `R∈{512,1024,2048,4096}` (both roles). Emit accuracy(R) per role/domain and the **rescue set** (items wrong at low R, correct at high R) per `feedback_accuracy_token_tradeoff_rescue_metric`. Observation-grade.
- [ ] **RE-4.5 — package + ledger**: package artifacts to `coordination/inference-batch/bundles/RE-4/`; write the terminal ledger row (`DONE_PASS` / `DONE_MARGINAL_OBS` per the fork); flip `K-LCM-1` only on `DONE_PASS`. Update `handoffs/active/inference-batch-loop.md` "RE-4 protocol repair" checkbox.
- [ ] **RE-4 runner confidence/persistence parity** (filed 2026-07-22, from the confidence-coverage audit): `longcot_mini_stack_runner.py` (epyc-inference-research) was NOT covered by the orchestrator-side uniformity fixes (`7f69ad4d`) — before RE-4.3 runs, verify it (a) persists per-question rows incrementally, (b) captures confidence with `confidence_is_real` provenance or emits honest nulls (never placeholder 0.0), (c) classifies infra errors as excluded rows (REL-1). Coverage table: `handoffs/active/safetygate-rlvr-provenance-audit-2026-07-22.md`.

---

## 8. Answer to the task's RETURN

- **Chosen design:** two-phase forced-final-answer generation (free CoT → grammar-forced `solution=` terminal turn *only when* Phase 1 didn't emit one), scored by the existing deterministic structural matcher, deployed over a reasoning-budget ladder {512,1024,2048,4096} with a `R=4096` reference. This gives bounded reasoning + deterministic extraction and produces the accuracy-vs-token curve the benchmark exists for.
- **Probe plan:** 30 stratified rows (8/8/7/7 chem/chess/cs/math by sorted id), frontdoor-only, R=4096, deterministic scorer; accept iff accuracy ∈ (10%,90%) with ~100% marker presence; escalate R→8192 on floor, mark saturated on ceiling.
- **Runner code changes needed:** **YES** (structural). SPEC in §6: `--two-phase`/`--reasoning-budget`/`--final-answer-max-tokens`/`--seed`/probe-selection flags, a Phase-1→Phase-2 conditional second turn, `seed` added to every payload (fixes a standing reproducibility gap), row/summary token accounting, and four monkeypatched unit tests. Scorer (`score_longcot_run.py` / `longcot_mini_adapter.py`) is unchanged. Per the task's "prefer spec-only if the change is structural," the runner was **not** edited by this design task.
