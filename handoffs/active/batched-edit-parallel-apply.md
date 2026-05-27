# Batched Structured Editing + Parallel Apply Fan-out

**Status**: implementation-scoped draft — audit-refined 2026-05-25; production multi-file remediation is now the separate default-off edit transaction. BEP-2/J8 remains useful only as a decision experiment for the legacy structured patchset path, not as the critical remediation gate.
**Created**: 2026-05-25 (via `/research-intake` deep dive of intake-605 Repo Prompt)
**Categories**: agent_architecture, inference_serving, hardware_optimization, tool_implementation
**Source**: intake-605 (Repo Prompt — think-then-act XML edits + parallel sandboxed apply)
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P23
**BEP-2 falsification-harness construction**: [`bep-dcp-falsification-harness.md`](bep-dcp-falsification-harness.md) (2026-05-26 — reviewed / ready to build; safe model-facing task-root override + workload + A/B driver needed to actually run BEP-2; the `_execute_turn` divergence is already wired `ea5f010`)

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
- [ ] **BEP-2 / J8 — CPU latency A/B for the legacy structured patchset path.** Head-to-head bench: batch-edit mode vs interleaved Root LM loop on a coding/edit workload — measure round-trip count, total prefill tokens, end-to-end latency, bundle/context size if DCP is enabled, patch-parse failure rate, apply failure rate, verification pass rate, and quality. This no longer gates practical multi-file coding remediation because the separate `force_mode="edit"` transaction has already solved that blocker. Run BEP-2/J8 only if its answer would change whether the legacy `batch_edit_mode` patchset path is kept, retired, or exposed as a narrow task-class knob. First run an offline replay with already-known patches to estimate deterministic apply overhead; then run inference. *(Inference-gated — prepare commands, user runs; standalone llama-bench only for raw speed per `feedback_speed_verify_via_llama_bench`.)*
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

## Deferred live-wiring spec (build before J8) — the change to make once reviewed

The pure pieces are done + tested on main (merged 2026-05-26): `src/batch_edit.py` (PatchSet/validate/conflict/dependency + `apply_file_patch_to_text`), `src/batch_edit_parse.py` (`parse_patchset_from_model_output` + `BATCH_EDIT_INSTRUCTIONS` rider), flag `batch_edit_mode` (default off). What remains touches the production execution core, so it is specified here for a reviewed landing rather than shipped blind.

