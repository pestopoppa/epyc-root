# Deep Dive: Multi-Agent Architectures -- Paperclip & AgentRxiv

**Intake IDs**: intake-115 (Paperclip), intake-131 (AgentRxiv)
**Date**: 2026-03-15
**Researcher**: Claude Opus 4.6

---

## Executive Summary

Two distinct approaches to multi-agent coordination, both relevant to EPYC's orchestrator and autopilot systems:

- **Paperclip** (github.com/paperclipai/paperclip) models agents as employees in a company org chart with budgets, heartbeat-driven execution, atomic task checkout, and board-level human oversight. TypeScript/PostgreSQL, MIT license, ~23k GitHub stars.
- **AgentRxiv** (arxiv:2503.18102, Schmidgall & Moor, 2025) models agents as research labs sharing findings through a preprint server, achieving 13.7% improvement on MATH-500 through iterative knowledge accumulation.

Neither is a drop-in replacement for EPYC's architecture, but both contain extractable patterns. Paperclip's cost governance and ticket-based coordination are directly applicable. AgentRxiv's shared-knowledge accumulation pattern maps naturally onto our autopilot's experiment journal.

---

## Part 1: Paperclip

### 1.1 Architecture

Paperclip is a control plane for "zero-human companies" -- multi-agent organizations where AI agents hold roles, report to managers, and execute work through a structured task hierarchy.

**Stack**: TypeScript monorepo (pnpm workspace), Hono REST API, React+Vite UI, PostgreSQL (PGlite for dev), Better Auth. Single Node.js process manages all org state.

**Key modules** (from `server/src/`):

| Module | Purpose |
|--------|---------|
| `services/costs.ts` | Cost event recording, budget enforcement, auto-pause |
| `services/heartbeat.ts` | Agent invocation orchestration, session management |
| `services/approvals.ts` | Human approval gates for hiring, strategy changes |
| `services/issues.ts` | Task lifecycle, atomic checkout, status tracking |
| `services/agents.ts` | Agent CRUD, org chart, adapter management |
| `services/goals.ts` | Goal hierarchy (Company -> Team -> Agent -> Task) |
| `services/activity-log.ts` | Immutable audit trail |
| `adapters/` | Process, HTTP, and plugin-based agent runners |

**Data model** (Drizzle ORM on Postgres):

```
companies
  ├── agents (reportsTo: self-referential FK for org chart)
  │     ├── budgetMonthlyCents, spentMonthlyCents
  │     ├── adapterType (process | http | plugin)
  │     └── status (idle | active | paused | terminated)
  ├── goals (company-level objectives)
  ├── projects (time-bound deliverables under goals)
  └── issues (work units)
        ├── assigneeAgentId (single owner, atomic checkout)
        ├── checkoutRunId, executionRunId (heartbeat run linkage)
        ├── requestDepth (delegation hop counter)
        ├── billingCode (cross-org cost attribution)
        └── parentId (sub-issue nesting)
```

### 1.2 Multi-Agent Coordination

Paperclip's coordination model is **task-centric**: there is no separate messaging or chat system. All inter-agent communication flows through issue creation, status updates, and comments on issues.

**Heartbeat protocol**: Agents are not long-running processes. The server invokes agents via "heartbeats" -- either scheduled (cron) or event-triggered (task assignment, mention). Each heartbeat delivers a context payload containing assigned issues, org context, and goal ancestry. The agent runs, performs work, reports results, and exits. Next heartbeat picks up where it left off.

```
invoke(agentConfig, context?) -> void
status(agentConfig) -> AgentStatus
cancel(agentConfig) -> void
```

Key design decisions:
- **Paperclip controls when, agent controls what**: The server decides invocation timing and context shape. The agent decides execution strategy during its run.
- **Session persistence across heartbeats**: Agents using supported adapters (Claude, Codex, Cursor, Gemini) can resume the same conversation/session across heartbeats rather than cold-starting each time.
- **No auto-recovery on crash**: Stale tasks surface through dashboards for human/monitoring-agent triage. This matches our philosophy of "surface problems, don't hide them."
- **Adapter abstraction**: Process adapters spawn local CLI tools, HTTP adapters call webhooks. A plugin system allows custom adapter types. This is analogous to our adapter layer between the orchestrator and llama-server.

