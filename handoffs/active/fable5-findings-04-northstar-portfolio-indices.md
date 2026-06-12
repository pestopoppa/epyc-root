# Fable 5 findings 04 — North Star critique, backlog-relevance map, index reorganization (deliverables §8.2–8.3, §8.5)

**Date**: 2026-06-12. Inventory basis: all 7 indices read; 105 active / 1 blocked / 96 completed / 80 archived handoffs counted; ~75 outstanding workstreams classified; autopilot action surface verified in code (`actions.py:679-694`, `structural_lab.py:359-412`, `features.py:77-188`, `numeric_swarm.py:31-96`, `config_applicator.py:27-93`).

---

## 1. The North Star, critiqued clause by clause

> *"orchestration infrastructure agnostic to the specific models, cures itself organically, optimally learns to use every tool available — implemented and backlogged — to maximize inference task quality AND speed."*

1. **"Model-agnostic"** — aspirational, currently false, and no workstream owns the gap. Routing intelligence is keyed to the deployed stack and died with it once already (2026-05-25 reset invalidated classifier/GAT/SkillBank simultaneously; retrain still BLOCKED). The missing artifact is the **model-capability descriptor** (findings-02 §3): a versioned per-model vector compiled from the research registry. With it, a swap is a data update. Without it, "model-agnostic" means "rule-based fallback survives the swap" — which is what you actually have.
2. **"Cures itself organically"** — currently scoped only to the autopilot's own loop (mature: safety gate, WAL recovery, designed halts, exogenous-restart resilience). The **serving stack** self-heals not at all: gemma4 wedge needs manual SIGKILL, throttle remediation is "operator schedules weekly reboot", planner halts wait days for operator marks. And the deepest reading of "cures itself": the system cannot even *attest its own running state* (flags diverge per-worker, flag-on/weights-missing, stated≠running architecture — findings-02). Self-cure presupposes self-knowledge; add **running-state attestation** as the prerequisite clause.
3. **"Optimally learns to use every tool — implemented AND backlogged"** — the premise is half right and the half matters. Verified concretely: the autopilot's real toolbox is 14 action types, all 82 registry flags (via structural_experiment), 23 numeric knobs, prompts/code-mutation/KV-compaction. The backlog reaches the planner **only as a denylist** (`program.md:335-352` "Do NOT Propose"); the promotion pattern (backlog→surface) has run exactly once systematically (2026-05-20, 7 knobs + 3 flags); the declared "Stack-Config as Optimization Axis" table has **no implementing code**; and **~0% of the measured speed levers are autopilot-actionable** (draft_max/MTP/MoE-Spec/GGML_* env/binary choice/numa-mode are all launch-time, operator-only). Speed is half the objective; the optimizer holds almost none of its levers. *But*: do not fix this by "exposing everything" — per findings-01 the instrument cannot yet ratify what the optimizer already controls. Sequence: instrument first, then surfaces.
4. **"Maximize quality AND speed"** — missing two words: **"at measured confidence"** (else this clause licenses noise-mining, which is what trials 714–776 are) and missing a **workload model** entirely: optimal for *whom*? Today's de-facto workload is the eval harness itself plus batch campaigns (findings-02 §2.3, findings-03 §1.2). A North Star that doesn't name its traffic cannot define routing or serving optimality. Hypothesis #6 answer: **the framing to drop first is "the eval tower is fixed infrastructure"** (program.md froze the instrument while its resolution is the binding constraint); second, "single-user latency-first serving"; third, "the backlog is a TODO list" (split it: capability registry vs work queue).

**Proposed restatement** (for your consideration, not a mandate):
> *An orchestration layer that (1) can prove what is running, (2) measures its own quality and speed at known statistical confidence against a declared workload model, (3) treats models as swappable via capability descriptors, (4) exposes every safe runtime lever — including promoted backlog capabilities — to a self-optimizer whose evidence base is append-only and provenance-checked, and (5) detects and remediates its own serving pathologies without operator action.*

## 2. Backlog-relevance map (per recommended architectures; full inventory in agent report)

