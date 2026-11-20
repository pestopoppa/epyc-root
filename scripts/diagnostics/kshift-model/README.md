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

`instrument.py` adds diagnostic output to the SHA-pinned r1 source: one record
per probe position with KLD, both top-1 token IDs and both top-two logit margins.
It retains the original aggregate calculation and adds fresh-offset-d and
repeat-offset-0 controls, plus tail-key-shift and dropped-prefix controls.
The latter controls test other perturbations; they cannot retroactively satisfy
r1's half-prefix sensitivity gate. `test_instrument.py` executes the actual
instrumented comparator on known synthetic logits under UBSan, checking KLD,
ties, margins, token IDs and aggregate preservation.

`diagnostic_job.py` compiles this standalone harness and runs exactly the native
Qwen3 f16 candidate/baseline pair through a compute row. Smoke compiles/links
without model inference. Small input and library hashes are pinned; model
weights are checked before publication and never hashed in the grant. Runtime
mapped-library paths are verified for both libllama and libggml-cpu. Output
contains complete position records and first/last-eight-position KLD summaries.
This is exploratory diagnostic evidence, with no H1–H3 qualification verdict.

The original diagnostic row `kshift-diagnostic-20261120` aborted at its
wrong-query-offset control: it requested position 512 after cached position 447.
The pinned decoder requires the next position to equal the cached maximum + 1.
A successor uses `negctl_tail_key_shift_64`: prefill at zero, shift only the
last cached key from 447 to 511, then probe at 512 through the normal consecutive
path. Earlier keys stay at 0–446. This perturbs both the tail key and query
positions, so it is **not** a pure query-offset experiment and retains a new
scenario name. Its sensitivity is unknown until measured. The dropped-prefix
control starts an empty cache at position 448; the decoder permits a nonzero
starting position when no earlier sequence position exists.

The position regression executes the generated control block and actual
`probe_logits` lambda with a model-free decoder stub implementing the pinned
consecutive-position check. It verifies cache geometry and 64 consecutive
probe positions for both controls. Restoring the old gap must fail with the
observed decode refusal. Comparator and corpus-boundary tests remain in place.
Old row inputs, results, and acceptance thresholds are unchanged; publish any
successor separately, with the new control explicitly described in its rule.
