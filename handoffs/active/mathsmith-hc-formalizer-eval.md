# MathSmith HC Formalizer Evaluation & A/B Testing

**Status**: refreshed 2026-05-28 — active but blocked on model availability check + S4 protocol; not a generic stub
**Created**: 2026-03-20 (via research intake)
**Updated**: 2026-05-28
**Categories**: training_distillation, benchmark_methodology
**Depends on**: ~~rlm-orchestrator-roadmap.md~~ (Phase 4 Formalizer — Done, roadmap archived 2026-03-29)

## 2026-05-28 Audit Reset — Executor Start Here

This handoff remains useful, but the old "stub" status understated both the deployed baseline and the real next decision. The open work is not to revisit the formalizer concept; it is to decide whether an HC model improves JSON consistency, math accuracy, and total-token cost enough to replace the current MathSmith-Hard formalizer.

**Critique of older structure**: it mixed registry cleanup, model acquisition, spec decode, and formalize-then-solve A/B without a front-door gate. A fresh implementer should first prove that the HC artifact exists and is loadable, then run a small S4 protocol before any broad benchmark.

**Current verified baseline**:

- `input_formalizer` feature exists in orchestrator `src/features.py`.
- Formalizer registry cleanup landed in inference-research commit `8cf5ada`.
- Historical benchmark records show the current Q4 formalizer path exists; Q8 speed anomaly remains a known issue.
- `MATHSMITH_CANONICALIZER_PROPOSAL.md` is retired; this file is the authority.

**Next action: S2 artifact check, then S4 mini-protocol**:

1. Check whether HC GGUFs already exist:
   ```bash
   huggingface-cli scan-cache | rg -i "MathSmith|HC|Jasaxion" || true
   ls /mnt/raid0/llm/models | rg -i "MathSmith|HC|formalizer" || true
   ```
2. If no GGUF exists, inspect HF availability before downloading:
   ```bash
   huggingface-cli repo ls Jasaxion/MathSmith-HC-Problem-Synthesizer-Qwen3-8B
   ```
3. If the model exists and the user approves inference, run a **10-problem mini S4** before any full suite:
   - 5 AIME-style problems
   - 5 OlympiadBench-style problems
   - same solver, same seed, two arms: direct solve vs HC formalize-then-solve
   - score with Math-Verify, not exact match
   - record both accuracy and total generated tokens

**Decision forks**:

| Mini S4 result | Action |
|---|---|
| Accuracy improves or ties and total tokens drop >=10% | Run full S4 on AIME/OlympiadBench. |
| Accuracy improves but tokens rise | Keep as selective hard-problem tool; route only high-ambiguity math. |
| Tokens drop but accuracy falls | Do not deploy; inspect formalization omissions before rerun. |
| HC artifact unavailable or conversion fails | Park this handoff as monitoring; keep current formalizer. |

**S4 mini-protocol table**:

| Date | HC artifact | Solver | Direct acc/tokens | Formalized acc/tokens | Decision |
|---|---|---|---:|---:|---|
| _pending_ | | | | | |

## Objective

Evaluate the updated MathSmith-HC (High Consistency) model as a replacement for the current MathSmith-Hard formalizer, and run the first end-to-end A/B comparison of formalize-then-solve vs direct solve on hard math problems.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-170 | MathSmith: Towards Extremely Hard Mathematical Reasoning (AAAI 2026) | medium | already_integrated |

## Background

The formalizer pipeline is fully deployed (Phase 4 Done, `src/formalizer.py`, feature flag `input_formalizer`). Current model: MathSmith-Hard-Problem-Synthesizer-Qwen3-8B (Q4_K_M @ 14.2 t/s, Q8_0 @ 3.3 t/s with known speed bug).

