# Archived Role Files — the pre-session-bus persona layer

**Archived**: 2026-08-16 · **Authority**: Loop-Owned Fleet doctrine collapse, task P1-5 in
[`handoffs/active/loop-owned-fleet-implementation.md`](../../handoffs/active/loop-owned-fleet-implementation.md) ·
**Plan of record**: `docs/design/loop-owned-fleet.html`

## What is here

Eight task-based persona files: `benchmark-analyst`, `build-engineer`, `lead-developer`,
`model-engineer`, `research-engineer`, `research-writer`, `safety-reviewer`, `sysadmin`.

They are archived, not deleted. `git mv` preserved their full history.

## Why they were archived

They were a dormant layer. Work is not assigned by persona in this project:

1. **The live fleet roster does not know these names.** `coordination/session-bus/config.yaml`
   identifies every agent by roster id (`mainA`…`mainD`, `auditor`, `inference`,
   `coordinator-agent`, `hardware-backfill`) and gives each a role from a closed set —
   `main | coordinator-agent | reviewer | retired | service`. None of the eight persona names
   appears in the roster, in the bus schema, or in any dispatch path.
2. **Assignment is roster id + lane + typed brief.** The unit of work is a queue row with exact
   task text, a lane (`cpu | gpu | none`), and typed constraints. A persona name has no slot in
   that contract and never gated a dispatch.
3. **Role decomposition is a measured anti-pattern here.** `agents/shared/OPERATING_CONSTRAINTS.md`
   names "decomposition by ROLE rather than by context boundary" as an anti-pattern. The delegation
   matrix in `lead-developer.md` was the only consumer of the other seven files, so the layer cited
   only itself.
4. **They were stale.** No file was edited for its own content after 2026-07-30, and four predate
   the session-bus era entirely. The 2026-07-30 audit
   (`docs/reference/agent-config/agent-file-audit-2026-07-30.md`) already recorded several as
   framed around deprecated subsystems.

Verified before archiving: no live code, hook, skill, slash command, validator, dashboard, or
registry referenced any of the eight. The schema hook `scripts/hooks/agents_schema_guard.sh` and
`scripts/validate/validate_agents_structure.py` both scan `agents/*.md` non-recursively, so these
files leave their enforcement scope by moving here — that is intended.

## Where the content went

Every load-bearing rule in these files already had a canonical home, and that home — not the
persona file — is what governs:

| Content | Canonical home |
|---|---|
| Claim grammar, era labelling, protocol citation | `MEASUREMENT.md` · `agents/shared/MEASUREMENT_POLICY.md` |
| Canonical bench recipe, region lock, host health | `measurement/protocols/bench-cpu.md` · `agents/shared/OPERATING_CONSTRAINTS.md` |
| `DT_RUNPATH` / `--disable-new-dtags` binary-resolution check | `measurement/protocols/bench-cpu.md` |
| Kernel freeze and experimental-branch workflow | root `CLAUDE.md` § Experimental Kernel Workflow |
| Trust-boundary, append-only, external-content quarantine | `agents/shared/OPERATING_CONSTRAINTS.md` |
| Model registry standards | `repos/epyc-inference-research/docs/reference/models/REGISTRY_STANDARDS.md` |
| Writer, benchmark-analyst and safety-reviewer procedures | `docs/guides/agent-workflows/` |

## Rule for anyone who needs this content

**Cite git history. Do not resurrect the file.**

```bash
git log --follow -- agents/archived/<name>.md
git show <sha>:agents/<name>.md
```

If a rule in one of these files is genuinely missing from the canonical surfaces above, add it to
the canonical surface. Restoring a persona file re-creates the dormant layer this task removed.
