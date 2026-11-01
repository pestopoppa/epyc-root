# KPF-17a shared-trunk exactness harness preparation

This scratch copy starts from the KVU-19a `fa_harness.cpp` source at
`/mnt/raid0/llm/tmp/fa-maskskip-20261003/harness/fa_harness.cpp` (source SHA-256
`6dd03a07406cfe26dfd4ff52de4a4067fd7229d77ee5191bbd8e2e34956fa823`). The
original 86 exactness cases remain first and unchanged in case ordering. The
scratch version adds 25 shared-trunk cases (aligned and unaligned trunk sizes,
F16/Q8_0 KV, head sizes 128/256, batch sizes 1/4/32, plus a long production
trunk case).

The harness treats the first `n_shared` occupied KV cells as shared by every
sequence, then assigns private runs and leaves free cells masked. It includes
independently derived layout and causal-visibility invariants. The checks are
still unexecuted and have no mutation-based negative control; the owner should
add/run independent guard-removal controls before treating them as proof. Each
listing row records `shared=`. The harness emits explicit unsupported rows;
those are evaluated against a backend-specific expected-case manifest.

`expected_cpu.json` declares all 111 cases supported. `expected_rocm0.json`
records the historical 22 ROCm0 unsupported base cases (21–41 and 77) and
declares all 25 new shared-trunk cases required to be supported. Any deviation,
including a newly unsupported shared case, fails comparison. `compare_exact.py`
requires complete listings, validates the declared support set and ALL hash,
requires all shared cases supported, and rejects missing or malformed dumps,
non-finite outputs, metadata or length mismatches, and any bitwise output
difference. Compare runs from the same backend path (CPU-vs-CPU or ROCm0-vs-ROCm0).
This preparation has not been built or run.

Nothing in this directory is a published row or evidence of a passing test.
