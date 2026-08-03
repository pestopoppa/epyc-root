<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Staged for operator review per
     artifacts/operator/autokernel-policy-draft/README.md.
     Target: measurement/protocols/bench-cpu.md (Annex B) ONLY, appended as a new
     section §E. The Annex G extension is DEFERRED — see §6.
     Author: AutoKernel design pass, 2026-08-02. Revised 2026-08-03 after adversarial review. -->

# DRAFT — §E: the no-concurrent-inference exclusion precondition (Annex B)

**Status:** COMPLETE AND SIGNABLE (revised 2026-08-03). Every binding below is a **contract** or a
**procedure** whose value is supplied at run time by the run attestation or by a field an existing
ratified protocol already mandates. No binding names an artifact that does not exist at signature
time, no threshold is a literal, and **no protocol loses a satisfiable precondition path**.

**Amends:** the `no concurrent inference` precondition clause of `P-BENCH-1`
(`measurement/protocols/bench-cpu.md:15-16`), and thereby every Annex B protocol that inherits it.
**Creates:** no new protocol id, no registry row, no metric, no reps rule.
**Presented in:** attestation 1a, as item 4 of [`RATIFICATION_PACKAGE.md`](RATIFICATION_PACKAGE.md).
**Owning handoff:** `handoffs/active/autokernel-research-loop.md` §3.5 (`:441-457`), §2.6 (`:310-314`),
invariants 9–10 (`:524-527`), §14 AK2 (`:1946-1968`).

---

## 0. What changed after review, and why the scope shrank

The earlier revision of this item appended one identical §E to **both** Annex B and Annex G, defined a
two-stage regime (Stage I interim enumerator → Stage T target), and pinned a sanctioned enumerator
path into `human_only_paths.yaml`. Adversarial review found that, as drafted, **signing it would have
made every GPU measurement observation-grade on day one** and would have bound the constitution to a
tool that does not exist. Five findings drove the rewrite:

1. **It bricked the GPU protocols.** Stage T was unreachable on GPU (no conforming device claim
   exists — R1), Stage I required a pinned enumerator that does not exist and was explicitly
   fail-closed, and Stage I was available *only while a backend was not Stage-T-eligible*. Every
   `P-GPU-1`, `P-DFLASH-LINEUP-1` and `P-SHED-1` run started after ratification would therefore have
   had **no satisfiable precondition path at all** — strictly worse than the status quo the item
   exists to repair, and disclosed nowhere.
2. **Annex G never mandated the banned operation.** `gpu-cross-device.md:28-30` reads *"`llama-server`
   / AutoPilot / KFD **PID checks** before and after"* — a PID check, not a name pattern. `pgrep`
   appears **exactly once** in the entire annex corpus, at `bench-cpu.md:15`. The whole Annex G half
   of the amendment superseded a clause that was never in conflict.
3. **`E.1.4`'s sanctioned enumerator does not exist.** `scripts/utils/inference_preflight.sh`
   (handoff `:450`) is an open AK2 checkbox. Pinning it into `human_only_paths.yaml` would put an
   unverifiable line into a file whose own header promises *"real paths, verified to exist"*
   (`human_only_paths.yaml:21-24`) — and the sibling `human-only-paths-delta.draft.md:157-165` cites
   that exact header to **refuse** an unverifiable entry. Two items on one signature instructing
   opposite behaviour on one human-only file.
4. **The load-bearing factual claim was wrong.** The earlier text called `bench-cpu.md:53-76` *"a
   quantitative, entirely name-free contamination detector"*. It is not name-free: `:53-54` requires a
   *"competing llama/AutoPilot/KFD witness"*, `:63-64` makes *"no competing … witness"* an
   interval-**eligibility** condition, and `:72-74` makes a competing witness anywhere in the arm an
   unconditional invalidation. The premise for *"this is a generalisation rather than an invention"*
   was a misquote of the constitution used to justify amending it.
5. **The campaign manifest was made constitutionally load-bearing.** Stage-T eligibility was latched
   *"as recorded in the campaign manifest"* — an agent-written artifact, with no human verification,
   and one-way. A hand-run operator bench under P-BENCH-1 produces no campaign manifest at all, so the
   most common measurement on this host had no defined path.

