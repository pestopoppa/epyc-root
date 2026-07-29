# Gemma 4 MTP-Drafter Evaluation

## Closure note (2026-06-12, Fable 5 portfolio pass)

**Final outcome**: The deploy-or-not decision this handoff existed to make was made and shipped 5 weeks ago — gemma4-26B-A4B Q4_K_M MTP is `worker_general` in production since 2026-05-08 (+18pp tool_compliance, +6pp full suite, 76.5 t/s verified solo). Key measured results: 31B Dense MTP = 2.98× pure-CPU speedup (7.05 → 21.02 t/s, 84.3% acceptance); 26B-A4B MoE MTP = 1.06× only (MoE expert-routing cancellation confirmed quantitatively) but promoted anyway on the quality lift; 1-line server-context.cpp fix pushed upstream to ik_llama.cpp PR #1744.

**Why archived**: decision made and deployed; only residual follow-ups remained, none of which need this handoff's gate machinery.

**Where residuals now live**: the 3 residuals (gemma4_31b_q4km_mtp quality bench; q-scorer `baseline_tps` refresh; R1b/R1c hybrid-MTP reopener sub-gates, parked) were extracted to [`inference-acceleration-index.md`](../active/inference-acceleration-index.md) § "Inherited from gemma4-mtp-drafter-evaluation closure (2026-06-12)". The SpecDec++ follow-on is covered by `feedback_measure_alpha_before_specdec_investment` (measure baseline α first). The launch recipe lives in `project_gemma4_mtp_launch_recipe` memory.

**Reopen triggers**: R1b/R1c sub-gates clearing (hybrid-MTP reopener — see the extracted index entry); a community llama.cpp port of Nemotron-Diff tri-mode self-speculation (the documented MTP alternative if the 31B quality bench stalls); or a new Gemma drafter release changing the variant matrix.

---

**Status**: stub — expanded 2026-05-06 with per-variant gate analysis after deep dive
**Created**: 2026-05-06 (via research intake)
**Categories**: speculative_decoding, moe_optimization, inference_serving, local_inference
**Companion deep dive**: [`research/deep-dives/gemma4-mtp-drafter-deep-dive.md`](../../research/deep-dives/gemma4-mtp-drafter-deep-dive.md)

## Objective

Decide whether Google's pre-trained MTP drafter weights for Gemma 4 are deployable on the EPYC CPU stack as a coder, architect, or worker candidate. Distinct from `completed/mtp-speculative-decoding.md` (which closed Qwen3.5 hybrid MTP-1 as NOT VIABLE) because Gemma 4 is non-hybrid — the recurrent-verify wall does not apply. **The deep dive identified that "Gemma 4 MTP" is not one mechanism** — at least two architecturally distinct drafter classes exist across the 31B Dense, 26B-A4B MoE, and E4B/E2B variants — so this stub now sequences gates per variant.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-527 | Accelerating Gemma 4: faster inference with multi-token prediction drafters (Google blog, 2026-05-05) | high | new_opportunity |
| intake-251 | Gemma 4 MLX Collection — Apple MLX Optimized Gemma 4 Models | medium | worth_investigating |
| intake-252 | Gemma 4 Official — Google DeepMind Open Model Family | medium | worth_investigating |
| intake-256 | Gemma 4 Official follow-up | medium | worth_investigating |

Closed counterpoint: `completed/mtp-speculative-decoding.md` — MTP-1 on Qwen3.5 hybrid achieved 78.5% acceptance but 0.56× throughput because Delta-Net layers force O(N) recurrent verify. Gemma 4 has no Delta-Net; result does not generalize.

## Variant matrix and G0 status (post-deep-dive, G0.1+G0.2 RESOLVED 2026-05-06)

