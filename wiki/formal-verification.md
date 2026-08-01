# Formal Verification

**Category**: `formal_verification`
**Confidence**: verified
**Last compiled**: 2026-05-27
**Sources**: 7 documents (added RustEvo2 verification gate)

## Summary

Formal verification research for the EPYC stack centers on deploying a two-tier Lean 4 proving pipeline using local models. Two complementary systems have been evaluated: Goedel-Code-Prover-8B (function-level code verification, 62.0% prove rate, MIT license) and Leanstral (119B MoE, repo-scale proof engineering, 26.3 pass@2 on FLTEval, Apache 2.0). These tools serve different purposes -- Goedel is a prover (takes goal, produces tactic proof via hierarchical search), while Leanstral is an agent (uses lean-lsp-mcp, reads repo context for architectural proof planning).

Goedel-Code-Prover-8B achieves 2.6x over the strongest baseline on function-level verification (Verina/Clever/AlgoVeri, 427 tasks) despite being a vanilla Qwen3-8B with no architectural modifications. All innovation is in the training pipeline: SFT on 432K teacher-generated trajectories (GPT-5.2/Gemini-3-Flash), followed by hybrid RL using GRPO with auxiliary SFT loss to prevent regression. The decomposition score formula aligns training reward with inference-time ranking. A key ablation shows decomposition alone is worth +28pp, and joint training shows synergy (68.7% vs 59.2% with only one component trained). The model outperforms systems 4-84x larger including GPT-5.3-Codex (18.5%) and DeepSeek-Prover-V2 at 671B.

Leanstral is a fine-tune of Mistral Small 4 using DeepSeek V3-style MoE + MLA architecture. With 119B total parameters but only 6.5B active per token, it is an ideal candidate for REAP expert pruning -- 95% of total parameters are routed expert weights. If expert activation patterns cluster on Lean 4 workloads (likely given domain specialization), REAP could prune to 32 experts (~20 GB Q4_K_M) while maintaining quality. At full size it runs ~36 t/s on EPYC 9655; REAP-pruned could hit 40+ t/s. The `deepseek2` architecture is fully supported in llama.cpp.

The proposed pipeline follows the OCR pattern: Leanstral plans (repo-scale context, proof strategy, subgoal decomposition), Goedel-CP executes at volume (tactic generation, leaf-goal proving, pass@k with compiler feedback). Combined memory footprint is ~25 GB with REAP-pruned Leanstral + Goedel-CP Q4_K_M, leaving massive headroom on EPYC 9655.

Verina (intake-234) provides a benchmarking framework for verifiable code generation but was assessed as not applicable for direct integration -- it is a benchmark, not a tool.

## Key Findings

- **RustEvo2 is now a gate benchmark for narrow-domain coder distillation claims.** The Strand-Rust-Coder-14B verification handoff scopes a single standalone RustEvo2 run to test Fortytwo's "#1 on RustEvo2" and "beats GPT-5 Codex on Rust" claims before any larger swarm-dataset effort starts. The run is intentionally isolated from the production stack, sequential across models, and requires explicit approval before inference because it is a benchmark gate, not background autopilot traffic. Source: [strand-rust-coder-rustevo2-verification.md](../handoffs/active/strand-rust-coder-rustevo2-verification.md).

- Goedel-Code-Prover-8B achieves 62.0% prove rate on 427 verification tasks, 2.6x over strongest baseline (BFS-Prover-V2, 32B) [goedel-code-prover-analysis.md]
- All Goedel-CP innovation is in training methodology -- vanilla Qwen3-8B base with standard GGUF conversion [goedel-code-prover-analysis.md]
- Decomposition alone worth +28pp; decomposition score AUROC 0.903 as predictor of downstream provability [goedel-code-prover-analysis.md]
- Leanstral's 95% of params are routed experts -- ideal REAP pruning candidate. REAP-32 + Q4_K_M would be ~20 GB [leanstral-architecture-analysis.md]
- Leanstral beats Claude Sonnet 4.6 on FLTEval (26.3 vs 23.7 pass@2) at 15x lower cost ($36 vs $549) [leanstral-architecture-analysis.md]
- Goedel-CP pipeline defaults to 512 concurrent LLM requests; local deployment needs only 2-4 slots, extending wall-clock from 30 min to 2-6 hours per problem [goedel-code-prover-analysis.md]
- Goedel-CP Q4_K_M: ~4.5 GB, expected 25-40 t/s on EPYC 9655. Q8_0: ~8.5 GB, 15-25 t/s [goedel-code-prover-analysis.md]
- Different evaluation benchmarks: Goedel uses Verina/Clever/AlgoVeri (function-level), Leanstral uses FLTEval (repo-scale). Not directly comparable [both deep-dives]
- Both models require Lean 4 toolchain + Mathlib4 infrastructure, plus lean-ray-server for verification [lean-proving-pipeline.md]

