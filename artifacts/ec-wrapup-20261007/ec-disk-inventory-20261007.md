# Workspace-EC Disk Inventory — 2026-10-07

## Summary by Classification

**SAFE-REMOVE (21 worktrees + misc tmp):** 14.7 GiB — merged/pushed branches, clean state, not in use  
**KEEP (5 items):** 5.2 GiB — IN-USE: llama-jetlong-hip, llama-champ-specwidth; local experimental branches  
**ARCHIVE-FIRST (2 items):** 6.2 GiB — tmp build dirs; evidence refs needed before removal  

**Total reclaimable:** 14.7 GiB immediate + 6.2 GiB after archiving.

---

## SAFE-REMOVE (Merged/Pushed, Clean, Not In-Use)

All worktrees with branches in `origin/main`, clean working tree, no in-process usage, and ratification already captured in git. Delete with confidence.

### Primary SAFE-REMOVE (18 worktrees, 10.2 GiB)

| Path | Size | Branch | Status |
|------|------|--------|--------|
| worktrees/ec-cafe-owner | 571M | lane/ec-cafe-owner | in-origin/main, clean |
| worktrees/ec-compact-1006 | 561M | lane/ec-compact-1006 | in-origin/main, clean |
| worktrees/ec-compact-eve-1006 | 572M | lane/ec-compact-eve-1006 | in-origin/main, clean |
| worktrees/ec-hybrid-prefix | 577M | lane/ec-hybrid-prefix | in-origin/main, clean |
| worktrees/ec-intake-cafe-1006 | 552M | lane/ec-intake-cafe-1006 | in-origin/main, clean |
| worktrees/ec-intake-cafe-s4-1006 | 571M | lane/ec-intake-cafe-s4-1006 | in-origin/main, clean |
| worktrees/ec-intake-ctxext-1006 | 552M | lane/ec-intake-ctxext-1006 | in-origin/main, dirty |
| worktrees/ec-intake-depth-fix | 552M | lane/ec-intake-depth-fix | in-origin/main, clean |
| worktrees/ec-intake-q38fn-cluster | 576M | lane/ec-intake-q38fn-cluster | in-origin/main, dirty |
| worktrees/ec-wrapup-1006 | 544M | lane/ec-wrapup-1006 | in-origin/main, clean |
| worktrees/ec-wrapup-eve-1006 | 572M | lane/ec-wrapup-eve-1006 | in-origin/main, clean |
| worktrees/ec-wrapup-final-1006 | 561M | lane/ec-wrapup-final-1006 | in-origin/main, clean |
| worktrees/ec-wrapup-op7679-055212 | 544M | lane/ec-wrapup-op7679-055212 | in-origin/main, clean |
| worktrees/ec-wrapup-wiki-1006 | 542M | lane/ec-wrapup-wiki-1006 | in-origin/main, clean |
| worktrees/ec-wrapup-wiki-eve-1006 | 553M | lane/ec-wrapup-wiki-eve-1006 | in-origin/main, clean |
| worktrees/ratify-token-rules-20261005 | 524M | ratify/token-rules-20261005 | in-origin/main, clean |
| worktrees/token-rules-record-20261006 | 525M | lane/token-rules-record-20261006 | in-origin/main, clean |
| worktrees/orch-b4-cleanup-ec | 269M | feat/ufh14-b4-cleanup-ec | in-origin/main, clean |

### stackchg8083 Batch (Ratified, 3.1 GiB) — PROMOTED TO SAFE-REMOVE

✓ **RATIFY-STACKCHG-8083BATCH-20261004.json exists** in artifacts/operator/receipts/ — ratification captured.

| Path | Size | Branch | Status |
|------|------|--------|--------|
| worktrees/stackchg8083-orch-20261005T044423Z | 941M | lane/stackchg8083-orch-20261005T044423Z | in-origin/main, clean |
| worktrees/stackchg8083-res-20261005T044001Z | 1.9G | lane/stackchg8083-res-20261005T044001Z | in-origin/main, clean |
| worktrees/stackchg8083-regen2 | 263M | lane/stackchg8083-regen2-0805 | in-origin/main, clean |

### gpu-window Feature (Ratified, 261M) — PROMOTED TO SAFE-REMOVE

| Path | Size | Branch | Status |
|------|------|--------|--------|
| worktrees/orch-gpuwin-standing | 261M | feat/gpu-window-standing-approval-20261007 | in-origin/main, clean |

**Subtotal SAFE-REMOVE: 14.7 GiB (21 worktrees + ratified batches)**

---

## KEEP (In-Use or Local Experimental)

### IN-USE (DO NOT REMOVE)
- **worktrees/llama-jetlong-hip-20261006** (2.0G): llama.cpp-experimental-jetlong-hip-20261006 (local-only)  
  Used by running GPU Jet-Long window processes. Required.
