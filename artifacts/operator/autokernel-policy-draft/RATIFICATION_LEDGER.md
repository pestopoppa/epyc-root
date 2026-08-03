# AutoKernel attestation 1a — ratification ledger

> **NOT APPLIED.** This ledger is written *before* presentation and completed *at* apply time. The
> apply-time sections (§0 preimage hashes, §7 per-item disposition, §8 receipt) are filled by
> `apply_ratification.sh` and by the operator; everything else is the semantic delta record and is
> complete now.
>
> **Path note.** Cite this file as
> `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md`, always in full. The only other
> `RATIFICATION_LEDGER.md` in this repository belongs to the `measurement-v2-draft` bundle, and a bare
> filename invites writing into it.

**Bundle:** attestation 1a, "constitutional scaffolding".
**Package (the document the operator acts on):** [`RATIFICATION_PACKAGE.md`](RATIFICATION_PACKAGE.md).
**Apply script:** `apply_ratification.sh` (dry-run default).
**Structure follows** the precedent at `artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md`
(v1→v2, applied 20260730T103218Z).

---

## 0. Apply-time record — FILLED AT APPLY

| Field | Value |
|---|---|
| Apply token / `<APPLY_TS>` | *(pending)* |
| `<APPLY_DATE>` | *(pending)* |
| Operator | *(pending)* |
| Bundle commit (staging dir, pathspec-limited) | *(pending)* |

**Preimage SHA-256 per amended file** — captured by `scripts/operator/ratification_receipt.py capture`
**before** any edit. A delta expressed as "changed words only" is well-defined only against a named
preimage, and this tree is shared, so the file may move between presentation and apply.

| File | Preimage SHA-256 | Post-apply SHA-256 |
|---|---|---|
| `MEASUREMENT.md` | *(pending)* | *(pending)* |
| `measurement/protocols/bench-cpu.md` | *(pending)* | *(pending)* |
| `measurement/protocols/gpu-cross-device.md` | *(pending)* | *(pending)* |
| `measurement/protocols/kernel-research.md` *(created)* | n/a — new file | *(pending)* |
| `agents/shared/MEASUREMENT_POLICY.md` | *(pending)* | *(pending)* |
| `coordination/session-bus/human_only_paths.yaml` | *(pending)* | *(pending)* |
| `coordination/session-bus/human_only_paths.sha256` | *(pending)* | *(pending)* |

---

## 1. Structural

- **K1 — A fourth annex.** `MEASUREMENT.md:16-21` has declared exactly **three** annexes since the v2
  restructure. This bundle creates a fourth, `measurement/protocols/kernel-research.md` (**Annex K**),
  for cross-backend kernel-research and kernel-release instruments. The trade is one more file to open
  and one more line in the registry key, against filing a cross-backend search instrument under a
  family letter that would then have to be redefined. **[decided 2026-08-02: create Annex K]** —
  operator approval recorded at `handoffs/active/autokernel-research-loop.md:1855-1861`.
- **K2 — Attestation 1 split into 1a and 1b.** The owning handoff defines attestation 1 as presented
  *after AK3*, with validation evidence *"AK1–AK3 deliverables plus the four calibrated controls"*
  (`:1771`). AK1/AK2/AK3 are 0/17, 0/12, 0/14. Signing the whole of attestation 1 tonight would
  ratify bindings whose referents do not exist — the specific mistake the handoff records at
  `:1867-1869`. **1a** (this bundle) carries only items whose referents exist today and which grant no
  operable authority; **1b** carries every AK1–AK3-dependent binding. `MEASUREMENT.md:138-145` is
  satisfied because 1a's validation results are textual and structural — preimage hashes, exact state
  diff, hook and pin probes — and there are no campaign measurements to wait for.
- **K3 — Package + ledger + dry-run apply script**, following `measurement-v2-draft` rather than
  presenting loose drafts. The v2 bundle is the only precedent for a multi-file human-only apply in
  this repository, and it is the one the staging `README.md:58-71` names.

