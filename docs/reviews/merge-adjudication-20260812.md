# Merge adjudication — `merge/reconcile-0205` (OURS `921113ed` × THEIRS `705b8f85`, base `3dd1ec1b`)

## VERDICT

**SAFE TO COMMIT — 0 genuine content drops.** Two cosmetic wording regressions (listed below), no lost code, tests, tasks, sections, or operator artifacts.

---

## Method (and why the previous two attempts were wrong)

Line-set comparison is the wrong primitive. The metric that actually answers "was anything dropped" is:

> for each file, the set of lines a parent **added relative to the merge base** (`git diff -U0 3dd1ec1b <parent>`, `+` lines) that are **absent from the merged working tree**.

A line that exists only in a parent's *unmodified* copy is not evidence of anything — that is the entire source of the 1,210-line noise floor. I also ran the mirror check (lines a parent *deleted* that reappear in the merge) and a whole-file check.

Four independent gates, all run against the worktree:

| Gate | Result |
|---|---|
| Parent-added lines absent from merge | 61 across 12 files → all adjudicated below |
| New files added by either parent, absent from merge | **0** (15 new from theirs, 63 from ours, all present) |
| Conflict markers left in tree | **0** |
| `pytest tests/test_session_bus.py test_tmux_adapter test_dashboard_panels test_handoff_parser test_backlog_row_check test_backlog_queue_gen tests/vidya` | **1068 passed, 1 skipped, 12 subtests** |
| `scripts/handoffs/index_state.py --check` | **0 problems** (coverage + schema + freshness) |

**A bug I caught in my own tooling before trusting it:** my first scan mis-ordered a tuple unpack and compared the working tree against *base* instead of against the merge, reporting 16,450 "lost" lines including 1,230 from `tests/test_session_bus.py` — a file byte-identical to OURS. Corrected numbers reproduce the 1,210/98 signal, which is how I know the method is calibrated.

The single most useful discriminator: `git diff --numstat` from base to each parent, plus merged-vs-each-parent. It classifies every flagged file into `merged==OURS`, `merged==THEIRS`, or `MANUAL`, crossed with whether one or both parents touched it. Only the `merged==X` + **BOTH-touched** and `MANUAL` cells can possibly hide loss. That is 20 files, not 98.

---

## GENUINE LOSSES

**None.**

Two cosmetic prose regressions, recorded for completeness — no fact, task, link target, or claim is lost in either:

