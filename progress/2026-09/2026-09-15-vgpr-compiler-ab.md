# 2026-09-15 — Research intake (MI210 compiler write-up) + compiler-only IQ2_XXS VGPR A/B

Session: shared clone, no lane (operator-spawned `/research-intake`); index appended as text, nothing staged.

## Intake (Stage 1 complete, report delivered; Stage 2 awaits operator selection)

- intake-1398: pasted, unsourced write-up. It is a reply to our own X thread `x-2026-09-15-mi210-low-quants`,
  so its 64-VGPR claims are circular; its attribution percentages are uncitable. credibility 0.
- Expansion intake-1399–1408 (cap 10): VeriLocc, AsmEvo, Magellan, MLGO, Meta LLM Compiler, kernel-anvil,
  llama.cpp PRs #23227 / #10498 / #14624, ROCm/llvm-project #4434. All `stage1-unverified`.
- `validate_intake.sh` OK (local tree at the time). `.research-session.json` holds the 5-row steering ledger;
  the previous session record is nested, not lost.

## Compiler-only VGPR A/B (operator-directed, zero GPU)

Artifact: `artifacts/gpu-aux-baselines/a10_iq2_vgpr_compiler_ab_20260915.md`.

- Reproduced the shipped v9 register table exactly from a single-TU rebuild in a detached worktree.
- The effective lever is `#pragma clang loop unroll(disable)` on the 4-trip sign-unpack loop.
  - IQ2_XXS production MoE decode: 78→44 VGPR (6→8 waves/SIMD).
  - IQ3_XXS: 71→44.
  - Zero spill; other quants unchanged.
  - Q3_K regresses (88→96) if the pragma is applied to its loop.
- About 30 AMDGPU register-allocator/scheduler knobs: no gain. The existing `#pragma unroll` is a no-op.
- `-O1` / `--unroll-count=1` also cross 64 but regress Q8_0/Q4_K.
- Static only. Executed instructions per block are probably about unchanged, and throughput is untested.
- Host hygiene: core 91 (off autokernel's CPU anchor and its SMT siblings), nice 19, ionice idle, serial.

## Open (named blockers)

- **GPU decode bench of the pragma candidate.** Blocked by the running autokernel CPU anchor window: a GPU
  run's host threads perturb the CPU floor. Run it after that window, on an experimental full candidate
  build, with a correctness pair.
- **Stage-3 plan items.**
  - Autocompiler decision package.
  - AK-QL-2 re-scope (unroll as the VGPR multiplier).
  - Belief-kernel wiring row for static compile-sweep register stats.
  - kernel-anvil / #23227 dives.

## Stage 2 / 2b / 3 / 4 (same day)

### Dives and index
- Stage 2 dived intake-1399, 1400, 1404, 1405 and 1407.
- Stage 2b round 1 wrote intake-1409..1417, dived intake-674/678 in place, and corrected intake-969.
- Stage 2b round 2 wrote intake-1418..1424.
- The operator selected sources at each close-out; round-3 declines were approved with the plan.
- `validate_intake.sh` OK; pre-session entries changed by appended fields only.

### Premise correction found while planning
- ROCm0 serves Q8_0 27B and Q4_K_M VL-30B-A3B. No IQ-format model is on the GPU.
- So the unroll(disable) IQ2/IQ3 lever has zero live payoff and is TRIPWIRE-gated.

### Operator decisions (approved plan `melodic-inventing-sonnet.md`)
- **D1:** no general autocompiler. Compile control is a latent AutoKernel search space (AK-QL-8).
- **D2:** no toolchain unpin; the known hazards are now runbook gates.

### Stage 4 edits (insert-only; nothing staged or committed; shared clone, no lane)
- `autokernel-research-loop.md` §22.2: AK-QL-2b [x], AK-QL-7 [ ], AK-QL-8 [x].
- `mi210-q8-dequant-gemv-roofline.md`: v_perm_b32 note, INF37-IQ-2 [ ], INF37-IQ-3 [x].
- `agentic-rocm-kernel-authoring.md`: #19984 correction note.
- `docs/runbooks/rocm-upgrade-checklist.md`: 3 preflight items and 1 validation-gate item; failure-signature paragraph rewritten.
- `vidya-belief-substrate-program.md` SC76 [ ], plus a candidate source row in `scripts/vidya/adapters/README.md`.
- Artifact addendum on `a10_iq2_vgpr_compiler_ab_20260915.md`.

### Counts and checks
- Checkboxes: 3 new open, 3 new closed.
- `index_state.py --check`: 0 problems.

### Wrap-up renumbering (2026-09-15)
- The session worked in the shared clone, whose `main` was 330 commits behind `origin/main`.
- A parallel intake session (`noninf-20260914`) had already published intake-1367..1397.
- This session's 27 entries were renumbered **1367..1393 → 1398..1424** (+31) in every committed file.
- The port was built on a throwaway `origin/main` worktree.
- There are no source collisions with the parallel session's entries.
- intake-1346..1366 were already on origin.
- The in-session Stage-1..4 report and the relay to the AutoKernel session used the OLD numbers. Map them +31.
