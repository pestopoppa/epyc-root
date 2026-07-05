# GPU CoT-Scaffold Sidecar — Preliminary Pure-GPU Research Lane

**Status**: PROPOSED / preliminary research lane (operator-approved 2026-07-04)
**Created**: 2026-07-04 (via research-intake deep-dive of the Fable-5 distillation ecosystem)
**Categories**: agent_architecture, training_distillation, hardware_optimization, routing_intelligence, local_inference
**Hardware**: single MI210 (gfx90a/CDNA2, 64 GB HBM2e, ROCm 6.2); HIP build `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip`. Kernel work (if any) lands in `llama.cpp-experimental` per the operator rule.

## Objective

Test whether a small, fast, GPU-resident **reasoning model** can generate a **chain-of-thought scaffold** that, injected into a larger CPU-tier worker's prompt, raises that worker's answer quality **more than the worker's own thinking does, per token spent**. If it holds, a single MI210-resident "CoT sidecar" could feed reasoning scaffolds to several lightweight roles at GPU speed while the workers stay CPU-resident.

This is a **research screen**, not a deploy plan. Every accuracy/throughput number it produces is an **OBSERVATION** (MEASUREMENT.md) until it is re-run through the codified eval-tower recipes with operator approval. The lane's job is to cheaply kill or promote the hypothesis.

## Why this is a *pure-GPU* lane (the load-bearing insight)

Aside from `architect_general` (Qwen3.5-122B, ~65 GB+ — does not fit) and `ingest_long_context` (huge KV), **every production-stack model fits on one 64 GB MI210**, and the generator + a beneficiary fit **co-resident at the same time**:

| Model | GGUF (verified path) | Size | Role in this lane |
|---|---|---|---|
| `Qwen3-4B-Thinking-2507` Q8 | **staged** `/mnt/raid0/llm/models/Qwen3-4B-Thinking-2507-GGUF` (4.0 GB) | ~4.0 GB | scaffold generator — **CONTROL** |
| `Qwable-v1` IQ4_XS **+ Q8_0** | **staged** `/mnt/raid0/llm/models/Qwable-v1-GGUF` (IQ4_XS cheap-deploy arm + Q8_0 clean-quality arm; AGPL-3.0) | 17.6 / 34.4 GB | scaffold generator — **TREATMENT** (see *Generator quantization*) |
| `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf` | local (ORIG base **required** on v6 — the non-ORIG Q4_K_M garbles) | **15.6 GB** | worker_general — **cross-family** beneficiary |
| `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` | local | 35.2 GB | frontdoor **and** coder_escalation (**shared GGUF**) — **same-family** beneficiary |

Note: `coder_escalation` and `frontdoor` are the **same qwen35moe GGUF** (shared mmap) — so hosting the code beneficiary co-loads only one 35 GB file, not two. Co-residency on 64 GB: scaffold-4B (~4) + gemma worker (~15.6) + KV ≈ **~22 GB**, both live at once; scaffold-4B + the shared qwen35 35 GB + KV ≈ ~42 GB also fits.

**Consequence:** the whole A/B runs as one GPU session with **no CPU-stack contention, no "no-concurrent-inference-on-EPYC" waiver, and no dependency on the blocked N5 external-draft spec-dec path** — because transfer here is via **text at the prompt level**, not shared vocab/KV. Scoring uses the eval tower pointed at GPU-hosted `llama-server` endpoints.

## Feasibility already confirmed (no fork changes needed)

- **Assistant-prefix injection** (arm 3) is native to `llama-server`: `continue_final_message` / `prefill_assistant` (`llama.cpp/tools/server/server-common.cpp:1025-1036`). The generator's `<think>` block is prefilled as the start of the beneficiary's assistant turn; the beneficiary continues from it.
- **MTP is irrelevant for the scaffold role.** Scaffold generation is plain text-gen; it needs no NEXTN head, no vocab alignment, no spec-dec. (This is exactly why the lane sidesteps N5.) The deep-dive finding that the community `Qwable-v1` GGUF *dropped* its MTP head (intake-777) therefore does **not** affect this lane — only the separate role-replacement idea, which is out of scope here.

