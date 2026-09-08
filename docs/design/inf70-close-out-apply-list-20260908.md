# INF-70 close-out — what the OPERATOR must apply under the wrap-up lease

Prepared 2026-09-08 by the `inf70-audit` wrap-up. **Nothing in this file has been applied.**
Everything else in the wrap-up is already committed on `lane/inf70-audit-20260902`.

Constraints honoured: no push, no promotion, no merge, no lease taken, no wiki compiled, no index
row written, no bench region lock, no inference, nothing written outside `/mnt/raid0/llm/`, and
`/mnt/raid0/llm/llama.cpp` untouched.

---

## A. LANE IS BEHIND `origin/main` — resolve this FIRST

`lane/inf70-audit-20260902` was **0 ahead / 33 behind** `origin/main` (`edd9d95a`) at wrap-up start;
every earlier commit of this session was already promoted. The autokernel lane has since landed
**CHAMP-3** and the **THP-shim adoption** on `main`.

**No conflict on this session's files.** `origin/main`'s new commits touch only
`autokernel-*.md`, `non-inference-backlog.md`, the two indices, and their own progress files.
`cpu-decode-roofline-program.md` and `progress/2026-09/2026-09-08-inf70-audit.md` are untouched
there, so this lane's edits apply cleanly.

**Order (the skill's SYNC-FIRST rule):** acquire lease → `git merge origin/main` → regen → promote →
release. Regenerating before the merge computes the generated block from stale inputs.

---

## B. INDEX ROW — PREPARED, NOT WRITTEN (one row, one cell)

`handoffs/active/inference-research-index.md`, the **INF-70** row. Its `Next action` is stale
(SYNC-19/20 are complete). Apply against **`origin/main`**, not this lane's copy — the lane's index
is 6 commits stale.

**FROM:**
```
| INF-70 | cpu decode roofline program | [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) | SYNC-19/20 measuring; then C0 DRAM bandwidth under the recipe, then C5 re-anchor sweep on the hot harness; OP-40 is the operator gate | INF-67, INF-10, INF-63 |
```

**TO:**
```
| INF-70 | cpu decode roofline program | [cpu-decode-roofline-program.md](cpu-decode-roofline-program.md) | CLOSED 2026-09-08: champion = ef81196d5 + GGML_NOHUGEPAGE_PROCESS=1 at launch; next WRAP-10 lands PROD-1's recipe module; OP-40 unruled | INF-67, INF-10, INF-63 |
```

`Next action` = **135 chars** (limit 140). Only the fourth cell changes; ID, Track, Handoff and Deps
are untouched. No row is added, deleted or re-pointed.

**No other index needs a row.** The survey found campaign hits only in `inference-research-index.md`
and `master-handoff-index.md`; the other six indices have zero. Every other matching row
(INF-65/66/73, OP-40/41) belongs to the autokernel campaign and is already current on `origin/main`.

---

## C. THE GENERATED BLOCK IS STALE — the one thing that needs the lease

```
$ python3 scripts/handoffs/index_state.py --check
cite-check: clean — 1 citation(s) across 1 document(s)    record=1
FRESHNESS: master index generated block is stale — run without --check
1 problem(s)
```

Everything else passes: **0 duplicates, 0 row-id collisions**, no orphans, no dead links, no
malformed rows, no over-long `Next action`, no unresolved `Deps`, cite-check clean.

Under the lease, after the merge in §A and the row edit in §B:
```
python3 scripts/handoffs/index_state.py           # regen
python3 scripts/handoffs/index_state.py --check   # must exit 0
```

---

## D. INDEX PRUNING — SCREENED, AND THE ANSWER IS NOTHING

```
PRUNE CANDIDATES: 0 of 174 handoffs
```

**Nothing to prune this wrap-up.** Screened with the generated signal, not `open == 0` (that
predicate was 13-of-15 false positives when measured 2026-08-18).

Campaign handoffs and their named blockers:

| Handoff | row | open | closed | blocker |
|---|---|---:|---:|---|
| `cpu-decode-roofline-program.md` | INF-70 | 66 | 85 | `open-tasks` |
| `batched-decode-measurement.md` | INF-07 | 11 | 43 | `open-tasks` |
| `autokernel-champion-aggregate.md` | INF-65 | 7 | 14 | `open-tasks` |
| `cpu-fused-decoder-blocks.md` | INF-67 | 3 | 5 | `open-tasks` |
| `autokernel-rebuild-program.md` | INF-66 | 61 | 85 | `open-tasks` |
| `autokernel-unified-surface-program.md` | INF-73 | 30 | 6 | `open-tasks` |
| `cpu-prefill-compute-large-models.md` | INF-09 | 1 | 27 | `open-tasks` |
| `numa-placement-defect-20260730.md` | INF-43 | 9 | 36 | `open-tasks` |
| `cpu-shape-specialized-gemv-decode.md` | INF-10 | **0** | 8 | **`undispatchable-tasks`** — 36 guarded boxes |

**Two rejections worth an operator eye, neither actioned here:**
- **INF-10** is the only campaign handoff whose row and checkbox state disagree: 0 open boxes, but a
  `Next action` ("next: re-rank levers from the receipts") that no open box backs. Not a prune
  candidate under the rule; it is either a missing checkbox or a stale cell. **A screener proves
  WELL-FORMED, not STILL-NEEDED** — this needs a read, not a rule change.
- **INF-09** is 1-of-28 open with `last_advanced` **2026-07-29**, ~6 weeks stale — the oldest advance
  in the set.

---

## E. HANDOFF COMPACTION — PROPOSED, NOT EXECUTED

`cpu-decode-roofline-program.md` is now **5,010 lines** and the campaign is closed, so the trigger is
met on the qualitative test: the first screen no longer answers "what do I do next?" **The header was
rewritten this wrap-up so it does again** — the split below is the structural half.

Proposed split, ~29% reduction (5,010 → ~3,600 active):

| Active path | Sibling path | Action | Reason |
|---|---|---|---|
| `handoffs/active/cpu-decode-roofline-program.md` | `handoffs/completed/cpu-decode-roofline-program-completed-through-2026-09-08.md` | **split out ~1,327 lines** | Landed/validated phases that remain evidence: Axis A (76 ln, all 5 boxes ticked, NO-GO closed via SYNC-5), Disk (26), RECLAIM-1 (82, executed), Operator-goal (18), Deployable-serving-speed (55, numbers now superseded), Ordering (15), Research-intake (5), and the **settled ~1,050 of CHAMPION KERNEL's 1,154** (SYNC-1/3a/4/5/7/8/9/11/12/13/14, D6-PLACE, MERGE-1, HYG-1b/2/3, PLACE-1, UP-1, B10/B11/B12, the INF-71 pointer). |
| `handoffs/active/cpu-decode-roofline-program.md` | `handoffs/archived/cpu-decode-roofline-program-history-through-2026-09-08.md` | **split out 43 lines** | The 2026-09-02 Audit log — a pure day-1 correction trail, no forward-looking content. |

**Carried forward into the active file, NOT moved** (~79 lines): CHAMPION KERNEL's 7 still-open items
— CHAMP-1, SYNC-2b, SYNC-3b, SYNC-6, METH-1, HYG-2b, and the SYNC-10 duplicate (now ticked).

**Stays active**: header/preamble, Why-this-model, Scope, the gap ledger (its 99.1 ms / 153 GB/s
numbers are cited by name throughout live sections), Reporting, Axes C/D/B/S, OP-35/PROD (PROD-1 is a
key-file reference; PROD-2/3 open), CHAMPION-3 (the *champion is always current* standing rule), both
STANDING RULE sections, the 2026-09-08 findings + Tasks-filed, WRAP-1..12, CLOSE-1..11, Axis E, and
Concurrency (**G2-CONC is a blocking promotion gate**).

**Safety check, explicitly:** every proposed move span was read in full. **No open checkbox, no
blocking gate (G2-CONC, PROD-2, PROD-3, CHAMP-1, MEAS-1/OP-40/OP-41), no standing rule and no
currently-cited key file is in the move set.**

Reciprocal banners required on execution: `Completed Scope` link in the active file; *"Historical
ledger only; current work lives in `../active/cpu-decode-roofline-program.md`"* in each sibling.
**Index handling: no new rows** — indices keep pointing at the active handoff only.

**Row deletions: NONE proposed, and none would follow from this split** (a partial compaction never
`git mv`s the active handoff, so INF-70's row and path are unchanged). Per your instruction, any row
deletion is yours; there is nothing here to hand over.

**Not attempted, and why:** Axis S (925 ln) and Axis E (947 ln) are the obvious phase-2 candidates
for finer sub-item extraction, but both are single undivided blocks with dense internal
cross-references. Splitting them needs a reference audit first, not a wrap-up.

---

## F. PROD-1 / WRAP-10 — THE THP KNOB IS IN THE DRAFT; DIFF READY

Diff: **`/mnt/raid0/llm/tmp/inf70/wrapup-20260908/PROD1-THP.diff`** (433 lines).
Backup of the pre-edit draft: `/mnt/raid0/llm/tmp/inf70/wrapup-20260908/prod1-draft-backup/`.
Edited in place at `/mnt/raid0/llm/tmp/inf70/agents/prod1/draft/`. **Tests 43/43 green** (was 38/38).

What changed:
1. **`CHAMPION_GGML_ENV` now exports `GGML_NOHUGEPAGE_PROCESS=1`.** The launcher restates no
   constants and reads this map, so it inherits the knob with **no edit**.
2. **`CHAMPION_KNOBS` entry moved** from `("off","leave unset", …pooled +0.16%, 73/120 = zero)` to
   `("1","export", …)`. The old note quoted an **arm-unit** result for a **session-unit** knob.
3. **New `THP_SHIM` record** carrying **unit = SESSION**, `set_at = LAUNCH`, mechanism
   `prctl(PR_SET_THP_DISABLE)` before the 92 GB allocation, exact **α = 0.0430 enumerated over 2¹⁰
   sequences** alongside the **0.078 a union bound would have given silently**,
   `magnitude_claimed = False`, the 6 pair effects, the OFF/ON sd pair, the launches-per-CI table,
   and the 1200-fold-error warning.
4. **The `GGML_NOHUGEPAGE` vs `GGML_NOHUGEPAGE_PROCESS` distinction spelled out in full** — madvise
   on the model buffer vs process-wide prctl in an ELF constructor; already-on vs opt-in; and the
   gating (`GGML_NOHUGEPAGE=0` is a master off that silently kills both).
5. **A defect found and fixed**: `PRECONDITIONS["thp_readback"]` used **AnonHugePages/Rss**, which
   the fold record proves is **not a valid discriminator** (0.06% of Rss at load, ~6% minutes later
   on the same process — pass or fail depends on *when* you looked). Replaced by a fail-closed
   **`THP_enabled` in `/proc/PID/status`, read once per LAUNCH**; the old read is retained but
   renamed `thp_readback_madvise_only`, named for what it can actually decide.
6. **`FLOORS` table — every floor now carries its unit**, plus a `MEASUREMENT_UNITS` register.
7. **`CURRENT_CHAMPION`** (ef81196d5 + recipe, four lineages by ancestry, FOLD-2 gates, and a
   `do_not_fold` list) and **`CHAMPION_PIN_RESOLVED = False`** with `CHAMPION_PIN_GAP`.
8. **`HEADLINES["champion_final_20260908"]`** = the 18-launch characterisation, carrying **both
   caveats** and the supersession list; `CANONICAL_HEADLINE` re-pointed to it; the prior two entries
   given explicit `status` supersession notes.
9. Five new guard tests: the two THP knobs must not collapse into one entry; the shim must not be
   verified by the invalid discriminator; every floor must carry its unit; the pin gap must be
   declared not hidden; the `do_not_fold` list must be carried.

**★ A rot trap fixed in passing:** `test_canonical_headline_is_the_champion` asserted the literal
string `"champion3"`. It became **wrong the moment the champion moved** and would still have passed
every other test. Rewritten to assert the **property** — the canonical headline names the current
champion and is not a superseded entry, and every non-canonical entry must *say* it is superseded.

**⚠ TWO THINGS THE OPERATOR MUST DECIDE BEFORE WRAP-10 LANDS:**
- **The pin is unresolved and the module says so.** `CHAMPION_*` still names champion3 (build 10241,
  digests measured); `CURRENT_CHAMPION` is `ef81196d5` with **no build number and no digests**.
  Either rebuild and re-digest at `ef81196d5`, or land with `CHAMPION_PIN_RESOLVED = False` and a
  loud preflight refusal. I did **not** invent a digest.
- **Adopting a launch-time knob CHANGES THE MEASURED CONDITION**, which invalidates a recipe's floor
  until re-calibrated — the same rule `cpu_list` carries in `serving.py`. The 18-launch headline was
  measured *with* the knob, so it is consistent; **every earlier headline on that module was not.**

**Scratch is the risk.** The drafts live in `/mnt/raid0/llm/tmp/inf70/agents/prod1/draft/` and **are
lost with it**. WRAP-10 is the task that lands them; MEAS-5's `build_locked.sh` and CLOSE-2's
`gate.py` guards should ride the same pass.

---

## G. WIKI COMPILATION SWEEP — ASSESSED AND DRAFTED, NOT COMPILED

- Assessment: `/mnt/raid0/llm/tmp/inf70/wrapup-20260908/wiki-assessment.md`
- Draft: `/mnt/raid0/llm/tmp/inf70/wrapup-20260908/WIKI-DRAFT.md`

Scanner run read-only (**no `--touch`**, `git status --porcelain wiki/` empty before and after):
**`total_new = 11`** — 8 `handoff-active`, 2 `progress`, 1 `docs`; drift 2 added / 9 changed / 1
removed (`progress/2026-08/2026-08-25.md`).

**Two scanner caveats:**
1. The stderr linked-worktree warning is a **false alarm here** — the default incremental path diffs
   **content hashes** against the tracked manifest, not mtimes, so `total_new = 11` is valid from a
   lane. The warning text is stale relative to the code it guards.
2. The reported `last_compile` (`2026-09-07T14:04:28Z`) comes from the **untracked** `wiki/.last_compile`
   and is ~19 h behind the **tracked** manifest's `2026-09-08T09:28:51Z`. Selection is unaffected;
   **do not quote the displayed watermark as the compile date.**

**Ordering that was a blocker and no longer is:** the assessment correctly flagged that none of the
five findings existed in a tracked source, so `writer_evidence_policy` (≥3 refs, `verified`) could
not be met. **This wrap-up landed them** in `progress/2026-09/2026-09-08-inf70-audit.md` and the
roofline handoff, so the source-first ordering is now satisfied. Re-run the scanner after merging
this lane so those sources enter the delta.

Targets: **two pages, one new H2, no new page, no new taxonomy category** —
`benchmark-methodology.md` (new H2 appended: precision, unit rule, vacuous-instrument pattern) and
`hardware-optimization.md` (extend-and-partially-correct the SMT section; supersession banner; new
champion H3).

**★ The one thing not to paste mechanically:** the new DRAM-bandwidth finding does not merely extend
the 2026-09-07 SMT section — **it bounds that section's prescribed remedy** (occupancy sampling), and
it puts pressure on the MEAS-1 *"PEAK, not total foreign load"* discriminator already compiled on
that page. Write the reconciliation deliberately; do not leave two sections disagreeing.

Post-compile order (unchanged): compile → `cite-check` if any `intake-NNN` → `lint_wiki.py` →
`compile_sources.py --check-manifest` → **then** `--touch` → commit the regenerated tracked manifest
with the pages. **OP-34 is open and relevant**: `--touch` has no scoped form, so it advances a
fleet-wide watermark past sources this compile did not cover.

---

## H. ID DISCIPLINE — allocated from `origin/main`, and what is BURNT

Ids used this wrap-up: **`CLOSE-1` … `CLOSE-11`** (prefix verified **unused** at `origin/main`) and
**`MEAS-7`** (next free).

**One collision found and fixed:** two different tasks both carried **`MEAS-6`** — the cross-campaign
contention measurement (`[x]`) and the "HARNESS-1 does not close MEAS-4" labelling task (`[ ]`). The
labelling task is renumbered **`MEAS-7`**; `MEAS-6` now means exactly one thing. That is the **fourth**
collision in two days (B7, INF-71, R23-49→OP-41, MEAS-6), on top of MEAS-2→MEAS-5 and DRIFT-1→DRIFT-5.

**★ BURNT — never re-issue:** `INF-71` (retired today; it reads as *free* in a grep of `origin/main`,
which is exactly the trap), `DRIFT-2` and `DRIFT-3` (claimed at allocation, text later removed, so
they also read as free), and every allocated-but-dequeued `OP-` id: OP-2, 4, 7, 8, 10, 11, 14, 16,
18, 21, 23, 24, 28, 30, 31, 32, 35, 36.

**Next free at `origin/main`**, for whoever mints next:

| prefix | next free | | prefix | next free |
|---|---|---|---|---|
| `PROD-` | PROD-4 | | `SYNC-` | SYNC-22 |
| `RETEST-` | RETEST-2 | | `FIX-` | FIX-4 |
| `MEAS-` | **MEAS-8** (7 taken here) | | `HARNESS-` | HARNESS-3 |
| `CHAMP-` | CHAMP-4 | | `DRIFT-` | **DRIFT-6** (2, 3 burnt) |
| `OP-` | OP-43 | | `STAT-`/`METH-`/`HYG-` | STAT-2 / METH-3 / HYG-4 |
| `R23-` | R23-62 | | INF-70's `B` / `G` | B13 / G5 |
| `CLOSE-` | **CLOSE-13** (12 used) | | `X-` | X-12 |

**The structural fix this keeps asking for:** ids are still minted from local context. The check is
one grep against `origin/main`, and a *lane* grep is not it — the lane was 33 commits stale today.

---

## I. NOT DONE, DELIBERATELY — with the named blocker for each

| Item | Named blocker |
|---|---|
| Lease-gated regen of the generated block | You told me not to take the lease. §C is the exact command pair. |
| Writing the INF-70 index row | Subagents PREPARE, the owning session APPLIES (ruling 2026-08-16). §B is the exact diff. |
| Compiling the wiki | Operator-cadence step; you told me to draft only. §G. |
| Push / promote / merge | Explicitly forbidden this session. §A is the sync the promoter must do first. |
| Executing the compaction split | Operator-cadence step; §E is the proposal, and it has no row deletions to hand over. |
| Landing WRAP-10 / CLOSE-2 out of scratch | Needs the `epyc-inference-research` repo and a decision on the unresolved champion pin (§F). |
| **Routing CLOSE-12 into `vidya-belief-substrate-program.md`** | That handoff belongs to another session; *handoff = whole scope theirs*. **CLOSE-12 is a real gap**: `VB-INF70-ARMS` is **arm**-unit, but the close-out headline is **launch**-unit, and an arm-shaped projection would grade the claim on a precision the run never captured — CLOSE-1's substitution, inside the grading ladder. The write side is cheap now and **impossible to retrofit**. Route it; do not let it lapse. |
| Ruling OP-40 / OP-41 / MEAS-6 | An operator decision, and it must be ruled **jointly** — deciding separately silently sets the other campaign's default. |
| Re-measuring anything | No inference, no region lock; the GPU session owns the host. |