1. `handoffs/active/cpu-shape-specialized-gemv-decode.md` (lines 55, 92) — OURS wrote the cross-reference as `[inference-research-index.md](...)` ⚑ START HERE block + Prioritized Task List item CPU18` / `⚑⚑⚑⚑⚑ Lowest-Hanging Fruit block + CPU26 entry in Pickup Sequence`. The resolution kept THEIRS' generic `(the merged CPU/GPU inference index)`. Same link target, less specific anchor text. Confidence: high.
2. `handoffs/active/batched-decode-measurement.md:93` — `**Related**` parenthetical: merged keeps OURS' `(CPU14/CPU17/CPU18 rows)` over THEIRS' `(merged CPU/GPU inference routing)`. Both correct. Confidence: high.

Neither is worth blocking on; neither needs a fix before commit.

---

## CONFIRMED BENIGN

### A. Theirs never touched the file — 41 files, ~430 flagged lines
`merged == OURS`, `git diff 3dd1ec1b 705b8f85 -- <path>` is **empty**. Zero possibility of loss; the flagged lines are base content OURS deliberately rewrote.

This covers **every priority-1 session-bus file** and the priority-3 trust-boundary files:

- `scripts/coordination/session_bus_coordinator.py` (49), `session_bus.py` (35), `tmux_adapter.py` (8), `backlog_row_check.py` (5), `backlog_queue_gen.py` (3), `bus_supervisor.sh` (5)
- `scripts/vidya/ledger.py` (2)
- `tests/test_session_bus.py` (4), `tests/test_tmux_adapter.py` (4), `tests/test_handoff_parser.py` (1)
- `measurement/protocols/gpu-cross-device.md` (3) — **Annex G intact**, merged byte-identical to OURS, ratification header on line 1 present. THEIRS made no change to this file, so the operator-signed amendment was never at risk.
- `coordination/session-bus/tokens/token-queue.md` (196 flagged) — merged == OURS, THEIRS untouched.
- `coordination/session-bus/BUS_PROTOCOL.md`, `wiki/INDEX.md`, `wiki/agent-architecture.md`, and 27 handoff/index files with 1–14 flagged lines each.

**C34–C43, R1, R2 explicitly verified.** Marker set extracted from the merged `session_bus.py`, `session_bus_coordinator.py`, `tmux_adapter.py`, `backlog_row_check.py`, `bus_supervisor.sh`, `tests/test_session_bus.py`:
`C12 C13 C14 C17 C18 C19 C20 C21 C23 C24 C25 C26 C27 C28 C29 C30 C31 C32 C33 C34 C35 C36 C37 C38 C39 C40 C41 C42 C43 R1( R2(` — **identical set to OURS, nothing missing.** Confidence: certain (files are byte-identical).

`artifacts/operator/`: OURS changed 23 files, THEIRS changed 0, merged differs from OURS in **0** files. Nothing at that boundary moved.

### B. Ours never touched the file — 26 files
`merged == THEIRS`, `git diff 3dd1ec1b 921113ed -- <path>` empty. Includes `dashboard/panels.py` (7), `scripts/vidya/measurement_record.py` (3), `handoffs/active/rocm-verify-profile-backend.md` (81), `autokernel-research-loop.md` (63), `agentic-rocm-kernel-authoring.md` (28), `docs/design/p2-5j-...md` (17), and 20 others at 1–9 lines.

- **`.research-session.json` (261) — confirmed benign as you believed.** It *is* tracked (not gitignored), but OURS made no change to it; THEIRS replaced it (+44/−317) with a new research-intake session record (`b3cb6221…`, `stage1-complete-awaiting-dive-selection`). Merged takes THEIRS. Nothing of ours to lose. Confidence: certain.

### C. Both sides touched it, merge is a verified superset — 5 files
Line-set flagged them; semantic inspection shows the merge contains everything both parents contributed.

- **`dashboard/server.py` (19 flagged / 5 added-lost)** — all 22 removals under `--word-diff` are *sub-line* fragments of reflowed docstrings (`transport`, `commits,`, `importing the research package.`). Symbols verified present in merged with the same counts as both parents: `_production_kernel_summary` ×2, `production_repo` ×9, `probe_note` ×1. THEIRS additionally adds `/api/kernel/health`, `kernel_data_health()`, `_autokernel_probe_receipts()`, `AUTOKERNEL_CONTROL_ROOT`. The 5 "lost" signature lines are the same signatures with a `control_root` parameter appended. Strict superset. Confidence: high.
- **`tests/test_dashboard_panels.py` (5)** — **zero test functions lost**: `comm -23` on the sorted `def` name sets is empty; merged has 109 defs vs OURS' 92. The flagged `# 7. Routing tables stay the enumeration source` was *renumbered to `# 8.`* because THEIRS inserted a new `# 7. A supervised restart must import the checkout the supervisor names`. `_fake_hub` gained a `health_routes` kwarg and kept `drop=()`. The 2 "lost" lines are call sites that gained a `root / "controls"` argument. Confidence: high.
- **`scripts/dashboard/hub_supervisor.sh` (5)** — THEIRS contains all 74 of OURS' added lines and adds two improvements on top (`cd "${EPYC_ROOT}"` subshell, `9>&-` fd close, `setsid -f` in the adoption note). Merge takes THEIRS. Strict improvement. Confidence: high.
- **`dashboard/static/kernel.html` (2)** — OURS' `else h+='<div class="muted">freeze attestation unavailable: …'` fallback is preserved, reworded at line 257 as `h+='<div class="detail">'+esc(prod.error||"attestation not found")+'</div>'` inside the same `state-card production` block. Fallback behaviour intact. Confidence: high.
- **`handoffs/active/non-inference-backlog.md` (1)** — both sides renamed `hermes-agent-index.md` → `user-facing-harness-index.md`; merge kept THEIRS' description. Confidence: certain.

### D. Deliberate rewrites — 2 files
- **`coordination/session-bus/tasks/post-reboot-session.md` (264) — confirmed, as you believed.** THEIRS made **no change to this file at all** (base→theirs diff is empty), so nothing of theirs could be dropped; the 264 are the superseded 2026-07-29 brief your rewrite replaced. Merged == OURS' rewrite, 282 lines, 11 sections (`§0` clock check … `§10` bus drain). Load-bearing content of the old brief was its work queue (E5 W1–W4, E8 baseline, P1-3, P2-5f, wiki compilation) — each of those items lives in its own handoff (`batched-decode-measurement.md`, `gpu-serving-tie-in-program.md`), all present and all rowed in an index (`index_state.py --check` = 0 problems). Nothing was load-bearing only here. Confidence: high.
- **`handoffs/completed/cpu-kernel-env-flags-inventory.md` (28)** — the one file where both sides independently added the *same* new column ("Effect on trace interpretation") to the 44-row flag table. The resolver merged them by hand, kept origin's entries, folded in the **Comparability** notes, added the COMPLETED-REFERENCE banner, fixed the `../active/` relative links, and documented the double-add in the file itself. 44 GGML rows in merged == 44 in base == 44 in both parents. Content enriched, not lost. Confidence: high.

### E. Regenerated / derived artifacts — 4 files
- `handoffs/active/.index-state.json` (60) and `.index-graph.json` (49): merged carries OURS' generated sidecars. I regenerated state in memory (`index_state.py --json`) and compared: **the on-disk sidecar is byte-equal to the freshly computed state for the merged tree** (169 handoffs both sides). No regeneration needed.
- `handoffs/active/master-handoff-index.md` (5 added-lost): the generated rollup block. `--check` reports the block as fresh, not stale. Regenerating post-commit is harmless but not required.
- `wiki/.last_compile` (1): a timestamp.
- 24 deleted `coordination/session-bus/heartbeats/*.json` + 2 `outbox/*.jsonl`: deleted by OURS in `060efa27` ("archive the non-roster residue"), THEIRS deleted none; the merge correctly honours the deletion.

### F. Scan artifacts — 3 files
`AGENTS.md` and `.claude/commands/wrap-up.md` are **symlinks** (`AGENTS.md -> CLAUDE.md`); `git show` yields the link target while the filesystem read yields the target's content, which is what produced the 1-line flags. `wiki/.last_compile`, `.research-session.json`, and the two `.index-*.json` files also generate set-membership noise from repeated structural lines (`},`, `"open": …`). No content implication.

### G. Renames — 5 files
`cpu-kernel-env-flags-inventory.md`, `k28-fused-chunked-gdn-kernel-research.md`, `mi210-mfma-compute-bound-paths.md`, `mi210-kernel-rnd-loop-proposal.md`, `mi210-speed-campaign-summary.md` moved `handoffs/active/` → `handoffs/completed/` by THEIRS. Four are byte-identical to THEIRS' completed version and OURS made **no** edit to them; the fifth is the hand-merge in §D. The corresponding `INF-27`/`INF-38`/etc. rows disappearing from `inference-research-index.md` is the **required** behaviour under the thin-row contract (row deleted on completion), not loss.

---

## UNRESOLVED

Nothing. Every one of the 98 flagged files falls into a category above, and the four independent gates agree.

Two items are worth *knowing* rather than *blocking on*:

- `handoffs/active/numa-placement-defect-20260730.md` — THEIRS fixed two links from `cpu-inference-optimization-index.md` to `inference-research-index.md`; the merge kept OURS' version with the old target. That target does not exist in **either parent** (the rename predates the base commit; ~20 completed/archived docs still reference it), so this is pre-existing repo debt the merge neither created nor worsened. Not a merge drop.
- The pass I ran is line-granular plus symbol-granular on the code files. It would not detect a *semantic* conflict where both sides' text merged cleanly but the combined behaviour is wrong. The 1068-test run and the clean `index_state.py --check` are the mitigations, and both are green.
