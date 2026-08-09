# Vidya Architecture Appendix — non-binding

**Status:** NON-BINDING sketch. Nothing here is a pilot requirement, a ratified decision, or an
implementation commitment. Revisit only at promotion.
**Date:** 2026-08-09 (V2 revision; split out of the 2026-08-09 v1 draft §16.2)
**Owning handoff:** [`handoffs/active/vidya-belief-substrate-program.md`](../../handoffs/active/vidya-belief-substrate-program.md)
**Siblings:** [pilot spec](vidya-pilot-spec.md) (binding) · [research program](vidya-research-program.md)

---

## Why this is quarantined here

The v1 draft carried ~15% of its length as a mature-daemon stack selection — language, RPC
framework, serialization codec, authenticated-map implementation, rule engine, e-graph engine, and a
table of explicitly rejected dependencies. It was well reasoned and entirely premature: none of it
changes the pilot's go/no-go decision, and a detailed stack table read as a decision already made.
The audit's recommendation, operator-endorsed, was to sever it so it cannot masquerade as a
requirement.

**Read this only if the pilot is promoted.** By then some of it will be wrong — parts already are
(see §3).

---

## 1. The pilot stack (this part *is* binding — it lives in the pilot spec)

For the avoidance of doubt: the pilot is Python 3 with pinned dependencies, an **append-only JSONL
ledger with fsync-per-append as the canonical record** and SQLite (WAL) only as a rebuildable
derived index, JSON Schema validation, canonical JSON (RFC 8785) for hashing and fixtures, BLAKE3 or
SHA-256 with the algorithm recorded in every identifier, a deterministic single-writer fold, sorted
iteration at every hash or output boundary, explicit `as_of` injection, and property/fixture/mutation
tests. The pilot avoids a full Datalog or e-graph dependency unless the rule set proves too complex
for straightforward stratified Python; a smaller implementation is easier to audit while the model is
still moving.

---

## 2. Mature-daemon sketch

If promoted, the shape that follows from the constraints (not a selection):

| Component | Direction | Why |
|---|---|---|
| Language | Rust, pinned toolchain | deterministic control, low idle overhead, single-binary deploy |
| Fold | hand-written seminaive core; a Datalog embedding only as a development accelerator | no general engine supplies the required provenance circuits; certified ordering stays ours |
| Provenance | Vidya-owned hash-consed DAG circuits | the correctness-critical representation; not delegable |
| Ledger | JSONL canonical (house pattern); SQLite WAL as derived index | the canonical record stays diff-reviewable; the index is disposable and rebuilt by the fold |
| Serialization | versioned envelopes; canonical JSON as interchange/audit form | the ledger is permanent, so schema evolution dominates decode speed |
| Hashing | BLAKE3 with algorithm-tagged identifiers | content, world, and Merkle hashing |
| Authenticated log | RFC 9162 tree math; tile materialization only at the L2 trigger | see pilot spec §11.1 |
| API | typed RPC with a checked interface definition | four endpoints, several client languages, a streaming change feed |
| Runtime | async I/O around one pinned single-threaded fold | correctness-bound service with few connections |
| Parsing | incremental parse trees for structured anchors | only if code anchors ever enter scope (they do not today) |
| Observability | structured tracing + a metrics exporter | low overhead |

**Process topology.** One daemon (thin API and storage wrapper over a reusable deterministic kernel
library), one standalone verifier, and any number of adapters. The verifier shares only canonical
serialization, hashing, authenticated-map, and circuit-evaluation code — its narrow dependency
surface *is* the trust design.

**Four primitive operations.** `submit_frame` (the sole mutation), `query`, `impact` (hypothetical
change, nothing committed), `subscribe`. Verdict, TTL, corroboration and consumer-policy
admissibility are read-time. No API may write a belief, verdict, freshness state, projection status,
or obligation status directly — those are fold or read-time results.

**Crash recovery.** The ledger is the only source of epistemic truth; snapshots are performance
caches. Boot loads the newest snapshot, verifies its metadata and state hash, replays frames after
its frontier, and falls back to a full refold from origin if the snapshot is absent or invalid. A
corrupted snapshot is discarded without ceremony. Snapshot cadence follows measured full-refold
latency.

