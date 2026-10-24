# RATIFY-CTXCKPT-HYBRID-20261024 — declare `--ctx-checkpoints 32` on every hybrid serving role

Prepared 2026-10-24 by session 3c4ca599 (subagent). Nothing has been applied: three branches are pushed, none is merged, and nothing was reloaded.

## 1. The one command (operator, from a real terminal)

```bash
cd /mnt/raid0/llm/worktrees/ratify-ctxckpt-root-20261024 && RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_ctx_checkpoints_hybrid_20261024.sh --apply --attest RATIFY-CTXCKPT-HYBRID-20261024
```

- Review first, if you want to (it pushes nothing and writes no receipt): the same command with `--dry-run` in place of `--apply --attest …`.
- After landing (read-only): `--verify`.
- The worktree is epyc-root branch `ratify/ctx-checkpoints-hybrid-20261024` @ `b44b15f7028f22482d7386267026c7dd127fae90`. The script reads its pinned evidence from that checkout.

## 2. Why

- On a hybrid model (gated-delta-net or SSM layers), context checkpoints are the only partial-restore point, so without them any prefix divergence forces a full re-prefill.
- KPF-64.4 measured this on frontdoor (Qwen3.6-35B-A3B qwen35moe, np=4, v10): with checkpoints off, prefix-hit share falls 3.9 pp (pooled −3.87 pp, 95% CI [−6.42, −1.99]) and each request carries about 1,400 more uncached tokens. Sources: `handoffs/active/kv-prefix-fork-and-paged-attention.md` KPF-64.4, `/mnt/raid0/llm/tmp/qb2-kpf64/POLICY_NOTE_DRAFT.md`, and `docs/design/ufh14-b4-prefix-cache-policy-20261003.md` §3.7.
- Today no registry or manifest declares the setting. Every server gets 32 from llama-server's built-in default (`common/common.h:633` in the frozen v10 tree `ffc1bac82`; spellings `-ctxcp` / `--ctx-checkpoints` / `--swa-checkpoints`, `common/arg.cpp:1520`). A change to that default would therefore change production without anyone deciding it.
- Since 32 equals the default, **behaviour is unchanged**.

## 3. What it changes

The repo defines the path itself. The master registry lives in **epyc-inference-research**. The orchestrator copy of `model_registry.yaml` is a LEAN, DERIVED file (stack-change `DERIVATION.md`), so it is regenerated, never hand-edited. Nothing compiled the key before, so the orchestrator needed a code change. That change follows the `cache_idle_slots` precedent (STACKCHG-8083BATCH-20261004 A): compile, emit, attest.

