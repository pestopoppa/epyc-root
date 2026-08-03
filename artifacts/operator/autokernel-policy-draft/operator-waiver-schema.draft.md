<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Staged for operator review per
     artifacts/operator/autokernel-policy-draft/README.md (attestation 2).
     Target: measurement/protocols/kernel-research (Annex K), appended as a new block —
     see §7 for why the waiver instrument cannot live in a single backend annex.
     Author: AutoKernel design pass, 2026-08-03. -->

# DRAFT — `epyc.autokernel.operator_waiver.v1`

**Status:** COMPLETE DRAFT, **NOT PRESENTABLE UNTIL ATTESTATION 2** (revised 2026-08-03 after
adversarial review). Every binding is a contract or a procedure and there are no unfilled tokens — but
three of its dependencies resolve only after AK1/AK5, and one (the release verdict's protocol id)
requires an operator placement decision that has not been taken. Those are enumerated in §10, and the
item is registered in the deferred-work register at `RATIFICATION_PACKAGE.md` §D as **D7**.

An earlier revision claimed *"no binding references an artifact that does not yet exist"*. That was
false in six places, and the draft's own §10.1 contradicted it (*"Until it is chosen, §4's verdict
clause has no clause to cite"*). The corrections are marked inline; none required inventing a value.

**Creates:** one schema and its verification contract. It creates no new authority.
**Generalises:** `epyc.cpu_prefill_v8.operator_waiver.v1`
(`artifacts/operator/waive_q8_cpu_prefill_v8_20260725.json`), the single waiver in the project's
history, which shipped v8.
**Presented in:** attestation 2 ("release authorization"), after AK5
(`artifacts/operator/autokernel-policy-draft/README.md:41-49`).
**Owning handoff:** `handoffs/active/autokernel-research-loop.md` §10.4 (`:1456-1474`), §7.6
(`:1012-1018`), §14 AK0 (`:1882-1884`).

---

## 1. The waiver already exists in the constitution — it just has no schema

Annex B's CPU kernel-promotion decision rule already ends on this sentence:

> "A failed production-recipe cell blocks pending repair or **an explicit operator waiver**."
> — `measurement/protocols/bench-cpu.md:96`

That clause names an instrument the constitution never defines. The v8 freeze supplied one ad hoc:
a JSON blob, hash-pinned at a named commit by `artifacts/operator/freeze_v8_production_20260725.sh:214`,
asserted by predicate at `:248-252`, and cross-checked against the evidence matrix at `:260-268`.
This draft turns that one-off into a named object with a verification contract, and nothing more.

**The boundary that must not move.** The constitution is explicit that a waiver is not the remedy for
a bad gate:

> "A gate that blocks on a non-production arm is **defective and is repaired, not waived**."
> — `MEASUREMENT.md:125-126`
>
> *(Span corrected. `:126-127` is the adjacent `llama-bench`/spec-dec RECORDED-not-blocking clause —
> a different rule. The same wrong span appeared inside the verbatim-append text at §4 and is
> corrected there too.)*

A waiver is therefore an instrument for evidence that **cannot be obtained or cannot be validly
taken**, not for evidence that is inconvenient. The v8 case is the archetype: the Qwen3.6 Q8 workload
sustains ~50-55 target core-equivalents and structurally cannot satisfy the ratified 72-core
eligibility floor at `bench-cpu.md:62-63`, so the measurement was never eligible to exist
(`waive_q8_cpu_prefill_v8_20260725.json:21`).

**Why a binary gate is not an option.** v8's own machine verdict was `promotion_decision: false`,
preserved verbatim and reinterpreted rather than overwritten
(`artifacts/operator/ratify_v8_final_freeze_20260725.json:188-189`). Handoff §10.4 (`:1458`) states
the consequence plainly: a binary PASS/FAIL release gate would have blocked v8. T3 therefore emits
`PASS` / `FAIL` / `PASS_WITH_WAIVER` (`handoffs/active/autokernel-research-loop.md:1267`, `:1469`).

## 2. Design rule: ratify the contract, never the value

Two kinds of number appear near this schema and they are not the same kind:

- **Protocol constants** — thresholds, floors, noise levels. This draft contains **none**. Every one
  it would otherwise need is derived by an existing rule that already lives in the constitution and is
  cited rather than restated (`bench-cpu.md:83-96` for the CPU decision bands, `bench-cpu.md:21-22`
  for reps, `MEASUREMENT.md:103-112` for the noise table). Protocols are append-or-version and never
  silently edited (`MEASUREMENT.md:116-118`), so a guessed constant here would be expensive to walk
  back.
- **Instance values** — the model hash, the cell count, the campaign id in one signed waiver. These
  are *supplied at authorship by the human who signs the object*. They are not calibration and the
  schema is entitled to require them.

Everywhere a value would otherwise be invented, the field is specified as *"the value recorded in
&lt;named artifact&gt;"* — a contract the implementation must satisfy, resolvable at run time.

## 3. The schema, field by field

Required unless marked optional. `sha256` fields are lowercase hex SHA-256 of exact file bytes.

### 3.1 Object identity and type predicate

| Field | Purpose | v8 precedent / why the generalisation needs it |
|---|---|---|
| `schema` | Constant `"epyc.autokernel.operator_waiver.v1"`. The type predicate a gate asserts. | v8 used `"epyc.cpu_prefill_v8.operator_waiver.v1"` — the **campaign name was inside the schema id**, so the freeze predicate at `freeze_v8_production_20260725.sh:248` identified one specific waiver by its type. That does not generalise: a stable schema cannot name a campaign. Identity moves to `waiver_id` + the pinned hash (§5.2 gives the replacement predicate form). |
| `waiver_id` | Stable, unique identifier; how the release receipt, the suppressed-claim rows, and the preserved obligations all refer to this object. | v8 had none — the object was identified only by file path and SHA-256. A bundle carrying two waivers could not have referred to either. |
| `label` | Human-readable display token, e.g. `WAIVE-Q8`. **Display only.** Verifiers MUST NOT branch on it. | v8's `decision: "WAIVE-Q8"` mixed the type predicate with a human label. |
| `decision` | Constant `"WAIVE"`. One admissible value. | Deliberate narrowing. If the field could carry another verdict, this object would become a general-purpose operator-verdict channel into an automated gate — the exact authority creep §6 forbids. |
| `protocol_changed` | Constant `false`, asserted by the verifier. | v8 carried it as data. In v1 it is a **type invariant**: a waiver that changed a protocol would be an amendment, and amendments are human-only, PR-reviewed, and append to the owning annex (`MEASUREMENT.md:116-118`) — never a JSON file under `artifacts/`. A `true` value is a malformed object, not a stronger waiver. |
| `related_amendment` *(optional)* | `{path, sha256}` of a ratified annex amendment authored alongside this waiver. A pointer, never a substitute. | New. Lets the record show "the protocol was also amended, separately and properly" without the waiver claiming to have done it. |

### 3.2 Ratification and authorship

| Field | Purpose | v8 precedent / why new |
|---|---|---|
| `ratified_at` | RFC 3339 UTC instant of the operator signature. | v8: `"2026-07-25T14:04:16Z"`. |
| `ratification_receipt` | `{path, sha256}` of the operator attestation carrying this waiver into force, per consolidated apply-time ratification (`MEASUREMENT.md:138-145`). | New. v8's binding ran the other way only — the freeze script pinned the waiver's hash (`:214`) and the ratification recorded it under `evidence_sha256.waive_q8` (`ratify_v8_final_freeze_20260725.json:41`). Making the pointer reciprocal means neither artifact can be read without discovering the other. |

There is no in-band signature field. Authorship is established procedurally — see §4 (*Authorship
and storage*) and §10 item 3.

### 3.3 Bindings

| Field | Purpose | v8 precedent / why new |
|---|---|---|
| `binds.campaign_id` | The `campaign_id` of the owning campaign manifest (`epyc.autokernel.campaign.v2`, handoff `:814-815`). | **New — required by §10.4 (`:1468`).** v8 was campaign-scoped only in prose: `q8_claim: "none; campaign-scoped WAIVE-Q8 remains binding …"` (`ratify_v8_final_freeze_20260725.json:190`). Prose is not a predicate. |
| `binds.campaign_manifest_sha256` | The manifest's hash at authorship. Its change is an invalidation event (§4, *Invalidation conditions*). | New. Without it, "campaign-scoped" cannot be checked against a mutated campaign. |
| `binds.source_tree` | The source tree the waiver applies to. Value = the tree named in the campaign manifest's `source_tree`. | **New — required by the task and by §1.5 (`:129-153`): freezes are per tree.** |
| `binds.backends[]` | The backend adapters whose cells are waived — a subset of the backends the tree serves. | **New.** `llama.cpp` serves both `cpu` and `gpu` from one frozen branch (`:135-136`). A waiver that did not name its backends would be ambiguous across the two binaries of one tree. |
| `binds.candidate` | `{branch, commit, seal_sha256?}`. `seal_sha256` is the sealed-release-candidate seal hash defined by the sealed-candidate amendment draft, when the waiver is authored after sealing; `null` when authored at plan time. | v8 carried `candidate_head`. The optional seal permits a waiver authored *before* the seal — which is the v8 shape, since the Q8 ineligibility was structurally known in advance. Identity fields beyond these are **not** restated: `bench-cpu.md:38-44` already defines candidate release identity, and this schema adopts it by reference. |
| `binds.incumbent` | `{branch, commit, version}` of the production anchor the waived comparison would have been against. | v8 carried `production_head`. Kept because a ratio without its denominator is meaningless, and because anchor movement is an invalidation event (`handoffs/active/autokernel-research-loop.md:1634`, `ANCHOR_MOVED`). |
| `binds.instrument.evaluator_bundle_sha256_at_authorship` | The evaluator/runner bundle hash **as recorded in the T3 verdict bundle of the run the waiver was authored against** (owning handoff §7.6 `:1014` lists the T3 verdict bundle as a release-package member). | Generalises v8's `runner_sha256_before_waiver_implementation`. Its purpose is the load-bearing one: it proves the exclusion was a decision *about evidence*, not a change to the measuring device. **Corrected after review:** an earlier revision sourced this from *"the campaign manifest"*, but `epyc.autokernel.campaign.v2` (handoff `:813-851`) has no evaluator-bundle field — it carries `scope.derived_role_manifest_sha256` and `policy_ref.policy_bundle_sha256` and nothing else hash-shaped. Every waiver would have been unauthorable or would have carried a fabricated value. Re-pointed at an artifact the design does define. If AK1 instead adds `instrument.evaluator_bundle_sha256` to the campaign manifest, this field may source from there; that schema delta is §10 item 7. |
| `binds.instrument.recipe_ids[]` | The codified recipe identifiers of the waived cells, as assigned by the recipe constructor. | New. `bench-cpu.md:8-9` forbids hand-typed commands; naming the recipe makes the waived cell reproducible by anyone auditing later. |

### 3.4 Scope — enumeration, never predicate

| Field | Purpose | v8 precedent / why new |
|---|---|---|
| `scope.addressing` | Constant `"release_plan_cell_id"`. Declares that cells are addressed by the identifier the release plan assigns (§10.1, `:1400-1409`), joined by **exact string equality**. | New. v8 addressed cells by ad-hoc strings (`"qwen36_q8-pp2048-iqk1"`) that happened to match the runner's naming. Naming the join key makes the match mechanical rather than conventional. |
| `scope.release_plan_sha256` | The plan the cell ids are drawn from. | New. A cell id without its plan is not an address. |
| `scope.waived_cells[]` | One entry per waived cell: `{cell_id, protocol_id, backend, phase, model:{id, path, sha256, durability_class}, recipe_id, arm_runs, observed_status}`. | Generalises `excluded_pairs` + `excluded_model` + `excluded_model_path`. Three additions: **(a) per-cell `protocol_id`** — v8 carried one scalar `protocol: "P-BENCH-PREFILL-1"` while its two excluded pairs are a `pp2048` cell and a `tg128` cell, which the registry assigns to P-BENCH-PREFILL-1 and P-BENCH-1 respectively (`MEASUREMENT.md:51-52`), and which `bench-cpu.md:87-88` explicitly pairs inside one IQ-utility rule. A scalar cannot say which rule each waived cell escaped. **(b) `model.sha256` + `durability_class`** — v8 recorded a path only; `bench-cpu.md:41-44` requires model path/size/SHA256, and a multi-GiB GGUF is `hash-and-provenance-only` evidence under `MEASUREMENT.md:151-155`. **(c) `observed_status`** ∈ `FAIL` / `INELIGIBLE` / `UNOBTAINABLE` — what actually happened, so the receipt can distinguish "measured and lost" from "never validly measurable". |
| `scope.waived_cell_count`, `scope.waived_arm_runs` | Counts, asserted against the enumeration. | v8: `excluded_arm_runs: 4`. |
| `scope.residual` | `{required_cell_count, required_arm_runs, manifest_sha256}` — the evidence that MUST still be present and passing. | Generalises `remaining_matched_pairs: 14` / `remaining_arm_runs: 28`, which the freeze script asserted *both* in the waiver (`:250`) and in the matrix (`:263`, `(.pair_results | length) == 14`). This reciprocal count is the anti-swallow control: it makes the waiver state its own negative space, so a waiver that quietly grew would fail its own residual assertion. |

**Enumeration, never predicate.** Waived cells are listed by explicit address. A pattern, glob,
regex, or predicate is not admissible, because a predicate is evaluated later against a matrix that
may have changed, and can silently widen. This is the single most important scope rule in the schema.

### 3.5 Reason

| Field | Purpose |
|---|---|
| `reason.text` | The human explanation. v8's is a model: it names the physical quantity (~50-55 core-equivalents) and the rule it cannot meet (the 72-core floor). |
| `reason.class` | A short slug for reporting and aggregation only. **The verifier MUST NOT branch on it.** Left deliberately open rather than a closed enum: a closed vocabulary inside an append-or-version protocol would require an amendment every time a new situation arose, and a vocabulary the evaluator branches on is a control surface. |
| `reason.refs[]` | `file:line` citations for every rule the cell cannot satisfy. v8's reason cites the eligibility floor in prose; v1 requires the pointer (`measurement/protocols/bench-cpu.md:60-66`). |

### 3.6 Consequences — split into three kinds

v8's `consequences[]` is a five-item prose list that mixes three different kinds of statement. v1
separates them so each becomes checkable:

| Field | Purpose | From v8's list |
|---|---|---|
| `forfeited_claims[]` | `{claim_text, protocol_id, cells[], suppression_scope}` where `suppression_scope` ∈ `campaign` / `release`. Copied verbatim into the T3 verdict bundle (§4, *Claim suppression*). **Two corrections after review.** (a) `claim_id` is **removed**: no claim-identifier space exists anywhere — `claim_id` appears in no annex, in `MEASUREMENT.md`, or in the owning handoff, and `MEASUREMENT.md:13` defines a claim as an unkeyed tuple `(metric, protocol-id, n/reps, date, host-attestation ref)`. The join key is `claim_text` **verbatim**, which §4 already makes load-bearing, plus `protocol_id` + `cells[]`. (b) `permanent` is **removed** from the enum: a permanent suppression authored in a JSON file under `artifacts/` would be a fourth retroactivity verb, instance-configurable, alongside the three constitutional ones at `MEASUREMENT.md:174-186`. The cap is `release`, which is already broader than v8's actual `campaign` scope; anything standing goes through an annex amendment, which is the instrument the constitution already provides. | Item 1: *"No v8 Q8 non-regression claim may be made from this campaign."* |
| `preserved_obligations[]` | `{text, cells[], must_pass: true}` — what the waiver explicitly does **not** touch, addressed by cell id so the verifier asserts those cells are present and PASSED. | Items 2-4: the 72-core floor unchanged for every remaining arm; the Gemma Q4 non-IQ B4 pairs still mandatory; all retained IQ B3 pairs still mandatory. Prose in v8; predicates in v1. |
| *(no field)* | Item 5 — *"Pre-waiver artifacts remain ineligible and cannot be retro-certified"* — is **promoted out of the instance into standing protocol text** (§4, *Prospective*). A standing rule restated per instance is a rule that can be forgotten by omission. | Item 5. |

### 3.7 Validity — expiry, invalidation, self-retirement

| Field | Purpose |
|---|---|
| `validity.use_scope` | Exactly one of `single_seal` / `single_campaign`. Declares how many evaluations this waiver may serve. Default `single_seal`, consistent with the sibling amendment's single-use seals (`P-GPU-1-sealed-candidate-amendment.draft.md` §7 open question 2, whose recommendation is *keep it strict*). **`until_next_freeze_of_source_tree` is removed after review**: freeze scope is *"the union of backends served by the tree"* (owning handoff §1.5 `:150-153`), so one such waiver would reach every backend of `llama.cpp` for months — a standing authority §6 of this document explicitly claims the schema cannot express. Both statements could not be true; the value is dropped rather than the claim. Note the cited default is a **recommendation in an open-questions block**, not a settled rule, and the sealed-candidate amendment is unratified — §10 item 6 records that co-dependency. |
| `validity.expires_at` *(optional)* | Absolute RFC 3339 instant after which the waiver is inactive. Optional because the derived invalidation conditions below are the real expiry mechanism; a wall-clock date is a convenience, not the contract. |

**The invalidation set is normative and is NOT instance-configurable.** A waiver that attempts to
enumerate, select, or narrow its own invalidation conditions is malformed. If the instance could
choose, an operator could sign away `ANCHOR_MOVED` and the object would outlive its own denominator.

### 3.8 Skeleton

Placeholders are written as contracts, not as example values, because no instance exists yet.

```json
{
  "schema": "epyc.autokernel.operator_waiver.v1",
  "waiver_id": "<unique id; convention: akw-<source_tree>-<label-slug>-<ratified_at>>",
  "label": "<display token>",
  "decision": "WAIVE",
  "protocol_changed": false,
  "related_amendment": null,
  "ratified_at": "<RFC3339 UTC instant of operator signature>",
  "ratification_receipt": {"path": "<in-repo path>", "sha256": "<hash of that file's bytes>"},
  "binds": {
    "campaign_id": "<campaign manifest campaign_id>",
    "campaign_manifest_sha256": "<hash of the manifest at authorship>",
    "source_tree": "<source_tree named in that manifest>",
    "backends": ["<backend adapter ids affected>"],
    "candidate": {"branch": "<...>", "commit": "<...>", "seal_sha256": "<seal hash, or null if pre-seal>"},
    "incumbent": {"branch": "<...>", "commit": "<...>", "version": "<...>"},
    "instrument": {
      "evaluator_bundle_sha256_at_authorship": "<evaluator bundle hash recorded in the campaign manifest>",
      "recipe_ids": ["<recipe ids of the waived cells>"]
    }
  },
  "scope": {
    "addressing": "release_plan_cell_id",
    "release_plan_sha256": "<hash of the release plan the cell ids come from>",
    "waived_cells": [
      {
        "cell_id": "<id assigned by that plan>",
        "protocol_id": "<protocol governing THIS cell>",
        "backend": "<...>",
        "phase": "<prefill|decode|capacity>",
        "model": {"id": "<...>", "path": "<...>", "sha256": "<...>",
                  "durability_class": "<carried-in-git|durable-untracked|hash-and-provenance-only>"},
        "recipe_id": "<...>",
        "arm_runs": 0,
        "observed_status": "<FAIL|INELIGIBLE|UNOBTAINABLE>"
      }
    ],
    "waived_cell_count": 0,
    "waived_arm_runs": 0,
    "residual": {"required_cell_count": 0, "required_arm_runs": 0,
                 "manifest_sha256": "<hash of the residual cell manifest>"}
  },
  "reason": {"class": "<reporting slug>", "text": "<...>", "refs": ["<file:line>"]},
  "forfeited_claims": [
    {"claim_text": "<the claim that MUST NOT be made>",
     "protocol_id": "<...>", "cells": ["<cell_id>"], "suppression_scope": "<campaign|release>"}
  ],
  "preserved_obligations": [
    {"text": "<what is explicitly NOT waived>", "cells": ["<cell_id>"], "must_pass": true}
  ],
  "validity": {"use_scope": "<single_seal|single_campaign>",
               "expires_at": null}
}
```

**Three enums were narrowed after review, each because the schema permitted authoring an instance the
normative text forbids.** An open control surface inside a subtractive-authority object is a defect,
not flexibility:

- `phase` — was `<prefill|decode|quality|stability|capacity|...>`. `quality` and `stability` are two of
  the classes §4 declares **non-waivable**, so the schema admitted exactly the instance §4 bars; and
  the trailing `...` made the enum open-ended. Narrowed to the phases whose governing rule is a
  throughput, capacity or evidence-eligibility rule, with no open tail.
- `suppression_scope` — `permanent` removed (§3.6).
- `use_scope` — `until_next_freeze_of_source_tree` removed (§3.7).

**`binds.candidate.seal_sha256: null` — the matching rule, stated rather than left to inference.**
ACTIVE condition 3 requires `binds.candidate` to equal the bundle's values, and a sealed bundle has a
non-null seal. `null` is therefore defined as **"authored pre-seal; matches the first seal produced
for this `{campaign_id, branch, commit}` and no other"** — the seal hash is bound at first
verification and recorded in the bundle ledger, after which the waiver behaves as though it had
carried that hash all along. It is **not** a wildcard: a re-seal produces a different seal, which does
not match, and the waiver is INACTIVE until re-signed. Without this rule, either every pre-seal waiver
is permanently inactive (killing the v8 shape this schema is built to express) or `null` floats across
re-seals, which is the standing authority §6 disclaims.

---

## 4. Normative text (proposed)

> ### K-WAIVER — Operator waiver of a release-gate cell (AMENDMENT, ratified `<APPLY_DATE>`)
>
> **Scope.** `epyc.autokernel.operator_waiver.v1` is the ONLY object by which a human may remove an
> enumerated cell from the required set of a kernel-freeze evaluation, for one source tree. It governs
> waiver authorship, verification, and the suppression of the claims a waived cell would otherwise
> have supported.
>
> **Per-annex reach — this clause grants nothing an annex has not granted.** Annex B already provides
> the instrument in principle: *"A failed production-recipe cell blocks pending repair or an explicit
> operator waiver"* (`measurement/protocols/bench-cpu.md:96`). This clause supplies the object that
> sentence names, and a cross-reference is appended to `bench-cpu.md:96` in the same apply recording
> that the instrument is now defined here. **Annex G contains no waiver clause at all**, and its
> kernel-provenance rule (`gpu-cross-device.md:16-21`) is stated absolutely with no operator escape.
> A waiver therefore reaches a GPU cell **only if** Annex G receives a corresponding clause in the
> same signature. Absent that, `binds.backends` is restricted to backends whose owning annex grants a
> waiver, and a waiver enumerating a GPU cell is **malformed**. *(Corrected after review: an earlier
> revision asserted the object was "cross-backend by construction", sourcing authority over GPU and
> speech backends entirely from one sentence inside P-BENCH-PREFILL-1's CPU decision rule in Annex B.
> An instrument may be cross-backend in shape without being cross-backend in authority.)*
>
> **Authority — subtractive only.** A waiver MAY remove enumerated cells from the required set. It
> MUST NOT change what any cell must satisfy: not a threshold, a ratio band, a rep count, an
> eligibility floor, a decision rule, an objective weighting, or a protocol's text. A waiver that
> would alter a rule is an amendment and MUST go through the annex (`MEASUREMENT.md:116-118`).
>
> **What a waiver does NOT authorize.** It MUST NOT authorize any of the **five** enumerated human-only
> writes — *"era-registry rows, **this constitution and its annexes**, AutoPilot baseline-state
> applies, production freezes/cutovers, host reboots"* (`MEASUREMENT.md:140-142`). *(An earlier
> revision said "all four", silently omitting the constitution itself — the member most relevant to an
> object that could otherwise be read as amending a protocol.)* It MUST NOT convert an observation
> into a claim, retro-certify any artifact, or upgrade evidence taken under a superseded instrument.
> It MUST NOT authorize deletion of any evidence (`MEASUREMENT.md:174-175`). It MUST NOT be used where
> the failing cell is a non-production arm — that gate is defective and is repaired, not waived
> (`MEASUREMENT.md:125-126`).
>
> **Non-waivable classes.** A waiver's cells MUST be cells whose governing rule is a throughput,
> capacity, or evidence-eligibility rule. The following are NOT waivable by this object, quoting
> `bench-cpu.md:89-90` in full — *"model-load, correctness/coherence, numerical-safety, attribution,
> or cleanup failure = FAIL regardless of throughput"* — plus quality-regression, integrity,
> determinism-class, stability, linkage, and identity failures. **`model-load` and `attribution` were
> missing from an earlier revision of this list**, and the positive admission test admitted them: a
> cell that fails on model-load is still governed by P-BENCH-PREFILL-1, a throughput protocol, so the
> object would have granted waiver authority over two failure classes the constitution makes
> unconditional. Correctness is lexicographically first
> (`handoffs/active/autokernel-research-loop.md:518-519`). A `REQUIRES_HUMAN_CODE_REVIEW` marking
> (`:1484-1489`) is likewise not waivable here. The absence of an instrument for those classes is
> deliberate; creating one would require its own ratification.
>
> **`observed_status: FAIL` is admissible only where the owning annex grants it.**
> `bench-cpu.md:96` permits waiving a *failed production-recipe CPU cell*, and that is the only place
> the constitution grants a waiver over evidence that was validly taken and lost. For a cell whose
> `protocol_id` is not a CPU bench protocol, only `INELIGIBLE` and `UNOBTAINABLE` are admissible — a
> waiver is *"an instrument for evidence that cannot be obtained or cannot be validly taken, not for
> evidence that is inconvenient"* (§1), and an earlier revision extended `FAIL`-waivability to every
> backend and phase in a way §1's own boundary paragraph did not support.
>
> **Authorship and storage.** A waiver is written by a human and by no other agent. It MUST live at a
> path matched by an entry in `coordination/session-bus/human_only_paths.yaml` — an entry added in the
> **same apply that ratifies this clause**, over a **directory created in that same apply with a
> README**, so the entry names a path that exists and the file's own header promise of *"real paths,
> verified to exist"* (`:21-24`) is kept. *(This resolves the conflict a review found between this
> clause and `human-only-paths-delta.draft.md:159-165`, which refuses to add a waiver entry today on
> exactly that header's authority. Both are right: the entry must not be added while the directory is
> empty and unratified, and it must be added when the clause lands. It lands with the clause, on
> attestation 2, and the directory is created first.)* — so that the PreToolUse refusal, the `.sha256`
> pin, and the coordinator audit all apply to it
> (`coordination/session-bus/human_only_paths.yaml:1-18`). The evaluator, the release packager, and
> any autonomous process MUST NOT author, template, pre-fill, edit, move, or delete a waiver; the
> packager is already forbidden to "waive failed evidence"
> (`handoffs/active/autokernel-research-loop.md:1519-1521`). An evaluator MAY report which cells
> failed, with their addresses — that report is a failure record and MUST NOT be shaped as an
> instance of this schema.
>
> **Every exclusion has exactly one provenance.** A cell may be absent from the required set for
> exactly one of **three** reasons, and the reason MUST be recorded: (a) mechanically derived scope
> narrowing with its derivation receipt (affected-surface manifest or backend-unchanged transfer
> receipt); (b) an active waiver; or (c) an **operator-declared plan-level exclusion**, recorded on
> the plan with a reason and an operator identity, for a model or surface deliberately outside the
> release's scope. There is no fourth channel. An exclusion appearing in a release plan with none of
> the three is a hard failure of the plan, not a silent narrowing.
>
> *(Channel (c) was added after review. An earlier two-channel formulation made this document's own
> worked example a hard plan failure: the v8 matrix carries `.plan.explicit_exclusion |
> index("qwen3.5-122b") != null` (`freeze_v8_production_20260725.sh:266`) with no waiver object behind
> it — an operator-declared scope exclusion, which is a real and legitimate third thing. Under the
> two-channel rule the AK5 dry-run this document nominates as its own acceptance test would have
> failed for a reason the document created, while §5 simultaneously claimed "Nothing in the v8 record
> is inexpressible in v1". Channel (c) makes that true, and it makes the distinction visible in the
> receipt instead of discoverable only by reading a `jq` predicate.)*
>
> #### A waiver is ACTIVE for an evaluation only when ALL of:
>
> 1. it resolves at the path and SHA-256 pinned in the release bundle, **as a blob at a named commit**,
>    and the working-tree copy matches that blob (the `freeze_v8_production_20260725.sh:214,225`
>    pattern — an untracked file is indistinguishable from a committed one on the filesystem);
> 2. `schema`, `decision == "WAIVE"`, and `protocol_changed == false` hold;
> 3. `binds.campaign_id`, `binds.campaign_manifest_sha256`, `binds.source_tree`, `binds.backends`,
>    `binds.candidate`, and `binds.incumbent` all equal the corresponding values in the bundle under
>    evaluation;
> 4. `binds.instrument.evaluator_bundle_sha256_at_authorship` equals the evaluator bundle hash of the
>    run being judged;
> 5. every `scope.waived_cells[].cell_id` resolves in the release plan named by
>    `scope.release_plan_sha256`, and the enumerated counts equal the enumeration;
> 6. the evidence matrix contains exactly the residual set `scope.residual` describes, and every
>    `preserved_obligations[].cells` entry is present and PASSED;
> 7. the evidence matrix names this waiver's SHA-256 (`freeze_v8_production_20260725.sh:265` — the
>    binding is reciprocal, bundle→waiver and matrix→waiver, so neither can be swapped alone);
> 8. **no waived cell is cited as evidence supporting a claim** in the verdict bundle's claim set.
>    *(Corrected after review, twice over. The citation was swapped with condition 7's — the
>    waiver-hash binding is at `:265` and the model-absence assertion at `:264`. And the test itself
>    was a **presence** test — v8 asserted the waived model absent from the arm runs entirely
>    (`freeze_v8_production_20260725.sh:264`) — which is mutually exclusive with self-retirement
>    below: a cell that never ran produces no result, so the reopen predicate could never be
>    evaluated and the headline reopen mechanism was dead text. **Waived cells ARE executed and
>    recorded, labelled `WAIVED`**; what condition 8 forbids is *citing* one as supporting evidence.
>    The v8 shape is the weaker historical form, cited as precedent, not as the rule.)*
> 9. `validity.use_scope` is not already exhausted by an earlier sealed bundle for this source tree,
>    **evaluated as follows**: a `single_campaign` waiver does not consult the bundle ledger and this
>    condition is satisfied by `binds.campaign_id` matching; a `single_seal` waiver consults the
>    append-only release-bundle ledger and, **where that ledger does not exist, FAILS CLOSED and the
>    waiver is INACTIVE**. *(Corrected after review: an earlier revision made every waiver consult a
>    ledger that is an AK1 deliverable, and separately required fail-closed behaviour when it is
>    missing — which made every waiver permanently INACTIVE, made `PASS_WITH_WAIVER` unreachable, and
>    made §8's own required AK5 dry-run outcome unsatisfiable. The `single_campaign` carve-out gives
>    the dry-run a reachable path without weakening `single_seal`.)* `validity.expires_at`, if set,
>    has not passed; and
> 10. no invalidation condition below has occurred.
>
> Failure of ANY of these makes the waiver INACTIVE. An inactive waiver does not soften anything: its
> cells revert to gating, and the verdict is computed without it.
>
> **Invalidation conditions (normative, not instance-configurable).** A waiver becomes INACTIVE when
> any of the following occurs between authorship and verification: the incumbent anchor identity
> changes (`ANCHOR_MOVED`); the campaign manifest hash changes; the evaluator bundle hash differs from
> the authorship hash; the annex text governing any waived cell's `protocol_id` is amended; an
> instrument-era boundary is crossed for any affected backend (`MEASUREMENT.md:188-204`); a freeze of
> this source tree completes; or the declared use scope is exhausted.
>
> **Self-retirement (the reopen predicate).** A waiver is INACTIVE for any cell that, on the run being
> judged, satisfies its governing protocol's decision or eligibility rule. A waiver MUST NEVER convert
> a passing cell into a waived one. This makes the reopen predicate derived rather than declared: when
> the condition that made the cell unmeasurable ceases to hold, the cell simply passes, the waiver
> stops applying to it, and the receipt reports the waiver as `SELF_RETIRED` for that cell so the
> operator can retire the object.
>
> #### Verification contract — the evaluator checks, it never judges
>
> The evaluator MUST perform every check above mechanically. It MUST NOT assess whether the reason is
> good, whether the forfeited claims are adequate compensation, whether the scope is proportionate, or
> whether a similar cell "should" also be covered. It MUST NOT infer, extend, interpolate, or
> generalize scope by any means, including similarity, pattern, or model family. It MUST NOT branch on
> `reason.class` or `label`. A cell not enumerated is not waived.
>
> #### Verdict
>
> T3 emits exactly one of `PASS`, `FAIL`, `PASS_WITH_WAIVER`. `PASS_WITH_WAIVER` is emitted only when
> at least one active waiver applied AND every remaining required cell passed. A waiver never rescues
> an un-waived failure: any failing cell outside every active waiver's enumeration yields `FAIL`. The
> waiver object itself MUST NOT contain a verdict field — the verdict is computed, never asserted.
>
> Consumers MUST render the three states distinctly. Collapsing `PASS_WITH_WAIVER` into `PASS`, or
> into a boolean, is a defect in the consumer. The precedent is `promotion_decision: false` preserved
> verbatim beside its interpretation rather than overwritten
> (`artifacts/operator/ratify_v8_final_freeze_20260725.json:188-189`).
>
> #### Claim suppression — positive, never silent
>
> **The artifact these rules bind is the T3 verdict bundle**, which the release package already
> carries (owning handoff §7.6 `:1014`), and whose **claim set** is defined for this purpose as *the
> enumerated set of claim texts the bundle asserts, each with its `protocol_id` and its contributing
> `cell_id`s*. *(Corrected after review: an earlier revision hung five normative MUSTs on "the release
> receipt", an artifact with no schema, no owner and no defined claim set anywhere in the constitution,
> the annexes or the owning handoff — which made clause 2 unverifiable by construction. Binding them
> to the T3 verdict bundle, and defining its claim set in one sentence, makes every clause checkable.)*
>
> A waived cell suppresses exactly the claims its waiver names, and the suppression is **stated, not
> implied**. Absence of a claim is not suppression: a later reader cannot distinguish a claim that was
> never made from one that was forfeited, so the bundle MUST say which.
>
> 1. **Per-cell status.** The T3 verdict bundle MUST carry, for every waived cell, a status token
>    `WAIVED` — distinct from `PASS` and from `FAIL` — together with `waiver_id`, the waiver SHA-256,
>    and the cell's `observed_status`. A waived cell MUST NOT be omitted; omission is
>    indistinguishable from a cell that was never planned.
> 2. **Suppressed-claim rows.** For each `forfeited_claims[]` entry the bundle MUST carry a row whose
>    text is the waiver's `claim_text` **verbatim**, with its `suppression_scope`. The bundle's claim
>    set MUST NOT contain any claim that a suppressed row names, matched on `claim_text` verbatim plus
>    `protocol_id`. The precedent is v8's
>    `q8_claim: "none; campaign-scoped WAIVE-Q8 remains binding and v8 makes no Q8 non-regression
>    claim"` (`ratify_v8_final_freeze_20260725.json:190`).
> 3. **Propagation.** Every artifact derived from the receipt — era-registry row draft, AutoPilot
>    rebaseline note, registry rows, dashboards, summaries — MUST carry the suppressed-claim rows. A
>    derived view that drops them is a retire-view defect (`MEASUREMENT.md:182-183`), repaired by
>    rebuilding the view, not by re-deriving the claim.
> 4. **Durability of the suppression.** Any later claim asserted about a waived cell, sourced from the
>    evidence of the campaign that waived it, is INVALID by construction: it cites a protocol whose
>    cell was removed from that campaign's required set.
> 5. **Evidence is retained.** Waiving a cell suppresses a claim; it never deletes, edits, or hides the
>    underlying records (`MEASUREMENT.md:174-175`). Ineligible or failed arm artifacts stay in the
>    campaign evidence root under `MEASUREMENT.md:146-156`, labelled.
>
> #### Grammar
>
> Suppressed claim (one row per forfeited claim):
> `NO CLAIM: <claim_text> — cell <cell_id> WAIVED [<protocol_id>, waiver <waiver_id>
> (<waiver_sha256[:12]>), scope <campaign|release>, campaign <campaign_id>, YYYY-MM-DD]`
>
> **Record class (required of every Annex K protocol by the Annex K Remit).** A suppressed-claim row
> is **not a claim**: it is a negative statement about what may not be asserted, and it gates nothing.
> The release verdict below **is a verdict, not a claim** — it carries no metric and no `n/reps`, so
> `MEASUREMENT.md:13`'s tuple does not apply to it, and it is not a cross-protocol comparison of
> anything. What it aggregates is per-cell PASS/FAIL determinations each made **within** its own
> protocol; the verdict states whether the required set is satisfied, never that one protocol's number
> beat another's. That is why it does not violate `MEASUREMENT.md:83-84`.
>
> Release verdict:
> `<source_tree> release <PASS|FAIL|PASS_WITH_WAIVER>, required=<r>, waived=<w>, suppressed_claims=<s>
> [<release-protocol-id>, bundle <bundle_sha256[:12]>, YYYY-MM-DD, attest <receipt>]`
>
> **`<release-protocol-id>` resolves to the protocol that defines the release verdict, which MUST have
> a `MEASUREMENT.md` §2 registry row before this grammar line is ratified.** This clause does not
> define that protocol and does not name it. **Presentation precondition (§10 item 1): if the release
> protocol has no registry row at presentation time, this grammar line is struck and the rest of
> K-WAIVER is ratified without it** — the authority, scope, non-waivable classes, ACTIVE conditions and
> claim-suppression rules are all independently useful, and a verdict grammar whose protocol slot
> resolves to nothing would be an observation under `MEASUREMENT.md:9-11` and could not legally gate
> the freeze it exists to gate.
>
> **Prospective.** Applies only to waivers authored after ratification and to evaluations run after
> it. No pre-ratification artifact is upgraded, and no pre-waiver artifact of any campaign may be
> retro-certified by the existence of a waiver — the standing rule v8 recorded per instance
> (`waive_q8_cpu_prefill_v8_20260725.json:27`) is hereby standing text. The v8 waiver itself is NOT
> re-expressed as a v1 object: it remains durable historical provenance under its own schema, and §5
> below is an exercise, not a migration.

