# S8-c candidate eviction unit

Model-free validation calls the actual built `llama_kv_compress_evict` exported by the candidate `libllama`; executable PLT preemption injects deterministic scoring and a memory double. Cases test default threshold compatibility, ties, absolute and relative recency, sink overlap and budget, invalid controls, gapped occupied positions and failed `seq_rm`. Both gap accounting and failure propagation must be correct for the row to pass: current source inspection suggests those cases may fail. Results are not evidence about the real scorer, physical KV layout or server API.

The packet copies candidate libraries and headers into its own scratch before the build row is filed. `candidate-pin.json` binds copied bytes to the build manifest and the frozen production base plus patch. The compiler and test run only under the row launcher; a complete smoke is a real one-shot result.
