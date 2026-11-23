# Dive — kobus — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2504.15475v1", retrieved: "2026-11-23", sha256: "a45bca19eef5"}

Bearing entry: intake-2831 (dice), low priority. Surfaced by the dice dive §7 as "Kobus & Gündüz 2025". Found by web search: arXiv 2504.15475. The page text read here is v1, titled "Speculative Decoding via Exponential Races"; the arXiv API and the ACL Anthology (Findings of ACL 2025, pp. 18189-18204, fetched on 2026-11-23) give the later title "Speculative Sampling via Exponential Races". Same paper.

## 1. Stage-1 fields
- **Title**: Speculative Decoding via Exponential Races (v1); published as "Speculative Sampling via Exponential Races"
- **Authors**: Szymon Kobus, Deniz Gündüz (Imperial College London)
- **Version**: v1, 21 Apr 2025, cs.CL; Findings of ACL 2025
- **Categories**: speculative_decoding
- **Novelty**: medium. Links speculative decoding to channel simulation; proposes ERSD (exponential-race speculative decoding) from the Poisson functional representation; derives a speed-up bound via Tunstall codes.
- **Relevance**: low. The dive's question was what it adds beyond DICE and Daliri. The answer is a null for our stack: ERSD does not beat the standard verifier on a chain, and its optimal-tree construction is the best-first expansion already used in the DTREE simulator.
- **credibility_score**: 4. Peer-reviewed, ACL Findings (+2); first posted Apr 2025 is 19 months old, so neither the recency bonus nor the age penalty (0); established information-theory author (+1); no commercial bias (0); independent corroboration +1 (Daliri et al. derive the same Gumbel race and a consistent ceiling). Total 4.
- **Verdict**: already_integrated. The decision-relevant technique (grow the tree by repeatedly adding the node with the highest acceptance probability, equal to the earlier Chen et al. 2025 algorithm under a 0-th order approximation) is in-house as probability-greedy best-first expansion in the DTREE simulator and server builder (§5). ERSD itself is not adopted because the paper shows it does not beat the standard verifier on single drafts or sequences.

## 2. Key claims
0. **ERSD with one draft token is the Gumbel-max coupling: CONFIRMED.** Draft and target each take the argmin of e_i/probability over shared exponential variables e_i; the paper notes this "is also known as the Gumbel-max trick". It is the same protocol as the Gumbel coupling in the Daliri entry; the verification step differs only in being written as a race. Anchor: §3 "This is also known as the Gumbel-max trick".
1. **ERSD's first-token acceptance is lower than the standard verifier's: CONFIRMED.** Lemma 3.1 puts it between the harmonic-mean distance and 1-D_TV. The text states that greedy (standard) decoding is optimal for single drafts at 1-D_TV, and that ERSD is "not inferior" overall only through entropy effects over many tokens. Anchors: §3 "greedy decoding achieves optimality within token-based speculation"; §3 "Despite a lower first-token acceptance probability, exponential races are not inferior to greedy decoding."
2. **Empirical ordering by drafting strategy: CONFIRMED.** Batch drafting: GSD above ERSD at k = 1, comparable at k = 2, ERSD higher for k >= 3, both plateauing just below 2 expected tokens. Sequence drafting: GSD superior. Optimal tree: GSD slightly ahead at low k, the gap closes as k grows. Anchors: §5 "For sequence drafting, GSD demonstrates superior performance compared to ERSD"; §5 "Both methods plateau just below" (batch drafting plateau).
3. **The optimal drafting tree is built by best-first expansion on acceptance probability, and the 0-th order Markov approximation of that probability underestimates the speed-up: CONFIRMED.** Algorithm 3 is a priority-queue loop in O(k log k). With an empirical acceptance estimate it reduces to Chen et al. 2025. The authors report empirical performance above the model's prediction and attribute it to higher-order dependence. Anchors: §4 "Algorithm 3 iteratively builds the tree by greedily adding the next most likely token to be accepted."; §5 "Intriguingly, our empirical results also challenge the 0-th order acceptance assumption".
4. **Setting is not stated for temperature or wall-clock: NOT-FOUND-IN-SOURCE.** No sampling temperature appears in the text; the metric is expected generated tokens per target evaluation, not time. The experiments use Llama-3.1-70B as target and Llama-3.2-1B as draft, 100k generated tokens per strategy, on 8 RTX A6000 GPUs for 140 wall-clock hours. Anchor: §5 "The experiments were performed on 8 Nvidia RTX A6000 GPUs".

