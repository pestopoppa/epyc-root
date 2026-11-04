# R23-62 runner preparation — NON-READY

These are development artifacts, **not a qualified or runnable measurement launcher**. The `--execute` path always refuses after the host-uptime check. Do not remove or bypass that refusal to collect measurements. No live benchmark has exercised this code. `run_one` and `campaign` are incomplete building blocks, not independently authorized entry points.

From this directory, run the bounded, model-free checks:

```sh
python3 r2362_runner.py --selftest
python3 test_r2362_runner.py -v
python3 -m py_compile r2362_runner.py runner_parts.py prepare_plan.py screen_strict.py test_r2362_runner.py
```

The five fixture tests use mocks and owned short-lived Python children; they do not load a model, acquire a compute claim, or run inference. They exercise scheduling, a parity abort, incomplete rows and child cleanup; they do **not** validate real server behavior, counters, linkage, performance, or the full experiment. `prepare_plan.py` prints a **non-executable** recipe-derived plan and contains scratch paths that require review. `screen_strict.py` validates telemetry structure and emits `DIAGNOSTIC_ONLY`; it never authorizes measurement or substitutes for a sanctioned witness.

Before any runnable version exists, finish and test the real execution integration: complete source/build and all-loaded-DSO identity and close-of-window checks; verify model-shard digests; prove claim acquisition and ownership before and after every arm; bind the sanctioned inference and residual-load witnesses; verify process THP and knob controls in live readbacks; collect eligible accounting; pre-register the estimand and stopping/analysis rule; exercise full parity and cleanup against controlled real binaries in a valid claimed window. Pin every referenced helper and workload, because the present scaffold imports mutable files from `/workspace/repos/epyc-inference-research/` and a historical client from `/mnt/raid0/llm/tmp/inf70/agents/harness1/`. The latter has scratch-relative dependencies and is not a durable instrument. Review the returned output scope: this is a prospective UD-model diagnostic, not a reconstruction of the old window.

The current 48-thread recipe cannot meet the existing prefill validator's 72-core eligibility threshold. See [ACCOUNTING-DECISION.md](../ACCOUNTING-DECISION.md) for the unresolved measurement-authority choice; no threshold has been changed. The sampled host uptime exceeded one week, requiring the applicable reboot and host-health preflight before a trusted run. The scaffold's live accounting call uses the 96-thread prefill validator unchanged and therefore must not be treated as a working 48-thread gate.

The proposed, unratified 48-thread accounting fixture is tested with `python3 proposed48_fixture_test.py`; it is synthetic-only and cannot authorize a run. See [PROPOSED-48-ACCOUNTING.md](../PROPOSED-48-ACCOUNTING.md).
