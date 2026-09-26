# Research-intake Stage-3 plan: orchestration prior art (harness to capacity-aware multi-model stack), 2026-09-26

**Status: PROPOSED. Awaiting operator approval. Nothing below has been applied.**
Lane: `intake/orch-prior-art-20260926` (worktree `/mnt/raid0/llm/worktrees/intake-orch-prior-art-20260926`, merged with
origin/main `5302d271`). Stage 4 applies exactly this plan, once approved, and nothing more.

## How to read this plan
- Sections P1 to P4 were drafted in parallel. **P4 §Reconciliation (R1–R6) is authoritative wherever it conflicts with
  P1, P2 or P3.** Its main effects:
  - The shared admission/wait estimator has ONE owner, **DAR-LAT-1**, under the **RTG-09** row
    (`decision-aware-routing.md`).
  - P1's HS-OD-9 and the UFH-01 Deps depend on RTG-09, not RTG-07.
  - P2's operator-queue row is **OP-62**.
  - The VB-* belief-kernel tasks are filed as ONE combined section.
  - P3's OD-A recommendation changes from B to **A**, per the P3-OD-A-ROCm fill in P4.
- The evidence base is 14 Stage-2 dived entries, 7 Stage-2b entries (intake-1815..1821, all dive-verified), and the
  Stage-1 records of 18 non-dived entries. No plan text quotes a number from a `stage1-unverified` entry. P4 §R5
  audited this.
- Checkbox discipline: every new task is `- [ ]`. Nothing is ticked except where a dive already settled it; each tick is
  flagged in its section. Ticking the OD-A "ingest-or-reaffirm" box as resolved-by-ingest (P3-4) happens only under this
  plan's human approval.

## Operator-directed scope (steering ledger seq 5): where each item landed
| Directive | Plan item(s) | Owner |
|---|---|---|
| (a) Chat-door Retry-After derived from live slot state | P1-A HS-OD-8 (make backpressure reach OpenCode at all: status and delivery) + P1-B HS-OD-9 (delay from DAR-LAT-1) | `harness-selection-and-integration.md` (UFH-01) |
| (a) Three GAIE gauges published internally | P2 "c3-A2 record + HSF-2" (slot-record fields; CPU roles need `--metrics` via stack-change) | `heterogeneous-slot-fabric-residency.md` |
| (a) Accept OpenCode `X-Session-Id` / `x-parent-session-id` as session fallback | P1-C HS-16 (+ P4-8 end-of-session signal / idle TTL) | `harness-selection-and-integration.md` |
| (a) No `x_*` rename to Dynamo `nvext` | P1-E decision record HS-18 (ticked decline) | `harness-selection-and-integration.md` |
| (a) Static per-role latency prior + saturation guard | P2 DAR-LAT-1 (shared estimator) + DAR-LAT-2 (weight-0 terms; prior keyed by role, device and topology_hash per P4-1) | `decision-aware-routing.md` (RTG-09) |
| (b) Load-sweep A/B, single-instance saturating tier, TTFT-bound, **Qwen3.8-Flash-Next** | P2 DAR-LAT-3 (six rigor controls; region claim + quiet CPU window as gating lines; VB-SEL-LOADAB wiring) | `decision-aware-routing.md` |
| (c) Stale: numa P/D assumes 2 sockets | P3-1 (re-scope to GPU-prefill/CPU-decode; 1 socket NPS4) | `numa-prefill-decode-disaggregation.md` |
| (c) Stale: fable5 rider F3 "no H2D measured" | P3-4 (dated notes; mainA-owned boxes get a bus flip request, not an agent tick) | `fable5-window2-findings-02-heterogeneous-gpu.md` |
| (c) Stale: OpenCode audit pin `350c726a` ≠ v1.18.31 tag `014614d3` | P1 §Stale-fact corrections (6 locations; the diff touches only console/web/.github, so the audit anchors hold) | `docs/reference/harness-candidates/*`, UFH-01 |
| (c) Other stale facts found | P1 (E2 backpressure cell, client-surface-audit §1, D-d status line, wiki cite :257 → :1870); P3-6 (pre-BIOS DRAM figures incl. `conversation-stack.md:98`, `wiki/multimodal.md:65`); P3 (INF-44 reopen trigger already fired; dead `llama.cpp/build/bin` path in `cpu_prefill_v8_regression_runner.py`) | per section |
| (d) Routing to owners (UFH-01, UFH-12 now on main) | Each item names exactly one owner. UFH-12 (`repl-embedding-retrieval.md`) gets no change: the DeLM/Proxifield items land on the D-d row of `repl-session-memory-maturity.md` (P1-F). | — |

## Operator decisions this plan needs (two, plus approval)
1. **OD-A (OP-61):** should KTransformers be declined as a runtime now, keeping only Expert Deferral as a technique
   behind F1 (option A)? Or should the build-only kt-kernel check F6 run first as evidence (option B)?
   **Recommendation: A.** The upstream-SGLang ROCm route does not exist for gfx90a (intake-1818), and the fork is
   CUDA-pinned (intake-1809).
2. **P-SERVE-SEL-1 (OP-62):** ratify the drafted serving-selection load-sweep protocol before DAR-LAT-3's first window,
   or accept observation grade for its result? **Recommendation: ratify**, bundled with any other pending ratification.
   This blocks only the claim grade. DAR-LAT-1/2, HSF-1 and the VB wiring proceed regardless.
- **Pre-run blocker to know about (not a decision):** live `:8074` (Qwen3.8-Flash-Next) runs `-t 96`, but the
  registered and codified recipe says 48. DAR-LAT-3's pre-run gate fails until a `stack-change` package reconciles the
  drift (P2 §Cross-section flags).

## Stage-3 completeness gates
- [x] Stage-2 close-out gate closed. 7 sources went to Stage-2b; the 19 declines are recorded in the bearing entries'
      `dive_corrections`. The 20 Stage-2b-surfaced sources are recorded as not ingested (the operator allowed one pass).
      The 4 distinct sources the dives flagged as worth a future intake are Continuum arXiv 2511.02230 (surfaced by two
      dives), vLLM issue #43563, Dochkina arXiv 2603.28990 and LEGOMem arXiv 2510.04851. They are `monitor` candidates
      only, with no task; the full list is in `.research-session.json` `stage2b.surfaced_sources_not_ingested`.
- [x] Every Stage-1 preliminary actionable (18 non-dived entries) maps to a plan item or an explicit decline. See the
      P1, P2 and P3 coverage tables.
- [x] Every dive-ledger row (35 Stage-2 + 26 Stage-2b) maps to a plan item, a fold or an explicit decline. See the P1–P4
      coverage tables.
- [x] Every steering-ledger row is a named item or an explicit decline: seq1 (single Stage-2 round) was honoured; seq2
      (CPU+RAM thesis) → P3 K1–K3 and P2 HSF-1; seq3 (Stage-2 selection) was executed; seq4 (two front doors, REPL
      hierarchy, consultant principle) is the framing of P1 and P2 and of P1-F/P4-12; seq5 → the table above.
- [x] No `stage1-unverified` number is quoted (P4 §R5).
- [x] Every named owner handoff was checked for frozen or pointer status (each section records the check).
      `dynamic-stack-concurrency.md:118`'s scope line moved the Retry-After work to UFH-01.
- [x] Second-reader disagreements are listed for the operator (next section), not auto-applied.

## Second-reader disagreements (operator may accept or reject; Stage 4 applies accepted ones as `claim_corrections`)
- intake-1783#6 is overstated: `engineConfigs` also carry LoRASpec and CacheInfoSpec.
- intake-1785#4: the source says "two" topologies.
- intake-1808#4: HumanEval used 10 sampling runs.
- intake-1809#3: gfx90a appears in `hip.h:160`, but there is no evidence it was tested. The torch-cu130 index is aarch64
  only.
- intake-1787#4: "short jobs" is not in the paper's stated future work.
- intake-1803#4: the optional LLM verifier is the worker's own model. #8(e): only 2 strategy prefixes are active.
- intake-1815#4: the Figure-6 fixed-rule tie count should be 6 of 8, not 5.
- intake-1819#11: it omits the medium-load router SCT gain.
- One mis-targeted anchor each on intake-1810 and intake-1808, and one weak (motivation-only) anchor on intake-1816.
- P4 §Stage-4 intake-index edits E1–E7 give exact text for the dive-driven corrections to intake-1796, 1789, 1809, 923,
  1803, 1785, 1815 and 1819.

## Stage-4 closing obligations (carried from the skill)
- Fill `handoffs_updated` / `handoffs_created` and `integration_disposition` + `disposition_evidence` on every touched
  entry. Each section's "Intake-entry dispositions" table gives the values.
- Run `validate_intake.sh`, `python3 scripts/handoffs/index_state.py` then `--check` (exit 0), and `vidya cite-check`.
- Stage only own paths, and close out the lane (worktree and branch) after `git cherry origin/main` is empty.

---
## P1 — Harness front doors, control plane and shared REPL state

**Pins used.** Lane worktree `33e82ae3` (merged with origin/main `5302d271`). Orchestrator
`epyc-orchestrator@fb7871ea` (HEAD on 2026-09-26, the same commit the c2/c3 dives read, so the dive line numbers
still hold). OpenCode: release tag `v1.18.31` = `014614d35b39`, lane audit pin `350c726aa8b6`. Both are in the
local clone `/mnt/raid0/llm/harness/opencode`, and the tag is also in `/mnt/raid0/llm/tmp/dive-intake-1790/repos/opencode`.
The pinned `@ai-sdk/openai-compatible@2.0.41` is at `/mnt/raid0/llm/harness/audit-deps/typecheck/node_modules`.

**Routing decisions, one owner each.**
- **UFH-01 `harness-selection-and-integration.md` owns every front-door item.** That covers HS-OD-8, HS-OD-9, HS-16,
  HS-17, the HS-18 decline record, the HS-3 note and the dormant-trigger prose.
  - c2-A1 moves here from `dynamic-stack-concurrency.md`. That handoff limits its own scope to "stack/profile
    orchestration and dynamic quarter assignment only" (`dynamic-stack-concurrency.md:118`). The Retry-After defect
    is a `/v1` seam defect, and the seam belongs to this handoff (`harness-selection-and-integration.md:109`).
  - c2-A6 moves from `learned-routing-controller.md` to a dormant naming note in `client-surface-audit.md` §1. That
    handoff is "FROZEN for expansion" (`learned-routing-controller.md:5`), and §1 is where the `x_*` naming contract
    lives.
- **P2 dependency, named and not duplicated.** HS-OD-9 consumes the expected-wait estimate that P2's C1-A2 saturation
  guard builds. That guard is owned by `contention-model-device-and-load-axes-rider.md` (RTG-07), and both read the
  same dispatch ledger: `AdmissionController.get_status()` (`src/api/admission.py:229`) plus the contention gate's
  active decodes. HS-OD-9 must not build a second estimator. HS-OD-8 has no P2 dependency.
- **c6/DeLM: `repl-session-memory-maturity.md` (EVL-36) owns both surviving items, as acceptance criteria on the
  unbuilt D-d row (`:154`).** No shared-notes block exists yet ("nothing in the lane has a blackboard today", c6
  design answer), so the prefix-stability invariant (6-A1) belongs to whatever creates the block.
  - `dynamic-stack-concurrency.md` is not amended. Its "(Z) Guard the prefix-stability assumption" row (`:241`)
    stays migration-scoped and is recorded as the analogue to reuse.
  - **UFH-12 (`repl-embedding-retrieval.md`) gets nothing.** Its invariant 1 (search returns pointers, reads go
    through `get`/`peek`, `:18-19`) already has the gist → pointer → unfold shape of intake-1803#1, so no new work
    is justified.

### Plan items

Four immediate packets survive compression: P1-A, P1-B, P1-C and P1-D. P1-E is records only, and P1-F is an
acceptance spec for an unbuilt row.

- **Safe to run concurrently:** P1-A, P1-C and P1-D. They touch different code (the `/v1` admission and stream path,
  the `/v1` session-key resolution, and `src/mcp_server.py` plus the OpenCode template).
- **Must wait:** P1-B runs after P1-A and after P2's C1-A2 estimator lands.
- **Anytime:** the P1-E records and the P1-F prose can land whenever.

None of the four packets blocks HS-4 P0.4. P1-A is worth landing first, because a P0.4 turn that meets an admission
denial today can fail with no retry (see P1-A).

#### P1-A — HS-OD-8: make `/v1` backpressure reach the shell as a retryable HTTP status (operator-agreed a1, part 1)

- **Project decision.** Whether OpenCode, the chosen shell, survives a busy stack. Today it does not reliably.
  Everything below was verified at orch `fb7871ea`.
  1. **Queue-full becomes a 502.** A full admission queue raises
     `RuntimeError("[ERROR: admission] Backend queue full …")` after a 2 s bounded wait
     (`src/llm_primitives/inference.py:958-972`). `/v1` has no handler for that case, so it reaches the generic
     backend-failure branches and answers **502 "Backend failed"** with no `Retry-After`. That happens at
     `openai_compat.py:1427-1433` for non-stream requests and `:1008-1016` for stream requests.
  2. **Streaming requests never carry a header.** On `stream:true`, which OpenCode's main loop E1 uses (lane
     `opencode-p03-audit-20260916.md:42`), every admission outcome is decided inside the generator after the 200 is
     sent. The source says so: "A stream cannot retract its 200" (`openai_compat.py:139-141`). So neither
     `Retry-After` nor `retry-after-ms` can ever reach OpenCode's `session/retry.ts` `delay()` (`:47-78`).
  3. **In-stream errors do not match OpenCode's retry patterns.** None of the three in-stream error texts matches
     OpenCode's retryable message patterns (`retry.ts:33-41`, `:146-152`). This was checked by running the patterns
     against the literal messages: the contention-gate text (`inference.py:518-519`), the placement-timeout text
     (`backends/concurrency_aware.py:1588-1590`) and "Backend failed: [ERROR: admission] …". A queued streaming turn
     can therefore end with no retry at all. The pinned SDK turns an `error` chunk into a plain-string error part
     (`@ai-sdk/openai-compatible@2.0.41` `dist/index.mjs:682-687`), not an `APIError` with status or headers.
     Whether that chunk even parses as the error variant is unverified; the test settles it.
- **Sources and ledger rows.** c2-A1, first half: status and delivery. It rests on intake-1790#1 (ACP carries no load
  signal) and intake-1792#1 (Tasks `pollIntervalMs` is not admission), so plain HTTP on the chat door is the only
  channel the pinned harness honours (c2 design answer (2)).
- **Primary owner.** `handoffs/active/harness-selection-and-integration.md`. **Execution posture:** `primitive-now`.
- **Reusable primitive.** A `/v1` backpressure contract: denial happens before the stream is committed, as a real HTTP
  503 carrying both headers, with a retryable text for anything that must stay in-stream. It keeps its value whatever
  delay policy follows.
- **Consumers.**
  - **Direct:** OpenCode `session/retry.ts`. OpenCode actors on the AutoKernel lane that call `:8000`
    (`autokernel-orchestrator-actor-backend.md`, INF-78).
  - **Evidence:** the P0.4 runner's `verify` (`scripts/harness/hs4_p04_acceptance.py`) sees fewer spurious failed
    turns. `src/api/health_tracker.py:244` classifies "admission … queue full" and must keep doing so after the
    status changes.
  - **Policy:** `tests/unit/test_openai_compat_backend_failure_status.py` pins 502 for genuine upstream faults and
    must keep doing so.
  - **Prospective:** any `/v1` client with standard retry, such as the research `scripts/lib/executor.py:630`, which
    already retries 503.
- **Consumer search evidence.** `grep -rlE "retry_after|Retry-After|retry-after|== 503|contention_denied"` over the
  orchestrator `src scripts tests orchestration` and research `scripts`. `grep -n "admission" src/api/routes/openai_compat.py`
  returned zero hits, which confirms there is no handler. Lane `grep -rln "Retry-After"` returned only the P0.3 audit.
