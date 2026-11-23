# Dive — samdecoding — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2411.10666v3", retrieved: "2026-11-23", sha256: "75d91f1fcafd"}

Bearing entry: intake-2832 (copyro). Surfaced by the copyro dive §7 ("SAM-Decoding (Hu et al. 2025; ...)"). The paper is arXiv 2411.10666, found by web search; the abs-page title from the arXiv API, "SAM Decoding: Speculative Decoding via Suffix Automaton", matches. Note the paper is dated 2024 (first posted 16 Nov 2024, v3 16 Dec 2024), not 2025 as the bearing dive wrote.

## 1. Stage-1 fields
- **Title**: SAM Decoding: Speculative Decoding via Suffix Automaton
- **Authors**: Yuxuan Hu, Ke Wang, Xiaokang Zhang, Fanjin Zhang, Cuiping Li, Hong Chen, Jing Zhang (Renmin University of China; Tsinghua affiliation for one author)
- **Version**: v3, 16 Dec 2024, cs.CL. Code is "available at our repository" (no URL in the page text; not read).
- **Categories**: speculative_decoding, retrieval_augmented_decoding
- **Novelty**: medium. Suffix automata for exact longest-suffix retrieval with O(1) amortised update, a static (corpus) plus dynamic (current text) pair, and a match-length rule for choosing between retrieval and an auxiliary drafter.
- **Relevance**: low-medium. It supplies the retrieval index and switch rule that CoPyro's proposals and Switch baseline build on, but every number is greedy, batch 1, Vicuna-7B on an A6000, and our measured composition of n-gram with DFlash2 lost on the 27B (§5).
- **credibility_score**: 0. No venue shown on the page (0); latest version Dec 2024 is 23 months old, first posting 24 months and a week old, so I use the latest version and give 0, not -1, and flag it; university group, not a major lab (0); no commercial bias (0); no independent corroboration of the numbers (0). Total 0.
- **Verdict**: worth_investigating. The component is cheap and standard, but the one question that decides whether it matters to us (how much copy coverage our traffic has at short match lengths) is answerable offline from archived outputs (§6 S1), and nothing in the paper answers it.

## 2. Key claims
0. **Retrieval index: CONFIRMED.**
   - Two suffix automata. A static one is built offline over a concatenated corpus with EOS separators. A dynamic one is extended online over prompt plus generated tokens. Each node stores `min_endpos`, the earliest end position of its substrings, so the draft is the next n tokens after the earliest occurrence of the longest matched suffix.
   - The static automaton also keeps frequency-ranked top-k successors per state and drafts a tree with Prim's algorithm over successor probabilities (Appendix A.2).
   - Anchors: §3.1 "we record the earliest position of all substrings corresponding to that node in the reference string, termed as min_endpos"; §3.1 "we construct a tree-structured draft by Prim’s algorithm based on top-k successors".
1. **Switch rule: CONFIRMED.** Prefer the dynamic automaton; use the static draft only if the static match length exceeds the dynamic match length by more than l_bias. When combined with an auxiliary drafter (Token Recycling or EAGLE-2), the auxiliary is used unless the retrieval match length exceeds a fixed virtual threshold l_threshold. Both are 5 (l_bias is 0 with no auxiliary). The authors call it heuristic. Anchors: §3.2 "We use the draft from the static automaton only if"; §3.4 "For the auxiliary SD method, we set a fixed virtual match length"; §7 "we use a very heuristic approach, i.e., we choose different methods depending on the match length".
2. **Speed claims against the baselines: PARTIAL (narrowed).**
   - Vicuna-7B-v1.3, greedy, batch 1, fp16, one A6000: SAM-Decoding 2.30 mean accepted tokens, 69.37 tok/s, 1.84x on Spec-Bench, against PLD 1.75 / 59.02 / 1.56x. By my arithmetic that is +17.5% in tok/s and +17.9% in speedup ratio over PLD, so the abstract's "18%+" holds only on the rounded ratio.
   - Against EAGLE-2 (Table 1, tok/s): +8.2% on Spec-Bench (97.56 vs 90.14), +3.6% on HumanEval (130.28 vs 125.77), +16.9% on HAGRID (96.60 vs 82.61). The abstract's "3.28%-11.13%" is for MT-Bench across backbones (figure-only), and the HAGRID value falls outside it.
   - Anchors: §4 "SAM-Decoding 2.30 69.37 1.84"; §4 "PLD 1.75 59.02 1.56"; abstract "when combined with advanced EAGLE-2, it provides an additional speedup of"; §4 "we used the float16 data type and applied greedy decoding with a batch size of 1".
