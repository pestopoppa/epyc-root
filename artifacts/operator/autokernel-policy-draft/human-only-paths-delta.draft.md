<!-- DRAFT — NOT RATIFIED, NOT IN FORCE. Staged for operator review per
     artifacts/operator/autokernel-policy-draft/README.md (attestation 1).
     Target: coordination/session-bus/human_only_paths.yaml + human_only_paths.sha256.
     Author: AutoKernel design pass, 2026-08-03.
     Filenames of not-yet-existing markdown are written WITHOUT `.md` per that README. -->

# DRAFT — `human_only_paths.yaml` delta (AutoKernel instrument surfaces)

**Status:** SPLIT after adversarial review (2026-08-03). **The two `paths:` entries are DEFERRED; the
two `conceptual:` entries are signable tonight.**

**Presented tonight (attestation 1a, item 8):** two `conceptual:` entries — **C1** and **C2** — plus
the `human_only_paths.sha256` rewrite, as **one strikeable line** covering the YAML edit and the pin
together (owning handoff `:1793-1795`). Both entries record boundaries that are **verified true
today**, name **no path**, and therefore cannot put an unverifiable line into a file whose own header
promises *"real paths, verified to exist"* (`human_only_paths.yaml:21-24`).

**Deferred to attestation 1b (`RATIFICATION_PACKAGE.md` §D, D3 and D4):** the **D1** evaluator-bundle
entry and the **D2** policy-plane entry. The blocking fact is trivially checkable and was verified:

| Proposed entry | Path it names | Status today |
|---|---|---|
| D1 | `epyc-inference-research/scripts/kernel_rnd/autokernel/evaluator/**` | the parent directory holds only `__init__.py` and `schemas.py`; **there is no `evaluator/`** |
| D2 | `measurement/policy/autokernel/*.yaml` | `/workspace/measurement/policy/` **does not exist at all** |

This draft already used exactly that argument at §1.6 to defer the waiver-directory entry — *"Adding
a path entry now for a directory that will be empty for months would put an unverifiable line in a
file whose own header promises real paths, verified to exist"*. D1 and D2 point at directories that
are **further** from existing than an empty one, so the same argument is fatal to them. Deferring
them also costs nothing: §2.1 already concedes they are *"naming contracts on AK3's deliverable
layout, not references to existing artifacts"*, so the entry text is corrected for free before apply.

**Amends:** `coordination/session-bus/human_only_paths.yaml` (2 `conceptual:` entries) and its
`human_only_paths.sha256` pin.
**Owning handoff:** `handoffs/active/autokernel-research-loop.md` §3.6 (`:459-473`), §14 AK0
(`:1873-1874`).

> **Collision resolved.** An earlier revision of the preflight-substitute item
> (`preflight-substitute.draft.md`, superseded) also required an entry in this same hash-pinned file
> on the same signature. Because the pin is a **whole-file** SHA-256 (`config.yaml:161-164`), two
> independently strikeable lines cannot both edit it — whichever applied second would invalidate the
> first's recorded pin and its receipt, reproducing the exact drift signature of a hostile
> out-of-band edit (§5). That enumerator entry is withdrawn with Stage I, so **exactly one item in
> tonight's package touches `human_only_paths.yaml`**, and the "one strikeable line, one terminal pin
> rewrite" claim is implementable as stated. Any future package adding several entries MUST merge
> them into one line with one terminal pin rewrite, resolving per-entry strikes **before** the pin is
> computed, never after.

---

## 0. What this delta is, and what it is not

`coordination/session-bus/human_only_paths.yaml:1-18` states the trust boundary as data and documents
its three enforcement layers: a PreToolUse hook that refuses Write/Edit, a `.sha256` content pin
checked by `session_bus.py validate`, and a coordinator-daemon audit that emits a `defect` on drift.
`BUS_PROTOCOL.md:38-41` restates the rule from the bus side — *"The human-only path list is itself
human-amendment-only and hash-pinned — coordinator-agent reads it, never writes it."*
`MEASUREMENT.md:119-120` gives the constitutional reason: the constitution, its annexes, the era
registry, the eval tower and scoring contracts *"are read-only for autonomous optimization
processes"*. AutoKernel is an autonomous optimization process. Its evaluator and its gate thresholds
are scoring contracts. They therefore belong inside that boundary, and today they are outside it only
because they do not exist yet.

> **What lands tonight adds two `conceptual:` entries and nothing else. It authorizes nothing and it
> enforces nothing.** It does not ratify `P-AK-SEARCH-1` or any other protocol; it does not create the
> evaluator bundle or the policy file; it does not authorize AutoKernel to run, to search, to seal, to
> freeze, or to cut over; and it does not grant any agent — including a session doing AutoKernel
> implementation work — permission to write anything. The environment override
> `EPYC_ALLOW_TRUST_BOUNDARY_EDIT=1` (documented at `scripts/hooks/check_trust_boundary_edit.sh:28`,
> implemented at `:33`) remains operator-scoped, and this delta MUST NOT be cited as a reason for an
> agent to set it.
>
> **On the "does not alter the enumerated human-only writes" claim.** An earlier revision asserted
> that flatly. It was **false of the deferred D1/D2 entries**, which add two write classes — an
> AutoKernel evaluator bundle and an AutoKernel threshold policy plane — that appear in none of the
> three places the closed enumeration is restated: `MEASUREMENT.md:141-142`,
> `agents/shared/MEASUREMENT_POLICY.md:71-73`, and `coordination/session-bus/BUS_PROTOCOL.md:38-39`.
> Either that enumeration is closed, in which case D1/D2 exceed it and must ride a `MEASUREMENT.md`
> §5 append plus a CHANGELOG line plus matching one-line deltas to the digest and the bus protocol; or
> it is illustrative, in which case that must be stated and the precedent cited. **It cannot be
> both.** Left unresolved, the constitution, the agent-facing digest, the bus protocol and the gate
> list would disagree about what requires an operator signature, with `MEASUREMENT.md:20-21` making
> the constitution win while agents read the digest. That reconciliation is now a **named precondition
> on D1/D2** (`RATIFICATION_PACKAGE.md` §D, D3), not an assertion. The two `conceptual:` entries
> landing tonight add no write class at all — a `conceptual:` entry is explicitly *"unenforceable by
> the audit"* by construction (`human_only_paths.yaml:51-55`) — so the claim is true of them.

