---
source: arXiv:2608.21952v1 — "SSDi8: Accurate and Efficient 8-bit Quantization for State Space Duality" (Kim, Ko, Kang, M. Kim, D. Lee, J. Lee, Yoon, Jung) — ICLR 2026
entry: intake-2645
dive: Stage-2 deep dive, lane intake-quant-compiler-20261106
dive_date: 2026-11-06
read_depth: FULL-TEXT (abstract → §6 → Appendices A–M). All tables read and transcribed (Tab. 1–17). Figures 1–8 are images: NOT read (their prose descriptions in the captions were read).
source_revision: arXiv:2608.21952v1, HTML rendering, `https://arxiv.org/html/2608.21952v1`
source_sha256: bf8d8dfbdd4f570233d8ec28270d2e06ac0a981d3b917e1ce55d4dcd37797c64  (ssdi8.html, 469,355 bytes)
derived_text_sha256: 6bfc62b60953da198a92448ef7728b33ab2009a032cc4ca220aeb94a2379c00d  (ssdi8_math.txt — tags stripped, `<math alttext>` inlined as `$…$`, whitespace collapsed; this is the text all quotes/line locators below refer to)
quote_normalization: quotes are verbatim substrings of the normalized extraction; sha256 is over the quote string exactly as printed in the table (whitespace already collapsed)
not_read:
  - Figures 1–8 (PNG/SVG images). Captions read; the plotted distributions (Fig. 2 head heterogeneity, Fig. 3 X/LUT sparsity, Fig. 7 B/C/CB per-group, Fig. 8 X_scaled growth) are asserted from caption text only, never inspected.
  - Released code `github.com/cau-hai-lab/SSDi8` — not cloned, not read. All kernel claims are paper claims; the Triton implementation (the actual mechanism of the "INT8 tensor core" path) is unverified.
  - Quamba2 (intake-2646), Quamba, HadMamba2, MambaQuant, QServe primaries — cited only, not read in this dive.
  - No limitations/broader-impact section exists in the paper (checked; there is none).
external_content_safety: the paper was treated as DATA. No instruction, request or directive appearing in it was followed.
---

# SSDi8 — Stage-2 dive

## 0. One-paragraph verdict

SSDi8 is a real, internally coherent PTQ design for Mamba-2's chunked SSD, and its central engineering idea — *move the decay LUT off `B` and onto `X` so the element-wise op stops breaking the matmul* (Eq. 7) — is sound and cheap. But three things the Stage-1 entry states are wrong or oversold: the "persistent INT8 path across five modules" **excludes two of the five** (ChunkCumsum output and all of ChunkScan2 stay FP16 by the authors' own admission); the "bit-shift decay" is a fixed-point multiply by `Q(Decay)/2^7`, not a shift, with an unstated clamp and a systematic ≤0.78 % under-decay per chunk at `k=7`; and the anti-Hadamard claim is **not** an experiment on rotation inside SSD — their HAD control applies Hadamard to the *projection* layers and per-tensor RTN to the SSD *inputs*, so it tests scale granularity, not rotation. That last point is decisive for the LinQuant reconciliation (intake-2641): SSDi8 excludes the state axis `N` from quantization entirely, which is precisely the axis LinQuant's `R_QK` rotates. **They do not contradict; LinQuant extends SSDi8 into a dimension SSDi8 deliberately refused to quantize** — but neither paper ran the head-to-head.

## 1. Claims table

Verdict vocabulary: CONFIRMED / PARTIAL / OVERTURNED / NOT-FOUND.

