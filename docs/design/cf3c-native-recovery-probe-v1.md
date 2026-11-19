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
