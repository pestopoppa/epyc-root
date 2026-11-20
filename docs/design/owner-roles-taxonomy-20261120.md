# Owner-Role Taxonomy (draft, 2026-11-20)

Read-only analysis. This was a sampling pass, not a full read. Commit counts are `git log --since=2026-07-01 -i --grep=<term>` in epyc-root, which has 14,440 commits since July. Over the same period epyc-orchestrator has 2,554 and epyc-inference-research has 2,785. These counts are proxies: terms overlap, so the same commit can count toward several terms.

## Evidence base
- `handoffs/active/` has 33 non-index program files and 6 domain indices: inference-research (17 rows), routing-and-optimization (11), research-evaluation (6), user-facing-harness (4), pipeline-integration (3) and reviewer-control-plane (3).
- The dispatcher registry (`/mnt/raid0/llm/tmp/compute-flags/handoff-sessions.json`) has **75 per-handoff sessions**. Its default engine is codex and `max_live` is 2. This one-session-per-handoff design is the fragmentation that owner roles would replace.
- Commit-term volume: autokernel 1199, wiki 599, intake 584, promotion 530, harness 504, vidya 499, dashboard 372, stack 328, autopilot 288, pipeline+churn 339, hygiene 109, speech 105.
- Existing role files are `agents/coordinator-agent.md`, `auditor-main.md` and `inference-main.md`. The bus roster (`coordination/session-bus/config.yaml`) assigns lanes to mains A–D plus the coordinator and auditor. It is lane-based, not domain-based.
- There are 364 memory notes. Most of them are re-learned lessons, and they cluster by domain, as shown below.

## 1. Work clusters → candidate roles

**A. autokernel** (being drafted). Mission: AutoKernel loops, champion accumulation, human-in-the-loop kernel levers, CPU/GPU roofline.
- Owns: autokernel-akx-program, autokernel-loop, kernel-champion-and-promotion (contributor only on its promotion half), cpu-decode-roofline-program, rocm-kernel-authoring, workspace-58-champion-calibration, quantization-and-low-bit, speculative-decoding (kernel side).
- Volume: the largest stream. 1199 commits and 9 registry sessions (`autokernel-*`, `akagg`, `agentic-rocm-kernel-authoring`, `iqk-iquant-enablement`, `mi210-*`).
- A long-lived dedicated session has held this stream, per the memory note feedback_codex_off_ak_autopilot_tracks.
- Lost knowledge: stale binaries (HYG-1/INF-70 C9, memory note feedback_stale_build_artifact), INC-20260925-parallel-repack-lost-in-bundled-revert, project_ak_64k_keep_did_not_replicate, the A3B GPU coverage gate.

**B. autopilot** (being drafted). Mission: the autopilot evidence plane, strategy store, journal and Pareto state.
- Owns: autopilot-program, eval-tower-program (shared with measurement work), scaffold-autopilot-cost-lever.
- Volume: 288 commits. The engine has been dormant since 2026-08-09 (project_autopilot_dormant_journal_audit_last).
- Lost knowledge: INC-20261109-autopilot-refresh-process-faults; rewinds must purge the strategy store; pause is a no-op; journal shards rotate, so all of them must be read.

**C. pipeline-mgmt** (being drafted). Mission: the rowflow, dispatcher, compute calendar and grant writers, results filing, and the handoff and index standard.
- Owns: churn-pipeline, coordination-and-churn-pipeline, dispatch-placement-telemetry, the backlog-priority json files, master-handoff-index and the six domain indices' liveness. It also owns the `inference-backlog-scheduling` skill.
- Volume: 339 commits and the sessions coordination-and-churn-pipeline and non-inference-backlog. This is where the incident rate is highest.
- Lost knowledge: INC-20261110-rowflow-switches, INC-20261024-subagent-took-cpu-region-without-grant, INC-20261024-codex-worker-ungranted-tests-in-quiet-block, INC-20261004-subagent-unlocked-cpu-in-held-window, and 10+ memory notes (book need+margin, QUEUED means runnable, watch published rows, demote on failure).

