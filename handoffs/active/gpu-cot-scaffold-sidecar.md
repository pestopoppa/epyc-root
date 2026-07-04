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
