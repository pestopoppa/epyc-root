# Stale-Open Backlog Audit — 2026-07-18

**Status**: ACTIVE/REFRESHING — initial 22-handoff audit completed 2026-07-18; current-inventory reconciliation and exact-partition follow-up opened 2026-07-29.
**Priority**: HIGH
**Created**: 2026-07-18
**Categories**: governance, measurement, handoff-hygiene
**Parent index**: [`master-handoff-index.md`](master-handoff-index.md)

**Trigger**: operator question — *"if the inference-batch-loop consolidation is only 11 checkboxes, what are the remaining ~660 open tasks about?"* The board's headline open-task count (678 active+blocked, 2026-07-18) treats **every unchecked box as live work**. This audit measures how much of that is actually **stale-open**: work that landed, was superseded, deprioritized, parked, or is owned by another handoff — but whose boxes were never flipped (deprioritized ≠ done, so they were correctly never checked; they just shouldn't read as live backlog).

## Method

For each flagged handoff: read the full file, get git last-touch, classify the leading **Status**/**Priority** verbs, skim every open `- [ ]`, and cross-ref any "owned by / claim X there / superseded by" pointer to confirm where the work really lives. Verdict ∈ `LIVE | PARKED | SUPERSEDED | LANDED | DUPLICATE | MIXED`; each handoff gets a `live_open` vs `stale_open` split. **No checkbox flips** — recommendations are re-anchor / close / split / reactivate / add-`Lifecycle`-override.

Scope = the 22 handoffs the board's status-signal scan flagged (parked/landed keyword in Status or Priority). This is the *candidate* net; the board's own dimming signal is deliberately narrower (5 cards) to avoid ever dimming a live handoff.

## Headline (all 22 flagged handoffs)

| | Open tasks | Genuinely live | Stale-open |
|---|---:|---:|---:|
| Batch A (kernel/GPU, 8) | 64 | 14 | 50 |
| Batch B (routing/eval/RAG, 7) | 81 | 19 | 62 |
| Batch C (stack/infra, 7) | 28 | 6 | 22 |
| **Total (22)** | **173** | **39** | **134 (77%)** |

**Historical 2026-07-18 finding:** 77% of the open tasks in the flagged handoffs (134 of 173) were stale-open — landed, superseded, deprioritized, parked, or frozen behind an unfired gate. The then-derived `≈544` was a dated heuristic, not a current board count.

Caveat: this audits only the **22 flagged** handoffs (those whose Status/Priority carried a park/landed keyword). The other ~105 open handoffs were not individually audited. The current dispatch inventory, not this historical heuristic, is the source for current raw counts.

## Per-handoff verdicts

### Batch A — kernel / GPU

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [cpu-shape-specialized-gemv-decode](cpu-shape-specialized-gemv-decode.md) | 38 | 2 | MIXED | re-anchor — kernel LANDED 2026-04-24, SIMD Phase 0–5 deprioritized; box only the 2 live graph-fusion tasks |
| [gemma-challenge-kernel-techniques-v7](gemma-challenge-kernel-techniques-v7.md) | 9 | 6 | LIVE | keep — split K28 out (owned in mi210 roadmap); correctly NOT board-flagged |
| [llamacpp-v6-consolidation](llamacpp-v6-consolidation.md) | 6 | 1 | SUPERSEDED | close → completed (v6 cutover shipped 2026-06-26); re-anchor 5 items to v7 |
| [llama-cpp-dsa-contribution](llama-cpp-dsa-contribution.md) | 4 | 4 | **LIVE** | **add `Lifecycle: live` override** — board over-flags it "superseded" (only the *original* objective was); D2/D3 re-anchored + live. GLM-5.2 box co-owned by glm51-reap |
| [qwen36-27b-cpu-feasibility](qwen36-27b-cpu-feasibility.md) | 4 | 0 | PARKED | keep parked (CPU foreclosed) **+ cross-link the MI210 GPU campaign** (see callout) so it doesn't read as "dead model"; consider close |
| [gpu-drafter-mi200-investigation](gpu-drafter-mi200-investigation.md) | 1 | 0 | LIVE | re-anchor — Stage 4 box blocked on Stages 1–3 (failed economics 2026-07-17); add drafter-redesign task |
| [sarathi-serve-cpu-evaluation](sarathi-serve-cpu-evaluation.md) | 1 | 0 | PARKED | **reactivate** — multi-tenant trigger may have fired via batched-decode E1/E2 (active) |
| [agent-file-prose-compression](agent-file-prose-compression.md) | 1 | 1 | LIVE | keep — single operator rollout decision pending |

### Batch B — routing / eval / RAG

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [decision-aware-routing](decision-aware-routing.md) | 26 | 3 | PARKED | re-anchor — core FROZEN/closed in routing-truth-restoration W8; keep only Factory-ai/URE backlog |
| [learned-routing-controller](learned-routing-controller.md) | 17 | 2 | MIXED | split — live BGE+MLP rollout decision vs FROZEN Phase 1.5+ expansion |
| [glm51-reap-cpu-evaluation](glm51-reap-cpu-evaluation.md) | 11 | 9 | LIVE | keep — real work; true blocker = operator-approved GLM inference runs |
| [colbert-reranker-web-research](colbert-reranker-web-research.md) | 10 | 2 | PARKED | re-anchor — close S5 request-path NO-GO; keep inference-gated LateOn/DenseOn latency+A/B |
| [internal-kb-rag](internal-kb-rag.md) | 8 | 0 | LANDED | re-anchor — K1–K7 CERTIFIED 2026-06-13; keep only deferred K8 + optional Hy-MT2 |
| [minddr-deep-research-mode](minddr-deep-research-mode.md) | 8 | 2 | LIVE | keep — MD-9 A/B inference-gated. **Reactivate note**: Phase-2 hardware gate flipped (DGX→MI210 present) |
| [x-mas-text-routing](x-mas-text-routing.md) | 1 | 1 | LANDED | re-anchor — enforce enabled (`d4a6c927`); convert to standing telemetry-watch |

### Batch C — stack / infra

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [model-stack-single-source-update-pipeline](model-stack-single-source-update-pipeline.md) | 7 | 0 | PARKED | re-anchor as the authoritative consumer-SSoT contract; reconcile the stale X-MAS default-off box (enforce already enabled) |
| [standardized-stack-update-pipeline-finalization](standardized-stack-update-pipeline-finalization.md) | 3 | 0 | **DUPLICATE** | consolidate/close into `stack-change-governance-pipeline`; core landed |
| [per-request-reasoning-budget](per-request-reasoning-budget.md) | 4 | 4 | LIVE | keep — llama.cpp implementation genuinely pending (inference window + experimental branch) |
| [unified-trace-memory-service](unified-trace-memory-service.md) | 3 | 0 | PARKED | split — close landed T1–T6 nav parent; keep T7 (Hermes-daily-use gate, unfired) + consolidation parked |
| [frontier-f2-self-running-lab](frontier-f2-self-running-lab.md) | 2 | 2 | LIVE | keep — W3 accumulating now (real quiet-window batches producing verdicts), W4 sequenced |
| [sliders-local-validation](sliders-local-validation.md) | 8 | 0 | PARKED | **reactivate signal** — KB-RAG K7 reopen precondition FIRED 2026-06-13; surface to operator (still needs explicit ask; else keep parked, LOW/speculative) |
| [security-review-skill](security-review-skill.md) | 1 | 0 | PARKED | close — skill shipped + in production; keep CI-gate as a deferred backlog note |

## Cross-cutting findings

1. **Reopen-triggers that already fired (REACTIVATE candidates).** MI210 GPU installed 2026-07-02 flipped hardware gates that predate it: `gpu-drafter-mi200` (fired; Stages 1–2 ran + failed economics), `minddr` Phase-2 (DGX abandoned → MI210 training-viability smoke now possible), `sarathi-serve` (multi-tenant trigger via active batched-decode E1/E2). These read as "parked" but their premise changed.

2. **The Qwen3.6-27B fragmentation error (exemplar).** `qwen36-27b-cpu-feasibility` is correctly parked *on CPU* (BW-roofline ~7.5–9 t/s, GDN spec-dec wall) — but the **same model was characterized extensively on the MI210 GPU** in the operator-launched 2026-07-03 speed campaign (`progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md`): plain Q8 29.5 → **40.4 t/s (+37%)** via embedded-NEXTN MTP + MMVQ→MMQ fix (`de447119f`), EAGLE-3 tested (no-go), GDN-MFMA profiled+killed. That banked "dense-Q8 +37%" win in `v7-promotion.md` is this model. **The parked CPU handoff never cross-links the GPU campaign** — so reading it alone wrongly implies the model is dead. A single research thread's work is split across a parked handoff and a thriving one that it doesn't reference. This is why the raw open count both over-counts backlog *and* mis-reads liveness.

3. **Frozen-behind-an-unfired-gate is the dominant stale pattern.** The largest stale masses (decision-aware-routing 23, learned-routing-controller 15, GEMV 36) are all work correctly halted by an explicit gate whose reopen trigger has been tested and NOT fired (DAR-1 replay 0.00%; GEMV kernel-ceiling proven barrier-bound). Boxes are honestly unchecked; they simply aren't live.

4. **Board signal reconciliation.** The live board dims only 5 cards (high-precision). This audit's wider net (22) surfaces LANDED/SUPERSEDED/frozen cases the conservative heuristic intentionally skips (e.g. `internal-kb-rag` LANDED, `decision-aware-routing` frozen). Fix path: encode audited verdicts as explicit `**Lifecycle**:` fields (authoritative over the heuristic) — including a `Lifecycle: live` override on `llama-cpp-dsa-contribution`, which the heuristic over-flags.

5. **A five-handoff duplicate cluster on the stack-update pipeline.** `model-stack-single-source-update-pipeline` (N11a), `standardized-stack-update-pipeline-finalization` (N11), `model-stack-update-pipeline-audit`, `model-stack-change-standardization-audit`, and `stack-change-governance-pipeline` all describe the **same landed pipeline**. `model-stack-update-pipeline-audit` self-demotes to "historical-detail support"; the routing index already merges N11 + governance into one row. **Authoritative pair**: `model-stack-single-source-update-pipeline` (consumer-SSoT) + `stack-change-governance-pipeline` (command/gates). **Redundant**: `standardized-stack-update-pipeline-finalization` + the two audit docs. Core work is landed; every remaining open box across the cluster is opportunistic-on-new-finding or evergreen discipline — none actionable now. Consolidating this cluster is the single highest-leverage backlog cleanup. **2026-07-18 execution correction (on verification):** the "retire 3" framing was too coarse — only `standardized-stack-update-pipeline-finalization` is cleanly retirable (its sole live box, W4 swap-CI, is co-tracked in both authoritative docs); `model-stack-update-pipeline-audit` has 2 **orphan-live** boxes (`ctx_model_max`, tap/policy-hint) tracked in *neither* authoritative doc, so it stays LIVE until they migrate; `model-stack-change-standardization-audit` is a repeatable **runbook**, not done-work. Soft-consolidation (Lifecycle + pointer notes) applied 2026-07-18; hard-archive + orphan-box migration + index repointing is operator-gated.

## Recommendations (follow-up tasks — no checkbox flips on the audited handoffs)

- [x] Add `**Lifecycle**: live` to `llama-cpp-dsa-contribution` (board over-flags it superseded) ✅ 2026-07-18
- [x] Cross-link the MI210 GPU speed campaign into `qwen36-27b-cpu-feasibility` (parked-on-CPU ≠ dead model) ✅ 2026-07-18
- [x] Surface the fired reopen-triggers (gpu-drafter MI210-gate, minddr DGX→MI210, sarathi batched-decode E1/E2) with dated notes + reactivate `- [ ]` tasks in each handoff ✅ 2026-07-18
- [ ] Re-anchor GEMV to its 2 live graph-fusion tasks; move the deprioritized SIMD Phase 0–5 plan to a closed appendix
  - **VERIFIED 2026-07-29 (`auditor`), handed to the CPU-lane owner — NOT executed here**, because this
    section is headed *"no checkbox flips on the audited handoffs"* and the move would effectively close
    26 boxes. **The recommendation is correct and the target handoff says so itself:** line 5 reads
    *"Priority: ~~MEDIUM~~ DEPRIORITIZED for the SIMD ukernel; but the barrier/op-count sub-lever is
    RE-ELEVATED"*, and its verdict section adds *"Not pursued. ROI doesn't beat the production-side
    alternative"* and *"CPU2 closes here for Q8 specifically — the 4.4 t/s ceiling is genuinely
    architecture-bound"*, with two graph-rewrite probes recorded as disproved.
    **Measured:** 36 open boxes in that file — 10 are the Pickup Checklist (a reusable template, guarded
    separately today), and **26 are Phases 0–5 of the very plan the header calls deprioritized.**
    The two live anchors to keep: the barrier/op-count sub-lever, and the qwen35 DeltaNet fusable
    cluster `wqkv + wqkv_gate + ssm_beta + ssm_alpha` named in the verdict.
    **This is the cleanest `stale by supersession` case found so far** — not *already done* but
    *overtaken by the handoff's own recorded verdict* — and it is invisible to every mechanical
    detector tried today, because each box's own text reads fine and only the header and verdict
    elsewhere in the file contradict it. 26 boxes in one file is why the ~1/3-live estimate looks
    plausible.
- [ ] Close/relocate the LANDED/SUPERSEDED handoffs (v6-consolidation → completed; kb-rag K1–K7 certified; x-mas → telemetry-watch)
- [ ] Split `learned-routing-controller` and `decision-aware-routing`: live rollout/backlog vs frozen-behind-unfired-gate expansion
- [x] Stack-cluster soft-consolidation (corrected on verification — NOT a clean "retire 3"): superseded `standardized-stack-update-pipeline-finalization` (W4 co-tracked); kept `model-stack-update-pipeline-audit` LIVE (2 orphan boxes); flagged `model-stack-change-standardization-audit` as a repeatable runbook ✅ 2026-07-18
- [ ] Stack-cluster HARD-archive (operator-gated): git-mv the superseded + runbook docs to `completed/`, migrate the audit's 2 orphan-live boxes (`ctx_model_max`, tap/policy-hint) into the SSoT, repoint the ~10 inbound index links
- [x] Surface the SLIDERS reopen precondition (KB-RAG K7 certified 2026-06-13) as a fired-but-needs-operator-decision note ✅ 2026-07-18
- [x] **Publish the current dispatch-inventory baseline ✅ 2026-07-29**: [`BACKLOG-DISPATCH-QUEUE.md`](../../coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md) reports **1,103 unchecked active-handoff tasks at sweep start** and **~232 none-lane, unblocked tasks dispatchable now**. This supersedes the historical `≈544` heuristic; it is an inventory count, not an exact audited live/stale partition. The exact partition remains open below.
- [ ] **NEW 2026-07-29 — Extend the stale-open audit to an exact current live/stale partition, then present a derived dashboard field with audit date and source.** The original 22 audited handoffs now contain 208 open tasks (vs 173 at audit time); current lifecycle parsing identifies only 58 high-precision parked/superseded rows, so neither source can certify the remaining 949-or-fewer tasks as live.
- [ ] Extend the audit to the ~105 un-flagged open handoffs to convert "≤544" into an exact live count
  - **PARTIAL 2026-07-29 (`auditor`) — the exactly-certifiable part is done, and it is small; automated
    exact stale-detection is EXHAUSTED.** Parsed every `- [ ]` box in `handoffs/active/`: **992 raw
    open boxes across 150 files** (the queue's 1082-1103 figures from this morning have burned down
    during the day). Exact, checkable reductions:
    | bucket | n | basis |
    |---|---|---|
    | **NOT A TASK** — reusable checklist or standing constraint | **36** | neither live nor stale; must leave the denominator entirely |
    | STALE — box duplicates a `- [x]` in the SAME file | 0 | exact normalised text match |
    | STALE — box duplicates a `- [x]` in ANOTHER file | 0 | exact normalised text match |
    | STALE — handoff header declares complete/closed/superseded | 1 | `autopilot-authority-autoenable-proposal.md:100` |
    | **UNCERTIFIED-LIVE** | **955** | no automatic signal can certify these |
  - **The load-bearing negative result:** stale rows do NOT restate their completed twin verbatim, so
    exact-text duplicate detection yields **zero**. That independently corroborates this task's own
    premise ("lifecycle parsing identifies only 58 high-precision parked/superseded rows") and means
    the residual 955 cannot be certified by any cheap automatic rule — certification requires READING
    each box against its handoff's prose. Recorded so nobody re-attempts the automated route.
  - **The category this task did not anticipate:** 36 boxes are neither live nor stale because they
    are not tasks at all — reusable checklists (`Update Checklist For Any …`, `Pickup Checklist`,
    `Reopen Checklist`, `Rules For New Tests`) and standing constraints under task-shaped headings.
    They were being served as dispatchable work and two were actually flipped. Excluding them is an
    exact, defensible reduction to the denominator, not an estimate.
  - **Derived dashboard field, ready to wire:** `backlog_live_uncertified = 955`,
    `backlog_not_a_task = 36`, `audit_date = 2026-07-29`, `audit_source = auditor / exact parse of
    handoffs/active`, `certification_method = none available automatically — requires read-through`.
    Reproduce with `scripts/coordination/backlog_row_check.py` per row.
  - **READ-CERTIFIED 2026-07-29 (mainB, 2 rows):**
    `agent-collab-rnd-harness.md` has two optional spikes, neither a current
    live task: the orx/OpenCode vehicle is explicitly gated on operator
    interest, and the OpenHyra adapter additionally requires an external
    container plus an unsandboxed opt-in. Both remain valid future work but
    are **gated**, not dispatchable (and E5 separately prohibits their local
    llama workload). `backlog_live_uncertified = 953` for this dated
    read-through slice; `backlog_not_a_task = 36` is unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 1 row):**
    `autopilot-authority-autoenable-proposal.md` is explicitly superseded by
    consolidated apply-time ratification. Its sole box is an archive
    disposition that waits for operator acknowledgement; it is
    **operator-gated**, not live engineering work. `backlog_live_uncertified
    = 952` for this dated read-through slice; `backlog_not_a_task = 36` is
    unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 2 rows):**
    `autopilot-control-plane-integration.md` remains actively owned/dirty;
    its AP-3 restart-scoped spec-decode/KV work requires quality-cleared
    composed configurations and a sequential reload. The residual source-proof
    subtask is part of that same restart policy. Both are **campaign-gated**
    (and prohibited during E5), not dispatchable. `backlog_live_uncertified =
    950` for this dated read-through slice; `backlog_not_a_task = 36` is
    unchanged. No owner handoff was edited.
  - **READ-CERTIFIED 2026-07-29 (mainB, 8 rows):**
    `autopilot-dashboard-fidelity-audit-2026-07-22.md` has eight clearly
    non-dispatchable boxes: two server/process-owner fixes, an E8 campaign
    counter reconciliation, a human-amendment era-row commit, the
    inference-owned cold-guard, two deferred stretch panels, and the deferred
    grouped provenance/attribution surfaces. These are **owned, E8/E5-gated,
    human-only, or deferred**, not current independent work. The separate hub
    percentage-presentation box remains unclassified for its owner.
    `backlog_live_uncertified = 942` for this dated read-through slice;
    `backlog_not_a_task = 36` is unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 7 rows):**
    `autopilot-sequential-allocation.md` has seven non-dispatchable decision
    or campaign gates: the SEQ-A/SEQ-B policy changes and their explicit
    operator decisions are measurement-trust-boundary work; SEQ-3 requires
    either that ruling or an E8 clean re-run, which itself waits for the
    fail-closed E8 rebaseline. These are **human-only or E8-gated**, not
    current independent work. The deterministic SEQ-4 re-examination and two
    summary-pointer boxes remain unclassified. `backlog_live_uncertified =
    935` for this dated read-through slice; `backlog_not_a_task = 36` is
    unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 4 rows):**
    `batched-edit-parallel-apply.md` has no current independent dispatch:
    BEP-2 is inference-gated, BEP-3 is conditional on its result, BEP-5 is a
    safety-gated general-autonomy design, and the residual LM-repair lane is
    explicitly inference-gated. `backlog_live_uncertified = 931` for this
    dated read-through slice; `backlog_not_a_task = 36` is unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 2 rows):**
    `bep-dcp-falsification-harness.md` is actively dirty under another owner.
    Its two remaining rows are a host-quiet deploy-attestation-plus-inference
    gate and optional J8 provenance. Both are **inference-gated**, not current
    E5-safe dispatch. `backlog_live_uncertified = 929` for this dated
    read-through slice; `backlog_not_a_task = 36` is unchanged. No owner
    handoff was edited.
  - **READ-CERTIFIED 2026-07-29 (mainB, 2 rows):**
    `capability-registry-and-promotion.md` leaves W3/W4 behind the
    evidence-plane ledger, shadow attestation, and a monthly promotion pass.
    Both are **evidence-gated**, not current independent work.
    `backlog_live_uncertified = 927` for this dated read-through slice;
    `backlog_not_a_task = 36` is unchanged.
  - **READ-CERTIFIED 2026-07-29 (mainB, 1 row):**
    `colbert-reranker-web-research.md` is dirty under another owner, but its
    primary S5 request-path reranker row is **prose-closed** by the
    representative 55-synthesized-page `<10%` irrelevant-page NO-GO. It is a
    stale checkbox, not live work; the owner file was intentionally untouched.
    `backlog_live_uncertified = 926` for this dated read-through slice;
    `backlog_not_a_task = 36` is unchanged.
  - **TRANCHE 1 READ-CERTIFIED 2026-07-29 (`auditor`) — 19 boxes, the single-open-box handoffs.**
    Read each box with its section, `Status:` header and following context. Result:
    | verdict | n | meaning |
    |---|---|---|
    | **LIVE** | 9 | genuine outstanding work (PC-4, W8b, W3 fine-tunes, `real_suite_v1`, MoE B-sweep, RD-12, TM-8, W4 consumer migration, post-soak cleanup) |
    | **PARKED — explicit reopen trigger, not fired** | 6 | `mi210-mfma:47` *reopen only if a new compute-bound path appears*; `numa-prefill-decode:76` *reopen on multi-tenant shift*; `yarn-context-extension:105` *reactivate when …*; `security-review-skill:60` *intentionally deferred*; `model-capability-descriptors:40` *GATED tail, IF ever opened*; `gpu-cot-scaffold-sidecar:21` *only if a deployment decision is proposed* |
    | **OPERATOR / HUMAN-OWNED** | 2 | both are *"archive after operator acknowledgement"* rows |
    | **STALE BY OBSOLESCENCE** | 1 | `mi210-speed-campaign-summary:70` — *"run KernelBench over current v6 production kernel"*; v6 is two generations stale (v8 is production), so the task as written names a target that no longer exists |
    | **STANDING ACTIVITY** | 1 | `x-mas-text-routing:51` — *"monitor post-enable live telemetry"*; ongoing, not completable |
    **Two categories the audit did not enumerate, both found here:** *stale by obsolescence* (the task
    still stands but names a superseded target — it is neither done nor doable as written) and
    *parked with a named reopen trigger* (dormant by design; counting it as backlog overstates the
    live queue).
    **SAMPLING BIAS, stated because it would otherwise mislead:** 10 of 19 in this tranche are not
    live work, but single-open-box handoffs are **structurally biased toward residue** — a handoff
    with exactly one box left is usually a finished one carrying a parked tail. **Do NOT extrapolate
    ~50% to the remaining 936.** The rate must be re-measured on multi-box handoffs before it means
    anything fleet-wide.
  - **TRANCHE 2 READ-CERTIFIED 2026-07-29 (`auditor`) — 45 boxes, STRATIFIED multi-box sample**
    (one median-size file from each of the 2-3 / 4-8 / 9-20 / 21+ buckets:
    `objective-task-rate-goodput` 2, `integration-test-coverage` 5, `hermes-agent-index` 11,
    `gpu-serving-tie-in-program` 27). Per-box verdicts recorded in the commit.
    | verdict | n | % |
    |---|---|---|
    | **LIVE NOW** | 13 | 29% |
    | PHASE — real work, later phase of an active program | 7 | 16% |
    | **DUP-INDEX — already counted in its owning handoff** | 6 | 13% |
    | GATED-DEP — blocked on a named dependency | 6 | 13% |
    | NOT-A-TASK — standing policy | 5 | 11% |
    | GATED-OP — waiting on an operator | 5 | 11% |
    | GATED / PARKED | 3 | 7% |
    **MY PREDICTED BIAS WAS WRONG, IN DIRECTION.** I said single-box handoffs were biased toward
    residue and warned against extrapolating tranche 1's low live-rate. The stratified multi-box
    sample came back **lower still — 29% live vs tranche 1's 47%.** The reason is visible once read:
    large handoffs are *program plans*, not task lists. `gpu-serving-tie-in-program` alone carries 27
    boxes of which most are later-phase or operator-gated. So the caution was right but the arrow
    pointed the wrong way, and I am recording that rather than quietly dropping the earlier warning.
    **THIRD NEW CATEGORY: DUP-INDEX.** 6 of 45 (13%) are index-pointer rows duplicating the owning
    handoff's row (`hermes-agent-index:99/101/107/108/109/111`). The collision map names several as
    C2 duplicates; this confirms they **inflate the open-box total**, since both copies count.
    **Combined: 64 of 982 boxes certified (6.5%), 22 LIVE (34%).** Both strata independently land
    near one-third live, which is the first evidence that the ~1/3 figure may be robust — but 6.5%
    coverage is not a basis for a fleet number, and it should not be quoted as one yet.
  - **TRANCHE 3 — the "cheap exact reduction" I recommended DOES NOT EXIST. Third negative of the
    same shape.** ✅ measured 2026-07-29 (`auditor`). I proposed de-duplicating index-pointer rows as
    a mechanical reduction needing no reading. Measured across all 8 index files (65 open boxes):
    * **exact-text cross-file duplicates: 0.** Index rows *summarise* their owner's row in different
      words, so the same text-matching that failed for staleness fails for duplication.
    * **12 rows explicitly name an owner file.** Checking each against its owner: only the ID-level
      test ("every id named in the index row is `[x]` in the owner, none still open") is suggestive,
      and it yields **2 candidates**, of which **1 is confirmed stale by reading**:
      `cpu-inference-optimization-index.md:120` tracks *"B1-B5 in a quiet window"* while
      `iqk-iquant-enablement.md` has B1–B5 all `- [x]` (2026-07-25/26) and Status **"PROMOTED AND
      FROZEN IN v8"**. **That is a genuine already-done-but-open row — the category the audit wanted
      and could not find.**
    * **The signal I thought was strongest is WRONG.** "Index row names an owner with zero open
      boxes" looked decisive; `research-evaluation-index.md:84` disproves it — its owner
      `frontier-f1-real-task-corpus.md` has 0 open boxes but Status **IN PROGRESS**, because that
      handoff tracks in prose. Owner-has-no-boxes means *"the owner does not use checkboxes"* at
      least as often as it means *"the work is done"*. Recorded because acting on it would have
      wrongly closed live work.
    **CONCLUSION FOR THE AUDIT: every cheap mechanical route has now been tried and failed** — exact
    text staleness (0), cross-file duplication (0), index-pointer de-duplication (~1 confirmed of
    65). Reading is the only route, and its rate is now measured. Stop looking for a shortcut.
  - [ ] **REMAINS OPEN:** read-certify the remaining ~918. That is the only route left and it is a bounded but
    large job; it should be split across mains by handoff, not attempted in one session.
    - [x] **Tranche 3 — the 6 orphan handoffs, complete: 18 of 18 boxes certified, 0 DEAD ✅ 2026-07-29 (`auditor`)**
      (`agent-collab-rnd-harness`, `autopilot-authority-autoenable-proposal`, `core-v2-design-note-2026-07-23`,
      `qwen-mtp-llamacpp-port`, `re4-protocol-redesign`, `stale-open-audit-2026-07-18`).
      **The result falsifies the premise I picked them on.** I chose the orphans expecting a high stale
      rate — linked from no index, so nothing finds them by navigation and nothing has been pruning them.
      Not one row is dead. Every one is live and *gated*: 4 on an operator decision, 6 on an inference
      window, 2 on a predecessor row, the rest on a named owner. **Orphan status is not staleness**; it is
      an indexing defect with a different fix — link these from an index rather than audit them for rot.
      Prior tranches for comparison: T1 47% live (n=19), T2 29% (n=45), T3 **100%** (n=18).
    - [x] **`re4-protocol-redesign.md:151` sharpened rather than closed ✅ 2026-07-29** — the row asks to verify
      the RE-4 runner has (a) incremental per-question persistence and (b) confidence capture with
      `confidence_is_real` provenance. Verified against
      `epyc-inference-research/scripts/benchmark/longcot_mini_stack_runner.py`: **(a) is already satisfied** —
      `_write_role_result` (:452) is called per question inside the loop at :560, writes atomically via
      tmp+replace, and :521 resumes from persisted rows. **(b) is genuinely unmet** — `confidence` appears
      nowhere in the file (the sole `conf` hit is `config_name` at :469; checked a second spelling before
      concluding absence). So the row stays open but is now scoped to (b) alone. Not patched here: RE-4 is
      the CPU lineage's, and that runner is measurement-instrument code.

> All verdicts above are **observations** for backlog-hygiene decisions, not measurement-gating numbers. No production kernel, registry, or handoff checkbox was modified by this audit.
