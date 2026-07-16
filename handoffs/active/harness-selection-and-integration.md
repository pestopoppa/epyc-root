# Harness Selection & Integration — Orchestrator ↔ User-Facing Harness

**Status**: active — strategy/selection index (harness UNCHOSEN; no implementation committed)
**Created**: 2026-07-16 (operator question: keep the Orch orthogonal to its harness, or bake it in?)
**Categories**: agent_architecture, inference_serving, tool_implementation, context_management
**Related (down)**: [`hermes-outer-shell.md`](hermes-outer-shell.md) (Hermes candidate eval), [`hermes-agent-index.md`](hermes-agent-index.md) (Hermes/agent-UX dispatch), [`tool-output-compression.md`](tool-output-compression.md) (context-collision surface), [`meta-harness-optimization.md`](meta-harness-optimization.md) (RLM harness self-improvement lineage)
**Related (precedent)**: [`../completed/orchestrator-conversation-management.md`](../completed/orchestrator-conversation-management.md) (backend-side session/compaction boundary), [`../archived/claude-code-local-constellation-routing.md`](../archived/claude-code-local-constellation-routing.md) (archived ACP-as-Path-B precedent)

## Objective

Decide **how** the orchestrated stack ("the Orch") relates to its user-facing agent harness, and eventually **which** open-source harness to adopt — without prematurely coupling to one. This index owns the harness-agnostic thesis + the selection decision; per-candidate detail lives in the leaf handoffs below.

## Thesis — orthogonal backend moat + cooperation-requiring agent loop

The Orch's value splits into two layers:

