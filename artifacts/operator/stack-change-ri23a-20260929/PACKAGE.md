# Stack-change package: RI-23a, coder_escalation thinks like its :8083 host (UNSIGNED)

**Decision (operator, 2026-09-29).** OP-69 = (a): thinking-on roles run on the chat-completions lane. The operator also said "proceed" on RI-23a in chat on 2026-09-29. This package carries the one registry fix that decision needs.

**The defect.** `coder_escalation` is an alias on the :8083 process (Qwen3.8-27B Q8 on the MI210, host role `architect_critic`). Its declarations disagreed:

| Surface | Before | Where it is read |
|---|---|---|
| `server_mode.coder_escalation.chat_template_kwargs` | `{enable_thinking: false}` | per request, by `registry_loader.chat_template_kwargs_for_role()`; sent in the `/v1/chat/completions` body |
| `roles.coder_escalation.model.disable_thinking` | `true` | the descriptor compiler only |
| Stack priors `acceleration.enable_thinking` | `true`, derived from the host through `server_mode.architect_critic.shared_with` | RI-23's admission to the chat lane |
| The :8083 process (`server_mode.architect_critic`) | thinking ON at `reasoning_effort: medium` (ruling C1) | — |

The kwarg was dead while `coder_escalation` rode `/completion`. RI-23 (orchestrator `e0787feb`) admits every role whose prior says `--jinja` and `enable_thinking: true` to the chat lane when the flag `thinking_roles_chat_lane` is on. Once admitted, the role is sent its own kwargs, so `coder_escalation` runs on the chat lane with thinking **OFF**.

**This is live now.** Orchestrator `a504ba28` turned the flag on in production. The running API (pid 3004477, started 2026-09-29 10:30:18, main `c62fcadd`) has `ORCHESTRATOR_FEATURE_THINKING_ROLES_CHAT_LANE=1`. See `evidence/no_relaunch.txt` §5.

**The fix.** It mirrors the host row and the other alias on the same process (`ingest_long_context`):
- `server_mode.coder_escalation.chat_template_kwargs = {enable_thinking: true, reasoning_effort: medium}`;
- `roles.coder_escalation.model.disable_thinking: true → false`.

Nothing is applied. No process was started, stopped or reloaded, and no inference was run.

## 1. Classification

This is **not** a role move, a model swap or a topology change (change-role shapes a/b/c do not apply).
- No port, process, model, NUMA placement or launch argv changes.
- It changes one request-side kwarg row, plus one compiler-input flag that already agreed with what the compiler derived.
- `evidence/url_kwargs_diff.txt` shows it: of 40 static facts, only `ctk coder_escalation` changed. The 19 URL rows, the 13 live-role prior rows and the thinking-lane role set are identical.

## 2. Acknowledgements (the signature covers these)

- **A-1: latency goes up.** `coder_escalation` answers on the chat lane will include thinking at `reasoning_effort: medium`, split into `reasoning_content`.
  - The RI-23b A/B (`/mnt/raid0/llm/tmp/ri23b/run-20260929T070600/SUMMARY.md`, coder probe) measured `coder_escalation` at **1.44 s** with thinking OFF on the chat lane (76 tokens). That is the current defective state.
  - It measured **5.65 s** with inline thinking on `/completion` (269 tokens, 855 characters of think).
  - Expect the post-fix chat-lane latency to be of the second kind, not the first. Medium effort on the chat lane has not itself been measured for this role.
- **A-2: no llama-server relaunch.** The kwargs are request-side. The bring-up is an API reload only (§7).
  - The proof from the code is in `evidence/no_relaunch.txt`: `chat_template_kwargs` is read per request from the lean registry and put in the POST body.
  - Nothing under `scripts/server` reads it.
  - `disable_thinking` has no consumer outside the descriptor compiler.
  - `coder_escalation` launches no process of its own.
  - The :8083 process already serves `{enable_thinking: true, reasoning_effort: medium}` to `architect_critic` and `ingest_long_context`.

