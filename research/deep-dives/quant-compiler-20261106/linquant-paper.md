---
entry: intake-2641
title: "LinQuant: Functional Invariances for Low-Precision Linear Recurrences"
dive_date: 2026-11-06
dive_agent: stage-2 research-intake deep dive (subagent of intake-quant-compiler-20261106)
source_revision: "arXiv:2610.39418v1 [cs.LG], 29 Oct 2026"
source_url: https://arxiv.org/abs/2610.39418
source_file: raw/arxiv2610.39418.html
source_sha256: 531c4a6167431158eb4b3a4a3b26211fb74d12805392f9f162036f88f2b5ebb9
stripped_text: raw/paper.txt
stripped_text_sha256: ad6e9afb65f199b2c159c4b8b08b76df1e7eaa922dcf3dcbc84e73debfa9f027
read_depth: >-
  FULL for prose, equations, all tables (1-19), Appendix C proofs, Appendix D kernel
  implementation and Algorithms 1-3, and Appendix E/F ablations and production tables.
  PARTIAL for: the reference list (skimmed for provenance only); all figures 1-16, which are
  LaTeX-rendered vector graphics in the HTML5 build - captions and in-text numbers were read,
  the plotted data points were NOT (this is why Figure 5(a)'s ratio band and Figure 15's
  per-stage bars are quoted as qualitative statements, never as numbers); the supplementary
  "full source grids" the authors repeatedly defer to ("retained in the supplementary source"),
  which are not in the arXiv HTML.
lane_worktree: /mnt/raid0/llm/worktrees/intake-quant-compiler-20261106
frozen_tree: /mnt/raid0/llm/llama.cpp @ production-consolidated-v10 (ffc1bac82eeca6f9099e1ccd9ba49703c460a115)
verdict: dive-verified-with-corrections
---

# intake-2641 — LinQuant (arXiv 2610.39418v1) — Stage-2 dive