---

## 1. The boundary argument — what belongs, and what must stay out

### 1.1 The failure mode being avoided

An over-broad entry is not merely untidy: it converts routine research into operator ceremony. The
research runtime is `epyc-inference-research/scripts/kernel_rnd/autokernel/` (owning handoff
`:271-273`, `:2277-2286`), and that tree will be edited continuously for months. The naive entry —

```yaml
  - repo: epyc-inference-research
    glob: "scripts/kernel_rnd/**"          # REJECTED
```

— would put the controller, planner prompts, journal writer, store, sweep driver, backend adapters,
dashboard exporter and every test behind an operator token. That is the outcome the operator
explicitly does not want, and it would also be *self-defeating*: a boundary that fires on every
ordinary edit gets routed around, and a routed-around boundary protects nothing.

The correct test for an entry is narrow: **could an agent with write access to this path change what
counts as a pass?** Everything that answers yes belongs in; everything that answers no stays out.

### 1.2 D1 — the evaluator bundle. BELONGS.

The evaluator decides correctness, coherence, and whether a candidate beat its anchor. Owning handoff
invariant 17 (`:540-541`) — *"No evaluator self-modification"* — and AK-D10 (`:2226`) — *"The
optimizer cannot rewrite its judge"* — are the design statements; `MEASUREMENT.md:119-120` is the
constitutional one. An agent able to edit the evaluator's test list, its reference outputs, or its
gate implementation can pass any gate by deleting the check, which is the exact defect class recorded
in project memory as *"can I pass this by deleting what it inspects?"*.

**Scope discipline.** The entry covers the *bundle root only*, not the runtime. This requires a
structural commitment from AK3, stated here as a contract:

> The AutoKernel evaluator bundle MUST be a single directory containing everything that determines a
> verdict: the evaluator entry points, the declared test list, reference outputs, sentinel and
> holdout corpus manifests, the gate implementations, and **the reducers that compute the gated
> statistic**. Nothing that determines a verdict MAY live outside it, and nothing that does not
> determine a verdict SHOULD live inside it. One directory, one entry: the alternative — a new path
> entry each time the evaluator gains a file — grows the human-only surface by accretion and requires
> an operator amendment per file.
>
> **Recipe construction is a property, not a location.** An earlier revision put *"the codified recipe
> constructors the runner uses to build argv"* inside the bundle. That is unworkable both ways: the
> canonical constructors live in `epyc-inference-research/scripts/benchmark/` (owning handoff
> `:2280`), a shared tree used by non-AutoKernel benches, so forking them into the bundle creates two
> sources of truth for the production recipe — the exact defect recorded as
> *"import codified recipe constants"* — while dragging the shared tree behind an operator token makes
> a routinely-edited path ceremonial. The requirement is therefore stated as a property: **the
> evaluator MUST recompute the gated statistic from raw persisted samples and MUST NOT consume a
> reducer output it did not itself compute; the argv actually executed MUST be recorded in the run
> attestation and MUST be recomputable inside the bundle from the codified recipe constants imported
> from `epyc-inference-research/scripts/benchmark/` at a pinned revision.** A recipe change is then
> visible as a pinned-revision change in the attestation, not as a silent argv drift.

### 1.3 D2 — the objective / threshold policy plane. BELONGS.

`P-AK-SEARCH-1` and the per-backend objective (owning handoff §1.6, `:171-187`) are prose in Annex K.
A daemon cannot read prose. The file it *does* read — the machine-readable projection of those rules:
the objective rule identifier, phase-to-protocol mapping, gate bands, anchor-gate tolerance, minimum
block counts, the noise-floor derivation procedure, the stopping-rule schema, the freeze cadence
(owning handoff `:1819-1820`), and the expected evaluator-bundle SHA-256 — is the file that actually
decides pass/fail. The campaign manifest already anticipates it: `policy_ref` at owning handoff
`:833-836` carries `policy_bundle_sha256` under the comment *"authority/thresholds live in the
human-only policy plane"*. That plane is only human-only if something makes it so. This entry is that
something.

This entry also carries the second half of the evaluator defense. D1 stops *agent tool writes* to the
evaluator bytes. D2 pins the *expected hash of those bytes* on the human-only side, so a write that
never passes a hook — a daemon, a subprocess, a shell redirect — is caught fail-closed at run start
rather than being trusted. Neither entry alone does that; the pair does.

> The policy bundle MUST carry the expected evaluator-bundle digest, and a conforming runner MUST
> recompute the bundle digest at run start and at every resume, compare it against the pinned value,
> and refuse the run on mismatch. A drift detected mid-run voids the window per the Annex K void
> conditions. The runner MUST NOT repair, re-pin, or "adopt" an observed digest.

### 1.4 The "campaign policy plane" — SPLIT. Only its authority half belongs.

This is the entry that would have gone wrong. The phrase covers two different things:

