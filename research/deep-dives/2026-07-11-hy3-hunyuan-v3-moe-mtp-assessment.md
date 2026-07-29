# Hy3 (Hunyuan v3) 295B/21B-active MoE + native MTP — feasibility & CPU-MTP assessment

**Date:** 2026-07-11
**Companion handoff:** [`handoffs/active/speculative-decoding-mtp-refresh.md`](../../handoffs/active/speculative-decoding-mtp-refresh.md) · [`handoffs/active/angelslim-techniques-evaluation.md`](../../handoffs/active/angelslim-techniques-evaluation.md)
**Intake entries:** intake-806 (`tencent/Hy3`) · intake-808 (`satgeze/Hy3-1M-GGUF`)
**Scope:** Architecture verification, GGUF/MTP port status (llama.cpp PR #25395), CPU feasibility on the EPYC 9655, credibility hardening, adoption recommendation. Does NOT run any bench — all performance figures are OBSERVATIONS pending an operator-gated measurement.
**Credibility:** architecture + host-feasibility math = **VERIFIED** (primary `config.json` + `df`); CPU-MTP speedup = **OBSERVATION-grade prediction** (author's Metal net-neutral datapoint + our prior MoE-A3B ~1.06× wall); model quality = **Tencent self-reported**, no third-party eval as of 2026-07-11.

---

## TL;DR

Hy3 is a real, RAM-feasible (~142–225 GB for IQ2_M/Q4_K_M + 256K KV, vs 1.1 TB host) **295B-total / 21B-active MoE with a native single-depth MTP head**. It is a legitimate **architect-tier capability candidate** but a **poor CPU-MTP-acceleration candidate**:

- Its **ungated** greedy MTP acceptance is only **~41% (IQ2_M) / 47% (f16)** — matching Tencent's official vLLM (46.7%). The widely-quoted **"88.2%" is a `p_min=0.75` confidence-gated figure** that a llama.cpp maintainer explicitly flagged as *not* a valid acceptance measure.
- On a **bandwidth-bound backend (Metal M3 Max), MTP is net-neutral** (23.27 vs 23.21 t/s). Our EPYC CPU decode is *also* BW-bound → predicted **net-neutral**, i.e. Hy3 *confirms* the MoE expert-verification wall our handoff already documents (~1.06× for MoE-A3B), it does not break it.
- Native context is **256K** (`config.json` `rope_type: "default"`, no scaling). The **"1M" is a community RoPE extension** by the GGUF packager (degrades to ~70%/needle at 1M).
- The GGUF+MTP path **works today** via `satindergrewal/llama.cpp@hy3-mtp`; upstream **PR #25395 is open and maintainer-engaged** (not stalled). **Disk headroom (~680 GB free), not RAM, is the real limiter** — download one quant.

**Net:** for the MTP mission of the companion handoff, Hy3 is a *negative* datapoint and low-EV for operator compute. As a *model-as-architect-candidate*, it is worth a separate, plain (no-MTP) quality bench **only if** the operator wants a new contender vs the incumbent Qwen3.5-122B.

---

## 1. Verified architecture (`tencent/Hy3/config.json`)

| Field | Value | Note |
|---|---|---|
| `model_type` / class | `hy_v3` / `HYV3ForCausalLM` | new arch line; not previously indexed |
| hidden size | 4096 | |
| layers | **80 + `num_nextn_predict_layers: 1`** | MTP layer = `blk.80` (6 `nextn.*` tensors) — matches intake claim exactly |
| experts | **192 routed, top-8, `num_shared_experts: 1`** | ≈ 9 active experts/token |
| expert dim | 1536 (`moe_intermediate_size`); layer 0 dense (`first_k_dense_replace: 1`, `intermediate_size` 13312) | |
| router | **sigmoid + expert bias** (`router_scaling_factor` 2.826) | DeepSeek-style |
| attention | **GQA 64 Q / 8 KV, head_dim 128, `qk_norm: true`** (QK-RMSNorm) | |
| context | `max_position_embeddings: 262144` = **256K native**, `rope_type: "default"`, `rope_theta` 11,158,840 | **no `rope_scaling`/YaRN** |
| vocab | 120,832; fullwidth EOS `<｜hy_eos:opensource｜>`; `<think:opensource>` reasoning (open tag prefilled); `reasoning_effort` = `no_think`/`low`/`high` | affects chat-template integration |

Active/total derivation reproduces **~21B active / ~295B total** — intake headline numbers are structurally consistent (VERIFIED-by-derivation).

## 2. MTP head design — why single-depth + BW-bound caps CPU gains

- The MTP head is a **single-depth** predictor (`num_nextn_predict_layers: 1`). Per llama.cpp maintainer `pwilkin`, only StepFun-3.7 currently does multi-layer drafting; Hy3 is one draft token/step.
- **Ungated greedy acceptance ≈ 41% (IQ2_M) / 47% (f16)**, cross-checked against Tencent official vLLM (bf16/TP4/B200) at **46.7%** — a dead match, so the port is faithful. The **"88.2%"** figure is what survives `--spec-draft-p-min 0.75` confidence-gating; maintainer `ruixiang63` objected that gating "truncates the draft tokens… does not provide a stable measurement for correctness."
- **Bandwidth-bound backends see no benefit:** author's **Metal M3 Max (128 GB, IQ2_M)** = **23.27 t/s with MTP vs 23.21 without** (net-neutral); his own explanation: the q8 MTP-head reads offset the accepted drafts. CUDA gains (+13% on 2×H200; +26–37% elsewhere; +40% Strix-Halo Vulkan) are compute-bound regimes.
- **21B-active / top-8-of-192** means multi-token verification widens the **expert union** touched per verify step → *more* memory traffic/step than gemma4's ~3.8B-active worker. Hy3 is a **larger instance of the worst-case MoE-MTP scenario**, not a fix for it.
- **CPU prediction (OBSERVATION):** EPYC decode is memory-BW-bound (our roofline priors); Metal net-neutral + our MoE-A3B ~1.06× wall ⇒ Hy3 MTP on the 9655 predicted **net-neutral to slightly negative**.

## 3. GGUF/MTP port status (llama.cpp PR #25395)

- **OPEN / REVIEW_REQUIRED**, +933/−4 across 16 files, author `satindergrewal`; adds `hy_v3` + the MTP path. **Actively progressing** — maintainer `pwilkin` is building companion parser support; his jinja `str.format` fix was cross-picked, which **retires the hand-patched chat template** (stock GGUF-embedded template now renders with `--jinja`). So intake-808's "requires the fixed `chat_template_llamacpp.jinja`" is becoming obsolete.
- **Arch-string caveat:** this PR uses `hy_v3`; earlier community converters used `hy-v3` (dash) and maintainers lean toward the dash. The final merged string may change → **pin a specific commit**; downloaded GGUFs may need a metadata rename.
- **CI red but plausibly environmental:** 5 SIGILL tests on ubuntu-x64 also fail on master HEAD; 1 windows jinja-hasher crash is pre-existing; local ctest 52/52. Not substance-blocking, but **unmerged**.

## 4. Host feasibility (VERIFIED disk/RAM)

KV derivation (config: 163,840 elem/token = 2·80·8·128):

| Quant | Weights | +256K KV (q8_0 ~42 GB) | Fits 1.1 TB? | On ~680 GB free disk? |
|---|---|---|---|---|
| IQ1_M | 62 GB | — (avoid: `no_think`-only, reasoning collapse) | — | yes |
| **IQ2_M** (rec.) | **100 GB** | **~142 GB** | ✅ | ✅ |
| Q4_K_M | 183 GB | ~225 GB | ✅ | ✅ |
| Q6_K | ~246 GB | ~288 GB (~566 GB @1M f16) | ✅ | ✅ (barely) |

- **RAM is a non-constraint** (GLM-5.2 UD-IQ2 ~238 GB precedent). **Disk is the tighter limit:** working FS is 81% used, **~680 GB free**, models dir already ~1.4 TB. Any *single* quant fits; you cannot hoard several. **Download IQ2_M only** for the first pass.

## 5. Credibility & reception

- **Quality = Tencent self-reported** (GPQA-D 90.4, SWE-Bench-Verified 78, blind-eval 2.67/4 vs GLM-5.1 2.51/4). No independent quality eval as of 2026-07-11.
- **Market reception (secondary/marketing, NOT a benchmark):** released 2026-07-06; reportedly #1 OpenRouter token usage / coding / tool-calls (~15.4% share) during a free-preview window; Nous Research + Kilo Code added access; Artificial Analysis pricing ~$0.12/M in, $0.43/M out.
- **The port has real independent corroboration:** vLLM official-reference acceptance match (46.7% vs 46.9%) + Metal & Strix-Halo replications + live maintainer scrutiny. The *implementation* is credibly faithful; only the *speedup framing* was corrected. → intake-808 credibility raised 2→3; intake-806 stays 2 (self-reported quality).
- **Genuinely new model line:** grep confirms no prior Hunyuan large-MoE *inference* entry — existing touchpoints are Hy-MT2 translation, AngelSlim toolkit (Hy3-FP8 already noted in `angelslim-techniques-evaluation.md`), and UniRL training. Registry has zero Tencent inference entries.

## 6. Recommendation

- **Do NOT spend operator compute to chase an MTP speedup** — the evidence is near-decisive it will be net-neutral on our BW-bound CPU.
- **Architect-candidate track is separate and optional:** if the operator wants a new architect contender vs Qwen3.5-122B, bench IQ2_M plain (no-MTP) on the review suite.

## 7. Operator-gated experiment protocol (single decisive run, if closure wanted)

1. Download **IQ2_M only** (100 GB, MTP head included; fits ~680 GB free).
2. Build `satindergrewal/llama.cpp@hy3-mtp` **CPU-only** at a **pinned commit**.
3. One **host-quiesced** run (`orchestrator_stack.py stop --all`): measure **ungated greedy** (`--spec-draft-p-min 0`) `--spec-type draft-mtp` t/s vs no-MTP baseline + a short correctness probe. Protocol per the gemma-4-31B gate: `taskset -c 0-95 numactl --interleave=all`, `-t 96 -fa 1`, OMP stack + `KMP_BLOCKTIME=10`, `temp=0 seed=42`.
4. **Predicted result: net-neutral.** This single run simultaneously (a) closes the CPU-MTP question and (b) confirms Hy3 runs on our stack → then reconsider as a plain architect candidate on a quality bench.

> MEASUREMENT.md: every number above sourced from external cards/PRs/threads is an OBSERVATION; none gates a keep/deploy/promote decision. Only the operator-gated run in §7, via a codified recipe, produces a decision-grade number.
