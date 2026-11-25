# S3-legospec-gramdelta: LEGOSpec / DFlux (intake-2965) and GramDelta (intake-2966)

Read depth: FULL for both (s10 55.5k chars, s11 89k chars). Lane head f19b902. Adversarial pass: 1 WebSearch per entry, nothing independent found.

## intake-2965 LEGOSpec / DFlux (arXiv 2611.33004v1)

| # | Claim | Verdict | Locator |
|---|---|---|---|
| 0 | 4-component split (Context/Backbone/Proposal/Objective), one trainer | CONFIRMED | Abstract, Sec V-A |
| 1 | DFlux +13.7% regular / +34.7% long acceptance | PARTIAL | Table III, Sec VI-B/C |
| 2 | Training throughput up to 79% (1.79x) over SpecForge | CONFIRMED | Sec VI-F |
| 3 | Batch-1 A3B TPS DFlux > DFlash2 | PARTIAL (true, scoped) | Table V |
| 4 | Compact SWA/GDN/MLA state shrinks draft cache | CONFIRMED | Table II, IV-B |

Counts: C 3, P 2, O 0, NF 0.

**Acceptance (claim 1).** 13.7% is GSM8K on the A3B (6.06 -> 6.89). It is not the regular maximum: Alpaca A3B is 3.45 -> 4.13 (+19.7%), LCB Qwen3-4B 4.30 -> 4.95 (+15.1%). 34.7% is SWE-bench on Qwen3-4B against DLite (3.03 -> 4.08), not against DFlash2 (2.96). On the A3B the long-context gain over DFlash2 is small (SD-QA +7.2%, L-ICL +2.7%, MD-QA +3.4%, SWE +9.9%). T=1, 5 seeds, 1,024 max tokens, block 8 (block 9 for the Qwen3-4B DFlash2 checkpoint).

**Where the gain comes from.** Three things are mixed:
1. Training scale. DFlux trains on 1.4M self-generated T=1 samples, 6 epochs, Muon, 16 H800. Baselines are released checkpoints of unknown data. The authors' own Fig. 1 says optimizer or data size changes can match a Markov head.
2. Matched 80K training (Table VII) shrinks regular gains to about 1.3-7.8% over DFlash2 (Qwen3.5-9B Alpaca 3.05 -> 3.09; Qwen3-4B GSM8K 5.61 -> 6.02).
3. Ablation (Table IV, Qwen3-4B): Regular 4.472 -> 4.618 (+3.3%), Long 2.450 -> 3.123 (+27.5%). The SWA-hybrid + conv backbone gives nearly all of Long (+24.5%, Regular +0.2%). R-Corrector adds +1.2% Regular. Hierarchical loss adds about +1.8% over Mix. The ablation base is GQA+RNN+Mix, not DFlash2. The nearest DFlash2 proxy is Selector+CE: R-Corrector+Mix beats it by 3.3% Regular / 4.0% Long (Table IV, row 4 vs row 3).

**Throughput (claim 3).** Alpaca 353 vs 298 TPS (+18.5%), GSM8K 602 vs 517 (+16.4%), MBPP 532 vs 500 (+6.4%) at batch 1. T=0, SGLang, authors' own DFlux port. GPU model for serving is NOT-FOUND-IN-SOURCE (H800 is training only). Not comparable to llama.cpp on MI210.

**Release.** Repo named as `SJTU-DAI-Sys/LEGOSpec` (link text, no URL); DFlux checkpoints: NOT-FOUND-IN-SOURCE. Same group released a DLite checkpoint (Table VIII), a weak prior only. Not fetched, per brief.