| repo | branch tip (pinned) | files |
|---|---|---|
| epyc-inference-research | `7e201b50efd66899a55aac98149e7238c5eed5a8` (1 commit on origin/main `d3db98e2`) | `orchestration/model_registry.yaml`: `ctx_checkpoints: 32` with a provenance comment, in `server_mode.frontdoor`, `server_mode.architect_critic` and `server_mode.architect_general` (+24 lines) |
| epyc-orchestrator | `aeb077cda08ce7ba6d9a92ce5a2717c9ae78fd03` (4 commits on origin/main `26affbf8`) | **A** `dcaa0774`: `src/registry/stack_priors.py` compiles `runtime.flags.ctx_checkpoints` only when it is declared; `scripts/server/orchestrator_stack.py` adds `("ctx_checkpoints", "--ctx-checkpoints", False, False)` to `_RUNTIME_SERVING_FLAG_ARGS`, emitted right after `--cache-ram`; `scripts/server/stack_commands.py` adds a dedicated attestation that compares the server's RESOLVED value (the last of the three spellings, otherwise 32), plus a `_RUNTIME_FIELD_CHECKS` entry; new `tests/unit/test_ratify_ctxckpt_hybrid.py`. **B1** `b245dfe8`: `stack_change_pipeline.py update` against UNCHANGED research origin/main. This is drift that already exists on main: the lean registry was compiled on 10-21 and the export refuses it as stale. It covers the content-addressed `chat_template_file` path, `runtime_defaults.artifact_integrity`, the DS-V4.1-Flash-Q4 graveyard row and fingerprints, and `start` would recompile the same anyway. **B2** `360fab45`: regenerated against research `7e201b50`. Its content diff is exactly `ctx_checkpoints: 32` on the 3 lean `server_mode` rows and on the 10 priors records those hosts serve, plus fingerprints and timestamps. **C** `aeb077cd`: a fix to the test's tree check (aliases inherit their host's declaration). |
| epyc-root | `b44b15f7028f22482d7386267026c7dd127fae90` (1 commit on origin/main `2b6921ec`; root main has since moved and the script lands onto fresh main regardless) | `scripts/operator/ratify_ctx_checkpoints_hybrid_20261024.sh` and `artifacts/operator/ratify-ctxckpt-hybrid-20261024/{argv_before.json, argv_after.json, argv_diff.txt, gguf_arch.txt}` (sha256-pinned in the script). At apply time the script also writes `landing_argv_*`, `PACKAGE.md` (this file), `artifacts/operator/ratify_ctx_checkpoints_hybrid_20261024.receipt.json` and the keyed index `artifacts/operator/receipts/RATIFY-CTXCKPT-HYBRID-20261024.json`. |

The `--apply` steps, each of which refuses on any mismatch:

1. Check the signer.
2. Check the evidence sha256 pins, and that `origin/<branch>` equals the pinned SHA in both repos.
3. In scratch worktrees on a fresh origin/main, fast-forward to the pin, or do a clean `--no-ff` merge if main has moved. A conflict means the package is STALE and refuses.
4. Check the path allow-list.
5. Run `stack_change_pipeline.py update` (stack-change phase 7). A substantive derived change is committed in scratch; fingerprint churn is discarded.
6. Prove the argv again against the pre-landing origin/main.
7. Run the file-scoped tests.
8. Push research, then orchestrator, then root, each through the `serialized_push.py` push lock as a fast-forward of main.

The script is idempotent and resumable: a pin already on main is skipped, and a run after full landing reports `ALREADY RATIFIED`.

## 4. Role list

Hybrid status was verified from GGUF metadata (`general.architecture`, `<arch>.ssm.*` keys, `full_attention_interval = 4`, `ssm_*` tensors) and from `llm_arch_is_hybrid()` in the frozen v10 `src/llama-arch.cpp:1040-1060`. Evidence: `artifacts/operator/ratify-ctxckpt-hybrid-20261024/gguf_arch.txt`.

**Declared (3 servers, 5 launch targets, 10 roles):**

| server (`server_mode`) | ports | model (GGUF arch) | roles served |
|---|---|---|---|
| `frontdoor` | 8070, 8080, 8180 | Qwen3.6-35B-A3B-MTP-Q8_0 (`qwen35moe`, ssm.inner 4096) | frontdoor + shared_with worker_summarize, worker_general, worker_explore, worker_math, toolrunner, and the alias worker |
| `architect_critic` | 8083 (GPU) | Qwen3.8-27B-Q8_0 (`qwen35`, ssm.inner 6144) | architect_critic + aliases coder_escalation, ingest_long_context |
| `architect_general` | 8074 | Qwen3.8-Flash-Next-UD-IQ4_XS (`qwen4exp`, ssm.* in shard 1, `ssm_*` tensors in shard 2) | architect_general |

The declaration goes on the host `server_mode` row only, the same place `cache_ram` lives. Alias and shared_with roles inherit it through the compiler. `worker`, `coder_escalation` and `ingest_long_context` have `alias_of` rows and are never launched on their own.

**Excluded (non-hybrid or not a serving launch):**

- `worker_vision` / `vision_escalation` (:8086), Qwen3-VL-30B-A3B `qwen3vlmoe`: pure attention, no ssm keys.
- `embedder`, `embedder_1..5` (:8090-8095), bge-large `bert`; `embedder_bge_m3` (:8098) and `embedder_multilingual_e5_base` (:8097), `bert`; `embedder_granite_97m_r2` (:8096), `modern-bert`: encoders, no recurrent state.
- `worker_fast` (:8102), Qwen2.5-Coder-1.5B `qwen2`: pure attention.
- `eval_batch_frontdoor` (:18070): a launcher-only warm eval lane, not a serving role. Its builder emits no declared serving flags (not even `--cache-ram`), and it keeps the kernel default 32. It is outside this change.
- `speech:whisper`, `speech:tts`: not llama-server.
- The model-role catalogue rows (`qwen36_35b_a3b_mtp_q8_local`, `qwen38_27b_q8_local`, `qwen38_flash_next_ud_iq4xs_local`) are benchmark or candidate records, not launch targets.

## 5. Argv-diff evidence

The repo's own offline launcher export, `python -m scripts.server.autokernel_enrollment --instance-mode both`, calls the real `build_server_command(prepare_runtime_dirs=False)` and launches nothing.

- **Before**: origin/main orchestrator code with derived files refreshed against research origin/main (B1-equivalent).
- **After**: the branch tip with the research branch master.

| target | before → after |
|---|---|
| frontdoor@8070, @8080, @8180 | 40 → 42 tokens: `--ctx-checkpoints 32` inserted after `--cache-ram 32768`, nothing else |
| architect_general@8074 | 42 → 44: inserted after `--cache-ram 32768` |
| architect_critic@8083 | 47 → 49: inserted after `--cache-ram 65536` |
| embedder@8090…8095, embedder_granite/e5/bge_m3, worker_vision@8086, worker_fast@8102, eval_batch_frontdoor, speech | **byte-identical** |

- The full `argv` (with its numactl prefix), `environment`, `topology`, `workload` and `aliases` are identical on every target, apart from the two inserted tokens.
- Files: `artifacts/operator/ratify-ctxckpt-hybrid-20261024/argv_{before,after}.json` and `argv_diff.txt`.
- The script repeats this proof at landing time against the then-current origin/main and records it as `landing_argv_diff.txt`. It also requires the hybrid target set to equal the set of targets whose GGUF arch is hybrid.

## 6. Tests and gates run (all in the branch worktrees, no inference)

| what | result |
|---|---|
| `tests/unit/test_ratify_ctxckpt_hybrid.py` (new; compiler, launcher, attestation, this-tree recompute) | **17 passed** |
| touched or adjacent suites plus the pipeline's promotion-gate list: `test_stackchg_8083_idle_slots`, `test_stackchg_8083_batch`, `test_orchestrator_stack_reload`, `test_external_drafter_launch`, `test_diag_env_override`, `test_prefix_cache_policy`, `test_autokernel_enrollment`, `test_stack_change_pipeline_simulated_fixtures`, `test_build_server_command_helpers`, `test_seeding_infra{,_additional,_branching}`, `test_seed_specialist_routing_main_and_retry` | **444 passed, 1 failed**. The one failure was my own tree check, fixed in commit C and re-run: 17/17 pass. |
| `stack_change_pipeline.py update` (B1, B2) | every compile and guard step `ok` (numa_mode, shared_with_derivations, lean_registry, descriptors, stack_priors, guard, guard_strict, reasoning-effort certs, artifact_integrity, serving_shape_capacity, stack_manifest_registry, q_scorer_priors). `runtime_attestation` fails only on lane-worktree live drift ("unmanaged listener on :8000"; a worktree has no state file), the same as the 8083BATCH precedent. |
| start-time `registry_validator.validate_or_raise` on the regenerated lean (gate 2 of the 3 stack-change gates) | OK |
| `orchestrator_stack.py start --validate-only` | PASS, nothing launched |
| ratify script `bash -n` | OK |
| ratify script `--dry-run` (full run: fetch, pins, push locks FREE, ff staging, both `update`s, argv proof, tests) | **DRY-RUN OK, rc 0.** Both repos fast-forward onto origin/main. ARGV CHECK OK: 5 hybrid targets gain exactly `--ctx-checkpoints 32`, every other target is byte-identical, and the hybrid set equals the GGUF-hybrid set. Staged tests: 266 passed. Nothing was pushed and no receipt was written; the scratch worktrees were removed (verified). Log: `/mnt/raid0/llm/tmp/ratify-ctxckpt-20261024/dryrun_1.txt`. |
| `check_ratifier_receipt_contract.sh` | the new script is conformant (writes the keyed index). The checker exits 1 on pre-existing findings only. |

Interpreter note: the brief asked for `/usr/bin/python3 -m pytest`. That interpreter has no `fastapi`, so the conftest cannot load. The orchestrator venv (`/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python`) was used from the worktree instead, which is the same interpreter the ratify script and the precedent scripts use.

## 7. Reload needed?

**No, not for behaviour or attestation.**

- 32 is what every hybrid server already runs.
- The new attestation compares the resolved value, so running servers attest clean the moment this lands.
- The script reloads nothing, and it does not set the stack-change-pending GPU marker, because there is no bring-up.

The flag *appears* in live argv at each server's next ordinary reload. That reload is run by the session that owns the role's inference, at its own boundary (CLAUDE.md, *Reload ownership*). It is a separate, later owner step and not part of the signature. From the orchestrator repo:

```bash
python3 scripts/server/orchestrator_stack.py reload frontdoor           # :8070 / :8080 / :8180
python3 scripts/server/orchestrator_stack.py reload architect_general   # :8074
python3 scripts/server/orchestrator_stack.py reload architect_critic    # :8083 (GPU)
```

Then `tr '\0' ' ' < /proc/<pid>/cmdline` should show `--ctx-checkpoints 32` on each of those pids.

**Side effect to know about:** the AutoKernel production-enrollment recipes are sealed over the production argv. The five hybrid targets' recipe digests change when this lands, because they gain 2 tokens. Any AK campaign pinned to an older export needs a fresh export.

## 8. How to revert

- In epyc-orchestrator and epyc-inference-research, `git revert` the landed commits. The receipt records them:
  - after a fast-forward: `git revert --no-edit 26affbf8..aeb077cd` (orchestrator, 4 commits) and `git revert --no-edit 7e201b50` (research); the receipt records the exact pre-landing bases;
  - after a merge: `git revert -m 1 <merge>`.
- Then the owners reload frontdoor, architect_general and architect_critic at their boundary.
- Reverting restores "inherit the kernel default", which is the same 32 on v10. No data, model or symlink changes.
- Before signing: do nothing. The three branches can be deleted with `git push origin :ratify/ctx-checkpoints-hybrid-20261024` in each repo.

## 9. Open items for the operator

None block signing.

- A guard that refuses `ctx_checkpoints: 0` on a hybrid role at compile time would turn the policy's "never 0" into a structural rule. It is not included, to keep this change minimal. Say if you want it.
- The B1 refresh shows that origin/main's lean registry has been stale against the research master since 10-21. This package lands that refresh too.