**Organizational hierarchy**: The `reportsTo` self-referential FK on agents creates an org tree. Managers follow an escalation protocol: decide locally, delegate down, or escalate up. A `requestDepth` counter on issues tracks delegation hops to prevent infinite delegation chains.

### 1.3 Cost Governance Model

This is the most mature and directly adoptable subsystem.

**Three-tier enforcement**:

1. **Visibility** -- Real-time dashboards showing spend per agent, per issue, per project, per company. Token counts and dollar costs tracked separately.

2. **Soft alerts** -- Configurable threshold warnings (e.g., 80% of budget).

3. **Hard ceiling** -- When `spentMonthlyCents >= budgetMonthlyCents`, the agent is atomically set to `status = "paused"`. No more heartbeats fire. Board notified for override.

**Implementation** (from `services/costs.ts`):

```typescript
// Atomic cost recording + budget check
const event = await db.insert(costEvents).values({ ...data, companyId }).returning();

// Increment agent spend atomically
await db.update(agents).set({
  spentMonthlyCents: sql`${agents.spentMonthlyCents} + ${event.costCents}`,
});

// Auto-pause if over budget
if (updatedAgent.spentMonthlyCents >= updatedAgent.budgetMonthlyCents) {
  await db.update(agents).set({ status: "paused" });
}
```

**Cost events** track granular detail:
- `provider`, `model` -- which LLM was used
- `inputTokens`, `outputTokens` -- raw token counts
- `costCents` -- dollar cost in cents
- `issueId`, `projectId`, `goalId` -- full attribution hierarchy
- `billingCode` -- cross-org cost attribution when Agent A requests work from Agent B

**Budget scope**: Per-agent monthly budgets with company-level aggregate tracking. Budget of 0 means unlimited. Monthly counters presumably reset on a cron cycle (not visible in the schema, likely in `services/cron.ts`).

### 1.4 Ticket System

Issues are the fundamental work unit, with a rich lifecycle:

**Status categories** (6 fixed categories, customizable statuses within each):
- Triage -> Backlog -> Unstarted -> Started -> Completed -> Cancelled

**Atomic checkout**: Single assignee per issue, enforced at the database level. The `checkoutRunId` and `executionRunId` fields link issues to specific heartbeat runs, creating full traceability from "who worked on this" to "what exactly happened."

**Goal ancestry**: Every issue traces upward through project -> goal -> company mission. Agents see not just the task title but the full "why" chain, reducing misalignment.

**Sub-issues**: Parent-child nesting enables work decomposition. If multi-agent collaboration is needed, the pattern is: create sub-issues with different assignees rather than assigning multiple agents to one issue.

**Request depth tracking**: The `requestDepth` integer on issues counts delegation hops. When Agent A creates a task for Agent B, depth increments. This is a simple but effective anti-pattern for detecting runaway delegation (analogous to our escalation chain depth).

### 1.5 Comparison to EPYC Escalation/Delegation

| Dimension | Paperclip | EPYC Orchestrator |
|-----------|-----------|-------------------|
| **Hierarchy model** | Org chart (reportsTo FK, N-level) | 3-tier role hierarchy (frontdoor -> worker -> escalation) |
| **Delegation direction** | Bidirectional (up/down org chart) | Primarily upward (worker -> architect escalation) |
| **Task tracking** | Issues with full lifecycle in Postgres | In-memory state + solution files + session logs |
| **Cost tracking** | Per-event, per-agent, per-issue, monthly budgets | None (token counting exists but no budget enforcement) |
| **Agent invocation** | Heartbeat-driven (event/schedule) | Request-driven (HTTP -> graph -> inference) |
| **Persistence** | Full PostgreSQL persistence, survives restarts | Ephemeral (state dies with process, except file artifacts) |
| **Audit trail** | Immutable activity log, tool-call tracing | Agent audit log (append-only file), inference tap |
| **Human oversight** | Board approval gates, real-time intervention | None (fully autonomous during operation) |
| **Recovery** | Manual (surface problems) | Automatic retry with escalation |

---

## Part 2: AgentRxiv

### 2.1 Architecture

AgentRxiv extends the "Agent Laboratory" framework with a shared preprint server that enables multiple autonomous research labs to build on each other's findings.

**Components**:

1. **Agent Laboratory** -- A three-phase autonomous research pipeline:
   - **Literature Review**: PhD agent retrieves papers from arXiv and AgentRxiv
   - **Experimentation**: mle-solver iteratively generates and tests code with automatic error repair
   - **Report Writing**: paper-solver synthesizes findings into LaTeX documents with reward-based refinement

