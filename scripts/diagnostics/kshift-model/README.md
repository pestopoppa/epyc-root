# K-shift model harness repair

`fixture-bounds.patch` fixes the corpus slice guard in the diagnostic used by
`kshift-fix-model-test-20261119-r1`. The original source is
`/mnt/raid0/llm/tmp/kshift-fix-model-test-20261119-r1/out/src/tests/test-kshift-model.cpp`,
SHA-256 `73748c6be895d4728ffeca07b5e8f48d3c295166f70336397be35f2b24da088a`.

The original check requires only `prefix + probe + 8` tokens, while both slices
start after a 200-token header. With the default arguments it accepts 520 tokens
but accesses through token 711. The signed addition can also overflow, and
non-positive lengths are accepted. The replacement checks the actual slice
extent using subtraction and rejects non-positive lengths.

For a future separately registered row, apply the patch to its experimental
diagnostic source and place `fixture_bounds.h` beside `test-kshift-model.cpp`.
Do not alter the old row's inputs, build receipts or results. No production
kernel change is required.

Validation: `python3 -m unittest discover -s scripts/diagnostics/kshift-model`.
The test compiles and executes the C++ helper with undefined-behavior
sanitization, covering the formerly accepted short corpus, the exact boundary,
negative/zero lengths and integer extremes. The patch also passed
`git apply --check` against the original harness; the complete corrected harness
passed C++17 syntax checking with its pinned llama/ggml headers.

This fixes a reachable input-validation defect. It does not explain the recorded
weak negative control or the two translation top-1 mismatches. The original
`FUTILITY_INSENSITIVE` verdict and all thresholds remain unchanged. Before a
new model row, diagnose those independently: the original sensitivity statistic
averages 64 teacher-forced probe positions after corrupting only the first half
of the prefix. Attenuation by recent intact context is a hypothesis requiring
measurement, not an established root cause or permission to loosen thresholds.