---

## 5. Worked example — v8 `WAIVE-Q8` re-expressed in v1

Values below are historical facts read from
`artifacts/operator/waive_q8_cpu_prefill_v8_20260725.json`,
`artifacts/operator/ratify_v8_final_freeze_20260725.json`, and
`artifacts/operator/freeze_v8_production_20260725.sh`. Fields v1 requires that the v8 record does not
supply are marked **`[not in the source record]`** — each is a defect §5.3 explains, not an invention.

### 5.1 Field for field

| v1 field | Value |
|---|---|
| `schema` | `epyc.autokernel.operator_waiver.v1` |
| `waiver_id` | `akw-llama.cpp-waive-q8-20260725T140416Z` |
| `label` | `WAIVE-Q8` |
| `decision` | `WAIVE` |
| `protocol_changed` | `false` |
| `ratified_at` | `2026-07-25T14:04:16Z` |
| `ratification_receipt` | `{path: artifacts/operator/ratify_v8_final_freeze_20260725.json, sha256: <its bytes>}` — the reverse pointer already exists as `evidence_sha256.waive_q8 = fcd52b61…7522d7` |
| `binds.campaign_id` | **`[not in the source record]`** — the campaign existed (`cpu-prefill-v8-regression.v3`) but no id was bound |
| `binds.campaign_manifest_sha256` | **`[not in the source record]`** |
| `binds.source_tree` | `llama.cpp` |
| `binds.backends` | `["llama_cpu"]` — the waived cells are CPU llama-bench cells |
| `binds.candidate` | `{branch: production-consolidated-v8, commit: 67a433bf45a8a091d83b4ea0b32ff0735fd51800, seal_sha256: null}` (authored pre-seal) |
| `binds.incumbent` | `{branch: production-consolidated-v7, commit: 6ad45fa3ff6718c07c000061dbc6e29c1771f6e3, version: "10098"}` |
| `binds.instrument.evaluator_bundle_sha256_at_authorship` | `2fb0013d2cb71b149a7429995830ac0356048582671ae83428cb1ef15ccfe024` |
| `binds.instrument.recipe_ids` | **`[not in the source record]`** |
| `scope.addressing` | `release_plan_cell_id` |
| `scope.release_plan_sha256` | **`[not in the source record]`** — the plan lived inside the matrix artifact (`.plan.arm_runs`), unhashed as a standalone object |
| `scope.waived_cells[0]` | `cell_id: qwen36_q8-pp2048-iqk1`, `protocol_id: P-BENCH-PREFILL-1`, `backend: llama_cpu`, `phase: prefill`, `model: {id: qwen36_q8, path: /mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf, sha256:` **`[not in the source record]`**`, durability_class: hash-and-provenance-only}`, `arm_runs: 2`, `observed_status: INELIGIBLE` |
| `scope.waived_cells[1]` | `cell_id: qwen36_q8-tg128-iqk1`, `protocol_id: P-BENCH-1` (decode — see §5.3), rest as above, `phase: decode` |
| `scope.waived_cell_count` / `waived_arm_runs` | `2` / `4` |
| `scope.residual` | `{required_cell_count: 14, required_arm_runs: 28, manifest_sha256:` **`[not in the source record]`**`}` — the counts are v8's `remaining_matched_pairs` / `remaining_arm_runs`, and the freeze script already asserted both sides (`:250`, `:263`) |
| `reason.class` | `instrument_inapplicable` |
| `reason.text` | *"The Qwen3.6 Q8 workload naturally sustains about 50-55 target core-equivalents and cannot satisfy the ratified 72-core eligibility floor."* |
| `reason.refs` | `["measurement/protocols/bench-cpu.md:60-66"]` |
| `forfeited_claims[0]` | `{claim_text: "No v8 Q8 non-regression claim may be made from this campaign.", protocol_id: P-BENCH-PREFILL-1, cells: [both], suppression_scope: campaign}` |
| `preserved_obligations[]` | 3 entries: the 72-core floor unchanged for every remaining arm; the Gemma Q4 non-IQ B4 pairs mandatory; all retained IQ B3 pairs mandatory — each now carrying its `cells[]` |
| *(consequence 5)* | Not a field. Standing protocol text per §4's Prospective clause. |
| `validity.use_scope` | `single_campaign` — matching `q8_claim`'s "campaign-scoped … remains binding" |
| `validity.expires_at` | `null` |

