# AKX-ALL-24 — CPU FA decode parallelism on C14, and a split-KV candidate (2026-11-18)

Owner task: `handoffs/active/autokernel-akx-program.md` → AKX-ALL-24 (parent AKX-ALL-23; related routes AKX-ALL-9/10).
Status: code reading plus arithmetic from existing serving data. **No new measurement.** The candidate is built and timed
by the prepared row `c15-cpu-fa-splitkv-20261118` (not published).

## 1. Does C14 decode FA parallelise only over q heads × n?

Read at champion C14 `eee3da838`, `ggml/src/ggml-cpu/ops.cpp` `ggml_compute_forward_flash_attn_ext_f16` (L10447-10612).
The store is built `GGML_IQK_FLASH_ATTENTION=OFF`, so the iqk hook at L10492 is compiled out.

| Call shape | Path | Parallel unit |
|---|---|---|
| n = 1, `GGML_FA_SPLIT_KV` unset or 1, f16/f32 KV, n_kv >= 512 | split-KV (upstream #19209) | KV chunks: `chunk = ceil(n_kv/nth)`, one per thread, all q heads; `reduce_partials` merges |
| n = 1 with `GGML_FA_SPLIT_KV=0` (**the C10/AK serving env, `lp_common.ENV`**) | row split | q heads only: 24 rows |
| 2 <= n <= 63 (every MTP verify step) | row split, static chunks (`neq1 <= 4`) or dynamic | rows = n_head × n |
| n >= 64 | tiled | rows |

**Answer: yes for every verify step, and also for n = 1 under the serving env.** Q38FN (24 q heads, 2 KV heads, GQA 12,
head dim 256, f16 KV, 12 attention layers) with MTP draft n-max 4 verifies 5 rows: 120 rows on 96 threads. With
`nr = 120`, `nth_scaled = 384`, `chunk_size = 1`, `nchunk = 120 >= nth`, so 24 threads walk the full KV twice and 72 walk it
once. The critical path is 2 full-KV walks against an ideal of 1.25 (1.6x). At 48 threads it is 3 walks against 2.5.

The bigger cost is the traversal. Each row is one `_one_chunk` walk over all `n_kv` cells, so the 12 q heads that share a
KV head, times 5 rows, read the same K/V 60 times. At 32k, one layer's K+V for one KV head is 32k × 256 × 2 B × 2 = 32 MiB,
which does not fit in a CCD's L3. Per verify step, 120 rows × 32 MiB × 12 layers = **45 GiB** of K/V traffic, against 0.75 GiB of
unique KV bytes (`ak-longctx-audit-20261004/REPORT.md` §3.1).

## 2. What would split-KV with a fixed-order merge gain at 32k/64k?

No profile of Q38FN with a per-op breakdown at depth exists. The AK census (0.99% FA) ran at about 300 tokens
(`ak-longctx-audit-20261004/REPORT.md` L104-106). The sources at depth are:

- **Production `:8074` (96t, MTP d4):** 41.1 tok/s under 8k, 16.7–18.4 tok/s at 32k–131k (2,706 requests). That is 24.3 ms
  against about 57 ms per token, so about 58% of per-token time at 32k scales with context. Task mix confounds MTP acceptance.
- **Bytes model:** 45 GiB of K/V reads per verify step at 32k. Streaming from DRAM or other CCDs' L3 at an effective 300–450 GB/s
  is 100–160 ms per step. At about 2.5–3 tokens per step, the observed context term is about 33 ms/token, roughly 80–100 ms per
  step. The two agree in order of magnitude, so FA traffic is the plausible owner of the context term.

**Split-KV for n <= 8.** Each thread takes one contiguous KV chunk for all 120 rows: 341 cells at 96t, 683 at 48t. Processed
KV-head-major, one head's chunk is 341–683 × 256 × 2 B × 2 = 0.35–0.7 MiB, which stays in L2 (1 MiB/core) across the 60 row
re-reads. DRAM traffic falls from about 45 GiB to about 0.75 GiB per step, and load balance becomes exact. What remains is compute:
120 × 32k × 2 × 256 MAC × 12 layers ≈ 24 GMAC per step, about 15–30 ms at 96t for the scalar-ish `_one_chunk` body. Merge cost is
120 rows × nth chunks × 258 floats, under 1 ms.

| Context | FA share of step (est.) | Gain, conservative (1.6x FA balance only) | Gain, traffic-bound model |
|---|---|---|---|
| 4k | 5–10% | 2–4% | small (the merge is a few µs per layer) |
| 32k | 40–58% | 15–22% | 30–45% |
| 64k | 55–70% | 20–26% | 40–55% |

The floor case is an FA share of only 10% at 32k with just the 1.6x balance gain, which still gives 3.75%. **The expected gain
is >= 2% of decode at 32k, so the candidate was implemented.** The 48t row cell understates 96t. At 48t, the balance term is
3 → 2.5 walks; the traffic term is unchanged.

The same mechanism is a candidate explanation for the YARN-CPU-ATTN curve that AKX-ALL-24 was filed from (A3B, 16 q heads,
dense attention, 5x falloff from 34k to 253k). That claim is still unmeasured.

## 3. Does IQK FA already do this? Why is it OFF?

- iqk FA (ik_llama `fa/` templates, AKX-ALL-LB4) processes GQA heads together. **Its split-KV path runs only at N = 1**
  (AKX-ALL-LB4 note of 2026-10-22: "its GQA split-KV path runs only at N=1"). A 5-row verify takes its row-tiled kernel, which
  is better than mainline's per-row walk but not KV-split.
- It is OFF because the fold was never timed. LB4 to LB4.9 passed correctness (5182/5182 backend-ops, row-exact 30/30, sinks
  gate C12), but manifest row V11-102 stays PEND for AKX-ALL-LB3 timing, and every shipped CPU recipe since C10 configures
  `-DGGML_IQK_FLASH_ATTENTION:BOOL=OFF` (`c10-fold-build-20261109/configure_argv-cpu.json`, sha `711d190d…`). The LB4.9 hook
  folded into C13 is compiled out of C13/C14 stores.

## 4. Candidate (default OFF)

Fork branch `llama.cpp-experimental-c15-cpu-fa-splitkv-20261118` = C14 `eee3da838` + `9a2cb02b0` + `b67125fbd` (tip
`b67125fbdaf08710cf52e213f691c13235a702f8`). It was **never compiled locally**; the row's in-row build is its first compile.

- `GGML_CPU_FA_SPLIT_KV=1` (read once, default off): FA calls with 1 <= n <= `GGML_CPU_FA_SPLIT_KV_MAX_N` (8) take the
  split-KV path. The other conditions are unchanged: not `use_ref`, `neq3 == 1`, f16/f32 KV with K == V type, f32 Q, and
  n_kv >= 512.
- Under the knob, n = 1 splits too, even with `GGML_FA_SPLIT_KV=0`. Every width then uses the same chunking, which keeps the
  INF-70 1-row/n-row consistency instead of breaking it. With the knob unset, behaviour is unchanged from C14.
- `reduce_partials` is generalised to rows `q_row = iq2·n + iq1`, which is the `write_partials` order of `_one_chunk`. Its
  `dst` offset follows the permute(0,2,1,3). Chunks merge in fixed order 0..nth-1, so the result is deterministic for a given nth.
- The workspace (`ggml-cpu.c`) sizes partials for n <= 8 rows.
- The opt-in test-backend-ops set `fa_cpu_split_kv` covers:
  - D256 GQA12, kv 512/4096/33000/32768/65536, nb 1–5, 8 and 9 (9 is the fallback);
  - q8_0 fallback, no-mask and large-V cases;
  - D512 GQA64 with sinks (applied on the first chunk only);
  - D128 GQA4 at 32k.

## 5. Row `c15-cpu-fa-splitkv-20261118` (prepared, READY-TO-PUBLISH, not published)

`/mnt/raid0/llm/tmp/c15-cpu-fa-splitkv-20261118/`. It makes one in-row build; arm A has the knob unset, arm B has
`GGML_CPU_FA_SPLIT_KV=1`, so both arms run the same binary.

1. tbo `FLASH_ATTN_EXT`: the default corpus and the extra set, each with the knob off and on. Pass means no new failures with
   the knob and no f16 nb 2–8 failures.
2. KLD with llama-perplexity at `-ub 5`, so every FA call is verify-width. The bar is KLD <= 0.01, top-1 >= 97% and |dPPL| <= 0.5%.
3. 8 visits ABBAABBA of Q38FN decode at 4k and 32k, 48t, with the C10 serving argv/env.

**KEEP iff 32k geomean >= 1.02 and 4k >= 0.995.** Gate class is futility-only. It stops for futility if a block-1 32k ratio is
below 0.99.

## 6. Not covered

- 96-thread effect: the row uses 48t.
- 64k and 128k cells.
- N = 1 vs N = 5 bit-exactness under the knob. Expected to hold because the chunking is the same and the REG path is chosen
  for DV = 256 at every n, but this is unmeasured.
- GQA-shared KV pass inside a chunk (AKX-ALL-9's "one KV pass per KV head"). The chunk being L2-resident captures most of it.
