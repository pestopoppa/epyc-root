# Agentic World Modeling — Levels × Laws Taxonomy as Referee Framework for the EPYC Autopilot Stack

**Intake**: intake-498
**ArXiv**: 2604.22748 (submitted 2026-04-24, cs.AI)
**Categories**: agent_architecture, autonomous_research
**Status**: deep-dive (written 2026-04-28)
**Companion repo**: github.com/matrix-agent/awesome-agentic-world-modeling (105★, 2 watchers, 1 fork — bibliography aligned to the L×R grid; no released eval package)
**Cross-refs**: intake-444 (Agent-World, primary subject of `agent-world-env-synthesis.md`), intake-413 (HCC), intake-244 (Meta-Harness), intake-411 (Qwen-Agent MCP), intake-412 (DeepPlanning), intake-148/149 (AutoResearch loop)
**Parent handoff**: [`agent-world-env-synthesis.md`](../../handoffs/active/agent-world-env-synthesis.md) — primary integration; see also `autopilot-continuous-optimization.md`, `meta-harness-optimization.md`

---

## 1. Why this entry exists

The intake scoring placed this paper at medium novelty / medium relevance / `worth_investigating` — appropriate for a survey. A full read of the section structure and Section 5.4 (L3 governance) reveals that **one specific recipe inside the paper is directly actionable today**: the "governed validation: updates pass regression and robustness gates (including rollback and canary policies)" framing for L3 Evolver systems maps almost line-for-line onto the autopilot SafetyGate + Pareto archive + tiered eval tower we already run. That promotes the practical relevance from "framing only" to "we should explicitly adopt the L1/L2/L3 vocabulary and the four evaluation principles as autopilot reporting conventions, gated on a low-cost adoption window."

That said: the paper is still a survey with no released code, no released benchmark, and no first-author single point of accountability. The actionable ask is **vocabulary adoption and evaluation-principle integration**, not "build something new". The GPU-gated angle is that the paper contextualizes Agent-World (intake-444 / `agent-world-env-synthesis.md`) — whose Phase 2 multi-environment GRPO training is GPU-gated — by giving Phase-1 ETD work a place on the L×R map.

---

## 2. Authors and provenance

42 authors across 9+ institutions:

- **Hong Kong University of Science and Technology** (7) — including Jiaya Jia (cross-listed), Qifeng Chen
- **National University of Singapore** (8)
- **University of Oxford** (3) — Philip Torr senior
- **Nanyang Technological University** (2) — Ziwei Liu senior
- **Chinese University of Hong Kong** (3) — Jiaya Jia senior
- **University of Hong Kong** (2)
- **University of Washington** (2)
- **Singapore University of Technology and Design** + **Singapore Management University**

**Core contributors (†)**: Meng Chu, Xuan Billy Zhang, Kevin Qinghong Lin, Lingdong Kong, Jize Zhang, Teng Tu, Weijian Ma.

**Senior authors (§)**: 15 marked, including Qifeng Chen, Ziwei Liu, Philip Torr, Jiaya Jia.

**Provenance read**: this is a HKUST/NUS-anchored consortium with Oxford/NTU/CUHK senior involvement. The 42-author single-paper format is unusual outside of survey/benchmark consortia (cf. BIG-bench, HELM). The presence of established senior figures (Torr, Jia, Liu) in the senior author list provides credibility for the framework's seriousness, but the lack of a tight author group reduces accountability for taxonomic precision — sections may have been written by different sub-teams and reconciled rather than co-developed. (See `feedback_credibility_from_source_not_readme` — applies to long surveys too.)

---

## 3. Section structure

| Section | Topic |
|---------|-------|
| 1-2 | Introduction, motivation, philosophical foundations, notation |
| 3 | L1 Predictor (one-step transition operators) |
| 4 | L2 Simulator (multi-step rollouts, includes Section 4.3 failure modes) |
| 5 | L3 Evolver (evidence-driven self-revision, includes Section 5.4 governance) |
| 6 | Evaluation methodology (Section 6.1: prediction → decision-centric shift) |
| 7 | Architectural and computational considerations |
| 8 | Trends, open problems (Sections 8.2-8.3 incl. "Beyond L3") |
| 9 | Conclusion |
| A-F | Philosophical grounding, conceptual boundaries, domain details, MREP design (Section E.6) |

