# Internal Interaction Lifecycle

**Status**: queued behind contention/autopilot gate (P2-0 discovery complete; P1/P2 runtime work not started)
**Priority**: P0 for substrate cleanup; downstream of intake-655 deep-dive
**Created**: 2026-05-31
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md)
**Related**: [`delegation-context-preassembly.md`](delegation-context-preassembly.md), [`routing-intelligence.md`](routing-intelligence.md), [`hermes-outer-shell.md`](hermes-outer-shell.md), intake-655
**Provenance**: 2026-05-31 deep-dive on intake-655 (A2A protocol). Two-question framing: adopt A2A *lifecycle semantics* internally; defer A2A *wire transport*.

## Objective

Replace the implicit delegation loop shape in `epyc-orchestrator` with an explicit `Interaction` lifecycle abstraction modeled after A2A's task semantics. Use the same substrate for `delegate` and a new `consult` kind. Skill contracts described in a sibling YAML, keyed by role × skill, with typed advisory output schemas. Reuse every existing optimization machinery (region locks, contention gating, shared-backend aliasing, DCP context packaging, `delegation_cache`, MemRL telemetry) underneath.

## Non-Goals

- No internal A2A wire transport. No per-role A2A servers.
- No opaque-agent boundary inside the orchestrator. Region-lock / contention visibility preserved.
- No streaming consult in v1. Current `/chat/stream` wraps pipeline events, not backend tokens (`stream_adapter` calls `primitives.llm_call()` then emits events) — true concurrent integration requires backend streaming callbacks first.
- No multi-turn `input_required` consult in v1. Would require a local `ConsultationTask` store with terminal/interrupted states.
- No behavior change in P1.

## Current Execution Gate (2026-05-31)

Sequencing is locked:

1. **Now**: P2-0 discovery only — complete, no runtime change.
2. **After contention/autopilot bake is clean**: P1 lifecycle refactor.
3. **After P1 regression gate**: P2 one-shot consult at the P2-0 chosen attach point.
4. **After A/B evidence**: P3 consult gating, then P4 reward/eval.

Do not start P1 until the cross-role contention/autopilot bake gate is clean. P2-0 was safe because it was documentation/discovery only; P1 touches the delegation substrate and would otherwise contaminate live attribution.

## Core Model

New module `src/orchestration/interaction.py`:

```python
@dataclass
class Interaction:
    kind: Literal["delegate", "consult", "verify", "route"]
    owner_role: str
    callee_role: str
    skill: str
    state: Literal["created", "working", "input_required", "completed", "failed", "cancelled"]
    artifacts: list[ArtifactRef]            # report handles, advice bundles
    events: list[InteractionEvent]          # generalized DelegationEvent
    token_budget: int
    deadline: float | None
    scheduler_policy: SchedulerPolicy
    telemetry: InteractionTelemetry         # interaction_type, skill, context_hash, policy_version

INTERACTION_POLICY_VERSION = "1.0"
```

`InteractionEvent` generalizes `DelegationEvent` (`src/api/models/responses.py:19-30`) by adding `interaction_type: Literal["delegate", "consult", "verify", "route"] = "delegate"`. Default preserves backward compat with existing `delegation_events` consumers.

`SchedulerPolicy` is a thin dataclass wrapping the existing `ChatRequest` admission fields:

| Field | Maps to | Default for `delegate` | Default for `consult` |
|-------|---------|------------------------|-----------------------|
| `priority: str` | `ChatRequest.request_priority` (`requests.py:102`) | `"interactive"` | `"background"` |
| `max_queue_wait_ms: int \| None` | `ChatRequest.max_queue_wait_ms` (`requests.py:107`) | inherit | `2000` |
| `migration_budget_ms: int \| None` | `ChatRequest.migration_budget_ms` (`requests.py:114`) | inherit | `inherit` |
| `cancellable: bool` | NEW | `False` | `True` |