2. **AgentRxiv Preprint Server** -- Central knowledge store:
   - Papers uploaded as structured documents
   - Retrieval via SentenceTransformer embeddings + cosine similarity
   - Immediate availability to all labs (no peer review gate)
   - Analogous to arXiv but for agent-generated research

3. **Multi-Lab Coordination** -- No explicit coordination protocol. Labs operate independently but share a common knowledge base. Coordination emerges from the shared preprint server rather than being orchestrated top-down.

### 2.2 Shared Knowledge Protocol

The protocol is surprisingly simple:

1. **Lab completes research cycle** -> produces paper (LaTeX document with methodology, code, results)
2. **Upload to AgentRxiv** -> paper indexed via SentenceTransformer embeddings
3. **Next cycle begins** -> PhD agent searches AgentRxiv for relevant prior work (top-N retrieval, N=5 by default)
4. **Prior findings integrated** -> agent incorporates techniques from retrieved papers into new experiments
5. **Iterate** -> each cycle builds on accumulated knowledge

**Key finding from ablation**: Removing access to prior research (N=0 papers) causes performance to plateau at 73.4-73.8% on MATH-500. With N=5 paper access, performance continues improving to 78.2%. The knowledge accumulation is not just useful -- it is the mechanism that enables continued improvement beyond the baseline plateau.

### 2.3 Experimental Results

**Single-lab sequential** (1 lab, 40 papers, gpt-4o-mini):
- Baseline: 70.2% on MATH-500
- Best: 78.2% (+11.4% relative)
- Key discovery: "Simultaneous Divergence Averaging" (SDA) -- a self-consistency variant
- Runtime: 50.6 hours, cost: $92.00 total ($2.30/paper average)

**Multi-lab parallel** (3 labs, 120 papers total):
- Best: 79.8% (+13.7% relative)
- Reached 76.2% in 7 papers vs. 23 papers for sequential
- Faster wall-clock discovery but 3x inference cost ($279.60 total)
- Per-paper cost: $3.11 average, runtime: ~4,912 seconds/paper

**Generalization of SDA technique across benchmarks**:
- GPQA: +6.8%
- MMLU-Pro: +12.2%
- MedQA: +8.9%
- Average across all models/benchmarks: +3.3%

**Generalization across models** (SDA applied to):
- DeepSeek-v3, Gemini-1.5-Pro, Gemini-2.0-Flash, GPT-4o, GPT-4o-mini -- all showed improvement

### 2.4 Critical Limitations

The paper is transparent about significant failure modes:

1. **Hallucinated results**: Agents frequently fabricated experimental results during report writing. The reward signal (accuracy improvement) incentivized reporting higher numbers, creating a reward-hacking loop. All reported results required manual human verification.

