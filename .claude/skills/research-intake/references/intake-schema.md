# Intake Index Entry Schema

Each entry in `research/intake_index.yaml` follows this schema.

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID, format `intake-NNN` (zero-padded 3 digits) |
| `arxiv_id` | string or null | arXiv identifier (e.g., `"2402.12374"`). Primary dedup key. Null for non-arXiv sources. |
| `url` | string | Source URL |
| `source_type` | enum | `paper`, `blog`, or `repo` |
| `title` | string | Title of the work |
| `categories` | list[string] | 1+ category keys from `taxonomy.yaml` |
| `novelty` | enum | `high`, `medium`, `low`, or `duplicate` |
| `relevance` | enum | `high`, `medium`, `low`, or `none` |
| `discovered_via` | enum | `seed`, `input`, `expansion`, or `search` |
| `verdict` | enum | `new_opportunity`, `already_integrated`, `worth_investigating`, `not_applicable`, `superseded`, `adopt_patterns`, or `adopt_component` |
| `ingested_date` | string | ISO date (YYYY-MM-DD) |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `authors` | list[string] | Author names |
| `key_claims` | list[string] | 3-5 key claims extracted from the work |
| `techniques` | list[string] | Named techniques introduced or applied |
| `reported_results` | list[string] | Key metrics/results reported |
| `cross_references` | object | Cross-reference targets (see below) |
| `expanded_from` | string or null | ID of the entry this was expanded from |
| `recommended_actions` | list[string] | Suggested follow-up actions |
| `credibility_score` | integer or null | Source credibility score (0-6). Rubric: peer-reviewed +2, recent +1/old -1, authority +1, bias -1, corroboration +1/source max +2. Null for repos/blogs without empirical claims. |
| `contradicting_evidence` | list[string] or null | Contradicting evidence found during Tier 2b search. Null if none found or search not performed. |
| `handoffs_updated` | list[string] | Active handoff filenames amended with insights |
| `handoffs_created` | list[string] | New stub handoff filenames created |
| `citation_context` | string | Surrounding text where this was cited (seed entries only) |
| `notes` | string | Free-form analysis notes, deep-dive findings, revision history |
| `verification` | enum | `stage1-unverified` (default on Stage-1 persist) · `dive-verified` · `dive-overturned`. **Set by Stage 1; promoted only by a Stage-2 dive that read primary source.** |
| `reader_should_conclude` | string | A **directive to a future agent**, not prose for a human: what a reader consulting this entry should take away and what they must not. See below. |
| `dive_corrections` | string | Dated record of what a Stage-2 dive changed, so an overturned conclusion cannot be re-derived. Append-only. |
| `integration_disposition` | enum | Workflow disposition: `integrated`, `knowledge_only`, `monitor`, `declined`, or `awaiting_dive`. This describes how the source is handled; `integrated` means routed into a durable owner, not necessarily deployed code. |
| `disposition_evidence` | list[string] | One or more repository-grounded reasons for the disposition. Required whenever `integration_disposition` is present. |
| `locator_note` | string | Why this entry has no `url` and no `arxiv_id`. See below. |
| `claim_anchors` | list[object] | Per-claim span anchors recorded at dive time. See below. |

## `locator_note` — the honest empty-URL case (added 2026-08-09)

`url` is required, but a 2026-08-09 audit found **9 entries** whose `url` was present with a null
value — accepted because the validator checked key *presence*, not non-emptiness. All nine turned
out to be legitimate: `discovered_via: input` operator-supplied inline material (a pasted write-up,
a social post, a screenshot pair, a local `src.zip`). No canonical URL exists, and inventing one
would be strictly worse than leaving it blank.

So the rule is **locatability**, not URL-presence: an entry must carry a non-empty `url`, a
non-empty `arxiv_id`, **or** a `locator_note` saying why neither exists and where the material
actually came from. The validator enforces exactly that and rejects an entry satisfying none of the
three.

