# Checkbox-flip evidence audit — 2026-07-29

**Scope**: every checkbox state change committed to `main` on 2026-07-29 (UTC) across
`epyc-root`, `epyc-orchestrator`, `epyc-inference-research`.
**Method**: mechanical diff extraction (`git show --unified=0 --diff-filter=M -- '*.md'`) over all
247 commits since `2026-07-29T00:00:00Z`, paired old/new checkbox lines by normalised task text,
then per-entry citation resolution against the filesystem and all four git repos (including
`/mnt/raid0/llm/llama.cpp`).
**Posture**: read-only. Nothing was edited, unflipped, or committed. This file is the only output.

---

## 1. Summary

| Metric | Count |
|---|---|
| Commits scanned (3 repos, since 00:00Z) | 247 |
| Commits containing checkbox state changes | 125 |
| Handoff/doc files touched | 57 |
| **Total checkbox events** | **221** |
| — `[ ]` → `[x]` (flips) | 92 |
| — line **added already `[x]`** (new-checked) | 104 |
| — `[x]` → `[ ]` (unflips) | 25 |
| **Total closures (flips + new-checked)** | **196** |
| Closures in documentation-only commits (no code/test/data files) | 146 |
| Closures in commits also carrying code/tests/data | 50 |
| | |
| **Closures classified INFERENCE-GATED** | **18** |
| — with a verified evidence trail | 17 |
| — **without** a verified evidence trail (SUSPECT) | **1** |
| **Closures classified UNCERTAIN** | **6** |
| **Closures classified NOT inference-gated** | **172** |
| | |
| Closures whose cited paths/commits **all resolve** | 196 / 196 |
| Closures with a citation to a **nonexistent** path or SHA | **0** |

**Repo distribution**: all 221 events are in `epyc-root`. `epyc-orchestrator` (56 commits today)
and `epyc-inference-research` (19 commits) changed no checkbox lines in modified Markdown — they
carry the code/artifact side of the work only. Handoff bookkeeping is centralised in `epyc-root`.

**Headline**: citation hygiene today was unusually good. Every path, run directory, artifact
namespace and commit SHA cited in a closure annotation was resolved and **exists on disk**. There
were zero dangling-citation rug-sweeps. One inference-gated closure is nonetheless unsupported —
see SUSPECT S1.

---

## 2. The exclusive-window timeline (established from the session bus, not assumed)

Reconstructed from `coordination/session-bus/{outbox/*.jsonl,advisory.jsonl,adapter-ledger.jsonl}`:

| Time (UTC) | Event |
|---|---|
| ~06:00–10:18 | Pre-reboot freeze. `mainB` reports "no stack/API reload, no inference, no region claim" honoured. `auditor` repeatedly nudged "no inference, no region claim". |
| 10:18 | `inference` (Codex) advisory: `working\|p0-2-fg4b-exclusive-run → idle`. Token request `RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729` filed. |
| 10:59 | Ratification artifact written: `artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729T105911Z.json`. |
| 11:01–11:49 | **FG-4b run executes** under that ratification (`fg4b-a4-cpu-optimized-server-20260729T110152Z`). |
| ~11:24 | Final-C1 capacityfix generation namespace written. |
| ~13:00–14:00 | Operator host reboot. |
| **15:20** | Operator decision relayed: *"E5 gets the host EXCLUSIVELY and runs to completion, W1–W4, in one campaign."* |
| **15:25** | Coordinator to `mainA`: *"THE HOST IS YOURS. START E5 STAGE-B NOW."* |
| 15:45 | Coordinator to `inference`: relaxes the lane but confirms *"actually_forbidden_during_e5: any llama-fam…"*. |
| 15:47–18:45 | **E5 Stage-B exclusive window.** W1 → W4 → W2 run contiguously. |
| 18:45 | Last E5 run (`e5-w2-gemma-…`) completes. |

**Consequence for this audit**: the fleet-wide inference prohibition ran **15:20 → ~18:45Z**, and
`mainA` was the only session entitled to run inside it. Work in the morning block was under a
*reload/stack* freeze, not an absolute inference ban — `inference` held its own operator-ratified
FG-4b window at 11:01. Both regimes are respected in the classification below.

