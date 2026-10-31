# MAIN preparation only — LOOP-25 source registration

Base for semantic application: ROOT commit `5733a80f46cc4366ae2b6217eaf3cd34f0dbcb8b`.
No ROOT handoff, source table, index, or checkbox was edited. MAIN applies these exact drafts
after reviewing the candidate and its write-side boundary.

The candidate writes timestamped filesystem free-byte samples and a projected-reserve alarm.
That is a new operational measurement source. The current log is not a belief tuple writer and
has no self-hash/protocol warrant, so this draft enrolls only prospective source work and forbids
retrospective grading. It reuses the existing `measurement` class and `ClaimTuple` ladder; it adds
no class or grading rule.

## Exact source-table row draft

Insert under the `Source | Class | scope / absence rules | producer / adapter` table in
`scripts/vidya/adapters/README.md`:

```markdown
| workspace-58 ready-depth filesystem forecast samples (LOOP-25) | measurement (candidate; existing shared ladder) | Prospective UTC free-byte observations for one resolved target and filesystem device, joined to the exact deduplicated READY/ARMED row IDs and est_output_GiB values used in each eight-hour projection. Preserve measured history window/rate, reservation sum, projected bytes, floor, and UNKNOWN reasons; an alert is not an admission, host-safety, or inference-performance verdict. The current depth-only log and this uninstalled candidate have no self-hashed belief writer or protocol warrant: no retrospective ClaimTuple or grade. Wire only prospectively through the existing measurement ClaimTuple ladder, and require the source-bound planning-context canary before calling it wired; no new source class, ladder, or grading rule. | Candidate writer: `artifacts/ni/loop25-disk-forecast-20261031/ws58-ready-depth-candidate.sh`; runtime parser copy `/mnt/raid0/llm/tmp/compute-flags/validate_fillers.py` (same SHA as tracked `scripts/coordination/validate_fillers.py` at the reviewed base); follow-up: `VB-LOOP25-DISK-FORECAST-WIRE` |
```

## Exact follow-up task draft

Add under the open task list in `handoffs/active/vidya-belief-substrate-program.md`:

```markdown
- [ ] **VB-LOOP25-DISK-FORECAST-WIRE — wire prospective disk-forecast measurements if LOOP-25 is adopted.** If workspace-58 adopts the LOOP-25 candidate, write a source-bound native record at each forecast boundary that preserves UTC capture, resolved target/device identity, current free bytes, exact deduplicated READY and ARMED row IDs plus declared est_output_GiB, selected history samples/window and rate, eight-hour projection, 150 GiB floor comparison, and each UNKNOWN reason. Bind the writer/source and captured input record by digest. Project only through the existing `measurement` ClaimTuple ladder; missing protocol, repetition, date, or host-attestation elements remain whatever the existing grader determines, with no new class, grading rule, or invented warrant. Require the producer/reader planning-context canary before calling the source wired. This is a prospective follow-up, separate from and not a prerequisite for owner adoption, deployment, or the runtime alarm. Do not grade/backfill the current depth-only log, claim a forecast alert is an admission verdict, or change keeper/admission policy.
```

This task is a source-wiring dependency, not a completion claim. It does not authorize MAIN to
check LOOP-25 or change the original backlog row.
