# Dive — copyro — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2611.27217v1", retrieved: "2026-11-23", sha256: "487b68801374"}

## 1. Stage-1 fields

- **Title**: CoPyro: Feeding Copy Proposals to Parallel Drafters
- **Authors**: Hong-Kai Zheng, Piji Li (Nanjing University of Aeronautics and Astronautics)
- **Version**: v1, 20 Nov 2026, cs.CL
- **Code**: "will be released" at github.com/dt-3t/CoPyro. On 2026-11-23, `gh api repos/dt-3t/CoPyro` returns 404.
- **Categories**: speculative_decoding, retrieval_augmented_decoding, training_distillation
- **Novelty**: medium. Hybrid copy-plus-neural drafting is old (SAM-Decoding chooses one source by match length). CoPyro's new step is feeding the copied tokens to a block drafter as inputs, in place of mask tokens, together with two learned reliability embeddings, so the drafter learns to keep or revise each copied token.
- **Relevance**: medium.
  - It targets our served drafter family: DFlash2 on the 27B, served on :8083.
  - The gains are small against a strong drafter: +1.08–2.00% acceptance length and +0.39–1.33% throughput with the 710K-trained DFlash.
  - Every gain requires retraining the drafter.
- **credibility_score**: 1. Arithmetic: not peer-reviewed (0); recent (+1); not a major lab (0); no commercial bias (0); no corroboration (0).
- **Verdict**: worth_investigating.
  - There is no training-free path in the paper.
  - The natural carrier is DF2-FT-1, the in-house drafter fine-tune pilot. Adding proposal inputs, zero-initialised tables and proposal dropout to that recipe costs little extra once training happens anyway.
  - A one-row training-free probe can settle whether our existing DFlash2 weights tolerate copied tokens at all.

## 2. Key claims

0. **Copy proposals replace mask tokens in the drafter input: CONFIRMED.**
   - Retrieval: the longest context suffix with an earlier occurrence is found through an online suffix automaton, with minimum match length 1. The up-to-B−1 tokens that followed that occurrence are copied. Matches never cross control tokens.
   - The first K mask embeddings become E(c_k), plus a slot-indexed match-length embedding (21 buckets) and a slot-indexed agreement embedding (5 buckets).
   - Architecture, cost and verification are otherwise unchanged. The two tables add about 1.0M parameters at d = 2560 and 1.6M at d = 4096.
   - Anchor: "CoPyro replaces the first K K mask embeddings of the block with the embeddings of the proposed tokens and adds a match-length embedding and an agreement embedding".
1. **Drafter retraining is required: CONFIRMED. A training-free variant: NOT-FOUND-IN-SOURCE.**
   - Every drafter and its CoPyro variant are trained from scratch with the same recipe. The tables are zero-initialised and trained jointly, with proposal dropout p = 0.2.
   - The only inference-time ablation (Table 5) turns proposals *off* in a CoPyro-trained model: 3.90 vs 3.93 for plain DFlash. Feeding proposals to an untrained DFlash or DFlash2 is never tested.
   - Anchors: "so we train each drafter and its CoPyro variant from scratch with the same recipe"; "We train the drafter and zero-initialized copy tables".
2. **Qwen3-4B acceptance-length gain of +2.19–5.08% (100K samples, 4 drafters): CONFIRMED.**
   - Per drafter: DFlash 5.08%, Domino 3.40%, DSpark 2.19%, DFlash2 3.03%.
   - Throughput gains: +4.04%, +2.56%, +0.99%, +1.83%.
   - Setting: T = 0, Transformers, batch 1, BF16.
   - Anchors: "with gains of 2.19–5.08% when trained on 100K samples"; "the relative gains are 5.08% for DFlash, 3.40% for Domino, 2.19% for DSpark, and 3.03% for DFlash2".
