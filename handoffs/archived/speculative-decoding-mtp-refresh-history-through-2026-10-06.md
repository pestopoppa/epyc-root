# Speculative-Decoding / MTP Refresh — superseded history through 2026-10-06

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

---

# Appended 2026-10-06 (operator /wrap-up compaction)

Completed detail moved verbatim from the active handoff; line numbers refer to the pre-compaction file.

<!-- active lines 190-233 -->
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

<!-- active lines 309-363 -->
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

<!-- active lines 391-397 -->
## 2026-07-29 — intake Stage-4: KAT-Coder-V2.5-Dev artifact facts + a reusable preflight rule

_Via `/research-intake` Stage-4 (intake-916/917/932 lineage, AREX-Base as the counterexample). Zero-inference artifact reads; no bench implied._

- [x] **Record two durable artifact facts for KAT-Coder-V2.5-Dev.** ✅ 2026-07-29 — (a) its **tokenizer is byte-identical** to the deployed frontdoor — `sha256 5f9e4d49…cb42` on `tokenizer.json`, with matching `vocab.json` / `merges.txt` — so the **exact-tokenizer precondition for speculative decoding is SATISFIED** and needs no re-derivation. (b) its **MTP head is REMOVED**: `mtp_num_hidden_layers` 1→0 and **zero** `nextn`/`mtp` tensors across **31,333** revision-pinned weight-map entries. This is a regression versus the live frontdoor GGUF, which carries `blk.40.nextn.*`; any frontdoor-lane candidate manifest must therefore mark native MTP `absent` and cannot be compared as a like-for-like speculative-decoding replacement. A quality benchmark alone cannot detect that loss.
- [x] **Adopt the reusable preflight rule: verifying a fine-tune's architecture from `config.json` is UNSOUND.** ✅ 2026-07-29 — **AREX-Base retains `"mtp_num_hidden_layers": 1` while shipping ZERO mtp weights**: a config-level check reports "preserved" and is **wrong**. Before any architecture-dependent capability claim or candidate comparison, require a manifest record of (1) source/revision, (2) `model.safetensors.index.json` tensor-name/count evidence (or GGUF header tensor count plus relevant metadata key), and (3) explicit present/absent conclusion for every claimed MTP/draft head, vision tower, tied embedding, or other component. `config.json` may describe the expected shape only; it cannot satisfy the preflight or justify an architecture-equivalence claim. File this alongside the existing tensor-count-not-file-size rule — same failure family.