| Variant | Type | HF drafter | Drafter shape | GGUF drafter | Standard llama.cpp | Our fork loadable? | G0 verdict |
|---------|------|------------|---------------|--------------|--------------------|--------------------|------------|
| Gemma 4 31B | Dense | `google/gemma-4-31B-it-assistant` | Gemma4Assistant (4 layers, 1024 hidden, 32/16 heads, ~500M total) | `Radamanthys11/...-GGUF` (Q8_0 515 MB, F16 955 MB) | ✗ NOT supported | requires ik_llama.cpp MTP-path port | **G0a CONDITIONAL** — port required (estimated 2-4 days, see G0.1 below) |
| Gemma 4 26B-A4B | MoE A4B | `google/gemma-4-26B-A4B-it-assistant` | Gemma4Assistant (4 layers, 1024 hidden, 16/8 heads — **same class as 31B**, narrower) | none yet | ✗ | requires GGUF conversion + same port | **G0b CONDITIONAL** — same port covers it; need GGUF conversion |
| Gemma 4 E4B | Edge multimodal | `google/gemma-4-E4B-it-assistant` (BF16) | Gemma4Assistant (4 layers, 256 hidden, 4/2 heads, 78M) | none direct; LiteRT-extraction at `SeatownSin/...` (INT4-dequant, 35% top-1 ceiling) | ✗ | requires GGUF conversion + same port | **G0c CONDITIONAL** — same port mechanism; only relevant for multimodal-pipeline track |
| Gemma 4 E2B | Edge multimodal | not yet checked | likely same class, narrower | none observed | ✗ | same path | DEFER |

**Headline G0 findings:**

