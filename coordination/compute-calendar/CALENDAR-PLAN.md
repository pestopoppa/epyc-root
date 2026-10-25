# Compute calendar plan: 2026-10-25 12:00Z → 2026-10-27 00:00Z

> **Tracked calendar plan.** The calendar owner regenerates this file from
> `handoffs/active/backlog-priority.json` at every task boundary and wrap-up, overwriting it in place; git history is its record
> (`.claude/skills/inference-backlog-scheduling/SKILL.md` §3 step 0). This first instance is the 2026-10-25 ~08:00Z
> proposal, copied verbatim from `/mnt/raid0/llm/tmp/cal-1025/CALENDAR-PLAN.md` (scratch is not a record).

**Status:** PROPOSAL for workspace-58 (calendar owner) to review and arm. Prepared 2026-10-25 ~07:15-08:00Z by a ws58 subagent.
Nothing here is armed. No grant, queue or FILLERS.md edit was made, and no process was started or stopped.

**Inputs read:**
- root `origin/main:handoffs/active/backlog-priority.json`: 178 rows, generated 06:59Z. I regenerated the box-level ranked list from an origin/main snapshot into `work/bp2.md`, with each row's best box mapped to its handoff line in `work/rowctx.txt`.
- `queue_status.py` at 07:01Z.
- `FILLERS.md` (06:58Z), `ws58-gpu.queue`, `ws58-quarters-20261025.queue` (empty by design).
- Writers `grant-gpu-1025-v11.sh` (pid 1265567) and `grant-ws58-quarters-20261025.sh` (prepared, not armed).
- The calendar REVISION log `compute-calendar-20261021.md`.
- `DEADLINES-FROM-WS58.json` and `tasks-from-ws58/*`.

---

## 0. Act first: three calendar-owner fixes found while building this

1. **The GPU writer v11 will never re-offer `hsf-5p-microbench`. This is a bug in `gq_next`.**
   - `gq_next` touches `.wsg-granted-<id>` only *after* `step()` returns, and `step()` returns only after `.ended` appears. So the stamp is always newer than `.ended`.
   - The re-offer test `[ ended_mtime -ge stamp_mtime ] || continue` therefore always skips the item.
   - Measured: `.wsg-granted-hsf-5p-microbench` = 15:44:57.99Z, `grants/hsf-5p-microbench.ended` = 15:44:54.08Z (10-24).
   - Effect: after the yarn slice ends at 08:02Z, v11 grants `akx-all-30a-arbiter`, which has no stamp. It then skips hsf-5p and goes back to yarn slices until its 22:00Z cap. The "hsf-5p re-run after yarn" in the 06:58Z REVISION will not happen.
   - Minimal fix (ws58 owns the state): `touch -d '2026-10-24T15:44:50Z' /mnt/raid0/llm/tmp/compute-flags/.wsg-granted-hsf-5p-microbench`, before 08:02Z if possible. Durable fix in a v12 writer: stamp at grant time, as the quarter writer does (`touch` right after writing `.grant`).
   - The same defect will hide `akx-all-30a-arbiter` and every other queue item from any later re-offer.
2. **v11's liveness checks use `kill -0`.** The checks are in `gq_next` and in `step`, and memory note `feedback_kill0_blind_use_ps_for_liveness` says `kill -0` is blind in this sandbox.
   - In `gq_next`, a failed check is a silent `continue`.
   - In `step`, it returns 2, and `gq_next` then *stamps the item as granted without running it*.
   - It worked for yarn (pid 1198715). It is unproven for arbiter pid 1693294.
   - v12: replace both with `ps -o pid= -p "$lp" >/dev/null`.
3. **v11 stops at 22:00Z 10-25, and no GPU writer covers 10-25 22:00Z → 10-27.** Yesterday's miss repeats unless v12 is armed. The section 2 timeline assumes v12 exists, with the cap at 2026-10-27T00:30Z.

**FILLERS hygiene.** `queue_status` reports 4 STALE-ARMED rows. ws58 applies the fixes:

| Row | Fix |
|-|-|
| `v10-fused-coh` | Set COMPLETE. VERDICT NO-DEFECT, `.ended` rc 0 10-24 09:42Z. |
| `s5-kpf64-ef` | Set BACKLOG, `blocker=harness fix: EB infeasible at quarter scale; F/FB re-arm = kpf64-f-fb`. |
| `v11-086-cpu` | Set BACKLOG, `blocker=harness fix: V11-086-SLOW-1`. |
| `codex-ni-eg2-side-calls-20261024` | Set BACKLOG, `blocker=harness fix: EG2 job 14`. |

`akx-lb3-2-attribution`, `hpr-b-64k-holdout` and `inf66-r2364-thread-sweep` show as ARMED-UNBOOKED, but their fixes have not landed. **Do not grant any of the three until the fix is pinned** (SKILL section 4, "a job whose fix has not landed is not granted").

---

## 1. Compute map

**Coverage.** Every T1, T6 and T7 row is mapped, plus every T2 row whose best item needs compute. Tiers come from `backlog-priority.json`; "best" is that row's best open box.

**Legend:**
- CPU-q: one quarter.
- CPU-h: whole host 0-95.
- quiet: 0-95 plus the GPU idle.
- GPU: mi210_0 plus 184-191.
- Launcher: an existing dir or row, `new` (this plan), or `—`.

### T1 (21 rows: non-inference, unblocked, unblocks compute)

