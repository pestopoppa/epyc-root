# RATIFY-WS58-RETENTION-LESSONS-20261025: one signature, three human-only change sets

Prepared by a workspace-58 subagent on 2026-10-25. **Nothing here has been applied.** Every target is
human-only (`coordination/session-bus/human_only_paths.yaml`: `MEASUREMENT.md`, `CLAUDE.md`,
`agents/shared/*.md`), or is a settings registration that is an operator act (`.claude/settings.json`).
The ledger row in set B is not human-only; it rides with the clause it records.

The hook that set C registers is set **D**: four new files, `scripts/hooks/check_destructive_scratch.sh`,
`scripts/hooks/destructive_scratch_scan.py`, `scripts/hooks/tests/test_destructive_scratch_hook.sh` and
`scripts/hooks/tests/destructive_scratch_cases.py`. Its test passes 37 of 37 and takes about 0.03 s
per call. These files are not human-only. But `scripts/hooks/` is the **D9 loop plane**: every commit
there needs an operator ack (`check_d9_loop_plane.py`), and an agent cannot give that ack. So D rides
in the same signed commit, with a `D9-ack:` line naming you, and does not land unsigned.

## Run it (one command, from a terminal)

```bash
git -C /workspace fetch -q origin main && git -C /workspace worktree add -q --detach /mnt/raid0/llm/worktrees/ratify-ws58-retention-1025 origin/main && RATIFY_OPERATOR='<your name>' bash /mnt/raid0/llm/worktrees/ratify-ws58-retention-1025/scripts/operator/ratify_ws58_retention_lessons_20261025.sh --apply --attest RATIFY-WS58-RETENTION-LESSONS-20261025
```

The script never touches the checkout it is launched from. It stages a detached worktree of a fresh
`origin/main` under `/mnt/raid0/llm/tmp/ratify-ws58-retention.*` and refuses if its own bytes differ from
`origin/main`'s copy. It then checks every pin and runs `git apply --check` on A, B and C one at a time
and then together. It applies all three, proves the post-state, emits the `MEASUREMENT.md` §5
consolidated receipt plus the decision receipt and keyed index, commits nine paths, and pushes
`HEAD:main` under the `serialized_push.py` push lock. The script
applies D as well, and the hook files are among the thirteen paths it commits. Any failure before the commit leaves nothing
changed anywhere. A rejected push lands nothing; re-run it.

- Dry run (default; the full pipeline in a throwaway stage, nothing kept):
  `bash scripts/operator/ratify_ws58_retention_lessons_20261025.sh`
- Verify after applying (read-only): `... --verify`
- Afterwards, remove the launch worktree:
  `python3 /workspace/scripts/system/worktree_gate.py remove /mnt/raid0/llm/worktrees/ratify-ws58-retention-1025`

## What it changes

