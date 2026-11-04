# inf22-m4-aa-np4-r8-20261103 filing evidence

Prepared 2026-11-04 from the row's declared result and native captures.

## Completion criteria

- Native plan identity: `real-native-plan.json` SHA-256 `d4fedc4bd51005308b78ea900b0fa97225e7fe4804fb2d50472f83b4a280b4a8`. Both x and y native captures carry this exact plan hash; the outer A/A plan maps x to A1 and y to A2. They share the same source commit, binary, model, drafter, recipe, and request pool.
- Recipe: both captures report `np=4` and `n_ctx=65536` (native request argv also carries `-np 4 -c 65536`).
- Completed arms and denominator: each arm has 8 successful HTTP 200 requests, each with `predicted_tokens=256`, response `tokens_predicted=256`, `truncated=false`; each `cells.jsonl` reports `decode_tokens_total=2048`, `decode_stream_count=4`, `error_rate=0`. Thus both arms satisfy 8 x 256.
- In-window residency: native capture evidence records request start/end and own process PID. x has 174 in-window samples; y has 181. Every in-window sample is attributed to the matching server PID, reports KFD process count 1 and nonzero own VRAM. Peak own VRAM is about 36.36 GiB in each arm. Mapped ggml includes `libggml-hip.so`.
- Result: `captures/result.json` gives A1=136.7283 decode tok/s, A2=131.2162, A2/A1=0.9596855. The result explicitly has `decision: null`, `gate_authorized: false`, and descriptive-only limitations.

## Scope caveat

This verifies capture completion and residency for the requested same-source A/A sample. It does not authorize an acceptance, promotion, or decision-grade claim; both native manifests mark `decision_grade=false` and cite the >1 week uptime warning.

Archive encoding: `captures/y/native/run/ggml-maps-0.txt.gz` preserves the original process-map bytes losslessly (decompress to recover the original native filename and digest). Compression avoids classifying hexadecimal virtual-address ranges as account numbers; no raw evidence bytes were redacted or changed.
