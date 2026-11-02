# Inference Research — Active Backlog

**Purpose**: dispatch. Kernels, quantization, serving performance, models. CPU and GPU both live here — sub-area is the Track column, not a separate file.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**Compute-gated rows** are packed onto the host by the calendar owner under [`.claude/skills/inference-backlog-scheduling/`](../../.claude/skills/inference-backlog-scheduling/SKILL.md); a row is QUEUED only when ARMED with a live launcher, otherwise BACKLOG with a named blocker.

**History**: superseded narration for this index lives in [`../archived/inference-research-index-history-through-2026-08-10.md`](../archived/inference-research-index-history-through-2026-08-10.md).

**IDs are stable.** `INF-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| INF-02 | agent collab rnd harness | [agent-collab-rnd-harness.md](agent-collab-rnd-harness.md) | Spike S3-ACH-01's actor allowlist; scope AC-CHECKPOINT-ALLOC against eligible independent continuations | — |
| INF-03 | agentic rocm kernel authoring | [agentic-rocm-kernel-authoring.md](agentic-rocm-kernel-authoring.md) | the C5 backlog; REGAUDIT-3 and AGPR-1 parked (operator 2026-09-27; resume steps in file) | INF-48, EVL-47 |
| INF-05 | attention matching kv compaction | [attention-matching-kv-compaction.md](attention-matching-kv-compaction.md) | Add exact PrefixRouter-key fingerprints to serving records; rerun KV-1 rolling-window count | — |
| INF-06 | autokernel research loop | [autokernel-research-loop.md](autokernel-research-loop.md) | GPU MMQ seeds parked (operator 2026-09-27): resume by running window_ab.sh in a GPU window (AK-MMQ-H10a/b), then AK-MMQ-H3 iglp_opt arm | INF-48, EVL-47, INF-02 |
| INF-65 | autokernel aggregate candidate (champion) | [autokernel-champion-aggregate.md](autokernel-champion-aggregate.md) | Qualify C6 serving gates and resolve baseline GPU properties; assemble the CAS review package without updating champion | INF-06, INF-62, INF-02 |
| INF-66 | autokernel teardown and rebuild | [autokernel-rebuild-program.md](autokernel-rebuild-program.md) | Investigate R23-62 champion divergence under its recorded controls | INF-06, INF-02, INF-65 |
| INF-62 | dflash2 block drafter experimental build | [dflash2-block-drafter-experimental-build.md](dflash2-block-drafter-experimental-build.md) | DF2 open rows (DF2-DRAFTER-CAPABILITY, DF2-11/12/13/15/16/20, DF2-LB1); Qwopus items CANCELLED 2026-10-27 | INF-06, INF-50 |
| INF-13 | engram conditional memory | [engram-conditional-memory.md](engram-conditional-memory.md) | Make k budget-conditional rather than fixed (intake-936 rider) | — |
| INF-16 | gemma challenge kernel techniques v7 | [gemma-challenge-kernel-techniques-v7.md](gemma-challenge-kernel-techniques-v7.md) | K10 — on a quiesced host, confirm the nodes[0] collision via stderr keylog, then re-eval Lever A and decide land/drop | — |
| INF-70 | cpu decode roofline program | [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) | CLS-RECT-1, then G2-CONC on coherence_gate; XFER-3 paired task eval (uniform IQ4_XS); XFER-4b allowlist prefill A/B + task eval | EVL-21 |
| INF-72 | moe routing locality tap | [moe-routing-tap-and-locality-measurement.md](moe-routing-tap-and-locality-measurement.md) | RT-1 (Q38FN) + RT-9 (Q36) traced/analysed, RT-5 gate not met; RT-10 DS41 tap hook (C++), then RT-6/7 on DS41 | INF-22, INF-70 |
| INF-77 | deepseek v41 flash evaluation | [deepseek-v41-flash-evaluation.md](deepseek-v41-flash-evaluation.md) | W5 closed INVALID; W5d baseline+MMID 10-24 ~10:00Z, C46 j64 repro 10-23 q2; rest held for AK kernel work; W8d ram_admit | INF-31, RTG-57 |
| INF-78 | autokernel orchestrator actor backend | [autokernel-orchestrator-actor-backend.md](autokernel-orchestrator-actor-backend.md) | OAB-30 stub e2e (incl. keep→continuation); OAB-34 16384 output-cap hit rate per role | INF-77, INF-66, EVL-37, RTG-56, UFH-01 |
| INF-79 | conversation stack (speech) | [speech-and-multimodal.md](speech-and-multimodal.md) | Qualify the repaired STT5 offline scorer, retain filed WER, then finish STT3 acceptance and STT7 predictions | — |
| INF-80 | exl3 cpu mi210 implementation | [quantization-and-low-bit.md](quantization-and-low-bit.md) | EXL3-6c5a: emit epyc.exl3.measurement.v1 rows (10-04 copy + research data/exl3-6c5-quality), ingest, tick; 6c5b p1 margin | — |
| INF-22 | gpu serving tie in program | [mi210-serving-program.md](mi210-serving-program.md) | Implement M4 fold-gate capture, current role bindings and qualified CPU/GPU execution; see audited execution route | — |
| INF-23 | heterogeneous slot fabric residency | [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md) | HSF-5.P: re-run microbench (-lv 4, G4 amendment) on GPU after v11-086-cpu ~10-25 00:00Z | — |
| INF-31 | llama cpp dsa contribution | [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md) | D4 residual — pin the faulty `dequantize_V_bf16` line and file upstream (D4 done: c49a37c4) | — |
| INF-33 | log linear gated deltanet readiness | [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md) | Wire hattention_recurrent() into HGatedDeltaNetAttention.forward and confirm it reproduces chunk-path logits on CPU | INF-48 |
| INF-37 | mi210 q8 dequant gemv roofline | [mi210-q8-dequant-gemv-roofline.md](mi210-q8-dequant-gemv-roofline.md) | Resolve Q4/IQ2 approvals; scope INF37-MOE-Q8-FUSION's experimental GLU correctness slice | INF-48, EVL-47 |
| INF-44 | numa prefill decode disaggregation | [numa-prefill-decode-disaggregation.md](numa-prefill-decode-disaggregation.md) | Blocked on INF-34 PF1 (CPU-vs-MI210 prefill crossover); then run NPD-1 or close the GPU-prefill branch | INF-22 |
| INF-45 | numa topology cutover resume | [numa-placement-and-contention.md](numa-placement-and-contention.md) | P0-3 — cold-start the stack, re-bench the contention matrix, commit + push all three repos | — |
| INF-48 | rocm verify profile backend | [rocm-verify-profile-backend.md](rocm-verify-profile-backend.md) | Repair audited C6 carriers, wire oracle/Ghost boundary | EVL-47 |
| INF-49 | sarathi serve cpu evaluation | [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md) | Re-evaluate Sarathi-Serve chunked-prefill for the eval-batch serving class (the multi-tenant trigger fired by batched-decode E2) | — |
| INF-50 | speculative decoding mtp refresh | [speculative-decoding-mtp-refresh.md](speculative-decoding-mtp-refresh.md) | Run XGRAMMAR-A2 raw p95 and 16-prompt parity; qualify new benchmark symbols separately before any fold | — |
| INF-59 | yarn context extension research | [yarn-context-extension-research.md](yarn-context-extension-research.md) | Re-plan YARN-128K-MI210 (128K items off CPU quarters); extension arms; optional YARN-AGG-1f power | RTG-57 |
| INF-61 | model evaluation queue (INF-60-gated) | [gpu-candidates-surface-qwen38-update.md](gpu-candidates-surface-qwen38-update.md) | Run a same-window n-max 4 vs 8 ABA at np≥2 before shipping the re-collected grid; then depth-sweep A4, A3, A1, FF and Laguna | INF-22 |
| INF-73 | autokernel unified surface | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) | LIVE GPU leg (serving-owner grant, ws58) | INF-66, INF-65, INF-70 |
| INF-74 | autokernel concurrent targets | [autokernel-concurrent-target-coordination.md](autokernel-concurrent-target-coordination.md) | Land INF-74-CGROUP-ROOT (root-owned cgroup delegation, Codex script), add escape tests, re-run gate; cutover rejected until then | INF-73 |
| INF-75 | autokernel cross-workload keep gate | [autokernel-cross-workload-keep-gate.md](autokernel-cross-workload-keep-gate.md) | AKX-P0d — run the W1–W6 base census on the current champion-of-record under stage claims, then AKX-P1b replay 732389d6 | INF-73, INF-66, INF-65 |
| INF-81 | autokernel all devices all dimensions | [autokernel-all-devices-all-dimensions.md](autokernel-all-devices-all-dimensions.md) | AKX-ALL-30b: write G3-first order + G1/G2 re-rank (R=1.73) into the seed draft; AKX-ALL-LB3.2 re-run via akxlb32 v2 | INF-73, INF-75, INF-77, INF-62, RTG-57, RTG-58 |
| INF-76 | model evaluation queue (EVL-08-gated) | [paw-compiled-specialists.md](paw-compiled-specialists.md) | PAW-2 — self-hosted compile spike (intake-1481 server + intake-1478 weights); then PAW-5 candidates list | EVL-08 |
## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
