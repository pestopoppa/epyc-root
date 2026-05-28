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

### DEREFERENCE (4) — trim index entries to outstanding TODOs only

- `numa-prefill-decode-disaggregation.md` — only Phase 0 xGMI BW falsification test remains; Tier 2b counter-evidence noted.
- `wdata-aware-mul-mat-coalescing-design.md` — Phase 0 design complete with honest NEGATIVE verdict (2-7% gain at 260-410 LOC + ABI cost); trim to decision statement only.
- `qwen36-benchmark-fixes.md` — Qwen3.6 fixed (TIDE-gate `2ffbdbbba`, registry updates landed); bimodal throughput regression now tracked in progress notes, not this handoff.
- `root-archetype-linter-templates-upstream.md` — core deliverables 1-4 DONE; remaining cleanup-only (test linter, update init-project.sh, document in root-archetype README).

**Tracking correction 2026-05-27**: only `root-archetype-linter-templates-upstream.md` was a master-index dereference and has already been trimmed there. The remaining dereference work is domain-scoped:

- `numa-prefill-decode-disaggregation.md` — trim `inference-acceleration-index.md` and `cpu-inference-optimization-index.md` to the Phase 0 xGMI KV-transfer falsification task only.
- `wdata-aware-mul-mat-coalescing-design.md` — trim the handoff to the Phase 0 negative decision and open re-evaluation triggers; keep only a lightweight sibling pointer from `cpu22-hybrid-spillover-design.md`.
- `qwen36-benchmark-fixes.md` — trim or close after one post-reboot confirmation; the bimodal-throughput regression belongs in progress/future tracking, not this handoff.

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

1. DONE 2026-05-27: trim the `root-archetype-linter-templates-upstream.md` master-index entry to outstanding-TODO bullets only (no file move).
2. OUTSTANDING: trim the three domain-scoped DEREFERENCE entries above in `inference-acceleration-index.md`, `cpu-inference-optimization-index.md`, `cpu22-hybrid-spillover-design.md`, and/or their handoff bodies as appropriate.
3. Flag 6 NEEDS_REFRESH handoffs to their owners via a single progress-log entry (no file moves).
4. Re-verify any future ARCHIVE proposal against the corrected audit method (reference-target check + acceptance-criteria-as-written check).

## Notes

- First pass (morning 2026-05-27) only archived handoffs with explicit landed/closed dispositions and low ambiguity.
- Second pass (evening 2026-05-27) used parallel code-verification agents; results above.
- Open-but-aging handoffs intentionally left alone unless code verification confirms closure.

## Third pass executed 2026-05-28 — structure refinement, no archive moves

User asked for systematic handoff audit/refinement, ambiguity reduction, dependency forks, and explicit critique logging. This pass handled the six `NEEDS_REFRESH` handoffs from the second pass one at a time. No file was moved: all six still have open work, but each now has an executor-first audit block with current next action, dependencies, forks, and failure handling.

### Refined handoffs

| Handoff | Critique | Refinement |
|---|---|---|
| `glm51-reap-cpu-evaluation.md` | Looked like a simple download/eval despite a 325GB artifact, recent registry changes, and DSA being the load-bearing architecture dependency. | Added Phase 0 readiness fork: current disk free, current architect-replacement premise, DSA status. Default disposition is WAIT-DSA unless user explicitly wants short-context dense-fallback data. |
| `agent-file-prose-compression.md` | Completed implementation was mixed with the safety-critical eval gate, making Phase 5 rollout look closer than it is. | Added Phase 3 runbook skeleton, result table, and pass/fail forks. Phase 5 is explicitly blocked until per-model compliance curves exist. |
| `colbert-reranker-web-research.md` | Still read like model selection even though S1-S4 were already done; S5 gate was underspecified. | Added telemetry gate: implement S5 only if irrelevant-page rate is >20% over >=50 synthesized pages; hold or no-go otherwise. Added default-off/fail-open risk controls. |
| `privacy-hygiene-precommit-hooks.md` | Landed hook/fixture details obscured the now-overdue PII-3 checkpoint. | Reframed as overdue re-eval only; added hook-install verification, fixture/current-hook check, bypass/false-positive search, and decision forks. |
| `mathsmith-hc-formalizer-eval.md` | `stub` status understated deployed baseline and did not front-load artifact availability or mini-gate. | Added HC artifact check, 10-problem S4 mini-protocol, Math-Verify/token-cost scoring, and result-driven branches. |
| `granite-97m-r2-bench-plan.md` | Status over-gated Phase A on K2 despite an already-described fallback corpus path. | Corrected status: Phase A fallback corpus and dry-run bench script are unblocked; K2 is preferred but not required. Phase B remains inference-gated. |

