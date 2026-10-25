# HANDOFF-DIFFS-PROPOSED — tmp-loss reconciliation (prepared 2026-10-25, NOT applied)

Prepared by a read-only subagent for **workspace-58 to apply** (ruling (b) 2026-08-16: a subagent
prepares, the owning session applies). Line numbers are against root `origin/main` at
`97268ec0f`. **The task text is the identity; `file:LINE` is only a hint.** Re-resolve before
applying. Each annotation goes on the box **owner's** line. Appending an annotation is not ticking
or unticking, but per INVARIANTS 9 the owner (or workspace-58 as calendar/cleanup owner, with a
note) applies it. No box is unticked by anything in this file.

Annotation grammar reuses the ratified MEASUREMENT.md §5 enforcer vocabulary
(`epyc-inference-research/scripts/validate/check_evidence_durability.py`):
`ARTIFACT LOST` on the citing line = recorded loss (WAIVED_LOST, a WARN, not a silent MISSING);
`REPOINTED from <old>` = provenance line for a re-pointed citation; `<file>.WITHHELD.sha256` =
hash-and-provenance-only. The checker's own MISSING hint: *"If it is genuinely gone and was a
measurement RESULT, the claim is unverifiable: re-measure it or demote the number to a prior.
Do not fabricate a replacement path."*

New task IDs: the next free NIB2 id on origin/main is **NIB2-104** (allocate against origin/main
again at apply time).

---

## 1. Class B — new `- [ ]` tasks (top priority; ready to file)

Each line is ready to paste under the named owning handoff, next to the box it unblocks.
Compute is the cost of the **recovery** step only; the unblocked task's own compute is unchanged.

### 1a. Reconstruct-from-transcript (17 SOFT items, no compute)

Shared method for every 1a task (state it once in NIB2-104 and cite it): the text was authored by
an agent and survives as `Write`/`Edit`/heredoc records in the session transcripts
(`~/.claude/projects`, `~/.codex/sessions`, the immutable `/mnt/raid0/llm/cloud-llm-vault`, and the
Micron session-archive mirror, 60 days). Replay the LAST `Write` record and every later `Edit` in
order; diff against any surviving excerpt; write the file to its **durable home** (never back to
tmp); cite the new path with `REPOINTED from <old tmp path>`. The index of which transcript holds
which file is `/mnt/raid0/llm/tmp/ws58-tmp-loss-reconcile-20261025/work/transcript_authorship.json`
(+ `work/scan/*.jsonl` for file and line offsets).

- **non-inference-backlog.md** (umbrella):
  `- [ ] **NIB2-104** (HIGH): **reconstruct the 17 transcript-recoverable Class-B inputs lost in the 2026-10-20 reclaim and the 2026-10-07/10-23 scratch sweep**, one commit per owning repo, each file into its durable home (decision/design docs → root docs/design/ or the owning handoff; scripts → the owning repo's scripts/ or tests/; row text → handed to the owning session to apply). Inventory: /mnt/raid0/llm/tmp/ws58-tmp-loss-reconcile-20261025/LOSS-INVENTORY.tsv (class=B, blocking=SOFT). Method: replay last Write + later Edits from the transcript index (work/transcript_authorship.json). No compute. Ticks when every SOFT row's citing box is re-pointed with `REPOINTED from`.`