3. **+1.08–2.00% with DFlash trained on 710K samples: CONFIRMED.**
   - The range covers acceptance length across Qwen3-4B/8B at T ∈ {0, 1}. Throughput is only +0.39–1.33%.
   - Both figures are for DFlash (v1). The 710K study did not include DFlash2.
   - Anchors: "With DFlash trained on 710K samples, overall gains range from 1.08% to 2.00% across the tested model sizes and temperatures."; "1.08–2.00% in Overall acceptance length and 0.39–1.33% in end-to-end throughput".
4. **+0.24 ms per round on Qwen3-8B in Transformers: CONFIRMED.**
   - Measured value: 0.238 ms, 95% CI [0.089, 0.427], on an RTX 3090, BF16 SDPA, batch 1, with the C++ index. Index build costs 0.355 ms per request.
   - SGLang at batch 1/8/16 adds 0.223–0.557 ms per batch round.
   - Anchors: "On Qwen3-8B, processing the proposals adds an average of 0.24 ms per decoding round in Transformers."; "The setup uses Qwen3-8B on an RTX 3090 with BF16 SDPA".
5. **CoPyro beats choosing one draft source by match length (Switch): CONFIRMED.** Against Switch, it improves overall acceptance length by 5.63–6.56% and throughput by 1.89–4.63%. Anchor: "Compared with Switch, CoPyro improves Overall acceptance length by 5.63–6.56% and throughput by 1.89–4.63%."

## 3. Reported results (as stated)

- **Main results, Table 1** (710K PerfectBlend, block 16, 5-layer drafters, Transformers batch 1, BF16, 994 requests per configuration):
  - DFlash+CoPyro overall τ / speedup over AR: Qwen3-4B T=0 5.45 / 3.58 (DFlash 5.38 / 3.55); Qwen3-4B T=1 4.90 / 3.02 (4.85 / 3.00); Qwen3-8B T=0 5.49 / 3.58 (5.40 / 3.54); Qwen3-8B T=1 4.78 / 2.93 (4.68 / 2.92).
  - Pure n-gram drafting reaches 1.19–1.29x AR.
  - Code benchmarks gain most: HumanEval +2.37–3.71%, LCB +1.43–6.64% acceptance length.
  - At T = 0, DFlash and CoPyro produce identical token sequences on all 994 requests.
  - The GPU type used for these main runs is not stated in the main text; the overhead protocol uses an RTX 3090.
- **Generality, Table 2** (Qwen3-4B-Instruct-100K, T = 0): DFlash 3.91 → 4.11, Domino 4.59 → 4.74, DSpark 4.47 → 4.57, DFlash2 4.69 → 4.83 overall τ.
- **Ablations, Table 3**: proposal only gives 4.06 (+3.79%); adding the length embedding gives 4.10; adding the agreement embedding gives 4.10; the full method gives 4.11.
- **SGLang v0.5.11, Qwen3-8B, concurrency 1–32**: +1.73% aggregate throughput, +3.15% acceptance length.
- **Mechanism, Table 5** (Qwen3-8B): k̄ is 3.93 for DFlash, 3.90 for CoPyro with masks, 4.12 for CoPyro with proposals. 96.75% of correct proposal tokens are kept, and 78.44% of incorrect ones are corrected.
- **Overhead**: 0.238 ms per round (RTX 3090, Transformers); 0.223–0.557 ms per batch round (SGLang).

## 4. Performance-principles table (mechanism and cost model)

**1. Online suffix-automaton retrieval of the longest suffix match.**
- MI210 gfx90a: YES. It runs on the host, as it would on any GPU host.
- Zen 5 EPYC: YES. It costs microseconds per token on the host (uncited).
- In-house: `ngram-mod` (`common/ngram-mod.cpp`, `common/speculative.cpp:2651-2812 @ a6a32c1`) is a hashed fixed-n lookup, not a longest-match suffix automaton. The match semantics differ (min length 1 vs n_min), so a port needs an SAM index. Port cost is small.

