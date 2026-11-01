# NEMO-PROF-RESEG retained-trace review

Source: 2026-10-25 `nemo-gpu-prof` passes. L is Qwen3.8-27B Q8_0 with DFlash2, but the result below is its *plain* P request. B is Nemotron-3.5-Bolt-74B-A9B IQ2_XXS. Both traces had HIP graphs ON. This is read-only analysis; no GPU run or model adoption.

## Durable copy and method

The raw pass directories were copied byte-for-byte to `/mnt/raid0/llm/epyc-inference-research/data/nemo-gpu-prof/retained-raw-20261025/` before analysis. The local `SHA256SUMS` verifies every copied file; kernel CSV digests are `c1bebdff0cfb35e98df39ba3fb729f9114b0f676cf3bf6ef4ba76ce267d8ca94` (L) and `4bfb3cdd73c7ff8cda2c8bab783ee9bbd21f46d19fec540b6add518a25e000ad` (B), matching the scratch originals.

`resegment.py` now uses the server's monotonic request marks as the primary boundary. `run.json` records the exact start/end monotonic timestamps for the measured P request (L) and M request (B); rocprof's `Start_Timestamp`/`End_Timestamp` use the same monotonic clock. The analyzer keeps every complete GPU kernel dispatch inside that interval, sums its busy duration, and divides by the server-reported generated-token count. It independently parses the matching final server `eval time` row and checks both token count and wall ms/token against `run.json` within 2%.

The earlier repeated ordered kernel-name fingerprints are retained as a secondary shape cross-check, not used to assign token boundaries. L fingerprints identify 156 complete steady graphs (55 × 2,065 and 101 × 2,081 dispatches); B identifies 94 × 1,845-dispatch steady graphs. The atypical graph shapes remain excluded from that secondary summary. The primary server-timed window includes all complete measured-request GPU dispatches, including edge shapes, rather than silently dropping them.

B has 3,880 `ssm_scan_f32_group` dispatches, exactly 97 groups of 40: one prefill group and 96 generated steps. Group boundaries anchored eight dispatches before the first scan yield 94 identical 1,845-dispatch steady graphs with a repeated exact fingerprint. The prefill and first decode interval precede that steady set; a 1,861-dispatch transition is separately excluded.

## Observations

| Pass | Generated tokens | Request-window dispatches | GPU kernel busy/token | Server wall/token | Busy/wall |
|---|---:|---:|---:|---:|---:|
| L plain | 160 | 332,946 | 33.0175 ms | 56.98 ms | 0.5794 |
| B Bolt | 96 | 179,633 | 22.2745 ms | 33.92 ms | 0.6566 |

Kernel busy sums per-dispatch `End_Timestamp - Start_Timestamp` for the full server-marked request. Server wall/token is from the logged `eval time` row and independently agrees with `1000 / predicted_per_second` in `run.json`. The 33.0 ms L and 22.3 ms B GPU busy averages are below their corresponding 57.0 ms and 33.9 ms wall averages, consistent with wall including host and scheduling time. The aggregate window supports an average busy-per-generated-token value; it does not expose an individual GPU interval for each token or attribute the wall gap to a cause. This replaces only the invalid per-token busy figures from the old gap segmenter. Original category shares and the separate L speculative-round analysis have not been rederived here.

Checks: `python3 resegment.py` completed with the request-window, token-count, log-timing and source-hash assertions; `python3 -m py_compile resegment.py` passed; copied `SHA256SUMS` passed. JSON records the exact server mark bounds, dispatch counts, busy totals, timing rows, source hashes, and the fingerprint cross-check. The analyzer does not claim per-token boundary resolution.

Replay from this directory with `python3 resegment.py`. The script reads the durable raw copy by its absolute path, asserts exact CSV and ordered graph fingerprints, and writes `resegmentation.json`; compare that file with the committed result after replay. `PROVENANCE.json` pins the run records, raw CSVs, analyzer, result, and original predeclaration digests. The 285 MB raw copy is retained outside Git; only the compact analyzer/result/provenance/README belong in ROOT.
