# Architect-Candidate Benchmark — Runbook (SOP)

**Purpose.** A repeatable, decision-grade procedure for answering one question about any *new* architect
candidate model: **is it worth deploying as the `architect` role** (deep multi-step reasoning / planning /
decomposition over broad context) — and if its quality merely *ties* the incumbent, does anything else
justify the switch?

**Status.** Adopted 2026-07-20, distilled from the first full run (Qwen3.5-122B-IQ2 vs Qwen3.6-27B-dense
vs Qwen3.6-35B-A3B). That run's evidence + verdicts live in
[`../../handoffs/active/architect-model-selection-bench.md`](../../handoffs/active/architect-model-selection-bench.md)
and [`architect-model-selection-2026-07-20.md`](architect-model-selection-2026-07-20.md). This runbook is
the *process*; those are the *instance*. Numbers quoted here are illustrative from that run — re-measure,
never inherit.

**Audience.** An operator or agent session with GPU access. Everything here is measurement-only; it makes
**no** production stack change. A deployment change is a separate, operator-gated action *informed* by this
result.

---

## 0. Golden rules (read once, they are the difference between a result and an artifact)

1. **A quality number is decision-grade; a throughput number is an OBSERVATION until `P-GPU-1` certifies it.**
   Accuracy is device-independent — it gates. GPU t/s does not gate until post-promotion cert. Era-stamp
   everything (MEASUREMENT.md).
2. **Pair everything.** Every arm answers the *identical* questions (pinned to disk), so deltas are
   McNemar-testable. Re-sampling per arm silently voids the pairing.
3. **A cross-arm parse-failure gap is a scorer bug until proven otherwise** — it penalises exactly the
   models that show their work. Always report per-arm `noparse`/`truncated`/`empty` next to accuracy.
   ([[feedback_parse_failure_rate_is_a_scoring_artifact]])
4. **Persist every full response.** A scorer fix is then replayed offline at *zero* inference cost. This
   single discipline saved hours on the 2026-07-20 run (three separate scorer issues, all re-scored, none
   re-run). ([[feedback_incremental_persistence]])
5. **Classify failures by reason.** A truncated answer (`finish_reason=length`) is a *budget* failure; an
   unparseable one is a *scorer* failure; a wrong one is a *reasoning* failure. Never let the first two
   masquerade as the third. ([[feedback_classify_eval_failures_by_reason]])
6. **Never edit a shell script while it is executing** (bash resumes at a shifted byte offset). Copy to
   `*_run.sh` and launch the copy. ([[feedback_never_edit_running_shell_script]])
7. **GPU-only. Do not touch the CPU inference stack.** Pin the bench server to spare cores, `--device
   ROCm0 -ngl all`, one arm at a time. Verify production ports stay healthy throughout.

---

## 1. Prerequisites & gates

- [ ] **Kernel:** the current production kernel's GPU build (`llama.cpp/build-hip/bin/llama-server`), e.g.
      `production-consolidated-v7`. Confirm `--version` and record it. Bench numbers must come from the
      real production binary, never a stripped bench build.
- [ ] **GPU idle:** `rocm-smi --showuse --showmemuse` → 0% / 0 VRAM, no KFD PIDs. The single MI210 runs
      **one arm at a time**.
- [ ] **CPU stack untouched:** the production llama-servers run `--device none`; leave them. Pin the bench
      server to spare cores (e.g. `taskset -c 88-95`, node 3) and `OMP_NUM_THREADS=1`.
- [ ] **Operator approval** for GPU inference (`feedback_no_concurrent_inference`). GPU-only work may be
      approved even when the broader inference-batch gate is closed — that is an explicit, narrow grant.
- [ ] **Datasets cached** (offline): verify each suite's HF dataset loads under `HF_DATASETS_OFFLINE=1`
      before starting (§4 lists them). Missing cache → fetch in a bounded, non-GPU step first.
- [ ] **Candidate GGUF on disk**, plus the incumbents you will pair against.

---

## 2. Define the arms

Always include, at minimum:

| Role in the bench | What it is | Why |
|---|---|---|
| **Candidate** | the new model @ its intended deploy quant + device | the thing under test |
| **Incumbent architect** | whatever holds `architect` today, @ its deploy quant/device | the bar to beat |
| **Quant-control** (if candidate is quantized) | the *same* model at a near-lossless quant | isolates quant damage from architecture (this is the H1 axis) |
| **Frontdoor / shallow baseline** | the smallest routed model | sanity floor — if it ties, the suite can't separate the field (see §8 saturation) |

