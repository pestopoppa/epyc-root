# Dive — futurevalid — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2605.07698v1", retrieved: "2026-11-24", sha256: "55ab8773a0fa"}

Stage 2b wave 1 light dive. Bearing entry: grammardraft (intake-2873), ledger A2 and D2. The bearing entry's draft cites this arXiv id inside its own record only; there is no standalone entry for it.

## 1. Stage-1 fields

- title: Future Validity is the Missing Statistic: From Impossibility to Phi-Estimation for Grammar-Faithful Speculative Decoding
- authors: Wenhua Nie, Zijie Meng, Kun Zou, Zheng Lin, Ziwei Li, Haoran Zheng, Jyh-Shing Roger Jang, Hao Zhang
- version/date: arXiv 2605.07698v1, 08 May 2026
- categories: speculative_decoding, inference_serving
- novelty: medium. The masked-sampling bias is the known GAD result (Park et al. 2024); new here is the speculative-decoding formalization and the Phi-correction measurements.
- relevance: medium-low. It fixes what "lossless under a grammar" means for our verifier and shows the gap is a property of masked sampling, not of speculation. It does not change A2's design.
- credibility_score: 2. +1 (<=12 months); +1 independent corroboration of the phenomenon (GAD, NeurIPS 2024, cited by the paper and not read here); +0 not peer-reviewed; +0 known lab. All fidelity claims are scoped by the authors to enumerable grammars.
- verdict: worth_investigating (low priority): one offline measurement on our enum-style schemas (ledger F1). Otherwise adopt_patterns for the reference-distribution definition.

## 2. Key claims

0. **Any speculative decoder with local mask access, Leviathan rejection and rollback soundness samples the locally projected distribution, not the grammar-conditional one (CONFIRMED; a corollary, not a new rejection-sampling theorem).** The authors state the contribution is a negative characterization: adding a mask does not make Leviathan's target the grammar-conditional law. Anchors: page, abstract, "any speculative decoder with local mask access, Leviathan rejection, and rollback soundness samples from the locally projected distribution"; section 3, Prop 3, "adding a grammar mask does not make the target the grammar-conditional law".
1. **The gap can be near-total on adversarial recursive grammars: TV up to 0.996 (Qwen3-8B, Dyck D3,16, 5,000 samples, temperature 1) (CONFIRMED, not representative).** The witness has Phi_root about 1e-7, i.e. the model almost never produces valid strings unmasked. Anchors: page, abstract, "the total-variation gap can reach 0.996"; section 3 Witness, "(5,000 samples, temperature 1)".
2. **On real finite JSON languages the gap is 0.174-0.681 TV on Qwen3-8B (CONFIRMED, small enumerations).** Table 15: schemas of 3, 4, 18, 24 and 2,000 canonical strings: TV 0.188, 0.421, 0.174, 0.681, 0.244. Example: for a 3-string status schema the masked sampler emits "error" 27% vs 8% under the grammar-conditional law. Free-text fields and arbitrary whitespace are NOT covered (the open-xgrammar run is "an implementation smoke test"). Task accuracy is not measured. Anchor: page, section H.8, "The local-projection gap ranges from 0.174 to 0.681 TV on Qwen3-8B".
3. **The bias vanishes when Phi is constant over locally valid tokens (CONFIRMED).** "This often holds for simple regex constraints and permissive schemas, but it fails for recursive or concentrated schemas". Anchor: page, section 7, that quoted sentence.
4. **Speculative decoding itself preserves the masked distribution; correction is cheap only where Phi is precomputable (CONFIRMED, with a NEGATIVE for the cheap estimator).** Cost model: SD is 4.8x faster than AR yet "preserves the same local-projection distribution"; exact DP reduces Dyck TV 97% at no runtime cost. With the real DFlash drafter and exact finite-trie Phi, terminal TV falls from mean 0.350 to 0.017 on four schemas while throughput moves 91.7 to 81.1 tok/s (-11.6%, dive arithmetic). The one-token OneStep estimator can WORSEN concentrated JSON (0.622 vs 0.575, 0.843 vs 0.820, 0.878 vs 0.847 in Table 3). Anchors: page, section 6.5, "Standard speculative decoding is about 4.8 x faster than AR in this setting but preserves the same local-projection distribution"; section 6.4, "OneStep can worsen concentrated JSON schemas".
5. **Temperature scope (NOT-FOUND-IN-SOURCE for T below 1).** The only stated sampling temperature is 1; "broader temperature effects remain future work". Our vendor temperatures (27B T1.0, 35B T0.7, operator-given) are covered at 1.0 only by the Dyck witness. Anchor: page, section 7, "broader temperature effects remain future work".