**Where to read first** for EPYC purposes:
- Section 5 (L3 Evolver) + Section 5.4 (governance) — directly maps to autopilot
- Section 6.1 (decision-centric evaluation principles) — directly informs AR-3 evaluation gates
- Section 8.2-8.3 (Beyond L3, cross-regime transfer) — informs autopilot species framework evolution

---

## 4. The Levels × Laws taxonomy

### 4.1 Capability levels

| Level | Definition | One-line test |
|-------|-----------|---------------|
| **L1 Predictor** | Learns one-step local transition operators p(s_{t+1} \| s_t, a_t) | "Given current state and action, predict next state" |
| **L2 Simulator** | Composes L1 operators into multi-step, action-conditioned rollouts that respect domain laws | "Given a plan, generate a coherent trajectory long enough to act on" |
| **L3 Evolver** | Autonomously revises its own model when predictions fail against new evidence | "When the model is wrong, the model fixes itself" |

The L1 → L2 → L3 axis is the genuinely novel contribution. Prior surveys group by modality (text/video/3D) or domain (robotics/web/code); this paper argues the capability axis cuts across both.

### 4.2 Governing-law regimes

| Regime | What constraints | Where it fails |
|--------|-----------------|---------------|
| **Physical** | Mass/energy conservation, contact, kinematics | Long-horizon physics drift, unmodeled friction |
| **Digital** | API contracts, file system semantics, rate limits, HTTP | Brittle locator/selector matching, race conditions, auth state |
| **Social** | Theory of mind, norms, multi-agent strategy | Distribution-shifted behaviour, identity collapse |
| **Scientific** | Formal models (PDEs, mechanism), measurement noise | Out-of-distribution composition, hidden confounders |

The four-regime axis is reasonable but not unprecedented; the *value* is the joint L×R grid as an organizing tool.

### 4.3 Representative systems on the L×R grid (selected)

| | Physical | Digital | Social | Scientific |
|--|---------|---------|--------|------------|
| **L1 Predictor** | Dreamer/DreamerV3, TD-MPC2, PILCO, PETS, MuZero, EfficientZero | IRIS, Delta-IRIS, STORM, DIAMOND (token-based digital worlds) | SimCLR/MoCo/CURL representation learning | VAE, latent diffusion, neural surrogates |
| **L2 Simulator** | Physics engines, video models (Sora-class), RoboCasa, sim-to-real | Web/GUI agents (OSWorld, SWE-bench, WebArena), code agents | Sotopia, generative agents (Park 2023), sandbox arch | GraphCast (weather), operator learning, DiscoveryBench, ScienceWorld |
| **L3 Evolver** | Closed-loop manipulation, dynamics revision from grasp failure | Installation-failure → reusable-skill loops | Strategy revision in service envs | AlphaEvolve (2025), Boiko et al. autonomous chemistry, hypothesis-driven loops |

### 4.4 Where EPYC's stack lands on this grid

Mapping our active workstreams onto the L×R grid (an exercise the paper does not do for us, but its taxonomy enables):

- **Autopilot species loop** (`autopilot-continuous-optimization.md`): **L3 Evolver / Digital regime**. The species loop revises its own routing/prompts/structure based on AR-3 evaluation evidence. Digital because the constraints are software contracts (Pareto archive validity, eval suite invariance, llama-server stability), not physical laws.
- **Agent-World ETD species** (`agent-world-env-synthesis.md` Phase 1): **L2 Simulator → L3 Evolver bridge / Digital regime**. The ETD agent synthesizes a digital-laws environment (MCP tools as state, verifiers as constraint checks); when training succeeds, the policy becomes an L3 system whose model of digital environments evolves with capability gaps.
- **Meta-harness search** (`meta-harness-optimization.md` Tier 3): **L3 Evolver / Digital regime**. The harness-search outer loop revises tool definitions, prompt templates, and routing based on aggregate trial outcomes.
- **Q-scorer + learned-routing-controller** (`routing-intelligence.md`): **L1 Predictor / Digital regime**. Predicts per-prompt difficulty and routes accordingly. Pure prediction, no rollout, no revision.
- **AR-3 tiered eval tower**: **Evaluation surface for L1/L2/L3 systems above**. Independent of the levels.

