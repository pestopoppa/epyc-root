# Pilot preflight validation

The actual captured output and exit code are `preflight-test.stdout` and `preflight-test.rc`. `preflight-test-before.sha256` and `preflight-test-after.sha256` were taken immediately around this run and match. `preflight-snapshot/` preserves the tested pilot and test sources plus the accompanying README. No model was loaded and no GPU work was performed.

Command:

```text
/workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list 0-1 --role build --timeout-s 2 --tag lsa-preflight-offline -- taskset -c 0-1 /mnt/raid0/llm/epyc-inference-research/.venv/bin/python -m pytest -q /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/research-lsa/tests/lsa_moe/test_pilot.py::test_preflight_refuses_futile_fit_before_model_load /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root/artifacts/lsa-screen-20261103/offline-evidence/test_pilot_projection.py::test_actual_pilot_terminal_failure_hook
```

Both infeasible fit cases assert the loader was not called and the native failure record remains invalid with no captures or projection steps. The third check covers the actual early-failure evidence hook. The actual teacher pilot has not run.