| # | Claim (as given) | Verdict | Locator | Verbatim quote | quote_sha256 |
|---|---|---|---|---|---|
| 1 | First PTQ framework designed specifically for Mamba-2 SSD, maintaining a persistent INT8 path across **ChunkCumsum, ChunkState, StatePassing, ChunkBMM, ChunkScan** | **PARTIAL — the first-claim survives, the five-module coverage is OVERTURNED** | Abstract, `ssdi8_math.txt:137`; §4 opening `:226`; §2 `:188` | "the first post-training quantization framework specifically designed for SSD to maintain a persistent INT8 path" | `2ab4b760dec72ee51d0cc7792177837c1d6e805821371eeae41481c0a9c20dde` |
| 1b | (the overturn) ChunkCumsum + ChunkScan2 are **FP16** | as stated | §4 opening, `ssdi8_math.txt:226` | "The output tensor $$dA_{cs}$$ from ChunkCumsum is negligible in size compared to other tensors, yet its recovery after quantization is challenging due to the element-wise multiplication; hence, it is retained in FP16. In the same vein, ChunkScan2 remains in FP16 for analogous reasons." | `90c604910aad864f72c15c51babc359a8af34796daa15307aebd249b3029a137` |
| 2 | Decouples element-wise mul from matmul; quantized B and C reused across three SSD submodules; quantizes along group axis G with \|G\|≪\|H\| at ~3 % latency | **CONFIRMED** | §4.2 `:301` (reuse), `:303` (G-axis, 3 %) | "SSDi8 performs an early quantization of the channel-varying activations $$B$$ and $$C$$ once along the group axis G at the beginning of each SSD layer." / "quantization along G is considerably more efficient, adding only about $$3\%$$ to the total SSD latency." | `f7686fd90e953bcd630eb5172486f9a5b1e5861a2522d965f2e351517734528c` / `48fd02cb9a8dd1157e0659e021285ffbd298b2c8847f5fc3540f0ce31a8e1c31` |
| 2b | "three SSD submodules" = ChunkState (B), ChunkBMM (B,C), ChunkScan1 (C) | CONFIRMED (which three, resolved) | §4.2 `:301`, `:347`, `:345` | "they are repeatedly invoked across three SSD submodules. Rather than quantizing them separately within each module, SSDi8 quantizes once and reuses the resulting INT8 tensors" | `b6c7da875cc27dec318cc6dd3bae7a768f8d1b0471ba27cfdc1c66df559f5036` |
| 3 | Persists recurrent state in INT8, **bit-shift** decay updates + per-channel mean correction; accuracy ≈ FP16; up to **1.4×** in W4A8/W8A8 | **PARTIAL** — INT8 state and mean correction confirmed; "bit-shift" is a fixed-point multiply by `Q(Decay)/2^k`; "1.4×" hides 1.38/1.47 | §4.2 Eq. 9 `:339`,`:343`; Abstract `:180` | "where $$S$$ is a gating constant chosen as $$2^{k}$$ to enable bit-shift operations for minimal latency (with $$k=7$$ in experiments)." / "enabling up to 1.4 $$\times$$ inference speedup under both W4A8 and W8A8 configurations" | `4cf18b4302cc79e7136e01b995d28b445dc4031698eef4d9526b1c0d0c1f8aaf` / `010fdbe4eaec58462f72e59a181aa788e0848955b95822aa5b0e649b536c4ecf` |
| 4 | Directly applying Transformer-style Hadamard rotation / GPTQ to SSD layers degrades accuracy **because** D decomposes into head and per-head axes with different outlier distributions | **PARTIAL — the observation is real; the causal attribution is not tested; the rotation half is NOT-FOUND as an experiment** | §1 `:175`; Tab. 1 `:148`; control definition `:566`,`:1723`; failure numbers Tab. 6 `:946`, Tab. 8 | "directly applying quantization methods originally designed for Transformers—such as Hadamard rotation or GPTQ—to SSD layers leads to substantial accuracy degradation." / "the HAD (HadMamba2) baseline, where HAD applies the Hadamard rotation to the Mamba-2 projection layers ( Chiang et al. 2025a ) , GPTQ weight quantization and RTN quantization of SSD inputs." | `fd0b2df3f63e159c828b80ba7dbc732435def916199ae0d975ca36d4b1211d35` / `923ba740b1f8829fc9fc8c946ec7553c5ae8f04be33a585078d20825785521dc` |

Supporting numbers for claim 4 (no quote needed, table locators):

| control | 1.3B W8A8/W4A8 | 2.7B W8A8/W4A8 | 8B W8A8/W4A8 |
|---|---|---|---|
| FP16 | 59.5 | 63.8 | 70.7 |
| **HAD** (Hadamard on *projections* + GPTQ W4 + **per-tensor RTN on SSD inputs**) | 57.3 / 57.0 | 58.5 / 57.3 | 65.8 / 65.4 |
| Quamba2 | 58.3 / 57.7 | 62.5 / 62.1 | 69.8 / 69.1 |
| SSDi8 | 59.1 / 58.8 | 63.2 / 62.6 | 70.2 / 69.6 |

(Tab. 2 `:349`–`:548`, Tab. 8 `:1729`–`:1955`. Pattern: the naive recipe loses **2.2 / 5.3 / 4.9** points at W4A8 and its damage concentrates in LAMBADA — 2.7B 51.2 % vs 69.5 %.)

**Number hygiene (supports the PARTIAL on claim 3, and a caveat for any citation).** The speedup headline is not one number: abstract 1.4× (`:180`, plus "single-inference speedups reaching 1.5×"), §4.2 "up to 1.38× overall … 1.6× in the ChunkScan module" (`:349`), §5.2 "1.47× over FP16 and 1.38× over Quamba2" at B=32,L=2048 (`:696`), conclusion 1.47×/1.38× (`:996`). And Fig. 4's caption (`:690`) says "1.47× overall speedup and 1.77× **in the State path**", while the body attributes 1.77× to **ChunkScan** and 2.25× to **StatePassing**. Accuracy text drifts too: `:685` says 2.7B W4A8 is "62.7 % vs. 62.1 %", while Tab. 2 and Tab. 8 both print **62.6** for SSDi8. Only the body text and Tab. 5 are internally consistent; every citation must name the axis (overall vs module) *and* the baseline (FP16 vs Quamba2 vs W4A16).

