# Speculative-Decoding / MTP Refresh

**Status**: active (created 2026-06-22 via operator-directed MTP review; v6 status correction added 2026-07-11)
**Categories**: speculative_decoding, hardware_optimization, local_inference, moe_optimization
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md)
**Related**: [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md), [`summary-token-attention-readiness.md`](summary-token-attention-readiness.md); completed: [`gemma4-mtp-drafter-evaluation.md`](../completed/gemma4-mtp-drafter-evaluation.md), [`mtp-speculative-decoding.md`](../completed/mtp-speculative-decoding.md)

## Objective

Decide whether to adopt new MTP (multi-token-prediction) speculative decoding for stack models, given that upstream shipped native MTP heads (Qwen3.6/3.5) + mainline llama.cpp MTP/EAGLE support in spring 2026 while our fork has none of it. **All numbers here are OBSERVATIONS (MEASUREMENT.md) — none gate a keep/deploy decision; the operator runs all benches.**

## Current State Correction (2026-07-11)

- Production has moved past the June v5/ik split. Current production is the single `production-consolidated-v6` llama.cpp tree: upstream native MTP/NEXTN speculative decoding + EPYC CPU forward-ports + iqk AVX-512 GEMM kernels. `ik_llama.cpp` is deprecated as a separate production binary.
- The June dense-Gemma measurements below remain useful observations, but future benches/deploy decisions must use the v6 native flag surface (`--spec-type draft-mtp`, `--spec-draft-n-max`) or a fresh `llama.cpp-experimental` v7-candidate started from current production. Do not revive the separate ik runtime except to reproduce historical results.
- `worker_general` Gemma4-26B-A4B still uses Google's official assistant head; the architecture question is no longer "mainline vs ik" but draft depth / sampling / quality under v6 and, for future Qwen work, whether the remaining MTP port belongs in `llama.cpp-experimental`.

