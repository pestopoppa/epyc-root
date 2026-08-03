# Agent Architecture

**Category**: `agent_architecture`
**Confidence**: inferred
**Last compiled**: 2026-07-30 (adds the full-stack agent-file audit and restructure: layered context architecture, incident-log house style, enforcement hardening, and the frozen-tree governance gap; prior coordination-plane update retained)
**Sources**: 70+ documents

## Compiled Update — 2026-07-30 the agent-file stack: audited, restructured, enforced

An operator-requested full audit of the agent-context surface (root entry files,
`agents/` role layer, `agents/shared/` policy layer, sub-repo CLAUDE/AGENTS files,
MEASUREMENT constitution) produced a 13-defect register (D1–D13) and a same-day
restructure that landed net −214 lines while ADDING three canonical documents.
Confidence: `verified` — every defect was fact-checked against repo ground truth
before filing, and every fix was validated by the (newly hardened) validators.

### Key Findings (2026-07-30)

- **The context architecture is now explicitly layered**: per-session auto-load
  (root `CLAUDE.md`, with `AGENTS.md` symlinked; sub-repo CLAUDE.md for sessions
  rooted there) → read-order shared policy (`agents/shared/`, now including the
  extracted `SESSION_LIFECYCLE.md` as the canonical home of the wrap-up//clear/
  pre-reboot/idle-main axioms) → thin role overlays → on-demand operational docs
  (`docs/guides/agent-workflows/`). Duplication that had accreted across five
  files per rule (checkbox discipline ×5, idle-main ×5) collapsed to single
  canonical statements with pointers.
  [agent-file-audit-2026-07-30](../docs/reference/agent-config/agent-file-audit-2026-07-30.md)
- **Negative rules keep their teeth, not their narratives.** House style
  (operator-directed): every incident-derived prohibition retains its directive
  plus a one-line `origin: INC-<id>` pointer; the full blow-by-blow lives in a
  single incident log (9 entries at creation). The rule survives compression;
  the story stops taxing every session's context.
  [INCIDENT_LOG](../docs/reference/agent-config/INCIDENT_LOG.md)
- **The worst finding was an inversion of protection**: the FROZEN production
  llama.cpp tree — the highest-stakes tree in the project — had *only* upstream
  ggml-org agent files, which invite building in the tree and mandate the
  opposite commit conventions. It cannot be fixed in place (HEAD is pinned by
  the freeze verifier), so a project overlay is staged for bake-in at the next
  kernel promotion, and both sibling repos' auto-load files now carry FROZEN
  warnings. The governance matrix was expanded from one governed file to the
  full discovered surface, with a validator that discovers `repos/*/CLAUDE.md`
  and fails on unaccounted files.
  [CLAUDE_MD_MATRIX](../docs/reference/agent-config/CLAUDE_MD_MATRIX.md)
- **Enforcement now validates what agents will write, not what they wrote.** The
  reference guard was rebuilt to reconstruct and scan POST-edit content (its
  pre-edit scan both missed newly-introduced bad references and wedged the very
  edit that fixed one); the reference validator gained `#anchor` slug checking
  (GitHub-style, including the double-hyphen-for-`&` subtlety) and caught four
  latent bad references on its first run.
  [agent-file-prose-compression](../handoffs/active/agent-file-prose-compression.md)
- **The compliance suite is a deployment-gate instrument and drifts like one.**
  Restructuring the source file silently invalidated 29% of the suite's tasks
  (they probed content that moved out) — caught in zero-inference prep, fixed as
  a versioned instrument bump (`agent_file_compliance_v2_20260730`, 30/30/30
  pools) with a mechanical anchor invariant: the perfect-fake must score 1.0 at
  every compression level, so a live failure measures the model, never anchor
  availability.
  [agent-file-prose-compression](../handoffs/active/agent-file-prose-compression.md)

## Compiled Update — 2026-07-29 the coordination plane: two tiers, and one defect class

The N-main-thread control structure reached `DESIGN-RATIFIED — build-ready` and
accumulated a substantial implementation, but its **authority milestones are not
accepted**: assignment authority stays at `manual`, triage stays `off`, and
headless-worker caps stay at 0 pending a soak that cannot be compressed. The
durable knowledge from this arc is less about the transport than about a defect
class that recurred four separate times in a single day.

Confidence: `verified` for the landed code, test counts, and the operator
decisions recorded in the handoff; `inferred` for the generalization of the
polarity lesson. Milestone acceptance state is quoted as-is — several items are
"BUILT ✅ … acceptance pending", which is not the same as done.

### Key Findings (2026-07-29)

- **One role, two tiers — and the split is load-bearing.** The **coordinator-daemon**
  is host-side deterministic code (singleton under flock, tick loop, epoch fencing,
  heartbeat) and is explicitly *not* an agent; the **coordinator-agent** is an agent
  session with a roster row, inbox, outbox, heartbeat and cursor. The rationale is
  stated as a capability argument rather than a preference: an always-on watchdog
  cannot be an LLM (it compacts, dies, and costs tokens per tick), and deterministic
  code cannot draft decisions or merge. The bright line is that the daemon "never
  analyzes, reviews, or edits work products — queue/routing/watchdog only", because
  the moment it reviews, it is a second main.
  [session-bus-thin-dispatcher](../handoffs/active/session-bus-thin-dispatcher.md)

- **Single-writer ownership is structural, not conventional.** `queue.jsonl` and
  `inbox/*` belong to the daemon, `outbox/<agent>` to that agent, and token-queue
  checkboxes to the operator. Agents never write the queue — they propose and report,
  and the daemon transcribes ("pure bookkeeping, no judgment"). Adding a main is one
  roster row plus four files. Authority is matched to the writer: mains reprioritize
  their own lane only, cross-main sequencing belongs to the coordinator-agent and the
  operator, and the daemon never sets priorities.
  [session-bus-thin-dispatcher](../handoffs/active/session-bus-thin-dispatcher.md)

