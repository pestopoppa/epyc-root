# Owner roles — wiring proposal (2026-11-20, pipeline-mgmt)

Role files (branch `pm-owner-roles`, not pushed): `agents/autokernel.md`, `agents/autopilot.md`,
`agents/pipeline-mgmt.md`. Each passes the role schema check; the live owners review their own file
before it lands.

## 1. Handoff header key

Add `**Owner role**: agents/<role>.md` to the handoff header, next to `**Owner**`. It is a pointer
and nothing else. `task_lint.py` checks that the file exists and passes the role schema. A handoff
with no key gets the generic brief, as it does today.

## 2. Loading the role into a spawned session

The single injection point is `handoff_sessions.brief_text()`. Both `start_handoff` (fresh lane) and
the OWNER-SPAWNED path (proposals pending) go through `_go(... brief_text(...) + first ...)`.
`brief_text` reads the header key and puts the role file first in the brief, under a heading such
as `## Your role (agents/<role>.md @ <sha>)`. Because the content arrives on stdin, it works for
every engine and survives `transfer`. The blob sha is stored in the registry entry (`role_sha`), so
a resume can tell when the role file changed and re-send it.

Harness-native reinforcement, optional, wired in `engine_cmd`:

| Engine | Flag (checked with `--help` 2026-11-20) | Use |
|---|---|---|
| claude | `--append-system-prompt-file <path>` (listed in `claude --help`) | Pass the role file, so the role survives compaction as system prompt |
| codex | No instructions-file flag in `codex exec --help`; `-c key=value` overrides config | Brief prefix only. Optionally `-c model_instructions_file=<path>`, but verify the key on the installed version before relying on it. `AGENTS.md` is per-directory and shared, so it is not used per role |
| opencode | `opencode run --agent <name>` | Generate `.opencode/agent/<role>.md` from the role file at deploy. Brief prefix stays the source of truth |

Guard: a spawn whose header key names a missing or schema-failing file is refused
(`REFUSED-SPAWN role-file-invalid`) and does not start without its role.

## 3. Learned entries and the review gate

- **Append**: a session adds `- YYYY-MM-DD — rule — why — session` under `## Learned`. It works in a
  fresh `origin/main` worktree on branch `<role>/learned-<date>`, makes a pathspec commit of that one
  file, and pushes with `serialized_push.py`. No other section changes in that commit.
- **Lint**: a pre-commit check in diff-scoped mode. A commit by a non-owner that touches a role file
  outside `## Learned` is refused, unless it carries `Role-Review: <owner roster id> <corr_id>`.
- **Review**: the live owner session reviews promotions from Learned into Decision Rules and any
  structural edit. If no owner is live, the edit waits for the next owner session; it is not applied
  by a peer.
- Anything that changes shared policy is drafted under `ratify/`, because `agents/shared/*.md` and
  `CLAUDE.md` are human-only.

## 4. Handoff → role mapping

| Role | Handoffs |
|---|---|
| autokernel | autokernel-loop, autokernel-akx-program, kernel-champion-and-promotion (champion tracks; promotion stays operator-gated), rocm-kernel-authoring (INF-48), workspace-58-champion-calibration |
| autopilot | autopilot-program (all tracks); autopilot-surface boxes in harness-program, by box tag rather than by header |
| pipeline-mgmt | churn-pipeline, coordination-and-churn-pipeline |

All other handoffs stay with the generic Codex brief. With the header key in place, the
Codex-off-AK/autopilot rule becomes structural: the dispatcher never auto-starts a Codex lane on a
handoff whose role is `autokernel` or `autopilot`.

## 5. Roster follow-ups (pipeline-mgmt, D9-acked)

Add `autopilot` and `pipeline-mgmt` service rows to `coordination/session-bus/config.yaml`.
`autokernel` already exists, and `codex-ak-main-01a11473` is stale. No `agents/shared` change is
needed for this proposal.