- **batched-decode-measurement.md** (near L847 "RE-MEASURE E5 Stage-B"): `- [ ] E5-B-LAUNCHER — reconstruct `a7-fire-all.sh` (heredoc in 4 transcripts; lost in the 2026-08-23 reclaim) into epyc-inference-research/scripts/, re-point this box; no compute.`
- **autokernel-all-devices-all-dimensions.md** (AKX-ALL-1, L162): `- [ ] AKX-ALL-1a — reconstruct PREPARED_ROWS.md (Write record) and hand its adapters/README row + VB-AK-LONGCTX text to the owning session; no compute.`
- **autokernel-orchestrator-actor-backend.md** (OAB-4, L142) and **vidya-belief-substrate-program.md** (VB-AK-SEAT-b2): `- [ ] OAB-4.0 — reconstruct ak-seat-ab/driver.py (Write + Edits) into the orchestrator repo (not tmp) so OAB-4's orch arm and VB-AK-SEAT-b2 build on a committed driver; no compute.`
- **deepseek-v41-flash-evaluation.md** (DS41-C4/C4b, L270/296): `- [ ] DS41-C4.0 — reconstruct patches/0001-ggml-gather-rows-…-profiling-counters.patch and 0002-deepseek41-engram-profile-…patch (Write records) into artifacts/ds41/engram-profile/, re-run `git apply --check` on the DSpark tree when it lands; no compute.`
- **deepseek-v41-flash-evaluation.md** (DS41-C51 / DS41-C113): `- [ ] DS41-C113.0 — reconstruct ds41_watchdog.sh, swap_args.sh, swap_bi6_10o.sh, pause_measure2.sh (Write) and numa_maps_probe.py (heredoc) from ds41-scope-20260926 into epyc-inference-research/scripts/ds41/; re-point C51/C113; no compute.`
- **gpu-serving-tie-in-program.md** (GPUWIN-STANDING-APPROVAL, L338): `- [ ] GPUWIN-0 — reconstruct ratify_gpu_window_standing_approval_20261007.sh (Write) into scripts/operator/, fill __ORCH_FILE_SHA__, present the ONE --apply command to the operator; no compute.`
- **numa-topology-cutover-resume-20260730.md** (W6, L1230): `- [ ] W6.0 — reconstruct the guard-audit prove_failopen.py/prove2-4.py and registry fixtures (heredocs) as committed tests in the orchestrator repo, then fix the seven fail-open guards against them; no compute.`
- **kv-unified-stack-rollout.md** / **vidya-belief-substrate-program.md** (VB-SERVING-DF2 / SSU-F3): `- [ ] SSU-F3.0 — reconstruct kv-sizing-8083-20261003/DECISION.md (Write + Edits) into docs/design/ and re-point the capacity citation (§1.3 DFlash2 VRAM components); no compute.`
- **model-stack-single-source-update-pipeline.md** (SSU-F18, L173): `- [ ] SSU-F18.0 — the box asked for this commit before a reclaim; do it now: reconstruct ssuf5/moved_lineup.py (Write) and patch*.py fixtures (heredoc) and commit them to orchestrator tests; no compute.`
- **agentic-serving-harness-fixes.md** (UFH14-B1c/B1e): `- [ ] UFH14-B1.0 — reconstruct codex-local-provider-template.toml and orch/DESIGN-NOTE.md (Write + Edits) into docs/design/ (B1d's STACKCHANGE-ITEM is already durable); no compute.`
- **agentic-serving-harness-fixes.md** (UFH14-B4b/c/d): `- [ ] UFH14-B4.0 — reconstruct B4bcd-RUNBOOK.md (Write + Edits; trashed 2026-10-07 by scratch_cleanup, swept 2026-10-23) into docs/design/; no compute.`
- **vidya-belief-substrate-program.md** (VB-AK-BELIEF, L1742): `- [ ] VB-AK-BELIEF-0 — reconstruct vidya-planner-receipt-proposal-20260925.md (Write) into docs/design/ so §7's consumer-table row can be applied; no compute.`
- **vidya-belief-substrate-program.md** (VB-FA-MASKSKIP-b/-c, VB-COHGATE-1, VB-SERVING-DF2; also typed-decision-plane.md L571, qwen38-27b-replace-qwen36.md L153): `- [ ] VB-ROWS-0 — reconstruct the four INDEX_ROWS.md files (wrapup-ec-fold, -gpublock2, -kvu19b, -maskskip; Write + Edits) and hand the row text to the owning session; check each row is not already in scripts/vidya/adapters/README.md first; no compute.`
- **yarn-context-extension-research.md** (JETLONG-LONGCTX-RUN, L255/281): `- [ ] JETLONG-0 — reconstruct jetlong/longctx_skeleton.sh (Write) into epyc-inference-research/scripts/; OPTIONS.md is already at artifacts/yarn-ctx-20261006/; no compute.`

### 1b. Re-point (3 NOT-BLOCKING items, read-only)