**What survives, and it is the valuable part:** the attribution-class model, the claim-witness
contract, own-scope enumeration, the residual-load witness, and the precondition-witness grammar. What
is deferred: the Annex G extension, the Stage I enumerator, and the manifest-latched staging. Deferred
items are registered at `RATIFICATION_PACKAGE.md` §D (D1, D2), not silently dropped.

---

## 1. The contradiction

`CLAUDE.md:84` — *"Kill only PIDs you captured yourself. **NEVER `pkill`/`pgrep` on a name pattern on
this host**"* — with origin `INC-20260731-broad-process-pattern-kills`
(`docs/reference/agent-config/INCIDENT_LOG.md:75-83`).

**Exactly one ratified clause mandates what that bans**, and one digest line restates it:

| Where | Text |
|---|---|
| `measurement/protocols/bench-cpu.md:15-16` | *"**Preconditions (all enforced or attested)**: no concurrent inference (`pgrep llama` zombie check; benches require a region claim per `feedback_no_concurrent_inference` as amended 07-27)"* |
| `agents/shared/MEASUREMENT_POLICY.md:38` | *"Host-health preflight … `pgrep` zombie check."* |

`gpu-cross-device.md:28-30` is **not** in this table, and the earlier revision was wrong to put it
there: it requires *PID checks*, which are satisfiable without any name pattern, by the device PID
mapping `gpu-cross-device.md:24-27` already mandates.

A conforming Annex B evaluator therefore cannot satisfy the protocol it must run under. The handoff
records this as blocking *"every protocol-conformant measurement"* (`:314`).

**Read the incident precisely, because the precision is the whole argument.** The incident log says
the failure was *"a broad process pattern (`llama-server -m`) used to 'clean up' a benchmark"* which
*"killed **another agent's running server — twice in one day**"*, and separately that *"`earlyoom` was
killed by a pattern sweep because its own command line contains `--ignore
^(llama-server|sd-server)$`"* (`INCIDENT_LOG.md:76-79`). It then generalises: *"on a shared box any
name-based pattern is a wildcard over other sessions' processes, and a guard's argv necessarily
contains the names it guards"* (`:80-81`).

Two distinct harms are compounded in that sentence, and they have different blast radii:

- **The kill harm.** A pattern that selects a *signal target* converts every false positive into a
  destroyed process belonging to someone else. Both recorded losses are of this kind.
- **The selection harm.** A name pattern is simultaneously over-inclusive (it matched a guard whose
  job is to name the guarded) and under-inclusive (it names only what someone thought to name).

**§E resolves the contradiction by removing the need for the read entirely**, not by narrowing the
prophylactic margin around it. There is no Stage I in this revision and no sanctioned enumerator:
a conforming run either establishes the precondition by claim, own-scope and residual-load witness
(§E.3), or it establishes it exactly as the unamended protocol text already says (§E.2, `LEGACY`).
Neither path invokes a name pattern that §E authorises, because §E authorises none.

## 2. What the precondition is actually establishing

Naming the property matters more than replacing the instrument, because the replacement has to be
argued against the property, not against the instrument.

**The property:** *for the whole duration of the measurement window, the resources the run measures
are not being consumed by work the run did not launch* — because such consumption contaminates the
samples, and the contamination is not visible in the number.

`pgrep llama` is a **proxy** for that property, and it is a weak one in five separate ways:

1. **It samples an instant; the property is about an interval.** The scan happens at t₀; the window
   is [t₀, t₁]. Annex G already names this failure in another protocol: *"observing the lane 'looks
   free' is TOCTOU, not exclusion"* (`gpu-cross-device.md:142-143`). The handoff raises it to an
   invariant: *"Resources are acquired, not observed … Idle sensing is never a claim"*
   (`autokernel-research-loop.md:524-525`).
2. **Contamination does not require the string `llama`.** A ROCm profiler, an eval harness, a
   whisper.cpp or qwentts.cpp server (both are production kernels — `CLAUDE.md` §Experimental Kernel
   Workflow), a `-j192` build, or a large `curl` onto the same RAID all contaminate a
   bandwidth-bound decode measurement and none of them match.
3. **It matches things it should not**, including guard processes whose argv contains the guarded
   names (`INCIDENT_LOG.md:77-79`) and the run's own processes (`scripts/dashboard/hub_supervisor.sh:122`
   had to be deliberately engineered *"self-match-proof"*).
