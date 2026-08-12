# Quiesce → merge → push → reboot — operator runbook

**Written 2026-08-12 ~04:10Z. Every fact verified live at that time.** If you re-measure and get
something different, trust your measurement.

## 0. Situation

`epyc-root` `main` diverged from `origin/main` at merge-base `3dd1ec1b`: **267 ahead (unpushed),
93 behind** at 04:07Z. Ahead = five Claude mains' overnight work, committed and never pushed.
Behind = the AutoKernel campaign `inference` pushed through the day. Neither side is wrong; they
never met. A reconciled merge exists on `merge/reconcile-0205` (worktree
`/mnt/raid0/llm/worktrees/merge-reconcile-0205`, tip `c0387984` @ 03:45:34Z, parents `66f40eeb` ×
`ea255b54`), adjudicated safe: 0 genuine content drops, 1068 tests pass, `index_state.py --check`
exits 0, no conflict markers, all new files from both sides present, `merge_gate.py check` =
AUTONOMOUS. It has re-broken four times from ordinary activity — three mains committing (a progress
file, `tool-output-compression.md`, `intake-derived-work-2026-07-25.md` which a two-path freeze
missed) and twice `inference` pushing. It is stale again now: 9 new `origin/main` commits, 3 fresh
conflicts.

> **This merge cannot be landed incrementally while either side is active. Do it once, at full
> quiesce — and a reboot quiesces the fleet by definition, so the merge goes INSIDE the reboot
> sequence, not before it.**

## 1. Preconditions

**1.1 No inference lane or region held.** Run
`/workspace/repos/epyc-orchestrator/scripts/region-lock status`. Expect
`q0 free / q1 free / q2 free / q3 free` — all four were free at 04:07Z. Anything else: find the
holder, do not proceed.

**1.2 `inference` at a boundary, not mid-rollout.** `cat /workspace/coordination/session-bus/boundary_state.json`.
At 04:07Z `inference` = `working|autokernel-source-seam-dashboard-audit` — **not at a boundary.**
Wait for `idle` or `draining`. It has already declared (bus `msg-20260812T020832Z-275-inference`)
that it holds no claim and needs nothing from OP-16 but the reboot; its dashboard supervisor/hub
are disposable across reboot.

**1.3 Working trees clean — telling ignorable dirt from real dirt.** Raw porcelain counts are
useless. Classify:

```bash
for r in /workspace /workspace/repos/epyc-orchestrator /workspace/repos/epyc-inference-research; do
  echo "=== $r"
  git -C "$r" status --porcelain | grep -vc '^??'                  # tracked-modified: MATTERS
  git -C "$r" status --porcelain | grep -c  '^??'                  # untracked: usually evidence
  git -C "$r" status --porcelain | grep -E '^(UU|AA|DU|UD|AU|UA)'  # unmerged: MUST be empty
done
```

Measured 04:07Z:

| Repo | dirty | untracked | tracked-mod | verdict |
|---|---|---|---|---|
| `epyc-root` | 233 | 149 | 84 | untracked = 83 `artifacts/operator/` + 28 `coordination/session-bus/` — evidence, ignorable |
| `epyc-orchestrator` | 1 | 0 | 1 (`scripts/autopilot/failure_blacklist.yaml`) | trivial |
| `epyc-inference-research` | 1173 | 1161 | 12 | untracked = `data/*` bench results; **never `git add` this tree wholesale** |

Rule of thumb: untracked under `data/`, `benchmarks/results/`, `artifacts/*/`, `logs/` is generated
evidence — ignorable. Tracked-modified is real and needs an owner. Unmerged is a stop.

**BLOCKER at 04:07Z:** `epyc-inference-research` is **mid-cherry-pick of `57363905`**, 2 unmerged
paths (`scripts/kernel_rnd/autokernel/FOOTPRINT.md`, `.../controller/__init__.py`) plus 3 staged
adds — `inference`'s in-flight work. It must finish or `--abort` it. Do not resolve it for them.

**1.4 Unpushed counts (fetch first — these move).** In the same loop:
`git -C "$r" fetch --quiet && git -C "$r" rev-list --left-right --count HEAD...@{u}`.
At 04:07Z: root **267 / 93**, orchestrator **1 / 0**, research **10 / 148**.

## 2. Quiesce

Each main writes its **own** wrap-up, per task. The coordinator verifies, never substitutes — a
coordinator reconstructing a main's day from commit messages produces a plausible and wrong log
(operator decision, 2026-08-11).

The fleet was already converging at 04:07Z: `auditor` idle (`merge-sequencing-adjudicated-ready-for-quiesce`),
`mainA` idle (`freeze-lift-and-flush`), `mainB` idle (`merge-state-measured-post-lift`), `mainC`
idle (`reboot-ready`), `mainD` draining (`post-merge-drain`) — only `inference` still working.

