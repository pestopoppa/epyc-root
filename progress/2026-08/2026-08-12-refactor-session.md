# 2026-08-12 — coordinator-seat refactor (refactor-session)

Per-agent shard, per the wrap-up contract landed today. The shared
`2026-08-12.md` is 514 KB and was appended by ten wrap-ups; this file is why
that stops.

## What this session was

The operator's coordinator-agent had failed in 38 catalogued ways over ~36
hours — leaving compute idle, unable to reliably reach its mains, reporting
dispatch as utilisation, and colliding with its own fleet in a shared clone.
The operator took the fleet over by hand and asked for an audit and a
refactor. This session ran that: five read-only audits, then an eight-phase
implementation, then the batch push the operator had been holding all day.

## The diagnosis that shaped everything

Not memory decay — **retrieval at the moment of emission**. F-02 was committed
as the coordinator's own correction #2 at 10:07:18Z and recurred at 10:28Z and
~10:40Z: same session, same day, zero decay. So every "write it down better"
fix was already measured as failed (the durable ledger built that morning went
out of contract in 48 minutes). What worked, without exception, were mechanisms
on paths the role cannot avoid.

Three moves followed: **subtract** the accreted measurement duty (47% of the
failures were the role acting as an instrument its mission never gave it),
**enforce at the two choke points** it provably passes through (`append` and
`drain`), and **move the clock out of the LLM thread** into the daemon and the
watchers.

## Phases

| Phase | Outcome |
|---|---|
| 0 — git reconciliation | 139-commit batch push across 3 repos after two-way reconciliation; 84 landed branches pruned; 3 broken worktree registrations repaired (0 prunable from both depths) |
| 1 — role subtraction | AUD-1 receipts-not-dials, D6 files-never-grades, F-30 decision template; stale charter row struck |
| 2 — delivery plane | H-1, H-2, H-3 all closed; 236 tests |
| 3 — worktrees + wrap-up | 9 breakage points fixed; per-agent progress shards; O_EXCL wrap-up lease; concurrent-wrap-up test with a negative control |
| 4 — bus refactor | 310 triage items → 45 MUST-ACT + 265 FYI (85% off the acting queue); typed task-assign |
| 5 — watchdogs | SHA deploy marker replaces the mtime storm (7/7 mutants killed); inference_guard fails closed; linkage verifier non-vacuous; screener unsilenceable |
| 6 — loop | Tick gated on screened_by + expected_occupancy; deeper work wins; depth observable at drain |
| 7 — retro-certification | v9 freeze evidence SURVIVES; 2 certifiable, 5 observation-grade, no measured number shown wrong |

## Corrections to my own account, made in flight

- I called the AUD-15 instruction-surface gate a containment boundary. It is
  not: Layer 2 of that hook fails OPEN by design, because an unparseable gate
  list must not block every edit in the repo. It is a speed bump. Corrected in
  the operator package before it was presented.
- I stated the inbox false-positive rate as 97%. Corpus-wide steady state is
  **83%** (499 action_required rows, 86 sole-target); 97% is a real burst-window
  reading. A later agent measured 96% under a third definition and I filed the
  discrepancy for the auditor rather than picking the flattering number.
- The first untrack commit claimed to untrack four files and did not: a
  pathspec commit BYPASSES THE INDEX and commits working-tree state instead.
  That is `dada0bbc`'s own lesson, committed by me, one commit after reading it.
  Corrected in `f1717d80` with the mechanism named.

## What is measured, not asserted

- **Composer discard**: `space + 1.0s + C-u` CLEARS; `space + Escape` and bare
  `Escape` are no-ops. Measured against a disposable TUI at 21:45:06Z. The
  sequence the adapter already sent turned out to be right — it was inferred,
  and now it is verified. Escape, the tempting guess, does nothing.
- **Truncation**: the loss was never the TUI refusing long text. Above the
  single-burst paste threshold (Codex 1001, Claude ~805) the TUI renders an
  attachment, and Codex caps attachment content at 1024 chars — a 2,998-char
  dispatch arrived as `[Pasted Content 1024 chars]`. 400-char chunks with a
  0.15s gap are lossless to 12,000 chars on both TUIs; the gap is load-bearing.
- **Concurrent wrap-ups**: 3 passes × 3 runs with a negative control, plus a
  live run where mainD was refused 5× and acquired 2.16s later.

## Hazards found and neutralised

The five `.orphan-20260812T1035Z` backup checkouts still carried the
pre-repair RELATIVE gitdir pointer, which resolves to **the same admin
directory the repaired live lanes use**. A stray `git add` inside a backup
would have landed in a working lane's index. Each `.git` renamed to
`.git.disabled-20260812`: content preserved, inert to git, reversible.
`git worktree prune` must never be the tool here — prune is what caused the
original destruction.

## Closing — ratification applied by the operator, and the two delegated calls

**The operator ran `artifacts/operator/ratify_20260812.sh --apply`.** All three safe items
landed and were verified independently rather than on the script's own say-so:

| Item | Verified |
|---|---|
| AUD-15 gate | 2 entries present in `human_only_paths.yaml`; pin matches file; `validate` reports trust-boundary pin intact |
| P-GPU-1 field 3 | clause present in `measurement/protocols/gpu-cross-device.md` |
| `/etc/gitconfig` | `worktree.useRelativePaths` unset system-wide |

That last one closes the worktree-destruction root cause **host-wide**, not just for this
repo — every other clone on the box was still exposed until now.

**Both delegated decisions: relabelled, not re-run.** Neither number is asserted wrong; both
attestations claimed a warrant their evidence never carried.

- `model_registry.yaml` `architect_general` — `contended_tps` and its −35.8% delta rest on
  `gpu_coresidency_20260731`: experimental kernel, no `LD_LIBRARY_PATH`, no commit, n=3, and
  its own title says *"no gate"*. It reaches `repl_memory` `bilinear_scorer`/`q_reward`
  baselines, which is why this one mattered most — a mis-warranted number there propagates
  silently into routing rewards. Now carries `attest_grade: OBSERVATION-GRADE`.
- `worker_vision` cutover — the throughput/VRAM half is relabelled the same way. The
  **accuracy** half is explicitly marked as needing no re-run, with the reasons inline:
  accuracy is device-invariant, `harness.py:242` *prepends* the HIP build dir so the
  stale-path precondition never held, and sampled VRAM scaled monotonically with model size.

**Why relabel rather than re-run**: a re-run costs a GPU window to re-derive numbers that gate
nothing today. The false *warrant* was the urgent part and it is gone. A governed
re-measurement can replace them when the host is quiet — which folds into mainC's request.

**Standing operator directive captured as a guardrail** (`agents/coordinator-agent.md`):
ratifications ACCUMULATE while the operator is away and are surfaced as ONE runnable command
with context on their return, never a trickle — with a carve-out that a genuinely urgent
hazard still goes up immediately. `ratify_20260812.sh` is the working template.

## Open, with named blockers

- Two trust-boundary amendments (AUD-15, P-GPU-1 field 3) — operator-only by
  construction; in `artifacts/operator/RATIFICATION-PACKAGE-20260812.md`.
- `worktree.useRelativePaths=true` in `/etc/gitconfig` — needs root.
- A venv created into `/workspace` itself — needs its owner.
- The tick will dispatch NOTHING until queue rows carry `screened_by` and
  `expected_occupancy` at intake. Fail-closed and intended; the intake
  population is the last piece of work in flight.
