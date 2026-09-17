# EPYC Handoff — Master Index

**Purpose**: **routing only.** Find your domain index, then your row. This file owns no backlog rows —
it is the cheapest hop, so it stays short. Work lives in the domain indices; history lives in `progress/`
and `handoffs/completed|archived/`.

> **Live campaign state** (autopilot posture, freeze status, active lanes):
> [`CURRENT-CAMPAIGN.md`](CURRENT-CAMPAIGN.md) — read it before starting anything that touches the
> production stack.

## Domain indices

| Domain | Index | Scope |
|--------|-------|-------|
| Inference research | [inference-research-index.md](inference-research-index.md) | Kernels, quantization, serving performance, models (CPU **and** GPU) |
| Routing / autopilot / stack | [routing-and-optimization-index.md](routing-and-optimization-index.md) | Orchestrator, registry, stack lifecycle, autopilot, fleet coordination |
| Research & evaluation | [research-evaluation-index.md](research-evaluation-index.md) | Benchmarks, scorers, audits, research programs |
| User-facing harness | [user-facing-harness-index.md](user-facing-harness-index.md) | REPL/UX, prompting, memory, output compression (surface, not an implementation commitment) |
| Pipelines & integration | [pipeline-integration-index.md](pipeline-integration-index.md) | Ingestion, document/RAG pipelines, knowledge base |
| Reviewer control plane | [reviewer-control-plane-index.md](reviewer-control-plane-index.md) | Reviewer roles, capability gates, control-plane policy |

**Exactly one index owns each handoff.** A handoff listed twice is a defect — `index_state.py --check`
fails on it. Cross-domain relevance is a `Deps` edge, never a second row.

## Operator decision queue

