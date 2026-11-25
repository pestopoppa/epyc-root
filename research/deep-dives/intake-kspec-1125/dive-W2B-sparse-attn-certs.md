# W2B-sparse-attn-certs: certificates and bounds for top-k sparse attention

Entries covered (new, expanded_from intake-2970): intake-2980 (arXiv 2610.24991v1, Certified Sparse Attention via Perturbed Retrieval, source w03) and intake-2981 (arXiv 2512.07647v1, A Mathematical Theory of Top-k Sparse Attention via Total Variation Distance, source w04).

Read depth: both PARTIAL.
- w03 read: abstract, intro, related work, problem setup start, full Method (S4.1-4.5), Theory statements (Thm 1-4, Lemma 1, Prop 1), S6.1, S6.2, start of S6.3-6.5, S6.6, S7, S8, App A.9 (Prop 2), F.2-F.4. Unread: proofs A.1-A.8, App B (B.2 deterministic score bounds, B.6 negative results), App C, App D tables, F.1, F.5 beyond its first line.
- w04 read: abstract, S4.1-4.6, S5.1-5.5, S7, S8.1, S8.6-8.8, S9 with limitations. Unread: S2, S6 derivation (Gaussian tail law), S5.6 (max-spanning-tree diameter), proofs in the appendix.

## Short answers to the three questions

1. Cheap certificate from scores already in a decode step? Partly. w04 gives an EXACT identity: the output error of keeping a set is tau * ||mu_tail - mu_head||, and the distribution error is the discarded softmax mass tau (equivalently KL = -log(1 - tau)). The gap form (Thm 4.5) needs only the sorted logits around the boundary plus n. Inputs: the true attention logits of ALL n keys (for the exact mass), or s_k and an upper bound on every unscored key (for the gap form). So it is cheap only when the full score row already exists. Cost for exact tau: one dense score row plus one logsumexp, no extra forward. w03's certificate is NOT cheap in that sense: it needs a 4-bit scan of every key (16.4% of dense bytes, index +40% storage) and it certifies a sampling estimator, not a top-k set.
   - (a) DSA-style indexer top-k (Q38FN trunk indexer): the indexer selects blocks with its own head dimensions (`build_qsa_top_k`, `src/models/qwen4exp.cpp:L684-L720 @ 98ff8a4`), so its scores are not the attention logits. The bound must be evaluated on the MAIN attention logits of the dropped blocks. At run time that defeats the purpose (it needs dense scores). As an OFFLINE gate it is usable: dense reference pass on a calibration set, compute the attention mass the indexer's selected set misses, per layer/head/step. That is a direct diagnostic for why an approximate parallel top-k broke greedy identity (a different selected set, so a different discarded mass). It does not replace the exact-set test, because identity needs the same set, not a small tau.
   - (b) KV eviction/compaction gates: same story. tau is defined per query against the full cache, so it needs the full cache's scores for that query. Future queries are unknown, so it cannot certify an eviction decision made now; it can only be measured on a held-out query set. w03's guarantee is also per call with fresh perturbations, not a bound on eviction.
2. Agree or conflict with intake-2970? No conflict; they test different things. Details below.
3. Principle verdicts are in the table.

## Per-claim verdicts