### 5.2 What the migration must not lose — the gate predicate

Removing the campaign name from the schema id changes how a freeze script identifies a waiver.
`freeze_v8_production_20260725.sh:248-252` asserted:

```
.schema == "epyc.cpu_prefill_v8.operator_waiver.v1" and .decision == "WAIVE-Q8" and
.candidate_head == $head and .scope.excluded_arm_runs == 4 and
.scope.remaining_matched_pairs == 14 and
any(.consequences[]; . == "No v8 Q8 non-regression claim may be made from this campaign.")
```

Under v1 the equivalent, with no loss of specificity, is: the hash pin at `:214` (unchanged, and
already the real identity check), plus

```
.schema == "epyc.autokernel.operator_waiver.v1" and .decision == "WAIVE" and
.protocol_changed == false and .waiver_id == $waiver_id and
.binds.candidate.commit == $head and .binds.campaign_id == $campaign and
.scope.waived_arm_runs == 4 and .scope.residual.required_cell_count == 14 and
any(.forfeited_claims[]; .claim_text == "No v8 Q8 non-regression claim may be made from this campaign.")
```

The specificity that lived in the schema string moves to `waiver_id` plus the pinned SHA-256 — which
was always the stronger binding, since a hash pin cannot be satisfied by a different object of the
same type.

