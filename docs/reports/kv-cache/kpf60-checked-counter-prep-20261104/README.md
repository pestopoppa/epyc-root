# KPF-60 checked counter arithmetic candidate

`checked_counter.hpp` is a standalone, unintegrated native C++ arithmetic core
for prospective F16 row-major tensor reads. It checks multiplication and sum
overflow, byte bounds, observed offsets and lengths, per-tensor range ordering
and overlap, and expected tensor/range coverage before releasing totals. On a
refusal it will not return totals. The included C++ fixture covers normal K/V
and metadata, overflow, overlap, unsupported transposed layout and a mismatched
observed length. Neither file has been compiled or run: the owner must put that
work in a row, not treat source review as a test result.

This is **not a native byte counter or a ready measurement**. In particular,
the current observer receives only computed byte offsets, not the original cell
ranges or independently validated complete tensor/layer inventory. Wiring must
supply those data from the cache and selection before unchecked legacy arithmetic
can be trusted, prove true tensor capacity and F16 row layout from GGML, and
preserve the normal writer's exact bytes and order. The core does not support
quantized or transposed V, SWA, mirrors, a hybrid accessor, non-tensor metadata
outside `state_write_data`, native JSON records, model custody or backend
transfer. Expected tensor and cell inventory is an explicit independent input,
not discovered by this helper. CPU/HIP calibration and belief capture remain
open. Skipped source-impact files remain uncleared.

A model-free compile-and-test row for this isolated header is possible, but it
would establish only C++ fixture behavior, not source integration, writer
parity or calibration. No such row or full build was prepared here.
