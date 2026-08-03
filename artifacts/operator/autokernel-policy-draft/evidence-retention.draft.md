<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Staged for operator review per
     artifacts/operator/autokernel-policy-draft/README.md (attestation 1).
     Target: MEASUREMENT.md §5 Governance, appended as a new bullet after the
     2026-08-02 evidence-durability clause (:146-160), plus the §6 note in §4.3 below.
     Author: AutoKernel design pass, 2026-08-03. -->

# DRAFT — Evidence retention and reclamation (`MEASUREMENT.md` §5 amendment)

**Status:** COMPLETE AND SIGNABLE (revised 2026-08-03 after adversarial review) — **no `[BLOCKED-ON]`
bindings and no unfilled tokens in the normative text.** Every threshold is a *procedure that derives
a value at run time* or a *named field supplied by the campaign manifest*, never a literal. It is
signable against an implementation that does not exist yet, because it ratifies contracts and never
referents.
**Amends:** `MEASUREMENT.md` §5 Governance — extends *"Evidence must be DURABLE, not merely hashed"*
(`MEASUREMENT.md:146-160`) with the retention half that clause left open.
**Owns, for the whole constitution:** the definition of `storage_floor_bytes_free`. `P-AK-SEARCH-1`
precondition 7 references it by name and defines no second floor.
**Interacts with:** the prime directive (`MEASUREMENT.md:174-175`) and the explicit dump list
(`MEASUREMENT.md:223-229`). It **narrows nothing** in either, **edits neither**, and — corrected after
review — **derives no authority from either**. `:223-229` is the 2026-06 reconciliation's explicit
dump list, whose rule is that everything not enumerated *is kept*, and whose sole "operator call" is
~1.2 GB of superseded embedding blobs under `repl_memory/sessions/`. It confers no general reclamation
authority, so §3.7 is a **fresh, self-contained, bounded grant** rather than a slice carved out of a
larger pool. That distinction matters: framing it as a slice would write into the permanent record an
interpretation that a closed enumeration is a delegable authority pool, enlarging what future
amendments could carve from.
**Presented in:** attestation 1a, as item 5 of
[`RATIFICATION_PACKAGE.md`](RATIFICATION_PACKAGE.md).
**Owning handoff:** `handoffs/active/autokernel-research-loop.md` §3.7 (`:475-503`), §5.8
(`:690-706`), §10.5 (`:1476-1482`), §14 AK0 (`:1871-1872`).

---

## 1. The defect this closes

The constitution now states two rules that, taken together, have no physical solution.

1. **Nothing may be destroyed.** *"Prime directive: never destroy primary records; demote, label, or
   re-derive interpretations"* (`MEASUREMENT.md:174-175`). The only enumerated deletions are the
   closed list at `:223-229` — whose own rule is that *everything else … is kept* (`:223-224`), and
   whose single discretionary item is *"Disk-hygiene candidates (~1.2GB superseded embedding blobs
   under `repl_memory/sessions/`) are an operator call, not contamination"* (`:227-229`). Read
   correctly, that list is an **inventory of past deletions**, not a grant of reclamation authority.
   There is therefore no sanctioned route by which a running loop reclaims anything at all.
2. **Everything must be kept in-repo.** Evidence behind a ratified or production-affecting claim
   *"MUST therefore live inside a repository, under `epyc-inference-research/data/<campaign>/`, with
   a `SHA256SUMS` and a README"* (`MEASUREMENT.md:149-152`).

An autonomous kernel-research loop that produces build trees, worktrees and profiler traces on every
iteration, retains all of them, and may never reclaim any of them without a human in the loop, halts
on a full disk within a handful of campaigns (`handoffs/active/autokernel-research-loop.md:693-695`).

**Measured 2026-08-03T00:46Z on this host** (`df`/`du`). **These figures are OBSERVATION-GRADE host
telemetry, cited as motivation only.** They carry no protocol id and no `category=` label, they gate
nothing, and no normative text below depends on them — which is why `MEASUREMENT.md:11` and `:85-95`
are satisfied rather than violated by their appearance here. The side-by-side against the handoff's
2026-08-02 figures is a **labelled analysis** of drift between two dated readings
(`MEASUREMENT.md:83-84`), not a comparison of two arms:

