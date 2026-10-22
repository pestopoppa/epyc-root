# 2026-10-22 research intake: SLQ, IST-DASLab, kaitchup Qwen3.8-27B SLQ (intake-ist-slq-20261022)

Run by a subagent for workspace-58. Lane `intake/ist-slq-20261022`, worktree from origin/main `3251a246b`.
Sources: arXiv 2605.02404 (SLQ), github.com/IST-DASLab (org triage), huggingface.co/collections/kaitchup/qwen38-27b-slq.

## Stages

- **Stage 1:** 23 entries, intake-2461..2483: 3 submitted sources, 17 IST-DASLab repos and 3 expansions (the ISTA 27B
  GSQ-RCO GGUF, the 27B NVFP4 prefiller, arXiv 2608.15046). marlin was re-encountered (intake-1531). Phase 1+2 ran on 5
  parallel agents.
- **Stage 2:** the operator pre-approved all recommended dives for up to 4 waves. All 4 waves ran.
  - Wave 1: groups A-E dived 19 entries.
  - Wave 2: groups F-G Stage-2b, intake-2484..2490.
  - Wave 3: group H, intake-2491..2492.
  - Wave 4: group I, intake-2493.
  - Second readers checked 186 + 104 + 45 anchors. 10 mis-indexed anchors were re-pointed, and 3 non-verbatim MathML
    renderings in intake-2475 were flagged.
  - Index corrections: intake-2474, intake-2461 and intake-2492 (restatement vs corroboration, stale pointers), plus a
    dated re-encounter note on intake-1256.
- **Stage-2 close-out:** two surfaced sources were not dived because the wave cap was reached: AFPQ (arXiv 2311.01792)
  and aiha-lab/MX-QLLM. Both are recorded in intake-2493.
- **Stage 3:** plan at `/mnt/raid0/llm/tmp/intake-ist-slq-20261022/stage3/STAGE3_PLAN.md`. Its validator payload passes
  `validate_intake.sh --plan-file/--session-file`.
  - Contents: 57 ledger rows; 5 packets (P1 27B A/B EXL3-X0D, P2 EAR column, P3 Q38FN allocator NEW-12, P4
    prefill/decode probe NEW-13, P5 degradation statistics); K1-K2 knowledge; M1-M4 triggers; 10 proposed task lines.
  - **Not approved; Stage 4 not run.**

## Key findings

- **The kaitchup SLQ checkpoints cannot be served by us.** They are vLLM/Humming CUDA-only (no ROCm, CPU or GGUF path).
  - We serve Q8_0 GGUF; there is no FP8 27B in our stack.
  - SLQ has no speed or quality case against our Q8_0. EAR99 is not smaller than Q8_0.
  - Recommendation: do not download.
- **The relevant lower-byte candidate is a different artifact.** ISTA-DASLab Qwen3.8-27B GSQ-RCO GGUF (intake-2481): 11-13
  native ggml types including IQ1, with IQ3_S at 0.42x Q8_0 bytes.
  - Its card results are author-reported single runs on small samples.
  - Roofline estimate: 0.94-1.65x no-draft, and 0.6-1.1x with DFlash2 on v10.
  - The DFlash2 drafter is tokenizer-compatible: keep it, but measure acceptance.
- **GSQ code has no GGUF/IQ export.** The iqk NEW-10/NEW-11 trigger stays unfired.
- **Disaggregated quantization accuracy is not llama.cpp-native.** It is BF16-dequantized vLLM. The untrained
  higher-precision prefill control is real at IQ1/IQ2 and harmful at 3-bit or more.

## Wrap-up gates

- **Checklist-sync:** 0 checkbox flips. No handoff was edited, because the intake skill forbids handoff writes before
  plan approval.
- **Derived-actionables:** all 57 ledger rows have a terminal mapping in the plan.
  - 16 rows map to 10 proposed tasks, not filed, pending approval.
  - 10 explicit declines.
  - 18 knowledge-only rows.
  - 13 rows are trigger prose (M1-M4).
- **Index rows:** prepared only, for workspace-58 under ruling (b). These are the optional INF-80 and INF-26 next-action
  refreshes in the plan; there are no new stubs.

## Compute

None was run. The calendar-owner table is in the plan:
- the EXL3-X0D download (~40 min);
- the X0D quality pass (correctness class, 1-2 h);
- the X0D speed pass (timing class, at least 2.5 h, exclusive);
- NEW-12 (CPU correctness, 3-5 h / 20-25 h);
- NEW-13 (CPU correctness, 3-5 h);
- EXL3-EAR2 (55.6 GB BF16 download, operator call).

## Deviation

The wave-3 dive agent imported and called pure functions of the downloaded LLM-Accuracy-Stats script (milliseconds of
CPU, no state change). This is recorded in the session `process_deviations`.