3. **Where the gain comes from: CONFIRMED, with a corpus caveat.** In the SAM-Decoding[T] run on Spec-Bench, 85.96% of rounds used the auxiliary drafter (mean accepted 2.51), 11.59% the dynamic automaton (6.57) and 2.45% the static one (3.39). The usage-weighted mean is 3.00 by my arithmetic, against the 3.03 table value, so the breakdown is self-consistent; by the same arithmetic the dynamic automaton supplies about a quarter of accepted tokens from about a ninth of rounds. Removing the static automaton costs 10.7% of tok/s (1.84x to 1.64x), removing the dynamic one 27% (to 1.33x). The static corpus is Vicuna-7B's own generations on Stanford-alpaca, python-code-instruction-18k and GSM8K, and Spec-Bench contains a GSM8K split; the authors concede the corpus "may deviate from the text generated by other LLMs". Anchors: Appendix C "in 85.96% of the cases, due to insufficient matching length, we generate drafts based on the auxiliary method, corresponding to an average accept length of 2.51"; Table 2 "w/o Static SAM 1.85 61.93 1.64"; §4 "we constructed a static suffix automaton based on the Vicuna-7B generation results on datasets Stanford-alpaca, python-code-instruction-18k, and GSK8k".
4. **Cost: CONFIRMED.** State transfer is O(1) amortised (energy argument, Appendix A.3), worst case O(L); PLD is O(n^2 L) and REST O(n^2 log L). Draft generation is 0.6% of the SAM-Decoding[T] cycle (decoding 65.4%, verification 23.4%, update 6.3%, prefill 4.2%). Anchor: Appendix C "the draft generation stage contributes only 0.6% to the overall duration".

## 3. Reported results
- Hardware and setup: 20-core CPU, one RTX A6000 48 GB, PyTorch 2.3.0, Transformers 4.46.1, CUDA 12.1; fp16, greedy decoding, batch 1; Vicuna-7B-v1.3 main table, Llama3-8B-Instruct, Vicuna-13B and -33B in Appendix B; one A800 table (Table 9, values not captured in the page text).
- Table 1 (Vicuna-7B, mean accepted tokens / tok/s / speedup): Spec-Bench SAM-Decoding 2.30 / 69.37 / 1.84x, SAM-Decoding[T] 3.03 / 85.73 / 2.27x, SAM-Decoding[E2] 4.62 / 97.56 / 2.58x; HumanEval 2.64 / 88.91 / 2.29x, 2.94 / 95.08 / 2.45x, 4.95 / 130.28 / 3.35x; HAGRID 2.44 / 76.72 / 2.24x, 3.23 / 87.93 / 2.57x, 4.75 / 96.60 / 2.81x. Baselines on Spec-Bench: PLD 1.75 / 59.02 / 1.56x, Token Recycling 2.83 / 69.65 / 1.84x, EAGLE-2 4.36 / 90.14 / 2.38x.
- Ablations: l_bias and l_threshold both peak at 5 (figure-only); draft size peaks at 40 (16 used for code); Table 2 above.
- No sampled-mode, no batch > 1, no model above 33B, no block drafter.

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Suffix-automaton longest-match retrieval (O(1) amortised transfer, min_endpos copy of the next n tokens) | YES. Pure host work per round; the 27B DFlash2 round is about 44 ms at np1 (per the copyro dive), so a sub-millisecond index is invisible; the unknown is coverage, not cost. | YES. The same host code; the CPU-served MTP rounds are also tens of ms. Memory: states are up to about 2L with transition maps (uncited estimate: tens of MB at 100k tokens). |
| Static corpus automaton plus top-k successor tree draft (Prim) | PARTIAL. The tree draft needs a tree verify, which the served DFlash2 chain does not use; the static corpus would be our own prior outputs. | PARTIAL for the same reason; CPU tree verify not served. |
| Match-length-gated choice between retrieval and a model drafter | YES as a policy; but a hard switch removes the model's draft for that round, and the measured composition on the 27B lost (§5). | Same. |
| Longest-match (no fixed n) versus fixed-n hashed lookup | YES. This is the one structural difference from `ngram-mod`; short matches become usable, with a match-length feature available to a downstream consumer such as CoPyro. | Same. |

