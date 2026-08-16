# `coordination/evals/` — the prose-rule moratorium, and the fixtures that replace prose

**The rule, in force from 2026-08-16 (task P0-9,
[`handoffs/active/loop-owned-fleet-implementation.md`](../../handoffs/active/loop-owned-fleet-implementation.md)):**

> When a new incident or edge case occurs, you **append a labeled example to the fixtures here**.
> You **never** add a new rule, clause or conjunct to `coordination/session-bus/BUS_PROTOCOL.md`,
> `CLAUDE.md`, the shared policy files under `agents/shared/`, or any agent role file.

This is a standing constraint of the ratified Loop-Owned Fleet plan, binding on every task in it.
It has exactly three exits, and nothing else:

| Response to an incident | Allowed? |
|---|---|
| Append a labeled fixture here (+ optionally an example-pack entry) | **Yes — this is the default** |
| Add a **mechanical** check: a hook, a schema field, a test, a validator, a refusal | **Yes** — mechanism is not prose |
| Delete a rule that the incident proved does not fire | **Yes** |
| Write a new prose rule, conjunct, warning or "always remember to…" | **No** |

Amending an *invariant* is a separate act with its own gate. The fifteen invariants live in
agents/shared/INVARIANTS.md, a hash-pinned human-only path (P1-1). The moratorium governs the
**judgment layer** — the flowchart rules — not that core.

## Why: prose rules do not fire at the moment of emission

The moratorium is not a style preference. It rests on measurements the project made on itself.

**A rule was violated 3 minutes 33 seconds after being written.** Failure row F-22
([`handoffs/active/coordinator-role-failure-modes-and-refactor.md`](../../handoffs/active/coordinator-role-failure-modes-and-refactor.md)
line 106): at 10:52:06Z the coordinator pledged *"Every future dispatch from me carries the TASK TEXT
as primary and the line only as a hint … if my pointer disagrees with the text, the TEXT wins."* At
10:55:39Z — the very next dispatch, 213 seconds later — it dispatched five items keyed by
`file.md:LINE`, one of them unresolvable. The catch came from a peer main, not from the rule.
The same audit records F-02 recurring 21 and ~33 minutes after its correction was committed to git,
same session, same author.

**The diagnosis is retrieval, not decay**
([`docs/reviews/coordinator-role-audit-20260812.md`](../../docs/reviews/coordinator-role-audit-20260812.md)
lines 84-86):

> Decay is not the variable. Proximity was maximal in both cases. What failed is **retrieval at the
> moment of emission**: nothing in the act of composing a bus payload or typing a `git` command
> required a read of the place the correction lived.

**And the resulting law** (same audit, lines 184-188):

> A rule is followed at the rate at which the act it governs forces a read of it. … A paragraph in a
> file does not force anything, however recently it was written, and however close to the code that
> breaks it.

**The corpus answered failure with more of what failed.** Commit `22c4aff5` encoded the 2026-08-12
lessons as **+204 lines of prose across 8 files, of which 0 of 7 rules are enforced by any hook,
test or CI check** (same audit, lines 527-534). The instruction surface an agent is bound by measured
**1,509 lines / 252 directive-bearing lines** across `CLAUDE.md`, `agents/AGENT_INSTRUCTIONS.md`,
`agents/coordinator-agent.md`, `agents/shared/OPERATING_CONSTRAINTS.md`,
`agents/shared/SESSION_LIFECYCLE.md`, `agents/shared/MEASUREMENT_POLICY.md`,
`coordination/session-bus/BUS_PROTOCOL.md` and the coordinator skill (same audit, lines 57-63).
Corpus-wide anchor rot inside that surface rose from 27% (2026-07-29) to 51% over twelve days
([`wiki/agent-architecture.md`](../../wiki/agent-architecture.md) line 209) — the corpus was decaying
faster than it was being read.

The plan of record states the headline as **"doctrine corpus ~67% incident patch; ~40 incidents each
minted a standing rule"**, growing without converging
(`docs/design/loop-owned-fleet.html` line 212).

> **Provenance note, recorded here deliberately.** That 67% is an assertion of the six-reader audit
> whose working notes were never persisted: no denominator, method or date for it exists in the
> repo. By this directory's own standard it is `ledger-narrative`. The moratorium does not rest on
> it — it rests on F-22 (3m33s), F-02 (21 min), the +204-lines/0-of-7-enforced count and the
> 1,509-line corpus measurement above, all of which are `primary-artifact`. Stating this in the
> README is the point: a document about label provenance that launders an underived number would
> refute itself.

An example does not need to be recalled. It is *in the prompt* at the moment the decision is made.
That is the entire substitution.

## Layout

