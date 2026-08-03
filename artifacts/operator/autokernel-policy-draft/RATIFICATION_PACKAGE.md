<!-- OPERATOR RATIFICATION PACKAGE — attestation 1a. NOT APPLIED.
     This is the document to read and act on. The drafts in this directory are its sources.
     Assembled 2026-08-03 after adversarial review of six staged drafts. -->

# AutoKernel — attestation 1a ratification package

**Read this document. The drafts are its sources; you do not need to read them to sign.**

| | |
|---|---|
| **Attestation** | 1a — "constitutional scaffolding" |
| **Items** | **8**, each independently strikeable (`MEASUREMENT_POLICY.md:77-78`) |
| **Files touched** | `MEASUREMENT.md`; `measurement/protocols/bench-cpu.md`; `measurement/protocols/gpu-cross-device.md`; **new** `measurement/protocols/kernel-research.md`; `agents/shared/MEASUREMENT_POLICY.md`; `coordination/session-bus/human_only_paths.yaml` + `.sha256` |
| **Apply script** | [`apply_ratification.sh`](apply_ratification.sh) — **dry-run by default** |
| **Delta record** | [`RATIFICATION_LEDGER.md`](RATIFICATION_LEDGER.md) |
| **Owning handoff** | `handoffs/active/autokernel-research-loop.md` §3, §14 AK0 |

---

## A. One screen: what this is

### What is being ratified

The **rules AutoKernel will have to obey**, before AutoKernel exists. Eight amendments: a fourth annex
to hold a kernel-research search protocol, that protocol's text, a cross-reference so Annex G records
that one of its clauses has been narrowed, a name-free replacement for the `pgrep llama` precondition
in Annex B, an evidence-retention clause that makes disk reclamation possible without deleting
records, two optional navigational lines, and two `conceptual:` notes in the trust-boundary gate list.

### What it authorises

One thing: an automated kernel-research controller may **rank, retain, abandon, or branch candidate
kernels inside its own experimental worktrees**, on measurements taken there — and only after it
satisfies eight preconditions and completes a per-campaign calibration, none of which is possible
today. That is the narrow lift of one half of one clause (`gpu-cross-device.md:16-21`, the
*consumption* half). It lifts nothing else.

Plus one narrow, bounded delete authority: a deterministic executor may transition three enumerated
kinds of **derivable** artifact from `durable-untracked` to `hash-and-provenance-only`, leaving a
tombstone that records what existed, its hash, its size and why it is gone — inside operator-set
namespace roots, over artifacts the loop itself created, under an eight-conjunct predicate, while
holding a region claim.

### What it explicitly does NOT authorise

- **No production write of any kind.** No building in, committing to, or modifying a production tree
  or production-named branch; no repointing a stable kernel path; no registry, lineup or era write.
- **No freeze, no cutover, no era-registry row, no AutoPilot baseline apply, no host reboot.** All
  five human-only writes at `MEASUREMENT.md:140-142` are untouched — including *"this constitution and
  its annexes"*.
- **No gating outside the worktree.** A search record can never gate a keep / revert / deploy /
  promote / buy / close decision, and can never become a claim by any route.
- **No release activity.** No T3, no verdict, no freeze eligibility, no waiver judgement, no sealing.
- **No self-amendment.** The controller may not modify the protocol, the evaluator, the controls, the
  objective, the calibrated thresholds, or any scoring contract.
- **No consumption by any other optimizer**, and no consumption by a later campaign except for
  hypothesis formation.
- **No deletion of any primary record.** The prime directive is untouched; the explicit dump list at
  `:223-229` is untouched and stays closed.
- **No new enforcement.** Item 8 adds two notes to a list; a `conceptual:` entry is unenforceable by
  construction, and this package says so rather than implying protection it does not deliver.

### What changes for your day-to-day

**Nothing, until AutoKernel is built.** Concretely:

- Every precondition in the new protocol **fails closed** against machinery that does not exist — no
  evaluator bundle, no campaign manifest schema, no claim substrate. No campaign can start.
- Item 4 supplies a *second* way to satisfy an Annex B precondition and **keeps the existing way**
  (`preflight=LEGACY`). Your benches run exactly as they do today unless you opt into `WITNESS`.
- Item 5's delete authority reaches nothing that exists: it is prospective, scoped to artifacts a
  loop creates after ratification, and requires manifest fields no artifact carries.
- Item 5 does file **one report against today's state**: the 144 MB v7 binary the v8 quality gate
  compared against sits outside any git repository with no `SHA256SUMS`. That is a *tracked defect*,
  not a gate — no v8 claim changes status and the v8 freeze is not reopened.

### Why tonight, and why only these eight

The owning handoff defines attestation 1 as presented *after AK3*, with validation evidence
*"AK1–AK3 deliverables plus the four calibrated controls"* (`:1771`). **AK1 is 0/17, AK2 0/12, AK3
0/14.** Signing all of attestation 1 tonight would ratify bindings whose referents do not exist —
precisely the mistake the handoff records at `:1867-1869` as the one to avoid.

So attestation 1 is split. **1a is tonight**: every item whose referent exists today, and which
grants no operable authority. **1b is after AK3**: every item that names a deliverable — the
evaluator-bundle and policy-plane gate-list entries, the Stage I enumerator, the Annex G extension.
Those are in §D, deferred with their preconditions written out, not silently dropped.

