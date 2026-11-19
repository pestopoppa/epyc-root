CAFE-4 CPU modes native control row
===================================

`df2-cafe4-modes-native-cpu-20261119` runs the qualified CPU modes executable
in place; no binaries, model weights, source trees or historical logs are copied.
Its [input manifest](inputs.json) binds executable and library hashes from the
existing CPU build receipt, the exact v10 commit and diagnostic patch, generated
candidate identity, model content receipt and unchanged full stat, and runtime
files. Input preparation verified these before publication. Runtime checks
small artifacts and model stat, never model-weight hashes.

Question: with the original one-prompt numerical rule, do verify widths 2 and 3
each satisfy the positive rollback control and explicit failing fault CLI?
The native program retains its built-in short fixed-prompt conversion as part of
model initialization; this row introduces no corpus preparation or tokenization
job. The question is diagnostic behavior, not throughput or sampled acceptance.

The four predeclared cases are width2 normal, width2 fault, width3 normal and
width3 fault, all with `-ngl 0`. Each program invocation internally executes
matched off/observe/target-fault controls, native MTP drafting, strictly partial
acceptance (diagnostic cap), rejected-suffix removal and replay. The parser
requires finite numeric values, native mode1/mode2 and rewind witnesses,
nonfault errors at most the original baseline plus 1e-5, fault deviations
strictly above 10 times that tolerance, and exact intended exit/result text:
normal rc0 with PASS; explicit fault rc1 with FAIL injected-fault. Arbitrary rc1
is rejected. Insufficient proposals and failed numerical or provenance controls
are UNKNOWN, not a relaxed threshold. Stop at the first failed case or after
all four pass; no repeated search over widths or tolerances.

During each child process the runner captures actual model and all five local
llama/ggml mappings. A foreign library refuses the run. It preserves the inherited
row environment and CPU affinity, binds the live official `.grant` by digest for
scheduled execution, sets this build's `LD_LIBRARY_PATH`, and manages only the
child PID it created. STOP/deadline terminates and reaps that child, escalating
to SIGKILL after ten seconds. Per-case logs, hashes, controls, mapping receipts,
cutoffs and child exits are kept in scratch. Unknown cases are retained.

The four-CPU smoke qualifies only actual native model/library mapping and a clean
STOP. It does not establish rollback correctness or fault sensitivity. Results:
`/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-20261119/RESULT.json`.

Five model-free regression tests pass: intended normal/fault exits; arbitrary
errors; nonfinite and failed numeric controls; missing native witnesses and
invalid partial acceptance; duplicate and contradictory outputs. Run:

```bash
python3 -m unittest discover -s scripts/diagnostics/cafe4-native -p 'test_*.py' -v
```

The existing CAFE-4 prospective source registration and `VB-SERVING-DF2` task
cover this producer. It is not yet belief-wired: native token/replay identities
and a shared-carrier projection plus planning-context canary remain absent.
This CPU diagnostic cannot close the parent CAFE-4 box; GPU `-ngl N` validation
and any numerical failures still require their own evidence.

Publication smoke PASS (2026-11-19): cores 116–119, first native model/library
mapping accepted, clean STOP rc75 at 04:49:52Z. Receipt `/mnt/raid0/llm/tmp/compute-flags/dryrun/df2-cafe4-modes-native-cpu-20261119/PASS.json`;
SHA-256 `20eb5ba67fb7987b433675eece92f118df2292a102ef46e53c8b3bc3cd0821d2`. Full native control verdict remains pending.
