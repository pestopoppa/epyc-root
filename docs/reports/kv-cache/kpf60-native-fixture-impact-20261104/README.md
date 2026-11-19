# KPF-60 native fixture source impact

The exact-source index at detached commit `8952a0f693fb923918157eb25117641b74766230`
was current when queried. The class query for `llama_kv_cache` in
`src/llama-kv-cache.h` returned **HIGH**, 31 affected nodes and 17 direct. The
constructor query in `src/llama-kv-cache.cpp` returned LOW with zero affected
nodes. Exact argv, stdout, stderr and index status are retained alongside this
report. This is a graph result, not evidence that analyzer-skipped files have
zero impact; [prior scan coverage](../kpf60-gpux-impact-8952-20261104/) remains
applicable.

The source-edit rule requires stopping and warning on HIGH. No fixture patch,
build or model execution was performed after these queries; the owning session
was informed. This report does not clear source edits or establish native
correctness.