**Load-bearing (the recommended architectures make these MORE important):**
- `tool-use-eval-contract.md` — prototype of the eval-provenance discipline; generalize it into the standing instrument contract (and commit it — it is untracked in git, as is the fable5 brief).
- `eval-tower-verification.md` EV-8/9/10 — but re-sequence: power/pairing (findings-01) before calibration metrics.
- `retrain-routing-models.md` — becomes the descriptor-schema pilot; unblock via BGE re-embed (also the GPU's §2.3-alternative).
- `decision-aware-routing.md` DAR-4 bilinear — the ONE distilled predictor shape to keep (findings-02 §3/§4).
- `cpu-benchmark-rigor-and-revalidation.md` (CPU20) — promote from CPU-domain protocol to **system-wide measurement constitution**; it is the only place the project's metrology discipline is written down, and findings-01 is largely "apply CPU20 to the autopilot's own instrument."
- `gpu-drafter-mi200-investigation.md` + `gpu-acceleration-path.md` — keep, with findings-03 reordering (residency + eval-acceleration ahead of drafter farm; G1 α-measurement this week).
- `shape-keyed-contention-gating.md`, `within-role-placement-state-machine.md` — the safety layer; unchanged, healthy.
- `handoff-backlog-hygiene-audit.md` — raise from LOW/unassigned to the vehicle for §3 below.

**Reordered/demoted:**
- All learned-routing expansion (Trinity TR-4/5, outer-coordinator OC-*, LRC Phase 1.5+, SPO+/DAR-3) — **freeze until** per-question eval vectors exist and the DAR-1 regret replay justifies routing as a bottleneck (findings-02 §6). Predicted outcome: demoted for months.
- New eval *content* work (EV calibration, new suites) — after instrument re-powering.
- MTP-split, FastDraft, cross-tokenizer — stay gated (your own gates are right).
- `program.md` trim — **re-scope from token-budget task to integrity task** (findings-01 §2.4): generated system-card + short constitution.

**Obsolete / close (beyond the agent's dead-code list in findings-02 §4):**
- The 26 terminal rows still occupying master priority-queue slots; the 5 standalone-table rows pointing at completed/ files.
- `09-ouroboros-multi-model-validation.md` (blocked/, references deprecated stack) — archive.
- Index items serving no North-Star clause: readme-refresh row (done), repo-readiness-scorer, autowiki, agent-file-prose-compression's HIGH rating (it is ergonomics, not North Star) — keep the work if you like it, but stop letting it occupy HIGH slots in the queue an agent is told to execute top-down.

## 3. Index & handoff reorganization (deliverable §8.3 — concrete shape, not a task list)

**Diagnosis** (quantified): ~48% of the 56K words of index content is chronology; the master "Updated" header is a single 964-word line; 22 strikethrough rows; roughly half of all checkboxes across indices are completed work retained inline; the master index's own autopilot row was 8 days stale (said DOWN-at-500 while the system ran at trial 776). The indices have become **narrative stores** — the same disease as the autopilot's strategy store: history that outlives its facts, re-read by every agent, drowning the decision-relevant signal. Your own governance memory ("indices track only outstanding TODOs; chronology → progress logs") already states the cure; it isn't applied because nothing enforces it.

**Proposed structure** (apply the findings-01 fact/policy/narrative split to the doc system itself):

1. **Master index = dispatch + priority queue ONLY** (~60 lines): one table of LIVE rows (id, one-line item, actionable-by, gate, link), a 5-line "what changed this week" pointer into progress/, and the sub-index map. Everything terminal moves out on completion — no strikethroughs, ever. The 964-word header line becomes a progress entry.
2. **Domain indices keep the CLAUDE.md contract** (checkboxes/dependency-graph/cross-cutting/reporting/key-files — 5 of 7 already structurally comply) but are **regenerated views, not hand-grown logs**: research-intake appendices move to the intake index/deep-dives; completed checkboxes are pruned on completion (the pipeline index, 22 open / 3 done, is your existing exemplar — make it the template).
3. **Add one column to every index row: `actionable-by ∈ {operator, autopilot, either, gated:<gate>}`.** This single field operationalizes North-Star clause 3: it makes the toolbox/work-queue split explicit, makes "promote to autopilot surface" a visible state transition, and gives the (future) capability registry its source of truth. The 10-item promotion shortlist already exists in the agent report (spec-dec knobs, MoE-Spec budget, GGML env blocks, placement flags, contention flags, EA profiles, enable_thinking per-role, edit-transaction rollout, P21.B axis, stack-topology axes).
4. **Two new standing documents** (not handoffs — contracts):
   - `MEASUREMENT.md` — the system-wide instrument constitution (CPU20 generalized + the eval-tower contract + GPU canonical protocol when the card lands). Anything that produces a number cites its protocol here.
   - `ATTESTATION.md` (or a `gitnexus`-style generated artifact) — what is *actually running*: live flag state across workers, deployed binaries per role, spec-dec per role, index-vs-reality drift checks. Generated, never hand-edited.
5. **Lifecycle rule with teeth**: a handoff is `active` only if it has an unchecked actionable item AND an owner AND its Current-State header is <14 days old; else it auto-moves to `completed/` (extract-then-archive) or gets a `gated:` tag with the reopen condition. The freshness script exists; wire it to fail loud (65 aging today, growing).

## 4. Negative-space audit (§8.5)

**Delete / merge / freeze / stop optimizing:**
- Stop **adding guards to the autopilot pipeline** (12 sanitizers and counting) — each new one is rent paid on the missing ledger architecture.
- Stop **all learned-routing investment** until the regret replay says otherwise; delete the zero-caller trio; freeze GAT/SkillBank/SPO+ (findings-02 §4).
- Stop hand-curating `program.md`, `model_quality_signatures.yaml` (stale since 2026-04-16, read every trial), and index chronology — replace with generated views.
- Merge facets 1+2 permanently (this review's first act); merge the 14 research-intake appendices per index into the intake system.
- Freeze further T0 sentinel work — the gate is saturated and its harder half is dead config; fix or drop, don't extend.

**Most dangerous silent assumptions** (ranked):
1. *"The eval tower measures what we optimize"* — it measures a 43-question fixed set at 1–2-flip resolution; everything downstream inherits this.
2. *"What we configured is what is running"* — falsified three independent ways (test defaults live; 1-of-6 worker flags; flag-on/weights-missing).
3. *"The backlog will be wielded by the orchestration"* — there is no mechanism; only a denylist.
4. *"Single-user latency-first"* — the workload is mostly the harness itself.
5. *"The bandwidth wall is where our throughput story ends"* — frontdoor spec-dec was never turned on; batch class unexplored.

**Invariant interfaces the North Star actually needs** (the load-bearing five):
1. **Measurement ledger** (append-only, per-question outcomes, supersession, policy versions) — findings-01.
2. **Model-capability descriptor schema** (versioned; compiled from the research registry) — findings-02.
3. **Running-state attestation** (flags/binaries/spec-config across all processes, queryable) — findings-02 §2.2.
4. **Capability registry with `actionable-by` + applicator contracts** (incl. the missing safe role-restart applicator that would unlock the speed levers) — §1.3/§3.3.
5. **Workload model** (declared traffic classes: interactive / eval-batch / campaign; per-class SLOs) — findings-03 §3; without it "optimal" is undefined.

**Smallest decisive observations** (cheap, run soon, each kills or crowns a recommendation):
1. Replay 120 trials' keep/revert under McNemar with per-question vectors → if ≥30% flip, the sequential-instrument redesign is proven on your own data (findings-01 gate).
2. `reconstruct_archive_from_journal_rows` vs live archive diff → **RUN during this review (2026-06-12): T1 frontier matches exactly; T2 diverges — live {363} vs reconstructed {363, 367}. Drift is real; the event-sourcing case is proven on live data** (findings-01 §4).
3. DAR-1 regret replay on a current week → routing facet priority (findings-02 §6).
4. α(1.7B→frontdoor) on CPU → the GPU-drafter fork (findings-03 G1).
5. `GET /config` probe per uvicorn worker (add the endpoint) → how divergent production flag state actually is right now.

**Compounding vs optional bets:**
- **Compound now**: per-question ledger; descriptor schema; attestation endpoint; explicit prod-flag block; α measurement; GPU-as-eval-engine framing; index reorg (it is the doc-layer of the same architecture). All reversible, all multiply every later decision.
- **Optional until evidence**: drafter farm, learned-routing expansion, outer coordinator, MTP-split, multi-tenant serving, NPS/BIOS changes (your own closed investigations stay closed), DSA/DeepSeek ports (gated as documented).
