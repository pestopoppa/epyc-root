# KPF-60 writer-observer source preparation

`writer-observer.patch` targets experimental source
`8952a0f693fb923918157eb25117641b74766230`. It adds an optional private
observer to the existing `state_write_data` traversal, recording metadata
write sizes and each K/V tensor write's layer, stream, offset and length. The
normal writer passes no observer. The patch does not expose a measurement API,
enable hybrid export, count bytes, validate layouts or handle overflow.

`git diff --check` passed. Removing the observer wrappers and reversing the
call substitutions produces a byte-for-byte source match to the original
writer traversal; this is a structural comparison, not compiled or runtime
proof of byte identity. No build, model or measurement ran. The previously
captured `state_write_data` impact was LOW with two impacted nodes, but files
skipped by the analyzer remain outside that coverage. A linked build, exact
writer regression and CPU/HIP calibration remain required before any use.
