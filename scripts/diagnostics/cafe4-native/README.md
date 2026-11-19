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

Scheduled CPU verdict (2026-11-19)
----------------------------------

**INCONCLUSIVE / UNKNOWN**, scheduled rc2 at 04:50:38Z. The first
width-2 normal case exited rc2: `off_error=observe_error=0.907920361`
exceeded the original `tolerance=0.743863867` (lower error is better).
`off_observe=0`, `fault_error=18.5714054`, `fault_observe=18.6988792`.
The internal target-fault differences exceed 10 times tolerance, but do not
substitute for the explicit fault CLI case, which never ran.

Native witnesses include width2/accepted1, selected1/faulted1, draft rewind
and target modes 1/2. The model and all five local libraries were mapped;
there was no cutoff and the child was reaped. The first failed numerical
control correctly stopped the row: width2 explicit fault and both width3
cases are unexecuted. The receipt binds the grant, inputs, build and model;
its per-case log digest was checked when filing.

Existing evidence, referenced in place:
- `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-20261119/RESULT.json`, SHA-256 `5c3abc2acfb29d08d8a231d191e34abb3905942e8e13b745eb19d7dd0354a100`.
- `/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-20261119/runs/793b587812e749499b8d6e9d1aa82418/width-2-fault-0.log`, SHA-256 `d1fe8cc15f0ca91833a6c6b7346d3dd0934fef472f08e85ef517941b18adbe98`.
- `/mnt/raid0/llm/tmp/compute-flags/grants/df2-cafe4-modes-native-cpu-20261119.ended`, SHA-256 `a21ca4dd5ee56ffa05affe5604c3e955a535bd5418472d6f117976729e927d32`.

Filing record: `/mnt/raid0/llm/tmp/compute-flags/filing-done/df2-cafe4-modes-native-cpu-20261119.verdict.json`.

Keep the original numerical rule. Before any numerical rerun, diagnose the
cold-prefix reference versus matched replay geometry; the result does not
establish the cause of the excess error. Next executable task is the already
identified HIP qualification symbol-predicate repair with regression tests;
GPU native controls require qualified HIP artifacts. Parent CAFE-4 remains
open. No GPU, performance or complete rollback/fault claim.
[no-belief: inconclusive single-prompt diagnostic; producer not belief-wired]