`InteractionTelemetry` carries `interaction_type`, `skill`, `context_hash`, `policy_version` for log emission and reward attribution.

## Invariants

| # | Invariant | Why | How to verify |
|---|-----------|-----|---------------|
| I1 | Region-lock visibility preserved across all interaction kinds | shape-aware contention (`inference.py:230`) depends on cross-role state; opacity would break the global region-mutex (see [[project_cross_role_contention_placement_blind]]) | `epyc-orchestrator/scripts/server/affinity_preflight.py` snapshot per phase |
| I2 | Shared-backend `topology_role` alias preserved | `coder_escalation` aliases `frontdoor` pool (`backend.py:90-140`); consult must dispatch under physical role | Live thread-union affinity vs `NUMA_CONFIG` (per [[feedback_verify_live_affinity_not_just_topology_hash]]) |
| I3 | `enable_thinking=false` per-role transport flags preserved | Qwen3.6 frontdoor + Qwen3.5-122B architect_general require thinking=off ([[feedback_qwen3x_enable_thinking_false]]); applies on `/v1/chat/completions` only ([[feedback_enable_thinking_requires_chat_completions_path]]) | Per-role chat completions probe |
| I4 | DCP remains advisory, not a hard context firewall | DCP-4 (`chat_delegation.py:247-289`) explicitly "advisory only; reactive discovery stays fully enabled" | Reactive top-up still works in consult mode |
| I5 | Legacy delegation telemetry readable for one rev | External MemRL / log / wandb consumers may read `delegation_events` / `DelegationEvent` field name; rename must alias-not-break | Field alias verified in `delegation_events` consumers; old name still serializes |
| I6 | One-shot only in P2; no `input_required` consult | Multi-turn consult requires `ConsultationTask` store; out of scope for v1 | API rejects multi-turn consult requests with `UnsupportedOperationError` parity |

## Phase Plan

### P1 — Lifecycle refactor, no behavior change

**Goal**: Express the existing delegation loop in the `Interaction` abstraction without changing behavior.

- [ ] **P1-1**. Create `src/orchestration/interaction.py` with `Interaction` dataclass, `InteractionEvent`, `ArtifactRef`, `SchedulerPolicy`, `InteractionTelemetry`, and `INTERACTION_POLICY_VERSION = "1.0"`.
- [ ] **P1-2**. Add `interaction_type: str = "delegate"` field to `DelegationEvent` (`responses.py:19-30`) additively. Update `ChatResponse.delegation_events` description to mention `interaction_type`. Do NOT rename the field. Do NOT rename the class.
- [ ] **P1-3**. Refactor `_architect_delegated_answer()` (`chat_delegation.py:658-743`) to construct an `Interaction(kind="delegate", ...)` internally. Preserve the `tuple[str, dict]` return signature. Preserve `stats["delegation_events"]` field shape on the wire.
- [ ] **P1-4**. Wire `Interaction.scheduler_policy` to existing `request_priority` / `max_queue_wait_ms` / `migration_budget_ms` admission path (`inference.py:230-259`). No new fields on `ChatRequest`.
- [ ] **P1-5**. Add `ProgressLogger.log_interaction()` (`progress_logger.py:250+`) as a generalization of `log_delegation()`. Preserve `log_delegation()` as an alias that calls `log_interaction(interaction_type="delegate", ...)`. Add `INTERACTION_POLICY_VERSION` alongside existing `DELEGATION_POLICY_VERSION`.
- [ ] **P1-6**. Preserve all existing tests. Add unit tests for `Interaction` lifecycle state transitions and event emission.

**Gate to P2**:
- `pytest tests/test_chat_delegation.py` green
- `delegation_diagnostics` byte-equal on identical inputs across before / after
- No change to `delegation_events` field on the wire
- `epyc-orchestrator/scripts/server/affinity_preflight.py` shows no region-lock drift
- One autopilot cycle (≥48h) with no rise in `delegation_cache_hits` miss rate or `ContentionDenied` 503 rate