## 3. Reported results
- Setup: open-ended generation up to 200 tokens, 100k tokens per strategy, Llama-3.1-70B target, Llama-3.2-1B draft, 8 RTX A6000, 140 h. Metric: expected number of generated tokens per target evaluation. Sampling temperature: none in source.
- Figure 3 and Figure 4 carry the curves (figure-only; values not read). In text: batch drafting plateau "just below 2"; ordering as in claim 2.
- Theory: speed-up upper bound as a function of drafted tokens via Tunstall-code analysis (Lemma 4.2, minimal bound over the parameter m); no numbers beyond the figures.

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| ERSD exponential race: one exponential per vocabulary entry, argmin of e_i/prob for draft and target | YES but pointless: it is an elementwise pass plus argmin, hashable from (seed, position, index). No gain over the standard verifier on chains. | YES, same, host-side over truncated candidates. |
| Batch drafting as the first k arrivals of the race (ERSD wins at k >= 3) | PARTIAL. Needs a multi-sibling tree verify; our tree path is greedy-only and unserved (T16 only at parity), so there is no consumer. | NO consumer: no CPU tree path is served. |
| Best-first tree growth by acceptance probability (Algorithm 3, O(k log k)) | YES, host-side; already in DTREE (§5). | YES, same. |
| Tunstall-code bound on speed-up vs drafted tokens | Analytic only; not a kernel. A calibration check, not a transferable mechanism. | Same. |

## 5. In-house state
- **Standard verifier = the paper's GSD.** The rejection path at common/sampling.cpp:1020-1128 @ a6a32c1 is the standard accept-with-ratio-then-residual scheme; DFlash2 supplies the draft distribution (common/speculative.cpp:1811-1829 @ a6a32c1). MTP and other drafters without distributions use sample-and-compare (common/sampling.cpp:659-710).
- **Best-first tree growth is in-house.** DTREE-TREE-QUALITY step (2) simulates probability-greedy expansion; on 27B the greedy W12 gives mean length 5.64 against static T12 5.32, and the server tree builder carries the winning greedy policy (speculative-decoding.md:1041-1052 @ d785b6d; KEEP_CANDIDATE G12 tok/s ratio 1.0266, CI [1.0100, 1.0432]).
- **Same under-prediction as the paper.** The same note records that the calibrated drafter probabilities under-predict the replay (5.35 against 5.82), a gap the paper attributes to ignoring higher-order dependence. This is consistent with, not proof of, that explanation.
- **Tree is greedy-only and not served**, so the batch regime where ERSD helps (k >= 3 siblings drawn from the draft distribution) has no consumer. The dice dive already declined DICE-tree on the same ground with the trigger "DTREE-GDN-BATCH makes T16 beat linear at T = 0".

## 6. Derived-actionables ledger
**K1. Refit the acceptance calibration with a path-conditional term (low priority hypothesis).**
- Task: In the DTREE simulator's calibration step, add a first-order term (acceptance at depth d conditional on acceptance at depth d-1) and report whether the calibrated mean length moves from 5.35 toward the replay value 5.82 on the same 545-round 27B capture.
- Owner: speculative-decoding.md DTREE-TREE-QUALITY note family (the box is ticked; a child row, or an autokernel-loop.md hypothesis under the operator's sub-3% rule).
- Compute: code-only, CPU seconds on the existing dump (`ak-dtree-dump-gpu-20261120`).
- Stop rule: question = does a first-order term close the calibration gap? If the calibrated prediction stays more than 5% under the replay, drop it; the deployed policy already ranks the same with raw and calibrated probabilities.

**Declines.**
- ERSD as a served verifier: declined. On single drafts and sequences, the shapes our served paths use, the paper reports the standard verifier at or above ERSD (Lemma 3.1 and §5). Re-evaluate only at the DTREE-GDN-BATCH trigger already recorded for DICE-tree.
- Building the paper's Tunstall-code speed-up bound into the simulator: declined; the replay simulator is already exact against the target stream (sim T16 5.62 against live 5.60), so a looser analytic bound adds nothing.

## 7. Dive-surfaced sources (grepped unbounded: 2504.15475 and "Kobus" hits only inside intake-2831's own notes)
- Chen et al. 2025 (empirical optimal tree under a 0-th order approximation): decline. Equals the best-first expansion already implemented; changes no ledger row.
- Li and Anantharam 2021 (Poisson matching lemma): decline. Theory; the bound in Lemma 3.1 is already usable from this paper.
- Daliri et al. (arXiv 2408.07978): already dived as a sibling in this wave.

## 8. Contradiction / adversarial pass
- Authors' stated limits: speed gains matter most for small k, where the standard verifier is usually the practical choice; joint sequence generation could help but its practicality is uncertain; the stateless approximation of the acceptance function oversimplifies language.
- The paper's own data show the 0-th order acceptance model is inaccurate, so its bounds are conservative.
- Single model pair, single hardware stack, figure-only numbers, no temperature stated.

## 9. read_depth
FULL for main text, Algorithms 1-3, Lemma 3.1 and the experiments; appendices B (proofs) and C (Tunstall codes) were not read beyond their headings; Figures 3-4 not viewed as images. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## 10. Artifact audit
artifact audit: clean (page.txt 64,401 chars from the arXiv v1 HTML render; anchor quotes verified as substrings; venue confirmed from the ACL Anthology page; nothing written inside any git repo).