## 3. Surface inventory

### Research: `lane/ri23a-20260929`
- `orchestration/model_registry.yaml` (the master), commit `4ba28678`:
  - `server_mode.coder_escalation.chat_template_kwargs` gets the host's kwargs, with a dated comment;
  - `roles.coder_escalation.model.disable_thinking: false`.

  This is exactly the prepared patch `/mnt/raid0/llm/tmp/ri23b/RI-23a-master-registry.patch`. It was re-verified against research origin/main `48ed3f77`, which was still the tip at preparation, and applied cleanly.

### Orchestrator: `lane/ri23a-20260929`
- `1f437ac5`, tests:
  - `tests/unit/test_registry_chat_template_kwargs.py` expects the new kwargs.
  - **New guard** `test_alias_thinking_kwarg_agrees_with_its_host`: a `shared_with` alias whose request-side `enable_thinking` disagrees with its host's fails. This is the RI-23a defect class. It fails on the pre-fix lean (checked: 2 failed) and passes after.
- `269e755a`, derived: `stack_change_pipeline.py update --numa-mode both --research-registry <lane master>`.
  - **Lean diff:** only the two rows above, plus the header (compile time, cache key, master path).
  - **Descriptors and stack priors:** provenance only (`compiled_at`, sha256, `repo_commit`, research path/sha). The descriptor already derived `coder_escalation` thinking-on from its host.
  - **Summary:** hashes.
- `ac281703`: merge of origin/main `c62fcadd`. Main moved while this package was prepared: `a504ba28` enabled the flag, and `c62fcadd` regenerated provenance. Conflicts were resolved to the lane side, then regenerated.
- `8991000d`, derived: regenerated after the merge. Provenance only.

**Net against origin/main `c62fcadd`:** 5 files (`patches/orchestrator/NET.diff`).

### Root: `lane/ri23a-20260929`
This package only: PACKAGE.md, the ratify script, `tools/snapshot_static.py`, `evidence/` and `patches/`.

### Deliberately not edited
- `roles.coder_escalation.description` in the master still says "alias on architect_general's :8083". That text predates ARCHSWAP. It is cosmetic, is not read by code, and belongs to the next registry pass.
- The orchestrator `docs/chapters/02-*.md`, `04-*.md` and `10-*.md` notes dated 2026-05-20 describe `coder_escalation` on the retired Qwen3.6-35B with thinking off. They are dated history.

## 4. Operator decision already taken; nothing open

- **OP-69 = (a)**, 2026-09-29.
- **"proceed" on RI-23a** in chat, 2026-09-29 (session https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ).

The ratify script records the signature and acknowledgements A-1 and A-2. It takes no options.

## 5. Ordering against other work

- **RI-23 and the production flag are already on main** (`e0787feb`, `a504ba28`). This package fixes the running defect, so land it at the next API-reload boundary.
- **ARCHSWAP B2 is pending.** The :8074 `slot_save_path` drift appears identically in the main baseline and in the lane check (`evidence/pipeline-check-main-baseline.txt` and `evidence/pipeline-check-after-livestate.txt`). This package neither adds to it nor clears it.
- **Any change on main to one of the 6 touched paths** (§6a) makes `ratify_ri23a_20260929.sh` refuse. The derived files move whenever `orchestrator_stack.py` changes (provenance hash). The package is then refreshed by its preparer and re-pinned, never signed stale:
  1. merge origin/main into the orchestrator lane;
  2. run `update` against the lane master;
  3. re-snapshot and re-pin.

## 6. Gates, as run on the lanes (evidence/)

