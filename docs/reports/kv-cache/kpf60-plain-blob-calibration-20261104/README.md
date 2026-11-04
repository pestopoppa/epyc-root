# KPF-60 plain F16 serialization calibration helper

`plain_blob.py` independently parses the **data portion** of a little-endian,
non-transposed, plain F16 `state_write_data` fixture at source
`8952a0f693fb923918157eb25117641b74766230`. The caller supplies independently
known cell count, layer row widths, absent-V layers and F16 type ID; the parser
checks headers, bounds, overflow, exact end-of-buffer and per-layer payload
spans. It reports K, V and writer-header metadata totals separately.

Three model-free tests passed, including two lengths, absent V, invalid row
geometry, overflow, corrupted headers, truncation and trailing bytes. Fixtures
are synthetically constructed independently of the parser. No native blob,
fragmented or shared cells, transposed or quantized V, hybrid cache, observer,
GPU, or backend transfer was tested. The output is not a measurement warrant,
the private observer is not connected to a live test, and this helper does not
qualify a build or a target-model row. A native fixture and independent writer
output are required before treating it as calibration.
