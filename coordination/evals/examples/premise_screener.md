# Example pack — `premise_screener`

Few-shot content for the P2-2 premise screener: the point LLM call in `worker_runner.py`'s preflight
that decides, forced-choice, whether a backlog row's premise still holds before a worker is spawned
against it.

**Ladder:** `still-needed` | `stale` | `UNKNOWN`, with a mandatory evidence quote.
`UNKNOWN` and `stale` park the row and emit a routed fix task.

**Why this decision exists.** A screener proves a row is WELL-FORMED, not STILL-NEEDED. Rows are
dispatched by task TEXT, not by `file.md:LINE`, because line anchors rot — measured corpus-wide at
27% on 2026-07-29 rising to 51% twelve days later. A well-formed row pointed at work the world has
already done wastes a whole worker invocation and, worse, can undo it.

**Fixtures:** `../fixtures/premise_screener.json`. Every example below cites the fixture `id` that
carries its label, its `label_provenance` and its `evidence_ref`.

---

## The procedure the examples demonstrate

1. Read the row's **task text** as the identity. The `source_hint` is a hint; if text and pointer
   disagree, the text wins.
2. Enumerate **every conjunct**. A row with three asks has three premises.
3. For each, name the **probe that would settle it** — file contents at a line, a commit, `git
   ls-files`, a symlink test, a count, an absence over several spellings.
4. Run the probe against the **primary artifact**. Not against prose in the same document.
5. `stale` only if **every** conjunct is dead. `still-needed` if any survives. `UNKNOWN` if the
   premise's subject is not something an artifact can settle.

---

## POSITIVE examples — label `still-needed`

### P1 — the plain case (fixture `premise_screener-001`)

> **Row:** "P0-7 Bus runtime off-tree (D5) … `queue.jsonl`, `advisory.jsonl`, `claims/` … move to
> `/mnt/raid0/llm/bus-runtime/`."

**Probe:** is `coordination/session-bus/queue.jsonl` a symlink?
**Result:** regular file; `/mnt/raid0/llm/bus-runtime/` does not exist.
**Verdict: `still-needed`.** Evidence quote: *"queue.jsonl — test -L reports REGULAR_FILE."*
*Teaches:* a premise asserting a filesystem shape is decidable in one probe. Reach for the probe.

### P2 — measurement confirms the asserted numbers (fixture `premise_screener-007`)

> **Row:** "P0-3 Ghost-state sweep … enumerate the 14 INFRA_BLOCKED rows + 11 dead-owner
> CLAIMED/RUNNING/STALE_REQUEUED rows and claims."

**Probe:** fold `queue.jsonl` to the latest record per `task_id`, then count by status.
**Result:** INFRA_BLOCKED = 14; CLAIMED 4 + RUNNING 1 + STALE_REQUEUED 6 = 11. Both exact.
**Verdict: `still-needed`.**
*Teaches:* old rows are not presumptively stale. This is the positive control against N2 below —
same premise class, opposite outcome. Note the reduction: the log is append-only, and counting raw
lines (235) instead of folded tasks (38) gets every number wrong.

### P3 — the target files are named, so the screen is a lookup (fixture `premise_screener-008`)

> **Row:** "P2-10 Belief-kernel wiring … Add the source row to `scripts/vidya/adapters/README.md`
> and the wiring task to `handoffs/active/vidya-belief-substrate-program.md`."

**Probe:** grep both named files for the producers the row lists.
**Result:** no match in either, across several distinct keys.
**Verdict: `still-needed`.**
*Teaches:* when a row states where the change lands, screen by lookup, not by judging whether the
work sounds done. And take a negative over **several spellings** — a single-key miss is not absence.

---

## NEGATIVE examples — label `stale`

### N1 — the identifier survives only in its own obituary (fixture `premise_screener-004`)

> **Row:** "DP-3 (MED): `bus_supervisor.sh`'s stale-source check is mitigated by a config constant,
> not fixed. `STALE_SRC_SKEW_S=5` (`scripts/coordination/bus_supervisor.sh:362`) exists because …"

**Probe:** read the cited line; grep the constant.
**Result:** `grep STALE_SRC_SKEW_S` **hits** — at line 334, inside the comment *"H-4 (2026-08-12).
THE MTIME PREDICATE IS GONE ON PURPOSE … All three are deleted."* Line 362 now holds
`git rev-parse HEAD:scripts/coordination`. Commit `bc6dc77f` replaced the whole predicate.
**Verdict: `stale`.**
*Teaches:* **a grep hit is not a live identifier.** The token survived in the comment documenting its
removal, so presence-grep alone inverts the answer. Read the cited line and read what it says.

