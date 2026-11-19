# FM-4 prospective gate execution

`scripts/experiments/fm4/run_gate.py` captures execution of an explicitly selected
acceptance gate and uses the existing `task_acceptance.py` producer to bind its
result to caller-supplied task, parent-session, dispatch and child identities.
The gate command runs as an argument vector without a shell. Select a bounded,
task-specific gate before running it; an arbitrary command returning zero does
not establish that a task succeeded.

The native execution evidence retains the command, working directory, UTC start
and end times, exit status, timeout state and base64-encoded stdout and stderr.
A normally completed gate supplies pass for exit zero and fail for a positive
exit status. A timeout, signal termination or launch error retains execution evidence but supplies no
acceptance record. This distinguishes a failed gate from an incomplete attempt
to execute one. Evidence files can contain sensitive gate output; retain them in
the task's private scratch directory rather than committing raw output.

The runner validates caller identities and output destinations before invoking
the gate. The acceptance producer retains a read-only content-addressed snapshot
and verifies its digest. That detects changes to the retained evidence; it does
not authenticate the caller's identities or prove that the chosen gate measures
the intended task. The caller must obtain identities from the actual dispatch
and use a gate suitable for that task.

```bash
python3 -B scripts/experiments/fm4/run_gate.py \
  --out /absolute/private/task/acceptance.json \
  --cwd /absolute/task/worktree --timeout-s 60 \
  --parent-session-id ACTUAL_PARENT --dispatch-tool-use-id ACTUAL_DISPATCH \
  --child-agent-id ACTUAL_CHILD --task-id ACTUAL_TASK \
  -- /absolute/task/acceptance-check --task ACTUAL_TASK
```

Replace all paths and identities with the actual dispatch context. The output
parent directory must already exist. Runner exit zero means an acceptance record
was written; inspect its `gate_result`, because a completed failing gate also
produces a record. Native evidence is saved beside it as
`acceptance.json.execution.json`, including when execution is incomplete.

For a real delegated task, obtain the four identities from the parent dispatch
before launching the gate. Choose a new output path under
`/mnt/raid0/llm/tmp/coordination-and-churn-pipeline/`, retain the execution JSON
and content-addressed snapshot together, and validate the acceptance record with
`task_acceptance.py validate`. Supply that record to the oracle only after its
protected consumer has landed. Test fixture identities must not be reused as
native task-outcome evidence. A failed capture is not a failed task verdict.

The timeout bounds the direct child. It does not guarantee termination of
descendants created by the gate; use commands with bounded child lifetimes.
This tool is not an inference launcher and does not authorize benchmark compute
outside published rows.

The protected oracle consumer remains a separate D9 proposal in
`proposed/fm4-acceptance-consumption/`. Native task-outcome evidence, exact
transcript identity consumption, shared belief projection and the recipient
planning-context canary are still required before FM-4 can close. Runner controls
exercise software behavior; they supply no task-accuracy, historical-outcome or
faithfulness result. Source enrollment is `VB-FM4-ORACLE-WIRE`.