## 3. Reported results

- Qwen3-8B (and a Qwen3-8B-DFlash-b16 drafter for the pilot); Dyck D3,12 / D3,16; finite canonical JSON languages (3-24 strings, one 2,000-string); hardware not needed for the TV calculations (exact terminal-law, no sampling noise).
- Table 3: TV(proj, star) JSON status 0.575, action 0.820, method-path 0.847, Dyck D3,12 0.456, D3,16 0.418; exact-Phi TV below 0.001, 0.097, 0.601, 0.018, 0.014 (method-path exact is high from sample variance with Phi-bar 0.066).
- Table 4 cost model (35 ms verify, 5 ms draft, 3.07 accepted/round): AR 16.0 tok/s; SD 76.8 tok/s TV 0.418; SD + OneStep-Cheap 76.2 tok/s TV 0.359; exact DP 76.8 tok/s TV 0.014.
- Table 14 DFlash finite-trie pilot: mean TV 0.350 to 0.017 (95% pooled), 91.7 to 81.1 tok/s; the "error" branch emitted 26.8% vs 8.8% under the grammar-conditional law, 7.9% after correction.
- Learned Phi on external schemas: mean TV 0.510 to 0.498 (2 seeds) and 0.547 to 0.525 (3 seeds); modest.
- Equality verifier note: an "accept if equal to an independent target sample, else resample fresh" kernel has marginal p_i(1+q_i-<p,q>), amplifying draft-favored tokens.

## 4. Performance-principles table (mechanism and cost model)

| Principle | MI210 gfx90a (27B DFlash2 / trees) | Zen 5 EPYC (A3B MTP, CPU) |
|---|---|---|
| Local masking + Leviathan = masked-AR distribution (bias is of masking, not of speculation) | YES: our verifier builds the target after all constraints (`common/sampling.cpp:1038-1107`, `grammar_first=true` at :1047 @ 98ff8a4), so it samples exactly the masked distribution a non-speculative masked sampler would | YES: the sample-and-compare branch (`sampling.cpp:699-713` @ 98ff8a4) pushes the target's OWN sample as the committed token on both accept and mismatch, so the marginal is exactly the masked target p, not the biased equality kernel |
| Phi-correction via future-validity reweighting | PARTIAL: needs per-prefix Phi; exact only for enumerable grammars/tries; OneStep unreliable on concentrated schemas. Runtime cost measured -11.6% tok/s with the real DFlash path | PARTIAL: same Phi; the host-side DP is offline-precomputable for finite enum schemas |
| Accept-with-probability-1 for single-allowed-token positions | YES lossless: mask admits one token so masked p=1 there, matching grammardraft A2 part (3) | YES, same |
| Accept-with-probability-1 for multi-tokenization forced strings (D2) | Stays declined: it deviates from the masked target (it is not even defined by Phi) | same |

## 5. In-house state