| Gate | Result |
|---|---|
| Patch re-verified against research origin/main `48ed3f77` | `git apply --check` clean. Applied as commit `4ba28678`, which is YAML-valid. The research pre-commit evidence-durability check shows 0 errors (5 pre-existing WAIVED_LOST warnings). |
| `stack_change_pipeline.py update --numa-mode both` (lane master) | lean ok (recompiled from the lane master). Descriptors, stack_priors, procedure_enums and operator_summary were updated. guard, guard_strict, reasoning_effort_certifications, stack_manifest_registry and q_scorer_priors are **ok** (`evidence/pipeline-update.txt`). |
| `check` in the lane worktree (no state file) | Every step ok except runtime_attestation. Its 17 errors are all "unmanaged listener": a lane worktree has no state file, the same as in ARCHSWAP (`evidence/pipeline-check-after.txt`). |
| `check` in the lane with a **copy** of the live state file | Every step ok, plus `declared_env_attestation: ok` over 17 processes. runtime_attestation shows **exactly 1** error, the pre-existing ARCHSWAP-B2 `slot_save_path` drift on :8074 (`evidence/pipeline-check-after-livestate.txt`). |
| The same `check` on origin/main `c62fcadd` (baseline) | The same single error and the same `declared_env_attestation: ok` (`evidence/pipeline-check-main-baseline.txt`). **The lane adds no drift.** |
| Static snapshot diff, main `c62fcadd` vs lane `8991000d` | **PASS:** the only changed fact is `ctk coder_escalation`. 0/19 URLs moved, 0 priors rows changed, and the thinking-lane role set is unchanged (`evidence/url_kwargs_diff.txt`). |
| change-role `assert_alias_clean.py` on a lane scratch view | `coder_escalation → architect_critic` **PASS**; `--all` (9 aliases) **PASS** (`evidence/assert_alias_clean.txt`). |
| `check_shared_with_derivations.py --master-registry <lane master>` | OK, rc 0. |
| Targeted tests: `nice -n 19 taskset -c 0-47 pytest -n 4 tests/unit -k "registry or stack_priors or chat_completions_roles or thinking"`, run at `8991000d` | **599 passed, 6 skipped, rc=0** (`evidence/tests.txt`). |

## 6a. Lanes and commits (all pushed; nothing on any main)

| Repo | Lane | Base (origin/main) | Lane commits |
|---|---|---|---|
| epyc-inference-research | `lane/ri23a-20260929` | `48ed3f77` | `4ba28678` registry |
| epyc-orchestrator | `lane/ri23a-20260929` | `c62fcadd` (merged in at `ac281703`) | `1f437ac5` tests · `269e755a` derived · `ac281703` merge · `8991000d` derived |
| epyc-root | `lane/ri23a-20260929` | `04a82bc8` | this package |

Touched paths:
- research `orchestration/model_registry.yaml`;
- orchestrator `docs/generated/current_stack_summary.md`, `orchestration/derived/stack_priors.yaml`, `orchestration/model_descriptors.yaml`, `orchestration/model_registry.yaml`, `tests/unit/test_registry_chat_template_kwargs.py`.

`patches/<repo>/` holds the lane-only commits as `git format-patch` output, plus `NET.diff` (the lane against its base).

## 7. Bring-up (after the receipt exists; run by the session that owns the inference, at its boundary)

Preconditions:
- `artifacts/operator/receipts/RATIFY-RI23A-20260929.json` exists. It is written next to this package, in whichever root tree the script was run from. Commit it on root `lane/ri23a-20260929`.
- No eval or measurement is running against the API. If one is, SIGSTOP its runner around step 4, or wait for its boundary.

1. **Merge the lanes ff-only to main at the pinned commits, and push with the project's push-lock procedure.**
   - Research: `4ba28678` onto `48ed3f77`.
   - Orchestrator: `8991000d`, which already contains `c62fcadd`.
   - Root: the lane head, which carries the package and the receipt.
   - The shared checkouts are `/mnt/raid0/llm/epyc-inference-research` and `/mnt/raid0/llm/epyc-orchestrator`. Update them in place (`git merge --ff-only origin/lane/ri23a-20260929`); do not switch branches.
   - The lane's `model_descriptors.yaml` provenance names the lane master path, because its hash chain is part of what `check` verifies. Step 2 rewrites it; do not hand-normalize it.
