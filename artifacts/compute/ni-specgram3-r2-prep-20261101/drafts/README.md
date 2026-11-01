# SPEC-GRAM.3 r1 failed-row repair proposal

Private review packet for `codex-ni-specgram3-llg101-cpu-r2-20261101`. No ROOT edits, READY manifest, official grant, native qualification, or science result have been produced. The r1 `FAILED-RUN rc70` row and filing remain immutable.

## Verified failure and approved repair

The fresh ROOT filing at `4d6db587b3799d4baee8ab4644c4f2e9acac0ef4` records r1 `FAILED-RUN rc70`, no `RESULT.json`, and no cost/parity/replay/adoption verdict; the historical 24.86 ms proxy is not a measured current step share. The filed row used `regions=any-cpu-quarter` and `claimed_cpus=any-cpu-quarter`. Its ended record and launcher log show the actual grant `24-47`, then `DRYRUN_REFUSED: malformed claimed_cpus`.

The old copied checker parsed `claimed_cpus` numerically and rejected the symbolic claim. Canonical ROOT v14 `dryrun_check.py` from `4d6db587...` supports `claimed_cpus=dynamic`, resolving CPUs from the actual grant and in-claim allowed set. The proposed r2 row preserves `regions=any-cpu-quarter`, uses `claimed_cpus=dynamic`, preserves the original scientific task, denominator, evaluator, output schema, window, and adoption state, and writes only to a new r2 output path.

## Executable prep packet

See [cpu-r2-20261101/README.md](cpu-r2-20261101/README.md) and its pinned scripts/source bundle. It carries the unchanged scientific `job.py full` entry plus canonical v14 launcher wiring and source hashes. The canonical engine/checker source pins identify ROOT commit `4d6db587b3799d4baee8ab4644c4f2e9acac0ef4`, foundation `11ce`, and expected installed bundle `/mnt/raid0/llm/tmp/compute-flags/bin/qual-v1`.

**Production qualification is explicitly pending.** `job_entry.sh` refuses a production qualification request with rc70 before any toy fixture or science work starts. Direct production invocation of `qual_fixture.py` also refuses. The model-free `COMMAND_NATIVE` fixture is restricted to `production=false`; it cannot write a production recipe claim or stand in for the actual science backend. The real same-job first-compute/result-writer/active-STOP qualification entry is not yet implemented. Do not publish READY or treat fixture evidence as production/HARD evidence.

## Tests and limits

`tests/test_canonical_cpu_claim.py` passes actual `24-47` and relocated `72-95` grant-shape behavior, malformed-note refusal, deadline reserve, expired grant, and atomic boundary receipt checks.

`cpu-r2-20261101/test_real_entry_fixture.py` passes a nonproduction canonical fixture receipt and rc75 result-writer check, a separate nonproduction active-stop fixture with `UNKNOWN` partial and preserved normal result, and a regression that verifies both `job_entry.sh` and direct `qual_fixture.py` refuse a production toy attempt. No official nonce or HARD/pass receipt was issued.

The actual scientific model is 37.8 GB on disk, and captured prior cutoff peak RSS was about 37 GB. No model/native qualification smoke was run under the <=8 GiB R11 allowance. The production same-job qualification therefore remains pending an eligible keeper boundary and resources. A real same-job throughput measurement at the actual 24-thread quarter grant is also required; no 2-SMT fixture, planning estimate, or historical proxy is substituted.

The exact agent audit task rows are retained in `evidence/agent-log-session.jsonl`.
