---
source: arXiv:2501.13484v3 — "MambaQuant: Quantizing the Mamba Family with Variance Aligned Rotation Methods" (Z. Xu, Y. Yue, X. Hu, Z. Yuan, Z. Jiang, Z. Chen, J. Yu, C. Xu, S. Zhou, D. Yang) — ICLR 2025
entry: intake-pending (absent from research/intake_index.yaml; only a passing mention at `research/intake_index.yaml:116165`)
dive: Stage-1 + Stage-2b combined, lane intake-quant-compiler-20261106
dive_date: 2026-11-06
read_depth: FULL-TEXT (abstract → §6 → Appendices A.1–A.9). All tables read and transcribed (Tab. 1–7). Figures 1–13 are images: NOT read; their captions and the prose describing them were read.
source_revision: arXiv:2501.13484v3, HTML rendering, `https://arxiv.org/html/2501.13484v3`; v1 2025-01-23, v3 2025-03-11
sha256: fa393a944e8ac2f61322e872b04d7e244bea537fc3b978c5b52c5c2dc6925228  (mambaquant.html, 390,874 bytes)
derived_text_sha256: bc4dddc1dd2c6a5076d411bc86e325869de043e9eecba06a6a371f9bf058b972  (mambaquant.txt — tags stripped, block elements to newlines, whitespace collapsed; **this is the text every line locator below refers to**)
quote_normalization: quotes are verbatim substrings of the normalized extraction; `quote_sha256` = sha256 of the quote with whitespace collapsed to single spaces and stripped. Every quote below was asserted to be a substring by `quotes.py`/`quotes3.py` before hashing (`present: true` for all rows printed; four candidate quotes were dropped as not-verbatim rather than paraphrased).
not_read:
  - Figures 1–13 (PNG/SVG). Captions and body prose read only. Fig. 2 (max/variance per channel pre/post rotation), Fig. 7/8 (quantile + quantisation-loss histograms), Fig. 9–11 (variance before/after Hadamard), Fig. 12 (KLT generalisation to OOD inputs), Fig. 13 (PScan amplification) are all asserted from caption text.
  - Released code (paper says it is published; no URL is given anywhere in the text — checked). No kernel is verified.
  - Quamba (arXiv:2410.13229), HadMamba2, I-LLM/S-SiLU primaries — cited only, not read in this dive.
external_content_safety: the paper was treated as DATA. No instruction, request or directive appearing in it was followed.
---

# MambaQuant — Stage-1 + Stage-2b dive

## 0. One-paragraph verdict