Record each arm as `(model, quant, device, spec-dec config)`. **Index every measurement by model/quant,
never by role** ([[feedback_model_not_role_indexing]]) — a model serving several roles is measured once.

---

## 3. Per-model config discovery (do this BEFORE the quality runs)

Each model has its **own** optimal GPU serving config; do not inherit another model's. Sweep, then pin.

- **Spec-dec draft depth is per-model.** On the 2026-07-20 run the optimum differed on the *same* GPU and
  kernel: 122B-IQ2 → `draft-mtp n-max 2`; 27B-dense and 35B-A3B → `n-max 4`. Inheriting one cost ~29% t/s.
- Sweep `{spec none, draft-mtp n-max ∈ 1..4}` × KV/`-ub` at production sampling, ~512-token generations,
  best-of-2, with an output-coherence check. Pick the max-decode config that stays coherent.
- **Record the winner in the research registry** as `acceleration.optimal_gpu_serving` (+ a
  `gpu_spec_depth_sweep_observation`) so no future session re-derives it. Grade = observation (pre-`P-GPU-1`).
- Confirm the model's reasoning-mode requirement: for Qwen3.x, `--reasoning off` server-side **and**
  `chat_template_kwargs.enable_thinking=false` request-side are mandatory (else degenerate `<think>` loops
  — see §6 and [[feedback_qwen3x_enable_thinking_false]]). Verify by curling one degenerate-prone prompt
  and confirming non-empty `content`.

---

## 4. The suite ladder (what to run, in order, and why)

Run **cheap-and-saturating first, decisive-and-hard last**. Each rung has a distinct job; do not collapse
them.

> **⚠ PILOT-GATE (mandatory before any full multi-arm run) — added 2026-07-22 after it bit.** Before
> committing all arms × full-n to a suite, run **one arm (the incumbent) on a ~20-item pilot** and check the
> saturation diagnosis (§8). If the pilot saturates (all/near-all correct) the suite will not discriminate —
> **do not run the full matrix**; fix the suite (harder items / better scorer) first. On the 2026-07-20/22
> run this step was skipped for `olympiadbench_numeric`: A1 came back 89.3% (saturated — the clean-numeric
> filter had selected the easy-answer subset), so 3 arms × 150 items of GPU time bought only a
> higher-powered *restatement* of a null already known, not the harder-difficulty test the suite was built
> for. A 20-item pilot on A1 would have flagged it and redirected to the symbolic-scorer fix first. **The
> saturation diagnosis belongs on a pilot, not on the full result.**

| # | Suite (adapter) | Job | n | Notes |
|---|---|---|---|---|
| L0 | **`mmlu_pro`** | knowledge control | 100–200 | should show quant-parity *while* reasoning suites reveal gaps — the asymmetry is the point |
| L1 | **`gpqa_diamond`** (letter-only) | no-CoT prior/knowledge probe | 198 | ~2 tokens/q; a floor, saturates for strong models |
| L2 | **`gpqa_diamond_cot`** | reasoning w/ CoT in `content` | 198 | the +CoT lift is large (≈+30pp); still saturates ~85–90% for frontier-ish models |
| L3 | **`aime25`** (avg@k) | decisive competition-math reasoning | 30 × k | lower ceiling than GPQA; **the discriminator** — but only 30 items |
| L4 | **`olympiadbench_numeric`** | harder-tier ceiling-breaker | 100–150 | 492 cleanly-scorable items; use when L3 saturates (it usually does) |
| A | **thinking ablation** (`--reasoning on/off`) | is the native `<think>` channel worth it? | 50 | see §6 |
| B | **effort / `--reasoning-budget`** | can native thinking be made safe/cheap? | 50 | see §6; ref [`reasoning-effort-levels.md`](../../handoffs/active/reasoning-effort-levels.md) |
| P2 | **SWE-bench-Verified agentic** (FAIL_TO_PASS) | the architect's *actual job*: tool-using multi-step planning | — | operator-gated design; objective oracle, no model-judge |

