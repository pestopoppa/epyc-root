# Dive — bspecforensics — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2510.22876v4", retrieved: "2026-11-23", sha256: "17875e337308"}

Expanded from intake-2830 (vegafafnir), section 7. Version note: the HTML read is **v4** (31 Aug 2026), retitled "Correctness Forensics for Batch Speculative Decoding: Diagnosing the Ragged Tensor Problem", accepted to Findings of EMNLP 2026. v1 (26 Oct 2025) was titled "Batch Speculative Decoding Done Right". Its abstract, read via the arXiv abs page for v1 and not anchored, says "maintaining 95% output equivalence" with efficient scaling "through batch size 8". The arXiv listing shows v2 on 29 Jan 2026 and v3 on 15 Feb 2026. Code: `github.com/eBay/spec_dec` (exists; not cloned).

## 1. Stage-1 fields

- **Title (v4)**: Correctness Forensics for Batch Speculative Decoding: Diagnosing the Ragged Tensor Problem
- **Authors**: Ranran Haoran Zhang, Soumik Dey, Ashirbad Mishra, Hansi Wu, Binbin Li, Rui Zhang (Penn State; eBay)
- **Version**: arXiv 2510.22876v4, 31 Aug 2026, cs.CL; Findings of EMNLP 2026
- **Categories**: speculative_decoding, benchmark_methodology, inference_serving
- **Novelty**: medium in general, low for us. It formalizes the synchronization invariants for contiguous-layout batch speculation (I1 rectangular alignment, I2 position/KV correspondence), provides a failure-signature diagnostic (exact vs partial match), and shows that published implementations (BSP, DSD) silently emit garbage. llama.cpp's unified KV is cell-indexed (per-cell pos/seq), which is the paper's Family B-like layout, so I1 never arises for us. I2 does.
- **Relevance**: medium. The I2 invariant and the "high partial, low exact means cache drift, ending in repeat loops" signature map onto our open np4 problems: DF2-12.1 / C8-NP4-GARBAGE (repeat loops at np4 only) and C18-REPLAY-Q4X-CONC-BISECT (concurrent-only excess divergence). The headline exact-match figures are HF fp16 on A100 and do not transfer as thresholds.
- **credibility_score**: 3. Findings of EMNLP 2026, peer-reviewed: +2. v4 is within 12 months: +1. No major-lab byline (Penn State plus eBay research; I do not count eBay as a major ML lab): 0. eBay sells nothing here, so no commercial bias: 0. No independent replication found: 0.
- **Verdict**: adopt_patterns. Adopt the I2 invariant as a multi-sequence ragged-rollback test, and the partial-match signature as a classifier input. EqSpec/EXSpec are not adopted (see §6).

## 2. Key claims

0. **"95% exact match at batch 8": OVERTURNED for v4 (reattributed to v1).** v4 reports 90.8-97.3% exact match against batch-size-1 non-speculative decoding, and its Table 2 has exact match only at **batch 1 and batch 4** (EqSpec/EXSpec batch 4: Vicuna 92.1/90.8, Qwen3 92.3/95.0, GLM4 96.5/95.2). No batch-8 exact-match figure is in v4. The "95% ... through batch size 8" wording is from the v1 abstract. In v4, "batch size 8" attaches only to the 3x EXSpec throughput claim.
   - page Abstract: "Our methods remove catastrophic synchronization failures but achieve 90.8–97.3% exact match against batch-size-1 non-speculative decoding"
   - page Abstract: "On SpecBench across three model families, EXSpec reaches 3 × 3\times throughput at batch size 8"
   - page Table 2 caption: "EqSpec and EXSpec do not achieve bit-exact identity; DSD and BSP exhibit near-zero exact match"
1. **Root cause is the ragged tensor problem. I1 matters only for contiguous layouts; I2 (position plus KV correspondence after rollback) is required for every layout, variable-length ones included: CONFIRMED.**
   - page Abstract: "variable token acceptance desynchronizes position IDs, attention masks, and KV-cache across a batch"
   - page §3.1: "Continuous-batching systems (vLLM, SGLang) sidestep I1 through variable-length packing (Family B, Section 2 ), but I2 remains a prerequisite for correctness regardless of batching strategy"