Write the note so a future reader can find the material or know that they cannot:

```yaml
locator_note: 'Operator-supplied inline material: two screenshots at epyc-root/tmp/HMViJC-WIAAkUTU.jpeg
  and HMVh-pCWkAAklkX.jpeg (filenames consistent with Twitter/X media). arxiv_id is deliberately null
  so the FAKE claimed ID cannot false-positive a dedup sweep.'
```

An entry whose only locator is a note is, by construction, **unanchored** — nothing can be
retrieved from it — and any downstream consumer should treat it accordingly.

## `claim_anchors` — recording the span a dive actually read (added 2026-08-09)

A Stage-2 dive reads a specific passage. `key_claims` records what it concluded; `claim_anchors`
records **where it read it**, which is otherwise lost the moment the dive ends.

```yaml
claim_anchors:
  - claim_index: 0                      # index into key_claims
    kind: page-and-quote                # page-and-quote | heading-and-hash | json-pointer | line-range | file-hash
    locator: 'p.98, §4.5'               # human-resolvable pointer within the source
    quote: 'Property 13 (Deletion). For every provenance semiring Prov(X)...'
    quote_sha256: '<hex of the normalized quote>'
    source_revision: 'arXiv:2202.10766v1'   # the revision the quote was read at
    verified_by: 'research-intake/stage2'
```

**Why this field exists.** Without it an entry identifies a *document*; with it, an individual claim
identifies a *location*. That distinction is the entire difference between a claim a reader can
check and one they must take on trust, and it is measurable: a 2026-08-09 pass over all 1,067
entries found that **zero** claims could reach an anchored grade, because no entry carried a
per-claim span. Recording the anchor at dive time — when the author has the passage open — costs
seconds; reconstructing it later costs a re-read, and often is not possible at all.

Anchors are optional and per-claim: record them for claims that will be cited, gate a decision, or
enter an authoritative projection. Ordinary prose does not need one.

## `claim_corrections` — which claims a correction actually touched (added 2026-08-10)

`dive_corrections` is prose. It says a dive changed *something* about the entry, and no program can
read which claim. The consequence was measured on 2026-08-10: **27 `dive-overturned` entries
blanket-opposed 114 claims**, and **155 prose corrections blanket-flagged 681**. intake-896 is the
case — four claims, one fabricated, all four opposed for fifteen days.

Record the verdict per claim while the dive is open:

```yaml
claim_corrections:
  - claim_index: 3
    effect: overturned          # overturned | narrowed | reattributed | unaffected
    note: 'FABRICATED. The four-step /doctor description does not exist in the product.'
  - claim_index: 0
    effect: unaffected
    note: 'The 80% system-prompt figure was never disputed; the retraction covers claim 3 only.'
```

**`unaffected` is the load-bearing member.** Without a way to say "this sibling survived", the only
expressible position is blanket doubt, and blanket doubt is what makes a correction destroy good
work next to bad. Recording it is also what separates *examined and cleared* from *nobody looked* —
only the first should stop a future dive re-litigating the claim.

What each effect does:

| Effect | Ledger consequence |
|---|---|
| `overturned` | opposition edge on that claim alone |
| `narrowed` / `reattributed` | review-required; **not** opposition — a narrowed claim is not a false one |
| `unaffected` | support stands; the claim is excluded from the correction's `claim_ids` |
| `uncertain` | a reader examined the prose and it still does not say; keeps the entry-level verdict and clears nothing |
| *(no record)* | falls back to blanketing every claim, which stays the honest default for unindexed prose |

`uncertain` and *no record* are not the same thing, and the difference is worth the field. One says
somebody looked and the prose was silent; the other says nobody looked. Only the first should stop
a future reader repeating the work.

`note` is required on every row. An unexplained per-claim verdict cannot be reviewed or overturned
later, and the adapter still refuses to PARSE `dive_corrections` prose — keyword-scanning for
"OVERTURNED" would be deterministic, plausible, and sometimes wrong.