This mapping suggests an immediate consolidation: the autopilot loop, agent-world ETD, and meta-harness search are all L3-Evolver-on-Digital-laws instances and should share a common evaluation rubric. The paper's four evaluation principles (next section) provide that rubric.

---

## 5. The four evaluation principles (Section 6.1)

Beyond generic prediction accuracy, the paper proposes four capabilities:

| Principle | Definition | EPYC-instance |
|-----------|-----------|---------------|
| **Long-horizon coherence** | "Rollouts remain usable over H steps rather than degrading immediately via compounding error" | Autopilot must maintain Pareto-archive validity over ≥100 mutation rounds without quality collapse |
| **Intervention sensitivity** | "Counterfactual edits (action or premise changes) induce stable and directionally meaningful trajectory changes" | Disabling species 0/1/2/3 individually should produce predictable Pareto-front shifts; if not, the species is collinear with another or malfunctioning |
| **Constraint consistency** | "Generated futures respect the governing laws of the target regime" | All Pareto frontier points must satisfy quality-floor + per-suite guard + routing-diversity gates; any frontier point that violates a gate is a mis-categorized data point |
| **Closed-loop use** | Planning, acting, self-improvement through interaction | Species loop must measurably improve T2-suite scores over runs; if not, the loop is an open-loop randomizer |

**These four are testable in our existing AR-3 eval infrastructure today** — they are just rubric labels for behavior we already care about. The adoption cost is documentation (relabeling AR-3 metrics in these terms) plus per-run reporting (each AR-3 run cycle should report all four).

This is the paper's most actionable single contribution for EPYC.

---

## 6. The L3 governance recipe (Section 5.4) — directly maps to autopilot SafetyGate

Section 5.4 prescribes for L3 Evolver systems:

> "Governed validation: updates pass regression and robustness gates (including rollback and canary policies)."

Mapping to existing autopilot infrastructure:

| Paper's L3 governance prescription | Autopilot equivalent |
|------------------------------------|--------------------|
| Regression gate | Quality floor (per-T2-suite) — `autopilot-continuous-optimization.md` SafetyGate |
| Robustness gate | Per-suite guard (no-suite-falls-below threshold) |
| Rollback policy | Hot-swap reversal on quality regression (Pareto archive provides previous configurations) |
| Canary policy | T0 (10q/30s) → T1 (100q/5m) → T2 (500+q/30m) tiered evaluation tower |

**The autopilot already implements this recipe.** What the paper adds is **vocabulary** (we should call them "L3 governance gates" to align with the field) and **completeness check** — verify all four prescriptions are implemented and reported per cycle.

A minor identified gap: the paper's "rollback policy" expects automatic rollback. The autopilot Pareto archive supports rollback but the controller currently uses Pareto-front replacement rather than explicit rollback semantics. Worth documenting whether these are equivalent for our purposes.

---

## 7. The Minimal Reproducible Evaluation Package (MREP) — proposed but not released

Section E.6 sketches an MREP intended to be:
- Standardized across L1/L2/L3 boundary conditions
- Including long-horizon coherence metrics, intervention sensitivity tests, constraint-violation detection across regimes, and a capability coverage matrix
- Released as a public package

**Status as of 2026-04-28**: NOT released. The companion repo (matrix-agent/awesome-agentic-world-modeling, 105★) is a bibliography not a package — it lists existing benchmarks (OSWorld, WebArena, SWE-bench, MCU) and organizes them by L×R but does not bundle them or define a common evaluation interface.