## Candidate scaffold generators (refined by 2026-07-04 deep-dive)

The core question is **"does distilling frontier CoT into a small model make a *better* scaffold generator than a purpose-built general reasoner?"** So this is a **control vs treatment** design — a CoT-distilled model is the point, the vanilla reasoner is the bar it must clear. Run them together.

- **CONTROL — `Qwen/Qwen3-4B-Thinking-2507`** (~4 GB Q8, Apache-2.0, published evals). A strong, cheap, purpose-built long-CoT reasoner. NOT the "answer" — it's the **baseline the distilled models must beat**. If no distilled model beats it, "baked on frontier traces" bought us nothing.
- **TREATMENT (primary) — `Qwable-v1` IQ4_XS** (~17.6 GB, intake-777). The strongest **off-the-shelf CoT-distilled model on our own qwen35moe family**: two-stage Opus-4.7-reasoning + Fable-5-agentic distill, agentic-tuned (fits the code beneficiaries). This is the "special finetuned version baked on CoT traces." Caveats: 35B → a heavier/slower generator, and **zero published evals** (hypothesis-grade). MTP-drop is irrelevant for scaffolding.
- **TREATMENT (cheap 4B) — `ermiaazarkhalili/Qwen3-4B-SFT-Fable5-Glint`** (full-SFT, GGUF). A 4B Fable-CoT-distilled arm in the **same weight class as the control**, so it isolates the *distillation* effect without the 35B confound. Add if the 35B arm looks promising but too heavy.
- **FUTURE / ideal — an in-house tune on the cached seed.** The truly matched "special version" (our target model, full sequence length, our recipe) **does not exist yet**; the ~0.2 GB Fable-5 seed we just cached is its training data. Gated on the `swarm-dataset-distillation` path — and this lane's G1/G2 result is exactly what decides whether building it is worth it.
- **DROPPED**: `dharandhamo/fable5-qwen3-4b-lora` (intake-773 — no GGUF, `down_proj` missing, 2048-token cap truncates traces); `AliesTaha/fable-traces` (intake-775 — non-thinking base, short-reply tuned, **hard-disqualified**).

### Generator quantization (MI210) — regime-dependent, per the live GPU-session logs

**Not** "bigger quant = faster." The active MI210 campaign (`mi210-speed-campaign-summary.md`, 2026-07-04) measured a **regime split** — verify against it, do not assume:

- **Single-stream (B=1, bandwidth-bound): Q8 wins** — Q8 **96.6** vs bf16 **73.1 t/s** (1.32×; fewer bytes, BW-bound). This is the *on-demand sidecar* regime.
- **Batch decode (B≥16–32, compute-bound): bf16 wins** (+27–43%, **crossover B≈16–24**) — bf16 runs native on MFMA with no dequant. This is the *bulk offline scaffold-generation* regime (generating scaffolds over a whole eval suite at once).
- **Q4_K/IQ**: fewer bytes but a real **dequant penalty at B=1** (~28 pp for Q4_K, ~12 pp for Q8 vs the fp16 62.5% ceiling) that *amortizes across columns* at B>1. **IQ (i-quants) has no measured MI210 number yet — still under study** (sub-4-bit CDNA2 dequant enabler is an open research bet).

For a *scaffold generator* the quantity we measure **is** reasoning quality; bf16 ≈ Q8 are both near-lossless while Q4/IQ trade quality. So:

