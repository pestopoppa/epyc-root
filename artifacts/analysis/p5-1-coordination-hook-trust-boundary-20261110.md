# P5-1 — Trust-boundary analysis of the coordination-plane hook surface (2026-11-10)

Box: `handoffs/active/coordination-and-churn-pipeline.md` P5-1 (~line 5185). Source: `intake-1325#05`.
Zero compute; read-only analysis. Scope = `.claude/settings.json` hooks, `.opencode/plugins/`, and the
scripts under `scripts/hooks/` and `scripts/coordination/` they invoke.

## 1. Headline

- **22 registered Claude Code hook commands** in `.claude/settings.json`: 1 SessionStart, 1 PostToolUse, 20 PreToolUse
  (PreToolUse: 11 Bash-matcher, 8 Write|Edit, 1 Agent|Task). One opencode plugin acts as a hook.
- **`classifierContext`: 0 uses** anywhere in `.claude/settings.json`, `.opencode/`, `scripts/hooks/`, `scripts/coordination/` (grep, 2026-11-10).
- **`hookSpecificOutput`: 2 emitters** — `scripts/hooks/session_start_lane_notice.py:96` (SessionStart, `additionalContext` at :98)
  and `scripts/hooks/planner_readonly_gate.py:53` (PreToolUse `permissionDecision` allow/ask; NOT registered in settings.json, used by a read-only actor seat via argv).
- **`additionalContext`: 4 emitters.** The two above plus three PreToolUse scripts that print a bare top-level
  `{"additionalContext": ...}`: `scripts/hooks/benchmark_context.sh:15`, `claude_accounting_context.sh:15`, `skills_context.sh:15`.
  Finding: that top-level shape is not the `hookSpecificOutput.additionalContext` envelope, so it is likely inert (never reaches the model);
  static strings only, no bus/stdin data interpolated. Low risk; recorded, not a boundary issue.
- **No hook reads the bus for content it then re-emits.** The coordination-plane path from bus text to a main's consent state is
  currently absent in the hook surface; this analysis declares it must stay absent (section 4).

## 2. Hook inventory

Deny convention: PreToolUse guards deny with **exit 2 + stderr** (not JSON). Fail mode column: open = allow when the check cannot run.

| # | Event / matcher | Script | Reads | Emits | Fail mode | Boundary crossed |
|---|---|---|---|---|---|---|
| 1 | SessionStart | `session_start_lane_notice.py` | `CLAUDE_PROJECT_DIR`, git/worktree state; stdin unused | `hookSpecificOutput.additionalContext` (static notice, :96-98) | open (`sys.exit(0)` :108) | hook -> model context (static, hook-authored text) |
| 2 | PostToolUse Bash | `posttool_kb_rag_update.sh` | stdin `tool_input.command`; git HEAD | writes KB-RAG index + log (via `.claude/hooks/post_commit_kb_rag_update.sh`); no stdout decision | open (errors non-fatal) | tool output -> filesystem (index). No context channel |
| 3 | PreToolUse Bash | `check_pytest_safety.sh` | stdin command | exit 2 | closed on match | agent command -> host CPU |
| 4 | PreToolUse Bash, Write\|Edit | `check_live_holder_interference.sh` | stdin; CPU region claims (coordination state), running scripts | exit 2 (:98,:131) | open on parse failure | agent -> live bench/coordination claims (R10) |
| 5 | PreToolUse Bash | `check_commit_hygiene.py` | stdin; git index; env bypass var | exit 2 | closed on match; bypass only via session env | agent -> shared repos |
| 6 | PreToolUse Bash | `check_d9_loop_plane.py` | stdin; staged diff vs fleet-behavior paths (`session-bus/config.yaml`, `BUS_PROTOCOL.md`, schema, `compute_policy.yaml`) | exit 2 | closed on match | agent -> **coordination policy plane** |
| 7 | PreToolUse Bash | `check_process_pattern_kill.sh` | stdin; scanner | exit 2 | closed for unambiguous form, scanner-failure fallback | agent -> other sessions' processes |
| 8 | PreToolUse Bash | `check_operator_apply_copy.sh` | stdin; protected operator scripts | exit 2 | closed on derivation | agent -> **operator-gated apply/ratify scripts** |
| 9 | PreToolUse Bash | `check_destructive_scratch.sh` | stdin; `destructive_scratch_pins.json` | exit 2; no override | open on unparseable | agent -> shared scratch/worktrees |
| 10 | PreToolUse Bash | `check_git_clean.sh` | stdin; `git clean -n` | exit 2; `REVERT_VERIFIED=1` in-command override | closed on non-empty | agent -> untracked data |
| 11 | PreToolUse Bash | `check_destructive_git.sh` | stdin; target repo | exit 2 | closed on match | agent -> shared git metadata |
| 12 | PreToolUse Bash, Write\|Edit | `check_filesystem_containment.sh` (+ `.opencode/plugins/filesystem-containment.ts` `tool.execute.before`, :56) | stdin command/file_path; `filesystem_allowlist.yaml` | exit 2 (ts: throws) | closed | agent -> host outside containment root |
| 13 | PreToolUse Bash | `check_llama_cli_guard.sh` | stdin | exit 2 | closed | agent -> CPU region lock/disk |
| 14 | PreToolUse Write\|Edit | `agents_schema_guard.sh` | stdin file_path; file | exit 2 | open if file absent | agent -> agent-file schema |
| 15 | PreToolUse Write\|Edit | `agents_reference_guard.sh` | stdin; post-edit content | exit 2 | open if no jq/file | agent -> governance docs |
| 16 | PreToolUse Write\|Edit | `check_trust_boundary_edit.sh` | stdin; `human_only_paths.yaml` + `.sha256` | exit 2; override `EPYC_ALLOW_TRUST_BOUNDARY_EDIT=1` (operator env) | Layer 1 never degrades; Layer 2 open on unparseable list | **agent -> human-only trust boundary (INV 4)** |
| 17-19 | PreToolUse Write\|Edit | `benchmark_context.sh`, `claude_accounting_context.sh`, `skills_context.sh` | stdin file_path | top-level `additionalContext` (static) | open | hook -> model context (static, likely inert) |
| 20 | PreToolUse Agent\|Task | `check_agent_dispatch.py` | stdin; agent frontmatter; `CLAUDE_PROJECT_DIR`, `AGENT_DISPATCH_AUDIT_LOG` | appends `logs/agent_dispatch_audit.jsonl`; no deny (0 exit-2 paths) | open | main -> subagent dispatch (audit only) |

