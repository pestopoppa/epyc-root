# C22 W66 prefill-budget replay

Row `codex-ap-w66-budget-gpu-20261128` ran on the MI210 with physical cores 88–95 and their SMT siblings reserved. It used the immutable C22 build `ce6fcbbde1ee58f165283fbfe74910f47bb2efba`, A3B Q8_0 with MTP D2, and four f16 split-KV slots with 131,072 tokens each. [Rowflow spec](spec.json) · [Qualification](rowflow-smoke.json) · [Rowflow end](rowflow-ended.txt)

Each visit starts a new server on a private port. It restores the same sealed ON 28 then OFF 56 prefixes through restore-only links to the prior private archive. The runner verifies snapshot hashes, native restore counters, source and model identity, affinity, runtime linkage, and in-request GPU residency. The control passes 0 tokens / 0 ms and the treatment passes 256 tokens / 900 ms. Both visits preserve each request’s original chat and sampler settings, cap both outputs at 256 tokens, and launch OFF 56 at ON 28’s first emitted delta. The peer’s fixed output cap is a change from the 27 November replay. Generated tool proposals remain inert.

The experiment measures ON 28 native decode, OFF 56 delivered TTFT, time from the ON 28 send until both streams finish, and native mixed-iteration timing. The C22 log distinguishes prompt rows processed alongside decode from the remaining OFF 56 rows processed alone. The report uses nearest-rank p99 for the declared 900-ms comparison and also records the rounded-index convention used in the prior 27B comparison. The native iteration timer and delivered TTFT have different boundaries. [Numeric summary](summary.json)

Both fixed output caps isolate the timing question. The results give no task-quality or accepted-work measurement.

## Reproduce the numeric summary

The owner-only archive includes all fresh visit receipts, launch and cleanup evidence, native logs, resource samples, private streams, and the row contract. The restored snapshots remain anchored to the previous owner-only archive by their sealed digests. [Archive manifest](archive-manifest.json)

```sh
python3 -B artifacts/analysis/w66-prefill-budget-20261128/reduce.py \
  /mnt/raid0/llm/archive/compute-evidence/w66-prefill-budget-20261128/native/out/run \
  /tmp/w66-prefill-budget-summary.json
cmp artifacts/analysis/w66-prefill-budget-20261128/summary.json /tmp/w66-prefill-budget-summary.json
```

The launcher and row contract are retained for reproduction through a fresh named row. The source manifest binds the driver, completion check, and reused endpoint implementation from the prior private archive. [Launcher](launch.sh) · [Driver](job.py) · [Source digests](SOURCE.sha256)