**2. Copied tokens replace masks in the block input, with no extra FLOPs.**
- MI210: YES. The drafter input is built at `common/speculative.cpp:1458-1460, 1760, 1978 @ a6a32c1` (`i == 0 ? dp.id_last : mask_token_id`). Swapping in proposal ids is a few lines, and block size and compute are unchanged.
- Zen 5: YES, same code. It matters only if a CPU-served DFlash2 role ever exists.

**3. Learned slot × bucket length and agreement embeddings.**
- MI210: PARTIAL. Needs new GGUF tensors (15×26×d), a converter entry and two `get_rows` plus add operations in the drafter graph. The added cost is negligible, but the tensors only exist after training.
- Zen 5: PARTIAL, same as the MI210.

**4. Training with zero-init tables and proposal dropout p = 0.2.**
- MI210: PARTIAL. DF2-FT-1 is the in-house drafter fine-tune lane. The block-16 pipeline is code-complete except for the GPU run (kernel-champion-and-promotion.md:197). Adding CoPyro inputs to that recipe is a data-pipeline change: proposals precomputed per anchor.
- Zen 5: NO for training compute (not a CPU job). The model-free smoke tests do run on CPU.

**5. Overhead cost model of 0.24 ms per round.**
- MI210: YES. Against about 44 ms per round for the 27B DFlash2 at np1 (design doc §5a: 44.3 ms per round), this is about 0.5% (inferred). Our C++ host lookup already exists for ngram-mod.
- Zen 5: YES. Negligible against a CPU decode step of about 93–97 ms (Q38FN, speculative-decoding.md DRAFT-HEAD row).

## 5. In-house state

- **No copy or n-gram speculation is served.**
  - The registry rule says "No n-gram composition: a role that speculates runs ONE drafter, never `ngram-mod,<drafter>`" (orchestration/model_registry.yaml L1731-1732 @ orchestrator 1a10541b, amended 2026-10-03).
  - The `ngram_candidate_spec_type` field was retired on 2026-07-31.
- **C19 carries COPYSPEC-WIDTH but does not serve it.**
  - C19 `a6a32c1` includes the per-implementation draft width `8b66aabc6`: ngram-mod n-max may exceed the draft n_max when `--spec-ngram-mod-n-max` is explicit (`common/speculative.cpp:3110-3126`), plus the speculative-simple fix-up `a6a32c1`.
  - It is reachable only if a launch adds `--spec-type ngram-mod,...`, which the registry forbids.
  - CPU evidence: cap 16 gave +13.09% with identity 65/65 (speculative-decoding.md:485-487 @ d785b6d).
- **27B GPU census matches CoPyro's Switch result.** COPYSPEC-27B: P (DFlash2) 59.32 tok/s, NM8 (ngram+DFlash2) 46.95, ngram-only 31.84 (speculative-decoding.md:492). Composing n-gram drafts with DFlash2 loses on the 27B MI210, the same direction as CoPyro's Switch baseline losing to DFlash. CoPyro's approach (input to the one drafter) does not hit the registry ban, because nothing extra is verified.
- **Our DFlash2 is block size 8**, from the z-lab weights (`dflash.block_size=8`), while CoPyro used block 16 (kernel-champion-and-promotion.md:196). Proposals can fill at most 7 slots.
- **The DF2-FT-1 KL re-alignment pilot is open** (speculative-decoding.md:2250). It is the only path that will retrain the served drafter.

## 6. Derived-actionables ledger

**A1. Training-free probe of copied tokens in place of masks.**
- Task: On an experimental branch from the current champion, behind a default-off env knob, feed ngram-mod (or SAM longest-match, min 1) proposals to the existing 27B DFlash2 drafter in place of mask ids, with no learned embeddings. Measure acceptance length against masks on code, RAG and prose prompts.
- Owner: speculative-decoding.md (INF-50). It exists and is not frozen. Per the operator's 2026-11-20 rule that sub-3% levers go to the AK loop, this could instead be seeded as an AK hypothesis in autokernel-loop.md.
- Compute: code, then one GPU row (27B Q8_0 + DFlash2, np1, ABBA, ~30 min).
- Stop rule: question = do untrained DFlash2 weights use or tolerate copied inputs? Pass if acceptance length is ≥ +1% on code with prose no worse than −0.5%; then the training-free variant is worth a throughput row. Otherwise close the training-free path, and CoPyro proceeds only inside A2.