`MEASUREMENT.md:138-145` is satisfied because what you are signing over is **textual and structural**
— preimage hashes, an exact state diff, hook and pin probe results — and there are no campaign
measurements pending to wait for.

### One thing to know before you sign

**RESOLVED 2026-08-03 — this section is superseded.** The matcher was repaired in epyc-root `6f1c4a8b` (the right-hand side of the `[[ … == … ]]` is now unquoted, restoring bash pattern matching) and the missing wildcard cases were added to the canonical suite `scripts/hooks/tests/test_trust_boundary_edit.py` in `51613c9e`. Annexes B, Q, G **and the new Annex K** are enforced by layer 1 today; the suite asserts all four block and that ordinary files, a non-`.md` file inside the protected directory, and a `.md` file outside it do not. Deferred item D5 is CLOSED. The text below is retained as the record of what was found and why the test exists.

**Layer-1 hook enforcement of `measurement/protocols/*.md` does not work today**, and this package
does not fix it. `scripts/hooks/check_trust_boundary_edit.sh:90` quotes the right-hand side of its
`[[ … == … ]]`, which disables bash pattern matching, so **every `glob:` entry in the gate list
matches nothing** — Annexes B, Q and G are agent-writable through `Write`/`Edit` right now, and the
new Annex K will be too. Literal entries (`MEASUREMENT.md`, `MEASUREMENT_POLICY.md`) are unaffected
and do block. The defect predates AutoKernel. Item 8 records it in the file it concerns; the repair
is code and is deferred item **D5**. §F probes it and records the actual exit codes.

---

## B. The strikeable item list

Each line is independently strikeable. **The "if you strike it" column is the point of this table** —
read it before the description.

| # | What it does | Files | **If you strike it** |
|---|---|---|---|
| **1** | **Create Annex K.** New file `measurement/protocols/kernel-research.md` with its remit and admission test. Layout paragraph "three annexes"→"four … filed by family **or instrument class**"; §2 key line gains **K**; CHANGELOG bullet. Grants **no authority to anything**. | `MEASUREMENT.md` (3 spots), new annex file | Item 2 has no home and is struck with it (it cannot go in B, Q or G without fragmenting one authority across three amendment histories). Item 3 goes with 2. Items 4–8 are unaffected. **Net: the search authority is not granted at all.** |
| **2** | **`P-AK-SEARCH-1`** — the search authority: what the controller may decide for itself (4 verbs, worktree-only), nine denials, eight preconditions, a per-campaign calibration procedure with a stated solve order, four mandatory controls plus a fifth under a declared contract, and a record grammar that says *SEARCH RECORD, NOT A CLAIM*. Plus its §2 registry row. | new annex file, `MEASUREMENT.md` §2 | The annex is created and left **empty** — a coherent state that reserves the letter and the remit and grants nothing. **The §2 registry row MUST then be dropped too** (a row pointing at absent text is worse than no row), and item 3 struck with it. **Net: AutoKernel gets no ranking authority; the GPU consumption clause stays absolute.** |
| **3** | **Annex G cross-reference.** One sentence appended after P-GPU-1's kernel-provenance paragraph recording that its *consumption* clause is narrowed for in-worktree search only, that the *decision-grade* clause is unchanged, and that consumption still binds every other consumer. | `measurement/protocols/gpu-cross-device.md` | **Do not strike this while item 2 lands.** Item 2 changes what a G clause *means* while G's *text* stays untouched — the silent edit `MEASUREMENT.md:116-118` forbids by name. Any session reading Annex G after apply would get the wrong answer about a clause the handoff calls *"what stops AutoKernel ranking GPU candidates at all"* (`:331`). **Items 2 and 3 strike together or land together.** |
| **4** | **§E exclusion preconditions (Annex B).** Replaces the `pgrep llama` zombie check with a name-free instrument: a held resource claim, own-scope enumeration, and a residual-load witness, evaluated over attribution classes instead of process names. Adds an always-available `LEGACY` path so nothing is bricked. Plus the one-bullet `MEASUREMENT_POLICY.md:38` digest fix. | `bench-cpu.md`, `agents/shared/MEASUREMENT_POLICY.md`, `MEASUREMENT.md` CHANGELOG | The `CLAUDE.md:84` ↔ `bench-cpu.md:15-16` contradiction stays open: a conforming evaluator still cannot satisfy the protocol it must run under without a name-pattern read the project forbids. Item 2's precondition 2 then falls back to Annex B's own unamended text — it never leaves a backend with no path. **Net: benches continue exactly as today; the contradiction is unresolved.** |
| **4R** | *(sub-line of 4)* **R3 — the quiet-host reinterpretation.** E.3.4 renders P-BENCH-4's host-wide *"no competing inference"* as two derived tests. This **changes outcomes in both directions**: a dormant foreign server small enough to pass both now passes; a foreign `whisper.cpp`/`qwentts.cpp` server — invisible to `pgrep llama` today — now fails. | same | §E lands but `bench-cpu.md:142-143` keeps its current unspecified instrument, so P-BENCH-4's quiet-host clause has no operable definition under `WITNESS`. **Recommendation: accept** — the derived tests correlate better with the actual property, and both production speech kernels are invisible to `pgrep llama` today. Strike it deliberately or accept it deliberately; do not let it ride. |
| **5** | **Evidence retention and reclamation** (`MEASUREMENT.md` §5). Three durability classes; a closed list of three expirable artifact kinds; an eight-conjunct predicate; fail-closed tombstones written before any unlink; `storage_floor_bytes_free` and the `DISK_PRESSURE` stop state; and an explicit operator-only list. Defines `storage_floor_bytes_free` for the whole constitution. | `MEASUREMENT.md` §5 + CHANGELOG | Item 2's precondition 7 has no floor to reference, so **no campaign can evaluate it — which fails closed, not open.** The durability/retention deadlock stays: everything must be kept, nothing may be reclaimed, and a loop halts on a full disk. The v7-backup retention defect goes unfiled. Item 2 still ratifies; it just cannot start a campaign. |
| **6** | **§6 cross-reference** — one sentence appended to the explicit dump list pointing a reader of §6 at §5's retention rule and restating that the list is otherwise closed. Purely navigational. | `MEASUREMENT.md` §6 | A reader of §6 alone does not discover §5's rule and may conclude the dump list is the complete inventory of sanctioned deletions. Harmless; nothing else changes. **Lowest-stakes line in the package.** |
| **7** | **§6b strategy-store narrowing** — appends to the per-corpus table: the **kernel-research** rows written by `kernel_store.py` are demoted-to-prior and quarantined from every correct-only frontier and readiness computation, with a re-measure ticket for any lineage decision resting only on them. Reason: that evaluator never gated on coherence, so its correctness labels were emitted without an anchor comparison and are not verdicts. | `MEASUREMENT.md` §6b + CHANGELOG | Those rows keep their current standing under the general §6b ruling at `:216`, and a future AutoKernel campaign could seed a champion lineage from correctness labels that were never verdicts. **This is the only item that changes the standing of existing data**, which is exactly why it is its own line rather than buried inside item 2's protocol text. Striking it costs nothing else. |
| **8** | **`human_only_paths.yaml` — two `conceptual:` entries** + the `.sha256` pin rewrite, as **one atomic action**. C1: evaluator immutability needs OS-level enforcement, not a hook. C2: the verified layer-1 glob-matcher defect. Adds **no path and no write class**. | `human_only_paths.yaml`, `human_only_paths.sha256` | The glob-matcher history stays undocumented in the file it affected, and the next reader has no in-file record that wildcard entries were once inert — so a future re-quoting of the matcher would look like a cosmetic change rather than a regression. **Updated 2026-08-03:** the defect itself is now FIXED in epyc-root `6f1c4a8b`, with `scripts/hooks/test_check_trust_boundary_edit.sh` asserting both directions, so the three annexes are genuinely protected as of that commit. Striking this item costs the durable record of why the test exists, not the protection. **Never split this line**: the YAML edit and the pin rewrite are one action, and a struck half of either produces drift indistinguishable from a hostile out-of-band edit. |

