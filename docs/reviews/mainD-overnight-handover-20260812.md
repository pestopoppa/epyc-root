# `mainD` — overnight handover, 2026-08-12

**Lane**: `none` throughout — no inference, no benchmarks, no servers, no region claims. Compute went
live overnight and I stayed clear of it. No signer was edited. The merge was never committed or pushed
by me.

**Scope**: C-OWN, the session-bus delivery plane.

Authorship note: every agent commits under one git identity, so the `author` field proves nothing.
The hashes below were attributed by **path and content**, not by author.

---

## 1. What I finished — a list you can verify

| Commit | What it does |
|---|---|
| `48648df2` | **C42 never fired from the loop.** The stale-source check was wired into `check_once`, which the supervisor's *healthy* path skips — so it had never run. Also makes C43 lock contention name its holder. |
| `1ecb91ae` | **C43 second half** — bounded lock retry (`flock -w`) closing the relaunch race against a dying holder. |
| `f5f8ad97` | **The bootstrap chain closed in production, 00:45:19Z.** Stale supervisor → undetected stale daemon → un-run rotation. One restart collapsed all three: `advisory.jsonl` 1,044 MiB → 0, 660 flags preserved across shards, daemon CPU 29.5% → 1.8%. |
| `f83d7871` | **C42 ported to the dashboard hub** — `hub_supervisor.sh` now detects a hub serving code older than `dashboard/`. Needs no host change. |
| `032164aa` | **C39 spent-gate notice** — `token-queue.md` stops misleading a reader who has only that file. Append-only; never ticks a checkbox. |
| `9d741ed4` | C39 advice no longer instructs an agent across the trust boundary. |
| `3c6e6b6a`, `eb0df7cd`, `d73fc421` | **C34 residual disposition** — triaged by value rather than by count; of 81 rows, exactly one was worth re-filing. |
| `28139999` | **HG-3**, and a fourth screening signal in `backlog_row_check.py` (below). |
| `bd2e830d` | **C44** — the token relay is withdrawal-blind (below). |
| `4007ceba` | **The trust-boundary guard's pytest wrapper passed with an empty case table.** `main()` returns `0` when there is nothing to fail. Mutation-verified; floor added. Also commits the superseded `.sh` test whose deletion `mainA` flagged as unowned. |
| `23dc960d` | Catalogue **faces 10 and 11** — `mainB`'s sentinel-that-is-also-content, and `mainA`'s instance under the readiness-metric generalisation. |
| `03369bb0`, `e4cb8373` | C39 keyed-receipt patch **prepared and NOT applied**, as instructed. |
| `9ec9da54` | **Withdrew my own patch** after review found a hole in it. It stays withdrawn. |
| `5bdf59f5`, `74855be7`, `c27fe838` | Lane write-ups, including the P0 merge resolution and the freeze-window findings. |

Also closed and written up: C23, C28, C37, C38, C40, C41, A19, R1, R2, M5b, and verification of
C11 / C22 / C18a.

**Not closed, and it is yours**: **C39 is PARKED.** The single artifact is v3
(`artifacts/operator/e8v4_keyed_receipt_20260812.patch`) and it is **not applied**. It has two known
defects. The worse one is `mainA`'s: a hard *refuse-on-index-exists* — an idiom lifted from the
one-shot ratifiers — **would have broken this host**, because `mint_receipt` here is verify-or-continue
and re-run-after-crash is the *designed* recovery path. Do not sign it as it stands.

---

## 2. What I found that nobody asked me to look for

**C42 could not bootstrap itself.** I went to verify my own shipped work rather than assume it had
taken effect, and found the watchdog that detects stale daemons was itself stale — it predated its own
check by fourteen hours and had logged zero detections. The failure is recursive, and it is the
strongest argument yet for the OP-9 cron decision: *a self-healing mechanism cannot heal the process
that would have started it.*

**C44 — the token relay is withdrawal-blind** (fixed, `bd2e830d`). C39 taught the relay to notice a
gate already *signed*. Nothing taught it to notice a gate the **requester withdrew**. A withdrawal
leaves the block unchecked and byte-identical to a live ask, so the escalation ladder chases you about
it. Measured: a gate filed 01:21, withdrawn 01:41, still escalating at 04:01 — asking for your
signature on a patch its own author had stopped standing behind. Two tiers, because a withdrawal
signal that is *too broad* suppresses a live operator ask, which is the same defect inverted and worse.

**A fourth dispatch-screening signal** (`28139999`). A row can be blocked by the handoff's own
**Dependency Graph** — a block invisible to both the row text and the child-box check, which is exactly
how the queue served a blocked row as `none` lane with no blocker. Measured 12 of 2,177 open boxes
(0.55%), every hit gated verbatim.

**The freeze set was derivable in one command.** `git merge-tree --write-tree --name-only A B` — its
`Auto-merging` lines are byte-identical to the two-diff intersection of both sides' changes. Freeze
that set; resolve the `CONFLICT` subset.

**A sequencing correction, and it is the one that matters for the reboot.** The fleet was asked to
commit in-flight edits on four paths so the merge could "fire instantly". All four were *inside the
merge's own 70-path changed set*, so committing them re-conflicted the merge — which is what happened,
three fresh conflicts, within minutes. **A merge cannot be pre-baked while the tree is still moving.**
The right order is the one the coordinator themselves proposed: quiesce → merge → push → reboot, with
the merge recomputed *after* quiesce.

