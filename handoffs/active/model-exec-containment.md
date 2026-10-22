# Model-exec containment — what an open-weight model's tool calls can reach

**Status**: stub
**Created**: 2026-10-21 (via research intake, operator-approved 2026-10-21 plan intake-backdoor-cvec-20261020)
**Scratch**: `/mnt/raid0/llm/tmp/model-exec-containment/`
**Categories**: agent_architecture, tool_implementation, local_inference
**Related**: [model-artifact-integrity.md](model-artifact-integrity.md) (artifact side) · [qwen-chat-template-evaluation.md](qwen-chat-template-evaluation.md) (CT-12: special-token injection, the input-side sibling — not duplicated here) · [agentic-serving-harness-fixes.md](agentic-serving-harness-fixes.md) (UFH14-A6: Landlock for harness experiments, not production) · [repl-session-memory-maturity.md](repl-session-memory-maturity.md) (D-RI-CONTAIN: the opt-in contained CPython lane for REPL *cells*, no network/secrets; this handoff owns the tool-subprocess path, credential reach and the audit log, and its env/no-network helpers are offered to D-RI-CONTAIN rather than built twice)

## Objective

Assume any open-weight model we serve may carry a trigger-conditioned backdoor that rewrites a tool call
(intake-2191#record demonstrates it for a QLoRA-poisoned tool-calling model; intake-2199#record shows
the class survives clean fine-tuning and evades guardrail screening). Contain what a model-issued
command can reach — environment secrets, credential files, the network — and keep a durable record of
every call, so that a backdoor that fires has nothing to steal and leaves a trace.

## Current state (verified 2026-10-21, orchestrator @ 50f7ffbd)

- `run_shell` allowlists `python`/`python3` (external_access.py:128-152), so its curl/wget block does
  not stop network access; `find`/`awk`/`sed` exec forms are refused only under a task_root scope.
- `run_shell` and `run_python_code` children inherit the full API environment, fenced or not
  (knowledge_fence.py:733/765 build the fenced env from `os.environ`).
- No egress control on any model-exec path; the eval Landlock fence is filesystem-only and eval-only.
- Tool-call logging is the in-memory ExplorationLog; refused, timed-out and errored calls are not recorded.
- The API sets `HF_HOME` to the shared cache (orchestrator_stack.py:2466), which holds an HF token file;
  same-uid credential files (git, gh, agent CLIs) are readable by children.
- Already in place and kept: credential redaction of REPL output before it reaches model context; the
  CT-12.3a control-token neutraliser (input side).
- Already planned elsewhere: D-RI-CONTAIN (repl-session-memory-maturity.md) contains REPL cell execution in an
  opt-in killable child with no network/secrets; it does not cover the run_shell/run_python_code subprocesses,
  the default production path, credential files or tool-call logging.

## Tasks