4. **It is silent about intent.** A competitor that is *about to* start is indistinguishable from an
   empty host. The process table cannot represent a reservation.
5. **It fails open.** A missing tool, a renamed binary, or a changed argv yields "clean".

**A claim establishes the same property differently, and more strongly:** it is prospective (held
across the interval, closing 1); keyed by resource rather than by name (closing 2 and 3 for
participants); authoritative about intent, since a would-be competitor is refused at acquisition
(closing 4); fail-closed, since acquisition fails when someone else holds it (closing 5); and it makes
ownership decidable, because holder id, PID and process start time are recorded.

**The residual gap, stated honestly:** a claim binds only participants in the claim discipline. It is
therefore combined below with two name-free legs that cover non-participants — **own-scope
enumeration** (positive accounting of what the run itself launched) and a **residual-load witness**
(detection of foreign consumption *by its effect*, not by its name).

**What is already ratified in Annex B, stated accurately this time:**

- `bench-cpu.md:142-147` (P-BENCH-4) already requires a claim-holder witness verified *"before launch
  AND after server teardown while the lock is still held"*, and already rules that *"a merely
  globally-held region, different owner, or changed holder is a failure"*. §E generalises this and
  cites it rather than duplicating it.
- `bench-cpu.md:53-76` (P-BENCH-PREFILL-1, amended 2026-07-25) ratifies a **quantitative contamination
  detector** — `signed_external_core_equivalents`, computation and pass band `[-1.0, 4.0]` at
  `:66-71`. **That machinery is name-free; its surrounding eligibility and invalidation clauses are
  not.** `:53-54`, `:63-64` and `:72-74` each rest on a *"competing llama/AutoPilot/KFD witness"* —
  a name-based test. §E adopts the **computation and the band at `:66-71` unchanged, by reference**,
  and replaces the three name-witness clauses with the E.3.4 attribution predicate. That is the
  precise, and only, substitution §E performs in Annex B.

## 3. Normative text — proposed append to Annex B

Appended to `measurement/protocols/bench-cpu.md`. **One annex, one location, one amendment history
entry.** (`MEASUREMENT.md:117` says an amendment *"appends to the owning annex file"* — singular. The
earlier revision appended one identical text to two annexes, creating two independently amendable,
separately hash-pinned copies of one normative rule, with no mechanism detecting divergence. Where a
cross-annex rule is genuinely needed, the precedent is `MEASUREMENT.md:121-129`, which states it in
the **core file** and supersedes annex text from there.)