| Quantity | Measured | Handoff §5.8 (`:692`) |
|---|---|---|
| `/mnt/raid0` (`/dev/md127`, 3.7T) | **96% used, 156G available** (166,441,676,800 B) | 96% full, 162G free |
| `epyc-inference-research/data/` | **118G** (`cpu_optimization` 64G, `op2_canonical_window` 24G, `cpu_prefill_compute` 24G) | 118G |
| llama worktrees under `/mnt/raid0/llm/` | **41G across 18 trees** (`llama.cpp-experimental` 13G, its preserved copy 15G, production 5.0G) | 41G, 13 worktrees |

The free-space figure has moved 6G in one day and the worktree count has moved from 13 to 18. That
drift is itself the argument: a literal floor ratified into an append-or-version protocol
(`MEASUREMENT.md:116-118`) would already be stale.

**A verified live exposure motivates the permanent classes.** The v8 quality gate compared against a
*preserved* v7 binary, because rebuilding an old commit under a drifted toolchain does not reproduce
it (`handoffs/active/autokernel-research-loop.md:1476-1482`). That binary exists — 144M at
`/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff`, `cpu-bin/llama-server` present — and I
confirmed it is **not inside any git repository** (`git rev-parse --is-inside-work-tree` → *"not a
git repository"*), while `/mnt/raid0/llm/kernels/archive/` is **empty**. It is also outside the
durability enforcer's scope *by construction*: that validator's whitelist explicitly excludes
*"kernel build trees"* as *"inputs and system paths, not measurement results"*
(`epyc-inference-research/scripts/validate/check_evidence_durability.py:35-37`; note the enforcer
lives in the research repo, not epyc-root as `MEASUREMENT.md:155` implies — recorded at
`handoffs/active/autokernel-research-loop.md:481-482`). So the single artifact a ratified production
cutover bound its quality claim to is today unlabelled, untracked, unreachable by the enforcer, and
one `rm -rf` from unverifiable. This rule is not only a licence to delete; it is first a duty to
**protect**.

## 2. What does NOT change

- **The prime directive is untouched.** No primary record becomes deletable. This rule reclaims
  *derivable bytes* and never a record; §3's transition is `durable-untracked →
  hash-and-provenance-only`, which the constitution already blesses as a legitimate evidence state
  (`MEASUREMENT.md:153-155`).
- **The explicit dump list at `:223-229` is still closed.** Only the operator may add to it. Nothing
  in this rule makes a contaminated corpus, a superseded row, or a dated backup deletable.
- **The `repl_memory/sessions/` blobs at `:227-229` stay an operator call.** They are not AutoKernel
  artifacts and this rule does not reach them.
- **The three reconciliation verbs are unchanged** (`MEASUREMENT.md:177-184`). Expiry is not
  `retire-view`, not `demote-to-prior`, not `retro-certify`; it acts on bytes, never on status.
- **In-repo durability is unchanged and is strengthened, not relaxed.** Every evidence citation still
  resolves in-repo per `:150-156`; this rule adds a required class field to the citation.
- **No new authority over anything else.** Nothing here authorizes any of the **five** enumerated
  human-only writes at `MEASUREMENT.md:140-142` — *"era-registry rows, **this constitution and its
  annexes**, AutoPilot baseline-state applies, production freezes/cutovers, host reboots"*. The
  emphasised member is the one an earlier revision of this list omitted; it is the one most relevant
  to a clause that could otherwise be read as amending a protocol, and §3.7 item 8 states it
  normatively rather than leaving it to be inferred from item 7.
- **No status change to any existing citation.** The class field is required of loop-produced
  citations only; no pre-existing claim becomes an observation on the strength of this clause.
- **No git history is ever rewritten.** Artifacts of class *carried-in-git* are outside the delegated
  slice entirely (§3.7).

## 3. Normative text (proposed append to `MEASUREMENT.md` §5)

> - **Evidence retention and reclamation** *(operator-ratified `<APPLY_DATE>`)*: durability is a duty to
>   keep, and keeping has a physical limit. This clause makes that limit explicit, bounds it with a
>   procedure, and delegates exactly one narrow reclamation authority. It extends, and supersedes
>   nothing in, *"Evidence must be DURABLE, not merely hashed"* (`:146-160`).
>
>   **3.1 Durability class — required on every artifact.** Every artifact produced by an autonomous
>   research loop MUST record exactly one **durability class** at creation, in its campaign manifest
>   and in every citation of it:
>
>   - **`carried-in-git`** — tracked in a repository and reachable from a pushed ref, so it survives
>     a fresh clone. The strongest class, and the only class for events, reduced metrics, patches,
>     hashes and manifests.
>   - **`durable-untracked`** — the bytes live on this host, at a locator and on a filesystem both
>     recorded in the campaign manifest, and are **covered by a `SHA256SUMS` that is itself
>     carried-in-git under `epyc-inference-research/data/<campaign>/`**. The bytes need NOT sit inside
>     a repository working tree: build trees, worktrees and preserved binaries live under
>     `/mnt/raid0/llm/`, and `:153` already names build trees as the archetypal artifact too large to
>     carry. What must be in git is the **hash chain**, not the blob. The artifact survives on the
>     host; it does NOT survive a fresh clone, and the class MUST be declared rather than inferred,
>     because the enforcer named at `:155` verifies location and existence, not tracked-ness.
>   - **`hash-and-provenance-only`** — the bytes are not retained; the record retains the artifact's
>     SHA-256, byte size, collection recipe, and provenance. Already permitted by `:153-155` for
>     artifacts too large to carry, *"and the citation says so explicitly"*.
>
>   A class is a fact about the artifact, not a preference. **This rule creates a classification duty,
>   and it is prospective.** An artifact created after ratification whose class is unrecorded is not
>   durable evidence and MUST NOT be cited by a ratified claim. A **pre-ratification** citation is NOT
>   demoted by the absence of a class field: it opens a **retention-defect item**, tracked to closure
>   by the measurement-debt queue (`:164-166`). The distinction is load-bearing — demoting a
>   pre-existing citation would be a status change over a historical record, and status changes are
>   governed by the three verbs at `:177-183`, none of which is "de-cite".
>
>   **Three states, not two.** A later verifier MUST distinguish: artifact present and hashing
>   correctly → **conforming**; artifact absent **with** a tombstone (§3.5) whose predicate is
>   satisfied → **expected absence**; artifact absent **without** a tombstone → **defect**. An
>   artifact present *and* tombstoned is an **incomplete reclamation** and MUST be resolved, never
>   ignored.
>
>   **3.2 Expiry is a class transition, not a deletion.** The only reclamation this clause authorizes
>   is the transition `durable-untracked → hash-and-provenance-only`, recorded by a tombstone event.
>   The primary RECORD — what existed, its hash, its size, its provenance, and why it is gone —
>   survives the artifact. `carried-in-git` artifacts are NEVER expirable by this clause; removing
>   one would be a history rewrite, which remains operator-only.
>
>   **3.3 Permanent — never expirable under this clause.** MUST be retained, and MUST be classed
>   `carried-in-git` where size permits:
>
>   1. the append-only event journal and every event in it, including failures, crashes, timeouts,
>      rejected proposals, negative results, and invalidated runs;
>   2. reduced metrics and the raw samples from which each reduction is reproducible;
>   3. patches, diffs, and content-addressed source snapshots;
>   4. hashes, manifests, `SHA256SUMS`, and README files;
>   5. every tombstone (§3.5);
>   6. **incumbent production binaries and their linked libraries**, for every production version
>      that any un-superseded claim, gate, or quality-transfer comparison names as its comparison
>      anchor. That set is DERIVED from the claim record, never fixed by a number; it is at minimum
>      the immediately preceding production version, because rebuilding an old commit under a drifted
>      toolchain does not reproduce the binary a prior gate compared against. Where such a binary is
>      too large to carry in git, it is classed `durable-untracked` with a recorded second location,
>      and its removal is operator-only.
>
>   **A preserved incumbent binary that is not classed and not covered by a `SHA256SUMS` is a
>   RETENTION DEFECT**, reported as such, whether or not any campaign is running. **This duty binds at
>   ratification and is discharged by a reported defect, never by a gate**: it creates no blocker, it
>   invalidates no claim, and it removes no evidence. Its whole effect is to convert a silent exposure
>   into a tracked item. The first such item is named in the ratification bundle, so the report exists
>   before the loop that would rely on it does.
>
>   **3.4 Expirable — the closed class list and the predicate.** Exactly three artifact kinds are
>   expirable, and only when EVERY conjunct of the predicate below holds. The list is closed:
>   widening it is an amendment (`:116-118`), never a runtime decision.
>
>   | # | Kind | Class-specific conjunct |
>   |---|---|---|
>   | E1 | Rejected-candidate build tree (object files, build directory, linked binaries of a candidate that is not, and is not an ancestor of, a retained champion) | The candidate's terminal disposition is recorded; its patch bundle, source-tree hash, binary and linkage SHA-256s, and reduced metrics are retained at `carried-in-git` |
>   | E2 | Worktree of a retired campaign | The campaign has reached a terminal stop state; its evidence directory verifies against its `SHA256SUMS`; and **every commit the worktree holds is reachable from a ref on a REMOTE**, so the source survives in git rather than in the checkout. A local ref is insufficient: `/workspace/repos/<name>` and `/mnt/raid0/llm/<name>` are one clone, so a local ref and the worktree share a failure domain, and "the source survives in git" would be merely likely rather than true |
>   | E3 | Raw profiler trace older than the lineage it informed | The reduction derived from the trace is retained; the mechanism finding it supported is either superseded or re-confirmed against a later anchor; and the trace's collection recipe is recorded in the tombstone so it can be re-collected |
>
>   **An expiry is conforming only if ALL of** the following hold, in addition to the class-specific
>   conjunct:
>
>   1. **Ownership** — the artifact was created by this loop, inside a namespace root drawn from
>      `namespace_roots`. **`namespace_roots` is an operator-set prefix list**: a campaign manifest
>      MAY name a subset of it and MUST NOT extend it. A delegate that declares its own delete
>      boundary has no boundary — declaring `/mnt/raid0/llm/` a root would bring every pre-existing
>      worktree inside the fence, leaving only "created by this loop" as a guard, which is also a
>      loop-recorded fact. Nothing created by a human, by another session, or before the campaign is
>      in scope, regardless of where it sits.
>   2. **Class** — the artifact's recorded class is `durable-untracked`.
>   3. **Derivation closure** — the tombstone names the retained records from which the artifact
>      could be re-derived or which supersede it, by event id and hash. If that field cannot be
>      filled, the artifact is NOT expirable. There is no "unrecoverable but expendable" case.
>   4. **No live binding** — no un-superseded record names the artifact as its comparison anchor, no
>      open waiver depends on it, it is not the current champion or an ancestor of it, and it is not
>      referenced by any open release package or operator decision package.
>   5. **Retention hold** — the campaign that produced it has reached a terminal stop state AND at
>      least `retention_hold_boundaries` subsequent operator boundaries (attestation, freeze, or
>      campaign start) have passed. The hold is counted in **events, not days**, so it cannot expire
>      on a quiet weekend. `retention_hold_boundaries` is an **operator-set minimum**; a campaign
>      manifest MAY declare a longer hold and MUST NOT declare a shorter one. Whoever sets the hold
>      sets how long evidence must survive before it can be reclaimed, so the delegate does not set it.
>   6. **Quiescence, established by claim rather than by self-knowledge** — the executor **holds the
>      region claim covering the affected filesystem** for the duration of an expiry batch. Unlinking
>      tens of gigabytes perturbs page cache and I/O, which the cache-preparation rules at
>      `measurement/protocols/bench-cpu.md:46-51` and the cold/warm pairing gate at
>      `measurement/protocols/bench-cpu.md:210-212` depend on — and the host is shared, so "no
>      measurement window of *mine* is open" is idle sensing, which *"is never a claim"* (owning
>      handoff invariant 9, `:524-525`). After any expiry, the next arm re-runs its declared cache
>      preparation.
>   7. **Explicit target** — the artifact is removed by the exact path the loop recorded when it
>      created it. Glob, pattern, wildcard, `find -delete`, and name-matching sweeps are FORBIDDEN on
>      this shared host, for the same reason name-pattern process kills are (`CLAUDE.md:84`).
>   8. **Fresh hash** — the SHA-256 written into the tombstone is computed from the artifact
>      immediately before removal, never copied from an earlier manifest.
>
>   **3.5 Tombstones.** Every expiry MUST append an event of schema
>   `epyc.autokernel.tombstone.v1` carrying, at minimum: the artifact's locator as it existed; its
>   SHA-256 (for a directory, the hash of its per-file `SHA256SUMS`); its byte size; its durability
>   class at creation; its expirable kind (E1/E2/E3) and the evidence, by event id, that each
>   conjunct of §3.4 was satisfied; the derivation closure; the campaign id; the executing component's
>   identity; the ratification receipt this authority derives from; the timestamp; and free bytes on
>   the target filesystem before and after.
>
>   **Ordering is fail-closed and MUST NOT be reversed**, following the transaction precedent at
>   `measurement/protocols/bench-cpu.md:132-140`: append and fsync the tombstone, and fsync its
>   containing directory, BEFORE unlinking anything. A crash between the two leaves a tombstone for a
>   still-present artifact — an incomplete reclamation, which recovery either completes or marks
>   aborted. A crash in the reverse order would leave a destroyed artifact with no record, which is
>   the one outcome the prime directive forbids.
>
>   **3.6 Quota, floor, and the `DISK_PRESSURE` stop state.** Two limits, deliberately distinct,
>   because conflating a self-inflicted budget with a shared-resource emergency produces the same
>   confusion as conflating a plateau with a broken searcher:
>
>   - **Quota (campaign-scoped)** — `max_storage_gb`: the campaign's own footprint over its declared
>     namespace roots, against the budget recorded in its manifest. The footprint is **measured** at
>     each iteration boundary and journaled, never estimated. Exceeding it is a budget stop. It is
>     NOT a licence to expire.
>   - **Floor (host-scoped)** — **`storage_floor_bytes_free`**: free space on each filesystem actually
>     hosting a namespace root, resolved at run time and read fresh after outstanding writes are
>     fsynced. **This is the constitution's only definition of a campaign storage floor**, and every
>     other clause that needs one references it by this name rather than deriving a second. It is a
>     quantity of **bytes free on a host filesystem**, never a quantity of bytes consumed by a
>     campaign; conflating the two produces a figure whose sign is undefined. It is DERIVED at
>     bootstrap, not a constant: at least the maximum of
>     **(a)** the largest single artifact the campaign is contracted to produce, including a sealed
>     release bundle plus the incumbent archive it must write;
>     **(b)** the measured high-water transient footprint of one complete iteration, multiplied by
>     `storage_safety_factor` recorded in the manifest; and
>     **(c)** `host_reserve_bytes`, an **operator-set value**. It is recomputed per campaign and
>     recorded in the manifest, so it tracks the host rather than a document.
>
>     **`host_reserve_bytes` fails CLOSED, never open.** A campaign whose resolved floor lacks a host
>     reserve is **non-conforming and MUST NOT start**. An unset reserve MUST NOT be read as zero: on
>     a shared host at 96% capacity the reserve is the only input protecting other sessions' work from
>     this loop, and a silently-zero reserve collapses the floor to `max(a,b)`.
>
>     **"Each filesystem" is resolved by mount identity, not by path prefix.** The executor records
>     the device or mount identifier backing each namespace root at the moment it reads free space,
>     because the same path resolves to different filesystems from different execution contexts
>     (`/mnt/raid0` is `/dev/md127` on the host and can present as an overlay inside a container).
>     A floor evaluated against the wrong filesystem is not a floor.
>
>   Below the floor, the loop enters **`DISK_PRESSURE`**: it quiesces at a boundary, persists,
>   journals the condition, and raises an operator decision package. It MUST NOT resume until
>   headroom is restored.
>
>   **Pressure orders expiries; it never creates eligibility.** Eligibility is decided solely by
>   §3.4. Under pressure the loop MAY execute the backlog of already-eligible expiries, and MAY
>   choose their order by reclaimed bytes. It MUST NOT shorten a retention hold, waive a conjunct,
>   reclassify an artifact, or expire anything outside the closed list in order to keep running. If
>   the eligible backlog does not clear the floor, the correct behaviour is to stop.
>
>   **3.7 Who may execute an expiry.** This is a **fresh, self-contained grant**, bounded by the prime
>   directive at `:174-175` and by nothing else it borrows. It is **not** a slice of `:223-229`, which
>   is an inventory of past deletions and confers no general reclamation authority; that list is
>   untouched by this clause and stays closed. The grant is bounded on five axes at once: **one class
>   transition** (`durable-untracked → hash-and-provenance-only`), **three artifact kinds**
>   (E1/E2/E3), **one creator** (artifacts the loop itself made), **one namespace** (operator-set
>   `namespace_roots`, which a campaign may narrow and may not extend), and **one predicate** (all
>   eight conjuncts of §3.4).
>
>   Within those bounds, a deterministic **reclamation executor** in the campaign control plane may
>   act without a per-expiry signature. It is distinct from the actor that authors candidate source
>   and from the planner. **The LLM may request an expiry; the controller owns disposition from
>   records; the operator owns everything outside the enumerated slice.** A request that does not
>   satisfy §3.4 is refused and journaled as refused, not escalated into a token request.
>
>   **Operator-only, without exception** — this clause delegates none of the following:
>
>   1. any artifact not created by the loop, including every pre-existing worktree under
>      `/mnt/raid0/llm/`, every corpus under `data/` predating the campaign, and the
>      `repl_memory/sessions/` blobs at `:227-229`;
>   2. anything of permanent class under §3.3, including archived incumbent binaries;
>   3. any addition to, or reading-by-analogy from, the explicit dump list at `:223-229`;
>   4. any artifact classed `carried-in-git`, and any git history rewrite or object-store prune;
>   5. any campaign's evidence directory, in whole or in part, at any time;
>   6. any emergency reclamation to escape `DISK_PRESSURE` beyond the already-eligible backlog;
>   7. any change to the expirable list, the predicate, the hold, the floor derivation, or this
>      delegation — each is an amendment under `:116-118`;
>   8. **any write to the measurement trust boundary** — this constitution, its annexes, or
>      `coordination/session-bus/human_only_paths.yaml`. The reclamation executor has no write
>      authority there of any kind, and nothing in this clause may be read as conditioning the
>      enumerated human-only writes at `:141-142`: *"era-registry rows, this constitution and its
>      annexes, AutoPilot baseline-state applies, production freezes/cutovers, host reboots"* — all
>      **five**, including the second, which an authority-granting clause has the most reason to state
>      and the most temptation to omit.
>
>   **Prospective — scoped to expirability, not to the classification duty.** **No pre-existing
>   artifact becomes EXPIRABLE by this clause, and no historical deletion is retro-certified by it.**
>   Expiry applies only to artifacts created after ratification, inside a campaign whose manifest
>   records `storage_floor_bytes_free`, `max_storage_gb`, `retention_hold_boundaries` and its
>   `namespace_roots`. The §3.1 classification duty and the §3.3.6 incumbent-archive duty bind at
>   ratification and are discharged by reported defects; they remove nothing, gate nothing, and
>   demote nothing.
>
>   **Grammar (citation extension — loop-scoped).** Every evidence citation **produced by an
>   autonomous research loop** carries its class:
>   `attest <locator> [durability=<carried-in-git|durable-untracked|hash-and-provenance-only>,
>   sha256=<hash>]`. A citation to a reclaimed artifact carries its tombstone:
>   `attest <original locator> [durability=hash-and-provenance-only, sha256=<hash>,
>   tombstone=<event_id>]`. **A loop-produced citation with no class field is an observation, not a
>   claim. Pre-existing citations and citations produced by human sessions are unaffected and are NOT
>   demoted by this rule** — the canonical exemplar at `:70`, and every citation at `:79`, `:80` and
>   `:96-97`, remain exactly as ratified. A §5 governance clause authored to authorise an autonomous
>   loop does not rewrite the claim grammar for the whole project, and per `:100-101` a general
>   grammar extension would in any case belong in the owning protocol's annex entry rather than here.

## 4. Notes for the ratification bundle

**4.1 Where it lands, and why appending to the CORE file is legitimate.** §5, appended immediately
after the 2026-08-02 durability bullet (`MEASUREMENT.md:146-160`), because retention is the half of
durability that clause left open. `:116-118`'s literal wording says an amendment *"appends to the
owning annex file"* — but §5 **is** the core file's own governance section, and the core file is the
owning file for its own governance clauses. Two ratified precedents establish this reading: the
2026-08-02 durability bullet itself (`:146-160`, CHANGELOG `:241-245`) and the 2026-07-31 category
amendment (`:251-255`), both of which appended to the core file. This item follows them, and the
ledger records that reading so a later reader does not have to reconstruct it. It does **not** belong
in Annex K: Annex K holds the search instrument, and admission test (1) excludes a clause whose
subject is evidence lifecycle rather than kernels (`Annex-K-container.draft.md` §3).

**4.2 What it supersedes.** Nothing. `:223-229` is not edited, not narrowed, and not read as a source
of authority (see the Status block). §3.7 is a fresh bounded grant, and the ledger records that
reading explicitly so a later reader does not mistake silence for a conflict — and so that no future
amendment can cite this one as precedent for carving further slices out of a closed enumeration.
Prior receipt of the clause this one extends: the 2026-08-02 durability amendment, CHANGELOG entry at
`MEASUREMENT.md:241-245`.

**4.3 One optional cross-reference in §6.** `:223-229` currently reads as the complete inventory of
sanctioned deletions. If the operator wants a reader of §6 to find §5's rule, a single appended
sentence suffices — *"Autonomous-loop reclamation of the enumerated expirable classes is governed by
§5 'Evidence retention and reclamation'; this list is otherwise closed and confers no authority
beyond its own enumeration."* — and is the minimum edit that keeps the two sections consistent.
Presented as its own strikeable line (`RATIFICATION_PACKAGE.md` item 6), not folded into §3.

**4.4 Why every number here is a procedure.**

| Quantity a naive draft would fix | Field name | What this draft ratifies instead | Who sets it |
|---|---|---|---|
| Free-space floor in GB | `storage_floor_bytes_free` | Derived per campaign as `max(a, b, c)` of §3.6 | derived; fails closed without (c) |
| Per-campaign storage quota | `max_storage_gb` | Measured footprint against the manifest budget (§3.6) | campaign |
| Retention period in days | `retention_hold_boundaries` | A hold counted in operator boundaries (§3.4 conjunct 5) | **operator minimum**; campaign may lengthen |
| Archive depth (N−1, N−2) | *(derived)* | Every production version any un-superseded claim binds to as its anchor, derived from the claim record; at minimum N−1 (§3.3.6) | derived from the claim record |
| Safety multiplier | `storage_safety_factor` | Calibrated by the campaign's own bootstrap measurement (§3.6) | campaign |
| Host reserve | `host_reserve_bytes` | Floor conjunct (c); **unset ⇒ campaign non-conforming, MUST NOT start** | **operator** |
| Which paths are expirable | `namespace_roots` | Operator-set prefix list, intersected with three named kinds (§3.4) | **operator**; campaign may narrow |

**4.5 Field names are normative, and three of the seven are operator-set.** An earlier revision left
all of these to "whatever the implementation writes into the manifest", which made the delegate the
author of its own delete boundary, its own retention period and its own emergency threshold. The
three marked **operator** above are not delegate-writable: `namespace_roots` and
`retention_hold_boundaries` bound what may be deleted and for how long it must survive, and
`host_reserve_bytes` is the only input protecting other sessions on a shared host. A campaign manifest
may **narrow** an operator-set value and MUST NOT widen it; a manifest that widens one is a schema
violation, not a configuration choice.

None of these depends on AK1–AK6 existing. Each is satisfied by a named field, and a manifest that
omits one makes its campaign non-conforming — which is the enforcement mechanism, and it works before
any code is written. The corresponding schema delta to `epyc.autokernel.campaign.v2` is owed by AK1
and is registered in *Residual dependencies* item 5.

## 5. Ratification checklist (attestation 1a, this item only)

- [ ] Append §3 verbatim to `MEASUREMENT.md` §5 — append, never edit in place (`:116-118`).
      Substitute `<APPLY_DATE>`; **no other token remains in the normative text**.
- [ ] Decide §4.3 (the one-sentence §6 cross-reference) as a separate strikeable line
      (`RATIFICATION_PACKAGE.md` item 6).
- [ ] Add the `MEASUREMENT.md` CHANGELOG entry — **verbatim text supplied** at
      `RATIFICATION_PACKAGE.md` §E, not described.
- [ ] Record in `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md` (full path; the
      only other `RATIFICATION_LEDGER.md` in the repo belongs to the `measurement-v2-draft` bundle):
      the `MEASUREMENT.md` preimage hash; that `:223-229` is unedited and confers no authority this
      clause relies on; the five axes bounding §3.7; the supersession statement (*supersedes nothing;
      extends the 2026-08-02 durability clause, CHANGELOG `:241-245`*); and the SHA-256 of the v7
      incumbent backup recorded as the first §3.3.6 retention-defect item.
- [ ] Record the first retention-defect item: `/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff`
      (144M, `cpu-bin/llama-server` present, verified outside any git repository, no `SHA256SUMS`) —
      the artifact the v8 quality gate compared against. Compute its SHA-256 into the bundle. This is
      a **report**, not a gate: the v8 freeze is not reopened and no v8 claim changes status.
- [ ] No `MEASUREMENT.md` §2 registry row — this is a governance clause, not a protocol; it emits no
      metric and gates no measurement.
- [ ] Confirm no `human_only_paths.yaml` change is needed: this clause adds no new human-only path,
      and `MEASUREMENT.md` is already covered at `coordination/session-bus/human_only_paths.yaml:26-28`
      as a **literal** entry, which the hook does enforce.
- [ ] Verify every cited path resolves in-repo, using
      `epyc-inference-research/scripts/validate/check_evidence_durability.py` (the enforcer lives in
      the research repo, not epyc-root as `:155` implies — owning handoff `:481-482`). Re-verify the
      §1 `df`/`du` figures at apply time — they are dated observations, not constants.
- [ ] Pre-validate the apply command sequence end-to-end via `apply_ratification.sh`
      (`MEASUREMENT.md:145`).
- [ ] Present with the other attestation-1a items as one attestation with strikeable lines.

## 6. Questions resolved into §3 (ledger note, not open questions)

An earlier revision posed three questions whose answers changed §3's normative wording, which meant
there was no single ratifiable text. All three are now **resolved into §3 as the draft itself
recommended**; they are recorded here so the alternatives are visible as considered-and-rejected
rather than unconsidered.

1. **Does the §3.3.6 incumbent-archive duty bind now, or at first freeze?** → **Binds now**, as a
   reported defect rather than a blocking gate (§3.3.6, and the Prospective clause scoped to
   expirability). Deferring it would leave the artifact the v8 quality gate depends on protected only
   by nobody having run `rm`.
2. **Does E2 require a remote ref or a local one?** → **Remote** (§3.4, E2 row). A local ref shares a
   failure domain with the worktree, so *"the source survives in git"* would be merely likely.
3. **Is quiescence bound to the loop's own windows or to the region-claim state?** → **The region
   claim** (§3.4 conjunct 6). The host is shared; idle sensing is never a claim.

## 7. Residual dependencies

Bindings that could not be expressed as a contract or a procedure, with the reason. **This list is
intentionally short, and none of these blocks signature.**

1. **The E1/E2/E3 kind list is enumerated, not derived — and deliberately so.** A predicate general
   enough to derive the list ("anything re-derivable from retained records") would authorize far more
   than three kinds, and authority creep is the failure mode this project fears most. The cost is
   real: a fourth expirable kind discovered during AK1–AK6 requires a second amendment rather than a
   configuration change. That is the intended trade, recorded here so it is chosen rather than
   discovered.
2. **`epyc.autokernel.tombstone.v1` is defined by this clause, not referenced from an implementation.**
   §3.5 fixes the minimum field set; the concrete serialization is AK1's, and AK1 may add fields but
   may not omit one. Should AK1 find a required field genuinely unfillable, that is an amendment, not
   a waiver. No signature is blocked, because the field set is the contract.
3. **The §1 disk figures are dated observations, not constants**, and no normative text depends on
   them. They will be stale at apply time; §5 requires re-reading them then. They appear in the draft
   as motivation only.
4. **A campaign-manifest schema delta is owed by AK1.** §3.4 and §3.6 bind seven named fields
   (`namespace_roots`, `retention_hold_boundaries`, `storage_floor_bytes_free`, `max_storage_gb`,
   `storage_safety_factor`, `host_reserve_bytes`, plus the per-artifact `durability_class`), of which
   `epyc.autokernel.campaign.v2` (owning handoff `:837-843`) today carries only `max_storage_gb`.
   Three of them are **operator-set** and belong in the human-only policy plane the manifest
   references by digest (`policy_ref.policy_bundle_sha256`, handoff `:833-836`,
   *"authority/thresholds live in the human-only policy plane"*), not in the manifest the compiler
   writes. Expressed here as a fail-closed conformance condition rather than as a blocked binding: a
   manifest that omits a field makes its campaign non-conforming, which binds before the schema
   exists. **What this does not do is invent the field names at run time** — they are fixed by §3.6
   and §4.4 above, so the delegate cannot define their meaning.
5. **Enforcement is unimplemented and named as a duty, not as a tool.** Unlike the 2026-08-02
   durability clause, which names `check_evidence_durability.py` as its enforcer (`:155-156`), §3
   names no script — the retention checker does not exist, and naming one would violate the rule that
   no binding may reference an artifact that does not yet exist. The clause is therefore enforced by
   the conformance conditions themselves (an unclassed artifact is not durable evidence; a manifest
   missing a floor makes its campaign non-conforming), which bind without tooling. Extending the
   existing enforcer to check class fields and tombstones is AK1 work and needs no further
   ratification, because §3 already states what a conforming artifact looks like.