Decisions only the operator can make. **This is the one hand-maintained list in this file** — it exists
because a form-screen cannot detect "needs a human choice", and a decision buried in a handoff body gets
missed (measured: G9-disk sat unnoticed for two weeks and governed 227 GB).

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-1 | P0.1–P0.3 sign-off bundle | [orchestration-robustness-audit-2026-07-11.md](orchestration-robustness-audit-2026-07-11.md) | 2026-07-11 |
| OP-5 | Reviewer control-plane decision bundle (P-REV-1 amendment) | [reviewer-control-plane-index.md](reviewer-control-plane-index.md) | 2026-07-16 |
| OP-6 | Consolidated quiet window — reviewer-plane baselines on the v8 reference lineup | [reviewer-control-plane-index.md](reviewer-control-plane-index.md) | 2026-07-17 |
| OP-26 | ParEval CPU/HIP trials — flagged tier-1 at Hawkeye Stage-2b close but never reached the approved plan: run, file, or decline | [research-intake session record, `git show c927e943:.research-session.json`] | 2026-08-21 |
| OP-27 | ~20 unselected Stage-2b sources from the Hawkeye batch — QiMeng-Xpiler `2505.02146` highest-value (only AMD/HIP-touching artifact in the line): select dives or decline | [research-intake session record, `git show c927e943:.research-session.json`] | 2026-08-21 |
| OP-33 | Disk reclaim: minimal set + GLM-5.2 + the 22-artifact zero-consumer purge all EXECUTED (743 G free). REMAINING: 7 ambiguous artifacts (~128 G) needing a call — chiefly a 70 G Qwen3.5-122B copy the lean registry calls PRODUCTION while the served path points elsewhere (a registry defect, not a disk question); plus the 4 rollback-anchor holds. `opencode.db` **RESOLVED 2026-09-07: 236.1 GB → 11.4 GB** (event change-feed pruned to 7-day retention, content tables untouched, `quick_check` ok, +225 GB reclaimed) | [2026-08-31-disk-reclaim-menu.md](../../progress/2026-08/2026-08-31-disk-reclaim-menu.md) §EXECUTED | 2026-08-31 |
| OP-42 | Admit BEAM 128K and Tulving 200ch/100K as M-12's instruments and grant one inference window: M-12a (Tulving) first, M-12b (BEAM) second. Eval-pool registration is a separate decision from adoption as an instrument (CJ-GATE precedent; MEASUREMENT.md is human-amendment-only) | [episodic-memory-integrity.md](episodic-memory-integrity.md) M-12 | 2026-09-07 |
| OP-38 | **P-KLD divergence protocol** — we have NO ratified KLD/PPL/coherence protocol (`MEASUREMENT.md` §2 has zero divergence terms) while two campaigns now quote divergence numbers. Distilled annex ready: full-vocab only, fp64 sums, declared estimand, bootstrap by document cluster, no universal bands, fail-closed runner + receipts, and a route-pinned cell before attributing KLD to the codec on a MoE. **Human-amendment-only trust boundary → needs an operator-run `ratify_*.sh`, not a session edit** | [autokernel-rebuild-program.md](autokernel-rebuild-program.md) → R23-47 | 2026-09-07 |
| OP-41 | **CPU co-tenancy: serialize or regress.** RULED 2026-09-08: operator owns admission-control design/implementation after champion finalised → promotion → host reboot. Clarify whether the new implementation instruction delegates broker-code work now; live activation gates remain unchanged. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → §3.4, AKU-11 | 2026-09-08 |
| OP-AKU-HELD | Approve the additional versioned provider-held-cost lifecycle event and replay/settlement recovery (HIGH: 22 upstream, three processes). Descendant-event approval is already granted but does not include this addition; no live grant or measurement-policy change. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → AKU-07j | 2026-09-09 |
| OP-AKU-BIND | Approve versioned selected-work binding and source/build multi-child accounting: original receipts, typed admission denial/cancellation and atomic one-attempt settlement (HIGH: 22 upstream; Journal validation HIGH20). Paired HELD approval covers original durable costs. No live grants, policy amendment or production changes. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → AKU-07k/06l; [decision package](../../docs/design/autokernel-source-build-accounting-v2-proposal.md) | 2026-09-09 |
| OP-AKU-STACK | Approve canonical generated-stack repair in the isolated orchestrator lane (HIGH: 66 upstream): lean registry, descriptors, priors, procedure enums and summary; preserve split-instance mode. No compiler edits, service reload or production-kernel change. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → AKU-12c | 2026-09-09 |
| OP-AKU-PROMPT | Approve frozen-prompt v2 with explicit seed and token-output request, preserving v1 exactly (HIGH: 18–22 upstream serialization consumers). Needed for same-server determinism/token evidence; no live execution or policy change. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → AKU-07o/07r | 2026-09-09 |
| OP-AKU-CONTROLS | Choose whether to prepare a narrowly scoped control-only bootstrap policy for ratification, or require an existing qualified same-frame panel. No provisional PASS, candidate ranking or promotion authority is granted by this request; raw preparation and discovery continue. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → AKU-07x | 2026-09-09 |
| OP-AKU-ENROLL | Approve versioned original build-enrollment INTENT/ACTIVATED recovery through Journal native payload validation (HIGH: 20 upstream, three processes). Needed for durable candidate/expiry authority; no deletion, production mutation or live grant. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → AKU-10i | 2026-09-09 |
| OP-AKU-A2 | Approve versioned native A2 intent/one-shot permit/diagnostic terminal semantics (HIGH: transition validator, 17 upstream). Preserves legacy events and forbids replayed intent from authorizing relaunch; no measurement-policy change or fabricated witness passes. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → AKU-04f | 2026-09-09 |
| OP-AKU-REFRESH | Approve explicit versioned profile-request and PROFILE_VERIFIED successor records with original predecessor/settlement joins (HIGH: actor event validator, 16 upstream). Required for autonomous profile renewal; preserves legacy refusal, original validity, production freeze and measurement policy. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → AKU-06i | 2026-09-09 |
| OP-AKU-U3 | Select the variance-only RUNTIME_CONFIG keep rule: recommend log downside-semideviation ratio, paired-bootstrap one-sided 95% upper bound <0, n≥14/arm, with throughput LCB above −session floor; or name another estimand/test/N/mean guard. This is scientific admission authority, not implementation detail. | [autokernel-unified-surface-program.md](autokernel-unified-surface-program.md) → U3-SEED, S3-AKU-04 | 2026-09-15 |
| OP-12 | Approve or decline one experimental commit for the one-file IQ2_XXS one-row VPOPCNT dispatch; screening A/B is +5.733% at n=1 and parity at n=512 | [mi210-q8-dequant-gemv-roofline.md](mi210-q8-dequant-gemv-roofline.md) INF-37 | 2026-08-11 |
| OP-13 | Ratify a P2-5j placement amendment or require a full P-BENCH-PLACEMENT-1 composite; the old four-arm design is observation-only | [gpu-serving-tie-in-program.md](gpu-serving-tie-in-program.md) P2-5j | 2026-08-11 |
| OP-15 | Approve or decline one experimental commit for the Q4_K branchless scale/min decoder before a clean governed replay | [mi210-q8-dequant-gemv-roofline.md](mi210-q8-dequant-gemv-roofline.md) INF-37 | 2026-08-11 |
| OP-17 | Amend frozen-v9 attestation with llama ggml `0.16.0`, or retain an intentionally unverified complete-kernel-set fold | [autokernel-research-loop.md](autokernel-research-loop.md) AK6 dashboard residual | 2026-08-12 |
| OP-25 | After C5-3 produces a live gfx90a correctness run, choose whether to leave SOL scoring disabled or port measured gfx90a constants for k215 only. Recommendation: k215-only if scoring is needed; never present the four >100×-headroom seeds as speed-of-light objectives | [agentic-rocm-kernel-authoring.md](agentic-rocm-kernel-authoring.md) C5 | 2026-08-16 |
| OP-29 | Scope decision: is video generation a product need? Gates the 165 GB MiniMax-H3 Ref2VA + 10Eros-Max download (volume at 92%, 291 GB free) | [minimax-h3-video-generation-evaluation.md](minimax-h3-video-generation-evaluation.md) EVL-32 | 2026-08-30 |

