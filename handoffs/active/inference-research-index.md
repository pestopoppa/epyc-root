# Inference Research — Active Backlog

**Purpose**: dispatch. Kernels, quantization, serving performance, models. CPU and GPU both live here — sub-area is the Track column, not a separate file.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**Compute-gated rows** are packed onto the host by the calendar owner under [`.claude/skills/inference-backlog-scheduling/`](../../.claude/skills/inference-backlog-scheduling/SKILL.md); a row is QUEUED only when ARMED with a live launcher, otherwise BACKLOG with a named blocker.

**History**: superseded narration for this index lives in [`../archived/inference-research-index-history-through-2026-08-10.md`](../archived/inference-research-index-history-through-2026-08-10.md).

**IDs are stable.** `INF-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| INF-06 | autokernel research loop | [autokernel-loop.md](autokernel-loop.md) | Read surface row A2 (iglp0); AK-H5-VERIFY full-shape A/B before any hand-asm FA keep; GDN-SHARE-1 MI210 picks the C8 target | INF-48, EVL-47 |
| INF-65 | autokernel aggregate candidate (champion) | [kernel-champion-and-promotion.md](kernel-champion-and-promotion.md) | C8 candidate fold5 a08f7eb0b: promotion blocked; root-cause and fix C8-NP4-GARBAGE, re-run parity | INF-06, INF-50 |
| INF-82 | autokernel akx program (keep gate + all dims) | [autokernel-akx-program.md](autokernel-akx-program.md) | AUTO-4 landed; replay 6.528% block once a clean floor exists; build AKX-P1e classifier; wire ALL-31 gates; then P0a census | INF-06, INF-65 |
| INF-83 | v11 promotion checklist | [v11-promotion-checklist.md](v11-promotion-checklist.md) | Keep the v11 runbook current: log each champion CAS carry-in (C7r: V11-124); boxes close only at promotion | INF-65 |
| INF-84 | workspace-58 champion calibration | [workspace-58-champion-calibration.md](workspace-58-champion-calibration.md) | CH-27a: repair the store-image recipe-digest mismatch on C7r, re-run the ch27 dry plan to actionable | INF-65 |
| INF-70 | cpu decode roofline program | [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) | CLS-RECT-1, then G2-CONC on coherence_gate; XFER-3 paired task eval (uniform IQ4_XS); XFER-4b allowlist prefill A/B + task eval | INF-65 |
| INF-77 | deepseek v41 flash evaluation | [deepseek-v41-flash-evaluation.md](deepseek-v41-flash-evaluation.md) | W5 closed INVALID; W5d baseline+MMID 10-24 ~10:00Z, C46 j64 repro 10-23 q2; rest held for AK kernel work; W8d ram_admit | INF-48, RTG-58 |
| INF-79 | conversation stack (speech) | [speech-and-multimodal.md](speech-and-multimodal.md) | Qualify the repaired STT5 offline scorer, retain filed WER, then finish STT3 acceptance and STT7 predictions | — |
| INF-80 | exl3 cpu mi210 implementation | [quantization-and-low-bit.md](quantization-and-low-bit.md) | EXL3-6c5a: emit epyc.exl3.measurement.v1 rows (10-04 copy + research data/exl3-6c5-quality), ingest, tick; 6c5b p1 margin | — |
| INF-45 | numa topology cutover resume | [numa-placement-and-contention.md](numa-placement-and-contention.md) | P0-3 — cold-start the stack, re-bench the contention matrix, commit + push all three repos | — |
| INF-48 | rocm verify profile backend | [rocm-kernel-authoring.md](rocm-kernel-authoring.md) | Repair audited C6 carriers, wire oracle/Ghost boundary | EVL-47 |
| INF-50 | speculative decoding mtp refresh | [speculative-decoding.md](speculative-decoding.md) | Bind DF2-EXL3 target on REVISION; file writer-race r4 at .ended; run CAFE-2 r2 and DF2-13-CLASSIFY (main-inf22 owns MI210 boxes) | — |
| INF-59 | yarn context extension research | [long-context-program.md](long-context-program.md) | Run YARN-NATIVE-WINDOW-GATE; then the REPL-EMB-A7 file + bounded-read probe (harness-program.md); ≥256k YaRN parked until C8-1 | RTG-58 |
## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