1. **All three Gemma 4 drafters share one architecture class** (`Gemma4AssistantForCausalLM`, `model_type: gemma4_assistant`). Earlier framing of "31B = conventional small-LM, E4B = Q-only-shared-KV" was wrong. They differ only in width parameters. **One llama.cpp port covers all three.**
2. **GGUF exists ONLY for the 31B Dense drafter today**, and only via ik_llama.cpp. The 26B-A4B and E-series drafters need community (or in-house) GGUF conversion — but they share the architecture, so conversion is parameterized.
3. **ik_llama.cpp's MTP path is NOT Gemma-specific** — already supports GLM-4.x MoE (PR #1270, foundational, +813/-199, 16 files), Qwen 3.5 dense (PR #1698, +398/-128). Port amortizes across at least 5 model classes.
4. **Qwen 3.5 hybrid MTP is explicitly NOT supported in ik_llama.cpp** (PR #1698 says "dense models only"). **Independent third-party confirmation** of our `completed/mtp-speculative-decoding.md` 0.56× hybrid finding.
5. **PR #1724 (May 3, 2026)** added "MTP per-step checkpoints with CPU recurrent layers" — small (+40/−22, 4 files) but architecturally significant. **Potential reopener** for the closed Qwen 3.5 hybrid MTP work; needs focused diff read.

## Gate sequence (revised post-G0.1+G0.2)

### G0 — pre-bench decision (RESOLVED through G0.2)

| Gate | Action | Status | Outcome |
|------|--------|--------|---------|
| **G0.1** | Identify ik_llama.cpp MTP commits + estimate port effort | ✓ DONE 2026-05-06 | 13 PRs since 2026-02-22; foundational +813/-199 across 16 files; multi-architecture (GLM-4.x/Qwen3.5-dense/Gemma 4); estimated 2-4 days port |
| **G0.2** | Inspect 26B-A4B drafter shape | ✓ DONE 2026-05-06 | Gemma4Assistant class shared across all three Gemma 4 variants; one port covers all |
| **G0.3** | Port-vs-wait decision | preliminary | **Option (d) recommended**: build ik_llama.cpp standalone on EPYC for a directional G1 measurement BEFORE committing to a fork port |

### G0.4 — directional measurement via standalone ik_llama.cpp (EXECUTED 2026-05-06; BLOCKED)

Build ik_llama.cpp standalone, run a directional pure-CPU bench, treat as non-production answer. User-approved.

| Sub-gate | Action | Status | Outcome |
|---------|--------|--------|---------|
| G0.4a | Host-readiness checks (zombie / freq throttle / NUMA balancing / disk space) | ✓ DONE | clean: 0 inference processes; 96 cores ramp to ~3.3 GHz under synthetic load (no throttle); numa_balancing=0; 414 GB free on /mnt/raid0/llm |
| G0.4b | Locate / acquire target + drafter GGUFs | ✓ DONE | target `gemma-4-31B-it-Q4_K_M.gguf` already present (18 GB); drafter `Radamanthys11/Gemma-4-31B-it-assistant-Q8_0.gguf` (491 MB) downloaded |
| G0.4c | Clone + build ik_llama.cpp main HEAD (`b937219`, post-PR-#1741) | ✓ DONE | znver5 native, OpenMP, no CUDA; ~3 min build at -j96; binaries OK |
| G0.4c-extension | Switch to PR #1744 branch (`feat/gemma-4-mtp` at `0f728f380d`) — required because ik_llama.cpp main has no `gemma4_mtp` arch class | ✓ DONE | branch fetched (refs/pull/1744/head); rebuild ~2 min |
| G0.4d | Bench baseline (no MTP) on EPYC canonical (`taskset -c 0-95`, `numactl --interleave=all`, `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active`, `-t 96 -fa 1 --no-mmap`) | ✓ DONE | **7.05 t/s on Gemma 4 31B Q4_K_M, 128 predicted tokens, deterministic temp=0 seed=42**. Matches prior 6.85 t/s @ 2026-05-04 within 3% noise (`data/cpu_optimization/2026-05-04-q6k-default-on-validation/a2-gemma4_31b_q4km-q6kavx0.json`). Confirms dense 31B Q4_K_M is bandwidth-bound at ~25% of 460 GB/s aggregate — expected per `feedback_cpu_decode_bw_bound.md`. |
| G0.4e (1st attempt) | Bench MTP (target + drafter, `-mtp -md ... --draft-max 3 --draft-p-min 0.0`) | ✗ FIRST ATTEMPT FAILED | Segfault on first /completion request. Root cause: chicken-and-egg in `params_use_gemma4_external_mtp` — required `params.speculative.type == COMMON_SPECULATIVE_TYPE_MTP` precondition, but that field is set as a CONSEQUENCE of the helper returning true. Gate at line 356 fell through to "Disabling speculative" warning, leaving `slot.has_mtp=false` while drafter context was loaded. Downstream code dereferenced inconsistent state. (27 GB core dump, deleted; `ulimit -c 0` set.) |
| G0.4-fix Phase B | Patched `params_use_gemma4_external_mtp` in `examples/server/server-context.cpp:35-39`. Removed the `type==MTP` precondition. `has_mtp` flag + drafter arch `gemma4_mtp` is sufficient evidence of intent. | ✓ DONE 2026-05-06 | One-line patch, ~10s incremental rebuild |
| **G0.4e (2nd attempt — patched)** | Same canonical bench as 1st attempt | **✓ SUCCESS** | **21.02 t/s on Gemma 4 31B Q4_K_M target + Q8_0 drafter, 84.3% per-token acceptance (91/108)**, 100% per-batch acceptance (36/36 batches had at least one accept). MTP enabled cleanly, no segfault. Server log confirms: `srv init: MTP needs embeddings on decode, enabling` + `common_speculative_state_mtp: using external MTP assistant context (n_ctx=4096)`. |

### G0.4 verdict — directional answer obtained

| Config | Throughput | Acceptance | Speedup vs baseline |
|--------|------------|------------|---------------------|
| **Baseline (no MTP)** | **7.05 t/s** | — | 1.0× (reference) |
| **MTP draft-max=3** (patched ik_llama.cpp) | **21.02 t/s** | 84.3% per-token | **2.98×** |
| (PR #1744 mixed-CPU/GPU, threads=24, b=128, -ngl 99) | 21.1 → 48.6 | 74% per-token | 2.3× |

**Pure-CPU EPYC achieves 2.98× — exceeding the PR's mixed-CPU/GPU 2.3× speedup.** Why: the small 500 MB drafter amortizes well against the slow dense 31B target on CPU; MTP is relatively more impactful when the target is BW-bound. On GPU the target is already fast, so the absolute speedup is comparable but the relative gain is smaller.

**Patch deliverable**: a 1-line fix to `examples/server/server-context.cpp` is candidate for upstream PR #1744. The "Oops: strange tensor name mtp_post_proj.weight / mtp_pre_proj.weight" warnings remain (cosmetic — size-accounting iteration at `src/llama.cpp:2509` doesn't recognize non-`blk.*` tensors; loading is unaffected via `create_gemma4_mtp_tensors`).

### Updated G0.4 follow-up options

| Option | Description | Cost | Status |
|--------|-------------|------|--------|
| ~~(i) Watch PR #1744, re-run G0.4d when fixes land~~ | superseded by (ii) | — | ✗ skipped |
| **(ii)** Patch PR #1744 ourselves | done — 1-line fix landed locally; bench result obtained | DONE | ✓ |
| **(iia)** Push the patch upstream | posted to PR #1744 as comment 4388461769 with the 1-line fix + our pure-CPU benchmark numbers | DONE | ✓ |
| (iii) Accept the mixed-CPU/GPU number as directional | superseded — we have a pure-CPU number now | — | superseded |
| (iv) Park track | superseded — gate G0.4 cleared | — | superseded |

### G0.4-26B — 26B-A4B MoE bench (2026-05-06)

In-house GGUF conversion of `google/gemma-4-26B-A4B-it-assistant` (840 MB BF16 → 441 MB Q8_0 via PR #1744's converter) plus full canonical bench. Result: **MoE-A4B + MTP is NOT a coder upgrade candidate.**

| Run | Throughput | Acceptance | Speedup |
|-----|-----------|------------|---------|
| 26B-A4B baseline (no MTP) | 41.49 t/s | — | 1.0× |
| 26B-A4B + MTP draft-max=3 | 44.12 t/s | 58.7% per-token (81/138) | **1.06×** |
| (Coder-30B-A3B Q4_K_M baseline, for context) | 49.1 t/s | — | — |

26B-A4B + MTP at 44 t/s **is slower than the existing Coder-30B-A3B baseline of 49.1 t/s**. The MTP drafter does not amortize on MoE the way it does on dense — confirmed empirically. Per-token acceptance dropped from 84.3% (31B Dense) to 58.7%, and the verifier-side expert-load cost per accepted draft token erodes the bandwidth saving. **Tier X (eval-only, not deployable)** in the registry. The lilting.ch contradicting-evidence finding (intake-527 was originally) is now a documented quantitative result on EPYC.

**Net Gemma 4 MTP picture on EPYC after G0.4 + G0.4-26B:**

| Variant | Baseline | + MTP | Speedup | Verdict |
|---------|----------|-------|---------|---------|
| **31B Dense** | 7.05 t/s | **21.02 t/s** | **2.98×** | ✓ architect-tier candidate |
| **26B-A4B MoE** | 41.49 t/s | 44.12 t/s | 1.06× | ✗ not deployable (slower than existing coder) |
| E4B / E2B | not benched | — | — | deferred (multimodal track) |

Only the 31B Dense path is deployable. Open follow-up: **quality benchmark on `gemma4_31b_q4km_mtp` registry entry** to confirm the 84% per-token acceptance translates to the byte-exact output the Leviathan guarantee promises.

### G1/G2/G3/G4 — promotion path

Only after G0.4 directional positive:

| Gate | Action |
|------|--------|
| **G1** | Port ik_llama.cpp MTP path into our `llama.cpp-experimental` fork (foundational PR #1270 + Gemma 4 PRs #1736/#1741, plus Qwen 3.5 dense #1698 if free); resolve conflicts against our NUMA / CPU-EP work |
| **G2** | Re-bench on canonical EPYC under our fork; compare against G0.4 standalone numbers |
| **G3** | Test composition with `--moe-spec-budget` (verifier-side) on 26B-A4B |
| **G4** | Registry slot proposal per `model-registry-v5-deployment-draft.yaml` |

### Spin-off — `mtp-speculative-decoding.md` reopener (R0 RESOLVED 2026-05-06)

PR #1724 ("MTP per-step checkpoints with CPU recurrent layers") was investigated as a potential unblock for the recurrent-verify wall that closed our Qwen 3.5-A3B hybrid MTP work. **Verdict: does not directly unblock pure-CPU EPYC.**

| Sub-gate | Status | Finding |
|---------|--------|---------|
| **R0** | ✓ DONE 2026-05-06 | PR #1724 changes the gate from `if (!has_gpu \|\| has_cpu)` to `if (!has_gpu)` in `src/llama.cpp::spec_ckpt_try_per_step`. Pure-CPU (no GPU) still hits the disabled path with explicit log "per-step disabled — recurrent layers are CPU-only". CPU compute infrastructure IS in place (`save_all_steps` parameter wired through `iqk_fused_delta_net`, CPU code writes per-step states). Gate is one line away from pure-CPU support but is NOT enabled. |
| **R1a** | ✓ DONE 2026-05-06 | Per-step checkpointing helps **rollback efficiency** when drafts are rejected, NOT recurrent compute cost. Our 0.56× was at 78.5% acceptance — rejection-rollback is a small fraction of cost, dominated by O(N) recurrent-verify per draft step. PR #1724's mechanism would not have meaningfully changed our 0.56× regression. |
| **R1b** | open | PR #1718 (hidden-state lifetime, +8 / −2) is independent of the per-step gate, applies to pure CPU, reports 1.67× / 2.16× uplifts at draft_max=2 on hybrid Qwen3.6-27B-MTP (mixed CPU/GPU). May meaningfully help **draft acceptance** even on pure-CPU. Worth a focused re-test of our Qwen3.5-A3B work under ik_llama.cpp HEAD if R1c clears. |
| **R1c** | open | PR #1698 ("Qwen 3.5 MTP, dense models only") explicitly does NOT cover Qwen3.5-A3B (MoE hybrid). Need to determine whether "dense models only" means MoE-not-supported, or hybrid-recurrent-not-supported. Our prior work was on the MoE hybrid (Delta-Net + attention + MoE FFN) — likely both blockers apply. |
| **R2** | low-priority | Reopener proposal is contingent on R1b/R1c clearing. Even then, the path requires either patching the pure-CPU gate locally (one-line) and accepting the un-validated risk, OR reaching out to Kawrakow for guidance. **Recommend deferring** until G0.4 returns directional positive — Gemma 4 path is the higher-EV track. |

**Bottom line**: pure-CPU per-step MTP is one-line away from being possible in ik_llama.cpp, but the gate is intentionally restrictive and we have no evidence of correctness on pure-CPU. The fundamental K-batched-verify wall on Delta-Net layers is unchanged. **Reopener stays parked.**

### G1 — 31B Dense + 0.5B drafter on EPYC

Only attempt after G0.3 = (a). Prerequisites:
1. ik_llama.cpp MTP path ported into our fork (or ik_llama.cpp itself built on EPYC).
2. Q4_K_M GGUF of `google/gemma-4-31B-it` target available (Google's official GGUF if released, or convert from HF safetensors).
3. Drafter Q8_0 from `Radamanthys11/Gemma-4-31B-it-assistant-GGUF` already exists.

Bench protocol (per `feedback_speed_verify_via_llama_bench.md`):
- ONE standalone llama-bench invocation: `tg128`, `r=3`, canonical settings (`taskset -c 0-95 -t 96 -fa 1 --mmap 0`, `numactl --interleave=all`).
- Compare against architect-tier baseline (frontdoor / Qwen3.6-35B class — confirm exact baseline before running).
- Quality benchmark on standardized suite (do NOT skip — −38% FP8 slowdown case is documented).

### G2 — 26B-A4B MoE + drafter on EPYC

Prerequisites:
1. Community GGUF for the 26B-A4B drafter exists (or we convert it).
2. G0.3 = (a) and ik_llama.cpp MTP path applies to MoE drafters too (verify in G0.1).
3. Drafter architecture class confirmed conventional or shared-KV-Q-only (G0.2 output).

Bench protocol:
- Compare against Coder-30B-A3B Q4_K_M baseline (49.1 t/s on 96t-single-NUMA-node per `project_96t_single_node_operating_point.md`).
- Match canonical settings.
- Quality benchmark on coder-class suite.

### G3 — Compose with MoE-spec budget

Only attempt if G2 ≥ +20% standalone:
- Layer `--moe-spec-budget 64` from `moe-spec-cpu-spec-dec-integration.md` Phase 1 atop the MTP-drafter run.
- Watch for KV-cache-sharing-assumption breakage — the budget mechanism mutates expert selection per token.
- Goal: confirm orthogonality (compose) or identify mutual exclusivity.

### G4 — Registry slot proposal

Only after G2 OR G1 ≥ +20% AND quality holds:
- Propose v6 registry slot following `model-registry-v5-deployment-draft.yaml` per-role binary_path / drafter pattern.
- Per `project_orchestrator_stack_freeze.md`, registry-stack rollout is future work — coordinate with stack-freeze policy.

## Open Questions

1. **ik_llama.cpp port scope**: Is `--spec-type mtp` Gemma-specific or does it generalize to other MTP heads (DeepSeek-V3, GLM-5)? If general, the fork-port investment amortizes across multiple targets and changes the cost-benefit.
2. **26B-A4B drafter shape**: Conventional small-LM (1-3B params, own KV) or Q-only-shared-KV (78M-class, like E4B)? Determines whether one llama.cpp port covers it.
3. **MoE batch=1 cancellation severity**: lilting.ch reports per-draft-candidate expert routing kills the speedup. Our production stack runs batch=1 by default. Quantify on EPYC before committing.
4. **Quant-mismatch slowdown**: Documented FP8 case showed −38% (slowdown). Validated target/drafter quant pairs?
5. **Composition with `--moe-spec-budget`**: Do the mechanisms compose, or does the per-token expert mutation break the drafter's KV-cache-sharing?
6. **TTFT confirmation**: Our long-context / autopilot workloads are decode-dominated, so MTP's no-TTFT property is favourable — but quantify the role-by-role decode/prefill split before claiming applicability.
7. **Upstream llama.cpp roadmap**: Is MTP-drafter wiring on the upstream roadmap? If imminent, fork-port effort is wasted.

## Notes

- The blog claims "no quality degradation" via the standard Leviathan (2211.17192) verifier-rejects-mismatched-tokens guarantee — already foundational in our intake.
- License (Apache 2.0) matches `feedback_opensource_only.md`.
- **CPU is the primary target.** The headline 2-3× speedup numbers are framework-and-batch-dependent claims, not architecture-bound, so there is no fundamental reason they cannot be reproduced (or approximated) on EPYC at canonical settings — the rate-limiter is the ik_llama.cpp port (G0.1) and the architecture-class question (G0.2). The relevant CPU-specific contention is DRAM bandwidth: drafter weights are tiny (78 MB to ~500 MB) compared to the 460 GB/s aggregate budget, so first-order BW analysis says the drafter's marginal cost is dominated by KV reuse and accepted-token rate, not by additional weight transfers. The 26B-A4B batch=1 expert-routing-cancellation finding (lilting.ch) is the genuine CPU concern — it applies regardless of substrate. **G1 and G2 must run on EPYC canonical**; do not substitute GPU benches.
- GPU fallback (`gpu-acceleration-path.md`) is reserved for the case where G0.3 = (b) or (c) (no fork-port path) — it is NOT a parallel deployment plan.
- `feedback_audit_parallel_agent_first.md` and `feedback_handoff_driven_tracking.md` apply: any phase movement must update progress logs and this handoff.
- The deep-dive is deliberately separate from this stub. This stub stays a coordination point with checkboxes; the deep dive carries the architectural detail.

## References

- intake-527 (this entry's seed)
- [`research/deep-dives/gemma4-mtp-drafter-deep-dive.md`](../../research/deep-dives/gemma4-mtp-drafter-deep-dive.md) — full architectural / framework / quantization analysis
- `completed/mtp-speculative-decoding.md` — prior MTP-1 work on hybrid Qwen3.5 (closed, NOT VIABLE on hybrid; non-hybrid result does not generalize)
- `inference-acceleration-index.md` — index entry under MTP-1 reopener gates (this is a separate track — different architecture class, different drafter shape, no per-NUMA-quarter cost-model dependency)
- `multimodal-pipeline.md` — Gemma 4 E-series candidates if multimodal-unified path is taken; G0c relevant only there
- `moe-spec-cpu-spec-dec-integration.md` — verifier-side budgeted-expert; G3 composition target
- `gpu-acceleration-path.md` — fallback path if CPU G0.3 = (b) or (c)
- `model-registry-v5-deployment-draft.yaml` — registry pattern for G4

---

## 2026-05-08 — production deployment LANDED (26B-A4B variant only)

**Status**: gemma4-26B-A4B Q4_K_M MTP is now `worker_general` in production. Phase 1 (declarative) + Phase 2 (launcher) + Phase 3 (smoke test) complete. The 31B Dense variant remains evaluation-only (Tier B).

**Why 26B-A4B was promoted ahead of 31B**: rigorous Claude-as-Judge re-scoring of the May-7 eval found 26B-A4B at 165/183 (90%) full suite + 26/27 (96%) tool_compliance, narrowly beating 31B Dense (164/183, 90%). Combined with 26B-A4B's 60-76 t/s baseline (vs 31B Dense's 4.7 t/s), MTP at the small-MoE class is the deployable form.

**MoE batch=1 cancellation (Q3) RESOLVED via measurement**: research-registry block records `mtp_speedup: 1.06` (44.12 vs 41.49 baseline tps) with 58.7% per-token acceptance — confirming lilting.ch's MoE-cancellation finding qualitatively, but the marginal +1.06× still composes with the 18pp quality lift, so promotion is justified. The full canonical orchestrator launch (taskset 0-95 + numactl interleave + canonical OMP env) brings the production tps higher (76.5 t/s solo verified) — the speedup gap closes when launch params match bench.

**Phase 3 launch-recipe quirk discovered**: the orchestrator's worker_pool branch was missing **8 launch params** vs the bench's canonical recipe. Each missing param surfaced as the same `GGML_ASSERT(buf != NULL && "tensor buffer not set")` assertion at `ggml-backend.cpp:236`. Recipe is now in `project_gemma4_mtp_launch_recipe` memory; reference for any future MTP-role deployment.

**Open follow-ups (not blocking deployment):**
- Launcher full-XOR-quarter gating (task #57) — running all 5 instances simultaneously creates 1.5× CPU oversubscription (load 420 → 9 t/s).
- Q-scorer `baseline_tps` may need refresh (was calibrated against Qwen3-Coder values per `project_qscorer_calibration`).
- 31B Dense MTP rollout deferred — quality is similar to 26B-A4B but tps is unviable (4.7 t/s).

## Research Intake Update — 2026-05-20

### New Related Research

- **[intake-576] "Nemotron-Labs-Diffusion: A Tri-Mode Language Model Unifying Autoregressive, Diffusion, and Self-Speculation Decoding"** (NVIDIA tech report, 2026-05-19; no arXiv ID)
  - Relevance to this handoff: Nemotron-Diff is the first release that **directly claims to outperform MTP** as a speedup technique, with NVIDIA's own data. From the model card: "**3× higher acceptance length and 2.2× speed-up vs. Qwen3-8B-Eagle3** in SGLang"; "**5.9× tokens per forward over Qwen3-8B (no MTP)** with the same accuracy". If MTP via PR #1744 stalls or quality-collapses, Nemotron-Diff's unified-model self-spec is the natural alternative direction to evaluate.
  - Key technique: same weights serve AR + diffusion + self-spec via attention-pattern switching, with **shared KV cache** between drafter and verifier — removes the drafter-target alignment friction that has shaped this handoff (G0 port + cross-variant gate matrix).
  - Delta from current Gemma 4 MTP approach: Gemma 4 MTP uses a **separate drafter** (Gemma4Assistant, 4-layer ~500M for 31B / ~78M for E4B) trained jointly with the target. Nemotron-Diff uses **the same weights** for draft and verify. Different deployment story: one model on disk vs target + drafter pair. Same CPU-deployment caveat: NO llama.cpp / GGUF path announced; release is BF16-only on vLLM/SGLang only — Nemotron-Diff is NOT a CPU-deployable alternative today, only a research-direction signal.
  - Caveats: (a) PDF tech report did not decode via WebFetch in this intake pass — full ablations vs MTP and quality benchmarks (MMLU/GSM8K/HumanEval) are in the report body but not yet captured; (b) sibling Nemotron-3-Nano GGUF releases have known llama.cpp Mamba-base assertion crashes (ggml-org/llama.cpp #20570, #18099) — community port path is non-trivial.
  - Action: monitor for community llama.cpp port + ablation re-extraction from PDF; re-evaluate as MTP alternative on Tier B candidates if `gemma4_31b_q4km_mtp` quality-bench stalls.
  - **Deep dive 2026-05-20**: [`research/deep-dives/nemotron-labs-diffusion-tri-mode.md`](../../research/deep-dives/nemotron-labs-diffusion-tri-mode.md) — full PDF parsed; Tab. 10 acceptance length on SPEED-Bench gives the head-to-head MTP comparison: **Nemotron-Diff Native 5.46 / LoRA-tuned 6.82 vs Qwen3-9B-MTP 4.24**. On the four diffusion-friendly categories (coding/math/reasoning/multilingual) the gap widens to 8.69 vs 4.73. This is the strongest single-paper evidence yet that "self-speculation > MTP" as a paradigm at low concurrency on dense models. Caveat: paper baseline is Qwen3-9B-MTP, not Gemma 4 MTP — our 2.98× pure-CPU gemma4-26B-A4B-MTP datapoint may still beat Nemotron-Diff if the Gemma 4 drafter is significantly better aligned to its target than Qwen3-9B-MTP is to Qwen3-9B.

---

## Research Intake Update — 2026-05-27

A companion `/research-intake` run for the `gpu-drafter-mi200-investigation.md` handoff surfaced three papers that bear on this handoff's design assumptions.

### New Related Research

- **[intake-621] "DeepSeek-V3 Technical Report" (MTP section)** (arxiv:2412.19437, Dec 2024)
  - Relevance: Confirms that the MTP heads are designed to be *separable from the trunk* — "during inference, we can directly discard the MTP modules and the main model can function independently." This is the same separability the Gemma 4 MTP G0 ports rely on. DeepSeek-V3 uses **sequential** MTP (D=1 here, but the architecture supports D>1 stacked modules each with their own transformer block + projection M_k); Gemma 4 Assistant drafters appear closer to this sequential-with-shared-head topology than to Gloeckle's parallel-heads design.
  - Key technique: shared embedding + shared output head across MTP modules and main model; per-depth transformer block + projection.
  - Reported results: ablation shows MTP improves HumanEval 20.7→26.8% small / 44.5→53.7% large, GSM8K 25.4→31.4%; no inference TPS reported.
  - Delta from current approach: validates the Gemma 4 G0 architectural assumption that the assistant head is structurally a "speculative-drafting peer" of the trunk, not an entangled trunk module. Independently corroborates the deep-dive's two-class taxonomy of Gemma 4 drafters (Gemma4Assistant 31B/26B vs E4B variants).

- **[intake-623] "Better and Faster Large Language Models via Multi-Token Prediction" (Gloeckle et al.)** (arxiv:2404.19737, NeurIPS 2024 spotlight, Meta FAIR)
  - Relevance: Parent paper of the entire MTP head family. **Parallel** MTP (Gloeckle, 4 heads sharing trunk) vs **sequential** MTP (DeepSeek-V3, depth-D stacked) is the design fork. Gemma 4 Assistant drafters are 4-layer 1024-hidden transformer blocks — closer to "small attached sub-model" than to either Gloeckle's parallel heads or V3's per-depth blocks. Worth comparing acceptance rates if Google publishes details.
  - Key technique: train n parallel output heads on a shared trunk; each head predicts token t+i.
  - Reported results: code/math gains scale with n; up to 3× decoding speedup on code with n=4.
  - Delta: gives this handoff the *spectrum* (parallel ↔ sequential ↔ separate-sub-model) into which Gemma 4 Assistant should be classified — affects whether G0 port mechanics from one work on the others.

- **[intake-620] "SpecDec++: Boosting Speculative Decoding via Adaptive Candidate Lengths"** (arxiv:2405.19715, COLM 2025)
  - Relevance: Adaptive γ controller. The 1.06× MoE-batch=1 vs 2.98× dense Gemma 4-31B split (per handoff header) implies that **fixed γ is the wrong setting** under MoE expert-routing cancellation — the optimal γ likely varies per-token by routing entropy. SpecDec++'s acceptance-prediction head on the drafter is the right substrate to encode that.
  - Key technique: lightweight binary classifier on draft hidden state, MDP-derived stop threshold.
  - Reported results: 2.04× Alpaca / 2.26× GSM8K / 2.23× HumanEval over fixed γ.
  - Delta: if G0a/G0b ports succeed, SpecDec++ is a follow-on lever specifically targeted at recovering the MoE-batch loss. Caveat (Tier 2b): training the acceptance head has class-imbalance + signal-sparsity issues; the COLM camera-ready discusses mitigations.

### Cross-link to companion handoff
- See `gpu-drafter-mi200-investigation.md` § Research Intake Update for the full 9-entry intake batch and stage mapping.
