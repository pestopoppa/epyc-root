# Inference Research — Active Backlog

**Purpose**: dispatch. Kernels, quantization, serving performance, models. CPU and GPU both live here — sub-area is the Track column, not a separate file.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**Compute-gated rows** are packed onto the host by the calendar owner under [`.claude/skills/inference-backlog-scheduling/`](../../.claude/skills/inference-backlog-scheduling/SKILL.md); a row is QUEUED only when ARMED with a live launcher, otherwise BACKLOG with a named blocker.

**History**: superseded narration for this index lives in [`../archived/inference-research-index-history-through-2026-08-10.md`](../archived/inference-research-index-history-through-2026-08-10.md).

**IDs are stable.** `INF-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| INF-06 | autokernel research loop | [autokernel-loop.md](autokernel-loop.md) | Land AITER topksoftmax/i8gemm C13 ports; H10b dense defect; AA-bisect r4 (GPU suspects); GPU exact lane waits on A/A fix; GDN-SHARE-1 | INF-48, EVL-47 |
| INF-65 | autokernel aggregate candidate (champion) | [kernel-champion-and-promotion.md](kernel-champion-and-promotion.md) | C14 = C13 + FA-ALLMASK fix (FOLD_READY) + q8_1 fix, after q81 r4 passes; farows verify-quiet row; C12 CPU KEEP provisional | INF-06, INF-50 |
| INF-82 | autokernel akx program (keep gate + all dims) | [autokernel-akx-program.md](autokernel-akx-program.md) | Fix C12 CPU mul_mat IQ3_XXS/Q6_K (QDEC r3) + QDEC judge; q81 r4 edge leg; EDGE-HIP-NONFINITE; LB4.9 per-route bar | INF-06, INF-65 |
| INF-83 | v11 promotion checklist | [v11-promotion-checklist.md](v11-promotion-checklist.md) | Run V11-C13-GPU-LOADCHECK (row 1b); flip llguidance default at promotion (D2); carry C13 CAS into V11 log; C14 fold per INF-65; D6/D7 | INF-65 |
| INF-84 | workspace-58 champion calibration | [workspace-58-champion-calibration.md](workspace-58-champion-calibration.md) | Q38FN floor moved to AK-C9-Q38FN-FLOOR (INF-82); revisit CH-27 boxes after it lands | INF-65 |
| INF-70 | cpu decode roofline program | [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) | Q38P-1 r4 on C13 queued (profiler path inside Landlock fence); XFER-4b prefill A/B + task eval; G2-CONC on candidate; WRAP-8 rerun | INF-65 |
| INF-77 | deepseek v41 flash evaluation | [deepseek-v41-flash-evaluation.md](deepseek-v41-flash-evaluation.md) | W5 closed INVALID; W5d baseline+MMID 10-24 ~10:00Z, C46 j64 repro 10-23 q2; rest held for AK kernel work; W8d ram_admit | INF-48, RTG-58 |
| INF-79 | conversation stack (speech) | [speech-and-multimodal.md](speech-and-multimodal.md) | Qualify the repaired STT5 offline scorer, retain filed WER, then finish STT3 acceptance and STT7 predictions | — |
| INF-80 | exl3 cpu mi210 implementation | [quantization-and-low-bit.md](quantization-and-low-bit.md) | EXL3-6c5a: emit epyc.exl3.measurement.v1 rows (10-04 copy + research data/exl3-6c5-quality), ingest, tick; 6c5b p1 margin | — |
| INF-45 | numa placement and contention program | [numa-placement-and-contention.md](numa-placement-and-contention.md) | P1-8 autopilot reader for region_lock_wait_s_by_holder; W2 cost era; W6 fail-open guards; then E5 Stage-B re-measure | — |
| INF-48 | rocm verify profile backend | [rocm-kernel-authoring.md](rocm-kernel-authoring.md) | RKA-VERIFY-TILE GPU + A3B48-E2E rows; C6-CONTROLLER-PROOF (r7 if queued) then LIVE-1 wiring; race-eqv with 7/7 fixtures; GATEUP-PROBE | EVL-47 |
| INF-50 | speculative decoding mtp refresh | [speculative-decoding.md](speculative-decoding.md) | DF2-13-CLASSIFY r3; EXL3 device gate; CAFE-3 | — |
| INF-59 | yarn context extension research | [long-context-program.md](long-context-program.md) | Run YARN-NATIVE-WINDOW-GATE; then the REPL-EMB-A7 file + bounded-read probe (harness-program.md); ≥256k YaRN parked until C8-1 | RTG-58 |
## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
