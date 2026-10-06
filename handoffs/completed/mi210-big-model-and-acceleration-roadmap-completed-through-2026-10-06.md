# MI210 Big-Model & Acceleration Roadmap — Completed Through 2026-10-06

> Historical ledger only; current work lives in `../active/mi210-big-model-and-acceleration-roadmap.md`.

Closed (`- [x]`) Progress-checklist detail moved verbatim from the active handoff (INF-34) at the 2026-10-06 evening /wrap-up compaction. Open boxes and their parent lines stayed in the active file.

- [x] Gating experiment 3: 122B IQ2 eval-parity (PASSED judge-free d0.0pp 2026-07-05) ✅
- [x] Gating experiment 1: expert-routing-skew profile (Zipfian? -> offload/REAP viability). Production-representative repeat completed: near-uniform global aggregate (`top_32=15.19%`, entropy `0.9987`) with weak layer-local skew (median layer `top_32=39.19%`). Do not build generic GLM hot-expert offload/REAP from this evidence. Reopen trigger **rewritten 2026-09-07**: an **SRP/SCH measurement on per-token routing traces**, not "a cacheable Zipfian hot set". The 2026-07-17 artifact is a cumulative per-expert histogram over a mixed calibration corpus — it has no time axis, so it cannot observe segment-level locality (`intake-1328#00`), and corpus-mixing alone collapses the signal (per-domain entropy 0.79–0.85 → 0.9453 mixed; Gini 0.62–0.71 → 0.3889; top-10% share 0.42–0.58 → 0.252, recomputed from released traces, `intake-1336#01`). The `/mnt/raid0/llm/tmp/expert-routing-skew-glm52-*` directories no longer exist; this prose is the only record. **Payoff bound, so a positive signal is not by itself a reopen**: trained routing locality is worth **+1.58% to +2.03% end-to-end** on this host (ReMoE best simulated µMiss reduction 7.34% @C=6 / 9.41% @C=12 applied to the intake-1318 expert path, 20.96 ms of a 99.1 ms token, perfect-hit ceiling +27% = 10.09 → 12.80 t/s on qwen4exp) — `intake-1338#03`, and that is an upper bound assuming a fill-bound expert path, which ours is not. Measurement instrument: the routing tap (INF-72, [moe-routing-tap-and-locality-measurement.md](moe-routing-tap-and-locality-measurement.md)). The kill stands. ✅ 2026-07-17
- [x] Gating experiment 2a: GPU-draft N5 alpha feasibility (`n5_spec_on` accepted `376/376`) ✅ 2026-07-16
- [x] Gating experiment 2b-Stage-1: CPU-target + MI210 external-drafter speed economics failed (`0.915x` decode, `508/508` accepted) ✅ 2026-07-17
- [x] Gating experiment 2c-Stage-2: frontdoor + drafter co-resident speed economics failed (`native MTP 0.948x`, external drafter `0.355x` vs GPU no-spec) ✅ 2026-07-17
- [x] Axis-B DR-1 break-even model: external Stage-1/2 are not acceptance-blocked; they are overhead/control-cost blocked, so future lanes must satisfy `E(α,K) > F(K)+H(K)` before build. Evidence: [docs/reference/gpu-drafter-break-even-model-2026-07-18.md](../../docs/reference/gpu-drafter-break-even-model-2026-07-18.md). ✅ 2026-07-18
- [x] Gate-R candidate frontdoor residency row: same-window CPU re-anchor, MI210 no-spec, and MI210 native-MTP 8K/1024-token `n=5` reps completed; native MTP wins this longer repetitive shape (`119.69 t/s`, `7.00x` CPU, `100%` accepted drafts) ✅ 2026-07-18
- [x] Qwen3.6-27B dense current-v7 MI210 context row recorded: `data/gpu-mi210/qwen36-27b-dense-v7-context-20260718T2225Z`, prompt `854.17/807.61/666.62 t/s`, decode `29.64 t/s`; observation-only because ratified `P-GPU-1` requires a production-named kernel ✅ 2026-07-18
- [x] Draft `P-GPU-1` ratification package for operator review: `docs/reference/p-gpu-1-ratification-package-2026-07-18.md` maps required MEASUREMENT fields to existing Gate-R/K35 MI210 artifacts and keeps the amendment itself human-only ✅ 2026-07-18
- [x] Ratify/update `P-GPU-1` now that MI210 exists ✅ 2026-07-19: `/workspace/MEASUREMENT.md` is signed with a production-named-kernel-only claim path. Existing experimental-v7 Gate-R/K35/AXA rows remain observation-grade; Gate-R decision-grade certification now targets `production-consolidated-v7`.
- [x] Probe gemma4-IQ4 mid-precision residency: current experimental-v7 `d1e5a20eb` MI210 observation at `/mnt/raid0/llm/epyc-inference-research/data/gemma4_iq4_residency/gemma4_26b_ud_iq4xs_mi210_v7_20260718T162446Z/summary.json` loaded `gemma-4-26B-A4B-it-UD-IQ4_XS.gguf` fully resident, measured `pp2048 2449.01 t/s`, `tg256 81.91 t/s`, and a server/chat 8K coherence probe with `6971` prompt tokens at `2257.80 t/s` plus `201` completion tokens at `76.02 t/s`; cleanup proof shows no KFD PIDs. Follow-up optimized lane at `/mnt/raid0/llm/epyc-inference-research/data/gemma4_iq4_residency/mtp_ab_local_20260718T170739Z/summary.json` measured no-spec q8-KV `pp2048 2450.51 t/s`, `tg512 81.41 t/s`, and external assistant-head MTP `117.01 t/s` with `360/362` drafts accepted. Strict JSON content was not clean, so quality retention/template cleanup remains open before any role claim. ✅ 2026-07-18
- [x] Axis B / DR-0: measure quant-asymmetric self-spec acceptance and implied `F(K)+H(K)`; alpha alone is insufficient after DR-1 ✅ 2026-07-20
  - [x] DR-0a: procure/build/register an aggressive same-model IQ drafter artifact (IQ1/IQ2_XXS or REAP+IQ1)
    that fits 64 GB HBM for the selected CPU high-quant verifier. Inference-research commit
    `b696241` registers and smoke/context-tests the local
    `/mnt/raid0/llm/models/Qwen3.5-122B-A10B-MTP-GGUF/UD-IQ2_M/Qwen3.5-122B-A10B-UD-IQ2_M.gguf`
    candidate (37.60 GiB, same MTP family, fits MI210). The missing-artifact blocker fed
    the DR-0 acceptance/economics runs; do not download IQ1_M solely for DR-0 because IQ2_M
    passed the strict aggressive-quant drafter gate. ✅ 2026-07-19
  - [x] DR-0b task-class acceptance/economics first pass: source-head v7 MI210 probes on the
    122B UD-IQ2_M candidate show native MTP is still negative on short architect prompts
    (`0.61x`), but positive on long repetitive output (`37.87 -> 60.65 t/s`, `511/511`
    accepted). Composed `ngram-mod,draft-mtp` is much stronger on the same repetitive
    shape (`287.09 t/s`, `7.58x`, `746/746` accepted) and modestly positive on a
    3-prompt mixed architect/reviewer slice (`41.85 -> 50.77 t/s`, `3/3` sanity pass,
    `235/356` accepted). This closes the "is there any task-class signal?" subquestion,
    but not full DR-0: the broadened 8-prompt sanity slice passed only `5/8`, so broader
    quality and explicit `F+H` remain open. ✅ 2026-07-19
  - [x] DR-0d live quant-asymmetric CPU-verifier + MI210-drafter run completed ✅ 2026-07-20:
    corrected reasoning-off artifact
    `/mnt/raid0/llm/epyc-inference-research/data/dr0_quant_asym_self_spec/dr0_quant_asym_self_spec_20260720T043000Z_reasoning_off/`
    measured CPU Q4 baseline `6.890 t/s`; combined K1 `9.959 t/s` (`1.445x`,
    alpha `0.963`), K2 `11.335 t/s` (`1.645x`, alpha `0.928`), and K4 `12.298 t/s`
    (`1.785x`, alpha `0.837`). Cleanup/postflight passed. This does not close DR-0:
    quality sanity failed (`1/28`), target output changed on the code-review control, and
    `F(K)+H(K)` is still not separately observable from current llama-server telemetry.
  - [x] DR-0e telemetry/quality rerun: add `F(K)`/`H(K)` observability and repeat under
    stricter prompt/schema controls; require target-output stability on all tasks before
    any Axis-B serving integration. ✅ 2026-07-20
    - [x] DR-0e.1 telemetry live ✅ 2026-07-20: experimental-v7 server timing fields now
      expose `spec_verify_steps`, `spec_draft_ms`, `spec_verify_ms`, `spec_process_ms`,
      `spec_sample_accept_ms`, and `spec_accept_by_depth`; reduced K2 live artifact
      `/mnt/raid0/llm/epyc-inference-research/data/dr0_quant_asym_self_spec/dr0_quant_asym_self_spec_20260720T050531Z_telemetry_k2/`
      recorded combined `10.694 t/s`, alpha `0.891`, `F(K)=39.889s`, and `H(K)=0.740s`
      with clean postflight.
    - [x] DR-0e.2 quality/stability rerun ✅ 2026-07-20: inference-research final artifact
      `/mnt/raid0/llm/epyc-inference-research/data/dr0_quant_asym_self_spec/dr0_quant_asym_self_spec_20260720T060423Z_dr0e2_full_k_sweep_final/`
      passed quality (`28/28`), output stability for combined K1/K2/K4 versus CPU baseline
      on all four task classes, and cleanup. CPU Q4 baseline was `7.083 t/s`; combined
      K1/K2/K4 reached `9.888` / `11.407` / `11.847 t/s` (`1.396x` / `1.610x` /
      `1.672x`) with alpha `0.945` / `0.900` / `0.787`. F/H observed rows:
      K1 `39.040s/0.545s`, K2 `33.667s/0.657s`, K4 `32.280s/0.781s`.
  - [x] DR-2 serving/routing design ✅ 2026-07-20: reference design
    [docs/reference/quant-asymmetric-self-spec-serving-design-2026-07-20.md](../../docs/reference/quant-asymmetric-self-spec-serving-design-2026-07-20.md)
    selects K2 as the first default-off lane (`1.610x`, alpha `0.900`) and rejects K4
    as first rollout because its incremental speed over K2 is only `3.85%` while alpha
    falls to `0.787`. The lane remains research-only until wider K2 admission and
    production-named `P-GPU-1` certification pass.
    - [x] DR-3a dry-run package scaffold ✅ 2026-07-20: inference-research
      `scripts/benchmark/dr3_quant_asym_k2_admission_prep.py` generated
      `data/dr3_quant_asym_k2_admission/dr3_quant_asym_k2_admission_20260720T063100Z_codex_dryrun/`
      with fixed-K2 launch templates for 8K/16K, six broader task classes, and
      the required lease/cleanup, frontdoor opportunity-cost, and production-named
      `P-GPU-1` gates; focused tests passed (`5 passed`).
    - [x] DR-3b live admission executor + 8K smoke ✅ 2026-07-20:
      inference-research `scripts/benchmark/dr3_quant_asym_k2_admission_runner.py`
      runs fresh CPU-baseline and combined-K2 servers, scores row quality/equivalence,
      and preserves no-serving/no-NumericSwarm gates. Corrected 8K artifact
      `data/dr3_quant_asym_k2_admission/dr3_quant_asym_k2_admission_20260720T071200Z_live_smoke_ctx8192_r1_v2/`
      passed quality (`12/12`), output stability, context coverage, and cleanup;
      CPU baseline `7.185 t/s`, combined K2 `11.104 t/s` (`1.545x`, alpha `0.876`),
      observation-grade only.
    - [x] DR-3c default 8K+16K admission package ✅ 2026-07-20:
      artifact
      `/mnt/raid0/llm/epyc-inference-research/data/dr3_quant_asym_k2_admission/dr3_quant_asym_k2_admission_20260720T071816Z_dr3c_default_ctx8192_16384_r1/`
      passed quality (`24/24`), output stability, context coverage for `8192`
      and `16384`, and cleanup. Combined K2 vs CPU baseline: 8K `10.535` vs
      `6.980 t/s` (`1.509x`, alpha `0.876`); 16K `10.429` vs `6.979 t/s`
      (`1.494x`, alpha `0.879`). Observation-grade only.
    - [x] DR-3d frontdoor opportunity-cost gate ✅ 2026-07-20:
      inference-research artifact
      `data/dr3_frontdoor_opportunity_cost/dr3_frontdoor_opportunity_cost_20260720T074853Z_live_ctx8192_r1/`
      passed as experimental observation: frontdoor `93.690 -> 94.157 t/s`
      after eviction/reload (`1.005x`), DR-3 K2 active `11.701 t/s`,
      alpha `1.000`, cleanup pass, serving/NumericSwarm disabled.