### 5.3 Defects in the original that v1 repairs

1. **One `protocol` scalar for cells of two protocols.** The excluded pairs are `pp2048` and `tg128`;
   the registry assigns prompt-processing to P-BENCH-PREFILL-1 and decode to P-BENCH-1
   (`MEASUREMENT.md:51-52`), and `bench-cpu.md:87-88` pairs prefill and decode ratios inside one IQ
   utility rule, so a v8-shaped campaign genuinely spans both. Whether the runner applied one
   eligibility algorithm to both arms is a property of that runner; the *schema* could not say which
   rule each waived cell escaped. v1 attributes a `protocol_id` per cell.
2. **Model identified by path, not hash.** `bench-cpu.md:41-44` requires model path/size/SHA256 in
   release identity; a path is a locator, not an identity, and the file it names can be replaced. v1
   requires `model.sha256` with a `durability_class` (`MEASUREMENT.md:151-155`), since a
   35B Q8 GGUF is hash-and-provenance-only evidence.
3. **No campaign binding.** "Campaign-scoped" existed only as prose in the ratification
   (`ratify_v8_final_freeze_20260725.json:190`). v1 binds `campaign_id` + manifest hash, making the
   scope machine-checkable and making campaign mutation an invalidation event.
4. **No expiry or reopen predicate.** The v8 object, read alone, is timeless. v1 supplies the derived
   invalidation set and self-retirement.
