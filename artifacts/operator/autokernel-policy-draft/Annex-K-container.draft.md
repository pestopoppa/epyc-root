<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Staged for operator review per
     artifacts/operator/autokernel-policy-draft/README.md (attestation 1).
     Target: NEW FILE measurement/protocols/kernel-research, plus the three core-file
     deltas in §4 of this document. Annex creation approved by operator 2026-08-02
     (handoffs/active/autokernel-research-loop.md:1855-1861).
     Scope: CONTAINER ONLY. The normative text of P-AK-SEARCH-1 is a separate draft and a
     separate strikeable line in the same attestation. Author: AutoKernel design pass. -->

# DRAFT — Annex K container (kernel research & release)

**Status:** COMPLETE AND SIGNABLE (revised 2026-08-03 after adversarial review). Every binding below
is a **contract or a procedure**; the only unfilled tokens are apply-time literals enumerated in §5,
each with the artifact that supplies it at apply time. There are no `[BLOCKED-ON]` bindings in this
document, by construction — see §10 *Residual dependencies*.

**Creates:** a fourth annex file, `measurement/protocols/kernel-research`.
**Also changes:** three lines of `MEASUREMENT.md` (§4a, §4b, §4c) plus one appended sentence in Annex
G (§4d). Nothing else.
**Does not create:** `P-AK-SEARCH-1`. Its normative text is drafted separately and cited here by
protocol id only.
**Presented in:** attestation **1a** ("constitutional scaffolding"), as item 1 of
[`RATIFICATION_PACKAGE.md`](RATIFICATION_PACKAGE.md).

**Presentation-precondition correction (blocking defect, fixed).** An earlier revision asserted that
"the package is signable tonight" while the owning handoff defines attestation 1's validation evidence
as *"AK1–AK3 deliverables plus the four calibrated controls"*
(`handoffs/active/autokernel-research-loop.md:1771`), with AK1 at 0/17, AK2 at 0/12 and AK3 at 0/14
checkboxes. Both statements cannot be true. The resolution is to **split the handoff's attestation 1
in two**, which the package does:

- **Attestation 1a (tonight)** — the constitutional scaffolding whose referents all exist today: the
  annex container, the protocol text, the Annex G cross-reference, the Annex B exclusion
  preconditions, the retention clause, and the core-file §6/§6b lines. None of these binds to an
  AK1–AK3 deliverable; none grants operable authority; every one of them fails closed until the
  machinery exists. `MEASUREMENT.md:138-145` is satisfied because the validation results being signed
  over are *textual and structural* — preimage hashes, exact state diff, hook and pin verification —
  not campaign measurements, and there are no campaign measurements to wait for.
- **Attestation 1b (after AK3)** — every item that binds to a delivered artifact: the evaluator-bundle
  and policy-plane gate-list entries, the Stage I sanctioned enumerator, and the Annex G extension of
  §E. These are enumerated in `RATIFICATION_PACKAGE.md` §D and are **not** presented tonight.

That split preserves the draft-early / ratify-last sequencing the handoff records at `:1867-1869`: it
ratifies no binding whose referent is missing, and it defers every binding whose referent is.

**Owning handoff:** `handoffs/active/autokernel-research-loop.md` §3.1, §14 AK0.

**Transcription note.** Per `artifacts/operator/autokernel-policy-draft/README.md:87-93`, markdown
filenames in this staging area are written **without** the `.md` extension so the repository's
reference guard (`scripts/hooks/agents_reference_guard.sh`, PreToolUse) does not block edits to a
document that necessarily cites a file which does not yet exist. Restore `.md` on every occurrence of
`measurement/protocols/kernel-research` when this text is transcribed at apply time.

**Supersedes within this staging area — one map, stated identically in both files.** This container
supersedes **§1, §2, §5 (the ratification checklist) and §6** of
[`Annex-K-kernel-research-and-release.draft.md`](Annex-K-kernel-research-and-release.draft.md); the
sibling [`P-AK-SEARCH-1.draft.md`](P-AK-SEARCH-1.draft.md) supersedes that file's **§3 and §4**.
Between them the mixed draft is superseded in whole. It is **PROVENANCE ONLY — NOT PRESENTED**, and no
third reading of it is possible. Two drafts of one annex MUST NOT both be presented; the operator
receives this container plus the sibling protocol draft.

*(Correction: an earlier revision of this paragraph named "§4 (checklist)". The mixed draft's §4 is
"Bindings still blocked" and its §5 is the checklist. The mapping above is the corrected one, and
`P-AK-SEARCH-1.draft.md:15-24` now states the identical map.)*

**Consequence for the apply.** The **live ratification checklist is §8 of this document**, plus the
package sequence at [`RATIFICATION_PACKAGE.md`](RATIFICATION_PACKAGE.md) §E/§F. The retired checklist
at `Annex-K-kernel-research-and-release.draft.md:199-213` — the one carrying the `[BLOCKED-ON]` line —
does not govern anything.

---

## 1. Why a fourth annex

`MEASUREMENT.md:16-21` declares the annex layout, and it declares exactly three:

> Full normative protocol text lives in
> three annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
> file — they are the constitution, filed by family, not commentary on it.

*(The owning handoff and the staging README cite this paragraph as `:15-20`; `:16-21` is its exact
extent in the current file. Line 15 is blank.)*

