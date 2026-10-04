# Quant-variant survey for the two CPU models: DS41 and Q38FN (2026-10-03)

**Source**: `/mnt/raid0/llm/tmp/quant-variant-survey-20261003/report.md` (scratch; copied verbatim below the line apart from path clarifications)
**Date**: 2026-10-03
**Author session**: ak-ds41-main
**Status**: research review — not a measurement claim. Figures labelled computed/inferred are arithmetic, not runs.
**Operator decisions (2026-10-03/04)**: (a) IQ\*_K/KS self-quant for Q38FN (Qwen3.8-Flash-Next) is allowed "exceptionally if justifiable" — this lifts the no-requant constraint stated below for that one option only; (b) DS41 (DeepSeek-V4.1-Flash) lossless MXFP4 experts: "plan it".
**Companion**: [cpu-quant-research-20261003.md](cpu-quant-research-20261003.md) (follow-up that corrects §3 and §4 of this survey).
**Paths**: relative paths are relative to `/workspace` (root repo), except `ggml/…` and `src/…`, which are relative to the experimental tree `/mnt/raid0/llm/llama.cpp-experimental-fastload-ds41-20260925`. Anything under `/mnt/raid0/llm/tmp/` or `/tmp/claude-1000/` is **scratch** and may be gone.

---

Scope: read-only. I used the HF API, READMEs, a few small text and image files (two KLD/PPL plots and two RCO allocation lists), and GGUF headers from local files. No model downloads, no model loads, no inference. Operator constraint: no requantizing on our side. A swap to a published variant of equal quality is allowed.

## TL;DR

| Rank | Option | Expected decode gain | Quality risk | Effort | Verdict |
|---|---|---|---|---|---|
| 1 | **Q38FN: UD-IQ4_XS → `bartowski/Qwen3.8-Flash-Next-GGUF` IQ4_XS** (97.68 GB, imatrix built on BF16, same type policy as our local "uniform" speed control) | **+10–15%** at N=1 (measured pre-BIOS with the local uniform file; post-BIOS and the MTP-d4 serving shape are unmeasured) | **medium, unmeasured.** Dense goes Q8_0 → IQ4_XS/Q5_K. No published KLD for this file. | speed: 0 download, about 25 min. Quality: Q8_0 reference (188 GB) plus 97.7 GB | **Do this X0** |
| 2 | Q38FN: `ISTA-DASLab/...-GSQ-RCO-GGUF` IQ3_S (83.6 GB, standard GGUF types, claims task parity with BF16) | unknown. −12% bytes/token vs UD, but BF16 hc tensors and many non-iqk types | medium (task scores only, no KLD) | 83.6 GB | second arm only if #1 fails on quality |
| 3 | DS41: lossless MXFP4 routed experts (JigSawPT / mxxm-t / smalinin repacks of the released FP4 blocks) | ≤ +2% (−3.5% bytes per N=3 verify) | **negative**: better than the current file, because Q4_K is a lossy requant of FP4 | ~300 GB download (does not fit in the 243 GB free), container/loader surgery, iqk allowlist work | park. Below the 3.4–4.5% admission floor |
| 4 | DS41: any published variant with lower-bit **dense** tensors and the same Q4 experts | — | — | — | **none exists in a format our loader accepts** |
| 5 | EXL3 on CPU (either model) | Q38FN: +0–6% over a uniform IQ4_XS. DS41: ≤ MXFP4's gain, and lossy | Q38FN 3.05 bpw ≈ UD quality (turboderp harness). DS41: all published branches sit below the FP4 source bpw | 6–10+ sessions (importer, ggml type, dense path, n-gram rows, graph) | **no.** INF-71 reopen trigger not met |

## 1. Models in use, verified locally

### DS41: DeepSeek-V4.1-Flash
- **Served file** (from `/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/inputs/ds41-cpu-t48-dspark.launch.json`): `/mnt/raid0/llm/models/antirez/deepseek-v4.1-flash-gguf/DeepSeek-V4.1-Flash-Q4.gguf` (518.6 GB, arch `deepseek41`, imatrix `bootstrap-calibration-8192.dat`).
  - The DSpark draft is `-md .../DeepSeek-V4.1-Flash-DSpark.gguf` with `--spec-draft-n-max 2`, so the verify step is N=3.