**Datasets (HF, cached):** `TIGER-Lab/MMLU-Pro`, `ankner/gpqa` (main 448 — Diamond membership recovered
from `hendrydong/gpqa_diamond`, 198), `opencompass/AIME2025` (30, 2025-only — *not* 2024, which predates
model cutoffs and conflates recall), `math-ai/olympiadbench` (674 → 492 single-answer Numerical with
clean gold).

**Why the ladder, not one big suite:** strong models saturate GPQA (~85–90%), where 1–2 questions
separate any two arms and a null is weak evidence ([[feedback_eval_saturation_masks_model_gap]]). AIME'25
has a lower ceiling but only 30 items (low power). OlympiadBench supplies *harder items at real n* — the
one thing the others can't. Run them all; read them together.

---

## 5. Protocol constants (identical across arms)

- **Production sampling, seed-pinned:** `temperature 0.6, top_p 0.95, top_k 20, seed 42` (+1 per avg@k
  pass). NOT temp-0 — greedy distorts sampling-sensitive reasoning/MTP measurements and can invert signs
  ([[feedback_production_sampling_seed_not_temp0]]).
- **`enable_thinking=false`** and server `--reasoning off` for the main quality runs (the ablation §6 is
  the sole exception).
- **Token budget generous enough that truncation is rare** (`max_tokens` ≥ 8192 for CoT, ≥ 16384 for
  AIME/Olympiad — the 122B legitimately uses ~9k on hard items). A truncated answer scores wrong for a
  *budget* reason; if the truncation rate is more than a few %, raise the budget and re-run (or top-up).
- **avg@k for low-ceiling suites** (AIME): k independent draws (seeds `42..42+k-1`); report **avg@k** (mean
  over draws) and **pass@k** (solved ≥1). k is variance reduction on the same items — it does not raise the
  item count, so it cannot manufacture separation; the power limit is n.
- **Pin the question set** on the first arm (`--questions-out`), replay on every later arm and every future
  session (`--questions-in`). This is what makes a *later CPU-arm session* comparable.

---

## 6. The two reasoning axes (do not conflate them)

"Should our models reason?" is **two independent questions**. The 2026-07-20 run measured both:

1. **Prompt axis — does the prompt permit CoT in `content`?** *Large lever.* Letter-only → "reason step by
   step" was **+32.0pp** (p=8.6e-04) at ~4× tokens. This is a per-role *prompt-template* property, and it
   validated the harness (CoT score matched vendor-published within noise).
2. **Native-channel axis — `--reasoning on` / `enable_thinking`.** *Liability as configured.* Unlimited
   native `<think>` **lost** for both models (−16pp architect, −36pp frontdoor) — but the cause was a
   **non-termination tail** (18% / 50% of items burned the whole budget inside `<think>` and emitted no
   answer), not a reasoning deficit (where it *did* terminate, on/off was n.s.).
   - **Fix — budget-capped thinking:** `--reasoning on --reasoning-budget N --reasoning-budget-message
     "…"` force-closes `<think>` so the model must answer. This drove non-termination to **0%** and
     recovered accuracy to ≈ think-off (neutral, p≈1.0), at ~1.6–3× tokens instead of 6×. Higher budget was
     ≤ lower budget — more room only adds derailment.

**Takeaway for deployment:** the accuracy lever is the **prompt** (axis 1); `--reasoning-budget` is the
**safety mechanism** that makes the native channel usable without the tail risk. Both are **per-model** —
the non-termination severity was 18% vs 50% across two models, so certify each model independently
([[reasoning-effort-levels]]).

---

## 7. Scoring discipline (where benches go wrong)

- **Multiple choice** (`extract_letter_answer`): explicit `ANSWER:`/`\boxed` tag → answer-marker
  (last-match, CoT says "answer" repeatedly) → terse letter → **bare letter alone on the final line** →
  single-candidate fallback. The bare-final-line rule is essential: without it, verbose (CoT) arms fail to
  parse while terse arms score fine — a direct bias against the models that reason.
- **Math** (`math_numeric`): brace-balanced `\boxed{}` extraction (`extract_boxed`) → numeric equivalence
  (`parse_math_number`: handles `\frac`, `\sqrt`, `%`, products, `\pi`). **Filter the suite to items whose
  GOLD parses to a clean number** so every item is scorable and a parse miss can only be the model's — do
  not trust substring/LaTeX matching (it reintroduces per-arm bias). Validate the scorer offline:
  gold-scores-itself ≈100%, perturbed-gold ≈0% false-positive.
