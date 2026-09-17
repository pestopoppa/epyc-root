# 2026-09-16 — Research Intake: Dream-RSI batch (intake-1435…1459)

**Session**: operator-spawned `/research-intake` (shared clone was 475 commits behind origin/main; all writes in
worktree `/mnt/raid0/llm/worktrees/intake-dreamrsi-20260916`, branch `intake/dreamrsi-20260916` off `origin/main` `86f290d0`).
**Mandate**: ingest https://arxiv.org/html/2609.14858 (Dream-RSI). Operator frame (steering): distil insights/gaps vs
autopilot/autokernel loops and inform a future **autoharness** loop for improving the user-facing harness.
**Status**: Stage 4 complete; branch UNCOMMITTED (shared-tree hygiene; separate commit decision pending).

## Sources ingested (25 new entries total)

- **Stage 1** (9): intake-1435 Dream-RSI (paper) + 1436 companion repo (code-free) + 7 reference-chased
  (EvoX, SimpleTES, SwarmResearch, PACEvolve, PACEvolve++, DeltaEvolve, Meta^n).
- **Stage 2 dives** (6): 1435, 1437, 1438, 1439, 1440, 1442 — all entry-level `dive-verified`, many claims narrowed;
  claim anchors + per-claim corrections recorded. Load-bearing corrections: Dream-RSI's implemented replay reward is
  App. B.2's `pareto.auc − λ·parallel_penalty` (not Eq. 1); "1.22x/1.74x/zero-gradient" are companion-README-only;
  EvoX scores strategies online only (no replay); PACEvolve's MBB/CE need a known target bound; SimpleTES' "generations"
  is Dream-RSI's relabeling of evaluator queries; the SwarmResearch 13/15 count is threshold-ambiguous.
- **Stage 2b** (11): 1444 harness-null-pool (3.1M rollouts, no superior harness; adaptive portfolio margin), 1445 CostAda,
  1446 google/pacevolve (ground truth: freeze=15 rolling, m0 code-vs-paper mismatch, no persistent failure log),
  1447 AIChilles (49 weaknesses; robust gating zeroes gains), 1448 AdaEvolve, 1449 CORAL, 1450 repro repo
  (13/15 NOT resolvable), 1451 EvoReplay study (30% line cycling; BO tuning ceiling 13/15), 1452/1453 SkyDiscover,
  1454 SimpleTES code (RPUCG selection-only).
- **Stage 2b2** (5): 1455 CORAL repo (opencode/codex can target orchestrator `/v1`; pin v0.7.20), 1456 BaSE bandits,
  1457 Efficiency Matters (fluid bandit), 1458 EvoReplay tooling, 1459 EvoTrace dataset.

All four close-out gates closed by operator selection; every dive-surfaced source ingested-and-dived or declined
(declines recorded in bearing entries' `dive_corrections`).

## Stage-4 outcome (operator-approved plan, 2026-09-17)

14 new task rows across 6 handoffs; 0 checkbox flips:

| Handoff | Rows |
|---|---|
| `autokernel-research-loop.md` | AK-WM-3 replay over archives; AK-adaptive policy panel (EvoX/AdaEvolve/BaSE); AK-plateau pack (PACEvolve HCM/momentum/revert); AK-cost-credit (CostAda); AK-lineage diagnostics (cycling/taxonomy/semantic deltas + vidya hook); AK-promotion controls (replay N=10 + BO ceiling); AK-integrity pack (SimpleTES hardening + AIChilles probes) |
| `agent-collab-rnd-harness.md` | AC-CORAL pinned spike vs `/v1`; AC-branch-per-agent SwarmResearch spec |
| `autokernel-rebuild-program.md` | RB-lineage telemetry (spawn parent/branch/width×depth) |
| `harness-selection-and-integration.md` | HS-E1 harness-null-pool evidence for HS-4 (operator-owned gate) |
| `autopilot-sequential-allocation.md` | SEQ-4 zero-inference allocation replay (BaSE/fluid vs budget=8) |
| `agentic-rocm-kernel-authoring.md` | AR-RPUCG selection A/B; AR-ROCm-eval port input |

Explicit declines (with reasons in the plan): all autopilot-continuous-optimization mechanics (handoff STOPPED
2026-08-10; restart needs explicit operator permission), DeltaEvolve→TOC/CF, guidance-prompt task, monitor rows,
HS/DAR/TOC domain mismatches, external re-measurements, and the 13/15 re-run (≥$1.1k, no decision depends).

## Validators

- `validate_intake.sh` exit 0 (1455 entries).
- `index_state.py` generate + `--check` exit 0 (0 problems; master rollup refreshed).
- `cite-check` exit 0 (clean).
- Intake entries: `handoffs_updated` + `integration_disposition` + `disposition_evidence` set on 1435–1459.
- All writes in the worktree; `handoffs/` edits are the six files above plus the generated master index.

## Wrap-up (operator-invoked /wrap-up, 2026-09-17)

- **Checklist-sync gate**: 0 checkbox flips this session (intake session files new work, executes none); 14 new unchecked rows added (verified by diff count); derived-actionables gate satisfied at Stage 3/4 (26 explicit declines recorded in the approved plan; every dive-ledger row filed or declined).
- **Handoff index**: `index_state.py` + `--check` exit 0 under the wrap-up lease; prune screen ran in the operator-cadence step — **0 candidates**, nothing archived/compacted; `Next action` cells of the six advanced handoffs reviewed, no cell changes required (new rows are additive/observe-only and do not supersede their current next actions).
- **README freshness**: checker silent (all pass); no refreshes needed.
- **Wiki compilation sweep** (operator cadence): two passes compiled the residual drift into `wiki/{autonomous-research,benchmark-methodology,agent-architecture,knowledge-management,safety,hardware-optimization,speculative-decoding,ssm-hybrid,multimodal,tool-implementation}.md`; watermark advanced via `--touch` under lease after all drift was folded.
- **Agent log**: session not logging-driven; no open `agent_task_end` to close.
- **Commits/promotion**: see the wrap-up output block in the session response (root repo only; no child-repo changes).

## Commits & promotion (2026-09-17)

| Repo | Branch | Commit | Pushed | Promoted to main | Message |
|------|--------|--------|--------|------------------|---------|
| epyc-root | intake/dreamrsi-20260916 | 1e418919 | ✅ | ✅ via 5f6d4f1d | research-intake (Dream-RSI batch): intake-1435..1459, 14 task rows across 6 handoffs |
| epyc-root | intake/dreamrsi-20260916 | ffe490cb | ✅ | ✅ via 5f6d4f1d | Merge origin/main into intake/dreamrsi-20260916 |
| epyc-root | intake/dreamrsi-20260916 | a9d329de | ✅ | ✅ via 5f6d4f1d | wrap-up: wiki compilation sweep (fleet drift), progress close-out |
| epyc-root | intake/dreamrsi-20260916 | ada8168b | ✅ | ✅ via 5f6d4f1d | Merge origin/main into intake/dreamrsi-20260916 |
| epyc-root | intake/dreamrsi-20260916 | 31146958 | ✅ | ✅ via 5f6d4f1d | wrap-up: advance wiki manifest after merge (post-sync --touch) |
| epyc-root | intake/dreamrsi-20260916 | 5f6d4f1d | — | ✅ (merge commit on main) | Merge intake/dreamrsi-20260916 into main (wrap-up promotion 2026-09-17) |

Promotion published with the attributed push-guard hatch (`EPYC_ALLOW_UNSERIALIZED_PUSH`, wrap-up lease held, no push-lock holder). Local `main` pointer in the shared clone was left as-is (branch checked out there; remote main is authoritative).
