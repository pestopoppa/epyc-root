# GPU CoT-Scaffold Sidecar — Preliminary Pure-GPU Research Lane

**Status**: SCAFFOLD-INJECTION **REOPENED + VALIDATED on reasoning-bottlenecked tasks** (2026-07-05 GPQA reversal). **The verdict is DISTRIBUTION-CONDITIONAL, not "dead."** The full arc: single-shot scaffold FALSIFIED on **code** (both strength regimes, transplanted reasoning ≠ transplanted capability) → self-debug/recursive **loop weak on code** (4% rescue, RL-ceiling arXiv:2504.13837) → **literature reads as a scaffold-injection dead-end** (2605.28913 amplifier-not-substitute, 2506.11578, 2504.13837) → **BUT the GPQA re-test on the RIGHT distribution REVERSED it**: on GPQA grad-science (N=48, wide caps) **scaffold-Qwable 73% vs nothink 48% = +12 (15 of 25 nothink-failures rescued, 3 regressions, 0 truncation)**, ownthink 67% (lower bound — 20/48 still truncated @16384, the 35B over-thinks). **The scaffold WORKS where the receiver has latent capability to amplify** — reconciling with "amplifier not substitute" (the receiver's latent capability is the gate: GPQA has it, library-code doesn't). Two operator methodology catches were decisive: **(1)** we had tested the WRONG distribution (bigcodebench = library-API, not reasoning); **(2)** caps were too tight (8192 truncated ownthink). Scaffold ≈ ownthink quality but far more token-efficient (Qwable concise/no-truncation vs the 35B overthinking). **CAVEAT:** needs a **Qwable-standalone GPQA control** (amplify vs Qwable-solves-and-35B-relays) — PENDING; deployment value holds either way. **VERIFIER/SELECTOR best-of-N is now a COMPLEMENTARY mode, NOT a replacement** — harness BUILT (`/mnt/raid0/llm/tmp/cot-g1/driver_verifier.py`, GenRM on cruxeval), ready to run, not yet launched (GenRM 2408.15240; GenPRM 2504.00891 — a 1.5B PRM beats GPT-4o as a judge; GPU-only via beneficiary-t/s rescale, reuses the EV-9 DRACO/MindDR scorer). Conditional deploy rule: reasoning-bound tasks where the beneficiary has latent capability (gate via `difficulty_band` + task-class); the autopilot reasoning-effort lever now has a validated positive instance. Distillation-adds-value + format-native-injection stand as components. (Lane originally operator-approved 2026-07-04.)
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

**⚠️ VERDICT CORRECTED (operator reframe, 2026-07-05) — the "marginal/config-fragile" read above is WRONG on metric, distribution, AND deployment:**
1. **Metric.** Gating on "token-efficient vs nothink's *average*" is the wrong test. When nothink *fails*, token cost is irrelevant — completing at 3× tokens beats failing at 1×. The data already shows the real value: the scaffold **RESCUED 3 (native cross-family) / 4 (distilled) tasks nothink failed outright, 0 regressions** = it *enables tasks nothink cannot handle*. The token-normalized average buried the rescues (only meaningful when both paths succeed).
2. **Distribution.** Code puzzles are where reasoning helps *least* (short, verifiable → nothink saturates). Rescue value lives in the hard tail + realistic multi-step agentic workflows (planning / escalation / cross-file debug) — the `/mnt/raid0/llm/cot-corpus/` distribution (783 real Claude thinking traces ~378K words), NOT HumanEval.
3. **Deployment.** Not always-on — a **CONDITIONAL** lever gated by **episodic memory** that learns per-task-class when the accuracy-for-tokens trade is worth paying. The scaffold joins a *family* of such levers (think-mode, MTP, model-escalation) the orchestration already toggles; the learned-routing-controller / strategy-store is where the when-to-deploy policy lives.
- **Both survivors are orchestration components, not throwaways:** distilled>vanilla → an in-house reasoner distilled on the in-domain corpus is a standing sidecar; format-native injection → a general cross-model primitive.
- **RE-SCOPED EXPERIMENT:** rescue-rate on hard/realistic tasks where nothink FAILS (0-regression gate), distribution = orchestration realistic eval tasks + corpus, deployment = episodic-memory-gated. **NOT closed — actively reframed toward autopilot/orchestration fine-tuning.** [[project_learned_routing_controller]] · [[feedback_seed_autopilot_via_strategy_store]]

