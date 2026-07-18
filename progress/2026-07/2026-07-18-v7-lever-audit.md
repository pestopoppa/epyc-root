# 2026-07-18 — v7 kernel lever audit + inference-research handoff refresh

Operator-requested read-only audit of ~5 weeks of v7-experimental + CPU/GPU/spec-dec/GLM
optimization work, delivered as a refreshed inference-research handoff set for the parallel
inference agent. Docs-only; **no production kernel or inference touched** (production frozen).

## Method
5 parallel research agents swept: the v7 tracker + reviewer-control-plane tail, GPU/MI210
lever taxonomy, CPU lever taxonomy (roofline), July progress reports (negative-results
sweep), GLM-5.2 acceleration state, and spec-dec/MTP state. Cross-verified against live
branch state (`experimental-v7-refresh-20260716` @ `d1e5a20eb`: iqk + GPU-opt flags +
`GGML_TYPE_Q2_0`=42 all present on disk) and the master-index operator-decision queue.

## Headline finding
The single largest measured performance win is **already built, correctness-verified, and
banked — but UNPROMOTED**. v7 refresh carries HIP graphs +25% worker spec-dec, MMVQ→MMQ
+17–32%, bf16-GDN-state +16–21% agg, +37% single-stream dense-Q8. K5 quality gate PASSED
(v6≈v7, +0.0%); all P0 correctness blockers resolved (K22 `96986f5e9`, K23 `3dee86a5a`,
K32/K33). v7 is held only by operator gates (K35 finalize, OP-2 canonical bench, `P-GPU-1`
ratification) + the CPU-correctness gate — not by missing engineering.

## Frontier reframes (recorded for the parallel agent)
- **CPU decode is bandwidth-exhausted** (0.17 IPC, 96.6% memory-stalled @96t) — proven, not
  asserted. The *sole* live CPU decode lever is Q8_0 barrier-count operator/graph fusion
  (+2.6% measured → +10–15% graph-rewrite → +72% ceiling). Untapped large-model regime =
  **prefill-compute** (compute-bound, not BW-killed) → new track.
- **GPU raw-speed frontier is structurally exhausted** (both occupancy rewrites falsified;
  single-stream dense-Q8 at +37% ceiling). Live GPU frontier = **residency + teleport**
  (AXA-1 now unblocked by the K22 grammar fix) + two residuals (stream-K, K28).
- **GLM acceleration EV is contingent on quality repair** (patch-review FA up to 91.7%);
  native-GLM-MTP port (+34–89% decode) and real sparse final-attention sequence AFTER
  GC-shadow-repair4b → P-REV-1.

## Two-lane queue delivered
- **LANE A (operator-facing):** A1 K35 finalize · A2 OP-2 canonical-bench window · A3
  `P-GPU-1` ratification package · A4 branch-naming reconciliation.
- **LANE B (agent-executable):** B1 barrier-fusion tg128 A/B (fold into A2) · B2 stream-K
  pmc-CSV read · B3 MoE-Spec reopen assessment · B4 DSA-D3 profile (fold into A2) · B5 E3/E4
  zero-inference decisions · B6 native-GLM-MTP scoping (build gated on GLM quality) · B7
  prefill-compute PC-0.

## Deliverable — handoff edits (docs-only)
Modified: `inference-acceleration-index.md` (new §v7 lever audit + two-lane queue + ledger +
checklist rows), `cpu-inference-optimization-index.md` (BW-exhausted reframe + prefill-compute
row), `mi210-big-model-and-acceleration-roadmap.md` (stream-K + K28 owned tasks + frontier
note), `gemma-challenge-kernel-techniques-v7.md` (v7 promotion-readiness block),
`tree-draft-forward-port-plan.md` (native-GLM-MTP gate update: PR#21149 stale → quality gate;
new task), `glm52-reviewer-capability-gates.md` (acceleration-gating note),
`master-handoff-index.md` (2026-07-18 coordination checkpoint).
Created: `cpu-prefill-compute-large-models.md`, `gpu-drafter-control-redesign.md` (both
user-approved new tracks).