**One-line verdict.** The paper is methodologically solid and its invariance algebra is correct, but
its contribution is *conditional on owning a low-precision recurrent core that we do not have*: all
seven transformations are exact identities in real arithmetic, so they buy nothing at all until an
INT8/FP8 chunked recurrence exists. Stage 1 read this as a production-quantization result; it is
better read as a **quality-preserving design catalogue for a GDN/Mamba prefill core**, plus one
genuinely transferable measurement (Table 9's INT8-carry tolerance in *decaying* recurrences).

**What changed versus the stage-1 read** (details in §4 and §5):

| # | Stage-1 read | Stage-2 finding |
|---|---|---|
| a | "map the seven invariances onto ggml per-32-block quant types" | Nearly vacuous: **six of seven act on activations inside the recurrence**; they never meet Q4_K/IQ block layouts. Only the *projection-level* Hadamard (not LinQuant's contribution) touches weights. |
| b | "2.7B 9.441 → 9.379" alongside 8B 7.435 | Column mixing: 9.379 is the **R_QK-only** value-side row; R_QK+D_QK is 9.383 and the best 2.7B row is 9.372 (key side). Claim 3 is a blend of two configurations. |
| c | "canonical R_V costs 1.24–1.72×" | That range is LA/M2/GLA only (Table 4). Delta cells cost **1.77–10.56×** (DN 10.56× on A100). |
| d | "1.98× / 1.66× the excess NLL" | Reproducible only as **excess-perplexity** ratios (1.983 / 1.665). Under the paper's own definition (`excess NLL = log(PPLq/PPLFP)`, paper.txt:1356) the ratios are **2.008 / 1.865**. The paper itself only says "roughly twice". |
| e | "free latency" as a property of the transform | It is a property of **SSDi8's fused split-and-quantize pass**. llama.cpp's GDN core is FP32 with no such pass, so in our tree the rotation is a new per-layer `D_k×D_k` matmul, i.e. strictly added cost. |
| f | "check gfx90a integer-dot availability" | Already resolved: `v_dot4_i32_i8` (common.cuh:697) **and** int8 MFMA `mfma_i32_16x16x16i8` on gfx90a (mma.cuh:1315). The primitive is not the blocker; the operand path is. |

---

## 1. What the paper actually says

### 1.1 The seven invariances (Section 3; proofs Appendix C)

All seven are exact rewrites of the *same* FP recurrence; the paper is explicit that they "generally do
not commute with quantization" (paper.txt:522) — i.e. they change error without changing the function.

1. **(1/7) key-side rotation** `(q,k) → (R_QK q, R_QK k)`, `R_QK ∈ O(D_k)`, exact **iff**
   `R_QK Λ_t = Λ_t R_QK` (paper.txt:537, proof :1390–1402). Automatic for no decay or scalar decay;
   with diagonal decay only *local* (post-decay-weighting) rotations are valid and the carried state
   stays unrotated.
2. **(2/7) key-side reciprocal rescaling** `(q,k) → (D_QK q, D_QK⁻¹ k)`; `D_QK` commutes with
   *diagonal* decay, so it survives every linear write — but "does not, however, preserve delta
   corrected writes" (paper.txt:550; the requirement `D²k = k` is derived at :1413).
3. **(3/7) value-side rotation** `v → R_V v`, `S → R_V S`, inverse on output. Valid for **every**
   family and every decay (:1417–1423), because the recurrence acts independently along the value axis.
4. **(4/7) value-side rescaling** `v → D_V v`. Same validity; and App C notes it **cancels** under
   per-channel scales (`(d_p v_p)/(d_p s_p) = v_p/s_p`, :1423).
5. **(5/7) scalar-decay absorption**: `Γ^→` split as `(Γ^→)^η` on values / `(Γ^→)^{1-η}` on keys,
   `η ∈ [0,1]` (:584). `η=1` is SSDi8's value-side endpoint.
6. **(6/7) diagonal-decay absorption**: only the per-token scalar magnitude
   `e_r = max_n (Γ^→)_{rn}` moves to the value side; the relative channel pattern must stay on the key
   (:595–604).
7. **(7/7) write-factor absorption**, with a **compensated WY placement** for delta rules:
   `L^(σ) = tril((B^σ K)(B^{1-σ} K)^T, −1)`, `F^(σ) = B^{σ−1} F`, and a second split `τ` on the
   transformed write operands `V^(σ,τ) = B^{(1−σ)(1−τ)} F^(σ)`, `K^(σ,τ) = B^{(1−σ)τ} K`
   (:618–639). `(σ,τ)=(1,1)` recovers standard FLA placement.

### 1.2 Reconstructed applicability matrix (Table 1)

Table 1's HTML renders as one flattened token stream (the stage-1 note flagged this). Reconstructed
from the header order `LA | Mamba-2 | GLA | DN | GDN | KDA` and **cross-checked against §3.2, App C
and Fig. 2/3(a)**; confidence high, with the two ambiguities noted after the table.

| # | transform | LA | Mamba-2 | GLA | DN | GDN | KDA |
|---|---|---|---|---|---|---|---|
| 1/7 | `R_QK` | ✓ | ✓ | (✓) | ✓ | ✓ | (✓) |
| 2/7 | `D_QK` | ✓ | ✓ | ✓ | × | × | × |
| 3/7 | `R_V` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 4/7 | `D_V` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 5/7 | scalar-decay `(Γ^→)^η` | × | ✓ | (✓) | × | ✓ | (✓) |
| 6/7 | diagonal-decay `E^η` | × | ✓ | ✓ | × | ✓ | ✓ |
| 7/7 | write gate `(B^ξ, B^{1−ξ})` | (✓) | (✓) | (✓) | ✓ | ✓ | ✓ |

`×` not applicable · `✓` applicable · `(✓)` applicable under constraints. Reading notes:
- `(✓)` on 1/7 for GLA/KDA = **local-only** rotation (diagonal decay does not commute; paper.txt:537).
- `×` on 5/7 and 6/7 for LA/DN = those cells have no decay at all, so the split is vacuous.
- `(✓)` on 7/7 for LA/M2/GLA = only the *gated* zoo cells (`+β`) admit it; DN/GDN/KDA always carry β.
- **Rows 2/7 vs 1/7 disagree for DN/GDN/KDA**, and that is the substantive result: a *scalar*
  rescaling breaks the delta erase term while a *rotation* does not (rotations preserve `kkᵀ`.
  `D k kᵀ D⁻¹` does not). Applicability is not "delta vs linear" — it is per-transform.

**Why this matters for us:** our production stack is 75% standard GDN (Qwen3.5-35B-A3B, 30/40 layers;
lane `handoffs/active/model-architecture-readiness.md:62`). For GDN the matrix gives **1/7, 3/7, 4/7,
5/7, 6/7(deprecated to 5/7 for scalar decay), 7/7 — and NOT 2/7**. The paper's *production* win is
mostly `D_QK`, the one transform GDN cannot use. This is the single sharpest stage-2 correction.

### 1.3 What is quantized, what stays FP (Appendix B.1, D.1, D.2; Algorithms 1–3)

- **Quantized (INT8 operands, INT32 accumulate):** the three contractions — state write
  `Q(BV)ᵀ Q(Γ^→⊙K)`, state read `Q(Q) Ŝᵀ`, local score `Q(Q)Q(K)ᵀ`. Each contraction quantizes its
  **own** copy of the operands ("The local path and state write quantize their operands separately",
  paper.txt:1691).
- **FP16:** the intra-chunk output product `Â · Q(BV)` ("uses FP16 arithmetic on INT8-quantized
  values", :1691).
- **FP32:** the FP32 carry state; the Gram matrix, the triangular solve and all WY intermediates
  (:1554); the 16-token diagonal blocks of the local score under diagonal decay (dequantized q/k, :1352).
- **State:** "An FP32 state is carried between chunks, and reads consume an INT8 copy with one scale
  per head and value channel, calibrated on the carry" (:1352) — the *stored state* is an INT8 read
  copy, the *carry* is FP32. (Production replaces the carry with an INT8 fixed point: Algorithm 3
  line 6, `Ŝ ← fx(γ^C Ŝ) + Q8(H, s_S)`.)
- **Scales:** symmetric, static, max-abs over 8 WikiText-2 windows of 2048 tokens; keys
  per-tensor (or per-channel *write* keys in `⟨H,C⟩`), values per-channel/per-head/per-tensor
  (`⟨b_QK, b_V⟩ ∈ {H,C,T}²`), production per-`(H,D_v)` values and per-group INT8 keys/queries (:1372).
- **Delta machinery:** only the incoming-state correction `Q(W[i]) Ŝᵀ` is a quantized contraction;
  everything else in WY is FP32 (:1554, Algorithm 2 line 5).

### 1.4 Controlled study (340M/1.3B zoo, INT6)

Why INT6 at all: "Several normalized decaying and delta-rule models already incur little quantization
error at INT8 with per-channel value scales (Table 7). We therefore use INT6 in the controlled study
to amplify quantization effects" (:721). **This is a deliberate amplification, not a deployment point.**

Table 5, `⟨T,T⟩` (per-tensor value scales), 340M:

| model | FP | naive | best single | stack |
|---|---|---|---|---|
| LA | 17.117 | 30.694 | 23.151 | **18.138** |
| LA+β | 16.688 | 28.381 | 19.773 | 17.388 |
| Mamba-2 | 15.553 | 16.446 | 16.036 | **15.633** |
| Mamba-2+β | 15.420 | 16.230 | 15.609 | 15.473 |
| DeltaNet | 15.678 | 20.323 | 16.138 | 15.871 |
| GDN | 15.004 | 17.064 | 15.236 | 15.103 |
| KDA | 14.489 | 15.837 | 14.885 | 14.906 |

Table 5/6 also carry `⟨T,C⟩` columns, where the stack is much closer to FP (M2 15.605 vs FP 15.553).

### 1.5 Production (W4A8 projections + INT8 recurrence; Table 2 / 17)

| model | FP16 | SSDi8 | `R_QK` | `R_QK+D_QK` (value) | `R_QK+D_QK` (key) |
|---|---|---|---|---|---|
| Mamba-2 1.3B | 10.420 | 10.928 ± 0.004 | 10.860 ± 0.007 | **10.849 ± 0.011** | 10.830 ± 0.007 |
| Mamba-2 2.7B | 9.060 | 9.441 ± 0.017 | 9.379 ± 0.011 | 9.383 ± 0.007 | **9.372 ± 0.003** |
| Mamba-2 8B | 7.250 | 7.620 ± 0.009 | 7.456 ± 0.009 | **7.435 ± 0.008** | 7.437 ± 0.004 |
| Nemotron-H Base | 6.030 | 6.338 | 6.186 | **6.178** | 6.175 |
| Nemotron-H Reasoning | 8.423 | 8.921 | 8.666 | 8.650 | 8.670 |

Fraction of *excess NLL* actually removed (my arithmetic, `log(PPLq/PPLFP)`, Table 17 values):
1.3B **15.2%**, 2.7B **15.0%**, 8B **49.4%**, Nemotron-H Base **51.3%**. The two "strong" results are
the 8B and Nemotron-H; the two small models recover about a sixth of the gap, and their six-task
averages barely move (1.3B 0.588→0.588; 2.7B 0.626→0.627; 8B 0.696→0.699 — Table 17).

### 1.6 Timing (what is measured, on what)

- Full-model prefill, **A5000, B=8, T=2048**, absolute: 1.3B **609 ms**, 2.7B **1163 ms**,
  8B **2542 ms** for their SSDi8 re-implementation (official SSDi8: 616/1184/2563 ms) — Table 13.
- Rotated arms: reported only as a **ratio** to the matched SSDi8 setting (Fig. 5(a), B = 1…32) —
  "no measurable end-to-end prefill latency" (paper.txt:967). No absolute ms and no CI for the
  rotated arm.
- Layer-level: 1.3B, B=1, **1.498 ms** without rescaling and **1.498 ms** fused (Table 14) — a 6-digit
  coincidence, so the resolved precision is ≤0.1% at that shape.
- Kernel-level canonical-`R_V` overhead, `B=H=8, T=2048, D_k=D_v=128`: LA/M2/GLA **1.24–1.72×**,
  DN/GDN/KDA **1.77–10.56×** (DN 10.56× on A100) — Table 4.

---

## 2. What the paper does NOT say

**Decode — ABSENT.** The word "decode" appears twice in the whole text (a reference title, and one
related-work sentence about per-token cost); there is no token/s, no batch-1 latency series, no
autoregressive path. §5 scope statement: "Although our implementation focuses on integer prefill…"
(:967). The per-token path is not merely unmeasured, it is unbuilt: the companion repo raises
`NotImplementedError` for the non-chunk mode (intake-2642 note, lane `entries.yaml:101`).

**ROCm / gfx90a — ABSENT.** Every measured device is NVIDIA (A5000, A100-SXM4, H100 — Table 4).
No HIP, no wave64, no MFMA, no `rocprof`.

**CPU — ABSENT.** No CPU backend, no x86 measurement, no discussion of a non-tensor-core machine.

**Absolute latency for the transformed configuration — ABSENT** (ratios only; the only absolute ms
are for the *baseline*, Table 13, and the 1.3B B=1 layer case, Table 14).

**A control that separates rotation from recalibration — ABSENT.** Table 19 varies only the Hadamard
*sign pattern* (deterministic vs random vs no rotation). Every rotated production arm re-measures
activation scales **with the transform applied** and re-runs GPTQ **after fusing the transform**
(:1374), so "rotation" and "recalibration + re-GPTQ" are bundled by construction. The one isolation
control in the paper is a negative one the authors volunteer: "Static value-side runs omit the
output-projection mean correction used by the other configurations, so the static comparison does
not isolate decay placement" (:3376).

**Independent replication — ABSENT.** Single lab; the controlled 340M/1.3B checkpoints are not
released ("retained in the supplementary source"); the production models are public but the SSDi8
baseline is the authors' re-implementation (validated against the official release to ±0.01 PPL and
±1.2% latency, Table 13).

---

## 3. Mechanism: where the gains come from

1. **Range redistribution (the headline).** A rotation spreads channel-concentrated energy so a
   *shared* scale fits better: "random rotations spread energy across channels, reducing outlier
   concentration" (:535). `D_QK` is the same idea in a cheaper form — it *transports magnitude*
   between q and k channels by `(max|k|/max|q|)^κ` (:552), which is SmoothQuant's move applied
   per head across the q/k pair.
2. **Granularity coupling, not a new error term.** The transforms only pay when a scale is *shared*
   across the axis they act on. The paper proves the limiting case: per-channel scales make `D_V`
   cancel exactly (:1423) and Fig. 7's caption states the empirical version. **The gain is a
   function of the quantizer, not of the model.**
3. **Operand reuse / requantization cost (the runtime story).** "Moving decay onto an operand after
   its INT8 representation has been formed requires rereading and requantizing the floating-point
   tensor. The cost therefore depends on which operand is affected, its dimension, and how often its
   quantized representation is reused" (:963), and "the remaining difference is in the state write,
   which reloads the absorbed operand in floating point before weighting and quantizing it" (:3451).
   This is why value-side decay wins on Mamba-2 (`D_k=128, D_v=64`): the same value operand is
   quantized once and reused by the local output and the write, whereas key-side decay forces a
   floating-point re-read of the keys in the state write (Fig. 15, :3451–3453).
4. **Not** outlier *clipping*, not GPTQ compensation, not a better codebook. There is no
   reconstruction objective anywhere; every transform is a closed-form algebraic rewrite plus a
   calibration-set scalar (`κ`, `η`, `ξ`, `σ`, `τ`).

---

## 4. Claims adjudication

Quotes are lifted programmatically from `raw/paper.txt` by line + anchor
(`verify/quotes.py`); `quote_sha256` is sha256 of the quote after collapsing whitespace runs to one
space and stripping. Math spans survive as the HTML5 text layer renders them (e.g. `𝐑 Q ​ K`,
`⟨ T , T ⟩`) — that is verbatim, not a transcription choice.

| claim | verdict | locator | verbatim quote | quote_sha256 | evidence note |
|---|---|---|---|---|---|
| **1** — seven exact transformations; applicability recurrence-dependent; key rotation exact only when it commutes with decay | **CONFIRMED** | §3.1–3.3; App C; Table 1 (paper.txt:165, 537, 550, 584–639, 1390–1473) | "we introduce LinQuant, a framework for low-precision recurrent prefill based on seven such invariances, including rotations, diagonal rescalings, and alternative placements of recurrent decay and write factors." | `0e9b2414abeadcf9bc7c3d64a8b84f481dbc26b23437ab1e58d700598a2912f6` | All seven proved as exact identities in App C. Commutation condition stated in §3.2 and restated in the proof. One correction: "key rotation only when it commutes with decay" is right but incomplete — `R_QK` also survives *diagonal* decay in a **local-only** form (post-decay-weighting, unrotated carry), which is what Table 1's `(✓)` for GLA/KDA means. |
| **1b** — key-rotation commutation condition | **CONFIRMED** | §3.2 (paper.txt:537) | "Invariance thus holds with no decay or scalar decay." | `a88b2068b368643438e5147f74cf75eaad261cbae8b12addbabb4d331f8e3474` | Immediate follow-on sentence: "With diagonal decay, a general rotation does not commute with Λ_t, so the recurrent state cannot be carried in a globally rotated basis." |
| **2** — stack recovers 1.98× (M2) / 1.66× (LA) the excess NLL of the best single transform at INT6/per-tensor | **PARTIAL** | §4.1; Table 5 `⟨T,T⟩` (paper.txt:832; 2428–2435; 2410–2417) | "At INT6 under ⟨ T , T ⟩ \langle\mathrm{T,T}\rangle , the selected combination recovers roughly twice as much excess NLL as the best single transformation for both 340M Mamba-2 and LA (Table 5 )" | `bbc2590c8e0d75a557016432c94f993c60881b1d491d4b88e5cadbb4c4185ac2` | Table values reproduce exactly (M2 16.446→15.633, FP 15.553; LA 30.694→18.138, FP 17.117). The **multiples do not survive the paper's own metric**: `excess NLL = log(PPLq/PPLFP)` (:1356) gives **2.008×** and **1.865×**, not 1.98/1.66. 1.983/1.665 are ratios of raw **perplexity deltas**. For LA the two framings disagree by 12%. The paper's own wording is only "roughly twice". |
| **3** — production W4A8+INT8 state: 8B 7.620→7.435 (FP 7.250), 2.7B 9.441→9.379, 1.3B 10.928→10.849, Nemotron-H Base 6.338→6.178 (FP 6.030) | **PARTIAL** | §4.2; Tables 2, 17 (paper.txt:197; 904–957; 3519–3625) | "We apply LinQuant to production W4A8 models with INT8 recurrent states, improving over SSDi8 on Mamba-2 1.3B, 2.7B, and 8B and Nemotron-H 8B." | `ff3da61896b558e3b50d4fef9c3f83b88847ead395a21cbcbf9fb3e6c03c4d21` | 8B/1.3B/Nemotron-H numbers are the **R_QK+D_QK value-side** row (Table 17) ✓. **2.7B 9.379 is the R_QK-only row**; R_QK+D_QK is 9.383 (a 0.004 regression, inside ±0.007) and the best 2.7B is 9.372 key-side. Claim mixes two configurations. Effect sizes: 15% / 15% / 49% / 51% of excess NLL removed — the two small models are weak; 1.3B downstream avg is 0.588 vs 0.588 for SSDi8. |
| **4a** — key-axis transforms free when fused into an existing split-and-quantize pass | **CONFIRMED (with a scoping condition that voids it here)** | §4.2, App D.2 (paper.txt:960, 1737, 967) | "Moreover, on the evaluated Mamba-2 models, query–key rotation adds no measurable prefill latency." | `0c7006dab045c52fa32cbfe1e1055d5c2825531e92082f6abd682c7ebd4c8205` | True *for SSDi8's fused pass*: "Neither transformation requires a separate kernel launch or memory pass **in this implementation**" (:1737). The measurement is a ratio (Fig. 5(a)), resolution ~1%; no CI. In a tree without such a pass the rotation is a new matmul — see T2. |
| **4b** — value-axis not deployed; rotated state 10.496→10.533; canonical R_V 1.24–1.72× | **PARTIAL** | §4.2, App F.1; Tables 15, 4 (paper.txt:3370; 3370–3372; 2105–2140) | "Since it provides no quality gain under the production scale policy, LinQuant leaves the value axis unchanged." | `8a26fd8dac856ee1d0679dd77e784c6f3835c59cb744315259b26d9a89b8f5ef` | 10.496→10.533 (rotated) / 10.497 (canonical) confirmed (Table 15, 1.3B, FP projections + INT8 fixed-point state). But the **1.24–1.72× range is LA/M2/GLA only**; delta cells are 1.77–10.56× (Table 4). The stated reason is per-channel value scales already saturating the gain — a granularity argument, not "value rotation is bad". |
| **5** — INT4 unsolved; per-tensor stack 85.441→17.141 vs FP 15.553; sub-INT8 needs a better scheme and a sub-byte kernel | **CONFIRMED** | §E.2, Table 7 `⟨T,T⟩` (paper.txt:2825; 2652–2659) | "These experiments use 4-bit integer ranges within INT8 kernels; deployment below INT8 therefore requires both a more accurate quantization scheme and an efficient sub-byte implementation." | `c8a697045572b54a2e65e7c63532f16a60dc5528675b253b084b86d04e9b954e` | Exactly the table values. Note the shape of the result: 94% of the excess **NLL** is recovered but the residue is still **+10.2% perplexity** (17.141 vs 15.553) — the naive INT4 baseline is catastrophic (85.441), so percentage-recovered flatters it. |

### 4.1 Additional questions

| q | answer | locator | verbatim quote | quote_sha256 | note |
|---|---|---|---|---|---|
| **A** — applicability matrix | **ANSWERED**; see §1.2 table | Table 1 (flattened), §3.2, App C | "It does not, however, preserve delta corrected writes." | `7de87a6cb141df68b0946b5dc0bca3f866ba9f99f0486cd10b71f296d0ab8fb5` | The `D_QK`-vs-`R_QK` split inside the delta family is the whole point: rotation preserves `kkᵀ`, reciprocal rescaling does not. |
| **A2** — commutation clause | **ANSWERED** | App C (paper.txt:1402) | "Commutation is automatic for absent or scalar decay. For fixed diagonal decay, 𝐑 {\color[rgb]{0.0313,0.5664,0.6016}\bm{\mathrm{R}}} must preserve the common decay eigenspaces." | `16484cca4db7f7801fcded2531648a138e95e441c28d0db945414672fa71b794` | For diagonal decay the *carried* state cannot be globally rotated; only within-chunk score operands can. |
| **B** — what is quantized vs FP; accumulate precision | **ANSWERED** | App B.1, D.1, D.2, Alg. 1–3 | "The state read, local score, and state write use INT8 operands with INT32 accumulation, while the intra-chunk output uses FP16 arithmetic on quantized values. The state is carried in FP32, with an INT8 copy used by the next chunk." | `5e75500a5cf3464665af235c7c870b55c488fb5d1162411857905552d384dcbe` | Plus the delta boundary — "The Gram matrix, the triangular solve, and the WY intermediates are computed in FP32" (`4919bb28e5bbc64bc1231e8ffd38459f25ac3e180f3496d49756589fcc3b232d`). Delta WY is *never* quantized; that is the hard boundary. |
| **C** — is "free" measured end-to-end or inferred? | **MEASURED, at ratio resolution** | Fig. 5(a); Table 13; Table 14 | "Value-side absorption is faster for the tested Mamba-2 geometry, where D k = 128 D_{k}=128 and D v = 64" | `c4532dca0ae9c014683fdf0dee476282182b9483c900e13ed27fd4b9c6ac9601` | End-to-end prefill ratio on **A5000, T=2048, B=1…32**; absolute ms only for the baseline (609/1163/2542 ms at B=8); layer-level absolute 1.498 ms at B=1. Resolution ≈1%, no CI, no significance test. |
| **D** — any decode / token-s-per-second evidence? | **ABSENT** | whole text | — | — | Zero occurrences of decode throughput, batch-1 latency, or tokens/s. Prefill-only by construction (§5). |
| **E** — mechanism; is rotation isolated from calibration? | **ANSWERED; no isolation control** | §3.2, §F.1, Table 19 | "The SSDi8 pipeline already uses per-channel value scales, matching the controlled setting in which 𝐑 V {\color[rgb]{0.0313,0.5664,0.6016}\bm{\mathrm{R}}_{V}} and 𝐃 V {\color[rgb]{0.8633,0.2227,0.4648}\bm{\mathrm{D}}_{V}} provide little benefit." | `fe528ce97ab619ed8b4f273736bfbc0025f8271a9938c4df357bcf6fe6046ed1` | Mechanism = range redistribution + operand-reuse economics (§3 above). No rotation-vs-recalibration arm; Table 19 isolates only the sign pattern. The nearest thing to an isolation control is the admitted confound at :3376 (`so the static comparison does not isolate decay placement`, `b730617ead7cd21bb4f7623655f91abeeb8277feebe191dc298b294243d5672e`). |
| **F** — honest statements about noise and about the D_k=128/D_v=64 asymmetry | **PARTIAL** — no explicit "within noise" statement anywhere | §4.1, §F.2, §F.1 | "Combining transformations can improve further, although the selected stack does not outperform every individual setting in every configuration." | `727d5809cb1f5ff7c015a8b8176adc9c7ba8917b411f6d1aa0be8c6ec7d1f252` | The paper reports mean±std but never declares a win non-significant. A reader can see it: 1.3B `D_QK` gain 0.011 vs σ 0.007–0.011 (≈1σ); 2.7B `D_QK` is a **regression** (9.383 vs 9.379); 8B value vs key 7.435 vs 7.437 (identical). Downstream: "Perplexity improvements do not imply uniform gains in task accuracy, as the comparison with the unrescaled configurations in Table 17 shows." (`0d0e765248a49b899337f17a4aee44c921264f45eaa442315f5ec1b572cdcae8`). The D_k/D_v asymmetry is explained mechanistically (Fig. 15 + :3451–3453): value tile is smaller and quantized once and reused; key side re-reads fp keys to apply per-head decay. It narrows and can reverse at `D_k=64` (:3513). |

### 4.2 Two further load-bearing anchors, quoted in the body

| anchor | locator | verbatim quote | quote_sha256 | where it is load-bearing |
|---|---|---|---|---|
| granularity cancels diagonal rescaling | App C (paper.txt:1423) | "With per-channel scales, diagonal rescaling cancels because ( d p ​ v p ) / ( d p ​ s p ) = v p / s p (d_{p}v_{p})/(d_{p}s_{p})=v_{p}/s_{p} , where s p s_{p} is the channel scale. Consistently transformed scales therefore leave quantization unchanged, apart from finite-precision rounding." | `85a49c31135d274491059c37a69b0be871b9ed421fa8200cd8809cffea69cf66` | T1 — proves the gain is a function of the *quantizer*, not the model: the finer the scale on the transformed axis, the smaller the invariance's payoff, and at per-channel it is exactly zero. |
| the paper's own metric | §B.1 (paper.txt:1356) | "Excess NLL is log ⁡ ( PPL quant / PPL FP )" | `f4cc699d7a5c2aef75afb1792f777a3e7d343ef544ca5ba91a2db4e90445b63c` | Claims-table row 2 — this definition is what turns the stage-1 "1.98×/1.66×" into 2.008×/1.865×. |

---

## 5. Transfer answers (binding lens)

Context from the lane and the frozen tree:

- **75% of the production stack is standard GDN** — Qwen3.5-35B-A3B, 30/40 layers
  (`handoffs/active/model-architecture-readiness.md:62`). State size scales as `H·D_k·D_v` floats per
  layer: the lane's 21-layer f32 reference at `6×192×384` is ≈37 MB (`:182`), and a 30-layer
  `16×128×128` GDN is ≈**31 MB** — the number used in T3 below.
- **Serving formats today**: Q8_0 on the GDN hybrids and on the 27B incumbent
  (`handoffs/active/quantization-and-low-bit.md:86–90`); decode sits at **70.2% of HBM roofline for
  Q8_0** vs 46.5% for Q4_K on the 27B (`:101`). In other words we are already bandwidth-saturated in
  the format we ship, and the low-bit question on this host is a kernel/occupancy question, not an
  algebra question (`:97–100`).
- **llama.cpp's GDN prefill is a graph of plain `ggml` ops** — `src/models/delta-net-base.cpp:61`
  (`CS = 64`, 16 for KDA), `:72–73` (`v_b = v*b`, `k_b = k*b`), `:166` (`ggml_solve_tri`, F32),
  `:243/:255` (state read/write as `ggml_mul_mat` on the F32 state). The CUDA per-token kernel is
  F32/BF16 only and carries the standing TODO at `ggml/src/ggml-cuda/gated_delta_net.cu:191`.

### T1 — Do `R_QK`/`D_QK` survive per-32-block max-abs scales with dequant-on-load?

**Yes for exactness; the interesting part is that the question is mostly mis-framed.**

1. **Exactness is quantizer-independent.** All seven are identities in real arithmetic applied *before*
   `Q`. No scale geometry can break them.
2. **They never meet the weight block layout.** `R_QK`/`D_QK` act on `q`,`k` **after** the conv+SiLU
   pre-processing (`paper.txt:539`, `:1376` — "Moving it before the nonlinear preprocessing would not
   preserve the function"), i.e. on *activations*. Q4_K/Q5_K/Q6_K/IQ block structure
   (`ggml/src/ggml-common.h:341–382`; `QK_K=256` at `:89`, 8×32 sub-blocks for `q4_K`) is irrelevant
   to them. The one weight-side rotation in the paper is the **projection-level Hadamard** folded into
   the weights before GPTQ (`paper.txt:1374`) — that is QuaRot/SpinQuant's transform, not LinQuant's
   contribution, and is separately available to us.
3. **Per-32-block scales are *native* in ggml, so the transform costs nothing extra on the scale side.**
   `block_q8_0` is one fp16 scale per 32 (`ggml-common.h:251–256`); the CPU dot applies it per block
   (`ggml/src/ggml-cpu/arch/x86/quants.c:1442–1444`, `d = dx*dy` then FMA into a float accumulator) and
   CUDA MMQ rescales per 32 inside the k-loop. So `D_QK`/`R_QK` need no new scale machinery.
4. **But the benefit ordering flips relative to the paper.** `D_QK`'s gain **vanishes as the scale
   narrows on its own axis** — proved for `D_V` at `paper.txt:1423` and shown empirically for `D_V` in
   Fig. 7's caption. `D_QK` is only ever evaluated by the authors with per-tensor or per-head **key**
   scales (`:724`: the key axis is contracted, so its scales must enter the contraction). Per-32-block
   key scales sit strictly between "per-tensor" (paper's best case for `D_QK`) and "per-channel"
   (exact cancellation), so **`D_QK` survives but with a smaller ceiling than the paper's numbers**.
   `R_QK` does not cancel at any granularity, because it mixes channels — provided the Hadamard width
   is ≤ the scale block (a 32-wide Hadamard keeps each block's 32 channels together; a 128-wide
   Hadamard across 32-element blocks is still legal but must be followed by a re-derived per-block
   max, which is just "quantize the rotated tensor", i.e. normal ggml behaviour).
5. **Rank order for a per-32-block budget: `R_QK` > `D_QK`.** For GDN specifically, `D_QK` is `×`
   anyway (Table 1 row 2/7) — the question is moot for 30 of our 40 layers.

**"Dequant-on-load" never arises** for the recurrent core: the operands are float tensors that get
quantized at the contraction; there is no stored low-bit state to dequantize. It would only arise if
we stored the recurrent state in a block format (see T3).

### T2 — Which of the seven is implementable in ggml today for a GDN/Mamba prefill path, and what is the smallest proving experiment?

Implemented-as-graph-ops today (all seven are *expressible*; none is *profitable* without a quantizer):

| transform | GDN | implementable in the existing chunked graph? | cost today |
|---|---|---|---|
| 1/7 `R_QK` | ✓ (scalar decay commutes) | yes — a `D_k×D_k` Hadamard per head on `q`,`k` after conv+SiLU/qk-norm; cannot fold into `W_Q/W_K` because of the intervening conv+SiLU | **new matmul per layer per token** — the opposite of "free" |
| 2/7 `D_QK` | **×** | n/a | — |
| 3–4/7 `R_V`/`D_V` | ✓ | yes (`ggml_mul` / matmul on `v` and the state) | pointless: the core is F32, so there is no scale to rebalance |
| 5/7 scalar decay | ✓ | already there: the graph builds `g_cumsum`/`g_exp` and applies them to `k` and `v` (`delta-net-base.cpp:96–200`) | rewiring only |
| 6/7 diagonal decay | ✓ (degenerate for scalar) | same | rewiring only |
| 7/7 write gate `(σ,τ)` | ✓ | **yes, cheapest of all**: today `v_b = v*b` and `k_b = k*b` (`:72–73`) = gate on V plus gate on the Gram's left operand; the paper's selected coarse-scale placement is `σ∈{0,½}`, `τ=1`, i.e. move the gate off the Gram's left operand onto the transformed keys (`paper.txt:829`, `:639`) | one line of graph rewiring |

**The hard blocker is not the invariance; it is that our core is FP32 and there is nothing to fix.**
In the frozen tree the recurrent-core contractions are `ggml_mul_mat` on F32 tensors, the WY solve is
F32 (`ggml_solve_tri`, `:166`), and no int8 operand path exists for anything except quantized
*weights*. So:

- **Smallest proving experiment #1 (decides everything, days not weeks):** profile the GDN core's share
  of prefill and of decode at our serving shape (Qwen3.5-35B-A3B Q8_0; 2048-token prompt; CPU and
  MI210; `GGML_CPU_PROF` / `rocprof` per-kernel). **Pre-registered rule:** core < 5% of prefill wall →
  decline the whole line; ≥ 15% → open an INT8-core feasibility packet. *Expected direction:* the core
  is **~1%** — its state ops are `3·H·D_k·D_v ≈ 0.8M` MACs/token/layer against ~75M MACs/token/layer
  for the MoE FFN of a 3B-active model over 40 layers, and its 62 MB of state traffic (read+write) is
  **0.17%** of the ~37 GB of weights streamed per decode token. I expect the profile to kill it.
- **Smallest proving experiment #2 (only if #1 says ≥15%):** the quality-side fake-quant probe — add
  quantize→dequantize (Q8_0, per-32 block) on the four contraction operands of the *existing* graph,
  per Algorithm 1, with and without `R_QK`, and measure WikiText-2 ΔPPL on a small GDN checkpoint.
  *Expected direction:* naive Q8_0 operands cost **<0.5% PPL** on a normalized decaying model (paper
  Table 7: M2 340M INT8 `⟨T,C⟩` 15.612 vs FP 15.553 = +0.38%), so the headroom the invariance can
  recover is itself <0.5% — at our 7–10 PPL scale that is ≤0.04 PPL, the same order as our
  four-calibration-set spread (0.007–0.017), i.e. at the edge of resolvability rather than comfortably
  inside it.

### T3 — Does anything here reach decode (T=1)?

**No.** Prefill-only (`paper.txt:967`), no token/s, no per-token path. The only decode-shaped evidence
is the state-precision control (Table 9, INT6, 340M, no transforms):

| model | FP state | INT8 read (FP32 carry) | INT8 carry |
|---|---|---|---|
| LA | 19.954 | 22.349 (+2.40) | 23.963 (+1.61 over read) |
| Mamba-2 | 15.763 | 15.795 (+0.03) | 15.914 (+0.12) |
| GDN | 15.120 | 15.122 (+0.00) | 15.153 (+0.03) |

The transferable asymmetry: **decay damps carry error.** An INT8 *carry* costs GDN +0.2% PPL and
Mamba-2 +0.8%, but accumulating linear attention +8%. Mechanically that supports a *state-byte*
reduction in decode for decaying models — which is exactly what llama.cpp already half-has: the GDN
kernel carries `float` or `nv_bfloat16` state (`ggml/src/ggml-cuda/gated_delta_net.cu:338–343`), and
an in-graph F32→Q8_0 store is supported (`ggml/src/ggml-cpu/ops.cpp:296–298`, the same `from_float`
path the KV cache uses).

**But the arithmetic says it cannot pay.** Per token the per-token kernel reads+writes the full state:
`H·D_k·D_v` floats ≈ 262k × 4 B = 1 MB/layer, ×30 GDN layers ≈ **31 MB read + 31 MB written = 62 MB**
per token. Against ~37 GB of Q8_0 weights streamed per token that is **0.17%**; at MI210's 1638 GB/s it
is ~38 µs of a ~22 ms token. Halving it to INT8 buys ~0.08% — two orders below the noise. Even the
15×-larger log-linear state
(557 MB, `model-architecture-readiness.md:183`) is ~1.5% of per-token bytes.

**Verdict: decline for decode.** The INT8-carry tolerance is worth recording as a *prior*, not as a
work item.

### T4 — Would any claim survive on CPU, where the win is bandwidth not integer tensor cores?

**No, and for a sharper reason than "CPU lacks tensor cores".**

1. The integer dot is *not* missing. `v_dot4_i32_i8` via `__builtin_amdgcn_sdot4` on gfx90a
   (`ggml/src/ggml-cuda/common.cuh:694–697`), int8 MFMA `mfma_i32_16x16x16i8`
   (`ggml/src/ggml-cuda/mma.cuh:1315`, `CDNA2` selected for `__gfx90a__` at
   `vendors/hip.h:203–205`), and on CPU `ggml_vec_dot_q8_0_q8_0`
   (`ggml/src/ggml-cpu/arch/x86/quants.c:1417`) with a true int8×int8 VNNI dot under
   `__AVXVNNIINT8__` (`:122–127`, `_mm256_dpbssd_epi32`) falling back to sign-magnitude
   `maddubs` (`:229–243`). Whether *our* build enables `__AVXVNNIINT8__` on the EPYC 9655 is a
   one-command check, not a research question.
2. The invariances change **activation** representation, and on CPU the activation traffic in the GDN
   core is ~62 MB/token (read+write) against ~37 GB/token of weights. There is no byte to save: the weights are
   already Q8_0/Q4_K, and the transform does not touch weight formats. **A bandwidth win is
   arithmetically excluded.**
3. A *compute* win could exist in CPU prefill (VNNI int8 at ~2× fp32 lane throughput). Two things
   bound it: our CPU lane's latency budget is decode-dominated (long prompts amortised over
   generation), and the recurrent core is ~1% of prefill FLOPs anyway (T2). It is not excluded, it is
   bounded to roughly nothing.

So the honest CPU answer: **nothing survives**, and the reason is model geometry, not ISA.

---

## 6. Derived actionables ledger

Owners are the lane's own handoffs. Disposition vocabulary: **immediate packet** (do now),
**probe** (cheap measurement that could change a decision), **trigger** (armed on a named event),
**decline** (with the reason it cannot pay).

| ID | source claim | action | owning handoff (lane) | disposition | smallest deciding experiment + expected direction |
|---|---|---|---|---|---|
| **LQ-1** | whole paper (prefill-only premise) | Measure the GDN recurrent core's share of prefill and decode wall time on our serving shape, CPU and MI210 | `quantization-and-low-bit.md` (INF-80); co-owner `cpu-decode-roofline-program.md` (INF-70) | **immediate packet** (≤1 agent-day, decides LQ-2…LQ-6) | 2048-token prompt, Qwen3.5-35B-A3B Q8_0, per-kernel profile of the 30 GDN layers vs the MoE FFN. **Rule:** core <5% of prefill → decline the line; ≥15% → open an INT8-core packet. *Expected:* ~1% (0.8M vs ~75M MACs/token/layer; 31 MB state vs 37 GB weights) → decline. |
| **LQ-2** | claim 1 + Table 1 row 2/7 | Record in the architecture handoff that **`D_QK` is inapplicable to standard GDN**, so the paper's production win does not transfer to 30/40 of our layers | `model-architecture-readiness.md` (INF-48) | **immediate packet** (documentation only, no compute) | No experiment: proof is App C (`D²k = k`, `paper.txt:1413`). Direction: prevents a mis-scoped port. |
| **LQ-3** | claim 4a ("free" latency) | Record that "free" is a property of SSDi8's fused split-and-quantize pass, absent in our tree; any `R_QK` here is a new per-layer matmul | `quantization-and-low-bit.md` (INF-80) | **immediate packet** (documentation) | No experiment; if a port is ever proposed, the acceptance test is measured end-to-end prefill ms with the rotation on vs off, not a ratio from another tree. |
| **LQ-4** | claim 5 | Keep sub-INT8 **out** of scope for the recurrent core; the paper states it needs a new scheme *and* a sub-byte kernel | `quantization-and-low-bit.md` (INF-80) | **decline** | Reason: 17.141 vs FP 15.553 = +10.2% PPL even after 94% of the excess NLL is recovered; no sub-byte kernel exists in-tree. Revisit only with a new codec. |
| **LQ-5** | Table 9 (INT8 carry tolerance) | Record the decaying-vs-accumulating asymmetry (GDN +0.2% vs LA +8% PPL from an INT8 carry) as a design prior for any recurrent-state byte reduction | `kv-cache-program.md` (RTG-58) for the state-cache question; `quantization-and-low-bit.md` (INF-80) for the format | **trigger** (armed on: a model whose recurrent state exceeds ~10% of per-token bytes) | At our geometry the state is 0.17% of per-token bytes (62 MB vs 37 GB) → no probe now. On a 15×-state log-linear GDN it is ~3% read+write — still too small; would need a state-dominant model. |
| **LQ-6** | claim 3 (production gains) | Do **not** re-derive the paper's W4A8 numbers as a target; they are the delta between two INT8-core designs, not a gain over FP | `quantization-and-low-bit.md` (INF-80) | **decline** | Reason: the arms are SSDi8-with-rotation vs SSDi8; the FP gap closes only 15–51%, and the six-task averages barely move (1.3B 0.588→0.588, 2.7B 0.626→0.627). Our serving formats are Q8_0 weights with an FP32 GDN core — a different baseline entirely. |
| **LQ-7** | claim 1, 7/7 `(σ,τ)` | If an int8 GDN prefill core is ever built, start from the write-gate placement, not from `R_QK`: it is a graph rewiring (`delta-net-base.cpp:72–73`) with no new kernel | `model-architecture-readiness.md` (INF-48) → `autokernel-loop.md` (INF-06) at execution | **trigger** (armed on LQ-1 ≥15%) | Experiment: FP32 fake-quant A/B at `(σ,τ) ∈ {(1,1),(½,1),(0,1)}` on a small GDN, WikiText-2 ΔPPL. *Expected:* `σ<1` wins under coarse scales (paper Fig. 11, `:829`) by ~0.05–0.1 PPL; exact zero change in FP32, so this only becomes visible with a quantizer. |
| **LQ-8** | T1 finding | Record that the seven invariances act on activations and **never** interact with Q4_K/IQ block layouts — the stage-1 "map onto per-32-block types" action is closed as mis-scoped | `quantization-and-low-bit.md` (INF-80) | **immediate packet** (documentation; closes a stage-1 recommended action) | No experiment. Direction: removes a would-be work item. |

---

## 7. Dive-surfaced sources

Checked against `research/intake_index.yaml` in the lane (grep on arXiv id and title; SSDi8 /
Quamba2 / FLA / GDN / QuIP# are already present, so they are *not* listed here).

| source | id | what it would settle | bears on |
|---|---|---|---|
| **DAMP: Decay-aware mixed-precision recurrent-state quantization** (Zhang et al., 2026) | arXiv:2608.27513 | Whether the state carry should be *decay-aware* rather than uniformly INT8 — i.e. whether Table 9's GDN/LA asymmetry is already exploited, and whether a mixed-precision state beats a single INT8 carry at equal bytes. The most direct competitor to LQ-5. | claim 3/4; T3 |
| **The key to state reduction in linear attention: a rank-based perspective** (Nazari & Rusch, 2026) | arXiv:2602.04852 | The cited origin of the `R_QK Λ = Λ R_QK` commutation condition, and whether the same key-axis basis freedom that LinQuant uses for quantization also supports state *pruning* at no quality cost (a cheaper byte win than quantization). | claim 1 (1/7); T1 |
| **The curious case of in-training compression of state space models** (Chahine et al., 2025) | arXiv:2510.02823 | Whether key-axis basis choice during *training* changes the state's quantizability — i.e. whether our models could be made rotation-friendly rather than post-hoc rotated. | claim 1; mechanism |
| **MambaQuant: quantizing the Mamba family with variance-aligned rotation** (Xu et al., 2025) | arXiv:2501.13484 | The closest prior art: mixer-agnostic rotations already adopted for Mamba. Settles how much of LinQuant's production gain is the *rotation* versus the *placement/calibration*, which the paper never isolates (§2, "control ABSENT"). | claim 4a; Q-E |
| **Quamba: a post-training quantization recipe for selective SSMs** (Chiang et al., 2024) | arXiv:2410.13229 | The INT8 SSM baseline that LinQuant's controlled study implicitly improves on; would bound how much of the 340M INT8 excess (0.38% PPL) is inherent to the recurrence vs the projections. | claim 2/3 |
| **Quantifying memory utilization with effective state-size** (Parnichkun et al., 2025) | arXiv:2504.19561 | Whether our GDN state is *effectively* much smaller than its nominal 262k elements — if so, the decode-state byte argument in T3 gets worse, not better, and LQ-5's trigger should be retired outright. | T3; LQ-5 |

---

## 8. Artifact audit

| artifact | path | status |
|---|---|---|
| Stripped source text (3,762 lines, 165,399 chars) | `/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/paper.txt` | clean — regenerable from `raw/arxiv2610.39418.html` (sha256 `531c4a61…b5ebb9`) by the tag-strip in §8.1 |
| Quote extractor + hasher | `/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/verify/quotes.py` | clean — 18/18 anchors resolved, exit 0 |
| Quote hashes | `/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/verify/quotes.json` | clean |
| This report | `/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/drafts/linquant-paper.md` | clean |
| Lane worktree | `/mnt/raid0/llm/worktrees/intake-quant-compiler-20261106` | **no writes by this dive**. `git status --porcelain` shows two modified paths — `.research-session.json` and `research/intake_index.yaml` — both mtime 16:02–16:03 UTC (before this dive's first write at 16:04) and both containing the *parent session's* stage-1 `intake-2641…2646` appends. No report file, no index row, and no handoff was written into the lane by this agent (a subagent may prepare, the owning session applies). |
| Frozen kernel tree | `/mnt/raid0/llm/llama.cpp` | **read-only** — no build, no branch change, no write; HEAD `ffc1bac82` on `production-consolidated-v10` |

### 8.1 Reproduction

```bash
cd /mnt/raid0/llm/tmp/dive-quant-compiler-20261106
sha256sum raw/arxiv2610.39418.html          # 531c4a6167431158eb4b3a4a3b26211fb74d12805392f9f162036f88f2b5ebb9
python3 verify/quotes.py                    # re-extracts and re-hashes all 18 quotes
sha256sum raw/paper.txt
cd /mnt/raid0/llm/worktrees/intake-quant-compiler-20261106 && git status --porcelain   # only the parent's 16:02-16:03 intake bookkeeping
cd /mnt/raid0/llm/llama.cpp && git rev-parse HEAD && git branch --show-current          # ffc1bac82 / production-consolidated-v10
```

### 8.2 Residual uncertainty (stated, not deferred)

- **Table 1 column mapping** is inferred from a flattened token stream. The row/column assignments are
  cross-checked against three independent prose statements (§3.2, App C, Fig. 2/3 captions) and are
  consistent, but the *rendered table* was never seen. If a later reader has the PDF, one glance
  settles it; nothing in this report's conclusions depends on a cell that the prose does not also state.
- **Figure 5(a), 15, 16** are vector graphics: the "no measurable latency" claim is the authors'
  wording plus a caption with no axis values readable as text. I did not and cannot quote a number
  from them.
- **The controlled study is INT6 on purpose** and its checkpoints are unreleased, so no number in §1.4
  is a deployment prediction; §1.5 (production) is the only deployment-shaped evidence, and it is
  single-lab.
