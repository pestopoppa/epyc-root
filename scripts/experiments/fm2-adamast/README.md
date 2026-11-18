# FM-2 fixed-catalog grading pilot

This packet applies AdaMAST's 14-code MAST taxonomy once per trace to a frozen,
stratified sample of Claude and Codex transcripts. It uses the previously selected
Qwen3.8-27B Q8_0 judge and pinned CPU v10 image. It produces descriptive diagnoses;
it does not measure task accuracy, judge faithfulness, or the benefit of fan-out.

Prepare inputs **before** publishing, using an existing AdaMAST checkout containing
commit `3c83d81c85937f5e8911fd96daa2ca38c1ad2585`:

```bash
bash scripts/experiments/fm2-adamast/prepare.sh \
  /mnt/raid0/llm/tmp/coordination-and-churn-pipeline/fm2 \
  /mnt/raid0/llm/worktrees/rtg34-fm-20261110-scratch/adamast-upstream
python3 scripts/coordination/rowflow/publish_row.py \
  /mnt/raid0/llm/tmp/coordination-and-churn-pipeline/fm2/spec.json --smoke-now
```

Preparation freezes and normalizes the sample, checks model bytes, snapshots the
pinned runtime modules and local transport patch, and seals inputs and code.
The prepared directory is immutable: preparation refuses a sealed packet. A
successor needs its own row ID and input declaration. Never launch `job.sh`
directly; the keeper owns full runs.

The launcher starts one private CPU server inside the granted CPU set. It proves
listener ownership, captures mapped library identities, and journals exact request
and response bytes. SDK and judge retries are disabled. A journaled request is not
reissued after interruption. Smoke uses a shorter trace/output cap and writes only
to the publisher's isolated native result directory; it cannot complete the pilot.

Native results are `out/results.jsonl`, per-trace `out/units/*/receipt.json`, and
`out/summary.json`. The summary retains planned, attempted and valid denominators
by stratum, failed response counts, and per-code Wilson 95% intervals. All trace
receipts, or more than 25% failures after at least eight attempts, end the run.
Deadline and STOP preserve partial results. Inspect the summary when filing:
engine completion alone does not establish successful grading.

The crosswalk contains proposed symptom overlaps and explicitly unmapped codes.
It is not a validated equivalence between MAST and the F-series ledger. Outcome
fields are stripped, but the observable trajectory is retained; the pilot has no
independent outcome oracle or human gold labels. Belief projection and a real
planning-context canary remain tracked by `VB-FM2-ADAMAST-WIRE`.

Run the six synthetic transport and summary controls without inference:

```bash
/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B \
  scripts/experiments/fm2-adamast/test_pilot.py
```

Set `FM2_ADAMAST_CHECKOUT` if the pinned source commit lives in a different clone.
Test scratch stays under this handoff's temporary root and is removed on exit.

## Prospective diagnostic capture

A fresh prepared packet can activate capture with a sealed
`code/belief-selection.json` listing its predeclared trace IDs. Include it and
the producer in `SOURCE.sha256` before publication. The producer writes
`belief-begin.json` before each request, with its input and runtime identities.
An existing begin marker conservatively ends that unit as interrupted; it
never issues a replacement request. Smoke exercises this boundary with a
separate scope and remains ineligible for official projection.

The explicit Vidya source `fm2-adamast` verifies the pre-call marker, source
seal, grant, original request and response, and complete normalized diagnosis.
It reuses the pinned AdaMAST parser and regenerates the prompt from the frozen
trace and taxonomy. Failures and partials emit no numeric diagnosis. A valid
assigned-code count describes one judgment through the shared diagnostic
observation carrier, without accuracy or faithfulness warrant.

After an official native unit completes, use its receipt with
`belief_canary.py --receipt <packet>/out/units/<unit>/receipt.json --scratch
/mnt/raid0/llm/tmp/vidya-belief-substrate/fm2-current`. The canary uses an
isolated ledger and checks the exact `coordination.fm2` claim, its limitations
and exclusion from the reader reliance whitelist and unrelated consumers. A production
coordinator consumption point remains a separate acceptance requirement in
`VB-FM2-ADAMAST-WIRE`.

The focused controls are `test_pilot.py` and
`tests/vidya/test_fm2_adamast.py`; run them with the prepared runtime Python
containing the OpenAI transport dependencies. Set `FM2_TEST_ROOT` under this
handoff's scratch and `FM2_ADAMAST_CHECKOUT` to a local clone containing the
pinned AdaMAST revision when needed. They make no model calls.
