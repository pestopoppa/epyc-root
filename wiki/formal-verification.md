# Formal Verification

**Category**: `formal_verification`
**Confidence**: verified
**Last compiled**: 2026-09-08 (the SC69-73 audit survivors closed as verifications, not checks — SC61's `attested` binding producer landed and all five defects were fixed under the placement rule that made them findings, `5d7f14be`; plus the RC-12 16-threshold audit naming three selection-on-the-certification-sample VIOLATIONS; earlier: 2026-09-07, the belief kernel's own grading-implementation audit — 5 survivors from a mutation audit, led by a verifier grading Attested on a digest never checked; earlier: RustEvo2 verification gate)
**Sources**: 15 documents

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
- [Lean proving pipeline handoff](/workspace/handoffs/completed/lean-proving-pipeline.md) -- Two-tier architecture design, work items S1-S5, infrastructure requirements
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

## Compiled Update — 2026-09-07 (incremental): a machine-checked artifact certifies the proposition the CHECKER decided, not the claim it is cited for

**Confidence: verified** (primary-source dive of arXiv:2605.28365 v1, 2026-09-07; the headline
number is a projection and is scoped as such below).

A kernel-checked proof is the strongest evidence a pipeline can emit, and it still says nothing
about the question a reader is asking. The certificate covers **the proposition the checker
decided**; nothing in the machinery binds that proposition to the informal claim someone later
cites the artifact for. The source states its own limit explicitly — the risk certificate "does not
certify individual mathematical truth, does not assign a label to unresolved answer classes, and
does not extend to fallback predictions" (`intake-1307#05`), and statement faithfulness is outside
it entirely.

**The gap is measured, in one pipeline, and it is large.** Of 314 proved artifacts, an automated
rational-evaluation check classes 40.1% genuine / 33.4% structural / 22.9% trivial / 2.5%
spurious — so **73.6% "non-trivial and correct"**. A manual faithfulness audit reweighted by those
same population frequencies puts faithfulness at **~43%** (`intake-1307#00`, `intake-1307#01`). A
wrong answer class is proved in 8% of problems.

**How that 43% may and may not be used.** It is a **reweighted projection, not a count**: the
per-category rates come from a **45-example, single-annotator** audit whose only reported cells are
6/6 and 0/6, and the source itself labels it "diagnostic error analysis, not benchmark-grade
annotation". Its denominator is ambiguous in the source and never reconciled — 105 proved problems,
140 proved classes and 314 proved artifacts are all reachable from the phrase "proved statements"
(our record pins the 314). An independent measurement on a different population, domain and
formalizer strength puts the compile-versus-faithfulness gap at 3.0–29.0 points. So: **admissible as
an existence proof that the gap between "the checker said yes" and "the statement means what was
intended" is large in at least one real pipeline — never as a rate**, and never as a general
autoformalization faithfulness number.

**There is no LLM judge in that paper.** Despite "Lean-as-judge" in the title, **the judge is
Lean**; the human comparison runs against a symbolic rational-arithmetic checker measuring a
different construct, and the work yields no judge-versus-human agreement rate at all
(`intake-1307#02`). Filing it as evidence about LLM-as-judge reliability is a category error.

Two further findings transfer directly to any verifier-gated pipeline:

- **Formal-judge reliability is coverage-dependent — a cliff, not a slope.** The top proved answer
  class matches the reference **96%** of the time at high proved coverage and **20%** at low
  coverage (`intake-1307#03`). A reliability figure quoted without its coverage regime is
  unreadable.
- **Absence of proof is a heterogeneous event, not a negative label.** Of 1,403 answer-class
  observations: 741 never formalized, 251 ill-typed, 271 typechecked-but-unproved, 140 proved, 0
  timed out (`intake-1307#04`). The bottleneck sits entirely **before** proof search, so treating
  "unproved" as "false" collapses four different failure causes into one wrong label.

