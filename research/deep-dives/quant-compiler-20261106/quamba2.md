---
title: "Stage-2 deep dive — Quamba2 (intake-2646, arXiv:2503.22879v4, ICML 2025)"
entry: intake-2646
read_depth: full-primary
read_scope: "abstract through Appendix G (all sections, all tables T1-T13, all figures F1-F14). 2544 extracted lines / 74,610 chars / 74,827 bytes. Nothing skipped; appendices A-G read because they carry the table numbering, the roofline argument, and the per-task accuracy that the body omits."
source_revision: "arXiv:2503.22879v4 (HTML), stamped 06 Nov 2025, ICML 2025"
source_url: https://arxiv.org/html/2503.22879v4
source_sha256: "a828ec49d1438106d1f94863e8a8728343b0dfe9b6c9e9f53d50eb4ea543c30f"
source_bytes: 394025
retrieved: "2026-11-06"
lane_worktree: /mnt/raid0/llm/worktrees/intake-quant-compiler-20261106
lane_head: dd0fb48e0
raw_artifact: /mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/quamba2.html
extracted_text: /mnt/raid0/llm/tmp/dive-quant-compiler-20261106/raw/quamba2.txt
extracted_text_sha256: "19f6db9d22a31bbbdfe576cb523c97866bd29b3d0bae8bcc4ad2216fcde8faf9"
analyst: research-intake/stage2
lineage: "intake-2641 -> 2642 (LinQuant) / 2645 (SSDi8) / 2646 (Quamba2)"
verdict: "claims confirmed; decode mechanism resolved to weight streaming; no CPU evidence; one derived actionable (head-to-toe) and two declines"
---

# Quamba2 — Stage-2 deep dive

**Read depth: full primary source.** Everything below is adjudicated against the v4 HTML itself, not
the Stage-1 abstract read. Line numbers refer to the extracted text artefact
(`raw/quamba2.txt`), which is a deterministic LaTeXML strip of `raw/quamba2.html`
(sha256 `a828ec49d1438106d1f94863e8a8728343b0dfe9b6c9e9f53d50eb4ea543c30f`). Quotes are verbatim from that extraction; see §9 for the two
normalisations this implies and why the hashes are only reproducible against the `.txt`.

**Headline.** All three Stage-1 claims are CONFIRMED. The one number that mattered most — the 3x
generation speedup — resolves cleanly to a **weight-streaming win on a memory-bound GPU at batch 1**,
and it is 98% attributable to *weight bytes*, not to anything the paper invented. Quamba2 contributes
no CPU evidence of any kind. The one element worth taking is not the sort-and-cluster machinery but
**head-to-toe lm-head/embedding quantization**, which is a config-level change on our stack.

---

## 1. Claims adjudication

| # | Claim (Stage-1 wording, condensed) | Verdict | Locator (raw/quamba2.txt) | Verbatim quote | quote_sha256 |
|---|---|---|---|---|---|
| Supports W8A8 / W4A8 / W4A16 head-to-toe for Mamba-1 and Mamba-2, motivated by cloud-throughput vs edge-generation bit-width needs | **CONFIRMED** | Abstract L179; Table 2 caption L246; motivation L178 | Q1b (`836dfdc612e4`) · Q1c (`d768d8455c32`) · Q1a (`7aa2b641e8ae`) |
| Quantizes recurrence inputs offline by sort-and-cluster so similar-range heads share a scale; quantizes input-dependent B/C per state group; exploits channel-order preservation and activation persistence | **CONFIRMED (two precision notes)** | Abstract L179; S4.1 L398, L406, L417; S4.2 L428 | Q2a (`68e7466fd9cb`) · Q2b (`f9a88f8799a0`) · Q2c (`2ffd7a2f7104`) · Q2d (`0222e57ee142`) |
| 1.3x prefill and 3x generation speedup, 4x memory reduction, 1.6% average accuracy drop; Mamba2-8B on Orin Nano 8G at 13 tok/s | **CONFIRMED (scope must travel; 13 TPS is a round-up)** | Abstract L179; S5.2 L655-L658; Table 5 caption L575 | Q3a (`5360b590bf3b`) · Q3b (`1d4788022e16`) · Q3c (`41ca13fcdfa9`) · Q3d (`7937604ec960`) |

### Verbatim quotes (hash-bound)

Every hash below is sha256 over the quoted string exactly as printed.

- **Q1a** — `7aa2b641e8ae021f329aae150eaaade101308fb61966d1ff2d174feb5d58141d`
  > However, distinct bit-width configurations are essential for different scenarios, like W4A8 for boosting large-batch decoding speed, and W4A16 for enhancing generation speed in short prompt applications for a single user.
- **Q1b** — `836dfdc612e43b5435449dcba528d78c1deac3674b1095db498c4b816c1e490f`
  > To this end, we present Quamba2, compatible with W8A8 , W4A8 , and W4A16 for both Mamba1 and Mamba2 backbones, addressing the growing demand for SSM deployment on various platforms.
