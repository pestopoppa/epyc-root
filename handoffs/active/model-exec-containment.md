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
- [x] **SEC-EXEC-3 — No network for model-exec children.** Probe host support first (unprivileged network namespace or Landlock network rules), then run run_shell and run_python_code children without network; web_fetch stays the only network tool and gains a private-range and link-local deny; tests show a child connect() fails while web_fetch to a public URL works (deny-by-default, because a trusted-domain allowlist can host the payload: intake-2191#07).
  - Probe 2026-10-21 (agent sandbox, user node, kernel 6.14.0-37): `unshare -rn true` fails EPERM (uid_map write; AppArmor userns restriction likely) so no netns; Landlock ABI 6, so Landlock net rules (TCP bind/connect only) are available. Re-probe as the actual service user before choosing. Still OPEN: the child no-network enforcement and the web_fetch private-range/link-local deny (web_fetch currently has none; only audit logging was added).
  - ✅ 2026-10-22 (landed, flag-gated, DEFAULT OFF) — orchestrator `bbc74d5c` (origin/main, 8 commits on `d0e0e477`): `fe0244af` Landlock (ABI 6, TCP connect/bind deny) + seccomp shim for run_shell/run_python_code children (`exec_sandbox.py`, `_fence_kernel_shim.py`; refuses visibly when the host cannot enforce, never runs the command unrestricted), `e29ebadf` `web_guard.py` private-range/link-local deny for web_fetch/fetch_docs (redirect, DNS-rebinding, non-canonical-IP safe), flags in `bdb9b858` (`exec_containment`, `web_fetch_guard`). Tests: `test_sec_exec3_5_sandbox.py::test_child_has_no_network_but_the_control_does`, `test_sec_exec3_web_guard.py`. Acceptance (tests: child connect() fails, public web_fetch works) is met by the code; it is NOT in force until the flags are turned on (task SEC-EXEC-POST-e below).
- [x] **SEC-EXEC-4 — Durable tool-call audit log.** Append-only rotated JSONL with one record per run_shell / run_python_code / web_fetch call INCLUDING refused, timed-out and errored calls (tool, argv or code text plus sha256, cwd, exit, duration, refusal reason, role, request id); today ExplorationLog is in-memory and run_shell records only successful calls; a test shows a refused call is recorded. ✅ 2026-10-21 — same commits: `<log_dir>/tool_call_audit.jsonl` (override ORCHESTRATOR_TOOL_AUDIT_LOG), RotatingFileHandler 20MB x 10, one redacted record per run_shell / run_python_code / web_fetch call incl. refused, timed-out and errored; refused-call test passes. Gate: 10 REPL/fence/task_root suites 367 passed, 1 skipped.
- [x] **SEC-EXEC-5 — No credential-file reach from model-exec children.** Children run under a separate uid or a production Landlock read-deny covering $HF_HOME/token, $HF_HOME/stored_tokens, ~/.git-credentials, ~/.config/gh and the agent-CLI auth directories, and get a token-free HF_HOME (the API sets HF_HOME to the shared cache at orchestrator_stack.py:2466 @ 50f7ffbd); a test shows open() of each path fails in a child while ordinary tool calls work (intake-2208#record).
  - ✅ 2026-10-22 (landed, flag-gated, DEFAULT OFF) — `fe0244af`: production Landlock read-deny over the credential path set ($HF_HOME token files, ~/.git-credentials, ~/.config/gh, agent-CLI auth dirs; operator extra-deny honoured; rules deny paths that do not exist yet) plus token-free HF_HOME for contained children (`test_child_env_has_a_token_free_hf_home_only_when_contained`); `1b971951` /proc environ bypass test. Tests: `test_credential_files_are_unreadable_to_the_child_and_ordinary_files_are_not`, `test_credential_path_set_covers_the_handoff_list`. In force only once `exec_containment` is on (SEC-EXEC-POST-e).
- [x] **SEC-EXEC-6 — HF token hygiene (operator decision package).** Options: (a) revoke the token under /mnt/raid0/llm/cache/huggingface if no gated-model pull needs it; (b) keep a read-only fine-grained token, mode 0600, in a path only the download wrapper reads (recommended if gated pulls exist). Then chmod, give the nextplaid containers a token-free cache mount, and record the decision; token values are never printed.
  - *(2026-10-21, operator.)* Decided option (a): revoke and delete. The local token files are deleted by the owning session; the revoke on huggingface.co can only be done by the operator.
  - *(2026-10-22, status.)* Code side landed: `1b971951` points nextplaid-code/docs at `{cache_dir}/huggingface/hub` only (`orchestration/launch_manifest.yaml`, token files no longer visible to the containers) and adds an HF-token-reappearance warning. LEFT OPEN: the running containers still hold the old root mount until recreated (SEC-EXEC-POST-c); tick this box after the recreate is verified.
  - [x] **DECLINED by operator (2026-10-22):** revoke HF token on huggingface.co. Closed as declined via AskUserQuestion: the token lived only on this host, was never committed, and both local files (`token`, `stored_tokens`) were deleted 2026-10-21; nothing depends on the revoke. Residual risk accepted: a host process could have copied it while `stored_tokens` was 0664. ✅ 2026-10-22
  - ✅ 2026-10-22 — acceptance met: token files deleted (2026-10-21), option (a) decided, nextplaid containers recreated with the token-free `huggingface/hub`-only mount and verified with `docker inspect` (SEC-EXEC-POST-c).
- [x] **SEC-EXEC-7 — First-seen destination and out-of-root write flags.** Depends on SEC-EXEC-4: each audit record carries first_seen_host and write_outside_root booleans, and a zero-token daily summary lists flagged calls for review.
  - ✅ 2026-10-22 (landed, flag `exec_write_flags` DEFAULT OFF) — `bdb9b858` + `fe0244af`: `write_audit.py` adds `first_seen_host` / `write_outside_root` to each audit record, `scripts/security/tool_audit_summary.py` is the zero-token daily summary; tests `test_sec_exec7_audit_flags.py`. Live proof of the new fields on a real API process is still owed (SEC-EXEC-POST-d).
- [x] **SEC-SECRETS-1 — HF and W&B key patterns plus a name-only history scan.** Add hf_ and W&B key patterns with fixtures to scripts/hooks/pii_precommit.sh, install the hook in epyc-web, run a one-off history scan of the epyc-* repos that reports path and commit only (never the value), record the result and rotate anything found (intake-2208#07).
  - *(2026-10-21, operator.)* D9 ack approved: commit with trailer `D9-ack: operator 2026-10-21 (SEC-SECRETS-1 hook patterns)` after its tests pass.
  - ✅ 2026-10-22 — patterns: root `a7bfde22d` (hf_/W&B in `scripts/hooks/pii_precommit.sh`, fixtures `research/fixtures/pii_secret_tokens_hf_wandb.jsonl`; D9-ack 2026-10-21); epyc-web in the hook installer (operator ack 2026-10-22; `install_git_hooks.sh` run, all repos ok); scan tool `scripts/audit/secret_history_scan.py` (`3508bd4aa`, name-only by construction, test proves the planted value is absent from all output). History scan run 2026-10-22 over every ref of epyc-root, epyc-orchestrator, epyc-inference-research, epyc-web, HF + W&B families, `nice -n 19`, read-only: real findings 0 / 0 / 0 / 0 (commits scanned 8430 / 3990 / 6299 / 9). Only hits: 10 allowlisted, all in the documented fake-token fixture `research/fixtures/pii_secret_tokens_hf_wandb.jsonl` (root commits `d008394c5`, `3508bd4aa`). Nothing to rotate; nothing rewritten. Re-run when the pattern set widens (`--all-families` is the broad, noisy mode and was not run).

## Post-landing steps (2026-10-22, workspace-f8)

- [x] **SEC-EXEC-POST-c — Recreate the nextplaid-code and nextplaid-docs containers (owning session runs this; NOT run by f8).** The manifest now mounts only `{cache_dir}/huggingface/hub`; the running containers still hold the old cache-root mount (token files already deleted 2026-10-21, but the mount shape must change so a token reappearing is not exposed). `start_docker_container` does `docker rm -f <name>` then `docker run` from `orchestration/launch_manifest.yaml`, and the aux reload path kills listeners on the port first. Command, one container at a time, from `/workspace/repos/epyc-orchestrator`: `python3 scripts/server/orchestrator_stack.py reload nextplaid-code`, wait for health on :8088 (`/health`), then `python3 scripts/server/orchestrator_stack.py reload nextplaid-docs`, wait for :8089. Prove: `docker inspect nextplaid-code nextplaid-docs --format '{{.Name}} {{range .Mounts}}{{.Source}} {{end}}'` shows only `.../huggingface/hub`, and a code/docs search still returns results. (Retrieval briefly unavailable per container; do not do it mid-eval.) Then tick SEC-EXEC-6.
  - ✅ 2026-10-22 (main session, ~21:33Z, operator decision (b)) — recreated ONLY the two containers, one at a time: `orchestrator_stack.py reload nextplaid-code` then `nextplaid-docs`; both healthy, models loaded, docs index served; mounts now `{cache_dir}/huggingface/hub -> /root/.cache/huggingface/hub`, verified with `docker inspect`; shared orch clone fast-forwarded to `074e9148` first.
- [ ] **SEC-EXEC-POST-d — Live proofs after the operator's API reload** (`orchestrator_stack.py reload orchestrator` only; never the whole stack, autopilot stays up). With the new code live and flags still off, then each flag on a canary: (1) a fresh `tool_call_audit.jsonl` record carries `first_seen_host` and `write_outside_root` (needs `exec_write_flags` on); (2) a `fetch_docs` call appears in the audit log (SEC-EXEC-4 covers web_fetch; confirm fetch_docs specifically); (3) the `seen_hosts` file is created and a repeat host is not flagged first-seen; (4) `scripts/security/tool_audit_summary.py` renders the flagged calls. Record file names and counts only, never call arguments.
- [x] **SEC-EXEC-POST-e — Decision package: turn on `exec_containment` and `web_fetch_guard`?** Operator decision (see the package below); `exec_write_flags` is observe-only and can precede both. Recommendation and tradeoffs are in the package; nothing is enabled by f8.
  - ✅ 2026-10-22 DECIDED (operator, AskUserQuestion): Option A, staged. Order: `exec_write_flags`, then `web_fetch_guard`, then `exec_containment`; each step = one API reload (operator runs it manually) + live proof.
  - [ ] **SEC-EXEC-POST-e1 — Step 1: `exec_write_flags` ON.** Orch branch `f8/exec-guards-step1` @ `a73af3cc` (one line in `PRODUCTION_FEATURE_WAVE_OVERRIDES`, `scripts/server/orchestrator_stack.py`); land to orch main, then apply at the operator's API reload + live proof (`write_outside_root` in `tool_call_audit.jsonl`).
  - [ ] **SEC-EXEC-POST-e2 — Step 2: `web_fetch_guard` ON.** Same one-line override, apply at the operator's next API reload + live proof (private/link-local/metadata fetch refused, public fetch OK).
  - [ ] **SEC-EXEC-POST-e3 — Step 3: `exec_containment` ON.** Same one-line override, apply at the operator's next API reload + live proof (child has no network, scratch HOME, credential read denied); run the REPL/tool suites on the canary first.

### SEC-EXEC-POST-e decision package

- Question: enable `exec_containment` (Landlock+seccomp child sandbox: no network, credential read-deny, token-free HF_HOME) and `web_fetch_guard` (private-range/link-local deny) in production, and when.
- Option A, recommended: enable `exec_write_flags` first (observe only), then `web_fetch_guard` (narrow: blocks only private/link-local/non-canonical destinations), then `exec_containment`, each after one API reload and one live-proof pass (POST-d), spaced so a regression is attributable. Tradeoff: slower, three reloads; each step reversible by flag.
- Option B: enable all three in one reload after POST-c and POST-d. Faster; a failure cannot be attributed to a single flag. `exec_containment` refuses visibly when the host cannot enforce, so a bad host shows as refused tool calls, not silent exposure.
- Option C: leave all off until a model with tool access that is community-origin enters a SEC-ART-3 review. Zero risk of tool regressions; leaves the documented backdoor-reach gap open on the default path, against the handoff objective.
- Known cost to weigh: contained children lose network (an `exec` that pip-installs or curls will fail), and `HOME` is a per-task scratch dir (SEC-EXEC-1). Verify the REPL/tool suites on the canary before the broad flip.

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