5. **Campaign name inside the schema id**, making the type predicate un-reusable (§5.2).
6. **`consequences[]` conflates three kinds of statement** — a forfeited claim, three preserved
   obligations, and one standing protocol rule — in one prose array, so only the first was
   machine-asserted (`freeze_v8_production_20260725.sh:251`) and the rest were unenforced text.
7. **A second, unwaived exclusion channel.** The same matrix predicate that binds the waiver hash also
   asserts `.plan.explicit_exclusion | index("qwen3.5-122b") != null`
   (`freeze_v8_production_20260725.sh:266`) — a model excluded from the required set with no waiver
   object behind it. v1 does not judge that exclusion; it requires that every exclusion carry exactly
   one of the **three** admissible provenances (§4), and this one is channel **(c)**, an
   operator-declared plan-level exclusion. The distinction becomes visible in the verdict bundle
   instead of being discoverable only by reading a `jq` predicate. *(Span corrected from `:266-267`;
   `:267` is the `iq_utility` assertion.)*
8. **No waiver id and no reverse pointer to the ratification receipt** (§3.1, §3.2).

Nothing in the v8 record is inexpressible in v1.

---

## 6. What this schema deliberately cannot express

Enumerated so that the absences are choices on the record, not oversights:

- **A correctness, quality, numerical-safety, stability, linkage, or identity waiver.** Not
  representable, by construction (§4, *Non-waivable classes*).