**Coupling summary, restated because it is the easy mistake:**

- 1 struck ⇒ 2 and 3 struck.
- 2 struck ⇒ 3 struck, **and** the §2 registry row from item 1 dropped.
- 2 landed ⇒ 3 landed. *(No exceptions. This is a `:116-118` requirement, not a preference.)*
- 8 is atomic. Edit and pin, or neither.
- 4, 5, 6, 7 are free-standing.

---

## C. Ratification ledger — semantic deltas versus current ratified text

The full itemised ledger is [`RATIFICATION_LEDGER.md`](RATIFICATION_LEDGER.md), structured to match
`artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md` (Structural / semantic deltas /
Not changed / Supersession). The headline rows:

**Structural (K1–K3):** a fourth annex; attestation 1 split into 1a/1b so no binding is ratified
ahead of its referent; a package + ledger + dry-run apply script instead of loose drafts.

**Supersessions — what stops being true.** `MEASUREMENT.md:118` requires these to be named:

| Superseded text | By | Prior receipt |
|---|---|---|
| `MEASUREMENT.md:16-21` — *"three annexes … filed by family"* | item 1 | v2 apply 20260730T103218Z |
| `MEASUREMENT.md:45-46` — the B/Q/G key line | item 1 | v2 apply 20260730T103218Z |
| `bench-cpu.md:15-16` — the phrase *"`pgrep llama` zombie check"* (instrument only; *no concurrent inference* survives verbatim) | item 4 | v2 apply 20260730T103218Z |
| `bench-cpu.md:53-54`, `:63-64`, `:72-74` — the *"competing llama/AutoPilot/KFD witness"* **name test** in each (the retention duty, eligibility condition and invalidation rule all survive, re-bound to attribution classes) | item 4 | v2 apply 20260730T103218Z |
| `MEASUREMENT.md:216` §6b — the strategy-store ruling, **narrowed for kernel-research rows only** | item 7 | 2026-06 reconciliation |
| `gpu-cross-device.md:16-21` — the **consumption** half, **narrowed** (not superseded) for in-worktree search | items 2 + 3 | v2 apply 20260730T103218Z |

**Not changed:** every decision rule, threshold, rep count, ratio band and provenance gate outside
those spans; the prime directive; the explicit dump list; the three retroactivity verbs; all five
human-only writes; the trust boundary's human-only / append-or-version character; every production
kernel branch.

**Reported, not fixed (§3 of the ledger):** `MEASUREMENT.md:155` names
`scripts/validate/check_evidence_durability.py` in epyc-root; the file is in the research repo. The
hook's glob matcher is inoperative. `config.yaml:164`'s `on_pin_mismatch: refuse` has no consumer.