**A2. Add CoPyro inputs as an arm of DF2-FT-1.**
- Task: In the DF2-FT-1 fine-tune recipe, add CoPyro's inputs as a second arm: proposals precomputed per anchor with the inference retrieval rule, zero-initialised 7×26×d tables for block 8, and proposal dropout 0.2. Gate it on τ and tok/s against the plain re-aligned drafter.
- Owner: speculative-decoding.md DF2-FT-1 (open; the integrator prepares and the owning session applies).
- Compute: training rides the DF2-FT-1 GPU budget, plus a converter/graph change and one serving A/B row.
- Stop rule: KEEP iff tok/s CI-lower > 1.0 against the plain re-aligned drafter at np1 and np4. DROP if τ gains less than 1% overall, the paper's strong-drafter floor.

**Decline.** Reviving n-gram composition (ngram-mod plus DFlash2) as CoPyro's comparison point is declined. COPYSPEC-27B already measured composition at 46.95 vs 59.32 tok/s on the 27B MI210, and the registry forbids it. CoPyro's own Switch baseline also loses to DFlash.

## 7. Dive-surfaced sources (grepped unbounded in the intake index)

- **SAM-Decoding** (Hu et al. 2025; suffix-automaton retrieval with a match-length switch). Not ingested; the arXiv id is not given in the page. It is the retrieval index CoPyro adopts and the basis of the Switch baseline, and it would settle the cost of a longest-match index versus our hashed ngram-mod. Recommendation: ingest-and-dive.
- **github.com/dt-3t/CoPyro**: code not yet released (404 on 2026-11-23). It would settle the exact bucket boundaries and the training-data pipeline. Recommendation: re-check later and ingest when it is published.
- **D-MTP project page** (github.io/D-MTP; Shen & Huang 2026, pretrained MTP for first-position prediction). Not ingested. It bears on A3B/Q38FN MTP drafting rather than CoPyro. Recommendation: decline for this run; the page names no arXiv id and the bearing is weak.
- **ReTrace** (Lin et al. 2026; conditions DFlash on the previous round's rejected suffix). Not ingested. It is a competing input-side DFlash change. Recommendation: ingest-and-dive, because it is training-light input conditioning on our drafter family.
- **Domino** (Huang et al. 2026) and **DDTree** (Ringel & Romano 2026) are already referenced in the intake index. **Contextual correction of parallel drafts** (2610.12570) is already ingested as intake-2561. **PARD** (2504.18583) is not ingested; decline it, since it is cited background only.

## 8. Contradiction / adversarial pass

- **The authors' own limitations (Appendix F):** one proposal source; modest gains over strong drafters, shrinking as the drafter gets stronger; benefits concentrated on code.
- **Contested baseline.** The headline 2.19–5.08% comes from drafters trained on only 100K samples. Against the stronger 710K DFlash, throughput gains are 0.39–1.33%, from a single timed run per configuration with no repeat-timing interval (Appendix D). That is near typical run-to-run noise. Our measured A/A range on the 27B GPU is 0.981–1.002, i.e. about ±1%, in the DTREE rows.
- **Not the served weights.** All drafters were retrained from scratch with the authors' recipe, not the released checkpoints. The DFlash2 result therefore does not describe the z-lab DFlash2 weights we serve.
- **Exactness.** At T = 0, CoPyro does not change the outputs (identical on 994 requests), so it is safe with respect to exactness.
- No independent reproduction found.

## 9. read_depth

FULL (main text, Tables 1–9, Appendices A–F). Figures not viewed as images. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## 10. Artifact audit

artifact audit: clean (page.txt 75,498 bytes, LaTeXML render of v1; all 11 anchors verified as substrings).
