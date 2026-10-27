# HSF-5.P host KV mirror: findings to date and revival checklist (2026-10-27)

Owner session: workspace-58. Handoff: `handoffs/active/heterogeneous-slot-fabric-residency.md` (HSF-5.P-NEXT). Purpose: keep everything learned so far so the GPU+CPU hybrid-kernel line for large models can be revived later. Operator: "We cannot afford to lose knowledge about progress completed until now on this."

Status decision (2026-10-27): Codex builds a repair on the current champion now (model-free validation only). GPU attribution/benchmark testing is DEFERRED until a later operator go. HSF-5.P-NEXT is NOT closed.

All numbers below are copied from the cited sources. Raw evidence lives under `/mnt/raid0/llm/tmp/` (scratch; the committed copy of the original microbench is research `data/hsf-5p/microbench-20261025/` @ `1452e226d`).

## 1. What HSF-5.P is

A host-pinned KV mirror for the MI210 np4 slots (DI-140 fired by HSF-5, see `docs/design/hsf-5-host-kv-mirror-costing-20261024.md`): mapped host tier on the membind=3 node, KV tail written as a graph-safe copy, a recurrent checkpoint every k=6 steps per slot, restore by bulk H2D. Prototype branch `experimental/hsf-5p-host-kv-mirror-20261024` @ `14d0f7fa2b61c26f8edfacf91c300c37962e1d20`, cut from champion `dcc853b55`. Runtime argv: `--kv-host-mirror k=6,node=3,mode=lag,path=auto`, np4, DFlash2 n-max 7, q8_0 KV, graphs ON. The current champion C5 is `c72ec82f5417bb2937310326120f149b665e8400`; the mirror tip is NOT the current champion and C5 has no mirror file.

## 2. Measured decode cost and gate

Source: `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/tasks-from-ws58/HSF-5P-NEXT-ATTRIBUTION.md`; research `data/hsf-5p/microbench-20261025/` @ `1452e226d`. Predeclaration sha256 `9de08e8f6b6d6639b3f60ef3acd976099419c86da7b66ea9f57c9f0e48f23f70`.

`predicted_per_token_ms` (lower is better): A1 43.88, A2 43.64 (mirror off); B 45.58, Bf 45.21 (mirror on). B is slower in all 6 waves. Delta B vs mean(A) = +4.17% against a gate of <= 3%: FAIL. G2 (graphs reused), G3 (restore equivalence), G4 (mirror engaged) PASS. Phase-1 desk report (`/mnt/raid0/llm/tmp/codex-ni-20261026-hsf5p-next/REPORT.md`): B-Abar = 1.8243 ms/token; at least 0.511545 ms/token must be removed to reach 3% (arithmetic from recorded values). The desk read found a checkpoint-serialization mechanism (the checkpoint `backend_wait` makes the main stream depend on the checkpoint D2H) plus incidental per-decode CPU work, but it did NOT apportion the 1.82 ms causally. Recommendation there: FIX (device snapshot then async host transfer), not RETIRE.

## 3. Profiling attempts (phase 2, mirror off/on/off with rocprof)

| Id | Dir | Outcome | Cause |
|---|---|---|---|
| P1 | `/mnt/raid0/llm/tmp/cal-1026/hsf-5p-next-profile-1/` | rc1, all 3 arms INCOMPLETE | memory exports SIGKILLed (`capture validation incomplete`). Offline recovery of raw memory records is derived-only, completeness UNKNOWN, not a measurement |
| P2 | `.../hsf-5p-next-profile-2/` | stopped | night whole-host HOLD (`RuntimeError('HOLD present')`): a scheduling error by the owner, not a job fault. Only A1 exists, so no cross-arm parity can be assessed |
| P3 | `.../hsf-5p-next-profile-3/` | `PermissionError(13)` | Yama `ptrace_scope=1`: reads of `/proc` for a non-ancestor process denied |
| P4 | `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf3-runtime-recovery/profile-4`, run `20261027T040542Z` | rc1 at 04:21:04Z, INCOMPLETE | first-request divergence: warmup `/completion` slot 0 (n_predict 64) differs at zero-based token 45, A1=4619 vs B=A2=20572. Warmup draft counters A1 121/45 vs B and A2 115/46. All other completions matched. Exports were natural exit 0 (not the P1 failure). See `codex-ni-20261027-hsf4-runtime-recovery/ACTUAL-FAILURE.md`, `WS58-DECISION-PACKAGE.md` |
| Determinism job | `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf-determinism-job/out/20261027T055316Z` | rc0, COMPLETE | 4 fresh mirror-OFF processes (U1,U2 untraced; T1,T2 traced): 4/4 identical, all 30 completions per arm, token 45 = 20572 in all. Normalized hash `a8aa28c5e8907f566a0df77a54f435870ed6b4c81ce4a2d8d1bbb7bfef1f6b05`; PROFILE_SUMMARY sha256 `91e250494cebfcf12a7e1db497c15bc6935aa5cc3e6577cc60345bf4dbab520d`. Did NOT reproduce the P4 divergence; two processes per condition does not establish determinism or its cause |
| P5 | `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf-profile5/out/20261027T063913Z` | rc1 at 06:53:23Z, INVALID | restore-state control failed (`B: restore state invalid`). No first-request divergence recurred (all bodies/tokens equal). A/A median spread 1.82565% (passes the 3% screen). No attribution follows |