- [x] **SEC-EXEC-1 — Minimal allowlisted env for model-exec children.** One helper builds the child env (PATH, LANG, TMPDIR and fence variables only) for run_shell and run_python_code, fenced and unfenced: today both pass the full parent environment (external_access.py:227/323/332 and knowledge_fence.py:733/765 @ 50f7ffbd); a unit test plants a fake API key and HF_HOME in the parent and proves both are absent in the child (intake-2191#07). ✅ 2026-10-21 — epyc-orchestrator 644c6530 + 65fbdce3: `child_env` allowlist (PATH, LANG*, LC_*, TZ, TMPDIR/TEMP/TMP, PYTHONIOENCODING/UTF8 + explicit fence vars) in `exec_containment.py`, fenced and unfenced; HOME = per-task scratch dir (+XDG cache/config under it), real home never the child HOME; PYTHONPATH/VIRTUAL_ENV not needed (python3 resolved via PATH, nothing in src relies on them); tests in `test_sec_exec_containment.py`.
- [x] **SEC-EXEC-2 — Close the interpreter hole in run_shell.** Drop python/python3 from the run_shell allowlist (external_access.py:128-152 @ 50f7ffbd; run_python_code is the sanctioned Python path) and apply the task_root command-execution refusals (find/awk/sed exec forms, task_root.py:285-337) unscoped in production; one test per refusal plus a test that `python3 -c` through run_shell is refused. ✅ 2026-10-21 — same commits: python/python3 dropped from the run_shell allowlist; `task_root.check_shell_exec` applies the find/awk/sed exec-form refusals unscoped ("EXEC CONTAINMENT"); one test per refusal plus `python3 -c` via run_shell.
- [ ] **SEC-EXEC-3 — No network for model-exec children.** Probe host support first (unprivileged network namespace or Landlock network rules), then run run_shell and run_python_code children without network; web_fetch stays the only network tool and gains a private-range and link-local deny; tests show a child connect() fails while web_fetch to a public URL works (deny-by-default, because a trusted-domain allowlist can host the payload: intake-2191#07).
  - Probe 2026-10-21 (agent sandbox, user node, kernel 6.14.0-37): `unshare -rn true` fails EPERM (uid_map write; AppArmor userns restriction likely) so no netns; Landlock ABI 6, so Landlock net rules (TCP bind/connect only) are available. Re-probe as the actual service user before choosing. Still OPEN: the child no-network enforcement and the web_fetch private-range/link-local deny (web_fetch currently has none; only audit logging was added).
- [x] **SEC-EXEC-4 — Durable tool-call audit log.** Append-only rotated JSONL with one record per run_shell / run_python_code / web_fetch call INCLUDING refused, timed-out and errored calls (tool, argv or code text plus sha256, cwd, exit, duration, refusal reason, role, request id); today ExplorationLog is in-memory and run_shell records only successful calls; a test shows a refused call is recorded. ✅ 2026-10-21 — same commits: `<log_dir>/tool_call_audit.jsonl` (override ORCHESTRATOR_TOOL_AUDIT_LOG), RotatingFileHandler 20MB x 10, one redacted record per run_shell / run_python_code / web_fetch call incl. refused, timed-out and errored; refused-call test passes. Gate: 10 REPL/fence/task_root suites 367 passed, 1 skipped.
- [ ] **SEC-EXEC-5 — No credential-file reach from model-exec children.** Children run under a separate uid or a production Landlock read-deny covering $HF_HOME/token, $HF_HOME/stored_tokens, ~/.git-credentials, ~/.config/gh and the agent-CLI auth directories, and get a token-free HF_HOME (the API sets HF_HOME to the shared cache at orchestrator_stack.py:2466 @ 50f7ffbd); a test shows open() of each path fails in a child while ordinary tool calls work (intake-2208#record).
- [ ] **SEC-EXEC-6 — HF token hygiene (operator decision package).** Options: (a) revoke the token under /mnt/raid0/llm/cache/huggingface if no gated-model pull needs it; (b) keep a read-only fine-grained token, mode 0600, in a path only the download wrapper reads (recommended if gated pulls exist). Then chmod, give the nextplaid containers a token-free cache mount, and record the decision; token values are never printed.
  - *(2026-10-21, operator.)* Decided option (a): revoke and delete. The local token files are deleted by the owning session; the revoke on huggingface.co can only be done by the operator.
  - [ ] operator: revoke HF token on huggingface.co
- [ ] **SEC-EXEC-7 — First-seen destination and out-of-root write flags.** Depends on SEC-EXEC-4: each audit record carries first_seen_host and write_outside_root booleans, and a zero-token daily summary lists flagged calls for review.
- [ ] **SEC-SECRETS-1 — HF and W&B key patterns plus a name-only history scan.** Add hf_ and W&B key patterns with fixtures to scripts/hooks/pii_precommit.sh, install the hook in epyc-web, run a one-off history scan of the epyc-* repos that reports path and commit only (never the value), record the result and rotate anything found (intake-2208#07).
  - *(2026-10-21, operator.)* D9 ack approved: commit with trailer `D9-ack: operator 2026-10-21 (SEC-SECRETS-1 hook patterns)` after its tests pass.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-2191#record | ProjectDiscovery: QLoRA trigger-phrase backdoor in an open tool-calling model | high | adopt_patterns | dive-verified |
| intake-2199#record | Malice in Agentland: backdoors in the AI agent supply chain | high | adopt_patterns | dive-verified |
| intake-2208 | ProjectDiscovery: pwning AI labs through employees' leaked tokens | high | adopt_patterns | dive-verified |
| intake-2210 | Poisoning attacks need a near-constant number of samples | medium | worth_investigating | dive-verified |

## Open Questions

- Does the host kernel allow unprivileged network namespaces or Landlock network rules for the service user (SEC-EXEC-3 probes this first)?
- Separate uid or Landlock read-deny for credential paths (SEC-EXEC-5): which composes better with the existing eval fence?

## Notes

- Egress denial alone is not enough: a network-restricted backdoored agent can switch to local destructive actions (intake-2199#record), so SEC-EXEC-2 and SEC-EXEC-4 stay in scope alongside SEC-EXEC-3.
- Do not adopt guardrail models or weight-diff monitors as the backdoor defence for tool-bearing roles; they failed in intake-2199#record.