2. **Failure signatures: near-zero partial match means position-ID errors (immediate). High partial with low exact match means KV-cache drift, a gradual decay that ends in repetitive loops: CONFIRMED** (BSP: partial match up to 39.7%, exact ≤3.5%; DSD: near zero on both).
   - page §6: "high partial / low exact ⇒ \Rightarrow cache drift; both low ⇒ \Rightarrow position-ID errors"
   - page §2: "Our partial-match diagnostic reveals BSP’s signature: initially correct output before KV-cache drift triggers repetitive loops (gradual decay, not immediate failure)"
3. **The residual mismatch is batch-dependent floating-point noise: PARTIAL.** The authors only assert consistency ("consistent with"); they report no margin evidence. Supporting data: non-speculative batched decoding at batch 4 vs batch 1 is only 53.8% (Vicuna), 92.9% (Qwen3) and 93.3% (GLM4) exact. In the vLLM v1 control (Qwen3-4B/0.6B, K=3, 80 MT-Bench prompts), batch-invariant kernels give 80/80 on all three comparisons on H100, but on A100 they give 62/80, 58/80 and 56/80. So the batch-invariant mode did **not** restore identity on A100, and the paper does not explain why.
   - page §4.2: "The remaining divergence is consistent with batch-dependent floating-point effects and argmax tie-breaking"
   - page Table 4: "H100 on 80/80 80/80 80/80 off 66/80 80/80 62/80 A100 on 62/80 58/80 56/80 off 58/80 61/80 63/80"
   - page Table 2: "Non-Spec-Batch – – 53.8 98.2 – – 92.9 96.5 – – 93.3 97.2"
4. **Realignment overhead grows superlinearly: PARTIAL, with an internal inconsistency.** The intro says it reaches 40% at **batch size 8**. §4.3 says it rises from ~13% at BS=1 to nearly 40% at **BS=32**. The Figure 5b caption says "up to 38%". The superlinear trend is supported, but the batch size at which ~40% is reached contradicts itself. Either way the cost is specific to contiguous layouts.
   - page §1: "this overhead grows superlinearly, reaching 40% at batch size 8"
   - page §4.3: "Overhead rises from ∼ 13 % \sim 13\% at BS=1 to nearly 40% at BS=32"

## 3. Reported results (as stated)

Setup: A100 80GB, PyTorch 2.7, HF Transformers 4.51.3, FP16, greedy, 5 draft tokens per round. Pairs: Vicuna-7B/68M, Qwen3-8B/0.6B, GLM-4-9B/0.6B. SpecBench (plus Multi30k for grouping).
- Table 2, exact/partial match vs BS=1 non-speculative:
  - EqSpec BS1: 97.3/98.6, 94.6/96.9, 96.7/98.1. BS4: 92.1/98.6, 92.3/95.7, 96.5/98.3.
  - EXSpec BS4: 90.8/97.6, 95.0/97.1, 95.2/97.7.
  - Spec-1 (BS1): 97.1, 94.6, 96.0.
  - Non-Spec-Batch BS4: 53.8, 92.9, 93.3.
  - DSD: 0.0-0.2 exact. BSP: 0.2-3.5 exact, partial up to 39.7.
- Table 4, vLLM v1 control (Qwen3-4B/0.6B, K=3, 80 MT-Bench, greedy), columns non-spec BS>1 / spec BS=1 / spec BS>1:
  - H100 batch-invariant on: 80/80/80. Off: 66/80/62.
  - A100 on: 62/58/56. Off: 58/61/63.
- Throughput: EXSpec 3x at BS=8. Overhead anatomy: EqSpec 95.6 TPS vs EXSpec 156.4 TPS (64% higher); OH% 27.7 vs 14.6.
- Online tradeoff: EXSpec 2-14% more throughput but 1.5-7.7x worse P90/P99. EqSpec P99 < 23 s at all batch sizes.
- Table 7, continuous batching vs each system's own non-speculative mode, exact match:
  - vLLM+Spec: 96.9 / 65.6 / 72.7
  - SGLang+EAGLE: 69.8 / 47.7
  - SGLang+EAGLE+Det: 85.0 / 50.6

## 4. Performance-principles table

| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| P1. I1 rectangular alignment and dynamic padding (unpad-append-repad) | NO. llama.cpp's KV is cell-indexed (`llama_kv_cache::find_slot`, per-cell pos/seq metadata; design doc §1b cites `src/llama-kv-cache.cpp:916`). Sequences never share a padded rectangle, so I1 never arises. Not a port gap: the layout makes it moot. | NO, same KV implementation. |
| P2. I2 position/KV correspondence after per-sequence rollback, plus recurrent state (our hybrid extension) | YES, and live. Per-slot `seq_rm` across ragged acceptance, GDN state rollback or replay per seq, and slot reuse are exactly suspects (a)/(c) of C18-REPLAY-Q4X-CONC-BISECT and the C8 np4 hypothesis ("rollback/seq_rm across slots, per CH-37"). | YES. The Q38FN np4 concurrent replay excess (r7) is on CPU. |
| P3. Partial-match signature (match length before first divergence plus loop onset) as a defect-vs-noise discriminator | YES, analysis only. The C8 np4 diag pattern (np1 0/32 flagged; np4 12/32 with repeat loops; `n-max=1` 0/32; without `--kv-unified` 0/32; speculative-decoding.md:2234) matches the paper's KV-drift signature better than a pure near-tie flip. | YES, same harness. |
| P4. EXSpec same-length grouping to skip realignment | NO: no realignment exists to skip (P1). | NO. |
| P5. Non-speculative batched decoding as the mandatory numeric control | YES. DF2-12.1 already requires a speculation-off np4 control. The 53.8% Vicuna Non-Spec-Batch figure shows why it is mandatory. | YES. |

## 5. In-house state

- **No test covers multi-sequence ragged rollback.** `tests/test-recurrent-state-rollback.cpp` sets `cparams.n_seq_max = 1` (L13 @ a6a32c1). `tests/test-multiseq-ubatch.cpp` teacher-forces 3 sequences with changing subsets but never rolls back. `tests/test-gdn-replay-identity.cpp` is single-sequence (snapshot vs replay, bitwise). `tests/test-device-accept-multiseq.cpp` tests lazy logits download only. These are all the multi-seq, rollback and replay tests at C19 `a6a32c1`.
- DF2-12.1 (`handoffs/active/speculative-decoding.md:2229 @ d785b6d`) is open. It covers 27B DFlash2 np4 and A3B draft-MTP np4, with the near-tie rule top-1/top-2 gap ≤ 0.25 (L2238) and controls including speculation off at np4. C10 27B np4 PASS (0 real divergences in the spec arms; the speculation-off control had 5 real out of 16; L2241). The A3B shape FAILed on a repeat loop, later adjudicated partly as a harness artifact (L2239-2240).
- C8-NP4-GARBAGE (`kernel-champion-and-promotion.md:230`) and the C8 diag (speculative-decoding.md:2234): loops only at np4; removed by `n-max=1` or by dropping `--kv-unified`.
- The Q4X replay re-allow failed concurrent identity: r6 ON 13 vs OFF2 10; r7 ON 31 vs OFF2 23 over 4 judged triples; phase S symmetric (speculative-decoding.md:1316-1319). Diagnostic row C18-REPLAY-Q4X-CONC-BISECT (`kernel-champion-and-promotion.md:53`) is open.

## 6. Derived-actionables ledger

