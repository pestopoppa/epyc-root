# Speculative-Decoding / MTP Refresh — superseded history through 2026-09-29

> **Historical ledger only; current work lives in [`../active/speculative-decoding-mtp-refresh.md`](../active/speculative-decoding-mtp-refresh.md).**
> Superseded state notes (v5/v6/v8 eras) and the withdrawn 2026-07-30 ngram text, preserved unedited; the retraction
> banner that governs it stays in the active file.

## Current State Correction (updated 2026-07-29)

- Production has moved past the June v5/ik split and the July v7 promotion. Current production is the single frozen `production-consolidated-v8` llama.cpp tree at `67a433bf45a8a091d83b4ea0b32ff0735fd51800` / binary `10107`; `ik_llama.cpp` remains deprecated as a separate production binary.
- The June dense-Gemma measurements below remain useful observations, but future benches/deploy decisions must use the v8 native flag surface (`--spec-type draft-mtp`, `--spec-draft-n-max`) or a successor experimental branch freshly started from v8. Do not revive the separate ik runtime except to reproduce historical results.
- `worker_general` Gemma4-26B-A4B still uses Google's official assistant head; the architecture question is no longer "mainline vs ik" but draft depth / sampling / quality under v8 and, for future Qwen work, whether any remaining MTP port belongs in `llama.cpp-experimental`.

## Historical State (verified 2026-06-22; superseded by v6 cutover)

- Our fork `production-consolidated-v5` (HEAD a6c793fc66): `--spec-type` = ngram-only; **no `draft-mtp`**; EAGLE3 is an inert `// TODO PR-18039` stub. Qwen3.6/3.5 MTP heads are NOT runnable here.
- gemma-4-26B-A4B (worker_general) MTP runs on a **separate** clone `/mnt/raid0/llm/ik_llama.cpp` branch `production-gemma4-mtp` (patched PR #1744), NOT the consolidated fork.
- The worker drafter `gemma-4-26B-A4B-it-assistant-Q8_0.gguf` is **Google's official assistant head** (verified GGUF metadata: `general.architecture=gemma4_mtp`, `Gemma4AssistantForCausalLM`, Apache-2.0), GGUF-quantized in-house — registry wording corrected this session.

## ngram speculation — measured 2026-07-30, and it changes two verdict rows

> **Read this before the verdict table above.** The table's framing is *draft-model* speculation.
> **`ngram-mod` needs no draft model**, so two rows the table closes are re-opened by it.
> ⛔ **CORRECTED 2026-07-31.** The struck sentence below was wrong on both counts.
> ~~Production launches `--spec-type draft-mtp` **alone**; the MASTER registry has carried
> `ngram_candidate_spec_type: ngram-mod,draft-mtp` as a **never-deployed candidate**.~~
> Composed `ngram-mod,draft-mtp` **is** the production recipe (operator standing decision);
> it was deployed by K16 on 2026-07-16 with live cmdlines verified, then silently
> un-deployed by research commit `2370025f` (2026-07-19), which demoted `spec_type` back to
> `draft-mtp` and moved the composed value into the sidecar `ngram_candidate_spec_type`.
> That sidecar field is now **RETIRED** and the registry carries the composed recipe directly.
> **Canonical source — link, do not restate:** the `speculative_decoding_policy` block at the
> top of `epyc-inference-research/orchestration/model_registry.yaml`.
> Note this correction is independent of the 2.80× retraction above: the composed recipe is
> carried for its repetitive-context upside at an accepted ~−1.6% ordinary-text cost, **not**
> because of the retracted speedup.
> Root-cause context and attestation: [numa-placement-defect-20260730.md](../active/numa-placement-defect-20260730.md)
> → *ngram speculation*. Era `production-consolidated-v8` @ `67a433bf4` (binary `10107`),
> protocol `P-BENCH-PLACEMENT-1` (ratified 2026-07-30), region-lock held as `role='bench'`.

Measured on **realistic text** — real repository source, **10.6 % repeated 5-grams**:

| model / role | prompt | `draft-mtp` | `ngram-mod,draft-mtp` | speedup |
|---|---:|---:|---:|---:|
| Qwen3.6-35B-A3B — `frontdoor` / `coder_escalation` | 14,059 tok | 24.92 (accept `.505`) | **69.89** (accept `.755`) | **2.80×** |
| Qwen3.6-35B-A3B | 53,730 tok | 12.46 | 18.71 | **1.50×** |
| Qwen3-Next-80B — `ingest_long_context` | — | 17.40 | **20.06** (accept `.812`) | **1.15×** |
| gemma4-26B-A4B — `worker_general` (accept `.754`) | — | — | — | **no gain** |
| Qwen3.5-122B-A10B — `architect_general` (accept `.650`) | — | — | — | **no gain** |

**PRINCIPLE: ngram's benefit is inversely proportional to the incumbent drafter's acceptance
rate.** It fills headroom, and there is none when the drafter is already strong. That single rule
predicts all five rows — and it means the "MoE CPU spec-dec is low-EV because expert verification
dominates" verdict is **about draft-model speculation specifically**, not about speculation.

**Verdict-table amendments (2026-07-30):**

* **Qwen3.6-35B-A3B (frontdoor + coder_escalation)** — the row reads "operator-gated low-EV bench
  only, pure-MoE-A3B = worst CPU-MTP case". That stands **for MTP**. With `ngram-mod` stacked in
  front of it the same role measures **2.80× at 14k tokens**. The low-EV verdict does **not**
  transfer to the ngram path.
* **Qwen3-Next-80B (ingest)** — the row reads "not viable on CPU", and the registry carries
  `acceleration: {type: none}` because its **SSM hybrid has no draft-model path**. `ngram-mod`
  requires no draft model: **it is the only speculation this role can have**, and it measures
  `17.40 → 20.06` with `.812` acceptance. Re-read the verdict as *no draft-model speculation*,
  not *no speculation*.
* **gemma4-26B-A4B and Qwen3.5-122B-A10B** — unchanged. Measured **no gain**; their incumbent
  drafters already have the acceptance.

**Methodological caveat that must travel with any ngram number.** A first pass used **synthetic
filler** — 99.7 % repeated 5-grams, 23 distinct tokens across 8,736 words — and returned `2.52×`.
That is nearly worthless as evidence: it measures the filler, not the workload. Real repository
text confirmed the *direction* but **moved the number**. **Every ngram claim must carry its
corpus and its repeated-5-gram fraction.**
