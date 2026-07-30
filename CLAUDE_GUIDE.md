# Understanding the Agent Configuration

Human-facing guide to how AI agent sessions are configured in this project. Rewritten
2026-07-30 (the previous version described a ~370-line CLAUDE.md layout retired months ago).

## The Layers

```
CLAUDE.md (= AGENTS.md symlink)   ← Auto-loaded every session rooted at /workspace.
                                    Repo map, v8 kernel freeze, handoff entry point,
                                    measurement pointer, session-bus commands.
repos/<name>/CLAUDE.md            ← Auto-loaded for sessions rooted in a child repo
                                    (AGENTS.md symlinks serve Codex). epyc-llama has
                                    only upstream stubs — see the coverage matrix.
agents/AGENT_INSTRUCTIONS.md      ← Execution contract + read order for the layers below.
agents/shared/*.md                ← Cross-cutting policy: OPERATING_CONSTRAINTS,
                                    MEASUREMENT_POLICY (digest of MEASUREMENT.md),
                                    ENGINEERING_STANDARDS, SESSION_LIFECYCLE, WORKFLOWS,
                                    HARNESS_RUN_POLICY.
agents/<role>.md                  ← Thin role overlays (6-header schema, hook-enforced).
docs/guides/agent-workflows/      ← Operational procedures extracted from prompts.
docs/reference/agent-config/      ← Governance records: coverage matrix, audit docs,
                                    INCIDENT_LOG (origin narratives behind rules),
                                    staged llama-tree overlay.
MEASUREMENT.md + measurement/protocols/  ← The measurement constitution (human-only writes).
.claude/commands/ + .claude/skills/      ← On-demand skills; loaded only when invoked.
.claude/settings.json                    ← Hooks (below).
```

Design principle: the auto-loaded layer stays small and factual; everything situational is a
pointer. Negative rules keep a one-line origin (`origin: INC-<id>`); full narratives live in
`docs/reference/agent-config/INCIDENT_LOG.md`.

## Hooks (`.claude/settings.json` → `scripts/hooks/`)

| Hook | What it does |
|---|---|
| `check_pytest_safety.sh` | Blocks `pytest -n auto` / oversized worker counts |
| `check_filesystem_path.sh` | Blocks writes outside sanctioned paths |
| `check_trust_boundary_edit.sh` | Blocks agent edits to human-only files (`coordination/session-bus/human_only_paths.yaml`) |
| `check_live_holder_interference.sh` | Guards against interfering with a live inference holder |
| `check_commit_hygiene.py` | Commit hygiene checks |
| `agents_schema_guard.sh` | Enforces the 6-header role schema on `agents/*.md` |
| `agents_reference_guard.sh` | Validates markdown references in governance files (post-edit content) |
| `benchmark_context.sh` / `claude_accounting_context.sh` / `skills_context.sh` | Context reminders |
| `posttool_kb_rag_update.sh` | Keeps the KB index fresh after edits |

## Validators (`scripts/validate/`)

- `validate_agents_structure.py` — role-file schema
- `validate_agents_references.py` — markdown refs + `#anchor` links across agents/ + workflow docs
- `validate_claude_md_matrix.py` — discovers all CLAUDE/AGENTS files and checks matrix coverage
- `check_claims_grammar.sh` — warn-mode scan for uncited measurement claims in handoff diffs
- `check_agent_file_symlink.sh` — AGENTS.md symlink integrity

## Where to Look

| Topic | Read this |
|---|---|
| Governance boundaries for CLAUDE/AGENTS files | `docs/reference/agent-config/CLAUDE_MD_MATRIX.md` |
| Why a rule exists (incidents) | `docs/reference/agent-config/INCIDENT_LOG.md` |
| Agent-file architecture rationale | `docs/reference/agent-config/AGENT_FILE_LOGIC.md` |
| 2026-07-30 full-stack audit | `docs/reference/agent-config/agent-file-audit-2026-07-30.md` |
| Measurement rules | `MEASUREMENT.md` (constitution) → `agents/shared/MEASUREMENT_POLICY.md` (digest) |
| Session lifecycle (wrap-up, /clear, close) | `agents/shared/SESSION_LIFECYCLE.md` |
| Multi-session coordination | `agents/coordinator-agent.md`, `coordination/session-bus/BUS_PROTOCOL.md` |

## Updating the Configuration

- New skill: add under `.claude/commands/` or `.claude/skills/`; keep command/skill parity
  (`skills_context.sh` reminds you).
- New hook: script in `scripts/hooks/` (JSON on stdin; exit 0 allow, exit 2 block), wire in
  `.claude/settings.json`, `chmod +x`.
- Any new CLAUDE.md/AGENTS.md anywhere: update the coverage matrix + JSON in the same change —
  the matrix validator fails on unaccounted files.
- Keep CLAUDE.md lean: if a section is situational, extract to `docs/guides/agent-workflows/`
  or a skill and leave a pointer.

*This guide is for human orientation. For actual work, agents follow the read order in
`agents/AGENT_INSTRUCTIONS.md`.*