Full text for OP-1..OP-6 (including the closed OP-2 and the superseded narration) is preserved in
[`../archived/master-handoff-index-history-through-2026-08-10.md`](../archived/master-handoff-index-history-through-2026-08-10.md).
OP-3 and OP-19 (resolved) are preserved in
[`../archived/master-handoff-index-history-through-2026-09-14.md`](../archived/master-handoff-index-history-through-2026-09-14.md).

## Standing contracts

`/workspace/MEASUREMENT.md` (adopted) · `instrument_eras.yaml` (epyc-orchestrator `orchestration/`) ·
current architecture review: [fable5-findings-00-executive-summary.md](../completed/fable5-findings-00-executive-summary.md)
(COMPLETE 2026-06-12 — standing reference, not an open row) ·
cross-domain governance: [stale-open-audit-2026-07-18.md](stale-open-audit-2026-07-18.md).

## Backlog state (generated)

Regenerate with `python3 scripts/handoffs/index_state.py`. Per-handoff detail — open/closed counts,
`last_advanced`, blocked/guarded — lives in `handoffs/active/.index-state.json`.

**`last_advanced` is the date a checkbox last changed**, not the file mtime and not the last commit:
prose edits and typo fixes are not progress. A domain whose oldest advance is months back has handoffs
nobody is moving.

<!-- BEGIN GENERATED index_state -->
| Domain | Handoffs | Open | Blocked | Oldest advance |
|--------|----------|------|---------|----------------|
| inference-research | 57 | 760 | 15 | 2026-07-29 |
| pipeline-integration | 5 | 70 | 1 | 2026-07-29 |
| research-evaluation | 43 | 429 | 10 | 2026-07-29 |
| reviewer-control-plane | 6 | 27 | 12 | 2026-07-29 |
| routing-and-optimization | 49 | 479 | 18 | 2026-07-29 |
| user-facing-harness | 7 | 49 | 2 | 2026-07-29 |
<!-- END GENERATED index_state -->

## Reporting

On completing a row: flip the checkbox in the owning **handoff**, update the row's `Next action` in its
domain index, append to `progress/YYYY-MM/`. Then run `python3 scripts/handoffs/index_state.py` to
refresh generated state and `--check` before committing. Numbers use the claim grammar in
[`MEASUREMENT_POLICY.md`](../../agents/shared/MEASUREMENT_POLICY.md).

Row contract (what may and may not go in a row):
[`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).