**Implication**: the most directly useful artifact the paper *promises* is not yet available. Set a watch on:
1. arxiv.org/abs/2604.22748 for v2/v3 revisions adding code links
2. matrix-agent/awesome-agentic-world-modeling for an `mrep/` or `eval/` directory
3. Author Twitter/blog announcements (Meng Chu, Kevin Qinghong Lin)

If the MREP is released, re-rank intake-498 to high relevance and run a focused integration handoff.

---

## 8. Beyond L3 — meta-world-modeling and our autopilot

Section 8.2-8.3 introduces "Beyond L3": systems where **the governing laws themselves become learnable**. The paper frames this as an open research direction with no current systems instantiating it.

**EPYC parallel**: the autopilot species framework is exactly such a system. Species 3 (StructuralLab) modifies flags + routing model lifecycle — i.e., the digital "laws" governing how the orchestrator behaves. When StructuralLab disables a flag, it is rewriting the rules the L3 species-0/1/2 operate under.

This is an interesting framing but should not be over-claimed (per `feedback_closure_inflation`). What we have is one species (StructuralLab) modifying the operating rules of the other three; we don't have a principled meta-learning loop that *itself* gets revised. The honest framing: "the autopilot has an L3.5 hook (StructuralLab) but is not a Beyond-L3 system in the paper's sense; treating it as such would be inflation."

**Practical use**: cite the Beyond-L3 framing as motivation for keeping StructuralLab's safety gates strict (it modifies the operating rules of other species; failures cascade) — not as evidence that we have already solved meta-world-modeling.

---

## 9. Cross-regime transfer — the Section 8.2 open problem

The paper highlights cross-regime transfer (physical → digital → social) as an open research direction. Most EPYC work is single-regime (digital), so this isn't directly actionable. But:

- If we ever expand the autopilot to optimize *physical* properties (e.g., NUMA-physical placement, NVMe IO patterns), that becomes an L3-Evolver-on-Physical-laws extension.
- Per `project_raid_numa_split_nps4` memory, the NPS4 layout interacts with physical IO topology in ways the autopilot doesn't currently model. A future autopilot extension that treats NUMA layout as physical-regime variables would be the cleanest mapping of cross-regime work onto our stack.

Park as a long-term option, not a near-term action.

---

## 10. Risks and contradicting evidence

1. **Field is fragmented** — at least three competing 2025-2026 surveys cover overlapping ground:
   - arxiv:2503.23037 — "Agentic LLM survey"
   - arxiv:2601.12560 — "Agentic AI Architectures and Taxonomies"
   - arxiv:2601.01743 — "AI Agent Systems"
   - Convergence on Levels × Laws as the canonical taxonomy is unlikely. Our adoption is locally useful regardless of field-wide convergence, but don't bet on the vocabulary being universal in 2 years.

2. **"Critiques of World Models"** (arxiv:2507.05169) argues the primary goal should be "simulating all actionable possibilities of the real world for purposeful reasoning" — i.e., the L×R taxonomy may underweight the **actionability axis**. For our autopilot, this critique is mostly fine because the Pareto archive does encode actionability (every frontier point is a deployable configuration), but worth tracking.

3. **No empirical validation of the four evaluation principles** — they are proposed, not benchmarked across the surveyed systems. The paper does not produce a table showing which of the 100+ systems satisfy each principle. Adoption value is in the rubric, not in derivative claims.

4. **MREP is a promise, not a product** — promises in survey papers regularly fail to materialize. Don't make EPYC plans contingent on the MREP shipping.

5. **42-author surveys have diluted accountability** — sections may have been written by different sub-teams and reconciled rather than co-developed; minor inconsistencies in how L1/L2/L3 boundaries are drawn across regimes are likely. Treat the framework as a starting vocabulary, not a precise specification.

6. **Closure-inflation risk** — the temptation to declare "we have solved L3 Evolver / Digital regime" because autopilot exists. We have *one instance* of an L3-Digital system; the field has many. Adopting the vocabulary is fine; claiming dominance is not.

---

## 11. Integration into the GPU-gated backlog

The world-model-survey is **not GPU-gated by itself**, but its integration touches GPU-gated work:

### Direct (CPU-feasible, do now)

