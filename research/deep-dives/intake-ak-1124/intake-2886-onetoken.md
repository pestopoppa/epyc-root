# Dive — onetoken — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2507.08794v3", retrieved: "2026-11-24", sha256: "caab8301e3f6"}

Stage 2b wave 1, light dive. Expanded from intake-2877 (loopholes). Settles the master-key string library and the mitigation for A1.

## 1. Stage-1 fields
- **Title**: One Token to Fool LLM-as-a-Judge.
- **Authors**: Yulai Zhao, Haolin Liu, Dian Yu, S.Y. Kung, Meijia Chen, Haitao Mi, Dong Yu (Princeton, UVA, Tencent AI Lab, Rutgers; work done during two internships at Tencent AI Lab).
- **Version**: arXiv 2507.08794 v3, cs.LG, 11 Jun 2026 (page.txt render; arxiv_meta.json says v3). v1 id is July 2025, so it is older than 12 months. No venue stated in the page text.
- **Categories**: benchmark_methodology, training_distillation.
- **Novelty**: medium. Judge-vulnerability papers exist; the contribution here is that content-free strings (punctuation, "Thought process:", "Solution") flip reference-based judges, plus a cheap SFT fix.
- **Relevance: medium.** Gives the exact string library and per-judge FPR levels that A1 (loopholes dive ledger) needs, and two prompt-level mitigations testable without training. No live gate of ours optimises against an LLM judge (loopholes dive section 5), so not high.
- **Credibility: 1/6.** peer-reviewed +0 (none stated); <=12 months +0 (v1 July 2025); major lab +1 (Tencent AI Lab); commercial bias 0; independent corroboration 0 (intake-2877 uses it as one of 14 families but that is a consumer, not a replication). Total 1.
- **Verdict: adopt_patterns.** Adopt the string list and the no-question / no-CoT prompt variants as A1 arms; do not adopt Master-RM weights (Qwen2.5-7B/32B, math/general reference-based; release promised, not confirmed in source).