### intake-2980 (w03)
| # | Claim | Verdict | Locator |
|---|---|---|---|
| 0 | Exp(1)-perturbed scores turn threshold retrieval into PPS sampling; HT estimate unbiased; per-head stopping certificate, Pr[certified and error > eps*M] <= delta | CONFIRMED (math as stated; Thm 1, 4) | S4.1-4.3, S5 |
| 1 | O(eps^-2 log 1/delta) values suffice, independent of n, at a threshold that needs D; adaptive rule reads 1.8-3.5x the keys of an uncertified CLT rule and 4.1-4.9x the oracle stopping level | CONFIRMED, with caveat: the n-independent count is for the unrealizable threshold tau = D/m; the practical rule reads more | S5 Thm 2, S6.6 |
| 2 | No certificate violated on 3 LLMs x 10 settings (16K-128K); p90 error 4.6-7.9x lower than the best of 15 baseline families at equal KEYS; at equal BYTES the best baseline has 0.6-1.6x our p90 and >=4.9x our max | CONFIRMED, but the equal-keys comparison hides the 16.4% byte floor; at equal bytes the headline flips for typical error. Captured KV/queries of 5 decode steps, not live generation | S6.2, abstract |
| 3 | Candidate generation reads every key (4-bit scan = 16.4% of dense bytes; index 720 vs 512 B/token); CPU only (Xeon 8555C, 8358); 1.1-1.4x faster whole steps vs the authors' own 16-bit dense kernel; no speedup with G=7 | CONFIRMED | S4.5, S6.5, S7, F.5 |
| 4 | Oracle top-k at the same keys: p90 0.068-0.109, PG-19 ppl +4.8-11.5%, CWE 27.8->12.0 (Llama); but strongest baselines at equal bytes match the method end to end | CONFIRMED; note the end-to-end win is over oracle top-k only, not over MagicPIG/RetroInfer/vAttention | S6.2, S6.4, S7 |

### intake-2981 (w04)
| # | Claim | Verdict | Locator |
|---|---|---|---|
| 0 | TV(P, P_topk) = discarded softmax mass = 1 - exp(-KL(P_topk||P)) exactly | CONFIRMED (Lemma 4.1, Thm 4.3); elementary, follows from renormalising a subset | S4.1-4.3 |
| 1 | Output error = tau*||mu_tail - mu_head||, <= tau*diam_HT <= 2C*tau, and <= sqrt(tau/(1-tau))*sqrt(Var_P(V)) | CONFIRMED (Thm 5.2, Prop 5.3-5.4, Thm 5.6); the diam and variance terms need value vectors of the whole cache | S5.2-5.5 |
| 2 | Gap certificate: Delta_k >= log((n-k)/k) + log((1-eps)/eps) implies TV <= eps; mass certificate from block lower/upper bounds; Delta-Search/MC-Search certify while scoring only some keys | CONFIRMED as math; practical cost depends on a cell index with per-cell score upper bounds that the paper assumes, never builds | S4.4-4.6, S7 |
| 3 | Empirics support the theory and give 2-4x fewer scored keys | PARTIAL: only bert-base-uncased (n~15 avg over 6,048 rows; WikiText-2 n=128-512) plus synthetic Gaussian logits to n=16384. Gap certificate passes on 1.79% (n~15) and 0% (n=128-512). Mass-certified k/n stays ~0.4 at eps=0.01, so required k grows linearly with n. The "speedup" is a count of scored keys n/k_mc, computed with the oracle sorted softmax, not wall-clock and not the search algorithms' cost | S8.1, S8.6-8.8 |
| 4 | Limits stated by the authors | CONFIRMED: Gaussian/sub-Gaussian priors, real heads heavier-tailed so certificates may be vacuous, no downstream accuracy measured | S9 |

Count: intake-2980: C 5 / P 0 / O 0 / NF 0. intake-2981: C 4 / P 1 / O 0 / NF 0.

## Adversarial pass
- No WebSearch run (not needed; both papers state their own limits). Cross-check inside the sources: w03 itself cites w04 ("top-k truncation has deterministic per-query bounds once all scores are known", Tzachristas et al. 2025) and argues those bounds need all scores, which is why it samples. That is a restatement of the dependency, not independent corroboration.
- w04's decisive weakness for us: no decoder LLM, no long context, no timing. Do not carry any "2-4x" figure to Q38FN or 27B.
- w03's decisive weakness for us: the certificate is on a sampling estimator with a full linear scan; a top-k kernel gets none of its guarantees. Its theory also does not cover closed-loop generation with fixed perturbations (S7).