| Content | Written by | Belongs in the list? |
|---|---|---|
| objective rule, gate bands, block minimums, noise-floor derivation, stopping-rule schema, freeze cadence, evaluator digest | operator | **YES** — this is D2 |
| campaign manifests (`epyc.autokernel.campaign.v2`), budgets, scope, schedule, backend selection | campaign compiler | **NO** |

Pinning campaign manifests would mean an operator token per campaign — a per-experiment ratification
cycle, which is precisely what `MEASUREMENT_POLICY.md:77-78` and the two-attestation split exist to
prevent, and what `MEASUREMENT.md:139` forbids when it requires that *"evidence collection and
validation never wait on a human signature"*.

The manifest is nonetheless prevented from lying, without a token, by a fail-closed check rather than
a write boundary:

> A campaign manifest MUST reference the policy bundle by digest (`policy_ref.policy_bundle_sha256`).
> A conforming controller MUST refuse to start, and MUST journal the refusal, when the referenced
> digest does not equal the digest of the on-disk policy bundle. The manifest MAY narrow what the
> policy permits — a smaller budget, a subset of backends — and MUST NOT widen it. A manifest field
> that would relax a gate band, lower a block minimum, or alter the objective rule is a schema
> violation, not a configuration choice. This is the `config.yaml:149-156` pattern
> (`on_topology_mismatch: refuse`), applied to policy rather than topology.
>
> **Narrow-versus-widen is evaluated on the D1/D2 side, never by the manifest's own schema.** The
> comparison operator, and the definition of which direction is narrower for each field, live inside
> the human-only policy plane. Otherwise the guarantee is self-referential: `epyc.autokernel.campaign.v2`
> is agent-writable (§1.5), so a loop that could not widen a value could still widen the schema that
> defines widening.

**The sanctioned evolution path for the evaluator — stated so D1 does not read as a freeze.** A
conforming controller that discovers its evaluator lacks a required coverage class records
**`EVALUATOR_COVERAGE_GAP`**, blocks release for the affected lineage, continues unrelated research,
and MAY draft an amendment bundle for human review. It MUST NOT modify the live evaluator (owning
handoff `:471-473`). This matters for how D1 and D2 are read together: because D2 pins the digest of
D1's bytes, every legitimate evaluator change costs an operator signature on both — so the batching
rule at `MEASUREMENT_POLICY.md:77-78` applies to evaluator amendments exactly as it applies here, and
a package of accumulated `EVALUATOR_COVERAGE_GAP` reports is presented as **one** attestation with
strikeable lines, never one signature per gap. Without that, D1 + D2 reproduce the per-experiment
ratification cycle `MEASUREMENT.md:139` exists to prevent.

### 1.5 Explicitly NOT added

Recorded so a later reader knows these were considered and rejected, not overlooked. Each stays
agent-writable:

- **the append-only event journal and its shards** — written continuously by the daemon, so a write
  boundary is impossible. But *"append-only integrity is an implementation property"* was too casual:
  the journal is the primary record of void conditions and stopping-rule state, and an actor that can
  rewrite a shard can retract a void after the fact. `MEASUREMENT.md:174-176` governs its content
  without making it real. **Required companion, stated as an implementation obligation:** journal
  shards are written append-only at the OS level (`O_APPEND`, and a shard sealed with its own
  content hash at rotation), the seal hash of every closed shard is carried into the campaign's
  evidence directory under `SHA256SUMS`, and a shard whose recomputed hash differs from its seal
  voids every record it contains. Without that, "append-only" is a naming convention;
- **campaign manifests, budgets, scope, schedules** — §1.4;
- **the controller, planner and critic prompts** — an actor that can rewrite its own prompts cannot
  thereby change a verdict; the evaluator is downstream of all of it;
- **backend adapters** — *only* as launchers and result parsers. **The argv an adapter emits is
  constrained by §1.2's recomputability property**, and an adapter whose emitted argv cannot be
  recomputed inside the bundle from pinned recipe constants voids the run. An earlier revision listed
  adapters here unqualified while §1.2 put argv construction inside the bundle; the two statements
  contradicted each other, and an adapter that freely builds argv can change the measured number
  without touching the evaluator — which fails this draft's own inclusion test at §1.1;
- **reducers — MOVED.** An earlier revision left reducers agent-writable on the ground that the
  evaluator is downstream of them. It is not: a reducer produces the statistic the gate compares, so
  an actor that can rewrite it changes what counts as a pass without ever touching the evaluator.
  That fails the inclusion test, invariant 17 *"No evaluator self-modification"* (`:540-541`), and
  AK-D10 *"The optimizer cannot rewrite its judge"* (`:2226`). Reducers are now inside the D1 bundle
  (§1.2);
- **candidate source, campaign worktrees, campaign branches** (`ak/<campaign_id>/…`) — the point of
  the design is that these are freely mutable; the frozen production branches are already covered at
  `human_only_paths.yaml:42-49`;
- **`scripts/kernel_rnd/kernel_store.py`, `kernel_sweep.sh`, `kernel_eval.sh`** — the pre-AutoKernel
  scaffolding, which owning handoff `:198-200` documents as defective and slated for replacement.
  Freezing a known-defective evaluator would be the worst of both outcomes: it protects nothing and
  blocks its own repair;
- **the dashboard and its export contract** — a view cannot change a verdict, provided it is in fact
  a view. *(An earlier revision cited `dashboard/server.py:826` as proof of read-only-ness; that line
  is `elif route == "/kernel":`, a route dispatch, and the citation named no repo despite ~10 copies
  of that file existing across worktrees. The claim stands on the design — the dashboard consumes the
  journal and the store and writes neither — and the citation is withdrawn rather than repaired,
  because a wrong file:line is worse than none.)*