| Row | Best item | Next step needs compute? | Launcher / predecl / blocker | Box says |
|-|-|-|-|-|
| EVL-47 | VB-FOLDGATE-WRITE | no (code) | Codex, assigned, due 10-26 18:00Z | write side of the CH-28 fold gate; gates the C4/C5 fold records |
| INF-26 | fix armP coherence harness | done | armP2 ppl/coh COMPLETE 03:43Z; speed FAIL (decode -8.9%) → P2 does not ship | tick pending (done_pending) |
| INF-65 | CH-LB1.1 fold 5f1eee195+452887155 | yes, after the operator: C6 fold build (CPU-q ~40 min) + gates (GPU corr 45 min, leak 40 min, CPU corr 30 min, quiet gate-e 40 min) | no launcher; **blocked on OP-C4-CAS** (then the C5 CAS); trial-merge prep = Codex brief B2 | re-run (1)-(3) on the trial-merged build |
| UFH-14 | UFH14-LB1.1 fold 0daa3ca8d | same C6 bundle as INF-65 | same | — |
| RTG-57 | KVU-LB1.d F32 VKQ carrier | decision first; then a frontdoor/worker CPU-shape check (CPU-q correctness) | no launcher; owner decision (ws58) | NO_COST on the architect measured |
| INF-62 | DF2-QWOPUS scope + estimate | no (desk) | — | training card-days estimated later |
| INF-64 | re-screen 19 deletion modules | no (AK code; tests run via granted rows) | unassigned; low | — |
| INF-67 | FD-OFF-PROD ratification package | no | v10-fused-coh = NO-DEFECT on the real model; C5 makes fused OFF the code default | package → operator |
| RTG-54 | CT-12.5 fold 6dfbc9e86 | no (already in C2 as 9a44414c4, tests PASS) | tick/verify only | — |
| RTG-58 | KPF-62.2 chunk_kv KPF-62 kinds | yes: tiny-model G1 capture run (build CPU-q ~30 min + run <10 min) | Codex producer 0a9fa2c29 PROPOSED; ws58 review + launcher | acceptance needs a real G1 fixture row |
| INF-81 | AKX-ALL-LB4.9 sinks in iqk merges | yes: build CPU-q + test-backend-ops parity (correctness) | unassigned (f8 consolidated into ws58) → Codex brief B4 | — |
| INF-78 | OAB-29 fake-model wire test | no | unassigned, low | — |
| UFH-01 | HS-OD-4 max_tokens contract | no (operator choice OP-HSOD4 first) | — | — |
| INF-73 | freeze r6 source/reader/runner | AK surface; held by the AK hold | — | — |
| UFH-12 | REPL-EMB-2.10 migration gaps B-1..B-5 | later: re-embed migration (CPU-q/GPU) | Codex holds REPL-EMB-2.13; 2.10 unassigned → brief B13 | — |
| INF-50 | XGRAMMAR-A2 mask cache | yes later: build + grammar speed arm (CPU-q) | unassigned → brief B11 (multi-day) | — |
| INF-75 | AKX-P0d base census W1-W6 | yes: correctness census; runs via AK stage claims → **AK hold** | held | — |
| INF-74 | CTC-Q-D sweep-merge at registration | no (tooling) | brief B12 (D9: scripts/coordination) | — |
| EVL-37 | RTE-LOG-1 prompt-structure logging | no (orch code); feeds S4 Omega A/B (needs stack) | brief B10 | — |
| UFH-08 | HIL-15b harder task set | built; the re-run needs the **shared flag-on stack window** (operator bring-up) | s5-stackup-bundle BACKLOG | — |
| EVL-50 | CME-7T first-call full budget | yes: one-quarter CME-7 re-run with own server after the capture fix | brief B8 | — |

### T6 (2 rows) and the inference boxes that carry compute in T1/T2 rows

The live and ready inference boxes are listed by their T4/T5 box rank.

