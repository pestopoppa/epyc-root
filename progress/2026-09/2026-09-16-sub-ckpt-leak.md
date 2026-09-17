# 2026-09-16 — sub-ckpt-leak: operator ratification to close the eval-leak rewind hole

Operator decision: option A. This session prepared the ratification and did not apply it. Branch `sub/ckpt-leak-ratify-20260916` @ `f00e5c9c` (worktree `/mnt/raid0/llm/worktrees/sub-ckpt-leak`) is not pushed.

## Inventory
Sources a rewind reads (`StructuralLab.restore_checkpoint`):
- `CHECKPOINT_FILES`
- `prompts/`
- `classifier_config.yaml`
- `autopilot_short_term_memory.md`
- `strategy_store/`

Scan method:
- grep for `Aschoff`, `University of Bonn`, and the HumanEval/55 solution code;
- 8-token shingles (MHS-3 tokenisation, pool DF<32) of `simpleqa_general_00912`/`00795` and `sv_HE-R{,+}_HumanEval/55::sol0-4`.

Leaked copies:
- `prompts/rules.md` sha256 `b250c227…` in 10 checkpoints: 20260716_062336, 20260727_005741, 20260727_030219, 20260803_120918, 20260803_130944, 20260804_104155, 20260804_152401, 20260808_184245, 20260809_115107, and multitier_v10_20260810 (= production_best).
  - All 10 are byte-identical to `09bdb998^`.
  - The fixed file `09bdb998:rules.md` is `18f8ea01…`.
- 20260727_053326 has no prompts/.

Clean:
- The HumanEval/55 copy (`src/prompts/coder_system.txt`) is not checkpointed.
- No hit in state, AP-22 memory, classifier config, skills.db (0 rows) or the strategy store (1428 rows, no prompt snapshots).

Pins:
- the v10 `checkpoint_meta.json` `file_sha256` (the only manifest; the older metas carry no hashes);
- the v10 receipt `production_checkpoint.metadata` (`file_sha256` plus `checkpoint_sha256` `c60364f1…` = canonical hash over the manifest plus the meta file hash).

A rewind verifies **no** hash, so the pins are attestation only.

Out of scope (recorded in the receipt):
- `episodic.db` holds 4 HumanEval/55 task memories, in every checkpoint and in the live store.
- The `autopilot_state*.bak*` files mention Aschoff in `last_traces`.

## Deliverables
- `scripts/operator/ratify_checkpoint_prompt_leak_20260916.sh` (dry-run by default, `--apply`, `--verify`):
  - checks pins and the full v10 manifest;
  - refuses on inventory drift and on the AutoPilot lock;
  - writes a durable backup to `/mnt/raid0/llm/backups/ckpt-leak-20260916/`;
  - swaps the two Example 4b lines, giving `18f8ea01`;
  - re-pins the meta (`54224ec7`, checkpoint `a604276f`) and the v10 receipt (`e6682b2f`);
  - writes the decision receipt, the keyed index `RATIFY-CKPT-PROMPT-LEAK-20260916`, and the section-5 consolidated receipt;
  - rolls back on any failure and is idempotent.
- `scripts/operator/run_ckpt_leak_ratify_20260916.sh`, the operator wrapper:
  - fresh worktree `op/ckpt-leak-ratify-apply`;
  - asks the operator to type RATIFY;
  - requires `--operator`;
  - commits exactly 4 paths and does not push.

Operator command (after the main session pushes):
```
bash -c 'bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ckpt_leak_ratify_20260916.sh) --operator pestopoppa'
```

## Tests (throwaway copy, since removed)
Ratify script: 24/24 passing.
- rollback on a late refusal of the section-5 receipt;
- refusal on pre-state tampering, v10 receipt tampering, inventory drift and the held AutoPilot lock;
- apply;
- a sandboxed `restore_checkpoint()` from production_best: 39/39 files match the re-pinned manifest, and rules.md = 18f8ea01;
- `--verify`;
- re-run prints ALREADY RATIFIED;
- refusal on post-state tampering.

Wrapper, in test mode:
- apply, then a commit of exactly the 4 paths;
- `--resume` reports already done;
- refuses when the worktree already exists;
- `--yes` and a missing `--operator` are refused through the `bash <(…)` form.

## Notes for the main session
- The shared orchestrator clone `/mnt/raid0/llm/epyc-orchestrator` is on `main` @ `3e967e27`. That does not contain `09bdb998`, so the live `orchestration/prompts/rules.md` and `constants.py` there **still carry the leak** until someone fast-forwards the clone. That is outside this sub's scope because the clone is shared.
- The wrapper refuses while AutoPilot holds `orchestration/.autopilot.lock`.
