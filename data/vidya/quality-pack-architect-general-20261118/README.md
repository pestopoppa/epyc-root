# Architect-general partial HIP input packet

The [preparation receipt](receipt.json) records a pinned prospective input packet for the three-shard Qwen3.8-Flash-Next UD-IQ4_XS model. The isolated recipe uses one MI210, CPUs184–191, 24 GPU layers, 4096 context, split f16 KV, one slot and no speculation. It preserves the distinction from deployed CPU/MTP.

The full runner requires four predetermined requests per arm on immutable v10/C13 runtimes, two in-request samples of pinned HIP mappings and same-PID nonzero MI210 VRAM for every response, a production bank sealed before candidate launch, and PID/listener/KFD cleanup. It records original request/response bytes and stops on the first custody or runtime failure. Runtime and shard content identities were prepared before publication; the grant performs no model hashing or preparation.

Publication returned **GPU-SMOKE-QUEUED** because the GPU was busy. The separate four-CPU v10 small-model smoke has not run and readiness has not passed. Do not republish this unchanged queued packet; consume its smoke event. Full native capture, broad seven-profile comparison and planning-context acceptance remain open. Previous output mismatches remain in scope. This packet establishes no deployed equivalence or promotion authority.

The source manifest names files in the original scratch packet; JSON original-byte envelopes preserve the sealed declarations. [Row spec](row.spec.json) identifies the launcher and scratch root.