MambaQuant is the **ancestor** of the rotation dispute, and it answers the dispute's load-bearing
question in the opposite direction to the way SSDi8's abstract is usually read. It does **not** say
Hadamard rotation hurts Mamba. It says, with a proper fixed-granularity control the later papers never
ran, that rotation at unchanged granularity **helps** (+1.5/+6.6/+0.1/+4.8 points over RTN on the four
ablation cells, Tab. 3) and that a **variance-aligned** rotation helps enormously (+15.3/+7.1 offline,
+22.0/+30.1 online, Tab. 3–4). What fails is the *Transformer recipe* — rotate the projections, then
quantise the SSM-specific tensors per-tensor — which is exactly what SSDi8's HAD/QuaRot arm did and
exactly what MambaQuant diagnoses and fixes. Its central technical claim (Hadamard cannot equalise
channel variance; pre-multiplying by the calibration covariance's eigenbasis then Hadamard makes every
channel's variance exactly `Σλ/((n−1)m)`) is a **correct proof**, verified here line by line. The
implementation value for EPYC/MI210 is close to zero: Mamba-1 only, per-tensor quantiser, **no latency,
no device, no decode, no perplexity, no generation** — the entire result set is zero-shot accuracy.
Verdict on the three-way question: **EXTENSION** — LinQuant's `R_QK` extends SSDi8, and MambaQuant is
the mechanism-level evidence that makes that extension a supported prediction rather than a hope.

---

## 1. Stage-1 entry

| field | value |
|---|---|
| **title** | MambaQuant: Quantizing the Mamba Family with Variance Aligned Rotation Methods |
| **authors** | Zukang Xu\*, Yuxuan Yue\*†, Xing Hu, Zhihang Yuan, Zixu Jiang†, Zhixuan Chen, Jiangyong Yu, Chen Xu, Sifan Zhou†, Dawei Yang✉ (\*equal contribution, †internship at Houmo AI, ✉corresponding) |
| **affiliations** | Houmo AI; Harbin Institute of Technology (Shenzhen); Nanjing University; Southeast University |
| **venue** | **ICLR 2025** — verified outside the source (`proceedings.iclr.cc/paper_files/paper/2025`; OpenReview `KI45uDnmzv`). arXiv itself carries **no** comments or journal-ref field, so the venue is not provable from the primary source. |
| **id** | arXiv:2501.13484 [cs.LG], v1 2025-01-23 / v3 2025-03-11 |
| **categories** | `quantization`, `hardware_optimization`, `ssm_hybrid`, `inference_serving` |
| **novelty** | **medium** — a composition (QuaRot's absorbable rotation + SmoothQuant's per-channel scaling + PCA whitening), not a new primitive. What is genuinely new: (i) the *measured* demonstration that Hadamard alone cannot equalise channel variance and the exact construction that does, (ii) applying the smoothing **inside** the scan by absorbing it into `W_B`, `W_C` **and `Δ`** (Eq. 16), which is the only published trick in this lineage that reaches the recurrent state's own basis. |
| **relevance** | **high for the rotation dispute, low for implementation.** It is the missing third position on "does rotation help SSM quantization", and it is the only one of the three papers with a rotation-on/off control at fixed granularity. It is *not* a Mamba-2 SSD paper, has no latency measurement of any kind, and its quantiser granularity is per-tensor. |
| **verdict** | `adopt_patterns` — adopt the *mechanism* (variance-align before rotating; a rotation along an axis where decay is scalar is exact), decline the implementation. |
| **credibility_score** | **3** |

**Credibility arithmetic (rubric, additive).** peer-reviewed **+2** (ICLR 2025, verified);
≤12 mo **0** (published 2025-01, 22 months before this dive); major lab **0** (Houmo AI is a commercial
AI-accelerator vendor and the HIT/NJU/SEU groups are academic collaborators — not a major research lab);
commercial bias **0** (no vendor hardware is used, no product is named, no proprietary benchmark: the
usual bias channel is absent — but see the caveat that the paper reports *no hardware at all*, so
"commercial bias" has nothing to act on); independent corroboration **+1** (Quamba2 re-measured four of
MambaQuant's cells: Mamba1-1.4B W8A8 58.3 ✓ exact, 1.4B W4A8 54.3 ✓ exact, 2.8B W4A8 58.5 ✓ exact,
2.8B W8A8 61.8 vs 62.1 — see `research/deep-dives/quant-compiler-20261106/quamba2.md:293`). SSDi8 does
not compare against it. **Total 3.**

### key_claims (Stage-1)

1. **K1** — MambaQuant is "the first comprehensive PTQ design for the Mamba family", covering both
   Mamba vision (Vim, Mamba-ND) and language (Mamba-LLM), with weights **and** activations at 8-bit and
   <1 % accuracy loss.
2. **K2** — Transformer rotation fails on Mamba because **Hadamard does not equalise channel variance**:
   post-rotation variance still varies per channel, so a shared scale is wrong for most channels.
   QuaRot therefore loses 21 points on Vim-T† even at W8A8, and >12 % on Vim at 8 bits.
3. **K3** — **KLT-enhanced offline rotation** (`H_K = K H`, `K` = eigenvectors of the calibration
   covariance) makes every channel's post-rotation variance **exactly** `Σλ_j /((n−1)m)`, and is
   absorbed into weights so it is free at inference.
4. **K4** — **Smooth-fused online rotation**: a per-channel smoothing vector applied *before* the online
   Hadamard, absorbed into `W_g`/`W_o` (via S-SiLU), `W_B`, `W_C` and `Δ`, costs 0.01 % parameters and
   0.91 % MACs, and closes most of the remaining gap at the output projection and the matmul.
5. **K5** — W4A8 costs "about 1 %" on vision and delivers "significant accuracy improvements" over
   existing methods on language.

### techniques

- Offline: `X → X K H`, `K` from eigendecomposition of the calibration activation/weight covariance;
  applied to the LoRA module and the inter-block connection (output projection, gate projection, state
  projection) — QuaRot's offline design, ported to the Mamba block.
- Online: `S-SiLU(x,s) = x ⊙ σ(s ⊙ x)` with `W_g' = W_g ⊘ s_out`, `W_o' = s_out ⊙ W_o` (Eq. 15) —
  an **exact** reparameterisation, since `S-SiLU(y/s, s) = SiLU(y)/s`; then an `[m,m]` Hadamard on the
  activation with `Hᵀ` absorbed into the corresponding weight.
- Matmul/scan: smoothing `s_mm` transmitted through **both** sides of the scan's addition — absorbed by
  `W_B` (route through `B̄`) and by `Δ` via `addcmul(−ln(s_mm), Δ(1), A)` on the **first token only**
  (Eq. 16). This is the trick that puts a scale inside the recurrence.
- Hadamard widths used: `[16,16]` for the "matrix multiplication layer", `[5120,5120]` for the output
  projection of Mamba-2.8B (`mambaquant.txt:1309`).

### reported_results

| | FP16 | W8A8 | W4A8 |
|---|---|---|---|
| Vim-T / T† / S / S† / B | 76.1 / 78.3 / 80.5 / 81.6 / 80.3 | 75.6 / 77.8 / 80.3 / 81.4 / 80.1 | 72.1 / 73.7 / 79.4 / 80.4 / 79.8 |
| Mamba-ND 2d-S / 2d-B / 3d | 81.7 / 83.0 / 89.6 | 81.2 / 82.8 / 89.0 | 80.4 / 81.9 / 88.4 |
| Mamba-LLM 370m / 790m / 1.4b / 2.8b | 50.9 / 54.8 / 58.6 / 62.2 | 50.0 / 53.8 / 58.3 / 62.1 | 43.9 / 45.8 / 54.3 / 58.5 |

(Tab. 1 `mambaquant.txt:407-534`; Tab. 2 `:541-619`.) **Speedup / latency: none reported.** The only
efficiency figures are analytic: 329 k extra parameters (0.01 %) and 25.6 GFLOP on a 2.8 TFLOP baseline
(0.91 %) at L = 1024 (`:735`).

### limitations

- **No hardware, no wall-clock, no throughput, no decode.** Not "not in the abstract" — absent from all
  seven tables and nine appendices. No GPU is named anywhere in the paper. The efficiency claim is a
  hand-derived MAC count.
- **No perplexity, no generation, no long-context.** Five zero-shot classification averages
  (ARC-E/ARC-C/PIQA/WinoGrande/HellaSwag) and ImageNet/UCF-101 top-1 only.
- **Mamba-1 only.** §3.2 defines the selective scan (`Δ = Softplus(LoRA_Module(x'))`, Eq. 3–6); there is
  no chunked SSD, no `ChunkState`, no `B`/`C`/`CB` chunk decomposition. Nothing here is Mamba-2.
- **Quantiser granularity never stated.** The only occurrence of the word in the paper is "the 4-bit
  per-tensor method" in a *loss-visualisation* caption (`:679`); smoothing is one scalar per quantisation
  channel (`:734`). A reader must infer SmoothQuant-style per-tensor activation quantisation.
- **Weight-only 4-bit is admitted to fail** (App. A.1, `:1107`).
- **KLT cannot be applied online** — eigenvalue decomposition per step (`:1108`).
- **The `[5120,5120]` Hadamard is not a power of two**, so the cited `O(n log₂ n)` transform
  (Fino & Algazi 1976, Sylvester orders) does not apply as written; the composite construction is never
  given and the 0.91 % is not reproducible. See §5.
- **Does not cite Quamba** (`arXiv:2410.13229`, 2024-10-17) — a Mamba PTQ method, itself a *static
  per-tensor SSM* quantiser, that predates it by three months. Full-text grep for "Chiang" and
  "Quamba" returns **zero** hits.

---

## 2. Per-claim adjudication

| # | Claim | Verdict | Locator | Verbatim quote | quote_sha256 |
|---|---|---|---|---|---|
| 1 | First comprehensive PTQ for the Mamba family (vision + language) | **PARTIAL** — true for "vision **and** language" together; false as "the first PTQ solution specifically designed for Mamba models", since Quamba is uncited and predates it | `mambaquant.txt:134`, `:220` | "To the best of our knowledge, MambaQuant is the first comprehensive PTQ design for the Mamba family, paving the way for further advancements in its application." | `4ea3931081d1ce1f9a4053c4cb49d60a8c3b74455539f3c1b88ffda5186fc838` |
| 1b | (the stronger form) | **OVERTURNED** | `:220` | "Notably, to our knowledge, our method is the first PTQ solution specifically designed for Mamba models, applicable to both Mamba-based vision and language tasks." | `125649062f5619c6cf0f875651867bc2c9fad8df5e03147ec35bcebe6c8c95da` |
| 2 | W8A8 <1 % loss on vision **and** language | **PARTIAL** — vision max drop 0.6 ✓; language Mamba-790m drops **exactly 1.0** (53.8 vs 54.8), so the "for all models" form at `:185` fails on one cell | `:134` | "Experiments show that MambaQuant can quantize both weights and activations into 8-bit with less than 1% accuracy loss for Mamba-based vision and language tasks." | `f08a610a93e4373f65d8d7b40668c166f21dff368a9baea967b9eb88f300e5d3` |
| 3 | QuaRot loses 21 % on Vim-T† at W8A8; >12 % on Vim at 8 bits | **OVERTURNED as written** — 21 % is 20.9 **percentage points** (78.3→57.4), not percent (26.7 % relative); the ">12 %" number reproduces in *neither* unit (5-model mean 79.36→67.96 = **11.40 points / 14.4 % relative**) | `:131`, `:168` | "Quarot suffers a 21% accuracy drop on Vim-T† even under W8A8" | `e2ef6551b23433c4273f5bf69c8f4f4c28fc468fe1d0ae54aa8415229ab5899b` |
| 3b | (the 12 % form) | **OVERTURNED** | `:168` | "However, directly applying this method to Mamba models leads to significant accuracy degradation (e.g., on average more than 12% accuracy drop on Vim (Xu et al., 2024) even at 8 bits)." | `d317f684ca54a83249b4d4835f09441bf7df3da490711ce0a10edc34652a29b0` |
| 4 | The failure is **variance misalignment**, not rotation | **CONFIRMED** — derivation verified (Eq. 8–9, App. A.2–A.3); the failure mode is "un-aligned", not "harmful" | `:169`, `:309` | "Our analysis reveals that Hadamard transformation fails to achieve variance alignment across channels, as shown in Figure 2(b)(e)." | `a058ab30126b5fcb9ccfa367ab306b7c1eff2574fb9bdffa24e916d4e9f8e8a3` |
| 4b | (the causal word) | **CONFIRMED** — "sub-optimal", never "harmful" | `:309` | "This property of Hadamard transformation inevitably formulates a distinct distribution for each channel, thus leading to sub-optimal quantization." | `efd5a7dfa423c652975fb7fffc020d862ba9a060a1d368d4eb745395cf5a5385` |
| 4c | Why a fixed orthogonal transform cannot fix it | **CONFIRMED** — `λ` and `K` are input-dependent, `H` is not | `:308` | "it is not feasible for the Hadamard transformation to uniformly adjust the channel variances across all scenarios." | `4704d0fed71b9cc327248382f2731ce13973dc1ea04bc2489f03c6c386a08f7e` |
| 5 | KLT∘Hadamard equalises variance exactly | **CONFIRMED (math)** — Eq. 12–13: with `K` orthogonal, `C_{XH_K} = HᵀΛH`, so `(C)_ll = Σλ_j/((n−1)m)` for every `l` | `:339` | "In this way, the variance of each channel becomes the same, making quantization much easier." | `6e0d1a1006dde6b71d09feb8d90b4113d1252434a77f5b4ac0996c10fa17d37f` |
| 6 | Smoothing before the online Hadamard is the online fix | **CONFIRMED** | `:352`, `:391` | "The motivation of employing this method is to uniform the channel variances through a smoothing vector." | `0baa2ff9d6154c0cb02edf4ff84ec64d9285836312269013f6fa6a14b1818e43` |
| 6b | (result) | **CONFIRMED** | `:391` | "After smoothing, the channel variances of activations for the output projection and the matrix multiplication becomes relatively uniform." | `203a9b243945f3e83db70cef369ccee40a97ea3f34bf5ffc1fe3220be38d0746` |
| 7 | Offline KLT is free at inference (calibration-time only) | **CONFIRMED** | `:342` | "In practice the KLT is offline performed by using the calibration data to avoid extra computational costs." | `a8de65f46a1a39aea79ea8b4f4a78fda73d5418a43f3d8ad4ad946c9290cf8e2` |
| 8 | 0.01 % params / 0.91 % MACs | **CONFIRMED arithmetic, PARTIAL as a claim** — 329 k/2.8 G = 0.0118 % ✓; `(5120+16)×64 = 328,704` ✓; 25.6 GFLOP/2.8 TFLOP = 0.914 % ✓; but both sides are MAC counts (`params × tokens`), not measured time, and the 5120-point transform is not a `2^k` FWHT | `:735`, `:1303` | "Taking the Mamba-2.8B model as an example, the smooth scale adds only 329k parameters to the 2.8B model, while for a token sequence length of 1024, the computational increase is 25.6 GFLOPs over the baseline 2.8 TFLOPs." | `172c8e79df428b909fc7de160d79e2c0cf197f73ead4fb5b2465e16bb773656f` |
| 8b | (the parameter split that identifies the smoothing axes) | **CONFIRMED** — 5,120 = `d_inner` (S-SiLU) and **16 = `d_state`** (the matmul/Δ route). This is the hard evidence for §3.3 | `:1303` | "In our Method 4.3, we integrated a smoothing process by replacing the SiLU activation function with the S-SiLU activation function, which added 5,120 smoothing scale parameters. Additionally, we modified the mul operation to an addcmul operation, contributing an additional 16 parameters." | `ec008779995a9cd0f963701f0afe4418b9d62f2697c8e02bbe3d25a4e7b5c198` |
| 9 | W4A8 costs "about 1 %" on vision | **OVERTURNED** — Vim-T −4.0 (76.1→72.1), Vim-T† −4.6 (78.3→73.7); only Vim-S/B/ND are ≈1 % | `:186` | "Additionally, it can quantize weights to 4-bit with a minimal accuracy drop (about 1%) for vision tasks, and achieves significant accuracy improvements in language tasks compared to existing methods." | `c0c9b5202627e4f4b6af93d7c1003cee2830af6b273020cbaf99db3cb8e0eccd` |
| 9b | (the paper's own admission) | **CONFIRMED — and it overturns 9** | `:1107` | "While this approach can effectively quantize the weights and activations of Mamba models into 8-bit with less than a 1% drop in accuracy, it struggles to maintain such a high level of accuracy when quantizing weights to 4-bit." | `2aff5ae51772987eefe92f206119b72d65f0e33ede588d3e1d3b73005fa80692` |
| 10 | PScan amplifies outliers | **CONFIRMED** (qualitative + A.8 magnitudes); Fig. 13 unread | `:1824` | "It has been observed that following the application of the pscan operator, the distribution differences of activation values in the hidden dimension become more pronounced." | `f88dd13946295f47bcfa837d2d3e2fcc2690daab733a6718a7e61ce148cb33ca` |
| 11 | KLT cannot be applied online | **CONFIRMED** (and the sentence contains a typo: "efficiently constrained" reads as "computationally constrained") | `:1108` | "In addition, we note that the proposed Karhunen-Loève Transformation (KLT) enhanced rotation is efficiently constrained if applied to the online Hadamard rotation." | `11072785e55b69747aecdf9c015f0def5574879b5fdd5090272ac0fb6040c89d` |
| 12 | Hadamard performs "less satisfying" on the hard layers | **CONFIRMED** — note the wording: insufficient, never harmful | `:741` | "Secondly, we find that Hadamard transformation method widely adopted in Transformer quantization performs less satisfying when quantizing these hard layers." | `c2ab6e306335f85c0b2431d34781e20b5cac7598602ae823e44bbda352093010` |
| 13 | Only the *shape* of the quantiser granularity is stated | **CONFIRMED** — one occurrence, in a loss simulation | `:679`, `:734` | "while the lower part illustrates the quantization loss distribution using the 4-bit per-tensor method" | `b4e9b6b8b3bf2143db507980fcc92dd743bb69eb72d96606dfc46c16b228b7bc` |
| 13b | (per-channel smoothing, i.e. per-tensor quant + per-channel scale) | **CONFIRMED** | `:734` | "with minimal storage overhead since each quantization channel is represented by a single scalar" | `b32c834957324d55a877a2028bc559d9ce9a0be16b11d98fe0efb2e653a5f2a2` |

**Systematic number-hygiene defect: every "%" in this paper is a percentage point.** Confirmed on three
independent cells — "21 %" = 20.9 pts (`:131`), "about 14 % higher than the direct hadamard method" = 13.8
pts (`:676`), "11.7 % ahead" = 11.7 pts (`:730`). Any citation must convert to points.

**A third defect: the Table 3 arrow.** W4A8 Vim-T† KLT-Enhanced prints `38.9(↑3.9)` (`:669`) but
25.0 → 38.9 is **+13.9**; every other arrow in Tab. 3–4 checks out (15.3, 7.1, 6.9, 22.0, 0.5, 23.1,
0.7, 30.1, 2.0, 34.8, 3.5). The 3.9 is a dropped leading digit.

**Two table defects.** Tab. 4's FP16 Mamba-790M reads **54.6** in the W8A8 block and **58.6** in the W4A8
block (`:692-699`), while Tab. 2 and Tab. 6 both give **54.8** — and 58.6 is Mamba-1.4B's FP16 value, so
the W4A8 block copied the wrong row. Tab. 4's W8A8 "+Smooth-Fused" 790M is 53.3 vs Tab. 2/6's 53.8.
None of these move a conclusion; they do mean the ablation deltas carry ±0.5.

---

## 3. THE LOAD-BEARING QUESTION

> *Does MambaQuant demonstrate that rotation-based smoothing improves SSM quantisation, or does it
> agree that naive rotation hurts? What exact mechanism and scale granularity does it use? Settle whether
> LinQuant's `R_QK` contradicts or extends SSDi8.*

### 3.1 Direct answer

**Both, at different granularities — and the distinction is the whole finding.** The paper contains a
rotation-on/off control at **fixed** granularity that neither SSDi8 nor LinQuant ran, and rotation is
**positive in all four cells**:

**Tab. 3** (`mambaquant.txt:627-670`) — same per-tensor quantiser, only the rotation differs:

| arm | Vim-T† W8A8 | Mamba-790m W8A8 | Vim-T† W4A8 | Mamba-790m W4A8 |
|---|---|---|---|---|
| RTN (no rotation) | 32.4 | 44.2 | 25.0 | 35.4 |
| **+ Hadamard** | **33.9 (+1.5)** | **50.8 (+6.6)** | **25.1 (+0.1)** | **40.2 (+4.8)** |
| + KLT-Enhanced (variance-aligned) | 47.7 (+15.3) | 51.3 (+7.1) | 38.9 (+13.9) | 42.3 (+6.9) |

**Tab. 4** (`:681-724`) — same KLT baseline, only the *online* rotation differs:

| arm | Vim-T† W8A8 | Mamba-790m W8A8 | Vim-T† W4A8 | Mamba-790m W4A8 |
|---|---|---|---|---|
| KLT only (no online rotation) | 47.7 | 51.3 | 38.9 | 42.3 |
| **+ online Hadamard** | **69.7 (+22.0)** | **51.8 (+0.5)** | **62.0 (+23.1)** | **43.0 (+0.7)** |
| + smooth, *then* Hadamard | 77.8 (+30.1) | 53.3 (+2.0) | 73.7 (+34.8) | 45.8 (+3.5) |

So: **naive rotation helps a little; unaligned rotation on top of a per-tensor quantiser helps a lot;
aligned rotation helps enormously.** Nothing in this paper supports "rotation hurts". The claim
"MambaQuant agrees naive rotation hurts" is **OVERTURNED**.

What *does* hurt is the Transformer recipe applied without touching the SSM-specific tensors. QuaRot's
Mamba loss is real and large — Vim-T 76.1→59.3, Vim-T† 78.3→57.4, Vim-S 80.5→73.8 at W8A8 — but QuaRot
rotates the residual stream and leaves the PScan output / matmul operand per-tensor-quantised, which is
precisely the arm MambaQuant's Table 4 shows is worth +22 points to fix. QuaRot is *MambaQuant with the
two hard layers removed*, not "rotation".

### 3.2 The exact mechanism, and its granularity

**Offline (weights + inter-block, absorbable, exact).** For a centred `X ∈ R^{n×m}` with covariance
`C_X = KΛKᵀ/(n−1)`, apply `X → X K H`. Then `H_K = KH` is orthogonal, `KᵀK = I`, and

```
C_{XH_K} = Hᵀ Λ H /(n−1)   ⇒   (C_{XH_K})_ll = Σ_j λ_j /((n−1)m)   for every l     (Eq. 13)
```

Every channel gets the *same* variance. Verified: the algebra is correct and the claim is exact, not
approximate. Two things worth stating precisely because the paper's framing blurs them:

1. **KLT alone does *not* equalise variance.** After `XK` the variances are `λ_j/(n−1)` — still ordered
   and still unequal; that is what PCA *is*. The equalisation is done by the **Hadamard acting on
   whitened data** (`Hᵢⱼ² = 1/m` turns `HᵀΛH` into a scalar multiple of `I`). "KLT-enhanced rotation"
   is therefore correctly named only as a *pair*; the Hadamard is load-bearing.
2. **It is exact only for the calibration distribution.** `K` is estimated from calibration data and
   fixed (`:342`); App. A.7 argues by figure (Fig. 12) that it generalises, and admits only the claim
   that on dissimilar inputs it is "still not worse than" Hadamard. No OOD number is given.

**Online (activations, exact reparameterisation, fused).** `s_out` enters through `S-SiLU`;
`s_mm` enters through **both** sides of the scan's addition and is absorbed into `W_B` and into `Δ` via
`addcmul(−ln(s_mm), Δ(1), A)` on the first token. Then an `[m,m]` Hadamard is applied to the activation
with `Hᵀ` folded into the weight. Because `S-SiLU(y/s,s) = SiLU(y)/s` exactly, and because a rotation
`H` that is absorbed into `W_B`, `W_C` and `Δ` leaves the block function unchanged, the whole online
transform is algebraically free — the cost is the per-token `[m,m]` butterfly, not a new error term.

**Granularity: per-tensor activation quantisation with one smoothing scalar per channel.** The deployed
granularity is never stated; the only granularity word in the paper is "per-tensor" in a loss-visualisation
caption, and the smoothing vector is "one scalar per quantization channel". This matters more than
anything else in the paper for transfer: their entire gain is the gain of making a **per-tensor** scale
survive SSM activations. `q4_K`/`q8_0` already have per-32-block scales, so the marginal value of the
same rotation in our tree is a fraction of theirs.

### 3.3 The finding that actually decides the dispute: the rotation axis is `N`

The paper never names the axis of its `[16,16]` Hadamard. It does not have to — three locators pin it:

1. The rotated tensor is "the output of the parallel scan (PScan) operator, which is also one of the
   input to the matrix multiplication" (`:157`), i.e. the recurrent state `h`, not a projection.
2. The transform width is **16** (`:1309`), which is `d_state` for every Mamba-1 size; `d_inner = 5120`
   is used separately for the output projection. A width-16 transform cannot be a `d_inner` rotation.
3. The smoothing vector for that layer adds **exactly 16 parameters per block** (`:1303`), and is
   absorbed into `W_B` and `W_C` — whose *output* dimension is `d_state = 16`. A length-16 vector could
   not be absorbed into a 5120-wide projection.

**Therefore MambaQuant applies a 16-point Hadamard along the state axis `N`, with a per-channel scale
absorbed inside the scan.** This is not an incidental detail: `N` is the axis SSDi8 **explicitly
excluded from quantisation** ("it directly participates in subsequent matrix multiplications, where
quantization errors cannot be restored", `ssdi8.md` §2 item 5) and the axis LinQuant's `R_QK` rotates.
MambaQuant rotated it in 2025 and got +22 to +30 points at W8A8 on Vim.

Why it is exact there is the bridge to LinQuant: along `N`, Mamba-1's decay `Ā = exp(A ⊙ Δ)` is a
per-channel **scalar** (constant in `N`), so it commutes with any `N`-axis rotation — LinQuant's
sufficient condition, "Invariance thus holds with no decay or scalar decay."
(`linquant-paper.md:240`). MambaQuant found the same invariance empirically some 21 months earlier and never
stated the commutation condition; the cost of not stating it is that the paper cannot say *which* axes
may be rotated, which is exactly the question SSDi8 got wrong.

### 3.4 Verdict: EXTENSION (and, at mechanism level, a refutation of SSDi8's general claim)

| position | statement | status after MambaQuant |
|---|---|---|
| **SSDi8** (ICLR 2026) | "directly applying … Hadamard rotation … to SSD layers leads to substantial accuracy degradation" | **Stands only as a description of the recipe it tested** (rotate projections + per-tensor RTN on SSD inputs). Its own Tab. 10 shows the delta is scale granularity, and MambaQuant's Tab. 3 shows rotation at fixed granularity is *positive*. **The general causal claim is refuted.** |
| **LinQuant** `R_QK` (2026) | rotate `q`,`k` along the key/state axis, fuse into operand prep, exact iff `R` commutes with decay | **EXTENSION of SSDi8** — it rotates the axis SSDi8 refused — **and now mechanism-supported, not merely compatible**: MambaQuant is a worked, measured instance of the same invariance on the adjacent architecture, with a variance-alignment fix LinQuant does not have. |
| **MambaQuant** (this paper) | rotation is right; **unaligned** rotation is weak and the Transformer recipe is catastrophic | Occupies the third position: it is neither "rotate" nor "don't rotate" but "**align, then rotate, along an axis whose decay is scalar**". |

**Verdict: EXTENSION — CONTRADICTION would be wrong and ORTHOGONAL would be wrong.** Not orthogonal:
all three are making claims about the same object (channel-variance structure of SSM operands under a
rotation), and MambaQuant's Tab. 3/4 are the missing control. Not contradiction: nothing in MambaQuant
says `R_QK` is invalid, and the axis/architecture differ (Mamba-1 scan vs Mamba-2 chunked SSD).

**Two honest scoping caveats.** (i) MambaQuant predates both and never mentions SSD, Mamba-2, Quamba or
`R_QK`; it is evidence about the *mechanism*, not a head-to-head. (ii) Its own rotation axis (`N` in
Mamba-1) is rotated as a **dense 16×16** transform applied to a tensor that SSDi8 says must stay FP16;
the arithmetic that makes it legal (scalar decay along `N`) is *the same* in Mamba-2, so the transfer of
the mechanism is sound, but the transfer of the *number* (+22 pts) is not: SSDi8/LinQuant already have
per-(H,P)/(H,D_v) scales, so the baseline it beats does not exist here.

---

## 4. What is actually reported

| axis | reported? |
|---|---|
| **bit widths** | W8A8 and W4A8 only. No W4A4, no W4A16, no sub-4-bit. |
| **models** | Vim-T/T†/S/S†/B (ImageNet); Mamba-ND 2d-S/2d-B/3d (ImageNet / UCF-101); Mamba-LLM 130m, 370m, 790m, 1.4b, 2.8b (5-task zero-shot). |
| **accuracy** | Tab. 1–2; W8A8 mean drop 0.36 (vision) / 0.58 (language); W4A8 mean drop 1.88 (vision) / 6.00 (language). |
| **speedup** | **None measured.** Only the analytic 0.91 % MAC increase. |
| **latency / throughput** | **Absent.** No device named in the paper. No ms, no tok/s, no TTFT, no batch sweep. |
| **decode / generation** | **Absent.** Every evaluation is teacher-forced zero-shot classification or top-1 image accuracy. No PPL (no WikiText anywhere), no generation task, no long-context. |
| **memory** | Only the 0.01 % parameter count. No bytes, no KV-cache accounting. |

**Where the W4A8 language headline actually comes from** (Tab. 2, `:590-619`) — the claim is
"consistently outperforms baseline techniques by a significant margin", but against QuaRot the margin
is one model:

| Mamba-LLM W4A8 | 370m | 790m | 1.4b | 2.8b |
|---|---|---|---|---|
| QuaRot | 43.4 | 40.0 | 53.8 | 58.5 |
| Ours | 43.9 | **45.8** | 54.3 | **58.5** |
| Δ | +0.5 | **+5.8** | +0.5 | **0.0** |

Against RTN/GPTQ/SmoothQuant the W4A8 gains are large and real (+5 to +10); against QuaRot they are
+1.7 mean and entirely carried by Mamba-790m. The second contribution (online smooth-fused rotation) is
likewise a **vision** effect: +22.0/+23.1 on Vim-T† but **+0.5/+0.7** on Mamba-790m (Tab. 4). Any claim
of the form "this fixes Mamba language quantisation" is unsupported at ≥1.4B.

---

## 5. Transfer to EPYC / MI210

**Conclusion: nothing here should be built now; three things should be recorded.** Decisive, per piece:

1. **Online smooth-fused rotation — DECLINE.** It requires a per-token `[16,16]` (and `[5120,5120]`)
   transform *inside* the recurrence, i.e. a new per-layer matmul on the state path. Our GDN/Mamba
   recurrence is FP32 (`ssdi8.md` §7: `GGML_OP_SSM_SCAN` CPU f32, and the linquant dive's T2), so there
   is no int8 state to protect and the rotation buys nothing while costing a pass per token. On
   band-width-bound EPYC decode that prices strictly negative; on MI210 it breaks the fused state update
   for a quality lever we cannot spend. Same verdict the Quamba2 and LinQuant dives reached for their
   rotations.
2. **Offline KLT∘Hadamard — DECLINE as a conversion step, PROBE as one arm.** `K` is dense `m×m` and
   calibration-derived: a new per-model artifact class that ends the "any GGUF" property, for a gain
   measured against a per-tensor quantiser we do not use. `q4_K`/`q8_0` already carry per-32-block
   scales, which is most of what the KLT is buying. Worth one arm inside the **already-proposed**
   Q2-2 permutation probe (32-wide Hadamard vs KLT∘32-wide vs permutation, fixed per-32-block budget,
   block-amax/clipping error + ΔKLD, no kernel, no GGUF change) — not a new task.
3. **S-SiLU reparameterisation — DECLINE for now, and it is only exact because it is trivial.**
   `S-SiLU(y/s,s)·s = SiLU(y)`, so it is an exact per-channel scale transfer with zero runtime cost
   *if* we ever per-tensor-quantise the gate output. We do not (W4A16 on CPU has no activation
   quantiser; the KV path is unaffected). Recorded as the one genuinely free piece, gated on an
   activation-quantised decode path existing.
4. **The `[5120,5120]` Hadamard — a spec gap, not an option.** 5120 = 2¹⁰·5 is not a Sylvester order, so
   the cited `O(n log₂ n)` FWHT does not apply as written; a dense transform would be 5120² ≈ 26.2 M MAC
   per token per block ≈ **61 %** of their own 2.8 TFLOP baseline, i.e. ~67× their stated 0.91 %. They
   must be using a blocked/composite construction (Fino & Algazi's "unified matrix treatment" covers
   composite orders) but never say so, and the FLOP table cannot be reproduced. For us the live width is
   16 (trivially a 2⁴ butterfly) and our shipped WHT is 64
   (`handoffs/active/quantization-and-low-bit.md:684-688`, upstream `744c0c731`).
5. **Supersession, stated plainly.** As an **implementation** source MambaQuant is superseded on both
   sides: SSDi8 dominates the compute side (Mamba-2, measured on A5000 and Orin NX, decode-shaped
   caveats documented) and Quamba2 dominates the weight side (W4A16, 8B, generation + kernel numbers).
   As **evidence** it is *not* superseded and cannot be: it is the only one of the three with a
   rotation-on/off control at fixed granularity, so it is the citation of record for "rotation is not
   the problem; variance alignment is".

---

## 6. Derived-actionables ledger

| ID | Action | Owning lane handoff | Disposition |
|---|---|---|---|
| **MQ-1** | Ingest MambaQuant as a new entry (`arxiv_id 2501.13484`, ICLR 2025, credibility 3, `adopt_patterns`), cross-referenced to intake-2641 (LinQuant), intake-2645 (SSDi8), intake-2646 (Quamba2). It is the named baseline of two of those three entries and has **no entry at all** — only a passing mention at `research/intake_index.yaml:116165`. | `handoffs/active/quantization-and-low-bit.md` (INF-80) | **immediate** (record). Prepared here; the owning session applies the YAML. |
| **MQ-2** | Upgrade the SD-4 record: SSDi8's "rotation degrades SSD" is now **refuted as a general claim** by a fixed-granularity control (Tab. 3: +1.5/+6.6/+0.1/+4.8 over RTN) and by the axis finding in §3.3. Change intake-2641's `contradicting_evidence` from "tension, unreconciled" to "**boundary extension, mechanism-supported; no Mamba-2 head-to-head**". | `handoffs/active/model-architecture-readiness.md` (SD-1/SD-4) | **immediate** (record correction; no experiment). |
| **MQ-3** | Amend SD-1's probe design: arm (b) (N-axis Hadamard at fixed granularity) is no longer exploratory — its *sign* is now predicted positive, and its *effect size* is predicted to shrink with scale granularity (per-tensor +22 pts → per-(H,P) unknown). State both predictions and the falsifier before running. | `handoffs/active/model-architecture-readiness.md` (SD-1) | **immediate** (amend the pre-registration); probe itself stays as filed. |
| **MQ-4** | Add a third arm to the existing Q2-2 channel-permutation probe: 32-wide Hadamard and KLT∘Hadamard vs magnitude-sorted permutation, at a fixed per-32-block budget, on one real `Q4_K` row — block amax/clipping error, weight-block scale error, ΔKLD. No kernel, no converter change. | `handoffs/active/quantization-and-low-bit.md` (INF-80) | **probe** — merge into Q2-2, do **not** open a new task; one experiment, three transforms. |
| **MQ-5** | Record the rotation-hazard entries: (i) `[5120,5120]` is not a `2^k` order so the cited `O(n log n)` cost is unreproducible — any port must name the composite construction; (ii) their "0.91 %" is a MAC count against a `params × tokens` baseline, not time; (iii) every "%" in this paper is percentage points. | `handoffs/active/quantization-and-low-bit.md` (hazard register, next to SD-3) | **trigger** — armed on any rotation port or on any citation of these numbers. |
| **MQ-6** | Decline the implementation wholesale: online smooth-fused rotation, offline KLT, S-SiLU. Reason (one sentence, for the record): per-tensor quantiser + Mamba-1 + zero latency/decode evidence ⇒ the measured benefit is against a baseline we do not ship, at a cost profile (per-token transform inside an FP32 recurrence) we cannot amortise. Re-open only if an INT8 state path lands (LQ-1) **and** someone proposes per-tensor activation quantisation. | `handoffs/active/quantization-and-low-bit.md` (INF-80) | **decline** (with reason), recorded. |

---

## 7. Dive-surfaced sources not in `research/intake_index.yaml`

Checked by literal grep on the lane index (`grep -c -i -F`), all **0** hits:

| Source | What it would settle |
|---|---|
| **Quamba** — Chiang et al., `arXiv:2410.13229` (2024-10-17) | The precedence check for MambaQuant's "first PTQ solution specifically designed for Mamba models" — a Mamba PTQ method that predates it and that MambaQuant **never cites** (zero full-text hits for "Chiang"/"Quamba"). Needed only if anyone repeats the first-claim; no lane decision currently depends on it. |
| **I-LLM / S-SiLU** — Hu et al., `arXiv:2405.17849` | Whether the S-SiLU reparameterisation survives *integer-only* inference and what it costs outside the fold. This is the only piece of MambaQuant that is free at runtime, so it is the only one worth reading if an activation-quantised decode path is ever proposed. |
| **HadMamba2** — Chiang et al. 2025a, cited by SSDi8 as its "HAD" baseline | Whether the HAD baseline Quamba2 inherits is *identical* to MambaQuant's Tab. 4 "Hadamard Rotation" arm. If it is, then MambaQuant's +22-point rotation gain is measured on exactly the configuration SSDi8 used to conclude rotation is harmful — which would make the refutation in §3.4 airtight rather than analogical. |
| **RepQ-ViT** — Li et al., `arXiv:2303.15105` | The origin of "reparameterise the scale out of the activation into the preceding op" for vision transformers; the ancestor of S-SiLU. Low priority — the mechanism is already fully stated here, so this would only add lineage. |

Not surfaced for ingest: Fino & Algazi 1976 (the FWHT algorithm, referenced for the complexity bound
only) and Mamba-ND (the vision model, not a quantisation source).

---

## 8. Artifact audit

| Artifact | Path | sha256 | Note |
|---|---|---|---|
| Paper HTML v3 | `/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/mambaquant.html` | `fa393a944e8ac2f61322e872b04d7e244bea537fc3b978c5b52c5c2dc6925228` | 390,874 B; fetched 2026-11-06; primary source |
| Tag-stripped text | `…/raw/mambaquant.txt` | `bc4dddc1dd2c6a5076d411bc86e325869de043e9eecba06a6a371f9bf058b972` | 1,870 lines / 9,118 words; **all line locators refer to this file** |
| Quote verifier | `…/raw/quotes.py`, `…/raw/quotes2.py` | `a90147a992a2ea403c735dbcab281a691d1ce524556252876261ac4f638d77bd`, `29c57700c700721ed674b27862526d26b95c0add51277478c44c5a5fcbf23eb6` | asserts each quote is a verbatim substring before hashing |
| Locator/hash finaliser | `…/raw/quotes3.py` → `…/raw/quotes.json` | — | builds a char→line offset map so locators are exact; 4 candidate quotes were **dropped** (not-verbatim) rather than paraphrased |
| Metadata evidence | arxiv.org/abs/2501.13484 | — | `citation_date 2025/01/23`, `online 2025/03/11`, no comments / journal-ref field |

Reproduction: `cd …/raw && sha256sum mambaquant.html mambaquant.txt && python3 quotes.py && python3 quotes3.py`.
A `MISS` from `quotes.py` or `line=None` from `quotes3.py` means a quote in this report is not verbatim
and must not be cited.

Environment note: the lane worktree `/mnt/raid0/llm/worktrees/intake-quant-compiler-20261106` was read
**read-only** (`research/intake_index.yaml`, `handoffs/active/quantization-and-low-bit.md`,
`handoffs/active/model-architecture-readiness.md`, `research/deep-dives/quant-compiler-20261106/{linquant-paper,ssdi8,quamba2}.md`).
Nothing was written into it. Every locator above is a lane path or a dump path under
`/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/`.
