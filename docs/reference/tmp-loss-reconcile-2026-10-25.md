# workspace-58 tmp-loss reconciliation plan (2026-10-25)

Read-only investigation. Nothing was restored, deleted, moved or committed, and no handoff, FILLERS
or queue file was edited. Every handoff change is in `HANDOFF-DIFFS-PROPOSED.md`, prepared for
workspace-58 to apply. The per-path table is `LOSS-INVENTORY.tsv`. Working files are in `work/`.
This is separate from the loop-inputs audit in `/mnt/raid0/llm/tmp/ws58-loop-inputs-audit-20261025/`.

## 1. Summary

- Root `origin/main` handoffs/active (`97268ec0f`) cite **497** distinct `/mnt/raid0/llm/tmp/<x>`
  paths. **230** survive and **267** are missing.
- **23 of the 267 were never real losses.**
  - 13 are declared `**Scratch**:` roots that were never populated.
  - 10 are template fragments such as `ak-`, `dive-` or `...`.
  - That leaves **244 real losses**.
- **Class counts:**

  | Class | Count | Meaning |
  |---|---|---|
  | A | 102 | evidence for a ticked box |
  | B | 28 | input to open work |
  | C | 131 | historical; includes the 23 above |
  | D | 6 | unclear |

- **Class B blocking status:**
  - **17 SOFT**: reconstructible from session transcripts, with no compute.
  - **3 NOT-BLOCKING**: either a copy exists on disk or the task can re-point.
  - **8 HARD**: the raw measurement outputs or binaries are gone, so those rows need a regeneration
    or a re-scope.
- **No ARMED or QUEUED FILLERS row depends on a missing path.** Every non-COMPLETE row's paths are
  present, or are STOP or output flags that are absent by design. The only FILLERS citation of a
  lost path is `kqroute-build-20261003`, the prior evidence of the COMPLETE row `v11-052-gpu`.
  Compute that is armed now is not blocked.
- **Host backups cannot restore any lost tmp path.** The NIB2-92 job does not cover
  `/mnt/raid0/llm/tmp` (§4). It does back up session transcripts, and the transcripts are the main
  recovery route for authored text.
- Per-handoff counts are in `work/per_handoff.tsv`. The heaviest are:

  | Handoff | Lost citations |
  |---|---|
  | `gemma-challenge-kernel-techniques-v7.md` | 56 (54 A, nearly all 2026-07 runs; 16 have committed research `data/` copies) |
  | `numa-topology-cutover-resume-20260730.md` | 24 |
  | `vidya-belief-substrate-program.md` | 17, including 10 B |
  | `deepseek-v41-flash-evaluation.md` | 14, including 5 B |

## 2. What removed them, and when

| Event | When | Actor (as logged) | Approval reference | Mechanism | Real losses (A/B/C/D) |
|---|---|---|---|---|---|
| **E0** | 2026-08-23 | opencode ad-hoc session, no lane (`progress/2026-08/2026-08-23-disk-reclaim.md`) | "Operator then approved scope: **tmp/ scratch + worktrees (~280G)**" | Raw removal of "~15k stale loose files" (tmp went from 285G to 2.9G) plus 138 `git worktree remove --force`. This predates `guarded_rm.sh`, whose first audit line is 2026-08-28, so no per-path record exists. | 163 (76/5/78/4), attribution inferred (below) |
| **E1** | 2026-10-07T03:53Z | wrap-up `scratch_cleanup.py` via `guarded_rm.sh` (184-event wave) | wrap-up step ratified as RATIFY-SCRATCH-LIFECYCLE-20261004 | Files inside `ufh14-b4-20261005/` and `kvu16b-rootcause-20261004/` were trashed (B4bcd-RUNBOOK.md, B4f.md, B4g-1.md, HANDOFF_EDITS.md, REPORT.md). | 2 (B 1, C 1) |
| **E2** | 2026-10-20 13:44–13:53Z | ad-hoc session "shared clone, no lane" (`progress/2026-10/2026-10-20.md:26-34`; tools in `/mnt/raid0/llm/tmp/ds41-1017-swap/`; the manifest was built by subagent transcript `agent-ae82d0b3b639d5a1f.jsonl` of Claude session `e3953395…`) | "Operator-approved (2026-10-20) volume reclaim" (`reclaim_volume_exec.py` docstring); audit lines say "operator-approved 2026-10-20 batch purge" | `reclaim_volume_exec.py --execute` (70 cited paths) and `reclaim_tmp_pass2.py --execute` (3) ran `guarded_rm.sh`. **`purge_batch.py` then `shutil.rmtree`'d the batch out of `.trash` 20 s to 2 min later**, so trash residency was zero. | 74 (24/22/26/2) |
| **E3** | 2026-10-23T15:31Z | workspace-58 main, `trash-sweep.sh --older-than 7` | operator-approved "sweep trash now" (10-23) | Purged the 10-04..10-07 trash, including E1's files. | (completes E1) |
| E4 | 2026-10-24T15:41Z | workspace-58 scheduled `/mnt/raid0/llm/tmp/compute-flags/trash-sweep-20261024.sh` | same 10-23 approval | `--older-than 1`: purged entries trashed 10-20..10-23 about 24 h after trashing. No handoff-cited path lost here, but residency was again ≤ 1 day. | 0 cited |
| unlogged | between creation and 10-20 | unknown | none | No `guarded_rm` record; absent from the 10-20 13:0x scan (`tmp_scan.tsv`). | 5 (2 A, 3 C) |