### Index verification

- Verified all 86 active `.md` handoffs are referenced by at least one core active index (`master`, `routing`, `inference`, `research`, `hermes`, `pipeline`, `cpu`).
- Updated `master-handoff-index.md` rows for GLM-5.1, ColBERT, MathSmith, privacy hygiene, agent-file compression, and Granite.
- Updated `inference-acceleration-index.md` rows for GLM-5.1 and MathSmith.
- Updated `research-evaluation-index.md` GLM-5.1 row and Granite P9 gate correction.

### Remaining audit queue

After this pass, the freshness script still reports aging handoffs. Next systematic batch should prioritize the aging CPU/reference anchors that are large or high-risk to misread: `cpu-benchmark-rigor-and-revalidation.md`, `cpu-kernel-env-flags-inventory.md`, `cpu-optimization-thesis-pause-2026-04-26.md`, `integration-test-coverage.md`, and `intra-process-tensor-parallel-decode.md`.

## Fourth pass executed 2026-05-28 — CPU/reference-anchor ambiguity reduction

Handled the five high-risk aging anchors named above. No archive moves: all five remain load-bearing references, but each now states whether it is a live implementation queue, standing protocol, or historical correction ledger.

| Handoff | Critique | Refinement |
|---|---|---|
| `cpu-benchmark-rigor-and-revalidation.md` | Looked like an old revalidation task despite being the current standing benchmark protocol. | Reframed as ACTIVE PROTOCOL. Added minimal artifact skeleton, current operating rule table, and explicit "do not blanket-rerun historical rows" guidance. |
| `cpu-kernel-env-flags-inventory.md` | Mixed historical cherry-pick planning with live deployment advice after v5 cleanup landed. | Reframed as reference inventory for launch wiring. Added executor rule table and "do not resurrect deprecated flags" block. |
| `cpu-optimization-thesis-pause-2026-04-26.md` | Preserved old user-confirmation questions and priority queues that later decisions superseded. | Reframed as historical correction ledger / reference anchor. Added "do not run old queues directly" warning and pointers to current CPU20/index/env inventory documents. |
| `integration-test-coverage.md` | Started from the stale refactoring-audit coverage table even though later test tranches changed the useful next work. | Reframed as active focused-slice backlog. Added next-work option table and rules against blanket 100% coverage chasing. |
| `intra-process-tensor-parallel-decode.md` | Still opened with HIGH/top-priority framing even though later CPU1-specific levers were exhausted for current NPS4 single-user decode. | Reframed as reference + revalidation-gated. Added reopen checklist requiring new trigger plus CPU20-compliant bottleneck proof. |

Index updates:
- `master-handoff-index.md`: refreshed CPU20 and integration-test rows.
- `inference-acceleration-index.md`: refreshed CPU20 and intra-process TP rows.
- `cpu-inference-optimization-index.md`: refreshed CPU1 and CPU20 priority/list rows.

## Fifth pass executed 2026-05-28 — research/architecture gate clarification

Handled six aging research and routing-architecture handoffs where old implementation history was obscuring the live gate. No archive moves: each file still has an open purpose, but each now states whether it is a validation queue, monitoring tracker, or scoping-only parking lot.

| Handoff | Critique | Refinement |
|---|---|---|
| `lightning-attention-port.md` | 788-line handoff opened like an active port even though v1 already reached coherent decode; implementers could redo L1-L4 or jump to L5 without profile evidence. | Added executor reset: v1 complete, L1-L4 historical, choose one validation slice (quality, long-context, drafter) after branch sanity. L5 dedicated op is profile-gated only. |
| `log-linear-gated-deltanet-readiness.md` | "High priority" plus an implementation plan could be misread as code-ready despite no checkpoint. | Reframed as monitoring-only; activation requires checkpoint, inference reference, and architecture docs. Added evidence template and forks for partial upstream releases. |
| `memento-block-reasoning-compression.md` | S1 success made S3 runtime integration look close even though no adapter evidence exists. | Added S2 runbook and result table. S3 is explicitly blocked until format compliance, compression ratio, accuracy, and S1-masking stability are recorded. |
| `minddr-deep-research-mode.md` | Top status still said stub even though MD-1..MD-8 had landed; the only open Phase 1 question is A/B value. | Reframed as MD-9-gated. Dispatcher wiring waits for sentinel A/B; EV-9 absence permits structural-only scoring but not default-on promotion. |
| `tri-role-coordinator-architecture.md` | Still opened as a stub despite TR-1/2/3.1/3.2 landing. TR-4 could be started before telemetry proved the role classifier meaningful. | Reframed around TR-3.3/3.4 telemetry gates; added distribution diagnostic and fork for degenerate role output. |
| `outer-coordinator-learned-head.md` | Prior audit nearly archived it; status did not explain why it remains active but non-executable. | Reframed as scoping/parking only. Added ROI forks: <20% replaceable Claude decision cost closes not_pursued; >50% uniform decisions prefer rules-first; learned-head spike requires context-dependent decisions plus a usable fitness signal. |

