# IFBench grant lookup repair (2026-11-19)

CJ-6a and CJ-6e both failed before cohort exposure because their clean environment explicitly supplied an empty grants-directory variable. Python's getenv default applies only to an absent key. Consequently both workers looked for a relative grant file under their working directory.

The patch gives each launcher a nonempty default before crossing env -i, preserves explicit grants/flags overrides through sudo, and makes each worker fall back from an empty value to the flags directory's grants subdirectory. Missing/empty grant files still fail closed; grant bytes remain captured and checked throughout generation. The first arm uses successor id codex-ifbench-cj6a-27b-v5-20261119. The second arm's runtime is repaired but its successor must be published in a later turn.

Run test_preflight.py to test the actual runtime files referenced in qualification.json. The tests execute the actual AST preamble only through grant validation and replace the final job invocation with env when testing the launcher's clean environment. They never load the model, read the cohort or request inference. Both workers are tested with absent/empty grants roots, custom roots and missing/present grant files; both launcher bridges cover default, empty, flags override and grants override.

qualification.json binds the runtime files and regression result; repair.patch records only the delta against the SHA-256-bound existing workers and launchers. Source trees, model weights and logs remain at their original paths. Benchmark scores remain UNKNOWN until a full run completes. The initial successor smoke caught an outdated worker entry in RUNTIME-INPUTS.sha256; both runtime seals and their outer V3 seals were then refreshed before republication.