**D. harness** (user-facing harness, new). Mission: the orchestrator API (:8000), frontdoor, routing, REPL, MCP and chat, plus the reviewer control plane, i.e. everything a user's request touches.
- Owns: harness-program, routing-program, context-and-token-economy, memory-program, hybrid-checkpoint-prompt-reuse, long-context-program, reviewer-control-plane, thesis-experiment-orchestrator-vs-strongest-model, and the user-facing-harness, routing-and-optimization and reviewer-control-plane indices.
- Volume: 504 harness commits plus most of epyc-orchestrator's 2,554. Over 20 registry sessions are already in this cluster (`repl-*`, `routing-*`, `reviewer-*`, `harness-*`, `tool-output-compression`, `delegation-context-preassembly`, `unified-trace-memory-service`, `typed-decision-plane`, …). It is the most fragmented cluster, with no single owner.
- Lost knowledge: enable_thinking requires the chat-completions path; Qwen3.x needs enable_thinking=false; the API reloads alone, not the whole stack; and project_pending_api_reload (the STACK-UP RELOAD QUEUE).

**E. stack-and-kernel-release** (new, operator-gated). Mission: prepare stack changes (lineup, topology, registry) and kernel promotions as single signable packages, then run bring-up after the operator signs.
- Owns: stack-lifecycle-program, numa-placement-and-contention, model-evaluation-queue (the lineup decision end), v11-promotion-checklist (parked), the promotion attestations, model-registry-v5-deployment-draft, and kernel-champion-and-promotion's promotion half. Its tools are the skills stack-change, kernel-promotion, retire-model, change-role and change-topology.
- Volume: 530 promotion and 328 stack commits, in rare, high-stakes bursts.
- Lost knowledge: INC-20261003-start-dry-run-launched-stack, INC-20261003-runtime-flag-survived-reboot, INC-20260926-local-actor-bringup, INC-20260929-dry-run-missed-live-checks; ratify scripts must be apply-tested; a bring-up must exercise the consumer path.

**F. inference-research** (new; it evolves `inference-main.md`). Mission: model evaluations, benchmark suites, KV and long-context research, and speech/multimodal evaluation. It is a producer of rows, not their scheduler.
- Owns: inference-research-index, benchmark-suites, deepseek-v41-flash-evaluation, kv-cache-program, speech-and-multimodal, and the measurement side of the eval-tower.
- Volume: most of epyc-inference-research's 2,785 commits, plus model evaluation sessions (stt5, yarn, kvu, kvfork, exl3, ernie, tq3, mathsmith, document-parser…).
- Lost knowledge: llama-bench adding unrequested rows; label every throughput number; the speech corpus needs a human ear; YaRN must not regress the native window.

**G. knowledge** (new; merges research intake, wiki/KB and vidya). Mission: research intake through its four stages, the wiki and KB compilation, and the vidya belief kernel and cite-check.
- Owns: knowledge-pipelines, vidya-belief-substrate-program, research-evaluation-index, pipeline-integration-index.
- Volume: wiki 599, intake 584 and vidya 499 commits, the largest after autokernel. Sessions include vidya-belief-substrate, internal-kb-rag and intake-derived-work.
- Lost knowledge: an intake lane owns its leftovers; at most four Stage-2 waves; a medium-relevance item must get a deep dive; wire the write side immediately (benchmarks/results: 0 of 200 files usable).

**H. coordinator** (existing). Mission: cross-main sequencing, reboot recovery, bus routing and liveness.
- Lost knowledge: pane capture cannot detect compaction; reuse main aliases after a reboot; never kill a main to clear a block.

**I. auditor** (existing). Mission: independent review, closure-inflation checks and cite-checks. It owns no backlog by design.

**J. hygiene** (task class, not a role). Covers engineering-hygiene-backlog, disk/reclaim, earlyoom, clone symlinks, gitnexus and dashboards. Volume: 109 hygiene commits; dashboard has 372 commits, but they mostly follow subsystem work.

## 2. Candidate verdicts

| Candidate | Verdict |
|---|---|
| User-facing harness | **Role (D)**. It is the largest unowned code surface and also absorbs routing, REPL, MCP and reviewer work. |
| Stack lifecycle / bring-up | **Role (E)**, merged with kernel promotion. Both produce one operator signature, then bring-up and proof that the stack serves. |
| Kernel promotion | **Merge into E**. The operator executes it; E prepares it. AutoKernel only supplies the candidate. |
| Inference / benchmarks / compute calendar | **Split**: the research goes to F and the calendar to C (pipeline-mgmt). |
| Research intake | **Merge into G**. |
| Wiki / KB | **Merge into G**. |
| Vidya | **Merge into G**. It can spin out later if the substrate program outgrows G. |
| Measurement governance | **Not a role.** The constitution is human-amendment-only. Day-to-day application is a contribution duty of F and the auditor. |
| Speech / multimodal | **Merge into F** (the speech kernels are frozen; the remaining work is evaluation). |
| Dashboard / hub | **Task class.** Under the plane rule, each subsystem owner owns its own data contract. Hub chrome falls under hygiene. |
| Coordinator | **Keep the role** (existing). |
| Auditor | **Keep the role** (existing; spawned on demand). |
| Infra / hygiene | **Task class** with no owner. Pipeline-mgmt dispatches it as non-inference filler. |

