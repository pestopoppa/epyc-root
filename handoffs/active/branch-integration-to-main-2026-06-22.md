# Branch integration to `main` — standalone-session report (2026-06-22)

**Purpose**: hand the main-integration decision to a dedicated session. This documents the
exact branch topology, what's on the branches, the uncommitted churn, the risks, and ready-to-run
commands. **Nothing in here was executed** — per operator direction this session held (C) and did
not touch any branch/main/remote state.

> ⚠️ Scale correction: an earlier checkpoint note estimated "~20 commits" of codex work to
> integrate. The real divergence is **107 commits (epyc-root) and 783 commits (epyc-orchestrator)**
> ahead of `origin/main`. FF-merging publishes the *entire* divergent working history to production
> `main`, not just the A9 series. Treat this as a real release decision.

## 1. Topology (as of 2026-06-22, post-fetch)

| Repo | Working branch | Upstream | Ahead of `origin/main` | FF-able? | `origin/main` tip |
|------|----------------|----------|------------------------|----------|-------------------|
| epyc-root | `research-intake-refine-merge-2026-06-20` | **none set** | **107** | **Yes** (origin/main is a strict ancestor) | `ff2bdf57` "Record F1 live token probe" |
| epyc-orchestrator | `fix/substring-scorer-digit-separators` | **none set** | **783** | **Yes** | `d74a8bfc` "dashboard: de-inflate pre-fix speeds…" |
| epyc-inference-research | `main` | origin/main | 0 (in sync) | n/a | — |
| llama.cpp (epyc-llama) | `production-consolidated-v5` | **none set** | — (separate line; not a main-merge candidate) | — | — |

Key facts:
- Both feature branches are **clean fast-forwards** — zero merge conflicts mechanically. The risk
  is **content/release**, not conflict: FF advances production `main` by the full history.
- The feature branches have **no upstream tracking ref** — they are local-only. "Push the feature
  branches" requires `git push -u origin <branch>` to create `origin/<branch>` first.
- `origin/main` is **far behind** the working branches (107 / 783). Either the team's real work
  lives on these branches and main is intentionally lagging, or main is neglected. **Confirm which
  before FF-publishing** — that judgment is the whole point of doing this in a dedicated session.
- The **autopilot runs from the epyc-orchestrator working tree on `fix/…`**. Any branch checkout in
  that tree must be coordinated with the autopilot lifecycle (stop it first, or use a separate
  `git worktree`), or it will read inconsistent files mid-run.

## 2. What's on the branches

- **A9 offline reward-oracle eval** (the codex long-horizon session, 2026-06-20→22): 9 `Record A9…`
  commits (epyc-root) + 10 `A9…` commits (epyc-orchestrator, `scripts/graph_router/*` + report
  artifacts). Outcome was mostly null/negative diagnostics — see `progress/2026-06/2026-06-22.md`
  and routing-index P1 row. Pairwise ranker repaired `suite:livecodebench` but still fails
  `seeding_eval` + `thinking`.
- Plus **~3 days of other accumulated work** (F4/F6/N11/evidence-plane W4-W7/X-MAS/ODL/pipeline
  commits) and, before that, the full divergence back to `origin/main` (months on the orchestrator
  branch). The 783 is not all recent — it's the long-lived working branch.
- My 2026-06-22 checkpoint commit `0fb771f8` (epyc-root) is included in the 107.

## 3. Uncommitted churn (per repo, as of this session)

| Repo | Path | Nature | Recommendation |
|------|------|--------|----------------|
| epyc-orchestrator | `scripts/autopilot/failure_blacklist.yaml` (+6) | live autopilot runtime state | commit while autopilot stopped (snapshot of learned failures) |
| epyc-root | `llama.log` (+3898), `logs/agent_audit.log` (+207), `logs/.current_session`, `.devc/Dockerfile.patch` (52) | tracked log/runtime churn + a devcontainer patch | the logs are tracked but log-shaped → **candidate for `.gitignore`** rather than committing 3.9k-line diffs; review `.devc/Dockerfile.patch` separately (it's a real edit, not churn) |
| epyc-root | `progress/2026-06/2026-06-22-autopilot.md` | auto-generated digest (untracked) | commit (small progress artifact) |
| epyc-inference-research | `data/preflight/*.json`, `*.pid`, `data/research/*`, `data/batched_decode/*` | transient/scratch data, untracked for weeks | **gitignore, do not commit** (standing gitignore-binaries rule) |
| llama.cpp | `.gitnexusignore` (added 2026-06-12, excludes vendored Eigen from gitnexus), `gguf-py/uv.lock` | small useful config | commit to `production-consolidated-v5` |

## 4. Recommended integration approach (operator's call)

1. **Decide the target**: is `origin/main` the intended destination, or should these branches BE
   the main line (rename / reset main)? The 783-commit gap suggests answering this first.
2. **If FF-publishing to main**:
   - Stop the autopilot first (it runs from the orchestrator tree). Then per repo:
     ```
     git -C <repo> fetch origin
     git -C <repo> checkout main
     git -C <repo> merge --ff-only <feature-branch>
     git -C <repo> push origin main
     ```
   - `--ff-only` guarantees no surprise merge commit; if it refuses, origin/main advanced since this
     report — re-evaluate.
   - Restart the autopilot from `main` afterward (code is identical post-FF).
3. **If backup-only (option B)**: `git -C <repo> push -u origin <feature-branch>` for epyc-root and
   epyc-orchestrator; leave main untouched. Reversible.
4. **Churn**: handle per the table in §3 during the same session (commit failure_blacklist with the
   autopilot stopped; gitignore the transient data + logs rather than committing bloat).

## 5. Risks
- **Production publish of in-flight/experimental work** — the branches include null diagnostics,
  default-off experiments, and partial work. FF-to-main makes all of it production history.
- **Autopilot ↔ orchestrator tree coupling** — never checkout/merge in the orchestrator tree while
  the autopilot is live; stop it or use `git worktree`.
- **Shared clone** — `/workspace/repos/<name>` and `/mnt/raid0/llm/<name>` are the same tree; other
  agents may commit concurrently. Re-fetch and re-check FF-ability immediately before merging.
- **No upstream on feature branches** — the first push must use `-u`.

## 6. What this session did NOT do
Held (C): no merge, no push, no branch checkout, no remote mutation. Local work (this report, the
A9 diagnostic, wiki recompile, meaningful churn commits) stays on the current feature branches with
**no pushes**. Integration is entirely deferred to the standalone session this report is for.
