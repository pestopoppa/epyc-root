# MathSmith HC Formalizer Evaluation & A/B Testing

**Status**: stub
**Created**: 2026-03-20 (via research intake)
**Categories**: training_distillation, benchmark_methodology
**Depends on**: ~~rlm-orchestrator-roadmap.md~~ (Phase 4 Formalizer — Done, roadmap archived 2026-03-29)

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

### S1: Registry cleanup (low effort)
- [ ] Remove `forbid: speculative_decoding` from `formalizer` and `formalizer_q4` registry entries
- [ ] Update notes to reflect current state

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

### S5: Update proposal document
- [ ] Rewrite `MATHSMITH_CANONICALIZER_PROPOSAL.md` to reflect current deployment, HC results, and A/B findings
- [ ] Or retire it in favor of this handoff

## Open Questions

- Does the HC variant's consistency reward translate to better FormalizationIR JSON compliance?
- Is 8B the right size for formalizer, or would 14B/32B HC produce meaningfully better formalizations worth the speed cost?
- Should formalization be selective (only on hard/ambiguous problems) or always-on?
- Can the weakness-focused self-improvement loop be applied to our own problem distributions?

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