- **B1 (refines intake-2830 A4 and C18-REPLAY-Q4X-CONC-BISECT suspects (a)/(c); code plus a tiny CPU test).** Task: write `tests/test-multiseq-ragged-rollback.cpp`. Put 3-4 sequences in one context and run it with `kv_unified` both true and false. Each round, decode k+1 rows per sequence, accept a different a_i per sequence (including 0 and k+1), then roll back each sequence via `seq_rm` with snapshot restore, and via `LLAMA_RS_REPLAY`. Compare each sequence's next-round logits with a single-sequence reference that replays the identical accept pattern. Pass: the test-multiseq-ubatch tolerance (≤ ~0.5 max |logit| on a 0.8B Q8_0 hybrid). Replay vs snapshot on CPU must be bitwise for an F32 log replayed in the same order. Owner: kernel-champion-and-promotion.md (C18-REPLAY-Q4X-CONC-BISECT, autokernel), with a pointer from speculative-decoding.md DF2-12.1. Compute: a unit test on a small model (seconds to minutes, CPU q0-q2, no row). Decision rule: if it fails, the concurrent divergence is an I2-class state defect, so the bisect row is superseded by the fix and DF2-12.1's loop hypothesis gets a mechanism. If it passes in both kv_unified modes, demote suspects (a)/(c) and take TIE_FLIPS as the bisect's prior. This changes the run order: run B1 before booking the bisect.
- **B2 (refines DF2-12.1 classification, speculative-decoding.md:2229; doc/analysis-only).** Task: add two fields to the DF2-12.1 per-divergence record: tokens matched before the first divergence, and whether a repeat loop starts within 64 tokens after it. Tag "near-tie first divergence followed by loop onset" as DEGEN_AFTER_TIE. It counts as a defect when the speculation-off np4 control shows no such case, whatever the first-divergence margin. Reason: the paper's KV-drift signature begins with correct output and decays into loops, so a small margin at the first divergence does not clear a state defect. Owner: speculative-decoding.md (DF2-12.1). Compute: none; re-classify the retained C8/C10 runs. Stop: answered when every retained np4 loop case is tagged.
- **B3 (guard on intake-2830 A1/A3; doc-only).** Task: record in DF2-12.1 / design doc §3 that no fixed exact-match threshold imported from literature (this paper's 90.8-97.3% or v1's "95%") may serve as an identity pass criterion. These are HF fp16 A100 figures, and even non-speculative batching there scored 53.8% on Vicuna. The gate stays margin-classified against an in-row A/A floor. Owner: speculative-decoding.md. Compute: none.
- **Decline: adopt EqSpec/EXSpec (dynamic padding, same-length grouping).** llama.cpp's cell-indexed unified KV has no rectangular batch to realign (P1). Their whole cost model (up to ~40% overhead) addresses a problem our layout does not have.
- **Decline: run a batch-invariant mode as an np4 fix.** Table 4 shows vLLM batch-invariant kernels failing to restore identity on A100 (62/58/56 of 80). Our GPU knob is atomics ordering, not batch invariance (llm42 entry L1). Neither makes A/B identical.

## 7. Dive-surfaced sources

- **github.com/eBay/spec_dec** (code; not in the index). Decline. HF-transformers contiguous-layout implementation; B1 does not need it.
- **arXiv 2510.22876 v1 ("Batch Speculative Decoding Done Right")**: same entry, earlier version. The 95%/BS8 wording is recorded in dive_corrections. No separate entry.
- **arXiv 2601.11580 (Liu et al., "Speculative decoding: performance or illusion?")**: already ingested as intake-1845.
- **BASS (Qian et al., Findings ACL 2024)**, custom-kernel masking. Decline. Contiguous layout plus CUDA kernels; it would not change B1-B3.

## 8. Contradiction / adversarial pass

- **Internal inconsistency**: ~40% overhead at BS=8 (intro) vs at BS=32 (§4.3) vs "up to 38%" (Fig. 5b).
- **Version drift**: the widely relayed "95% at batch 8" (the v1 abstract, also in the web-search snippet) is not what v4 reports. Snippets relaying it are restatements of a superseded version.
- **Attribution is asserted, not measured**: the residual mismatch is "consistent with" floating-point effects, with no top-2 margin capture. A100 batch-invariant 56-62/80 is unexplained and could hide a residual defect.
- **Cross-entry tension with intake-2830**: on H100 vLLM v1 with batch invariance off, speculative BS=1 matched non-speculative BS=1 on 80/80. On that stack, verify width alone flipped no prompt, while Vega-Fafnir's HF/4090 stack flips 60% with verify-4. Verify-width sensitivity is a property of the stack, which agrees with Vega-Fafnir's own caveat (its claim 5).
- **Limitations stated**: contiguous layouts only, not integrated with vLLM/SGLang, gains confined to moderate batch sizes, no bit-exact identity.

## 9. read_depth

FULL for the v4 HTML body and appendices A-I. Figures were not viewed as images. The v1 abstract was read via the arXiv abs page only (not anchored). The repo was not read. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## 10. Artifact audit

artifact audit: clean. page.txt (78923 bytes, sha256 17875e337308…) is retained (artifact=yes, arXiv v4). All 14 quotes used are verified substrings.

**Bearing on intake-2830 / quotability:** this paper anchors no Vega-Fafnir number. It anchors (i) the observation that batched execution alone diverges from batch-1 (Non-Spec-Batch 53.8-93.3%), (ii) vLLM batch-invariant identity results that differ by GPU, and (iii) the I2/partial-match diagnostics. For np4 parity, it points away from "near-tie" as the default explanation for np4 repeat loops and toward an I2 state-correspondence check (B1).