- **Immediate deliverable.** Paste under `## \`/v1\` seam defects — HS-OD-3..7 (found 2026-09-17, descriptions fixed,
  behaviour not)` (`harness-selection-and-integration.md:107`), after HS-OD-7 (`:115`) and before "**Read these
  together with HS-OD-1.**" (`:117`). Retitle the heading to `HS-OD-3..9`. No anchor links to it: `grep -rn
  "seam-defects"` returned none. IDs checked: HS-OD-1..7 are used and HS-OD-8/9 are free across `handoffs`, `docs`,
  `research/intake_index.yaml` and `progress`.
  ```
  - [ ] **HS-OD-8 — backpressure never reaches the shell as a retryable HTTP status.** At orch `fb7871ea`: a full admission queue (`inference.py:958-972`) answers **502** "Backend failed" with no `Retry-After` (`openai_compat.py:1427-1433`, stream `:1008-1016`); on `stream:true` (OpenCode's main loop) every denial is an SSE event after a 200, so no header can reach `session/retry.ts`; and no in-stream error text matches OpenCode's retry patterns (`retry.ts:33-41,146-152`), so a queued turn can fail with no retry. Fix: admit or probe before returning the `StreamingResponse`; answer a denial as HTTP **503 with `Retry-After` and `retry-after-ms`** (OpenCode reads `-ms` first, `retry.ts:51-56`); map queue-full to 503, keep genuine upstream faults 502; make any residual in-stream error text retryable (contains "503 service unavailable"). The header value stays the current constant until HS-OD-9. Acceptance: extend `harness/opencode-plugin/test/wire-contract.test.ts` through the pinned SDK 2.0.41 + `retry.ts delay()` — the header is honoured on a pre-stream 503 and the in-stream fallback is retried; `test_openai_compat_backend_failure_status.py` still pins 502 for upstream faults. Zero inference. [intake-1790#1, intake-1792#1]
  ```
- **Rigor (deterministic infrastructure).** No holdout applies.
  - Conformance: SDK-in-the-loop fixtures for four cases (pre-stream 503 with headers, in-stream fallback, a genuine
    502 upstream fault, and the 413 context overflow, which must stay non-retryable per `retry.ts:87`).
  - Mutation cases: drop the header, emit a 502 for queue-full, and emit a non-retryable in-stream text. Each must
    fail a test.
  - Provenance: the SDK version comes from `bun.lock` 2.0.41; the `retry.ts` copy is from tag `v1.18.31`.
- **Dependencies.** None. It is independent of P1-C and P1-D, and P1-B depends on it.
- **Broader trigger / if unfired.** Not applicable. Nothing broader is planned.

#### P1-B — HS-OD-9: derive the delay from live queue state; hold, don't bounce (operator-agreed a1, part 2)

- **Project decision.** Whether the one backpressure channel OpenCode honours carries capacity information.
  - Today the header values are constants: 5 s at `src/api/__init__.py:401,406` (ContentionDenied), 10 s at `:418`
    (retryable KV-pool exhaustion) and 30 s at `src/api/routes/chat.py:321`.
  - OpenCode retries at most 5 times (`retry.ts:31`), so a queue longer than the retry budget spans fails the turn.
  - OpenCode caps a header-supplied delay only at 2^31 ms (`retry.ts:30`), so an accurate estimate is honoured as
    given.
- **Sources and ledger rows.** c2-A1, second half. It rests on intake-1790#1 and intake-1792#1.
- **Primary owner.** `harness-selection-and-integration.md`. **Execution posture:** `primitive-now` for the code, and
  `monitor` for the live calibration verdict, which fires once there are enough bounces.
- **Reusable primitive.** A per-bounce backpressure receipt, plus a hold-or-bounce rule driven by the shared
  expected-wait estimate.
- **Consumers.**
  - **Direct:** OpenCode `retry.ts`, and the INF-78 actors.
  - **Dependency (provider):** P2's C1-A2 expected-wait estimate (RTG-07). Suggested interface:
    `expected_wait_s(role, priority) -> (seconds | None, basis)`, where `None` falls back to the constant with
    `basis="constant"`.
  - **Evidence:** the belief kernel, through the new source row VB-V1-BACKPRESSURE below. The SC19 `contention_gate`
    adapter (`scripts/vidya/adapters/README.md:268`) covers `/chat` `ChatResponse.contention_gate` only, not `/v1`
    bounces.
  - **Policy:** the closed `epyc.failure_provenance.v1` contract (`scheduling/contention_gate.py:516-604`) must NOT be
    widened.
- **Consumer search evidence.** The same greps as P1-A, plus `grep -n "contention_gate\|SC19\|failure_provenance"
  scripts/vidya/adapters/README.md`.
- **Immediate deliverable.** Paste directly after HS-OD-8:
  ```
  - [ ] **HS-OD-9 — derive the backpressure delay from live queue state (after HS-OD-8; consumes RTG-07's expected-wait estimate).** Replace the constants (5 s `api/__init__.py:401,406`; 10 s `:418`; 30 s `routes/chat.py:321`) with the expected wait from the ONE dispatch-ledger estimator the RTG-07 saturation guard builds (C1-A2) — never a second occupancy model. Hold the request in the orchestrator while the estimate fits its own wait budget (the template's `headerTimeout:false` means a pre-stream hold does not time out the shell); bounce only beyond it, with `Retry-After`=ceil(s) and `retry-after-ms`, so OpenCode's 5-retry budget (`retry.ts:31`) spans the queue. Emit `retry_after_ms` + `retry_after_basis` (`estimate|constant`) beside, never inside, the closed `epyc.failure_provenance.v1`. Write one receipt per bounce (VB-V1-BACKPRESSURE). [intake-1790#1, intake-1792#1]
  ```
- **Rigor (empirical: the live calibration of the estimate).**
  - Frozen input: every receipt carries the ledger snapshot at bounce time (per-backend `limit`/`available`/`waiting`,
    active decodes by role) and the estimator's version hash.
  - Incumbent baseline: the constant-header policy as shipped by HS-OD-8.
  - Per-item evidence: a JSONL receipt per bounce with `request_id`, `role`, `priority`, `t_bounce`, `retry_after_ms`,
    `basis`, `t_next_attempt`, `admitted_on_next_attempt` and `turn_outcome`.
  - Holdout: the estimator's constants are frozen before the first live window, and the verdict is taken on the next
    window only.
  - Denominator: every bounce counts. Bounces that were never retried (the turn failed or the client left) count as
    misses, and `basis=constant` bounces are counted separately.
  - Predeclared rule: keep `basis=estimate` if, over at least 30 estimate-basis bounces, the next-attempt admission
    rate is ≥ 80% and ≥ the constant baseline, AND retry-exhaustion turn failures are ≤ the baseline. Otherwise
    revert the header to `constant` and file the miss against RTG-07. This is an observation-grade gate under
    `MEASUREMENT.md`. It authorizes no deployment beyond the header basis.
- **Dependencies and concurrency.** It runs after P1-A and after P2's C1-A2 estimator lands. Nothing else waits on it.
- **Broader trigger.** A failed calibration reopens the estimator at RTG-07, not here.

#### P1-C — HS-16: accept session identity from headers as a fallback on `/v1`, and record the parent (operator-agreed a2)

- **Project decision.** Whether session identity and the child→parent link survive without the plugin hook.
  - The plugin's `chat.params` hook has no parent id: for a `task` child, `x_session_id` is the child's own id (audit
    E7, `opencode-p03-audit-20260916.md:48`).
  - OpenCode natively sends `x-session-affinity`, `X-Session-Id` and, for children, `x-parent-session-id` on every
    provider whose id does not start with `opencode` (`packages/opencode/src/session/llm/request.ts:187-201`). This
    was verified at tag `v1.18.31` with `git show v1.18.31:…`, and the dive verified it at HEAD `a42f393c`. Our
    provider id is `epyc-orchestrator` (template `:15-16`).
- **Sources and ledger rows.** c3-A1, resting on intake-1785#6 and intake-1785#2.
- **Primary owner.** `harness-selection-and-integration.md`. **Execution posture:** `primitive-now`.
- **One deliberate narrowing of the ledger text, not a reversal.** The ledger says the guard should "check the header
  before returning 422". For an **OpenCode user-agent with no body `x_session_id`**, the guard keeps its 422.
  - The header supplies identity but not `x_tool_mode="client"` or the plugin's other keys.
  - A plugin-less OpenCode turn would therefore be served in REPL-bridge mode, which is exactly the silent fail-open
    the guard exists to stop (`opencode-p03-audit-20260916.md:97-101`; guard `openai_compat.py:419-461`).
  - The header fallback satisfies the guard for every other trigger, for example `x_tool_mode=client` from a
    non-OpenCode client, or Dynamo headers.
  - The operator-agreed adoption (header identity as a fallback, plus the parent link) is delivered in full.
- **Honest scope.** The parent link has no live traffic today, because the template disables `task`, `@agent` and
  background subagents (audit E7–E9). It matters once HS-4 P4 (delegation, `:85`) or a template change re-enables
  children. Header identity would also key the E12 v2 runner path, which sends `X-Session-Id` but no `x_*`
  (`opencode-p03-audit-20260916.md:53`).
- **Reusable primitive.** A session-identity resolver with provenance: `session_id_source` and `parent_session_id`.
- **Consumers.**
  - **Direct:** OpenCode (native headers); any Dynamo-convention client (`x-dynamo-session-id`,
    `x-dynamo-parent-session-id`).
  - **Evidence:** the P0.4 `verify` A2/A4 checks match `request_keys.x_session_id`. They are unchanged, because the
    body key wins and the new fields appear only when a header supplied the id. The inference-tap metadata picks up
    `parent_session_id`.
  - **Prospective:** HS-4 P2/P3 memory and `session_search` keying (`:82-84`); HS-4 P4 delegation lineage.
- **Consumer search evidence.** In the orchestrator: `grep -n "v1_client_session_guard\|x_session_id\|user-agent\|
  parent_session" src/api/routes/openai_compat.py src/api/models/openai.py`. In the lane: `grep -rn "X-Session-Id\|
  x-parent-session-id"` over `docs/` and `handoffs/`. In the OpenCode tag: `request.ts` headers.
- **Immediate deliverable.** Paste under a new final section `## Research Intake Update — 2026-09-26 (orchestrator
  prior-art: harness front doors)`, appended after `:179` (the current end of the file, after the HS-TD-4 consumers
  paragraph). IDs checked: HS-1..HS-15 are used, and so are the retired HS-5/6/7/8/10/11/12/14 (`:166-168`); HS-16,
  HS-17 and HS-18 are free.
  ```
  - [ ] **HS-16 — accept session identity from headers as a FALLBACK on `/v1`, and record the parent.** Resolve `x_session_id` as body → `x-dynamo-session-id` → `X-Session-Id`; record `parent_session_id` from `x-dynamo-parent-session-id` → `x-parent-session-id`. OpenCode sends these natively on every non-`opencode*` provider (`session/llm/request.ts:187-201` at tag `v1.18.31`), including the child→parent link its `chat.params` hook cannot see (audit E7). Add `session_id_source` and `parent_session_id` to `request_keys` only when a header supplied them, so existing golden output is unchanged. Body wins on conflict; log it and flag `session_id_mismatch`. The P0.2 guard keeps its 422 for an OpenCode user-agent with no body key (a header gives identity, not `x_tool_mode`; a plugin-less turn would silently fall into REPL-bridge mode) and accepts header identity for every other trigger. Tests: precedence table, mismatch, a child `task` request carrying `x-parent-session-id`, Dynamo header-only accepted. Then update `client-surface-audit.md` §1's header line. Zero inference. [intake-1785#6, intake-1785#2]
  ```
- **Rigor (deterministic infrastructure).** No holdout applies.
  - Conformance: the precedence table covers each source alone, body plus a matching header, body plus a conflicting
    header, and the two header conventions against each other.
  - Guard branches: OpenCode user-agent with a header only (422); `x_tool_mode=client` with a header only (accepted);
    no identity from any source (422).
  - Golden: `request_keys` is byte-identical when only the body key is present.
  - Provenance: the header names come from the tag `v1.18.31` source and Dynamo `agents.rs@81a9871a:11-21`.
- **Dependencies.** None. It lands independently of P0.4, but not in the middle of a live P0.4 window, because it
  changes `/v1` behaviour that P0.4 exercises.

#### P1-D — HS-17: keep a queued `orchestrator_chat` MCP call alive; set the shell's MCP timeout

- **Project decision.** Whether the MCP control door works for calls longer than 60 s. Today it cannot.
  - OpenCode calls MCP tools with the SDK default timeout (60 000 ms, c2 dive). It resets that timeout only on
    `notifications/progress`, and it throws the progress message away:
    `resetTimeoutOnProgress:true, onprogress: () => {}` (`mcp/catalog.ts:54-66` @v1.18.31).
  - `orchestrator_chat` is a synchronous blocking POST with a default `timeout_s` of 120 s (`src/mcp_server.py:452`,
    `:383-406`).
  - The template's `mcp.orchestrator` block sets no `timeout` (`harness/opencode-plugin/config/opencode.jsonc.template:102-108`).
  - So any orchestrator-door call that queues or runs past 60 s dies in the shell. The template ships MCP
    `enabled:false`, and `--enable-mcp` turns it on (`hs4_p04_acceptance.py:199-200`).
- **Sources and ledger rows.** c2-A2, resting on intake-1792#4. The core MCP progress pattern is cited directly from
  `mcp-spec-2026-07-28-progress.mdx@ab3a39c1`, saved under `dive-intake-1792/sources/`.
- **Primary owner.** `harness-selection-and-integration.md`. **Execution posture:** `primitive-now`.
- **Reusable primitive.** A progress keep-alive for long orchestrator MCP tools, plus a config-lint rule.
- **Consumers.**
  - **Direct:** OpenCode with `--enable-mcp`, and INF-78 actors if they use the orchestrator MCP server (HS-4 P6,
    `:88`, would add more long-running tools).
  - **Policy:** the config lint in `harness/opencode-plugin/src/config-lint.ts`.
  - **Prospective:** the HS-4 P2 `memory_*` server (`:83`).
- **Consumer search evidence.** `grep -n "timeout\|report_progress\|Context" src/mcp_server.py`; `grep -rn "mcp\|timeout"
  harness/opencode-plugin/config`. In the OpenCode tag: `packages/core/src/v1/config/mcp.ts:20,56` (the `timeout`
  field) and `config.ts:182` (`experimental.mcp_timeout`). FastMCP 3.3.1 has `Context.report_progress`
  (`.venv/.../fastmcp/server/context.py:389`).
- **Immediate deliverable.** Paste in the same new section, after HS-16:
  ```
  - [ ] **HS-17 — keep a queued `orchestrator_chat` MCP call alive, and set the shell's MCP timeout.** OpenCode calls MCP tools with the SDK's 60 s default, reset only by `notifications/progress`, whose message it discards (`mcp/catalog.ts:54-66`, `onprogress: () => {}`); `orchestrator_chat` is a synchronous POST with a 120 s default (`src/mcp_server.py:452`, `:383-406`), and the template sets no MCP timeout, so any call past 60 s dies in the shell. (a) Template: set `mcp.orchestrator.timeout` ≥ the tool's `timeout_s` + 5 s (`packages/core/src/v1/config/mcp.ts:20`), and make the lint require it whenever MCP is enabled. (b) Server: the chat tools emit monotone `ctx.report_progress` (FastMCP 3.3.1) at under half the client timeout while `/chat` is in flight. Any user-visible queue or capacity text goes in the tool RESULT (for example `contention_gate.waited_s`). Acceptance: a fake MCP client with a 60 s timeout and reset-on-progress survives a 90 s call only with (b); the lint refuses an MCP-enabled config with no timeout. Zero inference. [intake-1792#4]
  ```
- **Rigor (deterministic infrastructure).** No holdout applies.
  - Conformance: the fake-client timeout test, using SDK 1.29.0 semantics (saved at
    `dive-intake-1792/sources/mcp-ts-sdk@1.29.0_protocol.js.timeout`).
  - Lint mutation cases: MCP enabled with no timeout, and a timeout shorter than `timeout_s`.
  - Existing guard: `tests/unit/test_mcp_undeclared_args_refused.py` must stay green, because the tool signature
    changes.
- **Dependencies.** None. It is independent of P1-A to P1-C.

#### P1-E — Decision records, dormant triggers and one standing rule (knowledge-only and decline; no open checkbox)

- **Sources and ledger rows.**
  - c2-A3 (intake-1790#0, #4); c3-A4 (intake-1785#2, #5, #6; operator-agreed a3); c2-A4, c2-A5 and c2-A7 (declines
    with triggers); C1-A3 (intake-1796#2, intake-1798#3; supporting evidence only).
  - intake-1791#0 and #4 (the standing rule).
  - The non-dived Stage-1 actionables for intake-1786, 1793, 1794, 1795, 1800, 1801 and 1806.
- **Primary owner.** `harness-selection-and-integration.md`.
- **Deliverable 1 — the HS-3 note (c2-A3).** Append as an indented sub-bullet under HS-3 (`:56`). The row stays `[x]`
  with no checkbox change:
  ```
    - 2026-09-26 (research intake): ACP `providers/set` does **not** fire the "ACP gains inference-routing semantics" clause. It is a Draft RFD gated behind the `unstable_llm_providers` schema feature: a process-scoped redirect of the agent's upstream (`baseUrl`, `apiType`, static headers) with no model, role, per-request routing or capacity field, which the `opencode.jsonc` `baseURL` already provides. Pinned OpenCode does not implement it. HS-3 stays not-triggered. [intake-1790#0, intake-1790#4]
  ```
- **Deliverable 2 — the HS-18 decline record (c3-A4).** Add a `[x]` row in the new 2026-09-26 section, because the
  dive and the operator settled it:
  ```
  - [x] **HS-18 — do NOT rename or alias the `x_*` keys to Dynamo's `nvext.agent_hints` (operator-agreed decline).** ✅ 2026-09-26 — No client in our stack emits `nvext` (OpenCode source has none). The two SDK emitters found send keys that Dynamo's own `deny_unknown_fields` schema rejects. Dynamo calls the API "a v1 API that we are actively co-designing". And `x_*` carries role forcing, REPL, memory and tool mode, which `agent_hints` has no field for. The adoptable part, session identity from headers, is HS-16. Revisit only if a harness we adopt emits `agent_hints`. [intake-1785#2, intake-1785#5, intake-1785#6]
  ```
- **Deliverable 3 — prose in the same new section (no checkbox).** Paste as-is:
  ```
  **Standing rule.** The orchestrator stays the sole caller of models; no orchestrator feature may depend on MCP sampling (deprecated in protocol 2026-07-28, earliest removal in the first revision released on or after 2027-07-28; never enabled by pinned OpenCode; and OpenCode's only provider is the orchestrator, so "borrowing the harness's model" loops back to us). [intake-1791#0, intake-1791#4]

  **Supporting evidence for the HS-4 one-router decision (`:11`, `:60`), no new work.** A decoupled router in front of or beside the orchestrator cannot make the latency-priced mix shift that RouteBalance's four-arm isolation attributes the gain to (intake-1796#2), and interference between routers that independently send to shared instances is open future work (intake-1798#3).

  **Dormant triggers (no checkbox until one fires):**
  - MCP Tasks for `orchestrator_*` — re-evaluate when an OpenCode release enables the `tasks` client capability (issue 28567; commented out at `mcp/index.ts:47-48`). Tasks absorbs overload, it does not propagate it, and adoption needs fastmcp 3.3.1 → 4.x. [intake-1792#1, intake-1792#4]
  - An ACP-shaped `usage_update` from the orchestrator — declined: the orchestrator is not on the ACP wire, OpenCode already computes it from the OpenAI usage block, and it has no load field. [intake-1790#1, intake-1790#4]
  - The orchestrator as an ACP proxy/conductor — declined: Draft, in no schema, north of the shell, and proxies cannot touch model parameters. [intake-1790#3]
  - A gateway or load balancer in front of `/v1` (intake-1786, intake-1800; both stage1-unverified) — declined: it is a second router, contrary to HS-4's "one router" (`:60`). Reopen only if an adopted shell cannot reach `/v1` directly.
  - Harness-side fan-out sizing (intake-1806, unverified) — only if HS-4 P4 or a template change re-enables shell subagents (`permission.task`, `subagent_depth`); then the capacity signal is HS-OD-9's `Retry-After` plus HS-16's parent link, not a new hint key.
  - Architect→editor split (intake-1794, unverified) — only if P0.4 or later live runs show malformed tool calls from a reasoning role; dive the source before citing it.
  - Delegation defaults (intake-1793, unverified) — HS-4 P4 may consult it when it designs delegation defaults; dive before citing it.
  ```
- **Execution posture.** `knowledge-only` for the rule and the evidence note; `decline` or `monitor` for the triggers,
  each with an observable condition as named. intake-1795 (model choice stays server-side) and intake-1801 (a
  capacity-signal contract) need no prose here. intake-1795 is already the HS-OD-3 operator decision (`:111`).
  intake-1801's question was answered by the c3 dive: GAIE proposal-003 is the only standard contract (c3-A2, owned
  elsewhere).
- **Deliverable 4 — the c2-A6 naming note.** This is a dormant `monitor` item. `learned-routing-controller.md` is
  frozen for expansion, so it goes in `docs/reference/harness-candidates/client-surface-audit.md` under
  `## 1. The contract being audited` (`:13`), as a continuation of the "**Deterministic override flags.**" bullet
  (`:40-43`):
  ```
    *Naming note (2026-09-26, dormant):* if a harness→orchestrator priority hint is ever added, name its typed `x_*` keys after MCP's `costPriority` / `speedPriority` / `intelligencePriority` (0–1, advisory; the orchestrator makes the final choice) and cite them as borrowed vocabulary. `ModelPreferences` is a deprecated MCP type (SEP-2577), not a live contract. The plugin injects static body keys, which limits per-turn use. [intake-1791#2]
  ```

#### P1-F — D-d acceptance: admission gate for shared notes and a prefix-stable notes block (6-A2, 6-A1)

- **Project decision.** How the future curation layer admits shared or pinned notes, and how it injects them into
  prompts without breaking prefix reuse. D-d is unbuilt and marked "Lowest priority"
  (`repl-session-memory-maturity.md:154-155`).
- **Sources and ledger rows.** 6-A2 (intake-1803#4, #6) and 6-A1 (intake-1803#2).
- **Primary owner.** `handoffs/active/repl-session-memory-maturity.md` (EVL-36). The file was checked for frozen or
  pointer status: its status is "active", and it has no "do not add" clause.
- **Execution posture.** `monitor`. The trigger is the D-d design opening. D-d stays the one checkbox, and these
  bullets are its acceptance criteria.
- **Consumers.**
  - **Evidence:** `repl-turn-efficiency.md:159`, the prefix-cache contradiction row, which reads the same `/slots`
    reuse figure.
  - **Policy analogue:** `dynamic-stack-concurrency.md:241` (Z), the migration-scoped prefix guard, reused and not
    forked.
  - **Prospective:** `tri-role-coordinator-architecture.md`'s Verifier policy ("cheapest model trusted for the role",
    `:220-226`). That file is frozen, so it gets no task.
- **Consumer search evidence.** `grep -n "D-d"` over RSMM; the c6 design answer's search of `delegation-context-
  preassembly.md:42-45` (push bundles, no blackboard); `grep -n "cache_n\|n_prompt_tokens_cache"
  wiki/benchmark-methodology.md` (`:1870`).
- **Immediate deliverable.** Paste as indented sub-bullets directly under D-d, after `:155`. The D-d checkbox itself is
  not touched:
  ```
    - **D-d acceptance (added 2026-09-26, research intake).**
      - *Admission gate for shared or pinned notes.* A deterministic grounding check comes first: a note's cited span must appear verbatim in its source, and a note that claims a result must reference an execution present in the session record. Only after that, an optional worker-tier semantic check. Admission is never routed to the architect. The one ablated DeLM component is admission verification (LongBench-v2, GPT-5.4, a single model; 60.1 → 55.2 without it) [intake-1803#6]; its cheapest form is a verbatim reference check [intake-1803#4].
      - *Any notes block injected into delegated or REPL-worker prompts is a prefix by construction:* rendered append-only, byte-identical across viewers, and placed before any per-worker, per-step or tools content. Acceptance is a static check that the rendered block is a prefix-stable function of the note log, plus a reuse reading from `/slots` `n_prompt_tokens_cache` / `timings.cache_n` (`wiki/benchmark-methodology.md:1870`). DeLM's released prompts break all three conditions [intake-1803#2]; that is the failure mode this guards against. The migration-side analogue is `dynamic-stack-concurrency.md` "(Z) Guard the prefix-stability assumption"; do not fork it.
  ```
- **Rigor.** No experiment runs now. When D-d is built:
  - The admission gate is deterministic infrastructure. Its conformance checks are verbatim-span hit and miss cases, a
    fabricated execution reference, and a mutation that corrupts the source.
  - The reuse reading is observation-only, taken alongside `repl-turn-efficiency.md:159`'s measurement.
- **If unfired.** It stays prose under D-d, with no new checkbox and no index change (EVL-36's next action remains
  D-f1).

### Stale-fact corrections

1. **The OpenCode pin is not the `v1.18.31` tag.**
   - **Evidence.** The c2 `artifact_audit` item (1) (`stage2/c2.yaml:580-583`), plus this section's own check in
     `/mnt/raid0/llm/harness/opencode`:
     - `git rev-parse v1.18.31^{commit}` gives `014614d35b39` ("release: v1.18.31", 2026-09-14).
     - `git merge-base 350c726a v1.18.31` gives `a97622c8`. The pin is 8 commits past it and the tag is 1.
     - `git diff --name-only v1.18.31 350c726a` touches only `packages/console` (28 files), `packages/web` (36) and
       `.github/TEAM_MEMBERS`. `packages/{opencode,core,llm,server,plugin,tui}` and `bun.lock` are identical.
   - **So the label is wrong but the audit holds.** Every anchor in the audit holds at the installed release. The
     freeze should name the tag.
   - **Conventions.** Audit and design docs take dated correction notes in italics (precedent at
     `opencode-p03-audit-20260916.md:76`). Live status lines in the handoff are corrected in place, and dated history
     bullets are left alone.
   - (a) `docs/reference/harness-candidates/opencode-p03-audit-20260916.md`, after the §1 table (after `:18`), append:
     ```
     *Correction 2026-09-26 (research intake): `350c726aa8b6` is a dev-branch commit whose packages report 1.18.31, not the release. Tag `v1.18.31` (what `npm install opencode-ai@1.18.31` installs) is `014614d35b39`. Both descend from `a97622c8` (pin +8 commits, tag +1 release commit); `git diff v1.18.31 350c726a` touches only `packages/console`, `packages/web` and `.github`, so `packages/{opencode,core,llm,server,plugin,tui}` and `bun.lock` are byte-identical and every anchor below holds at the released tag. The P0.4 pin freeze records `014614d3` as the served identity and `350c726a` as the audit anchor.*
     ```
   - (b) `handoffs/active/harness-selection-and-integration.md:29`, candidates-table cell. Replace
     "pin `350c726a` (v1.18.31)" with "pin `350c726a` (audit anchor; release tag `v1.18.31` = `014614d3`,
     source-identical — audit §1 correction)".
   - (c) Same file, `:65` (P0.3 live-state line). Replace "Done at pin `350c726a` (v1.18.31)" with "Done at pin
     `350c726a` (source-identical to release tag `v1.18.31` = `014614d3`; audit §1 correction 2026-09-26)".
   - (d) Same file, `:66` (P0.4). After "OpenCode 1.18.31 installed.", insert "The freeze records tag `014614d3`
     (served) and `350c726a` (audit anchor)."
   - The dated history bullets at `:68`, `:70` and `:75` are left as written. `:75`'s "the audited pin is 1.18.31
     (`350c726a`)" is true for the source that matters, per the diff above.
   - (e) `docs/reference/harness-candidates/client-surface-audit.md:6-7`. Replace "pin `350c726a` v1.18.31" with
     "pin `350c726a`, source-identical to release tag `v1.18.31` = `014614d3`".
   - (f) `docs/design/hs4-shell-and-orchestrator-features-20260916.md:32` and
     `docs/design/hs4-harness-decision-package-20260916.md:237`. Append inside each italic superseded note:
     " *(Correction 2026-09-26: `350c726aa8b6` is the audit anchor, not the `v1.18.31` tag `014614d3`; source-identical
     for `packages/opencode` — see `opencode-p03-audit-20260916.md` §1.)*"
2. **The P0.3 audit's E2 cell overstates backpressure delivery** (`opencode-p03-audit-20260916.md:43`).
   - The stale text is "503 from admission control will be retried with backoff and honours `retry-after`
     (`retry.ts:47-78`)".
   - At orch `fb7871ea`, queue-full answers 502 and carries no header. On `stream:true`, every denial is an in-stream
     event sent after a 200, and none of those texts matches OpenCode's retry patterns (P1-A evidence). OpenCode also
     reads `retry-after-ms` first (`retry.ts:51-56`).
   - The audit's convention is addenda, so append a new `## Addendum 2026-09-26: backpressure delivery and session
     headers (research intake)` at the end of the file:
     ```
     - **E2 correction.** The E2 cell's "503 from admission control … honours `retry-after`" holds only for a pre-stream HTTP 503. At orch `fb7871ea` a full admission queue answers 502 with no header (`inference.py:958-972` → `openai_compat.py:1427-1433`), and on `stream:true` every denial is an SSE event after a 200, whose text matches none of `retry.ts:33-41`. OpenCode reads `retry-after-ms` before `retry-after` (`retry.ts:51-56`). Fix: HS-OD-8/HS-OD-9.
     - **E7/E12 and session headers.** The `X-Session-Id`, `x-session-affinity` and `x-parent-session-id` headers (`session/llm/request.ts:187-201`, identical at tag and pin) become an identity fallback under HS-16. E12's v2 runner would then be keyed by identity, but still carries no `x_*` keys.
     - **MCP timeout.** Tool calls use the SDK's 60 s default, reset only by progress notifications (`mcp/catalog.ts:54-66`). The template sets no `mcp.orchestrator.timeout` — HS-17.
     ```
3. **`client-surface-audit.md` §1 has two stale sentences.**
   - (a) `:30` lists `x_force_model` as an extension field. HS-OD-3 renamed it to `x_force_role`, keeping
     `x_force_model` as a deprecated alias (orch `2a609f5c`, `harness-selection-and-integration.md:111`). Replace
     "`x_force_model`" with "`x_force_role` (deprecated alias `x_force_model`)".
   - (b) `:33` says "The only HTTP header the API reads is the `x-task-id` observability tag." That is stale: the P0.2
     guard reads `User-Agent` (`openai_compat.py:448`). Replace the sentence with: "The API reads two request
     headers: the `x-task-id` observability tag and `User-Agent` (the HS-4 P0.2 session guard). HS-16 adds session-id
     headers as an identity fallback, not as overrides." The rest of the bullet ("There is **no header path to an
     override** …") still holds.
4. **The `repl-session-memory-maturity.md:3` status line says D-d landed.** It reads "D-a/…, D-c1, D-d, D-e all
   landed 2026-07-27", but D-d is an open box (`:154`) and the implementation log records only D-a, D-b and D-e
   (`:282`).
   - Fix: delete "D-d, " from the landed list.
   - Then append to the "Remaining:" clause: "D-d (curation layer; acceptance extended 2026-09-26)".
5. **Incidental, not an assigned file (for the owning session).**
   - `dynamic-stack-concurrency.md`'s "(Z) Fix the misnamed `VERIFIED`" row cites `wiki/benchmark-methodology.md:257`
     as the KV-reuse instrument.
   - That anchor has rotted: the text is now at `:1870`. Stage 4 may re-point it, and it is flagged here only.

### Explicit declines

| Row | Decline | Reason (one line) |
|---|---|---|
| C1-A3 | Already decided; no new work | The HS-4 one-router decision (`:11`, `:60`) and HS-OD-3's "role is the contract" (`:111`) are implemented. The evidence is recorded as prose in P1-E (intake-1796#2, intake-1798#3). |
| c2-A4 | MCP Tasks for `orchestrator_*` | No path reaches pinned OpenCode: its `tasks` capability is commented out (`mcp/index.ts:47-48`), and its SDK 1.29.0 speaks protocol 2025-11-25, which is not wire-compatible. Tasks absorbs overload rather than propagating it, and adoption needs fastmcp 4.x. Trigger: OpenCode issue 28567 (P1-E prose). |
| c2-A5 | ACP `usage_update` analogue | The orchestrator is not on the ACP wire; OpenCode derives it itself (`acp/usage.ts:208-217`); it has no load field. |
| c2-A7 | Orchestrator as an ACP proxy/conductor | Draft and in no schema; it would sit north of the shell; proxies cannot touch model parameters; there is no editor in the deployment (HS-2, `:55`). |
| c3-A4 | Rename `x_*` to `nvext.agent_hints` (operator-agreed a3) | Recorded as the `[x]` row HS-18 (P1-E). |
| 6-A3 | A DeLM-style queue with idle slots claiming subtasks | DeLM's released system has no queue, and the queue and shared context are not ablated (intake-1803#0, #6). Any pull-claiming design must argue from `heterogeneous-slot-fabric-residency.md:190-196, 221-230`, not from DeLM. |
| 6-A4 | A flat RLM-worker arm with shared notes | It rests on one run with no variance and a transcribed RLM baseline, and no hybrid code is released (intake-1803#3). `repl-turn-efficiency.md:154` already records that RLM fan-out converts prefill into decode on this box. Revisit only on an independent replication. |
| intake-1786 (SMG) | Gateway between OpenCode and `/v1` | It would be a second router, contrary to HS-4 (`:60`). Gateway-side history is already planned inside the orchestrator (HS-4 P1–P3). Unverified entry, and no mechanism is cited. |
| intake-1800 (LiteLLM) | A "LiteLLM in front of `/v1`" profile | It would be a second router or balancer. OpenCode reaches `/v1` directly (`enabled_providers:["epyc-orchestrator"]`, audit `:90`). Unverified. |
| intake-1805 | Borrow a blackboard "cleaner" role for REPL state | REPL session state is a namespace, not a message board; bounding is already owned by D-e/D-h/D-i. Unverified; no mechanism is cited. |
| intake-1807 | Read-set-validated writes as an MCP file-tool policy | The orchestrator MCP serves no write tools (HS-4 P6 is read-only, `:88`), and shell subagents are disabled. Unverified. |

The Stage-1 actionables for intake-1793, 1794, 1795, 1801 and 1806 are not declined outright. They are recorded as
knowledge-only or monitor items in P1-E.

### New stubs + index rows

- **New stubs:** none. Every item amends an existing handoff.
- **New index rows:** none.
- **One `Deps` edit.** In `user-facing-harness-index.md`, whose table header (`:11`) is
  `| ID | Track | Handoff | Next action | Deps |`, the UFH-01 row's `Deps` changes from `—` to `RTG-07`. HS-OD-9 consumes
  the RTG-07 saturation-guard estimator. UFH-01's `Next action` stays P0.4.
- **EVL-36 and RTG-11 are unchanged.**
- **Belief-kernel write-side wiring for HS-OD-9's receipts.** Per CLAUDE.md, this is surfaced now. The text below is
  prepared by this section, and the owning session applies it.
  - Add to `handoffs/active/vidya-belief-substrate-program.md` as a new section after `:2961`
    (`## VB-V1-BACKPRESSURE — /v1 backpressure receipts (filed 2026-09-26)`). The ID was checked free: it has no hits
    in `handoffs/`.
    ```
    - [ ] **VB-V1-BACKPRESSURE — wire the write side of `/v1` backpressure receipts** (`harness-selection-and-integration.md` HS-OD-9) before the first live bounce: one receipt per bounce with the dispatch-ledger snapshot, estimator version, `retry_after_ms`, `retry_after_basis`, next-attempt time and admission, and turn outcome. Locator = request; never graded above observation until a codified protocol exists. Distinct from SC19 (`ChatResponse.contention_gate`, `/chat` only).
    ```
  - Add to the source table in `scripts/vidya/adapters/README.md`, whose header is at `:193` (`| source | class |
    state | adapter |`):
    ```
    | `/v1` backpressure receipts (HS-OD-9; one per 503 bounce) | measurement | **candidate — wire the write side NOW**, before HS-OD-9 ships: dispatch-ledger snapshot + estimator hash + emitted `retry_after_ms`/`basis` + realized next-attempt admission; locator = request; observation-grade only | — |
    ```

### Intake-entry dispositions

| Entry | handoffs_updated | integration_disposition | disposition_evidence (one line) |
|---|---|---|---|
| intake-1785 | + `harness-selection-and-integration.md` (P1 rows; other sections add theirs) | integrated | "HS-16 (header-precedence session identity plus parent link) filed; HS-18 records the operator-agreed nvext rename decline (Stage 4, 2026-09-26)." |
| intake-1790 | + `harness-selection-and-integration.md` | integrated | "HS-3 note records that providers/set does not fire the ACP routing trigger; HS-OD-8/9 rest on #1 (no load signal in ACP)." |
| intake-1791 | + `harness-selection-and-integration.md` (standing-rule prose) | knowledge_only | "Sole-caller-of-models rule recorded in the harness handoff; modelPreferences kept only as a dormant naming note in client-surface-audit §1." |
| intake-1792 | + `harness-selection-and-integration.md` | integrated | "HS-OD-8/9 (HTTP backpressure on the chat door) and HS-17 (progress keep-alive plus MCP timeout) filed; Tasks declined until OpenCode issue 28567 lands." |
| intake-1803 | + `repl-session-memory-maturity.md` | integrated | "D-d acceptance extended with a deterministic admission gate and a prefix-stable notes block; queue/pull-claiming and the DeLM+RLM arm declined." |
| intake-1796, intake-1798 | + `harness-selection-and-integration.md` (evidence prose only) | set by P2's section | Supporting evidence for the one-router decision (C1-A3); no disposition change from P1. |
| intake-1786 | none | declined | "A gateway in front of /v1 would be a second router, contrary to HS-4 'one router'; history already planned in-orchestrator (HS-4 P1–P3)." |
| intake-1793 | + `harness-selection-and-integration.md` (dormant prose) | knowledge_only | "Pointer for HS-4 P4 delegation defaults; stage1-unverified, dive before citing." |
| intake-1794 | + `harness-selection-and-integration.md` (dormant prose) | monitor | "Trigger: live runs show malformed tool calls from a reasoning role; no current evidence of edit-format failure." |
| intake-1795 | none | knowledge_only (unchanged) | "Contrast case; model choice already server-side by operator decision HS-OD-3." |
| intake-1800 | none | declined | "A LiteLLM front is a second router; OpenCode reaches /v1 directly." |
| intake-1801 | none | knowledge_only | "Its capacity-contract question was answered by the c3 dive (GAIE proposal-003 is the only standard); no dive." |
| intake-1805 | none | knowledge_only (unchanged) | "REPL state bounding owned by D-e/D-h/D-i; the pruning-role idea stays unverified." |
| intake-1806 | + `harness-selection-and-integration.md` (dormant prose) | monitor | "Trigger: shell subagents re-enabled (permission.task / subagent_depth or HS-4 P4); the signal is then HS-OD-9 Retry-After plus the HS-16 parent link." |
| intake-1807 | none | knowledge_only (unchanged) | "No MCP write tools and no parallel shell agents in one tree today." |

The c2 dive-surfaced sources were declined in Stage 2 (issues 28567 and 11948, the progress/cancellation spec, the
SEP-2663 implementations and the ACP rust-sdk conductor). Issue 28567 is now the recorded watch trigger for c2-A4 in
P1-E, and nothing else is needed.

### Coverage table

| Row | Maps to |
|---|---|
| C1-A3 | decline (P1-E evidence prose) |
| c2-A1 | P1-A (HS-OD-8) + P1-B (HS-OD-9) |
| c2-A2 | P1-D (HS-17) |
| c2-A3 | P1-E, HS-3 note |
| c2-A4 | decline + monitor trigger (P1-E) |
| c2-A5 | decline (P1-E prose) |
| c2-A6 | P1-E deliverable 4 (dormant naming note, `client-surface-audit.md` §1) |
| c2-A7 | decline (P1-E prose) |
| c3-A1 | P1-C (HS-16) |
| c3-A4 | P1-E, HS-18 `[x]` decline record |
| 6-A1 | P1-F (D-d acceptance, prefix-stable notes block) |
| 6-A2 | P1-F (D-d acceptance, admission gate) |
| 6-A3 | decline |
| 6-A4 | decline |
| intake-1786 | decline (P1-E prose) |
| intake-1793 | knowledge-only (P1-E prose) |
| intake-1794 | monitor (P1-E prose) |
| intake-1795 | knowledge-only (no edit) |
| intake-1800 | decline (P1-E prose) |
| intake-1801 | knowledge-only (answered by c3) |
| intake-1805 | decline |
| intake-1806 | monitor (P1-E prose) |
| intake-1807 | decline |

### Open questions for the operator

None. The three operator-agreed adoptions (a1, a2, a3) are planned as work above.

The HS-16 guard behaviour for an OpenCode user-agent without a body key is a deliberate narrowing of the ledger's
wording, not a reversal. The fallback and the parent link are delivered in full. The guard keeps refusing the one case
where a header identity would hide a missing plugin and route the turn silently into REPL-bridge mode.

---

## P2 — Capacity-aware selection, slot telemetry, residency, and the load-sweep A/B

**Pinned revisions read.** Lane worktree `/mnt/raid0/llm/worktrees/intake-orch-prior-art-20260926` @ `33e82ae3`
(merge of origin/main 5302d271). Orchestrator `/mnt/raid0/llm/epyc-orchestrator` @ `fb7871ea29908f5a6051e854d957e32d20b72508`
(main). Research repo read-only. Live `:8074` argv read with `ps` on 2026-09-26 (pid 2030855). All `file:line` cites
without a repo prefix are lane-relative.

**The decision this section changes.** Today, `/v1` selection has no latency term and no load term. The only cost
term is historical elapsed time from episodic memory (`_scalarized_selection_score`, orch
`orchestration/repl_memory/retriever.py:46-57`, fed by `_estimate_cost_components` at :113-142).
`baseline_tps_by_role` is used only on the reward side (`q_reward.py:223`; `q_scorer.py:1177-1179`). The dive found
that a latency term is what carries the gain, and that a static prior matched a learned live estimate
(intake-1796#02). The one regime nobody has tested is ours: a single instance per role, TTFT-bound, with the
preferred tier saturated (stage2/c1.yaml contested claim "Residual", status open).

**Action architecture: three packets.** A and C are independent and can run in parallel. B depends on A.

| Packet | Items | Posture | Owner | Blocks |
|---|---|---|---|---|
| A — selection primitive | DAR-LAT-1 (shared `SlotCapacity` + `expected_wait_s`), DAR-LAT-2 (prior + guard at weight 0, AB plumbing) | primitive-now | `decision-aware-routing.md` | B; P1's Retry-After (c2-A1) |
| B — load-sweep A/B | DAR-LAT-3 (a–c) + VB-SEL-LOADAB | cheap-screen-now (operator-chosen; trigger = the open c1 residual) | `decision-aware-routing.md` | the default-weight flip (trigger prose) |
| C — swap-cost receipt | HSF-1 + VB-SWAP-C | primitive-now | `heterogeneous-slot-fabric-residency.md` | N-dwell C, capability card field |

Records with no work: C1-A5 signal map (rider), c3-A2 slot-record schema (fabric), c3-A5 load-cost reference
(within-role), C5-A3 and C5-A4 spec bullets (fabric). The declines (C1-A4, C1-A6, c3-A3, C5-A2, C5-A5) and the
non-dived triggers are listed after the plan items.

**Shared primitive with P1 (named, not duplicated).** `SlotCapacity` + `expected_wait_s(role)` sits on the
orchestrator's single admission ledger, `AdmissionController` (orch `src/api/admission.py:118-245`, live as
`state.admission`, `src/api/state.py:94`). P2 builds it in DAR-LAT-1. **P1's chat-door Retry-After derivation (c2-A1,
`dynamic-stack-concurrency.md`) is a direct consumer and depends on DAR-LAT-1**, so P1 should not build a second
wait estimator.
*Assembler note:* if P1's section already claims the ledger extension, invert the edge: P1 owns the build, DAR-LAT-1
shrinks to a consumer line, and DAR-LAT-2 depends on P1's task. Only one of the two may carry the build checkbox.

---

### Plan items

#### DAR-LAT-1 — Build `SlotCapacity` + dead-reckoned `expected_wait_s` on the ONE admission ledger
- **Project decision:** a saturation guard and a derived Retry-After both need per-role busy/queued/expected-wait
  state. Today it exists only as bare counts (`AdmissionController.get_status()`, orch `src/api/admission.py:229-245`).
  There are no dispatch timestamps and no per-role view. The contention gate cannot supply it: it reads region
  holders only when `ORCHESTRATOR_PER_REGION_LOCKS=1` and otherwise returns `{}` (orch
  `src/scheduling/contention_gate.py:160-173`).
- **Sources / ledger rows:** C1-A2 (guard input), c3-A2 (runtime half of the slot-record fields), shared with P1
  c2-A1. Sources: intake-1796#01 (dead reckoning as the anti-herding mechanism), intake-1798#02 (LPS with k = np),
  intake-1783#01 and intake-1783#07 (proposal-003 semantics; llama-server mapping).
- **Primary owner:** `handoffs/active/decision-aware-routing.md`. The (a4) adoption has exactly one owner. The C1-A2
  ledger proposal named the contention rider, but the rider is a DESIGN/no-code record
  (`contention-model-device-and-load-axes-rider.md:5`). Its ratified rule "router owns soft costs, fail OPEN with a
  penalty" (:160-163) is the rule this item implements, so the rider is recorded as a policy consumer, not an owner.
- **Posture:** primitive-now.
- **Reusable primitive:** role-keyed `SlotCapacity{queued, running, limit, kv_occupancy, source}` plus
  `expected_wait_s(role)`. It keeps its value even if the latency prior loses: Retry-After, the dashboard and the
  fabric slot record all use it.
- **Consumers:**
  - direct: DAR-LAT-2 guard; P1 Retry-After (orch `src/api/__init__.py:389-418`, `src/api/routes/chat.py:319-321`,
    which are constants today).
  - evidence: DAR-LAT-3 receipts; VB-SEL-LOADAB.
  - policy: rider §7 Q1 soft-cost rule.
  - prospective: the fabric slot record (HSF schema below, gated handoff); scout fan-out cap (orch
    `scout_stage.py:709-731`, which already derives `free = slots - processing` from `/slots`). The scout gets
    no task; it can switch to `SlotCapacity` when next touched.
- **Consumer search evidence:** orch `src/`, `orchestration/`, `scripts/server/` for `AdmissionController`,
  `get_status`, `admission`, `pool_occupancy`, `parse_slots`, `/slots`, `requests_deferred`, `requests_processing`,
  `llamacpp:`, `Retry-After`, `retry_after`, `slots_by_port`. There are zero `/metrics` pollers. Lane handoffs for
  `Retry-After`, `admission`, `queue depth`, `saturation`, `slot record`.
- **Immediate deliverable:** see the task line below.
- **Rigor (deterministic infrastructure):**
  - Holdout and incumbent are inapplicable.
  - Conformance: the ledger and `/slots` agree on `running` under a scripted fake backend.
  - Refusal branch: an absent ledger returns `source=unavailable` and `W=0` with a penalty flag.
  - Mutation case: a dispatch released without an acquire must not drive `running` negative.
  - Provenance: every field carries its source label.
- **Dependencies / concurrency:** none upstream. It does not touch the OP-41 resource broker (AKU-11), which governs
  campaign compute admission, not per-request serving admission.

#### DAR-LAT-2 — Static per-role latency prior + saturation guard in selection, landed at weight 0
- **Project decision:** whether selection prices latency and saturation, which is operator-agreed (a4).
- **Sources / ledger rows:** C1-A1 (prior), C1-A2 (guard). Sources: intake-1796#02, #06; intake-1797#00, #04;
  intake-1798#04, #05.
- **Primary owner:** `decision-aware-routing.md`. This follows the DAR-4b precedent: an inference-time term on the
  existing selector, which "does **not** reopen DAR-3/DAR-6/Package-I expansion gates" (`decision-aware-routing.md:155`).
  Landing at weight 0 keeps the routing freeze in the header (:3) intact until DAR-LAT-3 decides.
- **Posture:** primitive-now.
- **Code seam (orch @fb7871ea):**
  - Insert the term in `HybridRouter._apply_priors` (`orchestration/repl_memory/hybrid_router.py:308-327`), before the
    sort, the graph blend (:512) and `get_best_action` (`retriever.py:328`). Putting it in the retriever would couple
    the memory layer to the serving ledger.
  - Coverage gaps, recorded rather than silently accepted:
    - The MLP fast path bypasses the score (`hybrid_router.py:405-490`). It is OFF today
      (`learned-routing-controller.md:1754-1757`, LRC-2); see the LRC rollout precondition below.
    - The rules fallback (`hybrid_router.py:569`, `chat_routing.py:201`) has no score.
    - Escalation hops use the fixed ladder (`src/roles.py` escalation map), not selection.
    - X-MAS enforce (`routing.py:318`) and the failure veto (:344) can override the choice afterwards. Receipts
      record both the selection-time role and the final role.
- **Term definition:**
  - `score' = score − λ_lat·(T̂(role) + W(role)) / T_ref`, where `T̂ = L̂(role) · TPOT(role)`.
  - `TPOT = 1/baseline_tps_by_role` (registry-derived, `q_scorer.py:1057`). Each prior row carries its provenance:
    optimized versus substituted baseline, per `q_scorer.py:386-402`.
  - `L̂` = per-role p50 `tokens_generated` from `logs/progress` under an analysis id, using the same pattern as
    `derive_duration_baselines.py` (`decision-aware-routing.md:647`).
  - `W` = `expected_wait_s` from DAR-LAT-1.
- **Reusable primitive:** a per-decision **selection receipt** holding the Q, cost, T̂, W and live-term components,
  the admission snapshot, and the selection-time and final role. It is useful to DAR-5, RI-16 and any future
  routing A/B even if the prior loses.
- **Consumers:**
  - direct: `select_initial_route` (`routing_decision.py:314`).
  - evidence: VB-SEL-LOADAB; VB-ROUTE-LAT (`vidya-belief-substrate-program.md:2954`, which covers stage timing, not
    selection terms; no duplicate).
  - policy: DAR-LAT-3.
  - prospective: DAR-5 (the model-identity vector may absorb T̂).
- **Consumer search evidence:** as in DAR-LAT-1, plus `_apply_priors`, `_scalarized_selection_score`, `cost_lambda`,
  `routing_preferences`, `estimate_routing_cost`, `predicted_output`, `expected_tokens`, `output_length`, `tpot`.
  No output-length predictor exists anywhere; `max_tokens` is the only proxy (`routing.py:136`).
- **Rigor (deterministic infrastructure):**
  - A test pins λ_lat = 0 ⇒ rankings byte-identical to the current selector (RTG-09 precedent, `:647`).
  - Positive-control readback: A0/A1/A2 term components are zero or non-zero exactly as declared.
  - Fail-open branch: a missing prior or ledger gives term 0 plus a penalty flag.
- **Dependencies:** DAR-LAT-1.

#### DAR-LAT-3 — Load-sweep A/B: static prior + guard vs + live term, single-instance saturating tier, TTFT-bound, Qwen3.8-Flash-Next
- **Project decision:** keep the static prior + guard as the selection design, or add a live queue/progress term.
  The result also decides whether A1's weights leave 0. This is the c1 open residual; C1-A4 reopens only if the live
  arm wins.
- **Sources / ledger rows:** C1-A1 (A/B clause), C1-A2, C1-A4 (reopen condition). Sources: intake-1796#02,
  intake-1797#04, intake-1798#04, intake-1798#05.
- **Primary owner:** `decision-aware-routing.md`. This is a selection-policy A/B, and no existing handoff owns TTFT
  load tests.
  `cpu-decode-roofline-program.md` (INF-70, the Flash-Next program) is CLOSED OUT (:3). It is an evidence consumer:
  per the Flash-Next inventory (lane search; research-repo harness lines not re-read by P2), no TTFT or np>1 serving
  measurement exists for this model, and `:8074` runs `-np 1` (`kv-unified-stack-rollout.md:257`).
- **Posture:** cheap-screen-now. The trigger has already fired: the operator chose the experiment, and it is the named
  open residual. It is the smallest experiment that bears the claim, not a paper reproduction.
- **Instrument (read, not assumed):**
  - Tier under test: `architect_critic` = Qwen3.8-Flash-Next UD-IQ4_XS, CPU, `:8074`, registry `slots: 1`
    (orch `orchestration/model_registry.yaml:1863-1916`).
  - Codified recipe: `epyc-inference-research/scripts/lib/qwen38_flash_next_recipe.py`
    (`RECIPE_ID` :67, `THREADS = 48  # NOT 96` :690, `PARALLEL_SLOTS = 1` :692).
  - Architecture: GDN hybrid, 36 GDN + 12 attention layers (`cpu-decode-roofline-program.md:111`).
  - Divert target: `architect_general` (`:8083`, MI210). This is the registered fallback pair (orch `src/roles.py`
    `_FALLBACK_MAP`: `ARCHITECT_CRITIC: [ARCHITECT_GENERAL]`).
  - **The live argv differs from the recipe:** `-t 96 -c 262144 -np 1`, with no `--metrics`. So
    `llamacpp:requests_deferred` is unavailable on this CPU server, and the A2 live term reads `/slots` only.
- **Why A2 tests progress, not queue (design inference from code, not measured):** when the orchestrator is the only
  client, the ledger semaphore caps in-flight at np (`admission.py:125-129`, `inference.py:953-972`). A server-side
  deferred queue is then about 0 by construction, so live queue depth equals the ledger's. What A2 can add is
  **observed decode progress** (`/slots` busy flags + `n_decoded`) in place of dead reckoning. Traffic from
  non-orchestrator clients is out of scope and stated as a scope limit.
- **Arms:**
  - A0: incumbent, λ_lat = 0. Labelled production incumbent, category=OPTIMUM per MEASUREMENT.md §3.
  - A1: static prior + guard (DAR-LAT-2). category=CANDIDATE.
  - A2: A1 + live `/slots` term. category=CANDIDATE.
  - λ_lat is predeclared on the scale of the existing cost term (`cost_lambda·cost_tau`) and is never tuned on the
    evaluation half.
- **Six rigor controls:**
  1. **Frozen input manifest.**
     - Prompts: a seeded sample of the graded MMLU-Pro/GPQA item sets already used for Flash-Next's frozen-v10
       quality (`amd-ai-lab-website-publication.md:18`).
     - `max_tokens` capped (predeclared), `--reasoning off` as live, so the workload is TTFT-bound.
     - Item ids + sha256 recorded.
     - Candidate set predeclared as {architect_critic, architect_general} via the AB-mode restriction.
     - Items kept only if a dry route-explain pass (no generation) chooses architect_critic under both A0 and
       A1-at-zero-load. The kept fraction is reported, so the saturating tier really is Flash-Next.
     - Frozen prior table (TPOT, L̂) with digest.
     - Read-only episodic snapshot with digest, and Q-updates OFF for the window. The live store drifts otherwise.
     - Live argv plus the `kv_unified =` log line for :8074 and :8083 (`OPERATING_CONSTRAINTS.md:112`); kernel
       store digests (`verify_kernel_store.sh`).
     - **TTFT budget per item** = 2 × unloaded p50 TTFT of architect_critic for that item's prompt-length bucket,
       measured in a calibration phase on the calibration half. The factor 2 is predeclared.
     - Load points ρ ∈ {0.5, 0.8, 1.0, 1.25, 1.6, 2.0} × μ̂, where μ̂ is architect_critic's measured unloaded
       service rate on the calibration half. Saturating points are ρ ≥ 1.0.
     - Open-loop seeded Poisson arrivals. A block is 40 arrivals.
     - All of the above is frozen in `FROZEN-AT-LAUNCH.sha256` before the first arm block (R23-58 precedent,
       MEASUREMENT.md:576-600).
  2. **Incumbent baseline:** A0 runs at every load point, in the same window.
  3. **Per-item raw outputs.** `epyc-inference-research/data/sel-loadsweep-ab-<UTC>/` holds `manifest.json`,
     `requests.jsonl` and `blocks.jsonl`.
     - Each `requests.jsonl` row holds: arm, block, ρ, arrival/send/first-byte/done timestamps, HTTP status and error
       class, selection receipt (DAR-LAT-2), admission snapshot, `/slots` snapshot (A2), selection-time and final
       role, output text + hash, token counts, grader verdict.
     - `env/` holds argv, environ, kernel digests, host-health and region-claim witness.
     - Also `summary.json`.
     - Driver: new `scripts/benchmark/selection_loadsweep_ab.py`, reusing `measure_stream_ttft`
       (`server_np_sweep.py:602`) against the orchestrator's streaming `/v1/chat/completions`.
  4. **Holdout.**
     - Prompts are split 50/50 by seeded hash. The calibration half is used only for μ̂, the TTFT budgets and the
       sanity check on the priors. All arm blocks run on the evaluation half.
     - Time holdout: a later window W2, ≥24 h after W1, repeats ρ = 1.25 with all three arms in ABBA order and fresh
       arrival seeds.
  5. **Complete denominator.**
     - Every scheduled arrival counts. Late completions, 503s (ContentionDenied, `__init__.py:389-406`), 429s,
       `[ERROR: admission] Backend queue full` (`inference.py:972`), 413/overflow, the client hard deadline
       (predeclared as max(10 × budget, 600 s)) and connection errors are all TTFT-SLO misses, reported by class.
     - Quality scores failures as 0 (the E17 era rule).
     - The driver makes no retries.
  6. **Predeclared decision rule.**
     - Primary metric: S = TTFT-SLO attainment per block.
     - **Floor F**: the 95% upper bound of |ΔS| over **24 A1/A1 block pairs** at ρ = 1.25.
       - unit = **arm**: arms switch per request/block inside one experiment-API session, with no relaunch.
       - Recorded with n and an interval (FLOOR-UNIT-1, MEASUREMENT.md:533).
     - **Adopt the live term (A2)** only if all of the following hold. Otherwise keep static + guard and write a
       BOUNDED-NULL-1 statement (MEASUREMENT.md:576) with the power bound and the positive controls.
       - mean(S_A2 − S_A1) > F at ≥2 saturating ρ in W1;
       - the same sign and a gap > F at ρ = 1.25 in W2;
       - realized quality is non-inferior (A2 ≥ A1 − one per-suite quantum, MEASUREMENT.md §4);
       - no ρ < 1 point degrades by more than F.
     - **Clear A1's weights for a flip** under the same structure versus A0.
     - Intervals: PAIRED-CI-1 with the small-K correction, within a window only. W1 and W2 are never pooled
       (MEASUREMENT.md:434-438).
- **Positive controls (BOUNDED-NULL-1, both directions):**
  - Per-request receipts show exactly-zero terms in A0 and non-zero T̂ in A1/A2.
  - Every diversion carries a snapshot with `in_flight ≥ limit`; no non-saturated snapshot diverts.
  - A2's live term carries a fresh `/slots` timestamp; in A0/A1 it is null.
- **Scope notes:**
  - Diverting to the MI210 lane (host threads 184-191, SMT siblings inside region 0-95) couples the tiers through
    host contention (`cpu-decode-roofline-program.md:1025`, MEAS-6). That coupling is the production topology, so it
    is in scope and recorded, not removed.
  - `-np` stays 1. Raising it would trigger the G2-CONC gate (`cpu-decode-roofline-program.md:650-653`).
- **Gating prerequisites.** Each is an explicit task line below; none is a question.
  - A compute window granted through the bus (`agents/shared/INVARIANTS.md:27`, #8) covering the whole host: CPU
    0-95 plus the MI210 lane, per MEAS-6.
  - A region claim **acquired** (INVARIANTS.md:23, #5), by wrapping the driver in
    `region-lock run --cpu-list 0-95 -- …` (`agents/shared/OPERATING_CONSTRAINTS.md:106`, orch `scripts/region-lock`);
    an MI210 lease (orch `src/gpu_lease.py`).
  - AutoPilot quiesced by its owning session.
  - Reload ownership: the experiment session owns every API action in the window (`OPERATING_CONSTRAINTS.md:125`). A
    dedicated experiment API process (own port, AB mode) with a captured PID is used, and the production API is not
    reloaded.
  - Host-health preflight (`:110`).
  - Quiet-window preconditions (`measurement/protocols/bench-cpu.md:59`). The zombie check uses region-lock holders
    and captured PIDs, never `pgrep` name patterns (CLAUDE.md Process Management).
  - All other production servers show zero in-flight, **sampled during** each block (`OPERATING_CONSTRAINTS.md:47-67`).
  - The live `:8074` argv and environ match the registered recipe, including the OMP stack (`bench-cpu.md:116`). This
    **fails today** (`-t 96` vs 48); see the cross-section flags.
  - VB-SEL-LOADAB wired before the first block.
- **Claim grade:**
  - `instrument_class=serving` (production servers, registered recipe, orchestrator in the loop).
  - No ratified text-LLM TTFT/serving-load protocol exists (MEASUREMENT.md §2 :43-60; annexes list only P-TTS-3 for
    first-audio latency).
  - DAR-LAT-3a therefore drafts **P-SERVE-SEL-1** as a staged (📋) annex entry with a ratify script. Until the
    operator applies it, results are observation-grade (`MEASUREMENT_POLICY.md:7`). See the open questions.
- **Sizing and stop rules:**
  - After calibration the session computes the projected window length. If it exceeds the granted window, load points
    are dropped in the predeclared order 1.6 → 0.8 → 2.0. The n = 24 floor is never reduced.
  - Stop the run on any failed prerequisite sampled during a block. That block is re-queued, never dropped.
- **Broader-reproduction trigger:** if A2 wins, C1-A4's learned or live predictor question reopens, with an
  SFS-style simulator still excluded by the frozen kernel (intake-1798#06). If A2 loses, no broader work follows.
- **Dependencies:** DAR-LAT-1 → DAR-LAT-2 → DAR-LAT-3a → gates → 3b → 3c. VB-SEL-LOADAB goes before 3b. No safe
  parallel lane exists inside packet B.

#### HSF-1 — Launch-phase receipt on every production GPU launch → measured swap cost C per (model, MI210)
- **Project decision:** the N-dwell rule's C. Today it is illustrative: "C=20 s" (`heterogeneous-slot-fabric-residency.md:91-92`).
  The only datum is a single hot-cache load on an experimental build, and its own record says it is not decision-grade
  (`mi210-big-model-and-acceleration-roadmap.md:288`).
- **Sources / ledger rows:** C5-A1, and the C field of C5-A4. Sources: intake-1787#02, #03; intake-1789#04 (the
  fixed-penalty form C = a + size/b; seconds are NOT imported, per C5-A5).
- **Primary owner:** `heterogeneous-slot-fabric-residency.md`.
  The handoff is "DESIGN — GATED … Nothing is built until … the operator authorizes" (:18-22). This item adds
  instrumentation to the existing launcher and changes no placement or residency behaviour. **Plan approval is the
  operator authorization the gate names, scoped to HSF-1 only.** The N-dwell consumer at :153 stays gated.
- **Posture:** primitive-now. The receipt is produced by launches that happen anyway, so it needs no dedicated window.
- **Deliverable (what the receipt contains):**
  - In the orch `scripts/server/orchestrator_stack.py` GPU launch path (:1259-1275), write
    `orchestration/reports/launch_phase/<role>-<UTC>.json`.
  - It holds the decomposed timer from llama-server stderr: process start → `load_model` → `model loaded` → health
    ready → first token of a 1-token probe.
  - Plus: effective argv, binary path + store digest (`scripts/session/verify_kernel_store.sh`), GGUF sha256,
    page-cache resident fraction of the GGUF shards measured with `fincore` immediately before exec, and the
    outcome class.
- **Rigor (it is a measurement):**
  - frozen input: GGUF + binary digests and argv hash per receipt.
  - baseline: the illustrative 20 s and the :288 datum.
  - per-item: one receipt per launch.
  - holdout: leave-one-model-out prediction of C from the fit, plus a later-window launch.
  - denominator: every launch attempt counts. Failed loads are kept by class. Launches whose page-cache fraction is
    below 0.99 are labelled cold/partial and excluded from the hot fit by the predeclared rule, with the count reported.
  - decision rule:
    - When ≥5 hot receipts exist for each of ≥3 model sizes, fit `C = a + size/b`.
    - If the leave-one-out error is within the between-launch spread (unit = process launch), write the per-model C
      interval into the capability card and replace the illustrative C in N-dwell.
    - Otherwise write per-model C only.
    - Cold/post-reboot C stays gated on the operator protocol (`mi210-big-model-and-acceleration-roadmap.md:296`).
- **Consumers:**
  - direct: N-dwell (`:153`); capability card (`:147`).
  - evidence: VB-SWAP-C.
  - prospective: the Layer-3 policy (`:152`); the AXA-2 teleport break-even (roadmap AXA-2, which needs the hot load
    term).
- **Consumer search evidence:** lane handoffs for `swap cost`, `N-dwell`, `load_ready_ms`, `cold-load`, `min-dwell`,
  `capability card`; orch `scripts/server/` for `load_model`, `model loaded`, `health`.
- **Fallback trigger (prose, no checkbox):** if fewer than 5 hot receipts per model accumulate within 30 days, request
  a bus-granted GPU window for a 5-launch series per model. The GPU residents are drained under the swap protocol
  (:80-87) by the stack-owning session.
- **Dependencies:** none. Safe in parallel with packets A and B.

#### C1-A5 record — llama-server capacity-signal map (rider)
- **Posture:** knowledge-only. It is a durable record the dive settled from source; no checkbox.
- **Owner:** `contention-model-device-and-load-axes-rider.md`.
- **Why here:** it prevents a future agent from wiring a vLLM-shaped signal (KV%) or a lifetime-average gauge into
  routing. It adds one EPYC fact the dive did not have: CPU launches carry no `--metrics`. The live `:8074` argv was
  read on 2026-09-26, and orch `orchestrator_stack.py:1267` adds `--metrics` only on the GPU launch path.

#### c3-A2 record + HSF-2 — Slot-record fields in proposal-003 semantics (internal only)
- **Posture:**
  - Schema text: knowledge-only.
  - HSF-2 (`--metrics` on CPU launches): primitive-now, bundled into the next stack-change package. It is a
    production launch-argv change, which needs the stack-change signature, so it is not an ad-hoc edit.
- **Owner:** `heterogeneous-slot-fabric-residency.md` owns the schema. DAR-LAT-1 is the single runtime implementation
  (it has no gate).
- **Operator-agreed (a5):**
  - `queued` ← `llamacpp:requests_deferred`, falling back to ledger `waiting_*`.
  - `running` ← `llamacpp:requests_processing`, falling back to ledger `in_flight`, cross-checked against `/slots`
    busy flags.
  - `kv_occupancy` = Σ(n_prompt_tokens + n_decoded) over processing slots / Σ n_ctx, from `/slots`.
  - Each field carries a source label. While a CPU launch lacks `--metrics`, the fallback applies.
- **GDN-hybrid caveat:**
  - KV is preallocated at launch (`contention-model-device-and-load-axes-rider.md:193`), so `kv_occupancy` is a
    context-fill ratio, never a memory-pressure signal.
  - For GDN-hybrid residents the recurrent state is fixed per slot, and only the attention layers' KV scales with
    tokens (`:76`; Flash-Next 12 of 48 layers, `cpu-decode-roofline-program.md:111`). Do not route on it for those
    residents.
- **EPYC-only fields beside the three:** `device_class`, `numa_node`/`cpuset`, residency state including `UNKNOWN`,
  co-tenant count, measured prompt/predicted t/s.
- **Explicitly not** a Prometheus exporter and not an EPP feed (c3-A3 decline).

#### c3-A5 record — within-role replica load-cost reference
- **Posture:** knowledge-only.
- **Owner:** `within-role-placement-state-machine.md`.
- **Content:**
  - Dynamo's worker cost shape is the checked reference for any future load term in full-versus-quarter replica choice
    (intake-1785#01): `prefill_load_scale·max(0, raw_prefill_blocks − overlap_credit_blocks) + (active_decode_blocks +
    incoming_active_blocks) + decode_active_request_weight·active_requests`, with softmax temperature for spread.
  - The missing input, named honestly: llama-server exposes only post-hoc `n_prompt_tokens_cache`, not KV events
    (intake-1783#07). The prefix-overlap term therefore has no live source.
  - Carries the intake-1784 dive trigger.

#### C5-A3 / C5-A4 spec bullets — residency policy prior + capability-card fields
- **Posture:** knowledge-only. These are specs attached to the existing gated tasks `:152` and `:147`, and they inherit
  those gates; no new checkbox.
- **Owner:** `heterogeneous-slot-fabric-residency.md`.

---

### Paste-ready handoff edits

**1. `handoffs/active/decision-aware-routing.md`: append a new section at EOF (after line 681).** The last heading is
`## Research Intake Update — 2026-09-07` at :675.
IDs checked: the `DAR-*`, `DAR-SPLIT-1`, `URE-*` and `DAR-4b` series; `DAR-LAT` is unused, so the new series starts at
DAR-LAT-1.

```markdown
## Research Intake Update — 2026-09-26 (orchestration prior art: static latency prior + saturation guard; intake-1796/1797/1798)

Selection has no latency or load term today. The only cost is historical elapsed from memory
(orch @fb7871ea `retriever.py:46-57`, fed by :113-142), and `baseline_tps_by_role` is reward-side only
(`q_reward.py:223`). The dive puts the gain on a latency term and found a static per-tier prior as good as a
learned live estimate (intake-1796#02). The regime left open is ours: single-instance, TTFT-bound, preferred tier
saturated (intake-1798#05; intake-1797#04). The terms land at weight 0 like DAR-4b: they do not reopen the
DAR-3/DAR-6 expansion gates, and nothing changes live routing until DAR-LAT-3 decides.

- [ ] **DAR-LAT-1 — Build the shared `SlotCapacity` snapshot and `expected_wait_s(role)` on the ONE admission ledger.**
  Role-keyed over the role's backend URLs:
  - `queued` = `AdmissionController` waiting_*, `running` = in_flight, `limit` = np (orch `src/api/admission.py:229-245`).
  - `kv_occupancy` comes from the existing `/slots` reader (`context_limits.py:433-452`); extend `parse_slots` with
    `n_decoded`.
  - Every field carries a source label.
  - Record dispatch start time + predicted length at `acquire`/`release` and dead-reckon the expected wait (0 when
    a slot is free).
  - No new poller and no `/metrics` dependency (Axiom 1, heterogeneous-slot-fabric-residency.md:201).
  - Direct consumers: DAR-LAT-2 and the chat-door Retry-After derivation (dynamic-stack-concurrency.md, c2-A1).
  - Tests: ledger/`/slots` agreement, free-slot W=0, fail-open when the ledger is absent. intake-1796#01, intake-1798#02.
- [ ] **DAR-LAT-2 — Add the static per-role latency prior + saturation guard to `HybridRouter._apply_priors`
  (`hybrid_router.py:308-327`), landed at λ_lat=0 (byte-identical, test-pinned).**
  - `score −= λ_lat·(T̂+W)/T_ref`, with `T̂ = L̂(role)/baseline_tps_by_role[role]` (provenance-labelled,
    `q_scorer.py:386-402`).
  - `L̂` = per-role p50 `tokens_generated` from `logs/progress` under an analysis id.
  - `W` = DAR-LAT-1; missing inputs give term 0 plus a penalty flag (rider §7 Q1: soft cost fails open).
  - Emit a per-decision selection receipt: components, admission snapshot, and the selection-time role vs the final
    role after X-MAS (`routing.py:318`) and the failure veto (:344).
  - Env-gated AB mode: per-request arm id, declared candidate restriction, read-only episodic snapshot, Q-updates
    off, arm-A2 live term from `/slots` (busy flags + `n_decoded`). intake-1796#02, intake-1798#04.
- [ ] **DAR-LAT-3 — Load-sweep A/B on the single-instance saturating tier under a TTFT-bound workload:
  Qwen3.8-Flash-Next (`architect_critic` :8074, `-np 1`) with divert target `architect_general` (:8083, MI210).**
  - Arms: A0 incumbent (λ_lat=0), A1 static prior + guard, A2 A1 + live `/slots` term.
  - Results go to `epyc-inference-research/data/sel-loadsweep-ab-<UTC>/`.
  - Decision rule (predeclared, frozen in FROZEN-AT-LAUNCH.sha256):
    - Adopt A2 only if S = TTFT-SLO attainment beats A1 by more than floor F (24 A1/A1 block pairs at ρ=1.25,
      unit=arm) at ≥2 saturating ρ, AND reproduces at ρ=1.25 in holdout window W2, AND quality is non-inferior (≥ −1
      per-suite quantum), AND no ρ<1 point degrades by more than F.
    - Otherwise write a BOUNDED-NULL-1 statement and keep static + guard.
    - The same structure clears A1 against A0.
  - Settles the c1 open residual. intake-1796#02, intake-1797#04, intake-1798#05.
  - [ ] **DAR-LAT-3a — Freeze the pre-registration.**
    - Manifest: seeded MMLU-Pro/GPQA items (the frozen-v10 sets, amd-ai-lab-website-publication.md:18), `max_tokens`
      cap, candidate pair, dry-route-explain filter (architect_critic chosen under A0 and A1 at zero load), frozen
      prior table and episodic snapshot digests.
    - Calibration on the 50% calibration half: μ̂ and TTFT budget = 2 × unloaded p50 per length bucket.
    - Load points: ρ ∈ {0.5,0.8,1.0,1.25,1.6,2.0}×μ̂, 40 Poisson arrivals per block, ABBA arm order per ρ.
    - Denominator: every arrival; failures count as misses and quality 0; no retries.
    - Also draft the P-SERVE-SEL-1 annex entry + ratify script for the operator.
  - [ ] **DAR-LAT-3g — GATE (acquire, never observe):**
    - bus-granted whole-host window (INVARIANTS #8), because MEAS-6 forbids a concurrent CPU/GPU campaign;
    - `region-lock run --cpu-list 0-95 -- <driver>` (OPERATING_CONSTRAINTS.md:106) + MI210 lease;
    - AutoPilot quiesced by its owner; experiment API on its own port with a captured PID (production API untouched,
      :125);
    - host-health preflight (:110);
    - quiet-window preconditions (bench-cpu.md:59), checked via region holders and captured PIDs, never name patterns;
    - other servers sampled idle DURING each block;
    - live :8074 argv/env = the registered recipe incl. the OMP stack (bench-cpu.md:116);
    - VB-SEL-LOADAB wired.
  - [ ] **DAR-LAT-3b — Run W1** (calibration, then the arm sweep plus the 24 A1/A1 floor pairs). Stop on any
    prerequisite that fails during a block; re-queue the block, never drop it. Per-request receipts + raw outputs.
  - [ ] **DAR-LAT-3c — Holdout W2 (≥24 h later, ρ=1.25, ABBA, fresh seeds) + verdict.** PAIRED-CI-1 within a window
    only; W1 and W2 are never pooled (MEASUREMENT.md:434-438). Record the verdict and, on A2 loss, the BOUNDED-NULL-1
    power bound + positive-control readback.

**Default-weight flip (trigger prose, no checkbox).**
- Fires only when DAR-LAT-3c clears A1 (or A2) against A0.
- The flip is a routing-policy change. It needs an operator-signed instrument-era row (cf. E18) through consolidated
  ratification (MEASUREMENT.md:181), bundled with P-SERVE-SEL-1 if that is still pending.
- If A2 wins, the learned/live-predictor question declined in learned-routing-controller.md (C1-A4) reopens. An
  SFS-style engine simulator stays excluded by the frozen kernel (intake-1798#06).

**Mixture-of-agents trigger (prose, no checkbox).**
- Fires if DAR-6 swarm-fanout or any cross-model aggregation mode is re-authorized on the x_* surface.
- Before choosing cross-model mixing vs same-model multi-sample aggregation, dive intake-1799 and intake-1802 (both
  stage1-unverified; do not cite their numbers until dived).

**Code pointers as of orch @fb7871ea (dated note; the Key Files table above is historical).**
- Selection score: `_scalarized_selection_score` at `retriever.py:46-57`, called at :286-297 and :786-810.
- Prior blend: `hybrid_router.py:308-327`.
- Initial route: `routing_decision.py:259-314`.
```

**2. `handoffs/active/heterogeneous-slot-fabric-residency.md`.**
IDs checked: the handoff has no task IDs (only a `**P2` token at :139); `HSF-` is unused repo-wide, so the new series
starts at HSF-1.

(a) Nested spec bullets, no checkbox, inserted directly under the existing tasks. Under :147 (`- [ ] **Model-keyed
capability records …`):
```markdown
  - Card fields (2026-09-26, intake-1787#01, #03): `swap_cost_hot_s` {median, interval, n, receipt refs; filled by
    HSF-1} and `partial_offload_curve` {`-ngl` fraction → decode t/s}. Both are per (model, device), because offload
    sensitivity is model- and device-specific. They are model-keyed, never role-keyed.
```
Under :152 (`- [ ] **Layer-3** autopilot residency policy …`):
```markdown
  - Policy prior (2026-09-26, intake-1789#02):
    - When a swap to model B fires, admit queued and tracked B-eligible sessions as ONE group before any swap back.
    - The bound `swap_group_max` is policy data: bounded, reversible, sweepable per the conversion rule. Do not
      import Aegaeon's constant.
    - Turn boundaries only, under the existing drain protocol (:80-87). This amortizes C over the group without
      preemption.
```
(b) Append at EOF (after :230; last heading `## 2026-08-09 — async generation/execution split …` at :219):
```markdown
## Research Intake Update — 2026-09-26 (orchestration prior art: slot record, swap cost C, residency declines; intake-1783/1787/1789)

**Slot-record fields, schema only (c3-A2).** DAR-LAT-1 in decision-aware-routing.md is the single runtime
implementation; this handoff owns the schema. The fields use proposal-003 semantics (intake-1783#01), internal only:
- `queued` ← `llamacpp:requests_deferred`, falling back to ledger waiting.
- `running` ← `llamacpp:requests_processing`, falling back to ledger in_flight, cross-checked against `/slots` busy.
- `kv_occupancy` = Σ(n_prompt_tokens+n_decoded)/Σ n_ctx over processing slots (intake-1783#07).
- Every field carries a source label.
- KV is reserved at launch (contention rider :193), so `kv_occupancy` is context-fill, never memory pressure. For
  GDN-hybrid residents only the attention layers' KV scales with tokens; do not route on it for them.
- EPYC-only fields beside the three: `device_class`, `numa_node`/`cpuset`, residency state incl. `UNKNOWN`, co-tenant
  count, measured prompt/predicted t/s.
- Not an exporter and not an EPP feed: fronting with a GAIE EPP is declined (dynamic-stack-concurrency.md, 2026-09-26).

- [ ] **HSF-1 — Write a launch-phase receipt on every production GPU launch; it is the measured swap cost C per
  (model, MI210).**
  - Written from orch `orchestrator_stack.py` (GPU path :1259-1275) to
    `orchestration/reports/launch_phase/<role>-<UTC>.json`.
  - Timer from stderr: process start → `load_model` → `model loaded` → health → first token.
  - Also: effective argv, binary + kernel-store digest, GGUF sha256, `fincore` page-cache fraction before exec, and
    outcome class.
  - Fit rule: once each of ≥3 model sizes has ≥5 hot receipts (page-cache fraction ≥0.99; colder launches counted
    and labelled), fit C = a + size/b (intake-1787#03, intake-1789#04). Holdout is leave-one-model-out.
  - Write per-model C into the capability card (:147) and replace the illustrative C=20 s in N-dwell (:91-92).
  - Cold/post-reboot C stays gated (mi210-big-model-and-acceleration-roadmap.md:296).
  - Plan approval 2026-09-26 authorizes this item only; the rest of this list stays GATED.
- [ ] **HSF-2 — Add `--metrics` to CPU llama-server launch argv in the next stack-change package.** Today it is set
  only on the GPU path (orch `orchestrator_stack.py:1267`; live :8074 argv has none), so `queued`/`running` fall back
  to the ledger on CPU roles. Bundle with the next signed stack change; never an ad-hoc relaunch.

**Trigger (prose, no checkbox):** if HSF-1 has <5 hot receipts per model after 30 days, request a bus-granted GPU
window for a 5-launch series per model, with residents drained under the swap protocol by the stack-owning session.

**DECLINED — token/step-level GPU model multiplexing, Aegaeon-style (C5-A2; intake-1789#01, #03, #07).**
- It is mid-decode preemption, which axiom 4 forbids.
- It needs engine internals llama-server lacks: in-process component reuse, a host KV pool, IPC-event KV sync, and
  in-flight slot KV save (production v10 defers save/restore while a slot is processing, server-context.cpp:2593-2596).
- Prefetch-hiding needs VRAM for a second model beyond the ~58 GB 2-resident set (:65-66).
- The authors concede static multiplexing at strict SLOs, and the CPU fallback grid already absorbs the head-of-line
  blocking Aegaeon targets.
- Revisit only if a llama.cpp-experimental llama-server gains cooperative decode preemption
  (within-role-placement-state-machine.md:31).

**DECLINED — importing 2605.19593's absolute reload seconds or its "~2% overhead" into any EPYC cost model or dwell
calculation (C5-A5; intake-1787#02, #04).**
- Those figures come from single-request FP16 HF-Transformers on NVIDIA, with page-cache state unstated and a
  7,000-token-job denominator.
- Only the cost-model FORM transfers: a fixed penalty per (model, device). HSF-1 measures ours.
```

**3. `handoffs/active/contention-model-device-and-load-axes-rider.md`: append at EOF (after :307; last heading
`## 7. RATIFIED 2026-08-01` at :158).**
No checkbox; the rider's Q-series is operator questions, not tasks.
```markdown
## Research Intake Update — 2026-09-26 — llama-server capacity-signal map (C1-A5) + monitor triggers

**Signal map, from production v10 source (server-context.cpp@ffc1bac8:698-722, 903-908, 4720-4760, per the intake-1797 dive).**
- HW-Router's running/waiting counts map to `llamacpp:requests_processing` / `requests_deferred`. These exist only
  with `--metrics`, which CPU launches do NOT pass today (orch `orchestrator_stack.py:1267` is GPU-only; live :8074
  argv read 2026-09-26).
- KV-cache % has NO analogue: KV is preallocated per slot at launch (:193). The nearest signal is per-slot fill from
  `/slots` n_prompt_tokens + n_decoded vs n_ctx.
- TTFT/TPOT averages must come from counter deltas. `prompt_seconds_total/prompt_tokens_total` excludes queue wait.
  The `prompt_tokens_seconds` / `predicted_tokens_seconds` gauges are lifetime averages in v10, because
  `metrics_reset_bucket` is never set.
- Pending decode tokens are not exposed: `n_remain` is -1 without `n_predict`.
- v10 `/slots` does emit n_prompt_tokens, n_prompt_tokens_processed and n_prompt_tokens_cache. Deferred-request
  lengths are not exposed.
- Never wire a vLLM-shaped KV% or a lifetime gauge into routing (intake-1797#01, intake-1796#01, intake-1798#02).

**Where the soft load cost lives.** The per-request saturation guard is an instance of §7 Q1 ("soft cost, fail OPEN
with a penalty"). It is owned by decision-aware-routing.md DAR-LAT-1/2 and reads the orchestrator's own admission
ledger, not a second poller. No task here.

**Triggers (prose, no checkbox; both entries are stage1-unverified, so no figure from them may be cited until dived):**
- When Artifact 3 (interference cost) is parameterised with a batch-throughput lane in scope, dive intake-1812 first,
  as a candidate analytic prior for that lane.
- If fable5-window2-findings-02-heterogeneous-gpu.md F1 (:239) shows the overlap is worth pursuing, dive intake-1814
  before designing R-A5's async CPU backend. Any live device/PCIe load axis must reuse existing readers (Axiom 1).
```

**4. `handoffs/active/learned-routing-controller.md`: append at EOF (after :1757; last heading
`## 2026-09-26 audit follow-ups (code + live-process audit)` at :1748).**
No checkbox. The LRC phases past 1.5 are frozen (:4-5); these are declines plus a rollout precondition.
```markdown
## Research Intake Update — 2026-09-26 (orchestration prior art: declines + a rollout precondition)

**DECLINED — an HW-Router-style learned live latency predictor or an SFS engine-snapshot simulator for role
selection (C1-A4).**
- Neither was compared against a static latency prior. HW-Router's baselines are priced in money and it has no
  live-signal ablation (intake-1797#04); SFS has no static arm (intake-1798#04).
- SFS needs per-iteration engine snapshots from a forked server, which the frozen kernel forbids (intake-1798#06).
- Reopen only if decision-aware-routing.md DAR-LAT-3 adopts its live arm (A2).

**Already satisfied (C1-A6).** The routing classifier is one ~70K-param MLP forward at <1 ms (:583), not a serial
generative scorer. RouteBalance's deployment ladder (intake-1796#04) is a caution only if a generative scorer is ever
put on the /v1 hot path; then it must be batched or amortised.

**Rollout precondition (prose).** The MLP fast path (orch `hybrid_router.py:405-490`) returns before the selection
score. If `routing_classifier` is ever enabled (LRC-2), first apply the DAR-LAT-2 saturation guard as a post-check on
the fast-path result (around :411). Otherwise saturated roles bypass the guard.
```

**5. `handoffs/active/within-role-placement-state-machine.md`: append at EOF (after :421; last heading
`## Progress checklist` at :373).**
No checkbox. The ID series is `WP-*`/`J*`; none is added.
```markdown
## Research Intake Update — 2026-09-26 — replica load-cost reference (c3-A5)

- If replica choice ever gains a load term, use Dynamo's default worker cost as the checked reference (intake-1785#01):
  `prefill_load_scale·max(0, raw_prefill_blocks − overlap_credit_blocks) + (active_decode_blocks +
  incoming_active_blocks) + decode_active_request_weight·active_requests`, with lowest cost winning and optional
  softmax temperature for spread.
- The missing input: the overlap term needs per-slot prefix state, and llama-server offers only post-hoc
  `n_prompt_tokens_cache`, with no KV events (intake-1783#07). The per-slot inputs should come from the
  DAR-LAT-1 `SlotCapacity` record (decision-aware-routing.md).
- Trigger (prose): when that load term is actually designed, dive intake-1784 (llm-d router scorers;
  stage1-unverified) and map each scorer to this shape or to a named gap.
```

**6. `handoffs/active/dynamic-stack-concurrency.md`: append at EOF (after :342; last heading
`## Research Intake Update — 2026-08-23 …` at :259).**
No checkbox. If P1 appends a 2026-09-26 section here for c2-A1, the assembler merges this block into it.
```markdown
**DECLINED 2026-09-26 — fronting the orchestrator with a GAIE/llm-d Endpoint Picker (c3-A3; intake-1783#04–#07).**
- It is a Kubernetes/Envoy ext-proc stack for replicas of one model per InferencePool.
- llama.cpp is in neither the proposal-003 mapping nor llm-d-router's built-in engines, and there is no KV-util gauge.
- The reference LWEPP is round-robin, and heterogeneous accelerators are unbuilt.
- NUMA, residency and device class could only ride as untyped CustomMetrics.
- The orchestrator already sees more than the protocol can carry. The three gauges are adopted as internal
  slot-record fields instead (heterogeneous-slot-fabric-residency.md, 2026-09-26).
```

**7. Belief-kernel write-side wiring (CLAUDE.md "Belief Kernel — wiring new sources").**

(a) `handoffs/active/vidya-belief-substrate-program.md`: append at EOF (after :2961; last heading
`## VB-ROUTE-LAT / VB-UFH12-RETR / VB-TD-ADVICE …` at :2947).
IDs checked: the `SCnn` series (max SC89) and ~81 `VB-<TAG>` ids; `VB-SEL-LOADAB` and `VB-SWAP-C` are unused.
```markdown
## VB-SEL-LOADAB / VB-SWAP-C — selection load-sweep A/B and swap-cost receipts (filed 2026-09-26, research-intake)

Filed at design time, before either producer exists, per the CLAUDE.md belief-kernel rule. The source-table rows are
in `scripts/vidya/adapters/README.md`.

- [ ] **VB-SEL-LOADAB — wire the write side of the selection load-sweep A/B (decision-aware-routing.md DAR-LAT-3)
  before its first block.**
  - Per-request rows carry: arm, ρ, block, manifest/prior-table/episodic-snapshot digests, TTFT budget, outcome class,
    selection receipt, final role, grader verdict, and `instrument_class=serving`.
  - Locator = block (arm × ρ × window). Floor pairs are their own locators.
  - Project; do not grade. The grade comes from the protocol id (P-SERVE-SEL-1 once ratified, observation before that).
- [ ] **VB-SWAP-C — wire the write side of the launch-phase receipts (heterogeneous-slot-fabric-residency.md HSF-1).**
  - One launch = one locator, with GGUF/binary digests, argv hash, page-cache fraction, phase timings and outcome class.
  - Cold/partial-cache launches project with their label and never merge into hot C.
```
(b) `scripts/vidya/adapters/README.md`: two rows appended at the end of the source table (header
`| source | class | state | adapter |` at :193; insert after the last row, :321, "Typed routing as advice A/B"):
```markdown
| Selection load-sweep A/B (`decision-aware-routing.md` DAR-LAT-3: static prior + guard vs live term, single-instance saturating tier, TTFT-bound; `epyc-inference-research/data/sel-loadsweep-ab-*`) | measurement | **not wired; filed at design time, before the first block (2026-09-26).** Per-request rows bind arm, ρ, block, manifest/prior/episodic-snapshot digests, TTFT budget, outcome class (timeouts, 503/429 and admission errors are misses, never dropped), selection receipt and grader verdict, `instrument_class=serving`. **Locator = block**; W1 and W2 are separate windows and never pool. Task row: VB-SEL-LOADAB | none (planned) |
| MI210 launch-phase receipts (`heterogeneous-slot-fabric-residency.md` HSF-1: swap cost C per (model, device); orch `orchestration/reports/launch_phase/`) | measurement | **not wired; filed at design time, before the producer exists (2026-09-26).** One launch = one locator: GGUF + kernel-store digests, argv hash, `fincore` page-cache fraction, stderr phase timings, outcome class. Cold/partial-cache launches carry their label and never merge into the hot C. Task row: VB-SWAP-C | none (planned) |
```

---

### Stale-fact corrections
1. `handoffs/active/decision-aware-routing.md:18-19` and the Key Files table at :291-293 cite
   `retriever.py L225-368` and `selection_score = Q_value − cost_lambda·(expected_cost/cold_cost)`.
   - Evidence it is stale: orch @fb7871ea has the scalarized form at `retriever.py:46-57`, called at :286-297 and
     :786-810, plus the prior blend at `hybrid_router.py:308-327`.
   - Status line :3 declares the April body historical, so do not rewrite it. The fix is the dated "Code pointers as
     of orch @fb7871ea" note already included in edit 1.
2. No other stale lines in P2's scope. `:77`'s "~26 GB/s" belongs to C4-A2 in another section.

### Explicit declines
| Row | Decline, with reason | Recorded in |
|---|---|---|
| C1-A4 | Learned live predictor or SFS simulator: never compared to a static arm (intake-1797#04, intake-1798#04); needs a forked engine (intake-1798#06). Reopen only if DAR-LAT-3's A2 arm wins. | LRC, edit 4 |
| C1-A6 | Already satisfied: an MLP under 1 ms (LRC :583). Only a caution if a generative scorer is added. | LRC, edit 4 |
| c3-A3 | EPP fronting: K8s/Envoy, no llama.cpp engine or KV gauge, round-robin reference, untyped CustomMetrics. | DSC, edit 6 |
| C5-A2 | Aegaeon token-level multiplexing: axiom 4, missing engine internals, VRAM, authors' own strict-SLO concession. Revisit trigger recorded. | fabric, edit 2b |
| C5-A5 | Importing 2605.19593's absolute seconds or overhead: FP16 HF on NVIDIA, cache state unstated. Only the form transfers. | fabric, edit 2b |
| intake-1788 (Stage-1) | Harvest AIBrix routing taxonomy + DRAM KV-pool eviction: the taxonomy is subsumed by the dived 1796/1783 records and DAR-LAT-2. A host KV pool needs engine internals llama-server lacks (the C5-A2 code fact). No work; knowledge_only. | intake entry only |
| intake-1802 (Stage-1) | Superseded; provenance only. The MoA trigger prose (edit 1) names it as reading before any cross-model aggregation mode. | intake entry + edit 1 prose |
| intake-1804 (Stage-1) | "Post-and-volunteer" dispatch next to the router: idle-slot pull-claiming must be argued from slot-fabric and contention evidence, not borrowed (the same ruling as 6-A3). No immediate action; knowledge_only. | intake entry only |

### New stubs + index rows
- **No new stubs.** Every item amends an existing owner.
- **Proposed row edit (routing-and-optimization-index.md, header `| ID | Track | Handoff | Next action | Deps |` at :11):**
  change RTG-09's `Next action` to
  `DAR-LAT-1 — build SlotCapacity + expected_wait_s on the admission ledger; then DAR-LAT-2 weight-0 selection terms`
  (113 chars). DAR-5 stays open in the handoff.
  - Optional Deps edge: none. RTG-11 (P1 Retry-After) should carry `RTG-09` in its Deps if P1 consumes DAR-LAT-1;
    the assembler applies that on P1's row.
- **INF-23 (heterogeneous-slot-fabric-residency) row:** unchanged. HSF-1 is passive instrumentation. If the assembler
  prefers discoverability, replace the next action with
  `HSF-1 — emit launch-phase receipts on production GPU launches; fit swap cost C when ≥5 hot receipts × ≥3 models`
  (≤140 chars).
- **Master index, operator queue:** one row if the operator does not settle it in plan approval:
  `| OP-<next> | Ratify P-SERVE-SEL-1 (text-LLM selection load-sweep protocol, drafted in DAR-LAT-3a) before DAR-LAT-3 W1, or accept observation grade for the A/B | [decision-aware-routing.md](decision-aware-routing.md) | 2026-09-26 |`

### Intake-entry dispositions (Stage 4 sets)
| Entry | handoffs_updated | disposition | disposition_evidence (one line) |
|---|---|---|---|
| intake-1796 | decision-aware-routing.md, learned-routing-controller.md, contention-model-device-and-load-axes-rider.md | integrated | Static per-tier prior + dead-reckoned guard adopted as DAR-LAT-1/2 (weight 0) with the DAR-LAT-3 load-sweep A/B. |
| intake-1797 | contention-model-device-and-load-axes-rider.md, learned-routing-controller.md, decision-aware-routing.md | knowledge_only | Signal map recorded in the rider; the live-predictor build is declined (C1-A4) with a DAR-LAT-3 reopen trigger. |
| intake-1798 | decision-aware-routing.md, learned-routing-controller.md, contention-model-device-and-load-axes-rider.md | integrated | Its single-instance, TTFT-bound regime defines the DAR-LAT-3 experiment; the SFS simulator is declined (frozen kernel). |
| intake-1783 | heterogeneous-slot-fabric-residency.md, dynamic-stack-concurrency.md, within-role-placement-state-machine.md | integrated | Proposal-003 gauges adopted as internal slot-record fields (schema + DAR-LAT-1 runtime); EPP fronting declined. |
| intake-1785 | within-role-placement-state-machine.md (P2 part only) | set by the section owning c3-A1/c3-A4 | P2 contributes only the c3-A5 knowledge note; do not set the disposition from P2 alone. |
| intake-1787 | heterogeneous-slot-fabric-residency.md | integrated | Cost-model form adopted as HSF-1 swap-cost receipts + capability-card fields; absolute seconds declined (C5-A5). |
| intake-1789 | heterogeneous-slot-fabric-residency.md | knowledge_only | Token-level multiplexing declined (axiom 4); only the group-by-model admission prior is kept, as a gated Layer-3 spec. |
| intake-1784 | within-role-placement-state-machine.md | monitor | The dive is triggered when a replica load term is designed (within-role note, 2026-09-26). |
| intake-1788 | — | knowledge_only | Taxonomy subsumed by the dived 1796/1783 records; the DRAM KV pool needs engine internals llama-server lacks. |
| intake-1799 | decision-aware-routing.md | monitor | Dive before any cross-model aggregation mode (DAR-6 re-authorization trigger). |
| intake-1802 | decision-aware-routing.md | knowledge_only | Superseded (Self-MoA); named as reading in the DAR MoA trigger. |
| intake-1804 | — | knowledge_only | Pull-claiming dispatch must be argued from slot-fabric evidence (6-A3 ruling); no action. |
| intake-1812 | contention-model-device-and-load-axes-rider.md | monitor | The dive is triggered when Artifact 3 is parameterised with a batch-throughput lane in scope. |
| intake-1814 | contention-model-device-and-load-axes-rider.md | monitor | The dive is triggered if fable5 findings-02 F1 justifies R-A5 async-CPU-backend design. |

### Coverage table
| Row | Maps to |
|---|---|
| C1-A1 | DAR-LAT-2 (prior) + DAR-LAT-3 (A/B) |
| C1-A2 | DAR-LAT-1 (ledger/wait) + DAR-LAT-2 (guard); owner re-routed from the rider to DAR (one owner for a4) |
| C1-A4 | decline (edit 4), reopen trigger = DAR-LAT-3 A2 win |
| C1-A5 | knowledge-only record (edit 3) |
| C1-A6 | decline, already satisfied (edit 4) |
| c3-A2 | schema record (edit 2b) + DAR-LAT-1 runtime + HSF-2 |
| c3-A3 | decline (edit 6) |
| c3-A5 | knowledge-only record (edit 5) |
| C5-A1 | HSF-1 + VB-SWAP-C |
| C5-A2 | decline + revisit trigger (edit 2b) |
| C5-A3 | spec bullet under :152 (edit 2a) |
| C5-A4 | spec bullet under :147 (edit 2a); C field filled by HSF-1 |
| C5-A5 | decline (edit 2b) |
| intake-1784 | monitor trigger (edit 5) |
| intake-1788 | decline / knowledge_only |
| intake-1799 | monitor trigger (edit 1) |
| intake-1802 | knowledge_only (edit 1 prose) |
| intake-1804 | decline / knowledge_only |
| intake-1812 | monitor trigger (edit 3) |
| intake-1814 | monitor trigger (edit 3) |

### Cross-section flags (for the assembling session; not operator questions)
- **Live recipe drift on the tier under test.**
  - Live `:8074` runs `-t 96` (ps, 2026-09-26). The registry recipe block says `threads: 48` (orch
    `model_registry.yaml:1899-1904`), and the codified recipe says `THREADS = 48  # NOT 96: the served decode optimum`
    (`qwen38_flash_next_recipe.py:690`).
  - The stack template carries `threads: 96` (`stack_templates/default.yaml:155`), which is the likely source.
  - The production `n_ctx` 262144 also differs from the recipe's validated 8192.
  - DAR-LAT-3g fails until the drift is reconciled. The fix is a production launch change, so it goes through the
    `stack-change` package (the owner of the lineup and recipe is not P2).
- **P1 ↔ P2 edge.** DAR-LAT-1 is the shared primitive for c2-A1's Retry-After (see the assembler note at the top).
- **C4 section.** The intake-1814 trigger in edit 3 points at findings-02 F1. If C4 edits that rider, it may
  cross-reference the trigger rather than restate it.

### Open questions for the operator
1. **Ratify P-SERVE-SEL-1 (drafted in DAR-LAT-3a) before W1, so the A/B is decision-grade, or accept observation grade
   for a result that would drive a default-weight flip?** The measurement trust boundary is human-amendment-only
   (INVARIANTS.md:38, #15). Recommendation: ratify, bundled into one command with any other pending ratification.
   This decision blocks only the claim grade. DAR-LAT-1/2/3a, HSF-1 and the VB wiring proceed regardless.

---

## P3 — Hybrid CPU/GPU MoE, OD-A (KTransformers), and hardware-fact corrections

Drafted 2026-09-26 against the lane worktree `/mnt/raid0/llm/worktrees/intake-orch-prior-art-20260926` @ `33e82ae3`
(merged with origin/main `5302d271`). Every `file:line` below is a lane line. Read-only cross-repo pins:
epyc-orchestrator `fb7871ea`, epyc-inference-research `2a060a41`. Quotable sources: intake-1808/1809/1810
(dive-verified). intake-1811/1813 are stage1-unverified: this section cites them only as `#record` and
quotes none of their numbers.

**Program shape (3 packets, fewer than 5 by design).** After compression, P3's ledger leaves three
independent units. Splitting further would only split doc edits by file.

| Packet | Items | Compute | Can run alongside |
|---|---|---|---|
| **K1: corrections + design priors** (zero compute) | P3-1, P3-2, P3-4, P3-6, P3-7 | none | everything (each item edits a different file) |
| **K2: prefill crossover** (compute) | P3-3 (+ its VB write-side hook first) | full-box CPU plus the MI210 | K1 only. It must not overlap K3: a build on the box poisons a bench. |
| **K3: kt-kernel build check** (build, operator-gated) | P3-5 | isolated build | K1 only. Never inside K2's region claim. |

P3-2's rule is design text that can land now. Its inputs come from P3-3. NPD-1 (P3-1) depends on P3-3's
outcome. P3-5 depends on the operator's OD-A answer.

### Plan items

#### P3-1 — Re-scope the NUMA disaggregation stub to GPU-prefill / CPU-decode, correct its topology, re-point its blocker

- **Project decision:** whether prefill/decode disaggregation has any regime on this host (INF-44). Today the stub's only falsifier (xGMI KV transfer) rests on a topology the host does not have. So the stub sits BLOCKED on a test that cannot run, even though its reopen trigger has already fired: `sarathi-serve-cpu-evaluation.md:12` records the multi-tenant/eval-batch trigger as materialized on 2026-07-18.
- **Sources / ledger rows:** intake-1810#02 (intra-node GPU-prefill / CPU-decode, one shared DRAM weight copy, `<2K` chunked, decode batched to a target, KV handoff not addressed); C4-A1.
- **Primary owner:** `handoffs/active/numa-prefill-decode-disaggregation.md`. Frozen/pointer check: `**Status**: stub` (:3). It is neither frozen nor a pointer, and the only checkbox is :76.
- **Posture:** `knowledge-only` for the re-scope and the corrections. The disaggregation experiment itself is `monitor`: it is durable trigger prose, not a checkbox, until P3-3 reports.
- **Reusable primitive:** a corrected feasibility frame. Its key design fact is that llama.cpp op-offload already runs GPU prefill and CPU decode **inside one process**: KV stays in host RAM, there is one weight copy, and experts are streamed to the MI210 per ubatch at `ubatch ≥ 32` (`fable5-window2-findings-02-heterogeneous-gpu.md:165-167`). So on this host the 1810 split needs no KV handoff unless the work is split across processes.
- **Consumers:** `inference-research-index.md:53` (INF-44 row, prepared below); `sarathi-serve-cpu-evaluation.md` (INF-49, which owns the CPU-only phase-specialisation question: evidence consumer, gets a dated note, see corrections); `dynamic-stack-concurrency.md` (named analogue; no task). Search: `xgmi|2-socket|8-NUMA|inter-socket|two-socket` over handoffs/active, wiki, agents, docs/reference; `op-offload|cmoe|ncmoe` over handoffs.
- **Immediate deliverables (paste-ready; the file has no task-ID scheme; checked: zero IDs in the file, external aliases are CPU16 at `sarathi-serve-cpu-evaluation.md:8`, C55 at `design-backlog-triage-2026-07-23.md:150`, and INF-44; new wave-local prefix `NPD`):**
  1. Insert after :10 (below the `**Hygiene note (2026-05-27)**` line):
     > **Correction 2026-09-26 (research intake `intake/orch-prior-art-20260926`, `intake-1810#02`):** this stub's topology premise is wrong for this host. The EPYC 9655 host is **one socket, NPS4 = 4 NUMA nodes** (`lscpu`: `Socket(s): 1`, `NUMA node(s): 4`, captured 2026-09-26 in `/mnt/raid0/llm/tmp/dive-intake-1810/sources/host_lscpu_20260926.txt`). There is **no xGMI inter-socket link**, so the Phase 0 xGMI KV-transfer falsifier cannot run as written. Between NPS4 nodes, KV in DRAM stays addressable from every node: there is no copy to make, only a remote-node read penalty. The disaggregation that stays live here is the one intake-1810 measures: **GPU prefill vs CPU decode** over one DRAM-resident weight copy. llama.cpp's op-offload already does that split inside one process (KV in host RAM, experts streamed per ubatch, `fable5-window2-findings-02-heterogeneous-gpu.md:165-167`). The open question is therefore whether a *separate* prefill instance ever beats it. The multi-tenant reopen trigger is already recorded as fired (`sarathi-serve-cpu-evaluation.md:12`, 2026-07-18).
  2. Replace :14 (Objective) with:
     `Evaluate whether prefill/decode disaggregation yields net throughput-under-SLO gains on this host — one EPYC 9655 socket (NPS4, 4 NUMA nodes) plus one MI210 — in the form intake-1810 measures: long prefill on the GPU with weights streamed from DRAM, decode on the CPU against the same DRAM-resident weight copy, short prompts prefilled on the CPU. *(Re-scoped 2026-09-26; the original 2-socket / 8-node / KV-over-xGMI premise does not match the host — see the correction note above.)*`
  3. Replace the parenthetical at :8 and the `4×48t` clause at :40 (quarters retired 2026-07-30, `numa-topology-cutover-resume-20260730.md:96-102`; the live shapes are full `-t 96`, half A `-t 48`, half B `-t 48`):
     :8 → `(the live CPU shapes are one full 96t instance and two 48t halves per quarterable role — quarters retired 2026-07-30, numa-topology-cutover-resume-20260730.md:96 — the closest existing analogue)`;
     :40 → `- (a) the existing stack shapes (one full 96t prefill-favorable instance + two 48t halves), which is already a soft form of phase specialization, AND`
  4. Add to the Research Context table (:20-26):
     `| intake-1810 | Cloud-grade-SLO MoE serving on dual EPYC 9355 + 2× RTX 5090 (OSDI'26) | adopt_patterns | dive-verified. Long prefill → GPU weight streaming, decode → CPU over ONE shared DRAM weight copy, <2K chunked, decode batched to a target (intake-1810#02). Its 4K switch is a policy on an unquantified PCIe 5.0 link, not a crossover (intake-1810#01). The disaggregated form dedicates a GPU to prefill; KV handoff not costed. No code released. |`
  5. Mark item 5 at :34 void in place by appending: ` *(Void on this host, 2026-09-26: single socket, no xGMI — see the correction note. The link that matters is PCIe Gen4 x16 to the MI210, measured H2D 28.89 GB/s, gpu-acceleration-path.md:313-316.)*`
  6. Replace the Phase 0 section heading at :53 with `## Proposed Phase 0 — re-scoped 2026-09-26 (original xGMI test void on a 1-socket host)`. Replace :55-60 with:
     `Phase 0 is the CPU-vs-MI210 prefill crossover, owned by mi210-big-model-and-acceleration-roadmap.md PF1 (not duplicated here). The superseded xGMI steps asked for inter-socket KV-transfer bandwidth; there is no inter-socket link on this host.`
     `**Reopen trigger (durable, no checkbox until it fires):** PF1 reports a GPU-prefill regime (L* ≤ 32K). Then NPD-1: on the served over-HBM MoE, measure decode TPOT inflation while ONE concurrent long prefill runs through in-process op-offload (the interference 1810 disaggregates away; CPU23 measured 9.6× first-decode TTFT amplification under concurrent CPU prefill, sarathi-serve-cpu-evaluation.md:110). Spec a separate prefill instance only if the inflation exceeds a bound predeclared in that run's manifest. If PF1 finds no regime ≤ 32K, close this handoff's GPU branch; the CPU-only question stays with INF-49.`
  7. Replace :76 with:
     `- [ ] BLOCKED on mi210-big-model-and-acceleration-roadmap.md PF1 (CPU-vs-MI210 prefill crossover); the xGMI falsifier is void on a 1-socket host (2026-09-26); then NPD-1 per the reopen trigger, or close the GPU branch`
- **Rigor controls:** N/A (documentation). Conformance checks: `index_state.py --check` exits 0 after the row edit; grep `xGMI` in this file returns only the struck/void mentions.
- **Dependencies:** none for the edits; NPD-1 depends on P3-3.
- **Broader trigger / if unfired:** as stated in deliverable 6.

#### P3-2 — Computable prefill-placement rule in the fabric, with the measured H2D link

- **Project decision:** how the capacity-aware scheduler places a long prefill of a DRAM-resident over-HBM MoE, CPU vs GPU streaming. Today the only threshold in circulation is 1810's 4K. That is a policy on a link the paper never quantifies, and a crossover is not judgeable from it (intake-1810#01).
- **Sources / ledger rows:** intake-1810#01, intake-1810#02; C4-A2.
- **Primary owner:** `handoffs/active/heterogeneous-slot-fabric-residency.md`. Frozen check: `**Status (2026-07-20): DESIGN — GATED**` (:18). Design text is allowed. The task list says "all GATED" (:144), so the new box is explicitly design/input-filling only.
- **Posture:** `primitive-now` (rule text with named inputs). The inputs are filled by P3-3.
- **Reusable primitive:** `T_cpu(L) = L / R_cpu(L)` vs `T_gpu(L, ub) ≥ S(L, ub) / B_h2d`. It is useful even if GPU streaming never wins, because it states *why* CPU prefill is the default.
- **Consumers:**
  - `within-role-placement-state-machine.md`: the Layer-1 dispatcher. Prospective consumer; no task until the rule has measured inputs.
  - `decision-aware-routing.md`: the T_hat prefill term. Prospective consumer; it reads the R_cpu(L) table.
  - `contention-model-device-and-load-axes-rider.md` / orch `src/scheduling/device_model.py`: prospective. It carries no PCIe constant today; searched `pcie|h2d|link_bw` in `src/scheduling/` and found 0 hits.
  - `gpu-serving-tie-in-program.md`: prospective. Hosting a streaming-prefill instance is a GPU-slot (Layer 2) decision.
  - Search terms: `prefill.*threshold|predicted_prefill` in orch `src/` (0 hits); `~26 GB/s|26 GB/s` in handoffs/wiki (fabric :77 plus two historical mentions).
- **Immediate deliverables:**
  1. Replace at :77 `(HBM ~1.6 TB/s vs PCIe ~26 GB/s, ~60×)` → `(HBM ~1.6 TB/s vs PCIe Gen4 H2D 28.89 GB/s measured 2026-08-03, epyc-inference-research/data/mi210-h2d-d2h/20260803T131500Z/, ~55×)`
  2. Insert after :78 (end of the "Teleport = re-prefill (v1)" paragraph), under `## Core mechanisms` (:61):
     `**Prefill placement rule — candidate (2026-09-26, research intake; design-only, inputs unmeasured).** For an over-HBM MoE whose weights stay DRAM-resident (one weight copy; the GPU never holds the model), send a prompt of length L to a GPU streaming path only if T_gpu(L) < T_cpu(L). Here T_cpu(L) = L / R_cpu(L) (CPU prefill rate at length L, on the served artifact and the production recipe) and T_gpu(L) ≥ S / B_h2d, with B_h2d = 28.89 GB/s measured (34.6 ms per streamed GB). S is what the path streams. For llama.cpp op-offload (the path we have), S = ceil(L/ub) × W_offloaded, because offloaded weights are re-sent every ubatch (hypothesis; PF1 tests it). For a stream-once-per-prompt design (1810's SLP; no code released), S = W_experts once. Consequence: -ub is a first-class knob of the rule, not a detail. Do NOT carry 1810's 4K switch: it is a policy on a PCIe 5.0 link whose bandwidth the paper never states (intake-1810#01). Precondition: a GPU slot is free to host the streaming instance, which is a Layer-2 decision; Layer 1 can only route to an instance that already exists. Inputs are bench-class (llama-bench) until a serving-class confirmation exists.`
  3. Add to `## Task list (all GATED — post-v7-promotion + post-E5; nothing starts before then)` (:144), after :153. The list has no ID scheme (checked :145-153, bold titles only), so this uses bold-title style:
     `- [ ] **Prefill placement rule — fill R_cpu(L) and R_gpu(L, ub) from mi210-big-model-and-acceleration-roadmap.md PF1, then decide whether Layer 1 gets a length threshold** (design only; blocked on PF1)`
- **Rigor:** N/A (design text); the numeric inputs carry PF1's six controls.
- **Dependencies:** deliverables 1-2 have none; deliverable 3 closes on P3-3.

#### P3-3 — PF1: measure the CPU-vs-MI210 prefill crossover for the served over-HBM MoE (full rigor)

- **Project decision:** whether *any* prompt length ≤ 32K prefills faster through the MI210 than on the CPU for the model production actually serves over HBM. That result sets P3-2's rule, P3-1's reopen, and the operator's "long prefill → GPU" scheduler thesis. The existing evidence does not answer it. M3 (`fable5-window2-findings-02-heterogeneous-gpu.md:61`) measured op-offload at pp1024 only, on an 80B that *fits* HBM. The post-BIOS CPU prefill point (pp512 t48 203.30 ± 0.75 t/s, `progress/2026-09/2026-09-21.md:111`) is on the uniform research artifact with build 10151, not the served file or v10.
- **Sources / ledger rows:** intake-1810#01; C4-A3.
- **Primary owner:** `handoffs/active/mi210-big-model-and-acceleration-roadmap.md`. Status (:3) is `STRATEGIC THREAD … every step is experimental-HOLD`; that is not frozen, and it accepts dated intake sections (:273, :280, :300, :312).
- **Posture:** `cheap-screen-now`. It uses existing production binaries, needs no build, and adds no code beyond a recipe entry.
- **Reusable primitive:** a length × ubatch prefill table R_cpu(L), R_gpu(L, ub) for the served artifact on v10, with a codified sweep entry. It is useful whichever arm wins: it is the input to P3-2, to AXA-2's re-prefill cutover cost, and to `cpu-prefill-compute-large-models.md` (the first post-BIOS CPU prefill-vs-length curve on a served MoE).
- **Consumers:**
  - direct: P3-2's rule.
  - evidence: `cpu-prefill-compute-large-models.md`; the belief kernel (VB-PREFILL-XOVER below).
  - policy: P3-1's NPD reopen.
  - prospective: `decision-aware-routing.md` (T_hat), AXA-2 (`mi210-big-model-and-acceleration-roadmap.md:285`), `gpu-serving-tie-in-program.md`.
  - Search: `op-offload|GGML_OP_OFFLOAD_MIN_BATCH|cmoe|ncmoe` over handoffs, research `scripts/`, orch `src/`. Only bench runners were found. **Defect found:** `epyc-inference-research/scripts/benchmark/cpu_prefill_v8_regression_runner.py:36-39` hardcodes `/mnt/raid0/llm/llama.cpp/build/bin/llama-bench`. That binary serves nothing under v10 (CLAUDE.md), so PF1 must NOT reuse the runner unrepointed.
- **Immediate deliverable.** Append a new section at EOF (after :404) of the roadmap. The ids are wave-local per the convention at :314, and the classes follow :315-316. Existing ids checked: K28, AXA-1..3, DR-3*, B3, B5, G15, G15a; G16 is external.
  ```
  ## Research Intake Update — 2026-09-26 (intake-1810 / 1808 / 1809: CPU-vs-MI210 prefill crossover)

  Row ids are wave-local (`PF` = prefill) and do not continue earlier sections; classes Z/G/B as at :315-316.

  **Computed prior (Z — not a measurement).** llama.cpp op-offload re-sends offloaded weights every ubatch (hypothesis). The served
  Qwen3.8-Flash-Next UD-IQ4_XS is 93.68 GB (3 shards, 87.25 GiB); at the measured 28.89 GB/s H2D that is a 3.24 s transfer floor per ubatch,
  i.e. ≤ ~158 tok/s at -ub 512, ≤ ~632 at -ub 2048, ≤ ~1263 at -ub 4096. The CPU reference is pp512 t48 203.30 t/s (post-BIOS, uniform
  research artifact, build 10151 — 2026-09-21.md:111). So -ub decides whether a crossover can exist at all. The prior is falsified if an
  op-offload arm at -ub 512 exceeds ~158 tok/s on this file. `intake-1810#01`.

  - [ ] **PF1 (G) — measure the CPU-vs-MI210 prefill crossover for the served over-HBM MoE.** Artifact = the served
        Qwen3.8-Flash-Next UD-IQ4_XS (sha256 of all 3 shards in the manifest). Production v10 binaries from the kernel store,
        no build. Arms: A0 CPU incumbent (`kernels/production/cpu`, canonical_recipe.py); A1 GPU op-offload `-ngl 0`
        (default threshold 32); A2 `-ngl 99 -cmoe`; plus one A1-with-offload-disabled control
        (GGML_OP_OFFLOAD_MIN_BATCH=2147483647) to separate the binary from the offload. L ∈ {1K, 2K, 4K, 8K, 16K, 32K},
        GPU -ub ∈ {512, 2048, 4096}, -n 0, r=5; the A0 L=2048 cell at P-BENCH-PREFILL-1 (r=10).
        Rule: L* = smallest L where the best GPU arm's median ≥ 1.10× A0 at that L with non-overlapping 95% CIs,
        reproduced in a later-window reversed-order replicate. Results feed the fabric prefill rule and the
        numa-prefill-decode-disaggregation.md reopen trigger. Bench-class: this authorizes no serving change.
  ```
- **Frozen input manifest:** artifact path + 3 shard sha256; binary paths resolved through `kernels/production/{cpu,gpu}` with `verify_llama_cpp.sh` + `verify_kernel_store.sh` passing and binary/.so sha256 recorded; `llama-bench` `build:` line (`10303` expected); argv + env per cell; the L/ub/arm grid; the manifest's own sha256 written before cell 1.
- **Incumbent baseline:** A0 is exactly what production does today (all prefill on the CPU, v10, canonical recipe).
- **Per-item raw outputs:** llama-bench JSON per (arm, L, ub, rep) with `samples_ts`, plus the following captured during each cell:
  - `rocm-smi` VRAM/clock samples at ≥1 Hz. llama.cpp dlopens `libggml-hip.so`, so a non-zero VRAM reading is the only proof of a GPU run.
  - KFD process count;
  - `numastat -p`;
  - the P-BENCH-PREFILL-1 `/proc/stat` contention samples.
  - Plus `verify_ggml_linkage.sh` for the GPU binary. Everything lands in `epyc-inference-research/data/prefill-crossover-<UTC>/` with `SHA256SUMS` + `receipt.json`.
- **Holdout:** a later-window replicate (a different session, ≥4 h later, reversed arm order). It runs at the two L values bracketing L*, or at 8K and 32K if there is no crossover. The rule counts only if the replicate agrees in sign. Arms are interleaved within each rep block, never blocked (host drift ~3%/h).
- **Complete denominator:** every planned cell (4 arms × 6 L × ub grid × reps) is reported. OOM, load failure, timeout and op-fallback warnings are counted as failed cells with their reason. A crossover claim requires zero failed cells at the bracketing L.
- **Predeclared decision rule:**
  - If L* ≤ 32K and it is reproduced: write the R table into P3-2, tick its box, and fire P3-1's NPD-1.
  - If there is no L* at any ub: record "no GPU-streaming prefill regime ≤ 32K for the served over-HBM MoE on this host (v10)". P3-2's rule stays documented with a CPU default, and P3-1's GPU branch closes.
  - Either way the result is bench-class, not a serving claim. The GPU arms are P-GPU-1 decision-grade only if every P-GPU-1 evidence field is captured (v10 is production-named).
- **Region-claim / quiet-window prerequisite:**
  - The run needs **all 96 cores (q0–q3) and an idle MI210 at the same time**. Request the compute window via the bus (invariant 8), then acquire `region-lock` q0–q3. `bench_canonical.sh` acquires the CPU claim itself and refuses to run unlocked.
  - Verify the MI210 is idle before cell 1: KFD process count 0, and VRAM at its baseline, sampled twice.
  - If a production quarter or the GPU lane holds either resource, PF1 waits. Acquiring the claim is the gate; no human gate applies (no `operator_gates[]` trust boundary is touched).
  - Host-health preflight: the uptime rule; `drop_caches` + `numactl --interleave=all` re-warm; per-node free memory ≥ the artifact's per-node share before load. Placement alone moved prefill −30% (`cpu-decode-roofline-program.md:142`).
- **Freeze constraints:** run the frozen v10 binaries unmodified; no build; no edit to `/mnt/raid0/llm/llama.cpp` or `kernels/`. Set `LD_LIBRARY_PATH` per binary and prove the ggml linkage (three ggml generations on the host).
- **Belief-kernel write side (CLAUDE.md, before the first cell):**
  1. In `scripts/vidya/adapters/README.md`, append to the source table (the table holding the `llama-bench sweeps` row at :232):
     `| MI210/CPU prefill crossover sweep (PF1, mi210-big-model-and-acceleration-roadmap.md; epyc-inference-research data/prefill-crossover-<ts>/) | measurement | **prospective — write-side hook filed 2026-09-26 BEFORE the first cell (VB-PREFILL-XOVER).** One self-hashed record per (arm, L, ub, rep): binary digest, build line, protocol id (P-BENCH-PREFILL-1 for A0 L=2048; P-GPU-1 fields for GPU arms; observation otherwise), VRAM-during-run samples. |`
  2. In `handoffs/active/vidya-belief-substrate-program.md`, append at EOF a new section in the current `## VB-… (filed …)` convention (checked: the last is `## VB-ROUTE-LAT / … (filed 2026-09-26)` at :2947; `VB-PREFILL-XOVER` is unused):
     `## VB-PREFILL-XOVER — CPU-vs-MI210 prefill crossover records (filed 2026-09-26, research intake)`
     `- [ ] **VB-PREFILL-XOVER — wire PF1 on the WRITE side before its first cell runs.** Emit one self-hashed ClaimTuple-shaped record per cell (artifact + binary digests, build line, protocol id or observation, n, date, VRAM-during-run witness, failure reason when failed) into the PF1 run dir; no read-side reconstruction.`
     Re-verify both ids against origin/main at apply time: a /workspace working copy has uncommitted edits to this file.
- **Dependencies and concurrency:** VB-PREFILL-XOVER comes first. PF1 may share one claimed window with rider F1, which also uses static `-cmoe`, but the two are not merged. PF1 must not overlap P3-5's build.
- **Broader trigger:** DeepSeek-V4.1-Flash-Q4 (519 GB, the 1810-class model) is excluded from PF1: it is not served and its window is held behind OP-53. *Monitor:* rerun the PF1 grid on it when DS41 becomes a served role or holds a claimed window. This stays as prose only.

#### P3-4 — Correct the OD-A rider's premises and install the decision package (no decision taken)

- **Project decision:** OD-A itself. The operator should decide on corrected premises. Today the rider carries these stale facts:
  - F3 "no measured H2D/D2H";
  - #1612 "unanswered";
  - M2 "still unrun";
  - "`rocm-bandwidth-test` not installed";
  - the gpu-acceleration-path sweep box;
  - the HumanEval "single-run" wording;
  - "460 GB/s CPU pool".

  It also relies on the overturned intake-923 "no AVX-512-native MoE operator family". OD-A is not in the master operator queue at all: `master-handoff-index.md:31-51` has no OD-A row.
- **Sources / ledger rows:** intake-1809#01, #03; intake-1808#01, #03, #04; intake-1810#05; C4-A4, C4-A5.
- **Primary owner:** `handoffs/active/fable5-window2-findings-02-heterogeneous-gpu.md` (index row EVL-20, `research-evaluation-index.md:29`). It is not frozen. The body is a findings deliverable, so corrections are appended or dated per the rider's own convention: `Nothing here reverses a verdict in this document` (:80-82) and the 1793659d italic note at :99 / :248.
- **Checkbox ownership:** the rider's boxes were filed by `mainA` (:80). Per SESSION_LIFECYCLE *Two axioms* / invariant 9, Stage 4 does **not** flip F3 (:242), M2 (:244) or the gpu-acceleration item (:257). It writes dated stale-notes, which is allowed, and posts one bus item (own outbox, `corr_id`) asking the rider owner to flip them, routed via the coordinator if mainA no longer holds EVL-20. **Exception:** main's 1793659d note says of the OD-A box "box left for that session" (:248-249), which delegates that box to this intake session. Operator approval of this plan is the approval for that flip.
- **Posture:** `knowledge-only` (a corrected decision package plus a queue row).
- **Reusable primitive:** the R-A10 decision package (options, tradeoffs, recommendation, one-sentence decision). Every clause is anchored to dive-verified claims.
- **Consumers:**
  - policy: `master-handoff-index.md` operator queue, and `mi210-big-model-and-acceleration-roadmap.md:40`, the OD-A evidence rider (it reads the package; no task).
  - evidence: intake-923 (dive_corrections append, see dispositions).
  - Search: `OD-A|KTransformers` in handoffs/active (hits: this rider and roadmap :40 only).
- **Immediate deliverables:**
  1. Under `### R-A7. Falsifiers — what would kill this` (:197), append after :210:
     `  *Note 2026-09-26 (research intake):* the "no measured H2D/D2H" clause is stale — H2D 28.89 / D2H 28.20 GB/s were measured 2026-08-03 with rocm-bandwidth-test 2.6.0 (receipt epyc-inference-research/data/mi210-h2d-d2h/20260803T131500Z/, commit 2aa14264; gpu-acceleration-path.md:313-330), and the fabric's "~26 GB/s" is now at heterogeneous-slot-fabric-residency.md:77. That receipt's smallest transfer is 1 MB, so the per-crossing small-message latency this falsifier names is not in it; F1's per-split timing (t_d2h + t_h2d) measures it in situ.`
  2. After :223 (the vendor-risk paragraph in R-A7), append:
     `*Note 2026-09-26:* #1612 is open but was answered the same day by a repo COLLABORATOR (KMSorSMS, 2025-11-15: "Yes, we can try AMD's CPU with AVX512 support right now"), intake-1809#record. On ROCm: gfx90a appears in kt-kernel source only as an arch-family macro (kt-kernel/cpu_backend/vendors/hip.h:160) — still no evidence of gfx90a testing or use; the torch==2.9.1 exact pin holds on x86_64 (a PyPI CUDA build; the cu130 index applies to aarch64 only). intake-1809#03.`
  3. Under `### R-A8. Recommendation` (:225), append after :231:
     `*Note 2026-09-26:* F3 is done (2026-08-03; rocm-bandwidth-test WAS used, v2.6.0) — the recommendation reduces to F1.`
  4. Under `### R-A3. Three corrections…` (:119), append after :125 (dated, no rewrite):
     `   *Note 2026-09-26:* HumanEval in Table 2 is t=0.3 over 10 sampling runs; the other suites are greedy; no CIs anywhere (intake-1808#record, second-reader flag).`
  5. Replace the box at :245-249 (delegated) with the following ticked line plus a successor box:
     `- [x] **OPERATOR DECISION — ingest-or-reaffirm KTransformers** — resolved as INGEST: the operator selected cluster 4 for the 2026-09-26 Stage-2 round; intake-1808 (SOSP'25 paper), intake-1809 (repo @ c40722bf) and intake-1810 (KT measured on non-AMX EPYC) are dive-verified. The earlier rotted anchors intake_index.yaml:45670 / :45706 (:96, :245) meant intake-923 — cite intake-923#record. ✅ 2026-09-26`
     `- [ ] **OPERATOR DECISION — OD-A runtime question (R-A10): authorize F6 (build-only kt-kernel check) as evidence, or decline KTransformers as a runtime and keep only Expert Deferral behind F1** — master queue OP-61`
  6. Insert a new subsection between R-A8 and R-A9 (before :236). The heading is `R-A10` because R-A1..R-A9 are used (checked).
     ```
     ### R-A10. OD-A decision package — corrected premises (2026-09-26, research intake `intake/orch-prior-art-20260926`)

     Three facts the decision turns on (all dive-verified):
     1. **The CPU half is source-portable to Zen 5.** At kvcache-ai/ktransformers@c40722bf, kt-kernel's BF16/FP8/RAWINT4 native
        backends and LLAMAFILE (GGUF) exist in source and compile for an AVX-512 host without AMX (floor AVX512F+BW; BF16 and VBMI
        emulated if absent; umbrella enabled when CPUINFER_CPU_INSTRUCT is NATIVE/FANCY/AVX512). The EPYC 9655 exposes
        avx512_bf16/vbmi/vnni and no AMX. Built/run here: untested (F6). `intake-1809#01`. This overturns intake-923's
        "no AVX-512-native MoE operator family" (`intake-923#record`) — the kernels sit under operators/amx/ behind AMX-named classes.
     2. **The paper's CPU prefill gain is AMX-dependent; its decode is not.** Its own AVX-512 kernel is worse than baseline in prefill
        (§6.4); decode is AVX-512-led. Expect a Zen 5 CPU half to help decode and capacity, not long prefill (`intake-1808#01`). Expert
        Deferral is decode-only and batch-1 (`intake-1808#04`); its async vehicle is host-callback submit/sync inside one graph
        (`intake-1808#03`) — the capability our CPU backend lacks (R-A5).
     3. **The GPU half is CUDA-packaged; ROCm is an untested option.** sglang-kt pins cuda-python and kt-kernel==0.7.0.post4; kt-kernel has
        a ROCm build option and a HIP shim, the AMD test is a placeholder, no gfx90a testing evidence (`intake-1809#03`).
        Upstream-SGLang route: **P3-OD-A-ROCm — pending Stage-2b sglang-kt-integration (owning session fills).**
     The only third-party KT-on-EPYC numbers (intake-1810, KT Q4_K_M = the LLAMAFILE/GGUF path, non-AMX EPYC 9355) are cross-precision
     and cross-length against 1810's FP8 engine — not a like-for-like verdict (`intake-1810#05`). Implementation pin moved:
     R-A2 read a8062bfa (v0.6.4); current HEAD c40722bf.

     | Option | What | Cost | Risk |
     |---|---|---|---|
     | A | Decline KT as a runtime now; keep Expert Deferral as a technique gated on F1 (R-A8 unchanged) | none | leaves the Zen-5 CPU-half kernels unexamined; the decline must cite the corrected reasons (CUDA-packaged GPU half, parallel SGLang runtime), not AMX |
     | B | F6 build-only check now (no inference), then decide runtime-vs-technique after F1 and P3-OD-A-ROCm | one isolated build, pinned torch env (several GB), build CPU time; nothing touches production | small; a build proves portability, not speed |
     | C | Evaluate the KT runtime end to end on gfx90a | high: a forked SGLang beside the v10 fork, CUDA-packaged, ROCm unproven | contradicts "the fork is the substrate" (§1.4); only after B passes and a ROCm route exists |

     **Recommendation: B.** F1 remains the gate for any runtime or kernel work (R-A8); F6 converts "compiles in source" into "builds here" at near-zero risk.
     **The decision:** authorize the build-only kt-kernel check (F6) as OD-A evidence, or decline KTransformers as a runtime now and keep only the Expert Deferral technique path behind F1?
     ```
  7. At :11 (§1), append after the sentence: ` *(2026-09-26: "460 GB/s" was the pre-2026-09-21 theoretical at 4800 MT/s; now 537.6 GB/s theoretical, 446.8/449.4 GB/s measured read-sum at t96 — cpu-decode-roofline-program.md:281-285.)*`
  8. Stale-notes for the owner's boxes (append one italic line under each; do not flip):
     - :244 M2: `*Stale 2026-09-26: M2 EXECUTED 2026-08-13 (§5 :60) — owner to flip.*`
     - :257-258: `*Stale 2026-09-26: fixed 2026-08-03 (gpu-acceleration-path.md:331; no "PCIe 5" and no one-direction 64 GB/s remain) — owner to flip.*`
     - :242 F3: `*Stale 2026-09-26: done 2026-08-03 — see the R-A7 note; owner to flip.*`
  9. Master index operator queue (`## Operator decision queue`, :25; table header `| ID | Decision | Owner | Open since |` at :31). OP-60 is already claimed by DS41 (`progress/2026-09/2026-09-26-ak-ds41-main.md:126`), so this takes the next free id, re-verified against origin/main and the parallel P-sections at apply:
     `| OP-61 | OD-A (KTransformers): authorize the build-only kt-kernel check F6 as evidence, or decline KT as a runtime and keep only Expert Deferral behind F1 | [fable5-window2-findings-02-heterogeneous-gpu.md](fable5-window2-findings-02-heterogeneous-gpu.md) → R-A10 | 2026-07-29 |`
- **Rigor:** N/A (documentation). Conformance: `python3 scripts/vidya/cli.py cite-check --as-of <ts>` exits 0 on the rider (all intake cites use `#NN` of dive-verified entries or `#record`); `index_state.py --check` exits 0.
- **Dependencies:** R-A10 item 3's ROCm clause waits on the Stage-2b placeholder (P3-OD-A-ROCm); everything else can land now.

#### P3-OD-A-ROCm (pending Stage-2b sglang-kt-integration)

**PLACEHOLDER. The owning session fills this from the Stage-2b dive of upstream SGLang's KT integration**
(`sgl-project/sglang@c73f7077` `python/sglang/srt/layers/moe/kt_ep_wrapper.py`, 393 lines, torch.cuda stream handles;
issue #11425 closed "completed" 2026-02-08). The fill must supply four things:
1. Whether a kt-kernel GPU half can ride upstream SGLang's ROCm build (the 3rd fact in R-A10, and option C's precondition).
2. The intake-923 point-(4) correction: whether "SGLang adopting KTransformers (#11425)" names an issue or a merged integration.
3. Whether F6's ROCm arm should target the upstream wrapper rather than sglang-kt.
4. The new entry's disposition and its line in R-A10.

Until then, R-A10 fact 3 carries the placeholder text verbatim, and F6's ROCm arm builds kt-kernel only (no SGLang).

#### P3-5 — F6: kt-kernel build-only check on this host (operator-gated by OD-A; deterministic)

- **Project decision:** OD-A option B. It turns "the CPU half compiles in source" (1809#01) into "the CPU half builds here", and tests whether the ROCm flag builds for gfx90a.
- **Sources / ledger rows:** intake-1809#01, #03; C4-A6.
- **Primary owner:** `fable5-window2-findings-02-heterogeneous-gpu.md` (same frozen check as P3-4).
- **Posture:** `cheap-screen-now`, as a deterministic build check. It runs only if the operator answers OD-A = B.
- **Reusable primitive:** a build receipt pinning which kt-kernel backends a Zen-5 + gfx90a host actually gets. It also serves any later KT-derived evaluation.
- **Consumers:** evidence, intake-1809 (dive_corrections append with the result); policy, OP-61. Search: `kt-kernel|ktransformers` in research `scripts/` and orch `src/` found 0 hits, so there is no existing harness.
- **Immediate deliverable** (the rider's R-A9, after F3 at :243; the F-series is the rider's falsifier scheme and F1–F5 are taken, checked at :199-216):
  `- [ ] **F6 — kt-kernel build-only check on this host** (only if OD-A = B): isolated venv under /mnt/raid0/llm/tmp, pinned c40722bf; CPU-only arm (CPUINFER_CPU_INSTRUCT=NATIVE) and ROCm arm (CPUINFER_USE_ROCM=1, PYTORCH_ROCM_ARCH=gfx90a); record __cpu_variant__ / __fp8_kernel__ / __rawint4_kernel__; no inference, no production tree.`
- **Deterministic-check framing:** the empirical controls map to build controls as follows.
  - *Frozen input:* the kt commit, verified by `git rev-parse HEAD` = `c40722bf04c494f2492b7eb9e86ef01a4ede45b3`; the host `/proc/cpuinfo` flags; toolchain versions (gcc, hipcc, cmake, python, torch); the full env; the sha256 of every build log.
  - *Incumbent:* none. It is replaced by a **predeclared expectation** derived from source. On the CPU arm expect `__fp8_kernel__ == "avx512-fp8-decode-bf16"` and `__rawint4_kernel__ == "amx-int4-kgroup-g32"` (both gated on AVX512_BF16, which the host has, `ext_bindings.cpp:565-572`), and a BF16 backend string of `AVX512-BF16` (`bf16-moe.hpp:59-61`).
  - *Per-item outputs:* per arm, the build log, the compile command lines (which show the `-mavx512*` / `-march=native` flags), the attribute readout from a fresh-process `import` (attribute read only; no MoE forward, no model), and, on the ROCm arm, `nm -D` showing whether `hipLaunchHostFunc` is referenced.
  - *Holdout:* N/A for a deterministic build. It is replaced by a fresh-process re-import that must reproduce identical attributes.
  - *Denominator:* both arms are always reported. Failures are classified as `toolchain|dependency|no-matching-torch|source`, never retried away.
  - *Decision rule:* expectation met means 1809#01 is upgraded to "builds here" in dive_corrections. Mismatch or build failure means 1809#01 is narrowed to "source-only" with the failure class. A ROCm-arm failure does not block the CPU verdict.
- **Production isolation / freeze:**
  - kt-kernel is an external package, not llama.cpp kernel work, so it must not go into `/mnt/raid0/llm/llama.cpp`, `kernels/`, or `llama.cpp-experimental` either.
  - Never point `LD_LIBRARY_PATH` at the kernel store. Never install into the system, orchestrator or research venvs. Never upgrade host ROCm.
  - If no torch build matches host ROCm, record `no-matching-torch`; that is a result.
  - Run with `nice -n 19` and a bounded `-j`, outside any bench region claim, never overlapping PF1. Do one download at a time. Check free disk before starting.
  - Keep the logs and the receipt. List the venv's size for operator-confirmed reclaim; do not self-delete it.
- **Receipt:** `epyc-inference-research/data/kt-kernel-buildcheck/<UTC>/` (receipt.json + SHA256SUMS). Then tick F6 (this session's own box).
- **Broader trigger:** a runtime/throughput evaluation (option C) needs F6 to pass, F1 to clear its pre-registered rule, and P3-OD-A-ROCm to show a route. Until all three hold it stays prose in R-A10.

#### P3-6 — Supersede the pre-BIOS DRAM-bandwidth figures where they are still read as current

- **Project decision:** every CPU-decode roofline or feasibility argument; C4-A7's reason is that the stale rows are off by ~2.7×. The ledger rows also carry a decomposition ("~70 ms dispatch floor") that the post-BIOS C5 re-anchor falsified (`progress/2026-09/2026-09-21.md:127-138`), yet the ledger never received it: grep `16.82|59.5 ms|post-BIOS` in the file returns 0.
- **Sources / ledger rows:** our own receipts (`epyc-inference-research/data/bios-postreboot-20260921/`, `/mnt/raid0/llm/tmp/ds41-scope-20260926/readbw-20260926T105535Z.txt`); intake-1810#04 is only the ledger's rests_on. C4-A7.
- **Primary owner:** `handoffs/active/cpu-decode-roofline-program.md`. Status (:3): `THE CAMPAIGN IS CLOSED OUT` (a closed campaign, not a pointer). A correction note is not a new task. MEASUREMENT.md §6 says append, never edit, and `2026-09-21.md:137-138` applies exactly that to this ledger.
- **Posture:** `knowledge-only`.
- **Deliverables:** see Stale-fact corrections S7–S10. The wiki :99 half is **already discharged**: `wiki/hardware-optimization.md:5820` ("Compiled Update — 2026-09-26: The 220 GB/s Read Ceiling Was a Half-Screen Figure", commit `91f1305a`) supersedes :99, and :247 carries the 446.8 GB/s figure. So there is no wiki :99 write.
- **Gap noted, not owned here:** the ledger's D0/B1 decomposition row (:152) needs re-deriving post-BIOS (`2026-09-21.md:135-138`). That is INF-70 profiling work outside this intake's rows. The S7 note names it so the INF-70 owner sees it; no task is filed from here.
- **Consumers / search:** `220 GB/s|446.8|449.4|150–220|460.8` over handoffs/active and wiki. Additional live sites found: `conversation-stack.md:98` and `wiki/multimodal.md:65` (S9, S10).

#### P3-7 — Record Fiddler and HybriMoE as ingested lineage in the wiki inoculation

- **Project decision:** none new. This keeps the `T*(q*)` inoculation truthful: `wiki/moe-optimization.md:167` says "Fiddler, HybriMoE … none of them ingested", and both are now in the index.
- **Sources / ledger rows:** intake-1811 and intake-1813 (Stage-1 preliminary actionables). The only Fiddler facts quoted here come from dive-verified intake-1808#00 and #02.
- **Primary owner:** wiki compile sweep (see S13). No handoff task, because 1813's and 1811's handoff lists point at `large-moe-expert-parallelism.md` (COMPACTED, :3), `heterogeneous-slot-fabric-residency.md` and `moe-routing-tap-and-locality-measurement.md` (stub), none of which has distinct adoption work for a lineage row.
- **Posture:** `knowledge-only`.

### Stale-fact corrections

"Who applies" is Stage 4 unless marked *wiki sweep*. Per CLAUDE.md, the wiki compilation sweep waits for an operator-invoked `/wrap-up`. If the owning session treats intake Stage 4 as allowed to compile, apply S11–S14 as one appended Compiled Update. Otherwise hand the prepared text to that sweep.

| # | File:line (lane) | Stale text (quoted) | Evidence | Action |
|---|---|---|---|---|
| S1 | `numa-prefill-decode-disaggregation.md:14`, `:34`, `:10`, `:56`, `:76` | "EPYC 9655's 2-socket / 8-NUMA-node topology … with KV migration over xGMI"; "xGMI inter-socket ≈ 64 GB/s/dir" | `/mnt/raid0/llm/tmp/dive-intake-1810/sources/host_lscpu_20260926.txt` (`Socket(s): 1`, `NUMA node(s): 4`); `wiki/hardware-optimization.md:2816` already states the xGMI bottleneck "doesn't exist on single-socket EPYC" | P3-1 deliverables 1, 2, 5, 6, 7 |
| S2 | `numa-prefill-decode-disaggregation.md:8`, `:40` | "DS-7 already pre-warms 1×96t … + 4×48t decode-favorable instances" | `numa-topology-cutover-resume-20260730.md:96-102` ("Quarters are retired."; shapes full / half A / half B) | P3-1 deliverable 3 |
| S3 | `inference-research-index.md:53` (INF-44 Next action) | "BLOCKED: feasibility-gated (xGMI KV-transfer falsification); reopen on multi-tenant shift" | S1; `sarathi-serve-cpu-evaluation.md:12` (trigger already materialized) | Prepared row, see *New stubs + index rows* |
| S4 | `sarathi-serve-cpu-evaluation.md:26` (under `## Why This Comes Before CPU16 (NUMA Disagg)`, :24) and `:116` | "On EPYC, where xGMI inter-socket bandwidth (~64 GB/s) is dramatically lower than NVLink…"; "the Phase 0 xGMI KV-transfer-BW measurement was never run" | S1 | Append after :26: `*Note 2026-09-26: this host is single-socket NPS4 — there is no xGMI link; CPU16 has been re-scoped to GPU-prefill / CPU-decode (numa-prefill-decode-disaggregation.md). The chunked-prefill case here stands on its own.*` Append the same one-liner after :116. |
| S5 | `heterogeneous-slot-fabric-residency.md:77` | "PCIe ~26 GB/s, ~60×" | `epyc-inference-research/data/mi210-h2d-d2h/20260803T131500Z/` (H2D 28.894 GB/s at 128 MB; commit `2aa14264`) | P3-2 deliverable 1 |
| S6 | `fable5-window2-findings-02-heterogeneous-gpu.md:206-209`, `:220-221`, `:228-229`, `:242`, `:244`, `:245-249`, `:257-258`, `:124-125`, `:11`, `:96`/`:245` anchors | "no measured H2D/D2H bandwidth anywhere"; "#1612 … open and unanswered"; "`rocm-bandwidth-test` is not installed"; "M2 … still unrun"; "It has never been ingested"; "`gpu-acceleration-path.md:306` states PCIe 5.0"; "single-run without CIs"; "460 GB/s CPU pool"; `intake_index.yaml:45670/:45706` | H2D receipt above (the header reads `RocmBandwidthTest Version: 2.6.0`); intake-1809 reported_results (collaborator reply); `fable5…:60` (M2 EXECUTED 2026-08-13); `gpu-acceleration-path.md:331`; second-reader flag on 1808 claim 4; `cpu-decode-roofline-program.md:281-285`; the rider's commit `c47a229a` resolves :45670 → intake-923 and :45706 → intake-924 (drift) | P3-4 deliverables 1–8. The 1793659d note at :99 already fixed "never been ingested" in R-A1; it is not duplicated, only completed by deliverable 5. |
| S7 | `cpu-decode-roofline-program.md:146`, `:147`, `:149`, `:150`, `:151`, `:152`, `:163-172` | "**460.8 GB/s today**"; "212 GB/s"; "**152.6 GB/s at 48 threads, 165.6 at 96** … global (~170 GB/s)"; "27 ms/token (37 t/s) at the measured 153 GB/s"; "27% … 9% of theoretical"; D0/B1 decomposition; "the recipe gets 153 GB/s of a 460.8 GB/s machine" | `epyc-inference-research/data/bios-postreboot-20260921/` (C0 read-sum 446.8 at t96, 410.4 at t48, gemv-2560 478.9); `/mnt/raid0/llm/tmp/ds41-scope-20260926/readbw-20260926T105535Z.txt` (449.4 at t96, load average 17–21); `progress/2026-09/2026-09-21.md:49,91-138` | Append after :172 (before `## Axis C — measurement …` at :175), without editing the rows, per MEASUREMENT.md §6: `> **Post-BIOS supersession — appended 2026-09-26 (research intake; rows above are pre-BIOS and are not edited).** On 2026-09-21 the operator applied memory interleave ON + DDR5 5600 MT/s (C8, :281-287). Current host facts: theoretical **537.6 GB/s**; C0 read-sum **446.8 GB/s at t96** (410.4 at t48; gemv-2560 478.9) — epyc-inference-research/data/bios-postreboot-20260921/; re-read 2026-09-26 under load average 17–21: **449.4 GB/s** at t96. The ~170 GB/s global cap in :149 is gone. Superseded as current-host facts: :146 "460.8 today", :147, :149, :150–151, and the "153 GB/s of a 460.8 GB/s machine" above. Recomputed roofline at the same 4.16 GB/token: **9.3 ms (107 t/s)** at 446.8 GB/s, **7.7 ms (129 t/s)** at 537.6 — computed, not measured. The D0/B1 split at :152 and the "~70 ms dispatch floor" do not survive: the post-BIOS C5 re-anchor shed 39 ms/token (98.6 → 59.5 ms, tg128 t48, build 10151, uniform IQ4_XS research artifact), more than the row's entire 27 ms bandwidth budget (progress/2026-09/2026-09-21.md:91-138); re-deriving :152 post-BIOS is INF-70 work.` |
| S8 | `wiki/hardware-optimization.md:99` | "Host read-bandwidth ceiling, measured directly: 220 GB/s" | Already superseded in place at `:5820-5838` (commit `91f1305a`) | **No action** (C4-A7's wiki half is discharged) |
| S9 | `conversation-stack.md:98` (under `## Facts that constrain the design (verified 2026-09-24)`, :73) | "Decode-usable bandwidth is about **150–220 GB/s**, not the 460.8 GB/s theoretical figure" | S7 receipts; `deepseek-v41-flash-evaluation.md:662-668` | Append a sub-bullet after :98: `  - *Correction 2026-09-26:* 150–220 GB/s is pre-BIOS. Since 2026-09-21 a full-screen read-sum measures 446.8 GB/s at t96 (cpu-decode-roofline-program.md:281-285) and 449.4 under load (deepseek-v41-flash-evaluation.md:662-668). A ~250 GB/s decoder is no longer excluded by the ceiling alone; whether it fits beside a -t 96 LLM is the contention question in the next bullet.` The owner of this file is the INF-79 session. This is a dated correction note, not a task. |
| S10 | `wiki/multimodal.md:65` | "Decode-usable CPU bandwidth is **about 150–220 GB/s, not 460**" | as S9 | *wiki sweep*: an appended Compiled Update line carrying S9's correction. |
| S11 | `wiki/hardware-optimization.md:1692-1694` | "the same '~64 GB/s' string also appears … attached to **xGMI inter-socket** bandwidth — a completely different link" | S1; the same page at :2816 | *wiki sweep*: `**Correction (2026-09-26):** the "xGMI inter-socket ~64 GB/s" figures the 2026-08-03 sweep deliberately left alone do not describe this host at all — it is single-socket NPS4 (lscpu 2026-09-26), so there is no xGMI link. The sites that relied on it (numa-prefill-decode-disaggregation.md, sarathi-serve-cpu-evaluation.md) were re-scoped 2026-09-26; the disaggregation question here is GPU-prefill vs CPU-decode over PCIe Gen4 (H2D 28.89 GB/s).` |
| S12 | `wiki/inference-serving.md:1800` | "`numa-prefill-decode-disaggregation.md` remains active only for the Phase 0 xGMI KV-transfer falsification gate" | S1 | *wiki sweep*: `numa-prefill-decode-disaggregation.md was re-scoped 2026-09-26 to GPU-prefill / CPU-decode (intake-1810#02); its Phase 0 is the CPU-vs-MI210 prefill crossover (PF1).` |
| S13 | `wiki/moe-optimization.md:167` | "**Fiddler, HybriMoE, SMoE and FluxMoE** — none of them ingested" | intake-1811 / intake-1813 exist (lane index :224287, :224433) | *wiki sweep*: `Update 2026-09-26: Fiddler and HybriMoE are now in the index as lineage anchors only (intake-1811#record, intake-1813#record; stage1-unverified, knowledge_only). The inoculation still applies. The one Fiddler fact with dive-verified provenance comes via KTransformers' measurements of it: >7,000 CUDA kernel launches per decoded token and a 16% one-to-two-socket gain (intake-1808#00, intake-1808#02).` |
| S14 | intake-923 `dive_corrections` (`research/intake_index.yaml:54822`, inside the KTransformers package) | "…with NO AVX-512-native MoE operator family" | intake-1809#01 (source-level at c40722bf) | Stage 4 appends to intake-923 `dive_corrections` (see dispositions). No `claim_corrections` row applies, because the package is prose in dive_corrections, not a key_claim of this AgentENV entry. |

### Explicit declines

- **C4-A8 — adopt or port 1810's SLP/DSLP implementation** (owner in ledger: `gpu-serving-tie-in-program.md`). Declined. No code or artifact is released (arXiv HTML, USENIX page and GitHub search all empty, per c4 contested_claims). The policy that transfers is captured by P3-1, P3-2 and P3-3. `gpu-serving-tie-in-program.md` receives no edit; it is listed as a prospective consumer in P3-2.
- **`design-backlog-triage-2026-07-23.md:150` (C55, "disagg across 8 NUMA nodes … xGMI")**: no edit. The file is a dated triage snapshot (`status: triage for operator review`, :4). The live owner (numa handoff) carries the correction, and editing a historical snapshot would violate append-don't-rewrite.
- **`gpu-acceleration-path.md:331`** ("Their own Phase-0 xGMI measurement remains unrun"): no edit. It is a ticked 2026-08-03 record and its category-error warning is correct as written. S1 and S11 fix the premise at its owners.
- **PF1 on DeepSeek-V4.1-Flash-Q4:** `monitor`. The trigger is recorded in P3-3 as prose.

### New stubs + index rows

- **New stubs:** none. Every item has a live owner.
- **Index row edits.** A subagent prepares these; the owning session applies them.
  - `handoffs/active/inference-research-index.md`, header `| ID | Track | Handoff | Next action | Deps |` (:11). Replace row :53:
    `| INF-44 | numa prefill decode disaggregation | [numa-prefill-decode-disaggregation.md](numa-prefill-decode-disaggregation.md) | Blocked on INF-34 PF1 (CPU-vs-MI210 prefill crossover); then run NPD-1 or close the GPU-prefill branch | INF-34 |`
    (Next action is 102 characters.)
  - INF-34, INF-23, INF-70 and EVL-20 rows: unchanged. Each keeps its current next action; PF1 is discoverable through INF-44's Deps edge and the fabric task.
- **Master operator queue:** OP-61 row (P3-4 deliverable 9). This is the only master-index write.

### Intake-entry dispositions (Stage 4 sets)

| Entry | handoffs_updated / handoffs_created | integration_disposition | disposition_evidence (one line) | Other |
|---|---|---|---|---|
| intake-1810 | updated: numa-prefill-decode-disaggregation.md, heterogeneous-slot-fabric-residency.md, mi210-big-model-and-acceleration-roadmap.md | integrated | "Policy pattern (GPU-prefill/CPU-decode over one DRAM copy) routed to the numa re-scope, the fabric prefill rule and PF1; SLP/DSLP port declined (no code released)." | none |
| intake-1808 | updated: fable5-window2-findings-02-heterogeneous-gpu.md | integrated | "AMX-dependent prefill / AVX-512 decode split, deferral scope and host-callback graph mechanism carried into the OD-A package R-A10." | none |
| intake-1809 | updated: fable5-window2-findings-02-heterogeneous-gpu.md | integrated | "Source-level Zen-5 portability of the kt-kernel CPU half and the CUDA-packaged/ROCm-untested GPU half carried into R-A10; F6 build check filed (OD-A-gated)." | Later (after F6), append the build result to `dive_corrections` |
| intake-923 | unchanged | unchanged (do not invent one for this AgentENV entry) | none | **Append to `dive_corrections`:** `2026-09-26 correction (intake/orch-prior-art-20260926 Stage 2; intake-1809#01, intake-1809#03): the KTransformers package above is corrected on two points. (1) OVERTURNED — "NO AVX-512-native MoE operator family": at kvcache-ai/ktransformers@c40722bf the BF16/FP8/RAWINT4 AVX-512 backends and LLAMAFILE exist in source and compile without AMX (floor AVX512F+BW); they live under operators/amx/ behind AMX-named classes, which a path-level census cannot see. Built/run on Zen 5: untested. (2) NARROWED — the GPU half: kt-kernel carries a ROCm build option and a HIP shim, the AMD test is a placeholder, no evidence of gfx90a testing or use; the serving package (sglang-kt) is CUDA-packaged. The AMX discount stands NARROWED for prefill only (intake-1808#01). [Point (4) "#11425": pending Stage-2b — P3-OD-A-ROCm fills.]` |
| intake-1811 | none | knowledge_only (keep) | Replace with: "Lineage anchor only; superseded for the runtime role by KTransformers (intake-1808); named in the wiki T*(q*) inoculation as intake-1811#record (moe-optimization.md, 2026-09-26 compile)." | none |
| intake-1813 | none | knowledge_only (keep) | Replace with: "Lineage anchor only; already covered by the wiki T*(q*) inoculation, now cited as intake-1813#record (moe-optimization.md, 2026-09-26 compile)." | none |

If S13 lands only at a later `/wrap-up`, write the 1811 and 1813 evidence lines then, not before, so the evidence does not claim a citation that does not exist yet.

### Coverage table

| Row / actionable | Plan item | Terminal mapping |
|---|---|---|
| C4-A1 | P3-1 (+ S1–S4, INF-44 row) | knowledge-only edits, plus a monitor trigger (NPD-1) |
| C4-A2 | P3-2 (+ S5) | primitive-now (design rule); input box blocked on P3-3 |
| C4-A3 | P3-3 (PF1 + VB-PREFILL-XOVER) | cheap-screen-now with all six controls |
| C4-A4 | P3-4 deliverables 1–5, 7, 8 (S6) | knowledge-only (dated notes, a delegated tick, owner flips requested via bus) |
| C4-A5 | P3-4 deliverables 6, 9 (R-A10, OP-61), P3-OD-A-ROCm | knowledge-only decision package; ROCm fact pending Stage-2b |
| C4-A6 | P3-5 (F6) | cheap-screen-now, deterministic; operator-gated (OD-A = B) |
| C4-A7 | P3-6 (S7–S10; S8 already discharged) | knowledge-only |
| C4-A8 | Explicit declines | decline |
| intake-1811 (Stage-1 preliminary) | P3-7 / S13 | knowledge-only |
| intake-1813 (Stage-1 preliminary) | P3-7 / S13 | knowledge-only |
| Operator-directed: intake-923 overturn | S14 + dispositions | dive_corrections append |
| Operator-directed: F3 stale | S6 / P3-4 deliverables 1, 3, 8 | dated note; owner flips |
| Operator-directed: numa 2-socket / 8-node | S1–S4 | corrected |
| Operator-directed: DRAM bandwidth rows | S7–S10 | corrected (wiki :99 already done) |

### Open questions for the operator

1. **OD-A (OP-61), one sentence:** should the build-only kt-kernel check (F6) run as OD-A evidence, or should KTransformers be declined as a runtime now, leaving only Expert Deferral as a technique behind F1? *Recommendation: F6 (option B).*

Approving this plan also approves ticking the delegated OD-A "ingest-or-reaffirm" box as resolved-by-ingest (P3-4 deliverable 5). That is recorded here so the flip has a human authorization, not an agent one.

---

## P4 — Stage-2b actionables (intake-1815..1821), the P3-OD-A-ROCm fill, and cross-section reconciliation

**Pins.** Lane worktree `/mnt/raid0/llm/worktrees/intake-orch-prior-art-20260926` @ `8ff8fc5c` (the Stage-2b commit on
top of `33e82ae3`; the handoffs are identical to what P1-P3 read). Orchestrator: P1-P3 cite `fb7871ea`, and HEAD is now
`a439070e`. The drift is covered in Reconciliation R6. Every `file:line` without a repo prefix is a lane line.

**Quotable sources.** intake-1815 (RouterWise), 1816 (ThunderAgent), 1817 (Dynamo PR #7977), 1818 (SGLang KT
integration), 1819 (Talaria), 1820 (Proxifield) and 1821 (EvoHarnessBench) are all dive-verified. There is one caveat:
intake-1815 claim 4 counts "5 of 8" panels but lists six. The second reader's substantive flag catches this. Nothing
below quotes that count; Stage 4 corrects the entry (index edit E6).

**IDs checked before allocating** (grep over lane `handoffs/`, `docs/`, `research/intake_index.yaml` and the P1-P3
drafts):

| Series | Already taken | P4 allocates | Where checked |
|---|---|---|---|
| Fabric (P2 introduced `HSF-`) | HSF-1, HSF-2 (P2) | **HSF-3** | fabric has no other task IDs (only `**P2` at :139) |
| `KVU-` | KVU-0a..0i, 1, 1a-1e, 2, 3, 3a, 4, 4a, 5, 6, 7, 8, 9, 10, 11, 11a-11c, 12, 13a-13c | **KVU-14** | `kv-unified-stack-rollout.md` |
| DSC wave-local rows (`K4`, `K4a`, `G4`, `H20`, `H21`, `B3`) | G4 | **G5 (G)** | `dynamic-stack-concurrency.md` (no `G5`) |
| `HS-` / `HS-OD-` | HS-1..HS-18, HS-OD-1..9 (P1 takes 8, 9, 16, 17, 18) | none; P4 folds into HS-16 and HS-4 P6 | harness handoff + P1 |
| `DAR-LAT-` | DAR-LAT-1..3 (+3a, 3g, 3b, 3c) (P2) | none; P4 folds into DAR-LAT-2 | P2 |
| VB tasks | VB-V1-BACKPRESSURE (P1), VB-SEL-LOADAB, VB-SWAP-C (P2), VB-PREFILL-XOVER (P3); SC max SC89 | **VB-GAP-DIST, VB-MT-REPLAY**; activation records **VB-SPILL-TTFT, VB-KT-BUILD, VB-NPD-1** | vidya program + adapters README: zero hits |
| Master `OP-` | OP-60 (DS41), OP-61 (P3) | none; P2's `OP-<next>` becomes **OP-62** (R1) | master index + `progress/` |

P4 creates no new stubs and adds no new index rows.

---

### Plan items

#### P4-1 — Key DAR-LAT-2's latency prior by (role, device, topology_hash)  *(FOLD into P2 DAR-LAT-2)*
- **Rows:** 2b-routerwise-A1. **Sources:** intake-1815#0, intake-1815#6; intake-1796#2 (already P2's).
- **Owner:** `decision-aware-routing.md`, inside P2 edit 1. The status line (:3) is not frozen for this. The DAR-4b
  precedent (:155) applies, and DAR-LAT-2 lands at weight 0.
- **Posture:** primitive-now, as part of DAR-LAT-2.
- **Why:** RouterWise's latency model is per (model, setup), and its runtime router is itself a static-prior router
  with no live arm. It therefore *supports* DAR-LAT-2's design, but only if the prior is conditioned on the deployed
  placement. Today `baseline_tps_by_role` is keyed by role alone (`decision-aware-routing.md:593-611`), while fabric
  residency changes on a minutes timescale (`heterogeneous-slot-fabric-residency.md:55`).
- **Amendment A: DAR-LAT-2.** Append this sub-bullet to DAR-LAT-2 in P2 edit 1, after the "Env-gated AB mode" bullet:
  ```
    - Key every prior row by (role, device, topology_hash), never by role alone: record the device (CPU region set or MI210) and the `ContentionGate._live_topology_hash()` value (orch `src/scheduling/contention_gate.py:141`) the TPOT/L̂ inputs were derived under. A row whose topology_hash differs from the live stack contributes term 0 plus a `prior_stale` flag (the same fail-open path as a missing prior), so a stack change or a Layer-2 residency swap cannot leave a CPU-era prior pricing a GPU-resident role. Re-derive the table on every stack change. RouterWise's latency model is per (model, setup) and its own router is a static prior with no live arm (intake-1815#0, intake-1815#6).
  ```
- **Amendment B: DAR-LAT-3a manifest.** Replace "frozen prior table and episodic snapshot digests" with "frozen prior
  table (keyed by role/device/topology_hash, with the live topology_hash at freeze) and episodic snapshot digests".
- **Amendment C: section heading.** Append `/1815` to the P2 edit 1 section heading's intake list.
- **Consumers:**
  - Direct: DAR-LAT-3 manifest and positive controls.
  - Prospective: the model-keyed capability card (`heterogeneous-slot-fabric-residency.md:147`, per (model, device)).
    The prior can later read TPOT from it.
  - Search terms: `baseline_tps_by_role`, `topology_hash`, `_live_topology_hash` over orch `src/ orchestration/
    scripts/`.
- **Rigor (deterministic):**
  - A stale-hash fixture must give term 0 plus the flag.
  - Mutation: a role-only key must be rejected by the loader.
  - The weight-0 byte-identity test (P2) stays green.
- **Deps:** DAR-LAT-2 (P2).

#### P4-2 — Routed-traffic share vs allocated compute as a Layer-3 regime-change input  *(FOLD into P2 edit 2a, under fabric :152)*
- **Rows:** 2b-routerwise-A2. **Sources:** intake-1815#1, intake-1815#4.
- **Owner:** `heterogeneous-slot-fabric-residency.md`. Its status is "DESIGN — GATED" (:18). This is a spec bullet
  under a gated task and needs no checkbox.
- **Posture:** knowledge-only (spec). It inherits the :152 gate.
- **Paste:** nested under :152, directly after P2's "Policy prior (2026-09-26, intake-1789#02)" bullet.
  ```
    - Regime-change input (2026-09-26, intake-1815#1, intake-1815#4): report each role's routed-traffic share (final role from the DAR-LAT-2 selection receipts, decision-aware-routing.md; admission-ledger dispatch counts) beside its allocated compute (device, NUMA instance count), and flag a role whose share and allocation diverge under sustained load. RouterWise's only material placement losses are whole-device-per-model isolation under skewed load at a small device budget; a load- or size-proportional fixed rule recovers most of its searched optimum (predicted score from profiled curves, not measured). Regime-change timescale only (Layer 2/3, minutes); never a per-request placement signal; no new telemetry (Axiom 1, :201).
  ```
- **Consumers:** Layer-3 policy (:152) and N-dwell (:153). Search: `traffic share|routed share|allocation` over lane
  handoffs found no existing input.
- **Deps:** DAR-LAT-2 receipts (P2).

#### P4-3 — Dynamo has no worker device class; keep the EPYC slot fields  *(FOLD into P2 edit 2b, slot-record paragraph)*
- **Rows:** 2b-dynamo-pr7977-A1. **Sources:** intake-1817#2, intake-1817#3.
- **Owner:** fabric. **Posture:** knowledge-only.
- **Paste:** in P2 edit 2b's "**Slot-record fields, schema only (c3-A2).**" list, after the "EPYC-only fields beside
  the three" bullet.
  ```
  - No upstream home for those fields (intake-1817#2, intake-1817#3): at Dynamo 81a9871a a CPU decode worker is an untyped decode worker — ModelRuntimeConfig has no CPU/GPU/XPU field, the default worker cost has no device or throughput term, and CPU bias is possible only through hand-set taints — and the Planner budgets in GPUs. Keep `device_class` and measured t/s as EPYC fields; do not wait for an upstream contract.
  ```

#### P4-4 — Spillover measurement arm: CPU capacity as a TTFT relief valve under GPU queueing  *(spec bullet under fabric :148; activation-gated)*
- **Rows:** 2b-dynamo-pr7977-A2. **Sources:** intake-1817#4 (author-reported, not a prior) and intake-1817#1.
- **Owner:** fabric. The spillover path belongs to the GPU-as-placement-target design (:148; Layer 1 at :54).
- **Posture:** monitor. It fires when Layer-1 spillover is measured. This is the operator's "CPU+RAM is
  under-leveraged" thesis stated so it can be tested.
- **Paste:** nested under :148.
  ```
    - Spillover measurement arm (2026-09-26, intake-1817#4; design only, inherits this task's gate): when Layer-1 spillover is measured, include a partial-offload arm — under deep GPU queueing, route a fraction r of NEW sessions whole-request to the designated CPU fallback (no KV handoff; re-prefill per the teleport rule, :73-78) and report TTFT, TPOT and completed requests/min against GPU-only at matched load, with P-GPU-1 device-state capture and the codified CPU recipe. Dynamo's PR ratios are author-reported with no hardware, load or r-control stated; they are not a prior. Reuse DAR-LAT-3's driver (`scripts/benchmark/selection_loadsweep_ab.py`, decision-aware-routing.md); the CPU-speech collision (kv-unified-stack-rollout.md KVU-11b) and MEAS-6 host coupling are in scope. Belief kernel: VB-SPILL-TTFT (activation record).
  ```
- **Six controls.** These are predeclared now and frozen into the run manifest when the arm fires.
  1. **Frozen input manifest:** prompt-set digest, served artifacts and store digests, argv, and the r grid
     {0, 0.125, 0.25, 0.5}.
  2. **Incumbent baseline:** r = 0 (GPU-only), measured in the same window.
  3. **Per-item raw outputs:** one row per request (arm, r, load point, timestamps, outcome class).
  4. **Holdout:** a later-window replicate at the best r.
  5. **Complete denominator:** every arrival counts. Timeouts and 503/429 responses are misses.
  6. **Predeclared decision rule:** adopt a spillover threshold only if TTFT-SLO attainment beats r = 0 by more than an
     A/A floor at 2 or more GPU-saturating loads, completed requests/min does not fall by more than the floor, and
     TPOT stays within the SLO. Otherwise write BOUNDED-NULL-1.
- **Deps:** the :148 design, and the DAR-LAT-3 driver (P2).

#### P4-5 — HSF-3: measure the per-session inter-call gap distribution  *(NEW task in P2's fabric 2026-09-26 section)*
- **Rows:** 2b-talaria-A1. **Sources:** intake-1819#2, #4, #12. Talaria's own gaps are sub-second and are NOT carried
  over.
- **Owner:** fabric (INF-23).
- **Gate:** "Nothing is built until … the operator authorizes" (:18-22). HSF-3 is a read of existing logs: zero
  inference, no build, no placement change. As with HSF-1, plan approval authorizes it (see R1 for the scope-line fix).
- **Posture:** cheap-screen-now (zero-inference measurement).
- **Reusable primitive:** the gap distribution per (role, client class). It is the single input for every
  keep-KV / lease / TTL constant planned in this intake.
- **Paste:** in P2 edit 2b, after HSF-2.
  ```
  - [ ] **HSF-3 — Measure the per-session inter-call gap distribution from existing logs (zero inference).** Gap = model response complete → next enqueue for the same session, per role and per client class (OpenCode `/v1` harness, `/chat`/REPL, autopilot). Sources: inference-tap structured events (`request_keys.x_session_id`; orch `src/llm_primitives/inference.py:1198-1200`), progress-log session events (`orchestration/repl_memory/progress_logger.py:768-800`) and `/chat` session checkpoints (`src/session/sqlite_store.py:184`). Step 0 prices the source: count sessions carrying a session key plus completion and next-enqueue timestamps; a class with <50 such sessions is recorded as a gap and deferred to HS-4 P0.4/HS-14 runs. Publish p50/p90/p99 with n per class and a later-window replicate. Consumers: τ in the swap-protocol amendment (:89), the tracked-session TTL (:98), HS-16's idle-retention TTL, dynamic-stack-concurrency.md G5's gap lengths, kv-unified-stack-rollout.md KVU-14's forced-resume timeout. Talaria's τ=1 s is sized to its own sub-second p90 and is NOT carried (intake-1819#4, intake-1819#12). Plan approval 2026-09-26 authorizes this item. Belief kernel: VB-GAP-DIST.
  ```
- **Six controls:**
  1. **Frozen input manifest:** the log file list with sha256, the window [t0, t1), the extractor revision and the
     session-key resolution rule. It is written before the first read.
  2. **Incumbent baseline:** N/A. The result is descriptive. Today's implicit values are recorded as "no TTL on `/v1`
     session state; fabric TTL unset", and no decision is taken against them.
  3. **Per-item raw outputs:** one row per gap (session hash, role, class, t_done, t_next, gap_s, source), plus
     `summary.json`.
  4. **Holdout:** a second window W2, 7 or more days later. W1 and W2 are never pooled.
  5. **Complete denominator:**
     - Every session with 2 or more calls counts.
     - Single-call sessions are counted.
     - Gaps with a missing timestamp are counted as unmeasurable, by class.
     - Sessions cut by a window edge are counted.
  6. **Predeclared decision rule:**
     - A class's published τ candidate is its W1 p90, but only if n ≥ 200 gaps and the W2 p90 is within ±25%.
     - Otherwise no τ is published for that class, and consumers keep a predeclared constant.
     - The result is observation-grade and authorizes no serving change.
- **Consumer search:** `inter-call gap|tool gap|idle TTL|session TTL|tracked-session` over lane handoffs. The only hit
  is fabric :98 ("TTL/LRU demote on idle"), which has no measured value.
- **Deps:** none. It can run at any time and needs no window.

#### P4-6 — Swap protocol: reclaim at SESSION quiescence; save idle tracked slots before a forced swap  *(fabric; dated amendment + FOLD into P2 edit 2a)*
- **Rows:** 2b-talaria-A2. **Sources:** intake-1819#1, intake-1819#7, intake-1819#10.
- **Owner:** fabric. **Posture:** knowledge-only (a design amendment on a gated design).
- **(a) Insert after :89.** This goes after the "Fail-safe:" line and follows the dated-correction blockquote
  precedent at :68-71.
  ```
  > **Amendment 2026-09-26 (research intake; intake-1819#1, intake-1819#7, intake-1819#10):** step 2's "drain at turn boundaries" is necessary, not sufficient. A call boundary inside a live agent session is exactly where a model's window closes on a pending return: Talaria measured it on its own Aegaeon-like round-scheduler ablation (disabling session-prefill raises p50 session completion time from 189 s to 623 s), not on Aegaeon. Reclaim model A only at SESSION quiescence — no tracked A session completed a call within the last τ (τ from HSF-3). When a swap cannot wait (kill-switch, regime change), first `POST /slots/{id}?action=save` for every idle A slot holding a tracked session; production v10 permits a save only on an idle slot (server-context.cpp:2593-2596 @ffc1bac8). The save pays off only when the session returns to the same GGUF/quant (the recovery term under the tracked-session index task); otherwise it re-prefills. Do not rely on `--cache-ram`: that host prompt cache is in-process and dies with the evicted server. Axiom 4 unchanged; no kernel change.
  ```
- **(b) Fold into P2 edit 2a.** In the :152 "Policy prior" bullet, replace "Turn boundaries only, under the existing
  drain protocol (:80-87)." with "Session quiescence only (the 2026-09-26 swap-protocol amendment after :89), under
  the existing drain protocol (:80-87)."
- **Consumers:** the Layer-2 actuator verb (:149); N-dwell (:153); KVU-5 and KVU-14, which use the same save verb.
- **Deps:** HSF-3 for τ. It is text-only now.

#### P4-7 — KV-recovery term for a returning tracked session; the tracked-session index is the ONE session table  *(spec bullet under fabric :151)*
- **Rows:** 2b-talaria-A3. **Sources:** intake-1819#5, intake-1819#11 (qualitative only; see E7).
- **Owner:** fabric. **Posture:** knowledge-only (spec on a gated task).
- **Paste:** nested under :151.
  ```
    - KV-recovery term and single session table (2026-09-26, intake-1819#5, intake-1819#11): when a tracked session returns and its GPU home is draining or evicted, the placement cost of its next call adds an explicit recovery term — 0 (slot still warm), slot-file restore (same GGUF/quant only; dual-resident pairs are quant-asymmetric, :74-76, so a cross-device restore is invalid), or full re-prefill on the CPU fallback priced by R_cpu(L) (mi210-big-model-and-acceleration-roadmap.md PF1) — so the fallback is never treated as free because it has spare slots. Talaria's router data show load-only placement reopening models and losing KV. This index is the ONE per-session state table: identity comes from harness-selection-and-integration.md HS-16's resolver, idle expiry from HSF-3, and kv-unified-stack-rollout.md KVU-14 reads it rather than building a second table (Axiom 1).
  ```
- **Deps:** PF1 (P3-3) supplies R_cpu(L). HS-16 (P1-C) supplies identity.

#### P4-8 — HS-16 lifecycle: end-of-session signal plus idle-retention TTL  *(FOLD into P1-C HS-16)*
- **Rows:** 2b-thunderagent-A3. **Sources:** intake-1816#4, intake-1816#6.
- **Owner:** `harness-selection-and-integration.md` (UFH-01). Its status is active, with no frozen clause.
- **Posture:** primitive-now (deterministic).
- **Why fold here:** HS-16 builds the session-identity resolver. Release is the only harness signal a program-level
  scheduler needs beyond the id, and it keys on the same resolved id.
- **Amendment:** in P1-C's HS-16 task line, insert this before "Then update `client-surface-audit.md` §1's header
  line.":
  ```
  Lifecycle (intake-1816#4, intake-1816#6): at tag `v1.18.31`, check whether the plugin `event` hook delivers a session idle, end or delete event; if it does, the plugin sends one end-of-session signal (an `x_session_final` body key on a minimal `/v1` request, or an MCP call); in every case per-session orchestrator state keyed by the resolved id expires on an idle-retention TTL (HSF-3's harness-class p99; a predeclared constant until then) and records `session_end_source` (`signal|ttl`). Tool start/end events are not forwarded (declined; ACTING is inferred from response completion).
  ```
  Also append to HS-16's "Tests:" clause: "TTL expiry; a final-signal release; the event-hook finding recorded in
  `client-surface-audit.md` §1."
- **Rigor (deterministic):**
  - Conformance: expiry at TTL, and release on the final signal.
  - Mutation: a final signal for an unknown id must be a no-op that is logged.
  - Golden: `request_keys` stays unchanged when no signal is sent.
- **Consumers:** the fabric tracked-session index (P4-7); KVU-14; HS-4 P2/P3 memory keyed on `x_session_id` (`:82-84`).
- **Deps:** HSF-3 for the TTL value. That dependency does not block, because a constant is used until HSF-3 lands.

#### P4-9 — MCP catalog growth: a retention and token check as HS-4 P6 acceptance
- **Rows:** 2b-evoharnessbench-A1. **Sources:** intake-1821#1, #2, #7.
- **Owner:** harness handoff. P6 is at `:88`. P1 lists P6 only as a consumer, so this does not duplicate P1.
- **Posture:** primitive-now as acceptance text. The check runs when P6, or the P2 `memory_*` server, changes the
  catalog.
- **Paste:** nested sub-bullet under `:88`, with no new checkbox.
  ```
        - *Catalog-growth acceptance (added 2026-09-26, research intake):* before P6 (or the P2 `memory_*` server) changes the MCP tool catalog OpenCode sees, re-run a frozen set of previously passing OpenCode tasks before and after the change, logging per-task tokens; the change lands only if no previously passing task fails in both of two reruns, and the per-task token ratio is reported. Catalog growth can raise accuracy while nearly tripling tokens (EvoHarnessBench, ReAct: 26.0 → 30.2 pass for 27.2M → 75.8M tokens, intake-1821#2), and pool growth can break previously working delegation (intake-1821#1, intake-1821#7). Runs through the P0.4 runner, so records project via SC86.
  ```
- **Six controls:**
  1. **Frozen input manifest:** the task set and its digest.
  2. **Incumbent baseline:** the pre-change catalog.
  3. **Per-item raw outputs:** each task's `attempts.jsonl`.
  4. **Holdout:** the second rerun.
  5. **Complete denominator:** every task in the set.
  6. **Predeclared decision rule:** as stated in the paste above.
- **Belief kernel:** the existing SC86 row (`scripts/vidya/adapters/README.md:304`). No new VB row is needed.

#### P4-10 — DSC G5: N-session tool-gap replay, with forced re-prefill split by cause
- **Rows:** 2b-thunderagent-A1. **Sources:** intake-1816#1, intake-1816#7.
- **Owner:** `dynamic-stack-concurrency.md` (RTG-11).
  - Status: "COMPACTED" (:3). It is not a pointer and has no "do not add" clause.
  - Its scope line (:118) is stack orchestration. However, the (G) multi-turn replay row (:246-257) already lives in its
    2026-08-21 intake section, and G5 extends that row's instrument.
  - Moving the row would split one instrument across two handoffs.
- **Posture:** cheap-screen-now. It needs a window and shares the (G) row's instrument and window.
- **Paste:** nested under the "(G) #25592 is the LARGER exposure" row, after `:257`.
  ```
    - [ ] **G5 (G) — extend this replay to N concurrent sessions with tool gaps, before any program-level scheduler work** (2026-09-26, intake-1816#1, intake-1816#7). Same instrument (dedicated `-lv 4` instance on the served artifact and production recipe, never a production server), on the kv-unified shape (`--kv-unified --cache-ram`, kv-unified-stack-rollout.md) and on the frontdoor. N ∈ {1, np, 2·np}; gap lengths = HSF-3's harness-class p50/p90 (heterogeneous-slot-fabric-residency.md). Per turn, keyed by `x_session_id`: `cache_n` vs `prompt_n`, with each forced re-prefill attributed to one cause — (a) hybrid checkpoint (`forcing full prompt re-processing`, the #25592 class above), (b) prefix rewrite (request bytes differ at or before the cached prefix), (c) cross-session eviction during the gap (neither a nor b). Only (c) is what session-keyed admission (kv-unified-stack-rollout.md KVU-14) fixes; ThunderAgent matched vLLM within noise when the working set fit (intake-1816#7). Decision rule: KVU-14 opens only if cause-(c) re-prefilled tokens are ≥10% of all prompt tokens at some N ≤ 2·np in BOTH windows; otherwise BOUNDED-NULL-1 with the N and gap range covered. Belief kernel: VB-MT-REPLAY.
  ```
- **Six controls:**
  1. **Frozen input manifest:**
     - Replay-transcript set digest: HS-4 P0.4 OpenCode transcripts plus the existing multi-turn set.
     - Binary and kernel-store digests, `verify_ggml_linkage.sh` output, argv, the N grid.
     - HSF-3 receipt digest.
  2. **Incumbent baseline:** N = 1, the (G) row's single-session replay, run in the same window.
  3. **Per-item raw outputs:** per-turn rows (session, turn, prompt_n, cache_n, cause, log-excerpt hash).
  4. **Holdout:** a later-window replicate at N = 2·np.
  5. **Complete denominator:** every turn of every session. Turns without `cache_n` count as unattributed.
  6. **Predeclared decision rule:** as stated in the paste above.
- **Window:**
  - A bus-granted window, plus a region claim acquired for the CPU instance and an MI210 lease for the kvu shape.
  - It shares the (G) row's run.
  - It is never concurrent with DAR-LAT-3 or PF1, which are both whole-host windows.
- **Deps:** HSF-3 (gap lengths) and the (G) row instrument.

#### P4-11 — KVU-14: session-keyed admission hold on shared-pool servers (design, gated on G5)
- **Rows:** 2b-thunderagent-A2. **Sources:** intake-1816#1, #4, #6.
- **Owner:** `kv-unified-stack-rollout.md` (RTG-57). Its status is ACTIVE, with no restriction.
- **Posture:** monitor. It is a design row that opens only on G5's rule. RTG-57's `Next action` is unchanged.
- **Paste:** in "### B — orchestrator" (:163), after KVU-13c and before "### C — kernel candidate (v11, guarded)"
  (:218).
  ```
  - [ ] **KVU-14 — session-keyed admission hold on shared-pool servers (DESIGN; opens only if dynamic-stack-concurrency.md G5 finds cross-session eviction).** ThunderAgent's contract (intake-1816#1, intake-1816#4, intake-1816#6): a session is REASONING while a request is in flight and ACTING from response completion; capacity = the unified KV pool plus `--cache-ram`; under pressure, hold the NEXT turn of the smallest idle (ACTING) sessions at admission — never mid-decode — and resume shortest-first with hysteresis and a forced-resume timeout (HSF-3 p99). Optionally back the hold with `POST /slots/{id}?action=save` to RAM (the verb KVU-5 uses). Reads the ONE session table (heterogeneous-slot-fabric-residency.md tracked-session index; identity from harness-selection-and-integration.md HS-16); shares the admission queue with KVU-5/KVU-6; no second occupancy notion. Upstream ThunderAgent and Dynamo's plugin are not deployable here (vLLM/SGLang backends only; Dynamo frontend only).
  ```
- **Deps:** G5, HS-16 and HSF-3.

#### P4-12 — Cost bound on the D-d notes admission gate  *(FOLD into P1-F)*
- **Rows:** 2b-proxifield-A1. **Sources:** intake-1820#1, #3, #4; intake-1803#4.
- **Owner:** `repl-session-memory-maturity.md` (EVL-36). **Posture:** monitor (acceptance criteria on the unbuilt D-d).
- **Amendment:** in P1-F's deliverable, append to the "*Admission gate for shared or pinned notes.*" sub-bullet:
  ```
  Cost bound (intake-1820#1, intake-1820#3, intake-1820#4): writes are event-triggered (a subtask result or a new grounded fact), never every step; the verbatim-anchor check runs against the writer's own tool/REPL output at 0 LLM calls; summary/gist compression and any LLM faithfulness stage stay OFF unless an A/B on a fact-pooling workload shows they pay; budget ≤1 extra model call per admitted note. The only independent cost curve for a DeLM-style board (synchronous, every agent writes every step, 5N calls per round) runs 10.8–12.6× no-communication at every N, and its one win is fact pooling.
  ```

#### P4-13 — Routing-evaluation caution in LRC  *(FOLD into P2 edit 4; knowledge-only)*
- **Rows:** 2b-evoharnessbench-A3. **Source:** intake-1821#7.
- **Owner:** `learned-routing-controller.md` is "FROZEN for expansion" (:5), so it gets no task. P2 edit 4 already
  appends a no-checkbox section there.
- **Paste:** in P2 edit 4, after the "**Rollout precondition (prose).**" paragraph.
  ```
  **Evaluation caution (2026-09-26, intake-1821#7).** In EvoHarnessBench's delegation study, specialist-selection precision stays around 90%, yet 78–86% of trials that reach every required specialist still fail their verifier: a metric that scores only role choice misses the dominant failure. GPT-5-only and enterprise-workflow-only, so a hypothesis for our traces. If LRC-2 is evaluated for rollout, report realized task outcome beside role agreement; decision-aware-routing.md DAR-LAT-3 already grades realized quality per request.
  ```

#### P4-14 — OD-A: upstream SGLang is not a gfx90a route  *(FOLD into P3-4; this is Task B)*
- **Rows:** 2b-sglang-kt-integration-A1, with A3 and A4 recorded as declines in R-A10.
- **Sources:** intake-1818#0, #2, #3, #4, #6.
- **Owner:** `fable5-window2-findings-02-heterogeneous-gpu.md` (EVL-20). P3 has already checked it is not frozen.
- **Posture:** knowledge-only.
- **Deliverable:** the text in **Fill for P3-OD-A-ROCm** below.

#### P4-15 — numa P/D stub: record the Dynamo XPU/CPU example as a declined port  *(FOLD into P3-1 deliverable 4)*
- **Rows:** 2b-dynamo-pr7977-A3 (decline). **Sources:** intake-1817#0, #2, #5.
- **Amendment:** add a second row to P3-1 deliverable 4, the Research Context table at `numa-prefill-decode-
  disaggregation.md:20-26`.
  ```
  | intake-1817 | Dynamo PR #7977 — heterogeneous XPU-prefill / CPU-decode example | declined (port) | dive-verified. Examples-only launch scripts; no device-class routing or Planner support (intake-1817#0, intake-1817#2). The mechanism lives in vLLM's CPU_ATTN decoder + NIXL KV transfer (intake-1817#5); we serve llama.cpp, dual residents are quant-asymmetric, and the in-process op-offload split (correction note) needs no KV handoff. |
  ```

---

### Fill for P3-OD-A-ROCm

Replace P3's placeholder item (`P3.md:211-221`) with this item:

#### P3-OD-A-ROCm — upstream SGLang is NOT a gfx90a route for a kt-kernel CPU-expert half (filled from Stage-2b intake-1818)

- **Sources:** intake-1818#0, #2, #3, #4, #6 (dive-verified at `sgl-project/sglang@c73f7077`, upstream main HEAD on
  2026-09-26). Row: 2b-sglang-kt-integration-A1. Declines: A3 and A4.

**Answers to the four questions the placeholder asked.**
1. **Can a kt-kernel GPU half ride upstream SGLang's ROCm build?** No, as shipped. There are three independent
   blockers:
   - **API break.** The upstream wrapper never passes the `gpu_experts_mask` argument that every kt-kernel release
     since v0.5.1 requires, so it binds only to kt-kernel ≤ v0.5.0.post1. Fix PR #20516 is open (`intake-1818#2`).
   - **No gfx90a build.** Upstream's documented ROCm build exits for any arch other than gfx942/gfx950/gfx1250, and
     community PR #17082, which would have added gfx90a, was closed unmerged (`intake-1818#3`).
   - **No packaging.** No SGLang artifact packages or tests KT (`intake-1818#4`).

   The glue itself is unguarded and uses torch.cuda stream handles. That is necessary for a ROCm route but not
   sufficient, and nothing was built or run.
2. **intake-923 point (4).** #11425 names an umbrella issue that a github-actions inactivity bot closed. The
   integration *was* merged: five PRs, 2025-10-21 to 2025-11-26 (`intake-1818#0`). Upstream carries only that
   Nov-2025 feature subset, and the fork's scheduling features are absent (`intake-1818#6`). This is evidence that
   the merge was accepted, not evidence of maintained production use.
3. **Should F6's ROCm arm target the upstream wrapper?** No.
   - The upstream wrapper cannot bind to any current kt-kernel, and its SGLang build refuses gfx90a.
   - sglang-kt is CUDA-packaged.
   - F6's ROCm arm, if it runs at all, builds kt-kernel's HIP shim only (`CPUINFER_USE_ROCM=1`,
     `PYTORCH_ROCM_ARCH=gfx90a`). That is P3's fallback text, now confirmed.
4. **Disposition and R-A10 line.** intake-1818 is `integrated`, following P3's convention for R-A10 inputs. Its line
   in R-A10 is fact 3 below.

**(a) R-A10 fact 3, final sentence.** In P3-4 deliverable 6, replace
"Upstream-SGLang route: **P3-OD-A-ROCm — pending Stage-2b sglang-kt-integration (owning session fills).**" with:
```
        Upstream-SGLang route: **none for gfx90a** (intake-1818, dive-verified at sgl-project/sglang@c73f7077). Its KT wrapper is
        API-broken against every kt-kernel ≥ v0.5.1 (required `gpu_experts_mask` never passed; fix PR #20516 open) (`intake-1818#2`);
        its documented ROCm build exits for any arch but gfx942/gfx950/gfx1250 (`intake-1818#3`); no SGLang artifact packages or
        tests KT (`intake-1818#4`). #11425's "closed completed" is an inactivity-bot close; the Oct–Nov 2025 merge is real, and
        upstream carries only that feature subset (`intake-1818#0`, `intake-1818#6`). Revival needs #20516 merged AND gfx90a admitted
        upstream; F1 still gates. Porting SGLang to gfx90a is declined: a second serving substrate beside the frozen fork.
```

**(b) Option C row of the R-A10 table.** Replace it with:
```
     | C | Evaluate the KT runtime end to end on gfx90a | high: a forked SGLang beside the v10 fork | **no route exists** (fact 3): the fork is CUDA-packaged, and upstream SGLang refuses gfx90a and is API-broken against current kt-kernel; contradicts "the fork is the substrate" (§1.4) |
```

**(c) Recommendation. This changes P3's B to A, for the assembler to accept.** In R-A10, replace the
"**Recommendation: B.** …" line and the "**The decision:** …" line with:
```
     **Recommendation: A** (revised 2026-09-26 after Stage-2b intake-1818). With no gfx90a route for the GPU half, the runtime question is answered for this host; F6 would only prove that the CPU half builds, and no pending decision consumes that fact. Keep Expert Deferral as a technique behind F1 (R-A8). Option B stays valid if the operator wants the Zen-5 build fact on record.
     **The decision:** decline KTransformers as a runtime now and keep only the Expert Deferral technique path behind F1 (A), or also authorize the build-only kt-kernel check F6 as evidence (B)?
```
Consequential text changes:
- **P3-4 deliverable 5, the successor box.** It becomes `**OPERATOR DECISION — OD-A runtime question (R-A10): decline
  KT as a runtime and keep only Expert Deferral behind F1 (recommended), or also authorize F6 (build-only kt-kernel
  check) as evidence** — master queue OP-61`.
- **P3-4 deliverable 9, the OP-61 row.** Replace the Decision cell with `OD-A (KTransformers): decline KT as a runtime
  and keep only Expert Deferral behind F1 (recommended), or also authorize the build-only kt-kernel check F6`.
- **P3 Open questions item 1.** Change it the same way, with *Recommendation: A*.
- **P3-5.** Unchanged ("only if OD-A = B").
- **P3-5 broader trigger.** Replace "and P3-OD-A-ROCm to show a route" with "and a gfx90a ROCm route to exist, which
  intake-1818 shows does not today".
- **OD-A itself stays the operator's.** Only the recommendation's premise changed.

**(d) R-A8 note (A1's R-A7/R-A8 note).** Append after P3-4 deliverable 3's R-A8 note:
```
   *Note 2026-09-26 (Stage-2b, intake-1818):* "not recommended: adopting KTransformers as a runtime" is reinforced — upstream SGLang is not an escape hatch from the CUDA-pinned sglang-kt fork on gfx90a: its KT wrapper is API-broken against every kt-kernel ≥ v0.5.1 (intake-1818#2), its documented ROCm build refuses gfx90a (intake-1818#3), and no SGLang artifact packages KT (intake-1818#4). F1 remains the first step.
```

**(e) intake-923 `dive_corrections`, P3 S14.** Replace the trailing bracket "[Point (4) "#11425": pending Stage-2b —
P3-OD-A-ROCm fills.]" with:
```
(3) NARROWED — "SGLang adopting KTransformers as a CPU-kernel backend (sgl-project/sglang#11425) — third-party production adoption is real corroboration": the integration WAS merged upstream (five PRs, 2025-10-21..2025-11-26), but #11425's "closed completed" is a github-actions inactivity close, upstream carries only the Nov-2025 feature subset, and its wrapper is API-broken against every kt-kernel ≥ v0.5.1; it corroborates that maintainers accepted the merge, not maintained production use (intake-1818#0, intake-1818#2, intake-1818#6).
```

**Until the fill lands,** R-A10 fact 3 must NOT carry P3's placeholder text into the handoff. Apply (a) together with
P3-4 deliverable 6.

---

### Explicit declines

| Row | Decline, with reason | Recorded in |
|---|---|---|
| 2b-routerwise-A3 | A joint placement+routing optimizer. RouterWise's own Figure 6 shows no material gain over sensible fixed rules in most cells (intake-1815#4). Its deployed comparison confounds placement with latency-blind baselines (intake-1815#5). MPS fractional compute has no counterpart when the GPU footprint is fixed at launch. Placement is a gated Layer-2 or signed stack change, not an optimizer output. Reopen only if DAR-LAT-3 shows static-prior losses that track placement. | fabric: P2 edit 2b section, new DECLINED paragraph (text below) |
| 2b-thunderagent-A4 | Forwarding tool start/end events. Neither ThunderAgent's code nor the Dynamo port consumes them; ACTING is inferred from response completion (intake-1816#4, #6). Revisit only if a tool-duration predictor is pursued. | the HS-16 lifecycle clause (P4-8) |
| 2b-thunderagent-A5 | Deploying upstream ThunderAgent or Dynamo's plugin. They support only vLLM/SGLang backends and run only inside `dynamo.frontend` (intake-1816#6). The pattern transfers as KVU-14; the component does not. | DSC 2026-09-26 section (merged with P2 edit 6; see R1) |
| 2b-dynamo-pr7977-A3 | Porting Dynamo's XPU-prefill/CPU-decode example. It is vLLM-specific, a KV handoff is invalid for quant-asymmetric residents, and the fabric chose re-prefill teleport. | P4-15 (numa context row) |
| 2b-sglang-kt-integration-A3 | Porting upstream SGLang to gfx90a. It would be a second serving substrate beside the frozen fork, would still need #20516, and F1 gates first. | R-A10 fact 3 (Fill (a)) |
| 2b-sglang-kt-integration-A4 | A watch task on PR #20516. A merge fixes only the API blocker; the gfx90a refusal is independent. The revival trigger lives in intake-1818 `reader_should_conclude`. | R-A10 fact 3 ("Revival needs …") |
| 2b-talaria-A4 | Porting Talaria's cold-pool mechanisms. They are SGLang/VMM/CUDA-graph engine internals, cold-pool decodes are time-sliced (mid-generation parking breaks axiom 4), the kernel is frozen, and Talaria pins stable traffic to hot instances (intake-1819#3, #6, #8). | fabric C5-A2 decline paragraph (text below) |
| 2b-proxifield-A2 | Embedding-routed peer-to-peer messaging between REPL workers. At N = 5 Proxifield only ties a central orchestrator; its advantage appears at N ≥ 25 in one simulated environment with no released code (intake-1820#7). | intake entry only (`tri-role-coordinator-architecture.md` is frozen for TR-4/5) |
| 2b-evoharnessbench-A2 | The hosted EvoHarnessBench eval service. It needs an account key, installs via curl-pipe-bash from an ngrok endpoint (a supply-chain risk), its tasks are GPT-5-calibrated, and nothing tests model-heterogeneous harnesses (intake-1821#9). | intake entry only |

**Paste texts for the two fabric declines.** Both go into P2 edit 2b.
- Append to the Aegaeon "DECLINED" bullet list:
  ```
  - Talaria's cold-pool mechanisms (session-prefill mid-slot admission, bump-managed HBM, host KV registry, D2D weight staging) are declined on the same grounds: SGLang/VMM/CUDA-graph engine internals, and cold-pool decodes are time-sliced across rounds — mid-generation parking, which axiom 4 forbids. Talaria itself pins stable traffic to never-switching hot instances, which is our role shape and supports static residency (intake-1819#3, intake-1819#6, intake-1819#8).
  ```
- New paragraph after the 2605.19593 decline:
  ```
  **DECLINED — a RouterWise-style joint placement+routing optimizer (2b-routerwise-A3; intake-1815#4, intake-1815#5).** Its own Figure 6 shows a sensible fixed allocation rule matching or nearly matching the searched setup in most cells (predicted score, not measured); its deployed comparison pits it against latency-blind routers on isolated placement; its fractional-compute knob (MPS caps) has no counterpart when the GPU footprint is fixed at launch (contention rider :192-194). Placement here is a gated Layer-2 or signed stack change. Reopen only if decision-aware-routing.md DAR-LAT-3 shows static-prior losses that track placement.
  ```

---

### Stage-4 intake-index edits (exact text)

**E1 — 2b-routerwise-A4, intake-1796 `contradicting_evidence[5]`.** Replace "RouterWise (arXiv 2604.10907, not dived)
argues latency depends jointly on placement and routing. RouteBalance takes placement as fixed." with:
```
RouterWise (intake-1815, dive-verified; arXiv 2604.10907) shows a latency prior must be conditioned on the deployed placement — its latency model is per (model, setup) and its own runtime router is a static profiled prior with no live arm (intake-1815#0, intake-1815#6). Its only placement-isolating arm (Study 1) does NOT show material gain from searching placement over a sensible fixed rule in most cells; material gaps appear only at G=4, lambda 50-60 (+0.018/+0.028 predicted score over Equal-Split, +0.064 over whole-GPU Isolated), and the "87%" headline is a worst-to-best spread (intake-1815#3, intake-1815#4). All scores are predicted from profiled curves on homogeneous A100s. Scope condition for claim 2: key the static prior by (role, placement), not role alone.
```
Also add `intake-1815` to intake-1796 `cross_references.intake_entries`.

**E2 — 2b-talaria-A5, intake-1789 `contradicting_evidence[1]`.** Replace the whole line with:
```
Talaria (intake-1819, dive-verified; arXiv 2607.17181, independent, section 2.3) critiques round-based token-level schedulers 'such as Aegaeon' for agent sessions: when a tool returns, the session's KV may still be in HBM but its model window may have closed, so it waits up to one round. Talaria MEASURES this failure mode on its own Aegaeon-like round-scheduler ablation in SGLang (disabling session-prefill: p50 session completion time 623 s vs 189 s, intake-1819#10), not on Aegaeon itself, so it is still not a measured refutation of Aegaeon. Talaria also keeps static residency for stable traffic (hot instances never switch, intake-1819#3). Bears directly on RLM/agent workloads.
```
Also add `intake-1819` to intake-1789 `cross_references.intake_entries`.

**E3 — 2b-sglang-kt-integration-A2, intake-1809.**
- (i) In `key_claims[3]`, replace the last sentence "Upstream SGLang@c73f7077 carries a small (393-line) generic KT
  wrapper built on torch.cuda stream handles, a possible but untested ROCm route." with:
  ```
  Upstream SGLang@c73f7077 carries a small (393-line) generic KT wrapper built on torch.cuda stream handles, but it is NOT a gfx90a route: it is API-broken against every kt-kernel >= v0.5.1 (required gpu_experts_mask never passed; fix PR #20516 open) and upstream SGLang's documented ROCm build refuses gfx90a (intake-1818#2, intake-1818#3).
  ```
- (ii) Replace the existing `claim_corrections` row for `claim_index: 3`, so there is one row per claim, with:
  ```yaml
  - claim_index: 3
    effect: narrowed
    note: "The ROCm story is 'untested option', not 'absent'. kt-kernel has the ROCm build flag and HIP shim; the AMD test is a placeholder, ROCm.md run steps are archived-era (a Hygon gfx936 build note was added 2026-07-06), the sglang-kt package is CUDA-pinned, and the fork's INT4 GPU-expert prep path has a CUDA-only import. 2026-09-26 Stage-2b (intake-1818): the upstream SGLang KT wrapper is NOT a live ROCm route — API-broken vs kt-kernel >= v0.5.1 and on an SGLang build that refuses gfx90a."
  ```
- (iii) Add to `depends_on`:
  `{entry: intake-1818, claim_index: 2, why: "claim 3's upstream-route sentence rests on the API break"}` and
  `{entry: intake-1818, claim_index: 3, why: "claim 3's upstream-route sentence rests on the gfx90a build refusal"}`.

**E4 — 2b-sglang-kt-integration-A2, intake-923 `dive_corrections`.** This uses the text in Fill (e), which goes inside
P3 S14's appended paragraph. `dive_corrections` history is append-only. The original 2026-07-29 sentence stays, and no
`claim_corrections` row is added (P3 S14 gives the reason).

**E5 — recommended, from `effect_on_bearing_entry` (not derived_actionables).** intake-1803 `contradicting_evidence`.
- Replace `[0]` with:
  ```
  Proxifield (intake-1820, dive-verified; arXiv:2609.20889) implements a DeLM-INSPIRED shared context — synchronous rounds, no task queue, every agent writes every step, bounded board, checks on each agent's own model, 5N calls per round (intake-1820#1). Independent and adverse on cost: the most expensive protocol in every experiment, 10.8-12.6x no-communication at every N (intake-1820#3). "Consistently underperforms" holds against Star and Proxifield on DroneSwarm only: it beats no-communication at N=5 and N=25 and trails within SEM at N=50 (intake-1820#2), and on HiddenBench fact pooling it is the best protocol at 35B-A3B (intake-1820#4). The same N=25 condition gives 11.5 in one table and 6.0 in another (intake-1820#6).
  ```
- Replace `[1]` with:
  ```
  EvoHarnessBench (intake-1821, dive-verified; arXiv:2609.04280) runs a re-implemented DeLM (shared task pool, up to 3 workers, plus a benchmark-added per-agent raw memory DeLM lacks — intake-1821#3). Table 2: DeLM is last (EOG 20.3±1.8, overall 18.7, most time and tokens), but the comparator AutoGen is effectively a single solver loop on this axis, so the result is about parallel decomposition on stateful workflows, not the shared verified context; run count behind ± unstated (intake-1821#4). On the agents axis DeLM is mid-pack (intake-1821#6). "Memory can even hurt DeLM" concerns the bolted-on cross-task memory, not DeLM's shared context (intake-1821#5).
  ```
- Add `intake-1820` and `intake-1821` to `cross_references.intake_entries`.

intake-1785 edits, also recommended:
- Add `intake-1816` and `intake-1817` to `cross_references.intake_entries`.
- Append to the `claim_corrections` row for `claim_index: 7`: " 2026-09-26 Stage-2b (intake-1817): the v1.5.0 CPU-decode
  addition is examples-only launch scripts; the router sees a CPU decode worker as an untyped decode worker and the
  Planner budgets GPUs (intake-1817#0, intake-1817#2, intake-1817#3)."

**E6 — intake-1815 `key_claims[4]` recount (second-reader substantive flag).** Replace "in 5 of 8 panels" with "in 6 of
8 panels", and add:
```yaml
claim_corrections:
  - claim_index: 4
    effect: narrowed
    note: "2026-09-26 second reader: the enumerated panels (G=4 lambda 70/80; G=8 lambda 50/60/70/80) are six, not five; the count understated the contradiction. Gaps and above-tau points re-checked and unchanged."
```

**E7 — intake-1819 `claim_corrections` (second-reader substantive flag on claim 11).** Add:
`{claim_index: 11, effect: narrowed, note: "Second reader: the section-5.3 paragraph's headline is the MEDIUM-load SCT
gain, which the claim omits; the high/low-load statements stand. The claim understates the router's measured
benefit."}`. P4 cites #11 only qualitatively.

---

### Belief-kernel wiring (P4's rows; see R4 for the consolidated section)

**vidya program: task lines.** Placed per R4.
```
- [ ] **VB-GAP-DIST — wire the write side of the session inter-call gap measurement** (`heterogeneous-slot-fabric-residency.md` HSF-3) before its first extraction: one row per gap (session hash, role, client class, t_done, t_next, gap_s, source), with the log-manifest digest, extractor revision and window. Locator = window × class; W1 and W2 never pool. Observation-grade.
- [ ] **VB-MT-REPLAY — wire the write side of the multi-turn replay** (`dynamic-stack-concurrency.md` "(G) #25592" row and its G5 extension) before the first replay: per-turn rows keyed by `x_session_id` with prompt_n, cache_n, forced-re-prefill cause (a/b/c/unattributed), N, gap lengths and the HSF-3 receipt digest, plus binary/store digests and argv. Locator = run × N. Project; do not grade.
```
**Activation records.** No checkbox. They go under the existing "**Durable activation triggers — these are records, not
active tasks**" list (:2941).
```
- **VB-SPILL-TTFT:** activate when the fabric's spillover partial-offload arm (heterogeneous-slot-fabric-residency.md, under the GPU-as-placement-target task) is scheduled. Bind r grid, load points, served artifacts and store digests, P-GPU-1 device-state capture, per-request TTFT/TPOT/outcome class and completed-requests/min; the Dynamo PR ratios are never projected.
```
**adapters README: rows** appended after `:321` per R4.
```
| Session inter-call gap distribution (`heterogeneous-slot-fabric-residency.md` HSF-3; orchestrator inference-tap events, progress-log session events, `/chat` checkpoints) | measurement | **not wired; filed at design time, before the first extraction (2026-09-26).** One row per gap: session hash, role, client class, t_done, t_next, gap_s, source; log-manifest digest + extractor revision. Locator = window × class; W1/W2 never pool. Task row: VB-GAP-DIST | none (planned) |
| Multi-turn agentic replay (`dynamic-stack-concurrency.md` "(G) #25592" row + G5 N-session tool-gap extension) | measurement | **not wired; filed at design time, before the first replay (2026-09-26).** Per-turn rows keyed by `x_session_id`: prompt_n, cache_n, forced-re-prefill cause (a/b/c/unattributed), N, gap lengths, binary/store digests, argv. Locator = run × N. Task row: VB-MT-REPLAY | none (planned) |
| Fabric spillover partial-offload arm (`heterogeneous-slot-fabric-residency.md`, GPU-as-placement-target task) | measurement | **trigger-gated — materialize VB-SPILL-TTFT before the arm is scheduled.** Then bind r grid, load points, device-state capture, per-request TTFT/TPOT/outcome class. | none |
```

---

### Intake-entry dispositions (Stage 4 sets)

| Entry | handoffs_updated | integration_disposition | disposition_evidence (one line) |
|---|---|---|---|
| intake-1815 | decision-aware-routing.md, heterogeneous-slot-fabric-residency.md | integrated | "DAR-LAT-2's static prior keyed by (role, device, topology_hash); traffic-share vs allocation added as a Layer-3 regime-change input; joint optimizer declined (Stage 4, 2026-09-26)." |
| intake-1816 | dynamic-stack-concurrency.md, kv-unified-stack-rollout.md, harness-selection-and-integration.md | integrated | "G5 N-session tool-gap replay gates KVU-14 (session-keyed admission hold); HS-16 gains the end-of-session signal plus idle TTL; tool-event forwarding and component deployment declined." |
| intake-1817 | heterogeneous-slot-fabric-residency.md, numa-prefill-decode-disaggregation.md | knowledge_only | "No upstream device class: EPYC slot fields kept; spillover partial-offload arm specced on the gated fabric task; XPU/CPU example port declined." |
| intake-1818 | fable5-window2-findings-02-heterogeneous-gpu.md | integrated | "R-A10 fact 3: upstream SGLang is not a gfx90a route (API break, gfx90a refused, unpackaged); option C loses its precondition; OD-A recommendation revised to A." |
| intake-1819 | heterogeneous-slot-fabric-residency.md | integrated | "HSF-3 gap-distribution measurement filed; swap protocol amended to session quiescence plus save-before-forced-swap; KV-recovery term specced; cold-pool port declined." |
| intake-1820 | repl-session-memory-maturity.md | integrated | "D-d admission gate gains a cost bound (event-triggered writes, 0-LLM anchor check, ≤1 call per note); P2P messaging declined." |
| intake-1821 | harness-selection-and-integration.md, learned-routing-controller.md | integrated | "HS-4 P6 catalog-growth retention check (via SC86); LRC evaluation caution recorded; hosted eval service declined." |
| intake-1796, 1789, 1809, 923, 1803, 1785 | no change to the dispositions P1-P3 set | as P1-P3 | E1-E5 above edit evidence fields only. |

**Surfaced sources (not this round, listed for the operator's next selection).**
- arXiv:2511.02230 (Continuum, KV time-to-live across tool calls). Two dives recommended it (thunderagent, talaria), and
  it would sharpen HSF-3's τ use and KVU-14.
- arXiv:2603.28990 (proxifield).
- arXiv:2510.04851 (LEGOMem; evoharness).
- vLLM #43563 (dynamo). This is a Xeon socket-split P/D test. On our single-socket host (P3-1) its bearing is small.

---

### Coverage table

| Row | Maps to |
|---|---|
| 2b-routerwise-A1 | P4-1 (fold → DAR-LAT-2) |
| 2b-routerwise-A2 | P4-2 (fold → P2 edit 2a, :152) |
| 2b-routerwise-A3 | decline (fabric DECLINED paragraph) |
| 2b-routerwise-A4 | E1 (intake-1796) |
| 2b-thunderagent-A1 | P4-10 (DSC G5) + VB-MT-REPLAY |
| 2b-thunderagent-A2 | P4-11 (KVU-14) |
| 2b-thunderagent-A3 | P4-8 (fold → HS-16) |
| 2b-thunderagent-A4 | decline (HS-16 clause) |
| 2b-thunderagent-A5 | decline (DSC 2026-09-26 section) |
| 2b-dynamo-pr7977-A1 | P4-3 (fold → P2 edit 2b) |
| 2b-dynamo-pr7977-A2 | P4-4 (spec under :148) + VB-SPILL-TTFT |
| 2b-dynamo-pr7977-A3 | decline, P4-15 (fold → P3-1 deliverable 4) |
| 2b-sglang-kt-integration-A1 | P4-14 / Fill (a)(d) (fold → P3-4) |
| 2b-sglang-kt-integration-A2 | E3 (intake-1809) + E4 / Fill (e) (intake-923) |
| 2b-sglang-kt-integration-A3 | decline (R-A10 fact 3) |
| 2b-sglang-kt-integration-A4 | decline (R-A10 fact 3 revival clause) |
| 2b-talaria-A1 | P4-5 (HSF-3) + VB-GAP-DIST |
| 2b-talaria-A2 | P4-6 (dated amendment + fold → P2 edit 2a) |
| 2b-talaria-A3 | P4-7 (spec under :151) |
| 2b-talaria-A4 | decline (fold → P2 C5-A2 paragraph) |
| 2b-talaria-A5 | E2 (intake-1789) |
| 2b-proxifield-A1 | P4-12 (fold → P1-F) |
| 2b-proxifield-A2 | decline (intake entry) |
| 2b-evoharnessbench-A1 | P4-9 (HS-4 P6 acceptance; SC86) |
| 2b-evoharnessbench-A2 | decline (intake entry) |
| 2b-evoharnessbench-A3 | P4-13 (fold → P2 edit 4, knowledge-only) |
| P3 placeholder P3-OD-A-ROCm | Fill for P3-OD-A-ROCm |

All 26 rows are covered, and so is the placeholder.

---

### Reconciliation

#### R1 — ID collisions and duplicate ownership

**IDs.** No ID is used twice across P1-P4, with one exception:
- **P2's master row `OP-<next>`.** It must be **OP-62**. P3 takes OP-61, and OP-60 is already DS41's
  (`progress/2026-09/2026-09-26-ak-ds41-main.md:126`). Fix: in P2's "Master index, operator queue" line, set
  `| OP-62 | Ratify P-SERVE-SEL-1 … |`. Re-verify both IDs against origin/main at apply.

**Duplicate ownership, with fixes:**
1. **c2-A1 (the `/v1` Retry-After) has two homes in the text.** P1 owns it in `harness-selection-and-integration.md`
   (HS-OD-8/9). P2 still points it at `dynamic-stack-concurrency.md` in three places. Fix:
   - `P2.md:371` DAR-LAT-1 line: replace "the chat-door Retry-After derivation (dynamic-stack-concurrency.md, c2-A1)"
     with "harness-selection-and-integration.md HS-OD-9 (the `/v1` Retry-After derivation, c2-A1)".
   - `P2.md:20` packet table: in "Blocks", replace "P1's Retry-After (c2-A1)" with "HS-OD-9 (harness handoff)".
   - `P2.md:30-31`: replace "(c2-A1, `dynamic-stack-concurrency.md`)" with "(c2-A1, harness-selection-and-integration.md
     HS-OD-9)". Delete the *Assembler note* at `P2.md:33-34`, because R2 resolves it.
   - `P2.md:580` (edit 6 preamble): delete "If P1 appends a 2026-09-26 section here for c2-A1, the assembler merges this
     block into it." P1 does not touch DSC.
2. **The shared wait estimator.** Resolved in R2.
3. **Session state was headed for four homes:** HS-16's resolver (P1), the fabric tracked-session index, KVU-14 and the
   Talaria recovery term. The fix is P4-7's text:
   - Identity = HS-16.
   - The ONE state table = fabric tracked-session index (:151).
   - KVU-14 and the recovery term are policies that read it.
   - The TTL value = HSF-3.
4. **The slot-save verb.** KVU-5, the P4-6 amendment and KVU-14 all use the existing `POST /slots/{id}?action=save`.
   There is one verb and no new code.
5. **R_cpu(L).** PF1 (P3-3) is the single producer. P3-2, P4-7 and DAR (T̂ prefill) are consumers only.
6. **DSC placement defect.** P2 edit 6 appends a bare bold paragraph after `:342`, which lands inside
   "### B3 (B, blocked on …)" (`:331`). Fix: put it under a new heading
   `## Research Intake Update — 2026-09-26 (orchestration prior art; intake-1783, intake-1816)` at EOF, then P2's
   c3-A3 decline, then this line:
   ```
   **DECLINED 2026-09-26 — deploying upstream ThunderAgent or Dynamo's thunderagent plugin in front of llama-server (2b-thunderagent-A5; intake-1816#6).** Upstream supports only vLLM/SGLang backends; Dynamo's plugin reads published GPU KV-block capacity and runs only inside dynamo.frontend. The orchestrator is already the single scheduler; the pattern transfers as kv-unified-stack-rollout.md KVU-14, the component does not.
   ```
   The G5 row goes under the (G) row (P4-10), not in this section.
7. **Fabric plan-approval scope.** In P2 edit 2b, HSF-1 says "Plan approval 2026-09-26 authorizes this item only; the
   rest of this list stays GATED." Replace it with "Plan approval 2026-09-26 authorizes HSF-1 and HSF-3 only (passive
   instrumentation and a log read); the rest of this list stays GATED." P2's HSF-1 prose "scoped to HSF-1 only" changes
   the same way.

#### R2 — One owner and one ID for the admission/wait estimator

- **Decision.** The owner is **`decision-aware-routing.md`, task DAR-LAT-1 (index row RTG-09)**. `RTG-07` and `C1-A2`
  are retired as names for this build.
- **Why:**
  - The rider behind RTG-07 is "DESIGN — audit + open questions. No code." (`contention-model-device-and-load-axes-
    rider.md:5`).
  - RTG-07's next action is Artifact 2/3 parameterization.
  - P2 already carries the build checkbox and its tests.
  - P1 already says HS-OD-9 "must not build a second estimator".
  - C1-A2 stays a ledger-row ID in the coverage tables only.
- **One interface, stated once in DAR-LAT-1:** `expected_wait_s(role, priority="interactive") -> (seconds | None,
  basis, source)`. The ledger already has the priority dimension (`AdmissionController._norm_priority`,
  `src/api/admission.py:140`). Each consumer applies its own fallback:
  - DAR-LAT-2 uses term 0 plus a penalty flag.
  - HS-OD-9 uses the constant header with `basis=constant`.

**Corrected Deps text, P2 side:**
- DAR-LAT-1 task line (`P2.md:371`): replace it with "Direct consumers: DAR-LAT-2 and harness-selection-and-
  integration.md HS-OD-9 (c2-A1). Interface: `expected_wait_s(role, priority="interactive")` returns seconds or None
  with `basis` and `source`; each consumer applies its own fallback."
- New stubs (`P2.md:648-649`): delete the "Optional Deps edge … RTG-11 (P1 Retry-After) …" bullet. RTG-11 is
  `dynamic-stack-concurrency.md`, not P1's row. Replace it with "UFH-01 `Deps` = `RTG-09` (applied once, on P1's row
  edit)."
- Cross-section flag "P1 ↔ P2 edge" (`P2.md:708`): mark it resolved (R2).

**Corrected Deps text, P1 side:**
- `P1.md:18-21`: replace with "**P2 dependency, named and not duplicated.** HS-OD-9 consumes `expected_wait_s(role,
  priority)` from decision-aware-routing.md DAR-LAT-1 (RTG-09), the one estimator on the admission ledger
  (`AdmissionController.get_status()`, `src/api/admission.py:229`). HS-OD-9 must not build a second estimator. HS-OD-8
  has no P2 dependency."
- `P1.md:38` and `:144`: replace "after P2's C1-A2 estimator lands" with "after DAR-LAT-1 lands (decision-aware-
  routing.md)".
- `P1.md:116-118`: replace with "**Dependency (provider):** DAR-LAT-1's `expected_wait_s(role, priority)`
  (decision-aware-routing.md, RTG-09); `None` falls back to the constant with `basis="constant"`."
- HS-OD-9 task line (`P1.md:128`):
  - Replace "(after HS-OD-8; consumes RTG-07's expected-wait estimate)" with "(after HS-OD-8; consumes decision-aware-
    routing.md DAR-LAT-1's `expected_wait_s`)".
  - Replace "the ONE dispatch-ledger estimator the RTG-07 saturation guard builds (C1-A2)" with "the ONE admission-ledger
    estimator, decision-aware-routing.md DAR-LAT-1".
- `P1.md:142`: replace "file the miss against RTG-07" with "file the miss against DAR-LAT-1 (RTG-09)".
- `P1.md:145`: replace "at RTG-07" with "at DAR-LAT-1".
- `P1.md:403-404`: replace with "the UFH-01 row's `Deps` changes from `—` to `RTG-09`. HS-OD-9 consumes DAR-LAT-1's
  estimator. UFH-01's `Next action` stays P0.4."
- The P1 coverage and decline tables are unaffected.

#### R3 — Index-row writes: one section per row

| Row | Edited by | Final value |
|---|---|---|
| UFH-01 `Deps` | P1 only | `RTG-09` (corrected from `RTG-07`) |
| RTG-09 `Next action` | P2 only | P2's text |
| INF-23 `Next action` | **P4 only.** This supersedes P2's optional HSF-1 wording. | `HSF-3 — publish per-session inter-call gap p50/p90/p99 from existing session-keyed logs; HSF-1 receipts accrue on GPU launches` (126 chars) |
| INF-44 `Next action` / `Deps` | P3 only | P3's text, `INF-34` |
| Master queue | P3 (OP-61, text revised by Fill (c)); P2 (OP-62) | two rows; no other master writes |
| RTG-07, RTG-11, RTG-15, RTG-42, RTG-57, EVL-20, EVL-36, INF-34, INF-70 | nobody | unchanged. G5, KVU-14 and PF1 stay discoverable via their handoffs and Deps edges |

Across P1-P4, no handoff gains a second row and no stub is created. Every handoff edited by more than one section
still has one owning row. Run `python3 scripts/handoffs/index_state.py --check` once after all four sections apply.

**Multi-section edits of the same file.** Apply by quoted text, not by line number.
- `heterogeneous-slot-fabric-residency.md`:
  - P2: :147 and :152 bullets, plus the EOF section.
  - P3-2: :77 replace, insert after :78, and a task after :153.
  - P4: an amendment after :89, bullets under :148 and :151, and additions inside P2's bullets and section.
  - Apply bottom-up. Sequence: P3-2 :153 → P2 :152 (+P4-2, P4-6b) → P4-7 :151 → P4-4 :148 → P2 :147 → P4-6a :89 →
    P3-2 :78/:77 → EOF section (P2 + P4-3/5 + declines).
- `harness-selection-and-integration.md`: P1 (seam section, HS-3 note, new EOF section) and P4-9 (under :88). The
  targets are disjoint.
- `fable5-window2-findings-02-heterogeneous-gpu.md`: P3-4 only, carrying the P4 Fill text.
- `decision-aware-routing.md`, `learned-routing-controller.md` and `repl-session-memory-maturity.md`: P4 edits only
  inside P2's or P1's own blocks.

#### R4 — Belief-kernel wiring: exactly one VB task and one README row per empirical item

| Empirical item | VB id | vidya line | README row | Status |
|---|---|---|---|---|
| HS-OD-9 live calibration (P1-B) | VB-V1-BACKPRESSURE | P1 | P1 | ok |
| DAR-LAT-3 load-sweep A/B (P2) | VB-SEL-LOADAB | P2 | P2 | ok |
| HSF-1 launch receipts (P2) | VB-SWAP-C | P2 | P2 | ok |
| PF1 prefill crossover (P3-3) | VB-PREFILL-XOVER | P3 | P3 | ok |
| HSF-3 gap distribution (P4-5) | VB-GAP-DIST | P4 | P4 | ok |
| DSC (G) replay + G5 (P4-10) | VB-MT-REPLAY | P4 | P4 | ok. One source covers both rows; the (G) row had none before. |
| Spillover arm (P4-4, gated) | VB-SPILL-TTFT (activation record) | P4 | P4 (trigger-gated) | ok |
| HS-4 P6 retention check (P4-9) | SC86 (existing) | existing | `README.md:304` | ok, no new row |
| **F6 build check (P3-5)** | **none in P3** | **add** | **add** | **gap: fix below** |
| **NPD-1 (P3-1 trigger)** | **none in P3** | **add** | **add** | **gap: fix below** |
| P1-F reuse reading | none | none | none | exempt. No producer exists until D-d is built; add the line below to P1-F's rigor. |

No VB ID or README source row is duplicated across the sections.

**Fix for the F6 and NPD-1 gaps.** Add activation records, following the `VB-FORMAL-1` precedent. They go under the
vidya "Durable activation triggers" list (:2941).
```
- **VB-KT-BUILD:** activate if OD-A = B authorizes F6 (fable5-window2-findings-02-heterogeneous-gpu.md R-A9). Bind kt commit, host cpuinfo flags, toolchain versions, env, build-log digests, per-arm attribute readout and failure class; project as a verified finding that updates intake-1809 claim 1, never as a performance claim.
- **VB-NPD-1:** activate when numa-prefill-decode-disaggregation.md's reopen trigger fires (PF1 finds L* ≤ 32K). Bind the served artifact and store digests, argv, the concurrent-prefill schedule, per-token decode TPOT with and without the concurrent prefill, and the manifest's predeclared inflation bound.
```
README rows, appended with the others:
```
| kt-kernel build-only check (F6, `fable5-window2-findings-02-heterogeneous-gpu.md` R-A9) | verified finding | **trigger-gated — materialize VB-KT-BUILD if OD-A = B authorizes F6.** Then bind commit, toolchain, env, build-log digests, attribute readout, failure class. | none |
| NPD-1 decode-inflation-under-concurrent-prefill run (`numa-prefill-decode-disaggregation.md`) | measurement | **trigger-gated — materialize VB-NPD-1 when PF1 reports L* ≤ 32K.** Then bind artifact/store digests, argv, prefill schedule, per-token TPOT both arms, the predeclared bound. | none |
```
Add to P1-F's rigor: "When D-d is built, file a VB row for the `/slots` reuse reading before its first run (the
repl-turn-efficiency.md :159 measurement has none today)."

**Placement conflict.** All four sections append a new `##` section at vidya EOF (after `:2961`), and all four append
README rows at the end of the one source table (header `:193`, last row `:321`). P1 names the header, and P3 names
`:232`; both refer to the same table. Fix:
- **One vidya section:** `## VB-V1-BACKPRESSURE / VB-SEL-LOADAB / VB-SWAP-C / VB-PREFILL-XOVER / VB-GAP-DIST /
  VB-MT-REPLAY — orchestration prior-art intake sources (filed 2026-09-26, research-intake)`.
  - Under it: one "filed at design time" sentence, then the six task lines in that order, pasted verbatim from P1, P2,
    P3 and P4.
  - The three activation records go into the existing list at :2941, not under this section.
- **One README append pass after `:321`**, in the order P1, P2, P3, P4 (including the two trigger rows above).
- Re-verify every VB ID against origin/main at apply time. The `/workspace` working copy holds uncommitted edits to
  both files (P3 raised this too).

#### R5 — Quotes from stage1-unverified entries

- **No section quotes a number or mechanism from a stage1-unverified entry.** Every mention in P1-P3 was checked: 1784,
  1786, 1788, 1793, 1794, 1795, 1799, 1800, 1801, 1802, 1804, 1805, 1806, 1807, 1811, 1812, 1813 and 1814. They are
  triggers, declines or lineage only. P4 quotes only intake-1815..1821, which are dive-verified.
- **Overturned entries:** P1 quotes only the corrected claims (intake-1792#1, #4; intake-1803#2, #6).
- **Citation-form fixes.** Writing *about* an entry is a citation (CLAUDE.md), so in handoff text use `#record`:
  - P1-E dormant-trigger prose (`P1.md:262-265`): change `intake-1786`, `intake-1800`, `intake-1806`, `intake-1794` and
    `intake-1793` to `intake-NNNN#record`.
  - P2 edit 1 MoA trigger: `intake-1799#record`, `intake-1802#record`.
  - P2 edit 3 triggers: `intake-1812#record`, `intake-1814#record`.
  - P2 edit 5: `intake-1784#record`.
  - The disposition tables are unaffected.
- **The inverse defect.** P3-4 deliverable 2 asserts the #1612 collaborator reply under `intake-1809#record`, and
  deliverable 4 asserts the HumanEval sampling under `intake-1808#record`. `#record` asserts nothing, so cite-check
  cannot gate those facts. Use the bare `intake-1809` and `intake-1808`, which rely on the whole dive-verified entry.
- **Verified entries with internal defects:**
  - intake-1815#4's "5 of 8" is fixed by E6.
  - intake-1819#11 is fixed by E7.
  - Neither number is quoted anywhere in P1-P4.

#### R6 — Other findings

- **Orchestrator anchor drift.** HEAD moved `fb7871ea` → `a439070e` (57 files).
  - Unchanged: every file P1/P2 cite by line — `admission.py`, `openai_compat.py`, `inference.py`, `hybrid_router.py`,
    `retriever.py`, `mcp_server.py`, `api/__init__.py`, `routes/chat.py`, `contention_gate.py` and `context_limits.py`.
  - **`scripts/server/orchestrator_stack.py` shifted +5 lines after :960.** P2's GPU launch path `:1259-1275` is now
    `:1264-1280`, and `--metrics` `:1267` is now `:1272`. Keep the `@fb7871ea` pin in the pasted text, or re-anchor at
    apply.
  - `model_registry.yaml` changed only at :13 and :2144+, so P2's `:1863-1916` and `:1899-1904` hold. `src/roles.py`
    changed, but P2 cites the `_FALLBACK_MAP` symbol, not a line.
- **The OD-A recommendation now differs from P3's (B → A).** See Fill (c). The operator decides OD-A either way. The
  change is the premise: no gfx90a route exists.

---

### Open questions for the operator

None new. OD-A (OP-61) is still the one operator decision this intake needs, and its recommendation is now A (Fill
(c)). The P-SERVE-SEL-1 ratification (P2, OP-62) is unchanged.