**How the E0 attribution was inferred:**
- 166 of the 194 paths with no `guarded_rm` record were already cited on `origin/main` before
  2026-08-23 23:59Z.
- Nothing in `/mnt/raid0/llm/tmp` older than 2026-08-20 survives, apart from one root-owned dir.
- None of these paths was present in the 10-20 scan.
- The remaining 28 are the 23 non-losses plus the 5 unlogged paths.

**Which guard should have refused, and why it did not:**

- **E2: the citation check existed but was skipped for small entries.** The inline classifier that
  wrote `tmp_manifest.tsv` (recovered from the transcript, timestamp 2026-10-20T13:22:50Z) ran:

  ```
  refs = grep -rIl -F <name> /workspace/handoffs/active  if g>=0.02 else []
  ```

  So **2,518 of the 2,741 SAFE entries were never citation-checked** because they were under
  0.02 GiB. Of the 73 cited paths E2 removed, 72 were under 0.02 GiB, and **71 were cited on
  `origin/main` at the time**.
  - The executors re-checked only KEEP markers, mtime under 7 days, evidence-shaped names, git state
    and live-process references, never citations.
  - **KEEP marker absent** on all 73.
  - **Citation not checked** at plan time (size threshold), at execute time, or at purge time.
  - The trash-first window was defeated by the same-minute purge, which logged itself as
    `TRASH_SWEEP` and so looks like `trash-sweep.sh` output.
- **E0: no citation check at all for tmp.** That reclaim cross-referenced `models/` against active
  handoffs but not tmp loose files.
  - KEEP marker: not a convention yet.
  - Citation: not checked.
  - No trash: removal was raw.
- **E1 and E3: neither check reads handoffs.** `scratch_cleanup.py` KEEP-REFERENCED reads launchers,
  AK inputs, the manifest, the bus and crontab, but **not handoffs, FILLERS or the ledger**. It also
  matches full paths only and fails open on files over 2 MiB or on read errors. `trash-sweep.sh`
  never re-checks citations. KEEP marker: absent. Citation: not checked.
- **All events: the guards themselves have no citation check.** No guard (`guarded_rm.sh`,
  `trash-sweep.sh`, `scratch_cleanup.py`, `worktree_gate.py`, `autokernel_disk_sweep.py`) consults
  handoffs, FILLERS or the belief ledger. No hook blocks inline `rmtree` or `rm -rf` under tmp.
  Details with file:line are in `work/guards-design.md` §1.

**The same exposure is live today** (guards subagent, `work/guards-design.md`):
- Handoffs (active + blocked) cite 1,045 tmp paths, of which 381 do not resolve.
- FILLERS.md cites 655 tmp paths.
- The canonical ledger `/mnt/raid0/llm/state/vidya/ledger.jsonl` cites 250 tmp paths, of which
  95 are missing.
- The scratch-lifecycle ratification's own evidence dir `tmp/disk-audit-20261003/` is gone.

## 3. Class B: full list, recoverability and blocking status