- **evidence artifacts under `epyc-inference-research/data/<campaign>/`** — governed by evidence
  durability (`MEASUREMENT.md:146-156`) and by the retention clause riding this same package. A write
  boundary on evidence would stop the loop from *recording* evidence, which inverts the goal.
  *(Corrected: an earlier revision said "deletion authority there is already an operator matter per
  `MEASUREMENT.md:223-229`". It is not. `:223-229` is the 2026-06 explicit dump list, whose rule is
  the opposite — everything not enumerated **is kept** — and whose only operator call is ~1.2 GB of
  superseded embedding blobs under `repl_memory/sessions/`. Deletion authority over campaign evidence
  comes from the retention clause, or from nowhere.)*

### 1.6 Deferred to attestation 2 — deliberately, not omitted

`epyc.autokernel.operator_waiver.v1` instances. A waiver the actor can write is a self-waiver, and
the v8 precedent is explicit hash-pinned waiver verification
(`artifacts/operator/freeze_v8_production_20260725.sh:214`, `:248`, `:268`; owning handoff `:206`,
AK-D13 `:2229`). It is nonetheless *not* in this delta: no waiver, and no waiver schema, exists yet,
and attestation 2 is where release-side bindings land (staging README `:41-49`). Adding a path entry
now for a directory that will be empty for months would put an unverifiable line in a file whose own
header (`:21-24`) promises *"real paths, verified to exist"*.

---

## 2. The exact YAML entries

### 2a. PRESENTED TONIGHT — two `conceptual:` entries

**Transcribe verbatim.** Append both as the last items of the `conceptual:` block (currently ending
`human_only_paths.yaml:60`), preserving the file's two-space list indentation. **No `paths:` entry is
added, so no path that does not exist is named.**

```yaml
# --- C1, appended to the `conceptual:` block ----------------------------
  - "AutoKernel evaluator immutability against non-agent writes — the PreToolUse layer sees agent tool calls only, so a daemon or a candidate subprocess bypasses it entirely; the enforcing layer is OS-level (separate uid or read-only bind mount), and no glob can express it"

# --- C2, appended immediately after C1 ---------------------------------
  - "glob: entries in the paths: block above were DECLARATIVE ONLY until 2026-08-03: the matcher in scripts/hooks/check_trust_boundary_edit.sh quoted its right-hand side, which disables bash pattern matching, so measurement/protocols/*.md matched nothing and Annexes B/Q/G were agent-writable through Write/Edit while the guard reported success. Literal entries were unaffected and always blocked, which is why the defect survived every prior test. REPAIRED in epyc-root 6f1c4a8b (RHS unquoted) with scripts/hooks/test_check_trust_boundary_edit.sh asserting both directions against the live gate list. A future editor must not re-quote it"
```

**Why these two, and why they belong in this file rather than in a handoff.** The `conceptual:` block
exists precisely for *"real boundaries that no path pattern captures … listed so they are not silently
forgotten, and explicitly marked unenforceable by the audit so nobody mistakes a clean audit for full
coverage"* (`human_only_paths.yaml:51-55`).

- **C1** is §6 of this draft made durable inside the file it concerns, so a future reader who sees a
  `paths:` entry pass the audit does not conclude the evaluator is protected.
- **C2** is the same discipline applied to a **verified live defect in this file's own enforcement**.
  Finding V2 (§3) is not an AutoKernel matter — it means the measurement annexes are agent-writable
  today. Recording it beside the entries it silences is the cheapest durable form the finding can
  take, and it prevents the next reader from doing what the earlier revision of the Annex K container
  did: asserting that a glob protects a new annex file.

Neither entry names a path, neither adds a write class, and neither can go stale by an artifact
failing to appear. C2 becomes obsolete when the matcher is repaired, at which point it is amended out
by the same operator procedure — which is a correct outcome, not a maintenance burden.

### 2b. DEFERRED — the two `paths:` entries (D1, D2)

Reproduced here so the contract is on the record and the entry text can be corrected for free before
AK3 delivers. **These are NOT applied tonight** (`RATIFICATION_PACKAGE.md` §D, D3/D4).

```yaml
# --- D1 — DEFERRED, do not apply ----------------------------------------
  - repo: epyc-inference-research
    glob: "scripts/kernel_rnd/autokernel/evaluator/**"
    why: "AutoKernel evaluator bundle — test list, reference outputs, gate implementations, reducers; an optimizer that can edit its own judge can pass any gate by deleting the check"

# --- D2 — DEFERRED, do not apply ----------------------------------------
  - repo: epyc-root
    glob: "measurement/policy/autokernel/*.yaml"
    why: "machine-readable projection of the Annex K objective and gate rules, plus the expected evaluator-bundle digest; the daemon cannot read the annex, so this is the file that actually decides pass/fail"
```

