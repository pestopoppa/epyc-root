# StreamingLLM Baseline for KV Reduction Cluster

**Status**: current-v7 source surface, CPU mechanical smoke, and pre-v7 floor/admission sweep recorded; no KV cluster admitted from the floor. Full 4-axis research sweep remains open.
**Created**: 2026-05-19 (post-KV-admission-cluster deep-dive)
**Categories**: kv_cache, context_extension, hardware_optimization
**Priority**: MEDIUM (gate for the entire May 2026 KV-reduction cluster — must land before PBKV/LU-KV/KVP/ForesightKV/SP-KV prioritization is meaningful)
**Depends on**: `../completed/llama-cpp-fork-rebase.md` (KV-cache abstraction), `attention-matching-kv-compaction.md`
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-kv-admission-cluster.md`](../../research/deep-dives/2026-05-19-kv-admission-cluster.md)

## Objective

Land a clean **StreamingLLM (attention sink + sliding window)** baseline in our llama.cpp fork (`epyc-llama`) to measure the **easy-floor** that any KV reduction method must beat. Without this floor, the relative gains claimed by the May 2026 KV cluster (SP-KV / KVP / LU-KV / ForesightKV / PBKV) cannot be evaluated against the simplest possible competing technique.

**2026-06-13 implementation checkpoint**: `llama.cpp` commit `632ce0f92` adds a low-invasive scaffold using the existing server context-shift path rather than patching core KV tensor layout. `--kv-streaming-sink` / `--kv-streaming-window` are exposed in `llama-cli` and `llama-server`, per-request JSON accepts `kv_streaming_sink` / `kv_streaming_window`, and middle eviction is performed with the existing `llama_memory_seq_rm` + `llama_memory_seq_add` sequence-shift mechanism. Defaults are disabled, preserving existing behavior until explicitly enabled.

**2026-07-18 current-v7 evidence checkpoint**: commits `111bff89d` (streaming KV context controls) and `cf051d3e1` (completion surface) are pushed to `fork/experimental-v7-refresh-20260716`. The root checkpoint commit is `d6bdd4da`, with main merge `45d8e09` already recorded.

- Clean rebuilt Qwable Q8 MI210 artifact: `/mnt/raid0/llm/epyc-inference-research/data/model_admission_throughput/qwable_q8_mi210_llama_bench_20260718T220220Z_rebuilt_cf051d3e1`.
- `bench.json` rows: prompt-only `p512` `2101.214398 t/s`; `tg128` `99.172708 t/s`; combined `pg2048/1024` `avg_ts` `266.820398`; `pg8192/1024` `avg_ts` `602.11996`; `pg32768/512` `avg_ts` `1252.673664`. These `pg` values are `llama-bench` combined prompt+generation `avg_ts`, not isolated decode.
- A prior first run self-reported stale `build_commit=41ae83402` and is superseded by the clean rebuilt artifact.
- CPU mechanical smoke: `/mnt/raid0/llm/epyc-inference-research/data/streamingllm_floor/streamingllm_qwen06_completion_cpu_floor_20260718T2200Z/summary.md` records baseline context-shift decode `319` tokens at `105.57 t/s` and StreamingLLM decode `319` tokens at `103.10 t/s`.
- Both lanes passed mechanical smoke but failed prompt-quality checks. This is not an admission or performance claim. The failed `streamingllm_qwen06_cpu_floor_20260718T215438Z` artifact is excluded; its oversized stdout was removed by main.

**2026-07-20 pre-v7 floor/admission sweep**: inference-research adds
`scripts/benchmark/streamingllm_floor_sweep.py` plus focused tests and artifact
`/mnt/raid0/llm/epyc-inference-research/data/streamingllm_floor/streamingllm_qwen17_q8_cpu_sweep_20260720Tlive/summary.json`.
The sweep used Qwen3-1.7B Q8 CPU-only, `-c 384`, `-n 768`, context-shift
baseline plus sink/window clusters `8:128`, `16:192`, and `32:256`. All four
arms exited `0`, crossed the runtime context, and decoded about `31 t/s`, but
all failed the prompt-quality/final-marker floor and no streaming arm improved
speed materially over baseline (`0.990x` to `1.011x`). Admission decision:
`admit_cluster=false`, reason `no_streaming_cluster_passed_quality_and_speed_floor`.
This closes the pre-v7 "is there a simple KV admission cluster to admit now?"
question negatively; it does not close the broader 4-axis KV research program.

## Why This is a Cluster-Wide Gate

The deep-dive surfaced a structural gap: **of the 5 papers in the cluster, only KVP (intake-551) explicitly compares to StreamingLLM**. Without an internal floor:
- LU-KV's "80% KV reduction at minimal degradation" claim is unanchored — what does sink + window already achieve?
- SP-KV is empirically refuted (Steele arxiv:2601.14279) precisely because position-based heuristics (sink + last-N) match learned scorers — but we have no internal data point.
- PBKV's 1.85× over LRU doesn't tell us how much of that gain is from being smarter than naïve LRU vs being smarter than sink + window.

Landing the floor first **changes the rank-order** of the cluster priorities, possibly demoting attention-kernel methods (LU-KV / KVP / ForesightKV) in favor of orchestrator-layer methods (PBKV) that compose with sink + window rather than replace it.

## Research Context

| Intake ID | Title | Relevance | Notes |
|-----------|-------|-----------|-------|
| intake-538 | SP-KV (arxiv:2605.14037) — write-time admission | medium | empirically refuted by Steele's sink+window floor (arxiv:2601.14279) — this spike validates that refutation on our hardware |
| intake-551 | KVP (arxiv:2602.10238) — per-head RL eviction | high | only cluster paper that compares to StreamingLLM |
| intake-552 | LU-KV (arxiv:2602.08585) — global combinatorial per-head budget | medium | frozen-weights compatible; needs the floor to be meaningful |
| intake-553 | ForesightKV (arxiv:2602.03203) — oracle distillation + GRPO | high | needs floor + requires FT infra (deferred) |
| intake-554 | PBKV (arxiv:2605.06472) — workflow-aware residency | high | orchestrator-layer; composes with sink+window |

## Spike Plan (single phase)

### StreamingLLM patch in `epyc-llama` (~200 LoC, 1 nightshift sweep)

**Mechanism**: keep the first K_sink tokens permanently (attention sink), keep a sliding window of the last K_win tokens, evict everything in between. Standard implementation: `K_sink = 4`, `K_win = 1024–4096` tunable.

**Steps**:
1. **DONE 2026-06-13**: Add disabled-by-default sink + window policy through server context-shift (`llama_memory_seq_rm` / `llama_memory_seq_add`) plus CLI and per-request controls.
2. **PENDING**: Bench sweep on:
   - **Long-context retrieval** (S-NIAH or RULER subset)
   - **Long-context reasoning** (LongBench or a coder-trace subset)
   - **Multi-session dialogue** (existing autopilot eval-tower trace samples)
   - 3 cache budgets: 25%, 50%, 75% of full KV
   - 2 models: gemma4-26B-A4B Q4_K_M (worker_general production), coder-30B Q4_K_M

**Success criteria**:
- StreamingLLM at 50% budget loses ≤10% accuracy vs full-KV on long-context reasoning
- StreamingLLM at 25% budget loses ≤25% on the same — establishes the noisy floor

**Gate criteria for cluster prioritization**:
- If StreamingLLM at 50% budget already preserves ≥95% accuracy on our representative workloads, **demote LU-KV / KVP / ForesightKV** — their incremental gain over the floor is too small to justify the kernel work.
- If StreamingLLM degrades significantly at 50% budget, **promote LU-KV** as the next-priority attention-kernel method (it's the only frozen-weights compatible candidate in the cluster).
- Either way, **PBKV stays prioritized** because it operates at the orchestrator layer and composes with sink + window rather than competing.

**Dev cost**: code scaffold landed as 60 insertions / 2 deletions in `epyc-llama` commit `632ce0f92`.
**Compute cost**: 1 nightshift (~8 hours) for the 4-axis sweep (3 budgets × 2 models × 4 workloads). Requires `feedback_no_concurrent_inference` per-bench approval per sweep cell.

## Non-Goals

- **No fine-tuning**: StreamingLLM is purely inference-time, no model surgery.
- **No KV quantization changes**: orthogonal to `kv-cache-quantization.md` (completed); StreamingLLM operates on the *selection* axis, not the *precision* axis.
- **No comparison to TriAttention / AttentionMatching**: those are already in flight under their own handoffs; this spike establishes a NEW (sink+window) baseline they should also be measured against in a follow-up.

## Failure Modes to Watch

- **Sink-token attention drift on quantized models**: position-based methods can interact badly with Q4_K_M KV quantization if the sink tokens hit different quant blocks than the window tokens. Sweep both Q4_K_M and F16 KV cache configs to disambiguate.
- **Sliding-window edge effects**: long-context reasoning may need the sink + window combination tuned per workload (coder traces are different from dialogue). Report per-workload sweep results, not just averages.
- **Per-head heterogeneity hidden by uniform sink+window**: LU-KV's whole pitch is that different heads have different temporal patterns. If sink+window already wins, that pitch is undercut — but if some heads degrade catastrophically under uniform sink+window, LU-KV's per-head budget allocation has demonstrable value. Track per-head attention entropy in the sweep.

## Open Questions for User

1. **K_sink, K_win defaults**: StreamingLLM paper uses 4 + 1024. For our coder/frontdoor traces (often 5-10 K tokens of context), the window should likely be larger. Sweep K_win ∈ {1024, 2048, 4096} per workload?
2. **Quantization scope**: include or skip the F16 KV-cache baseline? F16 isolates the algorithm from quant interaction but doubles the sweep size. Recommend: include F16 only on the smallest model (gemma4-26B-A4B is 26B; running F16 KV adds ~2 GB per slot — feasible).
3. **PBKV order-of-operations**: should this StreamingLLM baseline land BEFORE the PBKV spike (per the deep-dive recommendation), or in parallel? Sequential is safer but adds 1-2 weeks to PBKV's start.

## References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-kv-admission-cluster.md`
- StreamingLLM paper: `https://arxiv.org/abs/2309.17453` (Xiao et al., ICLR 2024)
- StreamingLLM reference impl: `https://github.com/mit-han-lab/streaming-llm`
- Steele falsification (sink+window beats learned scoring): `https://arxiv.org/abs/2601.14279`
- Related handoffs: `attention-matching-kv-compaction.md`, `triattention-kv-selection.md`, `summary-token-attention-readiness.md`, `multiscreen-attention-evaluation.md`, `../completed/llama-cpp-fork-rebase.md`

## Progress checklist

- [x] StreamingLLM sink+window scaffold landed in epyc-llama (commit 632ce0f92, disabled by default) ✅
- [x] Current-v7 source/build surface reconciled at `111bff89d` + `cf051d3e1` on `fork/experimental-v7-refresh-20260716` ✅ 2026-07-18
- [x] CPU mechanical smoke completed for baseline and StreamingLLM lanes; both passed mechanics but failed prompt-quality, so no admission/performance claim ✅ 2026-07-18
- [x] Pre-v7 floor/admission sweep completed on Qwen3-1.7B Q8 CPU-only: all arms exited cleanly, no sink/window cluster passed quality+speed floor, and no KV cluster is admitted before v7 promotion ✅ 2026-07-20
- [ ] Run 4-axis inference sweep: 3 workloads (retrieval/reasoning/dialogue) x 3 budgets (25/50/75%) x 2 models
- [ ] Evaluate success criteria (<=10% loss at 50% budget, <=25% at 25%) per-workload, track per-head attention entropy
- [ ] Apply cluster-prioritization gate: demote LU-KV/KVP/ForesightKV or promote LU-KV based on floor
- [ ] Resolve user questions: K_sink/K_win sweep values, F16 KV scope, PBKV order-of-operations
