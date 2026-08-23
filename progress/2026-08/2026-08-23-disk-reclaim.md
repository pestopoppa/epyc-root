# 2026-08-23 — disk reclamation session

**Agent**: opencode (ad-hoc, no lane; shared-clone session). Self-contained close-out record;
the same entry is appended to the shared `progress/2026-08/2026-08-23.md`.

## Mandate

Operator asked: "is there any space that can be easily reclaimed on /mnt/raid0/llm?" — stale temp
files and unused models. Operator then approved scope: **tmp/ scratch + worktrees (~280G)**.

## Findings (census, 3.4T/3.7T = 97% used)

- `tmp/` 285G — 147 registered git worktrees (epyc-inference-research 88, workspace 44,
  llama.cpp-experimental 4, llama.cpp 4, epyc-orchestrator 2) from 08-11→08-22 sessions + ~15k
  loose stale files. Only `dashboard-v26-telemetry-integrity-20260821` had live open handles.
- `models/` 1.9T — cross-referenced every top-level entry against production configs
  (autopilot system_card.md, launch_manifest.yaml), autokernel campaigns/controls, research
  recipes/scripts, active handoffs, and live `ps`. ~25G safe duplicates/orphans; biggest
  judgment calls flagged for operator.
- `autokernel/worktrees/` 165G — 146 one-shot session worktrees, 2 referenced by active handoffs.
- Stale kernel trees ~18G; `cache/huggingface` 127G re-downloadable.

## Changes made

| Path | Action |
|---|---|
| `/mnt/raid0/llm/tmp/` | 285G → 2.9G: removed 138 registered worktrees (per-worktree `git worktree remove --force`, NEVER `prune` — 2026-08-12 incident) + ~15k stale loose files |
| `/workspace/tmp/` | temporary census/removal scripts (removed after use) |

**Preserved**: 4 worktrees (`dashboard-v26-telemetry-integrity-20260821` in-use;
`evaluator-91a-audit.3i6ycm`, `merge-20260816`, `root-session-wrapup-20260820` dirty) + all live
coordination files (runtime facts, started_at markers, locks). Worktree branches/commits persist
in shared repos (nothing deleted from git).

## Results

111G free → **371G free** (97% → 90% used). **~260G reclaimed** in the approved scope.

## Deferred (operator options, not actioned)

- autokernel/worktrees 165G (144/146 stale — 2 referenced by active handoffs)
- model duplicates/orphans ~25G (safe set listed in census)
- stale kernel trees ~18G (preserved-20260724T135832Z, v6-iqk, v7-sanitize-audit, k28-prototype)
- cache/huggingface 127G (re-downloadable)
- `ak-supervisor-*-canary.*` dirs have permission-protected files (negligible size, need root)