> ### §E — Exclusion preconditions (AMENDMENT, ratified `<APPLY_DATE>`)
>
> **Scope.** This section supplies an **instrument** by which every protocol in this annex may
> establish its no-concurrent-inference precondition, whether that precondition is stated directly or
> inherited. It applies to runs on the `cpu` backend of the llama kernel tree, which is the backend
> whose protocol today mandates a name-pattern process check. It states no rule about any other
> annex, and no protocol outside this annex inherits it.
>
> **What §E does to stringency, stated plainly rather than asserted away.** §E is a
> **reinterpretation** of what counts as satisfying the precondition, and it changes outcomes **in
> both directions**. A dormant foreign server small enough to fall under both E.3.4 tests now passes
> where `pgrep llama` would have failed it; conversely a foreign `whisper.cpp` or `qwentts.cpp`
> server — a production kernel, invisible to `pgrep llama` today — now fails where `pgrep llama`
> passed it. §E also **enlarges** the mandatory evidence set of every protocol in this annex by the
> E.5 witness fields and the E.1.2 residual-load witness at both endpoints. The operator assents to
> both effects, or strikes this item; it is not claimed to be stringency-neutral.
>
> #### E.1 Definitions
>
> **Attribution classes.** Every process observed by any leg below is assigned exactly one class:
> `own` (launched by this run, inside its own scope per E.1.3), `claimed-foreign` (attributable to a
> live claim holder other than this run, per the claim registry), or `unattributed`. An observation
> that cannot be classified is `unattributed`; there is no fourth class and no "probably fine".
>
> **E.1.1 Claim-witness contract.** A *conforming claim* over a resource class (a CPU region set; a
> compute device) is one satisfying ALL of:
> 1. **acquired, not observed** — obtained by an atomic exclusive operation before the window opens,
>    never inferred from an idle reading;
> 2. **exact footprint** — the claim covers every resource the run pins and no resource it does not,
>    per the P-BENCH-4 pattern at `measurement/protocols/bench-cpu.md:144` (over-claiming to
>    manufacture exclusivity is a defect, not a precaution);
> 3. **identified holder** — the receipt records owner id, PID, process start time, purpose, and the
>    campaign or request tag;
> 4. **liveness by identity, not by heartbeat** — a holder is live iff its PID exists AND its process
>    start time matches the receipt; a claim whose holder fails that test is reclaimable and the
>    reclamation is journaled;
> 5. **held across the window and re-verified** — the same holder is verified before launch AND after
>    teardown while the claim is still held, per `measurement/protocols/bench-cpu.md:145-147`, which
>    this contract adopts by reference rather than restating;
> 6. **revocable only by drain** — a revocation marks the claim `revoking` and the holder releases at
>    its own boundary; a forcible steal is a defect, never a procedure;
> 7. **receipt id recorded** in the run attestation.
>
> A claim mechanism satisfies §E.1.1 by exhibiting these properties. This section names no
> implementation, no CLI, and no lock path; the mechanism actually used is recorded, by identity and
> version, in the run attestation. **A run MUST NOT self-designate a mechanism as conforming by
> assertion alone:** the attestation records the mechanism's identity and version, and the
> demonstration that it exhibits properties 1, 4 and 6 — a contention test, a stale-holder
> reclaimability test, and the absence of a forcible-preempt path — is an acceptance obligation on
> whoever supplies the mechanism, discharged once per mechanism version and cited by the attestation,
> not re-argued per run.
>
> **E.1.2 Residual-load witness.** The name-free, resource-side evidence that foreign consumption did
> or did not occur during the window, recorded at both endpoints of the window and retained in full:
> - **CPU** — for any run whose measured footprint includes a **pinned CPU region**, the contention
>   accounting already ratified at `measurement/protocols/bench-cpu.md:66-71`, including its
>   `signed_external_core_equivalents` computation and its `[-1.0, 4.0]` pass band, **applies
>   unchanged, including its own eligibility conditions at `:62-63`**. §E introduces no new CPU band
>   and no new sampling rule. A run with no pinned CPU region records `residual=cpu:n/a` and is
>   evaluated on its other legs alone; the band is never imported as a gate into a context where its
>   eligibility precondition cannot be met.
> - **Host residency** — system-wide mlocked bytes, and a full-process-table enumeration ranked by
>   resident set, each entry assigned an attribution class. This enumeration applies **no name
>   filter** and is therefore not a name-pattern read.
>
> **E.1.3 Own scope.** Every process a run launches MUST be launched into a **run-scoped control
> group** whose identifier is recorded in the run attestation; own-scope enumeration is a read of that
> scope's process list. Where a run-scoped control group is unavailable, process ancestry from the
> run's root PID MAY be used instead, and the attestation MUST record that it was, because ancestry
> loses a reparented or daemonised child and a control group does not. A process in own scope that
> outlives the run is a **hard failure**, never a warning
> (`handoffs/active/autokernel-research-loop.md:725`).
>
> #### E.2 Availability — two paths, and neither is ever removed
>
> A run under any protocol in this annex establishes its no-concurrent-inference precondition by
> **exactly one** of:
>
> - **`WITNESS`** — the three legs of E.3. Available to any run that can hold a conforming claim over
>   its measured footprint, launch into an own scope, and record the residual-load witness.
> - **`LEGACY`** — the precondition established exactly as the unamended protocol text requires,
>   recorded as `preflight=LEGACY` in the run attestation.
>
> **§E never removes a satisfiable path before it supplies one.** `LEGACY` is not deprecated by this
> amendment, is not sunset by it, and does not lapse on any condition stated here. Its retirement, if
> it is ever retired, is a later amendment presented on its own merits with a working substitute in
> hand — and a run choosing `LEGACY` is a disclosure, recorded in the attestation and countable, not a
> defect.
>
> **This section authorises no enumerator and pins no tool.** Where an operator or a runner satisfies
> `LEGACY` by the means the unamended text names, `CLAUDE.md:84` governs that means exactly as it does
> today, unchanged and un-narrowed by §E.
>
> #### E.3 `WITNESS` — claim witness, own-scope enumeration, residual-load witness
>
> `WITNESS` establishes the precondition with **no name pattern anywhere**. Three legs, all required;
> no leg substitutes for another.
>
> **E.3.1 Claim witness.** A conforming claim per E.1.1 is held over **every** resource class the run
> measures, for the entire window, verified before launch and after teardown, receipts recorded.
>
> **E.3.2 Own-scope enumeration.** The run's own scope per E.1.3 is enumerated at both endpoints. At
> the closing endpoint the scope MUST be empty of processes not accounted for by the run's declared
> teardown; a surviving process is a hard failure.
>
> **E.3.3 Residual-load witness.** Recorded per E.1.2 at both endpoints and retained in full,
> regardless of verdict.
>
> **E.3.4 Attribution predicate.** The protocol's own stringency is evaluated over the attribution
> classes, not over process names:
> - Where the owning protocol requires only that the **measured footprint** be uncontended: the
>   `unattributed` set MUST hold no process consuming the claimed resources, and where the run has a
>   pinned CPU region the residual-load value MUST fall in the band ratified at
>   `measurement/protocols/bench-cpu.md:70-71`.
> - Where the owning protocol requires a **quiet host** (the P-BENCH-4 clause at
>   `measurement/protocols/bench-cpu.md:142-143`): additionally, no `unattributed` process may hold a
>   resident set at or above **the smallest model artifact recorded under this run's own
>   release-identity block** (`measurement/protocols/bench-cpu.md:41-44`, which already requires model
>   path, size and SHA-256), and system-wide mlocked bytes MUST be fully attributable to `own` plus
>   `claimed-foreign`. Both thresholds derive from data the run is already required to record; neither
>   is a constant, and neither reads an artifact class no protocol defines.
> - **`claimed-foreign` is disclosure, not automatic failure.** A live disjoint claim holder is
>   co-residency, which is a scheduling matter governed by versioned, staleness-guarded co-residency
>   data (`agents/shared/OPERATING_CONSTRAINTS.md:37`) and disclosed in the run header. Whether it is
>   acceptable is the owning protocol's question, and §E does not answer it.
>
> **Decision-grade under `WITNESS` requires ALL of**: E.3.1, E.3.2, E.3.3 and E.3.4, each recorded in
> the run attestation, in addition to every precondition the owning protocol states and §E does not
> touch. Missing ANY → observation-grade (informs design, gates nothing).
>
> #### E.4 What §E does NOT authorize
>
> §E authorises an **instrument for a precondition** and nothing else. In particular it does NOT
> authorize:
>
> - **signalling anything.** No process may be terminated, stopped, or otherwise signalled on the
>   basis of any enumeration in this section. `CLAUDE.md:84-85` is unchanged: kill only PIDs you
>   captured yourself, verify death, escalate TERM→KILL.
> - **any name-pattern read.** §E sanctions none, interim or otherwise, and creates no precedent for
>   one. Name-pattern reads elsewhere on this host — supervision, scheduling, cleanup, host-busy
>   sensing — remain governed by `CLAUDE.md:84` unchanged, are **outside §E's scope entirely**, and
>   neither void nor validate any run (see R4).
> - **idle sensing as a claim.** An idle device, a free-looking region, or an empty process table is
>   never exclusion (`measurement/protocols/gpu-cross-device.md:142-143`).
> - **dropping any existing evidence field.** Every P-BENCH-* precondition other than the process
>   check remains mandatory and unmodified — host-health tier, governor, `numa_balancing`, THP, cache
>   preparation, live-affinity verification, reps, categories.
> - **removing the region claim.** The region claim required by `measurement/protocols/bench-cpu.md:16`
>   is unchanged and remains mandatory. §E replaces the *zombie check*, never the claim.
> - **latching a stringency regime from an agent-written artifact.** §E defines no per-backend
>   eligibility latch and reads no campaign manifest. `WITNESS` and `LEGACY` are per-run properties,
>   evaluated from the run attestation itself, with no cross-run state.
> - **retro-certification.** No pre-ratification artifact is upgraded by §E, and none is downgraded
>   by it either.
> - **any human-only write.** Era-registry rows, this constitution and its annexes, AutoPilot
>   baseline-state applies, production freezes/cutovers, and host reboots remain human-only
>   (`MEASUREMENT.md:141-142`), and this constitution and its annexes remain amendable only by a
>   human (`MEASUREMENT.md:116-120`).
> - **extension to any other annex.** `P-GPU-1`, `P-SHED-1`, `P-DFLASH-LINEUP-1` and the speech
>   kernels are untouched by §E. When an equivalent is wanted for Annex G it is drafted, argued and
>   presented against Annex G's own text.
>
> #### E.5 Precondition-witness grammar
>
> Recorded in the host attestation that every claim under this annex already references
> (`MEASUREMENT.md:13`):
>
> `preflight=<WITNESS|LEGACY>, claims=[<receipt-id>…], own-scope=<scope-id|ancestry:<root-pid>|n/a>,
> residual=cpu:<signed-external-core-equivalents|n/a>, unattributed=<count>`
>
> A run whose attestation omits any field of this grammar is **observation-grade for the purposes of
> this annex**. This states a rule for §E's own fields; it is not a general principle derived from
> `MEASUREMENT.md:95`, whose *"an unlabelled measurement is not decision-grade"* is the closing line
> of the `category=` rule at `:85-94` and says nothing about preflight fields.
>
> #### E.6 What voids a run
>
> Under `WITNESS`: a claim not held for the whole window, lost, revoked-and-not-drained, or held by a
> different owner or a changed holder at either endpoint; a failed or unrecorded residual-load witness
> at either endpoint; a surviving own-scope process at teardown; or an `unattributed` set violating
> E.3.4. Under either path: an attestation omitting an E.5 field. A voided run is journaled as INVALID
> with its reason and is never silently discarded.
>
> **Prospective.** §E applies only to runs started after ratification. No pre-ratification artifact
> may be retro-certified on the strength of §E. Equally, no pre-ratification run that satisfied the
> superseded clause as written is invalidated by §E — the prime directive is *"never destroy primary
> records; demote, label, or re-derive interpretations"* (`MEASUREMENT.md:174-175`), and this
> amendment changes an instrument going forward, not the standing of history.

