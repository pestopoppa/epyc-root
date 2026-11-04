# KPF-60 fixture blob-export preparation

`fixture-blob.patch` applies only to the proposed test fixture
`tests/test-kpf60-cache-fixture.cpp`, after the source candidate in
`kpf60-native-fixture-prep-20261104` has been prepared. It adds an optional
`--data-blob PATH` argument to write the existing writer sink's exact data
section to a newly created file. Existing paths and final-component symlinks
are refused with `O_EXCL` and `O_NOFOLLOW`; writes handle interruptions and
are flushed before close. The caller must supply a path inside its separately
claimed output directory. Parent-directory symlink containment and same-UID
mutation protection are not established.

The output is written before all subsequent negative cases complete. A future
runner must retain every attempt and accept a blob only when the same fixture
process exits zero and all other source, build, cleanup and custody checks pass;
partial files are never a successful capture. Two separately captured blobs
can then be checked by `kpf60-blob-pair-verifier-20261104` and its fixed
152-byte oracle.

The HIGH-impact `llama_kv_cache` class was not edited by this preparation. The
patch and fixture remain uncompiled and unrun. No native blob, byte-equivalence,
cache correctness, hybrid or GPU calibration, or measurement result follows.
The native candidate and any new class changes remain subject to the HIGH
impact stop and skipped-file limits.