- **A threshold relaxation.** There is no field that can move a ratio band, a rep count, an
  eligibility floor, or an objective weight. A waiver subtracts cells; it cannot edit rules.
- **A pattern-scoped or open-ended scope.** No globs, no predicates, no "and similar cells".
- **A verdict.** The waiver cannot assert `PASS_WITH_WAIVER`; verdicts are computed.
- **A blanket or standing waiver.** Every waiver binds one campaign, one source tree, one candidate,
  one incumbent, and one declared use scope.
- **A waiver of the human-only boundary.** Freeze, cutover, era rows, and baseline applies stay human
  (`MEASUREMENT.md:140-142`); no waiver field touches them.
- **Retroactive coverage.** A waiver cannot reach backwards over evidence already produced under a
  different evaluator or era.

## 7. Placement — RESOLVED, and reconciled with the container

**The normative `K-WAIVER` clause is filed in Annex K** (`measurement/protocols/kernel-research.md`),
alongside `P-AK-SEARCH-1`; **the JSON schema itself lives in the schema plane.** The two halves are
different objects and go to different places.

*(This reconciles a contradiction a review found. An earlier revision of this section recommended
Annex K while `Annex-K-container.draft.md:143` listed the whole object under "What Annex K does NOT
hold", routing it to the schema plane — so the operator would have received two mutually
contradictory placements on one page. The container's §3 table is now amended to admit the K-WAIVER
clause and to keep the JSON schema in the schema plane, and it states which admission test the clause
satisfies.)*

