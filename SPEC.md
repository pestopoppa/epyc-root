# Operational Specification

## Logging

All agent actions are logged via append-only JSONL format to `logs/agent_audit.log`.

### Required Events
- Session start/end
- Task start/end with success/failure status
- Escalation decisions
- Error encounters (with context)

### Loop Prevention
Max 3 retries on any single action. After 3 failures: log blocker, stop, escalate.

## Hooks

Hooks in `scripts/hooks/` are referenced from `.claude/settings.json` and execute on Claude Code tool calls.

| Hook | Trigger | Purpose |
|------|---------|---------|
| `check_filesystem_path.sh` | Write, Edit | Block writes outside `/mnt/raid0/` |
| `agents_schema_guard.sh` | Write, Edit | Validate agent file YAML schema |
| `agents_reference_guard.sh` | Write, Edit | Validate agent file cross-references |
| `check_pytest_safety.sh` | Bash | Block `pytest -n auto` and `-n N` where N > 16 |
| `benchmark_context.sh` | Various | Inject benchmark context |
| `claude_accounting_context.sh` | Various | Inject CLAUDE.md governance context |
| `skills_context.sh` | Various | Inject skills context |

## Permissions

### Filesystem
- All LLM-related files on `/mnt/raid0/` (RAID array)
- Never write to root filesystem (`/home/`, `/tmp/`, `/var/`)
- Environment variables enforce cache/temp paths to RAID

### Git
- Never force-push to main/master
- Never skip hooks (--no-verify)
- Always create new commits (never amend unless explicitly requested)

### Testing
- Never `pytest -n auto` (192 threads = OOM)
- Safe default: `pytest -n 8`
- Memory guard: tests fail if < 100GB available

## Cross-Repo Coordination

Changes that affect multiple repos require:
1. Handoff document in `handoffs/active/`
2. Dependency map review (`.claude/dependency-map.json`)
3. Validation pass in all affected repos
4. Progress update in `progress/`