**Entry grammar** (the file's existing shape, stated so a later addition matches):
`- {repo: <repo-id>, glob: "<path-pattern>", why: "<one line naming the authority the entry protects>"}`

### 2.1 Preconditions D1 and D2 must clear before they are presented

1. **The paths exist.** D1's bundle root is delivered by AK3 with a `SHA256SUMS`; D2's policy
   directory exists and holds the bundle the campaign manifest's `policy_ref` names.
2. **The matcher is repaired** (§3, finding V2) with a wildcard test case, and the compliant path is
   asserted still to pass. Without this, D1 and D2 are wildcards enforced by nothing and buy exactly
   zero enforcement at layer 1.
3. **The closed-enumeration question is resolved** (§0): either a `MEASUREMENT.md` §5 append extends
   the enumerated human-only writes, with a CHANGELOG line and matching one-line deltas to
   `MEASUREMENT_POLICY.md:71-73` and `BUS_PROTOCOL.md:38-39`; or the enumeration is declared
   illustrative, on the record, with its precedent.
4. **D2's normativity question is resolved.** `MEASUREMENT.md:17-18` declares that *"full normative
   protocol text lives in three annexes in `measurement/protocols/`"*. D2 places the operative gate
   bands, objective rule and stopping-rule schema — *"the file that actually decides pass/fail"*
   (§1.3) — outside that home, with nothing requiring the YAML to equal the Annex K prose and nothing
   detecting divergence. Editing that YAML would then amend a protocol without an annex append or a
   CHANGELOG line: the silent edit `:116-118` forbids, performed by the operator rather than by an
   agent, which is not a cure. **Required before D2 lands**, pick one and state it in the layout
   paragraph: *(a)* the policy bundle carries the Annex K version and section it projects, any change
   to a projected value rides an Annex K append plus a CHANGELOG line in the same signature, and a
   validator asserts projection-equals-annex and fails the run on divergence; or *(b)* the YAML is
   declared normative and the annex descriptive.
5. **The D2 contract forbids a cross-protocol gate in terms.** The policy plane is exactly where a
   gate spanning more than one `protocol_id` would be introduced, and both `MEASUREMENT.md:83-84` and
   the owning handoff `:185-187` (*"cross-backend roll-ups may be reported … They never gate"*) forbid
   it. Silence is not a prohibition.
6. **One merged line, one terminal pin.** If any other item in the same package also edits this file,
   all entries merge into a single strikeable line with a single pin rewrite computed after the last
   byte; per-entry strikes are resolved before the pin is computed, never after.
7. **The reciprocal dependency is acknowledged.** `P-AK-SEARCH-1` precondition 5 requires the
   evaluator bundle to be pinned; its R2 records that the pin closes the agent write path only, and
   that the immutability the precondition assumes is OS-level. D1 must be presented with that
   correction visible, not as though it delivered immutability.

### 2.2 No `schema_version` bump

Adding entries uses the existing v1 shape (a bare string for `conceptual:`, `repo` / `glob` / `why`
for `paths:`). No consumer needs to change to read them, so `schema_version` at
`human_only_paths.yaml:19` is unchanged. Stated explicitly so the apply diff can be reviewed as
purely additive.

---

## 3. CRITICAL VERIFICATION — does `measurement/protocols/*.md` already cover Annex K?

The owning handoff and the staging README both say *"the existing `measurement/protocols/*.md` entry
is a glob and already covers the new annex file — verify, do not amend"* (staging README `:39`, Annex
K draft `:206-209`). This section is that verification. It was run against the live repository on
2026-08-03.

> **Evidence of record for this section.** An earlier revision cited *"the ratification bundle"* for
> the probe commands and outputs; no such bundle existed, which is precisely the defect
> `MEASUREMENT.md:146-156` was ratified to close one day earlier. The probes are therefore
> **re-runnable from this document**: every command below is written out in full, takes under a
> second, requires no inference, and mutates nothing. The apply checklist (§7) requires the operator
> to re-run them and record the exit codes in the receipt, and `apply_ratification.sh --verify`
> executes them. A finding whose evidence is a re-runnable one-second command is more durable than
> one whose evidence is a captured log, and it needs no `SHA256SUMS` because it is not a measurement.

### V1 — As DATA: YES. No new entry is needed, and adding one would be a defect.

The existing entry is `human_only_paths.yaml:32-34`:

```yaml
  - repo: epyc-root
    glob: "measurement/protocols/*.md"
    why: "MEASUREMENT v2 protocol annexes — same trust boundary as the core constitution"
```

Annex K is created at `measurement/protocols/kernel-research` (plus the `.md` extension restored at
ratification per staging README `:87-93`). That is one path segment below `measurement/protocols/`
with a `.md` suffix, so it matches `measurement/protocols/*.md` under every ordinary glob semantics —
shell, `fnmatch`, `pathlib`, and `git` pathspec alike. The `why` field already generalises to it
("protocol annexes"), and `MEASUREMENT.md:45-47` will name K in the same annex key line the entry
describes.

> **Finding V1.** Annex K requires **no** addition to `human_only_paths.yaml`, and the pin is
> unaffected by its creation: a new file matching an existing glob does not change the YAML bytes, so
> `sha256sum` over the gate list is unchanged. Adding a literal per-annex entry would be a defect,
> not belt-and-braces: it would establish that each annex needs its own line, which silently converts
> the glob into decoration and makes the *next* annex's protection depend on somebody remembering.

### V2 — As ENFORCEMENT: NO. Verified defect in the hook's layer 2. No glob entry is enforced today.

Verification was run rather than assumed, and the assumption failed. The PreToolUse guard
(`scripts/hooks/check_trust_boundary_edit.sh`, wired at `.claude/settings.json:76`) resolves each
glob against each repo root at `:89` and then compares at `:90`:

```bash
candidate=$(realpath -m "${root}/${glob}" 2>/dev/null || printf '%s' "${root}/${glob}")
if [[ "$TARGET" == "$candidate" ]]; then
```

The right-hand side is **quoted**, which disables bash pattern matching in `[[ … == … ]]`. The
comparison is therefore literal string equality against a string that still contains `*`, and
`realpath -m` normalises the path without expanding it. Probes against the live hook — **re-runnable
verbatim**, each mutating nothing:

```bash
probe() {  # $1 = absolute target path; prints the hook's exit code
  printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$1" \
    | CLAUDE_PROJECT_DIR=/workspace bash /workspace/scripts/hooks/check_trust_boundary_edit.sh \
      >/dev/null 2>&1; echo "$?  $1"
}
probe /workspace/MEASUREMENT.md                          # expect 2 (literal entry, blocks)
probe /workspace/measurement/protocols/bench-cpu.md      # expect 2; ACTUAL 0
probe /workspace/measurement/protocols/quality-eval.md   # expect 2; ACTUAL 0
probe /workspace/measurement/protocols/kernel-research.md  # expect 2; ACTUAL 0 (post-apply)
```

| Probe target | Entry that should catch it | Hook exit | Expected |
|---|---|---|---|
| `/workspace/MEASUREMENT.md` | `:26-28` (literal) | **2 — BLOCKED** | 2 |
| `/workspace/measurement/protocols/bench-cpu.md` | `:32-34` (glob) | **0 — ALLOWED** | 2 |
| `/workspace/measurement/protocols/quality-eval.md` | `:32-34` (glob) | **0 — ALLOWED** | 2 |
| future Annex K file under `measurement/protocols/` | `:32-34` (glob) | **0 — ALLOWED** | 2 |

Isolated root cause, same bash construct, both quotings:

```
candidate = /workspace/measurement/protocols/*.md
[[ "$T" == "$C" ]]  -> no match     # what the hook does today
[[ "$T" ==  $C  ]]  -> match        # pattern matching enabled
```

> **Finding V2.** Layer 1 of the three-layer enforcement stack does **not** enforce any `glob:` entry
> containing a wildcard. Annexes **B, Q and G are agent-writable through Write/Edit today**, and a
> new Annex K would be equally exposed. The literal entries (`MEASUREMENT.md`,
> `MEASUREMENT_POLICY.md`, `instrument_eras.yaml`, `autopilot_baseline.yaml`) are unaffected and do
> block correctly, and the unconditional layer-1 refusal of the gate list and its pin
> (`check_trust_boundary_edit.sh:47-66`) is also unaffected — that path needs no parsing and never
> degrades, exactly as its comment claims.
>
> **The correct repair is to the matcher, not to the YAML.** Adding literal entries for each annex
> would paper over a defect that also silences every future glob, including D1. The repair is code,
> so it cannot ride in this delta; it is an implementation obligation listed under *Residual
> dependencies*, and it MUST land with a test covering a wildcard entry — the existing suite,
> `scripts/hooks/tests/test_trust_boundary_edit.py`, contains no glob case, which is why this
> survived. Per project practice the test must also assert the **compliant** path still passes, so
> the repair does not forbid the guard's own idiom.
>
> Consequence for sequencing: until the matcher is repaired, the staging README's statement that
> `measurement/protocols/*.md` files are *"hook-blocked"* (`:9-12`) is true of the policy and false
> of the mechanism. Layers 2 and 3 are unaffected — they hash the gate list, not the annexes — so an
> edit to an annex is caught by neither. That gap predates AutoKernel and is not created by it.

### V3 — Adjacent gap, reported not proposed: the guard is not itself on the list.

`scripts/hooks/check_trust_boundary_edit.sh` and `.claude/settings.json` are the mechanism that
enforces the list, and neither is on the list. An agent can edit the hook that blocks it. This is
recorded for the operator because it is the same class of finding, but it is **deliberately not part
of this delta**: it is a bus/hook governance question that belongs to the session-bus owner, not to
AutoKernel, and folding it in would be exactly the authority creep this draft argues against.

---

## 4. Operator apply procedure — two steps, one landing

Both steps are operator actions (`human_only_paths.yaml:14-18`). Neither is performable by an agent:
layer 1 of the guard refuses Write/Edit to the gate list and its pin unconditionally
(`check_trust_boundary_edit.sh:47-66`). The operator's path is unaffected because it is an editor or
a ratify script, not the Write/Edit tools — the guard says so itself at `:22-25`.

> **Step 0 — preconditions (all MUST hold before the edit).**
> 1. `python3 scripts/coordination/session_bus.py validate` reports the trust boundary intact
>    **before** any edit, so a pre-existing drift is not silently absorbed into this amendment.
> 2. The working tree's staged set contains nothing else (`git status --short`); a shared clone
>    means another session's staged files ride into any commit made here.
> 3. **No other item in this package edits `human_only_paths.yaml`.** Verified for tonight: the
>    preflight enumerator entry is withdrawn with Stage I, and the waiver storage path rides
>    attestation 2. If that ever ceases to be true, all entries merge into one line with one terminal
>    pin (§0).
>
> *(Steps 0.1–0.3 of the earlier revision — evaluator-bundle existence, policy-directory existence,
> and digest equality — are preconditions on the DEFERRED D1/D2 entries, not on tonight's conceptual
> entries. They move to §2.1.)*
>
> **Step 1 — edit the gate list.** Apply §2a verbatim to
> `coordination/session-bus/human_only_paths.yaml`. Additive only: no existing entry is edited,
> reordered, or removed, and `schema_version` is unchanged. This is the last byte-level change; any
> further correction restarts at step 1.
>
> **Step 2 — rewrite the pin, using the command the file documents at `:15-17`.**
> ```bash
> sha256sum coordination/session-bus/human_only_paths.yaml | awk '{print $1}' \
>   > coordination/session-bus/human_only_paths.sha256
> ```
>
> **Step 3 — verify, do not assume.**
> ```bash
> python3 scripts/coordination/session_bus.py validate      # expect: trust-boundary pin intact
> ```
> `validate` returns exit 1 and prints `FAIL trust boundary DRIFT: …` if the pair disagrees
> (`session_bus.py:644-657`, `:661-686`).
>
> **Step 4 — commit both files in ONE pathspec-limited commit.**
> ```bash
> git commit -- coordination/session-bus/human_only_paths.yaml \
>               coordination/session-bus/human_only_paths.sha256
> ```
> A pathspec-limited commit is required in this shared clone so a parallel session's staged files
> cannot ride into a trust-boundary commit.
>
> **Step 5 — record the receipt** in the attestation-1 bundle: the pre-edit and post-edit gate-list
> digests, the new pin, the commit SHA, and the `validate` output. Per `MEASUREMENT.md:146-156` the
> receipt lives in-repo; a scratch path is not a citation of record.

