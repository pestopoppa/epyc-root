# Forced KB build identity reconciliation

APP source2860624a17c08f6d14e15babc6c41af74285b572 changes only `kb_rag.py::build_index` and five fake/temp tests. MAIN manually reviewed MEDIUM writer/caller scope while host GitNexus remains untrusted. [Original synthetic acceptance](../../artifacts/ni07/run-37447817516/README.md) passes113/113, including5new cases. No real encoder/index build or migration ran.

After successful encoding and vector writing, the writer reuses the lowest existing chunk ID matching exact file/content-hash/line identity, updates its row/FTS, and removes only other matching duplicate catalog/FTS rows. Absent identity inserts normally. Encoding failure leaves existing rows/FTS/vector bytes intact. Nonforced unchanged skip and changed/absent-file cleanup retain their prior policy. Vector files are never unlinked by this correction; distinct current line identities may share the same content-addressed path.

Fixtures require actual SQLite FTS5 and verify repeated-force stable ID, no duplicate FTS, native dependency readback, nonforced no-encode, failed encode preservation, changed-key cleanup and a touched duplicate beside another current line identity. Complete surviving row/FTS and shared vector are preserved. A corpus file excluded by the narrowed fixture still receives existing absent-file cleanup; no excluded-file preservation is claimed.

Native dependency evidence covers logical catalog only. Direct serialization to an active vector path can fail before a full replacement is ready; separately enrolled NI07-16 protects that individual write boundary with staging/atomic publication. Such staging does not restore prior bytes after later SQLite final-commit failure, guarantee crash recovery or turn logical-catalog evidence into vector integrity.
