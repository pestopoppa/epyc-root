# Batched Structured Editing + Parallel Apply Fan-out

**Status**: implementation-scoped draft — audit-refined 2026-05-25; BEP-2 remains the falsification gate before broader build-out
**Created**: 2026-05-25 (via `/research-intake` deep dive of intake-605 Repo Prompt)
**Categories**: agent_architecture, inference_serving, hardware_optimization, tool_implementation
**Source**: intake-605 (Repo Prompt — think-then-act XML edits + parallel sandboxed apply)
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P23

## Objective

Two coupled, CPU-relevant levers borrowed from Repo Prompt's edit pipeline:
1. **Think-then-act batch editing** — let a heavy role spend its full reasoning budget then emit ONE complete structured edit/patch set, instead of interleaving many REPL tool-call round-trips into the reasoning chain.
2. **Parallel apply fan-out** — fan the per-file changes from that edit set out to cheap workers that apply (and optionally verify) them concurrently across NUMA quarters.

## Strategic frame — why this is sharp on EPYC

- Our Root LM **interleaves** REPL tool calls into reasoning. Each round-trip is a fresh **prefill + decode** — and on EPYC 9655 decode is BW-bound and prefill is pure latency. N interleaved tool calls ≈ N round-trips of overhead.
- RP deliberately makes the reasoner **think to completion, then emit one structured XML edit set** (it exploits GPT-5 Pro's parallel-instance behavior; for us the motivation is round-trip cost, not a model quirk). Fewer round-trips = less cumulative prefill/decode overhead — **a plausibly real latency lever, and cheaply falsifiable.**
- RP then **fans the per-file edits out to cheap CLI agents applying in parallel in a sandbox**. This maps directly onto our proven NUMA concurrency strength: **32×6t concurrent split = +44–58% aggregate** (`project_concurrent_split_throughput`). "Heavy model plans → N cheap workers apply concurrently" is architecturally native to us.

## What we already have

- **Root LM REPL loop** — interleaved code-gen → execute → observe (the baseline to beat). `epyc-orchestrator/src/README.md` Root LM pattern.
- **Escalation chain** (worker→coder→architect) — quality escalation, NOT a plan/apply split.
- **NUMA concurrency** — 32×6t split, +44–58% aggregate, zero code change (orchestrator config). The substrate for fan-out.
- **Meta-Harness Tier 2** — structured code mutation with `ast.parse()` validation + git-commit-before + sandbox discipline, but limited to a 4-file allowlist — a partial precedent for structured-edit application + safety gating.
- **TOON encoder** — structured-payload encoding for the edit set.

## RP mechanism to mine

- **Think-then-act**: reasoner emits one **XML edit set** (per-file change list) after reasoning, no mid-reasoning tool calls. RP parses XML → per-file changes.
- **Parallel apply**: parsed per-file changes implemented in parallel by cheap agents in a sandbox; **reviewable diffs, machine-readable patches, sandbox-before-disk, granular accept/reject** (90-min tool timeout tolerates long reasoning).

## Proposed tasks (implementation-grade after audit)

- [ ] **BEP-1 — Batch-edit mode (think-then-act).** Add a coder/architect mode that produces a complete structured patch set (per-file hunks) in one shot after a bounded evidence-gathering phase, with no edit/apply tool calls interleaved through the reasoning chain. Define the patch schema as deterministic data, not free-form XML-only prose: `base_repo_sha`, per-file `path`, `base_content_sha256`, `operation`, hunks with line anchors or unified-diff body, expected postconditions, and declared cross-file dependencies. Reuse TOON for compact transport if useful, but validate into a typed Python object before touching disk. Default-off feature flag.
- [ ] **BEP-2 — CPU latency A/B (the cheap-to-falsify core).** Head-to-head bench: batch-edit mode vs interleaved Root LM loop on a coding/edit workload — measure round-trip count, total prefill tokens, end-to-end latency, bundle/context size if DCP is enabled, patch-parse failure rate, apply failure rate, verification pass rate, and quality. **This is the falsification gate**; if batch mode doesn't cut latency at equal quality, stop. First run an offline replay with already-known patches to estimate deterministic apply overhead; then run inference. *(Inference-gated — prepare commands, user runs; standalone llama-bench only for raw speed per `feedback_speed_verify_via_llama_bench`.)*
- [ ] **BEP-3 — Autopilot search-space knob.** If BEP-2 is positive, expose batch-vs-interleaved as a StructuralLab boolean (or per-role/per-task-class knob) so autopilot can find where each wins. Wires into autopilot-continuous-optimization search space. The knob must be task-class aware because run-test-iterate tasks may require interleaving while mechanical multi-file edits may benefit from batching.
- [ ] **BEP-4 — Parallel apply fan-out.** Given a BEP-1 patch set, first try deterministic patch application in parallel by file/process with no additional LM calls. Only if deterministic apply fails should an optional cheap-worker repair lane run, and that lane must be explicitly inference-gated. Collect per-file results; surface a combined reviewable diff plus a machine-readable failure manifest. Reuse the 32×6t concurrent-split harness for CPU parallelism, but preserve a dependency graph: files with declared cross-file ordering constraints or generated-code dependencies must serialize within their group.
- [ ] **BEP-5 — Sandbox-before-disk + granular accept/reject (general).** Generalize Meta-Harness Tier-2's git-commit-before / ast-validate discipline beyond the 4-file allowlist into a general "stage in sandbox/worktree → reviewable diff → independent verify → accept/reject per file or hunk → commit" apply path. Safety-gated — design most carefully (autonomous general code edits). Use base-hash preconditions to reject stale patches, forbid edits outside the declared scope, and always run a whole-repo verification pass after per-file verification because cross-file errors are invisible to isolated checks.

## Open questions

- Does think-then-act hurt quality on tasks that genuinely need feedback mid-reasoning (run-test-iterate)? Likely task-dependent → hence the autopilot knob (BEP-3), not a global switch.
- Patch-application failure handling: if a fanned-out apply fails verification, retry that file only, or re-plan the whole set?
- BEP-4 vs `feedback_no_concurrent_inference` (no unapproved concurrent inference on EPYC): fan-out apply uses cheap workers concurrently — must respect the per-run-approval rule; design as opt-in, single-user-aware.
- Verification-sensor independence (ties to intake-607 §3.4.4): the per-file verify in BEP-4 should be an independent oracle (tests / type-check), not the applying model grading itself.

## Audit refinements / missed gaps

1. **Deterministic apply should come before agent fan-out.** RP's "cheap agents apply" pattern is useful, but on our stack the safest and fastest first implementation is a typed patch parser plus deterministic applier. LM repair should be a fallback, not the baseline, otherwise BEP adds both inference risk and nondeterminism.
2. **Structured patch schema needs stale-base protection.** Every file patch must name the base hash it was planned against. If the file changed since planning, reject or re-plan that file; do not fuzzy-apply across unknown edits.
3. **Parallelism is by dependency component, not blindly by file.** Independent files can apply concurrently, but migrations, public API changes, generated code, import graph edits, and test fixture updates can require ordering. The patch schema should let the planner declare dependencies; the applier should also infer obvious conflicts such as two hunks touching the same file.
4. **Verification must have two layers.** Per-file syntax/type checks catch cheap failures early; whole-repo tests/type checks catch cross-file regressions. The final accept gate should be based on the whole-repo layer, not the median per-file result.
5. **Quality failure is not only "patch did not apply."** Track parse failures, over-broad diffs, undeclared file edits, generated-file churn, formatter-only noise, and "passes tests but violates requested behavior." These become BSV behavior-signature inputs.
6. **BEP and DCP should share manifests.** A batch edit planned from a DCP bundle should record the bundle ID and omitted-context manifest. If the patch touches a file that was only `codemap_only` or excluded, flag the plan as under-evidenced before apply.
7. **Rollback should be transactional.** Stage in a worktree or sandbox; never partially copy successful files into the main tree while failed files remain unresolved. Granular accept/reject is a review UX over a coherent staged diff, not piecemeal mutation of production files.

## Dependencies / cross-cutting

- **delegation-context-preassembly** (sibling) — a pre-assembled bundle feeds a clean batch edit.
- **autopilot-continuous-optimization** — BEP-3 knob; BEP-2 latency/reliability objective.
- **NUMA concurrency** (`project_concurrent_split_throughput`) — BEP-4 substrate.
- **meta-harness-optimization** — Tier-2 structured-mutation precedent → BEP-5 generalization base.
- Honors `feedback_no_concurrent_inference`, `feedback_speed_verify_via_llama_bench`.

## Key file locations (targets)

- `epyc-orchestrator/src/README.md` Root LM loop / `src/orchestration/` — batch-edit mode (BEP-1).
- `epyc-orchestrator/scripts/autopilot/species/` (StructuralLab) — BEP-3 knob.
- 32×6t concurrent-split config (`orchestrator_stack.py`) — BEP-4 substrate.
- Meta-Harness Tier-2 mutation path — BEP-5 generalization base.

## Reporting

Update this handoff + routing-index P23 after each BEP task; persist BEP-2 bench results incrementally per `feedback_incremental_persistence`.
