# Dive — ray — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2606.01066v1", retrieved: "2026-11-24", sha256: "043dcc30e2d3"}

Stage 2b wave 1, light dive. Expanded from intake-2877 (loopholes). Question: is the fuzzing procedure a cheaper or complementary audit for our deterministic graders?

## 1. Stage-1 fields
- **Title**: Before the Model Learns the Bug: Fuzzing RLVR Verifiers (title from arxiv_meta.json).
- **Authors**: NOT-FOUND-IN-SOURCE (page text has no author block; the key name "ray" comes from the bearing dive).
- **Version**: arXiv 2606.01066 v1.
- **Categories**: benchmark_methodology, tool_implementation.
- **Novelty**: medium-low. Differential testing (buggy vs strict reference) applied to RLVR verifiers; the result that bugs create exploitable false-positive regions is expected.
- **Relevance: medium.** It is the only entry that audits DETERMINISTIC verifiers (math-verify, JSON schema, test harness) which is what our eval_tower scorers are, with no model inference. The paper's workloads are toy.
- **Credibility: 1/6.** peer-reviewed +0; <=12 months +1; major lab 0; commercial bias 0; independent corroboration 0. Total 1. Claims rest on bugs the authors injected themselves into toy workloads.
- **Verdict: adopt_patterns** (adopt the paired buggy/strict differential procedure and the "report FPR with acceptance and coverage" rule).

## 2. Key claims
1. **CONFIRMED (synthetic).** Injected-bug verifiers accept incorrect completions at high rates over 10 seeds: math 0.832 FPR, JSON 0.869, code 0.557; strict variants 0.000 on the generated cases. The "strict" verifier is an operational proxy, not proof of correctness. Anchors 0, 1.
2. **CONFIRMED (narrow, but relevant).** Replay of the open-source math-verify on 100 cases: FPR 10/60 = 0.167, all from partial_answer cases (gold value in prose, no final-answer marker). The SymPy-backed strict final answer removes these but accepts fewer cases (0.500 to 0.400) and covers fewer (0.900 to 0.760). Replay is relative to the authors' own stricter contract. Anchor 2.
3. **CONFIRMED.** Buggy rewards are found fast: exploit within two queries in 94/100 math trials and 98/100 JSON trials, 100/100 within four; strict verifiers 0/100 at all budgets. Fixed template pool, not a neural policy. Anchor 3.
4. **CONFIRMED.** The code verifier bug classes visible-test overfitting, stdout spoofing, missing timeout; hardening step removing stdout acceptance and adding hidden tests takes code FPR 0.55 to 0. Anchor 4.
5. **CONFIRMED (limits).** Evaluation scoped to verifier behaviour, not end-to-end RLVR training; they do not estimate exploit rates for neural fine-tuning. Anchor 5.

## 3. Reported results
Plain Python, no GPU; seeds 0-9; 95% bootstrap CIs. Math workload 200 cases (120 negative, 80 positive); JSON 500; code 100. Round-0 exploit-candidate rates 0.513 math, 0.888 JSON, 0.533 code; after one adaptive round 1.000 each. Template search and tabular policy gradient (final round): buggy math reward 0.967, proxy correctness 0.154. HumanEval-style study: 20 programs (4 correct, 16 incorrect), buggy verifier FPR 16/16, strict 0/16.

## 4. Performance-principles table (procedure)
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Paired buggy/strict differential testing with mutation categories (contradiction, missing marker, partial answer, loose float, stdout spoof) | YES, no device use. | YES: pure Python, minutes on CPU. |
| Report FPR together with acceptance and coverage | YES: a lower FPR from narrower language must show lower acceptance. | YES, same. |
| Black-box query budget as exploit-discovery metric | PARTIAL: applies to a policy with reward feedback; AK/AP search with deterministic graders could be probed the same way. | PARTIAL, same. |

## 5. In-house state
eval_tower deterministic scorers: `math_verify` scoring with hard-fail (EV-11, `handoffs/active/eval-tower-program.md:528` @ f74b175), nested-boxed fix EV-11a (`:529`), and an audit table with SCORE-01 to SCORE-25 findings at `:1979-1991` (silent scorer fallbacks; threaded math_verify degrade to exact_match; A1 fix ticked at `:2165`). The audit found scorer bugs by reading code, not by differential fuzzing with a strict reference. No mutation-category fuzz of the scorers is in the lane (grep of `fuzz`, `differential` in eval-tower-program.md: no hits). Scorer code paths in the orchestrator: `/workspace/repos/epyc-orchestrator/scripts/autopilot/eval_tower.py` (read path only, not traced).

## 6. Derived-actionables ledger
| # | Task line | Owner | Type | Stop/decision rule |
|---|---|---|---|---|
| R1 | refines loopholes A1/A2 (complementary, cheaper first step): replay the ray mutation categories (partial_answer, missing marker, contradictory finals, loose float, wrong-then-correct) against the eval_tower math_verify and exact-match scorers and report FPR with acceptance and coverage, using a stricter marked-answer reference. | `eval-tower-program.md` (scorer-audit neighbourhood, SCORE-* table at :1979) | code-only, CPU minutes, zero model inference | Question: does our math scorer accept a prose-only gold value as correct? Stop-on-answer after the five categories; futility if FPR = 0 on all. |
| R2 | Decline: JSON/tool-call fuzz of schema validators. Reason: no lane scorer is a JSON schema verifier that gates a decision; revisit if one is added. |  |  |  |
| R3 | Decline: template-search/tabular-PG exploit-discovery proxy. Reason: needs a policy with reward feedback; none optimises against our graders. |  |  |  |

## 7. Dive-surfaced sources
- Helff et al. arXiv 2604.15149 and Khalifa et al. arXiv 2603.07084 (cited by ray as prior verifier-gaming work): would change no ledger row; decline.

## 8. Contradiction / adversarial pass
Authors state the fuzzers use deterministic templates and one adaptive loop, do not model a trained policy's completion distribution, and the code harness is not a sandbox. The math-verify "false positives" are defined against the authors' own stricter contract (a replay mismatch of accepted language), not a defect claim about math-verify. jsonschema row has 0 coverage, so it measures non-engagement. No external replication.

## 9. read_depth
PARTIAL: read abstract, Sections 1-9; reference list read only for the cited prior work. Authors, repo, and artifact manifest NOT-FOUND-IN-SOURCE. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