Confirm every main is `idle`/`draining` with its wrap-up committed, then instruct each to stop
committing. **From here until §4 completes, nothing commits to any repo.**

## 3. Merge

Is the existing branch still fresh? `0` on the right = fresh, skip to the gates below.
**At 04:07Z it read `258  9` — stale.**

```bash
git -C /mnt/raid0/llm/worktrees/merge-reconcile-0205 fetch --quiet
git -C /mnt/raid0/llm/worktrees/merge-reconcile-0205 rev-list --left-right --count HEAD...origin/main
```

**Re-run from scratch.** Do not repair the old branch; build a fresh one from current tips:

```bash
cd /workspace && git fetch
S=$(date -u +%H%M)
git worktree add -b merge/reconcile-$S /mnt/raid0/llm/worktrees/merge-$S main
cd /mnt/raid0/llm/worktrees/merge-$S
git merge origin/main
git diff --name-only --diff-filter=U      # the conflict set
```

Conflict set measured at 04:07Z — **3 files, all generated**:
`handoffs/active/.index-graph.json` (modify/delete), `handoffs/active/.index-state.json`
(modify/delete), `handoffs/active/master-handoff-index.md` (content). Take either side, then
regenerate:

```bash
python3 scripts/handoffs/index_state.py           # rewrites both sidecars + master rollup
python3 scripts/handoffs/index_state.py --check   # must exit 0, 0 problems
```

**`logs/agent_audit.log`** did not conflict this run but conflicts on most merges — a tracked
append-only log written by every agent. Resolve by **unioning both sides' appended lines and
re-sorting chronologically**; never pick one side. Known structural tax, filed as **C45**; it needs
a real fix (untrack, or a merge driver), not a repeat of this paragraph.

Any non-generated conflict goes to its **owning main** — each resolver touches only its own paths.
Verify (§5), then:

```bash
git commit
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python \
  scripts/coordination/merge_gate.py check --repo epyc-root --range origin/main..HEAD
```

Expect **AUTONOMOUS**. GATED means a human-only path was touched — read the reason before pushing.

## 4. Push

> **MANDATORY PRE-STEP — line 1 below aborts without it.** `/workspace` holds an **untracked**
> `agents/shared/HARNESS_RUN_POLICY.md`, and `origin/main` introduces that path (added by
> `b5054029`, which is in `origin/main` but not in local `main`). Git refuses:
> *"The following untracked working tree files would be overwritten by merge."*
>
> ```bash
> rm /workspace/agents/shared/HARNESS_RUN_POLICY.md    # then run the merge below
> ```
>
> **Provably lossless** — the on-disk file is byte-identical to the incoming blob
> (`git hash-object` = `d1430bd798e8c4fb985d3285e5d93641927cf397` on both sides, 101 lines), so the
> merge restores exactly those bytes. Second backup at
> `/mnt/raid0/llm/tmp/era-repair/HARNESS_RUN_POLICY.stray-backup.md`, sha verified equal.
>
> Three things about this that matter more than the fix:
> - **Rebuilding the branch (§3) does not clear it.** It is not a property of `c0387984`; it is a
>   property of `origin/main` meeting `/workspace`'s working tree. The fresh worktree in §3 is
>   unaffected — a new checkout has no untracked strays — which is exactly why §3 will look clean
>   and §4 will still die.
> - **It is not a conflict and no conflict check can see it.** `merge-tree` says clean add, zero
>   conflicts; `merge-tree` models the *index*, and this abort comes from *worktree safety*. A
>   conflict count of zero is not a statement that the merge will run.
> - **Byte-identical content does not exempt it.** Verified in a throwaway `git clone --shared`
>   against the genuine `origin/main` (`a0c66af2`), not assumed.
>
> Re-derive rather than trusting this list — the predicate is *merge's changed set ∩ everything in
> the working tree, untracked included* (` M` filters miss it, which is how five agents did):
>
> ```bash
> comm -12 <(git -C /workspace diff --name-only $(git -C /workspace merge-base main origin/main) origin/main | LC_ALL=C sort -u) \
>          <(git -C /workspace status --porcelain | sed 's/^...//' | LC_ALL=C sort -u)
> ```

```bash
git -C /workspace merge --ff-only <merge-commit>
git -C /workspace push origin main

git -C /workspace/repos/epyc-orchestrator push origin main          # 1 unpushed, no divergence

# research: 10 unpushed / 148 behind — needs its own merge, and only after §1.3 is cleared
git -C /workspace/repos/epyc-inference-research merge origin/main
git -C /workspace/repos/epyc-inference-research push origin main
```