## 4. What this supersedes, sentence by sentence

Per `MEASUREMENT.md:116-118`, *"Superseding amendments name what they supersede."* **One span per
disposition, no overlaps** — the earlier revision simultaneously superseded and adopted
`bench-cpu.md:63-64`, which left an apply-time reader unable to determine whether a run with a
competing name-witness is eligible or invalid.

### 4.1 Annex B — `measurement/protocols/bench-cpu.md`

| Locus | Current text | Disposition |
|---|---|---|
| `:15-16` | *"no concurrent inference (`pgrep llama` zombie check; benches require a region claim …)"* | **Instrument superseded.** The phrase *"`pgrep llama` zombie check"* is replaced by §E. The requirement *no concurrent inference* survives verbatim; the region-claim requirement survives and is **promoted** from a co-requirement to the primary evidence. Nothing else in the bullet is touched. |
| `:53-54` | retention of a *"competing llama/AutoPilot/KFD witness"* | **Instrument superseded** by the E.1.2 residual-load witness plus the E.3.4 attribution predicate. The retention *duty* survives; what is retained is the attribution-classed enumeration rather than a name-matched witness. |
| `:63-64` | interval-eligibility clause *"no competing llama/AutoPilot/KFD witness"* | **Instrument superseded** by E.3.4. The eligibility *condition* survives with `competing witness` re-bound to *"an `unattributed` process consuming the claimed resources"*. The `:62-63` target-use eligibility condition is **untouched**. |
| `:66-71` | `signed_external_core_equivalents` computation and `[-1.0, 4.0]` band | **NOT superseded. Adopted unchanged and by reference**, including its eligibility conditions. §E states no band of its own. |
| `:72-74` | *"Any sampling failure, ownership change, swap I/O, or competing witness anywhere in the arm remains an unconditional invalidation."* | **Instrument superseded** for the `competing witness` limb only, re-bound as above. Sampling failure, ownership change and swap I/O are untouched and remain unconditional invalidations. |
| `:142-143` | P-BENCH-4 *"The quiet-host preflight MUST prove no competing inference (witness retained)."* | **Instrument supplied, stringency REINTERPRETED.** The clause never named an instrument; §E supplies one, and E.3.4's quiet-host predicate is the reading. This changes outcomes in both directions — see R3, which the operator should strike or accept deliberately. |
| `:143-147` | P-BENCH-4 region-lock ownership witness | **NOT superseded — this is the precedent §E generalises.** Cited, not duplicated. |
| `:174-178` | P-BENCH-4 *"exactly five … no retry, replace, discard, or pooling"* | **Untouched.** §E states no reps rule and never raises or lowers a fixed count. |
| `:38-44` | P-BENCH-PREFILL-1 release identity | **Untouched, and newly load-bearing:** E.3.4's quiet-host threshold reads the model size this block already requires. §E adds no field here. |