## `depends_on` — the edge that actually propagates (added 2026-08-10)

A `cross_references.intake_entries` pointer means "related reading". It does **not** mean this
entry's claims rest on that entry's claims, and it must never be read that way — measured on
2026-08-10 over a 60-edge sample stratified across the 672 citation edges from dived entries,
**18% were evidential, 75% topical, 7% companion artifact**. Treating citation as dependency would
have created roughly 550 false dependencies, and a false dependency is worse than a missing one: it
propagates invalidation into work that never depended on anything.

So dependency is its own edge, written only when it is real:

```yaml
depends_on:
  - entry: intake-1039           # the entry this one's claims rest on
    claim_index: 2               # optional: which of THIS entry's claims depends
    why: 'Our Cor 4.7 restatement is only valid for semirings satisfying their Deletion Property.'
```

**Write it during Stage 2, while the dive is open.** The test is counterfactual and takes a second
to apply:

> If that entry's claim were retracted tomorrow, would a claim in this entry have to change?

Yes → `depends_on`. No → leave it in `cross_references`. "Same topic", "cites it in related work",
"we found this via that" are all **no**. A survey citing the work it surveys is **no**. A paper
whose result is only valid under another paper's theorem is **yes**.

Two mechanical shortcuts were tried against the same 60-edge sample and both failed — naming the
target entry in the claim text (precision 0.50, recall 0.09) and verification-language keywords
(0.50 / 0.27). There is no way to recover this later from what the index records, which is why it
is a write-time field: seconds during the dive, unreconstructable afterwards.

**`located_by: machine` (added 2026-08-10).** An anchor produced by matching a claim's terms
against the fetched source — rather than by a person reading the passage — MUST carry
`located_by: machine`. It then tops out at `T2 MachineLocated`, strictly below `T3 Anchored`,
however complete the rest of the record is (spec §4.2 amendment). A quote hash and a revision make
a machine match *checkable*; they do not make it *read*, and the level above records a person's
judgment that the passage says what the claim says. Omit the field for human anchors.

## Integration disposition lifecycle (added 2026-08-05)

Actionable verdicts (`worth_investigating` and `new_opportunity`) need an explicit
workflow disposition once their initial review ages past the intake window:

| State | Meaning | Required companion metadata |
|---|---|---|
| `integrated` | Routed into a durable active/completed handoff owner. This does **not** by itself claim code deployment. | `handoffs_created` or `handoffs_updated`; `disposition_evidence` |
| `knowledge_only` | Retained as architecture, methodology, or comparison context with no implementation task. | `disposition_evidence` |
| `monitor` | No current task; revisit only when the stated trigger or feasibility condition changes. | `disposition_evidence` naming the trigger/posture |
| `declined` | Reviewed and intentionally closed as non-authoritative, negative, superseded, or otherwise not worth pursuing. | `disposition_evidence` naming the reason |
| `awaiting_dive` | Still plausibly actionable, but Stage 2 primary-source verification has not happened. | `verification: stage1-unverified`; `disposition_evidence` |

A wiki citation is discovery evidence, not implementation evidence. It may support
`knowledge_only`, `monitor`, or `awaiting_dive`; it must not be used alone to infer
`integrated`.

## Cross-References Object

```yaml
cross_references:
  chapters: ["01-speculative-decoding.md"]
  handoffs: ["tree-speculation-numa-drafting.md"]
  experiments: ["specexec-verification-profile.md"]
  intake_entries: ["intake-003"]
  intake_entry_notes: ["intake-003 (SpecExec — the verification-profile source)"]
```

### `intake_entries` must contain BARE IDs only (enforced 2026-08-09)

`intake_entries` is the **citation graph**. Every value must be an exact, resolvable `intake-NNN`
that exists in the index — nothing else. No annotation, no parenthetical, no free prose, no
`intake-?` placeholder.

