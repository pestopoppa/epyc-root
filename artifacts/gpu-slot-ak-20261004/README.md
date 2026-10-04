# GPU slot gpu-slot-ak-20261004 — KVU-16b replay, skip OFF/ON × `-b 2048`/`-b 512` (durable copy)

Run by ak-ds41-main, 2026-10-04 05:08:09Z–06:20:04Z (71.9 min), MI210 slot claimed (`mi210_0`), scratch port
:18183, :8083's argv (launch 2026-10-04T02:48:09Z, `argv_sha256 b865820d557f`) with only the binary, port, `-b` and
`-lv` changed. Build `gpu-20261004-c7f5ac9ad` (`b10312-c7f5ac9ad`). Source:
`/mnt/raid0/llm/tmp/gpu-slot-ak-20261004/results/20261004T050808Z/` (not durable).

**Attribution: every skip-ON arm is the combined 19a+19b build INCLUDING commit 2** (`c7f5ac9ad`, WMMA seq tiles).
Commit 2 is not in the KVU-19 fold (19a + commit 1 only). Do not attribute skip-ON numbers to the fold. Skip-OFF
arms (`GGML_CUDA_FA_MASK_SKIP=0 GGML_CUDA_FA_SEQ_ROWS=0`) are the production-equivalent v10 path and carry the
`-b 512` stack-change evidence (KVU-16f).

The replay uses a FIXED decoding predicate (a slot decodes only past prompt end), so its PASS means four requests
decoding at once, unlike the invalid KVU-16b PASS of 2026-10-04 03:25Z.

## Headline

| Comparison | Result |
|---|---|
| skip OFF, `-b 512` vs `-b 2048` | **3.5–4.2× decode while a neighbour prefills**; KFD peak 48.57 vs 51.69 GiB (**−3.1 GiB**); solo shallow prefill TTFT 208.3 vs 154.2 s (**−26%**). Both arms CAPPED at 20 min with 3 decoding at most. |
| skip ON + `-b 512` vs the original v10 run | decode summed while i=3 prefills **7.91 vs 0.56 tok/s (14×)**; all 4 requests decoding at once at 7.7–10.7 tok/s each; PASS in 926 s; KFD 48.59 GiB. |
| skip ON + `-b 2048` | 2.30 tok/s summed while i=3 prefills; all 4 decoding at 7.8–9.0 tok/s; PASS in 781 s. |
| Coherence | greedy spot-check text identical across all four arms (sha `821d2f3d3a563435`); no classifier. |

P3 v2 (parked-neighbour pairs) did not run: budget.

## Files

| Path | What |
|---|---|
| `results/report.md` | The slot report (timeline, replay table, s/iteration by occupied cells, per-request decode during each prefill, `-lv 4` memory breakdowns). It omits the `kvu_off_b512` column; read that arm in `results/kvu_off_b512/replay/report.md` and `results/kvu_off_b512.driver.log`. |
| `results/<arm>/replay/{report.json,report.md,iterations.json,requests.jsonl}` | Per-arm replay output |
| `results/<arm>/{arm.json,coherence.json}`, `results/*.driver.log`, `results/slot_run.json`, `results/slot.log` | Arm config, live env, coherence, driver timeline |
| `results/linkage.llama-server.txt` | HIP linkage proof |
| `runners/` | The slot runner and replay scripts as run (`SOURCES.sha256` pins the originals they were adapted from) |

Server logs, per-event streams, `/slots` samples and KFD 1 Hz series stay in the tmp source.

Consumers: `handoffs/active/kv-unified-stack-rollout.md` (KVU-16f, KVU-16b-1, KVU-19b; owner workspace-ec) and
`handoffs/active/kv-prefix-fork-and-paged-attention.md`.
