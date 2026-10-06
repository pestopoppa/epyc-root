# 2026-10-06 Wrap-up — workspace-ec

## Summary

Clerical wrap-up: added four groups of operator-approved tasks (10 total) to active handoffs, covering YaRN inertness research, copy-spec evaluation, belief-substrate adapters, and GPU serving backlog. Applied index state validation (`--check` exit 0). Ratified token-efficiency rules (e17a0cbdc) and FIFO region-lock review (d48b6b79 CHANGES-REQUESTED → APPROVED).

## Tasks added

1. **yarn-context-extension-research.md** (3 tasks):
   - YARN-INERT-PRIORART: prior-art audit to confirm YaRN SOTA and how other stacks avoid native-window regression
   - YARN-MSCALE-AB: 3-arm greedy A/B on mscale-neutral YaRN (no-YaRN / static / attn-factor-cancelled) on `llama.cpp-experimental/yarn-mscale-20261006`
   - YARN-OPTION-D-DECISION: decide between length-routed second server (D) and in-process per-request YaRN (A) after audit and mscale A/B

2. **speculative-decoding-mtp-refresh.md** (4 tasks):
   - COPYSPEC-P1: copy/prompt-lookup speculation re-evaluation, phase 1+2 full-host window
   - COPYSPEC-WIDTH: per-impl n_max change for v11 champion (never production)
   - COPYSPEC-27B: GPU 27B leg (ngram + DFlash2) after AK GPU run 2 frees MI210
   - COPYSPEC-RECIPE: on v11 promotion, update canonical :8070/:8083 recipes

3. **vidya-belief-substrate-program.md** (1 task):
   - VB-COPYSPEC: adapter for copy-spec results; re-grade 2026-07-30 ngram retraction scope (measured non-copy prompts only)

4. **gpu-serving-tie-in-program.md** (2 tasks):
   - KVU-16g: first-prompt TTFT cost attribution on GPU slot
   - YARN-E1-MEM: attribute +15 GiB KFD overshoot from long-prefill E1 arms

## Key artifacts and status notes

- **FIFO region-lock review (d48b6b79)**: CHANGES-REQUESTED → APPROVED. Default-off, deterministic control required before default-on.
- **YaRN inert design study** (OPTIONS.md in `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/`): root cause is mscale 1.0693 → 1.143× logit sharpening at all positions; cparams bug.
- **Copy-spec survey and plan**: phase 1 arms P / ngram-mod(n-min 4)+MTP / ngram-only / P2 on production-shaped prompt set.
- **GPU run-2 parking protocol** with workspace-89: `AK_GPU_RUN2_READY` / `AK_GPU_RUN2_PARKED` flags coordinate MI210 availability.
- **Token rules ratified (e17a0cbdc)**: codified recipes + canonical baseline protocol.

## Index validation

✅ `python3 scripts/handoffs/index_state.py --check` exit 0