- **Q1c** — `d768d8455c32bcb24a7e122594342e4822e0a407427170bbd54cd64bf1a0a05d`
  > Table 2 : (Supported bit-widths.) Quamba2 supports head-to-toe (H2T) 4/8-bit from the embedding layer, SSM blocks, to the final output layer ( i.e., lm head).
- **Q2a** — `68e7466fd9cb11d64d0d8ae19570b6273b0679115cb2344ca0bf087233f1cd67`
  > Based on the channel order preserving and activation persistence of SSMs, we propose an offline approach to quantize inputs of a linear recurrence in 8-bit by sorting and clustering for input x , combined with a per-state-group quantization for input-dependent parameters B and C . To ensure compute-invariance in the SSM output, we rearrange weights offline according to the clustering sequence.
- **Q2b** — `f9a88f8799a09438c5cd2025f153a331854b353ff5e13a00e11c2d4334d67555`
  > Specifically, we first obtain the channel maximum from a calibration dataset.
- **Q2c** — `2ffd7a2f710471c8d18a2a1c48ed8453bb2a9bf29bc510d1dcbb2dd3b5ee6a59`
  > We find that m=4 and n=4 provide sufficiently good results throughout all experiments.
- **Q2d** — `0222e57ee142a179f97988c8166c73226652f33b865ef43ed9731a5031daf0ef`
  > Thus, we apply per-state-group quantization to B and C , where each group utilizes a single scaling factor.
- **Q3a** — `5360b590bf3b1695ab3668a542c42a4996266bb5028e424d2e1f02d516116bfb`
  > The experiments show that Quamba2-8B outperforms two state-of-the-art SSM quantization methods and delivers 1.3 \times and 3 \times speed-ups in the pre-filling and generation stages, respectively, while offering 4 \times memory reduction with only a 1.6\% average accuracy drop.
- **Q3b** — `1d4788022e1675c3cb4071b2daa02414b82e97acd126ea2640259f2ddb5451c9`
  > In the W4A8 configuration, Quamba2 achieves 3.89\times less memory use, 1.39\times prefilling, and 3.05\times faster generation speed for Mamba2-8B on A5000.
- **Q3c** — `41ca13fcdfa9903a81e66e850d514a4acb55d327488cb9ebab400ace9290ccd6`
  > Our approach allows the deployment of Mamba2-8B on Nano 8G with a speed of generating 13 tokens per second, while FP16 and W8A8 fail, as illustrated in Figure 1 and Table 5 .
- **Q3d** — `7937604ec960acfaaee22ee124f8b2fc4cc0af888d755db9bbeab15edf28f5e4`
  > Table 5 : (Mamba2-8B latency.) TPOT and TTFT on Nvidia A5000 GPU and Orin Nano 8G are measured in milliseconds ( ms ) with one batch. TTFT is profiled with 1024 tokens. (OOM: out-of-memory)

### Claim 1 — CONFIRMED

Head-to-toe is not a slogan: Table 2 has a column `H2T` with an explicit grid, and the paper states
the covered regions as embedding, SSM blocks and lm head. W4A16 is offered for **both** backbones
(Table 1 row `W4A16 / Mamba2` is checked), and the bit-width motivation is stated in the cloud-vs-edge
terms the Stage-1 entry used. Nothing to overturn.