- **Native checkpoint precision** (`models/deepseek-ai/DeepSeek-V4.1-Flash/config.json`): `quant_method fp8`, block 32×32, `ue8m0` scales, **`expert_dtype: fp4`**.
  - The routed experts are therefore natively MXFP4-class (E2M1 + E8M0 per 32 = 4.25 bpw), and dense is FP8.
  - antirez's **Q4_K experts (4.5 bpw) are a lossy requant of 4.25-bpw FP4 source**.
  - The **Q8_0 dense (8.5 bpw) ≈ the FP8 source**.
- **Header census** (all 1,065 tensors):

| group | type | GB in file | read per token? |
|---|---|---|---|
| routed experts gate/up/down (384 × 40 layers) | Q4_K | 305.8 | 6/384 ⇒ **4.78 GB/token** |
| engram tables ×2 (`e4m3_e8m0_32_row264`) + token_embd (F16) | I8 / F16 | 204.1 | row gather only (negligible) |
| dense: attn_q_b 1.78, attn_output_b 1.78, attn_output_a 1.43, shexp 1.50, attn_q_a 0.28, attn_kv 0.11, output 0.70 | Q8_0 | **7.59** | every token |
| F16/F32 2-D: engram_kv 0.63, ffn_gate_inp (F32) 0.31, hc_*_fn, indexer, compressor | F16/F32 | 1.15 | every token |

- **Bytes read:**
  - **N=1:** 13.51 GB/token, 65% dense (Q8_0 + F16).
  - **N=3 verify (served), no expert overlap:** 23.07 GB, 62% experts.
- **What-if byte deltas** (computed, not measured):

| variant | N=1 | N=3 verify |
|---|---|---|
| MXFP4 experts | −2.0% | −3.5% |
| dense Q6_K | −12.8% | −7.5% |
| dense Q5_K | −19.8% | −11.6% |
| MXFP4 + dense Q6_K | −14.8% | −11.0% |

- **Why the realised gain is smaller than the byte delta:** the profile in `/mnt/raid0/llm/tmp/cpu-lowbit-seeds-20261003/hypotheses-fable-cpu.md` (scratch) §0 shows only ~50% of cycles streaming (Q8_0 gemm4xN ≈ 24%, Q4_K X4_T ≈ 26%). libgomp spin takes 37.5% and a small-op sync floor about 10%. At roughly 0.5 bytes-elasticity, even dense Q6_K would give about +3–4%, which sits at the 3.4–4.5% admission floor.

### Q38FN: Qwen3.8-Flash-Next (arch `qwen4exp`: 48 layers, 512 experts, 10 active, expert FFN 640)

