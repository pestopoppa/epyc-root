# Flash-Next drafter retarget — 2026-10-28

The current priority rollup still identified the retired Qwen3.5-122B DR-3 K2
certification as open. The operator's newer directive in the MI210 roadmap
explicitly retires that rerun and calls for a new Flash-Next verifier and low-bit
GPU drafter with new artifacts. Removed the obsolete open boxes, preserved the
historical closed results, added the distinct DR-FN1 task and updated its index
and generated priority basis. No old 122B result is transferred to the new task.

The pinned public DS4 IQ2 release reports a 44.81 GB main file and required 32.00 GB PLE sidecar, with DS4-specific padded-down support. It is a potential source, not an established MI210 fit or llama.cpp-compatible artifact. At the current free-space level the two files exceed the 150 GiB reserve; version-pinned range-backed input or additional canonical storage is an engineering path to assess. Runtime footprint and quality remain to be measured. No model was downloaded,
quantized or run for DR-FN1 in this checkpoint.

During this checkpoint the `index_state --check` and `backlog_priority --out`
processes initially started with affinity 0–191 at 23:01:34 UTC. Their captured
PIDs were rebound to sibling CPUs 170–171 before a 23:02:08 UTC clock check.
The unrestricted interval was disclosed to the parallel session; it overlaps
that session's INF-12 diagnostic window, with impact unknown. Subsequent
checks use the permitted sibling pair.

A bounded header-only scan of the current canonical UD-IQ4_XS verifier found its
IQ4_NL per-layer token embedding payload is 28,800,138,240 bytes. Subtracting
that payload from the three files' combined 93,682,584,224 bytes leaves
64,882,445,984 file bytes (60.426 GiB), not a runtime or GPU-memory result.
The frozen source marks the tensor lazy, and the production server advertises
lazy-read and draft-specific tensor-placement flags. Whether those flags permit a
usable CPU-PLE/GPU-draft configuration remains an unrun feasibility question;
model contents were not freshly rehashed. Evidence: `artifacts/drfn1-metadata-20261028/headers.log`; the scanner remains in
`/mnt/raid0/llm/tmp/drfn1-metadata-prep-20261028/`.