- **Exact match** (`exact_match` + `extract_patterns`): ordered most-explicit-first, last-match-wins;
  `normalize_numeric` for integer answers (AIME).
- **After any scorer change, re-score every arm offline** (`architect_bench_rescore.py`) and make the
  analyzer prefer `*.rescored.jsonl` — never compare arms scored under different rules.

---

## 8. Statistics & stopping rules

- **Paired McNemar** on binary correctness (per question, or pass@k) is the primary test. Report discordant
  counts `b`,`c` and the exact p — with `n=30` and ~4 discordant pairs, "significant"-looking deltas are
  usually noise.
- **avg@k → paired bootstrap** on the continuous per-question score when k>1 (McNemar needs binary).
- **Saturation diagnosis** (run it before believing a null): count questions where all arms are
  saturated-equal (all-correct or all-wrong). If half the suite carries no discriminating signal, the
  effective n is tiny and a null means "suite too easy," not "models equal." That is the trigger to climb
  to L4 / a harder suite.
- **Difficulty-descending sequential evaluation** (efficiency): for a suite with an **a-priori,
  model-independent** difficulty key (AIME problem number — validated: tiers 1–5/6–10/11–15 → 92/76/50%),
  run hardest→easiest with arms **interleaved per question**, and stop early on:
  (a) **saturation** — remaining easier items carry ≈0 info (always safe); or
  (b) **decision** — an **always-valid / e-process** boundary for separation *or* futility (reuse the
  reviewer control-plane e-process infra; a fixed-α peek is p-hacking).
  **Rank only by the a-priori key, never by your own arms' solve rates** — that is circular selection and
  manufactures significance. This is ordering/stopping efficiency, not a power fix.

---

## 9. Decision framework

1. **Candidate ≫ incumbent on the decisive suites (L3/L4), significant** → strong deploy signal; proceed to
   P2 (tool-use) to confirm the architect's real job, then propose the swap.
2. **Candidate ≈ incumbent (null after L4 with adequate power)** → **accuracy does not decide.** Fall to the
   **deployment-robustness axis** — and it is not neutral:
   - **Self-fallback:** a GPU-only model with no viable CPU home (e.g. a dense model at ~4 t/s on CPU) has
     no self-substitute for GPU drains/failure; it needs a *separate* fallback architect and **pins the
     single GPU slot**.
   - A **dual-resident** model (fits GPU *and* CPU at a deployable quant) is **cheaper to operate at equal
     quality** — this typically favors keeping the incumbent when quality ties.
   - Weigh: quant headroom, KV/context ceiling, tool-access latency, and what else wants the GPU slot.
3. **Candidate ≪ incumbent** → reject; if it was a cheaper-residency bet, record the quality cost and stop.

> The bench answers "is quality different?" The deploy decision also weighs "what does it cost to *operate*?"
> A quality tie is the branch where operating cost wins — usually for the dual-resident option.

---

## 10. Tooling (all in `epyc-inference-research/scripts/benchmark/`)

- **Runner:** `v7_quality_gate_runner.py` — flags: `--suites --n --seed --repeats`,
  `--temperature/--top-p/--top-k`, `--enable-thinking/--no-enable-thinking`, `--max-tokens`,
  `--per-question-out` (incremental JSONL), `--questions-out/--questions-in` (pin/replay), `--limit`,
  `--arm`, `--kernel/--binary/--models` (metadata). **Idempotent `(id,seed)` resume**: never re-queries a
  collected draw — safe restarts and avg@k top-ups (add seeds only).
- **Adapters:** `dataset_adapters.py` — suites `mmlu_pro`, `gpqa_diamond`, `gpqa_diamond_cot`, `aime25`,
  `olympiadbench_numeric`. Scoring paths `multiple_choice`, `exact_match`, `math_numeric`.
- **Analysis:** `architect_bench_analyze.py` (paired McNemar/bootstrap, per-arm failure columns, prefers
  `*.rescored.jsonl`), `architect_bench_rescore.py` (offline re-score from stored responses),
  `thinking_ablation_analyze.py`, `e6_budget_analyze.py`.