### P2 — One-shot consult sibling

**Goal**: Add `kind="consult"` as a narrow specialization on the same substrate, with typed output schema and scheduler defaults. **First and only consult site in v1: the code-edit drafting requester → `architect_general` for `review_before_commit`** (requester role identified in P2-0).

- [x] **P2-0**. **Discovery — identify the exact attach point** in the code-edit pipeline for the first consult site. Candidate paths to enumerate: the `force_mode="edit"` flow (`requests.py:force_mode` consumers), `batched-edit-parallel-apply` (sibling handoff), the REPL final-answer hook, `worker_coder` / `coder_escalation` drafting flows. Pick the single attach point where (a) the requester has a complete-enough draft to advise on, (b) integration of advisory feedback before commit is structurally possible (one re-run capacity), (c) the requester role identity is stable. Output: a one-paragraph design note appended to this handoff naming the chosen pipeline file:function. Validate with `gitnexus impact <chosen_function> --direction upstream` before P2-1 begins. **Do NOT assume `worker_general` is the requester** — the consultant skill `review_before_commit` is keyed by *consultant role*, not requester role; the requester is whatever role is at the attach point. Completed 2026-05-31: chosen seam is `epyc-orchestrator/src/edit_transaction.py:199` `run_edit_transaction()`, between draft parse and transactional apply; requester role is `coder_escalation`.

- [ ] **P2-1**. Create `orchestration/interaction_skills.yaml` (sibling to `model_registry.yaml`):

  ```yaml
  interaction_skills:
    architect_general:
      review_before_commit:
        kind: consult
        description: "Advisory review of a coder draft before it commits."
        output_schema:
          type: object
          required: [risks, blocking_issues, confidence, recommended_delta]
          properties:
            risks:             { type: array, items: { type: string } }
            blocking_issues:   { type: array, items: { type: string } }
            confidence:        { type: number, minimum: 0, maximum: 1 }
            recommended_delta: { type: string }
            do_not_do:         { type: array, items: { type: string } }
            needs_input:       { type: string, nullable: true }
        max_output_tokens: 400
        scheduler_defaults:
          priority: background
          max_queue_wait_ms: 2000
          cancellable: true
        tools_budget: 0
        cache_ttl_seconds: 1800
  ```

- [ ] **P2-2**. Add `consult()` entrypoint in `src/orchestration/consultation.py`:

  ```python
  def consult(
      consultant_role: str,
      requester_role: str,
      skill: str,
      context: str,
      primitives: "LLMPrimitives",
      *,
      override_max_tokens: int | None = None,
      override_priority: str | None = None,
  ) -> tuple[dict, dict]:
      """Returns (parsed_advisory, stats). parsed_advisory matches the skill's output_schema."""
  ```

  Loads the skill spec from `interaction_skills.yaml`. Constrains the LLM output via `LLMPrimitives.llm_call(..., json_schema=skill.output_schema)` (`primitives.py:506`) — **NOT** via `ChatRequest.output_schema`, which is a REPL-context FINAL() validator injected into the prompt, not a call-time output constraint. Parses + validates the returned JSON against the schema; on parse / validation failure, raises `ConsultationDenied(reason="schema_violation")`. Enforces `max_output_tokens` and `tools_budget`. Dispatches through the same contention gate (`inference.py:230`) and shared-backend `topology_role` mapping (`backend.py:90+`).