**Fork 4 RESOLVED (operator 2026-07-05): EXTERNAL generators only — NO in-house training now.** All CoT-scaffold spec strategies use **Qwable-v1** (IQ4_XS + Q8_0 on disk) or the **fable5-distilled 4B** (`Qwen3-4B-SFT-Fable5-Glint`, q8_0 GGUF); the vanilla `Qwen3-4B-Thinking` stays only as the CONTROL bar. The **in-house-reasoner build is PARKED** (documented, not pursued): the operator confirms the MI210 *probably could* train (ROCm/PyTorch on gfx90a) but does not wish to explore it now; if ever revived it also needs prompt→thinking pair reconstruction from the session vault (corpus is thinking-text-only, 0 Fable-5). [[project_dgx_spark_target]]

### DENSE-BENEFICIARY GENERALIZATION (2026-07-05, GPQA n=10 each) — scaffold COST-efficiency generalizes; QUALITY benefit is HEADROOM-conditional
Campaign-tested dense vehicles vs the sparse-MoE 35B. OBSERVATION, n=10 single-sample.
| beneficiary | nothink | ownthink | scaffold | ownthink CPU-tok | scaffold CPU-tok(+GPU) |
|---|---|---|---|---|---|
| 35B-A3B (sparse MoE, 48q ref) | 48% | 67% | 73% | huge, 20 trunc | ~180 (+2073) |
| Qwen3.6-27B (dense-FFN-GDN) | 6/10 | 6/10 | **9/10** | **9041** (3 trunc) | **176** (+2073) |
| gemma-4-31B (pure dense) | 8/10 | 8/10 | 8/10 | **3049** | **98** (+2131) |
- **Scaffold COST-efficiency GENERALIZES (robust, arch-independent):** both dense models cap CPU tokens at ~100-175 vs their own overthinking (3049-9041) = a 20-50x CPU-token reduction, reasoning offloaded to GPU.
- **Scaffold QUALITY benefit is HEADROOM-CONDITIONAL:** big on the 27B (6→9 — overthinks catastrophically + weak nothink), NEUTRAL on gemma-31B (8=8 — already at its ceiling, strong nothink). Lifts quality only where the beneficiary is weak-and-overthinking.
- **Both dense models: ownthink ≈ nothink** (6=6, 8=8) — own reasoning is wasted CPU cost with NO quality gain; the sparse-MoE 35B DID gain (+19pp). n=10 caveat; suggestive that sparse-MoE reasons more productively on GPQA.
- **cruxeval verifier on dense too (n=6): qwen27b gap 0, gemma31b gap 1 unrecovered** → confirms poor-testbed; math verifier is the fair test.

