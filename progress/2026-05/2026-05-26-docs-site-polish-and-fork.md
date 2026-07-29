# 2026-05-26 — Docs-site Phase D polish + 3 stories + ik_llama.cpp fork

## Context

Third segment of the 2026-05-26 session. The first segment refreshed sibling-repo chapters (`2026-05-26-chapters-audit.md`); the second scaffolded MkDocs Material on GH Pages (`2026-05-26-docs-site-scaffold.md`); the third wrote the link-rewriter + 7 narrative stories (`2026-05-26-docs-site-stories.md`). This entry covers the post-second-wrap-up work: Phase D polish, three more narrative stories, and an unrelated infrastructure task — making the `ik_llama.cpp` fork writable.

## Changes — docs site

### Phase D polish (commit `6dfa0c3` on epyc-root, `ab2d235` on epyc-inference-research)

| Item | File(s) | Notes |
|---|---|---|
| Mermaid topology diagram on landing | `site_src/index.md` | Runtime flow: user → API → router → 4 model tiers (worker, coder, architect, ingest) → response → telemetry → MemRL → posterior back to router |
| Auto-generated Recent results page | `scripts/docs/build-recent-results.py`, `site_src/stories/recent-results.md` (gitignored, regenerated each build) | Walks `progress/YYYY-MM/*.md` for last 90 days; extracts H1 + first non-heading paragraph; emits chronology table linking to GitHub source. 77 entries on first run. Wired into the GH Actions workflow between `rewrite-links.py` and `mkdocs build` |
| Anchor fix in research chapters | `epyc-inference-research/docs/chapters/01-speculative-decoding.md`, `03-prompt-lookup.md` | MkDocs collapses em-dash to single dash but the links used double-dash form. Three references corrected |
| Self-anchor on deep-dive | `research/deep-dives/markdownfs-rust-mcp-vfs.md` | Explicit `{ #architectural-limits }` on the heading |

**Build verdict**: 651 → 0 warnings, 3 → 0 stale-anchor INFO.

### Three new narrative stories (commit `6dfa0c3`)

| Page | What it documents |
|---|---|
| `site_src/stories/skillbank-rollout.md` | Materialized-view-over-episodic-store architecture; teacher-distillation pipeline; the feature-flagged-off rollout discipline |
| `site_src/stories/autopilot-restart-resilience.md` | Fleet markers + WAL crash recovery; the discipline of exogenous-event tests; how AutoPilot learned to tell "operator did this" from "the config is broken" |
| `site_src/stories/creativity-planner.md` | Stagnation gating, 6→3 axis rubric, persisted falsifiers, quote-don't-regenerate guard |

Stories index regrouped: Features & systems / Specific wins / Investigations / Operations / Live work. Nav order updated.

## Changes — ik_llama.cpp fork (no commits in tracked repos; remote operations only)

**Problem**: `/mnt/raid0/llm/ik_llama.cpp` had `origin` pointing at `ikawrakow/ik_llama.cpp` (read-only). The `pr-1744` branch with the deployed gemma4-MTP patches was committed locally but unpushable. One uncommitted operational fix was sitting in the working tree.

**Resolution**:
1. Committed the uncommitted fix: `src/llama.cpp` silences `LLAMA_LOG_WARN("Oops: tensor with strange name ...")` for the gemma4_mtp top-level tensors that PR #1744 introduces. Functionally a no-op; cleans up production log noise.
2. Created public fork via `gh repo fork ikawrakow/ik_llama.cpp --clone=false --remote=false`.
3. Re-pointed remotes: `origin` → `pestopoppa/ik_llama.cpp` (writable), `upstream` → `ikawrakow/ik_llama.cpp` (read-only sync point).
4. Pushed `pr-1744` to the new origin, then renamed locally + on remote to `production-gemma4-mtp` (matches the naming convention in the llama.cpp fork).
5. Set `production-gemma4-mtp` as the fork's default branch.
6. Synced local `main` to upstream HEAD (`d2da6da0`).
7. Bulk-deleted 896 inherited branches from the fork via `gh api -X DELETE` parallelized (`xargs -P 8`). Fork now has 2 branches: `main` (upstream tracker) + `production-gemma4-mtp` (deployed binary state).

**Branch-name reasoning**: every meaningful commit on the patch series is gemma4-specific (`gemma-mtp: build the arch`, `gemma-mtp: fix mtp kv state`, the gemma4_mtp tensor warning silence). Naming the branch `production-gemma4-mtp` keeps it accurate; a future generalized-MTP variant would warrant a separate branch.

## Results

- Docs site live with Phase D polish + 10 narrative stories at https://pestopoppa.github.io/epyc-root/. Deploy run `26458357755` completed 86 s. Build is now zero-warning.
- ik_llama.cpp fork at https://github.com/pestopoppa/ik_llama.cpp; deployed binary state is pushable; upstream sync path documented in the local clone (`upstream` remote).

## Deferred

- More narrative stories (no immediate queue; open for future writing — SkillBank A/B test results when they land, the dashboard topology bug investigation from 2026-05-24, the global KMP_BLOCKTIME=10 fix from 2026-05-21 would all be candidates).
- Custom domain + analytics for the docs site.
- Future ik_llama.cpp upstream rebases: `git fetch upstream && git rebase upstream/main production-gemma4-mtp`, then force-push. The deployed binary is the source of truth; rebases are deliberate operations.

## Commits this segment

| Repo | Commit | Branch | Pushed |
|---|---|---|---|
| epyc-root | `6dfa0c3` | main | yes |
| epyc-inference-research | `ab2d235` | main | yes |
| ik_llama.cpp (new fork) | `c04881fc` | production-gemma4-mtp | yes |
| ik_llama.cpp (new fork) | `d2da6da0` | main | up-to-date (matches upstream) |

Wrap-up commit pending (this progress entry + handoff close).
