# 2026-09-17 — sub-episodic-leak: prepared the purge of the HumanEval/55 and Aschoff leaks from memory and state backups

Operator decision: "clean both". This session **prepared** the purge. It did not run it on live data.

Commit: epyc-orchestrator `41baad2b` (branch `sub/episodic-leak-cleanup-20260917`), pushed to `origin/main`. Worktree: `/mnt/raid0/llm/worktrees/sub-episodic-leak`. It adds two files:
- `scripts/maintenance/purge_eval_leak_memories_20260917.py`
- `scripts/maintenance/purge_eval_leak_memories_20260917.sh` (the wrapper; it uses `$ORCH/.venv/bin/python` for faiss)

## Inventory (dry-run over the real stores, read-only)

**Signature.** 190 leak shingles from 12 pool rows (`simpleqa_general_00912`/`00795`, `sv_HE-R{,+}_HumanEval/55::sol0-4`). 21 template shingles were dropped at DF>=32. Anchors: `aschoff`, `hilde`, `jurgen`. Signature digest `506189348e011d91`.

**Episodic stores.** Exactly 4 ids are flagged, and nothing else: `9f75290f`, `d2ddc823`, `e344a27c`, `500740fe`. That is 0 false positives across about 5.7k generic Fibonacci keyword rows. No `episodic.db` holds Aschoff text. The ids appear in both `memories` and `memories_appendonly_legacy` (the legacy table exists only from 20260727 on) in 22 files:
- live `sessions/episodic.db`, at positions 18746-18749;
- 11 checkpoints: 20260716, 20260727×3, 20260803×2, 20260804×2, 20260808, 20260809, and `multitier_v10` (pinned);
- 10 backups: `episodic.db.pre-repair-20260727T210348Z`, `pre-reseed-*`×8, and `backups/episodic_routing_poison_*`.

Clean: `.bak`, `.bak_pre_erase`, `.backup-20260415`, `.wipe-bak`, and all worktree fixtures. `worktrees/t2-targeted-recovery-20260810/.../sessions` is a symlink to the live store; the script dedupes it by real path.

**State files.** 15 dirty, each with 1 hit, the `"Jurgen Aschoff university"` query stem in `last_traces`:
- 9 `autopilot_state.json.bak-*`
- 5 `archived_backups/autopilot_state.json.pre-*`
- `autopilot_state.pre-reseed-20260723T124507Z.json`

The live `autopilot_state.json` and every checkpoint `autopilot_state.json` are clean.

**Store oddities.**
- 20260716 carries a pre-existing FAISS desync of +32, with 639k wrong pointers. The purge preserves both exactly.
- 20260727_053326 has a truncated `embeddings.faiss` (950 MB of 2.85 GB) and no `id_map`. Only its DB rows are purged there.

## Design notes
- `repair_faiss_id_map.diagnose()` is used as the consistency oracle, and `repair()` is not called. `repair()` would truncate the historical desync and write GB-sized `pre-repair` copies into the store directories.
- The v10 checkpoint pins `episodic.db`, `embeddings.faiss` and `id_map.npy` in `checkpoint_meta.json`, and the ckpt-leak ratify script verifies the full manifest. So v10 needs `--include-pinned`, which refuses until RATIFY-CKPT-PROMPT-LEAK-20260916 has been applied. It then writes `pinned_repin_proposal.json`. The re-pin of the v10 meta and receipt is a human-only ratification amendment.

## Tests (throwaway copies, since removed)
All of these passed:
- refusal on the live :8000 listener (exit 3, and the procedure is printed);
- refusal when a process holds the DB open (exit 3);
- refusal when the AutoPilot lock is held;
- live apply: the integrity check is HEALTHY and the raw marker count is 0;
- pinned: refused before the ratify, purged after it, and the proposal is written;
- the 20260716 desync is preserved, and the diagnose deltas are exact;
- index-only DB-only purge;
- rollback after an injected publish failure restores the preimage;
- idempotent re-run (0 DIRTY);
- `--verify` passes;
- state redaction is a single-line diff.

## Operator sequence
The sequence is in the final report to the main session. The API stop/start is operator-controlled, and AutoPilot must stay stopped.