---

## 3. SUSPECT — inference-gated closures lacking a verified evidence trail

### S1 — RE-4 LongCoT-Mini calibration protocol closed while its owner is still open

- **File:line**: `handoffs/active/research-evaluation-index.md:83`
- **Commit**: `3d509613` · 2026-07-29T15:19:57Z · *"bus(C24): name the real containment invariant and pin it as a test"*
- **Event kind**: `NEW_CHECKED` — the line was **added already checked**, not flipped.
- **Task text (as committed)**:
  > `- [x] RE-4 LongCoT-Mini calibration protocol, intake-386 (execution owner: inference-batch-loop.md; design: re4-protocol-redesign.md, M) — runner v2 and entry v2 landed 2026-07-21; a v8-topology re-attestation is required before the operator quiet-window probe. The earlier bulk-campaign ownership and v7 premise are historical. ✅ 2026-07-29`

**What is missing, precisely:**

1. **The annotation contradicts itself.** The row is marked `[x] ✅ 2026-07-29` while its own text
   states *"a v8-topology re-attestation **is required** before the operator quiet-window probe."*
   The completion date is today; the stated remaining work is not dated, scoped out, or delegated.
2. **The owner handoff still carries the task open.** `handoffs/active/inference-batch-loop.md:198`
   reads `- [ ] **RE-4 protocol repair** — redesign LongCoT-Mini execution so models may do bounded
   reasoning while deterministic final-answer extraction still works.` It is unchecked at HEAD.
3. **The design note explicitly forbids the execution.**
   `handoffs/active/re4-protocol-redesign.md` header: *"**Status:** ACTIVE/GATED — runner v2 and
   entry v2 landed 2026-07-21; **no inference is authorized by this design note**"* and
   *"re-attest current v8 topology before the quiet-window probe"*.
4. **The prior state is a recorded failure, not a success.** `inference-batch-loop.md:28` records
   the *"RE-4 terminal blocker (2026-07-21T03:25Z; **no RE-4 flip**)"* — the optimized v7
   quarter-stack rerun floor-saturated (frontdoor 0/402, worker_general 0/307). Partial scores are
   at `coordination/inference-batch/bundles/RE-4/partial_*_score_20260721T013833Z.*`.
5. **No run id, artifact path, or attestation is cited** for anything dated 2026-07-29.
6. **Ride-along**: the commit's subject and body are entirely about `tmux_adapter.py` C24
   containment. The commit's code payload is `scripts/coordination/tmux_adapter.py` +
   `tests/test_tmux_adapter.py`; the RE-4 line arrived alongside checkbox changes in **10 unrelated
   handoff files**. This is the staged-file ride-along pattern, not a deliberate RE-4 closure.

**Contrast with the correct handling of the same situation**: at `5c10b466` the `auditor` closed
two structurally identical index pointers and *wrote out the verification* — naming the owner file,
quoting each owning box's state and date, and stating the pointer never followed. See CLEAN below.
No equivalent verification exists for RE-4, and the owner's state is the opposite (open).

**Not an accusation**: RE-4's index row may legitimately be closable as "ownership re-pointed, not
work-complete". But as committed it reads as a completed inference-gated calibration protocol, and
nothing on disk or in the owner supports that reading.

---

## 4. Citation-hygiene notes (inference-gated, evidence found — but not by the annotation)

These are **not** suspects. In each case I located corroborating evidence, but the annotation itself
does not cite a path, so a reviewer cannot verify it without independent search.

### N1 — M-17j semantic health live checkpoint
- `handoffs/active/episodic-memory-integrity.md` · commit `33cc30bb` · 07:26Z (pre-window)
- Claims measured numbers with no artifact path: `ntotal=58749`, `id_map=58749`, `desync=0`,
  round-trip 500/500, **mean cosine 0.9824 over 8 samples**, plus *"An API-only reload activated the
  guards."*
