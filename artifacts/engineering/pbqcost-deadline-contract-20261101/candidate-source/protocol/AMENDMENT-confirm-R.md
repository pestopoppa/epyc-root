# PB-QCOST-1 confirm-R: AMENDMENT to PREDECLARATION.md

Written 2026-10-24T08:10Z by a workspace-f8 subagent, BEFORE any compute of `pb-qcost-1-confirm-r`. Nothing in this file may be
edited after the first launch. The job records its sha256 next to the predeclaration's in RUN_RECORD.json, and verdict_q records
it in VERDICT.json (`amendment_sha256`). Handoff: `gpu-serving-tie-in-program.md`, PB-QCOST-1 confirm-R.

The base rule is unchanged: `PREDECLARATION.md`, sha256 `f45aef1a43976af3d707aea4e7d61875a83e343ec726a61e1725316b385d3e06`,
copied byte-identical into this directory. This amendment changes only what is listed in A1 to A3.

## Why

The parent run `pb-qcost-1-confirm` (2026-10-23 19:12-20:17Z, `/mnt/raid0/llm/tmp/f8-launchers-20261023/pb-qcost-1-confirm/`,
`verdict_q.py` sha256 `31a972d2c25c36b904f82fd48daf70fb0df69983908a0ac9a02299e9978845bb`) got the label
`PB-QCOST-1 confirm CONFIRMED; q axis PASS; grade INDICATIVE`. Two things went wrong:

1. **A harness path defect.** job.sh passes `--out <job>/out/run`, but `sibling_sampler.py` writes `<job>/out/sibling_summary.json`.
   verdict_q looked in `<job>/out/run/`, read null, and could only grade INDICATIVE (fail-closed).
2. **A real disturbance hidden by a run-level bar.** Another session's CPU work ran on cores 92-95 (SMT siblings of host threads
   184-191) from about 19:30 to 20:00Z. The job's own 88-95 sampler saw it: 32 of 60 windows were above 5 % busy, with a peak of
   36.4 %. It overlapped ub 512 (the decision-grade confirm) and ub 256. Section 2's bars are run-wide (median 0.28 %, 1.56 % of
   windows above 25 %), so they pass even with a 20-minute load inside them.

## A1. Path fix (verdict_q.py)

verdict_q reads `sibling_summary.json` and `sibling_load.csv` from the PARENT of `--out` (the directory the sampler writes to).
`--sibling-dir` can override it. A missing file still fails closed to INDICATIVE. Fixed `verdict_q.py` sha256
`7e811a47a95b70519e8f20cae850c64d887c513c3915f15182497b66939d28a3`. Tests in `test_pbq_q.py` (sha256
`219e8413377b28d02aee3c5116b27b844fa8915461f3e3e2f44983b3616e07df`, 12 tests): the 7 original ones plus 5 amendment tests.

## A2. Per-phase contention grade

The thresholds stay exactly as in section 2: median 30-s busy fraction of CPUs 88-95 <= 5 %, and at most 5 % of 30-s windows above
25 %. They are now applied **to each completed ub phase's own window** as well as run-wide.

- Windows are rebuilt from `out/sibling_load.csv`, the sampler's own 5-s samples, grouped in sixes as the sampler groups them. A gap
  over 15 s starts a new sampler run, because the CSV is appended once per grant. A trailing partial group is dropped, as the
  sampler drops it. On the parent's CSV the rebuild reproduces its summary exactly: 128 windows, median 0.0028, max 0.3644, and
  0.0156 of windows above 25 %.
- Phase span: from the phase_id start stamp (written when the phase begins, before server load) to the phase_done row's `t`. Only
  completed phases are graded, and a voided phase is not graded.
- A window counts toward a phase if it **overlaps** the span. A boundary window counts toward both phases, which fails closed.
- A phase is **UNCONTENDED** iff its windows pass both bars. A phase with no windows, or with an unknown span, is INDICATIVE.
- **Run grade = UNCONTENDED** iff the run-wide bar passes (section 2, unchanged, now actually read), every completed phase is
  UNCONTENDED, and every graphs/HSA/VRAM proof is ok. Otherwise the grade is INDICATIVE. This is strictly tighter than section 2:
  no outcome that section 2 grades INDICATIVE becomes UNCONTENDED.
- VERDICT.json carries `grade` (the amended run grade), `grade_run_level` (section 2 alone), and `sibling_per_phase`.

## A3. Re-run all three ub phases

Section 2 grades the whole run, so this is a fresh run of all three phases, 512 then 256 then 1024, in a NEW job directory. It does
not resume from the parent's records. Section 3's reps per length are unchanged.

- Offline estimate 86 min (36.5 + 28.5 + 21.4). The parent measured 65 min (19:12-20:17Z).
- Min window: 100 min (`--min-window 6000`), so one grant covers all three phases. The job refuses to start with less than 95 min
  before its deadline (86 min x 1.1).
- `--skip-done` stays, so a run that is stopped part-way resumes with the remaining phases on the next grant. A2 grades every phase
  in its own window, whichever grant ran it.
- Re-running only ub 512 and ub 256 is NOT what this amendment declares.

## Unchanged

Everything else is unchanged:

- binary, model, argv, prompt set, `-np 5`, n in {1, 4}, TRAIN/HELD-OUT lengths;
- the confirm, q-axis and proof rules (sections 2-6), the label format and the driver `pb_qcost_1_q.py` (sha256
  `89a35f2de62c43e86eb4b58bcce4ad8470219fa99461d99596802a2d89f180cb`, byte-identical copy);
- the sampler `sibling_sampler.py`, the 60 GiB own-pid VRAM guard, the HSA knob and graphs ON;
- placement: mi210_0 GPU flock plus gpu-quiet shared claim, host threads 184-191, siblings 88-95 sampled, production :8083 parked;
- engine `filler_run7.sh --repeat --class gpu --claim-cpus 184-191`, port 18391, RAM 48 GiB, and the booking class.

Only these change:

- the item id `pb-qcost-1-confirm-r`, its STOP file `STOP.f8-pb-qcost-1-confirm-r` and its grant `grants/pb-qcost-1-confirm-r.grant`;
- the min window (A3) and `--complete-cmd test -e <new dir>/PASSED`.

## Reanalysis of the 10-23 data (information only)

The fixed verdict_q was re-run over the parent's existing records, without editing the parent's `VERDICT.json`, and written to
`/mnt/raid0/llm/tmp/f8-launchers-20261023/pb-qcost-1-confirm/VERDICT.reanalyzed-pathfix.json`. That record is information only. It
does not replace this re-run and does not change the parent's label.