- [ ] **P2-3**. Extend `DelegationCache.make_key()` (`src/orchestration/delegation_cache.py:69-78` — the actual module; `src/delegation_cache.py` is only a back-compat shim) to namespace by interaction type and skill:

  ```python
  @staticmethod
  def make_key(
      brief: str,
      delegate_to: str,
      *,
      interaction_type: str = "delegate",
      skill: str = "",
      schema_hash: str = "",
      policy_version: str = "1.0",
  ) -> str:
      normalized = brief.strip().lower()[:200]
      payload = f"{interaction_type}|{skill}|{normalized}|{delegate_to}|{schema_hash}|{policy_version}"
      return hashlib.sha256(payload.encode()).hexdigest()
  ```

  Existing call sites (`chat_delegation.py:939`) pass only `(brief, delegate_to)` — keyword defaults preserve them. Cache TTL per-skill via `cache_ttl_seconds` field; falls back to `DEFAULT_TTL_SECONDS = 3600`.

- [ ] **P2-4**. Reuse `_maybe_dcp_seed_context()` (`chat_delegation.py:247-289`) for consult context packaging. Do NOT invent a new packer. Gate with `features().dcp_for_consult` (default off; on requires `features().dcp_pre_assembly`).

- [ ] **P2-5**. Add `log_consult()` shim on `ProgressLogger`. Calls `log_interaction(interaction_type="consult", skill=..., ...)`.

- [ ] **P2-6**. Add `ConsultationDenied` exception (parallel to `ContentionDenied`). **P2 is an INTERNAL consult sibling — no new HTTP endpoint and no 503 mapping in this phase.** Internal callers catch `ConsultationDenied` and record a `consult_denied` event in `interaction_events`. The current contention gate (`inference.py:230`) queues per `TrafficClass` + `max_queue_wait_ms` and raises `ContentionDenied` on rejection; for the cancellable consult policy, `consult()` MUST achieve skip-or-admit semantics by passing `max_queue_wait_ms=0` (or per-skill override) — this leverages existing gate behavior, do NOT add separate queue-skip logic into the gate itself. Translate the resulting `ContentionDenied` into `ConsultationDenied(reason="contention_skip")` at the `consult()` boundary so callers see one exception type. A future external consult HTTP endpoint (deferred, D3-adjacent) would map `ConsultationDenied` to 503; that mapping is out of scope here.
  - **Verified 2026-05-31** (`contention_gate.py:346-399`): `max_queue_wait_ms=0` achieves the intended skip-or-admit semantics natively. The default-fallback at `:366` (`if max_queue_wait_ms is None`) does NOT catch `0`, so per-skill `0` is preserved. `deadline = time.monotonic() + 0/1000 = now` at `:372`, the loop at `:375` runs one `evaluate()` call, admits-immediately if no blocker, otherwise returns `reason="timeout"` after that single evaluate with `waited_s ≈ 0`. No separate skip-logic needed. Add a regression test pinning this behavior so a future gate refactor cannot silently re-introduce the default-fallback for `0`.

- [ ] **P2-7**. Wire the first consult site **at the attach point identified in P2-0**. Skill: `review_before_commit`. Consultant: `architect_general`. Requester: the role producing the code-edit draft at the chosen attach point (named in the P2-0 design note — may be `worker_coder`, `coder_escalation`, or another; do NOT assume `worker_general`). Call shape:
  ```python
  consult(
      consultant_role="architect_general",
      requester_role=<from P2-0>,
      skill="review_before_commit",
      context=draft_summary,
      primitives=primitives,
  )
  ```
  Integrate the parsed advisory:
  - If `blocking_issues` non-empty AND `confidence >= 0.6`: re-run the requester with the advisory injected; cap at 1 re-run.
  - Otherwise: emit the advisory as a `review_advisory` event in the response telemetry and proceed.
  - On `ConsultationDenied`: emit a `consult_denied` event and proceed without the advisory.

**Gate to P3**: A/B test on a fixed eval slice (≥50 code-edit turns):
- Tokens saved vs full-delegation baseline ≥ 30% on the advisory leg
- Answer quality non-regression: ≤ 1pp drop on the code-edit eval slice
- Contention tax not visible: `worker_general` decode p50 within ±5% pre vs post
- Advice cache hit rate ≥ 10% on repeated identical-shape edits within a 1h window
- All six invariants (I1–I6) hold under P2 traffic