Index updates:
- `master-handoff-index.md`: refreshed Trinity/outer-coordinator, Lightning, Memento, and MindDR rows.
- `inference-acceleration-index.md`: refreshed Lightning, Log-Linear GDN, and Memento rows.
- `research-evaluation-index.md`: refreshed Log-Linear GDN and Memento rows.
- `routing-and-optimization-index.md`: refreshed MindDR, Tri-role, Outer-coordinator, P18, P19.1, and P19.8 entries.

## Sixth pass executed 2026-05-28 — final aging-set refresh

Handled the last nine aging handoffs reported by `check_handoff_freshness.sh`. No archive moves: each remains a useful active reference or gate, but all now have current executor rules and 2026-05-28 status.

| Handoff | Critique | Refinement |
|---|---|---|
| `ernie-image-turbo-evaluation.md` | Production backend details were current, but old open questions still described loader/Hermes integration as unresolved. | Reframed as production via sd-server Q8; remaining work is prompt-enhancer policy, content-filter audit, typography spot-check, and Spark rebench. Resolved loader/Q4/Hermes questions. |
| `orchestrator-nps4-48x4-notes.md` | Notes-only topology reference looked like latent implementation work. | Added trigger table: reopen only for multi-tenant/batch aggregate routing or CPU15/CPU17 topology decisions; preflight requires mmap dedupe, latency-aware routing, and draft-sharing plan. |
| `qkernel-q5q6-default-on-flip.md` | Handoff still said "pending bench" while master-index recorded Phase A failure. | Reconciled failure state: Q6_K PPL passed, 96t perf failed; default flip no-go; Q5/blanket flip deprioritized unless workload/profile changes. |
| `repl-turn-efficiency.md` | Large file still framed S5 code items as proposals despite NIB2 landing them. | Added executor reset: S1/S2/S3/S5/S6/S7 landed; live work is S4 Omega A/B, ColGREP soak/cold-start daemon gate, version/index hygiene. |
| `root-archetype-linter-templates-upstream.md` | Master-index said blocked on missing clone, but clone exists; remaining scope is cross-repo cleanup. | Corrected blocker: local clone exists with unrelated dirty logs. Remaining tasks are root-archetype linter test, scaffold copy, README docs. |
| `single-instance-system-tuning.md` | Original high-priority knob sweep could encourage unsafe blanket sysctl/reboot work after later CPU results narrowed the path. | Reframed as targeted CPU20-gated tuning only; no blanket sudo/reboot actions; reopen only on measured topology/workload trigger. |
| `sliders-local-validation.md` | Stub was structurally decent but needed stronger parking instructions relative to KB-RAG. | Added Phase 0-only executor gate; no integration or prompt tuning before FinQ5 verdict; KB-RAG K7 remains independent. |
| `summary-token-attention-readiness.md` | Readiness tracker needed the same monitoring-only discipline as Log-Linear GDN. | Added activation evidence template and no-code rules; GPU arrival triggers CPT scoping, not automatic implementation. |
| `triattention-kv-selection.md` | Status was deployed but body still centered old S1/S2 evaluation gates. | Reframed live work around S8 per-role autopilot profiles and S9 auto-trigger; S2/S3 are optional comparators, not blockers. |

Index updates:
- `master-handoff-index.md`: refreshed ERNIE, Summary-token, Qkernel, TriAttention, Root-archetype, and SLIDERS rows.
- `inference-acceleration-index.md`: refreshed TriAttention, Summary-token, Single-instance tuning, and KV-selection cross-reference rows.
- `research-evaluation-index.md`: refreshed REPL, Root-archetype, SLIDERS, P6, and P0.5 notes.
- `cpu-inference-optimization-index.md`: refreshed NPS4 notes, CPU3, and Qkernel entries.
- `pipeline-integration-index.md` and `hermes-agent-index.md`: refreshed ERNIE local-image rows.