- **Measured by me**: cited commits resolve — orchestrator `93d8349b` (2026-07-29T07:04:25Z,
  *fix(memory): require semantic integrity and exact Q updates*) and `ec087da1` (07:09:01Z). The
  store exists: `orchestration/repl_memory/sessions/{embeddings.faiss,id_map.npy}`, `id_map.npy`
  length **58843** at audit time (grew from the claimed 58749; consistent, not contradictory).
- **Gap**: the cosine/round-trip figures are not persisted to any cited artifact. They are
  reproducible only by re-running the health check — which is itself an embedding-service call.

### N2 — G3-3 deterministic saved-output replay
- `handoffs/active/gpu-cot-scaffold-sidecar.md` · commit `33cc30bb` · 07:26Z (pre-window)
- Claims per-arm scores (receiver-nothink `25/48`, Qwable standalone `40/48`, Qwable-prefix `42/48`,
  FF-prefix `41/48`, TC-prefix `43/48`) with **zero mismatches** on frozen-scorer replay, and no
  cited run directory on the closing line.
- **Measured by me**: the saved-output corpus is cited one entry up in the same file (G3-3a,
  ✅ 2026-07-28) at `/mnt/raid0/llm/tmp/cot-g1/g3_20260728/runs/g3-gpqa-20260728T070247Z-manual2/`
  — **exists on disk**. The replay is therefore a deterministic rescoring of saved outputs, which is
  the *preferred* route under MEASUREMENT_POLICY → *Deterministic replay before regeneration*.
- The closure correctly leaves `- [ ] G3-4 — future decision instrument` open and states *"No
  deployment, lineup, registry, or generator-selection rule changes."* Well-disciplined.

### N3 — core-v2 activation group, dated to a prior day
- `handoffs/active/core-v2-design-note-2026-07-23.md:157,161,185,188,192,193` · commit `3d509613`
- Six boxes closed, four of them inference-adjacent (**"Launch autopilot"**, **"Restart"**,
  **"Verify live"**, **"Re-run the validator"**), all annotated **✅ 2026-07-23** — i.e. the
  legitimate stale-open-close pattern, claiming work done six days ago, *not* today.
- **Measured by me**: corroborated. `epyc-orchestrator/orchestration/instrument_eras.yaml:125-133`
  carries the era row with `core_id: "core_v2"`, `policy_version: "core_v2_designed_e7_v1"`, and
  `dataset_content_sha256=88d7a59c…b639ca` — exactly what "Append the quality/core era row" and
  "Re-run the validator" would produce.
- **Gap**: no trial id or `eval_details` record is cited for "Verify live", and these six boxes rode
  into the same unrelated C24 commit as S1.

---

## 5. UNCERTAIN

Six closures where I could not decide from the text alone whether execution required a model. Each
is listed with my reasoning rather than a guess.

1. **`64410d3b` — "2b-agentic-1. Pin and verify the tool-call parser before any Jackrong-family bench"**
   (`scoring-infra-standardization.md`). "Verify" could mean *run the model and inspect emitted tool
   calls* (inference) or *pin the wire contract in fixtures* (not). The annotation takes the second
   reading: orchestrator `22c476dd` (verified, 17:52Z) plus separate v2 (6,994 B) / Coder (4,718 B)
   wire-contract fixtures and 134 passing prompt-builder tests. The task text itself says *"before
   any … bench"*, which supports the static reading. **Leaning NOT gated**; flagged because a
   parser "verified" only against recorded fixtures has not been shown to survive live output.