- **Routing intent became a structural message field, after prose routing lost real
  findings.** `needs_routing_to` and `action_required` are now schema fields with
  fail-closed authoring, backed by a lint that catches prose-only routing (it was
  validated against both of the day's actual failure messages), and by a `triage`
  standing queue that is cursor-independent and delivery-independent because it scans
  outboxes. The motivating failure is concrete: a payload truncation ate exactly the
  sentence carrying "FOR \<AGENT\>" and the finding was lost. Truncation itself was then
  made *evident* rather than silent, via numbered fences with byte counts and a
  completion trailer. The machinery caught real traffic immediately, surfacing findings
  that no relay had yet delivered.
  [session-bus-thin-dispatcher](../handoffs/active/session-bus-thin-dispatcher.md),
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **The recurring defect class: a state that could not be determined was treated as a
  benign value.** It appeared four times in one day, in four different subsystems — a
  spawn-cap undercount that *relaxed* the cap and invented capacity (and whose invariant
  was documented backwards in the docstring and in two pushed commit messages), window
  endpoints that could not be parsed, roster metadata used as a liveness proxy, and an
  unreadable tmux session. The adopted rule is to **prefer the refusal a human can
  override to the silence nobody can see**: unreadable endpoints, ambiguous window
  ownership and unparseable rows all now refuse. The corollary warning is filed with the
  blocking item — do not "fix" an unreadable tmux by counting it as zero mains, because
  that hands out occupied slots.
  [session-bus-thin-dispatcher](../handoffs/active/session-bus-thin-dispatcher.md),
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **A merged fix and a running fix are different states, and only the process owner can
  close the second.** The same lesson landed twice on one file in one day: a message
  routed to a dead session was dropped silently, the fan-out fix merged, and the notice
  stayed inert until the daemon's owner restarted it (activated at epoch 9). A third
  activation gap of the same shape is still open. Reachability is now **observed, not
  declared** — liveness is tested rather than read off roster metadata — and the policy
  is deliver-plus-warn, never refuse.
  [session-bus-thin-dispatcher](../handoffs/active/session-bus-thin-dispatcher.md),
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **The delivery plane can be entirely healthy while coordination fails at the last
  hop.** The first `coordinator-agent` instantiation ran with its cursor **33 messages
  behind**, including a hard block needing an operator signature and a completed audit
  carrying two CRITICAL findings — while daemon relay, boundary detection and the
  severity watcher all functioned correctly. Every fix shipped that day was in the
  delivery plane; the actual defect was in **bus → operator**, which is judgment and
  cannot be mechanised. It became a standing rule on *every* reply rather than a startup
  step: **DRAIN BEFORE YOU SPEAK**. A companion artifact was promoted to first-class
  status for the same reason: `rebuild` reconstructs the bus *mechanism* (queue rows,
  tokens, cursors, unread depth) but carries no record of what a session was mid-way
  through or which gate a campaign is parked behind — so a fresh coordinator correctly
  reports an empty queue while a campaign sits one command from resuming. The mechanism
  makes a coordinator addressable; the brief makes it useful.
  [session-bus-thin-dispatcher](../handoffs/active/session-bus-thin-dispatcher.md),
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **A test suite can be green because it cannot fail.** A standalone adapter suite shared
  a basename with another test file, so pytest raised an import-file-mismatch collection
  ERROR that aborted the entire run — and its entry points never asserted, so had it been
  collected it would have reported PASS with every check failing. Fixing it also exposed a
  racy fixture (a spawned `command="true"` is reaped in ~0.3 s), which retroactively made an
  earlier "37/37" **flaky-green**. Separately, no whole-repo pytest existed at all; creating
  one moved the tree from 2200 collected + 46 errors + aborted to 576 collected with 0 errors
  and a completing run. The stated goal is worth preserving: *a run that is honestly red, not
  a green one.* [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **Bus noise is a payload-shape property, not a retry bug.** An operator complaint about a
  repeated triage disposition audited clean on the transport — 19 messages, 19 distinct
  `corr_id`s, 19 distinct ids, relayed 1:1 with no fan-out. The real defect was a
  byte-identical ~1.5 KB payload sent 19 times, differing only by `corr_id`, because clearing
  triage requires one `corr_id` per item. Rule adopted: a repeated payload across N `corr_id`s
  is noise by construction — make the body per-item, or send one message naming all N. The
  underlying protocol gap (no bulk-clear granularity) was filed rather than worked around.
  [progress 2026-07-29](../progress/2026-07/2026-07-29.md)

- **Adversarial critique escalates by construction unless something is chartered to delete.**
  A nine-agent specification effort consumed ~919k tokens over ~43 minutes to produce a
  ~113k-character spec, which was rejected as disproportionate to the problem. The recorded
  process lesson is that a panel of that shape needs a fourth lens whose job is to *delete*.
  [session-bus-thin-dispatcher](../handoffs/active/session-bus-thin-dispatcher.md)

### Open Questions (2026-07-29)

- Assignment authority (M4) is code-complete and **not accepted**: its go/no-go rests on the
  advisory-accuracy evidence of the read-only tier — would-assign matching actual human and
  agent choices over a working day, with divergences explainable. That needs elapsed time and
  cannot be compressed. Until then the switch stays at `manual`, `triage` stays `off`, and
  headless-worker caps stay at 0.
- The CPU-region claim is **structurally verified, not end-to-end verified** — a real
  `llama-bench` has never acquired the claim, held it through a run, and released it.
- Ownership of the whole tmux-adapter hardening arc lapsed when its session was re-tasked; it
  is filed as unowned and re-assignment is a coordinator call.
- One blocking bring-up dependency is manual by design: nothing creates the tmux session a
  spawn requires, and the adapter will never create one, so a human must create it before any
  spawn can succeed.
- The handoff and the day's final wrap-up disagree on the current concurrency-cap number (the
  handoff entry predates an operator raise the same day). Treat the handoff's figure as stale;
  the authoritative value is whatever the live config says, and this wiki deliberately records
  no number.

### Source References (2026-07-29)

- [session-bus-thin-dispatcher.md](../handoffs/active/session-bus-thin-dispatcher.md) — the
  daemon/agent nomenclature split and bright line, single-writer ownership, authority matrix,
  structural routing fields, milestone acceptance state, rider status, and the C-series ledger.
- [progress 2026-07-29](../progress/2026-07/2026-07-29.md) — the polarity arc across four
  subsystems, the activation-gap repetition, the coordinator-agent instantiation and close,
  the invisible-suite and whole-repo-pytest findings, and the bus-noise diagnosis.
- [gpu-serving-tie-in-program.md](../handoffs/active/gpu-serving-tie-in-program.md) — an
  operator decision (activation sequencing) routed and recorded *through* the bus as a task
  id, demonstrating the decision-package path the coordination plane exists to carry.

## Summary

The EPYC orchestrator is a pydantic_graph-based multi-agent system running on a single AMD EPYC 9655 (192 threads, **4 NUMA nodes** — NPS4 since the 2026-04-24 reboot; corrected 2026-07-30 from "2 NUMA nodes") with llama.cpp as the inference backend. It uses 7 typed node classes across 4 model tiers (frontdoor, coder, architect, worker), a 180+ field mutable TaskState, and compile-time safe transitions via Union return types. Routing decisions are made by a MemRL learned routing system with MLP+GAT classifiers, Q-value weighted voting, and a factual-risk scorer. A 3-tier escalation ladder (worker to coder to architect) handles complexity beyond the initial role's capability, while a 5-layer context management pipeline (hard preview, stale clearing, session log, compaction/virtual memory, solution file persistence) ensures context window pressure stays manageable on the 8K-32K windows available to local quantized models.

Three deep-dives map the design space against external architectures. Paperclip (intake-115) represents the hierarchical org-chart model: N-level reporting chains with `reportsTo` self-referential foreign keys, heartbeat-driven agent invocation, PostgreSQL-backed issue tracking with atomic checkout and full goal ancestry, and a three-tier cost governance layer (visibility, soft alerts, hard ceiling with auto-pause). Its coordination is task-centric -- all inter-agent communication flows through issue creation and status updates, with no separate messaging system. AgentRxiv (intake-131) represents the peer-to-peer model: independent research labs operating autonomously and sharing findings through a preprint server indexed by SentenceTransformer embeddings. Coordination emerges from shared knowledge rather than explicit orchestration, achieving 13.7% improvement on MATH-500 through iterative accumulation, though with a critical weakness -- no quality control on shared findings, leading to hallucinated papers polluting the knowledge base. OpenGauss (intake-172/173) represents the production agent shell: a CLI-first multi-agent orchestrator forked from hermes-agent and specialized for Lean 4 theorem proving, with managed backend spawning, protected-zone context compression with tool-pair sanitization, prompt injection scanning, ACP (Agent Client Protocol) server, and ShareGPT-format trajectory export.

The EPYC orchestrator's tiered pipeline sits between these topologies. It has stronger coordination than AgentRxiv's peer-to-peer approach (explicit routing decisions, escalation chains, safety gates) but less rigid hierarchy than Paperclip's org chart (no persistent issue database, request-scoped lifecycle). Where it genuinely leads the field is in three areas: (1) learned routing intelligence that no surveyed framework matches -- MemRL Q-value weighted routing, factual-risk scoring, difficulty signal classification, 9 production routing subsystems that coordinate without conflicting; (2) 5-layer context management versus basic message trimming (LangGraph) or no management at all (Paperclip, AgentRxiv); and (3) production safety infrastructure with 43+ feature flags, quality floor gates, per-suite regression guards, consecutive failure auto-rollback, and a think-harder ROI calculation that regulates compute spend on escalation.

The key architectural tension is between the current pydantic_graph's flat 7-node structure and the need for composable subgraphs as the system grows. LangGraph's subgraph composition, checkpoint granularity with time-travel debugging, and `interrupt()` flexibility at any node represent genuine capability gaps. However, migration carries significant risk: 180+ state fields, 120+ tests, and deep domain-specific features (MemRL, think-harder ROI, budget enforcement, 5-layer context) have no LangGraph equivalents and would require porting. The recommended path is hybrid -- build new capabilities as LangGraph subgraphs alongside the existing pydantic_graph, migrating nodes incrementally.

### New Findings (2026-07-08 — local-first authority restart with process-relative planner freshness)

- **The routing plane now runs through a fresh local-first authority wrapper instead of the older cloud-default restart target.** AutoPilot restarted as PID `3681234` with `AUTOPILOT_PLANNER_PRIMARY=local_ingest`, `AUTOPILOT_PLANNER_CRITIC=local_frontdoor`, `stack_mode=both`, and `code_stale=false`. That is an architecture-level shift: the planner path now prefers the local stack by default while still preserving a distinct critic role and explicit restart boundary. Sources: [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md), [master-handoff-index.md](../handoffs/active/master-handoff-index.md), [progress 2026-07-08](../progress/2026-07/2026-07-08.md).

- **Planner evidence is now process-relative rather than text-relative.** `b5cadba6` added `planner_tap_mtime_s` and `planner_tap_precedes_autopilot_start`, so dashboard consumers can tell whether a planner tap is actually from the current process or just a stale file still on disk. That is an observability contract change, not just a UI tweak: it prevents old tap history from masquerading as current routing evidence. Sources: [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md), [frontier-f2-self-running-lab.md](../handoffs/active/frontier-f2-self-running-lab.md), [progress 2026-07-08](../progress/2026-07/2026-07-08.md).

- **Planner prompt hygiene is now enforced as a separate containment rule.** `b7518da0` keeps `StrategyStore` hints in planner-context only, ignores legacy `strategy_hints` on Seeder, and quarantines the contaminated `1257-1263` trials append-only with `bug_corrupted_by=b7518da0`. Architecturally, that separates durable evidence from mutable prompt assembly, which is the right boundary if the routing plane is going to keep learning from its own history without replaying corrupted history into new actions. Sources: [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md), [progress 2026-07-08](../progress/2026-07/2026-07-08.md), [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md).

- **The live loop now has explicit supervision and attestation surfaces, not just "start" and "restart" paths.** The orchestration robustness wrap-up landed a supervisor/death ledger wrapper for autopilot launches plus startup attestation that records config digests, a combined config hash, gate-environment capture, mismatch reporting, and phase-health flags for tool/planner state. The planner spend breaker is intentionally visible but not required: the local-planner authority daemon runs with `AUTOPILOT_PLANNER_SPEND_BREAKER=0`, and phase health reports that state so future sessions do not infer the wrong contract from a stale test. Sources: [orchestration-robustness-audit-2026-07-11.md](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [progress 2026-07-11.md](../progress/2026-07/2026-07-11.md).

- **The REPL/tool surface now exposes a compatibility layer for the exact failure modes the audit measured.** `FINAL(...)` keyword aliases (`answer`/`result`/`secret`/`value`/`response`) are accepted and unsupported kwargs fail loudly, while builtin compatibility tools (`search_files`, `get_time`, `fetch_stock_price`, `translate_text`, `start_service`) are registered with safe/read-only behavior. That reduces the chance that tool availability diverges from prompt expectations and silently wastes trials. Sources: [orchestration-robustness-audit-2026-07-11.md](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [progress 2026-07-11.md](../progress/2026-07/2026-07-11.md).

- **PromptForge's code-mutation surface now has a safer new-file primitive instead of a generic write hatch.** MH-9 landed bounded `new_file` proposals under `src/` with absolute/traversal rejection, parent-directory existence checks, collision checks, syntax/import validation, dirty-fence coverage for parent directories, and fresh-file apply/revert handling for no-index diffs. Sources: [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md), [progress 2026-07-11.md](../progress/2026-07/2026-07-11.md), [orchestration-robustness-audit-2026-07-11.md](../handoffs/active/orchestration-robustness-audit-2026-07-11.md).

### New (2026-07-14, process-attested autonomy boundary)

- **The architecture now makes process identity and gate state part of the agent contract.** A fresh authority daemon replaced a stale supervisor/child pair after SIGKILL verification, and the live phase health exposed `planner_prompt_build`, `code_stale=false`, `tool_sentinels=true`, `w6_audit=true`, and `AUTOPILOT_PLANNER_SPEND_BREAKER=0`. That turns restart hygiene into an architectural concern: agents are only meaningful when their current code and gate-set are known, not merely when the PID exists. Sources: [orchestration robustness audit](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [Progress 2026-07-14](../progress/2026-07/2026-07-14.md).
- **The dashboard-facing lock view now exposes the full configured topology, not only the active-runtime subset.** The 2026-07-14 region-lock topology sidecar teaches the display to keep configured quarter instances visible under `stack_numa_mode=full`, mark `launch_selected`, and label all configured NUMA ports independently of the expected launch mode. That is an architectural correction because the operator view now reflects the configured launch topology directly instead of collapsing it to whatever happens to be active at the moment. Sources: [orchestration-robustness-audit-2026-07-11.md](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [Progress 2026-07-14](../progress/2026-07/2026-07-14.md), `epyc-orchestrator` `774fed69`.

- **The web/tool boundary now records evidence quality separately from tool availability.** Gate-3 showed the tool-sentinel lane healthy (`get_eval_secret` 7/7, no-tool isolation passed) while `web_research` failed closed as `search_failed`; a fallback DDG hit can still be surfaced as a relevant result, but it no longer upgrades the failed search into a fake success. That is the correct agent-architecture split between "tool path worked" and "evidence was good." Sources: [orchestration robustness audit](../handoffs/active/orchestration-robustness-audit-2026-07-11.md), [HALO Spike Results](../research/deep-dives/halo-spike-results-2026-07-14.md).

### New Findings (2026-07-16 — open-source harness selection became a first-class architecture gate)

- **The user-facing harness is now treated as a selectable open-source integration point, not a hardcoded frontend.** The new parent index makes the load-bearing split explicit: the orchestrator keeps the backend moat behind `/v1/chat/completions` + `x_*`, while the harness must cooperate with routing, context folding, and escalation. Closed harnesses are excluded because that cooperation cannot be enforced externally. Sources: [harness-selection-and-integration.md](../handoffs/active/harness-selection-and-integration.md), [hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md), [hermes-agent-index.md](../handoffs/active/hermes-agent-index.md), [progress 2026-07-16](../progress/2026-07/2026-07-16.md).

- **Hermes remains the candidate track, not the general decision.** Hermes/OpenGauss is still the most concrete open harness surface, but the new selection index means the Hermes outer shell should stay scoped to Hermes-specific validation and packaging. OpenCode and ACP-speaking harnesses remain open candidates until HS-1/HS-2 settle the cooperation-surface and ACP ROI questions. Sources: [hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md), [harness-selection-and-integration.md](../handoffs/active/harness-selection-and-integration.md), [hermes-agent-index.md](../handoffs/active/hermes-agent-index.md).

## 2026-07-19 Update — reviewer control plane is additive and release-decoupled

- The reviewer control plane now has a concrete typed-decision integration path: reviewer false-accept/false-reject and decision-latency axes are optional additive evaluation dimensions, and the autopilot critic loop emits schema-valid `ReviewDecision` records without changing planner content or control flow. Sources: [autopilot control-plane integration](../handoffs/active/autopilot-control-plane-integration.md), [GLM reviewer capability gates](../handoffs/active/glm52-reviewer-capability-gates.md), [reviewer model ablations](../handoffs/active/reviewer-model-ablations.md).
- The evaluation contract is representation-scoped. Exact-answer, patch-diff, code-prefix, and judge-preference tasks need separate corpora/scorers; a mixed "balanced" slice can create misleading calibration and must be rejected by the runner. Sources: [GLM reviewer capability gates](../handoffs/active/glm52-reviewer-capability-gates.md), [reviewer model ablations](../handoffs/active/reviewer-model-ablations.md), [model-probe scoreboard](../docs/reference/model-probe-scoreboard.md).
- The current architecture separates production orchestration from reviewer experimentation. GLM and the fast RM-2 slate are not admitted as production patch reviewers, while v7 production promotion proceeds on independent inference gates; future reviewer admission requires a new repair hypothesis or screened candidate, not unchanged reruns. Sources: [v7 promotion](../handoffs/active/v7-promotion.md), [GLM reviewer capability gates](../handoffs/active/glm52-reviewer-capability-gates.md), [autopilot control-plane integration](../handoffs/active/autopilot-control-plane-integration.md).

## Key Findings

### 2026-07-28 — Transport-only coordination and contract-backed tooling

- **The session bus distinguishes mechanical delivery from autonomous coordination.** At
  `manual|advisory` authority, the daemon may relay an explicitly addressed outbox message, issue
  a fixed overdue-ACK redelivery, or surface a recorded non-idle-to-idle boundary, but it cannot
  choose work, mutate queue/lease/gate state, or determine a token outcome. The acceptance witness
  is therefore a provenance trace over each mutation—not the retired "two files written" proxy.
- **Agent-facing enforcement and client helpers need tests that model their real contracts.** The
  reference guard now resolves the nested session-bus references used by the compliant coordinator
  role instead of forbidding that valid idiom. Separately, the Hermes reference-client tests now
  construct the parser's complete `max_tokens` Namespace and prove both default omission and
  explicit request-cap inclusion. These repairs preserve production behavior while making the
  stated interfaces executable.
- **Readiness evidence is only useful when it points to an artifact.** Recursive readiness surfaces
  now expand to concrete non-ignored files, so an empty directory cannot claim security or native
  tooling readiness and remediation consumers receive the actionable path that justified a pass.

#### Source References

- [Session Bus + Thin Coordinator](../handoffs/active/session-bus-thin-dispatcher.md) — M3
  decision-property acceptance, C7/C8 coverage, and guard self-idiom regression.
- [Hermes/OpenGauss as Outer Shell](../handoffs/active/hermes-outer-shell.md) — reference-client
  parser and payload contract regression.
- [Repo-Readiness Scorer](../handoffs/active/repo-readiness-scorer.md) — file-level evidence
  requirement and empty-directory regression.
- [Progress 2026-07-28](../progress/2026-07/2026-07-28.md) — focused validation outcomes and
  remaining C6 limitation.

### New Findings (2026-07-06 — Hermes boundary generalized to multi-client contract)

- **Hermes is now framed as one client of a shared orchestrator contract, not a special routing path.** The active Hermes handoff now records the governing boundary: client-specific UX stays at the edge, while the orchestrator owns the stable OpenAI-compatible `/v1/chat/completions` plus `x_*` override surface. The July 2026 audit closed the non-Hermes client sufficiency pass: bare SDK/curl, Hermes, coding-agent proxies, IDE clients, and KB-RAG/retrieved-context clients can all express current needs through standard OpenAI fields plus `x_orchestrator_role`, `x_max_escalation`, `x_force_model`, `x_disable_repl`, and `x_show_routing`. Remaining live work is validation and packaging, not new orchestrator policy: test `x_disable_repl` end-to-end, verify `x_max_escalation` when full graph enforcement is available, and optionally repackage the skills as a namespaced Hermes plugin bundle. Sources: [hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md), [progress 2026-07-02](../progress/2026-07/2026-07-02.md), [progress 2026-07-04](../progress/2026-07/2026-07-04.md).

### New Findings (2026-07-06 — operator-facing optimization brief now explains rejected search space)

- **The optimization brief is now a better steering surface because it surfaces what the planner has already ruled out, not just what it is still exploring.** `scripts/autopilot/optimization_brief.py` now emits a `ruled_out_experiments` block that separates critic-rejected fenced proposals from malformed-surface churn, and `src/api/routes/dashboard.html` renders that data under the operator brief as a compact "what's been ruled out (and why)" section. That makes the dashboard's optimization view closer to an operator summary: current levers, fence reasons, and invalid-surface hotspots are visible together. Sources: `scripts/autopilot/optimization_brief.py`, `src/api/routes/dashboard.html`, [loops-and-dashboards-audit-2026-07-05.md](../handoffs/active/loops-and-dashboards-audit-2026-07-05.md), [2026-07-06 progress](../progress/2026-07/2026-07-06.md).

### New Findings (2026-07-05 — consult v1 wired default-off, BEP verifier gate, DCP J7 hold, MindDR parked at its A/B gate)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. Several numbers below (J7 latency/token deltas, bake counters) are observations without decision-gating protocol citations.

- **The internal consult primitive went from design to a fully staged, default-off v1 in one week — every layer shipped behind flags while live behavior stays locked on the P1 bake.** IIL P1 (the `Interaction` lifecycle substrate) landed 2026-06-28 in orchestrator `18956892` as a proven no-behavior-change refactor: `delegation_diagnostics` byte-equal regression test, additive `interaction_type="delegate"` field (no rename of `DelegationEvent`/`delegation_events`), and a clean affinity-preflight artifact (22 instances across 6 roles, `live_affinity_verified=true`, 0 memory mismatches). The P2 consult scaffold then staged 2026-07-04 with zero inference: `orchestration/interaction_skills.yaml` (`architect_general.review_before_commit`, JSON output schema, background priority, 400 max output tokens, 0 tools budget, 1800s TTL), `src/orchestration/consultation.py` with schema-constrained `consult()` + `ConsultationDenied` + contention-to-`contention_skip` translation, consult namespacing on `DelegationCache.make_key()` preserving legacy delegate keys, and `ProgressLogger.log_consult()`. On 2026-07-05, `0e555822` wired the first consult site at the P2-0 seam (`run_edit_transaction()`, `force_mode="edit"` route) behind a new `review_before_commit_consult` flag: at most one requester rerun on high-confidence blocking advice, consult events surfaced in response diagnostics, flag-off preserves one-shot edit behavior exactly. The remaining gate is purely evidential: bake readouts advanced 28.96h→38.04h of the required 48h with 3 delegation-cache lookups / 0 hits / 0 ContentionDenied — blockers `window_too_short` and `delegation_cache_split_comparison_unavailable`, not instrumentation absence. [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md) P1/P2; [progress 2026-07-04](../progress/2026-07/2026-07-04.md) §IIL P2 scaffold; [progress 2026-07-05](../progress/2026-07/2026-07-05.md) §Prompt-and-BEP-verifier `verified`

- **Consult deliberately reuses the DCP seed-context packer instead of growing a second one.** Orchestrator `4183522f` added a default-off `dcp_for_consult` flag (requires `dcp_pre_assembly`) so `consult()` packages context via the existing `_maybe_dcp_seed_context()` ranking/rendering when a caller supplies `code_search_fn` and both flags are on. This enforces the architectural rule stated in both handoffs: DCP owns context packaging, IIL owns consult lifecycle — no parallel packers. [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md); [delegation-context-preassembly.md](../handoffs/active/delegation-context-preassembly.md) cross-cutting `verified`

- **The batch-edit (BEP) safety arc closed a full transactional-apply story between 2026-06-28 and 2026-07-05, all while the flag stays default-off.** Five hardening steps landed on the legacy think-then-act patchset path: (1) sandbox promotion now refuses live-tree promotion unless verification explicitly passed; (2) the runner fail-closes under-evidenced edits — a patch touching a file in the DCP bundle's `omitted_context_paths` blocks the whole set pre-sandbox (the first live BEP↔DCP manifest coupling from audit item #6); (3) live promotion is transactional across copy/delete phases with backup-and-restore on failure; (4) deterministic BEP-4 fan-out is real — independent files within a dependency stage apply concurrently in the sandbox while declared stages serialize; (5) sandbox apply is atomic on stage failure (snapshot + restore, apply metadata cleared so callers can't mistake a restored sandbox for a partial diff). Then `8fb8f69a` (2026-07-05) added the missing whole-repo accept gate: setting `ORCHESTRATOR_BATCH_EDIT_VERIFY_CMD` stages a lightweight full-tree snapshot with touched-file overlay and runs the command in the sandbox before any promotion; unset preserves touched-file py_compile. GitNexus marked `_maybe_batch_edit_turn` CRITICAL blast radius, which is why the live hook change stayed default-off and env-gated. The strategic status is unchanged: the edit transaction remains the production multi-file fix, and BEP-2/J8 stays an optional decision experiment for whether `batch_edit_mode` is kept, retired, or scoped. [batched-edit-parallel-apply.md](../handoffs/active/batched-edit-parallel-apply.md); [progress 2026-07-05](../progress/2026-07/2026-07-05.md) §Prompt-and-BEP-verifier `verified`

- **DCP's first live J7 A/B is a self-classified `hold`: it won on tokens, lost on latency, and was never quality-scored.** The n=3/arm run (orchestrator `56a72f6`, artifact `benchmarks/results/runs/dcp_j7/20260619T113143Z/`) completed cleanly (6/6 HTTP-200, zero errors) with ON cutting average generated tokens 352.0→247.3 but worsening p50 latency 20.2s→32.6s; `dcp_pre_assembly` stays default-off. Two governance mechanics are the durable lesson: the runner summary now emits a `decision` block (`dcp_j7_decision.v1`, blockers `latency_not_improved` + `quality_not_scored`) so future clean-window runs are self-classifying, and `c3b2514e` added a read-only DCP/J7 section to `generate_attestation.py` so running-state attestation surfaces the latest artifact status without launching inference — the eval verdict and its visibility are both artifacts, not tribal memory. Separately, DCP-5's non-prescriptive discovery prompt landed 2026-07-05 in `b7ba6265` (`architect_investigate` reframed as evidence-bundle/open-questions-first), prompt-surface-only with DCP-6 still the enablement gate. [delegation-context-preassembly.md](../handoffs/active/delegation-context-preassembly.md) DCP-5/DCP-6 `observed`

- **MindDR `deep_research_mode` is the page's one fully-built-but-never-measured pipeline: Phase-1 scaffold complete since 2026-04-22, parked at the inference-gated MD-9 A/B ever since.** The three-agent role-specialization pattern (PlanningNode → DeepSearchFanOutNode with bounded asyncio fan-out → ReportSynthesisNode) is implemented as a standalone `src/graph/minddr/` subpackage deliberately decoupled from production dispatch — wiring is an intentional 1-line check deferred until evidence exists. The promotion rule is crisp: default-on only if rubric uplift ≥+5pp on the 20-query sentinel suite, no eval-tower regression, and tool calls ≤2× baseline; structural-`expected_contains` scoring alone cannot promote (EV-9 rubric is the required scorer), and MD-9 must hold if no web/search backend is live (a research pipeline without retrieval is not the paper's claim). Phase 2 (four-stage RL: SFT → Search-RL → Report-RL → DPO) is GPU-gated — its "DGX Spark" wording is stale post-MI210 pivot and needs re-basing before any Phase-2 planning. Contradicting-evidence flags stand: MindDR Bench 51.8 is self-curated Li Auto data (deployment evidence, not generalization); public anchors are BrowseComp-ZH 45.7 / WideSearch 46.5 / xbench-DS 75.0. [minddr-deep-research-mode.md](../handoffs/active/minddr-deep-research-mode.md) `planning`

- **AutoPilot planner drafting moved from cloud-only to local-first (2026-07-05).** Orchestrator `7036630c` added `LocalPlannerProvider` calling the orchestrator's own OpenAI-compatible `/v1/chat/completions` with role aliases (`local`, `local_worker`, `local_ingest`), `x_orchestrator_role` + `x_disable_repl=true`; the Fable authority launcher now defaults `AUTOPILOT_PLANNER_PRIMARY=local_ingest` with `AUTOPILOT_PLANNER_CRITIC=codex`. Operator-decided fallback semantics: if the local drafter fails and Codex emits a schema-valid fallback draft, dispatch proceeds without pausing, with provider/fallback recorded in planner-archive telemetry. Queued next: a two-stage local provider (`ingest_long_context` produces a bounded planner brief → `frontdoor`/`worker_general` drafts) with Codex retained as critic/escalation. This is the meta-loop eating its own dogfood — the optimizer's planning inference migrating onto the stack it optimizes. [progress 2026-07-05](../progress/2026-07/2026-07-05.md) §AutoPilot local planner provider `verified`

- **Parallel tool-call batching already exists; the real bottleneck is that tool use is barely exercised.** A read-only sidecar investigation found the orchestrator already has a conservative parallel path for multiple independent read-only structured REPL calls in one model response (`REPLEnvironment._execute_structured()` + `execute_parallel_calls()`). Recent AutoPilot windows still show near-zero live `total_tool_calls`, and a 2026-07-06 diagnostics refresh confirmed only `30/807` REPL rows with multiple tools and `0` recorded `parallel_tools_used=True` rows, so batching remains a measurement follow-up (measure `len(tools_called) >= 2`, read-only eligibility, `parallel_tools_used`) before touching HIGH/CRITICAL executor paths — recorded in [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md). [progress 2026-07-05](../progress/2026-07/2026-07-05.md); [progress 2026-07-06](../progress/2026-07/2026-07-06.md) §REPL multi-tool batching telemetry `observed`

- **The self-running lab split agent-safe monitoring from quiet-window inference — deterministic read-only jobs now run while AutoPilot and 30 llama-servers are active.** Orchestrator `0f7252bb` + `4829028d` added guarded `deterministic_command` lab jobs (`risk=read_only`, argv list, JSON-schema-validated stdout) with mutually exclusive `--active-safe-only` / `--quiet-window-only` selection, and the nightshift wrapper now runs active-safe deterministic jobs first, then model-backed shadow jobs only when inference is quiet. First enabled job: `autopilot_authority_watch` wrapping the phase-health report, so AutoPilot code-staleness monitoring no longer needs a quiet window. This is a clean two-tier agent-autonomy taxonomy: deterministic observation is always-safe; model-backed judgment is contention-gated. [progress 2026-07-05](../progress/2026-07/2026-07-05.md) §Self-running lab `verified`

### New Findings (2026-07-07 — Internal Interaction bake gate cleared; J17 targeted consult **targeted-positive / default-off**; targeted consult gate implemented; F2/F3 lab evidence)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. J17 quality deltas and bake counters are observations without decision-gating protocol citations.

- **The Internal Interaction P1 bake gate is now cleared.** Quiet-window probe issued two real delegated `/chat` requests (`mock_mode=false`, `force_role=architect_general`, `force_mode=delegated`) to generate delegation-cache observations in the bake's second half. `orchestration/reports/internal_interaction_bake_report_20260707T005105Z.{json,md}` reports `gate_ready=true`, blockers `none`, full-window lookups/hits/misses `4/0/4`, split miss rates `1.0/1.0`, and `0` ContentionDenied events. The P1 regression/contention bake no longer blocks Internal Interaction work. Sources: [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md), [progress 2026-07-07](../progress/2026-07/2026-07-07.md).

- **J17's first live A/B was a blanket-negative, but a targeted rerun showed real consult value.** The initial 5-task BEP sandbox repeated 10x showed zero quality delta (`0.800/0.800`) and `+22.58%` latency. A second targeted 10-task high-risk slice (parser edge cases, data-contract edits, transaction rollback, etc.) scored baseline `35/50` (`quality=0.70`) vs consult `40/50` (`quality=0.80`), a `+10.0pp` quality lift. Consult rescued the parser/comment/value edge case from `0/5` to `5/5` but failed on transaction-rollback and plugin-registry verifier. Coder wall p50 rose `5.093s` to `5.831s` (`+14.49%`). **Decision**: J17 updated from blanket HOLD to **targeted-positive / default-off** — consult gates should fire only on high-risk task shapes, parser/data-contract edits, high blast radius, or known hidden-verifier-risk patterns. Sources: [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md), [progress 2026-07-07](../progress/2026-07/2026-07-07.md).

- **The targeted consult gate is implemented and default-off.** `src/orchestration/review_consult_gate.py` triggers on parser/data-contract terms, compatibility/fallback terms, hidden-verifier or transaction-risk terms, deletes, multi-file edits, and public API/registry/config paths; skips unparsed drafts and plain single-file edits. Flag `review_before_commit_targeted_gate` (`ORCHESTRATOR_FEATURE_REVIEW_BEFORE_COMMIT_TARGETED_GATE=1`) is inert unless `review_before_commit_consult` is also enabled. Skipped consults are `targeted_gate_skip` events with `gate_reasons`. Focused pytest `86 passed`. Sources: [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md), [progress 2026-07-07](../progress/2026-07/2026-07-07.md).

- **F2 quiet-window lab produced real gold tuples.** `scripts/lab/run_job.py` resolves lab roles to live orchestrator roles and rejects mock responses. `handoff_freshness_lint` passed as real `worker_general`; `attestation_watch` required reduced context budget then passed. One positive `lab_gold_tuple.v1` accepted, one negative rejected after review caught a false attestation-empty claim. `review_queue_report.py` reports `pending_reviews=0`, `verdicts=12`. Sources: [frontier-f2-self-running-lab.md](../handoffs/active/frontier-f2-self-running-lab.md), [progress 2026-07-07](../progress/2026-07/2026-07-07.md).

- **F3 trusted-label gate cleared and baseline acceptance passed.** Four prompt-free review packets applied to reach `100` trusted labels. Baseline report: `80` train rows, `20` held-out, `18` correct, `0.90` accuracy, threshold `0.85`. F3 W2 satisfied; remaining blockers: F2 tuple evidence and gfx90a training-viability. Sources: [frontier-f3-data-flywheel.md](../handoffs/active/frontier-f3-data-flywheel.md), [progress 2026-07-07](../progress/2026-07/2026-07-07.md).

**Sources**: handoffs [internal-interaction-lifecycle](../handoffs/active/internal-interaction-lifecycle.md), [batched-edit-parallel-apply](../handoffs/active/batched-edit-parallel-apply.md), [delegation-context-preassembly](../handoffs/active/delegation-context-preassembly.md), [minddr-deep-research-mode](../handoffs/active/minddr-deep-research-mode.md), [frontier-f2-self-running-lab](../handoffs/active/frontier-f2-self-running-lab.md), [frontier-f3-data-flywheel](../handoffs/active/frontier-f3-data-flywheel.md) · progress [2026-07-04](../progress/2026-07/2026-07-04.md), [2026-07-05](../progress/2026-07/2026-07-05.md), [2026-07-06](../progress/2026-07/2026-07-06.md), [2026-07-07](../progress/2026-07/2026-07-07.md) · orchestrator commits `18956892`, `0e555822`, `4183522f`, `8fb8f69a`, `b7ba6265`, `7036630c`, `0f7252bb`, `56a72f6`, `c3b2514e`

### New Findings (2026-07-02 — fixed-model harness evolution + Fable 5 window-2 architecture co-leads)

- **An external empirical run confirms EPYC's core bet: for a frozen open-weight model, evolving the harness alone can lift held-out task performance from ~0% to 80%.** "Don't Train the Model, Evolve the Harness" (intake-753, Joel Niklaus) ran our exact loop — an Opus proposer that reads execution traces and proposes one mechanism per iteration, scored by a Python evaluator over a 24-task dev set × 3 trials — against DeepSeek-V4-Pro on Harvey's Legal Agent Benchmark, lifting held-out pooled-criterion pass from 63.4 to 80.1 (all-pass 0→5.0) with zero weight changes and beating external harnesses on the same model (Pi 45.4, Goose 23.2, mini-swe-agent 3.5). This maps ~1:1 onto our HLE-3/J9 fixed-model harness lane, which serves fixed open models where weight training is off the table. [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md) Research Intake Update 2026-07-02; [intake-753](https://huggingface.co/spaces/joelniklaus/harness-optimization) `external`

- **Prefer deterministic-code mechanisms over prompt edits for weak/frozen models — and tune the harness per served model, because code fixes transfer across families but prompt playbooks do not.** In intake-753, 5 of the top 6 accepted harnesses were deterministic code mechanisms, not prompt edits — empirically validating our Tier-2 code-mutation search over pure PromptForge prompt-editing. Transfer is mechanism-type-dependent: a code-based harness carried +14.4 pts to the same-family V4-Flash but a prompt playbook carried only +0.4 pts cross-family to Nemotron-3 Ultra. Two additional harvestable patterns: a cost-aware scoring formula `pooled_criterion + 0.5·all_pass − 0.005·tokens_per_million` with copy-and-adapt accepted-frontier inheritance, and a 3-trial ≥1-point noise-margin promotion rule that mirrors our resolution-aware / mad_noise gate. MEASUREMENT.md caveat: single legal benchmark, LLM-judge scoring, non-peer-reviewed — usable to shape the proposer contract, NOT to gate promote/revert without local re-measurement. [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md) MH intake update; [intake-753](https://huggingface.co/spaces/joelniklaus/harness-optimization) `external`

- **The Darwin Gödel Machine stress-tests two of autopilot's design choices: greedy Pareto pruning vs. keep-all-stepping-stones archives, and whether the meta-optimizer code should be self-mutable.** DGM (intake-772, Zhang/Hu/Lu/Lange/Clune, arXiv:2505.22954) is a self-referential coding agent that iteratively rewrites its own code-editing codebase, validated empirically each iteration (SWE-bench 20.0→50.0%, Polyglot 14.2→30.7%), and both ablations — "w/o self-improvement" and "w/o open-ended exploration" — are load-bearing. Its distinctive triad relative to our corpus: self-referential improvement of the editing agent itself, an open-ended growing-tree archive that retains all variants as stepping stones (the opposite of our ParetoArchive's dominated-config pruning), and performance×fecundity parent sampling (score × number of edit-capable children). Harvestable for autopilot: a bounded open-ended stepping-stone lane that retains a diversity-sampled subset of dominated-but-novel configs to test the local-optima-escape claim, and fecundity-weighted parent sampling to bias PromptForge/StructuralLab toward productive lineages — both gated on our resolution-aware/sequential-verdict machinery and single-host compute limits before any keep-all-archive change. [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md) reference-chased expansion; [intake-772](https://arxiv.org/abs/2505.22954) `adopt_patterns`

- **The self-optimizer integrity architecture shifted from mechanism-building to a guarantee question: the evidence plane went live-authority on 2026-07-02.** The event-sourced per-question ledger plus sequential e-process verdicts now run under `AUTOPILOT_SEQ_VERDICT=1` with `decision_grade_possible=true`; the W6 current-era gaming audit is clear (`gaming_alarm=false`) and the W7 game-layer hardening shipped. The acute contamination symptoms diagnosed in the 2026-06-12 Fable 5 window are, for now, quiet. The open architectural question is now narrower and deeper: whether the shipped design delivers the guarantee *by construction* — that refuted narratives cannot re-inject and the optimizer cannot game the evidence base — rather than by after-the-fact alarm (is W7 the right design or a patch to re-derive?), and whether W6 being "clear" today means *solved* or merely *re-based*. [fable5-architecture-review-2.md](../handoffs/active/fable5-architecture-review-2.md) §1.5/§2/§4A; [2026-07-02-fable5-window2-brief.md](../progress/2026-07/2026-07-02-fable5-window2-brief.md) `inferred`

- **A repeated calibration no-go poses the objective-specification question: is the instrument correctly rejecting a mis-specified objective, or is it mis-built?** The W5 `core_v2` calibration remains a "do not promote" (33/40, held since 2026-06-15, no smaller fallback `core_id`, no extra repeat planned). The instrument built to *be* the product will not certify itself — an unresolved tension between measurement discipline and objective design that the Fable 5 window-2 brief flags as the single held-open integrity question after the evidence plane went live. [fable5-architecture-review-2.md](../handoffs/active/fable5-architecture-review-2.md) §2/§6; [2026-07-02-fable5-window2-brief.md](../progress/2026-07/2026-07-02-fable5-window2-brief.md) `inferred`

- **The heterogeneous CPU+GPU serving frontier is now live: the MI210 landed 2026-07-02, framing three competing architecture families whose fork is a single still-unmeasured number.** With a CPU (1.1 TB, bandwidth-rich) plus one AMD Instinct MI210 (gfx90a, ROCm 6.2; Vulkan impossible, HIP needs an fp8 guard for ROCm<6.3, gemma4-31B+MTP has full HIP op coverage but MTP only via llama-server), the serving architecture decomposes into three families to critique: (A) dense RAM+GPU hybrid (static layer split / GPU-resident islands / grouped or dense-block streaming); (B) sparse MoE expert residency + streaming (hot-expert HBM cache, cold-miss GPU_LOAD vs. CPU_EXPERT, à la Fiddler/HybriMoE); (C) CPU-primary target + MI210 speculative sidecar (small draft model / EAGLE-3 head / native MTP). The decisive measurement that forks the whole GPU-draft program — α(drafter→target) acceptance rate — is still unmeasured; the tokenizer blocker is now understood (aligned drafter = Qwen3.5-0.8B Q8/Q4) and a retest harness is staged behind a clean-window gate. Architectural guidance is most valuable *before* pouring concrete into the GPU path. [fable5-architecture-review-2.md](../handoffs/active/fable5-architecture-review-2.md) §4B/§5; [2026-07-02-fable5-window2-brief.md](../progress/2026-07/2026-07-02-fable5-window2-brief.md) `inferred`

- **The one-shot strategic-architecture consult is itself a governed agent pattern: a full-agent GitNexus-grounded review with read-only subagents, adversarial synthesis, and standing unprompted deliverables.** The Fable 5 window-2 brief codifies a reusable review-agent contract: run as a Claude Code agent with GitNexus-first grounding (raw file reads for algorithm internals / config values), spawn parallel subagents but hold strict write authority (subagents are read-only; only the lead writes, and only to designated findings files — index restructures are *proposed* artifacts, not in-place edits, per CLAUDE.md's no-index-modification-without-approval rule), ground every claim in a query result or file with a citation, ship every falsifiable claim with the cheapest decisive experiment that would validate it, and produce two standing deliverables unprompted every run: a full index-driven portfolio audit + reprioritized queue, and a closing self-critique. This encodes lessons from the 2026-06-12 window (needed 4+ operator-requested depth passes; one "cheap" step silently blocked by a tokenizer mismatch; density hurt scannability). [fable5-architecture-review-2.md](../handoffs/active/fable5-architecture-review-2.md) §7/§8; [2026-07-02-fable5-window2-brief.md](../progress/2026-07/2026-07-02-fable5-window2-brief.md) `inferred`

**Sources**: [intake-753](https://huggingface.co/spaces/joelniklaus/harness-optimization) Don't Train the Model, Evolve the Harness · [intake-772](https://arxiv.org/abs/2505.22954) Darwin Gödel Machine · handoffs [meta-harness-optimization](../handoffs/active/meta-harness-optimization.md), [fable5-architecture-review-2](../handoffs/active/fable5-architecture-review-2.md) · progress [2026-07-02-fable5-window2-brief](../progress/2026-07/2026-07-02-fable5-window2-brief.md)

### New Findings (2026-06-25 — REPL delegation patterns audit + Fugu/Trinity/Conductor architecture)

- **Three REPL delegation patterns have distinct context policies — isolation for workers already implemented (2026-06-25).** `routing.py` audit reveals three interaction patterns with different correct context policies: (1) **Consultation** (frontdoor → architect): full context correct; implemented via escalation + IIL `consult` kind (P2 in progress); (2) **Worker execution** (frontdoor → coder): isolation already implemented in `_delegate_single` — workers see `self.context[:4000]` + brief only, NOT frontdoor scratchpad; (3) **Fan-out + synthesis** (N workers → synthesizer): `_delegate_parallel` handles homogeneous same-role fan-out (up to 4 concurrent, isolated) — synthesis done by calling model reading result list. These patterns were confirmed through a Fugu Ultra / Conductor architecture deep-dive. Source: [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md) P3.

- **Heterogeneous structured delegation chains are P3 scope (post-P2 gate) — autopilot can explore homogeneous fan-out now (2026-06-25).** The gap vs. Conductor's access_list pattern: `_delegate_parallel` dispatches to one role only; no explicit per-step context routing exists. The heterogeneous chain (coder isolated → architect sees coder output → synthesize) needs `delegate_chain(steps)` (P3, gated on P2 A/B). However, autopilot can explore the homogeneous fan-out + synthesis pattern TODAY via PromptForge mutations on `resolver.py` — teaching frontdoor to use `delegate(brief, parallel=True)` + explicit synthesis. Two strategy store entries seeded (2026-06-25) to prime this exploration. Source: [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md) P3.

- **Fugu / Trinity / Conductor architecture deep-dive: 7 mechanism insights, 2 new for EPYC (2026-06-25).** Comprehensive reading of all three Sakana AI papers (Trinity ICLR 2026 arxiv:2512.04695, Conductor ICLR 2026 arxiv:2512.04388, Fugu Technical Report arxiv:2606.21228). Five findings already covered in existing handoffs (penultimate-token probe in LRC P4.1, Verifier-ACCEPT gate in TR-4.4, sep-CMA-ES in LRC P4.4, Trinity/Conductor already in outer-coordinator). Two genuinely new: (1) **Fugu Ultra's intra-workflow isolation** (workers see only original task + designated prior outputs — orchestration collapse prevention) is already implemented in our `_delegate_single`; (2) **Conductor's access_list selective context injection** is the P3 design target for IIL. Competitive intelligence: Fugu Ultra achieves frontier-equivalent benchmarks but with real-world ~30-minute latency — confirms multi-agent orchestration has substantial overhead that single-dispatch (Fugu, Trinity lineage) avoids. Sources: intake-474, intake-493, intake-728.

### New Findings (2026-06-20 — agent-harness intake cluster: mostly-covered, three net-new deltas)

- **The only net-new primitive from Centaur (intake-696) is a placeholder-credential egress proxy — the agent process never holds live secrets.** Centaur (paradigmxyz, MIT, self-hosted "multiplayer" Slack agents) lets agents see only placeholder strings; a mitmproxy-style "iron-proxy" swaps the real secret in only on authorized outbound requests (with 1Password runtime resolution). This is a credential-hygiene design note worth recording: a prompt-injection exfiltration attempt leaks only placeholders, not live secrets. Centaur's other primitives are duplicative — its harness-adapter abstraction is already covered by HOS-Pattern-S (5-file adapter shim), its durable child-agent workflow by the A2A internal/external split and the child-agent delegation/swarm "Key Questions", and its per-conversation k3s sandbox is out-of-scope on single-host EPYC (no Kubernetes substrate). [intake-696 → [hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md) agent-harness cluster] `external`

- **eve (intake-697) carries no net-new architectural lift — it is the productized successor of vercel-labs/open-agents (intake-397).** Vercel's "Next.js for agents" framework packages durable park/resume, hierarchical subagent delegation, zero-registration tools, conditional skills, and eval-on-deploy. Every one of those patterns was already enumerated in the vercel-open-agents deep-dive and carried through the hermes-outer-shell / tool-output-compression / tool-use-eval-contract Phase 2 work. The packaging is new; the techniques are not, and they mirror EPYC's own thin-map + skills + subagent harness. [intake-697, intake-397] `external`

- **ruflo (intake-700) is a maturity datapoint, not a new mechanism; its sole net-new element (zero-trust cross-machine federation) is out-of-scope on single-host EPYC.** The ex-Claude-Flow swarm meta-harness (~60k stars) re-packages primitives EPYC already has: `strategy_store` + 4-tier ReasoningBank trajectory memory, SiliconSwarm-style cross-species sharing (Applied) and BT consensus (killed in autopilot), and pi-agent-core-style hooks. The only fresh element — zero-trust cross-machine federation (mTLS / ed25519 / PII-gating) — is out-of-scope for a single-host single-user box. Its self-published 1.3×–1953× benchmark range is vendor-reported (observations, not decision-gating per MEASUREMENT.md); note its recent CWE-78 (OS command injection) patch if its hook-shell surface is ever inspected. [intake-700] `external`

- **The OpenRouter subagent server tool (intake-705) confirms EPYC already ships its core primitive — the real remaining delta is a cost-aware capable→cheaper-worker delegation mode.** OpenRouter's `openrouter:subagent` is a provider-hosted, stateless, scoped delegation primitive (worker sees only `task_description`, no parent conversation; worker model and per-request task cap pinned at configure time). EPYC already has a server-side delegate that does this in software: `src/api/routes/chat_delegation.py` performs architect→specialist delegation with role pinning (`_valid_delegate_roles`/`_normalize_delegate_role`), per-request loop caps (`DELEGATION_MAX_SAME_TARGET`, `DELEGATION_MAX_TOTAL_TOKENS`, per-turn token caps), and a re-entrance/depth guard. The genuinely-missing feature is OpenRouter's *cost-aware delegation direction*: a capable model spending input-only tokens to hand a self-contained subtask down to a cheaper/faster worker, bounded by a per-request task-execution cap. [intake-705 → [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md) 2026-06-20 update; verified against `chat_delegation.py`] `verified`

- **The child structured-return contract is already shipped for the batched and single-delegate REPL paths.** Re-reading intake-693 (RLM schema-constrained subagent returns as an "external attention mask") against the code confirms the *parent* contract (schema-normalize → contract-at-step-0 → validate-on-`FINAL` → retry-with-errors) shipped 2026-05-20 under flag `final_schema_validation`, the *batched child* path shipped in commit `18b5ceb` ("Validate batched child LLM schemas", 2026-06-14), and the single-delegate REPL path shipped in commit `6426dd4` ("Add schema validation for single delegates", 2026-06-27). This supersedes the earlier "~30–40 LoC still-open" framing for child schemas; remaining deltas are parallel-delegation schema support only if a fan-out-heavy eval proves a gap, plus native-tools sentinel/parity and cost-aware cheaper-worker delegation. [commits `18b5ceb`/`6426dd4`, intake-693, [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md)] `verified`

**Sources**: [intake-696](https://centaur.run/) Centaur (paradigmxyz, MIT) · [intake-697](https://vercel.com/eve) eve · [intake-700](https://github.com/ruvnet/ruflo) ruflo · [intake-705](https://openrouter.ai/docs/guides/features/server-tools/subagent) OpenRouter subagent server tool · handoffs [hermes-outer-shell](../handoffs/active/hermes-outer-shell.md) (agent-harness cluster), [tool-use-eval-contract](../handoffs/active/tool-use-eval-contract.md) (intake-705 update) · epyc-orchestrator `src/api/routes/chat_delegation.py`, `src/repl_environment/combined_ops.py` (commit `18b5ceb`)

### New Findings (2026-05-31 — A2A semantics adopted internally, transport deferred)

- **The Agent2Agent (A2A) protocol's *lifecycle model* is adopt-worthy internally even though its wire transport is not.** A2A's primitives — `Message | Task`, states (working / input_required / completed / failed / cancelled), artifacts, terminal-state guarantees, Agent Card-style skill contracts — model both `delegate` and a new `consult` interaction kind cleanly. Adopting them as an internal `Interaction` abstraction over the existing delegation substrate (`_architect_delegated_answer`, `DelegationEvent`, `delegation_cache`, contention gate, DCP) gives the architectural discipline (forced context packaging, declared advisory skills per role, bounded budget, terminal advisory state) without paying for opacity that would break our cross-role region-lock visibility (`project_cross_role_contention_placement_blind`), shared-backend `topology_role` aliasing, and contention gating. External A2A wire adapter (inbound at hermes-outer-shell / outbound for cross-vendor consult) remains deferred. [intake-655 → handoff [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md)] `adopt_patterns (narrow)`

- **Consultation is a distinct interaction shape from delegation and deserves a first-class primitive.** Delegation = callee finishes & returns; consult = caller integrates advice & finishes itself; bounded sub-question vs whole-task; often multi-turn vs one-shot; pays input-only tokens vs full callee inference. Today this pattern (e.g., a coder role drafts → `architect_general` reviews → coder finalizes) gets kludged as full delegation we under-utilize. The new four-phase plan adds a typed-output `consult()` entrypoint with skill registry, `kind="consult"` namespacing on `delegation_cache.make_key()` additively, scheduler-policy default to `priority=background` + `max_queue_wait_ms=0` (skip-or-admit semantics verified native in `epyc-orchestrator/src/scheduling/contention_gate.py:346-399` — the `is None` check at `:366` does NOT catch `0`, so the loop runs one `evaluate()` then admits-or-times-out with `waited_s ≈ 0`), and `ConsultationDenied` internal exception (no HTTP/503 mapping in v1). First consult site = code-edit drafting requester → `architect_general` `review_before_commit`, with the exact attach point gated on a P2-0 discovery subtask (candidates: `force_mode="edit"`, batched-edit pipeline, REPL final-answer hook, `worker_coder`, `coder_escalation`). [internal-interaction-lifecycle.md P2] `planning`

**Sources**: [intake-655](https://github.com/a2aproject/A2A) A2A Protocol v1.0.1 LF · [intake-318] Agentnetes (uses A2A Agent Card) · [intake-394] Evolver (uses A2A hub) · [intake-145] Agent Protocol (alternative interop standard) · handoffs [internal-interaction-lifecycle](../handoffs/active/internal-interaction-lifecycle.md) · [hermes-outer-shell](../handoffs/active/hermes-outer-shell.md) Path-A external exposure · [delegation-context-preassembly](../handoffs/active/delegation-context-preassembly.md) (DCP-4 reused for P2 consult context packaging)

### New Findings (2026-05-27 - edit-transaction protocol fix)

- **The multi-file coding failure was an agentic protocol failure, not a model capability failure.** The deployed `coder_escalation` role (`Qwen3.6-35B-A3B Q8`) solved the exact five BEP scratch coding tasks **5/5** in a single direct prompt with full file contents and the same verifiers, including every read-first task that failed the REPL/BEP read→peek→edit→FINAL loop. The remediation is therefore an interaction-contract change, not a model swap: a first-class `force_mode="edit"` path asks once for complete file replacements and applies them transactionally. [multi-file-coding-completion-capability.md](../handoffs/active/multi-file-coding-completion-capability.md) `verified`

- **For routine file edits, one-shot full-file edit transactions are the safe alternative to free-form tool choreography.** The shipped edit path is default-off and requires both `ORCHESTRATOR_EDIT_TRANSACTION=1` and a scoped `ORCHESTRATOR_EDIT_ROOT`; explicit `force_mode="edit"` fails closed with HTTP 412 if either precondition is missing. The transaction preserves nested paths, rejects absolute/escape paths all-or-nothing, bounds unscoped context at 50 files / 400 KB via `stat()` before reading, syntax-checks with `compile()` to avoid `__pycache__` side effects, rolls back on failure, and auto-finalizes in one turn. Validation: 21 edit/cc-role unit tests, module 5/5 through the real coder, live server 3/3, plus 55 chat route/endpoint/canary tests. [multi-file-coding-completion-capability.md](../handoffs/active/multi-file-coding-completion-capability.md) `verified`

- **BEP-2's practical remediation is no longer the Repo Prompt-style batch-vs-interleaved A/B.** The edit transaction is a third path that bypasses both the legacy REPL loop and the older batch-edit proposal, so Package J now treats J8 as an optional decision experiment: run it only if the answer would change whether `batch_edit_mode` is kept, retired, or scoped to large-repo/provenance/task-class cases. DCP-6 is likewise no longer blocked by the BEP read-loop; DCP-4 advisory attach is already wired/default-off, and only the DCP-6 replay/eval remains. [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md), [batched-edit-parallel-apply.md](../handoffs/active/batched-edit-parallel-apply.md), [delegation-context-preassembly.md](../handoffs/active/delegation-context-preassembly.md), [progress/2026-05-27](../progress/2026-05/2026-05-27.md) `verified`

### New Findings (2026-04-26 — Trinity deep-dive)

- **The lightweight-learned-coordinator-over-heterogeneous-pool thesis has direct prior art in Trinity (intake-474, ICLR 2026, Sakana AI).** Trinity is a 0.6B SLM (Qwen3-0.6B) + 10K-parameter linear head, trained with sep-CMA-ES against terminal binary task fitness, that picks `(LLM, role)` per turn from a pool of 7 LLMs and 3 roles {Thinker, Worker, Verifier}; multi-turn protocol up to K=5 with Verifier-acceptance termination. Achieves 86.2% on LiveCodeBench v6 and 21.9% mean relative-error reduction over the 2nd-best multi-agent baseline. Trinity is core to Sakana's commercial Sakana-Fugu product — open code release is unlikely. **Standing comparative context** for all EPYC orchestrator and routing work: even where our final architecture differs, Trinity attempts to build around the same thesis we are building around. Deep-dive: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md). Spawned new handoffs [`tri-role-coordinator-architecture.md`](../handoffs/active/tri-role-coordinator-architecture.md) and [`outer-coordinator-learned-head.md`](../handoffs/active/outer-coordinator-learned-head.md), plus tasks across `learned-routing-controller.md` Phase 4 + `decision-aware-routing.md` DAR-1.5 + `routing-and-optimization-index.md` P19. [intake-474, deep-dive] `verified`

- **Per-call role assignment (Thinker / Worker / Verifier) is an architectural axis orthogonal to model selection — and currently absent from our orchestrator.** Trinity's ablation evidence: removing the tri-role decomposition costs −5 to −8 points across all four benchmarks (LCB / Math500 / MMLU / RLPR); removing Thinker alone costs −6.0 on Math500 and −4.57 on RLPR. The tri-role lever is the second-largest empirical effect in the paper after feature-position. Our orchestrator collapses every dispatch to model-selection only; review/escalation lives at the pipeline layer outside the routing policy. Roles in our system today (`frontdoor`, `architect_general`, `coder`, `reviewer`, `worker`) are *attached to models* — a model permanently has a role. Trinity's insight is that role is a *per-turn property of the dispatch*, not of the model: the same Qwen-3-32B can be Thinker on turn 1, Worker on turn 3, Verifier on turn 5. New handoff `tri-role-coordinator-architecture.md` (TR-1..TR-5) isolates this architectural change so it can ship under any optimizer choice. [intake-474, tri-role-coordinator-architecture.md] `verified`

- **Pool-homogeneity caveat is layer-specific — the outer Claude-driven coordination layer is the closer Trinity match than the inner inference pool.** First-pass deep-dive analysis flagged that Trinity's 21.9% mean error reduction comes from a heterogeneous 7-LLM pool with massive quality variance (GPT-5 vs Gemma-3-27B), and our open-source-only inner inference pool is structurally narrower. User observation revised this: at the *outer coordination layer* (Claude Code, autopilot), Claude vs cheap-frontdoor vs specialist-coder is a wider quality gradient than the inner pool — closer to Trinity's regime. The deep-dive's revised reading is that *the outer layer is the closer Trinity analogue*, which led to a separate scoping handoff [`outer-coordinator-learned-head.md`](../handoffs/active/outer-coordinator-learned-head.md). Phase OC-0 (scoping document only) is gated until tri-role + DAR + LRC Phase 4 land. [intake-474, deep-dive section 2.3] `verified`

### New Findings (2026-04-26 — pi-agent-core deep-dive)

- **pi-agent-core (intake-473) factors agent-runtime primitives more crisply than any other open-source TS framework surveyed.** Source-level review of `@mariozechner/pi-agent-core` (`badlogic/pi-mono/packages/agent`, 1,966 LOC src + 2,048 LOC tests, 80+ contributors, ~70 versions, **Armin Ronacher top-5**) identified five named primitives worth lifting into the EPYC orchestrator's vocabulary even before any code port: (1) **two-stage message pipeline** — `transformContext` runs every turn at the agent-message level (custom types in scope), `convertToLlm` filters and shapes into the LLM-strict `user|assistant|toolResult` payload; (2) **`beforeToolCall` / `afterToolCall` hooks** with field-replace-only semantics and per-call throw-isolation (a throw in `afterToolCall` becomes an error result for *that* tool, parallel batch continues, per CHANGELOG #3084); (3) **steering vs follow-up split** as two named queues with `one-at-a-time` (default backpressure) vs `all` (drain-everything) drain modes — exactly the "user typed mid-response" vs "user typed after response" distinction `repl-turn-efficiency` lacked vocabulary for; (4) **per-tool `executionMode` override** with batch-falls-back-to-sequential rule for mixing exclusive-access tools with concurrent ones; (5) **terminate-unanimous-batch** rule (early stop only fires when *every* tool result in the batch sets `terminate: true`) for clean early-exit semantics. The framework explicitly excludes built-in tools, memory tier, plan mode, and MCP — positioned as a *runtime layer* below a coding-agent harness. [pi-agent-core-stateful-ts-runtime.md, intake-473] `verified`

- **Initial intake-473 credibility/novelty/relevance scores were materially wrong from a README-only read.** Lesson: scoring credibility from README alone produced a 4-axis mis-estimate (credibility=null, novelty=low, relevance=low, "single-author indie") that source review revised to credibility=3, novelty=medium, relevance=medium, verdict=adopt_patterns. The README listed only Mario Zechner; `git shortlog` revealed 80+ contributors with 2,957 / 66 / 55 / 51 / 44 commits at the head of the distribution — the second-place is Helmut Januschka, third is Armin Ronacher (Flask, Sentry CTO). Captured as feedback memory `feedback_credibility_from_source_not_readme.md` — minimum credibility-scoring checks now require `git shortlog`, commit count, version cadence, CHANGELOG style, and test/source ratio before assigning the score for non-trivial repo entries. `verified`

- **EPYC's existing handoff vocabulary maps cleanly onto pi-agent-core's named primitives.** Cross-cutting integration into 6 active handoffs identified the existing pattern in each: `hermes-outer-shell` already needs the `streamFn` injection point + two-stage message pipeline (drop-in candidate for Package E streaming); `meta-harness-optimization`'s code-mutation safety gates would compose more cleanly as `beforeToolCall`/`afterToolCall` middleware than the current inlined `dispatch_action()` checks; `repl-turn-efficiency`'s S3 contextual-suggestions feature flag is the same problem as the queue-mode switch but as an unnamed flag rather than a first-class API knob; `tool-output-compression`'s Phase 3d.4 "compressor 503/404 → main model" fallback story benefits directly from `afterToolCall`'s throw-isolation; `context-folding-progressive`'s fold-decision logic should factor onto the agent-message-level `transformContext` step rather than mixing with LLM-payload shaping. Naming + factoring lift, not a code port. [hermes-outer-shell.md, meta-harness-optimization.md, repl-turn-efficiency.md, tool-output-compression.md, context-folding-progressive.md, hermes-agent-index.md — all 2026-04-26 updates] `external`

### New Findings (2026-04-21)

- **Memory Transfer Learning validates insight-level abstraction over trace-level memory.** MTL (arxiv:2604.14004, intake-425) empirically shows cross-domain memory transfer improves coding agent performance by +3.7% on average across 6 benchmarks, but only when memories use the "Insight" abstraction (title + description + generalizable content, no task-specific details). Concrete traces induce negative transfer due to specificity. Simple embedding retrieval (cosine on `text-embedding-3-small`) outperforms LLM reranking — validating our FAISS-based `strategy_store` approach. A 431-memory MTL set outperforms AgentKB's 5,899 memories by +1.7%, reinforcing that curated abstraction beats raw accumulation. The negative-transfer taxonomy (domain-mismatched anchoring, false validation confidence, misapplied best-practice transfer) is directly actionable for PromptForge mutation safety gates. Caveat (intake-426 follow-up): "Memory Transplants" ICLR 2026 Workshop finds architecture transfer is system-dependent and weaker solvers benefit most — the 3.7% gain may not hold for stronger models. [autopilot-continuous-optimization.md 2026-04-21 update, meta-harness-optimization.md 2026-04-21 update] `verified`

- **Claude Code design study is the strongest external validation of the meta-harness optimization thesis.** "Dive into Claude Code" (arxiv:2604.14228, intake-426) documents that 98.4% of agent complexity lives in operational infrastructure (permissions, context management, tool routing), not AI decision logic. This independently confirms the meta-harness-optimization handoff's core bet: harness engineering is the primary locus of agent capability improvement, not raw model capability. The paper's five-layer compaction pipeline (budget reduction → snip → microcompact → context collapse → auto-compact) is a concrete taxonomy for auditing coverage gaps against EPYC's L1-L5 compression tiers. Other extractable patterns: seven-mode permission system with ML-based safety classifier (93% approval rate, 40% auto-approve by 750 sessions); append-only JSONL session storage with sidechain files; the "observability-evaluation gap" framing (agents produce outputs but evaluating them is hard) identified as an open design direction. Caveat from Anthropic's own harness blog: "context anxiety" in Sonnet 4.5 made compaction alone insufficient — compaction silently discards provenance and context resets are sometimes needed. [meta-harness-optimization.md 2026-04-21 update, context-folding-progressive.md 2026-04-21 update] `external`

- **Claude Code 98.4% infrastructure / 1.6% AI logic is the strongest external validation of the meta-harness thesis.** The "Dive into Claude Code" analysis (arxiv:2604.14228, intake-426) quantifies that 98.4% of Claude Code's complexity is operational infrastructure (permissions, context management, tool routing) and only 1.6% is AI decision logic. This independently confirms the meta-harness-optimization handoff's core bet and the "Mismanaged Geniuses" hypothesis: harness engineering is the primary locus of agent capability improvement. [intake-426]

- **13 design principles mapped from 5 human values provide a principled design framework.** Claude Code traces implementation choices to 5 human values through 13 intermediate design principles. "Context as scarce resource" and "Minimal scaffolding, maximal harness" align directly with EPYC's architecture -- the orchestrator is a thin routing/escalation layer around heavy infrastructure (5-layer context management, 9 routing subsystems, 43+ feature flags). The comparison with OpenClaw shows deployment context (local CLI vs cloud IDE) drives architectural divergence from shared principles. [intake-426]

- **Memory Transfer Learning: insight-format design and a negative-transfer taxonomy inform PromptForge safety gates.** MTL (arxiv:2604.14004, intake-425) motivates retaining title, description, and generalized-content fields, while its three failure modes -- domain-mismatched anchoring, false validation confidence, and misapplied best-practice transfer -- remain directly actionable for PromptForge. Its reported transfer numbers are external observations, not EPYC measurements or a justification for strategy-store write-path policy. [intake-425]

### New Findings (2026-04-19)

- **Qwen-Agent's MCP singleton manager pattern fills an identified gap in EPYC tool extensibility.** Qwen-Agent (QwenLM/Qwen-Agent, intake-411) implements an `MCPManager` singleton managing MCP server connections in a background async event loop on a dedicated thread, with dynamic `BaseTool` subclass generation per discovered MCP tool, ping+auto-reconnect health checks, and atexit cleanup. The pattern gives MCP tools the same interface as native tools -- the agent loop does not distinguish between native and MCP-backed tools. This is the cleanest MCP integration pattern surveyed and directly applicable to our `tool_registry.py`. Implementation would create `src/tools/mcp_manager.py` (~200 LoC), register MCP tools alongside native tools, and gate access via `tool_policy.py`. Not urgent (current tool ecosystem is sufficient) but becomes relevant for MemPalace MCP (H-8) or other MCP-based tools. Updated verdict: `adopt_patterns`. [qwen-agent-framework-deep-dive.md](../research/deep-dives/qwen-agent-framework-deep-dive.md) `verified`

- **DeepPlanning benchmark provides the strongest empirical evidence for reasoning-mode routing.** DeepPlanning (arXiv:2601.18137, intake-412) is a 240-task planning benchmark with fully deterministic rule-based scoring across 26 models. The reasoning vs non-reasoning gap is the largest documented in the literature: GPT-5.2 gains +40.1pp overall (4.5% to 44.6%) and +34.6pp on travel case accuracy. Critically, reasoning mode achieves higher accuracy with *fewer* tool calls and *fewer* turns (Claude-4.5-Opus: 12.5 vs 16.9 turns, 72.9 vs 79.5 tool calls). The benchmark demonstrates that planning tasks benefit from reasoning far more than typical QA benchmarks -- adding a planning-complexity signal to the Category A classifier would improve routing decisions. The multi-granularity scoring architecture (8-dimension commonsense / composite / case-level binary) catches failure modes that single-metric scoring misses entirely: models scoring 85 composite can have 0% case accuracy. [deepplanning-agent-benchmark.md](../research/deep-dives/deepplanning-agent-benchmark.md) `external`

- **DeepPlanning's error taxonomy validates investment in global optimization over local reasoning.** Analysis of 140 failed trajectories shows global optimization failures dominate (101/80 travel, 52/60 shopping) -- agents gather correct information and satisfy local constraints but fail at maintaining global coherence (temporal overlaps, logical discontinuities between days, suboptimal combinatorial choices). This is the frontier capability separating 35% case accuracy from 0%. Implicit constraint failures (B2) are more common than explicit ones (B1), meaning models are better at following stated requirements than inferring unstated real-world constraints. [deepplanning-agent-benchmark.md](../research/deep-dives/deepplanning-agent-benchmark.md) `external`

### Findings (2026-04-17)

- **Observer-sidecar pattern: clean separation without context pollution.** claude-mem (intake-395) implements a tool-disabled LLM subprocess running alongside the primary session in an isolated cwd and sanitized env. It captures every PostToolUse event and emits structured XML `<observation>` records without any tool access of its own. The primary session never sees compaction work; the observer never sees user context. This is architecturally distinct from EPYC's current in-session compaction (which mutates the main session's summary). The sidecar doubles per-tool inference cost, so local adoption should pair it with a cheap local model as observer. AGPL-3.0 license blocks code vendoring; re-implement patterns in Python. [claude-mem-persistent-memory.md](../research/deep-dives/claude-mem-persistent-memory.md) `inferred`

- **Five sub-patterns from claude-mem are directly adoptable for in-flight handoffs.** (A) Observer-sidecar with env isolation and tool sandbox. (B) Mode-defined observation taxonomy in YAML rather than code-coupled enums — applies to `research/taxonomy.yaml`. (C) Batched-ID fetch MCP tool (`get_observations(ids=[...])`) that enforces filter-before-fetch at the schema level, not just in prompt instructions. (D) `<private>` tag with edge-layer stripping (ReDoS-guarded, applied to tool_input/output and user prompt) for user-controlled compaction exclusion. (E) Six-field `<summary>` schema on Stop hook (`request/investigated/learned/completed/next_steps/notes`) as an A/B candidate for Tier-2 consolidation. The 10x token-savings claim is an arithmetic ratio of description/detail sizes, not a measured end-to-end result; the "biomimetic" label for Endless Mode is marketing. [claude-mem-persistent-memory.md](../research/deep-dives/claude-mem-persistent-memory.md) `verified`

- **The L1 insight-index pattern (≤30 lines, always-in-context) is the highest-leverage pattern from GenericAgent for any memory-using agent.** GenericAgent (lsdefine/GenericAgent, intake-399) uses a hard-capped `global_mem_insight.txt` (≤30 lines by SOP rule) that is injected into every turn's system prompt. The file contains only keyword→filename pointers for L2/L3 memory files. This keeps the always-present memory overhead constant and minimal while still giving the LLM a lookup index. Promotion is entirely LLM-driven via `start_long_term_update`, which returns the memory SOP and instructs the LLM to `file_patch` appropriate tiers — no heuristic fires automatically. The "100-line loop / 9 atomic tools" headline is accounting framing; the honest core is ~2K LoC of Python. [genericagent-minimal-framework.md](../research/deep-dives/genericagent-minimal-framework.md) `verified`

- **Four additional GenericAgent patterns are worth borrowing for EPYC harness design.** (1) Content-in-reply-body for verbose tool outputs: `file_write` and `web_execute_js` script bodies go in the LLM's reply as markdown, not in tool-call JSON — keeps tool-arg payloads compact. (2) `no_tool` recovery handler: catches empty response, max-tokens truncation, and large-code-block-without-tool-call cases at the engine level, reducing silent turn waste. (3) Generator-based tool dispatch (`try_call_generator` + `yield from`) unifies streaming output and structured return without two code paths. (4) L4 session archiver: 12-hour cron compresses raw session logs into monthly zips with deduplication against an `all_histories.txt` roll-up. The remote `skill_search` service (Fudan University host) and unsandboxed `code_run` are not portable to EPYC. [genericagent-minimal-framework.md](../research/deep-dives/genericagent-minimal-framework.md) `verified`

- **The workflow event log (not Vercel's cloud runtime) is the portable durability primitive from open-agents.** vercel-labs/open-agents (intake-397) uses a Workflow SDK backed by a persistent event log: each step's `(step_id, input_hash, output)` is committed before the workflow proceeds. On reconnect, replay replays only the event log — tools already executed are not re-run. The key insight for EPYC: a SQLite WAL of `(run_id, step_id, args_hash) → output` tuples is approximately 200 lines of Python and directly addresses the reconnection-waste concern in `repl-turn-efficiency.md`. The "snapshot-based hibernate" framing at intake overstated what Vercel does — Vercel Sandbox snapshots are filesystem-only (no memory, no processes); E2B does real Firecracker memory+process hibernate but open-agents does not use it. CRIU is too fragile for Python processes holding HTTP sockets to llama-server. [vercel-open-agents-durable-workflow.md](../research/deep-dives/vercel-open-agents-durable-workflow.md) `verified`

- **The typed sandbox contract (explicit interface between LLM loop and execution environment) is directly applicable to the REPL.** open-agents' `Sandbox` interface (`exec/execDetached/readFile/writeFile`) decouples the agent from the execution backend. The current EPYC REPL lives inside the orchestrator process with no explicit `ExecutionEnvironment` protocol. Extracting one would make REPL backend swaps (in-process, subprocess-isolated, Docker, remote) one-adapter changes rather than cross-cutting edits. The `task(subagentType, task, instructions)` scoped-subagent pattern — where only a summary returns to the parent, internal tool calls isolated — is tighter than the current `_escalate()` signal and worth mirroring. The large-output-to-FS convention (`{ status, content_type, byte_count, file_path }`) from issue #781 generalizes across `web_fetch`, `web_search`, and `peek`. [vercel-open-agents-durable-workflow.md](../research/deep-dives/vercel-open-agents-durable-workflow.md) `verified`

- **The Gene-record schema from EvoMap/evolver is a governance upgrade for PromptForge mutation strategies.** Evolver (intake-394, GPL-3.0) ships a Gene record with 7 fields: `id, category (repair/optimize/innovate), signals_match[], preconditions[], strategy[], constraints (max_files, forbidden_paths[]), validation[]`. PromptForge's current `MUTATION_TYPES` is a flat string list at `prompt_forge.py:37`. Replacing it with a YAML Gene catalog adds per-strategy forbidden-path deny-lists, signal-matching semantics, and validation shell commands — roughly one day of work. Two additional patterns: (1) intent-mix presets (balanced/innovate/harden/repair weights for mutation-type sampling) that extend the existing species-budget rebalancing; (2) EvolutionEvent log field alignment (`intent, gene_id, parent_event_id, blast_radius, validation_result`) for `experiment_journal.jsonl`. Evolver's algorithmic core (signal-extraction + template-prompt + validate) is strictly below PromptForge+GEPA. Do not adopt the Hub, A2A protocol, skillPublisher, or `.integrity`/`shield.js`/`deviceId.js` layers. GPL-3.0 and partially obfuscated code prevent vendoring. [evomap-evolver-gep-protocol.md](../research/deep-dives/evomap-evolver-gep-protocol.md) `verified`

- **EvoMap's public dispute with Nous/Hermes has no technical merit but creates reputational coupling risk.** EvoMap accused Hermes Agent of architectural copying (Apr 2026). Nous/Teknium rebutted with timeline evidence (Hermes predates Evolver by 6 months) and noted that Hermes uses GEPA (ICLR 2026 Oral, unrelated to GEP). The allegation is undone by the GEP-vs-GEPA confusion. EPYC's adoption of Gene-schema ideas only (not the Hub or runtime) avoids any reputational coupling. [evomap-evolver-gep-protocol.md](../research/deep-dives/evomap-evolver-gep-protocol.md) `external`

- **A cross-cutting pattern across all four deep dives: progressive disclosure with enforced filter-before-fetch.** claude-mem's `search → timeline → get_observations(ids=[...])`, GenericAgent's L1 keyword index before L2/L3 file reads, open-agents' compact tool-result summary before full payload read via `readFile`, and Evolver's signal-match before gene selection all implement the same discipline: expose a cheap index first, force an explicit narrowing step, then allow full-detail retrieval by ID/path. None of these systems implement this as a hard enforcement at the storage layer (all are convention-based), but the pattern is consistent enough that EPYC should standardize it as a naming convention: `peek_*` for index queries, `get_*` for detail fetch by ID. [claude-mem-persistent-memory.md, genericagent-minimal-framework.md, vercel-open-agents-durable-workflow.md, evomap-evolver-gep-protocol.md](../research/deep-dives/) `inferred`

### Prior Findings

- **Cost governance is the largest identified gap.** Paperclip's three-tier model (visibility via real-time dashboards, soft alerts at configurable thresholds, hard ceiling with atomic auto-pause when `spentMonthlyCents >= budgetMonthlyCents`) is directly adoptable. Cost events track provider, model, input/output tokens, cost in cents, and full goal ancestry for attribution. The orchestrator currently tracks token usage but has no budget enforcement, no per-request cost attribution, and no auto-throttle. For CPU inference, cost maps to wall-clock compute time per NUMA node rather than API billing, so per-role time budgets may be more appropriate than per-token budgets. [agent-architectures-paperclip-agentrxiv.md](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md)

- **LangGraph's checkpoint granularity enables time-travel debugging that our resume_tokens cannot match.** Our system captures ~10 fields in <500 bytes at resume points; LangGraph checkpoints full state at every node transition with pluggable backends (Postgres, Redis, in-memory). If a worker produces bad output at turn 3 that cascades to a coder failure at turn 7, we cannot replay from turn 3 with a different approach. The incremental recommendation: log TaskState snapshots at each node transition (~50 lines in persistence.py) for post-hoc debugging without full migration. [langgraph-ecosystem-comparison.md](../research/deep-dives/langgraph-ecosystem-comparison.md)

- **The orchestrator's domain-specific features are substantially more sophisticated than any surveyed framework.** LangGraph offers basic message trimming and manual lambda routing; Paperclip has no context management or learned routing; AgentRxiv operates on fixed-format LaTeX with no quality control. EPYC's 5-layer context management, MemRL learned routing, error taxonomy with 3-tier escalation ladder, think-harder ROI regulation, and 43+ feature flags with live toggle represent production-hardened capabilities that no framework provides out of the box. [langgraph-ecosystem-comparison.md](../research/deep-dives/langgraph-ecosystem-comparison.md)

- **OpenGauss's tool-pair sanitization solves a critical context compression bug.** When context is compressed, orphaned tool calls (call without result) or orphaned tool results (result without call) cause API rejections and can break downstream processing. OpenGauss's `_sanitize_tool_pairs()` pattern -- stub results for orphaned calls, removal of orphaned results -- with protected-zone parameters (first 3 + last 4 turns preserved, 50% trigger, ~2500 token summary target) is directly portable to session_log.py. [opengauss-architecture-analysis.md](../research/deep-dives/opengauss-architecture-analysis.md)

- **Paperclip's request depth tracking prevents infinite escalation loops.** A simple integer `requestDepth` counter on issues tracks delegation hops. When Agent A creates a task for Agent B, depth increments. This is trivially adoptable as an `escalation_depth` field on EscalationContext (~2 hours). Our escalation chain currently has no depth counter. [agent-architectures-paperclip-agentrxiv.md](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md)

- **Meta-harness optimization shows execution trace feedback provides +15 points over score-only feedback** for automated harness optimization (34.6% median accuracy with scores only, 50.0% with full filesystem access to traces). This is implemented as Tier 1 in the autopilot: inference_tap.log traces are fed back to PromptForge's mutation step. Tier 2 extends the search space to Python orchestration code (not just prompt templates), with an allowlist of 4 mutable files and ast.parse() syntax validation. [intake-244, meta-harness-optimization.md handoff]

- **Plaintext `inference_tap.log` is not safe for per-request correlation; the structured `inference_tap_events.jsonl` stream is.** The TapWriter (`src/runtime/inference_tap.py`) writes header / prompt / chunks / timings under separate per-append locks, so concurrent requests can interleave into syntactically-valid but cross-contaminated sections (observed 2026-05-30: `chat-83123001` routed to frontdoor displayed as `role=worker_explore` with another task's response after substring-based plaintext fallback). The structured JSONL stream is fcntl-locked and keyed by `request_id` + `task_id`, and is the correct source for any consumer that needs deterministic prompt↔response pairing. Eval scoring is unaffected because `seeding_eval._build_role_result` scores `resp["answer"]` from the orchestrator HTTP JSON, not the tap log — but residual consumers (PromptForge `last_traces`, Claude debugger byte-range inlines, `scripts/analysis/mine_repl_patterns.py`) still read raw plaintext and should migrate. [progress/2026-05/2026-05-30.md, epyc-orchestrator `7e9e441`]

- **Reasoning chain compression is an active research front with direct CPU inference applicability.** FlowSteer (intake-126) uses nonlinear activation steering to transform verbose reasoning into concise chains with input-dependent control enabling per-request reasoning budget allocation. S3-CoT (intake-125) uses self-sampled succinct reasoning via activation steering with no teacher model required. Both address the fundamental tension on CPU inference: thorough reasoning burns scarce tokens in constrained 8K-32K context windows. [intake-125, intake-126]

- **REPL tool invocations hurt accuracy on 7/10 evaluation suites** (the "Omega problem"). Direct mode outperforms REPL on agentic (-54pp), coder (-44pp), and general (-26pp) suites. Only hotpotqa (+12pp) and gpqa (+6pp) benefit from tool use. This motivates both prompt-side fixes (tighter tool-use policy) and structural fixes (frecency discovery, combined operations, contextual suggestions) to make each tool invocation more valuable. [repl-turn-efficiency.md handoff]

- **CoT reasoning expands factual recall but introduces hallucination risks.** Two mechanisms drive recall improvement: computational buffer (extra forward passes) and factual priming (semantic associations). However, generative self-retrieval creates fabricated intermediate facts that propagate through the reasoning chain. This informs the factual-risk scorer design: high-risk factual queries should route to larger models with better parametric knowledge. [intake-103](https://arxiv.org/abs/2603.09906)

- **Agentic Critical Training (ACT) shows RL-based self-reflection outperforms imitation by +5.07 points** and transfers across model sizes (4B trained with 8B trajectories reaches 92.14% on ALFWorld). ACT also improves general reasoning (MATH-500 87.73%) without reasoning-specific training data. This validates the autopilot's approach of using GRPO-based training for routing model improvement. [intake-106](https://arxiv.org/abs/2603.08706)

- **Agent context files can hurt performance.** ETH Zurich research (intake-272) found context files reduce task success rates and increase inference cost by 20%+. The thin-map architecture used by EPYC's agent files may be near-optimal, but requires empirical validation via instruction token budget tracking (AP-16). [intake-272](https://arxiv.org/abs/2602.11988)

- **Harness engineering, not model capability, is the primary performance differentiator.** The "Skill Issue" practitioner study (intake-271) showed ~28 rank positions on TerminalBench-2 from harness changes alone on the same Opus model. The "Mismanaged Geniuses" hypothesis (intake-312) extends this: frontier LLMs are already superhuman on hardest exams (IMO, IOI), and the bottleneck is orchestration, not model power. A 4B RLM achieved 100% on MRCRv2 via composition. [intake-271, intake-312]

## 2026-06-15 Update — Edit Transactions Beat Tool Choreography

- **One-shot edit transactions are now the practical fix for multi-file coding.** The BEP-2 follow-up showed that the deployed coder role solved the scratch tasks directly when asked for full-file replacements, so the old read→peek→edit→FINAL REPL choreography is no longer the blocker; it is now an optional decision experiment. Sources: [multi-file-coding-completion-capability.md](../handoffs/active/multi-file-coding-completion-capability.md), [batched-edit-parallel-apply.md](../handoffs/active/batched-edit-parallel-apply.md), [tool-use-eval-contract.md](../handoffs/active/tool-use-eval-contract.md).
- **The agent stack is moving toward explicit interaction kinds rather than looser prompt discipline.** The security-review skill scaffold, along with the edit-transaction path, shows the direction of travel: bounded tool surfaces, explicit contracts, and reviewable outputs instead of open-ended tool choreography. Source: [security-review-skill.md](../handoffs/active/security-review-skill.md).
- **The same pattern applies to broader delegation surfaces.** The architectural lesson is to treat complex interactions as typed primitives first and only then choose the transport or UI, because the hidden cost is usually in the protocol, not the model. Source: [hermes-agent-index.md](../handoffs/active/hermes-agent-index.md).

## Actionable for EPYC

### High Priority
1. **Add cost event logging to the inference path** -- per-role/per-request cost tracking with configurable monthly budgets per model tier. Auto-degrade to cheaper model rather than hard-stop when budget exceeded. Effort: ~2 days. Source: Paperclip cost governance model.
2. **Port tool-pair sanitization** from OpenGauss's `context_compressor.py` into session_log.py. Critical for context compression reliability. Effort: ~4 hours.
3. **Continue AR-3 autopilot run** with GEPA integration, short-term memory, and self-criticism loop. All infrastructure is implemented and verified. State at trial_counter=46.
4. **Upgrade PromptForge mutation strategy catalog to Gene-record YAML schema** -- replace flat `MUTATION_TYPES` list (`prompt_forge.py:37`) with per-strategy records adding `signals_match`, `preconditions`, `constraints.forbidden_paths`, and `validation` fields. Effort: ~1 day. Source: EvoMap/evolver Gene schema.
5. **Add `<private>` tag stripping to session compaction** -- strip `<private>...</private>` blocks before persisting to session log and before feeding to Tier-2 summarizer. ~30 lines in Python. Pair with `context-folding-progressive.md` Phase 2d forgetting-policy work. Source: claude-mem.

### Medium Priority
6. **Add escalation depth counter** to EscalationContext -- increment on each escalation, hard cap at configurable max (e.g., 3). Effort: ~2 hours.
7. **Thread request_id through all cost events** for per-request cost attribution. Effort: ~4 hours.
8. **Instruction token budget tracking** (AP-16) -- count tokens in all loaded .md templates, alert if ratio > 20%. Prerequisite for structural pruning experiments.
9. **State history snapshots at node transitions** for post-hoc debugging (~50 lines in persistence.py).
10. **Address the Omega problem** -- REPL turns hurting accuracy on 7/10 suites requires both prompt-side (tighter tool policy) and structural (frecency, combined ops) interventions.
11. **Implement SQLite-backed workflow event log for REPL turn reconnection** -- `(run_id, step_id, args_hash) → output` WAL (~200 lines Python), wrap REPL tool calls, replay on reconnect. Directly addresses wasted-turn-on-reconnect in `repl-turn-efficiency.md`. Source: open-agents/Vercel Workflow SDK pattern.
12. **Extract `ExecutionEnvironment` protocol from `repl_environment/`** -- explicit typed interface (`exec, read_file, write_file, grep, code_search, list_dir, peek, web_fetch`) decouples LLM loop from execution backend. Makes REPL backend swaps one-adapter changes. Source: open-agents Sandbox interface.
13. **Standardize L1-style insight index for any memory-using agent** -- hard-cap an always-injected index file at ≤30 lines with keyword→filename pointers. Prevents always-present memory overhead from growing unboundedly. Source: GenericAgent L1 pattern.
14. **A/B test six-field `<summary>` schema for Tier-2 consolidation** -- compare current freeform Tier-2 against the `request/investigated/learned/completed/next_steps/notes` schema from claude-mem on retention@compression metric. Add as Phase 2a candidate in `context-folding-progressive.md`.
15. **Add `no_tool` recovery handler at engine level** -- catch empty response, max-tokens truncation, and large-code-block-without-tool-call at harness level rather than relying on model self-correction. Source: GenericAgent `do_no_tool`.
16. **Add per-strategy intent-mix preset to PromptForge** -- `balanced/innovate/harden/repair` presets that bias mutation-type sampling distribution per session, extending existing species-budget rebalancing. Source: EvoMap evolver strategy presets.

### Deferred
17. **LangGraph migration assessment** -- strongest argument is subgraph composition for heterogeneous agent types, but migration cost is high. Recommended: hybrid approach, building new capabilities as LangGraph subgraphs alongside existing graph.
18. **Approval gates before production deployment** -- adopt Paperclip's board approval pattern for autopilot configuration changes affecting live traffic.
19. **Agent Protocol / ACP naming alignment** -- align API naming with Runs/Threads/Store standard for future interop. ACP (OpenGauss) extends Agent Protocol with session forking and structured callbacks.
20. **Multi-backend abstraction** -- OpenGauss's `ManagedWorkflowSpec` pattern shows how to abstract over multiple backends (llama-server, vLLM, TGI) with per-backend config generation.
21. **Scoped subagent contract mirroring open-agents `task` tool** -- typed `(subagentType, task, instructions)` with enforced summary-only return to parent. Tighter than current `_escalate()` string-based delegation.
22. **Mode-defined observation taxonomy for research/taxonomy.yaml** -- make observation-type categories YAML-configurable per project/session rather than code-coupled, following claude-mem's `plugin/modes/*.json` pattern.

## Open Questions

- Should the orchestrator migrate to LangGraph or evolve pydantic_graph incrementally? The subgraph composition argument is strong, but 180+ state fields, 120+ tests, and deep domain-specific features create migration risk. The recommended path is hybrid: build new capabilities as LangGraph subgraphs alongside the existing graph.
- What is the right cost model for CPU inference? Paperclip's per-token pricing assumes API billing. For local inference, cost maps to wall-clock compute time per NUMA node. Per-role time budgets may be more appropriate than per-token budgets.
- How should cross-layer preferences propagate in the Hermes outer shell architecture? User preferences expressed to Hermes reach the orchestrator as text in the prompt unless deterministic override flags (`routing_override`, `max_escalation`, `force_model`) are used via API parameters.
- Can a 32B local model do diagnostic reasoning from execution traces, or does this require Opus-class capability? The Meta-Harness paper only tested Opus.
- How does reasoning chain compression (FlowSteer, S3-CoT) interact with speculative decoding acceptance rates? Shorter reasoning chains may change the distribution of draft token acceptance.
- What is the optimal balance between tool availability and the Omega problem? 7/10 suites perform worse with REPL tools, but some tasks genuinely need them.
- Should EPYC adopt the observer-sidecar pattern for context compaction, or remain with in-session compaction? Sidecar avoids polluting main-session attention but doubles per-tool inference cost. Only viable if a cheap local model can serve as observer. (New — 2026-04-17, source: claude-mem deep dive)
- What is the right granularity for the REPL workflow event log? Tool-call level (every exec, file op) matches open-agents' step model but generates significant write volume. Turn-level is cheaper but loses reconnection fidelity within a multi-step turn. (New — 2026-04-17, source: open-agents deep dive)
- Does skill crystallization need automatic heuristics to trigger, or is LLM-prompted discipline sufficient at EPYC's task volume? GenericAgent has no automatic trigger; all promotion is LLM-driven. At higher task volume (autopilot overnight runs), LLM-directed promotion may be insufficient without a frequency-based or quality-gated trigger. (New — 2026-04-17, source: GenericAgent deep dive)
- Is a cost-aware capable→cheaper-worker delegation mode worth adding to `chat_delegation.py`, and what is the right cost model? OpenRouter's subagent (intake-705) frames delegation *downward* (capable model pays input-only tokens to hand a subtask to a cheaper worker under a per-request task cap). On CPU inference, "cost" is wall-clock compute per NUMA node, so the gate is whether the worker's faster decode plus the architect's avoided output tokens nets positive against the extra round-trip — open until measured. (New — 2026-06-20, source: intake-705)
- Should the placeholder-credential egress-proxy pattern (Centaur, intake-696) be implemented for EPYC's outbound tool calls (web_research, future API tools), or is single-host single-user trust sufficient to make it not worth the mitmproxy-style infrastructure? The defense is real (prompt-injection exfil leaks only placeholders) but the threat model on a single-user box is narrow. (New — 2026-06-20, source: intake-696)
- Does the shipped W7 game layer give the self-optimizer-integrity guarantee *by construction* — refuted narratives cannot re-inject and gaming is structurally impossible — or only by after-the-fact alarm? W6 being "clear" (`gaming_alarm=false`) today may mean the mechanism is solved or merely re-based; the guarantee, not the mechanism, is the open question. (New — 2026-07-02, source: fable5-architecture-review-2.md §2/§4A)
- Is the W5 `core_v2` calibration no-go (33/40, "do not promote" since 2026-06-15) the instrument correctly rejecting a mis-specified objective, or a mis-built instrument? The system built to *be* the product will not certify itself. (New — 2026-07-02, source: fable5-architecture-review-2.md §2)
- Is A/B/C the right decomposition for heterogeneous CPU+GPU serving on the MI210, or is the discriminating axis something else (prefill/decode disaggregation, KV-offload-primary when the KV cache rather than weights is the memory pressure, batch-regime, or a fourth family)? And is α(drafter→target) — still unmeasured — the correct single decisive experiment to run before pouring concrete into any GPU path? (New — 2026-07-02, source: fable5-architecture-review-2.md §4B)
- Should autopilot's ParetoArchive gain a bounded open-ended stepping-stone lane (DGM-style keep-diversity-sampled-dominated-configs) to escape local optima, given that our current policy intentionally prunes dominated configs — and should any species/meta-optimizer code become self-mutable (DGM self-referential rewrite) on a single-host box that cannot run concurrent inference? (New — 2026-07-02, source: intake-772)
- Can the DeepSeek-V4-Pro 0→80% frozen-model harness-evolution result (intake-753) be reproduced with a *local* proposer instead of Opus, given that the paper — like the original Meta-Harness — only tested an Opus-class proposer? The code>prompt transfer finding suggests deterministic-code mutations may be robust to a weaker proposer, but this is unmeasured. (New — 2026-07-02, source: intake-753)

## Related Categories

- [Routing Intelligence](routing-intelligence.md) -- MemRL learned routing is the core input classifier for agent role selection
- [Memory Augmented](memory-augmented.md) -- episodic, strategy, and skill memory stores that inform routing decisions
- [Autonomous Research](autonomous-research.md) -- the autopilot system that continuously optimizes agent configuration
- [Tool Implementation](tool-implementation.md) -- GitNexus codebase intelligence for coding agent context
- [Context Management](context-management.md) -- 5-layer context pipeline is a core architectural subsystem
- [Speculative Decoding](speculative-decoding.md) -- α(drafter→target) is the decisive gate for the MI210 CPU+GPU speculative-sidecar serving family
- [Hardware Optimization](hardware-optimization.md) -- heterogeneous CPU+GPU (EPYC + MI210/gfx90a) substrate underpins the 2026-07-02 serving-architecture co-lead

## Source References

- [Paperclip & AgentRxiv deep dive](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md) -- cost governance model (3-tier enforcement), ticket system with atomic checkout, shared knowledge accumulation, request depth tracking, heartbeat-driven invocation
- [LangGraph ecosystem comparison](../research/deep-dives/langgraph-ecosystem-comparison.md) -- checkpoint granularity gap, subgraph composition need, interrupt() flexibility, state immutability + reducers, domain advantages assessment (EPYC leads in 7 categories)
- [OpenGauss architecture analysis](../research/deep-dives/opengauss-architecture-analysis.md) -- tool-pair sanitization, protected-zone context compression, multi-backend abstraction, ACP server, prompt injection scanning, session analytics, trajectory export
- [orchestration-robustness-audit-2026-07-11.md](../handoffs/active/orchestration-robustness-audit-2026-07-11.md) -- supervisor/death ledger, startup attestation, loop supervision, REPL/tool compatibility layer
- [progress 2026-07-11](../progress/2026-07/2026-07-11.md) -- wrap-up checkpoint for landed docs-only changes and verification results
- [intake-103](https://arxiv.org/abs/2603.09906) Thinking to Recall -- CoT reasoning expands factual recall via computational buffer and factual priming; hallucination risk from generative self-retrieval
- [intake-105](https://arxiv.org/abs/2603.08640) PostTrainBench -- agents can surpass official baselines in targeted scenarios (BFCL 89% vs 67%) but substantially underperform on general post-training (23.2% vs 51.1%)
- [intake-106](https://arxiv.org/abs/2603.08706) Agentic Critical Training -- GRPO-based self-reflection for quality-aware agents; transfers across model sizes
- [intake-115](https://github.com/paperclipai/paperclip) Paperclip -- org-chart multi-agent orchestration with cost governance (~23k GitHub stars)
- [intake-117](https://github.com/NousResearch/hermes-agent) Hermes Agent -- self-improving agent with learning loop, FTS5+LLM summarization memory; validates outer-shell architecture
- [intake-120](https://openai.com/index/reasoning-models-chain-of-thought-controllability/) Reasoning Models Struggle to Control CoT -- 0.1-15.4% controllability, lower controllability correlates with higher monitorability
- [intake-125](https://arxiv.org/abs/2602.01982) S3-CoT -- self-sampled succinct reasoning via activation steering, no teacher model
- [intake-126](https://arxiv.org/abs/2602.05539) FlowSteer -- nonlinear activation steering for concise reasoning with input-dependent per-request budget
- [intake-131](https://arxiv.org/abs/2503.18102) AgentRxiv -- collaborative autonomous research, shared preprint server, 13.7% improvement on MATH-500
- [intake-133](https://arxiv.org/abs/2603.08462) Reasoning as Compression -- information bottleneck view of budget forcing; theoretical grounding for think-harder ROI
- [intake-271](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents) Skill Issue -- harness engineering drives ~28 rank positions on TerminalBench-2
- [intake-272](https://arxiv.org/abs/2602.11988) Evaluating AGENTS.md -- context files reduce success rates +20% cost; thin-map may be optimal
- [intake-312](https://alexzhang13.github.io/blog/2026/mgh/) Mismanaged Geniuses Hypothesis -- orchestration, not model power, is the bottleneck; 4B RLM achieves 100% MRCRv2
- [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md) -- execution trace feedback (+15pts), code mutation search space, GEPA integration
- [repl-turn-efficiency.md](../handoffs/active/repl-turn-efficiency.md) -- Omega problem (7/10 suites worse with REPL), frecency discovery, combined operations
- [tool-output-compression.md](../handoffs/active/tool-output-compression.md) -- 7-handler output compression, 60-90% token reduction per tool output
- [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) -- 4-species architecture, safety gates, evolution manager, GEPA optimizer
- [claude-code-local-constellation-routing.md](../handoffs/archived/claude-code-local-constellation-routing.md) -- MCP tool delegation, deterministic routing overrides
- [hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md) -- two-layer architecture with deterministic routing override flags, cross-layer preference propagation; 2026-04-17 update cross-references open-agents intake-397
- [claude-mem-persistent-memory.md](../research/deep-dives/claude-mem-persistent-memory.md) -- observer-sidecar pattern, 7-hook lifecycle taxonomy, structured XML observation schema with mode-defined taxonomy, `<private>` tag edge-layer stripping, six-field Stop-hook summary schema, batched-ID MCP tool for progressive disclosure; AGPL-3.0, no code adoption
- [genericagent-minimal-framework.md](../research/deep-dives/genericagent-minimal-framework.md) -- L0-L4 flat-file memory taxonomy, L1 ≤30-line always-in-context insight index, content-in-reply-body tool pattern, `no_tool` recovery handler, generator-based tool dispatch, L4 session archiver cron, LLM-driven promotion via SOP discipline; no sandbox, CN-market-first, not portable wholesale
- [vercel-open-agents-durable-workflow.md](../research/deep-dives/vercel-open-agents-durable-workflow.md) -- workflow event log for durable reconnect (portable pattern), typed Sandbox interface (exec/execDetached/read/write), scoped `task` subagent contract with summary-only return, large-output-to-FS convention; Vercel Sandbox is FS-only snapshot not memory hibernate, CRIU not viable for REPL with llama-server sockets
- [evomap-evolver-gep-protocol.md](../research/deep-dives/evomap-evolver-gep-protocol.md) -- Gene-record schema for mutation governance (signals_match/preconditions/strategy/constraints/validation), per-strategy forbidden-path deny-list, intent-mix strategy presets, EvolutionEvent log field alignment; no empirical benchmarks, partially obfuscated code, GPL-3.0, Hub invite-gated and unreliable; EvoMap/Hermes dispute has no technical merit
- [qwen-agent-framework-deep-dive.md](../research/deep-dives/qwen-agent-framework-deep-dive.md) -- intake-411, MCP singleton manager pattern (dynamic BaseTool subclass per tool, ping+reconnect, background async thread), Nous function-calling template (parallel `<tool_call>` XML), Reciprocal Rank Fusion hybrid search (`1/(rank+1+60)`), ParallelDocQA map-reduce, Router (LLM-driven selection, naive vs our learned routing); verdict: adopt_patterns (MCP integration model, RRF formula, DeepPlanning eval methodology)
- [deepplanning-agent-benchmark.md](../research/deep-dives/deepplanning-agent-benchmark.md) -- intake-412, 240-task planning benchmark with rule-based deterministic scoring, 26-model leaderboard, reasoning-mode gap data (+7.6pp to +40.1pp), multi-granularity scoring (dimension/composite/case), error taxonomy (global optimization dominant), reverse-generation solvability guarantee; verdict: adopt_patterns (multi-granularity scoring, planning-complexity signal, reverse-generation for PromptForge)
- [intake-418](https://arxiv.org/abs/2604.08224) Externalization in LLM Agents -- survey: three-dimensional externalization model (memory/skills/protocols), weights→context→harness era progression, self-evolving harness search; validates meta-harness optimization thesis (worth_investigating)
- [hcc-cognitive-accumulation-autopilot.md](../research/deep-dives/hcc-cognitive-accumulation-autopilot.md) -- intake-413, L1/L2/L3 tiered knowledge distillation maps to AutoPilot memory hierarchy (STM≈L1, missing L2, strategy_store≈flat L3); proposes knowledge_distiller.py for tier promotion; P14 AP-28–31 (adopt_patterns)
- [token-savior-extractable-patterns.md](../research/deep-dives/token-savior-extractable-patterns.md) -- intake-414, four extractable patterns for strategy_store.py: RRF hybrid retrieval, content-hash staleness, MDL convention promotion, progressive disclosure; priority: staleness > RRF > disclosure > MDL (adopt_patterns)
- [autopilot-iteration-strategy-synthesis.md](../research/deep-dives/autopilot-iteration-strategy-synthesis.md) -- synthesizes intake-413/414/415 into 4-phase AutoPilot improvement: (1) strategy memory upgrade ~200 LoC, (2) knowledge distillation ~300 LoC, (3) context budget ~150 LoC, (4) mutation knowledge graph ~200 LoC
- [intake-425](https://arxiv.org/abs/2604.14004) Memory Transfer Learning -- insight format (title/description/generalized_content) transfers best; negative transfer taxonomy (3 failure modes) for PromptForge safety gates; 431 curated memories beat 5,899 raw. Its task-agnostic comparison is external-paper evidence, not an EPYC measurement or a strategy-store write-path justification.
- [intake-426](https://arxiv.org/abs/2604.14228) Dive into Claude Code -- 98.4% infrastructure / 1.6% AI logic; 13 design principles from 5 human values; "Context as scarce resource" and "Minimal scaffolding, maximal harness" principles; ML permission classifier (anti-gaming); graduated trust model
- [hermes-agent v2026.4.23 release deep-dive](../research/deep-dives/hermes-agent-v2026-4-23-release.md) -- 2026-04-24: major upstream release (1,556 commits / 761 PRs / 29 contributors since v0.9.0). Key portable patterns: orchestrator-role subagents with cross-agent file-state coordination, `/steer` mid-run course correction without turn termination, **compressor anti-thrashing** (prevents compress→uncompress→re-compress oscillation already observed in our Phase 2b monitoring), language-aware collapse, fallback-to-main-model chain on 503/404, expanded plugin surface (slash-command registration, `pre_tool_call` veto, `transform_tool_result` hooks, namespaced bundles), transport abstraction. **Important finding**: `/mnt/raid0/llm/hermes-agent` is NOT a fork — tracks upstream cleanly with only an untracked `HERMES.md`. Recommendation: bump pin (`git checkout v2026.4.23`) rather than rebase. Tracked at `hermes-agent-index.md` P2.6.
- [intake-454](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.4.23) hermes-agent v2026.4.23 (v0.11.0) -- 2026-04-23 release; Ink TUI rewrite (React + Python JSON-RPC), Project/strict execution modes for code-exec safety, auto-prune sessions + state.db VACUUM at startup, 12 MCP improvements (timeout, status, tool-call forwarding, CDP raw passthrough), 5 new transports (Gemini CLI OAuth, NIM, ai-gateway, etc.).
- [Venice skills cross-runtime authoring deep-dive](../research/deep-dives/veniceai-skills-cross-runtime-authoring.md) -- 2026-04-24: `veniceai/skills` documents Hermes as a first-class target runtime (`$HERMES_OPTIONAL_SKILLS_DIR` / `~/.hermes/skills/`). Three portable patterns: `sync_from_swagger.py` OpenAPI→SKILL.md drift-detection (nightly CI), ≤500-line authoring rubric (short lead → endpoint table → curl + SDK example → gotchas), one-skill-per-API-surface decomposition. Concrete drift-detector gap identified in our `scripts/hermes/skills/` ↔ `OpenAIChatRequest.x_*` surface. Tracked at `hermes-outer-shell.md` Skills authoring rubric subsection.
- [intake-450](https://github.com/veniceai/skills) veniceai/skills -- canonical reference implementation of cross-runtime SKILL.md (Claude Code + Codex + OpenCode + Hermes + Cursor + Cline). MIT licensed.
- [pi-agent-core deep-dive](../research/deep-dives/pi-agent-core-stateful-ts-runtime.md) -- 2026-04-26: source-level review of `@mariozechner/pi-agent-core` (`badlogic/pi-mono/packages/agent`). 5 named primitives worth lifting into EPYC orchestrator vocabulary: two-stage message pipeline (`transformContext` + `convertToLlm`), `beforeToolCall`/`afterToolCall` hooks with field-replace + throw-isolation, steering-vs-follow-up split with `one-at-a-time`/`all` queue modes, per-tool `executionMode` override + batch fallback, terminate-unanimous-batch rule. 80+ contributors (Armin Ronacher top-5), 3,805 commits, formal CHANGELOG with `closes #N`, ~1:1 test/src ratio. Initial intake mis-estimated credibility from README alone — captured as feedback memory.
- [intake-473](https://github.com/badlogic/pi-mono/tree/main/packages/agent) `@mariozechner/pi-agent-core` — Stateful TypeScript Agent Runtime. Verdict: `adopt_patterns`. 6 handoffs updated 2026-04-26 with pattern lifts.
- [intake-474](https://arxiv.org/abs/2512.04695) TRINITY: An Evolved LLM Coordinator (ICLR 2026, Sakana AI). Verdict: `new_opportunity`. **Standing comparative context** for all orchestrator/routing work. Spawned [`tri-role-coordinator-architecture.md`](../handoffs/active/tri-role-coordinator-architecture.md) and [`outer-coordinator-learned-head.md`](../handoffs/active/outer-coordinator-learned-head.md), plus tasks across `learned-routing-controller.md` Phase 4 + `decision-aware-routing.md` DAR-1.5 + `routing-and-optimization-index.md` P19.
- [Trinity deep-dive](../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) — methodology cross-check vs our stack, portable-vs-not split, replication budget estimate, 9 refined recommended actions.
- [intake-498](https://arxiv.org/abs/2604.22748) Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond (Chu et al., 42 authors HKUST/NUS/Oxford/CUHK/NTU/HKU/UW; cs.AI 2026-04-24). Survey introducing **Levels × Laws** taxonomy: capability levels L1 Predictor / L2 Simulator / L3 Evolver × four governing-law regimes physical/digital/social/scientific. Synthesizes 400+ works, 100+ representative systems. Verdict: `adopt_patterns` (vocabulary + four-principle rubric, NOT full framework). EPYC stack mapping: autopilot = L3-Evolver / Digital, agent-world ETD = L2-Simulator → L3-Evolver bridge / Digital, meta-harness = L3-Evolver / Digital, q-scorer = L1-Predictor / Digital. Section 5.4 governance recipe (regression / robustness / rollback / canary gates) maps line-for-line onto autopilot SafetyGate. Section 6.1 four evaluation principles (long-horizon coherence, intervention sensitivity, constraint consistency, closed-loop use) testable in existing AR-3 today. MREP (Section E.6) proposed but not released; companion repo `matrix-agent/awesome-agentic-world-modeling` is bibliography-only.
- [Agentic World Modeling deep-dive](../research/deep-dives/agentic-world-modeling-levels-laws-taxonomy.md) — full L×R taxonomy with EPYC-stack mapping, governance recipe alignment, four-principle rubric, Beyond-L3 framing for Species 3 with closure-inflation guard, MREP watch.
- [intake-696](https://centaur.run/) Centaur (paradigmxyz/Tempo, MIT) — self-hosted multiplayer Slack agents; net-new primitive = placeholder-credential egress proxy ("iron-proxy" + 1Password runtime resolution); harness-adapter + durable child workflow duplicate HOS-Pattern-S / A2A; k3s sandbox out-of-scope. `external`
- [intake-697](https://vercel.com/eve) eve (Vercel, open-sourced 2026-06-17) — "Next.js for agents"; productized successor of vercel-labs/open-agents (intake-397); durable park/resume, hierarchical subagent delegation, zero-registration tools, conditional skills, eval-on-deploy all already enumerated in the vercel-open-agents deep-dive; no net-new lift. `external`
- [intake-700](https://github.com/ruvnet/ruflo) ruflo (ruvnet, ex-Claude-Flow) — swarm meta-harness; named primitives (strategy_store, ReasoningBank memory, SiliconSwarm sharing, pi-agent-core hooks) already covered; only net-new = zero-trust cross-machine federation (out-of-scope single-host); vendor-reported benchmarks are observations; CWE-78 patch noted. `external`
- [intake-705](https://openrouter.ai/docs/guides/features/server-tools/subagent) OpenRouter subagent server tool — provider-hosted stateless scoped delegation; EPYC already ships the core primitive (`chat_delegation.py` architect→specialist with role pinning + per-request caps; batched structured return in commit `18b5ceb`); real remaining delta = cost-aware capable→cheaper-worker delegation mode. `verified` (code), `external` (product)
- [intake-753](https://huggingface.co/spaces/joelniklaus/harness-optimization) Don't Train the Model, Evolve the Harness (Joel Niklaus, HF Space) — third-party empirical run of the Meta-Harness loop (intake-244) on Harvey's Legal Agent Benchmark; DeepSeek-V4-Pro 0→80.1% held-out via harness-only evolution; code>prompt mechanism-preference finding (5 of top 6 accepted = deterministic code); cost-aware scoring formula; 3-trial ≥1pt promotion; per-served-model tuning (code transfers cross-family, prompt playbooks do not). Single legal benchmark, LLM-judge, non-peer-reviewed → shapes proposer contract, does not gate. `adopt_patterns`, `external`
- [intake-772](https://arxiv.org/abs/2505.22954) Darwin Gödel Machine (Zhang/Hu/Lu/Lange/Clune) — self-referential self-improving coding agent (SWE-bench 20→50%, Polyglot 14.2→30.7%); distinctive triad vs. our corpus: self-rewrite of the editing agent, open-ended keep-all-stepping-stones tree archive (opposite of our greedy Pareto pruning), performance×fecundity parent sampling; both self-improvement and open-ended-exploration ablations load-bearing. Expanded from intake-753. Harvestable as a bounded QD lane + fecundity sampling, gated on resolution-aware verdicts + single-host compute. `adopt_patterns`
- [fable5-architecture-review-2.md](../handoffs/active/fable5-architecture-review-2.md) — window-2 entry brief for the `claude-fable-5` one-shot strategic-architecture consult; codifies the review-agent contract (full-agent GitNexus-grounded, read-only subagents, adversarial synthesis, cheapest-decisive-experiment guardrail, standing unprompted portfolio-audit + self-critique deliverables) and frames two co-leads: 4A self-optimizer integrity guarantee (evidence plane live-authority 2026-07-02, W6 clear, W7 shipped, W5 `core_v2` no-go held) and 4B heterogeneous CPU+GPU serving (MI210/gfx90a; A/B/C architecture families; α(drafter→target) still unmeasured).
- [2026-07-02-fable5-window2-brief.md](../progress/2026-07/2026-07-02-fable5-window2-brief.md) — session log reconstructing the 2026-06-12 window-1 (~500 KB / 17 files, MEASUREMENT.md adopted as instrument constitution), assessing the operator's draft prompt, and hardening the window-2 brief; documents the live-tree preflight (W6 clear not firing; MI210/ROCm 6.2 present; evidence plane live; α unmeasured; W5 33/40) and the read-only-subagent / proposed-not-in-place index write authority.
- [internal-interaction-lifecycle.md](../handoffs/active/internal-interaction-lifecycle.md) — A2A-semantics `Interaction` lifecycle over the existing delegation substrate; P1 substrate landed 2026-06-28 (`18956892`), P2 consult v1 staged default-off through 2026-07-05 (`interaction_skills.yaml`, `consultation.py`, `review_before_commit_consult` flag at the `run_edit_transaction()` seam, `0e555822`); invariants table (region-lock visibility, topology_role aliasing, enable_thinking flags, DCP-advisory, telemetry compat); live J17 gated on the ≥48h delegation-cache/ContentionDenied bake.
- [batched-edit-parallel-apply.md](../handoffs/active/batched-edit-parallel-apply.md) — think-then-act batch editing + parallel apply fan-out (intake-605); 2026-06-28→07-05 hardening arc: verified-only promotion, DCP `omitted_context_paths` fail-close preflight, transactional backup/restore promotion, deterministic stage-local BEP-4 fan-out, atomic sandbox restore, and the `ORCHESTRATOR_BATCH_EDIT_VERIFY_CMD` full-tree verifier gate (`8fb8f69a`); flag default-off, BEP-2/J8 an optional decision experiment post-edit-transaction.
- [delegation-context-preassembly.md](../handoffs/active/delegation-context-preassembly.md) — budget-bounded proactive context assembly for delegation (intake-605); DCP-1..5 built, DCP-4 advisory attach wired default-off; first live J7 A/B self-classified `hold` (`dcp_j7_decision.v1`: tokens 352→247.3 avg but p50 latency 20.2s→32.6s, quality unscored); attestation now surfaces DCP/J7 status read-only (`c3b2514e`); DCP-5 non-prescriptive discovery prompt landed `b7ba6265`.
- [minddr-deep-research-mode.md](../handoffs/active/minddr-deep-research-mode.md) — three-agent Planning/DeepSearch/Report `deep_research_mode` (intake-438, Li Auto MindDR); Phase-1 scaffold complete 2026-04-22 (`src/graph/minddr/`, flag, classifier, prompts, 20-query sentinel suite), parked at inference-gated MD-9 A/B with a ≥+5pp / no-regression / ≤2×-tool-calls promotion rule; Phase 2 RL GPU-gated (DGX wording stale post-MI210); MindDR Bench treated as deployment, not generalization, evidence.
- [progress 2026-07-04](../progress/2026-07/2026-07-04.md) / [progress 2026-07-05](../progress/2026-07/2026-07-05.md) — IIL P2 scaffold + bake readouts; consult/BEP/DCP-prompt wiring commits; AutoPilot `LocalPlannerProvider` (`7036630c`, local_ingest primary / Codex critic); tool-call batching investigation (parallel read-only REPL path exists, near-zero live tool use); self-running lab active-safe vs quiet-window job split (`0f7252bb`, `4829028d`).

## 2026-06-13 Update — Fable 5 Strategic Spine

Fable 5 reframes the North Star as a lab architecture, not just a serving/router architecture. The highest-ROI frontier is F1 -> F2 -> F3:

- **F1 real-task corpus**: define the demand side from recurring project work such as research intake, deep dives, benchmark analysis, code review, handoff hygiene, and ops runbooks. Public benchmarks remain useful, but they are supply-side proxies until real recurring tasks are captured with outcomes.
- **F2 self-running lab**: local agents should first take over mechanical lab-maintenance jobs in shadow/reviewed modes: freshness reports, attestation drift, digest drafts, intake triage, and claims checks. Jobs write review-queue artifacts, not handoffs or indices directly.
- **F3 data flywheel**: planner archives, intake decisions, per-question eval ledgers, and reviewed lab-job tuples become training corpora only after era labels and contamination filters are applied.

Two architectural guardrails matter. First, the evidence plane comes before autonomy: lab jobs must inherit per-question ledger, attestation, and claims discipline, or they will amplify stale narratives. Second, external-source injection hardening is a prerequisite for intake-touching jobs, because arbitrary papers/blogs/READMEs can otherwise smuggle instructions into future executable handoffs.

Sources: [Fable 5 strategic frontiers](../handoffs/completed/fable5-findings-07-strategic-frontiers.md), [frontier-f5-intake-injection-hardening.md](../handoffs/completed/frontier-f5-intake-injection-hardening.md).

## Updates — 2026-04-28

This update consolidates the Trinity-derived tri-role architecture (intake-474), defines the Conductor + Flywheel "design-space-reference" pattern as competitive intelligence (intake-492, intake-493), scopes the outer-coordinator OC-0 deliverable, situates meta-harness Tier 3's deferred outer-loop rebuild relative to Conductor, and confirms the pi-agent-core five-primitives cross-link.

### Trinity-derived tri-role architecture (intake-474)

Per [`tri-role-coordinator-architecture.md`](../handoffs/active/tri-role-coordinator-architecture.md) and the Trinity deep-dive (`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`, intake-474, ICLR 2026, Sakana AI):

- **Decouple role from model.** Today every EPYC role (`frontdoor`, `architect_general`, `coder`, `reviewer`, `worker`) is *attached to a model* — a model permanently has a role. Trinity's insight: role is a *per-turn property of the dispatch*. The same model can serve as Thinker on turn 1, Worker on turn 3, Verifier on turn 5. The dispatch policy decides per-turn role assignment, independent of which weights run that turn.
- **Empirical evidence.** Trinity ablation: removing the tri-role decomposition costs −5 to −8 points across all four benchmarks (LCB / Math500 / MMLU / RLPR). Removing Thinker alone costs −6.0 on Math500 and −4.57 on RLPR. The tri-role lever is the **second-largest empirical effect** in the paper after feature-position. This is the single most surprising finding: an architectural split below the model layer can dominate model selection.
- **Trinity itself uses 0.6B coordinator + 10K-parameter linear head trained via sep-CMA-ES against terminal binary task fitness.** EPYC's learned routing controller would apply the same tri-role dispatch *post-coordination*: the routing classifier picks model + role per turn.
- **Closure-inflation note.** Trinity is **NOT a target architecture**, it is a validated design-space reference. We do not plan to replicate Trinity's CMA-ES training, the 7-LLM heterogeneous pool with massive quality variance, or the 0.6B coordinator. We are taking the **architectural axis** (tri-role decomposition) and the **falsification value** (the −5 to −8 ablation gap) as standing comparative context for orchestrator and routing work.

### Conductor + Flywheel as design-space-reference pattern (intake-493, intake-492)

Both Conductor and Flywheel appear in [`meta-harness-optimization.md`](../handoffs/active/meta-harness-optimization.md) as **competitive intelligence references**, NOT target adoptions:

- **Conductor (intake-493)** = scheduler + cache-aware routing. 7B GRPO on 2× H100. Out of CPU stack — we cannot replicate the GRPO training, and a 2× H100 hardware target is GPU-gated. Reference value: validates that learned scheduling + cache-aware routing as joint optimization target is a legitimate design choice. Our learned-routing controller is a Conductor analogue at the model-selection layer; Conductor's scheduling layer is what our `dynamic-stack-concurrency.md` would converge toward at scale.
- **Flywheel (intake-492)** = durable memory + atomic-undo write contract. Node/MCP/Obsidian runtime. Lift-and-shift is not viable (Node-specific runtime, Obsidian-coupled). Reference value: the **abstract write contract** (atomic undo + content-addressed persistence) IS portable — applicable to `internal-kb-rag.md` K8 and `repl-turn-efficiency.md` durable-workflow patterns. The runtime is not.

**Pattern: design-space-reference table.** When recording an external system as competitive intelligence rather than a target, document:

| Field | Purpose |
|-------|---------|
| Roles | What the external system does |
| Key differences from EPYC | Where the architectural axes diverge |
| Why we reference | Validation of design trade-offs, NOT prescriptive target |
| Portable subset | Specific patterns/contracts that lift cleanly |
| Non-portable subset | Hardware/runtime/license constraints |

This is a deliberate anti-closure-inflation pattern: it forces a record of *what we are NOT adopting*, preventing the "we considered Trinity therefore we have a Trinity-class system" failure mode.

### Outer-coordinator OC-0 scoping (gated)

Per [`outer-coordinator-learned-head.md`](../handoffs/active/outer-coordinator-learned-head.md):

- **Speculative; gated until tri-role + DAR + LRC Phase 4 land.** OC-0 is a scoping document only — no implementation work has started. The phase order matters: until tri-role decoupling exists in the inner orchestrator, an outer coordinator has no per-turn role to dispatch over.
- **OC-0.6 NEW (2026-04-28)** populates the Trinity + Conductor design-space-reference comparison table inside the OC-0 deliverable, framed as competitive intelligence per user direction. The table follows the design-space-reference pattern above: roles, key differences from EPYC, why we reference, portable/non-portable splits. Trinity columns reference the deep-dive's revised reading that the *outer Claude-driven coordination layer* is the closer Trinity match than the inner inference pool (Claude vs cheap-frontdoor vs specialist-coder is a wider quality gradient than the inner pool).

### Meta-harness Tier 3 deferred outer-loop rebuild

Per [`meta-harness-optimization.md`](../handoffs/active/meta-harness-optimization.md):

- **Tier 1+2 done.** PromptForge integrated, GEPA folded into AR-3 Package D at 30% of mutation trials.
- **Tier 3 deferred.** "Outer-loop rebuild" is the design-space target where the harness searches over its own optimisation procedure (not just prompts/code). Phase 2 of env_synth (Agent-World GRPO) would be the first Tier 3 implementation; currently GPU-gated.
- **Conductor analogue for Tier 3.** A Conductor-style scheduler dispatching INTO meta-harness's optimised configurations is **compositional, not competitive** — Conductor would consume meta-harness Tier 2 output (validated harness configurations) and select per-request. This composition is hypothetical and tracked as design-space reference, not as scheduled work.

### pi-agent-core five primitives (cross-link confirmed)

The five named primitives from intake-473's pi-agent-core deep-dive remain in scope as naming/factoring lift, no code port:

1. Two-stage message pipeline (`transformContext` per turn at agent-message level, `convertToLlm` filter to LLM-strict payload).
2. `beforeToolCall` / `afterToolCall` hooks with field-replace-only semantics and per-call throw-isolation.
3. Steering-vs-followup queue split with `one-at-a-time` (default backpressure) vs `all` (drain-everything) drain modes.
4. Per-tool `executionMode` override with batch-falls-back-to-sequential rule.
5. Terminate-unanimous-batch rule — early stop only fires when *every* tool result in the batch sets `terminate: true`.

Cross-links to current handoffs (`hermes-outer-shell.md`, `meta-harness-optimization.md`, `repl-turn-efficiency.md`, `tool-output-compression.md`, `context-folding-progressive.md`) remain active as of 2026-04-28; no new cross-references added.

### Sources

- [intake-474](https://arxiv.org/abs/2512.04695) TRINITY: An Evolved LLM Coordinator (ICLR 2026, Sakana AI)
- [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md)
- [`handoffs/active/tri-role-coordinator-architecture.md`](../handoffs/active/tri-role-coordinator-architecture.md) — TR-1..TR-5
- [`handoffs/active/outer-coordinator-learned-head.md`](../handoffs/active/outer-coordinator-learned-head.md) — OC-0.6 design-space reference
- [`handoffs/active/meta-harness-optimization.md`](../handoffs/active/meta-harness-optimization.md) — Conductor/Flywheel competitive intelligence, Tier 3 deferred
- intake-492 (Flywheel — durable memory + atomic-undo write contract; Node/MCP/Obsidian runtime non-portable, abstract contract portable)
- intake-493 (Conductor — 7B GRPO on 2× H100; reference value only, GPU-gated)
- [intake-473](https://github.com/badlogic/pi-mono/tree/main/packages/agent) `@mariozechner/pi-agent-core` — five-primitives cross-link confirmed

## HALO Hierarchical Agent Loop Optimizer — applied RLM, mostly already-covered (2026-04-30)

**TL;DR**: HALO (Context Labs / inference.net, MIT, 2026-04 release) is an applied implementation of the foundational RLM paper (Zhang/Kraska/Khattab arxiv:2512.24601 = our intake-153, already_integrated with ~80% pattern coverage). Most of HALO's primitives duplicate existing EPYC infrastructure; three patterns are net-new and worth lifting WITHOUT vendoring halo-engine.

### Reported deltas (AppWorld benchmark, dev/test_normal split)

| Model | dev SGC | test_normal SGC |
|-------|---------|-----------------|
| Gemini 3 Flash | 36.8% → 52.6% (+15.8 pts) | 37.5% → 48.2% (+10.7 pts) |
| Sonnet 4.6 | 73.7% → 89.5% (+15.8 pts) | 62.5% → 73.2% (+10.7 pts) |

Findings independently verified against source trace files per repo claim. Single-bench scope; no peer review; pre-1.0 release (`0.1.2` at intake date).

### Net-new patterns worth lifting (3)

1. **Six-tool trace-query analyzer surface** (`get_dataset_overview`, `query_traces`, `count_traces`, `view_trace`, `search_trace`, `view_spans`) backed by a two-file JSONL+byte-offset trace store. Lands in [`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) T1+T5 (~230 LoC).
2. **dev/test_normal split discipline** as anti-overfitting guard. Cleaner than Pareto-archive replacement alone for both `meta-harness-optimization.md` Tier 3 and `autopilot-continuous-optimization.md` species frontier (cross-ref `feedback_checkpoint_pareto_state.md`). ~50 LoC + methodology change.
3. **Concrete failure-mode taxonomy** (4 labels: hallucinated tool calls / redundant args / refusal loops / semantic correctness). Complementary to intake-509 Pocock 4-mode taxonomy already in meta-harness scope; serves as seed labels for trace-clustering.

### Already-covered (do NOT re-implement)

| HALO primitive | EPYC equivalent |
|----------------|-----------------|
| OTel span emission | `scripts/autopilot/telemetry.py:to_otlp_span` (since 2026-04-12, intake-338) |
| Trace-driven mutator | meta-harness Tier 1 (intake-244 done) |
| Code-mutation search via coding agent | meta-harness Tier 2 done |
| GEPA evolution | autopilot AP-18-20 done (intake-345) |
| RLM REPL recursion | intake-153 R1-R6 done (~80% pattern coverage) |

### AppWorld decision: DEFER and skip the dataset

Hardware-feasible (no GPU/Docker; FastAPI in-process, ~5s first task). But integration cost is 3-5 days and **no current eval gap demands it**. 168 traces is reference-scale not training-scale. Revisit only when an autopilot signal explicitly demands a long-horizon multi-tool benchmark, or when meta-harness Tier 3 needs an external dev/test_normal anchor.

### Spike scoped

`handoffs/active/halo-trace-loop-spike.md` (READY-TO-CLAIM as of 2026-04-30): pre-flight (30 min) + Day 1 AM converter (~30 LoC for autopilot, ~200 LoC including tests) + Day 1 PM 4-criterion go/no-go gate + conditional Day 2 manual lift. **No vendoring of halo-engine.**

### Risks (carried to spike handoff)

- HALO `0.1.2` is pre-1.0 — API churn likely; pin version.
- Default `max_depth=1` in OSS RLM impls suggests recursive-depth claim is harder to operationalize than the paper implies.
- Default analyzer model is `gpt-5.4-mini`; spike must validate small-model coherence on local 30B-A3B coder before committing.
- Report is free-text markdown not structured JSON — adds a parse step if machine-actionable output is desired.

### Sources

- [intake-517](https://github.com/context-labs/halo) HALO — Hierarchical Agent Loop Optimizer (MIT, Context Labs / inference.net)
- [intake-518](https://pypi.org/project/halo-engine/) halo-engine 0.1.2 PyPI
- [intake-516](https://huggingface.co/datasets/inference-net/HALO-Gemini-3-Flash-AppWorld) HALO-Gemini-3-Flash-AppWorld dataset (168 traces, 3,438 spans)
- [intake-153](https://arxiv.org/abs/2512.24601) RLM foundational paper (Zhang/Kraska/Khattab) — already_integrated
- [`research/deep-dives/halo-rlm-trace-loop-integration.md`](../research/deep-dives/halo-rlm-trace-loop-integration.md) — full spike plan + risk register
- [`handoffs/active/halo-trace-loop-spike.md`](../handoffs/active/halo-trace-loop-spike.md) — claim-ready spike

## `/caveman` prose-style rider — orthogonal compression mechanism class (2026-04-30)

**TL;DR**: Pocock's `/caveman` (intake-509, MIT) is a **prompt-side prose-envelope rider** — different mechanism class from any compressor in the EPYC stack today. Operates on the agent's free-form prose generation; orthogonal (NOT substitutable) to TOON which owns structured payloads. Three handoffs converged on the same intake with three different framings:

| Handoff | Stance |
|---------|--------|
| `tool-output-compression.md` | Reframe — `/caveman` is prose-only, NOT a generic compression alternative. Stack order: `caveman on prose wrapper → TOON on embedded structured payload`. Anything structured belongs to TOON. |
| `repl-turn-efficiency.md` | Companion to S3 suggestion-injection — same Omega-gate requirement (suppression vs injection are different signs of the same axis). |
| `agent-file-prose-compression.md` (NEW handoff) | A different deployment target — agent-file authoring time, not runtime. Static, build-time, human-reviewed. |

### Three risks (block runtime/inter-model deployment without explicit gates)

1. **Hedge-preservation**: `/caveman`'s drop-list explicitly includes "hedging". For inter-model escalation/delegation/consultation flows, hedge-stripping silently turns "this might work but..." into "this work" — a downstream verifier comparing confidence levels across models cannot tell low-confidence answers from high-confidence ones. **Lever must NOT be deployed on flows that aggregate multi-model opinions until a hedge-preservation eval (uncertainty-marker recall on a held-out set) is in place.**
2. **Persistence-clause**: `/caveman`'s prompt body says verbatim **"ACTIVE EVERY RESPONSE once triggered. No revert after many turns."** Session-scoped, NOT turn-scoped. If wired into REPL-turn machinery, the `setCaveman(on|off)` setter must be **session-level state** and the steer/follow-up queues must NOT be allowed to flip it implicitly. Queue mode (per-turn drain) and caveman mode (session-level prose style) live at different timescales and must not be conflated.
3. **Reasoning-fidelity**: prompt-side style riders are known to occasionally degrade reasoning on multi-step tasks (model "compresses" intermediate thinking it actually needed). Pocock's repo does not measure this; the auto-clarity exception in `/caveman` covers "multi-step sequences where fragment order risks misread" but the gate is non-deterministic.

### Minimum eval gate before runtime deployment

50 consultation traces, blind quality scoring by Q-scorer, target **≥95% baseline quality at ≥40% prose-only token reduction**, plus an explicit hedge-preservation recall eval on a held-out set with explicit uncertainty markers. Do NOT trust Pocock's 75% headline as either a target or a baseline — treat it as an upper bound only.

### Agent-file prose compression — different beast, three structural advantages

The `agent-file-prose-compression.md` handoff (NEW 2026-04-30, HIGH priority) addresses a different deployment target than runtime `/caveman`:

1. **Static, build-time, human-reviewed.** Compression is run once per agent file, the diff is reviewed by a human, the result is committed. Non-determinism of the compressor is replaced by a human gate. No 5-minute prompt-cache pressure, no live failure modes.
2. **Monolog, not aggregation.** Agent reads agent file as instructions to itself. There is no downstream verifier comparing confidence markers, so the hedge-stripping failure mode that blocks runtime `/caveman` does not apply here. Hedging in instruction prose is usually noise.
3. **Read-many, write-once amortization.** Agent files are loaded into context every session by every agent. A 30-50% reduction at session start compounds across every session of every agent.

Three new agent-file-specific risks: (a) directive polarity (`must`/`must not`/`never`/`always` and RFC 2119 vocabulary) must survive — vanilla `/caveman` does not specifically protect them; project rider MUST; (b) procedural ordering must survive (numbered procedures carry order via list structure; prose-described workflows need a preserve-clause); (c) smaller drafter models read agent files too — per-model compression-tolerance curve is the right answer; a single fixed level is wrong.

**Pipeline integration**: per-model compliance gate becomes a step in the `/new-model` onboarding flow. A model that fails ≥95% baseline compliance at the candidate compression level is flagged before reaching production.

### Sources

- [intake-509](https://github.com/mattpocock/skills) Skills For Real Engineers — Matt Pocock's Claude Code skills collection (`/caveman`, `/grill-with-docs`, `/setup-matt-pocock-skills`, `/write-a-skill`)
- intake-450 — veniceai/skills sibling cross-runtime SKILL.md authoring rubric
- intake-301 — AXI: Agent eXperience Interface (TOON encoding — orthogonal layer)
- [`handoffs/active/tool-output-compression.md`](../handoffs/active/tool-output-compression.md) Research Intake Update 2026-04-30 — TOON-orthogonality reframe + 3-risk register
- [`handoffs/active/repl-turn-efficiency.md`](../handoffs/active/repl-turn-efficiency.md) Research Intake Update 2026-04-30 — persistence-clause caveat
- [`handoffs/active/hermes-outer-shell.md`](../handoffs/active/hermes-outer-shell.md) Research Intake Update 2026-04-30 — Pocock skills installer pattern as per-repo bootstrap
- [`handoffs/active/agent-file-prose-compression.md`](../handoffs/active/agent-file-prose-compression.md) NEW — `/agent-file-compress` skill + per-model deployment gate

## DeepSeek-TUI vocabulary + snapshot-store port recipe (2026-04-30)

**TL;DR**: intake-508 (Hmbown/DeepSeek-TUI) is a closed-DeepSeek-API-only Rust TUI; nothing to fork or import wholesale. Two patterns lifted with corrected framings after primary-source review.

### Pattern 1 — Plan/Agent/YOLO names: keep vocabulary, drop the two-axis claim

Source review confirms `AppMode` is a **flat tri-state enum** (`crates/tui/src/core/engine.rs`), NOT a clean (gate × approve) cross-product:

| Mode | Mechanism | Honest framing |
|------|-----------|----------------|
| `Plan` | Registry-restricted: mutating tools never registered (`with_read_only_file_tools()` ~line 1450) | Strong enforcement at registry-build, not a runtime gate. Porting the *guarantee* requires committing to the same registry-shaping discipline. |
| `Agent` | Full registry + per-call approval prompts. Approval channel exists but the "does this call need approval" predicate is woven through `Feature` flags + `session.allow_shell` + per-tool `SafetyLevel` | **No single function to lift** — porting requires a refactor. |
| `YOLO` | Base case: short-circuit `if mode == AppMode::Yolo { return false; }` (~lines 1070-1090) | Negligible logic. |

**Honest framing for outer-shell**: "Plan = registry-restricted to read-only; Agent = full registry + per-call approval prompts; YOLO = full registry, prompts skipped." Adopt names; design our own per-call gate predicate. Do **not** sell this externally as a clean two-axis (gate × approve) system — DeepSeek-TUI does not actually implement that.

**Caveat (live TODO in source)**: `command_safety.rs` carries a top-of-file `// TODO(integrate): Wire command safety analysis into shell tool approval flow`. The shell-command safety classifier is **not yet wired** into the approval flow.

### Pattern 2 — Side-git snapshot rollback: workspace-files-only, clean port recipe

Source review (`crates/tui/src/snapshot/{repo.rs, paths.rs}`) confirms:

- **Storage**: `~/.deepseek/snapshots/<project_hash>/<worktree_hash>/.git`. Both hashes are FNV-1a of the canonicalized workspace path. The two-tier hash strips `.worktrees/<name>` so sibling worktrees share a snapshot project while branches stay isolated — **worth borrowing**.
- **Init**: `git init --quiet <parent_dir>`. Not a clone, not a hardlink, not a worktree-add.
- **Per-call invariant**: every subsequent `git` invocation passes both `--git-dir` and `--work-tree`. Makes the store immune to cwd surprises and forecloses accidental `.git` mutation. **Cleaner than a shadow clone.**
- **Snapshot create** (lines 113-156): `git add -A` → `git write-tree` → `git commit-tree` → `git update-ref HEAD`.
- **Restore** (lines 161-177): `git checkout <sha> -- :/` plus `remove_paths_missing_from_target()`.

**CAVEAT (leaky abstraction)**: snapshots are **workspace-files-only**. Conversation/session state is persisted separately (`session.rs`); `revert_turn` does NOT roll back the model context. A restored workspace can desync from the running conversation. If we promise users "session rollback", we must also serialize and restore the conversation state — DeepSeek-TUI does not.

**Port recipe (Python, ~30 LoC)**: subprocess-only, language-agnostic. `subprocess.run(["git", "--git-dir", g, "--work-tree", w, "add", "-A"])`, then `write-tree`/`commit-tree`/`update-ref`/`checkout`. Two-tier FNV-1a path hash for the store layout. Pin this as the actionable port if/when outer-shell needs checkpointing.

### MCP approval as JSON-RPC error `-32001` (informational)

`mcp_server.rs` rejects unapproved tool calls with `-32001`; client resends with `"approved": true`. Tidy way to expose tri-state semantics to MCP clients without a bespoke schema. Worth recording for any future MCP-server work in this repo.

### Sources

- [intake-508](https://github.com/Hmbown/DeepSeek-TUI) DeepSeek TUI — Terminal-native coding agent for DeepSeek V4 (Rust, closed-API-only)
- [`handoffs/active/hermes-outer-shell.md`](../handoffs/active/hermes-outer-shell.md) Research Intake Update 2026-04-30 — flat-enum disclosure + snapshot port recipe

## Hermes/OpenGauss outer shell (2026-05-06)

Coordinating handoff [hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md) tracks integration of Hermes (Nous Research agent frontend, upstream at /mnt/raid0/llm/hermes-agent) with OpenGauss as a possible outer-shell coordination layer above the EPYC orchestrator. Architecture pattern: Hermes handles user-facing dialogue + planning; orchestrator handles role routing + LLM dispatch; OpenGauss provides persistence for episodic memory + cross-session state. Status: design + intake; no production deployment yet.

Source: [handoffs/active/hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md).

## Per-model agent-file prose compression as a deployment gate (2026-05-06)

Static compression of agent-file prose (`agents/*.md`, `agents/shared/*.md`, `CLAUDE.md`) at authoring time is a **different deployment target** from the runtime inter-model `/caveman` rider documented in the 2026-04-30 section above. Three structural advantages: static + build-time + human-reviewed (no streaming-cache pressure); monolog (no downstream verifier comparing confidence markers across authors, so the hedge-stripping failure that blocks `/caveman` on consultation flows does not apply); read-many-write-once amortization (every session of every agent loads the file). Three new risks: directive polarity must survive (RFC 2119 keywords carry directive sign — dropping or downcasing one is a compliance bug), procedural ordering must survive (prose-described workflows must keep "first / then / finally" ordering words), and smaller drafter models read agent files too (per-model compression level is the right answer; a single fixed level is wrong).

Mechanism: project-specific rider at `.claude/skills/agent-file-compress/` with stricter Drop list (articles, filler, pleasantries, non-directive hedging, redundancy, parenthetical asides) and an explicit Preserve-verbatim list (RFC 2119 markers, headers, frontmatter, code blocks, ordered lists, file-path refs, examples, RFC citations, procedural-ordering words). Polarity gate: `grep -o` occurrence count of `(must|must not|shall|should|may|never|always|do not|don.t)` must be exactly equal between original and compressed (line-counting `grep -c` under-reports when compression merges multiple directive sentences onto one line).

Per-model compression-tolerance curve becomes a **deployment gate** via `agent_file_compression_operating_point` field in `model_registry.yaml` (orchestrator + research) — values `none | mild | medium | aggressive`. `none` blocks production deployment of the model to roles that consume agent files. The orchestrator routes the same logical agent file at different compression levels to different models based on each model's operating point.

Pilot finding (2026-05-06, `agents/shared/ENGINEERING_STANDARDS.md`): file is unusually compression-resistant (12 RFC-2119 directives in 696 words — 1.7% density — plus 27% non-prose content). Achieved reductions: mild 12.4%, medium 21.8%, aggressive 28.4% (vs band targets 20%/40%/60%). All 12 directives preserved exactly. Useful empirical signal that the band targets are calibrated for narrative-prose files, not directive-dense policy files; the per-model curve must be measured per-file-class.

Sources: [`handoffs/active/agent-file-prose-compression.md`](../handoffs/active/agent-file-prose-compression.md), `.claude/skills/agent-file-compress/SKILL.md`, `tests/compliance/agent_file/` (15+12+15 task pool + runner harness), `.claude/commands/new-model.md` (Step 6.5).

## RAO + RLM substrate cluster (2026-05-19)

May 2026 brought a coherent cluster of papers on recursive-agent training, RLM reproduction, and harness substrates that, taken together, split the previously-monolithic "recursive language models" research direction into four distinct EPYC-actionable threads.

**RAO** (intake-536, arxiv:2605.06639, CMU — Gandhi/Chakraborty/Wang/Kumar/Neubig) is the **training-side complement** to RLM's inference-time orchestration paradigm. It trains an LLM agent via RL to dynamically spawn and coordinate recursive copies of itself. The three load-bearing mechanisms: (1) **mean-of-children delegation bonus** (NOT sum — explicitly prevents the trivial-spawn exploit); (2) **multi-task objective sampled across execution-tree depths** providing an automatic curriculum from model-generated sub-tasks; (3) **leave-one-out (LOO) baseline shared across rollout group** + **depth-level inverse-frequency weighting** preventing leaf-trajectory domination. Headline empirical: TextCraft-Synth hard 0.88 (recursive) vs ~0 (single-agent); Oolong-Real (10–12pg D&D, 32K ctx) 30B recursive ≈ frontier Claude/o3/GPT-5-mini.

**ReDel** (intake-550, arxiv:2408.02248, EMNLP 2024 Demos) is the **working open-source harness substrate** RAO presumes. MIT + Commons Clause licensed (research use OK, resale blocked). 98.9 KB Python core, Python ≥3.10, last push 2026-05-11. Built on `kani`; backend swappable to local llama-server via `OPENAI_BASE_URL` env var. Two delegation primitives: `DelegateOne` (blocking) and `DelegateWait` (non-blocking with `asyncio.gather`). First-class event-stream logger and web debugger. Lifts cleanly onto EPYC; substrate spike at [`rao-redel-substrate-spike.md`](../handoffs/active/rao-redel-substrate-spike.md) covers a 3-step gated rollout (1-day pre-flight → 1-week paired A/B vs in-house `repl_executor` → 2-3 week feature-flagged substrate replacement).

**Wang RLM reproduction** (intake-547, arxiv:2603.02615) is the **load-bearing depth caveat**: independently reproduces the Zhang/Kraska/Khattab RLM framework on DeepSeek v3.2 and Kimi K2. **Direction-of-effect is model-dependent** — Kimi K2 OOLONG depth-0 (86.6%) BEATS depth-1 RLM (60.0%). Depth=2 inflates DeepSeek v3.2 S-NIAH wall-clock 96× (3.6s → 89.3s → 344.5s). `max_depth=1` is now the load-bearing default for any RAO/RLM-style integration on EPYC unless we explicitly train a depth-controller.

**Orchestration-trace survey** (intake-548, arxiv:2605.02801) identifies the **stopping-decision gap** — as of May 2026 NO published RL method explicitly trains the stopping decision. RAO uses fixed depth/step caps. On CPU EPYC where every token is BW-expensive, a learned stop policy has more differential value than anywhere else. The survey's 5-sub-decision taxonomy `{when-to-spawn, whom-to-delegate, how-to-communicate, how-to-aggregate, when-to-stop}` becomes a labelling axis on the episodic store (~50 LoC, mirrors `tri-role-coordinator-architecture.md` TR-2.2's `assigned_role` precedent).

**Tree-GRPO** (intake-549, arxiv:2509.21240, ICLR 2026): methodological alternative to RAO's LOO baseline. Each tree node is a complete agent interaction step; prefix-sharing across siblings increases rollout count under fixed token+tool-call budgets. Proof: intra-tree group-relative optimization is equivalent to step-level direct preference learning — derives dense step-wise process signal from outcome-only rewards.

**Sources**: [intake-536](https://arxiv.org/abs/2605.06639) RAO · [intake-547](https://arxiv.org/abs/2603.02615) Wang RLM reproduction · [intake-548](https://arxiv.org/abs/2605.02801) Orchestration-trace survey · [intake-549](https://arxiv.org/abs/2509.21240) Tree-GRPO · [intake-550](https://arxiv.org/abs/2408.02248) ReDel · [Deep-dive](../research/deep-dives/2026-05-19-rao-rlm-cluster.md) · [Substrate spike](../handoffs/active/rao-redel-substrate-spike.md)

## Latent multi-agent systems cluster — heterogeneity actionable; latent handoff blocked (2026-05-19)

Five papers spanning training-free latent collaboration, theoretical identifiability, heterogeneous text-MAS, and cross-architecture frozen-LLM composition. Deep-dive verdict: **only X-MAS is actionable today on EPYC**; the latent-handoff entries (RMAS / LatentMAS / Dead Weights) are blocked on llama.cpp HTTP server fork work (4-8 weeks + 2× rebase debt vs ik_llama PR #1744 worker_pool branch).

**X-MAS** (intake-557, arxiv:2505.16997) — empirical (5-domain × 5-function × 27-LLM) sweep with 1.7M evals. Heterogeneous MAS significantly outperforms homogeneous MAS with no structural change. Reported magnitudes: MATH +8.4% (heterogeneous chatbot-only), AIME +47% (mixed chatbot-reasoner). Text-mediated, zero llama.cpp changes. Spike at [`x-mas-text-routing.md`](../handoffs/active/x-mas-text-routing.md) builds a 5×5 (domain × function) → winner-model lookup on our 4-model production stack. Cheap-kill failure mode: if gemma4-26B-A4B wins ~all cells (per its `project_worker_general_swap_2026_05_08` tool_compliance dominance), heterogeneity doesn't apply and the spike aborts.

**RMAS** (intake-544, arxiv:2604.25917, Yang et al.) — extends RLM to multi-agent via unified latent-space recursive computation. RecursiveLink modules (two-layer residual projections, inner+outer); inner-outer loop training. Reported +8.3% avg accuracy, 1.2-2.4× inference speedup, 34.6-75.6% token reduction across 9 benchmarks. Requires fine-tuning shared embedding spaces across roles — heavyweight for frozen GGUF mixed-architecture (Qwen/Gemma/Llama) stack.

**LatentMAS** (intake-555, arxiv:2511.20639, ICML 2026 Spotlight) — training-free framework using last-layer hidden embeddings. Claims 4-4.3× decode speedup, 70.8-83.7% output token reduction, +14.6% accuracy across 9 benchmarks. **Heterogeneity claim overstated** (paper Section C.3 admits all agents share same shape of transformer layers; all experiments use only Qwen3 4B/8B/14B — same family, same tokenizer).

**Dead Weights** (intake-558, arxiv:2604.08335, Armstrong/Ayoobi/Mukherjee — 3-author preprint, no code) — claims independently trained LLMs converge to geometrically compatible latent spaces; a single learned linear projection (~17.6M trainable params vs ~12B frozen) suffices to translate activations between heterogeneous architectures (Llama-3.2-1B / Qwen2.5-1.5B / Gemma-2-2B → Phi-3-mini / Mistral-7B). Reports ARC-Challenge 87.3% (+11.4pp over best single model). **Keystone but credibility-weakest** in cluster; GPU rental for replication (~$200-500) DEFERRED per user 2026-05-19.

**Thought Communication** (intake-556, arxiv:2510.20733) — theoretical identifiability framework: nonparametric recoverability of shared vs private thoughts between agent pairs. No engineering hook yet.

**Sources**: [intake-544](https://arxiv.org/abs/2604.25917) RMAS · [intake-555](https://arxiv.org/abs/2511.20639) LatentMAS · [intake-556](https://arxiv.org/abs/2510.20733) Thought Communication · [intake-557](https://arxiv.org/abs/2505.16997) X-MAS · [intake-558](https://arxiv.org/abs/2604.08335) Dead Weights · [Deep-dive](../research/deep-dives/2026-05-19-latent-mas-cluster.md) · [X-MAS spike](../handoffs/active/x-mas-text-routing.md)

## Code-as-Agent-Harness survey + Repo Prompt harness analysis (2026-05-25)

Deep dive of intake-607 (*Code as Agent Harness* survey, arxiv:2605.18747) + intake-605 (Repo Prompt as a harness/context **competitor**, not a closed-source dead end). The survey mostly *confirms* our direction (it names Context-Folding as the canonical compaction design — we already track intake-154); the genuinely additive ideas + RP's harness patterns are below, all seeded into draft handoffs P22–P25 in [`routing-and-optimization-index.md`](../handoffs/active/routing-and-optimization-index.md).

- **Harness-level evaluation, not just final-task-success (§5.2.1 / §5.2.7) — the standout.** Scoring only task completion optimizes a noisy single bit that rewards shortcut configs (cf. our Package-B finding that REPL "succeeds" by web-searching the answer). Instead score *intermediate* behavior on named axes — **execution fidelity, feedback interpretation, planning stability, memory coherence, recovery rate** — plus an **oracle-adequacy meta-metric** (does the eval oracle actually cover the failure modes, or am I assuming "no exception = correct"?). Methodology: **hold the model fixed, vary only the harness**. → meta-harness `HLE-1/2/3` + autopilot `HLE-4`.
- **Behavior-signature versioning for regression-safe self-improvement (§5.2.3 / §5.2.4).** We are *ahead* on scalar regression gating (quality floor, per-suite guard, auto-rollback, git reverts) but merge improvements *syntactically* — a new autopilot config can silently break a prior Pareto win. Prescription: attach a behavior signature (per-sentinel outcome hash/vector) to each archive member; differential-test new-vs-old in parallel and compare *behavior* not just aggregate score; flag semantic conflicts when two mutations touch the same subsystem. → autopilot `BSV-1/2/3`.
- **Uncertainty-routed escalation with approval as harness state (§5.2.5).** A second escalation axis orthogonal to our quality Q-values: quantify decision *uncertainty*, route high-uncertainty decisions up, persist the approval/escalation decision as auditable harness state. → decision-aware-routing `URE-1/2/3`.
- **Experiential memory = index *failed* trajectories for avoidance (§3.2.1 / §3.2.3).** Failures should be stored and *retrieved for pattern-matched avoidance*, not just logged (ExpeL / Evo-Memory / MemGovern); and working state should be *externalized* because LLMs fail at latent-state persistence. → unified-trace-memory `EXM-1/2/3`. The memory taxonomy (working / semantic / experiential / long-term / multi-agent) is a useful coverage checklist.
- **Repo Prompt as a harness competitor (intake-605).** Reactive-vs-proactive context (see [context-management.md](context-management.md)) plus two edit-pipeline patterns sharp on CPU: **think-then-act batch editing** (emit one structured edit set, no interleaved tool calls → fewer prefill+decode round-trips) and **parallel apply fan-out** (cheap workers apply per-file concurrently, maps to our 32×6t NUMA split, +44–58%). → handoff [`batched-edit-parallel-apply.md`](../handoffs/active/batched-edit-parallel-apply.md) (BEP-1..5). **2026-05-27 update:** BEP-2's production fix shipped through edit-transaction mode, so the original batch-vs-interleaved A/B is optional provenance rather than the critical falsification gate. RP also exposes its MCP tools to *both* its own Context Builder sub-agent and external agents (one tool surface, two consumers), ships a first-class `oracle_send` escalation primitive (modes chat/plan/edit/review), and sandbox-before-disk reviewable patches with granular accept/reject.

A concurrent competing survey ("Agent Harness for LLM Agents", Preprints 202604.0428, 110+ papers) confirms 607 `novelty:low` — the harness-survey cluster is saturated; the value is the actionable framings above, not the taxonomy itself.

**Sources**: [intake-607](https://arxiv.org/abs/2605.18747) Code as Agent Harness · [intake-605](https://repoprompt.com/) Repo Prompt · [intake-244] Meta-Harness (in-flight) · handoffs [meta-harness-optimization](../handoffs/active/meta-harness-optimization.md) HLE · [autopilot-continuous-optimization](../handoffs/active/autopilot-continuous-optimization.md) HLE-4/BSV · [decision-aware-routing](../handoffs/active/decision-aware-routing.md) URE · [unified-trace-memory-service](../handoffs/active/unified-trace-memory-service.md) EXM · [delegation-context-preassembly](../handoffs/active/delegation-context-preassembly.md) · [batched-edit-parallel-apply](../handoffs/active/batched-edit-parallel-apply.md) · intake_index.yaml intake-605/607 `deep_dive`

## Internal interaction lifecycle: A2A semantics, not transport (2026-05-31)

The A2A protocol deep dive split the adoption question into two independent choices. EPYC should adopt A2A-style lifecycle semantics internally, but should not adopt A2A wire transport between local roles yet. The internal target is an `Interaction` abstraction with `kind ∈ {delegate, consult, verify, route}`, explicit states (`created`, `working`, `input_required`, `completed`, `failed`, `cancelled`), artifacts, events, budgets, scheduler policy, and policy-versioned telemetry. This makes current architect delegation and future "consult a larger model for advice" calls siblings on one substrate.

The transport decision stays deferred because the current optimization model depends on cross-role visibility that opaque peer-agent boundaries would hide or force into protocol metadata: region-lock state, shape-aware contention, shared-backend `topology_role` aliasing, and per-role transport quirks such as `enable_thinking=false` on `/v1/chat/completions`. The new handoff therefore treats A2A as a vocabulary and lifecycle model, not as an internal service mesh.

Planned rollout is four gated phases: P1 refactors existing architect delegation with no behavior change; P2 adds one-shot typed consults using `interaction_skills.yaml`; P3 shadow-tests `should_consult()` gates using routing-intelligence signals; P4 measures integration quality (`advice_adopted_correctly`, issue catch rate, false-block rate, downstream quality delta, contention tax) before blending any reward. External A2A remains a Hermes outer-shell concern, reopened only when external agent exposure or cross-vendor A2A peers become load-bearing.

P2-0 discovery is complete: the first consult seam is `epyc-orchestrator/src/edit_transaction.py:199` `run_edit_transaction()`, between draft parse and transactional apply, with `coder_escalation` as requester and `architect_general` as consultant for `review_before_commit`. Implementation remains gated: P1 must wait for the cross-role contention/autopilot bake to clear, P2 waits for P1's regression gate, and the P2 A/B is registered as J17 in `bulk-inference-campaign.md`. The missing bake-counter emission was fixed and deployed in `epyc-orchestrator` `02a01617` on `2026-07-03T15:40:30Z`; the remaining gate is now the ≥48h clean counter window, not instrumentation absence.

**2026-07-05 update**: P1 landed 2026-06-28 (`18956892`, byte-equal diagnostics proof + clean affinity preflight), and the whole P2 consult v1 — skill spec, schema-constrained `consult()`, cache-key namespacing, `log_consult()`, DCP-packer reuse via `dcp_for_consult` (`4183522f`), and the wired edit-transaction consult site behind `review_before_commit_consult` (`0e555822`) — is staged default-off. Live J17 behavior stays locked on the ≥48h bake (38.04h/48h as of 2026-07-05). Full detail in the 2026-07-05 New Findings section above.

**Sources**: [`internal-interaction-lifecycle.md`](../handoffs/active/internal-interaction-lifecycle.md) · [`hermes-outer-shell.md`](../handoffs/active/hermes-outer-shell.md) intake-655 update · [`routing-and-optimization-index.md`](../handoffs/active/routing-and-optimization-index.md) subsystem row · `research/intake_index.yaml` intake-655 · [`progress/2026-05/2026-05-31.md`](../progress/2026-05/2026-05-31.md)

## Intake deep-dives: Economy of Minds & RLM structured-output contracts (2026-06-12)

Two agent-architecture intake entries (intake-692, intake-693) were deep-dived; both refined toward "less new than it looked."

**Economy of Minds / EoM (intake-692, arxiv:2606.02859) — adopt_patterns → metaphor-mostly.** A Hayekian agent *economy*: agents compete via auctions for action rights, exchange payments, accumulate wealth from environmental rewards (decentralized credit assignment), and the population evolves by economic selection (wealthy→mutated, bankrupt→replaced). The deep-dive found autopilot **already implements the economic-selection idea in soft form**: `ExperimentJournal.species_effectiveness()` (`experiment_journal.py:759`, `rate=pareto/total`) → `MetaOptimizer.rebalance()` → weighted-random `select_species()` (`meta_optimizer.py:136`) is exactly a softmax-over-effectiveness bandit. EoM's "auction" reduces to fixed-bid first-price (= static priority + random tie-break); its only genuinely novel content — **bucket-brigade temporal credit assignment** (winner pays the previous step's winner) — requires a multi-step **live-reward episode with N concurrent agents**, incompatible with our sequential single-config trial policy + no-concurrent-inference rule. **No decision-aware-routing action** (routing is single-shot). The one portable item is a ~60-LOC `SpeciesLedger` replacing `rebalance()`'s hand-tuned constants with a rent+reward `softmax(wealth)`, gated behind `AUTOPILOT_SPECIES_LEDGER=shadow` for ≥80 trials and likely to DROP (same Pareto signal). Lesson: many MAS papers are economic *vocabulary* over machinery a Pareto-archive optimizer already has — check the existing selection loop before "adopting the pattern."

**RLM structured-output contracts (intake-693, AVB/fast-rlm) — parent, batched-child, and single-delegate REPL schema contracts are shipped.** The pattern: forcing each subagent to return a JSON-Schema-constrained value (validated on `FINAL`) so the parent reads a typed flag instead of parsing prose — booleans act as an "external attention mask," cutting aggregator hallucination on fan-out. Mapping it to our code: the **parent** mechanism (schema-normalize → contract-at-REPL-step-0 → validate-on-`FINAL` → retry-with-errors) was already lifted from the same fast-rlm commits on **2026-05-20** under flag `final_schema_validation` (`src/features.py:134`; `_render_schema_preamble`/`_validate_final_answer`/`_format_validation_failure_message` in `src/graph/helpers.py:1266-1316`; 2-attempt retry at `repl_executor.py:549-565`). The batched child path shipped in `18b5ceb`, and the single-delegate REPL path shipped in `6426dd4`. Parallel delegation still rejects `schema=`, so any future child-schema work should be justified by fan-out-heavy eval evidence rather than reopening the shipped single-delegate/batch contract.

Sources: [`research/deep-dives/2026-06-12-economy-of-minds.md`](../research/deep-dives/2026-06-12-economy-of-minds.md), [`research/deep-dives/2026-06-12-rlm-structured-output-contracts.md`](../research/deep-dives/2026-06-12-rlm-structured-output-contracts.md), [`handoffs/active/autopilot-continuous-optimization.md`](../handoffs/active/autopilot-continuous-optimization.md), [`handoffs/active/tool-use-eval-contract.md`](../handoffs/active/tool-use-eval-contract.md), intake-692/693.

## Agent-harness intake cluster — mostly-covered, three net-new deltas (2026-06-20)

A 2026-06-19 research-intake batch surfaced four agent-harness/delegation products. Three (Centaur, eve, ruflo) are production-maturity packagings of primitives EPYC already tracks; OpenRouter's subagent tool confirms a primitive EPYC already ships. The disciplined output is one design note, one out-of-scope flag, and one concrete remaining feature-mine — not a re-adoption of already-covered patterns.

**Recurring lesson (cf. the 2026-06-12 Economy-of-Minds finding):** mature agent products mostly re-package the same harness primitives — durable park/resume, scoped subagent delegation, zero-registration tools, swarm memory. Before recording a "pattern to adopt," map each named primitive onto the existing handoff/code line that already covers it; what survives that mapping is the only real delta.

- **Centaur (intake-696, paradigmxyz, MIT)** — net-new = placeholder-credential **egress proxy**. Agents see only placeholder secrets; a mitmproxy-style "iron-proxy" injects the real secret on authorized outbound requests (1Password runtime resolution). Recorded as a credential-hygiene design note: the agent process never holds live secrets, so prompt-injection exfil leaks only placeholders. Everything else duplicates HOS-Pattern-S (harness adapter), the A2A internal/external split (durable child workflow), and the child-agent delegation/swarm Key Questions; the k3s per-conversation sandbox is out-of-scope (no Kubernetes on single-host EPYC).
- **eve (intake-697, Vercel)** — productized successor of vercel-labs/open-agents (intake-397). Durable park/resume, hierarchical subagent delegation, zero-registration tools, conditional skills, eval-on-deploy are all already enumerated in the vercel-open-agents deep-dive and carried in hermes-outer-shell / tool-output-compression / tool-use-eval-contract. **No net-new lift.** (eval-suite-on-deploy, if pursued, belongs to the eval-tower, not the meta-harness.)
- **ruflo (intake-700, ex-Claude-Flow)** — every named primitive already covered (`strategy_store` + ReasoningBank memory, SiliconSwarm sharing, BT consensus, pi-agent-core hooks). Only net-new = zero-trust cross-machine federation (mTLS / ed25519 / PII-gating), **out-of-scope** for single-host single-user EPYC. Self-published 1.3×–1953× benchmarks are vendor observations, not decision-gating. Note the recent CWE-78 patch if its hook-shell surface is ever inspected.
- **OpenRouter subagent server tool (intake-705)** — provider-hosted stateless scoped delegation (worker sees only `task_description`; model + per-request task cap pinned at configure time). EPYC's `src/api/routes/chat_delegation.py` already does this server-side in software (architect→specialist, role pinning, per-request loop/token caps, depth guard), and the batched structured-return contract shipped in commit `18b5ceb` (2026-06-14). **Real remaining delta: a cost-aware capable→cheaper-worker delegation MODE** — a capable model spending input-only tokens to hand a self-contained subtask *down* to a cheaper/faster worker under a per-request task cap. This is the one feature-mine worth carrying forward from the cluster.

Sources: [intake-696](https://centaur.run/) · [intake-697](https://vercel.com/eve) · [intake-700](https://github.com/ruvnet/ruflo) · [intake-705](https://openrouter.ai/docs/guides/features/server-tools/subagent) · [`handoffs/active/hermes-outer-shell.md`](../handoffs/active/hermes-outer-shell.md) (agent-harness cluster) · [`handoffs/active/tool-use-eval-contract.md`](../handoffs/active/tool-use-eval-contract.md) (intake-705 / 18b5ceb update) · `research/intake_index.yaml` intake-696/697/700/705 · epyc-orchestrator `src/api/routes/chat_delegation.py`, `src/repl_environment/combined_ops.py` (commit `18b5ceb`).

## Architect→Reviewer control plane — dormant-machinery activation + 13-dive evidence base (2026-07-16)

The operator's deep-research report proposing a formalized Architect→Reviewer control plane was audited against the stack and landed as a 10-handoff series ([`reviewer-control-plane-index.md`](../handoffs/active/reviewer-control-plane-index.md) H0 + 9 leaves; intake-834..849). Durable findings for this category:

- **The review-governance layer is a real gap in the public ecosystem — and it was already half-built here.** No framework or vendor guidance ships typed reviewer decisions with bounded authority + false-accept/false-reject calibration (confirmed against the Anthropic engineering set, intake-846, and the intake index). Locally, `ArchitectReviewService` + typed `ReviewDecision` existed behind OFF flags, the trace store was scaffolded unmaterialized, and the autopilot already ran a planner/read-only-critic split — the series ACTIVATES rather than builds (audit doc `research/deep-dives/2026-07-16-architect-reviewer-control-plane-audit.md`).
- **Two-turn reviewer is the load-bearing architecture on CPU economics.** Rubric AUTHORING is expensive and capability-sensitive; GRADING is near-free and capability-insensitive (2.4pp across judge tiers) — so the heavyweight (GLM-5.2-IQ2 target / 122B-IQ2 interim) authors cached per-domain rubrics and a cheap model grades every candidate (intake-834, ACL 2026; deep-dive `2026-07-16-agentic-rubrics-two-turn-reviewer.md`).
- **Overcorrection, not permissiveness, is the measured reviewer failure mode** (false-reject ≫ false-accept 10:1-440:1; explain-then-fix prompting doubles it) → symmetric FA/FR e-processes, reject-admissibility (objective evidence or down-weighted), CandidatePackage sanitization, pointwise-only grading (intake-836/837/838; deep-dive `2026-07-16-reviewer-calibration-evidence.md`).
- **Verifier precedence is conditional on conclusiveness**: solver-in-loop delivers step-function gains (10%→93.9%) where claims are encodable, but formalization incompleteness yields ~15% false-positives → three-valued outcomes (PASS / FAIL-with-certificate / INCONCLUSIVE), certificates as the request_evidence payload (intake-842/843).
- **Debate does not survive our regime** (strong judge, no information asymmetry: martingale null; consultancy degrades judges) → escalate-default, single two-sided rebuttal only as a per-task-class gated option (intake-840/841).
- **Framework verdicts** (deep-dive `2026-07-16-framework-adoption-shortcuts.md`): LangGraph = adopt_component (SqliteSaver + interrupt via the pre-existing dormant bridge; our persistence.py was write-only); OpenAI Agents SDK = mine_patterns ×7 (we're AHEAD on shadow/warn-only + priority-ordered bindings); OpenHands = strongest-surface/weakest-orthogonality HS-4 candidate + EventStream blueprint for a future untrusted-code tier; MetaGPT = contract-shape mining (reviewer-no-authorship independently validated).
- **Standing floor**: the whole plane must beat a single augmented LLM on the same tasks (multi-role tax is 2-3× cost / 8-10× latency in the critique lit; single-host parallel review costs SUM not MAX) — enforce-mode is blocked on the H-LB budget gate; the 2026-07-16 plan-review 2× regression is the cautionary instance.
- **The 2026-07-17 spec tightens the control plane into a bounded runtime-assurance layer, not a second general-purpose loop.** The reviewer cannot mutate authoritative artifacts; decision envelopes are immutable and replayable; `REQUEST_EVIDENCE` is the only bounded feedback path; and authority is criterion-scoped with separate logical-vs-execution status plus per-domain assurance profiles. Sources: `research/deep-dives/2026-07-17-local-architect-reviewer-control-plane-spec.md`, `progress/2026-07/2026-07-17.md`.
- **The spec response landed as a bounded semantics layer, not a new open-ended loop.** Implementation commit `43a77eaf` adopted the control-plane spec with four scoping amendments: additive v1.1 fields instead of a six-schema rewrite, one enforcement authority per plane, shadow mode pinned to the existing CPU architect alias, and the new semantics layer kept below existing behavioral levers. The landed surface adds immutable/replayable decision envelopes, the reducer, `evidence_item` / `decision_envelope` / `assurance_profile`, hash-bound invalidation, and a durable escalation sink; shadow remains flag-gated and does not mutate authoritative artifacts. Source: `research/deep-dives/2026-07-17-control-plane-spec-audit-response.md`.

Sources: [`handoffs/active/reviewer-control-plane-index.md`](../handoffs/active/reviewer-control-plane-index.md) (+ 9 leaf handoffs, same date) · `research/deep-dives/2026-07-16-architect-reviewer-control-plane-audit.md` · `research/deep-dives/2026-07-16-reviewer-calibration-evidence.md` · `research/deep-dives/2026-07-16-agentic-rubrics-two-turn-reviewer.md` · `research/deep-dives/2026-07-16-framework-adoption-shortcuts.md` · `research/deep-dives/2026-07-16-plan-compliance-verification-debate.md` · `research/deep-dives/2026-07-17-local-architect-reviewer-control-plane-spec.md` · `research/intake_index.yaml` intake-834..849 · master-index §A00 OP-5 (operator decisions pending).

## 2026-07-17 — Agent-authored artifacts fail silently on grounding and coherence, not on schema

Two adversarial-audit findings from the inference-batch campaign. Both are failure modes that PASSED the obvious validators (schema, lint, freshness) and were only caught by a second, deliberately-adversarial pass — so both generalize into standing gates for any agent-produced artifact.

- **Command-fabrication: sub-agents that author execution commands from *semantic intent* produce plausible-but-ungrounded commands, and schema+lint cannot catch it — only `--help`/execution grounding can.** The consolidated inference-batch manifest (52 entries authored by four sub-agents) passed schema+lint, yet an adversarial command-audit found a large fraction of `execution.command` strings cited runners/flags/recipes that exist nowhere on disk (no `eval_tower.py replay` CLI = ~11 entries, no `bench_canonical.sh --recipe` flag = ~6, 7 missing helper scripts). Root cause: the agents wrote commands in a *plausible naming convention* from intent without grounding a single flag against `--help`; the YAML is well-formed, so structural validators are blind to it. The durable rule: **adversarial command-audit (execute or `--help`-check every authored command) is a required gate before an agent-generated command manifest is trusted** — an authored command is a hypothesis until a real binary accepts its flags. Companion rule: a **5-pass ground-truth-on-disk re-audit** (commands / provenance / preconditions / graph / committed-code) *localizes* fabrication rather than discarding all authoring work — here it confirmed the damage was confined to leaf command-strings (provenance ~98% grounded, 0 fabricated files, committed modules 0 stubs / ~440 tests green). Sources: [inference-batch-loop.md](../handoffs/active/inference-batch-loop.md), [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).

- **Derived-view incoherence: a freshness/age contract detects staleness but is structurally blind to VALUE-divergence, and atomic writes stop torn reads but NOT lost updates under concurrent read-modify-write.** After a prior "freshness contract" fix, the `:8000` autopilot dashboard went incoherent again. A 5-hypothesis adversarial root-cause found the freshness contract is only a read-layer AGE detector — it never compares source *values*, so two disagreeing-but-fresh representations both read "fresh" (H5, confirmed). The real divergence sources were concurrency, not staleness: **H4** — `autopilot_state.json` is rewritten by 5+ processes with per-write atomicity (`tmp`+`os.replace`) but ZERO mutual exclusion, so concurrent read-modify-write silently *loses updates* and state drifts from the append-only journal; **H2** — the earlier coherent-snapshot fix covered only the live-inference plane, so the four autopilot panels shared no snapshot epoch. Fixes: a `state_lock` cross-process **flock** + daemon control-field merge (H4), a shared `state_generation` **snapshot epoch** + `/autopilot_snapshot` endpoint (H2), and a **value-consistency divergence axis** added alongside the age axis (H5). H1 (non-atomic writes) and H3 (shard race) were refuted. Generalizable lesson: **coherence of derived views needs three independent guarantees — atomicity (torn-read safety), cross-process mutual exclusion (lost-update safety), and a shared snapshot epoch — plus a value-divergence check; an age/freshness contract supplies none of them.** Sources: [inference-batch-loop.md](../handoffs/active/inference-batch-loop.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md), [bulk-inference-campaign.md](../handoffs/active/bulk-inference-campaign.md).


## Adapter-protocol dispatch: presence vs None-ness (2026-07-25)

**Gotcha with a five-month silent-failure precedent.** GEPA's reflective mutation selects the
proposer with `if self.adapter.propose_new_texts is not None` (`reflective_mutation.py:66-67`),
while `GEPAAdapter` declares the hook as a **class attribute defaulting to `None`**
(`gepa/core/adapter.py:180`). EPYC's `OrchestratorGEPAAdapter` instead defined it as a *method*
that raised `NotImplementedError` to signal "use the built-in proposer" — but **a bound method is
never `None`**, so the check always took the adapter branch and raised **before any LM call**.

Cost: `633 s and 50 evals burned per invocation for a guaranteed no-op`, from ≥2026-06-04 until
2026-07-25, logged at INFO as a normal `0.718 → 0.000` completion. Fixed by declaring
`propose_new_texts = None`. Deleting the attribute would have been wrong — the class does not
inherit the protocol, so a missing attribute turns the same check into an `AttributeError`, and
`gepa/api.py:231` separately uses `hasattr()` to decide whether `reflection_lm` is mandatory.

**Transferable rule**: when an optional hook is declared as a protocol *attribute*, opt out by
setting it to the declared default — never by defining a raising stub. Check whether the consumer
dispatches on presence (`hasattr`), identity (`is not None`), or both; they can disagree.

**Second defect in the same file**: passing a reflection LM as a model-id *string* is
unroutable to a local endpoint. GEPA's string path builds its own wrapper calling
`litellm.completion(model=..., messages=...)` with **no `api_base`** (`gepa/api.py:242-244`), so
litellm's resolution order falls through to `https://api.openai.com/v1`. Pass a **callable**
carrying `api_base` instead.

_Sources: `handoffs/active/autopilot-continuous-optimization.md` § 2026-07-25;
`handoffs/active/intake-derived-work-2026-07-25.md` ID-1; `progress/2026-07/2026-07-25.md`._

## Driving another agent's TUI is a transport with no delivery receipt (2026-07-28)

Coordinating N agent mains on one host eventually needs one main to *say something* to another.
Where the peer is an interactive TUI (Claude Code, Codex CLI) in a tmux pane, the transport is
`tmux send-keys` — and it has no acknowledgement. tmux reports whether the *keystrokes* were
delivered to the pane, never whether the TUI *accepted* them, so the naive implementation reports
success for a message that is sitting unsubmitted in someone's composer. Three fix attempts on
`scripts/coordination/tmux_adapter.py` produced a transferable model.

**Measured TUI behaviour** (disposable sessions, 2026-07-28; Codex CLI v0.145.0, Claude Code
v2.1.220). One `send-keys -l` call is rendered as typed text below a length threshold and as a
*paste attachment* at or above it: Codex 1000 → typed, 1001 → `[Pasted Content 1001 chars]`;
Claude 800 → typed, 805 → `[Pasted text #n]`. Above the threshold content is also **lost** — Codex
truncates such blobs at 1024 chars, so 1498- and 2998-char bursts both render as 1024. Splitting
the message into 400-char chunks with a **0.15 s gap** renders as ordinary typed text with no blob
and no loss, verified to 12,000 chars on both TUIs; a 0 s gap re-coalesces into one burst and blobs
again. The gap, not the chunk size, is the load-bearing part.

**The verification predicate.** The terminal cursor sits at the end of pending input in both TUIs,
and overlays (plan confirmations, agent pickers, file pickers) render *below* it — so "everything
up to the cursor" is a stable anchor that a row-window heuristic is not. Matching must be
whitespace-insensitive because both TUIs soft-wrap the composer and a wrap can fall inside the
matched fragment. Both TUIs **echo a submitted message into the transcript**, so "the text is still
visible" is the *success* rendering, not a failure — a pane-wide search for the message inverts the
verdict on every good send.

**Absence is not delivery — the rule that generalises.** Post-Enter, "the message is no longer at
the cursor" is *not* proof it was submitted: an Enter consumed by a completion overlay rewrites or
extends the composer and leaves a pane byte-for-byte identical to success. Success must be
*positive* evidence (the transcript echo), and where a mode makes the outcome undecidable the input
is refused up front rather than classified after the fact — messages containing `@` or starting
with `/ ! #` never get typed, since those put the composer in a mode where Enter accepts a
completion or, for `!` in Claude Code, **executes a shell command** in the peer's session.

**Cap what costs something.** The same adapter capped spawns with a daily action count, so closing
an idle main never returned its slot — punishing exactly the lifecycle behaviour the system asks
for. Concurrency caps belong on the live resource (windows that exist now), not on the rate of the
action that creates it.

**Fail-closed is a per-branch property, not a posture.** Four defects in this one file (C3, C6, C8,
C9) were all the same shape: a query that could not be answered was treated as a benign answer —
missing inbox → drain succeeded, unreadable pane → nudge confirmed, failed window list → zero mains
live. "I could not determine X" must return unknown and refuse, never an empty set or a zero.

_Sources: `handoffs/active/session-bus-thin-dispatcher.md` § M5 → C6, C9, C10–C15;
`progress/2026-07/2026-07-28.md`; `scripts/coordination/tmux_adapter.py` (commits `8033f039`,
`e0deeaf7`, `8cbe50c0`); `coordination/session-bus/tasks/bus-c6-verification-followup.md`._

## Three ways a test suite reports coverage it does not have (2026-07-29)

Companion to the TUI-transport section above: same module, same week. Hardening one small
grant-gated adapter surfaced three distinct mechanisms by which a green result meant nothing. They
are worth naming because none of them looks like a bug — each looks like a passing suite.

**1. A fixture that deletes the signal under test.** Post-submit verification had to observe that
both TUIs echo a submitted message into the transcript. The end-to-end fixture cleared the screen on
submit (`\033[2J\033[H` after `read`). No real TUI does that, and the echo is exactly what the
predicate reads — so the fixture would have passed an implementation that cannot distinguish a
submission from a swallowed Enter. **Audit what a fixture removes, not only what it reproduces.**
The same bug was then found in a second file the next day, which is how you know the rule
generalises.

**2. A suite that cannot fail.** A standalone suite recorded results by appending `(ok, why)` tuples
to a module-global list that only its `main()` inspected; its two pytest-visible functions returned
`None`. Collected, it would have reported PASS with every check failing. It was also *uncollectable*
— it shared a basename with another test file and neither directory was a package, so pytest raised
`import file mismatch`, **a collection ERROR that aborts the entire run** rather than skipping one
file. Uncollected-and-red for a day; the repair had to make it both collected *and* capable of
failing, in that order.

**3. A result that depends on where you stand.** Two agents reported different pass/fail counts for
the same commit with the same interpreter. Cause: `/workspace` and `/mnt/raid0/llm/epyc-root` are one
tree (same `.git` inode), but ratifier scripts compare the invocation path against the *literal*
canonical root as a trust-boundary guard. From one name the guard passes and the suite is green;
from the other it fires and three tests fail on the wrong refusal message. Path-dependence also
changed *what ran* (615 vs 618 tests) and how long it took, because the guard short-circuits a
network validation. **The guard was left alone** — a production ratifier declining to accept a
second name for the production root is the check working. The fix is to quote the invocation path
with any tally, not to loosen the boundary.

**The structural precondition for all three.** A bare repo-wide `pytest` collected 2200 tests and
then aborted on 46 collection errors, so there was no whole-repo run for anything to be red *in*.
Fixing that (exclude non-repo trees from recursion; make an unimportable package importable) is what
turned "green" into a claim with a denominator. One subtlety worth keeping: `tests/` had no
`__init__.py`, and **a namespace package loses to a regular package found anywhere on `sys.path`,
regardless of order** — so `import tests.compliance` resolved to a *different repository's* `tests`
package reached through a shared venv. Putting the repo root first on `sys.path` does not fix that;
only making the directory a real package does.

**Transferable rule.** A passing suite is evidence only if you can state what would have made it
fail. For each of the three: delete the echo → the predicate still passes (bad); flip a check to
False → the test still passes (bad); run from the other path → the count changes (bad). Each was
found by asking that question, not by reading the tests.

_Sources: `handoffs/active/session-bus-thin-dispatcher.md` § M5 → C6, C9, C10, C14, C16, C19;
`progress/2026-07/2026-07-28.md`; `progress/2026-07/2026-07-29.md`; commits `bf1adb94`, `536839d3`,
`42884724`, `97955ac8`._

## Compiled Update — 2026-07-29: the harness is a first-class, re-targetable layer — and a merged fix is not a running fix

**Confidence**: verified for the first-party coordination findings (each observed
by running the system); **observation-grade** for the external harness figures,
which are n=1 per cell on closed frontier models and gate nothing.

### Harness decomposition and the Harness Card

Two independent taxonomies converge on making the scaffold an auditable object
rather than an implementation detail. A six-dimension decomposition — **context
assembly / tool interaction / generation control / orchestration / memory
management / output processing** — is extended by a seven-layer variant that adds
**Observability** and **Governance**, and both propose a **Harness Card** as a
disclosure schema. The adopted action is an audit table recording, per dimension,
which parts of our Layer-B surface are **editable** versus **hard-coded** — a
table, not a code change.
[`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) §HS-6

### Re-targetability outranks per-model tuning (operator, 2026-07-29)

The fleet is upgraded as better open-weight models land, so **harness policy must
survive a freeze change**. This is a standing selection criterion: a design that
expresses run-level policy as an **editable natural-language document** with
mechanisms in code ranks **above** a model-specific experience bank, even when
the latter has the stronger headline numbers. Anything proposing to bake
per-model behaviour into the harness is measured against this criterion first.
[`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) §HS-7

The measured reductions attached to the policy-as-document pattern —
60.10k→2.90k tokens / 68→3 files; 47.50k→1.40k / 5→1; 10.50k→0.80k / 3→1 — are
to be carried as **design**, not as numbers: every arm ran on a closed frontier
mini model. The open transfer question is whether an **open-weight** model can
*interpret* such a policy document faithfully; their own adherence metrics
(Workflow Preservation, Stage Coverage, Ordered Workflow, Artifact Contract, Tool
Call Success, Information Handoff Recall) score adherence **without** a benchmark
score, so drift is measurable on saved traces and is deterministic-replay
eligible. Their own red flag: **Information Handoff Recall drops to 0.32/0.55
under parent-child execution even on a frontier model** — the exact topology our
sub-agent delegation uses.
[`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) §HS-8, §HS-9

### Capability versus harness — both halves or neither

A one-step **model** swap buys ≈**3.6×** the full textual→verification harness
ladder and a one-step **reasoning-budget** bump ≈**2.0×**; but at **fixed** model
and effort a harness *revision* moved **+7.23**, larger than the entire
5.08-point architecture spread at that setting. Harness engineering at frozen
capability is **first-order, not marginal**, and this is the direct empirical
support for the re-targetability position above. The previously relayed "~6×
more bought by capability than architecture" reading was **wrong** — the figure
behind it was the verification-minus-simplification margin, **one rung of the
ladder**, not the architecture axis.
[`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) §HS-12;
[`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) §Records corrected

### "Present-but-uninstructed": a mechanism in a repo carries no measured result

A verification primitive (`plan_executor.py` — simulate the plan in the induced
world model, execute step-by-step, compare predicted versus observed state after
each non-terminal step, halt and dump artifacts on the first divergence) exists
in a published agent system, but **none of that system's agent-facing prompts
mentions it or requires its use**. It is therefore not what the paper measured
and no reported number attaches to it. Reading a capability off a repository's
file listing is unsound in the same way reading a fine-tune's architecture off
its `config.json` is (see [Speculative Decoding](speculative-decoding.md)):
**presence is not participation**. The pattern is still worth mining — pure
Python, no GPU, no Docker — but as an implementable design we would have to
measure ourselves.
[`agent-world-env-synthesis.md`](../handoffs/active/agent-world-env-synthesis.md) §Research Intake Update 2026-07-29

### A merged fix and a running fix are different states

Three separate **activation gaps** landed on one file in a single day: a fix was
committed, reviewed and tested, and remained **inert** because the long-running
coordinator daemon carrying the old code had not been restarted. "Landed" and
"active" are two states and only the **process owner** can close the second.
Corollaries recorded from the same arc:

- **Derive state from what is observable, never from a field somebody must
  maintain.** Reachability now consults liveness (a live window in the tmux
  session, else heartbeat freshness) rather than roster metadata; a roster row is
  a durable identity and a session is not.
- **Deliver-plus-warn, never refuse.** An inbox row is durable and a merely
  offline agent drains it on return, so bouncing on staleness converts transient
  offline into message loss — the opposite-polarity error. A false warning costs
  one visible line; false silence costs the defect.
- **A warning needs a reader.** The first fix wrote the defect notice to an
  advisory ledger that is delivered to no one, so the defect had two layers: a
  message in an inbox nobody drains, and a notice about it in a ledger nobody
  reads. The notice now also lands in the inbox of the party that can act on it.
  Idempotency is keyed on the notice's **own durable trace**, not on the ledger,
  because the ledger is written by the tick loop and any direct caller would
  re-notify on every pass.
- **Fail-closed startup dependencies belong on the reboot checklist.** The spawn
  adapter refuses when it cannot count live mains, and never creates its own tmux
  session by design — so after a reboot, spawning is dead until an operator
  creates the session by hand. That refusal reads like a defect and is not one.
  The wrong "fix" — treating an unreadable tmux as zero mains — hands out
  occupied slots.

[`session-bus-thin-dispatcher.md`](../handoffs/active/session-bus-thin-dispatcher.md) §C15/C17/C18/C20 and the post-reboot handover block

### Model choice is not the lever for a protocol gap

The multi-file coding shortfall remains diagnosed as a **protocol/tooling gap,
not a capability gap**, and the 2026-07-29 intake explicitly declines to reopen
the model-swap question on its back; the only thing pinned is *which artifact*
to use **if** a coder-role A/B is ever authorized for other reasons — and even
then, a spec-dec variant must not be bundled into a quality A/B, because that
confounds two axes.
[`multi-file-coding-completion-capability.md`](../handoffs/active/multi-file-coding-completion-capability.md) §2026-07-29 rider

### Source References

- [`harness-selection-and-integration.md`](../handoffs/active/harness-selection-and-integration.md) — HS-6 (six/seven-dimension decomposition, Harness Card), HS-7 (re-targetability as a standing criterion), HS-8/HS-9 (policy-as-document reductions; open-weight interpretation unestablished), HS-12 (both halves of the capability-vs-harness figure)
- [`session-bus-thin-dispatcher.md`](../handoffs/active/session-bus-thin-dispatcher.md) — C18 liveness/observability polarity and the "warning needs a reader" second half; C20 fail-closed reboot dependency; C15 key-conflation hazard; C17 scope resolution
- [`agent-world-env-synthesis.md`](../handoffs/active/agent-world-env-synthesis.md) — plan-executor divergence halt as a present-but-uninstructed mechanism; TaleSuite/Jericho as a public long-horizon eval
- [`multi-file-coding-completion-capability.md`](../handoffs/active/multi-file-coding-completion-capability.md) — protocol-gap diagnosis stands; artifact choice conditional on an authorized A/B
- [`progress/2026-07/2026-07-29.md`](../progress/2026-07/2026-07-29.md) — the corrected capability-over-architecture decomposition; staged-files-ride-along attribution hazard

## A correct guard whose answer is discarded: composition, not the check, is the defect (2026-08-03)

Three guards were found sound and non-functional on the same day, in three repos, for the same
reason. Each check was correct. Each *composition around it* threw the answer away.

1. **Secret scanning was advisory-only.** `.git/hooks/pre-commit` called its hooks bare:
   ```bash
   "…/pii_precommit.sh" "$@"
   "…/hermes_drift_precommit.sh" "$@"
   ```
   A bash script exits with its **last** command's status, so a failing PII hook was discarded by a
   passing drift hook. Reproduced in a throwaway repo: an AWS access key + secret staged, the hook
   printed `BLOCKED: [secret] AWS secret access key`, and **the commit landed**.
2. **A trust-boundary guard compared paths with a quoted right-hand side** — literal equality, not
   pattern matching. Literal entries matched, so it looked healthy; the one wildcard entry matched
   nothing, leaving three annexes agent-writable while the guard reported success.
3. **An attestation check consulted a mode-scoped map.** The expectation was compiled in one NUMA
   mode and the fleet ran another, so `slots_by_port` missed every half-instance port and the check
   fell back to a role-level number, reporting drift on four **correctly-launched** servers.

**The generalisable screen.** This project already runs *"can I pass this check by deleting the
thing it inspects?"* — which catches a gutted guard. It catches none of these. The complement is:

> **Does the thing that RUNS this check propagate its answer?**

Ask it of every guard's caller, not the guard. In all three cases the guard had its own tests and
they all passed; nothing tested the composition, and the composition was the defect.

**Corollary — a false alarm is a defect, not noise.** Case 3 was "non-functional" only in the sense
that launches were correct; its real cost is that a warning channel crying wolf on correct servers
teaches readers to ignore it, so the next *true* warning is lost. The function's own docstring said
so, and it had started doing exactly what it was written to prevent.

**Corollary — an untracked guard is an unguarded repo.** `.git/hooks/pre-commit` existed in **no
tracked code** in any of the three repos, despite each announcing "Auto-installed by epyc-root".
A fresh clone therefore had no hook at all, silently, and every fix reached one checkout. The same
shape appeared twice more the same day: `check_evidence_durability.py` — the enforcer
MEASUREMENT.md §5 names **by path** — was untracked, and three superseded SWE-eval JSONs sat
untracked in a repo root where they read as authoritative. **The artifact that proves a rule is
the one most likely to be missing from version control**, because it is written in the moment of
proving and never treated as deliverable.

_Sources: `handoffs/active/contention-model-device-and-load-axes-rider.md`;
`progress/2026-08/2026-08-02.md`; epyc-root `scripts/hooks/install_git_hooks.sh` +
`scripts/hooks/tests/test_precommit_wrapper.sh`; epyc-orchestrator `9e14c069`, `93e7f5a2`,
`cd76de50`._

## `Path(__file__)` cannot fix a leak in packaging (2026-08-03)

62 modules hard-coded an absolute checkout path, so a test run in a git worktree read the **main**
checkout's registry and priors — which is why a "clean baseline" run could not be trusted for
failure attribution. Converting them to `Path(__file__).resolve().parents[N]` fixed 53 of them and
**could not fix the rest**, for two reasons worth separating:

- **The root cause was a function, not a literal.** `_get_default_project_root()` *returned* the
  path, and ~14 modules resolved through `get_config().paths`. One line fixed all of them; grepping
  for the literal would never have ranked it above the other 61.
- **The last one was in packaging.** `pip install -e .` bakes the origin checkout's absolute path
  into the venv `.pth`. Every module's `Path(__file__)` is *correct* and still resolves into the
  wrong tree — because the wrong tree is what got imported. Source anchoring cannot reach one level
  below itself.

**pytest masked it**: rootdir is inserted at `sys.path[0]` and wins, so the suite was green
throughout and "the tests pass" was never evidence for this class.

Two traps for anyone repeating the sweep:
- **Quoting style is not a defect boundary.** A second leak in the same file used single quotes and
  matched neither grep pattern.
- **Check the tests themselves.** 12 test files ran `sys.path.insert(0, "<literal>")`, so a test in
  a worktree imported main-checkout `src/`. Those tests could not have measured their own tree even
  in principle — and two more asserted against the literal and would have newly *broken* once the
  config fix landed, passing only because the code under test leaked the same way they did.

Verification that made the sweep safe, and generalises: import every changed module pre- and
post-change and diff its path-valued constants (**172 identical, 0 divergent**); take the baseline
by checking `HEAD` into a throwaway worktree and requiring **byte-identical failure sets in both
directions**; and prove the property directly rather than by proxy — probed constants leaking to
the main checkout went **17/17 → 0**.

_Sources: epyc-orchestrator `5c061f58`, `93e7f5a2`, `cd76de50`; `progress/2026-08/2026-08-02.md`._
