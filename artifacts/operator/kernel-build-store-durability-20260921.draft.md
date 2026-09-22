# DRAFT — NOT APPLIED. Prepared 2026-09-21 by an investigation subagent.

Index rows and handoff edits are the owning session's write (CLAUDE.md, ruling (b) 2026-08-16).
Everything below is prepared text plus the exact diff. Nothing here has been applied.

Observed state of the store: `/mnt/raid0/llm/kernels/STORE-STATE.md` (written this session).
Runbook fix: `artifacts/operator/kernel-freeze-runbook-step6-fix-20260921.patch`
(`git apply --check` passes; NOT applied).

---

## No new index row is proposed. The gap already has an owner.

`handoffs/active/autokernel-research-loop.md` (row **INF-06**) already states the condition:

* `:971` — "archive/ exists and is **empty**; no generic candidate install/seal transaction
  uses the layer"
* `:2477-2483` §10.5 — "Incumbent builds are archived, not merely rebuildable… The freeze
  transaction must archive the incumbent's built binaries and linked libraries for N-1 and
  ideally N-2."
* `:3988-3992` Phase **AK7** — "first supervised freeze", five unchecked boxes.

A second row for the same work would be a defect (`index_state.py --check` fails on it).
**Recommendation: amend §10.5 in place with the task list below, and re-seed INF-06's
`Next action`.** Open the alternative only if the operator wants store durability tracked
independently of the stalled AutoKernel loop — in which case ID `INF-77` is free on
`origin/main` and the row slots between `INF-26` (line 38) and `INF-28` (line 39) of
`handoffs/active/inference-research-index.md`.

### Proposed `Next action` re-seed for INF-06 (inference-research-index.md:17)

```diff
-| INF-06 | autokernel research loop | [autokernel-research-loop.md](autokernel-research-loop.md) | Await operator restart decision; preserve stopped v28 and diagnose GLM Q8/synchronization before another campaign | INF-48, EVL-47, INF-64 |
+| INF-06 | autokernel research loop | [autokernel-research-loop.md](autokernel-research-loop.md) | §10.5 KBS-1 — rebuild ef81196d5 with CMAKE_BUILD_RPATH_USE_ORIGIN=ON; the champion cannot be promoted as-is | INF-48, EVL-47, INF-64 |
```

(Only if the operator agrees the durability work now outranks the restart decision; otherwise
leave the row alone and just add the tasks to §10.5.)

### Tasks to append to §10.5 of `autokernel-research-loop.md`

- [ ] **KBS-1 — the champion cannot be promoted as it stands.** Rebuild `ef81196d5`
      (build 10301), both `cpu` and `gpu`, with `-DCMAKE_BUILD_RPATH_USE_ORIGIN=ON`. The
      existing binaries bake an absolute RUNPATH into `/mnt/raid0/llm/tmp/build-*/bin`
      (`readelf -d`), while production carries `$ORIGIN`. A `production/<B>` symlink whose
      target names an absolute lib dir keeps loading the OLD libs — silently. Gate: `readelf -d`
      shows `$ORIGIN`, and `env -u LD_LIBRARY_PATH verify_ggml_linkage.sh` PASSes.
- [ ] **KBS-2 — make runbook step 6 executable.** Apply
      `artifacts/operator/kernel-freeze-runbook-step6-fix-20260921.patch`: materialize
      `kernels/builds/<B>-<YYYYMMDD>-<sha>/bin` + `SHA256SUMS`, prove it standalone, then
      archive the outgoing target by its *resolved* path. Includes the one-time copy exception
      for the first promotion out of the accretive source-tree build dirs.
- [ ] **KBS-3 — decouple archival from promotion.** This is the fix that would have saved
      build 10196. Seal a ratified champion into the store at ratification time; do not wait on
      an operator freeze. The retention policy at `:1498` already says these binaries are
      "Permanent, large… Never deleted" — nothing implements it.
- [ ] **KBS-4 — make the two silent fallbacks fatal.**
      `epyc-orchestrator/scripts/server/orchestrator_stack.py:156-167` and
      `src/registry/stack_priors.py:1930-1954` swallow `KernelPathError` and fall back to a
      CPU-only literal with an empty `LD_LIBRARY_PATH`. That is the exact silent-CPU class the
      store was built to kill (INC-20260731-ggml-linkage-silent-cpu-fallback).
- [ ] **KBS-5 — finish the 2026-08-01 migration.** It missed
      `epyc-orchestrator/scripts/server/gpu_shadow_lane.py:49-50` and
      `orchestration/gpu_shadow_lane_tenancy.yaml:47` (both created 2026-07-28, `cbfe0cde` /
      `e70722f0` — in scope at the time). A GPU lane still launches from a literal, so the
      README's closing warning is accurate, not stale.
- [ ] **KBS-6 — add a store-level gate.** Only `dashboard/server.py:3155-3170` checks the
      symlink→target mapping and it is a read-only projection. `verify_llama_cpp.sh` and
      `verify_speech_kernels.sh` attest the build dirs directly, so nothing enforcing can detect
      a mis-pointed `production/*`.
- [ ] **KBS-7 — AK7 checklist item:** `dashboard/server.py:565-570` hardcodes the 2026-07-31
      resolution targets in `PRODUCTION_STABLE_LINKS`. The first legitimate freeze will show as
      `matches_expected: false`. That table must move with the symlink.
- [ ] **KBS-8 — tmp retention.** Operator decision, OP-33 precedent. Four zero-reference build
      dirs are classified reclaimable in STORE-STATE.md §10; `ak-loop-tree`, the source tree for
      four builds, has *already* been swept. Nothing may be deleted without that decision.

### Belief-kernel wiring (CLAUDE.md requires this be surfaced immediately)

A promotion transaction produces verified findings, so it needs a write-side hook. Proposed:
add a row to the source table in `scripts/vidya/adapters/README.md` for the kernel store
(`kernels/builds/<B>-<date>-<sha>/SHA256SUMS` + provenance → `ClaimTuple`), and a task in
`handoffs/active/vidya-belief-substrate-program.md`. Preparing only — not applied.
