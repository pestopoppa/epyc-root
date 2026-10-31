# Draft source-partial note for USAGE-PROV-1

The additive APP writer carrier is published in orchestrator source commit `0d01dc94c294` (APP
main `3d35934f7f29`); the strict ROOT reader, ingest registration, and process/counter binding are in
ROOT commits `657395e78`, `b5d9f418d`, and `020a992a1`. The reader uses a bounded hash-bound snapshot
index, and its 250-row control confirms two whole-file reads total, with append, replacement, and
symlink refusal controls. The self-contained reader suite passed 10 tests; the opt-in actual writer
to planning-context canary passed as part of 11 tests when the companion source checkout was set.

Existing unannotated records remain unprojectable. No production call site authors a declaration,
no native inference usage capture was made, and the canary uses an explicitly test-only synthetic
declaration. Keep USAGE-PROV-1 unchecked and open for real source-authored native capture and its
runtime canary. This source partial does not establish wired or READY status.

`[no-belief: software source publication and synthetic correctness controls; no measurement]`