| Set | File | Section | What it changes | Origin |
|---|---|---|---|---|
| A | `agents/shared/OPERATING_CONSTRAINTS.md` | Filesystem and Storage | + "Scratch is scratch: nothing durable lives only in `/mnt/raid0/llm/tmp`" | ws58 calendar lessons; 2026-10-20 purge took the 10-04 TensorFold study |
| A | `agents/shared/OPERATING_CONSTRAINTS.md` | Operator Decision Requests | + a dismissed question pauses only that item | 2026-10-24 ws58 calendar froze ~40 min |
| A | `agents/shared/OPERATING_CONSTRAINTS.md` | Codex Delegation & Long-Horizon Throughput | + Codex has no compute authority; git limits | ws58 10-24/25 lessons |
| A | `agents/shared/SESSION_LIFECYCLE.md` | Two axioms | + "A result tick names its belief" | belief design §7.4.2 |
| A | `CLAUDE.md` | Belief Kernel — wiring new sources | + recording conclusions is not inventing warrant; tick markers; "wired" = canary | belief design §7.4.3 |
| B | `MEASUREMENT.md` | §5 Governance, after *Evidence must be DURABLE* | + **Evidence retention and reclamation**: evidence homes; reproducible data never carried; three durability classes (aligns §5 with the 2026-08-03 durable-untracked ruling, D7); one reclamation predicate binding every reclaimer (not cited by the enumerated sources, not KEEP-marked, no size threshold, fail-closed, re-checked at plan, execute and purge time, trash-first with a 7-day hold, exact paths, tombstone before unlink); three-state verifier; grants no authority; the 2026-08-03 draft's loop-expiry grant is not enacted. This resolves the §6 reference that dangled. | reconcile doc §5 D2 (recommended option), D7; draft `autokernel-policy-draft/evidence-retention.draft.md` §3.1, §3.4 conjuncts 3/4/5/7/8, three-state verifier |
| B | `MEASUREMENT.md` | CHANGELOG | + 2026-10-25 amendment entry | same |
| B | `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md` | §7 per-item disposition | + an item-5 row recording "applied in amended form"; the pending row is kept (append-only) | same |
| C | `agents/shared/OPERATING_CONSTRAINTS.md` | Destructive operations, item 1 | + **Citation check: cited is not removable** (handoffs, FILLERS, grants and launchers, ledger; no size threshold; fail-closed; `citation_oracle.py` once NIB2-105 lands) | reconcile §5 D4; `work/guards-design.md` §2.7 |
| C | `agents/shared/OPERATING_CONSTRAINTS.md` | Destructive operations, item 2 | + purge only through `trash-sweep.sh` after at least 7 days; never rmtree the trash root | guards-design §2.6, §2.7 |
| C | `agents/shared/OPERATING_CONSTRAINTS.md` | Destructive operations, new item 5 | + reclaims go through `reclaim_scratch.py` (NIB2-108; until it lands, exact paths through `guarded_rm.sh`); inline executors are a violation; the hook and its override | guards-design §2.5, §2.7 |
| C | `.claude/settings.json` | `hooks.PreToolUse[Bash]` | + registers `scripts/hooks/check_destructive_scratch.sh` (timeout 5), placed before the containment hook | guards-design §2.5 |
| D | `scripts/hooks/check_destructive_scratch.sh`, `destructive_scratch_scan.py`, `tests/test_destructive_scratch_hook.sh`, `tests/destructive_scratch_cases.py` | new files | the hook, its scanner and its 37-case test (D9 loop plane, acked by this signature) | guards-design §2.5, §3 test row; NIB2-108 |

All four patches are additions only (zero removed lines; D creates new files only). The script
checks this again after applying.

**Pins:**
- Patches:
  - A `be6928de…`
  - B `e9462163…`
  - C `523005b5…`
  - D `f393e7b5…`
- Pre-state: root `origin/main` `2d934313e`.
- Post-state: the full hashes are in the script's `TARGETS` and `HOOK_FILES` tables.

## Read before signing: drafted text and judgment calls

1. **B is DRAFTED-FROM-OUTLINE.** The reconcile doc gives D2 and D7 only as an outline. D2 says to
   "ratify the draft amended": widen §3.4's predicate to every reclaimer, name the citation-oracle
   sources, forbid size thresholds, and require a re-check at purge time. The doc also lists the
   draft's gaps (fail-closed reads, a named enforcer). D7 says to align §5 with the 2026-08-03
   ruling. No redline text existed, so the clause was drafted from that outline and from the
   draft's own §3.1 classes, §3.4 conjuncts 3/4/5/7/8 and three-state verifier. It is the **minimal**
   form. It does **not** carry the draft's autonomous-loop expiry grant (§3.2, §3.3 permanent
   classes, the E1/E2/E3 kinds, `namespace_roots`, `retention_hold_boundaries`, the storage floor,
   or §3.7 delegation). It says explicitly that the grant is not enacted. If you want that grant
   too, it is a separate amendment. Strike B if you would rather have the draft owner redline the
   full draft first.
2. **D7 is appended, not edited in place.** The *Evidence must be DURABLE* bullet still says
   "inside a repository". The new clause states that carried-in-git and durable-untracked both
   satisfy it, which keeps the constitution append-only. Your D7 wording was "align §5's text"; if
   you meant an in-place edit of that bullet, this does not do it.