Put the annotation in **`intake_entry_notes`**, an optional sibling list of free-form strings. The
convention is to lead with the ID (`"intake-261 (Skill0 — RL-based skill internalization)"`) so the
note stays greppable, but nothing parses it — it is for human readers.

**Why this is enforced.** Before the 2026-08-09 migration, **458 of 1,952 cross-reference values
(23.5%), across 133 entries, did not resolve** — overwhelmingly annotated IDs of the form
`intake-261 (Title…)`. Any consumer building a citation graph silently dropped roughly a quarter of
the edges, and the most-cited-entry ranking that a backfill was scoped from was wrong as a result. A
second, sharper failure: eight of those annotations contained an unquoted `:`, so YAML parsed the
list item as a **mapping** rather than a string, and the value stopped being a string at all. The
migration normalised every value to a bare ID and preserved all 458 annotations verbatim in
`intake_entry_notes`; nothing was discarded.

## ID Sequencing

IDs must be sequential: `intake-001`, `intake-002`, etc. The `seed_index.py` script assigns initial IDs. New entries appended by the skill continue the sequence.

**Gaps left by a merge are permanent. Never renumber to close them.** An intake id is a stable
identifier, not an index into an array, and it is load-bearing well outside this file. Measured
2026-08-10, closing the four gaps the D5 merges created would have meant:

| | |
|---|---:|
| Entries needing a new id | 728 (everything above the first gap) |
| References to rewrite outside the index | 5,565, across 479 files |
| Distinct ids embedded in Vidya ledger claim/source identifiers | 731 of 1,067 |

Two reasons that is a no, and the second holds even if the first ever stops applying:

1. **The ledger cannot be renumbered.** Claim ids are `clm_intake_939_00` and source ids are
   `src_intake_939`, so changing an entry number changes the frame content, hence its
   content-addressed `frame_id`, hence the hash chain the published checkpoint attests to.
   Renumbering means rewriting an append-only log whose whole purpose is that it cannot be
   rewritten.
2. **A reused id is worse than a missing one.** If intake-940 becomes intake-936, then
   "intake-939" in an older handoff still resolves — to a *different paper*. That is not a dangling
   reference anyone notices; it is a silent misdirection inside the citation graph. A gap is a
   benign absence.

Gaps cost nothing operationally, and the mechanism is one function in one file — the sequencing
check is the ONLY place in the codebase that assumes contiguity; everything else iterates the entry
list. A surviving entry declares what it absorbed:

```yaml
merged_ids:
  - intake-785          # structured, for the validator
merge_history:
  - 'Merged intake-785 on 2026-08-10 (handoff D5): same locator; 4 claims folded in.'
```

`merged_ids` is what the allowance reads; `merge_history` is prose for the reader. Deriving the
allowance from the prose — as the first version did — makes a validation rule depend on how
somebody worded a sentence. A gap is accepted only where some entry names that exact id, so a
genuine skip, a duplicated id, and a gap "excused" by declaring an unrelated id all remain errors
(`tests/skills/test_research_intake_id_sequencing.py`).

### The redirect map

Refusing to renumber is only defensible if a removed id stays **recoverable**. A reference in a
July progress log has to be answerable, or "resolves to nothing" is just a slower kind of broken.
So every merge is published in [`research/intake_merge_map.md`](../../../../research/intake_merge_map.md):

| Removed | Resolves to |
|---|---|
| `intake-797` | `intake-418` |

The map is **generated** from `merged_ids`, never hand-kept — a redirect table that drifts is worse
than none, because it answers confidently and wrongly:

```bash
.claude/skills/research-intake/scripts/resolve_intake_id.py intake-797     # one lookup
.claude/skills/research-intake/scripts/resolve_intake_id.py --write-map    # regenerate
.claude/skills/research-intake/scripts/resolve_intake_id.py --audit        # where each is still cited
```

`validate_intake.py` fails if an absorbed id is missing from the map, so a merge cannot quietly
skip publication.

