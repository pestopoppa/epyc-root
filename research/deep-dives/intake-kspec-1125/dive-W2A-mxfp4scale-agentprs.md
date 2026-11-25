# W2A-mxfp4scale-agentprs: OAS vs floor/Midmax for MXFP4, and agent perf-PR validation reporting

Entries covered (new, Stage-2b, dive-verified): intake-2978 (arXiv 2603.08713v1), intake-2979 (arXiv 2610.03969v1).
Read depth: intake-2978 FULL (68k chars). intake-2979 PARTIAL (read: abstract, intro, method 3.4/3.5, results 4.3/4.4, threats, discussion 6.1-6.4, conclusion; NOT read: RQ1/RQ2 results 4.1-4.2, 3.1-3.3 details, 6.5, references).
Date 2026-11-25. Lane head f19b902; C21 worktree 98ff8a4.

## intake-2978: Overflow-Aware Scaling (OAS)

### What OAS is, exactly
- Block of 16 (not 32). Scale is a power of two (E8M0, run on the NVFP4 pipeline with E4M3 holding powers of two).
- Standard routine maps the block max into (3,6]. OAS maps it into (3.5,7] instead (Sec 4.2).
- When the standard mapping lands in [3,3.5], OAS doubles the scale factor, so the max lands in [6,7] and is clamped to 6. The relative error on that max is unchanged, and every smaller element gains one binade of range.
- OCP MXFP4 (floor) maps the max into (4,8] (Sec 4.2).
- Implemented by "checking mantissa bits". About 15% of blocks change. Claimed QSNR +0.5 dB, no overhead.

### OAS vs floor vs Midmax (my reduction; derived, not a paper claim)
- Floor: scaled max in [4,8). Our `quantize_row_mxfp4_ref` is exactly this: `floorf(log2f(amax)) - 2 + 127` (ggml-quants.c:L368 @ 98ff8a4).
- OAS window (3.5,7] equals floor window [4,8) with one change: if the floor-scaled max is above 7, take the next scale up (max lands in (3.5,4)). Otherwise identical to floor.
- Midmax (intake-2961): round the scale up when the floor-scaled max is >= 7.0. Same threshold. The rules differ only at exactly 7.0 (OAS keeps it, Midmax rounds up). So OAS and Midmax are the same rule from two papers. Neither paper cites the other in the text I read.
- Both trade a 14%-21% clamp error on blocks whose max is in (7,8) for a mid-binade max with finer small-value resolution. Neither is MSE-optimal; a direct per-block MSE choice between e and e+1 would subsume both (not tested by either source).

### Verdict table
| # | Claim | Verdict | Locator |
|---|---|---|---|
| 0 | OAS maps max to (3.5,7] vs OCP (4,8] | CONFIRMED | Sec 4.2 |
| 1 | ~15% blocks affected, +0.5 dB QSNR, zero overhead | CONFIRMED as stated (QSNR is W+A mixed, no split) | Sec 4.2 |
| 2 | OAS improves accuracy | PARTIAL: +2.84 (Llama3.1-8B) and +2.89 (Qwen3-8B) avg points over MXFP4-16; but DeepSeek-R1 MMLU-Pro 76.29 to 75.36 and GSM8K 96.66 to 96.29 go DOWN; Llama Winogrande 72.14 to 71.27 down | Tables 1,2,3 |
| 3 | Evidence is weight-only usable | NOT-FOUND-IN-SOURCE: every result quantizes weights AND activations, direct-cast, vLLM; no weight-only ablation; no KLD; perplexity is Wikitext word-level | Sec 5.1, Table 6 |
| 4 | "gap to NVFP4 10% to <1%" | PARTIAL: that closure needs MBS (extra 8-bit mantissa per 128 elements), not OAS. Tables show avg gap to NVFP4 of 5.77 / 5.98 points for OCP (derived), MBS-H 0.52 / 0.64. "10%" matches OCP loss vs BF16 on DeepSeek MMLU-Pro, not the avg gap | Abstract, Tables 1-3 |

Other checks: OAS's own contribution at block 32 is not tested (MXFP4-16 vs MXFP4-16-OAS only). Block 16 alone is mixed (Llama -0.70 vs OCP, Qwen +1.32, derived), so OAS carries the gain at 16. The text also says MX+ +1.76 and OAS +1.42 over MX+; I checked these reproduce from Tables 1-2.

