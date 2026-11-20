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

## Prospective offset-matched calibration v1

Generate with `instrument.py SOURCE OUTPUT --offset-calibration`. The default
generator and historical r1 comparisons remain unchanged. Extra work occurs
after the historical measurements; it saves the original x1, x4 and round-trip
logits and performs two more independent reset/prefill/probe runs at each of
offsets 0, d and 4d. Together with each original fresh reference this gives
three fresh references at each offset, all with the same teacher-forced probe
tokens and consecutive positions. No query gap is introduced.

For each offset, emit fresh-reference pairs 01, 02 and 12, then compare fresh
references 1 and 2 against the saved corresponding shifted output (round trip
at 0, x1 at d, x4 at 4d). Reference/test direction stays explicit; KLD is
directional. Names are `cal_{0,d,4d}_{01,02,12,shift1,shift2}`. Existing
`control_offset_d` and `control_offset_4d` describe cross-offset variation;
these are separate from the new same-offset repeatability controls. Never
subtract their KLD or mask matching mismatch positions from shift results.

`calibration.summarize` requires every position of all 15 comparisons, rejects
duplicate/out-of-range indices, unknown calibration names, invalid token IDs,
nonfinite/negative KLD and margins. It retains all token IDs, margins, mismatch
indices and per-position KLD. Historical records are handled separately and
must retain their original evaluator; there is no replacement r1 verdict.

This protocol preregisters **diagnostic capture only**. A future row stops after
one candidate/baseline pair, or immediately on the first input, build, mapping,
decode, or record failure, with no retries or extra sampling chosen from the
outputs. Question: are differences reproducible at each matched offset, and
how do shift errors compare to same-offset repeats and cross-offset variation?
The expected effect is unknown; three fresh references per offset in one fixed
fixture characterize repeatability, not a population error rate. Completion is
`CALIBRATION_COMPLETE`, `qualification=false`, never PASS for H1–H3. No new
thresholds are selected here. Any later qualification must separately freeze
its offsets, models, caches, controls, KLD and top-1 gates, sensitivity rule,
sample size and stopping rule **before publishing that qualification row**.
Neither a stronger negative control nor offset-specific allowances may
retroactively repair the original `FUTILITY_INSENSITIVE` result.

Model-free tests execute the generated calibration block under UBSan, checking
all six fresh-prefill geometries, 15 comparison directions, preservation of
historical code and strict reduction failures. Synthetic logits establish code
behavior only. The existing `diagnostic_job.py` is deliberately unchanged:
before a calibration row, its owner must explicitly opt into this generator,
pin the new producer and reducer, save native position records and invoke the
strict reducer for each unit. Existing source-family wiring is `VB-YARN-E1`;
no native claim hook or planning-context canary is asserted by these tests.