**Failure posture.** The daemon is read-only over governed artifacts unless a separately authorized
compatibility writer is invoked. If it is down, existing workflows continue in their pre-Vidya mode.
If an adapter is down, its source frontier is visibly stale. If the fold fails, the daemon refuses
current-state certification and refolds. If certificate verification fails, consumers treat the
answer as *uncertified* — never as false.

---

## 3. What the 2026-08-09 audit already changed here

The v1 stack table predates the landscape review and is superseded in three places:

1. **Authenticated storage.** v1 reached for a Jellyfish/sparse-Merkle implementation. The audit
   found the ecosystem converged on tile-based transparency logs (C2SP `tlog-tiles`, a
   production-ready Go library, and a re-engineered public log GA in late 2025) with static,
   CDN-cacheable tiles and client-computed proofs. **But the pilot needs none of it** — the ladder in
   the pilot spec puts ~200 lines of Merkle roots plus signed-note checkpoints at L1 and defers tiles
   to a named trigger. If that trigger ever fires, evaluate the tile stack before any custom store.
2. **Spec drift is real.** The checkpoint format has already moved on main toward post-quantum
   cosignatures. Whatever is adopted must be pinned to a tag and re-read before implementation.
3. **Certificates have a template.** The v1 draft invented a certificate schema; the supply-chain
   world has a verification-summary attestation whose field set maps almost one-to-one (see pilot
   spec §11.2), including the composition property that makes a certificate re-enter the ledger as an
   attestation frame.

---

## 4. Negative results that constrain any future stack

These are not preferences; they are reasons a plausible choice is wrong.

- **Differential-dataflow / Z-set incrementalization needs abelian-group structure.** `min`/`max`
  lack inverses. Such an engine can host a re-encoded fallback, but the re-encoding loses native
  evidence-token semantics.
- **Monus / m-semiring subtraction is not valid deletion** on this carrier. Retraction is
  substitution, not subtraction.
- **Counting-based deletion is incompatible with idempotent alternative support** — `max`
  intentionally collapses multiplicity.
- **Minimal-depth provenance semantics break the Deletion Property.** Any engine whose provenance is
  shortest-derivation-only cannot support exact retraction (pilot spec §5.2).
- **Provenance circuits may be polynomial while explanation enumeration is exponential.** Never
  expand all supports to claim scalability.
- **Recursive Datalog containment is undecidable in general.** Machine-enforced policy comparison
  stays inside a declared decidable fragment; anything outside routes to human review.
- **Sound, complete static purity analysis is unavailable** for dynamic languages — which is why R3
  is severed rather than scheduled.
- **Equality-saturation engines may schedule work nondeterministically**; an e-graph's internal order
  must never reach a digest.
- **Arrival order, model confidence, and "latest prose wins" are not conflict-resolution rules.**

---

## 5. Determinism discipline (applies whenever a certified path exists)

1. The fold executes on one pinned thread; parallel engine modes are banned from certified builds.
2. No hash-map or filesystem enumeration order reaches a hash, certificate, export, or explanation.
   Collections are ordered structurally or sorted by canonical key.
3. Floating-point values are forbidden in the certified algebra. Advisory-overlay degrees are not
   part of it (pilot spec §13); any float metadata needs a canonical byte encoding and may not
   influence ordering without a deterministic rule.
4. Toolchain, parser, database, and rule-engine versions are pinned and recorded in outputs.
5. Golden fixtures run on more than one architecture and require identical state hashes, belief
   versions, impact reports, and certificates.
6. Incremental results are continuously checked against full refolds on sampled and adversarial
   workloads.
7. Locale, timezone, ambient clock, random seeds, and environment variables are explicit inputs or
   excluded from semantics.

---

## 6. Reversal thresholds

If the mature build ever happens, these are the pre-registered conditions for changing a choice —
recorded so a future decision is evidence-driven rather than re-litigated from scratch.

| Choice | What reverses it |
|---|---|
| SQLite | material C/build friction, or a pure-Rust audit mandate |
| Hand-written fold | a rule set too large to maintain, *with* golden-hash stability demonstrated for the alternative |
| Full refold as the retraction path | p95 refold exceeds the ratified interactive budget at real ledger volume — and only with continuous verification against full refold |
| Single daemon | independent multi-writer operation becomes a ratified requirement |
| L1 checkpoints | the L2 trigger fires (second writer, external verifier, served proofs, or scale) |
| No advisory overlay | reviewers demonstrably need ranking beyond the certified grades |