### Weight-only vs needs-activation-quantization
- Weight-only applicable offline (GGUF requant, KLD-judged): the OAS scale rule itself (a one-line change to the exponent choice; dequant is unchanged, so no kernel change on either device).
- Needs activation quantization or new format: all reported OAS accuracy numbers; MBS (1x128 macro scale, GEMM epilogue, CUTLASS/Blackwell kernel); block 16 on NVIDIA hardware.
- Tension with intake-2961: that entry measured Midmax at about +0.12 points average, weights only. OAS here shows +2.8 with W+A. Since the rules are the same, the likely driver is activation quantization (per-token online blocks have heavier tails). This is an inference, not tested.

### Adversarial pass (2 searches)
- No independent reproduction found. Search shows an ICML 2026 poster listing and PMLR page (venue evidence from a search result; the source text only says "Keywords: ICML"). Restatement, not corroboration.
- Related, surfaced by search: "Four Over Six" (arXiv 2512.02010, two candidate scales per NVFP4 block, MIT-Han-lab code) and "Half-S" (ACL Findings 2026) on halving the MXFP4 scale. Both are the same family of scale-choice fixes. Not read.

### In-house comparison
- `quantize_row_mxfp4_ref` uses plain floor (ggml-quants.c:L350-L382 @ 98ff8a4; floor at L368). No OAS/Midmax, no MSE search.
- Only MXFP4 model served is the lossless native-FP4 repack (handoffs/active/deepseek-v41-flash-evaluation.md:L1089-L1093 @ f19b902: bit-for-bit repack, KLD 0.0290 to 0.0102 vs Q4_K requant). A lossless repack never calls the quantizer scale rule, so OAS cannot change it. OAS only matters if we requantize a BF16 model to MXFP4 ourselves.
- MXFP4 showed no CPU speed case (x1.00 N=1, x1.04 N=3; quantization-and-low-bit.md:L174 @ f19b902), so any MXFP4 requant would be quality-per-byte only.