- **(A) Harness-agnostic backend moat** — kernels, MTP spec-dec, quantization, model serving, the eval tower, MEASUREMENT governance, cost-aware *scoring*. It has **no UI** and **must stay orthogonal** behind a stable API (`/v1/chat/completions` + `x_*` overrides). Baking it into a harness would entangle the measurement trust boundary with frontend churn. Supporting datapoint: **intake-426** — a coding harness (Claude Code) is ~98.4% operational infrastructure / ~1.6% AI decision logic; the harness is mostly plumbing, our intelligence is the moat.
- **(B) Agent-loop intelligence** — per-turn routing / difficulty estimation, context-folding / tool-output compaction, plan-review reroute, sub-agent fan-out, trace-memory, cost-aware escalation. **Layer (B) only pays off if the harness COOPERATES** (defers to / integrates with the Orch's decisions).

**Load-bearing consequence (operator, 2026-07-16): cooperation ⇒ the harness must be OPEN-SOURCE.** A closed harness (Claude Code, grok-build's binary — intake-249/426/827) cannot be modified to defer to the Orch's routing/compaction/escalation, so (B) would be wasted or actively contested. Therefore closed harnesses are excluded as Orch frontends. **Claude Code is the development harness (this repo's dev loop), NOT an Orch-frontend candidate.**

**Recommendation (default posture):** keep (A) orthogonal; do **NOT** build a bespoke harness (that re-implements ~98% plumbing per intake-426). Adopt an open-source harness whose cooperation surface fits, and inject (B) through it (typed override flags — see the Deterministic Override Flags pattern in `hermes-outer-shell.md` L55-69 — and/or MCP, and/or ACP).

## Candidates (selection is OPEN)

| Candidate | Kind | Cooperation surface | Detailed track |
|---|---|---|---|
| **Hermes / OpenGauss** | open-source | `/v1` + `x_*` overrides; ACP adapter as "Path B" | [`hermes-outer-shell.md`](hermes-outer-shell.md) + [`hermes-agent-index.md`](hermes-agent-index.md) |
| **OpenCode** | open-source | TBD (no eval yet) | — (task HS-1 stands one up) |
| **ACP-speaking open harnesses** | open-source | ACP (Agent Client Protocol) | contingent on ACP-ROI (task HS-2) |
| ~~Claude Code / grok-build~~ | closed | none (can't be made to defer) | excluded — reference only (dev harness) |

## Prioritized Task List

- [ ] **HS-1 — Cooperation-surface audit per open candidate (Hermes, OpenCode):** for each, map how its layer-(B) behavior (context compaction, model selection, sub-agent spawning, tool loop) can be made to DEFER to the Orch's routing / context-folding / escalation, and the integration/patch cost. Generalizes the **Client Surface Audit** in `hermes-outer-shell.md` (L321-344) beyond Hermes. **Do NOT audit Claude Code** (dev harness, not a candidate).
- [ ] **HS-2 — ACP ROI evaluation:** is adopting ACP as the integration protocol worth it? High ROI would *widen* the candidate set to all ACP-speaking open harnesses rather than committing to Hermes/OpenCode native surfaces. **Re-open the intake-263 "MCP-first, ACP=editor-agent-not-inference" lean with this lens** (it predates the unchosen-harness framing).
- [ ] **HS-3 — (only if HS-2 is positive) Survey ACP-speaking open harnesses** as additional candidates (e.g., Local Studio Pi / intake-833, Zed, others); do NOT include closed ones.
- [ ] **HS-4 — Harness-selection decision gate:** Hermes vs OpenCode vs an ACP-speaker, gated on HS-1 + HS-2. Default outcome preserved: (A) stays orthogonal; no bespoke harness unless a specific research-demo differentiator justifies it.

## Dependency Graph

```text
HS-1 cooperation-surface audit (Hermes, OpenCode) ─┐
HS-2 ACP ROI evaluation ───────────────────────────┤→ HS-3 (if ACP+) → HS-4 selection decision
                                                    └→ HS-4 selection decision
```

## Cross-Cutting Concerns

1. **Context-collision surface** — a candidate harness's OWN conversation compaction / prompt-cache mgmt / sub-agent spawning can double-up or fight orchestrator-side Phase-2 compression + context-folding. Owned by [`tool-output-compression.md`](tool-output-compression.md) (see its Phase-4 cross-refs) and the Hermes Cons/Key-Questions in `hermes-outer-shell.md` (L37-42, L84-90). This is the concrete instance of "(B) needs cooperation."
2. **Backend-moat orthogonality + MEASUREMENT trust boundary** — layer (A) (eval tower, scoring, era registry, safety gates) stays server-side and human-amendment-only; a harness must never absorb it.
3. **RLM harness self-improvement lineage** — the "specialized harness beats a general one" idea (intake-517 HALO) cross-links to [`meta-harness-optimization.md`](meta-harness-optimization.md) (frozen pointer; do not route work there).

## Key Files / Surfaces

- The **`/v1/chat/completions` + `x_*` override** contract (the stable orthogonal API) — orchestrator routing/override surface.
- `research/deep-dives/opengauss-architecture-analysis.md` — ACP / session-analytics / context-compression prior art.
- `hermes-outer-shell.md` L55-69 (Deterministic Override Flags = the cooperation pattern), L321-344 (Client Surface Audit = the audit instrument).

## Reporting Instructions

- Record HS-1/HS-2 findings here (or in the candidate leaf) and flip the checkbox with `✅ YYYY-MM-DD`. HS-4's decision, when made, updates this index's Status and the candidate handoffs.
- Any change to the orthogonality posture or the open-source requirement is an operator decision — flag, do not decide autonomously.

## Evidence Base (intake)

intake-833 Local Studio (mgmt-GUI end) · intake-827 grok-build (closed, ACP) · intake-263 claude-acp-server (ACP↔Anthropic; prior MCP-first lean) · intake-426 "Dive into Claude Code" (98.4% infra / 1.6% logic) · intake-249 Claude Code leak analysis · intake-243 Claw Code · intake-254 Goose · intake-255 Clido · intake-473 pi-agent-core · intake-517 HALO · intake-183 0xSero/vllm-studio.