## Verification
- Link integrity: all new cross-links resolve (checked programmatically).
- No production-kernel/`/mnt/raid0` path in the epyc-root working tree.
- Handoff-freshness validator: PASS (tree-draft 2026-07-18 ok).
- Checkbox discipline: all additions are open `- [ ]` tasks; no un-checkboxed completion claims.
- Known pre-existing (NOT this session): `wiki/source_manifest.json` doc-drift is stale for
  171 files from the parallel session's work (only 2 are mine); manifest regeneration is a
  separate wiki-tooling task and would fold in 169 unrelated changes — left for the wiki owner.

## Memory
Filed `project_v7_lever_audit_2026_07_18` (v7 banked-but-unpromoted = highest EV; CPU decode
BW-exhausted → barrier-fusion sole live decode lever; GLM kernel work gated on quality).

---

## Follow-up (2026-07-18 PM — interactive advisory + v7 promotion structure)

Continuation of the same session; operator Q&A on promotion structure + governance cleanup.
All docs-only; shared tree with an active parallel inference agent (careful single-file commits).

**Parallel agent progress on the plan (observed):** in ~30 min it closed most of the two-lane
queue — A1 (K35 finalize), A3 (P-GPU-1 package), A4 (branch tip = `experimental-v7-refresh-20260716`
@ `d1e5a20eb`), B2 (stream-K read: already live, compact-LDS negative), B3 (MoE-Spec reopen
decision), B5 (E3/E4), B6 (native-GLM-MTP scaffold now **builds + passes bounded CPU draft-mtp
smokes** — feasibility proven), B7 (prefill-compute), DR-1 (break-even model: external Stage-1/2
failed at α=1.0 → blocker is control/overhead cost). Agent-executable kernel work is essentially
exhausted; remainder is operator-window-gated (OP-2 bundle) or GLM-quality-gated.

**Deliverables this round:**
| Change | File(s) | Commit |
|---|---|---|
| COUPLED v7 promotion gate (operator-chosen: hold v7 until GLM optimized decode confirmed) | `v7-promotion.md` (initially misplaced in `v6-iqk-promotion.md`, corrected) | `bd64aff5`, `ea25e0a6` |
| Split v7 promotion into its own handoff `v7-promotion.md` (v6→v7 is a distinct cutover; reuses v6 phased procedure + rollback) | `v7-promotion.md` new; `v6-iqk-promotion.md` → forward-pointer | `ea25e0a6` |
| **Archived** `v6-iqk-promotion.md` → `handoffs/completed/` (cutover complete 2026-06-26; residual OP-2 bench owned by cpu-index P0 / OP-2 package / v7-promotion Phase-J) + ARCHIVED banner | `git mv` + banner + link repoints | `b10913ab`, `247db5d5` |
| `/goal` start-here note (run as `/goal`, lead with P2 eval-tower) | `inference-batch-loop.md` | `b10913ab` |
| Reviewer language generalized: GLM-5.2 is **one** candidate; reviewer choice open/undecided (Qwable+architect only an example); don't over-constrain exploration | `v7-promotion.md` | `ac269350` |

**Correction recorded (rigor):** I initially claimed OP-2 was "runnable now, not reboot-blocked"
because a reboot happened ~2 weeks ago. On checking MEASUREMENT.md discipline this was **wrong** —
"post-reboot canonical bench" is a cold-cache/clean-NUMA/no-throttle requirement, and ~2 weeks of
uptime is not that fresh state. So OP-2 still needs a verified bench-clean host or the next operator
reboot window; it is **not** closer to done. Only my "waiting a month" phrasing was stale (→ ~2 weeks).
The OP-2 owners' "post-reboot" wording was left unchanged (it is correct, not stale).

**Shared-tree discipline:** repoints for the v6-iqk archive were committed surgically (3/4 via
`git apply --cached --unidiff-zero`, agent WIP untouched); `inference-acceleration-index.md`'s
repoint rides with the agent (its edit sat on a table row adjacent to mine → not isolable).

**Deferred / for the operator:** v7 production promotion is operator-authorized (frozen kernel);
the coupled gate now drives the agent to READY-then-STOP. GLM-as-reviewer is undecided.