## Actionable for EPYC

- **S1 (P0): Convert Goedel-CP-8B to GGUF**: Download safetensors, convert with `convert_hf_to_gguf.py`, quantize to Q4_K_M and Q8_0. Validate with simple Lean proof generation test. Trivial -- vanilla Qwen3-8B.
- **S2 (P1): Profile Leanstral expert activation**: Download community GGUF (68 GB Q4_K_M), run with `--moe-expert-stats` on Lean 4 workloads. Determine if <=32 experts cover 95% of activations.
- **S3 (P1): REAP-prune Leanstral**: If profiling confirms clustering, prune to top-32 experts. Target: ~20 GB Q4_K_M at 40+ t/s.
- **S4 (P2): End-to-end pipeline test**: Run Goedel-CP against local llama-server (2-4 slots) on FormalQualBench subset (5 theorems). Measure prove rate and wall-clock.
- **S5 (P3): Two-tier integration**: Design routing between Leanstral (planning) and Goedel-CP (execution). Implement adapter between Leanstral MCP output and Goedel-CP input format.
- **Infrastructure**: Install Lean 4 toolchain, Mathlib4, lean-ray-server. These are prerequisites for any formal verification work.
- **Strip Leanstral's Pixtral vision encoder**: Dead weight for proof tasks (~1B params). Could be removed to save memory.

## Open Questions

- Does the formalizer-as-cost-reduction hypothesis (arxiv:2504.06514) generalize beyond math to code verification domains?
- Does Leanstral's planning output format align with Goedel-CP's input expectations, or is significant adapter work needed?
- Can lean-ray-server and lean-lsp-mcp coexist, or do they need separate Lean toolchain instances?
- What is the minimum viable concurrency for Goedel-CP's pipeline before wall-clock becomes impractical (target: <6 hours per problem)?
- Is FormalQualBench (23 math theorems) the right eval for code verification, or should Verina subset be used?
- How do REAP-pruned Leanstral quality metrics compare to full model on Lean 4 specifically?

## Formalizer as Cost-Reduction Tool

- **Formalizer reduces total pipeline cost, not just accuracy**: arxiv:2504.06514 ("Missing premise exacerbates overthinking in reasoning models") shows that missing or ambiguous premises cause solvers to explore multiple interpretations, generating excessive reasoning tokens. The MathSmith formalizer pre-fills missing structure via `[FORMAL SPECIFICATION]` blocks, causing the solver to converge with fewer tokens. The Conditional Information Bottleneck (Proposition 4.1) provides theoretical backing: formalization raises I(Z; Y | X), reducing optimal reasoning length. The HC variant's GRPO consistency reward further strengthens this effect. [mathsmith-hc-formalizer-eval.md](../handoffs/active/mathsmith-hc-formalizer-eval.md)
- **Math-Verify for benchmark answer validation**: intake-377 (HuggingFace Math-Verify) provides robust mathematical expression comparison with LaTeX parsing, symbolic simplification, and matrix equivalence. Current exact-match scoring underestimates model capability by ~66% on math expressions. Integration caveats: `verify(gold, pred)` is NOT symmetric, NOT thread-safe (`signal.alarm()`), and open intervals `(1,2)` convert to `Tuple(1,2)`. Applicable to MathSmith S4 A/B benchmark and Goedel-CP evaluation. [mathsmith-hc-formalizer-eval.md](../handoffs/active/mathsmith-hc-formalizer-eval.md)
- **Question quality filtering for eval**: intake-379 (MathQ-Verify) provides a 5-stage pipeline for validating question quality. Flawed questions with missing premises also waste compute by triggering solver overthinking. Stage 5 (completeness) hurts F1 by +0.57pp -- deploy stages 1-4 only. [mathsmith-hc-formalizer-eval.md](../handoffs/active/mathsmith-hc-formalizer-eval.md)



