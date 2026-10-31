# NEMO-PROF-RESEG retained-trace review

Source: 2026-10-25 `nemo-gpu-prof` passes. L is Qwen3.8-27B Q8_0 with DFlash2, but the result below is its *plain* P request. B is Nemotron-3.5-Bolt-74B-A9B IQ2_XXS. Both traces had HIP graphs ON. This is read-only analysis; no GPU run or model adoption.

## Durable copy and method

The raw pass directories were copied byte-for-byte to `/mnt/raid0/llm/epyc-inference-research/data/nemo-gpu-prof/retained-raw-20261025/` before analysis. The local `SHA256SUMS` verifies every copied file; kernel CSV digests are `c1bebdff0cfb35e98df39ba3fb729f9114b0f676cf3bf6ef4ba76ce267d8ca94` (L) and `4bfb3cdd73c7ff8cda2c8bab783ee9bbd21f46d19fec540b6add518a25e000ad` (B), matching the scratch originals.

`resegment.py` uses repeated ordered full kernel-name fingerprints, never the 50 µs gap rule. L starts each plain graph at a repeated `k_set_rows → rms_norm → k_get_rows → quantize_q8_1_1d` signature: 159 graph starts after 2,601 prefill dispatches for 160 generated tokens. Its two steady graph shapes are 55 × 2,065 and 101 × 2,081 dispatches, each with one repeated exact fingerprint. The 2,250-dispatch first graph, 2,257-dispatch shape transition and 2,082-dispatch final edge are explicitly excluded from steady statistics.

B has 3,880 `ssm_scan_f32_group` dispatches, exactly 97 groups of 40: one prefill group and 96 generated steps. Group boundaries anchored eight dispatches before the first scan yield 94 identical 1,845-dispatch steady graphs with a repeated exact fingerprint. The prefill and first decode interval precede that steady set; a 1,861-dispatch transition is separately excluded.

## Observations

| Pass | Steady graph count | Kernel busy mean | Graph span mean | Server wall/token |
|---|---:|---:|---:|---:|
| L plain | 156 | 32.8851 ms | 57.3104 ms | 56.9829 ms |
| B Bolt | 94 | 20.5130 ms | 22.0249 ms | 33.9236 ms |

Kernel busy sums per-dispatch `End_Timestamp - Start_Timestamp`. Graph span is first start to last end; server wall/token is `1000 / predicted_per_second` from `run.json`. The different numbers reflect distinct observables; the trace alone cannot assign the wall gap to a particular host or device cause. This replaces only the invalid plain-token and Bolt-step busy numbers from the old gap segmenter. Original category shares and the separate L speculative-round analysis have not been rederived here.

Checks: `python3 resegment.py` completed with all count/hash/sequence assertions; `python3 -m py_compile resegment.py` passed; copied `SHA256SUMS` passed. JSON contains the exact excluded graph lengths, fingerprints, and busy values.

Replay from this directory with `python3 resegment.py`. The script reads the durable raw copy by its absolute path, asserts exact CSV and ordered graph fingerprints, and writes `resegmentation.json`; compare that file with the committed result after replay. `PROVENANCE.json` pins the run records, raw CSVs, analyzer, result, and original predeclaration digests. The 285 MB raw copy is retained outside Git; only the compact analyzer/result/provenance/README belong in ROOT.