Validation after sixth pass:
- `bash scripts/validate/check_handoff_freshness.sh`: PASS — 0 aging, 0 stale.
- Core index coverage: 86 active non-index handoffs, 0 missing from core indices.
- `git diff --check`: PASS.
- Follow-up 2026-05-28: split-repo validator drift resolved. `validate_agents_references.py` and `validate_doc_drift.py` pass after removing the archived handoff scan target, replacing the pre-split llama.cpp path reference, resolving `PORT_MAP` from `repos/epyc-orchestrator/scripts/server/stack_manifest.py`, and making root Makefile checks conditional on documented `make` refs.

## Seventh pass executed 2026-05-28 — handoff compaction split pilot

Executed the first whole-project active/completed split pass using the new wrap-up compaction rule. This pass did not delete project knowledge; it moved completed detail into completed ledgers and rewrote active twins to expose only live tasks, gates, forks, key files, and reporting instructions.

| Active handoff | Completed sibling | Critique / reason for split |
|---|---|---|
| `lightning-attention-port.md` | `../completed/lightning-attention-port-v1-completed-through-2026-05-28.md` | Active file was dominated by v1 port history even though live work is role decision, broader quality, Ring-flash drafter check, and profile-gated L5. |
| `integration-test-coverage.md` | `../completed/integration-test-coverage-phases-1-4-completed-through-2026-05-28.md` | Old phase tables made blanket coverage expansion look live; active twin now tracks focused coverage slices only. |
| `repl-turn-efficiency.md` | `../completed/repl-turn-efficiency-completed-through-2026-05-28.md` | Landed S1/S2/S3/S5/S6/S7 work obscured S4 Omega A/B, ColGREP soak, and version/index hygiene. |
| `triattention-kv-selection.md` | `../completed/triattention-kv-selection-deployment-completed-through-2026-05-28.md` | Deployed S1-S7 evidence hid the real live work: S8/S9 autopilot profiles/auto-trigger and optional comparators. |
| `context-folding-progressive.md` | `../completed/context-folding-progressive-completed-through-2026-05-28.md` | Completed Phases 0-3b were much larger than the remaining CF-L5/CF-3c/CF-2c.0/CF-DD8 gates. |
| `intra-process-tensor-parallel-decode.md` | `../completed/intra-process-tensor-parallel-decode-completed-through-2026-05-28.md` | HIGH/top-priority framing was stale; active twin now says reference + revalidation-gated only. |
| `meta-harness-optimization.md` | `../completed/meta-harness-optimization-completed-through-2026-05-28.md` | Tier 1/2 and SkillOpt/HLE history buried the live MH-6/7/9 plus HLE-3/J9 validation path. |
| `bep-dcp-falsification-harness.md` | `../completed/bep-dcp-falsification-harness-completed-through-2026-05-28.md` | BEP-2 remediation was complete, so the active harness now only owns DCP-6 plus optional J8 provenance. |
| `dynamic-stack-concurrency.md` | `../completed/dynamic-stack-concurrency-completed-through-2026-05-28.md` | DS-B-D and DS-6/DS-7 gap history made scheduler implementation look ready. Active twin now gates DS-6 on Phase E evidence and treats KVCOMM as optional. |
| `large-moe-expert-parallelism.md` | `../completed/large-moe-expert-parallelism-completed-through-2026-05-28.md` | First screen still carried superseded EP win/regression claims. Active twin now records CPU15 as default-off infrastructure with CPU20 revalidation required. |
| `routing-intelligence.md` | `../completed/routing-intelligence-completed-through-2026-05-28.md` | Body still contained old Phase 4/5 "not started" sections contradicting completed RI-1..8 state. Active twin now owns RI-10/11/12 rollout and gated RI-13 injection-risk fork. |

Index/reference updates:
- Master/domain indices still point at active twins only.
- Completed siblings have reciprocal banners back to active twins.
- Active twins include `Completed Scope` tables linking their siblings.
- Dynamic-stack, CPU15, and routing-intelligence index rows were corrected to avoid stale implementation cues.
- CPU15 stale deployment claims were softened across CPU index, env-flag inventory, NPS runbook, MoE-Spec, and master-index history phrasing.
- J14 now points to routing-intelligence RI-13 as the conditional injection-risk fork, while preserving the cheap-first unconditional A/B gate.

Validation after compaction split pilot:
- `bash scripts/validate/check_handoff_freshness.sh`: PASS — 0 aging, 0 stale.
- `git diff --check`: PASS.
- Active non-index handoff coverage in master/domain indices: PASS — 0 missing.
- Targeted link check for 11 new completed ledgers: PASS — 0 missing.