## 4. Source-proven restore mechanism (why P5 restore differed)

Source: `/mnt/raid0/llm/tmp/codex-ni-20261027-hsf-restore-source-audit/PROPOSED-REVIEW.md`, hashes in its `EVIDENCE.sha256`, read from `git show` of 14d0f7fa2 and C5.

- In lag mode, save selects the latest VALID recurrent checkpoint C and writes only the prefix up to it. The live slot is unchanged until erase.
- `poll(true)` at save drains outstanding copies but does NOT advance the checkpoint to the live position.
- R = C + 1 = M + 1 - replay_tokens (N - T when N = M + 1).
- Observed: saved/restored 4079 vs erased 4116; `replay_tokens=37 replay_steps=6` at `server.B.log:1820`; 4116 - 37 = 4079. Continuation prompt evaluated 38 tokens in B vs 1 in A1/A2 (4117 - 4079 = 38; one token is the baseline gap). Bytes: B 696747784 vs OFF 740054204.
- Lag-truncated save skips the live draft-state save (`server-context.cpp:2949-2951`), and restore clears ctx_dft, so B reconstructs drafting state differently.
- C5 saves the full live state with no truncation, so the behavior difference is in the mirror's save policy, not a C5 defect.

## 5. NOT established

- The attribution of the 1.82 ms/token decode cost to a specific copy/sync/scatter term (no valid profile exists; P1-P5 all failed or invalid).
- The cause of the 90/50 (B) vs 55/55 (A1/A2) continuation draft counts. The lifecycle asymmetry is source-proven; which drafter field accounts for the 35 extra proposals and 5 fewer accepted is not.
- The decomposition of 37 into per-step advances (per-decode accepted-token vectors are unavailable).
- The cause of the P4 first-request divergence, or whether tracing changes its incidence; cold-JIT/cache and graph-init state were not recorded as initial witnesses.
- Blast radius via GitNexus on the pinned experimental snapshots (UNKNOWN).

## 6. Repair design being built now (Codex, T2, model-free)

- Port the mirror onto the FULL current champion C5 `c72ec82f5417bb2937310326120f149b665e8400` in an experimental tree (never production; retain all champion features and the overlay).
- Save drains to the LIVE position (so R = N, no replay tail, live draft state preserved), instead of selecting the lagged checkpoint.
- The new save behavior is an opt-in knob, default OFF.
- Validation is a model-free restore round-trip test (saved = erased = restored token count, no extra continuation prompt tokens). No GPU, no benchmark.
- Any later promotion must be a full-candidate new production version validated on GPU+CPU as a whole.

## 7. REVIVAL CHECKLIST (GPU testing deferred pending operator go)

1. Run P6 attribution (mirror off/on/off) with the all-output bar: exact-body token equality over warmup plus every measured and restore request; unequal output stays an INCOMPLETE control, never excluded or regraded.
2. Fix capture/shutdown: 180 s export reserve per arm, natural-exit-0 exporters, no SIGKILL; captured PIDs/starttick custody.
3. Use a launch-time evidence helper that reads process state at launch (avoid non-ancestor `/proc` reads under Yama `ptrace_scope=1`, the P3 failure).
4. Record startup metadata: argv/env, process birth, DSO hashes before/after, graph/batching startup logs, startup sequence, JIT-cache path candidates.
5. Predeclare the first-request-divergence rule (what a warmup token mismatch means and what is done) BEFORE the run.
6. Cache is OBSERVED, not manipulated: record residency with during-run witnesses; any isolated-cache intervention is a separately predeclared follow-up.
7. Check HOLDs/calendar before booking (P2 lesson); GPU-quiet, mi210_0 plus host threads 184-191, private port.
8. Restore-state control must pass (saved = erased = restored; continuation cache = restored) before any attribution claim; run on the repaired C5 build, with binary/mapped-library identity and strings-compiled-in checks.
9. Budget estimate from P4: about 450 s per process, window about 2100-2400 s; trace output about 16 GiB for three arms.
