# Worker Vision HIP multimodal input packet

The [preparation receipt](receipt.json) records four synthetic visual fixtures and their exact inline PNG chat requests. The paired run uses the registered Qwen3-VL-30B-A3B-Instruct Q4_K_M weights, F16 projector and embedded template on one MI210 with full model and projector offload. The compiled Worker Vision deployment uses CPU, q8_0 KV and 65,536 context tokens. This isolated recipe uses f16 KV and 4,096 context tokens.

Each arm launches its own loopback server with one slot and no speculation. Capture preserves raw request and response bytes, the native projector load and image decode log, two in-request samples of same-PID MI210 VRAM and the mapped HIP and mtmd libraries, and captured-PID, listener and KFD cleanup. The production bank is sealed before candidate launch. The four-fixture visual slice supplies source bytes for the broad quality pack. The earlier frontdoor JSON mismatch remains recorded.

The publisher queued a single Qwen3-0.6B no-spec text completion on the v10 HIP runtime, the MI210 and four CPU threads. Its readiness predicate checks current request and response bytes, mapped HIP libraries, same-PID residency and cleanup. Readiness is pending. [GPU smoke queue receipt](GPU-SMOKE-QUEUED.json)

The [row spec](row.spec.json) points to the original scratch packet. The runner reuses an exact copy of the architect-general capture helpers selected by the manifest. The [plan](plan.json.original-bytes.json), [model hash receipt](model-hash-receipt.json.original-bytes.json) and [original preparation receipt](receipt.json.original-bytes.json) preserve their original bytes.

`SOURCE.sha256` still describes the scratch sources. To check a reconstructed copy, decode the plan and model hash receipt envelopes' `bytes_b64` into their original filenames, verify each decoded SHA-256 against the envelope's `sha256`, and run `sha256sum --check SOURCE.sha256` alongside the remaining source files. Verify the decoded preparation receipt against its envelope hash. The scratch packet retains its original paths and bytes.
