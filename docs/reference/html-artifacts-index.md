# HTML Artifacts Index

The single catalog of every standalone HTML artifact this project has authored — design docs, flow
maps, deep-dive write-ups, operator reports. If you're looking for one, it's a row below. If
you're about to add or edit one, read
[`docs/guides/agent-workflows/html-artifacts-runbook.md`](../guides/agent-workflows/html-artifacts-runbook.md)
first — it has the placement rule, naming convention, and the mandatory registration step.

**Generated 2026-08-23** from a full repo scan (`scripts/docs/check_html_artifact_index.py`,
excluding the scopes below). Kept honest by that same script — see *Keeping this honest* at the
bottom.

## What's in scope

Any self-contained `.html` file the project authored as a document in its own right — not
generated build output, not application UI. As of 2026-08-23 that's exactly 5 files.

## What's explicitly out of scope (never add these here)

| Excluded | Why | Governed by |
|---|---|---|
| `dashboard/static/*.html` (6 files) | The dashboard hub's live application UI — served pages, not documents | [`dashboard/README.md`](../../dashboard/README.md) view-plane rule |
| `tmp/**/*.html` | Fetched external material / research-intake scratch, gitignored | `agents/shared/OPERATING_CONSTRAINTS.md` → *External Content Handling* |
| `worktrees/**/*.html` | Duplicate checkouts of files already listed here at their canonical path | — |

## Catalog

| Path | Title | Category | Companion / caveat | Last updated |
|---|---|---|---|---|
| [`artifacts/operator/e5_w0_preliminary_results.html`](../../artifacts/operator/e5_w0_preliminary_results.html) | CPU serving reference — production recipes, shapes, and capacity | Operator report | Sibling `.md` of the same stem is the source | 2026-08-11 |
| [`docs/coordination/session-bus-task-flow.html`](../coordination/session-bus-task-flow.html) | EPYC coordination task flow — implementation audit map | Coordination audit map | **See [`session-bus-task-flow-STATUS.md`](../coordination/session-bus-task-flow-STATUS.md) before editing** — the canonical copy has lived ahead of this one, in the auditor's lane worktree | 2026-08-16 |
| [`docs/design/loop-owned-fleet.html`](../design/loop-owned-fleet.html) | Loop-Owned Fleet | Design doc / plan of record | Load-bearing: cited by anchor (`#pivot`, `#d-runner`, `#decisions`) from `agents/README.md` and by 4 production scripts' module docstrings (`scripts/coordination/{promote_lane,headless_audit,worker_runner,premise_screener}.py`). Don't rename anchors without checking those. | 2026-08-16 |
| [`docs/infrastructure/orchestration-stack-map.html`](../infrastructure/orchestration-stack-map.html) | EPYC Orchestration Stack — flow map | Infrastructure flow map | Self-declared living doc; its own header names re-verification sources (`model_registry.yaml`, `stack_manifest.py`, `autopilot.py`) — re-verify against those before editing | 2026-07-29 |
| [`research/deep-dives/2026-05-23-creativity-constrained-tail-search.html`](../../research/deep-dives/2026-05-23-creativity-constrained-tail-search.html) | Creativity as Constrained Tail Search — v3 | Research deep-dive | Sibling `.md` of the same stem is the source | 2026-07-29 |

## Adding or updating an artifact

Don't add a row by hand without reading the runbook first — placement, naming, and companion-file
rules live there so they're authored once:
[`docs/guides/agent-workflows/html-artifacts-runbook.md`](../guides/agent-workflows/html-artifacts-runbook.md).

## Keeping this honest

An index that isn't checked rots exactly the way the pre-2026-08-23 undiscoverable scatter did.
Run before committing any change that adds, moves, or removes an HTML artifact:

```bash
python3 scripts/docs/check_html_artifact_index.py --check
```

Exits non-zero and prints the two-way diff if an on-disk artifact has no row here, or a row here
points at a file that no longer exists. Mirrors `scripts/handoffs/index_state.py --check`.