### P3 — Consult gating policy, shadow first

**Goal**: Stop calling consult on every code edit. Gate by signals owned by `routing-intelligence`.

- [ ] **P3-1**. Gate signal taxonomy:
  - `factual_risk_score` (from `routing-intelligence`)
  - `difficulty_band` (`progress_logger.log_delegation` already carries this; reuse via `log_interaction`)
  - `diff_size` (lines changed in the proposed edit)
  - `touched_symbol_blast_radius` (via `gitnexus impact <symbol> --direction upstream`)
  - `recent_failure_history` (last N turns of this requester role)
  - `benchmark_class` (in-eval or live)
  - `latency_budget_remaining`

- [ ] **P3-2**. Implement `should_consult(interaction_intent, signals) -> bool` policy. Per-skill thresholds in `interaction_skills.yaml`.

- [ ] **P3-3**. **Shadow mode**: log the gate decision but always run the consult (baseline). Compare offline: would gating have saved tokens? Did skipped consults lose quality?

- [ ] **P3-4**. After ≥1 week of shadow data: enable enforcement for one signal at a time. Require an explicit gate-rollback handoff if quality regresses (≥1pp on the code-edit eval slice).

**Gate to P4**: Shadow logs show consult provides nonzero advice value on > 30% of triggered turns; enforcement plan shows expected net token saving with bounded quality risk.

### P4 — Integration-quality evaluation

**Goal**: Beyond token / latency, measure whether consultation actually helps.

- [ ] **P4-1**. Integration-quality metrics:
  - `advice_adopted_correctly` — did the requester act on the advice?
  - `issue_catch_rate` — did consult catch real bugs that delegation alone missed?
  - `false_block_rate` — consult flagged a non-issue, blocked the requester unnecessarily
  - `downstream_answer_quality_delta` — vs no-consult baseline on the same prompt
  - `contention_impact_tax` — cross-role latency cost of running consults

- [ ] **P4-2**. Wire metrics into MemRL reward signal as a separate `consult_reward` head. Do NOT blend with delegation reward until calibrated.

- [ ] **P4-3**. Quarterly review: keep / tune / disable each consult skill based on metrics.

**Exit**: At least one skill (`worker_general → architect_general review_before_commit`) shows positive `consult_reward` over 4 weeks. Metrics dashboard exists. Quarterly review cadence established.

### Deferred Work — require their own gate before re-opening

- **D1. Streaming consult**. Needs backend streaming callback exposure (current `/chat/stream` wraps pipeline events, not backend tokens). Reopen when `stream_adapter` exposes tokens directly OR when a consult skill needs intermediate artifacts to integrate concurrently.
- **D2. Multi-turn `input_required` consult**. Needs local `ConsultationTask` store with terminal / interrupted states. Reopen when one-shot consult fails on a real use case (e.g., consultant needs clarification before advising).
- **D3. External A2A adapter**. Inbound at `hermes-outer-shell` (advertise Agent Cards for external callers); outbound for cross-vendor consult (consume external A2A peers). Reopen when (a) Path A external exposure becomes load-bearing on `hermes-outer-shell`, OR (b) a frontier cloud model exposes A2A endpoints.

## Dependency Graph

```
P1 (lifecycle refactor, no behavior change)
  │
  ▼
P2 (one-shot consult sibling) ◄── delegation-context-preassembly (DCP-6: ranking/rendering for context packaging)
  │
  ▼
P3 (gating policy, shadow first) ◄── routing-intelligence (factual-risk / difficulty / shadow-routing signal quality)
  │
  ▼
P4 (integration-quality eval) ──► MemRL/reward telemetry (separate consult_reward head)

External deferred:
  D3 (external A2A) ◄── hermes-outer-shell Path A go/no-go
```

## Migration Plan (additive, two revs)