The AAAI 2026 paper introduces:
- **HC (High Consistency) variant**: adds answer consistency as GRPO reward dimension — should produce more stable, parseable JSON
- **New model sizes**: 1.7B, 4B, 8B, 14B, 32B (all vanilla Qwen3 — spec decode compatible)
- **Weakness-focused self-improvement**: iterative training targeting weak mathematical concepts
- Updated training (v3, 2026-03-08)

The canonicalizer proposal (`epyc-inference-research/research/MATHSMITH_CANONICALIZER_PROPOSAL.md`) is 3+ months old and partially stale.

## Current State

### What's deployed
- `math_formalizer` role: Q8_0 (8.1 GB, 3.3 t/s — speed bug)
- `math_formalizer_q4` role: Q4_K_M (4.7 GB, 14.2 t/s baseline, 16.1 t/s spec decode n3)
- Production uses Q4_K_M
- `formalizer.py`: 351-line implementation with keyword detection, JSON output, context injection

### Known issues
- Registry has stale `forbid: speculative_decoding` on both entries (Q4_K_M already has verified spec decode results)
- Q8_0 speed anomaly (3.3 t/s for an 8B model, should be 12-15+ t/s) — likely mradermacher GGUF conversion issue, never root-caused
- No A/B comparison of formalize-then-solve vs direct solve exists

## Work Items

### S1: Registry cleanup (low effort) — DONE 2026-04-05
- [x] Remove `forbid: speculative_decoding` from `formalizer` and `formalizer_q4` registry entries (both orchestrator + research registries)
- [x] Update notes to reflect current state

### S2: Download and quantize HC model
- [ ] Check mradermacher/bartowski for pre-made GGUFs of `Jasaxion/MathSmith-HC-Problem-Synthesizer-Qwen3-8B`
- [ ] If not available, convert from HF weights: `convert_hf_to_gguf.py` + `llama-quantize` for Q4_K_M and Q8_0
- [ ] Verify speed is normal (12-15+ t/s for Q8_0) — if so, confirms mradermacher conversion was the old speed bug
- [ ] Benchmark on existing formalizer test suite (summary.csv rows 15-16 baseline)

### S3: Spec decode validation
- [ ] Test Qwen3-0.6B as drafter for HC-8B (tokenizer-compatible, vanilla Qwen3)
- [ ] Test Qwen3-1.7B as drafter
- [ ] Compare against current Q4_K_M + spec decode n3 (16.1 t/s ceiling)
- [ ] Consider MathSmith-HC-Qwen3-1_7B-ShortCoT as domain-matched drafter

### S4: A/B benchmark — formalize-then-solve vs direct solve
- [ ] Design test protocol using new `aime` suite (60 questions, AIME2024+2025) and `olympiadbench` suite (674 questions)
- [ ] Pipeline A (baseline): solver model receives raw problem, produces answer
- [ ] Pipeline B (formalizer): MathSmith-HC formalizes → solver receives formalized problem → answer
- [ ] Solver candidates: Qwen2.5-Math-7B, Qwen3-8B, current production worker
- [ ] Measure: accuracy delta, latency overhead, total pipeline time
- [ ] Key question: does formalization help more on harder problems (AIME > OlympiadBench > MATH-500)?
- [ ] Measure total pipeline token cost: (formalizer tokens + solver tokens) vs (baseline solver tokens). Report per-problem breakdown — formalizer overhead is fixed (~300-500 tok) but solver savings should scale with problem ambiguity. Net cost reduction at equal-or-better accuracy validates the cost-reduction hypothesis (arxiv:2504.06514)
- [ ] Use Math-Verify (intake-377) for answer comparison instead of exact-match — 66% more accurate on math expressions. See eval-tower-verification.md for caveats (NOT symmetric, NOT thread-safe)

### S5: Update proposal document — DONE 2026-04-17
- [x] Retired `MATHSMITH_CANONICALIZER_PROPOSAL.md` (renamed to `.retired`). This handoff is the authoritative document; the 3+ month stale proposal added no value.

## Open Questions

