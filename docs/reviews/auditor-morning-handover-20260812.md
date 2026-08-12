# `auditor` — overnight handover, 2026-08-11 → 2026-08-12

**Role tonight**: review/audit lane (Fable 5), lane `none` throughout — no inference, no
benchmarks, no servers, no region claims, no signer edits. Every item wrapped at its own
boundary, pathspec commits only. Operator decision surface is consolidated separately in
[`artifacts/operator/auditor-morning-note-20260812.md`](../../artifacts/operator/auditor-morning-note-20260812.md) — this document is the work record.

## 1. Finished — with hashes

| Item | Where | Evidence |
|---|---|---|
| Completion-flurry wiring audit (sections A–D + reconciliation + addenda) | `artifacts/audit/completion-flurry-wiring-audit-20260811.md` | `5c2212ce`…`6f53e0a6`, addenda `8ab72a28`, `16ce0412`-adjacent |
| Read-certification T4–T7: **389 rows** LIVE/DEAD/GATED/REWRITE, adjudicated | `artifacts/audit/read-certification-tranche{4..7}-20260812.md` | records at stale-open L269+ |
| Three ratification vehicles authored → operator-signed → consumer-verified | `artifacts/operator/ratify_{consolidated_era_rows,annexg_v9_currency,v9_cpu_bench_era_advance}_20260811.sh` | receipts + C39 keyed index |
| C39 receipt conformance checker | `scripts/operator/check_ratifier_receipt_contract.sh` | exit-1 residual = e8-v4, by design |
| e8-v4 signer repair, v3 (two defects fixed, three-agent review) | `artifacts/operator/e8v4_keyed_receipt_20260812.patch` | `51738208`, **not applied** |
| SC17 ledger future-stamp guard + 6 tests | `scripts/vidya/ledger.py` | `a2a6d503`, suite 371 green |
| Judge-prompt priming fix (calibration block → generic anchors) | research `score_with_claude.py` | research `9501b353` |
| CJ-1a GPQA 198/198 re-confirmed via the adapter itself, offline | `canonical-judge-suite-revamp.md` | `921113ed` |
| CJ-1b size anchor **corrected 140K → ~5.7M** (T5 arithmetic flag proven) | same | `921113ed` |
| **HS-OD-1**: unhonoured OpenAI body fields now 422-with-field-name; `max_completion_tokens` implemented | orchestrator `src/api/models/openai.py` + 30 tests | orch `cbe551e8` (**pushed**; reload routed to inference) |
| scoring-infra 1b closed **by exhaustion** (per-consumer proofs verified in git) | `scoring-infra-standardization.md` | `a4f0860f` |
| ID-7 `ordered_subsequence` verifier, both metrics, empty-config refused | research `answer_scoring.py` + 8 tests | research `9cc8db2d` |
| toc L449 **audit half**: live peek is file-capable; spill pointers followable | `tool-output-compression.md` | `40aa9d38`, `723a3539` |
| ID-12 closed landed-elsewhere (git evidence) + stale-open :109 tranche-state annotation | two handoffs | `13ff61d6` |
| KVQuant decision package (exact retrieval parity; rec A) | `docs/reviews/kvquant-27b-decision-package-20260812.md` | `b455101e` |
| P0 merge: four dashboard paths adjudicated (proven superset, 91+12 tests) then the final toc conflict (one-token anchor adjudication) | worktree → `c0387984` | msgs 234/241/246/250 |
| Void-gate sweep, mainC 3-pull review, debugbench adjudication, morning notes | artifacts + bus | `1ea430e8`, `83872df8`, `e5083163` |

## 2. Found without being asked

1. **`scripts/validate/check_ratification_receipts.py` is fully orphaned** — guards the
   human-amendment-only measurement boundary, landed 08-02, ZERO references anywhere since.
   The most invisible gate in the ratification path (full table in the flurry-audit addendum).
2. `index_state.py --check`: CLAUDE.md binds it with "must exit 0 before committing" and no
   mechanism runs it — post-commit hook is generate-only with exit discarded.
3. `verify_llama_cpp.sh` failure is warn-and-continue inside `session_init.sh` — a
   wrong-branch kernel produces one banner, then exit 0.
4. The bench adapter's `datasets` dep lives **only in system python3** — venv-invoked runs
   take the adapter's fail-open path (one stdout line, 0 items, no abort).
5. Research and orchestrator each have a `scripts/benchmark/debug_scorer.py` — **unrelated
   modules, same path** — a name collision that nearly produced a false negative during 1b.
6. Latent spill-pointer hazard: installing RestrictedPython + flipping `restricted_python`
   silently makes every `_spill_if_truncated()` pointer unfollowable (annotated in toc L449).
7. The E8 final-c1 token is **unspent** and superseded (v5 final-c1 completions + E9 era) —
   became the `e8-token-retire` recommendation.
8. The freeze-lift sequencing race (lift announced while main had not fast-forwarded, three
   append buffers primed) — flagged before it fired; superseded by merge-inside-quiesce.
9. DebugBench refinement on mainC's finding: echo-pass and boilerplate-vacuity are **two
   distinct mechanisms** and one flagship sentence overstated by one row (`msg-248`).

## 3. What I got wrong, and how it was caught