## Relation to intake-2970 (joint support vs independent ranking)
- 2970 claim: independent Top-K over singleton-deletion KL is not the jointly optimal support; plain attention top-k does as well; SwapCert costs K(M-K) partial forwards.
- w04: ranking by the true attention score IS exactly optimal for the distribution-level error (tau is minimised by keeping the largest weights, Lemma 4.1). But the output error is tau*||mu_tail - mu_head||, which depends on where the values lie. So a mass-optimal set is not output-optimal, which is the same reason a joint support can differ from an independent ranking. Consistent with 2970, and it gives a cheaper first-order screen than SwapCert: compute tau and the head/tail value-mean gap from one dense pass, no K(M-K) forwards. It is first-order only (one layer's output, not downstream KL), so it is a screen, not a replacement.
- w03: shows oracle top-k (true scores, independent ranking) leaves a heavy error tail (p90 0.068-0.109) and large CWE loss, and fixes it by sampling, not by a better support. It neither tests nor contradicts joint-support optimality.
- Net: neither contradicts 2970; w04 explains it; w03 shows the same top-k tail problem from the other side. Neither paper does a joint-support search.

## In-house comparison (pinned)
- `handoffs/active/autokernel-akx-program.md:L1371 @ f19b902` Q38FN-INDEXER-TOPK-CPU: the approximate GGML_CPU_TOPK_PAR failed greedy identity at P32K/P64K (note at L1372); `...:L1373 @ f19b902` Q38FN-INDEXER-TOPK-EXACT fixed it by returning the exact serial set. The papers' tau is a poor tool here: identity needs the identical set. tau is useful to explain or bound HOW MUCH a changed set could matter, and to grade a future approximate (non-exact) indexer such as a block-pruned or lower-precision indexer.
- `handoffs/active/long-context-program.md:L616-L625 @ f19b902` (attention-matching KV compaction track, EA-POOL-SCREEN): the open question is scorer resolution vs eviction mechanics. tau on held-out queries is a direct, cheap per-layer metric to log beside the 60-item harness; it does not replace the task score (w04 says so itself).
- `handoffs/active/kv-cache-program.md` contains no eviction/compaction gate (grep `evict|compact|snapkv|h2o` returned nothing); its gates are fork/restore correctness. Nothing there to attach a TV gate to.
- Needle rows in long-context-program.md (e.g. L79, L120) are end-to-end checks; a TV gate would be a leading indicator only.

## Principles table
| principle | source evidence | MI210 (gfx90a) | EPYC Zen 5 | why (mechanism) | port cost |
|---|---|---|---|---|---|
| TV/KL identity for top-k truncation: error = discarded softmax mass; KL = -log(1 - tau) | w04 Lemma 4.1, Thm 4.3 | TRANSFERS-WITH-CHANGES (as offline/diagnostic gate) | TRANSFERS-WITH-CHANGES | exact math, hardware-free; needs the full score row, so only a gate, never a speed lever. A flash-attention kernel keeps a running max/sum over the keys it visits; the kept-set sum gives numerator, dense reference gives total | low: log per-head logsumexp of kept vs total in a debug build or a Python replay over captured logits |
| Output-error identity tau*||mu_tail - mu_head|| and diam/variance bounds | w04 Thm 5.2, Prop 5.3-5.4 | TRANSFERS-WITH-CHANGES | TRANSFERS-WITH-CHANGES | needs P-weighted value means over head and tail: one extra pass over V for the tail; usable offline on captured q/K/V | low-medium: analysis script on captured tensors; no kernel |
| Boundary-gap certificate Delta_k >= log((n-k)/k)+log((1-eps)/eps) | w04 Thm 4.5, S7.1 | DOES-NOT-TRANSFER for gating long-context decode | DOES-NOT-TRANSFER | the log((n-k)/k) term grows with n; passes on 1.79% of BERT rows and 0% at n=128-512; real heads are heavy-tailed so it is vacuous exactly where n is large | none (don't build) |
| Mass certificate with block upper/lower bounds (MC-Search) | w04 Thm 4.6 bound (4.4), S7.2 | UNKNOWN-NEEDS-PROBE | UNKNOWN-NEEDS-PROBE | valid math, needs per-block score bounds; our indexer already pools keys per block (`qwen4exp.cpp:L622+` per akx L1371), so block bounds may be nearly free; but no evidence at LLM scale and w04 reports k/n~0.4 at eps=0.01 on BERT | medium: needs a rigorous per-block bound (centre+radius), not just pooled-key score |
| Certified retrieval by perturbation (Exp(1) noise, PPS threshold sampling, HT estimate, anytime-valid stop) | w03 S4, Thm 1-4 | TRANSFERS-WITH-CHANGES, as a kernel change | TRANSFERS-WITH-CHANGES | unbiased and certified, removes the oracle-top-k tail, but reads every key via a 4-bit scan (16.4% of bytes); only 1.1-1.4x end to end on CPU vs the authors' dense kernel; 1.7-2.1x faster than llama.cpp CPU FA alone per their Table D.11c is for their kernel, not ours | high: new KV index (+40% bytes), per-head sequential levels, branchy; AVX-512 VNNI int8 scan fits Zen 5 well; on MI210 the scan is bandwidth-bound and sampled gather is divergent on wave64 (no GPU impl exists) |
| 4-bit scan with deterministic score upper bounds shared across a GQA group | w03 S4.4, B.2 (B.2 unread) | UNKNOWN-NEEDS-PROBE | TRANSFERS-WITH-CHANGES | exact candidate generation with rigorous bounds is the reusable piece: a scan that provably contains the top set. Could give a certified indexer, but our indexer is learned, not a bound on q.k | medium-high |
| Fresh per-step perturbations for validity in closed-loop generation | w03 S7, F.4 | UNKNOWN-NEEDS-PROBE | UNKNOWN-NEEDS-PROBE | determinism cost: output is bitwise reproducible only per CPU model and thread count (w03 F.4); our greedy-identity gates would need a fixed-seed plan, which w03 says Thm 4 does not cover | n/a until a kernel exists |
| As a GATE vs as a KERNEL change | both | gate: yes (offline); kernel: no near-term | gate: yes (offline); kernel: not now | the cheap, safe use is a recorded tau (and the value-mean gap) per layer/head on a calibration set as extra evidence next to greedy identity and task score; the kernel route costs a full scan and is CPU-only evidence | gate low; kernel high |

## Derived actionables
- KS-W2B-1: add an offline "attention mass captured" (tau, and tau*||mu_tail-mu_head||) diagnostic to the indexer top-k evidence for any future approximate or lower-precision indexer on Q38FN. Gate role only; exact-set identity stays the pass criterion. Owner: autokernel-akx-program.md (Q38FN-INDEXER-TOPK-CPU). Disposition: monitor (no approximate indexer is queued now).
- KS-W2B-2: log tau on held-out queries next to the EA-POOL-SCREEN task scores to separate scorer resolution from eviction mechanics. Owner: long-context-program.md (EA-POOL-SCREEN). Disposition: knowledge-only until the screen runs.
- KS-W2B-3: certified-sampling kernel (w03). Disposition: decline for now; reason: needs a full 4-bit scan, CPU-only evidence, 1.1-1.4x vs authors' own dense kernel, and our decode is already bandwidth-bound with a learned block indexer. Revisit only if we need a per-call guarantee.
- KS-W2B-4: first-order screen for intake-2970's joint-support question: use the head/tail value-mean gap from one dense pass before paying K(M-K) partial forwards. Owner: wherever 2970's actionables land. Disposition: knowledge-only.

## Dive-surfaced sources
- arXiv 2606.07205, "Towards Tight Bounds for Streaming Attention" (printed in w03 references as Chen et al. 2026a): lower bounds on summarising a KV cache; bears on eviction limits (intake-2980). Recommend decline (wave 2 is the last wave; theory-only).
- arXiv 2502.07861, "Streaming Attention Approximation via Discrepancy Theory": appears literally in w03 references; same bearing. Recommend decline.
