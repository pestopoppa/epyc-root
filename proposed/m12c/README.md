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

Validation: 10 offline tests, real synthetic parquet input, real full/RAG adapter,
stub trace backend and HTTP transport. The synthetic three-arm receipts clear the
checker at research `c9aac169b:scripts/benchmark/beam_prerun_checklist.py`; mismatched
budgets and truncated answers fail their respective items. No real model, trace
service, GPU recipe, floor score, or measured synthesis cap was validated. The
historical checker does not yet require a completed receipt or validate its new
source/prompt bindings; tighten that admission before relying on it for a new run.
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
