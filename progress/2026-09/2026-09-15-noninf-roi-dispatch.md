# 2026-09-15 — non-CPU-inference ROI sweep: dispatch + integration

Session without a lane (ad-hoc, shared clone). All work done in private worktrees off origin/main; this file lands
with the integration branch `sub/integrate-20260915`.

**Environment finding:** the shared `/workspace` clone was 332 commits behind origin/main (local `main` @ 2026-09-09).
The first ROI overview was verified against that stale tree, so several "open" items were already closed upstream
(M-12e `dcb769c1`, SC67 `baaa6741`, MHS-1, SEQ-B2). Every later agent read handoffs from origin/main.

## Landed (branches, unpushed at time of writing)
- **Stale-row cleanup** (`sub/stale-row-cleanup-20260915`): 8 index rows re-pointed, OP-22 retired (container PID 1
  2026-08-13, after `136894e8`), NIB2-64 + NI-IO ticked, RTG-49 status fixed, RE-1 note.
- **RECLAIM-2 / OP-37 resolved** (same branch): operator kept `UD-IQ4_XS` (INF-67 megakernel benchmark artifact) and
  `IQ4_XS-uniform` (recipe pin, re-hashed `4bfb9849…` OK). Deleted `-gateup-r16`, `-uniform-r16`, and the recipe-REJECTED
  self-contained MTP head. Record in `cpu-decode-roofline-program.md`.
- **R23-61a** GPU serving floor, PRE-BIOS: 7.897% p95_dev, process unit, n=24, CI [5.520, 11.322]%, recipe-hash
  verified, residency 24/24. R23-61b post-BIOS repeat filed. CI code: research `sub/r23-61a-floor-n-ci` `a25aaf1f`.
- **NIB2-69** (orchestrator `sub/nib2-69-strict-gate`): check-mode artifact root-caused; one NUMA mode per `check`;
  unit failures 33 → 0.
- **OBS-8 / OBS-6** (`sub/obs-8-obs-6`): port gate refuses when blind or occupied; health check scores unreadable as UNKNOWN.
- **DF2-QWOPUS scoping** (`sub/df2-qwopus-scoping`): don't train yet; K1 gate first (`docs/design/df2-qwopus-scoping-20260915.md`).
- **OP-38 P-KLD package** (`sub/op38-pkld-package`): annex + ratify script (never run) + decision package.
- **CME-2 + SC68 done, CME-1 partial** (research `sub/cme-1-beam-adapter`, root `sub/sc68-beam-write-side`). BEAM data licence is CC BY-SA 4.0.
- **AP-50 cockpit** (orchestrator `sub/ap-50-decision-cockpit`, root `sub/ap-50-cockpit-page`): built and tested offline; not deployed.
- **AutoKernel disk sweep** (`sub/autokernel-disk-sweep`): DRY-RUN manifest (607 GB scanned; REMOVE 34.8 GB, KEEP-dirty
  369.9 GB), plus design review `docs/design/autokernel-disk-hygiene-20260915.md`. `--apply` only after operator review.
- **Disk:** ~195 GiB reclaimed (r16 ×2, rejected MTP head, NIB2-65/66 partials); `/mnt/raid0` 156 → 336 GB free.

## Open, needs operator
- EVL-25: ~19 GB Qwen3.5-9B download vs 7B stand-in.
- NIB2-65: `Qwen3-4B-Thinking-2507-GGUF` rationale conflict. NIB2-66: dirty `k28-prototype` tree.
- AutoKernel sweep apply (host root, fresh dry-run, review). 29 dirty acceptance trees (48 GB) hold unique diffs.
- OP-38 ratification; OP-38 → OP-46 renumbering proposal.
- AP-50 deploy (API reload + hub restart).
