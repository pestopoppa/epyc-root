# Speculative-Decoding / MTP Refresh

**Status**: active (created 2026-06-22 via operator-directed MTP review; v6 status correction added 2026-07-11)
**Categories**: speculative_decoding, hardware_optimization, local_inference, moe_optimization
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md), [`summary-token-attention-readiness.md`](summary-token-attention-readiness.md); completed: [`gemma4-mtp-drafter-evaluation.md`](../completed/gemma4-mtp-drafter-evaluation.md), [`mtp-speculative-decoding.md`](../completed/mtp-speculative-decoding.md)

## Objective

Decide which remaining MTP (multi-token-prediction) speculative-decoding paths are worth operator benches now that production is frozen at `production-consolidated-v8` with native MTP/NEXTN support, and now that the Qwen/native MTP surface has a built experimental checkpoint. The open work is no longer "does our fork have MTP at all"; it is per-model deploy evidence under the v8 native runtime or a future refreshed experimental line started from current production. **All numbers here are OBSERVATIONS (MEASUREMENT.md) — none gate a keep/deploy decision; the operator runs all benches.**

## Current State Correction (updated 2026-07-29)

- Production has moved past the June v5/ik split and the July v7 promotion. Current production is the single frozen `production-consolidated-v8` llama.cpp tree at `67a433bf45a8a091d83b4ea0b32ff0735fd51800` / binary `10107`; `ik_llama.cpp` remains deprecated as a separate production binary.
- The June dense-Gemma measurements below remain useful observations, but future benches/deploy decisions must use the v8 native flag surface (`--spec-type draft-mtp`, `--spec-draft-n-max`) or a successor experimental branch freshly started from v8. Do not revive the separate ik runtime except to reproduce historical results.
- `worker_general` Gemma4-26B-A4B still uses Google's official assistant head; the architecture question is no longer "mainline vs ik" but draft depth / sampling / quality under v8 and, for future Qwen work, whether any remaining MTP port belongs in `llama.cpp-experimental`.

## Historical State (verified 2026-06-22; superseded by v6 cutover)

