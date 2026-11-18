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
observations about the selected gate. Its synthetic planning-context controls
test this plumbing only.

## Native oracle and Vidya canary

After the [D9 oracle acceptance change](../../../proposed/fm4-acceptance-consumption/README.md)
is authorized and available in this checkout, pass the actual Claude child and
parent transcript files, the task ID obtained independently from the dispatch,
and the existing `run_gate.py` acceptance record:

```bash
python3 -B scripts/experiments/fm4/native_canary.py \
  --child /private/fm4/agent-actual-child.jsonl \
  --parent /private/fm4/actual-parent.jsonl \
  --task-id <independently-known-assigned-task-id> \
  --acceptance /private/fm4/task-acceptance.json \
  --state-dir /private/fm4/vidya-canary-new
```

The parent transcript must contain a uniquely attributable terminal structured
`Agent` or `Task` result without an explicit outcome. The child must qualify
for the oracle's acceptance join. An asynchronous launch acknowledgment by
itself is insufficient. The current API joins Claude transcripts. Supply the
execution sidecar and snapshot at their recorded bundle locations. The canary
refuses if the D9 API is missing or if the oracle declines to apply the receipt.

The state directory must be new and its parent must exist. The canary ingests
one record through the registered adapter, uses a local empty intake index,
and checks that `coordination.fm4` retrieves the exact receipt-derived claim as
planning context. The directory holds the isolated ledger, freshness marker
and planner read record. It can remain on disk if a later check fails.

Exit 0 emits a JSON receipt with child, parent and acceptance SHA-256 hashes,
the execution evidence digest, the matched identities, the oracle result and
the selected claim. Both a passing and a failing gate can satisfy the canary
when the oracle applies the corresponding outcome. The hashes check artifact
consistency across the run. Gate suitability and the origin of the task ID
remain caller obligations. The selected claim describes the prospective gate's
exit. It carries no grade for historical task accuracy.

## Codex dispatch evidence

Use the standalone collector with the actual parent and child Codex rollout
files. It reads the files and emits a content-free JSON receipt to stdout.

```bash
python3 -B scripts/experiments/fm4/codex_dispatch.py \
  --parent /private/fm4/parent-rollout.jsonl \
  --child /private/fm4/child-rollout.jsonl
```

The collector verifies the child's structured `parent_thread_id` against the
parent session ID. It requires one parent `collaboration.spawn_agent` call and one
attributable result with the same `call_id`. A result can bind the child's
session UUID directly with `agent_id` or return the exact canonical task path
held in the child's `agent_path`. In the path case the receipt keeps the child
UUID from its metadata and records `binding_kind: native_agent_path`. Conflicting
IDs, duplicate matching results or an explicit spawn error refuse the binding.
The receipt covers the supplied rollout pair and cannot rule out duplicate
child rollout files elsewhere.

Exit 0 means the first child turn has a matching structured terminal event and
the dispatch identity is bound. The receipt distinguishes completion and
interruption, and records whether a final message was present without retaining
its contents. A structured refusal or launch-only receipt exits 1. Malformed
or changing input exits 1 with an error on stderr. Every receipt keeps both
rollout hashes, and `task_outcome` stays null. A separate independently
identified task and an appropriate executed gate are required for prospective
task acceptance. The standalone Codex collector is separate from the Claude
oracle canary above.

### Replay a filed Codex census in Vidya

Create a read-only JSON replay descriptor containing `schema`
`fm4.codex_dispatch.replay.v1`, `result` (the absolute path to the filed
`official/RESULT.json`), `result_sha256` (its pinned digest), `snapshot_dir`
(the absolute path to the retained private snapshots), and `pair_ids` (the
nonempty list of filed pair IDs to replay). Keep the filed `input-pins.json`
one directory above `official/`. The adapter checks the census and input-pin
digests, the pinned collector version, the read-only snapshots, and the
entire structured receipt for each selected pair. Each observation links to
the digest-only public census and its pair ID.

```bash
python3 -B scripts/experiments/fm4/native_canary.py \
  --dispatch-replay /private/fm4/dispatch-replay.json \
  --state-dir /private/fm4/vidya-dispatch-canary-new
```

The canary uses the registered `fm4-gate-acceptance` ingest and the shared
planning reader for `coordination.fm4`. It checks the exact selected claims,
their `Judged/Located` harness tier, and their exclusion from reliance and
from `autokernel.planner`. The metric records a bound first-turn terminal
event, including interruption. Every selected receipt carries a null task
outcome. The same replay descriptor is accepted by Vidya's explicit
`ingest fm4-gate-acceptance --path` entry point.
