# OBS-1 supervisor observation contract — evidence capsule

This capsule binds the accepted OBS-1 implementation to the final hosted source-correctness run. It is not a native-runtime, deployment, or belief-measurement receipt.

## Final hosted validation

- Workflow: `.github/workflows/obs1-supervisor-contract.yml` on `ubuntu-latest`, contents read, pinned Actions, 15-minute ceiling.
- Command: `PYTHONPATH=tests python -m pytest -q --junitxml=... tests/test_observer_contract.py scripts/coordination/tests/test_bus_supervisor.py`.
- Result: **38 passed, 0 failed, 0 errors, 0 skips** in 124.41 seconds; exit code 0.
- Candidate source commit: `70d01ac9982a6c95a5645eb8cff10174b0d24a35`.
- Run: [41279642985](https://github.com/pestopoppa/epyc-root/actions/runs/41279642985).
- `green/` preserves complete pytest stdout, JUnit, dependency-install stdout, exact source commit and all five source SHA-256 values. `run-metadata.json`, `job-metadata.json`, and `artifact-custody.json` are filtered GitHub API records; the run id, job outcome/steps, and artifact download metadata are retained. The 12-digit job database id is omitted because the repository PII hook flags that numeric shape.

## Source changes

The contract folds heartbeat identity and independent process observation into present/absent/unobservable and exposes uniform `observe` status codes. When either channel is unavailable, the bus and reference backfill callers suppress both signal and launch; the shared `observer_guard.sh` fold remains unchanged. Registry contract v1 and real stand-in coverage include disagreement, partial blindness, action suppression, and genuine absence.

- Bus adoption commit: `7f08d858b2f137411ce31c579b103456abe57554`.
- Reference backfill caller correction: `1d26cde2a6032f6aec14760867d891d93397e72c`.
- Final source-candidate patch: `candidate-source.patch.b64` (base64 preserves the exact whitespace-bearing patch); lineage and promotion are in `source-provenance.txt`.

## Preserved failed attempts

- Run `41278943836`: invalid workflow context (`runner.temp` at job-level env); zero jobs, no tests or artifact. Exact annotation is in `red/bootstrap-run-41278943836.md`.
- Run `41279068746`: **36 passed, 2 failed**. It exposed the genuine backfill action-under-partial-blindness defect and the missing hosted inert-kernel/PyYAML fixture closure. Original pytest stdout and JUnit are retained byte-exact as base64 under `red/41279068746/`; `red/raw-evidence-sha256.txt` records hashes of decoded bytes.
- Run `41279418549`: **37 passed, 1 failed**. The backfill correction passed; hub fixture still lacked PyYAML for its inert manifest. Original pytest stdout and JUnit are retained byte-exact as base64 under `red/41279418549/`; `red/raw-evidence-sha256.txt` records hashes of decoded bytes.

## Local R6 attempt

The R6 refusal receipt is preserved separately at `/tmp/obs1-r6-receipt.json`. The attempt was refused before test start because selected CPUs intersected active whole-host grant `codex3-kvu-lb1d-t96-quiet-r1-20261031`; no PID was started. This is distinct from and does not reduce the green hosted result.

## Scope

No live supervisor/backfill process was started, stopped, or reloaded. No process was signaled. The CI-only hub fixture uses a temporary empty kernel path and private listener/manifest fixtures; it invokes no production endpoint or model service.
