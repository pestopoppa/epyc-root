# RTG-48 A-3 / A-5 source review — MAIN accepted 2026-10-08

**Review point:** ROOT private worktree at `c2fd4e35caa0259a6bf01c5a6920422111257bba` (`codex/ni08-evl180-task-wrap-20261007`). MAIN's A-2 handoff edit is present in the dirty worktree; it is included by the working-tree hash in `source-bindings.json` and was not changed here.

**Scope:** Read the exact open A-3 and A-5 tasks, current RTG-48 source, MAIN-applied A-2 adjudication/custody, the earlier A-1 mechanism audit and 2026-08-12 role audit, plus the later checked R-16/R-19/AUD-13/AUD-14/AUD-16 text. No tests, imports, runtime probes, inference, statistical rate estimates, GitNexus, or ClaimTuple grading were performed. This is a source classification, not a claim about coordinator population behavior.

## A-3 — grouping and over-fit review

A-3 is still open and A-2 does not answer it. A-2 adjudicates selected RC-1 counterexamples and explicitly rejects a population-rate estimate; it does not compare RC-2…RC-7 as a taxonomy. Do not reopen the settled R-16 decision about what the loop may do.

The task's “seven groups over thirty-two failures” names RC-1 plus RC-2…RC-7. RC-1 is stated as the parent of the six child causes, so those seven are not seven peer clusters. A-3's 32-case scope is the original F-01…F-32 set; later additions (including F-37/F-38 in the table and F-33…F-36 / later F-series sections) must remain separately labelled unless explicitly reclassified. The current file therefore must not be summarized as a fresh 32-case exhaustive census.

The six child causes also are not a disjoint partition. RC-3 and RC-4 both list F-11 and F-14; RC-2 and RC-3 both list F-25. The RC-2 member line says eleven cases, while its sub-shape examples additionally name F-04, F-08 and F-20, which are absent from that member line (F-20 is a listed RC-6 member). The text does not state whether those are cross-group analogues or additional RC-2 members. This is a concrete classification ambiguity, not evidence for a measured collapse.

**No RC-2…RC-7 pair should be collapsed on this finite source record.** The source distinguishes six control points; their examples can overlap without making their checks interchangeable:

| Group | Distinguishing question / control point |
|---|---|
| RC-2 | Does the instrument, sample window and scope support the published claim? |
| RC-3 | Was the intended work/outcome actually completed, rather than merely messaged or dispatched? |
| RC-4 | What observes or acts between operator turns; is the loop absent or idle? |
| RC-5 | Were edits reviewed and made durable, independent of who typed them? |
| RC-6 | Did the action stay within the role's authority and avoid broadcasting a false premise? |
| RC-7 | Did the dispatch resolve the current task text and address the right recipient? |

The explicit overlaps are RC-2/RC-3 (F-25), RC-3/RC-4 (F-11/F-14), and the RC-2 sub-shape examples F-04/F-08/F-20; F-23 touches RC-6/RC-7 but its claimed violation is not established. The remaining pairs differ on the control point above and have no source-backed common test that would make a merge more explanatory than the current split. This is a qualitative comparison of the cited cases, not validation of the clusters on an independent sample.

- RC-2 concerns the validity/scope of a published claim relative to its instrument; RC-3 concerns treating a sent message as an achieved outcome. F-25 overlaps, but “wrong measurement” and “unverified completion” remain distinguishable checks.
- RC-3 and RC-4 share F-11/F-14, but one is outcome/reporting substitution and the other is lack of continuous observation between prompts. The same event can exhibit both. R-16 is already checked: the operator authorized a daemon tick to dispatch under existing authority and gates; `fleet_watch` remains detect-only. That settled control decision is not reopened here.
- RC-4 and RC-5 are operationally distinct at the mechanism level: temporal monitoring/dispatch versus review, ownership and commit custody. However, “wrong work on the thread” is not established. The present RC-5 text itself says author identity is not established for all five artifacts; AUD-13 later narrows F-16 to one commit-body self-report and F-17 to a contemporaneous progress self-report. The evidence supports the historical unreviewed/uncommitted tree state and scoped self-reports, not a general authorship claim.
- RC-6 (authority boundary) and RC-7 (task/recipient identity) remain distinguishable from those axes. F-23's standing block could touch both, but later R-19 and AUD-16 alter the role premise; see A-5 below.

**MAIN ruling:** retain RC-2…RC-7 as provisional, overlapping control-point lenses; do not describe them as seven independent groups or infer a rate. Clarify the RC-2 examples as cross-group examples or define membership explicitly; preserve original F-01…F-32 separately from later cases. This answers the source-level collapse challenge without statistical generalization. MAIN applied the membership clarification and completed A-3 as a bounded taxonomy audit.

