## Research Intake Report — Stage 1 — 2026-10-06 (session intake-q38fn-cluster-ec-20261006)

Lane: /mnt/raid0/llm/worktrees/ec-intake-q38fn-cluster (branch lane/ec-intake-q38fn-cluster, base origin/main 6033e30cd). Writes: research/intake_index.yaml, .research-session.json only. Prior stage4-complete session archived under prior_sessions.

### Processed Entries
| ID | Title | Type | Novelty | Relevance | Cred | Verdict | Verification |
|----|-------|------|---------|-----------|------|---------|--------------|
| intake-1937 | myllmbox/qwen38-flash-next-cluster-recipe (2x Spark, vLLM 0.30, TP2/EP, RoCE) | repo | high | high | null | worth_investigating | stage1-unverified |
| intake-1938 | AMD ROCm 10.1 blog (2026-10-05), tracking params stripped | blog | medium | medium | null | worth_investigating | stage1-unverified |
| intake-1939 | azampatti Qwen3.8-Flash-Next-125B-A5B-INT4-AutoRound (HF card) | repo | high | high | null | worth_investigating | stage1-unverified |
| intake-1940 | azampatti Qwen3.8-Flash-Next-Int4-FAST (single-Spark kit) | repo | medium | medium | null | worth_investigating | stage1-unverified |
| intake-1941 | Saren-Arterius qwen3.8-Flash-DGX-AutoRound (hybrid fp8 vLLM build) | repo | medium | medium | null | worth_investigating | stage1-unverified |
| intake-1942 | vllm PR #58863 RecoverSSM | repo | medium | medium | null | worth_investigating | stage1-unverified |
| intake-1943 | NVIDIA DGX Spark hardware docs (+ clustering page) | blog | medium | high | null | worth_investigating | stage1-unverified |
| intake-1944 | AMD ROCm 10.1.0 documentation (release notes, compat matrix) | blog | medium | high | null | worth_investigating | stage1-unverified |
| intake-1945 | Qwen/Qwen3.8-Flash-Next (HF card, architecture) | repo | medium | high | null | worth_investigating | stage1-unverified |
| intake-1946 | local-inference-lab/b12x (RoCE one-shot all-reduce) | repo | low | medium | null | worth_investigating | stage1-unverified |
| intake-1947 | eugr/spark-vllm-docker | repo | low | medium | null | worth_investigating | stage1-unverified |
| intake-1948 | NVIDIA forum: Q38FN on 1/2/4 Sparks, official NVFP4 (tonyd615) | blog | high | high | null | worth_investigating | stage1-unverified |

Dedup: swept unbounded against all url/arxiv_id values; no collision for the two inputs or any expansion URL (b12x/pull/49 and other rocm.blogs.amd.com posts are distinct sources).

### Literature Expansion
- 10 of 10 (cap reached): 7 via reference chasing (1939, 1941, 1942, 1945, 1946, 1947 from the cluster README; 1940 from the 1939 card), 1 from the ROCm blog (1944), 2 via search/targeted discovery (1943 NVIDIA spec, 1948 forum thread). hibrid48 HF card fetched but not persisted (cap; its claim is already in 1937). tonyd2wild / MiaAI-Lab repos and the ai-muninn blog seen in search output, not persisted (cap) - Stage-2b candidates.

### Cheap contradiction pass (Tier 2b — provisional)
- 1937 headline: contradicted at Stage 1 by independent forum numbers (1948): official 10-expert NVFP4 on 2x Spark TP2 median 53.7 / peak 63.7 tok/s; one Spark median 32.5; search digests also show 41.7-43.9 tok/s on one Spark and 52.1-53.7 on dual. The kit's default is a different (5-of-10 experts) model, so the two are not like-for-like. Provisional.

### Physics comparison (Stage-1 preliminary, UNVERIFIED; final table in INTAKE_STAGE2.md)