**Why claim 4 is PARTIAL, precisely.** Tab. 6 (`:946`) isolates it: "HadMamba quantization yields only 51.2 % accuracy, whereas applying SSD quantization substantially boosts performance to 67.2 %." The delta between those two arms is *where the per-tensor scale sits* (RTN on SSD inputs vs per-(P,H)/(G) SSD quant), not *whether a rotation was applied*. And Tab. 10 (`:2101`–`:2166`) is an **axis** ablation, not a rotation ablation: `X,State` at per-T → PPL 11.97 vs 7.42 at per-P+per-H, while `B,C` are insensitive (7.59 vs 7.42). So the paper's own controlled evidence supports "**scale granularity along the H/P axes**", and only *infers* "rotation is bad". A rotation control at fixed granularity does not exist anywhere in the paper.

## 2. A — What stays FP16, where quantization happens, and the decay arithmetic

**Tensors that stay FP16 (exhaustive as stated):**

1. `dA_cs` — the ChunkCumsum output, shape (B,H,c,l). Explicitly FP16 (`:226`): "negligible in size … yet its recovery after quantization is challenging due to the element-wise multiplication".
2. `LUT_state = Δ ⊙ exp(dA_cs_final − dA_cs)`, `LUT_scan1 = Δ ⊙ exp(dA_cs)`, `LUT_scan2` — all (B,H,c,l) / (B,H,c,l,l) element-wise decay factors. Never quantized; they are the *carrier* of the fused dequant scales.
3. `X` inside **ChunkScan2** — the diagonal path is `(LUT_Scan2 ⊙ Q(CB)) × X` with `X` in FP16, "enforcing a floating-point path" (`:347`). Reformulation is *declared infeasible* here "due to a shape mismatch with `X`" — `LUT_Scan2` is (l,l) and `X` is stepped along l, so the same trick as Eq. 7 has no valid axis to move onto.
4. Everything outside SSD except in/out projections: activations per-tensor INT8 with a fused fast-Hadamard (`:1723`); weights W4 via GPTQ.
5. The state axis **`N`** is *not* FP16 but is **excluded from the quantization axes** (`:304`): "While the state dimension N exhibits relatively consistent statistics, it directly participates in subsequent matrix multiplications, where quantization errors cannot be restored. Thus, it is excluded from the quantization axes." [quote_sha256 `8f126d506fcdc99b0e47391563b5eb08a70536ae958f9a0237ff96f146a73b52`] State carries one scale per **(H,P)**, shared across `N` *and* across all chunks `c`.

**Where quantization is placed:** (i) `B`,`C` at SSD-layer entry, along `G` (per-G, optionally per-(G,N) — Tab. 10 shows per-G,N is 0.02 PPL better, called negligible); (ii) `X_scaled = LUT_state ⊙ X` at ChunkState, along **(P,H)**; (iii) ChunkState's INT32 accumulator → INT8 **in registers** (Eq. 8, `:329`); (iv) ChunkBMM's `CB` INT32 → INT8, axis unstated ("similar to ChunkState", `:347`); (v) `Decay` in StatePassing, element-wise fixed-point.

**The decay / state-pass arithmetic (Eq. 8–9, `:329`,`:339`):**

```
State_INT8 = Round( State_INT32 ⊙ (s_x · s_b · q_max) / s_s ),   q_max = 2^(b-1) − 1      (8)
Q(State_{i+1}) ← Q(State_{i+1}) + ( Q(Decay_{i+1}) / S ) ⊙ Q(State_i),   S = 2^k, k = 7   (9)
```

