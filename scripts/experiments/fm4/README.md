# FM-4 prospective task acceptance capture

`task_acceptance.py` captures an explicit acceptance-gate decision at write time.
It does not infer a result from completion, an exit code, or report prose. Supply
the identities from the actual dispatch and the digest of the gate's saved
evidence:

```bash
python3 -B scripts/experiments/fm4/task_acceptance.py write \
  --out /private/fm4/task-acceptance.json \
  --parent-session-id session-123 \
  --dispatch-tool-use-id toolu_123 \
  --child-agent-id agent-123 \
  --task-id FM4-EXAMPLE \
  --gate-result fail \
  --evidence-path /private/fm4/gate-evidence.json \
  --evidence-sha256 <64-lowercase-hex-digest>

python3 -B scripts/experiments/fm4/task_acceptance.py validate \
  /private/fm4/task-acceptance.json
```

Use `pass` only for an explicit passing gate result and `fail` for an explicit
failing result. Both commands emit the verified record as JSON on success;
validation errors go to stderr with exit status 1. Argument errors exit 2. The
writer generates a UTC timestamp, verifies the supplied digest, saves a
read-only content-addressed evidence copy beside the output in `evidence/`,
rechecks that copy, and exclusively creates the acceptance record. Existing
records are never overwritten. A failed write can leave an evidence snapshot
without an acceptance record.

The versioned record binds the parent session, dispatch tool-use ID, child agent,
task, explicit result, timestamp, and evidence path/digest. Validation requires
the exact v1 schema and readable, read-only evidence whose current bytes match
the digest. Keep the evidence directory with its record; paths are absolute.

Read-only permissions and digest verification provide integrity checks, not
filesystem immutability: a filesystem owner can replace files and recompute
digests. This offline tool neither authenticates the caller nor proves that a
gate actually ran, that its criteria were appropriate, or that the supplied
identities match a dispatch transcript. It defines no grading rule. There is no
historical import, backdating option, oracle integration, or acceptance claim
about historical task accuracy.

For a gate that must actually execute, use `run_gate.py` with the same four
dispatch identities and direct command arguments after `--`:

```bash
python3 -B scripts/experiments/fm4/run_gate.py \
  --out /private/fm4/task-acceptance.json \
  --cwd /absolute/path/to/reviewed/worktree --timeout-s 120 \
  --parent-session-id <actual-parent-session-id> \
  --dispatch-tool-use-id <actual-dispatch-tool-use-id> \
  --child-agent-id <actual-child-agent-id> --task-id <assigned-task-id> \
  -- python3 -B -m pytest -q tests/path_to_the_tasks_acceptance_gate.py
```

Create the output directory first. Select a gate that checks the assigned task
and obtain the identities from its dispatch independently of the gate record.
The runner saves argv, cwd, UTC start/end times, raw stdout/stderr and return
code in `OUT.execution.json`, then retains that evidence beside the acceptance
record. Timeout, launch failure and signal termination retain execution evidence
without creating an acceptance record. The timeout kills the direct process;
it does not promise cleanup of descendants.

Runner exit status **0 means the record was written**, including a record of a
failing gate. Read `gate_result` to distinguish pass from fail. Neither exit 0
nor an execution record authenticates a dispatch or establishes that the gate
was suitable for the task.

The opt-in Vidya source `fm4-gate-acceptance` revalidates these records as
observations about the selected gate. Its synthetic planning-context canary
tests this plumbing only. The protected oracle consumer, native task-outcome
evidence and end-to-end identity binding remain separate acceptance steps.
