# KPF-60 GPU-X source impact

`kpf60-gpux-impact-8952-20261104` completed rc=0 at exact source `8952a0f693fb923918157eb25117641b74766230`: six native upstream impacts and `scan_complete` with `partial=false` were recorded. `chunk_kv_cache` and `llama_chunk_kv_export` are MEDIUM, with 25 and 10 impacted nodes respectively; `chunk_export`, `state_write_meta`, `state_write_data`, and `get_mem_attn` are LOW, with 0, 2, 2, and 2 nodes. No HIGH/CRITICAL appears in the six records.

The native verbose analyzer stdout/stderr and coverage file are retained here. Files omitted under the analyzer size cap are not cleared by this scan; no inference, KV byte/token measurement, runtime correctness or crossover conclusion follows.
