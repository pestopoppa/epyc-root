# 2026-09-22 — v10 kernel promotion (store cutover) + promotion-runbook hardening

Session: post-BIOS rebench → champion qualification → v10 store cutover → runbook audit.
Host: EPYC 9655 NPS4, memory interleave ON, 5600 MT/s (operator-applied at reboot).

## What landed

| Area | Change |
|---|---|
| Champion defects | `llama-model.cpp` nextn read/assert restored to v9 ordering (gemma4-assistant exempted from the early generic read); `llama-graph.cpp` MoE fusion gated on all-CPU backends |
| Kernel store | `kernels/production/{cpu,gpu}` → `builds/{cpu,gpu}-20260921-ffc1bac82`; `archive/{cpu,gpu}-20260810-0db32c06e` populated for the first time since 2026-07-31 |
| Store wiring | `scripts/lib/env.sh` (root + orchestrator) store-resolved, fail-closed; `scripts/lib/executor_paths.py` `base_dir` from `backend_dir("cpu")` (fixed a split-brain where executor launched v9 while everything else ran v10) |
| Verification | NEW `scripts/session/verify_kernel_store.sh` (symlink → target → binary → ggml linkage, per backend, incl. companion tools); wired into `session_init.sh` §0.55 |
| Freeze scope | `scripts/validate/kernel_freeze_scope.py::_backend_of()` resolves via `backend_dir()` instead of a `"build-hip" in p` substring — fixed gpu 0→4 roles, cpu 12→8 |
| Dashboard | `src/api/routes/dashboard_topology.py` `_is_gpu_binary()` resolves through the store — GPU roles no longer report substrate `cpu` |
| Skill | NEW `.claude/skills/kernel-promotion/` — 9-phase contract, rollback anchor as phase 0, plus `anchor.sh` / `preflight.sh` / `verify_serving.sh` |
| Provenance | `PROVENANCE.md` written into both `builds/*-20260921-ffc1bac82/`; `artifacts/operator/v10-cutover-20260922-ffc1bac82/` holds 4 manifests (448 files) + `journal.json` |

## Measurement discipline

Operator ruling, binding: **no baselines — max-performance numbers only.** An unlabelled
spec-dec-off table was presented early in the session and retracted; both banked artifacts now
carry warning banners. Comparison grammar for promotion is *max-performance recipe on v9 vs
max-performance recipe on the candidate*.

## Rollback was exercised for real

A first promotion attempt shipped a partial build (`--target llama-server llama-bench` → 2
binaries vs 92). It was rolled back through the archive anchor, rebuilt in full, and the verifier
was extended to count companion tools so the same shape cannot recur.

## Status: promotion is INCOMPLETE

The **store side** is done and serving. The **freeze side** is not: there is no
`production-consolidated-v10` branch, no `FREEZE-V10` ratification, and `verify_llama_cpp.sh`
still attests v9/10125 while the store serves 10303.
`artifacts/operator/v10-qualification-20260921-ffc1bac82.json` records this as `INCOMPLETE`,
including both earlier overstatements rather than erasing them.

Blocked on one operator-run command (the branch cut in the frozen tree); the command has been
handed over verbatim. Everything downstream — ratification artifact, verifier constants, the
CLAUDE.md freeze block, and the champion reseed off the newly frozen kernel — is sequenced
behind it.

## Known residue

The v10 binaries' RUNPATH ends in an empty element (`$ORIGIN:`), so the loader also searches
CWD; v9's archive is clean. Harmless here, fix at the next rebuild. (My own RUNPATH check
initially had the very bug it was written to catch — `tr ':' '\n'` drops the trailing empty
field; fixed with awk field splitting.)

## Deferred to the stack-change window

R23-65 CPU floors (42 launches), R23-64 thread sweep (18 launches), speech `$ORIGIN` rebuild,
Flash-Next quality gate, the lineup change (C1–C4 decisions outstanding), and the disk deletion
of the deprecated gemma4 / Qwen3.5-122B / Next-80B weights at session end.
