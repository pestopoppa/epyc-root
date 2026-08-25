# Speculative Decoding — Compatibility Handoff

> **COMPLETED 2026-08-23 — compatibility pointer retired.** This file was a
> retained compatibility pointer (created 2026-07-11) keeping a legacy
> active-handoff path alive for older progress logs, research-intake routing,
> and the multi-handoff completion goal. It never carried its own implementation
> queue. Its live home is the active speculative-decoding handoff
> [`speculative-decoding-mtp-refresh.md`](../active/speculative-decoding-mtp-refresh.md)
> (with the Qwen/native MTP port checkpoint at
> [`qwen-mtp-llamacpp-port.md`](../active/qwen-mtp-llamacpp-port.md) and the
> historical MTP-1 ledger at `../completed/mtp-speculative-decoding.md`). The
> `01-` prefix predates the current naming convention; the file was retired and
> redirected to the live handoffs on 2026-08-23. Do not add work here.

**Status**: COMPLETED — compatibility pointer retired 2026-08-23.
**Created**: 2026-07-11
**Categories**: speculative_decoding, local_inference, hardware_optimization
**Current active work**: [speculative-decoding-mtp-refresh.md](../active/speculative-decoding-mtp-refresh.md)

## Purpose

This file keeps the legacy active-handoff path referenced by older progress logs, research-intake routing, and the current multi-handoff completion goal. It does not create a second speculative-decoding queue and should not be archived while those active-path references still exist.

## Current Routing

- Active MTP/NEXTN refresh and remaining operator-gated benches: [speculative-decoding-mtp-refresh.md](../active/speculative-decoding-mtp-refresh.md)
- Qwen/native MTP port checkpoint: [qwen-mtp-llamacpp-port.md](../active/qwen-mtp-llamacpp-port.md)
- Historical MTP-1 hybrid result: [mtp-speculative-decoding.md](mtp-speculative-decoding.md)
- Production chapter: `/mnt/raid0/llm/epyc-inference-research/docs/chapters/01-speculative-decoding.md`

## Current Verdict

As of 2026-07-20, the active implementation surface is already recorded in the MTP refresh handoff. Dense CPU MTP is validated on Gemma4-31B and Qwen3.5-9B observations, MoE CPU MTP remains low-EV because expert verification dominates, and hybrid recurrent CPU MTP remains a negative datapoint in the completed historical ledger. Production uses the single `production-consolidated-v7` llama.cpp tree with native MTP/NEXTN; the old separate `ik_llama.cpp` path is reproduction-only.

Remaining speculative-decoding work is not safe to run autonomously: T4, T5, Hy3 confirmation, MI210/GPU-drafter smoke tests, and any future production-kernel promotion require operator-approved bench windows, no-concurrent-inference discipline, and measurement protocol IDs.

## Progress Checklist

- [x] Missing active handoff path restored as a compatibility pointer, without duplicating operator-gated benchmark tasks. ✅ 2026-07-11
- [x] Pointer retained deliberately after closeout audit; current work remains owned by the MTP refresh handoff. ✅ 2026-07-11

## Reporting Instructions

Do not add new speculative-decoding tasks here. Update [speculative-decoding-mtp-refresh.md](../active/speculative-decoding-mtp-refresh.md) for active MTP work, the completed historical handoffs for retrospective evidence, and the inference-research chapter for user-facing conceptual documentation.
