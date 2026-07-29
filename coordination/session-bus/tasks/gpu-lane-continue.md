# Task: commit your P2-1/P2-3 work, then reconcile with P2-6

**For** `claude-gpu-lane`. Continuation of
[`gpu-lane-p2-1-p2-3.md`](gpu-lane-p2-1-p2-3.md) — same work, so keep your context. All prior
constraints still bind.

## Operator decisions relayed

1. **Keep building.** Your q3 finding is accepted and does not stop P2-1/P2-3: the work is
   zero-inference, and the lane will not activate this session regardless. The MI210 stays idle
   until the Phase-3 bake-off.
2. **Your q3 finding is now a first-class program constraint**, not a footnote. Make sure P2-1
   encodes it where the next reader cannot miss it: *an idle MI210 does not imply a startable
   lane*, because host threads pin to SMT siblings 184-191 → physical cores 88-95 → atomic region
   **q3**, currently `HELD` by `bench-e8-quality` (`e8-v5-r2-cadencefix-20260728T160917Z`).
   Activation requires a q3 claim that would force codex to drain deadline-bearing E8 work.
   Confirmed by `region-lock status`, so state it as measured, not inferred.

## 1. Commit your work — carefully

The orchestrator tree has 8 modified files and **P2-6 is mid-flight in the same ones**. You
already noticed this and correctly did not touch their in-flight file.

- **Commit ONLY the paths you authored.** Verify each one is yours before staging — `git diff`
  it and confirm you recognise the change. If a file contains both your work and P2-6's, **stop
  and report**; do not attempt to split it, and do not commit it.
- **Explicit paths only.** Never `git add -A` or `git add .`. **Stage and commit in ONE step** —
  a parallel session swept a staged set into an unrelated commit earlier today.
- Do not push. Report the SHA to `coordinator-agent`.

## 2. Reconcile against P2-6's launch-layer coupling

You flagged that P2-6 adds real launch-layer coupling, so **the P0-7 zero-coupling witness no
longer means what your original brief assumed** — that brief was written against a premise that
has since changed. You were right to flag rather than revert.

- Work out what the witness now attests, and what it no longer attests.
- If your P2-1/P2-3 work rests anywhere on the old zero-coupling assumption, identify it
  explicitly rather than quietly rewriting around it.
- **Do not edit P2-6's in-flight files to make them agree with you.** Coordinate through
  `coordinator-agent`: report what conflicts and what you propose. At 16:31Z their change to
  `evaluate_preflight` (now returning 3 values) transiently reddened 17 of their own preflight
  tests — they are actively mid-edit, so treat those files as hot.

## 3. Carry your three defect findings into the record

You found and fixed real defects; make sure they survive as durable findings, not just as diffs:

- **P1-4 confirmed** — the measured grid is the FF arm (27.74 GiB) filed under a tenant carrying
  stock's 26.70 GiB; now split, with stock an explicit `derived_conservative_transfer` row and no
  throughput table.
- **NEW-1** — FF-MTP is a **different GGUF** (30,239,022,560 B; 851 base + 15 MTP tensors), not
  the non-MTP file with a flag. As a mode override it would have carried the wrong model size
  into every VRAM budget. Now its own tenant. This one is worth a line in the owning handoff:
  it is a silent-wrong-answer class defect, not a hygiene fix.
- The A4 bridging item you reported (truncated in transit) — restate it in full.

## Definition of done

- Your work committed, P2-6's untouched.
- P2-1 encodes the q3 coupling as measured fact.
- A clear statement of what the P0-7 witness attests post-P2-6, and any of your work that rested
  on the old premise.
- Owning-handoff `- [ ]` boxes for P2-1/P2-3 flipped to `- [x] … ✅ 2026-07-28` **by you**, with
  evidence refs. Coordinator-agent does not tick checkboxes. Anything discovered mid-flight gets
  its own new task line rather than being folded silently into an existing one.
- Report to `coordinator-agent` via your outbox.

## Constraints (unchanged)

Registry FROZEN — proposal diffs only, apply nothing. No activation, no preflight against live
hardware, no server launch. **Never take the cpu lane**, and take **no region claim** — q3 is
held by deadline-bearing E8. No stack or API reload. Drain and refresh your heartbeat at every
task boundary; retire `task_id` at terminal state.