2. **`b5851d43` — "E5 harness: `--reasoning` was never emitted; gemma4 W2 ran with reasoning ON"**
   (`batched-decode-measurement.md`, 15:58Z). This is a *finding about* inference already run (the
   W0 scout), landed as a code fix (research `5d6a17f2`, verified, 15:57:22Z). Whether the finding
   required re-running anything to confirm is not stated; the later W2 capture smoke (18:30Z, inside
   mainA's own window) is what actually demonstrates the fix. **Probably not independently gated.**

3. **`9a22d1a1` — "Phase C decision + update internal-kb-rag / colbert-reranker / searxng handoffs"**
   (`granite-97m-r2-bench-plan.md`, 15:30Z — inside the E5 window). "Phase C" sits inside a
   *bench plan*, which reads gated. But the handoff records the bench as already done: *"The
   2026-07-20 inference-batch run closed the load/vector smoke and Phase B retrieval/latency
   execution"*, and Phase C is defined at line 189 as *"Decision + deployment recommendation
   [post-bench]"*. The closure states *"no existing service is swapped or launched."*
   **Leaning NOT gated** — a decision over 07-20 data.

4. **`5a5d252d` — "Wire missing Prometheus migration counters … **or verify observable evidence**"**
   (`within-role-placement-state-machine.md`). The disjunction is the problem: the first branch is
   code, the second may require a live workload to observe counters incrementing. Closed citing
   orchestrator `03c7a15e` — which resolves but is dated **2026-07-17**, so the work predates today
   entirely. **Leaning NOT gated**, but the "verify observable" branch is not addressed.

5. **`60085686` — "Pre-hardware prep (now). Pin GEAK/GEAK-eval/Apex/AgentKernelArena repos …"**
   (`rocm-verify-profile-backend.md`). GPU/ROCm-adjacent, but the deliverables are repo pins,
   licence inspection, and a drafted environment recipe. The annotation explicitly records *"the
   no-execution activation order"*. **Leaning NOT gated.**

6. **`33cc30bb` — G3-3** (see N2). Sits on the replay-vs-regeneration boundary. Under the
   deterministic-replay rule it is *correctly* not-gated; under a stricter reading, "0 mismatches
   across 5×48 saved outputs" is a scoring claim. Listed here for completeness; evidence located.

---

## 6. CLEAN — inference-gated closures with a verified evidence trail (17)

Summarised, not enumerated line-by-line.

**A. Executed inside a legitimately held window (6 closures, all artifacts verified on disk)**

| Closure | Commit / time | Verified evidence |
|---|---|---|
| **E5 Stage-B COMPLETE** — 31 cells, 3 model groups, 26/31 decision-grade | `a88a356a` 18:58 (`mainA`) | All three run dirs exist under `epyc-inference-research/data/batched_decode/`: `e5-w1-qwen36-20260729T154725Z` (mtime 16:56), `e5-w4-80b-20260729T165639Z` (18:30), `e5-w2-gemma-20260729T183151Z` (18:45) — each with `cells.jsonl`, `events.jsonl`, `manifest.json`, `affinity/`, `logs/`. Timestamps fall inside mainA's 15:25–18:45 exclusive grant. |
| **W2 capture smoke PASSED** | `b9bef3fc` 18:34 (`mainA`) | `e5-w2-capture-smoke-20260729T183019Z/` exists with `capture_smoke_verdict.json` (723 B), mtime 18:31 — matching the claimed run id to the minute. |
| **FG-4b canonical A4 re-anchor** (`architect-model-selection-bench.md`) | `e428bceb` 11:13 (`inference`) | `epyc-inference-research/artifacts/architect-27b-finetunes-v8-20260726/fg4b-a4-cpu-optimized-server-20260729T110152Z/` exists with `COMPLETE` marker, `evidence.json` (6.4 MB), `content-hashes.json`, three response files. Ratification artifact `artifacts/operator/ratify_pbench4_fg4b_affinity_witness_20260729T105911Z.json` exists (written 10:59, before the 11:01 run). Bus advisory confirms `p0-2-fg4b-exclusive-run`. **Pre-dates the E5 window.** |
| **P0-2 FG-4b** (`gpu-serving-tie-in-program.md`, `13.159866755320987 tok/s` median) | `e428bceb` 11:13 | Same run; same evidence. |
| **Final-C1 capacityfix ordinals collected** | `87fabd80` 13:04 | Namespace `artifacts/operator/e8_quality_baseline_v5_partial_r2_final_c1_capacityfix_20260729T112433Z` exists. Ratifier `ratify_e8_final_c1_retry_capacityfix_20260729.{json,sh}` present. Annotation correctly says *"generated requests only; no final evidence, inference completion, state apply, or publication"*. |
| **M-17j semantic health checkpoint** | `33cc30bb` 07:26 | Commits verified; store verified (see N1). |

**B. Inference-gated tasks closed by a legitimate NON-execution route (11 closures)**

- **`5c10b466` (18:41, `auditor`) — two P0 index pointers, the model close.**
  *"P0 iqk IQ-quant enablement: build + per-model coherence/speed gates B1-B5"* and *"P0 Batched
  decode E2/E3: capture EvalTower telemetry"*. Both closed as **stale index pointers**, with the
  owner state quoted inline. **I verified both owners independently**:
  `iqk-iquant-enablement.md` has B1 ✅2026-07-25 (`b8ad9d292`, resolves in `/mnt/raid0/llm/llama.cpp`),
  B2 ✅2026-07-25 (6-arm/24-task three-model attestation), B3/B4 ✅2026-07-25, B5 ✅2026-07-26
  ("PROMOTED AND FROZEN IN v8"); `batched-decode-measurement.md` has E2 `[x]` twice — including the
  row naming `eval_batch_serving_evaltower_window.py` — and E3 `[x]` NO-GO/CLOSED ✅2026-07-18.
  The underlying work completed 3–11 days before the flip. **Textbook stale-pointer close.**
- **`de491074` (16:28) — TQ3 "Evaluate PR #21089 **when merged**"**: conditional trigger never
  fired. Upstream closed the PR unmerged 2026-06-02 (no `mergedAt`); local tree contains no TBQ
  commit. Annotation states *"No build, benchmark, or runtime action was taken."*
- **`fcbbd8e6` (13:04) — P2-2d whisper**: `RESOLVED-BY-DECISION`, operator chose defer (W3);
  refiled as P2-9.
- **`2c6a1abd` (16:19) + `b5851d43` (15:58) — W3 dense control**: dropped/removed by operator
  decision (*"27b_q8 is scheduled to run residently on the GPU"*). Recorded as a scope change,
  appended not rewritten, consistent with the era/append-only rule.
- **`acb8d7b8` (14:58) ×3 — E5 pre-window readiness, throttle-gate repair, W2 smoke staging**: all
  three annotations self-label **"(zero inference)"**. Cited research commits `98cfff44` (14:50) and
  `c48bcb60` (14:56) both resolve. Filed *before* the 15:20 window opened.
- **`33cc30bb` — G3-3** (see N2).
- **`3d509613` core-v2 group** (see N3), counted here as prior-dated closes.

**C. Explicitly deferred rather than swept — worth noting as counter-evidence**

Several sessions declined to close the measurement half of a task rather than rationalising it:
- `f6d3dba2` — *"audit(P2-5l): close the topology half; **decline the measurement half**"*.
- `ed692da3` — *"K-eval re-scoped … **execution still requires a region claim**"*.
- `ed692da3` — *"P2-5j protocol design … **filed before any inference**"*.
- `2b25c2d6` — *"Write P-GPU-1 measurement protocol **before any GPU runs**"* (writing a protocol,
  ratified into MEASUREMENT.md on 2026-07-19 — not a run).
- `1c02a57b` — HS-3 closed as *"not triggered: HS-2's ROI verdict is LOW"* (conditional task).
- `d8ea6b4c` — *"verify the GEMV re-anchor; **hand it to the owner rather than executing it**"*.

This is the behavioural signature of sessions that understood the constraint.

---

## 7. NOT inference-gated (172) — summary only

The bulk of today's closures are genuinely non-inference:

- **Session-bus / coordination defects (36 closures, `session-bus-thin-dispatcher.md`)** — C9–C36
  are Python fixes to `tmux_adapter.py` / `session_bus_coordinator.py` with pytest coverage. 5 of
  these commits carry the tests in the same commit.
- **Research-intake derived work (~40)** — recording, correcting, or demoting claims from ingested
  papers (`683f70de`, `c942728e` cited repeatedly; both resolve).
- **Harness selection (13, `harness-selection-and-integration.md`)** — literature/decision-matrix
  rows.
- **Static audits and index hygiene (~30)** — stale-pointer closes, era-pin sweeps, dead-code
  removals, `numactl -H` topology reads.
- **Design/decision rows (~25)** — outer-coordinator ROI, DAR triage rescope, reasoning-compression
  taxonomy tiers.
- **Doc/artifact tooling (~15)** — benchmark dashboard (`81e2f3cb`, reads saved artifact JSON only),
  model/artifact inventories, validators.

Notable verified case: **`28d86c0c` "Post-E8 read-only rebuild"** at 18:24Z — *inside* the E5
window. I checked `epyc-orchestrator/scripts/autopilot/core_v2_select.py` for any HTTP/model call
(`requests|httpx|urllib|llama|openai|/v1/|localhost:`) — **none**; it is a pure ledger read. The
cited output `/mnt/raid0/llm/tmp/mainc-core-v2-20260729/{core.jsonl,report.json}` exists (mtime
18:24). Correctly non-inference and correctly performed during the window.

---

## 8. Collateral finding — 25 unflips, and a 794-file deletion

Not part of the brief, but discovered mechanically and material to dashboard truth.

**24 of the 25 `[x]` → `[ ]` events were accidental reverts from stale working trees**, riding into
commits whose subjects are unrelated to the reverted files:

| Commit | Subject | Boxes silently unflipped |
|---|---|---|
| `27fbfce5` 18:50 | *"docs: park Ring-mini as architecture reference"* | **15** boxes across 6 files (`harness-selection`, `gpu-serving-tie-in`, `cpu-shape-specialized-gemv-decode`, `agent-file-prose-compression`, `frontier-f3-data-flywheel`) |
| `81e2f3cb` 17:06 | *"Add read-only benchmark artifact dashboard"* | **9** boxes across 6 files (`tq3-quantization-evaluation`, `colbert-reranker`, `rocm-verify-profile-backend`, `harness-selection`, `intake-derived-work`) |

Each reverted line lost its `✅ 2026-07-29` annotation and the evidence prose written with it. **24
of 25 were re-flipped by a later commit and are `[x]` at HEAD**, so the net dashboard count is
correct — but the work was un-recorded for 30–100 minutes and would have been permanently lost had
the owning session not re-committed.

The one still-unchecked unflip is **deliberate and correct**: `43f601f7` *"fix(handoffs): preserve
recurring pickup checklist semantics"* reopened *"Check llama.cpp upstream for any new CPU ukernel
PRs"* — a recurring checklist item that must stay open.

Related: commit `24b06884` (17:29, *"docs: record tinyBLAS tile pattern review"*) touched **794
files**, deleting large parts of the tree including `handoffs/active/core-v2-design-note-2026-07-23.md`;
`2053b758` (17:30, *"fix: restore full tree after malformed isolated index"*) restored it one minute
later. This is the same stale-index/ride-along failure mode.

---

## 9. Coverage statement

**Fully covered**: all 221 checkbox events, all 125 checkbox-bearing commits, all 57 files, across
all three repos, for the full UTC day. Every event was read individually — no sampling.

**Verification depth**: every absolute path, repo-relative path, and 7–40 char git SHA appearing
inside a closure annotation was resolved programmatically against the filesystem and against
`epyc-root`, `epyc-orchestrator`, `epyc-inference-research`, and `llama.cpp`. 196/196 resolved.

**Limits**:
- Checkbox events inside files that were **created or renamed** in a commit (rather than modified)
  were excluded by design — `--diff-filter=M` only. Without this filter the bulk restore at
  `2053b758` alone produced ~6,400 phantom events. This means a task legitimately closed in a
  brand-new handoff file today is not counted. Spot-checking the added-file set showed no
  inference-gated closures there, but I did not enumerate it exhaustively.
- I verified that cited artifacts **exist and are timestamp-consistent**. I did **not** open the
  E5 `cells.jsonl` / FG-4b `evidence.json` payloads to confirm the reported numbers
  (26/31 decision-grade, `13.159866755320987 tok/s`) are what the files actually contain. That is a
  deeper measurement audit than this brief.
- Session attribution comes from annotation self-labels (`auditor`, `mainA`, `mainB`, `inference`,
  `coordinator-agent`) and the bus, not from git author — all 125 commits are authored
  `pestopoppa`.