| # | Error | Caught by |
|---|---|---|
| 1 | Refuted mainA's `--validate-only` finding from the shared **working tree** + HEAD dates — the "fix" was mainB's uncommitted hunk; my refutation predated the commit by 20s | Self, timeline re-derivation vs git; retracted at full volume; now catalogue face 3's instance |
| 2 | Claimed a banner-enumeration gap ("seventh box") with the wrong mechanism | mainD counted; mechanism retracted (loss-mode substance later vindicated by mainC) |
| 3 | Piped my own checker through `grep MISSING-WRITE`, hiding flags it raised | Self, on re-read — a filtered check cannot say what you didn't ask |
| 4 | Stage-capture loop: shell `$st` expansion failed, `2>/dev/null` laundered it into all-empty "no stage" reads on a UU path | Self — all-zeros is the vacuous-read signature (face 8); re-ran with literal commands |
| 5 | Two wrong-path greps nearly concluded "cross-reference missing" (debug_scorer collision) | Self — verify-negatives rule; widened search before concluding |
| 6 | Declared exhaustion, then the drain delivered 9 items | Self — final-drain discipline; protocol now: drain **before** declaring |
| 7 | Planned a T8 fan-out on a wrong premise ("more files remain") | Self — read my own T7 artifact first; it says non-live-owner certification is COMPLETE |
| 8 | `grep\|head` + `$status` read head's exit; a failed glob aborted a compound grep | Self — both re-run unpiped before concluding |

Common shape, same as the fleet's: every one silent by construction, none failed loudly; the
catches all came from reading the artifact instead of the report, or from a number too clean
to be true. Two sweeps of my uncommitted lane entries (`6ef76348`, `74855be7`) and one sweep
**by** me (`13ff61d6` took mainD's probe-line removal) are part of the night's 8-instance
shared-file record — content intact in all three, carrying commits misattributed, no reverts.

## 4. Open, with the specific next action

| Row | Next action | Gated on |
|---|---|---|
| toc L449 build half | A/B owner supplies the artifact **event schema** (question written in the row; hook point documented) | owner input |
| T8 certification | regenerate the dispatch queue, then certify what it emits; live-owner files stay excluded by policy | merge landing |
| stale-open :103/:104 handoff moves | execute the git-mvs | merge landing (their renames collide) |
| stale-open :109 dashboard field | finish the partition, then derive the field | T8 |
| e8-v4 v3 patch | operator `git apply` — **or mooted by `e8-token-retire`** | operator |
| DebugBench oracle rebuild | mainC opened the remediation row; needs an eval-pipeline owner | routing |
| HS-OD-1 activation | API reload at inference's own boundary (routed, no urgency) | inference |

## 5. Needs the operator (pointers — the package items)

All three of mine are consolidated in **`artifacts/operator/auditor-morning-note-20260812.md`**:
C39 park (two defects, exact attribution), KVQuant adopt/keep/rerun (rec **A**), and
**`e8-token-retire`** (rec **a** — closes the checker's only MISSING-WRITE without touching a
signer; distinct from mainB's `e8-era-pin`, disambiguated in both handovers). Also standing
from my lane: the unwatched-gates table (headline: item 2.1 above), the effect-gate
threshold-vs-martingale finding routed URGENT to inference, and the research-repo 10/136
divergence (mains' side backed up on `wrapup/research-mains-20260812`).

## 6. One process note

The night's most reusable artifact is mainB's verification-failure catalogue — **eleven** faces
(count re-resolved at 04:40; it was nine when this document certified), five agents, all
measured. My contribution to it was involuntary (face 3's instance) and voluntary (spotting
face 9's kin), and the mechanism that made every catch work is now fleet doctrine three times
over: **a metric can flag candidates; only the artifact settles them.**

## 7. Post-certification addendum (04:40Z) — the re-stale check, run on this document

A handover is certified at a timestamp and read at a later one (mainB's hazard, reproduced by
mainA on their own document, now run on mine — three decays found and fixed here):

1. **The night's highest-severity finding post-dates §1–§5**: mainA's merge-abort blocker —
   `agents/shared/HARNESS_RUN_POLICY.md` untracked in `/workspace`, blob-identical to the
   incoming add from origin/main, aborting the §4 fast-forward on worktree safety. I verified
   it independently twice (`??` status + `git hash-object` = `d1430bd7…`; then the revised
   form: `b5054029` is an ancestor of origin/main and not of local main, so **every rebuild
   reintroduces it**). The one-command remedy is a mandatory pre-step in the committed runbook
   (`9c8fd6fe` :130). Face 11 came out of it: every readiness metric models one subsystem.
2. **Two late errors of mine for the §3 table**: (9) compared `sha1sum` against a git blob id
   when re-verifying the stray — different hash domains, caught before concluding, re-run with
   `git hash-object`; (10) asked the coordinator to commit "your document" — authorship
   unverified; the runbook wasn't theirs and was already committed by the operator. mainA ran
   the authorship check I skipped.
3. **The catalogue count in §6 expired within the hour** — fixed in place above, and the
   lesson generalized: a self-referential count in a certified document is a claim that
   expires; where possible cite the resolver, not the total (mainA's fix, adopted).