## Incomplete-checklist verification: when the check is correct but does not cover enough

**Confidence: verified** (three measured instances, 2026-08-01)

A sibling of the fail-open class, and harder to find. A fail-open guard returns the wrong
*answer*; an incomplete-checklist guard returns the right answer to **too small a question**. It
never lies, it just never looks. Nothing is duplicated, so a de-duplication or refactoring pass
walks straight past it, and no amount of reviewing what *is* checked can reveal what is absent.

### The shape

A **producer** emits N facts. A **verifier** iterates a hand-maintained list of M < N of them.
The gap is invisible because both sides are individually correct and the output is green.

### Three measured instances, one day

| checklist | producer emitted | verifier checked | consequence |
|---|---|---|---|
| runtime attestation fields | every declared launch field | all **except `device`** | a 27B declared on ROCm0 ran on 24 CPU threads with the GPU at 0%, reporting `healthy / attest ok`; VRAM 13 MB of 68.7 GB |
| `REQUIRED_SOURCE_ARTIFACTS` | 9 source pins | a hardcoded **7** | two newly declared config artifacts were pinned and **never verified** — mutating them changed no verdict |
| `RETIRED_LIVE_ROLES` | a table stale in every value | grep for **one** known-bad role name | passed a file whose 4/4 rows described a fleet retired ~3 months earlier at throughputs 1.4×–11× too low |

The third is the sharpest: name-matching cannot detect a table that is stale in every **value**
while naming only **current** roles. The guard was structurally incapable of the finding.

### The remedy generalises

**Derive the checklist, not just the values.** Iterate the producer's own keys, so a fact added
upstream is verified automatically with nobody needing to remember. Keep the hand-written list as
a **floor** — required entries must still be present — so a producer that silently *stops*
emitting one is still caught. Coverage is gained without losing any.

For the value-staleness variant, the durable form is a **comparison against the compiled
artifact**, not a grep for known-bad strings. A rule that compares catches drift nobody enumerated
in advance. Deployed as `stale_role_fact_table`, it fired on first run against a live launch
surface where every row named a current role — including a `frontdoor` entry pointing at a
**non-MTP** GGUF that would have silently disabled speculative decoding.

### A related sub-pattern: the hardcoded lookup KEY

The value is properly derived; the **key** is not.

```python
coder_escalation: str = field(default_factory=lambda: _server_url_default("frontdoor"))
```

This calls the derived resolver and looks locally correct — which is why it survives every "is
this value derived?" audit. It faithfully returns the right answer to the **wrong role**, and it
broke the moment that role was repointed. Detection is mechanical: compare each field name
against the literal key it looks up, and treat every mismatch as suspect. Four were found this
way; three were byte-identical when derived (legitimate aliases the resolver already handles) and
one was a real defect that had silently survived a whole model cutover.

**Rule: the field name IS the key.** Alias resolution belongs inside the resolver, which already
reads the registry's `shared_with` relation — a call site that names another role has taken that
decision away from the data.

### Screen

Add to the two fail-open screens a third:

3. **Is my checklist derived from the producer, or written by hand?** If hand-written, the
   question is not whether the entries are right but what is *missing* — and that cannot be
   answered by reading the list.

### Sources

- `progress/2026-08/2026-08-01.md` — W1 cutover session, three instances with measured blast radius
- `handoffs/active/numa-topology-cutover-resume-20260730.md` — NEW section, 2026-08-01
- epyc-orchestrator `a517793c` — all three remedies plus `stale_role_fact_table`
- `/mnt/raid0/llm/tmp/launcher-refactor-proof/` — byte-equality snapshot proving the extraction changed no value

## Related Categories

- [MoE Optimization](moe-optimization.md) -- Leanstral is a prime REAP pruning candidate with 128 routed experts
- [Reinforcement Learning](reinforcement-learning.md) -- Goedel-CP uses hybrid GRPO + SFT training
- [Speculative Decoding](speculative-decoding.md) -- Both models benefit from standard speculation on dense architectures

## Source References