The recovery sources for B were checked in order:
1. host backups;
2. other copies on disk (worktrees, AK campaign stores, `state/`, a same-name find);
3. committed copies (root, research and orchestrator trees and their histories);
4. the belief ledger;
5. transcripts;
6. regeneration.

| # | Lost path (tmp/…) | Event | Needed by (open box) | Recoverability | Blocking | Action |
|---|---|---|---|---|---|---|
| 1 | `a7-fire-20260813` (`a7-fire-all.sh`) | E0 | RE-MEASURE E5 Stage-B (batched-decode-measurement.md:847) | transcript heredoc (4 sessions) | SOFT | reconstruct the launcher into the research repo |
| 2 | `ak-alldims-handoff-20261004/PREPARED_ROWS.md` | E2 | AKX-ALL-1 (autokernel-all-devices-all-dimensions.md:162) | transcript Write | SOFT | reconstruct, hand rows to owner |
| 3 | `ak-seat-ab/driver.py` | E2 | OAB-4 (autokernel-orchestrator-actor-backend.md:142), VB-AK-SEAT-b2 | transcript Write+Edit (32 sessions) | SOFT | reconstruct into the orch repo |
| 4 | `champion-sidecar` (4 scripts + pre-K1 receipt) | E2 | TD-29.M4 / TD native re-runs (typed-decision-plane.md:54-56, 343) | scripts: Write; **receipt: lost** | **HARD** (baseline only) | reconstruct scripts; re-run the pre-K1 arm in the K2 window, or re-scope |
| 5 | `ds41-engram-profile` (2 patches) | E2 | DS41-C4/C4b | transcript Write | SOFT | reconstruct into artifacts/ds41/ |
| 6 | `ds41-scope-20260926` (watchdog, swap_*, numa_maps_probe) | E2 | DS41-C51, DS41-C113 | Write (probe: heredoc) | SOFT | reconstruct into research scripts |
| 7 | `gpu-backlog-20261006` (attempt scripts) | E2 | YARN-E1-MEM (gpu-serving-tie-in-program.md:285) | heredoc | NOT-BLOCKING | box already says rerun via gpu_window_executor |
| 8 | `gpuwin-standing/ratify_…_20261007.sh` | E2 | GPUWIN-STANDING-APPROVAL | transcript Write | SOFT | reconstruct, fill SHA, operator `--apply` |
| 9 | `guard-audit` (prove*.py, fixtures) | E0 | W6 seven fail-open guards | heredoc | SOFT | reconstruct as committed tests |
| 10 | `iqk-allow-20261003/ab-runs/20261003T174700Z` | E2 | VB-CPU-XFER-1 | **raw runs lost**; scripts in transcript | **HARD** | re-scope to the next run; optional CPU window ~1-2 h |
| 11 | `kqroute-build-20261003` (`ab_kqroute.sh`, `results/20261004T021143Z`) | E2 | VB-KQROUTE-1 | script: Write; **results lost** | **HARD** | re-point the first projection to v11-052-gpu (`tmp/v11-runs/052/`, KEEP); regen ~2 h GPU only if needed |
| 12 | `kv-sizing-8083-20261003/DECISION.md` | E2 | VB-SERVING-DF2 / SSU-F3 | transcript Write+Edit | SOFT | reconstruct into docs/design |
| 13 | `q38fn-lane-inputs-20261003/inbox/61-…md` | E2 | DS41-C107/C111 | **on disk**: `autokernel/campaigns/ak-q38fn-cpu-decode-20261003/store/inbox/` | NOT-BLOCKING | re-point |
| 14 | `q38fn-transfer-20261003/runs/20261003T172030Z` | E2 | VB-CPU-XFER-1 (also ticked XFER-1) | **raw runs lost**; report.py in transcript | **HARD** | as #10 |
| 15-17 | `r2110-build-{a,b,parent}` | E2 (13:44Z) | R22-4 (autokernel-rebuild-program.md:1135) | regenerable from pinned SHAs | **HARD** | check R22-4 is still live; rebuild ~3×15-30 min, build role |
| 18 | `ssuf5/moved_lineup.py` + fixtures | E2 | SSU-F18 ("commit before a disk reclaim removes it") | Write + heredoc | SOFT | commit to orch tests now |
| 19 | `ufh14-b1-20261003` (template toml, DESIGN-NOTE) | E2 | UFH14-B1c / B1e | Write+Edit | SOFT | reconstruct into docs/design |
| 20 | `ufh14-b4-20261005/B4bcd-RUNBOOK.md` | E1+E3 | UFH14-B4b/c/d | Write+Edit | SOFT | reconstruct into docs/design |
| 21 | `vidya-planner-receipt-proposal-20260925.md` | E2 | VB-AK-BELIEF | Write | SOFT | reconstruct into docs/design |
| 22-24 | `worker_general_{baseline_prompt_embeddings,irt_cold_start,keyed_irt_scores}_20260627_185242.*` | E0 | P5.2 (learned-routing-controller.md:521) | binary outputs; **regenerable** (`irt_cold_start_ab.py`, orch) | **HARD** | one CPU-quarter run ~1 h after verifying inputs |
| 25 | `worktree-inventory-20260926.md` | E2 | DS41-C41 | Write, but **stale** | NOT-BLOCKING | regenerate with `worktree_gate.py report` (read-only) |
| 26-29 | `wrapup-ec-{fold,gpublock2,kvu19b,maskskip}/INDEX_ROWS.md` | E2 | VB-FA-MASKSKIP-b/-c, VB-COHGATE-1, VB-SERVING-DF2 | Write+Edit | SOFT | reconstruct, owner applies rows |
| 30 | `yarn-inert-design-20261006/jetlong/longctx_skeleton.sh` | E2 | JETLONG-LONGCTX-RUN | Write (OPTIONS.md committed) | SOFT | reconstruct into research scripts |