| file | experts | dense | per-token bytes |
|---|---|---|---|
| **UD-IQ4_XS (served)** 93.68 GB | IQ3_S gate/up ×47, IQ4_XS ×1, IQ4_NL down ×43, Q8_0 down ×5 | **Q8_0** (attn_qkv 1.00, ssm_out 0.60, attn_gate 0.60, attn_q 0.40, hc 0.67, shexp 0.25 …), output Q6_K | **dense 4.64 + experts 1.16 = 5.80 GB** |
| IQ4_XS-uniform (local) 98.39 GB, quant-from-UD speed control (OP-32) | IQ4_XS gate/up, IQ4_NL down ×42, Q5_1 ×6 | IQ4_XS, attn_qkv Q5_K, output Q6_K | **dense 2.85 + experts 1.30 = 4.14 GB** (matches INF-70's 4.16) |

- The per-layer n-gram table (`per_layer_token_embd`, IQ4_NL, 28.8 GB) is gather-only in both files.
- **Q38FN is dense-dominated per token** (UD: 80% dense), so the dense precision is where a variant gains or loses speed.
  - The OP-32 control measured UD → uniform at +15.2% (+10.5% under clean placement) for −29% bytes/token.
  - That gives an **observed bytes-elasticity of about 0.4–0.5** on this model.
- **Kernel-path note:** `ffn_down_exps` has rows of 640, so it can only use 32-block types (IQ4_NL/Q5_1/Q8_0/MXFP4).
  - IQ4_NL and MXFP4 are **not** in `iqk_typeA_supported` (`iqk_dispatch.cpp:128`).
  - They run on mainline CPU_REPACK `iq4_nl_8x8` / `mxfp4_8x8` (AVX2), not iqk (`repack.cpp:4548-4568, 4709-4740`). In both Q38FN files that covers roughly a third of the expert bytes.
  - An iqk IQ4_NL/MXFP4 kernel already exists in `iqk_gemm_legacy_quants.cpp` but is unreachable from the allowlist. That is a kernel-side item, not a quant swap, and it matters for any MXFP4 option.

## 2. Published alternatives (HF API, 2026-10-03)

### DS41: no drop-in variant with lower-bit dense
- **Format compatibility is the blocker.** Our loader (`src/models/deepseek41.cpp:26-40`, written for the antirez artifact) accepts only `engram.encoding = e4m3_e8m0_32_row<N>` and the HF-style KV names. Every other converter stores the engram tables differently, so their files will not load without adapter work:
  - vcruz305 / Solstice-AI / AMAImedia (upstream PR #28696 converter): engram follows the quant rung.
  - smalinin: Q8_0 or Q5_K engram.
  - JigSawPT: raw fp8 plus separate scale tensors.
  - mxxm-t: engram ~49 GiB per table.
- **antirez publishes only Q2 and Q4.** Q2 is IQ2_XXS gate/up + Q2_K down with the same Q8 dense (340.6 GiB); Q4 is the current file.
  - Q2 is not equal quality. Lucebox measured KL top-256 vs the FP4 teacher at 0.260, top-1 78.3%, PPL 9.71 vs 8.45.
  - Q2_K is also not on the iqk path.
- **Files that do lower the dense precision come only with Q2/Q3 experts.** Example: smalinin `Q2_K_Protected-Q8`, with Q6_K attention and output, Q5_K/Q6_K shexp, Q2_K/Q3_K experts, 413 GB. That is lower quality, uses another converter, and is CUDA-tested only.
- **Lossless-expert repacks of the released FP4 experts:**
  - **JigSawPT/DeepSeek-V4.1-Flash-GGUF:** MXFP4-engram, 502 GB, "480/480 identical" block check, Q8_0/BF16 dense.
  - **mxxm-t:** MXFP4, 375.8 GiB.
  - **smalinin MXFP4:** 120 MXFP4 + 332 Q8_0 tensors, Q8_0 engram, 508 GB.
  - Experts at 4.25 bpw vs 4.5 means fewer bytes and *higher* fidelity than the current file.
  - The catch: the container is incompatible, ~300 GB of expert shards would have to be fetched, and MXFP4 runs on mainline AVX2 repack, not iqk.
- No KLD table exists for any Q4-class DS41 file. Lucebox's table covers only Q2-class files.

### DS41: EXL3

| repo | bpw | size | notes |
|---|---|---|---|
| Mia-AiLab 2.9 / 3.0bpw | 3.02 decoder, head 6, mtp 4 | 196 / 204 GiB | **engram tables not included** (use original shards 47–48, ~190 GiB) |
| dealignai 2.9bpw | 2.9 | 196 GiB | abliterated |
| diffbot 3bpw | 3 | 309 GiB | |
| bot-lab-21 3.5bpw | 3.5 | 428 GiB | |
| coolbho3k 3bpw | 3 | 592 GiB (4 branches) | |
| sfxnz | 2.0bpw MCG branches | — | |
| satgeze / kotobalabs | 2.0bpw | 242 GiB | abliterated |

- No turboderp DS41 EXL3 exists (turboderp has V4-Flash-0731 at 2.04–3.04 bpw).
- **Every DS41 EXL3 is ≤ 3.5 bpw, i.e. below the 4.25-bpw FP4 source on the experts.** All of them are lossy relative to the released model, and none publishes a KLD.
- The runtime is exllamav3/vLLM on CUDA.

### Q38FN: GGUF
- **unsloth:** UD-IQ1_S 72.6 · UD-IQ1_M 74.5 · UD-Q2_K_XL 78.9 · UD-IQ3_XXS 82.0 · UD-Q3_K_XL 90.0 · **UD-IQ4_XS 93.7** · UD-Q4_K_XL 111.3 · UD-Q5_K_XL 158.3 · UD-Q6_K_XL 169.2 · Q8_0 188.2 · BF16 354 GB. There is no non-UD IQ4_XS, and the README has no KLD table.
- **bartowski** (llama.cpp b10665, imatrix on BF16, standard type policy, arch `qwen4exp`):
  - **IQ4_XS 97.68 GB** ≈ our local uniform 98.39 GB. The uniform file was built with the same `llama-quantize` IQ4_XS policy, so this is the published, quality-representative version of the speed control.
  - Also available: IQ4_NL 100.3, Q4_0 100.6, Q4_K_S 113.1, Q4_K_M 119.6, Q8_0 188.3. No KLD table.
- **ISTA-DASLab GSQ-RCO** (standard GGUF types, per-tensor RCO allocation lists published): IQ3_S 83.6 GB / IQ3_XXS 75.8 GB.
  - Task-panel claims: IQ3_S matches or beats BF16; IQ3_XXS reaches 99.4% of the BF16 task average. No KLD.
  - From their allocation file joined to our tensor shapes (computed): IQ3_S **5.09 GB/token** (dense 4.11, experts 0.98) and IQ3_XXS 4.61 GB/token.
  - The dense side stays heavy because every `hc_*` tensor is BF16. The files use BF16, IQ4_NL and Q2_0 types, all outside iqk.
- **AesSedai** (KLD vs BF16 in their own harness): IQ4_XS-mix (Q8_0 dense / IQ3_S experts) 0.076, Q4_K_M 0.034, Q5_K_M 0.020. These sizes are larger than UD.
- **AtomicChat** AD-4.27bpw Q4_K_M-M64: KLD 0.084, top-1 89.5% in their harness.
- **ji-farthing** IQ3_KT/IQ4_KT: ik_llama-only trellis types. Our tree has the KT enums only as dead `#define`s (`iqk_ext_types.h`), so these files cannot load. KT CPU decode is also slow (3INST, fp32).
- KLD numbers across publishers are **not comparable** (different references and corpora).

### Q38FN: EXL3 (turboderp, one harness, includes the GGUF points)
- Branches: 2.05 / **3.05 (79.3 GiB)** / 4.05 (100.1 GiB) / 5.05 / 6.05 bpw.
- turboderp's plot (KLD vs FP, self-generated in-domain trace, 14.5k input + 45.6k output tokens):

| quant | KLD |
|---|---|
| UD-IQ1_M | 0.0804 |
| UD-Q2_K_XL | 0.0533 |
| UD-IQ3_XXS | 0.0349 |
| **UD-IQ4_XS** | **0.0165** |
| UD-Q4_K_XL | 0.0084 |
| NVFP4 W4A16 | 0.0100 |
| EXL3 2.05 | 0.0684 |
| **EXL3 3.05** | **0.0177** |
| **EXL3 4.05** | **0.0067** |
| EXL3 5.05 | 0.0040 |
| EXL3 6.05 | 0.0031 |

- The noise floor is 0.0025. PPL vs BF16 1.3842: UD-IQ4_XS 1.4017, EXL3 3.05 1.4075, EXL3 4.05 1.3900.
- So **EXL3 3.05 ≈ UD-IQ4_XS quality at about 25% fewer bits**. That is the "NVIDIA users see huge gains" result, and it is real for quality per bit.

## 3. Can we run EXL3 on our CPU?

**Today, no.** Nothing on this host executes an EXL3 model end to end.
- **What exists:**
  - EXL3-1/2 standalone EPYC primitives (research `0e683fc0`: scalar dense and indexed-expert operators, AVX-512BW/VNNI/VBMI `mul1`, vector MCG, K1–K8, rows 1–4).
  - exllamav3's own `moe_mul1.cpp` CPU GEMV (experts only, M≤4).
  - buun-llama.cpp's CPU executor (intake-1575): dense plus grouped, K1–K8, but **AVX2/FMA only**, and its arch coverage beyond the Qwen 27B is unverified.
- Q38FN EXL3 weights were reclaimed on 09-07 (only `download.log` remains).

**What a whole model would need, Q38FN or DS41:**
1. A safetensors → GGUF importer that carries trellis, `suh`, `svh` and per-tensor K.
2. A new ggml type plus a `mul_mat_id` path. The per-expert-projection Hadamard-128 transform is applied on both sides, so it does not fit `vec_dot`.
3. A dense EXL3 path, because EXL3 also quantizes attention, GDN, shared experts and the head at K5/K6.
4. The n-gram/engram rows. The Q38FN `_ng` rows use their own format, or we keep the GGUF table. DS41 EXL3 repos omit engram entirely, so we would keep antirez's packed tables.
5. A dequant → GEMM prefill fallback.
6. Wiring into our `qwen4exp` / `deepseek41` graphs.

Prior estimate (INF-71): importer about 1 session, type and MoE path 3–5, measurement 1, plus dense and graph work. That is **about 6–10+ sessions**. This is EXL3-6, which is parked.

**Measured CPU decode cost per weight** (INF-71 X1, real Q38FN experts, exllamav3 `mul1`):
- **Per core, compute-bound:** K4 17.3 GB/s ≈ 34.6 G weights/s; K3 9.4 GB/s ≈ 25 G weights/s. K3 is *slower per weight* because `byte_pair_ok` pairs only rows 8–15 at K3.
- **At 48 threads:** caps of about 1.66 T w/s (K4) and about 1.2 T w/s (K3).
- **Bytes-bound GGUF paths at today's 394 GB/s ceiling:** Q4_K ≈ 0.70 T w/s, IQ4_XS ≈ 0.74 T w/s, Q8_0 ≈ 0.37 T w/s. K3 would be ≈1.05 T w/s if purely bytes-bound, but its 1.2 T w/s compute cap is right next to that.
- **Ideal ceiling on the expert matmul only:** K3 ≤ about 1.4× vs Q4_K/IQ4_XS, and K4 ≈ 1.05×. The realistic range is +0–30%, before the Hadamard prep.
- The pre-BIOS 48T harness ran at 59–69% (K3) and 72–81% (K4) of the then-ceiling.
- Dense EXL3 at K5/K6 vs Q8_0 is the bigger byte lever on Q38FN, but its CPU decode rate is unmeasured.

**Where that leaves each model:**
- **Q38FN**, full EXL3 3.05 (dense ~K5 + K3 experts): about 3.6 GB/token, computed.
  - That is −38% vs UD but only **−13% vs the uniform IQ4_XS**.
  - At the observed 0.4–0.5 elasticity, that is roughly +5–6% over uniform before any ALU penalty.
  - The token is not bytes-bound: the post-BIOS uniform anchor of 59.5 ms for 4.14 GB is about 70 GB/s, roughly 17% of the ceiling.
- **DS41:** the EXL3 value proposition largely disappears because the experts are already 4-bit at the source.
  - The best possible expert artifact is the lossless MXFP4 repack.
  - A published EXL3 ≤3.5 bpw is lossy, and a hypothetical 4.0 bpw EXL3 saves only about 6% bytes versus a lossless 4.25 bpw.

**Why NVIDIA users see big gains and we would not:** a GPU has about 14–38 vector ops per HBM byte, so trellis decode is nearly free there. On Zen 5 at a 394–450 GB/s ceiling, the decode ALU cost is the same order as the byte savings (the K3 compute cap is ≈ 451 GB/s-equivalent at 48T).

### INF-71 reopen trigger: **NOT met**
INF-71 was written for Q38FN experts with two conditions:
1. "Reopen when the floor moves enough that the expert stream binds."
2. "Answer the low-bpw quality question first."

**Condition 1:** today's finding is a *kernel-level* fact about *DS41's dense Q8_0* (the node fit streams at about 394 GB/s). It is not a token-level fact about Q38FN.
- DS41's token is still about 50% non-streaming (spin 37.5%).
- Q38FN's regime has not changed (sync/dispatch dominated, about 17% of the bandwidth ceiling).
- For DS41, EXL3 is the wrong tool because the experts are FP4 at the source.

**Condition 2:** nobody has measured the quality question on our side. turboderp's plot is the only evidence, and it is in-domain and self-generated.
- If INF-71 is ever reopened, that question still comes first.
- The cheaper GGUF X0 below also answers the bytes-elasticity half of it for free.

## 4. Recommendation: the cheapest decisive CPU X0

**X0 = Q38FN "published uniform" swap test (UD-IQ4_XS → bartowski IQ4_XS).** No DS41 artifact swap qualifies (§2).

**Phase S, speed: zero download, about 25 min, in a DS41 pause window.**
- `/mnt/raid0/llm/tmp/q38fn-transfer-20261003/run_transfer.sh` (scratch) already plans UD vs uniform × arms A/B/C: llama-bench `-p 5,256 -n 128`, r3 × 3 rounds, plus coherence. Its 15:55 dry run refused only because the DS41 loop was not paused.
- The local uniform file has the same type mix as the bartowski file, so it is a valid speed proxy. The OP-32 ruling allows it for speed comparison, not quality.
- **Add the serving shape:** llama-server with `-md .../MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf`, MTP d4 (verify N=5), ABA, 3 launches per arm. At N=5 the expert union grows while dense is read once, so the gain should shrink from the N=1 +10–15%.
- **Pre-registered stop rule:** if uniform is < +8% over UD at the serving shape, stop. No swap justifies a quality risk below that.

**Phase Q, quality: only if S passes.**
1. Download a KLD reference: unsloth `Q8_0/` (188.23 GB, about 5.8 h at ~9 MB/s). It fits in the 243 GB free. One download at a time.
2. In a DS41 pause window with DS41 unloaded (Q8_0 is about 188 GB resident; DS41 holds about 520 GB with `--no-mmap`):
   - Run `llama-perplexity --kl-divergence-base` on a fixed held-out corpus (about 32 chunks × 2048; logits file about 15–30 GB at 248,320 vocab).
   - Then run `--kl-divergence` for UD and the local uniform, about 7 min each at pp ≈ 150 t/s.
3. Delete the Q8_0 and keep the base logits.
4. Download **bartowski IQ4_XS** (97.68 GB, about 3 h). Check from its header that the type mix matches the uniform file, then run KLD and Phase S again on it.
5. **Decision rule** (proposed; the operator should ratify it before any run). Adopt bartowski IQ4_XS for serving iff all three hold:
   - serving-shape decode ≥ +8% vs UD;
   - mean KLD (Q8 reference) ≤ 1.25 × UD's;
   - same-top-1 within 1 pp of UD.

   Otherwise UD stays, and the result closes the "lower-bit dense" question for Q38FN. The same data also gives the bytes-elasticity input any future EXL3 reopen needs.
6. Optional second arm if bartowski fails on KLD: ISTA GSQ-RCO IQ3_S (83.6 GB), same harness.

**DS41: spend nothing on artifacts.**
- The quality-safe published byte cut (MXFP4 lossless experts) is worth ≤ +2%, below the floor, and costs about 300 GB plus loader work.
- The only larger artifact lever, dense Q8_0 → Q6_K (−7.5% bytes per verify, about +3–4% end to end), would need a requant, which the operator has excluded.
- The DS41 levers are kernel and placement work: seed #1 (NUMA quartering) and the others in `/mnt/raid0/llm/tmp/cpu-lowbit-seeds-20261003/hypotheses-fable-cpu.md` (scratch).
- Keep the MXFP4 repack on file as a *quality* upgrade that costs nothing in bytes, in case DS41 output quality ever becomes the question.

## Evidence pointers
- **Header dumps and downloaded plots/allocations (session scratchpad, ephemeral — not preserved):** `/tmp/claude-1000/-workspace/654db1ee-133c-43cc-883a-95de28742ec2/scratchpad/{ds41.tsv,q38_*.tsv,alloc_IQ3_S.txt,alloc_IQ3_XXS.txt,q38_kld.png,q38_ppl.png}`
- **Loader constraint:** `/mnt/raid0/llm/llama.cpp-experimental-fastload-ds41-20260925/src/models/deepseek41.cpp:26-40`
- **iqk allowlist (same experimental tree):** `ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:128-138`
- **Repack guard and IQ4_NL/MXFP4 repack selection (same tree):** `ggml/src/ggml-cpu/repack.cpp:4548-4568, 4709-4740`
- **Prior CPU EXL3 numbers:** `handoffs/completed/exl3-trellis-cpu-kernel.md` (X1)
- **Uniform control:** `handoffs/completed/qwen4exp-uniform-iq4xs-baseline-control.md`
- **GPU analogue decided today:** `handoffs/active/exl3-cpu-mi210-implementation.md` EXL3-X0. The 27B Q4_K_M came in under +10%, so EXL3 has no speed case there.