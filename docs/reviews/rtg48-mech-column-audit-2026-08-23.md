# RTG-48 A-1 — Audit of the `Mech` column: mutation-tested mechanisms vs. prose rules

**Date**: 2026-08-23 · **Subject**: `handoffs/active/coordinator-role-failure-modes-and-refactor.md` —
the `Mech` column of the F-table (F-01…F-38, self-assessment: 6 `MECH` · 6 `MECH-UC` · 20 `RECALL` ·
1 withdrawn) · **Index row**: RTG-48, task A-1.
**Deliverable**: [`tests/coordination/test_mech_column_audit.py`](../../tests/coordination/test_mech_column_audit.py)
— 27 tests, all green (`uv run --with pytest pytest -q tests/coordination/test_mech_column_audit.py`).

## The standard applied

A `MECH` claim is only true if the named mechanism **would have REFUSED the specific failure** in
that row — not if it merely covers the topic. Where a mechanism is code, the claim is proven by
mutation: the real path refuses, then the one load-bearing clause is deleted and the failure recurs.
Where a mechanism is prose, no mutation exists; the claim is downgraded. The two closures whose
mutation cannot be applied in place (the per-agent rate-limit filter in `tmux_adapter.probe`, and
the advisory distinct-row dedup) are mutated as a faithful replica of the exact production
arithmetic with the clause deleted — both directions asserted.

## Per-row verdicts