### GPQA REASONING DIAGNOSTIC (2026-07-05, wide caps) — REVERSAL: the scaffold WORKS on the RIGHT distribution
Operator methodology catches (wrong bench: code/library-API not reasoning; + too-tight 8192 cap truncating ownthink) reversed the earlier "scaffold dead-end." GPQA grad-science, N=48, 35B beneficiary, ownthink 16384 / scaffold-gen 8192, deterministic MC scoring, seed 42. OBSERVATION-grade.
| arm | pass | vs nothink | note |
|---|---|---|---|
| nothink | 23/48 (48%) | — | |
| ownthink | 32/48 (67%) | +9 | 20/48 STILL truncated @16384 → LOWER BOUND (35B over-thinks, doesn't converge) |
| **scaffold-Qwable** | **35/48 (73%)** | **+12 (+25%)** | **0 truncated; 15 of 25 nothink-failures rescued / 3 regressions** |
- **The scaffold WORKS on reasoning-bottlenecked tasks** (+12, 15 rescues/3 regr). REVERSES the single-shot falsification (mode_advantage_hard code + Qwable→gemma), which was **DISTRIBUTION-SPECIFIC** (code/library-API/capability-limited — nothing to amplify).
- **Reconciles with the literature ("amplifier not substitute", arXiv:2605.28913):** the RECEIVER's latent capability is the gate. GPQA (grad-science) → the 35B HAS it → scaffold amplifies (+12); bigcodebench (library-API knowledge gaps) → nothing to amplify (self-debug loop 4%).
- **Scaffold ≈ ownthink on quality but FAR more efficient:** +3 over ownthink (~parity given ownthink's 20/48 truncation under-count), with **0 truncation** because Qwable reasons concisely+completely in 8192 while the 35B OVERTHINKS (>16k, non-convergent). GPU reasoner delivers the benefit at a fraction of the beneficiary token cost, dodging the overthinking-truncation trap.
- **CAVEAT (needs a control):** on MC the +12 could be "35B latent capability elicited" OR "Qwable solves it + 35B relays the choice." **A Qwable-standalone GPQA control disambiguates** — but deployment value (the beneficiary server answers better) holds either way; both readings are literature-endorsed (amplify vs standalone-reasoner).
- **Qwable-standalone CONTROL (2026-07-05) — the scaffold is DOMINATED by standalone routing (walks back "amplification"):** GPQA four-way: nothink 48% / 35B-ownthink 67% / **Qwable-standalone 77%** / scaffold(Qwable→35B) 73%. **Qwable-standalone (77%) > scaffold (73%): the 35B DEGRADES Qwable −2** (scaffold-right/Qwable-wrong 3, Qwable-right/scaffold-wrong 5). The +12 vs nothink was NOT amplification — **Qwable is simply the better GPQA reasoner**, and the scaffold is a LOSSY delivery of its reasoning through the 35B. **Deployment rule (RE-CONFIRMS the literature's #1 pattern): route reasoning-heavy tasks to the strong reasoner STANDALONE** (Qwable), NOT scaffold-inject into a weaker beneficiary. The scaffold is justified ONLY when the beneficiary must be the answerer (tools/context/deployed role Qwable lacks) — there it's a lossy-but-positive lift over the beneficiary's own reasoning. This ALSO strengthens the verifier/selector case: since Qwable is genuinely strong, grading/selecting is likely higher-value than injecting.
- **VERIFIER/SELECTOR full result (cruxeval, 35B, 2026-07-05) — 0% gap recovery; likely a POOR testbed.** Qwable grades 5 candidates from the 35B-A3B (predict-output, N=60, correctness-first prompt). pass@1 55% / random-of-5 51% / **verifier-selected 55% (=pass@1) / oracle pass@5 65%. GAP RECOVERED 0/6 = 0%.** Selection-acc 85% is INFLATED — confirms the easy questions but recovers NONE of the 6 rescuable ones. The 5q smoke (gap-rec 1.00) was small-sample-misleading (n=5→n=60 REVERSED — a lesson). **Same "wrong bench" lens as the GPQA-scaffold catch: cruxeval is likely a poor verifier testbed** — tiny diversity gap (35B traces to the same output → only 6 rescuable) + verification requires Qwable to ALSO trace the code (not a checkable-answer domain). GenRM/GenPRM gains were on MATH (diverse solutions + verifiable answers). **Fair verifier test = a MATH bench (AIME/MATH) — PENDING**, analogous to the GPQA re-test that rescued the scaffold. Dense-vehicle smokes (running) use cruxeval too → share this caveat.
- **CoT-scaffold lane end-state: works-but-dominated.** The scaffold beats the beneficiary's own reasoning but is dominated by standalone routing → it's a FALLBACK (beneficiary-must-answer cases), not the primary lever. Primary levers on reasoning tasks: (1) standalone strong-reasoner routing, (2) verifier/selector best-of-N [next]. 
- **CoT-scaffold lane REOPENED + VALIDATED on reasoning-bottlenecked tasks.** Conditional deploy rule: reasoning-bound tasks where the beneficiary has latent capability (gate via difficulty_band + task-class). The verifier/selector is now a COMPLEMENTARY mode, not a replacement. The autopilot reasoning-effort lever now has a validated positive instance.
- **Verifier/selector harness BUILT (not yet launched):** `/mnt/raid0/llm/tmp/cot-g1/driver_verifier.py` — GenRM best-of-N on cruxeval, ready to run. With the reversal, it runs ALONGSIDE the reopened scaffold lane, not instead of it.
- **gemma-4-26B IQ4_XS verified (13.6 GB)** — mid-precision beneficiary arm (between the deployed Q4_K_M 15.6 GB and the Q8 clean-quality arm); mid-precision probe queued.

### RESEARCH (2026-07-05) — scaffold-injection is a KNOWN dead-end; the working GPU-reasoner mode is VERIFIER/SELECTOR
Public-literature survey CONFIRMS our negatives as the consensus:
- **"Reasoning that Travels" (arXiv:2605.28913):** transplanted reasoning is a "capability AMPLIFIER, not a capability SUBSTITUTE" — helps capable receivers, "cannot overcome fundamental performance gaps in weaker models"; transfer success tracks the RECEIVER's base capability. = our "transplanted reasoning doesn't transplant capability."
- **Small-planner-degrades-executor (arXiv:2506.11578):** small-model plans drop a LARGER executor BELOW its baseline. = our single-shot 4B→35B derailing.
- **RL-ceiling (arXiv:2504.13837):** self-refinement bounded by base pass@k; more loops don't cross the ceiling. = our self-debug loop (4%).
- **Reasoning is ELICITED not INSTALLED** (LIMO 2502.03387, s1 2501.19393, structure>content 2502.07374).
- **Learnability gap (arXiv:2502.12143):** below ~3–7B long-CoT HURTS → our **4B-Fable5 is AT the boundary** (mix-distillation is the remedy); Qwable-35B is above it.
**THE ONE WORKING "help another model" MODE (untested by us): VERIFIER / SELECTOR.** The reasoner does ITS OWN task — grade/rank/verify the beneficiary's candidates (best-of-N), never transplanting capability. **GenRM (2408.15240):** BoN 5%→45%, 73%→93%. **GenPRM (2504.00891):** a 1.5B generative PRM BEATS GPT-4o as a judge; 7B beats 72B. Sidesteps the transplant problem, fits GPU-reasoner+CPU topology, **plugs into the existing EV-9 DRACO/MindDR scorer.** HIGHEST-VALUE untested pattern.
**Reframed GPU-reasoner role:** (1) **standalone** — route reasoning-heavy tasks (math/code/STEM) to it; (2) **verifier/selector (best-of-N)** over CPU-model outputs. NOT scaffold-injection (dead-end, confirmed by us AND the literature). Offline: Qwable can generate CoT to fine-tune CPU models (data-gen). See also [[project_reasoning_trace_corpus_landscape]].

### SELF-DEBUG LOOP result + reasoning-effort framing + VERIFIER/SELECTOR next (2026-07-05)
**Self-debug loop** (35B, bigcodebench 60q, write→execute→feed-error→revise, MAX_ITERS=3, -fa on): 1-shot 22% → loop-final 25% (net +2); **RESCUES 2/47 = 4%**; effort curve **FLAT** (both rescues at iter 2, none at 3). The recursive mechanism is also weak — matches RL-ceiling (arXiv:2504.13837): self-refinement is bounded by the base's pass@k, so loops don't cross the ceiling. **CAVEAT (operator):** bigcodebench is library-API-heavy (knowledge gaps, not reasoning) — possibly the wrong distribution; the **GPQA reasoning-diagnostic** (nothink vs **OWNthink** vs scaffold-Qwable, 35B) is the fundamental "is the distribution the issue" test [in flight → result decides whether the scaffold closes bench-independently, or whether ownthink helps but the transplant doesn't].
**Reasoning-effort framing (operator):** loop-depth = a "reasoning effort" knob = the local analog of cloud `reasoning_effort` / thinking-budget. Unifies {nothink → think-budget → single-shot scaffold → loop-depth → model-escalation} on ONE effort axis → an operator **FLAG** + an autopilot per-task-class **TUNABLE** (the existing 4D Pareto + `per-request-reasoning-budget` plumbing). Even the negative loop run yields the calibration data (rescue-vs-effort curve, flat here).
**VERIFIER/SELECTOR = recommended next GPU-reasoner experiment (operator 2026-07-05, GPU-only):** Qwable **grades/ranks N candidate answers** from the beneficiary (best-of-N), never transplanting capability (GenRM 2408.15240; GenPRM 2504.00891 — a 1.5B PRM beats GPT-4o as a judge). **Testable ENTIRELY on GPU** — host the beneficiary on GPU + artificially **RESCALE its t/s** to evaluate the CPU-cost tradeoff pivots (same rescale insight as the loop; no CPU needed). Reuses the **EV-9 DRACO/MindDR scorer**. Run immediately or after the incremental levers land.

### RESCUE-RATE experiment RESULT (2026-07-05, optimized -fa on) — single-shot scaffold on a STRONG beneficiary FAILS
Suite `mode_advantage_hard` (60q, code/comp/reason/synth ×15, nothink UNSATURATED at 41/60). Beneficiary 35B-A3B-Q8 (GPU). Generators: 4B-Thinking (control), Qwable-v1 IQ4 (distilled). Metric = rescue rate (nothink-fails→scaffold-completes) + 0-regression gate. OBSERVATION (single-sample seed=42). *(Speed note: initial run was `-fa off` → ~12 t/s; corrected to `-fa on` → ~92 t/s, both models; the earlier "Qwable too slow" was misconfig, NOT the model — Qwable IQ4 decodes ~96 t/s = as fast as the beneficiary.)*
| arm | ALL | code | comp | reason | synth | vs nothink |
|---|---|---|---|---|---|---|
| nothink | 41/60 | 14 | 9 | 4 | 14 | — |
| scaffold-4B | 32/60 | 10 | 8 | 1 | 13 | **0 resc / 9 regr / net -9** |
| scaffold-Qwable | 39/60 | 13 | 8 | 3 | 15 | **2 resc / 4 regr / net -2** |
- **Distillation CONFIRMED:** Qwable fixes 9 of the 4B's derails (4B fixes 2 of Qwable's); net -2 vs -9. Strong same-class generator derails far less.
- **But single-shot scaffold is NET-NEGATIVE even with Qwable.** comp+reason slice (nothink fails 17/30): 1 rescue, 3 regressions. On reason alone Qwable 3/15 < nothink 4/15.
- **Structural reason:** the 35B beneficiary is ALREADY as strong a reasoner as Qwable (a distilled 35B) → equal-strength injected reasoning adds no capability → nothing to rescue, only derail. Scaffold rescues ONLY if generator > beneficiary's own reasoning.
- **CPU-cost mechanism works** (scaffold-Qwable beneficiary 641 tok/q vs nothink 1071 = -40% CPU decode) **but at a quality loss** → not favorable on THIS pairing.
- **VERDICT (single-shot, strong beneficiary): FALSIFIED** (net-negative even distilled).

**Follow-up — generator>beneficiary (Qwable→gemma-26B, 2026-07-05, -fa on, format-native): ALSO FALSIFIED.** gemma-nothink 39/60 vs +Qwable-scaffold 36/60 = **net -3; 1 rescue of 21 available nothink-failures (5%), 4 regressions**; clean injection (no channel leak); no CPU savings (gemma 917 vs 920 tok/q). → **SINGLE-SHOT CoT-scaffold injection is FALSIFIED as a rescue lever in BOTH regimes (gen≈beneficiary AND gen>beneficiary).** Mechanism: **transplanted reasoning does not transplant capability** — handing a model a pre-made reasoning trace neither unlocks tasks it fails (20/21 gemma-failures unrescued) nor is cost-free (occasional derail). Independent of whether the beneficiary is stronger or weaker than the generator.

**LANE STATUS: single-shot CLOSED (clean negative, both regimes).** Only untouched mechanism = the **recursive reason↔execute LOOP** (bet: ground each step in execution feedback, not hand over reasoning) — a fundamentally different + bigger build, prior LOWERED by these negatives, treated as a separate OPERATOR-GATED investment (not autonomously spun up). Distillation-adds-value + format-native-injection findings stand as components IF the loop is ever built. Speed levers (residency/kernel) are the clearer path to the overarching goal.

### FORMAL OBJECTIVE (operator 2026-07-05): minimize BLENDED wall-clock at quality-parity
The lane's value is NOT "scaffold beats nothink" — it is "**approximate ownthink at lower blended wall-clock**," where the beneficiary runs on slow CPU (token efficiency paramount) and the reasoning is offloaded to the fast GPU. Per task:
```
T_scaffold = N_gen/r_GPU(gen)  +  N_gen/r_CPU_prefill(ben)  +  N_ans/r_CPU_decode(ben)
T_ownthink = (N_reason + N_ans)/r_CPU_decode(ben)
```
**Objective: minimize T_scaffold s.t. quality ≥ quality-parity(ownthink).** The win comes from the `r_GPU/r_CPU` ratio (fast small GPU model vs slow large CPU model) — moving reasoning off CPU-decode pays even at higher token count, as long as the beneficiary's own CPU-decode `N_ans` collapses (interim CONFIRMS it does: scaffold beneficiary answers ran 5–150 tok vs nothink ~1000). Prefill of the injected hint is the tax (CPU, but batched/cheap).
**Search space (the levers):** `generator {4B, fable5-4B, Qwable} × depth {setup-only, full} × mode {advisory, prefix} × gen-budget × per-task-class gate`. fable5-4B (high r_GPU, distilled) and Qwable (low r_GPU, stronger) are distinct frontier points. **Interim structural finding:** a generator WEAKER than the beneficiary's own reasoning (4B < 35B) drags quality *below nothink* (imposes wrong conclusions) — so the generator must ≳ the beneficiary's own reasoning, OR the scaffold must be setup-only/advisory so it doesn't import conclusions.
**autopilot — this IS its EXISTING objective, NOT a new one (verified 2026-07-05):** `safety_gate.objectives() = (quality, speed, -cost, reliability)` is a 4D Pareto (`pareto_archive.py`), and `q_reward.compute_reward` already penalizes wall-clock (`cost_ratio = actual_elapsed/expected_elapsed`, applied ONLY to correct answers = minimize-cost-subject-to-correctness). So the scaffold's blended GPU+CPU cost surfaces directly as the speed/cost axes autopilot scores per trial (end-to-end request wall-clock; GPU-reasoning time is part of the request path). **The work is NOT building a cost-aware optimizer — it is registering the scaffold as a LEVER** (`capability_registry` `prompt`-kind row, beside `per_role_enable_thinking`) so the existing 4D-Pareto + cost-penalized reward + episodic gating evaluate it. The recursive loop = one more action in the same optimizer. The manual sweep characterizes the (quality, speed, cost) datapoints that Pareto front ingests. [[feedback_accuracy_token_tradeoff_rescue_metric]] · [[project_learned_routing_controller]]

### RECURSIVE extension (operator 2026-07-05): single-shot scaffold → interleaved GPU-reason ↔ CPU-execute LOOP
For long-horizon/complex tasks the scaffold is not one-shot. Loop: **GPU reasoner emits next step/plan → CPU beneficiary (nothink) executes it → GPU reasoner reads the concrete output → next step → …**, recursively (a hierarchy of sub-tasks, each its own reason↔execute cycle). This is a **device-split planner-executor** = the stack's existing `graph_router` `react`/`repl` mode with the THOUGHT step device-pinned to the GPU and the ACT step to the CPU. All token-heavy reasoning lives on the cheap fast GPU; the expensive CPU model only ever executes concrete steps in nothink.
- **Self-correction (attacks the single-shot derailing — the key insight):** the one-shot 4B imposed a wrong *conclusion* the 35B swallowed unchecked. In the loop the reasoner proposes only the *next step*, the strong CPU model executes it, and the reasoner is then **grounded by the actual output** before the next step — so a weak reasoner's error is bounded per-round + corrected by execution feedback instead of compounding. The recursion may RESCUE the weak-generator case single-shot could not. **HYPOTHESIS, untested.**
- **Cost:** blended wall-clock becomes a multi-round sum; the per-round prefill tax `N_gen/r_CPU_prefill` recurs + GROWS as context accumulates → KV-persistence on the CPU beneficiary + shipping only deltas to the GPU reasoner is what keeps it bounded (the ceiling on how deep recursion pays). Stop-condition + depth-cap fall out of the quality-constrained objective (recurse to quality-parity or budget).
- **Autopilot:** the loop-control policy (reason / execute / recurse / stop, per state) is the recursive generalization of the per-task-class gate over the same lever-space.
Sequencing: characterize single-shot first (is 1 round net-positive on blended cost?); the loop is the bigger build and inherits per-round behavior — but its self-correction channel is the thing that could make it beat single-shot. · [[feedback_accuracy_token_tradeoff_rescue_metric]]
- **✅ REPORTED → single-shot lane CLOSED (2026-07-05).** The re-scoped rescue-rate experiment (`mode_advantage_hard`, nothink vs format-native scaffold, rescue metric + 0-regression gate) RAN to completion and, together with the favorable-regime (Qwable→gemma-26B) follow-up, **falsified single-shot injection in both regimes** (see the "RESCUE-RATE experiment RESULT" and "LANE STATUS: single-shot CLOSED" sections above — this bullet is now historical). The infra it used (~80% pre-built: `mode_advantage_hard` + `core_v2_select`; `iq2_arch_eval.py` no-think driver; `think_harder.py` scaffold-boolean; `difficulty_signal.py` band; `episodic.db` `q_value`/`hypothesis_graph`; `capability_registry.yaml` lever registry) and the 4 integration forks (static-band vs learned head; reward home; proactive vs reactive; distillation external-vs-build) carry over **only** to the recursive-loop investment, which is operator-gated. The lever registration is still meaningful IF the loop is built.

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