Analytical hazards (mine, not the paper's — the paper states none of them):

- **It is not a shift.** `Q(Decay)/2^7` is a fixed-point multiply; only the `/2^7` is shiftable. The product `(Q(Decay)/S)·Q(State)` needs ≥16-bit intermediates before the store back to INT8, and no accumulator width, clamp or rounding mode is specified.
- **Systematic under-decay at k=7.** `Decay ∈ (0,1]`, so `Q(Decay) = round(Decay·128)` reaches 128 at `Decay = 1`, which does not fit signed INT8 (max 127). Whichever way it is handled (clamp to 127, or uint8), the largest representable decay is ≤ 127/128 = 0.9922, i.e. **the state decays ~0.8 % too fast per chunk** — a *biased* error that compounds over `c` chunks (c = 16–32 at l = 64–128). The paper's long-context stability claim (App. H, PPL flat 8.94–9.36 to 14k) is evidence this is tolerable in practice, but it is not modelled.
- **Static state scale required.** Eq. 9's "all `State_INT8` across c share a common scale" forces `s_s` to be a *calibration-time constant* per (H,P); a runtime amax would break the recurrence. Nothing says how `s_s` is estimated or how saturation is avoided when a chunk-accumulated state exceeds the calibrated range. This is the single most underspecified point in the method.
- **Register round-trip.** INT32 → INT8 "in registers" (`:324`) is a Triton-level statement; it presumes the accumulator fragment layout is co-located with the epilogue, which is true in their kernel and would need re-deriving in any other backend.

## 3. B — The mean-correction term

Closed form (Eq. 10, `:554`–`:557`), for a layer whose FP output is `Y = XW ∈ R^{N×P}` and dequantized output `Y'`:

```
c*_p = (1/N) Σ_{i=1..N} (Y − Y')_{i,p}          E_c = ‖Y − (Y' + c)‖_F²
```

i.e. **the per-output-channel mean of the quantization error** — the minimizer of the least-squares residual. Verbatim (`:554`): "minimizing the error between $$Y$$ and $$Y^{\prime}$$ can be formulated as a least-squares problem, and the optimal correction vector $$c^{\star}$$ is given in closed form as the channel-wise mean of the quantization error:" [quote_sha256 `bef0be0f00ef93e353d024f8cc05a4d9eb6dc6c28bca5a35d4b8f2805547451a`]. Eq. 10 then writes the term explicitly as `c*_p = (1/N) Σ_{i=1..N} (Y − Y')_{i,p}`.

**Offline, at calibration — not runtime.** Algorithm 1 (`:1421`–`:1537`) is a layer-sequential pass over `S` calibration samples: for each target layer it computes the running mean of the *quantized* output `μ_q`, forms `δ = μ_fp[l] − μ_q`, damps it (`c[l] ← η·δ`, `η = 0.15`, `:568`), writes the correction into the layer, and **propagates the corrected activations forward** so later layers see the shifted distribution. At inference `c` is a frozen per-channel bias vector added to the layer output — cost measured at 1–2 % (`:562`), and Tab. 11 (`:2172`) shows `×0.987` speedup when placed at the out-projection.

**Placement:** out-projection layer only (`:562`), "whose dimensionality is half that of the input projection layer and where quantization error is most pronounced". Tab. 11 also records that placing it *after the SSD* gives the largest accuracy gain (67.5 % vs 67.4 %) — they traded 0.1 point for latency. Note the gain is small in absolute terms: 67.2 → 67.4 (Tab. 6). The mean correction is a real but **marginal** effect; the paper's own ablation gives it +0.2 points, not the headline.

## 4. C — Accuracy numbers and latency setup

**Zero-shot average, 6 tasks (LA, HS, PIQA, Arc-E, Arc-C, WG), Tab. 2 / Tab. 8:**

| | FP16 | SSDi8 W8A8 | SSDi8 W4A8 | Quamba2 W8A8 | Quamba2 W4A8 | Quamba2 W4A16 |
|---|---|---|---|---|---|---|
| 1.3B | 59.5 | 59.1 | 58.8 | 58.3 | 57.7 | 58.9 |
| 2.7B | 63.8 | 63.2 | 62.6 | 62.5 | 62.1 | 63.3 |
| 8B | 70.7 | 70.2 | 69.6 | 69.8 | 69.1 | 69.8 |

The W4A16 column matters when reading the headline: the strongest Quamba2 baseline is **not** W4A8 but W4A16 (2.7B 63.3, 8B 69.8), and SSDi8's W4A8 (62.6 / 69.6) sits just below it. The paper's own framing — "comparable to Quamba2 under W4A16 … even with W4A8" (`:1727`) — concedes that the activation-quantization gain does not fully close the gap to a weight-only baseline at 2.7B.

**WikiText-2 PPL, Tab. 3 (`:576`–`:681`):** FP16 10.42 / 9.06 / 7.25; SSDi8 10.63 / 9.22 / 7.49 (W8A8) and 10.92 / 9.43 / 7.62 (W4A8); Quamba2 10.80 / 9.32 / 7.79 and 11.08 / 9.54 / 7.94; HAD 11.31 / 11.42 / 8.57 and 11.63 / 11.85 / 8.79, for 1.3B / 2.7B / 8B.

**Latency setup.** NVIDIA **A5000 24 GB** (sm_86), forward pass only. Verbatim (`:696`): "Latency is measured in milliseconds as the average of 100 runs after warm-up." [quote_sha256 `184ab30cc5f83929125e290e0666e4979f7a0127737e1f590a6987bef9690507`]. Batch ≤ 32, seq ≤ 2048; module breakdown at B=32, L=2048 on 2.7B. 8B in App. G at B=16 (14.745 → 10.646 ms, −27.8 %) and B=32 (FP16 **OOM**, Quamba2 25.797 vs SSDi8 19.000 ms). Edge: **Orin NX 16G**, 2.7B, **B=16**, L=256…2048 (W8A8 L=2048: 249.29 → 217.69 ms). Long context App. H: 2.7B, B=8, L=2k…14k — "For each context length, we measure SSD-module latency, end-to-end throughput (tokens/s), and perplexity (PPL) to assess both computational efficiency and modeling behavior in the long-sequence regime." [quote_sha256 `df68ecd36e95d8fa26e8681df6c62a11174edb6c84e0f008ae9e65e9882d506b`]. Prefill throughput is the only tokens/s in the paper.

**Decode / generation measurement: ABSENT.** Not "not found in the abstract" — absent from the whole paper, all appendices, and all 17 tables. Every latency figure is a teacher-forced forward pass over a full sequence at batch ≥ 8 (the B=16/32/128/256 sweeps in App. K are SSD-module-only, still L=2048 forward). No batch-1 number is stated in text or in any table (Fig. 4a is a plot over "B ≤ 32" whose individual points are an image I did not read; the only quoted point is B=32). There is no per-token latency, no time-to-first-token, no tokens/s at decode, no speculation/acceptance. The one phrase that could be read as single-sequence — "single-inference speedups reaching 1.5×" (`:180`) — is undefined and unattached to a table, so it cannot be used as decode evidence. For a memory-bound host this is the single largest evidence gap: the entire result set is prefill-shaped, and the paper's own explanation of *why* short sequences lose ("`L=256` may show higher FP16 efficiency due to lower computational intensity", `:696`) is an admission that the win is arithmetic-intensity-dependent — precisely the regime decode is not in.

## 5. D — The Hadamard claim, and whether LinQuant contradicts it

**The exact experiment that exists.** Two arms, both defined at `:566` and `:1723`:
- **HAD** = Hadamard rotation applied to the *Mamba-2 projection layers* + GPTQ W4 weights + **RTN per-tensor quantization of the SSD inputs** + fused fast-Hadamard for all non-SSD activations.
- **SSDi8** = Hadamard/GPTQ on projections (same) + per-G `B,C`, per-(P,H) `X_scaled`, per-(H,P) INT8 state, per-? `CB`.

So in the only head-to-head, **both arms rotate the projections and neither rotates anything inside SSD**. The measured 5.3-point gap at 2.7B W4A8 is attributable to SSD *input scale granularity* (per-tensor → per-axis), which Tab. 10 confirms independently.

**Does it distinguish "rotation with naive per-tensor scales" from "rotation fused into SSD operand preparation"?** **No — it cannot.** The paper never runs an SSD-internal rotation at all, so it has no arm in which "rotation fused into SSD operand preparation" is even represented. Claim 4's first half is therefore a statement about *a recipe* ("Transformer-style", i.e. rotate the residual stream and per-tensor-scale what falls out), and its second half (the causal story) is an architectural argument supported by distribution plots (Fig. 2, Fig. 7 — images, unread) and by the axis ablation.

**Consequence for LinQuant's `R_QK` (intake-2641).** Not a contradiction — an **extension across a stated boundary**:

- SSDi8 quantizes `State` per **(H,P)** with `N` *inside* the shared scale, and explicitly refuses per-`N` quant because "quantization errors cannot be restored" after the `State × C` matmul (`:304`). The N-axis distribution is therefore never equalized, only tolerated.
- LinQuant's `R_QK` applies a random-signed Hadamard **along the key axis — which is `N`** — and fuses it into operand preparation, with per-(H, D_v) state scales (the same (H,P) granularity SSDi8 uses) and an FP32 carry. It attacks exactly the axis SSDi8 left alone, at exactly the granularity SSDi8 chose.
- The two papers' *shared* finding is compatible: both say the **H/P axis decomposition** is what matters (SSDi8 Tab. 10: per-T on X/State is catastrophic, 11.97 vs 7.42 PPL; LinQuant likewise keeps per-channel value scales). SSDi8's "don't rotate" claim is the weaker, untested half.

Residual risk, stated plainly: SSDi8's mechanism story — per-(H,P) block scales are *already* fine-grained, so a rotation only redistributes an error that is already controlled, while its cost (an extra `l×l`-shaped operand pass) is not free — is a legitimate *prediction* that `R_QK` should help less on top of SSDi8-style per-axis scales than it does on top of per-tensor scales. LinQuant reports `R_QK` gains *on top of its SSDi8 re-implementation* (8B 7.620 → 7.435), which is evidence against that prediction — but, per intake-2641's own caveat, with no naive-rotation control and inside calibration noise at 2.7B (9.441 → 9.379). **The dispute is unresolved by both papers; only a head-to-head at fixed granularity resolves it (SD-1).**

## 6. E — Mechanism of the 1.4×, and what survives on EPYC / MI210

**Decomposition from the paper's own ablation (Tab. 5, `:819`–`:917`, 2.7B, W4A8, ms → PPL):**

| arm | latency (ms) | cumulative × vs 8.63 |
|---|---|---|
| baseline (SSD in FP16) | 8.63 | 1.000 |
| + ChunkState `Q(X)` | 8.58 | 1.006 |
| + `Q(X)` + sparse reformulation | 8.05 | 1.072 |
| + … + quant of B,C | 7.60 | 1.135 |
| quant B,C **without** reformulation | 8.35 | 1.034 |
| + persistent INT8 (B,C quantized) | 8.00 | 1.079 |
| + persistent INT8 **+ ChunkBMM quant** | **6.53** | **1.322** |

(PPL rises monotonically 9.34 → 9.43 across these arms, i.e. ≤0.1 degradation — the efficiency and accuracy claims come from the same table.)

Text version (`:917`): quantizing `B`, `C`, `CB` **without** the reformulation is limited to 1.07×; the reformulation enables INT8 execution in ChunkScan1 for a further 1.08×; and quantizing ChunkBMM is what takes the total to 1.32×.

**So the ranking is: ChunkBMM/CB quantization ≫ reformulation+INT8 ChunkScan1 > B/C placement.** The `CB` tensor is (B,G,c,l,l) — quadratic in chunk size, "larger than `X`" — so **the dominant term is DRAM traffic on the largest intermediate, not integer-tensor-core FLOPs.** Corroborating: "StatePassing yields $$2.25\times$$ and $$2.17\times$$ improvements, respectively." [quote_sha256 `f6ef5857758f9c72063b4639f57c5de34920c9382e0aa6a7bb4a72e9d1c0a29b`, `:696`] — that is pure state-tensor traffic (INT32 → INT8 halves it), while ChunkScan's 1.77× is the tensor-core arm and is *smaller*. The "INT8 Tensor Core" phrasing at `:345` is true but is not what buys most of the speedup.

**(i) EPYC 9655 / AVX-512 VNNI.** Survives: the traffic halving on `CB` and `State` (identical 2× on bytes moved; VNNI's `VPDPBUSD` is in-tree at `ggml/src/ggml-cpu/arch/x86/repack.cpp:124-125`), and the *elimination of the INT32→FP16 materialisation* in the state pass. Does **not** survive: any "tensor core" framing — there is no int8 matmul unit; the gain becomes 4× peak MACs (`vpdpbusd` = 64 int8 MACs/512-bit instr vs 16 FP32 FMA) minus packing and per-(H,P) scale epilogue cost, which the paper never pays because it fuses scales into the LUT. Realistic expectation on CPU: the memory-bound part transfers, the compute part does not, and the whole thing needs `l×l` `CB` blocks that a CPU would rather not materialise at all.

**(ii) MI210 / gfx90a.** int8 MFMA **already exists in-tree and on this architecture**: `ggml/src/ggml-cuda/mma.cuh:1314` (`__builtin_amdgcn_mfma_i32_16x16x16i8`, CDNA2/CDNA1 branch) and `:1347` (`mfma_i32_32x32x8i8`), reached today through the MMQ vec-dot path for k-quants (`ggml/src/ggml-cuda/mmq-vec-dot.cuh:203-205`). Survives: the 2× operand-bandwidth reduction (the dominant term, per the ablation) and the fused-scale epilogue. The arithmetic step is *at most* 2×: both CDNA2 int8 intrinsics issue the same instructions as their FP16 counterparts (16×16×16), and AMD quotes MI210 at the same headline 181 for dense FP16 (TFLOPS) and INT8 (TOPS) — the same number, but int8 counts one op per MAC, so the gain is in MACs, not in a bigger unit. Unlike a consumer Ampere part there is no extra 2× on top of that. The residual blocker is structural, not arithmetic: ggml's int8 kernels are **weight-stationary** (quantized weights from memory, activations quantized in registers) and carry 1-D per-block scales; SSD needs **activation×activation** int8 GEMM with a 2-D (H,P) scale — no such primitive exists (see F).

Nothing in either backend breaks the method; what breaks is the claim's *headline reason*. The paper's speedup is a memory-traffic story that happens to use int8 tensor cores.

## 7. F — What a ggml implementation would need, and the smallest deciding experiment

**Current state of the tree (read-only, `/mnt/raid0/llm/llama.cpp` @ `ffc1bac82`, v10):**

- No chunked SSD op exists. `GGML_OP_SSM_SCAN` (`ggml/src/ggml.c:5680`; CPU f32 recurrence `ggml/src/ggml-cpu/ops.cpp:9976`) is **per-token sequential Mamba-1**; there is no `GGML_OP_SSD_CHUNK`, no chunked 5-module pipeline, no `ChunkCumsum/ChunkState/StatePassing/ChunkBMM/ChunkScan` decomposition anywhere in `ggml.h` (op list `ggml/include/ggml.h:540-575`: `SSM_CONV`, `SSM_SCAN`, `GATED_LINEAR_ATTN`, `GATED_DELTA_NET`, … nothing chunked-SSD).
- `GGML_TYPE_I8` exists (`ggml/include/ggml.h:414`) but nothing writes it as a *quantized accumulator with a persistent recurrence*.
- int8 dot primitives exist but are the wrong shape: CPU `dpbusd` (`arch/x86/repack.cpp:124`) and CUDA/MMQ int8 MMA are weight-stationary with 1-D block scales.

**Smallest missing set — exactly two primitives:**

1. **A fused chunked-SSD op with an INT8 persistent state** (one kernel computing all five submodules, state-owned across chunks, per-(H,P) state scale as an attribute). Without fusion the premise dies: `B`, `C`, `CB`, `State` each become a materialised ggml tensor between ops, which is exactly the traffic SSDi8 removes. The precedent for the shape of such an op is `GGML_OP_GATED_LINEAR_ATTN` (fused, multi-tensor, dispatched on CPU at `ggml/src/ggml-cpu/ggml-cpu.c:2452,2984` and on CUDA), not `SSM_SCAN`. The tree already flags the same gap on the GPU recurrence side: `ggml/src/ggml-cuda/gated_delta_net.cu:191` — `//TODO: Add chunked kernel for even faster pre-fill`.
2. **A per-(H,P)-scaled int8×int8 matmul** (dynamic×dynamic, 2-D group scales, INT32 accumulator with an optional INT32→INT8 register epilogue). This is the only genuinely new arithmetic; on gfx90a it can be built on `mfma_i32_16x16x16i8`, on CPU on `vpdpbusd` with a row-scale epilogue.

Not needed: mean correction (a per-channel bias add — `GGML_OP_ADD` today, calibration offline), the reformulation itself (a graph rewrite: `LUT ⊙ X` before the state matmul instead of `LUT ⊙ B`, expressible inside primitive 1), and W4A8 projections (already served by Q4_K/Q4_0 + q8 activations).

**Smallest deciding experiment (one quarter, no kernel):** capture `X`, `B`, `C`, `LUT_state`, `dA_cs` from a real Mamba-2 1.3B forward (HF reference, hooks, 2–4 layers, a few hundred tokens), then in float64/numpy simulate: (a) per-tensor vs per-(P,H) vs per-(H,P) scales — reproduces Tab. 10 and proves the axis claim is a property of *the data* rather than of their Triton kernel; (b) **the rotation control nobody ran**: Hadamard along `N` on `B`/`C`/`State` at *fixed* per-(H,P) granularity, against no rotation — this is the direct `R_QK` vs claim-4 test, and it decides SD-1/SD-4 in one run; (c) the `k=7` decay quantization of Eq. 9 with and without clamping, over 16–32 chunks, to size the under-decay bias. Cost: one activation capture + numpy; no build, no GPU kernel, no claim about speed. Only if (a)/(b) show recoverable headroom does primitive 1/2 become worth a build, and that build must carry a **decode (B=1) measurement** the paper does not have.

## 8. Derived actionables ledger

| ID | Action | Owning lane handoff | Disposition |
|---|---|---|---|
| **SD-1** | Run the deciding probe in §7: capture Mamba-2 1.3B SSD activations, simulate per-axis scales + an `N`-axis Hadamard control at fixed granularity + the `k=7` decay quant. Decides both SSDi8 claim 4 and the SSDi8↔LinQuant `R_QK` dispute in one CPU-only run. | `handoffs/active/model-architecture-readiness.md` (log-linear-gated-deltanet-readiness track — recurrence-operand quantization) | **PROPOSE** — highest value/cost ratio in this dive; no GPU, no kernel, no production risk. |
| **SD-2** | Record the two missing ggml primitives (§7) plus the in-tree evidence (`ggml.c:5680`, `ops.cpp:9976`, `mma.cuh:1314/1347`, `repack.cpp:124`, `ggml.h:414`) as a scoping note for any chunked-recurrence INT8 build; gated on SD-1 showing headroom. | `handoffs/active/quantization-and-low-bit.md` | **PROPOSE (scoping note only)** — build is *not* authorized; the note must state that gfx90a gains are bandwidth-only (no int8 arithmetic-rate step over FP16 MFMA). |
| **SD-3** | Add the INT8-state rounding/saturation hazards to the quantization hazard register: `k=7` ⇒ max representable decay ≤127/128 (systematic ≤0.78 %/chunk under-decay), unstated clamp and rounding mode, and the requirement that `s_s` be a static per-(H,P) calibration constant. Any port must specify all three. | `handoffs/active/quantization-and-low-bit.md` | **PROPOSE** — a spec requirement; no compute. |
| **SD-4** | Record LinQuant `R_QK` as an **extension across SSDi8's stated boundary** (SSDi8 excludes axis `N` from quantization; `R_QK` rotates exactly `N`), with the two caveats (no naive-rotation control in either paper; LinQuant's 2.7B delta inside noise). Update intake-2641's `contradicting_evidence` from "tension, unreconciled" to "boundary-extension, unresolved, SD-1 decides". | `handoffs/active/model-architecture-readiness.md` | **ACCEPT as a record correction**; supersedes the Stage-1 framing. |
| **SD-5** | Mean correction (Eq. 10 + Alg. 1): closed form `c*_p = (1/N)Σ_i (Y−Y')_{i,p}`, offline, layer-sequential, `η=0.15`, applied only at out-projection, worth **+0.2 points** for 1–2 % latency. Adopt as a calibration-side add-on if a quant lane needs the last 0.2 point; no primitive required. | `handoffs/active/quantization-and-low-bit.md` | **DECLINE for now** — real but marginal; no owning task needs it. Re-open only with a named lane that is 0.2 points short of a gate. |
| **SD-6** | Adopt W4A4-exclusion as-is: SSDi8 excludes W4A4 "due to hardware-induced slowdowns as discussed in Lin et al." (QServe). | `handoffs/active/quantization-and-low-bit.md` | **DECLINE (record-only)** — we run no W4A4 lane; adds nothing to a W4A8/W4A16 boundary already settled in-lane. |

## 9. Dive-surfaced sources (not in `research/intake_index.yaml`)

Checked against the lane index: `grep -c` = 0 for each id/title below.

| Source | Why it surfaced | Suggested disposition |
|---|---|---|
| **MambaQuant** — Xu et al., ICLR 2025, `arXiv:2501.13484v3` (id verified via arXiv API 2026-11-06) | The closest prior art on **rotation for SSMs** ("Variance Aligned Rotation Methods"). SSDi8 cites it as a Mamba-1 PTQ baseline; it is *also* the third position in the rotation dispute between SSDi8 and LinQuant. The index mentions the name once in a note and has no entry. | **Ingest** — it is the missing third data point for SD-1/SD-4. |
| **QServe** — Lin et al., MLSys 2024, `arXiv:2405.04532` (id + title verified) | SSDi8's sole authority for excluding W4A4 ("hardware-induced slowdowns"). If our lanes ever weigh W4A4, this is the citation; currently absent from the index. | Record in SD-6's decline row; ingest only if a W4A4 question is opened. |
| **SSDi8 code** — `github.com/cau-hai-lab/SSDi8` | The Triton kernels that *are* the mechanism. LinQuant pins the same tree as a submodule (`c10ccde6`, uninitialised). Needed only if SD-2 reaches a build. | **Artifact**, not a source. Note under SD-2. |
| **Slender-Mamba** — Yu et al., COLING 2025 | 1.58-bit full Mamba ("head to toe"). Out of scope (no sub-INT8 lane). | **Decline** — no entry; name recorded here only. |

## 10. Artifact audit

| Artifact | Path | sha256 | Note |
|---|---|---|---|
| Paper HTML v1 | `/mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/ssdi8.html` | `bf8d8dfbdd4f570233d8ec28270d2e06ac0a981d3b917e1ce55d4dcd37797c64` | 469,355 B; fetched 2026-11-06; primary source |
| Tag-stripped text (formulas lost) | `…/raw/ssdi8.txt` | `3f359866f34f1318e7eb775f0d7d272e7c9ef620071f6300efce25c8c4595d48` | superseded |
| Tag-stripped text, `<math alttext>` inlined | `…/raw/ssdi8_math.txt` | `6bfc62b60953da198a92448ef7728b33ab2009a032cc4ca220aeb94a2379c00d` | **all line locators refer to this file** |
| Quote verifier | `…/raw/quotes.py` | `bae3f8d51b6650e91930cc3a2d39729fb70537452e509612601a0e52852a0f01` | asserts every quote is a verbatim substring before hashing; all 22 `present: true` |
| Report-side verifier | `…/raw/verify_md.py` | `6b947723354e63d3b3f116c95c3c484a330eba6673882c300cb354ff9a1f9818` | re-checks that each quote *as displayed in this report* is verbatim in the extraction **and** that its hash appears in the report — catches a quote that drifted during formatting |
| Artifact sha list | `…/drafts/.artifact-sha.txt` | — | |

Reproduction: `cd …/raw && sha256sum ssdi8.html && python3 quotes.py && python3 verify_md.py`. `present: false` from `quotes.py`, or `FAIL` from `verify_md.py`, means the quote is not verbatim and must not be cited.

Environment note: the lane worktree `/mnt/raid0/llm/worktrees/intake-quant-compiler-20261106` was read only (`research/intake_index.yaml:379301-379346`, `handoffs/active/quantization-and-low-bit.md`, `handoffs/active/model-architecture-readiness.md`); nothing was written into it. `/mnt/raid0/llm/llama.cpp` was read read-only at `ffc1bac82`.