| Row / box | Compute | Launcher / status | Calendar placement |
|-|-|-|-|
| RTG-16 real_suite_v1 discriminability | eval runs (stack) | none; needs stack / serving | not placed (stack DOWN) |
| RTG-43 post-soak cleanup | no compute | precondition does not hold | — |
| INF-65 CH-30 C4 gates | DONE (all PASS) | — | OP-C4-CAS |
| INF-65 CH-31 C5 gates | DONE (c5-gate-b rc0 18:38Z; G2-CONC PASS under AMENDMENT 9) | — | CAS after C4 |
| INF-70 G2-CONC | DONE on C5 (relative rule) | — | — |
| RTG-58 KPF-64.3 E/EB/F/FB | E DONE; EB infeasible on a quarter; F/FB not started | **new `kpf64-f-fb`** (CPU-q) | q0 10-25 12:00→~20:00 |
| INF-66 R23-64 thread sweep | quiet ~53-80 min, 92 GiB | inf66 launcher alive; **waits INF66-AFF-1** | quiet block 10-26 01:35Z |
| RTG-57 HPR-B (b) 64k holdout | CPU-q ~7.3 h resumable, 54 GiB | launcher alive (373947); **waits HPR-B-SIM-FIX-2** + new predeclaration + token-ID capture | q1 from fix+1 h |
| INF-59 YARN-AGG-1 | GPU ~20-23 h remaining (A0 43 items, A1 95 items incl. 59 at 400-512K) | live (1198715), soak | GPU soak both days |
| INF-60 Q38-T10.1r / Q38-T7a | stack + API reload / organic traffic | blocked: stack DOWN | — |
| INF-65 CH-26b DS41-1017 floor | quiet 3.5 h, 739 GiB, ONE DS41 server | row CANCELLED; new run = AK serial_run → **AK hold**, and it should follow the C4/C5 CAS | operator (digest) |
| RTG-58 KPF-18.0d / R4 follow-up | GPU ~25 min | `kpf18-r4-discrim`: **waits on the Codex code read** (no report at 07:13Z) | GPU 10-26 after report |
| RTG-57 KVU-16g-1 prefill-budget A/B | already ran 10-04 (gpuab-*); scoring + fold remain | no compute | — |
| RTG-58 KPF-62.7 / KPF-60 | speed report vs tuned prefill (timing) | needs KPF-62.3/.4 code (brief B3) | not before 10-27 |
| INF-65 CH-27 Q38FN floors | quiet ~80-99 min, 95-200 GiB | launchers exist; **⛔ AK hold** ("DO NOT LAUNCH AUTOKERNEL") | operator |
| INF-81 AK-Q38FN-64K-FLOOR | folded into CH-27 | AK hold | operator |
| INF-81 AKX-ALL-LB3.2 | CPU-h ~1.5-2 h incl. a G-equivalent build, 110 GiB | launcher alive (1376639); **waits AKX-LB32-OVERHEAD-1** (due 14:00Z) | CPU-h 10-25 20:00Z |
| RTG-57 V11-FA-8 GPU FA overflow | GPU correctness ~30 min | needs an instrumented dump (per-warp row sums inside the MMA kernel) = code → brief B6 | 10-26 after build |
| INF-81 AKX-ALL-13a -t48 -tb96 | keep-grade A/B = AK keep gate | AK hold | operator |
| RTG-57 KVU-12.5 / 12.6 np8 L64k | CPU timing, frontdoor moving to GPU | declined 10-22 (b, c); 12.6 open, low | candidate soak filler (section 5) |
| RTG-57 KVU-19b-fold-c1-p3 | GPU timing ~45-60 min | **new `kvu19b-p3`** | GPU 10-25 ~14:05Z |
| RTG-57 CPU-FA-VKQ-2 | CPU decode A/B of the VKQ fix | subsumed by `v11-086-cpu` (REG vs C) | with v11-086 |
| UFH-12 REPL-EMB-2.12 | v11 full-stack window | blocked: stack | — |
| UFH-14 UFH14-LB3.4 | DONE 05:14Z | — | — |
| INF-65 NEMO-LILI-2 / NEMO-BOLT-PROF | GPU profiling ~20-30 min each (operator: "book a gpu slot but low priority") | **new `nemo-gpu-prof`** | GPU 10-25 ~15:10Z |
| RTG-57 KVU-16f -b/-ub 512 | **REDUNDANT**: 10-04 A/B ran, STACKCHG-8083BATCH signed and applied; :8083 runs `-b 512 -ub 512` (8083.json 10-07) | `cal-1025/kvu16f-b512/REDUNDANT.md` | tick, citing that file |
| INF-65 CH-26a M12 GPU recipe | "the operator runs everything here" (m12 doc) | operator-run | — |
| INF-80 EXL3-6c5 | CPU correctness half (load, smoke, PPL) | **new `exl3-6c5-quality`** (see section 3) | — |
| HSF-5.P | GPU 50 min, 64 GiB | launcher alive (1376631), G4 fix applied 10-24 20:01Z | **next GPU boundary** (after the section 0 fix 1) |
| AKX-ALL-30a arbiter | GPU 24-42 min | armed 06:58Z | 08:02Z (pre-calendar) |
| V11-086 REG vs C | quiet; realistic size unknown (the 10-24 plan's 12 min/launch was really 50+ min) | launcher dead; **waits V11-086-SLOW-1** (due 12:00Z) | quiet block 10-25 22:05Z, sized from the report |
| EG2 job 14, AK startup diag row | CPU-q, minutes | Codex, due 10:00Z | q2 on arrival |

### T7 (37 rows: held or blocked)

| Row(s) | Blocker | Compute it would need |
|-|-|-|
| 20 rows with "operator decision or approval pending" | see section 5 | per the digest |
| INF-03 | operator park 09-27 (GPU MMQ seeds) | GPU window_ab H10a/b |
| RTG-30, REV-02 (and T2 INF-77, INF-72 RT-10, KPF-28) | **DS41-1017 hold** (noise floor only) | DS41 server (739 GiB) runs |
| RTG-09, UFH-13, RTG-40, RTG-17 | parked until the 2nd MI210 plus swapped-stack autopilot | — |
| INF-45 | operator stack bring-up event | stack-up day |
| EVL-11, INF-04, INF-63, RTG-33, INF-52, INF-53 | external (upstream / artifact / disk) | — |
| INF-44 | blocked on PF1 (INF-34) | — |
| RTG-39 | blocked on RustEvo2 Phase B (EVL-45, operator) | — |
| RTG-18 | DO-NOT-DISPATCH checklist | — |

### T2 rows whose best item needs compute

These are mostly un-launchered; none blocks this calendar.

| Row | Item | Compute | State |
|-|-|-|-|
| INF-22 | M4 slot-order batch fill | M4.2 PASS (index); next is the production gate | — |
| INF-70 | ABLATE-1 harness1/ablate.sh | build-role CPU-q/h, leave-one-out, hours | no launcher → **soak filler candidate** |
| INF-60 | Q38-T7b neutral needle | GPU correctness gate | harness code first (brief B5) |
| INF-34 | PF1 CPU-vs-MI210 prefill crossover | GPU + CPU-h timing (quiet for the CPU arm) | no launcher; needs a predeclaration; 10-27+ |
| INF-59 | YARN-JUDGE-1 local judge | worker-model server (CPU-q) + 50 labelled items | code first (brief B9) |
| INF-23 | HSF-4 crossover | analytic from config + logs | no compute |
| EVL-08 | CJ-17 repoint judge | judge runs after a one-line edit | brief B7 |
| EVL-20 | F1 per-split -cmoe timing | GPU + CPU timing | no launcher |
| EVL-29 | ID-8 FrontierCS floor probe (~10 problems) | one production-model server (CPU-q or GPU) | no launcher; candidate filler |
| INF-42 | HRM-1 head-to-head (1B) | download + CPU-q eval | no launcher; low |
| PIP-05 | LightOnOCR-2-1B parser quality | CPU-q/GPU small model | no launcher; low |
| RTG-10 | DCP-10 ContextBench zero-decode scoring | CPU only (discovery, no decode) | no launcher; candidate filler |
| INF-12, EVL-25, RTG-28, RTG-01, RTG-23, INF-05, INF-16, INF-19, INF-28, INF-29, INF-49, INF-51, EVL-05, EVL-14, EVL-35 | heavy evals / GPU training / quiet re-evals / stack-gated | various | gated (stack, data, or operator quiet window); not placed |
| RTG-42, INF-24, EVL-07, RTG-05, REV-06 | stack relaunch / host-quiet windows | stack | blocked: stack DOWN |
| INF-41 | S-19 | only before worker_vision goes HOT again | not now |

---

## 2. Calendar: 10-25 12:00Z → 10-27 00:00Z

**Bins:**
- CPU: q0 0-23, q1 24-47, q2 48-71, q3 72-95.
- GPU: mi210_0 + 184-191 (q3's SMT siblings). Every GPU item here is a **no-fold** GPU-only claim, so it co-runs with whole-CPU correctness work but not with quiet blocks.

**Holds respected:**
- No AK run.py / serial_run (CH-27, CH-26b, AKX-ALL-13a, AKX-P0d held). Profiling (arbiter, nemo) is allowed.
- DS41-1017: no DS41 load in this plan.
- One DS41-class server host-wide: none planned.
- No inference in any dry run.

**Every window** satisfies `end ≥ start + min_window + 300 s`, and every grant is gated by `grant_ok.sh`.

### Timeline

| Window (UTC) | Resource | Item | Est | Class | Status |
|-|-|-|-|-|-|
| 10-25 08:02→~08:45 (pre) | GPU | akx-all-30a-arbiter | 22-42 m | timing-pairable | armable now (armed 06:58Z, in v11 queue) |
| 10-25 ~08:50→09:45 (pre) | GPU | hsf-5p-microbench re-run (G4 log fix) | 30-50 m | timing-pairable | **armable now, needs the section 0 fix 1**, else v11 skips it |
| 10-25 09:45→14:05 | GPU | yarn-extension-arms (2 slices of 7800 s) | 2×2h10 | correctness (soak) | live |
| 10-25 12:00→16:05 | CPU q0 | kpf64-f-fb arm F (atomic) | ~3.4-3.6 h | filler / correctness | **needs launcher** (prepared, section 3) + AMENDMENT-DRAFT adoption |
| 10-25 16:05→20:00 | CPU q0 | kpf64-f-fb arm FB (atomic) + F/FB analysis | ~3.5 h | filler | same grant chain (two windows ≥ 13,700 s) |
| 10-25 12:00→12:10 | CPU q2 | EG2 job 14 / AK startup-diag row (Codex) | <10 m each | correctness | **waits on a fix** (due 10:00Z) |
| 10-25 ~12:30→19:50 | CPU q1 | hpr-b-64k-holdout re-run (6 cells, resumable) | ~7.3 h | correctness | **waits HPR-B-SIM-FIX-2** (due 08:00Z) + new PREDECLARATION + PIN bump; earliest = fix + 1 h |
| 10-25 12:15→13:45 | CPU q2 | exl3-6c5-quality (8 resumable units: E/U smoke + PPL c512 ×40) | ~63 m (window 5400 s) | correctness | **needs launcher** (prepared, DRY rc 0) |
| 10-25 14:05→14:30 | GPU | kvu19b-p3 (K1 N1 K2 N2 + S1; -kvu vs -no-kvu, champion C3 image) | ~18 m (window 1500 s) | timing-pairable | **needs launcher** (prepared). Run it BEFORE any CAS: the job refuses rc 6 if ak/champion moves |
| 10-25 14:30→15:05 | GPU | nemo-gpu-prof (pass L DFlash round; pass B Bolt step) | ~28 m (window 2100 s) | correctness (profiling, not AK) | **needs launcher** (prepared); same CAS caveat |
| 10-25 15:05→17:15 | GPU | yarn slice | 2h10 | soak | live |
| 10-25 17:15→19:25 | GPU | yarn slice | 2h10 | soak | live |
| 10-25 19:25→21:35 | GPU | yarn slice (the last one that fits v11's 22:00Z cap, which needs ≥ 7500 s left) | 2h10 | soak | live |
| 10-25 20:00→21:55 | CPU-h 0-95 | akx-lb3-2-attribution re-run with the same-source G-equivalent arm (+ its build) | ~1.5-1.9 h | correctness (within-process ratios; GPU co-tenant allowed per its predeclaration) | **waits AKX-LB32-OVERHEAD-1** (due 14:00Z) + AMENDMENT; q0 is free at 20:00 after FB; q1 hpr-b must end by 20:00 (resumable; cut is fine) |
| 10-25 21:35→22:00 | GPU | idle 25 m. kpf18-r4-discrim (~25 m, window ≥ 1920 s) does not fit here; place it at the first 10-26 boundary | — | correctness | waits on the Codex report + launcher |
| 10-25 22:00 | — | v11 GPU writer cap. **v12 must be armed** (section 0 fix 3) | — | — | — |
| 10-25 22:05→~01:30 | QUIET 0-95 + GPU | v11-086-cpu REG vs C (re-sized per the SLOW-1 report; placeholder 3h25m) | ? (≥ 1h45 as declared; the 10-24 run showed ≥ 50 min/launch) | **quiet** (decision-grade) | **waits V11-086-SLOW-1** (due 12:00Z) |
| 10-26 01:35→03:00 | QUIET 0-95 + GPU | inf66-r2364-thread-sweep (18 launches, resumable) | 53-80 m (min window 4800 s) | timing (launcher claims quiet) | **waits INF66-AFF-1** (deadline 05:30Z MISSED; no REPORT at 07:14Z) |
| 10-26 03:00→03:50 | GPU | hsf-5p re-run (only if it did not run on 10-25) | 50 m | timing-pairable | — |
| 10-26 03:00→~23:50 | GPU | yarn-extension-arms soak (≈ 9 slices); short items take the next boundary as they arm (kpf18-r4-discrim, V11-FA-8 after its build, KVU-16b-1 re-run after its fix) | ~20 h | soak | live (needs v12) |
| 10-26 03:00→… | CPU q0-q3 | **free**. Unplaced work: C6 fold build + gates (after OP-C4-CAS + the C5 CAS); hpr-b remainder; EB redesign (section 5); Codex test rows; soak-filler candidates (section 4, end) | — | — | waits on the operator / launchers |
| 10-26 (operator-gated) | QUIET 0-95 | CH-27 Q38FN floors (~80-99 m) and/or the DS41-1017 floor (3.5 h, 739 GiB, alone) | — | quiet | **AK hold + post-CAS**. Book only on the operator's word; place in the 10-26 night after GPU HOLD |

### Critical path

```
CRITICAL PATH: GPU yarn soak (A1 400-512K items) → ETA beyond 10-27 00:00Z (~20-23 GPU-h left at 10-25 07:00Z; ~29 GPU-h available in the window minus ~2.5 h of short items)
CPU quiet chain: SLOW-1 (12:00Z) → v11-086-cpu 22:05Z → inf66 01:35Z → done ~03:00Z 10-26; slack 0 on the v11 window if the report sizes it > 3h25m (then inf66 slides to the 10-26 night)
```

### RAM ledger

Bookable ≈ 1069 GiB. No row has two DS41-class items, and none appears at all.

| Block | Concurrent items | Peak GiB |
|-|-|-|
| 10-25 12-16Z | yarn 64 + kpf64 F 42 + hpr-b 54 + exl3 (≤ ~110 if feasible) + codex 4 | ≤ 274 |
| 10-25 14:05-15:05Z GPU swap | kvu19b-p3 (40) / nemo (56) instead of yarn | ≤ 266 |
| 10-25 20-22Z | akx-lb3-2 110 + yarn 64 | 174 |
| 10-25 22Z-10-26 03Z | v11-086 95, then inf66 92 (alone, quiet) | 95 |
| 10-26 day | yarn 64 + CPU fillers TBD | < 300 |

### Compute-hours: planned vs idle in the 36 h window

**CPU** (capacity 4 quarters × 36 h = 144 quarter-hours, qh):

| Planned item | qh |
|-|-|
| kpf64-f-fb | 7.2 |
| hpr-b | 7.3 |
| exl3 | 1.1 |
| akx-lb3-2 | 7.6 |
| v11-086 (placeholder 3.4 h × 4) | 13.7 |
| inf66 | 5.3 |
| Codex test rows | ~0.5 |
| **Total** | **~42** (≈ 29%) |

- Operator-gated work that could add to this: C6 fold build + gates, ~2-3 qh; CH-27, 6.6 qh; DS41 floor, 14 qh.
- **Idle ≈ 102 qh, ~71%.** The cause is not packing. Nearly every remaining CPU inference item is held by an operator ruling (AK hold, DS41-1017 hold, stack DOWN) or blocked on code.
- Reducing it needs either the holds lifted (section 5) or new soak fillers (section 4 end: ABLATE-1, KPF-64 EB-on-half-host, KVU-12.6, DCP-10).

**GPU** (capacity 36 h):

| Category | GPU-h |
|-|-|
| yarn soak | ~28.5 |
| Short items | ~1.5-2.5 (kvu19b 0.3, nemo 0.5, kpf18-r4 0.4, hsf 0.8 if slipped, V11-FA-8 / KVU-16b if their code lands) |
| **Planned total** | **~30.5** |
| Idle by design: quiet blocks (GPU held for v11-086 + inf66) | ~4.9 |
| Idle: gap 21:35-22:00 (before the v11 cap) | ~0.4 |

---

## 3. Launchers prepared (under `/mnt/raid0/llm/tmp/cal-1025/<id>/`, each with KEEP)

**Results:**
- 4 launchers are prepared. All four DRY_RUN with rc 0, all four `validate_fillers.py --row` are OK with 0 refusals, and all four PREDECLARATION.sha256 files match their PREDECLARATION.md (I re-checked).
- 2 items were not built: one REDUNDANT, one waiting on Codex.
- All four rows are FILLERS_ROW.md drafts (status BACKLOG, `blocker=missing launcher`), not inserted.

| id | Row / box | Engine shape | Est | Min window | RAM GiB | Class (derived) | DRY | Arm command | Belief capture | Notes / risks |
|-|-|-|-|-|-|-|-|-|-|-|
| `kpf64-f-fb` | RTG-58 KPF-64.3 F + FB | filler_run9 `--class cpu --role build`, one quarter, port 18967, frontdoor 35B-A3B-MTP Q8_0 `-np 4 -c 262144 --no-mmap --reasoning off` | F ~3.2 h + FB ~3.2-3.6 h (2 atomic arms) | 14000 s per arm (window 14400) | 42 | filler (token counts only) | rc 0 | `cd /mnt/raid0/llm/tmp/cal-1025/kpf64-f-fb && setsid nohup bash launch.sh > launch.log 2>&1 &` | native `chunk_kv.py` (prefix_hit_share) via `analysis.py --belief-out` → `cli.py ingest chunk-kv` | **Refuses rc 14 until ws58 adopts AMENDMENT-DRAFT.md** (order F, FB now, EB deferred, rule unchanged): write `AMENDMENT-ADOPTED` containing that file's sha256. PREDECLARATION sha `62b63257…`, quoting PREDECLARED.md `44c11760…` unchanged. Writes F_FB_DONE, never EF_ALL_DONE / pass1-E / pass1-EB. Adds the frontdoor OMP env + node-local interleave (old: `--interleave=all`), stated in the amendment. |
| `exl3-6c5-quality` | INF-80 EXL3-6c5 (correctness half) | filler_run9 `--class cpu --role build`, one quarter; EXL3 tree `experimental/exl3-cpu-20261003` @ 20192b81d build/bin (no build needed) | ~63 m (8 resumable units) | 4500 s (window 5400) | 92 (U `--no-mmap` 87.3 + state) | block-correctness | rc 0 | `cd /mnt/raid0/llm/tmp/cal-1025/exl3-6c5-quality && setsid nohup bash launch.sh > launch.log 2>&1 &` | native `exl3.py` (`cli.py ingest exl3-measurement`); the job stages the logs and RUN_RECORD, the owner emits the `epyc.exl3.measurement.v1` rows | Rule (sha `216b4110…`): QUALITY_NOT_WORSE if PPL E/U−1 ≤ +1.0%; smoke prefix match ≥ 100/40/40 chars. Re-measure of the 10-04 PPL (E 2.8909 vs U 2.9925). Models pinned by size only. Smoke prompts p2 and p3 are new. The speed half is left for a quiet window. |
| `kvu19b-p3` | RTG-57 KVU-19b-fold-c1-p3 | filler_run9 `--class gpu --gpu-quiet exclusive --claim-cpus 184-191 --no-fold-siblings --role build --sched-port 8083`; champion image resolved from `ak/champion/llama-cpp-ffc1bac82eec` (today C3 dcc853b55) | ~18 m | 720 s (window 1500) | 40 (VRAM ~35 est, guard 60) | block-timing-pairable | rc 0 | `cd /mnt/raid0/llm/tmp/cal-1025/kvu19b-p3 && setsid nohup bash launch.sh > launch.log 2>&1 &` | `[belief: cc]`: `kvu_batched_decode_vs_nokvu_delta_pct`, pct, n=2 ABAB | Arms K1 N1 K2 N2 (+ S1 SEQ_ROWS=0 diagnostic), batched-bench npl 4 / npp 16384 / ntg 64, graphs ON, fresh process per arm. WITHIN_5PCT / OUTSIDE_5PCT / UNRESOLVED (pairs straddle the edge or spread > 3%). Sha `6b72d2e3…`. **rc 6 if CAS moves the champion before it runs.** Declares no `--port` (the reaper has no cmdline filter). |
| `nemo-gpu-prof` | INF-65 NEMO-LILI-2 + NEMO-BOLT-PROF | as above, port 18431; side-loaded rocprofv3 (AK pin c753449e), graphs ON | ~28 m (2 resumable passes) | 1200 s (window 2100) | 56 (L) / 36 (B) | block-correctness (attribution, no decision edge) | rc 0 | `cd /mnt/raid0/llm/tmp/cal-1025/nemo-gpu-prof && setsid nohup bash launch.sh > launch.log 2>&1 &` | `[belief: cc]`: `dflash_round_busy_ms`, `plain_token_busy_ms`, `bolt_decode_step_busy_ms` | Pass L 27B+DFlash2 at `-np 1 -c 16384` (deliberate deviation from :8083). Pass B Bolt 74B-A9B (`.../NVIDIA-Nemotron-3.5-Bolt-74B-A9B-24GB.gguf`). The analyzer has only seen synthetic traces, so the first run may come back INCOMPLETE. Sha `914fd9b1…`. Profiling only: never calls run.py or serial_run. Same CAS caveat. |
| `kvu16f-b512` | RTG-57 KVU-16f | — | — | — | — | — | — | — | — | **REDUNDANT** (`REDUNDANT.md`): A/B ran 10-04 (`artifacts/gpu-slot-ak-20261004/`), STACKCHG-8083BATCH signed and applied, and :8083 has run `-b 512 -ub 512` since 10-07. Tick KVU-16f citing that file. |
| `kpf18-r4-discrim` | RTG-58 KPF-18 R4 follow-up | — | ~25 m (future) | — | ~48 | correctness | — | — | likely `kv_prefix_fork.py` | **NOT-FEASIBLE yet** (`NOT-FEASIBLE.md`): KPF18-R4-FORK-CODEREAD-1-REPORT.md was absent at 07:14Z (due 08:00Z). A draft arm skeleton (coldL layout-matched, coldM padded) is in the file. The layout-matched arm may need new gate code. |

**Evidence (all four):** on completion each job stages VERDICT / RUN_RECORD / PREDECLARATION + SHA256SUMS + README into `<dir>/evidence-staged/data/<campaign>/`. The owner commits that to research `data/<campaign>/` (MEASUREMENT.md §5). The jobs perform no git operation.

---

## 4. Code-dispatch list

These are Codex briefs for T1/T2 non-inference items that unblock compute and are **not already assigned**. I checked `tasks-from-ws58/`, `ROWS-FOR-OWNER.md`, `OWNER-REPLY.json`, the two `OWNER-COORD-NONINFERENCE*` waves and `LOOP-SAFETY-C-BUNDLE.md`.

**Already assigned, excluded:**
- INF66-AFF-1, V11-086-SLOW-1, AKX-LB32-OVERHEAD-1, HPR-B-SIM-FIX-2, KPF18-R4-FORK-CODEREAD-1.
- VB-FOLDGATE-WRITE, LOOP-SAFETY C1-C7, AKX-ALL-31 numerics gates.
- EG2 job 14, AK startup-diag row, NIB2-102c/103, NIB2-98 (in discussion).
- The KPF62 G1 producer (0a9fa2c29 PROPOSED, awaiting ws58 review), REPL-EMB-2.13, S20, OAB.

Every brief carries the RULES-FROM-WS58.md boundaries: PROPOSED on `codex/*` from current origin/main with explicit refspecs, own worktrees only, never champion/production/store paths, tests only via granted rows, REPORT in `tasks-from-ws58/<ID>-REPORT.md`.

| # | ID (row, rank) | Brief | Deadline → window it unblocks |
|-|-|-|-|
| B1 | **C6-FOLD-PREP** (INF-65 #3 CH-LB1.1 + UFH-14 #4 UFH14-LB1.1) | Trial-merge `5f1eee195` + `452887155` + `0daa3ca8d` onto the C5 tip `c72ec82f5` on a new `experimental/champion-c6-<date>` fork branch (no build). Resolve conflicts with C3's `src/llama-kv-cache.cpp` K-shift change. Write FOLD.md (commit list, patch-ids, touched libs, the expected `fold_gate.py --expected-changed` set) and the gate plan (unit tests from each source branch, CPU/GPU correctness, leak check, gate-e), cloned from `/mnt/raid0/llm/tmp/c5-fold-prep/PLAN.md`. Report the ancestor checks (`merge-base --is-ancestor`) and any dropped hunk. | **10-26 06:00Z** → the first CPU build quarter after OP-C4-CAS + the C5 CAS (10-26 day); the C6 gates then fill ~3 GPU/CPU-h on 10-26 |
| B2 | **KPF62-SEL-RECOMP** (RTG-58 #10, KPF-62.3 + 62.4) | Implement the selector (head window W=64 + check-layer K deviation + group-contiguous runs) and sparse recompute by explicit-position batches beside the cache-reuse block, on the chunk-KV experimental branch (`786a30078…` lineage). Unit tests must include G0 bit-identical at r=100% (`tests/test-chunk-kv.cpp`). Phase-0 frozen thresholds in P0_THRESHOLDS are inputs and must not change. | 10-26 18:00Z → KPF-62.5 wiring, then the KPF-62.6 G3 harness and the KPF-62.7 speed report (a timing window, 10-27+) |
| B3 | **AKX-LB4-SINKS** (INF-81 #11, AKX-ALL-LB4.9 + LB4) | On an experimental branch from the champion tip: fold the GQA sink block into the #1212 and #277 nek2==1 iqk merges, pass `sinks->data` from the ops.cpp hook, and lift the sinks decline only after FLASH_ATTN_EXT matches the ggml reference on the listed cases. The cases: DS41 SWA layers 0-1, stock-mask DS41, the gathered n_kv 640/768 64h/1kv shape, per-head-distinct sinks at nth 1/16/32/64/96. Tests only (test-backend-ops), run via a granted build row. | 10-26 12:00Z → build quarter + parity row 10-26 afternoon; unblocks the LB3.x iqk-ON premeasure |
| B4 | **UFH14-LB6-RECORDING** (UFH-14 #4, UFH14-LB6) | Root-cause why `serving_calls` per-call recording produced only 19 records since 10-05 despite a live hook. Reproduce with the fake server (OAB-29 stub pattern) and fix in orchestrator, with a test asserting one record per call. No API reload by Codex; adoption is at ws58's API-only reload. | 10-26 12:00Z → every serving-window measurement (s5-stackup-bundle, S4-T1 proof, WP-15.3) records correctly when the stack comes up |
| B5 | **Q38-T7B-NEEDLE** (INF-60 #24) | Change the Q38 needle cells to a neutral haystack (RULER noise or essays) and ask the needle in both arms. Pin the filler corpus by sha. Unit-test the prompt builder (no model). Add the PREDECLARATION delta for the next production-shape correctness gate. | 10-26 12:00Z → one GPU correctness slot 10-26 (27B :8083 shape, ~40 m) |
| B6 | **V11-FA-8-DUMP** (RTG-57 #5, V11-FA-8) | Add an opt-in debug dump (compile flag on an experimental branch from the champion) that records per-channel max abs(V) and per-row unnormalised row sums over one warp's KV share in the MMA FA kernel for the 27B FA layers. Add a host-side reader plus the PREDECLARATION (8k repetitive prompt + 57k context; arms A and candidate C of the V11-FA-1 harness `/mnt/raid0/llm/tmp/v11-fa-ab-20261004/`). Code and tests only; the build runs in a granted build row. | 10-26 12:00Z → GPU build (q3 must be free, so schedule it in a non-GPU window) + a 30 m GPU correctness slot 10-26 |
| B7 | **CJ-17-REPOINT** (EVL-08 #42) | The one edit at `src/llm.py:61-64` (`model_url` + `model_name`) repointing the judge and the LIGHT scratchpad path to the canonical local judge. Add a test asserting the resolved judge identity. PROPOSED only. | 10-26 18:00Z → CJ judge runs (CPU-q with own server) |
| B8 | **CME-7T-CAPTURE** (EVL-50 #21) | In `system.py`, log the rejected `text` and `finish_reason` of a schema-failed call, and stop carrying a failed 2048-token reply into the parse-retry prompt (or cap it). Write a unit test with a fake reply. Then a root-cause note on why call 0 hits `max_output_tokens` with `enable_thinking=false`. | 10-26 12:00Z → a one-quarter CME-7 smoke re-run (own server, ~10 m) 10-26 |
| B9 | **YARN-JUDGE-1** (INF-59 #30) | Local judge client path to `localhost:{port}/v1` on the worker model for the judged HELMET / HoloBench cells. Pin the judge model and prompt in the claim tuple, and add a 50-item validation harness (labels stay human). No server start. | 10-26 18:00Z → judged cells for the yarn arms before A1 finishes (~10-27); a judge run on CPU-q outside the yarn GPU window |
| B10 | **RTE-LOG-1** (EVL-37 #19) | Add the ordered `blocks[]` (kind, offset, length, sha256 prefix), the chunk hash/rank, `prompt_tokens`/`cached_prompt_tokens`, `turn_index` and `source` to the dispatch and serving records, plus the B7 offline reader (hashes and lengths only). | 10-26 18:00Z → S4 Omega A/B offline analysis when the stack is up |
| B11 | **XGRAMMAR-A2** (INF-50 #16) | Port XGrammar's context-independent token-mask cache into `llama-grammar.cpp` on an experimental branch. Acceptance tests: byte-identical constrained output on the SPEC-GRAM corpus (model-free grammar tests first). Multi-day. | 10-27 18:00Z → build quarter + grammar speed arm (CPU-q) 10-28 |
| B12 | **CTC-Q-D-SWEEPMERGE** (INF-74 #18) | In `validate_fillers.py`, add a registration-time pass that lists rows sharing (model, build, argv-hash) or a DS41-class server, plus a `--sweep-merge` report. Tests. PROPOSED; landing needs a D9 ack (scripts/coordination). | 10-26 18:00Z → fewer duplicate loads in the 10-26/27 calendar |
| B13 | **REPL-EMB-2.10-GAPS** (UFH-12 #15) | Close B-1..B-5 in `scripts/migration/reembed_stores_eg2.py`: sessions archive-only mode, strategy store unit, identity key, consumer marker check, side-aware embedding. Write the BGE retrain list as a file. Tests only. Coordinate with Codex's own REPL-EMB-2.13 claim (no overlap). | 10-26 18:00Z → the EG2 re-embed migration run (CPU-q) |
| B14 | **KVU-16B-1-PREDICATE** (RTG-57, KVU-16b-1) | Fix the residency runner's decoding predicate, with a test on a recorded log. Then prepare the re-run row (GPU, corrected 393216-pool residency proof). | 10-26 12:00Z → a GPU slot 10-26 (~40 m) |

**Declined in writing (rule 27(d), the follow-up only unblocks held tests):**
- INF-72 RT-10 DS41 tap hook, INF-77 DS41-W8b, DS41-CED.1 / KPF-28: held by the operator ruling DS41-1017 (2026-10-22).
- AKX-AUTO-6 exercise, CH-27 re-anchor, AKX-P0d census, AKX-ALL-13a: held by the operator AK launch hold (2026-10-24).
- INF-64 deletion re-screen: AK code. It may proceed (no launch), but it unblocks no compute in the window.

**Soak-filler candidates** (they reduce the ~70% CPU idle; each needs a launcher, not code):
- INF-70 ABLATE-1: harness exists; build role, leave-one-out over TUs, hours on 1-2 quarters.
- KPF-64.3 EB redesign on q2+q3: 48 cores, atomic ~9-13 h; owner decision in section 5.
- KVU-12.6: np8 L48k plus np4 equal-token cells, CPU timing-pairable, ~2-3 h.
- RTG-10 DCP-10: ContextBench zero-decode discovery scoring, CPU only, no model decode.

---

## 5. Operator-decision digest

Each line gives the decision needed and the compute it unblocks. Compute cost comes first where known.

**Champion and folds**

| Item | Decision needed | Compute it unblocks |
|-|-|-|
| **OP-C4-CAS** (CH-30, C4 `cdb4d8c77`, GPU-LEAK-1c fold) | All gates PASS: c4-gpu-correctness, c4-leak-check, c4-gate-e quiet re-run rc 0 21:06Z. Approve the guarded CAS of `ak/champion` from `dcc853b55` to `cdb4d8c77`. The C5 CAS (`c72ec82f5`, all C5 gates complete, G2-CONC PASS under AMENDMENT 9) follows. | The C6 fold of CH-LB1.1 + UFH14-LB1.1 (B1): ~40 m build quarter, then ~3 h of CPU/GPU gates. The CH-30b leak-workaround removal. Champion-anchored re-measures (CH-26b DS41 floor 3.5 h quiet, CH-27 Q38FN floors ~1.5 h quiet; both also need the AK hold lifted). |

**Rows with "operator decision or approval pending"** (20 rows)

| Row | Decision needed | Compute it unblocks |
|-|-|-|
| RTG-46 BACKLOG-PRIORITY | `backlog-priority.json` is on main. Confirm it landed, then tick or close; the skill idea remains. | none |
| EVL-01 AFC-P5.E3 | Release the n=30 compliance campaign ("I will tell"). | n=30 agent-file compliance runs (serving needed) |
| EVL-49 S-04 | Approve an E5 Stage-B execution window. | E5 NUMA×batch sweep (whole-host quiet, multi-hour) |
| INF-37 INF37-MOE-Q8-FUSION | Approve experimental qualification, build and run. | build quarter + GPU correctness/timing on the 35B Q8 MTP |
| RTG-35 REGION-SIBLING-1 (= OP-77) | Merge `fix/region-lock-smt-siblings-ec` @ `4ae008a8`. | none directly; sibling-pinned jobs stop blocking behind 0-95 (packing) |
| RTG-36 SCG-PRIORS-WARM (= OP-72) | Sign STACKCHG-HYGIENE-20261003. | none (no relaunch) |
| UFH-11 WEB-1 | Choose the publication contact destination. | none |
| EVL-15 | Fix the llama-server log retention hole: approve the retention change. | none (evidence durability) |
| EVL-21 G1 | Ratify P-GPU-1 (measurement trust boundary). | GPU-protocol claims |
| EVL-26 W2 | Approve the restic backup job. | none (I/O) |
| EVL-31 | Approve the Mathsmith HF→GGUF convert + bench. | convert (CPU-q) + formalizer bench |
| EVL-32 | Video generation: product need, or close? | none |
| EVL-43 | Approve the sliders clone / GPT-4.1 call-site catalogue. | none |
| EVL-45 | Approve RustEvo2 Phase B. | sequential single-instance bench of 3 models (hours); unblocks RTG-39 |
| INF-46 P6b | v8-era fresh-experimental load + gate bench: close as superseded, or re-scope to v10/champion. | — |
| REV-09 RA-13a | Approve the blind read-back pilot. | reviewer-model runs (stack) |
| RTG-24 P0.1 | Run or pause the autopilot candidate species. | AutoPilot loop (stack) |
| RTG-29 | GAT + SkillBank retrains, only if DAR-1 regret ≥ 5%. | GPU training |
| RTG-32 T0.1 | Approve the capability-registry row (AutoPilot is stopped). | none |
| RTG-55 MHS-3d | Ratify the v10 episodic re-pin (one command). | none |

**Standing holds** (not T7 decision rows, but they idle most of the CPU)

| Hold | Decision needed | Compute it unblocks |
|-|-|-|
| AK launch hold (10-24) | Lift it, for floors only or entirely. | CH-27 floors ~80-99 m quiet (launchers exist; re-anchor to C3/C4/C5 first); DS41 floor 3.5 h quiet; AKX-ALL-13a; AKX-P0d census; AK-Q38FN-64K-FLOOR |
| DS41-1017 hold (10-22) | Keep it, or lift it after the floor. | KPF-28, RT-10, DS41-W8b, REV-02, RTG-30 |
| Stack bring-up event | Name the stack-up window. | s5-stackup-bundle (HIL-15b re-run, HIL-16a/18a), Q38-T10.1r, Q38-T7a, REPL-EMB-2.12, S4-T1 live proof, WP-15.3 capture |

**Owner decision for ws58, not the operator: the KPF-64.3 EB redesign**

- **Context:** EB (`cache-ram 0`, atomic) did 90 of ~388 requests in 6h13m on one quarter. That projects to ~26 h, which is infeasible.
- **Options:**
  - (a) EB on q2+q3 (48 cores): ~9-13 h atomic, soaking idle CPU on 10-26. It blocks q3-folded GPU work only if folded; all planned GPU items are no-fold.
  - (b) EB on the whole host: ~6-8 h, but it competes with the quiet blocks.
  - (c) Fewer sessions: needs an amendment and breaks E-vs-EB pairing on the same 19 sessions.
  - (d) Drop EB and decide on E vs A-D only.
- **Recommendation:** (a). It uses compute that is otherwise idle, and the rule is unchanged.
- **Default if unanswered:** (d) after F/FB.

---

## 6. Queue lines to add (after arming; pids from the live launchers)

**Writer formats:**
- `ws58-gpu.queue`: `id|pid|win|min|gib|regex|regions`.
- Quarter writer: `id|pid|window_s|gib|regions`.

Replace `PID` with the live launcher pid after arming. Run `grant_ok.sh <id> <gib> --window-s <win> --regions <r>` before adding each line.

**ws58-gpu.queue** (order = priority; v11 offers queue items before yarn):
```
hsf-5p-microbench|1376631|4200|3000|64|^ *gpu-quiet|mi210_0,184-191      # already present: needs only the stamp fix (section 0, fix 1)
kvu19b-p3|PID|1500|720|40|^ *gpu-quiet|mi210_0,184-191
nemo-gpu-prof|PID|2100|1200|56|^ *gpu-quiet|mi210_0,184-191
# later, after the Codex report + launcher: kpf18-r4-discrim|PID|1920|1500|48|^ *gpu-quiet|mi210_0,184-191
```

**ws58-quarters-20261025.queue** (the writer is prepared but not armed, cap 21:30Z):
```
kpf64-f-fb|PID|14400|42|0-23
exl3-6c5-quality|PID|5400|92|48-71
# after HPR-B-SIM-FIX-2 + new PREDECLARATION + PIN bump (same launcher id, re-armed):
# hpr-b-64k-holdout|<new pid>|7200|54|24-47
# Codex EG2 job 14 / AK startup-diag rows on arrival: <id>|<pid>|600|4|48-71
```
- The `kpf64-f-fb` 14400 s window takes ONE arm. The writer re-offers it after a clean end, which gives FB its window. The second arm ends ~20:05Z, and the cap is 21:30Z.

**Whole-host and quiet items.** These are not quarter-queue lines; they get dedicated one-shot writers, as on 10-24.
- `akx-lb3-2-attribution` 0-95 (≥ 2700 s; plus the G-equivalent build after the AKX-LB32 fix, so book 7200 s). Window 20:00→22:00Z, after FB ends and with hpr-b cut. It co-runs with the no-fold yarn slice.
- `v11-086-cpu` 0-95 + gpu-quiet `--reserve gpu-quiet`, sized from V11-086-SLOW-1. HOLD_GPU_FOR_QUIET from 22:00Z.
- `inf66-r2364-thread-sweep` 0-95 + gpu-quiet, 4800 s min, window 5100 s+, after v11-086 ends. A QUIET_BLOCK_ENDED flag releases the v12 GPU writer.

**v12 GPU writer** (needed; v11 ends 22:00Z):
- Cap 2026-10-27T00:30Z.
- ps-based liveness.
- Stamp at grant time.
- Waits on HOLD_GPU_FOR_QUIET_20261025.
- Then: queue items, then yarn slices.