### 4.2 Annex G — `measurement/protocols/gpu-cross-device.md`

**No disposition. Annex G is not amended by this item.** No clause in Annex G mandates a name-pattern
process check; `gpu-cross-device.md:28-30` requires *PID checks*, satisfiable by the device PID mapping
at `:24-27`. There is nothing here to repair, and the earlier revision's Annex G append superseded a
clause that was never in conflict — while simultaneously converting `:28-30`'s explicitly permitted,
disclosed *"declared non-quiesced with reason"* / *"intentionally co-resident"* state into a
precondition **failure**, and adding six fields to a field set `:23` declares closed and
all-mandatory. Both effects are withdrawn with the append.

An Annex G equivalent is deferred to attestation 1b (`RATIFICATION_PACKAGE.md` §D, D2), where it will
be argued against Annex G's own text and presented only once a conforming GPU device claim exists.

### 4.3 Digest delta (same transaction, human-only)

`agents/shared/MEASUREMENT_POLICY.md:38` is a single long bullet. Quoted whole, before and after, so
the operator reads what lands rather than a description of it (`MEASUREMENT.md:145`). The digest is
itself human-amendment-only (`human_only_paths.yaml:29-31`), so it cannot be pre-staged by an agent
and MUST ride in the same signature; otherwise the digest and the constitution disagree, and
`MEASUREMENT.md:20-21` makes the constitution win while agents read the digest — a split-brain that
reintroduces the contradiction on the agent-facing side.