**Which admission test it satisfies** (`Annex-K-container.draft.md` §2):

1. its subject is a **kernel release decision** — yes;
2. it is **cross-backend in shape** — one waiver binds a `source_tree` and may enumerate cells of
   several backends that tree serves (`handoffs/active/autokernel-research-loop.md:129-153`) — and it
   emits records that are **not claims** (a suppressed-claim row and a verdict) — yes;
3. **no existing annex states the rule this clause establishes** — `bench-cpu.md:96` *names* an
   operator waiver and defines no instrument, so K states the instrument rather than restating B's
   rule. Under the **narrowing carve-out**, `bench-cpu.md:96` receives an appended cross-reference in
   the same apply.

Placing the clause in one backend annex would give a shape-cross-backend object a backend home;
placing it in two would give one authority two amendment histories — exactly the argument the operator
already accepted for Annex K (`README.md:73-85`). **But note the authority limit in §4:** filing the
clause in K does not by itself extend waiver authority to a backend whose own annex grants none.
Annex G must grant it before a GPU cell may be waived.

## 8. Ratification checklist (attestation 2)

**Presentation preconditions — all MUST hold before this item is placed in front of the operator:**

- [ ] **Annex K exists.** `measurement/protocols/kernel-research.md` was created by attestation 1a
      item 1. If item 1 was struck, this item has no home and is not presentable.
- [ ] **The release protocol has a `MEASUREMENT.md` §2 registry row**, or the verdict-grammar line is
      struck (§4, `<release-protocol-id>`; §10 item 1).
- [ ] **The evidence-retention clause is in force**, so that `durability_class`'s enum is defined.
      Two of its three values (`carried-in-git`, `durable-untracked`) exist **only** in that clause;
      `MEASUREMENT.md:154` defines only `hash-and-provenance-only`. It lands as attestation 1a item 5;
      if that item was struck, narrow `model.durability_class` to the one ratified value plus a
      free-text provenance note before presenting. *(§10 item 8.)*
- [ ] **The sealed-candidate amendment's disposition is known** (§10 item 6): if it is struck,
      `binds.candidate.seal_sha256` is dropped and `use_scope: single_seal` is unavailable, leaving
      `single_campaign` as the only value.

**Apply steps:**

- [ ] Append §4 verbatim to `measurement/protocols/kernel-research.md` — append, never edit in place
      (`MEASUREMENT.md:116-118`). Substitute `<APPLY_DATE>`; the heading carries **no `DRAFT`
      marker** *(an earlier revision would have written the literal string `<DATE>` and the word
      DRAFT into the constitution, making the annex self-describing as non-ratified after
      ratification)*.
- [ ] Append the one-sentence cross-reference to `measurement/protocols/bench-cpu.md:96` recording
      that the instrument that sentence names is defined by `K-WAIVER` (Annex K, §7 admission test 3).
- [ ] Append the corresponding waiver clause to `measurement/protocols/gpu-cross-device.md`, **or**
      restrict `binds.backends` to CPU backends (§4, *Per-annex reach*).
- [ ] Add the one-line `MEASUREMENT.md` CHANGELOG entry, naming Annex K and Annex B as amended.
- [ ] Add or update the `MEASUREMENT.md` §2 registry row for the owning release protocol, naming the
      three verdict states.
- [ ] **Create the waiver storage directory with a README first**, then add its path to
      `coordination/session-bus/human_only_paths.yaml` and rewrite `human_only_paths.sha256` as one
      atomic pair; re-verify with `session_bus.py validate`. The directory must exist before the
      entry is written (`human_only_paths.yaml:21-24`, and §4 *Authorship and storage*).