---

## 3. What I got wrong, and how it was caught

Every one of these was caught by someone else, or by a check I nearly skipped. That is the pattern
worth preserving.

- **I swept a peer's uncommitted lane section into my commit** (`ece707b6`). A pathspec commit filters
  *paths*, not authorship *within* a path. Caught by `mainA`, whose next commit failed with "no changes
  added to commit".
- **I accused myself of a sweep that never happened.** My own pre-commit check showed `mainC`'s heading
  in the added set; they committed in the gap between my check and my commit, so I wrote a stale
  reading into a permanent commit message as a claim about a colleague. Retracted. The fix is to verify
  the **artifact** after committing (`git show <sha> -- <file>`), never the intention before.
- **I twice reported a commit as failed when it had not failed**, citing `git rev-parse HEAD` — which
  in a five-agent clone handed me *another session's* commit, twice, and I cited it as evidence.
- **A corpus measurement that read 0.00%** across 460 files, because `_boxes()` strips the state so an
  open box is `""` and not `" "`. A clean 0.00% is the empty-input signature. Asserting the *input
  size* caught it; reading the number never would have.
- **I proved a conclusion with an empty read.** `git show <ref>:<path> 2>/dev/null | grep -c` returned
  0 on both branches and I took it as evidence — the file had read **zero lines**; my `2>/dev/null`
  laundered an error into a plausible zero. The conclusion happened to survive; the evidence did not.
- **The freeze set was in my own output and my filter discarded it.** I reported "two conflicts" from a
  `merge-tree` run that had printed the third path as an `Auto-merging` line. I was grepping for
  `CONFLICT` and read the rest as noise, which helped put the coordinator on the wrong basis and left
  an agent committing to an unflagged file. **When you grep a tool's output you inherit its
  vocabulary.**
- **I fixed three stale counts in the catalogue and left three more standing** (`23dc960d`). I had
  grepped for the exact phrases I expected — `nine ways`, `The nine faces`, `the eight questions` —
  and corrected precisely those, while `nine distinct mechanisms`, `three of the nine faces` and
  `none of the nine tests` survived untouched. That is face 4 (*assertion pins a spelling*) applied
  to an **edit** rather than a check: I audited my own change with the same too-narrow pattern that
  produced it. `mainA` caught it and it became face 12's own instance. The fix is to grep for the
  **property** (`\bnine\b`) and adjudicate each hit, not for the spellings you remember writing.
- **A guard I wrote forbade its own documentation** — it grepped module source for a phrase the fix's
  own comment quotes. Rewritten to assert against the produced notice and check polarity.
- **I told the fleet to trust `git merge-tree` for merge readiness.** It models the **index**; the
  merge aborted on **worktree safety**, which no conflict metric inspects. `mainA` caught it. The
  auditor and I had both run it correctly and both got the right answer to the wrong question —
  which is why the catalogue entry it became is marked as failing *open while carrying independent
  confirmation*. Two agents agreeing does not widen a metric's domain.
- **A mutation test that could not fail.** Probing the trust-boundary wrapper, I ran the mutant from
  a temp dir outside the repo; it reported `1 error` — neither pass nor fail. A mutation the
  instrument cannot import is not a mutation test. Re-run in place it *passed*, and that pass was
  the defect I was looking for.
- **I echoed "uncommitted work does not survive a reboot"** and used it to justify urgency. False —
  `/workspace` and the tmp and memory dirs are one persistent RAID. `mainA` proved it; the
  coordinator corrected their own broadcast in the same channel. Committing is still right, but as a
  *concurrency* argument, not a durability one.
- **I mis-suspected four files of holding stale reverted content** (`b41af9d7`'s signature) and nearly
  raised a false alarm. I was reading *dates in the content* as the direction of the change; all four
  were the newer state.

---

## 4. Filed, not done — `C45`, sized

`logs/agent_audit.log` is git-tracked, append-only, and written concurrently by every agent. Both sides
always append at the tail, so it conflicts on essentially every cross-branch merge — it conflicted on
this one, and it was one of the four files blocking the merge at 03:45Z. Pure merge tax, no
informational benefit from being tracked.

**Recommendation: option 1 — untrack and gitignore it**, exactly as A19 did for the generated index
sidecars. The audit trail lives on disk and is read via `agent_log_analyze.sh`; nothing reads it out of
git history. Cost is minutes, and the A19 precedent means the argument is already settled. Option 2
(per-agent shards) also works and preserves tracking, at more moving parts. **Reject option 3**
(`merge=union` driver): it makes the conflict disappear while silently reordering chronology — it would
pass every check and produce a log nobody can trust to be ordered, which is the fail-open shape we
spent the night eliminating.

One caveat on option 1: `git rm --cached` alone will *not* untrack it, because a pathspec commit
re-reads the worktree and resurrects the file. It needs the file absent at commit time — `mv` aside,
commit, `mv` back — and verification with `git ls-files`, not by reading `.gitignore`.

---

*Updated after first publication (`mainB`'s point: a handover is a snapshot that gets
certified while the fleet keeps moving — theirs was wrong twenty minutes after being declared
finished). Three commits and three errors landed after this was written; they are folded in
above rather than appended, so the lists stay readable as lists. Anyone assembling the morning
package should re-resolve cross-references at assembly time rather than trusting any artifact's
internal counts, including this one.*