- **Control (4B): Q8** (4 GB, near-lossless). bf16-4B (8 GB) is the batch-regime option if we bulk-generate, but the 4B gap is small — hold unless a batch sweep says otherwise.
- **Treatment (35B): Q8_0 (34.4 GB) is forced as the near-lossless choice — bf16-35B ≈70 GB does NOT fit the 64 GB card**, so the batch-regime bf16 win is unavailable for it; Q8 is both the fitting near-lossless quant and the single-stream optimum. **IQ4_XS (17.6 GB)** is the exploratory cheap-deploy arm (matches "IQ still under study") and the only one that **co-resides with a same-family qwen35 beneficiary** (IQ4 17.6 + coder_escalation 35.2 = 53 GB fits 64; Q8 34.4 + 35.2 = 70 GB does not — Q8 runs with the gemma beneficiary or sequentially).
- **Future (noted per operator 2026-07-04, out of scope for G1):** "bf16-35B doesn't fit" is *today's* limit, not permanent. With **MoE expert-offload** — cold experts streamed from the 1.1 TB host, only the ~3B active + non-expert weights GPU-resident — a bf16 35B-A3B could drop under 64 GB and **reopen the batch-regime bf16 win** for the treatment. The machinery exists default-off (`large-moe-expert-parallelism.md`, bit-correct EP) alongside heterogeneous GPU/CPU op-offload (`fable5-window2-findings-02-heterogeneous-gpu.md`). Another day — does not gate G1.
- **Which regime applies depends on how G1 runs the generator**: bulk/offline over a suite → batch (bf16 territory, but 35B-bf16 doesn't fit *today* → Q8); live on-demand sidecar → single-stream (Q8). G1 reports **per-quant** and feeds the open MI210 quant-roofline question (`mi210-speed-campaign-summary.md`, `mi210-q8-dequant-gemv-roofline.md`, findings-05b/05c). Delete the losing quant after G1 as hygiene (two Qwable quants ≈52 GB) — not urgent: raid0 is ~955 GB free / 74% since the 2026-07-04 coding-corpus reclaim.

## Beneficiaries — the code-writing/correcting roles (operator-scoped 2026-07-04)

Operator scope: **"any model responsible for writing/correcting code."** That is the two code roles:

1. **`Qwen3.6-35B-A3B` coder_escalation** (Q8) — PRIMARY code role; **same-family** as the qwen35 generators, so it isolates whether any lift is merely family-matched.
2. **`gemma-4-26B-A4B` worker_general** (Q4_K_M) — the other code-handling role and the decisive **cross-family** test (Qwen scaffold → gemma worker).

Together they give a clean same-family vs cross-family contrast, both on code tasks. `frontdoor` is the router/interactive path (not primarily code-writing) — include only if it turns out to sit in the code path. Suites: code-writing + code-correction/debug from the eval tower.

## Experiment arms (per generator × beneficiary × suite)

1. **BASELINE-nothink** — beneficiary answers directly, `enable_thinking=false`.
2. **BASELINE-ownthink** — beneficiary does its own CoT, `enable_thinking=true`.
3. **SCAFFOLD-prefix** — generator emits `<think>` → injected as assistant-prefix (`continue_final_message`) → beneficiary continues, then answers.
4. **SCAFFOLD-context** — generator emits a short plan → injected as system/context advisory → beneficiary answers with `enable_thinking=false`.

**Metrics per cell:** eval-tower accuracy **and** full token accounting (generator tokens + beneficiary tokens) **and** a wall-clock/latency estimate (scaffold is serial *pre*-decode). Compare **token-normalized**. The scaffold only wins if it beats **BASELINE-ownthink** at equal-or-lower total token cost, i.e. it must **substitute** for the worker's own thinking, not add to it.

## Kill-gates (each cheap, each pure-GPU)

- **G0 — Qwable-v1 GGUF MTP check — DONE (free).** Result: community GGUF dropped MTP/NEXTN (733 tensors, zero head) → *no impact on this lane* (scaffold role needs no MTP). Recorded in intake-777.
### G1 slice-1 RESULT (2026-07-05) — **GO** (does any scaffold beat own-think? YES), heavily caveated

Run by the GPU-campaign session. Control gen `Qwen3-4B-Thinking-2507-Q8_0` (:8801) × same-family beneficiary `Qwen3.6-35B-A3B` coder_escalation (:8802), co-resident on the MI210 (45.4/64 GB), eval-tower `debug/coder.yaml` (`code_execution` oracle), n=12 seed-42, eval-tower `debug_scorer.score_answer` (**no parallel scorer built**). All OBSERVATION (not eval-tower-recipe-confirmed).

| Arm | Acc | total tok | tok/solved | vs own-think |
|---|---|---|---|---|
| nothink | 0.833 | 1,241 | 124 | — |
| **ownthink (bar)** | 0.917 | 23,800 | 2,164 | — |
| SCAFFOLD-prefix | 0.833 | 13,833 | 1,383 | −1 acc → no |
| **SCAFFOLD-context** | **0.917** | **10,677** | 971 | **= acc, 0.45× tok → WIN** |

- **Verdict G1-(i): GO.** SCAFFOLD-context (advisory-plan → nothink beneficiary) matches own-think accuracy at **0.45× total tokens** (generator cost included) and rescues the single discriminating question (`code_hard_002`: nothink fails, all thinking arms pass). **Injection-mode answer: context-advisory beats assistant-prefix** — prefix loses to a `<think>`-prefill continuation-fidelity artifact.
- **Load-bearing caveats:** (1) suite is >90%-saturated (only **1** discriminating question after excluding buggy oracle `humaneval_004` — flagged for suite maintainers) → direction solid, magnitude n=1; (2) single-sample; (3) generator Q8_0 only (near-lossless MI210 single-stream optimum) → feeds the quant×quality curve.
- **Next (plan, not run):** (a) **fix saturation first** — re-run on a harder code set (nothink pass ~40–70%, e.g. code_hard tier-3 / HumanEval+/MBPP+ hard, ~25–40 q); (b) add TREATMENT `Qwable-v1` for G1-(ii) distillation (IQ4_XS 17.6 GB co-resides with the 35B; Q8 34.4 GB does not); (c) G2 cross-family gemma (expect nothink-only bar — gemma has no thinking mode); (d) keep SCAFFOLD-context as primary. Artifacts: `/mnt/raid0/llm/tmp/cot-g1/`.

### G1 slice-2 RESULT (2026-07-05) — CONFIRMED + REFRAMED: the injection-mode answer FLIPS to PREFIX
Harder suite `mode_advantage` tier-3 (hard code, N=27, nothink **77.8% = unsaturated**, 17/27 discriminating). Same slice-1 harness. OBSERVATION.
| Arm | Acc | total tok | tok/q | vs nothink |
|---|---|---|---|---|
| nothink | 77.8% (21/27) | 12,221 | 453 | — (correct cheap baseline) |
| ownthink | 33.3% (9/27) | 82,399 | 3,052 | **truncation-contaminated** (3072 cap on 26/27) |
| **SCAFFOLD-prefix** | **88.9% (24/27)** | 54,543 | 2,020 | **+11.1pp, net +3 Qs, rescues 4/6 → WINS** |
| SCAFFOLD-context | 77.8% (21/27) | 33,313 | 1,234 | ties nothink @2.7× tok → **Pareto-DOMINATED** |
- **The injection-mode answer FLIPPED from slice-1.** Slice-1 (saturated) said context-advisory wins + prefix loses; the harder unsaturated suite reverses it: **SCAFFOLD-prefix is the ONLY arm that beats plain nothink (+11.1pp)**; SCAFFOLD-context is Pareto-dominated by nothink (adds no value). The `<think>`-as-assistant-**prefix** lifts the 35B above its no-think ceiling; the plan-as-system-**context** does not. Slice-1's context-win was a saturation artifact — supersedes the "keep SCAFFOLD-context as primary" line above.
- **ownthink baseline is truncation-contaminated** (3072-token cap on 26/27) → the +44pp headline over ownthink overstates the gap; the correct cheap baseline is **nothink (77.8%)**, and prefix beats that.
- **Verdict: G1-(i) survives (a scaffold beats the cheap baseline) — but as PREFIX, not context.** Next: (a) **pivot the carried arm to SCAFFOLD-PREFIX** for G1-ii (Qwable treatment) + G2 (gemma cross-family); (b) **decontaminate ownthink** — re-run alone at 6144/8192 cap (~1 GPU-hr); (c) prefix is the more interesting cross-family test (depends on the `<think>` surviving gemma's template). Artifacts: `/mnt/raid0/llm/tmp/cot-g1/*_hard*`.

### G2 + G1-ii RESULTS (2026-07-05) — ⚠️ the "scaffold beats nothink" claim is CONFIG-FRAGILE; literal-prefix does NOT transfer cross-family. FLAGGED FOR OPERATOR DECISION.
Both OBSERVATION-grade (single MI210, single-sample seed=42, eval-tower `debug_scorer`). **These two results together walk back the slice-2 headline: every successive baseline cleanup has caught nothink catching up.**

**G2 — cross-family transfer (4B-Thinking → gemma-4-26B-A4B-ORIG).** Premise correction (mine): gemma-ORIG is NOT "no thinking mode" — `arch=gemma4` has a **native channel/harmony reasoning template** (`<|channel|>thought`); llama-server defaults thinking ON, so the clean no-think baseline requires `enable_thinking=False`.
| Arm | Acc | tok/solved | vs gemma-nothink |
|---|---|---|---|
| **nothink** (gemma direct, baseline) | **81.5%** (22/27) | **903** | — (already strong + cheapest) |
| scaffold-prefix **literal `<think>`** | 63.0% (17/27) | 6,116 | **−18.5pp, DOMINATED → does NOT transfer** |
| scaffold-prefix **native `<\|channel\|>thought`** | **92.6%** (25/27) | 2,406 | +11.1pp acc, 0 regressions — but 2.7× tok |
| scaffold-context (advisory) | 88.9% (24/27) | 1,507 | +7.4pp acc, 0 regressions — but 1.7× tok |
- **The carried literal-`<think>`-prefix mechanism is SAME-FAMILY-ONLY** (63.0%, below gemma's own no-think, Pareto-dominated). The `<think>` survives lexically (0 leaked tags, 27/27 valid code fence) but gemma doesn't treat the foreign `</think>` as a reasoning boundary → over-generates (14/27 hit the cap). **Slice-2's prefix-win was a FORMAT-family effect, not same-family.**
- **The reasoning *content* DOES transfer — iff delivered format-native** (into the target's own reasoning slot): +11.1pp, 0 regressions, 3 rescues. **Redefine SCAFFOLD-PREFIX = target-native reasoning-slot injection, NOT a literal Qwen tag.**
- **Token-normalized STRICT (acc↑ AND tok/solved≤baseline): NO arm beats gemma no-think.** The lift is on accuracy, bought at 1.7–6.8× the tokens. gemma's *own* native reasoning is a stronger ceiling (6/6 subset) but ~6× costlier.

**G1-ii — distillation (Qwable-v1 IQ4_XS vs vanilla 4B control, both prefix → 35B-Q8 beneficiary).**
| Arm | Acc | tok/solved | note |
|---|---|---|---|
| nothink (`-c 10240`) | **88.9%** (24/27) | 484 | ⚠️ jumped from 77.8% @`-c 8192` |
| **qwable-prefix** (35B distilled IQ4_XS) | **88.9%** (24/27) | **1,490** | ties nothink; **+11.1pp vs 4B-control, 0.58× tok** |
| control-prefix (vanilla 4B) | 77.8% (21/27) | 2,560 | regresses BELOW nothink here |
| ownthink @8192 | 44.4% (12/27) | 16,617 | Pareto-terrible, 22/27 still truncating |
- **Distillation thesis CONFIRMED (clean survivor):** distilled Qwable-prefix beats the vanilla 4B-control-prefix +11.1pp at 0.58× tok/solved + fewer generator tokens + less wall (concise EOS-closed reasoning, less disruptive to a strong beneficiary — derails 1 nothink-pass vs the 4B's 4). An in-house tune is *mechanistically* justified.
- **⚠️ CRITICAL CONFOUND — the "prefix beats nothink" result is a context-length artifact.** The clean own-think fix forced beneficiary `-c 10240` (to hold an 8192-tok own-think); slice-2 was `-c 8192`. **Qwen's context-length-dependent rope scaling** flipped nothink 77.8%→**88.9%** at the larger `-c`. So at `-c 10240` **NEITHER scaffold beats nothink** (qwable ties, control regresses). Slice-2's "nothink 77.8% + prefix wins" was a `-c 8192` artifact.

**NET VERDICT (both slices):** the lane's load-bearing claim — *a scaffold beats the cheap nothink baseline* — has **not survived successive baseline cleanups** (slice-1 saturation → slice-2 `-c 8192` rope artifact → clean `-c 10240` = nothink catches up). Two narrow survivors: **(a)** distilled > vanilla generator (mechanistically clean, but only matters if a scaffold regime exists at all); **(b)** format-native cross-family injection lifts accuracy +11pp/0-regressions (but not token-efficient vs a strong nothink). **The lane is a narrow, config-fragile, accuracy-critical-only lever — not the broad quality win the slice-2 headline suggested.** **FLAGGED FOR OPERATOR DECISION** (research-intake policy — not unilaterally closed): either (1) find a beneficiary/regime where nothink does NOT already saturate + deliver format-native (the only place a scaffold can clear the bar), or (2) bank as marginal and redirect the GPU to the residency + kernel levers. Artifacts: `/mnt/raid0/llm/tmp/cot-g1/{driver_g2,driver_g1ii,summary_g2,summary_g1ii,results_g2,results_g1ii_*}.*`.

- **G1 — scaffold lift (control AND treatment in one sweep).** Run **both** the control generator (Qwen3-4B-Thinking) and ≥1 distilled treatment (Qwable-v1) against the code beneficiaries. Two distinct questions: **(i) does *any* scaffold beat both baselines** token-normalized on ≥1 pair/suite (does scaffolding help at all)? **(ii) does the *distilled* generator beat the *control* generator** (did frontier-CoT distillation actually add value)? **KILL the lane if no scaffold beats BASELINE-ownthink** (thinking tokens aren't automatically additive — `feedback_qwen3x_enable_thinking_false`: `enable_thinking=false` won +33 pp on Qwen3.6/122B). **KILL the distillation thesis specifically if the distilled arm never beats the control** — then a vanilla thinker is all we need and no in-house tune is warranted.
- **G2 — cross-family transfer.** Does the lift survive Qwen-4B-Thinking scaffold → **gemma4** worker (not just same-family)? Epiphenomenal-CoT risk (arXiv:2606.13603) — injected reasoning may not causally drive the answer. KILL if lift is same-family-only.
- **G3 — residency + latency (only if G1+G2 pass).** Plan MI210 residency next to the frontdoor (fable5-window2-findings-05b/02 Gate R) and re-check the latency budget under realistic concurrency, since the scaffold is a serial pre-decode step.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-777 | Qwable-v1 (Qwen3.6-35B-A3B distill) | high | worth_investigating |
| intake-773 | Fable-5 → Qwen3-4B distill (adapter) | low | worth_investigating |
| intake-776 | Glint Fable-5-traces (un-redacted CoT corpus) | medium | worth_investigating |
| intake-775 | AliesTaha/fable-traces | low | not_applicable |
| intake-778 | Complete-FABLE.5-traces-2M | low | worth_investigating |

Prior art: Speculative Chain-of-Thought (arXiv:2504.19095) — small model drafts CoT, target consumes/corrects. Counter-signals: arXiv:2606.13603 (epiphenomenal CoT); OPSDC / `reasoning-compression.md` (reasoning can be net-harmful); our own `enable_thinking=false` +33 pp on Qwen3.6/122B.

## Dependencies / cross-cutting

- **`gpu-drafter-mi200-investigation.md`** — this lane is the **text-level alternative** to the spec-dec drafter farm; it deliberately sidesteps the N5 vocab/M-RoPE/GDN blocker class. If both land, the sidecar (quality) and the drafter (latency) are complementary, not competing.
- **`fable5-window2-findings-05b-mi210-inference-architecture.md`** — owns MI210 residency (Gate R), MTP/kernel work, and the frontdoor-residency bet G3 depends on.
- **`eval-tower-verification.md`** — scoring infra; the A/B points eval-tower suites at GPU `llama-server` endpoints.
- **`swarm-dataset-distillation.md`** — if the scaffold pattern works, an in-house SFT (seeded from the finite un-redacted Fable-5 CoT corpus, intake-776) could specialize a domain-aligned scaffold generator. Downstream, gated on G1/G2.
- **`routing-intelligence.md`** — a proven sidecar becomes a routing decision (which roles/queries get a scaffold).

### Reasoning-economics cluster (indexed together under `research-evaluation-index.md`)

This lane is **not standalone** — it is one point on the "**is added reasoning worth its cost?**" spectrum, and shares a measurement contract with its siblings:

- **`minddr-deep-research-mode.md`** — the **same gate, one weight up**: its **MD-9** ("does a multi-step deep-research pipeline beat direct-answer?") is our **G1** ("does an injected scaffold beat own-think?"). Share the EV-9 DRACO/MindDR scoring contract, suites, and token-normalization — do **not** re-derive them.
- **`reasoning-compression.md`** (OPSDC) — the cluster's **counter-evidence**: "much reasoning output is actively harmful; compressing it improves cost *and* quality" (Qwen3-14B 70.0→86.1% on MATH-500 from conciseness alone). This is the empirical case that a scaffold can be **net-negative** — it is exactly what G1's kill condition guards against, alongside epiphenomenal-CoT (2606.13603) and our `enable_thinking=false` +33 pp.
- **`per-request-reasoning-budget.md`** — the "how *much* reasoning per request" control; a proven scaffold becomes an input to that budget.
- **`rao-redel-substrate-spike.md`** — the heaviest (recursive-delegation) end of the same spectrum.

## Open questions (operator input welcomed)

1. **Which beneficiary roles** are the intended targets — worker_general only, or also the escalation gate / math-heavy routes?
2. **Injection mode** — assistant-prefix (arm 3, "continue its own thinking") vs context advisory (arm 4). This changes the experiment more than the generator choice does.
3. **Scaffold budget** — full CoT vs a short bulleted plan (cheaper, and may transfer better cross-family).
4. **Substitution vs addition** — is the scaffold allowed to replace the worker's thinking entirely, or augment it? Drives the token-accounting baseline.

## Key file locations

- Models dir `/mnt/raid0/llm/models/`. **Beneficiaries (on disk):** `gemma-4-26B-A4B-it-ORIG-Q4_K_M.gguf` (15.6 GB, v6-safe worker), `Qwen3.6-35B-A3B-MTP-Q8_0.gguf` (35.2 GB, shared by frontdoor + coder_escalation). **Generators (staged 2026-07-04):** `Qwen3-4B-Thinking-2507-GGUF/` Q8 (4.0 GB, control) + `Qwable-v1-GGUF/` IQ4_XS (17.6 GB) **and** Q8_0 (34.4 GB) (treatment: cheap-deploy + clean-quality arms). Cheap 4B treatment to add if wanted: `ermiaazarkhalili/Qwen3-4B-SFT-Fable5-Glint` (GGUF).
- MI210 HIP `llama-server`: `/mnt/raid0/llm/llama.cpp-mi210-hip/build-hip`.
- Eval tower: see `eval-tower-verification.md`.
- Kernel/experimental changes (if ever needed): `/mnt/raid0/llm/llama.cpp-experimental`.

## Reporting instructions

- Update this handoff at each gate (G1/G2/G3): record the (generator × beneficiary × suite) cells run, token-normalized deltas, and the gate verdict. Numbers are OBSERVATIONS until eval-tower-recipe-confirmed.
- Log via `agent_log.sh`; chronology to `progress/2026-07/`.
- On GO past G2, promote residency planning into `fable5-window2-findings-05b` (Gate R) rather than duplicating it here.

## Notes

All model-fit sizes and the MTP/tokenizer facts are from the 2026-07-04 research-intake deep-dive (sub-agent, HF public API + GGUF header parse, no full downloads). No inference was run to create this handoff. Handoff creation was directly operator-requested this session.