## 2. Key claims
1. **CONFIRMED.** Ten content-free responses (four non-word symbols, six reasoning openers incl. three languages' "Solution") elicit false-positive rewards from reference-based judges. Anchor: claim_index 0.
2. **CONFIRMED with number correction.** FPR is large for general judges: Qwen2.5-72B averages 66.8% (worst 90.9%) over five benchmarks without CoT; Qwen2.5-7B averages 12.6% (worst 31.0%); GPT-4o reaches 35% on punctuation. The claim "up to 80%" in Fig. 1 caption is a worst-cell value. Proprietary judges are low on average in the Multi-subject set (GPT-o1 0.9|3.4, Claude-4 0.7|4.1, average|worst) but this is one dataset; the paper states Claude-4 and GPT-o1 are also affected. Anchor: claim_index 1.
3. **CONFIRMED.** Fix by SFT augmentation: 20k first-sentence truncations labelled NO added to the 160k set; Master-RM-7B/32B reach near-zero FPR on all ten keys across all five benchmarks (average|worst 0.0|0.0 and 0.1|0.2 on Multi-subject), Cohen kappa 0.91 with GPT-4o and 0.90 with humans for the 7B. Authors' own evaluation only. Anchor: claim_index 2.
4. **PARTIAL (generalisation of inference-time fixes).** Majority-vote CoT does not reliably help: 7B average|worst 40.4|91.3 with CoT versus 12.6|31.0 without; 72B average falls 66.8 to 50.9 but worst rises 90.9 to 97.0. Removing the question from the judge prompt cuts FPR sharply on math (72B GSM8K 87.6|90.9 to 0.0|0.0; AIME 54.0|90.9 to 0.0|0.0) but less on NaturalReasoning (62.3|72.8 to 50.1|62.4); authors caution general reasoning needs the question. Anchor: claim_index 3.
5. **CONFIRMED.** Scale is non-monotone in the Qwen2.5 family: 0.5B lowest FPR but worst agreement, best balance at 7-14B, FPR climbs again at 32B/72B. Embedding-similar strings also work ("mental process" 16.1% on GSM8K for GPT-4o). So a fixed string list under-covers; paraphrases need testing. Anchors: claim_index 4.

## 3. Reported results (as stated)
Table 1 (five benchmarks, ten keys, twelve judges incl. Qwen2.5-72B/7B, LLaMA3-70B/8B, GPT-4o, GPT-o1, Claude-4, Multi-sub RM, General-Verifier, Omni-Judge). Table 1 Multi-subject RLVR average|worst: Master-RM-7B 0.0|0.0; Master-RM-32B 0.1|0.2; Multi-sub RM 0.1|0.5; General-Verifier 4.6|26.7; Omni-Judge 19.6|54.1; Qwen2.5-72B 51.4|70.5; Qwen2.5-7B 9.0|15.7; LLaMA3-70B 66.2|79.7; LLaMA3-8B 55.0|73.8; GPT-4o 10.4|28.9; GPT-o1 0.9|3.4; Claude-4 0.7|4.1. General-Verifier hits 66.8% on MATH with a single blank. Table 2: kappa and VerifyBench accuracy of Master-RM-32B 95.15 / 86.80 (VerifyBench / Hard). Hardware and judging setup NOT-FOUND-IN-SOURCE beyond model names; judge prompts are in Appendix B.1 (not read in full). Original collapsed RLVR run used Qwen2.5-72B-Instruct as the judge, which rewarded openers like "Solution".

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Content-free master key vs reference-based judge | YES, device-independent; each probe is one short judge call. Our 27B judge on MI210 handles ~471 problems x 10 keys per config cheaply (uncited estimate). | YES, same; CPU judge slower per call but bounded count. |
| Drop the question from the judge prompt (NQ) | YES: prompt-only change, shorter prompt so cheaper prefill. | YES, same. |
| SFT negative augmentation (Master-RM) | PARTIAL: needs training; MI210 fine-tuning of a 7B judge possible but not planned. Only worth it if an audit finds a judge failing. | NO: no CPU training. |
| Majority-vote CoT judge | NO benefit: worst case worsens and costs 5x calls (on either device). | NO, same. |

## 5. In-house state
- Default judge `architect_critic` and all served generators are Qwen-family (`scripts/autopilot/eval_tower.py:150`, `:3522-3531` @ lane f74b175 per loopholes dive section 5). Qwen2.5-72B at 66.8% average is the closest cousin tested; Qwen3.8-27B was NOT tested here (NOT-FOUND-IN-SOURCE).
- EV-29 (`handoffs/active/eval-tower-program.md:649` @ f74b175) measures FPR on known-wrong answers, show-candidate vs commit-first; this paper's NQ and no-CoT arms are cheap extra arms on the same labelled set. C21 `98ff8a4` not involved.
- No master-key probe exists in the lane (grep of intake index: 2507.08794 appears once, in a `referenced_arxiv_ids` list only).

## 6. Derived-actionables ledger
| # | Task line | Owner | Type | Stop/decision rule |
|---|---|---|---|---|
| O1 | refines loopholes A1: use the ten Table-1 keys (blank, ".", ",", ":", "Thought process:", "Let's solve this problem step by step.", "Solution", Chinese/Japanese/Spanish "Solution") as the seed library for the 14-string FPR probe, plus 3-5 paraphrases ("mental process") to test coverage. | `eval-tower-program.md` | judge-inference row (GPU/CPU), small | Question: does any key exceed the pre-set FPR for a gating judge? Stop-on-answer per judge; futility = all keys < 1%. |
| O2 | refines loopholes A3/EV-29: add a no-question (NQ) arm and a single-pass (no majority-vote CoT) arm to the EV-29 labelled set. | `eval-tower-program.md` EV-29 | judge-inference, reuses labelled set | Question: does NQ halve worst-key FPR for our judge on math suites? Stop if no change at n of the EV-29 set. |
| O3 | Decline: train a Master-RM style judge. Reason: no audit has found a failing judge yet; revisit only if O1 shows a gating judge above threshold (then the 20k truncated-opener recipe is the fix to cost). |  |  |  |
| O4 | Decline: majority-vote CoT as a defence. Reason: the paper's own Table 3(a) shows it worsens worst-case FPR for the 72B and the 7B. |  |  |  |

## 7. Dive-surfaced sources
- Appendix B.1/D prompts and Table 14 (more master keys) are in this paper; no further source. Master-RM weights: promised "upon publication", release NOT-FOUND-IN-SOURCE; decline ingest (would change no ledger row unless O1 fails).

## 8. Contradiction / adversarial pass
Authors' mitigation is self-evaluated; keys tested are held out only from training augmentation overlap by their own check. Reference-based setting only (reference answer in prompt); our reference-free judging (critic, coherence) is out of distribution. Human agreement by the authors themselves (PhD authors, majority vote). NQ result limited to math. No independent replication found in the page. Scaling hypothesis explicitly not established.

## 9. read_depth
PARTIAL: read abstract, intro, Sections 2-4, Tables 1-3; Appendices A-G (prompts, Table 14, appendix scaling/mechanism) not read. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