**Apply-receipt grammar:**
`human-only path delta applied: +<n> path entries, +<n> conceptual entries, pin <sha256[:12]> [operator apply, <YYYY-MM-DDThhmmssZ>, receipt artifacts/operator/<name>.json]`

**Prospective.** These entries bind writes attempted after the pin is rewritten. They do not
retro-certify, invalidate, or re-open any prior edit to the named paths, and they create no obligation
to audit history: the paths are new, so there is no history to audit.

---

## 5. Why the two steps must land together, and what happens if they do not

`config.yaml:158-164` declares the pair and its policy:

```yaml
trust_boundary:
  source: "coordination/session-bus/human_only_paths.yaml"
  pin: "coordination/session-bus/human_only_paths.sha256"
  on_pin_mismatch: refuse
```

The pin is a content hash of the gate list, so **any** edit to the list — legitimate or not —
invalidates it. The two steps are one item, not two (owning handoff `:1793-1795`), and are presented
as a single strikeable line: a struck YAML edit with an applied pin, or an applied edit with a struck
pin, both produce drift.

Verified consequences of drift, distinguishing declared policy from implemented mechanism:

| Layer | Behaviour on drift | Evidence |
|---|---|---|
| `session_bus.py validate` | prints `FAIL trust boundary DRIFT: … the gate list changed outside the operator path. Re-pin deliberately or revert.` and returns exit 1 | `session_bus.py:661-686`, `:644-657` |
| `session_bus.py rebuild` | surfaces `trust_boundary.pin_problems` in reconstructed state | `session_bus.py:988-990`, `:1015-1016` |
| coordinator-daemon audit | emits `kind: defect`, `check: trust-boundary-pin` | `session_bus_coordinator.py:1114-1118` |
| `on_pin_mismatch: refuse` | **declared, no consumer** — a repository-wide search finds the key only at its own definition site | `config.yaml:164` |

> **Finding.** The operative behaviour today is **detect-and-report**, not refuse: nothing gates on
> the mismatch, so a drifted pin produces a failing `validate`, a defect row, and otherwise normal
> operation. The declared `refuse` is aspirational. This does not weaken the procedure — an operator
> who runs step 3 sees the failure immediately — but it MUST NOT be described as a mechanism that
> stops anything, and no part of the AutoKernel design may rely on `refuse` firing. Recorded under
> *Residual dependencies*.

Ordering hazard worth stating because it is the easy mistake: the pin must be computed **after** the
final byte of the edit. Computing the pin and then making one more whitespace correction reproduces
exactly the drift signature of a hostile out-of-band edit, and the audit cannot tell the two apart —
`session_bus_coordinator.py:1100-1105` says as much, noting that a commit touching a human-only path
*"cannot be attributed to agent-vs-operator at all, because every session commits under one git
identity"*.

---

## 6. The critical gap — this delta is NECESSARY but NOT SUFFICIENT

Stated plainly, because a partial defense that reads as a complete one is worse than a known gap.

The guard is a Claude Code **PreToolUse** hook. It intercepts tool calls and inspects
`tool_name`, acting only on `Write` and `Edit` (`check_trust_boundary_edit.sh:36-38`). AutoKernel is a
**daemon**; a candidate kernel is a **compiled subprocess**. Neither makes a tool call. Neither passes
through the hook. Layers 2 and 3 hash only the gate list itself, so they would not observe a modified
evaluator at all — the owning handoff says this at `:465-466`: *"Layer 1 blocks agent tool writes
only. AutoKernel is a daemon; a candidate binary is a subprocess. Neither passes through a PreToolUse
hook, and layers 2–3 detect after the fact."*

> **What this delta actually buys.** It closes the *agent* write path: a Claude session — including a
> session doing AutoKernel implementation work, and including one acting on a plausible-sounding
> instruction — cannot edit the evaluator bundle or the threshold policy through its tools. That is a
> real and non-trivial vector, and it is the vector every previous trust-boundary entry addresses.
> It is not the vector that matters most for a daemon.
>
> **What it cannot buy, and MUST NOT be read as buying.** It does not prevent the AutoKernel process,
> any process it spawns, a candidate binary, a build script, or a shell redirect from writing the
> evaluator bundle or the policy plane. It offers no defense against a candidate whose behaviour
> under test differs from its behaviour under measurement.
>
> **The required companion, an implementation obligation:** the evaluator bundle and the policy plane
> MUST be OS-protected against the actor's and the candidate's execution context — a **separate uid**
> whose files are not writable by the actor's uid, or a **read-only bind mount** of the bundle into
> the execution context, per owning handoff §3.6(b) (`:469-470`) and invariant 4 (`:515-516`),
> *"Actor, evaluator, and release packager are distinct authority domains even on one host, enforced
> at the OS level"*, and AK-D5 (`:2221`), *"hook-based enforcement does not reach a daemon"*.
>
> **A YAML entry cannot deliver this.** `human_only_paths.yaml` is data consumed by a tool-call hook,
> a hash check, and an audit pass. It has no mechanism to constrain a process. Ratifying D1 without
> the OS-level companion produces a boundary that is documented, audited, and inoperative against the
> actor it was written for.
>
> **Acceptance test, and it is adversarial by construction:** with the actor running under its normal
> execution context, a deliberate write to a file inside the evaluator bundle MUST fail with a
> permission error, and the attempt MUST be journaled. A test that only demonstrates the hook
> refusing a `Write` tool call does not exercise this at all — it tests the layer that was never in
> doubt. Until that test passes, D1 is a policy statement, and the release path MUST treat evaluator
> immutability as unenforced.