**Discipline note.** `MEASUREMENT.md:117`'s append-or-version rule governs *protocols*; the digest is
a derived agent-facing projection, not a protocol, and is maintained by in-place correction (the
precedent is `apply_v2.sh` step 3, which replaced a digest bullet in place at the v2 apply). The exact
before/after text is carried in `RATIFICATION_PACKAGE.md` §E as verbatim apply text, because a
described delta cannot be pre-validated.

**No `human_only_paths.yaml` change is required by this item.** The earlier revision's enumerator pin
is withdrawn with Stage I. `measurement/protocols/*.md` is a glob already covering the file §E appends
to; **verify, do not amend** — and note that verification means the glob *declares* coverage, which
`Annex-K-container.draft.md` §6 shows is not the same as the hook *enforcing* it.

## 5. Ratification checklist (attestation 1a, this item only)

- [ ] Append §E verbatim to `measurement/protocols/bench-cpu.md` — append, never edit in place
      (`MEASUREMENT.md:116-118`). Substitute `<APPLY_DATE>`; the section heading carries no `DRAFT`
      marker and no unfilled token.
- [ ] Apply the `agents/shared/MEASUREMENT_POLICY.md:38` digest delta in the same transaction, using
      the verbatim before/after text at `RATIFICATION_PACKAGE.md` §E.
- [ ] Add the `MEASUREMENT.md` CHANGELOG entry, verbatim text at `RATIFICATION_PACKAGE.md` §E,
      naming Annex B and the five superseded spans.
- [ ] Record in `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md` every semantic
      delta in §4.1, plus the preimage hash of `bench-cpu.md` and of `MEASUREMENT_POLICY.md`.
- [ ] Confirm R3 (the quiet-host reinterpretation) is presented as its own strikeable sub-line and is
      struck or accepted deliberately.
- [ ] Verify every cited evidence path resolves in-repo (`MEASUREMENT.md:146-156`), using
      `epyc-inference-research/scripts/validate/check_evidence_durability.py`.
- [ ] Pre-validate the apply command sequence end-to-end via `apply_ratification.sh`
      (`MEASUREMENT.md:143-145`).
- [ ] Present with the other attestation-1a items as one attestation with strikeable lines.
- [ ] No registry row is required: §E creates no protocol id. **No `human_only_paths.yaml` edit is
      required either** — that was a consequence of the withdrawn Stage I.

