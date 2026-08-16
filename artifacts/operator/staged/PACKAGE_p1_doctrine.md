# P1 doctrine collapse — human-only half. Operator package.

**Run**: `artifacts/operator/staged/apply_p1_doctrine.sh` (dry run) → `--apply`.
**Covers**: P1-2, P1-3, P1-4 of `handoffs/active/loop-owned-fleet-implementation.md`.
P1-6 (`agents/coordinator-agent.md`) is NOT in the script — that path is not human-only, so it is
already rewritten in the working tree; review it with `git diff -- agents/coordinator-agent.md`.

## Why a script

`agents/shared/*.md`, `CLAUDE.md` and `agents/AGENT_INSTRUCTIONS.md` are hash-pinned in
`coordination/session-bus/human_only_paths.yaml`; `scripts/hooks/check_trust_boundary_edit.sh`
refuses agent Write/Edit on them. That is INVARIANTS 4 and 10 working. The content is staged and
you apply it. Nothing here launders an edit past the hook with `sed`/redirection: it copies whole
files you can read first.

## What was rehearsed before you see this

The script was run end-to-end against a shadow copy of the tree (`P1_REPO=<shadow>`), and every
gate was mutation-tested:

| Test | Result |
|---|---|
| `--apply` on a clean tree | all four items install, all five gates green, exit 0 |
| `--apply` a second time | all four report SKIP (byte-identical), gates still green |
| target drifted (one file) | that item ABORTS with both hashes printed; the others still install; exit 1 |
| staged source tampered | REFUSES to write, target left untouched, exit 1 |
| a required heading deleted | VERIFY 3 fails naming the dead anchor |
| VERIFY 5 as first written | fired on legitimate citations — it matched the section HEADING, which every correct pointer also contains. Fixed to match body sentences instead. This is the gate-passes-for-the-wrong-reason class, caught by rehearsal rather than in production. |

## The five merges — content that existed in ONE copy and would have been lost

P1-2 says "pick one canonical home and replace the others with a citation". Deleting a copy without
diffing it first destroys whatever only that copy carried. Five such amendments were found and
merged INTO the canonical before the duplicate was reduced:

1. **"the tightest instance, never an exemption"** — lived only in `agents/coordinator-agent.md`
   and the coordinator SKILL. The canonical fan-out section said a strict coordinator form *exists*
   but not that it is non-exemptible. Merged into `OPERATING_CONSTRAINTS` → *Parallel Subagent
   Fan-Out*.
2. **`INC-20260728-idle-mains` as fan-out's second origin** — recorded in `coordinator-agent.md`
   and `SESSION_LIFECYCLE.md`; the canonical cited only the 2026-08-12 incident. Both origins now
   sit in the canonical appendix.
3. **The AUD-2 typed-row enforcement** — `task_text` is schema-enforced (`append` REFUSES without
   it), plus `row_ref` / `screened_by` / `expected_occupancy` / `constraints[].source` / the 4 KB
   `brief_path` rule. This lived only in `.claude/skills/coordinator-agent/SKILL.md`, so the
   canonical rule did not know it had become machine-enforced. Merged into *Dispatching Backlog
   Work*.
