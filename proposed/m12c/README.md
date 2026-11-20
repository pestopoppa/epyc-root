M-12c receipt-producing BEAM reader launcher
==========================================

`payload/research/scripts/benchmark/run_beam_reader.py` is an opt-in launcher,
not an installed change to the research repository. It prepares one arm, then
executes its materialized questions with a fixed reader. `reader.json` retains
the existing `results.beam` layout for `judge_beam_run.py` / `score_beam_run.py`.
It emits no belief tuples and does not certify a benchmark result.

Preparation runs OUTSIDE a grant, before publishing a compute row:

```bash
PYTHONPATH=/mnt/raid0/llm/epyc-inference-research/scripts/benchmark \
  python run_beam_reader.py --prepare-only \
  --dataset /mnt/raid0/llm/data/eval/beam/data/100K-00000-of-00001.parquet \
  --dataset-sha256 c0519be25907005ba873c927c50877471d550873039d96c041554d0075a78ace \
  --arm rag --model READER_SERVER_ID --output SCRATCH_RUN_DIR
```

Repeat preparation for full and trace with the same reader and top-k (default
10 pair chunks). Preparation verifies the sole parquet source before and after
extraction, requires both roles in every conversation, materializes retrieval,
and records the actual adapter settings. All arms receive the same closed-book
instruction/template; only the context contents vary. The shared template hash
excludes history/question substitutions; full rendered prompt hashes are stored
separately for every question. A receipt binds source-file hashes, dataset digest,
roles/counts, chunking, retrieval budget/unit, generation settings, and question
count. The trace backend must work during preparation; no fallback is installed.

The future compute-row launcher invokes only execution:

```bash
PYTHONPATH=/mnt/raid0/llm/epyc-inference-research/scripts/benchmark \
  python run_beam_reader.py --output SCRATCH_RUN_DIR --reader-url http://SERVER
```

Execution checks the prepared prompt digest and small source files, then sends
the recorded parameters to `/v1/chat/completions`. It verifies `/v1/models` matches
the configured server identity. That identity is an alias check, not a model-weight
or kernel-content proof; those proofs belong in the published serving recipe.
Answers, finish reasons, and completed counts are checkpointed after every request.
A failure marks the receipt failed and preserves partial answers. Existing output
directories cannot be prepared over; started/failed runs cannot be silently rerun.

Validation: 41 offline tests, real synthetic parquet input, real full/RAG adapter,
stub trace backend and HTTP transport. The synthetic three-arm receipts clear the
checker at research `c9aac169b:scripts/benchmark/beam_prerun_checklist.py`; mismatched
budgets and truncated answers fail their respective items. No real model, trace
service, GPU recipe, floor score, or measured synthesis cap was validated. The
historical checker alone does not require completion or source/prompt bindings.
Use `admit_beam_runs.py` below for new runs; it validates those bindings before
invoking the unchanged checker. Direct use of the historical checker omits this
admission check.
The 2048-token adapter cap remains a parameter, not measured sufficiency.

Reproduce (scratch interpreter has pyarrow 26.0.1 / pytest 9.2.0):

```bash
PYTHONPATH=/mnt/raid0/llm/epyc-inference-research/scripts/benchmark \
  /mnt/raid0/llm/tmp/episodic-memory-integrity/m12c-venv/bin/python -m pytest \
  --noconftest -p no:cacheprovider \
  proposed/m12c/payload/research/scripts/benchmark/test_run_beam_reader.py -q \
  --basetemp=/mnt/raid0/llm/tmp/episodic-memory-integrity/m12c-tests
```

`source-pins.json` identifies the external dependencies used in this test, without
copying their source files. Runtime receipts capture the source actually imported.


Completed-run admission (M-12c-RECEIPT-ADMISSION)
----------------------------------------------

The launcher now records `reader_sha256` only after all answers are checkpointed.
The new stdlib-only `payload/research/scripts/benchmark/admit_beam_runs.py`
requires exactly one full, rag and trace run, all complete with matching question
sets and reader generation settings. Before calling the pinned eight-item
checker it verifies source/prepared-question/reader digests, unique question
IDs, per-question prompt hashes, shared template hash, every prepared field in
each saved answer, recorded generation parameters and finish reasons, reader
identity, and summary truncation count. Each directory must have exactly one
`scored-beam-*.json` summary. Incomplete or malformed artifacts fail closed.

Run offline, outside the grant (the unchanged checker rehashes the dataset):

```bash
python payload/research/scripts/benchmark/admit_beam_runs.py \
  --arm full=FULL_RUN --arm rag=RAG_RUN --arm trace=TRACE_RUN \
  --min-max-tokens MEASURED_REQUIREMENT \
  --expected-dataset-sha c0519be25907005ba873c927c50877471d550873039d96c041554d0075a78ace
```

Exit 0 requires integrity PASS and all eight checklist items PASS. Integrity
PASS alone cannot override a checklist failure. The checker's source is read
from research git object `c9aac169b:scripts/benchmark/beam_prerun_checklist.py`;
its blob is pinned in `source-pins.json`, without copying the file. Run both
`test_run_beam_reader.py` and `test_admit_beam_runs.py` with the interpreter and
PYTHONPATH shown above to reproduce all 41 tests.

This checks consistency of retained artifacts; it does not authenticate them or
prove serving-binary/model contents or judgment provenance. It rejects old runs
without the new native bindings; never backfill their missing receipts. The
measured synthesis cap, real three-arm qualification and the parent M-12c
checklist remain open. Deployment in research is still owner integration; these
are root-lane opt-in tools and no external repository was edited.