---

## 7. Ratification checklist (attestation 1a, this item only)

- [ ] Step-0 preconditions verified. **No path existence check is required** — §2a names no path.
- [ ] §2a applied verbatim; diff is purely additive; two `conceptual:` entries; `schema_version`
      unchanged; **no `paths:` entry added**.
- [ ] Pin rewritten with the documented command, as the last action.
- [ ] `session_bus.py validate` reports the trust boundary intact.
- [ ] Both files committed in one pathspec-limited commit.
- [ ] **Amendment mechanics** (`MEASUREMENT.md:116-118`, staging `README.md:60-71`), all four of which
      the earlier revision omitted:
      - [ ] one-line `MEASUREMENT.md` CHANGELOG entry — **verbatim text at
            `RATIFICATION_PACKAGE.md` §E**;
      - [ ] explicit supersession statement: **supersedes nothing**; adds two `conceptual:` entries
            that add no write class; prior receipt of the file's last amendment is the v2 apply
            (20260730T103218Z, `artifacts/operator/measurement-v2-draft/RATIFICATION_LEDGER.md`);
      - [ ] row in `artifacts/operator/autokernel-policy-draft/RATIFICATION_LEDGER.md` recording the
            pre-edit and post-edit gate-list digests and the new pin;
      - [ ] apply command sequence pre-validated end-to-end (`MEASUREMENT.md:143-145`) via
            `apply_ratification.sh` — every command in §4 runs against paths that exist today, so it
            is pre-validatable, which the earlier revision's version was not.
      - [ ] No `MEASUREMENT.md` §2 registry row: this item creates no protocol id.
- [ ] **V1 re-verified after Annex K lands**: the new annex file matched by
      `measurement/protocols/*.md` **as data**, with no YAML change and no pin change.
- [ ] **V2 probe re-run and its actual exit codes recorded in the receipt** (§3). Until the matcher is
      repaired the annex probes are expected to return 0, and the attestation states that plainly
      rather than implying the glob protects anything.
- [ ] **V2 repair filed** against the session-bus / hooks owner as deferred item D5, with a wildcard
      test case in `scripts/hooks/tests/test_trust_boundary_edit.py` and a compliant-path negative
      case.
- [ ] Receipt recorded in-repo per `MEASUREMENT.md:146-156`.
- [ ] Presented with the other attestation-1a items as one attestation with strikeable lines; the YAML
      edit and pin rewrite occupy **one** line.

---

## Residual dependencies

Bindings that could not be reduced to a contract or a procedure, with the reason. None is a blank
left for later calibration; each is a dependency on work outside this delta.

1. **The two path strings (D1, D2) are literals.** `schema_version:
   session_bus.human_only_paths.v1` is a flat list of literal path patterns with no indirection, so
   *"the path named in the campaign manifest"* is unrepresentable in the schema. Mitigated three
   ways: the paths are naming contracts on a deliverable that does not exist yet, so they cost
   nothing to change before apply; step 0 asserts existence at apply time; and the attestation is
   presented only after AK3, when the layout is fixed. *Not eliminable without a schema v2 that
   supports indirection, which is a larger amendment than this one.*
2. **The layer-2 matcher repair is code, not data** (finding V2). No YAML entry can make the hook
   match a wildcard. Until repaired, D1 is unenforced at layer 1 — as are the existing B/Q/G annex
   entries. Owner: session-bus / hooks. Must land with a wildcard test case in
   `scripts/hooks/tests/test_trust_boundary_edit.py`.
3. **OS-level protection is an implementation obligation** (§6). Separate uid or read-only bind
   mount, with an adversarial acceptance test. Not expressible in YAML at all; this is why D3 exists
   in the `conceptual:` block.
4. **`on_pin_mismatch: refuse` has no consumer** (`config.yaml:164`). The declared refusal is not
   implemented anywhere; the real behaviour is a failing `validate` plus a daemon defect row. Either
   implement the refusal or amend the key to describe what happens — but that is a session-bus
   amendment, not this delta. Nothing in the AutoKernel design may depend on `refuse` firing.
5. **The evaluator-bundle digest and every threshold are supplied at run time, by design.** They
   appear here as procedures and contracts — "the digest recorded in the policy bundle", "the
   noise-floor derivation recorded per campaign" — and never as values. This is a resolved item, not
   an open one; it is listed so a reviewer does not read the absence of numbers as an omission.
6. **`measurement/policy/autokernel/` is a new directory under `measurement/`.** The constitution
   declares only that normative protocol text lives in `measurement/protocols/`
   (`MEASUREMENT.md:16-21`); it does not reserve the parent, so no core-file layout amendment is
   required. The considered alternative was `epyc-orchestrator/orchestration/autokernel_policy.yaml`,
   beside `instrument_eras.yaml` and `autopilot_baseline.yaml` — rejected because owning handoff §5.1
   (`:605-609`) assigns search/release policy and evaluator-bundle hashes to the epyc-root
   constitution plane, and because a human-only file sitting among routinely agent-written
   `orchestration/` siblings invites exactly the accidental edit this list exists to stop. Flagged
   because it is a placement judgement the operator may overturn at zero cost before apply.
