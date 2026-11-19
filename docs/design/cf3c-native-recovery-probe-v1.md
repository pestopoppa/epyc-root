# CF-3c explicit native recovery probe v1

`scripts/experiments/cf3c-binding/recovery_probe.py` defines
`epyc.cf3c.native-recovery-probe.v1`, an instrument control separate from the
24 quality cells. It does not change the failed `cf3c-binding-20261119`
profile, its sealed packet, or its fixed cohort
`14c79e10bade5909a5406b86ea72d91e44b66f830859044639b0c9c622cb5cc3`.
There is no native PASS or policy-quality finding from this code change.

The compiler verifies that cohort's content digest and copies the deep archive
into a distinct `native_recovery_control_v1` input. Arm A1-k12 and seed
195981119 are fixed before any native attempt. The prompt explicitly requests
the registered full-log peek before answering. It supplies neither the masked
observation nor an answer oracle. This control has `grade_cohort=False`; its
construction and native costs must be reported separately from the 24-cell
accuracy and cost denominators. Higher accuracy and lower tokens/wall remain
the quality-task directions; this control measures a binary recovery witness.

Install `capture_peeks(REPLEnvironment, archive)` before constructing the REPL,
so the native tool namespace binds the wrapped method. After `install_archive`,
set the yielded receipt's `log_path` to `state.history_log_path`. Keep the capture
active through the graph run and persist it in the native trial result. The
wrapper calls the original method unchanged and records only hashes and flags.
Recovery requires that the actual returned text contain the complete fourth
archived observation, from the exact registered log, with a file digest matching
the source writer's receipt. A retrieval counter or a model assertion alone is
insufficient. The capture belongs in the isolated graph child; it is not a
production monkey patch or an additional tool invocation.

The new profile must run the existing wire/custody validation before passing
the control OUTCOME and capture to `qualify`. The predicate requires the
version, control identity/arm/seed, first active selected-history receipt,
source-written archive digest, actual recovery witness, observed wire usage,
complete token costs, child exit, server teardown and no transport error.
It never reads `correct` or `answer`. This prevents task correctness from
selecting qualification while retaining independent instrument checks.

Integration is the next code task: a new profile/version and packet must bind
the probe module, persist its capture, run exactly this control in publisher
smoke, and retain the unchanged 24-cell quality schedule for the official row.
Use the existing 420-second/18-turn control allowance, one qualification attempt,
no retry, and the original stop-on-custody/transport/allocator-failure rules.
Only `publish_row.py` may execute its allocator-owned native smoke. Do not
republish or modify the old failed candidate to obtain a PASS.

Offline validation: 21 probe controls plus four existing profile controls pass.
The probe controls cover correctness independence (including missing grades),
actual returned-text/path checks, unchanged cohort input, wrong version/seed,
quality-cell substitution, missing active custody, wrong archive/log hashes,
missing wire/status/cost, child/server teardown and transport failure. These
are software controls, not evidence that a model recovered the archive.

## Integrated profile

`cf3c-binding/prepare_v2.py`, `launcher_v2.sh` and `spec_v2.json` seal the
new `cf3c-binding-probe-v1-20261119` row. Shared suite helpers activate the
control only for this profile's smoke. `recovery_probe_v1` is sent to the
private graph child only for the versioned control input; its peek receipt
is persisted in `GRAPH.json` and the trial OUTCOME. The ordinary 24 quality
cells carry no control flag. Wire validation completes before qualification;
archive return receipts, grade independence and separate cost denominators
retain the v1 contract. Source-backed offline regression covers capture
installation before REPL namespace binding as well as native log recovery.

## First integrated qualification — failed before generation

The separately sealed `cf3c-binding-probe-v1-20261119` smoke ran once on
CPUs 140–143 on 2026-11-19 and ended rc=1 at 11:58:55Z. Publisher refused
qualification. Its only trial was UNKNOWN before child creation:
`KeyError: 'repeat'` in the native child-environment builder. There were
zero native wire requests, zero quality cells and no recovery observation.
The private server exited cleanly; `child_exited=false` records that no
child was launched, rather than claiming a successful child teardown.
This is an integration defect, not evidence about model recovery ability.
The failed sealed packet is unchanged and will not be retried.

Repository code now builds the control with `repeat=0`, via
`recovery_control_row`. Its regression executes the real child-environment
builder on the prospectively compiled control. The source-backed graph
regression also confirms the capture is installed before REPL construction,
its bound tool uses the wrapper, and returned log content produces the
source-log witness. Together 27 suite/binding integration checks and 27
probe/profile checks pass; Ruff, shell syntax and diff checks pass. These
software checks do not establish native qualification. A new sealed profile
version is needed to execute the repaired row; the original 24 quality cells
remain unchanged and unrun.

Failure ledger: `/mnt/raid0/llm/tmp/compute-flags/dryrun/cf3c-binding-probe-v1-20261119/cf3c-suite-native/PARTIAL.json`, SHA-256 `760250e343b68112ba69d4570caabc570fe599447e11d2be69522037a986e184`.

Failed input seal: `255cd80a1e5df9afc0820b113a621263558f53baab73579cbaef2d4dd6c21452`.
