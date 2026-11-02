# RTG-51 Phase 5 ratify draft: the narrow subagent exception to ruling (b)

**Status:** draft for operator review. Nothing here is in force. `CLAUDE.md` (with its `AGENTS.md`
symlink) and `agents/shared/*` are human-only. Item 5 of
`/mnt/raid0/llm/tmp/ws58-csh/ratify_brf_batch_20261102.sh` applies the three payloads below
verbatim. It applies them only when this file contains no unresolved operator slot. This file
has none.

**Decision being executed.** The operator approved option A on 2026-11-02 (decision tool, ws58):
*"Sign with a narrow subagent exception (one writer, one request, one lease)"*
(`docs/design/backlog-refactor-2026-11/decision-packages/coordination-and-churn-pipeline.md` #11;
box `handoffs/active/wrap-up-division-of-labor-policy.md:431-432`: "The subagent exception, if
retained, must be narrow: one designated writer, one request, one lease"). The migration matrix
row for `CLAUDE.md` / `AGENTS.md` reads "Preserve prohibition or ratify narrow designated-writer
exception" (same file, *Policy migration matrix*).

**Base:** epyc-root `origin/main` `cf03d5ca3`.

## Is the exception already present? No.

The 2026-10-07 RTG51 phase-5 review
(`/mnt/raid0/llm/tmp/ni08-thesis-audit-20261006/RTG51-phase5-migration-matrix-review-20261007.md`,
against root `e7ff59bee`) found `agents/shared/SESSION_LIFECYCLE.md` "already reconciled" and
`OPERATING_CONSTRAINTS.md` "substantively aligned". It also found that, for `CLAUDE.md` /
`AGENTS.md`, "the narrow designated-writer exception is not present". Rechecked against today's
text:

- **The alignment claim holds, for cadence and prepare/apply only.** All three protected surfaces
  state ruling (b) in its 2026-08-16 form. A subagent prepares, the owning session applies, and
  any widening needs explicit approval:
  - `CLAUDE.md:214-218`;
  - `agents/shared/OPERATING_CONSTRAINTS.md:704-710` (the canonical home);
  - `agents/shared/SESSION_LIFECYCLE.md:130-135`.
- **The exception is absent from every protected surface.** `designated` has zero hits in
  `CLAUDE.md`, in `agents/shared/*.md`, and in `agents/coordinator-agent.md` and
  `agents/auditor-main.md`.
- **The designated writer exists only in `agents/commands/wrap-up.md:36-71`**, the *Typed
  heavy-wrap transaction*. That section defines the mechanism the exception has to name. It is
  not itself an exception to ruling (b), and it is not on a protected surface. Those facts are:
  - Coordinator validates and issues one typed `wrapup-request`;
  - the request ID, integrated `origin/main` SHA and receipt cut are bound before any mutation;
  - Coordinator "chooses exactly one designated writer";
  - "the designated writer acquires one operation-token lease for the shared transaction".

So "already aligned" was true of everything except the one thing option A adds. Below is the
minimal addition. The canonical text goes into ruling (b)'s home in `OPERATING_CONSTRAINTS.md`,
and the two surfaces that restate (b) each get a one-sentence pointer.

## Grounding of each clause

| Clause | Source |
|---|---|
| One request: a typed `wrapup-request`, validated and issued by Coordinator, bound before mutation to its ID, `origin/main` SHA and receipt cut | `agents/commands/wrap-up.md:39-40`, `:45-48` |
| One writer: Coordinator chooses exactly one designated writer; nobody else writes for that request | `agents/commands/wrap-up.md:49-50` |
| One lease: the writer holds the request's operation-token lease and writes only under it | `agents/commands/wrap-up.md:52`, `:66-67` |
| Per-task subagent wrap-ups stay prepare-only | `SESSION_LIFECYCLE.md:130-135` and `wrap-up.md:178-180`. These have no typed request, so the three conditions cannot hold. |
| Authorizes a writer, not a step; ruling (a) unchanged | Option A ratifies an exception to (b) only. Ruling (a) (`OPERATING_CONSTRAINTS.md:692-702`) is untouched by this text. |

**Left as is, deliberately.** `agents/commands/wrap-up.md:41-44` says that until the protected
Phase-5 amendment is signed, a Coordinator request is not permitted to run the operator-cadence
steps (index pruning, the wiki compilation sweep). This draft does not answer that question.
Option A covers the writer exception only, and the payload states that ruling (a) is unchanged.
The non-protected half of Phase 5 (`coordination/session-bus/tasks/STANDING-MAIN-RULES.md` §8,
`post-reboot-session.md` §6, the mainA–D briefs) needs no signature and stays with
coordinator-agent. That is the Phase-5 box at `:429`, which stays open.

`<RATIFIED_DATE>` is the only token the ratify script fills, with the UTC date of the real run.

## Payloads (applied verbatim by the ratify script)

### `oc-ruling-b-exception`: inserted in `agents/shared/OPERATING_CONSTRAINTS.md` between ruling (b) and ruling (c)

<!-- payload: oc-ruling-b-exception -->
````markdown
**(b) Exception — the designated writer of a typed heavy wrap** *(operator-ratified
<RATIFIED_DATE>; RTG-51 Phase 5, option A: one writer, one request, one lease).* A subagent may
itself make the writes that (b) reserves to the owning session only while all three hold:

1. **One request.** It is executing one typed `wrapup-request` that Coordinator validated and
   issued, bound before any mutation to that request's ID, integrated `origin/main` SHA and
   receipt cut (`agents/commands/wrap-up.md` → *Typed heavy-wrap transaction*).
2. **One writer.** Coordinator chose it as that request's one designated writer. No other
   subagent or session writes those surfaces for the same request.
3. **One lease.** It holds the request's operation-token lease and writes only while it holds it.

Everywhere else (b) holds unchanged: a subagent prepares and the owning session applies. That
includes every per-task wrap-up a subagent runs on a session's behalf, which has no typed
request. The exception authorizes a writer, not a step: the designated writer performs only the
mutations the accepted request is otherwise authorized to perform, and ruling (a)'s operator
cadence is unchanged.
````
<!-- /payload -->

### `claude-md-ruling-b`: replaces the ruling-(b) bullet in `CLAUDE.md` (`AGENTS.md` is a symlink to it)

Current text (`CLAUDE.md:214-218`), for comparison:

```text
- **Index rows, intake entries and handoff stubs: a subagent may PREPARE, the owning session
  APPLIES.** Drafting the row text, running `scripts/handoffs/index_state.py --check` and reporting
  the exact diff is preparation. Adding, deleting or re-pointing a row is never a subagent's own
  write; widening that needs explicit user approval. (ruling (b), 2026-08-16 —
  `agents/shared/OPERATING_CONSTRAINTS.md` → *Doctrine rulings*)
```

<!-- payload: claude-md-ruling-b -->
````markdown
- **Index rows, intake entries and handoff stubs: a subagent may PREPARE, the owning session
  APPLIES.** Drafting the row text, running `scripts/handoffs/index_state.py --check` and reporting
  the exact diff is preparation. Adding, deleting or re-pointing a row is never a subagent's own
  write, with one ratified exception: the single designated writer of an accepted typed
  `wrapup-request` (one writer, one request, one lease). Any other widening needs explicit user
  approval. (ruling (b), 2026-08-16, exception <RATIFIED_DATE> —
  `agents/shared/OPERATING_CONSTRAINTS.md` → *Doctrine rulings*)
````
<!-- /payload -->

### `session-lifecycle-pointer`: inserted in `agents/shared/SESSION_LIFECYCLE.md` → *Wrap-up cadence*, right after the line ending `needs explicit operator approval. (ruling (b), 2026-08-16)`

<!-- payload: session-lifecycle-pointer -->
````markdown
  The one ratified widening is the designated writer of an accepted typed `wrapup-request` — one
  writer, one request, one lease (`agents/shared/OPERATING_CONSTRAINTS.md` → *Doctrine rulings*,
  ruling (b) exception, <RATIFIED_DATE>). A per-task wrap-up subagent has no typed request and
  stays prepare-only.
````
<!-- /payload -->

## What the ratify script does with this file (item 5)

1. It refuses unless every anchor occurs exactly once and the RTG-51 box at `:431` is still
   unticked.
2. If this file contains an unresolved operator slot, it STOPs and writes nothing.
3. Otherwise it captures the §5 pre-state of the three files and applies the payloads, filling
   `<RATIFIED_DATE>`. It then emits a §5 consolidated receipt
   (`RATIFY-RTG51-RULING-B-EXCEPTION-20261102`). Its validations are `git diff --check`, an
   exactly-once count for each anchor, and `scripts/validate/validate_agents_structure.py`. It
   ticks the `:431` box. Everything goes in ONE separate commit carrying `Operator-Ratified: yes`,
   as the Phase-5 box at `:429` requires ("Keep protected policy in a separate reviewable commit").
4. Afterwards, outside this script and per the Phase-5 boxes, Coordinator sends the
   instruction-refresh nudges naming the merged SHA, and the session-bus daemon restart is proven.