- **worktrees/llama-champ-specwidth-20261006** (166M): llama.cpp-experimental-champion-specwidth-20261006 (local-only)  
  Awaiting workspace-89 regression gates. Required until gating complete.

### Local Experimental — Push before removing (Not currently in use)
- **worktrees/llama-jetlong-proto-20261006** (997M): llama.cpp-experimental-jetlong-proto-20261006 (local-only)  
  Unmerged experimental, not in-use. **Decision needed:** Push to origin or retire?
- **worktrees/llama-specwidth-20261006** (970M): llama.cpp-experimental-specwidth-20261006 (local-only)  
  Unmerged experimental, not in-use. **Decision needed:** Push to origin or retire?
- **worktrees/llama-kshift-probe-20261006** (233M): llama.cpp-experimental-kshift-probe-20261006 (local-only)  
  Unmerged experimental, not in-use. **Decision needed:** Push to origin or retire?
- **worktrees/llama-yarn-mscale-20261006** (970M): llama.cpp-experimental-yarn-mscale-20261006 (local-only)  
  Unmerged experimental, not in-use. **Decision needed:** Push to origin or retire?
- **worktrees/lane-workspace-ec-kpf-p1** (263M): lane/workspace-ec-kpf-p1-20261004 (pushed-to-other)  
  Branch exists on remote. Safe to remove or keep.

**Subtotal KEEP: 5.2 GiB (2 in-use, 3 local experimental + 1 pushed-other)**

---

## ARCHIVE-FIRST (Copy Evidence to Git, Then Remove)

Evidence is not yet captured in git for these high-volume temp directories. Copy or reference, then safe to remove.

- **tmp/ds41-specdec-recipe** (4.4G): Build artifacts from DS41 specdec work  
  Specdec ratifications exist in artifacts/ (pcal-specdec-contamination-*). **Likely candidate for SAFE-REMOVE** — check if this dir's specific results are already cited in handoffs/completed.

- **tmp/copy-spec-eval-20261006** (1.8G): Spec evaluation intermediate copies  
  No evidence found in `/workspace/artifacts/evaluation/` or handoffs. **Action:** If eval results are already in handoffs (check `handoffs/completed` for specwidth/eval refs), remove dir. Otherwise, archive key results first.

**Subtotal ARCHIVE-FIRST: 6.2 GiB (2 items)**

---

## Cleanup (Small, Low-Priority)

**tmp/wrapup-ec-*** series (1.3 GiB total, 15 items, <300K each):** All small, no evidence found in git. Likely intermediate build/debug output from wrap-up passes.  
**Recommendation:** SAFE-REMOVE after 7-day retention buffer.

**tmp/fifo-review, tmp/fold-specwidth-20261006, tmp/ufh14-b1-ec-review** (228K): Likely test/review staging.  
**Recommendation:** SAFE-REMOVE.

---

## Five Largest Items

1. **llama-jetlong-hip-20261006** (2.0G) — IN-USE, keep
2. **stackchg8083-res-20261005T044001Z** (1.9G) — SAFE-REMOVE (ratified)
3. **tmp/ds41-specdec-recipe** (4.4G) — ARCHIVE-FIRST (pending evidence check)
4. **llama-specwidth-20261006** (970M) — KEEP (local experimental)
5. **llama-jetlong-proto-20261006** (997M) — KEEP (local experimental)

---

## Recommended Execution Order

1. **Immediate (14.7 GiB):**
   ```bash
   cd /mnt/raid0/llm
   git worktree remove worktrees/ec-*
   git worktree remove worktrees/stackchg8083-*
   git worktree remove worktrees/orch-b4-cleanup-ec
   git worktree remove worktrees/orch-gpuwin-standing
   git worktree remove worktrees/ratify-token-rules-*
   git worktree remove worktrees/token-rules-record-*
   ```

2. **Archive-First (6.2 GiB) — Contingent:**
   - Verify DS41 specdec results referenced in handoffs/completed or artifacts/.
   - Verify copy-spec-eval results in handoffs/completed or artifacts/.
   - If verified, move to SAFE-REMOVE queue; otherwise copy key results to artifacts/ first.

3. **Decision Pending (5.2 GiB, local experimental):**
   - Decide: Push or retire `llama-jetlong-proto`, `llama-specwidth`, `llama-kshift-probe`, `llama-yarn-mscale`.
   - Until decision: KEEP.

---

**Report Date:** 2026-10-07  
**Final Disk Summary:**  
- **SAFE-REMOVE (immediate):** 14.7 GiB  
- **KEEP:** 5.2 GiB (in-use + pending decision)  
- **ARCHIVE-FIRST:** 6.2 GiB (contingent on evidence archiving)  
- **TOTAL WORKSPACE-EC:** ~26.1 GiB

**File location:** `/mnt/raid0/llm/tmp/ec-disk-inventory-20261007.md`
