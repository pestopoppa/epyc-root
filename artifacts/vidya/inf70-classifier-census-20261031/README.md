# VB-SC75-CLS — implementing source `fc5688b802491af08243f57d2812937bcc3efa56` — Gitproof

## Source change

- Original task: `VB-SC75-CLS` in `handoffs/active/vidya-belief-substrate-program.md` (owner workspace-ec under EVL-47).
- Maintained source commit: `fc5688b802491af08243f57d2812937bcc3efa56` (`feat(vidya): preserve SC75 classifier identity`).
- Source parent: `471ba76dc0f15bfe00159ea1f17e715216919b7a` (fresh `origin/main` fast-forward before the source commit).
- Scope: `scripts/inf70/harness1/classify.py`, `client.py`, the existing SC75 writer `scripts/vidya/adapters/inf70_serving_arm_capture.py`, and their two focused test modules. Classifier verdict rules, metric values, protocol, source class and shared grade are unchanged.

The maintained classifier now declares `inf70-classify.v1`. The client explicitly records `token_source="synthetic-ids(uniq/top/run vacuous)"` at the call passing `list(range(npred))`, and records the classifier ID on successfully classified rows. HTTP-error rows do not assert either field. The existing writer emits a deterministic `extra.coherence_classifier` census keyed by the exact declared classifier and token-source values. Missing, blank, malformed or partial fields are `UNREPORTED`; no field is inferred from paths, dates, verdicts or archived artifacts. The existing strict reader and ingest path preserve the native census. This adds no grading ladder and does not backfill or rewrite prior records.

## Test evidence

The focused suite ran the real harness client in a model-free subprocess with a local `urllib` stub, then inspected native rows, emitted the sidecar, projected it through the strict reader and ingested it through `cli.py ingest inf70-arms`:

- `tests/vidya/test_inf70_serving_arm_adapter.py`
- `tests/vidya/test_inf70_harness_sc75_hook.py`
- Result: **45 passed in 1.00s**.
- `test-output.txt` is the captured output. The `SC75 capture refused ... 32400s ... backfill` line is the expected existing refusal control, not a test failure; the run exited 0.
- `pytest-process.json` and `client-process.json` preserve PID, start time, `/proc` start ticks, initial RSS and post-exit absence evidence.
- Run used actual `fcntl.flock` `/mnt/raid0/llm/tmp/compute-flags/prep-locks/36-37.lock`, CPU affinity `36-37,132-133`, `OMP_NUM_THREADS=1`, an 8 GiB address-space cap and a 900 s timeout. No inference/server/model was used.
- Test log SHA-256: `e13d6838fee3e1690af994268eac31cfa5591e106039900989ede8575ffb517e`.
- Candidate patch SHA-256 at test time: `7144bd49a6117c119c2919b30102a0e02816c9c4e18fb1ab64d37a1d2b1f9dd7`.

The stubbed integration produced 23 successful rows with the exact identity pair and one controlled HTTP-error row without identity metadata. The sidecar contained `UNREPORTED/UNREPORTED` for that row and the exact pair for the 23 successful rows. Strict projection and ingest preserved the census; `claim_tuple.grade()` remained `Witnessed/Attested` for the fixture.

## Legacy evidence scan

The maintained reader's `rows_for_run_dir()` enumerates `Path(run_dir).glob(f"*{SIDECAR_SUFFIX}")`; `SIDECAR_SUFFIX` is literally `.belief_measurements.jsonl`. A fresh read-only scan used that exact direct-child pattern in every `runs/` directory below `/mnt/raid0/llm/tmp/inf70/agents`, plus `**/*.rows.jsonl` to count native historical rows. A separate scan used the same declared sidecar suffix over the authorized checkout's `artifacts/` tree. Results: 29 `runs/` directories; 403 native row files; 9,654 JSON rows parsed; zero matching sidecars in the producer tree and zero sidecar-suffix files in checkout `artifacts/`; zero rows with a `classifier` key; zero rows with a `token_source` key. No other filename pattern was substituted for the producer/consumer contract. The original rows cannot satisfy the identity contract, so no archive reconstruction or sidecar backfill was attempted.

## Original acceptance remains open

The source/test work is complete and published as code, but the original `VB-SC75-CLS` checkbox must remain open. Fixture execution is not an original native run. Acceptance still requires a future genuine producer run to write the classifier and token-source declarations and for its producer-authored sidecar to pass the strict reader and a real `inf70-arms` ingest. No source-task checkbox was changed here.

`HANDOFF-DRAFT.md` and `SOURCE-TABLE-DRAFT.md` are preparation for MAIN to apply. They are not edits to the original handoff, source table, or index.