| Action | Owner / handoff | Cost | Value |
|--------|----------------|------|-------|
| Add L1/L2/L3 + four-regime vocabulary to `wiki/autonomous-research.md` | wiki | 1h | Common language across handoffs |
| Update AR-3 evaluation reporting to label scores by the four principles (long-horizon coherence, intervention sensitivity, constraint consistency, closed-loop use) | autopilot-continuous-optimization.md | 2-4h | Clearer evaluation narrative; surfaces intervention-sensitivity gaps |
| Document autopilot SafetyGate as the L3 governance instantiation in `autopilot-continuous-optimization.md` | autopilot-continuous-optimization.md | 1h | Vocabulary alignment; identifies rollback-vs-Pareto-replacement gap |
| Watch matrix-agent/awesome-agentic-world-modeling for MREP release | research-intake | 0h ongoing | Don't miss the actionable artifact if/when it ships |

### GPU-gated (deferred to GPU acquisition)

| Action | Owner / handoff | Trigger | Value |
|--------|----------------|---------|-------|
| Map Agent-World Phase 2 (multi-env GRPO RL training) onto the L3-Evolver / Digital framing | agent-world-env-synthesis.md | GPU acquired | Phase 2 plan reads as canonical L3-Evolver training, easier external communication and benchmarking |
| Run the four evaluation principles on Agent-World-trained policy vs autopilot-evolved policy | agent-world-env-synthesis.md | GPU + Phase 2 trained | Cross-regime transfer signal — does Agent-World-style RL training produce better-on-our-rubric L3 systems than autopilot's species loop? |
| If MREP ships, run our autopilot through it as external sanity check | autopilot-continuous-optimization.md | MREP released + GPU optional | External corroboration of autopilot competitiveness |

### Non-actions

- Don't rewrite autopilot architecture to match the paper. The taxonomy is a label, not a redesign blueprint.
- Don't create a new "L3 Evolver Index" handoff. The autopilot/agent-world/meta-harness handoffs already exist; just relabel.
- Don't author original L1/L2/L3 contributions for publication. Out of scope; we are an inference-optimization shop, not a foundational AI lab.

---

## 12. Open questions to revisit

1. Will the MREP ship? If yes, when, and does it cover digital-regime L3 systems usefully?
2. Do other 2025-2026 surveys converge on Levels × Laws or compete with their own taxonomies?
3. Does mapping autopilot's SafetyGate onto the paper's "rollback policy" expose a real gap (we use Pareto-front replacement, paper expects explicit rollback)? Worth a one-pager investigation.
4. Are there L3-Evolver / Digital instances in the surveyed 100+ systems we should benchmark against (e.g., "installation-failure → reusable-skill loops" instances cited in Section 5)?
5. If we ever benchmark autopilot externally, which paper-cited systems are the natural baselines?

---

## 13. References

- Paper: arxiv.org/abs/2604.22748 — "Agentic World Modeling: Foundations, Capabilities, Laws, and Beyond" (Chu et al., 42 authors, submitted 2026-04-24)
- Companion repo: github.com/matrix-agent/awesome-agentic-world-modeling
- Critique: arxiv.org/abs/2507.05169 — "Critiques of World Models"
- Competing surveys: arxiv:2503.23037, 2601.12560, 2601.01743
- Internal anchors:
  - intake-444 — Agent-World (primary subject); deep-dive at `research/deep-dives/agent-world-environment-synthesis.md`
  - intake-244 — Meta-Harness
  - intake-411 — Qwen-Agent MCP singleton
  - intake-413 — HCC autopilot
  - intake-148/149 — AutoResearch loop pattern
- Active handoffs:
  - `agent-world-env-synthesis.md` — primary integration point
  - `autopilot-continuous-optimization.md` — L3-Evolver / Digital instance
  - `meta-harness-optimization.md` — Tier 3 outer loop, also L3-Evolver / Digital
  - `routing-intelligence.md` — L1-Predictor / Digital instance
  - `gpu-acceleration-path.md` — GPU-gated activation point for Agent-World Phase 2 cross-rubric eval