- **deepseek-v41-flash-evaluation.md** (DS41-C107/C111, L957): edit the citation: `REPOINTED from /mnt/raid0/llm/tmp/q38fn-lane-inputs-20261003/inbox/61-q38fn-structural-seeds-20261004.md` → `/mnt/raid0/llm/autokernel/campaigns/ak-q38fn-cpu-decode-20261003/store/inbox/61-q38fn-structural-seeds-20261004.md` (campaign store copy, present).
- **deepseek-v41-flash-evaluation.md** (DS41-C41, L348): `- [ ] DS41-C41.0 — the 2026-09-26 inventory is lost AND stale (the 2026-10-20 reclaim removed 344 worktrees, kept 105: /mnt/raid0/llm/tmp/ds41-1017-swap/reclaim-worktrees.md). Regenerate with `python3 scripts/system/worktree_gate.py report` (read-only, seconds) and present that list for the operator's keep/commit/remove decision.`
- **gpu-serving-tie-in-program.md** (YARN-E1-MEM, L285): no new task; append `ARTIFACT LOST (gpu-backlog-20261006 attempt scripts, 2026-10-20 reclaim) — rerun via gpu_window_executor with a fresh launcher as the box already says`.

### 1c. HARD — evidence or binaries must be regenerated or the task re-scoped (8 rows, 6 tasks)

- **vidya-belief-substrate-program.md** (VB-CPU-XFER-1, L2393) + **cpu-decode-roofline-program.md** (L3852/3866): `- [ ] VB-CPU-XFER-1R — re-scope: the 10-03 runs (q38fn-transfer runs/20261003T172030Z, iqk-allow ab-runs/20261003T174700Z) are ARTIFACT LOST (2026-10-20 reclaim; the box's own "copy to a durable location" first step was never done). Reconstruct report.py/run_transfer.sh/ab_q38fn_iqkallow.sh from transcripts into epyc-inference-research/scripts/, write the adapter + write-side belief_measurements.jsonl, and project the NEXT run. Optional regen of the lost runs: one CPU timing window per run (~1-2 h each, Q38FN, whole-host or the run's original shape) — only if a live decision still needs the 10-03 numbers.`
- **vidya-belief-substrate-program.md** (VB-KQROUTE-1, L2381) + **exl3-cpu-mi210-implementation.md** (L99): `- [ ] VB-KQROUTE-1R — re-scope: results/20261004T021143Z is ARTIFACT LOST (2026-10-20 reclaim). Reconstruct ab_kqroute.sh (Write + Edits) into the research repo, add the write side, and make the FIRST projection the later v11-052-gpu run (FILLERS COMPLETE 2026-10-21, candidate B = C + V11-052 MMQ route vs baseline C; outputs under /mnt/raid0/llm/tmp/v11-runs/052/, KEEP-marked — carry its small records to research data/ first). No new compute; regen of the 10-04 run only if needed (one GPU exclusive window ~2 h).`
- **typed-decision-plane.md** (TD-29.M4, L343; L54-56): `- [ ] TD-29.M4.0 — reconstruct launch_champion_sidecar.sh, run_td_bench.sh, window_loop.sh, summarize_td_bench.py (Write + Edits) into the root/orch repo. The pre-K1 receipt (runs/td-20260929/td29/closed_native_id_only.pre-K1.json) is ARTIFACT LOST: either re-run the pre-K1 arm inside the K2 re-run window as its paired comparator (adds one TD native bench arm, same compute class as K2), or re-scope K2 to a fresh paired A/B. Decision for the box owner.`
- **autokernel-rebuild-program.md** (R22-4, L1135): `- [ ] R22-4.0 — first check R22-4 is still live after the v10 freeze; if it is, rebuild r2110-build-{a,b,parent} from their pinned SHAs (R22 rows) into the kernel store (not tmp), build role, ~3 × 15-30 min CPU, no timing window; then R22-4's own ~25 min device time.`
- **learned-routing-controller.md** (P5.2, L521): `- [ ] P5.2.0 — the 2026-06-27 keyed embeddings/IRT artifacts (worker_general_*_20260627_185242.{npz,json}) are ARTIFACT LOST (2026-08-23 reclaim). Regenerate with epyc-orchestrator scripts/calibration/irt_cold_start_ab.py from pinned inputs (verify the input set still exists first), writing to orchestration/reports/p52_irt_cold_start_acceptance/; one CPU-quarter run ~1 h incl. the embedding server; correctness/build role, no quiet window.`
- (champion-sidecar counted above; kqroute and the two XFER runs count as 3 HARD rows; the three worker_general files are 1 task.)

---

## 2. Class D — owner adjudication (6 rows)