The table has 30 lines for 28 inventory rows: the r2110 prefix is one row covering three builds,
and the three worker_general files are three rows.

**What each recovery source yielded for B:**
- **Host backup:** none.
- **Committed copy:** a partial one only, `artifacts/yarn-ctx-20261006/OPTIONS.md`.
- **On disk:** 1 (#13).
- **Ledger:** none for B.
- **Transcripts:** 17 SOFT plus scripts for 4 HARD.
- **Truly unrecoverable bytes:**
  - the raw A/B run outputs for #10, #11 and #14;
  - the pre-K1 TD receipt (#4);
  - the June IRT binaries, which are regenerable (#22-24);
  - the r2110 builds, which are regenerable (#15-17).

**Compute needed for recovery:**
- SOFT and NOT-BLOCKING rows: none.
- HARD rows:
  - about 1 CPU-quarter hour (P5.2);
  - about 1.5 h of build-role CPU (r2110);
  - one TD bench arm inside K2's own window.
- Optional only if a live decision needs the old numbers: 2 CPU timing windows (XFER) and 1 GPU
  window (kqroute). Re-pointing kqroute to v11-052 avoids that GPU window.

## 4. Backups (NIB2-92) and other recovery sources

**NIB2-92 does not cover tmp:**
- NIB2-92 (`non-inference-backlog.md:321`, ticked) is the host user-crontab job
  `/home/daniele/filesystem-agent/scripts/backup-claude-sessions.sh` (`0 4 * * *`). Per
  `/mnt/raid0/llm/tmp/host-actions-20261023/RESULTS.md` and
  `/mnt/raid0/llm/claude-backups/backup.log`, it backs up:
  - AI session transcripts (claude and codex; host, twyne, epyc) into the immutable
    `/mnt/raid0/llm/cloud-llm-vault`;
  - daily `ai-sessions-*.tar.gz` (3 kept locally);
  - opencode DB snapshots;
  - a mirror to `/mnt/micron/backups` (claude=60, opencode=30).
- It does **not** cover `/mnt/raid0/llm/tmp`, research `data/`, or `/mnt/raid0/llm/state/vidya`.
  **It cannot restore any lost path.**

**What the backed-up transcripts can recover:**
- A read-only scan of `~/.claude/projects`, `~/.codex/sessions` and the vault found transcript hits
  for **257 of the 263 real path names**, with `Write` / `Edit` / `apply_patch` / heredoc
  authorship records (`work/transcript_authorship.json`).
- Agent-authored text (reports, plans, scripts, patches, row text) is reconstructible.
- Measurement outputs are not, except where they were printed into a tool result.
- The vault is the only source for the June and July (E0) sessions.

**Committed copies:**
- 26 A, 20 C and 1 D paths have a committed copy. Most are July runs that were carried into
  `epyc-inference-research/data/<run>_<ts>/`, plus `artifacts/gpu-block-27b-20261004/`,
  `artifacts/cpu-window2-20261004/`, `artifacts/autokernel/glm53-evidence-20260922/`,
  `artifacts/backlog-schedule-20261004/` and `artifacts/research/df2-19-20261020/`.
- The `samename` hits under `/mnt/raid0/llm/worktrees/*` are clones of those same committed
  artifacts, not independent copies.

**Belief ledger:**
- Only `inf70-ingest-ds41scope` among the lost handoff-cited paths.
- 48 `claim_proposed` frames carry the measured values in `display_text`, alongside
  `source_observed` locators and `evidence_supports_claim` grades. The values survive; the raw
  files do not.
- The other ledger-cited tmp paths (95 missing per the guards scan) are outside this handoff set
  and are worth a follow-up for the loop-inputs audit.

## 5. Decision package for the operator

**D1. Class A: what happens to ticked boxes whose evidence is gone (102 paths, 157 citing lines).**
The ratified rule already exists. MEASUREMENT.md §5 "Evidence must be DURABLE, not merely hashed"
(origin/main :190-205) says scratch paths "MUST NOT appear as the evidence citation of a ratified
claim". Its enforcer `epyc-inference-research/scripts/validate/check_evidence_durability.py`
defines the remedies:
- `ARTIFACT LOST` on the citing line gives a WAIVED_LOST warning;
- `REPOINTED from` for a re-point;
- for a lost measurement RESULT: "re-measure it or demote the number to a prior".

The SESSION_LIFECYCLE axiom means a box records that the work happened. The §6/§7 rule is "never
edit historical records, append".

| Option | What | Tradeoff |
|---|---|---|
| **(b) Recommended** | Keep the ticks. Append `ARTIFACT LOST (<path>, <event>) — recorded 2026-10-25` on each citing line (75 evidence-lost). Re-point 26 to committed copies with `REPOINTED from`. Cite the ledger frames for 1. Open a **re-measure or demote-to-prior** item only where the box's number still gates a live decision (owners nominate; most are July v7-era numbers already superseded by later eras). | Policy-faithful and append-only, with no compute up front. A ticked claim whose number still matters becomes visibly unverifiable until re-measured. |
| (a) | Untick all 102. | Contradicts the axiom: the work happened. Mass-churns the dashboard and invents open work for superseded claims. Not recommended. |
| (c) | Re-verify all 102 by re-running. | Very high compute (dozens of CPU and GPU windows) for mostly superseded July numbers. Not recommended. |

**D2. MEASUREMENT.md §5 "Evidence retention and reclamation": a dangling constitutional
reference.**
- MEASUREMENT.md ~:275 points at a §5 section that does not exist. The only text is the unratified
  `artifacts/operator/autokernel-policy-draft/evidence-retention.draft.md` (2026-08-03, item 5 of
  the AK policy package; ledger `RATIFICATION_LEDGER.md:401` pending).
- **What the draft would have prevented:**
  - **As written, not 10-20.** Its reclamation grant covers only artifacts *created by an autonomous
    loop inside operator-set namespace roots*, and it leaves operator-approved session reclaims as
    "operator-only" with no procedure.
  - **If its predicate applied to every reclaimer, it would have refused nearly all of E2:**
    - conjunct 3, *derivation closure*: no entry named the records it could be re-derived from;
    - conjunct 4, *no live binding*: open decision packages and open boxes cited them;
    - conjunct 5, a *retention hold in operator boundaries, not days*: this forbids the same-minute
      purge;
    - conjunct 7, *explicit target, no sweeps*;
    - conjunct 8, plus §3.5, a *fresh-hash tombstone before unlink*.
  - **Its three-state verifier** (conforming / expected absence / defect) would classify the 194
    unlogged losses as defects.
- **What it lacks:**
  - an enumerated list of citation sources (handoffs, FILLERS, ledger);
  - a ban on size thresholds;
  - fail-closed reads;
  - a re-check at purge time;
  - a named enforcer.
- The constitution is human-amendment-only, so this is the operator's choice:

| Option | Tradeoff |
|---|---|
| **Ratify the draft amended (recommended)**: widen §3.4's predicate to every reclaimer (session, cleanup and sweep, not only the loop), name the citation-oracle sources, forbid size thresholds, and require a re-check at purge time. | Closes the actual 10-20 failure mode. Needs a redline by the draft owner before signing. |
| Ratify as written. | Fixes the dangling reference fast and protects AK loop artifacts, but would not have prevented E0 or E2. |
| Strike the dangling sentence and rely on code guards only. | Fastest, but leaves reclamation unconstitutional and the guards without a ratified contract. |

**D3. Class C (131 rows): leave or annotate.**
- **Recommended: leave.** They gate nothing.
- Optionally, append `ARTIFACT LOST` only where a C line cites the path as evidence. Never on the
  13 declared Scratch roots or the 10 fragments.

**D4. Guard doctrine and hook registration.**
- The guard code (NIB2-105..109) is agent-implementable.
- Two pieces need the operator:
  - the "Destructive operations" text in `agents/shared/*.md`, which is human-only;
  - registering the new PreToolUse hook in `.claude/settings.json`.
- Recommended: one ratify bundle covering both, once NIB2-105/106 land with tests.

**D5. Backup coverage for durable evidence.**
- Research `data/` (235 campaign dirs) and `state/vidya` (the canonical ledger, 43 MB) have **no
  backup** except git pushes. The ledger is not in git.
- Option (a): add `/mnt/raid0/llm/state/vidya` to the host job's vault or Micron step (host action).
- Option (b): accept git as the only copy for `data/` and leave `state/` unbacked.
- **Recommended: (a) for `state/vidya`.** `data/` is already pushed to origin.

**D6. HARD Class-B rows: re-scope or regenerate.**
- **Recommended: re-scope** VB-CPU-XFER-1 and VB-KQROUTE-1 to project the next or most recent run
  (v11-052 for kqroute) instead of re-running 2026-10-03/04.
- Regenerate only P5.2's IRT artifacts (~1 h CPU quarter) and, if R22-4 is still live, the r2110
  builds.
- The box owner decides TD-29.M4's baseline.

## 6. Reconciliation plan (concrete, minimal)

**Class B: top priority.** Full task texts are in `HANDOFF-DIFFS-PROPOSED.md` §1.
- **NIB2-104:** one umbrella task to reconstruct the 17 SOFT inputs from transcripts into their
  durable homes (no compute), with one `- [ ]` per owning box.
- **3 re-points.**
- **HARD rows:**
  - **VB-CPU-XFER-1R** and **VB-KQROUTE-1R**: re-scope;
  - **TD-29.M4.0**: baseline;
  - **R22-4.0**: rebuild if live;
  - **P5.2.0**: regenerate.

**Class A:** `ARTIFACT LOST` or `REPOINTED from` per line (generated list in
`HANDOFF-DIFFS-PROPOSED.md` §4), under D1(b).

**Class C:** leave (D3). **Class D:** six owner adjudications (`HANDOFF-DIFFS-PROPOSED.md` §2).

**Guards to stop recurrence** (design with file:line in `work/guards-design.md`; tasks NIB2-105..109
in `HANDOFF-DIFFS-PROPOSED.md` §5):
1. **New `scripts/system/citation_oracle.py`** (NIB2-105).
   - `root/scripts/vidya/adapters/evidence_durability.py` does **not** fit: it is a belief adapter
     that converts receipts into claims and has no lookup.
   - The research checker answers the inverse question (does every citation resolve?), so it is
     reused by import for its grammar only.
   - The oracle has no size parameter, fails closed, and reads root handoffs active and blocked
     (origin/main and the working tree), FILLERS, grants and launchers, the canonical ledger, the
     research registry, AK campaign inputs, the manifest, bus, observer registry and crontab.
   - `scripts/hooks/tests/test_evidence_durability_precommit.sh` is the template for the new shell
     tests.
2. **`scripts/safety/guarded_rm.sh`** (NIB2-106): refuse cited paths unless
   `--cited-ok <approval-ref>`, and write a provenance sidecar.
3. **`scripts/safety/trash-sweep.sh`** (NIB2-106): minimum 7-day residency with an exact-path
   approval mode only, and an oracle re-check on the original path at purge time.
4. **`scripts/system/scratch_cleanup.py`, `scripts/system/worktree_gate.py`,
   `scripts/system/autokernel_disk_sweep.py`** (NIB2-107): add a KEEP-CITED verdict and remove the
   fail-open paths. For `autokernel_disk_sweep.py`, `rmtree` becomes `guarded_rm.sh`.
5. **New `scripts/system/reclaim_scratch.py`** plus hook `scripts/hooks/check_destructive_scratch.sh`
   (NIB2-108): the only sanctioned ad-hoc reclaim path. The hook catches `purge_batch.py`-style
   inline purges.
6. **`scripts/system/host_hygiene_tick.py` + `backup_coverage.py`** (NIB2-109): alarm on
   vanished cited evidence and unsanctioned purges.
7. **Belief-kernel wiring:** a `reclaim_guard` source row and VB-RECLAIM-GUARD-1.

**Durable evidence home:** no new root.
- Per MEASUREMENT.md §5, evidence for ratified or production-affecting claims goes to
  `epyc-inference-research/data/<campaign>/` with SHA256SUMS and a README.
- Design and decision docs go to root `docs/design/` or the owning handoff.
- Reproducible data stays scratch and is never carried.
- See §7 for what survives in tmp today and where it belongs.

**D7. A conflict inside the durability rule: in-repo versus durable-untracked.**
- MEASUREMENT.md §5 says evidence must live "inside a repository, under
  epyc-inference-research/data/<campaign>/".
- The enforcer's docstring (`check_evidence_durability.py:1-60`) cites a 2026-08-03 operator
  ruling: raw campaign data stays on local disk, gitignored, and "durable, untracked" is valid. It
  checks only that a citation resolves outside scratch.
- The 2026-08-03 retention draft formalises this as the class `durable-untracked` with a
  git-carried `SHA256SUMS`.
- The options:
  - align §5's text to the 08-03 ruling (recommended; it rides with D2);
  - require git-commit for every ratified-claim file. The carry is small (59 MiB), but this
    reverses the 08-03 ruling.
- Either way, untracked `data/` has no off-host copy, which is D5.

## 7. Surviving durable artifacts in tmp (DURABLE-IN-TMP.tsv; notes in work/durable-notes.md)

**Inventory (read-only):** 1,203 rows, classified against MEASUREMENT.md §5:

| home | rows | size | rule |
|---|---:|---:|---|
| `research-data-commit`: `epyc-inference-research/data/<campaign>/` + SHA256SUMS + README | 183 | 16.2 MiB | small evidence behind a ratified or production-affecting claim |
| `root-docs-commit`: root `docs/design/`, `docs/reviews/`, `docs/coordination/`, or the owning handoff | 547 | 43.1 MiB | decision, design and review docs, handovers, calendar snapshots, intake outputs |
| `stays-scratch-until-ratified` | 151 | 20.6 MiB | evidence for WIP or provisional results; carry at ratification |
| `reproducible-never-carry` | 300 | 39.2 GiB | worktrees, builds, raw logs and downloads; provenance only |
| `transient-runtime` | 22 | 30.7 MiB | live queue state (FILLERS.md, grants, OPEN-WINDOWS/DEADLINES/OWNER-REPLY json); 29 MiB of it is 156 `FILLERS.md.bak-*` |

**What would actually be carried:** 704 rows, **59.1 MiB**. The research-data and root-docs homes
total 62.2 MiB, minus 26 rows already byte-identical in a repo.

**Caveat:** `claim_status` is a keyword heuristic that over-includes. The owner confirms each row
before carrying it.

**The enforcer run** (`check_evidence_durability.py --json --scan-docs --handoff-root /workspace`,
read-only):
- Registry: 454 citations, 0 errors, 5 WAIVED_LOST (old build trees).
- Prose: 1,692 EPHEMERAL tmp citations covering 1,231 distinct paths, of which 668 still exist.

**Exposure now:**
- No tmp-root file has a sibling `.epyc-keep`. That includes `compute-calendar-20261021.md`,
  `ws58-control-plan-20261024.md` and the three `handover-*-to-ws58-20261024.md` files.
- About 400 carry-class rows sit in dirs with no KEEP marker (about 40 MiB).
- **The 252 KEEP files written by workspace-58 on 10-25 say "durable snapshot under
  /mnt/raid0/llm/state/evidence/".** That path does not exist and contradicts §5. Re-word them to
  point at the §5 homes when the carry lands.
- The canonical belief ledger cites 187 tmp paths, of which 20 are gone, and has no backup.

**Top items:**
- FILLERS.md and the calendar: snapshot them to `docs/coordination/` at each wrap-up. They stay
  live in tmp.
- `belief-redesign-20261021/DESIGN.md` and `belief-kernel-review-20261021/REPORT.md`.
- The ch28, c3, c4 and c5 fold PLAN/RECORD files plus their gate evidence.
- The `batch-20261024` small subset.
- `inf70/agents`.
- The f8-launchers run dirs (VERDICT, RUN_RECORD, PREDECLARATION+sha, PASSED).
- `gpu-cpu-noise-20261021`.
- The remainders of the stack-change packages.
- `sub-gpu-runner-20260916`, which is ledger-cited and has no KEEP.
- `v11-runs`.
- **The tmp-only filler engine and job library** (`fillers-3c4ca599/filler_run9.sh`,
  `f8-fillers-20261022/{common.sh,mklaunch.sh}`). Only `filler_run2.sh` is committed.
- The handovers and the control plan.
- `codex-ni-20261024-scheduling/{RULES-FROM-WS58.md,ROWS-FOR-OWNER.md}`.
- `inference-backlog-audit-20261021/REPORT.md`.
- The `intake-reverify` subset.
- `tensorfold-114-review-20261024`.

**Forward convention: small evidence is staged straight into the §5 home and scratch stays in tmp.**
The changes go in this order:

1. **Commit the engine and job library to `epyc-root:scripts/fillers/`.** Then:
   - `common.sh`: `jb_begin` (:25-26), the `jb_write_ended` EXIT trap (:44-45) and `jb_note`
     (:73). 46 job.sh files source it, so it is the single choke point. Add
     `EVID=${FILLER_EVIDENCE_DIR}` and stage VERDICT, RUN_RECORD, PREDECLARATION+sha, AMENDMENT-*,
     run_valid, steps.txt, the ENDED/PASSED rc line and SHA256SUMS there in the EXIT trap.
   - `filler_run9.sh` (:65-69, :76, :111-113, :143-144): export `FILLER_EVIDENCE_DIR`.
   - `mklaunch.sh`: :22 still points at run2; emit `FILLER_EVIDENCE_DIR`.
   - Add a `predeclare` helper, because PREDECLARATION.sha256 is hand-made today.
2. **Committed root scripts:**
   - `scripts/fillers/filler_run2.sh`, to be retired in favour of run9;
   - `scripts/fillers/v11/{v11_driver.py:39,akx27_driver.py:32}`, which use `RUNS=/mnt/raid0/llm/tmp/v11-runs`;
   - `scripts/fillers/arm_v11_pollers.sh` and `scripts/fillers/akx27_run.sh`;
   - the readers `scripts/coordination/prior_check.py:119`, `scripts/vidya/ingest_sources.py:107,372`
     and `scripts/vidya/adapters/gpu_cpu_noise.py:248-299`, which must search `data/` as well as tmp.
3. **Research gpu-cpu-noise scripts** (they default their run dir to tmp; add `--evidence-dir`):
   - `scripts/benchmark/gpu_cpu_noise/gpu_cpu_noise_driver.py:1359` (and :1168, :1422);
   - `run_gpu_cpu_noise.sh:31`;
   - `analyze_gpu_cpu_noise.py:494`.
4. **About 22 per-run `job.sh` writers** under `f8-launchers-2026102{2,3,4}/` (lines listed in the
   notes) and the roughly 150 hand-cloned `compute-flags/grant-*.sh`, which become one committed
   template.
5. **Docs:**
   - `docs/guides/agent-workflows/compute-fillers.md:5-6,50-57`: it is stale on run8/run9; add the
     evidence rule;
   - `.claude/skills/inference-backlog-scheduling/{SKILL.md:15-16,48,62,68, references/grant-writer-pattern.md:17,109}`.
6. **Wrap-up:** run the research checker's `--handoff-root /workspace --scan-docs` advisory as a step,
   so a new EPHEMERAL citation on a ticked line is caught when it is written.
