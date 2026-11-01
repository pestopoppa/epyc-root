# EVL38 manual CI verification (2026-11-01)

ROOT shared hermetic CI was manually dispatched after the EVL38 scheduled candidate-gate workflow was retired. GitHub Actions run [41307788637](https://github.com/pestopoppa/epyc-root/actions/runs/41307788637) completed `success` on `main` at `58737a05e8e6984620934eecc97691f522c52bb2`; its only job, `hermetic`, completed successfully. The final `gh run watch` receipt is retained here.

The EVL38-specific periodic workflow remains deleted. This verifies the shared hermetic workflow dispatch path; it does not establish a passing whole-candidate EVL38 readiness gate or readiness/promotion authority. The earlier scheduled run 41223677301 remains failed at reference validation and is documented in [`docs/reports/evl38-schedule-retirement-20261101.md`](../../../docs/reports/evl38-schedule-retirement-20261101.md).

Full/watch logs and original API captures remain at `/mnt/raid0/llm/tmp/codex-ni-ci-root-20261101/tests-run-41307788637.*`; `RAW-SCRATCH-PINS.sha256` binds their original bytes.

[no-belief: source CI verification; no readiness or measurement claim]
