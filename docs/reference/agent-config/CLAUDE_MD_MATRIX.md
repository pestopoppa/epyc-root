# CLAUDE.md Coverage Matrix

This matrix defines governance boundaries for every `CLAUDE.md` / `AGENTS.md` discovered in
this project (root repo + child repos). Expanded 2026-07-30 (audit D11): previously it governed
only the root file while six sub-repo agent files existed unaccounted.

## Governed Files (root repo)

| Path | Scope | Action |
|---|---|---|
| `CLAUDE.md` | Project root agent policy | Maintain; keep aligned with hooks/skills/docs |
| `AGENTS.md` | Root symlink | Keep symlinked to CLAUDE.md (`scripts/validate/check_agent_file_symlink.sh`) |

## Child-Repo Governed Files

| Path | Scope | Action |
|---|---|---|
| `repos/epyc-orchestrator/CLAUDE.md` | Child repo policy | Maintain in child repo |
| `repos/epyc-orchestrator/AGENTS.md` | Child symlink | Keep symlinked to its CLAUDE.md |
| `repos/epyc-inference-research/CLAUDE.md` | Child repo policy | Maintain in child repo |
| `repos/epyc-inference-research/AGENTS.md` | Child symlink | Keep symlinked to its CLAUDE.md |

## Upstream / Unmanaged (frozen tree)

| Path | Scope | Action |
|---|---|---|
| `repos/epyc-llama/CLAUDE.md` | Upstream ggml-org stub in the FROZEN production kernel | **DO NOT EDIT.** Project overlay staged at `docs/reference/agent-config/llama-tree-overlay/`; baked in at next promotion (AFC-P6.20) |
| `repos/epyc-llama/AGENTS.md` | Upstream contribution policy | **DO NOT EDIT.** Scoped by the staged overlay (upstream-PR prep only) |

Known-untracked in the frozen tree (operator-blessed 2026-07-30, relocate at v9 bake):
`.gitnexusignore`, `tools/math-tools/` — both pre-freeze; no effect on HEAD-pin/verifier.

## Related Governance Files

| Path | Purpose |
|---|---|
| `CLAUDE_GUIDE.md` | Human-facing explanation of project-level agent configuration |

## Non-Governed Discovery Classes

| Class | Path Prefix | Action |
|---|---|---|
| Vendor/plugin trees | `config/plugins/`, `config/.claude/plugins/` | Do not edit; ignore for checks |
| Backups | `backups/` | Ignore except forensic reference |
| Child-repo harness scopes | `repos/epyc-orchestrator/.claude/`, `repos/epyc-inference-research/.claude/` (incl. the nested `scripts/benchmark/.claude/` settings scope) | Harness-local skills/settings; not CLAUDE-policy surfaces |

## Policy

1. Only governed files are migration targets in governance refactors.
2. If a new repo-owned `CLAUDE.md`/`AGENTS.md` is added anywhere, update this matrix, the JSON,
   and validators in the same change — `scripts/validate/validate_claude_md_matrix.py` now
   discovers `repos/*/CLAUDE.md|AGENTS.md` and fails on unaccounted files.
3. The frozen llama tree is never written; its agent layer changes only via the staged overlay
   at a version boundary.

## Related Design Doc

- `docs/reference/agent-config/AGENT_FILE_LOGIC.md`
