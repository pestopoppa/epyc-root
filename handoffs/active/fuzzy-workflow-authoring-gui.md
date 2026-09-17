# Fuzzy Workflow Authoring GUI — deterministic flow, fuzzy steps, one canvas

**Status**: stub (design idea from operator steering, 2026-09-17)
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Categories**: agent_architecture, tool_implementation, harness_optimization
**Parent index**: [user-facing-harness-index.md](user-facing-harness-index.md)
**Evidence**: intake-1460#record (operator digest: typed decisions; stage1-unverified), intake-1477#05 (compiled functions make fuzzy decisions while ordinary code handles exact operations — BM25, caching, branch control), intake-1481#record / intake-1482#record (compile-once specialists as candidate fuzzy nodes; gfx90a unproven — intake-1481#04), intake-1482#04 (confidence thresholding fails: the misses score 0.97–1.00), intake-1474#record (calibration warning: most wrong 7B fields are >0.90 confident)
**Related**: [`paw-compiled-specialists.md`](paw-compiled-specialists.md) PAW-5 (enumerates the ≤3 recurring fuzzy subtasks — **FW-1 consumes that enumeration, it does not repeat it**), [`typed-decision-plane.md`](typed-decision-plane.md) TD-2 (calibration gate) and TD-4 (closed-set tool-argument pilot), [`tool-use-eval-contract.md`](tool-use-eval-contract.md) TU-TD-1 (closed-set tool-argument arm — FW-1's tool-output-routing example links here rather than duplicating it), [`harness-selection-and-integration.md`](harness-selection-and-integration.md) (HS-4: one router, no patches)

## Objective

Design a process-authoring GUI where the user draws a flow whose deterministic steps are ordinary code and
whose fuzzy steps are typed decision calls or compiled specialists. Operator steering: "a GUI for designing
high level processes that clearly separate deterministic flow from fuzzy LLM work in a meaningful way."
The GUI is an authoring surface, not a runtime. **Candidate runtimes**: the orchestrator's own graph
(`epyc-orchestrator/src/graph`, `decision_gates.py`) together with the durable-execution component adopted
from intake-847#record (LangGraph `adopt_component`) — available today; the typed-decision plane (RTG-56) once
TD-2 calibration lands; PAW compiled programs (INF-76) once PAW-2 proves gfx90a. Neither RTG-56 nor INF-76 is
assumed to be the runtime.

## Tasks

- [ ] **FW-1 — Requirement sketch + one worked example.** Take one recurring fuzzy subtask from PAW-5's
  enumeration (candidate: eval-triage or tool-output routing; the latter links to TD-4 / TU-TD-1), express it
  as a two-layer graph (deterministic nodes: code; fuzzy nodes: typed questions / compiled programs), and
  record what the GUI must expose. **The sketch opens with a pseudocode loop block** per
  [`docs/guides/agent-workflows/agent-loop-design.md`](../../docs/guides/agent-workflows/agent-loop-design.md):
  every actor and what it reads; every gate and its rejection grounds; where every rejection GOES — a
  dangling rejection edge is a **lint error** for the GUI, not a warning; the one step that costs real
  resources (every gate sits before it, or says why not); one independent budget per gate, none feeding
  another. The GUI's node/edge vocabulary is derived from that block. **Fuzzy-node contract**: typed output —
  `choice` / `score` / `null` (RTG-56 spells it Noul) — plus a probability; a fuzzy node may **not** branch on model confidence, and the
  lift is **per (model pin, question catalogue) on an operator-ratified calibration record, never global**
  (amended 2026-09-17, FW-1 §4 D-1: TD-2 has landed — 27B ECE 0.0625 with one miss at ~0.90, LFM2.5-2.6B ECE
  0.267 — so "TD-2 landed" was never the unlock; the 27B number says nothing about LFM, one catalogue's ECE
  says nothing about another's, and TD-5 still forbids enforcement without operator approval)
  (intake-1474#record, intake-1482#04); schema-invalid output after the declared retry
  budget routes to a **declared** node (abstain / escalate / deterministic fallback), never off the canvas;
  every model call goes through `LLMPrimitives` (HS-4 "one router" — no side channels from the GUI runtime).
  Acceptance: the example runs end-to-end in a notebook or CLI harness with the GUI mocked, and the loop
  block is in the sketch with all four requirements and the budgets named.
  **Delivered 2026-09-17 (sketch half, zero inference): § *FW-1 sketch* below** — worked example = worker-failure
  routing (PAW-5 "tool-output classification"), loop block, derived GUI vocabulary + 11 lint rules, three forced
  decisions and two follow-ups. **Not yet done**: the mocked-GUI harness run (blocked on FW-4's write-side hook by
  the FW-4 acceptance text, and on the operator's zero-inference constraint this session); FW-3 not yet citable.
- [ ] **FW-2 — Record placement (no operator choice remains).** HS-4 §2 admits shell plugins only for
  configuration, so a harness plugin is excluded; the dashboard plane rule (`dashboard/README.md`, RTG-47,
  ratified 2026-08-10) puts every **page** on the hub `:8100` with a `dashboard/registry.json` entry, a
  `health_path` probe (`/health` is transport-only; `/api/health` is the freshness fold) and a freshness
  envelope, while the **data contract** lives with the subsystem it observes. So: workflow document schema,
  executor and the `/dashboard/api/workflows/*` contract in `epyc-orchestrator`; authoring page, registry
  row, probe and freshness envelope on the hub; nothing in the shell. GUI-authored workflows that run on
  `/v1` wait for the P0.4 freeze (HS-5b). Acceptance: a contract stub (schema + endpoint list) in
  `epyc-orchestrator` and a registry-row draft handed to the owning hub session — the drafting is this
  handoff's; the row write is the owner's.
- [ ] **FW-3 — Survey prior art (≤1 day).** Flow-authoring UIs with LLM nodes (e.g. Dify/LangFlow-class) and
  compiled-function authoring (PAW playground) — what to borrow, what to refuse. No ingestion; a short note.
  Acceptance: the note lands in `docs/reference/harness-candidates/` (one file, named for this handoff) and
  FW-1 cites it.
- [x] **FW-4 — Belief-kernel wiring, write side, prospective (CLAUDE.md → Belief Kernel).** Before the first
  FW-1 end-to-end run: a source-table row in `scripts/vidya/adapters/README.md` (class `measurement`;
  prospective; drafted here, written by that file's owner) plus an SC task in
  [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). Each run emits one `ClaimTuple`
  carrying the workflow document hash, the node types, the fuzzy-node model/pin (or compiled-program id), and
  every gate's outcome; `claim_tuple.grade()` decides the grade — no new ladder. Acceptance: row text +
  SC task drafted and the FW-1 harness refuses to run without the hook.
  ✅ 2026-09-17 — both halves filed: the source-table row is in `scripts/vidya/adapters/README.md`
  (class `measurement`, prospective, adapter lands with the FW-2 executor) and the task is **VB-FW-1** in
  [`vidya-belief-substrate-program.md`](vidya-belief-substrate-program.md). The tuple carries the
  workflow-document hash, the executed node types, each fuzzy node's model pin **and** question catalogue
  (both, because L2's lift is per `(model pin, catalogue)` — a record keyed on one is unusable), and each
  gate's outcome with its rejection destination. Confidence is recorded as evidence, never read by an edge.
  The adapter projects; `claim_tuple.grade()` decides. Residual: the FW-1 harness refuse-without-hook check
  lands with the FW-2 executor, since no harness exists yet to refuse.

## FW-1 sketch — worker-failure routing as a two-layer workflow (2026-09-17)

### 1. The worked example, and why this one

PAW-5's enumeration names four recurring fuzzy subtasks: tool-output classification, transcript/log filtering,
JSON repair, routing predicates. The example is the first: **classifying a failed worker turn's error output and
routing it** (retry / think-harder / escalate / fail). It is not a toy — the orchestrator graph does it today at
six duplicated call sites (`epyc-orchestrator/src/graph/nodes.py:232, 283, 347, 464, 568, 671, 776`) with a
keyword matcher, `classify_error()` in `src/graph/error_classifier.py`, that falls through to
`ErrorCategory.UNKNOWN` whenever none of its ~30 substrings match. The gates downstream of it —
`_should_think_harder`, `_should_retry`, `_should_escalate`, `_check_approval_gate` in
`src/graph/decision_gates.py` — are already code and stay code. The **only** fuzzy step is the classification of
the `UNKNOWN` residue, and it maps onto the typed-decision plane with no invention: one `choice` over the closed
set of `ErrorCategory` members and one `noul`. The typed runner (`src/typed_decisions/runner.py`) calls
`primitives.llm_call` (line 181), so the fuzzy node goes through `LLMPrimitives` by construction — HS-4 "one
router" is a fact of the runtime, not a rule the GUI has to police.

The link to TD-4 / TU-TD-1 is the same mechanism pointed the other way (tool *arguments* from closed sets rather than
tool *output* into a closed set); this sketch does not duplicate that arm.

### 2. The loop block

Convention: [`agent-loop-design.md`](../../docs/guides/agent-workflows/agent-loop-design.md). `[code]` =
deterministic node, `[fuzzy]` = typed decision through `LLMPrimitives`. `←$` marks the one step that costs real
resources. Budgets are named `B_*` and none feeds another.

```
each worker turn (graph node: FrontdoorNode / CoderNode / … — one subflow, referenced six times):
    WORKER  worker_call(role, prompt, state)                              [fuzzy, ←$ THE expensive step]
        reads   task prompt · state.last_error · state.last_output · role config
        emits   (output, error, tool_outputs)
    error is None → RESOLVE                                               [code]
        RESOLVE _resolve_answer(output, tool_outputs) → End(success, answer)

FAILURE ROUTING · every gate below sits BEFORE the next worker_call
    C0  keyword classifier                                                [code]   classify_error(error)
        reads   error string only
        emits   category ∈ {TIMEOUT SCHEMA FORMAT EARLY_ABORT INFRASTRUCTURE CODE LOGIC UNKNOWN}
        category == EARLY_ABORT → G4 directly   (as coded today; see follow-up F-1: this edge skips B_esc)
        category ≠ UNKNOWN      → G1            (no model call; the fuzzy node is residue-only)
        category == UNKNOWN     → F1

    F1  typed classifier · budget B_parse = 1 corrective retry              [fuzzy]  run_typed_decisions(primitives, …)
        reads   error (head, bounded) · tail of last_output · tool_outputs envelope · current_role
        asks    q_cat  : choice over the 7 NAMED categories — UNKNOWN is deliberately not an option
                q_done : noul  "output already contains a complete answer to the task"
        emits   per question: value · probabilities · confidence (kind "choice"/"noul")
                confidence and probabilities are WRITTEN to the run record (FW-4 ClaimTuple) and to the
                shadow log; NO edge below reads them (TD-2 / TD-5: no enforcement without operator approval)
        rejects on (checked in code by the runner, not by a model):
                no_json · schema_violation · invalid_value (label outside the set) · transport_error
          no_json / schema_violation / invalid_value → ONE corrective retry, failure text appended   (charges B_parse)
          transport_error                            → no retry; → F1.fallback now
          B_parse SPENT                              → F1.fallback
        F1.fallback  := category = UNKNOWN, continue at G1 exactly as the code does today.
                       A declared node on the canvas. Nothing leaves the canvas.
        cost of a rejection: one small-role call. No worker call, no retry counter touched.
        INDEPENDENCE: an F1 failure charges B_parse ONLY. It must NOT increment state.consecutive_failures —
                       that counter belongs to WORKER. (agent-loop-design.md "Budgets": different cause, different counter.)
        q_done.value == true → V1
        else                 → G1 with category = q_cat.value

    V1  answer validation                                                 [code]   _resolve_answer + task output schema
        rejects on: empty answer · fails the task's declared output schema
        REJECT → G1 carrying the ORIGINAL category (the noul was wrong; this is not a new worker failure,
                 so consecutive_failures is not incremented again)
        accept → End(success, answer, flagged "recovered_by_q_done")

    G1  think-harder gate · budget B_think = 1 per role                     [code]   _should_think_harder
        reads   category · state.think_harder_attempted · current_role
        rejects on: already attempted for this role · category not in the think-harder set
        pass   → WORKER (same role, CoT prompt, 2x tokens)                 ←$
        REJECT → G2

    G2  retry gate · budget B_retry = cfg.max_retries                       [code]   _should_retry
        reads   category · state.consecutive_failures
        rejects on: category == TIMEOUT (fail fast) · consecutive_failures ≥ max_retries
        pass   → WORKER (same role; the prompt carries state.last_error VERBATIM)   ←$
        REJECT → G3

    G3  escalation gate · budget B_esc = cfg.max_escalations                [code]   _should_escalate
        reads   category · last_error · escalation_count · role_history · next_tier
        rejects on: category ∈ no_escalate_categories · no next tier · escalation_count ≥ max_escalations ·
                    role cycle A→B→A→B in role_history · SCHEMA with a parser signature (not a capability gap)
        pass   → G4
        REJECT → End(failure) — record carries category, last_error, and every gate's verdict (G1..G3)

    G4  approval gate (feature-flagged) · no budget: a yes/no                [code]   _check_approval_gate
        reads   from_role · to_role · reason
        rejects on: approver declines
        pass   → WORKER (next tier; escalation_count += 1; consecutive_failures := 0)   ←$
        REJECT → End(failure, "escalation refused") — same record shape as G3's reject
```

**The four requirements, checked.** (1) Every actor lists its reads (WORKER, C0, F1, V1, G1–G4). (2) Every gate
names its rejection grounds; F1's grounds are the runner's four typed `ParseFailure.reason` values, checked in code.
(3) Every rejection has a destination on the canvas: C0→F1/G1/G4, F1→retry/F1.fallback→G1, V1→G1, G1→G2, G2→G3,
G3→End, G4→End. (4) The single expensive step is `WORKER`; every gate sits before it. The one exception is the
`EARLY_ABORT` edge, which reaches the escalated worker without passing G3/G4 — that is *why* it is written down (F-1).

**Budgets, four, independent.** `B_parse` (F1's own, size 1, from `run_typed_decisions(max_retries=1)`), `B_think`
(1 per role), `B_retry` (`cfg.max_retries`, counter `consecutive_failures`), `B_esc` (`cfg.max_escalations`, counter
`escalation_count`). The only coupling in today's code is deliberate: a pass through G4 resets `consecutive_failures`
because a new role starts fresh. F1 touching `consecutive_failures` would be the AutoKernel `critic_revise` defect
again and is lint rule L5 below.

### 3. What the GUI must expose — derived from the block

**Node vocabulary** (each is something the block needed):

| Node type | Block instance | Shows at a glance | Editable |
|---|---|---|---|
| `code` | C0, V1, RESOLVE | name · function ref · **reads** list · output type | reads list, output type, target of each outgoing edge. The function body is a reference, never edited on the canvas |
| `fuzzy` | F1 | question list (id · kind · option/level count) · model role or pin, or compiled-program id · `B_parse` size · fallback target · badge "probabilities → record only" | question text/options/levels/criteria · role/pin or program id · `B_parse` · fallback target · optional `shadow` flag (§4 D-2) |
| `gate` | G1–G4 | predicate ref · **rejection grounds** (count, expandable) · budget name + size, or "no budget" with a reason | grounds as named predicate refs (not free prose) · budget name · budget size · pass/reject targets |
| `expensive` | WORKER | role · cost class · a visible `$` marker · count of gates on every inbound path | role, cost class. The marker is not removable |
| `terminal` | End(success), End(failure) | outcome · record fields | record fields |
| `subflow` | FAILURE ROUTING, referenced six times | name · reference count | contents once; references are pointers |

**Edge vocabulary**: `flow` (default) · `pass` / `reject` (gate outcomes; a `reject` edge carries the ground(s) it
fires on and the reason payload it delivers) · `value` (from a fuzzy node, one per option label / level / boolean) ·
`fallback` (from a fuzzy node on budget spent or transport error) · `loopback` (any edge whose target is upstream —
drawn distinctly, because that is the arrow AutoKernel was missing).

**Lint rules the canvas enforces** — errors block save; warnings require a typed reason stored on the node.

| # | Rule | Derived from |
|---|---|---|
| L1 | **Dangling rejection**: a `reject`, `fallback` or `value` edge with no target is an **error**. | agent-loop-design.md requirement 3; FW-1 box text |
| L2 | **No branching on confidence**: an edge condition or gate predicate that reads `confidence`, `probabilities` or `token_logprob` is an **error**. Lift condition per §4 D-1, not global. | TD-2 / TD-5; intake-1474#record, intake-1482#04 |
| L3 | A `fuzzy` node with no `fallback` target is an error; a `fallback` target off-canvas is an error. | F1.fallback |
| L4 | `value` edges of a `fuzzy` node must be total over its option set (or declare a default); an option named `UNKNOWN`/`other` is an error — the fallback edge is the unknown. (`shadow`-flagged nodes are exempt: they have no `value` edges.) | F1's 7-label choice |
| L5 | **Budget independence**: two gates sharing a budget name is an error; a `fuzzy` node whose fallback or retry mutates a `gate`'s counter is an error; an unnamed budget is an error. | "Budgets"; the `critic_revise` defect |
| L6 | An `expensive` node reachable from a start or from another `expensive` node via a path with zero `gate` nodes is a **warning** requiring a stated reason. | requirement 4; the `EARLY_ABORT` edge would trip it |
| L7 | A `gate` with an empty rejection-grounds list is an error. | "the critic reviews it" is not a gate |
| L8 | A `code` or `fuzzy` node with an empty reads list is an error. | requirement 1; AutoKernel's empty context bundle |
| L9 | A `loopback` edge whose reason payload is not in the target's reads is an error — the actor must be able to see why it was rejected. | requirement 3; G2 → WORKER carries `last_error` |
| L10 | No node type exists that names a model endpoint. A `fuzzy` node has a role/pin or program id, never a URL; an import that contains one is refused. | HS-4 one router |
| L11 | A `terminal` failure node whose record omits the last category and each gate's verdict is a warning. | G3/G4 reject records |

### 4. Decisions the example forced, and follow-ups

- **D-1 (decided; AMENDMENT APPLIED to the FW-1 box 2026-09-17)**: the box says a fuzzy node may not branch on confidence
  "until RTG-56 TD-2 lands". TD-2 has landed (2026-09-17: 27B ECE 0.0625 with one miss at ~0.90; LFM2.5-2.6B ECE
  0.267), and TD-5 still says no enforcement without operator approval. So "TD-2 landed" is not the unlock. Proposed
  wording: **L2 lifts per (model pin, question catalogue) on an operator-ratified calibration record, never globally**
  — the 27B number says nothing about LFM, and a single catalogue's ECE says nothing about another's.
- **D-2 (decided)**: the fuzzy node sits on the `UNKNOWN` residue only; a classifier over *every* failure is a
  separate `shadow`-flagged fuzzy node (emits to the record, no `value` edges), i.e. the TD-5 pattern. This forced
  the `shadow` flag into the vocabulary and the L4 exemption.
- **D-3 (decided)**: the six duplicated call sites become one `subflow` referenced six times — the GUI needs the
  `subflow` node, and the declarative document (Open Question 1) needs a reference type. This is the first concrete
  argument for the declarative answer over code generation: six generated copies would re-create today's drift risk.
- **F-1 (follow-up, orchestrator graph owner)**: `nodes.py:235-241` — `EARLY_ABORT` increments `escalation_count` and
  enters `CoderEscalationNode` without `_should_escalate` (so without the `max_escalations` check, cycle detection or
  the approval gate). The block made it visible; L6 would flag it. Not fixed here (this session was write-only on
  this file); needs a row in the orchestrator's owning index, drafted by the owning session.
- **F-2 (follow-up, this handoff)**: the acceptance harness run. Prerequisites in order: FW-4 hook (the FW-4
  acceptance text says the harness refuses to run without it), then a mocked-GUI CLI run of the block over a frozen
  set of real `UNKNOWN`-class error strings pulled from the graph's failure records, with the direct-model baseline
  PAW-5 asks for. FW-3 is not yet written, so the FW-3 citation the FW-3 acceptance requires is still owed.

## Open Questions

- Does the GUI edit a declarative document (typed JSON/YAML graph) that the orchestrator executes, or generate code?
  (§4 D-3 adds a concrete argument for the declarative answer: one `subflow` referenced six times.)
  (intake-847#record already points at the declarative answer: a graph the orchestrator executes durably, topology kept.)
- How are fuzzy-node contracts versioned when the underlying model or compiled program changes?