**What the adversarial review caught, by class** — recorded so the operator can see what changed
between the reviewed drafts and this package:

| Class | Count | Examples |
|---|---|---|
| Binding to an artifact that does not exist | 6 | mandatory historical-win control; Stage I enumerator pin; D1/D2 gate-list paths; AK6 assembler; `evaluator_bundle_sha256` in a manifest that has no such field |
| Two definitions of one name | 2 | "campaign storage floor" (bytes-consumed vs bytes-free); two live ratification checklists |
| Sibling contradiction on one signature | 4 | absolute no-delete vs delegated expiry; two supersession maps; two rules for the same human-only file; two placements for the waiver |
| Silent edit of the core file | 3 | §6b ruling issued from an annex; §6 verb narrowed from an annex; registry-validity rule stated in an annex |
| Placeholder or circular value | 4 | `<DATE>` in verbatim text; `<RECEIPT_SHA256>` self-invalidating; three calibration inputs with no referent; circular `B_min` |
| Would brick a working path | 2 | GPU protocols left with no satisfiable precondition; `durable-untracked` unsatisfiable for everything it targets |
| Retroactive demotion of existing claims | 2 | unscoped citation-grammar extension; v8 quality anchor un-evidenced |
| Authority beyond the design | 5 | registry/headline surfaces; cross-campaign reuse; a fifth verb ("compose"); `permanent` suppression; `FAIL`-waivability everywhere |
| Wrong file:line | 9 | swapped waiver conditions 7/8; `:126-127`→`:125-126`; `:150-152`→`:149-152`; bare `:210-212`; hook `:31`→`:28`/`:33`; `server.py:826` |

---

## D. Deferred, with preconditions — not dropped

Nothing below is abandoned. Each has a written precondition; when it is met, the item is presented.

| # | Item | Attestation | Blocked on | Precondition to present |
|---|---|---|---|---|
| **D1** | Stage I **sanctioned enumerator** + its gate-list pin | 1b | `scripts/utils/inference_preflight.sh` does not exist (handoff `:450`; AK2 open at `:1965-1966`) | AK2 delivers the wrapper; the path exists; the entry rides one merged gate-list line with one terminal pin |
| **D2** | **Annex G equivalent of §E** | 1b | Annex G mandates no name pattern, so there is nothing to repair; and a GPU `WITNESS` path is unreachable without a device claim | a conforming MI210 device claim exists and passes E.1.1's acceptance obligation; the amendment is argued against `gpu-cross-device.md:23-30` and `:142-143` on their own terms |
| **D3** | **D1 gate-list entry** — evaluator bundle (`scripts/kernel_rnd/autokernel/evaluator/**`) | 1b | the directory does not exist (parent holds only `__init__.py`, `schemas.py`) | AK3 delivers the bundle with a `SHA256SUMS`; **D5 landed**; the closed-enumeration question resolved (see below) |
| **D4** | **D2 gate-list entry** — threshold policy plane (`measurement/policy/autokernel/*.yaml`) | 1b | `/workspace/measurement/policy/` does not exist | the directory and bundle exist; **D5 landed**; **and** the normativity question answered: the operative gate bands would live outside `measurement/protocols/`, so either the YAML must carry the Annex K version it projects with a validator asserting projection-equals-annex, or the YAML is declared normative and the annex descriptive. Otherwise every future gate-band change is a silent protocol amendment — performed by the operator, which is not a cure |
| **D5** | ~~**Trust-boundary matcher repair**~~ **CLOSED 2026-08-03** — repaired in epyc-root `6f1c4a8b`; wildcard cases added to the canonical suite `scripts/hooks/tests/test_trust_boundary_edit.py` in `51613c9e` (22/22 pass). The prediction that its `CASES` list had no wildcard case was correct and was the root cause. | code, no signature | nothing; it was a two-character fix | lands with a **wildcard test case** in `scripts/hooks/tests/test_trust_boundary_edit.py` (whose `CASES` at `:39-56` has none, which is why this survived) **and** a compliant-path negative case, so the guard does not forbid its own idiom. **Owner: session-bus / hooks** |
| **D6** | **P-GPU-1 §S sealed-candidate amendment** | 2 | its five `[BLOCKED-ON AKn]` markers are now **contracts**, but a sealed-candidate rule cannot be presented until a seal exists to verify it against | a real seal passes every §3 field and a deliberately-defective seal fails at the expected field |
| **D7** | **`epyc.autokernel.operator_waiver.v1` + K-WAIVER clause** | 2 | four dependencies: Annex K must exist (item 1); the release protocol needs a §2 registry row; the retention clause must be in force for `durability_class`'s enum; D6's disposition determines whether `seal_sha256` survives | all four, per `operator-waiver-schema.draft.md` §8 |
| **D8** | **Closed-enumeration reconciliation** for D3/D4 | 1b | `MEASUREMENT.md:141-142`, `MEASUREMENT_POLICY.md:71-73` and `BUS_PROTOCOL.md:38-39` restate one closed list of human-only writes; D3/D4 add two classes to none of them | either a §5 append extending the enumeration + CHANGELOG + matching one-line digest and bus-protocol deltas, or an on-the-record declaration that the enumeration is illustrative, with its precedent |
| **D9** | **`P-KERNEL-FREEZE-1` placement** — Annex K, or distributed amendments to B and G | 2 | operator decision, deliberately open | decide by the rule at `Annex-K-container.draft.md` §9: **Annex K only if its cross-tree scope clause cannot be stated without forward-referencing between B and G** |
| **D10** | **Campaign-manifest schema deltas** owed by AK1 | design, no signature | `epyc.autokernel.campaign.v2` carries none of the fields items 2 and 5 name | AK1 lands `calibration_block_count`, `contribution_floor`, `confirmation_admission_count`, `max_blocks_per_candidate`, `historical_win_replay`, `namespace_roots`, `retention_hold_boundaries`, `storage_floor_bytes_free`, `storage_safety_factor`, `host_reserve_bytes`. Enforced meanwhile by fail-closed conformance: a manifest omitting one makes its campaign non-conforming |

