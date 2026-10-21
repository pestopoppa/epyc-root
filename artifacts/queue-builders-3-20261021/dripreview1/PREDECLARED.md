# D-RI-PREVIEW-1: predeclared run spec (frozen 2026-10-21 BEFORE any model run)

Task text: `handoffs/active/repl-session-memory-maturity.md` D-RI-PREVIEW-1 and the D-h comparator note (intake-2245#record).
Fixture and scorer (unchanged): `epyc-orchestrator` `tests/fixtures/repl_preview/batch50.json`, `scripts/benchmark/repl_preview_fixture.py`
(`classify()`), `tests/unit/test_repl_preview_fixture.py`. Driver: `scripts/benchmark/run_repl_preview.py`; filler job:
`scripts/benchmark/dripreview1_filler_job.sh`. The driver's defaults equal the numbers below and it writes the flags it ran with into the result.

## Renderings (cells per role)
`current` (today's `get_state()`: name, type, `repr[:80]`, no true length), `bounded_k3` (`name = type(len=50, first 3: [...], last 3: [...])`),
`half_first25` (the test case itself: first 25 items shown, length not stated).

## Role set (decided, with the reason)
**ONE role: `worker_general`, served by the GGUF `Qwen3.6-35B-A3B-MTP-Q8_0.gguf`.** `orchestration/model_registry.yaml` binds `worker`,
`worker_general`, `worker_math`, `worker_explore`, `worker_summarize` and `frontdoor` to this single GGUF on one server (alias_of frontdoor,
2026-09-22 lineup). Running them as separate roles would be six copies of one measurement presented as six, so the table is per
(role = that GGUF) x rendering and the finding is worded for "the served worker model", never "the worker roles". A second row appears
only if the lineup gains a distinct worker GGUF (the driver takes repeated `--role NAME=URL@PID`; no code change).

## Sample size and sampling
n = 30 samples per cell, 3 cells, 90 calls. Temperature 0.7, seeds 1000..1029 (same seeds in every cell), max 700 output tokens,
`enable_thinking=false`, `cache_prompt=false`. One fixture batch (deterministic; the fixture has no randomness), so the 30 samples
measure sampling variance of the model on this one batch, NOT variance across batches: the result generalises to "this batch" only.
n=30 can distinguish correct-rates that differ by about 0.35 or more between cells (Fisher exact, 80% power at 0.5 vs 0.85); smaller
differences are reported as not resolved.

## Execution of the reply
The reply's python code block runs with `batch` bound in an isolated `python -I` child (10 s, empty env); `FINAL(x)` sets the answer.
A reply with no code block falls back to its last integer. A crash, timeout or missing FINAL counts as `no_answer` (reported, never
dropped from n). Classification: `repl_preview_fixture.classify(answer, fixture, rendering)` -> correct / blind_rule_fit / retyping_loss
/ other.

## Decision rule (report only)
The table (counts per class, n per cell) is filed as is. No threshold turns it into an adopt/reject verdict: D-h's renderer decision is
the operator's, and this run is the comparator evidence it asked for. Statements allowed: per-cell counts and rates with n; the
difference `bounded_k3 - current` in correct-rate with a Fisher exact two-sided p; "not resolved" when the difference is under 0.35.
A cell where `no_answer` exceeds 20% is flagged as a driver/prompt failure, not a model result.

## Host and window
Private llama-server, CPU store build `/mnt/raid0/llm/kernels/production/cpu/llama-server`, `-np 1 -c 8192 --jinja -ngl 0`, port 9461,
taskset on the granted region only. Correctness-class (no timing claim), so it does not need a quiet host. Estimated 15-25 min plus load;
resumable per sample.