### In-house comparison
- Served drafter for 27B is `Qwen3.8-27B-DFlash2-Q8_0` from incoai (`handoffs/active/speculative-decoding.md:L1904 @ f19b902`, `:L2315`); z-lab card conformance is `:L2105`. The A3B is served with native MTP, not DFlash2 (`:L1049-L1052`, `:L522`).
- Drafter header facts: 5 non-causal blocks, sliding window 2048, headless, selector codebooks 2x256x248320 (`:L2401`). So the drafter already has SWA and a selector; the paper's SWA-512 hybrid is a delta, not new.
- We have never trained a drafter. DF2-FT-1 (KL re-alignment pilot) is DEFERRED by operator ruling 2026-11-24 until kernel roofline parity (`:L2401-L2403`). The narrow-draft retrain was priced at +0.4% to +5.4% (27B half width) and parked (`:L1049-L1052`). We consume upstream checkpoints (z-lab/incoai, DSpine tested and dropped, `:L2363-L2369`).
- So a training-recipe gain does not matter today. It matters only if DF2-FT-1 is un-deferred, and then as options for the recipe.
- C21 already has the building blocks: DFlash conv kernel and selector rank/top_k keys (`src/models/dflash.cpp:L141-L144 @ 98ff8a4`, `L397-L398`) and per-layer SWA graph (`src/models/dflash-dspark41.cpp:L164-L332 @ 98ff8a4`).

### Principles table

| Principle | Source evidence | MI210 (gfx90a) | EPYC Zen 5 | Why | Port cost |
|---|---|---|---|---|---|
| Hybrid SWA(512)x4 + 1 full GQA draft backbone with block-local conv | Table IV Long +24.5% / +14.6%, Regular ~0 | UNKNOWN-NEEDS-PROBE | DOES-NOT-TRANSFER (no served CPU DFlash2 drafter; A3B uses MTP) | Math is hardware-agnostic; value only at long context; our drafter is already window-2048 SWA | Low-moderate: layout + window key; conv exists |
| Residual Corrector (top-16 x top-16 correction, full-vocab logits) | Table IV +1.2% Regular vs RNN; 3.3% vs Selector+CE | TRANSFERS-WITH-CHANGES | DOES-NOT-TRANSFER | Parallel table, small GEMMs; variant of existing selector | Moderate; needs trained weights |
| Hierarchical loss KL(0.2)+D-PAL | Table IV +0.4% over D-PAL | ALREADY-PRESENT? no (training-only) | n/a | Training objective, no inference cost | Training only |
| Metadata-aware async draft training | 1.79x vs SpecForge | n/a | n/a | Training infra | Not applicable while deferred |

### Derived actionables
- KS-S3-legospec-gramdelta-1 monitor for a released DFlux checkpoint at a served target (speculative-decoding.md, DF2-CARD-CONFORMANCE-1 area).
- KS-S3-legospec-gramdelta-2 knowledge-only: record recipe options under DF2-FT-1 (`:L2401-L2403`).
- KS-S3-legospec-gramdelta-3 knowledge-only: port-cost note above.

Dive-surfaced sources: `SJTU-DAI-Sys/LEGOSpec` (decline for now), `incoai/Qwen3.6-35B-A3B-DFlash2` (decline).

## intake-2966 GramDelta (arXiv 2611.32807v1)

| # | Claim | Verdict | Locator |
|---|---|---|---|
| 0 | Incremental Earley state, delta-only propagation | CONFIRMED | Sec 3, App A |
| 1 | Update latency about 10x below best reconstruction baseline | PARTIAL (protocol-scoped) | Table 1, 10.9-11.3x vs Fresh |
| 2 | Removes most added TPOT overhead | PARTIAL (update handling, not mask cost) | Table 1, Table 6 |
| 3 | No overhead without updates; masks equal reconstruction | CONFIRMED | Table 5, Prop 2 |

Counts: C 2, P 2, O 0, NF 0 (llguidance version is NOT-FOUND-IN-SOURCE as a side fact).