---

## E. Exact deltas — changed words only

Every block below is stated **against the apply-time preimage hash** recorded in
`RATIFICATION_LEDGER.md` §0, captured by `ratification_receipt.py capture` **before** any edit. This
is a shared clone; the files may move between presentation and apply, and a "changed words only"
delta is meaningless without a named preimage.

**Apply-time tokens** (produced by the apply, never guessed):

| Token | Supplied by | Form |
|---|---|---|
| `<APPLY_TS>` | the apply token timestamp | `20260803T HHMMSS Z` form, matching `bench-cpu.md:1` |
| `<APPLY_DATE>` | its date part | `YYYY-MM-DD` |
| `<PREIMAGE_SHA256>` | `ratification_receipt.py capture` | full hex, per amended file |
| `<RECEIPT_PATH>` / `<RECEIPT_SHA256>` | `ratification_receipt.py emit` | recorded in the **ledger only** — never in the CHANGELOG, which would make the receipt hash itself stale |

### E.1 — Layout paragraph · `MEASUREMENT.md:16-21` · item 1

**Before** (lines 17–19, the sentence only):

> Full normative protocol text lives in
> three annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
> file — they are the constitution, filed by family, not commentary on it.

**After** — two changed words, one added phrase:

> Full normative protocol text lives in
> **four** annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
> file — they are the constitution, filed by family **or instrument class**, not commentary on it.

> **This is a substitution, not a strike.** Annex K is explicitly not a measurement family — that is
> the whole argument for creating it — so *"four annexes … filed by family"* would leave the
> constitution asserting something this bundle denies. If you prefer a shorter delta, the alternative
> that is true under both readings deletes the descriptive clause instead of qualifying it:
>
> > … they are the constitution, not commentary on it.
>
> One of the two lands. There is no third option in which the paragraph says something false.

### E.2 — Annex key line · `MEASUREMENT.md:45-46` · item 1

**Before:**

> Full normative text: **B** = `measurement/protocols/bench-cpu.md`, **Q** =
> `measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`.

**After** — a comma and one clause before the terminal period:

> Full normative text: **B** = `measurement/protocols/bench-cpu.md`, **Q** =
> `measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`,
> **K** = `measurement/protocols/kernel-research.md`.

The status legend on the following line (`:47`) is unchanged.

### E.3 — Registry row · `MEASUREMENT.md` §2, appended after `:66` · item 2

> `| P-AK-SEARCH-1 | Kernel-candidate search inside experimental worktrees, per-backend | search verdict — **not a claim**; direction carried per record | ✅ <APPLY_DATE> | K |`

Five-column order preserved (`Protocol | Scope | Metric (direction) | Status | Annex`, `:49-50`).

**Two words are load-bearing.** *"per-backend"* — a single protocol id scoped across backends would
make a CPU-vs-GPU candidate comparison a *within-protocol* comparison, which `MEASUREMENT.md:83-84`
permits without labelling it analysis, laundering the cross-device composite withdrawn on 2026-08-02.
*"direction carried per record"* — `:40` requires direction wherever ambiguous, and a **ranking**
instrument has direction; it lives on the per-record metric, not on the protocol.

**Conditional:** this row lands **iff** item 2 lands. If item 2 is struck, the row is not added.

### E.4 — Annex G cross-reference · `gpu-cross-device.md`, appended after `:21` · item 3

Appended immediately after the kernel-provenance paragraph, before the blank line preceding
*"**Required evidence fields**"* at `:23`:

> *Narrowed for in-worktree candidate search only by `P-AK-SEARCH-1` (Annex K, ratified
> `<APPLY_DATE>`). The decision-grade clause above is unchanged, and the consumption clause continues
> to bind every consumer other than the AutoKernel controller that produced the record, within the
> campaign that produced it.*

### E.5 — Annex B §E · `bench-cpu.md`, appended at end of file · item 4

Full text: [`preflight-substitute.draft.md`](preflight-substitute.draft.md) §3, the blockquote.
Substitute `<APPLY_DATE>` in the section heading. Appended after `bench-cpu.md:240`; **nothing in the
existing file is edited in place** — the five superseded spans are superseded *by* §E's text, which is
how append-or-version works.

### E.6 — Digest bullet · `agents/shared/MEASUREMENT_POLICY.md:38` · item 4

A single long bullet. **Quoted whole, before and after**, because a described delta cannot be
pre-validated (`MEASUREMENT.md:145`) and this is a human-only file whose whole point is that the human
reads what lands.

**Before** (one line, `:38`):