| Row | Failure | Mechanism claimed | Verified in code today? | Would refuse the specific failure? | Mutation result | Honest classification |
|---|---|---|---|---|---|---|
| F-03 | Checkbox counts wrong all night — unanchored `- [ ]` matching | Anchored `_OPEN_BOX = ^\s*- \[ \] ` (`backlog_row_check.py:184`), consumed by `index_state` | **YES** — `backlog_row_check.py:184`; `index_state.scan_handoff` iterates `brc._boxes` (`index_state.py:270`) | **YES** — mid-line boxes are not counted; only line-start boxes are | Unanchored variant matches a mid-line box → the wrong count recurs; anchored refuses | **MECH survives** (as claimed: existed-unused; today it is the canonical counter, and R-4's `verdict=` stdout line, `f9c8b52b`, closes the laundering path) |
| F-04 | Cited 4,602 advisory records as a backlog | `a90870ec` added *Reporting Units* | **PARTIAL** — `a90870ec` itself is prose-only (rule + handoff edit). The mechanism landed in code later: `summarize_advisory_shard` (`session_bus_coordinator.py:3045`, `4622c0d7`) computes N/M/K; digest written by `_archive_advisory_shard`; pinned by `test_advisory_archive.py` | **YES (producer-format)** — the canonical advisory summary never emits N alone: 4,602 records → M=9, K never guessed (`None` + `k_method`) | Distinct-dedup deleted → M := N → "4,602 distinct rows" is internally consistent again, i.e. the failure recurs; dedup restored → refused | **MECH survives**, with a corrected citation: the named commit is a rule; the mechanism is the later code + tests. Caveat: it constrains the canonical producer, it cannot refuse a sentence written elsewhere |
| F-08 | Filed the nudge rate limit as a fleet-wide HIGH defect | `34a17894` regression test; `777f826e` doorbell | **YES** — per-agent filter `r.get("agent") != agent` at `tmux_adapter.py:1950`; `--min-interval-s` default 600 (`:3140`); both-direction tests at `tests/test_tmux_adapter.py:2075,2108` | **YES** — a bystander's nudge does not block this agent | Filter clause deleted → the same ledger reads 30s (bystander's nudge) → the fleet-wide HIGH claim is TRUE again; restored → refused | **MECH survives** |
| F-15 | Did not fan mains out to subagents by default | `2f787163` | **NO mechanism** — the commit touches 7 prose files (CLAUDE.md, agents/*.md, a guide, the owning handoff); no script, check or test | **NO** — the rule exists (OPERATING_CONSTRAINTS.md:181 *Parallel Subagent Fan-Out*) and is real policy, but nothing refuses serial work; the row itself admits the detector gap (RTG-49, `fleet-fanout-measurement.md`, still active) | No code to mutate — this is the row's own admission | **DOWNGRADED → RECALL** (rule only). A rule is not a mechanism; the honest protected count must not include it |
| F-22 | Dispatched by `file.md:LINE` as identity | `backlog_row_check.py --ref` exists, **not on the dispatch path** | **YES (both halves, now reversed)** — `--ref` exists (`:754,805-825`); the path is now wired: `check_task_assign` raises BusError without `task_text` (`session_bus.py:1462-1469`) and `dispatch_gate` refuses rows without `screened_by` (`session_bus_coordinator.py:1744-1759`, AUD-2 `9bed637f`) | **PARTIAL for `--ref`, FULL for the typed path** — `--ref` refuses dead anchors (ANCHOR_ROT, exit 3) but does NOT refuse identity substitution (a rotted line that is still a checkbox screens the WRONG row as DISPATCHABLE — mainC's `:327` catch); the typed `task_text`/`screened_by` path refuses the whole class | Dead anchor: real code exit 3 vs. mutated resolver reading a non-row as a row; wrong-line-still-a-checkbox: `--ref` screens the wrong row vs. text resolution (`--row`) finding the intended one | **MECH survives — stronger than claimed.** The F-03 shape (existed-unused) is confirmed as written; the wiring gap it names has since been closed structurally, so the protection is real, not aspirational |
| F-27 | 5,292 lane-rejection figure not reproducible; withdrawn | `a90870ec` covers the class | **PARTIAL (class only)** — prose rule + advisory N/M/K + `_top_rejection` carries `{reason, count, of}` (denominator) | **NO** — nothing refuses the publication of a bare rejection tally; the withdrawal was self-correction, and the code comment at `session_bus_coordinator.py:2076` **still asserts "5,292 occurrences per agent"** — the withdrawal did not propagate | No refusal to mutate | **DOWNGRADED → RECALL** (class covered by rule; not refused) |
| F-07 | Misread a session COMPACTING as idle | `fleet_watch.sh:60-64` IDLE-CANDIDATE … may be compacting (untracked) | **SUPERSEDED** — the pane heuristic was DELETED by P3-3 (`23357e7b`/`96ccad1a`), not landed as-is: pane text is now *evidence for a human, never a trigger*, and every probe is three-state (UNKNOWN never counts as idle) | **YES (class)** — the compaction-misread class is refused by the stronger landed rules + the adapter's C36 runtime check + AUD-1 (the role no longer reports instruments at all) | n/a (heuristic deleted) | **UPGRADE → MECH** — superseded by a stronger landed mechanism |
| F-10 | Reported the composer defect instead of fixing it | C51 `tmux_adapter.py` fix (uncommitted) | **LANDED** — `b6ea8679` (C51: rollback + `*-undelivered` rows + loud failure) and `2076e359` (C55: wake-char submit) | **YES** — `_press_key_with_wake` (`tmux_adapter.py:797-810`) sends space, settles `_WAKE_SETTLE_S=1.0`, then the key; `_fail_after_typing` records the strand state | Bare-key sequence (pre-C55) is the measured no-op — the failure recurs; wake-char sequence present in production | **UPGRADE → MECH** |
| F-11 | Reported idle compute rather than intermediating | `fleet_watch.sh` detects (untracked) | **LANDED** — `83f204cf`, evolved to P3-3; detect-only per the R-16 operator ruling | **YES** — continuous COMPUTE-IDLE detection with gating + persistence + three states | n/a (shell loop; its own mutation suite pins each detector) | **UPGRADE → MECH** (detect-only as designed; it does not resolve, by operator ruling) |
| F-13 | Sampled fleet state only when the operator asked | `fleet_watch.sh` (untracked) | **LANDED** — committed; queue- and hardware-grounded loop | **YES** — the continuous loop closes the sampling gap; composer visibility moved to the adapter's C51 `pending` detector | n/a | **UPGRADE → MECH**, with the F-33 caveat: the boundary *drain* remains prompt-driven |
| F-24 | Started `bus_supervisor.sh` without verifying it could see its target | Fix + `M1_pattern_adjacency`…`M4_no_storm_bound` harness (uncommitted) | **LANDED AS SUPERSEDED** — H-4 (`bc6dc77f`) replaced the mtime predicate with the SHA deploy-marker: daemon heartbeat `source_tree` vs `git rev-parse HEAD:scripts/coordination`; restarts rate-limited then ALARM; `STALE_SRC_SKEW_S` deleted | **YES** — running-tree-vs-HEAD compares two independently sourced values; the harness that existed (env override `BUS_SUPERVISOR_SH`) plus `test_supervisor_stale_source.sh` refuse the old predicate's return | Suite runs the script against deliberately mutated copies; my pins assert the old knob is not live | **UPGRADE → MECH**. The "mechanism was itself the defect" note is correct and unchanged: the ORIGINAL watchdog was the defect; the fix is the mechanism, and it is now landed and mutation-tested |
| F-35 | `doorbell` delivery to the auditor failed; composer would not consume Enter | C51 fix uncommitted per RC-5 | **LANDED** — C51 `b6ea8679`, C55 `2076e359`, H-2 `2054659d`, H-1 `e263e144` | **YES** — doorbell now submits via wake-char + Enter, verifies the post-Enter buffer, refuses on swallow, and records non-delivery | As F-10; submission suite at `test_tmux_adapter_submission.py` | **UPGRADE → MECH** |

## Summary

**Of the six `MECH` claims, four survive mutation-testing; two must be downgraded.**

- **Survive: F-03, F-04, F-08, F-22.** Each was verified in code today and mutation-tested in both
  directions (refusal holds; the failure recurs when the load-bearing clause is removed).
- **Downgraded to `RECALL`: F-15 and F-27.** F-15's commit is policy prose with no mechanism — the
  row itself admits the detector gap (RTG-49). F-27's claim is *"covers the class"* — true as a
  rule, and the advisory summary does carry N/M/K, but nothing would have refused the specific
  figure; the withdrawal was self-correction, and the withdrawn "5,292" still sits in a code comment
  (`session_bus_coordinator.py:2076`).

**Of the six `MECH-UC` claims, all six upgraded to `MECH`.** Every mechanism named as uncommitted on
2026-08-12 has since landed with tests: `fleet_watch.sh` (`83f204cf` → P3-3), C51/C55/H-1/H-2
(`b6ea8679`, `2076e359`, `e263e144`, `2054659d`), and the `bus_supervisor` fix (superseded by H-4's
SHA predicate, `bc6dc77f`). Zero rows remain uncommitted.

**The honest protected count.** The handoff's own arithmetic (6 `MECH`, minus the two
existed-unused, = 4) lands on four by a different route than this audit: the two *downgrades* are
the rule-only claims (F-15, F-27), while both *existed-unused* claims (F-03, F-22) actually survive
— F-22 because the wiring gap it names has since been closed structurally (AUD-2). Net: **four
`MECH` claims stand as mechanisms that would have refused their failure; two are rules that would
not.**

## Findings beyond the column

1. **F-27's withdrawn figure still lives in code.** `_top_rejection`'s docstring asserts
   *"5,292 occurrences per agent"* — the figure the row itself records as withdrawn (COR-6, "the
   current shard holds 7 each"). The withdrawal did not propagate to the comment that future agents
   will read as ground truth. Small, real, and exactly the class the column is supposed to be about.
2. **The F-22 `--ref` screener refuses rot, not substitution.** Pinned by test: a rotted anchor
   that is still a checkbox screens the WRONG row as DISPATCHABLE. Text identity is the only
   refusal, which is why the typed `task_text` mandate matters — the claim as written ("`--ref`
   exists") should not be read as covering the substitution half.
3. **A `MECH` is producer-format, not sentence-refusal.** F-04's mechanism constrains the advisory
   summary; it cannot stop an agent writing "4,602" in a message. This is the general limit of the
   column's standard and should be stated wherever the count is reused.

## Method note

Zero network, zero inference, zero process management. Production files were read-only; the only
writes are the test file and this review. Mutation style is stated in the test module docstring:
closures are mutated as faithful replicas of the production arithmetic with the one clause deleted,
because `probe`'s `_times` and the advisory dedup are not patchable in place.