2. **Re-run the derived files against the canonical master.** `update` rewrites only descriptor and priors provenance (the research path becomes the canonical master; sha and commit follow). No port changes, so the ARCHSWAP lean bootstrap is not needed.
   ```bash
   cd /mnt/raid0/llm/epyc-orchestrator
   .venv/bin/python scripts/registry/stack_change_pipeline.py update --numa-mode both
   ```
   Commit the provenance-only result on main ("derived: provenance after RI-23a merge") and push.
3. **Pre-reload proof in the main tree.** This expects the new kwargs from the new lean, before any process sees them:
   ```bash
   cd /mnt/raid0/llm/epyc-orchestrator
   .venv/bin/python -c "from src.registry.registry_loader import chat_template_kwargs_for_role as f; print(f('coder_escalation'))"
   #   expect {'enable_thinking': True, 'reasoning_effort': 'medium'}
   ```
4. **API reload only:**
   ```bash
   python3 scripts/server/orchestrator_stack.py reload orchestrator
   ```
   - Do **not** stop autopilot, and do not reload any model server.
   - The kwargs cache (`_CTK_LOADER`) is per API worker process, so this reload is what makes the change live.
   - Before calling it deployed, check that the new API pid's `ps -o lstart` is later than the step-1 merge time.
5. **Check:** run `stack_change_pipeline.py check --numa-mode both`. Expect the same result as `evidence/pipeline-check-main-baseline.txt`: at most the pre-existing :8074 `slot_save_path` line (gone if ARCHSWAP B2 has run meanwhile), and `declared_env_attestation: ok`.
6. **Serving proof.** Use a real token budget (≥ 2048 `max_tokens`), because thinking bills reasoning against `max_tokens`.
   - **P1.** A `/v1/chat/completions` request pinned to `coder_escalation` (`x_force_role=coder_escalation`, `x_disable_repl=true`) returns non-empty `reasoning_content`. The API log shows `llama POST /v1/chat/completions start role=coder_escalation`, and the `logs/llama-server-8083.log` task counter advances.
     - Before this package, the same request returns `reasoning_content` empty/absent (RI-23b "on" arm: `- (0)`).
   - **P2.** `x_force_role=architect_critic` is unchanged: reasoning is still present, and the kwargs are still medium.
   - **P3.** `ingest_long_context` is unchanged.

## 8. Rollback

`git revert` the research commit and the orchestrator range `c62fcadd..8991000d` plus the step-2 provenance commit. Then run `update` and `reload orchestrator`. No model server was touched, so nothing else moves.

Rollback restores the RI-23a defect (thinking OFF on the chat lane) while the production flag is on. The alternative that avoids the defect is to turn the flag off (reverting `a504ba28`), which is a separate decision.

## 9. Signing

```bash
cd /mnt/raid0/llm/tmp/ri23a-20260929/root/artifacts/operator/stack-change-ri23a-20260929
./ratify_ri23a_20260929.sh --validate-only
RATIFY_OPERATOR="<your name>" ./ratify_ri23a_20260929.sh --attest RATIFY-RI23A-20260929
#   chat consent recorded by a session: add RATIFY_CONSENT_REF="<chat reference>"
```

After the root lane merges, the same package is at `/workspace/artifacts/operator/stack-change-ri23a-20260929/`.

The script **refuses** in these cases:
- `RATIFY_OPERATOR` is unset, empty or a placeholder. The shared guard `scripts/operator/lib/ratify_operator.sh` also refuses the invoking login, system accounts and agent ids.
- The token is already spent.
- A pinned file changed.
- A lane commit is missing from its origin lane.
- **Any touched path moved on origin/main since the lane base.**

It applies nothing.
