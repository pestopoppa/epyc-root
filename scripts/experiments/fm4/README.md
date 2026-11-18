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
