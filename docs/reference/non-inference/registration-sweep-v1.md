# Proposed registration sweep v1

`registration_sweep.py` is a read-only checker for CTC-Q-D. It adds no columns to
the existing 18-cell queue and changes no existing validator CLI behavior. There
is no scheduler, lease, process probe, automatic join, live registration or
operational adoption here. `owner_adopted` and `all_producers_bound` remain false.

```
python3 scripts/coordination/registration_sweep.py \
  --file queue-snapshot.md --candidate-row one-row-table.md \
  --candidate-id ROW --catalog registration-catalog.json --for-registration
```

Both table files use the validator's exact header. Candidate file contains exactly
one row. Replacement excludes its own old ID. Terminal peers are excluded. Exit
0 permits the proposal (review mode also returns 0 for uncovered duplicates), 2
refuses an uncovered duplicate in strict mode, 3 means malformed candidate/input
or unavailable candidate provenance. Existing grant/row validation remains a
separate required gate; this checker does not establish readiness.

The catalog is JSON `{"schema":"epyc.registration_sweep.v1","rows":{"ROW":META}}`.
JSON duplicate keys are refused. META has `row_sha256`, `recipe`, `session`,
optional `server`, optional `resolutions`. A reference is exactly
`{"path":"/absolute/small-record.json","sha256":"<64 lowercase hex>"}`. Records
and both table inputs are limited to 2 MiB; anchors to 32 references. Reads open
with O_NOFOLLOW and O_NONBLOCK, verify a regular file with fstat before reading,
bound read size, and close the descriptor on success or failure. Final symlinks,
FIFOs, directories and devices are refused; parent directory symlink aliases are
allowed. JSON NaN/Infinity constants and duplicate keys are refused. Only explicit referenced JSON
is read; no launcher, model, network, recursive scan or inferred prose is read.
Paths locate records; content hashes bind their bytes. They are not signed owner
authentication. Catalog/source custody is the owner's responsibility.

`row_sha256` is SHA256 of the parsed, stripped 18-string array serialized with
UTF-8, sorted object keys, compact separators, ensure_ascii=false. All JSON
digests below use this convention except raw argv, which uses UTF-8 NUL-joined
strings with no trailing NUL. Embedded NUL arguments are refused.

`recipe` references `epyc.autokernel.canonical_launch.v1` from RESEARCH's
CanonicalResolvedRecipe. The checker verifies its snapshot checksum over all
fields except schema/snapshot_digest/execution_digest, then projects model,
optional drafter, executable, DSO contents, exact argv and environment. Artifact
records must use `epyc.autokernel.launch_artifact.v1` with native roles model,
drafter, executable or dso. Native execution_digest is retained as a distinct
normalized domain, never substituted for raw argv. This projection does not
replace native recipe capability/semantic/integrity validation. The native
producer must validate the complete record before supplying it. Unsupported
other recipe formats require a deliberate extension, not ad-hoc guessed hashes.

The shape key is `[model.sha256, drafter.sha256-or-null, executable.sha256,
sorted-array-of-[dso.role,dso.sha256], "sha256:nul-joined-utf8-argv/v1", argv-hash]`.
`session` supplies an owner-scoped `id`, `load_sha256`, and nonempty `anchors`.
The load hash is the JSON digest of `[shape-key, launch_env,
relevant_environment, absent_environment]`. Anchors reference native
`epyc.autokernel.experiment_plan.v1` or `.v2` records with nonempty
`anchor_identity`. Output anchor references are sorted triples
`[record-path, record-SHA256, JSON-digest-of-anchor_identity]`. This checks custody
and consistency of the owner's anchor declaration; it does not re-grade native
measurements, validate a full ExperimentPlan, or invent an anchor.

`server` references ORCH `epyc.stack.server_launch.v1`. The exact argv and native
NUL-argv hash must match the recipe. A DS41 row requires this reference. Same
DS41 server means both rows are DS41=y and their native launch_id, launched_at,
binary_realpath, model_path and raw-argv hash agree. A resource-class boolean,
port or PID alone is never a server identity. Launch records describe a launch;
they do not prove current listener ownership/residency. Existing owner admission
must freshly revalidate that independently before permitting live reuse.

For each matched peer ID, `resolutions[PEER]` is either
`{"action":"separate","reason":"<nonempty explanation>"}` or
`{"action":"join","session":"<same owner/session ID>",
"shared_load_sha256":"<same load hash>","anchor_refs":[<exact output triples>]}`.
Join additionally requires candidate and peer session, load, server identity and
anchor references to agree. Same-shape differing environments remain listed but
cannot join. One peer's reason cannot cover another peer. A reason records the
owner's explanation; it grants no waiver from resource/measurement rules.

A pure non-model row may instead supply exactly
`{"row_sha256":"...","non_model":"<reason>"}` with DS41=n. Old rows lacking
metadata, or carrying missing/changed/invalid native references, are reported as
UNKNOWN and never matched on null values. The result explicitly says whether
legacy coverage is exhaustive. Strict success with UNKNOWN peers is not evidence
that the whole queue is free of duplicate loads. Queue metadata capture remains
a separate integration cost.

WS58 owns integration. As confirmed 2026-10-27, the previously assumed live
publication lease did not exist; R6's lease is proposed source, not deployed.
The [reviewed source packet](../../../artifacts/coordination/ctc-qd-registration-20261027/README.md)
proposes a shared lease and a crash-recoverable, multi-file journal: it does not
claim filesystem-atomic publication of several files. Normalize the candidate,
bind native records, run the checker and revalidate before grant under the lease.
Row or candidate metadata changes invalidate its receipt; grant-time resweep
checks the current peer catalog and native references. Re-arm and server
relaunch require fresh bindings. No unlocked invocation closes TOCTOU races.
All row producers and grant paths must be bound before adoption can be asserted.
The proposed GAP R6 engine and its undeployed lease are untouched.

Source pins audited: ROOT 26f28d3397009c97a497bce20d6c39fb9eadb5f0,
ORCH 43c63034432b6159fc503dc46c4671968514e7c5,
RESEARCH 6f9799a933741fb0ae2dd267cfa29b39987b6165.