Ask each owner to classify before annotation: `ak-ctx-ab` (VB-AK-CTX-1: are the PII-redacted research copies under epyc-inference-research/artifacts/autokernel_ctx_ab_20260925/ enough for the digest-join acceptance?), `full_headline_results.txt`, `halfa_optimal_results.json`, `kvquant_results.json` (numa-topology-cutover-resume-20260730.md L942-946: 2026-07-31 "IN FLIGHT" sinks — if those boxes are superseded, they are C), `p6p7-20261003` (UFH14-A7: does the fix design exist only in the lost report? transcript has Write records), `w6_audit` (evidence-plane-instrument-repair.md L94).

## 3. Class C — leave (decision D3)

131 rows, no live dependency (incl. 13 declared `**Scratch**:` roots that were never populated and 10 template fragments). Recommended: leave the prose; the research checker classifies them only when scanned. If the operator prefers, append `ARTIFACT LOST` only where a C line names the path as *evidence* (not as a Scratch root or a fragment).

## 4. Class A — per-line annotations (decision D2, recommended option b)

157 citing lines in 36 handoffs. 26 paths have a committed copy (REPOINTED), 1 survives as ledger
values, 75 are evidence-lost. Generated list (owner applies):

#### `handoffs/active/gemma-challenge-kernel-techniques-v7.md` — 54 Class-A citation line(s)
- L131: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-quality-20260716, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L131: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-quality-20260716-chat, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L395: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-perf-20260716, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L397: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-server-smoke-20260716T153522Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L398: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-ingest-server-ab-20260716T155557Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L398: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-perf-20260716-postsmoke, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L398: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-spec-server-ab-20260716T155208Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L406: re-point `/mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344` → `research:data/glm52_current_source_ready_smoke_20260717T092344`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344 (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L406: re-point `/mnt/raid0/llm/tmp/glm52-dsa-true64k-probe-20260717T0125` → `research:data/glm52_dsa_true64k_probe_20260717T0125`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/glm52-dsa-true64k-probe-20260717T0125 (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L408: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k24-paired-quiet-20260717T074502Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L414: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k25-mmvq-verify-width-20260717-a, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L416: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k25-mmvq-drafttree-e2e-20260717T101243Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L417: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k25-route-log-smoke-20260717T102617Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L418: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k25-mmvq-route-external-only-20260717T211050Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L419: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k26-kv-cache-bench-20260717-codex, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L422: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k27-retire-q8-8x8-20260717T101836Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L423: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k27-q8-policy-final-20260717T105344Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L448: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k34-numa-distribute-20260717T094451Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L449: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cpu-bench-clean-preflight-20260717T100919Z-record, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L449: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cpu-bench-clean-preflight-20260717T100932Z-strict, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L452: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-worker-general-quarters-cpu-20260717T111949Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L452: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-worker-general-server-cpu-20260717T111809Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L452: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-worker-general-shortctx-recheck-20260717T112435Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L453: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-frontdoor-canonical-20260717T132933Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L453: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-frontdoor-deep-20260717T1218Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L453: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-frontdoor-gpu-smoke-20260717T1207Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L453: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-frontdoor-worker-8k-20260717T1212Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L453: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-worker-canonical-20260717T133244Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L453: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-worker-general-cpu-smoke-20260717T1208Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L453: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-worker-general-deep-20260717T1220Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L454: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-arch-ingest-2k-20260717T121543Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L454: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-arch-ingest-8k-20260717T121645Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L454: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-architect-8k-fixed-20260717T121856Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L454: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-ingest-deep-20260717T122029Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L454: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-ingest-default-2k8k-20260717T123107Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L454: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-ingest-default-deep-20260717T123308Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L456: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-vision-release-smoke-20260717T125719Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L459: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-memory-backfill-20260717T1400Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L460: re-point `/mnt/raid0/llm/tmp/k35-vision-matrix-20260717T1500Z` → `research:data/k35_vision_matrix_20260717T1500Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-vision-matrix-20260717T1500Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L462: re-point `/mnt/raid0/llm/tmp/k35-qwen3vl8-candidate-20260717T185330Z` → `research:data/k35_qwen3vl8_candidate_20260717T185330Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-qwen3vl8-candidate-20260717T185330Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L462: re-point `/mnt/raid0/llm/tmp/k35-qwen3vl8-mi210-default-image-20260717T185459Z` → `research:data/k35_qwen3vl8_mi210_default_image_20260717T185459Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-qwen3vl8-mi210-default-image-20260717T185459Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L464: re-point `/mnt/raid0/llm/tmp/k35-minicpm-o45-candidate-20260717T1909Z` → `research:data/k35_minicpm_o45_candidate_20260717T1909Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-minicpm-o45-candidate-20260717T1909Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L464: re-point `/mnt/raid0/llm/tmp/k35-minicpm-o45-reasoning-off-20260717T1911Z` → `research:data/k35_minicpm_o45_reasoning_off_20260717T1911Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-minicpm-o45-reasoning-off-20260717T1911Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L465: re-point `/mnt/raid0/llm/tmp/k35-minicpm-frontdoor-coresidency-20260717T191849Z` → `research:data/k35_minicpm_frontdoor_coresidency_20260717T191849Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-minicpm-frontdoor-coresidency-20260717T191849Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L482: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-vision-escalation-live-smoke-20260718T1225Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L487: re-point `/mnt/raid0/llm/tmp/k35-minicpm-frontdoor-service-tax-20260717T192427Z` → `research:data/k35_minicpm_frontdoor_service_tax_20260717T192427Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-minicpm-frontdoor-service-tax-20260717T192427Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L488: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/k35-frontdoor-operational-1024-20260717T201842Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L490: re-point `/mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z` → `research:data/k35_minicpm_service_matrix_20260717T2045Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-minicpm-service-matrix-20260717T2045Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L491: re-point `/mnt/raid0/llm/tmp/k35-supergemma4-candidate-20260717T193120Z` → `research:data/k35_supergemma4_candidate_20260717T193120Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/k35-supergemma4-candidate-20260717T193120Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L492: re-point `/mnt/raid0/llm/tmp/paddleocr-vl-first-smoke-20260717T194332Z` → `research:data/paddleocr_vl_first_smoke_20260717T194332Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/paddleocr-vl-first-smoke-20260717T194332Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L492: re-point `/mnt/raid0/llm/tmp/paddleocr-vl-receipt-extract-20260717T194415Z` → `research:data/paddleocr_vl_receipt_extract_20260717T194415Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/paddleocr-vl-receipt-extract-20260717T194415Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L493: re-point `/mnt/raid0/llm/tmp/odl-paddleocr-vl-demo-20260717T200212Z` → `research:data/odl_paddleocr_vl_demo_20260717T200212Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/odl-paddleocr-vl-demo-20260717T200212Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L494: re-point `/mnt/raid0/llm/tmp/odl-paddleocr-vl-htmltables-20260717T201106Z` → `research:data/odl_paddleocr_vl_htmltables_20260717T201106Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/odl-paddleocr-vl-htmltables-20260717T201106Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L496: re-point `/mnt/raid0/llm/tmp/odl-paddleocr-vl-postprocess-rescore-20260717T211432Z` → `research:data/odl_paddleocr_vl_postprocess_rescore_20260717T211432Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/odl-paddleocr-vl-postprocess-rescore-20260717T211432Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.

#### `handoffs/active/agentic-serving-harness-fixes.md` — 13 Class-A citation line(s)
- L142: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/ufh14-b1-ec-review, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L154: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/ufh14-b1-ec-review, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L196: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/kv-gate-8083-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L259: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L301: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L356: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/kv-gate-8083-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L367: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/integ2-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L425: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L450: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/integ2-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L456: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/integ2-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L459: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/integ2-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L484: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L491: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.

#### `handoffs/active/gpu-cot-scaffold-sidecar.md` — 9 Class-A citation line(s)
- L7: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L9: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L24: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L28: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L58: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L148: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L160: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L186: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L240: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/batched-decode-measurement.md` — 7 Class-A citation line(s)
- L148: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/evalbatch-evaltower-plan-smoke-2, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L690: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/e5-a6-trimmed-window, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L737: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/e5-a5-replay, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L746: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/era-repair, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L748: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/era-repair, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L823: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/e5-a6-trimmed-window, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L824: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/e5-a6-trimmed-window, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/deepseek-v41-flash-evaluation.md` — 6 Class-A citation line(s)
- L40: re-point `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` → `root:artifacts/backlog-schedule-20261004/backlog-schedule-20261004.md`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/backlog-schedule-20261004.md (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L872: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/ds41-c83-planner-gap-report.md, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L921: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/ds41-c98-package-20261003.md, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L1032: re-point `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` → `root:artifacts/backlog-schedule-20261004/backlog-schedule-20261004.md`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/backlog-schedule-20261004.md (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L1114: re-point `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` → `root:artifacts/backlog-schedule-20261004/backlog-schedule-20261004.md`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/backlog-schedule-20261004.md (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L1181: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/disk-audit-20261007, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/autokernel-champion-aggregate.md` — 6 Class-A citation line(s)
- L148: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/gpu-champion-ab, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L586: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/fold-window-20260908, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L690: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/gpu-champion-ab, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L708: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/gpu-champion-ab, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L730: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/gpu-champion-ab, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L732: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/gpu-champion-ab, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/kv-unified-stack-rollout.md` — 6 Class-A citation line(s)
- L121: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L160: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L167: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L232: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L460: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/kv-gate-8083-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L473: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/serving-timing-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/autokernel-unified-surface-program.md` — 5 Class-A citation line(s)
- L479: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/aku-full-roster-dryrun-inputs-20260910, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L510: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/aku-cpu-gpu-dryrun-inputs-20260910, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L565: re-point `/mnt/raid0/llm/tmp/aku12a-glm53-five-loop-output-continuation` → `root:artifacts/autokernel/glm53-evidence-20260922/files/aku12a-glm53-five-loop-output-continuation`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/aku12a-glm53-five-loop-output-continuation (lost unlogged removal before 2026-10-20; recorded 2026-10-25)`.
- L1294: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/fold-window-20260908, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L3794: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/aku-final-all8-dryrun-20260910-v2.log, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/speculative-decoding-mtp-refresh.md` — 5 Class-A citation line(s)
- L181: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/gpu-champion-ab, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L204: re-point `/mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-broad-20260717T212947Z` → `research:data/qwen35_9b_mtp_mi210_broad_20260717T212947Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-broad-20260717T212947Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L204: re-point `/mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-longoutput-20260717T202636Z` → `research:data/qwen35_9b_mtp_mi210_longoutput_20260717T202636Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-longoutput-20260717T202636Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L204: re-point `/mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-quality-20260717T202549Z` → `research:data/qwen35_9b_mtp_mi210_quality_20260717T202549Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/qwen35-9b-mtp-mi210-quality-20260717T202549Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L208: re-point `/mnt/raid0/llm/tmp/t5-gemma-worker-draft-depth-20260717T213641Z` → `research:data/t5_gemma_worker_draft_depth_20260717T213641Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/t5-gemma-worker-draft-depth-20260717T213641Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.

#### `handoffs/active/routing-intelligence.md` — 4 Class-A citation line(s)
- L53: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/ri16, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L54: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/ri16, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L189: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/sequencer-8d, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L258: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/integ2-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/internal-kb-rag.md` — 4 Class-A citation line(s)
- L86: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/kbrag_k7_eval_20260612, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L88: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/kbrag_index_k7_20260612, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L88: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/kbrag_k7_cert_parallel_20260613_075405, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L423: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/kbrag_index_k7_20260612, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/frontier-f3-data-flywheel.md` — 3 Class-A citation line(s)
- L22: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/f3-datasets-smoke-20260614-codex, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L54: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/sub-gpu, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L162: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/f3-datasets-smoke-20260614-codex, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/exl3-cpu-mi210-implementation.md` — 2 Class-A citation line(s)
- L127: re-point `/mnt/raid0/llm/tmp/cpu-window2-20261004` → `root:artifacts/cpu-window2-20261004/`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/cpu-window2-20261004 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L128: re-point `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` → `root:artifacts/backlog-schedule-20261004/backlog-schedule-20261004.md`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/backlog-schedule-20261004.md (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.

#### `handoffs/active/CURRENT-CAMPAIGN.md` — 2 Class-A citation line(s)
- L56: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.
- L280: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/cot-g1, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/non-inference-backlog.md` — 2 Class-A citation line(s)
- L387: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/disk-audit-20261007, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L391: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/disk-audit-20261007, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/llama-cpp-dsa-contribution.md` — 2 Class-A citation line(s)
- L110: re-point `/mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344` → `research:data/glm52_current_source_ready_smoke_20260717T092344`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344 (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L110: re-point `/mnt/raid0/llm/tmp/glm52-dsa-true64k-probe-20260717T0125` → `research:data/glm52_dsa_true64k_probe_20260717T0125`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/glm52-dsa-true64k-probe-20260717T0125 (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.

#### `handoffs/active/vidya-belief-substrate-program.md` — 2 Class-A citation line(s)
- L1969: append to the citing line: `ARTIFACT LOST (2026-10-20 reclaim + same-minute purge; measured values survive in the belief ledger as 48 claim_proposed frames, source ids src_inf70_results_ds41scope_20260926T105535Z_*) — recorded 2026-10-25`.
- L2242: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.

#### `handoffs/active/cpu-decode-roofline-program.md` — 2 Class-A citation line(s)
- L3858: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/ws58-q38fn-armP, unlogged removal before 2026-10-20) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L3866: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/iqk-allow-ab, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/autokernel-research-loop.md` — 2 Class-A citation line(s)
- L5589: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/mmq-jcap-ab-20260927T020637Z, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L5602: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/mmq-jcap-ab-20260927T020637Z, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/opendataloader-pipeline-integration.md` — 2 Class-A citation line(s)
- L50: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/odl013-bench-20260813T1336Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L55: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/odl013-bench-20260813T1336Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/dflash2-block-drafter-experimental-build.md` — 2 Class-A citation line(s)
- L225: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/p1-lookup-replay-20261003, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L237: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/p1-lookup-replay-20261003, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/thesis-experiment-orchestrator-vs-strongest-model.md` — 2 Class-A citation line(s)
- L286: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/sequencer-8d, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).
- L289: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/sequencer-8d, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/multimodal-pipeline.md` — 2 Class-A citation line(s)
- L103: re-point `/mnt/raid0/llm/tmp/stt_wer_results.json` → `research:data/speech_kernel_freeze_20260731/stt_wer_results.json`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/stt_wer_results.json (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.
- L304: re-point `/mnt/raid0/llm/tmp/stt_wer_results.json` → `research:data/speech_kernel_freeze_20260731/stt_wer_results.json`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/stt_wer_results.json (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.

#### `handoffs/active/iqk-iquant-enablement.md` — 1 Class-A citation line(s)
- L118: re-point `/mnt/raid0/llm/tmp/backlog-schedule-20261004.md` → `root:artifacts/backlog-schedule-20261004/backlog-schedule-20261004.md`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/backlog-schedule-20261004.md (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.

#### `handoffs/active/autokernel-all-devices-all-dimensions.md` — 1 Class-A citation line(s)
- L766: re-point `/mnt/raid0/llm/tmp/cpu-window2-20261004` → `root:artifacts/cpu-window2-20261004/`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/cpu-window2-20261004 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.

#### `handoffs/active/glm52-reviewer-capability-gates.md` — 1 Class-A citation line(s)
- L170: re-point `/mnt/raid0/llm/tmp/glm52-current-source-96k-quality-20260717T144022Z` → `research:data/glm52_current_source_96k_quality_20260717T144022Z`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/glm52-current-source-96k-quality-20260717T144022Z (lost 2026-08-23 disk reclaim; recorded 2026-10-25)`.

#### `handoffs/active/qwen38-27b-replace-qwen36.md` — 1 Class-A citation line(s)
- L142: re-point `/mnt/raid0/llm/tmp/gpu-block-27b-20261003` → `root:artifacts/gpu-block-27b-20261004/runners/ (runners+RUNBOOK; results/ec2_lease NOT carried)`; keep the old path on the line as `REPOINTED from /mnt/raid0/llm/tmp/gpu-block-27b-20261003 (lost 2026-10-20 reclaim + same-minute purge; recorded 2026-10-25)`.

#### `handoffs/active/architect-model-selection-bench.md` — 1 Class-A citation line(s)
- L216: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/h1_paired_analysis.py, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/stack-change-governance-pipeline.md` — 1 Class-A citation line(s)
- L135: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/integ2-ec, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/learned-routing-controller.md` — 1 Class-A citation line(s)
- L520: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/irt_prompt_scores_smoke.npz, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/fable5-window2-findings-03-portfolio-and-master-queue.md` — 1 Class-A citation line(s)
- L70: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/mainc-core-v2-20260729, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/autokernel-orchestrator-actor-backend.md` — 1 Class-A citation line(s)
- L125: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/oab2-smoke, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/evidence-plane-ledger-and-sequential-verdicts.md` — 1 Class-A citation line(s)
- L324: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/paired-stats-worktree, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/autokernel-rebuild-program.md` — 1 Class-A citation line(s)
- L1077: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/r23-5-results, 2026-10-20 reclaim + same-minute purge) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/tq3-quantization-evaluation.md` — 1 Class-A citation line(s)
- L194: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/v7-bonsai8b-gpu-bench-current-20260718T141319Z, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

#### `handoffs/active/numa-topology-cutover-resume-20260730.md` — 1 Class-A citation line(s)
- L1566: append to the citing line: `ARTIFACT LOST (/mnt/raid0/llm/tmp/w1-26b5f442, 2026-08-23 disk reclaim) — recorded 2026-10-25`; if the box's number gates a live decision, also file a re-measure / demote-to-prior item (decision D2).

---

## 5. Guard work — tasks to file (owning handoff: non-inference-backlog.md; design: work/guards-design.md)

- `- [ ] **NIB2-105** (HIGH): **citation oracle** — new stdlib-only scripts/system/citation_oracle.py (reverse index: who cites PATH?) over root handoffs/active+blocked on origin/main AND the working tree, FILLERS.md + grants + bookings + live launchers, the canonical belief ledger /mnt/raid0/llm/state/vidya/ledger.jsonl (+ legacy .vidya copies), research model_registry.yaml, AK campaign inputs, launch manifest, bus config, observer registry, crontab. Relations: exact, descendant, ancestor, basename, parent/basename. NO size parameter. Fail CLOSED on any unreadable source (exit 3). Reuse the research checker's EPHEMERAL_ROOTS / brace expansion / REPOINTED-from / ARTIFACT-LOST grammar by import (adds a cross-repo edge to .claude/dependency-map.json). Tests: tests/test_citation_oracle.py + tests/test_reclaim_size_threshold_regression.py (0 B, 1 KiB, 0.019 GiB, 1 GiB entries cited only by basename → all KEEP-CITED).`
- `- [ ] **NIB2-106** (HIGH): **guarded_rm.sh + trash-sweep.sh refuse cited paths** — guarded_rm: one oracle call before mkdir (:64), refuse cited targets unless --cited-ok <approval-ref> (audit-logged), always refuse UNVERIFIABLE; write .trash/.manifests/<entry>.json provenance after mv (:74); fix same-second name collision (:72) and audit JSON escaping (:29-30). trash-sweep: refuse --older-than < 7 (:102) except an --exact FILE --approval REF mode; re-run the oracle on each entry's ORIGINAL path before rm (:119-124) and defer cited/untraceable entries; fresh-hash purge record before each delete. Tests: scripts/hooks/tests/test_guarded_rm_citation_gate.sh, test_trash_sweep_residency.sh. Doctrine change in agents/shared (Destructive operations) is human-only → ratify package.`
- `- [ ] **NIB2-107** (HIGH): **scratch_cleanup.py / worktree_gate.py / autokernel_disk_sweep.py call the oracle** — KEEP-CITED verdict (scratch_cleanup build_plan :219/:288-296, apply_plan re-check :339/:376; worktree_gate classify :429-432, remove_one :547, stop silent skips :266/:311; autokernel_disk_sweep make_context :1055, :912, apply :1208, _git_source_texts raise not return-empty :507-516, replace rmtree :1239 with guarded_rm.sh). Extend tests/test_scratch_cleanup.py, test_worktree_gate.py, test_autokernel_disk_sweep.py.`
- `- [ ] **NIB2-108** (MEDIUM): **sanctioned ad-hoc reclaim path** — scripts/system/reclaim_scratch.py: plan → confirm token → fresh per-row oracle + KEEP + process re-check → guarded_rm.sh / git worktree remove only; never purges; size reported, never decides; tmp/compute-flags never a candidate. Plus hook scripts/hooks/check_destructive_scratch.sh (+ destructive_scratch_scan.py, scans python3/bash <file> contents, which catches purge_batch.py-style inline purges); registering it in .claude/settings.json is the operator's call.`
- `- [ ] **NIB2-109** (MEDIUM): **detection backstop** — host_hygiene_tick.py daily: alarm cited-evidence-vanished (cited path gone with no deletion record) and trash-unsanctioned-purge (trash entry gone outside trash-sweep.sh); backup_coverage.py:53 STORES gains research_data + vidya_state rows (report-only).`
- Belief-kernel wiring (CLAUDE.md, surface now): a source-table row in scripts/vidya/adapters/README.md for a `reclaim_guard` adapter (oracle refusals + vanished-citation alarms as findings) and a task in vidya-belief-substrate-program.md: `- [ ] **VB-RECLAIM-GUARD-1** — write side + projection for citation-oracle refusals and hygiene vanished-evidence alarms (source row in scripts/vidya/adapters/README.md); grade via claim_tuple.grade(), no new ladder.`

## 6. Index rows

No new handoff is proposed, so **no index row is added**. All tasks above live in existing handoffs
already owned by an index. Run `python3 scripts/handoffs/index_state.py --check` after applying.