4. **"never run OR APPROVE a reload around the owner"** — the approval half existed only in the
   coordinator SKILL. Merged into the reload-ownership rule. The owner-side duty ("own reload
   timing"), which existed only in `agents/inference-main.md`, is now cross-linked both ways.
5. **Invariant 13 vs "name your count"** — `INVARIANTS.md` fixes **two** samples, the canonical
   rule demanded a *named* count, `CLAUDE.md` said "several", the incident used **three**. Nothing
   reconciled them. Now stated explicitly: two samples is the floor for ACTING; a published absence
   CLAIM must name its own count.

Four further merges went into the checkbox axiom in `SESSION_LIFECYCLE.md`, each previously in a
single file: the never-tick SCOPE (invariant 9 says *another agent's* box; the SKILL said "never
flip a checkbox", absolute), the "saying a box is stale is not ticking it" carve-out
(`coordinator-agent.md` only), the frozen/compatibility-pointer handoffs that FORBID new checkboxes
(`research-intake` SKILL only), and the `blocked`/`partial` checkpoint outcomes with their
"nonterminal outcomes leave the source task open and add a checkpoint-keyed child task" rule
(`log` SKILL only — the binary flip axiom does not model them).

## Two broken pointers fixed

- `agents/commands/wrap-up.md` cites `SESSION_LIFECYCLE.md` → *Wrap-up cadence*. **That heading did
  not exist.** It does now, and it carries ruling (a).
- `SESSION_LIFECYCLE.md` cited `MEASUREMENT_POLICY.md` → *Observation windows*. **That section does
  not exist** in that file; the rule lives in `OPERATING_CONSTRAINTS.md`. Repointed.

Neither was caught by `validate_agents_references.py`, because both are prose citations rather than
markdown anchor links — the validator only resolves `[text](file.md#anchor)`.

## The three rulings, as worded

Canonical home is `agents/shared/OPERATING_CONSTRAINTS.md` → *Doctrine rulings — 2026-08-16*.

**(a) Wrap-up cadence.** The binding 2026-08-11 operator rule wins: one task done = one wrap-up, AS
YOU GO. Only index PRUNING and the wiki compilation sweep stay at the operator cadence. Nothing may
auto-trigger the full routine — no `Stop`/`SessionEnd`/`PreCompact` hook, no cron, no nightshift
task, and there must not be one.

**(b) Subagent index edits.** A subagent may PREPARE index edits; the owning session APPLIES them
and owns the commit. Preparation is drafting row text, running `index_state.py --check` and
reporting the exact diff. Same rule for intake entries and handoff stubs.

**(c) Role-based delegation.** Decomposition by ROLE is a measured anti-pattern and no live surface
may instruct it. Decompose by CONTEXT BOUNDARY.

## What this does NOT touch

- `agents/shared/INVARIANTS.md` — already applied by you; this package cites it and never rewrites
  it.
- Commit `b5ae002d`'s surfaces (BUS_PROTOCOL, wrap-up.md, the workflow guides, the coordinator
  SKILL body) — not redone.
- `CLAUDE.md`'s API-reload MECHANICS (`orchestrator_stack.py reload orchestrator`, the autopilot
  handling). That is the **sole copy in the corpus** of how a reload is actually performed;
  everything else covers who and when. Deliberately left alone.

## Judgement calls you may want to overturn

1. **`agents/coordinator-agent.md` landed at 170 lines, not ~50.** Going below meant deleting
   contracts rather than citing them. The instruction body did shrink (187 → ~150 excluding the new
   console contract and the appendix), and 21 distinct directives survive. Same call the previous
   attempt made at 134 lines, and for the same reason.
2. **`OPERATING_CONSTRAINTS.md` GREW, 269 → 366 lines.** P1-4 relocates narrative, it does not
   delete it; P1-3 required adding a rulings section (+37 lines) and P1-2 required adding five
   merges. The instruction path is 315 lines. If you want a genuinely shorter file, the appendix is
   the part to move to `INCIDENT_LOG.md` — say so and it goes.
3. **A ratified-D4 consistency note was added** to the *Inference resource ownership* bullet:
   grant AUTHORITY moved off `inference-main` to `compute_policy.yaml`. Everything about physical
   claims, residency evidence and drain-at-boundary is unchanged. This was not on the task list; it
   is a live contradiction with amended D4 and is flagged here so you can strike it if you prefer
   it filed rather than fixed.

## After you apply

```
git diff -- CLAUDE.md agents/
git commit -m "P1-2/P1-3/P1-4/P1-6: doctrine dedup, rulings, narrative appendices" -- \
  CLAUDE.md agents/AGENT_INSTRUCTIONS.md agents/shared/OPERATING_CONSTRAINTS.md \
  agents/shared/SESSION_LIFECYCLE.md agents/coordinator-agent.md agents/auditor-main.md \
  agents/inference-main.md .claude/skills/coordinator-agent/SKILL.md
```

Then tick P1-2, P1-3, P1-4, P1-6 in `handoffs/active/loop-owned-fleet-implementation.md`.