- Our fork `production-consolidated-v5` (HEAD a6c793fc66): `--spec-type` = ngram-only; **no `draft-mtp`**; EAGLE3 is an inert `// TODO PR-18039` stub. Qwen3.6/3.5 MTP heads are NOT runnable here.
- gemma-4-26B-A4B (worker_general) MTP runs on a **separate** clone `/mnt/raid0/llm/ik_llama.cpp` branch `production-gemma4-mtp` (patched PR #1744), NOT the consolidated fork.
- The worker drafter `gemma-4-26B-A4B-it-assistant-Q8_0.gguf` is **Google's official assistant head** (verified GGUF metadata: `general.architecture=gemma4_mtp`, `Gemma4AssistantForCausalLM`, Apache-2.0), GGUF-quantized in-house — registry wording corrected this session.

## Per-model verdict table

| Model / role | Arch | New upstream | Verdict | Why |
|---|---|---|---|---|
| **gemma-4-31B (DENSE, not deployed; on disk)** | dense | official `gemma-4-31B-it-assistant` head (491 MB, **on disk**) | **directional dense CPU-MTP win; promotion still gated** | T1 closed at ~1.84× after clean host-quiesced measurement; prior 2.98× single-run was corrected. Promotion still needs multi-prompt reps + Leviathan-style quality pass, and the path should be translated to v6/native flags or the refreshed experimental v7 branch before any deploy decision. |
| **Qwen3.5-9B (DENSE, not deployed; MTP GGUF downloaded)** | dense | `unsloth/Qwen3.5-9B-MTP-GGUF` | **functionally verified; structured-output niche** | T3 first closed via fresh upstream build: Q4_K_M baseline 14.90 → MTP 29.30 t/s, 87% draft accept, correct output. 2026-07-17 experimental-v7 MI210 evidence: no-spec is faster for tiny exact completions; native MTP is faster for long repetitive structured output with `682/682` draft tokens accepted; broader `default+expanded` slice keeps the same `13/18` pass profile while MTP improves mean decode `105.88 -> 114.09 t/s`. Not a broad frontdoor/worker role claim. |
| **Qwen3.6-35B-A3B (frontdoor + coder_escalation)** | MoE A3B | native NEXTN/MTP head; `unsloth/Qwen3.6-35B-A3B-MTP-GGUF`; mainline PR #22673 | **operator-gated low-EV bench only** | unblocks 2 roles BUT pure-MoE-A3B = worst CPU-MTP case (26B-A4B MoE measured only 1.06×). The experimental Qwen/native MTP surface now exists; remaining work is P6b model-load + Q4-vs-Q4 bench evidence, not a cherry-pick task. |
| **Qwen3.5-122B-A10B (architect)** | GDN hybrid | `unsloth/Qwen3.5-122B-A10B-MTP-GGUF` | **DEAD — do not pursue** | `autopilot/program.md:325`: MTP-1 already measured **0.56×** (net slowdown); 75% Delta-Net recurrent layers don't batch. Architecture, NOT NUMA (architect is already single-instance serial). |
| **Qwen3.5-27B (DENSE? no — HYBRID; on disk)** | SSM-Dense hybrid | `unsloth/Qwen3.5-27B-MTP-GGUF` | **DEAD — hybrid trap** | same Delta-Net wall; closed NOT VIABLE in `mtp-speculative-decoding.md`. (User listed it as dense — it is not.) |
| **Qwen3-Next-80B (ingest)** | SSM-MoE hybrid | native MTP (GPU/vLLM only) | **not viable on CPU** | only GGUF attempt (quivent) = net-negative 0.43×; verification wall holds |
| **gemma-4-26B-A4B (worker_general)** | MoE A4B | mainline/v6 native gemma4 MTP (#23398 lineage) | **not stale on head; v6-native now** | our head = official; production now uses the consolidated v6 native MTP path, not the separate ik fork. Cheap open check remains `draft_max` / `--spec-draft-n-max` 2→3→4 sweep under operator-approved bench conditions. |

## ngram speculation — **RETRACTED 2026-07-31 · DO NOT DEPLOY**

> ### ⛔ EVERYTHING IN THIS SECTION IS WITHDRAWN
>
> The `2.80×` / `1.50×` / `+15%` figures below are a **measurement artifact**, not a lever.
> Each cell launched ONE server and sent the **SAME prompt** r times at `temperature=0.3, seed=42`.
> Run 1 generates answer X; the server retains X in the slot KV; run 2 hits the prompt cache
> (`prompt eval = 4 tokens`) and `ngram-mod` — which drafts by **matching text already in context** —
> copies its own previous answer verbatim. Mean accepted draft length `3.58 → 15.88`; acceptance → `1.000`.
>
> **The control was in the data the whole time:** sorting all 68 cell logs by run2÷run1, *every* cell
> inflated >1.15× is an ngram arm, and *all 25* `draft-mtp`-only/`none` cells sit flat at 0.92–1.08×.
> `draft-mtp` drafts from weights, so a warm context cannot help it.
>
> **Corrected numbers.** Run-1-only, 16 model×depth×device cells: **−17.4% to +2.7%, centred on zero**
> (35B CPU @14k: 24.85 vs 24.86). Independent re-run with **3 DISTINCT prompts per rep**
> (`/mnt/raid0/llm/tmp/ngramfix_results.txt`): composed-vs-`draft-mtp` **−4.2% to +1.3%**;
> `ngram-mod` **alone costs 23–31%**.
>
> **Still true:** `ngram-mod` needs no draft model, so it remains the only speculative path
> *available* to `ingest_long_context`. It simply does not buy anything measurable.
>
> Retraction of record: research `84067a6e` →
> `data/numa_placement/20260730-P-BENCH-PLACEMENT-1/RETRACTION-ngram-20260730.md`.
> Master index row **N26**. Prompt screening was necessary but **not sufficient** — the prompts were
> clean real text at 6–17% repeated 5-grams; the contamination came from the **generation**.
>
> The original text is retained below **unedited**, as the record of what was believed and why.

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
> Root-cause context and attestation: [numa-placement-defect-20260730.md](numa-placement-defect-20260730.md)
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

## What is and is NOT runtime-switchable — read from source 2026-07-31 (v8, `67a433bf4`)

Operator question, answered from the frozen production source rather than from a benchmark.

**`--spec-type` is LAUNCH-ONLY.** Which drafters are active is fixed at server start
(`common/arg.cpp:3935`). **Autopilot cannot switch drafter per request.**

**⚠ CORRECTION to the working assumption — the per-request draft-budget fields are COMPILED OUT.**
It is easy to read `tools/server/server-schema.cpp` and conclude the budget is per-request: the file
*does* register `speculative.n_max` (line 208), `speculative.n_min` (212), `speculative.p_min` (216),
`speculative.type` (220) and `speculative.ngram_size_n/size_m/min_hits` (226/229/232). **But the
entire block is inside `#if 0` opened at line 206 and closed at line 234**, under the upstream
comment at line 205:

```
// TODO: to keep things simple, we disable speculative parameter adjustments for now
```

So on the production binary **there is no per-request speculative surface at all**. The
`speculative.n_max` keys visible in `tools/server/README.md` (768-820, 917-967, 982-1032) are
**`generation_settings` echoes of the launch defaults**, not accepted request fields — which is
precisely how this gets misread. A grep of `tools/server/*.cpp` confirms no other per-request parsing
path exists.

**Consequences (all four matter for autopilot design):**

1. Autopilot **cannot** dial the draft budget per call on v8, and **cannot** send `n_max: 0` to skip
   drafting for one request. Enabling that is a **kernel change** — i.e. a new production version
   built and validated per CLAUDE.md's four-step workflow, never a patch to the frozen tree.
2. Even if the fields were live, `n_max: 0` would kill **both** arms together. **ngram cannot be
   disabled selectively** — selective ngram requires **separate server instances**.
3. The composed recipe's **~1.6 % cost is therefore paid on every drafted request, unconditionally**.
   Its whole justification was the repetitive-context upside — and that upside is **retracted** (see
   the ⛔ section above). Nothing is left on the benefit side of that trade.
4. Any future "per-request drafting policy" design must budget for a kernel change *first*, not
   assume a config knob.

**Not empirically probed.** No request was sent — three measurement tracks were live on the host.
The claim rests on source at the exact lines cited; SW-2 below closes the loop cheaply when a lane
is free.

## Outstanding Tasks (priority order)

- [x] **T1 — gate-bench gemma-4-31B DENSE: DONE 2026-06-22 (host quiesced).** Result **~1.84× at draft_max=3** (see Results below). Speed win confirmed + survives noise; **corrects the prior single-run ~2.98× to ~1.84×**. Remaining for Tier-B promotion: multi-prompt reps + the quality (Leviathan byte-exact) suite + acceptance-rate capture. Operator decision: promote `gemma4_31b_q4km_mtp` only after the quality pass.
- [x] **NG0 — measure `ngram-mod,draft-mtp` against `draft-mtp` on all four production CPU models**, on realistic text after discarding a synthetic-filler first pass ✅ 2026-07-30
- [x] **NG1 — ~~deploy `ngram-mod,draft-mtp` on `frontdoor` + `coder_escalation`~~ CANCELLED ✅ 2026-07-31.** The 2.80×/1.50× were the self-copy artifact; re-measured gain is **−1.9% / −1.5%** on this model. **Do not deploy.** Original text: Needs: a quality/bit-exactness pass (speculation must not change output — pair speed with a correctness check), the depth at which the gain is quoted, and the reload gates. **Deploy is not self-authorising** — the reload belongs to the session that owns the inference.
- [x] **NG2 — ~~deploy `ngram-mod` on `ingest_long_context`~~ CANCELLED ✅ 2026-07-31** (artifact; +3.3% at r=1 is inside noise). The registry note that `acceleration: {type: none}` means *no draft-model path* rather than *no speculation possible* is still worth making. Original text: `1.15×`, `.812` acceptance, and it is **the only speculation an SSM hybrid with no draft-model path can have**. Update the registry's `acceleration: {type: none}` so it stops reading as "this role cannot be accelerated".
- [x] **NG3 — do NOT deploy ngram ANYWHERE ✅ 2026-07-31** (generalised from two roles to all roles by the retraction). Original text:, and record why in the registry rather than leaving it to be rediscovered: measured no gain, consistent with the acceptance-headroom principle (`.754` and `.650` incumbents). *(This is a decline, filed as a task so the next reader does not re-run it.)*
- [x] **NG4 — GPU sweep landed and was RE-SCORED run-1-only ✅ 2026-07-31.** 27B GPU: `draft-mtp` 47.79/40.46/39.20/31.97 vs `+ngram` 47.80/40.36/39.61/31.98 across 2k/8k/16k/32k — a wash. 122B IQ2 @16.5k: **−17.4%**. Original text: ngram **is** supported on GPU, and the v8 HIP build works (`ROCm0: AMD Instinct MI210`, version `10107` / `67a433bf4` — the same SHA production serves on CPU). The sweep was running at session close and is **NOT reportable**; do not quote a GPU ngram figure until it lands.
- [x] **SW-1 — answer the operator's runtime-switchability question from source** ✅ 2026-07-31 — `--spec-type` is launch-only; the per-request `speculative.*` fields exist in `server-schema.cpp` but sit inside `#if 0` (206-234) and are **not compiled in**. See the section above.
- [ ] **SW-2 — confirm SW-1 against a live server** when a lane is free and no protected bench region is held: POST a completion carrying `speculative.n_max` and verify the server neither honours nor rejects it (unknown fields are dropped). Cheap; closes a source-only claim. **Do not run this against a warm server on a repeated prompt** — that is the exact shape that produced the retracted ngram result twice.
- [ ] **SW-3 — decide whether a per-request draft-budget surface is worth carrying into v9.** Enabling the `#if 0` block is a kernel change, so it must ride a full experimental → validate → new-production cycle, never a patch to the frozen v8 tree. Inputs: (a) with ngram retracted, is there any remaining request class where skipping the draft pays? (b) does the ~1.6 % unconditional cost of the composed recipe justify the change on its own? File the answer here even if it is "no", so the question is not rediscovered.
- [ ] **SW-4 — record in the registry that composed spec-dec is launch-fixed**, so a future reader does not design an autopilot policy around a knob that does not exist. Pairs with the NG3 decline note.
- [x] **SR-1 — production was NOT running the operator's recipe; the LEAN registry is the file that decides** ✅ 2026-07-31 (epyc-orchestrator `6390b871`). The stack compiles from `epyc-orchestrator/orchestration/model_registry.yaml`, **not** the research registry — an earlier audit fixed the research copy, which changed nothing about what production launches. Since `2370025f` (2026-07-19) the launcher emitted `--spec-type draft-mtp` **alone**, because that commit reverted `spec_type` and moved the composed value into a sidecar key `ngram_candidate_spec_type` that nothing read. The lean registry still carried `draft-mtp` on six entries, both sidecars, and a stray **`spec_type: ngram-simple`** on `qwen36_q8_0` — a fourth, undiscussed variant on the model backing **both** frontdoor and coder_escalation. Now set to the composed value on all affected entries; sidecar retired; `stack_priors.yaml` + `model_descriptors.yaml` regenerated.
- [x] **SR-2 — the naive fix would have been WORSE than the bug** ✅ 2026-07-31 (epyc-orchestrator `2874ed73`). `stack_priors.py` tested `spec_type_prior == "draft-mtp"` by **exact equality**, so committing the composed value without this fix would have failed the test and fallen through to the **DISABLED** speculation branch — launching frontdoor and architect_general with *no speculation at all*. Replaced with a membership test. **Verified after the fix**: the launcher emits `ngram-mod,draft-mtp` for frontdoor / worker_general / architect_general and `enabled=False` for ingest_long_context. `stack_change_pipeline check`: **42 errors → 2**, both live-process drift (orchestrator API :8000, whisper :9000), neither config.
- [x] **SR-3 — `--spec-draft-n-max` is a SOFT BUDGET, not a cap, under a composed recipe** ✅ 2026-07-31 — mean accepted run length measured at **2.36–2.67 with `n_max=2`**. `ngram_mod_n_max` is a **separate, independent knob** and has not been touched. Any policy written on the assumption that `n_max` bounds the draft is wrong under composition.
- [x] **SR-4 — acceptance-rate dilution under a composed recipe is EXPECTED, not a fault** ✅ 2026-07-31 — `draft_n` counts proposals from **both** proposers, so the reported acceptance rate is mechanically lower than a `draft-mtp`-alone run of the same model. An acceptance gate calibrated on draft-mtp-alone numbers will wrongly reject a correctly-configured composed setup. Any such gate must declare the recipe it was calibrated against.
- [ ] **SR-5 — ⚠ RESOLVE THE NG-vs-OPERATOR CONTRADICTION ON THE RECORD.** NG1/NG2/NG3 above read "do NOT deploy ngram ANYWHERE", generalised from the retracted self-copy artifact. The **operator's standing decision is the composed recipe `ngram-mod,draft-mtp`**, and that is what is now committed and launching. Both statements are currently in the tree and a future reader cannot tell which governs. The operator decision governs; NG1–NG3 concerned `ngram-mod` *alone* and a contaminated measurement of it. Write the reconciliation into the `speculative_decoding_policy` block so the retraction cannot be read as overriding a live operator decision.
- [ ] **SR-6 — confirm the Qwen3.6-35B `n_max` 4 → 3 change at higher n before editing the registry.** Draft-max sweep (half A, composed recipe, production sampling) measured **+9.8 % on 3/3 paired prompts, acceptance 0.470 → 0.538**. That is 3 prompts; it is directional, not decisive. gemma **keep `n_max=2`**; 122B **keep 4**; `n_max` 6 and 8 are clearly bad everywhere. **Do not edit the registry on n=3.**
- [ ] **SR-7 — explain why the 122B VIOLATES acceptance-falls-with-n_max** (acceptance *rises* at `n_max=6`). Working hypothesis: a composed recipe shifts the branch mix between proposers as the budget grows, so the single-proposer monotonicity assumption does not survive composition. This matters because that assumption is load-bearing for any autopilot search over `n_max`.
- [ ] **NG5 — carry corpus + repeated-5-gram fraction on every ngram claim — STILL OPEN, and now known INSUFFICIENT.** These prompts passed screening at 6–17% repeated 5-grams and were still contaminated, because the copied text was the model's own *generation*. The rule must extend to: never replicate a context-reading drafter against a live server on a repeated prompt, and always run a non-context control arm. Original text:, in this handoff, the registry, and any index row that quotes one. Synthetic filler inflated the same measurement to a nearly meaningless `2.52×`.

## Results — gemma-4-31B dense MTP gate-bench (2026-06-22)

**Protocol** (clean directional measurement, NOT a full canonical gate): host quiesced (full stack stopped via `orchestrator_stack.py stop --all`); ik_llama.cpp `production-gemma4-mtp` `llama-server` + `/completion`; target `gemma-4-31B-it-Q4_K_M` + official `gemma-4-31B-it-assistant-Q8_0`; `taskset -c 0-95 numactl --interleave=all`, `-t 96 -fa 1 --no-mmap -c 16384 -ub 512 -ctk q8_0 -ctv q8_0`, OMP stack + `KMP_BLOCKTIME=10`; `n_predict=128, temp=0, seed=42, cache_prompt=false`; 1 warmup + 2 measured reps; single prompt.

| config | t/s (r1, r2) | median | speedup |
|---|---|---|---|
| baseline (no MTP) | 9.17 / 9.11 | 9.14 | 1.00× |
| MTP draft-max 2 | 15.95 / 16.00 | 15.98 | 1.75× |
| **MTP draft-max 3** | 16.83 / 16.75 | **16.79** | **1.84×** |
| MTP draft-max 4 | 16.02 / 16.38 | 16.20 | 1.77× |

**Findings**: dense gemma-4-31B CPU MTP gives a **real ~1.84×** (draft_max=3 optimal; 3 > 4 > 2) — confirming the dense thesis vs MoE's ~1.06×. The prior `gemma4-mtp-drafter-evaluation` 2.98× (7.05→21.02, single-run) does **not** reproduce on a clean host: clean baseline is higher (9.14 vs 7.05) and MTP lower (16.8 vs 21.0), so realized speedup is ~1.84×, not ~3×. Acceptance rate was NOT captured (the `/completion` timings JSON didn't expose draft_n/accepted under the probed keys — needs the server spec-stats path or `llama-speculative`, which currently SIGABRTs on this fork's gemma4-MTP path → use server). Numbers are a clean measurement but single-prompt/r=2 — a Tier-B gate still needs multi-prompt reps + quality byte-exactness.

**Implication for the port (T2)**: a ~1.84× dense win justifies finishing the #22673 Qwen MTP port to test dense **Qwen3.5-9B** (T3) — but it does **not** rescue the MoE cases (Qwen3.6-A3B), where the wall is expert-verification overhead, not draft quality.

### Hard-T2 verification + quality (2026-06-22, host quiesced)

Re-ran on two substantive checkable tasks (n=384, temp=0, seed=42), capturing output text + diffing baseline vs MTP:

| task | baseline t/s | MTP (dm=3) t/s | speedup | output correct? | MTP==baseline? |
|---|---|---|---|---|---|
| P1 Manacher's algorithm (Python) | 10.21 | **26.01** | **2.55×** | ✅ valid O(n) Manacher's | ✗ differs (valid alt impl) |
| P2 primes<100 + sum | 10.24 | **32.68** | **3.19×** | ✅ exact (25 primes, sum 1060) | ✅ byte-identical |

**The 16.8 t/s was not variance — on real structured/code output MTP is *faster* (26–32 t/s), because predictable tokens (code, `2, 3, 5, 7…`) draft at very high acceptance** (generic prose accepts less, hence the lower 1.84× there). Baseline dense 31B ≈ 10 t/s; MTP 26–32 t/s.

**Quality / losslessness (important correction)**: MTP output is **correct and sensible** (P2 exact answer; P1 valid Manacher's), but it is **distribution-lossless, NOT byte-exact greedy**. P1 diverged from sequential baseline at a near-tie comment token (“symmetry”→“mirroring”) then produced a different-but-equally-valid implementation — expected because the batched verification forward pass has different FP rounding than token-by-token decode, flipping greedy near-ties. This **supersedes the prior `gemma4-mtp-drafter-evaluation` “byte-exact under Leviathan verifier” claim** (too strong). Acceptable for chat/architect roles (output valid); do not rely on bit-determinism.

### Promotion decision (DATA-DRIVEN, 2026-06-22): do NOT promote gemma-4-31B — Pareto-dominated
We already HAVE the quality benchmarks (`epyc-inference-research/benchmarks/results/reviews/summary.csv`), and MTP is distribution-lossless so the MTP-variant's measured score is the deploy-relevant number. Verdict: gemma-4-31B wins **no** quality×speed frontier vs current incumbents:

| | gemma-4-31B MTP | Qwen3.5-122B (architect) | Qwen3.6-35B (frontdoor) | gemma-4-26B-A4B (worker) |
|---|---|---|---|---|
| quality | 90% (164/183) | 93% (196/210) | 94% | 90% + 96% tool |
| agentic | 23/30 | 30/30 | — | — |
| long_context | none measured | 24/27 | 27/27 | — |
| speed (MTP) | 26–32 t/s | 12.3 | 24.3 | 44.7 |

- vs **architect** Qwen3.5-122B (93%, 12.3 t/s, no-MTP — GDN hybrid): **NOT domination — a trade-off.** gemma-4-31B is **2–2.6× FASTER** (26–32 vs 12.3) but −3pp overall, **agentic 23 vs 30**, and **no long-context data**. For the accuracy-critical, long-context architect role the 122B's quality+long-context win **by default**; but if architect *throughput* ever becomes the bottleneck, a "fast architect" swap is a legitimate operator trade (gate: measure gemma-4-31B long-context first + accept the agentic gap).
- vs **frontdoor/coder** Qwen3.6-35B (94%, 24.3 t/s): roughly iso-speed, −4pp quality. No win.
- vs **worker** gemma-4-26B-A4B (90%, MTP): **THIS is the real domination.** Same 90% quality, but the A4B MoE is **structurally faster** — it reads ~3.8B active params/token vs gemma-4-31B's 31B dense, so on BW-bound CPU it wins the quality×speed frontier (~44.7 vs 26–32 t/s) regardless of exact numbers. The smaller gemma-4 *MoE* dominates the bigger gemma-4 *dense*.

**Conclusion (corrected)**: gemma-4-31B is **Pareto-dominated specifically by the gemma-4-26B-A4B MoE worker** (equal quality, structurally faster) — NOT by the 122B, which it is 2–2.6× faster than. So it has no *general-purpose* niche. The one open door is a deliberate "fast architect" quality↓/speed↑ trade vs the 122B (operator's call; needs a long-context measurement first). The MTP work's lasting value is **validating dense-CPU-MTP (2.5–3.2×)**, justifying the Qwen3.5-9B dense path (T3). (Sources: progress 2026-05-06/08; summary.csv:18 gemma-4-31B-MTP, :19 gemma-4-26B-A4B, :131 Qwen3.5-122B. The old summary.csv 4.7 t/s for gemma-4-31B-MTP was stale/contended — superseded by the clean 26–32 t/s, 2026-06-22.)

### ⚠ Eval-resolution caveat behind the "A4B ties dense-31B" finding (2026-06-22)

The promotion decision rests on "gemma-4-31B (31B dense) and gemma-4-26B-A4B (~3.8B active MoE) both score ~90%." Operator flagged this as suspicious ("how can an A4B *match* the dense 31B of its own family?"). Investigated publicly — **verdict: benchmark saturation, NOT a dense-Q4 quantization penalty**:

- **Quantization ruled out**: public dense-Q4 gemma-4-31B evals (e.g. SuperGemma-4-31B dense-Q4 ≈ 92%) land *above* our 90%, so Q4_K_M is not crippling the dense model. The dense 31B is genuinely the stronger model: ~1–3 pp better on standard suites and **~8–10 pp better on frontier/agentic suites our bench does not contain**.
- **Root cause = our quality suites are saturated** (90–94% band, near ceiling). When two models both sit near a suite's ceiling, the suite **cannot resolve** their true gap — so a structurally-stronger dense 31B and a cheaper A4B MoE *appear* tied. The tie is a **resolution artifact of the instrument**, not real quality parity (same failure family as [[feedback_per_suite_gate_resolution_artifact]] — quantized scores hiding real differences).
- **Consequence for THIS decision**: the Pareto-domination call (worker A4B over dense 31B) is **safe for the worker/general role** (where ~90% suffices and speed dominates), but it should **not** be read as "A4B = 31B in capability." For accuracy-critical / frontier-agentic roles the dense 31B's real edge would show — which is exactly why the "fast architect" door above stays open pending a *harder* eval.
- **Operator-review candidate (NOT acted on here — eval trust boundary is human-amendment-only)**: our review suite needs a frontier/harder tier to resolve top-of-stack models; this is the eval-tower **EV-9 / DRACO** concern (intake-713). **Now recorded in the owning handoff** — [`eval-tower-verification.md`](eval-tower-verification.md) "Research Intake Update — 2026-06-23 / EV-9 saturation: empirical instance" — as a standing-audit + frontier-tier candidate. Scoring untouched.
- [x] **T2 (WS5 port) — finish the Qwen MTP kernel port** in `llama.cpp-experimental` (historical branch `experimental-v7-candidate` at `46f876c12`, now superseded for promotion by `experimental-v7-refresh-20260716`). The experimental tree already contains the Qwen/native MTP surface (`draft-mtp`, `LLAMA_CONTEXT_TYPE_MTP`, Qwen graph mapping, and `nextn_predict_layers` conversion output), and the CPU-only build + help surface were verified on `llama-server` and `llama-speculative`. **T4/T5 and the operator-gated model-load / gate benches remain open.** **Full context + checkpoint details: [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md).** ✅ 2026-07-11
- [x] **T3 — Qwen3.5-9B dense MTP: FUNCTIONALLY VERIFIED 2026-06-22; v7 MI210 task-class/broad slice added 2026-07-17.** Initial closure used a fresh-upstream build because the #22673 cherry-pick into our fork was infeasible: `unsloth/Qwen3.5-9B-MTP-GGUF` Q4_K_M (5.47 GB), `llama.cpp-experimental/build-upstream` (`origin/master`, branch `upstream-mtp-verify`), baseline `14.90` → MTP (`--spec-type draft-mtp --spec-draft-n-max 3`) `29.30 t/s` = `1.97x`, `87%` draft accept (`184/211`), correct output. Full detail + reproduce cmd: [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md) ✅ section. Experimental-v7 HIP evidence used the local `build-hip/bin` server with pinned `LD_LIBRARY_PATH`, q8 KV, reasoning off, and fresh sequential servers: short exact tasks passed `5/6` on both no-spec and native MTP, but no-spec was faster (`124.77` vs `109.28 t/s`, MTP accepted `30/30`); long repetitive structured output passed on both arms and MTP was faster (`140.50` vs `95.08 t/s`, accepted `682/682`); broader `default+expanded` slice passed `13/18` on no-spec, `draft-mtp`, and `ngram-mod,draft-mtp`, with MTP improving mean decode `105.88 -> 114.09 t/s` and combined ngram→MTP effectively tied at `113.24 t/s`. Evidence: `/mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-quality-20260717T202549Z/summary.json`, `/mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-longoutput-20260717T202636Z/summary.json`, and `/mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-broad-20260717T212947Z/summary.json`. **Serving implication:** native MTP is task-class dependent; use no-spec for tiny verifier answers and MTP for longer structured/repetitive generation. The broad slice rejects a general frontdoor/worker role claim.
- [x] **T3b — record experimental-v7 MI210 Qwen3.5-9B MTP task-class gate** in root progress plus the research admission docs/registry; classify no-spec as the short-completion lane and native MTP as the long repetitive/structured-output candidate before the broader T3c slice. ✅ 2026-07-17
- [x] **T3c — broader Qwen3.5-9B MTP role/niche slice ✅ 2026-07-17**: realistic MI210 server pass across the `default+expanded` deterministic task set compared no-spec, native `draft-mtp`, and combined `ngram-mod,draft-mtp`. All arms passed `13/18` with the same failed task IDs; native MTP improves throughput but does not change quality. This closes the "broader role-quality/niche" open question as a structured-output niche, not a broad role promotion.
- [ ] **T4 (after T2 binary, low EV) — gate-bench Qwen3.6-35B-A3B** (Block C) for frontdoor/coder; mind the Q8(prod)-vs-Q4(MTP-GGUF) quant-parity caveat + MoE-on-CPU skepticism. **2026-07-17 artifact audit:** no Qwen3.6-35B-A3B Q4 or Q4-MTP GGUF is present under `/mnt/raid0/llm/models` or the old LM Studio cache; only Q8 frontdoor files and a stale HF metadata stub remain. Do not burn a quiet window on a Q8-vs-Q4 mismatch or call same-Q8 diagnostics the T4 gate. T4 is artifact-blocked until a matching Q4 no-spec / Q4-MTP pair is available, or explicitly re-scoped to a same-quant Q8 diagnostic.
- [x] **T5 — gemma-4-26B-A4B `draft_max` 2→3→4 worker sweep ✅ 2026-07-17; 1024-token CPU rerun ✅ 2026-07-18**: production-shaped CPU worker lane on experimental v7 (`ngram-mod,draft-mtp`, assistant v6 Q8 draft, q8 KV, reasoning off, 8K context, 512-token request) confirmed the live `draft_max=2` default. Evidence: `/mnt/raid0/llm/tmp/t5-gemma-worker-draft-depth-20260717T213641Z/summary.json`. Decode: depth 2 `87.76 t/s` (`492/666` accepted), depth 3 `76.38 t/s` (`492/812` accepted), depth 4 `84.40 t/s` (`494/734` accepted). Fresh 1024-token observation under `epyc-inference-research/data/t5_gemma_worker_draft_depth/20260718T175656Z_cpu_8k_1024tok/summary.json` used experimental `llama-server` `10089 (04753078f)`, `--device none -ngl 0 --spec-draft-device none --spec-draft-ngl 0`, and completed all depths: depth 2 `105.20 t/s` (`996/1173` accepted), depth 3 `93.91 t/s` (`996/1316` accepted), depth 4 `101.00 t/s` (`998/1242` accepted). Keep worker `draft_max=2`; deeper drafting over-drafts without more accepted tokens on this lane.
- [x] **T6 — branch-authority wording sync ✅ 2026-07-19**: future benches now point to the refreshed experimental v7 branch (`experimental-v7-refresh-20260716`) or a successor branch freshly started from current production. Old `experimental-v7-candidate` references in this handoff are historical checkpoints only, not authoritative promotion instructions.

## Dependency graph
- T1 is closed as a directional dense-CPU-MTP win; promotion still depends on operator-approved quality/multi-prompt evidence.
- T3 is closed as a functional dense-Qwen MTP verification and now has experimental-v7 MI210 task-class evidence. The upstream-master multiplier/path-health evidence remains valid but its absolute t/s is not production-comparable; the v7 A/B is deploy-shape evidence, not a broad role promotion.
- T4 is now blocked by the `qwen-mtp-llamacpp-port.md` P6b model-load gate, a missing matching Q4 artifact pair, and operator bench approval on the experimental `draft-mtp` binary; compare Q4+MTP against Q4 no-MTP, not against the Q8 production role. A same-Q8 no-spec/MTP diagnostic may still be useful for Qwen3.6 MTP mechanics, but it is not the quant-parity T4 gate unless this handoff is explicitly re-scoped.
- T5 is closed: worker `draft_max=2` remains the measured default; 3/4 did not improve accepted tokens or throughput on the production-shaped 8K worker lane, including the 2026-07-18 1024-token CPU-only rerun.
- The historical #22673 conflict/cherry-pick analysis lives in [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md). As of the 2026-07-11 checkpoint, `/mnt/raid0/llm/llama.cpp-experimental` branch `experimental-v7-candidate` at `46f876c12` already contained the Qwen/native MTP surface and CPU-only help-surface verification; that checkpoint is superseded for promotion by `experimental-v7-refresh-20260716`, and the remaining parent-handoff work is model-load/bench evidence.

## Cross-cutting concerns
- **CPU+MoE is the binding question**: every upstream MTP/EAGLE speedup is GPU; MoE shows ≤1.06× even on GPU (expert-union verification overhead). Dense is where CPU MTP can win; T1/T3 now provide the dense proof-points, while T4 remains the low-EV MoE confirmation bench. Any deploy decision still needs protocol-cited throughput/acceptance and quality evidence.
- **MTP parallelism must be verified per runtime**: the June ik path asserted on `-np>1`; v6 native MTP must still be checked per role because speculative decoding can trade off against 4×-quarter concurrent splits. Confirm per role before deploy.
- **NEVER touch production `/mnt/raid0/llm/llama.cpp`** — all port work in `llama.cpp-experimental` (verify_llama_cpp.sh enforces). Promotion means a new production version after positive operator bench + quality pass, never patching v6 in place.
- Quant parity: Qwen3.6 prod = Q8; MTP-GGUF = Q4 → compare C1(Q4+MTP) vs C0(Q4 no-MTP), not vs Q8 prod.
- **Draft-head is a small BW slice** (corroborated by FR-Spec vocab-trim, intake-740): trimming the draft LM-head −85% in kernel time yields only +1-3% end-to-end on bandwidth-bound decode — reinforcing that expert-verification overhead, not draft quality, is the CPU wall.

## Watch-items (deferred)
- **EAGLE-3** (mainline PR #18039) — deferred to the **MI210 GPU (~July 2026)** per operator; our fork's EAGLE3 is a stub. **Trigger now due (2026-07-02): the MI210 has landed** — and DeepSpec (intake-737) is an MIT EAGLE-3 training/eval framework, so this watch is actionable once GPU-side spec-dec work opens.
- **DSpark semi-AR draft head** (intake-738) — candidate future MTP-drafter alternative; deferred like EAGLE-3. Needs DeepSpec-pipeline training (MI210) + a GGUF port, then **measure α vs our native MTP before any investment** (per `feedback_measure_alpha_before_specdec_investment`); note gemma4 native MTP is already ~76.9% saturated → low headroom.
- **DFlash O(1)-drafting (intake-158 / deep-dive `dflash-dart-diffusion-speculation.md`) — promoted from "not-viable comparison" to explicit MI210 candidate (2026-07-03 intake sweep)**: DFlash was previously cited here only as the "same deployment wall" (CPU/GGUF-blocked). That wall was a *CPU* wall — on the MI210 the recurrent/diffusion draft path runs on GPU (parallel scan; verification bottleneck disappears — the same reason `gpu-acceleration-path.md` revives DFlash/DDTree). Two forks: (a) the deep-dive's Action-A O(1)-drafting port, and (b) the lucebox `llama.cpp-dflash-ggml` tree HIP re-scoped for gfx90a (currently CUDA-pinned). **Still α-gated**: measure acceptance vs native MTP first (G0 log read gives the baseline for free); our own DFlash C++ forward pass is already verified correct to <0.01, so the algorithm was never the blocker. [unverified] that the reference kernels build on ROCm.
- **Qwen3-Next MTP** — re-measure trigger only if a *merged* `qwen3next` MTP path with a positive CPU speedup appears.

## Operator bench commands

See WS4 prep for the historical June commands. **Block A (gemma-4-31B dense)** was run on `/mnt/raid0/llm/ik_llama.cpp/build/bin/llama-speculative` (branch `production-gemma4-mtp`) using ik-era flags (`-mtp --spec-type mtp --draft-max`). For July+ measurements, translate to the v6/native surface (`--spec-type draft-mtp`, `--spec-draft-n-max`) on `production-consolidated-v6` or the refreshed `llama.cpp-experimental` v7 branch (`experimental-v7-refresh-20260716`, or a successor branch fresh-pulled from current production), preserve the same operator-approved quiescing / CPU pinning / seed protocol, and record protocol IDs per `MEASUREMENT.md`. Blocks B/C use the experimental `draft-mtp` binary after download. (Full blocks were produced in the session WS4 report.)

## Operator gate packet - prepared 2026-07-11

This packet packages the remaining T4/T5/Hy3 gates without running inference. It must not be used to patch or rebuild frozen production `/mnt/raid0/llm/llama.cpp`; any kernel/model-load work happens in `/mnt/raid0/llm/llama.cpp-experimental` or a deliberately disposable side tree.

- **Shared measurement boundary:** every decision-gating number needs `(metric, protocol-id, n/reps, date, attestation ref)` per `MEASUREMENT.md`; all ad hoc log reads are observations. Pause/quiet concurrent inference before live benches, capture host covariates, and compare like-for-like quant/runtime arms.
- **T4 Qwen3.6-35B-A3B MTP gate:** run only after the `qwen-mtp-llamacpp-port.md` P6b model-load gate passes on the experimental `draft-mtp` binary and a matching Q4 no-spec / Q4-MTP artifact pair is present. Compare Q4+MTP against Q4 no-MTP, not against the Q8 production frontdoor/coder role. Required evidence fields: pinned experimental commit, GGUF path + quant, `--spec-type draft-mtp`, `--spec-draft-n-max`, acceptance counters, t/s, correctness probe, host covariates, and protocol id. Baseline/no-spec is the attribution control; the deployment answer must come from the fastest quality-clean realistic serving lane.
- **T5 gemma-4-26B-A4B draft-depth sweep:** first collect the zero-inference live acceptance baseline with `cd /mnt/raid0/llm/epyc-orchestrator && python3 scripts/benchmark/mtp_acceptance_report.py --no-write-defaults --no-strict`. The live sweep itself is operator-bench work: same worker model, same prompt set, same stack snapshot, depths `2`, `3`, and `4`, and the same host-quiesce protocol. `scripts/benchmark/md_self_draft_ab.py --dry-run` remains useful only to preview same-file `-md` vs embedded self-draft command shape; it is not a substitute for the T5 depth sweep.
- **Hy3 confirmatory CPU-MTP closure:** follow `research/deep-dives/2026-07-11-hy3-hunyuan-v3-moe-mtp-assessment.md` section 7: download **IQ2_M only**, pin `satindergrewal/llama.cpp@hy3-mtp`, run an ungated greedy arm (`--spec-draft-p-min 0`) against a no-MTP baseline, and add a short correctness probe. Predicted result is net-neutral on EPYC CPU; a separate plain architect quality bench is a different operator decision.
- [x] T5 zero-inference acceptance-log validation: `mtp_acceptance_report.py --no-write-defaults --no-strict` reports no failed MTP roles, acceptance evidence for `architect_general`, `frontdoor`, and `worker_general`, and aggregate token acceptance `0.7183` (observation-only; not a depth-sweep bench). ✅ 2026-07-11
- [x] Command-shape dry-run validation: `md_self_draft_ab.py --dry-run` prints same-file `-md` vs embedded self-draft commands and creates no output directory until a live run is explicitly approved. ✅ 2026-07-11

## Research context (intake)

| Intake | Item | Verdict |
|---|---|---|
| intake-721 | unsloth/Qwen3.6-35B-A3B-MTP-GGUF | worth_investigating |
| intake-722 | unsloth/Qwen3.5-122B-A10B-MTP-GGUF | not_applicable (hybrid wall) |
| intake-723 | unsloth/Qwen3.5-9B-MTP-GGUF | worth_investigating |
| intake-724 | google/gemma-4-31B-it-assistant | adopt_component (on disk) |
| intake-725 | llama.cpp/ik_llama MTP+EAGLE3 support (PRs #22673/#22400/#23398/#18039, ik #1744) | adopt_patterns |
| intake-737 | DeepSeek DeepSpec — MIT draft-model train/eval framework (DSpark/DFlash/EAGLE-3; Qwen3 + gemma-4-12B-it ckpts) | worth_investigating (checkpoints) / n/a (8-GPU framework, no CPU/GGUF path) |
| intake-738 | DSpark semi-AR drafter (parallel backbone + 1-token correction head) | adopt_patterns — transferable draft head (needs training + GGUF port); scheduler CPU-inert (→ moe-spec); vendor-unreproduced |
| intake-740 | FR-Spec draft-vocab trim for native MTP (llama.cpp #25187, `avifenesh@047bfa508`) | worth_investigating — lossless@temp0, −85% draft-head kernel → +1-3% e2e; impl → qwen-mtp-llamacpp-port.md P7 |
| intake-742 | Graft — training-free prune-then-graft draft tree (arXiv 2605.20104) | adopt_patterns (catalog → moe-spec); EAGLE-3-based + GPU adjacency |

## Reporting instructions
After any task: update the checkbox here + record measured numbers (with protocol-id per MEASUREMENT.md) in the owning artifact (registry entry `gemma4_31b_q4km_mtp` for T1; this handoff for T2 port status). Any promotion requires a fresh experimental candidate, positive operator bench, and quality pass — never auto-promote and never patch frozen production in place.

## Key file locations
- Historical Qwen/native MTP checkpoint: `/mnt/raid0/llm/llama.cpp-experimental` `experimental-v7-candidate` at `46f876c12`; P6b model-load/gate bench remains operator-gated. Current promotion authority is the refreshed `experimental-v7-refresh-20260716` line tracked in [v7-promotion.md](v7-promotion.md). Historical `feature/mtp-qwen36-port` / #22673 cherry-pick analysis is preserved in [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md).
- gemma MTP runtime: current production uses `/mnt/raid0/llm/llama.cpp` `production-consolidated-v7` native MTP; `/mnt/raid0/llm/ik_llama.cpp` `production-gemma4-mtp` is historical/reproduction-only
- Models on disk: `/mnt/raid0/llm/models/gemma-4-31B-it-Q4_K_M.gguf` (+ `-assistant-Q8_0.gguf`); verified Qwen MTP artifact `/mnt/raid0/llm/models/Qwen3.5-9B-MTP-GGUF/Qwen3.5-9B-Q4_K_M.gguf` (older non-MTP LM Studio Qwen3.5-9B quants also exist, but are not the T3 MTP artifact)
- Registry entries: `gemma4_31b_q4km_mtp` (research registry, Tier B); worker_general (lean registry)
- Read-only refs: `autopilot/program.md:325` (Qwen3.5 hybrid exhausted), `scripts/session/verify_llama_cpp.sh`

## Research Intake Update — 2026-07-02

### New Related Research
- **[intake-751 / intake-752] "Nemotron-Labs-TwoTower: Diffusion LM with Pretrained Autoregressive Context"** (arXiv 2606.26493 + HF weights; NVIDIA — Reda, Kamalu, Waleffe, Patwary, Shoeybi, Catanzaro)
  - **Relevance:** A parallel-decode approach that **competes with / contrasts against** our MTP/NEXTN refresh. It decouples a **FROZEN autoregressive context tower** from a **trainable diffusion denoiser tower** (cross-attention), emitting up to 16 tokens/step via confidence-based block denoising. Built on Nemotron-3-Nano-30B-A3B (Mamba-2/attention/MoE hybrid, ~3B active).
  - **Reported results:** **2.42× wall-clock generation throughput at 98.7% quality retention** (self-reported, GPU-only).
  - **Key idea worth stealing:** the two-tower "**freeze the pretrained AR backbone, train only a bolt-on parallel generator**" factorization is directly adjacent to how we train MTP/NEXTN heads on a frozen base — a candidate design lens for a parallel head on our frozen CPU models.
  - **Delta from current approach / why worth_investigating not new_opportunity:** it is **diffusion-based and GPU-only** (BF16, dual H100/A100) with **no CPU/GGUF path**, and the Nemotron Mamba2-hybrid-MoE backbone has documented llama.cpp CPU blockers — same deployment wall as DFlash (intake-158). Distinct from the already-indexed Nemotron-Labs-Diffusion tri-mode (intake-576). **Creative-use:** re-evaluate on the MI210/DGX-Spark GPU path if a diffusion-serving backend lands; the backbone is also a standing SSM-hybrid worker/drafter candidate independent of the diffusion tower.

## Research Intake Update — 2026-07-11

### New Related Research
- **[intake-798] "The Gemma Challenge and the Case for Agent Collabs"** (HF blog; HF + Google DeepMind)
  - Relevance: a 6-day agent collaboration optimizing **gemma-4-E4B MTP** inference — the same MTP-drafter family as our production `worker_general` (gemma-4-26B-A4B, Google assistant head). Surfaces one concrete, directly-applicable drafter technique.
  - Key technique — **`onegraph` (fastest *lossless* submission, 315 TPS, downstream-quality-preserving):** the Gemma MTP drafter is **Q-only, KV-shared, with no cross-position dependencies**, so the usual multi-position drafter **warm-up pass is unnecessary** — only the single position that starts the drafting loop is needed, and that step is equivalent to a normal loop iteration. They **fold the warm-up into the 7-step drafting loop, record the entire routine as ONE GPU graph, and replay it with a single launch** — turning a bookkeeping-heavy sequence into a uniform GPU-side routine with no output change.
  - Delta from our approach: this is a **GPU-graph-capture** optimization (relevant to the MI210 GPU-drafter path — see `gpu-drafter-mi200-investigation.md` — not the CPU regime). The *insight* (drafter warm-up is redundant given Q-only/KV-shared/no-cross-position structure) is worth checking against our gemma4 assistant-head drafter loop regardless of backend: if our warm-up does redundant multi-position work, the folding may shave latency on CPU too (verify the structural preconditions hold for our GGUF drafter).
  - **✅ Structural check COMPLETE (2026-07-11)**: all 3 preconditions (Q-only, KV-shared, no cross-position deps) verified against `experimental-v7-candidate` code. HIP graph capture infrastructure is already present (no port needed). See `gemma-challenge-kernel-techniques-v7.md` for details. Next: MI210 smoke-test + benchmark.
  - Contrast — **fastest *lossy* (491.8 TPS)** used vocab pruning + layer removal + a task-targeted fine-tuned drafter + CUDA-graph capture, but degraded GPQA-Diamond/MMLU-Pro by 15/40 points → a cautionary example of exactly the accept-rate-vs-quality trap this handoff's per-model table already guards against.
  - Numbers are OBSERVATION-grade (challenge-internal, GPU, self-reported).

### New Related Research (2nd intake wave — 2026-07-11, Hy3)
- **[intake-806] "Hy3 — Tencent 295B/21B-active MoE (Hunyuan v3 gen)"** (HF `tencent/Hy3`, Apache-2.0)
  - Relevance: ships a **native MTP layer (1 layer, 3.8B params)** on a 295B-total/21B-active, 192-expert (top-8) MoE with 256K context — a same-family MTP drafter to our production gemma4 head, but on a large open-weights MoE that is RAM-feasible on the EPYC 9655 (cf. UD-IQ2 GLM-5.2 ~238GB precedent).
  - Delta from current approach: distinct architecture (`hy_v3`) with a **baked native MTP** rather than a bolted-on assistant head; a standing architect/worker candidate whose MTP is directly on this handoff's topic. Quality claims are Tencent self-reported (blind-eval 2.67/4 vs GLM-5.1 2.51/4; GPQA-D 90.4, SWE-Bench Verified 78) — OBSERVATION-grade, no third-party reproduction (model ~days old).
- **[intake-808] "satgeze/Hy3-1M-GGUF"** (HF; community GGUF port, discovered via expansion of intake-806)
  - Relevance: **first GGUF quants of Hy3 with a working MTP path** — mainline llama.cpp does NOT yet support `hy_v3`; a patched **`hy3-mtp` branch (`satindergrewal/llama.cpp`)** is required, upstream **PR #25395 open + maintainer-engaged**. Port faithfulness confirmed vs Tencent's official vLLM.
  - **⚠️ CORRECTION (deep-dive 2026-07-11): the "88.2% acceptance" is a `p_min=0.75` CONFIDENCE-GATED number a maintainer flagged as invalid.** TRUE **ungated greedy acceptance ≈ 41% (IQ2_M) / 47% (f16)**, matching official vLLM 46.7%. This is a **single-depth** head; 21B-active/top-8-of-192 widens the verify-step expert union → more BW/step.
  - **This is a NEGATIVE datapoint for our CPU-MTP mission, not a win.** Author's own **Metal M3 Max (BW-bound) = net-neutral** (23.27 vs 23.21 t/s). EPYC decode is also BW-bound → predicted **net-neutral**, i.e. Hy3 *confirms* the MoE-A3B expert-verification wall (~1.06× row above), it does not break it. CUDA gains (+13% H200) are compute-bound only.
  - Delta / actionable: quants **IQ2_M 100GB → Q4_K_M 183GB → Q6_K 246GB** — RAM is a non-constraint (all << 1.1TB); **disk (~680GB free) is the limiter → download ONE quant**. **Native ctx = 256K** (config `rope_type:"default"`); the "1M" is a **community RoPE extension** (~70%/needle at 1M). The `chat_template_llamacpp.jinja` workaround is being **obsoleted upstream** (pwilkin jinja fix). Arch string `hy_v3` vs `hy-v3` unresolved → **pin a commit**. IQ1_M is `no_think`-only.
  - **Full assessment:** [`research/deep-dives/2026-07-11-hy3-hunyuan-v3-moe-mtp-assessment.md`](../../research/deep-dives/2026-07-11-hy3-hunyuan-v3-moe-mtp-assessment.md). Numbers OBSERVATION-grade; EPYC adoption operator-gated.
- [x] Hy3 MTP/runnability closure ✅ 2026-07-17: the official AngelSlim **`Hy3-IQ1_M-mtp.gguf`** (~92 GB, MTP/NextN head baked) is complete on disk at `models/hy3-angelslim/`, experimental v7 loads it, and CPU plus MI210-hybrid MTP/no-spec A/Bs passed functionally. The measured samples favored no-spec over `draft-mtp`, so the old first-load / CPU-MTP closure gate is done.
- [x] Hy3 task-quality / architecture-fit first slice ✅ 2026-07-18: `data/hy3_task_quality/hy3_task_quality_20260718Tcontinuation/` ran CPU no-spec and MI210-hybrid no-spec (`--cpu-moe --fit on`) on six deterministic server/chat tasks. Both lanes passed `5/6`, failed only exact six-word instruction, and cleaned up all `llama-server` PIDs. Hybrid no-spec averaged `11.51 t/s` decode vs CPU `5.21 t/s`. Classification: partially coherent and hybrid-faster, but not role-ready; next Hy3 work is prompt/template repair or a role-specific suite, not first-load or MTP-closure reruns.

## Research Intake Update — 2026-07-16

### New Related Research (3rd intake wave — 2026-07-16): DSpark drafter, GIDD foundation, official Hy3 MTP GGUF
- **[intake-821] Bonsai-27B whitepaper — DSpark drafter** (PrismML, 24pp PDF parsed)
  - Relevance: DSpark is a **semi-autoregressive speculative drafter** — a block-parallel backbone (DFlash lineage) + a lightweight sequential head for intra-block dependencies + a **confidence head for per-position survival** + a hardware-aware verify-cost scheduler; trained against the Bonsai-27B target with lossless verification. Reported H100: accepted length τ≈3.6–3.7, **1.34–1.37× decode**; a 4-bit-quantized drafter with rollout parity to bf16.
  - Delta from our MTP path: DSpark is a bolted-on confidence-scheduled semi-AR drafter vs our native gemma4/Hy3 MTP heads; the **confidence-gated per-position survival** idea is the transferable drafter-design pattern. All numbers are CUDA/compute-bound vendor self-report — the same BW-bound caveat as our Hy3-MTP finding likely applies on EPYC. credibility 1.
- **[intake-830] "Generalized Interpolating Discrete Diffusion" (GIDD, arxiv:2503.04482, ICML 2025)** — reference-chased from DSpark; credibility 4.
  - Relevance: the **foundational discrete-diffusion noise-process theory** beneath the block-diffusion drafter lineage (DFlash/DART/DSpark). Distinct from the existing DFlash entry (intake-158) — GIDD is the noise-process + emergent **self-correction** (revisable-token) theory, not an applied drafter. It has NO parallel-generation or serving method to port, and self-correction adds a second test-time compute axis (poor fit for BW-bound CPU — the same wall that α-gated DFlash CPU work). Keep as foundational context; re-weight only if a GPU diffusion-serving backend lands ([[gpu-acceleration-path]]).
- **[intake-824] "AngelSlim/Hy3-GGUF" (official) + [intake-823] "vcruz305/Hy3-GGUF" (community)** — official + community GGUF of Hy3 with a baked MTP head.
  - Relevance to the Hy3 MTP thread above: intake-824 is the **authoritative official GGUF path** (IQ1_M ~90 GB; ~185 GB Q4_K_M with-MTP) for the deferred, operator-gated confirmatory CPU-MTP run — an alternative to the community `satindergrewal/llama.cpp@hy3-mtp` port (intake-808). vcruz305 (intake-823) adds DGX Spark GB10 MTP numbers (+27% / +58%), which are CUDA compute-bound and **corroborate the predicted CPU net-neutral** rather than overturning it. Neither changes strategy: Hy3 MTP on BW-bound EPYC remains predicted net-neutral; the existing operator-confirmation item above already scopes the one IQ2_M run (intake-824's official IQ1_M is simply an alternative authoritative download source for it).

## Research Intake Update — 2026-07-21 (An external MTP draft-depth sweep with a non-monotonic optimum)

- **[intake-871] "brandonmusic/GLM-5.2-NVFP4-TR3-Hybrid"** — community hybrid quant of GLM-5.2 (744B MoE-DSA), artifact NOT loadable here (NVFP4 safetensors, Blackwell container, CUDA-only EXL3 extension), but it publishes a serving result worth having.
  - Relevance: an **MTP draft-depth sweep (2/3/5) with a non-monotonic optimum at depth 3**, beating both 2 and 5 at every measured context. Self-reported, 4x RTX PRO 6000: MTP3 62.5/63.2/62.6 tok/s at 0/32K/128K vs MTP2 60.3/58.4/54.5 and MTP5 50.0/43.3/42.2.
  - The stated mechanism is the transferable part: depth 2 accepted a **higher draft fraction but under-filled the verification window**, while depth 5's verification cost exceeded its accepted tokens. That is an accept-rate-vs-verification-window tradeoff, which is structurally the same tension our own native-MTP A/B probes.
  - **Comparison is structural, not numeric.** Their depth is a serving-side draft depth on a checkpoint with `num_nextn_predict_layers=1`, on compute-bound Blackwell GPUs; ours is a native MTP head on bandwidth-bound EPYC. Do not port the number; port the question — are we measuring enough depths to see a non-monotonic optimum, or assuming monotonicity?
  - Credibility 2: uploader is not a known quantizer, all numbers self-reported with zero independent corroboration, `verdictai/` Docker namespace suggests commercial affiliation. Raised from 1 by genuinely above-norm evidence discipline (calibration manifest with corpus sha256, pinned harness commits, SHA256SUMS, retained losing arms MTP2/MTP5, retained OOM failure case).
- **[intake-870] "vLLM-Moet"** — separately reports MTP acceptance 2.73 vs 2.68 and draft accept 86.3% vs 84.1% against an official (NV)FP4 baseline on the same model family. Sample sizes tiny/unstated; treat as a weak external reference point only.

- [x] MTP-refresh candidate: confirm our native-MTP A/B sweeps enough draft depths to detect a non-monotonic optimum rather than assuming monotonic falloff. ✅ 2026-07-29 — the paired T5 worker sweep covers depths `2/3/4` at both 512 and 1024 completion tokens and is non-monotonic in both runs: `2 > 4 > 3` in decode throughput, while accepted tokens are nearly flat. This is sufficient to reject a monotonic-depth assumption and retain depth 2; it does **not** establish a global optimum outside the tested range. Evidence: `t5_gemma_worker_draft_depth/20260718T175656Z_cpu_8k_1024tok/summary.json` and the 512-token predecessor.

### Audit note 2026-07-21 — quant-pair self-speculation (idea unexamined, not endorsed)

intake-870's **confidence-gated full-precision recompute** was dropped bundled with the (falsified) hot-expert delta tier, but it is a distinct mechanism and maps onto ground we already own: it is structurally **speculative decoding with a low-bpw quant as drafter and a higher-bpw quant of the SAME model as verifier** (e.g. GLM-5.2 UD-IQ2_M draft → UD-IQ3_XXS verify; both fit 1.1TB RAM together at ~540GB). Same-model different-quant should give very high acceptance α, which is the favorable spec-dec regime — but verifier bandwidth per accepted token is the whole question on a BW-bound host, and per standing discipline (`feedback_measure_alpha_before_specdec_investment`) **α must be measured before any investment**. Related prior art: completed [hsd-hierarchical-self-speculation.md](../completed/hsd-hierarchical-self-speculation.md).

- [ ] IF a GLM-5.2 higher-bpw artifact lands for H-Q1 anyway (glm52-reviewer-capability-gates.md), piggyback a cheap α(IQ2_M→IQ3_XXS) measurement on the same download before considering anything further. No download solely for this.


## Laguna DFlash intake integration — 2026-07-22
_Via /research-intake Stage-2 (intake-879/880); see [laguna-s21-cpu-port.md](laguna-s21-cpu-port.md). All rows operator-gated; numbers are OBSERVATIONS per MEASUREMENT.md._
- [ ] Bench DFlash accept-rate on Laguna: {Q8_0, Q4_K_M, IQ2_M} target x BF16 DFlash drafter. PRECONDITION: download Q8_0 (128GB) after architect benches free disk. Reopen the March NO-GO (`../completed/dflash-block-diffusion-speculation.md`) only if the Q8_0 target recovers per-token acceptance toward ~60%. **Causal correction 2026-07-29:** target-side quant noise in conditioning hidden states remains a hypothesis, not an established root cause: Laguna moved only 17.2% (Q4) → 19.0% (Q8), and BF16/F16 targets remain untested. The BF16 drafter alone cannot settle a target-side effect; treat acceptance as the gate rather than presuming its cause.
- [ ] Scope the DFlash draft-dflash spec-path port (poolside fork branch `laguna` only; NOT in ggml-org/llama.cpp PR #25165; reuse EPYC's completed hidden-state-tap + cross-conditioning scaffolding from `feature/dflash-speculation`) — GATED on the accept-rate bench above showing a viable regime


## 2026-07-25 — intake Stage-2a dive: the DFlash blocker is dead; two unmeasured production-role drafters

_Via `/research-intake` Stage-2; see [`intake-derived-work-2026-07-25.md`](intake-derived-work-2026-07-25.md) ID-28..ID-34, ID-15, ID-16._

- [x] **Retire the "DFlash requires SGLang/vLLM — no llama.cpp support, no GGUF, no CPU path" framing wherever it still appears. ✅ 2026-07-29** Verified: upstream merged DFlash 2026-06-28 (`d1b34251b`, PR #22105); forward-ported to **production** 2026-07-18 (`ed4091266`); `src/models/dflash.cpp` is present on `production-consolidated-v7`; `draft-dflash` is wired into `common/speculative.cpp`, `docs/speculative.md` and the server README; and `Qwen3.6-27B-DFlash-f16.gguf` (8,558,077,216 B) has been on disk since 2026-07-03. Corrected the remaining live global claims in `wiki/ssm-hybrid.md` and `research/deep-dives/lucebox-hub-consumer-gpu-dflash.md`, and clarified the historical vLLM-only benchmark wording in `gpu-acceleration-path.md`; the CPU no-go remains an acceptance/Delta-Net verification-cost finding, not an availability claim.
- [ ] **Measure `z-lab/gemma-4-26B-A4B-it-DFlash` (0.43B, apache-2.0) against the live worker_general target.** The z-lab collection grew from ~4 drafters to **22** and now covers two roles the March handoff recorded as *"GAP — needs custom training"*. This is the strongest candidate: pure MoE with no Delta Net recurrence (avoids the GDN verification wall), and the incumbent native-MTP drafter is already measured **NOT VIABLE** (58.7% acceptance / 1.06×). Precondition: the target weights must be the same `google/gemma-4-26B-A4B-it` that produced the ORIG Q4_K_M GGUF — conditioning hidden states are target-specific. Report against the L-6 acceptance floor; do **not** register in the production stack before the floor passes.
- [x] **Watch-item: `z-lab/Qwen3.5-122B-A10B-DFlash` (apache-2.0)** targets the live architect_general model, which currently self-drafts via native NEXTN MTP. **Acceptance-only scope ✅ 2026-07-29:** first acquire/convert only the target-locked drafter against the exact deployed `Qwen3.5-122B-A10B-UD-Q4_K_M` target; verify the converted artifact's target binding and run a pinned-prompt, fixed-runtime comparison that reports accepted / drafted tokens (α) beside the incumbent native-MTP α. No role registration, throughput or quality claim, production-stack change, or port effort follows from this probe; advance only if α clears the standing acceptance gate under an operator-approved run.
- [x] **Record the settled DFlash architecture ✅ 2026-07-29** so it stops being re-derived: drafters are **headless** (no `embed_tokens`, no `lm_head`; 58 tensors) and **non-causal** (`is_causal=False`), driven by a block of `mask_token_id` embeddings. They are **inert as `--model-draft`** and live only under `-md` + `--spec-type draft-dflash` after conversion with `--target-model-dir`. `fc.weight` is `[hidden, n_taps*hidden]`, so every drafter is **target-locked**. Drafting is **single-pass**, not iterative denoising. The reference repo has **zero tests, zero CI**, has been dormant since 2026-05-10, and contains **no custom CUDA kernels** (a complete MLX backend exists) — `adopt_patterns` reference semantics only, take no dependency. Source-record cross-check: `intake-derived-work-2026-07-25.md` ID-34.
- [x] **Provenance for the published DFlash speedups** ✅ 2026-07-29 — 6.17× MATH-500 / 5.91× AIME24 / 5.85× AIME25 are **Qwen3-8B, greedy temp 0, hardware unstated on the project page, measured against naive autoregressive decode at concurrency 1**. That is a naive baseline, unusable for comparison against a stack whose incumbent is native MTP. Code and agentic suites are **2.27×–5.43×**, roughly half the headline. Record all as non-gating observations under MEASUREMENT.md; no DFlash target, prompt, concurrency, acceptance, quality, or hardware claim transfers from them.
- [x] **DavidAU Qwen3.6-27B MTP GGUFs — header gate, zero inference.** ✅ 2026-07-29 — direct ranged reads of the public DavidAU Q8 pair verified the gate without downloading weights: the non-MTP artifact reports GGUF v3 / **851 tensors** / 69 KV pairs in bytes 0–23, while the MTP artifact reports v3 / **866 tensors** / 70 KV pairs; its first 64 KiB metadata window contains `qwen35.nextn_predict_layers`. The local ggml-org Q4_K_M and Q8_0 controls produce the same 851/866 split. **Use TENSOR COUNT, not file size**: `851 = no MTP, 866 = MTP` (+15 = the `blk.64.nextn.*` block), readable in a 24-byte ranged header read, plus KV key `qwen35.nextn_predict_layers`. File-size reasoning is unsound — ThinkingCap's Q4_K_M is 722 MB *smaller* than our non-MTP Q4_K_M and still has MTP. DavidAU's constant 451,320,768 B delta **is** exact across all ten pairs (dive-confirmed, zero variance); the repo publishes **22** GGUFs (IQ4_XS and Q6_K each have an undocumented `LOW-MTP` variant), apache-2.0, plus three mmproj projectors. **Relevance is asymmetric**: real on the MI210 (measured optimum 53.1 t/s at `--spec-draft-n-max 4`, 1.82×), but the CPU plane is architecturally foreclosed (48 of 64 layers are Gated DeltaNet; 0.56× measured on the Qwen3.5 hybrid sibling) — "MTP" in a filename must never read as a reopen trigger for the parked CPU handoff.
- [x] **ThinkingCap's MTP head is STOCK — confirmed at byte level.** ✅ 2026-07-29 — durable saved-header evidence and the Stage-2 artifact audit establish that the entire 451 MB layer-64 block is **byte-identical** to local `Qwen3.6-27B-MTP-Q8_0.gguf` (single SHA-256 over the region), as are `token_embd.weight`, `output.weight` (tied shared head), and `output_norm.weight`; a control tensor (`blk.32.ffn_gate`) genuinely differs, so the offset arithmetic is sound. The differing set is exactly the **256 LoRA target modules**, matching upstream `merge_verify_report.json` (r=64, α=128, merged scaling 2.0) and an MTP shard named `model-base-aux.safetensors`. Consequences: **MTP is not a ThinkingCap feature** (hold it constant across arms); it is a genuine **co-trained-head vs modified-trunk mismatch**, predicted worst on the early "keep thinking?" tokens the finetune targets; reported accept-length (3.69/3.65 vs base 3.66/3.61) is **statistically indistinguishable from base** and the vision numbers are slightly *worse*.
  - **Hazard for any Q4_K_M A/B**: our two local Q4_K_M artifacts are **not a clean pair** — `Qwen3.6-27B-MTP-Q4_K_M.gguf` (17,106,773,120 B, 866 tensors) is *smaller* than `Qwen_Qwen3.6-27B-Q4_K_M.gguf` (17,533,552,192 B, 851 tensors), i.e. different quantizer recipes. Any MTP-vs-non-MTP benchmark on those two is confounded.

## 2026-07-29 — intake Stage-4: KAT-Coder-V2.5-Dev artifact facts + a reusable preflight rule

_Via `/research-intake` Stage-4 (intake-916/917/932 lineage, AREX-Base as the counterexample). Zero-inference artifact reads; no bench implied._

- [x] **Record two durable artifact facts for KAT-Coder-V2.5-Dev.** ✅ 2026-07-29 — (a) its **tokenizer is byte-identical** to the deployed frontdoor — `sha256 5f9e4d49…cb42` on `tokenizer.json`, with matching `vocab.json` / `merges.txt` — so the **exact-tokenizer precondition for speculative decoding is SATISFIED** and needs no re-derivation. (b) its **MTP head is REMOVED**: `mtp_num_hidden_layers` 1→0 and **zero** `nextn`/`mtp` tensors across **31,333** revision-pinned weight-map entries. This is a regression versus the live frontdoor GGUF, which carries `blk.40.nextn.*`; any frontdoor-lane candidate manifest must therefore mark native MTP `absent` and cannot be compared as a like-for-like speculative-decoding replacement. A quality benchmark alone cannot detect that loss.
- [x] **Adopt the reusable preflight rule: verifying a fine-tune's architecture from `config.json` is UNSOUND.** ✅ 2026-07-29 — **AREX-Base retains `"mtp_num_hidden_layers": 1` while shipping ZERO mtp weights**: a config-level check reports "preserved" and is **wrong**. Before any architecture-dependent capability claim or candidate comparison, require a manifest record of (1) source/revision, (2) `model.safetensors.index.json` tensor-name/count evidence (or GGUF header tensor count plus relevant metadata key), and (3) explicit present/absent conclusion for every claimed MTP/draft head, vision tower, tied embedding, or other component. `config.json` may describe the expected shape only; it cannot satisfy the preflight or justify an architecture-equivalence claim. File this alongside the existing tensor-count-not-file-size rule — same failure family.
