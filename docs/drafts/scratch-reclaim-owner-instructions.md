# Scratch filing reclaim — owner review packet

Candidate only: integrate after review and deployment of the validator together
with the reclaim script. `validate_fillers.py` is in the grant-admission path;
this stricter rule rejects active rows declaring directory-wide KEEP, and all
scratch rows without nonempty raw patterns. Inventory and update affected rows
before installing it; terminal rows remain exempt. A declaration cannot prove a
mutable script writes no cache, so the candidate requires explicit raw patterns
for every scratch row. Native evidence should use individual file names or
file patterns, not a directory blanket.

At filing after a row becomes COMPLETE or CANCELLED:

```
python3 -B scripts/safety/reclaim_filler_scratch.py ROW_ID
python3 -B scripts/safety/reclaim_filler_scratch.py ROW_ID --apply
```

Review the dry-run file list before `--apply`; use a fresh claim and repeat all
custody and live-dependency checks at the action boundary. The helper selects
files inside `/mnt/raid0/llm/tmp`, subtracts KEEP patterns, refuses symlinks,
hard links, Git internals, live holders, active handoff references, open grants
and other active queue rows referencing the root. It checks identity again at
each move and stages into isolated per-file children under normal trash through
`guarded_rm.sh`. It reports allocated GB selected, not disk space freed: staging
on the same filesystem does not free that space. A partial failure is retained
for manual reconciliation and must never be retried blindly.

These checks do not establish all possible relative references or unrecorded
dependencies. The owner must examine source custody and references separately;
if that cannot be proved, do not apply. This tool does not amend the seven-day
retention rule. The same-day wording is a draft for human consideration only.
