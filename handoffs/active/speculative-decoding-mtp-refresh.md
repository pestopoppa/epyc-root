# Speculative-Decoding / MTP Refresh

**Status**: active (created 2026-06-22 via operator-directed MTP review)
**Categories**: speculative_decoding, hardware_optimization, local_inference, moe_optimization
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md), [`summary-token-attention-readiness.md`](summary-token-attention-readiness.md); completed: [`gemma4-mtp-drafter-evaluation.md`](../completed/gemma4-mtp-drafter-evaluation.md), [`mtp-speculative-decoding.md`](../completed/mtp-speculative-decoding.md)

## Objective

Decide whether to adopt new MTP (multi-token-prediction) speculative decoding for stack models, given that upstream shipped native MTP heads (Qwen3.6/3.5) + mainline llama.cpp MTP/EAGLE support in spring 2026 while our fork has none of it. **All numbers here are OBSERVATIONS (MEASUREMENT.md) — none gate a keep/deploy decision; the operator runs all benches.**

## Current State (verified 2026-06-22)

- Our fork `production-consolidated-v5` (HEAD a6c793fc66): `--spec-type` = ngram-only; **no `draft-mtp`**; EAGLE3 is an inert `// TODO PR-18039` stub. Qwen3.6/3.5 MTP heads are NOT runnable here.
- gemma-4-26B-A4B (worker_general) MTP runs on a **separate** clone `/mnt/raid0/llm/ik_llama.cpp` branch `production-gemma4-mtp` (patched PR #1744), NOT the consolidated fork.
- The worker drafter `gemma-4-26B-A4B-it-assistant-Q8_0.gguf` is **Google's official assistant head** (verified GGUF metadata: `general.architecture=gemma4_mtp`, `Gemma4AssistantForCausalLM`, Apache-2.0), GGUF-quantized in-house — registry wording corrected this session.

## Per-model verdict table

| Model / role | Arch | New upstream | Verdict | Why |
|---|---|---|---|---|
| **gemma-4-31B (DENSE, not deployed; on disk)** | dense | official `gemma-4-31B-it-assistant` head (491 MB, **on disk**) | **PRIMARY candidate — gate-bench now (no port)** | dense = best CPU-MTP case; prior directional **2.98× (7.05→21.02 t/s, 84.3% accept), Tier-B, quality-UNVERIFIED, single-run** — re-bench r≥3 + quality. Runs on existing ik_llama `production-gemma4-mtp`. |
| **Qwen3.5-9B (DENSE, not deployed; on disk Q4/Q6/Q8)** | dense | `unsloth/Qwen3.5-9B-MTP-GGUF` | **worth_investigating (2nd dense gate)** | pure dense; needs WS5 binary + GGUF download |
| **Qwen3.6-35B-A3B (frontdoor + coder_escalation)** | MoE A3B | native NEXTN/MTP head; `unsloth/Qwen3.6-35B-A3B-MTP-GGUF`; mainline PR #22673 | **worth_investigating, low EV** | unblocks 2 roles BUT pure-MoE-A3B = worst CPU-MTP case (26B-A4B MoE measured only 1.06×); needs the hard WS5 port |
| **Qwen3.5-122B-A10B (architect)** | GDN hybrid | `unsloth/Qwen3.5-122B-A10B-MTP-GGUF` | **DEAD — do not pursue** | `autopilot/program.md:325`: MTP-1 already measured **0.56×** (net slowdown); 75% Delta-Net recurrent layers don't batch. Architecture, NOT NUMA (architect is already single-instance serial). |
| **Qwen3.5-27B (DENSE? no — HYBRID; on disk)** | SSM-Dense hybrid | `unsloth/Qwen3.5-27B-MTP-GGUF` | **DEAD — hybrid trap** | same Delta-Net wall; closed NOT VIABLE in `mtp-speculative-decoding.md`. (User listed it as dense — it is not.) |
| **Qwen3-Next-80B (ingest)** | SSM-MoE hybrid | native MTP (GPU/vLLM only) | **not viable on CPU** | only GGUF attempt (quivent) = net-negative 0.43×; verification wall holds |
| **gemma-4-26B-A4B (worker_general)** | MoE A4B | mainline gemma4 MTP (#23398) | **not stale on head** | our head = official; mainline now an alt to the ik_llama fork; cheap check = `draft_max` 2→3→4 sweep |

## Outstanding Tasks (priority order)

- [ ] **T1 (READY now, no port) — gate-bench gemma-4-31B DENSE** on ik_llama `production-gemma4-mtp` (Block A below); re-confirm ~3× under r≥3 + noise bracket, then the quality (Leviathan byte-exact) suite. Operator-run. Decision: promote `gemma4_31b_q4km_mtp` past Tier B only if speed win survives noise AND quality passes.
- [ ] **T2 (WS5 port) — finish the Qwen MTP kernel port** in `llama.cpp-experimental` (branch `feature/mtp-qwen36-port`). #22400 DONE (commit b139eba138); remaining = reconcile **PR #22673** (25 conflicted files, see Dependency Graph). Then build (`-DGGML_CUDA=OFF`) and verify `--spec-type draft-mtp`.
- [ ] **T3 (after T2 binary) — gate-bench Qwen3.5-9B dense** (Block B) — the cleanest non-gemma dense CPU-MTP datapoint. Download `unsloth/Qwen3.5-9B-MTP-GGUF` first.
- [ ] **T4 (after T2 binary, low EV) — gate-bench Qwen3.6-35B-A3B** (Block C) for frontdoor/coder; mind the Q8(prod)-vs-Q4(MTP-GGUF) quant-parity caveat + MoE-on-CPU skepticism.
- [ ] **T5 (cheap) — gemma-4-26B-A4B `draft_max` 2→3→4 sweep** on the existing worker (mainline default uses 3-4; we run 2).

## Dependency graph
- T1, T5 → **independent, runnable now** (existing ik_llama fork; files on disk).
- T3, T4 → blocked-by **T2** (need the `draft-mtp` experimental binary) + GGUF downloads.
- **T2 remaining (#22673)** conflicts in 25 files — core: `common/speculative.cpp` (+1980), `common/speculative.h`, `common/arg.cpp` (the `--spec-type draft-mtp` enum), `common/common.{cpp,h}`, `include/llama.h`, `src/llama-context.cpp`, `src/models/qwen35.cpp`, `src/models/qwen35moe.cpp`, `conversion/{base,qwen}.py`, + ~15 more. Root cause: our fork's spec-dec is an **older API generation** (carries our EAGLE3 stub + tree/DySpec + ngram + gemma4 paths) than the PR base. Real work = hand-merge `speculative.cpp` preserving our existing paths, then compile-iterate. **Empirically a focused multi-session reconciliation, NOT 2-4 weeks of catastrophe and NOT a 5-min cherry-pick.**

## Cross-cutting concerns
- **CPU+MoE is the binding question**: every upstream MTP/EAGLE speedup is GPU; MoE shows ≤1.06× even on GPU (expert-union verification overhead). Dense is where CPU MTP can win — hence T1/T3 before T4. The single gating number = CPU MTP α/throughput on a dense model-we-own (T1).
- **MTP requires `-np 1`** (ik_llama PR #1744 asserts on `-np>1`); does NOT break NUMA for single-stream roles (architect/worker-full are already `-np 1`), but trades off against the 4×-quarter concurrent-split for roles that use it. Confirm per role before deploy.
- **NEVER touch production `/mnt/raid0/llm/llama.cpp`** — all port work in `llama.cpp-experimental` (verify_llama_cpp.sh enforces). Promotion to v5 is gated on a positive operator bench.
- Quant parity: Qwen3.6 prod = Q8; MTP-GGUF = Q4 → compare C1(Q4+MTP) vs C0(Q4 no-MTP), not vs Q8 prod.

## Watch-items (deferred)
- **EAGLE-3** (mainline PR #18039) — deferred to the **MI210 GPU (~July 2026)** per operator; our fork's EAGLE3 is a stub.
- **Qwen3-Next MTP** — re-measure trigger only if a *merged* `qwen3next` MTP path with a positive CPU speedup appears.

## Operator bench commands

See WS4 prep (this session). **Block A (gemma-4-31B dense) is runnable today** on `/mnt/raid0/llm/ik_llama.cpp/build/bin/llama-speculative` (branch `production-gemma4-mtp`): baseline `-no-mtp --spec-type none` vs MTP `-md gemma-4-31B-it-assistant-Q8_0.gguf -mtp --spec-type mtp --draft-max {2,3,4} --draft-p-min 0.0`, with `taskset -c 0-95 numactl --interleave=all`, the OMP stack + `KMP_BLOCKTIME=10`, `-t 96 -fa 1 --no-mmap -c 16384 -ub 512 -ctk q8_0 -ctv q8_0 --temp 0 --seed 42 -n 128`, 3 reps; read tg t/s + acceptance; `llama-bench` cannot drive MTP. Blocks B/C use the WS5 `llama.cpp-experimental` binary `--spec-type draft-mtp` after download. (Full blocks were produced in the session WS4 report.)

## Research context (intake)

| Intake | Item | Verdict |
|---|---|---|
| intake-721 | unsloth/Qwen3.6-35B-A3B-MTP-GGUF | worth_investigating |
| intake-722 | unsloth/Qwen3.5-122B-A10B-MTP-GGUF | not_applicable (hybrid wall) |
| intake-723 | unsloth/Qwen3.5-9B-MTP-GGUF | worth_investigating |
| intake-724 | google/gemma-4-31B-it-assistant | adopt_component (on disk) |
| intake-725 | llama.cpp/ik_llama MTP+EAGLE3 support (PRs #22673/#22400/#23398/#18039, ik #1744) | adopt_patterns |

## Reporting instructions
After any task: update the checkbox here + record measured numbers (with protocol-id per MEASUREMENT.md) in the owning artifact (registry entry `gemma4_31b_q4km_mtp` for T1; this handoff for T2 port status). Promotion to production-consolidated-v5 requires a positive operator bench + quality pass — never auto-promote.

## Key file locations
- Port branch: `/mnt/raid0/llm/llama.cpp-experimental` `feature/mtp-qwen36-port` (#22400 @ b139eba138; #22673 remaining)
- gemma MTP runtime: `/mnt/raid0/llm/ik_llama.cpp` `production-gemma4-mtp` → `build/bin/llama-speculative`
- Models on disk: `/mnt/raid0/llm/models/gemma-4-31B-it-Q4_K_M.gguf` (+ `-assistant-Q8_0.gguf`); `/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-9B-GGUF/`
- Registry entries: `gemma4_31b_q4km_mtp` (research registry, Tier B); worker_general (lean registry)
- Read-only refs: `autopilot/program.md:325` (Qwen3.5 hybrid exhausted), `scripts/session/verify_llama_cpp.sh`
