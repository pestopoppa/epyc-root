# LOOP-49 root components — candidate checkpoint

Implemented isolated branch `codex-loop49-qual-engine`, lane
`/mnt/raid0/llm/worktrees/loop49-qual-engine`. Added keeper-side qualification
run/verify/fingerprint, canonical shell/Python engine, READY v2 schema, structured
filer outcomes/science scoring, keeper gate hook, and 20 component regressions
with 18 byte-preserved real FILED receipts plus two tamper controls. Exact source
audit is retained at `docs/reports/failed-run-audit-20261031.md`.

Operator bindings: D1 hard gate, D2 science quota, D3 one canonical allowlisted
engine, D4 disk waits parked and uncounted. Qualification directories, fixtures,
nonce records and `.ended` are immutable retained artifacts; no cleanup deletes
or renames them. SIGKILL recovery checks PID plus birth before writing missing
terminal custody, with no signal to a reused PID.

Prepared an **unpinned, live-mode-disabled** v7f review candidate and exact v7e
base/diff in `/mnt/raid0/llm/tmp/loop49-keeper-v7f-candidate/`. It does not alter the
running keeper. Legacy queue carry/rearm/succession is disabled in that candidate
to avoid bypassing D1; actual writer-boundary gate integration is outstanding in
outside-root keeper/arm/gate scripts. Root integration contract names these
specific changes. No handoff/index rows were edited.

Validation: Python AST parsing, shell syntax parsing and diff whitespace check
passed. No test, build, qualification launcher or candidate keeper was executed:
there is no explicit compute grant for this work. The 20 tests are component
regressions and do not establish the report's full keeper dry-run acceptance
matrix. No runtime/deployment or science claim is made. GitNexus status was
stale; `impact boundary --direction upstream --repo /workspace` returned target
not indexed / UNKNOWN. All runtime files are additive with no existing caller
modified; a refreshed index and granted integration test remain required before
deployment. [no-belief: implementation checkpoint; no measurement result]