(Matcher fan-out makes `check_filesystem_containment.sh` and `check_live_holder_interference.sh` each register twice; unique scripts = 20 plus the opencode plugin.)

Unregistered/adjacent: `planner_readonly_gate.py` (PreToolUse `permissionDecision`, fail = **ask**, closed; the only hook that writes a permission decision),
`check_question_discipline.py`, `check_instruction_surface_ratified.py`, `check_test_collectability.py`, `check_sigpipe_grep_q.py`, pre-commit/pre-push scripts (git-hook plane, not Claude hooks).
`scripts/coordination/` scripts are invoked by daemons, not by Claude hooks; none emits hook JSON (grep clean). `session_bus.py` is reached only by agents via Bash, so it is data plane, not hook surface.

## 3. Trust-boundary summary

1. Hook -> model context is the only channel by which a hook can influence a main's reasoning. It is used by 4 scripts, all with static hook-authored text.
2. Hook -> permission/consent state: only `planner_readonly_gate.py` (`ask`/`allow` on its own seat); every other deny is exit 2.
3. Hook -> human-only paths: #16 enforces INV 4 mechanically; #6 and #8 protect the coordination policy plane and operator scripts.
4. Fail-open surface (#2, #4, #9, #14, #15, #17-20, #16 Layer 2) is deliberate per each header; backstops are `session_bus.py validate`, coordinator audit, hygiene tick.

## 4. DECLARATION — PostToolUse `hookSpecificOutput.classifierContext` is OUT OF BOUNDS

**No coordination-plane hook (any script in `.claude/settings.json`, `.opencode/plugins/`, `scripts/hooks/`, `scripts/coordination/`, or any future hook) may emit
`hookSpecificOutput.classifierContext`, on PostToolUse or any event.** Rationale (`intake-1325#05`): the permission classifier may weigh a user statement relayed
through this field as user intent, so a relayed statement can satisfy a **consent bar** that a real user turn would satisfy (never a hard boundary). That is a
concrete write path from any hook script — and thus from anything the hook reads (bus files, tool output, env) — into a main's CONSENT state. It violates
INV 4 in spirit (authority must not be assertable by relay) and INV 1 (authorship derived from path, never asserted). The coordination plane carries no consent;
consent is a human turn or a hash-pinned human-only path. Current state: 0 uses (compliant). `additionalContext` stays permitted only with static, hook-authored text;
a hook that interpolates bus/tool-output/stdin content into `additionalContext` needs P5-1 review first.

### Mechanical guard (added)
`scripts/hooks/tests/test_no_classifier_context.py` — scans `scripts/hooks`, `scripts/coordination`, `.opencode/plugins`, `.claude/hooks`, `.claude/settings.json`
(non-test files) and **fails** on any `classifierContext`, and fails on any *new* `hookSpecificOutput` emitter outside the pinned two
(`session_start_lane_notice.py`, `planner_readonly_gate.py`), forcing review. Result 2026-11-10: `OK: 0 classifierContext uses`. Recommended follow-up (owner session
applies): wire it into the existing hook test sweep / pre-commit so it runs on every hook change.

## 5. Operator token-request — proposed INVARIANTS text (human-amendment-only; NOT applied)

`agents/shared/INVARIANTS.md` is a human-only path. Proposed additions for the operator's signature:

- **Invariant 1 (Single writer) — append:** "No hook may write into another agent's consent, permission or classifier state; in particular no hook emits
  `hookSpecificOutput.classifierContext`. Authorship of intent is derived from the turn/path, never relayed through a hook."
- **Invariant 4 (Trust boundaries are human-only) — append:** "Consent is not a coordination-plane value: bus content, tool output and hook output
  can never satisfy a consent bar. A relayed user statement (including via `classifierContext`) is untrusted data. Enforced by
  `scripts/hooks/tests/test_no_classifier_context.py`."

## 6. Findings summary

- 0 `classifierContext` uses; guard test added and passing.
- 2 `hookSpecificOutput` emitters, 4 `additionalContext` emitters (3 use a likely-inert bare top-level shape at the cited lines).
- Only `planner_readonly_gate.py` writes a permission decision (fail-closed to `ask`).
- Action for owner: tick P5-1 design half, file the INVARIANTS token-request, optionally normalize or drop the three bare `additionalContext` scripts.
