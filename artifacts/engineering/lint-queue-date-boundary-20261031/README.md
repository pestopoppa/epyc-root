# LINT-QUEUE-DATE-BOUNDARY — maintained source and controls

ROOT implementation: `scripts/system/cpu_queue_f8_runner.sh`, commit `61bdf95ee27e82e2e7bff9547c90338861713ece`.

The tracked successor uses one UTC interval-overlap predicate for current blackout checks, dequeue filtering, and the final execution check. It rechecks inside the `region-lock run` command after region acquisition and in the paired-claim path after pair-guard setup. If a lock/setup wait moves a job into an overlapping interval, the runner exits that attempt with its defer status and returns the job to `pending/`. Normal mode requires a future, explicit UTC `STOP_AT`; sourcing and `CPU_QUEUE_F8_TEST_ONLY=1` return before queue setup.

The recurring blackout is half-open `[00:15, 06:30)` UTC. Dated exclusive windows remain the separate calendar guard with its existing 300-second margin; this runner does not change that guard or add the margin to the recurring daily boundary.

## Validation

- `bash -n scripts/system/cpu_queue_f8_runner.sh` — passed.
- `python3 -m unittest discover -s tests -p 'test_cpu_queue_f8_runner.py' -v` — 9 test methods passed; full output is in [`TEST.log`](TEST.log).
- Normal-entry integration controls use fake date, queue, region-lock, taskset, sleep, and executor commands. The fake clock advances from 00:09 to 00:12 during lock/setup for both direct and paired paths. The 5-minute job is returned to pending and its execution marker remains absent.
- The tests use the checked-in v1 shell fixture `tests/fixtures/cpu_queue_f8_v1_guard.sh.txt` by default. Fixture SHA-256: `5fe47cb1e12fa36775ac2b6f13a2451206a284bf66fec414bd71c884aa85c460`. The original v1 runner SHA-256: `d7f27ad46b5f6388cea53b04ed7b340ba8399faf2e6fade8d209998cd14250fd`.
- The private `/mnt/raid0/llm/tmp/cpu-queue-f8/runner.sh` and Research historical artifact both retained the original `d7f27a…` digest at validation time.

GitNexus could not provide a current impact graph in this worktree: status reported the repository unindexed, the analyzer wrapper was denied by CPU admission, and the new symbol was absent from the prior index. Manual caller search found no pre-existing caller for the newly introduced runner; it is not installed, activated, or referenced by a queue template. The test entry starts no queue or launcher. No live behavior or deployment change is claimed.

Source SHA-256: `d7da72619a5fbe94d2888c48330dfef5540234860075a8c275caf95d8ff17bca`.