- [Goedel-Code-Prover analysis](/workspace/research/deep-dives/goedel-code-prover-analysis.md) -- Architecture, training pipeline, decomposition scoring, deployment estimates
- [Leanstral architecture analysis](/workspace/research/deep-dives/leanstral-architecture-analysis.md) -- MoE + MLA architecture, REAP pruning analysis, EPYC deployment estimates
- [Lean proving pipeline handoff](/workspace/handoffs/active/lean-proving-pipeline.md) -- Two-tier architecture design, work items S1-S5, infrastructure requirements
- [intake-233](https://arxiv.org/abs/2603.19329) Goedel-Code-Prover intake entry -- Initial evaluation and verdict
- [intake-235](https://mistral.ai/news/leanstral) Leanstral intake entry -- Initial evaluation and verdict
- [MathSmith HC formalizer eval handoff](/workspace/handoffs/active/mathsmith-hc-formalizer-eval.md) -- Formalizer-overthinking connection (arxiv:2504.06514), Math-Verify integration (intake-377), MathQ-Verify question quality (intake-379)
- [Strand-Rust-Coder RustEvo2 verification](../handoffs/active/strand-rust-coder-rustevo2-verification.md) -- independent gate for Fortytwo's Rust specialist model and downstream dataset-distillation work

---

## Fail-open verification: when a check passes on the condition it detects

**Confidence: verified** (measured reproductions, 2026-07-31)

A guard that returns success when it *cannot evaluate* its condition is worse than no guard:
it converts an unknown risk into a false assurance, and everything downstream is built on it.
Seven instances were identified in a single working day across the orchestrator's validation
layer and two operator ratification scripts.

### The shape

Every instance collapses two distinct outcomes into one output:

> *"the property holds"* and *"I could not evaluate the property"*

Two variants recur. **Presence-checking**: a script verifies that its own edit arrived rather
than that the edited artifact is still coherent. **Neutral-return on exception**: a helper
returns `{}` / `None` / `[]` when an import or parse fails, and the caller reads the empty
value as "no violations".

### Two screens that catch the class

1. **Can I make this check pass by *deleting* the thing it inspects?** If yes, it is
   fail-open. Worked examples: `_launch_manifest_targets` passes by deleting the import; a
   binary-hash verifier passes by rebuilding the binary; a marker grep passes by renaming the
   tree.
2. **Did I verify *the* consumer, or just *a* consumer?** The first screen misses a distinct
   failure — tracing a consumer chain and stopping one hop early, where every check confirms a
   true statement about a function not on the live path. Remedy: resolve fallback chains at
   runtime and print the source label. A config surface with fallbacks and no source label has
   that absence as its first bug.

### Two rules

- **Inability-to-evaluate is a THIRD outcome.** Emit `PASS` / `FAIL` / `COULD-NOT-CHECK`,
  loudly and non-zero.
- **Verify the post-state, not the presence of your edit.**

### Measured blast radius

| guard | effect when it fires | measured |
|---|---|---|
| `stack_change_guard.py:829` | promotion gate goes clean | targets 22→0, errors 12→0 |
| `stack_change_guard.py:1000` | context assertion skipped everywhere | 0/22 roles checked, target count unchanged so invisible |
| `stack_change_guard.py:962` | model-path coverage drops | poisoned paths detected 10/10 → 8/10 |

A byte-hash integrity check does **not** cover this: during an import failure the source file
is byte-identical and unimportable simultaneously, so the hash stays green while the thing it
certifies cannot load.

### Self-referential case

A script that amends the document defining what a valid verification *is* must itself meet that
definition. Three 2026-07 measurement ratifications amended `MEASUREMENT.md` — whose §138-145
requires a consolidated bundle with evidence hashes and an exact state diff — and none emitted a
receipt. One of them tore a wrapped bullet in half and its own grep-for-my-marker check passed.

**The correct pattern usually already exists nearby.** In `stack_change_guard.py` the identical
`return []` idiom at `:1188` is *not* fail-open, because a second reader independently re-checks
and appends an error; `:1724` does it right for another artifact. The defect is an
inconsistently applied technique, not a missing one — which makes the fix small.

### Sources

- `handoffs/active/numa-topology-cutover-resume-20260730.md` (W6, W7) — 2026-07-31
- `progress/2026-07/2026-07-31.md` — session 18:00–20:00Z, measured reproductions
- `/mnt/raid0/llm/tmp/guard-audit/` — six runnable proof scripts (`prove_failopen.py`, `prove2-5.py`)
- epyc-root `13383c49` — repair of the torn `MEASUREMENT.md` bullet whose verification passed