- **GPU serving pattern** (record the exact recipe per run):
  `env LD_LIBRARY_PATH=<build-hip>/bin GGML_IQK=1 ROCR_VISIBLE_DEVICES=0 OMP_NUM_THREADS=1 taskset -c 88-95
  llama-server -m <gguf> --device ROCm0 -ngl all -fa on --reasoning off --metrics --slots --jinja
  -c 32768 -b 2048 -ub 2048 -ctk f16 -ctv f16 <per-model spec-dec> --port 18072`. One arm up at a time;
  `kill -TERM` then verify `ps -p` dead (escalate to `-9`) before the next; confirm VRAM releases to 0.
  *(The per-arm/per-budget driver scripts used on 2026-07-20 live in the session scratchpad; promote them
  into the repo when this runbook is next exercised.)*

---

## 11. Artifact layout & reproducibility

```
artifacts/architect-bench-<date>/
  questions_<suite>.json          # pinned item set — the paired contract; later sessions MUST replay it
  sweep_<arm>/results.jsonl       # per-model spec-dec config sweep
  runs/<suite>/<arm>/
    per_question.jsonl            # every draw: id, seed, expected, extracted, correct, finish_reason,
                                  #   truncated, completion_tokens, reasoning_chars, full response(-4000)
    per_question.rescored.jsonl   # after any scorer fix (analysis prefers this)
    result.json                   # per-suite summary + full meta (sampling, budget, pinned-set path)
    server_command.txt, timings.txt, rocm_during.txt
  ablation_thinking/<arm>_think{on,off}/
  e6_reasoning_budget/<arm>_budget<N>/
```

Every `result.json` carries the sampling config, budget, kernel, binary, and pinned-set path — so a result
is self-describing. Era-stamp; append, never overwrite historical numbers (MEASUREMENT.md).

---

## 12. Failure modes / gotchas (each cost time on the first run)

- **`--reasoning off` is a real flag** (`-rea/--reasoning [on|off|auto]`) — it genuinely disables thinking,
  it does not merely hide tags. Reasoning goes to `reasoning_content` under `--reasoning-format deepseek`.
- **Truncation ≠ wrong reasoning.** If truncation >~5%, raise `max_tokens`; on a resumed run the idempotent
  resume lets you top-up only the affected draws.
- **`pkill -f <pattern>` self-matches** your own command line (exit 144). Kill by PID; `TaskStop` on a
  background job cleanly takes down the whole process group (verified).
- **Saturation masquerades as parity.** Always run the §8 saturation diagnosis before reporting a null.
- **Circular difficulty selection.** Rank by a-priori difficulty only; never by your own results.
- **Two "reasoning" axes.** Prompt-CoT vs native-`<think>` are independent (§6); a stack review that flips
  `enable_thinking` and stops there leaves the larger prompt lever untouched.

---

## 13. End-to-end checklist

- [ ] Gates (§1) clear; kernel/GPU/stack/approval/datasets/GGUFs verified and recorded.
- [ ] Arms defined (§2); measurements keyed by model/quant.
- [ ] Per-model spec-dec swept and pinned to the registry (§3); reasoning-mode requirement confirmed.
- [ ] Question sets pinned on arm 1 (§5); every later arm replays them.
- [ ] Ladder run L0→L4 (§4), production sampling (§5), one arm at a time, GPU-isolated.
- [ ] Per-arm `noparse/truncated/empty` reported next to accuracy (§0.3); scorer validated offline (§7).
- [ ] Saturation diagnosis run before any null is believed (§8).
- [ ] Thinking ablation + budget-cap (§6) if the native channel is in question.
- [ ] Paired McNemar / bootstrap per suite (§8), era-stamped.
- [ ] Decision framework applied (§9); if quality ties, deployment-robustness assessed explicitly.
- [ ] P2 tool-use (SWE-bench agentic) if a survivor needs its *actual job* validated (operator-gated).
- [ ] Verdict recorded in the handoff; registry-change note opened (do **not** edit the live registry —
      operator-gated).

---

*Cross-refs:* [`architect-model-selection-bench.md`](../../handoffs/active/architect-model-selection-bench.md)
(the live instance) · [`architect-model-selection-2026-07-20.md`](architect-model-selection-2026-07-20.md)
(evidence/decision-tree) · [`reasoning-effort-levels.md`](../../handoffs/active/reasoning-effort-levels.md)
(the effort ladder) · `MEASUREMENT.md` (instrument constitution).
