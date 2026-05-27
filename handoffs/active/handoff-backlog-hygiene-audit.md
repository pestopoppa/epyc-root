---
title: Handoff backlog hygiene audit (archive-or-dereference aging handoffs)
status: active — first archive/dereference pass executed 2026-05-27
created: 2026-05-27
owners: unassigned (operator to assign)
priority: LOW (housekeeping; non-inference; perform as a wrap-up action)
related:
  - handoffs/completed/bulk-inference-2026-04-packages.md   # worked example of the pass
  - handoffs/completed/cross-role-nway-contention-matrix.md # worked example (archive)
  - .claude/commands/wrap-up.md                             # Step 3 "Index hygiene" = the procedure to follow
---

# Handoff backlog hygiene audit

## Problem

`handoffs/active/` holds ~101 handoffs; `scripts/validate/check_handoff_freshness.sh` flagged **56 aging** (>14d) and 0 stale (>30d) as of 2026-05-27. Many are likely complete or overtaken but remain inline + index-referenced. Per the operator's index-discipline rule (memory `feedback_index_tracks_outstanding_only`), indices should track **outstanding TODOs only**; completed work should be archived (if genuinely done) or its index entry dereferenced/trimmed (if open work remains).

The **bulk-inference campaign orbit already received this treatment** on 2026-05-27 (epyc-root commit `2b63ae1`: campaign handoff 1183→452 lines; master-index `#53` cell 6932→900 chars; `cross-role-nway-contention-matrix` archived). This handoff extends the same pass to the rest of the aging tree.

## Scope

All aging handoffs in `handoffs/active/` except the bulk-inference orbit elements that were already pruned or rewritten on 2026-05-27 (`bulk-inference-campaign`, `cross-role-nway-contention-matrix`). Active bulk-inference siblings such as `within-role-placement-state-machine` and `bep-dcp-falsification-harness` remain live work and should only be excluded when they are not part of the current aging set, not because they are "done." Non-inference housekeeping — **no benches, no host-quiet window required** (`feedback_no_concurrent_inference` does not gate this).

## Method (this is a WRAP-UP action — surface before pruning)

1. `bash scripts/validate/check_handoff_freshness.sh` → get the current aging list.
2. For each aging handoff, classify against **actual code / tests / commits** — verify, don't trust prose (many predate the 2026-02-25 monorepo split and reference stale paths per CLAUDE.md):
   - **Genuinely complete** → `git mv` to `handoffs/completed/` + add a completion banner + selectively fix relative `.md` links affected by the move (`../active/`, `../completed/`, or unchanged explicit paths as appropriate); remove or dereference its master-index / domain-index reference.
   - **Open work remains** → keep active; trim its index entry to the open items only; move any chronology into the progress log.
3. Follow `.claude/commands/wrap-up.md` Step 3 "Index hygiene": **archive, never delete**; **list everything pruned under an `## Index pruning` heading** for operator review before it leaves the active tree.
4. Update `handoffs/active/master-handoff-index.md` (registry + priority queue) and the 6 domain sub-indices.

## Constraints

- Index changes require operator visibility — do this **as a wrap-up** and surface the prune list; do NOT prune ad-hoc mid-work.
- Do NOT archive anything with open work. When in doubt, dereference/trim rather than archive.
- Preserve git history (`git mv`); fix relative links after moves; keep historical progress-log references intact (append-only).

## Deliverable

Leaner `handoffs/active/` tree; master-index tracking outstanding TODOs only; a prune list reported for operator review.

## First pass executed 2026-05-27

Freshness recheck at execution start: **56 aging, 0 stale**.

## Index pruning

- `qwen36-production-upgrade.md` → moved to `handoffs/completed/`
- `qwen35-122b-a10b-arch-class-probe.md` → moved to `handoffs/completed/`
- `llama-cpp-fork-rebase.md` → moved to `handoffs/completed/`
- `numa-mirror-integration.md` → moved to `handoffs/completed/`
- `cpu-hierarchical-barrier.md` → moved to `handoffs/completed/`
- `cpu-openmp-runtime-scheduling-matrix.md` → moved to `handoffs/completed/`
- `cpu-dynamic-moe-load-balancing.md` → moved to `handoffs/completed/`
- `cpu-context-regime-coverage.md` → moved to `handoffs/completed/`
- `cpu-uncore-fabric-attribution.md` → moved to `handoffs/completed/`

## Second pass executed 2026-05-27 (evening)

Freshness recheck: **37 aging, 0 stale** (down from 56 at first pass).

Classification by 4 parallel Explore agents verifying against actual code/tests/commits. After operator review, **all 4 ARCHIVE candidates were rejected** — three are load-bearing reference anchors in other active handoffs, and the fourth (launcher) had unmet acceptance criteria. The audit method itself was right; the agents' verdicts conflated "code work finished" with "handoff has no remaining role."

### EXCLUDED FROM ARCHIVE (4) — initial recommendations overturned 2026-05-27