- [x] **stream-K `nsm→k·nsm` + compact-LDS residual — zero-build artifact read CLOSED ✅ 2026-07-18** (v7-audit LANE B B2): artifact recovery found the original MI210 campaign under `/mnt/raid0/llm/tmp/mi210-build/campaign/`, including `mmq-compact-lds-NEGATIVE.patch`, `kernels/fused-prefetch-NEGATIVE.patch`, and rocprof CSVs under `moe-agg/prof/`. Read verdict: stream-K is already the live Q8 MMQ path (`mul_mat_q` plus `mul_mat_q_stream_k_fixup`); B32 Q8 MMQ dispatches use grid `53248 = 512 * 104 CUs`, i.e. one persistent workgroup per CU, with fixup grid `53248`, LDS `512`. The compact-LDS patch is explicitly negative and should not be revived. The only surviving idea is a distinct `2*nsm=208` persistent-grid experiment, but that is a new operator-gated build/bench with a narrow `+0–10%` IQ2/capacity ceiling, not a zero-inference closeout or saved-patch apply.
- [x] **K28 — GDN long-prefill recurrence kernel CLOSED NO-GO ✅ 2026-08-11** (GPU; `ggml/src/ggml-cuda/gated_delta_net.cu:191` TODO): governed whole-model attribution completed the cheap gate and found no admission case for a prototype. GDN summed-kernel share falls from 15.397% at p2048 to 12.180% at p32768; the optimistic 4x-op ceiling falls from 11.548% to 9.135%, below the requirement to materially beat higher-EV alternatives. Closeout: [k28-fused-chunked-gdn-kernel-research.md](../completed/k28-fused-chunked-gdn-kernel-research.md).
  - [x] **K28.1 — ROCm backend support/correctness/perf profile ✅ 2026-07-20**:
    experimental `build-hip` at `93d945885-dirty` built `test-backend-ops`;
    valid invocations pinned `LD_LIBRARY_PATH=$PWD/build-hip/bin` after a raw
    run bound the wrong DSO and failed on `ggml_lightning_indexer`. Support/perf
    artifacts: `data/k28_gdn_perf/k28-gdn-hip-currentdirty-20260720T085909Z/`,
    `data/k28_gdn_perf/k28-gdn-hip-console-currentdirty-20260720T085954Z/`,
    and `data/k28_gdn_perf/k28-gdn-hip-oddlen-currentdirty-20260720T090046Z/`.
    Console perf on MI210 reported realistic `head_count=32,head_size=128`
    long-token cases at `64: 152.99 us / 51.17 GB/s`, `256: 625.04 us /
    31.36 GB/s`, `512: 1254.23 us / 28.15 GB/s`, and `1024: 2485.09 us /
    26.87 GB/s`; odd-length 65-token GDN cases passed `3/3` correctness.
    Interpretation: the long-prefill path is not HBM-bandwidth-saturated, so
    chunking/fusion remains a plausible kernel target. Evidence is
    observation-grade because the source tree has unrelated default-off
    instrumentation changes; implementation remains open.
  - [x] **K28.2 — existing graph-chunked route A/B CLOSED NEGATIVE ✅ 2026-07-20**:
    a temporary default-off `LLAMA_DISABLE_FUSED_GDN_CH=1` probe was added,
    built, measured, and reverted in `llama.cpp-experimental` to compare the
    current fused GDN-CH path against the already-existing graph chunking path
    in `delta-net-base.cpp`. Qwen3.6-35B-A3B Q8 MI210 prompt-only cells all
    favored fused GDN-CH: p64 `706.40 -> 660.41 t/s` (`-6.51%`), p256
    `1643.63 -> 1539.88 t/s` (`-6.31%`), p2048 `2100.06 -> 1959.58 t/s`
    (`-6.69%`), p8192 `1995.07 -> 1869.34 t/s` (`-6.30%`). Evidence:
    `data/k28_gdn_perf/k28-fused-vs-graph-qwen36-35b-summary-20260720.json`.
    Verdict: do not implement a fused-vs-graph policy/threshold switch for
    K28; the remaining speed path is a real fused-kernel recurrence improvement
    (or a separate BF16-state/model-level quality gate), not routing to graph
    chunking.
  - [x] **K28.3 — BF16 recurrent GDN state speed A/B CLOSED NEUTRAL ✅ 2026-07-20**:
    existing `GGML_CUDA_GDN_STATE_BF16=1` was measured on Qwen3.6-35B-A3B Q8
    MI210 against default F32 recurrent state. Prompt-only rows slightly
    regressed: p2048 `2098.07 -> 2081.52 t/s` (`-0.79%`) and p8192
    `1994.42 -> 1979.34 t/s` (`-0.76%`). Decode-only p0/n128 moved
    `99.52 -> 100.25 t/s` (`+0.74%`). Evidence:
    `data/k28_gdn_perf/k28-gdn-state-bf16-qwen36-35b-20260720T092251Z/summary.json`.
    Verdict: do not treat BF16 GDN state as a throughput lever for K28; keep it
    as memory/residency research only, requiring a separate quality/coherence
    gate before any serving use.
  - [x] **K28.4 — Phase 0 op-rerun + ceiling model CLOSED ✅ 2026-07-20**:
    reran the MI210 `GATED_DELTA_NET` backend perf microbench per the detailed
    K28 handoff and reproduced the serial-dependency signature: realistic
    `head_count=32,head_size=128` GDN efficiency falls from `51.20 GB/s` at
    64 tokens to `26.84 GB/s` at 1024 tokens. Direct ROCm attribution was not
    possible because `rocprofv2`, `rocprof`, and `omniperf` are not installed.
    The modeled Phase-0 ceiling combines the op rerun with existing full-model
    Qwen3.6-35B-A3B Q8 prefill rows: estimated GDN prefill share is `15.31%`
    at p2048 and `14.54%` at p8192; an optimistic 4x op kernel maps to only
    `11.48%` / `10.91%` full-model prefill gain. Evidence:
    `data/k28_gdn_perf/k28-phase0-op-rerun-20260720T102526Z/` and
    `data/k28_gdn_perf/k28-phase0-ceiling-20260720T102644Z/summary.json`.
    Verdict: K28 remains a plausible default-off post-promotion kernel project,
    but do not delay v7 promotion for Phase 1 unless a direct profiler rerun or
    throwaway prototype shows materially higher full-model ceiling.
  - [x] **K28.4a — direct GDN timing hook CLOSED ✅ 2026-07-20**:
    because `rocprofv2`, `rocprof`, and `omniperf` were unavailable,
    experimental post-candidate commit `8bb53c520` added a default-off
    `GGML_CUDA_GDN_TIMING=1` HIP-event timing hook for
    `GGML_OP_GATED_DELTA_NET` (requires `GGML_CUDA_DISABLE_GRAPHS=1`).
    Focused validation passed: `build-hip` `test-backend-ops` built cleanly and
    `test-backend-ops test -o GATED_DELTA_NET -b ROCm0 -j 8` passed `38/38`.
    Full-model Qwen3.6-35B-A3B Q8 MI210 timing directly measured GDN at
    `15.45%` of p2048 prompt wall-clock and `14.64%` of p8192; a 4x GDN-op
    speedup maps to only `11.59%` / `10.98%` full-model prompt gain. Evidence:
    inference-research commit `2c2b94b7`,
    `data/k28_gdn_perf/k28-gdn-op-timing-hook-qwen35-20260720Tcurrent/summary.json`.
    Verdict: the timing hook validates the Phase 0 ceiling rather than raising
    EV; K28 remains post-promotion/default-off unless a constrained fused
    recurrence prototype proves materially better.
  - [x] **K28.5 — fused recurrence prototype gate CLOSED NO-GO ✅ 2026-08-11**:
    direct timestamp-only `rocprof` v1 attribution ran on the clean frozen-v9
    binary and Qwen3.6-35B-A3B Q8 at p2048/p8192/p32768. GDN shares were
    15.397%/14.649%/12.180%; optimistic 4x-op full-model ceilings were
    11.548%/10.987%/9.135%. These reproduce the old timing-hook estimate and do
    not materially beat the adjacent levers, so the gate says stop before a
    prototype. Receipt:
    `/mnt/raid0/llm/autokernel/probes/k28-rocprofv1-attribution-20260811-r3/receipt.json`,
    SHA-256 `981306080a674f89f5ac7f9c7631feef1d31071dacd46329aa983db72e74c5a0`.
    - [x] **K28.5a — pinned verbose trace scaffold audit CLOSED ✅ 2026-07-20**:
      `LLAMA_QWEN35_PREFILL_TRACE=2` on Qwen3.6-35B-A3B Q8 with pinned
      experimental v7 libs and `llama-bench -v` emitted structural graph-node
      attribution for p2048/p8192/p32768 prompt-only rows (`2079.36`,
      `1982.56`, `1650.80` prompt t/s). Trace groups show GDN at `24.50%` of
      `linear_attn_total` graph-node deltas and `12.22%` of
      `linear_attn_total+ffn_total` deltas. This confirms the scaffold and
      pinned-library recipe, but it is not wall-clock attribution and does not
      raise the Phase 0 ceiling; `K28.5` stays open only for direct profiler or
      throwaway-prototype evidence. Artifact:
      `data/k28_gdn_perf/k28-qwen35moe-gpu-trace-verbose-pinned-20260720T112158Z/summary.json`.
  - [x] **K28-R1 — Adopt the SGLang `fla/` four-stage decomposition as K28's named reference ✅ 2026-08-11**
    (research-intake 2026-08-09, intake-1030 dive-verified against `sgl-project/sglang` `main`).
    Cite by stage ROLE + entrypoint + pinned commit, never by kernel name alone (see K28-R4):
    `chunk_local_cumsum` (`fla/cumsum.py`) -> `recompute_w_u_fwd` (`fla/wy_fast.py`, the WY/UT
    transform) -> `chunk_gated_delta_rule_fwd_h` (`fla/chunk_delta_h.py`) -> `chunk_fwd_o`
    (`fla/chunk_o.py`), orchestrated by `chunk_gated_delta_rule_fwd` / `ChunkGatedDeltaRuleFunction`
    in `fla/chunk.py`. **This reframes the effort**: the SOTA engine is NOT running one monolithic
    fused kernel — it runs four separately-autotuned Triton stages with on-chip chunk locality, a
    materially easier target to match. Detail in
    [k28-fused-chunked-gdn-kernel-research.md](../completed/k28-fused-chunked-gdn-kernel-research.md).
  - [x] **K28-R2 — SGLang FLA torch-ROCm probe declined by the K28 gate ✅ 2026-08-11.** Direct
    whole-model attribution supplied the intended decision signal more cheaply and failed the
    prototype admission bar; running a second route cannot make the closed kernel project higher EV.
  - [x] **K28-R3 — sequencing dependency retired with K28-R2 ✅ 2026-08-11.** Triton gfx90a itself is
    proven by the INF-03 GEAK/Arena round-trip, but no K28-specific FLA run remains warranted.
  - [x] **K28-R4 — fixed-64 blocking hypothesis retired with the failed K28 gate ✅ 2026-08-11.** It
    remains reference material, not an executable task, because the parent prototype is a measured no-go.