## Historical State (verified 2026-06-22; superseded by v6 cutover)

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
| **gemma-4-26B-A4B (worker_general)** | MoE A4B | mainline/v6 native gemma4 MTP (#23398 lineage) | **not stale on head; v6-native now** | our head = official; production now uses the consolidated v6 native MTP path, not the separate ik fork. Cheap open check remains `draft_max` / `--spec-draft-n-max` 2→3→4 sweep under operator-approved bench conditions. |

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

### Promotion decision (DATA-DRIVEN, 2026-06-22): do NOT promote gemma-4-31B — Pareto-dominated
We already HAVE the quality benchmarks (`epyc-inference-research/benchmarks/results/reviews/summary.csv`), and MTP is distribution-lossless so the MTP-variant's measured score is the deploy-relevant number. Verdict: gemma-4-31B wins **no** quality×speed frontier vs current incumbents:

| | gemma-4-31B MTP | Qwen3.5-122B (architect) | Qwen3.6-35B (frontdoor) | gemma-4-26B-A4B (worker) |
|---|---|---|---|---|
| quality | 90% (164/183) | 93% (196/210) | 94% | 90% + 96% tool |
| agentic | 23/30 | 30/30 | — | — |
| long_context | none measured | 24/27 | 27/27 | — |
| speed (MTP) | 26–32 t/s | 12.3 | 24.3 | 44.7 |

- vs **architect** Qwen3.5-122B (93%, 12.3 t/s, no-MTP — GDN hybrid): **NOT domination — a trade-off.** gemma-4-31B is **2–2.6× FASTER** (26–32 vs 12.3) but −3pp overall, **agentic 23 vs 30**, and **no long-context data**. For the accuracy-critical, long-context architect role the 122B's quality+long-context win **by default**; but if architect *throughput* ever becomes the bottleneck, a "fast architect" swap is a legitimate operator trade (gate: measure gemma-4-31B long-context first + accept the agentic gap).
- vs **frontdoor/coder** Qwen3.6-35B (94%, 24.3 t/s): roughly iso-speed, −4pp quality. No win.
- vs **worker** gemma-4-26B-A4B (90%, MTP): **THIS is the real domination.** Same 90% quality, but the A4B MoE is **structurally faster** — it reads ~3.8B active params/token vs gemma-4-31B's 31B dense, so on BW-bound CPU it wins the quality×speed frontier (~44.7 vs 26–32 t/s) regardless of exact numbers. The smaller gemma-4 *MoE* dominates the bigger gemma-4 *dense*.

**Conclusion (corrected)**: gemma-4-31B is **Pareto-dominated specifically by the gemma-4-26B-A4B MoE worker** (equal quality, structurally faster) — NOT by the 122B, which it is 2–2.6× faster than. So it has no *general-purpose* niche. The one open door is a deliberate "fast architect" quality↓/speed↑ trade vs the 122B (operator's call; needs a long-context measurement first). The MTP work's lasting value is **validating dense-CPU-MTP (2.5–3.2×)**, justifying the Qwen3.5-9B dense path (T3). (Sources: progress 2026-05-06/08; summary.csv:18 gemma-4-31B-MTP, :19 gemma-4-26B-A4B, :131 Qwen3.5-122B. The old summary.csv 4.7 t/s for gemma-4-31B-MTP was stale/contended — superseded by the clean 26–32 t/s, 2026-06-22.)

### ⚠ Eval-resolution caveat behind the "A4B ties dense-31B" finding (2026-06-22)

The promotion decision rests on "gemma-4-31B (31B dense) and gemma-4-26B-A4B (~3.8B active MoE) both score ~90%." Operator flagged this as suspicious ("how can an A4B *match* the dense 31B of its own family?"). Investigated publicly — **verdict: benchmark saturation, NOT a dense-Q4 quantization penalty**:

- **Quantization ruled out**: public dense-Q4 gemma-4-31B evals (e.g. SuperGemma-4-31B dense-Q4 ≈ 92%) land *above* our 90%, so Q4_K_M is not crippling the dense model. The dense 31B is genuinely the stronger model: ~1–3 pp better on standard suites and **~8–10 pp better on frontier/agentic suites our bench does not contain**.
- **Root cause = our quality suites are saturated** (90–94% band, near ceiling). When two models both sit near a suite's ceiling, the suite **cannot resolve** their true gap — so a structurally-stronger dense 31B and a cheaper A4B MoE *appear* tied. The tie is a **resolution artifact of the instrument**, not real quality parity (same failure family as [[feedback_per_suite_gate_resolution_artifact]] — quantized scores hiding real differences).
- **Consequence for THIS decision**: the Pareto-domination call (worker A4B over dense 31B) is **safe for the worker/general role** (where ~90% suffices and speed dominates), but it should **not** be read as "A4B = 31B in capability." For accuracy-critical / frontier-agentic roles the dense 31B's real edge would show — which is exactly why the "fast architect" door above stays open pending a *harder* eval.
- **Operator-review candidate (NOT acted on here — eval trust boundary is human-amendment-only)**: our review suite needs a frontier/harder tier to resolve top-of-stack models; this is the eval-tower **EV-9 / DRACO** concern (intake-713). **Now recorded in the owning handoff** — [`eval-tower-verification.md`](eval-tower-verification.md) "Research Intake Update — 2026-06-23 / EV-9 saturation: empirical instance" — as a standing-audit + frontier-tier candidate. Scoring untouched.
- [ ] **T2 (WS5 port) — finish the Qwen MTP kernel port** in `llama.cpp-experimental` (branch `feature/mtp-qwen36-port`). #22400 DONE (commit b139eba138); remaining = reconcile **PR #22673** (25 conflicted files). **Full context + conflict map + task breakdown: [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md).** Gated behind T1 (don't invest until dense MTP proves out on CPU).
- [x] **T3 — Qwen3.5-9B dense MTP: FUNCTIONALLY VERIFIED 2026-06-22** (via fresh-upstream build, since the #22673 cherry-pick into our fork is infeasible). `unsloth/Qwen3.5-9B-MTP-GGUF` Q4_K_M (5.47 GB) downloaded; ran on `llama.cpp-experimental/build-upstream` (`origin/master`, branch `upstream-mtp-verify`): **baseline 14.90 → MTP (`--spec-type draft-mtp --spec-draft-n-max 3`) 29.30 t/s = 1.97×, 87% draft accept (184/211), correct output.** Confirms the dense-CPU-MTP thesis on a second (non-gemma) dense model. **CAVEAT**: upstream-master kernels (no our-fork NUMA/CPU opts) → the *multiplier* is the verified quantity, not the absolute t/s; deploy decision = fresh-upstream (loses our kernels) vs reimplement-in-fork. Full detail + reproduce cmd: [`qwen-mtp-llamacpp-port.md`](qwen-mtp-llamacpp-port.md) ✅ section.
- [ ] **T4 (after T2 binary, low EV) — gate-bench Qwen3.6-35B-A3B** (Block C) for frontdoor/coder; mind the Q8(prod)-vs-Q4(MTP-GGUF) quant-parity caveat + MoE-on-CPU skepticism.
- [ ] **T5 (cheap) — gemma-4-26B-A4B `draft_max` 2→3→4 sweep** on the existing worker (mainline default uses 3-4; we run 2).

## Dependency graph
- T1, T5 → **independent, runnable now only with operator bench approval**. The June reproduction path used the existing ik_llama fork; July+ work should prefer `production-consolidated-v6` / a fresh `llama.cpp-experimental` v7-candidate unless deliberately reproducing historical ik results.
- T3, T4 → blocked-by **T2** (need the `draft-mtp` experimental binary) + GGUF downloads.
- **T2 remaining (#22673)** conflicts in 25 files — core: `common/speculative.cpp` (+1980), `common/speculative.h`, `common/arg.cpp` (the `--spec-type draft-mtp` enum), `common/common.{cpp,h}`, `include/llama.h`, `src/llama-context.cpp`, `src/models/qwen35.cpp`, `src/models/qwen35moe.cpp`, `conversion/{base,qwen}.py`, + ~15 more. Root cause: our fork's spec-dec is an **older API generation** (carries our EAGLE3 stub + tree/DySpec + ngram + gemma4 paths) than the PR base. Real work = hand-merge `speculative.cpp` preserving our existing paths, then compile-iterate. **Empirically a focused multi-session reconciliation, NOT 2-4 weeks of catastrophe and NOT a 5-min cherry-pick.**

## Cross-cutting concerns
- **CPU+MoE is the binding question**: every upstream MTP/EAGLE speedup is GPU; MoE shows ≤1.06× even on GPU (expert-union verification overhead). Dense is where CPU MTP can win — hence T1/T3 before T4. The single gating number = CPU MTP α/throughput on a dense model-we-own (T1).
- **MTP parallelism must be verified per runtime**: the June ik path asserted on `-np>1`; v6 native MTP must still be checked per role because speculative decoding can trade off against 4×-quarter concurrent splits. Confirm per role before deploy.
- **NEVER touch production `/mnt/raid0/llm/llama.cpp`** — all port work in `llama.cpp-experimental` (verify_llama_cpp.sh enforces). Promotion means a new production version after positive operator bench + quality pass, never patching v6 in place.
- Quant parity: Qwen3.6 prod = Q8; MTP-GGUF = Q4 → compare C1(Q4+MTP) vs C0(Q4 no-MTP), not vs Q8 prod.
- **Draft-head is a small BW slice** (corroborated by FR-Spec vocab-trim, intake-740): trimming the draft LM-head −85% in kernel time yields only +1-3% end-to-end on bandwidth-bound decode — reinforcing that expert-verification overhead, not draft quality, is the CPU wall.

## Watch-items (deferred)
- **EAGLE-3** (mainline PR #18039) — deferred to the **MI210 GPU (~July 2026)** per operator; our fork's EAGLE3 is a stub. **Trigger now due (2026-07-02): the MI210 has landed** — and DeepSpec (intake-737) is an MIT EAGLE-3 training/eval framework, so this watch is actionable once GPU-side spec-dec work opens.
- **DSpark semi-AR draft head** (intake-738) — candidate future MTP-drafter alternative; deferred like EAGLE-3. Needs DeepSpec-pipeline training (MI210) + a GGUF port, then **measure α vs our native MTP before any investment** (per `feedback_measure_alpha_before_specdec_investment`); note gemma4 native MTP is already ~76.9% saturated → low headroom.
- **DFlash O(1)-drafting (intake-158 / deep-dive `dflash-dart-diffusion-speculation.md`) — promoted from "not-viable comparison" to explicit MI210 candidate (2026-07-03 intake sweep)**: DFlash was previously cited here only as the "same deployment wall" (CPU/GGUF-blocked). That wall was a *CPU* wall — on the MI210 the recurrent/diffusion draft path runs on GPU (parallel scan; verification bottleneck disappears — the same reason `gpu-acceleration-path.md` revives DFlash/DDTree). Two forks: (a) the deep-dive's Action-A O(1)-drafting port, and (b) the lucebox `llama.cpp-dflash-ggml` tree HIP re-scoped for gfx90a (currently CUDA-pinned). **Still α-gated**: measure acceptance vs native MTP first (G0 log read gives the baseline for free); our own DFlash C++ forward pass is already verified correct to <0.01, so the algorithm was never the blocker. [unverified] that the reference kernels build on ROCm.
- **Qwen3-Next MTP** — re-measure trigger only if a *merged* `qwen3next` MTP path with a positive CPU speedup appears.

## Operator bench commands

See WS4 prep for the historical June commands. **Block A (gemma-4-31B dense)** was run on `/mnt/raid0/llm/ik_llama.cpp/build/bin/llama-speculative` (branch `production-gemma4-mtp`) using ik-era flags (`-mtp --spec-type mtp --draft-max`). For July+ measurements, translate to the v6/native surface (`--spec-type draft-mtp`, `--spec-draft-n-max`) on `production-consolidated-v6` or a fresh `llama.cpp-experimental` v7-candidate, preserve the same operator-approved quiescing / CPU pinning / seed protocol, and record protocol IDs per `MEASUREMENT.md`. Blocks B/C use the experimental `draft-mtp` binary after download. (Full blocks were produced in the session WS4 report.)

## Research context (intake)

| Intake | Item | Verdict |
|---|---|---|
| intake-721 | unsloth/Qwen3.6-35B-A3B-MTP-GGUF | worth_investigating |
| intake-722 | unsloth/Qwen3.5-122B-A10B-MTP-GGUF | not_applicable (hybrid wall) |
| intake-723 | unsloth/Qwen3.5-9B-MTP-GGUF | worth_investigating |
| intake-724 | google/gemma-4-31B-it-assistant | adopt_component (on disk) |
| intake-725 | llama.cpp/ik_llama MTP+EAGLE3 support (PRs #22673/#22400/#23398/#18039, ik #1744) | adopt_patterns |
| intake-737 | DeepSeek DeepSpec — MIT draft-model train/eval framework (DSpark/DFlash/EAGLE-3; Qwen3 + gemma-4-12B-it ckpts) | worth_investigating (checkpoints) / n/a (8-GPU framework, no CPU/GGUF path) |
| intake-738 | DSpark semi-AR drafter (parallel backbone + 1-token correction head) | adopt_patterns — transferable draft head (needs training + GGUF port); scheduler CPU-inert (→ moe-spec); vendor-unreproduced |
| intake-740 | FR-Spec draft-vocab trim for native MTP (llama.cpp #25187, `avifenesh@047bfa508`) | worth_investigating — lossless@temp0, −85% draft-head kernel → +1-3% e2e; impl → qwen-mtp-llamacpp-port.md P7 |
| intake-742 | Graft — training-free prune-then-graft draft tree (arXiv 2605.20104) | adopt_patterns (catalog → moe-spec); EAGLE-3-based + GPU adjacency |

## Reporting instructions
After any task: update the checkbox here + record measured numbers (with protocol-id per MEASUREMENT.md) in the owning artifact (registry entry `gemma4_31b_q4km_mtp` for T1; this handoff for T2 port status). Any promotion requires a fresh experimental candidate, positive operator bench, and quality pass — never auto-promote and never patch frozen production in place.

## Key file locations
- Port branch: `/mnt/raid0/llm/llama.cpp-experimental` `feature/mtp-qwen36-port` (#22400 @ b139eba138; #22673 remaining)
- gemma MTP runtime: current production uses `/mnt/raid0/llm/llama.cpp` `production-consolidated-v6` native MTP; `/mnt/raid0/llm/ik_llama.cpp` `production-gemma4-mtp` is historical/reproduction-only
- Models on disk: `/mnt/raid0/llm/models/gemma-4-31B-it-Q4_K_M.gguf` (+ `-assistant-Q8_0.gguf`); `/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-9B-GGUF/`
- Registry entries: `gemma4_31b_q4km_mtp` (research registry, Tier B); worker_general (lean registry)
- Read-only refs: `autopilot/program.md:325` (Qwen3.5 hybrid exhausted), `scripts/session/verify_llama_cpp.sh`

## Research Intake Update — 2026-07-02

### New Related Research
- **[intake-751 / intake-752] "Nemotron-Labs-TwoTower: Diffusion LM with Pretrained Autoregressive Context"** (arXiv 2606.26493 + HF weights; NVIDIA — Reda, Kamalu, Waleffe, Patwary, Shoeybi, Catanzaro)
  - **Relevance:** A parallel-decode approach that **competes with / contrasts against** our MTP/NEXTN refresh. It decouples a **FROZEN autoregressive context tower** from a **trainable diffusion denoiser tower** (cross-attention), emitting up to 16 tokens/step via confidence-based block denoising. Built on Nemotron-3-Nano-30B-A3B (Mamba-2/attention/MoE hybrid, ~3B active).
  - **Reported results:** **2.42× wall-clock generation throughput at 98.7% quality retention** (self-reported, GPU-only).
  - **Key idea worth stealing:** the two-tower "**freeze the pretrained AR backbone, train only a bolt-on parallel generator**" factorization is directly adjacent to how we train MTP/NEXTN heads on a frozen base — a candidate design lens for a parallel head on our frozen CPU models.
  - **Delta from current approach / why worth_investigating not new_opportunity:** it is **diffusion-based and GPU-only** (BF16, dual H100/A100) with **no CPU/GGUF path**, and the Nemotron Mamba2-hybrid-MoE backbone has documented llama.cpp CPU blockers — same deployment wall as DFlash (intake-158). Distinct from the already-indexed Nemotron-Labs-Diffusion tri-mode (intake-576). **Creative-use:** re-evaluate on the MI210/DGX-Spark GPU path if a diffusion-serving backend lands; the backbone is also a standing SSM-hybrid worker/drafter candidate independent of the diffusion tower.

## Research Intake Update — 2026-07-11

### New Related Research
- **[intake-798] "The Gemma Challenge and the Case for Agent Collabs"** (HF blog; HF + Google DeepMind)
  - Relevance: a 6-day agent collaboration optimizing **gemma-4-E4B MTP** inference — the same MTP-drafter family as our production `worker_general` (gemma-4-26B-A4B, Google assistant head). Surfaces one concrete, directly-applicable drafter technique.
  - Key technique — **`onegraph` (fastest *lossless* submission, 315 TPS, downstream-quality-preserving):** the Gemma MTP drafter is **Q-only, KV-shared, with no cross-position dependencies**, so the usual multi-position drafter **warm-up pass is unnecessary** — only the single position that starts the drafting loop is needed, and that step is equivalent to a normal loop iteration. They **fold the warm-up into the 7-step drafting loop, record the entire routine as ONE GPU graph, and replay it with a single launch** — turning a bookkeeping-heavy sequence into a uniform GPU-side routine with no output change.
  - Delta from our approach: this is a **GPU-graph-capture** optimization (relevant to the MI210 GPU-drafter path — see `gpu-drafter-mi200-investigation.md` — not the CPU regime). The *insight* (drafter warm-up is redundant given Q-only/KV-shared/no-cross-position structure) is worth checking against our gemma4 assistant-head drafter loop regardless of backend: if our warm-up does redundant multi-position work, the folding may shave latency on CPU too (verify the structural preconditions hold for our GGUF drafter).
  - **✅ Structural check COMPLETE (2026-07-11)**: all 3 preconditions (Q-only, KV-shared, no cross-position deps) verified against `experimental-v7-candidate` code. HIP graph capture infrastructure is already present (no port needed). See `gemma-challenge-kernel-techniques-v7.md` for details. Next: MI210 smoke-test + benchmark.
  - Contrast — **fastest *lossy* (491.8 TPS)** used vocab pruning + layer removal + a task-targeted fine-tuned drafter + CUDA-graph capture, but degraded GPQA-Diamond/MMLU-Pro by 15/40 points → a cautionary example of exactly the accept-rate-vs-quality trap this handoff's per-model table already guards against.
  - Numbers are OBSERVATION-grade (challenge-internal, GPU, self-reported).