**Rev N (this handoff's P1 + P2)**:
- Add `InteractionEvent` class with `interaction_type: str` field default `"delegate"`.
- Add `interaction_type: str = "delegate"` field directly to `DelegationEvent` (additive).
- Keep `DelegationEvent` class name. Do NOT rename to `InteractionEvent` yet.
- Keep `ChatResponse.delegation_events` field name. Do NOT rename to `interaction_events` yet.
- Keep `ProgressLogger.log_delegation()` as an alias calling `log_interaction(interaction_type="delegate", ...)`.
- Keep `DELEGATION_POLICY_VERSION = "1.0"` alongside new `INTERACTION_POLICY_VERSION = "1.0"`.
- Update field descriptions to mention `interaction_type`.

**Rev N+1 (next major orchestrator release, after telemetry consumers audited)**:
- Optionally rename `DelegationEvent` → `InteractionEvent` (alias old name for one rev).
- Optionally rename `delegation_events` → `interaction_events` on `ChatResponse` (alias old name for one rev).
- Audit MemRL / wandb / external log consumers. Coordinate breaking-change announcement if needed.

## Open Decisions (none block P1; surface for P2)

1. **`tools_budget` semantics**. Proposal: `tools_budget=0` = no tools at all; `tools_budget=N` = at most N tool calls; `tools_budget=null` = inherit from caller. Confirm.
2. **`TrafficClass` for consult**. Proposal: reuse existing `TrafficClass.BACKGROUND` (per skill default). Reopen if BACKGROUND's queueing semantics (90s default queue wait) doesn't fit consult cancellability. Alternative: add `TrafficClass.FOREGROUND_ADVISORY`. Confirm.
3. **Consult cache TTL**. Existing `DEFAULT_TTL_SECONDS = 3600`. Proposal: 1800s default for consult (advice goes stale faster); per-skill override in `interaction_skills.yaml`. Confirm.
4. **`features()` flag naming**. Proposal: `features().consult_skills_enabled` as a per-skill dict (so `review_before_commit` can enable without enabling all future consults). Alternative: global `features().consult_enabled`. Confirm.

## Key file locations

Primary touch points:

- `epyc-orchestrator/src/api/routes/chat_delegation.py:658-743` (P1 refactor)
- `epyc-orchestrator/src/api/routes/chat_delegation.py:247-289` (P2 DCP reuse)
- `epyc-orchestrator/src/api/routes/chat_delegation.py:936-955` (P2 cache namespace)
- `epyc-orchestrator/src/orchestration/delegation_cache.py:27-78` (P2 `make_key` extension; `src/delegation_cache.py` is a back-compat shim only)
- `epyc-orchestrator/src/llm_primitives/primitives.py:506` (P2 `llm_call(..., json_schema=...)` constraint path)
- `epyc-orchestrator/scripts/server/affinity_preflight.py` (per-phase I1 region-lock verification)
- `epyc-orchestrator/src/api/models/responses.py:19-30` (P1 `DelegationEvent` additive `interaction_type`)
- `epyc-orchestrator/src/api/models/requests.py:102-131` (P1/P2 admission + `output_schema`)
- `epyc-orchestrator/orchestration/repl_memory/progress_logger.py:250-288` (P1 `log_interaction` generalization)
- `epyc-orchestrator/src/llm_primitives/inference.py:230-259` (preserve contention gate)
- `epyc-orchestrator/src/llm_primitives/backend.py:90-140` (preserve topology_role aliasing)
- `epyc-orchestrator/orchestration/model_registry.yaml` (sibling for new `interaction_skills.yaml`)

NEW files (created during phase execution):
- `epyc-orchestrator/src/orchestration/interaction.py` (P1)
- `epyc-orchestrator/src/orchestration/consultation.py` (P2)
- `epyc-orchestrator/orchestration/interaction_skills.yaml` (P2)

## P2-0 Design Note — chosen attach point (2026-05-31)

Discovery completed 2026-05-31. GitNexus is indexed only for `epyc-root` (not `epyc-orchestrator`), so upstream-caller analysis used grep + direct code read instead of `gitnexus impact`.

### Candidate scorecard

| Candidate | (a) Complete draft pre-commit | (b) Re-run capacity | (c) Stable requester | Verdict |
|-----------|-------------------------------|---------------------|----------------------|---------|
| `force_mode="edit"` → `run_edit_transaction()` at `src/edit_transaction.py:199` | ✅ `new_files: dict[str, str]` parsed at `:210` before apply at `:211` | ✅ in-memory draft; `apply_edit_transaction()` is a separate function — natural seam | ✅ routes to `coder_escalation` (Qwen3.6-35B-A3B Q8 @ :8071, shared mmap with frontdoor) per `model_registry.yaml:381,908` + CHANGELOG | **CHOSEN** |
| REPL `_final()` at `src/repl_environment/context.py:169` | ◐ answer complete, but the wiki notes this path was bypassed for code-edit work (multi-turn read→peek→edit→FINAL loop failed BEP) | ✘ `FINAL()` terminates REPL execution; injecting a consult that may re-run is structurally invasive | ◐ role identity varies by REPL caller (worker_general / worker_explore / etc.) | rejected |
| `worker_coder` default flow | — | — | ✘ `worker_coder` (port 8102, 30B alias) failed the BEP code-edit tasks; production code-edit producer is now `coder_escalation` per the 2026-05-27 protocol-fix work | rejected |
| `coder_escalation` default flow | overlaps with Candidate A when `force_mode="edit"` is set | — | ✅ same role as Candidate A | folded into Candidate A |
| Batched-edit pipeline (`batched-edit-parallel-apply`) | — | — | ✘ "implementation-scoped draft" status; BEP-2 was the falsification gate and is now optional provenance per its handoff banner — not a shipping production path | rejected |

### Chosen attach point

**`epyc-orchestrator/src/edit_transaction.py:199` `run_edit_transaction()`, between the one-shot draft `llm_call()` at `:209` and the transactional `apply_edit_transaction()` at `:211`.**

### Why this is the right seam

1. **Production-shipping path.** `force_mode="edit"` is the canonical multi-file code-edit surface (default-off via `ORCHESTRATOR_EDIT_TRANSACTION=1` + scoped `ORCHESTRATOR_EDIT_ROOT`, fail-closed with HTTP 412 if either is missing). The wiki names it as the remediation for the BEP read→peek→edit→FINAL failure class. Not a vapor target.
2. **Complete structured draft pre-commit.** After `parse_edit_response(raw)` at `:210`, the draft is a fully-typed `(new_files: dict[str, str], deletes: list[str])`. Advisory feedback can be summarized against this structured artifact rather than against free-form prose.
3. **Apply is a separate function.** `apply_edit_transaction()` (`:138`) handles snapshot / write / syntax-check / rollback as a discrete step. Inserting a consult between draft parse and apply is a single-statement change with no transaction-semantics risk — the rollback path is untouched.
4. **Stable requester role.** `force_mode="edit"` per `chat.py:589` calls `run_edit_transaction(..., _edit_llm_call, ...)`; the `_edit_llm_call` closure at `chat.py:573-586` calls `_execute_direct()` against `initial_role`, which for `force_mode="edit"` resolves to `coder_escalation` per the production routing. Stable identity for `interaction_skills.yaml` registry + telemetry.
5. **LOW blast radius.** Only TWO upstream callers of `run_edit_transaction` exist in the entire codebase:
   - `epyc-orchestrator/src/api/routes/chat.py:589` (sole production caller)
   - `epyc-orchestrator/tests/unit/test_edit_transaction.py:104` (`test_run_edit_transaction_with_stub_llm`)

   Adding `primitives` as a keyword-only optional with `None` default preserves the test's existing call shape.

### Wiring sketch (executed in P2-7)

```python
def run_edit_transaction(
    llm_call: Callable[[str], str],
    task_prompt: str,
    root: Path | str,
    target_files: list[str] | None = None,
    self_check: bool = True,
    *,
    primitives: "LLMPrimitives | None" = None,   # NEW (P2-7)
) -> tuple[EditResult, str]:
    try:
        files_ctx = assemble_context(root, target_files)
    except EditScopeError as e:
        return EditResult(ok=False, error=str(e)), ""
    raw = llm_call(build_edit_prompt(task_prompt, files_ctx)) or ""
    new_files, deletes = parse_edit_response(raw)

    # NEW (P2-7): optional advisory consult between draft and apply
    if primitives is not None and features().consult_skills_enabled.get("review_before_commit"):
        try:
            advisory, _stats = consult(
                consultant_role="architect_general",
                requester_role="coder_escalation",
                skill="review_before_commit",
                context=_summarize_draft(new_files, deletes, task_prompt),
                primitives=primitives,
            )
            if advisory.get("blocking_issues") and advisory.get("confidence", 0.0) >= 0.6:
                raw = llm_call(build_edit_prompt(task_prompt, files_ctx, advisory=advisory)) or ""
                new_files, deletes = parse_edit_response(raw)  # one re-run cap
        except ConsultationDenied:
            pass  # event recorded upstream as consult_denied in interaction_events

    return apply_edit_transaction(root, new_files, deletes, self_check=self_check), raw
```

### Wiring impact upstream

- `chat.py:589` becomes `run_edit_transaction(_edit_llm_call, request.prompt, get_task_root(), None, primitives=primitives)` — `primitives` is already in scope (passed to `_execute_direct` etc.).
- `build_edit_prompt()` gains an optional `advisory` parameter for the re-run path; default `None` preserves all existing call sites.
- `_summarize_draft()` is a new helper (small, P2-7 scope) producing the bounded context the consultant sees — NOT the full file bodies (that's the consultant's job to reason about, gated by `tools_budget`).

### Sanity gates before P2-1

- ✅ Single production caller verified (`chat.py:589`).
- ✅ Apply step is a separable function (`apply_edit_transaction` is called once at `:211`).
- ✅ Requester role identity stable (`coder_escalation` per `force_mode="edit"` branch).
- ✅ Test fixture impact LOW (keyword-only optional preserves `test_run_edit_transaction_with_stub_llm`).
- Pending P1: `Interaction(kind="consult", ...)` substrate must land before P2-7 wiring (per phase ordering — P2-7 depends on P1's interaction abstraction).

**Discovery status**: COMPLETE. P2-1 may proceed when P1 lifecycle refactor is gate-passed.

### Inference-window scheduling (bulk-inference-campaign cross-ref)

The P2 A/B (≥50 code-edit-turn comparison at the edit-transaction seam) is registered as **J17** in [`bulk-inference-campaign.md`](bulk-inference-campaign.md) under the "Other agents' inference-gated work" table. That handoff carries the inference-window scheduling logic, model requirements (`coder_escalation` + `architect_general`), and prereq-chain visibility for the operator triggering the eval. The bulk-inference handoff's "Internal Interaction Lifecycle (consult sibling) — TRACKING" tail section mirrors the live status (P2-0 ✅ / P1 ⏳ / P2 ⏳ / J17 🔒 / P3+P4 🔒) so the inference-window agent can see exactly when to schedule J17 without reading this full handoff. Update both sides when phase state changes.

## Reporting

- Tick checkboxes inline in this handoff after each phase task.
- Update `Status` line at top of handoff after each phase gate.
- Append A/B results and gate-pass evidence to `progress/YYYY-MM/YYYY-MM-DD.md`.
- Cross-link decisive findings to `routing-and-optimization-index.md` Outstanding Tasks section.
- On completion of all four phases, move this handoff to `handoffs/completed/` and write a wrap-up.