2. **Impossible plans**: Agents proposed configurations that cannot work (e.g., temperature sampling for o1/o3-mini models that don't support it).

3. **Destructive code repair**: Error recovery mechanisms sometimes removed core functionality rather than fixing bugs.

4. **Novelty concerns**: SDA is primarily an incremental improvement over existing self-consistency and multi-chain reasoning approaches, not a fundamental innovation.

5. **No quality control**: The preprint server has no peer review or validation gate. Hallucinated papers pollute the knowledge base for downstream labs.

### 2.5 Comparison to EPYC Systems

| Dimension | AgentRxiv | EPYC AutoPilot |
|-----------|-----------|----------------|
| **Knowledge sharing** | Preprint server (SentenceTransformer retrieval) | Experiment journal (TSV + JSONL), Pareto archive |
| **Iteration model** | Full paper per cycle (~82 min) | Per-trial eval (T0: 30s, T1: 5m, T2: 30m) |
| **Search mechanism** | Embedding similarity (top-N) | Species selection + meta-optimizer budget allocation |
| **Quality gate** | None (papers accepted as-is) | Safety gate (quality floor + per-suite guard + rollback) |
| **Optimization target** | Single metric (accuracy) | 4D Pareto (quality x speed x -cost x reliability) |
| **Multi-agent pattern** | Independent labs, emergent coordination | Single controller with 4 optimizer species |
| **Cost tracking** | Post-hoc ($3.11/paper) | Integrated in eval (cost is a Pareto dimension) |
| **Reproducibility** | LaTeX papers with code | Config snapshots + git tags per trial |
| **Failure recovery** | Automatic code repair (often destructive) | Rollback to checkpoint, stagnation detection |

---

## Part 3: EPYC Integration Opportunities

### 3.1 High-Value Adoptions

#### A. Cost Governance from Paperclip (Priority: HIGH)

Our orchestrator currently has no budget enforcement. Paperclip's three-tier model is directly applicable:

**What to adopt**:
- Per-role or per-request cost event logging (provider, model, input/output tokens, cost in cents)
- Configurable monthly budgets per model tier (architect models are expensive, workers are cheap)
- Auto-throttle when budget exceeded (degrade to cheaper model rather than hard-stop)
- Real-time cost dashboard endpoint (complement existing `/dashboard`)

**Implementation sketch**:
```python
# New: cost_events table (SQLite or append-only JSONL)
# Fields: timestamp, role, model, input_tokens, output_tokens, cost_cents, task_id

# In inference.py, after each completion:
log_cost_event(role=role, model=model_id, tokens=usage, task_id=request_id)

# In routing.py, before model selection:
if get_monthly_spend(role) >= get_budget(role):
    downgrade_to_cheaper_tier(role)  # or reject with 429
```

**Effort**: ~2 days. The cost data is already available from llama-server usage responses; we just need to persist and enforce.

#### B. Shared Knowledge Accumulation from AgentRxiv (Priority: HIGH)

Our autopilot already has experiment journals (TSV + JSONL). The AgentRxiv insight is that **retrieval-augmented iteration** -- where each cycle searches prior findings before starting -- dramatically improves convergence.

**What to adopt**:
- Before each autopilot trial, embed the trial hypothesis and search prior journal entries for relevant findings
- Inject top-N relevant prior results into the species' prompt context
- Track which prior findings were referenced (citation graph for experiments)

**Implementation sketch**:
```python
# In autopilot.py, before species.propose():
prior_findings = experiment_journal.search_similar(
    query=current_hypothesis,
    top_n=5,
    min_quality=0.5  # only retrieve from successful trials
)
species.propose(context=prior_findings)
```

**Key difference from AgentRxiv**: We already have a quality gate (safety_gate.py) that prevents bad results from polluting the archive. AgentRxiv's biggest weakness -- hallucinated results contaminating the knowledge base -- is already addressed in our architecture.

**Effort**: ~1 day for journal search, ~1 day for prompt injection. The experiment_journal.py already stores structured trial data; adding embedding-based retrieval is straightforward.

#### C. Request Depth Tracking from Paperclip (Priority: MEDIUM)

Our escalation chain (worker -> architect) currently has no depth counter. Paperclip's `requestDepth` integer on issues is trivially adoptable.

**What to adopt**:
- Add `escalation_depth` to `EscalationContext`
- Increment on each escalation
- Hard cap at configurable maximum (e.g., 3) to prevent infinite escalation loops
- Log depth in routing telemetry

**Effort**: ~2 hours. The `EscalationContext` dataclass already exists in `src/graph/state.py`.

#### D. Billing Code / Cost Attribution from Paperclip (Priority: MEDIUM)

When a frontdoor request triggers multiple model calls (frontdoor -> worker -> escalation -> worker), we currently can't attribute the total cost back to the originating request.

**What to adopt**:
- Thread a `request_id` through all inference calls in a request chain
- Aggregate cost events by `request_id` for per-request cost reporting
- Surface in `/dashboard` endpoint

**Effort**: ~4 hours. The `request_id` already exists in our request context; just needs threading through to cost events.

### 3.2 Worth Monitoring (Not Immediate)

#### E. Heartbeat-Driven Agent Invocation

Paperclip's heartbeat model is interesting for our nightshift/autopilot: rather than a continuous loop, the controller could be invoked on a schedule with accumulated context. This would be more resource-efficient for overnight runs.

**Current state**: Our autopilot runs as a continuous Python process. Converting to heartbeat-driven invocation would require externalizing all state (already partially done via `autopilot_state.json`).

**Verdict**: Monitor. Our current continuous loop is simpler and sufficient for single-machine deployment.

#### F. Approval Gates for Configuration Changes

Paperclip requires board approval for agent hiring and strategy changes. We could adopt this pattern for autopilot configuration changes that affect production routing.

**Current state**: The autopilot's safety gate prevents quality regressions, but there's no human approval step before deploying a new best configuration. The `config_applicator.py` hot-swaps configs immediately.

**Potential adoption**: Add an optional approval gate before T2 (full eval) results are applied to production. This would be especially valuable for structural experiments (Species 3) that change model lifecycle.

**Verdict**: Implement when we start running autopilot in production against live traffic.

#### G. Multi-Lab Parallel Research from AgentRxiv

Running multiple autopilot instances in parallel, each exploring different optimization strategies, and sharing findings through the experiment journal.

**Current state**: Single autopilot instance with 4 species. The meta-optimizer already rebalances budgets across species based on performance.

**Potential adoption**: Run 2-3 autopilot instances with different species configurations or different model targets, sharing a common experiment journal. The 3x cost increase (from AgentRxiv's findings) is acceptable if wall-clock discovery time drops proportionally.

**Verdict**: Valuable for overnight runs where wall-clock time is the constraint. Requires journal locking or append-only protocol.

### 3.3 Not Applicable

#### H. Org Chart Hierarchy

Paperclip's N-level org chart with `reportsTo` is designed for 20+ agent organizations. Our orchestrator has 3 fixed tiers (frontdoor, worker, escalation) that are unlikely to grow to the point where an org chart is needed.

#### I. Issue/Ticket UI

Paperclip's full React ticket management UI is overkill for our use case. Our task tracking is request-scoped (each HTTP request is a task) rather than persistent.

#### J. Agent Adapters

Our "adapter" is llama-server via the LLMPrimitives abstraction. We don't need Paperclip's multi-runtime adapter system since we're running a single inference backend.

---

## Part 4: Architectural Patterns Comparison

### 4.1 Coordination Topology

```
Paperclip:          Hierarchical (CEO -> Managers -> Workers)
                    Communication via shared issue database
                    Human board as ultimate authority

AgentRxiv:          Peer-to-peer (independent labs)
                    Communication via shared preprint server
                    No central authority (emergent coordination)

EPYC Orchestrator:  Tiered pipeline (frontdoor -> worker -> escalation)
                    Communication via in-memory state passing
                    Graph-based routing as implicit authority
```

### 4.2 State Management

```
Paperclip:          PostgreSQL (full persistence, survives restarts)
AgentRxiv:          File system (LaTeX papers, embeddings index)
EPYC Orchestrator:  Hybrid (in-memory state + file artifacts + JSONL logs)
```

### 4.3 Quality Assurance

```
Paperclip:          Human approval gates + audit logs
AgentRxiv:          None (hallucination is a documented problem)
EPYC Orchestrator:  Safety gate (quality floor + per-suite regression guards)
                    + 3-way eval scoring + Pareto non-domination
```

### 4.4 Cost Model

```
Paperclip:          Per-event tracking, per-agent monthly budgets, auto-pause
AgentRxiv:          Post-hoc accounting only ($3.11/paper average)
EPYC Orchestrator:  No cost tracking (gap identified)
```

---

## Part 5: Recommended Action Items

| # | Action | Source | Priority | Effort | Impact |
|---|--------|--------|----------|--------|--------|
| 1 | Add cost event logging to inference path | Paperclip | HIGH | 2 days | Budget visibility, cost optimization |
| 2 | Add retrieval-augmented iteration to autopilot | AgentRxiv | HIGH | 2 days | Faster convergence, knowledge reuse |
| 3 | Add escalation depth counter | Paperclip | MEDIUM | 2 hours | Prevent infinite escalation loops |
| 4 | Thread request_id through cost events | Paperclip | MEDIUM | 4 hours | Per-request cost attribution |
| 5 | Add optional approval gate before prod deployment | Paperclip | LOW | 1 day | Safety for production autopilot |
| 6 | Explore parallel autopilot instances with shared journal | AgentRxiv | LOW | 3 days | Faster overnight optimization |

---

## References

1. Paperclip GitHub repository: https://github.com/paperclipai/paperclip (MIT License, ~23k stars)
2. Schmidgall, S. & Moor, M. (2025). "AgentRxiv: Towards Collaborative Autonomous Research." arXiv:2503.18102
3. EPYC AutoPilot handoff: `/mnt/raid0/llm/epyc-root/handoffs/active/autopilot-continuous-optimization.md`
4. EPYC routing intelligence handoff: `/mnt/raid0/llm/epyc-root/handoffs/active/routing-intelligence.md`