3. **The 7-day hold appears in both B and C.** It comes from the guards design §2.6 ("days now, in
   agent tooling; the boundary hold if item 5 is ratified"). Because the loop-expiry grant is not
   enacted, the draft's operator-boundary hold has no subject yet, so days were used.
4. **C names two tools that do not exist yet**: `scripts/system/citation_oracle.py` (NIB2-105) and
   `scripts/system/reclaim_scratch.py` (NIB2-108). The doctrine words both as "once it lands" or
   "until that tool lands", with a stopgap that uses existing tools. The reconcile doc recommended
   signing after NIB2-105/106 land, but the operator asked for it now.
5. **What the hook blocks** (per guards-design §2.5): recursive `rm`, `find -delete`, a non-empty
   `rmdir`, and `rmtree`/`unlink`/`remove` in `python3 -c`, in heredocs, and inside `python3`/`bash`
   script files. It acts only when a target is under `/mnt/raid0/llm/{tmp,worktrees,.trash,state}`,
   and it blocks **whether or not the path is cited or KEEP-marked**. Citation awareness belongs to
   `guarded_rm.sh` and the oracle (NIB2-105/106). The hook's job is to force every delete through
   those guarded tools.
   - It allows the sanctioned tools, `/tmp/**`, the scratchpad, the `mktemp -d` and `trap` idiom,
     plain non-recursive `rm`, and `EPYC_ALLOW_SCRATCH_DELETE='operator: <who> <date>: <reason>'`.
   - It fails open on targets it cannot resolve and on scripts it cannot read; the hygiene tick
     (NIB2-109) is the backstop.
   - The test-only knob `EPYC_DESTRUCTIVE_SCRATCH_ROOTS` replaces the root list.
   - The hook takes effect in a session only after that session's checkout of
     `.claude/settings.json` syncs to main. `/workspace` was behind `origin/main` when this was
     prepared.
6. The C origin line says the 10-20 reclaim "removed 72 cited paths" under the 0.02 GiB skip. That
   follows the reconcile doc §2: of the 73 cited paths removed, 72 were under 0.02 GiB, and 71 were
   cited on `origin/main` at the time.

## Rollback

Run `git revert <ratify commit>` on a fresh `origin/main` worktree and push it through
`scripts/coordination/serialized_push.py` (`--lock-name push`). This is a human-only write, so the
operator runs it. The revert removes all four sets together: the doctrine, the §5 clause, the hook registration, and the hook
files go with it. The commit sha is printed at apply time and
recorded in `artifacts/operator/ratify_ws58_retention_lessons_20261025.json`.

## Regenerate (if a pin or `--check` fails because a target moved on main)

- Set A: `/mnt/raid0/llm/tmp/ws58-agentfiles-1025-hod/make_diffs.py`.
- Sets B and C: `bash /mnt/raid0/llm/tmp/ws58-ratify-retention-1025-gen/gen.sh <empty dir under /mnt/raid0/llm/tmp>`
  (KEEP-marked). It runs `make_bc.py` (anchor-exact, additions only) on a scratch copy of
  `origin/main` plus A, and it reproduced both committed patches byte for byte. It is not
  committed, because the §5 receipt checker classifies any script that writes those target names
  as a boundary writer. The patches are the durable record; every added line is in them.

## Landed alongside, as an ordinary commit

- `scripts/validate/check_ratification_receipts.py`, with two tests in
  `tests/validate/test_check_ratification_receipts.py`. On main the checker exited 2
  (COULD-NOT-CHECK), and its CI test `test_live_repository_is_clean` failed. The cause is that
  `RATIFY-CTXCKPT-HYBRID-20261024` wrote its operator decision receipt (schema
  `epyc.operator_receipt.v1`, which has no `verdict`) at a `.receipt.json` name. The checker now
  lists such files without judging them; one that carries a `verdict` is still judged. This
  script's preflight requires the checker to exit 0, so the fix was needed here.

Then refresh `PATCH_SHAS` and `TARGETS` in the script and re-run the dry run.
