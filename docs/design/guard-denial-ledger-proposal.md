# Guard-Denial Ledger — Proposal (DHM-6)

**Status**: PROPOSAL. Nothing is wired. Hook edits are human-applied (operator 2026-10-22); this document
is the package an operator applies or rejects.
**Task**: DHM-6 in [`handoffs/active/dev-harness-trace-mining.md`](../../handoffs/active/dev-harness-trace-mining.md)
(intake-2387#record, Beacon cross-harness trace capture).
**Consumers**: DHM-2 (guard audit: would-fire / blocked / slipped-through), DHM-3 (lesson ITS: hook-enforced
versus prose-only violation rates), the belief kernel (a source with `fidelity=observed`).

## Problem

Today a guard refusal is visible only as **text inside the transcript**: the harness appends the hook's
stderr to an errored tool result, and the projector classifies it with a regex
(`dh_sources._HOOK_BLOCK_RE`: `PreToolUse:|hook error|hook blocked|^BLOCKED:`). That has three defects:

1. **Fidelity is `inferred`, not `observed`.** A regex over tool-result text is a guess about which hook
   fired and why. A hook whose message changes wording drops out of the count silently.
2. **The rule is not recorded.** One hook (`check_filesystem_containment.sh`, `check_pytest_safety.sh`)
   refuses for several different reasons; the transcript text names none of them in a stable form.
3. **"Executed after its denial" cannot be detected.** The question DHM-2 most needs answered — did the
   agent run the refused command anyway, rephrased, through another tool or another harness — needs the
   refused command's identity on a timeline, joinable to later tool calls. The transcript has the text, but
   only inside sessions we can read; Codex and opencode guards leave no uniform trace at all.

## Proposal

Every PreToolUse refusal appends **one line** to **one private JSONL**, written by the hook at the moment
it decides to refuse, before it exits.

### Record (`dev-harness-guard-denial.v1`)

| Field | Type | Source | Note |
|---|---|---|---|
| `schema` | str | constant | `dev-harness-guard-denial.v1` |
| `ts` | str | hook clock, UTC ISO-8601 ms | |
| `hook` | str | hook's own basename | e.g. `check_process_pattern_kill.sh` |
| `rule` | str | hook-defined stable id | e.g. `pattern_kill.pkill_name`; one id per refusal branch, never message text |
| `session` | str | hook stdin `session_id` (Claude), thread id (Codex), session id (opencode) | per-session key: the ledger is private |
| `harness` | str | `claude_code` \| `codex` \| `opencode` | |
| `source` | str | `epyc` \| `host` \| `twyne` | the container the hook runs in |
| `tool` | str | hook stdin `tool_name` | `Bash`, `Write`, `Edit`, … |
| `cmd_blocks` | list[str] | keyed HMAC of the refused command | same key and 64-token-block scheme as the projector (`hmac-sha256-trunc16/64-token-blocks/v1`) |
| `cmd_n_chars` | int | | |
| `fidelity` | str | constant | `observed` |
| `decision` | str | | `deny` (exit 2); a later `ask`/`warn` mode would use the same ledger |

No command text, no path and no cwd are stored. `cmd_blocks` is the join key: the projector already
writes the same keyed block hashes for every `tool_call` event, so "a later tool call whose argument blocks
overlap a refused command's blocks, in the same session or family, after `ts`" is a mechanical query over
private data, with no transcript reread.

### Location and write discipline

* Path: `/mnt/raid0/llm/private/dev-harness-traces/guard-denials/<YYYY-MM>.jsonl`, directory 0700,
  file 0600 (same root and same `dh_privacy` rules as the projections; outside every git work tree).
* Append under `flock` on the file, one `write` of one line (< PIPE_BUF), so parallel sessions never
  interleave.
* **Best effort, never fatal**: a ledger failure must not change the hook's decision or its exit code.
  The helper swallows its own errors, counts them in a sidecar `guard-denials/.errors` counter, and the
  hook exits exactly as it does today.
* Budget: the append is one HMAC over the command plus one locked write; well under the 1 ms a hook
  already spends parsing stdin. No network, no Python import of the orchestrator.

### Shape of the change (for the operator to apply)

1. Add `scripts/hooks/lib/denial_ledger.py` (stdlib only; the key read from
   `<private-root>/keys/block_hmac.key`, the block hashing imported from `scripts/dev_harness/projector.py`
   or copied with a test pinning equality) and a two-line shell wrapper
   `scripts/hooks/lib/denial_ledger.sh` (`denial_ledger <hook> <rule>` reading the hook's saved stdin).
2. In each refusing hook, call it immediately before each `exit 2` / `sys.exit(2)` with that branch's rule id.
   Refusing hooks today (counts of refusal exits in parentheses):

   | Hook | Matcher | Refusal exits |
   |---|---|---|
   | `check_pytest_safety.sh` | Bash | 4 |
   | `check_live_holder_interference.sh` | Bash, Write\|Edit | 2 |
   | `check_commit_hygiene.py` | Bash | 1 |
   | `check_d9_loop_plane.py` | Bash | 1 |
   | `check_process_pattern_kill.sh` | Bash | 3 |
   | `check_operator_apply_copy.sh` | Bash | 1 |
   | `check_filesystem_containment.sh` | Bash, Write\|Edit | 4 |
   | `check_llama_cli_guard.sh` | Bash | 1 |
   | `agents_schema_guard.sh` | Write\|Edit | 1 |
   | `agents_reference_guard.sh` | Write\|Edit | 1 |
   | `check_trust_boundary_edit.sh` | Write\|Edit | 2 |
   | `codex_filesystem_containment.py` (Codex `[[hooks.PreToolUse]]`) | all | per branch |
   | `.opencode/plugins/filesystem-containment.ts` (opencode `tool.execute.before`) | all | per branch |

   `benchmark_context.sh`, `claude_accounting_context.sh` and `skills_context.sh` only inject context and
   never refuse; they are out of scope.
3. One test per hook that drives a known-refused input and asserts exactly one ledger line with the
   expected `hook`, `rule` and `fidelity=observed`, and that the hook's exit code is unchanged when the
   ledger directory is unwritable.
4. Projector: read the ledger as a fourth input and emit `denial` events with `fidelity=observed`; keep the
   regex classifier for history before the ledger existed, flagged `inferred`. A refusal seen both ways
   counts once, `observed` winning.

### What it enables

* **DHM-2** reports blocked counts per hook and rule from observation instead of regex, and
  **slipped-through-after-denial**: a refused command (by `cmd_blocks` overlap) that a later tool call in the
  same session family executed, by harness.
* **DHM-3** separates hook-enforced from prose-only lessons with an exact exposure denominator: refusals
  per 1000 tool calls per rule, before and after a hook landed.
* **Guard drift**: a rule whose refusal rate falls to zero after an unrelated edit is visible the next day.

### Publication

The ledger itself is per-session and private (F3-LB1). Only aggregates — counts per hook × rule × harness ×
source, rates with Wilson intervals — leave the private root, through `dh_privacy.publish_aggregate`
(schema `dev-harness-aggregate.v1`).

### Alternatives considered

* **Keep the regex only.** Zero cost, but `inferred`, rule-blind and blind to Codex/opencode refusals.
* **Have hooks print a structured marker into stderr and parse transcripts.** Still transcript-bound;
  sessions whose transcripts are not in the vault (live, uncaptured, other harness) are lost, and the marker
  becomes part of transcript content.
* **Log every hook invocation, not only refusals.** Gives would-fire denominators directly but costs a
  write per tool call on a shared box; DHM-2's retrospective predicates already produce would-fire counts
  from the projection. Refusals only is the minimal change.

### Recommendation

Apply steps 1–3 for the Claude Code hooks first (11 hooks, all in this repo, one helper), then the Codex and
opencode guards, then step 4. Expected effort: about one session plus a test per hook.