### N2 — the asserted quantity is wrong, and the sub-boxes say so (fixture `premise_screener-005`)

> **Row:** "C38 (NEW) — `advisory.jsonl` is 1,028 MiB / 2,986,358 rows and the daemon re-parses it in
> full every tick."

**Probe:** measure the file; read the nested checkboxes.
**Result:** 64.9 MiB / 145,058 rows — wrong by ~16× and ~20×. The tick-path conjunct carries a ticked
sub-box and commit `2e01d5dd`.
**Verdict: `stale`.**
*Teaches:* when a row asserts a number, go measure the number. And read **nested** boxes — a parent
box left open above ticked children is bookkeeping residue, not a live premise.

### N3 — the destructive row that confirms itself (fixture `premise_screener-011`)

> **Row:** "P1-9. Delete-candidate: `scripts/server/quarter_scheduler.py` — 403 lines, **zero runtime
> importers**, and now factually wrong about the machine. Confirm the two test-only references
> (`tests/unit/test_dynamic_stack.py:177`, `tests/unit/test_stack_templates_v2.py:234`) and delete."

**Probe:** check all three claims, and check the row's own citations.
**Result:** "zero runtime importers" is **true** — and irrelevant: production couples to this module
through a purpose-built DS-6 **API** at three live sites (`round_robin.py:119`,
`concurrency_aware.py:1718-1730`, `stack_migration.py:14-15`), not through an import of its name.
"Two test-only references" is false. "Factually wrong about the machine" is false — quarters are
*unused since W1*, i.e. parked, not wrong. And the cited anchor `:234` is an unrelated docstring;
the real line is `:322`, asserting `ds6_quarter_scheduler == "parked_until_static_prewarm_gap"`, so
"fixing" the anchor would break a governance contract. The module now carries a banner:
*"PARKED — NOT DEAD CODE. DO NOT DELETE."*
**Verdict: `stale` / refuted.**
*Teaches:* the highest-stakes shape in the corpus — **a wrong `still-needed` here deletes working
code.** A true-but-irrelevant metric can carry a false conclusion; coupling is not always an import;
and a row that helpfully supplies its own confirmation checklist is not thereby confirmed.

### N4 — well-formed, well-cited, and dead in a day (fixture `premise_screener-012`)

> **Row:** "P1-1. Generalise the `placement_policy` enum vocabulary … Rename to shape-agnostic
> (`BURST_PREFER_SPLIT`) with an **alias map** … `_coerce` returns `None` on an unknown string …
> Fix that too, or the alias map hides its own failures."

**Probe:** open `src/scheduling/placement_policy.py`.
**Result:** all three conjuncts already landed — `BURST_PREFER_SPLIT` at `:67`, the alias map at
`:112`, `raise ValueError(` inside `_coerce` at `:144` — in commit `270cf9ea`, **one day** after the
row was written.
**Verdict: `stale`.**
*Teaches:* **recency is not freshness, and quality is not liveness.** This row is specific, correct
at authoring time, and cites its own file and line; nothing in its form signals staleness. Only the
lookup settles it. Compare P2, where an equally specific row measures out true.

---

## NEAR-MISS examples — the ones that look like the other label

These are the discriminative core of the pack. Each one a plausible screener gets backwards.

### X1 — the deliverable exists on disk and the row is still live (fixture `premise_screener-002`)

> **Row:** "P0-0 Copy the plan of record into `docs/design/loop-owned-fleet.html`; future amendments
> edit the in-repo copy first" — stated purpose: *so the plan of record is in-repo and versioned.*

**Looks:** `stale` — the file is right there, 47 KB of it.
**Probe:** `git ls-files --error-unmatch docs/design/loop-owned-fleet.html` → **fails. UNTRACKED.**
**Verdict: `still-needed`.**
*Teaches:* resolve cited deliverables against **git**, not the filesystem — an untracked file is
byte-identical to a committed one on disk and satisfies none of "versioned". Read the row's purpose
clause, then choose the probe that tests the purpose.

### X2 — half the row is genuinely fixed (fixture `premise_screener-003`)

> **Row:** "P0-4 Fix `backfill_supervisor.sh` undefined `health_ok` (loop mode always takes the
> failure branch); add a test that exercises `loop` — THE consumer, not A consumer."