> - **Before any bench**: hold the region claim for the run's footprint via `region-lock` (`bench_canonical.sh` acquires it automatically and refuses to run unlocked). Concurrency alone is never grounds for a human gate — operator approval only where `operator_gates[]` names a trust boundary (`OPERATING_CONSTRAINTS.md` → Inference and Benchmarks, amended 2026-07-27). Host-health preflight (uptime ≤1wk → drop_caches + NUMA-interleave rewarm; ≥1wk → reboot required); `pgrep` zombie check.

**After** — the final clause only is replaced; everything before it is byte-identical:

> - **Before any bench**: hold the region claim for the run's footprint via `region-lock` (`bench_canonical.sh` acquires it automatically and refuses to run unlocked). Concurrency alone is never grounds for a human gate — operator approval only where `operator_gates[]` names a trust boundary (`OPERATING_CONSTRAINTS.md` → Inference and Benchmarks, amended 2026-07-27). Host-health preflight (uptime ≤1wk → drop_caches + NUMA-interleave rewarm; ≥1wk → reboot required); no-concurrent-inference precondition per Annex B §E — `WITNESS` (claim + own-scope + residual-load witness) or `LEGACY`; **never a name-pattern process read** (`CLAUDE.md:84`).

### E.7 — Retention clause · `MEASUREMENT.md` §5, appended after `:160` · item 5

Full text: [`evidence-retention.draft.md`](evidence-retention.draft.md) §3, the blockquote.
Substitute `<APPLY_DATE>`. Appended immediately after the 2026-08-02 durability bullet, because
retention is the half of durability that clause left open.

*Appending to the **core** file rather than an annex is legitimate here: §5 is the core file's own
governance section, and two ratified precedents did exactly this — the 2026-08-02 durability bullet
(`:146-160`) and the 2026-07-31 category amendment (`:251-255`).*

### E.8 — §6 dump-list cross-reference · `MEASUREMENT.md`, appended after `:229` · item 6

> Autonomous-loop reclamation of the enumerated expirable classes is governed by §5 *"Evidence
> retention and reclamation"*; this list is otherwise closed and confers no authority beyond its own
> enumeration.

### E.9 — §6b strategy-store narrowing · `MEASUREMENT.md` §6b · item 7

Appended as a new row to the per-corpus table (after `:217`), narrowing the existing ruling at `:216`:

> `| Kernel-research strategy store (`scripts/kernel_rnd/kernel_store.py` SQLite; rows written before <APPLY_DATE>) | pre-ratification rows | demote-to-prior (:180-182) + quarantine | Narrows the `Strategy store / STM / planner narrative` ruling above for these rows only. Their evaluator never gated on coherence, so correctness labels were emitted without an anchor comparison and are not verdicts. Quarantined from every correct-only frontier and readiness computation. Any lineage decision resting only on them gets a re-measure ticket (:164-166). Rows of that corpus written by the routing planner or the STM are NOT affected. |`

### E.10 — CHANGELOG · `MEASUREMENT.md:239`, inserted as the new first entries · all items

Inserted immediately after the `## CHANGELOG` heading, matching the placement of the current newest
entry (`:241-245`). **One bullet per item that lands; drop the bullet of any struck item.**

> - **`<APPLY_DATE>` (v2.x)** — AMENDMENT: **Annex K** (`measurement/protocols/kernel-research.md`)
>   created as a **fourth** annex, for cross-backend kernel-research and kernel-release instruments,
>   holding `P-AK-SEARCH-1` (per-backend candidate search inside experimental worktrees; emits
>   **search verdicts, not claims**). Supersedes the layout sentence at `:16-21` and the annex key
>   line at `:45-46`, both ratified 20260730T103218Z; §2 gains a `P-AK-SEARCH-1` row.
>   `gpu-cross-device.md:16-21`'s consumption clause is **narrowed** for in-worktree candidate search
>   only, with the cross-reference appended there. Full delta:
>   `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md`.
> - **`<APPLY_DATE>` (v2.x)** — AMENDMENT: Annex B gains **§E exclusion preconditions** — the
>   no-concurrent-inference precondition is established by a held resource claim, own-scope
>   enumeration and a residual-load witness over attribution classes, or by the unchanged `LEGACY`
>   path. Supersedes the instrument phrase at `bench-cpu.md:15-16` and the name-witness limbs at
>   `:53-54`, `:63-64`, `:72-74`; the quantitative machinery at `:66-71` is adopted unchanged.
>   `MEASUREMENT_POLICY.md:38` updated in the same transaction. Full delta: same ledger.
> - **`<APPLY_DATE>` (v2.x)** — AMENDMENT: §5 gains **evidence retention and reclamation** — three
>   durability classes, a closed list of three expirable artifact kinds under an eight-conjunct
>   predicate, fail-closed tombstones written before any unlink, `storage_floor_bytes_free` and the
>   `DISK_PRESSURE` stop state. Extends and supersedes nothing in the 2026-08-02 durability clause
>   (`:146-160`). `:223-229` is unedited and confers no authority this clause relies on. Full delta:
>   same ledger.
> - **`<APPLY_DATE>` (v2.x)** — AMENDMENT: §6b **narrows** the strategy-store ruling at `:216` for the
>   kernel-research rows written by `scripts/kernel_rnd/kernel_store.py` before this date:
>   demote-to-prior plus quarantine from correct-only frontiers and readiness. Rows written by the
>   routing planner or the STM are unaffected. Full delta: same ledger.
> - **`<APPLY_DATE>` (v2.x)** — `coordination/session-bus/human_only_paths.yaml` gains two
>   `conceptual:` entries (evaluator immutability requires OS-level enforcement; `glob:` entries are
>   declarative only until `check_trust_boundary_edit.sh:90` is repaired) and its `.sha256` pin is
>   rewritten. Adds no path and no write class; supersedes nothing.