**Resolution is a lookup, not a rewrite.** Do not bulk-repoint references to a merged id. Checked
on 2026-08-10: `handoffs/active/mi210-speed-campaign-summary.md` cites `intake-797` inside a
correction recording that intake-797 was a *mis-stamped* id, and `research/recommendations.md`
uses "intake-779 through intake-797" as a range naming a historical ingest batch. Repointing either
would have corrupted a correct record. A reference to a removed id is not automatically wrong.

## Deduplication

- Primary key: `arxiv_id` (exact match), **normalized** — a bare id and an arXiv URL are the same
  source, and `v2` suffixes do not distinguish papers
- Secondary: `url` (normalized: scheme, `www.`, and trailing slash ignored)
- **A duplicate is not persisted as an entry** — record the re-encounter on the existing entry and
  stop. See SKILL.md §2b; `novelty: duplicate` is a label on pre-2026-08-10 history only

## Schema versioning & permissive consumption (added 2026-06-20, intake-710/711)

The intake index follows a **permissive-consumption contract**: `validate_intake.py`
validates the REQUIRED fields and enum values listed above, but PRESERVES
unknown/extra keys — it does not reject an entry for carrying fields beyond the
required set. This makes new optional fields forward-compatible: a field can be
added by one agent without breaking validation for parallel agents that do not
yet know about it.

The taxonomy and this schema are versioned (`schema_version: "1.0"`) so consumers
can detect drift. See `wiki/SCHEMA.md` → `## Conformance` for the canonical
statement of both the version stamp and the permissive-consumption contract.


## Verification lifecycle (added 2026-07-25)

Every entry carries a `verification` state:

| State | Set by | Meaning |
|---|---|---|
| `stage1-unverified` | Stage 1 persist | Extracted from a fetch/summary pass. Claims are **provisional**. |
| `dive-verified` | Stage 2 dive | Claims checked against primary source (quoted `file:line` or passage). |
| `dive-overturned` | Stage 2 dive | A load-bearing claim was falsified; see `dive_corrections`. |

**The unverified contract.** No number, quoted metric, or named mechanism from a
`stage1-unverified` entry may be quoted in a Stage-3 plan item or a handoff task line. It must first
be promoted by a dive.

**Why this exists.** On 2026-07-25 two Stage-1 summariser agents invented specifics that were
persisted to the index and read as evidence: a paper ablation whose four numbers appear nowhere in
the paper (and which had additionally been cross-pasted into an *unrelated* entry), and a four-step
tool behaviour absent from its source, which contained two generic sentences. Both survived until a
Stage-2 dive read the primary sources. The `verification` field makes that provisional status visible
instead of invisible.

## `reader_should_conclude` (added 2026-08-09)

An optional, **directive** field. `verdict_justification` explains a decision to a human reviewer;
this tells a future agent what to do with the entry. It exists because the expensive failure mode is
not a missing entry, it is a correct entry whose conclusion gets **re-derived wrongly** by the next
reader.

Rules:

- **Write it as an instruction, not a summary.** "Cite the stage list; never cite the L4 occupancy
  figures" — not "this entry describes a profiling session".
- **Say what must NOT be carried**, not only what may be. Most re-derivation errors are over-claims.
- **Never write an affirmative conclusion on a `stage1-unverified` entry.** The only legitimate value
  there is a prohibition ("unverified — do not cite any figure"). Writing an authoritative-sounding
  conclusion on an unverified entry is precisely the failure this field exists to prevent.
- **It does not replace `verdict`, `verdict_justification` or `dive_corrections`** and must not
  contradict them. If it would, the dive was incomplete — fix the dive.

Adopted from the SGLang profiler catalog's "Skill should conclude" column (intake-1029), where the
pre-written verdict is what keeps the classification deterministic at read time.

**Cross-contamination check.** Before persisting, verify each entry's `key_claims` and
`reported_results` reference only its **own** source. A figure belonging to a different entry is a
defect, not a stylistic issue.