## 3. Boundaries
- **Ownership versus contribution.** The owner role holds a handoff's checkboxes, index row and next action. Contributors deliver evidence or code and report to the owner over the bus. They never tick the owner's boxes (INVARIANTS: never tick another agent's checkbox).
- **AutoKernel → E.** AutoKernel owns the champion until it is "ready". E owns the promotion package. Per the memory notes feedback_promotion_operator_only and feedback_kernel_promotion, only the operator unparks v11 or signs.
- **Harness ↔ E.** The harness role owns API code. A reload of the running API belongs to whoever owns the inference at that moment (CLAUDE.md, *Reload ownership*). Changes to the lineup or registry go through E's stack-change package.
- **F ↔ C.** F authors rows and interprets results. C books, grants, watches and files them. A blocked inference row becomes code work for whichever role owns the blocker.
- **G ↔ everyone.** Every role that produces measurements owes G a write-side adapter row (CLAUDE.md, Belief Kernel section).
- **Exclusions.** Codex harnesses stay off A and B. E's apply and bring-up steps run only after an operator signature. Under ruling (b), subagents prepare index edits and the owning role applies them.
- **Shared handoffs:** eval-tower (B/F), speculative-decoding (A kernel / F evaluation), quantization-and-low-bit (A / F), model-evaluation-queue (F / E), and numa-placement (E / C). Each has one owner; the second-named role contributes.

## 4. Proposed role set (8)

| # | Role | Roster id | File | Model fit | Live? |
|---|---|---|---|---|---|
| 1 | autokernel | `autokernel` | new `agents/autokernel.md` | Top tier for lever design; cheap for loop babysitting | **Live** (long loops) |
| 2 | autopilot | `autopilot` | new | Top tier for strategy; cheap for journal audits | Spawned while dormant; live once relaunched |
| 3 | pipeline-mgmt | `pipeline` | new; absorbs the queue parts of `inference-main.md` | Mid tier; most of the work is mechanical, with judgment needed on packing | **Live** (standing watcher, owns idle compute) |
| 4 | harness | `harness` | new `agents/harness.md` | Mid tier for code (Codex-eligible); top tier for routing/reviewer design | Spawned on demand; live during bring-ups |
| 5 | stack-release | `release` | new; wraps the stack-change and kernel-promotion skills | Top tier (CRITICAL blast radius) | Spawned only for operator-gated events |
| 6 | inference-research | `research` | evolves `agents/inference-main.md` | Mid tier for evaluation; top tier for interpreting results | Spawned |
| 7 | knowledge | `knowledge` | new | Cheap or mid tier for intake and wiki; top tier for Stage 3 and the vidya design | Spawned (intake batches) |
| 8 | coordinator | existing coordinator id | `agents/coordinator-agent.md` | Mid tier | **Live** whenever two or more mains run |
| (+) | auditor | existing auditor id | `agents/auditor-main.md` | Top tier, independent | Spawned |

The current mainA–D lane ids should become harness slots that host roles. They should not be roles themselves.

## 5. Gaps
- **No plausible owner yet:** engineering-hygiene-backlog (proposed: a C-dispatched task class); laguna-pgpu1-v8-promotion-attestation.json and v9-kernel-promotion-attestation.json, which are historical and should move to `completed/`; and the `backlog-priority*.json` files, which are data owned by C, not handoffs. Of the 75 registry sessions, about 15 map to no active handoff, including fable5-window2, frontier-f6-upstream-publication, publication-upstream, paw-compiled-specialists, rao-redel and minddr. They need either an owner or retirement.
- **Upstream publication** (2 sessions) has no home. Proposal: E, since it ships kernel patches upstream.
- **Roles with little backlog:** autopilot is dormant (its only live box is the journal audit); stack-release is idle between signatures; the auditor owns nothing by design. None of these should get a permanently live session.
