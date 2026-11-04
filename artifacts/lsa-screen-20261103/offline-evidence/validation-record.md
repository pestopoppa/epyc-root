# P4 offline validation record

The following is a transcription of the actual terminal output returned by the execution tools; it was not captured to a file when the test ran. The exit code was 0. The region lock held sub-quarter physical cores 0–1. No model or GPU was run.

```text
[region-lock] acquiring regions [] as role='build' (timeout_s=2.0) …
[region-lock] held sub-quarter cores {q0: [0, 1]}
.................
```

The execution tool then returned this second chunk:

```text
.............                                           [100%]
P1-A carrier invariants: 3 tuples from 1 source kinds checked (byte identity / grade invariance), 0 violation(s)
30 passed in 4.22s
```

The actual command was:

```text
/workspace/repos/epyc-orchestrator/scripts/region-lock run --cpu-list 0-1 --role build --timeout-s 2 --tag lsa-evidence-offline -- taskset -c 0-1 /mnt/raid0/llm/epyc-inference-research/.venv/bin/python -m pytest -q /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root/artifacts/lsa-screen-20261103/offline-evidence/test_pilot_projection.py /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/research-lsa/tests/lsa_moe/test_pilot.py /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root/tests/vidya/test_ingest_sources.py::test_every_source_is_a_cli_choice_and_the_literal_list_does_not_drift /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root/tests/vidya/test_ingest_sources.py::test_every_wired_adapter_projects_through_a_registered_projection
```

This includes the synthetic pilot fixture's producer-time envelope writer, strict reader, two-row CLI ingest and planning assertion; the actual pilot early-failure hook; tamper, partial, invalid identity and duplicate-event refusals; prospective unit-wrapper exit classifications; four research pilot tests; and the two specified registry tests. The test's subprocess CLI stdout and the full returned planning-context object existed only in process memory and were not saved. The successful assertions establish two projected rows, no refusals and both timing values in the ready context, but the exact CLI response and full context cannot be recovered. The copied `pilot-canary/` directory is the original synthetic pytest fixture and private ledger/read log, not a live pilot. Its files retain original absolute paths; relocation is an archive, not a new attestation.

`source-snapshot/manifest.json` hashes byte-checked copies captured after the test. No source digests were captured at test time, so these copies cannot independently prove the exact bytes used for the run. `baseline-coverage-proof.json` records the HEAD source/test contents for the separate coverage-set failure; neither `dtap-crm-pair` nor `ak-r18-symbols` appears anywhere in the baseline test while both appear in its baseline source registry.