- [ ] State supersession explicitly: this schema does **not** supersede
      `epyc.cpu_prefill_v8.operator_waiver.v1`, which remains the durable historical record of the v8
      freeze; name its path and SHA-256 as preserved provenance.
- [ ] Record every semantic delta in `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md`
      (full path), including the eight repairs in §5.3.
- [ ] Verify every cited evidence path resolves in-repo, using
      `epyc-inference-research/scripts/validate/check_evidence_durability.py`. *(The path matters: the
      validator does **not** exist at `scripts/validate/check_evidence_durability.py` in epyc-root,
      although `MEASUREMENT.md:155` names it there — a defect in the 2026-08-02 amendment inherited by
      every document that cites it, and worth surfacing to the operator independently of this item.)*
- [ ] Confirm the AK5 dry-run behaves as §10.4's calibration note requires
      (`handoffs/active/autokernel-research-loop.md:1473-1474`): v8 predicts **FAIL** without its
      waiver and `PASS_WITH_WAIVER` with it. The v8 shape is expressible as a `single_campaign`
      waiver, which does not consult the bundle ledger (ACTIVE condition 9), so the dry-run is
      reachable without AK1's store; its second, unwaived exclusion is provenance channel (c). A
      dry-run that passes without the waiver falsifies the compiler, not the schema.
- [ ] Present alongside the P-GPU-1 sealed-candidate amendment as one attestation with strikeable
      lines.

## 9. Open questions for the operator

1. **Default `use_scope`.** The draft recommends `single_seal`, which means an evaluator patch or a
   re-seal after a failed freeze requires the waiver to be re-signed. `single_campaign` (v8's de facto
   scope) is less friction and more standing authority. Recommendation: `single_seal` default,
   `single_campaign` available and stated on the receipt.
2. **Evaluator drift.** As drafted, any change to the evaluator bundle makes every open waiver
   inactive. That is fail-closed and requires no judgement; the alternative — "the delta does not
   touch the waived cells" — reintroduces exactly the merits judgement §4 forbids the evaluator to
   make. Recommendation: keep it strict.

## 10. Residual dependencies

Bindings that could not be reduced to a contract or a procedure, with the reason:

1. **The document that normatively defines the verdict enum — a PRESENTATION PRECONDITION, not merely
   a residual.** §4 emits and constrains `PASS` / `FAIL` / `PASS_WITH_WAIVER`, but the protocol that
   *defines* the release verdict is undecided: `P-KERNEL-FREEZE-1` in Annex K versus distributed
   amendments to B and G (`README.md:95-99`). `P-KERNEL-FREEZE-1` today exists only as a string in the
   campaign manifest (owning handoff `:836`) and in two open questions; it is absent from the
   `MEASUREMENT.md` §2 registry (`:49-66`). **Disposition:** the verdict-grammar line is struck unless
   a registry row exists at presentation time (§4, §8). The rest of K-WAIVER — authority, scope,
   non-waivable classes, ACTIVE conditions, suppression — ratifies without it.
2. **The `human_only_paths.yaml` glob string for waiver storage.** The schema binds the *property* —
   a path matched by a human-only entry — which is ratifiable. The literal glob is a path the operator
   chooses at ratification and must be typed into a human-only file by a human, so it cannot be
   written here. Note that the existing `measurement/protocols/*.md` entry
   (`coordination/session-bus/human_only_paths.yaml:32-34`) does **not** cover `artifacts/operator/…`,
   so this is a genuine addition, not a glob already satisfied. **Cross-reference:**
   `human-only-paths-delta.draft.md:157-165` deliberately refuses to add this entry today, on the
   ground that a path entry for a directory that will be empty for months violates that file's own
   header promise of real paths. Both positions are correct and are now reconciled: the directory is
   **created with a README in the same apply as this clause**, so the entry names a path that exists
   at the moment it is written (§4 *Authorship and storage*, §8).
3. **Human authorship cannot be cryptographically established.** Authorship rests on the trust
   boundary's three procedural layers plus git provenance
   (`coordination/session-bus/human_only_paths.yaml:5-12`), and that file itself records that layers 2
   and 3 detect *after the fact*. A process with shell access outside the PreToolUse hook could write
   a syntactically valid waiver; nothing in this schema closes that, and no field can. Closing it
   needs signing infrastructure that does not exist and is out of scope for a measurement annex.
4. **Cell addressing depends on an unbuilt compiler.** §3.4 binds cell identity to "the identifier the
   release plan assigns", joined by exact string equality. That is a contract, and it is ratifiable —
   but it places an obligation on AK5's release-plan compiler (stable, exact-matchable, hashed cell
   ids) that no delivered artifact yet satisfies. If AK5 produces unstable ids, this schema's join
   breaks and the fix is in the compiler, not here.
5. **`single_seal` use-scope exhaustion requires a bundle ledger that does not exist.** ACTIVE
   condition 9 checks whether an earlier sealed bundle already consumed the waiver. The waiver cannot
   record its own consumption — it is immutable and human-only — so the check reads an append-only
   **release-bundle ledger**: a record of which bundles consumed which waivers. **That store is AK1's
   and does not exist.** *(Corrected after review: an earlier revision cited owning handoff `:520-523`
   "invariant 7" as establishing it. Invariant 7 at `:520-521` describes an append-only **event
   journal**, not a bundle-consumption ledger, and `:522-523` is invariant 8. The cited text does not
   establish the store the condition reads, so the store is named here as an AK1 obligation rather
   than claimed to exist.)* Fail-closed without it — which is why `single_campaign` exists as a scope
   that does not consult it (condition 9), so the schema is not inert on ratification day.
6. **`binds.candidate.seal_sha256` depends on the sealed-candidate amendment, which is unratified.**
   The seal hash is defined by `P-GPU-1-sealed-candidate-amendment.draft.md` (§3 field 10, grammar
   line `:102`), which rides attestation 2 alongside this item. **Strike behaviour, stated on the
   attestation face:** if the sealed-candidate amendment is struck, `seal_sha256` is dropped from this
   schema and `use_scope: single_seal` becomes unavailable, leaving `single_campaign` as the only
   value. *(This co-dependency was absent from an earlier revision's §10, whose preamble claimed
   residual dependencies were exhaustively enumerated.)*
7. **A campaign-manifest schema delta is available but not required.**
   `binds.instrument.evaluator_bundle_sha256_at_authorship` now sources from the T3 verdict bundle
   (§3.3), which the design already defines. If AK1 prefers to add `instrument.evaluator_bundle_sha256`
   to `epyc.autokernel.campaign.v2`, that is a design change (owning handoff §7.1), not a
   constitutional one, and this field may source from there instead. Recorded so the option is on the
   record rather than rediscovered.
8. **`model.durability_class`'s enum is defined by a sibling clause, not by the core file.** Only
   `hash-and-provenance-only` appears in `MEASUREMENT.md` today, at `:154`. `carried-in-git` and
   `durable-untracked` are defined by the evidence-retention clause riding attestation 1a as item 5.
   **Hard prerequisite, with a stated fallback** (§8): if item 5 was struck, narrow the field to the
   one ratified value plus a free-text provenance note. *(An earlier revision cited
   `MEASUREMENT.md:151-155` for all three values; two thirds of that enum had no ratified definition
   anywhere.)*
9. **Era-boundary invalidation reads a registry this schema does not own.** The condition is stated as
   a procedure, but evaluating it requires read access to
   `epyc-orchestrator/orchestration/instrument_eras.yaml` (`MEASUREMENT.md:190-191`), which is
   human-only for writes and outside the evaluator bundle. Contract on AK3's evaluator; no literal
   involved.