| Handoff | Audit verdict | Why rejected |
|---|---|---|
| `cpu-optimization-thesis-pause-2026-04-26.md` | ARCHIVE | Load-bearing reference in `cpu-benchmark-rigor-and-revalidation`, `cpu-kernel-env-flags-inventory`, `nps-reboot-runbook`, `cpu-inference-optimization-index` — anchors the Phase I→J→K→L→M track plan. Archive would break 4 active handoffs' references. |
| `moe-dynamic-expert-selection.md` | ARCHIVE | Load-bearing reference in `moe-spec-cpu-spec-dec-integration` (Phase 3 follow-up) and `cpu-shape-specialized-gemv-decode`. Phase 0 NEGATIVE is a finding, but the handoff is a reference anchor. |
| `outer-coordinator-learned-head.md` | ARCHIVE | Explicitly gated scoping per master-index #28 and routing-index P19.8. "Deferred pending TR/DAR/LRC Phase 4" ≠ "complete/dead." |
| `launcher-numa-mode-gating.md` | ARCHIVE | Original acceptance criterion (`default --numa-mode quarter`) NOT MET — flag landed but default is `both`, so the 1.5× CPU oversubscription footgun still ships. Restored to active 2026-05-27 evening. |

**Audit-method correction**: any future ARCHIVE recommendation must verify (a) the handoff is not a reference target in another active handoff, AND (b) all acceptance criteria are met as written, not just the underlying code path being landed.

### DEREFERENCE (4) — trim master-index entries to outstanding TODOs only

- `numa-prefill-decode-disaggregation.md` — only Phase 0 xGMI BW falsification test remains; Tier 2b counter-evidence noted.
- `wdata-aware-mul-mat-coalescing-design.md` — Phase 0 design complete with honest NEGATIVE verdict (2-7% gain at 260-410 LOC + ABI cost); trim to decision statement only.
- `qwen36-benchmark-fixes.md` — Qwen3.6 fixed (TIDE-gate `2ffbdbbba`, registry updates landed); bimodal throughput regression now tracked in progress notes, not this handoff.
- `root-archetype-linter-templates-upstream.md` — core deliverables 1-4 DONE; remaining cleanup-only (test linter, update init-project.sh, document in root-archetype README).

### NEEDS_REFRESH (6) — open but stale; owner should reconcile

- `glm51-reap-cpu-evaluation.md` — 35d, Phase 1 audit incomplete; consolidation candidate with `llama-cpp-dsa-contribution` (DSA unlocks both V3.2 and GLM-5.1).
- `agent-file-prose-compression.md` — Phase 3 eval inference-gated; 21d no activity; master-index should reflect suspended state.
- `colbert-reranker-web-research.md` — S5 implementation gated on AR-3 data; 27d no progress signal.
- `privacy-hygiene-precommit-hooks.md` — PII-3 30-day re-eval gate scheduled for 2026-05-24; today is 2026-05-27; no follow-up recorded.
- `mathsmith-hc-formalizer-eval.md` — 69d old; S1 only DONE; S2-S5 untouched; no git commits since 2026-04-17.
- `granite-97m-r2-bench-plan.md` — 27d old; Phase A/B/C NOT STARTED; gated on K2 chunker (still STUB); blockers unresolved.

### KEEP_ACTIVE (rest)

Remaining 23 aging handoffs verified as legitimately live (recent commits, code landed, or genuinely backburnered with explicit policy). Notable confirmations:

- `triattention-kv-selection.md` — S1-S7 DONE; llama.cpp + autopilot wiring live; S8/S9 next.
- `tri-role-coordinator-architecture.md` — TR-1/2/3 LANDED 2026-05-07 (`c4e0f64`, `44eedb5`); 27 tests pass.
- `lightning-attention-port.md` — v1 COMPLETE 2026-04-30 (`33b60b925`); quality benchmarks pending.
- `repl-turn-efficiency.md` — S7 ColGREP DONE 2026-04-29 (`0dc0d6d`); 260 commits past 2mo show continuous shipping.
- `eval-tower-verification.md` — EV-1/2/6 DONE; EV-8 landed 2026-04-22.
- `halo-trace-loop-spike.md` — OTLP support verified at `telemetry.py:57`; ready-to-claim.

## Index pruning (second pass)

Second pass surfaced **0 net archive moves** after operator review. Remaining actions, all pending operator approval:

1. Trim 4 DEREFERENCE master-index entries to outstanding-TODO bullets only (no file moves).
2. Flag 6 NEEDS_REFRESH handoffs to their owners via a single progress-log entry (no file moves).
3. Re-verify any future ARCHIVE proposal against the corrected audit method (reference-target check + acceptance-criteria-as-written check).

## Notes

- First pass (morning 2026-05-27) only archived handoffs with explicit landed/closed dispositions and low ambiguity.
- Second pass (evening 2026-05-27) used parallel code-verification agents; results above.
- Open-but-aging handoffs intentionally left alone unless code verification confirms closure.