**The rule for our records.** A verifier verdict must be stored next to **the proposition it
decided**, not next to the claim it was run in support of; anything else lets a green check migrate
onto a claim nobody checked. This is the same two-plane split the belief substrate already
enforces — machine-checked correctness on one axis, an accruing trust score that gates nothing on
the other — and it is why `decided_proposition` is filed (SC57) as a field of the verifier-class
adapter contract rather than an optional provenance nicety, with SC56 making the binding a
precondition for any grade above `Judged`. The number entered our corpus through a one-hop
citation that transcribed it accurately but stripped every scope qualifier (`intake-1297#record`),
which is exactly the failure the storage rule prevents.

### Sources

- [intake-1307#record](https://arxiv.org/abs/2605.28365) — *Risk-Controlled Lean-as-Judge for
  Natural-Language Mathematical Reasoning*, credibility 6/6, dive-verified 2026-09-07: the
  certificate-scope limitation, the 73.6%/43% pair with its audit caveats, the coverage cliff, and
  the unformalized/ill-typed/unproved status split.
- [intake-1297#record](https://arxiv.org/abs/2608.28433) — the citing paper through which the 43% reached
  our records, quoted verbatim and stripped of scope.
- [`vidya-belief-substrate-program.md`](../handoffs/active/vidya-belief-substrate-program.md) —
  SC56–SC60, the statement-binding rows this finding funded.
- [`docs/design/vidya-pilot-spec.md`](../docs/design/vidya-pilot-spec.md) §4.1/§4.7 — the two-plane
  split and the one-ladder-per-source-class adapter contract.


## Compiled Update — 2026-09-07: the belief kernel's own T-axis top grade was reachable without verification

The prior entry on this page established the rule — *"a verifier verdict must be stored next to the
proposition it decided"* — as an EXTERNAL finding about a citing paper's number. A same-day mutation
audit of the belief kernel itself (`scripts/vidya/`, 62 mutations, 32 survivors over the portion it
reached) found the kernel's own implementation violates an adjacent version of that rule, at the top
of its own trust ladder.

**`Attested` — the highest grade on the T-axis of the kernel's `Q x T` lattice — never verifies the
digest it is named after.** `claim_tuple.py` length-checks `attestation_sha256` (must be 64 hex
characters) and branches on its mere presence; `hashlib` occurs zero times in the file. A tuple with
`attestation_path="MEASUREMENT.md"` and `attestation_sha256="0"*64` grades **Witnessed/Attested** —
the top of both axes of the lattice, on a digest of nothing. This is not fixed by adding a `hashlib`
call inside the grading function: `grade()` is pure and hashing is I/O, so the verification has to
happen at the adapter/write boundary, with the result carried in the tuple — the placement decision
comes before the code, which is why this is filed (SC69, P1) rather than patched inline.

Four further survivors share the same shape — **a presence check standing in for a verification** —
at different points in the same kernel: `claim_depends_on` (SC70) registers a dependency edge
without registering the claim it points at, so a dependent can silently have no belief to alert on;
an obligation with an EMPTY required-set reports itself satisfied (SC71) — the same
absence-filled-not-recorded defect this wave's benchmark-methodology page found three times
elsewhere, here inside the pilot spec's own §4.7 carrier; a gate can count one source as
corroboration twice, and a subject field is validated for presence rather than well-formedness one
layer below where the `Attested` defect bites (SC72); and `ledger.verify()` returns clean on an
empty or deleted ledger — the strongest possible reading of "chain=OK" is produced by having no
chain at all (SC73), the fail-open shape named elsewhere in this project's own standing feedback
record.

**Two things worth carrying forward, not just the finding.** First, the audit that found these five
also found three weaknesses in a test written the SAME DAY by the same session that landed SC56-60
— an assertion character-identical to its neighbor, a negation four different values satisfied, and
a whitespace-brittle source grep — a reminder that a same-day fix and its test are not exempt from
the review that finds defects in everything older. Second, the audit's own coverage is explicitly
bounded: it never reached `scripts/vidya/adapters/`, `canonical.py`, `checkpoint.py`, `evaluate.py`,
`cli.py`, `citation_gate.py`, `correction_queue.py`, `machine_anchor.py`, or roughly 29 adapter test
files. 32 surviving mutations is the measured rate over the portion actually reached; the unreached
portion carries no rate at all and must not be read as clean by omission.

### Sources

- [`vidya-belief-substrate-program.md`](../handoffs/active/vidya-belief-substrate-program.md) —
  SC69 through SC73, each with file:line, the demonstrated grade-inflation input, and the stated
  reason it was filed rather than fixed inline.
- `scripts/vidya/claim_tuple.py` — independently confirmed 2026-09-07: `hashlib` occurs 0 times in
  the file; `attestation_sha256` is length-checked at one site and presence-checked at another.
- `scripts/vidya/fold.py:409`, `scripts/vidya/projection.py:124`/`:288` — the two P1s the same audit
  found AND this wave fixed (a retraction with an empty target matching every id-less frame; a
  review-cause reporter naming only the first of two true reasons), each with a paired mutation
  test, kept here as the contrast case: same audit, same day, two fixed inline and five filed.
- [`2026-09-07-prove2me-intake.md`](../progress/2026-09/2026-09-07-prove2me-intake.md) — the
  session record, including the independent re-verification of the `hashlib` claim before this page
  was written.

## Compiled Update — 2026-09-08: the five audit survivors were fixed as verifications, not checks — and SC61 gave the `attested` binding its producer

**Confidence: verified** (commit `5d7f14be`, 43 files, suite 899 → 967; every fix red-first and
mutation-pinned; closure text in the program handoff rows).

The SC69–SC73 block above was filed — not fixed — because each defect's remedy carried a placement
decision the authoring session refused to make silently. The 2026-09-08 closure executed those
decisions, and the through-line is that **no fix moved I/O into `grade()`**: the purity rule that
made SC69 unfixable-inline is also the rule every closure honours.

- **SC69 (P1) closed — `Attested` now means the digest was recomputed.** Placement decision
  executed as filed: `grade()` stays pure, verification happens at the adapter/write boundary, and
  the result is CARRIED in the tuple as the new field `attestation_verified: bool | None` (`None` =
  never checked, can never reach `Attested`; `True` = digest recomputed against the artifact bytes
  at write time and matched; an explicit `False` is refused — an admitted mismatch asserts two
  contradictory facts). `claim_tuple.verify_attestation()` provides the I/O for boundaries that want
  it. Ten wired producers carry a real recompute (sealed_manifest, measurement_record,
  autopilot_journal, autokernel corpus/evaluation_event/property, memento_lora, pareval,
  chat_template_ab, contention_matrix, eval_tower_band). The REAL sealed corpus and REAL autopilot
  writer keep `Attested` through genuine recomputation; receipt rows whose digest cannot be
  re-derived from an artifact in hand grade honestly `Witnessed/Anchored` ("attestation sha256 never
  verified against the artifact's bytes") until their write path implements its own recompute.
  Mutation-pinned: `"0"*64` no longer reaches `Attested`. 12 red-first tests.
- **SC70 closed — a `depends_on` edge now creates the claim it points at.** `fold.py` `FT_DEPENDS`
  canonicalizes and `claims.add`s the dependent, so a dependent can no longer exist with no belief
  to alert on. Red-first: a dependent seen only via the edge had no belief; its withdrawal alerts
  vanished; discharge classified the entry discharged while the dependent never existed.
  3 tests (`test_vidya_depends_on_fold.py`).
- **SC71 closed — an obligation that requires nothing is refused.** `impact.py` `_evaluate`
  raises `ValueError` on an empty required-set under `all`/`any` ("an obligation that requires
  nothing reads identical to one whose requirements all passed"). Red-first: `{"all": []}` graded
  SATISFIED before; 4/5 tests failed first; a non-empty mutation companion stays green.
- **SC72 closed — corroboration can no longer be manufactured, and a subject digest must be a
  digest.** (a) Fold keys naming no source map to one shared `UNNAMED_SOURCE_KEY`, not a
  pseudo-source per evidence label; (b) the gate's disjoint-supports fallback counts an unaccounted
  belief as ONE unnamed source, never its labels — a single source can no longer corroborate twice;
  (c) `frames.validate_frame` refuses any subject digest that is not exactly `{sha256: 64-hex}` and
  any unnamed subject, closing the digest-shaped-string-is-not-a-digest hole one layer below SC69.
  One existing test had encoded the defect (two source-less paths satisfied a 2-source policy);
  its fixture now names two real sources and a mutation pins that unnamed paths abstain.
  11 red-first tests.
- **SC73 closed — a verifier that passes on the absence of the thing it verifies is no longer
  possible.** `ledger.verify(expected_count=None)` reports problems for a missing/empty ledger and
  flags a ledger shorter than a declared count; `cli.py cmd_verify` passes the newest published
  checkpoint tree size as the declared count, so a ledger truncated to a consistent prefix now
  fails chain (same-length rewrites remain the L1 case). Live-ledger smoke after the fix:
  frontier **13,141**, chain OK, checkpoints OK. 5 red-first tests (`test_ledger_empty_verify.py`).
- **SC61 closed — SC56's `attested` binding finally has a producer.** New
  `scripts/vidya/statement_binding.py` + `cli.py binding-candidates`/`binding-emit`: frame type
  `epyc.vidya/frame/claim_statement_binding/v1` asserts `{claim_id, decided_proposition}` verbatim
  with human reviewer + worksheet digest in provenance, parallel to `claim_alias/v1`. Candidates
  are proposed only where a binding is missing — identity-eligible pairs are never proposed, because
  the machine needs no human — and worksheet rows stay `pending` until a human `follows` with a
  named reviewer. The fold pass refuses a false attestation (a `binding_ref` must resolve to a LIVE
  binding naming the SAME claim and the SAME proposition under `claim_tuple`'s own normalization,
  else `FoldError`) and refuses a binding naming a claim absent from the ledger (it cannot create a
  belief — SC70's shape one level up); retraction withdraws; resolved bindings surface on
  `FoldResult.statement_bindings`. 20 unit tests + 1 CLI e2e.

**The wave's own test hygiene is the meta-finding.** All six closures were red-first with a
mutation companion that reverts the fix — the catalogue's one-line remedy ("mutate the guard and
confirm the check FAILS") executed as a standing discipline, including against the same-day tests
the audit had already shown to be fallible. The five defects shared one shape — *a presence check
standing in for a verification* — and each closure replaced presence with either a carried
verification result (SC69), a created object (SC70), a refusal (SC71, SC72c), or a structural
impossibility (SC73).

### The RC-12 16-threshold audit: three thresholds chosen on the sample that certifies them

**Confidence: verified** (audit table in `progress/2026-09/2026-09-08.md`; every `file:line`
re-read at audit time, because the ~110-threshold subagent report it was meant to absorb is **not
recoverable from the tree** — an unrecoverable subagent report is not evidence, and the
re-enumeration was read-verified per line).

RC-12 (intake-1307) asked of every reviewer/gate threshold whether it was chosen on a split
independent of the one used to certify it — the source's own point being that the same data
certifies at materially different risk levels under a grid search versus a threshold picked on an
independent dev split. The audit (16 thresholds) found:

- **VIOLATION — `rubric_pass_threshold` default 0.60** (`eval_tower.py:4334-4335`): unknown
  derivation; converts rubric aggregates into per-question `correct` feeding the SafetyGate quality
  axis. Remedy: derive from a rubric-vs-gold slice, or make `scoring_config` name threshold +
  rationale per suite (mirroring `gate_verdict`'s mandatory rationale); observation-only until then.
- **VIOLATION — the PII-hook exemption surface** (`scripts/hooks/pii_precommit.sh:93-295`): tuned
  on observed over-blocks with fixture rows added in the same commits that certify it — catalogue
  **face 15, the oracle endorses the defect**. Mitigation exists (the evaluator prints same-sample
  provenance); numbers stay observation-only, and the "held-out" label at
  `candidate_eval_gate.sh:26` was a wording violation, relabelled "same-sample PII fixture
  validation (observation-only)".
- **VIOLATION (low) — `DEFAULT_BASELINE_QUALITY=1.16`** (`safety_gate.py:365`): a silent numeric
  fallback of undocumented derivation; prefer fail-closed without a measured baseline.
- **Flagged — `review_ledger.py:563-564` FA/FR tolerances**: self-declared placeholders
  (`thresholds_are_placeholders: true`), library-only; re-derive on a held-out near-miss slice
  before any live wiring.
- **OK class**: sequential-verdict e-process policy (protocol-derived), SafetyGate tuning constants
  (incident-derived, continuously gated), `gate_verdict` (design is the anti-VIOLATION),
  CITATION_THRESHOLD_N=20, vidya policy floors, repo-readiness 80% (external rubric). One
  previously-filed violation (impact.py ordinal drift) was already fixed (`ae8ab82b`) — see the
  catalogue mapping below.

Remedies split by gate: the `rubric_threshold_source` mechanism, the baseline-load loudness fix and
the relabel landed 2026-09-08 (zero-inference; compiled on
[benchmark-methodology](benchmark-methodology.md)); the hard-refusal half and the reviewer-
tolerance re-derivation did NOT execute — they are inference/cadence-gated on RC-8 near-miss shadow
data and the RC-6a/P-REV-1 operator PR (MEASUREMENT.md is human-amendment-only), and are recorded
as such rather than lost.

### The verification-failure catalogue mapping — where these instances land among the fifteen faces

The audit and the SC69-73 wave both map onto the standing catalogue (`docs/guides/agent-workflows/
verification-failure-catalogue.md`), which is what makes the two records one theme:

- **SC73 and SC71** are the catalogue's **face 1 family** (empty input — the check cannot fail)
  in fail-open form: an empty ledger passes as "chain=OK", an empty required-set reads identical to
  a satisfied one. Both were invisible to mutation testing under the catalogue's own caveat —
  *mutate while the input is genuinely empty and the empty set satisfies the check* — which is why
  SC73's fix REQUIRES a non-empty frontier and a declared expected count (assert the input is
  non-empty first, then mutate).
- **SC69 and SC72** are **face 4** (an assertion pins a spelling, not a property): a 64-hex length
  check and a presence branch certified a digest nobody recomputed — at two layers (tuple grading
  and frame subject validation) of the same defect.
- **Impact.py ordinal drift** (found by the RC-12 audit, fixed `ae8ab82b`) is face 4's
  time-variant: the literal `g.t >= 2` was correct when written, then `MachineLocated` was inserted
  at ordinal 2 and the check silently began admitting machine-located spans while its docstring
  still said "anchored" — an assertion that was true when written and the world moved.
- **The PII-hook exemption surface** is **face 15** (the oracle endorses the defect): fixture rows
  added in the same commits that certified the over-blocking make the green suite argue against its
  own repair.
- SC69's own repair is the catalogue's remedy executed end-to-end: the `"0"*64` mutation companion
  is the guard that now fails if the fix regresses.

### Source References (2026-09-08)

- [`vidya-belief-substrate-program.md`](../handoffs/active/vidya-belief-substrate-program.md) — the
  SC61/SC69-73 closure text (placement decisions, carried-field design, mutation companions,
  live-ledger smoke at frontier 13,141), and the SC47/48/SC56-60 context rows.
- [`reviewer-calibration-accounting.md`](../handoffs/active/reviewer-calibration-accounting.md) —
  RC-11/RC-12: the audit's origin in intake-1307's selection-on-the-certification-sample finding,
  the 16-threshold enumeration, the violation classes and the OK class.
- [`progress/2026-09/2026-09-08.md`](../progress/2026-09/2026-09-08.md) — the full 16-threshold
  table with per-threshold file:line and the wave-2 remedy execution (mechanism half, loudness,
  relabel; recorded-not-executed halves).
- [`2026-09-07-prove2me-intake.md`](../progress/2026-09/2026-09-07-prove2me-intake.md) — the SC61
  filing (the `attested` half of SC56 was inert with no producer), and the wave's ratified doctrine
  amendments (three measurement rules on `MEASUREMENT_POLICY.md`, compiled on
  [benchmark-methodology](benchmark-methodology.md); the fan-out amendment on
  [agent-architecture](agent-architecture.md)).
- [`docs/guides/agent-workflows/verification-failure-catalogue.md`](../docs/guides/agent-workflows/verification-failure-catalogue.md)
  — the fifteen faces, for the face-1 / face-4 / face-15 mappings above.