## 2. Semantic deltas versus current ratified text

Every difference between what `MEASUREMENT.md` and its annexes say today and what they say after this
bundle applies. Item numbers match `RATIFICATION_PACKAGE.md` §B.

### Item 1 — Annex K container

- **D1.1 — Layout paragraph, `MEASUREMENT.md:16-21`.** *"three annexes"* → *"four annexes"*, and
  *"filed by family"* → *"filed by family or instrument class"*. **Supersedes** the sentence ratified
  20260730T103218Z. The second change is not cosmetic: Annex K is explicitly not a measurement family,
  so *"four annexes … filed by family"* would make the constitution assert something this same bundle
  denies. An alternative form deleting the descriptive clause entirely is offered as a
  **substitution**, not as a strike.
- **D1.2 — Annex key line, `MEASUREMENT.md:45-46`.** Gains `**K** = measurement/protocols/kernel-research.md`.
  **Supersedes** the sentence ratified 20260730T103218Z.
- **D1.3 — New file `measurement/protocols/kernel-research.md`.** Header block plus the Remit and
  admission test. Purely additive; no existing file's meaning changes by its creation.
- **D1.4 — CHANGELOG bullet.** Purely additive.
- **Remit content deltas versus the earlier draft of the same container**, recorded because the
  operator may have seen the earlier text:
  - admission test (2) was a **disjunction** (cross-backend *or* search instrument), which admitted
    any future single-backend search instrument on the second limb alone without any of §1's argument
    applying. Now a **conjunction**.
  - admission test (3) said *"already owns the rule being amended"*, which excluded Annex K's only
    member — `P-AK-SEARCH-1` amends a rule owned by G. Now *"already **states** the rule this protocol
    **establishes**"*, plus an explicit **narrowing carve-out** requiring the owning annex to receive
    a cross-reference in the same apply (item 3).
  - a **registry-validity rule about the core file's §2 table** was stated inside the annex Remit.
    Removed: an annex may not legislate over the core file (`MEASUREMENT.md:19-21`). The expectation
    is stated in the delta that writes the cell.
  - the Prospective clause introduced **"search-grade"** and **"admissible"** as undefined terms of
    art. Reduced to the constitution's own vocabulary.
  - **"and compose"** removed from the described authority: the design enumerates four verbs
    (`:352-353`), and composition is a T2 activity with its own re-evaluation obligation.

### Item 2 — `P-AK-SEARCH-1`

- **D2.1 — New registry row**, `MEASUREMENT.md` §2, appended after `:66`. Scope reads
  **per-backend**, not *"(all backends)"*: one protocol id scoped across backends would make a
  CPU-vs-GPU candidate comparison a *within-protocol* comparison, which `MEASUREMENT.md:83-84` permits
  unlabelled — laundering the cross-device composite the operator withdrew on 2026-08-02
  (`autokernel-research-loop.md:161-166`, AK-D12 `:2228`). Metric cell reads *"search verdict — not a
  claim; direction carried per record"*: `:40` requires direction wherever ambiguous, and a **ranking**
  instrument has direction, on the per-record metric.
- **D2.2 — New normative text** inside the new annex. Nothing existing is edited.
- **D2.3 — Effect on `gpu-cross-device.md:16-21`:** the **consumption** clause is **narrowed** for
  in-worktree candidate search by the AutoKernel controller that produced the record. The
  **decision-grade** clause is untouched. Recorded in Annex G by item 3.
