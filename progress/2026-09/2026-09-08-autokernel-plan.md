# AutoKernel autonomy planning — 2026-09-08

Documentation-only session, at the operator's explicit request. No application code, kernels,
campaigns, measurements, services or deployment settings changed.

Updated [INF-73](../../handoffs/active/autokernel-unified-surface-program.md#autonomy-design-20260908)
with a detailed, evolving implementation notebook: dated research audit and subsequent fold corrections;
accepted operator preferences; proposed resource manifests and broker lifecycle; mechanism-aware CPU
partition testing and transfer/coexistence evidence; adaptive seed-prioritized scheduling; deterministic
runtime sweeps; durable journal/recovery and candidate validation; low-friction Vidya projection/retrieval;
standalone supervision, authenticated minimal dashboard controls, truthful health, storage safety;
dependency-ordered implementation proposals, migration, fault tests and unattended acceptance criteria.

Preserved existing consolidation history and other owners' implementation checkboxes. Completed only
PLAN-DOC-1; PLAN-DOC-2 explicitly remains iterative documentation, not authorization to implement.
Numerical defaults and unresolved engineering choices are labeled provisional. Refreshed the existing
INF-73 index pointer; created no duplicate handoff or implementation dispatch queue.

Validation: `git diff --check`, local Markdown link targets, balanced code fences, generated handoff
index/citation checks (zero problems), and README freshness check passed before publication.
Integrated concurrent upstream close-out findings without overwriting them: floor-unit refusal and
third-party contamination despite cooperative locks remain in the owning handoff.
GitNexus's stale index has no symbol for this Markdown target; no code dependency changes are involved.
Used the wrap-up skill to capture the handoff, progress and focused documentation publication; no wiki
compilation or index pruning was requested.

## Operator-invoked session wrap-up

The subsequent explicit wrap-up request authorized the wiki sweep. Compiled the 14-source content-hash
delta into `wiki/autonomous-research.md`, `wiki/hardware-optimization.md`, and
`wiki/agent-architecture.md`, preserving distinctions between measured findings, recorded dispositions,
and unimplemented design. Source review covered consolidation, CPU measurement corrections and the
heavy-wrap test qualification; reviewer precision corrections were applied before publication.

Index regeneration/check passed with zero problems; pruning screen returned zero candidates. No
handoff was archived or split: the owning handoff's first screen exposes the iterative design next step,
and its substantial open design is intentional. PLAN-DOC-1 remains the one completed documentation
checkbox; PLAN-DOC-2 remains open for operator iteration. No new implementation tasks were dispatched;
the explicit decision not to file the provisional work packages as executable tasks is retained in §8.

README freshness check was clean. Source reviewers checked 20, 18 and 18 claim groups (some overlapping);
two precision corrections and one baseline-description clarification were applied. Wiki lint passed
with zero errors and 74 warnings; structural and wiki-link passes were clean. No application test
coverage or empirical performance validation is inferred from this documentation review.
The pre-existing August 25 progress source is untracked in the shared clone and absent in lane checkouts:
its unchanged hash was verified, and a temporary lane mirror preserves its existing manifest membership
without committing or deleting the operator's source. No application tests, builds or inference ran.

The design commits `28d94b4d` and `da33c6dd` were already published through main `2c719b3f` before this
final sweep. This wrap-up adds only wiki synthesis, the shared compile watermark and this close-out record.

## Final-session close-out audit and handoff refinement

At the operator's subsequent request, audited both completed research sessions' final logs and their
committed evidence against the unified design. Root snapshot `2a710cab`; research source inspected at
`6ab403ed` and self-draft recipe fix `c3e362a1`. Three independent read-only reviews covered CPU evidence,
GPU/recipe/calibration findings, and measurement-policy/authority consistency. No new inference, build,
server, runtime change or protected-policy amendment was performed.

Updated [§8.16 and the affected earlier clauses](../../handoffs/active/autokernel-unified-surface-program.md#final-closeout-audit-20260908):

- Actual measured instrument (`2516c9807`, build 10303, explicit champion-control state) is distinct from
  intended delivery `ef81196d5`. The CPU draft's unresolved pin is not actually checked by preflight;
  final admission must refuse unresolved identity rather than trust the boolean's existence.
- CPU THP adoption and GPU bounded non-transfer require per-target/surface recipes and scoped beliefs.
  Same-build runtime plans need level/dispersion estimands and direction-only/inconclusive/bounded-null
  conclusions, without promoting joint effects to individually proven component claims.
- Source inspection found explicit-unset semantics missing from recipe environment construction:
  parent treatment can survive `with_env(KNOB=None)`. THP readback protects R23-58 from silent acceptance;
  this does not invalidate that experiment. Added a proposed explicit-unset/effective-env identity contract
  and regression fixture; no implementation fix made in this documentation-only session.
- Ratified instrument-class, floor-unit/n≥24/interval and bounded-null requirements replace underspecified
  design text. Replay/cache calibration validation once per immutable dependency identity, not every arm.
  Preserve valid underpowered observations as inconclusive and historical dispositions unchanged.
- Completeness, shared screening, independent units and actual fired-path controls now feed every
  projection. Lifecycle sampling includes setup and gaps between arms; known-bad sampler labels cannot
  become clean claims. SC75 is already filed and is reused rather than duplicated.
- Corrected “unused half” reasoning, separated best-supported-recipe comparisons from causal contrasts,
  and added operating-frontier/unknown-ceiling and baseline-unmeasured states to the dashboard plan.
  Absolute before/after BIOS rates remain comparable with attribution caveats; floors need recalibration.
- Preserved operator-owned OP-41 after finalisation → promotion → reboot, and R23-64/65's BIOS gate.
  Added retention/ref-closure validation so a successful backup command is not confused with coverage.

Read-back reviews accepted the source/authority treatment; corrections applied for per-control activation
scope, distinct experimental units, calibration-cache reuse and missing-warrant versus low-power semantics.
Several source-summary arithmetic/extrapolation cautions remain explicitly marked in §8.16 rather than
copied into thresholds or used to amend the measurement constitution.

Completed one new documentation checkbox (PLAN-DOC-3); PLAN-DOC-2 remains iterative planning. No new
implementation dispatch rows: proposals refine the existing queue, and §5b's unowned items are not adopted.
Validation passed before publication: `git diff --check`, local link targets and balanced fences,
handoff index/citation check (zero problems), and README freshness. This is a per-task handoff update,
not another operator-cadence wiki sweep or pruning pass. The shared checkout's unrelated divergent
GLM work was left untouched; publication is through the isolated planning lane and remote main.

## Fresh end-to-end handoff review

At the operator's request, three fresh independent reviewers audited the unified handoff at root
`452bee84`: evidence/measurement authority, planning/resource allocation, and lifecycle/recovery.
The owning session reconciled their findings against ratified Annex K, MEASUREMENT.md, R23-54,
current accumulator source at research `6ab403ed`, and the dashboard plane rule. No inference, builds,
kernel/code edits, service changes or policy amendments were performed.

Updated [§8.17 and the affected earlier clauses](../../handoffs/active/autokernel-unified-surface-program.md#implementation-contract-review-20260908):

- Fixed two actual contradictions: R23-54 already ruled a four-keep serving cadence, not the notebook's
  proposed ten; A2 records ordinary foreign load as search noise, not a generic wait/refusal reason.
  Distinguished discovery, strict confirmation and owning release authority, including category,
  intended-use eligibility and A3's cross-epoch numerical search restriction.
- Delineated calibration provenance versus two-arm applicability, interval use without new thresholds,
  typed correctness/timing equivalence, and exact promotion-candidate evidence where required.
- Defined accumulated/validated/production pointers, immutable validation batches and recipe manifests,
  cross-repository journaled integration, cadence versus outstanding validation debt, and identifiable
  source/build/runtime leave-one-out treatments. New candidates do not erase older immutable evidence.
- Added held-claim resource accounting (including CPU used by GPU stages), bounded coverage rounds,
  finite seed boosts, reservations, idempotent target revisions and baseline pinning. Valid-result
  guarantees are not fabricated from service-opportunity bounds during noise or authority outages.
- Made transfer directed/nontransitive, rejection-screen authority explicit and auditable, coexistence
  profiles noncomposable, and refutation/retraction checks independent of top-k truncation. Queued stages
  use cheap local invalidation generations, not a network round trip or corpus scan per arm.
- Specified supervisor fencing, durable pre-spawn ownership, restart/unit reuse, linearized idempotent
  controls, expiry/drain deadlines and coherent ordered dashboard snapshots with lifecycle-aware health.
  Kept producer commands outside the hub's non-proxy presentation plane.
- Added code ownership/test seams, versioned migration/rollback refusal, and deterministic failure
  fixtures. Replaced stale run-30 execution instructions with current design navigation; preserved
  historical evidence and other owners' checkboxes, and repaired the malformed decision table.

Completed PLAN-DOC-4 only; PLAN-DOC-2 remains iterative design. Refreshed the existing INF-73 pointer;
no new execution queue, ownership adoption, wiki sweep, pruning or handoff compaction. The wrap-up skill
was used for the focused per-task handoff/progress/publication workflow. OP-41 and relaunch gates remain.

GitNexus is current for shared main but has no symbol for this Markdown handoff (`risk=UNKNOWN`);
manual impact review is documentation-only, confined to this handoff, its index pointer and progress.
The bus rejected this lane label as a non-roster identity; no other session's identity/outbox was used
and no roster mutation was made for a documentation task. Shared dirty/divergent GLM work is untouched.
Read-back corrections were applied for immutable old-batch validity, positive seed opportunities,
accounting every reserved stage, ordered snapshot streams and renewal-versus-revocation semantics.
Validation passed: `git diff --check`, all 93 local Markdown link targets, balanced fences, generated
handoff index/citation checks (zero problems), and README freshness (no warnings). No application or
performance test result is implied by this documentation audit.
