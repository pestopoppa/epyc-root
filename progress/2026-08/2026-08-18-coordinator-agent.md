# 2026-08-18 — coordinator-agent

Close-out of the recurrence-guard work that began at the 08-16 wrap-up, and the
operator-invoked `/wrap-up` that ends the session arc. Owning handoff:
`handoffs/active/loop-owned-fleet-implementation.md` (RTG-52).

## The two guards, landed under operator D9-ack (`96ccad1a`)

Answering the operator's challenge — *"why would these not be built?"* — by
building them. Both are `fleet_watch` conditions following the compute-idle
contract exactly: three-valued, persistence-gated, one owner and one routed fix
per alarm, emit-once via the channel.

**`REPO-SEQUENCER-STALE`.** Each cycle reads the `.git` sequencer head
(CHERRY_PICK_HEAD / MERGE_HEAD / REVERT_HEAD / rebase-merge) of the shared clone
and both sub-repos; a head older than 2h alarms. A live merge is minutes old; an
abandoned one ages forever, and while it ages every commit in that repo is
refused — the shape that blocked the research repo for three days, twice in four
days, invisible to every existing probe.

**`RETIRED-LANE-UNMERGED`.** Every retired roster identity's lane branch is
checked with `git cherry` — patch-id comparison, merges skipped — so graph
residue counts 0 while stranded CONTENT counts. The probe keeps emitting a
zero-row for a retired id whose branch was deleted, precisely so the alarm key
stays eligible and the clear sweep can resolve it; the first draft dropped the
id with the branch and would have wedged the alarm active forever. My own test
caught that before it shipped.

**Verification.** Suite 137 → 159 passed, 0 failed; the pre-existing 30/30
mutations still caught (mutation 20 repointed after the `fw_owns_key` refactor
moved its target line); 3 new targeted mutations all caught — one initially
SURVIVED because it hid in the probe layer the suite's fixtures replace, the
same blindness that let a `__file__`-relative BUS_ROOT survive a full rewrite,
so the suite now also drives the REAL probes against throwaway git repos
(backdated cherry-pick head; a lane with one stranded patch vs one with none).
Swapped atomically around the running watcher (live-edit hook refused the
in-place edit, correctly); the devcontainer rebuild restarts it onto the new
code.

## The guard paid for itself before it landed

Running `git cherry` for real found **19 stranded patches** on the tombstoned
lanes that every backup sweep had called safe — reachable from origin, never
merged to main. Adjudicated per patch and ported as `10ff9bdf`:

- `progress/2026-08/2026-08-13-mainD.md` did not exist on main **at all**.
- CJ-1c was open on main while the lane had **completed** it on 08-13 — the
  08-16 "re-screen it" note was written unaware. Lane row ported verbatim with
  provenance.
- The ODL-P2 vidya wiring, filed on the lane as "SC37" — a number already taken
  twice — landed as SC42 with the collision recorded inline.
- Deliberately NOT ported: the lane's "ROOT CAUSE" framing (main's audit demoted
  it to "demonstrated prompt/profile mismatch"; reintroducing it would undo a
  correction) and the RTE-Prefix section (main's checkpoint corrects two lane
  claims).

## Quiet on arrival

`lane/mainC` and `lane/mainD` worktrees removed by explicit path (D7 pattern —
never `prune`; the removal initially refused because the worktree metadata names
the repo by its `/mnt/raid0` spelling, resolved by operating from the canonical
path), branches deleted after confirming the tips preserved on origin.
`fw_retired_lane_rows` against the live clone reads zero across all five retired
identities; a `--once` cycle runs clean.

## Also observed

- The D9 commit-time hook false-positived on a compound shell command — it
  pattern-matched loop-plane scripts I was *invoking as tools* against a commit
  whose pathspec touched only handoffs. It fails closed, which is the right
  direction; the refinement (fire on the commit pathspec, not the command
  string) is filed in RTG-52 and is itself D9-gated.
- Two active handoffs whose prose names open work while carrying zero open
  checkboxes (`benchmark-results-dashboard.md`, `frontier-f1-real-task-corpus.md`)
  — checkbox-sync defects belonging to their owning sessions, flagged in the
  wrap-up output rather than repaired blind.

## Commits

| Commit | What |
|---|---|
| `96ccad1a` | the two fleet_watch guards + 159-test suite + mutation repoint (D9-ack: operator, in-channel) |
| `10ff9bdf` | the 19 stranded lane patches, ported per-patch |
| `d45d60f5` | RTG-52 record + tick |

All pushed to `origin/main` through `serialized_push.py` under the push lock.