## 5. In-house state
- **The cited line range is not the index.** `common/speculative.cpp:3110-3126 @ a6a32c1` (quoted in the copyro dive) is the n_max accumulation for `NGRAM_MOD` and the per-impl width helper `common_speculative_ngram_mod_width` (COPYSPEC-WIDTH). The ngram-mod implementation is `common/speculative.cpp:2651-2812` plus `common/ngram-mod.h` and `ngram-mod.cpp`.
- **`ngram-mod` is not an equivalent index.**
  - Key: a hash of a fixed n-token window (`n_match` default 24; `n_max` 64 and `n_min` 48 by default, common/common.h:359-363 @ a6a32c1). SAM keeps the longest suffix of any length.
  - Storage: one int32 successor per bucket in a 4M-entry table, last write wins, and lookup returns the bucket without verifying the key (ngram-mod.cpp add/get), so collisions give false hits. SAM is exact.
  - Continuation: one token per step by sliding the window over the previous drafted tokens, so a draft can splice different earlier occurrences. SAM copies a contiguous span from the earliest occurrence.
  - Source: prompt plus generated tokens of the sequence, in a table "shared across all sequences" (speculative.cpp:2655), reset when occupancy exceeds 0.25 at `begin()` and after five rounds below 0.25 acceptance (speculative.cpp:2690-2720, 2790-2815). There is no separate static corpus; the `ngram-cache` implementation (speculative.cpp:2830-2960) has static, dynamic and context tables, but with n at most 4 (`LLAMA_NGRAM_MAX 4`) and frequency counts, loaded from files, and is not a longest-match structure.
  - Switch: speculators run in a fixed priority list (speculative.cpp:3306-3340) and the first one that returns a non-empty draft wins the round (loop at speculative.cpp:3532-3600), with a per-impl cap (:3551-3553). The effective rule is "24-token window hit and at least 48 chained successors", not an adaptive match-length threshold (launch flags may override n_min and the cap; not read).
- **Served path does not reach it.** The registry forbids composition ("a role that speculates runs ONE drafter, never ngram-mod,<drafter>", orchestration/model_registry.yaml L1731-1732 @ orchestrator 1a10541b, as quoted in the copyro dive). C19 carries COPYSPEC-WIDTH but nothing serves it.
- **Measured composition on the served pair.** COPYSPEC-27B, 27B Q8_0 on the MI210: P (DFlash2) 59.32 tok/s, NM8 (ngram plus DFlash2) 46.95, ngram-only 31.84 (speculative-decoding.md:492 @ d785b6d); 46.95 against 59.32 is -20.9% by my arithmetic. The earlier CPU phase-1 on the MTP model shows the other side: the ngram-only control arm drafted 4,535 tokens on 60 of 85 requests at acceptance 0.912 (the MTP-only arm drafted 16,506 tokens at 0.716), and ngram plus MTP changed throughput by +3.22% against a 0.22% noise floor (artifacts/copyspec-20261006/p1-summary.md @ d785b6d).
- **Corpus for the offline probe exists.** `artifacts/copyspec-20261006/source-archive/results/P.jsonl` holds 85 requests with generated `text` (plus `prompts_p1.jsonl`) @ d785b6d. The 27B census results path recorded at speculative-decoding.md:496 did not resolve from this session on 2026-11-23.