Re-check `rev-list --left-right --count HEAD...@{u}` per repo; both numbers must read `0`.

## 5. Verification — read this before checking anything

**Three methods were tried on this merge; all three produced false results.**

1. **Counting markdown headings** — passed, by luck. It cannot see content.
2. **Line-set comparison** (`comm` over sorted unique lines) — reported **102,881 lost lines**; the
   real figure was ~1,210. Two defects: preprocessing differed between the two inputs, and `comm`'s
   "not in sorted order" warning was redirected to `/dev/null`, so it silently compared garbage.
3. **Lines-added-relative-to-merge-base** — best of the three, and what the adjudicator used to
   reach the safe verdict. Still not a verdict alone: it is **line-exact**, so any *rewording*
   during conflict resolution reads as loss. It raised a false "two lines dropped" alarm; both were
   dangling `P2.6`/`P2.6.1` anchors into a file with zero `P2` identifiers, which the resolver had
   deliberately adjudicated out and **pre-declared**.

> **Working method: use a metric to flag CANDIDATES, then settle each one by READING THE FILE.**
> Require every resolver to pre-declare in its report which variants it adjudicated out and why —
> that is the cheapest way to distinguish a deliberate drop from an accidental one.

Candidate scan, one file (`LC_ALL=C`, blanks stripped identically on both sides, **stderr not
suppressed**):

```bash
export LC_ALL=C
P=handoffs/active/some-file.md
BASE=3dd1ec1b; PARENT=<ours-or-theirs-sha>; MERGE=<merge-sha>
git diff -U0 "$BASE" "$PARENT" -- "$P" | grep '^+' | grep -v '^+++' | cut -c2- \
  | sed '/^[[:space:]]*$/d' | sort -u > /workspace/tmp/added.txt
git show "$MERGE:$P" | sed '/^[[:space:]]*$/d' | sort -u > /workspace/tmp/merged.txt
comm -23 /workspace/tmp/added.txt /workspace/tmp/merged.txt    # candidates — now go read them
```

Whole-tree version, written and calibrated: `/workspace/tmp/coord-coldstart/scan.py` (edit
`base`/`ours`/`theirs` at the top). Prior adjudication:
`/workspace/tmp/coord-coldstart/merge-adjudication-0245.md` — **untracked, under `/workspace/tmp/`;
copy it out if you want to keep it.** Four gates must all be green before pushing:

```bash
git diff --check                                              # no conflict markers
grep -rn '^<<<<<<<\|^>>>>>>>' . | head                        # empty
python3 scripts/handoffs/index_state.py --check               # 0 problems
python3 -m pytest tests/test_session_bus.py tests/test_tmux_adapter.py \
  tests/test_dashboard_panels.py tests/test_handoff_parser.py tests/vidya   # 1068 passed baseline
```

## 6. Reboot — OP-16

**Reboots are operator-only.** Preconditions: §1–§5 complete, all three repos pushed clean, every
main wrapped. Uptime at 04:07Z was **13 days, 14:26** — past the P-BENCH decision-grade window,
one of the reasons for the reboot.

`inference` is pre-reboot-drained and waiting on exactly this. Afterwards it runs a CPU IQK
campaign: verify kernel identities and host health, prove the captured dashboard PIDs
(`supervisor 1689063`, `hub 1689100` as of 01:56Z) are gone or restart cleanly, acquire protocol
regions, re-run five controls under the fresh campaign, then execute. The serving stack need not be
resident.

## 7. Post-reboot

Coordinator handover: **`coordination/session-bus/tasks/post-reboot-session.md`**, rewritten
2026-08-11 22:30Z, commit `1ae8a952`. Hand it to the incoming coordinator; do not re-derive fleet
state elsewhere. Bringup order:

1. `uptime` — confirm the reboot actually happened before believing anything else.
2. **tmux `agent` session must exist**: `tmux new-session -d -s agent` if absent.
   `tmux.allow_session_creation: false`, so `cmd_spawn` in `tmux_adapter.py` fails closed without
   it (**defect C20**). Nothing spawns until it exists; every main is a *window* in this one
   session (10 windows at 04:07Z).
3. **Start the SUPERVISOR, never the daemon by hand:**
   `nohup /mnt/raid0/llm/epyc-root/scripts/coordination/bus_supervisor.sh >/dev/null 2>&1 &`
4. **Confirm with `ps -p <pid>`, not `status`** — the state file outlives the process that wrote
   it; it once reported a daemon `working` for 243 hours after it died.
5. Re-spawn mains under their **existing roster ids**; a fresh alias orphans that identity's
   cursor, outbox and triage `corr_id`s.

Use `/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python` for every bus write and `validate` — bare
`/usr/bin/python3` has no `jsonschema` and silently refuses rows (C34).