- Does the HC variant's consistency reward translate to better FormalizationIR JSON compliance?
- Is 8B the right size for formalizer, or would 14B/32B HC produce meaningfully better formalizations worth the speed cost?
- Should formalization be selective (only on hard/ambiguous problems) or always-on?
- Can the weakness-focused self-improvement loop be applied to our own problem distributions?
- Does formalization reduce total pipeline token cost (formalizer + solver) compared to baseline solver-only, at equal or better accuracy? (arxiv:2504.06514 predicts yes — missing premises drive solver overthinking, and formalizer overhead may be recovered via reduced solver token count.)

## Notes

- All new MathSmith models are vanilla Qwen3 fine-tunes — no PARD tokenizer mismatch
- HC = High Consistency: GRPO reward adds answer consistency dimension on top of structural validity + reasoning complexity
- The existing `formalizer.py` implementation should work with the HC model without code changes — it's the same Qwen3-8B architecture
- AIME + OlympiadBench suites added to question pool on 2026-03-20 (intake-170 follow-up)

## Research Intake Update — 2026-03-28

### New Related Research
- **[intake-233] "Goedel-Code-Prover: Hierarchical Proof Search for Open State-of-the-Art Code Verification"** (arxiv:2603.19329)
  - Relevance: Uses same Qwen3-8B base + GRPO training pipeline for Lean 4 proof generation
  - Key technique: Hierarchical proof search with recursive lemma decomposition + decomposition score combining constructive justification and structural effectiveness
  - Reported results: 62.0% prove success on 427 tasks (2.6x over strongest baseline), beats GPT-5.3-Codex (18.5%)
  - Delta from current approach: Goedel trains for code verification proofs (specs→proofs), MathSmith trains for problem formalization (NL→formal). Same model family, different downstream task. Their GRPO + online Lean verification reward signal is analogous to HC's consistency reward but applied to proof correctness rather than answer consistency.

## Research Intake Update — 2026-04-15

### Formalizer-Overthinking Connection (PRIORITY ELEVATION)

arxiv:2504.06514 ("Missing premise exacerbates overthinking in reasoning models"), surfaced via intake-379 (MathQ-Verify), validates the formalizer's value proposition beyond accuracy:

**Mechanism**: Missing or ambiguous premises cause models to explore multiple interpretations, generating excessive reasoning tokens (overthinking). The formalizer pre-fills missing structure via `[FORMAL SPECIFICATION]` blocks — variables, constraints, edge cases — causing the solver to converge on the correct interpretation with fewer tokens.

**This reframes the formalizer from "accuracy tool" to "accuracy + cost-reduction tool."**

The key metric for S4 is **total pipeline cost** (formalizer generation + solver generation) vs **solver-only baseline**, at equal or better accuracy. Formalizer overhead (~300-500 tok from MathSmith-8B at 14.2 t/s Q4_K_M) must be offset by solver token savings. The overthinking theory predicts savings scale with problem ambiguity — expect largest gains on ambiguous/under-specified problems.

**Theoretical grounding**: Conditional Information Bottleneck (`research/deep-dives/overthinking-info-bottleneck.md`). The formalizer raises I(Z; Y | X) — adding conditioning information that makes the solver's compressed representation more informative about the answer, reducing optimal reasoning length (Proposition 4.1). The HC variant's consistency reward (GRPO) further strengthens this: more consistent formalizations → even less solver exploration needed.

**S4 priority elevated**: S4 now tests two hypotheses (accuracy improvement AND net cost reduction), not just one.

### Math-Verify for S4 Answer Validation
- **[intake-377] Math-Verify** (`github:huggingface/Math-Verify`): Use `math_verify.verify(gold, pred)` for answer scoring in S4 benchmarks (AIME, OlympiadBench, MATH-500). Current exact-match underestimates capability by ~66% on math expressions.
- Caveats: NOT symmetric (gold must be first arg), NOT thread-safe (`signal.alarm()`), open interval ambiguity `(1,2)` → `Tuple(1,2)`
- Cross-ref: `eval-tower-verification.md` Research Intake Update 2026-04-15 for full integration analysis

