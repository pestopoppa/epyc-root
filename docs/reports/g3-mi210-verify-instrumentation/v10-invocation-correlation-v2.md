# G3 v10 invocation correlation patch (source only)

Patch: [`v10-invocation-correlation-v2.patch`](v10-invocation-correlation-v2.patch)  
Target source: llama.cpp v10 `ffc1bac82eeca6f9099e1ccd9ba49703c460a115`  
SHA-256: `c9851af37cc6ba45e113a8e4cf210408f6c910186096317a6201f4931203b623`

The patch adds a diagnostic invocation scope around each target `llama_decode` call and prints that ID at the actual flash-attention dispatch. The scope is `thread_local`, not process-global: dispatches on another host thread read ID `0` and print `correlation=unknown`. The caller restores the prior scope on both normal return and C++ exception. The server labels a call `parallel_verify_candidate` only for a single speculative slot with a non-serial draft, exactly `drafts + 1` view tokens, and the expected contiguous batch indices. Other calls are labeled `unclassified` while retaining their ID.

This is a bounded correlation mechanism, not a runnable MI210 verification row. It has not been compiled or executed. Source inspection shows the v10 backend scheduler calls each backend's `graph_compute` callback directly while computing graph splits on the caller thread; this makes same-thread propagation plausible for the current path, but runtime controls must verify it. Any worker-thread dispatch remains ID `0` and UNKNOWN. The patch does not emit layer IDs or the actual index list, prove complete attention-event delivery, establish HIP residency, or validate outputs. The existing V1 trace reader does not parse these V2 markers; a V2 reader must correlate begin/dispatch/end records by ID and keep missing, duplicate, unknown-ID, nonzero-return, and incomplete calls UNKNOWN.

Validation performed without building: `patch --dry-run -p1` succeeded against files extracted from the exact v10 commit into `/mnt/raid0/llm/tmp/speculative-decoding-mtp/g3-correlation-v2/original/`; four source-contract tests pass with:

```bash
python3 -m unittest discover -s docs/reports/g3-mi210-verify-instrumentation -p 'test_invocation_patch_contract.py' -v
```

Next use only an isolated source worktree pinned to v10. Apply this patch there, then compile and first run positive and negative correlation controls before any G3 classification. Do not apply it to the frozen production tree.
