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

- [x] **T1 — gate-bench gemma-4-31B DENSE: DONE 2026-06-22 (host quiesced).** Result **~1.84× at draft_max=3** (see Results below). Speed win confirmed + survives noise; **corrects the prior single-run ~2.98× to ~1.84×**. Remaining for Tier-B promotion: multi-prompt reps + the quality (Leviathan byte-exact) suite + acceptance-rate capture. Operator decision: promote `gemma4_31b_q4km_mtp` only after the quality pass.

## Results — gemma-4-31B dense MTP gate-bench (2026-06-22)

**Protocol** (clean directional measurement, NOT a full canonical gate): host quiesced (full stack stopped via `orchestrator_stack.py stop --all`); ik_llama.cpp `production-gemma4-mtp` `llama-server` + `/completion`; target `gemma-4-31B-it-Q4_K_M` + official `gemma-4-31B-it-assistant-Q8_0`; `taskset -c 0-95 numactl --interleave=all`, `-t 96 -fa 1 --no-mmap -c 16384 -ub 512 -ctk q8_0 -ctv q8_0`, OMP stack + `KMP_BLOCKTIME=10`; `n_predict=128, temp=0, seed=42, cache_prompt=false`; 1 warmup + 2 measured reps; single prompt.

| config | t/s (r1, r2) | median | speedup |
|---|---|---|---|
| baseline (no MTP) | 9.17 / 9.11 | 9.14 | 1.00× |
| MTP draft-max 2 | 15.95 / 16.00 | 15.98 | 1.75× |
| **MTP draft-max 3** | 16.83 / 16.75 | **16.79** | **1.84×** |
| MTP draft-max 4 | 16.02 / 16.38 | 16.20 | 1.77× |

**Findings**: dense gemma-4-31B CPU MTP gives a **real ~1.84×** (draft_max=3 optimal; 3 > 4 > 2) — confirming the dense thesis vs MoE's ~1.06×. The prior `gemma4-mtp-drafter-evaluation` 2.98× (7.05→21.02, single-run) does **not** reproduce on a clean host: clean baseline is higher (9.14 vs 7.05) and MTP lower (16.8 vs 21.0), so realized speedup is ~1.84×, not ~3×. Acceptance rate was NOT captured (the `/completion` timings JSON didn't expose draft_n/accepted under the probed keys — needs the server spec-stats path or `llama-speculative`, which currently SIGABRTs on this fork's gemma4-MTP path → use server). Numbers are a clean measurement but single-prompt/r=2 — a Tier-B gate still needs multi-prompt reps + quality byte-exactness.

**Implication for the port (T2)**: a ~1.84× dense win justifies finishing the #22673 Qwen MTP port to test dense **Qwen3.5-9B** (T3) — but it does **not** rescue the MoE cases (Qwen3.6-A3B), where the wall is expert-verification overhead, not draft quality.

### Hard-T2 verification + quality (2026-06-22, host quiesced)

Re-ran on two substantive checkable tasks (n=384, temp=0, seed=42), capturing output text + diffing baseline vs MTP:

| task | baseline t/s | MTP (dm=3) t/s | speedup | output correct? | MTP==baseline? |
|---|---|---|---|---|---|
| P1 Manacher's algorithm (Python) | 10.21 | **26.01** | **2.55×** | ✅ valid O(n) Manacher's | ✗ differs (valid alt impl) |
| P2 primes<100 + sum | 10.24 | **32.68** | **3.19×** | ✅ exact (25 primes, sum 1060) | ✅ byte-identical |

**The 16.8 t/s was not variance — on real structured/code output MTP is *faster* (26–32 t/s), because predictable tokens (code, `2, 3, 5, 7…`) draft at very high acceptance** (generic prose accepts less, hence the lower 1.84× there). Baseline dense 31B ≈ 10 t/s; MTP 26–32 t/s.

**Quality / losslessness (important correction)**: MTP output is **correct and sensible** (P2 exact answer; P1 valid Manacher's), but it is **distribution-lossless, NOT byte-exact greedy**. P1 diverged from sequential baseline at a near-tie comment token (“symmetry”→“mirroring”) then produced a different-but-equally-valid implementation — expected because the batched verification forward pass has different FP rounding than token-by-token decode, flipping greedy near-ties. This **supersedes the prior `gemma4-mtp-drafter-evaluation` “byte-exact under Leviathan verifier” claim** (too strong). Acceptable for chat/architect roles (output valid); do not rely on bit-determinism.

### Possible architect_general candidacy (flag, do NOT auto-promote)
gemma-4-31B dense at **26–32 t/s with valid output** is a compelling speed profile vs the current architect **Qwen3.5-122B-A10B (~12 t/s)**. BUT promotion is a **capability decision, not speed**: a 31B replacing a 122B must first win (or acceptably tie) a head-to-head **quality eval on architect-tier tasks** (the eval-tower suite) vs the 122B incumbent. Gate: run that A/B before any role swap. Speed alone is necessary, not sufficient.
- [ ] **T2 (WS5 port) — finish the Qwen MTP kernel port** in `llama.cpp-experimental` (branch `feature/mtp-qwen36-port`). #22400 DONE (commit b139eba138); remaining = reconcile **PR #22673** (25 conflicted files). **Full context + conflict map + task breakdown: [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md).** Gated behind T1 (don't invest until dense MTP proves out on CPU).
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