The three are enumerated at `MEASUREMENT.md:45-46`: **B** = `measurement/protocols/bench-cpu.md`
(CPU bench family), **Q** = `measurement/protocols/quality-eval.md` (quality/eval/significance
family), **G** = `measurement/protocols/gpu-cross-device.md` (GPU and cross-device family). Each
annex letter is mnemonic for its family, and each annex file's header block says which family it is
(`bench-cpu.md:1-2`, `quality-eval.md:1-2`, `gpu-cross-device.md:1-2`).

`P-AK-SEARCH-1` fits none of the three, on two independent grounds:

- **It is cross-backend.** Its scope is every AutoKernel backend adapter — `llama_cpu`, `llama_gpu`,
  `whisper_stt`, `qwentts_tts`, `serving_runtime`
  (`handoffs/active/autokernel-research-loop.md:144-145`). B is CPU, G is GPU/cross-device, and
  neither `whisper.cpp` nor `qwentts.cpp` has any protocol family at all today
  (`handoffs/active/autokernel-research-loop.md:2240`). No existing annex letter can hold a
  protocol that governs all of them without redefining that letter's family.
- **It is a search instrument, not a measurement family.** B, Q and G each define how a *claim* is
  produced. `P-AK-SEARCH-1` defines a narrow authority to **rank, retain, abandon, or branch**
  candidates inside experimental worktrees — the four verbs the design enumerates
  (`handoffs/active/autokernel-research-loop.md:352-353`) — and it emits **search verdicts that are
  explicitly not claims** (`:352-356`). *(Composition is deliberately not listed here. It is a T2
  activity carrying its own mandatory combined-candidate re-evaluation obligation (`:2024`,
  §9.7 `:1373-1375`, and `:1194`'s prohibition on inferring composition by multiplying local
  speedups); where it is authorized at all, it is authorized inside `P-AK-SEARCH-1` with that
  obligation attached, not by a container's rationale.)* Filing an instrument that
  produces non-claims inside an annex whose organising principle is "how this family's claims are
  produced" mislabels it at the level of the file name.

### 1a. The rejected alternative — splitting across B, Q and G

The alternative considered was to write `P-AK-SEARCH-1` as three coordinated sections: a CPU search
section appended to Annex B, a GPU search section appended to Annex G, and a quality/correctness
section appended to Annex Q. It was rejected for four reasons, in descending order of weight:

1. **It destroys the property that matters most about the authority.** The whole point of
   `P-AK-SEARCH-1` is that the lift of the consumption prohibition at `gpu-cross-device.md:16-21` is
   *narrow, unified, and revocable in one place*. It **narrows** that clause rather than restating or
   replacing it, so it is admissible to K under §2's narrowing carve-out, and §4d appends the required
   cross-reference to Annex G in the same apply — the reader of Annex G is never left with an
   unqualified absolute that a K-filed protocol has quietly changed. An authority spread over three
   files is read three
   times, audited three times, and widened one file at a time. A reviewer asking "what exactly may
   the loop decide for itself?" MUST be able to answer it by reading one file.
2. **Three amendment histories where one belongs.** `MEASUREMENT.md:116-118` makes amendments
   *"human-only, PR-reviewed, append-or-version — protocols are never silently edited. An amendment
   appends to the owning annex …"*. A three-way split means every future calibration of the same
   protocol appends to three annexes and must be kept consistent by hand, with three chances to
   diverge and no mechanism that detects divergence.
3. **The registry cannot express it.** `MEASUREMENT.md:49-50` gives each protocol row exactly one
   **Annex** cell. A protocol split across B, Q and G either gets three rows (three protocol ids,
   which is a different design) or one row with a false annex letter.
4. **It would silently widen B and G.** Appending search authority to Annex B makes Annex B — the
   file every CPU bench cites — a file that also grants an automated process ranking authority. That
   is authority creep by filing decision, which is the failure mode this package is most concerned
   with.

The cost of the fourth annex is one more file to open and one more line in the registry key. That is
the correct trade.

### 1b. Why the letter K

`K` for **kernel**, following the existing mnemonic convention (B/bench, Q/quality, G/GPU). It is
unused in the registry (`MEASUREMENT.md:49-66`) and does not collide with any status glyph or column
value.

---

## 2. What Annex K holds

> **Remit.** Annex K holds protocols that govern **kernel research and kernel release** across source
> trees and backends: instruments whose subject is a *candidate kernel* rather than a measurement
> family, and instruments that are cross-backend by construction.
>
> **Admission to Annex K requires ALL of:**
>
> 1. the protocol's subject is a kernel candidate, a kernel lineage, or a kernel release decision;
> 2. the protocol is cross-backend — it governs at least two of `llama_cpu`, `llama_gpu`,
>    `whisper_stt`, `qwentts_tts`, `serving_runtime` — **and** it is a search or release instrument
>    that produces records which are not claims; and
> 3. no existing annex (B, Q, G) already **states** the rule this protocol **establishes**.
>
> **Narrowing carve-out (test 3).** A protocol that *narrows* a rule stated in another annex, without
> restating or replacing it, is admissible to K **only if the owning annex receives an appended
> cross-reference in the same apply** recording that its rule has been narrowed and by what (see §4d).
> A protocol that *restates or replaces* another annex's rule is not an Annex K protocol at all; it is
> an amendment to the owning annex, and where a rule already lives, the amendment goes.
>
> **Every protocol filed in Annex K MUST state, in its own grammar line, the class of record it
> emits** — a claim, or a verdict that is not a claim.
>
> **Comparison scope.** Records emitted under an Annex K protocol are comparable **only within one
> backend and one instrument version**. Cross-backend roll-ups are labelled analysis and never gate
> (`MEASUREMENT.md:83-84`; owning handoff §1.6). A single Annex K protocol id spanning several
> backends does NOT make a cross-backend comparison a within-protocol comparison.
>
> **Prospective.** Creating Annex K neither retro-certifies nor upgrades any artifact. No measurement
> taken before the apply timestamp becomes a claim, or a conforming record of any Annex K protocol, by
> virtue of this annex existing. Protocols already filed in B, Q or G stay there; Annex K MUST NOT be
> used to relocate an existing protocol.

At apply time, Annex K holds exactly one protocol: **`P-AK-SEARCH-1`**, whose normative text is a
separate item on the same attestation. Whether `P-KERNEL-FREEZE-1` later joins it is deliberately
left open — see §9.

## 3. What Annex K does NOT hold

Stated as carefully as §2, because the remit of a new container is decided once and then defended.

| Item | Where it goes instead | Why |
|---|---|---|
| **P-GPU-1 sealed-candidate amendment** | Annex **G**, appended to `P-GPU-1` | Fails admission test (3): the rule it amends — the kernel-provenance rule at `gpu-cross-device.md:16-21` — already lives in G. Per `MEASUREMENT.md:116-118` an amendment *appends to the owning annex*. Drafted at [`P-GPU-1-sealed-candidate-amendment.draft.md`](P-GPU-1-sealed-candidate-amendment.draft.md); rides attestation **2**, not this one (`README.md:41-48`). |
| **The `pgrep` substitute** (claim witness + own-scope enumeration + residual-load witness) | Annex **B**, amending the precondition in place. Annex **G** deferred | Fails admission test (3): the precondition it replaces is `bench-cpu.md:16-17` (*"no concurrent inference (`pgrep llama` zombie check…)"*) — the one place in the entire annex corpus where `pgrep` is mandated. It is an equivalence amendment to an existing precondition, not a new instrument. *(Corrected after review: an earlier revision also routed it into Annex G on the strength of `gpu-cross-device.md:28-30`. That text reads *"`llama-server` / AutoPilot / KFD **PID checks** before and after"* — a PID check, not a name pattern — so Annex G never mandated the banned operation and there is nothing there to repair. The Annex G extension is deferred to attestation 1b; see `RATIFICATION_PACKAGE.md` §D, D2.)* Owning handoff §3.5. |
| **The evidence-retention rule** (expirable classes, tombstoned expiry) | `MEASUREMENT.md` **§5 Governance**, appended next to the durability clause | Fails admission tests (1) and (3): its subject is evidence lifecycle, not kernels, and the rule it qualifies is the core-file durability clause at `MEASUREMENT.md:146-156` — which is also the correct anchor for evidence survival. *(Corrected after review: an earlier revision cited `MEASUREMENT.md:223-229` as establishing general operator reclamation authority. It does not. `:223-229` is the 2026-06 reconciliation's **explicit dump list**, whose rule is that everything not enumerated **is kept**, and whose only "operator call" is ~1.2 GB of superseded embedding blobs under `repl_memory/sessions/`. It confers no general authority over anything else, and the retention clause is a fresh, self-contained, bounded grant rather than a slice carved from it.)* Owning handoff §3.7, §5.8. |
| **`human_only_paths.yaml` additions** and the `.sha256` rewrite | `coordination/session-bus/human_only_paths.yaml` (+ its pin) | Not a protocol at all. Separate strikeable line on the same attestation. See §6 for the part of it this item does *not* need. |
| **`epyc.autokernel.operator_waiver.v1`** — the **JSON schema** | Schema plane, attestation 2 | Not a protocol; a data contract consumed by the release gate. |
| **`K-WAIVER`** — the **normative waiver clause** that governs authorship, ACTIVE conditions and claim suppression | Annex **K**, attestation **2** | *(Reconciled after review. An earlier revision routed the whole waiver object to the schema plane while its own draft §7 recommended Annex K, giving the operator two contradictory placements.)* The clause passes all three admission tests: its subject is a kernel release decision (1); it is cross-backend by construction — one waiver may enumerate CPU and GPU cells of one llama freeze (2); and it **establishes** a rule no annex states today — `bench-cpu.md:96` *names* an operator waiver but defines no instrument, so K states the instrument rather than restating B's rule (3). Under the §2 narrowing carve-out, `bench-cpu.md:96` receives an appended cross-reference in the same apply. Not presented tonight: [`operator-waiver-schema.draft.md`](operator-waiver-schema.draft.md) rides attestation 2. |
| **Freeze, cutover, era rows, AutoPilot baseline applies** | Nowhere — they remain human-only | `MEASUREMENT.md:140-142`: *"Human-only writes remain exactly: era-registry rows, this constitution and its annexes, AutoPilot baseline-state applies, production freezes/cutovers, host reboots."* Annex K MUST NOT be read as creating, delegating, or conditioning any of them. |

> **Authority statement (normative).** The creation of Annex K grants no authority to any process.
> It creates a file and three registry lines. Every authority the AutoKernel loop obtains at
> attestation 1 comes from `P-AK-SEARCH-1`'s text, which is a separate strikeable line, and from
> nothing in this document. An operator who applies this container and strikes `P-AK-SEARCH-1` has
> granted nothing.

---

## 4. Exact core-file deltas

Three changes to `MEASUREMENT.md` (§4a, §4b, §4c) plus one appended sentence in Annex G (§4d). Each is
stated as changed words only, against the files as they stand at the apply-time preimage hashes
recorded in
[`artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md`](RATIFICATION_LEDGER.md) — the
path is written in full everywhere, because the only other `RATIFICATION_LEDGER.md` in this repository
belongs to the `measurement-v2-draft` bundle and writing into it would be a defect. The preimage hash
is captured by `scripts/operator/ratification_receipt.py capture` at presentation time and recorded as
the `<PREIMAGE_SHA256>` token in §5. **None may be applied by an agent** — `MEASUREMENT.md` and
`measurement/protocols/*.md` are human-amendment-only (`MEASUREMENT.md:119-120`;
`coordination/session-bus/human_only_paths.yaml:26-34`).

### 4a. Layout paragraph — `MEASUREMENT.md:16-21`

Two changed words and one added phrase. Nothing else in the paragraph moves.

> Full normative protocol text lives in
> **four** annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
> file — they are the constitution, filed by family **or instrument class**, not commentary on it.

**Why the second change is not cosmetic, and why it is NOT strikeable.** The existing phrase is
*"filed by family"*. Annex K is explicitly **not** a measurement family (§1) — that is the entire
argument for creating it. Leaving the paragraph reading "four annexes … filed by family" would make
the constitution assert something the same bundle denies.

An earlier revision offered the added phrase as an operator strike option and documented its strike
branch as leaving *"a known-false descriptive clause in the layout paragraph"*. **That option is
withdrawn.** A strike branch whose documented consequence is that the constitution asserts something
false is not a legitimate choice to place in front of a signer. Either the phrase lands, or §4a is
struck in full together with §4b — which is the coherent alternative and is stated in §7. If a shorter
delta is wanted, the symmetric alternative that is true under both branches is to delete the
descriptive clause rather than qualify it:

> Full normative protocol text lives in
> **four** annexes in `measurement/protocols/`, which carry the SAME trust boundary and amendment rules as this
> file — they are the constitution, not commentary on it.

That variant is offered as a **substitution**, not as a strike: one of the two §4a forms lands.

**On naming K here.** The layout paragraph names no annex today — enumeration lives at
`MEASUREMENT.md:45-46`, amended by §4b. Naming K in the layout paragraph while B, Q and G go unnamed
would be asymmetric, and naming all four would put the annex list in two places that must be kept in
sync by hand. **Recommendation: name K only at :45-46.** If the operator wants the layout paragraph
self-contained, the symmetric variant is:

> … lives in **four** annexes in `measurement/protocols/` (**B**, **Q**, **G**, **K**), which carry
> the SAME trust boundary …

### 4b. Protocol registry — `MEASUREMENT.md` §2

**(i) The key line at `MEASUREMENT.md:45-46`** — the sentence wraps across two source lines; the
change is a comma and one clause appended before the terminal period:

> Full normative text: **B** = `measurement/protocols/bench-cpu.md`, **Q** =
> `measurement/protocols/quality-eval.md`, **G** = `measurement/protocols/gpu-cross-device.md`,
> **K** = `measurement/protocols/kernel-research`.

The status legend on the following line (`MEASUREMENT.md:47`, *"Status: ✅ ratified, 📋 staged
(operator-apply)"*) is unchanged.

**(ii) One new table row**, appended after the last existing row (`MEASUREMENT.md:66`,
`P-DFLASH-LINEUP-1`), preserving the table's five-column order
`Protocol | Scope | Metric (direction) | Status | Annex` established at `MEASUREMENT.md:49-50`:

> | P-AK-SEARCH-1 | Kernel-candidate search inside experimental worktrees, **per-backend** | search verdict — **not a claim**; direction carried per record | ✅ `<APPLY_DATE>` | K |

**Two words in that row are load-bearing and were repaired after review.** *"per-backend"* replaces
*"(all backends)"*: a single protocol id scoped "all backends" would make a CPU-versus-GPU candidate
comparison a **within-protocol** comparison, which `MEASUREMENT.md:83-84` permits without labelling it
analysis — laundering exactly the cross-device composite the operator withdrew on 2026-08-02 (owning
handoff §1.6 `:161-166`; AK-D12 `:2228`). The Remit's comparison-scope clause (§2) says the same thing
normatively; the registry cell must not say the opposite. And *"direction carried per record"* replaces
a bare *"no direction"*, because `MEASUREMENT.md:40` requires direction to be stated wherever
ambiguous and this instrument's function is to **rank**: the direction is real, it just lives on the
per-record metric rather than on the protocol.

**The Metric cell deliberately names no throughput metric, and this is load-bearing.**
`P-AK-SEARCH-1` emits **search verdicts**, not claims: its records rank candidates inside
experimental worktrees and MUST NOT gate a keep / revert / deploy / promote / buy / close decision
(`MEASUREMENT.md:9-11`; `handoffs/active/autokernel-research-loop.md:352-356`). Writing `t/s (↑)`
into that cell would make the registry — the first place any session looks — assert that the protocol
produces decision-grade throughput numbers, which is exactly the misreading the protocol exists to
prevent. The registry already has this idiom for verdict-producing and non-quantitative protocols:
`P-PAIRED` carries *"verdict (not delta)"* (`MEASUREMENT.md:61`) and `P-SMOKE-1` carries
*"pass/fail"* (`:62`). This row follows them.

**Registry-cell agreement (moved here from the Remit).** An earlier revision stated inside the Annex K
Remit that *"the Metric (direction) cell of its `MEASUREMENT.md` §2 registry row MUST agree"* with the
protocol's declared record class, and that a disagreeing cell is a registry defect. That is a validity
rule about the **core file's** table, and an annex may not legislate over the core file
(`MEASUREMENT.md:19-21`, `:116-118`). The intra-annex obligation — *every protocol filed in Annex K
states the class of record it emits in its own grammar line* — stays in the Remit, where it belongs.
The registry-agreement expectation is stated here, in the delta that writes the cell, as the reason
this cell reads as it does. It binds nothing beyond this row.

**Status-cell rule (procedure, not a literal).** The cell reads `✅ <APPLY_DATE>` **iff**
`P-AK-SEARCH-1`'s normative text lands in the same apply. If the operator strikes the
`P-AK-SEARCH-1` line while retaining this container, the row MUST NOT be added at all — a registry
row pointing at normative text that does not exist is worse than no row. See §7.

### 4c. CHANGELOG — `MEASUREMENT.md:239`

One bullet, inserted immediately after the `## CHANGELOG` heading, i.e. as the new first entry —
matching the placement of the current newest entry (`MEASUREMENT.md:241-245`):

> - **`<APPLY_DATE>` (v2.x)** — AMENDMENT: **Annex K** (`measurement/protocols/kernel-research.md`)
>   created as a **fourth** annex, for cross-backend kernel-research and kernel-release instruments,
>   holding `P-AK-SEARCH-1` (per-backend candidate search inside experimental worktrees; emits
>   **search verdicts, not claims**). Supersedes the layout sentence at `:16-21` ("three annexes …
>   filed by family") and the annex key line at `:45-46`, both ratified 20260730T103218Z; §2 gains a
>   `P-AK-SEARCH-1` registry row. `gpu-cross-device.md:16-21`'s consumption clause is **narrowed** for
>   in-worktree candidate search only, with the cross-reference appended there. Full delta:
>   `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md`.

**Two repairs to this bullet, both from review.**

1. **"Additive — supersedes nothing" was false, and `MEASUREMENT.md:118` requires superseding
   amendments to name what they supersede.** §4a *replaces* the layout sentence at
   `MEASUREMENT.md:16-21` and §4b(i) *replaces* the annex key line at `:45-46`, both ratified
   20260730T103218Z. Only §4b(ii) and §4c are purely additive. The bullet now names both superseded
   sentences, following the precedent of the 2026-07-31 entry (`MEASUREMENT.md:251-255`), which names
   `bench-cpu.md:216-220` as superseded. The `RATIFICATION_LEDGER.md` entry MUST name them too, plus
   the preimage hash.
2. **`<RECEIPT_SHA256>` is removed from the CHANGELOG and the bullet cites the ledger instead.** The
   receipt written by `scripts/operator/ratification_receipt.py` carries `state_diff[]` — the exact
   before/after SHA-256 of every amended file — and is emitted *after* the edits land. Writing the
   receipt's own digest into `MEASUREMENT.md` mutates a file the receipt has already hashed, so the
   receipt's recorded post-state hash would be stale the instant it was cited: the value cannot be
   computed without invalidating itself. No existing CHANGELOG entry does this — the v2 entry
   (`MEASUREMENT.md:248-250`) cites a ledger **path** and no digest. `<RECEIPT_PATH>` and
   `<RECEIPT_SHA256>` are recorded in `RATIFICATION_LEDGER.md` and in the receipt, which is where a
   self-referential digest is harmless.

**Supersession statement (required by `README.md:58-71`).** This item supersedes the layout sentence
at `MEASUREMENT.md:16-21` and the annex key line at `:45-46` (prior receipt: the v2 apply,
20260730T103218Z, `artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md`). It invalidates no
prior measurement and changes the meaning of no protocol other than the narrowing recorded in §4d. The
`RATIFICATION_LEDGER.md` entry MUST state this explicitly rather than omitting the field — an absent
supersession field is indistinguishable from an unanswered one.

### 4d. Annex G cross-reference — `measurement/protocols/gpu-cross-device.md`

**Why this exists (blocking defect, fixed).** `P-AK-SEARCH-1` narrows the consumption clause at
`gpu-cross-device.md:16-21` — *"MUST NOT be consumed by AutoPilot or any automated optimizer"* — and
the owning handoff records that this clause is *"what stops AutoKernel ranking GPU candidates at all"*
(`:331`). An earlier revision routed **all** Annex G work to attestation 2, so after the apply,
`gpu-cross-device.md:20-21` would still have read as an unqualified absolute with no marker that a
K-filed protocol had changed what it means. `MEASUREMENT.md:116-118` calls that a silent edit by name.

One sentence, **appended** (never edited in place) immediately after P-GPU-1's kernel-provenance
paragraph, before the *"Required evidence fields"* heading:

> *Narrowed for in-worktree candidate search only by `P-AK-SEARCH-1` (Annex K, ratified
> `<APPLY_DATE>`). The decision-grade clause above is unchanged, and the consumption clause continues
> to bind every consumer other than the AutoKernel controller that produced the record, within the
> campaign that produced it.*

This is a **separate strikeable line** (`RATIFICATION_PACKAGE.md` item 3), and its strike branch is
stated on the attestation face: striking it while retaining `P-AK-SEARCH-1` leaves Annex G asserting
an absolute that has been narrowed elsewhere — the exact silent edit `:116-118` forbids. Striking
`P-AK-SEARCH-1` and retaining this line leaves a cross-reference to a protocol that does not exist,
which is equally wrong. **The two lines strike together or land together**, and §7 says so.

The sealed-candidate amendment (`P-GPU-1-sealed-candidate-amendment.draft.md`) remains on attestation
2, where it belongs: it *replaces* the absolute form of the provenance rule rather than narrowing it,
and its referents (seal, release plan, evidence hash tree) are AK1/AK3/AK5 deliverables.

---

## 5. The annex file to be created

Created by the apply, at `measurement/protocols/kernel-research` (restore `.md`). Header block
matching the preamble form of `bench-cpu.md:1-2`, `quality-eval.md:1-2` and
`gpu-cross-device.md:1-2`:

> ```
> <!-- RATIFIED <APPLY_TS>. Annex K of MEASUREMENT.md (same trust boundary, same
>      amendment rules). Kernel research and release protocol family. Remit and admission
>      test below are normative. -->
>
> # Annex K — Kernel research & release protocols
> ```

The third preamble line is a **deliberate deviation** from the two-line form used by B, Q and G: it
points a reader at the remit section instead of leaving a reader to infer the annex's scope from its
one member. An operator who prefers exact symmetry MAY strike it back to two lines; the remit section
itself is then found only by reading the file, which is acceptable but weaker. **This strike option is
retained** (unlike §4a's, which was withdrawn) because a two-line preamble is symmetric with B, Q and
G and asserts nothing false under either branch.

The annex body at apply time is, in order: the **Remit** block quoted in §2 above, then the
`P-AK-SEARCH-1` normative text from its own draft. Nothing else.

### Apply-time values

No value below is guessed, calibrated, or deferred. Each is a literal produced *by the apply itself*.

**Corrected producer.** An earlier revision said these are *"written mechanically by the bundle
assembler"*, citing `handoffs/active/autokernel-research-loop.md:1797-1801` — which reads *"Write one
assembler in AK6 and have AK0's attestations use it."* AK6 is 0/9 checkboxes and does not exist, so
that contract had no counterparty at apply time. The tool that **does** exist is
`scripts/operator/ratification_receipt.py` (`capture` then `emit`, arguments at `:700-732`), and
`apply_ratification.sh` in this directory drives it. Attestation 1a is assembled with that tool plus a
hand-written ledger; see §10 residual 3.

**Write order (normative, and it is what makes `<PREIMAGE_SHA256>` well-defined):**

1. `ratification_receipt.py capture` — records the preimage SHA-256 of every file about to be amended;
2. apply the §4a / §4b / §4c / §4d deltas and create the annex file;
3. `ratification_receipt.py emit --pre <snapshot>` — writes the receipt with `state_diff[]`;
4. record `<PREIMAGE_SHA256>`, `<RECEIPT_PATH>` and `<RECEIPT_SHA256>` in
   `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md`.

| Token | Supplied by | Form |
|---|---|---|
| `<APPLY_TS>` | the attestation-1a apply token timestamp | compact ISO-8601 basic, matching `bench-cpu.md:1` (`20260730T103218Z`) |
| `<APPLY_DATE>` | the same timestamp, date part | `YYYY-MM-DD`, matching the registry Status and CHANGELOG idiom |
| `<PREIMAGE_SHA256>` | `ratification_receipt.py capture`, step 1 above | full hex digest **per amended file**, recorded in the ledger before any edit |
| `<RECEIPT_PATH>` | the operator attestation receipt written at step 3 | repo-relative path under `artifacts/operator/` |
| `<RECEIPT_SHA256>` | SHA-256 of the receipt bytes as written | full hex digest, recorded in the **ledger only** — never in the CHANGELOG (§4c repair 2) |

---

## 6. Verify, do not amend — but the glob is declarative only until the matcher is repaired

**Verify, do not amend.** `coordination/session-bus/human_only_paths.yaml:32-34` pins
`measurement/protocols/*.md` as a **glob**, not an enumeration:

> ```yaml
>   - repo: epyc-root
>     glob: "measurement/protocols/*.md"
>     why: "MEASUREMENT v2 protocol annexes — same trust boundary as the core constitution"
> ```

**As DATA the answer is yes.** A new file at `measurement/protocols/kernel-research.md` is one path
segment below `measurement/protocols/` with a `.md` suffix, so it falls inside the *declared* trust
boundary the moment it exists, with **no edit to `human_only_paths.yaml`**. Because the pin at
`coordination/session-bus/config.yaml:161-164` (`source: human_only_paths.yaml`,
`pin: human_only_paths.sha256`, `on_pin_mismatch: refuse`) is a hash over the **yaml file itself**,
and that file does not change, **this item requires no `.sha256` rewrite either.** Adding a literal
per-annex entry would be a defect, not belt-and-braces: it would establish that each annex needs its
own line, silently converting the glob into decoration.

**As ENFORCEMENT the answer is NO, and this was verified rather than assumed — a blocking defect in
the earlier revision of this section.** `scripts/hooks/check_trust_boundary_edit.sh:89-90` builds
`candidate=$(realpath -m "${root}/${glob}")` and tests `[[ "$TARGET" == "$candidate" ]]`. The
right-hand side is **quoted**, which disables bash pattern matching, and `realpath -m` normalises
without expanding. The candidate therefore resolves to the literal string
`/workspace/measurement/protocols/*.md`, which matches no real path. **Annexes B, Q and G are
agent-writable through `Write`/`Edit` today, and a new Annex K would be too.** The sibling
[`human-only-paths-delta.draft.md`](human-only-paths-delta.draft.md) §3 records the identical finding
as *"V2 — As ENFORCEMENT: NO"*, with the probe table.

**Consequence, stated so it cannot be misread.** Until
`scripts/hooks/check_trust_boundary_edit.sh:90` is changed to an unquoted RHS (or an `fnmatch`), the
new annex's protection at layer 1 is **nil**, exactly as B, Q and G's is today. Layers 2 and 3 hash
the gate list, not the annexes, so they do not observe an annex edit either. **This gap predates
AutoKernel and is not created by it** — but this item must not be signed on the strength of a
statement that the glob protects the new file, because it does not.

**Therefore:** the matcher repair is a named line on the attestation face
(`RATIFICATION_PACKAGE.md` §D, deferred-work register D5), owned by the session-bus / hooks owner, and
it MUST land with a wildcard case in `scripts/hooks/tests/test_trust_boundary_edit.py` — whose `CASES`
list at `:39-56` has no glob entry, which is why this survived. Per project practice the new test must
also assert the **compliant** path still passes.

**Post-apply verification (procedure — a real probe, not a tautology).** Verifying that the glob
*matches* is not the same as verifying the *consumer* enforces it
(`feedback_verify_integrity_not_presence_of_own_edit`), and
`scripts/coordination/session_bus.py validate` only checks a pin over an unchanged file, so it passes
tautologically here and proves nothing about annex coverage. The real probe is to attempt an `Edit` to
the new annex path and assert the hook exits 2. Until the matcher is repaired that probe is **expected
to exit 0**, and the attestation records that result rather than hiding it. The exact commands are in
`RATIFICATION_PACKAGE.md` §F.

---

## 7. Coupling and strike behaviour

The attestation lists each item separately so lines may be struck
(`agents/shared/MEASUREMENT_POLICY.md:77-78`). Two couplings MUST be stated on the attestation face,
because striking one line silently invalidates another:

- **Strike the container ⇒ `P-AK-SEARCH-1` has no home.** It cannot be filed in B, Q or G without the
  §1a consequences. Striking the container therefore strikes the protocol; the correct presentation
  is a single indented sub-line, not two peers.
- **Strike `P-AK-SEARCH-1`, retain the container ⇒ an empty annex.** Permitted and harmless *only if*
  the §4b registry row is dropped with it (§4b status-cell rule) and the CHANGELOG bullet's second
  clause is dropped. The result is a ratified, empty, zero-authority container plus a layout
  paragraph that says four. That is a coherent state — it reserves the letter and the remit without
  granting anything — but it MUST be a deliberate choice, not the residue of a struck line.

- **Strike `P-AK-SEARCH-1` ⇒ the §4d Annex G cross-reference MUST be struck with it**, and vice
  versa. A cross-reference to a protocol that does not exist is as wrong as an unqualified absolute a
  protocol has quietly narrowed. These two are one coupled pair (§4d).

**Recommended presentation:** one line reading *"Create Annex K (container, remit, admission test) +
`MEASUREMENT.md` layout/registry/CHANGELOG deltas"*, with `P-AK-SEARCH-1` as an indented sub-line
beneath it and the §4d Annex G cross-reference as a second indented sub-line coupled to it.

## 8. Apply checklist (this item only) — THE CHECKLIST OF RECORD

This supersedes `Annex-K-kernel-research-and-release.draft.md:199-213`, which is provenance only.

- [ ] **Confirm every bundle item is tracked in git** — `git ls-files artifacts/operator/autokernel-policy-draft/`
      returns all presented drafts plus `RATIFICATION_PACKAGE.md`,
      `RATIFICATION_LEDGER.md` and `apply_ratification.sh`. A working-tree file in a shared clone is
      one `git checkout` from gone and is invisible to any reviewer who clones; signing over a digest
      of bytes no repository holds is the exact failure `MEASUREMENT.md:146-156` was ratified to close.
      Commit pathspec-limited: `git commit -- artifacts/operator/autokernel-policy-draft/`.
- [ ] Run `scripts/operator/ratification_receipt.py capture` and record `<PREIMAGE_SHA256>` per amended
      file in `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md`.
- [ ] Restore `.md` on every occurrence of `measurement/protocols/kernel-research` (§ header note).
- [ ] Create the annex file with the §5 header block and the §2 Remit block.
- [ ] Append the `P-AK-SEARCH-1` normative text from its own draft (or omit, per §7).
- [ ] Apply the §4a layout delta (one of the two stated forms; not strikeable to nothing).
- [ ] Apply the §4b(i) key-line delta and, if `P-AK-SEARCH-1` lands, the §4b(ii) row.
- [ ] Apply the §4c CHANGELOG bullet — naming both superseded sentences, citing the ledger, and
      carrying **no** `<RECEIPT_SHA256>`.
- [ ] Apply the §4d Annex G cross-reference (coupled to `P-AK-SEARCH-1`; strike together).
- [ ] `ratification_receipt.py emit --pre <snapshot>`; record `<RECEIPT_PATH>` and `<RECEIPT_SHA256>`
      in the ledger.
- [ ] Record in `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md`: every semantic
      delta above, every preimage hash, and the explicit supersession statement (§4c) naming
      `MEASUREMENT.md:16-21` and `:45-46`.
- [ ] **Verify, do not amend**, the `human_only_paths.yaml` glob coverage; then run the §6 post-apply
      probe and record its actual exit code, expected to be 0 (unenforced) until the matcher is
      repaired.
- [ ] Confirm every evidence path cited by the bundle resolves in-repo per `MEASUREMENT.md:146-156`.
      Note the validator lives at
      `epyc-inference-research/scripts/validate/check_evidence_durability.py`, **not** at
      `scripts/validate/…` in epyc-root as `MEASUREMENT.md:155` implies (owning handoff `:481-482`);
      name the full path when running it.
- [ ] Pre-validate the full command sequence end-to-end via `apply_ratification.sh` (dry-run default);
      on failure re-present the **same** apply token with updated hashes, never a restarted chain
      (`MEASUREMENT.md:138-145`).

## 9. Open question for the operator

**Does `P-KERNEL-FREEZE-1` become an Annex K protocol, or stay as distributed amendments to Annexes B
and G?**

Not needed now — it belongs to attestation 2 at the earliest
(`handoffs/active/autokernel-research-loop.md:1772`). It is recorded here so the annex's remit is
decided deliberately rather than by accretion, which is the specific way a new container goes wrong.

**The case for distributed amendments (current lean, and my recommendation).** The CPU release rule
already exists in Annex B: `bench-cpu.md:83-88` defines the full CPU kernel-promotion decision rule
with ratio bands (≥0.98 PASS, <0.95 FAIL) and the bounded pooling rule, and `bench-cpu.md:38-44`
already defines candidate release identity. The GPU side is being amended in place anyway, in G, by
the sealed-candidate amendment (§3). Filing `P-KERNEL-FREEZE-1` in K would create a second place to
look for a rule that already has a home, and would fail admission test (3) of §2 for its CPU half.

**The case for Annex K.** Release scope is the **union of backends served by a source tree**
(`handoffs/active/autokernel-research-loop.md:148-150`) — CPU and GPU share one tree and one frozen
branch and cannot be frozen independently (`:140-142`). A gate whose scope is genuinely per-tree may
be impossible to state coherently as two per-annex amendments, and the speech backends have no annex
at all to amend (`:2240`).

**Recommendation.** Defer, with a decision rule rather than a preference: **file
`P-KERNEL-FREEZE-1` in Annex K only if its cross-tree scope clause cannot be stated without
forward-referencing between B and G.** If the release gate decomposes cleanly into "B governs the CPU
cells, G governs the GPU cells, and the freeze transaction sequences them", it is distributed
amendments. If the freeze rule must reason about the union of backends *as a single object* — which
the shared-tree constraint makes likely — it is an Annex K protocol, and it passes all three
admission tests in §2 on that basis. The decision is made when the release program is drafted at
AK5/AK6, and recorded in the decision log at `handoffs/active/autokernel-research-loop.md` §17.

Either way, §2's admission test — not precedent, not convenience — is the instrument that decides it.

---

## 10. Residual dependencies

Four. None is a blank; each is either a coupling to an item on the *same* attestation, or a disclosed
gap the operator signs over knowingly.

1. **The annex's body depends on the sibling `P-AK-SEARCH-1` draft existing at apply time.** A
   container is not self-sufficient by nature: a ratified annex file with a header and a remit and no
   protocol is legal (§7) but purposeless. This cannot be expressed away as a contract because the
   dependency is on *authored normative text*, not on a run-time value. **Mitigation:** both items
   ride the same attestation, and §7 states both strike directions and their consequences on the
   attestation face. **Not a blocker:** the sibling draft is an AK0 deliverable authored in parallel,
   not an AK1–AK6 implementation artifact.

2. **Five apply-time literals (§5) are supplied by the apply, not by this draft** — `<APPLY_TS>`,
   `<APPLY_DATE>`, `<PREIMAGE_SHA256>`, `<RECEIPT_PATH>`, `<RECEIPT_SHA256>`. Listed for completeness
   and explicitly **not** deferred bindings: each is produced by `ratification_receipt.py` at apply
   time in the write order stated in §5, and has no meaningful value before then. Writing any of them
   now would be fabricating a hash or a date — an evidence hash over an artifact that does not exist
   proves nothing, which is precisely the defect `MEASUREMENT.md:146-156` was ratified to close.

3. **There is no AK6 bundle assembler, and attestation 1a does not need one.** The assembler the
   owning handoff contemplates at `:1797-1801` is an AK6 deliverable (0/9 checkboxes, LOC band 1–2k,
   `:1719-1720`). This attestation is assembled with `scripts/operator/ratification_receipt.py` plus a
   hand-written `RATIFICATION_LEDGER.md`, driven by `apply_ratification.sh` in this directory. Stated
   here rather than implied, so the operator is not waiting for a machine that has not been built.

4. **Layer-1 hook enforcement of `measurement/protocols/*.md` is inoperative (§6).** The new annex
   lands under a boundary that is declared and audited but not enforced against agent `Write`/`Edit`,
   in exactly the way B, Q and G already are not. The repair is code, owned by the session-bus / hooks
   owner, and is registered as deferred item D5. The operator signs this item knowing that its stated
   protection rests on layer-3 audit and on the human-only convention, not on the hook.

**Deliberately absent:** there are no threshold, noise-floor, sample-count, or hash bindings in this
document. A container has none — every such binding belongs to `P-AK-SEARCH-1`, where it is expressed
as a procedure that derives the value per campaign rather than as a literal, per
`MEASUREMENT.md:116-118` (protocols are append-or-version and never silently edited, so a guessed
literal is expensive to walk back).
