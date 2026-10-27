# Scratch custody audit, 2026-10-27

Read-only q2 inventory is in
`/mnt/raid0/llm/tmp/codex-ni-20261027-priority-scratch-reclaim/audit-ni08.txt`.
The NI08 root's KEEP explicitly covers original native evidence, review bindings
and active proposals until custody retirement. Three `native/read-038.bin`
files in `evl49-s04-native-dry-capture-EXEC-PENDING-20261008-r3907`, `-v4`
and `-v5` each contain 1,350,221,880 bytes and hash to
`64218c27e07400acf3b10a3cac05a410d5ee67814f353788ab75a19c84dde584`.
This establishes identical content, not interchangeable provenance: retain the
three originals until custody and references are resolved. A per-file plan may
propose one raw copy only after those checks, alongside each required JSON, MD,
receipt and binding file; none were retired by this audit.

The inventory includes Git checkout HEADs and conservative status including
ignored and untracked files. No checkout passed both that clean test and
ancestry against its locally recorded `origin/main`; those remote-tracking refs
may be stale, and this is not proof of non-publication. Independently verify
fresh remote reachability, registered worktrees, live holders, dependencies,
queue references and custody before nominating exact candidates. Do not infer
reclaimable size from duplicate pack names.

The same inventory records each `codex-ni*/KEEP*` marker and its rationale.
They include original captures, review packets and active launchers, plus
superseded graph package roots whose specific node_modules were in the separate
approved manifest. The marker text does not distinguish every evidence file
from every cache: inspect and file a precise per-file plan for each root before
narrowing it. No marker or data was changed by this audit.