```
coordination/evals/
├── README.md                        this file — the moratorium
├── validate_fixtures.py             stdlib-only validator (run it before you commit a fixture)
├── fixtures/
│   ├── fixture.schema.json          the labeled-example contract
│   └── <decision>.json              the corpus, one file per decision
└── examples/
    ├── README.md                    how packs are built from fixtures
    └── <decision>.md                the few-shot pack injected into that classifier's prompt
```

## The fixture format

One JSON object per labeled example (files may hold a single object or an array). Schema:
[`fixtures/fixture.schema.json`](fixtures/fixture.schema.json). Every field is required.

| Field | What it holds |
|---|---|
| `id` | `<decision>-NNN`. Stable, never reused — packs and promotion records cite it. |
| `decision` | Which classifier this trains, e.g. `premise_screener`. One ladder per decision. |
| `input` | The evidence bundle **as the classifier sees it at decision time**: `presented` (the row text verbatim), `asserted_state` (the premise under test), `source_hint`, `context`. No hindsight, no answer leakage. |
| `label` | The ground-truth verdict on that decision's forced-choice ladder. |
| `label_provenance` | **Where the label came from.** `primary-artifact` \| `operator` \| `ledger-narrative`. |
| `evidence_ref` | Path (`:LINE`) and/or commit that **proves** the label. Never a restatement of it. |
| `created` | ISO date the fixture was labeled. |
| `notes` | What makes this example discriminative — the feature the classifier must learn. |
| `promotion_gating` | Optional. **Defaults to true** — opting out is explicit, so every `ledger-narrative` fixture must carry `"promotion_gating": false`. Defaulting it to false for `ledger-narrative` was rejected: that would make the gate vacuous, firing only on fixtures whose author had already set the flag. |

### `label_provenance` is the load-bearing field

Adversarial-review finding **R7** of the plan of record:
*"Eval labels contaminated — **the ledger graded itself**"* (`docs/design/loop-owned-fleet.html`
line 491). The concrete measurement behind it, open task A-7
(`handoffs/active/coordinator-role-failure-modes-and-refactor.md` lines 465-470):

> **Half the recurrence counts in this file are the coordinator's own tally of its own errors**,
> which is the least trustworthy possible source.

And why that is structural, not sloppiness (audit lines 521-525): the operator writes **0 of 839**
bus rows; every operator correction arrives through a tmux pane and its only durable form is
*whatever an agent chooses to transcribe — and the transcriber is the party the correction indicts.*

Therefore:

- **`primary-artifact`** — the label is proved by a thing that is not a narrative: a file's contents
  at a line, a commit, a config value, a symlink's type, the presence or absence of a test. Gating.
- **`operator`** — the label is the operator's own recorded verdict. Gating.
- **`ledger-narrative`** — the label comes from a handoff, progress note or ledger describing itself.
  **Advisory only.** It may seed a few-shot pack; it may never gate a classifier promotion.
  `validate_fixtures.py` fails the run if a promotion-gating fixture carries it.

A `ledger-narrative` fixture is not a defect — it is an honest marker that says *this one needs
re-labeling from a primary artifact before it counts.* That re-labeling is PN-1's precondition.

## How fixtures become few-shot examples

Fixtures are the durable, machine-checkable **corpus**. Example packs in
[`examples/`](examples/README.md) are a **curated projection** of it: the subset chosen as
demonstrations, rendered as prompt text, each citing the `id` of its fixture so any demonstration
traces back to the artifact that proves its label.

At runtime a classifier — the first is `premise_screener` (P2-2), forced-choice
`still-needed | stale | UNKNOWN` with a mandatory evidence quote — is prompted with its pack's
positive, negative and near-miss examples ahead of the live input. Promotion of any classifier to
authority is gated on the fixture corpus, scored on `primary-artifact` and `operator` labels only,
with precision measured **against a recall floor so that silence cannot score** (PN-1). The eval CI
runner (PN-3) is pulled by need, when the first promotion requires it; the fixtures exist from now
regardless, because the write side is cheap and permanent and the read side cannot be retrofitted.

## Adding a fixture

1. Write the example into `fixtures/<decision>.json`, `input` containing only what the classifier
   would have at decision time.
2. Find the **primary artifact** and put it in `evidence_ref` — go look at the file, the commit, the
   symlink. If you cannot reach one, label `ledger-narrative`, set `"promotion_gating": false`, and
   say in `notes` why not.
3. Run the validator:

   ```bash
   python3 coordination/evals/validate_fixtures.py
   ```

4. If the example teaches something a pack does not yet demonstrate, add it to
   `examples/<decision>.md`, citing its `id`.
5. Do **not** also write a rule about it. That is the whole moratorium.
