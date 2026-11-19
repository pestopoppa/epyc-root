# FM-4 parent-session outcome joins

`scripts/coordination/session_oracle.py` derives session verdicts from observed
gate, commit and push events. Its parent join applies only when those events do
not already determine a verdict. It requires the child's session and agent IDs
to match a structured parent `Agent` or `Task` result and its originating tool
call. It never inherits an unrelated parent gate or commit.

The result records its parent path, session, agent, tool-use ID, status and error
flag in `signals.parent_result`. An explicit structured success or failure can
refine the child verdict. A launch acknowledgment, completed report delivery or
successful prose report supplies no task-success label. Missing parents,
unattributable results and conflicting results retain the local verdict.
`signals.parent_join` distinguishes missing, matched and ambiguous joins.

The replay command consumes prepared, frozen transcript copies, verifies their
original hashes and validates historical verdicts against the pinned baseline.
Every entry in the original manifest receives an output row, including missing,
changed and refused inputs. Refused parents cannot be reopened through the
oracle's automatic path discovery. Source, manifest, baseline and result
digests are recorded in the summary. Success, failure and partial verdicts from
the local oracle on the same frozen inputs must remain unchanged after joining;
a changed local verdict makes the CLI fail. Differences from the older committed
verdict corpus are reported separately rather than silently normalized.

```bash
python3 -B scripts/coordination/replay_session_oracle.py \
  --manifest /mnt/raid0/llm/tmp/coordination-and-churn-pipeline/fm4/inputs/replay-inputs.json \
  --out data/fanout_timing/session_oracle.parent_join.v1.jsonl \
  --summary data/fanout_timing/session_oracle_parent_join_summary.v1.json
```

Raw transcript snapshots remain outside Git under the task's private scratch
directory. The committed output contains identifiers and outcome signals, not
transcript prose. This deterministic diagnostic cannot recover missing
transcripts or manufacture correctness labels. It grants no task-accuracy,
faithfulness or causal fan-out claim. Prospective belief projection is tracked
by `VB-FM4-ORACLE-WIRE`; no planning-context canary has been claimed.

The 2026-11-18 replay verified 1,516 inputs and recorded 4,313 missing inputs
against the 5,829-entry frozen manifest. No available snapshot changed or was
refused. There were 355 matched parent results, all without task-outcome evidence;
448 otherwise eligible child joins lacked parent evidence. All 712 local
success/failure/partial verdicts were preserved. Final counts were success 39,
failure 28, partial 645, delivered without outcome 795 and aborted 9. These are
classifier observations over available frozen prefixes, not correctness rates.
The result rows and digest-bound summary are in
`data/fanout_timing/session_oracle.parent_join.v1.jsonl` and
`data/fanout_timing/session_oracle_parent_join_summary.v1.json`.

Validation: 45 focused oracle/replay tests passed, including paired identity,
error, asynchronous-launch, conflicting-result, changed-input and baseline
provenance cases. Native replay exited 0 with no changed local outcome verdicts.

The first frozen replay differed from four committed historical verdicts: one
Claude `partial` became `aborted`, two Codex `success` became `partial`, and one
Codex `failure` became `partial`. All four live originals had grown beyond their
hash-matching frozen prefixes. This supports an input-window explanation but
does not prove which later events determined the historical verdicts. The replay
therefore separates historical drift from a join-induced change on identical
inputs. It does not overwrite the historical corpus or inherit its labels.