- **Deltas versus the earlier draft**, all of them narrowings:
  - Scope permitted a search record onto *"a registry row, a dashboard headline"*, which denial 2
    forbids and `MEASUREMENT.md:85-95` plus standing project policy contradict. Both surfaces are now
    **closed**; only re-measurement under the owning protocol reaches them.
  - Denial 4 forbade cross-campaign consumption and then permitted it in the next sentence. Reuse is
    now **hypothesis formation only** — the demote-to-prior verb applied prospectively — because a
    later campaign re-derives its own calibration and a reused record would be scored against a floor
    it was never measured under.
  - Authority 5 (advisory readiness) carried handoff invariant 14's stratum half and dropped its
    **deterministic-controller / no-narration** half. Restored; a readiness figure originating in
    narrative is `INVALID`.
  - Precondition 6 voided *"operator-driven microbenchmarks"* — a reach outside the protocol's own
    declared scope. Struck.
  - Precondition 7 asserted an **absolute** *"Evidence MUST NOT be deleted to create headroom"*, which
    the evidence-retention clause on this same signature contradicts, and which `MEASUREMENT.md:20-21`
    would have made dead text on landing. Now a **cross-reference** to `storage_floor_bytes_free`.
  - Calibration output 5 defined a **second, incompatible** "campaign storage floor" (bytes consumed,
    campaign-scoped) alongside the retention clause's (bytes free, host-scoped), both *"recorded in the
    manifest"*. **Deleted.** One definition, in the clause whose subject is storage.
  - Three calibration outputs consumed quantities nothing defined (*"calibration block count"*,
    *"contribution floor"*, *"maximum in-flight rounds"*). Precondition 8 now **enumerates every
    manifest field the calibration block consumes**, each fail-closed.
  - `B_min`, the stopping rule and `α_sel` were **mutually defined with no evaluation order**, so two
    conforming implementations could produce different `B_min` from identical data. A six-step
    **solve order** is now normative, terminating in an explicit calibration FAILURE.
  - `n ≥ 10` was imported from `gpu-cross-device.md:146-147` as a **universal constitutional floor**
    over every cell class. It is scoped inside P-SHED-1 to a `task_rate` comparison at CV ≈ 9.1% and
    says nothing about instrument-level `tokens/s` cells; it also collided with P-BENCH-4's *exactly
    five* at `bench-cpu.md:174-178`. Now: `B_min` is floored by P-BENCH-1's reps rule, and **an owning
    protocol's stricter or fixed rule governs its own cells**.
  - The **LCB ban** was absolute, which made two declared schema fields of the design
    (`reference_lcb_gain`, the champion record's `reference_signal`) non-conformant on day one. Now:
    an LCB may be carried **beside** the e-value as a labelled descriptive statistic and may never be
    the test that ranks.
  - Control 5 (**historical-win replay**) was **mandatory** and bound to durable in-repo evidence that
    does not exist — both `handoffs §3.7` exposures re-verified still open. Now a **contract naming
    its supplier** (`historical_win_replay` in the manifest) with a normative
    `HISTORICAL_REPLAY_UNAVAILABLE` branch that escalates to the operator and marks every record and
    readiness figure `controls=4/5`.
  - The **record-grammar template omitted five fields** the same section declared mandatory, so a
    record conforming to the template was `INVALID` under its own rule. Template completed.
  - A **core-file §6b ruling** (demote-to-prior + quarantine of the pre-ratification kernel-research
    strategy-store rows) was issued **from inside an annex**, and a class was carved out of the core
    §6 retro-certify verb. Both removed: the demotion is now **item 7**, a separately strikeable §6b
    append; the retro-certification denial is restated as a consequence of the core file's own
    precondition rather than as a narrowing of it.

### Item 3 — Annex G cross-reference

- **D3.1 — One sentence appended** to `measurement/protocols/gpu-cross-device.md` after the
  kernel-provenance paragraph (`:16-21`), recording that the consumption clause is narrowed for
  in-worktree candidate search only, that the decision-grade clause is unchanged, and that the
  consumption clause continues to bind every other consumer.
- **Why it exists:** without it, item 2 changes what a G clause **means** while G's **text** is
  untouched — the silent edit `MEASUREMENT.md:116-118` forbids by name. The owning handoff records
  that this clause is *"what stops AutoKernel ranking GPU candidates at all"* (`:331`), so it is the
  load-bearing half of the authority, not a formality.
- **Coupling:** items 2 and 3 strike together or land together.

### Item 4 — §E exclusion preconditions (Annex B)

- **D4.1 — `bench-cpu.md:15-16`.** The instrument phrase *"`pgrep llama` zombie check"* is superseded
  by §E. The requirement *no concurrent inference* survives verbatim; the region-claim requirement
  survives and is promoted to primary evidence.
- **D4.2 — `bench-cpu.md:53-54`, `:63-64`, `:72-74`.** The *"competing llama/AutoPilot/KFD witness"*
  name test in each is superseded by the E.3.4 attribution predicate. The **retention duty**, the
  **eligibility condition** and the **invalidation rule** all survive with `competing witness` re-bound
  to *"an `unattributed` process consuming the claimed resources"*. Sampling failure, ownership change
  and swap I/O at `:72-74` are untouched.
- **D4.3 — `bench-cpu.md:66-71`.** **NOT superseded.** The `signed_external_core_equivalents`
  computation, its `[-1.0, 4.0]` band, and its eligibility conditions are adopted unchanged and by
  reference. §E states no band.
- **D4.4 — `bench-cpu.md:142-143`.** The P-BENCH-4 quiet-host clause gains an instrument. This is a
  **reinterpretation that changes outcomes in both directions** — R3 — and is its own strikeable
  sub-line.
- **D4.5 — Evidence set enlarged** by the E.5 precondition-witness fields and the E.1.2 residual-load
  witness at both endpoints, for every protocol in Annex B. Stated as an enlargement rather than
  claimed to be stringency-neutral.
- **D4.6 — `agents/shared/MEASUREMENT_POLICY.md:38`.** In-place correction of one bullet, verbatim
  before/after in `RATIFICATION_PACKAGE.md` §E. The digest is a derived agent-facing projection, not a
  protocol; the precedent for in-place digest correction is `apply_v2.sh` step 3.
- **Deltas versus the earlier draft** — the scope shrank, and the shrink is the point:
  - it appended **one identical §E to both Annex B and Annex G**, creating two independently
    amendable, separately hash-pinned copies of one rule against `MEASUREMENT.md:117`'s singular
    *"the owning annex file"*. Now **Annex B only**.
  - **Annex G never mandated a name pattern.** `gpu-cross-device.md:28-30` requires *PID checks*;
    `pgrep` appears exactly once in the annex corpus, at `bench-cpu.md:15`. The Annex G half superseded
    a clause that was not in conflict, converted `:28-30`'s explicitly permitted *"declared
    non-quiesced with reason"* state into a precondition **failure**, and added six fields to a set
    `:23` declares closed. **All withdrawn.**
  - the **Stage I / Stage T** regime made every GPU run observation-grade on day one: Stage T
    unreachable (no device claim), Stage I requiring a pinned enumerator that does not exist and
    fail-closed. Replaced by `WITNESS` **plus an always-available `LEGACY` path**, so no protocol ever
    loses a satisfiable precondition.
  - **E.1.4's sanctioned enumerator** would have pinned `scripts/utils/inference_preflight.sh` — an
    open AK2 checkbox — into `human_only_paths.yaml`, whose header promises real paths verified to
    exist, and would have collided with the gate-list item on the same signature. **Withdrawn**
    (deferred D1).
  - the load-bearing claim that `bench-cpu.md:53-76` is *"entirely name-free"* was **false**; it is
    name-based at `:53-54`, `:63-64` and `:72-74`. Corrected, and the supersession table now disposes
    of those three spans explicitly instead of simultaneously superseding and adopting `:63-64`.
  - **Stage-T eligibility was latched from the campaign manifest** — an agent-written artifact, no
    human verification, one-way. Removed: `WITNESS`/`LEGACY` are per-run, evaluated from the run
    attestation, with no cross-run state and no manifest read.
  - the quiet-host threshold read *"this run's own model manifest"*, a term appearing nowhere in the
    constitution, the annexes or the handoff. Re-anchored to the model size the run **already records**
    under `bench-cpu.md:41-44`.
  - `E.2.2` voided any run with *"any second name-pattern process reader anywhere on the measurement
    path"* — an undefined term reaching over supervision code, which would have voided every nightshift
    run (`inference_guard.sh:26`). **Withdrawn.**
  - the P-BENCH-PREFILL-1 band was imported into Annex G as a pass/fail gate where its own eligibility
    precondition (`:62-63`, ≥ 0.75 × configured CPU count) can never be met on an 8-thread GPU lane.
    Moot with Annex G withdrawn; the CPU leg is additionally made conditional on the run having a
    pinned CPU region.
  - `E.6`'s *"unlabelled measurement is not decision-grade"* was sourced from `MEASUREMENT.md:95`,
    which is the closing line of the `category=` rule and says nothing about preflight fields. Now
    stated as §E's own rule about §E's own fields.

### Item 5 — Evidence retention and reclamation (`MEASUREMENT.md` §5)

- **D5.1 — New §5 bullet**, appended after the 2026-08-02 durability clause (`:146-160`). **Supersedes
  nothing.** It extends that clause; prior receipt is the 2026-08-02 amendment, CHANGELOG `:241-245`.
- **D5.2 — Three durability classes** become named terms of the constitution: `carried-in-git`,
  `durable-untracked`, `hash-and-provenance-only`. Only the third exists today (`:154`).
- **D5.3 — One narrow reclamation authority is created** where none existed: the class transition
  `durable-untracked → hash-and-provenance-only`, over three enumerated artifact kinds, for artifacts
  the loop created, inside operator-set namespace roots, under an eight-conjunct predicate, recorded
  by a tombstone written and fsynced **before** any unlink.
- **D5.4 — `storage_floor_bytes_free` is defined here, for the whole constitution.** Item 2's
  precondition 7 references it.
- **D5.5 — `MEASUREMENT.md:223-229` is NOT edited, NOT narrowed, and NOT relied upon.** The ledger
  records the reading explicitly so a later reader cannot cite this amendment as precedent for carving
  further slices out of a closed enumeration: `:223-229` is an inventory of past deletions whose rule
  is that everything not enumerated **is kept**, and whose sole operator call is ~1.2 GB of superseded
  embedding blobs under `repl_memory/sessions/`. §3.7 is a fresh, self-contained, bounded grant.
- **Deltas versus the earlier draft:**
  - the text ordered appended **verbatim** carried a literal `<DATE>`. Now `<APPLY_DATE>`, defined in
    the package's token table.
  - **three §6 "open questions" proposed changes to §3's own normative wording**, so there was no
    single ratifiable text. All three resolved into §3 as the draft itself recommended (remote ref for
    E2; region-claim quiescence; Prospective scoped to expirability), and §6 demoted to a
    considered-and-rejected record.
  - `durable-untracked` required the artifact to sit *"under `epyc-inference-research/data/<campaign>/`"*
    while E1/E2 target build trees and worktrees under `/mnt/raid0/llm/`, and `:153` names build trees
    as the archetypal too-large case — so **nothing the clause targeted could satisfy conjunct 2** and
    the clause was a no-op that read as a working authority. Redefined: **the hash chain must be in
    git; the bytes need not be.**
  - the grammar extension was **unscoped**, demoting every existing citation in the constitution —
    including the ✅ exemplar at `:70` — from claim to observation. Now **loop-scoped**, with explicit
    non-demotion of pre-existing and human-produced citations.
  - *"an artifact whose class is unrecorded … MUST NOT be cited by a ratified claim"* would have
    stripped the v8 production cutover's quality anchor (the unclassed 144 MB v7 backup) on signature
    day. Now a **prospective classification duty** whose pre-ratification effect is a tracked
    retention-defect item, not a demotion.
  - four bindings referenced **campaign-manifest fields that exist in no schema**. All are now **named
    fields** (`namespace_roots`, `retention_hold_boundaries`, `storage_floor_bytes_free`,
    `max_storage_gb`, `storage_safety_factor`, `host_reserve_bytes`), and **three of them are
    operator-set**, which a campaign may narrow and may not widen. The delegate no longer authors its
    own delete boundary, retention period or emergency threshold.
  - *"the host reserve set by the operator"* had no field name, no default and no unset behaviour — an
    unset reserve reads as zero and silently collapses the floor. Now `host_reserve_bytes`, **fail
    closed**: a campaign whose floor lacks it MUST NOT start.
  - conjunct 6 licensed filesystem churn on *"no measurement window is open"* — the loop's own
    knowledge, on a shared host. Now the executor **holds the region claim**.
  - the operator-only list omitted **writes to the measurement trust boundary**. Added as item 8, with
    all five human-only writes quoted rather than four.
  - citation repairs: `:150-152` → `:149-152`; bare `:210-212` → `bench-cpu.md:210-212` (bare `:NNN` is
    the house convention for the core file, and `MEASUREMENT.md:210-212` is the §6b table — a normative
    citation binding to the wrong document once transcribed); `:141-142` → `:140-142` with all five
    members quoted.

### Item 6 — §6 dump-list cross-reference (optional, one sentence)

- **D6.1** — one sentence appended to the explicit dump list at `MEASUREMENT.md:223-229` pointing a
  reader of §6 at §5's retention rule and restating that the list is otherwise closed and confers no
  authority beyond its own enumeration. Purely navigational. Struck ⇒ a reader of §6 alone does not
  discover §5's rule; nothing else changes.

### Item 7 — §6b strategy-store ruling (optional)

- **D7.1** — appends to the `MEASUREMENT.md` §6b per-corpus table, **narrowing** the existing
  *"Strategy store / STM / planner narrative | 1424+ entries | Findings-01 Phase 4"* ruling at `:216`
  for the **kernel-research rows specifically** (the `kernel_store.py` SQLite corpus): demote-to-prior
  per `:180-182`, quarantined from every correct-only frontier and readiness computation, with a
  re-measure ticket per `:164-166` for any lineage decision resting only on them.
- **Why it is a separate line.** This is the one item in the bundle that **changes the standing of an
  existing corpus**. Retroactivity verbs and per-corpus rulings are core-file `§6`/`§6b` matters
  (`:168-217`); the earlier draft performed this ruling from inside an Annex K protocol and described
  the bundle in the CHANGELOG as *"supersedes nothing"*, which is a `:116-118` mechanics failure on
  two counts. It is now filed where it belongs, named in its own CHANGELOG line, and **strikeable
  without touching anything else**.
- **Disambiguation the earlier draft owed and did not pay:** the §6b row at `:216` covers the
  *strategy store / STM / planner narrative* corpus generally. This delta narrows **only** the
  kernel-research rows written by `scripts/kernel_rnd/kernel_store.py`. Rows of that corpus written by
  the routing planner or the STM are **not** touched.
- **Substantive reason:** the evaluator that produced those rows never gated on coherence, so its
  correctness labels were emitted without an anchor comparison and are not verdicts (owning handoff
  §2). Quarantine is a supersession tag, not a deletion — `:174-175` is untouched.

### Item 8 — `human_only_paths.yaml` conceptual entries

- **D8.1** — two `conceptual:` entries appended, plus the `.sha256` pin rewrite as one atomic action.
  **Adds no path, no write class, and no enforcement.** A `conceptual:` entry is explicitly
  *"unenforceable by the audit"* by construction (`human_only_paths.yaml:51-55`).
- **D8.2 — C2 records a verified defect in this file's own layer-1 enforcement**:
  `scripts/hooks/check_trust_boundary_edit.sh:90` quotes the RHS of its `[[ … == … ]]`, disabling bash
  pattern matching, so **every `glob:` entry matches nothing** and Annexes B, Q and G are agent-writable
  through `Write`/`Edit` today. Verified by probe; the probe is re-runnable from
  `human-only-paths-delta.draft.md` §3 and from `apply_ratification.sh --verify`.
- **Deltas versus the earlier draft:** the two `paths:` entries (**D1** evaluator bundle, **D2** policy
  plane) are **deferred**, because `/workspace/measurement/policy/` does not exist and
  `…/kernel_rnd/autokernel/` contains only `__init__.py` and `schemas.py` — there is no `evaluator/`.
  The same draft used exactly that argument at `:157-165` to defer the waiver entry. Their
  preconditions are enumerated at `human-only-paths-delta.draft.md` §2.1 and include the matcher
  repair, the closed-enumeration reconciliation, and D2's normativity question.

## 3. Corrections to the constitution's own citations, surfaced not fixed

Found while assembling this bundle. **None is amended by it**; each is reported so the operator can
decide separately.

- **`MEASUREMENT.md:155` names a validator that is not where it says.**
  `scripts/validate/check_evidence_durability.py` does not exist in epyc-root. The file is at
  `epyc-inference-research/scripts/validate/check_evidence_durability.py`. Every document that cites
  the constitution's path inherits the error. *(Also recorded at `autokernel-research-loop.md:481-482`.)*
- **Layer-1 hook enforcement of `measurement/protocols/*.md` is inoperative** (item 8, D8.2). This
  predates AutoKernel. The repair is code and is registered as deferred item D5.
- **`config.yaml:164`'s `on_pin_mismatch: refuse` has no consumer.** The operative behaviour on
  trust-boundary drift is detect-and-report: a failing `session_bus.py validate` and a daemon defect
  row. Nothing gates. No part of this bundle relies on `refuse` firing.

## 4. Not changed

- **Every decision rule, threshold, rep count, ratio band, provenance gate and reconciliation verb** in
  Annexes B, Q and G carries over with its original meaning, except the five spans named in D4.1–D4.2
  and the one clause narrowed by D2.3/D3.1.
- **The prime directive** (`MEASUREMENT.md:174-175`) is untouched. Item 5 reclaims derivable bytes and
  never a record.
- **The explicit dump list** (`:223-229`) is untouched and stays closed.
- **The three retroactivity verbs** (`:177-183`) are untouched. Item 7 *applies* one; it does not
  create, modify or narrow any.
- **The enumerated human-only writes** (`:140-142`) are untouched — all five. No item in attestation 1a
  adds a write class. *(The deferred D1/D2 gate-list entries would; that reconciliation is one of their
  preconditions.)*
- **The trust boundary** remains human-only, PR-reviewed, append-or-version.
- **Production kernels** are untouched. No item in this bundle reads, writes, builds, or references a
  production kernel branch.

## 5. Supersession statement (required by `README.md:58-71` and `MEASUREMENT.md:118`)

| Item | Supersedes | Prior receipt |
|---|---|---|
| 1 | `MEASUREMENT.md:16-21` (layout sentence) and `:45-46` (annex key line) | v2 apply, 20260730T103218Z, `artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md` |
| 2 | nothing directly; **narrows** the consumption half of `gpu-cross-device.md:16-21` | same |
| 3 | nothing — records item 2's narrowing in the owning annex | same |
| 4 | `bench-cpu.md:15-16` (instrument phrase only), `:53-54`, `:63-64`, `:72-74` (name-witness limbs only) | same |
| 5 | nothing — **extends** the 2026-08-02 durability clause | 2026-08-02 durability amendment, CHANGELOG `MEASUREMENT.md:241-245` |
| 6 | nothing — navigational | n/a |
| 7 | **narrows** the §6b strategy-store ruling at `MEASUREMENT.md:216`, for kernel-research rows only | 2026-06 reconciliation (§6b, still governing) |
| 8 | nothing — two `conceptual:` entries | v2 apply, 20260730T103218Z |

Receipt SHA-256 values for each prior receipt are computed at apply time by
`ratification_receipt.py capture` and recorded in §0 above.

## 6. Evidence cited by this bundle

Attestation 1a is a **textual** amendment: it ratifies rules, not measurements, so it cites no
benchmark result and needs no `SHA256SUMS` over a data directory. What it does cite:

| Cited artifact | Kind | Resolves |
|---|---|---|
| `MEASUREMENT.md`, `measurement/protocols/*.md`, `agents/shared/MEASUREMENT_POLICY.md` | in-repo, tracked | verified at apply by preimage hash |
| `coordination/session-bus/human_only_paths.yaml` + `.sha256`, `config.yaml` | in-repo, tracked | verified at apply by pin check |
| `scripts/hooks/check_trust_boundary_edit.sh` + its test suite | in-repo, tracked | probed, exit codes recorded |
| `handoffs/active/autokernel-research-loop.md` | in-repo, tracked | line citations |
| `artifacts/operator/freeze_v8_production_20260725.sh`, `ratify_v8_final_freeze_20260725.json`, `waive_q8_cpu_prefill_v8_20260725.json` | in-repo, tracked | cited by the deferred waiver item only |
| `/mnt/raid0/llm/llama.cpp-v7-build-backup-6ad45fa3ff` | **on host, outside any git repo** | **retention-defect item**, filed by item 5; SHA-256 computed into this bundle at apply |
| the staging directory itself | **untracked at authoring time** | **MUST be committed before presentation** — see §7 |

## 7. Per-item disposition — FILLED AT APPLY

| # | Item | Applied / Struck | Notes |
|---|---|---|---|
| 1 | Annex K container + core-file deltas | *(pending)* | |
| 2 | `P-AK-SEARCH-1` | *(pending)* | coupled to 3 |
| 3 | Annex G cross-reference | *(pending)* | coupled to 2 |
| 4 | §E exclusion preconditions (Annex B) + digest | *(pending)* | R3 sub-line: *(pending)* |
| 5 | Evidence retention and reclamation | *(pending)* | |
| 6 | §6 dump-list cross-reference | *(pending)* | |
| 7 | §6b strategy-store narrowing | *(pending)* | |
| 8 | `human_only_paths.yaml` conceptual entries + pin | *(pending)* | atomic pair |

**Pre-apply gate:** `git ls-files artifacts/operator/autokernel-policy-draft/` MUST return every
presented draft plus `RATIFICATION_PACKAGE.md`, this ledger, and `apply_ratification.sh`. A
working-tree file in a shared clone is one `git checkout` from gone and is invisible to a reviewer who
clones; signing over bytes no repository holds is the exact failure `MEASUREMENT.md:146-156` was
ratified to close.

## 8. Receipt — FILLED AT APPLY

| Field | Value |
|---|---|
| `<RECEIPT_PATH>` | *(pending)* |
| `<RECEIPT_SHA256>` | *(pending)* |
| Post-apply `human_only_paths.sha256` | *(pending)* |
| `session_bus.py validate` result | *(pending)* |
| Hook probe exit codes (§F of the package) | *(pending)* |
| Commit SHA | *(pending)* |

`<RECEIPT_SHA256>` is recorded **here and in the receipt only**, never in the `MEASUREMENT.md`
CHANGELOG: the receipt hashes the files it amends, so writing its own digest into one of them would
make the receipt's recorded post-state hash stale the instant it was cited. The CHANGELOG cites this
ledger by path, matching `MEASUREMENT.md:250`.