- Served behaviour is exactly the paper's LMS class: grammar applied per verify row (bearing dive section 5: `common/sampling.cpp:616-658`, :660-741, :1038-1107 @ 98ff8a4). So our output distribution equals masked autoregressive sampling and is "biased" vs the grammar-conditional law by exactly the amount masked sampling itself is; speculation adds none.
- The sample-and-compare verify emits the same sample that failed the comparison (`sampling.cpp:699-713 @ 98ff8a4`: `result.push_back(id)` before `if (draft[i] != id) break`), so the equality-kernel bias in the paper's note (fresh resample on mismatch) does not occur in-house.
- Grammar-constrained production traffic is JSON-schema and typed-decision traffic (bearing dive section 5; orchestrator `src/typed_decisions/runner.py:231` per that dive). Their enumerations are the kind Table 15 measured (a few valid strings). The gap on OUR schemas is unmeasured.
- Phi-correction machinery: none in-house (no Phi anywhere; llguidance wrapper only consumes tokens and computes masks).

## 6. Derived-actionables ledger

| # | Task line | Owner (lane) | Compute | Stop / decision rule |
|---|---|---|---|---|
| F1 | For each production enum-style json_schema class (typed-decision runner, review abbreviations, plan steps), enumerate the finite canonical token trie, query the served model at every trie prefix at the served temperature, and compute exact TV between the masked-AR law and the grammar-conditional law (Table 15 method) | `speculative-decoding.md` SPEC-GRAM section (exists, not frozen); alternative owner `eval-tower-program.md` | offline script plus prefix forward passes only (small CPU or GPU run, no serving load) | Question: does any production schema have TV >= 0.1 between masked and grammar-conditional sampling. Stop-on-answer: every class under 0.1 closes it (masked sampling stays the target); any class >= 0.1 opens a design box on whether a Phi correction (finite-trie DP, offline) is worth its measured -11.6% tok/s. Note the paper covers T=1 only |
| F2 (refines grammardraft A2 part 2/3) | State in the A2 design that the acceptance target for any forced-token draft is the masked-AR distribution (what the verifier already samples), and that logit-free accept applies only where the mask admits exactly one token | `speculative-decoding.md` | doc-only | Done when the A2 text names the target; no compute |

Declines:
- Decline: implementing OneStep or any Phi estimator inside the verifier. Specific reason: the paper's own Table 3 shows OneStep worsening three of the JSON schemas it tested (TV up to 0.878), and exact Phi exists only for enumerable tries; F1 decides whether even the exact version matters here.
- Decline: changing D2 (accept-with-p-1 for multi-tokenization spans stays declined). Specific reason: this paper does not touch tokenization; a forced span with several allowed tokens departs from the masked target regardless of Phi.

## 7. Dive-surfaced sources

Index grepped unbounded: `2605.07698` appears only as text inside the grammardraft record (no standalone entry); `2603.05540` (Alpay and Senturk) 0 hits; `2403.06988` 0 hits.
- Alpay and Senturk arXiv 2603.05540 (one-step KL/TV bounds, same Doob view): would not change F1 or F2. Decline.
- GAD (Park et al. 2024) and DOMINO: no ledger row here depends on them. Decline.

## 8. Contradiction / adversarial pass

- The 0.996 TV is on a recursive grammar where the model puts about 1e-7 mass on valid strings; the paper's own JSON numbers (0.17-0.68) come from 3-24-string enumerations and one 2,000-string language. Neither is a free-text schema; the open-xgrammar run is a smoke test only.
- No task accuracy or downstream benchmark is measured; the "functional reading" is branch frequency of one status field.
- Learned Phi gains are modest (TV 0.547 to 0.525) and finite-trie only; the generalization claim is not established.
- Temperature: only 1 is reported; behaviour at 0.7 is open (authors).
- Exact Phi is #P-hard for general CFGs (authors).

## 9. Read depth

read_depth: PARTIAL. Read: abstract, introduction, section 3 (Prop 3, witness), 6.4-6.5, 7, H.4 transfer diagnostics, H.7 pilot, H.8 Table 15. Not read: proofs A-F, Dyck specification, H.2-H.3, H.5-H.6. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit

artifact audit: clean