### Question Quality Filtering
- **[intake-379] MathQ-Verify**: If applying question quality filtering to S4 test suite, use stages 1-4 only — stage 5 (completeness) hurts F1 by +0.57pp (ablation finding)
- Missing premises in eval questions also waste compute — flawed questions trigger solver overthinking, inflating per-question cost and degrading signal quality

## Research Intake Update — 2026-05-04

### Qwen-Scope feature-overlap analysis as test-suite construction signal

- **[intake-521] "Qwen-Scope: Turning Sparse Features into Development Tools for LLMs"** (Qwen Team, 2026-04-30) — deep-dive at `research/deep-dives/qwen-scope-sae-suite.md`; coordination handoff `../completed/qwen-scope-sae-toolkit.md` (archived 2026-06-12; Section-4 application now an EV-8 candidate in `eval-tower-verification.md`).
  - Relevance to MathSmith S4 test-suite construction: Section 4 of the paper provides an evaluation-free framework to detect **structural redundancy** within a benchmark (per-sample feature footprints saturating early as samples are added) and **capability overlap** between two benchmarks (asymmetric and min-normalized feature-set overlap). Both signals are directly applicable to MathSmith's harder-distribution test-suite design where sample budget is constrained and we want each sample to contribute discriminative power.
  - The paper's worked example is on point: from Figure 6, *63% of GSM8K's features are covered by MATH, while only 10% of MATH's features are covered by GSM8K*. The asymmetry carries the operational signal — MATH probes a broader feature set than GSM8K, so a suite containing MATH can drop GSM8K with little discriminative loss; the reverse substitution is not safe. Same logic applies to MathSmith S4 vs. its predecessor S1-S3 splits and to MathSmith vs. external math benchmarks (MATH, GSM8K, GPQA-D-math-only) we may want to deduplicate against.
  - Concrete additions to the handoff's existing question-quality-filtering pipeline (which currently uses MathQ-Verify stages 1-4 from intake-379):
    - **Pre-construction**: when sourcing or generating MathSmith candidate questions, encode them through SAE-Res-Qwen3.5-27B at the middle layer band and reject candidates whose feature footprints duplicate the existing pool (asymmetric overlap > some threshold against pool feature-footprint).
    - **Post-construction**: compute the suite's redundancy curve c_n; if c_n saturates early, the suite is over-redundant and adding more samples won't improve discriminative power. This becomes a stopping rule for the synthesis pipeline.
    - **Cross-suite**: compute MathSmith S4 ↔ {MATH, GSM8K, GPQA-D, KOR-Bench, AA-Omniscience-math-slice} feature-overlap matrix to characterize what S4 uniquely probes that the existing suites do NOT.
  - Caveats (deep-dive 2026-05-04):
    - SAE training data is undisclosed; redundancy claim is in-distribution to Qwen pretraining. For math benchmarks specifically, well-known datasets (MATH, GSM8K) are almost certainly in the pretraining corpus; this is fine for the comparative analysis, but the absolute feature-coverage numbers should not be interpreted as "objective" benchmark difficulty.
    - License `qwen` custom; Section 4 post-hoc analysis unambiguously permitted.
    - Wang et al. 2026 / AxBench critiques target steering and concept detection, not redundancy — they do not apply to this Section 4 application.
  - **Cross-link**: implementation work belongs in `eval-tower-verification.md` EV-8 (just queued there in the parallel intake update). MathSmith should consume that pipeline once it lands rather than pull a parallel SAE; only one EV-8 stack to maintain.
  - **Action**: defer until eval-tower EV-8 SAE-redundancy work lands. Track cross-suite overlap analysis as a stretch goal once S4 generation is operational and the pipeline produces feature footprints.
