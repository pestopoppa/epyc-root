# SPEC-GRAM.3 r2 executable prep packet (PROPOSED)

Fresh r2 proposal `codex-ni-specgram3-llg101-cpu-r2-20261101` preserves the original scientific task text, denominator, evaluator, result schema, window, and adoption state. It preserves the r1 `FAILED-RUN rc70` history and uses a new source/output path. It makes no READY, official grant, production qualification, HARD receipt, science-result, or cost/parity/replay claim. The 24.86 ms historical proxy remains unsupported as a current step-share measurement.

## CPU repair and published source pins

`row.md` retains `regions=any-cpu-quarter` and sets `claimed_cpus=dynamic`. Actual `WS58_REGIONS` and `FILLER_CPUS` remain authoritative. `launch.sh` pins canonical v14 `filler_run14.sh` and `dryrun_check.py` hashes and requires the production engine at `/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1`. `ENGINE.lock.json`, `PINS.json`, and `SOURCES.sha256` record the source commit and exact file hashes. Deployment of that canonical bundle remains the keeper's ws58 boundary. `engine-exact-fixture/` is a byte-identical snapshot used only for nonproduction plumbing tests.

The original native science path remains `job.py full`, reached through `job_entry.sh`; normal completion checks the original `out/RESULT.json` schema in `complete.sh`.

## Production qualification fails closed

Production qualification is pending because this packet does not have the real same-job qualification entry. If `WS58_QUAL=1` and the manifest says `production=true`, `job_entry.sh` exits 70 with an explicit refusal before calling the model-free fixture or starting science work. Calling `qual_fixture.py` directly with a production manifest also refuses. The fixture cannot attach a production recipe hash or create a production claim.

`test_real_entry_fixture.py` verifies that refusal through both paths. It separately exercises the model-free fixture with `production=false`: canonical nonproduction receipt/result-writer and rc75, plus a direct nonproduction active-stop `UNKNOWN` partial. The cutoff run writes `PARTIAL.json` and the test proves the normal `QUAL-RESULT.json` digest remains unchanged. These are fixture mechanics only; they are not canonical production active-cutoff or HARD evidence.

## Test and resource boundary

`../tests/test_canonical_cpu_claim.py` passes dynamic actual-grant `24-47` and relocated `72-95` behavior, malformed metadata refusal, short/expired grant refusal, and atomic receipt checks. Shell syntax, Python compilation, and `SOURCES.fixture.sha256` are checked independently.

The production model is 37.8 GB on disk and captured prior cutoff peak RSS was about 37 GB. No production/native qualification was run under the <=8 GiB R11 budget. The full same-job production qualification must remain pending an eligible resource boundary; do not use the toy fixture, a planning estimate, or 2-SMT fixture numbers as a 24-thread science measurement. Canonical v14 deployment/HARD proof and an actual 24-thread same-job throughput measurement remain prerequisites to READY or production execution.