### Principles table
| Principle | Source evidence | MI210 (gfx90a) | EPYC Zen 5 | Why (mechanism) | Port cost |
|---|---|---|---|---|---|
| Overflow-aware E8M0 scale choice (round up when floor-scaled max > 7) | Sec 4.2, Tables 1-3, 6 (W+A) | TRANSFERS (quantizer-side only; dequant unchanged) | TRANSFERS (same) | Changes only the stored exponent at quantize time; no FP4 hardware needed; tail elements gain a binade, max clamp error stays below the old worst case | ~3 lines in the experimental quantizer plus KLD check; value only when a BF16 to MXFP4 requant is wanted |
| Direct MSE choice of e vs e+1 (generalizes OAS/Midmax) | Not in source; implied by Sec 4.3.3 MBS-D SSE search | TRANSFERS | TRANSFERS | Offline, once per block, free at inference | Small; offline CPU |
| Macro Block Scaling (1x128, 8-bit mantissa) | Sec 4.3, Tables 1-3 | DOES-NOT-TRANSFER as a GGUF type today (needs new block type and dequant path; its win is tied to FP4 tensor cores' epilogue) | TRANSFERS-WITH-CHANGES (new type, ~0.0625 bpw extra, derived) | Costs a new format plus kernels; gain measured only W+A | High (new type, repack kernels, KLD/PPL validation) |
| Rotation (block Hadamard) | Only discussed: Sec 3.2 says rotation leaves flush-to-zero decrease unchanged; not proposed or run here | UNKNOWN-NEEDS-PROBE | UNKNOWN-NEEDS-PROBE | Weight-only offline rotation needs the inverse folded into neighbours; this source gives no evidence; see intake-2961 | Not estimable from this source |
| Block 16 with E8M0 | Sec 3.2, 4.1 (+1 dB QSNR) | DOES-NOT-TRANSFER now (GGUF MXFP4 is 32) | same | Would be a new block type (4.5 vs 4.25 bits/elem, Sec 3.4) | Medium-high |

## intake-2979: agent performance PRs

### Does it corroborate "agent perf PRs rarely validate their claimed mechanism"?
No. It does not test mechanisms at all. It is artifact-only: it classifies what the PR text says, and states "RQ4 neither verifies performance effects nor reproduces experiments." and "We do not execute the changed code, reproduce the reported experiments, or independently verify the performance claims." So it cannot confirm or refute intake-2958's finding (claimed mechanism held in 34 of 82). What it does independently show, about reporting only:
- Validation presence is similar for agents and humans (82.3% vs 80.6%).
- Agents lean on static reasoning (51.4% vs 39.3%) and benchmarks less (46.1% vs 57.2%), though benchmark use converges by 2026-Q2 (60.1% vs 58.7%).
- Among validated PRs only 50.9% (agentic) / 52.4% (human) report any quantitative metric.
- A claim-to-metric check: 34.5% of PRs report a metric the labelled pattern is expected to improve, vs 23.7% under a permutation baseline (p=0.002). That is weak association, not mechanism proof.
- Caveats: LLM labelling (3 models), regex metric extractor with 87.5% precision and unknown recall, human-authored comparison uses "no observable AI signal", and the authors warn agents may imitate benchmark reporting form.

Verdict: weak, partial corroboration of "reporting is incomplete"; NOT corroboration of "mechanism unvalidated".

### Taxonomy and what could shape an AutoKernel row
- Validation type (one primary): Benchmark-Based, Profiling-Based, Static-Reasoning-Based, Anecdotal/Informal, or none. Defined by form, not soundness: the paper says a benchmark label "establishes only that a measurement is reported".
- Metric dimensions M1-M9 (latency, throughput, memory, CPU work, I/O, size, build time, energy/cost, scalability) plus M0 (quantified gain with no named metric). Trade-off reporting (runtime vs memory) is rare.
- Sec 6.4 sketch: a model that states target metric, workload, baseline, measurement protocol and acceptable costs elsewhere.
- Not in the paper: A/A controls, counters, effect sizes with intervals (the only "effect size" use is Cramér's V on its own comparisons), claimed-mechanism fields. intake-2958 remains the source for those.
- In-house: `ak_row_lint.py` NO-WITNESS (L39, L680-L682 @ f19b902) fires only when the decision rule names a GGML_/LLAMA_ knob with no witness key; it does not check mechanism, counter, A/A or effect size. The spec already has `mechanism_prediction` (autokernel-loop.md:L1605-L1608) and a T1c rule that a failed mechanism prediction withholds the mechanism bonus (L2209-L2220); the keep path lists A/A as a timed stage (~L4423-L4426). So the required fields exist in the spec; the gap is lint enforcement, and this paper adds nothing beyond a vocabulary (the "none/anecdotal/static/profiling/benchmark" evidence-type ladder and M0 "unnamed gain" catch).
- Usable pattern: a lint rule rejecting an M0-style row (a gain claim with no named metric) and recording evidence type as a closed enum on the row. Small value.

## Derived-actionables ledger
- KS-W2A-mxfp4scale-agentprs-1: add OAS/Midmax or MSE-of-{e,e+1} scale choice to the experimental MXFP4 quantizer, KLD-judged, only when a BF16 to MXFP4 requant is actually scheduled. monitor.
- KS-W2A-mxfp4scale-agentprs-2: cite OAS and Midmax as ONE rule with two names; do not quote OAS's +2.8 points as weight-only. knowledge-only.
- KS-W2A-mxfp4scale-agentprs-3: do not pursue MBS or block-16 types now. decline (reopen if an FP4-capable device or a new CPU 4-bit type is planned).
- KS-W2A-mxfp4scale-agentprs-4: ak_row_lint candidate check for rows whose decision rule claims a mechanism but record no counter/A/A key (builds on intake-2958, not this paper). monitor; owner autokernel-loop.md.
- KS-W2A-mxfp4scale-agentprs-5: cite intake-2979 only for reporting-gap statistics, never as evidence about mechanism validity. knowledge-only.

## Dive-surfaced sources
- arXiv 2512.02010 "Four Over Six" (search result, not read): adaptive two-scale choice for NVFP4. Recommend decline (wave limit; same family).
- ACL Findings 2026 "Half-S" (search result, aclanthology 2026.findings-acl.241, not read): halve MXFP4 scale. Recommend decline (wave limit), flag for review if MXFP4 requant is scheduled.
- From source text: arXiv 2509.23202 (Egiazarian et al., microscaling FP4 PTQ with rotation, MSE guarantee). Bears on rotation question and intake-2961. Recommend ingest-and-dive only if rotation is pursued.
