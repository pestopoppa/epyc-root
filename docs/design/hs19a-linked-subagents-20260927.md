# HS-19a stage 1 — "Linked" harness subagents (spec, 2026-09-27)

Owner handoff: [`harness-selection-and-integration.md`](../../handoffs/active/harness-selection-and-integration.md) → HS-19 / HS-19a.
Operator approval: 2026-09-27. Canvas: https://claude.ai/artifact/UnjtMaouUFYs9xz5umnwPd.

## Operator decisions this spec implements

1. **The orchestrator owns model selection for harness subagents.** The harness never pins a model.
   OpenCode's config uses one logical model, `epyc-orchestrator/orchestrator`, for `model` and
   `small_model`. A `task` subagent is just a concurrent request to that provider, not a new process.
2. **The only pin is `x_force_model`**, set by us for evaluation and debugging, never by the harness in
   normal use.
3. **Build order:** stage 1 Linked → 2 Scheduled → 2.5 shared context by pointer → 3 full shared REPLs.

## Stage 1 = record the tree, change nothing else

Every piece is behind a default-OFF switch; with the switches off, live behaviour is byte-identical.

| Surface | What stage 1 adds | Switch |
|---|---|---|
| Orchestrator `/v1` | Resolves the parent link and records it in the inference-tap `request_keys` and the progress (session) log. Model selection, admission and response bodies are unchanged. | feature flag `v1_subagent_link` (default off in test and prod; `ORCHESTRATOR_FEATURE_V1_SUBAGENT_LINK=1`) |
| OpenCode config | A separate opt-in profile re-enables `task` with depth 1. The live template still denies it. | use `config/opencode.subagents.jsonc.template` instead of the live template |
| OpenCode plugin | Opt-in `stampAgentName` adds `x_agent_name` (the chat.params `agent`) to each request. | plugin option, default false |

### Identity resolution (HS-16's header fallback; body always wins)

- session id: body `x_session_id` → `x-dynamo-session-id` → `X-Session-Id`
- parent id: body `x_parent_session_id` → `x-dynamo-parent-session-id` → `x-parent-session-id`
  (OpenCode sends `X-Session-Id` and `x-parent-session-id` natively, `session/llm/request.ts:187-201`)
- a header that disagrees with the body is logged and flagged (`session_id_mismatch`,
  `parent_session_id_mismatch`); the body value is used.
- The P0.2 guard accepts a header-resolved identity for `x_tool_mode=client`, but an OpenCode
  user-agent still needs the body key (a header gives identity, not `x_tool_mode`).

### Refusals (422, same class as P0.2's typed keys)

Malformed id or agent name (header or body); a parent link with no child identity; a session that
names itself as parent; a link that would close a cycle; a session re-linked to a different parent.

### What is recorded

Child calls' tap `request_keys` gain `parent_session_id`, `parent_session_id_source`
(`body` | `header:<name>`), `subagent_depth`, `subagent_depth_basis` (`observed` = parent seen by this
process; `parent_unseen` = lower bound 1), optional `x_agent_name`, and `session_id_source` only when a
header supplied the session id. Root calls with a body session id are unchanged.
Each newly linked child writes one progress-log row: `event_type: session_created`,
`data.kind: harness_subagent_link`, with session, parent, depth, agent name and user id. Trees are
rebuilt from these rows plus the tap; they are the stage-2 training/eval corpus.

Depth comes from a bounded in-process registry (10k sessions, idle TTL 3600 s — HS-16's predeclared
constant until HSF-3 measures the harness-class p99). It is not persisted; the log rows are.

### Harness profile rules (lint-enforced)

Both profiles: no per-agent `model`, no `x_*` in agent options, no `x_force_*` anywhere in config.
Subagents profile: `permission.task` is `{"*":"deny","general":"allow"}`, `subagent_depth` exactly 1,
every enabled sub-agent denies `task` itself (no grandchildren), `small_model == model`, exactly one
provider model, compaction off, share/autoupdate off, the same env file (egress flags; background
subagents off, enforced), `stampAgentName: true`. `explore` stays disabled: user rules merge after its
`"*":deny`, so it would keep bash and is not read-only under this config.

## Acceptance (prepared, run by the main session in a coordinated window)

`scripts/harness/hs19a_acceptance.py` (`plan` / `prepare` / `verify`): OpenCode under the subagents
profile runs a task that spawns one subagent. `verify` checks one `task` part and one child session;
keyed parent and child calls in the tap; the parent link on every child call; the child served by the
orchestrator's normal selection (no pin, same logical model); A5 token parity per session; the
session-log row; and writes SC86 belief rows through the P0.4 write-side hook.
Precondition: the API runs with `v1_subagent_link` on.

## Not in stage 1

Scheduling or capacity decisions from the link (stage 2); HS-16's end-of-session signal and
`session_end_source` (still open under HS-16); HS-17's MCP timeout (needed only if the MCP control
door is enabled); any shared context (stages 2.5/3).