**Looks:** `stale` — open the file and `health_ok` is defined right there at line 204.
**Probe A:** grep the test tree for `backfill_supervisor`. **Nothing** — conjunct two is untouched.
**Probe B:** `git show HEAD:scripts/coordination/backfill_supervisor.sh` — **no definition at all**,
only calls at :300 and :306. The repair is another session's uncommitted +130-line diff.
**Verdict: `still-needed`**, on both grounds.
*Teaches:* two things at once. **Partial satisfaction is not stale** — a screener that stops at the
first satisfied clause destroys the surviving work. And **the working tree is not git** — reading the
checked-out file shows a fix that HEAD does not have, which is how a check silently targets state no
one else can see. Enumerate every conjunct, settle each against HEAD, and name the state you read.

### X3 — the absence was searched at the wrong root (fixture `premise_screener-006`)

> **Row:** "P0-8 `.orphan` worktree disposal (D7): archive tarball → verify each orphan tip is
> contained in a lane branch → delete by explicit path list."

**Looks:** `stale` — `ls worktrees/*.orphan*` from the repo root matches nothing, and a sibling row
even asserts *"its `.orphan` backup was handled in P0-8."*
**Probe:** search the real worktree root, `/mnt/raid0/llm/worktrees/`. **Five orphans, all extant.**
**Verdict: `still-needed`.**
*Teaches:* a no-match on the wrong path is not an absence, and a sibling row's presupposition is the
weakest witness in the building — here it is simply false.

---

## `UNKNOWN` example

### U1 — the premise's subject is a running process (fixture `premise_screener-009`)

> **Row:** "P0-5 Verify the H-4 SHA deploy-marker predicate is what the RUNNING bus_supervisor
> executes (`ps -o lstart` vs commit time of `bc6dc77f`); restart if stale."

**Looks:** `stale` — the H-4 predicate is plainly present in the source, `bus_supervisor.sh:331-368`.
**But:** the row does not ask what the source contains. It asks what a **process** is executing. No
artifact in the repo records the start time or loaded code of a live process.
**Verdict: `UNKNOWN`** → park the row, emit a routed runtime-observation task.
*Teaches:* abundant evidence that is **off-target** is not evidence. When the premise's subject is
runtime state, a confident label is the failure mode; `UNKNOWN` is the correct, informative output.

---

## Advisory example — NOT promotion-gating

### A1 — `label_provenance: ledger-narrative` (fixture `premise_screener-010`)

> **Row:** "A-7 — Rule on the durability gap … **Half the recurrence counts in this file are the
> coordinator's own tally of its own errors**, which is the least trustworthy possible source."

**Verdict: `still-needed`** — but the label rests on the ledger and the audit of it, because the
premise is *about* that ledger's self-grading and no independent artifact exists. The audit gives the
structural reason: the operator writes 0 of 839 bus rows, so every operator correction survives only
as *"whatever an agent chooses to transcribe — and the transcriber is the party the correction
indicts."*

> **This example may be shown to the model. It may never gate a promotion.** It carries
> `"promotion_gating": false`, and `../validate_fixtures.py` fails the run if that is removed.
> It becomes gate-eligible only when re-labeled by the operator or against a durable correction
> record — which is exactly what row A-7 is asking someone to build.

---

## Class balance

| Label | Examples here | Fixtures |
|---|---|---|
| `still-needed` | P1 P2 P3 X1 X2 X3 A1 | 7 |
| `stale` | N1 N2 N3 N4 | 4 |
| `UNKNOWN` | U1 | 1 |

**This distribution is a property of the seed corpus, not of the world, and must not be read as a
prior.** The rate at which real backlog rows go stale is *not currently known*, and the pack says so
deliberately rather than quoting a number.

Three aggregate figures circulate in the ledgers and **none of them is a measurement**: "four of
eight rows fact-checked this morning were already satisfied" (origin: a bus ack,
`msg-20260812T105206Z-45-coordinator-agent`, first written form commit `f3cb4462`); a separate
"nine independent checks" framing the same day; and mainA's *"eight rows I pulled had stale
premises"* (`progress/2026-08/2026-08-12.md:2371-2372`). They are three different ratios, none
enumerated — the fact-checks happened verbally on the bus and were never written back into the rows,
so no row-level report exists to recover. `git log` over the affected backlog file confirms none of
the implicated rows was ever ticked. All three are `ledger-narrative` and none may gate a promotion,
which is precisely the case `label_provenance` exists to mark.

So: grow the `stale` class from **primary artifacts**, one verified row at a time, the way N1–N4
were built. Do not import a ratio, and do not add a rule.