*No CHANGELOG bullet carries `<RECEIPT_SHA256>`. The receipt hashes the files it amends, so writing
its own digest into one of them would make its recorded post-state hash stale the instant it was
cited — the value cannot be computed without invalidating itself. It goes in the ledger, matching
`MEASUREMENT.md:250`, which cites a ledger path and no digest.*

### E.11 — Gate list · `human_only_paths.yaml`, appended to `conceptual:` after `:60` · item 8

```yaml
  - "AutoKernel evaluator immutability against non-agent writes — the PreToolUse layer sees agent tool calls only, so a daemon or a candidate subprocess bypasses it entirely; the enforcing layer is OS-level (separate uid or read-only bind mount), and no glob can express it"
  - "glob: entries in the paths: block above were DECLARATIVE ONLY until 2026-08-03: the matcher in scripts/hooks/check_trust_boundary_edit.sh quoted its right-hand side, which disables bash pattern matching, so measurement/protocols/*.md matched nothing and Annexes B/Q/G were agent-writable through Write/Edit while the guard reported success. Literal entries were unaffected and always blocked, which is why the defect survived every prior test. REPAIRED in epyc-root 6f1c4a8b (RHS unquoted) with scripts/hooks/test_check_trust_boundary_edit.sh asserting both directions against the live gate list. A future editor must not re-quote it"
```

`schema_version` (`:19`) is unchanged: both entries use the existing v1 bare-string shape.

---

## F. The operator command sequence

Run **in this order**. Every command is pre-validated: `apply_ratification.sh` executes the whole
sequence in dry-run and refuses to proceed if any edit site has drifted.

### Step 0 — commit the bundle (before anything else)

```bash
cd /workspace
git ls-files artifacts/operator/autokernel-policy-draft/          # inspect what is already tracked
git status --short artifacts/operator/autokernel-policy-draft/
git add -- artifacts/operator/autokernel-policy-draft/
git commit -- artifacts/operator/autokernel-policy-draft/
```

**Pathspec-limited, always.** This is a shared clone; another session's staged files ride into any
unqualified commit. And the bundle must be in git before it is signed over: a working-tree file is one
`git checkout` from gone and invisible to a reviewer who clones — the exact failure
`MEASUREMENT.md:146-156` was ratified to close.

### Step 1 — dry run, read the diff

```bash
bash artifacts/operator/autokernel-policy-draft/apply_ratification.sh
```

Prints an exact diff preview of every change and exits without writing. **Read it.** If any
`EXPECTED CONTENT NOT FOUND` line appears, a target file has drifted since this package was authored;
stop and re-present with updated hashes — the **same** apply token, never a restarted chain
(`MEASUREMENT.md:143-144`).

### Step 2 — capture the preimage

```bash
python3 scripts/operator/ratification_receipt.py capture \
  MEASUREMENT.md \
  measurement/protocols/bench-cpu.md \
  measurement/protocols/gpu-cross-device.md \
  agents/shared/MEASUREMENT_POLICY.md \
  coordination/session-bus/human_only_paths.yaml
```

Record each digest in `RATIFICATION_LEDGER.md` §0. Every "changed words only" delta in §E is defined
against these bytes.

### Step 3 — apply

Whole package:

```bash
bash artifacts/operator/autokernel-policy-draft/apply_ratification.sh --apply
```

With items struck — pass only the ones you are ratifying:

```bash
bash artifacts/operator/autokernel-policy-draft/apply_ratification.sh --apply --only 1,2,3,5,8
```

The script refuses `--only 2` without 1 or 3, and refuses `--only 3` without 2, because those
couplings are `:116-118` requirements rather than preferences. It is **idempotent**: re-running after
a partial apply detects what already landed and skips it.

### Step 4 — the `human_only_paths` two-step is ONE action

> **Atomic. Do not separate these, and do not do anything between them.**
>
> ```bash
> # 4a — edit the gate list (the script does this under --apply; shown for a manual apply)
> #      append the two conceptual: entries from §E.11 — this is the LAST byte-level change
>
> # 4b — rewrite the pin, using the command the file documents at :15-17
> sha256sum coordination/session-bus/human_only_paths.yaml | awk '{print $1}' \
>   > coordination/session-bus/human_only_paths.sha256
> ```
>
> The pin is a **whole-file** content hash (`config.yaml:161-164`), so any edit invalidates it. A
> struck YAML edit with an applied pin, or an applied edit with a struck pin, both produce drift —
> and the audit **cannot distinguish that drift from a hostile out-of-band edit**, because every
> session commits under one git identity (`session_bus_coordinator.py:1100-1105`). Computing the pin
> and then making one more whitespace correction reproduces exactly that signature.
>
> If you correct anything in the YAML after computing the pin, **recompute the pin**. That is the
> whole rule.

### Step 5 — emit the receipt

```bash
python3 scripts/operator/ratification_receipt.py emit --pre <snapshot-from-step-2>
```

Record `<RECEIPT_PATH>` and `<RECEIPT_SHA256>` in `RATIFICATION_LEDGER.md` §8 — **not** in the
CHANGELOG.

### Step 6 — commit the applied state