## 6. Deferred with this item — registered, not dropped

| # | What | Why deferred | Precondition to present |
|---|---|---|---|
| D1 | **Stage I sanctioned enumerator** and its `human_only_paths.yaml` pin | `scripts/utils/inference_preflight.sh` does not exist (handoff `:450`, AK2 open at `:1965-1966`); pinning it would put an unverifiable line in a file whose header promises real paths (`human_only_paths.yaml:21-24`) | AK2 delivers the wrapper; the path exists; the human-only entry rides one merged gate-list line with one terminal pin rewrite |
| D2 | **Annex G equivalent of §E** | Annex G mandates no name pattern, so there is nothing to repair today; and a GPU `WITNESS` path is unreachable until a conforming device claim exists (R1) | A conforming MI210 device claim exists and passes E.1.1's acceptance obligation; the amendment is then argued against `gpu-cross-device.md:23-30` and `:142-143` on their own terms |

## Residual dependencies

Four items. None blocks signature; each is disclosed because silence would be worse than the
disclosure.

**R1 — The GPU claim substrate does not exist, and Annex G already presumes it.**
`handoffs/active/autokernel-research-loop.md:310` records that `region-lock` is CPU-only and that the
only GPU lease in the codebase is process-local, while `measurement/protocols/gpu-cross-device.md:142-143`
(P-SHED-1, ratified) already requires *"the GPU device claim ACQUIRED via `region-lock`"*. **That gap
predates this draft, is not created by it, and is not closed by it.** A strict reading of P-SHED-1
`:142-143` is currently unsatisfiable on this host by any route. §E as presented touches Annex G
not at all, so it neither worsens nor repairs that; the repair is D2, and it needs the claim first.

**R2 — The claim mechanism is a contract, and the strong instrument is deliberately unpinned.** E.1.1
ratifies the claim *contract* and names no implementation, because naming one would bind the
constitution to an artifact that may be replaced. The earlier revision inverted the protection —
pinning the *weak* instrument (a read-only enumerator, whose worst failure is a false alarm) while
leaving the *strong* one (the claim, which is the entire basis of exclusion) to self-designation by
attestation. That inversion is removed with Stage I. What replaces it is the acceptance obligation in
E.1.1: properties 1, 4 and 6 are **demonstrated once per mechanism version** — contention test,
stale-holder reclaimability, no forcible preempt (handoff AK2 acceptance criteria `:1961-1963`) — and
the attestation cites that demonstration. A property that is only asserted is not established.

**R3 — The quiet-host predicate for P-BENCH-4 is a reinterpretation and needs explicit assent.**
`measurement/protocols/bench-cpu.md:142-143` requires proof that no competing inference is present
*host-wide*. A claim covers claimed resources only, so E.3.4 renders the host-wide requirement as two
derived tests: no `unattributed` process at or above the run's own smallest model artifact by resident
set, and all system mlocked bytes attributable to `own` plus `claimed-foreign`. Both thresholds derive
from data the run already records, so no literal is ratified — but this is a *reading* of a ratified
sentence, not a mechanical translation of it, and it changes outcomes in both directions.
**Recommendation:** accept, because the derived tests are strictly better correlated with the property
in §2 than a name match is, and because both production speech kernels are invisible to `pgrep llama`
today. **The operator should strike or accept this line deliberately rather than let it ride.**

**R4 — Scope boundary, recorded so it is not mistaken for an omission.** §E governs how a run under
an Annex B protocol establishes one precondition. It says nothing about, and voids nothing on account
of, name-pattern reads elsewhere on this host: `scripts/nightshift/inference_guard.sh:26`,
`scripts/coordination/inference_load_check.py`, `scripts/dashboard/hub_supervisor.sh:125` and
`scripts/coordination/bus_supervisor.sh:76` all read process names outside a measurement preflight and
remain governed by `CLAUDE.md:84`, unchanged. *(The earlier revision voided any run with "any second
name-pattern process reader anywhere on the measurement path" — an undefined term reaching outside the
measurement instrument, which would have voided every nightshift run, since `inference_guard.sh:26`
is a load gate deciding whether an overnight benchmark may start. Withdrawn: a measurement amendment
does not legislate over supervision code.)* Bringing supervision and scheduling under a
claim-and-attribution discipline is a separate question with a separate blast radius.