## A-5 — rulings on the eight numbered corrections

A-5 remains an open source task in the current file. The 2026-08-12 audit reviewed only selected correction numbers, and its §2 verdict on F-13 is superseded by the later checked AUD-14 account. AUD-13/14/16 resolve portions of the request but do not supply an integrated ruling over all eight numbered corrections plus the “harder than warranted” paragraph.

| Correction | Current source ruling | Evidence limit / unknown |
|---|---|---|
| 1. F-24 timing and severity | Accept the bounded correction as reported: the cited attempts are 42 seconds apart and the cited window is 74 seconds / two attempts, so “every ~10s forever” is not supported. The stronger wrong-predicate point is separately supported by A-2 as a wrong-mechanism case. | The original incident window is not in the retained host logs. Preserve attribution to the historical commit/report; do not claim a newly reopened raw log. |
| 2. F-13 “three mains” | AUD-14 is the current ruling: the C51 comment reports three examples and a mainB dispute is reported, but actual pane actors and contributor count are unknown. Do not publish “two” or “three” as authenticated. | Original denial row was not located in the tracked source set; keep the dispute attributed. |
| 3. F-12 quotation | The source's correction is directionally sound: do not quote “inference is genuinely working” as verbatim; preserve the separate, attested self-reported-busy-state error. | The correction records a repo-wide exact-string search, but this PREP did not repeat it; treat the exact absence as the prior source report's scope, not a fresh search result. |
| 4. F-08 attribution/date | Preserve the correction as a scoped historical attribution to mainD and 2026-08-11, rather than an operator correction. | No new message census was run. Use the named source/report, not an absolute claim about all unrecorded communication. |
| 5. F-23 | The auditor/mainA duplicate-prompt charge is contradicted. The 10:48 standing-block/assignment context may be retained as a historical dispatch fact, but the old READ-ONLY-vs-C-OWN conflict was resolved in config on 2026-07-29 and the stale MAIN-GOALS row was struck (R-19; AUD-16). The available source does not establish that this surviving message violated current authority or caused harm. Do not preserve F-23 as an established failure on that basis. | The original payload may be described as a main-shaped standing block sent to the auditor, alongside execution assignments; recipient effect/objection is not established here. No recurrence count. |
| 6. F-05 false-at-send vs later-stale | Accept “already false when sent” as materially distinct if the cited time-bound Git state is retained: the stated 3-ahead/6-behind divergence predated the 09:51:20Z message (origin reportedly left the base at 09:47Z). The later patch-id content-safety check does not make the state assertion accurate. | Evidence is preserved in the current handoff's historical account; this PREP did not independently reconstruct the old refs. Keep timestamps and attribution visible. |
| 7. F-06 recurrence | Accept a repeated reasoning class, but not a second identical accusation: the later inference statement was explicitly hedged and the handoff says it was not an instruction. | AUD-12 withdrew the active recurrence counts. Do not turn this into a numeric recurrence estimate. |
| 8. F-11 “eleven” | Accept that the number is a self-count, not an independently auditable count; preserve at most the scoped written reports and the single dated raising described in the source. | AUD-12 withdrew the active Recur column; no replacement count has been calculated. |

### “Harder than warranted” paragraph (the additional A-5 subquestion)

At the cited 10:58 snapshot, “surfaced-not-fixed” was inaccurate: the source records a reproduction harness and a C51 code correction already in the working tree. “Implemented but uncommitted/unreviewed at that snapshot” is a fair, narrower description. The later history makes “never landed” stale: A-1 records C51 at `b6ea8679` and C55 at `2076e359` as landed. AUD-13 supports only the bounded F-16 prototype authorship self-report in commit `83f204cf`; it does not authenticate every artifact's author. Thus “fixed on the wrong thread” is not an independently established general claim, and “never landed” is false as a present-tense summary.

**MAIN A-5 ruling:** append the table above as a dated, source-scoped ruling; retain unknowns; update F-13/F-23/F-05/F-10 wording only through MAIN's canonical edit. MAIN applied these source-scoped corrections and completed A-5 as the audit task it asks for. This is not a request to revisit settled AUD-13/14/16 or R-16 decisions.

## Scope boundary

This source review establishes no new event count, actor authentication, population-rate estimate, quality grade, runtime behavior or causal generalization. The private binding manifest records the exact source identities, original handoff task checkbox states and current ROOT base. MAIN independently compared the named current source sections and later rulings, corrected causal-lens wording, and owns the canonical application and checkbox changes.