```bash
git commit -- MEASUREMENT.md \
              measurement/protocols/bench-cpu.md \
              measurement/protocols/gpu-cross-device.md \
              measurement/protocols/kernel-research.md \
              agents/shared/MEASUREMENT_POLICY.md \
              coordination/session-bus/human_only_paths.yaml \
              coordination/session-bus/human_only_paths.sha256 \
              artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md
```

---

## G. Verification

Run after the apply. Also runnable later by any auditor:
`bash artifacts/operator/autokernel-policy-draft/apply_ratification.sh --verify`.

### G.1 Trust-boundary pin

```bash
python3 scripts/coordination/session_bus.py validate
```

**Expect:** exit 0, no `FAIL trust boundary DRIFT`. A mismatch prints
`FAIL trust boundary DRIFT: … the gate list changed outside the operator path. Re-pin deliberately or
revert.` and returns 1 (`session_bus.py:644-657`, `:661-686`).

> **What this does NOT prove.** `validate` hashes the gate list against its pin. It says nothing about
> whether the paths the gate list names are enforced. Passing here while the matcher is broken is
> exactly the tautology `feedback_verify_integrity_not_presence_of_own_edit` warns about — *verifying
> that the glob matches is not the same as verifying the consumer enforces it*.

### G.2 Hook enforcement — the real probe

```bash
probe() {
  printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$1" \
    | CLAUDE_PROJECT_DIR=/workspace bash /workspace/scripts/hooks/check_trust_boundary_edit.sh \
      >/dev/null 2>&1; echo "$?  $1"
}
probe /workspace/MEASUREMENT.md
probe /workspace/measurement/protocols/bench-cpu.md
probe /workspace/measurement/protocols/kernel-research.md
```

| Target | Expected today | Meaning |
|---|---|---|
| `MEASUREMENT.md` | **2 — BLOCKED** | literal entry; layer 1 works |
| `bench-cpu.md` | **0 — ALLOWED** | glob entry; **matcher defect (D5), pre-existing** |
| `kernel-research.md` | **0 — ALLOWED** | same defect; the new annex is no worse and no better than B/Q/G |

**Record the actual exit codes in the receipt.** A `2` on either annex means D5 landed — good, and
the C2 conceptual entry should then be amended out. A `0` is the expected, disclosed state; it is not
a failure of this apply.

### G.3 The deltas landed

```bash
grep -n 'four annexes' MEASUREMENT.md                               # E.1
grep -n 'kernel-research.md' MEASUREMENT.md                         # E.2
grep -n 'P-AK-SEARCH-1' MEASUREMENT.md                              # E.3 (item 2 only)
grep -c 'P-AK-SEARCH-1' measurement/protocols/kernel-research.md    # annex body, non-zero
grep -n 'Narrowed for in-worktree candidate search' measurement/protocols/gpu-cross-device.md   # E.4
grep -n '§E — Exclusion preconditions' measurement/protocols/bench-cpu.md                       # E.5
grep -n 'pgrep' agents/shared/MEASUREMENT_POLICY.md                 # E.6 — expect NO zombie-check hit
grep -n 'Evidence retention and reclamation' MEASUREMENT.md         # E.7
grep -n 'storage_floor_bytes_free' MEASUREMENT.md                   # E.7
grep -n 'kernel_store.py' MEASUREMENT.md                            # E.9 (item 7 only)
grep -c 'DECLARATIVE ONLY' coordination/session-bus/human_only_paths.yaml   # E.11, expect 1
```

### G.4 No placeholder survived into the constitution

```bash
grep -nE '<DATE>|<APPLY_DATE>|<APPLY_TS>|BLOCKED-ON|TBD|DRAFT' \
     MEASUREMENT.md measurement/protocols/*.md
```

**Expect no output** *once transcription is finished*. Any hit means a token was transcribed instead
of substituted — the single most common apply defect.

**Expected transient hit.** `apply_ratification.sh` creates the Annex K file with a `TRANSCRIBE, THEN
DELETE THIS COMMENT` marker that deliberately contains the literal token, so this check **fails while
the annex body is still un-transcribed**. That is the intended signal: an un-transcribed annex cannot
be mistaken for a finished one. Delete the marker when you paste the Remit and the protocol text, and
re-run.

### G.5 Nothing was destroyed

```bash
git diff --stat HEAD~1 -- MEASUREMENT.md measurement/protocols/
```

**Expect additions only**, plus the small in-place replacements at `MEASUREMENT.md:16-21` and `:45-46`
(items 1). Any deletion in `measurement/protocols/` is a defect: §E and the retention clause are
appends, and the superseded spans in `bench-cpu.md` are superseded *by* §E's text, not removed.

### G.6 Production kernels untouched

```bash
bash scripts/session/verify_llama_cpp.sh
git -C /mnt/raid0/llm/llama.cpp status --short
```

**Expect:** the production branch unchanged and a clean tree. No item in this package reads, writes or
references a production kernel branch; this confirms it.

### G.7 Downstream validators

```bash
python3 scripts/validate/validate_agents_references.py
scripts/validate/check_claims_grammar.sh
python3 /mnt/raid0/llm/epyc-inference-research/scripts/validate/check_evidence_durability.py
```

*The durability validator is in the **research** repo. `MEASUREMENT.md:155` names it at
`scripts/validate/check_evidence_durability.py` in epyc-root, where it does not exist — a defect in
the 2026-08-02 amendment, reported in the ledger §3 and not fixed by this package.*
