# 2026-10-05 — Codex non-inference campaign

Operator authorized the available non-inference queue, beginning with twelve ranked tasks.
Three concurrent implementation workers use isolated worktrees; main owns review, index writes,
wiki integration and publishing. Source-only work proceeds while tests wait on CPU-region claims.
The shared root checkout is dirty and behind remote main; it is not used for implementation.

Initial dispatch: VB-KVQ-V10-DICT, VB-INGEST-IDEMPOTENT, SSU-F9c. Remaining first-wave
deliverables and peer-owned exclusions are in non-inference-backlog.md § Codex session queue.
No task is accepted at this checkpoint.

## Source review checkpoint (06:20Z)

No implementation has been accepted: required local validation jobs are queued behind all four
AutoKernel CPU-region claims. Reviewed source packages exist for native statistics, only-new ingestion,
promotion locking, honest Makefile gates, evidence durability scanning and test-tool health checks.
Review caught and corrected scalar compatibility, retracted-evidence revival, optional constructor
imports and standalone-health behavior. Applicability (83 consumers) and expiry (four modules) received
explicit impact review before narrowly additive implementation. Backpressure preserves typed denial
without changing legacy string behavior or making a second inference call.

The expanded evidence checker is a new verified-findings source. Its write-side capture and existing-
ladder projection are registered immediately as VB-NI-DURABILITY / NI05-13, before the first broad scan.
HSF-3 source inspection found staging timestamps do not prove enqueue; exact/proxy data must remain
separate, and missing exact records cannot support a calibrated session timeout.

## First off-host validation boundary

GitHub Actions run `37273697465` tested root source `23298f00`, research `725eb412`, and orchestrator
`8ebfbc50` on isolated runners. The host remains claimed by AutoKernel; no local test or additive
dependency repair is claimed as executed. Main accepted SSU-F9c (three real-lock fixture passes),
VB-INGEST-IDEMPOTENT (16 focused passes), and VB-APPLICABILITY (24 focused passes plus 106 carrier
tests), all without focused skips. Their owners are preparing task documentation before main promotion.
The broad root suite had 1,630 passes, 89 explicitly skipped cases and four failures; focused acceptance
does not claim the skipped cross-repo producer cases passed. Durability adapter six-case native-writer
roundtrip passed; its missing CLI registration and fixture-coverage declaration were found and corrected.
Research fixture isolation and CI sibling bindings are being corrected before rerun. Orchestrator tests
did not execute because its tracked registry symlink was unresolved during package installation.

Reviewed code is published only on `codex/ni05-validation-*` branches across the three repositories.
The dedicated candidate workflow never deploys, reloads, signs or runs inference. The next source batch
adds prospective gap capture and optional backend-admission enqueue timing. HS-16's lifecycle remainder
is claimed as NI05-14 after confirming the header/parent resolver already exists; it reuses that registry.


## Publication boundary — first three tasks

Main integrated the approved ingestion, applicability and promotion source commits with each task's
prepared progress record and canonical checkbox. Own indices advance to the next action; wiki receives
a bounded operational note. Published completion tally is 3/16, including newly surfaced CI capture and
explicit kernel-override import work. The second off-host run `37275807626` passed 104 Node tests, six
Makefile gate fixtures and 77 durability tests (one named host-corpus case deselected); benchmark collection
reported 2,286 cases. Orchestrator execution remained blocked at import by eager production-store
discovery before explicit overrides. Root failures from AutoKernel fixture API drift belong to the parallel
Claude owner's scope. They are not treated as passing or silently repaired.

Execution incident: cheap_reliability ran an unclaimed Node plugin test (10 cases, about 1.044 seconds)
and later an unclaimed root GitNexus analysis (34.1 seconds, session 45256). The synchronous test finished
before 06:59:42Z; exact start/PID was not retained. Analysis had finished before cleanup interruption, so
hardware overlap cannot be ruled out. Neither execution is acceptance evidence. Main stopped the worker,
confirmed its analysis session had exited, retained source for review, and replaced it with a source-only
worker. No peer process was killed. Future execution remains behind CPU claims or on isolated CI runners.
Prospective CI receipt wiring was registered before its first captured run; the two historical runs are
ordinary validation evidence and will not receive retrofitted tuples.
