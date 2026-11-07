# Inference Research — Active Backlog

**Purpose**: dispatch. Kernels, quantization, serving performance, models. CPU and GPU both live here — sub-area is the Track column, not a separate file.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**Compute-gated rows** are packed onto the host by the calendar owner under [`.claude/skills/inference-backlog-scheduling/`](../../.claude/skills/inference-backlog-scheduling/SKILL.md); a row is QUEUED only when ARMED with a live launcher, otherwise BACKLOG with a named blocker.

**History**: superseded narration for this index lives in [`../archived/inference-research-index-history-through-2026-08-10.md`](../archived/inference-research-index-history-through-2026-08-10.md).

**IDs are stable.** `INF-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| INF-06 | autokernel research loop | [autokernel-loop.md](autokernel-loop.md) | C7r is champion (`62cb6a6af`); AK-ASM program decided (H8b dropped E2E, FA r5 keep in C7r); next: GDN-SHARE-1 MI210 to pick the C8 target | INF-48, EVL-47 |
| INF-65 | autokernel aggregate candidate (champion) | [kernel-champion-and-promotion.md](kernel-champion-and-promotion.md) | C8 fold ledger (main-inf22): C6-LOCAL-SERVING-PROFILE + CODE28K on C7r, then triage adopted fold candidates | INF-06, INF-50 |
| INF-82 | autokernel akx program (keep gate + all dims) | [autokernel-akx-program.md](autokernel-akx-program.md) | workspace-a6: adopt or route each stale AKX box (no staleness declines), then AKX-P0a census producer | INF-06, INF-65 |
| INF-83 | v11 promotion checklist | [v11-promotion-checklist.md](v11-promotion-checklist.md) | Keep the v11 runbook current: log each champion CAS carry-in (C7r: V11-124); boxes close only at promotion | INF-65 |
| INF-84 | workspace-58 champion calibration | [workspace-58-champion-calibration.md](workspace-58-champion-calibration.md) | CH-27a: repair the store-image recipe-digest mismatch on C7r, re-run the ch27 dry plan to actionable | INF-65 |
| INF-70 | cpu decode roofline program | [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) | CLS-RECT-1, then G2-CONC on coherence_gate; XFER-3 paired task eval (uniform IQ4_XS); XFER-4b allowlist prefill A/B + task eval | INF-65 |
| INF-77 | deepseek v41 flash evaluation | [deepseek-v41-flash-evaluation.md](deepseek-v41-flash-evaluation.md) | W5 closed INVALID; W5d baseline+MMID 10-24 ~10:00Z, C46 j64 repro 10-23 q2; rest held for AK kernel work; W8d ram_admit | INF-48, RTG-58 |
| INF-79 | conversation stack (speech) | [speech-and-multimodal.md](speech-and-multimodal.md) | Qualify the repaired STT5 offline scorer, retain filed WER, then finish STT3 acceptance and STT7 predictions | — |
| INF-80 | exl3 cpu mi210 implementation | [quantization-and-low-bit.md](quantization-and-low-bit.md) | EXL3-6c5a: emit epyc.exl3.measurement.v1 rows (10-04 copy + research data/exl3-6c5-quality), ingest, tick; 6c5b p1 margin | — |
| INF-33 | log linear gated deltanet readiness | [model-architecture-readiness.md](model-architecture-readiness.md) | Wire hattention_recurrent() into HGatedDeltaNetAttention.forward and confirm it reproduces chunk-path logits on CPU | INF-48 |
| INF-45 | numa topology cutover resume | [numa-placement-and-contention.md](numa-placement-and-contention.md) | P0-3 — cold-start the stack, re-bench the contention matrix, commit + push all three repos | — |
| INF-48 | rocm verify profile backend | [rocm-kernel-authoring.md](rocm-kernel-authoring.md) | Repair audited C6 carriers, wire oracle/Ghost boundary | EVL-47 |
| INF-50 | speculative decoding mtp refresh | [speculative-decoding.md](speculative-decoding.md) | Run XGRAMMAR-A2 raw p95 and 16-prompt parity; qualify new benchmark symbols separately before any fold | — |
| INF-59 | yarn context extension research | [long-context-program.md](long-context-program.md) | Fit DFlash2 draft at 512k (GPU 52.55>52 GiB; C7 server lacks -cd); run YARN-NATIVE-WINDOW-GATE | RTG-58 |
## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