**1. BEP-4 runner — `apply_patchset_sandboxed(ps, *, repo_root, current_shas, verify_cmd)` (NEW, e.g. `src/batch_edit_runner.py`).** Pure-of-inference; testable with a temp git repo.
- `validate_patchset(ps)`; `check_stale_base(ps, current_shas)` → refuse stale (return failure manifest, do not apply); `detect_conflicts(ps)` → refuse overlaps.
- **Stage in a sandbox (BEP-5)**: `git worktree add` a scratch worktree at the workspace HEAD (preferred — real git, cheap), or copy touched files into a temp dir. NEVER mutate the live tree here.
- For each `dependency_stages(ps)` stage (files in a stage are independent → may apply concurrently; stages serialize): apply each FilePatch — `create`/`modify` via `apply_file_patch_to_text`, `delete`/`rename` via filesystem ops — into the SANDBOX only.
- **Verify in two layers** (audit #4): per-file syntax/type check, then a **whole-repo** `verify_cmd` (tests/type-check). The accept gate is the whole-repo layer, not the median per-file result.
- Return a structured result: `{applied:[...], failed:[{path, failure_type}], diff, verify_passed, sandbox_path}`. Failure types (audit #5): `parse`, `stale_base`, `conflict`, `apply_error`, `verify_failed`, `undeclared_file`, `over_broad`.
- **Promotion is separate + explicit**: only on `verify_passed` AND accept does the runner copy the sandbox result into the live tree (transactional — all-or-nothing, audit #7). For the **J8 A/B**, no production promotion is needed: apply-to-sandbox + measure (latency / parse-failure / apply-failure / verify-pass / quality) is the whole experiment.

**2. BEP-1 `_execute_turn` divergence (the flag-gated live hook).** ✅ WIRED 2026-05-26 (`ea5f010`), behind `features().batch_edit_mode` (default-off). Implemented in `src/graph/helpers.py` as `_maybe_batch_edit_turn(ctx, role, raw_llm_output)` (self-contained; called right before code extraction): parse patchset → `apply_patchset_sandboxed` (repo_root mirrors `file_mutation._get_project_root`, `verify_fn` = py_compile of staged `.py`) → `promote_sandbox` if `result.ok` → `_finalize_batch_edit` (synthesize terminal FINAL summary). Returns `None` (fall through to REPL) when flag off / no patchset / parse fails; nudge tuple on apply/verify failure (live tree untouched). Prompt rider injected for coder/architect roles only. 7 tests (flag-off zero-change, verify-fail/stale-base no-promote). py_compile is a minimal accept gate; whole-repo test/type-check (audit #4) is a follow-up. *(Original spec template below, for reference.)* In `src/graph/helpers.py:_execute_turn`, after `code = auto_wrap_final(code)` (~line 687):
```python
if features().batch_edit_mode:
    from src.batch_edit_parse import parse_patchset_from_model_output
    try:
        ps = parse_patchset_from_model_output(raw_llm_output)   # None if no ```patchset block
    except ValueError:
        ps = None   # present-but-malformed → nudge to re-emit, or fall back to REPL this turn
    if ps is not None:
        result = apply_patchset_sandboxed(ps, repo_root=..., current_shas=..., verify_cmd=...)
        return _finalize_batch_edit(state, result)   # synthesize FINAL(summary); NO REPL this turn
    # ps is None → fall through to the normal REPL loop (ZERO behavior change when no patchset)
```
The `BATCH_EDIT_INSTRUCTIONS` rider must be injected into the coder/architect system prompt when the flag is on (via `resolve_prompt(..., variant="batch-edit-v1")` or appended in the prompt builder) so the model emits a patchset instead of REPL code.

**3. Safety invariants that MUST hold even behind the flag** (mitigation policy): default-off; **sandbox-before-disk** — production files untouched until whole-repo verify passes AND accept; stale-base rejection; fall-back-to-REPL on `parse=None`; whole-repo verify is the accept gate; granular accept/reject is review UX over a coherent staged diff, never piecemeal mutation of production files.

## Post-result conditional workflow + mitigation (BEP-2 / bulk-inference J8)

J8 is no longer the first critical gate for multi-file coding completion. The direct one-shot ablation and `force_mode="edit"` transaction already proved the practical diagnosis: the blocker was the read->edit->FINAL REPL/BEP protocol, not Qwen3.6 coding capability. Keep J8 as a separate decision experiment for the older structured patchset path:

- **Run J8 if** the result would change whether `batch_edit_mode` is kept, retired, or exposed as a narrow task-class/autopilot knob; if full-file edit transactions become too expensive for large repositories; if structured-patch provenance matters; or if BEP-3 needs task-class evidence.
- **Defer J8 if** the goal is routine coding completion reliability or near-term rollout of the already-built edit transaction. In that case J7, J9, J11, and passive J13-J15 are higher-leverage inference-window consumers.
- ✅ batch cuts end-to-end latency ≥15% AND quality within −1pp AND parse-failure ≤5% AND apply-failure ≤2% → proceed to **BEP-3** (autopilot task-class knob); keep flag available, default-off until BEP-3 localizes where batch wins.
- ⚠️ latency win but quality −1..−3pp OR parse/apply failures 5–15% → do NOT promote; harden BEP-1 prompt/parser; flag stays off; re-run only if structured-patch provenance or full-file-cost concerns remain material.
- ❌ no latency win OR quality < −3pp OR failures >15% → retire the legacy batch-vs-interleaved path; record NEGATIVE here + in intake-605. This does **not** invalidate the shipped edit-transaction remediation.

Mitigation/rollback: flag-off is instant rollback; sandbox isolation means a bad patch never reaches production; on any parse/validate failure the turn falls back to the existing REPL loop (no regression). Operator decision tree mirrored in [`bulk-inference-campaign.md`](bulk-inference-campaign.md) Package J § "Per-gate conditional workflows".
