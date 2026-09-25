# EXL3 CPU and MI210 research intake — 2026-09-25

## Problem

Turn the 2026-09-25 EXL3 Hopper report and the surrounding EXL3, QTIP, Marlin,
CPU, ROCm, model, and checkpoint material into a viable implementation program
for EPYC 9655 and MI210/gfx90a. Custom CPU and HIP kernels are explicitly in
scope. The frozen `production-consolidated-v10` kernel must remain unchanged.

## Research and decisions

- Ingested and verified 35 records, `intake-1528` through `intake-1562`.
- Dispositioned all 38 derived actionable rows exactly once and recorded 23
  accepted surfaced-source declines.
- Established separate implementation regimes: scalar and AVX-512 CPU decode,
  wave64 gfx90a decode GEMV, gfx90a MFMA prefill, mixed-K MoE dispatch, and a
  later hybrid CPU/GPU streaming study.
- Kept MCG behind an independent scalar oracle because the research did not
  establish an optimized MCG CPU implementation or a transferable `mul1`
  fusion.
- Treated W4A16 as an alternative deployment family. Any codec-quality claim
  must hold teacher revision, architecture, expert plan, evaluation panel, and
  storage budget constant.
- Declined CUDA/PTX, RDNA wave32, Blackwell scheduling, and foreign benchmark
  constants as direct gfx90a implementation defaults. They remain algorithmic
  and test references.

## Durable changes

| Surface | Result |
|---|---|
| `handoffs/active/exl3-cpu-mi210-implementation.md` | Created `INF-80` with 6 completed research decisions, 10 open implementation tasks, eight gates, and the critical path beginning at `EXL3-1`. |
| Quantization and ROCm handoffs | Added ownership boundaries and pointers without reopening the retired Qwen-specific CPU no-go or conflating EXL3 with IQ*_KT. |
| `scripts/vidya/adapters/README.md` and Vidya handoff | Registered prospective `epyc.exl3.measurement.v1` and `epyc.exl3.verifier.v1` write-side contracts. |
| `research/intake_index.yaml` and `.research-session.json` | Persisted verification, integration dispositions, steering coverage, derived-actionable coverage, and explicit declines. |
| `research/intake-stage3-plan-2026-09-25-exl3-cpu-mi210.md` | Preserved the approved implementation plan and Stage-4 execution record. |

## Verification and publication

- `bash scripts/validate/validate_intake.sh`: passed, 1,558 entries.
- `python3 scripts/handoffs/index_state.py --check`: passed with zero problems.
- Changed-file citation gate: passed, 175 citations across seven documents.
- Metadata audit: 35 integrated entries, 10 steering rows, 23 unique explicit
  declines, and 38 unique derived rows.
- `git diff --check`: passed.
- Repository-wide citation scan still reports two pre-existing overturned
  citations in `docs/research-intake/p-kld-annex-proposals-20260923.md`; the
  changed-file gate is clean.
- Published root commits `0baec47c` and `cd3ec538` to `origin/main`. The intake
  worktree and local branch were removed after `git cherry origin/main` became
  empty.

## Wrap-up compilation

- The generated handoff screen reported zero prune candidates; `INF-80` remains
  active and its first screen still exposes the next action, so no archival or
  compaction was warranted.
- Compiled all 14 content-hash changes since the previous wiki watermark into
  `quantization`, `hardware-optimization`, `autonomous-research`,
  `tool-implementation`, `agent-architecture`, and `benchmark-methodology`.
- Wiki lint passed with zero errors and 91 existing warnings. The refreshed
  source manifest contains no remaining content-hash drift.
- README freshness produced no warnings.

## Checklist sync and next action

- Completed checkboxes recorded by the intake: **6** (`EXL3-R1` through
  `EXL3-R6`).
- New open tasks: **11** — `EXL3-1` through `EXL3-10` plus the prospective
  `VB-EXL3-CPU-GFX90A` writer.
- Next action: `EXL3-1` — freeze the canonical EXL3 artifact and metadata
  contract, portable `mul1` and MCG oracles, revision-pinned real fixtures, and
  the two evidence writers before the first correctness or performance run.