One scope note the Stage-1 entry does not carry: head-to-toe is *implemented as CUDA kernels*
("we implement the CUDA kernels and support the 4-bit/8-bit embedding layer and 4-bit/8-bit output
head", L549). It is a kernel deliverable, not a format that another runtime inherits.

### Claim 2 — CONFIRMED, with two precision notes

The mechanism is exactly as described, and the "offline" wording is load-bearing and correct:
calibration supplies the per-channel maximum (Q2b), the sort/cluster indices are computed once, and
the weights are permuted to match so that no runtime sort or gather exists (Q2a). Scales are static
("The static scaling factor s is pre-calibrated and fixed during inference", L334).

Note (i) — **the paper contradicts itself on the group counts.** Figure 4's caption illustrates
`m=8` (`m=8 in (d)`), while §4.1 states m=4 and n=4 for all experiments (Q2c). Treat `m=4, n=4` as
the method and `m=8` as an illustration; do not cite m=8 as the operating point.

Note (ii) — **"per state group" is per (group, dstate-block), not per channel.** §4.1 fixes B/C at
8 groups of 128 channels and assigns one scale per group (Q2d). That is 8 scalars for B and 8 for C —
a very cheap side-information cost, and a large part of why it works (only a few groups are active,
so the inactive groups get a fine scale instead of being crushed by the active groups' maximum).

On the Stage-1 entry's *contradicting_evidence* (SSDi8's claim that Quamba2 "quantizes only SSD
inputs and does not touch internal SSD computation"): the primary source **partially supports**
SSDi8. Quamba2 does load 8-bit `x, A, B, C, z` into the SSD kernel and does modify the selective-scan
and SSD kernels ("the selective scan and SSD kernels ... are modified to accommodate inputs with
quantized weights, activations, and their scaling factors", L2301). But its own Table 3 shows the
standalone SSD kernel gaining only **1.08x-1.19x** over FP16 at batch 8, which is what you would see
from a narrower input format rather than from a persistent integer inner loop. SSDi8's wording
overstates ("only inputs"), its substance holds. Record as **partial corroboration**, not refutation.

### Claim 3 — CONFIRMED; every number reproduces, but the scope is narrower than the sentence

Recomputed from Table 5 (A5000, batch 1, TTFT at 1024 input tokens, Mamba2-8B):

| | FP16 | W8A8 | W4A8 | W4A16 |
|---|---|---|---|---|
| TPOT (ms) | 22.73 | 12.61 | **7.43** | 7.58 |
| TTFT (ms) | 197.80 | **122.33** | 140.78 | 209.19 |
| Model size (GB) | 15.7 | 7.9 | **4.0** | 4.0 |
| Orin Nano 8G TPOT (ms) | OOM | OOM | 79.91 | 78.77 |
| Orin Nano 8G TTFT (ms) | OOM | OOM | 2088.03 | 2316.23 |

- 3x generation: 22.73 / 7.43 = **3.06x** (paper: 3.05x). ✓
- 1.3x prefill: 197.80 / 140.78 = **1.41x** (paper: 1.39x — it *understates* its own number). ✓
- 4x memory: 15.7 / 4.0 = **3.93x** (paper: 3.89x). ✓
- 1.6% average drop: Table 11 8B, 70.7 -> 69.1 = **1.6 points**. ✓
- 13 tokens/s on Orin Nano 8G: Table 5 gives 1000/79.91 = **12.5 TPS** (W4A8) and 12.7 (W4A16).
  **[PARTIAL]** — 13 is a round-up of 12.5-12.7, not a measured 13.

Two inconsistencies inside the paper that a citing document must not inherit:

1. **"1.3x prefill" is relative to FP16 only, and W4A8 prefill is *worse* than W8A8.** Q3b says
   1.39x prefilling in the same sentence as 3.05x generation, which invites the reading that the two
   compose. They do not: W4A8 TTFT is 15% *slower* than W8A8's (140.78 vs 122.33 ms).
2. **The paper's own explanatory sentence is contradicted by its own table.** QA4 claims W4A8 *and*
   W4A16 "slow down TTFT compared to W8A8 and FP16". W4A16 does (209.19 > 197.80). W4A8 does not
   (140.78 < 197.80). The sentence is true only for W4A16-vs-FP16 and for both-vs-W8A8.

The 1.6% is also *not* a general-capability number — see §5.

---

## 2. A — What exactly is the 3x generation speedup?

**Measured on: NVIDIA RTX A5000 24 GB, batch size 1, Mamba2-8B, TPOT (steady-state per-output-token
latency), against the FP16 model on the same CUDA stack (CUTLASS + vLLM, CUTLASS-derived 4-bit
matmul kernels).** Not a GPU-hours or throughput figure; not a batch>1 figure; not MI210, not CPU,
not llama.cpp. TTFT is separately profiled at 1024 input tokens, so TPOT is prompt-length-independent
by construction.

**It is weight-streaming-bound, with a measurable ~22% efficiency loss to the dequant/load path, and
essentially zero contribution from the paper's own kernel work.** Four independent lines of evidence
inside the source, plus one arithmetic check:

1. The authors say so (QA1), and place it in a roofline argument rather than a kernel argument.
2. **W4A16 — weight-only, no activation quantization, no integer matmul at all (QA3) — is within 2%
   of W4A8** (7.58 vs 7.43 ms). If any part of the 3x were activation-quantization compute, W4A16
   could not match it. The paper's entire activation-side contribution (sort-and-cluster on x,
   per-state-group scales on B/C, 8-bit SSD inputs) is therefore worth **0.15 ms/token = 2.0%** of
   decode.
3. The SSD/INT8 kernel, measured alone, is 1.08x-1.19x (Table 3, batch 8) — an order of magnitude
   below 3x, and in a different batch regime.
4. The crossover at larger batch is explicitly attributed to dequant cost (QA2), i.e. the 4-bit path
   has a compute tax that is hidden at b=1 because memory is the constraint.

**Derived arithmetic (mine, not the paper's).** A5000 peak HBM bandwidth is 768 GB/s. The FP16 arm
moves 15.7 GB/token at 22.73 ms = **691 GB/s = 90% of peak** — the baseline is already at the memory
roofline. The W4A8 arm moves 4.0 GB at 7.43 ms = **538 GB/s = 70% of peak**. So bit-width reduction
converts bytes to time at **78% efficiency** (3.93x fewer bytes -> 3.06x less time). That 78% is the
transferable constant in this paper. It prices what any 4-bit weight-streaming proposal should
expect to recover, and it is consistent with the residual being per-token non-weight traffic
(activations, cached state read+write, which do not shrink with weight bits) plus dequant issue cost.

**Answer in one line:** weight-streaming-bound at batch 1; ~98% of the win is "4-bit weights are
3.9x fewer bytes"; the dequant overhead is present but latent; the paper's kernel work is worth ~2%.

---

## 3. B — CPU relevance

**ABSENT.** There is no CPU claim, measurement, or even a passing mention anywhere in the paper
(abstract through Appendix G). Full-text scan of the 74,610-char extraction for `cpu`, `x86`, `arm`,
`AVX`, `ggml`, `llama.cpp` returns **zero** substantive hits — the single match is the substring
inside "warm-up" in the profiling protocol. Every latency, energy and accuracy number is produced on
one of exactly two devices: an NVIDIA RTX A5000 (CUDA/CUTLASS/vLLM) or an NVIDIA Jetson Orin Nano 8G.

**The Orin Nano is not a CPU datapoint,** and it is important not to read it as one. Orin Nano 8G is
an Ampere GPU (1024 CUDA cores) sharing 8 GB LPDDR5 with an ARM CPU; Quamba2's kernels there are the
same CUDA kernels, and the 13 TPS is GPU decode. Its TTFT of 2088 ms for a 1024-token prompt
(0.49 tok/s prefill) is the more interesting number for edge realism and the paper does not discuss it.

Consequence: this entry **cannot** be cited for any CPU-side effect, and its 3x cannot be cited as
evidence that integer activation quantization helps on EPYC. What it *can* be cited for is the
GPU-side byte-to-time conversion constant in §2.

---

## 4. C — Sort-and-cluster: layout change, and its ggml expressibility

### What it does to the layout

The permutation is a two-level reindexing, computed once at calibration and folded into the weights:

1. Calibrate per-channel maximum of the SSM input `x` over 512 Pile sentences, then sort heads by that
   maximum and cluster them into `m` groups (§4.1).
2. Within each head group, sort and cluster channels into `n` groups (§4.1). One scale per
   `(head group, channel group)` cell -> `m x n` static scales for `x`.
3. Rewrite the *weights* so the runtime never sorts: input-projection output columns, causal-conv
   channels, normalisation weights, and output-projection input rows are all permuted with the same
   indices (QC1, QC4). Per-group weight scales are reordered alongside the weights, for coalesced
   Tensor-Core loading (QC2).
4. Fuse the Hadamard matrices offline into those same two projections (QC3), so the rotation costs
   nothing at inference and the block output is bit-identical in exact arithmetic.
5. The SSM state is *not* re-permuted at runtime because it inherits the same group structure: "Since
   the cached SSM states follow the head reordering and channel grouping indices from the SSM input
   x ... we apply the same m head and n channel groups to quantize each SSM state" (App. E).

So the tensor layout becomes **a permuted innermost axis with a block-structured scale vector
indexed by (head-group, channel-group)**. There is no gather, no extra metadata beyond the reordered
scale array, and no runtime cost.

### Can ggml express a permuted-channel layout with per-group scales?

Four separable answers, because they land differently:

- **The permutation alone: yes, and it is free.** A permutation of the innermost axis is not a stride
  trick in ggml — it is a different contiguous tensor, i.e. rewritten bytes at convert time. No new
  ggml type, no kernel change, no runtime gather. The cost is consistency, not representation: every
  consumer of that axis must be permuted identically (the producing projection's rows, the consuming
  projection's columns, the norm weights, and — for an SSM — the recurrent state). In llama.cpp this
  is a GGUF-conversion transform inside the architecture's tensor builder, and it must be
  reproducible from stored metadata or a documented calibration recipe.
- **Per-group *activation* scales at the paper's granularity: no.** ggml's CPU activation quantizers
  are fixed-window: `q8_0`/`q8_1` carry one scale per 32 elements; the K-quant dot path quantizes to
  `q8_K` with **one scale per 256-element super-block**. The paper's `n=4` over a Mamba2 head is 16
  channels at `headdim=64` and exactly 32 at `headdim=128`; the second case is *no finer than the
  block ggml already has*, and the first needs a new type. Either way there is nothing to import —
  and note the conclusion does not depend on the head width, which is why I did not chase the gated
  `state-spaces/mamba2-8b` config to pin it.
- **Per-group *weight* scales: partially, and better than it looks.** `Q4_K`/`Q6_K` already carry
  6-bit sub-block scales per 32 elements inside a 256 super-block. So one group per 32 input channels
  is native to K-quants; anything finer is not. `Q8_0`/`Q4_0` are strictly per-32.
- **The transferable residue is the sort, not the scales.** ggml's block quantizers are *fixed-window
  scale sharing*; the paper's premise is that scale sharing is only good when the members of the
  window have similar magnitude ("we ... group the channels across the heads with the same value
  range to create a smoother landscape in the group", §3.3). Those are the same statement with
  different window sizes. **If channels are permuted at convert time so that similar calibrated
  magnitudes become adjacent, ggml's existing 32-element (and 256-element activation) windows become
  homogeneous — no new type, no kernel change.** That is the only part of Quamba2's layout story with
  a path into our tree, and it needs a calibration statistic we already compute: `llama-imatrix`
  emits exactly per-input-channel activation statistics.

Caveat that must travel with it: a permutation that homogenises *activation* windows simultaneously
re-blocks the *weight* tensors, which can coarsen weight quantisation. Net sign is not obvious and is
model-dependent; the paper measured net-positive only on SSM blocks, where the sort had a physical
justification (channel-order preservation across the SSD recurrence). A transformer has no such
justification — only the statistical one.

---

## 5. D — The comparison set, the tasks, and what the 1.6% hides

**Who is compared:** MambaQuant (Xu et al., 2025) at W8A8 and W4A8, and Quamba (Chiang et al., 2025)
at W8A8 — the latter being **Quamba1, same first author, same lab** (QD3). **SSDi8 is never compared
and cannot be**: it is a later work (ICLR 2026), and the comparison direction runs SSDi8 -> Quamba2.
Any statement of the form "Quamba2 vs SSDi8" in our own documents must be built from SSDi8's
side, which reports Quamba2 numbers itself.

**On which tasks:** five different panels, and the headline number comes from the least demanding one.

| Panel | Tasks | Where |
|---|---|---|
| 5-task average | ARC-easy, ARC-challenge, PIQA, WinoGrande, HellaSwag | Table 6 (the MambaQuant comparison) |
| 6-task average | the above + LAMBADA | Table 11 (the 1.6% source) |
| MMLU 5-shot + LAMBADA | multitask generalisation | Table 7 |
| Generation | NQ exact-match, SquadV2 F1 | Table 12 |
| Kernel | SSD latency, batch 8, L=256..2048 | Table 3 |

**Does the 1.6% hide per-task regressions? Yes — by a factor of two, and it excludes the hard panels
entirely.** From Table 11, Mamba2-8B, W4A8 vs FP16:

| LA | HS | PIQA | Arc-E | Arc-C | WG | Avg |
|---|---|---|---|---|---|---|
| -2.1 | -0.6 | -0.6 | -1.0 | -2.0 | **-3.3** | -1.6 |

WinoGrande loses 3.3 points and LAMBADA 2.1 — more than double the headline — while the average is
held up by HellaSwag (-0.6), PIQA (-0.6) and ARC-easy (-1.0), the three tasks that barely move. And the panels that are *excluded from the 1.6%* are the ones that collapse:

- **MMLU 5-shot: 47.0 -> 41.2 = -5.8 points** (Table 7), which the paper itself names (QD2).
- **NQ exact-match: 17.2 -> 14.2 = -3.0**; **SquadV2 F1: 51.9 -> 45.9 = -6.0** (Table 12).
- W4A16 is much better behaved on all three (MMLU 45.3, NQ 16.6, SquadV2 50.7), which is the paper's
  actual argument for W4A16 on edge.

**Two further traps for a comparator table:**

1. **Quamba2 loses the W8A8 average-accuracy comparison to MambaQuant.** Table 6: Mamba1-1.4B 57.5 vs
   58.3; Mamba1-2.8B 61.8 vs 62.1. The abstract's "outperforms two state-of-the-art SSM quantization
   methods" is carried by W4A8 (56.7 vs 54.3; 61.0 vs 58.5) and by latency, not by W8A8 accuracy.
2. **The number is protocol-dependent, so the protocol must be pinned.** Mamba2-2.7B W4A8 is 61.4% in
   the 5-task Table 6 and 62.1% in the 6-task Table 11; SSDi8 cites "Quamba2 62.1%" against its own
   62.6%. The 0.7-point protocol difference is larger than SSDi8's own 0.5-point margin over Quamba2.

---

## 6. E — Would any element fit llama.cpp/EPYC decode better than SSDi8/LinQuant?

Short answer: **one element does, and it is not the one the paper is about.** The mechanism, term by
term.

**1. Decode on EPYC is a bytes-per-token problem, so W4A16 has nothing new to sell us.** At batch 1,
CPU decode time per token is `effective_BW / bytes_per_token`, and `bytes_per_token` is dominated by
the weight bytes read once each. llama.cpp already has per-group weight scales, which is all the
*bytes* mechanism W4A16 needs. What it does not have is an offline Hadamard folded into the input and
output projections — the rotation we ship is KV-cache-only, applied at the cache write — and that is
the whole of Quamba2's W4A16 delta. Quamba2's W4A16 does not reduce bytes below `Q4_K`; it compresses
*better at the same bytes*, a quality claim rather than a speed claim. Its two mechanisms (offline
Hadamard fusion into the output projection, and the channel permutation) are both quality levers at
fixed bit-width, both conversion-time transforms.

**2. The counter-evidence against importing the rest is ours, and it is strong.** This project has
already measured the failure mode: a richer per-weight format (TurboQuant/trellis) lost **2.2x to
plain `q4_0`** on EPYC 9975 (573 vs 1279 tok/s) because compute-per-weight dequant on AVX-512 costs
more than the bytes it saves (`handoffs/active/quantization-and-low-bit.md:861`). Quamba2's
activation-side machinery — `m x n` per-group activation scales, per-state-group scales on B/C, an
8-bit state cache — is exactly that class of mechanism: extra per-weight/per-state compute and
side-information to buy precision, not bytes. At 4-bit on a bandwidth-bound CPU it prices negative
before it is even measured. (Its own GPU table agrees about the direction, just at a threshold we are
always below: QA2, W4A8 loses to W8A8 from b=256 up.)

**3. SSDi8/LinQuant aim at a bottleneck we do not have in decode — and at one we do not serve.**
Their mechanism is a persistent INT8 path *inside* the SSD recurrence (ChunkCumsum/ChunkState/
StatePassing/ChunkBMM/ChunkScan). That is a **compute-side** win: it matters when you are
TOPS-limited, i.e. batched prefill or large-batch decode. Single-stream EPYC decode is never
TOPS-limited; the `vec_dot` kernels are already waiting on memory. So on the decode axis the ranking
is not "SSDi8 better than Quamba2" — it is "neither, because the lever is bytes and both are
precision mechanisms". SSDi8 would only become interesting for CPU **prefill**, which for short
prompts is a small fraction of wall time on our workloads. And the decisive practical point: our
low-bit scope is DS41/Q38FN (`quantization-and-low-bit.md:15`), neither of which contains an SSD
recurrence, so a persistent-INT8-SSD path has **no consumer**. Quamba2 is the weaker of the two on
its merits but the *more* transferable of the two, because weight layout is architecture-agnostic
while an SSD kernel is not.

**4. The element that is genuinely a better fit: head-to-toe, specifically the lm head.** This is the
one place where Quamba2 states a mechanism that is *exactly ours* and that we may not be exploiting.
Its argument (QE1): once the blocks are 4-bit, a half-precision embedding and output head become the
memory bottleneck. On a bandwidth-bound CPU decode that argument is stronger than on their GPU,
because **the lm head is read in full on every single token and never amortises.** Arithmetic
(mine): for `V=128k`, `d=4096`, an FP16 embed+head is `2 x V x d x 2 B ≈ 2.1 GB`; the head alone is a
~1.05 GB read per token at FP16 versus ~0.26 GB at 4-bit. If a served model's total per-token weight
read is ~4-6 GB, the head is 20-25% of decode bytes and a 4-bit head is a ~15-20% decode saving **with
zero kernel work** — `output.weight` is already a quantizable tensor in llama.cpp. The paper's
evidence that this is safe is scale-dependent and honest: 8B LAMBADA 68.5 -> 68.8 quantising both
(i.e. within noise), 2.7B 65.8 -> 65.7, but 370M 50.5 -> 46.6 and 130M 37.6 -> 33.4 — catastrophic
below ~1B (Table 10, QE2). Our served models are all far above that cliff. **This is a
config-and-measurement task, not a research task**, and it is the only Quamba2 element I would carry
forward.

**5. What I would explicitly not carry:** the permuted-channel *sort* is expressible and cheap but
unproven for transformers and it re-blocks the weight quantiser as a side effect (§4); the 8-bit
state cache has no analogue (llama.cpp's SSM state is not a quantized type) and no consumer; the
`m x n` activation scales cannot be represented in ggml at all; and the whole SSD kernel path is
irrelevant to what we serve.

### Evidence quotes cited in §2-§6

- **QA1** — `f8662491e496fe0a7182121aeb703b753a2858c4c3a30a4151fc6ce579c2832e`
  > When the input batch size is small ( e.g., b=1 in the table), the generation is memory-bound and therefore loading 4-bit weights ( e.g., W4A8 and W4A16) improves the roofline model.
- **QA2** — `ca85a023e6304cc5c6bace8c0f6309449d98992b26b091bc6ea602d5572bb6b1`
  > The ultimate TOPS of W4A8 is lower than W8A8 due to the extra steps for dequantizing weights from 4-bit to 8-bit ( e.g., b=256 in the table).
- **QA3** — `42f8775b66dd918abcce1c5c9f6b849fe775249606f0dd513bca3995fe973bb6`
  > We study the impact of each component in the case of W4A16 Quamba2-8B (weight-only quantization, i.e. , \overline{W}X ), and show the results in Table 9 .
- **QA4** — `0183b6e7bf78ff027fa70e21a2a22b40197051766e733198842575859aab119d`
  > W4A8 and W4A16 slow down TTFT compared to W8A8 and FP16 due to dequantization overhead.
- **QC1** — `80efa6fd93ec72fd8cadc40a59d4d48d09772a18b286661976913f8641636968`
  > The output column of input projection weights and the channel of causal convolution weights are reordered.
- **QC2** — `904e29674accfd4487256531be4ae4817d90e8961fdcfe54e904481a96647b78`
  > For projection layers, we reorder the weights and their per-group scaling factors ( Lin et al., 2024b ; Frantar et al., 2024 ; Zhang et al., 2024 ) to maximize the Tensor Core loading throughput.
- **QC3** — `378fca1a418312ea86cb7ce2342185d1e9fc29f8a5be768fcff7d2d3df26b909`
  > For the output projection, the Hadamard matrices are multiplied at both sides of the weight matrix, such that \mathbf{W}_{\text{out}}^{H}=\mathbf{H}_{n}\mathbf{W}_{\text{out}}\mathbf{H}_{n}^{\top} .
- **QC4** — `395f09f06c07e1d417a4d72305824b1fd920cd275388b6fdc067b4ecccd93630`
  > To ensure compute-invariance in the SSM output, we rearrange weights offline according to the clustering sequence.
- **QD1** — `a2e4cf1d5325b0402c6c150fc9e537d9ab4860d9f31add811e33609f422589e0`
  > To compare with MambaQuant ( Xu et al., 2025 ) , we average the accuracy across five datasets: ARC-easy, ARC-challenge, PIQA, WinoGrande and HellaSwag.
- **QD2** — `2e6533fbd2a6c5eac93bcbcd5cc22534ffeab83506ad9a7ed672cb28f215fbf4`
  > Our findings indicate that while full W4A8 quantization maximizes prefilling speedup, it suffers from a notable generalization gap ( -5.8\% on MMLU vs. -2.1\% on LAMBADA).
- **QD3** — `67050bb97af71bda62ba4fe5308b9315207f0245794036c7ecfdcf69ec951ad5`
  > In our W8A8 setting, we compare our framework with the latest quantization methods for SSM, MambaQuant ( Xu et al., 2025 ) (W8A8, W4A8) and Quamba ( Chiang et al., 2025 ) (W8A8) on zero-shot downstream tasks.
- **QE1** — `6e520acedc05474053fd8cb4b2b5c17b9b2d6e96784b778baf486ce8a3a3e2e2`
  > As the weights in all layers are represented in 4-bit, the half-precision embedding layer and the output head become the memory bottlenecks, preventing the W4A8 models from being deployed to edge devices ( ref. Figure 1 W4A8).
- **QE2** — `94f673461c08d13f12e275918ce6aa951530a6a7eb7d9a003eab449903e681de`
  > We show that larger models present more resilience to quantizing both the embedding layer and the output head, as the accuracy on the LAMBADA dataset remains nearly unchanged.

---

## 7. Derived-actionables ledger

| ID | Action | Owning handoff | Disposition |
|---|---|---|---|
| Q2-1 | **Audit the lm-head/embedding precision of every served DS41/Q38FN GGUF, and price a 4-bit `output.weight` + `token_embd` arm.** The argument is pure bytes: the head is read in full every token and does not amortise, so at 4-bit blocks it is the largest remaining per-token read. Record actual tensor types, tensor byte sizes, and per-token read budget before proposing an arm; then one paired decode arm (Q6_K vs Q4_K head) with the standard paired quality panel. | `handoffs/active/quantization-and-low-bit.md` | **OPEN — recommended, cheap.** Config-level, zero kernel work, and the paper's Table 10 supplies the safety prior at our scale. Note the paper's own scale cliff (130M/370M collapse) so the panel must include a reasoning/MMLU-class task, not just LAMBADA. |
| Q2-2 | **Deciding probe on magnitude-sorted channel permutation for the K-quant activation window.** Offline, in numpy, on one real `Q4_K` row: sort channels by `llama-imatrix`-derived activation magnitude, then measure (a) activation quantisation error of the 256-element `q8_K` window, (b) resulting weight-block scale error, (c) net KLD on a held-out shard, permuted vs unpermuted. No conversion surgery, no GGUF change, no kernel. | `handoffs/active/quantization-and-low-bit.md` | **OPEN — bounded probe only.** Mechanism is real (§4) but the net sign is unknown because the same permutation re-blocks the weights; do not touch the converter until the probe is positive. Decline the conversion-time implementation even if the probe is positive, until someone can show the residual-stream permutation is consistent with RoPE head layout and our landed KV rotation. |
| Q2-3 | Port the 8-bit cached SSM state / per-state-group B/C quantisation into a CPU path. | `handoffs/active/model-architecture-readiness.md` | **DECLINED.** No SSD/Mamba model is in scope (low-bit work is DS41/Q38FN per `quantization-and-low-bit.md:15`); llama.cpp's recurrent state is not a quantized type, so this is a scan-kernel rewrite with no consumer; and its measured GPU decode value is inside the 2% W4A8-vs-W4A16 delta (§2). |
| Q2-4 | Record the resolved decode mechanism on intake-2646 so the Stage-2b question is never re-asked: "generation speedup is weight-streaming at batch 1 on an A5000; W4A16 (weight-only) is within 2% of W4A8; activation-side contribution <=2%; byte-to-time conversion 78%." | owning session (intake record edit; `research/intake_index.yaml` intake-2646) | **PROPOSED EDIT (subagent-prepared, session applies).** Preparation only — I did not write the lane worktree. |
| Q2-5 | Add the carried caveat to intake-2646's `reported_results`: the 1.6% is the 6-task common-sense average; MMLU 5-shot is -5.8, NQ -3.0 EM, SquadV2 -6.0 F1; 13 TPS rounds a measured 12.5. | owning session (intake record edit) | **PROPOSED EDIT.** Preparation only. |
| Q2-6 | Downgrade intake-2646's `contradicting_evidence` wording from SSDi8's "quantizes only SSD inputs" to partial corroboration, citing Quamba2's own 1.08-1.19x SSD-kernel table. | owning session (intake record edit) | **PROPOSED EDIT.** Preparation only. |
| Q2-7 | Cite Quamba2 in any future comparator table only with the protocol pinned (5-task vs 6-task changes 2.7B W4A8 from 61.4 to 62.1). | `handoffs/active/quantization-and-low-bit.md` (comparator admission rules, cf. `intake-1543#record`-`1550#record` matched-count boundary) | **RECORDED as a constraint.** No task. |

---

## 8. Surfaced sources not already in the index

Checked against `research/intake_index.yaml` (grep for author, repo and title): none of the following
has an entry. Listed as *candidates*, with what each would be good for and its verification status.

1. **Quamba code release — `https://github.com/enyac-group/Quamba`.** The paper's only artifact
   pointer ("The code and quantized models will be released at", L179). **Status unverified** — I did
   not fetch it; treat the URL as a claim, not a repository. If it exists, it is the only place the
   actual group boundaries, the permutation indices and the `m=4/n=4` implementation could be read,
   and it would settle the Figure-4-vs-§4.1 `m` discrepancy.
2. **MambaQuant (Xu et al., 2025).** Named baseline, W8A8/W4A8, and the method that *beats* Quamba2
   on W8A8 Mamba1 average accuracy. No index entry. Worth a row only as a comparator if SSD/low-bit
   SSM work ever reopens; not worth reading now.
3. **Quamba1 (Chiang et al., 2025).** The lineage root and the W8A8 baseline Quamba2 improves on —
   same first author. No index entry. Its absence matters for lineage claims: SSDi8's "comparator
   generation before SSDi8" chain is really Quamba1 -> Quamba2 -> SSDi8, and Quamba1 is the one that
   introduced the Hadamard-on-output-projection baseline that Quamba2 inherits.

Not surfaced (already covered or out of scope): SSDi8 (intake-2645), LinQuant (intake-2642), the
Hadamard-rotation KV work already tracked at `handoffs/active/quantization-and-low-bit.md:684-688`.

---

## 9. Artifact audit

| Item | Value |
|---|---|
| Raw artifact | `raw/quamba2.html`, 394,025 bytes |
| Raw sha256 | `a828ec49d1438106d1f94863e8a8728343b0dfe9b6c9e9f53d50eb4ea543c30f` |
| Extractor | LaTeXML HTML -> deterministic tag strip; `<math>` rendered from its `alttext` attribute |
| Extracted | `raw/quamba2.txt`, 74,610 chars / 74,827 bytes, 2,544 lines, sha256 `19f6db9d22a31bbbdfe576cb523c97866bd29b3d0bae8bcc4ad2216fcde8faf9` |
| Coverage | abstract, §1-§7, App. A-G, Tables 1-13, Figures 1-14, references skimmed |
| Source revision | arXiv:2503.22879v4, stamped 06 Nov 2025. v4 post-dates ICML 2025 (July 2025), so Apps. E-G and the mixed-precision search may be later additions; I did **not** diff against the PMLR version, so cite "arXiv:2503.22879v4" — not "ICML 2025" — for anything drawn from those appendices. |

**Normalisation caveats (affect quote reproducibility).** The HTML→text strip renders every math token
from LaTeXML `alttext` and collapses whitespace, which is why quotes show artefacts like `W8A8 , W4A8`
(space before comma) and `-5.8\%`. **Every `quote_sha256` above is computed over the strings exactly as
they appear in this report, i.e. over `raw/quamba2.txt`, and will not match a hash taken over the raw
arXiv HTML or PDF.** Anyone re-verifying should regenerate `quamba2.txt` from the pinned raw HTML with
the same strip, or hash the substring from the `.txt` line numbers given in the locator column.

**Defects in the source that citing documents must not inherit** (1-3 are the authors'/LaTeXML's, not
extraction errors; 4 is my recomputation):

1. **Figure-4 caption vs body on `m`:** figure illustrates `m=8`, §4.1 states `m=4, n=4` for all
   experiments.
2. **Cross-reference slips:** intro says "As shown in Table 2 and 2" (should be 1 and 2); §4.2 and
   §5.2 both cite "Table 4" for SSD latency (it is Table 3); App. E cites "Table 11" for the
   TPOT-vs-batch matrix, which is captioned **Figure 11** (a table labelled as a figure).
3. **QA4 ("W4A8 ... slow down TTFT compared to ... FP16") is contradicted by Table 5**, where W4A8
   TTFT is 140.78 ms against FP16's 197.80 ms.
4. **1.39x prefill recomputes to 1.41x**; 3.89x memory recomputes to 3.93x. Both understated, so no
   claim is inflated by them — but cite the recomputed values or say "as reported".

**What this dive did *not* do:** no build, no run, no reproduction of any number. Every Quamba2 figure
here is a read of the paper. Nothing was written into the lane worktree
(`/mnt/raid0/llm/worktrees/intake-quant-compiler-20261106`); the lane was read-only and remains clean
except for the two files that were already modified before this dive (`.research-session.json`,
`research/intake_index.yaml`).