| Platform | Bandwidth peak / measured | Bytes/token | Roofline tok/s | Reported / measured tok/s | Efficiency |
|---|---|---|---|---|---|
| EPYC 9655 CPU (Q38FN, IQ4_XS-uniform) | 537.6 / 446.8 GB/s | 4.16 GB (our tensor table) | 107 (129 at peak) | 52.66 MTP (ours) | ~49% of plain roofline, spec-inflated (Stage-1 hypothesis) |
| MI210 | 1638 / 1433 GB/s | n/a (no Q38FN run) | 344 at 1433 | not measured | n/a |
| 2x DGX Spark (kit, 5-expert INT4) | 546 peak / unmeasured | unverified at Stage 1 | unverified | 93.2 avg / 176.8 peak (README) | unverified |
| 2x DGX Spark (independent, 10-expert NVFP4) | 546 / unmeasured | unverified | unverified | 53.7 median (forum) | unverified |

### Preliminary physics (UNVERIFIED hypotheses, finalised in INTAKE_STAGE2.md)
- Spark = 273 GB/s each (NVIDIA spec), 546 GB/s two nodes (not pooled), ~25 GB/s per QSFP port. Ours: EPYC 9655 12ch DDR5-5600 theoretical 537.6 GB/s, measured read-sum 446.8 GB/s (post-BIOS 2026-09-21); MI210 1.6 TB/s HBM2e (achievable 1.43 TB/s in our STREAM-triad-class reading).
- First-order reading: aggregate bandwidth of the pair (546) is within ~2% of our theoretical (537.6) and above our measured (446.8), so aggregate bandwidth does NOT explain a 2x gap; the candidates are model variant (5 vs 10 experts), speculative accepted-tokens per step, concurrency/aggregation, and our own efficiency.

### RECOMMENDED DEEP DIVES (ranked — operator pre-authorised "all recommended", <=10 per wave)
| Rank | Intake | Why | What a dive settles |
|---|---|---|---|
| 1 | 1937 | headline source; model variant and K unclear | which numbers are 5-expert vs 10-expert, per-prompt, c=1 |
| 2 | 1948 | only independent 10-expert numbers | 1/2/4-node scaling and setup |
| 3 | 1945 | architecture needed for bytes/token | active params, experts, layer layout |
| 4 | 1939 | the 5-of-10 cut and its quality cost | model variant, bytes, speed claims |
| 5 | 1943 | denominator citation | 273 GB/s, 200 Gb/s per port, no latency |
| 6 | 1944 | gfx90a support in ROCm 10.1 | MI210 support, graph-safe, FP8 rows, migration |
| 7 | 1938 | operator addition | blog content for MI210 relevance |
| 8 | 1940 | single-node number and acceptance | one-Spark tok/s, speculative config |
| 9 | 1941 | upstream of the loader, single-Spark numbers | bytes accounting, tok/s setups |
| 10 | 1942 | GDN rollback under deep K | cost of recurrent-state recovery |

### Preliminary actionables [ALL UNVERIFIED — hypotheses, not commitments]
| Intake | Likely owning handoff | Draft direction |
|---|---|---|
| 1937/1948 | cpu-decode-roofline-program.md | physics-normalised comparison row for external Q38FN numbers [unverified] |
| 1937/1942 | qwen38-flash-next-fp8-evaluation.md | probe MTP depth K>4 with cheap GDN rollback in llama.cpp [unverified] |
| 1944/1938 | MI210 handoffs (mi210-q8-dequant-gemv-roofline.md) | ROCm 6.2 -> 10.1 migration screen, REBUILD/AK tags [unverified] |

### Explicit declines (from the wave-1 dive list)
- intake-1946 (b12x): not dived in wave 1 only because the wave-1 cap is 10; carried to wave 2 as a recommended dive-surfaced source (RoCE all-reduce latency numbers).
- intake-1947 (eugr/spark-vllm-docker): wave-1 cap; carried to wave 2.

### Steering ledger
- 3 operator comments recorded this stage (dive policy, physics requirement, ROCm 10.1 addition), all carried to Stage 3 (dispositions context-only / planned / planned).