**Table 1 check (BFCL, 8K prefix, K=32).** Qwen3-8B: unconstrained 19.645 ms/tok; XGrammar 124.953 (536.1%); llguidance 27.078 (37.8%), update 49.437 ms; Fresh 28.855 (46.9%), 42.066 ms; GramDelta 21.174 (7.8%), 3.817 ms. All numbers match the text. GramDelta adds 1.45-1.53 ms/token; reduction vs llguidance 67.6-81.9% (abstract's 53.1-81.9% spans CodeEvo too).

**(a) Update gain vs (b) steady state.**
- (a) The gain exists only because every baseline must rebuild its matcher and replay the 8K prefix on each first-seen update. Table 6: llguidance spends 23.0 ms construction + 20.7 ms replay per update; GramDelta 0 replay. The authors state this "is not a general characterization" of those systems (App C.2). Gain shrinks to 1.77x at 100% affected rows and reconstruction can win on broad-history updates (Sec 4.4).
- (b) Static (K=0, Table 5, 1K/4K prefix, Qwen3-8B): unconstrained 17.79/18.85; GramDelta 18.05/19.19; XGrammar 17.94/19.01; llguidance 18.03/19.09 ms/tok. All about 1-1.5% over unconstrained and indistinguishable from each other. Sec 4.4 itself says precompiled XGrammar and llguidance keep lower overhead in static or low-update regimes. No steady-state advantage for any backend.

**Baselines.** llguidance: "Guidance AI, 2025" repo, persistent ParserFactory, regex-lexer grammars, `no_forcing` path; version NOT-FOUND-IN-SOURCE. XGrammar and XGrammar-2 cited without versions; XGrammar-Cache is slower than uncached on first-seen grammars. Hardware: one RTX PRO 6000 Blackwell, BF16, 15-61 ms/tok, single prefill.

### In-house comparison
- No served role changes grammar mid-request. Orchestrator turn-1 grammar is built once from the tool registry (`src/graph/helpers.py:L1694-L1716`, read-only working tree), json_schema/grammar are plain per-request fields (`src/inference/model_server.py:L114-L115`), and edit_transaction uses no grammar (`src/edit_transaction.py:L50-L61`). Turn-1 grammar is off by default anyway (`handoffs/active/v11-promotion-checklist.md:L126-L127 @ f19b902`).
- llguidance flip (D2): flip `ORCHESTRATOR_GRAMMAR_LLGUIDANCE` ON at v11 promotion (`v11-promotion-checklist.md:L29-L31 @ f19b902`). Our evidence already decides it: SPEC-GRAM.3 PASS, grammar share 15% -> 0.15-0.25%, reject cost 26.4 -> 0.33 ms (`speculative-decoding.md` SPEC-GRAM.3 and SPEC-GRAM.4 declined note, L806-L810 region); V11-122-AB 0 greedy mismatches (`v11-promotion-checklist.md:L124-L125`). GramDelta adds nothing to this.
- Comparability: the paper's llguidance 4-55% TPOT overhead is a rebuild-and-replay artifact on a 15-61 ms/tok GPU decode; our 0.15-0.25% is steady-state mask cost on A3B CPU (step 24.86 ms, SPEC-GRAM.2 table, L773-L790 region). Not comparable. The only comparable number is the paper's static K=0 (about 1.3%), which is a weak, independent consistency check that static llguidance cost is small (different grammars, GPU, unstated version).
- SPEC-GRAM-JSON-1 (`speculative-decoding.md` ~L942) is about forced-token share offline replay; GramDelta does not touch it.

### Principles table

| Principle | Source evidence | MI210 | EPYC Zen 5 | Why | Port cost |
|---|---|---|---|---|---|
| Delta-only Earley update, no prefix replay | Table 1/6 | DOES-NOT-TRANSFER (CPU mask logic, hardware-agnostic) | DOES-NOT-TRANSFER to current traffic | Needs mid-request grammar growth; we have none | Large (new matcher, not in llguidance) |
| Factorized token projection (vocab bitsets + shared-history trie) | Table 2 ablation | n/a | UNKNOWN-NEEDS-PROBE (relevant only to wide-string masks) | llguidance already uses derivative lexer + trie | Not worth it |
| Static mask cost is about 1% regardless of backend | Table 5 | ALREADY-PRESENT (our SPEC-GRAM.3 measurement) | ALREADY-PRESENT | Forward pass dominates | n/a |

### Derived actionables
- KS-S3-legospec-gramdelta-4 knowledge-only: one-line note, no change to D2 or SPEC-GRAM-JSON-1.
- KS-S3-legospec-gramdelta-5 monitor: re-open only if a role starts progressive schema/tool discovery inside one request.

Dive-surfaced sources: arXiv:2607.18357 Decode-time grammars (decline), XGrammar-2 (decline).