## 6. Derived-actionables ledger
**S1. Offline match-length coverage curve on archived outputs (refines intake-2832 A1; gates A1 and A2).**
- Task: Run an exact longest-suffix-match index (Algorithm 1 of the paper, any language) over the archived COPYSPEC P1 request streams (`source-archive/results/P.jsonl` generated text after tokenising with the target tokenizer, prompt included in the history) and tabulate, per position, the longest suffix match length l and how many of the next 1 to 7 tokens of the earliest-match continuation equal the realised tokens. Report coverage (share of positions with l at least 1, 3, 5, 8 and 24), the mean agreed prefix at each l, and a leave-one-request-out variant that builds the index from the other requests, by class (code, RAG, prose).
- Owner: speculative-decoding.md (INF-50 row family for the CoPyro probe; exists, not frozen). The owning session applies.
- Compute: code-only, CPU seconds, no model load (tokenisation only).
- Stop/decision rule: question = is there enough copy coverage for copy proposals to matter to a DFlash2 input or a gated switch? Predeclared: if positions with l at least 5 and at least 3 agreed tokens are under 5% of tokens on code and under 2% on prose, close intake-2832 A1 and A2 and the gated-switch idea; otherwise A1 proceeds with the match-length buckets read from this table. A higher coverage with mean agreed prefix near or above the DFlash2 mean accepted length (about 5) is the case where a gated switch could reverse the 27B composition loss.

**S2. Host longest-match index as the input source for intake-2832 A1 (prerequisite; only if S1 passes).**
- Task: Implement an exact suffix-automaton or equivalent longest-match index behind a default-off knob in the experimental branch, exposing for each position the proposal span and the match length, and use it, not `ngram-mod`, as the source of copy proposals for A1.
- Owner: speculative-decoding.md (same family as S1).
- Compute: code, then the single A1 GPU row already specified in the copyro ledger. Port estimate is small (uncited: on the order of 150 lines for Algorithm 1 plus the update step).
- Stop rule: a unit test against a brute-force longest-suffix search on random token streams (100% agreement) before any GPU time. Reason `ngram-mod` cannot stand in: its default window of 24 gives no short matches and its hashed lookup is not exact.

**Declines.**
- Serving SAM-Decoding standalone or reviving n-gram composition with DFlash2: declined on the measured 27B result (46.95 vs 59.32 tok/s) and the registry rule; S1 reopens the question only through the gated-switch case above.
- Building a static corpus from our outputs: declined as a separate build; the leave-one-request-out variant in S1 measures cross-request value first, and no served path could use a static corpus today.

## 7. Dive-surfaced sources (grepped unbounded: arXiv 2411.10666, "SAM Decoding" and "suffix automaton" in the intake index)
- The index mentions "SAM-Decoding" only inside the intake-2832 notes; the paper itself is not ingested.
- SAM-Decoding code repository: decline. The algorithm is fully stated; no ledger row needs its hyperparameters beyond l = 5.
- Token Recycling (Luo et al. 2024), PLD, REST, PIA, Lookahead: decline. Baselines; no row depends on them.

## 8. Contradiction / adversarial pass
- Authors' stated limits (§7): performance depends on task type and corpus quality; the corpus is Vicuna-7B-generated and may deviate from other models; the match-length switch is heuristic; datasets do not reflect real retrieval workloads.
- Contested baselines: baselines marked * were taken from their own environments (Table 1 footnote), not re-run in one harness.
- Greedy only: no evidence about sampled decoding. The corpus-overlap issue (GSM8K in both corpus and benchmark) can inflate the static automaton's contribution (10.7% of tok/s).
- Restatement: CoPyro (intake-2832) reuses the same index idea and a SAM-style Switch baseline, but does not re-measure SAM-Decoding's numbers; it is not corroboration.

## 9. read_depth
FULL for main text, Tables 1-2, Appendix A.2, A.3, B and C narrative; Algorithm 2-3 construction details (A.1) skimmed; figures and Tables 3-9 numbers not read (figure-only or not captured); repository not read. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## 10. Artifact audit
artifact audit: clean (page.txt 63,371 chars from the arXiv v3 HTML render; anchor quotes verified as substrings; all derived percentages are my arithmetic from the stated table values and are labelled; nothing written inside any git repo).
